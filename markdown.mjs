// The docs as Markdown, for agents (PLAN.md Decision 19). build.mjs calls markdown() with the docs'
// sections and writes the files it returns: one per section, an index of them and all of them joined.
// It reads only the markup the section files use, and fails the build on an element it has no rule for.
//
// A section's prose, headings, lists, tables and code samples are kept. Its live examples (<article>)
// leave only their code samples, and the controls that need the site's scripts leave nothing.

const VOID = new Set(["br", "hr", "img", "input", "source", "track", "wbr"]);
const DROPPED = new Set(["button", "dialog", "fieldset", "form", "input", "label"]);
const CONTAINERS = new Set(["div", "footer", "header", "hgroup", "section"]);
const PLAIN = new Set(["abbr", "cite", "del", "ins", "kbd", "mark", "s", "small", "span", "sub", "sup", "u"]);
const BOLD = new Set(["b", "strong"]), ITALIC = new Set(["em", "i"]);
const TOKEN = /<!--[\s\S]*?-->|<\/([a-z][\w-]*)\s*>|<([a-z][\w-]*)((?:\s+[^\s"'<>/=]+(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'<>]+))?)*)\s*(\/?)>|([^<]+)/giy;

/**
 * The docs' Markdown files.
 * @param {object} docs categories ([{ title, sections: [{ id, text }] }], text a section file with its
 *   placeholders filled), origin (the site's, for links), description (the docs page's), and build.mjs's
 *   unesc and fail
 * @returns {Map<string, string>} each file's path in dist/ and its text
 */
export function markdown({ categories, origin, description, unesc, fail }) {
  const ids = new Set(categories.flatMap((c) => c.sections.map((s) => s.id)));
  let where;

  function parse(html) {
    const root = { tag: "", attrs: {}, children: [] }, stack = [root];
    TOKEN.lastIndex = 0;
    for (let at = 0, m; at < html.length; at = TOKEN.lastIndex) {
      if (!(m = TOKEN.exec(html))) fail(`${where}: cannot read the markup at ${JSON.stringify(html.slice(at, at + 40))}`);
      const [, close, open, attrs, selfClosing, text] = m, top = stack.at(-1);
      if (text) top.children.push(text);
      else if (close) stack.length > 1 && top.tag === close.toLowerCase() ? stack.pop() : fail(`${where}: </${close}> closes <${top.tag}>`);
      else if (open) {
        const node = { tag: open.toLowerCase(), attrs: {}, children: [] };
        for (const [, name, , a, b, c] of attrs.matchAll(/([^\s=]+)(\s*=\s*(?:"([^"]*)"|'([^']*)'|(\S+)))?/g)) node.attrs[name.toLowerCase()] = unesc(a ?? b ?? c ?? "");
        top.children.push(node);
        if (!selfClosing && !VOID.has(node.tag)) stack.push(node);
      }
    }
    return stack.length === 1 ? root : fail(`${where}: <${stack.at(-1).tag}> is not closed`);
  }

  const raw = (n) => typeof n === "string" ? unesc(n) : n.children.map(raw).join("");
  const find = (n, test, out = []) => {
    if (typeof n !== "string") { if (test(n)) out.push(n); for (const c of n.children) find(c, test, out); }
    return out;
  };
  const language = (n) => n.tag === "code" && /(?:^|\s)language-([\w-]+)/.exec(n.attrs.class ?? "")?.[1];
  const ticks = (s) => Math.max(0, ...(s.match(/`+/g) ?? []).map((run) => run.length));
  const fence = (lang, code) => { const f = "`".repeat(Math.max(3, ticks(code) + 1)); return `${f}${lang}\n${code.replace(/\n$/, "")}\n${f}`; };
  const tidy = (s) => s.replace(/[ \t]*\n[ \t]*/g, "\n").replace(/ *<br> */g, "<br>").replace(/ {2,}/g, " ").trim();
  function link(href) {
    const url = !href.startsWith("#") ? (href.startsWith("/") ? origin + href : href)
      : ids.has(href.slice(1)) ? `${origin}/docs/${href.slice(1)}.md` : fail(`${where}: ${href} is no section`);
    return /[\s()<>]/.test(url) ? fail(`${where}: Markdown cannot link ${url}`) : url;
  }

  // Inline content. In a table cell a line break is <br>, and a | is escaped in code too, as GFM needs.
  function inline(n, cell) {
    if (typeof n === "string") return unesc(n).replace(/\s+/g, " ").replace(/[\\`*_[\]<|]/g, "\\$&");
    const kids = () => n.children.map((c) => inline(c, cell)).join("");
    if (n.tag === "br") return cell ? "<br>" : "\\\n";
    if (DROPPED.has(n.tag) || n.attrs.role === "img") return "";
    if (n.tag === "code" || n.tag === "samp") {
      const code = raw(n).replace(/\s+/g, " ").trim(), f = "`".repeat(ticks(code) + 1), pad = /^`|`$/.test(code) ? " " : "";
      return code ? f + pad + (cell ? code.replace(/\|/g, "\\|") : code) + pad + f : "";
    }
    if (n.tag === "a") { const text = tidy(kids()); return text ? `[${text}](${link(n.attrs.href ?? fail(`${where}: a link has no href`))})` : ""; }
    if (BOLD.has(n.tag) || ITALIC.has(n.tag)) { const text = tidy(kids()), mark = BOLD.has(n.tag) ? "**" : "*"; return text ? mark + text + mark : ""; }
    return PLAIN.has(n.tag) ? kids() : fail(`${where}: markdown.mjs has no rule for <${n.tag}> in a line of text`);
  }

  function table(n, out) {
    const caption = find(n, (c) => c.tag === "caption")[0];
    if (caption) out.push(`**${tidy(caption.children.map((k) => inline(k)).join(""))}**`);
    const rows = find(n, (c) => c.tag === "tr").map((tr) => tr.children.filter((c) => c.tag === "td" || c.tag === "th"));
    const width = Math.max(...rows.map((cells) => cells.length));
    const lines = rows.map((cells) => {
      // A row group's heading, one cell across the table, is bold in the first column.
      const texts = cells.map((c) => { const text = tidy(c.children.map((k) => inline(k, true)).join("")).replace(/\n/g, " "); return c.attrs.colspan && text ? `**${text}**` : text; });
      return `| ${texts.concat(Array(width - texts.length).fill("")).join(" | ")} |`;
    });
    if (!find(n, (c) => c.tag === "thead").length) lines.unshift(`|${" |".repeat(width)}`);
    lines.splice(1, 0, `|${" --- |".repeat(width)}`);
    out.push(lines.join("\n"));
  }

  function blocks(n, out = []) {
    let text = [];
    const flush = () => { const line = tidy(text.join("")); text = []; if (line) out.push(line); };
    for (const c of n.children) {
      const tag = c.tag;
      if (typeof c === "string" || !/^(article|blockquote|h[1-6]|hr|ol|p|pre|table|ul)$/.test(tag) && !CONTAINERS.has(tag) && !DROPPED.has(tag)) { text.push(inline(c)); continue; }
      flush();
      if (DROPPED.has(tag) || "data-palette-help" in c.attrs || "data-color-modal" in c.attrs || tag === "p" && c.attrs.class === "chapter") continue;
      if (tag === "article") for (const code of find(c, language)) out.push(fence(language(code), raw(code)));
      else if (CONTAINERS.has(tag)) blocks(c, out);
      else if (tag === "hr") out.push("---");
      else if (tag === "pre") { const code = c.children.find((k) => k.tag === "code"); out.push(fence(code && language(code) || "", raw(c))); }
      else if (tag === "table") table(c, out);
      else if (tag === "blockquote") out.push(blocks(c).join("\n\n").replace(/^/gm, "> ").replace(/^> $/gm, ">"));
      else if (tag === "ul" || tag === "ol") {
        out.push(c.children.filter((k) => k.tag === "li").map((li, i) => `${tag === "ol" ? `${i + 1}.` : "-"} ${tidy(li.children.map((k) => inline(k)).join("")).replace(/\n/g, " ")}`).join("\n"));
      } else {
        const line = tidy(c.children.map((k) => inline(k)).join(""));
        if (line) out.push(tag === "p" ? line : `${"#".repeat(Number(tag[1]))} ${line.replace(/\n/g, " ")}`);
      }
    }
    flush();
    return out;
  }

  const files = new Map();
  const index = [`# femto`, `> ${description}`,
    `Each section of femto's documentation is one Markdown file, listed here. [All of them in one file](${origin}/docs-full.md).`];
  for (const { title, sections } of categories) {
    const items = sections.map(({ id, text }) => {
      where = `docs/sections/${id}.html`;
      const tree = parse(text), hgroup = tree.children.find((c) => c.tag === "hgroup") ?? fail(`${where}: no hgroup`);
      const line = (node) => tidy(node.children.map((k) => inline(k)).join("")).replace(/\n/g, " ");
      const h1 = line(hgroup.children.find((c) => c.tag === "h1") ?? fail(`${where}: no h1`));
      const intro = hgroup.children.filter((c) => c.tag === "p" && c.attrs.class !== "chapter").map(line).join(" ");
      files.set(`docs/${id}.md`, `${blocks(tree).join("\n\n")}\n`);
      return `- [${h1}](${origin}/docs/${id}.md)${intro ? `: ${intro}` : ""}`;
    });
    index.push(`## ${title}`, items.join("\n"));
  }
  const all = [...files.values()].join("\n");
  files.set("docs.md", `${index.join("\n\n")}\n`).set("llms.txt", files.get("docs.md")).set("docs-full.md", all);
  return files;
}
