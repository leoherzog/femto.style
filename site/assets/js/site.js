// site.js: every page (loaded from partials/head.html).
//
// The page-wide behaviors, each attached through a data- attribute (PLAN.md Rules, JavaScript):
// - the theme toggles, the header's button[data-scheme-toggle] and the Color schemes section's
//   button[data-scheme-switcher], and the theme-color metas, which follow a stored choice;
// - the copy buttons of code blocks, button[data-copy-link];
// - the code blocks' focus, pre[data-scroll-focus]: only a block that scrolls takes focus;
// - the modal dialogs, <dialog data-modal> with its openers and closers.
// Each does nothing when its markup is absent.
//
// It also exports what other modules build on, so no widget keeps page state of its own:
// - pageTheme(), switchTheme(), onThemeChange(fn): the page's color scheme;
// - createModal(dialog, options): one modal helper per dialog, { open(), close() };
// - nameCopyButton(button): names a copy button by its icon, for one a module writes itself;
// - announceCopy(message): says "Copied" (or the message, "Copy failed") in the page's one copy
//   status region, for a module's own copy control;
// - perFrame(fn): a passive scroll or resize handler that runs fn at most once per frame;
// - setAttr(element, name, value), capitalize(text), escapeText(text): small DOM and text helpers.
// Import them with `import { createModal } from "./site.js";` (the same URL, so the same instance as
// the page's own <script type="module" src="/assets/js/site.js">).

// --- Helpers -----------------------------------------------------------------------------------

// fn at most once per animation frame, for passive scroll and resize listeners.
export function perFrame(fn) {
  let queued = false;
  return () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      fn();
    });
  };
}

// Sets an attribute only when its value differs, so an unchanged state causes no mutation. null,
// undefined or false removes it, true sets it empty, and anything else sets its String().
export function setAttr(element, name, value) {
  if (value === null || value === undefined || value === false) {
    element.removeAttribute(name);
    return;
  }
  const text = value === true ? "" : String(value);
  if (element.getAttribute(name) !== text) element.setAttribute(name, text);
}

// "jade" -> "Jade".
export const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

// Text as HTML: &, < and > escaped, as the browser serializes text.
export const escapeText = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// --- Color scheme (Decision 14) ----------------------------------------------------------------
// The reader's choice is localStorage femtoColorScheme as JSON ('"light"' or '"dark"'). data-theme
// on <html> is set only while a choice is stored (the color-scheme head script sets it before the
// first paint); without one the page follows prefers-color-scheme. A toggle switches to the opposite
// of the current scheme: it stores that scheme, unless it is the OS's, when it removes the stored
// choice instead, so the page follows the OS again. Other tabs follow through the storage event, and
// the OS scheme through matchMedia.

const KEY = "femtoColorScheme";
const root = document.documentElement;
const darkOs = matchMedia("(prefers-color-scheme: dark)");
const themeListeners = new Set();
let unstoredChoice = null; // a choice storage refused to keep (private mode, blocked storage)

function storedTheme() {
  let value = unstoredChoice;
  if (!value) {
    try {
      value = JSON.parse(localStorage.getItem(KEY));
    } catch {
      // No storage, or a value that is not JSON: no choice.
    }
  }
  return value === "light" || value === "dark" ? value : null;
}

const osTheme = () => (darkOs.matches ? "dark" : "light");

// "light" or "dark": the stored choice, else the OS scheme.
export function pageTheme() {
  return storedTheme() ?? osTheme();
}

// fn(theme) after every change of the page's scheme.
export function onThemeChange(fn) {
  themeListeners.add(fn);
}

// The theme toggles: the header's button[data-scheme-toggle] and the Color schemes section's
// button[data-scheme-switcher]. Each one's icon, a span[role=img] (Decision 18), is the sun or moon
// emoji (Decision 16), and its label, "Turn on dark mode" or "Turn off dark mode", follows the
// scheme: the button's text when it has one (the switcher, whose icon is hidden), else the icon's
// aria-label, which names the button (the header toggle).
const SCHEME_EMOJI = { light: "\u2600\uFE0F", dark: "\u{1F319}" };
const toggles = [...document.querySelectorAll("button:is([data-scheme-toggle], [data-scheme-switcher])")];

// The browser's own bar takes femto's background from the two theme-color metas (head.html), one
// per OS scheme. A stored choice applies its own scheme's meta and turns the other off.
const themeColors = [...document.querySelectorAll('head > meta[name="theme-color"][media]')]
  .map((meta) => ({ meta, media: meta.media, scheme: meta.media.includes("dark") ? "dark" : "light" }));

function applyTheme() {
  const stored = storedTheme();
  // The color-scheme head script has usually set it already: an unchanged value causes no mutation.
  setAttr(root, "data-theme", stored);
  for (const { meta, media, scheme } of themeColors) {
    setAttr(meta, "media", !stored ? media : scheme === stored ? "all" : "not all");
  }
  const theme = pageTheme();
  const label = theme === "dark" ? "Turn off dark mode" : "Turn on dark mode";
  for (const toggle of toggles) {
    const icon = toggle.querySelector(":scope > span[role=img]");
    if (!icon) continue;
    const text = [...toggle.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.data.trim());
    if (!text) setAttr(icon, "aria-label", label);
    else if (text.data !== label) text.data = label;
    if (icon.textContent !== SCHEME_EMOJI[theme]) icon.textContent = SCHEME_EMOJI[theme];
  }
  for (const fn of themeListeners) fn(theme);
}

// Switches to the opposite of the current scheme: stored, or, when it is the OS's, no choice.
export function switchTheme() {
  const next = pageTheme() === "dark" ? "light" : "dark";
  unstoredChoice = null;
  try {
    if (next === osTheme()) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Storage unavailable: the choice holds for this page only, and the OS's needs none.
    if (next !== osTheme()) unstoredChoice = next;
  }
  applyTheme();
}

for (const toggle of toggles) toggle.addEventListener("click", switchTheme);
addEventListener("storage", (event) => {
  if (event.key !== KEY && event.key !== null) return;
  unstoredChoice = null;
  applyTheme();
});
darkOs.addEventListener("change", applyTheme);
applyTheme();

// --- Copy buttons --------------------------------------------------------------------------------
// button[data-copy-link], the first child of div.code or footer.code (colors.js's color modal writes
// its own the same way): a click, or Enter or Space, copies the block's code text. The write starts
// in the click itself, while it counts as a user activation, and its outcome shows once it settles:
// the animated check icon with the tooltip "Copied", or the tooltip "Copy failed" (no clipboard, as
// over plain http, or a refused write) with the copy icon kept. 1 s after the latest copy, one timer
// per button restores the button's own icon and tooltip and blurs it, unless it has keyboard focus
// (:focus-visible), which stays where the reader left it. A screen reader hears the outcome too,
// which the tooltip alone does not say, at every copy (announceCopy, below). The icons are Decision
// 18's: the button's one child, a span[role=img] holding the copy character ⧉ and naming the button
// (aria-label "Copy code"), which gives way to a check ✓ with the same name, since the button still
// copies. code.css draws the check in, by the "Copied" tooltip.
// The button takes its name from the icon through aria-labelledby, not from its contents: femto's
// tooltip draws data-tooltip as the button's ::before text, which a name from contents would read
// first ("Copy code Copy code", "Copied Copy code"). nameCopyButton() gives the icon an id,
// copy-icon-<n>, unique on the page, and points the button's aria-labelledby at it; the check that
// swaps in carries the same id and aria-label, so the name stays the icon's label throughout. It runs
// on load for the page's buttons, which do nothing without JavaScript (common.css hides them then,
// as it hides the theme toggle), and colors.js calls it for the color modal's.
//
// The status region is one visually hidden p.visually-hidden role="status", the last child of
// <body>, added once a page has a copy button, before its first text, so that text is announced.
// Every copy button's module announces through it: site.js's own, colors.js's (by site.js's click
// handler) and examples.js's Copy as page, so a page has one region and one timer. While a dialog
// is shown with showModal(), everything outside it leaves the accessibility tree, the region in
// <body> too, so a screen reader would hear none of the color dialog's copies: createModal's
// open() moves the region into the dialog, as its last child, before any copy there, and the
// dialog's close moves it back to the end of <body>. announceCopy() writes its message and empties
// the region 1 s after the latest call, whoever made it: each call restarts the timer, so an earlier
// copy's timer never empties it under a later one. A screen reader can skip a message that repeats
// the one before it, even with the region emptied in between (VoiceOver does), so a message that
// repeats the last one ends in a no-break space, and the next repeat drops it again. A copy while
// the region still says something empties it first and writes the message in the next frame, so the
// change is a whole new message, not a trailing space.

const COPIED_FOR = 1000;
const copies = new WeakMap(); // button -> {icon, check, tooltip, timer} until it reverts
let copyIcons = 0; // the last n given to a copy-icon-<n> id

// Names the copy button by its icon (span[role=img], its one child): aria-labelledby, pointing at
// the icon's id, given one if it has none.
export function nameCopyButton(button) {
  const icon = button.querySelector(":scope > span[role=img]");
  if (!icon) return;
  if (!icon.id) {
    let id;
    do id = `copy-icon-${++copyIcons}`; while (document.getElementById(id));
    icon.id = id;
  }
  setAttr(button, "aria-labelledby", icon.id);
}

// The check ✓ that stands in for the icon while the button shows "Copied": the icon's id, so the
// button's aria-labelledby finds it, and its aria-label. Only one of the two is in the page at a time.
function checkIcon(icon) {
  const check = document.createElement("span");
  check.setAttribute("role", "img");
  for (const name of ["id", "aria-label"]) setAttr(check, name, icon.getAttribute(name));
  check.textContent = "\u2713";
  return check;
}

let copyStatus = null; // the status region
let statusHome = null; // the dialog shown with showModal() that holds the region, else null: <body>
let statusTimer = 0; // empties it 1 s after the latest announceCopy()
let statusFrame = 0; // writes the message, after a copy that found the region still speaking
let lastCopy = ""; // the region's last message, page-wide

// Puts the region, once it exists, at the end of the modal dialog shown, or else of <body>.
function placeStatus() {
  const home = statusHome ?? document.body;
  if (copyStatus && copyStatus.parentElement !== home) home.append(copyStatus);
}

function statusRegion() {
  if (!copyStatus) {
    copyStatus = document.createElement("p");
    copyStatus.className = "visually-hidden";
    copyStatus.setAttribute("role", "status");
  }
  placeStatus();
  return copyStatus;
}

export function announceCopy(message = "Copied") {
  const region = statusRegion();
  const text = lastCopy === message ? `${message}\u00A0` : message;
  lastCopy = text;
  clearTimeout(statusTimer);
  cancelAnimationFrame(statusFrame);
  if (region.textContent) {
    region.textContent = "";
    statusFrame = requestAnimationFrame(() => {
      region.textContent = text;
    });
  } else {
    region.textContent = text;
  }
  statusTimer = setTimeout(() => {
    cancelAnimationFrame(statusFrame);
    region.textContent = "";
  }, COPIED_FOR);
}
if (document.querySelector("button[data-copy-link], [data-color-modal]")) statusRegion();
for (const button of document.querySelectorAll("button[data-copy-link]")) nameCopyButton(button);

// Shows a copy's outcome on its button, and says it, until 1 s after the latest copy.
function showCopy(button, ok) {
  let state = copies.get(button);
  if (!state) {
    const icon = button.querySelector(":scope > span[role=img]");
    if (!icon) return;
    state = { icon, check: checkIcon(icon), tooltip: button.getAttribute("data-tooltip"), timer: 0 };
    copies.set(button, state);
  }
  // replaceWith() does nothing for the one of the two that is not in the page.
  if (ok) state.icon.replaceWith(state.check);
  else state.check.replaceWith(state.icon);
  setAttr(button, "data-tooltip", ok ? "Copied" : "Copy failed");
  announceCopy(ok ? "Copied" : "Copy failed");
  clearTimeout(state.timer);
  state.timer = setTimeout(() => {
    state.check.replaceWith(state.icon);
    setAttr(button, "data-tooltip", state.tooltip);
    copies.delete(button);
    if (!button.matches(":focus-visible")) button.blur();
  }, COPIED_FOR);
}

document.addEventListener("click", (event) => {
  const button = event.target instanceof Element ? event.target.closest("button[data-copy-link]") : null;
  if (!button) return;
  const code = button.parentElement.querySelector("pre code");
  const write = code && navigator.clipboard ? navigator.clipboard.writeText(code.textContent) : Promise.reject();
  write.then(() => showCopy(button, true), () => showCopy(button, false));
});

// --- Code block focus ----------------------------------------------------------------------------
// pre[data-scroll-focus], every highlighted <pre>, which build.mjs writes with tabindex="0" so that
// without JavaScript each one takes focus: a block whose code is wider than it scrolls sideways, and
// the keyboard scrolls it only once it has focus (axe's scrollable-region-focusable). Here only a
// block that overflows keeps tabindex="0", named as a figure, role="figure" with aria-label "HTML
// code" (or CSS, Bash: its code's language): ARIA's figure is the role for a code snippet, and
// unlike a region it is no landmark, so a page of code blocks does not fill the landmark list with
// names that repeat (axe's landmark-unique). The others leave the tab order and carry no role or
// name, so a screen reader neither stops at nor announces them. A ResizeObserver checks a block
// whenever its box changes (the viewport, a closed <details> opening). Code is in femto's monospace
// stack, a system font, so no font load changes its width later. A focused block keeps its
// tabindex until focus has left it.

const LANGUAGES = { html: "HTML", css: "CSS", bash: "Bash" };
const scrollers = [...document.querySelectorAll("pre[data-scroll-focus]")];

function fitFocus(pres) {
  const overflows = pres.map((pre) => pre.scrollWidth > pre.clientWidth || pre.scrollHeight > pre.clientHeight);
  pres.forEach((pre, i) => {
    if (overflows[i]) {
      const language = pre.querySelector("code")?.className.match(/\blanguage-([\w-]+)/)?.[1];
      setAttr(pre, "tabindex", "0");
      setAttr(pre, "role", "figure");
      setAttr(pre, "aria-label", `${LANGUAGES[language] ?? "Example"} code`);
    } else if (pre !== document.activeElement) {
      for (const name of ["tabindex", "role", "aria-label"]) pre.removeAttribute(name);
    }
  });
}

if (scrollers.length) {
  const observer = new ResizeObserver((entries) => fitFocus(entries.map((entry) => entry.target)));
  for (const pre of scrollers) observer.observe(pre);
  document.addEventListener("focusout", (event) => {
    const pre = event.target instanceof Element && event.target.matches("pre[data-scroll-focus]") ? event.target : null;
    if (pre) setTimeout(() => fitFocus([pre])); // once focus has moved on
  });
}

// --- Modal helper (one per dialog) ---------------------------------------------------------------
// Each dialog has a helper of its own with its own state, so opening one never opens another, and
// createModal() returns the dialog's helper when it already has one (its options are the first
// call's), so two modules that bind the same dialog share it. <html>'s modal classes and
// --femto-scrollbar-width are the page's, so one dialog holds them at a time: opening a dialog while
// another is shown hides that one at once, without its animation, and only the dialog that holds
// them takes them away.
// open(): when the page scrolls vertically, sets --femto-scrollbar-width on <html> to the scrollbar's
// width (innerWidth minus <html>'s clientWidth; 0px with overlay scrollbars); sets <html> class
// "modal-is-open modal-is-opening" and opens the dialog; 400 ms later the class is "modal-is-open".
// close(): "modal-is-open modal-is-closing", and 400 ms later no modal class, no
// --femto-scrollbar-width (an emptied style="" stays), the dialog closed, then onClosed().
// The dialog is a true modal, shown with showModal() and closed with close(): the page behind is
// inert, the browser moves focus into the dialog and back to the opener, and Escape (its keydown) and
// the browser's other close requests (the cancel event) run the animated close instead. A click on
// the dialog itself (its backdrop area: femto's dialog is the full-viewport overlay) closes it too,
// when both the press and the release were on it, so a text selection dragged out of the card leaves
// it open. While it is shown it holds the copy status region (above), the only place a screen reader
// can hear it then. femto's modal CSS styles these classes.

const MODAL_DURATION = 400;
const MODAL_CLASSES = ["modal-is-open", "modal-is-opening", "modal-is-closing"];
const modals = new WeakMap(); // dialog -> its helper
let holder = null; // hide() of the helper whose dialog holds <html>'s modal classes

function modalClasses(...names) {
  root.classList.remove(...MODAL_CLASSES);
  root.classList.add(...names);
}

export function createModal(dialog, { onClosed } = {}) {
  if (modals.has(dialog)) return modals.get(dialog);
  let state = "closed"; // "opening", "open", "closing"
  let timer = 0;
  let styled = false; // this modal set --femto-scrollbar-width
  const isOpen = () => state === "opening" || state === "open";

  // Escape, from its keydown on the document while the dialog is in the page. A dialog's cancel
  // event can be canceled only within the page's close-watcher allowance, which the Modal section's
  // two static <dialog open> examples use up on /docs, so there Escape's cancel would close the
  // dialog at once, without its animation. The keydown's preventDefault() stops that close request.
  const onKeydown = (event) => {
    if (event.key !== "Escape" || event.defaultPrevented) return;
    event.preventDefault();
    close();
  };

  // The end of a close, after its animation or at once: <html> given back, the dialog hidden.
  function hide() {
    clearTimeout(timer);
    document.removeEventListener("keydown", onKeydown);
    if (holder === hide) {
      modalClasses();
      if (styled) root.style.removeProperty("--femto-scrollbar-width");
      holder = null;
    }
    styled = false;
    dialog.close();
    if (statusHome === dialog) {
      statusHome = null;
      placeStatus();
    }
    state = "closed";
    onClosed?.();
  }

  function open() {
    if (isOpen()) return;
    if (holder && holder !== hide) holder();
    clearTimeout(timer);
    if (state === "closed") {
      styled = root.scrollHeight > root.clientHeight;
      if (styled) root.style.setProperty("--femto-scrollbar-width", `${innerWidth - root.clientWidth}px`);
      document.addEventListener("keydown", onKeydown);
    }
    holder = hide;
    modalClasses("modal-is-open", "modal-is-opening");
    if (!dialog.open) dialog.showModal();
    statusHome = dialog;
    placeStatus();
    state = "opening";
    timer = setTimeout(() => {
      modalClasses("modal-is-open");
      state = "open";
    }, MODAL_DURATION);
  }

  function close() {
    if (!isOpen()) return;
    clearTimeout(timer);
    modalClasses("modal-is-open", "modal-is-closing");
    state = "closing";
    timer = setTimeout(hide, MODAL_DURATION);
  }

  // A click's target is the nearest element holding both its press and its release, so a press in
  // the card released on the overlay is a click on the dialog: each end is checked on its own.
  let pressed = false;
  let released = false;
  dialog.addEventListener("pointerdown", (event) => {
    pressed = event.target === dialog;
  });
  dialog.addEventListener("pointerup", (event) => {
    released = event.target === dialog;
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog && pressed && released) close();
  });
  // The browser's other close requests (Android's back gesture), where it lets them be canceled.
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    close();
  });

  const helper = { open, close };
  modals.set(dialog, helper);
  return helper;
}

// --- Modal dialogs (data-modal) ------------------------------------------------------------------
// A <dialog data-modal="<name>"> gets its helper on load, a true modal: showModal() makes the page
// behind inert and moves focus into the dialog, and the close gives focus back to the opener. A
// click on [data-modal-open="<name>"] opens it, and a click on a [data-modal-close] inside it closes
// it; the helper adds the backdrop click and Escape, both with the animated close. The Modal
// section's demo is the one on the site.

const dialogs = document.querySelectorAll("dialog[data-modal]");
for (const dialog of dialogs) createModal(dialog);
if (dialogs.length) {
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const name = target?.closest("[data-modal-open]")?.getAttribute("data-modal-open");
    if (name) {
      const dialog = [...dialogs].find((element) => element.getAttribute("data-modal") === name);
      if (dialog) createModal(dialog).open();
      return;
    }
    const dialog = target?.closest("[data-modal-close]")?.closest("dialog[data-modal]");
    if (dialog) createModal(dialog).close();
  });
}
