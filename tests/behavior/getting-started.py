"""Getting started: the version picker (01 §2, Version picker; picker.js in the static site) and the
color-schemes section's own toggle (01 §2, small widgets).

The picker's colors were routes, /docs/version-picker and /docs/version-picker/<color>, which its
swatches pushed in place; on the one page they are /docs?theme=<color>#version-picker (Decision 8):
a swatch swaps the theme's <link> and replaceStates ?theme= (no history entry; azure, the default,
has none), and links to #version-picker are the browser's fragment navigation. The checks hold each
layout to its own URLs and the rest (samples, swatches, the example form, focus, the logo) to the
same rules."""
from behavior import HEADING_LINE, SNAPSHOT, TOKENS, check

GROUP = "getting-started"

CDN = "https://cdn.jsdelivr.net/npm/@leoherzog/femto@3/"
BASES = [  # (file pattern, Sass properties, the description's text that names no link)
    ("", [], "The default version of Pico CSS, with all components and classes."),
    ("classless.", [("$enable-semantic-container", "true"), ("$enable-classes", "false")],
     "for HTML purists with centered viewports."),
    ("fluid.classless.", [("$enable-semantic-container", "true"), ("$enable-viewport", "false"),
                          ("$enable-classes", "false")],
     "for HTML purists with a fluid viewport."),
]
CONDITIONAL = [
    ("", [], "The default version applies Pico styles to every HTML element."),
    ("conditional.", [("$parent-selector", '".pico"')],
     "This version restricts Pico styling to HTML elements within .pico containers only."),
]
SELECT = "#content select[name=configuration]"
SWITCH = "#content input[name=conditional]"
PICKER = "/docs#version-picker"   # azure; a color is /docs?theme=<color>#version-picker


def picker_route(color):
    return PICKER if color == "azure" else f"/docs?theme={color}#version-picker"


def picker_url(color, hash_="#version-picker"):
    """The one page's URL for the picker in `color`, with the hash the spy keeps."""
    return f"/docs{'' if color == 'azure' else '?theme=' + color}{hash_}"


# The theme stylesheets on the page: every <link> to femto's css/themes/ (the one page), or to the
# oracle's custom-themes/ (a color route), with its color.
THEME_LINKS = r"""
return [...document.querySelectorAll("link[rel=stylesheet]")].map(l => l.getAttribute("href"))
  .filter(h => /\/(css\/themes|custom-themes)\//.test(h)).map(h => h.replace(/^.*\//, "").replace(/\.css$/, ""));
"""


def swapped(page, color, label):
    """Wait until a swap to `color` is done: on routes the route's URL (wait_navigated), on the one
    page ?theme= in the URL (none for azure) and the page in that color's theme stylesheet only."""
    if page.layout == "routes":
        page.wait_navigated("/docs/version-picker" + ("" if color == "azure" else f"/{color}"), label=label)
        return
    search = "" if color == "azure" else f"?theme={color}"
    page.wait(f"{label}: the URL's query is {search or 'empty'}", "location.pathname === '/docs' && location.search === arguments[0]", 3,
              args=(search,), url=page.url())
    page.wait(f"{label}: the page is in {color} only", f"JSON.stringify((() => {{ {THEME_LINKS} }})()) === arguments[0]", 3,
              args=('[]' if color == "azure" else f'["{color}"]',))


def file_name(base, cond, color="azure"):
    return f"pico.{BASES[base][0]}{CONDITIONAL[cond][0]}{'' if color == 'azure' else color + '.'}min.css"


def sass_props(base, cond, color="azure"):
    return ([] if color == "azure" else [("$theme-color", f'"{color}"')]) + BASES[base][1] + CONDITIONAL[cond][1]


def expected_codes(base, cond, color="azure"):
    """The four generated code samples, as the oracle's VersionPickerContext and Usage write them:
    the theme example's footer link, Usage from CDN, Usage with Sass, Starter HTML template."""
    f = file_name(base, cond, color)
    link = f'<link rel="stylesheet" href="css/{f}">'
    props = sass_props(base, cond, color)
    sass = '@use "pico";' if not props else '@use "pico" with (\n' + ",\n".join(f"  {k}: {v}" for k, v in props) + "\n);"
    template = ("<!doctype html>\n"
                f'<html lang="en"{" class=\"pico\"" if cond else ""}>\n'
                "  <head>\n"
                '    <meta charset="utf-8">\n'
                '    <meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '    <meta name="color-scheme" content="light dark">\n'
                f"    {link}\n"
                "    <title>Hello world!</title>\n"
                "  </head>\n"
                "  <body>\n"
                '    <main class="container">\n'
                "      <h1>Hello world!</h1>\n"
                "    </main>\n"
                "  </body>\n"
                "</html>")
    return {"footer": link, "cdn": f'<link\n  rel="stylesheet"\n  href="{CDN}css/{f}"\n>', "sass": sass, "template": template}


# The four code samples in page order: the theme example's footer, then the three Usage sections.
CODES = """
const footer = S.querySelector("#content article.color-picker > footer pre code");
const usage = [...S.querySelectorAll("#content section")].filter(s => /^(Usage from CDN|Usage with Sass|Starter HTML template)/.test((s.querySelector("h2") || {}).textContent || ""))
  .map(s => s.querySelector("pre code"));
const [cdn, sass, template] = usage;
return {footer, cdn, sass, template};
"""

PICKER_STATE = """
const smalls = [...S.querySelectorAll("#content section small")].filter(s => !s.closest("article, footer, .edit-on-github"));
return {select: S.querySelector(arguments[0]).value, conditional: S.querySelector(arguments[1]).checked,
        base: (smalls[0] || {}).textContent, cond: (smalls[1] || {}).textContent};
"""


def code_texts(page):
    return page.js(CODES.replace("return {footer, cdn, sass, template};",
                                 "return Object.fromEntries(Object.entries({footer, cdn, sass, template}).map(([k, v]) => [k, v && v.textContent]));"))


def expect_state(page, base, cond, color="azure", label=""):
    want = expected_codes(base, cond, color)
    page.wait(f"{label}codes regenerated", "(() => { " + CODES.replace(
        "return {footer, cdn, sass, template};", "return cdn && cdn.textContent === arguments[2];") + " })()",
        1, args=(SELECT, SWITCH, want["cdn"]))
    got = code_texts(page)
    for k in ("footer", "cdn", "sass", "template"):
        page.eq(f"{label}{k} code for base {base}, conditional {cond}, {color}", got[k], want[k])
    s = page.js(PICKER_STATE, SELECT, SWITCH)
    page.eq(f"{label}select shows base {base}", s["select"], str(base))
    page.eq(f"{label}switch is {'on' if cond else 'off'}", s["conditional"], bool(cond))
    page.expect(f"{label}base description", BASES[base][2] in " ".join((s["base"] or "").split()), text=s["base"])
    page.expect(f"{label}conditional description", " ".join((s["cond"] or "").split()).startswith(CONDITIONAL[cond][2]), text=s["cond"])


def settle(page, label):
    """Wait until the scroll position has held for 250 ms (at most 4 s). Both sides' CSS has
    html { scroll-behavior: smooth }, so Firefox restores the position on back and forward with a
    smooth scroll, and a click while the page still scrolls can be lost there."""
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


def choose(page, base=None, cond=None):
    """Pick a base in the select (a real selection: click, then keyboard) and set the switch. The
    select is scrolled to the middle at once: both sides' CSS makes scrolling smooth, and a click on
    the switch while the page is still scrolling was sometimes lost in Firefox. The switch's click
    must then flip its checked state; one that does not within 1 s is noted and repeated once (its
    target is the switch itself, so a lost click is the input's, not the page's)."""
    import time
    from selenium.webdriver.support.ui import Select
    if base is not None:
        el = page.find(SELECT)
        page.js("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'})", el)
        Select(el).select_by_value(str(base))
    if cond is not None and page.js(f"return S.querySelector('{SWITCH}').checked") != bool(cond):
        want = f"S.querySelector('{SWITCH}').checked === {'true' if cond else 'false'}"
        page.click(page.find(SWITCH))
        deadline = time.time() + 1
        while not page.js(f"return {want}") and time.time() < deadline:
            time.sleep(0.05)
        if not page.js(f"return {want}"):
            page.note(f"the switch's click was lost (still {'off' if cond else 'on'} after 1 s); clicked it again")
            page.click(page.find(SWITCH))
        page.wait(f"the switch turns {'on' if cond else 'off'}", want, 1)


@check("picker-configuration", PICKER)
def picker_configuration(page):
    """The version picker's configuration (azure): the select (`name=
    configuration`, values 0 to 2) and the "Conditional Styling" switch (`name=conditional`)
    regenerate the four code samples (the theme example's footer link, Usage from CDN, Usage with
    Sass, the starter HTML template; textContent exactly as the oracle writes them: pico.min.css,
    pico.classless.min.css, pico.fluid.classless.min.css, each with conditional. when the switch is
    on, the Sass `with (...)` properties, and class="pico" on the template's <html>) and the two
    descriptions under the controls (their text; links to dropped routes may differ). Checked on
    load and after: base 1, conditional on, base 2, conditional off, base 0."""
    expect_state(page, 0, 0, label="on load: ")
    for base, cond in ((1, 0), (1, 1), (2, 1), (2, 0), (0, 0)):
        choose(page, base, cond)
        expect_state(page, base, cond, label=f"base {base} cond {cond}: ")


def scss_tokens(base, cond, color="azure"):
    """The oracle's highlighted Sass sample (Prism's scss grammar, flattened as
    react-syntax-highlighter does: unmatched text in class-less spans)."""
    props = sass_props(base, cond, color)
    t = [["token keyword", "@use"], ["", " "], ["token string", '"pico"']]
    if not props:
        return t + [["token punctuation", ";"]]
    t += [["", " "], ["token module-modifier keyword", "with"], ["", " "], ["token punctuation", "("]]
    for i, (k, v) in enumerate(props):
        t += [["", "\n"], ["", "  "], ["token property variable", k], ["token punctuation", ":"], ["", " "],
              ["token boolean" if v in ("true", "false") else "token string", v]]
        if i < len(props) - 1:
            t.append(["token punctuation", ","])
    return t + [["", "\n"], ["", ""], ["token punctuation", ")"], ["token punctuation", ";"]]


TOKEN_LISTS = TOKENS + CODES.replace("return {footer, cdn, sass, template};",
                                     "return Object.fromEntries(Object.entries({footer, cdn, sass, template}).map(([k, v]) => [k, tokens(v)]));")


def link_tokens(initial, file_from, file_to):
    """A link sample's tokens with the file name changed: the same tokens, the attr-value that held
    the old name now holding the new one."""
    return [[c, t.replace(f"css/{file_from}", f"css/{file_to}")] if "attr-value" in c else [c, t] for c, t in initial]


def template_tokens(initial, file_to, cond):
    out = link_tokens(initial, file_name(0, 0), file_to)
    if cond:  # class="pico" after lang="en": the value's closing quote, then the attribute
        i = next(i for i, (c, t) in enumerate(out) if c == "token tag attr-value" and t == "en") + 1
        out[i + 1:i + 1] = [["token tag", " "], ["token tag attr-name", "class"],
                            ["token tag attr-value punctuation attr-equals", "="], ["token tag attr-value punctuation", '"'],
                            ["token tag attr-value", "pico"], ["token tag attr-value punctuation", '"']]
    return out


@check("picker-code-highlight", PICKER)
def picker_code_highlight(page):
    """The regenerated samples stay highlighted the way the page highlights them on load (each
    child of `pre code` as [class, text]): the footer and CDN links keep their load-time tokens with
    only the file name's attr-value text changed; the starter template too, plus the six tokens of
    class="pico" after lang="en" when conditional; the Sass sample is Prism's scss output for its
    text (keyword @use, string "pico", module-modifier keyword with, property variable per
    $property, boolean or string values, punctuation). Checked for all six configurations."""
    initial = page.js(TOKEN_LISTS)
    page.eq("Sass on load", initial["sass"], scss_tokens(0, 0))
    for base, cond in ((1, 0), (2, 0), (2, 1), (1, 1), (0, 1), (0, 0)):
        choose(page, base, cond)
        expect_state(page, base, cond, label=f"base {base} cond {cond}: ")
        got = page.js(TOKEN_LISTS)
        f = file_name(base, cond)
        page.eq(f"base {base} cond {cond}: footer tokens", got["footer"], link_tokens(initial["footer"], file_name(0, 0), f))
        page.eq(f"base {base} cond {cond}: CDN tokens", got["cdn"], link_tokens(initial["cdn"], file_name(0, 0), f))
        page.eq(f"base {base} cond {cond}: Sass tokens", got["sass"], scss_tokens(base, cond))
        page.eq(f"base {base} cond {cond}: template tokens", got["template"], template_tokens(initial["template"], f, cond))


# What a color swap must leave exactly as a fresh load of the color has it: the theme example
# (swatches, hgroup, form, footer code) and the three Usage samples, as tree snapshots, plus the
# title, the primary color, the example form's control values (the oracle remounts the example) and
# every link's aria-current (header, footer, side menu, swatches; the table of contents' follows the
# scroll position, so it is left out). The copy links' and the form's Privacy Policy link's href
# name the page's own path and do nothing (preventDefault), so those two hrefs are left out of the
# tree snapshots.
PICKER_SNAPSHOT = SNAPSHOT + CODES.replace("return {footer, cdn, sass, template};", "") + """
const article = S.querySelector("#content article.color-picker");
const selfLinks = new Set([...S.querySelectorAll("#content a.copy-to-clipboard, #content form a")]);
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
return {article: tree(article), cdn: tree(cdn), sass: tree(sass), template: tree(template),
        form: [...article.querySelectorAll(":scope > form input")].map(i => [i.name, i.type === "checkbox" ? i.checked : i.value]),
        current: [...document.querySelectorAll("a[aria-current]")].filter(a => !a.closest("#table-of-contents"))
          .map(a => [region(a), a.getAttribute("href"), a.getAttribute("aria-current")]),
        title: document.title, primary: getComputedStyle(document.documentElement).getPropertyValue("--femto-primary").trim(),
        themes: (() => { """ + THEME_LINKS + """ })(),
        url: location.pathname + location.search + location.hash, history: history.length, y: Math.round(scrollY)};
"""


def swatch(color):
    return f"#content article.color-picker > header a.femto-background-{color}"


def picker_snapshot(page):
    return page.js(PICKER_SNAPSHOT)


def expect_like_loaded(page, color, label, config=None):
    """Compare the page now with a fresh load of the color (its route, or the one page at
    ?theme=<color>#version-picker, loaded in a second tab), set there to the same configuration
    first when `config` = (base, conditional) is given."""
    now = picker_snapshot(page)
    here = page.driver.current_window_handle
    route = picker_route(color)
    page.new_tab(route)
    if config:
        choose(page, *config)
        expect_state(page, *config, color, label=f"{label}: the fresh load set to base {config[0]} cond {config[1]}: ")
    fresh = picker_snapshot(page)
    page.driver.close()
    page.switch(here)
    for k in ("article", "cdn", "sass", "template", "form", "current", "title", "primary", "themes"):
        page.eq(f"{label}: {k} as on a fresh load of {page.address(route)}", now[k], fresh[k])
    return now


@check("picker-swatch", PICKER)
def picker_swatch(page):
    """A theme color swatch (`article.color-picker > header a`) switches the theme in place: with
    "abc" typed in the example's Login field and its Privacy switch turned off, scrolled down (200 px
    on routes, the swatches 300 px below the viewport's top on the one page), a click on pumpkin's
    swatch keeps the scroll position and leaves the theme example (swatches with the check icon and
    aria-current on pumpkin, every swatch's aria-label "Pumpkin", the hgroup, the form, the footer
    code), the Usage samples, the example form's values (reset: Login empty, the switch on), every
    link's aria-current outside the table of contents, the title, --femto-primary and the theme
    stylesheets exactly as a fresh load of pumpkin has them (tree snapshots; the do-nothing links'
    href aside). On routes the URL becomes /docs/version-picker/pumpkin with one new history entry
    (the footer's "Version picker" link loses aria-current); on the one page it becomes
    /docs?theme=pumpkin#version-picker with no new entry (replaceState, Decision 8), and pumpkin's is
    the page's one theme stylesheet. The configuration survives a swap: with base 1 and conditional
    on, jade's swatch gives pico.classless.conditional.jade.min.css and the select and switch keep
    their state. On routes back returns to /docs/version-picker/pumpkin's state; on the one page a
    reload keeps jade (the URL carries it). Azure's swatch then gives the picker as a fresh load of
    azure has it (on the one page with no ?theme= and no theme stylesheet)."""
    example = "#content article.color-picker > form"
    if page.layout == "routes":
        y = 200
    else:
        y = page.js("return Math.round(S.querySelector('article.color-picker').getBoundingClientRect().top + scrollY - 300)")
    page.scroll_to(y)
    page.click(page.find(f"{example} input[name=login]"))
    page.key("abc")
    page.click(page.find(f"{example} input[name=switch]"))
    page.wait("the example form holds what was typed", "(() => { const f = S.querySelector(arguments[0]);"
              " return f.elements.login.value === 'abc' && !f.elements.switch.checked; })()", 1, args=(example,))
    page.scroll_to(y)
    before = picker_snapshot(page)
    page.click(swatch("pumpkin"), scroll=False)
    swapped(page, "pumpkin", "pumpkin")
    now = expect_like_loaded(page, "pumpkin", "pumpkin")
    page.expect("the swap changed the theme example", now["article"] != before["article"] and now["primary"] != before["primary"])
    if page.layout == "routes":
        page.eq("one new history entry", now["history"], before["history"] + 1)
    else:
        page.eq("the URL is pumpkin's", now["url"], "/docs?theme=pumpkin#version-picker")
        page.eq("no new history entry (replaceState)", now["history"], before["history"])
    page.eq("the scroll position is kept", now["y"], before["y"])
    choose(page, 1, 1)
    expect_state(page, 1, 1, "pumpkin", label="pumpkin, base 1 cond 1: ")
    page.click(swatch("jade"))
    swapped(page, "jade", "jade")
    expect_state(page, 1, 1, "jade", label="jade after the swap: ")
    if page.layout == "routes":
        page.driver.back()
        page.wait_navigated("/docs/version-picker/pumpkin", label="back to pumpkin")
        settle(page, "back")
        expect_state(page, 1, 1, "pumpkin", label="back: ")
    else:
        url = page.url()
        page.js("window.__bhMarker = 'before the reload'; setTimeout(() => location.reload(), 0); return true;")
        page.wait("the page reloaded", "window.__bhMarker === undefined && document.readyState === 'complete'", 15)
        page.wait_ready()
        page.eq("reload: the URL keeps ?theme=jade", page.url(), url)
        page.eq("reload: jade is the page's theme stylesheet", page.js(THEME_LINKS), ["jade"])
    choose(page, 0, 0)
    # Back where the swaps started: on the one page the side nav's current link follows the scroll
    # position, and the swatch's own scroll into view (from the select, below) can leave the
    # picker's heading under the line, in Quick start.
    page.scroll_to(y)
    page.click(swatch("azure"), scroll=False)
    swapped(page, "azure", "azure")
    expect_like_loaded(page, "azure", "azure")


# Records every change of the header logo's class from now on, and every click, with
# performance.now() times.
LOGO_WATCH = """
const logo = document.querySelector("body > header a[aria-label='femto homepage'] > svg");
window.__bhLogo = [];
const t = () => Math.round(performance.now());
new MutationObserver(() => __bhLogo.push([t(), logo.getAttribute("class")])).observe(logo, {attributes: true, attributeFilter: ["class"]});
addEventListener("click", () => __bhLogo.push([t(), "click"]), true);
return logo.getAttribute("class");
"""


@check("picker-logo", PICKER)
def picker_logo(page):
    """The header logo animates for 1 s after each route change (HeaderContext.jsx, Logo.jsx), and
    the picker's swatches change the route (on the one page, the theme and its ?theme=) in place:
    the logo's class is "femto-logo" on load; after a click on pumpkin's swatch it becomes
    "femto-logo animated" (within 2 s of the click, once the color's stylesheet has loaded) and
    "femto-logo" again 900 to 1500 ms later, with no other step."""
    page.eq("the logo is not animated on load", page.js(LOGO_WATCH), "femto-logo")
    page.click(swatch("pumpkin"))
    swapped(page, "pumpkin", "pumpkin")
    page.wait("the logo animates and stops", "window.__bhLogo.filter(e => e[1] !== 'click').length >= 2", 3,
              got=page.js("return window.__bhLogo"))
    page.sleep(0.6)
    tl = page.js("return window.__bhLogo")
    page.eq("the steps: click, animated, not animated", [e[1] for e in tl], ["click", "femto-logo animated", "femto-logo"],
            timeline=tl)
    page.expect("animated within 2 s of the click", tl[1][0] - tl[0][0] <= 2000, timeline=tl)
    page.expect("animated for 1 s", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)


@check("picker-swatch-focus", PICKER,
       oracle_bug={"fails": "focus stays on pumpkin's swatch",
                   "reason": "the oracle remounts the theme example on a color change, which removes the focused swatch "
                             "and drops focus to <body> (Tab then starts over at the first swatch); picker.js swaps the "
                             "color in place, so focus stays (PLAN.md, oracle-bug)"})
def picker_swatch_focus(page):
    """Keyboard use of the swatches: with pumpkin's swatch focused, Enter swaps to pumpkin (the
    route /docs/version-picker/pumpkin, or ?theme=pumpkin on the one page) and focus stays on that
    swatch; Tab then moves focus to the next swatch, orange's, and Enter on it swaps to orange with
    focus on it."""
    page.focus(swatch("pumpkin"))
    page.key("ENTER")
    swapped(page, "pumpkin", "pumpkin")
    focused = "document.activeElement === document.querySelector(arguments[0])"
    page.wait("focus stays on pumpkin's swatch", focused, 1, args=(swatch("pumpkin"),))
    page.key("TAB")
    page.wait("Tab moves focus to orange's swatch", focused, 1, args=(swatch("orange"),))
    page.key("ENTER")
    swapped(page, "orange", "orange")
    page.wait("focus stays on orange's swatch", focused, 1, args=(swatch("orange"),))


NO_RELOAD = "window.__bhSameDocument === true"


def expect_top(page, label):
    """The page scrolls to the top (smoothly: both sides' CSS has scroll-behavior: smooth)."""
    page.wait(f"{label}: scrolled to the top", "Math.round(scrollY) === 0", 3)
    settle(page, label)
    page.expect(f"{label}: no page load", page.js(f"return {NO_RELOAD}"))


@check("picker-links", PICKER)
def picker_links(page):
    """The other links to the picker keep its configuration (base 2 here). On routes they render
    in place, as Remix's Link did: scrolled 600 px down, the table of contents' first link ("Theme",
    whose href is the page itself) scrolls to the top with no page load, the URL and the history
    length unchanged. After jade's swatch, scrolled to the bottom, the footer's "Version picker" link
    makes the URL /docs/version-picker with one new history entry, scrolls to the top with no page
    load, and leaves the page as /docs/version-picker has it on load (theme example, samples, form
    values, every link's aria-current outside the table of contents, title, --femto-primary; the
    fresh load set to the same configuration). After pumpkin's swatch, scrolled 600 px down, the side
    menu's "Version picker" link does the same; back from there returns to pumpkin and forward to
    /docs/version-picker, with no page load. On the one page they are fragment links in the same
    document: after pumpkin's swatch, scrolled 600 px below the picker's heading, the side menu's
    link (#version-picker) puts the heading on the scroll-padding line with ?theme=pumpkin kept; the
    footer's "Version picker" link (/docs#version-picker), from azure scrolled to the bottom, does the
    same with no query; from jade it does the same with ?theme=jade kept (docs.js turns that link
    into a fragment navigation, since the browser's own would load /docs without the query), and
    back from there returns, in the same document with ?theme=jade and jade's stylesheet kept, to the
    bottom (or, as Chrome may restore it, to the entry's section heading). Each with no page load,
    base 2 kept, and a new history entry only when the URL changed."""
    choose(page, 2, None)
    expect_state(page, 2, 0, label="base 2: ")
    page.js("window.__bhSameDocument = true")
    if page.layout == "one-page":
        top = page.js("return Math.round(document.getElementById('version-picker').getBoundingClientRect().top + scrollY)")
        footer = "body > footer a[href='/docs#version-picker']"
        for color, link, name in (("pumpkin", "#documentation-menu a[href='#version-picker']", "side menu"),
                                  ("azure", footer, "footer"), ("jade", footer, "footer from jade")):
            page.click(swatch(color))
            swapped(page, color, color)
            page.scroll_to(page.js("return document.documentElement.scrollHeight - innerHeight") if link == footer else top + 600)
            settle(page, f"{name} link: scrolled")
            url, n = page.url(), page.js("return history.length")
            page.click(link, scroll=False)
            page.wait(f"{name} link: the URL is the picker's", "location.pathname + location.search + location.hash === arguments[0]",
                      3, args=(picker_url(color),))
            page.wait(f"{name} link: the heading is on the scroll-padding line",
                      f"Math.abs(({HEADING_LINE})('version-picker')) <= 2", 3)
            settle(page, f"{name} link")
            page.expect(f"{name} link: no page load", page.js(f"return {NO_RELOAD}"))
            page.eq(f"{name} link: a new history entry only for a new URL", page.js("return history.length"),
                    n + (url != picker_url(color)), url_before=url)
            expect_state(page, 2, 0, color, label=f"{name} link: ")
            if color == "jade":
                page.driver.back()
                page.wait("back: the URL leaves #version-picker, ?theme=jade kept",
                          "location.search === '?theme=jade' && location.hash !== '#version-picker'", 3, url_before=url)
                settle(page, "back")
                page.expect("back: no page load", page.js(f"return {NO_RELOAD}"))
                page.eq("back: no new history entry", page.js("return history.length"), n + (url != picker_url(color)))
                page.eq("back: jade is the one theme stylesheet", page.js(THEME_LINKS), ["jade"])
                page.expect("back: at the bottom again, or the entry's section heading on its line", page.js(
                    "return Math.ceil(scrollY + innerHeight) >= document.documentElement.scrollHeight - 1"
                    f" || Math.abs(({HEADING_LINE})(location.hash.slice(1))) <= 2"),
                            y=page.js("return scrollY"), url=page.url())
        return
    page.scroll_to(600)
    n = page.js("return history.length")
    page.click("#table-of-contents a[href='/docs/version-picker']")
    expect_top(page, "Theme")
    page.eq("Theme: the URL is unchanged", page.url(), "/docs/version-picker")
    page.eq("Theme: no new history entry", page.js("return history.length"), n)
    expect_state(page, 2, 0, label="Theme: ")

    # Each link is clicked where it already is in view, the page standing still: Firefox 160 drops a
    # smooth scroll asked for right after an instant one (the click's own scroll into view), on the
    # oracle and the static site alike (seen 2026-10-31). The footer is reached by scrolling to the
    # bottom; the side menu sticks.
    bottom = "return document.documentElement.scrollHeight - innerHeight"
    for color, link, name in (("jade", "body > footer a[href='/docs/version-picker']", "footer"),
                              ("pumpkin", "#documentation-menu a[href='/docs/version-picker']", "side menu")):
        page.click(swatch(color))
        page.wait_navigated(f"/docs/version-picker/{color}")
        page.scroll_to(page.js(bottom) if name == "footer" else 600)
        n = page.js("return history.length")
        page.click(link, scroll=False)
        page.wait_navigated("/docs/version-picker", label=f"{name} link: navigated to /docs/version-picker")
        expect_top(page, f"{name} link")
        page.eq(f"{name} link: one new history entry", page.js("return history.length"), n + 1)
        expect_state(page, 2, 0, label=f"{name} link: ")
        expect_like_loaded(page, "azure", f"{name} link", config=(2, 0))
        if name == "side menu":
            page.driver.back()
            page.wait_navigated("/docs/version-picker/pumpkin", label="back to pumpkin")
            settle(page, "back")
            page.expect("back: no page load", page.js(f"return {NO_RELOAD}"))
            expect_state(page, 2, 0, "pumpkin", label="back: ")
            page.driver.forward()
            page.wait_navigated("/docs/version-picker", label="forward to azure")
            settle(page, "forward")
            page.expect("forward: no page load", page.js(f"return {NO_RELOAD}"))


SWITCHER = """
const b = document.querySelector("#theme-switcher button"), a = document.querySelector(arguments[0]);
return {text: b.textContent.trim(), moon: !!b.querySelector(".theme-toggle.moon"), icon: !!b.querySelector(".icon-theme-toggle.theme-toggle"),
        theme: document.documentElement.getAttribute("data-theme"), stored: localStorage.getItem("femtoColorScheme"),
        header: a && a.getAttribute("aria-label")};
"""
HEADER_TOGGLE = "body > header nav ul.icons a[aria-label$='dark mode']"


@check("color-schemes-toggle", "/docs#color-schemes")
def color_schemes_toggle(page):
    """The Color schemes section's own switcher (`#theme-switcher button`, icon `.icon-theme-toggle.
    theme-toggle`: the oracle's SVG, the site's emoji of Decision 16) reads "Turn on dark mode" on a
    light OS; a click sets data-theme="dark", stores '"dark"', and both it ("Turn off dark mode",
    icon with `moon`) and the header toggle relabel; a second click returns to light. The header
    toggle drives it too."""
    def expect_switcher(theme, label):
        page.wait(f"switcher reads {label!r}", "(() => { const b = document.querySelector('#theme-switcher button');"
                  " return b.textContent.trim() === arguments[0] && !!b.querySelector('.theme-toggle.moon') === (arguments[0] === 'Turn off dark mode')"
                  " && document.querySelector(arguments[1]).getAttribute('aria-label') === arguments[0]; })()", 1,
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
    expect_switcher("light", "Turn on dark mode")
    page.click(HEADER_TOGGLE)
    expect_switcher("dark", "Turn off dark mode")
    page.url_kept("the URL is unchanged", url)
