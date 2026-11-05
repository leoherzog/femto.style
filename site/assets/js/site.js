// site.js: every page (loaded from partials/head.html). docs/research/01 §2 and 03 §5.
//
// It rebuilds the oracle's page-wide behaviors. The copy links and the modal dialogs attach through
// data- attributes from Phase 3 (PLAN.md Conversion rules); the header toggle and the fixed header
// still bind to the oracle's own markup in the header partials, as Phases 1 and 2 did:
// - the body's min-height, innerHeight in px (react-div-100vh in Body.jsx);
// - the header theme toggle (PageContext.jsx, Nav.jsx);
// - the fixed header on docs pages (Header.jsx);
// - the copy links of code blocks, a[data-copy-link] (Code.jsx);
// - the submit of example forms, canceled (01 §2, last paragraph);
// - the modal dialogs, <dialog data-modal> with its openers and closers (ModalContext.jsx).
// Each does nothing when its markup is absent.
//
// It also exports what other modules build on, so no widget keeps page state of its own:
// - pageTheme(), switchTheme(), onThemeChange(fn): the page's color scheme;
// - createModal(dialog, options): one modal helper per dialog (ModalContext.jsx);
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

// Removes the attribute an empty class list or style leaves, as React does when the prop goes away.
function dropEmpty(element, name) {
  if (element.getAttribute(name) === "") element.removeAttribute(name);
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

// The header toggle (a[data-scheme-toggle] in the header nav), as Nav.jsx renders it: href is the
// current path (Remix's Link to="#"), and the label and the icon's moon class follow the scheme. The
// icon is the owner's sun or moon emoji (Decision 16), not the oracle's animated SVG.
const toggles = [...document.querySelectorAll("a[data-scheme-toggle]")];

function applyTheme() {
  const stored = storedTheme();
  // The color-scheme head script has usually set it already: an unchanged value causes no mutation.
  if (stored && root.getAttribute("data-theme") !== stored) root.setAttribute("data-theme", stored);
  else if (!stored) root.removeAttribute("data-theme");
  const theme = pageTheme();
  const dark = theme === "dark";
  for (const toggle of toggles) {
    toggle.setAttribute("aria-label", dark ? "Turn off dark mode" : "Turn on dark mode");
    toggle.querySelector(".icon-theme-toggle")?.classList.toggle("moon", dark);
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

for (const toggle of toggles) {
  toggle.setAttribute("href", location.pathname);
  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    switchTheme();
  });
}
addEventListener("storage", (event) => {
  if (event.key !== KEY && event.key !== null) return;
  unstoredChoice = null;
  applyTheme();
});
darkOs.addEventListener("change", applyTheme);
applyTheme();

// --- Body height (react-div-100vh) ---------------------------------------------------------------
// The oracle sets <body style="min-height: <innerHeight>px"> after hydration and on every resize.

const fitBody = () => {
  document.body.style.minHeight = `${innerHeight}px`;
};
fitBody();
addEventListener("resize", fitBody);

// --- Fixed header (docs pages) -------------------------------------------------------------------
// The docs header (header[data-fixed-header]) carries is-fixed-above-lg in its markup; is-fixed is
// added while scrollY > 20.

const fixedHeader = document.querySelector("header[data-fixed-header]");
if (fixedHeader) {
  const update = () => fixedHeader.classList.toggle("is-fixed", scrollY > 20);
  addEventListener("scroll", perFrame(update), { passive: true });
  update();
}

// --- Copy links (Code.jsx) -----------------------------------------------------------------------
// a[data-copy-link] (a.copy-to-clipboard, the first child of div.code or footer.code; colors.js's
// color modal writes its own the same way): a click copies the block's code text, shows the
// animated check icon with the tooltip "Copied", and 1 s later restores the clipboard icon and
// "Copy to clipboard" and blurs the link. As in Code.jsx, every click schedules its own revert, so
// after repeated clicks the first one's timer reverts (1 s after the first click) and each later one
// only blurs, or reverts a "Copied" a still later click showed. The check icon is Check.jsx's,
// isAnimated and strokeWidth 3, with the class "check", but without its path's id="check-icon": the
// docs page has that id already, in Version picker's swatch, and every link showing "Copied" would
// add one more (Decision 13). Its <style> selects the path through svg.check, the copy links' check
// alone.

const CHECK_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round" class="check"><style>
          svg.check > path {
            stroke-dasharray: 22px;
            stroke-dashoffset: 22px;
            animation: check 0.2s ease-out forwards;
          }

          @keyframes check {
            from {
              stroke-dashoffset: 22px;
            }
            to {
              stroke-dashoffset: 0;
            }
          }
        </style><path d="M5 12l5 5l10 -10"></path></svg>`;

const COPIED_FOR = 1000;
const copied = new WeakMap(); // link -> {icon, check} while it shows "Copied"

function checkIcon() {
  const template = document.createElement("template");
  template.innerHTML = CHECK_ICON;
  return template.content.firstElementChild;
}

document.addEventListener("click", (event) => {
  const link = event.target instanceof Element ? event.target.closest("a[data-copy-link]") : null;
  if (!link) return;
  event.preventDefault();
  const code = link.parentElement.querySelector("pre code");
  if (code) navigator.clipboard?.writeText(code.textContent).catch(() => {});
  if (!copied.has(link)) {
    const icon = link.querySelector("svg.clipboard");
    if (!icon) return;
    const check = checkIcon();
    icon.replaceWith(check);
    link.setAttribute("data-tooltip", "Copied");
    copied.set(link, { icon, check });
  }
  setTimeout(() => {
    const state = copied.get(link);
    if (state) {
      state.check.replaceWith(state.icon);
      link.setAttribute("data-tooltip", "Copy to clipboard");
      copied.delete(link);
    }
    link.blur();
  }, COPIED_FOR);
});

// --- Example forms -------------------------------------------------------------------------------
// Every form on the site is an example, inside <main>: none submits.

document.addEventListener("submit", (event) => {
  if (event.target instanceof Element && event.target.closest("main")) event.preventDefault();
});

// --- Modal helper (ModalContext.jsx, one per dialog) ---------------------------------------------
// The oracle's ModalContext was one flag for the whole site, which both of its dialogs (Modal's demo
// and the color modal) bound to, so on one page opening either would open both (01 §2). Here each
// dialog has a helper of its own with its own state, and createModal() returns the dialog's helper
// when it already has one (its options are the first call's), so two modules that bind the same
// dialog share it. <html>'s modal classes and --femto-scrollbar-width are the page's, so one dialog
// holds them at a time: opening a dialog while another is shown hides that one at once, without its
// animation, and only the dialog that holds them takes them away.
// open(): when the page scrolls vertically, sets --femto-scrollbar-width on <html> to the scrollbar's
// width (innerWidth minus <html>'s clientWidth; 0px with overlay scrollbars, as the oracle writes it);
// sets <html> class "modal-is-open modal-is-opening" and opens the dialog; 400 ms later the class is
// "modal-is-open". close(): "modal-is-open modal-is-closing", and 400 ms later no modal class, no
// --femto-scrollbar-width (the emptied style="" stays, as React leaves it), the dialog closed, then
// onClosed(). The oracle's own test, body taller than the screen (isScrollbarVisible.js), missed a
// page taller than the viewport but not the screen; "the page scrolls" is what it meant, and the
// docs page is taller than any screen.
// Escape closes it while it is open, and so does a click on the dialog itself (its backdrop area)
// unless backdrop is false. By default the dialog gets the open attribute, as the oracle's did
// (focus stays where it was); with modal: true it is shown with showModal() and closed with close(),
// so the browser moves focus into it and back, and its own Escape (the cancel event) runs the
// animated close instead. femto's modal CSS styles these classes.
// Returns {dialog, open(), close(), isOpen}.

const MODAL_DURATION = 400;
const MODAL_CLASSES = ["modal-is-open", "modal-is-opening", "modal-is-closing"];
const modals = new WeakMap(); // dialog -> its helper
let holder = null; // hide() of the helper whose dialog holds <html>'s modal classes

function modalClasses(...names) {
  root.classList.remove(...MODAL_CLASSES);
  root.classList.add(...names);
  dropEmpty(root, "class");
}

export function createModal(dialog, { modal = false, backdrop = true, onClosed } = {}) {
  if (modals.has(dialog)) return modals.get(dialog);
  let state = "closed"; // "opening", "open", "closing"
  let timer = 0;
  let styled = false; // this modal set --femto-scrollbar-width
  const isOpen = () => state === "opening" || state === "open";

  const onKeydown = (event) => {
    if (event.key !== "Escape" || !isOpen()) return;
    if (modal) event.preventDefault();
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
    if (modal) dialog.close();
    else dialog.removeAttribute("open");
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
    if (modal) {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
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
  if (modal) {
    dialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      close();
    });
  }

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
// A <dialog data-modal="<name>"> gets its helper on load, with the defaults (the open attribute, as
// the oracle's demo had). A click on [data-modal-open="<name>"] opens it, and a click on a
// [data-modal-close] inside it closes it; the helper adds the backdrop click and Escape. The Modal
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
