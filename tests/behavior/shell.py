"""Shell: what every page or every docs page shares (docs/research/01 §2: PageContext, Nav, Header,
Code, ModalContext, DocumentationMenu, Breadcrumb; and the example forms' submit, 01 §2's last
paragraph). In the static site these live in site.js and docs.js."""
import math

from behavior import COPY_SPY, check

GROUP = "shell"

TOGGLE = "body > header nav ul.icons a[aria-label$='dark mode']"
KEY = "femtoColorScheme"

THEME_STATE = """
const a = document.querySelector(arguments[0]);
return {theme: document.documentElement.getAttribute("data-theme"), stored: localStorage.getItem(arguments[1]),
        label: a && a.getAttribute("aria-label"), moon: !!(a && a.querySelector("svg.icon-theme-toggle.moon")),
        icon: !!(a && a.querySelector("svg.icon-theme-toggle"))};
"""


def theme(page):
    return page.js(THEME_STATE, TOGGLE, KEY)


def wait_label(page, label):
    """The toggle's label and icon settle within 1 s of a load or a change (the oracle relabels it in
    a React effect after the attribute changes)."""
    page.wait(f"toggle reads {label!r}", "(() => { const a = document.querySelector(arguments[0]);"
              " return a && a.getAttribute('aria-label') === arguments[1]"
              " && !!a.querySelector('svg.icon-theme-toggle.moon') === (arguments[1] === 'Turn off dark mode'); })()",
              1, args=(TOGGLE, label))


def toggle_and_expect(page, theme_after, label_after):
    url = page.url()
    page.click(TOGGLE)
    page.wait(f"data-theme becomes {theme_after}",
              "document.documentElement.getAttribute('data-theme') === arguments[0]", 2, args=(theme_after,))
    page.eq(f"{KEY} stores {theme_after!r} as JSON", theme(page)["stored"], f'"{theme_after}"')
    wait_label(page, label_after)
    page.eq(f"toggle icon {'has' if theme_after == 'dark' else 'lacks'} the moon class", theme(page)["moon"], theme_after == "dark")
    page.eq("the toggle does not navigate (no #)", page.url(), url)


@check("theme-toggle", ("/", "/docs/typography"))
def theme_toggle(page):
    """With a light OS scheme and nothing stored: <html> has no data-theme, the header toggle
    (`ul.icons a`, its icon `svg.icon-theme-toggle`) reads "Turn on dark mode" without the `moon`
    class. A click sets data-theme="dark" on <html>, stores localStorage femtoColorScheme = '"dark"'
    (JSON), relabels the toggle "Turn off dark mode" and adds `moon`; the URL is unchanged (no `#`).
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


@check("theme-toggle-keyboard", ("/", "/docs/typography"))
def theme_toggle_keyboard(page):
    """The header toggle (an <a href>) works from the keyboard as from the pointer: focused, Enter
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
        page.eq("Enter: URL unchanged", page.url(), url)


COMPARISON = "[...document.querySelectorAll('main > section.comparison div.code[data-theme]')].map(d => d.getAttribute('data-theme'))"
THEAD = "(() => { const h = document.querySelector('div.overflow-auto > table > thead[data-theme]'); return h && h.getAttribute('data-theme'); })()"


@check("theme-os-live", ("/", "/docs/table"))
def theme_os_live(page):
    """With nothing stored, the page follows a live change of the OS scheme (prefers-color-scheme
    switched while the page is open; use-prefers-color-scheme in PageContext.jsx): at dark the
    header toggle reads "Turn off dark mode" with `moon`, the homepage comparison's code samples
    read data-theme="dark" and /docs/table's inverse thead "light"; back at light all three return.
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


@check("theme-stored-dark", ("/", "/docs/button"), storage={KEY: '"dark"'})
def theme_stored_dark(page):
    """A stored choice wins over the OS: with femtoColorScheme = '"dark"' stored and a light OS,
    the loaded page has data-theme="dark" on <html> and the toggle reads "Turn off dark mode" with
    the `moon` class."""
    page.eq("data-theme is the stored dark", theme(page)["theme"], "dark")
    wait_label(page, "Turn off dark mode")


@check("theme-stored-light", "/docs/button", media="dark", storage={KEY: '"light"'})
def theme_stored_light(page):
    """With femtoColorScheme = '"light"' stored and a dark OS, the page has data-theme="light" and
    the toggle reads "Turn on dark mode" without `moon`; a click stores '"dark"'."""
    page.eq("data-theme is the stored light", theme(page)["theme"], "light")
    wait_label(page, "Turn on dark mode")
    toggle_and_expect(page, "dark", "Turn off dark mode")


@check("theme-stored-invalid", "/docs/table", media="dark", storage={KEY: '"blue"'},
       oracle_bug={"fails": "a stored value other than light or dark sets no data-theme",
                   "reason": "the oracle writes any stored femtoColorScheme into data-theme (PageContext.jsx), so a "
                             "value the site never writes, such as '\"blue\"', makes a dark-OS page light and "
                             "ignores the reader's OS scheme; the static site's head script and site.js accept "
                             "only \"light\" and \"dark\" (Decision 14; PLAN.md, oracle-bug)"})
def theme_stored_invalid(page):
    """With a dark OS and femtoColorScheme = '"blue"' stored (valid JSON, but neither "light" nor
    "dark", a value the site never writes), the stored item is left as it is, <html> has no
    data-theme, and the page follows the OS: the toggle reads "Turn off dark mode" with `moon`, and
    /docs/table's inverse thead reads data-theme="light". A click stores '"light"' and sets
    data-theme="light". The oracle writes "blue" into data-theme, which is the assertion it fails."""
    s = theme(page)
    page.eq("the stored value is left as it is", s["stored"], '"blue"')
    page.eq("a stored value other than light or dark sets no data-theme", s["theme"], None, **s)
    page.holds("a stored value other than light or dark sets no data-theme",
               "!document.documentElement.hasAttribute('data-theme')", 0.5)
    wait_label(page, "Turn off dark mode")
    page.wait("the inverse thead reads light",
              "(() => { const h = document.querySelector('div.overflow-auto > table > thead[data-theme]');"
              " return !!h && h.getAttribute('data-theme') === 'light'; })()", 1)
    toggle_and_expect(page, "light", "Turn on dark mode")


@check("theme-cross-tab", "/docs/typography")
def theme_cross_tab(page):
    """Two tabs of the same browser: a toggle click in tab A (on /docs/typography) reaches tab B (on
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


@check("header-fixed", "/docs/modal")
def header_fixed(page):
    """On a docs page (1300 px): `body > header` has class `is-fixed-above-lg` and not `is-fixed` at
    the top; `is-fixed` is added once scrollY > 20 (not at 20, at 21) and removed when scrolling back
    to 20 or 0."""
    cls = "document.querySelector('body > header').classList"
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


@check("copy-button", ("/docs", "/docs/modal"))
def copy_button(page):
    """Each code block's copy link (`a.copy-to-clipboard`, data-tooltip "Copy to clipboard", icon
    `svg.clipboard`): a click copies exactly that block's code text (its `pre code` textContent; the
    copy is recorded in the page, the machine's clipboard is never touched) and leaves the URL as it
    was. Timed in the page: within 100 ms of the click the tooltip reads "Copied" with the animated
    `svg.check` icon, and 1 s later (900 to 1500 ms) "Copy to clipboard" with `svg.clipboard` again,
    with no other step; the link then does not hold focus. A second block's link copies its own
    code."""
    page.js(COPY_SPY)
    links = page.els("a.copy-to-clipboard")
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
        page.eq(f"link {n}: URL unchanged", page.url(), url)
        page.wait(f"link {n}: reverted", "arguments[0].getAttribute('data-tooltip') === 'Copy to clipboard' && "
                  "!!arguments[0].querySelector('svg.clipboard') && window.__bhCopy.length >= 3", 2.5, args=(link,))
        tl = page.js("return window.__bhCopy")
        page.eq(f"link {n}: the steps", [x[1:] for x in tl], [["click"], ["Copied", "check"], ["Copy to clipboard", "clipboard"]],
                timeline=tl)
        page.expect(f"link {n}: 'Copied' within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
        page.expect(f"link {n}: reverts 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
        page.eq(f"link {n}: blurred after reverting", page.js(COPY_STATE, link)["focused"], False)


@check("copy-button-repeat", "/docs/modal")
def copy_button_repeat(page):
    """Repeated use of a copy link, as Code.jsx behaves (every click schedules its own 1 s revert,
    and the first one to fire reverts): two clicks 500 ms apart copy the block's code twice, and
    "Copied" reverts to "Copy to clipboard" with `svg.clipboard` once, 1 s after the FIRST click (900
    to 1200 ms), with no other step; the link then does not hold focus."""
    page.js(COPY_SPY)
    link = page.els("a.copy-to-clipboard")[0]
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


@check("modal-helper", ("/docs/modal",))
def modal_helper(page):
    """The modal helper on <html> (01 §2, ModalContext), opened by /docs/modal's "Open modal"
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


@check("modal-scrollbar-width", "/docs/modal")
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


TOC_STATE = """
const toc = document.getElementById("table-of-contents");
const links = [...toc.querySelectorAll("a")];
const sections = [...document.querySelectorAll("#content[role=document] > section")].slice(0, links.length);
const h = document.querySelector("body > header").offsetHeight;
const root = document.documentElement;
let model;
if (root.scrollTop + innerHeight >= root.scrollHeight) model = links.length - 1;
else model = sections.findIndex(s => { const r = s.getBoundingClientRect(); return r.top - 2 * h < innerHeight && r.top - 2 * h + r.height > 0; });
return {cur: links.map((a, i) => a.hasAttribute("aria-current") ? i : -1).filter(i => i >= 0),
        vals: links.filter(a => a.hasAttribute("aria-current")).map(a => a.getAttribute("aria-current")),
        model, y: Math.round(scrollY), max: root.scrollHeight - innerHeight, n: links.length, ns: sections.length};
"""


@check("toc-spy", ("/docs", "/docs/typography", "/docs/forms/input", "/docs/nav", "/docs/colors", "/docs/button",
                   "/docs/version-picker"))
def toc_spy(page):
    """The table of contents' scrollspy (TableOfContents.jsx, ghostui's Scrollspy; docs.js): scrolled
    through the page in 40 steps from the top to the end, the one link with aria-current="page" is
    always the first of #content's sections in view with the viewport shifted down by twice the
    header's height, or the last link at the page's end, and none when no section is in that view
    (ghostui's rule, computed in the page from the same DOM); the current link changes while
    scrolling. Phase 3's one-page spy replaces it."""
    first = page.js(TOC_STATE)
    page.expect("the page has a table of contents with a section per link", first["n"] >= 2 and first["ns"] == first["n"], **first)
    seen, bad = set(), []
    steps = 40
    for k in range(steps + 1):
        page.scroll_to(round(first["max"] * k / steps))
        page.ajs("await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));"
                 "await new Promise(r => setTimeout(r, 120)); return 1;")
        s = page.js(TOC_STATE)
        seen.add(tuple(s["cur"]))
        want = [s["model"]] if s["model"] >= 0 else []
        if s["cur"] != want or any(v != "page" for v in s["vals"]):
            bad.append({x: s[x] for x in ("y", "cur", "vals", "model")})
    page.eq("the current link follows the scroll at every step (ghostui's rule)", bad, [], steps=steps)
    page.expect("the current link changes while scrolling", len(seen) >= 2, seen=sorted(seen))


MENU_STATE = """
return [...document.querySelectorAll("#documentation-menu nav details")].map(d => {
  const s = d.querySelector("summary");
  return {title: s.textContent.trim(), open: d.open, summaryCurrent: s.getAttribute("aria-current"),
          current: [...d.querySelectorAll("a[aria-current]")].map(a => [a.getAttribute("href"), a.getAttribute("aria-current")])};
});
"""

CATEGORY = {"/docs": "Getting started", "/docs/version-picker/jade": "Getting started", "/docs/colors": "Customization",
            "/docs/grid": "Layout", "/docs/table": "Content", "/docs/forms/input": "Forms", "/docs/forms/radios": "Forms",
            "/docs/modal": "Components"}


@check("side-menu-current", ("/docs", "/docs/forms/input", "/docs/version-picker/jade"))
def side_menu_current(page):
    """The side menu (`#documentation-menu nav`) opens the category that holds the route: that
    `details` is open and its `summary` has aria-current="true"; every other category is closed and
    has no aria-current; the one link with aria-current is the route's own (aria-current="page"), or
    for a version-picker color route the "Version picker" link."""
    menu = page.js(MENU_STATE)
    want = CATEGORY[page.route]
    link = "/docs/version-picker" if page.route.startswith("/docs/version-picker/") else page.route
    opened = [m["title"] for m in menu if m["open"]]
    page.eq("only the route's category is open", opened, [want], menu=menu)
    cur = [m["title"] for m in menu if m["summaryCurrent"] is not None]
    page.eq("only its summary has aria-current", cur, [want])
    page.eq("its summary's aria-current is 'true'", next(m for m in menu if m["title"] == want)["summaryCurrent"], "true")
    links = [x for m in menu for x in m["current"]]
    page.eq("the route's link is the only current link", links, [[link, "page"]])


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


@check("side-menu-max-height", ("/docs/grid",), width=375, height=812)
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
        url: location.pathname + location.search + location.hash};
"""


@check("mobile-menu", "/docs/modal", width=375, height=812)
def mobile_menu(page):
    """At 375 px the breadcrumb's "Documentation" link opens the off-canvas menu: a click adds
    `is-open-on-mobile` to `aside#documentation-menu`, <html> stops scrolling (overflow-y hidden)
    and the URL is unchanged; the menu's own close link (`header a[aria-label=Close]`) removes the
    class, scrolling returns and the URL is still unchanged."""
    s = page.js(MOBILE)
    page.eq("closed on load", s["open"], False)
    url = s["url"]
    page.click("nav[aria-label=breadcrumb] ul li:first-child a")
    page.wait("the breadcrumb link opens the menu", "document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')", 1)
    s = page.js(MOBILE)
    page.eq("the page behind stops scrolling", s["overflowY"], "hidden")
    page.eq("opening leaves the URL", s["url"], url)
    page.click("#documentation-menu header a[aria-label=Close]")
    page.wait("the close link closes the menu", "!document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')", 1)
    s = page.js(MOBILE)
    page.expect("the page scrolls again", s["overflowY"] != "hidden", **s)
    page.eq("closing leaves the URL", s["url"], url)


@check("mobile-menu-keyboard", "/docs/modal", width=375, height=812)
def mobile_menu_keyboard(page):
    """At 375 px the off-canvas menu works from the keyboard as from the pointer: Enter on the
    breadcrumb's focused "Documentation" link adds `is-open-on-mobile`, with no navigation (URL
    unchanged, the document kept); Enter on the menu's focused close link removes it, still with no
    navigation."""
    page.js("window.__bhMarker = 'kept'")
    url = page.url()
    page.expect("the Documentation link takes focus", page.focus("nav[aria-label=breadcrumb] ul li:first-child a"))
    page.key("ENTER")
    page.wait("Enter on Documentation opens the menu", "document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')", 1.5)
    page.eq("opening: no navigation", (page.url(), page.js("return window.__bhMarker || null")), (url, "kept"))
    page.sleep(0.5)   # the menu slides in
    page.expect("the close link takes focus", page.focus("#documentation-menu header a[aria-label=Close]"))
    page.key("ENTER")
    page.wait("Enter on the close link closes the menu", "!document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')", 1.5)
    page.eq("closing: no navigation", (page.url(), page.js("return window.__bhMarker || null")), (url, "kept"))


@check("mobile-menu-link", "/docs/modal", width=375, height=812)
def mobile_menu_link(page):
    """At 375 px, with the off-canvas menu open, opening the "Layout" category and following its
    "Grid" link goes to /docs/grid with the menu closed (no `is-open-on-mobile`) and Grid's page
    shown (its hgroup h1 reads "Grid"). Back then returns to the same /docs/modal document (the
    oracle's client-side history, the static site's back-forward cache: a marker set on window
    survives), and its menu is closed too: the link closed it before the page was left."""
    page.js("window.__bhMarker = 'kept'")
    page.click("nav[aria-label=breadcrumb] ul li:first-child a")
    page.wait("menu open", "document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')", 1)
    summary = page.js("""return [...document.querySelectorAll('#documentation-menu nav details > summary')]
                         .find(s => s.textContent.trim() === 'Layout')""")
    page.click(summary)
    page.wait("Layout opens", "arguments[0].parentElement.open", 1, args=(summary,))
    page.click("#documentation-menu a[href='/docs/grid']")
    page.wait_navigated("/docs/grid")
    page.eq("the menu is closed", page.js(MOBILE)["open"], False)
    page.eq("Grid's page", page.js("return document.querySelector('main hgroup h1').textContent.trim()"), "Grid")
    page.js("history.back()")
    page.wait_navigated("/docs/modal", label="back on /docs/modal")
    page.eq("back: the same document (kept or restored from the back-forward cache)", page.js("return window.__bhMarker || null"), "kept")
    page.eq("back: the menu is closed", page.js(MOBILE)["open"], False)


@check("breadcrumb-sticky", "/docs/modal", width=375, height=812)
def breadcrumb_sticky(page):
    """At 375 px the breadcrumb (`nav[aria-label=breadcrumb]`, sticky at top: -1px) has no class at
    the top. Measured from its own natural top t (its top plus scrollY at the top of the page), it
    gets `is-sticky` (within 1 s) once it sticks, scrolled 400 px down and at ceil(t) + 2 (its top
    then at -2 px or less, Breadcrumb.jsx's rule being top <= -1), and loses it (within 1 s) while it
    does not, at floor(t) - 1 and floor(t) - 20 (its top at 1 px or more) and at the top. Relative
    to t because the page above it differs: the static site has no maintenance banner (Decision 5),
    so its breadcrumb sits about 37 px higher than the oracle's."""
    bc = "document.querySelector('nav[aria-label=breadcrumb]')"
    page.eq("no is-sticky at the top", page.js(f"return {bc}.classList.contains('is-sticky')"), False)
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


@check("breadcrumb-chapter", ("/docs", "/docs/version-picker/jade", "/docs/colors", "/docs/grid", "/docs/table",
                              "/docs/forms/radios", "/docs/modal"), width=375, height=812)
def breadcrumb_chapter(page):
    """The breadcrumb's last item names the route's menu category (Getting started, Customization,
    Layout, Content, Forms, Components; a version-picker color route is Getting started), and its
    first item is the "Documentation" link to /docs."""
    page.expect("the page has a breadcrumb", page.js("return !!document.querySelector('nav[aria-label=breadcrumb] ul li a')"))
    r = page.js("""const n = document.querySelector('nav[aria-label=breadcrumb]');
      const a = n.querySelector('ul li:first-child a');
      return {chapter: n.querySelector('ul li:last-child').textContent.trim(), text: a.textContent.trim(), href: a.getAttribute('href')}""")
    page.eq("the chapter is the route's category", r["chapter"], CATEGORY[page.route])
    page.eq("the first item is Documentation", r["text"], "Documentation")
    page.eq("which links to /docs", r["href"], "/docs")


FORM_FIELDS = """
const scope = document.querySelector("[role=document]") || document.querySelector("main");
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


@check("example-forms", ("/docs/forms", "/docs/forms/input", "/docs/group", "/docs/color-schemes", "/docs/version-picker"))
def example_forms(page):
    """No example form navigates: for every form in the page's content, Enter in each enabled
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
        page.expect(label, st["marker"] == "kept" and st["url"] == url and all(st["submits"] or [True]), **st)
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
