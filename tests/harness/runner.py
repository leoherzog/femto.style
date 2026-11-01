"""Worker pool: one thread per browser session, each holding a machine-wide slot (and the Safari lock),
each with its own proxy (harness.proxy) in front of the run's two servers."""
import collections
import contextlib
import threading
import time
import traceback

from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import HTTPError as Urllib3Error

from . import locks
from .browsers import FRAME_HEIGHT, Session
from .compare import attach_late_reports, run_cell
from .paths import HARNESS_PREFIX
from .proxy import Proxy

PSEUDOS = ["::before", "::after", "::marker", "::placeholder", "::file-selector-button", "::backdrop"]
PROBE = HARNESS_PREFIX + "probe.html"


def start_session(browser, proxy, log):
    """Start a browser on the proxy's host page and read which pseudo-elements it supports."""
    sess = Session(browser, proxy, log)
    try:
        rig = {"browser": browser, "version": sess.version, "driver": sess.driver_version, "launch_s": sess.launch_s,
               "os_scheme": sess.os_scheme, "host": sess.host}
        ld = sess.ajs("load", PROBE, 1300, FRAME_HEIGHT, {})
        if ld.get("errors"):
            rig["probe_errors"] = ld["errors"]
        sess.js("configure", {"entries": [], "masks": []})
        pr = sess.js("probePseudos")
        rig["pseudo_support"] = {p: bool(pr.get(p)) for p in PSEUDOS}
        rig["properties"] = pr.get("props")
        sess.pseudos = [p for p in PSEUDOS if pr.get(p)]
        sess.unsupported_pseudos = [p for p in PSEUDOS if not pr.get(p)]
        sess.js("unload")
        sess.rig = rig
        return sess
    except Exception:
        sess.quit()
        raise


def shot_name(cell):
    route = cell["route"].strip("/").replace("/", "--") or "index"
    return "__".join(str(x) for x in (cell["browser"], route, cell["scheme"], cell["width"])) + ".png"


def queue_order(cells):
    """Each browser's cells in the order its workers take them. Firefox switches prefers-color-scheme
    through a pref, so each media leg is kept together."""
    by = collections.defaultdict(list)
    for c in cells:
        by[c["browser"]].append(c)
    for lst in by.values():
        lst.sort(key=lambda c: (c["media"], c["route"], c["width"], c["scheme"]))
    return by


def chunks(cells, size):
    """Split the run into chunks of at most about `size` cells, each with a contiguous share of every
    browser's queue, so every browser keeps working in every chunk. The servers are restarted
    between chunks (targets.json max_documents)."""
    if not size or len(cells) <= size:
        return [cells]
    # Interleave the browsers' queues by relative position, then cut the sequence into slices: each
    # slice holds every browser's next share of its queue, in queue order.
    keyed = []
    for b, lst in queue_order(cells).items():
        keyed += [((i + 0.5) / len(lst), b, i, c) for i, c in enumerate(lst)]
    keyed.sort(key=lambda t: t[:3])
    seq = [t[3] for t in keyed]
    n = -(-len(seq) // size)
    per = -(-len(seq) // n)
    return [seq[k * per:(k + 1) * per] for k in range(n)]


class Pool:
    def __init__(self, cells, registry, opts, run_dir, sides, log, offset=0, grand_total=None, t0=None):
        self.cells, self.registry, self.opts, self.run_dir, self.sides, self.log = cells, registry, opts, run_dir, sides, log
        self.results, self.rigs, self.errors = [], [], []
        self.lock = threading.Lock()
        self.done = offset          # cells finished before this pool (earlier chunks), for the log
        self.stopping = False
        self.threads = []
        self.total = grand_total or len(cells)
        self.t0 = t0 or time.time()
        self.queues = {b: collections.deque(lst) for b, lst in queue_order(cells).items()}

    def _next(self, browser):
        with self.lock:
            if self.stopping:
                return None
            q = self.queues.get(browser)
            return q.popleft() if q else None

    def stop(self, wait=150):
        """Stop handing out cells, let running cells finish (at most `wait` s), return the results."""
        with self.lock:
            self.stopping = True
        end = time.time() + wait
        for t in self.threads:
            t.join(max(0.1, end - time.time()))
        with self.lock:
            return list(self.results)

    def _record(self, r):
        with self.lock:
            self.results.append(r)
            self.done += 1
            res = r.get("result") or {}
            self.registry.record_hits(res.get("registered", {}))
            n_err = len(r.get("errors", []))
            first_err = (r.get("errors") or [""])[0]
            el = time.time() - self.t0
            nb = ((r.get("sides") or {}).get("b") or {}).get("elements")
            self.log(f"[{self.done}/{self.total} {el:6.0f}s] {r['browser']:7} {r['route']} {r['scheme']} {r['width']}: "
                     f"{res.get('unregisteredTotal', 0)} unregistered, {res.get('total', 0) - res.get('unregisteredTotal', 0)} "
                     f"registered, {n_err} errors, {nb if nb is not None else '-'} elements, {r.get('timing', {}).get('total', 0)}s"
                     + (f" [{r['status']}]" if r.get("status") not in ("ok", None) else "")
                     + (f" [side {', '.join(x['side'] for x in r['ready_retries'])} reloaded after a readiness failure]"
                        if r.get("ready_retries") else "")
                     + (f" | {first_err[:300]}" if first_err else ""))

    def _worker(self, browser, n):
        label = f"{self.opts.run_id} {browser}#{n}"
        try:
            with locks.slot(label, self.log):
                guard = locks.safari(label, self.log) if browser == "safari" else contextlib.nullcontext()
                with guard:
                    self._session_loop(browser, label)
        except Exception as e:
            with self.lock:
                self.errors.append(f"{label}: worker failed: {e}\n{traceback.format_exc()}")
            self.log(f"{label}: worker failed: {e}")

    def _session_loop(self, browser, label):
        proxy = Proxy({"a": self.sides["a"].base, "b": self.sides["b"].base})
        sess = None
        restarts = 0
        try:
            while True:
                cell = self._next(browser)
                if cell is None:
                    break
                if sess is None:
                    # A loaded machine can time out a session start; retry twice before failing.
                    for attempt in range(3):
                        try:
                            sess = start_session(browser, proxy, self.log)
                            break
                        except WebDriverException as e:
                            if attempt == 2:
                                raise
                            self.log(f"{label}: session start failed ({str(e).splitlines()[0][:200]}); retrying")
                            time.sleep(10)
                    with self.lock:
                        self.rigs.append(sess.rig)
                    self.log(f"{label}: {browser} {sess.version} ({sess.driver_version}), launch {sess.launch_s}s, "
                             f"OS scheme {sess.os_scheme}, pseudo-elements {sess.pseudos}, proxy {proxy.base}")
                shot = self.run_dir / "shots" / shot_name(cell) if self.opts.shots else None
                try:
                    r = run_cell(sess, cell, self.registry, self.opts, self.sides, shot)
                except (WebDriverException, Urllib3Error, TimeoutError, ConnectionError) as e:
                    # The browser stopped answering (a WebDriver error, or no reply within the
                    # session's client timeout): record the cell, end the session, start a new one.
                    r = dict(cell, status="error", errors=[f"webdriver: {type(e).__name__}: "
                                                           f"{str(e).splitlines()[0] if str(e) else repr(e)}"],
                             skipped=[], result=None, timing={})
                    sess.quit(force=not isinstance(e, WebDriverException))
                    sess = None
                    restarts += 1
                    if restarts > 5:
                        self._record(r)
                        raise RuntimeError("too many session restarts")
                except Exception as e:
                    r = dict(cell, status="error", errors=[f"harness exception: {e!r}: {traceback.format_exc(limit=4)}"],
                             skipped=[], result=None, timing={})
                for p in proxy.take_harness_404():
                    r.setdefault("errors", []).append(f"harness file 404: {p}")
                self._record(r)
        finally:
            # CSP reports still on their way belong to the session's last cells (compare.py).
            time.sleep(0.3)
            attach_late_reports(proxy)
            if sess is not None:
                sess.quit()
            attach_late_reports(proxy)
            proxy.close()

    def run(self):
        threads = self.threads
        for browser, n in self.opts.workers.items():
            if browser not in self.queues:
                continue
            for i in range(max(1, min(n, len(self.queues[browser])))):
                if browser == "safari" and i > 0:
                    break
                t = threading.Thread(target=self._worker, args=(browser, i), name=f"{browser}-{i}", daemon=True)
                threads.append(t)
                t.start()
        for t in threads:
            t.join()
        left = sum(len(q) for q in self.queues.values())
        if left:
            self.errors.append(f"{left} cells never ran (workers failed)")
        return self.results
