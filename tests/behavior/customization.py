"""Customization: the Colors section's swatches, color modal and palette download (the Remix site's
ColorModal and docs.colors.jsx; colors.js in the static site).

The section describes femto.colors.css as femto 3 has it: the modal has five rows (Hexadecimal
color, RGB color, Color utility class, Background utility class, Custom property), each family's
main shade is the one femto.colors.css gives the family's unshaded names (550 for red and fuchsia),
the shade buttons sit in a div.shades and the close control is a button. Each family's shade buttons
are one Tab stop (a roving tabindex), and the arrow keys move between them as they move the modal's
color."""
import functools
import hashlib
import json
import re
from pathlib import Path

from behavior import COPY_SPY, check, expect_forced_focus, expect_name

GROUP = "customization"

ROUTE = "/docs#colors"
# The names of the colors these checks visit. They are the site's own, in colors.js (from the Remix
# site's app/data/colors.json): femto names no colors. The values come from femto (femto_palette).
NAMES = {
    ("red", "50"): "Salt Pebble",
    ("red", "100"): "Pale Shrimp",
    ("red", "450"): "Cascara",
    ("red", "500"): "Shōjōhi Red",
    ("red", "550"): "Bloody Red",
    ("red", "950"): "Bighorn Sheep",
    ("pink", "50"): "Pale Cherry Blossom",
    ("pink", "300"): "Posy Petal",
    ("pink", "500"): "Qing Dynasty Fire",
    ("pink", "550"): "Bright Rose",
    ("pink", "950"): "Ponzu Brown",
    ("fuchsia", "500"): "Melodramatic Magenta",
    ("fuchsia", "550"): "Loulou's Purple",
    ("slate", "500"): "Chicory Flower",
    ("slate", "600"): "Award Night",
    ("slate", "950"): "Dark Rift",
}


@functools.cache
def femto_palette():
    """femto's palette, read from the vendored femto.colors.css (site/vendor/femto/, which criterion 12
    pins to SOURCE's commit), the file criterion 13's drift check holds colors.js to: {family: {shade:
    hex}}, families in the file's order and shades ascending, and {family: main hex}, the family's
    unshaded --femto-color-<family>. A change of femto's colors then moves colors.js, the build's
    palette file and these checks together."""
    css = (Path(__file__).resolve().parents[2] / "site/vendor/femto/dist/femto.colors.css").read_text(encoding="utf-8")
    shaded = re.findall(r"--femto-color-([a-z]+)-(\d+)\s*:\s*(#[0-9a-fA-F]{6})\b", css)
    palette = {}
    for family, shade, hexv in shaded:
        palette.setdefault(family, {})[shade] = hexv.lower()
    palette = {f: dict(sorted(s.items(), key=lambda x: int(x[0]))) for f, s in palette.items()}
    main = {f: h.lower() for f, h in re.findall(r"--femto-color-([a-z]+)\s*:\s*(#[0-9a-fA-F]{6})\b", css)}
    return palette, main


def color(family, shade):
    """The name, hex and rgb() value the modal shows for a color."""
    hexv = femto_palette()[0][family][shade]
    return NAMES[(family, shade)], hexv, "rgb({}, {}, {})".format(*(int(hexv[i:i + 2], 16) for i in (1, 3, 5)))

MODAL = """
const d = [...document.querySelectorAll("dialog.color")].find(x => x.open) || null;
const cls = [...document.documentElement.classList].filter(c => c.startsWith("modal-is-")).sort().join(" ");
if (!d) return {open: false, classes: cls, url: location.pathname + location.search + location.hash};
const a = d.querySelector(":scope > article"), h = a.querySelector(":scope > header");
return {open: true, classes: cls, header: h.className, family: h.querySelector("h3.color-family").textContent,
        name: h.querySelector("p.color-shade").textContent, glow: a.style.getPropertyValue("--site-glowing-color").trim(),
        codes: [...a.querySelectorAll(".grid pre code")].map(c => c.textContent),
        labels: [...a.querySelectorAll(".grid > p")].map(p => p.textContent),
        focusInside: d.contains(document.activeElement), url: location.pathname + location.search + location.hash};
"""


def shade_button(family, shade):
    return f".color-families .family > .shades > button.femto-background-{family}-{shade}"


def expect_color(page, family, shade, label):
    name, hexv, rgb = color(family, shade)
    page.wait(f"{label}: the modal shows {family} {shade}",
              "(() => { const d = [...document.querySelectorAll('dialog.color')].find(x => x.open);"
              " return d && d.querySelector(':scope > article > header').classList.contains(arguments[0]); })()",
              1, args=(f"femto-background-{family}-{shade}",))
    m = page.js(MODAL)
    page.eq(f"{label}: header class", m["header"], f"femto-background-{family}-{shade}")
    page.eq(f"{label}: title", m["family"], f"{family.capitalize()} {shade}")
    page.eq(f"{label}: color name", m["name"], name)
    page.eq(f"{label}: glow is the family's main color at 26 alpha", m["glow"], f"{femto_palette()[1][family]}26")
    page.eq(f"{label}: the five labels", m["labels"], ["Hexadecimal color", "RGB color", "Color utility class",
                                                       "Background utility class", "Custom property"])
    page.eq(f"{label}: the five values", m["codes"], [hexv.upper(), rgb, f"femto-color-{family}-{shade}",
                                                      f"femto-background-{family}-{shade}", f"var(--femto-color-{family}-{shade})"])
    return m


def expect_modal(page, label):
    """The open color dialog is a true modal (showModal(): it matches :modal) with focus inside it."""
    page.eq(f"{label}: the dialog is modal, with focus inside it", page.js(
        "const d = document.querySelector('dialog.color[open]');"
        "return !!d && [d.matches(':modal'), d.contains(document.activeElement)];"), [True, True])


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
    """A shade button (`.color-families .family .shades > button.femto-background-red-500`) opens
    the color modal: one `dialog.color` is open, <html> has `modal-is-open`, and the dialog's header has
    class femto-background-red-500 and reads "Red 500" (non-breaking space) over the color's name
    ("Shōjōhi Red"); its article sets --site-glowing-color to the family's main hex plus "26"
    (femto.colors.css's unshaded --femto-color-red, red 550's #c52f21 on 2026-11-09); the five rows
    read Hexadecimal color (femto.colors.css's --femto-color-red-500 in capitals, #D93526 that day),
    RGB color (the same in rgb(), rgb(217, 53, 38)), Color utility class femto-color-red-500,
    Background utility class femto-background-red-500, Custom property var(--femto-color-red-500).
    Escape closes it.
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
    """The color modal, a true modal (it matches :modal, with focus inside it), closes three ways,
    each leaving no open `dialog.color` and no modal-is-* class on <html> within 1.5 s: its close
    control (`header .close`: a button), a click on the dialog outside its article (the backdrop),
    and Escape (the dialog's cancel, which runs the animated close). A click inside the article (on
    its hgroup) leaves it open."""
    page.click(shade_button("red", "500"))
    expect_color(page, "red", "500", "opened")
    expect_modal(page, "opened")
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


@check("color-modal-close-url", ROUTE)
def color_modal_close_url(page):
    """Closing the color modal with its close control leaves the URL as it was (/docs, with the hash
    of the section being read: no #close) and adds no history entry."""
    url, n = page.url(), page.js("return history.length")
    page.click(shade_button("red", "500"))
    expect_color(page, "red", "500", "opened")
    page.click("dialog.color[open] header .close")
    expect_closed(page, "close control")
    page.url_kept("the close button leaves the URL as it was", url)
    page.eq("no history entry", page.js("return history.length"), n)


@check("color-modal-focus", ROUTE)
def color_modal_focus(page):
    """Keyboard use of the color modal: with a shade button focused, Enter opens the modal, a true
    modal (it matches :modal), and focus moves into the open dialog; Escape closes it and focus
    returns to that button (the swatch of the color the modal shows)."""
    page.focus(shade_button("red", "500"))
    page.key("ENTER")
    expect_color(page, "red", "500", "opened with Enter")
    page.wait("focus moves into the dialog", "(() => { const d = document.querySelector('dialog.color[open]');"
              " return d && d.contains(document.activeElement); })()", 1)
    expect_modal(page, "opened with Enter")
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button("red", "500"),))


@check("color-modal-tab", ROUTE)
def color_modal_tab(page):
    """Keyboard use of the open color modal (Enter on red 500's shade button): the page behind is
    inert (showModal()), so the shade button cannot take focus while the dialog is open; Tab, then
    Shift+Tab, each leave the page's scroll position (scrollY) as it was and keep focus inside the
    open dialog; Escape then closes it with the page still at that position and focus back on the
    button."""
    page.focus(shade_button("red", "500"))
    y = page.js("return Math.round(scrollY)")
    page.key("ENTER")
    expect_color(page, "red", "500", "opened with Enter")
    expect_modal(page, "opened with Enter")
    page.eq("the page behind is inert: the shade button cannot take focus", page.focus(shade_button("red", "500")), False)
    page.expect("focus stays in the dialog", page.js(FOCUS)["inside"])
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


@check("color-modal-focus-small", ROUTE, width=375, height=480)
def color_modal_focus_small(page):
    """On a short viewport (375 x 480), where the open color modal's article overflows, Enter on
    pink 300's focused shade button opens the modal with focus on its close control (`header .close`),
    not on the scrollable article; Escape closes it and focus returns to the button."""
    page.focus(shade_button("pink", "300"))
    page.key("ENTER")
    expect_color(page, "pink", "300", "opened with Enter")
    page.wait("focus moves to the close button", "(() => { const d = document.querySelector('dialog.color[open]');"
              " return !!d && document.activeElement === d.querySelector(':scope > article > header .close'); })()", 1)
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button("pink", "300"),))


@check("color-modal-resize", ROUTE)
def color_modal_resize(page):
    """The open color modal's article follows the viewport's height through femto's own modal CSS
    (dialog > article, max-height: calc(100svh - --femto-spacing * 2); no inline style): its
    computed max-height is innerHeight minus two femto spacings (within 0.5 px) on opening at 1300 x
    900, and again after resizes to 1300 x 600 and 1300 x 760 while it stays open, and its bottom is
    inside the viewport."""
    page.click(shade_button("red", "500"))
    page.wait("the modal opens", "!!document.querySelector('dialog.color[open]')", 1.5)
    for w, h in ((1300, 900), (1300, 600), (1300, 760)):
        if h != 900:
            page.resize(w, h)
            page.sleep(0.3)
        page.wait(f"at {w} x {h}: the article's max-height is innerHeight minus two femto spacings",
                  "(() => { const a = document.querySelector('dialog.color[open] > article'); if (!a) return false;"
                  " const p = document.createElement('div'); p.style.cssText = 'position: absolute; visibility: hidden; width: var(--femto-spacing)';"
                  " a.append(p); const s = p.getBoundingClientRect().width; p.remove();"
                  " return Math.abs(parseFloat(getComputedStyle(a).maxHeight) - (innerHeight - 2 * s)) < 0.5"
                  " && a.getBoundingClientRect().bottom <= innerHeight + 0.5; })()", 1.5,
                  got=page.js("const a = document.querySelector('dialog.color[open] > article');"
                              " return a && [a.style.maxHeight, getComputedStyle(a).maxHeight, a.getBoundingClientRect().bottom, innerHeight]"))
    page.eq("still open", page.js(MODAL)["open"], True)


@check("palette-download", ROUTE)
def palette_download(page):
    """The palette Download link (`a[download="femto-color-palette.json"][role=button]`, text
    "Download the palette (JSON)") points at a same-origin resource (a blob: URL of this origin, or a path here) whose
    body is femto's palette as JSON: the vendored femto.colors.css's families in its order (20 on
    2026-11-09), each with its shades ascending (19), and each value that family and shade's
    --femto-color-<family>-<shade> (red 500 #d93526 that day); two-space indented (the body, less
    trailing whitespace, equals JSON.stringify(parsed, null, 2)), so its SHA-256 is that of
    femto's palette written the same way. The Remix site's download had the same bytes on
    2026-11-09."""
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
              palette: parsed, families: parsed && Object.keys(parsed),
              shades: parsed && Object.values(parsed).map(f => Object.keys(f)),
              hexes: parsed ? Object.values(parsed).every(f => Object.values(f).every(v => /^#[0-9a-f]{6}$/.test(v))) : false};""")
    want, _ = femto_palette()
    page.expect("the Download link exists", not r.get("missing"))
    page.eq("its text", r["text"], "Download the palette (JSON)")
    page.eq("role=button", r["role"], "button")
    page.expect("it points at this origin", r["sameOrigin"], href=r["href"])
    page.eq("the resource answers 200", r["status"], 200)
    page.eq("femto.colors.css's families, in order", r["families"], list(want))
    page.eq("each family's shades, in order", r["shades"], [list(s) for s in want.values()])
    page.expect("every value is a #rrggbb hex", r["hexes"])
    got = r["palette"] or {}
    wrong = [f"{f} {s}: {got.get(f, {}).get(s)}, femto.colors.css {h}" for f, shades in want.items() for s, h in shades.items()
             if got.get(f, {}).get(s) != h]
    page.eq("every color is femto.colors.css's", len(wrong), 0, wrong=wrong[:12])
    page.expect("two-space indented JSON", r["formatted"])
    page.eq("the palette, byte for byte once canonical", r["digest"],
            hashlib.sha256(json.dumps(want, indent=2).encode()).hexdigest())


MODAL_FOCUS = r"""
const d = document.querySelector('dialog.color[open]');
const a = document.activeElement;
return {inside: !!d && d.contains(a), close: !!d && a === d.querySelector('header button.close'),
        copy: !!d && [...d.querySelectorAll('.grid .code > button')].indexOf(a), body: a === document.body || a === null,
        active: a ? a.outerHTML.slice(0, 80) : null};
"""
# The color modal's copy buttons in order, each named by its row (colors.js: the icon's aria-label,
# which the button's aria-labelledby points at).
MODAL_COPY_NAMES = ["Copy hexadecimal color", "Copy RGB color", "Copy color utility class", "Copy background utility class",
                    "Copy custom property"]


# The page's copy status regions (site.js keeps one): how many, where the first one is, and its text.
STATUS_PLACE = """
const d = document.querySelector('dialog.color[open]');
const r = [...document.querySelectorAll('[role=status]')];
return {regions: r.length, text: r[0]?.textContent ?? null,
        parent: !r[0] ? null : d && r[0].parentElement === d ? 'the dialog' : r[0].parentElement === document.body ? 'body'
          : r[0].parentElement.localName};
"""


def expect_status_heard(page, label):
    """While the color dialog is shown with showModal(), the rest of the page is out of the
    accessibility tree, so the copy status region must sit inside the dialog to be heard. In
    Chrome, its accessibility tree (CDP Accessibility.getPartialAXTree) also has the region as a
    status that is not ignored."""
    page.wait(f"{label}: the page's one status region says Copied",
              "(() => { const r = document.querySelectorAll('[role=status]'); return r.length === 1 && r[0].textContent === 'Copied'; })()",
              1, got=page.js(STATUS_PLACE))
    if page.browser == "chrome":
        found = page.driver.execute_cdp_cmd("Runtime.evaluate", {"expression": "document.querySelector('[role=status]')"})
        tree = page.driver.execute_cdp_cmd("Accessibility.getPartialAXTree",
                                           {"objectId": found["result"]["objectId"], "fetchRelatives": False})
        node = tree["nodes"][0]
        page.eq(f"{label}: Chrome's accessibility tree has the region as a status, not ignored",
                {"ignored": node.get("ignored"), "role": node.get("role", {}).get("value")}, {"ignored": False, "role": "status"},
                ignoredReasons=[r.get("name") for r in node.get("ignoredReasons", [])])
    got = page.js(STATUS_PLACE)
    page.eq(f"{label}: the region is in the dialog", got["parent"], "the dialog", got=got)


@check("color-modal-tab-cycle", ROUTE)
def color_modal_tab_cycle(page):
    """In the open color modal (Enter on red 500's focused shade button), a true modal, focus starts
    on the close button; Tab moves through the five copy buttons in order, and Enter on the last
    copies its value, var(--femto-color-red-500), and the page's one copy status region, which
    site.js moves into the dialog while it is shown (the page behind is out of the accessibility
    tree), says Copied there; in Chrome the accessibility tree has it as a status, not ignored. Tab
    past the last copy button never reaches the
    page behind, which is inert: focus stays in the dialog or leaves the document for the browser's
    own controls (activeElement <body>, as every modal dialog lets it), and the next Tab or two bring
    it back into the dialog; three Shift+Tabs from there never reach the page behind either. Escape
    then closes the modal, the region is back in <body>, and focus returns to the shade button.
    Each button's computed name (the browser's, WebDriver Get Computed Label) is its icon's label
    alone, as colors.js writes it: the
    close button "Close", the copy buttons, in order, "Copy hexadecimal color", "Copy RGB color",
    "Copy color utility class", "Copy background utility class" and "Copy custom property", the last
    one also while its check ✓ shows after the copy (no tooltip text joins any of them). The copy
    comes before focus leaves the document: headless Firefox, once focus has been out to its
    controls, no longer turns Enter on a button into a click."""
    shade = shade_button("red", "500")
    page.js(COPY_SPY)
    page.focus(shade)
    page.key("ENTER")
    page.wait("the modal opens", "!!document.querySelector('dialog.color[open]')", 1.5)
    page.wait("focus is on the close button", "(() => { const d = document.querySelector('dialog.color[open]');"
              " return !!d && document.activeElement === d.querySelector('header button.close'); })()", 1)
    expect_modal(page, "opened with Enter")
    expect_name(page, "the close button's computed name", page.js("return document.activeElement"), "Close")
    for i in range(5):
        page.key("TAB")
        page.eq(f"Tab {i + 1}: copy button {i + 1}", page.js(MODAL_FOCUS)["copy"], i)
        expect_name(page, f"Tab {i + 1}: copy button {i + 1}'s computed name", page.js("return document.activeElement"),
                    MODAL_COPY_NAMES[i])
    page.js("window.__bhCopied.length = 0")
    page.key("ENTER")
    page.wait("Enter copies", "window.__bhCopied.length === 1", 1)
    page.eq("it copied the custom property", page.js("return window.__bhCopied[0].text"), "var(--femto-color-red-500)")
    expect_status_heard(page, "Enter's copy")
    icon = "return document.activeElement.querySelector(':scope > span[role=img]')?.textContent"
    page.eq("the check shows", page.js(icon), "✓")
    expect_name(page, "the check keeps the last copy button's computed name", page.js("return document.activeElement"),
                MODAL_COPY_NAMES[4])
    page.eq("the check still shows (the name was read while it did)", page.js(icon), "✓")
    page.key("TAB")
    f = page.js(MODAL_FOCUS)
    page.expect("Tab past the last copy button: focus stays in the dialog or leaves the document, never the page behind",
                f["inside"] or f["body"], **f)
    for _ in range(2):
        if f["inside"]:
            break
        page.key("TAB")
        f = page.js(MODAL_FOCUS)
    page.expect("Tab brings focus back into the dialog", f["inside"], **f)
    for n in range(3):
        page.tab(shift=True)
        f = page.js(MODAL_FOCUS)
        page.expect(f"Shift+Tab {n + 1}: focus stays in the dialog or leaves the document, never the page behind",
                    f["inside"] or f["body"], **f)
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    got = page.js(STATUS_PLACE)
    page.eq("after the close, the one status region is back in <body>", {"regions": got["regions"], "parent": got["parent"]},
            {"regions": 1, "parent": "body"})
    page.wait("focus returns to the shade button", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade,))


# -- the swatches: one Tab stop per family (colors.js's roving tabindex) ----------------------------

# Each family's shade buttons (its div.shades), in document order: the div's role and aria-label, the
# shades whose button is in the tab order (tabIndex 0), and how many buttons are out of it.
TOOLBARS = """
return [...document.querySelectorAll(".color-families .family > .shades")].map(g => {
  const buttons = [...g.querySelectorAll(":scope > button")];
  return {role: g.getAttribute("role"), label: g.getAttribute("aria-label"),
          stops: buttons.filter(b => b.tabIndex === 0).map(b => b.textContent.trim()),
          out: buttons.filter(b => b.tabIndex !== 0).length};
});
"""
# The focused element: a shade button's family and shade, whether it is in the tab order and how many
# of its family's buttons are; anything else by its markup, and whether it precedes or follows the
# grid in document order.
FOCUSED = r"""
const a = document.activeElement, grid = document.querySelector(".color-families");
const m = a && a.matches(".color-families .family > .shades > button")
  ? /(?:^|\s)femto-background-([a-z]+)-(\d+)(?:\s|$)/.exec(a.className) : null;
if (m) return {swatch: `${m[1]} ${m[2]}`, stop: a.tabIndex === 0,
               stops: [...a.parentElement.querySelectorAll(":scope > button")].filter(b => b.tabIndex === 0).length};
const pos = a && a !== document.body ? grid.compareDocumentPosition(a) : 0;
return {swatch: null, active: a ? a.outerHTML.slice(0, 80) : null, inGrid: !!(a && grid.contains(a)),
        before: !!(pos & Node.DOCUMENT_POSITION_PRECEDING), after: !!(pos & Node.DOCUMENT_POSITION_FOLLOWING)};
"""


def families():
    return list(femto_palette()[0])


def expect_swatch(page, family, shade, label):
    """Focus is on the family's shade button, which is the family's one Tab stop."""
    page.wait(f"{label}: focus is on {family} {shade}", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button(family, shade),), got=page.js(FOCUSED))
    at = page.js(FOCUSED)
    page.eq(f"{label}: {family} {shade} is {family}'s one Tab stop", [at["stop"], at["stops"]], [True, 1])


@check("color-grid-tab", ROUTE)
def color_grid_tab(page):
    """Each color family is one Tab stop: on load every family's shade buttons (`.family > .shades`)
    are a `role=toolbar` (ARIA's set of buttons with one Tab stop; not role=group, which femto
    styles as its Group component) named by the family (aria-label "Red", ..., "Slate",
    femto.colors.css's families in order; the browser's computed name of the first and last toolbar
    is "Red" and "Slate"), with only its first shade, 50, in the tab order (tabIndex 0) and its 18
    others out of it (tabIndex -1). From red 50's focused button, Tab goes to pink 50, then each next
    family's 50 to slate 50 (19 presses), and the 20th Tab leaves the grid for an element after it;
    Shift+Tab comes back to slate 50, 19 more go back through each family's 50 to red 50, and the
    next leaves the grid for an element before it."""
    names = families()
    toolbars = page.js(TOOLBARS)
    page.eq("each family's toolbar and its name", [(t["role"], t["label"]) for t in toolbars],
            [("toolbar", f.capitalize()) for f in names])
    page.eq("each family's one Tab stop is its 50", [t["stops"] for t in toolbars], [["50"]] * len(names))
    page.eq("each family's 18 other shades are out of the tab order", [t["out"] for t in toolbars], [18] * len(names))
    for i, f in ((0, names[0]), (len(names) - 1, names[-1])):
        toolbar = page.js("return document.querySelectorAll('.color-families .family > .shades')[arguments[0]]", i)
        expect_name(page, f"the {f} toolbar's computed name", toolbar, f.capitalize())
    page.focus(shade_button(names[0], "50"))
    expect_swatch(page, names[0], "50", "focused")
    for f in names[1:]:
        page.tab()
        expect_swatch(page, f, "50", f"Tab to {f}")
    page.tab()
    at = page.js(FOCUSED)
    page.expect("the 20th Tab leaves the grid for an element after it", not at["inGrid"] and at["after"], **at)
    page.tab(shift=True)
    expect_swatch(page, names[-1], "50", "Shift+Tab back")
    for f in reversed(names[:-1]):
        page.tab(shift=True)
        expect_swatch(page, f, "50", f"Shift+Tab to {f}")
    page.tab(shift=True)
    at = page.js(FOCUSED)
    page.expect("Shift+Tab from red 50 leaves the grid for an element before it", not at["inGrid"] and at["before"], **at)


# Every keydown the page has seen, from now on: its key and whether the page cancelled its default
# action (read at window, after the page's own listeners).
KEYS = "window.__bhKeys = []; addEventListener('keydown', e => __bhKeys.push([e.key, e.defaultPrevented])); return true;"
DOM_KEY = {"ARROW_RIGHT": "ArrowRight", "ARROW_LEFT": "ArrowLeft", "ARROW_DOWN": "ArrowDown", "ARROW_UP": "ArrowUp",
           "HOME": "Home", "END": "End"}
IN_VIEW = """const r = document.querySelector(arguments[0]).getBoundingClientRect();
  return r.top >= 0 && r.bottom <= innerHeight && r.left >= 0 && r.right <= innerWidth;"""
# The focused element's focus ring: whether it matches :focus-visible, whether its computed
# box-shadow has a layer with a spread wider than 0px (femto's ring is "0 0 0 <outline width>"), and
# the best contrast between a ring layer's color and the element's background (WCAG 1.4.11 asks 3:1
# of a focus indicator; a translucent layer counts as its color over that background).
RING = r"""const a = document.activeElement, cs = getComputedStyle(a), shadow = cs.boxShadow;
  const spread = (layer) => { const px = layer.match(/-?[\d.]+px/g) || []; return px.length >= 4 ? parseFloat(px[3]) : 0; };
  const rgba = (c) => { const n = (c.match(/[\d.]+/g) || []).map(Number); return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1]; };
  const lum = ([r, g, b]) => [r, g, b].map(v => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; })
    .reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0);
  const bg = rgba(cs.backgroundColor);
  const layers = shadow.split(/,(?![^(]*\))/).filter(l => spread(l) > 0);
  const contrast = layers.map(l => { const c = rgba(l.match(/rgba?\([^)]*\)/)?.[0] ?? cs.color), k = c[3];
    const over = [0, 1, 2].map(i => c[i] * k + bg[i] * (1 - k)); const [x, y] = [lum(over), lum(bg)].sort((m, n) => n - m);
    return Math.round((x + 0.05) / (y + 0.05) * 100) / 100; });
  return {visible: a.matches(":focus-visible"), shadow, ring: layers.length > 0, contrast: Math.max(0, ...contrast)};"""


def expect_ring(page, label):
    """The focused swatch draws its focus ring, in a color with 3:1 contrast against the swatch."""
    page.wait(f"{label}: the swatch draws its focus ring, 3:1 against it (once its box-shadow transition has run)",
              f"(() => {{ const r = (() => {{ {RING} }})(); return r.visible && r.ring && r.contrast >= 3; }})()", 1,
              got=page.js(RING))


@check("color-grid-arrows", ROUTE)
def color_grid_arrows(page):
    """With a swatch focused, the arrow keys move focus as they move the color modal's color, and
    Home and End to the family's first and last shade. From red 50: Right red 100, Left red 50,
    Left slate 950 (wrapping to the last color), Right red 50 (wrapping back), Down pink 50, Up red
    50, Up slate 50 (wrapping), Down red 50, End red 950, Home red 50, End red 950, Right pink 50.
    Each key's default action is cancelled (so it never scrolls the page), the page keeps its
    scrollY whenever the swatch it moves to was already in view, and the swatch it moves to is its
    family's one Tab stop and draws a focus ring (it matches :focus-visible, and its computed
    box-shadow has a ring wider than 0px, one of whose colors has 3:1 contrast against the swatch,
    WCAG 1.4.11). Each family keeps its own stop: from pink 50, Shift+Tab
    goes to red 950, the shade red was left on, and Tab back to pink 50. In forced colors (Chrome),
    which drop the box-shadow ring, the focused pink 50 still shows an outline."""
    page.focus(shade_button("red", "50"))
    expect_swatch(page, "red", "50", "focused")
    page.js(KEYS)
    for key, (f, s) in (("ARROW_RIGHT", ("red", "100")), ("ARROW_LEFT", ("red", "50")), ("ARROW_LEFT", ("slate", "950")),
                        ("ARROW_RIGHT", ("red", "50")), ("ARROW_DOWN", ("pink", "50")), ("ARROW_UP", ("red", "50")),
                        ("ARROW_UP", ("slate", "50")), ("ARROW_DOWN", ("red", "50")), ("END", ("red", "950")),
                        ("HOME", ("red", "50")), ("END", ("red", "950")), ("ARROW_RIGHT", ("pink", "50"))):
        seen = page.js(IN_VIEW, shade_button(f, s))
        y = page.js("return Math.round(scrollY)")
        page.js("window.__bhKeys.length = 0")
        page.key(key)
        expect_swatch(page, f, s, f"{key} to {f} {s}")
        page.eq(f"{key} to {f} {s}: one keydown, its default action cancelled", page.js("return window.__bhKeys"),
                [[DOM_KEY[key], True]])
        expect_ring(page, f"{key} to {f} {s}")
        if seen:
            page.sleep(0.1)
            page.eq(f"{key} to {f} {s}, already in view: the page does not scroll", page.js("return Math.round(scrollY)"), y)
    page.tab(shift=True)
    expect_swatch(page, "red", "950", "Shift+Tab from pink 50 goes to red's stop")
    page.tab()
    expect_swatch(page, "pink", "50", "Tab goes back to pink's stop")
    expect_forced_focus(page, "pink 50")


@check("color-grid-ring-dark", ROUTE, media="dark")
def color_grid_ring_dark(page):
    """In the dark scheme, where femto's own translucent ring is faint on the dark shades, every
    swatch the keyboard reaches draws a ring one of whose colors has 3:1 contrast against it: from
    red 50, Down through the 20 families' 50 and back to red, then End and Down through the 20
    families' 950."""
    page.focus(shade_button("red", "50"))
    page.key("ARROW_RIGHT")
    page.key("ARROW_LEFT")
    expect_ring(page, "red 50")
    families = [t["label"].lower() for t in page.js(TOOLBARS)]
    for shade in ("50", "950"):
        if shade == "950":
            page.key("END")
            expect_swatch(page, "red", "950", "End")
            expect_ring(page, "red 950")
        for family in families[1:] + families[:1]:
            page.key("ARROW_DOWN")
            expect_swatch(page, family, shade, f"Down to {family} {shade}")
            expect_ring(page, f"{family} {shade}")


@check("color-grid-modal", ROUTE)
def color_grid_modal(page):
    """The color modal opens on the focused swatch and gives focus back to the swatch of the color it
    shows when it closes. From red 50's focused button, End then Enter opens it on red 950, and
    Escape closes it with focus on red 950. Enter opens it again; Down in the modal shows pink 950,
    and Escape closes it with focus on pink 950, now pink's one Tab stop, while red's stop is still
    red 950 (Shift+Tab goes there). Space on red 950 opens it on red 950, and its close button
    (clicked) gives focus back to red 950. A click on Slate's family header opens slate 600, its main
    shade, and Escape gives focus to slate 600, slate's stop."""
    page.focus(shade_button("red", "50"))
    page.key("END")
    expect_swatch(page, "red", "950", "End")
    page.key("ENTER")
    expect_color(page, "red", "950", "Enter on red 950")
    expect_modal(page, "Enter on red 950")
    page.key("ESCAPE")
    expect_closed(page, "Escape")
    expect_swatch(page, "red", "950", "closed")
    page.key("ENTER")
    expect_color(page, "red", "950", "Enter again")
    page.key("ARROW_DOWN")
    expect_color(page, "pink", "950", "Down in the modal")
    page.key("ESCAPE")
    expect_closed(page, "Escape on pink 950")
    expect_swatch(page, "pink", "950", "closed on pink 950")
    page.eq("red's stop is still red 950", page.js(TOOLBARS)[0]["stops"], ["950"])
    page.tab(shift=True)
    expect_swatch(page, "red", "950", "Shift+Tab")
    page.key("SPACE")
    expect_color(page, "red", "950", "Space on red 950")
    page.click("dialog.color[open] header .close")
    expect_closed(page, "close button")
    expect_swatch(page, "red", "950", "closed by its button")
    page.click(".color-families .family > header.femto-background-slate")
    expect_color(page, "slate", "600", "Slate's header")
    page.key("ESCAPE")
    expect_closed(page, "Escape on slate 600")
    expect_swatch(page, "slate", "600", "closed on slate 600")


@check("color-grid-nojs", ROUTE, javascript=False)
def color_grid_nojs(page):
    """With the page's JavaScript off (skipped in Safari), the grid is the markup's: 20 families of 19
    shade buttons, each showing its shade (50 to 950) and each in the tab order (no tabindex), with no
    toolbar role or aria-label added; Tab from red 50's button goes to red 100's, so every swatch can
    be reached."""
    r = page.js("""const g = [...document.querySelectorAll(".color-families .family > .shades")];
      return {families: g.length, buttons: g.map(x => x.querySelectorAll(":scope > button").length),
              text: g.map(x => [...x.querySelectorAll(":scope > button")].map(b => b.textContent.trim()).join(" ")),
              tabindex: document.querySelectorAll(".color-families button[tabindex]").length,
              stops: [...document.querySelectorAll(".color-families .shades > button")].every(b => b.tabIndex === 0),
              added: g.filter(x => x.hasAttribute("role") || x.hasAttribute("aria-label")).length};""")
    want = " ".join(next(iter(femto_palette()[0].values())))
    page.eq("20 families", r["families"], len(families()))
    page.eq("19 shade buttons each", r["buttons"], [19] * len(families()))
    page.eq("each button shows its shade", r["text"], [want] * len(families()))
    page.eq("no button has a tabindex", r["tabindex"], 0)
    page.expect("every button is in the tab order", r["stops"])
    page.eq("no toolbar role or name is added", r["added"], 0)
    page.focus(shade_button("red", "50"))
    page.tab()
    page.wait("Tab from red 50 goes to red 100", "document.activeElement === document.querySelector(arguments[0])", 1,
              args=(shade_button("red", "100"),),
              got=page.js("return document.activeElement && document.activeElement.outerHTML.slice(0, 80)"))
