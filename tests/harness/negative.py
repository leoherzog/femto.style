"""`run.py selftest`: controls that prove the pages and styles modes detect what they must and tolerate
what they may.

Each control runs `run.py pages --a fixture --b fixture:<control>` (the styles controls: `run.py
styles`, with the fixture's state targets, tests/fixtures/states.json) in a subprocess exactly as a
user would: side A is the selftest site in tests/fixtures/site/, side B the same site with one named
change from tests/fixtures/controls.json, each served by its own harness server. The check then reads
the run's result.json. Ported from femto's negative.py; the controls are new.
"""
import json
import re
import subprocess
import sys
import time

from .paths import DIVERGENCES, FIXTURES, RESULTS, TESTS
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
             registry_errors=False, expect_errors=(), mode="pages"):
        # registry_errors: the control expects registry errors (harness errors starting "registry: "),
        # and its check judges them; expect_errors: substrings of the cell harness errors it expects
        # (the in-page "breadth: " and "coverage: " guards). Any other harness error still fails it.
        if "--registry" not in extra:
            extra = (*extra, "--registry", str(base_dir))
        if mode == "styles":
            extra = (*extra, "--states", str(FIXTURES / "states.json"))
        argv = [mode, "--a", "fixture", "--b", f"fixture:{control}" if control else "fixture",
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
        # Round 5 (p2 harness review): a pattern over the state checks would switch the state assertion
        # off; a skipped state check is one exact check for one browser.
        x("evade-skip-states", "skipped-check", check="/^state:/", where={"browsers": ["chrome", "firefox"]}),
        x("evade-skip-state-browsers", "skipped-check", check="state:hover:a", where={"browsers": ["chrome", "firefox"]}),
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
         "entry, a pattern over the state checks, a state check for two browsers), is a registry error, registers nothing, and leaves each record kind unregistered; a narrow entry "
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
    # An inherited longhand: a registered record on an element is not repeated by the descendants that
    # inherit it (differ.js inheritedFrom); a descendant with a value of its own is a record of its own.
    inh_dir = reg_dir.parent / "registry-inherited"
    inh_dir.mkdir(parents=True, exist_ok=True)
    inh_entries = [x("ok-lead", "style", "Positive control: the lead paragraph's tab-size.", selector=".lead",
                     property="tab-size"),
                   x("ok-list", "style", "Positive control: the list's tab-size.", selector="ul.list",
                     property="tab-size")]
    (inh_dir / "inherited.json").write_text(json.dumps(inh_entries, indent=1))
    first_li = "html > body:0 > main:1 > ul:2 > li:0"

    def inherited(r):
        recs = [y for _, y in _records(r)]
        got = sorted((y["path"], y.get("pseudo"), y["prop"]) for y in recs)
        folded = {}
        for c in r["cells"]:
            for k, n in ((c.get("result") or {}).get("inherited") or {}).items():
                folded[k] = folded.get(k, 0) + n
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        # Chrome Beta 158 and Firefox 160 both report tab-size on ::marker (Firefox reports no word-spacing
        # there), so the markers are asked for only where the first item's is reported.
        markers = (first_li, "::marker", "tab-size") in got
        want = [(first_li, "", "tab-size")] + ([(first_li, "::marker", "tab-size")] if markers else [])
        ok = got == want and used == {"ok-lead": 1, "ok-list": 1} and folded == {"ok-lead": 1, "ok-list": 4 if markers else 2}
        return ok, (f"unregistered {got}; registered {used}; folded into them {folded} (want the link under ok-lead, "
                    "the two other items, and their markers where the first item's is reported, under ok-list)")
    case("inherited", "inherited", inherited,
         "tab-size on the lead paragraph and the list, registered on those two elements, is folded on the link and the "
         "list items that inherit it (and their markers); the first item's own value, and its marker's, stay "
         "unregistered", extra=("--registry", str(inh_dir)))
    styles_cases(case, zero, x, reg_dir)
    return cases


MAIN = "html > body:0 > main:1"  # the fixture's <main>: an anchor (harness/styles.py ANCHORS)
LINK = "html > body:0 > main:1 > p:1 > a:0"  # the link the fixture's state targets name first
INPUT = "html > body:0 > main:1 > form:4 > input:0"  # the text input the fixture's focus target names


def styles_cases(case, zero, x, reg_dir):
    """The styles mode's controls (tests/README.md, Selftest): tokens, interactive states, and the
    registry's token and state matching."""
    def tokens_ran(r):
        idx = [c for c in r["cells"] if c["route"] == "/index.html"]
        names = {((c.get("sides") or {}).get("a") or {}).get("tokens", {}).get("names") for c in r["cells"]}
        states = {c.get("states_a") for c in idx} | {c.get("states_b") for c in idx}
        return names, states

    def styles_self(r):
        ok0, msg = zero(r)
        names, states = tokens_ran(r)
        return (ok0 and names == {10} and states == {7},
                f"{msg}; token names per cell {sorted(names, key=str)}; states replayed per side on /index.html "
                f"{sorted(states, key=str)}")
    case("styles-self", None, styles_self,
         "styles mode, the fixture site against itself, every leg, two widths, two routes: tokens (10 names, through "
         "@media, @supports, nesting and @property) and 7 state replays per side, zero differences",
         routes="/index.html,/other.html", widths="375,1300", schemes="light,dark,theme-light,theme-dark", mode="styles")

    def recs_of(r):
        return [y for c in r["cells"] for y in (c.get("result") or {}).get("unregistered", [])]

    def kinds_of(recs):
        return sorted({y["kind"] for y in recs})

    # Chrome Beta 158 resolves a token that is no color, in the color probes, to the initial text color
    # of the probe's scheme (black on light, white on dark); Firefox 160 keeps one initial color. So
    # in Chrome the other tokens show too, through those three probes only.
    scheme_probes = {"color", "border-top-color", "outline-color"}

    def token_resolution(r):
        recs = recs_of(r)
        tok = [y for y in recs if y["kind"] == "token"]
        mine = sorted({y["prop"] for y in tok if y["token"] == "--femto-scheme-color"})
        others = sorted({y["prop"] for y in tok if y["token"] != "--femto-scheme-color"})
        outside = [y["path"] for y in tok if not y["path"].startswith(MAIN)]
        kinds = kinds_of(recs)
        return (mine == ["background-color", "border-top-color", "color", "outline-color"] and set(others) <= scheme_probes
                and not outside and "token-raw" not in kinds and not {"surface-added", "surface-missing"} & set(kinds),
                f"--femto-scheme-color through {mine}; other tokens through {others}; anchors outside main "
                f"{outside[:2]}; kinds {kinds}")
    case("token-resolution", "token-resolution", token_resolution,
         "main gets color-scheme dark: --femto-scheme-color (light-dark()) keeps its raw text and resolves to its dark "
         "color through the four color probes, at the anchors in main only, and no token-raw record exists (in Chrome "
         "the other tokens' color, border-top-color and outline-color probes follow the scheme too)", mode="styles")

    def one_kind(kind, token, per_anchor=False):
        def chk(r):
            recs = recs_of(r)
            per_cell = {len((c.get("result") or {}).get("unregistered", [])) for c in r["cells"]}
            anchors = {((c.get("sides") or {}).get("b") or {}).get("tokens", {}).get("anchors") for c in r["cells"]}
            want = anchors if per_anchor else {1}
            toks = sorted({y.get("token") for y in recs})
            return (kinds_of(recs) == [kind] and toks == [token] and per_cell == want,
                    f"kinds {kinds_of(recs)}, tokens {toks}, records per cell {sorted(per_cell)} (want {sorted(want, key=str)})")
        return chk
    case("token-raw", "token-raw", one_kind("token-raw", "--femto-raw", per_anchor=True),
         "--femto-raw written #f00 instead of #ff0000: one token-raw record per anchor, and no token record (it "
         "resolves the same through every probe property)", mode="styles")
    case("token-added", "token-added", one_kind("surface-added", "--femto-new"),
         "a token only side B declares is one surface-added record and nothing else", mode="styles")
    case("token-missing", "token-missing", one_kind("surface-missing", "--femto-gone"),
         "a token only side A declares is one surface-missing record and nothing else", mode="styles")

    def only_state(state):
        def chk(r):
            recs = recs_of(r)
            states = sorted({str(y.get("state")) for y in recs})
            paths = sorted({y["path"] for y in recs})
            props = sorted({y["prop"] for y in recs if y["kind"] == "style"})
            return (bool(recs) and states == [state] and paths == [LINK] and kinds_of(recs) == ["style"],
                    f"states with records {states}, paths {paths}, properties {props}, kinds {kinds_of(recs)}")
        return chk
    case("hover-only", "hover-only", only_state("hover"),
         "a rule under #link:hover:not(:active) shows in the hover replay only, on the link only (none in the "
         "document as loaded, focus-visible or active)", mode="styles")
    case("focus-visible-only", "focus-visible-only", only_state("focus-visible"),
         "a rule under #link:focus-visible shows in the focus-visible replay (a real Tab) only, on the link only",
         mode="styles")
    case("active-only", "active-only", only_state("active"),
         "a rule under #link:active shows in the active replay (pointer down) only, on the link only", mode="styles")

    def focus_only(r):
        recs = recs_of(r)
        states = sorted({str(y.get("state")) for y in recs})
        paths = sorted({y["path"] for y in recs})
        return (bool(recs) and states == ["focus"] and paths == [INPUT] and kinds_of(recs) == ["style"],
                f"states with records {states}, paths {paths}, kinds {kinds_of(recs)}")
    case("focus-only", "focus-only", focus_only,
         "a rule under the text input's :focus shows in the focus replay (focus()) only, on the input only (and its "
         "::placeholder, which inherits it)", mode="styles")

    def dark_only_token(r):
        recs = recs_of(r)
        legs = sorted({c["scheme"] for c in r["cells"] if (c.get("result") or {}).get("unregisteredTotal")})
        toks = sorted({y.get("token") for y in recs})
        kinds = kinds_of(recs)
        return (legs == ["dark"] and toks == ["--femto-spacing"] and "token-raw" in kinds and set(kinds) <= {"token", "token-raw"},
                f"legs with records {legs}, tokens {toks}, kinds {kinds}")
    case("dark-only-token", "dark-only-token", dark_only_token,
         "a token changed only under prefers-color-scheme: dark (no data-theme) shows only in leg dark, as token and "
         "token-raw records", schemes=ALL_LEGS, mode="styles")

    color_probes = {"color", "background-color", "border-top-color", "outline-color"}

    def token_color2(r):
        recs = recs_of(r)
        tok = [y for y in recs if y["kind"] == "token"]
        props = sorted({y["prop"] for y in tok})
        toks = sorted({y.get("token") for y in recs})
        kinds = kinds_of(recs)
        return (kinds == ["token", "token-raw"] and toks == ["--femto-accent"] and "color" in props
                and set(props) <= color_probes,
                f"kinds {kinds} (no style record, though ::selection reads it), tokens {toks}, token probes {props}")
    case("token-color-2-of-255", "token-color-2-of-255", token_color2,
         "--femto-accent rgb(1, 106, 168) to rgb(3, 106, 168) (2/255), a token only ::selection reads, which no "
         "collected style shows: token resolution detects it through the color probes, and its raw text differs",
         mode="styles")
    case("token-color-1-of-255", "token-color-1-of-255",
         lambda r: (kinds_of(recs_of(r)) == ["token-raw"] and {y.get("token") for y in recs_of(r)} == {"--femto-accent"},
                    f"kinds {kinds_of(recs_of(r))}, tokens {sorted({y.get('token') for y in recs_of(r)})}"),
         "--femto-accent rgb(1, 106, 168) to rgb(2, 106, 168) (1/255) is tolerated by token resolution: only its raw "
         "text differs", mode="styles")

    # The minifier rule (differ.js sameRaw, sameMinified): clean-css's spellings compare as equal, the
    # same edits are found with --exact-minified, and real changes written the same way still are.
    H1 = "html > body:0 > main:1 > h1:0"
    MINIFIED = {"outline-width", "background-position", "background-position-x", "background-position-y"}

    def minified(r, real):
        recs = recs_of(r)
        style = [y for y in recs if y["kind"] == "style"]
        props = sorted({y["prop"] for y in style})
        outside = [y["path"] for y in style if not y["path"].startswith(H1)]
        toks = sorted({y.get("token") for y in recs if y["kind"] != "style"})
        kinds = kinds_of(recs)
        # Chrome Beta 158 collects the background-position shorthand, Firefox 160 its two longhands.
        position = [y for y in style if y["prop"].startswith("background-position")]
        if real:
            ok = ({"outline-width", "outline-style"} <= set(props) and position and "background-position-x" not in props
                  and all(y["b"].endswith("1px") for y in position) and kinds == ["style", "token", "token-raw"])
        else:
            ok = "outline-width" in props and position and set(props) <= MINIFIED and kinds == ["style", "token-raw"]
        return (ok and not outside and toks == ["--femto-shadow"] and not r["harness_errors"],
                f"kinds {kinds}, style properties {props}, style records outside h1 {outside[:2]}, tokens {toks}")
    case("minified-equal", "minified-equal", zero,
         "h1's outline: 0 and background: 0 0 for none, and --femto-shadow's .5rem and comma spacing, as clean-css "
         "wrote the oracle's: zero differences", mode="styles")
    case("minified-exact", "minified-equal", lambda r: minified(r, False),
         "the same control with --exact-minified: h1's outline-width and background-position records and "
         "--femto-shadow's token-raw records, nothing else", extra=("--exact-minified",), mode="styles")
    case("minified-real", "minified-real", lambda r: minified(r, True),
         "h1's outline: 2px solid and background: 0 1px, and --femto-shadow's blur 0.5rem to .3rem: outline-width "
         "(outline-style is solid on side B), the position's 1px (the shorthand in Chrome, -y in Firefox), and "
         "--femto-shadow's raw text and resolution are found; background-position-x, 0% against 0px, is not", mode="styles")

    # The state coverage rule counts what a state adds: a registered difference of the document that a
    # state's small subtree holds again was judged in the document, so it is no coverage error there.
    cov_dir = reg_dir.parent / "registry-state-coverage"
    cov_dir.mkdir(parents=True, exist_ok=True)
    (cov_dir / "coverage.json").write_text(json.dumps([
        x("ok-punctuation", "style", "Positive control: the progress code's punctuation tokens' word-spacing.",
          selector="article[aria-label=\"Progress example\"] span.punctuation", property="word-spacing",
          where={"comparisons": ["styles"], "routes": ["/index.html"]})], indent=1))

    def state_coverage(r):
        cov = [e for e in r["harness_errors"] if "coverage: " in e]
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        hover = sum(1 for c in r["cells"] for y in ((c.get("result") or {}).get("samples") or {}).get("ok-punctuation", [])
                    if y.get("state") == "hover")
        return (not cov and r["totals"]["unregistered"] == 0 and used.get("ok-punctuation") == 16,
                f"coverage errors {cov[:1]}; unregistered {r['totals']['unregistered']}; registered {used} (8 in the "
                f"document, 8 again under the footer's hover); hover samples {hover}")
    case("state-coverage", "state-coverage", state_coverage,
         "8 registered punctuation records are 16% of the document and 38% of the article the footer's hover "
         "collects: under the state they repeat the document's records, add nothing and cover nothing, so neither "
         "coverage check fails", extra=("--registry", str(cov_dir)), mode="styles")

    # The registry's token and state fields match only what they name: a token entry by token, anchor
    # and probe property, a token-raw entry by token and anchor path, a surface entry by token, and a
    # style entry's where.states by state. Entries that name no styles comparison never apply in one,
    # and a token entry that names every token is rejected (statically for *, in the page for a
    # pattern that reaches most of the cell's names).
    st = {"comparisons": ["styles"]}
    entries = [
        x("ok-token", "token", "Positive control: --femto-accent at main through color only.", token="--femto-accent",
          selector="main", property="color", where=st),
        x("ok-token-raw", "token-raw", "Positive control: --femto-accent's raw text at main only.", token="--femto-accent",
          path=MAIN, where=st),
        x("ok-surface", "surface-added", "Positive control: --femto-new only.", token="--femto-new", where=st),
        x("ok-hover", "style", "Positive control: the link's word-spacing under hover only.", selector="#link",
          property="word-spacing", where={"comparisons": ["styles"], "states": ["hover"]}),
        x("pages-only-hover", "style", "Negative control: an entry that names no comparison applies in pages runs, "
          "never in styles runs.", selector="#link", property="word-spacing"),
        x("evade-token-star", "token-raw", token="*", where=st),
        x("evade-token-nocomp", "token-raw", token="--femto-spacing"),
        x("evade-token-states", "token-raw", token="--femto-spacing", where={"comparisons": ["styles"], "states": ["hover"]}),
        x("evade-token-dot", "token-raw", token="/./", where=st),
    ]
    st_dir = reg_dir.parent / "registry-styles"
    st_dir.mkdir(parents=True, exist_ok=True)
    (st_dir / "styles.json").write_text(json.dumps(entries, indent=1))

    def registry_styles(r):
        reg_errs = [e for e in r["harness_errors"] if e.startswith("registry: ")]
        guard = [e for e in r["harness_errors"] if "breadth: registry entry " in e]
        rejected = sorted(e["id"] for e in entries if any(f"[{e['id']}]" in m for m in reg_errs))
        guarded = sorted(e["id"] for e in entries if any(f"entry {e['id']} matches" in g for g in guard))
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        recs = recs_of(r)

        def has(kind, token=None, at=None, not_at=None, prop=None, not_prop=None, state=None):
            return any(y["kind"] == kind and (token is None or y.get("token") == token)
                       and (at is None or y.get("path") == at) and (not_at is None or y.get("path") != not_at)
                       and (prop is None or y.get("prop") == prop) and (not_prop is None or y.get("prop") != not_prop)
                       and (state is None or y.get("state") == state) for y in recs)
        stays = {  # records no entry names: they stay unregistered
            "token --femto-accent at main, other probe properties": has("token", "--femto-accent", at=MAIN, not_prop="color"),
            "token --femto-accent at other anchors": has("token", "--femto-accent", not_at=MAIN, prop="color"),
            "token-raw --femto-accent at other anchors": has("token-raw", "--femto-accent", not_at=MAIN),
            "token and token-raw --femto-spacing": has("token", "--femto-spacing") and has("token-raw", "--femto-spacing"),
            "surface-added --femto-other": has("surface-added", "--femto-other"),
            "the link's word-spacing under active": has("style", at=LINK, prop="word-spacing", state="active"),
        }
        gone = {  # records an entry names: none stays unregistered
            "token --femto-accent at main through color": has("token", "--femto-accent", at=MAIN, prop="color"),
            "token-raw --femto-accent at main": has("token-raw", "--femto-accent", at=MAIN),
            "surface-added --femto-new": has("surface-added", "--femto-new"),
            "the link's word-spacing under hover": has("style", at=LINK, prop="word-spacing", state="hover"),
        }
        want_used = {"ok-token", "ok-token-raw", "ok-surface", "ok-hover"}
        ok = (rejected == ["evade-token-nocomp", "evade-token-star", "evade-token-states"] and guarded == ["evade-token-dot"]
              and set(used) == want_used and all(stays.values()) and not any(gone.values()) and r["status"] == "FAIL")
        return ok, (f"registry errors name {rejected}; in-page breadth errors name {guarded}; registered {used}; "
                    f"left unregistered: {[k for k, v in stays.items() if not v] or 'all as expected'} missing; "
                    f"wrongly unregistered: {[k for k, v in gone.items() if v] or 'none'}; run {r['status']}")
    case("registry-styles", "registry-tokens-states", registry_styles,
         "token, token-raw and surface entries match only the token, anchor and probe property they name, and a style "
         "entry's where.states only its state; an entry naming no styles comparison never applies in one; token *, a "
         "token entry without where.comparisons styles or with where.states is a registry error, and token /./ "
         "is taken out of the cell by the in-page breadth guard",
         extra=("--registry", str(st_dir)), registry_errors=True, expect_errors=("breadth: registry entry ",),
         mode="styles")

    # A catch-all split by name: each token-raw entry names under half of the cell's token names, and
    # together they name all of them. The token entries of a kind share one limit (differ.js
    # breadthGuard), so none of them is applied and the raw text changes stay unregistered.
    split = [x("evade-raw-a-m", "token-raw", token="/^--femto-[a-m]/", where=st),
             x("evade-raw-n-r", "token-raw", token="/^--femto-[n-r]/", where=st),
             x("evade-raw-s-z", "token-raw", token="/^--femto-[s-z]/", where=st)]
    split_dir = reg_dir.parent / "registry-token-split"
    split_dir.mkdir(parents=True, exist_ok=True)
    (split_dir / "split.json").write_text(json.dumps(split, indent=1))

    def token_split(r):
        guard = [e for e in r["harness_errors"] if "breadth: the 3 token-raw entries" in e]
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        raw = sorted({y["token"] for y in recs_of(r) if y["kind"] == "token-raw"})
        return (bool(guard) and not used and raw == ["--femto-accent", "--femto-spacing"],
                f"union errors {len(guard)}; registered {used}; token-raw records left unregistered for {raw}")
    case("registry-token-split", "registry-tokens-states", token_split,
         "three token-raw entries that each name under half of the cell's token names and together all of them are "
         "taken out of the cell by the in-page union limit, so the raw text changes stay unregistered",
         extra=("--registry", str(split_dir)), expect_errors=("breadth: the 3 token-raw entries",), mode="styles")

    def reg_dir_of(name, entries):
        d = reg_dir.parent / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "entries.json").write_text(json.dumps(entries, indent=1))
        return d

    # The same split for surface entries: the surface-added entries of a cell whose patterns are open
    # (a prefix, a range of names) share the token union limit, so the added names stay unregistered.
    surface_split = [x(f"evade-surface-{rng}", "surface-added", token=f"/^--femto-[{rng}]/", where=st)
                     for rng in ("a-m", "n-r", "s-z")]
    surface_dir = reg_dir_of("registry-surface-split", surface_split)

    def surface_split_chk(r):
        guard = [e for e in r["harness_errors"] if "breadth: the 3 surface-added entries with an open token pattern" in e]
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        added = sorted({y["token"] for y in recs_of(r) if y["kind"] == "surface-added"})
        return (bool(guard) and not used and added == ["--femto-new", "--femto-other"],
                f"union errors {len(guard)}; registered {used}; surface-added records left unregistered for {added}")
    case("registry-surface-split", "registry-tokens-states", surface_split_chk,
         "three surface-added entries with open patterns that each name under half of the cell's token names and "
         "together all of them are taken out of the cell by the in-page union limit, so the added tokens stay "
         "unregistered", extra=("--registry", str(surface_dir)),
         expect_errors=("breadth: the 3 surface-added entries with an open token pattern",), mode="styles")

    # A surface entry whose pattern writes its names out (registry.py _closed_set) may name up to 70%
    # of a cell's token names; the same names with one open alternative (r.w) are held to 50%.
    surface_closed = [
        x("ok-surface-closed", "surface-added", "Positive control: seven names written out, the two added among them.",
          token="/^--femto-(new|other|accent|gone|media|nested|raw)$/", where=st),
        x("evade-surface-open", "surface-added", token="/^--femto-(new|other|accent|gone|media|nested|r.w)$/", where=st),
    ]
    closed_dir = reg_dir_of("registry-surface-closed", surface_closed)

    def surface_closed_chk(r):
        guard = [e for e in r["harness_errors"] if "breadth: registry entry " in e]
        named = sorted(e["id"] for e in surface_closed if any(f"entry {e['id']} matches" in g for g in guard))
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        left = recs_of(r)
        return (named == ["evade-surface-open"] and used == {"ok-surface-closed": 2}
                and all(y["kind"] != "surface-added" for y in left),
                f"in-page breadth errors name {named}; registered {used}; surface-added records left "
                f"{[y['token'] for y in left if y['kind'] == 'surface-added']}")
    case("registry-surface-closed", "registry-tokens-states", surface_closed_chk,
         "a surface-added entry that writes out 7 of the 11 token names of side B (64%) registers the two added "
         "tokens; the same pattern with one open alternative is held to 50% and taken out of the cell",
         extra=("--registry", str(closed_dir)), expect_errors=("breadth: registry entry ",), mode="styles")

    # A pinned entry (registry.py _pinned): one route, one property, exact values. It may reach up to
    # 40% of a document on the repeats of one example, and its records cover nothing; an entry for
    # the same elements with open values, or a pinned one over two shapes of tree path, is held to
    # 25% (registry errors).
    fd = {"routes": ["/index.html"], "comparisons": ["styles"]}
    spans = "article[aria-label=\"Progress example\"] code > span"

    def femto(e):
        return dict(e, category="femto-divergence")
    pinned = [
        femto(x("ok-pinned", "style", "Positive control: the code tokens' tab-size.", selector=spans, pseudo="",
                property="tab-size", a="8", b="4", where=fd)),
        femto(x("evade-pinned-shapes", "style", selector=f"{spans}:nth-child(-n+12), ul.list > li", pseudo="",
                property="cursor", a="auto", b="pointer", where=fd)),
        femto(x("evade-pinned-open", "style", selector=spans, pseudo="", property="touch-action", a="*", b="*",
                where=fd)),
    ]
    pinned_dir = reg_dir_of("registry-pinned", pinned)

    def pinned_chk(r):
        reg_errs = [e for e in r["harness_errors"] if e.startswith("registry: ")]
        rejected = sorted(e["id"] for e in pinned if any(f"[{e['id']}]" in m for m in reg_errs))
        bad = [e for e in r["harness_errors"] if "breadth: " in e or "coverage: " in e]
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        left = recs_of(r)
        props = sorted({y["prop"] for y in left})
        per_cell = {((c.get("result") or {}).get("registered") or {}).get("ok-pinned") for c in r["cells"]}
        n = next(iter(per_cell)) if len(per_cell) == 1 else None
        return (rejected == ["evade-pinned-open", "evade-pinned-shapes"] and not bad and set(used) == {"ok-pinned"}
                and isinstance(n, int) and n >= 16 and props == ["cursor", "touch-action"] and kinds_of(left) == ["style"],
                f"registry errors name {rejected}; breadth or coverage errors {bad[:1]}; registered {used} "
                f"({sorted(per_cell, key=str)} per cell); left unregistered {props}, kinds {kinds_of(left)}")
    case("registry-pinned", "registry-pinned", pinned_chk,
         "a pinned entry (one route, one property, exact values) registers the tab-size of the 17 code tokens, 35% of "
         "the document and one shape of tree path, with no breadth or coverage error; the same tokens with open "
         "values, and a pinned entry over two shapes, are registry errors, so their records stay unregistered",
         extra=("--registry", str(pinned_dir)), registry_errors=True, mode="styles")

    # Layout consequences: a style entry for one route that names only geometry longhands (differ.js
    # GEOMETRY) covers nothing, so a registered change and the sizes it moves can pass 25% of a page
    # together; the same entry without its route counts, and the coverage rule fails the cell.
    cons_props = "/^(height|block-size|transform-origin|perspective-origin)$/"

    def consequence_entries(scoped):
        return [
            x("ok-cursor", "style", "Positive control: ten elements' cursor.",
              selector=".lead, .pseudo, h1, .wide, .scheme, ul.list > li, pre, footer.site", pseudo="", property="cursor",
              a="auto", b="pointer", where=fd),
            x("ok-padding", "style", "Positive control: the list's padding-block.", selector="ul.list", pseudo="",
              property="/^padding-(top|bottom|block-start|block-end)$/", a="0px", b="4px", where=fd),
            femto(x("ok-layout", "style", "Positive control: the list's and its ancestors' heights and origins.",
                    selector="html, body, main, ul.list", pseudo="", property=cons_props,
                    where=fd if scoped else st)),
        ]
    cons_dir = reg_dir_of("registry-consequence", consequence_entries(True))
    cons_open_dir = reg_dir_of("registry-consequence-unscoped", consequence_entries(False))

    def consequence(scoped):
        def chk(r):
            cov = [e for e in r["harness_errors"] if "coverage: " in e]
            used = {k: v for k, v in r["registered_by_entry"].items() if v}
            left = r["totals"]["unregistered"]
            ok = set(used) == {"ok-cursor", "ok-padding", "ok-layout"} and left == 0 and (not cov if scoped else bool(cov))
            return ok, f"coverage errors {cov[:1]}; registered {used}; unregistered {left}"
        return chk
    case("registry-consequence", "registry-consequence", consequence(True),
         "a cursor change on ten elements and the list's padding are registered, and the heights and origins the padding "
         "moves (the list, main, body, html) by a layout consequence for /index.html: together 29% of the document, "
         "the consequence covers nothing, so the coverage rule passes",
         extra=("--registry", str(cons_dir)), mode="styles")
    case("registry-consequence-unscoped", "registry-consequence", consequence(False),
         "the same entries with the consequence naming no route: it covers what it registers, so the cell's "
         "registered records cover 29% of the document and the coverage rule fails it",
         extra=("--registry", str(cons_open_dir)), expect_errors=("coverage: ",), mode="styles")

    # The replay's scrolling is instant (differ.js armStates): side B's html { scroll-behavior: smooth }
    # (registered) would make the focus() and Tab of #far smooth, and other.html's scroll spy would
    # count the positions in between. After the replay html's scroll-behavior is the page's own again.
    smooth_dir = reg_dir_of("registry-scroll-smooth", [
        x("ok-smooth", "style", "Positive control: html's scroll-behavior.", selector="html", pseudo="",
          property="scroll-behavior", a="auto", b="smooth", where={"routes": ["/other.html"], "comparisons": ["styles"]})])

    def scroll_smooth(r):
        used = {k: v for k, v in r["registered_by_entry"].items() if v}
        left = recs_of(r)
        far = {(c.get("states_a"), c.get("states_b")) for c in r["cells"]}
        after = {(c.get("scroll_behavior_a"), c.get("scroll_behavior_b")) for c in r["cells"]}
        return (not left and used == {"ok-smooth": len(r["cells"])} and far == {(3, 3)} and after == {("auto", "smooth")},
                f"unregistered {[fmt(y) for y in left[:3]]}; registered {used}; state replays per side {sorted(far, key=str)}; "
                f"html scroll-behavior after the replay (A, B) {sorted(after, key=str)}")
    case("scroll-smooth", "scroll-smooth", scroll_smooth,
         "side B's html { scroll-behavior: smooth } is one registered record; the focus (from the top), focus-visible "
         "and hover replays of #far below the fold scroll instantly on both sides, so other.html's scroll spy counts "
         "the same positions, and afterwards html's scroll-behavior is each side's own again", routes="/other.html",
         extra=("--registry", str(smooth_dir)), mode="styles")


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
