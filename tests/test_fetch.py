import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("fetch", Path(__file__).resolve().parents[1] / "scripts/fetch.py")
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)


class FetchTests(unittest.TestCase):
    def test_relative_urls_and_default_scheme(self):
        self.assertEqual(fetch.destination("../next.html", "https://example.com/a/index.html"), "https://example.com/next.html")
        self.assertEqual(fetch.destination("example.com"), "https://example.com")
        for url in ("javascript:alert(1)", "ftp://example.com", "https://name:password@example.com", "file://foreign/tmp/page"):
            with self.assertRaises(ValueError):
                fetch.destination(url)

    def test_start_page_and_file_limit(self):
        self.assertIn("<h1>", fetch.fetch({"url": "about:start"})["html"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "page.html"
            path.write_text("<h1>Local HTML</h1>")
            self.assertEqual(fetch.fetch({"url": path.as_uri()})["html"], path.read_text())
            path.write_bytes(b"x" * (fetch.LIMIT + 1))
            with self.assertRaises(ValueError):
                fetch.fetch({"url": path.as_uri()})

    def test_redirect_cannot_open_local_files(self):
        from urllib.request import Request
        with self.assertRaises(ValueError):
            fetch.Redirects().redirect_request(Request("https://example.com"), None, 302, "", {}, "file:///private")

    def test_http_fetch_follows_redirect_and_preserves_final_base(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import threading
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", "/pages/index.html")
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<h1>HTTP document</h1><a href='next.html'>Next</a>")
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = f"http://127.0.0.1:{server.server_port}"
            result = fetch.fetch({"url": origin + "/redirect"})
            self.assertEqual(result["url"], origin + "/pages/index.html")
            self.assertIn("HTTP document", result["html"])
            self.assertEqual(fetch.destination("next.html", result["url"]), origin + "/pages/next.html")
        finally:
            server.shutdown()
            thread.join(2)
            server.server_close()
