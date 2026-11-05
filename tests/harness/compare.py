"""One comparison cell: load side A's document, wait for it, check the environment, collect; the same
for side B in a fresh iframe; diff in the page; screenshot both sides (never gating). In the styles
mode the collect also reads the tokens, and each side replays its interactive states after its
collect (harness/styles.py). In the sections mode (harness/sections.py) the two sides load different
URLs (the cell's url_b: /docs#<id>) and compare different roots (root_b: the section around the id)."""
import io
import re
import time
from urllib.parse import urlsplit

from . import matrix
from .browsers import FRAME_HEIGHT, RigError
from .proxy import document_status, strip_load_param, with_load_param
from .targets import run_ready

SITE_ORIGIN = ("https", "femto.style", 443)  # the deployed site's origin: same-origin once deployed


def site_origin(url):
    """True for a URL on https://femto.style (default port), the site's own origin once deployed, as
    static_checks.same_origin() reads it; http://femto.style and other ports are other origins."""
    u = urlsplit(url)
    try:
        port = u.port or (443 if u.scheme == "https" else None)
    except ValueError:
        return False
    return (u.scheme, (u.hostname or ""), port) == SITE_ORIGIN


def new_result(cap):
    return {"total": 0, "unregisteredTotal": 0, "unregistered": [], "registered": {}, "samples": {}, "counts": {},
            "inheritedTotal": 0, "inherited": {}, "_cap": cap}


def merge(total, part):
    if not part:
        return
    total["total"] += part.get("total", 0)
    total["unregisteredTotal"] += part.get("unregisteredTotal", 0)
    room = total["_cap"] - len(total["unregistered"])
    if room > 0:
        total["unregistered"].extend(part.get("unregistered", [])[:room])
    for k, n in part.get("registered", {}).items():
        total["registered"][k] = total["registered"].get(k, 0) + n
    # records folded into a registered parent's record (differ.js inheritedFrom)
    total["inheritedTotal"] += part.get("inheritedTotal", 0)
    for k, n in part.get("inherited", {}).items():
        total["inherited"][k] = total["inherited"].get(k, 0) + n
    for k, s in part.get("samples", {}).items():
        cur = total["samples"].setdefault(k, [])
        cur.extend(s[: max(0, 2 - len(cur))])
    for k, n in part.get("counts", {}).items():
        total["counts"][k] = total["counts"].get(k, 0) + n


def _add_python_record(res, rec, hits):
    """A record found in Python (kind status) goes through the same bookkeeping as in-page ones."""
    res["total"] += 1
    res["counts"][rec["kind"]] = res["counts"].get(rec["kind"], 0) + 1
    if not hits:
        res["unregisteredTotal"] += 1
        if len(res["unregistered"]) < res["_cap"]:
            res["unregistered"].append(rec)
        return
    for i in hits:
        res["registered"][i] = res["registered"].get(i, 0) + 1
        s = res["samples"].setdefault(i, [])
        if len(s) < 2:
            s.append(rec)


def same_origin_loads(out, side, tgt, req):
    """Record a side's cross-origin loads (differ.js resources(): the Resource Timing entries of the
    document and its frames; csp_loads() adds the proxy's CSP reports at the end of the cell). For a
    target marked same_origin in targets.json (the static site, the fixture), each
    one is a criterion 15 failure, kept in out["cross_origin_loads"] and judged by report.py outside
    the diff, so no registry entry can absorb it. https://femto.style/ URLs (that scheme, host and
    default port only) are the site's own origin once deployed: listed per side under
    site_origin_loads and in the summary, never failing. Other targets (the oracle) are only
    reported."""
    if req is None:  # the collect failed; its errors are already the cell's
        return
    info = out["sides"][side]
    info["resources"] = req.get("total")
    info["cross_origin"] = req.get("cross", [])
    info["frames_read"] = req.get("frames", 0)
    if req.get("unreadable"):
        info["frames_unreadable"] = req["unreadable"]
    required = bool(getattr(tgt, "conf", {}).get("same_origin"))
    info["same_origin_required"] = required
    if not required:
        return
    if req.get("error") or req.get("origin") is None:
        out["errors"].append(f"{side} requests: cannot read the document's Resource Timing entries: {req.get('error')}")
    if req.get("full"):
        out["errors"].append(f"{side} requests: a Resource Timing buffer is full (250 entries in one document; "
                             f"{req.get('total')} in all), so later loads are not listed and the same-origin check is "
                             "incomplete")
    for where in req.get("unreadable") or []:
        out["errors"].append(f"{side} requests: cannot read the Resource Timing entries of {where} (another origin, or "
                             "sandboxed without allow-same-origin), so its loads are not checked")
    for url in req.get("cross", []):
        if site_origin(url):
            info.setdefault("site_origin_loads", []).append(url)
        else:
            out.setdefault("cross_origin_loads", []).append({"side": side, "url": url})


def _origin(url):
    u = urlsplit(url)
    try:
        port = u.port
    except ValueError:
        port = None
    return (u.scheme, u.hostname or "", port or {"http": 80, "https": 443, "ws": 80, "wss": 443}.get(u.scheme))


def csp_loads(out, side, tgt, reports, late=False):
    """Add a side's CSP reports (proxy.py: every document, frame and worker the side served carries
    a report-only policy that reports any other origin) to its cross-origin loads. A URL Resource
    Timing already listed is not repeated (Firefox and Chrome report a load's full URL, or only its
    origin after a redirect, which then matches a listed URL's origin). For a same_origin target each
    new one fails the run like any other cross-origin load. Reports whose blocked URI is not a URL
    (inline, eval) would mean the policy itself is wrong: they are kept under csp_other."""
    info = out.setdefault("sides", {}).setdefault(side, {})
    info["csp_reports"] = info.get("csp_reports", 0) + len(reports)
    listed = list(info.get("cross_origin") or [])
    origins = {_origin(u) for u in listed}
    required = bool(getattr(tgt, "conf", {}).get("same_origin"))
    for rep in reports:
        url = rep.get("blocked") or ""
        if not re.match(r"(?i)(https?|wss?)://", url):
            other = info.setdefault("csp_other", [])
            if len(other) < 20:
                other.append(f"{rep.get('directive')}: {url or '(none)'} in {rep.get('document')}")
            continue
        bare = re.fullmatch(r"(?i)(https?|wss?)://[^/?#]+/?", url) is not None
        if url in listed or (bare and _origin(url) in origins):
            continue
        listed.append(url)
        origins.add(_origin(url))
        info.setdefault("csp_cross_origin", []).append(url + (" (reported after the cell)" if late else ""))
        if not required:
            info.setdefault("cross_origin", []).append(url)
        elif site_origin(url):
            info.setdefault("site_origin_loads", []).append(url)
        else:
            info.setdefault("cross_origin", []).append(url)
            out.setdefault("cross_origin_loads", []).append(
                {"side": side, "url": url, "via": f"CSP report ({rep.get('directive')} in {rep.get('document')})"
                                                  + (", after the cell" if late else "")})


def attach_late_reports(proxy):
    """CSP reports that reached the proxy after their cell took its tag's reports: added to that
    cell's record (still in memory until the run's result is built)."""
    owners = getattr(proxy, "owners", {})
    for tag, reps in proxy.late_reports().items():
        if tag in owners:
            out, side, tgt = owners[tag]
            csp_loads(out, side, tgt, reps, late=True)


def _finish(out, res, t0, status):
    res.pop("_cap", None)
    out["result"] = res
    out["status"] = status
    out["timing"]["total"] = round(time.time() - t0, 2)
    return out


def run_cell(sess, cell, registry, opts, sides, shot_path=None):
    """Run one cell and return its record (cell fields plus result, errors, skipped, sides, timing)."""
    t0 = time.time()
    out = dict(cell)
    out.update(errors=[], skipped=[], timing={}, sides={})
    res = new_result(opts.max_records)
    media, theme = cell["media"], cell["theme"]

    # Safari cannot emulate prefers-color-scheme: run the OS scheme and register the missing leg.
    if sess.browser == "safari" and media != sess.os_scheme:
        out["skipped"].append(f"media:{media}")
        if theme is None:
            return _finish(out, res, t0, "skipped")
        media = sess.os_scheme
        out["media_used"] = media
    for ps in sess.unsupported_pseudos:
        out["skipped"].append(f"pseudo:{ps}")

    try:
        sess.set_media(media)
    except RigError as e:
        out["errors"].append(f"rig: {e}")
        return _finish(out, res, t0, "error")

    styles = getattr(opts, "styles", None)
    conf = sess.js("configure", {"entries": registry.for_cell(cell), "masks": opts.masks,
                                 "maxRecords": opts.max_records, "pseudos": sess.pseudos,
                                 "blobUuid": bool(getattr(opts, "blob_uuid", True)),
                                 "minified": bool(getattr(opts, "minified", True)),
                                 "breadth": registry.limits(),
                                 **(styles.configure_args() if styles else {})})
    targets = styles.states.for_cell(cell) if styles and styles.states else []
    out["errors"] += conf.get("errors", [])
    opts.value_rules = conf.get("valueRules")
    storage = matrix.storage_for(theme, opts.conf)
    pngs = {}
    tags = {}
    attach_late_reports(sess.proxy)
    if not hasattr(sess.proxy, "owners"):
        sess.proxy.owners = {}
    try:
        for side in ("a", "b"):
            tgt = sides[side]
            ts = time.time()
            tags[side] = sess.proxy.new_tag(side)
            sess.proxy.owners[tags[side]] = (out, side, tgt)
            sess.proxy.use(side, tags[side])
            # A section cell loads side B's one page at its section (url_b) and compares that
            # section (root_b); every other side loads the route and compares its own root.
            root = cell.get(f"root_{side}") or tgt.root
            for attempt in range(2):
                # Safari gets a URL no other load had (proxy.py, harness-load); the proxy forwards
                # and logs the route without it, and the cell records the route.
                url = cell.get(f"url_{side}") or cell["route"]
                if sess.browser == "safari":
                    url = with_load_param(url, f"{tags[side]}.{attempt}")
                ld = sess.ajs("load", url, cell["width"], FRAME_HEIGHT, {"storage": storage})
                if not ld.get("path"):
                    break
                ld["path"] = strip_load_param(ld["path"])
                # The proxy could not get the document from the side's server (it refused or did not
                # answer within the proxy's 60 s): the iframe holds the proxy's error page, not the
                # side's document. Load it once more, like a readiness failure.
                upstream = sess.proxy.document_error(ld["path"])
                ready_errors = [f"proxy: GET {ld['path']}: {upstream}"] if upstream else run_ready(sess, tgt)
                if not ready_errors:
                    break
                # A side that never became ready is loaded once more; the cell records the first
                # attempt (rig notes: headless Chrome's stalled idle periods, before the host page
                # kicked frames during loads).
                failed = sess.proxy.take_log()
                out.setdefault("ready_retries", []).append(
                    {"side": side, "errors": ready_errors, "requests": len(failed),
                     "http_errors": [f"{r['status']} {r['method']} {r['path']}" for r in failed if r["status"] >= 400][:10]})
                if attempt == 1:
                    out["errors"] += [f"{side} {e} (after one reload)" for e in ready_errors]
            sess.js("kick", False)
            out["errors"] += [f"{side} load: {e}" for e in ld.get("errors", [])]
            if not ld.get("path"):
                out["sides"][side] = {"requests": sess.proxy.take_log()}
                return _finish(out, res, t0, "error")
            chk = sess.js("check", cell["width"], {"media": media, "theme": theme})
            out["errors"] += [f"{side} {e}" for e in chk.get("errors", [])]
            col = sess.ajs("collect", side, root)
            out["errors"] += [f"{side} collect: {e}" for e in col.get("errors", [])]
            log = sess.proxy.take_log()
            bad = [r for r in log if r["status"] >= 400 or r.get("error")]
            out["errors"] += [f"{side} proxy: {r['method']} {r['path']}: {r['error']}" for r in bad if r.get("error")]
            out["sides"][side] = {
                "path": ld["path"], "status": document_status(log, ld["path"]), "requests": len(log),
                "http_errors": [f"{r['status']} {r['method']} {r['path']}" for r in bad][:20],
                "elements": col.get("elements"), "pseudo_elements": col.get("pseudo"), "masks": col.get("maskCounts", {}),
                "head_entries": col.get("head"),
                # exact copies of a data block counted once (differ.js collectHead; README, Collection)
                "head_repeats": col.get("headRepeats"),
                "content_type": ld.get("contentType"),
                "freeze": {k: col.get(k) for k in ("freezeBefore", "freezeTouched", "freezeAfter")},
            }
            if col.get("tokens"):
                out["sides"][side]["tokens"] = col["tokens"]
            same_origin_loads(out, side, tgt, col.get("requests"))
            # An animation that starts while the styles are read means a value may have been read
            # mid-transition: the cell cannot be trusted. One that animates only longhands a mask
            # leaves uncompared on its element is counted apart ("masked"; differ.js freeze).
            late = col.get("freezeAfter") or {}
            if late.get("finished") or late.get("paused"):
                out["errors"].append(f"{side} collect: {late.get('finished', 0)} animations finished and "
                                     f"{late.get('paused', 0)} paused after the styles were read")
            out["timing"][f"{side}_load"] = round(ld.get("ms", 0) / 1000, 2)
            out["timing"][f"{side}_collect"] = round(col.get("ms", 0) / 1000, 2)
            if "elements" not in col:
                return _finish(out, res, t0, "error")
            if side == "b":
                d = sess.js("diff")
                out["errors"] += [f"diff: {e}" for e in d.get("errors", [])]
                merge(res, d)
                out["timing"]["diff"] = round(d.get("ms", 0) / 1000, 2)
                if d.get("alignFallbacks"):
                    # A sibling list too long for the LCS table was paired by position: every pair is
                    # still compared, but the records may name neighbours (reported, not an error).
                    out["align_fallbacks"] = d["alignFallbacks"]
            if targets:
                from .styles import replay
                replay(sess, side, cell, targets, registry, out, res, merge)
            if opts.shots:
                sess.ajs("prepShot", root)
                pngs[side] = sess.frame_png()
                sess.js("unmask")
            # Remove the document before the proxy switches sides: nothing it still requests may
            # reach the other side's server.
            sess.js("unload")
            out["timing"][side] = round(time.time() - ts, 2)
    finally:
        sess.proxy.use(None)
        # Side A's reports had all of side B's load to arrive; side B's arrive with its own load.
        for side, tag in tags.items():
            csp_loads(out, side, sides[side], sess.proxy.take_reports(tag))

    a, b = out["sides"]["a"], out["sides"]["b"]
    # A section cell's sides answer different paths: side A its route, side B the one page (path_b,
    # with ?theme=<color> on a color route); each must be the one asked for, with the same status.
    want_b = cell.get("path_b")
    if want_b is None:
        differ = (a["status"], a["path"]) != (b["status"], b["path"])
    else:
        differ = a["status"] != b["status"] or a["path"] != cell["route"] or b["path"] != want_b
    if differ:
        rec = {"kind": "status", "path": cell["route"], "label": cell["route"],
               "a": f"{a['status']} {a['path']}", "b": f"{b['status']} {b['path']}"}
        _add_python_record(res, rec, registry.match_python(rec, cell))
    if len(pngs) == 2:
        out["pixels"] = pixel_diff(pngs["a"], pngs["b"], shot_path)
    return _finish(out, res, t0, "ok")


def pixel_diff(a: bytes, b: bytes, path=None):
    """Count differing pixels between two PNGs; save both and a diff mask when any differ by more
    than 8/255 (Chrome's raster varies by 1/255 between identical loads)."""
    from PIL import Image, ImageChops
    ia, ib = Image.open(io.BytesIO(a)).convert("RGB"), Image.open(io.BytesIO(b)).convert("RGB")
    if ia.size != ib.size:
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            ia.save(path.with_name(path.stem + "-a.png"))
            ib.save(path.with_name(path.stem + "-b.png"))
        return {"pixels": -1, "size": [list(ia.size), list(ib.size)]}
    d = ImageChops.difference(ia, ib)
    if not d.getbbox():
        return {"pixels": 0}
    r, g, bl = d.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), bl)
    hist = m.histogram()
    px = sum(hist[1:])
    out = {"pixels": px, "pixels_gt8": sum(hist[9:]), "bbox": list(d.getbbox())}
    if path and out["pixels_gt8"]:
        path.parent.mkdir(parents=True, exist_ok=True)
        m.point(lambda v: 255 if v else 0).save(path)
        ia.save(path.with_name(path.stem + "-a.png"))
        ib.save(path.with_name(path.stem + "-b.png"))
        out["image"] = str(path)
    return out
