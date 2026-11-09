"""Loads: criterion 15's run-time half, on every page of the URL inventory (the 404 page through a
path that has none) and the docs page once more with a theme. Every page loads only same-origin
resources, and its only render-blocking scripts are the two inline head scripts: the ?theme= script,
then the color-scheme script (Decisions 8 and 14). tests/static_checks.py reads the same two rules
from the markup, the CSS and the scripts; these checks read what the browser actually loaded.

A page's loads are read two ways. In the page: the performance entries (navigation and resource) of
the document and of every frame it can reach, those in open shadow roots included, which list every
load that finished, whatever markup or script started it, and never a URL that is only text. From
outside the page, in Chrome and Firefox: the browser's own request log (WebDriver BiDi network
events, page.requests()), which also has what no page's entries list: a worker's requests, a frame
the page cannot read, a load that fails before any response. Safari has no BiDi, so there the page's
entries are read alone. `uv run tests/run.py rig` proves that each way sees what it should
(tests/README.md, Rig).

https://femto.style (that scheme, host and default port only) is the site's own origin once
deployed: a load from it is noted, never failed. Production adds one cross-origin load that no build
has, the zone's Web Analytics beacon, which Cloudflare injects at the edge (criterion 15's exception,
the owner, 2026-11-08); a check against production would fail on it, as it should."""
from urllib.parse import urlsplit

from behavior import LOADS, check, origin

GROUP = "loads"

# PLAN.md's URL inventory, the 404 page through a path that has none, and /docs with a theme, so the
# theme's stylesheet is loaded too: the pages criterion 10's a11y run reads.
PAGES = ("/", "/docs", "/docs?theme=jade", "/examples", "/does-not-exist")
# One width per breakpoint band, the rig's widths: a media query that loads a file
# at one width only is reached.
WIDTHS = (375, 600, 800, 1100, 1300, 1600)
SITE_ORIGIN = ("https", "femto.style", 443)  # the deployed site's origin: same-origin once deployed
KEY = "femtoColorScheme"

# A JavaScript MIME type essence (HTML's list): a <script> with one, or with no type, is classic.
JS_TYPES = ("application/ecmascript application/javascript application/x-ecmascript application/x-javascript "
            "text/ecmascript text/javascript text/javascript1.0 text/javascript1.1 text/javascript1.2 "
            "text/javascript1.3 text/javascript1.4 text/javascript1.5 text/jscript text/livescript "
            "text/x-ecmascript text/x-javascript").split()

# Every classic script of the document, in document order, as the parser met it: inline or with a
# source, in <head> or not, async, defer, and which of the two head scripts it is by its text (the
# ?theme= script writes its <link> with document.write; the color-scheme script reads
# femtoColorScheme). A classic script blocks rendering unless it has a source and async or defer
# (a module never does; a script a script inserts is async).
SCRIPTS = """
const types = arguments[0];
return [...document.querySelectorAll("script")].filter(s => {
  const t = (s.getAttribute("type") ?? "").trim().toLowerCase();
  return s.hasAttribute("type") ? (t === "" || types.includes(t)) : true;
}).map(s => ({inline: !s.hasAttribute("src"), src: s.getAttribute("src"), head: !!s.closest("head"), async: s.async,
              defer: s.defer,
              role: s.hasAttribute("src") ? null : s.text.includes("document.write") ? "theme"
                    : s.text.includes("femtoColorScheme") ? "color-scheme" : "other"}));
"""

SETTLE = """
const frame = () => new Promise(r => requestAnimationFrame(() => r()));
await frame(); await frame();
await new Promise(r => setTimeout(r, 100));
return true;
"""


def judge(page, urls, own):
    """The URLs of `urls` on another origin than `own`, less https://femto.style's, which are noted."""
    cross, site = [], []
    for u in urls:
        o = origin(u)
        if o is None or o == own:
            continue
        (site if o == SITE_ORIGIN else cross).append(u)
    for u in sorted(set(site)):
        page.note(f"a load from the deployed site's own origin, https://femto.style: {u}")
    return sorted(set(cross))


def sweep(page):
    """Every width of WIDTHS in each color scheme the browser can give (Safari: the OS scheme
    only), then the page scrolled to its end and back, so a load that only a width, a scheme or a
    scroll starts has started."""
    schemes = ("light", "dark") if page.browser != "safari" else (page.sess.os_scheme,)
    for media in schemes:
        page.sess.set_media(media, page.check.motion)
        for w in WIDTHS:
            page.resize(w, page.check.height)
            page.ajs(SETTLE)
    page.scroll_to(page.js("return document.documentElement.scrollHeight"))
    page.scroll_to(0)
    page.ajs(SETTLE)


def expect_entries(page, label, own):
    """Read the loaded document's and its frames' performance entries (LOADS) and assert them:
    every frame readable, no buffer full, every entry's URL same-origin. Returns the entries."""
    r = page.js(LOADS)
    page.eq(f"{label}: every frame's entries can be read", r["unreadable"], [], docs=r["docs"])
    page.eq(f"{label}: no document's Resource Timing buffer is full ({r['limit']} entries)", r["full"], [])
    page.expect(f"{label}: the page has its navigation entry",
                any(e["type"] == "navigation" for e in r["entries"]), entries=len(r["entries"]))
    cross = judge(page, [e["url"] for e in r["entries"]], own)
    page.eq(f"{label}: every load in the pages' own entries is same-origin", cross, [],
            entries=[e for e in r["entries"] if e["url"] in cross])
    return r["entries"]


@check("same-origin-loads", PAGES, netlog=True, cold=True)
def same_origin_loads(page):
    """Criterion 15: every page loads only same-origin resources. The page is loaded three times:
    cold (the browser's caches emptied first, so every load is a request) with nothing stored, then with femtoColorScheme '"light"' and with '"dark"' stored (data-theme
    on <html>, Decision 14). Each time, once every width of WIDTHS has been shown in light and in
    dark (Safari: its OS scheme) and the page scrolled to its end and back, the performance entries
    of the document and of every frame it can reach (navigation and resource; frames in open shadow
    roots included) are read: every frame can be read, no document's buffer is full, the navigation
    entry is there, and every URL is on the page's origin (or https://femto.style, noted). Then, in
    Chrome and Firefox, the browser's own log of every request the check's loads started (WebDriver
    BiDi beforeRequestSent and fetchError) holds the documents' requests and no URL on another
    origin: that log also sees a worker's requests, a frame the page cannot read and a load that
    fails before any response. The page's location stays on its origin."""
    own = origin(page.base)
    total = 0
    for stored in (None, '"light"', '"dark"'):
        label = "nothing stored" if stored is None else f"{KEY} {stored} stored"
        if stored is not None:
            page.js("localStorage.setItem(arguments[0], arguments[1])", KEY, stored)
            page.load(page.route)
            page.eq(f"{label}: data-theme follows it", page.js("return document.documentElement.dataset.theme ?? null"),
                    stored.strip('"'))
        page.eq(f"{label}: the page is on its own origin", origin(page.js("return location.href")), own)
        sweep(page)
        total += len(expect_entries(page, label, own))
    page.note(f"{total} performance entries over the three loads")
    log = page.requests()
    if log is None:
        page.note(f"{page.browser} keeps no request log (no WebDriver BiDi): the pages' own entries were read alone")
        return
    path = urlsplit(page.route).path
    page.expect("the request log has the page's own requests",
                sum(1 for x in log if x["event"] == "request" and urlsplit(x["url"] or "").path == path) >= 3,
                requests=len(log), first=[x["url"] for x in log[:5]])
    cross = judge(page, [x["url"] for x in log], own)
    page.eq("every request the browser logged is same-origin", cross, [],
            requests=[x for x in log if x["url"] in cross])
    failed = [x for x in log if x["event"] == "error"]
    if failed:
        page.note(f"{len(failed)} same-origin requests failed before a response: "
                  + ", ".join(f"{x['url']} ({x.get('error')})" for x in failed[:5]))
    page.note(f"{len(log)} requests logged by the browser")


@check("render-blocking-scripts", PAGES)
def render_blocking_scripts(page):
    """Criterion 15: the only render-blocking scripts are the two inline head scripts, the ?theme=
    script and then the color-scheme script (Decisions 8 and 14). Of the document's classic scripts
    (no type, or a JavaScript MIME type), those that block rendering (inline, or with a source and
    neither async nor defer) are exactly two, both inline and in <head>: first the ?theme= script
    (it writes its <link> with document.write), then the color-scheme script (it reads
    femtoColorScheme). No other classic script is in the document. In Chrome, which reports a
    resource's renderBlockingStatus, no script the page loaded is render-blocking."""
    scripts = page.js(SCRIPTS, JS_TYPES)
    blocking = [s for s in scripts if s["inline"] or not (s["async"] or s["defer"])]
    page.eq("the render-blocking scripts are the ?theme= script, then the color-scheme script",
            [(s["role"], s["inline"], s["head"]) for s in blocking], [("theme", True, True), ("color-scheme", True, True)],
            scripts=scripts)
    page.eq("no other classic script", len(scripts), 2, scripts=scripts)
    r = page.js(LOADS)
    if not any(e["blocking"] is not None for e in r["entries"] if e["type"] != "navigation"):
        page.note(f"{page.browser} reports no renderBlockingStatus: only the document's scripts are read")
        return
    loaded = [e for e in r["entries"] if e["type"] == "script" or (e["url"] or "").split("?")[0].endswith((".js", ".mjs"))]
    page.eq("no script the page loaded is render-blocking", [e["url"] for e in loaded if e["blocking"] == "blocking"], [],
            scripts=loaded)
