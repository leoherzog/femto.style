// npm run build [-- --out DIR]: site/ into dist/ (PLAN.md Decision 3).
// Node built-ins and prismjs only. The same input always gives byte-identical output: no timestamps,
// sorted listings, and the output folder is synced (stale files removed, changed files written), so a
// server watching it never sees it vanish.
//
// 1. Copy. Every file under site/ except partials/, docs/ (menu.json and the section files) and
//    dotfiles: vendor/femto/ included, whose stylesheets every page links. The site's own CSS and
//    JavaScript, assets/**/*.css and *.js, lose their comments (strip); the rest is copied as it is.
// 2. Include. A line `<!-- include partials/<file> -->` is replaced by the partial, indented to the
//    marker (so partials hold no <pre> or <textarea>); partials may include partials. The placeholders
//    are {{version}} and {{commit}} (femto's, from vendor/femto/SOURCE), {{title}} and {{description}}
//    (a page's own <title> and description).
//    Links in an included header or footer partial whose href is the page's own path (/docs,
//    /examples; never the homepage's /) get aria-current="page".
// 3. Assemble the docs page (Decision 2), written to docs.html and served at /docs (never docs/index.html,
//    Decision 11). From docs/menu.json, the build fills docs.html's two empty elements: the side nav
//    (nav.is-sticky-above-lg) gets one open <details> per category, with its summary and one link to
//    #<id> per section (its label, else its h1's content), and #content every docs/sections/<id>.html
//    in menu order, each wrapped in a <section> and ending with its "Edit this section on GitHub" link
//    to the file, named ": <h1>" in visually hidden text. A missing file, one that does not begin with
//    its hgroup (the chapter, then <h1 id="<id>">), or one with its own edit link fails the build. It
//    also writes the Colors section's palette download, assets/femto-color-palette.json: femto.colors.css's
//    --femto-color-<family>-<shade> hex values by family and shade, as JSON.stringify(palette, null, 2).
// 4. Highlight. Every <code class="language-X"> holds escaped source text only; Prism tokenizes it and
//    the build writes each run of one color as one span whose class names the color (colorOf: the
//    four colors code.css draws); plain text, most punctuation among it, is not wrapped. "html" is
//    Prism's markup grammar, which inlines CSS and JavaScript.
//    The <pre class="prismjs"> around such a code block gets tabindex="0" and the hook
//    data-scroll-focus: a block whose code is wider than it scrolls sideways, and the keyboard can
//    scroll it only once it takes focus (axe's scrollable-region-focusable, criterion 10). Which
//    blocks scroll depends on the viewport, so without JavaScript every one takes focus; site.js then
//    keeps tabindex="0" only on the blocks that overflow, and names those.
// 5. Sitemap. sitemap.xml lists the canonical URL of every page except 404.html and noindex pages.
import { existsSync, mkdirSync, readdirSync, readFileSync, rmdirSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";

const require = createRequire(import.meta.url);
const Prism = require("prismjs"); // core with markup, css, clike and javascript
require("prismjs/components/prism-bash.js");

const ROOT = import.meta.dirname;
const SITE = join(ROOT, "site");
const GRAMMARS = { html: "markup", css: "css", bash: "bash" };

const fail = (message) => { throw new Error(`build: ${message}`); };
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00a0" };
const unesc = (s) => s.replace(/&(#x[\da-f]+|#\d+|\w+);/gi, (m, e) => e[0] !== "#" ? ENTITIES[e] ?? fail(`unknown entity ${m}`)
  : String.fromCodePoint(e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : Number(e.slice(1))));
const read = (path) => readFileSync(join(SITE, path), "utf8");

// --- 1. A site CSS or JS file without its comments. Prism tokenizes it, so a string or a regex is
// never read as a comment, and each comment, marked \uE000<n>\uE001, becomes its own newlines, so line
// numbers still match site/. Only spaces next to a comment go: before it when its line ends there,
// after it when the line ends after it. A comment that alone separates two tokens stays.
function strip(text, language, where) {
  if (/[\uE000\uE001]/.test(text)) fail(`${where}: holds a U+E000 or U+E001 character`);
  const comments = [];
  const flat = (t) => typeof t === "string" ? t : Array.isArray(t) ? t.map(flat).join("")
    : t.type === "comment" ? `\uE000${comments.push(flat(t.content)) - 1}\uE001` : flat(t.content);
  const marked = flat(Prism.tokenize(text, Prism.languages[language]));
  let out = "", last = 0;
  for (const { 0: all, 1: before, 2: k, 3: after, index } of marked.matchAll(/([ \t]*)\uE000(\d+)\uE001([ \t]*)/g)) {
    out += marked.slice(last, index) + before;
    last = index + all.length;
    const lines = comments[k].replace(/[^\n]/g, ""), next = marked[last] ?? "\n";
    if (lines) out = out.replace(/[ \t]+$/, "") + lines;
    if (next === "\n") out = out.replace(/[ \t]+$/, "");
    else if (next !== "\uE000") out += lines ? after : /(^|\s)$/.test(out) ? "" : after || comments[k];
  }
  return out + marked.slice(last);
}

// --- 4. Highlighting: Prism's tokens as runs of text, each run's color, one span per color run.
function runs(tokens, types = [], out = []) { // each text run with the types and aliases of the tokens around it
  for (const t of Array.isArray(tokens) ? tokens : [tokens]) {
    if (typeof t !== "string") runs(t.content, types.concat(t.type, t.alias ?? []), out);
    else if (t) out.push({ types: new Set(types), text: t });
  }
  return out;
}
// The four colors code.css draws: a tag's punctuation (<, >, the attribute's =) is plain, an
// attribute value's quotes take its color, and so does a whole doctype.
function colorOf(types) {
  const has = (...names) => names.some((name) => types.has(name));
  if (has("doctype") || has("comment") && !has("punctuation")) return "comment";
  if (has("attr-value", "string")) return has("attr-equals") ? null : "value";
  if (has("keyword", "boolean", "function")) return "attr";
  if (has("punctuation")) return null;
  if (has("attr-name", "selector")) return "attr";
  return has("tag", "property") ? "tag" : null;
}
const escText = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function highlight(code, language) {
  const grammar = Prism.languages[GRAMMARS[language]] ?? fail(`no grammar for language-${language}`);
  const list = runs(Prism.tokenize(code, grammar)).map(({ types, text }) => ({ color: /\S/.test(text) ? colorOf(types) : undefined, text }));
  // Whitespace shows no color: it takes its neighbors' color when they share one, so the three are
  // one span, and is plain text otherwise.
  list.forEach((run, i) => {
    if (run.color !== undefined) return;
    const before = list[i - 1]?.color ?? null, after = list.slice(i + 1).find((r) => r.color !== undefined)?.color ?? null;
    run.color = before === after ? before : null;
  });
  let html = "", open = null;
  for (const { color, text } of list) {
    if (color !== open) html += (open ? "</span>" : "") + (color ? `<span class="${color}">` : "");
    open = color;
    html += escText(text);
  }
  return open ? `${html}</span>` : html;
}
const highlightAll = (html, where) => html.replace(/(<pre class="prismjs">)?<code class="language-([\w-]+)">([\s\S]*?)<\/code>/g, (m, pre, lang, body) =>
  body.includes("<") ? fail(`${where}: <code class="language-${lang}"> must hold escaped text only`)
    : `${pre ? '<pre class="prismjs" tabindex="0" data-scroll-focus>' : ""}<code class="language-${lang}">${highlight(unesc(body), lang)}</code>`);

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
    return text;
  });
}
function render(html, page) {
  html = expand(html, page);
  if (html.includes("<!-- include ")) fail(`${page.file}: an include marker must be alone on its line`);
  if (/<code(?! class="language-[\w-]+">)[^>]*language-/.test(html)) fail(`${page.file}: write code as <code class="language-X"> exactly`);
  const values = { version: page.version, commit: page.commit, title: page.title, description: page.description };
  html = html.replace(/\{\{(\w+)\}\}/g, (m, key) => values[key] != null ? esc(values[key]) : fail(`${page.file}: no value for ${m}`));
  return highlightAll(html, page.file);
}
const swap = (html, from, to, where) => html.split(from).length === 2 ? html.replace(from, () => to) : fail(`${where}: expected one ${from}`);

// --- 3. The docs page and its palette file.
function docsPage(menu) {
  const files = menu.categories.flatMap((c) => c.sections).map(({ id }) => {
    const file = `docs/sections/${id}.html`;
    if (!existsSync(join(SITE, file))) fail(`docs/menu.json: no section file ${file}`);
    const text = read(file).trim();
    if (text.includes('class="edit-on-github"')) fail(`${file}: the build writes the section's edit link`);
    const heading = new RegExp(`^<hgroup>\\n[ \\t]*<p class="chapter">[^<]*</p>\\n[ \\t]*<h1 id="${id}">([\\s\\S]*?)</h1>`);
    return { id, text, h1: text.match(heading)?.[1] ?? fail(`${file}: must begin with <hgroup>, its chapter, then <h1 id="${id}">`) };
  });
  const nav = menu.categories.map((c) => {
    const links = c.sections.map((s) => `\n            <li><a class="secondary" href="#${s.id}">${s.label ?? files.find((f) => f.id === s.id).h1}</a></li>`);
    return `<details open><summary>${esc(c.title)}</summary><ul>${links.join("")}\n          </ul></details>`;
  });
  const edit = (id, h1) => `<section class="edit-on-github">\n  <p><a class="secondary" href="https://github.com/leoherzog/femto.style/blob/main/site/docs/sections/${id}.html"><small><span role="img" aria-hidden="true">✎</span>Edit this section on GitHub<span class="visually-hidden">: ${h1}</span></small></a></p>\n</section>`;
  const sections = files.map(({ id, text, h1 }) => `<section>\n${text}\n${edit(id, h1)}\n</section>\n`);
  let html = read("docs.html");
  html = swap(html, '<nav class="is-sticky-above-lg" aria-label="Documentation"></nav>', `<nav class="is-sticky-above-lg" aria-label="Documentation">\n          ${nav.join("\n          ")}\n        </nav>`, "docs.html");
  return swap(html, '<div id="content"></div>', `<div id="content">\n${sections.join("")}      </div>`, "docs.html");
}
function palette() {
  const palette = {};
  for (const [, family, shade, hex] of read("vendor/femto/css/femto.colors.css").matchAll(/^ {2}--femto-color-([a-z]+)-(\d+): (#[\da-f]{6});$/gm)) (palette[family] ??= {})[shade] = hex;
  if (!Object.keys(palette).length) fail("vendor/femto/css/femto.colors.css: no --femto-color-<family>-<shade> tokens");
  return JSON.stringify(palette, null, 2);
}

// --- 1. Copy, then 5. the sitemap, then write.
const walk = (dir) => readdirSync(dir, { recursive: true, withFileTypes: true }).filter((d) => d.isFile())
  .map((d) => relative(dir, join(d.parentPath, d.name)).split("\\").join("/")).filter((f) => !/(^|\/)\./.test(f)).sort();
function build() {
  const source = read("vendor/femto/SOURCE");
  const version = source.match(/^version: (\S+)$/m)?.[1] ?? fail("site/vendor/femto/SOURCE has no version");
  const commit = source.match(/^commit: ([0-9a-f]{40})$/m)?.[1] ?? fail("site/vendor/femto/SOURCE has no commit");
  const files = new Map();
  const pages = [];
  for (const file of walk(SITE)) {
    if (/^(partials|docs)\//.test(file)) continue;
    const own = /^assets\/.*\.(css|js)$/.exec(file)?.[1];
    if (own) { files.set(file, Buffer.from(strip(read(file), own === "js" ? "javascript" : "css", file))); continue; }
    if (!/^[^/]+\.html$/.test(file)) { files.set(file, readFileSync(join(SITE, file))); continue; }
    const html = file === "docs.html" ? docsPage(JSON.parse(read("docs/menu.json"))) : read(file);
    const title = html.match(/<title>([^<{]*)<\/title>/)?.[1];
    const description = html.match(/<meta name="description" content="([^"{]*)">/)?.[1];
    pages.push({ html, file, path: /^(index|404)\.html$/.test(file) ? null : `/${file.slice(0, -5)}`, version, commit,
      title: title && unesc(title), description: description && unesc(description) });
  }
  files.set("assets/femto-color-palette.json", Buffer.from(palette()));
  const locs = [];
  for (const page of pages) {
    const html = render(page.html, page);
    files.set(page.file, Buffer.from(html));
    if (page.file === "404.html" || /<meta name="robots" content="[^"]*noindex/.test(html)) continue;
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
  const prune = (dir) => { for (const d of readdirSync(dir, { withFileTypes: true })) if (d.isDirectory()) { const p = join(dir, d.name); prune(p); if (!readdirSync(p).length) rmdirSync(p); } };
  prune(out);
}

const out = resolve(parseArgs({ options: { out: { type: "string" } } }).values.out ?? join(ROOT, "dist"));
const files = build();
write(files, out);
console.log(`build: ${files.size} files in ${relative(ROOT, out) || "."}`);
