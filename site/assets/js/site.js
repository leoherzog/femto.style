// site.js: every page (loaded from partials/head.html).
//
// It rebuilds the Remix site's page-wide behaviors, each attached through a data- attribute (PLAN.md
// Rules, JavaScript):
// - the header theme toggle, button[data-scheme-toggle] (PageContext.jsx, Nav.jsx), and the
//   theme-color metas, which follow a stored choice;
// - the copy buttons of code blocks, button[data-copy-link] (Code.jsx);
// - the code blocks' focus, pre[data-scroll-focus]: only a block that scrolls takes focus;
// - the submit of example forms, canceled (each form also has method="dialog", so none submits
//   without JavaScript either);
// - the modal dialogs, <dialog data-modal> with its openers and closers (ModalContext.jsx).
// Each does nothing when its markup is absent.
//
// It also exports what other modules build on, so no widget keeps page state of its own:
// - pageTheme(), switchTheme(), onThemeChange(fn): the page's color scheme;
// - createModal(dialog, options): one modal helper per dialog (ModalContext.jsx);
// - nameCopyButton(button): names a copy button by its icon, for one a module writes itself;
// - announceCopy(): says "Copied" in the page's one copy status region, for a module's own copy
//   control;
// - perFrame(fn): a passive scroll or resize handler that runs fn at most once per frame.
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

// --- Color scheme (Decision 14) ----------------------------------------------------------------
// The reader's choice is localStorage femtoColorScheme as JSON ('"light"' or '"dark"'). data-theme
// on <html> is set only while a choice is stored (the color-scheme head script sets it before the
// first paint); without one the page follows prefers-color-scheme. The toggle stores the opposite of
// the current scheme. Other tabs follow through the storage event, and the OS scheme through matchMedia.

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

// "light" or "dark": the stored choice, else the OS scheme.
export function pageTheme() {
  return storedTheme() ?? (darkOs.matches ? "dark" : "light");
}

// fn(theme) after every change of the page's scheme; returns a function that removes it.
export function onThemeChange(fn) {
  themeListeners.add(fn);
  return () => themeListeners.delete(fn);
}

// The header toggle (button[data-scheme-toggle] in the header nav, a link in the Remix site's
// Nav.jsx): its icon, the button's one child, a span[role=img] (Decision 18), is the owner's
// sun or moon emoji (Decision 16), not the Remix site's animated SVG, and names the button. Its emoji
// and its aria-label follow the scheme. docs.js's Color schemes switcher shows the same emoji.
export const SCHEME_EMOJI = { light: "\u2600\uFE0F", dark: "\u{1F319}" };
const toggles = [...document.querySelectorAll("button[data-scheme-toggle]")];

// The browser's own bar takes femto's background from the two theme-color metas (head.html), one
// per OS scheme. A stored choice applies its own scheme's meta and turns the other off.
const themeColors = [...document.querySelectorAll('head > meta[name="theme-color"][media]')]
  .map((meta) => ({ meta, media: meta.media, scheme: meta.media.includes("dark") ? "dark" : "light" }));

function applyTheme() {
  const stored = storedTheme();
  // The color-scheme head script has usually set it already: an unchanged value causes no mutation.
  if (stored && root.getAttribute("data-theme") !== stored) root.setAttribute("data-theme", stored);
  else if (!stored) root.removeAttribute("data-theme");
  for (const { meta, media, scheme } of themeColors) {
    const want = !stored ? media : scheme === stored ? "all" : "not all";
    if (meta.media !== want) meta.media = want;
  }
  const theme = pageTheme();
  const dark = theme === "dark";
  for (const toggle of toggles) {
    const icon = toggle.querySelector(":scope > span[role=img]");
    if (!icon) continue;
    const label = dark ? "Turn off dark mode" : "Turn on dark mode";
    if (icon.getAttribute("aria-label") !== label) icon.setAttribute("aria-label", label);
    const emoji = SCHEME_EMOJI[dark ? "dark" : "light"];
    if (icon.textContent !== emoji) icon.textContent = emoji;
  }
  for (const fn of themeListeners) fn(theme);
}

// Stores the opposite of the current scheme.
export function switchTheme() {
  const next = pageTheme() === "dark" ? "light" : "dark";
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
    unstoredChoice = null;
  } catch {
    unstoredChoice = next; // storage unavailable: the choice holds for this page only
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

// --- Copy buttons (Code.jsx) ---------------------------------------------------------------------
// button[data-copy-link] (the first child of div.code or footer.code; colors.js's color modal
// writes its own the same way; links with tabindex="-1" in the Remix site, which the keyboard could
// not reach): a click, or Enter or Space, copies the block's code text, shows the
// animated check icon with the tooltip "Copied", and 1 s later restores the clipboard icon and "Copy
// to clipboard" and blurs the button, unless it has keyboard focus (:focus-visible), which stays
// where the reader left it. As in Code.jsx, every click schedules its own revert, so after repeated
// clicks the first one's timer reverts (1 s after the first click) and each later one only blurs, or
// reverts a "Copied" a still later click showed. A screen reader hears "Copied" too, which the
// tooltip alone does not say, at every click, the later ones too (announceCopy, below). The icons
// are Decision 18's: the button's one child, a span[role=img] holding the copy character ⧉ and
// naming the button (aria-label "Copy code"), which gives way to a check ✓ with the same name,
// since the button still copies. code.css draws the check in, by the "Copied" tooltip.
// The button takes its name from the icon through aria-labelledby, not from its contents: femto's
// tooltip draws data-tooltip as the button's ::before text, which a name from contents would read
// first ("Copy to clipboard Copy code", "Copied Copy code"). nameCopyButton() gives the icon an id,
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
// dialog's close moves it back to the end of <body>. announceCopy()
// writes "Copied" and empties the region 1 s after the latest call, whoever made it: each call
// restarts the timer, so an earlier copy's timer never empties it under a later one. A copy while
// the region still says "Copied" would write the same text, which is no change, and a screen
// reader would say nothing; so the region is emptied first and "Copied" written again in the next
// frame.

const COPIED_FOR = 1000;
const copied = new WeakMap(); // button -> {icon, check} while it shows "Copied"
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
  if (button.getAttribute("aria-labelledby") !== icon.id) button.setAttribute("aria-labelledby", icon.id);
}

// The check ✓ that stands in for the icon while the button shows "Copied": the icon's id, so the
// button's aria-labelledby finds it, and its aria-label. Only one of the two is in the page at a time.
function checkIcon(icon) {
  const check = document.createElement("span");
  check.setAttribute("role", "img");
  for (const name of ["id", "aria-label"]) {
    const value = icon.getAttribute(name);
    if (value) check.setAttribute(name, value);
  }
  check.textContent = "\u2713";
  return check;
}

let copyStatus = null; // the status region
let statusHome = null; // the dialog shown with showModal() that holds the region, else null: <body>
let statusTimer = 0; // empties it 1 s after the latest announceCopy()
let statusFrame = 0; // writes "Copied" again, after a copy that found it already there

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

export function announceCopy() {
  const region = statusRegion();
  clearTimeout(statusTimer);
  cancelAnimationFrame(statusFrame);
  if (region.textContent === "Copied") {
    region.textContent = "";
    statusFrame = requestAnimationFrame(() => {
      region.textContent = "Copied";
    });
  } else {
    region.textContent = "Copied";
  }
  statusTimer = setTimeout(() => {
    cancelAnimationFrame(statusFrame);
    region.textContent = "";
  }, COPIED_FOR);
}
if (document.querySelector("button[data-copy-link], [data-color-modal]")) statusRegion();
for (const button of document.querySelectorAll("button[data-copy-link]")) nameCopyButton(button);

document.addEventListener("click", (event) => {
  const button = event.target instanceof Element ? event.target.closest("button[data-copy-link]") : null;
  if (!button) return;
  const code = button.parentElement.querySelector("pre code");
  if (code) navigator.clipboard?.writeText(code.textContent).catch(() => {});
  if (!copied.has(button)) {
    const icon = button.querySelector(":scope > span[role=img]");
    if (!icon) return;
    const check = checkIcon(icon);
    icon.replaceWith(check);
    button.setAttribute("data-tooltip", "Copied");
    copied.set(button, { icon, check });
  }
  announceCopy();
  setTimeout(() => {
    const state = copied.get(button);
    if (state) {
      state.check.replaceWith(state.icon);
      button.setAttribute("data-tooltip", "Copy to clipboard");
      copied.delete(button);
    }
    if (!button.matches(":focus-visible")) button.blur();
  }, COPIED_FOR);
});

// --- Code block focus ----------------------------------------------------------------------------
// pre[data-scroll-focus], every highlighted <pre>, which build.mjs writes with tabindex="0" so that
// without JavaScript each one takes focus: a block whose code is wider than it scrolls sideways, and
// the keyboard scrolls it only once it has focus (axe's scrollable-region-focusable). Here only a
// block that overflows keeps tabindex="0", named as a figure, role="figure" with aria-label "HTML
// code" (or CSS, SCSS, Bash: its code's language): ARIA's figure is the role for a code snippet, and
// unlike a region it is no landmark, so a page of code blocks does not fill the landmark list with
// names that repeat (axe's landmark-unique). The others leave the tab order and carry no role or
// name, so a screen reader neither stops at nor announces them. A ResizeObserver checks a block
// whenever its box changes (the viewport, a closed <details> opening). Code is in femto's monospace
// stack, a system font, so no font load changes its width later. A focused block keeps its
// tabindex until focus has left it.

const LANGUAGES = { html: "HTML", css: "CSS", scss: "SCSS", bash: "Bash" };
const scrollers = [...document.querySelectorAll("pre[data-scroll-focus]")];

function fitFocus(pres) {
  const overflows = pres.map((pre) => pre.scrollWidth > pre.clientWidth || pre.scrollHeight > pre.clientHeight);
  pres.forEach((pre, i) => {
    if (overflows[i]) {
      const language = pre.querySelector("code")?.className.match(/\blanguage-([\w-]+)/)?.[1];
      if (pre.getAttribute("tabindex") !== "0") pre.setAttribute("tabindex", "0");
      if (pre.getAttribute("role") !== "figure") pre.setAttribute("role", "figure");
      const label = `${LANGUAGES[language] ?? "Example"} code`;
      if (pre.getAttribute("aria-label") !== label) pre.setAttribute("aria-label", label);
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

// --- Example forms -------------------------------------------------------------------------------
// Every form on the site is an example, inside <main>: none submits. Each has method="dialog"
// (criterion 9), whose submit does nothing outside a <dialog>, so without JavaScript none submits
// either, and nothing typed reaches the URL. Its code sample keeps a plain <form>.

document.addEventListener("submit", (event) => {
  if (event.target instanceof Element && event.target.closest("main")) event.preventDefault();
});

// --- Modal helper (ModalContext.jsx, one per dialog) ---------------------------------------------
// The Remix site's ModalContext was one flag for the whole site, which both of its dialogs (Modal's
// demo and the color modal) bound to, so on one page opening either would open both. Here each
// dialog has a helper of its own with its own state, and createModal() returns the dialog's helper
// when it already has one (its options are the first call's), so two modules that bind the same
// dialog share it. <html>'s modal classes and --femto-scrollbar-width are the page's, so one dialog
// holds them at a time: opening a dialog while another is shown hides that one at once, without its
// animation, and only the dialog that holds them takes them away.
// open(): when the page scrolls vertically, sets --femto-scrollbar-width on <html> to the scrollbar's
// width (innerWidth minus <html>'s clientWidth; 0px with overlay scrollbars, as the Remix site wrote it);
// sets <html> class "modal-is-open modal-is-opening" and opens the dialog; 400 ms later the class is
// "modal-is-open". close(): "modal-is-open modal-is-closing", and 400 ms later no modal class, no
// --femto-scrollbar-width (the emptied style="" stays, as React leaves it), the dialog closed, then
// onClosed(). The Remix site's own test, body taller than the screen (isScrollbarVisible.js), missed a
// page taller than the viewport but not the screen; "the page scrolls" is what it meant, and the
// docs page is taller than any screen.
// The dialog is a true modal, shown with showModal() and closed with close() (the Remix site's
// only set the open attribute, so focus stayed under the overlay): the page behind is inert, the
// browser moves focus into the dialog and back to the opener, and its own Escape (the cancel event)
// runs the animated close instead. A click on the dialog itself (its backdrop area) closes it too,
// unless backdrop is false. While it is shown it holds the copy status region (above), the only
// place a screen reader can hear it then. femto's modal CSS styles these classes.
// Returns {dialog, open(), close(), isOpen}.

const MODAL_DURATION = 400;
const MODAL_CLASSES = ["modal-is-open", "modal-is-opening", "modal-is-closing"];
const modals = new WeakMap(); // dialog -> its helper
let holder = null; // hide() of the helper whose dialog holds <html>'s modal classes

function modalClasses(...names) {
  root.classList.remove(...MODAL_CLASSES);
  root.classList.add(...names);
}

export function createModal(dialog, { backdrop = true, onClosed } = {}) {
  if (modals.has(dialog)) return modals.get(dialog);
  let state = "closed"; // "opening", "open", "closing"
  let timer = 0;
  let styled = false; // this modal set --femto-scrollbar-width
  const isOpen = () => state === "opening" || state === "open";

  const onKeydown = (event) => {
    if (event.key !== "Escape" || !isOpen()) return;
    event.preventDefault();
    close();
  };

  // The end of a close, after its animation or at once: <html> given back, the dialog hidden.
  function hide() {
    clearTimeout(timer);
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
    document.removeEventListener("keydown", onKeydown);
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

  if (backdrop) {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) close();
    });
  }
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    close();
  });

  const helper = {
    dialog,
    open,
    close,
    get isOpen() {
      return isOpen();
    },
  };
  modals.set(dialog, helper);
  return helper;
}

// --- Modal dialogs (data-modal) ------------------------------------------------------------------
// A <dialog data-modal="<name>"> gets its helper on load, a true modal (the Remix site's demo only
// set the open attribute, so focus stayed under the overlay and Tab walked the page behind it):
// showModal() makes the page behind inert and moves focus into the dialog, and the
// close gives focus back to the opener. A click on [data-modal-open="<name>"] opens it, and a click
// on a [data-modal-close] inside it closes it; the helper adds the backdrop click and Escape (the
// dialog's cancel event), both with the animated close. The Modal section's demo is the one on the
// site.

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
