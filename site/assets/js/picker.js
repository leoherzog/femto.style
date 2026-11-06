// picker.js: the Theme picker, the docs page's #theme-picker section (loaded from docs.html).
// docs/research/04 §1 (Theme picker) and 02 §5; PLAN.md Decision 8 and Open question 3.
//
// It binds to the section's data- hooks: the theme example with the 20 swatches,
// article[data-version-picker] (the hook keeps its Phase 3 name); the options,
// section[data-picker-options], one switch per file in femto's css/options/ (input[name=<option>]);
// and the three code samples, section[data-picker-usage=cdn|combine|template]:
// - cdn: the <link> tags in load order: femto, the theme (none for azure, which is built in), the
//   chosen options, then the reader's own stylesheet, styles.css;
// - combine: the same femto files in one jsDelivr combine URL, or femto's own link when it is the
//   only file (azure, no options);
// - template: femto's starter template, its femto <link> followed by the theme's and the options'.
// The samples keep the spans build.mjs writes (step 4: Prism's markup tokens, flattened and split
// at newlines): each <link> tag is written as those spans, and the template's other lines keep the
// spans the build gave them. The package and its version range (@leoherzog/femto@3) are read from
// the cdn sample as built, so the section file is their one source.
//
// - The theme color is the URL's ?theme=<color> (Decision 8). The ?theme= head script has already
//   written that color's stylesheet <link> with document.write, for a color the swatches name;
//   anything else is ignored, so the page is azure, the default. On load the section shows the
//   URL's color: aria-current="page" and the check icon on its swatch (each swatch's aria-label is
//   its own color's name), the example's heading and sentence, the code samples, and the example's
//   links to the page itself (its Privacy Policy link, which goes nowhere), which carry the color's
//   page, /docs?theme=<color> (/docs for azure).
// - A swatch (article.color-picker > header a, href /docs?theme=<color>#theme-picker, or
//   /docs#theme-picker for azure, which also works without JavaScript) switches the color in place:
//   it loads the color's femto theme stylesheet, then swaps it for the old one and shows the color
//   in the same task, and replaceStates ?theme= (none for azure), keeping the path, the rest of the
//   query and the #hash. No reload, no new history entry, and focus stays on the swatch. The
//   options and the example form keep their state. If the stylesheet fails to load, the browser
//   loads the swatch's URL. Back and forward to an entry of this document with another ?theme= show
//   that entry's color.
// - The option switches change only the samples: the page always loads responsive-spacings.css.
// - Every change of color also animates the header logo for 1 s (class "animated" on its svg).
// - The page's title, description, canonical and og:url stay the docs page's (Decision 9); docs.js
//   sets document.title for the section being read. site.js cancels the example form's submit.
// It does nothing on a page without the picker. The pure helpers are exported for tests.

// --- The files (femto's README: Themes, Options, Quick start) -------------------------------------

// femto's options, in the order their links are written.
export const OPTIONS = ["responsive-spacings", "fixed-typography", "no-transitions"];
// The reader's own stylesheet, after femto's files.
export const STYLESHEET = "styles.css";

// femto's files for a color and a set of options, in load order: femto, the theme, the options.
export function filesOf(color, options) {
  return ["dist/femto.min.css", ...(color === "azure" ? [] : [`css/themes/${color}.css`]),
    ...OPTIONS.filter((option) => options.includes(option)).map((option) => `css/options/${option}.css`)];
}

// jsDelivr's URL for one file of the package (e.g. @leoherzog/femto@3), and the combine URL for
// several, which is the one file's URL when there is only one.
export const fileUrl = (pkg, file) => `https://cdn.jsdelivr.net/npm/${pkg}/${file}`;
export function combineUrl(pkg, files) {
  return files.length === 1 ? fileUrl(pkg, files[0])
    : `https://cdn.jsdelivr.net/combine/${files.map((file) => `npm/${pkg}/${file}`).join(",")}`;
}

// The package as the cdn sample names it, from its text; null if it names none.
export function packageOf(text) {
  return /https:\/\/cdn\.jsdelivr\.net\/npm\/(@[\w.-]+\/[\w.-]+@[\w.-]+)\/dist\/femto\.min\.css/.exec(text)?.[1] ?? null;
}

// --- The highlighted samples (build.mjs, step 4) -------------------------------------------------
// Spans as the browser serializes the ones build.mjs writes: in text only &, < and > are escaped.

const escape = (text) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const span = (cls, text) => `<span class="${cls}">${escape(text)}</span>`;

// <link rel="stylesheet" href="<href>"> as Prism's markup tokens.
export function linkTag(href) {
  const attribute = (name, value) => span("token tag", " ") + span("token tag attr-name", name)
    + span("token tag attr-value punctuation attr-equals", "=") + span("token tag attr-value punctuation", '"')
    + span("token tag attr-value", value) + span("token tag attr-value punctuation", '"');
  return span("token tag punctuation", "<") + span("token tag", "link") + attribute("rel", "stylesheet")
    + attribute("href", href) + span("token tag punctuation", ">");
}

// One <link> tag per href, one per line, each line after the first indented by `indent`: a line
// break is a span of its own, then the next line's indent (an empty span without one).
export function linksHtml(hrefs, indent = "") {
  return hrefs.map(linkTag).join(span("", "\n") + span("", indent));
}

// --- The color -----------------------------------------------------------------------------------

const SECTION = "theme-picker";
// The docs page in a color, with ?theme= unless azure: what the section's links to the page itself
// carry. urlOf is its picker section, what a swatch links.
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
// "an azure", "a jade".
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
  const check = current?.querySelector(":scope > span[role=img]")?.cloneNode(true);
  const heading = article.querySelector(":scope > hgroup > h2");
  const sentence = article.querySelector(":scope > hgroup > p");
  const form = article.querySelector(":scope > form");
  // The options, section[data-picker-options]: one switch per option.
  const optionsPart = document.querySelector("[data-picker-options]");
  const switches = OPTIONS.map((option) => optionsPart?.querySelector(`input[type=checkbox][name="${option}"]`));
  // The code samples, section[data-picker-usage=<name>].
  const usages = ["cdn", "combine", "template"]
    .map((name) => [name, document.querySelector(`[data-picker-usage="${name}"]`)]);
  const codes = Object.fromEntries(usages.map(([name, part]) => [name, part?.querySelector("pre > code")]));
  const pkg = packageOf(codes.cdn?.textContent ?? "");
  if (!current || !check || !heading || !sentence || !form || switches.some((input) => !input)
    || Object.values(codes).some((code) => !code) || !pkg) return;

  // The template's lines other than its femto <link> keep the spans the build gave them.
  const femtoTag = linkTag(fileUrl(pkg, "dist/femto.min.css"));
  const template = codes.template.innerHTML;
  if (!template.includes(femtoTag)) return;
  const rendered = Object.fromEntries(Object.entries(codes).map(([name, code]) => [name, code.innerHTML]));
  const write = (name, html) => {
    if (rendered[name] === html) return;
    codes[name].innerHTML = html;
    rendered[name] = html;
  };

  let color = colorOf(current); // the color the section shows: azure, as the file has it
  // A reload or a return to the page can restore the switches: the samples follow what they show.
  const chosen = () => OPTIONS.filter((option, i) => switches[i].checked);

  function render() {
    const urls = filesOf(color, chosen()).map((file) => fileUrl(pkg, file));
    write("cdn", linksHtml([...urls, STYLESHEET]));
    write("combine", linksHtml([combineUrl(pkg, filesOf(color, chosen()))]));
    write("template", template.replace(femtoTag, () => linksHtml(urls, "    ")));
  }

  optionsPart.addEventListener("change", (event) => {
    if (switches.includes(event.target)) render();
  });

  // The example form's links to the page itself: they carry the color's page. (The code blocks' copy
  // controls were such links too until Phase 4; they are buttons now.)
  const selfLinks = [...form.querySelectorAll("a")];

  function show(next, animate) {
    color = next;
    const logo = document.querySelector("header a[data-site-logo] > svg.femto-logo");
    if (logo && animate) {
      logo.classList.add("animated");
      setTimeout(() => logo.classList.remove("animated"), 1000);
    }
    for (const swatch of swatches) {
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
    render();
    for (const link of selfLinks) setAttr(link, "href", pageOf(next));
  }

  // The theme stylesheet: femto's css/themes/<color>.css, after femto.colors.min.css; none for azure.
  const colorsSheet = document.querySelector("link[rel=stylesheet][href$='/femto.colors.min.css']");
  const themes = `${colorsSheet?.getAttribute("href").replace(/dist\/femto\.colors\.min\.css$/, "")}css/themes/`;
  let sheet = document.querySelector("link[rel=stylesheet][href*='/css/themes/']");
  let swaps = 0;
  let target = color; // the color the newest swap shows

  // Loads the color's stylesheet, then swaps it in and shows the color in the same task, so the
  // page never shows a color the section does not. With `toUrl` it replaces ?theme= in the URL.
  // The newest swap wins.
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

  // The example's Privacy Policy link goes nowhere.
  for (const link of form.querySelectorAll("a")) link.addEventListener("click", (event) => event.preventDefault());

  header.addEventListener("click", (event) => {
    const swatch = event.target instanceof Element ? event.target.closest("a") : null;
    if (!swatch || !swatches.includes(swatch) || event.defaultPrevented || event.button !== 0
      || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    // The current color's swatch does nothing.
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
