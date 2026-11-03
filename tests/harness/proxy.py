"""The per-session reverse proxy that puts both sides of a comparison on one origin.

A comparison loads side A's <path> and side B's <path> into the same host page, one after the other,
in a same-origin iframe of exact width, so the in-page collector can read both documents and keep
side A's snapshot in memory while side B loads (femto's model). Two servers have two origins, so
each browser session gets its own proxy on a free 127.0.0.1 port:

* /__harness/<file> serves the host page, differ.js and the rig probe from tests/harness/;
* every other request is forwarded to the side that is currently selected (use("a") or use("b")).

The proxy forwards the browser's Host header (the proxy's own host:port), so any absolute URL a
server builds from the request is the same on both sides and points back at the proxy. It asks for
identity encoding, strips conditional request headers and validators, and marks every response
"Cache-Control: no-store": the two sides serve different files at the same URLs, and nothing may be
reused from the other side's load. Location headers that name the upstream origin are rewritten to
the proxy's. Every forwarded request is logged per side (method, path, status), so the cell can
report the document's final status and subresource errors.

The host page removes side A's iframe before Python switches the proxy to side B, so nothing side A
still requests can reach side B's server.

Safari starts a load by requesting the subresources the previous load of the same URL used (WebKit's
speculative loading), and keeps their responses for the next document that asks: a side then gets
the other side's 404 for a stylesheet of its own (p2-styles-safari-light, 2026-11-03). So in Safari
every document load carries a parameter of its own, harness-load (compare.py, with_load_param): no
two loads share a URL. The proxy removes it before it forwards or logs a request, so the servers and
the request log see the route as in Chrome and Firefox, and puts it back on a redirect's Location.

Every forwarded response also carries a report-only Content Security Policy that allows everything
on the proxy's own origin (inline code, eval, data: and blob: URLs included) and reports anything
else to /__harness/csp/<tag> on the proxy, tagged with the load it belongs to (use()). It blocks
nothing, so the documents behave as without it, and it reaches what the page's Resource Timing
cannot: a worker's own loads (a worker script gets its policy from its own response), a frame in a
closed shadow root, a load that fails at the network level, an image from the browser's cache. The
reports are criterion 15 evidence for the cell of their tag (compare.py, csp_loads).
"""
import http.client
import http.server
import json
import re
import threading
import time
import urllib.parse
from functools import partial

from .paths import HARNESS, HARNESS_FILES, HARNESS_PREFIX

HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
       "transfer-encoding", "upgrade", "proxy-connection"}
DROP_REQUEST = HOP | {"if-none-match", "if-modified-since", "if-match", "if-unmodified-since", "if-range",
                      "accept-encoding", "content-length"}
DROP_RESPONSE = HOP | {"etag", "last-modified", "expires", "cache-control", "age", "content-length", "date", "server"}
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
CSP_PATH = HARNESS_PREFIX + "csp/"
# Everything on the proxy's origin ('self'), inline code and eval, data: and blob: URLs is allowed;
# any other origin is a violation, reported, never blocked (report-only). default-src covers every
# fetch directive (scripts, styles, images, fonts, media, frames, workers, connect, manifests).
CSP_POLICY = "default-src 'self' 'unsafe-inline' 'unsafe-eval' data: blob:; report-uri " + CSP_PATH + "{tag}"
CSP_MAX_REPORTS = 200  # per tag: a page that reports more is failing anyway
LOAD_PARAM = "harness-load"
_LOAD_RE = re.compile(r"([?&])" + LOAD_PARAM + r"=([^&#]*)(&?)")


def with_load_param(path, value):
    """path with harness-load=value added to its query, before any fragment."""
    base, hash_, frag = path.partition("#")
    return f"{base}{'&' if '?' in base else '?'}{LOAD_PARAM}={value}{hash_}{frag}"


def strip_load_param(path):
    """path without its harness-load parameter, the others as written; unchanged when it has none."""
    return _LOAD_RE.sub(lambda m: m.group(1) if m.group(3) else "", path)


def load_param(path):
    """The value of path's harness-load parameter, or None."""
    m = _LOAD_RE.search(path.partition("#")[0])
    return m.group(2) if m else None


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, proxy=None, **kwargs):
        self.proxy = proxy
        super().__init__(*args, **kwargs)

    def log_message(self, *args):
        pass

    def _send(self, status, body=b"", headers=()):
        self.send_response(status)
        for k, v in headers:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)

    def _harness_file(self, path):
        name = path[len(HARNESS_PREFIX):]
        if name not in HARNESS_FILES:
            self.proxy._note_harness_404(path)
            return self._send(404, b"not a harness file\n", [("Content-Type", "text/plain; charset=utf-8")])
        body = (HARNESS / name).read_bytes()
        ext = "." + name.rsplit(".", 1)[-1]
        return self._send(200, body, [("Content-Type", TYPES.get(ext, "application/octet-stream"))])

    def _forward(self):
        t0 = time.time()
        side, upstream = self.proxy.current()
        load = load_param(self.path)
        path = strip_load_param(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        if not upstream:
            self.proxy._note(side, self.command, path, 503, t0, "no side selected")
            return self._send(503, b"harness proxy: no side selected\n", [("Content-Type", "text/plain; charset=utf-8")])
        u = urllib.parse.urlsplit(upstream)
        headers = {k: v for k, v in self.headers.items() if k.lower() not in DROP_REQUEST}
        headers["Accept-Encoding"] = "identity"
        conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=self.proxy.timeout)
        try:
            conn.request(self.command, path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            status, reason = resp.status, resp.reason
            out = []
            for k, v in resp.getheaders():
                kl = k.lower()
                if kl in DROP_RESPONSE:
                    continue
                if kl == "location":
                    v = self.proxy.rewrite_location(v, upstream)
                    if load is not None and v.startswith("/") and not v.startswith("//"):
                        v = with_load_param(v, load)
                out.append((k, v))
        except (OSError, http.client.HTTPException) as e:
            self.proxy._note(side, self.command, path, 502, t0, f"{type(e).__name__}: {e}")
            return self._send(502, f"harness proxy: upstream {upstream} failed: {e}\n".encode(),
                              [("Content-Type", "text/plain; charset=utf-8")])
        finally:
            conn.close()
        self.proxy._note(side, self.command, path, status, t0)
        self.send_response(status, reason)
        for k, v in out:
            self.send_header(k, v)
        self.send_header("Content-Security-Policy-Report-Only", CSP_POLICY.format(tag=self.proxy.tag()))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD" and data:
            self.wfile.write(data)

    def _csp_report(self, path):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.proxy._note_csp(urllib.parse.unquote(path[len(CSP_PATH):]), body)
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _handle(self):
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path.startswith(CSP_PATH):
                return self._csp_report(path)
            if path.startswith(HARNESS_PREFIX):
                return self._harness_file(path)
            return self._forward()
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _handle


class _Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # A browser that drops a kept-alive connection (an iframe removed mid-request, a session
        # quitting) is not an error of the run; anything else is still printed.
        import sys
        if isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


class Proxy:
    """One per browser session. upstreams: {"a": base URL, "b": base URL} (either may be absent)."""

    def __init__(self, upstreams=None, timeout=60):
        self.upstreams = dict(upstreams or {})
        self.timeout = timeout
        self._lock = threading.Lock()
        self._side = None
        self._tag = "none"
        self._seq = 0
        self._log = []
        self._harness_404 = []
        self._csp = {}  # tag -> reports not taken yet
        self._taken = set()  # tags whose reports a cell took (later ones are late)
        handler = partial(_Handler, proxy=self)
        self.httpd = _Server(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True, name=f"proxy-{self.port}")
        self.thread.start()

    def use(self, side, tag=None):
        """Select the side every following request goes to, and start a new request log. tag names
        the load in the CSP reports of the documents served from now on (default: the side)."""
        if side is not None and side not in self.upstreams:
            raise KeyError(f"no upstream for side {side!r}")
        with self._lock:
            self._side = side
            self._tag = tag or (side or "none")
            self._log = []

    def new_tag(self, side):
        """A tag no earlier load of this proxy had."""
        with self._lock:
            self._seq += 1
            return f"{self._seq}{side}"

    def tag(self):
        with self._lock:
            return self._tag

    def _note_csp(self, tag, body):
        try:
            data = json.loads(body.decode("utf-8", "replace") or "null")
        except ValueError:
            data = None
        reps = data if isinstance(data, list) else [data]  # report-uri: one object; the Reporting API: a list
        with self._lock:
            lst = self._csp.setdefault(tag, [])
            for rep in reps:
                if not isinstance(rep, dict):
                    continue
                r = rep.get("csp-report") or rep.get("body") or rep
                if isinstance(r, dict) and len(lst) < CSP_MAX_REPORTS:
                    lst.append({"blocked": r.get("blocked-uri") or r.get("blockedURL"),
                                "document": r.get("document-uri") or r.get("documentURL"),
                                "directive": r.get("effective-directive") or r.get("effectiveDirective")
                                or r.get("violated-directive"),
                                "source": r.get("source-file") or r.get("sourceFile")})

    def take_reports(self, tag):
        """The CSP reports of a tag so far; any that arrive later are late_reports()."""
        with self._lock:
            self._taken.add(tag)
            return self._csp.pop(tag, [])

    def late_reports(self):
        """{tag: reports} that arrived after their tag was taken."""
        with self._lock:
            out = {t: self._csp.pop(t) for t in list(self._csp) if t in self._taken}
        return out

    def current(self):
        with self._lock:
            return self._side, self.upstreams.get(self._side)

    def take_log(self):
        with self._lock:
            out, self._log = self._log, []
        return out

    def document_error(self, final_path):
        """The proxy's own error for the last GET of the document (an upstream that refused or timed
        out), without consuming the log; None when the server answered."""
        with self._lock:
            for rec in reversed(self._log):
                if rec["method"] == "GET" and rec["path"] == final_path:
                    return rec.get("error")
        return None

    def take_harness_404(self):
        with self._lock:
            out, self._harness_404 = self._harness_404, []
        return out

    def _note(self, side, method, path, status, t0, error=None):
        rec = {"side": side, "method": method, "path": path, "status": status, "ms": round((time.time() - t0) * 1000)}
        if error:
            rec["error"] = error
        with self._lock:
            if side == self._side:
                self._log.append(rec)

    def _note_harness_404(self, path):
        with self._lock:
            self._harness_404.append(path)

    def rewrite_location(self, value, upstream):
        """An absolute Location on the upstream's origin becomes the same path on the proxy."""
        for origin in {upstream.rstrip("/"), upstream.rstrip("/").replace("127.0.0.1", "localhost")}:
            if value.startswith(origin + "/") or value == origin:
                return value[len(origin):] or "/"
        return value

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def document_status(log, final_path):
    """The final document's status: the last GET logged for the iframe's final path."""
    for rec in reversed(log):
        if rec["method"] == "GET" and rec["path"] == final_path:
            return rec["status"]
    return None
