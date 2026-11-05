// npm run build [-- --out DIR]: site/ into dist/ (PLAN.md Decision 3, docs/research/03 §2).
// Node built-ins and prismjs only. The same input always gives byte-identical output: no timestamps,
// sorted listings, and the output folder is synced (stale files removed, changed files written), so a
// server watching it never sees it vanish.
//
// 1. Copy. Every file under site/ except partials/, docs/ (menu.json and the section files) and
//    dotfiles: vendor/femto/ included, whose stylesheets every page links.
// 2. Include. A line `<!-- include partials/<file> -->` is replaced by the partial, indented to the
//    marker (so partials hold no <pre> or <textarea>); partials may include partials. The placeholders
//    are {{version}} (femto's, from vendor/femto/SOURCE), {{title}} and {{description}} (a page's own
//    <title> and description).
//    Links in an included header or footer partial whose href is the page's own path (the oracle's
//    rule: the path without its trailing slash, so "/" never matches) get aria-current="page", and
//    the header's theme toggle (href="#" in the partial) links to the page itself, as the oracle's
//    server HTML did (site.js sets it again on load, for the 404 page).
// 3. Assemble the docs page (02 §6), written to docs.html and served at /docs (never docs/index.html,
//    Decision 11). From docs/menu.json, the build fills docs.html's two empty elements: the side nav
//    (nav.is-sticky-above-lg) gets one open <details> per category, with its summary and one link to
//    #<id> per section (its label, else its title), and #content every docs/sections/<id>.html in
//    menu order, each wrapped in a <section>. A missing file, or one that does not begin with its
//    hgroup (the chapter, then <h1 id="<id>">), fails the build. It also writes the Colors section's
//    palette download, assets/femto-color-palette.json: colors.js's PALETTE hex values by family and
//    shade, as JSON.stringify(palette, null, 2), the JSON the oracle's DownloadColorPalette made on
//    load as a blob: URL (01 §2, 03 §5).
// 4. Highlight. Every <code class="language-X"> holds escaped source text only; Prism tokenizes it and
//    the build writes react-syntax-highlighter 15.6's spans: Prism's token tree flattened so each text run
//    is one span whose class list is the union of its ancestors' (class="" for plain text), and then
//    split at newlines exactly as its processLines() does (wrapLines off). The oracle's "html" was
//    refractor's html, which is Prism's markup grammar with CSS and JavaScript inlined (prism-light's
//    registerLanguage("html", jsx) ignores the name, so jsx was registered as jsx and never used).
// 5. Sitemap. sitemap.xml lists the canonical URL of every page except 404.html and noindex pages.
import { existsSync, mkdirSync, readdirSync, readFileSync, rmdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const Prism = require("prismjs"); // core with markup, css, clike and javascript
require("prismjs/components/prism-bash.js");
require("prismjs/components/prism-scss.js");

const ROOT = dirname(fileURLToPath(import.meta.url));
const SITE = join(ROOT, "site");
const GRAMMARS = { html: "markup", css: "css", scss: "scss", bash: "bash" };

const fail = (message) => { throw new Error(`build: ${message}`); };
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0" };
const unesc = (s) => s.replace(/&(#x[\da-f]+|#\d+|\w+);/gi, (m, e) => e[0] !== "#" ? ENTITIES[e] ?? fail(`unknown entity ${m}`)
  : String.fromCodePoint(e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : Number(e.slice(1))));
const read = (path) => readFileSync(join(SITE, path), "utf8");

// --- 4. Highlighting: refractor's hast, react-syntax-highlighter's flattenCodeTree and processLines.
function hast(tokens) { // refractor stringify(): a Token becomes span.token.<type>.<alias>; "" is dropped
  return (Array.isArray(tokens) ? tokens : [tokens]).filter((t) => t !== "").map((t) => typeof t === "string" ? t
    : { cls: ["token", t.type].concat(t.alias ?? []), children: typeof t.content === "string" ? [t.content] : hast(t.content) });
}
function flatten(nodes, cls = [], out = []) {
  for (const n of nodes) {
    if (typeof n === "string") out.push({ cls: [...new Set(cls)], text: n });
    else flatten(n.children, cls.concat(n.cls), out);
  }
  return out;
}
function splitLines(tree) { // a run is a span ({cls, text}) or, for some lines of plain text, a bare string
  const out = [];
  let last = -1;
  for (let i = 0; i < tree.length; i++) {
    const { cls, text } = tree[i];
    if (!text.includes("\n")) continue;
    const parts = text.split("\n");
    parts.forEach((part, k) => {
      if (k === 0) out.push(...tree.slice(last + 1, i), { cls, text: `${part}\n` });
      else if (k < parts.length - 1) out.push(cls.length ? { cls, text: `${part}\n` } : `${part}\n`);
      else if (tree[i + 1]) tree.splice(i + 1, 0, { cls, text: part });
      else out.push(cls.length ? { cls, text: part } : part);
    });
    last = i;
  }
  return out.concat(tree.slice(last + 1));
}
export function highlight(code, language) {
  const grammar = Prism.languages[GRAMMARS[language]] ?? fail(`no grammar for language-${language}`);
  const env = { code, grammar, language };
  Prism.hooks.run("before-tokenize", env);
  env.tokens = Prism.tokenize(env.code, env.grammar);
  Prism.hooks.run("after-tokenize", env);
  return splitLines(flatten(hast(env.tokens))).map((r) => typeof r === "string" ? esc(r)
    : `<span class="${r.cls.join(" ")}">${esc(r.text)}</span>`).join("");
}
export const highlightAll = (html, where) => html.replace(/<code class="language-([\w-]+)">([\s\S]*?)<\/code>/g, (m, lang, body) =>
  body.includes("<") ? fail(`${where}: <code class="language-${lang}"> must hold escaped text only`)
    : `<code class="language-${lang}">${highlight(unesc(body), lang)}</code>`);

// --- 2. Includes, placeholders and the header and footer links to the page itself.
function expand(html, page, depth = 0) {
  return html.replace(/^([ \t]*)<!-- include partials\/([\w.-]+\.html) -->/gm, (m, indent, file) => {
    if (depth > 5) fail(`${page.file}: includes nested too deep at ${file}`);
    let text = expand(read(`partials/${file}`).replace(/\n$/, ""), page, depth + 1).replace(/\n(?=.)/g, `\n${indent}`);
    text = indent + text;
    if (/header|footer/.test(file) && page.path) {
      text = text.replace(/<a\s[^>]*>/g, (a) => /\saria-current=/.test(a) || a.match(/\shref="([^"]*)"/)?.[1] !== page.path ? a
        : a.replace("<a ", '<a aria-current="page" '));
    }
    if (/header/.test(file) && page.path != null) text = text.replace(/(<a [^>]*aria-label="Turn on dark mode"[^>]*href=)"#"/, `$1"${page.path || "/"}"`);
    return text;
  });
}
function render(html, page) {
  html = expand(html, page);
  if (html.includes("<!-- include ")) fail(`${page.file}: an include marker must be alone on its line`);
  if (/<code(?! class="language-[\w-]+">)[^>]*language-/.test(html)) fail(`${page.file}: write code as <code class="language-X"> exactly`);
  const values = { version: page.version, title: page.title, description: page.description };
  html = html.replace(/\{\{(\w+)\}\}/g, (m, key) => values[key] != null ? esc(values[key]) : fail(`${page.file}: no value for ${m}`));
  return highlightAll(html, page.file);
}
const ownPath = (url) => url.replace(/\/$/, "");
const swap = (html, from, to, where) => html.split(from).length === 2 ? html.replace(from, () => to) : fail(`${where}: expected one ${from}`);

// --- 3. The docs page and its palette file.
function docsPage(menu) {
  const nav = menu.categories.map((c) => {
    const links = c.sections.map((s) => `\n            <li><a class="secondary" data-discover="true" href="#${s.id}">${s.label ?? esc(s.title)}</a></li>`);
    return `<details open><summary>${esc(c.title)}</summary><ul>${links.join("")}\n          </ul></details>`;
  });
  const sections = menu.categories.flatMap((c) => c.sections).map(({ id }) => {
    const file = `docs/sections/${id}.html`;
    if (!existsSync(join(SITE, file))) fail(`docs/menu.json: no section file ${file}`);
    const text = read(file).trim();
    const heading = new RegExp(`^<hgroup>\\n[ \\t]*<p class="chapter">[^<]*</p>\\n[ \\t]*<h1 id="${id}">`);
    if (!heading.test(text)) fail(`${file}: must begin with <hgroup>, its chapter, then <h1 id="${id}">`);
    return `<section>\n${text}\n</section>\n`;
  });
  let html = read("docs.html");
  html = swap(html, '<nav class="is-sticky-above-lg"></nav>', `<nav class="is-sticky-above-lg">\n          ${nav.join("\n          ")}\n        </nav>`, "docs.html");
  return swap(html, '<div id="content" role="document"></div>', `<div id="content" role="document">\n${sections.join("")}      </div>`, "docs.html");
}
function palette() {
  const js = read("assets/js/colors.js");
  const shades = JSON.parse(js.match(/^const SHADES = (\[[^\]]*\]);$/m)?.[1] ?? fail("assets/js/colors.js: no SHADES"));
  const families = [...js.matchAll(/^ {2}(\w+): \["\d+",\n([^\]]*)\],$/gm)].map(([, family, list]) => {
    const hexes = [...list.matchAll(/"([\da-f]{6}) /g)].map(([, hex]) => `#${hex}`);
    if (hexes.length !== shades.length) fail(`assets/js/colors.js: PALETTE.${family} has ${hexes.length} colors, not ${shades.length}`);
    return [family, Object.fromEntries(shades.map((shade, i) => [shade, hexes[i]]))];
  });
  if (!families.length) fail("assets/js/colors.js: no PALETTE families");
  return JSON.stringify(Object.fromEntries(families), null, 2);
}

// --- 1. Copy, then 5. the sitemap, then write.
function walk(dir, base = dir) {
  return readdirSync(dir).sort().flatMap((name) => {
    const full = join(dir, name);
    if (name.startsWith(".")) return [];
    return statSync(full).isDirectory() ? walk(full, base) : [relative(base, full).split("\\").join("/")];
  });
}
export function build() {
  const source = read("vendor/femto/SOURCE");
  const version = source.match(/^version: (\S+)$/m)?.[1] ?? fail("site/vendor/femto/SOURCE has no version");
  const files = new Map();
  const pages = [];
  for (const file of walk(SITE)) {
    if (/^(partials|docs)\//.test(file)) continue;
    if (!/^[^/]+\.html$/.test(file)) { files.set(file, readFileSync(join(SITE, file))); continue; }
    const html = file === "docs.html" ? docsPage(JSON.parse(read("docs/menu.json"))) : read(file);
    const title = html.match(/<title>([^<{]*)<\/title>/)?.[1];
    const description = html.match(/<meta name="description" content="([^"{]*)">/)?.[1];
    const url = file === "index.html" ? "/" : `/${file.replace(/\.html$/, "")}`;
    pages.push({ out: file, html, file, path: file === "404.html" ? null : ownPath(url), version,
      title: title && unesc(title), description: description && unesc(description) });
  }
  files.set("assets/femto-color-palette.json", Buffer.from(palette()));
  const locs = [];
  for (const page of pages) {
    const html = render(page.html, page);
    files.set(page.out, Buffer.from(html));
    if (page.out === "404.html" || /<meta name="robots" content="[^"]*noindex/.test(html)) continue;
    locs.push(new URL(html.match(/<link rel="canonical" href="([^"]+)">/)?.[1] ?? fail(`${page.file}: no rel=canonical`)).href);
  }
  const urls = [...new Set(locs)].sort().map((loc) => `  <url><loc>${esc(loc)}</loc></url>\n`).join("");
  files.set("sitemap.xml", Buffer.from(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}</urlset>\n`));
  return files;
}
function write(files, out) {
  const rel = relative(out, ROOT);
  if (out === ROOT || !rel.startsWith("..") && !rel.includes(":") || out.startsWith(SITE)) fail(`refusing to write into ${out}`);
  const old = existsSync(out) ? walk(out) : [];
  if (old.length && !old.includes("sitemap.xml")) fail(`${out} is not empty and holds no earlier build (sitemap.xml)`);
  for (const file of old) if (!files.has(file)) rmSync(join(out, file));
  for (const [file, data] of files) {
    const path = join(out, file);
    if (existsSync(path) && readFileSync(path).equals(data)) continue;
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, data);
  }
  const prune = (dir) => { for (const n of readdirSync(dir)) { const d = join(dir, n); if (statSync(d).isDirectory()) { prune(d); if (!readdirSync(d).length) rmdirSync(d); } } };
  prune(out);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  if (args.length && (args.length !== 2 || args[0] !== "--out")) fail(`unknown arguments ${args.join(" ")} (use --out DIR)`);
  const out = resolve(args[1] ?? join(ROOT, "dist"));
  const files = build();
  write(files, out);
  console.log(`build: ${files.size} files in ${relative(ROOT, out) || "."}`);
}
