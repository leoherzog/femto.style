"""`run.py rig`: start each browser and verify every mechanism the harness relies on."""
import contextlib
import json
import time

from . import locks, matrix
from .browsers import FRAME_HEIGHT, RigError, screen_front_app
from .paths import RESULTS
from .proxy import Proxy
from .runner import PROBE, start_session


def _input_checks(sess):
    """Real pointer and keyboard input on the probe (hover, active, Tab to :focus-visible).
    The pages mode needs none of it; the behavior mode will."""
    ok, why = sess.interactive()
    if not ok:
        return {"interactive": False, "reason": why}
    out = {}
    p = sess.js("pointOf", "hv")
    sess.move(p["x"], p["y"])
    time.sleep(0.05)
    out["hover"] = sess.js("matches", "hv", ":hover")
    sess.park()
    p = sess.js("pointOf", "ac")
    sess.press(p["x"], p["y"])
    try:
        out["active"] = sess.js("matches", "ac", ":active")
    finally:
        sess.release(p["x"], p["y"])
        sess.park()
    sess.js("focusId", "ac")   # the focusable element just before #fv
    sess.tab()
    out["focus-visible"] = sess.js("matches", "fv", ":focus-visible")
    sess.js("focusId", None)
    out["interactive"] = all(out.values())
    return out


def check_browser(browser, log):
    out = {"screen_front_app": screen_front_app()}
    proxy = Proxy({})
    try:
        sess = start_session(browser, proxy, log)
        try:
            out.update(sess.rig)
            conf = matrix.load_config()
            widths = {}
            for w in conf["widths"]:
                ld = sess.ajs("load", PROBE, w, FRAME_HEIGHT, {})
                info = sess.js("check", w, {})
                widths[w] = {"innerWidth": info.get("innerWidth"), "matchMedia": info.get("mqWidth"),
                             "css": info.get("cssWidth"), "errors": ld.get("errors", []) + info.get("errors", [])}
            out["widths"] = widths
            out["widths_ok"] = all(not v["errors"] for v in widths.values())
            schemes = {}
            for leg, (media, theme) in matrix.LEGS.items():
                try:
                    t0 = time.time()
                    sess.set_media(media)
                    sw = round(time.time() - t0, 3)
                except RigError as e:
                    schemes[leg] = {"skipped": str(e)}
                    continue
                ld = sess.ajs("load", PROBE, 1300, FRAME_HEIGHT, {"storage": matrix.storage_for(theme, conf)})
                info = sess.js("check", 1300, {"media": media, "theme": theme})
                pr = sess.js("probePseudos")
                schemes[leg] = {"matchMedia_dark": info.get("dark"), "css_dark": info.get("cssDark"),
                                "data_theme": info.get("theme"), "light_dark_color": pr.get("lightDark"),
                                "switch_s": sw, "errors": ld.get("errors", []) + info.get("errors", [])}
            out["schemes"] = schemes
            sess.ajs("load", PROBE, 1300, FRAME_HEIGHT, {})
            sess.js("configure", {"entries": [], "masks": []})
            out["freeze_on_probe"] = sess.js("freeze")
            t0 = time.time()
            png = sess.frame_png()
            out["screenshot"] = {"bytes": len(png), "s": round(time.time() - t0, 3)}
            out["input"] = _input_checks(sess)
            sess.js("unload")
        finally:
            sess.quit()
    finally:
        proxy.close()
    return out


def run_rig(args):
    run_id = args.run_id or f"{time.strftime('%Y%m%d-%H%M%S')}-rig"
    report = {}
    log = lambda m: print(f"{time.strftime('%H:%M:%S')} {m}", flush=True)
    status = 0
    for b in [x.strip() for x in args.browsers.split(",") if x.strip()]:
        try:
            with locks.slot(f"{run_id} rig {b}", log):
                guard = locks.safari(f"{run_id} rig", log) if b == "safari" else contextlib.nullcontext()
                with guard:
                    report[b] = check_browser(b, log)
            if not report[b].get("widths_ok") or any(v.get("errors") for v in report[b].get("schemes", {}).values()):
                status = 1
        except Exception as e:
            report[b] = {"error": repr(e)}
            status = 1
        print(f"{b}: {json.dumps(report[b], indent=1)}", flush=True)
    d = RESULTS / run_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "rig.json").write_text(json.dumps(report, indent=1))
    print(f"wrote {d}/rig.json")
    return status
