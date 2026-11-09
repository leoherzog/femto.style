"""`run.py rig`: start each browser and verify every mechanism the behavior and a11y modes rely on.

The rig needs no build: it serves its own probes (probe.html, probe-loads.html) from two small
servers on 127.0.0.1, the second one another origin, and drives them through the behavior mode's
own session and page (harness.behavior.Session and Page), as a check would:

* viewport: each of WIDTHS gives exactly that innerWidth and innerHeight, which matchMedia agrees with;
* color scheme and motion: light and dark, each with no-preference and reduce, emulated (Safari: the
  OS's, read), seen by matchMedia and by a light-dark() color;
* scripts: the page's inline script runs, and (not Safari) a preload script runs before it;
* input: a real pointer hovers and presses (:hover, :active), a real Tab reaches :focus-visible, and
  the document has focus;
* a viewport screenshot;
* JavaScript off (not Safari): the page's script does not run;
* the cache (not Safari): probe.css, cacheable, loads from the cache warm and from the server once
  the cache is emptied;
* a held response (not Safari): probe.css held 0.6 s takes at least 0.5 s;
* criterion 15's loads: of probe-loads.html's four loads from the other origin, the pages' own
  performance entries (behavior.LOADS) must list the image in the page, and the browser's request
  log (not Safari: Page.start_netlog) must list the image and the failed load. What else each way
  sees, the image in a closed shadow root's frame and the worker's fetch, is recorded under
  loads.seen; one the request log misses is listed under limits, which does not fail the rig.

Writes results/<run>/rig.json; exits 1 when a mechanism fails.
"""
import contextlib
import http.server
import json
import socket
import threading
import time
import urllib.parse
from types import SimpleNamespace

from . import locks
from .browsers import screen_front_app
from .paths import HARNESS, RESULTS

WIDTHS = (375, 600, 800, 1100, 1300, 1600)
HEIGHT = 812
PROBE = "/__rig/probe.html"
PROBE_LOADS = "/__rig/probe-loads.html"
PIXEL = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
HELD = 0.6


def add_parser(sub):
    p = sub.add_parser("rig", help="verify the browser mechanisms the behavior and a11y modes rely on")
    p.add_argument("--browsers", default="chrome,firefox,safari", help="comma list of chrome, firefox, safari")
    p.add_argument("--run-id", help="name of the results folder (default: timestamp-rig)")
    return p


class _Probes:
    """Two servers on 127.0.0.1: `base` serves the probes, `other` (another port, so another origin)
    the loads probe's cross-origin files. probe.css may be cached for an hour; everything else is
    no-store."""

    def __init__(self):
        self.servers = []
        # A port nothing listens on, for the load that fails before any response (a port Fetch
        # blocks, such as 1, is refused before any request, and Firefox logs no request for it).
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.refused = f"http://127.0.0.1:{sock.getsockname()[1]}"
        self.base = self._start(self._files)
        self.other = self._start(lambda path: ({"/__rig/pixel.svg": (PIXEL, "image/svg+xml")}.get(path), True))

    def _files(self, path):
        text = {"/favicon.svg": (PIXEL, "image/svg+xml"),
                "/__rig/pixel.svg": (PIXEL, "image/svg+xml"),
                "/__rig/probe.css": ("body { margin: 0; }\n", "text/css; charset=utf-8"),
                "/__rig/worker.js": (f'fetch("{self.other}/__rig/pixel.svg?worker", {{mode: "no-cors"}})'
                                     '.then((r) => postMessage("fetched"), (e) => postMessage(String(e)));\n',
                                     "text/javascript; charset=utf-8")}
        for name, page in (("probe.html", PROBE), ("probe-loads.html", PROBE_LOADS)):
            text[page] = ((HARNESS / name).read_text().replace("{other}", self.other).replace("{refused}", self.refused),
                          "text/html; charset=utf-8")
        return text.get(path), path != "/__rig/probe.css"

    def _start(self, files):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                found, no_store = files(urllib.parse.urlsplit(self.path).path)
                body, ctype = (found[0].encode(), found[1]) if found else (b"not found\n", "text/plain; charset=utf-8")
                self.send_response(200 if found else 404)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store" if no_store else "max-age=3600")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    def close(self):
        for srv in self.servers:
            srv.shutdown()
            srv.server_close()


CENTER = "const r = document.getElementById(arguments[0]).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2];"
COLOR = "return getComputedStyle(document.getElementById(arguments[0])).color;"
PROBE_CSS = """return performance.getEntriesByType("resource").filter(e => e.name.endsWith("/__rig/probe.css"))
  .map(e => ({transferSize: e.transferSize ?? null, duration: Math.round(e.duration)}))[0] ?? null;"""


def _load(page, path, javascript=True):
    page.check = SimpleNamespace(javascript=javascript)
    page.load(path)


def _widths(page):
    out = {}
    for w in WIDTHS:
        page.resize(w, HEIGHT)
        r = page.js("return {inner: [innerWidth, innerHeight], mq: matchMedia(`(width: ${arguments[0]}px) and "
                    "(height: ${arguments[1]}px)`).matches, client: document.documentElement.clientWidth}", w, HEIGHT)
        r["ok"] = r["inner"] == [w, HEIGHT] and r["mq"]
        out[w] = r
    return out


def _media(page, sess):
    out = {}
    pairs = [(m, mo) for m in ("light", "dark") for mo in ("no-preference", "reduce")]
    if page.browser == "safari":
        pairs = [(sess.os_scheme, sess.os_motion)]
    for media, motion in pairs:
        sess.set_media(media, motion)
        page.ajs("await new Promise(r => requestAnimationFrame(() => r())); return true;")
        r = page.js("return {dark: matchMedia('(prefers-color-scheme: dark)').matches,"
                    " reduce: matchMedia('(prefers-reduced-motion: reduce)').matches}")
        r["color"] = page.js(COLOR, "cs")
        r["ok"] = (r["dark"] == (media == "dark") and r["reduce"] == (motion == "reduce")
                   and r["color"] == ("rgb(0, 0, 2)" if media == "dark" else "rgb(0, 0, 1)"))
        out[f"{media} {motion}"] = r
    return out


def _input(page):
    from selenium.webdriver.common.actions.action_builder import ActionBuilder
    out = {"hasFocus": page.js("return document.hasFocus()")}
    x, y = page.js(CENTER, "hv")
    page.click_at(4, 4)   # away from the buttons first
    ab = ActionBuilder(page.driver, duration=0)
    ab.pointer_action.move_to_location(int(x), int(y))
    ab.perform()
    page.sleep(0.1)
    out["hover"] = page.js(COLOR, "hv") == "rgb(255, 0, 0)"
    x, y = page.js(CENTER, "ac")
    ab = ActionBuilder(page.driver, duration=0)
    ab.pointer_action.move_to_location(int(x), int(y)).pointer_down()
    ab.perform()
    try:
        page.sleep(0.1)
        out["active"] = page.js(COLOR, "ac") == "rgb(0, 255, 0)"
    finally:
        ab = ActionBuilder(page.driver, duration=0)
        ab.pointer_action.pointer_up()
        ab.perform()
    page.focus("#ac")   # the focusable element just before #fv
    page.tab()
    page.sleep(0.1)
    out["focus-visible"] = page.js(COLOR, "fv") == "rgb(0, 0, 255)"
    out["ok"] = all(out[k] for k in ("hasFocus", "hover", "active", "focus-visible"))
    return out


def _loads(page):
    """probe-loads.html's four cross-origin loads, as the pages' entries and the request log see them."""
    from behavior import LOADS
    page.start_netlog()
    _load(page, PROBE_LOADS)
    worker = page.ajs("return await Promise.race([window.__rigWorker, new Promise(r => setTimeout(() => r('timeout'), 5000))]);")
    page.sleep(1)
    entries = [e["url"] for e in page.js(LOADS)["entries"]]
    log = page.requests()
    page.cleanup()
    marks = ("img", "fail", "closed", "worker")
    seen = {"entries": {m: any(u.endswith(f"?{m}") for u in entries) for m in marks}}
    if log is not None:
        seen["requests"] = {m: any((x["url"] or "").endswith(f"?{m}") for x in log) for m in marks}
    need = seen["entries"]["img"] and (log is None or (seen["requests"]["img"] and seen["requests"]["fail"]))
    limits = [f"the request log misses the {m} load" for m in ("closed", "worker")
              if log is not None and not seen["requests"][m]]
    return {"worker": worker, "seen": seen, "limits": limits, "ok": bool(need),
            "requests": len(log) if log is not None else None}


def check_browser(browser, log):
    from .behavior import Page, Session
    out = {"screen_front_app": screen_front_app()}
    probes = _Probes()
    sess = None
    try:
        sess = Session(browser, log)
        out["session"] = sess.describe()
        page = Page(sess, probes.base, "static", scoped=False)
        if browser == "safari":
            out["session"]["os_scheme"], out["session"]["os_motion"] = sess.read_os_media(probes.base)
        _load(page, PROBE)
        out["widths"] = _widths(page)
        out["media"] = _media(page, sess)
        page.resize(1300, HEIGHT)
        r = page.js("return window.__rigScript ?? null")
        out["scripts"] = {"ran": bool(r and r["ran"]), "ok": bool(r and r["ran"])}
        out["input"] = _input(page)
        png = page.driver.get_screenshot_as_png()
        out["screenshot"] = {"bytes": len(png), "ok": png[:8] == b"\x89PNG\r\n\x1a\n"}
        if browser != "safari":
            sess.add_preload("() => { window.__rigPreload = true; }")
            _load(page, PROBE)
            r = page.js("return window.__rigScript ?? null")
            out["preload"] = {"afterPreload": bool(r and r["afterPreload"]), "ok": bool(r and r["afterPreload"])}
            sess.remove_preloads()
            _load(page, PROBE)
            warm = page.js(PROBE_CSS)
            page.clear_cache()
            _load(page, PROBE)
            cold = page.js(PROBE_CSS)
            out["cache"] = {"warm": warm, "cold": cold,
                            "ok": bool(warm and cold and warm["transferSize"] == 0 and cold["transferSize"] > 0)}
            page.clear_cache()
            page.delay_responses({"/__rig/probe.css": HELD})
            _load(page, PROBE)
            held = page.js(PROBE_CSS)
            page.cleanup()
            page.delayed = False
            out["held"] = {"entry": held, "ok": bool(held and held["duration"] >= (HELD - 0.1) * 1000)}
            page.disable_javascript()
            _load(page, PROBE, javascript=False)
            r = page.js("return window.__rigScript ?? null")
            page.cleanup()
            out["javascript_off"] = {"ran": r is not None, "ok": r is None}
            # A fresh tab: Chrome's CDP setting belongs to the tab that had JavaScript off.
            d = page.driver
            handles = d.window_handles
            d.switch_to.new_window("tab")
            fresh = d.current_window_handle
            for h in handles:
                d.switch_to.window(h)
                d.close()
            d.switch_to.window(fresh)
            sess.tab_opened()
        out["loads"] = _loads(page)
    finally:
        if sess is not None:
            sess.quit()
        probes.close()
    out["ok"] = all(v.get("ok", True) for v in out.values() if isinstance(v, dict) and "ok" in v) \
        and all(v["ok"] for v in out.get("widths", {}).values()) and all(v["ok"] for v in out.get("media", {}).values())
    return out


def run_rig(args):
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-rig"
    report = {}
    log = lambda m: print(f"{time.strftime('%H:%M:%S')} {m}", flush=True)
    status = 0
    for b in [x.strip() for x in args.browsers.split(",") if x.strip()]:
        try:
            with locks.slot(f"{run_id} rig {b}", log):
                guard = locks.safari(f"{run_id} rig", log) if b == "safari" else contextlib.nullcontext()
                with guard:
                    report[b] = check_browser(b, log)
            if not report[b]["ok"]:
                status = 1
        except Exception as e:
            report[b] = {"error": repr(e), "ok": False}
            status = 1
        print(f"{b}: {json.dumps(report[b], indent=1)}", flush=True)
    for b, r in report.items():
        for limit in (r.get("loads") or {}).get("limits", []):
            print(f"limit: {b}: {limit}", flush=True)
    d = RESULTS / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "rig.json").write_text(json.dumps(report, indent=1))
    print(f"{'PASS' if status == 0 else 'FAIL'}: rig {', '.join(report)}; wrote {d}/rig.json")
    return status
