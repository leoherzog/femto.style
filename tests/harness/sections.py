"""The sections mode: Phase 3's gate (PLAN.md Workflow, 3 One page; acceptance criterion 2).

Side A is the static site at tag static-femto, one page per old docs route; side B is the one docs
page. Each cell compares one old route's content, the subtree of its [role=document], against its
section of the one page: the element document.getElementById(id).closest("section"), loaded at
/docs#<id> so that the section is on screen as the route's content was. A version picker color route
(/docs/version-picker/<color>) is the picker's section on /docs?theme=<color>#version-picker.

The routes and their sections come from side A's menu.json (targets.json "menu"; for a build_tag
target it is read from the tag with git show, so the working tree's menu.json, which Phase 3 strips
of its per-route fields, never decides them): each section's route and the routes of its variants.
A cell keeps side A's route as its route (registry where.routes, reports) and records side B's URL
(url_b) and the section it compares (section, section_theme). Everything else, scheme legs, widths,
masks, value rules, chunking, the same-origin rule and the --full matrix, is the pages mode's.

Side A's root takes grafts (GRAFTS; differ.js graftsOf): the parts of the old route's section that sat
in its main, outside div#content, and that the one page holds inside the section. They are compared
as the root's first and last children, so the hgroup (the section's title and description), Modal's
dialog and Nav's overflow-with-focus nav pair with side B's and are compared in full.
"""
import json
import subprocess

from .paths import REPO
from .targets import TargetError

ROOT_A = "[role=document]"   # side A's alignment root: the old route's content (div#content)
SECTION = "section"          # side B's root: the closest <section> around the element with the id
# Side A's grafts: before, the root's first children (each section file starts with its hgroup);
# after, its last (site/docs/sections/modal.html and nav.html end with the element, after the edit
# link). An element in another place on side B is an only-a and an only-b record, never hidden.
GRAFTS = {"before": ["main > hgroup"],
          "after": ["main > dialog", 'main > nav[aria-label="overflow-with-focus"]']}
DEFAULT_PAGE = "/docs"       # the one page's URL for a base-URL side B


def load_menu(side):
    """(menu, where): side A's menu.json, parsed, and where it was read from."""
    spec = (side.conf or {}).get("menu")
    if not spec:
        raise TargetError(f"side A {side.spec} names no menu in targets.json: the sections mode maps its routes to "
                          "sections through it (tests/README.md, Sections)")
    tag = side.conf.get("build_tag")
    if tag:
        where = f"{tag}:{spec}"
        p = subprocess.run(["git", "show", f"refs/tags/{tag}:{spec}"], cwd=REPO, capture_output=True, text=True,
                           timeout=30)
        if p.returncode != 0:
            raise TargetError(f"cannot read {where} with git show: {(p.stderr or p.stdout).strip()[-300:]}")
        text = p.stdout
    else:
        where = spec
        try:
            text = (REPO / spec).read_text()
        except OSError as e:
            raise TargetError(f"cannot read {spec}: {e}") from None
    try:
        return json.loads(text), where
    except ValueError as e:
        raise TargetError(f"{where} is not JSON: {e}") from None


def color_of(route):
    """A variant route's color: its last path segment, without .html (/docs/version-picker/jade)."""
    last = route.rstrip("/").rsplit("/", 1)[-1]
    return last[:-5] if last.endswith(".html") else last


def route_map(side):
    """({route: (section id, theme color or None)} in menu order, where the menu was read from)."""
    menu, where = load_menu(side)
    out = {}
    for cat in menu.get("categories") or []:
        for s in cat.get("sections") or []:
            sid, route = s.get("id"), s.get("route")
            if not isinstance(sid, str) or not isinstance(route, str):
                raise TargetError(f"{where}: section {sid!r} has no id or no route (the sections mode reads the "
                                  "per-route fields of side A's menu)")
            out[route] = (sid, None)
            for v in s.get("variants") or []:
                if not isinstance(v.get("route"), str):
                    raise TargetError(f"{where}: a variant of section {sid} has no route")
                out[v["route"]] = (sid, color_of(v["route"]))
    if not out:
        raise TargetError(f"{where} lists no sections")
    return out, where


def one_page(side):
    """Side B's one docs page (targets.json "one_page"; /docs for a base URL)."""
    if side.kind == "url":
        return DEFAULT_PAGE
    page = (side.conf or {}).get("one_page")
    if not page:
        raise TargetError(f"side B {side.spec} names no one_page in targets.json: the sections mode loads each "
                          "section from it")
    return page


def root_a(sel):
    """Side A's root in a section cell: the element sel names (--root-a), with GRAFTS."""
    return {"sel": sel, **GRAFTS}


def graft_note():
    """How side A's root is described in the run's caps and result.json."""
    return ("with " + ", ".join(GRAFTS["before"]) + " grafted in as its first children and "
            + ", ".join(GRAFTS["after"]) + " as its last")


def fields(sid, color, page, sel=ROOT_A):
    """The cell fields of a section cell: side B's URL and expected path, and both roots."""
    path = page + (f"?theme={color}" if color else "")
    return {"section": sid, "section_theme": color, "url_b": f"{path}#{sid}", "path_b": path,
            "root_a": root_a(sel), "root_b": {"id": sid, "closest": SECTION}}
