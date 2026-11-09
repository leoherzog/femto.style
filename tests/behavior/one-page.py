"""The one docs page (PLAN.md Decisions 2, 8 and 10; criteria 7 and 15): the spy that moves the side
nav's current link, its category, the breadcrumb's chapter and section, the title and the URL's #hash with the
section being read; deep links, nav clicks, back, forward and reload, which are the browser's own
fragment navigation; smooth scrolling only for nav clicks; and ?theme=. They started from the
checks of the conversion's one-page prototype (its record is at tag conversion-final), run on the
real page.

Nav clicks are real input (WebDriver pointer actions): WebKit's back skips a history entry that a
script's click made. The side nav is scrolled to the link first, never the
page, since a click's own scroll into view would move the page too. Positions are read in the page: a heading is "on the line" when its top is within 2 px of html's
scroll-padding-top, where a link to its #id puts it (behavior.HEADING_LINE)."""
import json
from pathlib import Path

from behavior import HEADING_LINE, check

GROUP = "one-page"

# The sections in menu order, as the working tree's site/docs/menu.json lists them (40 on 2026-11-09).
MENU_IDS = [s["id"] for c in json.loads((Path(__file__).resolve().parents[2] / "site/docs/menu.json").read_text(
    encoding="utf-8"))["categories"] for s in c["sections"]]

SUFFIX = " • femto"
PAGE_TITLE = "Documentation • femto"
JADE = "jade"

# Where the reader is, as the page shows it: the URL, the title, the side nav's current links (href
# and aria-current) and current summaries, the open categories, the breadcrumb's chapter (its second
# item, the category) and section (its third and last item), scrollY and history.length.
STATE = """
const nav = document.querySelector("#documentation-menu nav");
const chapter = document.querySelector("main > nav[aria-label=breadcrumb] li:nth-child(2)");
const crumb = document.querySelector("main > nav[aria-label=breadcrumb] li:nth-child(3):last-child");
return {url: location.pathname + location.search + location.hash, title: document.title,
        nav: [...nav.querySelectorAll("a[aria-current]")].map(a => [a.getAttribute("href"), a.getAttribute("aria-current")]),
        summaries: [...nav.querySelectorAll("summary[aria-current]")].map(s => [s.textContent.trim(), s.getAttribute("aria-current")]),
        open: [...nav.querySelectorAll("details")].filter(d => d.open).map(d => d.querySelector(":scope > summary").textContent.trim()),
        chapter: chapter ? chapter.textContent.trim() : null, crumb: crumb ? crumb.textContent.trim() : null,
        y: Math.round(scrollY), history: history.length};
"""

# The sections in nav order, as the page has them: [id, the h1's text, the category's summary text].
SECTIONS = """
return [...document.querySelectorAll("#documentation-menu nav a[href^='#']")].map(a => {
  const id = a.getAttribute("href").slice(1), h = document.getElementById(id);
  return [id, h ? h.textContent.trim() : null, a.closest("details").querySelector(":scope > summary").textContent.trim()];
});
"""

# Records from now on: the side nav's current links after every change (MutationObserver), every
# scroll event with its time, scrollY and html's computed scroll-behavior, and every replaceState
# call (the page's own history.replaceState, wrapped to count it) with its time and URL.
TRACK = """
const nav = document.querySelector("#documentation-menu nav");
window.__bhTrack = {nav: [], scroll: [], replace: [], t0: Math.round(performance.now())};
new MutationObserver(() => __bhTrack.nav.push([Math.round(performance.now()),
  [...nav.querySelectorAll("a[aria-current]")].map(a => a.getAttribute("href")).join(" ")]))
  .observe(nav, {subtree: true, attributes: true, attributeFilter: ["aria-current"]});
addEventListener("scroll", () => __bhTrack.scroll.push([Math.round(performance.now()), Math.round(scrollY),
  getComputedStyle(document.documentElement).scrollBehavior]), {passive: true});
if (!window.__bhReplace) {
  window.__bhReplace = history.replaceState;
  history.replaceState = function (...args) {
    __bhTrack.replace.push([Math.round(performance.now()), String(args[2])]);
    return window.__bhReplace.apply(this, args);
  };
}
return __bhTrack.t0;
"""

# Records every scrollY the page's scroll events report into __bhRevealY, which the check empties
# before each scroll of its own (one listener per document).
REVEAL_TRACK = """
window.__bhRevealY = [];
if (!window.__bhRevealListening) {
  window.__bhRevealListening = true;
  addEventListener("scroll", () => window.__bhRevealY.push(Math.round(scrollY)), {passive: true});
}
"""

# Two frames after the spy marked the section (a scroll the reveal caused has fired its event by
# then): the current link's box and the side nav's, scrollY and every scrollY since the check's scroll.
REVEAL = """
const frame = () => new Promise(r => requestAnimationFrame(() => r()));
await frame();
await frame();
const nav = document.querySelector("#documentation-menu nav"), a = nav.querySelector("a[aria-current]");
const n = nav.getBoundingClientRect(), l = a.getBoundingClientRect();
return {link: [Math.round(l.top), Math.round(l.bottom)], nav: [Math.round(n.top), Math.round(n.bottom)],
        inside: l.top >= n.top - 1 && l.bottom <= n.bottom + 1, navScrollTop: Math.round(nav.scrollTop),
        y: Math.round(scrollY), scrolls: window.__bhRevealY.slice(0, 20)};
"""

# The scroll position once it has held for 250 ms (at most 4 s).
SETTLE = """
const frame = () => new Promise(r => requestAnimationFrame(() => r()));
const end = performance.now() + 4000;
let last = scrollY, since = performance.now();
while (performance.now() < end) {
  await frame();
  if (scrollY !== last) { last = scrollY; since = performance.now(); }
  else if (performance.now() - since >= 250) return true;
}
return false;
"""

# A theme stylesheet on the page: every <link> to femto's css/themes/, by color.
THEME_LINKS = """
return [...document.querySelectorAll("link[rel=stylesheet]")].map(l => l.getAttribute("href"))
  .filter(h => /\\/css\\/themes\\//.test(h)).map(h => h.replace(/^.*\\//, "").replace(/\\.css$/, ""));
"""
PRIMARY = "return getComputedStyle(document.documentElement).getPropertyValue('--femto-primary').trim()"


# Whether the page is at its end with the section's heading still more than 2 px below its line.
SHORT_OF_LINE = """
const root = document.documentElement, h = document.getElementById(arguments[0]);
return Math.ceil(scrollY + innerHeight) >= root.scrollHeight - 1
  && h.getBoundingClientRect().top - (parseFloat(getComputedStyle(root).scrollPaddingTop) || 0) > 2;
"""


def state(page):
    return page.js(STATE)


def offset(page, sid):
    """How far the section's heading is below its line (0 on it)."""
    return page.js(f"return ({HEADING_LINE})(arguments[0])", sid)


def settle(page, label):
    page.expect(f"{label}: the scroll position settles", page.ajs(SETTLE), y=page.js("return scrollY"))


def scroll_into(page, sid, below=0):
    """Scroll instantly so the section's heading is `below` px above its line (the section is then
    the one being read); returns scrollY."""
    return page.scroll_to(page.js(f"return Math.round(scrollY + ({HEADING_LINE})(arguments[0]) + arguments[1])", sid, below))


def wait_current(page, sid, label, timeout=1.5):
    """Wait until the side nav's one current link is the section's."""
    page.wait(f"{label}: the nav marks #{sid}",
              "(() => { const a = [...document.querySelectorAll('#documentation-menu nav a[aria-current]')];"
              " return a.length === 1 && a[0].getAttribute('href') === '#' + arguments[0]; })()", timeout,
              args=(sid,), got=state(page)["nav"])


def wait_url(page, url, label, timeout=2):
    page.wait(f"{label}: the URL is {url}", "location.pathname + location.search + location.hash === arguments[0]", timeout,
              args=(url,), got=page.url())


def click_nav(page, sid):
    """A real click on the side nav's link to the section, the nav (not the page) scrolled first so
    the link is in its view."""
    link = page.js("""const nav = document.querySelector("#documentation-menu nav");
      const a = nav.querySelector(`a[href="#${arguments[0]}"]`);
      const top = a.getBoundingClientRect().top - nav.getBoundingClientRect().top + nav.scrollTop;
      if (top < nav.scrollTop || top + a.offsetHeight > nav.scrollTop + nav.clientHeight) nav.scrollTop = top - nav.clientHeight / 3;
      return a;""", sid)
    page.click(link, scroll=False)


def animated(log):
    """Whether a scroll log ([time, scrollY, ...] per event) is an animation: a smooth scroll fires an
    event per frame for 100 ms or more over 3 or more positions spread over more than 50 px; an
    instant jump fires one or two, and a page that settles as fonts load moves a pixel or so."""
    ys = [e[1] for e in log]
    return len(set(ys)) >= 3 and max(ys) - min(ys) > 50 and log[-1][0] - log[0][0] >= 100


def expect_section(page, sid, title, category, heading, label):
    """The page shows the section as the one being read: its nav link alone current
    (aria-current="true"), its category's summary alone current, that category open, the
    breadcrumb's chapter the category and its last item the section's h1 text (`heading`), and the
    title the section's (the page's own for the first)."""
    s = state(page)
    page.eq(f"{label}: the one current nav link is #{sid}", s["nav"], [[f"#{sid}", "true"]], **s)
    page.eq(f"{label}: the one current summary is {category}", s["summaries"], [[category, "true"]], **s)
    page.expect(f"{label}: {category} is open", category in s["open"], **s)
    page.eq(f"{label}: the breadcrumb's chapter is {category}", s["chapter"], category)
    page.eq(f"{label}: the breadcrumb's last item is the section, {heading}", s["crumb"], heading)
    page.eq(f"{label}: the title", s["title"], title)
    return s


def section_title(sid, h1):
    return PAGE_TITLE if sid == "quick-start" else h1 + SUFFIX


# -- deep links ------------------------------------------------------------------------------------

# Runs before the page's own scripts: every scroll event of the load, with its time and scrollY.
LOAD_SCROLLS = """() => {
  window.__bhLoadScrolls = [];
  addEventListener("scroll", () => __bhLoadScrolls.push([Math.round(performance.now()), Math.round(scrollY)]), {passive: true});
}"""


def deep_link(page):
    page.wait("Input's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('input')) <= 2", 2,
              offset=offset(page, "input"))
    wait_current(page, "input", "deep link")
    s = expect_section(page, "input", "Input" + SUFFIX, "Forms", "Input", "deep link")
    page.eq("the URL is the deep link's", s["url"], "/docs#input")
    if page.preloaded:
        log = page.js("return window.__bhLoadScrolls")
        page.expect("the load's jump to #input is not animated", not animated(log), scrolls=log[:40])
    else:
        page.note("no preload script in this browser: the load's scrolling is not recorded")


@check("spy-deep-link", "/docs#input", preload=LOAD_SCROLLS, preload_optional=True)
def spy_deep_link(page):
    """A deep link, /docs#input, is the browser's own fragment scroll, not animated (Decision 10:
    Chrome animates every deep link when html itself is smooth): Input's heading lands on the
    scroll-padding line, below the fixed header (within 2 px), in one jump (not animated, by
    `animated`'s rule, over every scroll event from the document's start, recorded by a preload
    script; Safari, which has none, skips that assertion), and the spy marks the section: the nav's one current link is #input
    (aria-current="true"), its category Forms is open and its summary alone current, the
    breadcrumb reads Forms then Input and the title "Input • femto"; the URL stays /docs#input."""
    deep_link(page)


@check("spy-deep-link-small", "/docs#input", width=375, height=812, preload=LOAD_SCROLLS, preload_optional=True)
def spy_deep_link_small(page):
    """The same deep link at 375 x 812, where the sticky breadcrumb is part of the scroll padding:
    Input's heading lands on the scroll-padding line (within 2 px) in one jump, with the same nav,
    category, breadcrumb (Forms, Input), title and URL."""
    deep_link(page)


LAYOUT_SHIFT = """
const entries = [];
new PerformanceObserver((list) => entries.push(...list.getEntries())).observe({type: "layout-shift", buffered: true});
await new Promise(r => setTimeout(r, 1000));
return {total: entries.filter(e => !e.hadRecentInput).reduce((s, e) => s + e.value, 0), count: entries.length,
        shifts: entries.slice(0, 10).map(e => [Math.round(e.startTime), Math.round(e.value * 100000) / 100000])};
"""


@check("deep-link-cold", "/docs#input", cold=True)
def deep_link_cold(page):
    """Criterion 15's run-time check: a cold load (the browser's HTTP cache emptied first) of
    /docs#input ends with Input's heading on its scroll-padding line (within 2 px), and in a browser
    with the Layout Instability API (Chrome) records a layout shift below 0.01: the sum of every
    layout-shift entry without recent input, read with a buffered PerformanceObserver 1 s after
    the page is ready. Browsers without the API (Firefox, Safari) note it and assert the position."""
    supported = page.js("return (PerformanceObserver.supportedEntryTypes || []).includes('layout-shift')")
    page.wait("Input's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('input')) <= 2", 2,
              offset=offset(page, "input"))
    if not supported:
        page.note(f"{page.browser} has no layout-shift entries (Layout Instability API): only the position is checked")
        return
    r = page.ajs(LAYOUT_SHIFT)
    page.note(f"layout shift {r['total']:.5f} over {r['count']} entries")
    page.expect("layout shift below 0.01", r["total"] < 0.01, **r)
    page.expect("Input's heading is still on the line", abs(offset(page, "input")) <= 2, offset=offset(page, "input"))


@check("nojs-deep-link", "/docs#forms", javascript=False)
def nojs_deep_link(page):
    """With the page's JavaScript off (Chrome: CDP for this tab; Firefox: javascript.enabled;
    Safari cannot, so it is skipped there), the deep link /docs#forms still lands: the browser's own
    fragment scroll puts Forms' heading on the scroll-padding line (within 2 px), scrolled down."""
    page.wait("Forms' heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('forms')) <= 2", 3,
              offset=offset(page, "forms"))
    page.expect("the page is scrolled down", page.js("return scrollY") > 0)
    page.eq("no page script ran (the spy would have named the section in the title)", page.js("return document.title"),
            PAGE_TITLE)


# Every element in the tab order (tabIndex 0 or more), in the document and in its open shadow roots
# (the /examples mockups), focused one at a time: focus() scrolls it into view as Tab does. Each one
# that takes focus must then be on screen (a box that meets the viewport) and seen
# (checkVisibility with opacity and visibility: no hidden or fully transparent box, its own or an
# ancestor's). Returns how many took focus, the first that fail, and the controls that need the
# page's JavaScript and still show (they have a box): the copy buttons and the header's theme toggle,
# /docs' breadcrumb, its Documentation button, the menu's Close and the sections' script-driven
# controls, /examples' theme select and Copy as page buttons, and the homepage's widgets.
NOJS_FOCUS = """
const tabbable = "a[href], area[href], button, input:not([type=hidden]), select, textarea, summary, iframe, [tabindex], [contenteditable]";
const all = [];
const walk = (root) => {
  for (const el of root.querySelectorAll("*")) {
    if (el.matches(tabbable)) all.push(el);
    if (el.shadowRoot) walk(el.shadowRoot);
  }
};
walk(document);
const describe = (el) => el.localName + (el.id ? "#" + el.id : "") + (el.getAttribute("href") ? `[href="${el.getAttribute("href")}"]` : "")
  + ` "${(el.getAttribute("aria-label") || el.textContent).trim().slice(0, 30)}"`
  + (el.getRootNode() !== document ? " (in a shadow root)" : "");
const bad = [];
let focused = 0;
for (const el of all) {
  if (el.tabIndex < 0) continue;
  el.focus();
  if (el.getRootNode().activeElement !== el) continue;
  focused++;
  const r = el.getBoundingClientRect();
  const seen = el.checkVisibility({opacityProperty: true, visibilityProperty: true});
  const onScreen = r.width > 0 && r.height > 0 && r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight;
  if ((!seen || !onScreen) && bad.length < 12)
    bad.push([describe(el), seen ? "off screen" : "hidden", Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]);
}
document.activeElement?.blur();
const dead = ["button[data-copy-link]", "button[data-scheme-toggle]", "nav[data-docs-breadcrumb]", "button[data-menu-open]",
              "button[data-menu-close]", "button[data-scheme-switcher]", "section[data-grid-example] > .grid > button",
              "input[name=toggle-font-size-in-rem]", "button[data-modal-open]", "p[data-palette-help]",
              "article[data-version-picker] > header a", "#content section > p:has(+ article[data-version-picker])",
              "button[data-copy-page]", "p[data-examples-theme]", "label[data-femto-switch]", "fieldset[data-swatches]",
              "button[data-demo-pause]"];
const shown = dead.filter((sel) => [...document.querySelectorAll(sel)].some((el) => el.getClientRects().length > 0));
return {candidates: all.length, focused, bad, shown, present: dead.filter((sel) => document.querySelector(sel))};
"""


def nojs_focus(page):
    r = page.js(NOJS_FOCUS)
    page.note(f"{r['focused']} of {r['candidates']} candidates took focus")
    page.expect("elements take focus", r["focused"] > 0, **r)
    page.eq("every element that takes focus is on screen and seen once focused", r["bad"], [], focused=r["focused"])
    page.eq("no control that needs the page's JavaScript shows", r["shown"], [], present=r["present"])
    want = {"button[data-scheme-toggle]", "button[data-copy-link]"} \
        | ({"nav[data-docs-breadcrumb]", "button[data-menu-open]", "button[data-menu-close]", "button[data-scheme-switcher]",
            "section[data-grid-example] > .grid > button", "input[name=toggle-font-size-in-rem]", "button[data-modal-open]",
            "p[data-palette-help]", "article[data-version-picker] > header a",
            "#content section > p:has(+ article[data-version-picker])"} if page.section else set()) \
        | ({"button[data-copy-page]", "p[data-examples-theme]"} if page.route == "/examples" else set()) \
        | ({"label[data-femto-switch]", "fieldset[data-swatches]", "button[data-demo-pause]"} if page.route == "/" else set())
    page.expect("those controls are in the markup, hidden rather than missing", want <= set(r["present"]),
                want=sorted(want), present=r["present"])


@check("nojs-focus", ("/docs", "/", "/examples"), javascript=False)
def nojs_focus_large(page):
    """With the page's JavaScript off, at 1300 x 900, on /docs, the homepage and /examples: every
    element in the tab order (tabIndex 0 or more; the document's and its open shadow roots'), once
    focused (focus() scrolls it into view, as Tab does), has a box that meets the viewport and is
    seen (checkVisibility with opacity and visibility). Nothing takes focus off screen or hidden.
    The controls that need the page's JavaScript are in the markup but show nothing (no box): the
    header's theme toggle and the copy buttons; on /docs the breadcrumb, its Documentation button,
    the menu's Close, the Color schemes switcher, Grid's Add and Remove column, Typography's rem
    switch, the Modal demo's opener, the Colors palette's help, and the Theme picker's swatches with
    the sentence that introduces them (each a link to ?theme=, which only a head script applies);
    on /examples the theme select
    and the Copy as page buttons; on the homepage the femto switch, the theme swatches and the
    typing demo's Pause. Skipped in Safari (JavaScript cannot be turned off there)."""
    nojs_focus(page)


@check("nojs-focus-small", ("/docs", "/", "/examples"), width=375, height=812, javascript=False)
def nojs_focus_small(page):
    """The same at 375 x 812, where /docs's side menu is the off-canvas panel when JavaScript runs:
    with it off, none of the menu's links takes focus off screen (they sat at x = -375 before
    docs.css's (scripting: none) rules), and nothing else does."""
    nojs_focus(page)


# The side menu with JavaScript off: its box, #content's, and each nav link's box and whether it is seen.
NOJS_MENU = """
const m = document.querySelector("#documentation-menu"), c = document.querySelector("#content"), root = document.documentElement;
const sections = c.querySelectorAll(":scope > section > hgroup > h1[id]").length;
const mr = m.getBoundingClientRect(), cr = c.getBoundingClientRect();
const links = [...m.querySelectorAll("nav a[href^='#']")].map((a) => {
  const r = a.getBoundingClientRect();
  return [a.getAttribute("href"), a.checkVisibility({opacityProperty: true, visibilityProperty: true}), Math.round(r.left), Math.round(r.right)];
});
return {sections, position: getComputedStyle(m).position, menu: [mr.top + scrollY, mr.bottom + scrollY, mr.left, mr.right],
        content: [cr.top + scrollY, cr.left], links, clientWidth: root.clientWidth,
        unseen: links.filter((l) => !l[1] || l[2] < 0 || l[3] > root.clientWidth).slice(0, 8)};
"""


def nojs_menu(page, small):
    m = page.js(NOJS_MENU)
    page.eq("the menu has a link for each section", len(m["links"]), m["sections"])
    page.eq("every menu link is seen, inside the page's width", m["unseen"], [], clientWidth=m["clientWidth"])
    if small:
        page.eq("the menu is in the page's flow", m["position"], "static")
        page.expect("the menu comes before the sections", m["menu"][1] <= m["content"][0] + 0.5, **m)
    else:
        page.expect("the menu is the side nav, beside the sections", m["menu"][3] <= m["content"][1] + 0.5, **m)
    n = page.js("return history.length")
    page.click("#documentation-menu nav a[href='#grid']")
    wait_url(page, "/docs#grid", "the Grid link")
    page.wait("Grid's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('grid')) <= 2", 3,
              offset=offset(page, "grid"))
    page.eq("one new history entry", page.js("return history.length"), n + 1)
    page.eq("no page script ran", page.js("return document.title"), PAGE_TITLE)


@check("nojs-menu", "/docs", javascript=False)
def nojs_menu_large(page):
    """With the page's JavaScript off, at 1300 x 900, the docs menu is the side nav beside the
    sections: its links, one per section of menu.json, are all seen and inside the page's width, and a
    real click on Grid's link is the browser's own fragment navigation: /docs#grid, one new history
    entry, Grid's heading on the scroll-padding line (within 2 px), and the title unchanged. Skipped
    in Safari."""
    nojs_menu(page, small=False)


@check("nojs-menu-small", "/docs", width=375, height=812, javascript=False)
def nojs_menu_small(page):
    """The same at 375 x 812, where with JavaScript off the menu is no off-canvas panel but a block
    in the page's flow (position static) before the sections, all its links seen and inside the
    page's width; Grid's link lands Grid's heading on the scroll-padding line, which leaves room
    for its chapter label with no sticky breadcrumb above it."""
    nojs_menu(page, small=True)


# -- the spy while scrolling ----------------------------------------------------------------------

@check("spy-scroll", "/docs")
def spy_scroll(page):
    """Scrolling writes the section into the URL 200 ms after scrolling last moved, once the section
    it settles on differs from the hash (docs.js syncUrl restarts its timer on every scroll frame):
    from the top, a jump so Grid's heading is 40 px above its line makes the nav mark #grid and the
    title "Grid • femto" at once, and the URL /docs#grid by replaceState (no new history entry)
    180 ms or more after the jump. Back at the top the URL is plain /docs (no hash), the title the
    page's own ("Documentation • femto") and the nav marks #quick-start. At the very bottom the
    last section in menu.json is current: the URL is /docs#<its id>, the nav marks it and the
    title is its h1's."""
    s0 = state(page)
    page.eq("plain /docs at the top", s0["url"], "/docs")
    page.js(TRACK)
    at = page.js("return Math.round(performance.now())")
    scroll_into(page, "grid", 40)
    wait_current(page, "grid", "Grid")
    page.wait("the title is Grid's", "document.title === 'Grid • femto'", 1, got=page.js("return document.title"))
    wait_url(page, "/docs#grid", "Grid")
    rep = page.js("return __bhTrack.replace")
    page.expect("Grid: one replaceState, 180 ms or more after the jump", len(rep) == 1 and rep[0][0] - at >= 180,
                replace=rep, jump_at=at)
    page.eq("Grid: no new history entry", state(page)["history"], s0["history"])
    page.scroll_to(0)
    wait_current(page, "quick-start", "top")
    wait_url(page, "/docs", "top")
    s = state(page)
    page.eq("top: the page's own title", s["title"], PAGE_TITLE)
    page.eq("top: no new history entry", s["history"], s0["history"])
    page.scroll_to(page.js("return document.documentElement.scrollHeight"))
    last = MENU_IDS[-1]
    wait_current(page, last, "bottom")
    wait_url(page, f"/docs#{last}", "bottom")
    h1 = page.js("return document.getElementById(arguments[0]).textContent.trim()", last)
    page.eq(f"bottom: the title is {h1}'s", state(page)["title"], h1 + SUFFIX)


FAST_SCROLL = """
const height = document.documentElement.scrollHeight;
const t0 = performance.now();
let y = 0, steps = 0;
await new Promise(res => (function step() {
  scrollTo({top: y, behavior: "instant"});
  steps++;
  y += 200;
  if (y < height) setTimeout(step, 16); else res();
})());
const scrollMs = Math.round(performance.now() - t0);
await new Promise(r => setTimeout(r, 600));
return {height, steps, scrollMs, replace: __bhTrack.replace, url: location.pathname + location.search + location.hash};
"""


@check("spy-fast-scroll", "/docs")
def spy_fast_scroll(page):
    """A fast scroll from the top to the bottom, 200 px every 16 ms in the page, makes at most 3
    replaceState calls (the URL is written 200 ms after scrolling last moved) and ends on the last
    section in menu.json, /docs#<its id>, with the nav marking it."""
    page.js(TRACK)
    r = page.ajs(FAST_SCROLL)
    page.note(f"{r['steps']} steps over {r['scrollMs']} ms, {len(r['replace'])} replaceState calls")
    page.expect("at most 3 replaceState calls", len(r["replace"]) <= 3, **r)
    wait_url(page, f"/docs#{MENU_IDS[-1]}", "the end")
    wait_current(page, MENU_IDS[-1], "the end")


@check("spy-categories", "/docs")
def spy_categories(page):
    """The nav, its categories, the breadcrumb and the title follow the spy through every section:
    for each of the nav's links in order (one per section, as site/docs/menu.json lists
    them: 40 on 2026-11-09), with the page scrolled so
    that section's heading is on its line (or as far as the page goes, for the last), the one current
    link is its own (aria-current="true"), its category's summary alone is current and that category
    is open, the breadcrumb's chapter names the category and its last item the section (its h1's
    text), and the title is "<the section's h1> • femto" (the page's own for Quick start). The spy scrolls the side nav, never the page, to show
    the current link (docs.js revealInNav): at 1300 px, two frames after the mark, the current link's
    box lies within the side nav's (1 px slack), and the page is still where the check scrolled it,
    every scroll event since then reporting that scrollY (within 1 px). A category the reader closes
    opens again when one of its sections becomes current: Forms closed (a click on its summary) while
    Quick start is read opens, with its summary current, once the page is scrolled to Input."""
    sections = page.js(SECTIONS)
    page.eq(f"{len(MENU_IDS)} sections in the nav, in menu.json's order", [s[0] for s in sections], MENU_IDS)
    page.expect("every nav link has its section", all(s[1] for s in sections), missing=[s[0] for s in sections if not s[1]])
    page.js(REVEAL_TRACK)
    last = sections[-1]
    for sid, h1, category in sections:
        page.js("window.__bhRevealY = []")
        y = scroll_into(page, sid)
        if sid != last[0] and page.js(SHORT_OF_LINE, sid):
            # The page ends before this heading reaches its line: there the last section is current
            # once its top is on screen (docs.js, the spy), which the last step checks.
            page.note(f"#{sid}: the page ends before its heading reaches its line; the last section is current there")
            continue
        wait_current(page, sid, sid)
        expect_section(page, sid, section_title(sid, h1), category, h1, sid)
        r = page.ajs(REVEAL)
        page.expect(f"{sid}: the current link is inside the side nav's box", r["inside"], **r)
        page.expect(f"{sid}: the reveal scrolled the side nav, not the page",
                    all(abs(v - y) <= 1 for v in [r["y"], *r["scrolls"]]), scrolled_to=y, **r)
    page.scroll_to(0)
    wait_current(page, "quick-start", "top")
    forms = page.js("""return [...document.querySelectorAll('#documentation-menu nav details > summary')]
                       .find(s => s.textContent.trim() === 'Forms')""")
    if page.js("return arguments[0].parentElement.open", forms):
        page.click(forms)
    page.wait("Forms is closed", "!arguments[0].parentElement.open", 1, args=(forms,))
    scroll_into(page, "input")
    wait_current(page, "input", "Input")
    page.wait("Forms opens again for Input", "arguments[0].parentElement.open", 1, args=(forms,))
    expect_section(page, "input", "Input" + SUFFIX, "Forms", "Input", "Input")


# The breadcrumb's last item, the section, as the reader sees it: its box and the breadcrumb's, the
# first item's top (one line: every item on it), and whether its text is cut, with the overflow and
# text-overflow that draw the cut.
CRUMB_FIT = """
const nav = document.querySelector("main > nav[aria-label=breadcrumb]"), first = nav.querySelector("li:first-child");
const li = nav.querySelector("li:last-child"), cs = getComputedStyle(li);
const n = nav.getBoundingClientRect(), l = li.getBoundingClientRect();
return {text: li.textContent.trim(), left: l.left, right: l.right, navRight: n.right, innerWidth,
        sameLine: Math.abs(l.top - first.getBoundingClientRect().top) <= 1, cut: li.scrollWidth > li.clientWidth,
        overflow: cs.overflowX, textOverflow: cs.textOverflow, whiteSpace: cs.whiteSpace};
"""


def expect_crumb_fits(page, label):
    """The breadcrumb's last item stays on the breadcrumb's one line and inside its box, and when
    its text is longer than the room left it is cut with an ellipsis."""
    r = page.js(CRUMB_FIT)
    page.expect(f"{label}: the section's item is on the breadcrumb's one line, inside it",
                r["sameLine"] and r["right"] <= min(r["navRight"], r["innerWidth"]) + 0.5 and r["left"] < r["right"], **r)
    if r["cut"]:
        page.eq(f"{label}: the section's cut text ends in an ellipsis", [r["overflow"], r["textOverflow"], r["whiteSpace"]],
                ["hidden", "ellipsis", "nowrap"], **r)
    return r


@check("spy-chapter-small", "/docs", width=375, height=812)
def spy_chapter_small(page):
    """At 375 x 812, where the breadcrumb shows (sticky, "Documentation > <category> > <section>",
    the Documentation button drawn as its ☰ alone), its chapter and its last item follow the spy as
    the reader scrolls: Customization and Colors at
    Colors, Layout and Grid at Grid, Content and Table at Table, Forms and Radios at Radios,
    Components and Modal at Modal, Advanced and Cascade layer at Cascade layer, Reference and
    Migrating from Pico at Migrating from Pico, Reference and Browser support at Browser support, and
    Getting started and Quick start back at the top (each section's h1 text and its nav category, as
    the page has them). At each, the section's item stays on the breadcrumb's one line and inside
    it, and shows in full: with the button's label out of sight, even Getting started > Migrating
    from Pico fits. A name too long for the room left would be cut with an ellipsis (overflow
    hidden, text-overflow ellipsis, white-space nowrap), which is checked whenever one is cut."""
    names = {sid: (h1, category) for sid, h1, category in page.js(SECTIONS)}
    cut = []
    for sid in ("colors", "grid", "table", "radios", "modal", "cascade-layer", "migration", "browser-support", "quick-start"):
        h1, category = names[sid]
        if sid == "quick-start":
            page.scroll_to(0)
        else:
            scroll_into(page, sid)
        wait_current(page, sid, sid)
        page.wait(f"{sid}: the breadcrumb reads {category} > {h1}",
                  "(() => { const n = document.querySelector('main > nav[aria-label=breadcrumb]');"
                  " return n.querySelector('li:nth-child(2)').textContent.trim() === arguments[0]"
                  " && n.querySelector('li:nth-child(3):last-child').textContent.trim() === arguments[1]; })()", 1,
                  args=(category, h1), got=[state(page)["chapter"], state(page)["crumb"]])
        if expect_crumb_fits(page, sid)["cut"]:
            cut.append(sid)
    page.eq("at 375 px every section's name shows in full", cut, [])


# Records every scrollY the page's scroll events report into __bhOpenerY from now on.
OPENER_TRACK = """
window.__bhOpenerY = [];
addEventListener("scroll", () => window.__bhOpenerY.push(Math.round(scrollY)), {passive: true});
"""
OPENER = "main > nav[aria-label=breadcrumb] button[data-menu-open]"


def opener_shift_tab(page):
    sid = page.section
    h1, category = {s: (h, c) for s, h, c in page.js(SECTIONS)}[sid]
    page.wait(f"{h1}'s heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})(arguments[0])) <= 2", 2,
              args=(sid,), offset=offset(page, sid))
    wait_current(page, sid, "deep link")
    settle(page, "deep link")
    page.wait("the breadcrumb is stuck at the top", "Math.abs(document.querySelector('main > nav[aria-label=breadcrumb]')"
              ".getBoundingClientRect().top + 1) <= 1", 1)
    # A click on the section's crumb (text, not a control) puts the sequential focus starting point
    # there, so Shift+Tab goes to the opener just before it.
    page.click("main > nav[aria-label=breadcrumb] li:nth-child(3):last-child", scroll=False)
    before = state(page)
    page.js(OPENER_TRACK)
    page.tab(shift=True)
    page.eq("Shift+Tab focuses the Documentation button", page.js("return document.activeElement === document.querySelector(arguments[0])", OPENER),
            True, active=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
    page.sleep(0.6)   # a scroll would have run and the spy (200 ms) moved by now
    after = state(page)
    page.eq("the page did not scroll", page.js("return window.__bhOpenerY"), [], before=before["y"], after=after["y"])
    page.expect("scrollY is kept (within 1 px)", abs(after["y"] - before["y"]) <= 1, before=before["y"], after=after["y"])
    page.eq("the URL is kept", after["url"], f"/docs#{sid}")
    page.eq("the breadcrumb still reads the section", [after["chapter"], after["crumb"]], [category, h1])
    page.eq("the title is kept", after["title"], section_title(sid, h1))
    page.eq("no new history entry", after["history"], before["history"])


@check("opener-shift-tab-small", ("/docs#grid", "/docs#input"), width=375, height=812)
def opener_shift_tab_small(page):
    """At 375 x 812, deep-linked to a section, with the sticky breadcrumb stuck at the top: after a
    click on the breadcrumb's section item, Shift+Tab focuses the Documentation button
    (button[data-menu-open]) and the page stays where it is: no scroll event, scrollY within 1 px,
    and 600 ms later the URL's hash, the breadcrumb's chapter and section, the title and
    history.length unchanged. The stuck button sits inside html's scroll padding, which Chrome takes
    for out of view: without docs.css's scroll margin on it, Chrome scrolled the page about 420 px up
    and the spy moved everything to the section before (Firefox did not scroll)."""
    opener_shift_tab(page)


@check("opener-shift-tab", ("/docs#grid", "/docs#input"), width=800, height=1000)
def opener_shift_tab_md(page):
    """The same at 800 x 1000, in the md container, where the breadcrumb is full bleed and the root
    font size, and so the scroll padding, is larger."""
    opener_shift_tab(page)


# -- nav clicks, back, forward, reload -------------------------------------------------------------

def nav_click(page, label):
    """From 200 px into Modal, a real click on the nav's Container link; returns the state before
    and the tracked logs."""
    scroll_into(page, "modal", 200)
    wait_current(page, "modal", f"{label}: in Modal")
    wait_url(page, "/docs#modal", f"{label}: in Modal")
    before = state(page)
    page.js(TRACK)
    click_nav(page, "container")
    wait_url(page, "/docs#container", f"{label}: after the click", 3)
    page.wait(f"{label}: Container's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('container')) <= 2", 3,
              offset=offset(page, "container"))
    settle(page, label)
    page.sleep(0.3)   # the click's lock ends once its scroll reaches Container
    return before, page.js("return __bhTrack")


def expect_click(page, before, track, label):
    after = expect_section(page, "container", "Container" + SUFFIX, "Layout", "Container", label)
    page.eq(f"{label}: one new history entry", after["history"], before["history"] + 1)
    seen = sorted({x for _, x in track["nav"] if x})
    page.eq(f"{label}: the nav never shows a section in between", seen, ["#container"], log=track["nav"],
            scroll=track["scroll"][:12], t0=track["t0"])
    page.eq(f"{label}: html scrolls instantly again once the click's scroll is over",
            page.js("return getComputedStyle(document.documentElement).scrollBehavior"), "auto")
    return after


@check("spy-nav-click", "/docs#modal")
def spy_nav_click(page):
    """A nav click is the browser's own fragment navigation, smooth (Decision 10): from 200 px into
    Modal, a real click on the nav's Container link makes the URL /docs#container with exactly one new
    history entry and Container's heading on the scroll-padding line; the nav's current link moves
    straight to #container (never to a section passed on the way), with Layout's summary current and
    the title "Container • femto". The scroll is animated (`animated`: 3 or more positions over more
    than 50 px and 100 ms or more)
    with html's computed scroll-behavior smooth during it, and auto again once it is over."""
    before, track = nav_click(page, "click")
    expect_click(page, before, track, "click")
    page.expect("the click's scroll is animated", animated(track["scroll"]), scroll=track["scroll"][:40])
    page.expect("html's scroll-behavior is smooth while it scrolls", any(b == "smooth" for _, _, b in track["scroll"]),
                scroll=track["scroll"][:40])


@check("spy-nav-click-reduced", "/docs#modal", motion="reduce")
def spy_nav_click_reduced(page):
    """Under prefers-reduced-motion: reduce (emulated in Chrome and Firefox; Safari reads macOS's
    Reduce Motion, so it runs there in the owner's pass with it on, tests/owner-safari.sh reduced),
    the same nav click jumps without animation: the URL /docs#container with one new history entry,
    Container's heading on its line, the nav straight to #container, and the scroll one jump (not
    animated), html's scroll-behavior never smooth."""
    before, track = nav_click(page, "click")
    expect_click(page, before, track, "click")
    page.expect("the click jumps (no animation)", not animated(track["scroll"]), scroll=track["scroll"][:40])
    page.expect("html's scroll-behavior is never smooth", all(b != "smooth" for _, _, b in track["scroll"]),
                scroll=track["scroll"][:40])


@check("spy-back-forward", "/docs#modal")
def spy_back_forward(page):
    """Back and forward are the browser's own traversal, never animated: after the nav click from
    200 px into Modal to Container, back returns to /docs#modal, at the exact position it left
    (Firefox, Safari) or with Modal's heading on its line (Chrome goes to the entry's #hash heading;
    accepted, PLAN.md Risks), the nav marking #modal; forward returns to /docs#container, the nav marking
    #container. Neither scroll is animated."""
    before, _ = nav_click(page, "click")
    page.js(TRACK)
    page.driver.back()
    wait_url(page, "/docs#modal", "back", 3)
    settle(page, "back")
    wait_current(page, "modal", "back")
    s, off = state(page), offset(page, "modal")
    exact = abs(s["y"] - before["y"]) < 5
    page.expect("back: the exact position, or Modal's heading on its line", exact or abs(off) <= 2,
                y_before=before["y"], y=s["y"], heading_offset=off)
    page.note(f"back {'restored the exact position' if exact else 'went to the #modal heading'} (y {before['y']} then {s['y']})")
    log = page.js("return __bhTrack.scroll")
    page.expect("back is not animated", not animated(log), scroll=log[:40])
    page.js(TRACK)
    page.driver.forward()
    wait_url(page, "/docs#container", "forward", 3)
    settle(page, "forward")
    wait_current(page, "container", "forward")
    log = page.js("return __bhTrack.scroll")
    page.expect("forward is not animated", not animated(log), scroll=log[:40])


@check("spy-reload", "/docs#css-variables")
def spy_reload(page):
    """Reload keeps the reader in the section: scrolled 900 px into CSS variables (less in a shorter
    section: half its height), location.reload() comes back to the same URL at the exact position
    (Chrome, Firefox) or with the section's heading on its line (Safari; accepted 2026-11-02), the
    nav marking #css-variables; WebDriver's refresh (a hard reload in Firefox) shows the section too:
    the same URL and the nav marking #css-variables."""
    height = page.js("return Math.round(document.getElementById('css-variables').closest('section').getBoundingClientRect().height)")
    scroll_into(page, "css-variables", min(900, height // 2))
    wait_current(page, "css-variables", "scrolled")
    wait_url(page, "/docs#css-variables", "scrolled")
    before = state(page)
    page.js("window.__bhMarker = 'before the reload'; setTimeout(() => location.reload(), 0); return true;")
    page.wait("the page reloaded", "window.__bhMarker === undefined && document.readyState === 'complete'", 15)
    page.wait_ready()
    settle(page, "reload")
    wait_current(page, "css-variables", "reload")
    s, off = state(page), offset(page, "css-variables")
    page.eq("reload: the same URL", s["url"], before["url"])
    exact = abs(s["y"] - before["y"]) < 5
    page.expect("reload: the exact position, or the heading on its line", exact or abs(off) <= 2,
                y_before=before["y"], y=s["y"], heading_offset=off)
    page.note(f"location.reload() {'kept the exact position' if exact else 'went to the #css-variables heading'}")
    page.js("window.__bhMarker = 'before the refresh'")
    page.driver.refresh()
    page.wait("the page loaded again", "window.__bhMarker === undefined && document.readyState === 'complete'", 15)
    page.wait_ready()
    settle(page, "refresh")
    wait_current(page, "css-variables", "refresh")
    s = state(page)
    page.eq("refresh: the same URL", s["url"], before["url"])
    page.note(f"WebDriver refresh: y {s['y']}, the #css-variables heading {offset(page, 'css-variables'):.0f} px from its line")


# -- ?theme= ----------------------------------------------------------------------------------------

# Runs before the page's own scripts: --femto-primary in the first animation frame requested once
# the parser has reached <body>, after the head and its stylesheets. Chrome runs no frame before a
# render-blocking stylesheet has loaded, so there the first frame is the first one painted. Firefox
# runs animation frames, and paints, while a stylesheet in <head> is still loading, unless a later
# parser-blocking script waits for it: the site's color-scheme script, the second inline head script,
# comes after the ?theme= script (PLAN.md Decisions 8 and 14), so the parser, and with it Firefox's
# first paint, waits there until the theme's file has loaded, and <body> comes after it too. Probed
# on 2026-11-04 in headless Firefox 160 with jade's file held 300 ms: with one head script, the
# first contentful paint came at 80 to 277 ms, before the file's responseEnd; with a static inline
# script after it, at 455 to 588 ms, after it. With the two scripts, Firefox's first contentful
# paint came at 492 to 498 ms, after the file's responseEnd at 355 to 359 ms, and this frame was
# jade's; on a copy with the two merged into one script again it came at 181 ms, before the file
# (357 ms), with azure's frame (owner decision 13, tests/README.md). So in
# Chrome and Firefox alike the check asserts the first contentful paint after the file arrived and
# this frame in jade's color.
FIRST_FRAME = """() => {
  new MutationObserver((records, observer) => {
    if (!document.body) return;
    observer.disconnect();
    requestAnimationFrame(() => {
      window.__bhFirstFrame = getComputedStyle(document.documentElement).getPropertyValue("--femto-primary").trim();
    });
  }).observe(document, {childList: true, subtree: true});
}"""

THEME_TIMING = """
const link = [...document.querySelectorAll("link[rel=stylesheet]")].find(l => /\\/css\\/themes\\//.test(l.getAttribute("href")));
const entry = link && performance.getEntriesByName(link.href)[0];
const fcp = performance.getEntriesByName("first-contentful-paint")[0];
const nav = performance.getEntriesByType("navigation")[0];
return {inHead: !!link && link.parentElement === document.head, firstFrame: window.__bhFirstFrame ?? null,
        startTime: entry ? Math.round(entry.startTime) : null, responseEnd: entry ? Math.round(entry.responseEnd) : null,
        blocking: entry && "renderBlockingStatus" in entry ? entry.renderBlockingStatus : null,
        dcl: nav ? Math.round(nav.domContentLoadedEventStart) : null, fcp: fcp ? Math.round(fcp.startTime) : null};
"""

# How long the harness holds jade's file. Served at once, a <link> added by
# script would arrive before the first paint too, and the check could not tell it from document.write.
THEME_DELAY = 0.3


def azure_primary(page):
    """--femto-primary on plain /docs, loaded in a second tab."""
    here = page.driver.current_window_handle
    page.new_tab("/docs")
    v = page.js(PRIMARY)
    page.driver.close()
    page.switch(here)
    return v


@check("theme-first-frame", "/docs?theme=jade#grid", preload=FIRST_FRAME, preload_optional=True, cold=True,
       delay={f"/vendor/femto/css/themes/{JADE}.css": THEME_DELAY})
def theme_first_frame(page):
    """?theme=jade is applied as a parser-inserted stylesheet, before the first paint, on a cold load
    with jade's file held 300 ms (THEME_DELAY; resource timing shows the hold, except in Safari,
    which has no BiDi): the page has exactly one theme stylesheet, jade's
    (/vendor/femto/css/themes/jade.css), in <head> (the ?theme= head script's document.write,
    Decision 8); DOMContentLoaded comes after the file arrived (a parser-inserted stylesheet holds
    back the deferred scripts; a <link> added by script does not); --femto-primary is not azure's
    (plain /docs, read in a second tab). In Chrome and Firefox a first-contentful-paint entry exists
    within 3 s, the first contentful paint comes after the file arrived, and the first animation
    frame already has jade's value (read by a preload script; FIRST_FRAME): Chrome holds the paint
    for the render-blocking resource (renderBlockingStatus "blocking", asserted there; a <link>
    added by script is "non-blocking"), Firefox because the color-scheme head script, a
    parser-blocking script after the ?theme= one, waits for the stylesheet (Decisions 8 and 14).
    Safari's paint timing is asserted as in Chrome when it has the entries; its first frame (no
    preload script) is noted."""
    page.eq("one theme stylesheet, jade's", page.js(THEME_LINKS), [JADE])
    if page.browser != "safari":
        page.wait("a first-contentful-paint entry exists", "performance.getEntriesByName('first-contentful-paint').length > 0", 3)
    r = page.js(THEME_TIMING)
    page.expect("the theme's <link> is in <head>", r["inHead"], **r)
    if page.browser == "safari":
        page.note(f"the theme file was not held (no BiDi): {r}")
    else:
        page.expect("the theme stylesheet was held", r["responseEnd"] is not None
                    and r["responseEnd"] - r["startTime"] >= THEME_DELAY * 1000 - 50, **r)
    page.expect("DOMContentLoaded waits for the theme stylesheet (parser-inserted)",
                r["dcl"] is not None and r["responseEnd"] is not None and r["dcl"] >= r["responseEnd"], **r)
    now = page.js(PRIMARY)
    page.expect("--femto-primary is not azure's", now != azure_primary(page), primary=now)
    if page.browser == "chrome":
        page.eq("the theme stylesheet is render-blocking", r["blocking"], "blocking", **r)
    else:
        page.note(f"renderBlockingStatus {r['blocking']} (asserted in Chrome only)")
    if r["fcp"] is not None and r["responseEnd"] is not None:
        page.expect("the first contentful paint comes after the theme stylesheet arrived", r["fcp"] >= r["responseEnd"], **r)
    else:
        page.note(f"paint or resource timing missing: {r}")
    if page.preloaded:
        page.eq("the first animation frame has jade's --femto-primary", r["firstFrame"], now, **r)
    else:
        page.note(f"no preload script in this browser: the first animation frame is not read ({r['firstFrame']})")
    page.note(f"held {r['responseEnd'] - r['startTime'] if r['responseEnd'] is not None else None} ms; responseEnd "
              f"{r['responseEnd']}, DOMContentLoaded {r['dcl']}, first contentful paint {r['fcp']} ms")


@check("theme-kept", "/docs?theme=jade#grid")
def theme_kept(page):
    """?theme= stays in the URL through the spy and nav clicks (the path and query are kept, only the
    hash changes): scrolled into Modal the URL becomes /docs?theme=jade#modal; a nav click on Forms
    makes it /docs?theme=jade#forms; a nav click on Quick start ends on plain /docs?theme=jade (no
    hash) with Quick start's heading on its line and the page's own title. Jade stays the page's one
    theme stylesheet throughout."""
    scroll_into(page, "modal", 40)
    wait_current(page, "modal", "Modal")
    wait_url(page, "/docs?theme=jade#modal", "scrolled into Modal")
    click_nav(page, "forms")
    wait_url(page, "/docs?theme=jade#forms", "Forms click", 3)
    settle(page, "Forms click")
    page.sleep(0.3)
    wait_current(page, "forms", "Forms click")
    click_nav(page, "quick-start")
    wait_url(page, "/docs?theme=jade", "Quick start click", 3)
    page.wait("Quick start's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('quick-start')) <= 2", 3,
              offset=offset(page, "quick-start"))
    settle(page, "Quick start click")
    page.sleep(0.3)
    wait_url(page, "/docs?theme=jade", "Quick start click, settled")
    s = state(page)
    page.eq("Quick start click: the page's own title", s["title"], PAGE_TITLE)
    page.eq("jade is still the one theme stylesheet", page.js(THEME_LINKS), [JADE])


@check("theme-unknown", ("/docs?theme=bogus", "/docs?theme=azure", "/docs?theme=JADE", "/docs?theme=..%2Fthemes%2Fjade",
                         "/docs?theme=jade.css"))
def theme_unknown(page):
    """A ?theme= value that is not one of the 19 theme colors (an unknown word, azure the default,
    the wrong case, a path, a file name) is ignored: no theme stylesheet on the page and
    --femto-primary as on plain /docs (read in a second tab). The URL keeps the query as it was given,
    and so does the spy: scrolled into Grid, the URL is /docs?<the same query>#grid."""
    page.eq("no theme stylesheet", page.js(THEME_LINKS), [])
    search = page.js("return location.search")
    page.eq("the query is kept as given", search, "?" + page.route.split("?", 1)[1])
    page.eq("--femto-primary is azure's", page.js(PRIMARY), azure_primary(page))
    scroll_into(page, "grid", 40)
    wait_current(page, "grid", "Grid")
    wait_url(page, f"/docs{search}#grid", "Grid")
