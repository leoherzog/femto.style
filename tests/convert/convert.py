# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The one-time converter (PLAN.md Conversion rules): an oracle route's hydrated DOM into a section file.

  uv run tests/convert/convert.py /docs/forms/input           writes site/docs/sections/input.html
  uv run tests/convert/convert.py /docs/version-picker/jade   writes site/docs/sections/version-picker/jade.html
  uv run tests/convert/convert.py /examples --out -           any route's <main> content, to stdout
  uv run tests/convert/convert.py /docs/forms/input --report  also list what JavaScript must set (below)

Options: --out FILE (- for stdout; default: the section file of the route in site/docs/menu.json),
--force (overwrite an existing file, which may hold hand edits), --raw (no added line breaks: the
oracle's own whitespace only), --report.

Input is tests/oracle/capture/<slug>/dom.html (the hydrated DOM at 1300x900, light), slug being the
path without its end slashes, "/" -> "--" ("index" for /). Output is the route's content: on a docs
route every child of <main> after aside#documentation-menu (the hgroup, the table of contents, the
div#content with the sections and the edit link, and anything the route put there, such as a
<dialog>), which build.mjs wraps in the per-route docs layout again; on another route, every child of
<main>. The converter:
- drops comments (React's <!-- --> text separators), <script> elements and fetch-hint <link>s
  (preload, modulepreload, prefetch);
- rewrites hashed asset URLs (/build/_assets/<name>-<HASH>.<ext>) to /assets/img/<name>.<ext>
  (/assets/brand/ for the femto logo and mark files), and lists each, since the attribute then
  differs from the oracle;
- replaces the highlighted spans in <code class="language-X"> with the code's text, escaped
  (build.mjs highlights it again, run for run; tests/convert/highlight-check.mjs proves that on every
  oracle code block);
- drops aria-current from the table of contents' links: it is the scroll spy's state, which the server
  HTML does not have and docs.js sets;
- keeps every other element, attribute (data-discover included), text and order as they are.
It adds line breaks and indentation only between siblings that are all block-level elements by tag,
outside <pre>, <svg> and anything with text or inline children, where the whitespace renders nothing.
It warns about links to the routes Decision 5 drops, which must be removed or pointed at /docs by hand
(and registered as dropped-route).

--report compares the same region of server.html (before hydration), dom-dark.html
(prefers-color-scheme: dark) and dom-375.html (375 px wide) with dom.html and lists every element
whose attributes or own text differ: that is the state the oracle's JavaScript set at load, per scheme
or per width, which the static site's modules must set the same way (or the converter dropped, as with
the table of contents' aria-current).
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPTURE = ROOT / "tests/oracle/capture"
MENU = ROOT / "site/docs/menu.json"
SECTIONS = ROOT / "site/docs/sections"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
RAW = {"script", "style"}
BOOLEAN = {"open", "checked", "disabled", "readonly", "required", "selected", "hidden", "multiple", "autofocus",
           "novalidate", "inert", "async", "defer", "nomodule", "playsinline", "muted", "controls", "loop", "reversed"}
BLOCK = {"address", "article", "aside", "blockquote", "caption", "colgroup", "dd", "details", "dialog", "div", "dl",
         "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
         "hgroup", "hr", "legend", "li", "main", "menu", "nav", "ol", "optgroup", "option", "p", "pre", "search",
         "section", "summary", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul"}
NO_BREAKS = {"pre", "textarea", "code", "svg", "math", "select"}
DROPPED = ("/docs/classless", "/docs/conditional", "/docs/sass", "/docs/maintenance", "/docs/v2", "/docs/mission",
           "/docs/usage-scenarios", "/docs/brand", "/docs/built-with", "/docs/v1")
HINTS = {"preload", "modulepreload", "prefetch", "preconnect", "dns-prefetch", "prerender"}
ATTR = re.compile(r"""([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")
ASSET = re.compile(r"/build/_assets/([\w.-]+?)-[A-Z0-9]{8}(\.\w+)")


class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, attrs or [], parent, []

    def attr(self, name):
        return next((v for k, v in self.attrs if k.lower() == name), None)

    def elements(self):
        return [c for c in self.children if isinstance(c, Node)]

    def text(self):
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def label(self):
        bits = [self.tag]
        if self.attr("id"):
            bits.append("#" + self.attr("id"))
        if self.attr("class"):
            bits.append("." + ".".join(self.attr("class").split()))
        return "".join(bits)


class Tree(HTMLParser):
    """A DOM from a browser's serialization: every non-void element is closed explicitly. Tag and
    attribute names keep their case (SVG's viewBox, clipPath) from the start tag's own text."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = self.cur = Node("#root")
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        name = re.match(r"<([^\s/>]+)", raw).group(1)
        body = raw[len(name) + 1:].rstrip(">").rstrip("/")
        parsed = [(m.group(1), html.unescape(next((g for g in m.groups()[1:] if g is not None), "")))
                  for m in ATTR.finditer(body)]
        node = Node(name, parsed, self.cur)
        self.cur.children.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.cur = self.cur.parent

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag.lower() != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        self.cur.children.append(data)


def find(node, pred):
    for c in node.elements():
        if pred(c):
            return c
        hit = find(c, pred)
        if hit:
            return hit
    return None


def region(path_html):
    """The children of <main> that make up the route's content."""
    doc = Tree(path_html.read_text(encoding="utf-8")).root
    main = find(doc, lambda n: n.tag == "main")
    if main is None:
        sys.exit(f"convert: {path_html} has no <main>")
    kids = main.children
    menu = next((i for i, c in enumerate(kids) if isinstance(c, Node) and c.attr("id") == "documentation-menu"), None)
    return kids[menu + 1:] if menu is not None else kids


def clean(nodes, notes, in_toc=False):
    out = []
    for c in nodes:
        if isinstance(c, str):
            out.append(c)
            continue
        tag = c.tag.lower()
        if tag == "script" or (tag == "link" and set((c.attr("rel") or "").lower().split()) & HINTS):
            notes["dropped"].append(c.label())
            continue
        toc = in_toc or c.attr("id") == "table-of-contents"
        attrs = []
        for k, v in c.attrs:
            if toc and tag == "a" and k == "aria-current":
                notes["toc"] += 1
                continue
            if ASSET.search(v):
                new = ASSET.sub(lambda m: f"/assets/{'brand' if m.group(1).startswith(('femto-logo', 'femto-mark')) else 'img'}/"
                                          f"{m.group(1)}{m.group(2)}", v)
                notes["assets"].append(f"{c.label()} {k}: {v} -> {new}")
                v = new
            if tag == "a" and k == "href" and v.split("#")[0].rstrip("/") in DROPPED:
                notes["dropped_routes"].append(f"{c.label()} href={v} {c.text().strip()[:60]!r}")
            attrs.append((k, v))
        node = Node(c.tag, attrs, None)
        cls = (c.attr("class") or "").split()
        lang = next((x for x in cls if x.startswith("language-")), None)
        if tag == "code" and lang:
            node.children = [c.text()]
            notes["code"] += 1
        else:
            node.children = clean(c.children, notes, toc)
        out.append(node)
    # Comments never reach the tree (HTMLParser.handle_comment is not overridden).
    return out


def esc_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")


def esc_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace(" ", "&nbsp;")


def start(n):
    parts = [n.tag]
    for k, v in n.attrs:
        parts.append(k if v == "" and k.lower() in BOOLEAN else f'{k}="{esc_attr(v)}"')
    return "<" + " ".join(parts) + ">"


def breakable(n, raw):
    """Children may go on their own lines: all elements of block tags, no text but whitespace."""
    if raw or n.tag.lower() in NO_BREAKS:
        return False
    kids = n.children
    return bool(kids) and all(isinstance(c, Node) and c.tag.lower() in BLOCK for c in kids)


def serialize(n, depth, raw):
    tag = n.tag.lower()
    if tag in VOID:
        return start(n)
    if tag in RAW:
        return start(n) + "".join(n.children) + f"</{n.tag}>"
    if breakable(n, raw):
        pad = "\n" + "  " * (depth + 1)
        inner = "".join(pad + serialize(c, depth + 1, raw) for c in n.children) + "\n" + "  " * depth
    else:
        inner = "".join(esc_text(c) if isinstance(c, str) else serialize(c, depth, True if tag in NO_BREAKS else raw)
                        for c in n.children)
    return start(n) + inner + f"</{n.tag}>"


def slug_of(route):
    s = route.strip("/").replace("/", "--")
    return s or "index"


def default_out(route):
    menu = json.loads(MENU.read_text(encoding="utf-8"))
    for cat in menu["categories"]:
        for s in cat["sections"]:
            if s["route"] == route:
                return SECTIONS / f"{s['id']}.html"
            for v in s.get("variants", []):
                if v["route"] == route:
                    return SECTIONS / s["id"] / f"{route.rsplit('/', 1)[1]}.html"
    return None


def flat(nodes, path="", out=None):
    """(path, tag, attrs, own text) for every element, in tree order."""
    out = [] if out is None else out
    k = 0
    for c in nodes:
        if isinstance(c, Node):
            p = f"{path} > {c.label()}:{k}" if path else f"{c.label()}:{k}"
            own = re.sub(r"\s+", " ", "".join(x for x in c.children if isinstance(x, str))).strip()
            out.append((p, c.tag.lower(), dict(c.attrs), own))
            k += 1
            flat(c.children, p, out)
    return out


def report(route, base, limit=60):
    slug = slug_of(route)
    a = flat(base)
    for name, why in (("server.html", "before hydration -> hydrated: set by JavaScript at load"),
                      ("dom-dark.html", "light -> prefers-color-scheme dark: follows the scheme"),
                      ("dom-375.html", "1300 px -> 375 px: follows the width")):
        p = CAPTURE / slug / name
        if not p.exists():
            continue
        b = flat(region(p))
        first, second = (b, a) if name == "server.html" else (a, b)
        lines = []
        sm = difflib.SequenceMatcher(None, [x[1] for x in first], [x[1] for x in second], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal":
                lines.append(f"  structure {op}: {[x[0] for x in first[i1:i2]][:3]} -> {[x[0] for x in second[j1:j2]][:3]}")
                continue
            for x, y in zip(first[i1:i2], second[j1:j2]):
                for k in sorted(set(x[2]) | set(y[2])):
                    if x[2].get(k) != y[2].get(k):
                        lines.append(f"  {y[0]}  [{k}] {x[2].get(k)!r} -> {y[2].get(k)!r}")
                if x[3] != y[3]:
                    lines.append(f"  {y[0]}  text {x[3][:60]!r} -> {y[3][:60]!r}")
        print(f"{name}: {why}: {len(lines)} difference(s)", file=sys.stderr)
        for line in lines[:limit]:
            print(line, file=sys.stderr)
        if len(lines) > limit:
            print(f"  ... {len(lines) - limit} more", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("route", help="the oracle route, e.g. /docs/forms/input")
    ap.add_argument("--out", help="output file, - for stdout (default: the route's section file)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output file")
    ap.add_argument("--raw", action="store_true", help="add no line breaks")
    ap.add_argument("--report", action="store_true", help="list the state the oracle's JavaScript set")
    args = ap.parse_args(argv)
    route = "/" + args.route.strip("/") if args.route.strip("/") else "/"
    src = CAPTURE / slug_of(route) / "dom.html"
    if not src.exists():
        sys.exit(f"convert: no capture {src.relative_to(ROOT)} (run uv run tests/run.py oracle)")
    out = Path(args.out) if args.out and args.out != "-" else (None if args.out == "-" else default_out(route))
    if args.out is None and out is None:
        sys.exit(f"convert: {route} is not a section or variant route in site/docs/menu.json; give --out FILE or --out -")
    notes = {"dropped": [], "assets": [], "dropped_routes": [], "toc": 0, "code": 0}
    nodes = clean(region(src), notes)
    while nodes and isinstance(nodes[0], str) and not nodes[0].strip():
        nodes.pop(0)
    text = "".join(esc_text(c) if isinstance(c, str) else serialize(c, 0, args.raw) + ("" if args.raw else "\n")
                   for c in nodes if not (isinstance(c, str) and not c.strip() and not args.raw))
    if out is None:
        sys.stdout.write(text)
    else:
        out = out if out.is_absolute() else (Path.cwd() / out)
        if out.exists() and not args.force:
            sys.exit(f"convert: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} exists (hand edits?); --force overwrites it")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    where = "stdout" if out is None else (out.relative_to(ROOT) if out.is_relative_to(ROOT) else out)
    print(f"convert: {route} -> {where}: {notes['code']} code blocks as text, {notes['toc']} TOC aria-current dropped, "
          f"{len(notes['dropped'])} scripts and fetch hints dropped", file=sys.stderr)
    for line in notes["assets"]:
        print(f"  asset URL rewritten (an attribute difference): {line}", file=sys.stderr)
    for line in notes["dropped_routes"]:
        print(f"  link to a dropped route (Decision 5; remove it or point it at /docs, register dropped-route): {line}",
              file=sys.stderr)
    if args.report:
        report(route, region(src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
