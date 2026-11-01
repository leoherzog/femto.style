"""`run.py selftest`: controls that prove the pages mode detects what it must and tolerates what it may.

Each control runs `run.py pages --a fixture --b fixture:<control>` in a subprocess exactly as a user
would: side A is the selftest site in tests/fixtures/site/, side B the same site with one named change
from tests/fixtures/controls.json, each served by its own harness server. The check then reads the
run's result.json. Ported from femto's negative.py; the controls are new.
"""
import json
import re
import subprocess
import sys
import time

from .paths import DIVERGENCES, RESULTS, TESTS
from .report import fmt_rec as fmt

WIDTHS = "375,600,800,1100,1300,1600"
ALL_LEGS = "light,dark,theme-light,theme-dark"


def _records(result, kinds=None):
    for c in result["cells"]:
        for r in (c.get("result") or {}).get("unregistered", []):
            if kinds is None or r["kind"] in kinds:
                yield c, r


def _diff_cells(result):
    return [c for c in result["cells"] if (c.get("result") or {}).get("unregisteredTotal")]


def _summary_kinds(result):
    return sorted({r["kind"] for _, r in _records(result)})


def _for_browser(r, browser):
    """The result restricted to one browser's cells, so each control is judged per browser."""
    cells = [c for c in r["cells"] if c["browser"] == browser]
    registered = {}
    for c in cells:
        for k, n in ((c.get("result") or {}).get("registered") or {}).items():
            registered[k] = registered.get(k, 0) + n
    names = {f"{c['browser']} {c['route']} {c['scheme']} {c['width']}" for c in cells}
    cross = [x for x in r.get("cross_origin_loads") or [] if x["cell"] in names]
    return dict(r, cells=cells, cross_origin_loads=cross,
                totals=dict(r["totals"], differences=sum((c.get("result") or {}).get("total", 0) for c in cells),
                            unregistered=sum((c.get("result") or {}).get("unregisteredTotal", 0) for c in cells),
                            cross_origin_loads=len(cross)),
                harness_errors=[e for e in r["harness_errors"] if e.startswith(browser + " ") or not e.split(" ")[0] in
                                ("chrome", "firefox", "safari")],
                skipped_checks=[x for x in r["skipped_checks"] if x["browser"] == browser],
                registered_by_entry=registered)


def build_cases(reg_dir):
    cases = []
    # Every control runs against a registry of its own, never the live tests/divergences/: the phase
    # agents' entries there (and their validity, which follows dist/ as it is built) must not decide
    # whether detection is proved. A control without one gets the rig's seed (rig.json, the Safari
    # media skip) and nothing else.
    base_dir = reg_dir.parent / "registry-base"
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "rig.json").write_text((DIVERGENCES / "rig.json").read_text())

    def case(name, control, check, describe, routes="/index.html", widths="1300", schemes="light", extra=(),
             registry_errors=False, expect_errors=()):
        # registry_errors: the control expects registry errors (harness errors starting "registry: "),
        # and its check judges them; expect_errors: substrings of the cell harness errors it expects
        # (the in-page "breadth: " and "coverage: " guards). Any other harness error still fails it.
        if "--registry" not in extra:
            extra = (*extra, "--registry", str(base_dir))
        argv = ["pages", "--a", "fixture", "--b", f"fixture:{control}" if control else "fixture",
                "--routes", routes, "--widths", widths, "--schemes", schemes, *extra]
        cases.append({"name": name, "argv": argv, "check": check, "describe": describe,
                      "registry_errors": registry_errors, "expect_errors": tuple(expect_errors)})

    def zero(r):
        n = r["totals"]["differences"]
        x = r["totals"].get("cross_origin_loads")
        return (n == 0 and not r["harness_errors"] and x == 0,
                f"{n} differences, {len(r['harness_errors'])} errors, {x} cross-origin loads")

    case("self", None, zero, "the fixture site against itself (two servers), every leg, two widths: zero differences "
         "(the masks hide its random typing demo and progress value)",
         routes="/index.html,/other.html", widths="375,1300", schemes=ALL_LEGS)

    def color2(r):
        recs = [x for _, x in _records(r)]
        h1 = [x for x in recs if x["kind"] == "style" and x["label"].startswith("h1") and x["prop"] == "color"]
        outside = [x for x in recs if not x["path"].startswith("html > body:0 > main:1 > h1:0")]
        kinds = _summary_kinds(r)
        return (bool(h1) and not outside and kinds == ["style"],
                f"h1 color records {len(h1)}, records outside h1 {len(outside)}, kinds {kinds}, total {r['totals']['unregistered']}")
    case("color-2-of-255", "color-2-of-255", color2, "h1 color rgb(45, 49, 56) to rgb(47, 49, 56) is detected, on the h1 only")
    case("color-1-of-255", "color-1-of-255", zero, "h1 color rgb(45, 49, 56) to rgb(46, 49, 56) (1/255) is tolerated: zero differences")

    def attribute(r):
        recs = [x for _, x in _records(r)]
        ok = [x for x in recs if x["kind"] == "attribute" and x["prop"] == "title" and x["a"] == "lead paragraph" and x["b"] == "lead para"]
        return (len(ok) > 0 and len(ok) == len(recs), f"title records {len(ok)} of {len(recs)}, kinds {_summary_kinds(r)}")
    case("attribute", "attribute", attribute, "a changed attribute is one attribute record and nothing else")

    def structure(change, tag_a, tag_b):
        def chk(r):
            recs = [x for _, x in _records(r)]
            st = [x for x in recs if x["kind"] == "structure"]
            want = [x for x in st if x.get("change") == change and x["a"] == tag_a and x["b"] == tag_b]
            per_cell = {len([x for x in (c.get("result") or {}).get("unregistered", []) if x["kind"] == "structure"])
                        for c in r["cells"]}
            others = sorted({x["kind"] for x in recs} - {"structure"})
            return (bool(want) and per_cell == {1} and len(want) == len(st),
                    f"structure records per cell {sorted(per_cell)}: {[(x['change'], x['a'], x['b'], x['path']) for x in st[:1]]}; "
                    f"other kinds {others}")
        return chk
    case("added-element", "added-element", structure("only-b", None, "li"),
         "an element only on side B is one structure record (only-b) at its path")
    case("removed-element", "removed-element", structure("only-a", "li", None),
         "an element only on side A is one structure record (only-a) at its path")

    def changed_tag(r):
        ok, msg = structure("tag", "b", "strong")(r)
        kinds = _summary_kinds(r)
        return ok and kinds == ["structure"], msg + f"; kinds {kinds}"
    case("changed-tag", "changed-tag", changed_tag,
         "<b> to <strong> (both bold, same text) is one structure record (tag) and nothing else")

    def changed_tag_content(r):
        recs = [x for _, x in _records(r)]
        st = [x for x in recs if x["kind"] == "structure"]
        tx = [x for x in recs if x["kind"] == "text"]
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        ok = (bool(st) and all(x.get("change") == "tag" and x["a"] == "b" and x["b"] == "strong" for x in st)
              and bool(tx) and all(x["a"] == "fixture" and x["b"] == "fixtures" for x in tx)
              and per_cell == {2} and _summary_kinds(r) == ["structure", "text"])
        return ok, f"records per cell {sorted(per_cell)}, structure {len(st)}, text {[(x['a'], x['b']) for x in tx[:1]]}, kinds {_summary_kinds(r)}"
    case("changed-tag-content", "changed-tag-content", changed_tag_content,
         "<b>fixture</b> to <strong>fixtures</strong>: the tag record, and the changed word below it is still compared")

    def inserted(tag, label):
        # One only-b record naming the inserted element; its later siblings pair with their true
        # counterparts, so the only other records are the taller ancestors' styles.
        ancestors = {"html", "html > body:0", "html > body:0 > main:1"}

        def chk(r):
            recs = [x for _, x in _records(r)]
            st = [x for x in recs if x["kind"] == "structure"]
            per_cell = {len([x for x in (c.get("result") or {}).get("unregistered", []) if x["kind"] == "structure"])
                        for c in r["cells"]}
            want = [x for x in st if x.get("change") == "only-b" and x["b"] == tag and x["label"].startswith(label)]
            other = [x for x in recs if x["kind"] != "structure"]
            stray = [x for x in other if x["kind"] != "style" or x["path"] not in ancestors]
            return (per_cell == {1} and len(want) == len(st) and not stray,
                    f"structure records per cell {sorted(per_cell)}: {[(x['change'], x['label'], x['path']) for x in st[:1]]}; "
                    f"{len(other)} other records, {len(stray)} outside the ancestors' styles: {[fmt(x) for x in stray[:3]]}")
        return chk
    case("inserted-early", "inserted-early", inserted("p", "p.inserted"),
         "a paragraph inserted first in <main> is one only-b record naming it; the h1 and everything after still pair")
    case("inserted-same-tag", "inserted-same-tag", inserted("section", "section.extra"),
         "a section inserted before two sections is one only-b record naming it (same-tag neighbours still pair)")

    def pseudo_content(r):
        recs = [x for _, x in _records(r)]
        ps = sorted({x.get("pseudo") for x in recs if x["kind"] == "style"})
        content = [x for x in recs if x.get("pseudo") == "::before" and x["prop"] == "content"]
        return ps == ["::before"] and bool(content) and _summary_kinds(r) == ["style"], \
            f"pseudo-elements with diffs {ps}, content records {len(content)}, kinds {_summary_kinds(r)}"
    case("pseudo-content", "pseudo-content", pseudo_content, "a ::before content change is detected on ::before content")

    def widths_only(want):
        def chk(r):
            ws = sorted({c["width"] for c in _diff_cells(r)})
            ran = sorted({c["width"] for c in r["cells"]})
            return ws == want, f"widths with diffs {ws} of {ran}"
        return chk
    case("width-only", "width-only", widths_only([800]), "a rule for 790 to 810px differs at width 800 only, of the six widths",
         widths=WIDTHS)

    def dark_only(r):
        legs = sorted({c["scheme"] for c in _diff_cells(r)})
        if legs == ["dark"]:
            return True, f"legs with diffs {legs}"
        # Safari cannot run the media-dark leg on a light OS: then nothing may differ and the leg must be a registered skip.
        dark = [c for c in r["cells"] if c["scheme"] == "dark"]
        skipped = bool(dark) and all(c.get("status") == "skipped" for c in dark) and all(s["entries"] for s in r["skipped_checks"])
        return (not legs and skipped), f"legs with diffs {legs}; media-dark cells skipped and registered: {skipped}"
    case("dark-only", "dark-only", dark_only, "a rule under prefers-color-scheme: dark (no data-theme) differs only in leg dark",
         schemes=ALL_LEGS)

    def theme_dark_only(r):
        legs = sorted({c["scheme"] for c in _diff_cells(r)})
        return legs == ["theme-dark"], f"legs with diffs {legs}"
    case("theme-dark-only", "theme-dark-only", theme_dark_only,
         "a rule under html[data-theme=dark] differs only in leg theme-dark (data-theme from the stored femtoColorScheme)",
         schemes=ALL_LEGS)

    def text(r):
        recs = [x for _, x in _records(r)]
        t = [x for x in recs if x["kind"] == "text" and x["label"].startswith("p.lead")]
        return bool(t) and _summary_kinds(r) == ["text"], f"text records {len(t)}, kinds {_summary_kinds(r)}"
    case("text", "text", text, "a changed word is a text record on its element")

    def whitespace(r):
        recs = [x for _, x in _records(r)]
        t = [x for x in recs if x["kind"] == "text" and x["label"].startswith("p.lead")
             and x["a"] == "Lead text with ." and x["b"] == "Lead text with  ."]
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        return (bool(t) and len(t) == len(recs) and per_cell == {1},
                f"p.lead space records {len(t)} of {len(recs)}, records per cell {sorted(per_cell)}, kinds {_summary_kinds(r)}")
    case("whitespace", "whitespace", whitespace,
         "a space that renders between two inline boxes (after the lead paragraph's link) is one text record on its "
         "element, and nothing else", widths="375,1300")
    case("whitespace-collapsed", "whitespace-collapsed", zero,
         "source whitespace that renders nothing (between list items, and a space before <b> widened to a newline "
         "and indentation) gives zero differences", widths="375,1300")

    def whitespace_nbsp(r):
        recs = [x for _, x in _records(r)]
        t = [x for x in recs if x["kind"] == "text" and x["label"].startswith("p.lead")
             and x["a"] == "Lead text with ." and x["b"] == "Lead\u00a0 text with\u00a0\u00a0."]
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        return (bool(t) and len(t) == len(recs) and per_cell == {1},
                f"p.lead no-break space records {len(t)} of {len(recs)}, records per cell {sorted(per_cell)}, "
                f"kinds {_summary_kinds(r)}, b {[x['b'] for x in recs if x['kind'] == 'text'][:1]!r}")
    case("whitespace-nbsp", "whitespace-nbsp", whitespace_nbsp,
         "no-break spaces, which CSS never collapses, are text: '&nbsp; ' for the space after 'Lead' and two &nbsp; "
         "before the link are one text record on p.lead (side B 'Lead\\u00a0 text with\\u00a0\\u00a0.'), and nothing else",
         widths="375,1300")

    def pseudo_all(r):
        want = ["::after", "::backdrop", "::file-selector-button", "::marker", "::placeholder"]
        ps = sorted({x.get("pseudo") for _, x in _records(r, {"style"})})
        return ps == want, f"pseudo-elements with diffs {ps}"
    case("pseudo-elements", "pseudo-elements", pseudo_all,
         "changes on ::marker, ::placeholder, ::file-selector-button, ::backdrop and ::after are detected on each")

    case("masked-only", "masked-only", zero,
         "changes inside the masked areas only (the typing demo's content, the progress value and its code token) "
         "give zero differences")

    def progress_token(r):
        recs = [x for _, x in _records(r)]
        tx = [x for x in recs if x["kind"] == "text" and x["a"] == "100" and x["b"] == "200"]
        paths = {x["path"] for x in recs}
        return (bool(tx) and len(paths) == 1 and set(_summary_kinds(r)) <= {"text", "style"},
                f"text 100 -> 200 records {len(tx)}, paths with records {sorted(paths)[:3]}, kinds {_summary_kinds(r)}")
    case("progress-code-token", "progress-code-token", progress_token,
         "a token of the progress code outside the value mask (max 100 to 200) is detected, on that token only")

    def head(r):
        recs = [x for _, x in _records(r)]
        got = sorted({(x["path"], x["prop"]) for x in recs})
        want = [("link[rel=canonical]", "href"), ("meta[name=description]", "content"), ("title", "text")]
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        return (got == want and per_cell == {3} and _summary_kinds(r) == ["head"],
                f"head records {got}, per cell {sorted(per_cell)}, kinds {_summary_kinds(r)}")
    case("head", "head", head,
         "a changed title, meta description and canonical link are three head records and nothing else")

    def head_data(r):
        recs = [x for _, x in _records(r)]
        got = sorted({(x["path"], x["prop"], x["a"], x["b"]) for x in recs})
        want = [("base", "target", None, "_top"),
                ("script[type=application/ld+json]", "$.url", '"https://fixture.test/"', '"https://fixture.test/other"'),
                ("script[type=application/ld+json]", "$.version", '"1.0.0"', '"1.0.1"')]
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        return (got == want and per_cell == {3} and _summary_kinds(r) == ["head"],
                f"head records {[g[:2] for g in got]}, per cell {sorted(per_cell)}, kinds {_summary_kinds(r)}")
    case("head-data", "head-data", head_data,
         "a JSON-LD data block re-indented with its keys reordered and two values changed, and an added <base target>, "
         "are three head records ($.url, $.version, base target) and nothing else")

    def head_data_copy(r):
        ok0, msg = zero(r)
        reps = {s: sorted({(c.get("sides") or {}).get(s, {}).get("head_repeats") for c in r["cells"]}, key=str)
                for s in ("a", "b")}
        entries = {(c["sides"]["a"].get("head_entries"), c["sides"]["b"].get("head_entries")) for c in r["cells"]}
        ok = ok0 and reps == {"a": [0], "b": [1]} and all(x == y for x, y in entries)
        return ok, f"{msg}; head_repeats per side {reps}; head entries (A, B) {sorted(entries)}"
    case("head-data-copy", "head-data-copy", head_data_copy,
         "an exact copy of the JSON-LD block (re-indented, keys reordered, same leaves) is counted once: zero "
         "differences, and side B's head_repeats is 1 (the oracle's /docs/progress has one or two copies)")

    def head_data_near_copy(r):
        recs = [x for _, x in _records(r)]
        paths = sorted({x["path"] for x in recs})
        one_sided = all(x["a"] is None and x["b"] is not None for x in recs)
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        version = [x for x in recs if x["prop"] == "$.version" and x["b"] == '"1.0.1"']
        return (paths == ["script[type=application/ld+json]#2"] and one_sided and per_cell == {9} and bool(version)
                and _summary_kinds(r) == ["head"],
                f"paths {paths}, one-sided {one_sided}, per cell {sorted(per_cell)}, $.version records {len(version)}, "
                f"kinds {_summary_kinds(r)}")
    case("head-data-near-copy", "head-data-near-copy", head_data_near_copy,
         "a second JSON-LD block that differs in one leaf is not a copy: its own #2 entry, one head record per leaf "
         "(9) on side B only")

    def cross_origin(r):
        x = r.get("cross_origin_loads") or []
        n = r["totals"]["differences"]
        ok_urls = all(i["side"] == "b" and re.fullmatch(r"http://localhost:\d+/fixture\.css", i["url"]) for i in x)
        return (len(x) == len(r["cells"]) and ok_urls and n == 0 and r["status"] == "FAIL",
                f"cross-origin loads {[(i['side'], i['url']) for i in x[:1]]} in {len(x)} of {len(r['cells'])} cells, "
                f"{n} differences, run {r['status']}")
    case("cross-origin", "cross-origin", cross_origin,
         "a stylesheet a script loads from another origin (a URL built at run time, no URL literal) fails the run as one "
         "cross-origin load per cell (criterion 15) with zero differences")

    def cross_origin_frame(r):
        x = r.get("cross_origin_loads") or []
        recs = [y for _, y in _records(r)]
        ok_urls = all(i["side"] == "b" and re.fullmatch(r"http://localhost:\d+/fixture\.css", i["url"]) for i in x)
        frames = sorted({(c.get("sides") or {}).get("b", {}).get("frames_read") for c in r["cells"]}, key=str)
        only_frame = all(y["kind"] == "structure" and y.get("change") == "only-b" and y["b"] == "iframe" for y in recs)
        per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
        return (len(x) == len(r["cells"]) and ok_urls and only_frame and per_cell == {1} and frames == [1]
                and r["status"] == "FAIL",
                f"cross-origin loads {[(i['side'], i['url']) for i in x[:1]]} in {len(x)} of {len(r['cells'])} cells, "
                f"side B frames read {frames}, records per cell {sorted(per_cell)} {[fmt(y) for y in recs[:1]]}, "
                f"run {r['status']}")
    case("cross-origin-frame", "cross-origin-frame", cross_origin_frame,
         "a stylesheet that a script in a hidden same-origin iframe (srcdoc) loads from another origin is found in the "
         "frame's own Resource Timing: one cross-origin load per cell, and the iframe's only-b record")

    def csp_only(want_records):
        # A load only the proxy's CSP report shows (no frame or worker the page can read): it is a
        # cross-origin load of side B in every cell, and the run fails.
        def chk(r):
            x = r.get("cross_origin_loads") or []
            recs = [y for _, y in _records(r)]
            ok_urls = all(i["side"] == "b" and re.fullmatch(r"http://localhost:\d+/fixture\.css", i["url"])
                          and "CSP report" in (i.get("via") or "") for i in x)
            ok_recs = want_records(recs)
            return (len(x) == len(r["cells"]) and ok_urls and ok_recs and r["status"] == "FAIL",
                    f"cross-origin loads {[(i['side'], i['url'], (i.get('via') or '')[:40]) for i in x[:1]]} in {len(x)} "
                    f"of {len(r['cells'])} cells, records {[fmt(y) for y in recs[:2]]}, run {r['status']}")
        return chk
    case("cross-origin-worker", "cross-origin-worker", csp_only(lambda recs: not recs),
         "a fetch() from a dedicated worker to another origin (a URL built at run time) is in no page's Resource "
         "Timing; the proxy's CSP report shows it: one cross-origin load per cell, zero differences")
    case("cross-origin-closed-shadow", "cross-origin-closed-shadow",
         csp_only(lambda recs: len(recs) == 1 and recs[0]["kind"] == "structure" and recs[0].get("change") == "only-b"
                  and recs[0]["label"].startswith("div.closed-host")),
         "a stylesheet that a frame inside a closed shadow root loads from another origin (the page cannot reach that "
         "frame) is shown by the proxy's CSP report: one cross-origin load per cell, and the host's only-b record")

    def status(r):
        st = [x for _, x in _records(r, {"status"})]
        return (bool(st) and all(x["a"].startswith("200 ") and x["b"].startswith("404 ") for x in st),
                f"status records {[(x['a'], x['b']) for x in st[:1]]}, kinds {_summary_kinds(r)}")
    case("status-404", "status-404", status, "a route that answers 404 on side B is a status record",
         routes="/other.html")

    def suppression(r):
        recs = [x for _, x in _records(r)]
        h1 = [x for x in recs if x["path"].startswith("html > body:0 > main:1 > h1:0")]
        attr = [x for x in recs if x["kind"] == "attribute"]
        used = r["registered_by_entry"]
        ok = not h1 and bool(attr) and used.get("neg-h1-color", 0) > 0 and set(_summary_kinds(r)) == {"attribute"}
        return ok, f"unregistered h1 {len(h1)}, attribute {len(attr)}; registered {used}"
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "negative.json").write_text(json.dumps([
        {"id": "neg-h1-color", "kind": "style", "selector": "h1, h1 *", "property": "*", "category": "oracle-bug",
         "reason": "Negative control: suppress exactly the h1 color change."},
    ], indent=1))
    case("registry-suppression", "color-and-attribute", suppression,
         "an entry for the h1 color absorbs the h1 records and nothing else (the attribute change stays unregistered)",
         extra=("--registry", str(reg_dir)))

    # DET-5: entries that would match every record of their kind, however they are written, are
    # rejected by what they would actually match on the reference documents, and a rejected entry
    # registers nothing. The first nine are the review's (adv-detection, adv-verify-r1); the rest
    # are the next evasions in line: a scope only side B satisfies, a scope only the theme legs
    # satisfy, a selector concentrated on one route, and a catch-all split into twelve entries that
    # are each under the limits.
    def x(i, kind, reason="DET-5 evasion control", **f):
        return {"id": i, "kind": kind, **f, "category": "browser-limit" if kind == "skipped-check" else "merge-layout",
                "reason": reason}
    evasions = [
        x("evade-literal", "style", selector="*", property="*"),
        x("evade-dot", "text", path="/./"),
        x("evade-text", "text", path="/^html/"),
        x("evade-style", "style", selector=":not(#zz)", property="/^(?!Z9$)/"),
        x("evade-attr", "attribute", selector="html, html *", property="/^[a-z]/"),
        x("evade-structure", "structure", path="/^html/"),
        x("evade-head", "head", path="/^[a-z]/", property="*"),
        x("evade-routes", "text", selector="*", where={"routes": ["/^\\/(?!does-not-exist)/"]}),
        x("evade-skip", "skipped-check", check="*"),
        x("evade-b-only", "style", selector=":root:has([title=\"lead para\"]) *", property="*"),
        x("evade-theme", "text", selector="[data-theme] *"),
        x("evade-one-route", "attribute", selector=":root:has(a[download]) body *", property="*"),
    ] + [x(f"evade-split-{k}", "text", selector=f"span:nth-child(12n+{k})") for k in range(1, 13)]
    # Round 3 (DET5-R2): "*" as a route, a scope of routes with no reference document, and a catch-all
    # split by route into entries of three routes each, which together cover every known route.
    from .registry import ROUTE_SCOPE_MAX, _known_routes
    known = _known_routes()
    evasions += [
        x("evade-star-route", "style", selector="*", property="*", where={"routes": ["*"]}),
        x("evade-star-head", "head", path="*", property="*", where={"routes": ["*"]}),
        x("evade-uncaptured", "style", selector="*", property="*", where={"routes": ["/^\\/docs\\/v1\\/./"]}),
    ] + [x(f"evade-route-split-{k}", "style", selector="*", property="*",
           where={"routes": known[k:k + ROUTE_SCOPE_MAX]}) for k in range(0, len(known), ROUTE_SCOPE_MAX)]
    # Round 4 (adv-verify-p0r4): patterns Python's re and JavaScript's RegExp read differently (\Z
    # and \A are anchors in Python and the letters Z and A in JavaScript; {,1} is a quantifier in
    # Python 3.13 and literal text in JavaScript), which the registry now judges with JavaScript, the
    # engine differ.js applies them with; and the uncaptured v1 routes split three to an entry.
    v1 = [r for r in known if r.startswith("/docs/v1/")]
    evasions += [
        x("evade-dialect-z", "style", path="/^(?!.*\\Z)/", property="*"),
        x("evade-dialect-a", "text", path="/^(?!\\A)/"),
        x("evade-dialect-brace", "attribute", path="/^html(?!{,1}[ ])/", property="*"),
        x("evade-dialect-head", "head", path="/^(?!.*\\Z)/", property="*"),
    ] + [x(f"evade-uncaptured-split-{k}", "structure", selector="*", where={"routes": v1[k:k + ROUTE_SCOPE_MAX]})
         for k in range(0, len(v1), ROUTE_SCOPE_MAX)]
    ok_entry = x("ok-h1-color", "style", "Positive control: a narrow entry beside the rejected ones still applies.",
                 selector="h1, h1 *", property="color")
    evasion_dir = reg_dir.parent / "registry-evasion"
    evasion_dir.mkdir(parents=True, exist_ok=True)
    (evasion_dir / "evasion.json").write_text(json.dumps(evasions + [ok_entry], indent=1))

    def evasion(r):
        reg_errs = [e for e in r["harness_errors"] if e.startswith("registry: ")]
        other = [e for e in r["harness_errors"] if not e.startswith("registry: ")]
        named = {e["id"]: any(f"[{e['id']}]" in m for m in reg_errs) for e in evasions}
        missed = sorted(i for i, hit in named.items() if not hit)
        used = r["registered_by_entry"]
        leaked = sorted(i for i in used if i != "ok-h1-color" and used[i])
        kinds = _summary_kinds(r)
        ok_flagged = any("[ok-h1-color]" in m for m in reg_errs)
        want = {"attribute", "head", "structure", "style", "text"}
        ok = (not missed and not other and not leaked and not ok_flagged and used.get("ok-h1-color", 0) > 0
              and want <= set(kinds) and r["status"] == "FAIL")
        return ok, (f"{sum(named.values())}/{len(evasions)} evasions rejected (missed {missed}), {len(reg_errs)} registry "
                    f"errors, other harness errors {other[:2]}; registered {used}; unregistered kinds {kinds}; "
                    f"ok-h1-color {'flagged' if ok_flagged else 'valid'}; run {r['status']}")
    case("registry-evasion", "registry-evasion", evasion,
         "every catch-all the review wrote, and the next ones in line (a side-B-only scope, a theme-leg scope, one route "
         "hidden in a selector, a catch-all split in twelve, \"*\" as a route, a scope of uncaptured routes, a catch-all "
         "split by route, path patterns JavaScript reads otherwise than Python, uncaptured routes split three to an "
         "entry), is a registry error, registers nothing, and leaves each record kind unregistered; a narrow entry "
         "beside them still applies",
         extra=("--registry", str(evasion_dir)), registry_errors=True)

    # NF-RUNTIME-DOM: an entry keyed to a class only a script adds reaches nothing in the page
    # source, so the static rule accepts it; on the live document it reaches every element, and the
    # in-page guard (differ.js breadthGuard) takes it out of the cell with a harness error.
    rt_dir = reg_dir.parent / "registry-runtime"
    rt_dir.mkdir(parents=True, exist_ok=True)
    rt_entries = [x("rt-style", "style", selector=".js-added, .js-added *", property="*"),
                  x("rt-text", "text", selector=".js-added, .js-added *"),
                  x("rt-structure", "structure", selector=".js-added, .js-added *"),
                  x("rt-attribute", "attribute", selector=".js-added, .js-added *", property="*")]
    (rt_dir / "runtime.json").write_text(json.dumps(rt_entries, indent=1))

    def runtime(r):
        reg_errs = [e for e in r["harness_errors"] if e.startswith("registry: ")]
        guard = [e for e in r["harness_errors"] if "breadth: registry entry " in e]
        named = sorted(e["id"] for e in rt_entries if any(f"entry {e['id']} matches" in g for g in guard))
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        kinds = _summary_kinds(r)
        want = {"attribute", "structure", "style", "text"}
        return (not reg_errs and len(named) == len(rt_entries) and not used and want <= set(kinds) and r["status"] == "FAIL",
                f"registry errors {len(reg_errs)} (the static rule accepts them: the class is not in the source); "
                f"in-page breadth errors name {named}; registered {used}; unregistered kinds {kinds}; run {r['status']}")
    case("registry-runtime", "runtime-class", runtime,
         "entries keyed to a class a script adds on load (.js-added, .js-added *) reach nothing in the page source but "
         "every element of the live document: the in-page guard reports each, applies none, and every change stays "
         "unregistered",
         extra=("--registry", str(rt_dir)), expect_errors=("breadth: registry entry ",))

    # DET5-R2-3: a page side B does not have cannot pass, however narrow the entries. Here every
    # record of the missing /index.html is registered by entries that are each under every breadth
    # limit (statically and in the page), and the status entry names its one route; the registered
    # records still cover nearly all of side A's document, which the coverage guard reports. The roots
    # leave the head out, so that nothing stays unregistered and only the guard can fail the run.
    mp_dir = reg_dir.parent / "registry-missing-page"
    mp_dir.mkdir(parents=True, exist_ok=True)
    mp_entries = [x("mp-status", "status", path="/index.html", a="200 /index.html", b="404 /index.html"),
                  x("mp-main", "structure", selector="main#content"),
                  x("mp-footer", "structure", selector="footer.site"),
                  x("mp-nav", "structure", selector="header > nav"),
                  x("mp-pre", "structure", selector="pre"),
                  x("mp-pre-text", "text", selector="pre"),
                  x("mp-body", "style", selector="body", property="*")]
    (mp_dir / "missing.json").write_text(json.dumps(mp_entries, indent=1))

    def missing_page(r):
        reg_errs = [e for e in r["harness_errors"] if e.startswith("registry: ")]
        cover = [e for e in r["harness_errors"] if "coverage: " in e]
        breadth = [e for e in r["harness_errors"] if "breadth: " in e]
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        unreg = r["totals"]["unregistered"]
        ok = (not reg_errs and not breadth and bool(cover) and all("side A's document" in e for e in cover)
              and unreg == 0 and used.get("mp-status") and used.get("mp-main") and r["status"] == "FAIL")
        return ok, (f"registry errors {len(reg_errs)}, breadth errors {len(breadth)}, coverage errors "
                    f"{[e[e.find('coverage: '):][:110] for e in cover[:1]]}; unregistered {unreg}; registered {used}; "
                    f"run {r['status']}")
    case("registry-missing-page", "missing-index", missing_page,
         "a page side B does not have (404), every record registered by entries each under the breadth limits: the "
         "registered records cover most of side A's document, so the coverage guard fails the run",
         extra=("--registry", str(mp_dir), "--root-a", "body", "--root-b", "body"), expect_errors=("coverage: ",))

    # DET5-R2-2: with --root-a/--root-b the records carry the document's own tree paths (from html),
    # so a path pattern written for the old "tag{selector}" root form matches nothing.
    root_dir = reg_dir.parent / "registry-root-path"
    root_dir.mkdir(parents=True, exist_ok=True)
    root_entries = [x("root-text", "text", path="/\\{/"), x("root-struct", "structure", path="/\\{/"),
                    x("root-attr", "attribute", path="/\\{/", property="*"),
                    x("root-style", "style", path="/^[a-z]+\\{/", property="*")]
    (root_dir / "root.json").write_text(json.dumps(root_entries, indent=1))

    def root_path(r):
        recs = [y for _, y in _records(r)]
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        paths_ok = all(y["path"].startswith("html > body:0") for y in recs)
        kinds = _summary_kinds(r)
        want = {"attribute", "structure", "style", "text"}
        return (bool(recs) and paths_ok and not used and want <= set(kinds) and "head" not in kinds,
                f"{len(recs)} records, all paths from html > body:0: {paths_ok} (first {recs[0]['path'] if recs else None}); "
                f"registered {used}; unregistered kinds {kinds}")
    case("registry-root-path", "registry-evasion", root_path,
         "with --root-a body --root-b body, records carry the document's own paths from html (html > body:0 > ...), so "
         "entries keyed to the old root form (path /\\{/) register nothing and every change stays unregistered",
         extra=("--registry", str(root_dir), "--root-a", "body", "--root-b", "body"))

    # A route scope narrows where an entry applies, not how much of a page it may cover (round 4): an
    # entry scoped to /index.html registers there and nowhere else, and a catch-all scoped to its one
    # route is a registry error like any other catch-all.
    scoped_dir = reg_dir.parent / "registry-route-scope"
    scoped_dir.mkdir(parents=True, exist_ok=True)
    (scoped_dir / "scoped.json").write_text(json.dumps([
        x("scoped-h1", "style", "Positive control: a narrow entry scoped to one route applies on that route only.",
          selector="h1, h1 *", property="*", where={"routes": ["/index.html"]}),
        x("scoped-catch-all", "style", "Negative control: a catch-all is one, whatever route scope it names.",
          selector="*", property="*", where={"routes": ["/other.html"]}),
    ], indent=1))

    def route_scope(r):
        reg_errs = [e for e in r["harness_errors"] if e.startswith("registry: ")]
        catch_all = any("[scoped-catch-all]" in e for e in reg_errs)
        h1_flagged = any("[scoped-h1]" in e for e in reg_errs)
        index = [c for c in r["cells"] if c["route"] == "/index.html"]
        other = [c for c in r["cells"] if c["route"] == "/other.html"]
        idx_used = all(((c.get("result") or {}).get("registered") or {}).get("scoped-h1") for c in index)
        idx_kinds = sorted({x["kind"] for c in index for x in (c.get("result") or {}).get("unregistered", [])})
        oth_used = any((c.get("result") or {}).get("registered") for c in other)
        oth_h1 = all(any(x["kind"] == "style" and x["path"].startswith("html > body:0 > main:0 > h1:0")
                         for x in (c.get("result") or {}).get("unregistered", [])) for c in other)
        ok = (catch_all and not h1_flagged and index and other and idx_used and idx_kinds == ["attribute"]
              and not oth_used and oth_h1)
        return ok, (f"catch-all rejected {catch_all}, scoped-h1 valid {not h1_flagged}; /index.html: scoped-h1 registers "
                    f"in every cell {idx_used}, unregistered kinds {idx_kinds}; /other.html: registered anything "
                    f"{oth_used}, its h1 style records unregistered {oth_h1}")
    case("registry-route-scope", "color-and-attribute", route_scope,
         "an entry scoped to /index.html registers the h1 records there and none on /other.html (the attribute "
         "change stays unregistered); a style catch-all scoped to its one route is a registry error",
         routes="/index.html,/other.html", extra=("--registry", str(scoped_dir)), registry_errors=True)
    return cases


def run_selftest(args):
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-selftest"
    d = RESULTS / run_id
    cases = build_cases(d / "registry")
    if args.cases:
        want = set(args.cases.split(","))
        unknown = want - {c["name"] for c in cases}
        if unknown:
            print(f"unknown cases: {', '.join(sorted(unknown))}", file=sys.stderr)
            return 2
        cases = [c for c in cases if c["name"] in want]
    browsers = args.browsers or "chrome,firefox"
    report, ok_all = [], True
    for c in cases:
        rid = f"{run_id}--{c['name']}"
        argv = [sys.executable, str(TESTS / "run.py"), *c["argv"], "--browsers", browsers, "--run-id", rid, "--no-shots"]
        t0 = time.time()
        p = subprocess.run(argv, capture_output=True, text=True)
        path = RESULTS / rid / "result.json"
        verdicts = {}
        if not path.exists():
            msg = f"no result.json (exit {p.returncode}): {(p.stderr or p.stdout)[-800:]}"
            verdicts = {b: {"ok": False, "detail": msg} for b in browsers.split(",")}
        else:
            r = json.loads(path.read_text())
            for b in browsers.split(","):
                rb = _for_browser(r, b)
                if not rb["cells"]:
                    verdicts[b] = {"ok": False, "detail": "no cells ran"}
                    continue
                try:
                    ok_b, msg_b = c["check"](rb)
                except Exception as e:
                    ok_b, msg_b = False, f"check failed: {e!r}"
                errs = rb["harness_errors"]
                if c.get("registry_errors"):
                    errs = [e for e in errs if not e.startswith("registry: ")]
                errs = [e for e in errs if not any(x in e for x in c.get("expect_errors") or ())]
                if errs and ok_b:
                    ok_b, msg_b = False, msg_b + f"; harness errors: {errs[:3]}"
                verdicts[b] = {"ok": ok_b, "detail": msg_b, "cells": len(rb["cells"]),
                               "differences": rb["totals"]["differences"]}
        ok = all(v["ok"] for v in verdicts.values())
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'} {c['name']:22} {time.time() - t0:5.1f}s  {c['describe']}", flush=True)
        for b, v in verdicts.items():
            print(f"     {b:8} {'PASS' if v['ok'] else 'FAIL'}: {v['detail']}", flush=True)
        report.append({"case": c["name"], "ok": ok, "browsers": verdicts, "describe": c["describe"], "run": rid,
                       "exit": p.returncode})
    d.mkdir(parents=True, exist_ok=True)
    (d / "selftest.json").write_text(json.dumps(report, indent=1))
    print(f"{'PASS' if ok_all else 'FAIL'}: {sum(r['ok'] for r in report)}/{len(report)} controls; wrote {d}/selftest.json")
    return 0 if ok_all else 1
