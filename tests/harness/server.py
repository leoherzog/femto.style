"""Static HTTP server for the selftest fixture site (tests/fixtures/site/) on 127.0.0.1 and a free port.

A named control from tests/fixtures/controls.json can change what it serves: `edits` replace text
that must occur exactly once in a file, and `remove` makes files answer 404. The edits are checked
when the server starts, so a stale control is a setup error, not a silent no-op. Text types carry
charset=utf-8.
"""
import http.server
import json
import threading
import urllib.parse
from functools import partial
from pathlib import Path

from .paths import FIXTURES

SITE = FIXTURES / "site"
CONTROLS = FIXTURES / "controls.json"
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
}


class ControlError(Exception):
    pass


def load_controls():
    return json.loads(CONTROLS.read_text())["controls"]


def build_overrides(root: Path, control: str | None):
    """{url path: bytes} for edited files and a set of removed url paths."""
    if not control:
        return {}, set()
    controls = load_controls()
    if control not in controls:
        raise ControlError(f"unknown fixture control {control!r}; see {CONTROLS.relative_to(FIXTURES.parent.parent)}")
    c = controls[control]
    files = {}
    for e in c.get("edits", []):
        rel = e["file"]
        p = root / rel
        if not p.is_file():
            raise ControlError(f"control {control}: {rel} does not exist")
        text = files.get("/" + rel, p.read_bytes()).decode("utf-8")
        n = text.count(e["old"])
        if n != 1:
            raise ControlError(f"control {control}: {e['old']!r} occurs {n} times in {rel}, not once")
        files["/" + rel] = text.replace(e["old"], e["new"]).encode("utf-8")
    removed = {"/" + r for r in c.get("remove", [])}
    for r in removed:
        if not (root / r.lstrip("/")).is_file():
            raise ControlError(f"control {control}: cannot remove {r}, it does not exist")
    return files, removed


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, server_state=None, **kwargs):
        self.st = server_state
        super().__init__(*args, **kwargs)

    def log_message(self, *args):
        pass

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        if path.endswith("/"):
            path += "index.html"
        root = self.st["root"]
        if path in self.st["removed"]:
            return self._send(404, b"removed by the control\n", "text/plain; charset=utf-8")
        body = self.st["files"].get(path)
        if body is None:
            p = (root / path.lstrip("/")).resolve()
            if root not in p.parents or not p.is_file():
                return self._send(404, b"not found\n", "text/plain; charset=utf-8")
            body = p.read_bytes()
        ext = "." + path.rsplit(".", 1)[-1] if "." in path.rsplit("/", 1)[-1] else ""
        return self._send(200, body, TYPES.get(ext, "application/octet-stream"))

    do_HEAD = do_GET


class StaticServer:
    def __init__(self, root: Path = SITE, control: str | None = None):
        root = Path(root).resolve()
        files, removed = build_overrides(root, control)
        self.state = {"root": root, "files": files, "removed": removed}
        handler = partial(_Handler, server_state=self.state)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.httpd.daemon_threads = True
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True, name="fixture-http")
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
