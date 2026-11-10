"""The behavior suite: scripted checks of every widget on the site and of the one docs page
(criterion 7), and the run-time half of criterion 15, run by `uv run tests/run.py behavior`
(tests/harness/behavior.py) against one build at a time. tests/README.md, Behavior, lists every
check.

Each group module (shell.py, getting-started.py, ...) sets GROUP and registers its checks with
@check. A check is a function of one argument, the page (harness.behavior.Page), already loaded at
the check's route with the check's viewport, color scheme and storage. It drives the page with real
WebDriver input (clicks, keys, scrolling, window resizes) and asserts what a reader sees and can do:
DOM state, focus, the URL, history, storage and the page's loads. It never reads a script's source.

Assertions are page.expect(label, ok, **detail), page.eq(label, actual, expected) and
page.wait(label, js, timeout): the first one that fails ends the check, and its label is what the
result names. Routes are the site's URLs (/docs#modal, /docs, /docs?theme=jade#theme-picker), and on
the docs page a check's scripts find its section in S.
"""
import dataclasses
import inspect
import textwrap
import time
from urllib.parse import urlsplit

GROUPS = ("shell", "one-page", "getting-started", "customization", "layout", "content", "forms", "components-a",
          "components-b", "landing", "examples", "loads")
MEDIA = ("light", "dark")
MOTION = ("no-preference", "reduce")


@dataclasses.dataclass
class Check:
    name: str
    group: str
    routes: tuple
    fn: object
    doc: str
    width: int = 1300
    height: int = 900
    media: str = "light"
    storage: dict | None = None
    preload: str | None = None
    module: str = ""
    motion: str = "no-preference"
    javascript: bool = True
    cold: bool = False
    preload_optional: bool = False
    delay: dict | None = None
    safari_skip: str | None = None
    netlog: bool = False

    def describe(self):
        d = {"name": self.name, "group": self.group, "routes": list(self.routes),
             "viewport": [self.width, self.height], "media": self.media, "doc": self.doc}
        if self.motion != "no-preference":
            d["motion"] = self.motion
        if not self.javascript:
            d["javascript"] = False
        if self.cold:
            d["cold"] = True
        if self.delay:
            d["delay"] = self.delay
        if self.storage:
            d["storage"] = self.storage
        if self.preload:
            d["preload"] = True
        if self.safari_skip:
            d["safari_skip"] = self.safari_skip
        if self.netlog:
            d["netlog"] = True
        return d


REGISTRY: list[Check] = []


def check(name, routes, *, width=1300, height=900, media="light", storage=None, preload=None,
          motion="no-preference", javascript=True, cold=False, preload_optional=False, delay=None, safari_skip=None,
          netlog=False):
    """Register a check. routes: one URL or several, the site's URLs (the check runs once per
    route). width and height: the document viewport (innerWidth, innerHeight). media:
    prefers-color-scheme. motion: prefers-reduced-motion. storage: localStorage items (raw strings)
    set on the target's origin before the first load. preload: a JavaScript function declaration
    run in every new document before the page's own scripts (WebDriver BiDi
    script.addPreloadScript); Safari, which has no BiDi, skips the check (`preload`), unless
    preload_optional: it then runs the check without it (page.preloaded says which). safari_skip: why
    the check cannot run in Safari for another reason (what its WebDriver cannot do): skipped there
    (`safari`) with that reason. javascript=False: the page's JavaScript is off (Chrome and Firefox;
    skipped in Safari). cold: the browser's caches are emptied before the route loads (Page.clear_cache). delay:
    {path: seconds}, the target's responses for those exact paths held that long (WebDriver BiDi
    network interception, which slows a file as a slow server would; Safari, which has no BiDi, loads
    them at once and the check notes it). netlog: every request the browser starts for the check's
    loads, from the route's load on, is logged from outside the page (WebDriver BiDi network events;
    page.requests() reads the log; Safari, which has no BiDi, logs nothing and the check notes it)."""
    if isinstance(routes, str):
        routes = (routes,)
    if media not in MEDIA:
        raise ValueError(f"{name}: media must be one of {MEDIA}")
    if motion not in MOTION:
        raise ValueError(f"{name}: motion must be one of {MOTION}")

    def deco(fn):
        group = fn.__globals__.get("GROUP")
        if group not in GROUPS:
            raise ValueError(f"{name}: module {fn.__module__} sets no known GROUP ({group!r})")
        if any(c.name == name for c in REGISTRY):
            raise ValueError(f"duplicate check name {name}")
        doc = textwrap.dedent(inspect.getdoc(fn) or "").strip()
        if not doc:
            raise ValueError(f"{name}: a check states what it asserts in its docstring")
        REGISTRY.append(Check(name, group, tuple(routes), fn, doc, width, height, media, storage, preload,
                              fn.__module__, motion, javascript, cold, preload_optional, delay, safari_skip, netlog))
        return fn
    return deco


# -- in-page helpers shared by several groups ----------------------------------------------------

# Records what a copy would put on the clipboard, without touching the machine's clipboard: both
# ways a page can copy text are replaced for this document only. document.execCommand("copy")
# records the selected text (the selection's first range, as the browser would copy it) and reports
# success; navigator.clipboard.writeText() and .write() record their argument and resolve.
COPY_SPY = r"""
window.__bhCopied = [];
const exec = Document.prototype.execCommand;
document.execCommand = function (cmd, ...rest) {
  if (String(cmd).toLowerCase() === "copy") {
    const sel = document.getSelection();
    __bhCopied.push({via: "execCommand", text: sel && sel.rangeCount ? sel.getRangeAt(0).toString() : ""});
    return true;
  }
  return exec.call(this, cmd, ...rest);
};
if (navigator.clipboard) {
  navigator.clipboard.writeText = (t) => { __bhCopied.push({via: "writeText", text: String(t)}); return Promise.resolve(); };
  navigator.clipboard.write = async (items) => {
    let text = null;
    for (const item of items || []) {
      if (item.types && item.types.includes("text/plain")) text = await (await item.getType("text/plain")).text();
    }
    __bhCopied.push({via: "write", text});
  };
}
return true;
"""

# A tree snapshot that ignores comments (React's SSR text separators) and whitespace-only text
# between elements: tag, attributes (sorted) and text, so two renderings of the same state compare
# equal however they were produced.
SNAPSHOT = r"""
const snap = (n) => {
  if (n.nodeType === 3) return n.data;
  if (n.nodeType !== 1) return null;
  const attrs = [...n.attributes].map(a => [a.name, a.value]).sort((x, y) => x[0] < y[0] ? -1 : 1);
  const kids = [];
  for (const c of n.childNodes) {
    const s = snap(c);
    if (s === null) continue;
    if (typeof s === "string" && typeof kids[kids.length - 1] === "string") kids[kids.length - 1] += s;
    else kids.push(s);
  }
  return [n.localName, attrs, kids.filter(k => typeof k !== "string" || k.trim() !== "" || n.closest("pre"))];
};
"""

# The highlighted structure of a code element: each child as [classes, text].
TOKENS = r"""
const tokens = (code) => [...code.childNodes].map(n => n.nodeType === 1 ? [n.className, n.textContent] : ["#text", n.data]);
"""

# The docs' Theme picker's colors in its order, read from /docs (its swatches' aria-labels,
# lowercased): the order every list of femto's theme colors a reader chooses from follows, the
# homepage's swatches and /examples' theme select among them. An async script (page.ajs).
PICKER_ORDER = r"""
const doc = new DOMParser().parseFromString(await (await fetch("/docs")).text(), "text/html");
done([...doc.querySelectorAll("article[data-version-picker] > header a")].map(a => a.getAttribute("aria-label").toLowerCase()));
"""

# A function of a section id, run in the page: how far its heading's top is below the line a link to
# #<id> puts it on, html's scroll-padding-top (0 there; negative above). A heading the page cannot
# scroll up to that line, near the page's end, counts as on it.
HEADING_LINE = r"""(id) => {
  const h = document.getElementById(id), root = document.documentElement;
  const line = parseFloat(getComputedStyle(root).scrollPaddingTop) || 0;
  const off = h.getBoundingClientRect().top - line;
  return off > 0 && Math.ceil(scrollY + innerHeight) >= root.scrollHeight - 1 ? 0 : off;
}"""


def computed_name(el):
    """An element's accessible name as the browser computes it (WebDriver Get Computed Label,
    Selenium's WebElement.accessible_name), not an attribute read from the DOM. A button named by its
    contents reads all of them: a copy button's also include femto's tooltip, the ::before text that
    its data-tooltip draws ("Copy code Copy code", "Copied Copy code"), which its icon's aria-label
    alone does not show."""
    return el.accessible_name


def expect_name(page, label, el, want, timeout=0.5, /, **detail):
    """Assert that the element's computed name (computed_name) is `want` within `timeout` seconds.
    The browser's accessibility tree follows a DOM change a little later than the DOM: in the first
    milliseconds after a copy button's ⧉ gave way to its ✓, Firefox 160 still named the button by the
    ✓'s text, and by its label once the tree had caught up."""
    t0 = time.time()
    while True:
        name = computed_name(el)
        if name == want or time.time() > t0 + timeout:
            return page.eq(label, name, want, after_s=round(time.time() - t0, 3), **detail)
        time.sleep(0.05)


FORCED_FOCUS = r"""
const e = document.activeElement, cs = getComputedStyle(e);
const rgba = (cs.outlineColor.match(/[\d.]+/g) || []).map(Number);
return {focusVisible: e.matches(":focus-visible"), forced: matchMedia("(forced-colors: active)").matches,
        outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
        drawn: cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0 && (rgba.length < 4 || rgba[3] > 0)};
"""


def expect_forced_focus(page, label):
    """In forced colors, which drop box-shadow, the focused element still marks its focus: it
    matches :focus-visible and its computed outline has a style other than none, a width above 0
    and a color that is not transparent (forced colors draw a transparent outline in a system
    color). Chrome only, with forced-colors: active emulated over CDP Emulation.setEmulatedMedia and
    the check's own scheme and motion put back after; Firefox has no WebDriver way to emulate forced
    colors, and records a note."""
    if page.browser != "chrome":
        page.note(f"{label}: {page.browser} cannot emulate forced colors over WebDriver")
        return
    def features(forced):
        return [{"name": "prefers-color-scheme", "value": page.check.media},
                {"name": "prefers-reduced-motion", "value": page.check.motion}, {"name": "forced-colors", "value": forced}]
    page.driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"features": features("active")})
    try:
        got = page.js(FORCED_FOCUS)
        page.eq(f"{label}: in forced colors the focus shows as an outline", {"forced": got["forced"], "focusVisible": got["focusVisible"],
                "drawn": got["drawn"]}, {"forced": True, "focusVisible": True, "drawn": True}, outline=got["outline"])
    finally:
        page.driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"features": features("none")})


def self_href(page, link, section_only=False):
    """Whether an example link points at its own section, as an empty example link does: the page
    itself, /docs, or its section, /docs#<section> (only the section with `section_only`)."""
    r = page.js("const a = arguments[0]; return {path: new URL(a.href).pathname, hash: new URL(a.href).hash}", link)
    return r["path"] == "/docs" and r["hash"] in ((f"#{page.section}",) if section_only else ("", f"#{page.section}"))


# Criterion 15's loads (loads.py; the rig proves the collector): every load the document and the
# frames it can reach list in their own performance entries, each document's navigation entry and
# every resource entry, with its initiator and, where the browser has it (Chrome), its
# renderBlockingStatus. Frames are read at any depth, those of the document tree
# (window.frames) and the iframe, frame, object and embed elements of every open shadow root, which
# window.frames leaves out. A frame that cannot be read (another origin, or sandboxed without
# allow-same-origin) is listed under unreadable; a document whose resource buffer is full (later
# loads dropped) under full.
LOADS = """
const limit = 250;   // each document's default Resource Timing buffer; later entries are dropped
const out = {docs: [], entries: [], full: [], unreadable: [], limit};
const seen = new Set();
const roots = (d) => {
  const found = [];
  const walk = (n) => { for (const el of n.querySelectorAll("*")) if (el.shadowRoot) { found.push(el.shadowRoot); walk(el.shadowRoot); } };
  walk(d);
  return found;
};
const visit = (w, where) => {
  if (seen.has(w)) return;
  seen.add(w);
  let href, nav, res;
  try {
    href = w.location.href;
    nav = w.performance.getEntriesByType("navigation");
    res = w.performance.getEntriesByType("resource");
  } catch (e) { out.unreadable.push(where); return; }
  out.docs.push(href);
  if (res.length >= limit) out.full.push(href);
  for (const e of [...nav, ...res]) {
    out.entries.push({url: e.name, type: e.entryType === "navigation" ? "navigation" : e.initiatorType, doc: href,
                      blocking: "renderBlockingStatus" in e ? e.renderBlockingStatus : null});
  }
  const kids = [];
  let n = 0;
  try { n = w.frames.length; } catch (e) { n = 0; }
  for (let i = 0; i < n; i++) kids.push([() => w.frames[i], "frame " + i + " of " + where]);
  let d = null;
  try { d = w.document; } catch (e) { d = null; }
  if (d) {
    for (const r of [d, ...roots(d)]) {
      for (const el of r.querySelectorAll("iframe, frame, object, embed")) {
        kids.push([() => (el.localName === "embed" && el.getSVGDocument && el.getSVGDocument()
                          ? el.getSVGDocument().defaultView : el.contentWindow),
                   el.localName + " in " + where]);
      }
    }
  }
  for (const [get, label] of kids) {
    let f = null;
    try { f = get(); } catch (e) { out.unreadable.push(label); continue; }
    if (f) visit(f, label);
  }
};
visit(window, "the page");
return out;
"""


def origin(url):
    """(scheme, host, port) of an http(s) or ws(s) URL, or None for any other (data:, blob:, about:)."""
    u = urlsplit(url or "")
    if u.scheme not in ("http", "https", "ws", "wss"):
        return None
    try:
        port = u.port
    except ValueError:
        port = None
    return (u.scheme, (u.hostname or "").lower(), port or {"http": 80, "https": 443, "ws": 80, "wss": 443}[u.scheme])
