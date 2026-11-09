// npm run vendor [-- <femto checkout> [<commit>]]
//
// Copies femto's dist/, css/ and LICENSE.md into site/vendor/femto/, exactly as committed at HEAD
// of a clean femto checkout (default ../femto), or at <commit> when one is given (a hash, tag or
// ref the checkout holds, such as a release tag: npm run vendor -- ../femto v3.0.0), and records
// where they came from in site/vendor/femto/SOURCE: the commit, the tags that point at it, the refs
// that reach it (so a commit only a backup ref holds is visible as such), femto's version and the
// checkout. femto stays vendored from git, from its release tags once it is published, rather than
// from its npm package (PLAN.md Decision 4, the owner, 2026-11-09). Files are read from git
// objects, never from the working tree, and the folder is replaced entirely. SOURCE has no
// timestamp, so two runs at the same commit and refs write identical files.
//
// Then it prints what to review in the docs, from the commit the old SOURCE named to the new one:
// git diff --stat of femto's README.md, CHANGELOG.md and css/; each README H2 and H3 whose section
// changed, with the docs sections that name it in site/docs/menu.json (their readme key); the
// README H2s no section names; and the readme keys that name no heading. Node built-ins only.
import { execFileSync } from "node:child_process";
import { chmodSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = dirname(fileURLToPath(import.meta.url));
const DEST = join(ROOT, "site", "vendor", "femto");
const PATHS = ["dist", "css", "LICENSE.md"];

function fail(message) {
  console.error(`vendor: ${message}`);
  process.exit(1);
}

const given = process.argv[2];
const wanted = process.argv[3];
const checkout = given ? resolve(given) : resolve(ROOT, "../femto");

function git(args, options = {}) {
  return execFileSync("git", ["--no-optional-locks", "-C", top ?? checkout, ...args], {
    maxBuffer: 256 * 1024 * 1024,
    stdio: ["pipe", "pipe", "pipe"],
    ...options,
  });
}

let top = null;
try {
  top = git(["rev-parse", "--show-toplevel"], { encoding: "utf8" }).trim();
} catch {
  fail(`${checkout} is not a git checkout of femto`);
}

const status = git(["status", "--porcelain"], { encoding: "utf8" }).trimEnd();
if (status) {
  const lines = status.split("\n");
  fail(
    `${top} has uncommitted changes; commit or stash them, then run npm run vendor again:\n` +
      lines.slice(0, 20).map((line) => `  ${line}`).join("\n") +
      (lines.length > 20 ? `\n  ... and ${lines.length - 20} more` : ""),
  );
}

let commit;
try {
  commit = git(["rev-parse", "--verify", "--end-of-options", `${wanted ?? "HEAD"}^{commit}`], { encoding: "utf8" }).trim();
} catch {
  fail(
    `${wanted ?? "HEAD"} is not a commit in ${top}` +
      (wanted ? `; for a tag femto published after this checkout last fetched, run git -C ${top} fetch --tags` : ""),
  );
}
const tags = git(["tag", "--points-at", commit], { encoding: "utf8" }).split("\n").filter(Boolean).sort();
const refs = git(["for-each-ref", "--contains", commit, "--format=%(refname)"], { encoding: "utf8" })
  .split("\n")
  .filter(Boolean)
  .sort();
let version;
try {
  version = JSON.parse(git(["show", `${commit}:package.json`], { encoding: "utf8" })).version;
} catch {
  fail(`no package.json with a version at ${commit} in ${top}`);
}

// Every file under the three paths at the commit: "<mode> <type> <sha>\t<path>", NUL-separated.
const entries = git(["ls-tree", "-r", "-z", "--full-tree", commit, "--", ...PATHS], { encoding: "utf8" })
  .split("\0")
  .filter(Boolean)
  .map((line) => {
    const [meta, path] = line.split("\t");
    const [mode, type, sha] = meta.split(" ");
    return { mode, type, sha, path };
  });
for (const path of PATHS) {
  if (!entries.some((e) => e.path === path || e.path.startsWith(`${path}/`))) {
    fail(`${path} is not committed at ${commit} in ${top}`);
  }
}
const odd = entries.filter((e) => e.type !== "blob" || !["100644", "100755"].includes(e.mode));
if (odd.length) fail(`not plain files: ${odd.map((e) => `${e.path} (${e.mode})`).join(", ")}`);

// Read every blob in one git cat-file --batch call: "<sha> blob <size>\n<bytes>\n" per object.
const batch = git(["cat-file", "--batch"], { input: entries.map((e) => e.sha).join("\n") + "\n" });
let offset = 0;
for (const entry of entries) {
  const eol = batch.indexOf(10, offset);
  const [sha, type, size] = batch.subarray(offset, eol).toString("utf8").split(" ");
  if (sha !== entry.sha || type !== "blob") fail(`git cat-file returned ${sha} ${type} for ${entry.path}`);
  entry.bytes = batch.subarray(eol + 1, eol + 1 + Number(size));
  offset = eol + 1 + Number(size) + 1;
}

// SOURCE names the checkout relative to this repository when it is a sibling or inside it.
const rel = relative(ROOT, top);
const source = isAbsolute(rel) || rel.startsWith(`..${sep}..`) ? top : rel.split(sep).join("/") || ".";
const sourceText = [
  "# Written by npm run vendor (vendor.mjs). Do not edit: run it again to change femto.",
  `commit: ${commit}`,
  `tag: ${tags.length ? tags.join(", ") : "none"}`,
  `refs: ${refs.length ? refs.join(", ") : "none"}`,
  `version: ${version}`,
  `source: ${source}`,
  "",
].join("\n");

// The commit the old SOURCE named, read before the folder is replaced: the review starts there.
let previous = null;
try {
  previous = readFileSync(join(DEST, "SOURCE"), "utf8").match(/^commit: ([0-9a-f]{40})$/m)?.[1] ?? null;
} catch {
  // No SOURCE yet: the first run has nothing to compare.
}

// Write into a temporary sibling, then swap it in, so a failure never leaves a half-written folder.
const staging = join(dirname(DEST), `.femto-${process.pid}`);
rmSync(staging, { recursive: true, force: true });
try {
  for (const entry of entries) {
    const file = join(staging, ...entry.path.split("/"));
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, entry.bytes);
    chmodSync(file, entry.mode === "100755" ? 0o755 : 0o644);
  }
  writeFileSync(join(staging, "SOURCE"), sourceText);
  rmSync(DEST, { recursive: true, force: true });
  renameSync(staging, DEST);
} catch (error) {
  rmSync(staging, { recursive: true, force: true });
  fail(`could not write ${DEST}: ${error.message}`);
}

console.log(
  `vendor: femto ${version} at ${commit.slice(0, 8)} (tag ${tags.length ? tags.join(", ") : "none"}) from ${source}: ` +
    `${entries.length} files into ${relative(ROOT, DEST).split(sep).join("/")}/`,
);

// --- What to review. The copy is done, so nothing below fails the run: a problem is printed instead.

// femto's own contributing guide and license, which the docs do not describe: no section names them.
const UNDOCUMENTED = ["Contributing", "License"];
const short = (c) => c.slice(0, 8);

function has(rev) {
  try {
    git(["cat-file", "-e", `${rev}^{commit}`]);
    return true;
  } catch {
    return false;
  }
}

// README.md's H2 and H3 headings at a commit, in order, each with its section: the lines up to the
// next heading of its level or above, so an H2's section holds its H3s. A heading's text is the line
// after its #s, trimmed, which is what a readme key names. A line inside a fenced code block is never
// a heading. intro is the text above the first heading. null when the commit has no README.md.
function readme(at) {
  let text;
  try {
    text = git(["show", `${at}:README.md`], { encoding: "utf8" });
  } catch {
    return null;
  }
  const lines = text.split("\n");
  const heads = [];
  let fence = null;
  lines.forEach((line, i) => {
    if (fence) {
      const close = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(line)?.[1];
      if (close && close[0] === fence[0] && close.length >= fence.length) fence = null;
      return;
    }
    fence = /^ {0,3}(`{3,}|~{3,})/.exec(line)?.[1] ?? null;
    const m = !fence && /^ {0,3}(#{2,3})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/.exec(line);
    if (m && m[2]) heads.push({ level: m[1].length, text: m[2], line: i });
  });
  const sections = heads.map((h, k) => {
    const end = heads.slice(k + 1).find((n) => n.level <= h.level)?.line ?? lines.length;
    return { ...h, key: `${"#".repeat(h.level)} ${h.text}`, body: lines.slice(h.line + 1, end).join("\n").trimEnd() };
  });
  return { sections, intro: lines.slice(0, heads[0]?.line ?? lines.length).join("\n").trimEnd() };
}

// The ids of the docs sections that name each README heading, by the heading's text: a section's
// readme key (a heading's text; an array of them is read too). A section with no title in
// menu.json, the migration section, whose name criterion 14 keeps out of menu.json, names the text
// of its file's h1 instead, as its nav link takes it (build.mjs, step 3).
function readmeNames() {
  const plain = (html) =>
    html
      .replace(/<[^>]*>/g, "")
      .replace(/&nbsp;/g, " ")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&amp;/g, "&")
      .replace(/\s+/g, " ")
      .trim();
  const menu = JSON.parse(readFileSync(join(ROOT, "site", "docs", "menu.json"), "utf8"));
  const names = new Map();
  for (const section of menu.categories.flatMap((c) => c.sections)) {
    let keys = section.readme === undefined ? [] : [section.readme].flat();
    if (section.readme === undefined && section.title === undefined) {
      const file = readFileSync(join(ROOT, "site", "docs", "sections", `${section.id}.html`), "utf8");
      const h1 = /<h1\b[^>]*>([\s\S]*?)<\/h1>/.exec(file)?.[1];
      if (h1) keys = [plain(h1)];
    }
    for (const key of keys) names.set(key, [...(names.get(key) ?? []), `#${section.id}`]);
  }
  return names;
}

function review(from, to) {
  let names;
  try {
    names = readmeNames();
  } catch (error) {
    console.log(`vendor: could not read the readme keys in site/docs/menu.json: ${error.message}`);
    names = new Map();
  }
  const named = (text) => (names.has(text) ? names.get(text).join(", ") : "no section names it");
  const now = readme(to);
  if (!from) {
    console.log("vendor: there was no SOURCE with a commit before, so there is nothing to compare");
  } else if (from === to) {
    console.log(`vendor: femto was already at ${short(to)}, so nothing changed to review`);
  } else if (!has(from)) {
    console.log(`vendor: the old SOURCE's commit ${short(from)} is not in ${top}, so there is nothing to compare`);
  } else {
    const paths = ["README.md", "CHANGELOG.md", "css/"];
    const stat = git(["diff", "--stat", `${from}..${to}`, "--", ...paths], { encoding: "utf8" }).trimEnd();
    console.log(`vendor: femto's changes from ${short(from)} to ${short(to)}, to review in the docs:`);
    console.log(`  git -C ${source} diff --stat ${short(from)}..${short(to)} -- ${paths.join(" ")}`);
    console.log(stat ? stat.replace(/^/gm, "  ") : "   (no change to these files)");
    const was = readme(from);
    if (was && now) {
      const old = new Map(was.sections.map((s) => [s.key, s]));
      const fresh = new Set(now.sections.map((s) => s.key));
      const indent = (s) => "  ".repeat(s.level - 1);
      // A removed heading is listed where it was: after the last heading before it that remains.
      const after = new Map();
      let last = "";
      for (const s of was.sections) {
        if (fresh.has(s.key)) last = s.key;
        else after.set(last, [...(after.get(last) ?? []), s]);
      }
      const removed = (key) => (after.get(key) ?? []).map((s) => `  ${indent(s)}${s.key} (removed): ${named(s.text)}`);
      const lines = [];
      if (was.intro !== now.intro) lines.push("    (the text above the first H2)");
      lines.push(...removed(""));
      for (const s of now.sections) {
        const before = old.get(s.key);
        if (!before) lines.push(`  ${indent(s)}${s.key} (new): ${named(s.text)}`);
        else if (before.body !== s.body) lines.push(`  ${indent(s)}${s.key}: ${named(s.text)}`);
        lines.push(...removed(s.key));
      }
      console.log(
        lines.length
          ? `  README.md sections that changed, with the docs sections that name them:\n${lines.join("\n")}`
          : "  No README.md section changed.",
      );
    }
  }
  if (!now) {
    console.log(`vendor: femto has no README.md at ${short(to)}, so no readme key in site/docs/menu.json names a heading`);
    return;
  }
  const texts = new Set(now.sections.map((s) => s.text));
  const unnamed = now.sections.filter((s) => s.level === 2 && !UNDOCUMENTED.includes(s.text) && !names.has(s.text));
  const stale = [...names].filter(([text]) => !texts.has(text));
  console.log(
    unnamed.length
      ? `vendor: README H2s no docs section names: ${unnamed.map((s) => s.text).join(", ")}. ` +
          "Name each in a section's readme key in site/docs/menu.json, or write a section for it."
      : `vendor: every README H2 but ${UNDOCUMENTED.join(" and ")} is named by a docs section.`,
  );
  if (stale.length) {
    console.log(
      `vendor: readme keys that name no README heading at ${short(to)}: ` +
        stale.map(([text, ids]) => `"${text}" (${ids.join(", ")})`).join(", ") +
        ". Change each to the README heading its section now covers.",
    );
  }
}

try {
  review(previous, commit);
} catch (error) {
  console.log(`vendor: could not list what to review: ${error.message}`);
}
