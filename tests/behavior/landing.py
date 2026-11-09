"""Landing: the homepage's widgets (demo.js): the hero's one <link> line with its copy button; the
femto off and on block, everyday markup in two declarative shadow roots, the inner one linking femto,
with a switch that turns that link off and on; the theme swatches, which recolor the page in place;
and the typing demo, a hand-written loop that drives the form, as the Remix site's TypeIt demo did
(homepage/Demo). The demo has a pause button and a paused start under prefers-reduced-motion (WCAG
2.2.2): demo-pause and demo-reduced-motion hold them.

comparison-toggle is gone with the comparison it checked, femto's markup beside a utility
framework's, whose code samples followed the page's scheme: the femto off and on block took its
place (the owner, 2026-11-09), and femto-block-scheme checks that the block follows the scheme."""
import time

from behavior import COPY_SPY, PICKER_ORDER, check, expect_forced_focus, expect_name

GROUP = "landing"

# The demo's phases in order, named by the form's state (see PHASE below), and what the code
# sample shows while the form is in each: `has` substrings that must all appear and `not` ones that
# must not, in one snapshot of the code during the phase (text with the cursor "|" removed and
# whitespace collapsed, so line layout does not matter).
CYCLE = ["email", "invalid", "invalid-helper", "group-subscribe", "search", "search-busy", "date", "date-next",
         "select", "checkbox", "checkbox-checked", "switch-on", "switch-off", "range-25", "range-50"]
MARKERS = {
    "email": {"has": ["<form", "<input", 'type="email"', 'placeholder="Enter your email"'],
              "not": ["aria-invalid", "<small", "<button", 'role="']},
    "invalid": {"has": ['aria-invalid="true"'], "not": ["<small"]},
    "invalid-helper": {"has": ['aria-invalid="true"', "<small>", "Please enter a valid email!", "</small>"]},
    "group-subscribe": {"has": ["<fieldset", 'role="group"', "<button", 'type="submit"', "Subscribe", "</fieldset>"],
                        "not": ["aria-invalid", "<small"]},
    "search": {"has": ['role="search"', 'type="search"', 'placeholder="Search"', "Search"],
               "not": ["aria-busy", "Subscribe", "<fieldset"]},
    "search-busy": {"has": ['aria-busy="true"', "Search..."]},
    "date": {"has": ['type="date"'], "not": ["<button", "placeholder=", 'role="']},
    "date-next": {"has": ['type="date"', "<button>", "Next"]},
    "select": {"has": ["<select>", "<option>Select...</option>"], "not": ["<input"]},
    "checkbox": {"has": ["<label>", 'type="checkbox"', "Publish on my profile"], "not": ["checked", 'role="switch"', "<select"]},
    "checkbox-checked": {"has": ['type="checkbox"', "checked"], "not": ['role="switch"']},
    "switch-on": {"has": ['role="switch"', "checked"]},
    "switch-off": {"has": ['role="switch"'], "not": ["checked"]},
    "range-25": {"has": ['type="range"', 'value="25"', "Brightness"]},
    "range-50": {"has": ['type="range"', 'value="50"']},
}

# Installed once per check: classifies the demo form's state into a phase on every mutation of the
# demo article, and keeps one segment per phase: its start and end time, the form fields' last
# state, whether one code snapshot during it met the phase's markers, and the code's single-character
# growth steps (typing).
RECORDER = r"""
const markers = arguments[0];
const art = document.querySelector(".demo > article");
const form = art.querySelector("form"), code = art.querySelector("footer code");
const norm = (s) => s.replace(/\|/g, "").replace(/ /g, " ").replace(/\s+/g, " ").trim();
const fields = () => {
  const i = form.querySelector("input:not([type=checkbox]):not([type=range])"), b = form.querySelector("button"),
        s = form.querySelector("select"), c = form.querySelector("input[type=checkbox]"), r = form.querySelector("input[type=range]"),
        h = form.querySelector("small");
  return {role: form.getAttribute("role"),
    input: i && {type: i.getAttribute("type"), placeholder: i.getAttribute("placeholder"), invalid: i.getAttribute("aria-invalid"),
                 disabled: i.disabled, value: i.value},
    helper: h && h.textContent, button: b && {type: b.getAttribute("type"), text: b.textContent, busy: b.getAttribute("aria-busy")},
    select: s && [...s.options].map(o => o.textContent), checkbox: c && {role: c.getAttribute("role"), checked: c.checked,
    label: c.closest("label") && c.closest("label").textContent.trim()},
    range: r && {value: r.value, label: r.closest("label") && r.closest("label").textContent.trim()}};
};
const phase = (f) => {
  if (f.range) return f.range.value === "50" ? "range-50" : f.range.value === "25" ? "range-25" : "range-" + f.range.value;
  if (f.checkbox) return f.checkbox.role === "switch" ? (f.checkbox.checked ? "switch-on" : "switch-off") : (f.checkbox.checked ? "checkbox-checked" : "checkbox");
  if (f.select) return "select";
  if (!f.input) return "empty";
  if (f.input.type === "date") return f.button ? "date-next" : "date";
  if (f.role === "search") return f.button && f.button.busy === "true" ? "search-busy" : "search";
  if (f.role === "group") return "group-subscribe";
  if (f.input.invalid === "true") return f.helper ? "invalid-helper" : "invalid";
  if (f.input.type === "email") return "email";
  return "initial";
};
const meets = (p, text) => { const m = markers[p]; return !!m && m.has.every(s => text.includes(s)) && !(m.not || []).some(s => text.includes(s)); };
window.__bhDemo = {segments: [], typed: 0, deleted: 0, t0: performance.now()};
let lastText = norm(code.textContent), lastRaw = code.textContent.replace(/\|/g, "");
const rec = () => {
  const f = fields(), p = phase(f), now = Math.round(performance.now() - __bhDemo.t0), text = norm(code.textContent);
  const raw = code.textContent.replace(/\|/g, "");
  if (raw.length === lastRaw.length + 1) __bhDemo.typed++;
  if (raw.length === lastRaw.length - 1) __bhDemo.deleted++;
  lastRaw = raw;
  let seg = __bhDemo.segments[__bhDemo.segments.length - 1];
  if (!seg || seg.phase !== p) {
    if (seg) seg.end = now;
    seg = {phase: p, start: now, end: null, met: false, last: null, values: [], code: null};
    __bhDemo.segments.push(seg);
  }
  seg.last = f;
  if (f.input && f.input.value && seg.values[seg.values.length - 1] !== f.input.value) seg.values.push(f.input.value);
  if (!seg.met && meets(p, text)) { seg.met = true; seg.code = text; }
  if (!seg.met) seg.code = text;
  lastText = text;
};
rec();
new MutationObserver(rec).observe(art, {subtree: true, childList: true, attributes: true, characterData: true});
form.addEventListener("input", rec, true);
return __bhDemo.segments[0];
"""


def phases(segments):
    """Consecutive phases, a leading "initial" (the form before the demo's first phase) dropped."""
    out = [s["phase"] for s in segments]
    while out and out[0] == "initial":
        out.pop(0)
    return out


def check_fields(page, seg, label):
    """The form's own state at the end of a phase, beyond what names the phase."""
    f, p = seg["last"], seg["phase"]
    if p == "email" and seg["values"]:
        page.expect(f"{label}: the email is typed letter by letter", len(seg["values"]) >= 10 and seg["values"][-1] == "invalid@example"
                    and all("invalid@example".startswith(v) for v in seg["values"]), values=seg["values"])
    if p == "invalid-helper":
        page.eq(f"{label}: the helper", f["helper"], "Please enter a valid email!")
    if p == "group-subscribe":
        page.eq(f"{label}: the submit button", [f["button"]["type"], f["button"]["text"]], ["submit", "Subscribe"])
    if p == "search":
        page.eq(f"{label}: search input and button", [f["input"]["type"], f["input"]["placeholder"], f["button"]["text"]],
                ["search", "Search", "Search"])
    if p == "search-busy":
        page.eq(f"{label}: busy button, disabled input", [f["button"]["text"], f["input"]["disabled"]], ["Search...", True])
        # As the form has it: the code's search input carries the disabled attribute that phase.busy
        # sets (demo.js).
        page.expect(f"{label}: the code's input is disabled, as the form's is",
                    'placeholder="Search" disabled' in (seg["code"] or ""), code=seg["code"])
    if p == "date":
        page.expect(f"{label}: a date value, enabled", bool(f["input"]["value"]) and len(f["input"]["value"]) == 10
                    and f["input"]["value"][4] == "-" and not f["input"]["disabled"], input=f["input"])
    if p == "date-next":
        page.eq(f"{label}: the Next button", f["button"]["text"], "Next")
        # As the code shows it, <button>Next</button>: femto makes only a button[type=submit] full width
        # (demo.js phase.next).
        page.eq(f"{label}: the Next button has no type, as in the code", f["button"]["type"], None)
    if p == "select":
        page.eq(f"{label}: the select's option", f["select"], ["Select..."])
    if p in ("checkbox", "checkbox-checked", "switch-on", "switch-off"):
        page.eq(f"{label}: the checkbox label", f["checkbox"]["label"], "Publish on my profile")
    if p in ("range-25", "range-50"):
        page.eq(f"{label}: the range label", f["range"]["label"], "Brightness")


def watch(page, until, timeout):
    """Poll the recorder once a second until until(segments) holds or timeout s pass."""
    end = time.time() + timeout
    while True:
        d = page.js("return window.__bhDemo")
        if until(d["segments"]) or time.time() > end:
            return d
        time.sleep(1)


@check("demo-loop", "/")
def demo_loop(page):
    """The homepage demo (`.demo > article`: a form and a code sample in `footer code`)
    runs its whole sequence and starts over, the form following the code. Watched for up to 100 s,
    the form's phases are exactly: email, invalid, invalid-helper, group-subscribe, search,
    search-busy, date, date-next, select, checkbox, checkbox-checked, switch-on, switch-off,
    range-25, range-50, then email and invalid again (the loop). During each phase one snapshot of
    the code shows that phase's markup (e.g. aria-invalid="true", <fieldset role="group">,
    aria-busy="true", type="date", <select>, role="switch", value="50"; tests/behavior/landing.py,
    MARKERS), the form's fields carry the phase's values (the email typed letter by letter to
    invalid@example, the helper text, Subscribe, Search..., Next, Select..., Publish on my profile,
    Brightness; on the one page the Next button has no type attribute, as the code's <button>Next</button>
    has none, and the busy phase's code gives the search input the disabled attribute the form's
    input has), and the code is typed: at least 50 one-character insertions."""
    page.js(RECORDER, MARKERS)
    want = CYCLE + ["email", "invalid"]
    d = watch(page, lambda segs: len(phases(segs)) >= len(want), 100)
    got = phases(d["segments"])[:len(want)]
    page.note(f"phases: {[(s['phase'], s['start']) for s in d['segments']]}")
    page.eq("the phases, in order, then the loop", got, want)
    lead = 1 if d["segments"][0]["phase"] == "initial" else 0
    for s in d["segments"][lead:lead + len(want) - 1]:   # the last one is still running
        page.expect(f"{s['phase']} at {s['start']} ms: the code shows its markup", s["met"],
                    markers=MARKERS[s["phase"]], code=s["code"])
        check_fields(page, s, f"{s['phase']} at {s['start']} ms")
    page.expect("the code is typed (one-character insertions)", d["typed"] >= 50, typed=d["typed"], deleted=d["deleted"])
    page.note(f"the loop restarts at {d['segments'][lead + len(CYCLE)]['start']} ms")


def layout(page):
    """'large' when one line of the code holds both of the email input's attributes, 'small' when
    they sit on lines of their own; the code's rendered text (innerText) gives the lines."""
    lines = page.js("return document.querySelector('.demo > article footer code').innerText.split('\\n')")
    lines = [ln.replace("|", "") for ln in lines]
    both = any('type="email"' in ln and 'placeholder="Enter your email"' in ln for ln in lines)
    apart = any('type="email"' in ln and "placeholder" not in ln for ln in lines) and any(
        'placeholder="Enter your email"' in ln and "type=" not in ln for ln in lines)
    return "large" if both else "small" if apart else None, lines


@check("demo-variant", "/", width=1280, height=800)
def demo_variant(page):
    """The demo's code sample has two layouts, picked by innerWidth at 1280 px: at 1280 the large
    one (the email input's type and placeholder on one line, as innerText renders it), and after a
    resize to 1279 the small one (each attribute on its own line), with the demo started over at
    its first phase (an email input with no value); back at 1280, the large one again, started
    over too. Each switch shows within 3 s."""
    page.js(RECORDER, MARKERS)
    page.eq("large at 1280 on load", layout(page)[0], "large", lines=layout(page)[1])
    for w, want in ((1279, "small"), (1280, "large"), (375, "small")):
        page.sleep(2.5)   # let the demo move on first, so a restart shows
        page.resize(w, 800 if w > 375 else 812)
        deadline = time.time() + 3
        while layout(page)[0] != want and time.time() < deadline:
            time.sleep(0.1)
        got, lines = layout(page)
        page.eq(f"{want} at {w}", got, want, lines=lines)
        st = page.js("""const f = document.querySelector('.demo > article form'), i = f.querySelector('input');
          return {input: !!i && !['checkbox', 'range', 'date'].includes(i.getAttribute('type')), value: i ? i.value : null,
                  role: f.getAttribute('role'), invalid: i ? i.getAttribute('aria-invalid') : null}""")
        page.expect(f"started over at {w}: the first phase's email input, empty", st["input"] and st["value"] == ""
                    and st["role"] is None and st["invalid"] is None, **st)


TOGGLE = "body > header nav ul.icons button:has(> span[role=img][aria-label$='dark mode'])"   # the header's toggle button


# Records every change of the demo's state from now on (its code text, the form's markup and its
# fields' values), with times from the start, through a MutationObserver and a 100 ms poll (a
# field's value property changes no markup).
DEMO_WATCH = r"""
const art = document.querySelector(".demo > article");
const code = art.querySelector("footer code"), form = art.querySelector("form");
const state = () => [code.textContent, form.innerHTML,
  ...[...form.querySelectorAll("input, select, button")].map(e => e.type === "checkbox" ? String(e.checked) : e.value)].join("\u0001");
clearInterval(window.__bhDemoPoll);
window.__bhDemoOff = {changes: [], last: state(), t0: performance.now()};
const tick = () => { const s = state(); if (s !== __bhDemoOff.last) { __bhDemoOff.changes.push(Math.round(performance.now() - __bhDemoOff.t0)); __bhDemoOff.last = s; } };
new MutationObserver(tick).observe(art, {subtree: true, childList: true, attributes: true, characterData: true});
window.__bhDemoPoll = setInterval(tick, 100);
const r = art.getBoundingClientRect();
return r.bottom <= 0 ? "above" : r.top >= innerHeight ? "below" : "on";
"""


@check("demo-offscreen", "/")
def demo_offscreen(page):
    """The homepage demo (`.demo > article`) runs only while it is on screen: it changes
    within 4 s on screen at the top; scrolled until it is above the viewport, and after 2 s for the
    form changes already scheduled to settle, its code and form do not change for 7 s; scrolled back
    into view, it changes again within 5 s."""
    page.eq("the demo starts on screen", page.js(DEMO_WATCH), "on")
    page.wait("the demo changes on screen", "window.__bhDemoOff.changes.length > 0", 4)
    y = page.js("const r = document.querySelector('.demo > article').getBoundingClientRect(); return Math.ceil(r.bottom + scrollY + 50)")
    page.scroll_to(y)
    page.sleep(2)
    page.eq("scrolled, the demo is above the viewport", page.js(DEMO_WATCH), "above")
    page.sleep(7)
    page.eq("no change for 7 s while the demo is above the viewport", page.js("return window.__bhDemoOff.changes"), [])
    page.scroll_to(0)
    page.eq("back at the top, the demo is on screen", page.js(DEMO_WATCH), "on")
    page.wait("back on screen, the demo changes again within 5 s", "window.__bhDemoOff.changes.length > 0", 5)


# The typing demo's pause button (demo.js; WCAG 2.2.2), and the demo's state around it:
# the button's own state, and the play state of every animation in the code sample (the cursor's
# blink), which no mutation shows.
PAUSE = ".demo > article button[data-demo-pause]"
PAUSE_STATE = """
const b = document.querySelector(arguments[0]);
const code = document.querySelector(".demo > article footer code");
return b && {hidden: b.hidden, shown: b.getClientRects().length > 0 && getComputedStyle(b).visibility !== "hidden",
             type: b.getAttribute("type"), text: b.textContent.trim(),
             cursor: code.getAnimations({subtree: true}).map(a => a.playState)};
"""


def expect_button(page, label, text, cursor):
    """The pause button reads `text` (within 1 s) and the code's animations are all `cursor`."""
    page.wait(f"{label}: the button reads {text}", "document.querySelector(arguments[0]).textContent.trim() === arguments[1]", 1,
              args=(PAUSE, text))
    s = page.js(PAUSE_STATE, PAUSE)
    page.expect(f"{label}: the cursor's blink is {cursor}", s["cursor"] and all(c == cursor for c in s["cursor"]), **s)


@check("demo-pause", "/")
def demo_pause(page):
    """The typing demo's `button[data-demo-pause]`, hidden in the markup (nothing runs without
    JavaScript), is shown once demo.js runs: rendered, type="button", reading "Pause", with the
    cursor blinking (its animation running). The demo changes within 4 s while it plays. A click on
    the button relabels it "Play" and pauses the demo: from then on its code and its form (markup and
    field values, DEMO_WATCH) do not change for 6 s, and the cursor's blink is paused. A second click
    relabels it "Pause", the blink runs again, and the demo changes again within 4 s."""
    s = page.js(PAUSE_STATE, PAUSE)
    page.expect("the demo has a pause button", s is not None)
    page.eq("the script shows it: not hidden, rendered, type=button, reading Pause",
            [s["hidden"], s["shown"], s["type"], s["text"]], [False, True, "button", "Pause"])
    page.eq("the demo starts on screen", page.js(DEMO_WATCH), "on")
    page.wait("the demo changes while it plays", "window.__bhDemoOff.changes.length > 0", 4)
    expect_button(page, "playing", "Pause", "running")
    page.click(PAUSE)
    expect_button(page, "Pause clicked", "Play", "paused")
    page.js(DEMO_WATCH)   # record from here
    page.sleep(6)
    page.eq("paused: no change to the code or the form for 6 s", page.js("return window.__bhDemoOff.changes"), [])
    expect_button(page, "still paused", "Play", "paused")
    page.click(PAUSE)
    expect_button(page, "Play clicked", "Pause", "running")
    page.wait("playing again, the demo changes within 4 s", "window.__bhDemoOff.changes.length > 0", 4)


@check("demo-reduced-motion", "/", motion="reduce")
def demo_reduced_motion(page):
    """Under prefers-reduced-motion: reduce the typing demo starts paused: once demo.js runs, its
    pause button is shown reading "Play", the cursor's blink is paused, the code shows the first
    phase's markup (the email input's type and placeholder, no aria-invalid) and the form its one
    email input, empty and valid; neither the code nor the form changes for 6 s (unpaused, the first
    phase would start 1.75 s after load). A click on Play relabels the button "Pause", the blink
    runs, and the demo changes within 4 s: the viewer can still start it."""
    s = page.js(PAUSE_STATE, PAUSE)
    page.expect("the demo has a pause button", s is not None)
    page.eq("the script shows it reading Play", [s["hidden"], s["shown"], s["type"], s["text"]], [False, True, "button", "Play"])
    expect_button(page, "reduced motion", "Play", "paused")
    page.eq("the demo is on screen", page.js(DEMO_WATCH), "on")
    first = page.js("""const art = document.querySelector('.demo > article'), f = art.querySelector('form');
      const i = [...f.querySelectorAll('input, select, button')];
      return {code: art.querySelector('footer code').textContent.replace(/\\|/g, '').replace(/\\s+/g, ' ').trim(),
              fields: i.map(e => [e.tagName.toLowerCase(), e.getAttribute('type'), e.value, e.getAttribute('aria-invalid')]),
              role: f.getAttribute('role')};""")
    page.expect("the code shows the first phase's markup", all(m in first["code"] for m in MARKERS["email"]["has"])
                and not any(m in first["code"] for m in MARKERS["email"]["not"]), **first)
    page.eq("the form holds the first phase's email input, empty and valid", [first["role"], first["fields"]],
            [None, [["input", "email", "", None]]])
    page.sleep(6)
    page.eq("no change to the code or the form for 6 s", page.js("return window.__bhDemoOff.changes"), [])
    page.click(PAUSE)
    expect_button(page, "Play clicked", "Pause", "running")
    page.wait("playing, the demo changes within 4 s", "window.__bhDemoOff.changes.length > 0", 4)


# --- The hero's <link> line -----------------------------------------------------------------------
HERO_LINK = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@leoherzog/femto@3/dist/femto.min.css">'
HERO_COPY = "main > section.hero .hook .code > button[data-copy-link]"


@check("hero-link-copy", "/")
def hero_link_copy(page):
    """The hero holds one code block, `.hero .hook .code`, whose code is exactly femto's jsDelivr
    <link> line, the @3 one from Quick start, with site.js's copy button: named "Copy code", a click
    on it copies exactly that line once and its tooltip reads "Copied"."""
    page.js(COPY_SPY)
    s = page.js("""const c = document.querySelectorAll('main > section.hero .hook .code');
      return {n: c.length, code: c[0]?.querySelector('pre code')?.textContent ?? null, button: !!document.querySelector(arguments[0])};""",
                HERO_COPY)
    page.eq("one code block in the hero: the <link> line, with a copy button", [s["n"], s["code"], s["button"]], [1, HERO_LINK, True])
    button = page.el(HERO_COPY)
    expect_name(page, "the copy button is named Copy code", button, "Copy code")
    page.click(button)
    page.wait("a click copies", "window.__bhCopied.length > 0", 1)
    page.eq("it copies the <link> line, once", page.js("return window.__bhCopied.map(c => c.text)"), [HERO_LINK])
    page.wait("its tooltip reads Copied", "document.querySelector(arguments[0]).getAttribute('data-tooltip') === 'Copied'", 0.5,
              args=(HERO_COPY,))


# --- femto off and on -----------------------------------------------------------------------------
# The block (demo.js, 1): its frame, the inner host and its shadow root, femto's link there, and the
# switch.
BLOCK = """
const frame = document.querySelector('main > section.proof > div[data-femto-demo]');
const host = frame?.shadowRoot?.firstElementChild ?? null, root = host?.shadowRoot ?? null;
const femto = root?.querySelector('link[href="/vendor/femto/dist/femto.min.css"]') ?? null;
const label = document.querySelector('main > section.proof label[data-femto-switch]');
const sw = label?.querySelector('input') ?? null;
"""
SWITCH = "main > section.proof label[data-femto-switch] > input"

# What femto does to the block: whether its stylesheet applies in the inner root, and four styles it
# sets there (the inner host's font family and background, the nav's display, and whether the submit
# button is as wide as its form), with the switch's state and the host's color scheme and color.
LOOK = BLOCK + """
const cs = (e) => getComputedStyle(e);
const form = root.querySelector('form'), button = form.querySelector('button[type=submit]');
const sheets = [...root.styleSheets].filter(s => s.href?.endsWith('/vendor/femto/dist/femto.min.css') && !s.disabled);
return {femto: !!femto && !femto.disabled && sheets.length === 1 && sheets[0].cssRules.length > 100,
        font: cs(host).fontFamily, background: cs(host).backgroundColor, nav: cs(root.querySelector('nav')).display,
        wide: Math.abs(button.getBoundingClientRect().width - form.getBoundingClientRect().width) < 1,
        checked: sw ? sw.checked : null, scheme: cs(host).colorScheme, color: cs(host).color,
        page: cs(document.documentElement).backgroundColor};
"""
TRANSPARENT = "rgba(0, 0, 0, 0)"


def styled(s):
    """The block in femto's styles: its sheet applies, the nav is a flex row, the submit button fills its
    form, and the host has a background."""
    return s["femto"] and s["nav"] == "flex" and s["wide"] and s["background"] != TRANSPARENT


def unstyled(s):
    """The block in the browser's own styles: no femto sheet applies, the nav is a block, the button
    is as wide as its label, and the host has no background."""
    return not s["femto"] and s["nav"] != "flex" and not s["wide"] and s["background"] == TRANSPARENT


def look(page):
    return page.js(LOOK)


@check("femto-switch", "/")
def femto_switch(page):
    """The homepage's femto off and on block: `section.proof > div[data-femto-demo]`'s shadow root
    holds one element, a div with a shadow root of its own, whose first element is femto's stylesheet
    link, /vendor/femto/dist/femto.min.css, loaded, with no other <link> or <style>, and the markup
    after it is the code sample's text under the block (`section.proof > .code`), node for node
    (whitespace collapsed); it has no class attribute. The switch, an input type="checkbox"
    role="switch" in label[data-femto-switch], is shown once demo.js runs, checked, and named
    "femto". On load the block is in femto's styles (its sheet applies, the nav is a flex row, the
    submit button fills its form, the host has a background). A click on the switch unchecks it and
    turns femto off in the block alone: the link is disabled, the nav is a block, the button is no
    wider than its label, the host has no background and another font; the page keeps femto. A
    second click turns it on again, with the font and background of the load. The URL and history
    are kept, and nothing is stored."""
    s = page.js(BLOCK + r"""
      const norm = (node) => {
        const walk = (n) => {
          for (const c of [...n.childNodes]) {
            if (c.nodeType === 3) { const t = c.data.replace(/\s+/g, ' ').trim(); if (!t) c.remove(); else c.data = t; }
            else if (c.nodeType === 8) c.remove();
            else walk(c);
          }
        };
        walk(node);
        const div = document.createElement('div'); div.append(node); return div.innerHTML;
      };
      const out = {frame: !!frame, outer: frame?.shadowRoot?.children.length ?? 0, inner: !!root};
      if (!root) return out;
      out.first = root.firstElementChild?.outerHTML;
      out.styles = root.querySelectorAll('link, style').length;
      out.classes = root.querySelectorAll('[class]').length;
      const live = document.createDocumentFragment(), nodes = [...root.childNodes];
      for (const n of nodes.slice(nodes.indexOf(femto) + 1)) live.append(n.cloneNode(true));
      // The live form's method="dialog", which keeps it from submitting, is not in the sample.
      for (const f of live.querySelectorAll('form[method=dialog]')) f.removeAttribute('method');
      const t = document.createElement('template');
      t.innerHTML = document.querySelector('main > section.proof > .code pre code').textContent;
      const [x, y] = [norm(live), norm(t.content.cloneNode(true))];
      out.same = x === y && x.length > 300;
      if (!out.same) out.sample = [x.slice(0, 300), y.slice(0, 300)];
      out.switch = sw && {hidden: label.hidden, shown: label.getClientRects().length > 0, type: sw.type,
                          role: sw.getAttribute('role'), checked: sw.checked};
      return out;""")
    page.expect("two shadow roots, one element in the outer", s["frame"] and s["inner"] and s["outer"] == 1, **s)
    page.eq("the inner root's first element is femto's link, and its only stylesheet",
            [s["first"], s["styles"]], ['<link rel="stylesheet" href="/vendor/femto/dist/femto.min.css">', 1])
    page.expect("the code sample under the block is its markup", s["same"], **s)
    page.eq("the markup has no class attribute", s["classes"], 0)
    page.eq("the switch is shown, a checked role=switch checkbox", s["switch"],
            {"hidden": False, "shown": True, "type": "checkbox", "role": "switch", "checked": True})
    expect_name(page, "the switch is named femto", page.el(SWITCH), "femto")
    url = page.url()
    on = look(page)
    page.expect("on load the block is in femto's styles", styled(on), **on)
    page.click(SWITCH)
    page.wait("a click turns femto off in the block", f"(() => {{ {LOOK} }})().femto === false", 1)
    off = look(page)
    page.expect("off: the block is in the browser's own styles, unchecked", unstyled(off) and off["checked"] is False
                and off["font"] != on["font"], **off, on_font=on["font"])
    page.expect("off: the page keeps femto", page.js("""return [...document.styleSheets].some(s => s.href?.endsWith('/vendor/femto/dist/femto.min.css')
      && !s.disabled) && getComputedStyle(document.querySelector('main > section.hero a[role=button]')).display !== 'inline'"""))
    page.click(SWITCH)
    page.wait("a second click turns femto on again", f"(() => {{ {LOOK} }})().femto === true", 1)
    again = look(page)
    page.expect("on again: femto's styles, checked, the font and background of the load", styled(again) and again["checked"] is True
                and again["font"] == on["font"] and again["background"] == on["background"], **again)
    page.url_kept("the URL and history are kept", url)
    page.eq("nothing is stored", page.js("return localStorage.length"), 0)


@check("femto-switch-keyboard", "/")
def femto_switch_keyboard(page):
    """The femto switch is in the tab order right after the typing demo's Pause button: Tab from
    the Pause button focuses it, and in forced colors (Chrome), which drop femto's box-shadow ring,
    it shows an outline. Space turns femto off in the block and unchecks it; Space again turns it on
    and checks it, with focus kept on the switch throughout."""
    page.focus(PAUSE)
    page.tab()
    page.eq("Tab from the Pause button reaches the switch", page.js("return document.activeElement === document.querySelector(arguments[0])", SWITCH), True)
    expect_forced_focus(page, "the switch")
    for want in (False, True):
        page.key(" ")
        page.wait(f"Space: femto {'on' if want else 'off'}", f"(() => {{ {LOOK} }})().femto === {str(want).lower()}", 1)
        s = look(page)
        page.expect(f"Space: the switch {'checked' if want else 'unchecked'}, the block {'styled' if want else 'unstyled'}, focus kept",
                    s["checked"] is want and (styled(s) if want else unstyled(s))
                    and page.js("return document.activeElement === document.querySelector(arguments[0])", SWITCH), **s)


@check("femto-block-nojs", "/", javascript=False)
def femto_block_nojs(page):
    """With JavaScript off the block still renders from its declarative shadow roots, in femto's
    styles (its sheet applies, the nav is a flex row, the submit button fills its form, the host has a
    background), and neither control shows: label[data-femto-switch] and fieldset[data-swatches] keep
    their hidden attribute and are not rendered, and the fieldset holds no swatch."""
    s = look(page)
    page.expect("the block is in femto's styles", styled(s), **s)
    c = page.js("""const l = document.querySelector('main > section.proof label[data-femto-switch]'),
        f = document.querySelector('main > section.proof fieldset[data-swatches]');
      return {label: !!l && l.hidden && l.getClientRects().length === 0, swatches: !!f && f.hidden && f.getClientRects().length === 0,
              radios: f ? f.querySelectorAll('input').length : null};""")
    page.eq("the switch and the swatches are hidden, with no swatch", c, {"label": True, "swatches": True, "radios": 0})


def is_light(rgb):
    """True for a light color, from a computed rgb() or rgba() value."""
    r, g, b = (float(x) for x in rgb[rgb.index("(") + 1:].rstrip(")").split(",")[:3])
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 > 0.5


@check("femto-block-scheme", "/")
def femto_block_scheme(page):
    """The block follows the page's color scheme, femto on and off (landing.css: the frame passes
    the page's color-scheme down, and ::part() gives it to the inner host). On a light OS with
    nothing stored the inner host's color-scheme is light, its background is the page's (femto's
    light background) and its text dark; after a click on the header toggle, dark, the page's dark
    background and light text. Then with femto off in the block it stays dark, with the browser's
    own light text and no background; a second toggle click makes it light, with dark text; femto on
    again, it has the page's light background."""
    s = look(page)
    page.expect("light: the block's scheme, the page's background, dark text", s["scheme"] == "light" and s["background"] == s["page"]
                and is_light(s["background"]) and not is_light(s["color"]), **s)
    page.click(TOGGLE)
    page.wait("dark: the block follows the toggle", f"(() => {{ {LOOK} }})().scheme === 'dark'", 1.5)
    page.wait("dark: the page's background in the block", f"(() => {{ const s = (() => {{ {LOOK} }})(); return s.background === s.page; }})()", 1.5)
    s = look(page)
    page.expect("dark: a dark background and light text", not is_light(s["background"]) and is_light(s["color"]), **s)
    page.click(SWITCH)
    page.wait("femto off", f"(() => {{ {LOOK} }})().femto === false", 1)
    s = look(page)
    page.expect("off in dark: the dark scheme, the browser's light text, no background", s["scheme"] == "dark" and is_light(s["color"])
                and s["background"] == TRANSPARENT, **s)
    page.click(TOGGLE)
    page.wait("off in light: the block follows the toggle", f"(() => {{ {LOOK} }})().scheme === 'light'", 1.5)
    s = look(page)
    page.expect("off in light: dark text", not is_light(s["color"]), **s)
    page.click(SWITCH)
    page.wait("on in light: the page's light background", f"(() => {{ const s = (() => {{ {LOOK} }})(); return s.femto && s.background === s.page; }})()", 1.5)


@check("femto-block-stored-dark", "/", storage={"femtoColorScheme": '"dark"'})
def femto_block_stored_dark(page):
    """A stored dark choice reaches the block on a light OS: the inner host's color-scheme is dark,
    with the page's dark background and light text, so the block never shows the OS's light scheme
    while the page is dark."""
    s = look(page)
    page.expect("stored dark: the block is dark, with the page's background", s["scheme"] == "dark" and s["background"] == s["page"]
                and not is_light(s["background"]) and is_light(s["color"]), **s)


# --- The theme swatches ---------------------------------------------------------------------------
# femto's 20 theme colors as the swatches order them, the docs' Theme picker's order: around the
# color wheel from red to the greys.
THEMES = ["red", "orange", "pumpkin", "amber", "yellow", "lime", "green", "jade", "cyan", "azure",
          "blue", "indigo", "violet", "purple", "fuchsia", "pink", "sand", "grey", "zinc", "slate"]
FEMTO = "/vendor/femto/dist/femto.min.css"

# Each color's --femto-primary-background, from its file in the vendored femto, as rgb(); the swatches,
# the theme links on the page and in the block, and the color of a button on each.
RGB = "const rgb = (hex) => `rgb(${[1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;"
PRIMARY = RGB + """
const out = {};
for (const c of arguments[0]) {
  const css = await (await fetch(`/vendor/femto/css/themes/${c}.css`)).text();
  out[c] = rgb(css.match(/--femto-primary-background:\\s*(#[0-9a-f]{6})/i)[1]);
}
done(out);
"""
THEMED = BLOCK + """
const themes = (r) => [...r.querySelectorAll('link')].filter(l => l.getAttribute('href').startsWith('/vendor/femto/css/themes/'))
  .map(l => [l.getAttribute('href').replace(/^.*\\/|\\.css$/g, ''), l.previousElementSibling?.getAttribute('href') ?? null]);
return {page: themes(document.head), block: themes(root),
        pageButton: getComputedStyle(document.querySelector('main > section.hero a[role=button]:not(.contrast)')).backgroundColor,
        blockButton: getComputedStyle(root.querySelector('button[type=submit]')).backgroundColor,
        checked: document.querySelector('fieldset[data-swatches] input:checked')?.value ?? null};
"""
RADIO = "main > section.proof fieldset[data-swatches] input[value={}]"


def themed(page):
    return page.js(THEMED)


def expect_theme(page, label, color, primary):
    """The page and the block in `color`: its theme link right after femto's in each (none for
    azure), its swatch checked, and the buttons on both in its color, within 2 s (femto's buttons
    transition their color)."""
    want = [] if color == "azure" else [[color, FEMTO]]
    page.wait(f"{label}: the buttons on the page and in the block turn {color}",
              f"(() => {{ const s = (() => {{ {THEMED} }})(); return s.pageButton === arguments[0] && s.blockButton === arguments[0]; }})()",
              2, args=(primary[color],))
    s = themed(page)
    page.eq(f"{label}: {color}'s theme link after femto's, on the page and in the block, and its swatch checked",
            [s["page"], s["block"], s["checked"]], [want, want, color])


@check("theme-swatches", "/")
def theme_swatches(page):
    """The homepage's theme swatches, fieldset[data-swatches] in the femto block's toolbar with the
    legend "Theme color", are shown once demo.js runs: 20 radios, one per femto theme color, in the
    docs' Theme picker's order (THEMES, read from /docs too), all of one name, each named by its color ("Azure") and drawn in that color's
    --femto-primary-background as femto's theme file gives it (its border color); azure, the page's
    color, is checked, and no theme file is linked. A click on Jade recolors the page and the block in
    place: jade.css is linked right after femto's stylesheet on the page and in the block's shadow
    root, alone, and the hero's Get started button and the block's Sign up button take jade's
    color. A click on Pumpkin swaps jade for pumpkin the same way. A click on Azure removes the theme
    links, and both buttons are azure again. The URL and history are kept, and nothing is stored."""
    primary = page.ajs(PRIMARY, THEMES)
    s = page.js("""const f = document.querySelector('main > section.proof fieldset[data-swatches]');
      const r = f ? [...f.querySelectorAll(':scope > input')] : [];
      return {shown: !!f && !f.hidden && f.getClientRects().length > 0, legend: f?.querySelector(':scope > legend')?.textContent.trim(),
              values: r.map(i => i.value), types: [...new Set(r.map(i => i.type))], names: [...new Set(r.map(i => i.name))],
              checked: r.filter(i => i.checked).map(i => i.value), colors: r.map(i => getComputedStyle(i).borderTopColor)};""")
    page.eq("the swatches are shown, with their legend", [s["shown"], s["legend"]], [True, "Theme color"])
    page.eq("20 swatches, in THEMES' order", s["values"], THEMES)
    page.eq("the docs' Theme picker's order", s["values"], page.ajs(PICKER_ORDER))
    page.expect("radios of one name", s["types"] == ["radio"] and len(s["names"]) == 1 and s["names"][0], **s)
    page.eq("azure is checked", s["checked"], ["azure"])
    page.eq("each swatch in its color's --femto-primary-background", dict(zip(THEMES, s["colors"])), primary)
    for c in THEMES:
        expect_name(page, f"the {c} swatch is named {c.capitalize()}", page.el(RADIO.format(c)), c.capitalize())
    url = page.url()
    expect_theme(page, "on load", "azure", primary)
    for color in ("jade", "pumpkin", "azure"):
        page.click(RADIO.format(color))
        expect_theme(page, f"{color.capitalize()} clicked", color, primary)
    page.url_kept("the URL and history are kept", url)
    page.eq("nothing is stored", page.js("return localStorage.length"), 0)


@check("theme-swatches-keyboard", "/")
def theme_swatches_keyboard(page):
    """The swatches are one tab stop after the femto switch: Tab from the switch focuses the checked
    swatch, azure, which in forced colors (Chrome), which drop femto's box-shadow ring, shows an
    outline. Right arrow moves focus to blue and checks it, which recolors the page and the block
    blue (blue.css after femto's stylesheet in each, the buttons blue); Left arrow returns to azure,
    with no theme link."""
    primary = page.ajs(PRIMARY, ["azure", "blue"])
    page.focus(SWITCH)
    page.tab()
    page.eq("Tab from the switch reaches the checked swatch", page.js("return document.activeElement?.value ?? null"), "azure")
    expect_forced_focus(page, "the checked swatch")
    for key, color in (("ARROW_RIGHT", "blue"), ("ARROW_LEFT", "azure")):
        page.key(key)
        page.eq(f"{key}: focus on {color}", page.js("return document.activeElement?.value ?? null"), color)
        expect_theme(page, key, color, primary)
