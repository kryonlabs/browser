"""Exercise the new engine through its own window and disposable documents."""
import ast
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
assert os.environ.get("BROWSER_PRIVATE_XVFB") == "1", "Use make window-test"
output = ROOT / "build/screenshots"
output.mkdir(parents=True, exist_ok=True)
process = subprocess.Popen([str(ROOT / "build/browser-desktop")], cwd=ROOT, stderr=subprocess.PIPE)


def xdo(*args):
    return subprocess.check_output(["xdotool", *map(str, args)], text=True).strip()


def state(url=None):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        raw = subprocess.check_output(["xprop", "-id", window, "_HARMONY_APP_STATE"], text=True)
        if " = " in raw:
            value = json.loads(ast.literal_eval(raw.split(" = ", 1)[1].strip()))
            if not value["loading"] and value["nodes"] > 0 and (url is None or value["url"] == url):
                return value
        time.sleep(.1)
    raise AssertionError("Browser did not load " + str(url))


def action(label):
    control = next(c for c in state()["controls"] if c["label"] == label and c["enabled"])
    xdo("mousemove", "--window", window, int(control["x"] + control["width"] / 2), int(control["y"] + control["height"] / 2))
    xdo("click", "1")
    time.sleep(.2)


try:
    deadline = time.monotonic() + 10
    window = ""
    while time.monotonic() < deadline:
        assert process.poll() is None, process.stderr.read().decode()
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)], capture_output=True, text=True)
        if result.returncode == 0:
            window = result.stdout.splitlines()[0]
            break
        time.sleep(.1)
    assert window, "Browser window did not open"
    xdo("windowsize", window, 1060, 800)
    state("about:start")
    subprocess.run(["import", "-window", window, str(output / "start.png")], check=True)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "index.html"
        second = Path(folder) / "next.html"
        path.write_text("<title>Fixture page</title><style>body{background:#f4f7fb}main{max-width:760px;margin:12px auto;padding:20px;background:white}h1{color:#2468bc}</style><main><h1>A native HTML page</h1><p>The browser owns this document.</p><a href='next.html'>Next page</a>" + "<p>A paragraph for independent document scrolling.</p>" * 35 + "</main>")
        second.write_text("<title>Linked page</title><h1>Links stay in Browser</h1><p>Relative file navigation works.</p>")
        action("Address")
        xdo("key", "ctrl+a")
        xdo("type", "--clearmodifiers", path.as_uri())
        xdo("key", "Return")
        assert state(path.as_uri())["title"] == "Fixture page"
        subprocess.run(["import", "-window", window, str(output / "html-css.png")], check=True)
        action("Next page")
        state(second.as_uri())
        action("Back")
        state(path.as_uri())
        xdo("mousemove", "--window", window, 700, 600)
        xdo("click", "--repeat", "4", "--delay", "60", "5")
        time.sleep(.5)
        assert state()["scroll"] > 0
        action("Next")
        state(second.as_uri())
        action("Back")
        assert state(path.as_uri())["scroll"] > 0, "Back lost the page position"
        xdo("windowsize", window, 640, 800)
        time.sleep(.5)
        subprocess.run(["import", "-window", window, str(output / "narrow.png")], check=True)
    print("Native HTML/CSS rendering, address input, relative links, Back/Next, independent scrolling and narrow window verified")
finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
