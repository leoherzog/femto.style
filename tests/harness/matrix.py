"""Routes, scheme legs, widths and the comparison cells each mode runs.

A cell is one comparison: browser x route x scheme leg x width, side A against side B. The axes
are in tests/harness/matrix.json; every reduction of the full matrix is written to the run log as a
`cap:` line and stored in result.json.
"""
import json

from .paths import MATRIX

# scheme leg -> (prefers-color-scheme, data-theme on <html>)
LEGS = {
    "light": ("light", None),
    "dark": ("dark", None),
    "theme-light": ("dark", "light"),   # forced light on a dark OS
    "theme-dark": ("light", "dark"),    # forced dark on a light OS
}
MEDIA_LEGS = ["light", "dark"]
THEME_LEGS = ["theme-light", "theme-dark"]


class MatrixError(Exception):
    pass


def load_config():
    return json.loads(MATRIX.read_text())


def oracle_routes():
    """(kept paths, dropped paths) from tests/oracle-routes.json, through harness.oracle."""
    try:
        from . import oracle
    except ImportError as e:
        raise MatrixError(f"tests/harness/oracle.py cannot be imported: {e}") from None
    if not oracle.ROUTES_FILE.exists():
        raise MatrixError(f"{oracle.ROUTES_FILE} is missing: run `uv run tests/run.py oracle` first")
    every = oracle.load_routes(kept_only=False)
    # The static Pico v1 pages (kind v1-page) are listed as old paths for criterion 6, never compared.
    return ([r["path"] for r in every if r["kept"]],
            [r["path"] for r in every if not r["kept"] and r["kind"] != "v1-page"])


def storage_for(theme, conf):
    """localStorage entries a leg needs before the load: a data-theme leg stores its theme."""
    if not theme:
        return {}
    st = conf["theme_storage"]
    return {st["key"]: json.dumps(theme) if st.get("format") == "json" else theme}


def cells_for(browsers, routes, widths, theme_routes, legs_override=None):
    """Every cell: light and dark on every route, the data-theme legs on theme_routes (or the
    legs_override list on every route)."""
    out = []
    for b in browsers:
        for r in routes:
            legs = legs_override or (MEDIA_LEGS + (THEME_LEGS if r in theme_routes else []))
            for leg in legs:
                media, theme = LEGS[leg]
                for w in widths:
                    out.append({"browser": b, "route": r, "scheme": leg, "media": media, "theme": theme, "width": w})
    return out


def counts(cells):
    """{browser: {"cells": n, "by_leg": {...}, "by_width": {...}}} for the planner."""
    out = {}
    for c in cells:
        d = out.setdefault(c["browser"], {"cells": 0, "routes": set(), "by_leg": {}, "by_width": {}})
        d["cells"] += 1
        d["routes"].add(c["route"])
        d["by_leg"][c["scheme"]] = d["by_leg"].get(c["scheme"], 0) + 1
        d["by_width"][c["width"]] = d["by_width"].get(c["width"], 0) + 1
    for d in out.values():
        d["routes"] = len(d["routes"])
    return out
