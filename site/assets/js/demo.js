// demo.js: the landing pages' widgets, on / and /demo (docs/research/01 §2). Each does nothing when
// its markup is absent.
//
// 1. The comparison's code samples on / (homepage/Comparison.jsx) take the page's color scheme:
//    data-theme on `section.comparison div.code` is pageTheme(), on load and after every change.
//
// 2. The typing demo (homepage/Demo/*). The oracle drove it with TypeIt, which is GPL-3.0 or
//    commercially licensed (PLAN.md Risks), so this is a small hand-written loop instead. It binds to
//    the oracle's own markup, `.demo > article.component` with its form and `footer.code pre code`.
//    - The code sample is a list of characters, each with the token class it is typed in, plus line
//      breaks, and a cursor among them. The steps type, move the cursor, delete and pause exactly as
//      the oracle's LargeWidthCode.jsx and SmallWidthCode.jsx queue them (counts are in characters, a
//      line break counts as one), then run the step's form change.
//    - The form follows the code: one state object with DemoContext.jsx's fields, rendered as Form.jsx
//      renders it (one render per change, as React batches them).
//    - The large layout (attributes on one line) is used from an innerWidth of 1280 px, the small one
//      below; crossing 1280 px starts the demo over in the other layout, as the oracle's remount did.
//    - The whole sequence loops forever. It waits while the demo is off screen (PLAN.md, JavaScript:
//      intervals run only while their element is on screen).
//    Left out on purpose: the maximize controls and their Escape handler, dead code in the oracle
//    (01 §2); they are not rebuilt.

import { onThemeChange, pageTheme } from "./site.js";

// --- 1. The comparison's code samples ----------------------------------------------------------
const samples = document.querySelectorAll("main > section.comparison div.code[data-theme]");
if (samples.length) {
  const follow = (theme) => {
    for (const sample of samples) if (sample.getAttribute("data-theme") !== theme) sample.setAttribute("data-theme", theme);
  };
  follow(pageTheme());
  onThemeChange(follow);
}

// --- 2. The typing demo ------------------------------------------------------------------------
const article = document.querySelector(".demo > article.component");
const form = article?.querySelector("form");
const code = article?.querySelector("footer.code pre code");

// --- Timing (DemoContext.jsx: speed 7, so pause 70 ms and a phase 3.5 s) -------------------------
const PAUSE = 70;
const SHOW = 3500;
const FILL = 7;    // ms per character as the email field fills in (the input's own interval)
const TYPE = 17;   // ms per typed code character: TypeIt types at most one per frame
const LARGE = 1280;

// --- The code sample ---------------------------------------------------------------------------
// The strings are the oracle's, written with its helpers. A step's string is split into characters
// with the class of the span they are in: these strings hold only <span class="...">text</span>,
// <br />, &lt;, &gt; and plain text.
const tag = (v) => `<span class="token tag">${v}</span>`;
const attr = (v) => `<span class="token tag attr-name">${v}</span>`;
const value = (v) => `<span class="token tag attr-value">${v}</span>`;
const PIECE = /<span class="([^"]+)">([^<]*)<\/span>|<br \/>|&lt;|&gt;|[^<&]/g;

function chars(html) {
  const out = [];
  for (const [piece, cls, text] of html.matchAll(PIECE)) {
    if (cls) for (const ch of text) out.push({ ch, cls });
    else if (piece === "<br />") out.push({ br: true });
    else out.push({ ch: piece === "&lt;" ? "<" : piece === "&gt;" ? ">" : piece });
  }
  return out;
}

// A queue of steps, written like the oracle's TypeIt chain.
function queue() {
  const steps = [];
  const q = {
    steps,
    type: (html, options) => (steps.push({ op: "type", chars: chars(html), ...options }), q),
    move: (n, options) => (steps.push({ op: "move", n, ...options }), q),
    delete: (n, options) => (steps.push({ op: "delete", n, ...options }), q),
    pause: (ms) => (steps.push({ op: "pause", delay: ms }), q),
    exec: (fn) => (steps.push({ op: "exec", fn }), q),
  };
  return q;
}
const instant = { instant: true };
const moveOpts = { instant: true, delay: PAUSE };
const delOpts = { instant: true, delay: PAUSE };
const moveInstant = { instant: true, delay: 0 };
const delInstant = { instant: true, delay: 0 };

// --- The form ----------------------------------------------------------------------------------
// DemoContext.jsx's states and their initial values (resetForm).
const INITIAL = {
  formRole: null, formGroupIsFocused: false,
  displayInput: true, inputPlaceholder: "Enter your email", inputInvalid: null, inputClass: "", inputType: null,
  inputValue: "", displayedInputValue: "", inputIsDisabled: false, inputIsFocused: false,
  inputHelper: null, inputHelperClass: "",
  displaySelect: false,
  displayCheckbox: false, checkboxIsChecked: false, checkboxClass: "", checkboxRole: null, checkboxIsFocused: false,
  displayRange: false, rangeValue: 0, rangeIsFocused: false, rangeClass: "",
  displayButton: false, buttonType: null, buttonLabel: null, buttonClass: "", buttonIsBusy: false, buttonIsFocused: false,
};
let state = { ...INITIAL };

function el(name, attrs, ...children) {
  const element = document.createElement(name);
  for (const [k, v] of Object.entries(attrs)) element.setAttribute(k, v);
  element.append(...children);
  return element;
}
function setAttr(element, name, v) {
  if (v === null || v === undefined || v === false) element.removeAttribute(name);
  else if (element.getAttribute(name) !== String(v)) element.setAttribute(name, v);
}

// Form.jsx's controls, in its order. The input is the page's own; the others are made once and put
// in or taken out as their display state changes, as React mounts and unmounts them.
const parts = form && {
  input: form.querySelector("input"),
  helper: el("small", {}),
  select: el("select", { name: "select-demo", tabindex: "-1", required: "" },
    el("option", { disabled: "", value: "", selected: "" }, "Select...")),
  checkboxLabel: el("label", { class: "" }),
  checkbox: el("input", { name: "checkbox-demo", tabindex: "-1", type: "checkbox", class: "" }),
  rangeLabel: el("label", { class: "" }, "Brightness"),
  range: el("input", { name: "range-demo", tabindex: "-1", type: "range", value: "0", class: "" }),
  button: el("button", { tabindex: "-1", class: "", "aria-busy": "false" }),
};
if (parts) {
  parts.checkboxLabel.append(parts.checkbox, "Publish on my profile");
  parts.rangeLabel.append(parts.range);
}

function renderForm() {
  const s = state, { input, helper, select, checkboxLabel, checkbox, rangeLabel, range, button } = parts;
  setAttr(form, "role", s.formRole || null);
  setAttr(form, "class", s.formGroupIsFocused ? "is-focused" : "");
  setAttr(input, "type", s.inputType);
  setAttr(input, "placeholder", s.inputPlaceholder);
  setAttr(input, "class", `${s.inputClass}${s.inputIsFocused ? " is-focused" : ""}`);
  input.disabled = s.inputIsDisabled;
  input.value = s.displayedInputValue;
  setAttr(input, "value", s.displayedInputValue);
  setAttr(input, "aria-invalid", s.inputInvalid === null ? null : String(s.inputInvalid));
  setAttr(helper, "class", s.inputHelperClass);
  if (helper.textContent !== (s.inputHelper ?? "")) helper.textContent = s.inputHelper ?? "";
  setAttr(checkboxLabel, "class", s.checkboxClass);
  setAttr(checkbox, "role", s.checkboxRole);
  setAttr(checkbox, "class", s.checkboxIsFocused ? "is-focused" : "");
  checkbox.checked = s.checkboxIsChecked;
  setAttr(rangeLabel, "class", s.rangeClass);
  setAttr(range, "class", s.rangeIsFocused ? "is-focused" : "");
  range.value = String(s.rangeValue);
  setAttr(range, "value", s.rangeValue);
  setAttr(button, "type", s.buttonType);
  setAttr(button, "class", `${s.buttonClass}${s.buttonIsFocused ? " is-focused" : ""}`);
  setAttr(button, "aria-busy", String(s.buttonIsBusy));
  if (button.textContent !== (s.buttonLabel ?? "")) button.textContent = s.buttonLabel ?? "";

  const shown = [s.displayInput && input, s.inputHelper && helper, s.displaySelect && select,
    s.displayCheckbox && checkboxLabel, s.displayRange && rangeLabel, s.displayButton && button].filter(Boolean);
  for (const child of [...form.children]) if (!shown.includes(child)) child.remove();
  shown.forEach((child, i) => {
    if (form.children[i] !== child) form.insertBefore(child, form.children[i] ?? null);
  });
}

// --- Running -----------------------------------------------------------------------------------
let run = 0;          // the current run; a restart makes every older step and timer stop
let text = [];        // the code's characters
let at = 0;           // the cursor: the number of characters before it
let onScreen = true;
const resumes = [];

// ms later, and then only once the demo is on screen.
function wait(ms) {
  return new Promise((done) => setTimeout(done, ms))
    .then(() => onScreen || new Promise((done) => resumes.push(done)));
}
// A form change later in this run (the oracle's setTimeout inside a step).
function later(ms, fn) {
  const mine = run;
  setTimeout(() => mine === run && fn(), ms);
}

// Change the form state and render it once. inputValue fills the email field in letter by letter,
// as DemoContext.jsx's effect does; a date or an empty value shows at once.
function set(changes) {
  const filled = "inputValue" in changes && changes.inputValue !== state.inputValue;
  state = { ...state, ...changes };
  if (filled) {
    const v = state.inputValue;
    if (!v || /^\d{4}-\d{2}-\d{2}$/.test(v)) state.displayedInputValue = v;
    else {
      const mine = run;
      let i = 0;
      const timer = setInterval(() => {
        if (mine !== run) return clearInterval(timer);
        set({ displayedInputValue: state.displayedInputValue + v[i] });
        i++;
        if (i === v.length) {
          clearInterval(timer);
          later(SHOW / 4, () => set({ inputIsFocused: false }));
        }
      }, FILL);
    }
  }
  renderForm();
}

// The cursor: TypeIt's zero-width "|" between characters, solid while the code changes and
// blinking once it rests.
const caret = el("span", { class: "ti-cursor" }, "|");
caret.style.cssText = "display: inline-block; width: 0; transform: translateX(-0.25em)";
let blink = null;

function renderCode() {
  const nodes = [];
  let chunk = "", cls;
  const flush = () => {
    if (chunk) nodes.push(cls ? el("span", { class: cls }, chunk) : document.createTextNode(chunk));
    chunk = "";
  };
  text.forEach((c, i) => {
    if (i === at) { flush(); nodes.push(caret); }
    if (c.br) { flush(); nodes.push(document.createElement("br")); return; }
    if (c.cls !== cls) { flush(); cls = c.cls; }
    chunk += c.ch;
  });
  flush();
  if (at === text.length) nodes.push(caret);
  code.replaceChildren(...nodes);
  if (blink) blink.currentTime = 0;
  else blink = caret.animate([{ opacity: 1, easing: "step-end" }, { opacity: 0, easing: "step-end" }, { opacity: 1 }],
    { duration: 1000, iterations: Infinity });
}

async function play(steps, mine) {
  for (const step of steps) {
    if (step.op === "exec") step.fn();
    else if (step.op === "move") at = Math.max(0, Math.min(text.length, at + step.n));
    else if (step.op === "delete") {
      const n = Math.min(step.n, at);
      text.splice(at - n, n);
      at -= n;
    } else if (step.op === "type" && step.instant) {
      text.splice(at, 0, ...step.chars);
      at += step.chars.length;
    } else if (step.op === "type") {
      for (const c of step.chars) {
        await wait(TYPE);
        if (mine !== run) return;
        text.splice(at, 0, c);
        at++;
        renderCode();
      }
    }
    if (step.op === "move" || step.op === "delete" || (step.op === "type" && step.instant)) renderCode();
    // A step with no delay (the first lines, typed at once) runs on in the same task, so the first
    // paint shows the whole sample.
    if (step.delay === undefined) continue;
    await wait(step.delay);
    if (mine !== run) return;
  }
}

async function start(steps) {
  const mine = ++run;
  state = { ...INITIAL };
  renderForm();
  while (mine === run) {
    text = [];
    at = 0;
    await play(steps, mine);
  }
}

// --- The steps (LargeWidthCode.jsx and SmallWidthCode.jsx) -------------------------------------
// The form change after each phase, shared by both layouts.
const phase = {
  email: () => {
    set({ inputType: "email" });
    later(PAUSE, () => {
      set({ inputIsFocused: true });
      later(PAUSE * 2, () => set({ inputValue: "invalid@example" }));
    });
  },
  invalid: () => set({ inputInvalid: true, inputClass: "" }),
  helper: () => set({ inputHelper: "Please enter a valid email!", inputHelperClass: "fade-in" }),
  subscribe: () => set({ formRole: "group", inputInvalid: null, inputValue: "", inputHelper: null, displayButton: true,
    buttonType: "submit", buttonLabel: "Subscribe", buttonClass: "fade-in" }),
  search: () => set({ formRole: "search", inputType: "search", inputPlaceholder: "Search", buttonLabel: "Search" }),
  busy: () => set({ buttonIsFocused: true, formGroupIsFocused: true, buttonIsBusy: true, inputIsDisabled: true,
    buttonLabel: "Search..." }),
  date: () => {
    const day = new Date().toISOString().slice(0, 10); // todayForInputDate (yyyy-MM-dd)
    set({ formGroupIsFocused: false, formRole: null, displayButton: false, buttonIsFocused: false, buttonClass: "",
      buttonIsBusy: false, inputType: "date", inputClass: "fade-in", displayedInputValue: day, inputValue: day,
      inputPlaceholder: null, inputIsDisabled: false });
  },
  next: () => set({ inputClass: "", displayButton: true, buttonLabel: "Next", buttonClass: "fade-in" }),
  select: () => set({ displayInput: false, displaySelect: true }),
  checkbox: () => set({ displaySelect: false, displayButton: false, displayCheckbox: true, checkboxClass: "fade-in" }),
  check: (checked) => () => {
    set({ checkboxIsFocused: true });
    later(PAUSE, () => {
      set({ checkboxIsChecked: checked });
      later(PAUSE * 2, () => set({ checkboxIsFocused: false }));
    });
  },
  switch: () => set({ checkboxRole: "switch" }),
  range: () => set({ rangeClass: "fade-in", displayCheckbox: false, displayRange: true, rangeValue: 25 }),
  range50: () => {
    set({ rangeClass: "", rangeIsFocused: true });
    later(PAUSE, () => {
      set({ rangeValue: 50 });
      later(PAUSE * 2, () => set({ rangeIsFocused: false }));
    });
  },
  loop: () => set({ displayRange: false, displayInput: true, inputClass: "fade-in", inputType: "email", inputValue: "",
    displayedInputValue: "", inputPlaceholder: "Enter your email" }),
};

const largeCode = [
  `&lt;${tag("form")}&gt;`,
  `<br />  &lt;${tag("input")} ${attr("type")}=${value('"email"')} ${attr("placeholder")}=${value('"Enter your email"')} /&gt;`,
  `<br />&lt;/${tag("form")}&gt;`,
];
const large = queue()
  // Email input
  .type(largeCode[0], instant).type(largeCode[1], instant).type(largeCode[2], instant)
  .move(-11, instant)
  .pause(SHOW / 2)
  .exec(phase.email)
  // Invalid email input
  .pause(SHOW / 2)
  .type(` ${attr("aria-invalid")}=${value('"true"')}`)
  .exec(phase.invalid)
  // Invalid email input helper
  .pause(SHOW)
  .move(3, moveOpts)
  .type("  <br />  ", moveOpts)
  .type(`&lt;${tag("small")}&gt;Please enter a valid email!&lt;/${tag("small")}&gt;`)
  .exec(phase.helper)
  // Email input with submit button
  .pause(SHOW)
  .delete(47, delOpts)
  .move(-3, moveOpts)
  .delete(20, delOpts)
  .move(-53, moveOpts)
  .type(`<br />  &lt;${tag("fieldset")} ${attr("role")}=${value('"group"')}&gt;`)
  .move(56, moveOpts)
  .type(`<br />  &lt;/${tag("fieldset")}&gt;`)
  .move(-67, moveInstant)
  .type("  ", moveInstant)
  .move(53, moveInstant)
  .type(`<br />    &lt;${tag("button")} ${attr("type")}=${value('"submit"')}&gt;&lt;/${tag("button")}&gt;`)
  .move(-9, moveOpts)
  .type("Subscribe")
  .exec(phase.subscribe)
  // Search input with button
  .pause(SHOW)
  .move(-94, moveOpts)
  .delete(26, delOpts)
  .move(117, moveOpts)
  .delete(14, delOpts)
  .move(-40, moveInstant)
  .delete(2, delInstant)
  .move(-56, moveInstant)
  .delete(2, delInstant)
  .move(-4, moveOpts)
  .type(` ${attr("role")}=${value('"search"')}`)
  .move(23, moveOpts)
  .delete(7, delOpts)
  .type(value('"search"'))
  .move(31, moveOpts)
  .delete(18, delOpts)
  .type(value('"Search"'))
  .move(37, moveOpts)
  .delete(8, delOpts)
  .type("earch")
  .exec(phase.search)
  // Search input and button submitted
  .pause(SHOW)
  .move(-7, moveOpts)
  .type(` ${attr("aria-busy")}=${value('"true"')}`)
  .move(7, moveOpts)
  .type("...")
  .exec(phase.busy)
  // Date input
  .pause(SHOW)
  .move(9, moveOpts)
  .delete(60, delOpts)
  .move(-3, moveOpts)
  .delete(29, delOpts)
  .type(value('"date"'))
  .move(-22, moveOpts)
  .delete(14, delOpts)
  .exec(phase.date)
  // Date input with Next button
  .pause(SHOW)
  .move(25, moveOpts)
  .type(`<br />  &lt;${tag("button")}&gt;Next&lt;/${tag("button")}&gt;`)
  .exec(phase.next)
  // Select
  .pause(SHOW)
  .move(-24, moveOpts)
  .delete(21, delOpts)
  .type(`&lt;${tag("select")}&gt;&lt;/${tag("select")}&gt;`)
  .move(-9, moveOpts)
  .type("<br />    <br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`&lt;${tag("option")}&gt;Select...&lt;/${tag("option")}&gt;`)
  .exec(phase.select)
  // Checkbox
  .pause(SHOW)
  .move(12, moveOpts)
  .delete(50, delOpts)
  .type(`${tag("label")}&gt;&lt;/${tag("label")}&gt;`)
  .move(-8, moveOpts)
  .type("<br />    <br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`&lt;${tag("input")} ${attr("type")}=${value('"checkbox"')} /&gt;`)
  .type("<br />    ", moveOpts)
  .type("Publish on my profile")
  .move(35, moveOpts)
  .delete(24, delOpts)
  .exec(phase.checkbox)
  // Checkbox checked
  .pause(SHOW)
  .move(-40, moveOpts)
  .type(` ${attr("checked")}`)
  .exec(phase.check(true))
  // Switch checked
  .pause(SHOW)
  .move(-8, moveOpts)
  .type(` ${attr("role")}=${value('"switch"')}`)
  .exec(phase.switch)
  // Switch not checked
  .pause(SHOW)
  .move(8, moveOpts)
  .delete(8, delOpts)
  .exec(phase.check(false))
  // Range
  .pause(SHOW)
  .move(29, moveOpts)
  .delete(26, delOpts)
  .move(-44, moveOpts)
  .type("    <br />    ", moveOpts)
  .type("Brightness")
  .move(41, moveOpts)
  .delete(24, delOpts)
  .type(value('"range"'))
  .type(` ${attr("value")}=${value('"25"')}`)
  .exec(phase.range)
  // Range to 50
  .pause(SHOW / 4)
  .delete(4, delOpts)
  .type(value('"50"'))
  .exec(phase.range50)
  // Loop to input email
  .pause(SHOW)
  .move(15, moveOpts)
  .delete(79, delOpts)
  .move(-1, moveOpts)
  .move(1, moveOpts)
  .type("<br />")
  .move(-1, moveOpts)
  .type(largeCode[1])
  .exec(phase.loop);

const smallCode = [
  `&lt;${tag("form")}&gt;`,
  `<br />  &lt;${tag("input")}`,
  `<br />    ${attr("type")}=${value('"email"')}`,
  `<br />    ${attr("placeholder")}=${value('"Enter your email"')}`,
  "<br />  /&gt;",
  `<br />&lt;/${tag("form")}&gt;`,
];
const small = queue()
  // Email input
  .type(smallCode[0], instant).type(smallCode[1], instant).type(smallCode[2], instant)
  .type(smallCode[3], instant).type(smallCode[4], instant).type(smallCode[5], instant)
  .move(-13, instant)
  .pause(SHOW / 2)
  .exec(phase.email)
  // Invalid email input
  .pause(SHOW / 2)
  .type("<br />    ", moveOpts)
  .type(`${attr("aria-invalid")}=${value('"true"')}`)
  .exec(phase.invalid)
  // Invalid email input helper
  .pause(SHOW)
  .move(6, moveOpts)
  .type("  <br />", moveOpts)
  .move(-1, moveOpts)
  .type(`&lt;${tag("small")}&gt;&lt;/${tag("small")}&gt;`)
  .move(-8, moveOpts)
  .type("<br />    <br />  ", moveOpts)
  .move(-3, moveOpts)
  .type("Please enter a valid email!")
  .exec(phase.helper)
  // Email input with submit button
  .pause(SHOW)
  .move(11, moveOpts)
  .delete(53, delOpts)
  .move(-5, moveOpts)
  .delete(24, delOpts)
  .move(-58, moveOpts)
  .type("<br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`&lt;${tag("fieldset")} ${attr("role")}=${value('"group"')}&gt;`)
  .move(66, moveOpts)
  .type("<br />  ", moveOpts)
  .type(`&lt;/${tag("fieldset")}&gt;`)
  .move(-16, moveInstant)
  .type("  ", moveInstant)
  .move(-36, moveInstant)
  .type("  ", moveInstant)
  .move(-19, moveInstant)
  .type("  ", moveInstant)
  .move(-12, moveInstant)
  .type("  ", moveInstant)
  .move(69, moveInstant)
  .type("<br />    ", moveOpts)
  .type(`&lt;${tag("button")} ${attr("type")}=${value('"submit"')}&gt;&lt;/${tag("button")}&gt;`)
  .move(-9, moveOpts)
  .type("<br />      <br />    ", moveOpts)
  .move(-5, moveOpts)
  .type("Subscribe")
  .exec(phase.subscribe)
  // Search input with button
  .pause(SHOW)
  .move(-117, moveOpts)
  .delete(26, delOpts)
  .move(145, moveOpts)
  .delete(14, delOpts)
  .move(-10, moveInstant)
  .delete(2, delInstant)
  .move(-12, moveInstant)
  .delete(2, delInstant)
  .move(-26, moveInstant)
  .delete(2, delInstant)
  .move(-5, moveInstant)
  .delete(2, delInstant)
  .move(-34, moveInstant)
  .delete(2, delInstant)
  .move(-17, moveInstant)
  .delete(2, delInstant)
  .move(-10, moveInstant)
  .delete(2, delInstant)
  .move(-4, moveOpts)
  .type(` ${attr("role")}=${value('"search"')}`)
  .move(27, moveOpts)
  .delete(7, delOpts)
  .type(value('"search"'))
  .move(35, moveOpts)
  .delete(18, delOpts)
  .type(value('"Search"'))
  .move(44, moveOpts)
  .delete(8, delOpts)
  .type("earch")
  .exec(phase.search)
  // Search input and button submitted
  .pause(SHOW)
  .move(-26, moveOpts)
  .type("<br />   ", moveOpts)
  .move(14, moveOpts)
  .type("<br />    <br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`${attr("aria-busy")}=${value('"true"')}`)
  .move(15, moveOpts)
  .type("...")
  .exec(phase.busy)
  // Date input
  .pause(SHOW)
  .move(12, moveOpts)
  .delete(79, delOpts)
  .move(-2, moveOpts)
  .delete(46, delOpts)
  .type(` ${attr("type")}=${value('"date"')} `)
  .move(-23, moveOpts)
  .delete(14, delOpts)
  .exec(phase.date)
  // Date input with Next button
  .pause(SHOW)
  .move(25, moveOpts)
  .type("<br />  ", moveOpts)
  .type(`&lt;${tag("button")}&gt;Next&lt;/${tag("button")}&gt;`)
  .exec(phase.next)
  // Select
  .pause(SHOW)
  .move(-24, moveOpts)
  .delete(21, delOpts)
  .type(`&lt;${tag("select")}&gt;&lt;/${tag("select")}&gt;`)
  .move(-9, moveOpts)
  .type("<br />    <br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`&lt;${tag("option")}&gt;Select...&lt;/${tag("option")}&gt;`)
  .exec(phase.select)
  // Checkbox
  .pause(SHOW)
  .move(12, moveOpts)
  .delete(50, delOpts)
  .type(`${tag("label")}&gt;&lt;/${tag("label")}&gt;`)
  .move(-8, moveOpts)
  .type("<br />    <br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`&lt;${tag("input")} ${attr("type")}=${value('"checkbox"')} /&gt;`)
  .type("<br />    ", moveOpts)
  .type("Publish on my profile")
  .move(35, moveOpts)
  .delete(24, delOpts)
  .exec(phase.checkbox)
  // Checkbox checked
  .pause(SHOW)
  .move(-40, moveOpts)
  .type(` ${attr("checked")}`)
  .exec(phase.check(true))
  // Switch checked
  .pause(SHOW)
  .move(1, moveOpts)
  .type("<br />    ", moveOpts)
  .move(-14, moveOpts)
  .type("<br />     ", moveOpts)
  .move(-22, moveOpts)
  .type("<br />     ", moveOpts)
  .move(16, moveOpts)
  .type("<br />      ", moveOpts)
  .type(`${attr("role")}=${value('"switch"')}`)
  .exec(phase.switch)
  // Switch not checked
  .pause(SHOW)
  .move(14, moveOpts)
  .delete(14, delOpts)
  .exec(phase.check(false))
  // Range
  .pause(SHOW)
  .move(34, moveOpts)
  .delete(26, delOpts)
  .move(-56, moveOpts)
  .type("    <br />    ", moveOpts)
  .move(-9, moveOpts)
  .type("Brightness")
  .move(37, moveOpts)
  .delete(10, delOpts)
  .type(value('"range"'))
  .move(20, moveOpts)
  .delete(13, delOpts)
  .type(`${attr("value")}=${value('"25"')}`)
  .exec(phase.range)
  // Range to 50
  .pause(SHOW / 4)
  .delete(4, delOpts)
  .type(value('"50"'))
  .exec(phase.range50)
  // Loop to input email
  .pause(SHOW)
  .move(20, moveOpts)
  .delete(96, delOpts)
  .move(-1, moveOpts)
  .move(1, moveOpts)
  .type(`${smallCode[1]}<br />`)
  .move(-1, moveOpts)
  .type(smallCode[2])
  .type(smallCode[3])
  .type(smallCode[4])
  .type(" ", instant)
  .delete(1, instant)
  .exec(phase.loop);

// --- Start -------------------------------------------------------------------------------------
if (article && form && code) {
  new IntersectionObserver(([entry]) => {
    onScreen = entry.isIntersecting;
    if (onScreen) for (const done of resumes.splice(0)) done();
  }).observe(article);
  let isLarge = innerWidth >= LARGE;
  addEventListener("resize", () => {
    if ((innerWidth >= LARGE) === isLarge) return;
    isLarge = !isLarge;
    start((isLarge ? large : small).steps);
  }, { passive: true });
  start((isLarge ? large : small).steps);
}
