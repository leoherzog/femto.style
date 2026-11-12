"""Content: Typography's font-size table switch, Table's inverse thead and Link's example links
(the Remix site's FontsizeTable.jsx, docs.table.jsx and docs.link.jsx), the Media, code and lists
examples drawn by femto alone, and the Tokens table against the tokens on the page's root."""
from behavior import SNAPSHOT, check, self_href

GROUP = "content"

# The Remix site's fontSizesTableData (components/docs/FontsizeTable.jsx, tag remix-final).
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


@check("font-size-restored-switch", "/docs#typography")
def font_size_restored_switch(page):
    """A switch the browser restores as checked gets the matching table. The "Display in rem"
    switch is checked (the rem table shows) and the page reloaded (location.reload(); a marker set
    on window is gone). Firefox restores the switch as checked; a browser that brings it back
    unchecked (Chrome) must show the px table with it, and then gets the same restoration from a
    preload script (the checked state set as the parser inserts the switch, before any script) on
    a fresh load (Safari, which has no preload script, ends there). Either way, with the switch
    checked at load the table shows the root sizes as percentages and the multipliers, with no
    tooltips; one click unchecks the switch and restores the px table exactly as first loaded (the
    same tree)."""
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
        if page.browser == "safari":
            # No preload script without WebDriver BiDi; a switch Safari never restores needs no table.
            page.note("safari brought the switch back unchecked on the reload; the restored switch is Chrome's and "
                      "Firefox's (Safari has no preload script)")
            return
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
    toggle = "body > header nav button:has(> span[role=img][aria-label$='dark mode'])"   # the header's toggle button
    page.click(toggle)
    expect_thead(page, "light", "page made dark")
    page.click(toggle)
    expect_thead(page, "dark", "page made light")


@check("table-inverse-thead-dark-os", "/docs#table", media="dark")
def table_inverse_thead_dark_os(page):
    """On a dark OS with nothing stored, Table's color-schemes example thead has
    data-theme="light" and its sample reads <thead data-theme="light">."""
    expect_thead(page, "light", "dark OS")


# The example links of Link, in document order: every <a> inside an example (each of the section's
# articles is one) but the copy links of the code footers. That is the three of "Links example" and
# the three of the aria-current example: "Current link example" with a "Current link".
LINKS = """
return [...S.querySelectorAll("#content article a:not([data-copy-link])")].map(a =>
  [a, a.textContent, a.getAttribute("href"), a.closest("article").getAttribute("aria-label")]);
"""


LINK_TEXTS = [["Links example", "Primary"], ["Links example", "Secondary"], ["Links example", "Contrast"],
              ["Current link example", "Regular link"], ["Current link example", "Current link"],
              ["Current link example", "Regular link"]]   # [example label, link text] of the six links


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
    Regular links and the Current link of "Current link example": 6 links, each href="#", as its
    sample has it) goes nowhere, by pointer and by keyboard. A real click on each, then Enter
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


# The properties femto's media, figure, code, list and typography rules set, read from every element
# of the Media section's example cards (their code footers left out).
MEDIA_PROPS = ["display", "margin-top", "margin-right", "margin-bottom", "margin-left", "padding-top", "padding-right",
               "padding-bottom", "padding-left", "width", "height", "max-width", "min-width", "font-family", "font-size",
               "font-weight", "font-style", "line-height", "color", "background-color", "border-top-left-radius",
               "border-top-width", "border-top-style", "overflow-x", "overflow-y", "overflow-wrap", "vertical-align",
               "list-style-type", "fill", "text-decoration-line"]

# The same cards, footers removed, in an iframe whose document loads the page's femto stylesheets
# (and only those), each card given the page card's width and padding, so that its contents lay out
# alike. The iframe is as wide as the window, so the root font size steps at the same breakpoint.
MEDIA_STYLES = r"""
const props = arguments[0];
const arts = [...S.querySelectorAll("article[aria-label]")];
const pick = (el) => { const cs = getComputedStyle(el); return Object.fromEntries(props.map(p => [p, cs.getPropertyValue(p)])); };
const collect = (cards) => cards.map(a => [...a.querySelectorAll("*")].filter(e => !e.closest("footer.code")).map(e => [e.localName, pick(e)]));
await document.fonts.ready;
const sheets = [...document.querySelectorAll("link[rel=stylesheet]")].map(l => l.getAttribute("href")).filter(h => h.startsWith("/vendor/femto/"));
const theme = document.documentElement.getAttribute("data-theme");
const box = ["width", "padding-top", "padding-right", "padding-bottom", "padding-left"];
const cards = arts.map(a => {
  const c = a.cloneNode(true), cs = getComputedStyle(a);
  c.querySelector(":scope > footer.code")?.remove();
  c.style.cssText = box.map(p => `${p}: ${cs.getPropertyValue(p)}`).join("; ");
  return c.outerHTML;
}).join("");
const html = `<!DOCTYPE html><html lang="en"${theme ? ` data-theme="${theme}"` : ""}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark">${sheets.map(h => `<link rel="stylesheet" href="${h}">`).join("")}</head><body>${cards}</body></html>`;
const iframe = document.createElement("iframe");
iframe.style.cssText = `position: fixed; top: 0; left: 0; width: ${innerWidth}px; height: ${innerHeight}px; border: 0; visibility: hidden;`;
document.body.append(iframe);
await new Promise(res => { iframe.onload = res; iframe.srcdoc = html; });
const doc = iframe.contentDocument;
await Promise.all([...doc.querySelectorAll("link")].map(l => l.sheet ? null : new Promise(r => { l.onload = l.onerror = r; })));
await doc.fonts.ready;
await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
const a = collect(arts), b = collect([...doc.querySelectorAll("article")]);
iframe.remove();
const diffs = [];
a.forEach((els, i) => {
  if (els.length !== b[i].length) { diffs.push({card: arts[i].getAttribute("aria-label"), count: [els.length, b[i].length]}); return; }
  els.forEach(([name, st], k) => { for (const p of props) if (st[p] !== b[i][k][1][p]) diffs.push({card: arts[i].getAttribute("aria-label"), el: k + ":" + name, prop: p, page: st[p], femto: b[i][k][1][p]}); });
});
const img = S.querySelector('article[aria-label="Figure example"] img'), card = img.closest("article").getBoundingClientRect(), r = img.getBoundingClientRect();
const svgs = [...S.querySelectorAll('article[aria-label="Inline SVG example"] svg')].map(s => [getComputedStyle(s.querySelector("circle")).fill, getComputedStyle(s.parentElement).color, s.parentElement.localName]);
return {cards: arts.map(a => a.getAttribute("aria-label")), elements: a.flat().length, diffs: diffs.slice(0, 40), total: diffs.length,
        img: {width: r.width, height: r.height, left: r.left - card.left, right: card.right - r.right}, svgs,
        sheets, scrollWidth: document.documentElement.scrollWidth, innerWidth};
"""
MEDIA_CARDS = ["Figure example", "Inline SVG example", "Code block example", "Lists example"]


def media_femto(page):
    r = page.ajs(MEDIA_STYLES, MEDIA_PROPS)
    page.eq("the Media section's four example cards", r["cards"], MEDIA_CARDS)
    page.expect("the reference loads femto's stylesheets", "/vendor/femto/dist/femto.min.css" in r["sheets"], sheets=r["sheets"])
    page.note(f"compared {len(MEDIA_PROPS)} properties of {r['elements']} elements with a document of {', '.join(r['sheets'])} alone")
    page.eq("every element has femto's own computed styles", r["total"], 0, diffs=r["diffs"])
    img = r["img"]
    page.expect("the image fits inside its card", img["left"] >= 0 and img["right"] >= 0, **img)
    page.expect("the image keeps its 1200:630 ratio", abs(img["height"] - img["width"] * 630 / 1200) < 1, **img)
    page.eq("each inline SVG fills with its text's color (p, ins, del)", [[f == c, el] for f, c, el in r["svgs"]],
            [[True, "p"], [True, "ins"], [True, "del"]], svgs=r["svgs"])
    page.expect("the page does not scroll sideways", r["scrollWidth"] <= r["innerWidth"], scrollWidth=r["scrollWidth"], innerWidth=r["innerWidth"])


@check("media-femto", "/docs#media")
def media_femto_wide(page):
    """Media, code and lists shows femto's own look. Every element of its four example cards
    (Figure, Inline SVG, Code block and Lists; their code footers left out) has the computed display,
    margins, padding, size, fonts, colors, corner radius, overflow, vertical alignment, list style,
    fill and text decoration of the same markup in a document that loads only the page's femto
    stylesheets, in a card of the same width and padding: the site's own code-block styles never
    reach the plain <pre>, <code>, <samp> and <kbd>. The figure's 1200 x 630 image fits inside its
    card at that ratio, each inline SVG's circle fills with the color of the text around it (the
    paragraph's, <ins>'s and <del>'s), and the page does not scroll sideways."""
    media_femto(page)


@check("media-femto-small", "/docs#media", width=375, height=812, media="dark")
def media_femto_small(page):
    """As media-femto, at 375 x 812 with the OS in dark."""
    media_femto(page)


# The Tokens table: each group's header and its link, and each row's token, pair cell and text, with
# whether the token and its --femto-light-* and --femto-dark-* names have a value on <html>.
TOKENS_TABLE = r"""
const t = S.querySelector('div[role=region][aria-label="Tokens"] > table');
if (!t) return null;
const root = getComputedStyle(document.documentElement);
const has = (n) => root.getPropertyValue(n).trim() !== "";
const ids = [...document.querySelectorAll("#content > section > hgroup > h1[id]")].map(h => h.id);
return {groups: [...t.tBodies].map(b => { const a = b.rows[0].querySelector("th[scope=rowgroup] > a"); return a ? a.getAttribute("href") : null; }),
        ids,
        rows: [...t.tBodies].flatMap(b => [...b.rows].slice(1).map(r => {
          const n = r.cells[0].querySelector("code")?.textContent ?? "";
          return {n, pair: r.cells[1]?.textContent.trim(), setOn: /\bset (on|per)\b/.test(r.cells[0].textContent),
                  root: has(n), light: has(n.replace(/^--femto-/, "--femto-light-")), dark: has(n.replace(/^--femto-/, "--femto-dark-"))};
        }))};
"""


@check("tokens-table", "/docs#tokens")
def tokens_table(page):
    """The Tokens table (in div[role=region][aria-label=Tokens]) lists 149 distinct --femto-* tokens,
    grouped in row groups whose header links to a section of the page (#<a section id>). A
    row's Pair cell reads "Yes" exactly when <html> has a value for both its --femto-light-* and
    --femto-dark-* names (58 rows) and "No" when it has neither, and every token whose row does not
    say it is "set on" or "set per" elements has a value on <html>."""
    r = page.js(TOKENS_TABLE)
    page.expect("the Tokens table exists", r is not None)
    names = [x["n"] for x in r["rows"]]
    page.eq("149 tokens", len(names), 149)
    page.eq("no token twice", sorted(n for n in set(names) if names.count(n) > 1), [])
    page.eq("every token is a --femto-* name", [n for n in names if not n.startswith("--femto-") or n.startswith(("--femto-light-", "--femto-dark-"))], [])
    page.eq("every group header links to a section of the page", [g for g in r["groups"] if not (g or "").startswith("#") or g[1:] not in r["ids"]], [])
    page.eq("Pair is Yes exactly when both names of the pair have a value on <html>",
            [x["n"] for x in r["rows"] if x["pair"] != ("Yes" if x["light"] and x["dark"] else "No") or x["light"] != x["dark"]], [])
    page.eq("58 tokens with a pair", sum(x["pair"] == "Yes" for x in r["rows"]), 58)
    page.eq("every token not set on elements has a value on <html>", [x["n"] for x in r["rows"] if not x["setOn"] and not x["root"]], [])
    page.note(f"{len(names)} tokens in {len(r['groups'])} groups; {sum(not x['root'] for x in r['rows'])} set only on elements")
