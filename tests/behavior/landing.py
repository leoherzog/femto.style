"""Landing: the homepage's typing demo (01 §2, homepage/Demo: TypeIt driving the form; demo.js in
the static site, a hand-written loop). The parity runs mask the demo's contents (PLAN.md, Masked),
so these checks are what holds it to the oracle. /demo, the capture page that ran the same demo, is not built
from Phase 4 (PLAN.md Open questions 5), so its check went with it. Phase 4 added the demo's pause
button and its paused start under prefers-reduced-motion (WCAG 2.2.2), which the oracle lacks:
demo-pause and demo-reduced-motion hold them on the one page only."""
import json
import time

from behavior import check

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
const art = document.querySelector(".demo > article.component");
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
    """Consecutive phases, a leading "initial" (the oracle's input has no type for its first 1.75 s)
    dropped."""
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
    if p == "date":
        page.expect(f"{label}: a date value, enabled", bool(f["input"]["value"]) and len(f["input"]["value"]) == 10
                    and f["input"]["value"][4] == "-" and not f["input"]["disabled"], input=f["input"])
    if p == "date-next":
        page.eq(f"{label}: the Next button", f["button"]["text"], "Next")
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
    """The homepage demo (`.demo > article.component`: a form and a code sample in `footer code`)
    runs its whole sequence and starts over, the form following the code. Watched for up to 100 s,
    the form's phases are exactly: email, invalid, invalid-helper, group-subscribe, search,
    search-busy, date, date-next, select, checkbox, checkbox-checked, switch-on, switch-off,
    range-25, range-50, then email and invalid again (the loop). During each phase one snapshot of
    the code shows that phase's markup (e.g. aria-invalid="true", <fieldset role="group">,
    aria-busy="true", type="date", <select>, role="switch", value="50"; tests/behavior/landing.py,
    MARKERS), the form's fields carry the phase's values (the email typed letter by letter to
    invalid@example, the helper text, Subscribe, Search..., Next, Select..., Publish on my profile,
    Brightness), and the code is typed: at least 50 one-character insertions."""
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
    lines = page.js("return document.querySelector('.demo > article.component footer code').innerText.split('\\n')")
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
        st = page.js("""const f = document.querySelector('.demo > article.component form'), i = f.querySelector('input');
          return {input: !!i && !['checkbox', 'range', 'date'].includes(i.getAttribute('type')), value: i ? i.value : null,
                  role: f.getAttribute('role'), invalid: i ? i.getAttribute('aria-invalid') : null}""")
        page.expect(f"started over at {w}: the first phase's email input, empty", st["input"] and st["value"] == ""
                    and st["role"] is None and st["invalid"] is None, **st)


TOGGLE = "body > header nav ul.icons button:has(> span[role=img][aria-label$='dark mode'])"   # a button from Phase 4
COMPARISON = "[...document.querySelectorAll('main > section.comparison div.code[data-theme]')].map(d => d.getAttribute('data-theme'))"


@check("comparison-toggle", "/")
def comparison_toggle(page):
    """The homepage comparison's code samples (`section.comparison div.code`, Comparison.jsx:
    dataTheme={pageTheme}) take the page's color scheme: data-theme="light" on a light OS with
    nothing stored, "dark" after a click on the header theme toggle, "light" after the next."""
    s = page.js(f"return {COMPARISON}")
    page.expect("the comparison has code samples", len(s) >= 1, samples=s)
    page.wait("the samples read light on load", f"{COMPARISON}.every(v => v === 'light')", 1, got=s)
    for want in ("dark", "light"):
        page.click(TOGGLE)
        page.wait(f"the samples follow the toggle to {want}", f"{COMPARISON}.every(v => v === '{want}')", 1.5,
                  got=page.js(f"return {COMPARISON}"))


# Records every change of the demo's state from now on (its code text, the form's markup and its
# fields' values), with times from the start, through a MutationObserver and a 100 ms poll (a
# field's value property changes no markup).
DEMO_WATCH = r"""
const art = document.querySelector(".demo > article.component");
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


@check("demo-offscreen", "/", oracle_bug={
    "fails": "no change for 7 s while the demo is above the viewport",
    "reason": "the oracle's TypeIt instance (homepage/Demo, waitUntilVisible false by default) types, pauses and "
              "changes the form whether or not the demo is on screen; PLAN.md Conversion rules: intervals run "
              "only while their element is on screen"})
def demo_offscreen(page):
    """The homepage demo (`.demo > article.component`) runs only while it is on screen: it changes
    within 4 s on screen at the top; scrolled until it is above the viewport, and after 2 s for the
    form changes already scheduled to settle, its code and form do not change for 7 s; scrolled back
    into view, it changes again within 5 s."""
    page.eq("the demo starts on screen", page.js(DEMO_WATCH), "on")
    page.wait("the demo changes on screen", "window.__bhDemoOff.changes.length > 0", 4)
    y = page.js("const r = document.querySelector('.demo > article.component').getBoundingClientRect(); return Math.ceil(r.bottom + scrollY + 50)")
    page.scroll_to(y)
    page.sleep(2)
    page.eq("scrolled, the demo is above the viewport", page.js(DEMO_WATCH), "above")
    page.sleep(7)
    page.eq("no change for 7 s while the demo is above the viewport", page.js("return window.__bhDemoOff.changes"), [])
    page.scroll_to(0)
    page.eq("back at the top, the demo is on screen", page.js(DEMO_WATCH), "on")
    page.wait("back on screen, the demo changes again within 5 s", "window.__bhDemoOff.changes.length > 0", 5)


# The typing demo's pause button (demo.js, from Phase 4: WCAG 2.2.2), and the demo's state around it:
# the button's own state, and the play state of every animation in the code sample (the cursor's
# blink), which no mutation shows.
PAUSE = ".demo > article.component button[data-demo-pause]"
PAUSE_WHY = ("the pause button and the reduced-motion start are new from Phase 4 (WCAG 2.2.2, Pause, Stop, Hide: "
             "the demo moves for more than 5 s); the oracle's TypeIt demo has neither")
PAUSE_STATE = """
const b = document.querySelector(arguments[0]);
const code = document.querySelector(".demo > article.component footer code");
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


@check("demo-pause", "/", layouts=("one-page",), layout_reason=PAUSE_WHY)
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


@check("demo-reduced-motion", "/", motion="reduce", layouts=("one-page",), layout_reason=PAUSE_WHY)
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
    first = page.js("""const art = document.querySelector('.demo > article.component'), f = art.querySelector('form');
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
