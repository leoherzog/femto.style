"""Divergence registry: tests/divergences/*.json (every file but schema.json).

Each file is a JSON array of entries. Every difference the harness finds must match at least one
entry, or the run fails. tests/divergences/schema.json and tests/README.md document the fields.
Element records (structure, attribute, text, style) and head records are matched in the page
(differ.js), because selectors are evaluated against the documents; this module validates entries,
filters them per cell with `where`, and matches status records and skipped checks.

Three rules keep the registry from hiding what it should not:
- Self comparisons (criterion 1, "zero differences") apply skipped-check entries only: no element,
  head or status entry ever registers a difference between the oracle and itself.
- Breadth (an entry must be specific). It is judged on what the entry would actually match, not on
  how its patterns are written: its selector, path and route scope are evaluated on the reference
  documents (the oracle's captured DOMs in tests/oracle/capture/, the fixture site under every
  control, and dist/ once it is built plus any dist:<path> folder a run serves, page sources read
  with the HTML standard's tree construction; see _reference_docs), its path patterns with
  JavaScript's RegExp, the engine differ.js applies them with (_js_regexes). Every element or head
  entry, route-scoped or not, reaches at most DOC_SHARE_MAX of the compared elements (head: head
  keys) of any one document, and together with every other entry of its kind at most UNION_DOC_MAX
  (past DOC_FLOOR elements). An entry that is not route-scoped (where.routes naming at most
  ROUTE_SCOPE_MAX routes; items are routes or ^-regexes, never "*") also reaches at most
  SITE_SHARE_MAX of a whole site's compared elements over the routes in its scope, and those
  entries together at most UNION_SITE_MAX. All the entries of a kind share a budget of
  UNION_SITE_MAX of each whole site (_kind_budget). Site shares count only complete sites: the
  oracle's 64 routes and a dist build that holds every kept route, so a partial build never
  decides them. At most ROUTE_SCOPE_MAX routes without a reference document may be named, in one
  entry or in the whole registry. A status entry must name at most ROUTE_SCOPE_MAX routes. A
  skipped-check entry must name one or two browsers and at most SKIP_CHECKS_MAX known checks.
- An entry the validator rejects is not applied: it registers nothing, so the differences it would
  have hidden are reported as unregistered, besides the registry error that fails the run.

differ.js applies the same per-document limits again in every cell, on the live documents
(limits()): an entry or a kind that reaches too much of either side's document there is a harness
error and is not applied in that cell, and the registered records of a cell may cover at most
COVER_MAX of either document. That catches what a static read cannot see: markup a script adds, and
a page the other side does not have.
"""
import hashlib
import html.parser
import json
import re
import subprocess
from pathlib import Path

from .paths import DIVERGENCES, FIXTURES, MASKS, REPO, TESTS

KINDS = ("structure", "attribute", "text", "style", "head", "status", "skipped-check")
ELEMENT_KINDS = ("structure", "attribute", "text", "style")
PAGE_KINDS = ELEMENT_KINDS + ("head",)  # matched in the page by differ.js
CATEGORIES = ("dropped-route", "femto-divergence", "merge-layout", "id-rename", "oracle-bug", "highlight",
              "asset-path", "browser-limit", "owner-change")
WHERE_KEYS = ("browsers", "routes", "schemes", "widths", "comparisons")
BROWSERS = ("chrome", "firefox", "safari")
SCHEMES = ("light", "dark", "theme-light", "theme-dark")
COMPARISONS = ("self", "pages")
PSEUDOS = ("", "::before", "::after", "::marker", "::placeholder", "::file-selector-button", "::backdrop")
FIELDS = ("id", "kind", "selector", "path", "pseudo", "property", "a", "b", "check", "where", "category", "reason",
          "notes")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# Breadth limits (tests/README.md, Divergence registry, Breadth).
# A route-scoped entry names a page or two (and their 404 or redirect); more than this many routes
# wholesale is no longer one explained difference.
ROUTE_SCOPE_MAX = 3
# Share of the compared elements over the oracle's routes in the entry's scope (one document variant
# at a time). Narrow entries in sight (a dropped side-nav item, one component, one code token kind,
# the og:url meta) stay under 1%; the review's catch-alls reach 100%, `main *` 82%, `pre *` 46%.
SITE_SHARE_MAX = {"element": 0.05, "head": 0.10}  # the head has about 20 keys a page: 10% is two
# Share of any one document's compared elements (head: keys), so a selector cannot concentrate on a
# page (a route scope written as a selector, such as `:root:has(...) *`).
DOC_SHARE_MAX = 0.25
# All entries of one kind together: in one document (route-scoped ones included), and over a whole
# site (those that are not route-scoped; the kind budget adds the route-scoped ones), so a catch-all
# split into many narrow entries, by selector or by route, is caught as well.
UNION_SITE_MAX = 0.25
UNION_DOC_MAX = 0.50
# A document share counts only past this many elements (head: keys): a text/plain 404 has three
# compared elements (html, body, pre), and an entry for its body is not a catch-all.
DOC_FLOOR = 4
# In a cell (differ.js): the registered records together may cover at most this share of either
# document's compared elements (a structure record covers its whole subtree) or head keys. A page
# one side does not have is mostly one structure record, however narrow the entries.
COVER_MAX = 0.25
# The checks a session can skip (compare.py): the media legs and the collected pseudo-elements.
KNOWN_CHECKS = ("media:light", "media:dark") + tuple(f"pseudo:{p}" for p in PSEUDOS if p)
# One limit is one leg or one pseudo-element; the media pair is the widest (Safari runs one media
# leg per pass).
SKIP_CHECKS_MAX = 2

ORACLE_ROUTES = TESTS / "oracle-routes.json"
CAPTURE = TESTS / "oracle" / "capture"
DIST = REPO / "dist"
FIXTURE_SITE = FIXTURES / "site"
FIXTURE_ROUTES = ("/index.html", "/other.html")


# \Z, not $: "/x/\n" is no regex in differ.js (isRe), so it must not be one here either.
REGEX_RE = re.compile(r"^/(.+)/([imsu]*)\Z", re.S)
# Fields differ.js matches with JavaScript's RegExp (element and head records); the rest (routes,
# status records, skipped checks) are matched here, with Python's re.
JS_FIELDS = ("path", "pseudo", "property", "a", "b")

# Python's re and JavaScript's RegExp read some patterns differently (\Z and \A are anchors in
# Python and the letters Z and A in JavaScript without the u flag; {,2} is a quantifier in Python
# 3.13 and literal text in JavaScript), so a pattern differ.js applies is checked and judged with
# JavaScript itself: one node process per call, every pattern against every value.
_NODE_REGEXES = r"""
let s = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { s += d; });
process.stdin.on("end", () => {
  const { patterns, values } = JSON.parse(s);
  const out = {};
  for (const p of patterns) {
    const k = p.lastIndexOf("/");
    let re;
    try { re = new RegExp(p.slice(1, k), p.slice(k + 1)); }
    catch (e) { out[p] = { error: String((e && e.message) || e) }; continue; }
    if (!values) { out[p] = { ok: true }; continue; }
    const hits = [];
    for (let i = 0; i < values.length; i++) if (re.test(values[i])) hits.push(i);
    out[p] = { hits };
  }
  process.stdout.write(JSON.stringify(out));
});
"""


def _js_regexes(patterns, values=None):
    """JavaScript's reading of /body/flags patterns, as differ.js's strPat() builds them:
    {pattern: {"error": message} | {"ok": True} | {"hits": [indices of the values it matches]}}.
    Raises RuntimeError when node cannot run it."""
    try:
        proc = subprocess.run(["node", "-e", _NODE_REGEXES], input=json.dumps({"patterns": list(patterns), "values": values}),
                              capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"node cannot run: {e}") from None
    if proc.returncode != 0:
        raise RuntimeError(f"node exited {proc.returncode}: {proc.stderr.strip()[-300:]}")
    return json.loads(proc.stdout)


def _is_regex(v, route=False):
    """A pattern is a regex when written /body/flags (flags from i, m, s, u). Route patterns
    (where.routes, a status entry's path) start with / themselves, so there a regex must also start
    with ^ (for example /^.docs.forms/): /docs/forms/input is the route, never a regex."""
    if not isinstance(v, str) or not REGEX_RE.match(v):
        return False
    return v.startswith("/^") if route else True


def _check_pattern(v, field, errs, where, nullable=False, route=False, js=None):
    """js: a list to collect (field, pattern) in, for a field differ.js applies: those are checked
    with JavaScript's RegExp (Registry), not Python's re."""
    if v is None:
        if not nullable:
            errs.append(f"{where}: {field} must be a string")
        return
    if not isinstance(v, str):
        errs.append(f"{where}: {field} must be a string" + (" or null" if nullable else ""))
        return
    if _is_regex(v, route):
        if js is not None:
            js.append((field, v))
            return
        k = v.rfind("/")
        try:
            re.compile(v[1:k])
        except re.error as e:
            errs.append(f"{where}: {field} is not a valid regex: {e}")


def _pattern_match(pat, value, present=True, route=False) -> bool:
    """Patterns: omitted (present=False) or "*" any, null absent, "/re/flags" regex, else exact."""
    if not present or pat == "*":
        return True
    if pat is None:
        return value is None
    if value is None:
        return False
    if _is_regex(pat, route):
        k = pat.rfind("/")
        flags = (re.I if "i" in pat[k + 1:] else 0) | (re.M if "m" in pat[k + 1:] else 0) | (re.S if "s" in pat[k + 1:] else 0)
        return re.search(pat[1:k], value, flags) is not None
    return pat == value


def _route_match(pat, route) -> bool:
    """A where.routes item: an exact route or a /^regex/; never a wildcard (validate_entry rejects
    anything else, and this matcher never treats "*" as one)."""
    if not isinstance(pat, str):
        return False
    if _is_regex(pat, route=True):
        return _pattern_match(pat, route, route=True)
    return pat == route


def validate_entry(e, where, errs, ids, js=None):
    """js: a list that collects the entry's (field, regex) pairs that differ.js applies (element and
    head entries), for the caller to check with JavaScript."""
    if not isinstance(e, dict):
        errs.append(f"{where}: entry is not an object")
        return
    for k in e:
        if k not in FIELDS:
            errs.append(f"{where}: unknown field {k!r}")
    eid = e.get("id")
    if not isinstance(eid, str) or not ID_RE.match(eid):
        errs.append(f"{where}: id must match {ID_RE.pattern}")
    elif eid in ids:
        errs.append(f"{where}: duplicate id {eid!r} (also in {ids[eid]})")
    else:
        ids[eid] = where
    where = f"{where} [{eid}]"
    kind = e.get("kind")
    if kind not in KINDS:
        errs.append(f"{where}: kind must be one of {', '.join(KINDS)}")
    if e.get("category") not in CATEGORIES:
        errs.append(f"{where}: category must be one of {', '.join(CATEGORIES)}")
    if not isinstance(e.get("reason"), str) or not e["reason"].strip():
        errs.append(f"{where}: reason must be a non-empty string")
    if "notes" in e and not isinstance(e["notes"], str):
        errs.append(f"{where}: notes must be a string")
    if kind in ELEMENT_KINDS and "selector" not in e and "path" not in e:
        errs.append(f"{where}: {kind} entries need selector or path")
    if kind in ("style", "attribute", "head") and "property" not in e:
        errs.append(f"{where}: {kind} entries need property (the longhand, attribute name or head value)")
    if kind == "head":
        if "path" not in e:
            errs.append(f"{where}: head entries need path (the head key: title, meta[name=description], link[rel=canonical], ...)")
        if "selector" in e:
            errs.append(f"{where}: head entries take path (the head key), not selector")
    if kind == "skipped-check":
        if "check" not in e:
            errs.append(f"{where}: skipped-check entries need check")
        if e.get("category") != "browser-limit":
            errs.append(f"{where}: skipped-check entries use category browser-limit")
        for f in ("selector", "path", "pseudo", "property", "a", "b"):
            if f in e:
                errs.append(f"{where}: skipped-check entries take no {f}")
    elif "check" in e:
        errs.append(f"{where}: only skipped-check entries take check")
    if "pseudo" in e and kind != "style":
        errs.append(f"{where}: only style entries take pseudo")
    if kind == "status" and ("selector" in e or "property" in e):
        errs.append(f"{where}: status entries take path (the route) but no selector or property")
    if "selector" in e and (not isinstance(e["selector"], str) or not e["selector"].strip()):
        errs.append(f"{where}: selector must be a non-empty string")
    in_page = js if kind in PAGE_KINDS else None
    for f in ("path", "pseudo", "property", "check"):
        if f in e:
            _check_pattern(e[f], f, errs, where, route=(f == "path" and kind == "status"),
                           js=in_page if f in JS_FIELDS else None)
    if kind == "status" and isinstance(e.get("path"), str) and e["path"] != "*" and not _is_regex(e["path"], route=True) \
            and not e["path"].startswith("/"):
        errs.append(f"{where}: a status entry's path is a route (starting with /), * or a /^regex/, not {e['path']!r}")
    for f in ("a", "b"):
        if f in e:
            _check_pattern(e[f], f, errs, where, nullable=True, js=in_page)
    w = e.get("where", {})
    if not isinstance(w, dict):
        errs.append(f"{where}: where must be an object")
        return
    for k, v in w.items():
        if k not in WHERE_KEYS:
            errs.append(f"{where}: unknown where key {k!r} (allowed: {', '.join(WHERE_KEYS)})")
        elif not isinstance(v, list) or not v:
            errs.append(f"{where}: where.{k} must be a non-empty list")
        elif k == "widths":
            for x in v:
                if not (isinstance(x, int) or (isinstance(x, dict) and set(x) <= {"min", "max"} and x)):
                    errs.append(f"{where}: where.widths items are integers or {{min, max}} objects")
        elif k == "browsers" and set(v) - set(BROWSERS):
            errs.append(f"{where}: where.browsers items are {', '.join(BROWSERS)}")
        elif k == "schemes" and set(v) - set(SCHEMES):
            errs.append(f"{where}: where.schemes items are {', '.join(SCHEMES)}")
        elif k == "comparisons" and set(v) - set(COMPARISONS):
            errs.append(f"{where}: where.comparisons items are {', '.join(COMPARISONS)}")
        elif k == "comparisons" and "self" in v and kind != "skipped-check":
            errs.append(f"{where}: only skipped-check entries apply to self comparisons (criterion 1 asks for zero "
                        "differences between the oracle and itself)")
        elif k == "routes":
            for x in v:
                if not isinstance(x, str):
                    errs.append(f"{where}: where.routes items must be strings")
                elif not _is_regex(x, route=True) and not x.startswith("/"):
                    # "*" or any other word is not a route: where.routes names routes (/docs/forms) or
                    # matches them with a /^regex/, which the breadth rule counts.
                    errs.append(f"{where}: where.routes item {x!r} is not a route: name an exact route (starting with "
                                "/) or a /^regex/ (tests/README.md, Divergence registry)")
                else:
                    _check_pattern(x, "where.routes item", errs, where, route=True)


# =============================================================================================
# Breadth: what an entry would actually match.
#
# Element and head entries are evaluated on the reference documents with a stdlib HTML tree and a
# CSS selector engine, built to give the same tree paths, compared elements and head keys as
# differ.js. Selectors use Kleene logic: a pseudo-class a static document cannot settle (:hover,
# :checked, :open, :user-invalid, :host, ...) is "unknown" and counts as a match, so an entry's
# reach is never under-stated.
# =============================================================================================
_VOID = frozenset("area base br col embed hr img input link meta param source track wbr keygen basefont bgsound "
                  "frame".split())
_SVG_CASE = {t.lower(): t for t in (
    "altGlyph altGlyphDef altGlyphItem animateColor animateMotion animateTransform clipPath feBlend feColorMatrix "
    "feComponentTransfer feComposite feConvolveMatrix feDiffuseLighting feDisplacementMap feDistantLight "
    "feDropShadow feFlood feFuncA feFuncB feFuncG feFuncR feGaussianBlur feImage feMerge feMergeNode feMorphology "
    "feOffset fePointLight feSpecularLighting feSpotLight feTile feTurbulence foreignObject glyphRef "
    "linearGradient radialGradient textPath").split()}
# As differ.js: skipped in the tree (never compared, never counted in a path index).
SKIP_TAGS = frozenset(("head", "meta", "title", "script", "link", "style", "template", "base", "noscript"))
HARNESS_TAGS = frozenset(("harness-mq", "harness-cover"))
_HEAD_SKIP_RELS = frozenset(("stylesheet", "preload", "modulepreload", "prefetch", "preconnect", "dns-prefetch",
                             "prerender"))
_JS_TYPES = frozenset(("", "module", "application/ecmascript", "application/javascript", "application/x-ecmascript",
                       "application/x-javascript", "text/ecmascript", "text/javascript", "text/javascript1.0",
                       "text/javascript1.1", "text/javascript1.2", "text/javascript1.3", "text/javascript1.4",
                       "text/javascript1.5", "text/jscript", "text/livescript", "text/x-ecmascript",
                       "text/x-javascript"))


def _js_json(v):
    """JSON.stringify of a leaf as differ.js gives it (integral floats print as integers)."""
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e21:
        v = int(v)
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def _flatten_json(v, path, out):
    """differ.js flattenJson(): one value per leaf, keyed $.a.b[2]."""
    if isinstance(v, list):
        if not v:
            out[path] = "[]"
        for i, x in enumerate(v):
            _flatten_json(x, f"{path}[{i}]", out)
    elif isinstance(v, dict):
        if not v:
            out[path] = "{}"
        for k, x in v.items():
            step = "." + k if re.fullmatch(r"[A-Za-z_$@][\w$@-]*", k, re.A) else "[" + json.dumps(k, ensure_ascii=False) + "]"
            _flatten_json(x, path + step, out)
    else:
        out[path] = _js_json(v)


def _no_constant(name):
    raise ValueError(f"{name} is not JSON")


def _data_block_canon(ty, attrs, text):
    """A data block's compared value as differ.js collectHead() builds it (its attributes but type,
    then its JSON leaves or its text), canonicalized, so two blocks compare equal exactly when
    differ.js counts the second as a copy of the first."""
    vals = {k: v for k, v in attrs.items() if k != "type"}
    parsed = None
    if re.search(r"(^|[/+])json$", ty) or ty in ("importmap", "speculationrules"):
        try:
            parsed = (json.loads(text, parse_constant=_no_constant),)
        except ValueError:
            parsed = None
    if parsed is not None:
        _flatten_json(parsed[0], "$", vals)
    else:
        vals["(text)"] = text
    return json.dumps(sorted(vals.items()), ensure_ascii=False)


class _El:
    __slots__ =("tag", "attrs", "parent", "kids", "ns", "inert", "empty", "text", "classes", "pos", "n", "tpos",
                 "tn", "path", "ci")

    def __init__(self, tag, attrs, parent, ns, inert):
        self.tag, self.attrs, self.parent, self.ns, self.inert = tag, attrs, parent, ns, inert
        self.kids, self.text, self.empty = [], [], True
        self.classes = frozenset((attrs.get("class") or "").split())
        self.pos = self.n = self.tpos = self.tn = 1
        self.path, self.ci = None, None


_MATHML_TEXT_IP = frozenset(("mi", "mo", "mn", "ms", "mtext"))
_SVG_HTML_IP = frozenset(("foreignObject", "desc", "title"))


def _html_ip(el):
    """An HTML integration point (13.2.6.5): SVG foreignObject, desc and title, and MathML
    annotation-xml whose encoding is text/html or application/xhtml+xml."""
    if el.ns == "svg":
        return el.tag in _SVG_HTML_IP
    if el.ns == "math":
        return el.tag == "annotation-xml" and (el.attrs.get("encoding") or "").lower() in ("text/html",
                                                                                          "application/xhtml+xml")
    return False


def _html_rules(cur, tag):
    """Whether a start tag under cur is processed by the HTML rules (cur is an HTML element, an HTML
    integration point, or a MathML text integration point for anything but mglyph and malignmark),
    rather than by the rules for foreign content."""
    if cur is None or cur.ns == "html" or _html_ip(cur):
        return True
    return cur.ns == "math" and cur.tag in _MATHML_TEXT_IP and tag not in ("mglyph", "malignmark")


def _child_ns(parent, tag):
    """The namespace of the element a start tag inserts under parent: svg and math start foreign
    content, which goes on until an integration point."""
    if _html_rules(parent, tag):
        return "svg" if tag == "svg" else "math" if tag == "math" else "html"
    if parent.ns == "math" and parent.tag == "annotation-xml" and tag == "svg":
        return "svg"
    return parent.ns


class _Builder(html.parser.HTMLParser):
    """The element tree of a serialized DOM (outerHTML: the oracle capture). End tags are explicit
    there, so no implied-tag rules are needed; <template> content is inert, as in the DOM. Static
    pages use _StaticBuilder."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root, self.stack, self.all = None, [], []

    def _open(self, tag, attrs, selfclosing):
        parent = self.stack[-1] if self.stack else None
        ns = _child_ns(parent, tag)
        a = {}
        for k, v in attrs:
            if k not in a:
                a[k] = "" if v is None else v
        # <template> content is inert, and <noscript> content is text while scripts run (both
        # browsers run them): neither is an element of the document.
        inert = parent is not None and (parent.inert or parent.tag in ("template", "noscript"))
        el = _El(_SVG_CASE.get(tag, tag) if ns == "svg" else tag, a, parent, ns, inert)
        if parent is None:
            if self.root is not None:
                return
            self.root = el
        elif not inert:
            parent.kids.append(el)
            if parent.tag != "template":
                parent.empty = False
        self.all.append(el)
        if not ((ns == "html" and tag in _VOID) or (selfclosing and ns != "html")):
            self.stack.append(el)

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.stack[k].tag.lower() == tag:
                del self.stack[k:]
                return

    def handle_data(self, data):
        if self.stack and data:
            top = self.stack[-1]
            if not top.inert and top.tag != "template":
                top.text.append(data)
                top.empty = False


# HTML tree construction for static pages (the HTML standard, 13.2.6), the rules valid pages lean on.
_HEAD_ONLY = frozenset("base basefont bgsound link meta noscript script style template title".split())
_CLOSES_P = frozenset(("address article aside blockquote center details dialog dir div dl fieldset figcaption figure "
                       "footer header hgroup main menu nav ol p search section summary ul h1 h2 h3 h4 h5 h6 pre listing "
                       "form li dd dt plaintext table hr xmp").split())
_HEADINGS = frozenset("h1 h2 h3 h4 h5 h6".split())
# The "special" category: an end tag never closes past one of these, and li, dd and dt stop there.
_SPECIAL = frozenset(("address applet area article aside base basefont bgsound blockquote body br button caption "
                      "center col colgroup dd details dir div dl dt embed fieldset figcaption figure footer form frame "
                      "frameset h1 h2 h3 h4 h5 h6 head header hgroup hr html iframe img input keygen li link listing "
                      "main marquee menu meta nav noembed noframes noscript object ol p param plaintext pre script search "
                      "section select source style summary table tbody td template textarea tfoot th thead title tr "
                      "track ul wbr xmp").split())
# Scope boundaries ("has an element in scope"); button scope adds button, list item scope ol and ul,
# table scope is only html, table and template.
_SCOPE = frozenset("applet caption html table td th marquee object template".split())  # HTML elements; see
# _scope_boundary for the SVG and MathML ones


def _scope_boundary(el, extra=()):
    """An element that ends the search of "has an element in scope": applet, caption, html, table,
    td, th, marquee, object and template; MathML mi, mo, mn, ms, mtext and annotation-xml; SVG
    foreignObject, desc and title; and extra (HTML) ones."""
    if el.ns == "svg":
        return el.tag in _SVG_HTML_IP
    if el.ns == "math":
        return el.tag in _MATHML_TEXT_IP or el.tag == "annotation-xml"
    return el.tag in _SCOPE or el.tag in extra
_IMPLIED_END = frozenset("dd dt li optgroup option p rb rp rt rtc".split())
# Start tags that end SVG content and go back to HTML (13.2.6.5, any other start tag in foreign content).
_SVG_BREAKOUT = frozenset(("b big blockquote body br center code dd div dl dt em embed h1 h2 h3 h4 h5 h6 head hr i img li "
                           "listing menu meta nobr ol p pre ruby s small span strong strike sub sup table tt u ul "
                           "var").split())
_TABLE_SECTIONS = frozenset(("tbody", "thead", "tfoot"))
_TABLE_PARTS = _TABLE_SECTIONS | {"table", "tr", "td", "th", "caption", "colgroup"}
# End tags that close their element and the implied end tags open in it, when it is in scope.
_BLOCK_END = frozenset(("address article aside blockquote button center details dialog dir div dl fieldset figcaption "
                        "figure footer form header hgroup listing main menu nav ol pre search section summary ul li dd "
                        "dt p").split()) | _HEADINGS


def _is_special(el):
    """The "special" category: HTML's _SPECIAL elements, MathML mi, mo, mn, ms, mtext and
    annotation-xml, SVG foreignObject, desc and title."""
    if el.ns == "html":
        return el.tag in _SPECIAL
    return _scope_boundary(el)


class _StaticBuilder(_Builder):
    """The element tree of a static page as a browser builds it: _Builder plus the HTML standard's
    tree-construction rules that valid pages use: implied html, head and body; head-only elements
    before the body in head; p closed by a block start tag; li, dd, dt, option and table cells and
    rows closed by the next one; tbody, tr and colgroup implied in tables; end tags that never close
    past a special element, and </template> closing all that is open in its template; ruby; SVG and
    MathML content, its integration points (SVG foreignObject, desc and title; MathML annotation-xml
    with an HTML encoding, and mi, mo, mn, ms and mtext for HTML content) and its end by an HTML
    start tag. Not modelled (none occurs in a valid page): the adoption agency for misnested
    formatting, foster parenting of content misplaced in tables, and the quirks-mode table rule."""

    def __init__(self):
        super().__init__()
        self.head = self.body = None

    # -- the stack ----------------------------------------------------------------------------------
    def _cur(self):
        return self.stack[-1] if self.stack else None

    @staticmethod
    def _in_noscript(el):
        while el is not None:
            if el.tag == "noscript":
                return True
            el = el.parent
        return False

    def _in_scope(self, names, extra=()):
        for el in reversed(self.stack):
            if el.ns == "html" and el.tag in names:
                return True
            if _scope_boundary(el, extra):
                return False
        return False

    def _in_table_scope(self, names):
        for el in reversed(self.stack):
            if el.ns == "html" and el.tag in names:
                return True
            if el.ns == "html" and el.tag in ("html", "table", "template"):
                return False
        return False

    def _pop_until(self, names):
        while self.stack:
            el = self.stack.pop()
            if el.ns == "html" and el.tag in names:
                return

    def _implied_end(self, keep=()):
        while self.stack and self.stack[-1].ns == "html" and self.stack[-1].tag in _IMPLIED_END \
                and self.stack[-1].tag not in keep:
            self.stack.pop()

    def _close_p(self):
        if self._in_scope({"p"}, extra=("button",)):
            self._implied_end(keep=("p",))
            self._pop_until({"p"})

    def _raw_open(self, tag, attrs=(), selfclosing=False):
        super()._open(tag, list(attrs), selfclosing)
        return self.all[-1]

    def _ensure_html(self):
        if self.root is None:
            self._raw_open("html")

    def _ensure_head(self):
        self._ensure_html()
        if self.head is None:
            del self.stack[1:]
            self.head = self._raw_open("head")

    def _ensure_body(self):
        self._ensure_head()
        if self.body is None:
            del self.stack[1:]
            self.body = self._raw_open("body")

    # -- tokens -------------------------------------------------------------------------------------
    def _open(self, tag, attrs, selfclosing):
        cur = self._cur()
        if not _html_rules(cur, tag):
            # Foreign content (SVG, MathML; 13.2.6.5): one of these HTML start tags ends it, back to
            # the nearest HTML element or integration point; any other tag is a foreign element.
            if not (tag in _SVG_BREAKOUT or (tag == "font" and any(k in ("color", "face", "size") for k, _ in attrs))):
                return super()._open(tag, attrs, selfclosing)
            while self.stack and not _html_rules(self.stack[-1], tag):
                self.stack.pop()
            cur = self._cur()
        if cur is not None and (cur.inert or (cur.ns == "html" and cur.tag in ("template", "noscript"))) \
                and tag not in ("html", "head", "body"):
            # Inert content: <template>'s (its own elements are the scope of the body rules) and
            # <noscript>'s (text while scripts run: no rules, nothing closed)
            if not self._in_noscript(cur):
                self._body_rules(tag)
            return super()._open(tag, attrs, selfclosing)
        if tag == "html":
            if self.root is None:
                return super()._open(tag, attrs, selfclosing)
            for k, v in attrs:  # a later <html> adds its attributes
                self.root.attrs.setdefault(k, "" if v is None else v)
            return
        if tag == "head":
            if self.head is None and self.body is None:
                self._ensure_html()
                self.head = self._raw_open("head", attrs)
            return
        if tag == "body":
            if self.body is None:
                self._ensure_head()
                del self.stack[1:]
                self.body = self._raw_open("body", attrs)
            else:
                for k, v in attrs:
                    self.body.attrs.setdefault(k, "" if v is None else v)
            return
        if self.body is None:
            if tag in _HEAD_ONLY:
                self._ensure_head()
                if self.stack[-1] is not self.head and self.stack[-1].tag not in ("template", "noscript"):
                    self.stack.append(self.head)  # after </head>, a head-only element still goes in head
                    super()._open(tag, attrs, selfclosing)
                    if self.stack and self.stack[-1] is self.head:
                        self.stack.pop()
                    elif len(self.stack) >= 2 and self.stack[-2] is self.head:
                        self.stack.pop(-2)
                    return
                return super()._open(tag, attrs, selfclosing)
            self._ensure_body()
        self._body_rules(tag)
        super()._open(tag, attrs, selfclosing)

    def _body_rules(self, tag):
        """The implied end tags and implied parents a start tag brings in the body (and in template
        content, whose own elements are its scope)."""
        cur = self._cur()
        ct = cur.tag if cur is not None else None
        if tag in _CLOSES_P:
            if tag == "li":
                for el in reversed(self.stack):
                    if el.ns == "html" and el.tag == "li":
                        self._implied_end(keep=("li",))
                        self._pop_until({"li"})
                        break
                    if _is_special(el) and not (el.ns == "html" and el.tag in ("address", "div", "p")):
                        break
            elif tag in ("dd", "dt"):
                for el in reversed(self.stack):
                    if el.ns == "html" and el.tag in ("dd", "dt"):
                        self._implied_end(keep=(el.tag,))
                        self._pop_until({el.tag})
                        break
                    if _is_special(el) and not (el.ns == "html" and el.tag in ("address", "div", "p")):
                        break
            self._close_p()
            if tag in _HEADINGS and self._cur() is not None and self._cur().tag in _HEADINGS:
                self.stack.pop()
            return
        if tag in ("option", "optgroup"):
            if ct == "option":
                self.stack.pop()
            if tag == "optgroup" and self._cur() is not None and self._cur().tag == "optgroup":
                self.stack.pop()
            return
        if tag == "button" and self._in_scope({"button"}):
            self._implied_end()
            self._pop_until({"button"})
            return
        if tag in ("rb", "rtc", "rp", "rt"):
            if self._in_scope({"ruby"}):
                self._implied_end(keep=("rtc",) if tag in ("rp", "rt") else ())
            return
        if tag == "caption" or tag == "colgroup":
            self._clear_to({"table", "template"})
            return
        if tag == "col":
            self._clear_to({"table", "template", "colgroup"})
            if self._cur() is not None and self._cur().tag == "table":
                self._raw_open("colgroup")
            return
        if tag in _TABLE_SECTIONS:
            if self._in_table_scope(_TABLE_SECTIONS | {"caption", "colgroup"}):
                self._clear_to({"table", "template"})
            return
        if tag == "tr":
            if self._in_table_scope({"tr"}):
                self._clear_to(_TABLE_SECTIONS | {"table", "template"}, close={"tr"})
            self._clear_to(_TABLE_SECTIONS | {"table", "template"}, only_if_table=True)
            if self._cur() is not None and self._cur().tag == "table":
                self._raw_open("tbody")
            return
        if tag in ("td", "th"):
            if self._in_table_scope({"td", "th"}):
                self._implied_end()
                self._pop_until({"td", "th"})
            if self._cur() is not None and self._cur().tag in {"table", "colgroup", "caption"} | _TABLE_SECTIONS:
                if self._cur().tag in ("colgroup", "caption"):
                    self.stack.pop()
                if self._cur() is not None and self._cur().tag == "table":
                    self._raw_open("tbody")
                self._raw_open("tr")
            return

    def _clear_to(self, names, close=None, only_if_table=False):
        """Pop the open table parts above the nearest of names (the table context); close names an
        element (tr) to pop as well."""
        if only_if_table and not self._in_table_scope({"table", "template"} | _TABLE_SECTIONS):
            return
        if close:
            self._pop_until(close)
            return
        while self.stack and self.stack[-1].tag not in names and self.stack[-1].tag in \
                ({"tr", "td", "th", "caption", "colgroup"} | _TABLE_SECTIONS):
            self.stack.pop()

    def handle_endtag(self, tag):
        cur = self._cur()
        if cur is not None and cur.ns != "html":
            if tag in ("br", "p"):
                # </br> and </p> end foreign content as an HTML start tag does, then act as in HTML.
                while self.stack and not _html_rules(self.stack[-1], tag):
                    self.stack.pop()
            else:
                # Any other end tag closes the nearest foreign element of that name above the
                # nearest HTML element; past that it is an HTML end tag (13.2.6.5).
                for k in range(len(self.stack) - 1, 0, -1):
                    if self.stack[k].tag.lower() == tag:
                        del self.stack[k:]
                        return
                    if self.stack[k - 1].ns == "html":
                        break
        if tag == "template":
            # Closes the template and everything open in it, whatever it is (13.2.6.4.4: generate
            # all implied end tags thoroughly, then pop up to the template), never stopping at a
            # special element as other end tags do.
            if any(el.ns == "html" and el.tag == "template" for el in self.stack):
                while self.stack:
                    el = self.stack.pop()
                    if el.ns == "html" and el.tag == "template":
                        break
            return
        if tag in ("html", "body"):
            return  # content after </body> still goes in the body
        if tag == "head":
            if self.head is not None and self.head in self.stack:
                while self.stack and self.stack[-1] is not self.head:
                    self.stack.pop()
                self.stack.pop()
            return
        if tag == "br":
            self._open("br", [], False)
            return
        if tag == "p" and not self._in_scope({"p"}, extra=("button",)):
            self._ensure_body()
            self._raw_open("p")  # </p> with no open p is an empty p
            self.stack.pop()
            return
        if tag in _BLOCK_END:
            # Closes the element and whatever implied end tags (p, li, option, ...) are open in it.
            names = _HEADINGS if tag in _HEADINGS else {tag}
            extra = ("ol", "ul") if tag == "li" else ("button",) if tag == "p" else ()
            if self._in_scope(names, extra=extra):
                self._pop_until(names)
            return
        if tag in _TABLE_PARTS:
            if self._in_table_scope({tag}):
                self._pop_until({tag})
            return
        for k in range(len(self.stack) - 1, -1, -1):
            el = self.stack[k]
            if el.tag.lower() == tag:
                del self.stack[k:]
                return
            if _is_special(el):
                return  # any other end tag never closes past a special element

    def handle_data(self, data):
        if self.body is None:
            top = self._cur()
            if top is None or top is self.root or top is self.head:
                if not data.strip(" \t\n\r\f"):
                    return  # whitespace before the body is not part of the compared tree
                self._ensure_body()
        super().handle_data(data)


class _Doc:
    """A parsed document: its elements, the compared ones in tree order with their tree paths (as
    differ.js collects them: skipped tags left out, contents masks honored), and its head keys."""

    def __init__(self, text, contents_masks=(), static=False):
        # static: a page's source (dist/, the fixture site), built with the HTML standard's tree
        # construction rules; otherwise a serialized DOM (the oracle capture), whose end tags are
        # explicit.
        b = _StaticBuilder() if static else _Builder()
        b.feed(text)
        b.close()
        if b.root is None:
            raise ValueError("no root element")
        self.root = b.root
        self.elements = [e for e in b.all if not e.inert]
        for e in self.elements:
            counts = {}
            for k, c in enumerate(e.kids):
                c.pos, c.n = k + 1, len(e.kids)
                t = c.tag.lower()
                counts[t] = counts.get(t, 0) + 1
                c.tpos = counts[t]
            for c in e.kids:
                c.tn = counts[c.tag.lower()]
        masked = set()
        for sel in contents_masks:
            lst, _ = _parse_selector(sel)
            m = _Matcher(lst)
            masked |= {id(e) for e in self.elements if m.match(e) is True}
        self.compared = []
        stack = [(self.root, self.root.tag)]
        while stack:
            e, path = stack.pop()
            e.path, e.ci = path, len(self.compared)
            self.compared.append(e)
            if id(e) in masked:
                continue
            kids, k = [], 0
            for c in e.kids:
                if c.tag in SKIP_TAGS or c.tag in HARNESS_TAGS:
                    continue
                kids.append((c, f"{path} > {c.tag}:{k}"))
                k += 1
            stack.extend(reversed(kids))
        self.head_keys = self._head_keys()

    def _head_keys(self):
        """differ.js collectHead()'s keys: title, then each meta, non-stylesheet link, base and
        data-block script of the document outside <template>, with #2, #3 for repeats; a data block
        that repeats an earlier one of its key exactly (attributes and content) is counted once."""
        out = ["title"]
        seen = {"title": None}

        def put(key, canon=None):
            k, n = key, 1
            while k in seen:
                if canon is not None and seen[k] == canon:
                    return
                n += 1
                k = f"{key}#{n}"
            seen[k] = canon
            out.append(k)
        for e in self.elements:
            if e.ns != "html" or e.tag not in ("meta", "link", "base", "script"):
                continue
            a = e.attrs
            if e.tag == "script":
                if "type" not in a:
                    continue
                ty = a["type"].split(";")[0].strip().lower()
                if ty not in _JS_TYPES:
                    put(f"script[type={ty}]", _data_block_canon(ty, a, "".join(e.text)))
                continue
            if e.tag == "base":
                put("base")
                continue
            if e.tag == "meta":
                ident = next((x for x in ("name", "property", "http-equiv", "itemprop") if x in a), None)
                key = f"meta[{ident}={a[ident]}]" if ident else ("meta[charset]" if "charset" in a else "meta")
            else:
                rels = sorted(r for r in (a.get("rel") or "").lower().split() if r)
                if any(r in _HEAD_SKIP_RELS for r in rels):
                    continue
                key = "link[rel=" + " ".join(rels) + "]"
                for x in ("sizes", "hreflang"):
                    if x in a:
                        key += f"[{x}={a[x]}]"
            if "media" in a:
                key += f"[media={a['media']}]"
            put(key)
        return out


class SelectorError(ValueError):
    pass


_U = None  # unknown (Kleene logic)


def _and(a, b):
    if a is False or b is False:
        return False
    if a is _U or b is _U:
        return _U
    return True


_WS = " \t\n\r\f"
_LEGACY_PSEUDO_ELEMENTS = frozenset(("before", "after", "first-line", "first-letter"))
_LIST_PSEUDOS = frozenset(("not", "is", "where", "matches", "any", "-webkit-any", "-moz-any"))
_NTH = frozenset(("nth-child", "nth-last-child", "nth-of-type", "nth-last-of-type"))
_STATIC = frozenset(("root", "scope", "empty", "first-child", "last-child", "only-child", "first-of-type",
                     "last-of-type", "only-of-type", "link", "any-link", "defined"))
# HTML's attributes whose values selectors match ASCII case-insensitively on HTML elements.
_CI_ATTRS = frozenset((
    "accept accept-charset align alink axis bgcolor charset checked clear codetype color compact declare defer dir "
    "direction disabled enctype face frame hreflang http-equiv lang language link media method multiple nohref "
    "noresize noshade nowrap readonly rel rev rules scope scrolling selected shape target text type valign "
    "valuetype vlink").split())


class _SelParser:
    """Selectors Level 4 as browsers ship them: lists, the four combinators, type, universal, id,
    class and attribute selectors (all operators, i and s flags), :not, :is, :where, :has (relative),
    :nth-*() with "of S", the structural pseudo-classes; any other pseudo-class is parsed and left
    unknown. Pseudo-elements are refused: an entry's pseudo field names them."""

    def __init__(self, s):
        self.s, self.i = s, 0
        self.attr_names = set()

    def err(self, msg):
        raise SelectorError(f"{msg} (at offset {self.i})")

    def peek(self, n=0):
        j = self.i + n
        return self.s[j] if j < len(self.s) else ""

    def ws(self):
        seen = False
        while True:
            c = self.peek()
            if c and c in _WS:
                self.i += 1
                seen = True
            elif self.s.startswith("/*", self.i):
                j = self.s.find("*/", self.i + 2)
                if j < 0:
                    self.err("unclosed comment")
                self.i = j + 2
                seen = True
            else:
                return seen

    def _escape(self):
        self.i += 1
        c = self.peek()
        if not c:
            return "\ufffd"
        m = re.match(r"[0-9a-fA-F]{1,6}", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            if self.peek() and self.peek() in _WS:
                self.i += 1
            cp = int(m.group(0), 16)
            return chr(cp) if 0 < cp <= 0x10FFFF and not 0xD800 <= cp <= 0xDFFF else "\ufffd"
        if c == "\n":
            self.err("newline escape")
        self.i += 1
        return c

    @staticmethod
    def _namechar(c):
        return c.isalnum() or c in "-_" or ord(c) >= 0x80

    def ident(self):
        start, out = self.i, []
        if self.peek() == "-":
            out.append("-")
            self.i += 1
            if self.peek() == "-":
                out.append("-")
                self.i += 1
        c = self.peek()
        if out == ["-", "-"]:
            pass
        elif c == "\\":
            out.append(self._escape())
        elif c and (c.isalpha() or c == "_" or ord(c) >= 0x80):
            out.append(c)
            self.i += 1
        else:
            self.i = start
            self.err("identifier expected")
        while True:
            c = self.peek()
            if c == "\\":
                out.append(self._escape())
            elif c and self._namechar(c):
                out.append(c)
                self.i += 1
            else:
                return "".join(out)

    def name(self):
        out = []
        while True:
            c = self.peek()
            if c == "\\":
                out.append(self._escape())
            elif c and self._namechar(c):
                out.append(c)
                self.i += 1
            else:
                break
        if not out:
            self.err("name expected")
        return "".join(out)

    def string(self):
        q = self.peek()
        self.i += 1
        out = []
        while True:
            c = self.peek()
            if not c:
                self.err("unclosed string")
            if c == q:
                self.i += 1
                return "".join(out)
            if c == "\\":
                if self.peek(1) == "\n":
                    self.i += 2
                    continue
                out.append(self._escape())
            elif c == "\n":
                self.err("newline in string")
            else:
                out.append(c)
                self.i += 1

    def selector_list(self, relative=False):
        out = []
        while True:
            self.ws()
            out.append(self.complex(relative))
            self.ws()
            if self.peek() != ",":
                return out
            self.i += 1

    def complex(self, relative):
        """[(combinator before the compound, compound)], left to right; the first combinator is " ",
        or a relative selector's leading one (its relation to the :has() anchor)."""
        parts, comb = [], " "
        if relative and self.peek() in (">", "+", "~") and self.peek():
            comb = self.peek()
            self.i += 1
            self.ws()
        while True:
            parts.append((comb, self.compound()))
            had_ws = self.ws()
            c = self.peek()
            if c and c in ">+~":
                comb = c
                self.i += 1
                self.ws()
            elif c and c not in ",)":
                if not had_ws:
                    self.err(f"unexpected {c!r}")
                comb = " "
            else:
                return parts

    def compound(self):
        tag, subs, start = None, [], self.i
        c = self.peek()
        if c == "*" or c == "|" or (c and (c.isalpha() or c in "-_\\" or ord(c) >= 0x80)):
            if c == "*":
                self.i += 1
                first = "*"
            elif c == "|":
                first = ""
            else:
                first = self.ident()
            if self.peek() == "|" and self.peek(1) != "=":
                self.i += 1
                if first != "*":
                    self.err("namespace prefixes other than *| are not supported (querySelector cannot resolve them)")
                if self.peek() == "*":
                    self.i += 1
                    first = "*"
                else:
                    first = self.ident()
            tag = first
        while True:
            c = self.peek()
            if c == "#":
                self.i += 1
                subs.append(("id", self.name()))
            elif c == ".":
                self.i += 1
                subs.append(("class", self.ident()))
            elif c == "[":
                subs.append(self.attribute())
            elif c == ":":
                if self.peek(1) == ":":
                    self.err("a pseudo-element belongs in the entry's pseudo field, not in its selector")
                self.i += 1
                subs.append(self.pseudo())
            else:
                break
        if self.i == start:
            self.err("selector expected")
        return (None if tag in (None, "*") else tag.lower(), subs)

    def attribute(self):
        self.i += 1
        self.ws()
        if self.peek() == "*" and self.peek(1) == "|":
            self.i += 2
        elif self.peek() == "|":
            self.i += 1
        name = self.ident().lower()
        if self.peek() == "|" and self.peek(1) != "=":
            self.err("namespace prefixes other than *| are not supported (querySelector cannot resolve them)")
        self.attr_names.add(name)
        self.ws()
        if self.peek() == "]":
            self.i += 1
            return ("attr", name, None, None, None)
        op = next((o for o in ("~=", "|=", "^=", "$=", "*=", "=") if self.s.startswith(o, self.i)), None)
        if op is None:
            self.err("attribute operator expected")
        self.i += len(op)
        self.ws()
        val = self.string() if self.peek() and self.peek() in "\"'" else self.ident()
        self.ws()
        flag = None
        if self.peek() and self.peek().lower() in ("i", "s"):
            flag = self.peek().lower()
            self.i += 1
            self.ws()
        if self.peek() != "]":
            self.err("] expected")
        self.i += 1
        return ("attr", name, op, val, flag)

    def _skip_args(self):
        depth = 1
        while depth:
            c = self.peek()
            if not c:
                self.err("unclosed (")
            if c in "\"'":
                self.string()
            elif c == "\\":
                self._escape()
            else:
                self.i += 1
                depth += (c == "(") - (c == ")")

    def _close(self):
        self.ws()
        if self.peek() != ")":
            self.err(") expected")
        self.i += 1

    def pseudo(self):
        name = self.ident().lower()
        if name in _LEGACY_PSEUDO_ELEMENTS:
            self.err("a pseudo-element belongs in the entry's pseudo field, not in its selector")
        if self.peek() != "(":
            return ("pc", name) if name in _STATIC else ("unknown", name)
        self.i += 1
        if name in _LIST_PSEUDOS:
            lst = self.selector_list()
            self._close()
            return ("not" if name == "not" else "is", lst)
        if name == "has":
            lst = self.selector_list(relative=True)
            self._close()
            return ("has", lst)
        if name in _NTH:
            self.ws()
            a, b = self.anb()
            self.ws()
            of = None
            if name in ("nth-child", "nth-last-child") and self.s[self.i:self.i + 2].lower() == "of" \
                    and self.peek(2) and self.peek(2) in _WS:
                self.i += 2
                of = self.selector_list()
            self._close()
            return ("nth", name, a, b, of)
        self._skip_args()
        return ("unknown", name)

    def anb(self):
        m = re.match(r"(?i)(odd|even)(?![\w-])", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            return (2, 1) if m.group(1).lower() == "odd" else (2, 0)
        txt = re.match(r"[0-9nN+\-\s]*", self.s[self.i:]).group(0).rstrip()
        self.i += len(txt)
        t = re.sub(r"\s+", "", txt).lower()
        m = re.fullmatch(r"([+-]?\d*)n([+-]\d+)?", t)
        if m:
            co = m.group(1)
            return (-1 if co == "-" else 1 if co in ("", "+") else int(co)), int(m.group(2) or 0)
        if re.fullmatch(r"[+-]?\d+", t):
            return 0, int(t)
        self.err("An+B expected")


def _parse_selector(s):
    """A parsed selector list and the attribute names it tests; SelectorError if it cannot be parsed."""
    p = _SelParser(s)
    lst = p.selector_list()
    p.ws()
    if p.i != len(s):
        p.err("unexpected text")
    return lst, p.attr_names


def _attr_ok(el, name, op, val, flag):
    v = el.attrs.get(name)
    if v is None:
        return False
    if op is None:
        return True
    if flag == "i" or (flag is None and el.ns == "html" and name in _CI_ATTRS):
        v, val = v.lower(), val.lower()
    if op == "=":
        return v == val
    if op == "~=":
        return bool(val) and not any(c in _WS for c in val) and val in v.split()
    if op == "|=":
        return v == val or v.startswith(val + "-")
    if not val:
        return False
    if op == "^=":
        return v.startswith(val)
    if op == "$=":
        return v.endswith(val)
    return val in v


def _nth_ok(p, a, b):
    if a == 0:
        return p == b
    q, r = divmod(p - b, a)
    return r == 0 and q >= 0


def _descendants(el):
    out, stack = [], list(reversed(el.kids))
    while stack:
        e = stack.pop()
        out.append(e)
        stack.extend(reversed(e.kids))
    return out


class _Matcher:
    """Matches a parsed selector list on one document: True, False or unknown (_U)."""

    def __init__(self, lst):
        self.lst, self.memo = lst, {}

    def match(self, el):
        return self._list(el, self.lst)

    def _list(self, el, lst):
        key = ("l", id(el), id(lst))
        if key in self.memo:
            return self.memo[key]
        res = False
        for cx in lst:
            r = self._complex(el, cx, len(cx) - 1, None)
            if r is True:
                res = True
                break
            if r is _U:
                res = _U
        self.memo[key] = res
        return res

    def _complex(self, el, parts, k, anchor):
        key = ("c", id(el), id(parts), k, id(anchor))
        if key in self.memo:
            return self.memo[key]
        comb, comp = parts[k]
        r = self._compound(el, comp)
        if r is not False:
            if k == 0:
                if anchor is not None:
                    r = _and(r, self._rel(el, comb, anchor))
            elif comb == ">":
                r = False if el.parent is None else _and(r, self._complex(el.parent, parts, k - 1, anchor))
            elif comb == "+":
                sib = el.parent.kids[el.pos - 2] if el.parent is not None and el.pos > 1 else None
                r = False if sib is None else _and(r, self._complex(sib, parts, k - 1, anchor))
            else:
                cands = []
                if comb == " ":
                    p = el.parent
                    while p is not None:
                        cands.append(p)
                        p = p.parent
                elif el.parent is not None:
                    cands = el.parent.kids[:el.pos - 1][::-1]
                acc = False
                for c in cands:
                    x = self._complex(c, parts, k - 1, anchor)
                    if x is True:
                        acc = True
                        break
                    if x is _U:
                        acc = _U
                r = _and(r, acc)
        self.memo[key] = r
        return r

    @staticmethod
    def _rel(el, comb, anchor):
        if comb == ">":
            return el.parent is anchor
        if comb == " ":
            p = el.parent
            while p is not None:
                if p is anchor:
                    return True
                p = p.parent
            return False
        if anchor.parent is None or el.parent is not anchor.parent:
            return False
        return el.pos == anchor.pos + 1 if comb == "+" else el.pos > anchor.pos

    def _compound(self, el, comp):
        tag, subs = comp
        if tag is not None and el.tag.lower() != tag:
            return False
        res = True
        for s in subs:
            t = s[0]
            if t == "id":
                r = el.attrs.get("id") == s[1]
            elif t == "class":
                r = s[1] in el.classes
            elif t == "attr":
                r = _attr_ok(el, *s[1:])
            elif t == "pc":
                r = self._static(el, s[1])
            elif t == "not":
                x = self._list(el, s[1])
                r = _U if x is _U else not x
            elif t == "is":
                r = self._list(el, s[1])
            elif t == "has":
                r = self._has(el, s[1])
            elif t == "nth":
                r = self._nth(el, *s[1:])
            else:
                r = _U
            if r is False:
                return False
            if r is _U:
                res = _U
        return res

    @staticmethod
    def _static(el, name):
        if name in ("root", "scope"):
            return el.parent is None
        if name == "empty":
            return el.empty
        if name == "first-child":
            return el.pos == 1
        if name == "last-child":
            return el.pos == el.n
        if name == "only-child":
            return el.n == 1
        if name == "first-of-type":
            return el.tpos == 1
        if name == "last-of-type":
            return el.tpos == el.tn
        if name == "only-of-type":
            return el.tn == 1
        if name in ("link", "any-link"):
            return el.ns == "html" and el.tag in ("a", "area") and "href" in el.attrs
        return _U if "-" in el.tag else True  # defined: custom elements depend on script

    def _nth(self, el, name, a, b, of):
        last = name.startswith("nth-last")
        if name.endswith("of-type"):
            return _nth_ok(el.tn - el.tpos + 1 if last else el.tpos, a, b)
        if of is None:
            return _nth_ok(el.n - el.pos + 1 if last else el.pos, a, b)
        me = self._list(el, of)
        if me is False:
            return False
        sibs = el.parent.kids if el.parent is not None else [el]
        p = 1
        for j in (range(el.pos, len(sibs)) if last else range(el.pos - 1)):
            x = self._list(sibs[j], of)
            if x is _U:
                return _U
            p += bool(x)
        return _and(me, _nth_ok(p, a, b))

    def _has(self, el, lst):
        key = ("h", id(el), id(lst))
        if key in self.memo:
            return self.memo[key]
        res = False
        for cx in lst:
            if cx[0][0] in (" ", ">"):
                cands = _descendants(el)
            else:
                cands = []
                for s in (el.parent.kids[el.pos:] if el.parent is not None else []):
                    cands.append(s)
                    cands.extend(_descendants(s))
            for c in cands:
                x = self._complex(c, cx, len(cx) - 1, el)
                if x is True:
                    res = True
                    break
                if x is _U:
                    res = _U
            if res is True:
                break
        self.memo[key] = res
        return res


def _subject_index(lst):
    """For a selector list whose every subject compound names an id, a class or a tag: a function
    giving a document's candidate elements, so a narrow selector is not tried on every element."""
    keys = []
    for cx in lst:
        tag, subs = cx[-1][1]
        ids = [s[1] for s in subs if s[0] == "id"]
        classes = [s[1] for s in subs if s[0] == "class"]
        if ids:
            keys.append(("id", ids[0]))
        elif classes:
            keys.append(("class", classes[0]))
        elif tag is not None:
            keys.append(("tag", tag))
        else:
            return None

    def cands(doc):
        seen, out = set(), []
        for kind, v in keys:
            for e in doc.index(kind, v):
                if id(e) not in seen:
                    seen.add(id(e))
                    out.append(e)
        return out
    return cands


def _doc_index(self, kind, v):
    idx = getattr(self, "_idx", None)
    if idx is None:
        idx = self._idx = {"id": {}, "class": {}, "tag": {}}
        for e in self.compared:
            if "id" in e.attrs:
                idx["id"].setdefault(e.attrs["id"], []).append(e)
            for c in e.classes:
                idx["class"].setdefault(c, []).append(e)
            idx["tag"].setdefault(e.tag.lower(), []).append(e)
    return idx[kind].get(v, [])


_Doc.index = _doc_index


# -- the reference documents --------------------------------------------------------------------
_DOCS = {}  # sha1 of the text -> _Doc (or the parse error), per process


def _contents_masks():
    try:
        return tuple(m["selector"] for m in json.loads(MASKS.read_text())["masks"] if m.get("contents"))
    except (OSError, ValueError, KeyError):
        return ()


class _Ref:
    """One reference document: site (oracle, fixture, dist), route, variant, its text's hash, and
    whether its site is complete (site shares count only complete sites: the oracle, and a dist
    build that holds every kept route)."""
    __slots__ = ("site", "route", "variant", "key", "complete")

    def __init__(self, site, route, variant, key, complete=False):
        self.site, self.route, self.variant, self.key, self.complete = site, route, variant, key, complete

    def label(self):
        return f"{self.site} {self.route} ({self.variant})"


def _dist_page(root, route, kind):
    """The file a built folder serves for a route (wrangler pages dev: /a/b from a/b.html or
    a/b/index.html; an unknown path from 404.html), or None."""
    stem = route.strip("/")
    if kind == "404":
        cands = [root / "404.html"]
    elif not stem:
        cands = [root / "index.html"]
    else:
        cands = [root / f"{stem}.html", root / stem / "index.html"]
    return next((p for p in cands if p.is_file()), None)


def _reference_docs(dist_dirs=()):
    """(refs, problems, texts): every reference document, why a site could not be read, and each
    document's (text, static) by key.

    oracle: each captured route's dom.html (1300 light), dom-dark.html and dom-375.html, the
      markup the oracle's own scripts make per scheme and viewport (tests/README.md, The oracle);
      serialized DOMs, read with explicit end tags. A complete site.
    fixture: tests/fixtures/site/index.html and other.html, unchanged and under every control in
      controls.json, since a selftest's side B is one of them; page sources, read with the HTML
      standard's tree construction (_StaticBuilder). Never a site for site shares.
    dist: each route's built page in dist/ once it is built, and in every other built folder a run
      serves (dist:<path>): <route>.html, <route>/index.html, or 404.html for the 404 route; page
      sources, read as the fixture's are. A folder is a complete site once it holds a page for
      every kept route; until then only its documents count, one by one.
    Each also counts with data-theme light and dark on <html> (the theme legs) when the selector
    tests data-theme (_Breadth.reach)."""
    refs, problems, texts = [], [], {}

    def add(site, route, variant, text, static, complete):
        key = hashlib.sha1((("static\0" if static else "dom\0") + text).encode("utf-8", "surrogatepass")).hexdigest()
        texts[key] = (text, static)
        refs.append(_Ref(site, route, variant, key, complete))
    if CAPTURE.is_dir():
        for d in sorted(CAPTURE.iterdir()):
            meta = d / "meta.json"
            if not d.is_dir() or d.name.startswith("_") or not meta.exists():
                continue
            route = json.loads(meta.read_text())["path"]
            for f, variant in (("dom.html", "1300 light"), ("dom-dark.html", "1300 dark"), ("dom-375.html", "375 light")):
                if (d / f).exists():
                    add("oracle", route, variant, (d / f).read_text(), False, True)
    if not any(r.site == "oracle" for r in refs):
        problems.append(f"the oracle capture ({CAPTURE.relative_to(REPO)}) is missing: run `uv run tests/run.py oracle`")
    try:
        from .server import build_overrides, load_controls
        controls = [None] + sorted(load_controls())
        for c in controls:
            try:
                files, removed = build_overrides(FIXTURE_SITE, c)
            except Exception as e:  # a stale control is the fixture server's error to report
                problems.append(f"fixture control {c}: {e}")
                continue
            for route in FIXTURE_ROUTES:
                if route in removed:
                    continue
                body = files.get(route)
                text = body.decode("utf-8") if body is not None else (FIXTURE_SITE / route.lstrip("/")).read_text()
                add("fixture", route, c or "unchanged", text, True, False)
    except (OSError, ValueError, ImportError) as e:
        problems.append(f"the fixture site cannot be read: {e}")
    roots = []
    for d in [DIST, *dist_dirs]:
        d = Path(d).resolve()
        if d.is_dir() and d not in roots:
            roots.append(d)
    kinds = _route_kinds()
    kept = _kept_routes()
    for root in roots:
        variant = "static" if root == DIST.resolve() else f"static, {_rel_repo(root)}"
        pages = {}
        for route in _known_routes():
            if route in FIXTURE_ROUTES:
                continue
            p = _dist_page(root, route, kinds.get(route))
            if p is not None:
                pages[route] = p
        complete = bool(kept) and all(r in pages for r in kept)
        for route, p in pages.items():
            add("dist", route, variant, p.read_text(), True, complete)
    return refs, problems, texts


def _rel_repo(p):
    try:
        return str(Path(p).relative_to(REPO))
    except ValueError:
        return str(p)


def _route_kinds():
    try:
        return {r["path"]: r.get("kind") for r in json.loads(ORACLE_ROUTES.read_text())["routes"]}
    except (OSError, ValueError, KeyError):
        return {}


def _kept_routes():
    try:
        return [r["path"] for r in json.loads(ORACLE_ROUTES.read_text())["routes"] if r.get("kept")]
    except (OSError, ValueError, KeyError):
        return []


def _known_routes():
    out = []
    try:
        out = [r["path"] for r in json.loads(ORACLE_ROUTES.read_text())["routes"]]
    except (OSError, ValueError, KeyError):
        pass
    if CAPTURE.is_dir():
        for d in sorted(CAPTURE.iterdir()):
            meta = d / "meta.json"
            if d.is_dir() and meta.exists():
                p = json.loads(meta.read_text())["path"]
                if p not in out:
                    out.append(p)
    return out + [r for r in FIXTURE_ROUTES if r not in out]


def _get_doc(key, texts, masks):
    d = _DOCS.get(key)
    if d is None:
        text, static = texts[key]
        try:
            d = _Doc(text, masks, static=static)
        except Exception as e:  # a document the tree cannot be built from: reported, never silent
            d = e
        _DOCS[key] = d
    return d


def _route_scope(e, known):
    """The routes an entry names: where.routes (and a status entry's path), as a set of route paths
    (an exact route counts even if it is not among the known routes; a regex counts the known routes
    it matches), or None when the entry is not route-scoped at all."""
    w = e.get("where") if isinstance(e.get("where"), dict) else {}
    pats = w.get("routes") if isinstance(w.get("routes"), list) else None
    if e.get("kind") == "status":
        p = e.get("path", "*")
        names = {p} if isinstance(p, str) and p != "*" and not _is_regex(p, route=True) else \
            {r for r in known if _pattern_match(p, r, route=True)}
        if pats is not None:
            names = {r for r in names if any(_route_match(x, r) for x in pats)}
        return names
    if pats is None:
        return None
    names = set()
    for x in pats:
        if not isinstance(x, str):
            continue
        if _is_regex(x, route=True):
            names |= {r for r in known if _pattern_match(x, r, route=True)}
        else:
            names.add(x)
    return names


def _pct(x):
    return f"{x * 100:.1f}%"


class _Breadth:
    """Evaluates entries on the reference documents (lazily: nothing is parsed unless an entry needs it)."""

    def __init__(self, dist_dirs=()):
        self.known = _known_routes()
        self.dist_dirs = tuple(dist_dirs)
        self._refs = None
        self.doc_errors = {}  # reference label -> why its tree could not be built
        self.js_hits = {}  # regex path pattern -> the reference values (tree paths, head keys) it matches

    def refs(self):
        if self._refs is None:
            self._refs = _reference_docs(self.dist_dirs)
            self.masks = _contents_masks()
        return self._refs

    def judge_paths(self, patterns):
        """Evaluate regex path patterns with JavaScript's RegExp, as differ.js applies them, on every
        tree path and head key of the reference documents. Returns {pattern: error} for those that
        could not be evaluated (all of them when node cannot run)."""
        if not patterns:
            return {}
        refs, _, texts = self.refs()
        values = set()
        for r in refs:
            d = _get_doc(r.key, texts, self.masks)
            if not isinstance(d, Exception):
                values.update(e.path for e in d.compared)
                values.update(d.head_keys)
        values = sorted(values)
        try:
            res = _js_regexes(sorted(patterns), values)
        except RuntimeError as e:
            return {p: f"cannot be evaluated with JavaScript's RegExp ({e})" for p in patterns}
        errors = {}
        for p in patterns:
            r = res.get(p) or {}
            if "error" in r:
                errors[p] = f"is not a valid JavaScript regular expression: {r['error']}"
            else:
                self.js_hits[p] = {values[i] for i in r.get("hits", [])}
        return errors

    def _path_test(self, e):
        """The entry's path pattern as a test of a tree path or head key, as differ.js's strPat()."""
        if "path" not in e or e["path"] == "*":
            return lambda v: True
        p = e["path"]
        if _is_regex(p):
            hits = self.js_hits.get(p, set())
            return hits.__contains__
        return lambda v: v == p

    def reach(self, e, scope):
        """[(ref, data-theme or None, the indices of the compared elements (head: head keys) the entry
        matches, their total)] over the documents in its route scope (None: every document). Raises
        SelectorError for a selector the engine cannot parse."""
        refs, _, texts = self.refs()
        kind = e["kind"]
        sel_lst, attr_names, cands = None, set(), None
        if kind != "head" and isinstance(e.get("selector"), str) and e["selector"].strip() not in ("*", "*|*"):
            sel_lst, attr_names = _parse_selector(e["selector"].strip())
            cands = _subject_index(sel_lst)
        path_ok = self._path_test(e)
        out, done = [], {}
        for r in refs:
            if scope is not None and r.route not in scope:
                continue
            d = _get_doc(r.key, texts, self.masks)
            if isinstance(d, Exception):
                self.doc_errors[r.label()] = f"{type(d).__name__}: {d}"
                continue
            if kind == "head":
                items = d.head_keys
                hit = frozenset(i for i, key in enumerate(items) if path_ok(key))
                out.append((r, None, hit, len(items)))
                continue
            themes = [None]
            if "data-theme" in attr_names:
                themes += ["light", "dark"]
            for theme in themes:
                if (r.key, theme) in done:  # the same text under another control or variant
                    out.append((r, theme, done[(r.key, theme)], len(d.compared)))
                    continue
                old = d.root.attrs.get("data-theme")
                if theme is not None:
                    d.root.attrs["data-theme"] = theme
                try:
                    m = _Matcher(sel_lst) if sel_lst is not None else None
                    pool = d.compared if (m is None or cands is None) else cands(d)
                    hit = frozenset(x.ci for x in pool if (m is None or m.match(x) is not False) and path_ok(x.path))
                finally:
                    if theme is not None:
                        if old is None:
                            d.root.attrs.pop("data-theme", None)
                        else:
                            d.root.attrs["data-theme"] = old
                done[(r.key, theme)] = hit
                out.append((r, theme, hit, len(d.compared)))
        return out

    @staticmethod
    def worst(reach):
        """The highest site share, over a complete site's routes in scope in one document variant
        (the oracle, a complete dist build), and the highest share of one document past DOC_FLOOR
        elements, each as (share, label, matched, total)."""
        sites = {}
        doc_worst = None
        for r, theme, hit, total in reach:
            v = r.variant + (f", data-theme {theme}" if theme else "")
            if r.complete:
                s = sites.setdefault((r.site, v), [0, 0, 0])
                s[0] += len(hit)
                s[1] += total
                s[2] += 1
            if total and len(hit) > DOC_FLOOR:
                share = len(hit) / total
                if doc_worst is None or share > doc_worst[0]:
                    doc_worst = (share, f"{r.site} {r.route} ({v})", len(hit), total)
        site_worst = None
        for (site, v), (m, n, routes) in sites.items():
            if n and (site_worst is None or m / n > site_worst[0]):
                site_worst = (m / n, f"{site}'s {routes} routes in its scope ({v})", m, n)
        return site_worst, doc_worst


def _judge(entries, errs, known=None, dist_dirs=()):
    """Breadth errors for valid entries (list of (where, entry)); returns {id: breadth info} and the
    ids rejected. See the module docstring and tests/README.md (Divergence registry, Breadth)."""
    b = _Breadth(dist_dirs)
    known = b.known if known is None else known
    info, rejected = {}, set()
    unions = {}  # kind -> list of (id, where, reach, route-scoped)
    unjudged_by = {}  # id -> the routes it names that have no reference document
    unit = {"head": "head keys"}
    page = [(where, e) for where, e in entries if e.get("kind") in PAGE_KINDS]
    path_errors = b.judge_paths({e["path"] for _, e in page if _is_regex(e.get("path"))}) if page else {}
    for where, e in entries:
        kind, eid = e.get("kind"), e.get("id")
        if kind == "skipped-check":
            w = e.get("where") or {}
            br = w.get("browsers") or []
            checks = [c for c in KNOWN_CHECKS if _pattern_match(e.get("check"), c)]
            info[eid] = {"scope": "checks", "browsers": br, "checks": checks}
            why = []
            if not br or len(set(br)) >= len(BROWSERS):
                why.append(f"it applies to {'every browser' if not br else 'all three browsers'}, and a skipped check "
                           "names the browser (or two) that cannot run it in where.browsers")
            if len(checks) > SKIP_CHECKS_MAX:
                why.append(f"its check matches {len(checks)} of the {len(KNOWN_CHECKS)} known checks ({', '.join(checks)}), "
                           f"and a skipped-check entry names at most {SKIP_CHECKS_MAX} (one limit is one media leg or one "
                           "pseudo-element)")
            if why:
                errs.append(f"{where}: too broad: " + "; and ".join(why))
                rejected.add(eid)
            continue
        scope = _route_scope(e, known)
        if kind == "status":
            info[eid] = {"scope": "routes", "routes": sorted(scope)}
            if len(scope) > ROUTE_SCOPE_MAX:
                errs.append(f"{where}: too broad: its path and where.routes cover {len(scope)} routes; a status entry "
                            f"names at most {ROUTE_SCOPE_MAX} routes")
                rejected.add(eid)
            continue
        if kind not in PAGE_KINDS:
            continue
        route_scoped = scope is not None and len(scope) <= ROUTE_SCOPE_MAX
        refs, problems, _ = b.refs()
        what = unit.get(kind, "compared elements")
        hint = (f"; narrow its {'path' if kind == 'head' else 'selector or path'}"
                + ("" if route_scoped else f", or name at most {ROUTE_SCOPE_MAX} routes in where.routes")
                + " (tests/README.md, Divergence registry, Breadth)")
        if e.get("path") in path_errors:
            errs.append(f"{where}: path {e['path']!r} {path_errors[e['path']]}; differ.js applies path patterns with "
                        "JavaScript's RegExp, so the registry judges them with it")
            rejected.add(eid)
            continue
        if not any(r.site == "oracle" for r in refs):
            errs.append(f"{where}: its breadth cannot be judged: {'; '.join(problems)}{hint}")
            rejected.add(eid)
            continue
        if scope is not None:
            # Routes in the scope with no reference document cannot be judged: an entry may name at
            # most ROUTE_SCOPE_MAX of them (and the whole registry too, below).
            covered = {r.route for r in refs}
            unjudged = sorted(scope - covered)
            if unjudged:
                unjudged_by[eid] = (where, unjudged)
            if len(unjudged) > ROUTE_SCOPE_MAX:
                errs.append(f"{where}: its breadth cannot be judged: where.routes names {len(unjudged)} routes with no "
                            f"reference document ({', '.join(unjudged[:4])}{', ...' if len(unjudged) > 4 else ''}), "
                            f"more than the {ROUTE_SCOPE_MAX} an entry may name without being judged{hint}")
                rejected.add(eid)
                continue
        try:
            reach = b.reach(e, scope)
        except SelectorError as x:
            errs.append(f"{where}: selector {e.get('selector')!r} cannot be evaluated: {x}; the registry judges an "
                        f"entry's breadth by evaluating it on the reference documents{hint}")
            rejected.add(eid)
            continue
        site, doc = b.worst(reach)
        cap = SITE_SHARE_MAX["head" if kind == "head" else "element"]
        info[eid] = {"scope": "routes" if route_scoped else "elements",
                     "routes": None if scope is None else sorted(scope),
                     "site_share": round(site[0], 4) if site else 0, "site_worst": site[1] if site else None,
                     "doc_share": round(doc[0], 4) if doc else 0, "doc_worst": doc[1] if doc else None}
        why = []
        if not route_scoped and site and site[0] > cap:
            why.append(f"{site[2]} of the {site[3]} {what} ({_pct(site[0])}) on the {site[1]}, more than {_pct(cap)}")
        if doc and doc[0] > DOC_SHARE_MAX:
            why.append(f"{doc[2]} of the {doc[3]} {what} ({_pct(doc[0])}) of {doc[1]}, more than "
                       f"{_pct(DOC_SHARE_MAX)} of one document" + (" (a route scope narrows where an entry applies, not "
                                                                   "how much of a page it may cover)" if route_scoped else ""))
        if why:
            errs.append(f"{where}: too broad: it reaches " + ", and ".join(why) + hint)
            rejected.add(eid)
        else:
            unions.setdefault(kind, []).append((eid, where, reach, route_scoped))
    for label, why in sorted(b.doc_errors.items()):
        errs.append(f"breadth: the reference document {label} cannot be read ({why}); every entry was judged without it")
    # The whole registry may name at most ROUTE_SCOPE_MAX routes without a reference document, so a
    # scope of uncaptured routes split into entries of a few routes each is caught.
    all_unjudged = sorted({r for _, rs in unjudged_by.values() for r in rs})
    if len(all_unjudged) > ROUTE_SCOPE_MAX:
        ids = sorted(unjudged_by)
        errs.append(f"entries {', '.join(f'[{i}]' for i in ids)}: their breadth cannot be judged: together they name "
                    f"{len(all_unjudged)} routes with no reference document ({', '.join(all_unjudged[:4])}"
                    f"{', ...' if len(all_unjudged) > 4 else ''}), more than the {ROUTE_SCOPE_MAX} the whole registry may "
                    "name without being judged (tests/README.md, Divergence registry, Breadth)")
        rejected.update(ids)
    for kind in list(unions):
        unions[kind] = [g for g in unions[kind] if g[0] not in rejected]
    _unions(unions, info, rejected, errs, unit)
    _kind_budget(b, unions, info, rejected, errs, unit)
    return info, rejected


def _unions(unions, info, rejected, errs, unit):
    """Together: the entries of one kind that passed alone. In one document, all of them (route-scoped
    ones included) reach at most UNION_DOC_MAX of its compared elements past DOC_FLOOR; over a
    complete site, those that are not route-scoped reach at most UNION_SITE_MAX. Past a limit, every
    entry of the group that reaches the documents (or site) concerned is rejected, since none can be
    told apart as the one that makes the group too broad."""
    for kind, group in unions.items():
        if len(group) < 2:
            continue
        what = unit.get(kind, "compared elements")
        per_doc, sites = {}, {}
        for eid, _, reach, scoped in group:
            for r, theme, hit, total in reach:
                k = (r.key, r.site, r.route, r.variant, theme)
                cur = per_doc.setdefault(k, [set(), total, set(), r])
                if hit:
                    cur[0] |= hit
                    cur[2].add(eid)
                if not scoped and r.complete:
                    v = r.variant + (f", data-theme {theme}" if theme else "")
                    s = sites.setdefault((r.site, v), {})
                    cur_s = s.setdefault(r.key, [set(), total, set()])
                    if hit:
                        cur_s[0] |= hit
                        cur_s[2].add(eid)
        doc_bad, doc_worst = set(), None
        for (_, site, route, variant, theme), (u, total, members, r) in per_doc.items():
            if not total or len(u) <= DOC_FLOOR or len(members) < 2:
                continue
            share = len(u) / total
            if share > UNION_DOC_MAX:
                doc_bad |= members
                if doc_worst is None or share > doc_worst[0]:
                    v = variant + (f", data-theme {theme}" if theme else "")
                    doc_worst = (share, f"{site} {route} ({v})", len(u), total)
        site_bad, site_worst = set(), None
        for (site, v), per in sites.items():
            m = sum(len(x[0]) for x in per.values())
            n = sum(x[1] for x in per.values())
            members = set().union(*(x[2] for x in per.values())) if per else set()
            if n and len(members) >= 2 and m / n > UNION_SITE_MAX:
                site_bad |= members
                if site_worst is None or m / n > site_worst[0]:
                    site_worst = (m / n, f"{site}'s {len(per)} routes in their scope ({v})", m, n)
        bad = doc_bad | site_bad
        if not bad:
            continue
        ids = [g[0] for g in group if g[0] in bad]
        msg = []
        if site_worst:
            msg.append(f"{site_worst[2]} of the {site_worst[3]} {what} ({_pct(site_worst[0])}) on the {site_worst[1]} "
                       f"(those not route-scoped), more than {_pct(UNION_SITE_MAX)}")
        if doc_worst:
            msg.append(f"{doc_worst[2]} of the {doc_worst[3]} {what} ({_pct(doc_worst[0])}) of {doc_worst[1]}, more "
                       f"than {_pct(UNION_DOC_MAX)} of one document")
        errs.append(f"{kind} entries {', '.join(f'[{i}]' for i in ids)}: too broad together: these {len(ids)} {kind} "
                    f"entries reach " + ", and ".join(msg) + " (each alone is under the limits); merge them into fewer, "
                    "narrower entries (tests/README.md, Divergence registry, Breadth)")
        rejected.update(ids)
        for eid in ids:
            info[eid]["union"] = {"ids": ids, "site_share": round(site_worst[0], 4) if site_worst else 0,
                                  "doc_share": round(doc_worst[0], 4) if doc_worst else 0}
    for kind in list(unions):
        unions[kind] = [g for g in unions[kind] if g[0] not in rejected]


def _kind_budget(b, unions, info, rejected, errs, unit):
    """The kind budget: every entry of a kind that passed, route-scoped ones included, together
    reaches at most UNION_SITE_MAX of a whole complete site's compared elements (head: head keys),
    per site (the oracle's routes, a complete dist build) and document variant. Past it, the kind's
    route-scoped entries that reach that site are rejected (the others passed their own site union),
    so a catch-all split by route into entries of a few routes each cannot cover the site."""
    refs, _, texts = b.refs()
    totals = {}  # (site, variant) -> [compared elements (head keys) over every document, routes]
    for r in refs:
        if not r.complete:
            continue
        d = _get_doc(r.key, texts, b.masks)
        if isinstance(d, Exception):
            continue
        t = totals.setdefault((r.site, r.variant), [0, set(), 0])
        if r.route not in t[1]:
            t[1].add(r.route)
            t[0] += len(d.compared)
            t[2] += len(d.head_keys)
    for kind, group in unions.items():
        if not any(scoped for _, _, _, scoped in group) or len(group) < 2:
            continue
        hits = {}  # (site, variant, theme) -> {doc key: set of indices}
        scoped_on = {}  # (site, variant, theme) -> route-scoped ids with hits there
        for eid, _, reach, scoped in group:
            for r, theme, hit, total in reach:
                if not r.complete or not hit:
                    continue
                k = (r.site, r.variant, theme)
                hits.setdefault(k, {}).setdefault(r.key, set()).update(hit)
                if scoped:
                    scoped_on.setdefault(k, set()).add(eid)
        worst, bad = None, set()
        for (site, variant, theme), per in hits.items():
            t = totals.get((site, variant))
            n = (t[2] if kind == "head" else t[0]) if t else 0
            m = sum(len(v) for v in per.values())
            if n and m / n > UNION_SITE_MAX and scoped_on.get((site, variant, theme)):
                bad |= scoped_on[(site, variant, theme)]
                if worst is None or m / n > worst[0]:
                    v = variant + (f", data-theme {theme}" if theme else "")
                    worst = (m / n, f"{site}'s {len(t[1])} routes ({v})", m, n)
        if not bad:
            continue
        ids = [eid for eid, _, _, scoped in group if eid in bad]
        what = unit.get(kind, "compared elements")
        errs.append(f"{kind} entries {', '.join(f'[{i}]' for i in ids)}: too broad together: these {len(ids)} "
                    f"route-scoped {kind} entries, with the other entries of their kind, reach {worst[2]} of the "
                    f"{worst[3]} {what} ({_pct(worst[0])}) of the {worst[1]}, more than the kind budget of "
                    f"{_pct(UNION_SITE_MAX)} of the site; a catch-all split by route is still a catch-all "
                    "(tests/README.md, Divergence registry, Breadth)")
        rejected.update(ids)
        for eid in ids:
            info.setdefault(eid, {})["budget"] = {"ids": ids, "site_share": round(worst[0], 4)}


class Registry:
    def __init__(self, directory: Path = DIVERGENCES, dist_dirs=()):
        """dist_dirs: built folders a run serves besides dist/ (dist:<path> sides), read as reference
        documents too."""
        self.directory = Path(directory)
        self.entries, self.errors, self.files = [], [], []
        ids = {}
        valid = []
        if not self.directory.is_dir():
            self.errors.append(f"registry directory {self.directory} does not exist")
        for p in sorted(self.directory.glob("*.json")):
            if p.name == "schema.json":
                continue
            self.files.append(p.name)
            try:
                data = json.loads(p.read_text())
            except json.JSONDecodeError as e:
                self.errors.append(f"{p.name}: invalid JSON: {e}")
                continue
            if not isinstance(data, list):
                self.errors.append(f"{p.name}: top level must be an array")
                continue
            for n, e in enumerate(data):
                before = len(self.errors)
                js = []
                validate_entry(e, f"{p.name}#{n}", self.errors, ids, js)
                if isinstance(e, dict):
                    entry = dict(e, _file=p.name)
                    if len(self.errors) > before:
                        entry["_rejected"] = True
                    else:
                        valid.append((f"{p.name}#{n} [{e.get('id')}]", entry, js))
                    self.entries.append(entry)
        valid = self._check_js(valid)
        self.breadth, rejected = _judge(valid, self.errors, dist_dirs=dist_dirs)
        for e in self.entries:
            if e.get("id") in rejected:
                e["_rejected"] = True
        self.hits = {e.get("id"): 0 for e in self.entries}

    def _check_js(self, valid):
        """Check every regex differ.js applies (an element or head entry's path, pseudo, property, a
        and b) with JavaScript's RegExp, the engine that applies it: a pattern JavaScript cannot
        compile is an error, as is any pattern when node cannot run. Returns the (where, entry) pairs
        still valid."""
        pats = sorted({pat for _, _, js in valid for _, pat in js})
        res, why = {}, None
        if pats:
            try:
                res = _js_regexes(pats)
            except RuntimeError as e:
                why = str(e)
        out = []
        for where, entry, js in valid:
            bad = []
            for field, pat in js:
                if why is not None:
                    bad.append(f"{field} {pat!r} cannot be checked with JavaScript's RegExp ({why})")
                elif "error" in (res.get(pat) or {}):
                    bad.append(f"{field} {pat!r} is not a valid JavaScript regular expression: {res[pat]['error']}")
            if bad:
                self.errors.append(f"{where}: " + "; ".join(bad) + " (differ.js applies it with JavaScript's RegExp)")
                entry["_rejected"] = True
            else:
                out.append((where, entry))
        return out

    def limits(self):
        """The per-document limits differ.js applies in every cell, on the live documents."""
        return {"doc": DOC_SHARE_MAX, "union": UNION_DOC_MAX, "floor": DOC_FLOOR, "cover": COVER_MAX}

    def _applied(self):
        """The entries in force: an entry with a registry error is never applied."""
        return [e for e in self.entries if not e.get("_rejected")]

    def rejected(self):
        return [e["id"] for e in self.entries if e.get("_rejected") and isinstance(e.get("id"), str)]

    @staticmethod
    def _where_ok(e, cell) -> bool:
        w = e.get("where") or {}
        if "browsers" in w and cell["browser"] not in w["browsers"]:
            return False
        if "routes" in w and not any(_route_match(p, cell["route"]) for p in w["routes"]):
            return False
        if "schemes" in w and cell["scheme"] not in w["schemes"]:
            return False
        if "comparisons" in w and cell.get("comparison") not in w["comparisons"]:
            return False
        if "widths" in w:
            ok = False
            for x in w["widths"]:
                if isinstance(x, int):
                    ok |= cell["width"] == x
                else:
                    ok |= x.get("min", 0) <= cell["width"] <= x.get("max", 10 ** 6)
            if not ok:
                return False
        return True

    def for_cell(self, cell) -> list:
        """Element and head entries that apply to a cell, in the shape differ.js expects. None in a
        self comparison: there every difference counts (criterion 1)."""
        out = []
        if cell.get("comparison") == "self":
            return out
        for e in self._applied():
            if e.get("kind") not in PAGE_KINDS or not self._where_ok(e, cell):
                continue
            out.append({k: e[k] for k in ("id", "kind", "selector", "path", "pseudo", "property", "a", "b") if k in e})
        return out

    def match_python(self, rec, cell) -> list:
        """Entries matching a record found in Python (kind status); none in a self comparison."""
        if cell.get("comparison") == "self":
            return []
        return [e["id"] for e in self._applied()
                if e.get("kind") == rec["kind"] and self._where_ok(e, cell)
                and _pattern_match(e.get("path"), rec.get("path"), "path" in e, route=True)
                and _pattern_match(e.get("a"), rec.get("a"), "a" in e)
                and _pattern_match(e.get("b"), rec.get("b"), "b" in e)]

    def match_skipped(self, check: str, cell) -> list:
        return [e["id"] for e in self._applied()
                if e.get("kind") == "skipped-check" and _pattern_match(e.get("check"), check) and self._where_ok(e, cell)]

    def record_hits(self, counts: dict):
        for k, n in counts.items():
            if k in self.hits:
                self.hits[k] += n

    def unused(self):
        return [{"id": e["id"], "file": e["_file"], "kind": e.get("kind")} for e in self.entries if not self.hits.get(e.get("id"))]

    def by_category(self):
        out = {}
        for e in self.entries:
            out[e.get("category")] = out.get(e.get("category"), 0) + 1
        return out
