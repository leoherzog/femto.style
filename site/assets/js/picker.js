// picker.js: the version picker, the docs page's #version-picker section (loaded from docs.html).
// docs/research/01 §2 (Version picker), 02 §5 and 03 §5; PLAN.md Decision 8.
//
// It rebuilds the oracle's VersionPickerContext.jsx, VersionPickerCustomization.jsx,
// VersionPickerUsage.jsx and ThemePreview.jsx on the oracle's markup, found by its data- hooks
// (PLAN.md Conversion rules): the theme example, article[data-version-picker]; the Configuration
// subsection, section[data-picker-configuration]; and the three usage subsections,
// section[data-picker-usage=cdn|sass|template]:
// - The configuration select (name=configuration) and the Conditional Styling switch
//   (name=conditional) regenerate the description under each of them and the four code samples: the
//   theme example's footer link, Usage from CDN, Usage with Sass and the starter HTML template. The
//   samples keep the spans build.mjs writes (step 4): the link samples change only the text of the
//   attr-value that names the file, the template also gains or loses the tokens of class="pico", and
//   the Sass sample is written as Prism's scss tokens, flattened as the build flattens them.
// - The theme color is the URL's ?theme=<color> (Decision 8). The ?theme= head script has already
//   written that color's stylesheet <link> with document.write, for a color the swatches name;
//   anything else is ignored, so the page is azure, the default. On load, the section renders the
//   URL's color as /docs/version-picker/<color> showed it: every swatch's aria-label, the check icon
//   and aria-current on the current swatch, the example's heading and sentence, the code samples, and
//   the section's links to the page itself (the copy links and the Privacy Policy link, the oracle's
//   Link to="#"), which carry the color's page, /docs?theme=<color> (/docs for azure).
// - A swatch (article.color-picker > header a, href /docs?theme=<color>#version-picker, or
//   /docs#version-picker for azure, which also works without JavaScript) switches the color in place:
//   it loads the color's femto theme stylesheet, then swaps it for the old one and renders the color
//   in the same task, and replaceStates ?theme= (none for azure), keeping the path, the rest of the
//   query and the #hash. No reload and no new history entry. The configuration is kept, as
//   VersionPickerProvider's state outlived the picker's child routes, and the example's form is reset
//   (login and password empty, the Privacy switch on), as the oracle's remount of ThemePreview reset
//   it. If the stylesheet fails to load, the browser loads the swatch's URL. Focus stays on the
//   clicked swatch (the oracle's remount dropped it to <body>: PLAN.md, oracle-bug). Back and forward
//   to an entry of this document with another ?theme= render that entry's color.
// - Every change of color also animates the header logo for 1 s (class "animated" on its svg), as
//   HeaderContext.jsx did after each client-side route change.
// - The page's title, description, canonical and og:url stay the docs page's (Decision 9); docs.js
//   sets document.title for the section being read.
// - The example form's Privacy Policy link goes nowhere (Link to="#" with a preventDefault onClick);
//   site.js cancels the form's submit.
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

// --- The color (ThemePreview.jsx, the color routes) ----------------------------------------------

const SECTION = "version-picker";
// The docs page in a color, with ?theme= unless azure: what the section's links to the page itself
// (Link to="#") carry. urlOf is its picker section, what a swatch links.
export const pageOf = (color) => (color === "azure" ? "/docs" : `/docs?theme=${color}`);
export const urlOf = (color) => `${pageOf(color)}#${SECTION}`;
// The color a ?theme= query names, if it is one of `colors`; azure otherwise.
export function colorOfQuery(search, colors) {
  const theme = new URLSearchParams(search).get("theme");
  return colors.includes(theme) ? theme : "azure";
}
// The query with ?theme= set to the color, or removed for azure; the other parameters stay.
export function queryOf(search, color) {
  const params = new URLSearchParams(search);
  if (color === "azure") params.delete("theme");
  else params.set("theme", color);
  const query = params.toString();
  return query ? `?${query}` : "";
}
const named = (color) => color.charAt(0).toUpperCase() + color.slice(1);
// ThemePreview.jsx's colorWithPrefix: "an azure", "a jade".
const withArticle = (color) => `${/^[aeiou]/.test(color) ? "an" : "a"} ${color}`;

// --- The section ---------------------------------------------------------------------------------

function setAttr(element, name, value) {
  if (element.getAttribute(name) !== value) element.setAttribute(name, value);
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
  // The Configuration subsection, section[data-picker-configuration] (VersionPickerCustomization.jsx).
  const configuration = document.querySelector("[data-picker-configuration]");
  const select = configuration?.querySelector("select[name=configuration]");
  const switcher = configuration?.querySelector("input[name=conditional]");
  const baseNote = select?.nextElementSibling;
  const conditionalNote = switcher?.closest("fieldset")?.nextElementSibling;
  // The usage subsections, section[data-picker-usage=<name>] (VersionPickerUsage.jsx).
  const usages = ["cdn", "sass", "template"]
    .map((name) => [name, document.querySelector(`[data-picker-usage="${name}"]`)]);
  const codes = {
    footer: article.querySelector(":scope > footer pre > code"),
    ...Object.fromEntries(usages.map(([name, part]) => [name, part?.querySelector("pre > code")])),
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

  let color = colorOf(current); // the color the section shows: azure, as the file has it
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

  // The section's links to the page itself (Remix's Link to="#"): they carry the color's page.
  const selfLinks = [...article.querySelectorAll("a[data-copy-link]"),
    ...usages.flatMap(([, part]) => [...part.querySelectorAll("a[data-copy-link]")]), ...form.querySelectorAll("a")];

  function show(next, animate) {
    color = next;
    // HeaderContext.jsx: each route change sets the logo's "animated" class, and its own 1 s timer
    // clears it.
    const logo = document.querySelector("header a[data-site-logo] > svg.femto-logo");
    if (logo && animate) {
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
    if (heading.textContent !== named(next)) heading.textContent = named(next);
    const text = `Form example with ${withArticle(next)} theme.`;
    if (sentence.textContent !== text) sentence.textContent = text;
    if (animate) form.reset(); // the oracle remounted the example
    render();
    for (const link of selfLinks) setAttr(link, "href", pageOf(next));
  }

  // The theme stylesheet: femto's css/themes/<color>.css, after femto.colors.min.css; none for azure.
  const colorsSheet = document.querySelector("link[rel=stylesheet][href$='/femto.colors.min.css']");
  const themes = `${colorsSheet?.getAttribute("href").replace(/dist\/femto\.colors\.min\.css$/, "")}css/themes/`;
  let sheet = document.querySelector("link[rel=stylesheet][href*='/css/themes/']");
  let swaps = 0;
  let target = color; // the color the newest swap renders

  // Loads the color's stylesheet, then swaps it in and renders the color in the same task, as Remix
  // waited for a route's stylesheets before rendering it. With `toUrl` it replaces ?theme= in the
  // URL. The newest swap wins.
  function swap(next, toUrl) {
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
      (sheet ?? colorsSheet).after(link);
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
      if (next !== color) show(next, true);
      const query = queryOf(location.search, next);
      if (toUrl && query !== location.search) {
        history.replaceState(history.state, "", location.pathname + query + location.hash);
      }
    }, () => {
      link?.remove();
      if (ticket === swaps) location.assign(urlOf(next));
    });
  }

  // The form's Privacy Policy link is Link to="#" with a preventDefault onClick: it goes nowhere.
  for (const link of form.querySelectorAll("a")) link.addEventListener("click", (event) => event.preventDefault());

  header.addEventListener("click", (event) => {
    const swatch = event.target instanceof Element ? event.target.closest("a") : null;
    if (!swatch || !swatches.includes(swatch) || event.defaultPrevented || event.button !== 0
      || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    // The current color's swatch does nothing (Remix replaced the history entry with itself).
    if (colorOf(swatch) !== target) swap(colorOf(swatch), true);
  });

  // Back and forward between this document's entries: their ?theme= may differ.
  addEventListener("popstate", () => {
    const next = colorOfQuery(location.search, colors);
    if (next !== target) swap(next, false);
  });

  // The URL's color, whose stylesheet the ?theme= head script wrote: the newest swap's target from
  // the start.
  const start = colorOfQuery(location.search, colors);
  target = start;
  if (start !== color) show(start, false);
  else render();
}

// The picker is article[data-version-picker], the theme example with the swatches.
const article = globalThis.document?.querySelector("article[data-version-picker]");
if (article?.querySelector(":scope > header")) picker(article);
