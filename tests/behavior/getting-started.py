"""Getting started: the version picker (/docs/version-picker and its 19 color routes; 01 §2, Version
picker; picker.js in the static site) and the color-schemes page's own toggle (01 §2, small
widgets)."""
from behavior import SNAPSHOT, TOKENS, check

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
const footer = document.querySelector("#content article.color-picker > footer pre code");
const usage = [...document.querySelectorAll("#content section")].filter(s => /^(Usage from CDN|Usage with Sass|Starter HTML template)/.test((s.querySelector("h2") || {}).textContent || ""))
  .map(s => s.querySelector("pre code"));
const [cdn, sass, template] = usage;
return {footer, cdn, sass, template};
"""

PICKER_STATE = """
const smalls = [...document.querySelectorAll("#content section small")].filter(s => !s.closest("article, footer, .edit-on-github"));
return {select: document.querySelector(arguments[0]).value, conditional: document.querySelector(arguments[1]).checked,
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
        el = page.el(SELECT)
        page.js("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'})", el)
        Select(el).select_by_value(str(base))
    if cond is not None and page.js(f"return document.querySelector('{SWITCH}').checked") != bool(cond):
        want = f"document.querySelector('{SWITCH}').checked === {'true' if cond else 'false'}"
        page.click(SWITCH)
        deadline = time.time() + 1
        while not page.js(f"return {want}") and time.time() < deadline:
            time.sleep(0.05)
        if not page.js(f"return {want}"):
            page.note(f"the switch's click was lost (still {'off' if cond else 'on'} after 1 s); clicked it again")
            page.click(SWITCH)
        page.wait(f"the switch turns {'on' if cond else 'off'}", want, 1)


@check("picker-configuration", "/docs/version-picker")
def picker_configuration(page):
    """The version picker's configuration (on /docs/version-picker, azure): the select (`name=
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


@check("picker-code-highlight", "/docs/version-picker")
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


# What a color swap must leave exactly as the color's own page has it on load: the theme example
# (swatches, hgroup, form, footer code) and the three Usage samples, as tree snapshots, plus the
# title, the primary color, the example form's control values (the oracle remounts the example) and
# every link's aria-current (header, footer, side menu, swatches; the table of contents' follows the
# scroll position, so it is left out). The copy links' and the form's Privacy Policy link's href
# name the page's own path and do nothing (preventDefault), so those two hrefs are left out of the
# tree snapshots.
PICKER_SNAPSHOT = SNAPSHOT + CODES.replace("return {footer, cdn, sass, template};", "") + """
const article = document.querySelector("#content article.color-picker");
const selfLinks = new Set([...document.querySelectorAll("#content a.copy-to-clipboard, #content form a")]);
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
        url: location.pathname + location.search + location.hash, history: history.length, y: Math.round(scrollY)};
"""


def swatch(color):
    return f"#content article.color-picker > header a[href='/docs/version-picker{'' if color == 'azure' else '/' + color}']"


def picker_snapshot(page):
    return page.js(PICKER_SNAPSHOT)


def expect_like_loaded(page, color, label, config=None):
    """Compare the page now with a fresh load of the color's own route (loaded in a second tab),
    set there to the same configuration first when `config` = (base, conditional) is given."""
    now = picker_snapshot(page)
    here = page.driver.current_window_handle
    route = "/docs/version-picker" + ("" if color == "azure" else f"/{color}")
    page.new_tab(route)
    if config:
        choose(page, *config)
        expect_state(page, *config, color, label=f"{label}: the fresh load set to base {config[0]} cond {config[1]}: ")
    fresh = picker_snapshot(page)
    page.driver.close()
    page.switch(here)
    for k in ("article", "cdn", "sass", "template", "form", "current", "title", "primary"):
        page.eq(f"{label}: {k} as on {route}'s own page", now[k], fresh[k])
    return now


@check("picker-swatch", "/docs/version-picker")
def picker_swatch(page):
    """A theme color swatch (`article.color-picker > header a`) switches the theme in place: with
    "abc" typed in the example's Login field and its Privacy switch turned off, scrolled 200 px down,
    a click on pumpkin's swatch makes the URL /docs/version-picker/pumpkin with one new history
    entry, keeps the scroll position, and leaves the theme example (swatches with the check icon and
    aria-current on pumpkin, every swatch's aria-label "Pumpkin", the hgroup, the form, the footer
    code), the Usage samples, the example form's values (reset: Login empty, the switch on), every
    link's aria-current outside the table of contents (the footer's "Version picker" link loses it),
    the title and --femto-primary exactly as /docs/version-picker/pumpkin has them on load (tree
    snapshots; the do-nothing links' href aside). The configuration survives a swap: with base 1 and
    conditional on, jade's swatch gives pico.classless.conditional.jade.min.css and the select and
    switch keep their state. Back returns to /docs/version-picker/pumpkin's state, and azure's swatch
    to /docs/version-picker, as that route has it on load (its footer link current again)."""
    example = "#content article.color-picker > form"
    page.scroll_to(200)
    page.click(f"{example} input[name=login]")
    page.key("abc")
    page.click(f"{example} input[name=switch]")
    page.wait("the example form holds what was typed", "(() => { const f = document.querySelector(arguments[0]);"
              " return f.elements.login.value === 'abc' && !f.elements.switch.checked; })()", 1, args=(example,))
    page.scroll_to(200)
    before = picker_snapshot(page)
    page.click(swatch("pumpkin"), scroll=False)
    page.wait_navigated("/docs/version-picker/pumpkin")
    now = expect_like_loaded(page, "pumpkin", "pumpkin")
    page.expect("the swap changed the theme example", now["article"] != before["article"] and now["primary"] != before["primary"])
    page.eq("one new history entry", now["history"], before["history"] + 1)
    page.eq("the scroll position is kept", now["y"], before["y"])
    choose(page, 1, 1)
    expect_state(page, 1, 1, "pumpkin", label="pumpkin, base 1 cond 1: ")
    page.click(swatch("jade"))
    page.wait_navigated("/docs/version-picker/jade")
    expect_state(page, 1, 1, "jade", label="jade after the swap: ")
    page.driver.back()
    page.wait_navigated("/docs/version-picker/pumpkin", label="back to pumpkin")
    settle(page, "back")
    expect_state(page, 1, 1, "pumpkin", label="back: ")
    choose(page, 0, 0)
    page.click(swatch("azure"))
    page.wait_navigated("/docs/version-picker")
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


@check("picker-logo", "/docs/version-picker")
def picker_logo(page):
    """The header logo animates for 1 s after each route change (HeaderContext.jsx, Logo.jsx), and
    the picker's swatches change the route in place: the logo's class is "femto-logo" on load; after
    a click on pumpkin's swatch it becomes "femto-logo animated" (within 2 s of the click, once the
    color's stylesheet has loaded) and "femto-logo" again 900 to 1500 ms later, with no other
    step."""
    page.eq("the logo is not animated on load", page.js(LOGO_WATCH), "femto-logo")
    page.click(swatch("pumpkin"))
    page.wait_navigated("/docs/version-picker/pumpkin")
    page.wait("the logo animates and stops", "window.__bhLogo.filter(e => e[1] !== 'click').length >= 2", 3,
              got=page.js("return window.__bhLogo"))
    page.sleep(0.6)
    tl = page.js("return window.__bhLogo")
    page.eq("the steps: click, animated, not animated", [e[1] for e in tl], ["click", "femto-logo animated", "femto-logo"],
            timeline=tl)
    page.expect("animated within 2 s of the click", tl[1][0] - tl[0][0] <= 2000, timeline=tl)
    page.expect("animated for 1 s", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)


@check("picker-swatch-focus", "/docs/version-picker",
       oracle_bug={"fails": "focus stays on pumpkin's swatch",
                   "reason": "the oracle remounts the theme example on a color change, which removes the focused swatch "
                             "and drops focus to <body> (Tab then starts over at the first swatch); picker.js swaps the "
                             "color in place, so focus stays (PLAN.md, oracle-bug)"})
def picker_swatch_focus(page):
    """Keyboard use of the swatches: with pumpkin's swatch focused, Enter makes the URL
    /docs/version-picker/pumpkin and focus stays on that swatch; Tab then moves focus to the next
    swatch, orange's, and Enter on it makes the URL /docs/version-picker/orange with focus on it."""
    page.focus(swatch("pumpkin"))
    page.key("ENTER")
    page.wait_navigated("/docs/version-picker/pumpkin")
    focused = "document.activeElement === document.querySelector(arguments[0])"
    page.wait("focus stays on pumpkin's swatch", focused, 1, args=(swatch("pumpkin"),))
    page.key("TAB")
    page.wait("Tab moves focus to orange's swatch", focused, 1, args=(swatch("orange"),))
    page.key("ENTER")
    page.wait_navigated("/docs/version-picker/orange")
    page.wait("focus stays on orange's swatch", focused, 1, args=(swatch("orange"),))


NO_RELOAD = "window.__bhSameDocument === true"


def expect_top(page, label):
    """The page scrolls to the top (smoothly: both sides' CSS has scroll-behavior: smooth)."""
    page.wait(f"{label}: scrolled to the top", "Math.round(scrollY) === 0", 3)
    settle(page, label)
    page.expect(f"{label}: no page load", page.js(f"return {NO_RELOAD}"))


@check("picker-links", "/docs/version-picker")
def picker_links(page):
    """The other links to the picker's routes render in place, as Remix's Link did, so the
    configuration (base 2 here) survives them: scrolled 600 px down, the table of contents' first
    link ("Theme", whose href is the page itself) scrolls to the top with no page load, the URL and
    the history length unchanged. After jade's swatch, scrolled to the bottom, the footer's "Version
    picker" link makes the URL /docs/version-picker with one new history entry, scrolls to the top
    with no page load, and leaves the page as /docs/version-picker has it on load (theme example,
    samples, form values, every link's aria-current outside the table of contents, title,
    --femto-primary; the fresh load set to the same configuration). After pumpkin's swatch, scrolled
    600 px down, the side menu's "Version picker" link does the same; back from there returns to pumpkin and forward to
    /docs/version-picker, with no page load."""
    choose(page, 2, None)
    expect_state(page, 2, 0, label="base 2: ")
    page.js("window.__bhSameDocument = true")
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


@check("color-schemes-toggle", "/docs/color-schemes")
def color_schemes_toggle(page):
    """/docs/color-schemes' own switcher (`#theme-switcher button`, icon `.icon-theme-toggle.
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
    page.eq("the URL is unchanged", page.url(), url)
