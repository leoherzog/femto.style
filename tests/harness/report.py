"""result.json and summary.txt for a run, and the exit status."""
import collections
import json
import time


def _short(v, n=80):
    if v is None:
        return "(absent)"
    s = str(v)
    return repr(s if len(s) <= n else s[:n] + "~")


def fmt_rec(r):
    k = r["kind"]
    if r.get("state"):
        # A record found under a replayed interactive state (the styles mode): the same kinds, tagged.
        return f"[{r['state']}] " + fmt_rec({x: v for x, v in r.items() if x != "state"})
    if k == "token":
        return f"token {r['token']} via {r['prop']} at {r['label']}: {_short(r['a'])} -> {_short(r['b'])}  @ {r['path']}"
    if k == "token-raw":
        return f"token-raw {r['token']} at {r['label']}: {_short(r['a'])} -> {_short(r['b'])}  @ {r['path']}"
    if k in ("surface-missing", "surface-added"):
        return f"{k} {r['token']}: declared on side {'A' if k == 'surface-missing' else 'B'} only"
    if k == "style":
        ps = r.get("pseudo") or ""
        return f"style {r['label']}{ps} {r['prop']}: {_short(r['a'])} -> {_short(r['b'])}  @ {r['path']}"
    if k == "attribute":
        return f"attribute {r['label']} [{r['prop']}]: {_short(r['a'])} -> {_short(r['b'])}  @ {r['path']}"
    if k == "text":
        return f"text {r['label']}: {_short(r['a'])} -> {_short(r['b'])}  @ {r['path']}"
    if k == "structure":
        what = {"only-a": f"only on side A ({r.get('size_a')} elements)", "only-b": f"only on side B ({r.get('size_b')} elements)",
                "tag": f"tag {r['a']} -> {r['b']} (A: {r.get('label_a')})"}.get(r.get("change"), r.get("change"))
        return f"structure {r['label']}: {what}  @ {r['path']}"
    if k == "head":
        return f"head {r['path']} {r['prop']}: {_short(r['a'])} -> {_short(r['b'])}"
    if k == "status":
        return f"status {r['path']}: {r['a']} -> {r['b']}"
    return json.dumps(r)


def cell_name(c):
    return f"{c['browser']} {c['route']} {c['scheme']} {c['width']}"


# An entry that registers this many records in one cell is flagged in the summary: an entry that wide
# can hide unrelated differences, so review what it matches.
BROAD_PER_CELL = 100


def build(run, cells, registry, pool_errors, rigs, caps, extra=None):
    """Aggregate cell records into the run result."""
    unreg_cells, errors, skipped = [], [], collections.OrderedDict()
    registered = collections.Counter()
    inherited = collections.Counter()  # records folded into a registered parent's record, by entry
    entry_cells = {}  # entry id -> [cells hit, most records in one cell, that cell]
    per_group = collections.OrderedDict()
    pixels = []
    mask_totals = collections.Counter()
    unregistered_total = 0
    cross_loads = []                          # criterion 15: same-origin sides that loaded another origin
    site_loads = collections.OrderedDict()    # (side, url) -> cells: loads from https://femto.style, listed
    cross_reported = collections.OrderedDict()  # (side spec, url) -> cells, for sides not held to it
    for c in cells:
        for x in c.get("cross_origin_loads") or []:
            cross_loads.append({"cell": cell_name(c), **x})
        for sname, side in (c.get("sides") or {}).items():
            for u in side.get("site_origin_loads") or []:
                site_loads.setdefault((sname, u), []).append(cell_name(c))
        for sname, side in (c.get("sides") or {}).items():
            if side.get("same_origin_required"):
                continue
            for u in side.get("cross_origin") or []:
                key = ((run.get("sides") or {}).get(sname, {}).get("spec", sname), u)
                cross_reported.setdefault(key, set()).add(c["route"])
        res = c.get("result") or {}
        ut = res.get("unregisteredTotal", 0)
        unregistered_total += ut
        if ut:
            unreg_cells.append(c)
        for e in c.get("errors", []):
            errors.append(f"{cell_name(c)}: {e}")
        for chk in c.get("skipped", []):
            ids = registry.match_skipped(chk, c)
            key = (chk, c["browser"], tuple(ids))
            s = skipped.setdefault(key, {"check": chk, "browser": c["browser"], "entries": ids, "cells": 0})
            s["cells"] += 1
            for i in ids:
                registry.hits[i] = registry.hits.get(i, 0) + 1
        registered.update(res.get("registered", {}))
        inherited.update(res.get("inherited", {}))
        for k, n in (res.get("registered") or {}).items():
            st = entry_cells.setdefault(k, [0, 0, None])
            st[0] += 1
            if n > st[1]:
                st[1], st[2] = n, cell_name(c)
        for side in (c.get("sides") or {}).values():
            for m, n in (side.get("masks") or {}).items():
                mask_totals[m] += n
        g = (c["browser"], c["route"])
        pg = per_group.setdefault(g, {"cells": 0, "unregistered": 0, "registered": 0, "errors": 0, "pixel_cells": 0,
                                      "skipped_cells": 0, "seconds": 0.0})
        pg["cells"] += 1
        pg["unregistered"] += ut
        pg["registered"] += res.get("total", 0) - ut
        pg["errors"] += len(c.get("errors", []))
        pg["skipped_cells"] += c.get("status") == "skipped"
        pg["seconds"] += c.get("timing", {}).get("total", 0) or 0
        px = (c.get("pixels") or {}).get("pixels")
        if px:
            pg["pixel_cells"] += 1
            pixels.append({"cell": cell_name(c), **c["pixels"]})
    errors += pool_errors
    errors += [f"registry: {e}" for e in registry.errors]
    unregistered_skips = [s for s in skipped.values() if not s["entries"]]
    rereads = [c["reread"] for c in cells if c.get("reread")]
    status = "PASS" if not (unregistered_total or errors or unregistered_skips or cross_loads) else "FAIL"
    samples = {}
    for c in cells:
        for k, s in ((c.get("result") or {}).get("samples") or {}).items():
            cur = samples.setdefault(k, [])
            for r in s:
                if len(cur) < 3:
                    cur.append(dict(r, cell=cell_name(c)))
    slim = []
    for c in cells:
        d = {k: v for k, v in c.items() if k != "result"}
        res = c.get("result") or {}
        d["result"] = {k: v for k, v in res.items() if k != "samples"}
        slim.append(d)
    kinds = collections.Counter()
    for c in cells:
        kinds.update((c.get("result") or {}).get("counts") or {})
    # The styles mode: state replays per side, and the token names, anchors and probe groups per side.
    styles = None
    if any("states_a" in c or ((c.get("sides") or {}).get("a") or {}).get("tokens") for c in cells):
        tok = [((c.get("sides") or {}).get(s) or {}).get("tokens") for c in cells for s in ("a", "b")]
        tok = [t for t in tok if t]
        styles = {"state_replays": {s: sum(c.get(f"states_{s}") or 0 for c in cells) for s in ("a", "b")},
                  "cells_with_states": sum(1 for c in cells if c.get("states_a")),
                  "token_documents": len(tok), "token_names_max": max((t["names"] for t in tok), default=0),
                  "token_anchors": sum(t["anchors"] for t in tok), "token_ms": round(sum(t.get("ms") or 0 for t in tok))}
    return {
        **run,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": status,
        "totals": {
            "cells": len(cells),
            "cells_by_browser": dict(collections.Counter(c["browser"] for c in cells)),
            "cells_run": sum(1 for c in cells if c.get("status") == "ok"),
            "cells_skipped": sum(1 for c in cells if c.get("status") == "skipped"),
            "elements_compared": sum(((c.get("sides") or {}).get("b") or {}).get("elements") or 0 for c in cells),
            "differences": sum((c.get("result") or {}).get("total", 0) for c in cells),
            "differences_by_kind": dict(kinds),
            "unregistered": unregistered_total,
            "unregistered_cells": len(unreg_cells),
            "registered": sum(registered.values()),
            # differ.js inheritedFrom: records of an inherited longhand that repeat a registered
            # parent's record on its descendants, counted apart (tests/README.md, Divergence registry)
            "inherited": sum((c.get("result") or {}).get("inheritedTotal", 0) for c in cells),
            "harness_errors": len(errors),
            "unregistered_skipped_checks": len(unregistered_skips),
            "pixel_diff_cells": len(pixels),
            "pixel_diff_cells_gt8": sum(1 for p in pixels if p.get("pixels_gt8")),
            "ready_retries": sum(len(c.get("ready_retries") or []) for c in cells),
            "align_fallbacks": sum(c.get("align_fallbacks") or 0 for c in cells),
            "cross_origin_loads": len(cross_loads),
            # owner decision 22: cells read once more, and the records of either read that did not repeat
            # and so do not count (forgiven_first + forgiven_second of each cell's reread; a lower bound
            # when a cell's forgiven_first_at_least is set)
            "reread_cells": len(rereads),
            "reread_forgiven": sum((x.get("forgiven_first") or 0) + (x.get("forgiven_second") or 0) for x in rereads),
            # documents per side whose head held an exact copy of a data block, counted once
            # (differ.js collectHead; tests/README.md, Collection)
            "head_repeat_documents": {s: sum(1 for c in cells if ((c.get("sides") or {}).get(s) or {}).get("head_repeats"))
                                      for s in ("a", "b")},
            "styles": styles,
        },
        "cross_origin_loads": cross_loads,
        # loads from https://femto.style by a same_origin side: the live site, never failing, always listed
        "site_origin_loads": [{"side": k[0], "url": k[1], "cells": len(v), "first_cell": v[0]}
                              for k, v in site_loads.items()],
        "cross_origin_reported": [{"side": k[0], "url": k[1], "routes": sorted(v)} for k, v in cross_reported.items()],
        "ready_retries": [{"cell": cell_name(c), **x} for c in cells for x in (c.get("ready_retries") or [])],
        # the cells' reread without its record lists (first_records, forgiven_*_records, second_records)
        "rereads": [{"cell": cell_name(c), **{k: v for k, v in x.items() if not k.endswith("_records")}} for c, x in
                    ((c, c["reread"]) for c in cells if c.get("reread"))],
        "caps": caps,
        "masked_elements": dict(mask_totals),
        "rig": rigs,
        "harness_errors": errors,
        "skipped_checks": list(skipped.values()),
        "registered_by_entry": dict(registered),
        "inherited_by_entry": dict(inherited),
        "registered_spread": {k: {"cells": v[0], "max_in_one_cell": v[1], "max_cell": v[2],
                                  "broad": v[1] >= BROAD_PER_CELL} for k, v in entry_cells.items()},
        "registered_samples": samples,
        "unused_entries": registry.unused(),
        "pixels": pixels,
        "groups": [{"browser": b, "route": r, **v} for (b, r), v in per_group.items()],
        "cells": slim,
        **(extra or {}),
    }


def summary(result, limit=40) -> str:
    t = result["totals"]
    L = []
    L.append(f"femto.style parity {result['run_id']}  mode={result['mode']}  {result['status']}")
    sides = result.get("sides") or {}
    if sides:
        L.append("A: " + json.dumps(sides.get("a")) + "   B: " + json.dumps(sides.get("b")))
    L.append(f"{result.get('duration_s', 0):.0f}s, {t['cells']} cells " +
             "(" + ", ".join(f"{b} {n}" for b, n in t["cells_by_browser"].items()) + f"), {t['cells_run']} run, "
             f"{t['cells_skipped']} skipped, {t['elements_compared']} elements compared")
    L.append(f"differences {t['differences']}: unregistered {t['unregistered']} in {t['unregistered_cells']} cells, "
             f"registered {t['registered']}" + (f", inherited from registered parents {t['inherited']}" if t.get("inherited") else "")
             + (f"; by kind {t['differences_by_kind']}" if t["differences_by_kind"] else ""))
    if result.get("comparison") == "self":
        L.append("self comparison: only skipped-check entries apply, so every difference counts (criterion 1)")
    st = t.get("styles")
    if st:
        L.append(f"styles: tokens in {st['token_documents']} documents (up to {st['token_names_max']} names, "
                 f"{st['token_anchors']} anchors, {st['token_ms'] / 1000:.0f}s); interactive states replayed "
                 f"{st['state_replays']['a']} times on side A and {st['state_replays']['b']} on side B in "
                 f"{st['cells_with_states']} cells")
    if result.get("comparison") == "styles":
        L.append("styles comparison: only registry entries whose where.comparisons names styles apply (and skipped "
                 "checks); the pages mode's entries do not (tests/README.md, Divergence registry)")
    if result.get("comparison") == "one-page":
        L.append("one-page comparison: only registry entries whose where.comparisons names one-page apply (and skipped "
                 "checks); the pages and styles modes' entries do not (tests/README.md, Divergence registry)")
    if result.get("mode") == "sections":
        L.append("sections: each cell's route is side A's; side B loads the one page at the route's section (url_b) and "
                 "compares the <section> around its id (tests/README.md, Sections)")
    if t.get("align_fallbacks"):
        L.append(f"alignment: {t['align_fallbacks']} sibling lists too long for the LCS table were paired by position")
    hr = t.get("head_repeat_documents") or {}
    if any(hr.values()):
        L.append(f"head data blocks: an exact copy of a data block was counted once in {hr.get('a', 0)} side A and "
                 f"{hr.get('b', 0)} side B documents (tests/README.md, Collection)")
    L.append("")
    shown = 0
    if t["unregistered"]:
        L.append("UNREGISTERED DIFFERENCES (first per cell):")
        for c in result["cells"]:
            res = c.get("result") or {}
            if not res.get("unregisteredTotal"):
                continue
            L.append(f"  {cell_name(c)}: {res['unregisteredTotal']}")
            for r in res.get("unregistered", [])[:5]:
                L.append(f"    {fmt_rec(r)}")
            shown += 1
            if shown >= limit:
                L.append("  ... see result.json")
                break
        L.append("")
    reread = result.get("reread")
    rr = [c for c in result["cells"] if c.get("reread")]
    if reread is not None:
        least = any(c["reread"].get("forgiven_first_at_least") for c in rr)
        L.append(f"REREAD CELLS (owner decision 22; reread set: {', '.join(reread) or 'none'}): {len(rr)} cells, "
                 f"{'at least ' if least else ''}{t.get('reread_forgiven', 0)} records forgiven")
        for c in rr[:limit]:
            x = c["reread"]
            second = "did not finish" if x.get("second_unregistered") is None else f"{x['second_unregistered']} on the reread"
            line = f"  {cell_name(c)}: {x['first_unregistered']} unregistered on the first read, {second}"
            if x.get("forgives_nothing"):
                line += f"; nothing forgiven ({x['forgives_nothing']}): {x.get('counted')} count"
            elif x.get("untold"):
                line += (f"; repeats not told ({x['untold']}): every record of the reread counts ({x.get('counted')}), "
                         f"forgiven {'at least ' if x.get('forgiven_first_at_least') else ''}{x['forgiven_first']} of "
                         "the first read")
            else:
                line += (f", {x['repeated']} repeated; {x.get('counted')} count, forgiven {x['forgiven_first']} of the "
                         f"first read and {x['forgiven_second']} of the reread")
            L.append(line)
            for label, key in (("forgiven, first read", "forgiven_first_records"),
                               ("forgiven, reread", "forgiven_second_records"), ("reread", "second_records")):
                recs = x.get(key) or []
                for r in recs[:5]:
                    L.append(f"    {label}: {fmt_rec(r)}")
                if len(recs) > 5:
                    L.append(f"    ... {len(recs) - 5} more ({key} in result.json)")
            if x.get("untold"):
                for r in (x.get("first_records") or [])[:5]:
                    L.append(f"    first read: {fmt_rec(r)}")
            for label, key in (("first read", "first_pixels"), ("reread", "second_pixels")):
                px = x.get(key) or {}
                if px.get("pixels") == -1:
                    L.append(f"    {label}'s screenshots differ in size: {px.get('size')}")
                elif px.get("pixels"):
                    L.append(f"    {label}'s pixels: {px.get('pixels_gt8', 0)} px > 8/255, {px['pixels']} px in all"
                             + (f" ({px['image']})" if px.get("image") else ""))
        if len(rr) > limit:
            L.append(f"  ... {len(rr) - limit} more in result.json")
        L.append("")
    errs = result["harness_errors"]
    L.append(f"HARNESS ERRORS: {len(errs)}")
    for e in errs[:limit]:
        L.append(f"  {e[:400]}")
    if len(errs) > limit:
        L.append(f"  ... {len(errs) - limit} more in result.json")
    L.append("")
    xl = result.get("cross_origin_loads") or []
    L.append(f"CROSS-ORIGIN LOADS (criterion 15; sides whose target is same_origin, from Resource Timing): {len(xl)}")
    for x in xl[:limit]:
        L.append(f"  {x['cell']} side {x['side']}: {x['url'][:200]}")
    if len(xl) > limit:
        L.append(f"  ... {len(xl) - limit} more in result.json")
    sl = result.get("site_origin_loads") or []
    if sl:
        L.append(f"  from https://femto.style, the deployed site (same origin once deployed, never failing): {len(sl)}")
        for x in sl[:limit]:
            L.append(f"    side {x['side']}: {x['url'][:160]} ({x['cells']} cells, first {x['first_cell']})")
    xr = result.get("cross_origin_reported") or []
    if xr:
        L.append("  reported, not gating (targets not held to same-origin loading):")
        for x in xr[:limit]:
            L.append(f"    side {x['side']}: {x['url'][:160]} ({len(x['routes'])} routes: {', '.join(x['routes'][:4])}"
                     f"{', ...' if len(x['routes']) > 4 else ''})")
    L.append("")
    rr = result.get("ready_retries") or []
    L.append(f"SIDES RELOADED AFTER A READINESS FAILURE: {len(rr)}")
    for x in rr[:limit]:
        L.append(f"  {x['cell']} side {x['side']}: {'; '.join(x['errors'])[:300]}")
    L.append("")
    L.append(f"SKIPPED CHECKS: {len(result['skipped_checks'])}")
    for s in result["skipped_checks"]:
        reg = ", ".join(s["entries"]) if s["entries"] else "UNREGISTERED"
        L.append(f"  {s['browser']} {s['check']}: {s['cells']} cells, {reg}")
    L.append("")
    L.append(f"REGISTERED BY ENTRY: {len(result['registered_by_entry'])}")
    spread = result.get("registered_spread") or {}
    for k, n in sorted(result["registered_by_entry"].items()):
        sp = spread.get(k) or {}
        line = f"  {k}: {n}"
        if (result.get("inherited_by_entry") or {}).get(k):
            line += f" (+{result['inherited_by_entry'][k]} inherited by descendants)"
        if sp:
            line += f" in {sp['cells']} cells, at most {sp['max_in_one_cell']} in one ({sp['max_cell']})"
            if sp.get("broad"):
                line += f"  BROAD: {sp['max_in_one_cell']} records in one cell; check that it hides nothing unrelated"
        L.append(line)
    L.append("")
    un = result["unused_entries"]
    L.append(f"UNUSED REGISTRY ENTRIES: {len(un)}")
    for u in un:
        L.append(f"  {u['id']} ({u['file']}, {u['kind']})")
    L.append("")
    L.append("MASKS: " + ", ".join(f"{m['id']} ({m['selector']})" for m in result.get("masks", [])))
    L.append("  masked elements (both sides, all cells): " + (json.dumps(result.get("masked_elements")) or "{}"))
    L.append("")
    if result["caps"]:
        L.append("MATRIX CAPS:")
        for c in result["caps"]:
            L.append(f"  {c}")
        L.append("")
    L.append(f"PIXEL DIFFS (reported, not gating): {t['pixel_diff_cells_gt8']} cells with pixels off by more than "
             f"8/255, {t['pixel_diff_cells']} with any difference")
    for p in sorted(result["pixels"], key=lambda p: -p.get("pixels_gt8", 0))[:10]:
        L.append(f"  {p['cell']}: {p.get('pixels_gt8', 0)} px > 8/255, {p['pixels']} px in all")
    L.append("")
    L.append("PER BROWSER / ROUTE:")
    for g in result["groups"]:
        L.append(f"  {g['browser']:7} {g['route']:34} cells {g['cells']:4}  unreg {g['unregistered']:6}  "
                 f"reg {g['registered']:6}  err {g['errors']:3}  skip {g['skipped_cells']:3}  px {g['pixel_cells']:3}  "
                 f"{g['seconds']:7.1f}s")
    return "\n".join(L) + "\n"
