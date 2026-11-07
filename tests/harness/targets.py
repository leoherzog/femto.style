"""The two sides of a comparison: named targets from tests/harness/targets.json, or base URLs.

Side A is <base A><path> and side B is <base B><path>. A side is one of:

* `oracle`: the Remix site at tag remix-final, built if needed and served by harness.oracle.serve()
  (its own wrangler pages dev); readiness hook oracle.wait_ready().
* `fixture` or `fixture:<control>`: the selftest site in tests/fixtures/site/, served by the harness,
  optionally changed by a named control from tests/fixtures/controls.json.
* `command` targets such as `dist`: a server the harness starts from a command line in its own
  process group and stops with every child when the run ends. `dist:<path>` serves any built
  folder exactly as `dist` serves dist/ (the same wrangler, options, readiness and same-origin
  rule), so several agents can compare their own builds at once.
* a command target with `build_tag`, such as `static-multipage`, `static-femto` or
  `static-one-page`: the harness first builds that tag
  of this repository into the target's folder (harness.tagbuild: a temporary git worktree, node
  build.mjs --out), rebuilding when the folder's index.html or build.json is missing, the tag's
  commit or the prismjs version differs from the one build.json records, or the folder no longer
  matches its recorded tree hash (tagbuild.stale_reason), then serves the folder exactly as `dist`
  serves dist/.
* a base URL (`http://127.0.0.1:8788`): a server someone else runs; nothing is started or stopped.

A target may also name a `menu` (the sections mode reads side A's routes and their sections from it,
harness.sections), a `one_page` (the one docs page the sections mode loads side B's sections from)
and a `comparison` (what a pages or sections run is when the target is side A: static-femto makes it
one-page, which decides the registry entries that apply).

wrangler is always the repository's own: `npm exec --no -- wrangler`, checked first against the exact
version package.json pins. FEMTO_WRANGLER=<path to a wrangler executable> replaces it (only for
testing the harness before the repository has one); every run that uses it says so in a cap line.

Every named target that a run names is started once per side, so `--a oracle --b oracle` (the
self mode) runs two separate oracle servers. Readiness hooks run before the collector reads a side:
`oracle` (the oracle's own hydration check, run inside the iframe), `static` (the document is
complete, document.fonts.ready resolved and two animation frames passed, with a timer standing in
for a frame where rAF never runs) or `none`.
"""
import json
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from .paths import REPO, TARGETS

READY = ("oracle", "static", "none")
FORBIDDEN_PORTS = {8790}
WRANGLER_ENV = "FEMTO_WRANGLER"
NPM_WRANGLER = ["npm", "exec", "--no", "--", "wrangler"]


class TargetError(Exception):
    """A side cannot be resolved or started; the run stops before any browser starts (exit 2)."""


def load_targets():
    return json.loads(TARGETS.read_text())["targets"]


def _rel(p):
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def _package_of(exe):
    """The wrangler package.json an executable belongs to (node_modules/.bin/wrangler links to
    node_modules/wrangler/bin/wrangler.js), or None."""
    for d in Path(os.path.realpath(exe)).parents:
        pj = d / "package.json"
        if pj.is_file():
            try:
                data = json.loads(pj.read_text())
            except ValueError:
                return None
            return data if data.get("name") == "wrangler" else None
    return None


EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")


def wrangler_info():
    """{argv, version, source, pin}: how a command target runs wrangler. The repository's own
    (npm exec --no -- wrangler, node_modules/wrangler at the exact version package.json pins), or
    FEMTO_WRANGLER's executable for testing. Raises TargetError when the repository's is missing or
    does not match its pin."""
    override = os.environ.get(WRANGLER_ENV)
    if override:
        exe = Path(override).expanduser()
        if not (exe.is_file() and os.access(exe, os.X_OK)):
            raise TargetError(f"{WRANGLER_ENV}={override} is not an executable file")
        pkg = _package_of(exe) or {}
        return {"argv": [str(exe)], "version": pkg.get("version"), "source": f"{WRANGLER_ENV}={override}", "pin": None}
    try:
        pin = (json.loads((REPO / "package.json").read_text()).get("devDependencies") or {}).get("wrangler")
    except (OSError, ValueError) as e:
        raise TargetError(f"cannot read package.json: {e}") from None
    if not pin:
        raise TargetError("package.json has no devDependencies.wrangler: the dist targets run the repository's own "
                          "pinned wrangler (npm exec --no never downloads one)")
    if not EXACT_VERSION.match(pin):
        raise TargetError(f"package.json pins wrangler as {pin!r}, not an exact version (PLAN.md Repo changes: every "
                          "version pinned exactly)")
    pj = REPO / "node_modules" / "wrangler" / "package.json"
    if not (REPO / "node_modules" / ".bin" / "wrangler").exists() or not pj.is_file():
        raise TargetError(f"node_modules/.bin/wrangler is missing: run `npm install` (package.json pins wrangler {pin}); "
                          f"to test the harness without it, set {WRANGLER_ENV} to another wrangler executable")
    version = json.loads(pj.read_text()).get("version")
    if version != pin:
        raise TargetError(f"node_modules/wrangler is {version}, but package.json pins {pin}: run `npm install`")
    return {"argv": list(NPM_WRANGLER), "version": version, "source": "repository (npm exec --no -- wrangler)", "pin": pin}


class Side:
    def __init__(self, spec, ready=None, root=None):
        self.spec = spec
        self.root = root or None
        self.share = None   # "a": serve this side from side A's server (self --one-server)
        self.root_note = None  # the sections mode: side B's root is each cell's section, side A's takes grafts
        self.base = None
        self.control = None
        self.dir = None       # the folder a command target serves (dist, or dist:<path>)
        self.wrangler = None  # wrangler_info(), for a command that runs wrangler
        if spec.startswith(("http://", "https://")):
            self.kind, self.name, self.conf = "url", spec.rstrip("/"), {}
            self.base = spec.rstrip("/")
        else:
            name, _, control = spec.partition(":")
            targets = load_targets()
            if name not in targets:
                raise TargetError(f"unknown target {spec!r}: name one of {', '.join(sorted(targets))} or a base URL")
            self.name, self.conf = name, targets[name]
            self.kind = self.conf["kind"]
            if self.conf.get("build_tag") and control:
                raise TargetError(f"target {name} serves its own build of tag {self.conf['build_tag']}; it takes no "
                                  f"folder (got {spec!r})")
            if "dir" in self.conf:
                # dist:<path>: any built folder, served exactly as the target serves its own.
                d = Path(control or self.conf["dir"]).expanduser()
                self.dir = (d if d.is_absolute() else REPO / d).resolve()
            elif control:
                if self.kind != "fixture":
                    raise TargetError(f"target {name} takes no control (got {spec!r})")
                self.control = control
        self.ready = ready or self.conf.get("ready", "static")
        if self.ready not in READY:
            raise TargetError(f"unknown readiness hook {self.ready!r} (use {', '.join(READY)})")

    def uses_wrangler(self):
        return self.kind == "command" and "{wrangler}" in self.conf.get("command", [])

    def caps(self):
        """Cap lines for the run: a side whose wrangler is not the repository's."""
        if self.uses_wrangler() and os.environ.get(WRANGLER_ENV):
            return [f"side {self.spec}: wrangler from {WRANGLER_ENV}={os.environ[WRANGLER_ENV]}, not the repository's "
                    "pinned one (a harness test, not a gate)"]
        return []

    def describe(self):
        d = {"spec": self.spec, "kind": self.kind, "base": self.base, "ready": self.ready}
        if self.root:
            d["root"] = self.root + (f" ({self.root_note})" if self.root_note else "")
        elif self.root_note:
            d["root"] = self.root_note
        if self.control:
            d["control"] = self.control
        if self.dir is not None:
            d["dir"] = _rel(self.dir)
        if self.conf.get("build_tag"):
            from .tagbuild import BUILDS
            try:
                d["build"] = json.loads((BUILDS / self.conf["build_tag"] / "build.json").read_text())
            except (OSError, ValueError):
                d["build"] = None
        if self.wrangler:
            d["wrangler"] = {k: v for k, v in self.wrangler.items() if k != "argv"}
        if self.conf.get("same_origin"):
            d["same_origin"] = True
        return d

    def fill(self, s, **more):
        """A command, requires or env string with the target's placeholders filled in."""
        return s.format(dir=self.dir if self.dir is not None else "", **more)

    def check(self):
        """Setup checks that need no server (run before any browser or server starts)."""
        if self.kind == "fixture":
            from .server import SITE, build_overrides, ControlError
            try:
                build_overrides(SITE, self.control)
            except ControlError as e:
                raise TargetError(str(e)) from None
        elif self.kind == "command":
            tag = self.conf.get("build_tag")
            if tag:
                from .tagbuild import BuildError, ensure
                try:
                    ensure(tag, log=lambda m: print(m, flush=True))
                except BuildError as e:
                    raise TargetError(f"target {self.spec}: {e}") from None
            if self.dir is not None and not self.dir.is_dir():
                raise TargetError(f"target {self.spec}: {_rel(self.dir)} is not a folder (build it first)")
            req = self.conf.get("requires")
            if req:
                path = Path(self.fill(req))
                path = path if path.is_absolute() else REPO / path
                if not path.exists():
                    raise TargetError(f"target {self.spec} needs {_rel(path)}, which does not exist (build it first)")
            if self.uses_wrangler():
                self.wrangler = wrangler_info()
        elif self.kind == "oracle":
            try:
                from . import oracle  # noqa: F401
            except ImportError as e:
                raise TargetError(f"target oracle needs tests/harness/oracle.py: {e}") from None


def free_port():
    while True:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port not in FORBIDDEN_PORTS:
            return port


def _group_members(pgid):
    """The live (not zombie) processes of a process group, from ps."""
    try:
        out = subprocess.run(["ps", "-A", "-o", "pid=,pgid=,stat="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    rows = [line.split() for line in out.splitlines()]
    return [int(r[0]) for r in rows if len(r) >= 3 and r[1] == str(pgid) and not r[2].startswith("Z")]


def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # macOS answers EPERM for a group whose leader is an unreaped zombie: ask ps who is left.
        return bool(_group_members(pgid))


class _Command:
    """A server started from targets.json's command line, in its own process group."""

    def __init__(self, side, log, log_dir):
        conf = side.conf
        self.port, inspector = free_port(), free_port()
        while inspector == self.port:
            inspector = free_port()
        log_dir.mkdir(parents=True, exist_ok=True)
        cmd = []
        for a in conf["command"]:
            if a == "{wrangler}":
                if side.wrangler is None:
                    side.wrangler = wrangler_info()
                cmd += side.wrangler["argv"]
            else:
                cmd.append(side.fill(a, port=self.port, inspector_port=inspector, log_dir=log_dir))
        self.log_path = log_dir / f"server-{side.name}-{self.port}.log"
        self.log_f = open(self.log_path, "w")
        log(f"starting {side.spec}: {' '.join(cmd)} (log {self.log_path.name}"
            + (f"; wrangler {side.wrangler['version']}, {side.wrangler['source']}" if side.wrangler else "") + ")")
        env = dict(os.environ)
        env.update({k: side.fill(str(v), port=self.port, log_dir=log_dir) for k, v in (conf.get("env") or {}).items()})
        self.proc = subprocess.Popen(cmd, cwd=REPO / conf.get("cwd", "."), stdout=self.log_f, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True, env=env)
        self.base = f"http://127.0.0.1:{self.port}"
        deadline = time.time() + conf.get("start_timeout", 120)
        try:
            while True:
                if self.proc.poll() is not None:
                    raise TargetError(f"{side.name} exited {self.proc.returncode} before answering; see {self.log_path}")
                try:
                    urllib.request.urlopen(self.base + "/", timeout=5).close()
                    break
                except urllib.error.HTTPError:
                    break  # any HTTP answer means the server is up
                except (urllib.error.URLError, OSError):
                    pass
                if time.time() > deadline:
                    raise TargetError(f"{side.name} did not answer on {self.base}; see {self.log_path}")
                time.sleep(0.25)
        except BaseException:
            self.stop()
            raise

    def stop(self):
        pgid = self.proc.pid
        for sig, wait in ((signal.SIGTERM, 10), (signal.SIGKILL, 5)):
            self.proc.poll()  # reap the leader (npm exec exits first), so the group's state is its children's
            if not _group_alive(pgid):
                break
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                break
            except PermissionError:
                for pid in _group_members(pgid):
                    try:
                        os.kill(pid, sig)
                    except OSError:
                        pass
            end = time.time() + wait
            while time.time() < end:
                self.proc.poll()
                if not _group_alive(pgid):
                    break
                time.sleep(0.2)
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        self.log_f.close()


def start(stack, side, log, log_dir):
    """Start the side's server (if any) inside an ExitStack and set side.base."""
    if side.kind == "url":
        return
    if side.kind == "oracle":
        from . import oracle
        t0 = time.time()
        side.base = stack.enter_context(oracle.serve())
        log(f"oracle server {side.base} answered after {time.time() - t0:.1f}s")
    elif side.kind == "fixture":
        from .server import StaticServer
        srv = StaticServer(control=side.control)
        stack.callback(srv.close)
        side.base = srv.base
    elif side.kind == "command":
        if side.conf.get("build_tag"):
            # Hold the tag's build lock shared while the server reads the folder (tagbuild.serving).
            from .tagbuild import BuildError, serving
            try:
                stack.enter_context(serving(side.conf["build_tag"], log))
            except BuildError as e:
                raise TargetError(str(e)) from None
        c = _Command(side, log, log_dir)
        stack.callback(c.stop)
        side.base = c.base
    else:
        raise TargetError(f"target {side.name}: unknown kind {side.kind!r}")


def run_ready(sess, side, timeout=30):
    """Run the side's readiness hook on the document in the session's iframe. Returns a list of errors."""
    errors = []
    if side.ready == "oracle":
        from . import oracle
        with sess.in_frame():
            try:
                oracle.wait_ready(sess.driver, timeout=timeout)
            except Exception as e:
                errors.append(f"oracle.wait_ready: {type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}")
    if side.ready in ("oracle", "static"):
        r = sess.ajs("ready", int(timeout * 1000))
        errors += r.get("errors", [])
    return errors
