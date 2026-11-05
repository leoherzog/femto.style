"""Content: Typography's font-size table switch, Table's inverse thead and Link's example links
(01 §2, small widgets: FontsizeTable.jsx, docs.table.jsx, docs.link.jsx)."""
from behavior import SNAPSHOT, check, self_href

GROUP = "content"

# The oracle's fontSizesTableData (components/docs/FontsizeTable.jsx).
ROOT = [100, 106.25, 112.5, 118.75, 125, 131.25]
ELEMENTS = [("h1", 2, "rem"), ("h2", 1.75, "rem"), ("h3", 1.5, "rem"), ("h4", 1.25, "rem"), ("h5", 1.125, "rem"),
            ("h6", 1, "rem"), ("small", 0.875, "em")]


def js_number(x):
    """A number as JavaScript prints it (shortest round trip; integers without a fraction)."""
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def px_rows():
    rows = [[(f"{js_number(p * 16 / 100)}px", f"{js_number(p)}% * 16px") for p in ROOT]]
    for _, size, unit in ELEMENTS:
        rows.append([(f"{js_number(p * 16 / 100 * size)}px", f"{js_number(p)}% * {js_number(size)}{unit} * 16px") for p in ROOT])
    return rows


def rem_rows():
    rows = [[f"{js_number(p)}%" for p in ROOT]]
    for _, size, unit in ELEMENTS:
        rows.append([f"x {js_number(size)}{unit}" for _ in ROOT])
    return rows


TABLE = SNAPSHOT + """
const t = S.querySelector("table#responsive-font-sizes"), sw = S.querySelector('input[name="toggle-font-size-in-rem"]');
return {cells: [...t.querySelectorAll("tbody tr")].map(r => [...r.querySelectorAll("td")].map(td => {
          const s = td.querySelector(":scope > span[data-tooltip]");
          return [td.textContent, s ? s.getAttribute("data-tooltip") : null]; })),
        heads: [...t.querySelectorAll("tbody tr > th")].map(th => th.textContent),
        checked: sw.checked, role: sw.getAttribute("role"), label: sw.closest("label").textContent.trim(), tree: snap(t)};
"""
SWITCH = 'input[name="toggle-font-size-in-rem"]'


@check("font-size-units", "/docs#typography")
def font_size_units(page):
    """The responsive font-size table (`table#responsive-font-sizes`) shows px with a formula
    tooltip per cell (Base row 16px "100% * 16px" ... 21px; h1 row 32px "100% * 2rem * 16px" ...;
    the small row in em) while the "Display in rem" switch (`input[name=toggle-font-size-in-rem]`,
    role=switch) is off. Checking it shows the root sizes as percentages (100% ... 131.25%) and each
    element as a multiplier ("x 2rem", non-breaking space), with no tooltips; unchecking it restores
    the px table exactly as loaded (the same tree)."""
    t0 = page.js(TABLE)
    page.eq("the switch is a role=switch checkbox labelled 'Display in rem'", [t0["role"], t0["label"]], ["switch", "Display in rem"])
    page.eq("off on load", t0["checked"], False)
    page.eq("row heads", t0["heads"], ["Base"] + [f"<{n}>" for n, _, _ in ELEMENTS])
    page.eq("px values and formulas on load", t0["cells"], [[list(c) for c in r] for r in px_rows()])
    page.click(page.find(SWITCH))
    page.wait("rem values after checking", "S.querySelector('table#responsive-font-sizes tbody td').textContent === '100%'", 1)
    t1 = page.js(TABLE)
    page.eq("switch checked", t1["checked"], True)
    page.eq("percent and multipliers, no tooltips", t1["cells"], [[[c, None] for c in r] for r in rem_rows()])
    page.click(page.find(SWITCH))
    page.wait("px values after unchecking", "S.querySelector('table#responsive-font-sizes tbody td').textContent === '16px'", 1)
    t2 = page.js(TABLE)
    page.eq("switch unchecked", t2["checked"], False)
    page.eq("the px table exactly as loaded", t2["tree"], t0["tree"])


# Firefox's form restoration, for a browser that does not restore the switch on a reload itself
# (Chrome): the switch is checked as the parser inserts it, before any of the page's scripts runs.
# Only the control's checked state is set, as a restoration sets it; the markup is untouched.
RESTORE_SWITCH = """() => {
  new MutationObserver((records, observer) => {
    const input = document.querySelector('input[name="toggle-font-size-in-rem"]');
    if (input) { input.checked = true; observer.disconnect(); }
  }).observe(document, {childList: true, subtree: true});
}"""
RESTORED = "with the switch restored as checked, the table shows rem"


@check("font-size-restored-switch", "/docs#typography", oracle_bug={
    "fails": RESTORED,
    "reason": "FontsizeTable.jsx starts from useState(false) and never reads the switch, and React 19's hydration "
              "leaves a restored checked state alone (Firefox restores form state on a reload), so the oracle "
              "shows the px table under a checked switch and its first click unchecks the switch without "
              "changing the table; docs.js reads the switch at load"})
def font_size_restored_switch(page):
    """A switch the browser restores as checked gets the matching table. The "Display in rem"
    switch is checked (the rem table shows) and the page reloaded (location.reload(); a marker set
    on window is gone). Firefox restores the switch as checked; a browser that brings it back
    unchecked (Chrome) must show the px table with it, and then gets the same restoration from a
    preload script (the checked state set as the parser inserts the switch, before any script) on
    a fresh load. Either way, with the switch checked at load the table shows the root sizes as
    percentages and the multipliers, with no tooltips; one click unchecks the switch and restores
    the px table exactly as first loaded (the same tree)."""
    t0 = page.js(TABLE)
    page.eq("off on load over the px table", [t0["checked"], t0["cells"]], [False, [[list(c) for c in r] for r in px_rows()]])
    page.click(page.find(SWITCH))
    page.wait("rem values after checking", "S.querySelector('table#responsive-font-sizes tbody td').textContent === '100%'", 1)
    page.js("window.__bhMarker = 'before the reload'; setTimeout(() => location.reload(), 0); return true;")
    page.wait("the page reloaded", "window.__bhMarker === undefined && document.readyState === 'complete'", 15)
    page.wait_ready()
    t1 = page.js(TABLE)
    if t1["checked"]:
        page.note(f"{page.browser} restored the switch as checked on the reload")
    else:
        page.eq("brought back unchecked: the px table", t1["cells"], [[list(c) for c in r] for r in px_rows()])
        page.note(f"{page.browser} brought the switch back unchecked on the reload; restored as Firefox does, "
                  "by a preload script on a fresh load")
        page.sess.add_preload(RESTORE_SWITCH)   # removed after the check by the runner
        page.load(page.route)
        t1 = page.js(TABLE)
        page.eq("the switch arrives checked", t1["checked"], True)
    page.eq(RESTORED, t1["cells"], [[[c, None] for c in r] for r in rem_rows()])
    page.click(page.find(SWITCH))
    page.wait("px values after unchecking", "S.querySelector('table#responsive-font-sizes tbody td').textContent === '16px'", 1)
    t2 = page.js(TABLE)
    page.eq("switch unchecked", t2["checked"], False)
    page.eq("the px table exactly as first loaded", t2["tree"], t0["tree"])


THEAD = """
const sec = [...S.querySelectorAll("#content section")].find(s => (s.querySelector("h2") || {}).textContent?.startsWith("Color schemes"));
const th = sec.querySelector("table thead"), code = sec.querySelector(":scope > .code pre code, :scope > div.code pre code");
return {thead: th.getAttribute("data-theme"), code: code ? code.textContent : null, theme: document.documentElement.getAttribute("data-theme")};
"""


def code_for(theme):
    return f'<table>\n  <thead data-theme="{theme}">\n    ...\n  </thead>\n  <tbody>...</tbody>\n  <tfoot>...</tfoot>\n</table>'


def expect_thead(page, inverse, label):
    page.wait(f"{label}: thead data-theme={inverse}", "(() => { " + THEAD + " })().thead === arguments[0]", 1, args=(inverse,))
    page.eq(f"{label}: the sample reads data-theme=\"{inverse}\"", page.js(THEAD)["code"], code_for(inverse))


@check("table-inverse-thead", "/docs#table")
def table_inverse_thead(page):
    """In Table's "Color schemes" section the example table's thead takes the inverse of the
    page's scheme, and the code sample under it says so: on a light OS thead data-theme="dark" and
    the sample reads <thead data-theme="dark">; after the header toggle makes the page dark, both
    say "light"; toggled back, "dark" again."""
    expect_thead(page, "dark", "light OS")
    toggle = "body > header nav ul.icons a[aria-label$='dark mode']"
    page.click(toggle)
    expect_thead(page, "light", "page made dark")
    page.click(toggle)
    expect_thead(page, "dark", "page made light")


@check("table-inverse-thead-dark-os", "/docs#table", media="dark")
def table_inverse_thead_dark_os(page):
    """On a dark OS with nothing stored, Table's color-schemes example thead has
    data-theme="light" and its sample reads <thead data-theme="light">."""
    expect_thead(page, "light", "dark OS")


# The example links of /docs/link, in document order: every <a> inside an example (article.component)
# but the copy links of the code footers. That is the three of "Links example" and the three of
# "Active link example".
LINKS = """
return [...S.querySelectorAll("#content article.component a:not(.copy-to-clipboard)")].map(a =>
  [a, a.textContent, a.getAttribute("href"), a.closest("article").getAttribute("aria-label")]);
"""
LINK_TEXTS = [["Links example", "Primary"], ["Links example", "Secondary"], ["Links example", "Contrast"],
              ["Active link example", "Regular link"], ["Active link example", "Active link"],
              ["Active link example", "Regular link"]]

# Every click event on a link, in the capture phase, records whether it was canceled once its
# dispatch is over; a marker on window shows that the document was not replaced.
LINK_SPY = """
window.__bhClicks = [];
addEventListener("click", (e) => { const a = e.target.closest && e.target.closest("a");
  if (a) setTimeout(() => __bhClicks.push(e.defaultPrevented), 0); }, true);
window.__bhMarker = "kept";
"""

LINK_STATE = """
return {marker: window.__bhMarker, url: location.pathname + location.search + location.hash,
        history: history.length, scroll: Math.round(scrollY), clicks: window.__bhClicks.splice(0)};
"""


@check("link-examples", "/docs#link")
def link_examples(page):
    """Every example link of Link (Primary, Secondary and Contrast of "Links example", the two
    Regular links and the Active link of "Active link example": 6 links, each pointing at its own
    place: href="/docs/link" on routes, /docs or /docs#link on the one page) goes nowhere, by
    pointer and by keyboard. A real click on each, then Enter
    on each once focused, leaves the document (a marker set on window survives), the URL,
    history.length, the scroll position and the number of tabs as they were, and the click event
    is canceled (defaultPrevented)."""
    links = page.js(LINKS)
    page.eq("the six example links", [[a[3], a[1]] for a in links], LINK_TEXTS)
    page.eq("every example link points at the route itself", [self_href(page, a[0]) for a in links], [True] * 6,
            hrefs=[a[2] for a in links])
    page.js(LINK_SPY)
    url, history, tabs = page.url(), page.js("return history.length"), len(page.driver.window_handles)
    done = 0
    for how in ("click", "Enter"):
        for link, text, _, example in links:
            # Bring the link into view first, so the action itself scrolls nothing.
            page.js("const r = arguments[0].getBoundingClientRect();"
                    "if (r.top < 0 || r.bottom > innerHeight) arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", link)
            before = page.js("return Math.round(scrollY)")
            if how == "click":
                page.click(link, scroll=False)
            else:
                page.expect(f"{example}: {text!r} takes focus",
                            page.js("arguments[0].focus({preventScroll: true}); return document.activeElement === arguments[0];", link))
                page.key("ENTER")
            page.sleep(0.3)
            label = f"{example}: {how} on {text!r} goes nowhere"
            try:
                st = page.js(LINK_STATE)
            except Exception as e:   # the document went away: the link navigated
                page.expect(label, False, error=f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
            opened = len(page.driver.window_handles)
            page.expect(label, st["marker"] == "kept" and st["history"] == history
                        and st["scroll"] == before and st["clicks"] == [True] and opened == tabs,
                        url_before=url, history_before=history, scroll_before=before, tabs_before=tabs, tabs=opened, **st)
            page.url_kept(label, url)
            done += 1
    page.eq("every example link was clicked and activated with Enter", done, 12)
    page.note(f"{done} activations (6 clicks, 6 Enter presses), every click canceled, nothing navigated")
