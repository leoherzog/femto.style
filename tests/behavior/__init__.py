"""The behavior suite: scripted checks of every widget the static site rebuilds (docs/research/01
§2), run by `uv run tests/run.py behavior` (tests/harness/behavior.py) against one target at a time:
the oracle, the static site in dist/, or any base URL. tests/README.md, Behavior, lists every check.

Each group module (shell.py, getting-started.py, ...) sets GROUP and registers its checks with
@check. A check is a function of one argument, the page (harness.behavior.Page), already loaded at
the check's route with the check's viewport, color scheme and storage. It drives the page with real
WebDriver input (clicks, keys, scrolling, window resizes) and asserts only what any side can be held
to: DOM state, focus, the URL, history and storage. It never reads React state, a framework global
or a script's source, so the same check runs against the oracle and the static site.

Assertions are page.expect(label, ok, **detail), page.eq(label, actual, expected) and
page.wait(label, js, timeout): the first one that fails ends the check, and its label is what the
result names. oracle_bug={"fails": label, "reason": ...} marks a check whose assertion `label` is
an oracle bug the conversion fixes (PLAN.md, Divergence categories, oracle-bug): against the oracle
the check must fail at exactly that assertion (XFAIL); passing there (XPASS) or failing elsewhere
fails the run.
"""
import dataclasses
import inspect
import textwrap

GROUPS = ("shell", "getting-started", "customization", "layout", "content", "forms", "components-a",
          "components-b", "landing")
MEDIA = ("light", "dark")


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

    def describe(self):
        d = {"name": self.name, "group": self.group, "routes": list(self.routes),
             "viewport": [self.width, self.height], "media": self.media, "doc": self.doc}
        if self.storage:
            d["storage"] = self.storage
        if self.oracle_bug:
            d["oracle_bug"] = self.oracle_bug
        if self.preload:
            d["preload"] = True
        return d


REGISTRY: list[Check] = []


def check(name, routes, *, width=1300, height=900, media="light", storage=None, oracle_bug=None, preload=None):
    """Register a check. routes: one path or several (the check runs once per route). width and
    height: the document viewport (innerWidth, innerHeight). media: prefers-color-scheme. storage:
    localStorage items (raw strings) set on the target's origin before the first load. preload: a
    JavaScript function declaration run in every new document before the page's own scripts
    (WebDriver BiDi script.addPreloadScript). oracle_bug: see the module docstring."""
    if isinstance(routes, str):
        routes = (routes,)
    if media not in MEDIA:
        raise ValueError(f"{name}: media must be one of {MEDIA}")
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
                              oracle_bug, preload, fn.__module__))
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
