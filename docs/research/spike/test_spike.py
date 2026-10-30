# /// script
# requires-python = ">=3.12"
# dependencies = ["selenium==4.52.0"]
# ///
# Checks the spike's scroll spy, #hash sync, deep links, history and ?theme= stylesheet in headless
# Chrome Beta and Firefox, the same browsers femto's parity rig drives. Start serve.py first.
# Run: uv run docs/research/spike/test_spike.py [port]
import json
import sys
import time

from selenium import webdriver
from selenium.webdriver.firefox.service import Service

BASE = f"http://127.0.0.1:{sys.argv[1] if len(sys.argv) > 1 else 8790}"
CHROME = "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta"
FIREFOX = "/Applications/Firefox.app/Contents/MacOS/firefox"
JADE = "light-dark(#007a50, #00b478)"

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


def top_of(d, sid):
    return d.execute_script(f"return Math.round(document.getElementById('{sid}').getBoundingClientRect().top)")


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
    d.execute_script("document.querySelector('#docs-nav a[href=\"#container\"]').click()")
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
    print(f"   {name}: back {'restored the exact position' if exact else 'scrolled to the #hash heading'}")
    d.forward()
    time.sleep(1.2)
    fwd = state()
    check("forward returns", fwd["url"] == "/docs#container" and fwd["nav"] == "Container", fwd)

    # 8. Reload mid-section: does the browser restore the position or jump to the #hash target?
    scroll_to("document.getElementById('css-variables').closest('section').offsetTop + 900")
    before = state()
    d.execute_script("location.reload()")
    time.sleep(1.5)
    after = state()
    check("reload keeps position", after["url"] == before["url"] and abs(after["y"] - before["y"]) < 5, {"before": before, "after": after})
    d.refresh()
    time.sleep(1.5)
    hard = state()
    check("hard reload shows the section", hard["url"] == before["url"] and hard["nav"] == "CSS variables", {"before": before, "after": hard})

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
    d.execute_script("document.querySelector('#docs-nav a[href=\"#forms\"]').click()")
    time.sleep(1.8)
    s = state()
    check("?theme= kept by spy and clicks", s["url"] == "/docs?theme=jade&method=write#forms", s)
    d.execute_script("document.querySelector('#docs-nav a[href=\"#quick-start\"]').click()")
    time.sleep(1.8)
    s = state()
    check("Quick start click → plain /docs", s["url"] == "/docs?theme=jade&method=write" and s["y"] < 30, s)

    print(f"\n== {name} {d.capabilities.get('browserVersion')}")
    for label, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            print("      " + json.dumps(detail))
    return all(ok for _, ok, _ in results)


def run_without_js():
    d = chrome(js=False)
    try:
        d.get(BASE + "/docs#forms")
        time.sleep(0.8)
        top, y = top_of(d, "forms"), d.execute_script("return Math.round(scrollY)")
        ok = 60 < top < 140 and y > 0
        print(f"\n== chrome, JavaScript off\n{'PASS' if ok else 'FAIL'}  deep link /docs#forms scrolls natively")
        if not ok:
            print("      " + json.dumps({"headingTop": top, "y": y}))
        return ok
    finally:
        d.quit()


ok = True
for name, make in (("chrome", chrome), ("firefox", firefox)):
    d = make()
    try:
        ok = run(name, d) and ok
    finally:
        d.quit()
ok = run_without_js() and ok
sys.exit(0 if ok else 1)
