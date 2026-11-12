// examples.js: the examples page (/examples, site/examples.html).
//
// Each example is markup that only femto styles. Its frame, div[data-example], holds a declarative
// shadow root whose only element is the example's own shadow host, a <div part="example"> whose
// shadow root loads femto's stylesheet and holds the example (femto README, "Shadow roots"). The
// inner host sits in a shadow tree, so the page's rules cannot match it: the site's [data-theme]
// blocks, which set some of femto's tokens, never reach the example (examples.css reaches it only
// through ::part(), for its color-scheme). The roots are declarative, so the examples render without
// this script. Its markup, escaped, is the code sample in the <details> under it, which site.js's
// copy button copies. The script adds what a page holding the example would add:
// - the color scheme: the inner host's data-theme follows <html>'s (site.js, Decision 14), as femto
//   reads data-theme on a shadow host, so an example follows the page's light or dark choice. So
//   does every shadow host inside an example (the All theme colors example's 20), whose own root
//   loads femto and so gives the host a background in its own scheme. In print they all take
//   femto's print scheme, light;
// - links that go nowhere: a click on one is canceled, read at its first target (composedPath),
//   since a link may sit in a shadow root of the example's own, as the All theme colors example's
//   do. (Each mockup form has method="dialog", whose submit does nothing outside a <dialog>
//   (criterion 9); its HTML sample keeps a plain <form>.)
// - dialogs: each opener and closer also has command and commandfor, which open and close the dialog
//   with no script in a browser that has them, in the Copy as page output too. Only where the
//   browser lacks them (no commandForElement on HTMLButtonElement.prototype), a click on an element
//   whose aria-controls names a <dialog> opens it with showModal(), and a click on its rel="prev" or
//   .close button or on a button in its footer closes it. Everywhere, a click on the dialog itself
//   (its backdrop: femto's dialog is the full-viewport overlay) closes it when both the press and the
//   release were on it, so a text selection dragged out of the card leaves it open. Escape closes
//   it with no script. However it closes, focus goes back to the opener: Chrome and Firefox put it
//   there themselves, but in Safari a click does not focus a button, so the dialog would give focus
//   back to <body>. The footer's buttons are type="button", since femto makes every
//   button[type=submit] full width.
// And two controls of the page's own, which examples.css hides without JavaScript:
// - Copy as page, button[data-copy-page] in each example's header: copies the example's code sample
//   in femto's starter template (the page's template[data-starter-page], as femto README's Quick
//   start and the docs' Quick start write it), with the example's name for its title, the sample in
//   place of its <h1>, indented as the <h1> is (a <pre>'s later lines keep their own), and the
//   chosen theme's link after femto's, written as femto's. The page's own femto paths (/vendor/femto/,
//   in the All theme colors example) become the folder femto's link names on jsDelivr. For 1 s
//   after the latest copy the button's femto tooltip (data-tooltip, which it has only then) says
//   "Copied", or "Copy failed" when the clipboard refuses the text, as a code block's copy button
//   does; its label keeps its text, and site.js's status region says it.
// - The theme color, the select in p[data-examples-theme]: the chosen theme's stylesheet
//   (css/themes/<color>.css) is linked right after femto's in every inner shadow root, and azure,
//   femto's own color, removes it. A new link replaces the old one once it has loaded, so the
//   examples never show azure between two colors. A link that fails to load goes, and the examples
//   keep the color they show, which the select and Copy as page go back to. The page itself and the
//   All theme colors example's own roots keep their colors. No URL parameter: ?theme= belongs to the
//   docs page (Decision 8).
// It does nothing on a page without div[data-example].

import { announceCopy, escapeText, onThemeChange, setAttr } from "./site.js";

const root = document.documentElement;
const hosts = [...document.querySelectorAll("div[data-example]")]
  .map((frame) => frame.shadowRoot?.firstElementChild)
  .filter((host) => host?.shadowRoot);
// The shadow hosts inside the examples (the All theme colors example's), each with a root of its own.
const innerHosts = hosts.flatMap((host) => [...host.shadowRoot.querySelectorAll("*")].filter((el) => el.shadowRoot));

// --- Color scheme --------------------------------------------------------------------------------

// While the page prints, the hosts have no data-theme, so the examples print in femto's print
// scheme, light, as the page does (common.css, examples.css).
let printing = false;

function followScheme() {
  const scheme = printing ? null : root.getAttribute("data-theme");
  for (const host of [...hosts, ...innerHosts]) setAttr(host, "data-theme", scheme || null);
}

if (hosts.length) {
  followScheme();
  onThemeChange(followScheme);
  const printMedia = matchMedia("print");
  const setPrinting = (on) => {
    printing = on;
    followScheme();
  };
  addEventListener("beforeprint", () => setPrinting(true));
  addEventListener("afterprint", () => setPrinting(printMedia.matches));
  printMedia.addEventListener("change", () => setPrinting(printMedia.matches));
}

// --- Forms, links and dialogs --------------------------------------------------------------------

const NATIVE_COMMANDS = "commandForElement" in HTMLButtonElement.prototype;

for (const host of hosts) {
  const shadow = host.shadowRoot;
  // A click's target is the nearest element holding both its press and its release, so each end is
  // checked on its own (site.js's createModal() does the same).
  let pressed = null;
  let released = null;
  shadow.addEventListener("pointerdown", (event) => {
    pressed = event.composedPath()[0];
  });
  shadow.addEventListener("pointerup", (event) => {
    released = event.composedPath()[0];
  });
  shadow.addEventListener("click", (event) => {
    const first = event.composedPath()[0];
    const target = first instanceof Element ? first : null;
    if (!target) return;
    if (target.closest("a[href]")) {
      event.preventDefault();
      return;
    }
    const opener = target.closest("[aria-controls]");
    const dialog = opener ? shadow.getElementById(opener.getAttribute("aria-controls")) : null;
    if (dialog instanceof HTMLDialogElement) {
      if (!dialog.open) {
        // This click runs before the browser's own command, so the dialog is still closed here.
        if (!NATIVE_COMMANDS) dialog.showModal();
        dialog.addEventListener("close", () => {
          if (shadow.activeElement !== opener) opener.focus();
        }, { once: true });
      }
      return;
    }
    const open = target.closest("dialog[open]");
    if (!open) return;
    const onBackdrop = target === open && pressed === open && released === open;
    if (onBackdrop || (!NATIVE_COMMANDS && target.closest("[rel=prev], .close, footer button"))) open.close();
  });
}

// --- Theme color ---------------------------------------------------------------------------------

const THEMES = "/vendor/femto/css/themes/";
const themeSelect = hosts.length ? document.querySelector("p[data-examples-theme] select") : null;
let theme = "azure";

const themeLinks = (shadow) => [...shadow.children].filter((el) => el.localName === "link" && el.getAttribute("href")?.startsWith(THEMES));
const colorOf = (link) => link.getAttribute("href").slice(THEMES.length, -".css".length);

function showTheme(color) {
  theme = color;
  for (const host of hosts) {
    const shadow = host.shadowRoot;
    const old = themeLinks(shadow);
    if (color === "azure") {
      for (const link of old) link.remove();
      continue;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${THEMES}${color}.css`;
    link.addEventListener("load", () => {
      for (const done of old) done.remove();
    }, { once: true });
    // A file that fails goes, and the old link keeps its color. If the color was the latest choice,
    // the theme goes back to the newest one the example still has, azure with none.
    link.addEventListener("error", () => {
      link.remove();
      if (theme !== color) return;
      const kept = themeLinks(shadow).at(-1);
      theme = kept ? colorOf(kept) : "azure";
      themeSelect.value = theme;
    }, { once: true });
    (old.at(-1) ?? shadow.firstElementChild).after(link);
  }
}

// The select has autocomplete="off", so a reload starts at azure: no browser restores it.
themeSelect?.addEventListener("change", () => showTheme(themeSelect.value));

// --- Copy as page --------------------------------------------------------------------------------

// femto's starter template: the text of the page's template[data-starter-page], escaped there.
const starter = hosts.length ? document.querySelector("template[data-starter-page]")?.content.textContent ?? "" : "";
const COPIED_FOR = 1000;

// Each line indented, but a <pre>'s lines after its first, whose spaces are its content.
function indent(markup, spaces) {
  let pre = false;
  return markup.split("\n").map((line) => {
    const out = pre || !line ? line : spaces + line;
    const opens = /<pre[\s>]/.test(line);
    const closes = line.includes("</pre>");
    if (opens && !closes) pre = true;
    else if (closes) pre = false;
    return out;
  }).join("\n");
}

// An example's page: the template with the example's name for its title, the theme's link (none for
// azure) as a copy of femto's line, and the markup in place of the <h1>, its /vendor/femto/ paths
// made the folder femto's link names.
function pageOf(template, name, markup, color) {
  const femto = /^.*\bhref="([^"]*\/)dist\/femto\.min\.css".*$/m.exec(template);
  if (!femto) return markup;
  const [line, folder] = femto;
  const themeLine = color === "azure" ? "" : `\n${line.replace("dist/femto.min.css", `css/themes/${color}.css`)}`;
  return template
    .replace(line, () => line + themeLine)
    .replace(/<title>[^<]*<\/title>/, () => `<title>${escapeText(name)}</title>`)
    .replace(/^( *)<h1>Hello, world!<\/h1>$/m, (h1, spaces) => indent(markup.replaceAll('"/vendor/femto/', `"${folder}`), spaces));
}

const copyButtons = starter ? [...document.querySelectorAll("section.example > header > button[data-copy-page]")] : [];
for (const button of copyButtons) {
  const section = button.closest("section");
  // femto's tooltip draws data-tooltip as the button's ::before text, which a name from contents
  // would read first ("Copied Copy as page"): the label names the button throughout.
  setAttr(button, "aria-label", button.textContent);
  let timer = 0;
  button.addEventListener("click", async () => {
    const name = section.querySelector(":scope > header h2")?.textContent.trim() ?? "";
    const code = section.querySelector(":scope > details pre code");
    if (!code) return;
    // The write starts in the click itself; with no navigator.clipboard (an insecure origin) it
    // throws, and a refused write rejects.
    let message = "Copied";
    try {
      await navigator.clipboard.writeText(pageOf(starter, name, code.textContent, theme));
    } catch {
      message = "Copy failed";
    }
    setAttr(button, "data-tooltip", message);
    announceCopy(message);
    clearTimeout(timer);
    timer = setTimeout(() => setAttr(button, "data-tooltip", null), COPIED_FOR);
  });
}
