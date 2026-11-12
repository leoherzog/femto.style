"""Shell: what every page or every docs page shares (the Remix site's PageContext, Nav, Header,
Code, ModalContext, DocumentationMenu and Breadcrumb), and the example forms' submit, which their
method="dialog" stops. In the static site these live in site.js and docs.js. The one page's spy,
its URLs and ?theme= are the one-page group's.

The Remix site's link-styled controls are buttons here: the header's color-scheme toggle, the
code blocks' copy controls, the breadcrumb's Documentation control and the off-canvas menu's Close.
Some selectors still take either element (`:is(a, button)`); what only a button has (Space, the tab
order, type=button) has checks of its own."""
import json
import math
import time

from behavior import COPY_SPY, HEADING_LINE, check, expect_name

GROUP = "shell"

TOGGLE = "body > header nav button:has(> span[role=img][aria-label$='dark mode'])"   # a button named by its icon (Decision 18)
KEY = "femtoColorScheme"

THEME_STATE = """
const a = document.querySelector(arguments[0]), i = a && a.querySelector(":scope > span[role=img]");
return {theme: document.documentElement.getAttribute("data-theme"), stored: localStorage.getItem(arguments[1]),
        label: i && i.getAttribute("aria-label"), moon: !!i && i.textContent === "\\u{1F319}", icon: !!i};
"""


def theme(page):
    return page.js(THEME_STATE, TOGGLE, KEY)


def wait_label(page, label):
    """The toggle's label and icon settle within 1 s of a load or a change."""
    page.wait(f"toggle reads {label!r}", "(() => { const a = document.querySelector(arguments[0]);"
              " const i = a && a.querySelector(':scope > span[role=img]');"
              " return !!i && i.getAttribute('aria-label') === arguments[1]"
              " && (i.textContent === '\\u{1F319}') === (arguments[1] === 'Turn off dark mode'); })()",
              1, args=(TOGGLE, label))


def expect_scheme(page, label, stored):
    """<html>'s data-theme and the stored choice: `stored` ("light" or "dark") set on both, or None,
    no data-theme and nothing stored, the page following the OS (a toggle to the OS's own scheme
    removes the choice, Decision 14)."""
    if stored is None:
        page.wait(f"{label}: no data-theme", "!document.documentElement.hasAttribute('data-theme')", 2)
        page.eq(f"{label}: nothing stored", theme(page)["stored"], None)
    else:
        page.wait(f"{label}: data-theme becomes {stored}",
                  "document.documentElement.getAttribute('data-theme') === arguments[0]", 2, args=(stored,))
        page.eq(f"{label}: {KEY} stores {stored!r} as JSON", theme(page)["stored"], f'"{stored}"')


def toggle_and_expect(page, stored, label_after):
    """A click on the header toggle: `stored` as expect_scheme() takes it, then the label and its icon
    (the moon while the page is dark), with the URL unchanged."""
    url = page.url()
    page.click(TOGGLE)
    expect_scheme(page, "click", stored)
    wait_label(page, label_after)
    dark = label_after == "Turn off dark mode"
    page.eq(f"toggle icon is {'the moon' if dark else 'the sun'}", theme(page)["moon"], dark)
    page.url_kept("the toggle does not navigate (no #)", url)


@check("theme-toggle", ("/", "/docs#typography"))
def theme_toggle(page):
    """With a light OS scheme and nothing stored: <html> has no data-theme, the header toggle
    (femto's button in the header nav's last list; its icon, the `span[role=img]` of Decision 18,
    holds the emoji of Decision 16 and names the button) reads
    "Turn on dark mode" with the sun ☀️. A click sets data-theme="dark" on <html>, stores
    localStorage femtoColorScheme = '"dark"' (JSON), relabels the toggle "Turn off dark mode" and
    shows the moon 🌙; the URL is unchanged (no `#`).
    A second click, back to the OS's own scheme, removes the stored choice and data-theme, so the
    page follows the OS again (Decision 14), and restores the label and icon."""
    s = theme(page)
    page.eq("no data-theme before any choice", s["theme"], None)
    page.eq("nothing stored", s["stored"], None)
    page.expect("the toggle and its icon exist", s["label"] is not None and s["icon"], **s)
    wait_label(page, "Turn on dark mode")
    toggle_and_expect(page, "dark", "Turn off dark mode")
    toggle_and_expect(page, None, "Turn on dark mode")


@check("theme-toggle-dark-os", "/docs", media="dark")
def theme_toggle_dark_os(page):
    """With a dark OS scheme and nothing stored: no data-theme, and the toggle already reads "Turn
    off dark mode" with the moon 🌙 (the page follows the OS). A click stores '"light"' (the
    opposite of the current scheme) and sets data-theme="light"; the next click, back to the OS's
    dark, removes the stored choice and data-theme, and the toggle reads "Turn off dark mode"."""
    s = theme(page)
    page.eq("no data-theme before any choice", s["theme"], None)
    wait_label(page, "Turn off dark mode")
    toggle_and_expect(page, "light", "Turn on dark mode")
    toggle_and_expect(page, None, "Turn off dark mode")


@check("theme-toggle-keyboard", ("/", "/docs#typography"))
def theme_toggle_keyboard(page):
    """The header toggle (a <button>) works from the keyboard as from the pointer: focused, Enter
    sets data-theme="dark", stores '"dark"' and relabels it "Turn off dark mode" with the moon 🌙, with
    no navigation (URL unchanged, the document kept: a marker set on window survives); Enter again,
    back to the OS's light, removes the stored choice and data-theme the same way."""
    page.js("window.__bhMarker = 'kept'")
    url = page.url()
    for want, label in (("dark", "Turn off dark mode"), (None, "Turn on dark mode")):
        page.expect("the toggle takes focus", page.focus(TOGGLE))
        page.key("ENTER")
        expect_scheme(page, "Enter", want)
        wait_label(page, label)
        page.eq("Enter: the document is kept (no reload)", page.js("return window.__bhMarker || null"), "kept")
        page.url_kept("Enter: URL unchanged", url)


BLOCK_SCHEME = "getComputedStyle(document.querySelector('main > section.proof > div[data-femto-demo]').shadowRoot.firstElementChild).colorScheme"
THEAD = "(() => { const h = S.querySelector('div.overflow-auto > table > thead[data-theme]'); return h && h.getAttribute('data-theme'); })()"


@check("theme-os-live", ("/", "/docs#table"),
       safari_skip="the OS scheme changes while the page is open, which Safari cannot emulate; the harness never "
                   "changes macOS's appearance itself")
def theme_os_live(page):
    """With nothing stored, the page follows a live change of the OS scheme (prefers-color-scheme
    switched while the page is open, as the Remix site's PageContext followed it): at dark the
    header toggle reads "Turn off dark mode" with the moon 🌙, the homepage's femto off and on block
    takes the dark color-scheme and Table's inverse thead reads "light"; back at light all three
    return.
    No data-theme is ever written on <html>."""
    wait_label(page, "Turn on dark mode")
    for media, label, thead in (("dark", "Turn off dark mode", "light"), ("light", "Turn on dark mode", "dark")):
        page.sess.set_media(media)
        wait_label(page, label)
        if page.route == "/":
            page.wait(f"OS {media}: the homepage's femto block reads {media}", f"{BLOCK_SCHEME} === '{media}'", 1.5,
                      got=page.js(f"return {BLOCK_SCHEME}"))
        else:
            page.wait(f"OS {media}: the inverse thead reads {thead}", f"{THEAD} === '{thead}'", 1.5)
        page.eq(f"OS {media}: no data-theme written", page.js("return document.documentElement.getAttribute('data-theme')"), None)
        page.eq(f"OS {media}: nothing stored", page.js(f"return localStorage.getItem('{KEY}')"), None)


@check("theme-stored-dark", ("/", "/docs#button"), storage={KEY: '"dark"'})
def theme_stored_dark(page):
    """A stored choice wins over the OS: with femtoColorScheme = '"dark"' stored and a light OS,
    the loaded page has data-theme="dark" on <html> and the toggle reads "Turn off dark mode" with
    the moon 🌙."""
    page.eq("data-theme is the stored dark", theme(page)["theme"], "dark")
    wait_label(page, "Turn off dark mode")


@check("theme-stored-light", "/docs#button", media="dark", storage={KEY: '"light"'})
def theme_stored_light(page):
    """With femtoColorScheme = '"light"' stored and a dark OS, the page has data-theme="light" and
    the toggle reads "Turn on dark mode" without the moon 🌙; a click, to the OS's own dark, removes
    the stored choice and data-theme, and the toggle reads "Turn off dark mode" with the moon."""
    page.eq("data-theme is the stored light", theme(page)["theme"], "light")
    wait_label(page, "Turn on dark mode")
    toggle_and_expect(page, None, "Turn off dark mode")


@check("theme-stored-invalid", "/docs#table", media="dark", storage={KEY: '"blue"'})
def theme_stored_invalid(page):
    """With a dark OS and femtoColorScheme = '"blue"' stored (valid JSON, but neither "light" nor
    "dark", a value the site never writes), the stored item is left as it is, <html> has no
    data-theme, and the page follows the OS: the toggle reads "Turn off dark mode" with the moon 🌙, and
    Table's inverse thead reads data-theme="light". A click stores '"light"' and sets
    data-theme="light"."""
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


# The theme-color metas: each one's content and media, and whether its media matches now.
THEME_COLORS = """return [...document.querySelectorAll('head > meta[name="theme-color"]')]
  .map(m => [m.content, m.media, matchMedia(m.media || 'all').matches]);"""
LIGHT_BAR, DARK_BAR = "#fff", "rgb(19, 22.5, 30.5)"   # femto's --femto-light-background-color and --femto-dark-background-color


def expect_bar(page, label, content, media):
    """Exactly one theme-color meta applies, the one with `content`, and the two have `media`."""
    page.wait(f"{label}: the browser bar takes {content}",
              "(() => { const m = [...document.querySelectorAll('head > meta[name=\"theme-color\"]')]"
              ".filter(x => matchMedia(x.media || 'all').matches); return m.length === 1 && m[0].content === arguments[0]; })()",
              1, args=(content,), got=page.js(THEME_COLORS))
    page.eq(f"{label}: the metas' media", [m[1] for m in page.js(THEME_COLORS)], media)


@check("theme-color-meta", ("/", "/docs#table"), storage={KEY: '"dark"'})
def theme_color_meta(page):
    """The two theme-color metas give the browser's bar femto's background: #fff with
    media (prefers-color-scheme: light) and rgb(19, 22.5, 30.5) with (prefers-color-scheme: dark).
    A stored choice applies its own scheme's meta whatever the OS: with dark stored and a light OS,
    the dark meta's media is "all" and the light one's "not all". A click on the header toggle, to
    the OS's own light, removes the choice and gives both their prefers-color-scheme media back, and
    the light meta applies under the light OS; a second click stores dark again. Then, in another
    tab, so the storage event reaches this one: storing light there swaps the two ("all" for the
    light meta), and removing the stored item gives both their prefers-color-scheme media back."""
    os_media = ["(prefers-color-scheme: light)", "(prefers-color-scheme: dark)"]
    page.eq("two theme-color metas, light then dark", [m[0] for m in page.js(THEME_COLORS)], [LIGHT_BAR, DARK_BAR])
    expect_bar(page, "stored dark, light OS", DARK_BAR, ["not all", "all"])
    page.click(TOGGLE)
    page.wait("the toggle to the OS's light removes the choice", "localStorage.getItem(arguments[0]) === null", 2, args=(KEY,))
    expect_bar(page, "nothing stored, light OS", LIGHT_BAR, os_media)
    page.click(TOGGLE)
    page.wait("the toggle stores dark", "localStorage.getItem(arguments[0]) === '\"dark\"'", 2, args=(KEY,))
    expect_bar(page, "stored dark again", DARK_BAR, ["not all", "all"])
    a = page.driver.current_window_handle
    b = page.new_tab("/")
    page.js(f"localStorage.setItem('{KEY}', '\"light\"')")
    page.switch(a)
    expect_bar(page, "light stored in another tab", LIGHT_BAR, ["all", "not all"])
    page.switch(b)
    page.js(f"localStorage.removeItem('{KEY}')")
    page.switch(a)
    expect_bar(page, "removed in another tab, light OS", LIGHT_BAR, os_media)


@check("theme-cross-tab", "/docs#typography")
def theme_cross_tab(page):
    """Two tabs of the same browser: a toggle click in tab A (on Typography) reaches tab B (on
    /) without a reload: B gets data-theme="dark" and its toggle reads "Turn off dark mode". A
    second click in A, back to the OS's light, removes the stored choice, which removes data-theme
    in B, whose toggle then follows the OS again ("Turn on dark mode"). A light choice stored in A
    (localStorage.setItem) makes B light, and removing it (localStorage.removeItem) removes
    data-theme in B again."""
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
    page.wait("tab A follows the OS again", "!document.documentElement.hasAttribute('data-theme')", 2)
    page.eq("tab A: nothing stored", page.js(f"return localStorage.getItem('{KEY}')"), None)
    page.switch(b)
    page.wait("tab B drops data-theme when the choice is removed",
              "!document.documentElement.hasAttribute('data-theme')", 3)
    wait_label(page, "Turn on dark mode")
    page.switch(a)
    page.js(f"localStorage.setItem('{KEY}', '\"light\"')")
    page.switch(b)
    page.wait("tab B follows a light choice stored in A", "document.documentElement.getAttribute('data-theme') === 'light'", 3)
    page.switch(a)
    page.js(f"localStorage.removeItem('{KEY}')")
    page.switch(b)
    page.wait("tab B drops data-theme when the choice is removed in A",
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


@check("color-scheme-flash", ("/", "/docs"), storage={KEY: '"dark"'}, preload=FLASH_PRELOAD)
def color_scheme_flash(page):
    """With femtoColorScheme = '"dark"' stored, <html> carries data-theme="dark" before anything can
    paint: observed from a script that runs before the page's own, the attribute first appears
    while the head is parsed (no <body> yet: a parser-blocking head script, Decision 14), before the
    first paint (first-paint in Chrome, first-contentful-paint in Firefox), and the first animation
    frame already sees it."""
    # Chrome sometimes records its paint entries 50 to 300 ms after the readiness hook returns
    # (probes on 2026-10-31: 2 of 12 loads, never later than 2 s), so wait for one.
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


# A sticky bar's state: its class attribute, its top in the viewport, its computed position and
# its bottom border (style, width, color). header-fixed and breadcrumb-sticky read it.
BAR = """
const n = document.querySelector(arguments[0]), cs = getComputedStyle(n);
return {cls: n.getAttribute("class"), top: n.getBoundingClientRect().top, y: scrollY, position: cs.position,
        stickyTop: parseFloat(cs.top), border: [cs.borderBottomStyle, cs.borderBottomWidth, cs.borderBottomColor]};
"""


def expect_border(page, label, bar):
    """The bar's bottom border is drawn: solid, at least 1 px wide, and not fully transparent."""
    style, width, color = bar["border"]
    clear = color == "transparent" or color.replace(" ", "").endswith(",0)")
    page.expect(f"{label}: its bottom border is drawn", style == "solid" and float(width[:-2]) >= 1 and not clear, **bar)


@check("header-fixed", "/docs#modal")
def header_fixed(page):
    """On a docs page (1300 px) the header (`body > header`, with no class: docs.css makes it sticky
    from lg up) is sticky at top 0: at the top of the page (scrolled there first: the one page loads
    #modal far down) and scrolled to 21, 600, 0 and 300 its top is 0 (within 0.5 px), so it stays in
    view. Its bottom border is drawn (solid, at least 1 px, not transparent; femto's muted border
    color) and the same at every position, and it never gets a class attribute: no script watches
    the scroll."""
    header = "body > header"
    page.scroll_to(0)
    first = page.js(BAR, header)
    page.eq("no class, position sticky at top 0", [first["cls"], first["position"], first["stickyTop"]], [None, "sticky", 0])
    expect_border(page, "at the top", first)
    for y in (21, 600, 0, 300):
        page.scroll_to(y)
        page.sleep(0.2)
        bar = page.js(BAR, header)
        page.expect(f"scrollY {y}: its top is 0", abs(bar["top"]) <= 0.5, **bar)
        page.eq(f"scrollY {y}: still no class, and the same bottom border", [bar["cls"], bar["border"]], [None, first["border"]])


@check("header-landing", "/")
def header_landing(page):
    """On a landing page the header is never fixed: `body > header` has no class attribute, at the
    top and after scrolling 600 px, and it scrolls away with the page (its top then at -600 px,
    within 0.5 px)."""
    page.eq("no class at the top", page.js("return document.querySelector('body > header').getAttribute('class')"), None)
    page.scroll_to(600)
    page.sleep(0.3)
    page.eq("no class after scrolling", page.js("return document.querySelector('body > header').getAttribute('class')"), None)
    top = page.js("return document.querySelector('body > header').getBoundingClientRect().top")
    page.expect("it scrolled away with the page", abs(top + 600) <= 0.5, top=top)


# How wide the page is laid out: <html>'s scrollWidth and clientWidth, and the first elements whose
# right edge passes the viewport outside any box that scrolls or clips sideways (a code block's
# <pre>, a table's div.overflow-auto), to name the culprit when the check fails.
REFLOW = """
const root = document.documentElement, wide = [];
// An element's parent, through a shadow root to its host.
const up = (el) => el.parentElement ?? el.getRootNode().host ?? null;
const clipped = (el) => { for (let p = up(el); p && p !== root && p !== document.body; p = up(p))
  if (getComputedStyle(p).overflowX !== "visible") return true; return false; };
const walk = (scope) => {
  for (const el of scope.querySelectorAll("*")) {
    const r = el.getBoundingClientRect();
    if (r.width && r.right > root.clientWidth + 0.01 && !clipped(el) && wide.length < 8) {
      let named = el; while (named && !named.matches("[aria-label]")) named = up(named);
      wide.push(`${el.localName}${el.id ? "#" + el.id : ""} "${el.textContent.trim().slice(0, 20)}" in "${named?.getAttribute("aria-label") ?? ""}"`
        + `${el.getRootNode() !== document ? " (in a shadow root)" : ""}, right ${Math.round(r.right)}`);
    }
    if (el.shadowRoot) walk(el.shadowRoot);
  }
};
walk(document.body);
return {scrollWidth: root.scrollWidth, clientWidth: root.clientWidth, innerWidth, wide};
"""


# What prints: <html>'s color-scheme, the /examples hosts' (inner and nested) color-schemes and
# data-theme, and which of the screen-only controls still have a box. The header's links and toggle
# are its nav's last list: the logo, in the first, prints.
SCREEN_ONLY = ["body > header nav ul:last-of-type", "button[data-copy-link]", "main > aside#documentation-menu",
               "main > nav[aria-label=breadcrumb]",
               "article[data-version-picker] > header", "#content section > p:has(+ article[data-version-picker])",
               "[data-picker-options] fieldset", "button[data-scheme-switcher]", "section[data-grid-example] > .grid > button",
               "input[name=toggle-font-size-in-rem]", "button[data-modal-open]", "p[data-palette-help]",
               "body > main > .hero .grid.ctas", "button[data-demo-pause]", "body > main > .proof > .toolbar",
               "p[data-examples-theme]", "button[data-copy-page]"]
# What /docs prints in its code and colors: the distinct backgrounds of the examples' code footers
# and of every code block's <pre>, each with femto's light token for it as this browser computes it
# (a probe painted in the token itself: Chrome rounds femto's rgb(251, 251.5, 252.25) to whole
# channels), and the print-color-adjust of a Colors swatch and a Themes dot.
PRINTED_DOCS = """
const bgs = sel => [...new Set([...document.querySelectorAll(sel)].map(e => getComputedStyle(e).backgroundColor))];
const token = name => { const e = document.createElement('div'); e.style.backgroundColor = `var(${name})`; document.body.append(e);
  const c = getComputedStyle(e).backgroundColor; e.remove(); return c; };
const adjust = sel => { const e = document.querySelector(sel); return e ? getComputedStyle(e).printColorAdjust : null; };
return {footers: bgs('#content article > footer.code'), pres: bgs('#content .code > pre'),
        swatch: adjust('.color-families .family .shades > button'),
        dot: adjust('#content > section:has(> hgroup > h1[id=themes]) td > span[class^="femto-background-"]'),
        want: {footers: [token('--femto-light-card-sectioning-background-color')], pres: [token('--femto-light-code-background-color')]}};
"""


def emulate_print(page, scheme, label, screen):
    """Under Chrome's print media, with prefers-color-scheme at scheme, asserts that <html> is light
    and the screen-only controls have no box, and on /docs that every code block prints in femto's
    light code colors and the palette and the Themes dots keep their colors; returns what PRINTED
    read. The emulation is put back to the screen after, with prefers-color-scheme at screen, the
    check's own."""
    def features(value):
        return [{"name": "prefers-color-scheme", "value": value}, {"name": "prefers-reduced-motion", "value": "no-preference"}]
    page.driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"media": "print", "features": features(scheme)})
    try:
        got = None
        end = time.monotonic() + 1.5
        while time.monotonic() < end:
            got = page.js(PRINTED, SCREEN_ONLY)
            if got["html"] == "light" and not got["shown"] and (page.route != "/examples" or got["hosts"] == ["light:null"]):
                break
            time.sleep(0.05)
        page.eq(f"print, {label}: <html> is light and the screen-only controls have no box",
                {"html": got["html"], "shown": got["shown"]}, {"html": "light", "shown": []}, present=got["present"])
        if page.route.startswith("/docs"):
            d = page.js(PRINTED_DOCS)
            page.eq(f"print, {label}: every code block's <pre> has femto's light code background and every code footer femto's "
                    "light card sectioning color, and the palette and the Themes dots keep their colors",
                    {k: d[k] for k in ("footers", "pres", "swatch", "dot")}, {**d["want"], "swatch": "exact", "dot": "exact"})
        return got
    finally:
        page.driver.execute_cdp_cmd("Emulation.setEmulatedMedia", {"media": "", "features": features(screen)})
PRINTED = """
const hosts = [...document.querySelectorAll('div[data-example]')].map(f => f.shadowRoot.firstElementChild);
const nested = hosts.flatMap(h => [...h.shadowRoot.querySelectorAll('*')].filter(e => e.shadowRoot));
return {html: getComputedStyle(document.documentElement).colorScheme,
        hosts: [...new Set([...hosts, ...nested].map(h => getComputedStyle(h).colorScheme + ':' + h.getAttribute('data-theme')))],
        shown: arguments[0].filter(sel => [...document.querySelectorAll(sel)].some(e => e.getClientRects().length > 0)),
        present: arguments[0].filter(sel => document.querySelector(sel))};
"""
# Records each change of the /examples hosts' data-theme (the value it had before) and the print events.
PRINT_LOG = """
window.__bhPrint = [];
const hosts = [...document.querySelectorAll('div[data-example]')].map(f => f.shadowRoot.firstElementChild);
new MutationObserver(rs => { for (const r of rs) __bhPrint.push(['was', r.oldValue, r.target.getAttribute('data-theme')]); })
  .observe(hosts[0], {attributes: true, attributeFilter: ['data-theme'], attributeOldValue: true});
for (const e of ['beforeprint', 'afterprint']) addEventListener(e, () => __bhPrint.push([e]));
"""


@check("print-light", ("/", "/docs#colors", "/examples"), storage={KEY: '"dark"'},
       safari_skip="the harness prints through WebDriver's Print command and Chrome's media emulation")
def print_light(page):
    """A page prints in the light scheme, whatever the stored choice (dark here), and without the
    controls that only work on screen. Under print media (Chrome: CDP Emulation.setEmulatedMedia;
    Firefox has no WebDriver way to emulate it, so only the print below runs there) <html>'s
    color-scheme is light, and the header's links and toggle (its nav's last list; the logo prints),
    the copy buttons, /docs' side menu and breadcrumb,
    the Theme picker's swatches with their sentence and its option switches, the Color schemes
    switcher, Grid's Add and Remove column, Typography's rem switch, the Modal demo's opener and the
    Colors palette's help, the homepage's call-to-action buttons, its
    typing demo's Pause and its femto switch and swatches, and /examples' theme select and Copy as
    page buttons have no box. On /docs every code block's <pre> prints in femto's light code
    background (--femto-light-code-background-color) and every example's code footer in femto's
    light card sectioning color, whatever the scheme on screen, and the Colors swatches and the
    Themes table's dots have print-color-adjust: exact. Chrome checks this twice, with the
    OS light and with the OS dark. On /examples every inner and nested host is light with no
    data-theme. And on /examples a real print (WebDriver Print) takes data-theme="dark" off the
    hosts between beforeprint and afterprint, so the mockups print light too, and gives it back
    after."""
    if page.browser == "chrome":
        for scheme in ("light", "dark"):
            got = emulate_print(page, scheme, f"OS {scheme}", "light")
            if page.route == "/examples":
                page.eq(f"print, OS {scheme}: every example's host is light, with no data-theme", got["hosts"], ["light:null"])
            page.wait(f"after print, OS {scheme}: <html> is dark again",
                      "getComputedStyle(document.documentElement).colorScheme === 'dark'", 1.5)
    else:
        page.note(f"{page.browser} cannot emulate print media over WebDriver: only the real print is checked")
    if page.route != "/examples":
        return
    page.wait("on screen the hosts take the stored dark", "document.querySelector('div[data-example]').shadowRoot"
              ".firstElementChild.getAttribute('data-theme') === 'dark'", 1.5)
    page.js(PRINT_LOG)
    page.driver.print_page()
    page.wait("after the print, the hosts are dark again", "window.__bhPrint.length >= 4 && document.querySelector('div[data-example]')"
              ".shadowRoot.firstElementChild.getAttribute('data-theme') === 'dark'", 3, got=page.js("return window.__bhPrint"))
    log = page.js("return window.__bhPrint")
    events = [x[0] for x in log if x[0] != "was"]
    changes = [x[1] for x in log if x[0] == "was"]
    page.eq("beforeprint, then afterprint", events, ["beforeprint", "afterprint"], log=log)
    page.eq("data-theme taken off for the print, then given back", changes, ["dark", None], log=log)


@check("print-light-os-dark", "/docs#colors", media="dark",
       safari_skip="the harness prints through Chrome's media emulation")
def print_light_os_dark(page):
    """With nothing stored and a dark OS, /docs still prints light: under Chrome's print media
    (Firefox has no WebDriver way to emulate it, and records a note) <html> is light, the
    screen-only controls have no box, every code block's <pre> has femto's light code background
    and every example's code footer femto's light card sectioning color, and the Colors swatches
    and the Themes table's dots have print-color-adjust: exact. Back on screen <html> is dark, as
    the OS is."""
    if page.browser != "chrome":
        page.note(f"{page.browser} cannot emulate print media over WebDriver")
        return
    page.eq("on screen, nothing is stored", page.js(f"return localStorage.getItem('{KEY}')"), None)
    emulate_print(page, "dark", "OS dark, nothing stored", "dark")
    page.wait("after print: <html> is dark again", "getComputedStyle(document.documentElement).colorScheme === 'dark'", 1.5)


@check("reflow-320", ("/", "/docs", "/examples", "/does-not-exist"), width=320, height=640)
def reflow_320(page):
    """At 320 px wide (WCAG 1.4.10's reflow width: 1280 px at 400% zoom) no page is wider than the
    viewport: <html>'s scrollWidth equals its clientWidth on the homepage, /docs, /examples and the
    404 page, so nothing needs a sideways scroll, which <html>'s overflow-x: hidden would hide. And
    no element ends past the viewport's right edge, open shadow roots included (the /examples
    mockups), unless a box around it scrolls or clips it: code blocks and tables scroll inside their
    own boxes, which this allows. No page's body clips sideways. A behavior check rather than a 320 px
    a11y width: axe has no rule for it, and one load per page and browser measures it."""
    r = page.js(REFLOW)
    page.eq("<html>'s scrollWidth is its clientWidth", r["scrollWidth"], r["clientWidth"], innerWidth=r["innerWidth"], wide=r["wide"])
    page.eq("no element ends past the viewport outside a box that scrolls or clips it", r["wide"], [])


COPY_STATE = """
const a = arguments[0];
const i = a.querySelector(":scope > span[role=img]"), glyph = i && i.textContent;
return {tooltip: a.getAttribute("data-tooltip"), check: glyph === "\\u2713", clipboard: glyph === "\\u29C9",
        label: i && i.getAttribute("aria-label"), focused: document.activeElement === a, copied: window.__bhCopied};
"""
COPY_LABEL = "Copy code"   # a code block's copy icon's aria-label (Decision 18), which names its button
COPY_TOOLTIP = "Copy code"   # its data-tooltip, the same words, so a voice-control user can say what they see

# Records the copy link's tooltip and icon on every change, and the click, with performance.now()
# times, so the check measures the 1 s revert in the page.
COPY_TIMELINE = """
const a = arguments[0];
window.__bhCopy = [];
const t = () => Math.round(performance.now());
const glyph = () => a.querySelector(":scope > span[role=img]")?.textContent;
const state = () => [a.getAttribute("data-tooltip"), glyph() === "\\u2713" ? "check" : glyph() === "\\u29C9" ? "clipboard" : "none"];
let last = JSON.stringify(state());
new MutationObserver(() => { const s = state(), j = JSON.stringify(s); if (j !== last) { __bhCopy.push([t(), ...s]); last = j; } })
  .observe(a, {attributes: true, childList: true, subtree: true});
a.addEventListener("click", () => __bhCopy.push([t(), "click"]), true);
"""


@check("copy-button", ("/docs", "/docs#modal"))
def copy_button(page):
    """Each code block's copy control of the route's content (`button[data-copy-link]`;
    data-tooltip "Copy code", the words of its name, its icon a `span[role=img]` holding
    ⧉ that names it, Decision 18): a click copies exactly that block's code text (its `pre code`
    textContent; the
    copy is recorded in the page, the machine's clipboard is never touched) and leaves the URL as it
    was. Timed in the page: within 100 ms of the click the tooltip reads "Copied" with the animated
    check ✓, and 1 s later (900 to 1500 ms) the button's own tooltip, "Copy code", with ⧉ again,
    with no other step; the control then does not hold focus (a pointer click blurs it). The
    button's computed name (the
    browser's, WebDriver Get Computed Label) is its icon's label, "Copy code", and nothing else:
    before the click, while the check shows and after the revert (neither tooltip's text joins it). A
    second block's control copies its own code."""
    page.js(COPY_SPY)
    links = page.find_all("button[data-copy-link]")
    page.expect("at least two copy links", len(links) >= 2, count=len(links))
    for n, link in enumerate((links[0], links[-1]), 1):
        code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", link)
        s = page.js(COPY_STATE, link)
        page.eq(f"link {n}: tooltip {COPY_TOOLTIP!r} before", s["tooltip"], COPY_TOOLTIP)
        page.expect(f"link {n}: clipboard icon before", s["clipboard"] and not s["check"], **s)
        page.eq(f"link {n}: the icon's label", s["label"], COPY_LABEL, **s)
        expect_name(page, f"link {n}: the button's computed name is the icon's label before", link, COPY_LABEL)
        url = page.url()
        page.js("window.__bhCopied.length = 0")
        page.js(COPY_TIMELINE, link)
        page.click(link)
        page.wait(f"link {n}: copied", "window.__bhCopied.length > 0", 1)
        s = page.js(COPY_STATE, link)
        page.expect(f"link {n}: the check shows", s["check"], **s)
        expect_name(page, f"link {n}: the check keeps the button's computed name", link, COPY_LABEL)
        page.expect(f"link {n}: the check still shows (the name was read while it did)", page.js(COPY_STATE, link)["check"])
        page.eq(f"link {n}: copied once", len(s["copied"]), 1, copied=s["copied"])
        page.eq(f"link {n}: copied the block's code", s["copied"][0]["text"], code, via=s["copied"][0]["via"])
        page.url_kept(f"link {n}: URL unchanged", url)
        page.wait(f"link {n}: reverted", "arguments[0].getAttribute('data-tooltip') === arguments[1] && "
                  "arguments[0].querySelector(':scope > span[role=img]')?.textContent === '\\u29C9' && window.__bhCopy.length >= 3", 2.5,
                  args=(link, COPY_TOOLTIP))
        tl = page.js("return window.__bhCopy")
        page.eq(f"link {n}: the steps", [x[1:] for x in tl], [["click"], ["Copied", "check"], [COPY_TOOLTIP, "clipboard"]],
                timeline=tl)
        page.expect(f"link {n}: 'Copied' within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
        page.expect(f"link {n}: reverts 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
        page.eq(f"link {n}: blurred after reverting", page.js(COPY_STATE, link)["focused"], False)
        expect_name(page, f"link {n}: the button's computed name is the icon's label after", link, COPY_LABEL)


@check("copy-button-repeat", "/docs#modal")
def copy_button_repeat(page):
    """Repeated use of a copy control (one revert timer per button, restarted by every copy): two
    clicks 500 ms apart copy the block's code twice, and "Copied" reverts to the button's own
    tooltip, "Copy code", with ⧉ once, 1 s after the LAST click (900 to 1200 ms), with no other
    step; the control then does not hold focus."""
    page.js(COPY_SPY)
    link = page.find_all("button[data-copy-link]")[0]
    code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", link)
    page.js(COPY_TIMELINE, link)
    page.click(link)
    page.sleep(0.5)
    page.click(link)
    page.wait("reverted", "arguments[0].getAttribute('data-tooltip') === arguments[1] && arguments[0].querySelector(':scope > span[role=img]')?.textContent === '\\u29C9'",
              3, args=(link, COPY_TOOLTIP))
    page.sleep(0.8)   # a later, wrong revert or step would show by now
    tl = page.js("return window.__bhCopy")
    copies = page.js("return window.__bhCopied")
    page.eq("two clicks copy twice, the block's code each time", [c["text"] for c in copies], [code, code])
    page.eq("the steps: click, Copied, click, one revert", [x[1:] for x in tl],
            [["click"], ["Copied", "check"], ["click"], [COPY_TOOLTIP, "clipboard"]], timeline=tl)
    page.expect("it reverts 1 s after the last click", 900 <= tl[3][0] - tl[2][0] <= 1200, ms_after_last=tl[3][0] - tl[2][0],
                timeline=tl)
    page.eq("blurred after reverting", page.js(COPY_STATE, link)["focused"], False)


# A clipboard that refuses every write, as the browser's does when the page lacks permission: each
# call is recorded with its text, and its promise rejects. With arguments[0] true there is no
# navigator.clipboard at all, as on an insecure origin (an http LAN preview).
COPY_REFUSED = r"""
window.__bhRefused = window.__bhRefused || [];
if (arguments[0]) Object.defineProperty(navigator, "clipboard", {value: undefined, configurable: true});
else navigator.clipboard.writeText = (t) => { __bhRefused.push(String(t)); return Promise.reject(new DOMException("refused", "NotAllowedError")); };
return navigator.clipboard === undefined;
"""


@check("copy-failed", "/docs#modal")
def copy_failed(page):
    """A copy that fails says so (site.js, Copy buttons): with a clipboard whose writeText rejects,
    a click on the first copy button tries to write exactly its block's code, and within 100 ms
    the tooltip reads "Copy failed" with the copy icon ⧉ kept (no check ✓) and the status line
    (`body > p.visually-hidden[role=status]`) says "Copy failed"; 1 s later (900 to 1500 ms) the
    tooltip is the button's own "Copy code" again, with no other step. The button's computed name
    stays "Copy code". With no navigator.clipboard at all (an insecure origin), a second click says
    "Copy failed" again, and the status line, repeating its last message, says it with a no-break
    space after it (U+00A0)."""
    link = page.find_all("button[data-copy-link]")[0]
    code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", link)
    page.eq("the clipboard refuses", page.js(COPY_REFUSED, False), False)
    page.js(COPY_TIMELINE, link)
    page.click(link)
    page.wait("the tooltip reads Copy failed", "arguments[0].getAttribute('data-tooltip') === 'Copy failed'", 1, args=(link,))
    page.eq("it tried to write the block's code, once", page.js("return window.__bhRefused"), [code])
    s = page.js(COPY_STATE, link)
    page.expect("the copy icon stays, with no check", s["clipboard"] and not s["check"], **s)
    expect_name(page, "the button's computed name is still the icon's label", link, COPY_LABEL)
    page.eq("the status line says Copy failed", page.js(STATUS), "Copy failed")
    page.wait("it reverts", "arguments[0].getAttribute('data-tooltip') === arguments[1] && window.__bhCopy.length >= 3", 2.5,
              args=(link, COPY_TOOLTIP))
    tl = page.js("return window.__bhCopy")
    page.eq("the steps: click, Copy failed, its own tooltip", [x[1:] for x in tl],
            [["click"], ["Copy failed", "clipboard"], [COPY_TOOLTIP, "clipboard"]], timeline=tl)
    page.expect("'Copy failed' within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
    page.expect("reverts 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
    page.wait("the status line is empty again", "document.querySelector('body > p.visually-hidden[role=status]').textContent === ''", 1)
    page.eq("no navigator.clipboard", page.js(COPY_REFUSED, True), True)
    page.click(link)
    page.wait("no clipboard: the tooltip reads Copy failed", "arguments[0].getAttribute('data-tooltip') === 'Copy failed'", 1, args=(link,))
    page.expect("no clipboard: the copy icon stays", page.js(COPY_STATE, link)["clipboard"])
    page.eq("no clipboard: the status line repeats Copy failed, with a no-break space", page.js(STATUS), "Copy failed\u00A0")


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
# Modal's demo: its article, and in it the "Open modal" button, found by the modal helper's hook.
DEMO_ARTICLE = "#content article[aria-label='Modal demo']"
DEMO_OPENER = "button[data-modal-open=modal-demo]"


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
    """The modal helper on <html> (the Remix site's ModalContext), opened by Modal's "Open modal"
    button, timed in the page: within 100 ms of the click <html> has `modal-is-open
    modal-is-opening`, and 400 ms later (350 to 700) only `modal-is-open`; Escape then gives
    `modal-is-open modal-is-closing` within 100 ms, and 400 ms later (350 to 700) no modal class at
    all. No other class steps happen. Escape again, with nothing open, changes nothing."""
    page.eq("no modal class before", page.js(HTML_CLASSES), "")
    page.js(MODAL_TIMELINE)
    page.click(DEMO_OPENER)
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


@check("modal-scrollbar-width", "/docs#modal",
       safari_skip="the harness forces a classic scrollbar with a preload script (Chrome) or a pref (Firefox); Safari's "
                   "WebDriver has neither, and its scrollbars are the OS's, which the harness never changes")
def modal_scrollbar_width(page):
    """With a classic (space-taking) scrollbar, which the harness forces (Chrome: a
    ::-webkit-scrollbar sheet adopted before the page loads; Firefox: ui.useOverlayScrollbars 0):
    while the modal is open, <html>'s style sets --femto-scrollbar-width to the scrollbar's width
    (innerWidth minus <html>'s clientWidth, measured before opening), and the page behind does not
    move sideways (the demo article keeps its left edge). Once closed, the property is gone."""
    page.with_classic_scrollbars()
    sb = page.js("return innerWidth - document.documentElement.clientWidth")
    page.expect("the forced scrollbar takes space", sb > 0, scrollbar=sb)
    left = page.js("return document.querySelector(arguments[0]).getBoundingClientRect().left", DEMO_ARTICLE)
    page.click(DEMO_OPENER)
    page.wait("open", "document.documentElement.classList.contains('modal-is-open')", 0.5)
    v = page.js("return document.documentElement.style.getPropertyValue('--femto-scrollbar-width').trim()")
    page.eq("--femto-scrollbar-width is the scrollbar width", v, f"{sb}px")
    page.eq("the page behind does not move", page.js(
        "return document.querySelector(arguments[0]).getBoundingClientRect().left", DEMO_ARTICLE), left)
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

RED_500 = ".color-families .family > .shades > button.femto-background-red-500"


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


@check("modal-two-dialogs", "/docs#modal")
def modal_two_dialogs(page):
    """One modal helper per dialog, one holder of <html>'s classes (PLAN.md Rules; site.js
    createModal), with the two dialogs of the one page and a classic scrollbar (as
    modal-scrollbar-width forces it; Safari, which has no preload script, keeps its own, whose width
    may be 0). "Open modal" opens Modal's demo dialog alone, and once it is open (`modal-is-open`
    alone) <html>'s --femto-scrollbar-width is the scrollbar's width. The demo is a true modal
    (showModal()): it matches :modal, focus is inside it, and the page behind is
    inert, so the Colors section's red 500 shade button cannot take focus (focus stays in the demo)
    and no Enter on it can open the color modal, as it could while the demo was not modal. A script still can: a
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
    page.click(DEMO_OPENER)
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


# The side menu's nav: its computed max-height, its top, --femto-spacing in px (read from a hidden
# probe inside it), and <body>'s computed min-height.
MAX_HEIGHT = """
const n = document.querySelector("#documentation-menu nav"), probe = document.createElement("div");
probe.style.cssText = "position: absolute; visibility: hidden; width: var(--femto-spacing)";
n.append(probe);
const spacing = probe.getBoundingClientRect().width;
probe.remove();
return {maxHeight: getComputedStyle(n).maxHeight, top: n.getBoundingClientRect().top, spacing, innerHeight, innerWidth,
        y: scrollY, body: getComputedStyle(document.body).minHeight};
"""


def expect_max_height(page, label):
    m = page.js(MAX_HEIGHT)
    if m["innerWidth"] >= 1024:
        v = float(m["maxHeight"][:-2]) if m["maxHeight"].endswith("px") else None
        page.expect(f"{label}: the nav ends a femto spacing above the viewport's bottom",
                    v is not None and abs(v - (m["innerHeight"] - m["top"] - m["spacing"])) < 0.5, **m)
    else:
        page.eq(f"{label}: below lg the nav has no max-height (the off-canvas panel bounds it)", m["maxHeight"], "none")
    b = float(m["body"][:-2]) if m["body"].endswith("px") else None
    page.expect(f"{label}: body min-height is innerHeight", b is not None and abs(b - m["innerHeight"]) < 0.5, **m)


@check("side-menu-max-height", ("/docs#grid",), width=375, height=812)
def side_menu_max_height(page):
    """From lg up the side menu's nav, sticky below the header, ends a femto spacing above the
    viewport's bottom: its computed max-height is innerHeight minus its top minus --femto-spacing
    (within 0.5 px; docs.css's calc() on 100dvh) after the viewport grows to 1300 x 900, and after a
    resize to 1300 x 700 while scrolled 500 px down (where the nav is sticky). Below lg, on load at
    375 x 812 and after a resize to 375 x 600, it has none: the off-canvas panel's grid row bounds
    it. Each time <body>'s computed min-height is innerHeight (100dvh) too."""
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
OPENER = "nav[aria-label=breadcrumb] ul li:first-child :is(a, button)"
CLOSE = "#documentation-menu header button:has(> span[role=img][aria-label=Close])"   # named by its icon (Decision 18)
IS_OPEN = "document.querySelector('#documentation-menu').classList.contains('is-open-on-mobile')"


@check("mobile-menu", "/docs#modal", width=375, height=812)
def mobile_menu(page):
    """At 375 px the breadcrumb's "Documentation" control (a button) opens the
    off-canvas menu: a click adds `is-open-on-mobile` to `aside#documentation-menu`, <html> stops
    scrolling (overflow-y hidden) and the URL is unchanged; the menu's own Close control (`header
    button`, named "Close" by its icon) removes the class, scrolling returns and the URL is still
    unchanged."""
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


# Makes focus() ignore its options in this document, as Chrome Android, Samsung Internet and
# Firefox Android ignore its preventScroll option (BCD, api.HTMLElement.focus,
# options_preventScroll_parameter: version_added false; outside Decision 12's target): a page that
# relies on the option to keep its position scrolls here as it would there.
FOCUS_NO_OPTIONS = """
if (!window.__bhFocusNoOptions) {
  const focus = HTMLElement.prototype.focus;
  HTMLElement.prototype.focus = function () { return focus.call(this); };
  window.__bhFocusNoOptions = true;
}
return true;
"""
# Makes focusing the element arguments[0] matches also scroll the page 66 px up one frame later, as
# Safari 27 scrolls to a focused sticky element after the task (p6-behavior-safari-light-2: the
# page 66 px up once Escape had returned focus to the opener): a page that puts its position back
# only within focus()'s own task moves here as it does there. Installed after FOCUS_NO_OPTIONS.
FOCUS_LATE_SCROLL = """
if (!window.__bhFocusLateScroll) {
  const selector = arguments[0], focus = HTMLElement.prototype.focus;
  HTMLElement.prototype.focus = function (...options) {
    const result = focus.apply(this, options);
    if (this.matches(selector)) requestAnimationFrame(() => scrollBy(0, -66));
    return result;
  };
  window.__bhFocusLateScroll = true;
}
return true;
"""
# scrollY once two animation frames have passed (a scroll the focus caused has been applied).
SCROLL_Y = """
const frame = () => new Promise(r => requestAnimationFrame(() => r()));
await frame();
await frame();
return scrollY;
"""


def expect_scroll_kept(page, label, y0):
    """The page is where it was before the menu opened (within 1 px)."""
    y = page.ajs(SCROLL_Y)
    page.expect(label, abs(y - y0) <= 1, scrollY=y, before=y0, moved=y - y0)


@check("mobile-menu-focus", "/docs#modal", width=375, height=812)
def mobile_menu_focus(page):
    """At 375 px the off-canvas menu takes focus and gives it back (criterion 7), and the page keeps
    its scroll position: Enter on the breadcrumb's focused "Documentation" control opens the menu with
    focus inside `aside#documentation-menu`; Escape closes it (no `is-open-on-mobile`, the page
    scrolls again, the URL unchanged), focus returns to the Documentation control, and scrollY is
    within 1 px of where it was before the menu opened. Opened again with a pointer click, focus is
    inside the menu again; Enter on its focused Close control closes it, focus returns to the
    Documentation control, and scrollY is within 1 px of where it was before that opening. Escape
    with the menu closed changes nothing. Then the same again with focus() made to ignore its options
    (FOCUS_NO_OPTIONS), as Chrome Android and Samsung Internet ignore preventScroll: the opener sits in
    the sticky breadcrumb, which Chrome scrolls the page to show when it takes focus, so the
    position must be kept without the option. Then once more with focusing the opener also scrolling
    the page 66 px up a frame later (FOCUS_LATE_SCROLL), as Safari 27 does, so the position must be
    kept after focus()'s task too. That focus stays inside while the menu is open is
    mobile-menu-inert's."""
    url = page.url()
    for prefix in ("", "focus() without options: ", "focus() scrolling after the task: "):
        if prefix:
            page.js(FOCUS_NO_OPTIONS)
        if prefix.startswith("focus() scrolling"):
            page.js(FOCUS_LATE_SCROLL, OPENER)
        page.expect(f"{prefix}the Documentation control takes focus", page.focus(OPENER))
        y0 = page.ajs(SCROLL_Y)
        page.key("ENTER")
        page.wait(f"{prefix}Enter on Documentation opens the menu", IS_OPEN, 1.5)
        page.wait(f"{prefix}opening moves focus into the menu",
                  "document.querySelector('#documentation-menu').contains(document.activeElement)", 1, got=page.js(MOBILE))
        page.key("ESCAPE")
        page.wait(f"{prefix}Escape closes the menu", f"!{IS_OPEN}", 1.5)
        s = page.js(MOBILE)
        page.expect(f"{prefix}Escape: the page scrolls again", s["overflowY"] != "hidden", **s)
        page.url_kept(f"{prefix}Escape: no navigation", url)
        page.wait(f"{prefix}Escape: focus returns to the Documentation control",
                  "document.activeElement === document.querySelector(arguments[0])", 1, args=(OPENER,), got=page.js(MOBILE))
        expect_scroll_kept(page, f"{prefix}Escape: the page keeps its scroll position", y0)
        y0 = page.ajs(SCROLL_Y)
        page.click(OPENER)
        page.wait(f"{prefix}a click on Documentation opens the menu", IS_OPEN, 1)
        page.wait(f"{prefix}clicked open: focus is inside the menu",
                  "document.querySelector('#documentation-menu').contains(document.activeElement)", 1, got=page.js(MOBILE))
        page.sleep(0.5)   # the menu slides in
        page.expect(f"{prefix}the Close control takes focus", page.focus(CLOSE))
        page.key("ENTER")
        page.wait(f"{prefix}Enter on the Close control closes the menu", f"!{IS_OPEN}", 1.5)
        page.wait(f"{prefix}closed: focus returns to the Documentation control",
                  "document.activeElement === document.querySelector(arguments[0])", 1, args=(OPENER,), got=page.js(MOBILE))
        expect_scroll_kept(page, f"{prefix}closed: the page keeps its scroll position", y0)
        page.key("ESCAPE")
        page.sleep(0.3)
        page.eq(f"{prefix}Escape with the menu closed changes nothing", page.js(MOBILE)["open"], False)
        page.url_kept(f"{prefix}and leaves the URL", url)


@check("mobile-menu-link", "/docs#modal", width=375, height=812)
def mobile_menu_link(page):
    """At 375 px, with the off-canvas menu open, following the "Layout" category's "Grid" link (the
    category opened first if it is closed) closes the menu (no `is-open-on-mobile`) and shows Grid.
    The link is a fragment navigation in the same document: the URL becomes /docs#grid with one new
    history entry and Grid's heading on the scroll-padding line (within 2 px); back returns to
    /docs#modal, the same document (a marker set on window survives), with the menu closed."""
    page.js("window.__bhMarker = 'kept'")
    page.click(OPENER)
    page.wait("menu open", IS_OPEN, 1)
    summary = page.js("""return [...document.querySelectorAll('#documentation-menu nav details > summary')]
                         .find(s => s.textContent.trim() === 'Layout')""")
    if not page.js("return arguments[0].parentElement.open", summary):
        page.click(summary)
        page.wait("Layout opens", "arguments[0].parentElement.open", 1, args=(summary,))
    link = "#documentation-menu a[href='#grid']"
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
    """At 375 px the breadcrumb (`nav[aria-label=breadcrumb]`) is sticky at top: -1px. Measured from
    its natural top t (its top at the top of the page, scrolled there first: the one page loads
    #modal far down; more than 21 px), it moves with the page until it reaches the sticky line and
    then stays there: scrolled 400 px down and to ceil(t) + 2 its top is -1, at floor(t) - 1 and
    floor(t) - 20 it is t - scrollY (each within 0.5 px). Its bottom border is drawn (solid, at least
    1 px, not transparent; femto's muted border color) and the same at every position, and its class
    attribute never changes: no script watches for the moment it sticks. Relative to t, so the check
    holds whatever sits above the breadcrumb."""
    crumb = "nav[aria-label=breadcrumb]"
    page.scroll_to(0)
    first = page.js(BAR, crumb)
    t = first["top"] + first["y"]
    page.expect("the breadcrumb starts below the top", t > 21, natural_top=t)
    page.eq("position sticky at top: -1px", [first["position"], first["stickyTop"]], ["sticky", -1])
    expect_border(page, "at the top", first)
    stuck, free, far = math.ceil(t) + 2, math.floor(t) - 1, math.floor(t) - 20
    for y, label in ((400, "stuck"), (free, "just above its natural top"), (stuck, "just past its natural top"),
                     (far, "20 px above its natural top"), (400, "stuck again"), (0, "at the top")):
        page.scroll_to(y)
        page.sleep(0.2)
        bar = page.js(BAR, crumb)
        want = -1 if y > t + 1 else t - bar["y"]
        page.expect(f"scrollY {y} ({label}): its top is {round(want, 2)}", abs(bar["top"] - want) <= 0.5, natural_top=t, **bar)
        page.eq(f"scrollY {y}: the same class and bottom border", [bar["cls"], bar["border"]], [first["cls"], first["border"]])


@check("breadcrumb-chapter", ("/docs", "/docs?theme=jade#theme-picker", "/docs#colors", "/docs#grid", "/docs#table",
                              "/docs#radios", "/docs#modal"), width=375, height=812)
def breadcrumb_chapter(page):
    """The breadcrumb reads "Documentation > <category> > <section>": its second item names the
    route's menu category (Getting started, Customization, Layout, Content, Forms, Components; a
    Theme picker color, the old version-picker color route, is Getting started) and its third and
    last item the route's section, its h1's text (Quick start for /docs), within 1 s of the load (the
    one page's spy sets both for the section a deep link lands on), and its first item is
    "Documentation": a button (type=button) that opens the off-canvas menu
    (aria-controls="documentation-menu"). Below 576 px the button shows its ☰ alone, so the category
    and the section fit beside it: its label is out of sight (a box of 1 px), and the button's
    computed name is still "Documentation". On /docs, at 700 px the label shows again."""
    page.expect("the page has a breadcrumb", page.js("return !!document.querySelector('nav[aria-label=breadcrumb] ul li')"))
    crumbs = """return [...document.querySelectorAll('main > nav[aria-label=breadcrumb] > ul > li')].slice(1).map(li => li.textContent.trim())"""
    want = [CATEGORY[page.route], page.js("return document.getElementById(arguments[0]).textContent.trim()", page.section)]
    page.wait(f"the breadcrumb reads {want[0]} > {want[1]} after Documentation",
              "JSON.stringify([...document.querySelectorAll('main > nav[aria-label=breadcrumb] > ul > li')].slice(1)"
              ".map(li => li.textContent.trim())) === arguments[0]", 1,
              args=(json.dumps(want, separators=(",", ":"), ensure_ascii=False),), got=page.js(crumbs))
    r = page.js("""const n = document.querySelector('nav[aria-label=breadcrumb]');
      const a = n.querySelector('ul li:first-child > :is(a, button)');
      const text = a && [...a.childNodes].filter(c => !(c.nodeType === 1 && c.matches('[role=img]'))).map(c => c.textContent).join('');
      return a && {tag: a.localName, text: text.trim(), href: a.getAttribute('href'), type: a.getAttribute('type'),
                   controls: a.getAttribute('aria-controls')}""")
    page.expect("the first item is a link or a button", r is not None)
    page.eq("the first item is Documentation", r["text"], "Documentation")
    page.eq("a button that opens the menu", [r["tag"], r["type"], r["controls"]], ["button", "button", "documentation-menu"])
    page.eq("below 576 px the button shows ☰ alone, its label out of sight", opener_label(page), [False, True])
    expect_name(page, "the button is still named Documentation", page.el(OPENER), "Documentation")
    if page.route == "/docs":
        page.resize(700, 812)
        page.wait("at 700 px the button shows ☰ and its label", f"JSON.stringify(({OPENER_LABEL})()) === '[true,true]'", 1,
                  got=opener_label(page))


# Whether the breadcrumb's Documentation button shows its label (a box over 1 px, seen) and its ☰.
OPENER_LABEL = """() => { const b = document.querySelector('main > nav[aria-label=breadcrumb] button[data-menu-open]');
  const l = b.querySelector(':scope > span:not([role])'), r = l?.getBoundingClientRect();
  return [l ? r.width > 1 && r.height > 1 && l.checkVisibility() : "no label element",
          b.querySelector(':scope > span[role=img]').getClientRects().length > 0]; }"""


def opener_label(page):
    return page.js(f"return ({OPENER_LABEL})()")


FORM_FIELDS = """
const scope = S !== document.documentElement ? S : document.getElementById("content") || document.querySelector("main");
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
    enabled submit button leave the URL, the history and the document as they were (a marker set
    on window survives, so nothing reloaded). No script cancels the submit: every example form has
    method="dialog" (static criterion 9), whose submit does nothing outside a <dialog>, so with
    JavaScript on the forms behave as example-forms-nojs holds them without it; the note counts the
    submit events and how many a handler canceled. The browser's own rules decide whether Enter
    submits at all (implicit submission: Chrome never submits a form with several text fields and no
    submit button, Firefox may) and whether validation stops a submission; the check only asks that
    none goes through."""
    try_example_forms(page)


@check("example-forms-nojs", ("/", "/docs#forms", "/docs#group", "/docs#color-schemes", "/docs#theme-picker"),
       javascript=False)
def example_forms_nojs(page):
    """With the page's JavaScript off (Chrome and Firefox; skipped in Safari), example-forms'
    submissions still never navigate, and what was typed never reaches the URL: every example form
    has method="dialog" (static criterion 9), whose submit does nothing outside a <dialog>. No
    script cancels anything here, so the check asks only that the URL, the history and the document
    stay as they were."""
    try_example_forms(page)


def try_example_forms(page):
    """Enter in every text-like field and a click on every submit button of the route's example
    forms; none may navigate."""
    forms = page.js(FORM_FIELDS)
    page.expect("the page has example forms", len(forms) > 0)
    page.js(SUBMIT_SPY)
    url = page.url()
    tried, events, canceled = 0, 0, 0

    def after(label):
        nonlocal canceled
        page.sleep(0.5)
        try:
            st = page.js("return {marker: window.__bhMarker, url: location.pathname + location.search + location.hash,"
                         " submits: window.__bhSubmits}")
        except Exception as e:   # the document went away: a submission navigated
            page.expect(label, False, error=f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        page.expect(label, st["marker"] == "kept", **st)
        page.url_kept(label, url)
        page.js("window.__bhSubmits.length = 0")
        canceled += sum(1 for x in st["submits"] if x)
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
    page.note(f"{len(forms)} forms, {tried} submissions tried, {events} submit events, {canceled} of them canceled")


# -- the controls that are buttons, and the off-canvas menu's inert page --------------------------


@check("theme-toggle-button", ("/", "/does-not-exist"))
def theme_toggle_button(page):
    """The header's color-scheme toggle is a <button type="button"> with no href
    (`button[data-scheme-toggle]`): Tab from the header's GitHub link reaches it; Space turns the
    page dark (data-theme="dark") and Enter light again, back to the OS's scheme with no data-theme,
    with no navigation (URL and history kept), and it reads "Turn on dark mode" after."""
    gh = "body > header nav a[aria-label='GitHub repository']"
    t = "body > header nav button[data-scheme-toggle]"
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
    page.wait("Enter: light, the OS's, with no data-theme", "!document.documentElement.hasAttribute('data-theme')", 1.5)
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


@check("mobile-menu-inert", "/docs#modal", width=375, height=812)
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
        page.tab(shift=True)
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
        name: ({html: "HTML", css: "CSS", bash: "Bash"}[lang] || "Example") + " code"};
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


@check("copy-keyboard", ("/docs#button", "/examples"))
def copy_keyboard(page):
    """The copy buttons are in the tab order: Tab from the focusable element before the route's first
    copy button (on /examples the last one in the mockup before it) reaches it; Enter copies the
    block's `pre code` text, the tooltip and the visually hidden status line (`body >
    p.visually-hidden[role=status]`) read "Copied", and 1 s later the tooltip reads the button's
    own "Copy code", the status line is empty and keyboard focus is still on the button; Space
    copies again, and the status line says "Copied" with a no-break space after it (U+00A0), since
    a message that repeats the one before it is written so, for a screen reader that skips a
    repeat. Then the block's <pre> is a tab stop only when its code overflows it (site.js, Code
    block focus): a block that does not overflow has no tabindex, role or aria-label, and Tab moves
    past it to the next control, after the block in document order; a block that overflows has
    tabindex="0", role="figure" and aria-label "<language> code" ("HTML code"), and Tab moves to
    it (pre-scroll-keyboard holds that branch at 375 px, where Quick start's blocks overflow). The
    note says which branch each route took."""
    page.js(COPY_SPY)
    btn = page.js("const b = S.querySelector('button[data-copy-link]');"
                  " b.closest('details')?.setAttribute('open', ''); b.scrollIntoView({block: 'center'}); return b;")
    code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", btn)
    # The focusable element just before the button in the tab order: document order with each open
    # shadow root read in place of its host (on /examples the mockup before the copy button is one).
    prev = page.js(r"""const b = arguments[0], all = [];
      const focusable = 'a[href], button, input, select, textarea, summary, [tabindex]';
      const visit = (node) => {
        for (const e of node.children) {
          if (e.matches(focusable) && e.tabIndex >= 0 && !e.disabled && !e.closest('[inert]') && e.getClientRects().length) all.push(e);
          visit(e.shadowRoot ?? e);
        }
      };
      visit(document.documentElement);
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
    page.wait("it reverts", "arguments[0].getAttribute('data-tooltip') === arguments[1] && arguments[0].querySelector(':scope > span[role=img]')?.textContent === '\\u29C9'",
              2, args=(btn, COPY_TOOLTIP))
    page.sleep(0.2)
    page.eq("keyboard focus stays on the button", page.js(COPY_INFO, btn)["focused"], True)
    page.eq("the status line is empty again", page.js(STATUS), "")
    page.key(" ")
    page.wait("Space copies", "window.__bhCopied.length === 2", 1)
    page.wait("the status line says the repeat as Copied and a no-break space",
              "document.querySelector('body > p.visually-hidden[role=status]')?.textContent === 'Copied\\u00A0'", 0.5,
              got=page.js(STATUS))
    page.wait("it reverts again", "arguments[0].getAttribute('data-tooltip') === arguments[1]", 2, args=(btn, COPY_TOOLTIP))
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


@check("pre-scroll-keyboard", "/docs", width=375, height=812)
def pre_scroll_keyboard(page):
    """At 375 px Quick start's first code block that overflows sideways is a figure in the tab order
    (tabindex="0", role="figure", aria-label "<language> code", from site.js's Code block focus),
    takes focus with Tab from its copy button, matches :focus-visible with a focus ring, femto's
    link ring (a box-shadow outside the box, not inset), and the Right arrow key scrolls it: each
    press held 0.1 s, as a person's is (Safari's keyboard scrolling animates while the key is down),
    and the scroll waited for up to 2 s. The note records the keydown events the pre saw, and whether any was canceled."""
    pre = page.js("const p = [...S.querySelectorAll('.code pre')].find(p => p.scrollWidth > p.clientWidth);"
                  " p && p.scrollIntoView({block: 'center'}); return p || null;")
    page.expect("a code block overflows", pre is not None)
    expect_pre_focus(page, "the block", pre)
    btn = page.js("return arguments[0].parentElement.querySelector('button[data-copy-link]')", pre)
    page.key("SHIFT")
    page.js("arguments[0].focus({preventScroll: true})", btn)
    page.key("TAB")
    page.eq("Tab focuses the pre", page.js("return document.activeElement === arguments[0]", pre), True)
    page.eq("it matches :focus-visible", page.js("return arguments[0].matches(':focus-visible')", pre), True)
    ring = page.js("return getComputedStyle(arguments[0]).boxShadow", pre)
    page.expect("its focus ring shows, outside the box", ring not in ("", "none") and "inset" not in ring, ring=ring)
    # On window, as the event bubbles out last: canceled by any handler on its way.
    page.js("window.__bhKeys = []; const p = arguments[0]; addEventListener('keydown', e => { "
            "if (e.target === p) window.__bhKeys.push([e.key, e.defaultPrevented]); }); return 1;", pre)
    page.key("ARROW_RIGHT", 8, hold=0.1)
    left = page.ajs("""const p = arguments[0], end = performance.now() + 2000;
      while (p.scrollLeft <= 0 && performance.now() < end) await new Promise(r => setTimeout(r, 50));
      return p.scrollLeft;""", pre)
    keys = page.js("return window.__bhKeys")
    page.note(f"keydown events on the pre [key, canceled]: {keys}; scrollLeft {left}")
    page.expect("the arrow keys scroll it", left > 0, scrollLeft=left, keydowns=keys)
