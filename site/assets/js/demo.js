// demo.js: the homepage's widgets, on / (/demo is not built, PLAN.md Owner answers 5). Each does
// nothing when its markup is absent.
//
// 1. femto off and on. section.proof's div[data-femto-demo] holds a declarative shadow root whose
//    one element, div[part=page], has a shadow root of its own: it links femto's stylesheet and holds
//    a block of everyday markup, which the code sample under it shows again (landing.css explains the
//    two roots). The switch in label[data-femto-switch], hidden in the markup, turns that <link> off
//    and on (link.disabled), so the markup shows in the browser's own styles or in femto's. Without
//    JavaScript the switch stays hidden and femto stays on. The block's links go nowhere: a click on
//    one is canceled. Its form has method="dialog", whose submit does nothing outside a <dialog>
//    (criterion 9); the code sample keeps a plain <form>.
//
// 2. The theme swatches: fieldset[data-swatches], hidden in the markup, gets one radio per femto
//    theme color, in the docs' Theme picker's order with azure checked, each named by its color and
//    drawn in that theme's --femto-primary-background. Choosing one recolors the page in place: the
//    color's css/themes/<color>.css is linked after femto's stylesheet, on the page and in the
//    block's shadow root, and the old color's link goes once the new one has loaded, so the page
//    never shows a mix. A theme file that fails to load goes too, and the swatch goes back to the
//    color the page keeps. Azure, femto's own color, needs no file. The URL does not change: ?theme=
//    is the docs page's (PLAN.md Decision 8), and nothing is stored.
//
// 3. The typing demo, a small hand-written loop rather than TypeIt, which is GPL-3.0 or commercially
//    licensed (PLAN.md Risks). It binds to `article[data-typing-demo]`, with its form and
//    `footer.code pre code`.
//    - The code sample is a list of characters, each with the class of the span it is typed in,
//      plus line breaks, and a cursor among them. Each step types, moves the cursor, deletes or
//      pauses (counts are in characters, a line break counts as one), then runs the step's form
//      change. The busy step first types the disabled attribute that phase.busy gives the search
//      input: it moves back to the input's ">" (the large layout) or to the end of its placeholder
//      line (the small one), types it, and moves on to the button, and the date step's delete over
//      the input's attributes takes it too.
//    - The form follows the code: one state object, rendered once per change. The email input has
//      type="email" from the start, as the code shows it. The form is inert in the markup: it is a
//      picture of a form, which no pointer, key or screen reader reaches, so the control the code
//      focuses has the class is-focused, which landing.css draws as femto's :focus.
//    - The large layout (attributes on one line) is used while the viewport is at least 1280 px wide,
//      the small one below; crossing 1280 px starts the demo over in the other layout.
//    - The sequence loops until it is paused. It waits while the demo is off screen or the page is
//      hidden (PLAN.md Rules, JavaScript: intervals run only while their element is on screen) and
//      while it is paused: `button[data-demo-pause]` in the article pauses and plays it (its label
//      says which it does, "Pause" or "Play"), and the demo starts paused under
//      prefers-reduced-motion: reduce, or pauses when that setting turns on (WCAG 2.2.2). Paused,
//      nothing changes: the steps, the form changes they scheduled and the email's letters wait, and
//      the cursor stops blinking.

import { capitalize, setAttr } from "./site.js";

// --- 1. femto off and on -----------------------------------------------------------------------
const block = document.querySelector("div[data-femto-demo]")?.shadowRoot?.firstElementChild?.shadowRoot;
const blockFemto = block?.querySelector('link[href="/vendor/femto/dist/femto.min.css"]');
const femtoSwitch = document.querySelector("label[data-femto-switch]");
const femtoInput = femtoSwitch?.querySelector("input[role=switch]");
if (block) {
  block.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("a[href]")) event.preventDefault();
  });
}
if (blockFemto && femtoInput) {
  // The link follows the switch from the start, which a reload may restore unchecked.
  const follow = () => {
    blockFemto.disabled = !femtoInput.checked;
  };
  follow();
  femtoInput.addEventListener("change", follow);
  femtoSwitch.hidden = false;
}

// --- 2. The theme swatches ---------------------------------------------------------------------
// femto's theme colors (css/themes/) in the docs' Theme picker's order, around the color wheel from
// red to the greys, with azure, the default, checked; and in the same order each one's
// --femto-primary-background, the color of its buttons.
const THEMES = ["red", "orange", "pumpkin", "amber", "yellow", "lime", "green", "jade", "cyan", "azure",
  "blue", "indigo", "violet", "purple", "fuchsia", "pink", "sand", "grey", "zinc", "slate"];
const SWATCHES = ("c52f21 d24317 ff9500 ffbf00 f2df0d a5d601 398712 007a50 047878 0172ad "
  + "2060df 524ed2 7540bf 9236a4 c1208b d92662 ccc6b4 ababab 646b79 525f7a").split(" ");
const swatches = document.querySelector("fieldset[data-swatches]");
const pageFemto = document.querySelector('head > link[href="/vendor/femto/dist/femto.min.css"]');
if (swatches && pageFemto) {
  // Each femto link's theme links, in the order they were chosen: the page's, and the block's. The
  // newest goes right after femto's, before the older ones, which keep their color until it has
  // loaded and then go.
  const themed = new Map([[pageFemto, []]]);
  if (blockFemto) themed.set(blockFemto, []);
  const THEMES_PATH = "/vendor/femto/css/themes/";
  // The newest link, once it has loaded, replaces the older ones.
  const settle = (links) => {
    if (links.at(-1)?.sheet) for (const old of links.splice(0, links.length - 1)) old.remove();
  };
  const recolor = (color) => {
    for (const [femto, links] of themed) {
      if (color === "azure") {
        for (const old of links.splice(0)) old.remove();
        continue;
      }
      const link = el("link", { rel: "stylesheet", href: `${THEMES_PATH}${color}.css` });
      links.push(link);
      link.addEventListener("load", () => {
        if (links.at(-1) === link) settle(links);
      });
      // A file that fails goes. If it was the newest choice, the page keeps the newest color it
      // still has (azure with none), and that color's swatch is checked again.
      link.addEventListener("error", () => {
        const i = links.indexOf(link);
        if (i < 0) return;
        links.splice(i, 1);
        link.remove();
        if (i < links.length) return;
        settle(links);
        const kept = links.at(-1)?.getAttribute("href").slice(THEMES_PATH.length, -".css".length) ?? "azure";
        swatches.querySelector(`input[value="${kept}"]`).checked = true;
      });
      femto.after(link);
    }
  };
  THEMES.forEach((color, i) => {
    const label = capitalize(color);
    const radio = el("input", { type: "radio", name: "theme-color", value: color, "aria-label": label, title: label });
    radio.style.setProperty("--site-swatch", `#${SWATCHES[i]}`);
    radio.checked = color === "azure";
    swatches.append(radio);
  });
  swatches.addEventListener("change", (event) => recolor(event.target.value));
  swatches.hidden = false;
}

// --- 3. The typing demo ------------------------------------------------------------------------
const article = document.querySelector("article[data-typing-demo]");
const form = article?.querySelector("form");
const code = article?.querySelector("footer.code pre code");
const toggle = article?.querySelector("button[data-demo-pause]");

// --- Timing: a pause of 70 ms and a phase of 3.5 s ----------------------------------------------
const PAUSE = 70;
const SHOW = 3500;
const FILL = 7;    // ms per character as the email field fills in (the input's own interval)
const TYPE = 17;   // ms per typed code character: about one a frame
const LARGE = 1280;

// --- The code sample ---------------------------------------------------------------------------
// A step's string, written with these helpers, is split into characters with the class of the span
// they are in: these strings hold only <span class="...">text</span>, <br />, &lt;, &gt; and plain
// text.
const tag = (v) => `<span class="tag">${v}</span>`;
const attr = (v) => `<span class="attr">${v}</span>`;
const value = (v) => `<span class="value">${v}</span>`;
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

// A queue of steps, written as a chain of type, move, delete, pause and exec.
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
// The form's state and its initial values.
const INITIAL = {
  formRole: null, formGroupIsFocused: false,
  displayInput: true, inputPlaceholder: "Enter your email", inputInvalid: null, inputType: "email",
  inputValue: "", displayedInputValue: "", inputIsDisabled: false, inputIsFocused: false,
  inputHelper: null,
  displaySelect: false,
  displayCheckbox: false, checkboxIsChecked: false, checkboxRole: null, checkboxIsFocused: false,
  displayRange: false, rangeValue: 0, rangeIsFocused: false,
  displayButton: false, buttonType: null, buttonLabel: null, buttonIsBusy: false, buttonIsFocused: false,
};
let state = { ...INITIAL };

function el(name, attrs, ...children) {
  const element = document.createElement(name);
  for (const [k, v] of Object.entries(attrs)) element.setAttribute(k, v);
  element.append(...children);
  return element;
}

// The form's controls, in their order. The input is the page's own; the others are made once and
// put in or taken out as their display state changes.
const parts = form && {
  input: form.querySelector("input"),
  helper: el("small", {}),
  // The select is as the code shows it, <select><option>Select...</option></select>: no required
  // and no disabled placeholder option, which femto draws in its placeholder color (select:invalid).
  select: el("select", { name: "select-demo" }, el("option", {}, "Select...")),
  checkboxLabel: el("label", {}),
  checkbox: el("input", { name: "checkbox-demo", type: "checkbox" }),
  rangeLabel: el("label", {}, "Brightness"),
  range: el("input", { name: "range-demo", type: "range", value: "0" }),
  button: el("button", { "aria-busy": "false" }),
};
if (parts) {
  parts.checkboxLabel.append(parts.checkbox, "Publish on my profile");
  parts.rangeLabel.append(parts.range);
}

function renderForm() {
  const s = state, { input, helper, select, checkboxLabel, checkbox, rangeLabel, range, button } = parts;
  setAttr(form, "role", s.formRole || null);
  setAttr(form, "class", s.formGroupIsFocused && "is-focused");
  setAttr(input, "type", s.inputType);
  setAttr(input, "placeholder", s.inputPlaceholder);
  setAttr(input, "class", s.inputIsFocused && "is-focused");
  input.disabled = s.inputIsDisabled;
  input.value = s.displayedInputValue;
  setAttr(input, "value", s.displayedInputValue);
  setAttr(input, "aria-invalid", s.inputInvalid === null ? null : String(s.inputInvalid));
  if (helper.textContent !== (s.inputHelper ?? "")) helper.textContent = s.inputHelper ?? "";
  setAttr(checkbox, "role", s.checkboxRole);
  setAttr(checkbox, "class", s.checkboxIsFocused && "is-focused");
  checkbox.checked = s.checkboxIsChecked;
  setAttr(range, "class", s.rangeIsFocused && "is-focused");
  range.value = String(s.rangeValue);
  setAttr(range, "value", s.rangeValue);
  setAttr(button, "type", s.buttonType);
  setAttr(button, "class", s.buttonIsFocused && "is-focused");
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
let paused = false;
const resumes = [];
const running = () => onScreen && !paused && document.visibilityState === "visible";
function resume() {
  if (running()) for (const done of resumes.splice(0)) done();
}

// ms later, and then only once the demo is on screen, in a shown page, and not paused.
function wait(ms) {
  return new Promise((done) => setTimeout(done, ms))
    .then(() => running() || new Promise((done) => resumes.push(done)));
}
// A form change later in this run.
function later(ms, fn) {
  const mine = run;
  wait(ms).then(() => mine === run && fn());
}

// Change the form state and render it once. inputValue fills the email field in letter by letter;
// a date or an empty value shows at once.
function set(changes) {
  const filled = "inputValue" in changes && changes.inputValue !== state.inputValue;
  state = { ...state, ...changes };
  if (filled) {
    const v = state.inputValue;
    if (!v || /^\d{4}-\d{2}-\d{2}$/.test(v)) state.displayedInputValue = v;
    else fill(v, run);
  }
  renderForm();
}
async function fill(v, mine) {
  for (const letter of v) {
    await wait(FILL);
    if (mine !== run) return;
    set({ displayedInputValue: state.displayedInputValue + letter });
  }
  later(SHOW / 4, () => set({ inputIsFocused: false }));
}

// The cursor: a zero-width "|" between characters (landing.css), solid while the code changes and
// blinking once it rests (and solid while the demo is paused). It is no part of the code, so a
// screen reader skips it.
const caret = el("span", { "aria-hidden": "true" }, "|");
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
  blink ??= caret.animate([{ opacity: 1, easing: "step-end" }, { opacity: 0, easing: "step-end" }, { opacity: 1 }],
    { duration: 1000, iterations: Infinity });
  blink.currentTime = 0;
  if (paused) blink.pause();
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

// --- The steps, in the large layout and the small one ------------------------------------------
// The form change after each phase, shared by both layouts.
const phase = {
  email: () => {
    set({ inputType: "email" });
    later(PAUSE, () => {
      set({ inputIsFocused: true });
      later(PAUSE * 2, () => set({ inputValue: "invalid@example" }));
    });
  },
  invalid: () => set({ inputInvalid: true }),
  helper: () => set({ inputHelper: "Please enter a valid email!" }),
  subscribe: () => set({ formRole: "group", inputInvalid: null, inputValue: "", inputHelper: null, displayButton: true,
    buttonType: "submit", buttonLabel: "Subscribe" }),
  search: () => set({ formRole: "search", inputType: "search", inputPlaceholder: "Search", buttonLabel: "Search" }),
  busy: () => set({ buttonIsFocused: true, formGroupIsFocused: true, buttonIsBusy: true, inputIsDisabled: true,
    buttonLabel: "Search..." }),
  date: () => {
    const now = new Date(); // today in the reader's own time zone, as yyyy-MM-dd
    const day = [now.getFullYear(), now.getMonth() + 1, now.getDate()].map((n) => String(n).padStart(2, "0")).join("-");
    set({ formGroupIsFocused: false, formRole: null, displayButton: false, buttonIsFocused: false,
      buttonIsBusy: false, inputType: "date", displayedInputValue: day, inputValue: day,
      inputPlaceholder: null, inputIsDisabled: false });
  },
  // The code's <button>Next</button> has no type, and femto makes only a button[type=submit] full
  // width: the type the subscribe phase set goes (setAttr removes it), until the next loop's.
  next: () => set({ displayButton: true, buttonType: null, buttonLabel: "Next" }),
  select: () => set({ displayInput: false, displaySelect: true }),
  checkbox: () => set({ displaySelect: false, displayButton: false, displayCheckbox: true }),
  check: (checked) => () => {
    set({ checkboxIsFocused: true });
    later(PAUSE, () => {
      set({ checkboxIsChecked: checked });
      later(PAUSE * 2, () => set({ checkboxIsFocused: false }));
    });
  },
  switch: () => set({ checkboxRole: "switch" }),
  range: () => set({ displayCheckbox: false, displayRange: true, rangeValue: 25 }),
  range50: () => {
    set({ rangeIsFocused: true });
    later(PAUSE, () => {
      set({ rangeValue: 50 });
      later(PAUSE * 2, () => set({ rangeIsFocused: false }));
    });
  },
  loop: () => set({ displayRange: false, displayInput: true, inputType: "email", inputValue: "",
    displayedInputValue: "", inputPlaceholder: "Enter your email" }),
};

const largeCode = [
  `&lt;${tag("form")}&gt;`,
  `<br />  &lt;${tag("input")} ${attr("type")}=${value('"email"')} ${attr("placeholder")}=${value('"Enter your email"')}&gt;`,
  `<br />&lt;/${tag("form")}&gt;`,
];
const large = queue()
  // Email input
  .type(largeCode[0], instant).type(largeCode[1], instant).type(largeCode[2], instant)
  .move(-9, instant)
  .pause(SHOW / 2)
  .exec(phase.email)
  // Invalid email input
  .pause(SHOW / 2)
  .type(` ${attr("aria-invalid")}=${value('"true"')}`)
  .exec(phase.invalid)
  // Invalid email input helper
  .pause(SHOW)
  .move(1, moveOpts)
  .type("  <br />  ", moveOpts)
  .type(`&lt;${tag("small")}&gt;Please enter a valid email!&lt;/${tag("small")}&gt;`)
  .exec(phase.helper)
  // Email input with submit button
  .pause(SHOW)
  .delete(47, delOpts)
  .move(-1, moveOpts)
  .delete(20, delOpts)
  .move(-53, moveOpts)
  .type(`<br />  &lt;${tag("fieldset")} ${attr("role")}=${value('"group"')}&gt;`)
  .move(54, moveOpts)
  .type(`<br />  &lt;/${tag("fieldset")}&gt;`)
  .move(-65, moveInstant)
  .type("  ", moveInstant)
  .move(51, moveInstant)
  .type(`<br />    &lt;${tag("button")} ${attr("type")}=${value('"submit"')}&gt;&lt;/${tag("button")}&gt;`)
  .move(-9, moveOpts)
  .type("Subscribe")
  .exec(phase.subscribe)
  // Search input with button
  .pause(SHOW)
  .move(-92, moveOpts)
  .delete(26, delOpts)
  .move(115, moveOpts)
  .delete(14, delOpts)
  .move(-40, moveInstant)
  .delete(2, delInstant)
  .move(-54, moveInstant)
  .delete(2, delInstant)
  .move(-4, moveOpts)
  .type(` ${attr("role")}=${value('"search"')}`)
  .move(23, moveOpts)
  .delete(7, delOpts)
  .type(value('"search"'))
  .move(31, moveOpts)
  .delete(18, delOpts)
  .type(value('"Search"'))
  .move(35, moveOpts)
  .delete(8, delOpts)
  .type("earch")
  .exec(phase.search)
  // Search input and button submitted
  .pause(SHOW)
  .move(-32, moveOpts)
  .type(` ${attr("disabled")}`)
  .move(25, moveOpts)
  .type(` ${attr("aria-busy")}=${value('"true"')}`)
  .move(7, moveOpts)
  .type("...")
  .exec(phase.busy)
  // Date input
  .pause(SHOW)
  .move(9, moveOpts)
  .delete(60, delOpts)
  .move(-1, moveOpts)
  .delete(38, delOpts)
  .type(value('"date"'))
  .move(-22, moveOpts)
  .delete(14, delOpts)
  .exec(phase.date)
  // Date input with Next button
  .pause(SHOW)
  .move(23, moveOpts)
  .type(`<br />  &lt;${tag("button")}&gt;Next&lt;/${tag("button")}&gt;`)
  .exec(phase.next)
  // Select
  .pause(SHOW)
  .move(-24, moveOpts)
  .delete(19, delOpts)
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
  .type(`&lt;${tag("input")} ${attr("type")}=${value('"checkbox"')}&gt;`)
  .type("<br />    ", moveOpts)
  .type("Publish on my profile")
  .move(35, moveOpts)
  .delete(24, delOpts)
  .exec(phase.checkbox)
  // Checkbox checked
  .pause(SHOW)
  .move(-38, moveOpts)
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
  .move(27, moveOpts)
  .delete(26, delOpts)
  .move(-42, moveOpts)
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
  .move(13, moveOpts)
  .delete(77, delOpts)
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
  "<br />  &gt;",
  `<br />&lt;/${tag("form")}&gt;`,
];
const small = queue()
  // Email input
  .type(smallCode[0], instant).type(smallCode[1], instant).type(smallCode[2], instant)
  .type(smallCode[3], instant).type(smallCode[4], instant).type(smallCode[5], instant)
  .move(-12, instant)
  .pause(SHOW / 2)
  .exec(phase.email)
  // Invalid email input
  .pause(SHOW / 2)
  .type("<br />    ", moveOpts)
  .type(`${attr("aria-invalid")}=${value('"true"')}`)
  .exec(phase.invalid)
  // Invalid email input helper
  .pause(SHOW)
  .move(5, moveOpts)
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
  .move(-4, moveOpts)
  .delete(24, delOpts)
  .move(-58, moveOpts)
  .type("<br />  ", moveOpts)
  .move(-3, moveOpts)
  .type(`&lt;${tag("fieldset")} ${attr("role")}=${value('"group"')}&gt;`)
  .move(65, moveOpts)
  .type("<br />  ", moveOpts)
  .type(`&lt;/${tag("fieldset")}&gt;`)
  .move(-15, moveInstant)
  .type("  ", moveInstant)
  .move(-36, moveInstant)
  .type("  ", moveInstant)
  .move(-19, moveInstant)
  .type("  ", moveInstant)
  .move(-12, moveInstant)
  .type("  ", moveInstant)
  .move(68, moveInstant)
  .type("<br />    ", moveOpts)
  .type(`&lt;${tag("button")} ${attr("type")}=${value('"submit"')}&gt;&lt;/${tag("button")}&gt;`)
  .move(-9, moveOpts)
  .type("<br />      <br />    ", moveOpts)
  .move(-5, moveOpts)
  .type("Subscribe")
  .exec(phase.subscribe)
  // Search input with button
  .pause(SHOW)
  .move(-116, moveOpts)
  .delete(26, delOpts)
  .move(144, moveOpts)
  .delete(14, delOpts)
  .move(-10, moveInstant)
  .delete(2, delInstant)
  .move(-12, moveInstant)
  .delete(2, delInstant)
  .move(-26, moveInstant)
  .delete(2, delInstant)
  .move(-4, moveInstant)
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
  .move(43, moveOpts)
  .delete(8, delOpts)
  .type("earch")
  .exec(phase.search)
  // Search input and button submitted
  .pause(SHOW)
  .move(-40, moveOpts)
  .type(`<br />    ${attr("disabled")}`)
  .move(14, moveOpts)
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
  .move(-1, moveOpts)
  .delete(59, delOpts)
  .type(` ${attr("type")}=${value('"date"')}`)
  .move(-22, moveOpts)
  .delete(14, delOpts)
  .exec(phase.date)
  // Date input with Next button
  .pause(SHOW)
  .move(23, moveOpts)
  .type("<br />  ", moveOpts)
  .type(`&lt;${tag("button")}&gt;Next&lt;/${tag("button")}&gt;`)
  .exec(phase.next)
  // Select
  .pause(SHOW)
  .move(-24, moveOpts)
  .delete(19, delOpts)
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
  .type(`&lt;${tag("input")} ${attr("type")}=${value('"checkbox"')}&gt;`)
  .type("<br />    ", moveOpts)
  .type("Publish on my profile")
  .move(35, moveOpts)
  .delete(24, delOpts)
  .exec(phase.checkbox)
  // Checkbox checked
  .pause(SHOW)
  .move(-38, moveOpts)
  .type(` ${attr("checked")}`)
  .exec(phase.check(true))
  // Switch checked
  .pause(SHOW)
  .move(0, moveOpts)
  .type("<br />    ", moveOpts)
  .move(-13, moveOpts)
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
  .move(32, moveOpts)
  .delete(26, delOpts)
  .move(-54, moveOpts)
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
  .move(18, moveOpts)
  .delete(94, delOpts)
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
  new IntersectionObserver((entries) => {
    onScreen = entries.at(-1).isIntersecting; // the latest, when several queued up
    resume();
  }).observe(article);
  document.addEventListener("visibilitychange", resume);
  if (toggle) {
    const pause = (value) => {
      paused = value;
      toggle.textContent = paused ? "Play" : "Pause";
      if (blink && paused) {
        blink.pause();
        blink.currentTime = 0; // the cursor's solid frame
      } else blink?.play();
      resume();
    };
    const reduce = matchMedia("(prefers-reduced-motion: reduce)");
    if (reduce.matches) pause(true);
    toggle.hidden = false; // hidden in the markup, where nothing runs without JavaScript
    reduce.addEventListener("change", () => reduce.matches && pause(true));
    toggle.addEventListener("click", () => pause(!paused));
  }
  const largeMedia = matchMedia(`(min-width: ${LARGE}px)`);
  const restart = () => start((largeMedia.matches ? large : small).steps);
  largeMedia.addEventListener("change", restart);
  restart();
}
