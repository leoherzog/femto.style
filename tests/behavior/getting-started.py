"""Getting started: the Theme picker (picker.js) and the color-schemes section's own toggle
(Customization since the 2026-11-07 reorder).

The Theme picker is the Remix site's version picker reworked (PLAN.md Owner answers 3), section id
theme-picker: the 20 theme colors, a switch for each of femto's three option files, and three samples
of what to copy (the <link> tags in load order, one jsDelivr combine URL, the starter template). A
color is /docs?theme=<color>#theme-picker (Decision 8): a swatch swaps the theme's <link> and
replaceStates ?theme= (no history entry; azure, the default, has none), and links to #theme-picker
are the browser's fragment navigation."""
from behavior import HEADING_LINE, SNAPSHOT, TOKENS, check

GROUP = "getting-started"

PKG = "@leoherzog/femto@3"   # the package and version range the samples name (picker.js reads it from the built cdn sample)
CDN = f"https://cdn.jsdelivr.net/npm/{PKG}/"
OPTIONS = ["responsive-spacings", "fixed-typography", "no-transitions"]   # femto's css/options/, in link order
# The switches as the page loads them: responsive spacings on, since the page loads that option
# (the owner, 2026-11-08: the switches apply to the page as well as the samples).
DEFAULT = ["responsive-spacings"]
STYLESHEET = "styles.css"    # the reader's own stylesheet, after femto's files
PICKER = "/docs#theme-picker"   # azure; a color is /docs?theme=<color>#theme-picker
# Every stylesheet <link> on the page has loaded: a loading one has no sheet yet (Chrome), or one
# whose cssRules throw (Firefox).
SHEETS_LOADED = """[...document.querySelectorAll("link[rel=stylesheet]")].every(l => {
  try { return !!l.sheet && l.sheet.cssRules !== null; } catch (e) { return false; } })"""


def picker_route(color):
    return PICKER if color == "azure" else f"/docs?theme={color}#theme-picker"


def picker_url(color, hash_="#theme-picker"):
    """The one page's URL for the picker in `color`, with the hash the spy keeps."""
    return f"/docs{'' if color == 'azure' else '?theme=' + color}{hash_}"


# The theme stylesheets on the page: every <link> to femto's css/themes/, with its color.
THEME_LINKS = r"""
return [...document.querySelectorAll("link[rel=stylesheet]")].map(l => l.getAttribute("href"))
  .filter(h => /\/css\/themes\//.test(h)).map(h => h.replace(/^.*\//, "").replace(/\.css$/, ""));
"""
STYLESHEETS = "return [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.getAttribute('href'))"
# The page's femto option stylesheets, by option name, in document order; and its other stylesheets.
OPTION_SHEETS = STYLESHEETS + ".filter(h => h.includes('/css/options/')).map(h => h.replace(/^.*\\//, '').replace(/\\.css$/, ''))"
OTHER_SHEETS = STYLESHEETS + ".filter(h => !h.includes('/css/options/'))"
ROOT_FONT = "return getComputedStyle(document.documentElement).fontSize"


def swapped(page, color, label):
    """Wait until a swap to `color` is done: ?theme= in the URL (none for azure) and the page in that
    color's theme stylesheet only."""
    search = "" if color == "azure" else f"?theme={color}"
    page.wait(f"{label}: the URL's query is {search or 'empty'}", "location.pathname === '/docs' && location.search === arguments[0]", 3,
              args=(search,), url=page.url())
    page.wait(f"{label}: the page is in {color} only", f"JSON.stringify((() => {{ {THEME_LINKS} }})()) === arguments[0]", 3,
              args=('[]' if color == "azure" else f'["{color}"]',))


def files(color, options):
    """femto's files for a color and options, in load order: femto, the theme (none for azure, which
    is built in), the options in OPTIONS order (femto's README, Themes and Options)."""
    return (["dist/femto.min.css"] + ([] if color == "azure" else [f"css/themes/{color}.css"])
            + [f"css/options/{o}.css" for o in OPTIONS if o in options])


def link(href):
    return f'<link rel="stylesheet" href="{href}">'


def combine_href(fs):
    return CDN + fs[0] if len(fs) == 1 else "https://cdn.jsdelivr.net/combine/" + ",".join(f"npm/{PKG}/{f}" for f in fs)


def expected_codes(color="azure", options=()):
    """The three samples' text, as the README's Quick start, Themes and Options give them: cdn, a
    <link> per line for femto's files then styles.css; combine, femto's files in one jsDelivr combine
    URL, or femto's own link when it is the only file; template, the starter template with the same
    links (without styles.css) in place of femto's."""
    fs = files(color, options)
    links = [link(CDN + f) for f in fs]
    template = ("<!doctype html>\n"
                '<html lang="en">\n'
                "  <head>\n"
                '    <meta charset="utf-8">\n'
                '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '    <meta name="color-scheme" content="light dark">\n'
                + "".join(f"    {x}\n" for x in links) +
                "    <title>Hello, world!</title>\n"
                "  </head>\n"
                "  <body>\n"
                '    <main class="container">\n'
                "      <h1>Hello, world!</h1>\n"
                "    </main>\n"
                "  </body>\n"
                "</html>")
    return {"cdn": "\n".join(links + [link(STYLESHEET)]), "combine": link(combine_href(fs)), "template": template}


# The three samples, by their sections' hooks (section[data-picker-usage=cdn|combine|template]).
CODES = """
const pick = (n) => (S.querySelector(`[data-picker-usage="${n}"]`) || document.createElement("i")).querySelector("pre code");
const cdn = pick("cdn"), combine = pick("combine"), template = pick("template");
"""


def code_texts(page):
    return page.js(CODES + "return Object.fromEntries(Object.entries({cdn, combine, template}).map(([k, v]) => [k, v && v.textContent]));")


SWITCHES = "[data-picker-options] input[type=checkbox][role=switch]"


def chosen(page):
    return page.js(f"return [...S.querySelectorAll('{SWITCHES}')].filter(i => i.checked).map(i => i.name)")


def expect_state(page, color="azure", options=DEFAULT, label=""):
    want = expected_codes(color, options)
    page.wait(f"{label}codes regenerated", f"(() => {{ {CODES} return !!cdn && cdn.textContent === arguments[0]; }})()",
              1, args=(want["cdn"],), got=code_texts(page)["cdn"])
    got = code_texts(page)
    for k in ("cdn", "combine", "template"):
        page.eq(f"{label}{k} code for {color}, {list(options) or 'no options'}", got[k], want[k])
    page.eq(f"{label}the switches", chosen(page), [o for o in OPTIONS if o in options])


def settle(page, label):
    """Wait until the scroll position has held for 250 ms (at most 4 s): Firefox restores the
    position on back and forward with a smooth scroll, and a click while the page still scrolls can
    be lost there."""
    held = page.ajs("""
      const frame = () => new Promise(r => requestAnimationFrame(() => r()));
      const end = performance.now() + 4000;
      let last = scrollY, since = performance.now();
      while (performance.now() < end) {
        await frame();
        if (scrollY !== last) { last = scrollY; since = performance.now(); }
        else if (performance.now() - since >= 250) return true;
      }
      return false;""")
    page.expect(f"{label}: the scroll position settles", held, y=page.js("return scrollY"))


def choose(page, options):
    """Set the option switches to `options`, each with a real click on a switch that has to change
    (scrolled to the middle first, so the click never lands while the page still scrolls)."""
    for o in OPTIONS:
        sel = f"[data-picker-options] input[name={o}]"
        if page.js(f"return S.querySelector('{sel}').checked") != (o in options):
            el = page.find(sel)
            page.js("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'})", el)
            page.click(el, scroll=False)
            page.wait(f"{o} turns {'on' if o in options else 'off'}", f"S.querySelector('{sel}').checked === {'true' if o in options else 'false'}", 1)
            # The switch links its stylesheet at once, and it applies once loaded: fixed-typography's
            # shrinks every font size, which moved the next switch ~580 px up, off screen, between its
            # scroll and its click (2026-11-09, in Chrome and Firefox). So the page holds still first.
            page.wait(f"{o}: the page's stylesheets have loaded", SHEETS_LOADED, 3)


@check("picker-options", PICKER)
def picker_options(page):
    """The Theme picker's options (`section[data-picker-options]`): one switch per file in femto's
    css/options/ (`input[type=checkbox][role=switch]` named responsive-spacings, fixed-typography and
    no-transitions, in that order, each described by its helper <small> through aria-describedby),
    responsive spacings on at load and the others off, as the page loads responsive-spacings.css.
    The switches regenerate the three samples' text exactly (expected_codes: the cdn links in load
    order, femto, the theme, the chosen options, then styles.css; the combine URL, or femto's link
    alone; the starter template's links), and they apply to the page too: its femto option
    stylesheets are exactly the chosen ones, in OPTIONS order, while its other stylesheets (femto,
    femto.colors.css and the site's) stay as loaded, and with fixed typography on the root font
    size is 16px (100%), back to its load-time size once it is off. Checked on load and after six
    sets of options, the last the load-time one."""
    r = page.js(f"""return [...S.querySelectorAll('{SWITCHES}')].map(i => {{
        const d = document.getElementById(i.getAttribute('aria-describedby') || '');
        return [i.name, i.checked, !!d && d.localName === 'small' && d.textContent.trim().length > 0]; }})""")
    page.eq("three option switches, responsive spacings on, each with its helper", r,
            [[o, o in DEFAULT, True] for o in OPTIONS])
    page.eq("on load: the page's option stylesheets", page.js(OPTION_SHEETS), DEFAULT)
    others, font = page.js(OTHER_SHEETS), page.js(ROOT_FONT)
    expect_state(page, label="on load: ")
    for opts in (["fixed-typography"], ["responsive-spacings", "no-transitions"], OPTIONS, ["no-transitions"], [], DEFAULT):
        name = opts or "no options"
        choose(page, opts)
        expect_state(page, "azure", opts, label=f"{name}: ")
        page.eq(f"{name}: the page's option stylesheets follow the switches", page.js(OPTION_SHEETS), opts)
        page.eq(f"{name}: the page's other stylesheets are as loaded", page.js(OTHER_SHEETS), others)
        want = "16px" if "fixed-typography" in opts else font
        page.wait(f"{name}: the root font size is {want}", f"{ROOT_FONT.removeprefix('return ')} === arguments[0]", 3,
                  args=(want,), got=page.js(ROOT_FONT))


# The highlighted <link rel="stylesheet" href="..."> lines, as build.mjs writes them and picker.js
# regenerates them (TOKENS: [className, text] per child of code, "#text" for plain text): the tag
# name in span.tag, each attribute name in span.attr and its quoted value in span.value, the rest
# plain text, with a line break and the next line's indent between lines. A token list is compared
# as runs: chars() splits it into [class, character] pairs, runs() joins the neighbors of one class,
# as the page's text nodes join (the build writes no two spans of one class side by side).
def chars(tokens):
    return [(cls, ch) for cls, text in tokens for ch in text]


def runs(pairs):
    out = []
    for cls, ch in pairs:
        if out and out[-1][0] == cls:
            out[-1][1] += ch
        else:
            out.append([cls, ch])
    return out


def link_tokens(href):
    def attribute(name, value):
        return [["#text", " "], ["attr", name], ["#text", "="], ["value", f'"{value}"']]
    return [["#text", "<"], ["tag", "link"]] + attribute("rel", "stylesheet") + attribute("href", href) + [["#text", ">"]]


def lines_tokens(hrefs, indent=""):
    out = []
    for i, h in enumerate(hrefs):
        if i:
            out += [["#text", "\n" + indent]]
        out += link_tokens(h)
    return runs(chars(out))


TOKEN_LISTS = TOKENS + CODES + "return Object.fromEntries(Object.entries({cdn, combine, template}).map(([k, v]) => [k, tokens(v)]));"


def expected_tokens(initial_template, color, options):
    """The three samples' tokens: cdn and combine are link lines only; the template keeps the
    load-time tokens of its other lines, with the load-time switches' link lines (femto's, then
    responsive spacings') replaced by the links' lines."""
    fs = files(color, options)
    loaded = chars(lines_tokens([CDN + f for f in files("azure", DEFAULT)], "    "))
    t = chars(initial_template)
    i = next(k for k in range(len(t)) if t[k:k + len(loaded)] == loaded)
    return {"cdn": lines_tokens([CDN + f for f in fs] + [STYLESHEET]), "combine": lines_tokens([combine_href(fs)]),
            "template": runs(t[:i] + chars(lines_tokens([CDN + f for f in fs], "    ")) + t[i + len(loaded):])}


@check("picker-code-highlight", PICKER)
def picker_code_highlight(page):
    """The regenerated samples stay highlighted the way the build highlights them (each child of
    `pre code` as [class, text]): on load the cdn and combine samples are exactly the build's
    highlighting of their <link> lines (the model link_tokens: tag, attr and value spans, plain text
    between them, and a line break and the next line's indent between lines) and the template holds
    femto's link line's tokens; after option changes and swaps (all options; jade with all options; jade with
    fixed-typography; azure with none; azure with the load-time responsive spacings) every sample is
    exactly the model again, the template's other lines keeping their load-time tokens, and the last
    gives the load-time tokens."""
    initial = page.js(TOKEN_LISTS)
    want = expected_tokens(initial["template"], "azure", DEFAULT)
    for k in ("cdn", "combine", "template"):
        page.eq(f"on load: {k} tokens are the build's", initial[k], want[k])
    steps = [("azure", OPTIONS), ("jade", OPTIONS), ("jade", ["fixed-typography"]), ("azure", []), ("azure", DEFAULT)]
    color = "azure"
    for c, opts in steps:
        choose(page, opts)
        if c != color:
            page.click(swatch(c))
            swapped(page, c, c)
            color = c
        expect_state(page, c, opts, label=f"{c}, {opts or 'no options'}: ")
        got, want = page.js(TOKEN_LISTS), expected_tokens(initial["template"], c, opts)
        for k in ("cdn", "combine", "template"):
            page.eq(f"{c}, {opts or 'no options'}: {k} tokens", got[k], want[k])
    page.eq("azure, responsive spacings: the load-time tokens", page.js(TOKEN_LISTS), initial)


def swatch(color):
    return f"#content article[data-version-picker] > header a.femto-background-{color}"


# What a color swap must leave exactly as a fresh load of the color has it: the theme example
# (swatches, hgroup, form) and the three samples, as tree snapshots, plus the primary color, the
# theme stylesheets, every swatch's aria-label and every link's aria-current outside the side menu
# (header, footer, swatches; the side menu's follows the scroll position). The example form's
# Privacy Policy link's href names the color's page and does nothing (preventDefault), so that href
# is left out of the tree snapshots.
PICKER_SNAPSHOT = SNAPSHOT + CODES + """
const article = S.querySelector("#content article[data-version-picker]");
const selfLinks = new Set([...S.querySelectorAll("#content article[data-version-picker] form a")]);
const clean = (el, s) => {
  if (!Array.isArray(s)) return s;
  const [tag, attrs, kids] = s;
  const elKids = [...el.childNodes].filter(c => c.nodeType === 1);
  let k = 0;
  return [tag, selfLinks.has(el) ? attrs.filter(([n]) => n !== "href") : attrs,
          kids.map(c => Array.isArray(c) ? clean(elKids[k++], c) : c)];
};
const tree = (el) => el ? clean(el, snap(el)) : null;
const region = (a) => a.closest("body > header") ? "header" : a.closest("body > footer") ? "footer"
  : a.closest("#documentation-menu") ? "menu" : "content";
return {article: tree(article), cdn: tree(cdn), combine: tree(combine), template: tree(template),
        form: [...article.querySelectorAll(":scope > form input")].map(i => [i.name, i.type === "checkbox" ? i.checked : i.value]),
        current: [...document.querySelectorAll("a[aria-current]")].filter(a => !a.closest("#documentation-menu"))
          .map(a => [region(a), a.getAttribute("href"), a.getAttribute("aria-current")]),
        labels: [...article.querySelectorAll(":scope > header a")].map(a => a.getAttribute("aria-label")),
        primary: getComputedStyle(document.documentElement).getPropertyValue("--femto-primary").trim(),
        themes: (() => { """ + THEME_LINKS + """ })(),
        url: location.pathname + location.search + location.hash, history: history.length, y: Math.round(scrollY)};
"""
# The swatches' labels in order: rainbow order (ROYGBIV) by hue, then the neutrals from lightest to
# darkest (the owner, 2026-11-08; the Remix site's ran from red through pink and blue to orange).
NAMES = ["Red", "Orange", "Pumpkin", "Amber", "Yellow", "Lime", "Green", "Jade", "Cyan", "Azure", "Blue", "Indigo",
         "Violet", "Purple", "Fuchsia", "Pink", "Sand", "Grey", "Zinc", "Slate"]


def picker_snapshot(page):
    return page.js(PICKER_SNAPSHOT)


def expect_like_loaded(page, color, label, options=()):
    """Compare the page now with a fresh load of ?theme=<color>#theme-picker in a second tab, its
    switches set to the same options first."""
    now = picker_snapshot(page)
    here = page.driver.current_window_handle
    route = picker_route(color)
    page.new_tab(route)
    if options:
        choose(page, options)
        expect_state(page, color, options, label=f"{label}: the fresh load set to {list(options)}: ")
    fresh = picker_snapshot(page)
    page.driver.close()
    page.switch(here)
    for k in ("article", "cdn", "combine", "template", "current", "labels", "primary", "themes"):
        page.eq(f"{label}: {k} as on a fresh load of {route}", now[k], fresh[k])
    return now


@check("picker-swatch", PICKER)
def picker_swatch(page):
    """A theme color swatch (`article[data-version-picker] > header a`, aria-label its own color's name)
    switches the theme in place (criterion 7: the picker swaps the theme and updates ?theme=): with
    "abc" typed in the example's Login field and its Privacy switch turned off, the swatches 300 px
    below the viewport's top, a click on pumpkin's swatch keeps the scroll position, makes the URL
    /docs?theme=pumpkin#theme-picker with no new history entry (replaceState, Decision 8), and leaves
    the theme example (the check icon and aria-current on pumpkin, the hgroup "Pumpkin" and "Form
    example with a pumpkin theme."), the samples, every swatch's label, every link's aria-current
    outside the side menu, --femto-primary and the theme stylesheets (pumpkin's alone) exactly as a
    fresh load of pumpkin has them (tree snapshots; the Privacy Policy link's href aside); the form
    keeps what was typed. The options survive a swap: with fixed-typography on, jade's swatch gives
    jade's and fixed-typography's links. A reload keeps jade (the URL carries it) and the samples
    follow the switches as the browser restores them. Azure's swatch then gives the picker as a
    fresh load of azure has it: no ?theme=, no theme stylesheet."""
    example = "#content article[data-version-picker] > form"
    y = page.js("return Math.round(S.querySelector('article[data-version-picker]').getBoundingClientRect().top + scrollY - 300)")
    page.scroll_to(y)
    page.click(page.find(f"{example} input[name=login]"))
    page.key("abc")
    page.click(page.find(f"{example} input[name=switch]"))
    page.wait("the example form holds what was typed", "(() => { const f = S.querySelector(arguments[0]);"
              " return f.elements.login.value === 'abc' && !f.elements.switch.checked; })()", 1, args=(example,))
    page.scroll_to(y)
    before = picker_snapshot(page)
    page.eq("each swatch is labeled with its own color", before["labels"], NAMES)
    page.click(swatch("pumpkin"), scroll=False)
    swapped(page, "pumpkin", "pumpkin")
    now = expect_like_loaded(page, "pumpkin", "pumpkin")
    page.expect("the swap changed the theme example", now["article"] != before["article"] and now["primary"] != before["primary"])
    page.eq("the URL is pumpkin's", now["url"], "/docs?theme=pumpkin#theme-picker")
    page.eq("no new history entry (replaceState)", now["history"], before["history"])
    page.eq("the scroll position is kept", now["y"], before["y"])
    page.eq("the form keeps what was typed", now["form"], [["login", "abc"], ["password", ""], ["switch", False]])
    page.eq("pumpkin's heading", page.js("return S.querySelector('article[data-version-picker] > hgroup').textContent.replace(/\\s+/g, ' ').trim()"),
            "Pumpkin Form example with a pumpkin theme.")
    choose(page, ["fixed-typography"])
    expect_state(page, "pumpkin", ["fixed-typography"], label="pumpkin, fixed typography: ")
    page.click(swatch("jade"))
    swapped(page, "jade", "jade")
    expect_state(page, "jade", ["fixed-typography"], label="jade after the swap: ")
    url = page.url()
    page.js("window.__bhMarker = 'before the reload'; setTimeout(() => location.reload(), 0); return true;")
    page.wait("the page reloaded", "window.__bhMarker === undefined && document.readyState === 'complete'", 15)
    page.wait_ready()
    page.eq("reload: the URL keeps ?theme=jade", page.url(), url)
    page.eq("reload: jade is the page's theme stylesheet", page.js(THEME_LINKS), ["jade"])
    expect_state(page, "jade", chosen(page), label="reload: the samples follow the switches as restored: ")
    page.eq("reload: the page's option stylesheets follow the switches as restored", page.js(OPTION_SHEETS), chosen(page))
    choose(page, DEFAULT)
    # Back where the swaps started: the side nav's current link follows the scroll position, and a
    # switch's own scroll into view can leave the picker's heading under the line.
    page.scroll_to(y)
    page.click(swatch("azure"), scroll=False)
    swapped(page, "azure", "azure")
    expect_like_loaded(page, "azure", "azure")


@check("picker-swatch-focus", PICKER)
def picker_swatch_focus(page):
    """Keyboard use of the swatches: with pumpkin's swatch focused, Enter swaps to pumpkin
    (?theme=pumpkin) and focus stays on that swatch; Tab then moves focus to the next swatch (amber's,
    since the swatches are in rainbow order) and Enter on it swaps to that color with focus on it."""
    after = "amber"
    page.focus(swatch("pumpkin"))
    page.key("ENTER")
    swapped(page, "pumpkin", "pumpkin")
    focused = "document.activeElement === document.querySelector(arguments[0])"
    page.wait("focus stays on pumpkin's swatch", focused, 1, args=(swatch("pumpkin"),))
    page.key("TAB")
    page.wait(f"Tab moves focus to {after}'s swatch", focused, 1, args=(swatch(after),))
    page.key("ENTER")
    swapped(page, after, after)
    page.wait(f"focus stays on {after}'s swatch", focused, 1, args=(swatch(after),))


CURRENT_SWATCH = "S.querySelector('article[data-version-picker] > header a[aria-current=page]').className"


@check("picker-unknown-theme", ("/docs?theme=bogus#theme-picker", "/docs?theme=JADE#theme-picker"))
def picker_unknown_theme(page):
    """An unknown ?theme= (bogus, or JADE: the names are lowercase) is ignored by the picker as by
    the head script (criterion 7): no theme stylesheet, azure's swatch current, the heading "Azure",
    azure's samples, and the query left as given. Jade's swatch then swaps to jade and replaces the
    unknown value: ?theme=jade."""
    page.eq("no theme stylesheet", page.js(THEME_LINKS), [])
    page.eq("azure is current", page.js(f"return {CURRENT_SWATCH}"), "femto-background-azure")
    page.eq("the heading is Azure", page.js("return S.querySelector('article[data-version-picker] > hgroup > h2').textContent"), "Azure")
    expect_state(page, label="unknown theme: ")
    page.eq("the query is left as given", page.js("return location.search"), "?" + page.route.split("?")[1].split("#")[0])
    page.click(swatch("jade"))
    swapped(page, "jade", "jade")


@check("picker-popstate", PICKER)
def picker_popstate(page):
    """Back and forward between entries of the one page whose ?theme= differ show each entry's
    color: after jade's swatch (?theme=jade, replaceState), a fragment navigation to #themes (a new
    entry) and pumpkin's swatch (?theme=pumpkin, replaceState on that entry), back returns to the
    first entry with jade current, jade's stylesheet alone and jade's samples, and forward to
    pumpkin's, all in the same document."""
    page.js("window.__bhSameDocument = true")
    page.click(swatch("jade"))
    swapped(page, "jade", "jade")
    page.js("location.hash = '#themes'; return true")
    page.wait("at #themes", "location.hash === '#themes'", 3)
    page.click(swatch("pumpkin"))
    swapped(page, "pumpkin", "pumpkin")
    page.driver.back()
    page.wait("back: ?theme=jade", "location.search === '?theme=jade'", 3, url=page.url())
    page.wait("back: jade is current", f"{CURRENT_SWATCH} === 'femto-background-jade'", 3)
    page.wait("back: jade's stylesheet only", f"JSON.stringify((() => {{ {THEME_LINKS} }})()) === '[\"jade\"]'", 3)
    expect_state(page, "jade", label="back: ")
    page.driver.forward()
    page.wait("forward: ?theme=pumpkin", "location.search === '?theme=pumpkin'", 3, url=page.url())
    page.wait("forward: pumpkin is current", f"{CURRENT_SWATCH} === 'femto-background-pumpkin'", 3)
    page.wait("forward: pumpkin's stylesheet only", f"JSON.stringify((() => {{ {THEME_LINKS} }})()) === '[\"pumpkin\"]'", 3)
    page.expect("the same document throughout", page.js("return window.__bhSameDocument === true"))


NO_RELOAD = "window.__bhSameDocument === true"


@check("picker-links", PICKER)
def picker_links(page):
    """The other links to the picker keep its options (fixed-typography here) and color. They are
    fragment links in the same document: after pumpkin's swatch, scrolled 600 px below the picker's
    heading, the side menu's link (#theme-picker) puts the heading on the scroll-padding line with
    ?theme=pumpkin kept; the footer's "Theme picker" link (/docs#theme-picker), from azure scrolled
    to the bottom, does the same with no query; from jade it does the same with ?theme=jade kept
    (docs.js turns that link into a fragment navigation, since the browser's own would load /docs
    without the query), and back from there returns, in the same document with ?theme=jade and
    jade's stylesheet kept, to the bottom (or, as Chrome may restore it, to the entry's section
    heading). Each with no page load, the options kept, and a new history entry only when the URL
    changed."""
    choose(page, ["fixed-typography"])
    expect_state(page, "azure", ["fixed-typography"], label="fixed typography: ")
    page.js("window.__bhSameDocument = true")
    top = page.js("return Math.round(document.getElementById('theme-picker').getBoundingClientRect().top + scrollY)")
    footer = "body > footer a[href='/docs#theme-picker']"
    for color, link_, name in (("pumpkin", "#documentation-menu a[href='#theme-picker']", "side menu"),
                               ("azure", footer, "footer"), ("jade", footer, "footer from jade")):
        page.click(swatch(color))
        swapped(page, color, color)
        page.scroll_to(page.js("return document.documentElement.scrollHeight - innerHeight") if link_ == footer else top + 600)
        settle(page, f"{name} link: scrolled")
        url, n = page.url(), page.js("return history.length")
        page.click(link_, scroll=False)
        page.wait(f"{name} link: the URL is the picker's", "location.pathname + location.search + location.hash === arguments[0]",
                  3, args=(picker_url(color),))
        page.wait(f"{name} link: the heading is on the scroll-padding line",
                  f"Math.abs(({HEADING_LINE})('theme-picker')) <= 2", 3)
        settle(page, f"{name} link")
        page.expect(f"{name} link: no page load", page.js(f"return {NO_RELOAD}"))
        page.eq(f"{name} link: a new history entry only for a new URL", page.js("return history.length"),
                n + (url != picker_url(color)), url_before=url)
        expect_state(page, color, ["fixed-typography"], label=f"{name} link: ")
        if color == "jade":
            page.driver.back()
            page.wait("back: the URL leaves #theme-picker, ?theme=jade kept",
                      "location.search === '?theme=jade' && location.hash !== '#theme-picker'", 3, url_before=url)
            settle(page, "back")
            page.expect("back: no page load", page.js(f"return {NO_RELOAD}"))
            page.eq("back: no new history entry", page.js("return history.length"), n + (url != picker_url(color)))
            page.eq("back: jade is the one theme stylesheet", page.js(THEME_LINKS), ["jade"])
            page.expect("back: at the bottom again, or the entry's section heading on its line", page.js(
                "return Math.ceil(scrollY + innerHeight) >= document.documentElement.scrollHeight - 1"
                f" || Math.abs(({HEADING_LINE})(location.hash.slice(1))) <= 2"),
                        y=page.js("return scrollY"), url=page.url())


SWITCHER = """
const b = document.querySelector("#theme-switcher button"), a = document.querySelector(arguments[0]);
const i = b.querySelector(":scope > span[role=img]"), hi = a && a.querySelector(":scope > span[role=img]");
return {text: [...b.childNodes].filter(n => n.nodeType === 3).map(n => n.data).join("").trim(),
        moon: !!i && i.textContent === "\\u{1F319}", icon: !!i && i.getAttribute("aria-hidden") === "true",
        theme: document.documentElement.getAttribute("data-theme"), stored: localStorage.getItem("femtoColorScheme"),
        header: hi && hi.getAttribute("aria-label")};
"""
HEADER_TOGGLE = "body > header nav button:has(> span[role=img][aria-label$='dark mode'])"   # a button named by its icon (Decision 18)


@check("color-schemes-toggle", "/docs#color-schemes")
def color_schemes_toggle(page):
    """The Color schemes section's own switcher (`#theme-switcher button`; its icon is a decorative `span[role=img]` of Decision 18 holding the emoji of Decision 16) reads
    "Turn on dark mode" with the sun on a light OS; a click sets data-theme="dark", stores
    '"dark"', and both it ("Turn off dark mode", with the moon) and the header toggle relabel; a
    second click returns to the OS's light, removing the stored choice and data-theme. The header
    toggle drives it too."""
    def expect_switcher(theme, label):
        page.wait(f"switcher reads {label!r}", "(() => { const b = document.querySelector('#theme-switcher button');"
                  " const i = b.querySelector(':scope > span[role=img]'), h = document.querySelector(arguments[1]);"
                  " const text = [...b.childNodes].filter(n => n.nodeType === 3).map(n => n.data).join('').trim();"
                  " return text === arguments[0] && (i.textContent === '\\u{1F319}') === (arguments[0] === 'Turn off dark mode')"
                  " && !!h && h.querySelector(':scope > span[role=img]').getAttribute('aria-label') === arguments[0]; })()", 1,
                  args=(label, HEADER_TOGGLE))
        s = page.js(SWITCHER, HEADER_TOGGLE)
        page.eq(f"data-theme {theme}", s["theme"], theme)
        page.eq(f"stored {theme}", s["stored"], None if theme is None else f'"{theme}"')

    page.expect("the switcher and its icon", page.js(SWITCHER, HEADER_TOGGLE)["icon"])
    expect_switcher(None, "Turn on dark mode")
    url = page.url()
    page.click("#theme-switcher button")
    expect_switcher("dark", "Turn off dark mode")
    page.click("#theme-switcher button")
    expect_switcher(None, "Turn on dark mode")
    page.click(HEADER_TOGGLE)
    expect_switcher("dark", "Turn off dark mode")
    page.url_kept("the URL is unchanged", url)
