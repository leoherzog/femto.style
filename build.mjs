// npm run build [-- --out DIR] [-- --only id,id]: site/ into dist/ (PLAN.md Decision 3, docs/research/03 §2).
// Node built-ins and prismjs only. The same input always gives byte-identical output: no timestamps,
// sorted listings, and the output folder is synced (stale files removed, changed files written), so a
// server watching it never sees it vanish.
//
// 1. Copy. Every file under site/ except partials/, docs/ (menu.json and the section files) and the
//    docs.html template, and dotfiles: vendor/femto/ included, whose stylesheets every page links.
// 2. Include. A line `<!-- include partials/<file> -->` is replaced by the partial, indented to the
//    marker (so partials hold no <pre> or <textarea>); partials may include partials. The placeholders
//    are {{version}} (femto's, from vendor/femto/SOURCE) and, on docs pages, {{title}} and
//    {{description}} (from menu.json; elsewhere a page's own <title> and description).
//    Links in an included header or footer partial whose href is the page's own path (the oracle's
//    rule: the path without its trailing slash, so "/" never matches) get aria-current="page", and
//    the header's theme toggle (href="#" in the partial) links to the page itself, as the oracle's
//    server HTML did (site.js sets it again on load, for the 404 page).
// 3. Assemble the docs, per route (Phases 1 and 2). For every section in docs/menu.json, docs.html is
//    the page: its <main> holds the per-route layout of the oracle (breadcrumb, the documentation menu,
//    then the section file docs/sections/<id>.html at <!-- docs:sections -->), and it is written to the
//    section's old route: /docs -> docs.html, /docs/forms/input -> docs/forms/input.html (never
//    docs/index.html, Decision 11). Per route, the build sets what the oracle derived from the route:
//    the <main> class (container, has-table-of-contents unless "toc": false, page-<route>), the
//    breadcrumb's chapter (the category), the menu's close link, rel=canonical and og:url (the route's
//    URL; the oracle's og:url is a bug), the title ("<routeTitle or title> • femto") and description,
//    and the route's extra "styles" after the page's stylesheets. The menu at <!-- docs:menu --> lists
//    every section of menu.json by category; the route's category is open and its link is current.
//    Version picker colors: each of the 19 "variants" (/docs/version-picker/<color>) is its own route
//    with its own section file, docs/sections/version-picker/<color>.html, converted from that route's
//    oracle DOM like any other: the oracle renders the color into the content (heading, swatches, code,
//    links to the route), so one file per route keeps every route's markup exact without JavaScript.
//    Its menu, chapter and <main> class are the version picker's, as in the oracle. Phase 3 replaces
//    this step with the one docs page and deletes the variant files.
//    --only id,id assembles only those sections (and their variants), for a scratch --out folder: it is
//    refused for dist/, which must always hold every page. The shared pages are always built. A route
//    whose section file does not exist fails the build.
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
const ORIGIN = "https://femto.style";
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

// --- 3. The docs, per route.
function docsPages(menu, only, version) {
  const template = read("docs.html");
  const pages = [];
  const sections = menu.categories.flatMap((c) => c.sections.map((s) => ({ ...s, category: c.title })));
  for (const id of only ?? []) if (!sections.some((s) => s.id === id)) fail(`--only: no section ${id} in docs/menu.json`);
  for (const s of sections.filter((x) => !only || only.includes(x.id))) {
    const routes = [{ ...s, file: `docs/sections/${s.id}.html` }].concat((s.variants ?? []).map((v) =>
      ({ ...v, file: `docs/sections/${s.id}/${v.route.split("/").pop()}.html` })));
    for (const r of routes) {
      if (!existsSync(join(SITE, r.file))) fail(`${r.route}: no section file ${r.file}`);
      const nav = menu.categories.map((c) => {
        const open = c.title === s.category;
        const links = c.sections.map((x) => `<li><a ${x.route === s.route ? 'aria-current="page" ' : ""}class="secondary" data-discover="true" href="${x.route}">${x.label}</a></li>`);
        return `<details${open ? " open" : ""}><summary${open ? ' aria-current="true"' : ""}>${esc(c.title)}</summary><ul>\n            ${links.join("\n            ")}\n          </ul></details>`;
      }).join("\n          ");
      const page = s.route === "/docs" ? "index" : s.route.slice("/docs/".length).replace(/\//g, "-");
      const main = ["container", s.toc !== false && "has-table-of-contents", `page-${page}`].filter(Boolean).join(" ");
      const where = `docs.html for ${r.route}`;
      let html = swap(template, '<main class="container has-table-of-contents page-index">', `<main class="${main}">`, where);
      html = swap(html, "<li>Getting started</li>", `<li>${esc(s.category)}</li>`, where);
      html = swap(html, '<a aria-label="Close" class="secondary" data-discover="true" href="/docs">',
        `<a aria-label="Close" class="secondary" data-discover="true" href="${r.route}">`, where);
      html = swap(html, '<link rel="canonical" href="https://femto.style/docs">', `<link rel="canonical" href="${ORIGIN}${r.route}">`, where);
      html = swap(html, '<meta property="og:url" content="https://femto.style/docs">', `<meta property="og:url" content="${ORIGIN}${r.route}">`, where);
      const links = html.slice(0, html.indexOf("</head>")).match(/\n[ \t]*<link rel="stylesheet"[^>]*>/g) ?? fail(`${where}: no stylesheet`);
      const styles = (r.styles ?? []).map((href) => `\n    <link rel="stylesheet" href="${href}">`).join("");
      html = swap(html, links.at(-1), links.at(-1) + styles, where);
      html = swap(html, "<!-- docs:menu -->", nav, where);
      html = swap(html, "<!-- docs:sections -->", read(r.file).trim(), where);
      pages.push({ out: `${r.route.slice(1)}.html`, html, file: r.file, path: ownPath(r.route), version,
        title: `${r.routeTitle ?? s.routeTitle ?? s.title} • femto`, description: r.description ?? s.description });
    }
  }
  return pages;
}

// --- 1. Copy, then 5. the sitemap, then write.
function walk(dir, base = dir) {
  return readdirSync(dir).sort().flatMap((name) => {
    const full = join(dir, name);
    if (name.startsWith(".")) return [];
    return statSync(full).isDirectory() ? walk(full, base) : [relative(base, full).split("\\").join("/")];
  });
}
export function build({ only } = {}) {
  const source = read("vendor/femto/SOURCE");
  const version = source.match(/^version: (\S+)$/m)?.[1] ?? fail("site/vendor/femto/SOURCE has no version");
  const files = new Map();
  const pages = [];
  for (const file of walk(SITE)) {
    if (/^(partials|docs)\//.test(file) || file === "docs.html") continue;
    if (!/^[^/]+\.html$/.test(file)) { files.set(file, readFileSync(join(SITE, file))); continue; }
    const html = read(file);
    const title = html.match(/<title>([^<{]*)<\/title>/)?.[1];
    const description = html.match(/<meta name="description" content="([^"{]*)">/)?.[1];
    const url = file === "index.html" ? "/" : `/${file.replace(/\.html$/, "")}`;
    pages.push({ out: file, html, file, path: file === "404.html" ? null : ownPath(url), version,
      title: title && unesc(title), description: description && unesc(description) });
  }
  pages.push(...docsPages(JSON.parse(read("docs/menu.json")), only, version));
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
  const opt = (name) => { const i = args.indexOf(name); return i < 0 ? undefined : args[i + 1] ?? fail(`${name} needs a value`); };
  const unknown = args.filter((a, i) => !["--out", "--only"].includes(a) && !["--out", "--only"].includes(args[i - 1]));
  if (unknown.length) fail(`unknown arguments ${unknown.join(" ")} (use --out DIR, --only id,id)`);
  const out = resolve(opt("--out") ?? join(ROOT, "dist"));
  if (opt("--only") && out === join(ROOT, "dist")) fail("--only builds part of the site: give it a scratch --out folder, never dist/");
  const files = build({ only: opt("--only")?.split(",").filter(Boolean) });
  write(files, out);
  console.log(`build: ${files.size} files in ${relative(ROOT, out) || "."}`);
}
