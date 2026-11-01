// npm run vendor [-- <femto checkout> [<commit>]]
//
// Copies femto's dist/, css/ and LICENSE.md into site/vendor/femto/, exactly as committed at HEAD
// of a clean femto checkout (default ../femto), or at <commit> when one is given (a hash, tag or
// ref the checkout holds), and records where they came from in site/vendor/femto/SOURCE (PLAN.md
// Decision 4, docs/research/03 §3): the commit, the tags that point at it, the refs that reach it
// (so a commit only a backup ref holds is visible as such), femto's version and the checkout.
// Files are read from git objects, never from the working tree, and the folder is replaced
// entirely. SOURCE has no timestamp, so two runs at the same commit and refs write identical files.
// Node built-ins only.
import { execFileSync } from "node:child_process";
import { chmodSync, mkdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
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
  fail(`${wanted ?? "HEAD"} is not a commit in ${top}`);
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
