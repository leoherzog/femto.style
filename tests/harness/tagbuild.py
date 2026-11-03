"""A tagged commit of this site, built once into tests/builds/<tag>/dist (gitignored) and served like dist.

The styles mode compares the Phase 2 site against tag static-multipage (PLAN.md Workflow, 2 Styles):
the static site with the oracle's compiled CSS frozen in site/assets/legacy/. targets.json names it as
a command target with "build_tag": the harness builds the tag here, then serves the folder exactly as
it serves dist/ (wrangler pages dev, readiness static, same_origin).

Build. A detached worktree of the tag's commit in a temporary folder (git worktree add --detach),
the repository's node_modules linked into it (the tag's build.mjs needs prismjs only, and the
repository's is the pinned one), then `node build.mjs --out tests/builds/<tag>/dist`, and the worktree
is removed again (git worktree remove --force, then git worktree prune). build.json beside the
folder records the tag, its commit, the Node version, the prismjs version the build highlighted with
(node_modules/prismjs/package.json), a SHA-256 of the built tree (every file's path and content) and
the time taken.

Staleness. A build is redone when dist/index.html is missing, build.json is missing or unreadable, the
commit it records is not the tag's commit now, the repository's prismjs is another version than the
one it records, or the folder's tree no longer hashes to the recorded value (a file under it was
edited, added or removed). serving() checks all of it again before a server starts.

Locks. tests/builds/<tag>.lock: a build holds it exclusively, and every server of the folder holds it
shared for its whole life (serving()), so no run rebuilds the folder under a running server and two
runs never build it at once (the second waits, then finds it fresh).
"""
import contextlib
import fcntl
import hashlib
import json
import os
import random
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .paths import REPO, TESTS

BUILDS = TESTS / "builds"


class BuildError(Exception):
    """The tag cannot be resolved or built; the run stops before any browser starts (exit 2)."""


def folder(tag: str) -> Path:
    """The folder a tag's build is served from."""
    return BUILDS / tag / "dist"


def _git(*args, cwd=REPO, timeout=120):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise BuildError(f"git {' '.join(args)} failed: {(p.stderr or p.stdout).strip()[-400:]}")
    return p.stdout.strip()


@contextlib.contextmanager
def _lock(tag: str, shared: bool, label: str, log):
    """tests/builds/<tag>.lock: exclusive for a build, shared for a server or a freshness check."""
    BUILDS.mkdir(parents=True, exist_ok=True)
    f = open(BUILDS / f"{tag}.lock", "a+")
    mode = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
    announced = 0.0
    try:
        while True:
            try:
                fcntl.flock(f, mode | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - announced > 60:
                    log(f"{label}: waiting for {tag}.lock ("
                        + ("a build of the tag is running" if shared else "servers of the build or another build hold it")
                        + ")")
                    announced = time.time()
                time.sleep(0.5 + random.random())
        yield
    finally:
        try:
            fcntl.flock(f, fcntl.LOCK_UN)
        finally:
            f.close()


def _commit(tag: str) -> str:
    return _git("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}")


def _record(tag: str):
    try:
        return json.loads((BUILDS / tag / "build.json").read_text())
    except (OSError, ValueError):
        return None


def _prismjs() -> str:
    """The version of the repository's prismjs, the one package the tag's build.mjs loads."""
    try:
        return json.loads((REPO / "node_modules" / "prismjs" / "package.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "missing"


def tree_hash(root: Path) -> str:
    """SHA-256 over every file under root: its path relative to root and its content, in path order."""
    h = hashlib.sha256()
    for x in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(x.relative_to(root).as_posix().encode() + b"\0")
        h.update(hashlib.sha256(x.read_bytes()).digest())
    return h.hexdigest()


def stale_reason(tag: str, commit: str):
    """Why the tag's build must be redone, or None when it is fresh."""
    if not (folder(tag) / "index.html").is_file():
        return f"{folder(tag).relative_to(REPO)}/index.html is missing"
    rec = _record(tag)
    if not rec:
        return "build.json is missing or unreadable"
    if rec.get("commit") != commit:
        return f"build.json records commit {str(rec.get('commit'))[:9]}, but {tag} is {commit[:9]}"
    if rec.get("prismjs") != _prismjs():
        return f"build.json records prismjs {rec.get('prismjs')}, but node_modules holds {_prismjs()}"
    if rec.get("tree") != tree_hash(folder(tag)):
        return f"the files under {folder(tag).relative_to(REPO)} no longer match the tree hash in build.json"
    return None


def _build(tag: str, commit: str, log):
    out = folder(tag)
    t0 = time.time()
    if (BUILDS / tag).exists():
        shutil.rmtree(BUILDS / tag)
    out.parent.mkdir(parents=True)
    tmp = Path(tempfile.mkdtemp(prefix=f"femto-style-{tag}-"))
    tree = tmp / "worktree"
    _git("worktree", "add", "--detach", str(tree), commit)
    try:
        modules = REPO / "node_modules"
        if not modules.is_dir():
            raise BuildError("node_modules is missing: run `npm install` (the tag's build.mjs needs prismjs)")
        os.symlink(modules, tree / "node_modules", target_is_directory=True)
        p = subprocess.run(["node", "build.mjs", "--out", str(out)], cwd=tree, capture_output=True, text=True, timeout=600)
        if p.returncode != 0:
            raise BuildError(f"node build.mjs at {tag} ({commit[:9]}) exited {p.returncode}: "
                             f"{(p.stderr or p.stdout).strip()[-600:]}")
        node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        files = sum(1 for x in out.rglob("*") if x.is_file())
        (BUILDS / tag / "build.json").write_text(json.dumps(
            {"tag": tag, "commit": commit, "node": node, "prismjs": _prismjs(), "files": files, "tree": tree_hash(out),
             "seconds": round(time.time() - t0, 1), "built": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1) + "\n")
        log(f"built {tag} ({commit[:9]}) into {out.relative_to(REPO)}: {files} files in {time.time() - t0:.1f}s")
    except BaseException:
        shutil.rmtree(BUILDS / tag, ignore_errors=True)
        raise
    finally:
        try:
            _git("worktree", "remove", "--force", str(tree))
        except BuildError:
            shutil.rmtree(tree, ignore_errors=True)
        _git("worktree", "prune")
        shutil.rmtree(tmp, ignore_errors=True)


def ensure(tag: str, log=print) -> Path:
    """Build the tag if its folder is missing or stale; return the folder. Raises BuildError."""
    try:
        commit = _commit(tag)
    except BuildError:
        raise BuildError(f"tag {tag} does not exist in this repository") from None
    with _lock(tag, True, f"{tag} freshness check", log):
        if stale_reason(tag, commit) is None:
            return folder(tag)
    with _lock(tag, False, f"{tag} build", log):
        reason = stale_reason(tag, commit)
        if reason is not None:
            log(f"building {tag} ({commit[:9]}): {reason}")
            _build(tag, commit, log)
    return folder(tag)


@contextlib.contextmanager
def serving(tag: str, log):
    """Hold the tag's lock shared while a server reads its folder, and check it is still fresh."""
    with _lock(tag, True, f"{tag} server", log):
        reason = stale_reason(tag, _commit(tag))
        if reason is not None:
            raise BuildError(f"the {tag} build went stale before its server started ({reason}); run again")
        yield
