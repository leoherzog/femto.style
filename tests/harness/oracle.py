#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["selenium==4.52.0"]
# ///
"""The oracle: the Remix site at tag remix-final, built with its own locked toolchain and served the
way its "start" script serves it, as the parity reference (PLAN.md, Decision 6).

Public interface (tests/run.py imports this module as harness.oracle):

    ROUTES_FILE                      Path of tests/oracle-routes.json
    load_routes(kept_only=True)      list of {path, kind, kept, title}
    ensure_built(rebuild=False)      build the oracle if missing, stale or asked; returns the served dir
    serve(port=None)                 context manager yielding "http://127.0.0.1:<port>"
    wait_ready(driver, timeout=30)   hydrated, fonts loaded, two animation frames
    main(argv)                       the "oracle" mode: build, serve, capture every route

Standalone: uv run tests/harness/oracle.py [--rebuild] [--routes /,/docs/forms/input] [--no-shots]

Build. A detached git worktree of the tag at tests/oracle/worktree, "npx yarn@1.22.22 install
--frozen-lockfile" and "npm run build" under the Node on PATH (24.22.0 when written), falling back to
Node 20 and 18.19.0 if that fails: "npx -p node@<v> -p yarn@1.22.22 -- yarn install ..." and
"... -- yarn run build", so node and yarn come from one npx environment. FEMTO_ORACLE_NODE=<v>
(or "path") tries only that runtime, to test a fallback. tests/oracle/build.json records what was
used and a digest of the outputs. A build is stale when the tag moved, the worktree's HEAD, tracked
files or untracked (not ignored) files differ from the tag, an output is missing, or the digest of
public/, functions/, app/styles/css/ and the installed package versions changed; a rebuild starts
from "git clean -ffdx". build.lock: a build holds it exclusively, and every running serve() holds it
shared, so no process rebuilds (git checkout --force, git clean) under a live server.

Serve. The worktree's own wrangler (4.0.0, locked): "wrangler pages dev ./public --ip 127.0.0.1
--port <port> --compatibility-date=2023-06-21", plus --inspector-port on a free port (two servers
would otherwise both claim 9229) and --show-interactive-dev-session=false. wrangler and its workerd
children run in their own process group, which serve() terminates on exit.

Capture layout, tests/oracle/capture/<slug>/ (slug: the path without its outer slashes, "/" -> "--",
"" -> "index"; "/docs/forms/input" -> "docs--forms--input"):
    server.html      the raw HTTP body
    meta.json        status, response headers, title, stylesheets, screenshot sizes, console messages
    dom.html         document.documentElement.outerHTML after wait_ready(), viewport 1300x900
    dom-2.html       the same from a second, fresh browser session
    shot-375.png, shot-1300.png   full-page screenshots, light scheme, Chrome Beta headless
    dom-dark.html    the hydrated DOM again in the same session under prefers-color-scheme: dark
    dom-375.html     the hydrated DOM again at viewport 375x900, light
capture/_css/ holds each linked stylesheet once and capture/_fonts/ every font file a cross-origin
stylesheet references (Google Fonts' Pacifico on /docs/css-variables); capture/_run.json the run's
versions and settings; capture/_determinism.json every difference between the two DOM captures and
two HTTP fetches; capture/_variants.json every difference between dom.html and dom-dark.html or
dom-375.html (the markup the oracle's scripts make per color scheme and viewport).

Browser sessions honor femto's machine-wide locks (~/.cache/femto-harness/locks, same files and
protocol as femto's tests/harness/locks.py): one of FEMTO_HARNESS_SLOTS slots per session, and
driver-start.lock around WebDriver start-up. One session runs at a time.
"""
import argparse
import contextlib
import difflib
import fcntl
import json
import os
import random
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

__all__ = ["ROUTES_FILE", "load_routes", "ensure_built", "serve", "wait_ready", "main"]

_TESTS = Path(__file__).resolve().parent.parent
_REPO = _TESTS.parent
ROUTES_FILE = _TESTS / "oracle-routes.json"

_TAG = "remix-final"
_ORACLE = _TESTS / "oracle"
_WORKTREE = _ORACLE / "worktree"
_CAPTURE = _ORACLE / "capture"
_LOGS = _ORACLE / "logs"
_STAMP = _ORACLE / "build.json"
_YARN = "yarn@1.22.22"
_FALLBACK_NODES = ("20", "18.19.0")
_OUTPUT_DIRS = ("public", "functions", "app/styles/css")
_COMPAT_DATE = "2023-06-21"
_FORBIDDEN_PORTS = {8790}
_UNKNOWN_PATH = "/does-not-exist"
_V1_PATH = "/docs/v1/"
_DROPPED = {  # PLAN.md Decision 5
    "/docs/maintenance", "/docs/v2", "/docs/mission", "/docs/usage-scenarios", "/docs/brand",
    "/docs/built-with", "/docs/classless", "/docs/conditional", "/docs/sass", _V1_PATH,
}
_LANDING = ("/", "/examples", "/demo")
_DOM_VIEWPORT = (1300, 900)
_SHOT_WIDTHS = (1300, 375)  # 1300 first: the page is already loaded at the DOM viewport
_VIEWPORT_HEIGHT = 900

_CHROME_BINARY = os.environ.get("FEMTO_CHROME_BINARY",
                                "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta")
_LOCK_DIR = Path(os.environ.get("FEMTO_HARNESS_LOCK_DIR", Path.home() / ".cache" / "femto-harness" / "locks"))


def _log(msg: str) -> None:
    print(f"[oracle {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# -- routes -------------------------------------------------------------------------------------

def load_routes(kept_only: bool = True) -> list[dict]:
    """The oracle's routes from tests/oracle-routes.json: {path, kind, kept, title} each, in order."""
    data = json.loads(ROUTES_FILE.read_text())
    out = [{k: r[k] for k in ("path", "kind", "kept", "title")} for r in data["routes"]]
    return [r for r in out if r["kept"]] if kept_only else out


def _slug(path: str) -> str:
    return path.strip("/").replace("/", "--") or "index"


def _discover_paths(worktree: Path) -> list[str]:
    """Every page URL the tag serves: Remix flat routes (layouts excluded), the copied Pico v1 docs
    (/docs/v1/ and each of its static pages, extensionless as Pages serves them), and one unknown
    path for the 404 page. Order: landing pages, the docs menu, the color routes, /docs/v1/, its
    pages. Assets (stylesheets, scripts, images, fonts) are not listed."""
    stems = sorted(p.name[:-len(p.suffix)] for p in (worktree / "app" / "routes").iterdir()
                   if p.suffix in (".jsx", ".tsx", ".js", ".ts"))
    paths = []
    for stem in stems:
        if any(other.startswith(stem + ".") for other in stems):
            continue  # a layout (docs, docs.version-picker): its _index child serves its URL
        segs = [s for s in stem.split(".") if not s.startswith("_")]
        paths.append("/" + "/".join(segs))
    menu = json.loads((worktree / "app" / "data" / "documentationMenu.json").read_text())
    menu_order = [link["route"] for cat in menu for link in cat["links"]]
    landing = [p for p in _LANDING if p in paths]
    docs = [p for p in menu_order if p in paths]
    rest = sorted(p for p in paths if p not in landing and p not in docs)
    v1 = []
    if (worktree / "scripts" / "build-pico-v1-documentation.js").is_file():
        rest.append(_V1_PATH)  # build:v1-documentation copies @picocss/pico-v1's docs to public/docs/v1/
        v1 = [_V1_PATH + f.stem for f in sorted((worktree / "public" / "docs" / "v1").glob("*.html"))
              if f.name != "index.html"]
    return landing + docs + rest + v1 + [_UNKNOWN_PATH]


def _kind(path: str) -> str:
    if path == _UNKNOWN_PATH:
        return "404"
    if path.startswith(_V1_PATH) and path != _V1_PATH:
        return "v1-page"  # a static Pico v1 page: listed (an old path that must 404), never captured
    if path in _LANDING:
        return "landing"
    if path.startswith("/docs/version-picker/"):
        return "color"
    return "docs"


# -- locks (femto's protocol and files) ---------------------------------------------------------

@contextlib.contextmanager
def _flock(path: Path, label: str, waiting: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+")
    announced = 0.0
    try:
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - announced > 60:
                    f.seek(0)
                    _log(f"{waiting} (held by {f.read().strip() or '?'})")
                    announced = time.time()
                time.sleep(0.5 + random.random())
        f.seek(0)
        f.truncate()
        f.write(f"pid {os.getpid()} {label} since {time.strftime('%H:%M:%S')}\n")
        f.flush()
        yield
    finally:
        try:
            f.seek(0)
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)
        finally:
            f.close()


@contextlib.contextmanager
def _slot(label: str):
    """One of the machine-wide browser-session slots (femto's slot-<i>.lock files)."""
    try:
        n = max(1, int(os.environ.get("FEMTO_HARNESS_SLOTS", "4")))
    except ValueError:
        n = 4
    _LOCK_DIR.mkdir(parents=True, exist_ok=True)
    announced = 0.0
    while True:
        for i in random.sample(range(n), n):
            f = open(_LOCK_DIR / f"slot-{i}.lock", "a+")
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                f.close()
                continue
            try:
                f.seek(0)
                f.truncate()
                f.write(f"pid {os.getpid()} {label} since {time.strftime('%H:%M:%S')}\n")
                f.flush()
                yield i
            finally:
                f.seek(0)
                f.truncate()
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
            return
        if time.time() - announced > 60:
            _log(f"{label}: all {n} harness slots busy, waiting")
            announced = time.time()
        time.sleep(1 + random.random())


# -- build --------------------------------------------------------------------------------------

def _run(cmd, cwd: Path, check=True, log: Path | None = None, env=None) -> subprocess.CompletedProcess:
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as fh:
            fh.write(f"\n$ (cd {cwd}) {' '.join(map(str, cmd))}\n")
            fh.flush()
            p = subprocess.run(cmd, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, env=env, stdin=subprocess.DEVNULL)
    else:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    if check and p.returncode:
        detail = f"; see {log}" if log else f": {(p.stderr or p.stdout or '').strip()[-2000:]}"
        raise RuntimeError(f"{' '.join(map(str, cmd))} exited {p.returncode}{detail}")
    return p


def _git(*args, cwd: Path = _REPO, check=True) -> str:
    return _run(["git", *args], cwd, check=check).stdout.strip()


def _with_node(cmd: list[str], node: str | None) -> list[str]:
    """Run cmd under the Node on PATH (None) or under node@<node> fetched by npx."""
    return list(cmd) if node is None else ["npx", "--yes", "-p", f"node@{node}", "--", *cmd]


def _install_cmd(node: str | None) -> list[str]:
    """yarn install with the lockfile. Under a fetched Node, node and yarn come from one npx
    environment: "npx -p node@<v> -- npx yarn@<v>" fails there ("yarn@1.22.22: command not found")."""
    args = ["install", "--frozen-lockfile", "--non-interactive"]
    if node is None:
        return ["npx", "--yes", _YARN, *args]
    return ["npx", "--yes", "-p", f"node@{node}", "-p", _YARN, "--", "yarn", *args]


def _build_cmd(node: str | None) -> list[str]:
    if node is None:
        return ["npm", "run", "build"]
    # The system npm (11) refuses to support Node 18; yarn runs the scripts under the fetched Node.
    return ["npx", "--yes", "-p", f"node@{node}", "-p", _YARN, "--", "yarn", "run", "build"]


def _runtimes() -> tuple:
    """The runtimes ensure_built tries, in order: PATH, then the fallbacks, or FEMTO_ORACLE_NODE's."""
    forced = os.environ.get("FEMTO_ORACLE_NODE", "").strip()
    if not forced:
        return (None, *_FALLBACK_NODES)
    return (None,) if forced.lower() == "path" else (forced,)


def install_and_build(wt: Path, node: str | None, env: dict | None = None, logs: Path | None = None) -> dict:
    """Install and build the checkout wt under one runtime; never raises for a failed command.
    Returns {"ok", "label", "install_s", "build_s", "error"}."""
    env = env or _env()
    logs = logs or _LOGS
    label = "PATH" if node is None else f"node@{node}"
    out = {"ok": False, "label": label, "install_s": None, "build_s": None, "error": None}
    log = logs / f"install-{label}.log"
    log.unlink(missing_ok=True)
    t0 = time.time()
    p = _run(_install_cmd(node), wt, check=False, log=log, env=env)
    out["install_s"] = round(time.time() - t0, 1)
    if p.returncode:
        out["error"] = f"{label}: install exited {p.returncode} ({log})"
        return out
    log = logs / f"build-{label}.log"
    log.unlink(missing_ok=True)
    t0 = time.time()
    p = _run(_build_cmd(node), wt, check=False, log=log, env=env)
    out["build_s"] = round(time.time() - t0, 1)
    if p.returncode:
        out["error"] = f"{label}: build exited {p.returncode} ({log})"
        return out
    out["ok"] = True
    return out


def _env() -> dict:
    env = dict(os.environ)
    env.setdefault("WRANGLER_SEND_METRICS", "false")
    env.pop("NODE_OPTIONS", None)
    return env


def _read_stamp() -> dict:
    try:
        return json.loads(_STAMP.read_text())
    except (OSError, ValueError):
        return {}


def _outputs_digest(wt: Path) -> str:
    """sha256 over the build's outputs (every file under public/, functions/ and app/styles/css/,
    by path and content) and the installed packages (each node_modules package's name and version,
    and yarn's integrity file). About 0.2 s."""
    import hashlib
    h = hashlib.sha256()
    for d in _OUTPUT_DIRS:
        for f in sorted((wt / d).rglob("*")):
            if f.is_file():
                h.update(f"{f.relative_to(wt)}\0".encode())
                h.update(f.read_bytes())
    nm = wt / "node_modules"
    integrity = nm / ".yarn-integrity"
    h.update(integrity.read_bytes() if integrity.is_file() else b"no .yarn-integrity")
    for pj in sorted([*nm.glob("*/package.json"), *nm.glob("@*/*/package.json")]):
        try:
            version = json.loads(pj.read_bytes()).get("version")
        except (OSError, ValueError):
            version = None
        h.update(f"{pj.parent.relative_to(nm)}@{version}\n".encode())
    return h.hexdigest()


def _stale_reason(commit: str) -> str | None:
    wt = _WORKTREE
    if not (wt / ".git").is_file():
        return "no worktree"
    head = _git("rev-parse", "HEAD", cwd=wt, check=False)
    if head != commit:
        return f"worktree HEAD {head[:9]} is not {_TAG} {commit[:9]}"
    stamp = _read_stamp()
    if stamp.get("commit") != commit or not stamp.get("ok"):
        return "no successful build recorded for this commit"
    changed = _git("status", "--porcelain", "--untracked-files=normal", cwd=wt, check=False)
    if changed:
        return f"files differ from the tag (tracked, or untracked and not ignored): {changed.splitlines()[:3]}"
    needed = [wt / "functions" / "[[path]].js", wt / "public" / "docs" / "v1" / "index.html",
              wt / "node_modules" / ".bin" / "wrangler", wt / "app" / "data" / "stats.json"]
    missing = [str(p.relative_to(wt)) for p in needed if not p.exists()]
    if not any((wt / "public" / "build").glob("manifest-*.js")):
        missing.append("public/build/manifest-*.js")
    if missing:
        return f"missing outputs: {', '.join(missing)}"
    digest = _outputs_digest(wt)
    if stamp.get("outputs_digest") != digest:
        return (f"the outputs or installed packages changed since the build (digest {digest[:12]}, "
                f"build.json {str(stamp.get('outputs_digest'))[:12]})")
    return None


def _prepare_worktree(commit: str) -> None:
    wt = _WORKTREE
    if not (wt / ".git").is_file():
        _git("worktree", "prune")
        if wt.exists():
            if _ORACLE not in wt.resolve().parents:
                raise RuntimeError(f"refusing to remove {wt}")
            shutil.rmtree(wt)
        _ORACLE.mkdir(parents=True, exist_ok=True)
        _git("worktree", "add", "--detach", str(wt), commit)
    else:
        _git("checkout", "--detach", "--force", commit, cwd=wt)
        _git("clean", "-ffdxq", cwd=wt)


def _versions(wt: Path, node: str | None) -> dict:
    out = {"node": _run(_with_node(["node", "--version"], node), wt).stdout.strip()}
    for pkg in ("wrangler", "@remix-run/dev", "react", "react-dom", "sass", "miniflare"):
        try:
            out[pkg] = json.loads((wt / "node_modules" / pkg / "package.json").read_text())["version"]
        except (OSError, ValueError, KeyError):
            out[pkg] = None
    return out


_BUILD_LOCK = _ORACLE / "build.lock"
_serving = 0  # oracle servers this process is running (each holds build.lock shared)


@contextlib.contextmanager
def _build_lock(shared: bool, label: str):
    """build.lock: exclusive for a build, shared for a running server or a freshness check."""
    _BUILD_LOCK.parent.mkdir(parents=True, exist_ok=True)
    f = open(_BUILD_LOCK, "a+")
    mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
    announced = 0.0
    try:
        while True:
            try:
                fcntl.flock(f, mode | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - announced > 60:
                    _log(f"{label}: waiting for build.lock ("
                         + ("an oracle build is running" if shared else "oracle servers or another build hold it") + ")")
                    announced = time.time()
                time.sleep(0.5 + random.random())
        yield
    finally:
        try:
            fcntl.flock(f, fcntl.LOCK_UN)
        finally:
            f.close()


def ensure_built(rebuild: bool = False) -> Path:
    """Build the oracle from tag remix-final if missing, stale or asked; return the directory served
    (the worktree's public/, served with the worktree's functions/ by wrangler pages dev). A build
    waits until no oracle server runs (they hold build.lock shared)."""
    commit = _git("rev-parse", f"{_TAG}^{{commit}}")
    if not rebuild:
        with _build_lock(True, "oracle freshness check"):
            if _stale_reason(commit) is None:
                return _WORKTREE / "public"
    if _serving:
        raise RuntimeError(f"the oracle needs a rebuild ({'--rebuild' if rebuild else _stale_reason(commit)}), but this "
                           f"process is serving it ({_serving} servers); stop them first")
    with _build_lock(False, "oracle build"):
        reason = "--rebuild" if rebuild else _stale_reason(commit)
        if reason is None:
            return _WORKTREE / "public"
        _log(f"building the oracle from {_TAG} ({commit[:9]}): {reason}")
        _STAMP.unlink(missing_ok=True)
        _prepare_worktree(commit)
        env = _env()
        attempts = []
        for node in _runtimes():
            res = install_and_build(_WORKTREE, node, env)
            label, install_s, build_s = res["label"], res["install_s"], res["build_s"]
            if res["ok"]:
                break
            attempts.append(res["error"])
            _log(f"oracle build failed under {label}; {attempts[-1]}")
            _git("clean", "-ffdxq", cwd=_WORKTREE)
        else:
            raise RuntimeError("the oracle did not build: " + "; ".join(attempts))
        changed = _git("status", "--porcelain", cwd=_WORKTREE, check=False)
        stamp = {
            "ok": True, "tag": _TAG, "commit": commit, "runtime": node, "yarn": _YARN,
            "install_s": install_s, "build_s": build_s, "built": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "versions": _versions(_WORKTREE, node), "failed_attempts": attempts,
            "stats": json.loads((_WORKTREE / "app" / "data" / "stats.json").read_text()),
            "worktree_changes_after_build": changed.splitlines(),
            "outputs_digest": _outputs_digest(_WORKTREE),
        }
        _STAMP.write_text(json.dumps(stamp, indent=2) + "\n")
        reason = _stale_reason(commit)
        if reason:
            raise RuntimeError(f"oracle build finished but is not usable: {reason}")
        _log(f"oracle built under {label} ({stamp['versions']['node']}): install {install_s} s, build {build_s} s")
        return _WORKTREE / "public"


# -- serve --------------------------------------------------------------------------------------

def _free_port() -> int:
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port not in _FORBIDDEN_PORTS:
            return port


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextlib.contextmanager
def serve(port: int | None = None):
    """Serve the oracle with its locked wrangler pages dev; yield "http://127.0.0.1:<port>".
    On exit, stop wrangler and every child (workerd, esbuild): they share one process group. The
    server holds build.lock shared for its whole life, so no other process rebuilds under it."""
    global _serving
    with contextlib.ExitStack() as held:
        while True:
            ensure_built()
            held.enter_context(_build_lock(True, "oracle server"))
            # A build may have run between the check and the lock: check again under the lock.
            if _stale_reason(_git("rev-parse", f"{_TAG}^{{commit}}")) is None:
                break
            held.close()
        _serving += 1
        try:
            with _serve_built(port) as base:
                yield base
        finally:
            _serving -= 1


@contextlib.contextmanager
def _serve_built(port: int | None):
    if port is None:
        port = _free_port()
    if port in _FORBIDDEN_PORTS:
        raise ValueError(f"port {port} is reserved")
    inspector = _free_port()
    while inspector == port:
        inspector = _free_port()
    node = _read_stamp().get("runtime")
    cmd = _with_node([str(_WORKTREE / "node_modules" / ".bin" / "wrangler"), "pages", "dev", "./public",
                      "--ip", "127.0.0.1", "--port", str(port), f"--compatibility-date={_COMPAT_DATE}",
                      "--inspector-port", str(inspector), "--show-interactive-dev-session=false"], node)
    _LOGS.mkdir(parents=True, exist_ok=True)
    log_path = _LOGS / f"serve-{port}.log"
    log = open(log_path, "w")
    # wrangler writes a debug log of its own on every run, and 4.0.0's inspector proxy echoes every
    # DevTools event of the worker into it (about 300 MB per 1,200 page loads). Keep it beside the
    # serve log, inside the gitignored tests/oracle/, instead of ~/Library/Preferences/.wrangler/logs,
    # and delete it when the server ran until it was stopped (it is kept when wrangler exited early).
    debug_log = _LOGS / f"wrangler-debug-{port}.log"
    env = _env()
    env["WRANGLER_LOG_PATH"] = str(debug_log)
    proc = subprocess.Popen(cmd, cwd=_WORKTREE, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            env=env, start_new_session=True)
    pgid = proc.pid
    base = f"http://127.0.0.1:{port}"
    exited_early = True
    try:
        deadline = time.time() + 120
        while True:
            if proc.poll() is not None:
                raise RuntimeError(f"wrangler exited {proc.returncode} before answering; see {log_path}:\n"
                                   + log_path.read_text()[-2000:])
            try:
                with urllib.request.urlopen(base + "/", timeout=5) as r:
                    if r.status == 200:
                        break
            except (urllib.error.URLError, OSError):
                pass
            if time.time() > deadline:
                raise RuntimeError(f"wrangler did not answer on {base} within 120 s; see {log_path}")
            time.sleep(0.25)
        yield base
    finally:
        exited_early = proc.poll() is not None
        for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            if not _group_alive(pgid):
                break
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                break
            end = time.time() + wait
            while time.time() < end:
                try:
                    proc.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass
                if not _group_alive(pgid):
                    break
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        log.close()
        if not exited_early:
            debug_log.unlink(missing_ok=True)
        if _group_alive(pgid):
            raise RuntimeError(f"oracle server process group {pgid} survived SIGKILL")


# -- readiness ----------------------------------------------------------------------------------

_HYDRATION_JS = r"""
const b = document.body;
const s = {readyState: document.readyState, remix: !!window.__remixContext};
if (!b || document.readyState !== 'complete') return Object.assign(s, {ok: false, why: 'loading'});
if (!s.remix) return Object.assign(s, {ok: true, why: 'not a Remix page'});
const r = window.__remixRouter;
s.router = !!r;
if (!r || !r.state || !r.state.initialized || r.state.navigation.state !== 'idle')
  return Object.assign(s, {ok: false, why: 'router not initialized'});
s.fiber = Object.keys(b).some(k => k.startsWith('__reactFiber$'));
if (!s.fiber) return Object.assign(s, {ok: false, why: 'body not hydrated'});
// Body.jsx: use100vh() renders "100vh" on the server and the first client render, then an effect
// sets innerHeight in px. A px value proves hydration committed and its effects ran.
s.minHeight = b.style.minHeight;
if (/vh$/.test(b.style.minHeight)) return Object.assign(s, {ok: false, why: 'effects not run'});
return Object.assign(s, {ok: true, why: 'hydrated'});
"""

_SETTLE_JS = r"""
const done = arguments[arguments.length - 1];
const ms = arguments[0];
const frame = () => new Promise(res => {
  let fired = false;
  const go = how => { if (!fired) { fired = true; res(how); } };
  requestAnimationFrame(() => go('raf'));
  setTimeout(() => go('timer'), 100);   // rAF never runs on a hidden page (locked-screen Safari)
});
const timeout = new Promise(res => setTimeout(() => res('timeout'), ms));
const fonts = document.fonts ? document.fonts.ready.then(() => 'fonts') : Promise.resolve('no FontFaceSet');
Promise.race([fonts, timeout]).then(f => f === 'timeout' ? [f] : frame().then(a => frame().then(b => [f, a, b])))
  .then(r => done({result: r, fonts: document.fonts ? document.fonts.status : null}),
        e => done({error: String(e && e.stack || e)}));
"""


def wait_ready(driver, timeout: float = 30) -> None:
    """Wait until the oracle page in `driver` has hydrated (Remix router initialized, React attached
    to <body>, Body's use100vh effect run), document.fonts.ready has resolved and two animation
    frames have passed (a 100 ms timer stands in for a frame when rAF does not run). A page without
    Remix (the Pico v1 docs, a static page) counts as hydrated once loaded. Raises TimeoutError."""
    deadline = time.time() + timeout
    state = None
    while True:
        try:
            state = driver.execute_script(_HYDRATION_JS)
        except Exception as e:  # a navigation in flight replaces the document
            state = {"ok": False, "why": f"script error: {type(e).__name__}"}
        if state and state.get("ok"):
            break
        if time.time() > deadline:
            raise TimeoutError(f"oracle page not hydrated within {timeout} s: {state}")
        time.sleep(0.05)
    remaining_ms = max(1000, int((deadline - time.time()) * 1000))
    res = driver.execute_async_script(_SETTLE_JS, remaining_ms)
    if not res or res.get("error"):
        raise RuntimeError(f"oracle page did not settle: {res}")
    if res["result"][0] == "timeout":
        raise TimeoutError(f"document.fonts.ready did not resolve within {timeout} s (status {res.get('fonts')})")


# -- capture ------------------------------------------------------------------------------------

def _http_get(url: str, user_agent: str = "femto.style-oracle") -> tuple[int, list, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=60) as r:
            return r.status, list(r.headers.items()), r.read()
    except urllib.error.HTTPError as e:
        return e.code, list(e.headers.items()), e.read()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _title(html: str) -> str | None:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if not m:
        return None
    import html as _html
    return _html.unescape(m.group(1)).strip()


def _png_size(data: bytes) -> tuple[int, int]:
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _chrome():
    from selenium import webdriver
    o = webdriver.ChromeOptions()
    o.binary_location = _CHROME_BINARY
    for a in ("--headless", f"--window-size={_DOM_VIEWPORT[0]},{_VIEWPORT_HEIGHT}", "--force-device-scale-factor=1",
              "--no-first-run", "--no-default-browser-check", "--disable-search-engine-choice-screen",
              "--force-color-profile=srgb", "--hide-scrollbars", "--disable-background-timer-throttling",
              "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows"):
        o.add_argument(a)
    o.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    with _flock(_LOCK_DIR / "driver-start.lock", "oracle chrome", "oracle: waiting to start a driver"):
        d = webdriver.Chrome(options=o)
    try:
        d.set_page_load_timeout(60)
        d.set_script_timeout(90)
        d.execute_cdp_cmd("Emulation.setFocusEmulationEnabled", {"enabled": True})
        d.execute_cdp_cmd("Emulation.setEmulatedMedia",
                          {"features": [{"name": "prefers-color-scheme", "value": "light"}]})
    except Exception:
        d.quit()
        raise
    return d


def _viewport(driver, width: int) -> None:
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",
                           {"width": width, "height": _VIEWPORT_HEIGHT, "deviceScaleFactor": 1, "mobile": False})


def _scheme(driver, dark: bool) -> None:
    driver.execute_cdp_cmd("Emulation.setEmulatedMedia",
                           {"features": [{"name": "prefers-color-scheme", "value": "dark" if dark else "light"}]})


def _load(driver, url: str, width: int, base: str, dark: bool = False) -> list[dict]:
    """Load url at the given viewport width and color scheme, wait until ready; return console messages."""
    _viewport(driver, width)
    try:
        driver.get_log("browser")  # drain
    except Exception:
        pass
    driver.get(url)
    wait_ready(driver)
    got = driver.execute_script("return [innerWidth, matchMedia('(prefers-color-scheme: dark)').matches]")
    if got != [width, dark]:
        raise RuntimeError(f"viewport or scheme not as set at {url}: innerWidth/dark = {got}")
    try:
        entries = driver.get_log("browser")
    except Exception:
        entries = []
    return [{"level": e.get("level"), "message": e.get("message", "").replace(base, "")} for e in entries]


def _full_page_png(driver) -> bytes:
    import base64
    driver.execute_script("window.scrollTo(0, 0)")
    m = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
    size = m.get("cssContentSize") or m["contentSize"]
    w, h = int(-(-size["width"] // 1)), int(-(-size["height"] // 1))
    shot = driver.execute_cdp_cmd("Page.captureScreenshot", {
        "format": "png", "captureBeyondViewport": True, "fromSurface": True,
        "clip": {"x": 0, "y": 0, "width": w, "height": h, "scale": 1}})
    return base64.b64decode(shot["data"])


_STYLESHEETS_JS = r"""
return [...document.querySelectorAll('link[rel~="stylesheet"]')].map(l => ({
  href: l.getAttribute('href'), url: l.href, media: l.getAttribute('media')}))
  .concat([{inline_style_elements: document.querySelectorAll('style').length}]);
"""

_FONT_URL = re.compile(rb"url\(\s*['\"]?(https?://[^'\")\s]+\.(?:woff2|woff|ttf|otf))['\"]?\s*\)", re.I)
_VARIANTS = (("dark", "dom-dark.html", "prefers-color-scheme: dark, 1300x900"), ("375", "dom-375.html", "375x900, light"))

_TOKEN = re.compile(r"<!--.*?-->|<[^>]*>|[^<]+", re.S)
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


def _tokens_with_paths(html: str) -> tuple[list[str], list[str]]:
    toks, paths, stack = [], [], []
    for m in _TOKEN.finditer(html):
        t = m.group(0)
        toks.append(t)
        paths.append(" > ".join(stack[-6:]))
        if t.startswith("</"):
            name = t[2:-1].strip().lower()
            while stack:
                if stack.pop().split("#")[0].split(".")[0] == name:
                    break
        elif t.startswith("<!") or not t.startswith("<") or t.endswith("/>"):
            continue
        else:
            nm = re.match(r"<([a-zA-Z][\w:-]*)", t)
            if not nm or nm.group(1).lower() in _VOID:
                continue
            label = nm.group(1).lower()
            idm = re.search(r'\sid="([^"]*)"', t)
            clm = re.search(r'\sclass="([^"]*)"', t)
            if idm:
                label += "#" + idm.group(1)
            if clm:
                label += "".join("." + c for c in clm.group(1).split()[:3])
            stack.append(label)
    return toks, paths


def _clip(s: str, n: int = 400) -> str:
    return s if len(s) <= n else s[:n] + f"... ({len(s)} chars)"


def _diff(a: str, b: str) -> list[dict]:
    ta, pa = _tokens_with_paths(a)
    tb, _ = _tokens_with_paths(b)
    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    hunks = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        hunks.append({"op": op, "where": pa[i1] if i1 < len(pa) else (pa[-1] if pa else ""),
                      "first": _clip("".join(ta[i1:i2])), "second": _clip("".join(tb[j1:j2]))})
    return hunks


def _classify(route: dict, hunk: dict) -> str:
    """PLAN expects only the typing demo, spinners and the random progress value to vary."""
    text = hunk["first"] + hunk["second"]
    if route["path"] in ("/", "/demo") and ("div.demo" in hunk["where"] or "data-typeit-id" in text):
        return "expected: typing demo"  # TypeIt's text, cursor and its <style id=random> in <head>
    if route["path"] == "/docs/progress" and (
            "<progress" in text or all(re.fullmatch(r"\d+", hunk[k]) for k in ("first", "second"))):
        return "expected: random progress value"  # the <progress value> and its echo in the code sample
    return "UNEXPECTED"


def _write_routes_file(paths: list[str], titles: dict, commit: str) -> None:
    routes = [{"path": p, "kind": _kind(p), "kept": p not in _DROPPED and _kind(p) != "v1-page", "title": titles.get(p)}
              for p in paths]
    ROUTES_FILE.write_text(json.dumps({"tag": _TAG, "commit": commit, "routes": routes}, indent=2,
                                      ensure_ascii=False) + "\n")


def _write_variants(selected: list[dict], commit: str) -> dict:
    """capture/_variants.json: the markup the oracle's scripts make per color scheme and viewport,
    dom.html (1300, light) against dom-dark.html and dom-375.html for each route. Phase 1's
    converters rebuild these in JavaScript. Hunks the determinism check expects (the typing demo,
    the progress value) or a blob: URL are marked nondeterministic; the rest are "variant", and the
    summary groups them by change with hrefs left out, so one change on many routes is one line."""
    variants = {"tag": _TAG, "commit": commit, "base": "dom.html (1300x900, light)",
                "variants": {k: f"{f} ({how})" for k, f, how in _VARIANTS}, "routes": {}, "summary": {}}
    for r in selected:
        d = _CAPTURE / _slug(r["path"])
        if not (d / "dom.html").exists():
            continue
        dom1 = (d / "dom.html").read_text()
        for key, fname, _how in _VARIANTS:
            if not (d / fname).exists():
                continue
            hunks = _diff(dom1, (d / fname).read_text())
            for h in hunks:
                cls = _classify(r, h)
                if cls == "UNEXPECTED" and "blob:" in h["first"] and "blob:" in h["second"]:
                    h["class"] = "nondeterministic: blob: URL (random per document; _determinism.json)"
                elif cls.startswith("expected"):
                    h["class"] = "nondeterministic: " + cls.split(": ", 1)[1] + " (masked; its markup may also vary here)"
                else:
                    h["class"] = "variant"
            if hunks:
                variants["routes"].setdefault(r["path"], {})[key] = hunks
            for h in hunks:
                if h["class"] == "variant":
                    ctx = re.sub(r'\s(href|d)="[^"]*"', r' \1="…"', h["first"] + " => " + h["second"])
                    ctx = re.sub(r"\s+", " ", ctx)[:200]
                    variants["summary"].setdefault(key, {}).setdefault(ctx, []).append(r["path"])
    for key in list(variants["summary"]):
        variants["summary"][key] = [{"change": c, "routes": len(rs), "examples": rs[:3]}
                                    for c, rs in sorted(variants["summary"][key].items(), key=lambda x: -len(x[1]))]
    (_CAPTURE / "_variants.json").write_text(json.dumps(variants, indent=2, ensure_ascii=False) + "\n")
    return variants


def main(argv: list[str] | None = None) -> int:
    """The "oracle" mode: build if needed, serve, capture every route (or --routes) into
    tests/oracle/capture/, then capture each route's DOM again in a fresh session and diff."""
    ap = argparse.ArgumentParser(prog="oracle", description="Build, serve and capture the remix-final oracle.")
    ap.add_argument("--rebuild", action="store_true", help="rebuild from a clean worktree even if fresh")
    ap.add_argument("--routes", action="append", default=[],
                    help="comma-separated paths or slugs to capture (repeatable); default: every route")
    ap.add_argument("--no-shots", action="store_true", help="skip screenshots")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    t_start = time.time()
    errors: list[str] = []      # the capture is incomplete or inconsistent: exit 1
    warnings: list[str] = []    # facts about the oracle worth knowing (overflow, third-party CSS)

    served = ensure_built(args.rebuild)
    stamp = _read_stamp()
    commit = stamp["commit"]
    discovered = _discover_paths(_WORKTREE)

    if ROUTES_FILE.exists():
        data = json.loads(ROUTES_FILE.read_text())
        listed = [r["path"] for r in data["routes"]]
        if data.get("commit") != commit:
            errors.append(f"{ROUTES_FILE.name} names commit {data.get('commit')}, the tag is {commit}")
        if set(listed) != set(discovered):
            errors.append(f"{ROUTES_FILE.name} differs from the routes the tag serves: "
                          f"missing {sorted(set(discovered) - set(listed))}, extra {sorted(set(listed) - set(discovered))}")
        routes = load_routes(kept_only=False)
    else:
        routes = [{"path": p, "kind": _kind(p), "kept": p not in _DROPPED, "title": None} for p in discovered]

    v1_pages = [r for r in routes if r["kind"] == "v1-page"]
    routes = [r for r in routes if r["kind"] != "v1-page"]
    if v1_pages:
        _log(f"cap: {len(v1_pages)} static Pico v1 pages are listed in {ROUTES_FILE.name} (old paths for criterion 6) "
             f"and checked for status 200, not captured")
    wanted = [w.strip() for arg in args.routes for w in arg.split(",") if w.strip()]
    if wanted:
        known = {r["path"]: r for r in routes} | {_slug(r["path"]): r for r in routes}
        unknown = [w for w in wanted if w not in known]
        if unknown:
            print(f"unknown routes: {unknown}", file=sys.stderr)
            return 2
        selected = list({known[w]["path"]: known[w] for w in wanted}.values())
    else:
        selected = routes
        if _CAPTURE.exists():
            shutil.rmtree(_CAPTURE)
    _CAPTURE.mkdir(parents=True, exist_ok=True)
    css_dir = _CAPTURE / "_css"
    css_dir.mkdir(exist_ok=True)
    _log(f"capturing {len(selected)} routes from {served}")

    determinism = {"tag": _TAG, "commit": commit, "routes": [r["path"] for r in selected],
                   "dom": {}, "server": {}, "expected": {}, "unexpected": {}}
    titles: dict[str, str | None] = {}
    run_info: dict = {}
    from selenium import __version__ as selenium_version

    with serve() as base:
        run_info["base"] = base
        # 1. Raw HTTP, fetched twice
        for r in selected:
            slug, d = _slug(r["path"]), _CAPTURE / _slug(r["path"])
            if d.exists():
                shutil.rmtree(d)  # each run replaces the folders of the routes it captures
            d.mkdir(parents=True)
            status, headers, body = _http_get(base + r["path"])
            status2, _, body2 = _http_get(base + r["path"])
            (d / "server.html").write_bytes(body)
            text = body.decode("utf-8", "replace")
            title = _title(text)
            titles[r["path"]] = title
            want = 404 if r["kind"] == "404" else 200
            if status != want or status2 != want:
                errors.append(f"{r['path']}: HTTP {status}/{status2}, expected {want}")
            if r.get("title") is not None and title != r["title"]:
                errors.append(f"{r['path']}: title {title!r}, {ROUTES_FILE.name} says {r['title']!r}")
            if body != body2:
                hunks = _diff(text, body2.decode("utf-8", "replace"))
                for h in hunks:
                    h["class"] = _classify(r, h)
                determinism["server"][r["path"]] = hunks
            meta = {"path": r["path"], "slug": slug, "kind": r["kind"], "kept": r["kept"], "status": status,
                    "headers": headers, "title": title}
            (d / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        v1_status = {}
        if not wanted:
            for r in v1_pages:
                status, _, _ = _http_get(base + r["path"])
                v1_status[r["path"]] = status
                if status != 200:
                    errors.append(f"{r['path']}: HTTP {status}, expected 200 (a static Pico v1 page)")
            run_info["v1_pages"] = v1_status
        _log("HTTP pass done")
        if not ROUTES_FILE.exists():
            for p in discovered:
                if p not in titles:
                    titles[p] = _title(_http_get(base + p)[2].decode("utf-8", "replace"))
            _write_routes_file(discovered, titles, commit)
            _log(f"wrote {ROUTES_FILE}")

        # 2. Browser pass 1: hydrated DOM at 1300, screenshots at 375 and 1300
        css_urls: dict[str, str] = {}
        with _slot("oracle capture pass 1"):
            driver = _chrome()
            try:
                caps = driver.capabilities
                run_info["chrome"] = caps.get("browserVersion")
                run_info["chromedriver"] = (caps.get("chrome") or {}).get("chromedriverVersion", "").split(" ")[0]
                user_agent = run_info["user_agent"] = driver.execute_script("return navigator.userAgent")
                for n, r in enumerate(selected, 1):
                    d = _CAPTURE / _slug(r["path"])
                    meta = json.loads((d / "meta.json").read_text())
                    url = base + r["path"]
                    try:
                        console = _load(driver, url, _DOM_VIEWPORT[0], base)
                        dom = driver.execute_script("return document.documentElement.outerHTML")
                        (d / "dom.html").write_text(dom)
                        meta["dom_title"] = driver.title
                        meta["dom_viewport"] = list(_DOM_VIEWPORT)
                        meta["final_url"] = driver.current_url.replace(base, "")
                        links = driver.execute_script(_STYLESHEETS_JS)
                        meta["inline_style_elements"] = links.pop()["inline_style_elements"]
                        sheets = []
                        for l in links:
                            entry = {"href": l["href"], "media": l["media"]}
                            full = l["url"].split("#")[0]
                            if full.startswith(base + "/"):
                                rel = full[len(base):]
                                name = rel.split("?")[0].rstrip("/").split("/")[-1] or "index.css"
                            else:
                                # Fetched with the browser's user agent: Google Fonts answers per UA.
                                entry["cross_origin"] = True
                                name = re.sub(r"[^\w.-]+", "_", full.split("://", 1)[-1]).strip("_") + ".css"
                                warnings.append(f"{r['path']}: cross-origin stylesheet {full}")
                            if css_urls.get(name, full) != full:
                                name = re.sub(r"[^\w.-]+", "_", full.split("://", 1)[-1]).strip("_")
                            css_urls[name] = full
                            entry["file"] = f"_css/{name}"
                            sheets.append(entry)
                        meta["stylesheets"] = sheets
                        meta["console"] = {"1300": console}
                        shots = {}
                        for w in _SHOT_WIDTHS:
                            if w != _DOM_VIEWPORT[0]:
                                meta["console"][str(w)] = _load(driver, url, w, base)
                                (d / f"dom-{w}.html").write_text(
                                    driver.execute_script("return document.documentElement.outerHTML"))
                            if args.no_shots:
                                continue
                            png = _full_page_png(driver)
                            (d / f"shot-{w}.png").write_bytes(png)
                            pw, ph = _png_size(png)
                            shots[str(w)] = {"file": f"shot-{w}.png", "width": pw, "height": ph}
                            if pw != w:
                                shots[str(w)]["overflow_x"] = True
                                warnings.append(f"{r['path']}: the page is {pw} px wide at a {w} px viewport")
                        if shots:
                            meta["shots"] = shots
                        # The same viewport under prefers-color-scheme: dark (the scheme-dependent
                        # markup: data-theme attributes, the toggle's aria-label; _variants.json).
                        _scheme(driver, True)
                        try:
                            meta["console"]["dark"] = _load(driver, url, _DOM_VIEWPORT[0], base, dark=True)
                            (d / "dom-dark.html").write_text(
                                driver.execute_script("return document.documentElement.outerHTML"))
                        finally:
                            _scheme(driver, False)
                    except Exception as e:
                        errors.append(f"{r['path']}: pass 1 failed: {type(e).__name__}: {e}")
                        _log(errors[-1])
                    (d / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
                    if n % 10 == 0 or n == len(selected):
                        _log(f"pass 1: {n}/{len(selected)}")
            finally:
                driver.quit()

        # 3. Stylesheets, each downloaded once
        for name, full in sorted(css_urls.items()):
            try:
                status, _, body = _http_get(full, user_agent) if not full.startswith(base + "/") else _http_get(full)
            except (urllib.error.URLError, OSError) as e:
                status, body = f"{type(e).__name__}: {e}", b""
            if status != 200:
                errors.append(f"stylesheet {full.replace(base, '')}: HTTP {status}")
                continue
            (css_dir / name).write_bytes(body)
            if re.search(rb"@import", body):
                errors.append(f"stylesheet {full.replace(base, '')} has an @import, not followed")
            if not full.startswith(base + "/"):
                # A cross-origin stylesheet (Google Fonts): keep the font files it references too, so
                # the capture holds every byte the route renders with (Phase 1 self-hosts them).
                fonts_dir = _CAPTURE / "_fonts"
                fonts_dir.mkdir(exist_ok=True)
                for furl in sorted({m.group(1).decode() for m in _FONT_URL.finditer(body)}):
                    fname = re.sub(r"[^\w.-]+", "_", furl.split("://", 1)[-1]).strip("_")
                    try:
                        fstatus, _, fbody = _http_get(furl, user_agent)
                    except (urllib.error.URLError, OSError) as e:
                        fstatus, fbody = f"{type(e).__name__}: {e}", b""
                    if fstatus != 200:
                        errors.append(f"font {furl} (from {name}): HTTP {fstatus}")
                        continue
                    (fonts_dir / fname).write_bytes(fbody)
                    run_info.setdefault("fonts", []).append({"url": furl, "stylesheet": name,
                                                             "file": f"_fonts/{fname}", "bytes": len(fbody)})
        _log(f"downloaded {len(css_urls)} stylesheets and {len(run_info.get('fonts', []))} font files")

        # 4. Browser pass 2: a fresh session, hydrated DOM again
        with _slot("oracle capture pass 2"):
            driver = _chrome()
            try:
                for n, r in enumerate(selected, 1):
                    d = _CAPTURE / _slug(r["path"])
                    try:
                        _load(driver, base + r["path"], _DOM_VIEWPORT[0], base)
                        dom2 = driver.execute_script("return document.documentElement.outerHTML")
                        (d / "dom-2.html").write_text(dom2)
                    except Exception as e:
                        errors.append(f"{r['path']}: pass 2 failed: {type(e).__name__}: {e}")
                        _log(errors[-1])
                        continue
                    dom1 = (d / "dom.html").read_text() if (d / "dom.html").exists() else ""
                    if dom1 != dom2:
                        hunks = _diff(dom1, dom2)
                        for h in hunks:
                            h["class"] = _classify(r, h)
                        determinism["dom"][r["path"]] = hunks
                    if n % 10 == 0 or n == len(selected):
                        _log(f"pass 2: {n}/{len(selected)}")
            finally:
                driver.quit()

    for kind in ("dom", "server"):
        for path, hunks in determinism[kind].items():
            for h in hunks:
                bucket = "expected" if h["class"].startswith("expected") else "unexpected"
                determinism[bucket].setdefault(path, []).append(
                    f"{kind}: {h['class'] if bucket == 'expected' else h['where']}")
    (_CAPTURE / "_determinism.json").write_text(json.dumps(determinism, indent=2, ensure_ascii=False) + "\n")

    variants = _write_variants(selected, commit)

    console_errors = {}
    for r in selected:
        try:
            meta = json.loads((_CAPTURE / _slug(r["path"]) / "meta.json").read_text())
        except (OSError, ValueError):
            continue
        msgs = sorted({m["message"] for ms in meta.get("console", {}).values() for m in ms if m["level"] == "SEVERE"})
        if msgs:
            console_errors[r["path"]] = msgs
    size = sum(p.stat().st_size for p in _CAPTURE.rglob("*") if p.is_file())
    run_info.update({
        "tag": _TAG, "commit": commit, "build": {k: stamp.get(k) for k in ("runtime", "install_s", "build_s", "versions")},
        "selenium": selenium_version, "chrome_binary": _CHROME_BINARY, "scheme": "light",
        "dom_viewport": list(_DOM_VIEWPORT), "shot_widths": [] if args.no_shots else list(_SHOT_WIDTHS),
        "dom_variants": {k: f"{f} ({how})" for k, f, how in _VARIANTS},
        "variant_changes": {k: len(v) for k, v in variants["summary"].items()},
        "viewport_height": _VIEWPORT_HEIGHT, "routes": len(selected), "stylesheets": sorted(css_urls),
        "capture_bytes": size, "seconds": round(time.time() - t_start, 1), "errors": errors, "warnings": warnings,
        "console_errors": console_errors,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    run_info["base"] = run_info.get("base", "").rsplit(":", 1)[0] + ":<port>"
    (_CAPTURE / "_run.json").write_text(json.dumps(run_info, indent=2) + "\n")

    _log(f"{len(selected)} routes, {len(css_urls)} stylesheets, {size / 1e6:.1f} MB in {run_info['seconds']} s")
    for path, items in determinism["expected"].items():
        _log(f"nondeterministic (expected) {path}: {len(items)} hunk(s)")
    for path, items in determinism["unexpected"].items():
        _log(f"nondeterministic (UNEXPECTED) {path}: {sorted(set(items))[:5]}")
    for path, msgs in console_errors.items():
        _log(f"console errors on {path}: {msgs}")
    for w in warnings:
        _log(f"warning: {w}")
    for e in errors:
        _log(f"ERROR {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
