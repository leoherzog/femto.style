"""The styles mode's additions to a comparison cell: femto's tokens and interactive states.

Ported from femto's tests/harness at commit 7bcd5758 (README Tokens and States; compare.py
apply_state; differ.js collectTokens, stateTargets, afterState). femto compares one fixture under two
stylesheet lists; here the two documents are side A's and side B's builds of the same markup, aligned
element for element as in the pages mode (differ.js), so the tokens and states compare on top of
everything the pages mode compares.

Tokens. Every --femto-* custom property declared in either side's stylesheets; names on one side only
are surface-missing or surface-added records; for names on both, resolution through hidden probe
children under each anchor (PROBE_PROPS, femto's list) and the raw text at each anchor. The anchors are
femto's (html, body, every [data-theme] element, every article and dialog, each shadow root) plus
ANCHORS, the site's equivalents of femto's [data-module] wrappers.

States. The site's markup carries no data-states attributes (Phase 2 changes no markup), so the targets
come from harness/states.json (STATES): a selector, its states, the routes it applies to, how many of
its matches to replay, and the scope whose subtree is collected. Each state is applied with real input
on both sides in the same order (femto's apply_state), and side B's subtree is diffed against side
A's under the same state.
"""
import json
import re
import time
from pathlib import Path

from .browsers import PARK
from .paths import HARNESS, REPO

TOKEN_PREFIX = "--femto-"
# femto's probe properties (tests/harness/differ.js PROBE_PROPS at 7bcd5758): each token is resolved
# through each of these as var(<token>) on a hidden probe element.
PROBE_PROPS = [
    "color", "background-color", "border-top-color", "outline-color", "box-shadow",
    "background-image", "filter", "backdrop-filter", "opacity", "font-size", "font-family",
    "font-weight", "line-height", "letter-spacing", "width", "padding-top", "margin-top",
    "border-top-width", "border-top-left-radius", "outline-width", "outline-offset",
    "text-decoration-line", "text-underline-offset", "transition", "content",
]
# The site's own wrappers, femto's [data-module] in this site: the page header and footer, <main>, the
# docs page's menu and table of contents (main > aside) and its content ([role=document]), and the
# landing page's sections (main > section). The site's CSS sets tokens on these or on what they hold
# (the fixed header, the docs grid, the landing's hero and comparison), and a token that resolves
# differently inside one of them shows at its anchor. Everything else inherits from one of them, html
# or body, an article (every example card) or a [data-theme] element (every code block's footer).
ANCHORS = "body > header, body > footer, main, main > aside, [role=document], main > section"
STATES = HARNESS / "states.json"
STATE_NAMES = ("hover", "focus", "focus-visible", "active")
TARGET_FIELDS = ("id", "selector", "states", "routes", "scope", "max", "open", "widths", "why")


class StatesError(Exception):
    """The states file is invalid; the run stops before any browser starts (exit 2)."""


def _route_ok(pat, route):
    if pat.startswith("/^") and pat.endswith("/"):
        return re.search(pat[1:-1], route) is not None
    return pat == route


def _width_ok(spec, width):
    for x in spec:
        if isinstance(x, int) and x == width:
            return True
        if isinstance(x, dict) and x.get("min", 0) <= width <= x.get("max", 10 ** 6):
            return True
    return False


class States:
    """harness/states.json (or --states FILE): the state targets of every route."""

    def __init__(self, path=STATES):
        self.path = Path(path)
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError) as e:
            raise StatesError(f"{self.path}: {e}") from None
        self.targets = data.get("targets") if isinstance(data, dict) else None
        if not isinstance(self.targets, list):
            raise StatesError(f"{self.path}: needs a targets list")
        errs, ids = [], set()
        for n, t in enumerate(self.targets):
            where = f"{self.path.name} target #{n}"
            if not isinstance(t, dict):
                errs.append(f"{where}: not an object")
                continue
            where += f" [{t.get('id')}]"
            for k in t:
                if k not in TARGET_FIELDS:
                    errs.append(f"{where}: unknown field {k!r}")
            if not isinstance(t.get("id"), str) or not t["id"] or t["id"] in ids:
                errs.append(f"{where}: id must be a unique non-empty string")
            ids.add(t.get("id"))
            for f in ("selector", "scope", "open"):
                if f in t and (not isinstance(t[f], str) or not t[f].strip()):
                    errs.append(f"{where}: {f} must be a non-empty selector")
            if "selector" not in t:
                errs.append(f"{where}: needs selector")
            st = t.get("states")
            if not isinstance(st, list) or not st or any(s not in STATE_NAMES for s in st) or len(set(st)) != len(st):
                errs.append(f"{where}: states must list some of {', '.join(STATE_NAMES)}, each once")
            rs = t.get("routes")
            if not isinstance(rs, list) or not rs or not all(isinstance(r, str) and r.startswith("/") for r in rs):
                errs.append(f"{where}: routes must list routes (/docs/button) or /^regex/ patterns")
            if "max" in t and (not isinstance(t["max"], int) or t["max"] < 1):
                errs.append(f"{where}: max must be a positive integer")
            if "widths" in t and (not isinstance(t["widths"], list) or not t["widths"]
                                  or not all(isinstance(x, int) or (isinstance(x, dict) and x and set(x) <= {"min", "max"})
                                             for x in t["widths"])):
                errs.append(f"{where}: widths items are integers or {{min, max}} objects")
        if errs:
            raise StatesError("; ".join(errs))

    def for_cell(self, cell):
        """The targets that apply to a cell, in file order, as differ.js's prepTarget takes them."""
        out = []
        for t in self.targets:
            if not any(_route_ok(r, cell["route"]) for r in t["routes"]):
                continue
            if "widths" in t and not _width_ok(t["widths"], cell["width"]):
                continue
            out.append({k: t[k] for k in ("id", "selector", "states", "scope", "max", "open") if k in t})
        return out

    def describe(self):
        try:
            rel = str(self.path.relative_to(REPO))
        except ValueError:
            rel = str(self.path)
        return {"file": rel, "targets": len(self.targets),
                "target_states": sum(len(t["states"]) for t in self.targets)}


def configure_args():
    """The token settings H.configure takes in the styles mode."""
    return {"tokens": True, "tokenPrefix": TOKEN_PREFIX, "probeProps": PROBE_PROPS, "anchors": ANCHORS}


def apply_state(sess, side, target, state, key, scope):
    """Apply one state with real input, then collect (and on side B diff) the scope's subtree.

    femto's apply_state: pointer states retry once when the state did not match, after letting
    scrolling settle; focus-visible is a real Tab from the focusable before the target (Shift+Tab
    from the one after it when that misses; Safari, Option+Tab, then focus() right after the key
    presses for summary and input[type=color], which Option+Tab never lands on). When both Tabs miss,
    the target is focused and left with Shift+Tab, then reached again with Tab: the browser's own
    order, which also stops at keyboard-focusable scrollers (an overflowing pre)."""
    k = target["k"]
    info, extra = None, {}
    if state in ("hover", "active"):
        for attempt in range(2):
            if attempt:
                time.sleep(0.15)
            p = sess.ajs("pointAt", k)
            extra = {"hit": p["hit"], "hitLabel": p["hitLabel"], "retries": attempt}
            if p.get("outside"):
                info = {"matched": False}
                continue
            if state == "hover":
                sess.move(p["x"], p["y"])
                info = sess.ajs("afterState", side, k, state, key, scope)
            else:
                sess.press(p["x"], p["y"])
                try:
                    info = sess.ajs("afterState", side, k, state, key, scope)
                finally:
                    sess.release(p["x"], p["y"])
            sess.park()
            if info.get("matched"):
                break
            sess.js("resetState")
    elif state == "focus":
        sess.js("focusEl", k)
        info = sess.ajs("afterState", side, k, state, key, scope)
    else:  # focus-visible
        prep = sess.js("prepTab", k, 1)
        sess.tab()
        info = sess.ajs("afterState", side, k, state, key, scope)
        extra = {"method": "tab", "from": prep.get("from")}
        if not info.get("matched"):
            sess.js("resetState")
            prep = sess.js("prepTab", k, -1)
            sess.tab(shift=True)
            info = sess.ajs("afterState", side, k, state, key, scope)
            extra = {"method": "shift-tab", "from": prep.get("from")}
        if not info.get("matched"):
            # A tab stop focusables() cannot see (a keyboard-focusable scroller) lies before or after
            # the target: focus the target, Shift+Tab away and Tab back, in the browser's own order.
            sess.js("resetState")
            sess.js("prepBack", k)
            sess.tab(shift=True)
            sess.tab()
            info = sess.ajs("afterState", side, k, state, key, scope)
            extra = {"method": "back-and-tab"}
        if not info.get("matched") and sess.browser == "safari":
            sess.js("resetState")
            sess.js("focusEl", k)
            info = sess.ajs("afterState", side, k, state, key, scope)
            extra = {"method": "focus-after-tab"}
    sess.js("resetState")
    info.update(extra)
    return info


def replay(sess, side, cell, targets, registry, out, res, merge):
    """Replay every state target of the cell on one side (after its collect, and on side B after the
    document's diff). Side B's state records go into res; mismatches are harness errors."""
    if not targets:
        return
    t0 = time.time()
    if sess.browser == "safari":
        ok, why = sess.interactive()
        if not ok:
            out["errors"].append(f"{side} states: not replayed: {why}")
            return
    sess.js("armStates")
    # Start every side's replay from the same input modality: a pointer click on the host page's
    # strip, outside the document (focus-visible follows the last input; tests/README.md, Tokens and
    # states).
    sess.park()
    sess.press(*PARK)
    sess.release(*PARK)
    seen = out.setdefault("state_targets", {})
    runs = 0
    for spec in targets:
        # Side B replays exactly the elements side A took (by tree path).
        want = seen.get(spec["id"]) if side == "b" else None
        prep = sess.js("prepTarget", spec, want)
        out["errors"] += [f"{side} state target {spec['id']}: {e}" for e in prep.get("errors", [])]
        paths = [t["path"] for t in prep.get("targets", [])]
        if side == "a":
            seen[spec["id"]] = paths
        elif want != paths:
            gone = [p for p in want or [] if p not in paths]
            out["errors"].append(f"state target {spec['id']}: side A's {', '.join(gone)} does not render on side B, so "
                                 "its states are not replayed there (the document diff shows why; states.json's widths "
                                 "or selector may need narrowing)")
        if not paths and side == "a":
            out["errors"].append(f"{side} state target {spec['id']} ({spec['selector']}): none of its "
                                 f"{prep.get('matched', 0)} matches renders here (states.json routes and widths)")
        for tg in prep.get("targets", []):
            for st in spec["states"]:
                key = f"{spec['id']}|{tg['path']}|{st}"
                info = apply_state(sess, side, tg, st, key, spec.get("scope"))
                runs += 1
                if not info.get("matched"):
                    check = f"state:{st}:{tg.get('tag', '')}" + (f"[type={tg['type']}]" if tg.get("type") else "")
                    if not info.get("error") and registry.match_skipped(check, cell):
                        if check not in out["skipped"]:
                            out["skipped"].append(check)
                        continue
                    why = info.get("error") or (f"not hit-testable, covered by {info.get('hitLabel')}"
                                                if info.get("hit") is False else "")
                    out["errors"].append(f"{side} state {st} did not match on {tg['label']} at {tg['path']}"
                                         + (f" ({why})" if why else ""))
                    continue
                if info.get("error"):
                    out["errors"].append(f"{side} state {st} on {tg['label']}: {info['error']}")
                if side == "b" and info.get("result"):
                    out["errors"] += [f"state {st} diff: {e}" for e in info["result"].get("errors", [])]
                    merge(res, info["result"])
        sess.js("unprepTarget")
    # The replay's instant scrolling ends with it (differ.js armStates), before the screenshot: html's
    # scroll-behavior is the page's own again (scroll_behavior_<side>, control scroll-smooth).
    done = sess.js("disarmStates") or {}
    out[f"scroll_behavior_{side}"] = done.get("behavior")
    if done.get("left"):
        out["errors"].append(f"{side} states: the replay's scroll-behavior style is still in the document")
    out[f"states_{side}"] = runs
    out["timing"][f"{side}_states"] = round(time.time() - t0, 2)
