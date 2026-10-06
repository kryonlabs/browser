#!/usr/bin/env python3
"""Document IO only. Ziran owns HTML, CSS, layout and rendering."""
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urljoin, urlsplit, unquote
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler

LIMIT = 524288


def destination(value, base=""):
    if value == "about:start":
        return value
    if ":" not in value and not base:
        value = "https://" + value
    url = urljoin(base, value)
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https", "file") or parts.username or parts.password:
        raise ValueError("Enter an HTTP(S) address or a local file URL.")
    if parts.scheme == "file" and parts.netloc not in ("", "localhost"):
        raise ValueError("Only local file URLs are supported.")
    if parts.scheme in ("http", "https") and not parts.netloc:
        raise ValueError("Enter a complete website address.")
    return url


class Redirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = destination(newurl, req.full_url)
        if urlsplit(url).scheme not in ("http", "https"):
            raise ValueError("A website cannot redirect to a local file.")
        return super().redirect_request(req, fp, code, msg, headers, url)


def fetch(request):
    url = destination(request.get("url", "about:start"), request.get("base", ""))
    if url == "about:start":
        content = (Path(__file__).resolve().parent / "start.html").read_bytes()
    elif urlsplit(url).scheme == "file":
        with Path(unquote(urlsplit(url).path)).open("rb") as source:
            content = source.read(LIMIT + 1)
    else:
        req = Request(url, headers={"User-Agent": "KryonBrowser/0.1", "Accept": "text/html,text/plain;q=0.9"})
        with build_opener(Redirects()).open(req, timeout=15) as response:
            url = response.url
            if response.headers.get_content_type() not in ("text/html", "text/plain", "application/xhtml+xml"):
                raise ValueError("This resource is not an HTML or text document.")
            content = response.read(LIMIT + 1)
    if len(content) > LIMIT:
        raise ValueError("This document exceeds the 512 KiB page limit.")
    html = content.decode("utf-8", errors="replace")
    if urlsplit(url).path.endswith(('.txt', '.zi', '.css')):
        import html as escaping
        html = "<pre>" + escaping.escape(html) + "</pre>"
    return {"url": url, "html": html, "error": ""}


def main():
    os.umask(0o077)
    output = Path(sys.argv[2])
    try:
        result = fetch(json.loads(Path(sys.argv[1]).read_text()))
    except ValueError as exc:
        result = {"error": str(exc)}
    except Exception:
        result = {"error": "Could not load this page. Check the address and your connection."}
    fd, filename = tempfile.mkstemp(dir=output.parent)
    with os.fdopen(fd, "w") as stream:
        json.dump(result, stream, ensure_ascii=False)
    os.replace(filename, output)


if __name__ == "__main__":
    main()
