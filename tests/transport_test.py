"""Fixture server for tests/transport_test.zi; every check runs in Ziran."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

LIMIT = 524288


class Handler(BaseHTTPRequestHandler):
    def send(self, status, content_type, body, headers=()):
        self.send_response(status)
        if content_type:
            self.send_header("Content-Type", content_type)
        for name, value in headers:
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # curl stops oversized documents early, as intended

    def do_GET(self):
        if self.path == "/redirect":
            self.send(302, "", b"", [("Location", "/pages/index.html")])
        elif self.path == "/pages/index.html":
            self.send(200, "text/html; charset=utf-8", b"<h1>HTTP document</h1><a href='next.html'>Next</a>")
        elif self.path == "/image":
            self.send(200, "image/png", b"\x89PNG\r\n")
        elif self.path == "/to-file":
            self.send(302, "", b"", [("Location", "file:///etc/hostname")])
        elif self.path == "/big":
            self.send(200, "text/html", b"x" * (LIMIT + 1))
        else:
            self.send(404, "text/html", b"<h1>Missing</h1>")

    def log_message(self, *args):
        pass


def main():
    binary = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix="browser-transport-") as folder:
        root = Path(folder)
        (root / "local page.html").write_text("<h1>Local HTML</h1>")
        (root / "big.html").write_bytes(b"x" * (LIMIT + 1))
        (root / "notes.txt").write_text("a <b> & c")
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = dict(os.environ, BROWSER_TEST_DIR=str(root),
                       BROWSER_TEST_ORIGIN=f"http://127.0.0.1:{server.server_port}")
            env.pop("http_proxy", None)
            env.pop("HTTP_PROXY", None)
            return subprocess.run([str(binary)], env=env, timeout=120).returncode
        finally:
            server.shutdown()
            thread.join(2)
            server.server_close()


if __name__ == "__main__":
    sys.exit(main())
