#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Mechanical checks for PLAN.md acceptance criteria 1 to 15.

  uv run tests/static_checks.py                        every criterion
  uv run tests/static_checks.py --criteria 4,5,12      some of them
  uv run tests/static_checks.py --json out.json        also write the results as JSON
  uv run tests/static_checks.py --strict               NOT-YET counts as a failure (for gates)
  uv run tests/static_checks.py --phase 3              check as of a phase (default: inferred, below)
  uv run tests/static_checks.py --femto DIR            femto checkout for 12 and 13 (default: SOURCE's
                                                       source, then $FEMTO_REPO, then ../femto)
  uv run tests/static_checks.py --root DIR             check another checkout

From tests/run.py: `import static_checks; static_checks.main(argv) -> int` (argv without the program name).

Each criterion reports PASS, FAIL or NOT-YET (with why), plus evidence lines and notes. The exit
status is 1 if any criterion fails (or, with --strict, is not yet checkable), 2 on a usage error,
and 0 otherwise. A criterion with several parts fails if any part fails, is NOT-YET if no part
fails and some part cannot run yet, and passes only when every part ran and passed.

Phase. Some parts depend on the phase (PLAN.md Workflow). The phase is inferred from the Workflow
table's commit subjects reachable from HEAD and its tags: "Add Oracle And Parity Harness" (Phase 0
done, so 1), tag static-multipage or "Convert Pages To Static HTML" (2), tag static-femto or "Move
Styles To femto 3" (3), "Merge Docs Into One Page" (4), "Describe femto 3" (5), "Finish Static Site"
(6). Before Phase 2, site/assets/legacy/ is allowed in git (the Phase 1 gate's exception to 4) and in
dist/ (03 §2 copies it during Phase 1). From Phase 3, dist/ has no per-route docs/ pages, 6 expects
the old routes to 404, and 9 checks the one page's section ids and side nav. 13 applies from Phase 4.

Browser and server criteria (1, 2, 7, 10, and the layout-shift part of 15) are the harness's; this
script reports them NOT-YET with the harness command. 6 starts `wrangler pages dev dist` itself.

Interpretations, where PLAN's wording leaves a choice:
- 4: "git ls-files shows none of" is checked on the files that would be tracked after committing
  the working tree (the index minus files deleted on disk, plus untracked files that are not
  ignored), so a gate passes before its commit. `app/`, `scripts/`, `public/`, `functions/` and
  `site/assets/legacy/` are folders at those paths; `*.jsx` and `*.scss` match at any depth;
  `remix.config.js`, `server.js`, `jsconfig.json`, `.eslintrc.cjs` and `yarn.lock` are top-level (git
  pathspec semantics); `_redirects` matches at any depth (Decision 11). "The check tools" are eslint,
  @eslint/css, html-validate and axe-core (PLAN Repo changes), and all four are required. "A JS
  compat lint if one fits" (03 §7, checked in Phase 0 on 2026-10-30): eslint 10.14.0 is current, and
  two maintained plugins accept it, eslint-plugin-compat 7.0.2 (peer eslint ^9 || ^10, browserslist
  targets) and eslint-plugin-baseline-js 0.7.6 (peer eslint >=9.29 <11, Baseline targets). The check
  accepts COMPAT_LINT, eslint-plugin-baseline-js, because Decision 12's target is Baseline Widely
  Available, the same target @eslint/css's use-baseline checks; @eslint/js and globals are accepted
  as ESLint's own config support. Any other package fails. Pinned means an exact version, and
  optionalDependencies, peerDependencies and bundleDependencies must be empty.
- 11: the forbidden-syntax scans look at code only (comments removed, strings blanked), as femto's
  own checks do; mentions in comments are notes. Every scan (forbidden syntax, color functions,
  smooth scrolling) covers site/**/*.css outside site/vendor/ and site/assets/legacy/ (the frozen
  oracle CSS, deleted in Phase 2), plus <style> and style="" in site HTML; PLAN names site/assets/css/
  for the at-rules, and the site's own CSS anywhere follows the same rules (PROMPT.md, CSS). Decision
  10's class is the class a rule `html.X`, `:root.X` or `.X` sets `scroll-behavior: smooth` on,
  inside `@media (prefers-reduced-motion: no-preference)`, where X appears in site/assets/js/docs.js.
  The lint part proves coverage, not only an exit status, on site/**/*.css and site/**/*.js outside
  vendor/ and assets/legacy/ (PLAN names those globs; inline scripts in site HTML are listed as a
  note, outside the lint). (a) `npm run lint` exits 0, and its script runs eslint without --fix. (b)
  `eslint --print-config` on every such file: CSS has @eslint/css `css/use-baseline` as an error at
  `available: "widely"`; JS has rules on, among them COMPAT_LINT's `use-baseline` (under whatever
  key the config registers it) as an error at Baseline "widely". Allow lists and ignored features
  are exceptions, listed as notes. (c) A planted-violation probe in a temporary copy of the tree (the
  files a commit would hold, node_modules linked; never the repository): one file at a time, a
  feature that is Baseline newly but not widely available is appended after `/* eslint-enable */`,
  and `npm run lint` must exit non-zero and print that feature's use-baseline message once more than
  the clean copy did. The probes (CSS_PROBES, JS_PROBES) are first calibrated against the installed
  tools with a reference config, kept only if reported at "widely" and not at "newly", so the probe
  shows the level of the real run too: a lint script that skips a file, uses another config, or
  runs at "newly" fails. Before Phase 1 there is no lint script, so the lint part is NOT-YET.
  Exceptions in the files: an eslint-disable directive needs "-- reason"; an inline rule
  configuration comment (`/* eslint rule: [...] */`, which print-config never shows) needs one too,
  and one that configures a use-baseline rule fails outright (the level and allow lists belong in
  the config file).
- 14 and 13's No Pico: `git grep -il pico` as PLAN gives it, run once on tracked files and once with
  --untracked (new files a gate has not committed yet), and the union is compared with the list.
- 9: html-validate must be shown to run: `--version` answers the pinned version, and its JSON report
  parses, names only the files given, and (exit 1) holds an error. Empty or unparsable output is a
  tool failure, never a pass.
- 12: also fails when git ignores a vendored file (it would never be committed), whatever the
  working tree holds.
- 13: from Phase 4 (04 §3), on the docs page; the package-name part reads every dist page and
  dist script outside dist/vendor/. femto's package is FEMTO_PACKAGE, @leoherzog/femto (the owner,
  2026-10-30), and femto's package.json at the vendored commit must say so. In package contexts (a
  jsDelivr npm or combine URL, a jsDelivr package page or API URL, an unpkg URL, an npm package page
  or registry URL, an esm.sh, esm.run, Skypack, jspm or cdnjs URL, a name@version specifier, a
  package named in prose ("the femto.css package"), an install command (prose too, a backslash
  continuation joined), and in code, attributes and script strings also a dependency entry, a
  JavaScript import or require specifier, a package @import, and a CSS @import path into a package,
  `@import "femto/css/tokens/base.css"`), any name that means femto (says "femto", or is under
  "leoherzog") other than @leoherzog/femto fails, femto.css among them; so does a jsDelivr GitHub
  URL for femto. Script strings are read one by one and as runs joined with +, and JSON data blocks
  (JSON-LD's downloadUrl) by their string values. File names (femto.css, dist/femto.min.css, CSS's
  `@import url(femto.css)` and `@import "femto.css"`, a relative or absolute path, package.json)
  are not package contexts. femto has no Composer package: a composer command, a Packagist URL or an
  offer ("install ... with Composer", "see femto on Packagist") fails, except in a block (a
  paragraph, cell, code sample, attribute or script string) that also names Pico and no femto
  package, which is read as Pico's (the Migrating from Pico table) and listed as a note; a mention
  that offers nothing ("femto has no Composer package") is listed, and so is an offer its own
  clause denies ("You cannot install femto with Composer", "Nothing is listed on Packagist for
  femto"; a negation before the mention, with no clause break or "but" between them). Other packages (@picocss/pico, wrangler) are listed,
  not judged.
- 15: the /docs HTML budget is read from PLAN.md's "Risks" section: the first sentence that says
  "budget" and gives one or more sizes after it ("400 KB", "60 KB with Brotli", "90 KB gzipped";
  a size without a qualifier is the file's raw size). Until one is recorded that part is NOT-YET.
  Same-origin loading, static part, which fails unless on https://femto.style: URLs that markup
  loads (src, srcset, poster, data, background, loading <link>s, SVG href and <script href>, <base
  href>, which moves every relative URL, <iframe srcdoc> documents and data: documents in an
  iframe, frame, object or embed, inline and attribute CSS, import maps and speculation rules),
  url(), @import and image-set() strings in dist CSS (not @namespace; CSS escapes decoded, as in
  url("\\68ttps://x")), web app manifest icons, and in JS (dist files, inline <script>s, on*
  attributes, javascript: URLs, percent-decoded) static and dynamic imports, importScripts(), and
  the HTML a script hands the parser (document.write() and writeln(), also with .call() and
  .apply(), insertAdjacentHTML(), innerHTML =, also as document["write"]), whose elements load like
  markup; a javascript: URL's string result is a document, so every string in it that holds markup
  is read as HTML, and so is every string in every script once any script uses an HTML sink in a
  form the check cannot follow to its argument (an alias, .bind(), Reflect.apply(), a computed or
  destructured name; html_sink_aliases). A worker's loads are in no page's Resource Timing, so every
  script started in a worker (new Worker(), new SharedWorker(), serviceWorker.register(),
  importScripts(), a worklet's addModule()) is read strictly: any absolute URL of another origin in
  it fails, and so does a worker script that cannot be found in dist/; a worker API used in any
  other form (new (Worker)(...), const W = Worker, a serviceWorker kept in a variable;
  worker_aliases) reads every script strictly. URLs are read as a browser reads them (trimmed, tabs
  and newlines dropped, a backslash as a slash; http://femto.style is another origin). JS is read as
  espree's tokens (ESLint's parser, from node_modules), so a regex is told from a division exactly;
  a script espree cannot read fails (Decision 12's JavaScript always parses) and is read with a
  heuristic tokenizer for the rest. Template literals are followed into their substitutions and
  string escapes decoded (`https:\\/\\/x`). Any other absolute URL in a JS string (any host; the
  SVG, XHTML, XLink and MathML namespace URIs excepted), and a URL whose host is built at run time,
  is a note, not judged: a string can be a fetch(), an inserted element or text a script only
  displays (the picker's CDN <link> sample), which a static read cannot tell apart. Loads made at
  run time are the harness's: `pages --b dist` reads every dist document's Resource Timing entries
  and the proxy's CSP reports (workers, frames in closed shadow roots), and fails on a cross-origin
  load whatever started it (targets.json same_origin). Render-blocking: a classic script (HTML's
  JavaScript MIME types, or a language attribute) with a source and neither async nor defer, an
  inline classic script outside <head>, a second one in it, a classic script that document.write()
  writes (an inline one, or one with a source and neither async nor defer; any string that holds a
  classic script once HTML is read from every string), and blocking="render" on any element (a
  Decision 12 violation); scripts in <template> or <noscript> never run on load. The run-time loads and the layout-shift part (the behavior mode,
  Phase 1) need a browser, so 15 stays NOT-YET here, like 1, 2, 7 and 10.
"""

from __future__ import annotations

import argparse
import atexit
import gzip
import hashlib
import html
import http.client
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, unquote_to_bytes, urlsplit

WRANGLER = "4.156.0"  # latest on npm, checked 2026-10-30; package.json's exact pin wins once it has one
HTML_VALIDATE = "11.17.0"  # latest on npm, checked 2026-10-30; same rule
MAX_LINES = 12
SITE_ORIGIN = "https://femto.style"
DOCS_URL = "https://femto.style/docs"
FEMTO_GITHUB = "github.com/leoherzog/femto"
SECTION_ID = re.compile(r"^[a-z]+(-[a-z]+)?$")
CATEGORIES = ("dropped-route", "femto-divergence", "merge-layout", "id-rename", "oracle-bug", "highlight", "asset-path",
              "browser-limit")
PICO_ALLOWED = (
    "LICENSE.md",
    "README.md",
    "site/partials/footer.html",
    "site/docs/sections/migration.html",
)
# femto's own files, which criterion 12 pins to its commit: its LICENSE.md and the MIT banners in its
# CSS keep Pico's copyright line (from 74e65f6e on).
PICO_ALLOWED_DIR = "site/vendor/femto/"
PICO_SPEC = ["--", ".", ":!docs/research", ":!tests", ":!PLAN.md", ":!PROMPT.md"]
SCRIPTS = {"build", "dev", "deploy", "vendor", "lint"}
REQUIRED_DEV = {"prismjs", "wrangler"}
CHECK_TOOLS = {"eslint", "@eslint/css", "html-validate", "axe-core"}
COMPAT_LINT = "eslint-plugin-baseline-js"  # Phase 0's choice (docstring, 4); 0.7.6 on 2026-10-30
LINT_SUPPORT = {"@eslint/js", "globals", COMPAT_LINT}
SVG_NS = re.compile(r"^https?://www\.w3\.org/(2000/svg|1999/xhtml|1999/xlink|1998/Math/MathML|XML/1998/namespace)$")
EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")
VENDORED = ("dist", "css", "LICENSE.md")
COLORS = ("amber", "azure", "blue", "cyan", "fuchsia", "green", "grey", "indigo", "jade", "lime", "orange",
          "pink", "pumpkin", "purple", "red", "sand", "slate", "violet", "yellow", "zinc")

# The oracle's docs routes (01 §1, 02 §1). /docs itself is Quick start.
KEPT_ROUTES = (
    "version-picker", "color-schemes", "rtl", "css-variables", "colors", "container", "landmarks-section",
    "grid", "overflow-auto", "typography", "link", "button", "table", "forms", "forms/input", "forms/textarea",
    "forms/select", "forms/checkboxes", "forms/radios", "forms/switch", "forms/range", "accordion", "card",
    "dropdown", "group", "loading", "modal", "nav", "progress", "tooltip",
)
DROPPED_ROUTES = ("classless", "conditional", "sass", "maintenance", "v2", "mission", "usage-scenarios", "brand", "built-with")
COLOR_ROUTES = tuple(f"version-picker/{c}" for c in COLORS if c != "azure")

PHASE_COMMITS = (
    (1, "Add Oracle And Parity Harness"),
    (2, "Convert Pages To Static HTML"),
    (3, "Move Styles To femto 3"),
    (4, "Merge Docs Into One Page"),
    (5, "Describe femto 3"),
    (6, "Finish Static Site"),
)
PHASE_TAGS = ((2, "static-multipage"), (3, "static-femto"))

HARNESS = {  # tests/run.py modes (tests/harness/cli.py); styles and behavior are announced there, not built yet
    1: "uv run tests/run.py self --full (the oracle against itself in the PLAN.md matrix: Chrome, Firefox, then Safari serialized; the owner's dark Safari pass too)",
    7: "uv run tests/run.py behavior (Chrome, Firefox and Safari; the mode is not implemented yet)",
    10: "an axe-core pass in the harness (Chrome and Firefox, light and dark, 375 and 1300); tests/run.py has no such mode yet",
    15: "uv run tests/run.py behavior (cold load of /docs#input in Chrome: layout shift < 0.01, Input's heading within 2 px of its scroll-padding line; the mode is not implemented yet)",
}
HARNESS_15_LOADS = ("uv run tests/run.py pages --a oracle --b dist --full: every dist document's Resource Timing entries "
                    "and the proxy's CSP reports (workers and frames the page cannot read included), where a cross-origin "
                    "load fails the run whatever code or markup started it")

FORBIDDEN = [
    ("@layer", re.compile(r"@layer\b", re.I)),
    ("@scope", re.compile(r"@scope\b", re.I)),
    ("if(", re.compile(r"(?<![\w-])if\(", re.I)),
    ("@function", re.compile(r"@function\b", re.I)),
    ("@mixin", re.compile(r"@mixin\b", re.I)),
    ("@apply", re.compile(r"@apply\b", re.I)),
    ("@custom-media", re.compile(r"@custom-media\b", re.I)),
    ("@container style(", re.compile(r"@container\b[^{;]*?(?<![\w-])style\(", re.I)),
]
COLOR_FUNCTION = re.compile(
    r"(?<![\w-])(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|color-mix|light-dark|contrast-color)\(", re.I
)
SMOOTH = re.compile(r"(?<![\w-])scroll-behavior\s*:\s*smooth\b", re.I)
REDUCED_MOTION_OK = re.compile(r"@media\b[^{]*prefers-reduced-motion\s*:\s*no-preference", re.I)
SMOOTH_SELECTOR = re.compile(r"^(?:html|:root)?\.([A-Za-z_][\w-]*)$")


# ---------------------------------------------------------------------------- results


class Result:
    def __init__(self, cid: int, title: str):
        self.id, self.title = cid, title
        self.failures: list[str] = []
        self.evidence: list[str] = []
        self.notes: list[str] = []
        self.pending: list[str] = []

    def fail(self, line: str):
        self.failures.append(line)

    def fails(self, header: str, items: list[str], what: str = "more"):
        """One failure line plus indented, capped detail lines."""
        if items:
            self.failures.append(header)
            self.failures += ["    " + i for i in capped(items, what)]

    def ok(self, line: str):
        self.evidence.append(line)

    def note(self, line: str):
        self.notes.append(line)

    def not_yet(self, why: str):
        self.pending.append(why)

    @property
    def state(self) -> str:
        return "fail" if self.failures else "not-yet" if self.pending else "pass"

    def as_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "state": self.state, "why": self.pending,
                "failures": self.failures, "evidence": self.evidence, "notes": self.notes}

    def print(self):
        print(f"\n== Criterion {self.id}: {self.title}")
        print(self.state.upper())
        for prefix, lines in (("  FAIL ", self.failures), ("  why: ", self.pending), ("  ", self.evidence), ("  note: ", self.notes)):
            for line in lines:
                print(prefix + line)


def capped(items: list[str], what: str = "more") -> list[str]:
    out = list(items[:MAX_LINES])
    if len(items) > MAX_LINES:
        out.append(f"... and {len(items) - MAX_LINES} {what}")
    return out


# ---------------------------------------------------------------------------- git and files


def git(root: Path, *args: str, check: bool = False, binary: bool = False, input: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(root), *args], capture_output=True,
                          text=not binary, check=check, input=input)


def effective_files(root: Path) -> list[str]:
    """Files that would be tracked after committing the working tree: the index minus files
    deleted on disk, plus untracked files that are not ignored."""
    z = lambda *a: [p for p in git(root, "ls-files", "-z", *a).stdout.split("\0") if p]
    return sorted((set(z()) - set(z("--deleted"))) | set(z("--others", "--exclude-standard")))


def rel(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


def files_under(d: Path, suffixes: tuple[str, ...], skip: tuple[Path, ...] = ()) -> list[Path]:
    if not d.is_dir():
        return []
    out = []
    for p in sorted(d.rglob("*")):
        if p.is_file() and p.suffix.lower() in suffixes and not any(p.is_relative_to(s) for s in skip):
            out.append(p)
    return out


def read_blobs(repo: Path, shas: list[str]) -> list[bytes]:
    """Blob contents through one `git cat-file --batch` call."""
    out = git(repo, "cat-file", "--batch", binary=True, input=("\n".join(shas) + "\n").encode(), check=True).stdout
    blobs, offset = [], 0
    for sha in shas:
        eol = out.index(b"\n", offset)
        header = out[offset:eol].decode().split()
        if header[0] != sha or header[1] != "blob":
            raise RuntimeError(f"git cat-file returned {' '.join(header)} for {sha}")
        size = int(header[2])
        blobs.append(out[eol + 1 : eol + 1 + size])
        offset = eol + 1 + size + 1
    return blobs


def free_port() -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port != 8790:
            return port


# ---------------------------------------------------------------------------- CSS scanning


def scan_css(text: str) -> tuple[str, str, list[tuple[int, str]]]:
    """Return (code without comments, code without comments or string contents, comments).

    Comments are found outside strings; unquoted url(...) contents count as strings. Blanked text
    keeps its newlines, so offsets and line numbers stay valid."""
    no_comments, masked, comments = list(text), list(text), []

    def blank(chars: list[str], start: int, end: int):
        for k in range(start, min(end, len(chars))):
            if chars[k] != "\n":
                chars[k] = " "

    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            blank(masked, i + 1, min(j, n))
            i = j + 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            comments.append((i, text[i:j]))
            blank(no_comments, i, j)
            blank(masked, i, j)
            i = j
        elif text[i : i + 4].lower() == "url(" and (i == 0 or not re.match(r"[\w-]", text[i - 1])):
            j = i + 4
            while j < n and text[j] in " \t\n":
                j += 1
            if j < n and text[j] not in "\"'":
                k = text.find(")", j)
                k = n if k < 0 else k
                blank(masked, j, k)
                i = k
            else:
                i = j
        else:
            i += 1
    return "".join(no_comments), "".join(masked), comments


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def call_args(masked: str, open_paren: int) -> str:
    depth, i = 0, open_paren
    while i < len(masked):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return masked[open_paren + 1 : i]
        i += 1
    return masked[open_paren + 1 :]


def depth0(args: str) -> str:
    out, depth = [], 0
    for c in args:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0:
            out.append(c)
    return "".join(out)


def rule_preludes(masked: str) -> list[tuple[int, str]]:
    """(offset, prelude) for every block at any depth."""
    out, last = [], 0
    for i, c in enumerate(masked):
        if c in ";}":
            last = i + 1
        elif c == "{":
            prelude = masked[last:i]
            stripped = prelude.lstrip()
            out.append((last + len(prelude) - len(stripped), stripped.rstrip()))
            last = i + 1
    return out


def split_selectors(prelude: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for c in prelude:
        depth += c in "(["
        depth -= c in ")]"
        if c == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += c
    return parts + [cur.strip()]


def enclosing_blocks(masked: str, offsets: list[int]) -> dict[int, list[str]]:
    """For each offset, the preludes of the blocks around it, outermost first."""
    want, out, stack, last = sorted(set(offsets)), {}, [], 0
    k = 0
    for i, c in enumerate(masked):
        while k < len(want) and want[k] == i:
            out[i] = list(stack)
            k += 1
        if c == "{":
            stack.append(" ".join(masked[last:i].split()))
            last = i + 1
        elif c == "}":
            if stack:
                stack.pop()
            last = i + 1
        elif c == ";":
            last = i + 1
    for o in want[k:]:
        out[o] = list(stack)
    return out


CSS_ESC = r"(?:\\[0-9A-Fa-f]{1,6}[ \t\n\r\f]?|\\[^\n\r\f0-9A-Fa-f])"
CSS_IDENT = rf"(?:[\w-]|{CSS_ESC})+"


def css_unescape(s: str) -> str:
    """CSS escapes decoded as a browser decodes them (CSS Syntax 4.3.7): a backslash and 1 to 6 hex
    digits (and one following space) is that code point, a backslash before a newline in a string
    is nothing, and a backslash before any other character is that character. So
    url("\\68ttps://x") and url(https\\:\\/\\/x) are https://x."""
    def one(m: re.Match) -> str:
        e = m.group(0)[1:]
        if e[:1] in "\n\r\f":
            return ""
        h = re.match(r"[0-9A-Fa-f]{1,6}", e)
        if not h:
            return e
        cp = int(h.group(0), 16)
        return "\ufffd" if cp == 0 or cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF else chr(cp)
    return re.sub(r"\\(?:[0-9A-Fa-f]{1,6}[ \t\n\r\f]?|\r\n|[\s\S])", one, s)


def css_urls(code: str) -> list[tuple[int, str]]:
    """(offset, url) for every URL comment-free CSS loads: url(), @import "…" and the strings of
    image-set(), with CSS escapes decoded in the names (u\\72l(), @\\69mport) and in the URLs,
    as css-tree and the browser read them. The url() of @namespace names a namespace and loads
    nothing."""
    code = re.sub(rf"@{CSS_IDENT}[^;{{}}]*", lambda m: re.sub(r"[^\n]", " ", m.group(0))
                  if css_unescape(re.match(rf"@({CSS_IDENT})", m.group(0)).group(1)).lower() == "namespace" else m.group(0),
                  code)
    out = []
    for m in re.finditer(rf"(?<![\w\\-])({CSS_IDENT})\(", code):
        name = css_unescape(m.group(1)).lower()
        if name == "url":
            u = re.match(r"\s*(['\"]?)(.*?)\1\s*\)", code[m.end():], re.S)
            if u:
                out.append((m.start(), css_unescape(u.group(2)).strip()))
        elif name in ("image-set", "-webkit-image-set"):
            out += [(m.start(), css_unescape(x.group(2))) for x in re.finditer(r"([\"'])((?:\\[\s\S]|(?!\1).)*)\1",
                                                                               call_args(code, m.end() - 1))]
    for m in re.finditer(rf"@({CSS_IDENT})\s*(['\"])((?:\\[\s\S]|(?!\2).)*)\2", code):
        if css_unescape(m.group(1)).lower() == "import":
            out.append((m.start(), css_unescape(m.group(3))))
    return sorted(out)


# ---------------------------------------------------------------------------- HTML


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
IMPLIED_END = {  # start tag: (open elements it closes, elements that stop the search)
    "li": ({"li"}, {"ul", "ol", "menu"}),
    "dt": ({"dt", "dd"}, {"dl"}),
    "dd": ({"dt", "dd"}, {"dl"}),
    "option": ({"option"}, {"select", "datalist", "optgroup"}),
    "optgroup": ({"optgroup", "option"}, {"select"}),
    "tr": ({"tr", "td", "th"}, {"table", "thead", "tbody", "tfoot"}),
    "td": ({"td", "th"}, {"tr", "table"}),
    "th": ({"td", "th"}, {"tr", "table"}),
    "thead": ({"thead", "tbody", "tfoot", "tr", "td", "th"}, {"table"}),
    "tbody": ({"thead", "tbody", "tfoot", "tr", "td", "th"}, {"table"}),
    "tfoot": ({"thead", "tbody", "tfoot", "tr", "td", "th"}, {"table"}),
}
CLOSES_P = {"address", "article", "aside", "blockquote", "details", "dialog", "div", "dl", "fieldset", "figcaption",
            "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "main",
            "menu", "nav", "ol", "p", "pre", "search", "section", "table", "ul"}
P_SCOPE = {"button", "html", "body", "table", "td", "th", "template", "object", "caption"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line")

    def __init__(self, tag: str, attrs: dict[str, str], parent: Node | None, line: int):
        self.tag, self.attrs, self.children, self.parent, self.line = tag, attrs, [], parent, line

    def iter(self):
        yield self
        for c in self.children:
            if isinstance(c, Node):
                yield from c.iter()

    def find_all(self, *tags: str) -> list[Node]:
        return [n for n in self.iter() if n.tag in tags]

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def ancestors(self):
        p = self.parent
        while p is not None:
            yield p
            p = p.parent

    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def in_template(self) -> bool:
        return any(a.tag == "template" for a in self.ancestors())


class TreeBuilder(HTMLParser):
    """A small tree builder: enough of HTML's tree construction for ancestry and ids."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None, 0)
        self.stack = [self.root]

    def _attrs(self, attrs) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, v in attrs:
            out.setdefault(k, v if v is not None else "")
        return out

    def _pop_to(self, index: int):
        del self.stack[index:]

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            for i in range(len(self.stack) - 1, 0, -1):
                if self.stack[i].tag == "head":
                    self._pop_to(i)
                    break
        if tag in IMPLIED_END:
            closes, stop = IMPLIED_END[tag]
            for i in range(len(self.stack) - 1, 0, -1):
                t = self.stack[i].tag
                if t in closes:
                    self._pop_to(i)
                    break
                if t in stop:
                    break
        if tag in CLOSES_P:
            for i in range(len(self.stack) - 1, 0, -1):
                t = self.stack[i].tag
                if t == "p":
                    self._pop_to(i)
                    break
                if t in P_SCOPE:
                    break
        node = Node(tag, self._attrs(attrs), self.stack[-1], self.getpos()[0])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, self._attrs(attrs), self.stack[-1], self.getpos()[0])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self._pop_to(i)
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text: str) -> Node:
    b = TreeBuilder()
    b.feed(text)
    b.close()
    return b.root


def page_url(dist: Path, p: Path) -> str:
    """The URL path Cloudflare Pages serves an HTML file at: x.html at /x, x/index.html at /x/."""
    r = p.relative_to(dist).as_posix()[: -len(".html")]
    if r == "index":
        return "/"
    if r.endswith("/index"):
        return "/" + r[: -len("index")]
    return "/" + r


def section_target(href: str) -> str | None:
    """The fragment of a link into the docs page (#id, /docs#id or https://femto.style/docs#id)."""
    u = urlsplit(href.strip())
    if (u.scheme or u.netloc) and (u.scheme, u.netloc) != ("https", "femto.style"):
        return None
    if u.path in ("", "/docs") and u.fragment:
        return unquote(u.fragment)
    return None


def menu_ids(menu) -> list[str]:
    """Section ids from site/docs/menu.json, whatever its nesting: every object with a string "id"
    that does not itself hold a list of objects with ids (a category)."""
    out = []

    def walk(x):
        if isinstance(x, dict):
            children = [v for v in x.values() if isinstance(v, list) and any(isinstance(i, dict) and "id" in i for i in v)]
            if isinstance(x.get("id"), str) and not children:
                out.append(x["id"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(menu)
    return out


# ---------------------------------------------------------------------------- context


class Context:
    def __init__(self, root: Path, phase: int, phase_why: str, femto: str | None):
        self.root, self.phase, self.phase_why, self.femto_arg = root, phase, phase_why, femto
        self.site, self.dist = root / "site", root / "dist"
        self._pages: dict[Path, Node] = {}
        self.cache: dict[str, object] = {}

    def page(self, p: Path) -> Node:
        if p not in self._pages:
            self._pages[p] = parse_html(p.read_text(encoding="utf-8", errors="replace"))
        return self._pages[p]

    def reset_pages(self):
        self._pages.clear()

    def dist_pages(self) -> list[Path]:
        return files_under(self.dist, (".html",))

    def package(self) -> dict | None:
        p = self.root / "package.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def pinned(self, name: str, default: str) -> str:
        pkg = self.package() or {}
        v = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}.get(name, "")
        return v if EXACT_VERSION.match(v) else default

    def source(self) -> dict[str, str] | None:
        p = self.site / "vendor/femto/SOURCE"
        if not p.is_file():
            return None
        out = {}
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
        return out

    def femto_repo(self, commit: str) -> tuple[Path | None, list[str]]:
        """The first femto checkout that holds commit: --femto, SOURCE's source, $FEMTO_REPO, ../femto."""
        src = (self.source() or {}).get("source")
        tried, seen = [], set()
        for cand in (self.femto_arg, src, os.environ.get("FEMTO_REPO"), "../femto"):
            if not cand:
                continue
            path = (self.root / cand).resolve() if not os.path.isabs(cand) else Path(cand)
            if path in seen:
                continue
            seen.add(path)
            tried.append(str(path))
            if path.is_dir() and git(path, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0:
                return path, tried
        return None, tried


def infer_phase(root: Path) -> tuple[int, str]:
    subjects = set(git(root, "log", "--format=%s").stdout.splitlines())
    tags = set(git(root, "tag", "--merged", "HEAD").stdout.split())
    phase, why = 0, "no Workflow commit or tag yet"
    for n, subject in PHASE_COMMITS:
        if subject in subjects and n > phase:
            phase, why = n, f'commit "{subject}"'
    for n, tag in PHASE_TAGS:
        if tag in tags and n > phase:
            phase, why = n, f"tag {tag}"
    return phase, why


# ---------------------------------------------------------------------------- criteria 1, 2, 7, 10


def harness_only(cid: int, title: str, command: str):
    def check(ctx: Context) -> Result:
        r = Result(cid, title)
        r.not_yet(f"needs browsers: {command}")
        run_py = ctx.root / "tests/run.py"
        r.note("tests/run.py " + ("exists" if run_py.is_file() else "does not exist yet") + "; command names follow 03 §7's modes")
        return r

    return check


criterion_1 = harness_only(1, "The harness compares the oracle against itself with zero differences in Chrome, Firefox and Safari", HARNESS[1])
criterion_7 = harness_only(7, "Docs behavior: the suite passes in Chrome, Firefox and Safari", HARNESS[7])
criterion_10 = harness_only(10, "Accessibility: axe-core finds no serious or critical violation", HARNESS[10])


def criterion_2(ctx: Context) -> Result:
    r = Result(2, "Each parity gate (Phases 1, 2 and 3) reports zero unregistered differences in its full matrix")
    gates = {
        1: "uv run tests/run.py pages --a oracle --b dist --full (the static routes against the oracle; Chrome and Firefox)",
        2: "uv run tests/run.py styles --full (against tag static-multipage; the mode is not implemented yet)",
        3: "uv run tests/run.py pages --full (each section against its route's [role=document] at tag static-femto; then Safari, light and dark)",
    }
    current = gates.get(min(max(ctx.phase, 1), 3))
    r.not_yet(f"needs browsers; the gate for phase {ctx.phase} is: {current}")
    for n, cmd in gates.items():
        r.note(f"Phase {n} gate: {cmd}")
    return r


# ---------------------------------------------------------------------------- criterion 3


def criterion_3(ctx: Context) -> Result:
    r = Result(3, "Every registry entry has a category from the list and a reason")
    d = ctx.root / "tests/divergences"
    files = sorted(p for p in d.glob("*.json") if p.name != "schema.json") if d.is_dir() else []
    if not d.is_dir():
        r.not_yet("tests/divergences/ does not exist yet (the harness port writes it)")
        return r
    counts: dict[str, int] = {}
    total, ids, bad = 0, {}, []
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            r.fail(f"{rel(ctx.root, p)}: not valid JSON: {exc}")
            continue
        if not isinstance(data, list):
            r.fail(f"{rel(ctx.root, p)}: not a JSON array of entries")
            continue
        for i, e in enumerate(data):
            total += 1
            where = f"{p.name}[{i}]" + (f" {e.get('id')}" if isinstance(e, dict) and e.get("id") else "")
            if not isinstance(e, dict):
                bad.append(f"{where}: not an object")
                continue
            cat, reason = e.get("category"), e.get("reason")
            if cat not in CATEGORIES:
                bad.append(f"{where}: category {cat!r} is not one of {', '.join(CATEGORIES)}")
            else:
                counts[cat] = counts.get(cat, 0) + 1
            if not isinstance(reason, str) or not reason.strip():
                bad.append(f"{where}: no reason")
            if isinstance(e.get("id"), str):
                ids.setdefault(e["id"], []).append(where)
    r.fails(f"{len(bad)} registry entr{'y' if len(bad) == 1 else 'ies'} without a listed category or a reason:", bad, "more entries")
    r.ok(f"{total} entries in {len(files)} files under tests/divergences/ (schema.json excluded)")
    if counts:
        r.ok("by category: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if total == 0:
        r.note("the registry has no entries yet, so the criterion holds vacuously")
    dups = [f"{k}: {', '.join(v)}" for k, v in ids.items() if len(v) > 1]
    for line in capped(dups):
        r.note(f"repeated id {line}")
    return r


# ---------------------------------------------------------------------------- criterion 4


def criterion_4(ctx: Context) -> Result:
    r = Result(4, "Tree and packages")
    root = ctx.root
    files = effective_files(root)
    r.ok(f"{len(files)} files tracked or to be tracked (git ls-files, minus deleted, plus untracked not ignored)")
    top = lambda name: (lambda f: f == name)
    patterns = [
        ("app/", lambda f: f.startswith("app/")),
        ("*.jsx", lambda f: f.endswith(".jsx")),
        ("*.scss", lambda f: f.endswith(".scss")),
        ("remix.config.js", top("remix.config.js")),
        ("server.js", top("server.js")),
        ("jsconfig.json", top("jsconfig.json")),
        (".eslintrc.cjs", top(".eslintrc.cjs")),
        ("yarn.lock", top("yarn.lock")),
        ("scripts/", lambda f: f.startswith("scripts/")),
        ("public/", lambda f: f.startswith("public/")),
        ("functions/", lambda f: f.startswith("functions/")),
        ("_redirects", lambda f: f.rsplit("/", 1)[-1] == "_redirects"),
        ("site/assets/legacy/", lambda f: f.startswith("site/assets/legacy/")),
    ]
    clean = []
    for label, match in patterns:
        hits = [f for f in files if match(f)]
        if not hits:
            clean.append(label)
        elif label == "site/assets/legacy/" and ctx.phase < 2:
            r.note(f"{len(hits)} files under site/assets/legacy/: allowed before Phase 2 (the Phase 1 gate's exception)")
        else:
            r.fails(f"git ls-files shows {len(hits)} {label} file(s):", hits, "more files")
    if clean:
        r.ok("none of: " + ", ".join(clean))

    pkg = ctx.package()
    if pkg is None:
        r.fail("package.json is missing")
        return r
    deps = pkg.get("dependencies")
    if deps:
        r.fail(f"package.json has {len(deps)} dependencies: {', '.join(sorted(deps))[:300]}")
    else:
        r.ok("package.json has no dependencies" + (" (an empty object)" if deps == {} else ""))
    for field in ("optionalDependencies", "peerDependencies", "bundleDependencies", "bundledDependencies"):
        val = pkg.get(field)
        if val:
            r.fail(f"package.json has {field}: {', '.join(sorted(val)) if isinstance(val, dict) else val}"[:300])
    dev = pkg.get("devDependencies") or {}
    missing = sorted((REQUIRED_DEV | CHECK_TOOLS) - set(dev))
    if missing:
        r.fail(f"devDependencies lack {', '.join(missing)} (prismjs, wrangler and the check tools: eslint, @eslint/css, "
               "html-validate, axe-core)")
    other = []
    for name in sorted(dev):
        if name in REQUIRED_DEV or name in CHECK_TOOLS:
            continue
        if name in LINT_SUPPORT:
            r.note(f"devDependency {name} accepted as " + ("the JS compat lint (Phase 0's choice)" if name == COMPAT_LINT
                                                           else "ESLint config support"))
        else:
            other.append(name)
    r.fails(f"{len(other)} devDependencies are not prismjs, wrangler, a check tool, {COMPAT_LINT}, @eslint/js or globals:",
            other, "more packages")
    loose = [f"{k}: {v}" for k, v in sorted(dev.items()) if not EXACT_VERSION.match(str(v))]
    r.fails(f"{len(loose)} devDependencies are not pinned to an exact version:", loose, "more packages")
    if not missing and not other and not loose:
        r.ok(f"devDependencies, all pinned: {', '.join(f'{k} {v}' for k, v in sorted(dev.items()))}")
    scripts = pkg.get("scripts") or {}
    if set(scripts) != SCRIPTS:
        extra, lack = sorted(set(scripts) - SCRIPTS), sorted(SCRIPTS - set(scripts))
        r.fail(f"scripts are not exactly build, dev, deploy, vendor and lint: missing {lack or 'none'}; "
               f"extra ({len(extra)}) {', '.join(extra)[:300] or 'none'}")
    else:
        r.ok("scripts: " + ", ".join(sorted(scripts)))
    if "build" in scripts and "build.mjs" not in scripts["build"]:
        r.note(f"the build script does not run build.mjs (Decision 3): {scripts['build']!r}")
    if "deploy" in scripts and "wrangler pages deploy dist" not in scripts["deploy"]:
        r.note(f"the deploy script does not run wrangler pages deploy dist (Decision 11): {scripts['deploy']!r}")
    return r


# ---------------------------------------------------------------------------- criterion 5


def snapshot(d: Path) -> dict[str, str]:
    out = {}
    for p in sorted(d.rglob("*")):
        key = p.relative_to(d).as_posix()
        if p.is_symlink():
            out[key] = "symlink:" + os.readlink(p)
        elif p.is_file():
            out[key] = hashlib.sha256(p.read_bytes()).hexdigest()
        elif p.is_dir():
            out[key + "/"] = "dir"
    return out


def criterion_5(ctx: Context) -> Result:
    r = Result(5, "Build output")
    root, dist = ctx.root, ctx.dist
    if not (root / "build.mjs").is_file():
        r.fail("no build.mjs")
        return r
    scripts = (ctx.package() or {}).get("scripts") or {}
    if "build" not in scripts:
        r.fail("package.json has no build script")
        return r
    trees = []
    for run in (1, 2):
        start = time.monotonic()
        proc = subprocess.run(["npm", "run", "build", "--silent"], cwd=root, capture_output=True, text=True, timeout=900)
        if proc.returncode != 0:
            r.fail(f"npm run build (run {run}) exited {proc.returncode}: {(proc.stderr or proc.stdout).strip()[-400:]}")
            return r
        if not dist.is_dir():
            r.fail(f"npm run build (run {run}) wrote no dist/")
            return r
        trees.append(snapshot(dist))
        r.ok(f"npm run build, run {run}: {sum(1 for k in trees[-1] if not k.endswith('/'))} files in {time.monotonic() - start:.1f} s")
    ctx.reset_pages()
    a, b = trees
    changed = sorted(k for k in a.keys() & b.keys() if a[k] != b[k])
    only = sorted(a.keys() ^ b.keys())
    r.fails(f"{len(changed)} file(s) differ between the two builds:", changed, "more files")
    r.fails(f"{len(only)} path(s) exist after only one of the two builds:", only, "more paths")
    if not changed and not only:
        r.ok("the two dist/ trees are byte-identical")
    files = [k for k in b if not k.endswith("/")]
    for label, prefix in (("partials/", "partials/"), ("docs/sections/", "docs/sections/"), ("assets/legacy/", "assets/legacy/")):
        hits = [f for f in files if f.startswith(prefix)]
        if hits and prefix == "assets/legacy/" and ctx.phase < 2:
            r.note(f"dist/ holds {len(hits)} files from assets/legacy/: 03 §2 copies them during Phase 1")
        else:
            r.fails(f"dist/ holds {len(hits)} file(s) from {label}:", hits, "more files")
    # Copies of those sources under another name.
    sources = {}
    for sub in ("partials", "docs/sections", "assets/legacy"):
        folder = ctx.site / sub
        if (sub == "assets/legacy" and ctx.phase < 2) or not folder.is_dir():
            continue
        for p in sorted(folder.rglob("*")):
            if p.is_file() and p.stat().st_size > 0:
                sources.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), rel(root, p))
    copies = [f"dist/{f} is a copy of {sources[b[f]]}" for f in files if b[f] in sources]
    r.fails(f"{len(copies)} dist/ file(s) are copies of partials, section or legacy files:", copies, "more files")
    if not any(f.startswith(("partials/", "docs/sections/")) for f in files) and not copies:
        r.ok("dist/ holds nothing from partials/ or docs/sections/" + ("" if ctx.phase < 2 else " or assets/legacy/"))
    per_route = [f for f in files if f.startswith("docs/") and f.endswith(".html")]
    if ctx.phase >= 3:
        r.fails(f"dist/docs/ holds {len(per_route)} per-route page(s) (none from Phase 3):", per_route, "more pages")
        if not per_route:
            r.ok("no per-route docs/ pages (Phase 3 on)")
    elif per_route:
        r.note(f"dist/docs/ holds {len(per_route)} per-route pages, expected before Phase 3")
    if "docs/index.html" in files:
        r.note("dist/docs/index.html exists: Decision 11 says never write it (/docs/ must 308 to /docs)")
    return r


# ---------------------------------------------------------------------------- criterion 6

# Paths that Cloudflare Pages answers otherwise than 404 by its own rules (pretty URLs: a page's .html
# name and an index page's name redirect to the clean URL, and 404.html is an ordinary page at /404).
# Decision 11 forbids _redirects, so the site cannot change them. Criterion 6 says "any other path
# answers 404"; these are probed so that each answers exactly as recorded here (anything else fails),
# and each is listed as a note for the owner to accept in PLAN.md Risks (Cloudflare) or not.
# path: (status, Location path or None, what Pages does)
PAGES_INHERENT = {
    "/404": (200, None, "serves dist/404.html as an ordinary page, with status 200"),
    "/404.html": (308, "/404", "redirects a page's .html name to its clean URL"),
    "/index": (308, "/", "redirects an index page's name to its folder"),
    "/index.html": (308, "/", "redirects index.html to its folder"),
    "/docs/index": (308, "/docs/", "redirects an index page's name to its folder, which then redirects to /docs"),
    "/docs/forms/input.html": (308, "/docs/forms/input", "redirects a page's .html name to its clean URL"),
}


def criterion_6(ctx: Context) -> Result:
    r = Result(6, "URLs served under wrangler pages dev dist")
    dist = ctx.dist
    if not dist.is_dir():
        r.not_yet("no dist/ to serve (npm run build writes it)")
        return r
    not_found = dist / "404.html"
    if not not_found.is_file():
        r.fail("dist/404.html is missing (Decision 11: always ship a top-level 404.html)")
    pages = sorted({page_url(dist, p) for p in ctx.dist_pages() if p.relative_to(dist).as_posix() != "404.html"})
    themes = sorted(p.stem for p in (ctx.site / "vendor/femto/css/themes").glob("*.css")) or list(COLORS)
    ok_200 = {"/", "/docs"} | set(pages)
    ok_200 |= {f"/docs?theme={c}" for c in themes}
    old = {f"/docs/{x}" for x in KEPT_ROUTES + COLOR_ROUTES}
    gone = {f"/docs/{x}" for x in DROPPED_ROUTES} | {"/docs/v1/", "/no-such-page", "/docs/no-such-section", "/assets/no-such-file.css"}
    # The oracle's static Pico v1 pages (tests/oracle-routes.json, kind v1-page) are old paths too.
    routes_file = ctx.root / "tests/oracle-routes.json"
    if routes_file.is_file():
        gone |= {r["path"] for r in json.loads(routes_file.read_text(encoding="utf-8")).get("routes", [])
                 if r.get("kind") == "v1-page"}
    if ctx.phase >= 3:
        gone |= old
        ok_200 -= old
    else:
        ok_200 |= old
    for name in ("/examples", "/demo"):
        if name not in pages:
            r.note(f"{name} is not in dist/ (PLAN: per the Open questions), so it is not expected to answer 200")
    version = ctx.pinned("wrangler", WRANGLER)
    tmp = Path(tempfile.mkdtemp(prefix="femto-style-wrangler-"))
    port, inspector = free_port(), free_port()
    log_path = tmp / "wrangler.log"
    cmd = ["npx", "--yes", f"wrangler@{version}", "pages", "dev", str(dist), "--ip", "127.0.0.1", "--port", str(port),
           "--inspector-port", str(inspector), "--persist-to", str(tmp / "state"), "--log-level", "warn",
           "--show-interactive-dev-session=false"]
    # WRANGLER_LOG_PATH keeps wrangler's debug log in the temporary folder (removed below) instead of
    # ~/Library/Preferences/.wrangler/logs.
    env = {**os.environ, "WRANGLER_SEND_METRICS": "false", "CI": "true", "NO_COLOR": "1", "FORCE_COLOR": "0",
           "WRANGLER_LOG_PATH": str(tmp / "wrangler-debug.log")}
    with open(log_path, "w") as log:
        proc = subprocess.Popen(cmd, cwd=tmp, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    try:
        deadline, ready = time.monotonic() + 180, False
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                fetch(port, "/")
                ready = True
                break
            except (OSError, http.client.HTTPException):
                time.sleep(0.5)
        if not ready:
            tail = log_path.read_text(errors="replace")[-600:] if log_path.exists() else ""
            r.fail(f"wrangler@{version} pages dev did not start within 180 s: {tail.strip()}")
            return r
        r.ok(f"served dist/ with npx wrangler@{version} pages dev on 127.0.0.1:{port}")
        body_404 = not_found.read_bytes() if not_found.is_file() else None
        bad200, bad308, bad404 = [], [], []
        for path in sorted(ok_200):
            status, location, body = fetch(port, path)
            file = page_file(dist, path)
            if status != 200:
                bad200.append(f"{path}: {status}" + (f" -> {location}" if location else ""))
            elif file is None:
                bad200.append(f"{path}: 200, but dist/ has no page for it (a fallback answered)")
            elif body != file.read_bytes():
                bad200.append(f"{path}: 200, but the body is not {rel(ctx.root, file)}")
        for path in ("/docs/", "/docs.html"):
            status, location, _ = fetch(port, path)
            target = urlsplit(location or "")
            if status != 308 or target.path != "/docs" or target.query:
                bad308.append(f"{path}: {status}" + (f" -> {location}" if location else ""))
        for path in sorted(gone):
            status, location, body = fetch(port, path)
            if status != 404:
                bad404.append(f"{path}: {status}" + (f" -> {location}" if location else ""))
            elif body_404 is not None and body != body_404:
                bad404.append(f"{path}: 404, but the body is not dist/404.html ({len(body)} bytes, 404.html has {len(body_404)})")
        bad_inherent = []
        for path, (want, want_loc, what) in PAGES_INHERENT.items():
            status, location, body = fetch(port, path)
            loc = urlsplit(location).path if location else None
            if status != want or loc != want_loc or (want == 200 and body_404 is not None and body != body_404):
                bad_inherent.append(f"{path}: {status}" + (f" -> {location}" if location else "")
                                    + f", expected {want}" + (f" -> {want_loc}" if want_loc else " with the 404.html body"))
            else:
                r.note(f"{path} answers {status}" + (f" -> {loc}" if loc else "") + f", not 404: Cloudflare Pages {what} "
                       "(Pages-inherent, PAGES_INHERENT; Decision 11 forbids _redirects; for the owner to accept in PLAN.md Risks)")
        r.fails(f"{len(bad_inherent)} Pages-inherent path(s) do not answer as recorded:", bad_inherent)
        r.fails(f"{len(bad200)} page(s) do not answer 200 without a redirect:", bad200, "more pages")
        r.fails(f"{len(bad308)} of /docs/ and /docs.html do not 308 to /docs:", bad308)
        r.fails(f"{len(bad404)} path(s) do not answer 404 with the 404.html body:", bad404, "more paths")
        if not bad200:
            r.ok(f"{len(ok_200)} URLs answer 200 with no redirect ({len(pages)} pages in dist/, /docs?theme= for {len(themes)} colors"
                 + (", the 30 kept routes and 19 color routes" if ctx.phase < 3 else "") + ")")
        if not bad308:
            r.ok("/docs/ and /docs.html answer 308 to /docs")
        if not bad404:
            r.ok(f"{len(gone)} paths answer 404 with the 404.html body (dropped routes, /docs/v1/ and its pages, unknown paths"
                 + (", and the old per-route docs paths" if ctx.phase >= 3 else "") + ")")
    finally:
        stop(proc)
        shutil.rmtree(tmp, ignore_errors=True)
    return r


def page_file(dist: Path, path: str) -> Path | None:
    """The dist/ file Pages serves for an extensionless URL path: / is index.html, /x is x.html,
    /x/ is x/index.html. The query string does not matter."""
    p = urlsplit(path).path.strip("/")
    candidates = [dist / "index.html"] if not p else [dist / f"{p}/index.html"] if path.split("?")[0].endswith("/") else [dist / f"{p}.html"]
    return next((c for c in candidates if c.is_file()), None)


def fetch(port: int, path: str) -> tuple[int, str | None, bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    try:
        conn.request("GET", path, headers={"Accept": "text/html", "Accept-Encoding": "identity"})
        resp = conn.getresponse()
        return resp.status, resp.getheader("Location"), resp.read()
    finally:
        conn.close()


def stop(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


# ---------------------------------------------------------------------------- criterion 8


def criterion_8(ctx: Context) -> Result:
    r = Result(8, "Head: docs.html's title, description, og:* and canonical; sitemap.xml lists only page URLs")
    docs = ctx.dist / "docs.html"
    if not docs.is_file():
        r.not_yet("no dist/docs.html (npm run build writes it)")
        return r
    doc = ctx.page(docs)
    head = next(iter(doc.find_all("head")), None)
    if head is None:
        r.fail("dist/docs.html has no <head>")
        return r
    titles = head.find_all("title")
    metas = head.find_all("meta")
    links = head.find_all("link")
    found = []

    def one(label: str, values: list[str], want: str | None = None):
        values = [v.strip() for v in values]
        if len(values) != 1:
            r.fail(f"{label}: {len(values)} in docs.html's head, expected exactly one")
        elif not values[0]:
            r.fail(f"{label} is empty")
        elif want is not None and values[0] != want:
            r.fail(f"{label} is {values[0]!r}, expected {want!r}")
        else:
            found.append(f"{label} {values[0][:70]!r}")

    one("<title>", [t.text() for t in titles])
    one('<meta name="description">', [m.attrs.get("content", "") for m in metas if m.attrs.get("name", "").lower() == "description"])
    for prop in ("og:title", "og:description"):
        one(f'<meta property="{prop}">', [m.attrs.get("content", "") for m in metas if m.attrs.get("property") == prop])
    one('<meta property="og:url">', [m.attrs.get("content", "") for m in metas if m.attrs.get("property") == "og:url"], DOCS_URL)
    one('<link rel="canonical">', [l.attrs.get("href", "") for l in links if "canonical" in l.attrs.get("rel", "").lower().split()], DOCS_URL)
    for line in found:
        r.ok(line)

    sitemap = ctx.dist / "sitemap.xml"
    if not sitemap.is_file():
        r.fail("dist/sitemap.xml is missing")
        return r
    try:
        tree = ET.parse(sitemap)
    except ET.ParseError as exc:
        r.fail(f"dist/sitemap.xml is not well-formed XML: {exc}")
        return r
    locs = [(e.text or "").strip() for e in tree.iter() if e.tag.rsplit("}", 1)[-1] == "loc"]
    pages = {page_url(ctx.dist, p) for p in ctx.dist_pages() if p.relative_to(ctx.dist).as_posix() != "404.html"}
    bad = []
    for loc in locs:
        u = urlsplit(loc)
        if f"{u.scheme}://{u.netloc}" != SITE_ORIGIN or u.query or u.fragment or u.path not in pages:
            bad.append(f"{loc}: not a page URL (pages are {SITE_ORIGIN} + one of {len(pages)} served paths)")
    dups = sorted({l for l in locs if locs.count(l) > 1})
    r.fails(f"sitemap.xml lists {len(bad)} URL(s) that are not pages:", bad, "more URLs")
    if dups:
        r.fail(f"sitemap.xml lists {len(dups)} URL(s) twice: {', '.join(dups[:5])}")
    if not bad and not dups:
        r.ok(f"sitemap.xml lists {len(locs)} URLs, all pages: {', '.join(urlsplit(l).path for l in locs[:8])}" + (" ..." if len(locs) > 8 else ""))
    unlisted = sorted(pages - {urlsplit(l).path for l in locs})
    if unlisted:
        r.note(f"{len(unlisted)} pages are not in sitemap.xml: {', '.join(unlisted[:8])}" + (" ..." if len(unlisted) > 8 else ""))
    return r


# ---------------------------------------------------------------------------- criterion 9


def example_container(node: Node) -> Node | None:
    """The live example a node belongs to: its nearest article.component (the oracle's example card)."""
    return next((a for a in node.ancestors() if a.tag == "article" and "component" in a.classes()), None)


def criterion_9(ctx: Context) -> Result:
    r = Result(9, "Valid HTML and ids")
    pages = ctx.dist_pages()
    if not pages:
        r.not_yet("no HTML in dist/ (npm run build writes it)")
        return r
    root, dist = ctx.root, ctx.dist

    # html-validate, through npx at its latest version (or package.json's exact pin).
    version = ctx.pinned("html-validate", HTML_VALIDATE)
    configs = [p.name for p in root.glob(".htmlvalidate*")]
    report, why = None, None
    probe = subprocess.run(["npx", "--yes", f"html-validate@{version}", "--version"], cwd=root, capture_output=True,
                           text=True, timeout=300)
    if probe.returncode != 0 or version not in probe.stdout:
        why = (f"html-validate@{version} --version exited {probe.returncode} and printed {probe.stdout.strip()[:80]!r}: "
               f"{probe.stderr.strip()[-300:]}")
    else:
        # The report goes to a file, not a pipe: on macOS Node writes to a pipe asynchronously, and
        # html-validate's process.exit() cut its multi-megabyte JSON report short (the Phase 1
        # integration found a report of dist/ ending mid-string).
        with tempfile.TemporaryFile("w+", encoding="utf-8") as out:
            proc = subprocess.run(["npx", "--yes", f"html-validate@{version}", "--formatter", "json", *[str(p) for p in pages]],
                                  cwd=root, stdout=out, stderr=subprocess.PIPE, text=True, timeout=900)
            out.seek(0)
            proc.stdout = out.read()
        try:
            report = json.loads(proc.stdout) if proc.stdout.strip() else None
        except ValueError:
            report = None
        given = {str(p.resolve()) for p in pages}
        if proc.returncode not in (0, 1) or not isinstance(report, list):
            why = f"html-validate@{version} exited {proc.returncode} without a JSON report: {(proc.stderr or proc.stdout).strip()[-400:]}"
        elif any(str(Path(f.get("filePath", "")).resolve()) not in given for f in report):
            why = f"html-validate@{version}'s report names files it was not given"
        elif proc.returncode == 1 and not any(m.get("severity") == 2 for f in report for m in f.get("messages", [])):
            why = f"html-validate@{version} exited 1 but reported no error: {proc.stderr.strip()[-300:]}"
        elif proc.returncode == 0 and any(m.get("severity") == 2 for f in report for m in f.get("messages", [])):
            why = f"html-validate@{version} exited 0 but reported errors"
        if why:
            report = None
    if report is None:
        r.fail(why or f"html-validate@{version} did not run")
    else:
        errors = [f"{rel(root, Path(f['filePath']))}:{m.get('line')}: {m.get('ruleId')}: {m.get('message')}"
                  for f in report for m in f.get("messages", []) if m.get("severity") == 2]
        warnings = sum(f.get("warningCount", 0) for f in report)
        r.fails(f"html-validate@{version} reports {len(errors)} error(s) in {sum(1 for f in report if f.get('errorCount'))} of {len(pages)} files:", errors, "more errors")
        if not errors:
            r.ok(f"html-validate@{version} passes on all {len(pages)} HTML files in dist/")
        if warnings:
            r.note(f"html-validate warnings: {warnings}")
    r.note("html-validate config: " + (", ".join(configs) if configs else "none in the repository, so html-validate's own defaults (html-validate:recommended)"))

    # Duplicate ids on each page; radio and details names across separate examples.
    dup_lines, name_lines = [], []
    for p in pages:
        doc = ctx.page(p)
        where = rel(root, p)
        seen: dict[str, list[int]] = {}
        groups: dict[tuple[str, str], dict[int, Node | None]] = {}
        for n in doc.iter():
            if n.tag == "#document" or n.in_template():
                continue
            if "id" in n.attrs:
                seen.setdefault(n.attrs["id"], []).append(n.line)
            kind = "radio" if n.tag == "input" and n.attrs.get("type", "").lower() == "radio" else "details" if n.tag == "details" else None
            if kind and n.attrs.get("name"):
                box = example_container(n)
                groups.setdefault((kind, n.attrs["name"]), {})[id(box)] = box
        dup_lines += [f"{where}: id {k!r} {len(v)}x (lines {', '.join(map(str, v[:6]))})" for k, v in sorted(seen.items()) if len(v) > 1]
        for (kind, name), boxes in sorted(groups.items()):
            if len(boxes) > 1:
                lines = ", ".join("outside examples" if b is None else f"line {b.line}" for b in boxes.values())
                name_lines.append(f"{where}: {kind} name {name!r} in {len(boxes)} separate examples ({lines})")
    r.fails(f"{len(dup_lines)} duplicate id(s):", dup_lines, "more ids")
    if not dup_lines:
        r.ok(f"no duplicate id on any of {len(pages)} pages (ids inside <template> excluded)")
    r.fails(f"{len(name_lines)} radio or details name(s) repeat across separate examples (an example is its nearest article.component):", name_lines, "more names")
    if not name_lines:
        r.ok("no radio name or details name repeats across separate examples")

    # The one docs page: section heading ids and the side nav.
    if ctx.phase < 3:
        r.not_yet(f"section heading ids and side nav apply from Phase 3 (the one docs page); phase is {ctx.phase} ({ctx.phase_why})")
        return r
    docs = dist / "docs.html"
    menu_path = ctx.site / "docs/menu.json"
    if not docs.is_file():
        r.fail("dist/docs.html is missing")
        return r
    if not menu_path.is_file():
        r.fail("site/docs/menu.json is missing, so the section list is unknown")
        return r
    ids = menu_ids(json.loads(menu_path.read_text(encoding="utf-8")))
    doc = ctx.page(docs)
    by_id: dict[str, list[Node]] = {}
    for n in doc.iter():
        if "id" in n.attrs and not n.in_template():
            by_id.setdefault(n.attrs["id"], []).append(n)
    bad = []
    for sid in ids:
        nodes = by_id.get(sid, [])
        if not SECTION_ID.match(sid):
            bad.append(f"section id {sid!r} does not match {SECTION_ID.pattern}")
        if not nodes:
            bad.append(f"section {sid!r}: no element has this id")
        elif nodes[0].tag not in HEADINGS:
            bad.append(f"section {sid!r}: the id is on <{nodes[0].tag}> (line {nodes[0].line}), not a heading")
        elif nodes[0].tag != "h1":
            r.note(f"section {sid!r}: the id is on <{nodes[0].tag}>, not the section's h1 (Decision 13)")
    others = [f"<{n.tag} id={n.attrs['id']!r}> line {n.line}" for n in doc.iter()
              if n.tag in HEADINGS and "id" in n.attrs and n.attrs["id"] not in ids and not n.in_template()]
    r.fails(f"{len(bad)} section heading problem(s):", bad, "more")
    r.fails(f"{len(others)} heading(s) in docs.html carry an id but are not section headings:", others, "more headings")
    if not bad and not others:
        r.ok(f"{len(ids)} section headings, ids matching {SECTION_ID.pattern}; no other heading has an id")
    navs = [(sum(1 for a in nav.find_all("a") if section_target(a.attrs.get("href", "")) in ids), nav) for nav in doc.find_all("nav")]
    navs = [x for x in navs if x[0]]
    if not navs:
        r.fail("docs.html has no <nav> with links to sections (the side nav)")
        return r
    navs.sort(key=lambda x: -x[0])
    side = navs[0][1]
    if len(navs) > 1:
        r.note(f"{len(navs)} <nav> elements link to sections; checked the one with the most links (line {side.line})")
    links = side.find_all("a")
    stray = [f"{a.attrs.get('href', '')!r} (line {a.line})" for a in links if section_target(a.attrs.get("href", "")) not in ids]
    counts = {sid: 0 for sid in ids}
    for a in links:
        t = section_target(a.attrs.get("href", ""))
        if t in counts:
            counts[t] += 1
    wrong = [f"{sid}: {c} nav links" for sid, c in counts.items() if c != 1]
    r.fails(f"{len(stray)} side-nav link(s) do not target a section id:", stray, "more links")
    r.fails(f"{len(wrong)} section(s) do not have exactly one side-nav link:", wrong, "more sections")
    if not stray and not wrong:
        r.ok(f"the side nav (line {side.line}) has {len(links)} links, one per section")
    return r


# ---------------------------------------------------------------------------- criterion 11


def site_css_sources(ctx: Context) -> list[tuple[str, str, bool]]:
    """(label, css text, is_attribute) for site CSS outside vendor/ and assets/legacy/, plus <style>
    elements and style attributes in site HTML."""
    skip = (ctx.site / "vendor", ctx.site / "assets/legacy")
    out = [(rel(ctx.root, p), p.read_text(encoding="utf-8", errors="replace"), False) for p in files_under(ctx.site, (".css",), skip)]
    for p in files_under(ctx.site, (".html",), skip):
        doc = ctx.page(p)
        for n in doc.iter():
            if n.tag == "style":
                out.append((f"{rel(ctx.root, p)}:{n.line} <style>", n.text(), False))
            if "style" in n.attrs and n.tag != "#document":
                out.append((f"{rel(ctx.root, p)}:{n.line} style=\"\"", n.attrs["style"], True))
    return out


def criterion_11(ctx: Context) -> Result:
    r = Result(11, "Lint")
    root, site = ctx.root, ctx.site
    css_dir = site / "assets/css"
    css_files = files_under(css_dir, (".css",))
    sources = site_css_sources(ctx) if site.is_dir() else []
    if not css_files:
        r.not_yet("no site/assets/css/*.css yet (Phase 2 writes them)")
    if sources:
        counts = {"color functions": 0, "color-mix": 0}
        before = len(r.failures)
        for label, text, is_attr in sources:
            _, masked, comments = scan_css(text)
            where = lambda o: label if label.endswith((">", '""')) else f"{label}:{line_of(text, o)}"
            for name_, pattern in FORBIDDEN:
                for m in pattern.finditer(masked):
                    r.fail(f"{where(m.start())}: {name_}")
                for o, c in comments:
                    if pattern.search(c):
                        r.note(f"{where(o)}: a comment mentions {name_} (not code)")
            for m in COLOR_FUNCTION.finditer(masked):
                name = m.group(1).lower()
                args = call_args(masked, m.end() - 1)
                counts["color functions"] += 1
                if re.search(r"(?<![\w-])from(?![\w-])", depth0(args), re.I):
                    r.fail(f"{where(m.start())}: relative color syntax: {name}({args.strip()[:60]})")
                if name == "color-mix":
                    counts["color-mix"] += 1
                    if not re.match(r"\s*in\s+srgb\s*,", args, re.I):
                        r.fail(f"{where(m.start())}: color-mix without 'in srgb': color-mix({args.strip()[:60]})")
        what = (f"{len(sources)} site CSS sources ({sum(1 for _, _, a in sources if not a)} files and <style> elements, "
                f"{sum(1 for _, _, a in sources if a)} style attributes; vendor/ and assets/legacy/ excluded)")
        r.ok(f"{what}: no forbidden at-rule or function in code; {counts['color functions']} color function calls, "
             f"{counts['color-mix']} of them color-mix()" if len(r.failures) == before else f"{what} scanned")

    # scroll-behavior: smooth only under Decision 10's class.
    docs_js = site / "assets/js/docs.js"
    js_text = docs_js.read_text(encoding="utf-8", errors="replace") if docs_js.is_file() else ""
    smooth_ok, smooth_bad = 0, []
    for label, text, is_attr in sources:
        _, masked, _ = scan_css(text)
        hits = [m.start() for m in SMOOTH.finditer(masked)]
        if not hits:
            continue
        if is_attr:
            smooth_bad.append(f"{label}: scroll-behavior: smooth in a style attribute")
            continue
        blocks = enclosing_blocks(masked, hits)
        for o in hits:
            stack = blocks[o]
            media = any(REDUCED_MOTION_OK.match(b) for b in stack)
            rules = [b for b in stack if not b.startswith("@")]
            classes = [SMOOTH_SELECTOR.match(s) for b in rules for s in split_selectors(b)]
            where = f"{label}:{line_of(text, o)}" if not label.endswith(">") else label
            if not rules or not all(classes):
                smooth_bad.append(f"{where}: scroll-behavior: smooth under {' > '.join(stack) or 'no rule'} (not a class on <html>)")
            elif not media:
                smooth_bad.append(f"{where}: scroll-behavior: smooth outside @media (prefers-reduced-motion: no-preference)")
            elif not all(m.group(1) in js_text for m in classes):
                smooth_bad.append(f"{where}: class {', '.join(m.group(1) for m in classes)} is not set by site/assets/js/docs.js")
            else:
                smooth_ok += 1
    for p in files_under(site / "assets/js", (".js", ".mjs")):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"scrollBehavior\s*=\s*[\"'`]smooth|setProperty\(\s*[\"'`]scroll-behavior[\"'`]\s*,\s*[\"'`]smooth", text):
            smooth_bad.append(f"{rel(root, p)}:{line_of(text, m.start())}: script sets scroll-behavior: smooth")
        for m in re.finditer(r"behavior\s*:\s*[\"'`]smooth", text):
            r.note(f"{rel(root, p)}:{line_of(text, m.start())}: a scroll call asks for smooth behavior (Decision 10 limits smooth scrolling to nav clicks)")
    r.fails(f"{len(smooth_bad)} scroll-behavior: smooth outside Decision 10's class:", smooth_bad, "more")
    if sources and not smooth_bad:
        r.ok(f"scroll-behavior: smooth appears {smooth_ok} time(s), each under a class docs.js sets, inside prefers-reduced-motion: no-preference")
    if (site / "assets/legacy").is_dir():
        r.note("site/assets/legacy/ is not scanned (the frozen oracle CSS, deleted in Phase 2)")

    # Every lint exception carries a reason: eslint-disable directives need "-- reason".
    skip = (site / "vendor", site / "assets/legacy")
    unexplained = []
    for p in files_under(site, (".js", ".mjs", ".css", ".html"), skip):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(?:/\*|//)\s*eslint-disable(?:-next-line|-line)?\b([^\n]*?)(?:\*/|$)", text, re.M):
            if " -- " not in m.group(1) + " ":
                unexplained.append(f"{rel(root, p)}:{line_of(text, m.start())}: {m.group(0).strip()[:80]}")
    r.fails(f"{len(unexplained)} eslint-disable directive(s) without a '-- reason':", unexplained, "more")
    # Inline rule configuration (/* eslint rule: [...] */) overrides the config file for its file, and
    # `eslint --print-config` never shows it. The Baseline rules' level and allow lists belong in
    # the config, where they are read and listed: an inline one fails. Any other inline rule
    # configuration is an exception and needs "-- reason" too.
    inline_cfg, inline_bad = [], []
    for p in files_under(site, (".js", ".mjs", ".css", ".html"), skip):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"/\*\s*eslint\s+((?:[^*]|\*(?!/))*)\*/", text):
            body = m.group(1)
            # ESLint splits the description off at whitespace, two or more dashes, whitespace.
            parts = re.split(r"\s-{2,}\s", body + " ", maxsplit=1)
            rules, why = parts[0], parts[1] if len(parts) > 1 else ""
            names = inline_rule_names(rules)
            at = f"{rel(root, p)}:{line_of(text, m.start())}: /* eslint {rules.strip()[:70]} */"
            compat = [x for x in names if x.endswith("use-baseline") or x.split("/")[0] in (COMPAT_LINT.removeprefix("eslint-plugin-"),
                                                                                         COMPAT_LINT)]
            if compat:
                inline_bad.append(f"{at}: configures {', '.join(compat)} inline (the Baseline level and its allow lists "
                                  "belong in the config file)")
            elif not why.strip():
                inline_bad.append(f"{at}: inline rule configuration without a '-- reason'")
            else:
                inline_cfg.append(f"{at} -- {why.strip()[:60]}")
    r.fails(f"{len(inline_bad)} inline ESLint rule configuration comment(s) that are not allowed:", inline_bad, "more")
    if inline_cfg:
        r.note(f"{len(inline_cfg)} inline ESLint rule configuration(s), each with a reason: " + "; ".join(inline_cfg[:6]))
    configs = [p.name for p in root.glob("eslint.config.*")]
    if configs:
        r.note(f"{', '.join(configs)}: rules switched off there need a reason in a comment; not checked mechanically")

    scripts = (ctx.package() or {}).get("scripts") or {}
    inline = [f"{rel(root, p)}:{n.line}" for p in files_under(site, (".html",), skip) for n in ctx.page(p).iter()
              if n.tag == "script" and "src" not in n.attrs and script_kind(n) in ("classic", "module")]
    if inline:
        r.note(f"{len(inline)} inline script(s) in site HTML are outside the lint, which PLAN gives as site/**/*.js "
               f"(Decision 12 still applies to them): {', '.join(inline[:6])}" + (" ..." if len(inline) > 6 else ""))
    if "lint" not in scripts:
        r.not_yet("package.json has no lint script yet (Phase 1 writes it)")
        return r
    lint = scripts["lint"]
    if not re.search(r"(?<![\w-])eslint(?![\w-])", lint):
        r.fail(f"the lint script does not run eslint: {lint!r}")
    if re.search(r"(?<![\w-])--fix(?:-dry-run|-type)?(?![\w-])", lint):
        r.fail(f"the lint script fixes files (--fix), so it can pass by changing them; not run: {lint!r}")
        return r
    proc = subprocess.run(["npm", "run", "lint", "--silent"], cwd=root, capture_output=True, text=True, timeout=900,
                          env={**os.environ, **LINT_ENV})
    if proc.returncode != 0:
        r.fail(f"npm run lint exited {proc.returncode}: {(proc.stdout + proc.stderr).strip()[-500:]}")
    else:
        r.ok(f"npm run lint exited 0 ({lint!r})")
    css = files_under(site, (".css",), skip)
    js = files_under(site, (".js", ".mjs"), skip)
    if not js:
        r.not_yet("no site JS outside vendor/ and assets/legacy/ to lint yet")
    if not css and not js:
        return r
    eslint = root / "node_modules/.bin/eslint"
    if not eslint.exists():
        r.fail("node_modules/.bin/eslint is missing: npm install the pinned devDependencies before the lint check")
        return r
    lint_config(ctx, r, eslint, css, js)
    if proc.returncode == 0:
        lint_probe(ctx, r, css, js)
    else:
        r.note("the planted-violation probe needs npm run lint to pass first, so it did not run")
    return r


def inline_rule_names(rules: str) -> list[str]:
    """The rule names an inline /* eslint ... */ configuration sets: its keys at the top level, quoted
    ("css/use-baseline": ..., ESLint's documented form for plugin rules) or not, read past strings,
    arrays and objects, so an option object's keys are never taken for rule names."""
    names, depth, i, n, start = [], 0, 0, len(rules), 0
    while i < n:
        c = rules[i]
        if c in "\"'":
            j = i + 1
            while j < n and rules[j] != c:
                j += 2 if rules[j] == "\\" else 1
            i = j + 1
            continue
        if c in "[{(":
            depth += 1
        elif c in "]})":
            depth = max(depth - 1, 0)
        elif depth == 0 and c == ",":
            start = i + 1
        elif depth == 0 and c == ":":
            key = rules[start:i].strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
                key = key[1:-1]
            if key:
                names.append(key)
        i += 1
    return names


# Criterion 11's planted-violation probe. Each probe is Baseline newly available but not widely
# available (in @eslint/css 2.0.1 and eslint-plugin-baseline-js 0.7.6 on 2026-10-30). Every run first
# calibrates them against the installed tools with a reference config, at "widely" and at "newly", and
# keeps those reported at the first and not the second, so a data update that makes one widely
# available only drops it. Both JS lists parse in any script or module, and the plugin reports the
# first two with its default options (no includeJsBuiltins).
CSS_PROBES = (
    ".femto-lint-probe { transition-behavior: allow-discrete; }",
    ".femto-lint-probe { scrollbar-gutter: stable; }",
    "@starting-style { .femto-lint-probe { opacity: 0; } }",
    ".femto-lint-probe { zoom: 1.5; }",
    "@property --femto-lint-probe { syntax: \"*\"; inherits: false; }",
)
JS_PROBES = (
    "void Math.sumPrecise([1]);",
    "void Atomics.pause();",
    "void Promise.try(() => 0);",
    "void RegExp.escape(\"a\");",
    "void Iterator.from([]);",
)
JS_BASELINE_MESSAGE = re.compile(r"is not Baseline Widely available \([\w.-]+\)")
PROBE_TRIES = 3  # probes tried per file before it counts as not linted
LINT_ENV = {"NO_COLOR": "1", "FORCE_COLOR": "0", "npm_config_update_notifier": "false", "npm_config_fund": "false"}


def rule_setting(rules: dict, name: str) -> tuple[object, dict]:
    rule = rules.get(name)
    sev = rule[0] if isinstance(rule, list) and rule else rule
    opts = rule[1] if isinstance(rule, list) and len(rule) > 1 and isinstance(rule[1], dict) else {}
    return sev, opts


def compat_key(plugins: list) -> str | None:
    """The key COMPAT_LINT is registered under in a resolved config ("key:name@version" entries)."""
    for s in plugins:
        if isinstance(s, str):
            key, _, ident = s.partition(":")
            if ident.rsplit("@", 1)[0] == COMPAT_LINT or (not ident and key == "baseline-js"):
                return key
    return None


def lint_config(ctx: Context, r: Result, eslint: Path, css: list[Path], js: list[Path]) -> None:
    """eslint --print-config on every site CSS and JS file (vendor/ and assets/legacy/ excluded):
    each CSS file has @eslint/css css/use-baseline as an error at available "widely", and each JS
    file has rules on, among them COMPAT_LINT's use-baseline as an error at Baseline "widely".
    Allow lists and ignored features are exceptions, listed as notes."""
    root = ctx.root
    bad, exceptions, keys = [], [], set()
    for p in css + js:
        proc = subprocess.run([str(eslint), "--print-config", str(p)], cwd=root, capture_output=True, text=True, timeout=120,
                              env={**os.environ, **LINT_ENV})
        try:
            conf = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None
        except ValueError:
            conf = None
        where = rel(root, p)
        if not isinstance(conf, dict):
            bad.append(f"{where}: eslint --print-config gave no config (ignored or not covered): "
                       f"{(proc.stderr or proc.stdout).strip()[-150:]}")
            continue
        rules = conf.get("rules") or {}
        if p.suffix.lower() == ".css":
            sev, opts = rule_setting(rules, "css/use-baseline")
            if sev not in (2, "error") or opts.get("available", "widely") != "widely":
                bad.append(f"{where}: css/use-baseline is {rules.get('css/use-baseline')!r}, not an error at available \"widely\"")
            allowed = {k: v for k, v in opts.items() if k.startswith("allow") and v}
            if allowed:
                exceptions.append(f"{where}: css/use-baseline allows {json.dumps(allowed)[:160]}")
            continue
        if not any((v[0] if isinstance(v, list) and v else v) not in (0, "off") for v in rules.values()):
            bad.append(f"{where}: no ESLint rule is on")
        key = compat_key(conf.get("plugins") or [])
        if key is None:
            bad.append(f"{where}: {COMPAT_LINT} is not loaded for this file (the JS compat lint, COMPAT_LINT)")
            continue
        keys.add(key)
        name = f"{key}/use-baseline"
        sev, opts = rule_setting(rules, name)
        if sev not in (2, "error") or opts.get("available", opts.get("baseline", "widely")) != "widely":
            bad.append(f"{where}: {name} is {rules.get(name)!r}, not an error at Baseline \"widely\"")
        ignored = {k: v for k, v in opts.items() if k in ("ignoreFeatures", "ignoreNodeTypes") and v}
        if ignored:
            exceptions.append(f"{where}: {name} ignores {json.dumps(ignored)[:160]}")
    r.fails(f"{len(bad)} site file(s) are not configured as PLAN asks (eslint --print-config):", bad, "more files")
    if not bad:
        r.ok(f"eslint --print-config: css/use-baseline (error, widely) on {len(css)} CSS files; "
             f"{', '.join(sorted(k + '/use-baseline' for k in keys)) or COMPAT_LINT} (error, widely) and the other rules "
             f"on {len(js)} JS files")
    for line in capped(exceptions):
        r.note(line + " (an exception: eslint.config needs its reason)")


def lint_calibrate(root: Path, tmp: Path, kind: str) -> tuple[list[tuple[str, str]], str | None]:
    """(probe, message) for the probes the installed tool reports at "widely" but not at "newly",
    in list order, from two eslint runs on a reference config in tmp. The message is what the lint
    output must then show: @eslint/css's whole message, or the plugin's "is not Baseline Widely
    available (feature-id)" (its wording before that varies with the detector)."""
    probes, ext = (CSS_PROBES, "css") if kind == "css" else (JS_PROBES, "js")
    d = tmp / f"calibrate-{kind}"
    d.mkdir()
    (d / "node_modules").symlink_to((root / "node_modules").resolve())
    names = []
    for k, text in enumerate(probes):
        names.append(f"p{k}.{ext}")
        (d / names[-1]).write_text(text + "\n", encoding="utf-8")
    if kind == "css":
        conf = ('import css from "@eslint/css";\nexport default [{ files: ["**/*.css"], language: "css/css", plugins: { css }, '
                'rules: { "css/use-baseline": ["error", { available: process.env.FEMTO_LINT_LEVEL }] } }];\n')
    else:
        conf = (f'import plugin from "{COMPAT_LINT}";\nexport default [{{ files: ["**/*.js"], plugins: {{ "baseline-js": plugin }}, '
                'rules: { "baseline-js/use-baseline": ["error", { available: process.env.FEMTO_LINT_LEVEL, '
                'includeJsBuiltins: { preset: "auto" }, includeWebApis: { preset: "auto" } }] } }];\n')
    (d / "eslint.config.mjs").write_text(conf, encoding="utf-8")
    flagged: dict[str, dict[str, list[str]]] = {}
    for level in ("widely", "newly"):
        proc = subprocess.run([str(root / "node_modules/.bin/eslint"), "--format", "json", *names], cwd=d, capture_output=True,
                              text=True, timeout=300, env={**os.environ, **LINT_ENV, "FEMTO_LINT_LEVEL": level})
        try:
            report = json.loads(proc.stdout)
        except ValueError:
            return [], f"eslint at {level} gave no JSON report (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()[-200:]}"
        flagged[level] = {Path(f.get("filePath", "")).name: [m.get("message", "") for m in f.get("messages", [])
                                                            if (m.get("ruleId") or "").endswith("/use-baseline")] for f in report}
    out = []
    for name, text in zip(names, probes):
        wide, new = flagged["widely"].get(name) or [], flagged["newly"].get(name) or []
        if wide and not new:
            m = JS_BASELINE_MESSAGE.search(wide[0]) if kind == "js" else None
            out.append((text, m.group(0) if m else wide[0].rstrip(".")))  # stylish drops a message's final period
    return out, None


def lint_copy(root: Path, dest: Path) -> None:
    """Copy into dest the files a commit would hold (a git checkout) or else every file outside
    node_modules/, .git/, dist/ and the harness's outputs; link node_modules to the root's."""
    top = git(root, "rev-parse", "--show-toplevel")
    if top.returncode == 0 and Path(top.stdout.strip()).resolve() == root.resolve():
        files = effective_files(root)
    else:
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            d = Path(dirpath)
            here = d.relative_to(root).as_posix()
            keep = []
            for x in dirnames:
                path = x if here == "." else f"{here}/{x}"
                if x in ("node_modules", ".git", ".wrangler", "__pycache__") or path in ("dist", "tests/oracle", "tests/results"):
                    continue
                (files.append(path) if (d / x).is_symlink() else keep.append(x))
            dirnames[:] = keep
            files += [f if here == "." else f"{here}/{f}" for f in filenames]
    for f in files:
        src, dst = root / f, dest / f
        if f.split("/")[0] == "node_modules" or not (src.is_file() or src.is_symlink()):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            dst.symlink_to(src.resolve())
        else:
            shutil.copy2(src, dst)
    (dest / "node_modules").symlink_to((root / "node_modules").resolve())


def run_lint(cwd: Path) -> tuple[int, str]:
    """Exit status and output of npm run lint; entities unescaped, for formatters that write XML or
    HTML (checkstyle, junit, html)."""
    proc = subprocess.run(["npm", "run", "lint", "--silent"], cwd=cwd, capture_output=True, text=True, timeout=900,
                          env={**os.environ, **LINT_ENV})
    return proc.returncode, html.unescape(proc.stdout + proc.stderr)


def lint_probe(ctx: Context, r: Result, css: list[Path], js: list[Path]) -> None:
    """Prove that `npm run lint` lints every site CSS and JS file with use-baseline at widely: in a
    temporary copy of the tree (never the repository), plant one calibrated newly-but-not-widely
    available feature at the end of one file at a time (after /* eslint-enable */), run the lint
    script, and require a failing exit and one more report of that feature's use-baseline message
    than the clean copy gave. Up to PROBE_TRIES probes per file."""
    root = ctx.root
    tmp = Path(tempfile.mkdtemp(prefix="femto-style-lint-"))
    try:
        cal: dict[str, list[tuple[str, str]]] = {}
        for kind, files, pkg, names in (("css", css, "@eslint/css", "CSS_PROBES"), ("js", js, COMPAT_LINT, "JS_PROBES")):
            cal[kind] = []
            if not files:
                continue
            if not (root / "node_modules" / pkg / "package.json").is_file():
                r.fail(f"node_modules/{pkg} is missing, so the {kind.upper()} probe cannot run: npm install the pinned devDependencies")
                continue
            probes, err = lint_calibrate(root, tmp, kind)
            if err:
                r.fail(f"the {kind.upper()} probe calibration failed: {err}")
            elif not probes:
                r.fail(f"the installed {pkg} reports none of {names} at widely and not at newly: update {names} in static_checks.py")
            cal[kind] = probes
        copy = tmp / "copy"
        lint_copy(root, copy)
        code, control = run_lint(copy)
        if code != 0:
            r.fail(f"npm run lint exits {code} in a clean temporary copy of the tree, so the probe cannot run: {control.strip()[-300:]}")
            return
        bad, used = [], {}
        for p in css + js:
            kind = "css" if p.suffix.lower() == ".css" else "js"
            if not cal[kind]:
                continue
            where = rel(root, p)
            target = copy / p.relative_to(root)
            if not target.is_file():
                bad.append(f"{where}: not in the copy of the files a commit would hold (ignored by git?)")
                continue
            if target.is_symlink():
                data = target.read_bytes()
                target.unlink()
                target.write_bytes(data)
            if not target.resolve().is_relative_to(tmp.resolve()):
                bad.append(f"{where}: its path in the copy links outside the copy, so nothing was planted")
                continue
            original = target.read_bytes()
            hit, last = None, (0, "")
            try:
                for text, message in cal[kind][:PROBE_TRIES]:
                    target.write_bytes(original + b"\n/* eslint-enable */\n" + text.encode() + b"\n")
                    last = run_lint(copy)
                    if last[0] != 0 and last[1].count(message) > control.count(message):
                        hit = text
                        break
            finally:
                target.write_bytes(original)
            if hit:
                used.setdefault(kind, set()).add(hit)
            else:
                tried = ", ".join(t for t, _ in cal[kind][:PROBE_TRIES])
                bad.append(f"{where}: npm run lint did not report a planted feature ({tried}); last exit {last[0]}: "
                           f"{' '.join(last[1].split())[-200:]}")
        r.fails(f"{len(bad)} site file(s) where npm run lint misses a planted Baseline violation (in a temporary copy):", bad, "more files")
        if not bad and (cal["css"] or cal["js"]):
            r.ok(f"planted in a temporary copy, one file at a time, a newly but not widely available feature fails npm run lint "
                 f"with its use-baseline message at widely in each of the {len(css)} CSS and {len(js)} JS files "
                 f"(probes: {'; '.join(sorted(used.get('css', set()) | used.get('js', set())))})")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------- criterion 12


def criterion_12(ctx: Context) -> Result:
    r = Result(12, "Vendored femto: every file in site/vendor/femto/ equals the commit named in its SOURCE, byte for byte")
    vendor = ctx.site / "vendor/femto"
    src = ctx.source()
    if src is None:
        r.fail("site/vendor/femto/SOURCE is missing (run npm run vendor)")
        return r
    missing_keys = [k for k in ("commit", "tag", "version", "source") if not src.get(k)]
    if missing_keys:
        r.fail(f"SOURCE lacks {', '.join(missing_keys)}")
    commit = src.get("commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        r.fail(f"SOURCE's commit {commit!r} is not a full commit hash")
        return r
    r.ok(f"SOURCE: commit {commit}, tag {src.get('tag')}, version {src.get('version')}, source {src.get('source')}")
    repo, tried = ctx.femto_repo(commit)
    if repo is None:
        r.not_yet(f"no femto checkout holding {commit[:12]} (tried {', '.join(tried)}); pass --femto DIR or set FEMTO_REPO")
        return r
    listing = git(repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", *VENDORED, check=True).stdout
    entries = []
    for line in filter(None, listing.split("\0")):
        meta, path = line.split("\t", 1)
        mode, kind, sha = meta.split()
        entries.append((path, kind, sha))
    blobs = read_blobs(repo, [sha for _, kind, sha in entries if kind == "blob"])
    expected = {path: data for (path, _, _), data in zip([e for e in entries if e[1] == "blob"], blobs)}
    have = {}
    for p in sorted(vendor.rglob("*")) if vendor.is_dir() else []:
        if p.is_file():
            key = p.relative_to(vendor).as_posix()
            if key == "SOURCE":
                continue
            if p.name == ".DS_Store":
                r.note(f"site/vendor/femto/{key} ignored (macOS Finder file, gitignored)")
                continue
            have[key] = p.read_bytes()
    missing = sorted(set(expected) - set(have))
    extra = sorted(set(have) - set(expected))
    differ = sorted(k for k in set(expected) & set(have) if expected[k] != have[k])
    ignored = [f for f in git(ctx.root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--",
                              "site/vendor/femto").stdout.split("\0") if f and not f.endswith(".DS_Store")]
    if ignored:
        rule = git(ctx.root, "check-ignore", "-v", ignored[0]).stdout.strip()
        r.fails(f"{len(ignored)} vendored file(s) are ignored by git, so a commit would leave them out "
                f"({rule or 'no rule shown'}):", ignored, "more files")
    else:
        r.ok("git ignores no file in site/vendor/femto/")
    r.fails(f"{len(missing)} file(s) at {commit[:8]} are missing from site/vendor/femto/:", missing, "more files")
    r.fails(f"{len(extra)} file(s) in site/vendor/femto/ are not in femto's {', '.join(VENDORED)} at {commit[:8]}:", extra, "more files")
    r.fails(f"{len(differ)} file(s) differ from git show {commit[:8]}:<path>:", differ, "more files")
    if not missing and not extra and not differ:
        r.ok(f"all {len(expected)} files equal git -C {repo} show {commit[:8]}:<path> byte for byte "
             f"({sum(len(v) for v in expected.values())} bytes; SOURCE excluded)")
    pkg = git(repo, "show", f"{commit}:package.json")
    try:
        version = json.loads(pkg.stdout).get("version") if pkg.returncode == 0 else None
    except ValueError:
        version = None
    if version != src.get("version"):
        r.fail(f"SOURCE's version {src.get('version')!r} is not package.json's {version!r} at {commit[:8]}")
    tags = sorted(git(repo, "tag", "--points-at", commit).stdout.split())
    if (", ".join(tags) or "none") != src.get("tag"):
        r.note(f"SOURCE's tag {src.get('tag')!r}; the tags at {commit[:8]} are now {', '.join(tags) or 'none'}")
    src_path = src.get("source", "")
    resolved = (ctx.root / src_path).resolve() if src_path and not os.path.isabs(src_path) else Path(src_path)
    if resolved != repo:
        r.note(f"checked against {repo}; SOURCE's source {src_path} " + ("does not exist" if not resolved.exists() else "was not used"))
    return r


# ---------------------------------------------------------------------------- criterion 13


def femto_names(text: str) -> tuple[set[str], set[str]]:
    """(declared, referenced) --femto-* names in femto CSS."""
    code, _, _ = scan_css(text)
    declared = set(re.findall(r"(--femto-[\w-]+)\s*:", code))
    referenced = set(re.findall(r"var\(\s*(--femto-[\w-]+)", code))
    return declared, referenced


def css_classes(text: str) -> set[str]:
    _, masked, _ = scan_css(text)
    out = set()
    for _, prelude in rule_preludes(masked):
        if not prelude.startswith("@"):  # a dot in a selector always starts a class (table.striped)
            out |= set(re.findall(r"\.(-?[_a-zA-Z][\w-]*)", prelude))
    return out


def markdown_section(text: str, heading: str) -> str:
    lines, out, level, fence = text.split("\n"), [], None, None
    for line in lines:
        m = re.match(r"^(```|~~~)", line)
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
        h = None if fence else re.match(r"^(#{1,6})\s+(.*)", line)
        if level is None:
            if h and h.group(2).strip() == heading:
                level = len(h.group(1))
            continue
        if h and len(h.group(1)) <= level:
            break
        out.append(line)
    return "\n".join(out)


def version_ok(found: str, version: str) -> bool:
    """found is the vendored version or a numeric prefix of it at a dot (3, 3.0)."""
    return found == version or (re.fullmatch(r"\d+(\.\d+)?", found) is not None and (version + ".").startswith(found + "."))


# Criterion 13's package name (the owner, 2026-10-30): femto is the npm package @leoherzog/femto "for
# now", and it has no Composer package. Wherever the docs name a package for femto (a jsDelivr, unpkg
# or npm URL, an install command, a name@version specifier, an import or require specifier, a
# dependency entry), the name must be FEMTO_PACKAGE. File names (femto.css, dist/femto.min.css) are not
# package names and are never judged here.
FEMTO_PACKAGE = "@leoherzog/femto"
PKG_NAME = r"(?:@[A-Za-z0-9][\w.~-]*/)?[A-Za-z0-9][\w.~-]*"
PACKAGE_CONTEXTS = (  # (what, pattern, also read in prose)
    ("a jsDelivr npm URL", re.compile(r"(?i)(?:jsdelivr\.net/(?:combine/)?|,)npm/(" + PKG_NAME + ")"), True),
    ("a jsDelivr package page", re.compile(r"(?i)jsdelivr\.com/package/npm/(" + PKG_NAME + ")"), True),
    ("a jsDelivr API URL", re.compile(r"(?i)data\.jsdelivr\.com/v1/packages?/npm/(" + PKG_NAME + ")"), True),
    ("a jsDelivr GitHub URL (femto's jsDelivr URLs are npm/" + FEMTO_PACKAGE + ")",
     re.compile(r"(?i)jsdelivr\.net/gh/([\w.-]+/[\w.-]+)"), True),
    ("an unpkg URL", re.compile(r"(?i)unpkg\.com/(" + PKG_NAME + ")"), True),
    ("an npm package page", re.compile(r"(?i)npmjs\.(?:com|org)/package/(" + PKG_NAME + ")"), True),
    ("an npm registry URL", re.compile(r"(?i)registry\.npmjs\.org/(" + PKG_NAME + ")"), True),
    # Other npm CDNs (femto's documented CDN is jsDelivr; any of these naming femto must use its name).
    ("an esm.sh, esm.run, Skypack or jspm URL", re.compile(
        r"(?i)(?:esm\.sh|esm\.run|cdn\.skypack\.dev|jspm\.dev|ga\.jspm\.io)/(?:v\d+/)?(?:npm:)?(" + PKG_NAME + ")"), True),
    ("a cdnjs URL (femto is not on cdnjs; its CDN URLs are jsDelivr's npm/" + FEMTO_PACKAGE + ")",
     re.compile(r"(?i)cdnjs\.cloudflare\.com/ajax/libs/([\w.-]+)"), True),
    # "the femto.css package", "package femto-css": a package named in prose.
    ("a package named in prose", re.compile(
        r"(?i)(?<![\w@/.-])((?:@[\w.~-]+/)?[\w.~-]*femto[\w.~-]*)\s+(?:npm\s+)?package(?![\w-]|\.json|-lock\.json)"
        r"|\bpackage\s+(?:named\s+|called\s+)?[\"'`“]?((?:@[\w.~-]+/)?[\w.~-]*femto[\w.~-]*)"), True),
    ("a name@version specifier", re.compile(
        r"(?<![\w@/.-])((?:@[\w.~-]+/)?[\w.~-]*femto[\w.~-]*)@(?=\d|[\^~*]|(?:latest|next|alpha|beta|rc|canary)\b)", re.I), True),
    ("a dependency entry", re.compile(
        r"[\"']((?:@[\w.~-]+/)?[\w.~-]*femto[\w.~-]*)[\"']\s*:\s*[\"'](?:[\^~<>=]*\s*\d|\*|latest|next|alpha|beta)", re.I), False),
    # JavaScript's import (never CSS's @import "file.css", a relative file: CSS package imports are
    # the next context's).
    ("an import or require specifier", re.compile(
        r"(?:\bfrom\s*|(?<![@\w])import\s*\(?\s*|\brequire(?:\.resolve)?\s*\(\s*)[\"'`]((?:@[\w.~-]+/)?[\w~-][\w.~-]*)"), False),
    ("a CSS package import", re.compile(
        r"@import\s+(?:url\(\s*)?[\"']?(?:~((?:@[\w.~-]+/)?[\w~-][\w.~-]*)|(@[\w.~-]+/[\w.~-]+))"), False),
    # @import "femto/css/tokens/base.css": a path into a package (femto's README documents
    # @import "@leoherzog/femto/css/..." for npm installs). A bare name with no slash after it
    # ("femto.css") is a file, and a relative or absolute path never matches.
    ("a CSS @import package path", re.compile(r"@import\s+(?:url\(\s*)?[\"']([\w~-][\w.~-]*)/"), False),
)
INSTALL_COMMAND = re.compile(
    r"(?i)\b(?:(npm|pnpm|yarn|bun)\s+(?:install|i|add|in|ins|inst|insta|instal|isnt|isnta|isntal|isntall)"
    r"|(npx|bunx|pnpx|pnpm\s+dlx|yarn\s+dlx)|deno\s+(?:add|install))(?![\w-])([^\n;&|<>]*)")
INSTALL_VALUE_FLAGS = {"--prefix", "--registry", "--tag", "-w", "--workspace", "--cwd", "-C", "--filter", "--save-prefix",
                       "--cache", "--userconfig", "-p", "--package"}
COMPOSER = re.compile(r"(?i)(?<![\w-])(?:composer|packagist)(?![\w-])")
# "install femto with Composer", "available on Packagist", "get it via Composer"
COMPOSER_OFFER = re.compile(r"(?i)\b(?:install|installed|get|add|added|available|require|download|see|find|found|"
                            r"published|listed|is|are)\b(?:(?!\b(?:not|no|never|neither|nor)\b|n't)[^.\n]){0,40}?\b"
                            r"(?:with|via|through|from|on|using|in)\s+((?:composer|packagist))(?![\w-])")
COMPOSER_PACKAGE = re.compile(r"(?i)(?:\bcomposer\s+(?:global\s+)?(?:require|req|install|update|create-project)\s+(?:-\S+\s+)*"
                              r"|packagist\.org/packages/)([\w.-]+/[\w.-]+)")
TEXT_BLOCKS = {"#document", "html", "head", "body", "title", "p", "li", "dt", "dd", "td", "th", "tr", "caption",
               "figcaption", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "summary", "label", "legend",
               "option", "button", "pre", "div", "section", "article", "aside", "header", "footer", "nav", "main",
               "details", "dialog", "figure", "form", "fieldset", "table", "thead", "tbody", "tfoot", "ul", "ol", "dl",
               "menu", "search", "address", "template"}
CODE_TAGS = {"pre", "code", "samp", "kbd"}


# A clause that denies an offer: a negation before the Composer mention, in the same clause (clauses
# end at , ; : . ! ? and dashes, and at a contrast such as "but" or "however", which turns the
# sentence around: "npm is not needed, but you can install femto with Composer" offers it).
NEGATION = re.compile(r"(?i)\b(?:not|no|never|cannot|nothing|none|nowhere|neither|nor|without|unavailable)\b|n't\b|n’t\b")
CLAUSE_END = re.compile(r"(?i)[,;:.!?\n]\s|[—–]|\s-\s|\b(?:but|however|instead|yet|though|although|whereas|unless)\b")


def composer_negated(text: str, at: int) -> bool:
    """Whether the clause that holds the mention at offset `at` denies something before it."""
    before = text[:at]
    ends = list(CLAUSE_END.finditer(before))
    clause = before[ends[-1].end():] if ends else before
    return NEGATION.search(clause) is not None


def femto_like(name: str) -> bool:
    """A package name that means femto: it says femto, or is under the owner's npm name."""
    low = name.lower()
    return "femto" in low or low.lstrip("@").split("/")[0] == "leoherzog"


def install_names(cmd: str, args: str) -> list[str]:
    """Package names in an install command's arguments (npx and dlx: only the package they run)."""
    out, skip = [], False
    for tok in args.split():
        tok = tok.strip("\"'`(),").rstrip(".:")  # "npm install x." at the end of a sentence
        if skip or not tok:
            skip = False
            continue
        if tok.startswith("-"):
            skip = tok in INSTALL_VALUE_FLAGS
            continue
        tok = re.sub(r"^(?:npm|jsr):", "", tok)
        m = re.match(r"(@[^/@\s]+/[^/@\s]+)", tok) if tok.startswith("@") else None
        out.append(m.group(1) if m else tok.split("@", 1)[0] if not tok.startswith("@") else tok)
        if cmd:
            break
    return [n for n in out if n]


def js_strings(text: str) -> list[tuple[int, str]]:
    """(offset, value) of each string literal of a script, and of each run of literals joined with +
    ("https://cdn.jsdelivr.net/npm/" + "femto.css"), read as one string."""
    return literal_runs(js_tokens(text))


def data_block_strings(text: str) -> list[str]:
    """The string values (and keys) of a JSON data block (JSON-LD's downloadUrl, an import map), or
    its text when it is not JSON."""
    try:
        data = json.loads(text)
    except ValueError:
        return [text]
    out: list[str] = []

    def walk(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                out.append(k)
                walk(x)
    walk(data)
    return out


def page_texts(doc: Node) -> list[tuple[str, int, str]]:
    """(kind, line, text) pieces of a page: "prose" (each block element's own text, nested blocks
    apart), "code" (each outermost pre, code, samp or kbd), "attr" (each attribute value) and
    "script" (each string literal of its inline scripts). <style> is left out."""
    out: list[tuple[str, int, str]] = []
    texts: dict[int, list[str]] = {}
    lines: dict[int, int] = {}

    def walk(node: Node, key: int):
        for c in node.children:
            if isinstance(c, str):
                texts.setdefault(key, []).append(c)
            elif c.tag in ("script", "style"):
                if c.tag == "script" and script_kind(c) in ("classic", "module"):
                    out.extend(("script", c.line + line_of(c.text(), o) - 1, v) for o, v in js_strings(c.text()))
                elif c.tag == "script" and script_kind(c) in ("data", "importmap", "speculationrules"):
                    out.extend(("script", c.line, v) for v in data_block_strings(c.text()))
            elif c.tag in TEXT_BLOCKS:
                lines[id(c)] = c.line
                walk(c, id(c))
            else:
                walk(c, key)

    lines[id(doc)] = 0
    walk(doc, id(doc))
    out += [("prose", lines[k], "".join(v)) for k, v in texts.items() if "".join(v).strip()]
    for n in doc.iter():
        if n.tag in CODE_TAGS and not any(a.tag in CODE_TAGS for a in n.ancestors()):
            out.append(("code", n.line, n.text()))
        out += [("attr", n.line, v) for k, v in n.attrs.items() if v and k not in ("class", "id", "style")]
    return out


def package_findings(where: str, pieces: list[tuple[str, int, str]], bad: list[str], notes: list[str], others: set[str]):
    for kind, line, text in pieces:
        at = lambda o: f"{where}:{line + text.count(chr(10), 0, o)}" if line else where
        found: list[tuple[str, str, int]] = []
        for what, pattern, in_prose in PACKAGE_CONTEXTS:
            if kind == "prose" and not in_prose:
                continue
            for m in pattern.finditer(text):
                name = next(g for g in m.groups() if g is not None).rstrip(".")
                if what.startswith(("an import or require", "a CSS @import package path")) and not femto_like(name):
                    continue  # a local module or folder name, not a package
                found.append((what, name, m.start()))
        # Install commands, in prose too ("npm install femto.css"), a line continued with a backslash
        # read as one line (the same length, so offsets stay valid).
        joined = re.sub(r"\\\r?\n", lambda m: " " * len(m.group(0)), text)
        for m in INSTALL_COMMAND.finditer(joined):
            found += [("an install command", n, m.start()) for n in install_names(m.group(2) or "", m.group(3))]
        for what, name, o in found:
            if name == FEMTO_PACKAGE:
                continue
            if what == "a package named in prose" and name.lower() == "femto":
                continue  # "the femto package": femto itself, informally, not a package name
            if femto_like(name):
                hint = " (femto.css is a file name; the package is " + FEMTO_PACKAGE + ")" if name.lower() == "femto.css" else ""
                line_ = f"{at(o)}: {what} names {name!r}, not {FEMTO_PACKAGE}{hint}"
                if line_ not in bad:
                    bad.append(line_)
            else:
                others.add(name)
        # Composer: femto has none. A composer command, a Packagist URL or "install ... with Composer"
        # offers one and fails, unless it is Pico's (next to Pico, naming no femto package). A
        # sentence that only mentions Composer ("femto has no Composer package") is listed.
        femto_composer = {m.start() for m in COMPOSER_PACKAGE.finditer(text) if femto_like(m.group(1))}
        commands = {m.start() for m in COMPOSER_PACKAGE.finditer(text)}
        verbs = {m.start(1) for m in COMPOSER_OFFER.finditer(text)}
        pico = re.search(r"(?i)pico", text) is not None
        for m in COMPOSER.finditer(text):
            excerpt = " ".join(text[max(0, m.start() - 40):m.end() + 40].split())
            near_cmd = {o for o in commands if m.start() - 60 <= o <= m.end()}
            near = near_cmd | {o for o in verbs if m.start() - 60 <= o <= m.end()}
            negated = composer_negated(text, m.start())
            if pico and not (near & femto_composer):  # Pico's, unless it names femto
                line_ = f"{at(m.start())}: Composer next to Pico, read as Pico's package: …{excerpt}…"
                (notes if line_ not in notes else []).append(line_)
            elif near_cmd or (near and not negated):
                # A composer command or Packagist URL offers a package whatever the sentence says; an
                # install verb does unless its clause denies it ("You cannot install femto with Composer").
                line_ = f"{at(m.start())}: offers {m.group(0)}, but femto has no Composer package: …{excerpt}…"
                if line_ not in bad:
                    bad.append(line_)
            elif near:
                line_ = f"{at(m.start())}: says femto is not on {m.group(0)} (a negated sentence, not an offer): …{excerpt}…"
                (notes if line_ not in notes else []).append(line_)
            else:
                line_ = f"{at(m.start())}: mentions {m.group(0)} (femto has no Composer package; not an install offer): …{excerpt}…"
                (notes if line_ not in notes else []).append(line_)


def package_checks(ctx: Context, r: Result, repo: Path | None, commit: str):
    """Criterion 13: femto's package name and no Composer package, on every dist page and dist script
    (site/vendor/ copies excluded)."""
    dist = ctx.dist
    skip = (dist / "vendor",)
    bad: list[str] = []
    notes: list[str] = []
    others: set[str] = set()
    pages = files_under(dist, (".html",), skip)
    scripts = files_under(dist, (".js", ".mjs"), skip)
    for p in pages:
        package_findings(rel(ctx.root, p), page_texts(ctx.page(p)), bad, notes, others)
    for p in scripts:
        text = p.read_text(encoding="utf-8", errors="replace")
        package_findings(rel(ctx.root, p), [("script", line_of(text, o), v) for o, v in js_strings(text)], bad, notes, others)
    if repo is not None and commit:
        shown = git(repo, "show", f"{commit}:package.json")
        try:
            name = json.loads(shown.stdout).get("name") if shown.returncode == 0 else None
        except ValueError:
            name = None
        if name != FEMTO_PACKAGE:
            r.fail(f"femto's package.json at {commit[:8]} names {name!r}, not {FEMTO_PACKAGE} (the owner's name for now): ask the owner")
        if git(repo, "cat-file", "-e", f"{commit}:composer.json").returncode == 0:
            r.note(f"femto at {commit[:8]} still has a composer.json, but the owner says femto has no Composer package")
    r.fails(f"{len(bad)} place(s) name femto's package other than {FEMTO_PACKAGE}, or a Composer package:", bad, "more")
    if not bad:
        r.ok(f"{len(pages)} pages and {len(scripts)} scripts in dist/: every package name for femto is {FEMTO_PACKAGE}, "
             "and nothing names a Composer package")
    for line_ in capped(notes):
        r.note(line_)
    if others:
        r.note(f"other packages named (not femto, not judged): {', '.join(sorted(others)[:12])}" + (" ..." if len(others) > 12 else ""))


def content_checks(ctx: Context, r: Result) -> None:
    root, dist, vendor = ctx.root, ctx.dist, ctx.site / "vendor/femto"
    docs = dist / "docs.html"
    if not docs.is_file():
        r.not_yet("no dist/docs.html (npm run build writes it)")
        return
    src = ctx.source() or {}
    version, commit, tag = src.get("version", ""), src.get("commit", ""), src.get("tag", "none")
    doc = ctx.page(docs)
    main = next(iter(doc.find_all("main")), None) or next(iter(doc.find_all("body")), doc)
    text = main.text()
    attr_text = "\n".join(v for n in main.iter() for k, v in n.attrs.items() if k in ("href", "src", "content", "value"))

    # 1. Custom properties.
    declared, referenced = set(), set()
    for f in ("dist/femto.css", "dist/femto.colors.css"):
        if (vendor / f).is_file():
            d, ref = femto_names((vendor / f).read_text(encoding="utf-8"))
            declared |= d
            referenced |= ref
    if not declared:
        r.fail("site/vendor/femto/dist/femto.css is missing, so the --femto-* names cannot be checked")
    site_declared = set()
    for p in files_under(ctx.site / "assets/css", (".css",)):
        site_declared |= femto_names(p.read_text(encoding="utf-8", errors="replace"))[0]
    used = {}
    for m in re.finditer(r"--femto-[\w-]*", text):
        nxt = text[m.end() : m.end() + 1]
        used.setdefault((m.group(0), (nxt != "" and nxt in "<*{[") or m.group(0).endswith("-")), m.start())
    bad_names = []
    for (name, prefix), _ in sorted(used.items()):
        if prefix:
            stem = name.rstrip("-")
            if not any(d.startswith(stem) for d in declared | referenced):
                bad_names.append(f"{name}… (pattern): no femto name starts with it")
        elif name in declared:
            continue
        elif name in referenced:
            r.note(f"{name} is read by femto but declared nowhere in it (set by the page's script)")
        elif name in site_declared:
            bad_names.append(f"{name}: a site-internal token, not femto's")
        else:
            bad_names.append(f"{name}: declared in neither femto.css nor femto.colors.css")
    r.fails(f"{len(bad_names)} --femto-* name(s) in the docs are not femto's:", bad_names, "more names")
    if not bad_names and declared:
        r.ok(f"{len(used)} distinct --femto-* names in the docs, all femto's")

    # 2. Files and URLs.
    paths, bad_paths = set(), []
    blob = text + "\n" + attr_text
    for m in re.finditer(re.escape(FEMTO_PACKAGE) + r"(?:@[^/\s\"'<>]+)?/([^\s\"'<>,)]+)", blob):
        if not re.search(r"(?:npmjs\.(?:com|org)/package|jsdelivr\.com/package/npm|data\.jsdelivr\.com/v1/packages?/npm)/$",
                         blob[max(0, m.start() - 40):m.start()]):  # a package page or API URL: not a file path
            paths.add(m.group(1).rstrip(".:;!?"))  # a sentence's end is not part of the path
    for m in re.finditer(r"(?<![\w./@-])((?:dist|css)/[\w./<>*-]+\.css)\b", blob):
        paths.add(m.group(1))
    for p in sorted(paths):
        if re.search(r"[<>*{]", p):
            continue
        if not (vendor / p).is_file():
            bad_paths.append(f"{p}: not a file in site/vendor/femto/")
    refs = set()
    for m in re.finditer(re.escape(FEMTO_GITHUB) + r"/(?:blob|tree|raw|commit)/([^/\s\"'<>#?]+)", blob):
        refs.add(m.group(1))
    for ref in sorted(refs):
        if not ((len(ref) >= 7 and commit.startswith(ref)) or ref in tag.split(", ")):
            bad_paths.append(f"{FEMTO_GITHUB}/…/{ref}: not the vendored commit {commit[:8]} or tag {tag}")
    r.fails(f"{len(bad_paths)} femto file path(s), URL(s) or repository link(s) do not match the vendored femto:", bad_paths, "more")
    if not bad_paths:
        r.ok(f"{len(paths)} femto paths and {len(refs)} repository links match site/vendor/femto/ and SOURCE")

    # 3. Classes in example markup.
    femto_css = (vendor / "dist/femto.css").read_text(encoding="utf-8") if (vendor / "dist/femto.css").is_file() else ""
    colors_css = (vendor / "dist/femto.colors.css").read_text(encoding="utf-8") if (vendor / "dist/femto.colors.css").is_file() else ""
    femto_classes, color_classes = css_classes(femto_css), css_classes(colors_css)
    repo, _ = ctx.femto_repo(commit) if commit else (None, [])
    readme = git(repo, "show", f"{commit}:README.md").stdout if repo else ""
    if not readme:
        r.not_yet("femto's README at the vendored commit is not available (no femto checkout), so classes are unchecked")
    else:
        section = markdown_section(readme, "Classes and attributes")
        listed = set()
        for span in re.findall(r"`([^`]+)`", section):
            listed |= set(re.findall(r"(?<![\w-])\.([A-Za-z_][\w-]*)", span))
            for cls in re.findall(r"class=\"([^\"]*)\"", span):
                listed |= set(cls.split())
        example_classes: dict[str, int] = {}
        for n in main.iter():
            if n.tag != "#document" and example_container(n) is not None:
                for c in n.classes():
                    example_classes.setdefault(c, n.line)
        for code in main.find_all("code"):
            if re.search(r"language-(html|markup|jsx)", code.attrs.get("class", "")):
                for cls in re.findall(r"class=\"([^\"]*)\"", code.text()):
                    for c in cls.split():
                        example_classes.setdefault(c, code.line)
        unlisted = [f".{c} (line {line})" for c, line in sorted(example_classes.items())
                    if c in femto_classes and c not in listed and c not in color_classes]
        r.fails(f"{len(unlisted)} femto class(es) in example markup are not in README 'Classes and attributes' or femto.colors.css:", unlisted, "more classes")
        if not unlisted:
            r.ok(f"{len(example_classes)} classes in example markup; every femto one is listed in the README or is a color utility")
        site_only = sorted(c for c in example_classes if c not in femto_classes and c not in color_classes)
        if site_only:
            r.note(f"{len(site_only)} example classes femto does not style (site classes): {', '.join(site_only[:10])}" + (" ..." if len(site_only) > 10 else ""))

    # 4. Version strings.
    page_text = (next(iter(doc.find_all("body")), doc)).text()
    found, bad_versions = set(), []
    for m in re.finditer(re.escape(FEMTO_PACKAGE) + r"@(\d[\w.-]*)", page_text + "\n" + "\n".join(
            v for n in doc.iter() for v in n.attrs.values())):
        found.add(m.group(1).rstrip("."))
    for m in re.finditer(r"\bfemto(?:\.css)?\s+v?(\d+(?:\.\d+){0,2}(?:-[0-9A-Za-z.]+)?)", page_text, re.I):
        found.add(m.group(1).rstrip("."))
    for m in re.finditer(r"(?<![\w.])v?(\d+\.\d+\.\d+-[0-9A-Za-z]+(?:\.[0-9A-Za-z]+)*)", page_text):
        found.add(m.group(1))
    for v in sorted(found):
        if not version_ok(v, version):
            bad_versions.append(f"{v}: not {version} (SOURCE)")
    r.fails(f"{len(bad_versions)} femto version string(s) do not match SOURCE:", bad_versions)
    if not bad_versions:
        r.ok(f"femto version strings in docs.html ({', '.join(sorted(found)) or 'none'}) match SOURCE's {version}")

    # 5. The package name, and no Composer package (the owner, 2026-10-30).
    package_checks(ctx, r, repo, commit)

    # 6. No Pico: criterion 14's grep.
    hits, bad = pico_grep(ctx)
    r.fails(f"git grep -il pico lists {len(bad)} file(s) outside the allowed places:", bad, "more files")
    if not bad:
        r.ok("git grep -il pico lists only allowed places")


def criterion_13(ctx: Context) -> Result:
    r = Result(13, "Content: the content checks in 04 §3 pass")
    if ctx.phase < 4:
        preview = Result(13, "")
        content_checks(ctx, preview)
        r.not_yet(f"the content checks apply from Phase 4 (04 §3); phase is {ctx.phase} ({ctx.phase_why}); run with --phase 4 to apply them now")
        r.note(f"preview: {len(preview.failures)} failing line(s), {len(preview.pending)} part(s) not yet checkable"
               + (f": {preview.pending[0]}" if preview.pending else ""))
        return r
    content_checks(ctx, r)
    return r


# ---------------------------------------------------------------------------- criterion 14


def pico_allowed(path: str) -> bool:
    return path in PICO_ALLOWED or path.startswith(PICO_ALLOWED_DIR)


def pico_grep(ctx: Context) -> tuple[list[str], list[str]]:
    if "pico" not in ctx.cache:
        tracked = git(ctx.root, "grep", "-il", "pico", *PICO_SPEC).stdout.split("\n")
        untracked = git(ctx.root, "grep", "-il", "--untracked", "pico", *PICO_SPEC).stdout.split("\n")
        hits = sorted({h for h in tracked + untracked if h})
        ctx.cache["pico"] = (hits, [h for h in hits if not pico_allowed(h)], len([h for h in tracked if h]))
    hits, bad, _ = ctx.cache["pico"]
    return hits, bad


def criterion_14(ctx: Context) -> Result:
    r = Result(14, "No Pico: git grep -il pico lists only the allowed files")
    hits, bad = pico_grep(ctx)
    r.ok(f"git grep -il pico -- . ':!docs/research' ':!tests' ':!PLAN.md' ':!PROMPT.md': {ctx.cache['pico'][2]} tracked files; "
         f"{len(hits)} with --untracked")
    r.fails(f"{len(bad)} file(s) outside the allow-list mention pico:", bad, "more files")
    allowed = [h for h in hits if pico_allowed(h)]
    r.ok("allowed files that mention pico: " + (", ".join(allowed) if allowed else "none"))
    return r


# ---------------------------------------------------------------------------- criterion 15


NON_LOADING_RELS = {"canonical", "alternate", "author", "bookmark", "external", "help", "license", "me", "next",
                    "nofollow", "noopener", "noreferrer", "opener", "prev", "search", "tag", "privacy-policy", "terms-of-service"}
RESOURCE_ATTRS = {"script": ("src", "href", "xlink:href"), "img": ("src", "srcset"), "source": ("src", "srcset"),
                  "video": ("src", "poster"), "audio": ("src",), "track": ("src",), "iframe": ("src",), "frame": ("src",),
                  "embed": ("src",), "object": ("data",), "use": ("href", "xlink:href"),
                  # <image> is SVG's image (href), and in HTML the parser turns <image src> into <img src>
                  "image": ("src", "srcset", "href", "xlink:href"),
                  "feimage": ("href", "xlink:href"), "body": ("background",), "table": ("background",),
                  "td": ("background",), "th": ("background",)}  # background: the legacy attribute loads an image
# HTML's JavaScript MIME type essence strings: a <script> with any of these types is a classic script.
JS_MIME = {"application/ecmascript", "application/javascript", "application/x-ecmascript", "application/x-javascript",
           "text/ecmascript", "text/javascript", "text/javascript1.0", "text/javascript1.1", "text/javascript1.2",
           "text/javascript1.3", "text/javascript1.4", "text/javascript1.5", "text/jscript", "text/livescript",
           "text/x-ecmascript", "text/x-javascript"}
PLACEHOLDER = "\ue000"  # what a static read cannot know: a template substitution, a variable between literals
URL_STRIP = "".join(chr(c) for c in range(0x21))  # C0 controls and space, which URL parsing trims


def script_kind(n: Node) -> str:
    """How a browser treats a <script> (HTML's "prepare the script element"): "classic", "module",
    "importmap", "speculationrules", or "data" (a data block, never run)."""
    t = n.attrs.get("type")
    if t is None:
        lang = n.attrs.get("language")
        if not lang:
            return "classic"
        t = "text/" + lang
    t = t.strip(" \t\n\f\r").lower()
    if t == "" or t in JS_MIME:
        return "classic"
    return t if t in ("module", "importmap", "speculationrules") else "data"


def inert(n: Node) -> bool:
    """Inside <template> or <noscript>: a script there never runs on load (scripting on)."""
    return any(a.tag in ("template", "noscript") for a in n.ancestors())


def same_origin(url: str) -> bool | None:
    """True for a same-origin URL, None for https://femto.style itself (same origin once deployed),
    False otherwise. The URL is read as a browser reads it: leading and trailing spaces and controls
    are trimmed, tabs and newlines inside it dropped, and in an http(s) or relative URL a backslash
    is a slash, so `\\\\host/x` is protocol-relative. http://femto.style is another origin (the
    scheme differs, and the browser blocks it as mixed content)."""
    url = re.sub(r"[\t\n\r]", "", url.strip(URL_STRIP))
    if not url or url.startswith("#"):
        return True
    m = re.match(r"([A-Za-z][A-Za-z0-9+.-]*):", url)
    scheme = m.group(1).lower() if m else ""
    if scheme in ("", "http", "https", "ws", "wss", "ftp", "file"):
        url = url.replace("\\", "/")
    if url.startswith("//") or scheme in ("http", "https"):
        u = urlsplit(url)
        try:
            port = u.port
        except ValueError:
            return False
        return None if scheme in ("", "https") and u.hostname == "femto.style" and port in (None, 443) else False
    return scheme in ("", "data", "blob", "about", "javascript")


def built_host(url: str) -> bool:
    """An absolute URL whose host is built at run time (holds a PLACEHOLDER)."""
    m = re.match(r"\s*(?:[A-Za-z][\w+.-]*:)?[/\\]{2}([^/\\?#]*)", url)
    return bool(m and PLACEHOLDER in m.group(1))


def shown_url(url: str) -> str:
    return url.replace(PLACEHOLDER, "${…}")[:100]


def srcset_urls(value: str) -> list[str]:
    return [c.strip().split()[0] for c in value.split(",") if c.strip()]


def json_urls(data, kind: str) -> list[str]:
    """The URLs an import map maps to (its keys only name what is mapped) or that speculation rules
    prefetch or prerender."""
    out: list[str] = []
    if not isinstance(data, dict):
        return out
    if kind == "importmap":
        scopes = data.get("scopes") if isinstance(data.get("scopes"), dict) else {}
        for m in [data.get("imports"), *scopes.values()]:
            if isinstance(m, dict):
                out += [v for v in m.values() if isinstance(v, str)]
    else:
        for key in ("prefetch", "prerender"):
            for rule in data.get(key) or []:
                if isinstance(rule, dict) and isinstance(rule.get("urls"), list):
                    out += [u for u in rule["urls"] if isinstance(u, str)]
    return out


# Elements whose URL is a document: a data: URL there is a document of its own, whose markup loads
# what it names (an <img> or CSS url() data: SVG is an image, which loads nothing).
DATA_DOCUMENT_ATTRS = {"iframe": ("src",), "frame": ("src",), "object": ("data",), "embed": ("src",)}
DATA_DOCUMENT_TYPES = {"text/html", "application/xhtml+xml", "image/svg+xml", "text/xml", "application/xml"}


def data_document(url: str) -> str | None:
    """The markup of a data: URL whose type is a document type (HTML, XHTML, SVG, XML), decoded
    (base64 or percent-encoding), or None."""
    u = re.sub(r"[\t\n\r]", "", url.strip(URL_STRIP))
    m = re.match(r"(?i)data:([^,]*),(.*)\Z", u, re.S)
    if not m:
        return None
    params = [x.strip().lower() for x in m.group(1).split(";")]
    if (params[0] or "text/plain") not in DATA_DOCUMENT_TYPES:
        return None
    body = unquote_to_bytes(m.group(2))
    if "base64" in params[1:]:
        import base64
        try:
            body = base64.b64decode(re.sub(rb"[\s]", b"", body) + b"===", validate=False)
        except ValueError:
            return None
    return body.decode("utf-8", "replace")


def markup_urls(doc: Node) -> list[tuple[int, str, str]]:
    """(line, url, what) for every URL the markup itself loads: loading <link>s, src, srcset,
    poster, data and SVG href attributes, <base href> (every relative URL resolves against it),
    <iframe srcdoc> documents and data: documents (an iframe, frame, object or embed whose data: URL
    is HTML, XHTML, SVG or XML), CSS in <style> and style="", and the URLs of import maps and
    speculation rules. <template> content counts: a script clones it into the page."""
    out: list[tuple[int, str, str]] = []
    for n in doc.iter():
        tag, attrs = n.tag, n.attrs
        if tag == "#document":
            continue
        if tag == "base" and "href" in attrs:
            out.append((n.line, attrs["href"], "<base href>"))
        elif tag == "link":
            rels = set(attrs.get("rel", "").lower().split())
            if not (rels and rels <= NON_LOADING_RELS):
                if "href" in attrs:
                    out.append((n.line, attrs["href"], f"<link rel=\"{attrs.get('rel', '')}\">"))
                out += [(n.line, u, "<link imagesrcset>") for u in srcset_urls(attrs.get("imagesrcset", ""))]
        elif tag == "input" and attrs.get("type", "").lower() == "image" and "src" in attrs:
            out.append((n.line, attrs["src"], "<input type=image src>"))
        elif tag in RESOURCE_ATTRS:
            for a in RESOURCE_ATTRS[tag]:
                if a in attrs:
                    out += [(n.line, u, f"<{tag} {a}>") for u in (srcset_urls(attrs[a]) if a.endswith("srcset") else [attrs[a]])]
        if tag == "iframe" and "srcdoc" in attrs:
            out += [(n.line, u, f"{w} in <iframe srcdoc>") for _, u, w in markup_urls(parse_html(attrs["srcdoc"]))]
        for a in DATA_DOCUMENT_ATTRS.get(tag, ()):
            doc_text = data_document(attrs.get(a, ""))
            if doc_text is not None:
                out += [(n.line, u, f"{w} in a data: document (<{tag} {a}>)") for _, u, w in markup_urls(parse_html(doc_text))]
        if tag == "style":
            out += [(n.line, u, "a URL in <style>") for _, u in css_urls(scan_css(n.text())[0])]
        if "style" in attrs:
            out += [(n.line, u, "a URL in style=\"\"") for _, u in css_urls(scan_css(attrs["style"])[0])]
        if tag == "script" and script_kind(n) in ("importmap", "speculationrules"):
            kind = script_kind(n)
            try:
                data = json.loads(n.text())
            except ValueError:
                data = None
            out += [(n.line, u, f"<script type=\"{kind}\">") for u in json_urls(data, kind)]
    return out


def budget(plan: Path) -> list[tuple[float, str, str]]:
    """(bytes, kind, sentence) for the /docs HTML budget recorded in PLAN.md's Risks section."""
    if not plan.is_file():
        return []
    text = plan.read_text(encoding="utf-8")
    m = re.search(r"^## Risks.*?(?=^## )", text, re.S | re.M)
    if not m:
        return []
    units = {"b": 1, "bytes": 1, "kb": 1000, "kib": 1024, "mb": 1000**2, "mib": 1024**2}
    for sentence in re.split(r"(?<=[.|])\s+|\n", m.group(0)):
        at = re.search(r"budget", sentence, re.I)
        if not at:
            continue
        out = []
        for s in re.finditer(r"(\d+(?:\.\d+)?)\s*(bytes|B|KB|kB|KiB|MB|MiB)\b(?:\s+(?:with\s+)?(Brotli|gzip(?:ped)?|raw|uncompressed))?",
                             sentence[at.end():]):
            kind = (s.group(3) or "raw").lower()
            kind = "gzip" if kind.startswith("gzip") else "raw" if kind == "uncompressed" else kind
            out.append((float(s.group(1)) * units[s.group(2).lower()], kind, sentence.strip()))
        if out:
            return out
    return []


def compressed_size(data: bytes, kind: str) -> int:
    if kind == "raw":
        return len(data)
    if kind == "gzip":
        return len(gzip.compress(data, 9, mtime=0))
    proc = subprocess.run(["node", "-e", "const z=require('zlib');let c=[];process.stdin.on('data',d=>c.push(d));"
                           "process.stdin.on('end',()=>process.stdout.write(String(z.brotliCompressSync(Buffer.concat(c),"
                           "{params:{[z.constants.BROTLI_PARAM_QUALITY]:11}}).length)))"], input=data, capture_output=True, check=True)
    return int(proc.stdout)


# JavaScript, read as tokens (js_tokens: espree; js_tokens_heuristic: the fallback's keyword sets).
JS_EXPR_KEYWORDS = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do",
                    "else", "yield", "await", "extends", "default"}
# After the ) that closes the head of one of these, a statement starts: a slash there opens a regex
# (`if (ok) /"/.test(s)`), where after any other ) it is a division.
JS_CONTROL_HEADS = {"if", "for", "while", "with"}
JS_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
JS_SPACE = " \t\n\r\f\v\u00a0\ufeff\u2028\u2029"
# parseFromString's document is inert, but its nodes load once a script moves them into the page.
HTML_SINK_CALLS = {"write", "writeln", "insertAdjacentHTML", "createContextualFragment", "setHTMLUnsafe", "setHTML",
                   "parseFromString"}
HTML_SINK_PROPS = {"innerHTML", "outerHTML", "srcdoc"}  # an iframe's srcdoc is a document of its own
# An absolute URL in a string: http(s)://host, or //host at the start of the string or after a
# quote, a parenthesis, "=", "," or a space (a protocol-relative URL in a quoted attribute). Any
# host: dotted, localhost, an IP address, a port.
ABS_URL = re.compile(r"(?:(?<![\w.+-])(?i:https?|wss?):|^|(?<=[\"'(=\s,]))[/\\]{2}[^\s/\\\"'`<>?#)]+[^\s\"'`<>)]*", re.M)


def js_unescape(body: str) -> str:
    out, i, n = [], 0, len(body)
    while i < n:
        c = body[i]
        if c != "\\" or i + 1 >= n:
            out.append(c)
            i += 1
            continue
        e = body[i + 1]
        if e == "x" and re.fullmatch(r"[0-9A-Fa-f]{2}", body[i + 2:i + 4]):
            out.append(chr(int(body[i + 2:i + 4], 16)))
            i += 4
        elif e == "u" and body[i + 2:i + 3] == "{" and re.match(r"[0-9A-Fa-f]{1,6}\}", body[i + 3:]):
            j = body.index("}", i + 3)
            out.append(chr(min(int(body[i + 3:j], 16), 0x10FFFF)))
            i = j + 1
        elif e == "u" and re.fullmatch(r"[0-9A-Fa-f]{4}", body[i + 2:i + 6]):
            out.append(chr(int(body[i + 2:i + 6], 16)))
            i += 6
        elif e == "\r":
            i += 3 if body[i + 2:i + 3] == "\n" else 2
        elif e in "\n\u2028\u2029":
            i += 2
        else:
            out.append(JS_ESCAPES.get(e, e))
            i += 2
    return "".join(out)


# JavaScript is read with espree, ESLint's own parser (installed with eslint, a devDependency): a
# full parse gives exact tokens, so a slash is a regular expression or a division as the engine reads
# it (`{} / 2 + import("x")` is a division, then an import). One node process serves every script
# of a run. A script espree cannot parse is read with the heuristic tokenizer below and reported.
ESPREE = Path(__file__).resolve().parents[1] / "node_modules" / "espree" / "dist" / "espree.cjs"
_ESPREE_SERVER = r"""
const espree = require(process.argv[1]);
const rl = require("readline").createInterface({ input: process.stdin });
const modes = [{ sourceType: "module" }, { sourceType: "script" }, { sourceType: "commonjs" }];
rl.on("line", (line) => {
  const { code } = JSON.parse(line);
  let out = null, err = null;
  for (const m of modes) {
    try {
      const ast = espree.parse(code, Object.assign({ ecmaVersion: "latest", tokens: true, range: true }, m));
      out = ast.tokens.map((t) => [t.type, t.range[0], t.range[1], t.value]);
      break;
    } catch (e) { if (err === null) err = String((e && e.message) || e); }
  }
  process.stdout.write(JSON.stringify(out ? { tokens: out } : { error: err }) + "\n");
});
"""
_espree = {"proc": None, "why": None}
JS_UNPARSED: dict[str, str] = {}  # the first 80 characters of a script espree could not read -> why


def _espree_stop():
    proc = _espree["proc"]
    if proc is not None and proc.poll() is None:
        try:
            proc.stdin.close()
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            proc.kill()


def espree_tokens(text: str) -> list | None:
    """espree's tokens of a script, [type, start, end, value]; None when it cannot read the script (the
    reason goes to JS_UNPARSED) or cannot run."""
    if _espree["why"] is not None:
        JS_UNPARSED.setdefault(" ".join(text.split())[:80], _espree["why"])
        return None
    proc = _espree["proc"]
    if proc is None or proc.poll() is not None:
        if not ESPREE.is_file():
            _espree["why"] = f"espree is not installed ({ESPREE.relative_to(ESPREE.parents[3])}: npm install)"
            return espree_tokens(text)
        try:
            proc = subprocess.Popen(["node", "-e", _ESPREE_SERVER, str(ESPREE)], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1)
        except OSError as e:
            _espree["why"] = f"node cannot run: {e}"
            return espree_tokens(text)
        _espree["proc"] = proc
        atexit.register(_espree_stop)
    try:
        proc.stdin.write(json.dumps({"code": text}) + "\n")
        proc.stdin.flush()
        res = json.loads(proc.stdout.readline() or "null")
    except (OSError, ValueError) as e:
        _espree["why"] = f"the espree process failed: {e}"
        return espree_tokens(text)
    if not isinstance(res, dict) or "tokens" not in res:
        JS_UNPARSED.setdefault(" ".join(text.split())[:80], (res or {}).get("error") if isinstance(res, dict) else "no answer")
        return None
    return res["tokens"]


def js_tokens(text: str) -> list[tuple[str, int, int, str]]:
    """(kind, start, end, value) for each token of JavaScript source, comments and spaces left out.
    Kinds: "str" (a string literal, or a whole template literal at its opening backtick, with its
    escapes decoded and each substitution as PLACEHOLDER; the substitution's own tokens follow it),
    "name" (identifiers and keywords, escapes decoded), "num", "regex" and "punct" (one character).
    From espree's exact tokens; js_tokens_heuristic() for a script espree cannot read."""
    raw = espree_tokens(text)
    if raw is None:
        return js_tokens_heuristic(text)
    toks: list[tuple[str, int, int, str]] = []
    open_tpl: list[tuple[int, list[str]]] = []  # open template literals: (token index, chunks so far)
    for typ, start, end, v in raw:
        if typ == "Template":
            body = v[1:]
            closed = body.endswith("`")
            chunk = js_unescape(body[:-1] if closed else body[:-2])
            if v.startswith("`"):
                if closed:
                    toks.append(("str", start, end, chunk))
                else:
                    open_tpl.append((len(toks), [chunk]))
                    toks.append(("str", start, end, ""))
            elif open_tpl:
                idx, chunks = open_tpl[-1]
                chunks.append(chunk)
                if closed:
                    open_tpl.pop()
                    toks[idx] = ("str", toks[idx][1], end, PLACEHOLDER.join(chunks))
        elif typ == "String":
            toks.append(("str", start, end, js_unescape(v[1:-1])))
        elif typ == "Punctuator":
            toks += [("punct", start + i, start + i + 1, c) for i, c in enumerate(v)]
        elif typ == "RegularExpression":
            toks.append(("regex", start, end, text[start:end]))
        elif typ == "Numeric":
            toks.append(("num", start, end, v))
        else:  # Keyword, Identifier, Boolean, Null, PrivateIdentifier
            toks.append(("name", start, end, v))
    for idx, chunks in open_tpl:
        toks[idx] = ("str", toks[idx][1], len(text), PLACEHOLDER.join(chunks))
    return toks


def js_tokens_heuristic(text: str) -> list[tuple[str, int, int, str]]:
    """js_tokens() without a parser: enough of the lexical grammar to keep comments out, to tell a
    regular expression from a division in the common cases (after a keyword such as `return` a slash
    opens a regex), to follow a template literal into its substitutions, and to decode string
    escapes (`https:\\/\\/x` is `https://x`). Used only for a script espree cannot read."""
    toks: list[tuple[str, int, int, str]] = []
    opened: list[tuple[int, int]] = []  # open substitutions: (brace depth at "${", template token index)
    chunks: dict[int, list[str]] = {}  # template token index: its text so far
    state = {"depth": 0, "subst": False}
    parens: list[bool] = []  # open ( : whether it opens the head of if, for, while or with
    control_close: set[int] = set()  # token indices of the ) that close such a head

    def keyword_at(k: int, words) -> bool:
        """Token k is one of words as a keyword, not a property name (x.if, x?.default)."""
        return (0 <= k < len(toks) and toks[k][0] == "name" and toks[k][3] in words
                and not (k and toks[k - 1][0] == "punct" and toks[k - 1][3] == "."))
    i, n = 0, len(text)

    def add(tok: tuple[str, int, int, str]):
        toks.append(tok)
        state["subst"] = False

    def template(start: int, idx: int) -> int:
        j = start
        while j < n and text[j] != "`" and not text.startswith("${", j):
            j += 2 if text[j] == "\\" else 1
        chunks[idx].append(js_unescape(text[start:min(j, n)]))
        if j < n and text[j] != "`":
            opened.append((state["depth"], idx))
            state["subst"] = True
            return j + 2
        toks[idx] = ("str", toks[idx][1], min(j + 1, n), PLACEHOLDER.join(chunks.pop(idx)))
        return j + 1

    def regex_allowed() -> bool:
        if state["subst"] or not toks:
            return True
        kind, _, _, v = toks[-1]
        if kind == "name":
            return keyword_at(len(toks) - 1, JS_EXPR_KEYWORDS)
        if kind == "punct" and v == ")":
            return len(toks) - 1 in control_close
        if kind != "punct" or v == "]":
            return False
        if v in "+-" and len(toks) >= 3 and toks[-2][3] == v and toks[-2][2] == toks[-1][1] and (
                toks[-3][0] in ("name", "num", "str") or toks[-3][3] in ")]"):
            return False  # after a postfix ++ or --
        return True

    while i < n:
        c = text[i]
        if c in JS_SPACE:
            i += 1
        elif text.startswith("//", i) or (i == 0 and text.startswith("#!")):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            add(("str", i, min(j + 1, n), js_unescape(text[i + 1:min(j, n)])))
            i = j + 1
        elif c == "`":
            idx = len(toks)
            add(("str", i, i + 1, ""))
            chunks[idx] = []
            i = template(i + 1, idx)
        elif c == "}" and opened and opened[-1][0] == state["depth"]:
            i = template(i + 1, opened.pop()[1])
        elif c == "/" and regex_allowed():
            j, cls = i + 1, False
            while j < n and text[j] != "\n":
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "[":
                    cls = True
                elif text[j] == "]":
                    cls = False
                elif text[j] == "/" and not cls:
                    break
                j += 1
            j += 1
            while j < n and (text[j].isalnum() or text[j] in "_$"):
                j += 1
            add(("regex", i, min(j, n), text[i:j]))
            i = j
        elif c.isalpha() or c in "_$#\\" or ord(c) > 127:
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "_$\\" or (ord(text[j]) > 127 and text[j] not in JS_SPACE)):
                j += 1
            name = text[i:j]
            add(("name", i, j, js_unescape(name) if "\\" in name else name))
            i = j
        elif c.isdigit() or (c == "." and text[i + 1:i + 2].isdigit()):
            j = i + 1
            while j < n and (text[j].isalnum() or text[j] in "._"):
                j += 1
            add(("num", i, j, text[i:j]))
            i = j
        else:
            if c == "{":
                state["depth"] += 1
            elif c == "}":
                state["depth"] = max(state["depth"] - 1, 0)
            elif c == "(":
                parens.append(keyword_at(len(toks) - 1, JS_CONTROL_HEADS)
                              or (keyword_at(len(toks) - 1, {"await"}) and keyword_at(len(toks) - 2, {"for"})))
            elif c == ")" and parens and parens.pop():
                control_close.add(len(toks))
            add(("punct", i, i + 1, c))
            i += 1
    for idx in list(chunks):  # an unterminated template
        toks[idx] = ("str", toks[idx][1], n, PLACEHOLDER.join(chunks.pop(idx)))
    return toks


def js_imports(toks: list[tuple[str, int, int, str]]) -> list[tuple[int, str]]:
    """(offset, specifier) of every `import … from "x"`, `export … from "x"`, `import "x"` and
    `import("x…")` whose specifier is (or starts with) a literal string."""
    out = []
    for k, (kind, start, _, v) in enumerate(toks):
        if kind != "name" or v not in ("import", "from") or (k and toks[k - 1][:1] == ("punct",) and toks[k - 1][3] == "."):
            continue
        j = k + 1
        if v == "import" and j < len(toks) and toks[j][0] == "punct" and toks[j][3] == "(":
            j += 1
            while j < len(toks) and toks[j][0] == "punct" and toks[j][3] == "(":  # import(("x"))
                j += 1
        if j < len(toks) and toks[j][0] == "str":
            out.append((start, toks[j][3]))
    return out


def join_literals(text: str, toks: list[tuple[str, int, int, str]], a: int, stop_comma: bool) -> str:
    """The string an expression starting at token a builds: literals joined by + are joined, and
    anything else becomes one PLACEHOLDER. It ends at ), ] or } closing an outer bracket, at ; (and
    , when stop_comma), or where a new statement starts on the next line."""
    parts: list[str] = []
    depth = 0
    for k in range(a, len(toks)):
        kind, start, _, v = toks[k]
        if kind == "punct":
            if v in "([{":
                depth += 1
            elif v in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and (v == ";" or (v == "," and stop_comma)):
                break
        elif k > a and depth == 0 and toks[k - 1][0] != "punct" and "\n" in text[toks[k - 1][2]:start]:
            break
        if kind == "str":
            parts.append(v)
        elif not (kind == "punct" and v == "+") and parts and parts[-1] != PLACEHOLDER:
            parts.append(PLACEHOLDER)
    return "".join(parts)


def js_html_writes(text: str, toks: list[tuple[str, int, int, str]]) -> list[tuple[int, str, str]]:
    """(offset, html, sink) for literal HTML that a script hands to the HTML parser: document.write()
    and writeln(), insertAdjacentHTML(), createContextualFragment(), setHTMLUnsafe(), and
    assignments to innerHTML or outerHTML. Elements in it load what they name, as in the page's own
    markup; text a script only displays (textContent) is not HTML and is not read here."""
    out = []
    for k, (kind, start, _, v) in enumerate(toks):
        if kind == "str" and v in HTML_SINK_CALLS | HTML_SINK_PROPS and 0 < k and k + 1 < len(toks) \
                and toks[k - 1][3] == "[" and toks[k + 1][3] == "]" and toks[k - 1][0] == toks[k + 1][0] == "punct":
            # document["write"](...), el["innerHTML"] = ...: read as the dotted forms
            toks = toks[:k - 1] + [("punct", toks[k - 1][1], toks[k - 1][2], "."), ("name", start, toks[k][2], v)] \
                + toks[k + 2:]
            return js_html_writes(text, toks)
        if kind != "name" or k + 1 >= len(toks) or toks[k + 1][0] != "punct":
            continue
        nxt = toks[k + 1][3]
        if v in HTML_SINK_CALLS and nxt == "." and k + 3 < len(toks) and toks[k + 2][3] in ("call", "apply") \
                and toks[k + 3][3] == "(":
            # document.write.call(document, "<x>") and .apply(document, ["<x>"]): the arguments after
            # the first (insertAdjacentHTML: after the second).
            a = arg_start(toks, k + 4, 1 + (v == "insertAdjacentHTML"))
            if a is None:
                continue
            if toks[k + 2][3] == "apply" and toks[a][0] == "punct" and toks[a][3] == "[":
                a += 1
            markup = join_literals(text, toks, a, stop_comma=False)
            if "<" in markup:
                out.append((start, markup, v))
            continue
        if v == "setAttribute" and nxt == "(" and k + 2 < len(toks) and toks[k + 2][0] == "str" \
                and toks[k + 2][3].lower() in ("srcdoc", "innerhtml"):
            a = arg_start(toks, k + 2, 1)  # el.setAttribute("srcdoc", "<x>")
            if a is not None:
                markup = join_literals(text, toks, a, stop_comma=True)
                if "<" in markup:
                    out.append((start, markup, "srcdoc"))
            continue
        if v in HTML_SINK_CALLS and nxt == "(":
            a = k + 2
            if v == "insertAdjacentHTML":  # the second argument
                depth = 0
                while a < len(toks) and not (toks[a][3] == "," and toks[a][0] == "punct" and depth == 0):
                    depth += toks[a][3] in "([{" if toks[a][0] == "punct" else 0
                    depth -= toks[a][3] in ")]}" if toks[a][0] == "punct" else 0
                    if depth < 0:
                        break
                    a += 1
                if depth < 0 or a >= len(toks):
                    continue
                a += 1
            markup = join_literals(text, toks, a, stop_comma=False)
        elif v in HTML_SINK_PROPS and k and toks[k - 1][3] == "." and nxt in "=+":
            a = k + 2
            if nxt == "+":
                if not (a < len(toks) and toks[a][3] == "=" and toks[a][1] == toks[k + 1][2]):
                    continue
                a += 1
            elif a < len(toks) and toks[a][3] == "=" and toks[a][1] == toks[k + 1][2]:
                continue  # == or ===: a comparison
            markup = join_literals(text, toks, a, stop_comma=True)
        else:
            continue
        if "<" in markup:
            out.append((start, markup, v))
    return out


def arg_start(toks: list[tuple[str, int, int, str]], a: int, skip: int) -> int | None:
    """The token index of a call's argument after `skip` arguments, from the token after its "(";
    None when the call has fewer."""
    depth = 0
    while skip and a < len(toks):
        t = toks[a]
        if t[0] == "punct" and t[3] in "([{":
            depth += 1
        elif t[0] == "punct" and t[3] in ")]}":
            if depth == 0:
                return None
            depth -= 1
        elif t[0] == "punct" and t[3] == "," and depth == 0:
            skip -= 1
        a += 1
    return a if a < len(toks) and not (toks[a][0] == "punct" and toks[a][3] == ")") else None


def literal_runs(toks: list[tuple[str, int, int, str]]) -> list[tuple[int, str]]:
    """(offset, value) of each string literal, and of each run of literals joined with +."""
    out = [(t[1], t[3]) for t in toks if t[0] == "str"]
    k = 0
    while k < len(toks):
        if toks[k][0] != "str":
            k += 1
            continue
        j, parts = k, [toks[k][3]]
        while j + 2 < len(toks) and toks[j + 1][:1] == ("punct",) and toks[j + 1][3] == "+" and toks[j + 2][0] == "str":
            j += 2
            parts.append(toks[j][3])
        if len(parts) > 1:
            out.append((toks[k][1], "".join(parts)))
        k = j + 1
    return out


def sink_uses(toks: list[tuple[str, int, int, str]], names: set[str], followed) -> list[tuple[int, str]]:
    """(offset, name) of every mention of one of names that followed(k) does not accept as a form the
    check reads: an identifier, or a string (a computed access such as x["write"], a name joined at
    run time from literals) equal to one of them."""
    out = []
    for k, (kind, start, _, v) in enumerate(toks):
        if kind == "name" and v in names and not followed(k):
            out.append((start, v))
    for o, v in literal_runs(toks):
        if v in names:
            k = next((i for i, t in enumerate(toks) if t[1] == o), -1)
            # x["write"](...) and x["innerHTML"] = ... are read as their dotted forms
            if not (k > 0 and toks[k - 1][3] == "[" and k + 1 < len(toks) and toks[k + 1][3] == "]" and followed(k)):
                out.append((o, v))
    return out


def html_sink_aliases(toks: list[tuple[str, int, int, str]]) -> list[tuple[int, str]]:
    """Uses of an HTML sink the check cannot follow to its argument: document.write and writeln,
    insertAdjacentHTML, createContextualFragment, setHTML(Unsafe), DOMParser's parseFromString and
    innerHTML, outerHTML or srcdoc anywhere but in a direct call (with .call or .apply too) or a
    direct assignment: an alias (const w = document.write), .bind(), Reflect.apply(), destructuring, a
    computed name. Then any string in any script may reach the HTML parser."""
    calls, props = HTML_SINK_CALLS, HTML_SINK_PROPS

    def followed(k):
        j = k + 1 if toks[k][0] == "name" else k + 2  # past x["name"]'s ]
        if j >= len(toks):
            return False
        nxt = toks[j][3]
        if toks[k][3] in calls:
            return nxt == "(" or (nxt == "." and j + 2 < len(toks) and toks[j + 1][3] in ("call", "apply")
                                  and toks[j + 2][3] == "(")
        if toks[k][3] in props:
            # an assignment the check reads, or a read (getting innerHTML never parses anything)
            return not (nxt == "." and j + 1 < len(toks) and toks[j + 1][3] in ("call", "apply", "bind"))
        return True
    return sink_uses(toks, calls | props, followed)


WORKER_NAMES = {"Worker", "SharedWorker", "serviceWorker", "importScripts", "addModule", "audioWorklet", "paintWorklet",
                "layoutWorklet", "animationWorklet"}


def worker_aliases(toks: list[tuple[str, int, int, str]]) -> list[tuple[int, str]]:
    """Uses of a worker or worklet API in a form js_workers() does not read (new (Worker)(url), const
    W = Worker, const sw = navigator.serviceWorker; sw.register(url), "serviceWorker" in navigator):
    then the check cannot tell which scripts run in a worker."""
    def followed(k):
        if toks[k][0] != "name":
            return False
        v = toks[k][3]
        nxt = toks[k + 1][3] if k + 1 < len(toks) else ""
        if v in ("Worker", "SharedWorker"):
            dotted = k and toks[k - 1][3] == "."
            return nxt == "(" and k > 0 and (toks[k - 1][3] == "new" or (dotted and k >= 3 and toks[k - 3][3] == "new"))
        if v == "serviceWorker":
            return nxt == "." and k + 3 < len(toks) and toks[k + 2][3] == "register" and toks[k + 3][3] == "("
        if v == "importScripts":
            return nxt == "("
        if v == "addModule":
            return nxt == "(" and k > 0 and toks[k - 1][3] == "."
        return nxt == "." and k + 3 < len(toks) and toks[k + 2][3] == "addModule" and toks[k + 3][3] == "("
    return sink_uses(toks, WORKER_NAMES, followed)


WORKER_CTORS = {"Worker", "SharedWorker"}


def js_workers(text: str, toks: list[tuple[str, int, int, str]]) -> list[tuple[int, str, str, str]]:
    """(offset, what, url, base) for every script a script starts in a worker: new Worker(url),
    new SharedWorker(url), navigator.serviceWorker.register(url), and each importScripts() argument.
    base is "script" for new URL("x", import.meta.url) (relative to the script's own file), else
    "document". A URL that is not literal holds PLACEHOLDER."""
    out = []
    for k, (kind, start, _, v) in enumerate(toks):
        if kind != "name" or k + 1 >= len(toks) or toks[k + 1][3] != "(" or toks[k + 1][0] != "punct":
            continue
        dotted = k and toks[k - 1][0] == "punct" and toks[k - 1][3] == "."
        if v in WORKER_CTORS and k and (toks[k - 1][3] == "new" or (dotted and k >= 3 and toks[k - 3][3] == "new")):
            what = f"new {v}()"
        elif v == "register" and dotted and k >= 2 and toks[k - 2][3] == "serviceWorker":
            what = "serviceWorker.register()"
        elif v == "addModule" and dotted:
            what = "a worklet's addModule()"
        elif v == "importScripts" and not dotted:
            a, depth = k + 2, 0
            args = [a]
            while a < len(toks):
                t = toks[a]
                if t[0] == "punct" and t[3] in "([{":
                    depth += 1
                elif t[0] == "punct" and t[3] in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                elif t[0] == "punct" and t[3] == "," and depth == 0:
                    args.append(a + 1)
                a += 1
            out += [(start, "importScripts()", join_literals(text, toks, x, stop_comma=True), "script") for x in args
                    if x < len(toks) and not (toks[x][0] == "punct" and toks[x][3] == ")")]
            continue
        else:
            continue
        a = k + 2
        if a + 2 < len(toks) and toks[a][3] == "new" and toks[a + 1][3] == "URL" and toks[a + 2][3] == "(":
            out.append((start, what, join_literals(text, toks, a + 3, stop_comma=True), "script"))
        else:
            out.append((start, what, join_literals(text, toks, a, stop_comma=True), "document"))
    return out


def js_scan(text: str, where: str, base_line: int, cross: list[str], shown: list[str], label: str = "",
            blocking: list[str] | None = None, workers: list | None = None, strict: str | bool = False,
            markup: str | None = None):
    """Criterion 15's static read of JavaScript: a dist file, an inline <script>, an event handler
    attribute or a javascript: URL. A static or dynamic import() of another origin, and HTML handed
    to the parser (document.write() and writeln(), with .call() and .apply() too, innerHTML,
    insertAdjacentHTML(), ...) whose elements load from another origin, go to `cross`. Any other
    absolute URL in a string goes to `shown`: it may be a fetch(), an inserted element or text a
    script only displays (a code sample), which a static read cannot tell apart, so the harness's
    network log decides (Resource Timing and CSP reports per dist document). A URL whose host is
    built at run time is listed too.

    markup (a reason) reads every string that holds markup as HTML written into the page: in a
    javascript: URL, whose string result is the frame's document, and in every script once any script
    uses an HTML sink in a form the check cannot follow to its argument (html_sink_aliases()).

    A script that document.write() or writeln() writes runs as if it were in the markup: a classic
    one without async or defer goes to `blocking`. Scripts started in a worker go to `workers`
    ((where, line, what, url, base)): a worker keeps its own network log, which no page can read,
    so criterion_15 reads the worker script itself with strict set (to the reason), where every
    absolute URL of another origin in a string fails (`cross`) instead of being listed."""
    toks = js_tokens(text)
    line = lambda o: base_line + line_of(text, o) - 1
    judged: set[str] = set()

    def show(o: int, what: str, url: str):
        entry = f"{where}:{line(o)}: {label}{what}{shown_url(url)}"
        if entry not in shown:
            shown.append(entry)

    def written_html(o: int, html_text: str, sink: str, how: str):
        written = parse_html(html_text)
        if blocking is not None and sink in ("write", "writeln", "*"):
            for n in written.iter():
                if n.tag != "script" or script_kind(n) != "classic" or inert(n):
                    continue
                src = next((n.attrs[a] for a in ("src", "href", "xlink:href") if a in n.attrs), None)
                if src is None:
                    blocking.append(f"{where}:{line(o)}: {label}an inline classic script that {how}")
                elif "async" not in n.attrs and "defer" not in n.attrs:
                    blocking.append(f"{where}:{line(o)}: {label}<script src={shown_url(src)!r}> that {how}, without "
                                    "async or defer")
        for _, url, what in markup_urls(written):
            if same_origin(url) is False:
                judged.add(url)
                if built_host(url):
                    show(o, f"writes {what} (host built at run time) ", url)
                else:
                    cross.append(f"{where}:{line(o)}: {label}{what} {shown_url(url)} in HTML that {how}")

    for o, spec in js_imports(toks):
        if same_origin(spec) is False:
            judged.add(spec)
            if built_host(spec):
                show(o, "imports (host built at run time) ", spec)
            else:
                cross.append(f"{where}:{line(o)}: {label}imports {shown_url(spec)}")
    done: set[int] = set()
    for o, html_text, sink in js_html_writes(text, toks):
        done.add(o)
        written_html(o, html_text, sink, f"document.{sink}() writes" if sink in ("write", "writeln") else
                     f"the script hands to {sink}")
    if markup:
        for o, v in literal_runs(toks):
            if re.search(r"<[A-Za-z!/]", v) and o not in done:
                written_html(o, v, "*", f"may reach the HTML parser ({markup})")
    for o, what, url, base in js_workers(text, toks):
        judged.add(url)
        if same_origin(url) is False and not built_host(url):
            cross.append(f"{where}:{line(o)}: {label}{what} loads {shown_url(url)}")
        elif workers is not None:
            workers.append((where, line(o), what, url, base))
        elif PLACEHOLDER in url or same_origin(url) is False:
            cross.append(f"{where}:{line(o)}: {label}{what} with a URL built at run time ({shown_url(url)}): a worker's "
                         "loads are in its own network log, which the harness cannot read, so its script must be a "
                         "file the static check can read")
    for kind, o, _, v in toks:
        if kind != "str":
            continue
        for m in ABS_URL.finditer(v):
            url = m.group(0)
            if SVG_NS.match(url) or same_origin(url) is not False or any(url in j or j in url for j in judged):
                continue
            if strict:
                why = strict if isinstance(strict, str) else "a script that runs in a worker"
                cross.append(f"{where}:{line(o)}: {label}{shown_url(url)} in {why} (a worker's loads are not in the "
                             "page's Resource Timing, so any absolute URL of another origin fails)")
            else:
                show(o, "", url)


def worker_scripts(root: Path, dist: Path, workers: list, cross: list[str]) -> list[str]:
    """Read every script started in a worker strictly (js_scan strict): the harness reads only the
    page's and its frames' Resource Timing, never a worker's, so a worker script's cross-origin URLs
    fail here, and so does a worker script this check cannot find (a URL built at run time, a
    blob: worker, a missing file). A relative URL resolves against the page (or, for new URL(x,
    import.meta.url) and importScripts(), the calling script), or else the site root. Returns the
    files read."""
    done: list[str] = []
    queue = list(workers)
    while queue:
        where, line, what, url, base = queue.pop(0)
        u = url.strip(URL_STRIP)
        so = same_origin(u)
        if PLACEHOLDER in u or so is not True or u.lower().startswith(("data:", "blob:", "javascript:")):
            cross.append(f"{where}:{line}: {what} starts {shown_url(u) or '(empty)'}, a worker script this check cannot read "
                         "(a worker's loads are in its own network log, which the harness cannot read either)")
            continue
        path = re.split(r"[?#]", u.replace("\\", "/"), maxsplit=1)[0]
        here = PurePosixPath("/" + where.split(":")[0].removeprefix(rel(root, dist)).lstrip("/"))
        cands = []
        if path.startswith("/"):
            cands.append(path)
        else:
            cands += [str(PurePosixPath(here.parent, path)), "/" + path]
        found = None
        for c in cands:
            norm = os.path.normpath(c).lstrip("/")
            f = dist / norm
            if f.is_file() and dist.resolve() in f.resolve().parents:
                found = f
                break
        if found is None:
            cross.append(f"{where}:{line}: {what} starts {shown_url(u)}, which is not a file in dist/ (tried "
                         f"{', '.join(cands)}): a worker script this check cannot read")
            continue
        name = rel(root, found)
        if name in done:
            continue
        done.append(name)
        more: list = []
        js_scan(found.read_text(encoding="utf-8", errors="replace"), name, 1, cross, [], "", None, more, strict=True)
        queue += more
    return done


def manifest_urls(data) -> list[str]:
    """Icon and screenshot URLs of a web app manifest, which the browser fetches."""
    if not isinstance(data, dict):
        return []
    items = [*(data.get("icons") or []), *(data.get("screenshots") or [])]
    for sc in data.get("shortcuts") or []:
        if isinstance(sc, dict):
            items += sc.get("icons") or []
    return [i["src"] for i in items if isinstance(i, dict) and isinstance(i.get("src"), str)]


def criterion_15(ctx: Context) -> Result:
    r = Result(15, "Performance (static parts; run-time loads and layout shift are the harness's)")
    pages = ctx.dist_pages()
    if not pages:
        r.not_yet("no HTML in dist/ (npm run build writes it)")
        r.not_yet(f"loads made at run time (scripts, inserted elements) need a browser: {HARNESS_15_LOADS}")
        r.not_yet(f"layout shift and landing position need a browser: {HARNESS[15]}")
        return r
    root, dist = ctx.root, ctx.dist
    cross, femto_abs, blocking, heads, shown = [], 0, [], 0, []
    workers: list = []  # (where, line, what, url, base): scripts started in a worker, read strictly below
    JS_UNPARSED.clear()
    # Every piece of JavaScript of the site, first, so that a use of an HTML sink or a worker API the
    # check cannot follow, in any of them, changes how all of them are read: (text, where, line,
    # label, javascript: URL).
    sources: list[tuple[str, str, int, str, bool]] = []
    for p in pages:
        doc = ctx.page(p)
        where = rel(root, p)
        for n in doc.iter():
            if n.tag == "#document":
                continue
            for a, v in n.attrs.items():
                if a.startswith("on") and v.strip():
                    sources.append((v, where, n.line, f"<{n.tag} {a}> ", False))
                elif a in ("href", "src", "action", "formaction", "data") and \
                        re.sub(r"[\t\n\r]", "", v.strip(URL_STRIP)).lower().startswith("javascript:"):
                    # A javascript: URL runs its percent-decoded text; a string result becomes the
                    # frame's (or, on a click, the page's) document.
                    body = unquote(re.sub(r"[\t\n\r]", "", v.strip(URL_STRIP)).split(":", 1)[1])
                    sources.append((body, where, n.line, f"<{n.tag} {a}=\"javascript:\"> ", True))
            if n.tag == "script" and script_kind(n) in ("classic", "module") and \
                    not any(a in n.attrs for a in ("src", "href", "xlink:href")):
                sources.append((n.text(), where, n.line, "", False))
    for p in files_under(dist, (".js", ".mjs")):
        sources.append((p.read_text(encoding="utf-8", errors="replace"), rel(root, p), 1, "", False))
    sink_alias, worker_alias = [], []
    for text, where, line0, label, _ in sources:
        toks = js_tokens(text)
        sink_alias += [f"{where}:{line0 + line_of(text, o) - 1}: {label}{v}" for o, v in html_sink_aliases(toks)]
        worker_alias += [f"{where}:{line0 + line_of(text, o) - 1}: {label}{v}" for o, v in worker_aliases(toks)]
    markup_why = (f"{sink_alias[0]} uses an HTML sink in a form this check cannot follow" if sink_alias else None)
    for text, where, line0, label, jsurl in sources:
        js_scan(text, where, line0, cross, shown, label, blocking, workers,
                markup=markup_why or ("a javascript: URL's string result is a document" if jsurl else None))
    for p in pages:
        doc = ctx.page(p)
        where = rel(root, p)
        head = next(iter(doc.find_all("head")), None)
        inline_head = 0
        for n in doc.iter():
            if n.tag == "#document":
                continue
            if "blocking" in n.attrs and "render" in n.attrs["blocking"].lower().split():
                blocking.append(f"{where}:{n.line}: <{n.tag} blocking=\"render\"> (render-blocking; Decision 12 rules "
                                "blocking=\"render\" out)")
            if n.tag != "script":
                continue
            kind = script_kind(n)
            src = next((n.attrs[a] for a in ("src", "href", "xlink:href") if a in n.attrs), None)  # SVG's <script href>
            if kind != "classic" or inert(n):
                continue
            if src is not None:
                if "async" not in n.attrs and "defer" not in n.attrs:
                    blocking.append(f"{where}:{n.line}: <script src={src!r}> without async or defer")
            elif head is not None and head in n.ancestors():
                inline_head += 1
            else:
                blocking.append(f"{where}:{n.line}: an inline classic script outside <head>")
        if inline_head > 1:
            blocking.append(f"{where}: {inline_head} inline classic scripts in <head>, expected one (the inline head script)")
        heads += inline_head == 1
        for line, url, what in markup_urls(doc):
            so = same_origin(url)
            if so is False:
                cross.append(f"{where}:{line}: {what} {url.strip()[:100]}"
                             + (" (every relative URL on the page resolves against it)" if what == "<base href>" else ""))
            elif so is None:
                femto_abs += 1
    for p in files_under(dist, (".css",)):
        code, _, _ = scan_css(p.read_text(encoding="utf-8", errors="replace"))
        for o, url in css_urls(code):
            if same_origin(url) is False:
                cross.append(f"{rel(root, p)}:{line_of(code, o)}: {url[:100]}")
    for p in files_under(dist, (".webmanifest", ".json")):
        if p.suffix.lower() == ".json" and p.name.lower() != "manifest.json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            r.fail(f"{rel(root, p)}: not valid JSON, so its icon URLs cannot be read")
            continue
        cross += [f"{rel(root, p)}: icon {u[:100]}" for u in manifest_urls(data) if same_origin(u) is False]
    worker_files = worker_scripts(root, dist, workers, cross)
    if worker_alias:
        # A worker or worklet started in a form the check cannot follow: any script may run in it, so
        # every script is read as a worker script.
        why = f"a script of a site whose worker use the check cannot follow ({worker_alias[0]})"
        for text, where, line0, label, _ in sources:
            js_scan(text, where, line0, cross, [], label, None, None, strict=why)
        worker_files = list(dict.fromkeys(worker_files + [w for _, w, _, _, _ in sources]))
    cross = list(dict.fromkeys(cross))  # a worker script is also read as a dist script
    shown = [x for x in shown if x.split(":")[0] not in worker_files]  # judged strictly instead
    r.fails(f"{len(cross)} cross-origin resource(s) in markup, CSS, manifests, JS imports, HTML that JS writes or worker "
            "scripts:", cross, "more")
    if JS_UNPARSED:
        r.fails(f"{len(JS_UNPARSED)} script(s) that espree (ESLint's parser, ecmaVersion latest) cannot read, so their "
                "regular expressions and divisions are only told apart by a heuristic (Decision 12's JavaScript parses):",
                [f"{why}: {head}" for head, why in JS_UNPARSED.items()], "more")
    if worker_files:
        r.note(f"{len(worker_files)} worker script(s) read strictly (a worker's loads are not in the page's Resource Timing): "
               + ", ".join(worker_files[:MAX_LINES]))
    if worker_alias:
        r.note(f"{len(worker_alias)} use(s) of a worker API in a form the check cannot follow, so every script was read as "
               "a worker script: " + "; ".join(worker_alias[:4]))
    if sink_alias:
        r.note(f"{len(sink_alias)} use(s) of an HTML sink in a form the check cannot follow, so every string that holds "
               "markup was read as HTML written into the page: " + "; ".join(sink_alias[:4]))
    if not cross:
        r.ok(f"{len(pages)} pages: no cross-origin resource in their markup, CSS or manifest, and no cross-origin import, "
             "worker script or element in HTML their JS hands to the parser (document.write, innerHTML and the other "
             "sinks, javascript: URLs" + (", every string that holds markup" if sink_alias else "") + ")")
    if shown:
        r.note(f"{len(shown)} absolute URL(s) in JavaScript strings, listed for review and not judged here: a string may be a "
               "fetch(), an inserted element or text a script only displays; whether one loads is the harness's "
               "network log (" + HARNESS_15_LOADS + "):")
        for line in shown[:MAX_LINES]:
            r.note("  " + line)
        if len(shown) > MAX_LINES:
            r.note(f"  ... {len(shown) - MAX_LINES} more")
    if femto_abs:
        r.note(f"{femto_abs} resource URLs are absolute https://femto.style/ URLs (same origin once deployed, not under wrangler)")
    r.fails(f"{len(blocking)} render-blocking script(s) besides the inline head script:", blocking, "more")
    if not blocking:
        r.ok(f"the only render-blocking script is the inline head script ({heads} of {len(pages)} pages have one)")

    docs = dist / "docs.html"
    limits = budget(root / "PLAN.md")
    if not limits:
        r.not_yet("PLAN.md's Risks section records no /docs HTML budget yet (Phase 3 measures and records it)")
    elif not docs.is_file():
        r.fail("dist/docs.html is missing")
    else:
        data = docs.read_bytes()
        for limit, kind, sentence in limits:
            size = compressed_size(data, kind)
            line = f"dist/docs.html is {size:,} bytes {kind}, budget {int(limit):,} ({sentence[:90]})"
            (r.ok if size <= limit else r.fail)(line)
    r.not_yet(f"loads made at run time (scripts, inserted elements) need a browser: {HARNESS_15_LOADS}")
    r.not_yet(f"layout shift and landing position need a browser: {HARNESS[15]}")
    return r


# ---------------------------------------------------------------------------- main


CHECKS = {1: criterion_1, 2: criterion_2, 3: criterion_3, 4: criterion_4, 5: criterion_5, 6: criterion_6,
          7: criterion_7, 8: criterion_8, 9: criterion_9, 10: criterion_10, 11: criterion_11, 12: criterion_12,
          13: criterion_13, 14: criterion_14, 15: criterion_15}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="static_checks.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--criteria", help="comma-separated criterion numbers, 1 to 15 (default: all)")
    parser.add_argument("--json", metavar="FILE", help="also write the results to FILE as JSON")
    parser.add_argument("--strict", action="store_true", help="count NOT-YET as a failure")
    parser.add_argument("--phase", type=int, choices=range(0, 7), help="check as of this phase (default: inferred)")
    parser.add_argument("--femto", metavar="DIR", help="femto checkout for criteria 12 and 13")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]), help="repository root")
    try:  # argparse exits on --help and usage errors; return its code instead, for run.py
        args = parser.parse_args(argv)
        try:
            ids = sorted({int(x) for x in args.criteria.split(",") if x.strip()}) if args.criteria else sorted(CHECKS)
        except ValueError:
            parser.error(f"--criteria takes numbers: {args.criteria!r}")
        unknown = [i for i in ids if i not in CHECKS]
        if unknown:
            parser.error(f"unknown criteria: {unknown}")
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    root = Path(args.root).resolve()
    phase, why = (args.phase, "--phase") if args.phase is not None else infer_phase(root)
    ctx = Context(root, phase, why, args.femto)
    print(f"femto.style static checks: {root}, phase {phase} ({why})")
    results = []
    for i in ids:
        try:
            res = CHECKS[i](ctx)
        except Exception as exc:  # a crashed check is a failed check
            res = Result(i, f"Criterion {i}")
            res.fail(f"check crashed: {type(exc).__name__}: {exc}")
        results.append(res)
        res.print()
    counts = {s: sum(1 for x in results if x.state == s) for s in ("pass", "fail", "not-yet")}
    print(f"\nSUMMARY: {counts['pass']} PASS, {counts['fail']} FAIL, {counts['not-yet']} NOT-YET")
    if args.json:
        out = {"root": str(root), "phase": phase, "phase_source": why, "strict": args.strict,
               "summary": counts, "criteria": [x.as_dict() for x in results]}
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return 1 if counts["fail"] or (args.strict and counts["not-yet"]) else 0


if __name__ == "__main__":
    sys.exit(main())
