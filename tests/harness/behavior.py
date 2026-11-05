"""The behavior mode: scripted checks of every widget against one target (tests/behavior/).

    uv run tests/run.py behavior --target <oracle | dist | dist:<path> | base URL>
                                 [--groups g,..] [--checks name,..] [--browsers chrome,firefox]

Unlike the pages mode, a check drives a top-level document (no host page, no iframe, no proxy): the
URL, history, focus, storage events between tabs and window resizes are the browser's own. Each
browser runs headless, which keeps timers and animation frames at full rate (hidden or background
tabs throttle them to about once a second; docs/research/05-spike.md), and holds one of the
machine-wide harness slots for its whole life (harness.locks), with WebDriver start-up serialized.

For every check and route the page is reset first: a fresh tab (its own history and sessionStorage)
with every other tab closed, the viewport set to the check's innerWidth and innerHeight (WebDriver
BiDi browsingContext.setViewport), prefers-color-scheme emulated (CDP in Chrome, the content pref in
Firefox, as in harness.browsers), storage on the target's origin emptied (from a same-origin static
file, /favicon.svg) and the check's items stored, then the route loaded and its readiness hook run
(oracle: harness.oracle.wait_ready; static: load, fonts and two frames).

Safari (--browsers safari) runs under femto's Safari rules, as the other modes do (tests/README.md,
Rig notes, Safari): one session at a time machine-wide (the Safari lock, held for the session's
life), never while the user's own Safari is open, and only on an unlocked screen, since input never
reaches a hidden page. It is visible, not headless; it has no prefers-color-scheme emulation, so a
check whose media is not the OS scheme is skipped (status skip, `media:<scheme>`) and runs in the
owner's pass of the other appearance; it has no WebDriver BiDi, so the viewport is sized through the
window and a check that needs a preload script is skipped there (`preload`), as is one that says
what else Safari's WebDriver cannot do (safari_skip: `safari`). Its Tab is Option+Tab (Page.tab).

The target has one of two layouts (--layout; the target's by default). On `one-page` (the static
site from Phase 3: targets.json one_page) the docs are the one page /docs, and a check's routes are
written in its URLs: /docs#<id>, /docs (Quick start), /docs?theme=<color>#theme-picker. On `routes`
(the oracle, static-femto, static-multipage: one page per docs route) each such URL is loaded at its
old route instead, through static-femto's menu.json (the map PLAN.md's sections comparison uses):
/docs#modal at /docs/modal, /docs?theme=jade#theme-picker at /docs/version-picker/jade (Phase 4's
Theme picker is the old version picker's section, SECTION_ALIASES). Every
script a check runs sees `S`, the element its route's content lives in: on the one page the
route's section, document.getElementById(id).closest("section"); on routes the whole document
(document.documentElement). A check that can run on one layout only says why, and is recorded as
skip there with that reason.

Results go to tests/results/<run-id>/ like every other mode: result.json, summary.txt, log.txt, and
for a failed check a screenshot of the viewport under shots/.
"""
import contextlib
import importlib.util
import json
import os
import sys
import threading
import time
import traceback
import urllib.parse

from .paths import REPO, RESULTS, TESTS

BEHAVIOR_DIR = TESTS / "behavior"
BROWSERS = ("chrome", "firefox", "safari")
LAYOUTS = ("one-page", "routes")
STATUSES = ("pass", "xfail", "fail", "xpass", "error", "skip")
SCRIPT_TIMEOUT = 180     # the longest in-page wait is a few seconds; generous for a loaded machine
FF_SCHEME_PREF = "layout.css.prefers-color-scheme.content-override"
FF_SCHEME_VALUES = {"dark": 0, "light": 1}
FF_MOTION_PREF = "ui.prefersReducedMotion"   # a LookAndFeel int: 1 reduce, 0 no-preference
FF_JS_PREF = "javascript.enabled"
RESET_PATH = "/favicon.svg"   # a static same-origin file on every side: storage is emptied from it
ONE_PAGE = "/docs"            # the one docs page (PLAN.md Decision 2)
FIRST_SECTION = "quick-start"  # the section at the top of /docs, which has no hash
ROUTES_MENU = ("static-femto", "site/docs/menu.json")   # the old routes' menu: tag and path in it
# Phase 4's section ids whose section an old route showed under another id: the Theme picker is the
# version picker reworked (PLAN.md Open questions 3), so /docs?theme=jade#theme-picker is the old
# /docs/version-picker/jade on the routes layout.
SECTION_ALIASES = {"theme-picker": "version-picker"}


def route_parts(route):
    """(section id, theme color) of a check route on the one docs page, or None for another page:
    /docs#input is ("input", None), /docs is ("quick-start", None), /docs?theme=jade#theme-picker is
    ("theme-picker", "jade")."""
    u = urllib.parse.urlsplit(route)
    if u.path != ONE_PAGE:
        return None
    theme = urllib.parse.parse_qs(u.query).get("theme", [None])[0]
    return (u.fragment or FIRST_SECTION, theme)


def old_routes():
    """{(section id, theme color or None): old route} from static-femto's menu.json, read from the tag
    (harness.sections.route_map): the oracle's kept docs routes, which the routes layout loads."""
    import types
    from .sections import route_map
    tag, path = ROUTES_MENU
    routes, _ = route_map(types.SimpleNamespace(spec=tag, conf={"menu": path, "build_tag": tag}))
    return {v: k for k, v in routes.items()}


def to_old_route(route, table):
    """The old route that showed what a one-page check route shows, or None when none did (another
    query, a theme on a section other than the picker's)."""
    parts = route_parts(route)
    if parts is None:
        return route
    u = urllib.parse.urlsplit(route)
    if set(urllib.parse.parse_qs(u.query)) - {"theme"}:
        return None
    return table.get((SECTION_ALIASES.get(parts[0], parts[0]), parts[1]))


def csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else []


# -- command line --------------------------------------------------------------------------------

def add_parser(sub):
    p = sub.add_parser("behavior", help="scripted checks of every widget against one target (tests/behavior/)")
    p.add_argument("--target", help="oracle, dist, dist:<path> (wrangler pages dev <path>) or a base URL")
    p.add_argument("--groups", help="comma list of groups (default: all): " + ", ".join(_groups()))
    p.add_argument("--checks", help="comma list of check names (default: all in the groups)")
    p.add_argument("--browsers", default="chrome,firefox",
                   help="comma list of chrome, firefox, safari (default chrome,firefox; Safari serialized, the OS "
                        "scheme only, on an unlocked screen)")
    p.add_argument("--ready", help="readiness hook (oracle, static, none; default: the target's)")
    p.add_argument("--layout", choices=LAYOUTS,
                   help="one-page (the docs are /docs; a target with targets.json one_page, and a base URL) or routes "
                        "(one page per old docs route: the oracle and the other named targets, and a base URL with "
                        "--expect-oracle-bugs); default: the target's")
    p.add_argument("--expect-oracle-bugs", action="store_true",
                   help="treat the target as the oracle for oracle_bug checks (for a base URL serving it); "
                        "the named target oracle always does")
    p.add_argument("--workers", help="sessions per browser, e.g. chrome=2,firefox=2 (default 1 each)")
    p.add_argument("--run-id", help="name of the results folder (default: timestamp-behavior-pid)")
    p.add_argument("--label", help="free text stored in result.json")
    p.add_argument("--list", action="store_true", help="list the selected checks and exit; starts nothing")
    p.add_argument("--no-shots", action="store_true", help="no screenshot of a failed check")
    return p


def _groups():
    from behavior import GROUPS  # noqa: E402  (tests/ is on sys.path; see tests/run.py)
    return GROUPS


def load_checks():
    """Import every group module in tests/behavior/ (file names may hold hyphens) and return the
    registry in group order."""
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    import behavior
    if not behavior.REGISTRY:
        for group in behavior.GROUPS:
            path = BEHAVIOR_DIR / f"{group}.py"
            if not path.exists():
                continue
            spec = importlib.util.spec_from_file_location(f"behavior.{group.replace('-', '_')}", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
    order = {g: i for i, g in enumerate(behavior.GROUPS)}
    return sorted(behavior.REGISTRY, key=lambda c: order[c.group])


def select(checks, groups, names):
    known_groups = {c.group for c in checks}
    for g in groups:
        if g not in known_groups:
            raise SystemExit(f"unknown group {g} (groups: {', '.join(sorted(known_groups))})")
    known = {c.name for c in checks}
    for n in names:
        if n not in known:
            raise SystemExit(f"unknown check {n}")
    out = [c for c in checks if (not groups or c.group in groups) and (not names or c.name in names)]
    if not out:
        raise SystemExit("no checks selected")
    return out


# -- the page a check drives ---------------------------------------------------------------------

class Url(str):
    """A URL as page.url() read it, with the tab's history.length at that moment, so url_kept can
    assert that no history entry was added."""

    def __new__(cls, url, history):
        s = super().__new__(cls, url)
        s.history = history
        return s


class CheckFailed(Exception):
    def __init__(self, label, detail):
        super().__init__(label)
        self.label, self.detail = label, detail


class Page:
    """One browser session's top-level tab, as a check sees it."""

    def __init__(self, sess, base, ready, layout=None, routes=None):
        self.sess, self.driver, self.browser = sess, sess.driver, sess.browser
        self.base, self.ready_hook = base, ready
        self.layout = layout      # one-page, routes, or None (no check: harness.a11y loads plain pages)
        self.old_routes = routes  # the routes layout's {(section, theme): old route}
        self.assertions = []
        self.notes = []
        self.cleanups = []
        self.loads = 0
        self.check = None
        self.route = None         # the check's route, in the one page's URLs
        self.section = None       # its section id on the one page (None off the docs)
        self.theme = None         # its ?theme= color
        self.scope = None         # the JavaScript expression every check script sees as S
        self.delayed = False      # the check holds some responses (delay_responses)

    def address(self, route):
        """Where a check route is loaded on this target: itself on the one page, its old route on
        routes (a route no old route showed is a harness error: such a check runs on the one page
        only, and says so)."""
        if self.layout != "routes":
            return route
        old = to_old_route(route, self.old_routes)
        if old is None:
            raise RuntimeError(f"no old route shows {route}: a check on it runs on the one page only (layouts)")
        return old

    def _set_route(self, route):
        self.route = route
        parts = route_parts(route) if self.layout else None
        self.section, self.theme = parts if parts else (None, None)
        if self.layout == "one-page" and self.section:
            self.scope = f"document.getElementById({json.dumps(self.section)})?.closest('section') ?? null"
        elif self.layout:
            self.scope = "document.documentElement"
        else:
            self.scope = None

    def _scoped(self, body):
        return body if self.scope is None else f"const S = {self.scope};\n{body}"

    def cleanup(self):
        """Undo what the check changed beyond the document (prefs); run after every check."""
        while self.cleanups:
            fn = self.cleanups.pop()
            try:
                fn()
            except Exception:
                pass

    def with_classic_scrollbars(self):
        """Reload the route with a classic, space-taking scrollbar (headless browsers on macOS draw
        overlay scrollbars of width 0): in Chrome a ::-webkit-scrollbar sheet adopted by every new
        document before its scripts run, in Firefox the pref ui.useOverlayScrollbars 0 (undone after
        the check). The page's own markup and styles are untouched."""
        if self.browser == "firefox":
            d = self.driver
            with d.context(d.CONTEXT_CHROME):
                d.execute_script("Services.prefs.setIntPref('ui.useOverlayScrollbars', 0)")

            def undo():
                with d.context(d.CONTEXT_CHROME):
                    d.execute_script("Services.prefs.clearUserPref('ui.useOverlayScrollbars')")
            self.cleanups.append(undo)
        else:
            self.sess.add_preload("""() => { const s = new CSSStyleSheet();
              s.replaceSync("::-webkit-scrollbar { width: 15px; height: 15px; background: #ddd } ::-webkit-scrollbar-thumb { background: #888 }");
              document.adoptedStyleSheets = [...document.adoptedStyleSheets, s]; }""")
        self.load(self.route)

    # -- scripts -----------------------------------------------------------------------------
    def js(self, body, *args):
        """Run a function body in the current document and return its value. It sees S, the check
        route's content element (the module docstring)."""
        return self.driver.execute_script(self._scoped(body), *args)

    def ajs(self, body, *args):
        """Run an async function body (`done` is its callback) and return what it passes to done()."""
        script = ("const done = arguments[arguments.length - 1];"
                  "(async () => {" + self._scoped(body) + "})().then(done, e => done({__error: String(e && e.stack || e)}));")
        out = self.driver.execute_async_script(script, *args)
        if isinstance(out, dict) and "__error" in out:
            raise RuntimeError(f"in-page exception: {out['__error']}")
        return out

    def url(self):
        """The current URL (path, query and hash), carrying history.length at the time (Url)."""
        r = self.js("return [location.pathname + location.search + location.hash, history.length]")
        return Url(r[0], r[1])

    def url_kept(self, label, before, /, **detail):
        """Assert that nothing navigated since the URL was `before`, a page.url(): no new history
        entry, and the same URL. On the one page the spy writes the hash of the section being read
        whenever a check scrolls (replaceState, no history entry), so there the path and query must be
        the same and the hash either the same or a section's id (or none, the spy's plain /docs at the
        top); elsewhere the URL must be exactly the same."""
        now = self.js("""const u = new URL(arguments[0], location.href);
          const ids = [...document.querySelectorAll("#content > section > hgroup > h1[id]")].map(h => "#" + h.id);
          return {url: location.pathname + location.search + location.hash, history: history.length,
                  spy: location.pathname + location.search === u.pathname + u.search
                      && (location.hash === u.hash || location.hash === "" || ids.includes(location.hash))};""", before)
        ok = now["spy"] if self.layout == "one-page" else now["url"] == before
        history = getattr(before, "history", None)
        if history is None:
            raise RuntimeError(f"{label}: url_kept takes a page.url(), which carries history.length")
        return self.expect(label, ok and now["history"] == history, url=now["url"], before=str(before),
                           history=now["history"], history_before=history, **detail)

    def find(self, css):
        """The first element in S (the check route's content) that matches the CSS selector, or None."""
        return self.js("return S.querySelector(arguments[0])", css)

    def find_all(self, css):
        return self.js("return [...S.querySelectorAll(arguments[0])]", css)

    # -- assertions --------------------------------------------------------------------------
    def expect(self, label, ok, /, **detail):
        rec = {"label": label, "ok": bool(ok)}
        if detail:
            rec["detail"] = _jsonable(detail)
        self.assertions.append(rec)
        if not ok:
            raise CheckFailed(label, rec.get("detail"))
        return ok

    def eq(self, label, actual, expected, /, **detail):
        return self.expect(label, actual == expected, actual=actual, expected=expected, **detail)

    def wait(self, label, expr, timeout=2.0, /, args=(), interval=0.05, **detail):
        """Poll the JavaScript expression `expr` (arguments[0..] are `args`) until it is truthy;
        record the assertion and return the value. Fails after `timeout` seconds."""
        deadline = time.time() + timeout
        t0 = time.time()
        value, err = None, None
        while True:
            try:
                value = self.driver.execute_script(self._scoped(f"return ({expr});"), *args)
                err = None
            except Exception as e:  # a navigation in flight replaces the document
                value, err = None, f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"
            if value:
                self.expect(label, True, after_s=round(time.time() - t0, 3), **detail)
                return value
            if time.time() > deadline:
                self.expect(label, False, waited_s=timeout, last=value, error=err, expr=expr, **detail)
            time.sleep(interval)

    def holds(self, label, expr, duration, /, args=(), interval=0.05, **detail):
        """Assert that `expr` stays truthy for `duration` seconds."""
        end = time.time() + duration
        while time.time() < end:
            value = self.driver.execute_script(self._scoped(f"return ({expr});"), *args)
            if not value:
                self.expect(label, False, last=value, expr=expr, **detail)
            time.sleep(interval)
        return self.expect(label, True, held_s=duration, **detail)

    def note(self, text):
        self.notes.append(text)

    @staticmethod
    def sleep(s):
        time.sleep(s)

    # -- loading -----------------------------------------------------------------------------
    def reset(self, check, route):
        """Start the check in a fresh tab (its own history, which browsers cap at 50 entries, and its
        own sessionStorage), every other tab closed; size the viewport, set the color scheme and
        storage, load the route."""
        self.check = check
        self._set_route(route)
        self.assertions, self.notes = [], []
        self.preloaded = False
        self.delayed = False
        d = self.driver
        handles = d.window_handles
        d.switch_to.new_window("tab")
        fresh = d.current_window_handle
        for h in handles:
            d.switch_to.window(h)
            d.close()
        d.switch_to.window(fresh)
        self.sess.tab_opened()
        self.sess.remove_preloads()
        d.get(self.base + RESET_PATH)
        self.loads += 1
        self.resize(check.width, check.height)
        self.sess.set_media(check.media, getattr(check, "motion", None))
        d.execute_script("localStorage.clear(); sessionStorage.clear();"
                         "for (const [k, v] of Object.entries(arguments[0])) localStorage.setItem(k, v);",
                         check.storage or {})
        if check.preload and not (self.browser == "safari" and getattr(check, "preload_optional", False)):
            self.sess.add_preload(check.preload)
            self.preloaded = True
        if getattr(check, "cold", False):
            self.clear_cache()
        if getattr(check, "delay", None):
            self.delay_responses(check.delay)
        if getattr(check, "javascript", True) is False:
            self.disable_javascript()
        self.load(route)
        if self.layout == "one-page" and self.section and getattr(check, "javascript", True) is not False:
            self.expect(f"the page has the #{self.section} section", self.js("return !!S"))

    def clear_cache(self):
        """Empty the browser's HTTP cache, so the next load is a cold one (Chrome: CDP; Firefox: the
        cache service, from its chrome context). Safari has no way to: noted, and the load is warm."""
        if self.browser == "chrome":
            self.driver.execute_cdp_cmd("Network.clearBrowserCache", {})
        elif self.browser == "firefox":
            with self.driver.context(self.driver.CONTEXT_CHROME):
                self.driver.execute_script("Services.cache2.clear()")
        else:
            self.note("Safari's cache cannot be emptied over WebDriver: this load may be warm")

    def delay_responses(self, delays):
        """Hold the target's responses for these exact paths ({path: seconds}) that long, for this
        check's loads: a WebDriver BiDi intercept on each URL, whose request is continued only after
        the wait (the handler runs on Selenium's event thread, one per request). The intercept is
        removed after the check. Safari has no BiDi: noted, and the files load at once."""
        if self.browser == "safari":
            self.note(f"Safari has no WebDriver BiDi: {', '.join(delays)} not delayed")
            return
        net = self.driver.network
        for path, seconds in delays.items():
            handler = net.add_request_handler([self.base + path], lambda request, s=seconds: time.sleep(s))
            self.cleanups.append(lambda h=handler: net.remove_request_handler(h))
        self.delayed = True

    def disable_javascript(self):
        """Turn the page's JavaScript off for this tab's loads (Chrome: CDP, for this tab only; Firefox:
        the javascript.enabled pref, undone after the check). WebDriver's own scripts still run.
        Safari cannot (run_one skips such a check there)."""
        if self.browser == "chrome":
            self.driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled", {"value": True})
        elif self.browser == "firefox":
            d = self.driver
            with d.context(d.CONTEXT_CHROME):
                d.execute_script(f"Services.prefs.setBoolPref('{FF_JS_PREF}', false)")

            def undo():
                with d.context(d.CONTEXT_CHROME):
                    d.execute_script(f"Services.prefs.clearUserPref('{FF_JS_PREF}')")
            self.cleanups.append(undo)
        else:
            raise RuntimeError("WebDriver cannot turn JavaScript off in Safari")

    def load(self, route, fresh=True):
        """Navigate this tab to the route (its old route on the routes layout) and run the readiness
        hook. With `fresh`, a route that differs from the current document's URL only by its hash is
        reached through RESET_PATH, so it is a new document (going to a hash on the same page is a
        fragment navigation in the same document, which runs no preload script and no page script)."""
        url = self.base + self.address(route)
        if fresh:
            try:
                here = self.driver.execute_script("return location.origin + location.pathname + location.search")
            except Exception:
                here = None
            if here == url.split("#", 1)[0]:
                self.driver.get(self.base + RESET_PATH)
                self.loads += 1
        if self.delayed:
            # ChromeDriver runs no BiDi command while a classic one waits for the load, so a classic
            # get would wait for a held file whose continueRequest cannot run: navigate over BiDi.
            self.driver.browsing_context.navigate(context=self.driver.current_window_handle, url=url, wait="complete")
        else:
            self.driver.get(url)
        self.loads += 1
        if getattr(self.check, "javascript", True) is False:
            self.wait("the page has loaded", "document.readyState === 'complete'", 15)
        else:
            self.wait_ready()

    def wait_ready(self, timeout=30):
        if self.ready_hook == "oracle":
            from . import oracle
            # Headless Chrome can stop scheduling idle periods until a frame is produced, and the
            # oracle hydrates from requestIdleCallback (tests/README.md, Rig notes, Chrome: idle
            # periods); request frames until it has.
            self.js("""if (!window.__bhPump) { window.__bhPump = 1; const end = performance.now() + 30000;
                       (function f() { const r = window.__remixRouter;
                         if (performance.now() < end && !(r && r.state && r.state.initialized)) requestAnimationFrame(f); })(); }""")
            oracle.wait_ready(self.driver, timeout=timeout)
        elif self.ready_hook == "static":
            r = self.ajs("""
              const frame = () => new Promise(res => { let f = false; const go = () => { if (!f) { f = true; res(); } };
                requestAnimationFrame(go); setTimeout(go, 100); });
              if (document.readyState !== "complete") await new Promise(res => addEventListener("load", res, {once: true}));
              if (document.fonts) await document.fonts.ready;
              await frame(); await frame();
              return true;""")
            if r is not True:
                raise RuntimeError(f"static readiness: {r}")

    def wait_navigated(self, path, timeout=10, label=None):
        """After a click that navigates (a full load or a client-side route change), wait until
        location.pathname is `path` and the document is loaded and idle, then run the readiness
        hook again."""
        self.wait(label or f"navigated to {path}",
                  "location.pathname === arguments[0] && document.readyState === 'complete' && "
                  "(!window.__remixRouter || window.__remixRouter.state.navigation.state === 'idle')",
                  timeout, args=(path,))
        self.wait_ready()

    # -- window and input --------------------------------------------------------------------
    def resize(self, width, height):
        """Make the document's innerWidth and innerHeight exactly these, with WebDriver BiDi
        browsingContext.setViewport (headless windows are at least 500 px wide in both browsers, so
        a window size cannot give 375). The page sees a real resize: resize events, media queries."""
        d = self.driver
        want = (width, height)
        if self.browser == "safari":
            return self._resize_window(width, height)
        d.browsing_context.set_viewport(context=d.current_window_handle, viewport={"width": width, "height": height})
        deadline = time.time() + 5
        while True:
            inner = tuple(d.execute_script("return [innerWidth, innerHeight]"))
            if inner == want:
                return
            if time.time() > deadline:
                raise RuntimeError(f"cannot size the viewport to {want}: got {inner}")
            time.sleep(0.05)

    def _resize_window(self, width, height):
        """Safari has no WebDriver BiDi: size the window so the document's innerWidth and innerHeight are
        exactly these (the window's frame added once measured), or fail the check (a width under
        Safari's minimum window width cannot be given)."""
        d = self.driver
        inner = None
        for _ in range(4):
            outer = d.get_window_rect()
            inner = tuple(d.execute_script("return [innerWidth, innerHeight]"))
            if inner == (width, height):
                return
            d.set_window_rect(x=0, y=0, width=outer["width"] + width - inner[0], height=outer["height"] + height - inner[1])
            time.sleep(0.2)
        inner = tuple(d.execute_script("return [innerWidth, innerHeight]"))
        if inner != (width, height):
            raise RuntimeError(f"cannot size Safari's window to a {width} x {height} viewport: got {inner} (Safari has "
                               "no WebDriver BiDi setViewport, and its window has a minimum width)")

    def el(self, css):
        from selenium.webdriver.common.by import By
        return self.driver.find_element(By.CSS_SELECTOR, css)

    def els(self, css):
        from selenium.webdriver.common.by import By
        return self.driver.find_elements(By.CSS_SELECTOR, css)

    def click(self, target, at=None, scroll=True):
        """A real pointer click (WebDriver actions: move, press, release) on a CSS selector or
        element: scrolled to the middle of the viewport unless scroll is False (or already fully in
        view), then clicked at its center, or at `at` = (x, y) relative to its top left corner. The
        point must hit the element or a descendant, as a user's click would; anything covering it
        is an error once 1.5 s have passed; an element still moving (sliding in) is waited for. (WebDriver's
        element click misplaces the point under an emulated viewport in Chrome, so it is not used.)"""
        el = self.el(target) if isinstance(target, str) else target
        deadline = time.time() + 1.5
        prev = None
        while True:
            hit = self.driver.execute_script("""
              const [el, at, scroll] = arguments;
              let r = el.getBoundingClientRect();
              const inView = r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth;
              if (scroll && !inView) { el.scrollIntoView({block: "center", inline: "nearest", behavior: "instant"}); r = el.getBoundingClientRect(); }
              const x = Math.round(at ? r.left + at[0] : r.left + r.width / 2), y = Math.round(at ? r.top + at[1] : r.top + r.height / 2);
              const h = x >= 0 && y >= 0 && x < innerWidth && y < innerHeight ? document.elementFromPoint(x, y) : null;
              return {x, y, ok: !!h && (h === el || el.contains(h)), hit: h ? h.outerHTML.slice(0, 120) : null,
                      rect: [r.left, r.top, r.width, r.height]};""",
                                             el, list(at) if at else None, scroll)
            # Click only once the element holds still for two samples: one sliding in (the mobile
            # menu's transform transition) would move between press and release, and no click fires.
            if hit["ok"] and hit["rect"] == prev:
                break
            prev = hit["rect"] if hit["ok"] else None
            if time.time() > deadline:
                raise RuntimeError(f"click target is covered or outside the viewport at ({hit['x']}, {hit['y']}): {hit['hit']}")
            time.sleep(0.05)   # still moving (a transition), or covered for now
        self.click_at(hit["x"], hit["y"])
        return el

    def click_at(self, x, y):
        """A real pointer click at viewport coordinates."""
        from selenium.webdriver.common.actions.action_builder import ActionBuilder
        ab = ActionBuilder(self.driver, duration=0)
        ab.pointer_action.move_to_location(int(x), int(y)).pointer_down().pointer_up()
        ab.perform()

    def key(self, key, times=1, hold=0):
        """Real key presses sent to the focused element. key: a selenium Keys name ("ESCAPE",
        "ENTER", "ARROW_RIGHT") or text. hold: seconds each press stays down before its release (0:
        released at once). "TAB" is self.tab()."""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        if key == "TAB":
            return self.tab(times=times)
        k = getattr(Keys, key, key)
        ac = ActionChains(self.driver, duration=0)
        for _ in range(times):
            if hold:
                ac.key_down(k).pause(hold).key_up(k)
            else:
                ac.send_keys(k)
        ac.perform()

    def tab(self, shift=False, times=1):
        """Real Tab presses (Shift+Tab with shift). Safari's are Option+Tab: under its default setting
        ("Press Tab to highlight each item" off, which the harness never changes) plain Tab skips links
        and buttons, and Option+Tab reaches them (p4-behavior-safari-light-1; harness.browsers' tab()
        does the same)."""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        mods = ([Keys.SHIFT] if shift else []) + ([Keys.ALT] if self.browser == "safari" else [])
        ac = ActionChains(self.driver, duration=0)
        for _ in range(times):
            for m in mods:
                ac.key_down(m)
            ac.send_keys(Keys.TAB)
            for m in reversed(mods):
                ac.key_up(m)
        ac.perform()

    def focus(self, css):
        return self.js("const e = document.querySelector(arguments[0]); e.focus(); return document.activeElement === e;", css)

    def scroll_to(self, y):
        """Scroll the document instantly to `y` and wait until the position holds (Firefox applies
        scrollTo() asynchronously)."""
        return self.ajs("""
          const y = arguments[0];
          const frame = () => new Promise(res => requestAnimationFrame(() => res()));
          let last = -1, same = 0;
          for (let i = 0; i < 120 && same < 2; i++) {
            scrollTo({top: y, left: 0, behavior: "instant"});
            await frame();
            same = scrollY === last ? same + 1 : 0;
            last = scrollY;
          }
          return scrollY;""", y)

    # -- tabs --------------------------------------------------------------------------------
    def new_tab(self, route):
        """Open another tab of the same session at the route, with the check's viewport and color
        scheme; it becomes the current tab."""
        self.driver.switch_to.new_window("tab")
        self.sess.tab_opened()
        self.resize(self.check.width, self.check.height)
        self.sess.set_media(self.check.media, getattr(self.check, "motion", None))
        self.load(route)
        return self.driver.current_window_handle

    def switch(self, handle):
        self.driver.switch_to.window(handle)

    def screenshot(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.driver.get_screenshot_as_png())


def _jsonable(v):
    try:
        json.dumps(v)
        return v
    except TypeError:
        return json.loads(json.dumps(v, default=repr))


# -- browser sessions ----------------------------------------------------------------------------

class Session:
    def __init__(self, browser, log):
        from selenium import webdriver
        from . import browsers, locks
        self.browser, self.log = browser, log
        self.media_applied = None
        self.motion_applied = None
        self.preloads = []
        self.os_scheme = None   # Safari: the OS scheme, read in the page (no emulation)
        t0 = time.time()
        with locks.driver_start(f"behavior {browser} session", log):
            if browser == "chrome":
                o = webdriver.ChromeOptions()
                o.binary_location = browsers.CHROME_BINARY
                for a in ("--headless", "--window-size=1800,1100", "--force-device-scale-factor=1",
                          "--no-first-run", "--no-default-browser-check", "--disable-search-engine-choice-screen",
                          "--force-color-profile=srgb", "--disable-background-timer-throttling",
                          "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"):
                    o.add_argument(a)
                o.enable_bidi = True
                self.driver = webdriver.Chrome(options=o)
            elif browser == "firefox":
                from selenium.webdriver.firefox.service import Service
                o = webdriver.FirefoxOptions()
                o.binary_location = browsers.FIREFOX_BINARY
                for a in ("-headless", "--width=1800", "--height=1100"):
                    o.add_argument(a)
                o.set_preference(FF_SCHEME_PREF, FF_SCHEME_VALUES["light"])
                o.set_preference("layout.css.devPixelsPerPx", "1.0")
                o.set_preference("gfx.font_rendering.fallback.async", False)
                o.enable_bidi = True
                self.driver = webdriver.Firefox(options=o, service=Service(service_args=["--allow-system-access"]))
            elif browser == "safari":
                # Visible and serialized: the caller holds the Safari lock (Runner._worker), and
                # browsers._safari() refuses while the user's own Safari runs and ends any automation
                # instance left over.
                self.driver = browsers._safari()
            else:
                raise ValueError(f"behavior runs in {', '.join(BROWSERS)} (not {browser})")
        self.launch_s = round(time.time() - t0, 2)
        caps = self.driver.capabilities
        self.version = caps.get("browserVersion")
        self.driver_version = ((caps.get("chrome") or {}).get("chromedriverVersion", "").split(" ")[0]
                               or caps.get("moz:geckodriverVersion") or "")
        self.driver.set_script_timeout(SCRIPT_TIMEOUT)
        self.driver.set_page_load_timeout(60)
        try:
            self.driver.command_executor.client_config.timeout = SCRIPT_TIMEOUT + 60
        except AttributeError:
            pass
        self.tab_opened()

    def tab_opened(self):
        """Per-tab set-up for the current tab: Chrome's emulations (focus, color scheme) belong to
        one tab. Focus emulation keeps the document focused (document.hasFocus(), :focus) in
        headless Chrome, as in harness.browsers."""
        self.media_applied = None
        self.motion_applied = None
        if self.browser == "chrome":
            self.driver.execute_cdp_cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})

    def describe(self):
        d = {"browser": self.browser, "version": self.version, "driver": self.driver_version, "launch_s": self.launch_s}
        if self.os_scheme:
            d["os_scheme"] = self.os_scheme
        return d

    def read_os_scheme(self, base):
        """Safari: the OS scheme, read with matchMedia on a same-origin static file of the target."""
        self.driver.get(base + RESET_PATH)
        dark = self.driver.execute_script("return matchMedia('(prefers-color-scheme: dark)').matches")
        self.os_scheme = "dark" if dark else "light"
        return self.os_scheme

    def set_media(self, media, motion=None):
        """Emulate prefers-color-scheme `media` and, when given, prefers-reduced-motion `motion`
        (no-preference or reduce; None keeps the current one)."""
        motion = motion or self.motion_applied or "no-preference"
        if media == self.media_applied and motion == self.motion_applied:
            return
        if self.browser == "safari":
            # No emulation: run_one skips a check whose media or motion Safari cannot give first.
            if media != self.os_scheme:
                raise RuntimeError(f"Safari cannot emulate prefers-color-scheme: {media}; the OS scheme is {self.os_scheme}")
            if motion != "no-preference":
                raise RuntimeError(f"Safari cannot emulate prefers-reduced-motion: {motion}")
        elif self.browser == "chrome":
            self.driver.execute_cdp_cmd("Emulation.setEmulatedMedia",
                                        {"features": [{"name": "prefers-color-scheme", "value": media},
                                                      {"name": "prefers-reduced-motion", "value": motion}]})
        else:
            with self.driver.context(self.driver.CONTEXT_CHROME):
                self.driver.execute_script(f"Services.prefs.setIntPref('{FF_SCHEME_PREF}', {FF_SCHEME_VALUES[media]})")
                if motion == "reduce":
                    self.driver.execute_script(f"Services.prefs.setIntPref('{FF_MOTION_PREF}', 1)")
                else:
                    self.driver.execute_script(f"Services.prefs.clearUserPref('{FF_MOTION_PREF}')")
            want = [media == "dark", motion == "reduce"]
            deadline = time.time() + 10
            while self.driver.execute_script("return [matchMedia('(prefers-color-scheme: dark)').matches,"
                                             " matchMedia('(prefers-reduced-motion: reduce)').matches]") != want:
                if time.time() > deadline:
                    raise RuntimeError(f"Firefox did not apply {FF_SCHEME_PREF}={FF_SCHEME_VALUES[media]} and "
                                       f"{FF_MOTION_PREF} for {motion}")
                time.sleep(0.05)
        self.media_applied, self.motion_applied = media, motion

    def add_preload(self, fn_source):
        if self.browser == "safari":
            raise RuntimeError("Safari has no WebDriver BiDi, so no preload script can run before the page's own")
        self.preloads.append(self.driver.script._add_preload_script(fn_source))

    def remove_preloads(self):
        while self.preloads:
            sid = self.preloads.pop()
            try:
                self.driver.script._remove_preload_script(script_id=sid)
            except Exception:
                pass

    def quit(self):
        try:
            if self.browser == "firefox":
                with self.driver.context(self.driver.CONTEXT_CHROME):
                    for pref in (FF_SCHEME_PREF, FF_MOTION_PREF, FF_JS_PREF):
                        self.driver.execute_script(f"Services.prefs.clearUserPref('{pref}')")
        except Exception:
            pass
        try:
            self.driver.quit()
        except Exception:
            pass
        proc = getattr(getattr(self.driver, "service", None), "process", None)
        if proc is not None and proc.poll() is None:
            proc.kill()
        if self.browser == "safari":
            # safaridriver leaves its --automation Safari running after a quit (tests/README.md, Rig
            # notes, Safari); the caller holds the Safari lock, so it is this session's.
            from .browsers import _kill_automation_safari
            _kill_automation_safari()


# -- running ---------------------------------------------------------------------------------------

def _slug(route):
    return route.strip("/").replace("/", "--") or "index"


def run_one(page, check, route, oracle_side, shots_dir):
    """Run one check on one route; return its result record."""
    t0 = time.time()
    rec = {"check": check.name, "group": check.group, "route": route, "browser": page.browser}
    if page.layout == "routes" and route_parts(route) is not None:
        rec["loaded"] = to_old_route(route, page.old_routes)
    skip = None
    if page.layout not in check.layouts:
        # A check of what only one layout has (the one page's spy and URLs, say): recorded, with why.
        skip = (f"layout:{page.layout}", check.layout_reason)
    elif page.browser == "safari" and check.media != page.sess.os_scheme:
        # Safari runs the OS scheme only: the owner's pass of the other appearance runs this check.
        skip = (f"media:{check.media}", f"Safari cannot emulate prefers-color-scheme: {check.media}; the OS scheme is "
                                        f"{page.sess.os_scheme}")
    elif page.browser == "safari" and check.motion != "no-preference":
        skip = (f"motion:{check.motion}", f"Safari cannot emulate prefers-reduced-motion: {check.motion}")
    elif page.browser == "safari" and not check.javascript:
        skip = ("javascript:off", "WebDriver cannot turn JavaScript off in Safari (05: the JavaScript-off deep link "
                                  "runs in Chrome and Firefox)")
    elif page.browser == "safari" and check.preload and not check.preload_optional:
        skip = ("preload", "Safari has no WebDriver BiDi, so no preload script can run before the page's own "
                           "(the check runs in Chrome and Firefox)")
    elif page.browser == "safari" and check.safari_skip:
        skip = ("safari", check.safari_skip)
    if skip:
        rec.update(status="skip", failed=None, skipped=skip[0], duration_s=0.0, assertions=[], notes=[skip[1]])
        return rec
    try:
        page.reset(check, route)
        check.fn(page)
        status, failed = "pass", None
    except CheckFailed as e:
        status, failed = "fail", e.label
    except Exception as e:
        from selenium.common.exceptions import WebDriverException
        from urllib3.exceptions import HTTPError as Urllib3Error
        status, failed = "error", None
        rec["error"] = f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else repr(e)}"
        rec["traceback"] = traceback.format_exc(limit=6)
        if isinstance(e, (Urllib3Error, TimeoutError, ConnectionError)) or (
                isinstance(e, WebDriverException) and "session" in str(e).lower()):
            rec["webdriver_error"] = True
    finally:
        page.cleanup()
        try:
            page.sess.remove_preloads()
        except Exception:
            pass
    bug = check.oracle_bug if oracle_side else None
    if bug:
        rec["oracle_bug"] = bug
        if status == "fail" and failed == bug["fails"]:
            status = "xfail"
        elif status == "pass":
            status = "xpass"
    rec.update(status=status, failed=failed, duration_s=round(time.time() - t0, 2),
               assertions=page.assertions, notes=page.notes)
    if status in ("fail", "error", "xpass") and shots_dir is not None:
        try:
            shot = shots_dir / f"{page.browser}__{check.name}__{_slug(route)}.png"
            page.screenshot(shot)
            rec["screenshot"] = str(shot.relative_to(REPO))
        except Exception:
            pass
    return rec


class Runner:
    def __init__(self, jobs, base, ready, oracle_side, workers, run_dir, shots, log, run_id, layout, routes):
        self.base, self.ready, self.oracle_side = base, ready, oracle_side
        self.layout, self.routes = layout, routes
        self.run_dir, self.shots, self.log, self.run_id = run_dir, shots, log, run_id
        self.lock = threading.Lock()
        self.queues = {}
        for b, check, route in jobs:
            self.queues.setdefault(b, []).append((check, route))
        self.workers = workers
        self.results, self.sessions, self.errors = [], [], []
        self.total = len(jobs)
        self.stopping = False
        self.t0 = time.time()

    def _next(self, browser):
        with self.lock:
            q = self.queues.get(browser)
            if self.stopping or not q:
                return None
            return q.pop(0)

    def _record(self, rec):
        with self.lock:
            self.results.append(rec)
            n = len(self.results)
        tail = ""
        if rec["status"] in ("fail", "xfail", "xpass"):
            last = next((a for a in reversed(rec["assertions"]) if not a["ok"]), None)
            tail = f" at {rec['failed']!r}" + (f": {json.dumps(last.get('detail'))[:300]}" if last and last.get("detail") else "")
        elif rec["status"] == "error":
            tail = f": {rec.get('error', '')[:300]}"
        self.log(f"[{n}/{self.total} {time.time() - self.t0:5.0f}s] {rec['browser']:7} {rec['check']} {rec['route']}: "
                 f"{rec['status'].upper()} ({len(rec['assertions'])} assertions, {rec['duration_s']}s){tail}")

    def _worker(self, browser, n):
        from . import locks
        label = f"{self.run_id} behavior {browser}#{n}"
        try:
            with locks.slot(label, self.log), \
                    (locks.safari(label, self.log) if browser == "safari" else contextlib.nullcontext()):
                sess = None
                try:
                    while True:
                        job = self._next(browser)
                        if job is None:
                            break
                        if sess is None:
                            sess = Session(browser, self.log)
                            page = Page(sess, self.base, self.ready, self.layout, self.routes)
                            if browser == "safari":
                                sess.read_os_scheme(self.base)
                            with self.lock:
                                self.sessions.append(sess.describe())
                            self.log(f"{label}: {browser} {sess.version} ({sess.driver_version}), launch {sess.launch_s}s"
                                     + (f", OS scheme {sess.os_scheme}" if sess.os_scheme else ""))
                        check, route = job
                        loads = page.loads
                        rec = run_one(page, check, route, self.oracle_side, self.run_dir / "shots" if self.shots else None)
                        rec["loads"] = page.loads - loads   # documents loaded by page.load and reset
                        self._record(rec)
                        if rec["status"] == "error" and rec.get("webdriver_error"):
                            # The browser stopped answering: end the session, start a new one.
                            self.log(f"{label}: restarting the session after a WebDriver error")
                            sess.quit()
                            sess = None
                finally:
                    if sess is not None:
                        sess.quit()
        except Exception as e:
            with self.lock:
                self.errors.append(f"{label}: worker failed: {e}\n{traceback.format_exc()}")
            self.log(f"{label}: worker failed: {e}")

    def run(self):
        threads = []
        for b in self.queues:
            # One Safari session at a time machine-wide (the Safari lock), so one worker.
            n = 1 if b == "safari" else self.workers.get(b, 1)
            for i in range(max(1, min(n, len(self.queues[b])))):
                t = threading.Thread(target=self._worker, args=(b, i), name=f"behavior-{b}-{i}", daemon=True)
                threads.append(t)
                t.start()
        try:
            for t in threads:
                while t.is_alive():
                    t.join(0.5)
        except KeyboardInterrupt:
            with self.lock:
                self.stopping = True
            self.log("interrupted: finishing the running checks")
            for t in threads:
                t.join(120)
            self.errors.append("interrupted")
        left = sum(len(q) for q in self.queues.values())
        if left:
            self.errors.append(f"{left} checks never ran")
        return self.results


def default_layout(side, expect_oracle_bugs):
    """The target's layout: one-page for a target whose targets.json names its one_page (dist), and for
    a base URL unless it serves the oracle (--expect-oracle-bugs); routes for the oracle and every
    other named target (static-femto, static-multipage, the fixture)."""
    if side.kind == "url":
        return "routes" if expect_oracle_bugs else "one-page"
    return "one-page" if side.kind == "command" and side.conf.get("one_page") else "routes"


def resolve_target(spec, ready):
    """A harness Side for --target: a named target (oracle, dist), dist:<path> (dist's own server
    on another built folder; harness.targets handles it) or a base URL."""
    from .targets import Side
    return Side(spec, ready)


def summary_text(result):
    lines = [f"{result['status']}  behavior {result['target']} ({result['base']}, layout {result['layout']}), run "
             f"{result['run_id']}, {result['duration_s']} s"]
    t = result["totals"]
    lines.append("totals: " + ", ".join(f"{k} {v}" for k, v in t.items()))
    for b, d in result["by_browser"].items():
        lines.append(f"  {b:7} " + ", ".join(f"{k} {v}" for k, v in d.items()))
    bad = [r for r in result["checks"] if r["status"] in ("fail", "error", "xpass")]
    if bad:
        lines.append("")
        lines.append("FAILED CHECKS")
        for r in bad:
            lines.append(f"  {r['browser']} {r['check']} {r['route']}: {r['status'].upper()}"
                         + (f" at {r['failed']!r}" if r.get("failed") else "")
                         + (f" ({r['error']})" if r.get("error") else ""))
            last = next((a for a in reversed(r["assertions"]) if not a["ok"]), None)
            if last and last.get("detail"):
                lines.append("      " + json.dumps(last["detail"])[:600])
            if r["status"] == "xpass":
                lines.append(f"      expected the oracle to fail at {r['oracle_bug']['fails']!r}: {r['oracle_bug']['reason']}")
    sk = [r for r in result["checks"] if r["status"] == "skip"]
    if sk:
        lines.append("")
        lines.append(f"SKIPPED (a check of the other layout; in Safari, the other appearance's, which the owner's pass "
                     f"of that appearance runs, or one that needs what Safari's WebDriver cannot do, which Chrome and "
                     f"Firefox run): {len(sk)}")
        for r in sk:
            lines.append(f"  {r['browser']} {r['check']} {r['route']}: {r['skipped']}: {(r.get('notes') or [''])[0]}")
    xf = [r for r in result["checks"] if r["status"] == "xfail"]
    if xf:
        lines.append("")
        lines.append("EXPECTED FAILURES (oracle bugs the conversion fixes)")
        for r in xf:
            lines.append(f"  {r['browser']} {r['check']} {r['route']}: at {r['failed']!r}: {r['oracle_bug']['reason']}")
    if result["errors"]:
        lines.append("")
        lines.append("HARNESS ERRORS")
        for e in result["errors"]:
            lines.append("  " + e.splitlines()[0])
    lines.append("")
    lines.append("CHECKS")
    for r in sorted(result["checks"], key=lambda r: (r["group"], r["check"], r["route"], r["browser"])):
        lines.append(f"  {r['status'].upper():5} {r['browser']:7} {r['group']:15} {r['check']} {r['route']} "
                     f"({len(r['assertions'])} assertions, {r['duration_s']}s)")
    return "\n".join(lines) + "\n"


def run_behavior(args):
    from .cli import git_info
    from .targets import TargetError, start
    try:
        checks = select(load_checks(), csv(args.groups), csv(args.checks))
    except SystemExit as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    browsers = csv(args.browsers)
    for b in browsers:
        if b not in BROWSERS:
            print(f"error: the behavior mode runs in {', '.join(BROWSERS)}, not {b}", file=sys.stderr)
            return 2
    jobs = [(b, c, r) for b in browsers for c in checks for r in c.routes]
    if args.list:
        for c in checks:
            extra = [x for x in (c.motion != "no-preference" and f"motion {c.motion}",
                                 not c.javascript and "JavaScript off", c.cold and "cold cache") if x]
            print(f"{c.group:15} {c.name:28} {','.join(c.routes)}  {c.width}x{c.height} {c.media}"
                  + "".join(f", {x}" for x in extra)
                  + (f"  {' and '.join(c.layouts)} only: {c.layout_reason}" if len(c.layouts) < len(LAYOUTS) else "")
                  + (f"  oracle_bug fails at {c.oracle_bug['fails']!r}" if c.oracle_bug else ""))
            for line in c.doc.splitlines():
                print(f"{'':17}{line}")
        print(f"{len(checks)} checks, {sum(len(c.routes) for c in checks)} check-routes, {len(jobs)} runs "
              f"in {', '.join(browsers)}")
        return 0
    if not args.target:
        print("error: behavior needs --target (oracle, dist, dist:<path> or a base URL)", file=sys.stderr)
        return 2
    if "safari" in browsers:
        # femto's Safari rules (tests/README.md, Rig notes, Safari): never while the user's own Safari
        # is open, and only on an unlocked screen, since input never reaches a hidden page.
        from .browsers import screen_front_app, users_safari_running
        if users_safari_running():
            print("error: the user's own Safari is running; quit it (Cmd-Q) before a Safari run", file=sys.stderr)
            return 2
        if screen_front_app() == "loginwindow":
            print("error: the screen is locked; the behavior mode drives Safari with real input, which needs an "
                  "unlocked screen with the automation window in front", file=sys.stderr)
            return 2
    try:
        side = resolve_target(args.target, args.ready)
        side.check()
    except TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    oracle_side = side.kind == "oracle" or args.expect_oracle_bugs
    layout = args.layout or default_layout(side, args.expect_oracle_bugs)
    routes = None
    if layout == "routes":
        try:
            routes = old_routes()
        except TargetError as e:
            print(f"error: the routes layout reads the old routes from {ROUTES_MENU[0]}:{ROUTES_MENU[1]}: {e}",
                  file=sys.stderr)
            return 2
        missing = sorted({r for c in checks if layout in c.layouts for r in c.routes if to_old_route(r, routes) is None})
        if missing:
            print(f"error: no old route shows {', '.join(missing)}: a check on such a route runs on the one page "
                  "only (its layouts)", file=sys.stderr)
            return 2
    workers = {b: 1 for b in BROWSERS}
    for kv in csv(args.workers):
        k, _, v = kv.partition("=")
        workers[k] = int(v)
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-behavior-{os.getpid()}"
    run_dir = RESULTS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_f = open(run_dir / "log.txt", "a")
    log_lock = threading.Lock()

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        with log_lock:
            print(line, flush=True)
            log_f.write(line + "\n")
            log_f.flush()

    log(f"run {run_id}: behavior, {len(checks)} checks, {len(jobs)} runs in {', '.join(browsers)}; target "
        f"{args.target}{' (oracle bugs expected)' if oracle_side else ''}, layout {layout}; results in "
        f"{run_dir.relative_to(REPO)}")
    t0 = time.time()
    results, errors, sessions = [], [], []
    try:
        with contextlib.ExitStack() as stack:
            try:
                start(stack, side, log, run_dir)
            except Exception as e:
                log(f"error: cannot start the target: {type(e).__name__}: {e}")
                log_f.close()
                return 2
            log(f"target {side.spec} at {side.base} (ready: {side.ready})")
            runner = Runner(jobs, side.base, side.ready, oracle_side, workers, run_dir, not args.no_shots, log, run_id,
                            layout, routes)
            results = runner.run()
            errors, sessions = runner.errors, runner.sessions
    except KeyboardInterrupt:
        errors.append("interrupted while starting or stopping the target")
    log("target stopped")
    totals = {s: sum(1 for r in results if r["status"] == s) for s in STATUSES}
    totals["runs"] = len(results)
    totals["planned"] = len(jobs)
    by_browser = {}
    for b in browsers:
        rs = [r for r in results if r["browser"] == b]
        by_browser[b] = {s: sum(1 for r in rs if r["status"] == s) for s in STATUSES}
    # A skip is the other layout's check or, in Safari, the other appearance's (the owner's pass of
    # that appearance runs it) or one Safari's WebDriver cannot run (Chrome and Firefox run it).
    ok =not errors and len(results) == len(jobs) and all(r["status"] in ("pass", "xfail", "skip") for r in results)
    result = {"run_id": run_id, "mode": "behavior", "status": "PASS" if ok else "FAIL", "argv": sys.argv[1:],
              "label": args.label, "target": args.target, "base": side.base, "ready": side.ready, "side": side.describe(),
              "layout": layout,
              "oracle_bugs_expected": oracle_side, "browsers": browsers,
              "groups": sorted({c.group for c in checks}), "checks_selected": [c.describe() for c in checks],
              "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
              "duration_s": round(time.time() - t0, 1), "git": git_info(), "sessions": sessions,
              "totals": totals, "by_browser": by_browser, "errors": errors,
              "checks": sorted(results, key=lambda r: (r["browser"], r["group"], r["check"], r["route"]))}
    (run_dir / "result.json").write_text(json.dumps(result, indent=1))
    text = summary_text(result)
    (run_dir / "summary.txt").write_text(text)
    print(text)
    log(f"wrote {run_dir.relative_to(REPO)}/result.json and summary.txt")
    log_f.close()
    return 0 if ok else 1
