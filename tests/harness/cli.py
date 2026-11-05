"""Command line for the parity harness. Run `uv run tests/run.py --help`."""
import argparse
import contextlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from . import matrix
from .paths import MASKS, REPO, RESULTS, STATIC_CHECKS
from .registry import Registry
from .sections import ROOT_A
from .targets import Side, TargetError

MODES_HELP = """modes:
  rig       start each browser and verify every mechanism the harness relies on (widths, color
            schemes, pseudo-elements, screenshots, input); writes results/<run>/rig.json.
  self      the oracle against itself, two separate oracle servers (acceptance criterion 1).
            Fast axes; --full runs the PLAN.md matrix (Chrome, Firefox, Safari; light, dark; six
            widths; data-theme legs on the theme routes; kept routes only).
  pages     side A against side B, document against document: --a and --b are named targets
            (oracle, dist, static-femto, fixture[:control]; tests/harness/targets.json) or base URLs.
            The same target on both sides is a self comparison; side A static-femto makes it a
            one-page comparison (Phase 3). Fast axes; --full runs the PLAN.md matrix.
  fast      the agents' check: Chrome and Firefox at 375 and 1300, every leg the matrix gives a
            route. --self, or --a and --b.
  selftest  negative controls on the fixture site (tests/fixtures/) that prove detection.
  registry  validate tests/divergences/ and list the entries.
  oracle    build, serve and capture the oracle (tests/harness/oracle.py main; its own options).
  static    the static checks (tests/static_checks.py main; its own options).
  styles    the Phase 2 gate, femto's native mode on this site: --a (default static-multipage, the
            tag built by the harness) against --b (default dist), everything pages compares plus
            femto's tokens (surface, resolution, raw text) and interactive states replayed with
            real input (tests/harness/states.json, or --states FILE). Fast axes; --full runs the
            PLAN.md matrix. The same target on both sides is a self comparison.
  sections  the Phase 3 gate: each old docs route of --a (default static-femto, the tag built by the
            harness) against its section of the one docs page of --b (default dist): side A's
            [role=document] against the <section> around the element with the section's id, loaded
            at /docs#<id> (a color route: /docs?theme=<color>#version-picker). The routes and their
            sections come from side A's menu.json at the tag. Everything else is the pages mode's.
            Fast axes; --full runs the PLAN.md matrix.
  behavior  scripted checks of every widget (tests/behavior/; harness/behavior.py) against one target:
            --target oracle, dist, dist:<path> or a base URL; --groups, --checks, --browsers, --list.
  a11y      axe-core (node_modules/axe-core) in every page of one target (--target, default dist):
            /, /examples, /demo, the 404 page, /docs and /docs?theme=jade, in Chrome and Firefox,
            light and dark, at 375 and 1300 (criterion 10). A serious or critical violation fails.

Add --plan to self, pages, fast, styles or sections to print the planned cells per browser without
starting a server or a browser.
"""


def csv(s):
    return [x.strip() for x in s.split(",") if x.strip()] if s else []


def ints(s):
    return [int(x) for x in csv(s)]


def add_common(p):
    p.add_argument("--browsers", help="comma list of chrome, firefox, safari (default: the mode's)")
    p.add_argument("--routes", help="comma list of paths (default: the oracle's kept routes)")
    p.add_argument("--widths", help="comma list of iframe widths")
    p.add_argument("--schemes", help="comma list of legs (light, dark, theme-light, theme-dark) run on every route")
    p.add_argument("--no-shots", action="store_true", help="skip screenshots (the secondary pixel diff)")
    p.add_argument("--workers", help="sessions per browser, e.g. chrome=2,firefox=2 (Safari is always 1)")
    p.add_argument("--max-records", type=int, default=300, help="unregistered records kept per cell")
    p.add_argument("--run-id", help="name of the results folder (default: timestamp-mode-pid)")
    p.add_argument("--label", help="free text stored in result.json")
    p.add_argument("--registry", help="registry directory (default tests/divergences)")
    p.add_argument("--plan", action="store_true", help="print the planned cells and exit; starts nothing")
    p.add_argument("--max-documents", type=int,
                   help="restart the servers after this many documents per server (default: targets.json max_documents)")
    p.add_argument("--exact-blob-urls", dest="blob_uuid_placeholder", action="store_false",
                   help="compare blob: URLs exactly, UUID included (by default a blob: URL's UUID compares as a "
                        "placeholder: the owner's decision of 2026-10-30, tests/README.md Diff rule)")
    p.add_argument("--blob-uuid-placeholder", dest="blob_uuid_placeholder", action="store_true",
                   help="the default since 2026-10-30; still accepted so older commands run")
    p.set_defaults(blob_uuid_placeholder=True)
    p.add_argument("--exact-minified", dest="minified", action="store_false",
                   help="compare the oracle minifier's spellings exactly (by default a token's raw text compares "
                        "without leading zeros or the space after a comma, outline-width only under an outline-style "
                        "other than none, and 0px as 0%% in background positions: the owner's decision of 2026-11-02, "
                        "tests/README.md Diff rule)")
    p.set_defaults(minified=True)


def add_sides(p, required):
    p.add_argument("--a", required=required, help="side A: a named target or a base URL")
    p.add_argument("--b", required=required, help="side B: a named target or a base URL")
    p.add_argument("--ready-a", help="readiness hook for side A (oracle, static, none; default: the target's)")
    p.add_argument("--ready-b", help="readiness hook for side B")
    p.add_argument("--root-a", help="CSS selector of side A's alignment root (default: html)")
    p.add_argument("--root-b", help="CSS selector of side B's alignment root (default: html)")


def parse(argv):
    ap = argparse.ArgumentParser(prog="uv run tests/run.py", description="femto.style parity harness",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=MODES_HELP)
    sub = ap.add_subparsers(dest="mode", required=True)

    p = sub.add_parser("rig", help="verify browser mechanisms")
    p.add_argument("--browsers", default="chrome,firefox,safari")
    p.add_argument("--run-id")

    p = sub.add_parser("self", help="the oracle against itself")
    add_common(p)
    p.add_argument("--full", action="store_true", help="the PLAN.md matrix instead of the fast axes")
    p.add_argument("--one-server", action="store_true", help="serve both sides from one oracle server")

    p = sub.add_parser("pages", help="side A against side B")
    add_common(p)
    add_sides(p, required=True)
    p.add_argument("--full", action="store_true", help="the PLAN.md matrix instead of the fast axes")

    p = sub.add_parser("fast", help="the agents' check: Chrome and Firefox at 375 and 1300")
    add_common(p)
    add_sides(p, required=False)
    p.add_argument("--self", action="store_true", help="the oracle against itself")

    p = sub.add_parser("selftest", help="negative controls proving detection")
    p.add_argument("--browsers", help="default chrome,firefox")
    p.add_argument("--cases", help="comma list of control names")
    p.add_argument("--run-id")

    sub.add_parser("registry", help="validate the divergence registry")
    p = sub.add_parser("styles", help="the Phase 2 gate: tokens and interactive states on top of pages")
    add_common(p)
    p.add_argument("--a", default="static-multipage", help="side A: a named target or a base URL (default static-multipage)")
    p.add_argument("--b", default="dist", help="side B: a named target or a base URL (default dist)")
    p.add_argument("--ready-a", help="readiness hook for side A (oracle, static, none; default: the target's)")
    p.add_argument("--ready-b", help="readiness hook for side B")
    p.add_argument("--full", action="store_true", help="the PLAN.md matrix instead of the fast axes")
    p.add_argument("--states", help="state targets file (default tests/harness/states.json)")
    p.add_argument("--no-states", action="store_true", help="compare tokens but replay no interactive states")
    p = sub.add_parser("sections", help="the Phase 3 gate: each old docs route against its section of the one page")
    add_common(p)
    p.add_argument("--a", default="static-femto", help="side A: a named target with a menu (default static-femto)")
    p.add_argument("--b", default="dist", help="side B: a named target or a base URL serving the one page (default dist)")
    p.add_argument("--ready-a", help="readiness hook for side A (oracle, static, none; default: the target's)")
    p.add_argument("--ready-b", help="readiness hook for side B")
    p.add_argument("--root-a", default=ROOT_A, help=f"CSS selector of side A's alignment root (default {ROOT_A})")
    p.add_argument("--full", action="store_true", help="the PLAN.md matrix instead of the fast axes")
    from .behavior import add_parser as add_behavior_parser
    add_behavior_parser(sub)
    from .a11y import add_parser as add_a11y_parser
    add_a11y_parser(sub)
    return ap.parse_args(argv)


def git_info():
    def g(*a):
        try:
            return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    return {"commit": g("rev-parse", "HEAD"), "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": len(g("status", "--porcelain").splitlines())}


def os_scheme():
    """The macOS appearance, read only (agents never change it): 'dark' or 'light'."""
    try:
        out = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True, timeout=5)
        return "dark" if out.stdout.strip().lower() == "dark" else "light"
    except Exception:
        return "light"


def load_masks():
    return json.loads(MASKS.read_text())["masks"]


def make_opts(args, mode, full):
    workers = {"chrome": 1, "firefox": 1, "safari": 1}
    if full:
        workers.update(chrome=2, firefox=2)
    for kv in csv(getattr(args, "workers", None)):
        k, _, v = kv.partition("=")
        workers[k] = int(v)
    run_id = getattr(args, "run_id", None) or f"{time.strftime('%Y%m%d-%H%M%S')}-{mode}-{os.getpid()}"
    return SimpleNamespace(run_id=run_id, workers=workers, shots=not getattr(args, "no_shots", False),
                           max_records=getattr(args, "max_records", 300), masks=load_masks(), conf=matrix.load_config(),
                           blob_uuid=bool(getattr(args, "blob_uuid_placeholder", True)),
                           minified=bool(getattr(args, "minified", True)),
                           styles=getattr(args, "styles_mode", None))


def styles_describe(st):
    """result.json's record of the styles mode's settings (None in the other modes)."""
    if st is None:
        return None
    from . import styles
    return {"token_prefix": styles.TOKEN_PREFIX, "probe_properties": styles.PROBE_PROPS, "anchors": styles.ANCHORS,
            "states": st.states.describe() if st.states else None}


def styles_mode(args, caps):
    """The styles mode's settings (harness/styles.py): token configuration and the states file."""
    from . import styles
    states = None
    if getattr(args, "no_states", False):
        caps.append("--no-states: no interactive state is replayed (tokens and everything pages compares still are)")
    else:
        states = styles.States(Path(args.states).resolve() if args.states else styles.STATES)
        if args.states:
            caps.append(f"--states {args.states}: state targets from that file instead of tests/harness/states.json")
    return SimpleNamespace(states=states, configure_args=styles.configure_args)


def plan(args, mode, caps):
    """(cells, sides, comparison, full) for self, pages, fast, styles and sections. Starts nothing."""
    conf = matrix.load_config()
    comparison = "self" if mode == "self" or (mode == "fast" and getattr(args, "self", False)) else "pages"
    full = bool(getattr(args, "full", False))
    section_map = None
    if mode == "sections":
        # The same target on both sides is the mode's self check; otherwise a one-page comparison:
        # only the entries that name one-page apply (Divergence registry).
        from . import sections
        comparison = "self" if args.a == args.b else "one-page"
        sides = {"a": Side(args.a, args.ready_a, args.root_a), "b": Side(args.b, args.ready_b)}
        for s in sides.values():
            caps.extend(s.caps())
        section_map, where = sections.route_map(sides["a"])
        page = sections.one_page(sides["b"])
        sides["b"].root_note = f"the <{sections.SECTION}> around each cell's section id, on {page}"
        sides["a"].root_note = sections.graft_note()
        caps.append(f"sections: side A's root {args.root_a}, {sections.graft_note()} (tests/README.md, Sections)")
        n_var = sum(1 for _, c in section_map.values() if c)
        caps.append(f"sections: {len(section_map)} routes from side A's {where} ({len(section_map) - n_var} sections, "
                    f"{n_var} theme variants); side B's sections from {page}#<id>")
    elif mode == "styles":
        # The same target on both sides is the mode's self check: no registry entry but skipped checks applies.
        comparison = "self" if args.a == args.b else "styles"
        sides = {"a": Side(args.a, args.ready_a), "b": Side(args.b, args.ready_b)}
        for s in sides.values():
            caps.extend(s.caps())
    elif comparison == "self":
        if mode == "fast" and (args.a or args.b):
            raise SystemExit("fast takes --self or --a and --b, not both")
        sides = {"a": Side("oracle"), "b": Side("oracle")}
        if getattr(args, "one_server", False):
            sides["b"].share = "a"
            caps.append("self --one-server: both sides from one oracle server (no server restart covered)")
    else:
        if not (args.a and args.b):
            raise SystemExit(f"{mode} needs --a and --b" + (" (or --self)" if mode == "fast" else ""))
        sides = {"a": Side(args.a, args.ready_a, args.root_a), "b": Side(args.b, args.ready_b, args.root_b)}
        for s in sides.values():
            caps.extend(s.caps())
        # The same target on both sides is a self comparison, as in the styles mode; a side A that
        # names a comparison (static-femto: one-page) decides which registry entries apply.
        comparison = "self" if args.a == args.b else (sides["a"].conf.get("comparison") or "pages")
    browsers =csv(args.browsers) or (conf["browsers"] if full else conf["fast"]["browsers"])
    for b in browsers:
        if b not in ("chrome", "firefox", "safari"):
            raise SystemExit(f"unknown browser {b}")
    widths = ints(args.widths) or (conf["widths"] if full else conf["fast"]["widths"])
    legs = csv(args.schemes) or None
    for leg in legs or []:
        if leg not in matrix.LEGS:
            raise SystemExit(f"unknown scheme leg {leg}")
    theme_routes = conf["theme_routes"]
    if section_map is not None:
        routes = csv(args.routes) or list(section_map)
        unknown = [r for r in routes if r not in section_map]
        if unknown:
            raise SystemExit(f"not a docs route of side A's menu: {', '.join(unknown)} (compare a whole page with "
                             f"pages --a {args.a})")
    elif args.routes:
        routes = csv(args.routes)
    else:
        if any(s.kind == "fixture" for s in sides.values()):
            raise SystemExit("the fixture site has its own routes: name them with --routes (e.g. /index.html)")
        kept, dropped = matrix.oracle_routes()
        unknown = [r for r in theme_routes if r not in kept]
        if unknown:
            raise matrix.MatrixError(f"matrix.json theme_routes not among the kept routes: {', '.join(unknown)}")
        routes = kept
        caps.append(f"kept routes only: {len(kept)} routes; {len(dropped)} dropped routes left out (PLAN.md Decision 5): "
                    + ", ".join(dropped))
    cells = matrix.cells_for(browsers, routes, widths, theme_routes, legs)
    for c in cells:
        c["comparison"] = comparison
        if section_map is not None:
            c.update(sections.fields(*section_map[c["route"]], page, args.root_a))
    if not full:
        caps.append(f"fast axes (PLAN.md, Fast mode): browsers {', '.join(browsers)}; widths "
                    f"{', '.join(map(str, widths))}; --full runs the whole matrix")
    else:
        whole = matrix.cells_for(conf["browsers"], routes, conf["widths"], theme_routes)
        if len(cells) != len(whole) or args.routes:
            what = [f"--{k} {getattr(args, k)}" for k in ("browsers", "routes", "widths", "schemes") if getattr(args, k)]
            caps.append(f"command-line filters ({'; '.join(what)}) give {len(cells)} cells where the full matrix "
                        f"over these routes has {len(whole)}")
    if legs:
        caps.append(f"--schemes {','.join(legs)}: these legs on every route instead of the matrix's legs")
    if not getattr(args, "blob_uuid_placeholder", True):
        caps.append("--exact-blob-urls: blob: URLs compare exactly, so every /docs/colors cell reports its "
                    "Download link's href")
    if not getattr(args, "minified", True):
        caps.append("--exact-minified: the oracle minifier's spellings compare exactly, so a styles comparison "
                    "against a femto build reports them")
    return cells, sides, comparison, full


def print_plan(cells, caps, sides, comparison, full):
    counts = matrix.counts(cells)
    scheme = os_scheme()
    print(f"plan: {comparison}{' --full' if full else ''}, A {sides['a'].spec}, B {sides['b'].spec}: "
          f"{len(cells)} cells")
    for c in caps:
        print(f"cap: {c}")
    for b, d in counts.items():
        line = (f"  {b:7} {d['cells']:5} cells over {d['routes']} routes; legs "
                + ", ".join(f"{k} {v}" for k, v in d["by_leg"].items())
                + "; widths " + ", ".join(f"{k} {v}" for k, v in sorted(d["by_width"].items())))
        if b == "safari":
            other = "dark" if scheme == "light" else "light"
            skip = d["by_leg"].get(other, 0)
            line += (f"\n          macOS is {scheme} now: {skip} {other} cells are the registered skipped check "
                     f"media:{other}; {d['cells'] - skip} run (the owner's {other} pass runs the rest)")
        print(line)
    return 0


def cells_per_server_life(sides, override=None):
    """The most cells a run's servers may serve before they are restarted: each started target's
    max_documents (targets.json, or --max-documents) divided by the documents it serves per cell (2
    when both sides share one server). None when no target sets a limit."""
    limits = []
    for name, s in sides.items():
        if getattr(s, "share", None) or s.kind == "url":
            continue
        cap = override or (s.conf or {}).get("max_documents")
        if cap:
            per_cell = 1 + sum(1 for o in sides.values() if getattr(o, "share", None) == name)
            limits.append(max(1, int(cap) // per_cell))
    return min(limits) if limits else None


def run_compare(args, mode):
    from .browsers import users_safari_running
    from .report import build as build_result, summary
    from .runner import Pool, chunks
    from .targets import start
    caps = []
    try:
        cells, sides, comparison, full = plan(args, mode, caps)
        if mode == "styles":
            from .styles import StatesError
            try:
                args.styles_mode = styles_mode(args, caps)
            except StatesError as e:
                raise TargetError(f"states file: {e}") from None
        if args.plan:
            return print_plan(cells, caps, sides, comparison, full)
        for s in sides.values():
            s.check()
    except (matrix.MatrixError, TargetError, SystemExit) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    # A built folder a side serves (dist, dist:<path>) is a reference document set for the
    # registry's breadth rule too (registry.py, _reference_docs).
    dist_dirs = [s.dir for s in sides.values() if s.dir is not None]
    registry = Registry(Path(args.registry), dist_dirs=dist_dirs) if getattr(args, "registry", None) \
        else Registry(dist_dirs=dist_dirs)
    if registry.errors:
        print("registry errors:\n  " + "\n  ".join(registry.errors), file=sys.stderr)
    if not cells:
        print("error: no cells to run", file=sys.stderr)
        return 2
    if any(c["browser"] == "safari" for c in cells) and users_safari_running():
        print("error: the user's own Safari is running; quit it (Cmd-Q) before a Safari run", file=sys.stderr)
        return 2
    opts = make_opts(args, mode, full)
    run_dir = RESULTS / opts.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_f = open(run_dir / "log.txt", "a")

    def log(msg):
        line = f"{time.strftime('%H:%M:%S')} {msg}"
        print(line, flush=True)
        log_f.write(line + "\n")
        log_f.flush()

    for c in caps:
        log(f"cap: {c}")
    log(f"run {opts.run_id}: {comparison}, {len(cells)} cells; workers {opts.workers}; results in "
        f"{run_dir.relative_to(REPO)}")
    t0 = time.time()
    pool_errors, results, rigs = [], [], []
    size = cells_per_server_life(sides, getattr(args, "max_documents", None))
    parts = chunks(cells, size)
    if len(parts) > 1:
        log(f"servers restart every {size} cells at most (targets.json max_documents): {len(parts)} chunks of "
            + ", ".join(str(len(p)) for p in parts) + " cells")
    interrupted = False
    for k, part in enumerate(parts, 1):
        if len(parts) > 1:
            log(f"chunk {k}/{len(parts)}: {len(part)} cells, fresh servers and browser sessions")
        try:
            with contextlib.ExitStack() as stack:
                try:
                    for name in ("a", "b"):
                        s = sides[name]
                        if getattr(s, "share", None):
                            s.base = sides[s.share].base
                        else:
                            start(stack, s, log, run_dir)
                        log(f"side {name.upper()}: {s.spec} at {s.base} (ready: {s.ready}"
                            + (f", root {s.root}" if s.root else "")
                            + (f", root {s.root_note}" if s.root_note else "") + ")")
                except Exception as e:
                    log(f"error: cannot start the sides: {type(e).__name__}: {e}")
                    if k == 1:
                        log_f.close()
                        return 2
                    pool_errors.append(f"chunk {k}: cannot start the sides ({type(e).__name__}: {e}); "
                                       f"{sum(len(p) for p in parts[k - 1:])} cells never ran")
                    break
                pool = Pool(part, registry, opts, run_dir, sides, log, offset=len(results), grand_total=len(cells), t0=t0)
                try:
                    results += pool.run()
                except KeyboardInterrupt:
                    log("interrupted: stopping the workers, writing the cells that finished")
                    results += pool.stop()
                    pool.errors.append(f"interrupted after {len(results)} of {len(cells)} cells")
                    interrupted = True
                pool_errors += pool.errors
                rigs += pool.rigs
        except KeyboardInterrupt:
            pool_errors.append(f"interrupted while starting or stopping servers, after {len(results)} of {len(cells)} cells")
            interrupted = True
        finally:
            log("servers stopped")
        if interrupted:
            break
    run = {"run_id": opts.run_id, "mode": mode, "comparison": comparison, "full": full, "argv": sys.argv[1:],
           "label": getattr(args, "label", None),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0)), "duration_s": round(time.time() - t0, 1),
           "git": git_info(), "workers": opts.workers, "registry_files": registry.files,
           "sides": {k: s.describe() for k, s in sides.items()}, "masks": opts.masks,
           "server_chunks": {"cells_per_server_life": size, "chunks": [len(p) for p in parts]},
           "value_rules": getattr(opts, "value_rules", None),
           "styles": styles_describe(opts.styles),
           "planned": {b: {k: v for k, v in d.items()} for b, d in matrix.counts(cells).items()}}
    results.sort(key=lambda r: (r["browser"], r["route"], r["width"], r["scheme"]))
    result = build_result(run, results, registry, pool_errors, rigs, caps)
    (run_dir / "result.json").write_text(json.dumps(result, indent=1))
    text = summary(result)
    (run_dir / "summary.txt").write_text(text)
    print(text)
    log(f"wrote {run_dir.relative_to(REPO)}/result.json and summary.txt")
    log_f.close()
    return 0 if result["status"] == "PASS" else 1


def run_registry():
    reg = Registry()
    print(f"{len(reg.entries)} entries in {len(reg.files)} files: {', '.join(reg.files)}")
    for e in reg.entries:
        print(f"  {e.get('id')}: {e.get('kind')} {e.get('category')} ({e['_file']})")
    if reg.entries:
        print("by category: " + ", ".join(f"{k} {v}" for k, v in sorted(reg.by_category().items())))
    if reg.errors:
        print("errors:")
        for e in reg.errors:
            print(f"  {e}")
        return 1
    print("registry valid")
    return 0


def run_static(argv):
    if not STATIC_CHECKS.exists():
        print(f"error: {STATIC_CHECKS.relative_to(REPO)} does not exist yet", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("static_checks", STATIC_CHECKS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main(argv)


def _interrupt(signum, frame):
    # The first TERM unwinds like Ctrl-C; repeats (uv forwards the signal to the harness too) are
    # ignored, so the cleanup that writes the finished cells and stops every server runs to the end.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise KeyboardInterrupt(f"signal {signum}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # A TERM (a killed run) unwinds like Ctrl-C, so every server and browser is stopped.
    signal.signal(signal.SIGTERM, _interrupt)
    if argv and argv[0] == "oracle":
        from . import oracle
        return oracle.main(argv[1:])
    if argv and argv[0] == "static":
        return run_static(argv[1:])
    args = parse(argv)
    if args.mode == "registry":
        return run_registry()
    if args.mode == "behavior":
        from .behavior import run_behavior
        return run_behavior(args)
    if args.mode == "rig":
        from .rig import run_rig
        return run_rig(args)
    if args.mode == "selftest":
        from .negative import run_selftest
        return run_selftest(args)
    if args.mode == "a11y":
        from .a11y import run_a11y
        return run_a11y(args)
    try:
        return run_compare(args, args.mode)
    finally:
        from .browsers import quit_all
        quit_all()
