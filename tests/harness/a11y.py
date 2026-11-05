"""The a11y mode: acceptance criterion 10, "axe-core finds no serious or critical violation on any
page, in Chrome and Firefox, light and dark, at 375 and 1300".

    uv run tests/run.py a11y [--target dist | dist:<path> | static-femto | <base URL>]
                             [--pages /,/docs] [--browsers chrome,firefox] [--schemes light,dark]
                             [--widths 375,1300]

axe-core is the repository's own, node_modules/axe-core/axe.min.js at the exact version package.json
pins (it is never downloaded; a missing or mispinned copy is a setup error). For every browser, page,
scheme and width the page is reset and loaded as in the behavior mode (harness/behavior.py: a fresh
headless tab, the viewport set exactly with WebDriver BiDi, prefers-color-scheme emulated, storage
emptied, the page loaded and the static readiness hook run), then axe's source is run in the
document through Selenium and axe.run(document) reads it whole. The script is injected, never
loaded, so it adds no request and nothing on another origin.

A serious or critical violation fails the run; the moderate and minor ones are listed and do not.
result.json lists each violation's rule, impact, help, every node's target selector and HTML, and the
page and cell it was found in; summary.txt groups them by impact, rule, page and target.
"""
import contextlib
import json
import os
import sys
import threading
import time
import traceback
from types import SimpleNamespace

from .paths import REPO, RESULTS

AXE = REPO / "node_modules" / "axe-core"
# Criterion 10's pages: every page of the URL inventory (the 404 page through a path that has none),
# and the docs page once more with a theme, so the theme stylesheet's colors are covered too.
PAGES = ("/", "/examples", "/demo", "/does-not-exist", "/docs", "/docs?theme=jade")
BROWSERS = ("chrome", "firefox")
SCHEMES = ("light", "dark")
WIDTHS = (375, 1300)
HEIGHT = 800             # the parity matrix's one viewport height
FAILING = ("critical", "serious")
IMPACTS = ("critical", "serious", "moderate", "minor")


def csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else []


def add_parser(sub):
    p = sub.add_parser("a11y", help="axe-core on every page of one target (criterion 10)")
    p.add_argument("--target", default="dist", help="dist (default), dist:<path>, a named target or a base URL")
    p.add_argument("--pages", help="comma list of paths (default: " + ",".join(PAGES) + ")")
    p.add_argument("--browsers", default="chrome,firefox", help="comma list of chrome, firefox (default both)")
    p.add_argument("--schemes", default="light,dark", help="comma list of light, dark (default both)")
    p.add_argument("--widths", default="375,1300", help="comma list of viewport widths (default 375,1300)")
    p.add_argument("--ready", help="readiness hook (oracle, static, none; default: the target's)")
    p.add_argument("--workers", help="sessions per browser, e.g. chrome=2,firefox=2 (default 1 each)")
    p.add_argument("--run-id", help="name of the results folder (default: timestamp-a11y-pid)")
    p.add_argument("--label", help="free text stored in result.json")
    p.add_argument("--plan", action="store_true", help="print the planned cells and exit; starts nothing")
    return p


class AxeError(Exception):
    """node_modules/axe-core is missing or not the version package.json pins (exit 2)."""


def axe_source():
    """(source, version) of the repository's pinned axe-core."""
    try:
        pin = (json.loads((REPO / "package.json").read_text()).get("devDependencies") or {}).get("axe-core")
    except (OSError, ValueError) as e:
        raise AxeError(f"cannot read package.json: {e}") from None
    if not pin:
        raise AxeError("package.json has no devDependencies.axe-core: the a11y mode runs the repository's own axe-core")
    try:
        version = json.loads((AXE / "package.json").read_text())["version"]
        source = (AXE / "axe.min.js").read_text()
    except (OSError, ValueError, KeyError):
        raise AxeError(f"node_modules/axe-core is missing: run `npm install` (package.json pins axe-core {pin})") from None
    if version != pin:
        raise AxeError(f"node_modules/axe-core is {version}, but package.json pins {pin}: run `npm install`")
    return source, version


# axe.run on the whole document. Each violation keeps its rule, impact, help and every node's target
# (axe's CSS selector path; frames and shadow roots are joined with " >>> "), HTML and summary.
RUN_AXE = """
const done = arguments[arguments.length - 1];
axe.run(document, {resultTypes: ["violations"]}).then((r) => done({
  version: axe.version, url: location.pathname + location.search,
  passes: r.passes.length, incomplete: r.incomplete.length, inapplicable: r.inapplicable.length,
  violations: r.violations.map((v) => ({
    rule: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl, tags: v.tags,
    nodes: v.nodes.map((n) => ({
      target: n.target.map((t) => Array.isArray(t) ? t.join(" >>> ") : String(t)).join(" >>> "),
      impact: n.impact, html: String(n.html || "").slice(0, 300),
      failure: String(n.failureSummary || "").slice(0, 600),
    })),
  })),
}), (e) => done({error: String(e && e.stack || e)}));
"""


def run_cell(page, cell, source):
    """Load one page in one cell, run axe in it, and return the cell's record."""
    t0 = time.time()
    rec = dict(cell)
    check = SimpleNamespace(width=cell["width"], height=HEIGHT, media=cell["scheme"], storage={}, preload=None)
    try:
        page.reset(check, cell["page"])
        page.js(source + "\n;return typeof axe;")
        out = page.driver.execute_async_script(RUN_AXE)
        if out.get("error"):
            raise RuntimeError(f"axe.run: {out['error'][:500]}")
        rec.update(status="ok", url=out["url"], axe=out["version"], passes=out["passes"],
                   incomplete=out["incomplete"], inapplicable=out["inapplicable"], violations=out["violations"])
    except Exception as e:
        from selenium.common.exceptions import WebDriverException
        rec.update(status="error", error=f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else repr(e)}",
                   traceback=traceback.format_exc(limit=4), violations=[])
        rec["webdriver_error"] = isinstance(e, WebDriverException) and "session" in str(e).lower()
    rec["counts"] = {i: sum(1 for v in rec["violations"] if v.get("impact") == i) for i in IMPACTS}
    rec["duration_s"] = round(time.time() - t0, 2)
    return rec


def cell_name(c):
    return f"{c['browser']} {c['page']} {c['scheme']} {c['width']}"


def findings(cells):
    """Every violation node, one row per (impact, rule, page, target) with the cells it was found in."""
    rows = {}
    for c in cells:
        for v in c.get("violations") or []:
            for n in v["nodes"]:
                key = (v.get("impact") or "unknown", v["rule"], c["page"], n["target"])
                r = rows.setdefault(key, {"impact": key[0], "rule": v["rule"], "page": c["page"], "target": n["target"],
                                          "help": v.get("help"), "helpUrl": v.get("helpUrl"), "html": n["html"],
                                          "failure": n["failure"], "cells": []})
                r["cells"].append(f"{c['browser']} {c['scheme']} {c['width']}")
    order = {i: k for k, i in enumerate(IMPACTS)}
    return sorted(rows.values(), key=lambda r: (order.get(r["impact"], 9), r["rule"], r["page"], r["target"]))


def summary_text(result):
    t = result["totals"]
    L = [f"{result['status']}  a11y {result['target']} ({result['base']}), axe-core {result['axe']}, run "
         f"{result['run_id']}, {result['duration_s']} s",
         f"cells {t['cells']} (planned {t['planned']}), errors {t['errors']}; rules violated, summed over the cells, by "
         "impact: " + ", ".join(f"{i} {t['by_impact'][i]}" for i in IMPACTS)
         + f"; failing (serious or critical): {t['failing']} targets in {t['failing_rules']} rules"]
    for title, rows in (("FAILING (serious and critical: criterion 10)", result["failing"]),
                        ("LISTED (moderate and minor: not failing)", result["listed"])):
        L += ["", f"{title}: {len(rows)}"]
        for r in rows:
            L.append(f"  [{r['impact']}] {r['rule']} on {r['page']}: {r['target']}  ({len(r['cells'])} cells: "
                     + ", ".join(r["cells"][:6]) + (", ..." if len(r["cells"]) > 6 else "") + ")")
            L.append(f"      {r['help']}; {r['html'][:160]}")
    if result["errors"]:
        L += ["", "HARNESS ERRORS"] + [f"  {e.splitlines()[0]}" for e in result["errors"]]
    L += ["", "CELLS"]
    for c in result["cells"]:
        L.append(f"  {c['status'].upper():5} {cell_name(c)}: rules " + ", ".join(f"{i} {c['counts'][i]}" for i in IMPACTS)
                 + (f" | {c['error']}" if c.get("error") else f" (passes {c.get('passes')}, incomplete {c.get('incomplete')})"))
    return "\n".join(L) + "\n"


def run_a11y(args):
    from . import locks
    from .behavior import Page, Session
    from .cli import git_info
    from .targets import Side, TargetError, start
    browsers, schemes = csv(args.browsers), csv(args.schemes)
    pages = csv(args.pages) or list(PAGES)
    try:
        widths = [int(w) for w in csv(args.widths)]
    except ValueError:
        print(f"error: --widths takes integers, not {args.widths!r}", file=sys.stderr)
        return 2
    bad = [b for b in browsers if b not in BROWSERS] + [s for s in schemes if s not in SCHEMES]
    if bad or not (browsers and schemes and widths and pages):
        print(f"error: the a11y mode runs browsers {', '.join(BROWSERS)} and schemes {', '.join(SCHEMES)} "
              f"(criterion 10); got {', '.join(bad) or 'an empty axis'}", file=sys.stderr)
        return 2
    cells = [{"browser": b, "page": p, "scheme": s, "width": w}
             for b in browsers for p in pages for s in schemes for w in widths]
    if args.plan:
        print(f"plan: a11y, target {args.target}: {len(cells)} cells ({len(pages)} pages x {len(schemes)} schemes x "
              f"{len(widths)} widths per browser)")
        for b in browsers:
            print(f"  {b:7} {sum(1 for c in cells if c['browser'] == b)} cells: pages {', '.join(pages)}; "
                  f"schemes {', '.join(schemes)}; widths {', '.join(map(str, widths))}")
        return 0
    try:
        source, version = axe_source()
        side = Side(args.target, args.ready)
        side.check()
    except (AxeError, TargetError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    workers = {b: 1 for b in BROWSERS}
    for kv in csv(args.workers):
        k, _, v = kv.partition("=")
        workers[k] = int(v)
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-a11y-{os.getpid()}"
    run_dir = RESULTS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_f = open(run_dir / "log.txt", "a")
    lock = threading.Lock()

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        with lock:
            print(line, flush=True)
            log_f.write(line + "\n")
            log_f.flush()

    log(f"run {run_id}: a11y, {len(cells)} cells, axe-core {version}, target {args.target}; results in "
        f"{run_dir.relative_to(REPO)}")
    t0 = time.time()
    results, errors, sessions = [], [], []
    queues = {b: [c for c in cells if c["browser"] == b] for b in browsers}

    def worker(browser, n):
        label = f"{run_id} a11y {browser}#{n}"
        try:
            with locks.slot(label, log):
                sess = page = None
                try:
                    while True:
                        with lock:
                            cell = queues[browser].pop(0) if queues[browser] else None
                        if cell is None:
                            break
                        if sess is None:
                            sess = Session(browser, log)
                            page = Page(sess, side.base, side.ready)
                            with lock:
                                sessions.append(sess.describe())
                            log(f"{label}: {browser} {sess.version} ({sess.driver_version}), launch {sess.launch_s}s")
                        rec = run_cell(page, cell, source)
                        with lock:
                            results.append(rec)
                            k = len(results)
                        log(f"[{k}/{len(cells)} {time.time() - t0:5.0f}s] {cell_name(rec)}: {rec['status']}, "
                            + ", ".join(f"{i} {rec['counts'][i]}" for i in IMPACTS) + f" ({rec['duration_s']}s)"
                            + (f" | {rec['error'][:300]}" if rec.get("error") else ""))
                        if rec.get("webdriver_error"):
                            sess.quit()
                            sess = None
                finally:
                    if sess is not None:
                        sess.quit()
        except Exception as e:
            with lock:
                errors.append(f"{label}: worker failed: {e}\n{traceback.format_exc()}")
            log(f"{label}: worker failed: {e}")

    try:
        with contextlib.ExitStack() as stack:
            try:
                start(stack, side, log, run_dir)
            except Exception as e:
                log(f"error: cannot start the target: {type(e).__name__}: {e}")
                log_f.close()
                return 2
            log(f"target {side.spec} at {side.base} (ready: {side.ready})")
            threads = [threading.Thread(target=worker, args=(b, i), daemon=True, name=f"a11y-{b}-{i}")
                       for b in browsers for i in range(max(1, min(workers.get(b, 1), len(queues[b]))))]
            for th in threads:
                th.start()
            for th in threads:
                while th.is_alive():
                    th.join(0.5)
    except KeyboardInterrupt:
        errors.append("interrupted")
    log("target stopped")
    order = {(c["browser"], c["page"], c["scheme"], c["width"]): i for i, c in enumerate(cells)}
    results.sort(key=lambda r: order[(r["browser"], r["page"], r["scheme"], r["width"])])
    errors += [f"{cell_name(r)}: {r['error']}" for r in results if r["status"] == "error"]
    if len(results) < len(cells):
        errors.append(f"{len(cells) - len(results)} cells never ran")
    rows = findings(results)
    failing = [r for r in rows if r["impact"] in FAILING]
    listed = [r for r in rows if r["impact"] not in FAILING]
    by_impact = {i: sum(c["counts"][i] for c in results) for i in IMPACTS}
    ok = not errors and not failing
    result = {"run_id": run_id, "mode": "a11y", "status": "PASS" if ok else "FAIL", "argv": sys.argv[1:],
              "label": args.label, "target": args.target, "base": side.base, "side": side.describe(), "axe": version,
              "axe_source": str(AXE.relative_to(REPO) / "axe.min.js"), "browsers": browsers, "pages": pages,
              "schemes": schemes, "widths": widths, "height": HEIGHT, "failing_impacts": list(FAILING),
              "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)),
              "duration_s": round(time.time() - t0, 1), "git": git_info(), "sessions": sessions,
              "totals": {"planned": len(cells), "cells": len(results), "errors": len(errors), "by_impact": by_impact,
                         "failing": len(failing), "failing_rules": len({r["rule"] for r in failing}),
                         "listed": len(listed)},
              "failing": failing, "listed": listed, "errors": errors,
              "cells": [{k: v for k, v in r.items() if k not in ("traceback", "webdriver_error")} for r in results]}
    (run_dir / "result.json").write_text(json.dumps(result, indent=1))
    text = summary_text(result)
    (run_dir / "summary.txt").write_text(text)
    print(text)
    log(f"wrote {run_dir.relative_to(REPO)}/result.json and summary.txt")
    log_f.close()
    return 0 if ok else 1
