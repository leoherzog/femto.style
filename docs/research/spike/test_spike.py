# /// script
# requires-python = ">=3.12"
# dependencies = ["selenium==4.52.0"]
# ///
# Checks the spike's scroll spy, #hash sync, deep links, history and ?theme= stylesheet in the
# browsers femto's parity rig drives: Chrome Beta and Firefox headless, Chrome Beta with JavaScript
# off, and Safari in a visible window (WebDriver cannot turn JavaScript off in Safari).
# With --probes it also measures what the checks take for granted, per browser: when each ?theme=
# method's stylesheet applies against the first frame and the first contentful paint; the history
# API rate limit and the spy behind it; a fast scroll paced in the page; and whether a deep link, a
# click, back and forward animate, with the spike's click-only class and with today's
# html { scroll-behavior: smooth } (docs-smooth.html).
# Each session holds one of femto's machine-wide harness slots and starts its driver under femto's
# driver-start lock. Safari also holds femto's Safari lock, and runs only when the screen is unlocked
# and the user's own Safari is not running (femto tests/README.md, "Concurrency and locks" and
# "Rig notes"). Start serve.py first.
# Run: uv run docs/research/spike/test_spike.py PORT [chrome] [firefox] [chrome-nojs] [safari] [--probes]
# With no browser named it runs chrome, firefox and chrome-nojs. Run Safari as
# caffeinate -d -i uv run docs/research/spike/test_spike.py PORT safari --probes
import contextlib
import fcntl
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

BASE = f"http://127.0.0.1:{sys.argv[1] if len(sys.argv) > 1 else 8790}"
CHROME = "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta"
FIREFOX = "/Applications/Firefox.app/Contents/MacOS/firefox"
SAFARIDRIVER = "/usr/bin/safaridriver"
SAFARI_WINDOW = (1280, 852)  # an inner 1280×800 under Safari's 52 px toolbar, like the headless browsers
JADE = "light-dark(#007a50, #00b478)"
LOCK_DIR = Path(os.environ.get("FEMTO_HARNESS_LOCK_DIR", Path.home() / ".cache" / "femto-harness" / "locks"))
SLOTS = [f"slot-{i}.lock" for i in range(max(1, int(os.environ.get("FEMTO_HARNESS_SLOTS", "4"))))]


@contextlib.contextmanager
def hold(names, label):
    """Holds the first free lock among `names`, the way femto's harness does: an flock on a file in
    LOCK_DIR that names its owner and is released when this process exits."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    announced = 0.0
    while True:
        for name in random.sample(names, len(names)):
            f = open(LOCK_DIR / name, "a+")
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
                yield
            finally:
                f.seek(0)
                f.truncate()
                fcntl.flock(f, fcntl.LOCK_UN)
                f.close()
            return
        if time.time() - announced > 60:
            print(f"   {label}: waiting for {' or '.join(names)}", flush=True)
            announced = time.time()
        time.sleep(0.5 + random.random())


class Blocked(Exception):
    """A precondition for a session does not hold; the session did not run."""


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def safari_pids():
    """(automation, user) pids of running Safari processes. Only safaridriver starts Safari with
    --automation; the user's own Safari never carries it."""
    automation, user = [], []
    for pid in sh("pgrep", "-x", "Safari").split():
        (automation if "--automation" in sh("ps", "-o", "args=", "-p", pid) else user).append(pid)
    return automation, user


def kill_automation_safari():
    """Terminates Safari instances that safaridriver launched. One left by a session that died stays
    paired, and new sessions are refused with "already paired with a different session"."""
    automation, _ = safari_pids()
    for pid in automation:
        subprocess.run(["kill", pid], capture_output=True)
    if automation:
        time.sleep(3)
    return automation


def safari_preconditions():
    front = sh("lsappinfo", "info", "-only", "name", sh("lsappinfo", "front").strip())
    if "loginwindow" in front:
        raise Blocked(f"the screen is locked (lsappinfo front: {front.strip()})")
    _, user = safari_pids()
    if user:
        raise Blocked(f"the user's Safari is running (pid {', '.join(user)}); quit it first")


def idle_s():
    """Seconds since the last real keyboard or pointer input. safaridriver's synthesized input does
    not reset it, so it tells whether someone used the machine during a Safari session."""
    for line in sh("ioreg", "-c", "IOHIDSystem").splitlines():
        if '"HIDIdleTime"' in line:
            return int(line.rsplit("=", 1)[1]) / 1e9
    return None


@contextlib.contextmanager
def session(name, make):
    """One WebDriver session holding a harness slot (and for Safari the Safari lock) for its lifetime."""
    label = f"femto.style spike {name}"
    with hold(SLOTS, label):
        with hold(["safari.lock"], label) if name == "safari" else contextlib.nullcontext():
            if name == "safari":
                safari_preconditions()
            with hold(["driver-start.lock"], label):
                d = make()
            try:
                d.set_script_timeout(30)
                yield d
            finally:
                try:
                    d.quit()
                finally:
                    if name == "safari":
                        kill_automation_safari()


STATE = """return {
  url: location.pathname + location.search + location.hash,
  title: document.title,
  nav: document.querySelector('#docs-nav [aria-current]')?.textContent ?? null,
  y: Math.round(scrollY),
  history: history.length,
};"""


def chrome(js=True):
    o = webdriver.ChromeOptions()
    o.binary_location = CHROME
    for a in ("--headless", "--window-size=1280,800", "--force-device-scale-factor=1"):
        o.add_argument(a)
    if not js:
        o.add_experimental_option("prefs", {"profile.managed_default_content_settings.javascript": 2})
    return webdriver.Chrome(options=o)


def firefox():
    o = webdriver.FirefoxOptions()
    o.binary_location = FIREFOX
    for a in ("-headless", "--width=1280", "--height=800"):
        o.add_argument(a)
    return webdriver.Firefox(options=o, service=Service())


def safari():
    from selenium.common.exceptions import SessionNotCreatedException
    from selenium.webdriver.safari.service import Service as SafariService

    # The Safari lock is held, so no other session is live: start from no automation instance.
    kill_automation_safari()
    try:
        d = webdriver.Safari(service=SafariService(executable_path=SAFARIDRIVER))
    except SessionNotCreatedException as e:
        if "already paired" not in str(e) or not kill_automation_safari():
            raise
        d = webdriver.Safari(service=SafariService(executable_path=SAFARIDRIVER))
    d.set_window_rect(0, 0, *SAFARI_WINDOW)
    try:
        d.command_executor.client_config.timeout = 60  # fail a hung command after 60 s
    except AttributeError:
        pass
    return d


def top_of(d, sid):
    return d.execute_script(f"return Math.round(document.getElementById('{sid}').getBoundingClientRect().top)")


def click_nav(d, sid):
    """Clicks a nav link with WebDriver's element click, which is real input, so the page sees a user
    gesture as it does for a reader's click. A script's element.click() has none, and WebKit's back
    skips over history entries made without one: in Safari 27.2, back from the entry such a click
    made went two entries back."""
    d.find_element(By.CSS_SELECTOR, f'#docs-nav a[href="#{sid}"]').click()


def run(name, d):
    results = []

    def check(label, ok, detail):
        results.append((label, ok, detail))

    def state():
        return d.execute_script(STATE)

    def scroll_to(js_y, wait=0.6):
        d.execute_script(f"window.scrollTo({{top: {js_y}, behavior: 'instant'}})")
        time.sleep(wait)

    # 1. A deep link is the browser's own fragment scroll; the spy marks the section.
    d.get(BASE + "/docs#input")
    time.sleep(0.8)
    s, top = state(), top_of(d, "input")
    check("deep link /docs#input", s["nav"] == "Input" and s["title"] == "Input • femto" and 60 < top < 140, {**s, "headingTop": top})

    # 2. Scrolling writes the section's #hash and title.
    d.get(BASE + "/docs")
    time.sleep(0.4)
    scroll_to("document.getElementById('grid').closest('section').offsetTop - 40")
    s = state()
    check("scroll into Grid → #grid", s["url"] == "/docs#grid" and s["title"] == "Grid • femto", s)

    # 3. Back at the top, the hash goes and the title is the page's own.
    scroll_to(0)
    s = state()
    check("top → /docs, no hash", s["url"] == "/docs" and s["title"] == "Documentation • femto" and s["nav"] == "Quick start", s)

    # 4. The short last section wins at the bottom.
    scroll_to("document.documentElement.scrollHeight")
    s = state()
    check("bottom → #tooltip", s["url"] == "/docs#tooltip" and s["nav"] == "Tooltip", s)

    # 5. A fast scroll through everything makes few history calls.
    scroll_to(0, 0.4)
    d.execute_script("window.__r = 0; const o = history.replaceState.bind(history); history.replaceState = (...a) => (window.__r++, o(...a));")
    height = d.execute_script("return document.documentElement.scrollHeight")
    for y in range(0, height, 200):
        d.execute_script(f"window.scrollTo({{top: {y}, behavior: 'instant'}})")
        time.sleep(0.016)
    time.sleep(0.6)
    calls, s = d.execute_script("return window.__r"), state()
    check("fast scroll top→bottom", calls <= 3 and s["url"] == "/docs#tooltip", {**s, "replaceStateCalls": calls})

    # 6. A nav click is a native fragment navigation: one history entry, a smooth scroll, no flicker.
    scroll_to("document.getElementById('modal').closest('section').offsetTop + 200")
    before = state()
    d.execute_script("window.__navSeen = []; new MutationObserver(() => window.__navSeen.push(document.querySelector('#docs-nav [aria-current]')?.textContent)).observe(document.getElementById('docs-nav'), {subtree: true, attributes: true, attributeFilter: ['aria-current']});")
    click_nav(d, "container")
    time.sleep(1.8)
    after, seen = state(), d.execute_script("return window.__navSeen")
    top = top_of(d, "container")
    check("nav click → #container", after["url"] == "/docs#container" and after["history"] == before["history"] + 1
          and after["nav"] == "Container" and 60 < top < 140 and set(filter(None, seen)) <= {"Container"},
          {"before": before, "after": after, "navSeen": seen, "headingTop": top})

    # 7. Back returns to the old entry: Firefox restores the exact position, Chrome scrolls to the
    # entry's #hash heading. Either is fine; the spy must follow.
    d.back()
    time.sleep(1.2)
    back, top = state(), top_of(d, "modal")
    exact = abs(back["y"] - before["y"]) < 5
    check("back returns (exact or to #modal)", back["url"] == before["url"] and (exact or 60 < top < 140) and back["nav"] == "Modal",
          {"before": before, "back": back, "headingTop": top, "exact": exact})
    print(f"   {name}: back {'restored the exact position' if exact else 'scrolled to the #hash heading'}"
          f" (y before the click {before['y']}, after back {back['y']}; #modal heading at {top} px)")
    d.forward()
    time.sleep(1.2)
    fwd = state()
    check("forward returns", fwd["url"] == "/docs#container" and fwd["nav"] == "Container", fwd)

    # 8. Reload mid-section: Chrome and Firefox restore the exact position, Safari scrolls to the
    # #hash heading, as Chrome does on back. Either is fine (the owner, 2026-11-02).
    scroll_to("document.getElementById('css-variables').closest('section').offsetTop + 900")
    before = state()
    d.execute_script("location.reload()")
    time.sleep(1.5)
    after, top = state(), top_of(d, "css-variables")
    exact = abs(after["y"] - before["y"]) < 5
    check("reload returns (exact or to #css-variables)", after["url"] == before["url"] and (exact or 60 < top < 140)
          and after["nav"] == "CSS variables", {"before": before, "after": after, "headingTop": top, "exact": exact})
    print(f"   {name}: location.reload() {'kept the exact position' if exact else 'scrolled to the #hash heading'}"
          f" (y before {before['y']}, after {after['y']}; #css-variables heading at {top} px)")
    d.refresh()
    time.sleep(1.5)
    hard, top = state(), top_of(d, "css-variables")
    check("hard reload shows the section", hard["url"] == before["url"] and hard["nav"] == "CSS variables",
          {"before": before, "after": hard, "headingTop": top})
    print(f"   {name}: WebDriver refresh: y {hard['y']}, #css-variables heading at {top} px")

    # 9. ?theme= applies before the first frame, by either insertion method, and survives the spy and clicks.
    for method in ("append", "blocking", "write"):
        d.get(BASE + f"/docs?theme=jade&method={method}#grid")
        time.sleep(1.0)
        first = d.execute_script("return window.__firstFrame")
        now = d.execute_script("return getComputedStyle(document.documentElement).getPropertyValue('--femto-primary').trim()")
        ok = first == JADE and now == JADE
        print(f"   {name}: ?theme= by {method}: {'before' if ok else 'after'} the first frame")
        if method == "write":
            check("?theme=jade before first frame (document.write)", ok, {"firstFrame": first, "afterLoad": now})
    scroll_to("document.getElementById('modal').closest('section').offsetTop - 40")
    click_nav(d, "forms")
    time.sleep(1.8)
    s = state()
    check("?theme= kept by spy and clicks", s["url"] == "/docs?theme=jade&method=write#forms", s)
    # The first section's heading lands on the scroll-padding line, as every nav click's does, and the
    # spy then drops the hash. Where that leaves the page depends on the padding (y 10 in Chrome and
    # Firefox at a 100 px padding, 30 in Safari 27.2 at 80 px), so the check reads the heading, not the page's y.
    click_nav(d, "quick-start")
    time.sleep(1.8)
    s, top = state(), top_of(d, "quick-start")
    check("Quick start click → plain /docs", s["url"] == "/docs?theme=jade&method=write" and 60 < top < 140,
          {**s, "headingTop": top})
    print(f"   {name}: Quick start click: y {s['y']}, #quick-start heading at {top} px")

    print(f"\n== {name} {d.capabilities.get('browserVersion')}")
    for label, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            print("      " + json.dumps(detail))
    return all(ok for _, ok, _ in results)


def run_without_js(d):
    d.get(BASE + "/docs#forms")
    time.sleep(0.8)
    top, y = top_of(d, "forms"), d.execute_script("return Math.round(scrollY)")
    ok = 60 < top < 140 and y > 0
    print(f"\n== chrome, JavaScript off\n{'PASS' if ok else 'FAIL'}  deep link /docs#forms scrolls natively")
    if not ok:
        print("      " + json.dumps({"headingTop": top, "y": y}))
    return ok




# --- Probes: measurements behind the checks, printed for every browser so they compare -----------

PRIMARY = "return getComputedStyle(document.documentElement).getPropertyValue('--femto-primary').trim()"

THEME_TIMING = """const entry = performance.getEntriesByName(new URL(arguments[0], location.href).href)[0];
const fcp = performance.getEntriesByName("first-contentful-paint")[0];
return {
  firstFrame: window.__firstFrame ?? null,
  firstFrameAt: window.__firstFrameAt ?? null,
  themeResponseEnd: entry ? Math.round(entry.responseEnd) : null,
  firstContentfulPaint: fcp ? Math.round(fcp.startTime) : null,
  afterLoad: getComputedStyle(document.documentElement).getPropertyValue("--femto-primary").trim(),
};"""

# Calls replaceState 250 times at once, each to a new #burst-N, and records which calls threw and
# which took effect; errors that reach the window from then on are collected.
BURST = """window.__errors = [];
addEventListener("error", (e) => __errors.push(String(e.message)));
addEventListener("unhandledrejection", (e) => __errors.push(String(e.reason)));
window.__burstStart = Date.now();
let applied = 0, thrown = 0, firstThrow = null, error = null;
for (let i = 1; i <= 250; i++) {
  const hash = `#burst-${i}`;
  try {
    history.replaceState(history.state, "", location.pathname + location.search + hash);
  } catch (e) {
    thrown++;
    if (firstThrow === null) [firstThrow, error] = [i, `${e.name}: ${e.message}`];
    continue;
  }
  if (location.hash === hash) applied++;
}
return {calls: 250, applied, thrown, firstThrow, error, ms: Date.now() - __burstStart, hash: location.hash};"""

# Scrolls the whole page 200 px every 16 ms from inside the page, counting the spy's replaceState calls.
FAST_SCROLL = """const done = arguments[arguments.length - 1];
window.__r = 0;
const original = history.replaceState.bind(history);
history.replaceState = (...a) => (window.__r++, original(...a));
const height = document.documentElement.scrollHeight;
const t0 = performance.now();
let y = 0, steps = 0;
(function step() {
  scrollTo({top: y, behavior: "instant"});
  steps++;
  y += 200;
  if (y < height) return setTimeout(step, 16);
  const scrollMs = Math.round(performance.now() - t0);
  setTimeout(() => done({height, steps, scrollMs, replaceStateCalls: window.__r, hash: location.hash}), 600);
})();"""

SCROLL_SUMMARY = """const s = window.__scrolls;
return {
  events: s.length,
  spanMs: s.length ? s.at(-1)[0] - s[0][0] : 0,
  positions: new Set(s.map((e) => e[1])).size,
  firstEventY: s.length ? s[0][1] : null,
  y: Math.round(scrollY),
  url: location.pathname + location.hash,
};"""


def animated(log):
    """An instant jump fires one scroll event (two at most); an animation fires one per frame."""
    return log["events"] >= 3 and log["positions"] >= 3 and log["spanMs"] >= 100


def probe_theme(name, d):
    """Each ?theme= method on a color not loaded before in the session, so no cache helps it."""
    d.get(BASE + "/docs")
    time.sleep(0.5)
    default = d.execute_script(PRIMARY)
    out = {"default": default}
    for method, color in (("write", "pumpkin"), ("append", "violet"), ("blocking", "cyan")):
        d.get("about:blank")
        d.get(BASE + f"/docs?theme={color}&method={method}")
        time.sleep(1.2)
        r = d.execute_script(THEME_TIMING, f"/themes/{color}.css")
        r["color"] = color
        r["inFirstFrame"] = r["firstFrame"] == r["afterLoad"] != default
        fcp, end = r["firstContentfulPaint"], r["themeResponseEnd"]
        r["firstPaintAfterTheme"] = None if fcp is None or end is None else fcp >= end
        out[method] = r
        paint = {None: "no paint timing", True: "after", False: "BEFORE"}[r["firstPaintAfterTheme"]]
        print(f"   {name}: ?theme= by {method} ({color}): first frame {'in' if r['inFirstFrame'] else 'NOT in'} the theme "
              f"(frame at {r['firstFrameAt']} ms, theme response end {end} ms); first contentful paint at {fcp} ms, "
              f"{paint} the theme arrived")
    return out


def probe_history(name, d):
    """The history API rate limit, and the spy within it: the nav and title keep following, nothing
    reaches the window, and the URL catches up once the 10 s window is over."""
    d.get("about:blank")
    d.get(BASE + "/docs")
    time.sleep(0.5)
    burst = d.execute_script(BURST)
    d.execute_script("scrollTo({top: document.getElementById('grid').closest('section').offsetTop - 40, behavior: 'instant'})")
    time.sleep(0.8)
    during = d.execute_script(STATE)
    during["errors"] = d.execute_script("return window.__errors")
    during["sinceBurstMs"] = d.execute_script("return Date.now() - window.__burstStart")
    time.sleep(max(0.0, 10.5 - during["sinceBurstMs"] / 1000))
    d.execute_script("scrollBy({top: 60, behavior: 'instant'})")
    time.sleep(0.8)
    after = d.execute_script(STATE)
    after["errors"] = d.execute_script("return window.__errors")
    after["sinceBurstMs"] = d.execute_script("return Date.now() - window.__burstStart")
    spy_ok = during["nav"] == "Grid" and during["title"] == "Grid • femto" and not after["errors"]
    print(f"   {name}: replaceState x250 at once: {burst['applied']} took effect, {burst['thrown']} threw"
          + (f" from call {burst['firstThrow']} ({burst['error']})" if burst["thrown"] else "") + f", in {burst['ms']} ms")
    print(f"   {name}: within the limit's window the spy {'kept' if spy_ok else 'DID NOT keep'} following "
          f"(nav {during['nav']}, URL {during['url']}, window errors {after['errors']}); "
          f"{after['sinceBurstMs'] / 1000:.1f} s after the burst the URL is {after['url']}")
    d.get("about:blank")
    d.get(BASE + "/docs")
    time.sleep(0.5)
    fast = d.execute_async_script(FAST_SCROLL)
    print(f"   {name}: in-page fast scroll ({fast['steps']} steps of 200 px every 16 ms, {fast['scrollMs']} ms): "
          f"{fast['replaceStateCalls']} replaceState calls, ends on {fast['hash']}")
    return {"burst": burst, "during": during, "after": after, "spyKeptFollowing": spy_ok, "fastScroll": fast}


def probe_smooth(name, d):
    """Whether a load-time deep link, a nav click, back and forward animate, on the spike's page
    (smooth only under the click class) and on docs-smooth (html { scroll-behavior: smooth })."""
    out = {}
    for page in ("docs", "docs-smooth"):
        r = {}
        d.get("about:blank")
        d.get(BASE + f"/{page}#input")
        time.sleep(2.0)
        r["deep link"] = {**d.execute_script(SCROLL_SUMMARY), "from": 0, "headingTop": top_of(d, "input")}
        steps = (
            ("click", lambda: click_nav(d, "modal"), "modal"),
            ("back", d.back, "input"),
            ("forward", d.forward, "modal"),
        )
        for label, act, sid in steps:
            y0 = d.execute_script("window.__scrolls = []; return Math.round(scrollY)")
            act()
            time.sleep(2.5)
            r[label] = {**d.execute_script(SCROLL_SUMMARY), "from": y0, "headingTop": top_of(d, sid)}
        for label, log in r.items():
            log["animated"] = animated(log)
        out[page] = r
        print(f"   {name}: {page + '.html':17} " + "; ".join(
            f"{label} {'ANIMATED' if log['animated'] else 'instant'} ({log['events']} events over {log['spanMs']} ms, "
            f"{log['from']}→{log['y']})" for label, log in r.items()))
    return out


def environment(name, d):
    d.get(BASE + "/docs")
    time.sleep(0.8)
    env = d.execute_script("""return {visibility: document.visibilityState, hasFocus: document.hasFocus(),
      inner: [innerWidth, innerHeight], dpr: devicePixelRatio, ua: navigator.userAgent,
      firstFrameAt: window.__firstFrameAt ?? null};""")
    env["browserVersion"] = d.capabilities.get("browserVersion")
    if name == "safari":
        env["safaridriver"] = sh(SAFARIDRIVER, "--version").strip()
    print(f"   {name}: {json.dumps(env)}")
    if name == "safari" and (env["visibility"] != "visible" or env["firstFrameAt"] is None):
        raise Blocked("Safari's window is not visible or requestAnimationFrame did not run; "
                      "the checks need an unlocked screen with the automation window on it")
    return env


def frames_running(d):
    """Whether the page is visible and requestAnimationFrame still runs. In Safari both stop when the
    screen locks or the window is hidden, and then every timing above means nothing."""
    return d.execute_async_script("""const done = arguments[arguments.length - 1];
      requestAnimationFrame(() => done({visibility: document.visibilityState, rafRuns: true}));
      setTimeout(() => done({visibility: document.visibilityState, rafRuns: false}), 1000);""")


def main():
    names = [a for a in sys.argv[2:] if not a.startswith("--")] or ["chrome", "firefox", "chrome-nojs"]
    probes = "--probes" in sys.argv
    makers = {"chrome": chrome, "firefox": firefox, "chrome-nojs": lambda: chrome(js=False), "safari": safari}
    ok, report = True, {}
    for name in names:
        t0 = time.time()
        try:
            with session(name, makers[name]) as d:
                if name == "chrome-nojs":
                    ok = run_without_js(d) and ok
                    continue
                report[name] = {"environment": environment(name, d), "framesRunning": {}}
                stages = [("checks", lambda: run(name, d))]
                if probes:
                    stages += [("theme", lambda: probe_theme(name, d)), ("history", lambda: probe_history(name, d)),
                               ("smooth", lambda: probe_smooth(name, d))]
                for stage, go in stages:
                    if stage == "theme":
                        print(f"\n== {name} probes")
                    result = go()
                    if stage == "checks":
                        ok = result and ok
                    else:
                        report[name][stage] = result
                    frames = report[name]["framesRunning"][stage] = frames_running(d)
                    if frames != {"visibility": "visible", "rafRuns": True}:
                        print(f"   {name}: INVALID, after the {stage} the page reports {frames}")
                        ok = False
        except Blocked as e:
            print(f"\n== {name}: BLOCKED, not run: {e}")
            ok = False
        if name == "safari":
            took, idle = time.time() - t0, idle_s()
            if idle is not None and idle < took:
                print(f"   safari: real input during the session (HIDIdleTime {idle:.0f} s, session {took:.0f} s)")
            else:
                print(f"   safari: no real input during the session (HIDIdleTime {idle:.0f} s, session {took:.0f} s)")
            print("   safari: WebDriver cannot turn JavaScript off in Safari; the JavaScript-off check runs in Chrome only")
    if probes:
        print("\n== probe data\n" + json.dumps(report, indent=1, ensure_ascii=False))
    return ok


sys.exit(0 if main() else 1)
