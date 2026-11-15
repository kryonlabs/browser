"""Measure an owned browser process tree on the current private display."""

import argparse
import ast
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time


def process_stat(pid):
    text = Path(f"/proc/{pid}/stat").read_text()
    fields = text[text.rfind(")") + 2:].split()
    return int(fields[1]), int(fields[2]), int(fields[11]), int(fields[12])


def process_tree(root):
    parents = {}
    group = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            pid = int(entry.name)
            parent, process_group, _, _ = process_stat(pid)
            parents[pid] = parent
            if process_group == root:
                group.append(pid)
        except (FileNotFoundError, ProcessLookupError, PermissionError,
                IndexError, ValueError):
            pass
    if group:
        return sorted(group)
    owned = {root}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in owned and pid not in owned:
                owned.add(pid)
                changed = True
    return sorted(owned)


def memory(pids):
    pss = 0
    rss = 0
    live = []
    for pid in pids:
        try:
            lines = Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        live.append(pid)
        for line in lines:
            if line.startswith("Pss:"):
                pss += int(line.split()[1])
            elif line.startswith("Rss:"):
                rss += int(line.split()[1])
    return pss, rss, live


def cpu_ticks(pids):
    total = 0
    for pid in pids:
        try:
            _, _, user, system = process_stat(pid)
            total += user + system
        except (FileNotFoundError, ProcessLookupError, PermissionError,
                IndexError, ValueError):
            pass
    return total


def wait_native_ready(process, expected_url=None):
    deadline = time.monotonic() + 12
    window = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("native browser exited before opening a window")
        result = subprocess.run(
            ["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            window = result.stdout.splitlines()[0]
            break
        time.sleep(0.1)
    if not window:
        raise RuntimeError("native browser window did not appear")
    while time.monotonic() < deadline:
        raw = subprocess.check_output(
            ["xprop", "-id", window, "_HARMONY_APP_STATE"], text=True
        )
        if " = " in raw:
            state = json.loads(ast.literal_eval(raw.split(" = ", 1)[1].strip()))
            if (not state["loading"] and state["nodes"] > 0 and
                    (expected_url is None or state["url"] == expected_url)):
                return window
        time.sleep(0.1)
    raise RuntimeError("native browser did not finish loading")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--settle", type=float, default=3.0)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--url")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if os.environ.get("BROWSER_PRIVATE_XVFB") != "1":
        raise SystemExit("resource measurements require the private Xvfb wrapper")
    command = arguments.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("missing browser command")

    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        if arguments.native:
            window = wait_native_ready(process)
            if arguments.url:
                subprocess.run(["xdotool", "key", "--window", window, "ctrl+l"], check=True)
                subprocess.run(["xdotool", "type", "--window", window,
                                "--clearmodifiers", arguments.url], check=True)
                subprocess.run(["xdotool", "key", "--window", window, "Return"], check=True)
                wait_native_ready(process, arguments.url)
        time.sleep(arguments.settle)
        start_pids = process_tree(process.pid)
        if not start_pids:
            raise RuntimeError("browser command left no live owned processes")
        start_ticks = cpu_ticks(start_pids)
        pss_samples = []
        rss_samples = []
        live = []
        started = time.monotonic()
        while True:
            pss, rss, live = memory(process_tree(process.pid))
            pss_samples.append(pss)
            rss_samples.append(rss)
            elapsed = time.monotonic() - started
            if elapsed >= arguments.interval:
                break
            time.sleep(min(0.5, arguments.interval - elapsed))
        elapsed = time.monotonic() - started
        end_ticks = cpu_ticks(process_tree(process.pid))
        ticks = max(0, end_ticks - start_ticks)
        clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        cpu_seconds = ticks / clock_ticks
        result = {
            "label": arguments.label,
            "root_pid": process.pid,
            "process_count": len(live),
            "interval_seconds": round(elapsed, 3),
            "pss_kib_median": round(statistics.median(pss_samples)),
            "pss_kib_peak": max(pss_samples),
            "rss_kib_median": round(statistics.median(rss_samples)),
            "rss_kib_peak": max(rss_samples),
            "cpu_seconds": round(cpu_seconds, 3),
            "cpu_percent_one_core": round(cpu_seconds * 100.0 / elapsed, 2),
        }
        print(json.dumps(result, sort_keys=True))
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if process.poll() is None:
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
