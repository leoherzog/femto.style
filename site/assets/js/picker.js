// picker.js: the version picker, /docs/version-picker and its 19 color routes (loaded from docs.html).
// docs/research/01 §2 (Version picker) and 03 §5.
//
// Phase 1 rebuilds the oracle's VersionPickerContext.jsx, VersionPickerCustomization.jsx,
// VersionPickerUsage.jsx and ThemePreview.jsx on the oracle's own markup, adding no attribute:
// - The configuration select (name=configuration) and the Conditional Styling switch
//   (name=conditional) regenerate the description under each of them and the four code samples: the
//   theme example's footer link, Usage from CDN, Usage with Sass and the starter HTML template. The
//   samples keep the spans build.mjs writes (step 4): the link samples change only the text of the
//   attr-value that names the file, the template also gains or loses the tokens of class="pico", and
//   the Sass sample is written as Prism's scss tokens, flattened as the build flattens them.
// - A theme swatch (article.color-picker > header a) switches the color in place, as the oracle's
//   client-side route change did: it loads the color's custom-themes stylesheet, then renders the
//   color into the page (every swatch's aria-label, the check icon and aria-current on the current
//   swatch, the example's heading and sentence, the code samples, the links to the page itself,
//   aria-current="page" on the header's and footer's links to the color's path, which Link.jsx set
//   for the route and build.mjs writes per route, and the head's title, description, canonical and
//   og:url) and pushes /docs/version-picker/<color> (/docs/version-picker for azure) without
//   scrolling. The configuration is kept, as VersionPickerProvider's state outlived the picker's
//   child routes. The theme example's form is reset (login and password empty, the Privacy switch
//   on), as the oracle's remount of ThemePreview reset it. Back and forward render the color of the
//   entry's path. If a stylesheet fails to load, the browser navigates to the color's own page.
//   One difference from the oracle, on purpose: focus stays on the clicked swatch. The oracle's
//   remount removed the focused swatch, which dropped focus to <body> (Tab then started over at the
//   first swatch); keeping it is the fix an in-place swap gives naturally (PLAN.md, oracle-bug; the
//   picker-swatch-focus behavior check).
// - The other links to a picker route render in place too, as Remix's Link did, so they keep the
//   configuration: the side menu's and the footer's "Version picker" and the table of contents'
//   first link ("Theme", whose href is the page itself). A link to another color swaps as a swatch
//   does, then scrolls to the top (that Link had no preventScrollReset). A link to the page itself
//   only scrolls to the top, and pushes the path when the URL has a hash, as Remix's navigate did
//   (replace when the URL is unchanged, push otherwise). Links with a hash are the browser's own
//   fragment navigation, and every link off the picker's routes is a plain page load (the
//   picker-links behavior check).
// - The example form's Privacy Policy link goes nowhere (Link to="#" with a preventDefault onClick);
//   site.js cancels the form's submit.
// The links to the page itself are the oracle's Link to="#": the header theme toggle, the menu's
// Close link, the copy links, the Privacy Policy link and the table of contents ("#anchor").
// - Every change of the path also animates the header logo for 1 s (class "animated" on its svg), as
//   HeaderContext.jsx did after each client-side route change: 01 §2 drops that animation because a
//   static site has no client-side route changes, and the picker's in-place swaps are the exception.
// Dropped, as 01 §2 says: Remix's navigation feedback (aria-busy="true" on the swatch being loaded).
// Two generated descriptions linked Decision 5 routes (/docs/classless, /docs/conditional); those
// links point at /docs, as the converted pages' links to dropped routes do.
// It does nothing on a page without the picker. The pure helpers are exported for tests.

// --- The configurations (VersionPickerContext.jsx) -----------------------------------------------

export const BASES = [
  {
    file: "",
    description: "The default version of Pico CSS, with all components and classes.",
    sass: [],
  },
  {
    file: "classless.",
    description: 'The <a data-discover="true" href="/docs">class-less version</a> for HTML purists with centered viewports.',
    sass: [["$enable-semantic-container", "true"], ["$enable-classes", "false"]],
  },
  {
    file: "fluid.classless.",
    description: 'The <a data-discover="true" href="/docs">class-less version</a> for HTML purists with a fluid viewport.',
    sass: [["$enable-semantic-container", "true"], ["$enable-viewport", "false"], ["$enable-classes", "false"]],
  },
];

export const CONDITIONAL = [
  {
    file: "",
    description: "The default version applies Pico styles to every HTML element.",
    sass: [],
  },
  {
    file: "conditional.",
    description: 'This version restricts Pico styling to HTML elements within <code>.pico</code> containers only. <a data-discover="true" href="/docs">See&nbsp;here</a>.',
    sass: [["$parent-selector", '".pico"']],
  },
];

// The file name the samples link, e.g. pico.classless.conditional.jade.min.css.
export function fileName(base, conditional, color) {
  return `pico.${BASES[base].file}${CONDITIONAL[conditional].file}${color === "azure" ? "" : `${color}.`}min.css`;
}

// The Sass properties in the oracle's order: the theme color, then the base's, then the conditional's.
export function sassProperties(base, conditional, color) {
  return [...(color === "azure" ? [] : [["$theme-color", `"${color}"`]]), ...BASES[base].sass, ...CONDITIONAL[conditional].sass];
}

// --- The highlighted samples (build.mjs, step 4) -------------------------------------------------

const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const span = (cls, text) => `<span class="${cls}">${escape(text)}</span>`;
const FILE = /css\/pico\.(?:[a-z]+\.)*min\.css/g;

// A link sample: the load-time spans with the file name changed.
export function linkHtml(initial, file) {
  return initial.replace(FILE, `css/${file}`);
}

// The tokens of class="pico" after lang="en" on the template's <html>.
const LANG = /<span class="token tag attr-value">en<\/span><span class="token tag attr-value punctuation">(?:"|&quot;)<\/span>/;
const CLASS_PICO = span("token tag", " ") + span("token tag attr-name", "class") + span("token tag attr-value punctuation attr-equals", "=")
  + span("token tag attr-value punctuation", '"') + span("token tag attr-value", "pico") + span("token tag attr-value punctuation", '"');

// The starter template: the load-time spans (always without class="pico") with the file name changed,
// and class="pico" when conditional.
export function templateHtml(initial, file, conditional) {
  const html = linkHtml(initial, file);
  return conditional ? html.replace(LANG, (tag) => tag + CLASS_PICO) : html;
}

// The Sass sample (VersionPickerUsage.jsx's getSassCode) as Prism's scss tokens, flattened and split at
// newlines as build.mjs does: plain text runs are class-less spans.
export function sassHtml(properties) {
  const use = span("token keyword", "@use") + span("", " ") + span("token string", '"pico"');
  if (!properties.length) return use + span("token punctuation", ";");
  const lines = properties.map(([name, value]) => span("", "\n") + span("", "  ") + span("token property variable", name)
    + span("token punctuation", ":") + span("", " ") + span(/^(true|false)$/.test(value) ? "token boolean" : "token string", value));
  return use + span("", " ") + span("token module-modifier keyword", "with") + span("", " ") + span("token punctuation", "(")
    + lines.join(span("token punctuation", ",")) + span("", "\n") + span("", "") + span("token punctuation", ")") + span("token punctuation", ";");
}

// --- The color (ThemePreview.jsx, the color routes' meta) ----------------------------------------

const PICKER = "/docs/version-picker";
export const pathOf = (color) => (color === "azure" ? PICKER : `${PICKER}/${color}`);
// The color a path names (/docs/version-picker is azure), or null for any other path; not checked
// against the swatches.
export function colorOfPath(path) {
  const match = path.match(/^\/docs\/version-picker(?:\/([a-z]+))?\/?$/);
  return match ? match[1] ?? "azure" : null;
}
const named = (color) => color.charAt(0).toUpperCase() + color.slice(1);
// ThemePreview.jsx's colorWithPrefix: "an azure", "a jade".
const withArticle = (color) => `${/^[aeiou]/.test(color) ? "an" : "a"} ${color}`;
// The version picker's own meta, and utils/themeGenerator.js's for a color route.
const TITLE = (color) => (color === "azure" ? "Version picker • femto" : `Minimal ${named(color)} theme • femto`);
const DESCRIPTION = (color) => (color === "azure" ? "Easily select the ideal Pico CSS version variant to match your project's needs."
  : `CSS code to customize femto's primary color to ${named(color)} with CSS variables.`);

// --- The page ------------------------------------------------------------------------------------

function setAttr(element, name, value) {
  if (element && element.getAttribute(name) !== value) element.setAttribute(name, value);
}

function picker(article) {
  const header = article.querySelector(":scope > header");
  const swatches = [...header.querySelectorAll(":scope > a[class^='femto-background-']")];
  const colorOf = (swatch) => swatch.className.slice("femto-background-".length);
  const colors = swatches.map(colorOf);
  const current = swatches.find((swatch) => swatch.getAttribute("aria-current") === "page");
  const check = current?.querySelector(":scope > svg")?.cloneNode(true);
  const heading = article.querySelector(":scope > hgroup > h2");
  const sentence = article.querySelector(":scope > hgroup > p");
  const form = article.querySelector(":scope > form");
  const select = document.querySelector("#content select[name=configuration]");
  const switcher = document.querySelector("#content input[name=conditional]");
  const baseNote = select?.nextElementSibling;
  const conditionalNote = switcher?.closest("fieldset")?.nextElementSibling;
  // The samples, found by their sections' heading anchors (VersionPickerUsage.jsx).
  const usage = (id) => document.getElementById(id)?.closest("section")?.querySelector("pre > code");
  const codes = {
    footer: article.querySelector(":scope > footer pre > code"),
    cdn: usage("usage-from-cdn"),
    sass: usage("usage-with-sass"),
    template: usage("starter-html-template"),
  };
  if (!current || !check || !heading || !sentence || !form || !select || !switcher || baseNote?.localName !== "small"
    || conditionalNote?.localName !== "small" || Object.values(codes).some((code) => !code)) return;

  const initial = Object.fromEntries(Object.entries(codes).map(([name, code]) => [name, code.innerHTML]));
  const rendered = { ...initial, baseNote: baseNote.innerHTML, conditionalNote: conditionalNote.innerHTML };
  const write = (name, element, html) => {
    if (rendered[name] === html) return;
    element.innerHTML = html;
    rendered[name] = html;
  };

  let color = colorOf(current);
  // A reload or a return to the page can restore the controls' state: start from what they show.
  let base = BASES[select.value] ? Number(select.value) : 0;
  let conditional = switcher.checked ? 1 : 0;

  function render() {
    const file = fileName(base, conditional, color);
    write("footer", codes.footer, linkHtml(initial.footer, file));
    write("cdn", codes.cdn, linkHtml(initial.cdn, file));
    write("sass", codes.sass, sassHtml(sassProperties(base, conditional, color)));
    write("template", codes.template, templateHtml(initial.template, file, conditional));
    write("baseNote", baseNote, BASES[base].description);
    write("conditionalNote", conditionalNote, CONDITIONAL[conditional].description);
  }

  select.addEventListener("change", () => {
    base = BASES[select.value] ? Number(select.value) : 0;
    render();
  });
  switcher.addEventListener("change", () => {
    conditional = switcher.checked ? 1 : 0;
    render();
  });
  render();

  // The links to the page itself (Remix's Link to="#", and the table of contents' "#anchor" links).
  const selfLinks = () => [
    ...document.querySelectorAll("body > header nav ul.icons a[aria-label$=' dark mode']"),
    ...document.querySelectorAll("#documentation-menu > header a[aria-label=Close]"),
    ...document.querySelectorAll("#table-of-contents a"),
    ...document.querySelectorAll("#content a.copy-to-clipboard"),
    ...article.querySelectorAll(":scope > form a"),
  ];

  function show(next) {
    const from = pathOf(color), to = pathOf(next);
    color = next;
    // HeaderContext.jsx: each path change sets the logo's "animated" class, and its own 1 s timer
    // clears it.
    const logo = document.querySelector("body > header a[aria-label='femto homepage'] > svg.femto-logo");
    if (logo && from !== to) {
      logo.classList.add("animated");
      setTimeout(() => logo.classList.remove("animated"), 1000);
    }
    for (const swatch of swatches) {
      setAttr(swatch, "aria-label", named(next));
      if (colorOf(swatch) === next) {
        setAttr(swatch, "aria-current", "page");
        if (!swatch.firstElementChild) swatch.append(check.cloneNode(true));
      } else {
        swatch.removeAttribute("aria-current");
        swatch.replaceChildren();
      }
    }
    heading.textContent = named(next);
    sentence.textContent = `Form example with ${withArticle(next)} theme.`;
    form.reset(); // the oracle remounted the example
    render();
    const self = selfLinks();
    // The header's and footer's links (Link.jsx: aria-current="page" when the link names the route).
    // The links to the page itself (the header's theme toggle) never do.
    for (const link of document.querySelectorAll("body > header a[href], body > footer a[href]")) {
      if (self.includes(link)) continue;
      const href = link.getAttribute("href");
      if (href === to) setAttr(link, "aria-current", "page");
      else if (href === from) link.removeAttribute("aria-current");
    }
    for (const link of self) {
      const href = link.getAttribute("href");
      if (href === from || href?.startsWith(`${from}#`)) link.setAttribute("href", to + href.slice(from.length));
    }
    document.title = TITLE(next);
    setAttr(document.querySelector("meta[name=description]"), "content", DESCRIPTION(next));
    for (const [selector, name] of [["link[rel=canonical]", "href"], ["meta[property='og:url']", "content"]]) {
      const element = document.querySelector(selector);
      if (element) setAttr(element, name, new URL(to, element.getAttribute(name)).href);
    }
  }

  // The theme stylesheet: custom-themes/<color>.css after color-picker.css, none for azure.
  const pickerSheet = document.querySelector("link[rel=stylesheet][href$='/color-picker.css']");
  const themes = `${pickerSheet?.getAttribute("href").replace(/color-picker\.css$/, "")}custom-themes/`;
  let sheet = document.querySelector("link[rel=stylesheet][href*='/custom-themes/']");
  let swaps = 0;
  let target = color; // the color the newest swap renders

  // Loads the color's stylesheet, then swaps it in and renders the color in the same task, as Remix
  // waited for a route's stylesheets before rendering it, and scrolls to the top if `top` (a link
  // without preventScrollReset). The newest swap wins.
  function swap(next, push, top = false) {
    const ticket = ++swaps;
    target = next;
    const href = next === "azure" ? null : `${themes}${next}.css`;
    let link = null;
    let loaded = Promise.resolve();
    if (href && sheet?.getAttribute("href") !== href) {
      link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      loaded = new Promise((resolve, reject) => {
        link.addEventListener("load", resolve, { once: true });
        link.addEventListener("error", reject, { once: true });
      });
      (sheet ?? pickerSheet).after(link);
    }
    loaded.then(() => {
      if (ticket !== swaps) {
        link?.remove();
        return;
      }
      if (link || !href) {
        sheet?.remove();
        sheet = link;
      }
      if (next !== color) show(next);
      if (push && location.pathname !== pathOf(next)) history.pushState(history.state, "", pathOf(next));
      if (top) scrollTo(0, 0); // as Remix's ScrollRestoration did, so the page's CSS scroll-behavior applies
    }, () => {
      link?.remove();
      if (ticket !== swaps) return;
      if (push) location.assign(pathOf(next));
      else location.reload();
    });
  }

  // The form's Privacy Policy link is Link to="#" with a preventDefault onClick: it goes nowhere.
  for (const link of article.querySelectorAll(":scope > form a")) link.addEventListener("click", (event) => event.preventDefault());

  const plainClick = (event) => !event.defaultPrevented && event.button === 0
    && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

  header.addEventListener("click", (event) => {
    const swatch = event.target instanceof Element ? event.target.closest("a") : null;
    if (!swatch || !swatches.includes(swatch) || !plainClick(event)) return;
    event.preventDefault();
    // The current color's swatch does nothing (Remix replaced the history entry with itself).
    if (colorOf(swatch) !== target) swap(colorOf(swatch), true);
  });

  // Every other link to a picker route (header comment). Links whose own handlers cancel the click
  // (the copy links, the theme toggle, the menu's Close link, the Privacy Policy link) are left alone.
  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
    if (!link || swatches.includes(link) || !plainClick(event) || link.target || link.hasAttribute("download")) return;
    const url = new URL(link.href);
    if (url.origin !== location.origin || url.search || url.hash) return;
    const next = colorOfPath(url.pathname);
    if (!next || !colors.includes(next)) return;
    event.preventDefault();
    if (next !== target) {
      swap(next, true, true);
    } else {
      if (location.pathname + location.search + location.hash !== pathOf(next)) history.pushState(history.state, "", pathOf(next));
      scrollTo(0, 0);
    }
  });

  addEventListener("popstate", () => {
    const next = colorOfPath(location.pathname);
    if (next && colors.includes(next) && next !== target) swap(next, false);
  });
}

const article = globalThis.document?.querySelector("#content article.color-picker[aria-label='Custom theme example']");
if (article?.querySelector(":scope > header")) picker(article);
