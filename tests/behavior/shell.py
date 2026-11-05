"""Shell: what every page or every docs page shares (docs/research/01 §2: PageContext, Nav, Header,
Code, ModalContext, DocumentationMenu, Breadcrumb; and the example forms' submit, 01 §2's last
paragraph). In the static site these live in site.js and docs.js. The one page's spy, its URLs and
?theme= are the one-page group's.

Phase 4 turned the site's link-styled controls into buttons: the header's color-scheme toggle, the
code blocks' copy controls, the breadcrumb's Documentation control and the off-canvas menu's Close.
The selectors take either element (`:is(a, button)`), so the oracle's links are held to the same
behavior; what only a button has (Space, the tab order, type=button) and what only the one page does
(the inert page behind the open menu, focusable code blocks) run on the one page only."""
import json
import math
import time

from behavior import COPY_SPY, HEADING_LINE, check, nav_href

GROUP = "shell"

TOGGLE = "body > header nav ul.icons :is(a, button)[aria-label$='dark mode']"   # a button from Phase 4, the oracle's link
KEY = "femtoColorScheme"

THEME_STATE = """
const a = document.querySelector(arguments[0]);
return {theme: document.documentElement.getAttribute("data-theme"), stored: localStorage.getItem(arguments[1]),
        label: a && a.getAttribute("aria-label"), moon: !!(a && a.querySelector(".icon-theme-toggle.moon")),
        icon: !!(a && a.querySelector(".icon-theme-toggle"))};
"""


def theme(page):
    return page.js(THEME_STATE, TOGGLE, KEY)


def wait_label(page, label):
    """The toggle's label and icon settle within 1 s of a load or a change (the oracle relabels it in
    a React effect after the attribute changes)."""
    page.wait(f"toggle reads {label!r}", "(() => { const a = document.querySelector(arguments[0]);"
              " return a && a.getAttribute('aria-label') === arguments[1]"
              " && !!a.querySelector('.icon-theme-toggle.moon') === (arguments[1] === 'Turn off dark mode'); })()",
              1, args=(TOGGLE, label))


def toggle_and_expect(page, theme_after, label_after):
    url = page.url()
    page.click(TOGGLE)
    page.wait(f"data-theme becomes {theme_after}",
              "document.documentElement.getAttribute('data-theme') === arguments[0]", 2, args=(theme_after,))
    page.eq(f"{KEY} stores {theme_after!r} as JSON", theme(page)["stored"], f'"{theme_after}"')
    wait_label(page, label_after)
    page.eq(f"toggle icon {'has' if theme_after == 'dark' else 'lacks'} the moon class", theme(page)["moon"], theme_after == "dark")
    page.url_kept("the toggle does not navigate (no #)", url)


@check("theme-toggle", ("/", "/docs#typography"))
def theme_toggle(page):
    """With a light OS scheme and nothing stored: <html> has no data-theme, the header toggle
    (`ul.icons button`, the oracle's `ul.icons a`; its icon `.icon-theme-toggle`: the oracle's SVG, the site's emoji of Decision
    16) reads "Turn on dark mode" without the `moon` class. A click sets data-theme="dark" on
    <html>, stores localStorage femtoColorScheme = '"dark"' (JSON), relabels the toggle "Turn off
    dark mode" and adds `moon`; the URL is unchanged (no `#`).
    A second click stores '"light"', sets data-theme="light" and restores the label and icon."""
    s = theme(page)
    page.eq("no data-theme before any choice", s["theme"], None)
    page.eq("nothing stored", s["stored"], None)
    page.expect("the toggle and its icon exist", s["label"] is not None and s["icon"], **s)
    wait_label(page, "Turn on dark mode")
    toggle_and_expect(page, "dark", "Turn off dark mode")
    toggle_and_expect(page, "light", "Turn on dark mode")


@check("theme-toggle-dark-os", "/docs", media="dark")
def theme_toggle_dark_os(page):
    """With a dark OS scheme and nothing stored: no data-theme, and the toggle already reads "Turn
    off dark mode" with the `moon` class (the page follows the OS). A click stores '"light"' (the
    opposite of the current scheme) and sets data-theme="light"; the next click stores '"dark"'."""
    s = theme(page)
    page.eq("no data-theme before any choice", s["theme"], None)
    wait_label(page, "Turn off dark mode")
    toggle_and_expect(page, "light", "Turn on dark mode")
    toggle_and_expect(page, "dark", "Turn off dark mode")


@check("theme-toggle-keyboard", ("/", "/docs#typography"))
def theme_toggle_keyboard(page):
    """The header toggle (a <button>; the oracle's an <a href>) works from the keyboard as from the pointer: focused, Enter
    sets data-theme="dark", stores '"dark"' and relabels it "Turn off dark mode" with `moon`, with
    no navigation (URL unchanged, the document kept: a marker set on window survives); Enter again
    gives light the same way."""
    page.js("window.__bhMarker = 'kept'")
    url = page.url()
    for want, label in (("dark", "Turn off dark mode"), ("light", "Turn on dark mode")):
        page.expect("the toggle takes focus", page.focus(TOGGLE))
        page.key("ENTER")
        page.wait(f"Enter: data-theme becomes {want}", "document.documentElement.getAttribute('data-theme') === arguments[0]",
                  2, args=(want,))
        page.eq(f"Enter: {KEY} stores {want!r} as JSON", theme(page)["stored"], f'"{want}"')
        wait_label(page, label)
        page.eq("Enter: the document is kept (no reload)", page.js("return window.__bhMarker || null"), "kept")
        page.url_kept("Enter: URL unchanged", url)


COMPARISON = "[...document.querySelectorAll('main > section.comparison div.code[data-theme]')].map(d => d.getAttribute('data-theme'))"
THEAD = "(() => { const h = S.querySelector('div.overflow-auto > table > thead[data-theme]'); return h && h.getAttribute('data-theme'); })()"


@check("theme-os-live", ("/", "/docs#table"))
def theme_os_live(page):
    """With nothing stored, the page follows a live change of the OS scheme (prefers-color-scheme
    switched while the page is open; use-prefers-color-scheme in PageContext.jsx): at dark the
    header toggle reads "Turn off dark mode" with `moon`, the homepage comparison's code samples
    read data-theme="dark" and Table's inverse thead "light"; back at light all three return.
    No data-theme is ever written on <html>."""
    wait_label(page, "Turn on dark mode")
    for media, label, samples, thead in (("dark", "Turn off dark mode", "dark", "light"), ("light", "Turn on dark mode", "light", "dark")):
        page.sess.set_media(media)
        wait_label(page, label)
        if page.route == "/":
            page.expect("the homepage has comparison samples", len(page.js(f"return {COMPARISON}")) >= 1)
            page.wait(f"OS {media}: the comparison samples read {samples}", f"{COMPARISON}.every(v => v === '{samples}')", 1.5,
                      got=page.js(f"return {COMPARISON}"))
        else:
            page.wait(f"OS {media}: the inverse thead reads {thead}", f"{THEAD} === '{thead}'", 1.5)
        page.eq(f"OS {media}: no data-theme written", page.js("return document.documentElement.getAttribute('data-theme')"), None)
        page.eq(f"OS {media}: nothing stored", page.js(f"return localStorage.getItem('{KEY}')"), None)


@check("theme-stored-dark", ("/", "/docs#button"), storage={KEY: '"dark"'})
def theme_stored_dark(page):
    """A stored choice wins over the OS: with femtoColorScheme = '"dark"' stored and a light OS,
    the loaded page has data-theme="dark" on <html> and the toggle reads "Turn off dark mode" with
    the `moon` class."""
    page.eq("data-theme is the stored dark", theme(page)["theme"], "dark")
    wait_label(page, "Turn off dark mode")


@check("theme-stored-light", "/docs#button", media="dark", storage={KEY: '"light"'})
def theme_stored_light(page):
    """With femtoColorScheme = '"light"' stored and a dark OS, the page has data-theme="light" and
    the toggle reads "Turn on dark mode" without `moon`; a click stores '"dark"'."""
    page.eq("data-theme is the stored light", theme(page)["theme"], "light")
    wait_label(page, "Turn on dark mode")
    toggle_and_expect(page, "dark", "Turn off dark mode")


@check("theme-stored-invalid", "/docs#table", media="dark", storage={KEY: '"blue"'},
       oracle_bug={"fails": "a stored value other than light or dark sets no data-theme",
                   "reason": "the oracle writes any stored femtoColorScheme into data-theme (PageContext.jsx), so a "
                             "value the site never writes, such as '\"blue\"', makes a dark-OS page light and "
                             "ignores the reader's OS scheme; the static site's head script and site.js accept "
                             "only \"light\" and \"dark\" (Decision 14; PLAN.md, oracle-bug)"})
def theme_stored_invalid(page):
    """With a dark OS and femtoColorScheme = '"blue"' stored (valid JSON, but neither "light" nor
    "dark", a value the site never writes), the stored item is left as it is, <html> has no
    data-theme, and the page follows the OS: the toggle reads "Turn off dark mode" with `moon`, and
    Table's inverse thead reads data-theme="light". A click stores '"light"' and sets
    data-theme="light". The oracle writes "blue" into data-theme, which is the assertion it fails."""
    s = theme(page)
    page.eq("the stored value is left as it is", s["stored"], '"blue"')
    page.eq("a stored value other than light or dark sets no data-theme", s["theme"], None, **s)
    page.holds("a stored value other than light or dark sets no data-theme",
               "!document.documentElement.hasAttribute('data-theme')", 0.5)
    wait_label(page, "Turn off dark mode")
    page.wait("the inverse thead reads light",
              "(() => { const h = S.querySelector('div.overflow-auto > table > thead[data-theme]');"
              " return !!h && h.getAttribute('data-theme') === 'light'; })()", 1)
    toggle_and_expect(page, "light", "Turn on dark mode")


@check("theme-cross-tab", "/docs#typography")
def theme_cross_tab(page):
    """Two tabs of the same browser: a toggle click in tab A (on Typography) reaches tab B (on
    /) without a reload: B gets data-theme="dark" and its toggle reads "Turn off dark mode". A
    second click in A makes B light. Removing the stored item in A (localStorage.removeItem) removes
    data-theme in B, whose toggle then follows the OS again ("Turn on dark mode")."""
    a = page.driver.current_window_handle
    b = page.new_tab("/")
    page.js("window.__bhMarker = 'tab-b'")
    page.switch(a)
    page.click(TOGGLE)
    page.wait("tab A is dark", "document.documentElement.getAttribute('data-theme') === 'dark'", 2)
    page.switch(b)
    page.wait("tab B follows to dark", "document.documentElement.getAttribute('data-theme') === 'dark'", 3)
    wait_label(page, "Turn off dark mode")
    page.eq("tab B was not reloaded", page.js("return window.__bhMarker"), "tab-b")
    page.switch(a)
    page.click(TOGGLE)
    page.wait("tab A is light", "document.documentElement.getAttribute('data-theme') === 'light'", 2)
    page.switch(b)
    page.wait("tab B follows to light", "document.documentElement.getAttribute('data-theme') === 'light'", 3)
    page.switch(a)
    page.js(f"localStorage.removeItem('{KEY}')")
    page.switch(b)
    page.wait("tab B drops data-theme when the choice is removed",
              "!document.documentElement.hasAttribute('data-theme')", 3)
    wait_label(page, "Turn on dark mode")


# Runs before the page's own scripts: records when <html> first carries data-theme (a
# MutationObserver on the document, plus the case of an element parsed with it) and whether <body>
# existed then. Paint timing gives the first paint (Chrome: first-paint; Firefox has only
# first-contentful-paint).
FLASH_PRELOAD = """() => {
  window.__bhTheme = null;
  const seen = (how) => {
    if (window.__bhTheme) return;
    const h = document.documentElement;
    if (h && h.hasAttribute("data-theme"))
      window.__bhTheme = {how, value: h.getAttribute("data-theme"), at: performance.now(), body: !!document.body};
  };
  new MutationObserver(() => seen("mutation")).observe(document, {subtree: true, childList: true, attributes: true, attributeFilter: ["data-theme"]});
  requestAnimationFrame(() => { window.__bhFirstFrame = document.documentElement && document.documentElement.getAttribute("data-theme"); });
}"""


@check("color-scheme-flash", ("/", "/docs"), storage={KEY: '"dark"'}, preload=FLASH_PRELOAD,
       oracle_bug={"fails": "data-theme is set while the head is parsed",
                   "reason": "the color-scheme flash: the oracle renders no data-theme on the server and sets it "
                             "only during hydration, after the body is parsed and usually after the first paint "
                             "(PLAN.md, oracle-bug; Decision 14)"})
def color_scheme_flash(page):
    """With femtoColorScheme = '"dark"' stored, <html> carries data-theme="dark" before anything can
    paint: observed from a script that runs before the page's own, the attribute first appears
    while the head is parsed (no <body> yet: a parser-blocking head script, Decision 14), before the
    first paint (first-paint in Chrome, first-contentful-paint in Firefox), and the first animation
    frame already sees it. The oracle sets it during hydration, after the body is parsed; whether
    that still precedes the first paint is a race, so the head assertion is the one it fails."""
    # Chrome sometimes records its paint entries 50 to 300 ms after the readiness hook returns (the
    # Phase 1 integration's probes: 2 of 12 loads, never later than 2 s), so wait for one.
    page.wait("the page painted", "performance.getEntriesByType('paint').length > 0", 3)
    r = page.js("""const p = performance.getEntriesByType("paint");
      const fp = p.find(e => e.name === "first-paint") || p.find(e => e.name === "first-contentful-paint");
      return {theme: window.__bhTheme, firstPaint: fp ? fp.startTime : null, paintKind: fp ? fp.name : null,
              firstFrame: window.__bhFirstFrame === undefined ? "no frame recorded" : window.__bhFirstFrame,
              now: document.documentElement.getAttribute("data-theme")}""")
    page.eq("data-theme ends dark", r["now"], "dark")
    page.expect("the page painted", r["firstPaint"] is not None, **r)
    t = r["theme"]
    page.expect("data-theme was observed", t is not None, **r)
    page.expect("data-theme is set while the head is parsed", not t["body"], **r)
    page.expect("data-theme is set before the first paint", t["at"] <= r["firstPaint"], **r)
    page.eq("the first animation frame sees data-theme", r["firstFrame"], "dark", **r)


@check("header-fixed", "/docs#modal")
def header_fixed(page):
    """On a docs page (1300 px): `body > header` has class `is-fixed-above-lg` and not `is-fixed` at
    the top (scrolled there first: the one page loads #modal far down); `is-fixed` is added once
    scrollY > 20 (not at 20, at 21) and removed when scrolling back to 20 or 0."""
    cls = "document.querySelector('body > header').classList"
    page.scroll_to(0)
    page.wait("at the top: not fixed", f"!{cls}.contains('is-fixed')", 1)
    page.expect("is-fixed-above-lg at the top", page.js(f"return {cls}.contains('is-fixed-above-lg') && !{cls}.contains('is-fixed')"))
    for y, fixed in ((20, False), (21, True), (600, True), (20, False), (0, False), (300, True), (0, False)):
        page.scroll_to(y)
        expr = f"{cls}.contains('is-fixed')" if fixed else f"!{cls}.contains('is-fixed') && {cls}.contains('is-fixed-above-lg')"
        page.wait(f"scrollY {y}: is-fixed {'on' if fixed else 'off'}", expr, 1)


@check("header-landing", "/")
def header_landing(page):
    """On a landing page the header is never fixed: `body > header` has no class attribute, at the
    top and after scrolling 600 px."""
    page.eq("no class at the top", page.js("return document.querySelector('body > header').getAttribute('class')"), None)
    page.scroll_to(600)
    page.sleep(0.3)
    page.eq("no class after scrolling", page.js("return document.querySelector('body > header').getAttribute('class')"), None)


COPY_STATE = """
const a = arguments[0];
return {tooltip: a.getAttribute("data-tooltip"), check: !!a.querySelector("svg.check"), clipboard: !!a.querySelector("svg.clipboard"),
        focused: document.activeElement === a, copied: window.__bhCopied};
"""

# Records the copy link's tooltip and icon on every change, and the click, with performance.now()
# times, so the check measures the 1 s revert in the page.
COPY_TIMELINE = """
const a = arguments[0];
window.__bhCopy = [];
const t = () => Math.round(performance.now());
const state = () => [a.getAttribute("data-tooltip"), a.querySelector("svg.check") ? "check" : a.querySelector("svg.clipboard") ? "clipboard" : "none"];
let last = JSON.stringify(state());
new MutationObserver(() => { const s = state(), j = JSON.stringify(s); if (j !== last) { __bhCopy.push([t(), ...s]); last = j; } })
  .observe(a, {attributes: true, childList: true, subtree: true});
a.addEventListener("click", () => __bhCopy.push([t(), "click"]), true);
"""


@check("copy-button", ("/docs", "/docs#modal"))
def copy_button(page):
    """Each code block's copy control of the route's content (`.copy-to-clipboard`: a button from
    Phase 4, the oracle's link; data-tooltip "Copy to clipboard", icon
    `svg.clipboard`): a click copies exactly that block's code text (its `pre code` textContent; the
    copy is recorded in the page, the machine's clipboard is never touched) and leaves the URL as it
    was. Timed in the page: within 100 ms of the click the tooltip reads "Copied" with the animated
    `svg.check` icon, and 1 s later (900 to 1500 ms) "Copy to clipboard" with `svg.clipboard` again,
    with no other step; the control then does not hold focus (a pointer click blurs it). A second
    block's control copies its own code."""
    page.js(COPY_SPY)
    links = page.find_all(".copy-to-clipboard")
    page.expect("at least two copy links", len(links) >= 2, count=len(links))
    for n, link in enumerate((links[0], links[-1]), 1):
        code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", link)
        s = page.js(COPY_STATE, link)
        page.eq(f"link {n}: tooltip 'Copy to clipboard' before", s["tooltip"], "Copy to clipboard")
        page.expect(f"link {n}: clipboard icon before", s["clipboard"] and not s["check"], **s)
        url = page.url()
        page.js("window.__bhCopied.length = 0")
        page.js(COPY_TIMELINE, link)
        page.click(link)
        page.wait(f"link {n}: copied", "window.__bhCopied.length > 0", 1)
        s = page.js(COPY_STATE, link)
        page.eq(f"link {n}: copied once", len(s["copied"]), 1, copied=s["copied"])
        page.eq(f"link {n}: copied the block's code", s["copied"][0]["text"], code, via=s["copied"][0]["via"])
        page.url_kept(f"link {n}: URL unchanged", url)
        page.wait(f"link {n}: reverted", "arguments[0].getAttribute('data-tooltip') === 'Copy to clipboard' && "
                  "!!arguments[0].querySelector('svg.clipboard') && window.__bhCopy.length >= 3", 2.5, args=(link,))
        tl = page.js("return window.__bhCopy")
        page.eq(f"link {n}: the steps", [x[1:] for x in tl], [["click"], ["Copied", "check"], ["Copy to clipboard", "clipboard"]],
                timeline=tl)
        page.expect(f"link {n}: 'Copied' within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
        page.expect(f"link {n}: reverts 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
        page.eq(f"link {n}: blurred after reverting", page.js(COPY_STATE, link)["focused"], False)


@check("copy-button-repeat", "/docs#modal")
def copy_button_repeat(page):
    """Repeated use of a copy control, as Code.jsx behaves (every click schedules its own 1 s revert,
    and the first one to fire reverts): two clicks 500 ms apart copy the block's code twice, and
    "Copied" reverts to "Copy to clipboard" with `svg.clipboard` once, 1 s after the FIRST click (900
    to 1200 ms), with no other step; the control then does not hold focus."""
    page.js(COPY_SPY)
    link = page.find_all(".copy-to-clipboard")[0]
    code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", link)
    page.js(COPY_TIMELINE, link)
    page.click(link)
    page.sleep(0.5)
    page.click(link)
    page.wait("reverted", "arguments[0].getAttribute('data-tooltip') === 'Copy to clipboard' && !!arguments[0].querySelector('svg.clipboard')",
              3, args=(link,))
    page.sleep(0.8)   # a later, wrong revert or step would show by now
    tl = page.js("return window.__bhCopy")
    copies = page.js("return window.__bhCopied")
    page.eq("two clicks copy twice, the block's code each time", [c["text"] for c in copies], [code, code])
    page.eq("the steps: click, Copied, click, one revert", [x[1:] for x in tl],
            [["click"], ["Copied", "check"], ["click"], ["Copy to clipboard", "clipboard"]], timeline=tl)
    page.expect("it reverts 1 s after the first click", 900 <= tl[3][0] - tl[0][0] <= 1200, ms_after_first=tl[3][0] - tl[0][0],
                timeline=tl)
    page.eq("blurred after reverting", page.js(COPY_STATE, link)["focused"], False)


HTML_CLASSES = "return [...document.documentElement.classList].filter(c => c.startsWith('modal-is-')).sort().join(' ')"

# Records, from now on, every change of <html>'s modal-is-* classes and every click and keydown,
# each with its performance.now() time, so the check can measure the helper's timing in the page.
MODAL_TIMELINE = """
window.__bhModal = [];
const t = () => Math.round(performance.now());
const cls = () => [...document.documentElement.classList].filter(c => c.startsWith("modal-is-")).sort().join(" ");
let last = cls();
new MutationObserver(() => { const c = cls(); if (c !== last) { __bhModal.push([t(), "classes", c]); last = c; } })
  .observe(document.documentElement, {attributes: true, attributeFilter: ["class"]});
addEventListener("click", () => __bhModal.push([t(), "click"]), true);
addEventListener("keydown", (e) => __bhModal.push([t(), "key", e.key]), true);
"""

OPEN, OPENING, CLOSING = "modal-is-open", "modal-is-open modal-is-opening", "modal-is-closing modal-is-open"


def modal_timeline(page, label, want):
    """Assert that the recorded timeline, after its first click or key, is exactly the class steps
    in `want` [(classes, min_ms, max_ms) measured from the previous step, the first from the event]."""
    tl = page.js("return window.__bhModal")
    ev = next((i for i, e in enumerate(tl) if e[1] in ("click", "key")), None)
    page.expect(f"{label}: an input event was recorded", ev is not None, timeline=tl)
    steps = [e for e in tl[ev:] if e[1] == "classes"]
    page.eq(f"{label}: the class steps", [s[2] for s in steps], [w[0] for w in want], timeline=tl)
    prev = tl[ev][0]
    for s, (c, lo, hi) in zip(steps, want):
        page.expect(f"{label}: {c or 'no class'} after {lo} to {hi} ms", lo <= s[0] - prev <= hi, ms=s[0] - prev, timeline=tl)
        prev = s[0]


@check("modal-helper", ("/docs#modal",))
def modal_helper(page):
    """The modal helper on <html> (01 §2, ModalContext), opened by Modal's "Open modal"
    button, timed in the page: within 100 ms of the click <html> has `modal-is-open
    modal-is-opening`, and 400 ms later (350 to 700) only `modal-is-open`; Escape then gives
    `modal-is-open modal-is-closing` within 100 ms, and 400 ms later (350 to 700) no modal class at
    all. No other class steps happen. Escape again, with nothing open, changes nothing."""
    page.eq("no modal class before", page.js(HTML_CLASSES), "")
    page.js(MODAL_TIMELINE)
    page.click("#modal-demo button")
    page.wait("open", f"(() => {{ {HTML_CLASSES} }})() === '{OPEN}'", 1.5)
    modal_timeline(page, "opening", [(OPENING, 0, 100), (OPEN, 350, 700)])
    page.js("window.__bhModal.length = 0")
    page.key("ESCAPE")
    page.wait("closed", f"(() => {{ {HTML_CLASSES} }})() === ''", 1.5)
    modal_timeline(page, "closing", [(CLOSING, 0, 100), ("", 350, 700)])
    page.js("window.__bhModal.length = 0")
    page.key("ESCAPE")
    page.sleep(0.6)
    page.eq("Escape with no modal open changes nothing",
            [e for e in page.js("return window.__bhModal") if e[1] == "classes"], [])


@check("modal-scrollbar-width", "/docs#modal")
def modal_scrollbar_width(page):
    """With a classic (space-taking) scrollbar, which the harness forces (Chrome: a
    ::-webkit-scrollbar sheet adopted before the page loads; Firefox: ui.useOverlayScrollbars 0):
    while the modal is open, <html>'s style sets --femto-scrollbar-width to the scrollbar's width
    (innerWidth minus <html>'s clientWidth, measured before opening), and the page behind does not
    move sideways (the demo article keeps its left edge). Once closed, the property is gone."""
    page.with_classic_scrollbars()
    sb = page.js("return innerWidth - document.documentElement.clientWidth")
    page.expect("the forced scrollbar takes space", sb > 0, scrollbar=sb)
    left = page.js("return document.querySelector('#modal-demo').getBoundingClientRect().left")
    page.click("#modal-demo button")
    page.wait("open", "document.documentElement.classList.contains('modal-is-open')", 0.5)
    v = page.js("return document.documentElement.style.getPropertyValue('--femto-scrollbar-width').trim()")
    page.eq("--femto-scrollbar-width is the scrollbar width", v, f"{sb}px")
    page.eq("the page behind does not move", page.js(
        "return document.querySelector('#modal-demo').getBoundingClientRect().left"), left)
    page.key("ESCAPE")
    page.wait("closed", "!document.documentElement.classList.contains('modal-is-open')", 1)
    page.eq("no --femto-scrollbar-width once closed", page.js(
        "return document.documentElement.style.getPropertyValue('--femto-scrollbar-width')"), "")


# The page's modal state: [the open dialogs other than the Modal section's two static examples
# (dialog.example), each "demo" (Modal's dialog[data-modal=modal-demo]), "color" (dialog.color) or
# the start of its markup, in document order; <html>'s modal-is-* classes, sorted; and <html>'s
# --femto-scrollbar-width].
DIALOGS = """(() => {
  const open = [...document.querySelectorAll("dialog[open]:not(.example)")].map(d =>
    d.matches("[data-modal=modal-demo]") ? "demo" : d.matches(".color") ? "color" : d.outerHTML.slice(0, 60)).join(" ");
  const root = document.documentElement;
  return [open, [...root.classList].filter(c => c.startsWith("modal-is-")).sort().join(" "),
          root.style.getPropertyValue("--femto-scrollbar-width").trim()];
})()"""

# Records, from now on, every change of that state as a MutationObserver callback sees it (after
# the task or listener that made it, as a reader would: the synchronous steps inside one handler
# are not seen), with its performance.now() time, and every keydown.
DIALOGS_TIMELINE = f"""
window.__bhDialogs = [];
const t = () => Math.round(performance.now());
const read = () => {DIALOGS};
let last = JSON.stringify(read());
new MutationObserver(() => {{ const s = read(), k = JSON.stringify(s); if (k !== last) {{ __bhDialogs.push([t(), "state", ...s]); last = k; }} }})
  .observe(document.documentElement, {{subtree: true, childList: true, attributes: true, attributeFilter: ["open", "class", "style"]}});
addEventListener("keydown", (e) => __bhDialogs.push([t(), "key", e.key]), true);
return read();
"""

TWO_DIALOGS_WHY = ("Modal's demo dialog and the Colors section's color modal are on one page only on the one page (PLAN.md "
                   "Decision 2; Conversion rules, one modal helper per dialog); on routes /docs/modal and /docs/colors are "
                   "separate pages, so the two never meet")
RED_500 = ".color-families .family :is(main, .shades) > button.femto-background-red-500"   # .shades from Phase 4


def dialog_steps(page, label, tl, want, after="the key"):
    """Assert that the timeline's states after its first key (a keydown, or a marker a check pushes
    for a script's action, named by `after`) are exactly `want`, each [open,
    classes, scrollbar width, min_ms, max_ms] with its time measured from the key (not from the
    previous step: a step is seen only after the handler that made it returns, so the time between
    two steps loses whatever that handler did after it started a timer)."""
    ev = next((i for i, e in enumerate(tl) if e[1] == "key"), None)
    page.expect(f"{label}: the key was recorded", ev is not None, timeline=tl)
    steps = [e for e in tl[ev:] if e[1] == "state"]
    page.eq(f"{label}: the steps", [s[2:] for s in steps], [w[:3] for w in want], timeline=tl)
    key = tl[ev][0]
    for s, w in zip(steps, want):
        page.expect(f"{label}: {w[0] or 'no dialog'}, {w[1] or 'no class'} {w[3]} to {w[4]} ms after {after}",
                    w[3] <= s[0] - key <= w[4], ms=s[0] - key, timeline=tl)


@check("modal-two-dialogs", "/docs#modal", layouts=("one-page",), layout_reason=TWO_DIALOGS_WHY)
def modal_two_dialogs(page):
    """One modal helper per dialog, one holder of <html>'s classes (PLAN.md Conversion rules; site.js
    createModal), with the two dialogs of the one page and a classic scrollbar (as
    modal-scrollbar-width forces it; Safari, which has no preload script, keeps its own, whose width
    may be 0). "Open modal" opens Modal's demo dialog alone, and once it is open (`modal-is-open`
    alone) <html>'s --femto-scrollbar-width is the scrollbar's width. The demo is a true modal
    (showModal(), from Phase 4): it matches :modal, focus is inside it, and the page behind is
    inert, so the Colors section's red 500 shade button cannot take focus (focus stays in the demo)
    and no Enter on it can open the color modal, as it could before Phase 4. A script still can: a
    click() on that button (inert stops user input, not a script's events) runs colors.js's
    handler, which opens the color modal through
    its own helper while the demo is open, and that hides the demo at once: the first change after
    the click, within 250 ms of it (the demo's own close would take 400 ms), is the color modal open
    with the demo closed, `modal-is-open modal-is-opening` and the same scrollbar width, then
    `modal-is-open` 350 to 800 ms after the click, and nothing else (the demo never shows
    `modal-is-closing`, and the two are never open together); so <html> keeps `modal-is-open` while
    one is open, and the page behind is no longer inert (the color modal's close button has focus).
    Escape then gives `modal-is-closing modal-is-open` within 100 ms and, 350 to 800 ms after the
    key, no dialog open (the two static examples aside), no modal-is-* class on <html> and an empty
    --femto-scrollbar-width, and nothing changes in the next 0.6 s (no timer of the hidden demo acts
    late). Every state is read from a MutationObserver in the page, as it stands after each handler,
    and timed from the click or the key: colors.js's open handler starts the 400 ms timer
    (modal.open()) and then focuses the close button, which lays out the long page, so the observer
    sees `modal-is-opening` 65 to 106 ms after it and the gap to `modal-is-open` shrinks by as much
    as that layout takes (343 and 349 ms in Firefox in p3f-review-m2d-1 and p3f-review-behavior-1,
    342 in p3f-head-m2d-3, below the 350 ms floor the steps once had between them), while
    `modal-is-open` itself came 438 to 454 ms after Enter in every run of both browsers (p3f-head-*
    and p3f-review-*)."""
    if page.browser == "safari":
        page.note("Safari: no preload script, so the page's own scrollbar (overlay scrollbars give 0px)")
    else:
        page.with_classic_scrollbars()
    sb = page.js("return innerWidth - document.documentElement.clientWidth")
    if page.browser != "safari":
        page.expect("the forced scrollbar takes space", sb > 0, scrollbar=sb)
    width = f"{sb}px"
    page.eq("no dialog open and no modal class on load", page.js(DIALOGS_TIMELINE), ["", "", ""])
    page.click("#modal-demo button")
    page.wait("the demo opens, alone, with modal-is-open alone", f"JSON.stringify({DIALOGS}) === arguments[0]", 1.5,
              args=(json.dumps(["demo", OPEN, width], separators=(",", ":")),), got=page.js(f"return {DIALOGS}"))
    demo = "dialog[data-modal=modal-demo]"
    page.eq("the demo is a true modal (:modal) with focus inside it", page.js(
        "const d = document.querySelector(arguments[0]); return [d.matches(':modal'), d.contains(document.activeElement)];",
        demo), [True, True], active=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
    page.eq("the page behind is inert: the shade button cannot take focus", page.focus(RED_500), False)
    page.eq("focus stays in the demo", page.js("return document.querySelector(arguments[0]).contains(document.activeElement)", demo),
            True, active=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
    page.js("window.__bhDialogs.length = 0;"
            "window.__bhDialogs.push([Math.round(performance.now()), 'key', 'click()']);"
            "document.querySelector(arguments[0]).click();", RED_500)
    page.wait("a script's click() on the shade button opens the color modal", "!!document.querySelector('dialog.color[open]')", 1)
    page.wait("the color modal is open with modal-is-open alone", f"JSON.stringify({DIALOGS}) === arguments[0]", 1.5,
              args=(json.dumps(["color", OPEN, width], separators=(",", ":")),), got=page.js(f"return {DIALOGS}"))
    tl = page.js("return window.__bhDialogs")
    page.expect("no state has both dialogs open", not any(e[1] == "state" and len(e[2].split()) > 1 for e in tl), timeline=tl)
    page.expect("<html> has modal-is-open whenever a dialog is open",
                all("modal-is-open" in e[3].split() for e in tl if e[1] == "state" and e[2]), timeline=tl)
    dialog_steps(page, "the color modal over the demo", tl,
                 [["color", OPENING, width, 0, 250], ["color", OPEN, width, 350, 800]], after="the click()")
    page.eq("the demo is closed and the page behind no longer inert: the color modal's close button has focus", page.js(
        "const d = document.querySelector(arguments[0]), c = document.querySelector('dialog.color');"
        "return [d.open, d.matches(':modal'), !!c && c.contains(document.activeElement)];", demo), [False, False, True],
        active=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
    page.js("window.__bhDialogs.length = 0")
    page.key("ESCAPE")
    page.wait("Escape closes it: no dialog, no modal class, no --femto-scrollbar-width",
              f"JSON.stringify({DIALOGS}) === '[\"\",\"\",\"\"]'", 1.5, got=page.js(f"return {DIALOGS}"))
    page.sleep(0.6)
    dialog_steps(page, "Escape", page.js("return window.__bhDialogs"),
                 [["color", CLOSING, width, 0, 100], ["", "", "", 350, 800]])
    page.eq("still no dialog open, no modal class and no --femto-scrollbar-width", page.js(f"return {DIALOGS}"), ["", "", ""])


# Each route's menu category (Breadcrumb.jsx's chapter; the one page's spy sets it for the section).
CATEGORY = {"/docs": "Getting started", "/docs?theme=jade#theme-picker": "Getting started", "/docs#colors": "Customization",
            "/docs#grid": "Layout", "/docs#table": "Content", "/docs#input": "Forms", "/docs#radios": "Forms",
            "/docs#modal": "Components"}


MAX_HEIGHT = """
const n = document.querySelector("#documentation-menu nav");
return {style: n.style.getPropertyValue("--max-height").trim(), expected: innerHeight - n.getBoundingClientRect().top, y: scrollY};
"""


def expect_max_height(page, label):
    m = page.js(MAX_HEIGHT)
    v = float(m["style"][:-2]) if m["style"].endswith("px") else None
    page.expect(label, v is not None and abs(v - m["expected"]) < 0.5, **m)
    page.wait(f"{label}: body min-height is innerHeight", "document.body.style.minHeight === innerHeight + 'px'", 1,
              got=page.js("return [document.body.style.minHeight, innerHeight]"))


@check("side-menu-max-height", ("/docs#grid",), width=375, height=812)
def side_menu_max_height(page):
    """The side menu's nav carries --max-height = innerHeight minus the nav's top, in px: on load at
    375 x 812, after the viewport shrinks to 375 x 600, after it grows to 1300 x 900, and after a
    resize to 1300 x 700 while scrolled 500 px down (where the nav is sticky). Each is within 0.5 px
    of innerHeight - nav.getBoundingClientRect().top at that moment. Each time <body>'s inline
    min-height is innerHeight in px too (Body.jsx, react-div-100vh: on load and on every resize)."""
    expect_max_height(page, "on load at 375 x 812")
    for w, h in ((375, 600), (1300, 900)):
        page.resize(w, h)
        page.sleep(0.3)
        expect_max_height(page, f"after a resize to {w} x {h}")
    page.scroll_to(500)
    page.resize(1300, 700)
    page.sleep(0.3)
    expect_max_height(page, "after a resize to 1300 x 700, scrolled")


MOBILE = """
const m = document.querySelector("#documentation-menu");
return {open: m.classList.contains("is-open-on-mobile"), overflowY: getComputedStyle(document.documentElement).overflowY,
        url: location.pathname + location.search + location.hash,
        focus: document.activeElement === document.body ? "body" : document.activeElement.outerHTML.slice(0, 100),
        focusInside: m.contains(document.activeElement)};
"""
OPENER = "nav[aria-label=breadcrumb] ul li:first-child :is(a, button)"   # buttons from Phase 4, the oracle's links
CLOSE = "#documentation-menu header :is(a, button)[aria-label=Close]"
IS_OPEN = "document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')"


@check("mobile-menu", "/docs#modal", width=375, height=812)
def mobile_menu(page):
    """At 375 px the breadcrumb's "Documentation" control (a button; the oracle's a link) opens the
    off-canvas menu: a click adds `is-open-on-mobile` to `aside#documentation-menu`, <html> stops
    scrolling (overflow-y hidden) and the URL is unchanged; the menu's own Close control (`header
    [aria-label=Close]`) removes the class, scrolling returns and the URL is still unchanged."""
    s = page.js(MOBILE)
    page.eq("closed on load", s["open"], False)
    url = page.url()
    page.click(OPENER)
    page.wait("the Documentation control opens the menu", IS_OPEN, 1)
    s = page.js(MOBILE)
    page.eq("the page behind stops scrolling", s["overflowY"], "hidden")
    page.url_kept("opening leaves the URL", url)
    page.click(CLOSE)
    page.wait("the Close control closes the menu", f"!{IS_OPEN}", 1)
    s = page.js(MOBILE)
    page.expect("the page scrolls again", s["overflowY"] != "hidden", **s)
    page.url_kept("closing leaves the URL", url)


@check("mobile-menu-keyboard", "/docs#modal", width=375, height=812)
def mobile_menu_keyboard(page):
    """At 375 px the off-canvas menu works from the keyboard as from the pointer: Enter on the
    breadcrumb's focused "Documentation" control adds `is-open-on-mobile`, with no navigation (URL
    unchanged, the document kept); Enter on the menu's focused Close control removes it, still with
    no navigation."""
    page.js("window.__bhMarker = 'kept'")
    url = page.url()
    page.expect("the Documentation control takes focus", page.focus(OPENER))
    page.key("ENTER")
    page.wait("Enter on Documentation opens the menu", IS_OPEN, 1.5)
    page.url_kept("opening: no navigation", url)
    page.eq("opening: the document is kept", page.js("return window.__bhMarker || null"), "kept")
    page.sleep(0.5)   # the menu slides in
    page.expect("the Close control takes focus", page.focus(CLOSE))
    page.key("ENTER")
    page.wait("Enter on the Close control closes the menu", f"!{IS_OPEN}", 1.5)
    page.url_kept("closing: no navigation", url)
    page.eq("closing: the document is kept", page.js("return window.__bhMarker || null"), "kept")


MENU_FOCUS_BUG = {"fails": "opening moves focus into the menu",
                  "reason": "the oracle's off-canvas menu has no Escape handler and no focus handling "
                            "(01 §2, DocumentationMenu.jsx); PLAN.md criterion 7 asks for both on the one page"}


@check("mobile-menu-focus", "/docs#modal", width=375, height=812, oracle_bug=MENU_FOCUS_BUG)
def mobile_menu_focus(page):
    """At 375 px the off-canvas menu takes focus and gives it back (criterion 7): Enter on the
    breadcrumb's focused "Documentation" control opens the menu with focus inside
    `aside#documentation-menu`; Escape closes it (no `is-open-on-mobile`, the page scrolls again, the
    URL unchanged) and focus returns to the Documentation control. Opened again with a pointer click,
    focus is inside the menu again; Enter on its focused Close control closes it and focus returns to
    the Documentation control. Escape with the menu closed changes nothing. That focus stays inside
    while the menu is open is mobile-menu-inert's."""
    url = page.url()
    page.expect("the Documentation control takes focus", page.focus(OPENER))
    page.key("ENTER")
    page.wait("Enter on Documentation opens the menu", IS_OPEN, 1.5)
    page.wait("opening moves focus into the menu", "document.querySelector('#documentation-menu').contains(document.activeElement)",
              1, got=page.js(MOBILE))
    page.key("ESCAPE")
    page.wait("Escape closes the menu", f"!{IS_OPEN}", 1.5)
    s = page.js(MOBILE)
    page.expect("Escape: the page scrolls again", s["overflowY"] != "hidden", **s)
    page.url_kept("Escape: no navigation", url)
    page.wait("Escape: focus returns to the Documentation control", "document.activeElement === document.querySelector(arguments[0])",
              1, args=(OPENER,), got=page.js(MOBILE))
    page.click(OPENER)
    page.wait("a click on Documentation opens the menu", IS_OPEN, 1)
    page.wait("clicked open: focus is inside the menu", "document.querySelector('#documentation-menu').contains(document.activeElement)",
              1, got=page.js(MOBILE))
    page.sleep(0.5)   # the menu slides in
    page.expect("the Close control takes focus", page.focus(CLOSE))
    page.key("ENTER")
    page.wait("Enter on the Close control closes the menu", f"!{IS_OPEN}", 1.5)
    page.wait("closed: focus returns to the Documentation control", "document.activeElement === document.querySelector(arguments[0])",
              1, args=(OPENER,), got=page.js(MOBILE))
    page.key("ESCAPE")
    page.sleep(0.3)
    page.eq("Escape with the menu closed changes nothing", page.js(MOBILE)["open"], False)
    page.url_kept("and leaves the URL", url)


@check("mobile-menu-link", "/docs#modal", width=375, height=812)
def mobile_menu_link(page):
    """At 375 px, with the off-canvas menu open, following the "Layout" category's "Grid" link (the
    category opened first if it is closed) closes the menu (no `is-open-on-mobile`) and shows Grid.
    On routes it goes to /docs/grid, Grid's page (its hgroup h1 reads "Grid"); back returns to the
    same /docs/modal document (the oracle's client-side history, the static site's back-forward
    cache: a marker set on window survives) with its menu closed, since the link closed it before the
    page was left. On the one page the link is a fragment navigation in the same document: the URL
    becomes /docs#grid with one new history entry and Grid's heading on the scroll-padding line
    (within 2 px); back returns to /docs#modal, the same document (the marker survives), with the menu
    closed."""
    page.js("window.__bhMarker = 'kept'")
    page.click(OPENER)
    page.wait("menu open", IS_OPEN, 1)
    summary = page.js("""return [...document.querySelectorAll('#documentation-menu nav details > summary')]
                         .find(s => s.textContent.trim() === 'Layout')""")
    if not page.js("return arguments[0].parentElement.open", summary):
        page.click(summary)
        page.wait("Layout opens", "arguments[0].parentElement.open", 1, args=(summary,))
    link = f"#documentation-menu a[href='{nav_href(page, 'grid')}']"
    if page.layout == "routes":
        page.click(link)
        page.wait_navigated("/docs/grid")
        page.eq("the menu is closed", page.js(MOBILE)["open"], False)
        page.eq("Grid's page", page.js("return document.querySelector('main hgroup h1').textContent.trim()"), "Grid")
        page.js("history.back()")
        page.wait_navigated("/docs/modal", label="back on /docs/modal")
    else:
        n = page.js("return history.length")
        page.click(link)
        page.wait("the menu closes", f"!{IS_OPEN}", 1.5)
        page.wait("the URL is /docs#grid", "location.pathname + location.search + location.hash === '/docs#grid'", 3)
        page.wait("Grid's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('grid')) <= 2", 3,
                  offset=page.js(f"return ({HEADING_LINE})('grid')"))
        page.eq("one new history entry", page.js("return history.length"), n + 1)
        page.eq("the same document", page.js("return window.__bhMarker || null"), "kept")
        page.driver.back()
        page.wait("back on /docs#modal", "location.pathname + location.search + location.hash === '/docs#modal'", 3)
    page.eq("back: the same document (kept or restored from the back-forward cache)", page.js("return window.__bhMarker || null"), "kept")
    page.eq("back: the menu is closed", page.js(MOBILE)["open"], False)


@check("breadcrumb-sticky", "/docs#modal", width=375, height=812)
def breadcrumb_sticky(page):
    """At 375 px the breadcrumb (`nav[aria-label=breadcrumb]`, sticky at top: -1px) has no class at
    the top (scrolled there first: the one page loads #modal far down). Measured from its own
    natural top t (its top plus scrollY at the top of the page), it gets `is-sticky` (within 1 s)
    once it sticks, scrolled 400 px down and at ceil(t) + 2 (its top then at -2 px or less,
    Breadcrumb.jsx's rule being top <= -1), and loses it (within 1 s) while it does not, at floor(t)
    - 1 and floor(t) - 20 (its top at 1 px or more) and at the top. Relative to t because the page
    above it differs: the static site has no maintenance banner (Decision 5), so its breadcrumb sits
    about 37 px higher than the oracle's."""
    bc = "document.querySelector('nav[aria-label=breadcrumb]')"
    page.scroll_to(0)
    page.wait("no is-sticky at the top", f"!{bc}.classList.contains('is-sticky')", 1)
    t = page.js(f"return {bc}.getBoundingClientRect().top + scrollY")
    page.expect("the breadcrumb starts below the top", t > 21, natural_top=t)
    stuck, free, far = math.ceil(t) + 2, math.floor(t) - 1, math.floor(t) - 20
    page.scroll_to(400)
    page.wait("is-sticky once stuck", f"{bc}.classList.contains('is-sticky')", 1, natural_top=t)
    page.scroll_to(free)
    page.wait(f"not sticky just above its natural top ({free} px)", f"!{bc}.classList.contains('is-sticky')", 1,
              natural_top=t)
    page.scroll_to(stuck)
    page.wait(f"is-sticky just past its natural top ({stuck} px)", f"{bc}.classList.contains('is-sticky')", 1,
              natural_top=t)
    page.scroll_to(far)
    page.wait(f"not sticky 20 px above its natural top ({far} px)", f"!{bc}.classList.contains('is-sticky')", 1,
              natural_top=t)
    page.scroll_to(400)
    page.wait("is-sticky again", f"{bc}.classList.contains('is-sticky')", 1)
    page.scroll_to(0)
    page.wait("not sticky at the top", f"!{bc}.classList.contains('is-sticky')", 1)


@check("breadcrumb-chapter", ("/docs", "/docs?theme=jade#theme-picker", "/docs#colors", "/docs#grid", "/docs#table",
                              "/docs#radios", "/docs#modal"), width=375, height=812)
def breadcrumb_chapter(page):
    """The breadcrumb's last item names the route's menu category (Getting started, Customization,
    Layout, Content, Forms, Components; a Theme picker color, the old version-picker color route, is
    Getting started), within 1 s of the load (the one page's spy sets it for the section a deep link
    lands on), and its first item is "Documentation": on the one page a button (type=button) that
    opens the off-canvas menu (aria-controls="documentation-menu"; Phase 4), on routes the oracle's
    link to /docs."""
    page.expect("the page has a breadcrumb", page.js("return !!document.querySelector('nav[aria-label=breadcrumb] ul li')"))
    page.wait("the chapter is the route's category",
              "document.querySelector('nav[aria-label=breadcrumb] ul li:last-child').textContent.trim() === arguments[0]", 1,
              args=(CATEGORY[page.route],),
              got=page.js("return document.querySelector('nav[aria-label=breadcrumb] ul li:last-child').textContent.trim()"))
    r = page.js("""const n = document.querySelector('nav[aria-label=breadcrumb]');
      const a = n.querySelector('ul li:first-child > :is(a, button)');
      return a && {tag: a.localName, text: a.textContent.trim(), href: a.getAttribute('href'), type: a.getAttribute('type'),
                   controls: a.getAttribute('aria-controls')}""")
    page.expect("the first item is a link or a button", r is not None)
    page.eq("the first item is Documentation", r["text"], "Documentation")
    if page.layout == "one-page":
        page.eq("a button that opens the menu", [r["tag"], r["type"], r["controls"]], ["button", "button", "documentation-menu"])
    else:
        page.eq("which links to /docs", [r["tag"], r["href"]], ["a", "/docs"])


FORM_FIELDS = """
const scope = S !== document.documentElement ? S : document.querySelector("[role=document]") || document.querySelector("main");
const forms = [...scope.querySelectorAll("form")];
const text = ["", "text", "email", "password", "search", "tel", "url", "number", "date"];
return forms.map((f, i) => ({
  i,
  fields: [...f.querySelectorAll("input")].filter(x => text.includes((x.getAttribute("type") || "").toLowerCase()) && !x.disabled)
    .map(x => [x, x.getAttribute("name") || x.getAttribute("type") || "input"]),
  submits: [...f.querySelectorAll("button:not([type]), button[type=submit], input[type=submit]")].filter(x => !x.disabled)
    .map(x => [x, (x.textContent || x.value || "").trim() || "submit"]),
}));
"""

# Every submit event that reaches the window, with whether it was finally canceled (read after the
# dispatch, so every handler has run).
SUBMIT_SPY = """
window.__bhSubmits = [];
addEventListener("submit", (e) => setTimeout(() => __bhSubmits.push(e.defaultPrevented), 0), true);
window.__bhMarker = "kept";
"""


@check("example-forms", ("/docs#forms", "/docs#group", "/docs#color-schemes", "/docs#theme-picker"))
def example_forms(page):
    """No example form navigates: for every form in the route's content, Enter in each enabled
    text-like input (text, email, password, search, tel, url, number, date) and a click on each
    enabled submit button leave the URL and the document as they were (a marker set on window
    survives, so nothing reloaded), and any submit event they cause is canceled. The browser's own
    rules decide whether Enter submits at all (implicit submission: Chrome never submits a form
    with several text fields and no submit button, Firefox may) and whether validation stops a
    submission; the check only asks that none goes through."""
    forms = page.js(FORM_FIELDS)
    page.expect("the page has example forms", len(forms) > 0)
    page.js(SUBMIT_SPY)
    url = page.url()
    tried, events = 0, 0

    def after(label):
        page.sleep(0.5)
        try:
            st = page.js("return {marker: window.__bhMarker, url: location.pathname + location.search + location.hash,"
                         " submits: window.__bhSubmits}")
        except Exception as e:   # the document went away: a submission navigated
            page.expect(label, False, error=f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        page.expect(label, st["marker"] == "kept" and all(st["submits"] or [True]), **st)
        page.url_kept(label, url)
        page.js("window.__bhSubmits.length = 0")
        return len(st["submits"])

    for f in forms:
        for el, name in f["fields"]:
            page.js("arguments[0].scrollIntoView({block: 'center'}); arguments[0].focus();", el)
            page.key("ENTER")
            events += after(f"form {f['i']}: Enter in {name} does not navigate")
            tried += 1
        for el, name in f["submits"]:
            page.click(el)
            events += after(f"form {f['i']}: its {name!r} button does not navigate")
            tried += 1
    page.expect("something was submitted", tried > 0, tried=tried)
    page.note(f"{len(forms)} forms, {tried} submissions tried, {events} submit events (all canceled)")


# -- Phase 4: the controls that became buttons, and the off-canvas menu's inert page ---------------

PHASE4_BUTTONS = ("Phase 4 made these controls buttons (PLAN.md Workflow, 4; tests/README.md, Accessibility): the "
                  "oracle's are links with tabindex=-1 or href, which Space does not press and Tab skips")


def shift_tab(page):
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    ActionChains(page.driver, duration=0).key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT).perform()


@check("theme-toggle-button", ("/", "/does-not-exist"), layouts=("one-page",), layout_reason=PHASE4_BUTTONS)
def theme_toggle_button(page):
    """The header's color-scheme toggle is a <button type="button"> with no href
    (`button[data-scheme-toggle]`): Tab from the header's GitHub link reaches it; Space turns the
    page dark (data-theme="dark") and Enter light again, with no navigation (URL and history
    kept), and it reads "Turn on dark mode" after."""
    gh = "body > header nav ul.icons a[aria-label='GitHub repository']"
    t = "body > header nav ul.icons button[data-scheme-toggle]"
    r = page.js("const b = document.querySelector(arguments[0]); return b && [b.getAttribute('type'), b.hasAttribute('href')]", t)
    page.eq("a button of type button, with no href", r, ["button", False])
    page.key("SHIFT")   # a key press first, so the focus that follows is keyboard focus
    page.expect("the GitHub link takes focus", page.focus(gh))
    page.key("TAB")
    page.eq("Tab reaches the toggle", page.js("return document.activeElement === document.querySelector(arguments[0])", t), True,
            active=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
    url = page.url()
    page.key(" ")
    page.wait("Space: dark", "document.documentElement.getAttribute('data-theme') === 'dark'", 1.5)
    page.key("ENTER")
    page.wait("Enter: light", "document.documentElement.getAttribute('data-theme') === 'light'", 1.5)
    page.url_kept("no navigation", url)
    wait_label(page, "Turn on dark mode")


MENU_STATE = r"""
const m = document.querySelector('#documentation-menu');
const a = document.activeElement;
const outside = [];
for (let n = m; n.parentElement && n !== document.body; n = n.parentElement)
  for (const s of n.parentElement.children) if (s !== n) outside.push(s);
return {open: m.classList.contains('is-open-on-mobile'), menuInert: m.inert,
        outsideInert: outside.filter(e => e.inert).length, outside: outside.length,
        focus: a === document.body ? 'body' : a ? a.outerHTML.slice(0, 90) : null,
        inside: m.contains(a), expanded: document.querySelector(arguments[0]).getAttribute('aria-expanded')};
"""


@check("mobile-menu-inert", "/docs#modal", width=375, height=812, layouts=("one-page",),
       layout_reason="the oracle's off-canvas menu leaves the page behind it in the tab order (01 §2); from Phase 4 "
                     "docs.js makes it inert while the menu is open (tests/README.md, Accessibility)")
def mobile_menu_inert(page):
    """At 375 px the open off-canvas menu keeps focus (criterion 7, the mobile menu's focus): opened
    with Enter on the breadcrumb's Documentation button, focus is on the menu's Close button, the
    opener has aria-expanded="true", every sibling of the menu and of each of its ancestors up to
    <body> is inert and the menu is not, and 60 Tabs and 10 Shift+Tabs never put focus outside the
    menu. Escape closes it: nothing outside is inert, the menu is inert again (off screen, its links
    out of the tab order), aria-expanded="false" and focus is back on the opener. Opened again and
    closed by a nav link (Layout's Grid): nothing stays inert and the URL is /docs#grid. Opened at
    375 and resized to 1300 (the menu becomes the side nav), nothing is inert; back at 375, still
    open, the page behind is inert again."""
    def state():
        return page.js(MENU_STATE, OPENER)

    page.expect("the Documentation button takes focus", page.focus(OPENER))
    page.key("ENTER")
    page.wait("Enter opens the menu", IS_OPEN, 1.5)
    page.wait("focus is on Close", "document.activeElement === document.querySelector(arguments[0])", 1, args=(CLOSE,))
    s = state()
    page.eq("aria-expanded is true", s["expanded"], "true")
    page.eq("every element outside the menu is inert", s["outsideInert"], s["outside"], **s)
    page.eq("the menu is not inert", s["menuInert"], False)
    for i in range(60):
        page.key("TAB")
        s = state()
        page.expect(f"Tab {i + 1}: focus stays in the menu", s["inside"] or s["focus"] == "body", **s)
    for i in range(10):
        shift_tab(page)
        s = state()
        page.expect(f"Shift+Tab {i + 1}: focus stays in the menu", s["inside"] or s["focus"] == "body", **s)
    page.key("ESCAPE")
    page.wait("Escape closes it", f"!{IS_OPEN}", 1.5)
    page.sleep(0.1)
    s = state()
    page.eq("Escape: nothing outside is inert", s["outsideInert"], 0, **s)
    page.eq("Escape: the menu is inert again", s["menuInert"], True)
    page.eq("Escape: aria-expanded is false", s["expanded"], "false")
    page.wait("Escape: focus is on the opener", "document.activeElement === document.querySelector(arguments[0])", 1, args=(OPENER,))
    page.click(OPENER)
    page.wait("a click opens it", IS_OPEN, 1.5)
    s = state()
    page.eq("open again: the page behind is inert", s["outsideInert"], s["outside"], **s)
    summary = page.js("""return [...document.querySelectorAll('#documentation-menu nav details > summary')]
                         .find(s => s.textContent.trim() === 'Layout')""")
    if not page.js("return arguments[0].parentElement.open", summary):
        page.click(summary)
    page.click("#documentation-menu a[href='#grid']")
    page.wait("the link closes the menu", f"!{IS_OPEN}", 1.5)
    page.wait("the URL is /docs#grid", "location.hash === '#grid'", 3)
    page.sleep(0.2)
    s = state()
    page.eq("nav link: nothing outside is inert", s["outsideInert"], 0, **s)
    page.eq("nav link: the menu is inert", s["menuInert"], True)
    page.click(OPENER)
    page.wait("it opens once more", IS_OPEN, 1.5)
    page.resize(1300, 900)
    page.sleep(0.3)
    s = state()
    page.eq("1300: nothing outside is inert", s["outsideInert"], 0, **s)
    page.eq("1300: the menu is not inert", s["menuInert"], False)
    page.resize(375, 812)
    page.sleep(0.3)
    s = state()
    page.eq("back at 375, still open: the page behind is inert again", s["outsideInert"], s["outside"], **s)
    page.key("ESCAPE")
    page.wait("closed", f"!{IS_OPEN}", 1.5)
    page.eq("closed: nothing outside is inert", state()["outsideInert"], 0)


COPY_INFO = r"""
const b = arguments[0];
return {tooltip: b.getAttribute('data-tooltip'), focused: document.activeElement === b, copied: window.__bhCopied || []};
"""
STATUS = "const p = document.querySelector('body > p.visually-hidden[role=status]'); return p && p.textContent"

# A code block's tab stop (site.js, Code block focus): whether its code overflows it, its tabindex,
# role and aria-label, and the name a block that overflows takes from its code's language.
PRE_FOCUS = r"""
const p = arguments[0], lang = (p.querySelector("code").className.match(/\blanguage-([\w-]+)/) || [])[1];
return {overflows: p.scrollWidth > p.clientWidth || p.scrollHeight > p.clientHeight,
        attrs: [p.getAttribute("tabindex"), p.getAttribute("role"), p.getAttribute("aria-label")],
        name: ({html: "HTML", css: "CSS", scss: "SCSS", bash: "Bash"}[lang] || "Example") + " code"};
"""


def expect_pre_focus(page, label, pre):
    """Assert, within 1 s (site.js checks a block from a ResizeObserver, so a block just shown is
    checked a frame later), that a code block that overflows has tabindex="0", role="figure" and
    aria-label "<language> code", and one that does not has none of the three; return PRE_FOCUS."""
    end = time.time() + 1
    while True:
        fit = page.js(PRE_FOCUS, pre)
        want = ["0", "figure", fit["name"]] if fit["overflows"] else [None, None, None]
        if fit["attrs"] == want or time.time() > end:
            break
        time.sleep(0.05)
    page.eq(f"{label} {'overflows: a figure in the tab order' if fit['overflows'] else 'does not overflow: no tab stop, role or name'}",
            fit["attrs"], want, overflows=fit["overflows"])
    return fit


@check("copy-keyboard", ("/docs#button", "/examples"), layouts=("one-page",), layout_reason=PHASE4_BUTTONS)
def copy_keyboard(page):
    """The copy buttons are in the tab order: Tab from the focusable element before the route's first
    copy button (on /examples inside a Markup disclosure, opened first) reaches it; Enter copies the
    block's `pre code` text, the tooltip and the visually hidden status line (`body >
    p.visually-hidden[role=status]`) read "Copied", and 1 s later the tooltip reads "Copy to
    clipboard", the status line is empty and keyboard focus is still on the button; Space copies
    again. Then the block's <pre> is a tab stop only when its code overflows it (site.js, Code
    block focus): a block that does not overflow has no tabindex, role or aria-label, and Tab moves
    past it to the next control, after the block in document order; a block that overflows has
    tabindex="0", role="figure" and aria-label "<language> code" ("HTML code"), and Tab moves to
    it (pre-scroll-keyboard holds that branch at 375 px, where Quick start's blocks overflow). The
    note says which branch each route took."""
    page.js(COPY_SPY)
    btn = page.js("const b = S.querySelector('button.copy-to-clipboard');"
                  " b.closest('details')?.setAttribute('open', ''); b.scrollIntoView({block: 'center'}); return b;")
    code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", btn)
    prev = page.js(r"""const b = arguments[0];
      const all = [...document.querySelectorAll('a[href], button, input, select, textarea, summary, [tabindex]')]
        .filter(e => e.tabIndex >= 0 && !e.disabled && !e.closest('[inert]') && e.getClientRects().length);
      return all[all.indexOf(b) - 1];""", btn)
    page.key("SHIFT")
    page.js("arguments[0].focus({preventScroll: true})", prev)
    page.key("TAB")
    page.eq("Tab reaches the copy button", page.js("return document.activeElement === arguments[0]", btn), True,
            active=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
    page.js("window.__bhCopied.length = 0")
    page.key("ENTER")
    page.wait("Enter copies", "window.__bhCopied.length === 1", 1)
    s = page.js(COPY_INFO, btn)
    page.eq("Enter: the block's code", s["copied"][0]["text"], code)
    page.eq("Enter: the tooltip reads Copied", s["tooltip"], "Copied")
    page.eq("the status line says Copied", page.js(STATUS), "Copied")
    page.wait("it reverts", "arguments[0].getAttribute('data-tooltip') === 'Copy to clipboard' && !!arguments[0].querySelector('svg.clipboard')",
              2, args=(btn,))
    page.sleep(0.2)
    page.eq("keyboard focus stays on the button", page.js(COPY_INFO, btn)["focused"], True)
    page.eq("the status line is empty again", page.js(STATUS), "")
    page.key(" ")
    page.wait("Space copies", "window.__bhCopied.length === 2", 1)
    page.wait("it reverts again", "arguments[0].getAttribute('data-tooltip') === 'Copy to clipboard'", 2, args=(btn,))
    pre = page.js("return arguments[0].parentElement.querySelector('pre')", btn)
    fit = expect_pre_focus(page, "the block", pre)
    page.key("TAB")
    active = page.js("return document.activeElement.outerHTML.slice(0, 120)")
    if fit["overflows"]:
        page.eq("Tab moves to the block's pre, which overflows", page.js("return document.activeElement === arguments[0]", pre),
                True, active=active)
    else:
        page.expect("Tab skips the block's pre, which does not overflow, for the next control after it", page.js(
            """const a = document.activeElement, p = arguments[0], b = arguments[1];
            return a !== p && a !== b && a !== document.body && !p.contains(a)
              && !!(p.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_FOLLOWING);""", pre, btn), active=active)
    page.note(f"the first block {'overflows: Tab focused it' if fit['overflows'] else 'does not overflow: Tab moved on to ' + ' '.join(active.split())[:60]}")


@check("pre-scroll-keyboard", "/docs", width=375, height=812, layouts=("one-page",),
       layout_reason="from Phase 4 a highlighted <pre> whose code overflows is a focusable figure (build.mjs writes "
                     "tabindex=0, site.js keeps it on a block that overflows), so it scrolls from the keyboard "
                     "(axe's scrollable-region-focusable); the oracle's take no focus")
def pre_scroll_keyboard(page):
    """At 375 px Quick start's first code block that overflows sideways is a figure in the tab order
    (tabindex="0", role="figure", aria-label "<language> code", from site.js's Code block focus),
    takes focus with Tab from its copy button, matches :focus-visible with an inset focus ring
    (box-shadow), and the Right arrow key scrolls it."""
    pre = page.js("const p = [...S.querySelectorAll('.code pre')].find(p => p.scrollWidth > p.clientWidth);"
                  " p && p.scrollIntoView({block: 'center'}); return p || null;")
    page.expect("a code block overflows", pre is not None)
    expect_pre_focus(page, "the block", pre)
    btn = page.js("return arguments[0].parentElement.querySelector('button.copy-to-clipboard')", pre)
    page.key("SHIFT")
    page.js("arguments[0].focus({preventScroll: true})", btn)
    page.key("TAB")
    page.eq("Tab focuses the pre", page.js("return document.activeElement === arguments[0]", pre), True)
    page.eq("it matches :focus-visible", page.js("return arguments[0].matches(':focus-visible')", pre), True)
    ring = page.js("return getComputedStyle(arguments[0]).boxShadow", pre)
    page.expect("its focus ring shows", "inset" in ring, ring=ring)
    page.key("ARROW_RIGHT", 8)
    page.sleep(0.3)
    page.expect("the arrow keys scroll it", page.js("return arguments[0].scrollLeft", pre) > 0)
