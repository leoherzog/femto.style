// node tests/convert/highlight-check.mjs [route-slug ...]
//
// Checks build.mjs's highlighter against every highlighted <code class="language-X"> in the oracle's
// hydrated DOM (tests/oracle/capture/<slug>/dom.html; all captured routes, or the slugs given): the
// code's text is highlighted again and the two run lists must be equal, run by run (each span's
// classes and text, and the bare text between spans). PLAN.md Risks, Highlighting parity. Exits 1 on
// any difference, and prints the first one per block.
import { readdirSync, readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { highlight } from "../../build.mjs";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "../..");
const CAPTURE = join(ROOT, "tests/oracle/capture");
const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', nbsp: " ", apos: "'" };
const decode = (s) => s.replace(/&(#x[\da-f]+|#\d+|\w+);/gi, (m, e) => e[0] === "#"
  ? String.fromCodePoint(/^#x/i.test(e) ? parseInt(e.slice(2), 16) : Number(e.slice(1))) : ENT[e] ?? m);

function runs(inner) { // [{cls, text}] for spans, {cls: null, text} for bare text; adjacent bare text merged
  const out = [];
  const re = /<span class="([^"]*)">([^<]*)<\/span>|([^<]+)|(<[^>]*>)/g;
  for (const m of inner.replace(/<!--[\s\S]*?-->/g, "").matchAll(re)) {
    if (m[4]) throw new Error(`unexpected markup ${m[4]}`);
    if (m[3] !== undefined) {
      const text = decode(m[3]);
      if (out.length && out.at(-1).cls === null) out.at(-1).text += text; else out.push({ cls: null, text });
    } else out.push({ cls: m[1], text: decode(m[2]) });
  }
  return out;
}
const textOf = (inner) => decode(inner.replace(/<!--[\s\S]*?-->/g, "").replace(/<[^>]*>/g, ""));

const slugs = process.argv.slice(2).length ? process.argv.slice(2)
  : readdirSync(CAPTURE).filter((d) => existsSync(join(CAPTURE, d, "dom.html"))).sort();
let blocks = 0, bad = 0;
const seen = new Set();
for (const slug of slugs) {
  const dom = readFileSync(join(CAPTURE, slug, "dom.html"), "utf8");
  for (const m of dom.matchAll(/<code class="language-([\w-]+)">([\s\S]*?)<\/code>/g)) {
    const [, lang, inner] = m;
    const key = lang + "\0" + inner;
    if (seen.has(key)) continue; // the same block on another route
    seen.add(key);
    blocks++;
    const a = runs(inner), b = runs(highlight(textOf(inner), lang));
    const i = a.findIndex((r, k) => !b[k] || r.cls !== b[k].cls || r.text !== b[k].text);
    if (i >= 0 || a.length !== b.length) {
      bad++;
      const k = i >= 0 ? i : Math.min(a.length, b.length);
      const show = (r) => r ? JSON.stringify(r) : "(none)";
      console.log(`${slug} language-${lang} run ${k}: oracle ${show(a[k])} build ${show(b[k])}`);
      console.log(`  text: ${JSON.stringify(textOf(inner).slice(0, 160))}`);
    }
  }
}
console.log(`${blocks} distinct code blocks, ${bad} differ`);
process.exit(bad ? 1 : 0);
