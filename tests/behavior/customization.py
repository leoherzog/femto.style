"""Customization: the Colors section's color modal and palette download (01 §2, ColorModal and
docs.colors.jsx; colors.js in the static site).

Phase 4 describes femto.colors.css as femto 3 has it: the modal has five rows (the Sass variable row
is gone, and "CSS variable" reads "Custom property"), each family's main shade is the one
femto.colors.css gives the family's unshaded names (550 for red and fuchsia, where the oracle's
colors.json said 500), the shade buttons sit in a div.shades (the oracle's <main>) and the close
control is a button (the oracle's link). On routes the oracle's own markup and values are asserted,
so the same checks still hold the oracle."""
from behavior import COPY_SPY, check

GROUP = "customization"

ROUTE = "/docs#colors"
FAMILIES = ["red", "pink", "fuchsia", "purple", "violet", "indigo", "blue", "azure", "cyan", "jade", "green",
            "lime", "yellow", "amber", "pumpkin", "orange", "sand", "grey", "zinc", "slate"]
SHADES = ["50", "100", "150", "200", "250", "300", "350", "400", "450", "500", "550", "600", "650", "700",
          "750", "800", "850", "900", "950"]
# From the oracle's app/data/colors.json (tag remix-final): the colors these checks visit.
COLORS = {
    ("red", "50"): ("Salt Pebble", "#faeeeb", "rgb(250, 238, 235)"),
    ("red", "450"): ("Cascara", "#ee402e", "rgb(238, 64, 46)"),
    ("red", "500"): ("Shōjōhi Red", "#d93526", "rgb(217, 53, 38)"),
    ("red", "550"): ("Bloody Red", "#c52f21", "rgb(197, 47, 33)"),
    ("pink", "300"): ("Posy Petal", "#f8889e", "rgb(248, 136, 158)"),
    ("pink", "500"): ("Qing Dynasty Fire", "#d92662", "rgb(217, 38, 98)"),
    ("pink", "550"): ("Bright Rose", "#c72259", "rgb(199, 34, 89)"),
    ("fuchsia", "500"): ("Melodramatic Magenta", "#d9269d", "rgb(217, 38, 157)"),
    ("fuchsia", "550"): ("Loulou's Purple", "#c1208b", "rgb(193, 32, 139)"),
    ("slate", "500"): ("Chicory Flower", "#687899", "rgb(104, 120, 153)"),
    ("slate", "600"): ("Award Night", "#525f7a", "rgb(82, 95, 122)"),
    ("slate", "950"): ("Dark Rift", "#0e1118", "rgb(14, 17, 24)"),
}
# Each family's main hex, as the glow shows it: femto.colors.css's unshaded color from Phase 4, the
# oracle's colors.json "main" on routes.
MAIN = {"red": "#c52f21", "pink": "#d92662", "fuchsia": "#c1208b", "slate": "#525f7a"}
MAIN_ORACLE = {"red": "#d93526", "pink": "#d92662", "fuchsia": "#d9269d", "slate": "#525f7a"}
# sha256 of JSON.stringify(palette, null, 2), the palette being {family: {shade: hex}} over the 20
# families and 19 shades above, in that order (8,681 bytes): the oracle's Download content.
PALETTE_SHA256 = "73262eda105c487a7b2628946da06241f70e743d6eaaa6cda7d62a9b5b6a9636"

MODAL = """
const d = [...document.querySelectorAll("dialog.color")].find(x => x.open) || null;
const cls = [...document.documentElement.classList].filter(c => c.startsWith("modal-is-")).sort().join(" ");
if (!d) return {open: false, classes: cls, url: location.pathname + location.search + location.hash};
const a = d.querySelector(":scope > article"), h = a.querySelector(":scope > header");
return {open: true, classes: cls, header: h.className, family: h.querySelector("h3.color-family").textContent,
        name: h.querySelector("p.color-shade").textContent, glow: a.style.getPropertyValue("--femto-glowing-color").trim(),
        codes: [...a.querySelectorAll(".grid pre code")].map(c => c.textContent),
        labels: [...a.querySelectorAll(".grid > p")].map(p => p.textContent),
        focusInside: d.contains(document.activeElement), url: location.pathname + location.search + location.hash};
"""


def shade_button(family, shade):
    return f".color-families .family :is(main, .shades) > button.femto-background-{family}-{shade}"


def expect_color(page, family, shade, label):
    name, hexv, rgb = COLORS[(family, shade)]
    page.wait(f"{label}: the modal shows {family} {shade}",
              "(() => { const d = [...document.querySelectorAll('dialog.color')].find(x => x.open);"
              " return d && d.querySelector(':scope > article > header').classList.contains(arguments[0]); })()",
              1, args=(f"femto-background-{family}-{shade}",))
    m = page.js(MODAL)
    page.eq(f"{label}: header class", m["header"], f"femto-background-{family}-{shade}")
    page.eq(f"{label}: title", m["family"], f"{family.capitalize()} {shade}")
    page.eq(f"{label}: color name", m["name"], name)
    main = MAIN_ORACLE if page.layout == "routes" else MAIN
    page.eq(f"{label}: glow is the family's main color at 26 alpha", m["glow"], f"{main[family]}26")
    if page.layout == "routes":
        page.eq(f"{label}: the six labels", m["labels"], ["Hexadecimal color", "RGB color", "Sass variable",
                                                          "Color utility class", "Background utility class", "CSS variable"])
        page.eq(f"{label}: the six values", m["codes"], [hexv.upper(), rgb, f"${family}-{shade}", f"femto-color-{family}-{shade}",
                                                         f"femto-background-{family}-{shade}", f"var(--femto-color-{family}-{shade})"])
    else:
        page.eq(f"{label}: the five labels", m["labels"], ["Hexadecimal color", "RGB color", "Color utility class",
                                                           "Background utility class", "Custom property"])
        page.eq(f"{label}: the five values", m["codes"], [hexv.upper(), rgb, f"femto-color-{family}-{shade}",
                                                          f"femto-background-{family}-{shade}", f"var(--femto-color-{family}-{shade})"])
    return m


def expect_closed(page, label):
    page.wait(f"{label}: closed", "!document.querySelector('dialog.color[open]') && "
              "![...document.documentElement.classList].some(c => c.startsWith('modal-is-'))", 1.5)


# Where focus and the scroll positions are: the page's scrollY, and the open dialog's article
# scrollTop (null without an open dialog).
FOCUS = """
const d = [...document.querySelectorAll("dialog.color")].find(x => x.open) || null;
const a = d && d.querySelector(":scope > article");
return {inside: !!(d && d.contains(document.activeElement)),
        close: !!(d && document.activeElement === d.querySelector(":scope > article > header .close")),
        scrollY: Math.round(scrollY), articleTop: a ? Math.round(a.scrollTop) : null};
"""


def click_backdrop(page):
    """Click the open color dialog outside its article: a point on the dialog itself (or its
    ::backdrop, which hit-tests as the dialog)."""
    pt = page.js("""const d = document.querySelector("dialog.color[open]"), a = d.querySelector(":scope > article").getBoundingClientRect();
      for (const [x, y] of [[8, innerHeight / 2], [innerWidth - 8, innerHeight / 2], [innerWidth / 2, 8], [innerWidth / 2, innerHeight - 8]]) {
        const inA = x >= a.left && x <= a.right && y >= a.top && y <= a.bottom;
        if (!inA && document.elementFromPoint(x, y) === d) return [Math.round(x), Math.round(y)];
      }
      return null;""")
    page.expect("a point on the dialog outside its article", pt is not None)
    page.click_at(*pt)


@check("color-modal-open", ROUTE)
def color_modal_open(page):
    """A shade button (`.color-families .family .shades > button.femto-background-red-500`; the
    oracle's `main > button`) opens the
    color modal: one `dialog.color` is open, <html> has `modal-is-open`, and the dialog's header has
    class femto-background-red-500 and reads "Red 500" (non-breaking space) over the color's name
    ("Shōjōhi Red"); its article sets --femto-glowing-color to the family's main hex plus "26" (red
    550's #c52f21, femto.colors.css's unshaded red; the oracle's 500); the five rows read
    Hexadecimal color #D93526, RGB color rgb(217, 53, 38), Color utility class femto-color-red-500,
    Background utility class femto-background-red-500, Custom property var(--femto-color-red-500)
    (on routes the oracle's six, with Sass variable $red-500 and "CSS variable"). Escape closes it.
    A family header (Slate's `header.femto-background-slate`) opens the family's main shade, slate
    600."""
    page.eq("no open color dialog on load", page.js(MODAL)["open"], False)
    page.click(shade_button("red", "500"))
    m = expect_color(page, "red", "500", "red 500")
    page.expect("<html> has modal-is-open", "modal-is-open" in m["classes"].split(), classes=m["classes"])
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.click(".color-families .family > header.femto-background-slate")
    expect_color(page, "slate", "600", "Slate's header")
    page.key("ESCAPE")
    expect_closed(page, "Escape again")


@check("color-modal-arrows", ROUTE)
def color_modal_arrows(page):
    """With the color modal open, the arrow keys move through the 380 colors: Right is the next
    shade (red 500 to red 550), Left the previous, Down the next family at the same shade (pink
    500), Up the previous family (Up from red wraps to slate 500, Down from slate wraps back to red).
    Left from red 50 wraps to slate 950, the last color, and Right from slate 950 to red 50."""
    page.click(shade_button("red", "500"))
    expect_color(page, "red", "500", "opened")
    for key, (f, s) in (("ARROW_RIGHT", ("red", "550")), ("ARROW_LEFT", ("red", "500")), ("ARROW_LEFT", ("red", "450")),
                        ("ARROW_RIGHT", ("red", "500")), ("ARROW_DOWN", ("pink", "500")), ("ARROW_UP", ("red", "500")),
                        ("ARROW_UP", ("slate", "500")), ("ARROW_DOWN", ("red", "500"))):
        page.key(key)
        expect_color(page, f, s, f"{key} to {f} {s}")
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.click(shade_button("red", "50"))
    expect_color(page, "red", "50", "red 50")
    page.key("ARROW_LEFT")
    expect_color(page, "slate", "950", "Left wraps to slate 950")
    page.key("ARROW_RIGHT")
    expect_color(page, "red", "50", "Right wraps to red 50")


@check("color-modal-close", ROUTE)
def color_modal_close(page):
    """The color modal closes three ways, each leaving no open `dialog.color` and no modal-is-*
    class on <html> within 1.5 s: its close control (`header .close`: a button from Phase 4, the
    oracle's link), a click on the dialog outside its article (the backdrop), and Escape. A click
    inside the article (on its hgroup) leaves it open."""
    page.click(shade_button("red", "500"))
    expect_color(page, "red", "500", "opened")
    page.click("dialog.color[open] header .close")
    expect_closed(page, "close control")
    page.click(shade_button("pink", "500"))
    expect_color(page, "pink", "500", "reopened")
    page.click("dialog.color[open] header hgroup")
    page.sleep(0.6)
    page.eq("a click inside the article keeps it open", page.js(MODAL)["open"], True)
    click_backdrop(page)
    expect_closed(page, "backdrop")
    page.click(shade_button("slate", "950"))
    expect_color(page, "slate", "950", "reopened")
    page.key("ESCAPE")
    expect_closed(page, "Escape")


@check("color-modal-close-url", ROUTE,
       oracle_bug={"fails": "the close link leaves the URL as it was",
                   "reason": "the #close URL: the oracle's close link is <a href=\"#close\"> without preventDefault, so "
                             "closing pushes /docs/colors#close (PLAN.md, oracle-bug)"})
def color_modal_close_url(page):
    """Closing the color modal with its close control leaves the URL as it was (/docs/colors, or on the
    one page /docs with the hash of the section being read: no #close) and adds no history entry."""
    url, n = page.url(), page.js("return history.length")
    page.click(shade_button("red", "500"))
    expect_color(page, "red", "500", "opened")
    page.click("dialog.color[open] header .close")
    expect_closed(page, "close control")
    page.url_kept("the close link leaves the URL as it was", url)
    page.eq("no history entry", page.js("return history.length"), n)


@check("color-modal-focus", ROUTE,
       oracle_bug={"fails": "focus moves into the dialog",
                   "reason": "the oracle's color modal has no focus management (01 §2, ColorModal); the static "
                             "colors.js uses <dialog>'s own focus handling (PLAN.md, oracle-bug)"})
def color_modal_focus(page):
    """Keyboard use of the color modal: with a shade button focused, Enter opens the modal and focus
    moves into the open dialog; Escape closes it and focus returns to that button."""
    page.focus(shade_button("red", "500"))
    page.key("ENTER")
    expect_color(page, "red", "500", "opened with Enter")
    page.wait("focus moves into the dialog", "(() => { const d = document.querySelector('dialog.color[open]');"
              " return d && d.contains(document.activeElement); })()", 1)
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button("red", "500"),))


@check("color-modal-tab", ROUTE,
       oracle_bug={"fails": "Tab keeps focus inside the dialog",
                   "reason": "the oracle's color modal has no focus management (01 §2, ColorModal): Tab moves focus to "
                             "the shade buttons behind it; the static colors.js keeps focus on the dialog's close link, "
                             "as a modal <dialog> would (PLAN.md, oracle-bug)"})
def color_modal_tab(page):
    """Keyboard use of the open color modal (Enter on red 500's shade button): Tab, then Shift+Tab,
    each leave the page's scroll position (scrollY) as it was and keep focus inside the open dialog;
    Escape then closes it with the page still at that position and focus back on the button."""
    page.focus(shade_button("red", "500"))
    y = page.js("return Math.round(scrollY)")
    page.key("ENTER")
    expect_color(page, "red", "500", "opened with Enter")
    page.key("TAB")
    page.sleep(0.2)
    s = page.js(FOCUS)
    page.eq("Tab leaves the page where it was", s["scrollY"], y)
    page.expect("Tab keeps focus inside the dialog", s["inside"])
    page.tab(shift=True)
    page.sleep(0.2)
    s = page.js(FOCUS)
    page.eq("Shift+Tab leaves the page where it was", s["scrollY"], y)
    page.expect("Shift+Tab keeps focus inside the dialog", s["inside"])
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.sleep(0.2)
    page.eq("closing leaves the page where it was", page.js(FOCUS)["scrollY"], y)
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button("red", "500"),))


@check("color-modal-arrows-small", ROUTE, width=375, height=480)
def color_modal_arrows_small(page):
    """On a short viewport (375 x 480), where the open color modal's article overflows and can
    scroll, the arrow keys only change the color: opened from red 500's shade button, Down, Down,
    Right and Up show pink 500, fuchsia 500, fuchsia 550 and pink 550, and after each key the
    article's scrollTop is still 0 and the page's scrollY is unchanged."""
    page.click(shade_button("red", "500"))
    expect_color(page, "red", "500", "opened")
    s = page.js(FOCUS)
    page.expect("the article overflows", page.js("const a = document.querySelector('dialog.color[open] > article');"
                                                " return a.scrollHeight > a.clientHeight"))
    y = s["scrollY"]
    for key, (f, sh) in (("ARROW_DOWN", ("pink", "500")), ("ARROW_DOWN", ("fuchsia", "500")),
                         ("ARROW_RIGHT", ("fuchsia", "550")), ("ARROW_UP", ("pink", "550"))):
        page.key(key)
        expect_color(page, f, sh, f"{key} to {f} {sh}")
        page.sleep(0.25)
        s = page.js(FOCUS)
        page.eq(f"{key} to {f} {sh}: the article does not scroll", s["articleTop"], 0)
        page.eq(f"{key} to {f} {sh}: the page does not scroll", s["scrollY"], y)


@check("color-modal-focus-small", ROUTE, width=375, height=480,
       oracle_bug={"fails": "focus moves to the close link",
                   "reason": "the oracle's color modal has no focus management (01 §2, ColorModal); the static "
                             "colors.js moves focus to the dialog's close link (PLAN.md, oracle-bug)"})
def color_modal_focus_small(page):
    """On a short viewport (375 x 480), where the open color modal's article overflows, Enter on
    pink 300's focused shade button opens the modal with focus on its close control (`header .close`),
    not on the scrollable article; Escape closes it and focus returns to the button."""
    page.focus(shade_button("pink", "300"))
    page.key("ENTER")
    expect_color(page, "pink", "300", "opened with Enter")
    page.wait("focus moves to the close link", "(() => { const d = document.querySelector('dialog.color[open]');"
              " return !!d && document.activeElement === d.querySelector(':scope > article > header .close'); })()", 1)
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button("pink", "300"),))


@check("color-modal-resize", ROUTE)
def color_modal_resize(page):
    """The open color modal's article follows the viewport's height (ColorModal.jsx, use100vh): its
    inline max-height is calc(<innerHeight>px - 2rem) on opening at 1300 x 900, and again after
    resizes to 1300 x 600 and 1300 x 760 while it stays open."""
    page.click(shade_button("red", "500"))
    page.wait("the modal opens", "!!document.querySelector('dialog.color[open]')", 1.5)
    for w, h in ((1300, 900), (1300, 600), (1300, 760)):
        if h != 900:
            page.resize(w, h)
        page.wait(f"max-height at {w} x {h}",
                  "(() => { const a = document.querySelector('dialog.color[open] > article');"
                  " return !!a && a.style.maxHeight.replace(/\\s+/g, '') === `calc(${innerHeight}px-2rem)`; })()", 1.5,
                  got=page.js("const a = document.querySelector('dialog.color[open] > article'); return a && a.style.maxHeight"))
    page.eq("still open", page.js(MODAL)["open"], True)


@check("palette-download", ROUTE)
def palette_download(page):
    """The palette Download link (`a[download="femto-color-palette.json"][role=button]`, text
    "Download the palette (JSON)" from Phase 4, the oracle's "Download" on routes) points at a same-origin resource (a blob: URL of this origin, or a path here) whose
    body is the palette JSON: 20 families of 19 shades, each a #rrggbb hex, red 500 being #d93526,
    two-space indented (the body, less trailing whitespace, equals JSON.stringify(parsed, null,
    2)), and with the SHA-256 of the oracle's own download."""
    r = page.ajs("""
      const a = document.querySelector('a[download="femto-color-palette.json"]');
      if (!a) return {missing: true};
      const href = a.getAttribute("href"), url = new URL(href, location.href);
      const sameOrigin = url.protocol === "blob:" ? new URL(url.pathname).origin === location.origin : url.origin === location.origin;
      const res = await fetch(url.href), text = await res.text();
      let parsed = null; try { parsed = JSON.parse(text); } catch (e) {}
      const canon = parsed ? JSON.stringify(parsed, null, 2) : null;
      const digest = canon ? [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canon)))]
        .map(b => b.toString(16).padStart(2, "0")).join("") : null;
      return {text: a.textContent.trim(), role: a.getAttribute("role"), href, sameOrigin, status: res.status,
              type: res.headers.get("content-type"), formatted: canon !== null && text.trimEnd() === canon, digest,
              families: parsed && Object.keys(parsed), shades: parsed && Object.values(parsed).map(f => Object.keys(f).length),
              red500: parsed && parsed.red && parsed.red["500"],
              hexes: parsed ? Object.values(parsed).every(f => Object.values(f).every(v => /^#[0-9a-f]{6}$/.test(v))) : false};""")
    page.expect("the Download link exists", not r.get("missing"))
    page.eq("its text", r["text"], "Download" if page.layout == "routes" else "Download the palette (JSON)")
    page.eq("role=button", r["role"], "button")
    page.expect("it points at this origin", r["sameOrigin"], href=r["href"])
    page.eq("the resource answers 200", r["status"], 200)
    page.eq("20 families in order", r["families"], FAMILIES)
    page.eq("19 shades each", r["shades"], [19] * 20)
    page.expect("every value is a #rrggbb hex", r["hexes"])
    page.eq("red 500", r["red500"], "#d93526")
    page.expect("two-space indented JSON", r["formatted"])
    page.eq("the oracle's palette, byte for byte once canonical", r["digest"], PALETTE_SHA256)


MODAL_FOCUS = r"""
const d = document.querySelector('dialog.color[open]');
const a = document.activeElement;
return {inside: !!d && d.contains(a), close: !!d && a === d.querySelector('header button.close'),
        copy: !!d && [...d.querySelectorAll('.grid .code > button')].indexOf(a)};
"""


@check("color-modal-tab-cycle", ROUTE, layouts=("one-page",),
       layout_reason="from Phase 4 the color modal's close control and copy controls are buttons in its tab order (the "
                     "oracle's close link and copy links take no keyboard focus), and colors.js cycles Tab through them")
def color_modal_tab_cycle(page):
    """In the open color modal (Enter on red 500's focused shade button), focus starts on the close
    button; Tab moves through the five copy buttons in order and wraps to the close button; Shift+Tab
    goes back to the last copy button; Enter on it copies its value, var(--femto-color-red-500); Escape
    closes the modal and focus returns to the shade button."""
    shade = shade_button("red", "500")
    page.js(COPY_SPY)
    page.focus(shade)
    page.key("ENTER")
    page.wait("the modal opens", "!!document.querySelector('dialog.color[open]')", 1.5)
    page.wait("focus is on the close button", "(() => { const d = document.querySelector('dialog.color[open]');"
              " return !!d && document.activeElement === d.querySelector('header button.close'); })()", 1)
    for i in range(5):
        page.key("TAB")
        page.eq(f"Tab {i + 1}: copy button {i + 1}", page.js(MODAL_FOCUS)["copy"], i)
    page.key("TAB")
    page.eq("Tab wraps to the close button", page.js(MODAL_FOCUS)["close"], True)
    page.tab(shift=True)
    page.eq("Shift+Tab: the last copy button", page.js(MODAL_FOCUS)["copy"], 4)
    page.js("window.__bhCopied.length = 0")
    page.key("ENTER")
    page.wait("Enter copies", "window.__bhCopied.length === 1", 1)
    page.eq("it copied the custom property", page.js("return window.__bhCopied[0].text"), "var(--femto-color-red-500)")
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade,))
