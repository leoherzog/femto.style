// examples.js: the examples page (/examples, site/examples.html).
//
// Each example is markup that only femto styles. Its frame, div[data-example], holds a declarative
// shadow root whose only element is the example's own shadow host, a <div part="example"> whose
// shadow root loads femto's stylesheet and holds the example (femto README, "Shadow roots"). The
// inner host sits in a shadow tree, so the page's rules cannot match it: the site's [data-theme]
// blocks, which set some of femto's tokens, never reach the example (examples.css reaches it only
// through ::part(), for its color-scheme). The roots are declarative, so the examples render without
// this script. It adds what a page holding the example would add:
// - the color scheme: the inner host's data-theme follows <html>'s (site.js, Decision 14), as femto
//   reads data-theme on a shadow host, so an example follows the page's light or dark choice;
// - forms that do not submit and links that go nowhere: site.js cancels only the page's own, and a
//   submit event stops at its shadow root;
// - dialogs: a click on an element whose aria-controls names a <dialog> opens it with showModal(),
//   and a click on its rel="prev" or .close button, on a button in its footer, or on the dialog
//   itself (its backdrop) closes it. Escape closes it with no script. However it closes, focus goes
//   back to the opener: Chrome and Firefox put it there themselves, but in Safari a click does not
//   focus a button, so the dialog would give focus back to <body>. The footer's buttons are
//   type="button", since femto makes every button[type=submit] full width.
// It does nothing on a page without div[data-example].

import { onThemeChange } from "./site.js";

const root = document.documentElement;
const hosts = [...document.querySelectorAll("div[data-example]")]
  .map((frame) => frame.shadowRoot?.firstElementChild)
  .filter((host) => host?.shadowRoot);

// --- Color scheme --------------------------------------------------------------------------------

function followScheme() {
  const scheme = root.getAttribute("data-theme");
  for (const host of hosts) {
    if (!scheme) host.removeAttribute("data-theme");
    else if (host.getAttribute("data-theme") !== scheme) host.setAttribute("data-theme", scheme);
  }
}

if (hosts.length) {
  followScheme();
  onThemeChange(followScheme);
}

// --- Forms, links and dialogs --------------------------------------------------------------------

for (const host of hosts) {
  const shadow = host.shadowRoot;
  shadow.addEventListener("submit", (event) => {
    if (event.target instanceof HTMLFormElement && event.target.method !== "dialog") event.preventDefault();
  });
  shadow.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;
    if (target.closest("a[href]")) {
      event.preventDefault();
      return;
    }
    const opener = target.closest("[aria-controls]");
    const dialog = opener ? shadow.getElementById(opener.getAttribute("aria-controls")) : null;
    if (dialog instanceof HTMLDialogElement) {
      if (!dialog.open) {
        dialog.showModal();
        dialog.addEventListener("close", () => {
          if (shadow.activeElement !== opener) opener.focus();
        }, { once: true });
      }
      return;
    }
    const open = target.closest("dialog[open]");
    if (open && (target === open || target.closest("[rel=prev], .close, footer button"))) open.close();
  });
}
