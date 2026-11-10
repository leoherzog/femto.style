// picker.js: the Theme picker, the docs page's #theme-picker section (loaded from docs.html;
// PLAN.md Decision 8 and Owner answers 3).
//
// It binds to the section's data- hooks: the theme example with the 20 swatches,
// article[data-version-picker] (the hook keeps the version picker's name); the options,
// section[data-picker-options], one switch per file in femto's css/options/ (input[name=<option>]);
// and the three code samples, section[data-picker-usage=cdn|combine|template]:
// - cdn: the <link> tags in load order: femto, the theme (none for azure, which is built in), the
//   chosen options, then the reader's own stylesheet, styles.css;
// - combine: the same femto files in one jsDelivr combine URL, or femto's own link when it is the
//   only file (azure, no options);
// - template: femto's starter template, its femto <link> followed by the theme's and the options'.
// The section file writes the samples as azure with the switches checked in its markup (responsive
// spacings), the state a fresh load shows, so a fresh load rewrites nothing and shifts nothing.
// The samples keep the spans build.mjs writes (step 4: one span per color, plain text unwrapped):
// each <link> tag is written as those spans, and the template's other lines keep the spans the
// build gave them. The package and its version range (@leoherzog/femto@3) are read from
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
// - The option switches apply to the page and the samples alike: a checked switch's femto option
//   stylesheet (css/options/<option>.css) is linked, and an unchecked one's link is removed. The page
//   loads responsive-spacings.css, so that switch is checked in the markup. A reload or a return to
//   the page can restore other states, which the page follows on load.
// - Every change of color also animates the header logo for 1 s (class "animated" on its svg).
// - The page's title, description, canonical and og:url stay the docs page's (Decision 9); docs.js
//   sets document.title for the section being read.
// It does nothing on a page without the picker.

import { capitalize, escapeText, setAttr } from "./site.js";

// --- The files (femto's README: Themes, Options, Quick start) -------------------------------------

// femto's options, in the order their links are written.
const OPTIONS = ["responsive-spacings", "fixed-typography", "no-transitions"];
// The reader's own stylesheet, after femto's files.
const STYLESHEET = "styles.css";

// femto's files for a color and a set of options, in load order: femto, the theme, the options.
function filesOf(color, options) {
  return ["dist/femto.min.css", ...(color === "azure" ? [] : [`css/themes/${color}.css`]),
    ...OPTIONS.filter((option) => options.includes(option)).map((option) => `css/options/${option}.css`)];
}

// jsDelivr's URL for one file of the package (e.g. @leoherzog/femto@3), and the combine URL for
// several, which is the one file's URL when there is only one.
const fileUrl = (pkg, file) => `https://cdn.jsdelivr.net/npm/${pkg}/${file}`;
function combineUrl(pkg, files) {
  return files.length === 1 ? fileUrl(pkg, files[0])
    : `https://cdn.jsdelivr.net/combine/${files.map((file) => `npm/${pkg}/${file}`).join(",")}`;
}

// The package as the cdn sample names it, from its text; null if it names none.
function packageOf(text) {
  return /https:\/\/cdn\.jsdelivr\.net\/npm\/(@[\w.-]+\/[\w.-]+@[\w.-]+)\/dist\/femto\.min\.css/.exec(text)?.[1] ?? null;
}

// --- The highlighted samples (build.mjs, step 4) -------------------------------------------------
// Spans as the browser serializes the ones build.mjs writes: in text only &, < and > are escaped.

const span = (cls, text) => `<span class="${cls}">${escapeText(text)}</span>`;

// <link rel="stylesheet" href="<href>"> as the build highlights it: the tag name, the attribute
// names and the quoted values in their colors, the rest plain.
function linkTag(href) {
  const attribute = (name, value) => ` ${span("attr", name)}=${span("value", `"${value}"`)}`;
  return `&lt;${span("tag", "link")}${attribute("rel", "stylesheet")}${attribute("href", href)}&gt;`;
}

// One <link> tag per href, one per line, each line after the first indented by `indent`.
function linksHtml(hrefs, indent = "") {
  return hrefs.map(linkTag).join(`\n${indent}`);
}

// --- The color -----------------------------------------------------------------------------------

const SECTION = "theme-picker";
// The docs page in a color, with ?theme= unless azure: what the section's links to the page itself
// carry. urlOf is its picker section, what a swatch links.
const pageOf = (color) => (color === "azure" ? "/docs" : `/docs?theme=${color}`);
const urlOf = (color) => `${pageOf(color)}#${SECTION}`;
// The color a ?theme= query names, if it is one of `colors`; azure otherwise.
function colorOfQuery(search, colors) {
  const theme = new URLSearchParams(search).get("theme");
  return colors.includes(theme) ? theme : "azure";
}
// The query with ?theme= set to the color, or removed for azure. Only the theme pair changes: every
// other item of the search string stays as it was written, byte for byte (URLSearchParams.toString()
// would respell them: %20 as +, a bare ref as ref=). An item is a theme item when its name decodes,
// as URLSearchParams decodes it ('+' as a space, then percent-decoding), to "theme". The first one
// is replaced and later ones dropped, so get("theme"), the value the ?theme= head script reads,
// gives the color; theme=<color> is appended when there was none. Empty items (&&) are dropped, as
// URLSearchParams drops them.
const isThemeItem = (item) => {
  const name = item.split("=", 1)[0];
  try {
    return decodeURIComponent(name.replace(/\+/g, " ")) === "theme";
  } catch {
    return false; // a malformed escape, which URLSearchParams keeps as text: not "theme"
  }
};
function queryOf(search, color) {
  const items = [];
  let placed = color === "azure";
  for (const item of search.replace(/^\?/, "").split("&")) {
    if (!item) continue;
    if (!isThemeItem(item)) items.push(item);
    else if (!placed) {
      items.push(`theme=${color}`);
      placed = true;
    }
  }
  if (!placed) items.push(`theme=${color}`);
  return items.length ? `?${items.join("&")}` : "";
}
// "an azure", "a jade".
const withArticle = (color) => `${/^[aeiou]/.test(color) ? "an" : "a"} ${color}`;

// --- The section ---------------------------------------------------------------------------------

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

  // The template's lines other than its <link>s keep the spans the build gave them. Its <link>s are
  // the markup's state: azure, with the switches its markup checks.
  const defaults = OPTIONS.filter((option, i) => switches[i].defaultChecked);
  const builtTags = linksHtml(filesOf(colorOf(current), defaults).map((file) => fileUrl(pkg, file)), "    ");
  const template = codes.template.innerHTML;
  if (!template.includes(builtTags)) return;
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
    write("template", template.replace(builtTags, () => linksHtml(urls, "    ")));
  }

  optionsPart.addEventListener("change", (event) => {
    if (!switches.includes(event.target)) return;
    render();
    applyOptions();
  });

  // The example form's links to the page itself (its Privacy Policy link): they carry the color's
  // page, and go nowhere.
  const selfLinks = [...form.querySelectorAll("a")];
  for (const link of selfLinks) link.addEventListener("click", (event) => event.preventDefault());

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
    if (heading.textContent !== capitalize(next)) heading.textContent = capitalize(next);
    const text = `Form example with ${withArticle(next)} theme.`;
    if (sentence.textContent !== text) sentence.textContent = text;
    render();
    for (const link of selfLinks) setAttr(link, "href", pageOf(next));
  }

  // The theme stylesheet: femto's css/themes/<color>.css, after femto.colors.min.css; none for azure.
  const colorsSheet = document.querySelector("link[rel=stylesheet][href$='/femto.colors.min.css']");
  const themes = `${colorsSheet?.getAttribute("href").replace(/dist\/femto\.colors\.min\.css$/, "")}css/themes/`;
  let sheet = document.querySelector("link[rel=stylesheet][href*='/css/themes/']");

  // The option stylesheets: femto's css/options/<option>.css, one <link> per checked switch. A new
  // one goes after the option before it, else after the theme stylesheet, else after
  // femto.colors.min.css: no option changes a token a theme sets, so only the options' own order
  // matters.
  const optionsDir = themes.replace(/themes\/$/, "options/");
  const optionSheets = OPTIONS.map((option) =>
    document.querySelector(`link[rel=stylesheet][href="${optionsDir}${option}.css"]`));
  function applyOptions() {
    let previous = null;
    OPTIONS.forEach((option, i) => {
      if (switches[i].checked) {
        if (!optionSheets[i]) {
          const link = document.createElement("link");
          link.rel = "stylesheet";
          link.href = `${optionsDir}${option}.css`;
          (previous ?? sheet ?? colorsSheet).after(link);
          optionSheets[i] = link;
        }
        previous = optionSheets[i];
      } else if (optionSheets[i]) {
        optionSheets[i].remove();
        optionSheets[i] = null;
      }
    });
  }
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
        try {
          history.replaceState(history.state, "", location.pathname + query + location.hash);
        } catch {
          // WebKit's history limit (a SecurityError), as the spy's in docs.js: the color is shown,
          // and the URL keeps its old ?theme= until a later swap writes one.
        }
      }
    }, () => {
      link?.remove();
      if (ticket === swaps) location.assign(urlOf(next));
    });
  }

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
  // the start. The head script writes it only at the path /docs (partials/head.html), so at another
  // spelling of the path that serves this page (/DOCS, /%64ocs) the page is azure, and so is the
  // section.
  const start = location.pathname === "/docs" ? colorOfQuery(location.search, colors) : "azure";
  target = start;
  applyOptions();
  if (start !== color) show(start, false);
  else render();
}

// The picker is article[data-version-picker], the theme example with the swatches.
const article = document.querySelector("article[data-version-picker]");
if (article?.querySelector(":scope > header")) picker(article);
