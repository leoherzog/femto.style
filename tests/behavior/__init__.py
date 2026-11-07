"""The behavior suite: scripted checks of every widget the static site rebuilds (docs/research/01
§2) and of the one docs page (criterion 7), run by `uv run tests/run.py behavior`
(tests/harness/behavior.py) against one target at a time: the oracle, the static site in dist/, or
any base URL. tests/README.md, Behavior, lists every check.

Each group module (shell.py, getting-started.py, ...) sets GROUP and registers its checks with
@check. A check is a function of one argument, the page (harness.behavior.Page), already loaded at
the check's route with the check's viewport, color scheme and storage. It drives the page with real
WebDriver input (clicks, keys, scrolling, window resizes) and asserts only what any side can be held
to: DOM state, focus, the URL, history and storage. It never reads React state, a framework global
or a script's source, so the same check runs against the oracle and the static site.

Assertions are page.expect(label, ok, **detail), page.eq(label, actual, expected) and
page.wait(label, js, timeout): the first one that fails ends the check, and its label is what the
result names. Routes are written in the one page's URLs (/docs#modal, /docs, /docs?theme=jade#
theme-picker); on a target with one page per route each is loaded at its old route
(harness.behavior, layouts), and the check's scripts find its content in S, the route's section on
the one page or the whole document there. layouts=("one-page",) with layout_reason marks a check of
what only the one page has; it is recorded as skipped, with that reason, on the other layout.
oracle_bug={"fails": label, "reason": ...} marks a check whose assertion `label` is
an oracle bug the conversion fixes (PLAN.md, Divergence categories, oracle-bug): against the oracle
the check must fail at exactly that assertion (XFAIL); passing there (XPASS) or failing elsewhere
fails the run.

From Phase 4 the static site describes femto 3 and no longer matches the oracle's markup and text
(PLAN.md Decision 6). A check whose assertions hold the Phase 4 markup branches on page.layout where
the oracle's own markup can still be held to the same behavior (a link that became a button, a
count that changed), and runs on the one page only (layouts) where the widget itself is new or
reworked: the Theme picker, the /examples mockups.
"""
import dataclasses
import inspect
import textwrap
import time

GROUPS = ("shell", "one-page", "getting-started", "customization", "layout", "content", "forms", "components-a",
          "components-b", "landing", "examples")
MEDIA = ("light", "dark")
MOTION = ("no-preference", "reduce")
LAYOUTS = ("one-page", "routes")


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
    oracle_bug: dict | None = None
    preload: str | None = None
    module: str = ""
    layouts: tuple = LAYOUTS
    layout_reason: str | None = None
    motion: str = "no-preference"
    javascript: bool = True
    cold: bool = False
    preload_optional: bool = False
    delay: dict | None = None
    safari_skip: str | None = None

    def describe(self):
        d = {"name": self.name, "group": self.group, "routes": list(self.routes),
             "viewport": [self.width, self.height], "media": self.media, "doc": self.doc}
        if self.layouts != LAYOUTS:
            d["layouts"], d["layout_reason"] = list(self.layouts), self.layout_reason
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
        if self.oracle_bug:
            d["oracle_bug"] = self.oracle_bug
        if self.preload:
            d["preload"] = True
        if self.safari_skip:
            d["safari_skip"] = self.safari_skip
        return d


REGISTRY: list[Check] = []


def check(name, routes, *, width=1300, height=900, media="light", storage=None, oracle_bug=None, preload=None,
          layouts=LAYOUTS, layout_reason=None, motion="no-preference", javascript=True, cold=False,
          preload_optional=False, delay=None, safari_skip=None):
    """Register a check. routes: one URL or several, in the one page's URLs (the check runs once per
    route). width and height: the document viewport (innerWidth, innerHeight). media:
    prefers-color-scheme. motion: prefers-reduced-motion. storage: localStorage items (raw strings)
    set on the target's origin before the first load. preload: a JavaScript function declaration
    run in every new document before the page's own scripts (WebDriver BiDi
    script.addPreloadScript); Safari, which has no BiDi, skips the check (`preload`), unless
    preload_optional: it then runs the check without it (page.preloaded says which). safari_skip: why
    the check cannot run in Safari for another reason (what its WebDriver cannot do): skipped there
    (`safari`) with that reason. javascript=False: the page's JavaScript is off (Chrome and Firefox;
    skipped in Safari). cold: the browser's HTTP cache is emptied before the route loads. delay:
    {path: seconds}, the target's responses for those exact paths held that long (WebDriver BiDi
    network interception, as 05's serve.py slowed the theme file; Safari, which has no BiDi, loads
    them at once and the check notes it). layouts and layout_reason: see the module docstring.
    oracle_bug: see the module docstring."""
    if isinstance(routes, str):
        routes = (routes,)
    if media not in MEDIA:
        raise ValueError(f"{name}: media must be one of {MEDIA}")
    if motion not in MOTION:
        raise ValueError(f"{name}: motion must be one of {MOTION}")
    layouts = tuple(layouts)
    if not layouts or set(layouts) - set(LAYOUTS):
        raise ValueError(f"{name}: layouts must be some of {LAYOUTS}")
    if len(layouts) < len(LAYOUTS) and not layout_reason:
        raise ValueError(f"{name}: a check that runs on one layout only says why (layout_reason)")
    if oracle_bug is not None and not (oracle_bug.get("fails") and oracle_bug.get("reason")):
        raise ValueError(f"{name}: oracle_bug needs 'fails' (an assertion label) and 'reason'")

    def deco(fn):
        group = fn.__globals__.get("GROUP")
        if group not in GROUPS:
            raise ValueError(f"{name}: module {fn.__module__} sets no known GROUP ({group!r})")
        if any(c.name == name for c in REGISTRY):
            raise ValueError(f"duplicate check name {name}")
        doc = textwrap.dedent(inspect.getdoc(fn) or "").strip()
        if not doc:
            raise ValueError(f"{name}: a check states what it asserts in its docstring")
        REGISTRY.append(Check(name, group, tuple(routes), fn, doc, width, height, media, storage,
                              oracle_bug, preload, fn.__module__, layouts, layout_reason, motion, javascript, cold,
                              preload_optional, delay, safari_skip))
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
    its data-tooltip draws ("Copy to clipboard Copy code"), which its icon's aria-label alone does not
    show."""
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


def nav_href(page, sid):
    """The side menu's link to a section: #<id> on the one page, the old route's path on routes."""
    if page.layout == "routes":
        return page.address(f"/docs#{sid}") if sid != "quick-start" else "/docs"
    return f"#{sid}"


def self_href(page, link, section_only=False):
    """Whether an example link points at its own route or section, as docs.*.jsx's Link to="#" did:
    href="/docs/<route>" on routes (the page's own path), and on the one page the page itself, /docs,
    or its section, /docs#<section> (only the section with `section_only`)."""
    r = page.js("const a = arguments[0]; return {href: a.getAttribute('href'), path: new URL(a.href).pathname,"
                " hash: new URL(a.href).hash, here: location.pathname}", link)
    if page.layout == "one-page":
        return r["path"] == "/docs" and r["hash"] in ((f"#{page.section}",) if section_only else ("", f"#{page.section}"))
    return r["href"] == r["here"]

