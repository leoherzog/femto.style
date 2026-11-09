"""Command line for the browser harness. Run `uv run tests/run.py --help`."""
import argparse
import importlib.util
import signal
import subprocess
import sys

from .paths import REPO, STATIC_CHECKS

MODES_HELP = """modes:
  rig       start each browser and verify every mechanism the behavior and a11y modes rely on (exact
            viewports, color scheme and motion emulation, preload scripts, real input, screenshots,
            JavaScript off, cache clearing, held responses, and the loads log that criterion 15's
            checks read); writes results/<run>/rig.json.
  behavior  scripted checks of every widget and criterion 15's run-time loads (tests/behavior/;
            harness/behavior.py) against one target: --target dist, dist:<path> or a base URL;
            --groups, --checks, --browsers, --list; --expect-os-motion stops a Safari session whose
            OS prefers-reduced-motion is another.
  a11y      axe-core (node_modules/axe-core) in every page of one target (--target, default dist):
            /, /examples, the 404 page, /docs and /docs?theme=jade, in Chrome and Firefox,
            light and dark, at 375 and 1300 (criterion 10). A serious or critical violation fails.
  static    the static checks (tests/static_checks.py main; its own options).
"""


def parse(argv):
    ap = argparse.ArgumentParser(prog="uv run tests/run.py", description="femto.style browser harness",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=MODES_HELP)
    sub = ap.add_subparsers(dest="mode", required=True)
    from .rig import add_parser as add_rig_parser
    add_rig_parser(sub)
    from .behavior import add_parser as add_behavior_parser
    add_behavior_parser(sub)
    from .a11y import add_parser as add_a11y_parser
    add_a11y_parser(sub)
    sub.add_parser("static", help="the static checks (tests/static_checks.py; its own options)", add_help=False)
    return ap.parse_args(argv)


def git_info():
    def g(*a):
        try:
            return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:
            return ""
    return {"commit": g("rev-parse", "HEAD"), "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty_files": len(g("status", "--porcelain").splitlines())}


def run_static(argv):
    if not STATIC_CHECKS.exists():
        print(f"error: {STATIC_CHECKS.relative_to(REPO)} does not exist", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("static_checks", STATIC_CHECKS)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main(argv)


def _interrupt(signum, frame):
    # The first TERM unwinds like Ctrl-C; repeats (uv forwards the signal to the harness too) are
    # ignored, so the cleanup that writes the finished checks and stops every server runs to the end.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    raise KeyboardInterrupt(f"signal {signum}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # A TERM (a killed run) unwinds like Ctrl-C, so every server and browser is stopped.
    signal.signal(signal.SIGTERM, _interrupt)
    if argv and argv[0] == "static":
        return run_static(argv[1:])
    args = parse(argv)
    if args.mode == "behavior":
        from .behavior import run_behavior
        return run_behavior(args)
    if args.mode == "rig":
        from .rig import run_rig
        return run_rig(args)
    from .a11y import run_a11y
    return run_a11y(args)
