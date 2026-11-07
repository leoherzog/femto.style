# femto.style parity harness

This folder proves that the static femto.style matches the Remix site it replaces. The harness loads
each route twice in the real Chrome, Firefox and Safari on the macOS test machine, once from the
oracle (the Remix site at tag `remix-final`) and once from the other side (the oracle again, the
static site in `dist/`, or a fixture), and compares the two documents element by element: the tree,
every attribute, every element's own text and every computed style, pseudo-elements included, plus
the head's title, metas, links, `<base>` and data blocks (the JSON-LD structured data). Any
difference that is not registered in `tests/divergences/` fails the run, and so does a cross-origin
load by the static site or the fixture (criterion 15), which no registry entry can absorb.

It is a port of femto's harness (`../femto/tests/` at femto commit 65453b74): its rig, locks,
browsers, registry, reports, diff rule and selftest. femto compares one fixture page under two
stylesheet lists; this harness compares two documents served by two servers. Nothing here ships.
`PLAN.md` (Parity harness, Divergence categories, Acceptance criteria 1 to 3) is the spec, and
`docs/research/03-static-architecture.md` §7 lists the modes.

## Quick start

```sh
uv run tests/run.py rig                                   # verify the three browsers on this machine
uv run tests/run.py selftest                              # prove detection with negative controls
uv run tests/run.py self                                  # the oracle against itself, fast axes
uv run tests/run.py self --full --plan                    # print the full matrix's cells; starts nothing
uv run tests/run.py self --full                           # criterion 1: the full matrix, three browsers
uv run tests/run.py pages --a dist --b dist --full --routes '/,/docs,/docs?theme=jade,/examples,/does-not-exist'   # criterion 15's run-time loads
uv run tests/run.py styles --full --a static-multipage --b static-femto   # criterion 2, Phase 2's comparison between the tags (Phase 6)
uv run tests/run.py sections --full --a static-femto --b static-one-page  # criterion 2, Phase 3's sections between the tags (Phase 6)
uv run tests/run.py pages --full --a static-femto --b static-one-page --routes /,/examples,/demo,/does-not-exist   # and its whole pages
uv run tests/run.py a11y --target dist                    # criterion 10: axe-core on every page, Chrome and Firefox
uv run tests/run.py a11y --target dist:/path/to/build     # criterion 10 on an agent's own build
uv run tests/run.py registry                              # validate tests/divergences/
uv run tests/run.py oracle                                # build, serve and capture the oracle
uv run tests/run.py static                                # the static checks
uv run tests/static_checks.py --phase 4 --dist /path/to/build              # every static criterion and the link check, on a build
uv run tests/static_checks.py --criteria links --external --dist /path/to/build   # the link check, external links fetched once
uv run tests/run.py behavior --target oracle              # the behavior suite (tests/behavior/), Chrome and Firefox
uv run tests/run.py behavior --target dist --groups shell # one group against the static site
uv run tests/run.py behavior --target dist --browsers safari   # Safari, serialized, on an unlocked screen (the owner's: tests/owner-safari.sh)
uv run tests/run.py behavior --target dist:/path/to/build --browsers chrome,firefox   # criterion 7 on an agent's own build
```

The parity gates of Phases 1 to 3 compared each phase's own build, `dist/` then, with the oracle or
a tag. They are historical: from Phase 4 `dist/` describes femto 3 (PLAN.md Decision 6) and has no
per-route pages, `/demo` or version-picker routes, so it matches neither the oracle nor the tags,
and these commands cannot pass on today's site. They are kept for the record (Harness proof), and
Phase 6 reruns criterion 2's comparisons between the tags instead (above):

```sh
# Historical: dist/ was the phase's own build.
uv run tests/run.py fast --a oracle --b dist --routes /docs/forms,/docs/forms/input   # a Phase 1 route group agent's check
uv run tests/run.py fast --a oracle --b dist:build/forms --routes /docs/forms   # an agent's own build folder
uv run tests/run.py pages --a oracle --b dist --full      # the Phase 1 gate (criterion 2)
uv run tests/run.py styles --full                         # the Phase 2 gate: static-multipage against dist, tokens and states
uv run tests/run.py styles --b dist:build/p2 --routes /docs/button   # an agent's own build, fast axes
uv run tests/run.py sections --full                       # the Phase 3 gate: each section of the one page against its old route at static-femto
uv run tests/run.py sections --b dist:build/p3 --routes /docs/button,/docs/version-picker/jade   # an agent's own build, fast axes
uv run tests/run.py pages --a static-femto --b dist --full --routes /,/examples,/demo,/does-not-exist   # Phase 3's whole pages
```

Every comparison run writes `tests/results/<run-id>/result.json`, `summary.txt` and `log.txt`,
prints the summary, and exits 0 only when nothing unregistered differs and no harness error
occurred.

Python runs only through `uv`: `tests/run.py` carries PEP 723 metadata pinning
`selenium==4.52.0` and `pillow==13.0.0`, the latest on PyPI on 2026-10-30. Selenium Manager fetches
chromedriver and geckodriver into `~/.cache/selenium`; Safari uses `/usr/bin/safaridriver`.

## Layout and ownership

| Path | Owner | Contents |
|---|---|---|
| `README.md` | harness | this file |
| `run.py` | harness | CLI: `uv run tests/run.py <mode> [options]` |
| `harness/` | harness | Python modules, `differ.js` (in-page collector and differ), `host.html` (the host page), `probe.html` (rig probe), and the configuration: `matrix.json` (widths, fast axes, theme routes), `masks.json` (the only masks), `targets.json` (named sides) |
| `harness/oracle.py` | oracle | builds the oracle from tag `remix-final` in `tests/oracle/worktree`, serves it with its locked `wrangler pages dev`, captures every route; `wait_ready()` is side A's readiness hook |
| `oracle-routes.json` | oracle | the oracle's routes: path, kind, kept (Decision 5), title; the 20 static Pico v1 pages are listed as kind `v1-page` (old paths for criterion 6, never captured or compared) |
| `static_checks.py` | static | the mechanical acceptance criteria and the link check (Link check; `run.py static` calls its `main(argv)`) |
| `divergences/` | harness (schema, rig seed); phase agents add entries | divergence registry, `schema.json` |
| `fixtures/` | harness | the selftest site (`site/`, with `site/sections/`, a one-page docs site in miniature for the sections controls), its named controls (`controls.json`) and its state targets for the styles controls (`states.json`) |
| `harness/states.json` | harness | the styles mode's interactive state targets (Tokens and states) |
| `behavior/` | behavior | the behavior suite: `__init__.py` (the `@check` registry and shared in-page helpers) and one module per route group (`shell.py`, `getting-started.py`, `customization.py`, `layout.py`, `content.py`, `forms.py`, `components-a.py`, `components-b.py`, `landing.py`, `one-page.py`, and from Phase 4 `examples.py`); see Behavior |
| `harness/behavior.py` | behavior | the `behavior` mode: its subcommand, the page API checks drive, sessions, runner and report |
| `convert/` | conversion | Phase 1's one-time route converter, which ships nothing (PLAN.md Conversion rules): `convert.py` (an oracle route's captured hydrated DOM into its section file), `highlight-check.mjs` (build.mjs's Prism highlighting against every highlighted code block of the oracle; PLAN.md Risks, Highlighting parity) and its own `README.md` |
| `owner-safari.sh` | owner | the owner's Safari steps (Owner's Safari steps). Only the owner runs it, since it switches macOS's appearance |
| `oracle/`, `results/`, `builds/` | generated | gitignored; `builds/<tag>/` holds a tag's build (`harness/tagbuild.py`) |

Python modules in `harness/`: `cli.py` (modes and the planner), `matrix.py` (legs, widths, routes,
cells), `targets.py` (sides, their servers and readiness hooks), `proxy.py` (the per-session reverse
proxy), `server.py` (the fixture server), `runner.py` (worker pool and session start-up),
`compare.py` (one cell, pixel diff), `browsers.py` (drivers and the color-scheme and input
mechanisms), `registry.py`, `report.py`, `negative.py` (selftest), `rig.py`, `locks.py` (femto's,
unchanged), `paths.py`, `behavior.py` (the behavior mode; Behavior), `styles.py` (the styles mode's
tokens and state replay; Tokens and states), `tagbuild.py` (a tag of this repository built for a
target such as `static-multipage`, `static-femto` or `static-one-page`), `sections.py` (the sections mode's route map and
cells; Sections), `a11y.py` (the a11y mode; Accessibility).

## How one comparison works

A **cell** is one comparison: browser × route × scheme leg × width. Side A's document is
`<base A><route>` and side B's is `<base B><route>`, except in the sections mode, where side B's is
the one docs page at the route's section (`<base B>/docs#<id>`; Sections).

1. The run starts both sides' servers (for `self`, two separate oracle servers, so a server restart
   is covered too), and each browser session gets its own **proxy** on a free `127.0.0.1` port
   (`harness/proxy.py`). The proxy serves the host page at `/__harness/host.html` and forwards
   every other request to the side currently selected, so both documents load on the host page's
   origin.
2. Each browser session opens `/__harness/host.html` once. The host page holds `differ.js` and a
   20 px strip where the pointer parks.
3. For each side (A, then B) Python selects the side on the proxy; the host page empties
   `localStorage` and `sessionStorage` (they belong to the shared origin), stores the leg's theme
   when the leg has one, creates a **fresh iframe** exactly the cell's width and 800 px high, loads
   the route and waits for its `load` event. In Safari the route carries a `harness-load` parameter
   that no other load had, which the proxy removes (The proxy). From the load until the readiness
   hook returns, the host page requests an animation frame every frame (see Rig notes, Chrome: idle
   periods).
4. The side's **readiness hook** runs: `oracle` (`oracle.wait_ready(driver)`, run inside the iframe:
   the Remix router initialized, React attached to `<body>`, the `use100vh` effect run,
   `document.fonts.ready` resolved and two animation frames passed), `static` (the document is
   complete, `document.fonts.ready` resolved and two animation frames passed, with a 100 ms timer
   standing in for a frame where rAF never runs), or `none`. `oracle` and `static` both end with
   the stylesheet check: every stylesheet `<link>` on the document's own origin has a sheet with
   rules (Chrome and Firefox give a stylesheet that answered 404 an empty sheet; control
   `stylesheet-404`). A side that fails a hook or is still not ready after 30 s is loaded once more; the cell records the first attempt under `ready_retries`, and a second
   failure is a harness error. The same holds when the proxy could not get the document from the
   side's server at all (refused, or no answer within the proxy's 60 s; once on 2026-10-30 the
   Safari pass's oracle server took 64 s for one `/demo` request): the iframe then holds the proxy's
   error page, so the hook is not run and the side is loaded once more.
5. It checks the environment inside the document: `innerWidth` equals the width, `(width: Wpx)`
   matches both through `matchMedia` and through a temporary CSS media rule,
   `prefers-color-scheme` matches the leg through `matchMedia` and through CSS, and `data-theme` on
   `<html>` is what the leg asked for (none in the media legs). Any mismatch is a harness error.
6. It finishes transitions and finite animations, pauses infinite ones at `currentTime` 0, reads
   every element's style once (Chrome updates a closed `<details>`' content only when read; see Rig
   notes) and freezes again, then collects the tree, attributes, text and computed styles into the
   host page's memory (below). An animation that starts while the styles are read is a harness
   error.
7. Python reads the proxy's request log for the side: the final document's path and status, and
   any subresource answering 4xx or 5xx (reported per cell, not gating). The collect also returns
   the document's cross-origin loads, read from its own Resource Timing entries and those of every
   frame in it that it can read, and at the end of the cell the proxy hands over the side's CSP
   reports (below, Same-origin loads). The iframe is removed before the proxy switches sides, so
   nothing side A still requests can reach side B's server.
8. On side B the host page aligns the two trees and diffs them **in the page** (the head too, when
   the root is `html`), matches each difference against the registry entries that apply to the cell
   (none in a `self` comparison) and that the in-page breadth guard leaves in force, checks what the
   registered records cover (Divergence registry), and returns only counts and the unregistered
   records (up to `--max-records`, default 300) to Python. If the two documents' final status or path differ,
   Python adds a `status` record.
9. Both sides are screenshotted (the iframe viewport, the top 800 px, with the masked boxes
   covered) and pixel-diffed. Pixel differences are reported, never gating.

In the styles mode the collect also reads the tokens, the diff compares them, and each side replays
its interactive states after its collect (side B after the diff) and before its screenshot (Tokens
and states).

### The proxy

Two servers have two origins, and the in-page collector can only read a same-origin document, so
the proxy puts both sides on one origin per session. It forwards the browser's `Host` header (the
proxy's own `host:port`), so any absolute URL a server builds from the request is the same on both
sides. It asks the server for identity encoding, strips conditional request headers and validators,
and marks every response `Cache-Control: no-store`: the two sides serve different files at the same
URLs (`/favicon.svg`, fonts, stylesheets), and the browser must not reuse one side's file for the
other. Location headers on the server's origin are rewritten to the proxy's. It forwards HTTP only:
no WebSocket, so no live reload reaches the documents.

`no-store` does not cover Safari's speculative loading. When a load starts, WebKit requests the
subresources that the previous load of the same URL used, and keeps the responses for the next
document that asks for them. The first Safari styles runs (`p2-styles-safari-light` and `-dark`,
2026-11-03) show it:
- side B's load of a route made side B's server answer side A's `legacy/` stylesheets with 404s;
- the next load of that route, side A's in the next cell, got those 404s for its own stylesheets
  and rendered without them.

So in Safari each document load gets a URL of its own: the route plus `harness-load=<load tag>.<attempt>`
(compare.py), so WebKit has no earlier load of it to repeat. The proxy removes the parameter before
it forwards or logs the request, so both servers, the request log and the cell's paths see the
route as Chrome and Firefox do. It also puts the parameter back on a redirect's same-origin
`Location`. Chrome and Firefox load the bare route, as before. The page itself can still read the
parameter in `location.search`. Only `picker.js` reads `location.search`, after a swatch click. The
state replays stop every click before the page's listeners see it (States), so that code never
runs. The behavior mode loads one side's server per check, so it has no other side to cross-load
and gets no parameter.

Every response it forwards also carries a report-only Content Security Policy, `default-src 'self'
'unsafe-inline' 'unsafe-eval' data: blob:; report-uri /__harness/csp/<tag>`: it allows everything on
the proxy's origin and reports, without blocking, any load from another origin, tagged with the
side and load it belongs to. A worker script and the frames a document creates get the policy too
(a worker from its own response, `srcdoc`, `about:blank` and `data:` frames from their creator), so
the reports reach what the page's Resource Timing cannot: a worker's own loads, a frame in a closed
shadow root, a load that fails at the network level, an image Firefox serves from its cache (Same-origin
loads).

### Alignment and record kinds

An element's **tree path** names it in records: from `html`, each step is the element's tag and its
index among its parent's compared element children. With `--root-a`/`--root-b` only the root
element's subtree is compared, and its paths still start at `html` (the root's own path in its
document, then down), so a registry path pattern means the same in a section comparison as in a
whole-page one. The sections mode's side B root is no selector: it is
`document.getElementById(id).closest("section")` for the cell's section id, and a missing one is a
harness error (`root section around #<id> (...) not found`).
`head`, `meta`, `title`, `script`, `link`, `style`, `template`, `base` and `noscript` are skipped in
the tree and never counted, so a different number of scripts or stylesheet links never shifts an
index. An open shadow root's children are a separate list (path step `#shadow`). Paths read
`html > body:0 > main:1 > section:0 > p:3`, each side's own (a record carries side B's path, and
`path_a` too where the two differ).

Two sibling lists are **aligned by a keyed longest common subsequence**, in three passes, each run
on the gaps the one before left:

1. whole-subtree signatures: a hash of the tag, the attributes, the own text and the children's
   signatures, with masked parts left out, so identical subtrees anchor first;
2. the tag plus `id`, `class`, `type`, `name` and `role`;
3. the tag alone.

The common prefix and suffix are matched first, so equal lists cost one pass. Whatever a gap still
holds pairs by position (another tag there is a `tag` record), and the rest is `only-a` or
`only-b`. So an inserted or removed element is one `structure` record naming that element, and its
later siblings still pair with their true counterparts: a paragraph inserted first in `<main>` on
`/docs/table` is one `only-b` record plus the taller ancestors' heights, and a changed table cell
below it is still a `text` record. The alignment only decides which elements pair; each pair is
compared in full, so a poor alignment can add records but never hide a difference. A middle part
larger than 4 million table cells (after the prefix and suffix) pairs by position instead and is
counted under `align_fallbacks`.

| Kind | When | Fields |
|---|---|---|
| `structure` | an element on one side only (`change: only-a` or `only-b`; its subtree has no counterpart), or two elements paired with different tags (`change: tag`: their attributes and styles are not compared, their own text and every child still are) | `path`, `label` (side B's element, else side A's), `label_a` and `path_a` (tag changes), `a` and `b` (the tags, `null` when absent), `size_a` and `size_b` (elements in each subtree) |
| `attribute` | an attribute's value differs or it exists on one side only | `path`, `label`, `prop` (the name), `a`, `b` (`null` when absent) |
| `text` | the element's own text differs: its child text nodes, joined as they are where its `white-space-collapse` preserves whitespace; elsewhere read run by run, each run's whitespace one space where it renders and nothing where it collapses (Collection) | `path`, `label`, `a`, `b` |
| `style` | a computed longhand of the element or a pseudo-element differs | `path`, `label`, `pseudo`, `prop`, `a`, `b` |
| `head` | the document's title, a `<meta>`, a `<link>` other than a stylesheet or fetch hint (`preload`, `modulepreload`, `prefetch`, `preconnect`, `dns-prefetch`, `prerender`), a `<base>`, or a data-block `<script>` (any `type` that is not JavaScript or `module`: the oracle's `application/ld+json`, an `importmap`) differs or exists on one side only; compared when the root is `html` | `path` (the key: `title`, `meta[name=description]`, `meta[property=og:url]`, `link[rel=canonical]`, `link[rel=icon][sizes=...]`, `base`, `script[type=application/ld+json]`, `#2` for a repeat; an exact copy of an earlier data block is no repeat, see Collection), `prop` (`text` for the title, else the attribute; `(element)` for one with no other attribute; for a JSON data block one per leaf, `$.version`, `$.author.name`, `$.keywords[2]`, with the value JSON-encoded, so key order and whitespace never count; `(text)` for a data block that is not JSON or does not parse), `a`, `b` |
| `status` | the final document's status or path differs (a redirect or a 404 on one side) | `path` (the route), `a`, `b` (`"200 /docs"`) |

### Collection

- Every element in tree order from the root, open shadow roots included, minus the skipped tags.
  Each element is named by its path, with a readable label (`input#email[type=email] "..."`).
- The head, when the root is `html`: `document.title`, the attributes of every `<meta>`, of every
  `<link>` that is not a stylesheet or fetch hint and of `<base>`, and every data-block `<script>`
  (attributes and content, JSON leaf by leaf), keyed as in `head` records. Like the oracle's, they
  are read from the whole document outside `<template>`, wherever they sit. On the oracle every
  route but `/docs/v1` and the 404 has one `application/ld+json` block.
- **Exact copies of a data block count once.** A data block whose key, attributes and content (its
  JSON leaves, or its text) equal an earlier one's is not a `#2` entry: an identical copy adds no
  data. The oracle needs this rule: on `/docs/progress` the hydrated head holds the JSON-LD block
  once on some loads and twice on others. The route renders a random progress value
  (`useState(randomProgressValue())`, `app/routes/docs.progress.jsx`); when the server's and the
  client's values differ, hydration fails (React's error #418) and React's client render inserts a
  second, identical block, and when they happen to agree it does not. Round 2 claimed two blocks on
  every load; the third review found one block in 6 of 200 loads (Harness proof, Round 3). Each
  side records the copies it collapsed under `head_repeats` (the summary counts the documents that
  had one), so they are visible, never hidden. A second block that differs in anything, one leaf
  included, is still its own `#2` entry and compared leaf by leaf (controls `head-data-copy` and
  `head-data-near-copy`). Metas and links keep their repeat numbering: a second canonical link is a
  `#2` record. The rule applies on both sides (a `self` run's side B is the oracle too), so a page
  of `dist/` that wrote its JSON-LD twice would pass as well; `head_repeats` and the summary's
  `head data blocks` line show it per side, and `result.json` lists the rule under `value_rules`.
  PLAN.md's Parity harness names it beside the three masks and the `blob:` rule ("Counted once";
  accepted by the owner, 2026-10-31).
- Requests (criterion 15): `performance.getEntriesByType("resource")` of the document and of every
  frame inside it that the page can read (same-origin iframes, `srcdoc` and `about:blank` frames,
  objects and embeds, at any depth, and those in open shadow roots, declarative ones included,
  which `window.frames` leaves out), each document's own network log, read when the styles are:
  every http(s) URL on another origin than the top document's. It lists what loaded, whatever
  started it (markup, a script-inserted `<link>` or `<img>`, `fetch()`, CSS `url()`, fonts), and
  never a URL that is only text. A frame it cannot read (another origin, or sandboxed without
  `allow-same-origin`) is listed per side under `frames_unreadable`; `frames_read` counts the
  others. The proxy's CSP reports of the side's load are added at the end of the cell (side A's
  have side B's whole load to arrive; one that arrives later still goes to its cell, by its tag):
  a reported URL that Resource Timing did not list joins the side's `cross_origin` and
  `csp_cross_origin`, `csp_reports` counts them, and a report whose blocked URI is not a URL
  (`inline`, `eval`: the policy itself would be wrong) is kept under `csp_other`. Same-origin loads,
  below, judges them.
- Attributes: the full set, names and values, compared exactly.
- Text: the element's own text (not its descendants'), so a changed word is reported on the element
  that holds it. Where the element preserves whitespace (`pre`, `pre-wrap`, ...) its text nodes are
  joined as they are. Elsewhere they are read run by run: a run is a stretch of adjacent text nodes
  (a comment between them, React's `<!-- -->` separator, renders nothing and does not end it), and
  an element child ends it. A whitespace-only run, or a run's leading or trailing whitespace, counts
  as one space when the browser gives it a box of nonzero inline size (a `Range` client rect wider
  than 0; taller in a vertical writing mode) and as nothing when it collapses away, and whitespace
  inside a run's text collapses to one space. Probed in Chrome Beta 158 and Firefox 160 (round 1 of
  the Phase 1 fixes): whitespace between inline boxes, and before or after text next to an inline
  element, has a rect of the space's width; whitespace between blocks, flex or grid items, table
  parts, `<option>`s or SVG shapes has none, and whitespace that collapses after another space, at
  a line's start or end, or at a wrap point has rects of width 0. So a space that shows between two
  inline siblings is compared (the footer's two inline `<p>`s had one the oracle lacks, found by the
  Phase 1 gate review), and source whitespace that renders nothing (a hand-indented page against
  React's unindented markup) is not. The old rule joined, collapsed and trimmed the text, so it
  compared no whitespace-only run and no space at either end of an element's text (control
  `whitespace` FAILs with it, `p1f1-selftest-ws-oldrule`). Whitespace here is space, tab and line
  feed: CSS's document white space (CSS Text 3, section 4) less the carriage return, which CSS
  treats as a space but Firefox 160 renders as nothing (fix round 2's review, `adv-p1f2-1`), so a CR
  is text, compared exactly. Parsing turns every source CR into a line feed, so a CR in the DOM
  comes only from `&#13;` or a script. A no-break space (U+00A0), U+FEFF and the other Unicode space separators never
  collapse, so they are text, compared exactly: `Code&nbsp; licensed` is not `Code licensed`, and an
  `&nbsp;` run is never read as a collapsible space. Form feed is not document white space either
  (CSS renders it as a visible glyph). Round 1's rule used JavaScript's `\s`, which matches U+00A0,
  so a visible extra no-break space gave no `text` record (adversarial review of round 1; control
  `whitespace-nbsp` FAILs with it, `p1f2-selftest-nbsp-oldrule`). The class and `rel` token lists
  that key the alignment and the head records split on ASCII whitespace, as the DOM does, for the
  same reason. `result.json` lists this rule under `value_rules`.
- Properties: every name `getComputedStyle()` enumerates on `<html>`, minus custom properties
  (Chrome Beta 158: 480, Firefox 160: 394 longhands; Safari 27 enumerated 419 in femto's run).
- Pseudo-elements, as femto collects them: `::before` and `::after` on every element (when `content`
  computes to `none` or `normal` on both sides it is skipped; on one side only it is a difference on
  `content`); `::marker` on `li`, `summary` and anything whose `display` contains `list-item`;
  `::placeholder` on elements with a `placeholder` attribute; `::file-selector-button` on
  `input[type=file]`; `::backdrop` on every `dialog`. Each session verifies on `probe.html` which of
  these `getComputedStyle()` supports; an unsupported one is skipped and recorded as the skipped
  check `pseudo:<name>`, which must be registered.
- Animations: `document.getAnimations()` plus each shadow root's. Finite animations and transitions
  are `finish()`ed, infinite ones paused at 0, three rounds until nothing changes. Then every
  collected element's style, `::before` and `::after` are read once and the freeze runs again, so a
  transition that only a read starts (Chrome's closed `<details>` content) is finished too; each side
  records the three freeze counts under `freeze`, and an animation that starts after that, while
  the styles are read, is a harness error. An animation of an element whose every animated longhand
  a mask leaves uncompared on it is frozen too but counted apart (`masked`) and is no error: in
  Safari 27.2 the oracle's theme-toggle icon can start its transform transition after the first
  freeze (masks `oracle-theme-toggle`, and `oracle-maintenance-notice` for the banner link's color).
  A transient `input[type=file]::file-selector-button { transition: none !important }` cancels the
  transitions Chrome and Safari run on a UA shadow element that `getAnimations()` does not return.
- Custom properties (tokens) are not compared in the pages mode: their effects are in the computed
  styles. The `styles` mode adds femto's token comparison and interactive states (Tokens and states).

### Same-origin loads

A target marked `same_origin` in `targets.json` (`dist` and the fixture) must load only same-origin
resources (PLAN.md criterion 15). Every cross-origin URL in such a side's Resource Timing entries is
a `cross_origin_loads` item of its cell and fails the run. It is not a diff record, so no registry
entry can absorb it, and the summary lists it under `CROSS-ORIGIN LOADS`. URLs on
`https://femto.style` (that scheme, host and default port only, as `static_checks.same_origin()`
reads it: `http://femto.style` and `https://femto.style:8443` are other origins and fail) are the
site's own origin once deployed: they are kept per side under `site_origin_loads`, listed in the
summary under `CROSS-ORIGIN LOADS` as loads from the deployed site and in `result.json`
(`site_origin_loads`), and never fail. A full Resource Timing buffer (250 entries in one document,
past which the browser drops entries), an unreadable one, or a frame whose entries cannot be read is
a harness error on such a side. Other targets (the oracle) are only reported, under
`cross_origin_reported`: the oracle's `/docs/css-variables` loads Google Fonts. A worker keeps its
own network log, which no page can read: the proxy's CSP reports show its loads (and those of a
frame in a closed shadow root), and `static_checks.py` also reads every script started in a worker
strictly (any absolute URL of another origin there fails); otherwise it checks the markup, the CSS
and JS imports statically and only lists the other absolute URLs in JS, which this check decides
(`p0r2-rt-probe`, in Rig notes, shows what each browser lists; `p0r4-rt-frames` and
`p0r4-rt-nested`, round 4, what the CSP reports add; Known limits). A load from a CSP report fails
like any other, with `via` naming the report's directive and document in `cross_origin_loads`.

### Masks

`harness/masks.json` holds the only masked areas, PLAN's five (the random progress value in three
entries), and every run copies them into
`result.json` (`masks`) with the number of elements each covered (`masked_elements`, and per cell
under `sides`). A mask applies to an aligned element when its selector matches it on either side.
Masked parts are also left out of the alignment's subtree signatures.

| Mask | Selector | What is not compared |
|---|---|---|
| `spinner` | `[aria-busy=true]` | pixels only (its SVG animation cannot be frozen; its computed styles stay compared) |
| `typing-demo` | `.demo > article.component` | its contents: descendants and own text are not collected; the article's own attributes and styles (its height is fixed) stay compared; pixels covered |
| `progress-value` | `article[aria-label="Progress example"] > progress` | the `value` attribute; pixels covered |
| `progress-value-code` | `article[aria-label="Progress example"] > footer > pre > code > :nth-child(1 of .attr-value:not(.punctuation))` | the one token that prints the value (`value="NN"` comes before `max="100"`): its text, and the `transform-origin` and `perspective-origin` Firefox derives from its size. Every other token, its classes, the `pre` and the copy button stay compared. The screenshot covers the whole `pre`, since the digits shift the rest of the line |
| `progress-value-code-width` | `article[aria-label="Progress example"] > footer > pre > code` | the code's `width` and `inline-size`, and the `transform-origin` and `perspective-origin` that follow them (Phase 6). From Phase 4 the sample is longer than its `pre` at 375 px, and femto's `pre > code { min-width: min-content }` (`css/content/code.css:47-50`) makes the code as wide as its line, so a one-digit value makes it one character narrower than a two-digit one: 344.5 against 352.906 px in Chrome (`p4-gate-loads-1`, `p6-gate-loads-1`). Its height, its other styles and every token but the value stay compared; no pixels key, since `progress-value-code` covers the `pre` |
| `oracle-theme-toggle` | `svg.icon-theme-toggle *` | `transform` and `d` on the parts of the oracle's animated toggle icon; pixels covered. React adds `moon` after hydration when the page is dark, and the circle and rays then scale over 260 ms; in Safari 27.2 the transition can start after the freeze, so the oracle differed from itself (`p0-self-safari-light-locked`, 2026-11-01: 36 records in 18 theme-dark cells on a light OS, and 6 harness errors on `/docs/forms/input`). The site has an emoji instead (PLAN Decision 16); everything else about the SVG stays compared, and in `pages` its parts are registered `owner-change` records |
| `oracle-maintenance-notice` | `div.maintenance-notice > a` | `color` and the 15 longhands that follow `currentColor` (`caret-color`, `column-rule-color`, `outline-color`, `text-decoration-color`, `text-emphasis-color`, `-webkit-text-fill-color`, `-webkit-text-stroke-color` and the 8 border colors) on the link in the oracle's maintenance banner; pixels covered. The banner takes the inverse theme, and React sets its `data-theme` after hydration, so on a dark page it flips from dark to light and the link's colors transition over 0.2 s. Safari 27.2 once read it mid-transition without the freeze seeing a transition (`p0-self-safari-dark`, 2026-11-01: 16 records in `/docs/link` dark 375, no harness error). The site drops the banner (PLAN Decision 5, `p1-shell-maintenance-notice`); the banner, its `data-theme`, the link's text and its other styles stay compared |

Mask fields: `contents` (descendants and own text not collected), `text` (the text of the element
and its descendants not compared), `attributes` and `properties` (these attribute names and computed
longhands not compared on the element), `pixels` (`true` covers the element on both screenshots; a
selector string covers that selector's boxes instead).

### Diff rule

Values compare as exact strings, except colors in computed styles: `rgb()`, `rgba()`,
`color(srgb ...)`, hex and named colors are parsed and compared numerically with a tolerance of
1/255 per channel and 0.004 alpha, and the rest of the value (with each color replaced by a
placeholder) must be identical. Colors inside quoted strings and `url()` are text. Attributes,
text, tags and statuses compare exactly. `result.json` lists the rules in force (`value_rules`), with
the two collection rules that are always on: element text as Collection reads it, and exact copies
of a data block counted once.
Apart from the two rules below, no other tolerance exists; the selftest proves that a 2/255 change
is detected and a 1/255 change is not.

**`blob:` URLs are normalized** (the owner's decision, 2026-10-30). The oracle's `/docs/colors`
Download button links to a `blob:` URL made on load (`URL.createObjectURL` of the palette JSON). Its
UUID is random for every document, so compared exactly the oracle never equals itself there (one
`attribute` record, `href` on `a[download]`, in every `/docs/colors` cell). So by default a value
rule compares a `blob:` URL's UUID as a placeholder and the rest of the value, origin included,
exactly; `value_rules` lists it. It is a value rule, not a mask: the link, its text, its other
attributes and its styles are still compared, and PLAN.md's three masks stay the only masks.
`--exact-blob-urls` turns the rule off (the run then logs a `cap:` line);
`--blob-uuid-placeholder`, the old opt-in, is still accepted and does nothing.

**The oracle minifier's spellings are normalized** (the owner's decision, 2026-11-02). The oracle's
stylesheets went through clean-css, which writes some values differently from the source it was
given, and femto's are not minified. In Phase 2's first full styles gate (`p2-gate-styles-full-1`)
these were the only unregistered records left: 675,780 of them, all equal once normalized. So by
default (`differ.js` `sameRaw`, `sameMinified`):
- a token's raw text compares without a `0` before a decimal point and without the whitespace after
  a comma (`.25rem` and `0.25rem`, `rgba(0,0,0,.25)` and `rgba(0, 0, 0, 0.25)`; 444,288 records);
- `outline-width` compares only when `outline-style` is not `none` on both sides: clean-css writes
  `outline: none` as `outline:0`, so one side reads `0px` and the other `medium` (`3px`), and neither
  draws an outline (215,184 records, on links, buttons, summaries and inputs, in every state);
- `background-position` and its `-x` and `-y` longhands compare `0px` as `0%`: clean-css writes
  `background: none` as `background:0 0`, whose position reads `0px 0px` against `0% 0%` (16,308).

Everything else in those values stays exact, and a token's resolved values through the probe
properties are compared as before. `--exact-minified` turns the rule off (a `cap:` line).
Controls `minified-equal`, `minified-exact` and `minified-real` prove that it hides these spellings,
that they are found without it, and that real changes written the same way are still found.

## Modes

Common options for `self`, `pages`, `fast`, `styles` and `sections`: `--browsers chrome,firefox,safari`, `--routes`,
`--widths`, `--schemes light,dark,theme-light,theme-dark` (those legs on every route instead of the
matrix's legs), `--no-shots`, `--workers chrome=2,firefox=2`, `--max-records N`, `--run-id`,
`--label`, `--registry DIR`, `--exact-blob-urls` and `--exact-minified` (see Diff rule), and `--plan`
(print the planned cells per browser and exit, starting no server and no browser). `pages` and `fast` take `--a` and `--b` (a named target, `dist:<path>` or a base URL),
`--ready-a`/`--ready-b` (`oracle`, `static`, `none`) and `--root-a`/`--root-b` (CSS selectors of the
alignment roots). Without `--routes` the routes are the oracle's kept routes from
`tests/oracle-routes.json` (the sections mode: side A's docs routes).

The same target on both sides of `pages`, `fast` or `styles` (`--a static-femto --b static-femto`) is a
self comparison: no registry entry but a skipped check applies, so every difference counts. Otherwise
a run is the comparison its side A names in `targets.json` (`comparison`): `static-femto` makes a
pages run a `one-page` comparison, and every other side A a `pages` one; the styles mode is `styles`
and the sections mode `one-page`. The comparison decides the registry entries that apply (Divergence
registry, Comparisons).

| Mode | What it runs |
|---|---|
| `rig` | Starts each browser (`--browsers`, default all three) and reports versions, pseudo-element support, the six widths, each scheme leg's mechanism, screenshot timing and input checks to `results/<run>/rig.json`. |
| `self` | The oracle against itself, from two separate oracle servers (`--one-server` for one). Fast axes; `--full` runs the full matrix (acceptance criterion 1). |
| `pages` | `--a` against `--b`. Fast axes; `--full` runs the full matrix (criterion 2 at each parity gate). Phase 1 runs `pages --a oracle --b dist`. |
| `fast` | For agents: Chrome and Firefox at widths 375 and 1300 (PLAN.md, Fast mode), with the matrix's legs for each route. `--self`, or `--a` and `--b`. The same as `self` or `pages` without `--full`. |
| `selftest` | The negative controls (below), each a real `run.py pages` subprocess. `--cases`, `--browsers`. |
| `registry` | Validates `tests/divergences/` and lists the entries by category. Every comparison run validates them again (a registry error is a harness error). |
| `oracle` | `harness/oracle.py`'s `main(argv)`: build the oracle if missing or stale, serve it, capture every route into `tests/oracle/`. |
| `static` | `tests/static_checks.py`'s `main(argv)`: every criterion it can check without a browser, and the link check (Link check). `--dist DIR` reads a built folder instead of `dist/` (criterion 5 then builds into it, never into `dist/`), `--criteria 9,13,links` some of them, `--external` fetches the external links. |
| `styles` | The Phase 2 gate (criterion 2), femto's native mode ported to this site: one document, two stylesheet lists. `--a` (default `static-multipage`, the tag's build: the frozen legacy CSS) against `--b` (default `dist`: vendored femto, the responsive-spacings option and the site CSS). Phase 2 changes no markup apart from the stylesheet links, so the two documents align element for element, and everything `pages` compares is compared (tree, attributes, text, computed styles, head, status, same-origin loads, with the same routes, legs, widths, masks, value rules, chunking, Safari handling and `--full` matrix), plus femto's tokens and interactive states (Tokens and states). `--states FILE` replaces `harness/states.json`, `--no-states` replays none (a `cap:` line). The same target on both sides (`--a static-multipage --b static-multipage`) is a self comparison: no registry entry but a skipped check applies, the mode's criterion-1 check. A styles comparison applies only the registry entries that name it (Divergence registry). Fast axes; `--full` runs the full matrix. |
| `sections` | The Phase 3 gate (criterion 2; Sections): each old docs route of `--a` (default `static-femto`) against its section of the one page of `--b` (default `dist`), side A's `[role=document]` (`--root-a`) against the `<section>` around the element with the section's id, loaded at `/docs#<id>` (a color route at `/docs?theme=<color>#version-picker`). Its routes and their sections come from side A's `menu.json` at the tag. A `one-page` comparison; everything else is the pages mode's (legs, widths, masks, value rules, chunking, Safari handling, same-origin rule, `--full` matrix). Fast axes; `--full` runs the full matrix. |
| `behavior` | Scripted checks of every widget in 01 §2 that Phase 1 rebuilds, against one target (`--target oracle`, `dist`, `dist:<path>` or a base URL), in headless Chrome and Firefox, and in Safari with `--browsers safari` (serialized, the OS scheme and, from Phase 6, the OS motion only, on an unlocked screen: the owner's); see Behavior. Phase 3 adds the docs spy, `#hash` and history behavior and `?theme=` (criterion 7), growing from the spike's `test_spike.py`. |
| `a11y` | Criterion 10 (Accessibility): axe-core from `node_modules/axe-core` run in every page of one target (`--target`, default `dist`): `/`, `/examples`, the 404 page, `/docs` and `/docs?theme=jade` (until Phase 4 also `/demo`), in headless Chrome and Firefox, light and dark, at 375 and 1300. A serious or critical violation fails the run; moderate and minor ones are listed. `--pages`, `--browsers`, `--schemes`, `--widths`, `--plan`. |

Named targets (`harness/targets.json`):

| Target | Side | Readiness |
|---|---|---|
| `oracle` | the Remix site at `remix-final`, built if needed and served by `oracle.serve()` | `oracle` |
| `dist` | its `one_page` is `/docs` (the sections mode's side B); `npm exec --no -- wrangler pages dev dist` on free ports, with the wrangler pinned in `package.json` (`--no` never downloads one; before starting, the harness checks that `node_modules/wrangler` is the exact version `package.json` pins, else exit 2), its debug log and its own `--persist-to` state folder in the run's folder; needs `dist/index.html`; `same_origin` | `static` |
| `dist:<path>` | any built folder, served exactly as `dist` serves `dist/`: the same wrangler, options, readiness and same-origin rule; `<path>` is absolute or relative to the repository root, and needs `<path>/index.html`. Several agents can each compare their own build at once (`fast --a oracle --b dist:build/forms`), since every server has its own ports, log and state folder. The folder's pages are also reference documents for the registry's breadth rule, like `dist/`'s | `static` |
| `static-multipage` | the static site at tag `static-multipage` (the Phase 1 commit), built by the harness into `tests/builds/static-multipage/dist` (gitignored) and served exactly as `dist` serves `dist/`; `same_origin`. The build (`harness/tagbuild.py`): a detached `git worktree add` of the tag's commit in a temporary folder, the repository's `node_modules` linked into it, `node build.mjs --out <folder>`, then `git worktree remove --force` and `git worktree prune`. `build.json` beside the folder records the tag, commit, Node version, the prismjs version the build highlighted with (`node_modules/prismjs/package.json`, 1.30.0), file count, a SHA-256 of the built tree (every file's path and content) and seconds (0.3 s on 2026-11-02: 187 files). A run rebuilds when the folder's `index.html` or `build.json` is missing, the tag's commit is not the recorded one, the repository's prismjs is another version, or the folder no longer hashes to the recorded tree (a file under it edited, added or removed); the server start checks all of it again; `tests/builds/static-multipage.lock` is held exclusively by a build and shared by every server of the folder, so two runs never build at once and none rebuilds under a running server. `result.json` records `sides.<a|b>.build` | `static` |
| `static-femto` | the static site at tag `static-femto` (the Phase 2 commit, 7587a7e: one page per oracle route, styled by vendored femto), built by `tagbuild.py` into `tests/builds/static-femto/dist` (gitignored) exactly as `static-multipage` is (the same worktree build, `build.json`, rebuild rules and `tests/builds/static-femto.lock`) and served exactly as `dist` serves `dist/`; `same_origin`. Side A of Phase 3's comparisons: the sections mode reads its routes from the tag's `site/docs/menu.json` (`menu`, read with `git show`), and its `comparison` is `one-page`. 0.3 s, 166 files on 2026-11-04 | `static` |
| `static-one-page` | the static site at tag `static-one-page` (the Phase 3 commit, 7b90883, "Merge Docs Into One Page": the one docs page before Phase 4 rewrote it), built by `tagbuild.py` into `tests/builds/static-one-page/dist` (gitignored) exactly as `static-femto` is, and served exactly as `dist` serves `dist/`; `same_origin`. Its `one_page` is `/docs` (no `menu`, no `comparison`). Side B of Phase 3's comparisons when Phase 6 reruns them between the tags (owner decision 18): `sections --a static-femto --b static-one-page` and `pages --a static-femto --b static-one-page`. 118 files on 2026-11-06 | `static` |
| `fixture`, `fixture:<control>` | the selftest site, optionally changed by a control from `fixtures/controls.json`; `same_origin`; its `menu` and `one_page` are the sections fixture's (`fixtures/site/sections/menu.json`, `/sections/docs.html`) | `static` |
| a base URL | a server someone else runs (`http://127.0.0.1:8788`); nothing is started or stopped | `static` unless `--ready-a`/`--ready-b` |

Every named target a run uses is started once per side and stopped with all its children (the
oracle's wrangler and workerd included) when the run ends, also on Ctrl-C or SIGTERM. `result.json`
records each `dist` side's folder (`sides.<a|b>.dir`) and wrangler (`version`, `source`, `pin`).

`FEMTO_WRANGLER=<path to a wrangler executable>` replaces the repository's wrangler for the `dist`
targets. It is only for testing the harness before the repository has one (round 3 used a scratch
install of wrangler 4.156.0 for that); every run that uses it says so in a `cap:` line, so a gate
run with it shows as such.

### Scheme legs

| Leg | `prefers-color-scheme` | `data-theme` on `<html>` |
|---|---|---|
| `light` | light | none |
| `dark` | dark | none |
| `theme-light` | dark | light (forced light on a dark OS) |
| `theme-dark` | light | dark (forced dark on a light OS) |

Chrome emulates the media query with CDP, Firefox with its content pref (see Rig notes). A
data-theme leg does not set the attribute itself: before the load it stores the theme in
`localStorage.femtoColorScheme` as JSON (`"dark"`), as the site's own color-scheme switch does
(Decision 14), and the page's own script sets `data-theme` on `<html>`. The environment check then
requires the attribute; a page that ignores the stored choice is a harness error, not a difference.
`matrix.json` (`theme_storage`) holds the key and format.

Safari cannot emulate the media query: it runs the OS scheme in every leg, skips the leg whose media
differs from the OS when no `data-theme` is set, and records `media:<scheme>` as a skipped check,
registered in `divergences/rig.json` (`safari-no-media-dark`). Every Safari gate therefore runs
twice, once with macOS light and once with macOS dark; together the two passes run every leg.

### Safari dark pass

Agents never change the macOS appearance, so the owner does this step. (When macOS is set to the
Auto appearance it turns dark by itself at sunset; on 2026-10-30 it did at about 18:45, and round 1
ran the dark pass then without touching any setting; Harness proof.) Quit Safari first (Cmd-Q;
safaridriver sessions never start while your own Safari is open), and leave the machine alone while
it runs. Switch macOS to dark:

```sh
osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to true'
```

Then run the gate's Safari commands again, for example Phase 0's (criterion 1):

```sh
caffeinate -d -i uv run tests/run.py self --full --browsers safari --run-id p0-self-safari-dark
uv run tests/run.py selftest --browsers safari --cases self,dark-only,theme-dark-only --run-id p0-selftest-safari-dark
```

and at a parity gate, for example Phase 1's:

```sh
caffeinate -d -i uv run tests/run.py pages --a oracle --b dist --full --browsers safari --run-id p1-pages-safari-dark
```

Check that the session's `log.txt` line says `OS scheme dark` and that the skipped checks show
`media:light`, not `media:dark`; a session that read a light OS skips the dark cells instead of
passing them. Then switch back:

```sh
osascript -e 'tell application "System Events" to tell appearance preferences to set dark mode to false'
```

The selftest controls pinned to the light leg (all but `self`, `dark-only` and `theme-dark-only`)
compare nothing on a dark OS and report FAIL, so run `selftest --browsers safari` in full in the
light pass. `caffeinate -d -i` holds a display-awake assertion only while the harness runs and
changes no setting.

### The full matrix and its reductions

The full matrix (`--full`, `matrix.json`):

- Browsers: Chrome Beta, Firefox and Safari. Chrome and Firefox run 2 sessions each, Safari 1 (one
  Safari session at a time machine-wide).
- Widths: 375, 600, 800, 1100, 1300 and 1600, one inside each breakpoint band, exact in all three
  browsers (the iframe sets them).
- Legs: `light` and `dark` on every route; `theme-light` and `theme-dark` also on the theme routes
  in `matrix.json`, the kitchen-sink equivalent: `/`, `/docs`, `/docs/typography`, `/docs/button`,
  `/docs/table`, `/docs/forms/input`, `/docs/dropdown` and `/docs/version-picker/jade`. Together they
  hold every color-bearing element kind the site uses: the landing page with its hero, demo,
  features and comparison, the docs shell, text and code, every button variant, tables, form
  controls with validation states, dropdowns and nav menus, and one themed color route.
- Routes: the oracle's kept routes, 54 of its 64 (`oracle-routes.json`, `kept: true`); the 10
  Decision 5 routes are left out and logged as a cap: `/docs/classless`, `/docs/conditional`,
  `/docs/sass`, `/docs/maintenance`, `/docs/v2`, `/docs/mission`, `/docs/usage-scenarios`,
  `/docs/brand`, `/docs/built-with`, `/docs/v1/`. The kept routes include the 404 page
  (`/does-not-exist`).

Every reduction is printed as a `cap:` line in `log.txt` and stored in `result.json` (`caps`):
command-line filters (`--browsers`, `--routes`, `--widths`, `--schemes`) and the fast axes.

Planned with the harness's own planner (`uv run tests/run.py self --full --plan`, which starts no
server and no browser) on 2026-10-30:

| Browser | Cells | light | dark | theme-light | theme-dark | Per width |
|---|---|---|---|---|---|---|
| Chrome | 744 | 324 | 324 | 48 | 48 | 124 |
| Firefox | 744 | 324 | 324 | 48 | 48 | 124 |
| Safari | 744 | 324 | 324 | 48 | 48 | 124 |

That is 2,232 cells. On a light OS, Safari's 324 `dark` cells are the registered skip
`media:dark` and 420 run; the owner's dark pass runs the 324 `dark` cells and skips the `light`
ones. Its `theme-light` cells run with light media on a light OS (a `media:dark` skip is recorded on
each) and with dark media in the dark pass. The fast axes plan 248 cells per browser in Chrome and
Firefox (54 routes × light and dark × 2 widths, plus 8 theme routes × 2 theme legs × 2 widths).

### Sections

The sections mode is Phase 3's gate (PLAN.md Workflow, 3 One page; criterion 2): the one docs page
(Decision 2) holds every docs section, so each old route of the Phase 2 site is compared with its
section rather than with a page of its own.

```sh
uv run tests/run.py sections --full --browsers chrome,firefox      # the gate, Chrome and Firefox
uv run tests/run.py sections --b dist:/path/to/build --routes /docs/forms/input,/docs/version-picker/jade
uv run tests/run.py sections --plan                                # the planned cells; starts nothing
```

- **Sides.** Side A is `--a` (default `static-femto`, the harness's build of the tag), side B `--b`
  (default `dist`; `dist:<path>` or a base URL too). Side A's root is `[role=document]` (`--root-a`):
  the old route's `div#content`, which held the route's content and its edit link, but not its
  hgroup, breadcrumb, side menu or table of contents. Its **grafts** (`sections.py` `GRAFTS`,
  `differ.js` `graftsOf`) add the parts of the section that sat in the old route's `main` and that
  the one page holds inside the section: `main > hgroup` as the root's first child, and
  `main > dialog` (Modal's demo dialog) and `main > nav[aria-label="overflow-with-focus"]` (Nav's) as
  its last, the places the section files give them. So side A's root has the children side B's
  section has, and the hgroup (each section's title and description), the dialog and the nav pair
  with side B's and are compared in full. A grafted element's tree path is its place under the root
  (`... > div:2 > hgroup:0`), as side B's is; a graft selector that matches inside or around the
  root is a harness error. If the one page puts a grafted element elsewhere, it is an `only-a` and
  an `only-b` record, never hidden. Side B's root is the element
  `document.getElementById(id).closest("section")`: the build's `<section>` around the section,
  whose hgroup holds the `h1` that carries the id. A cell whose side B has no such element is a
  harness error, so a missing section never passes.
- **Routes.** The route-to-section map is read from side A's `menu.json` at the tag
  (`git show static-femto:site/docs/menu.json`; `targets.json` `menu`), never from the working tree,
  whose `menu.json` loses its per-route fields in Phase 3: each section's `route` is a cell route
  for its id, and each of its `variants` a route for the same id with the color its last path
  segment names. So `/docs` is `quick-start`, `/docs/landmarks-section` is `landmarks`,
  `/docs/forms/<x>` is `<x>`, `/docs/forms` is `forms`, `/docs/<x>` is `<x>`, and
  `/docs/version-picker/<color>` is `version-picker` with that theme: 50 routes, the 31 sections and
  the 19 color routes. Without `--routes` all of them run; a route that is not in the map is a setup
  error (exit 2): compare a whole page with `pages --a static-femto` instead.
- **Side B's URL.** `<one_page>#<id>` (`targets.json` `one_page`: `/docs`), so the browser's own
  fragment navigation puts the section on screen as the route's content was, and
  `/docs?theme=<color>#version-picker` for a color route, the same view (PLAN.md URL inventory). A
  cell keeps side A's route as its `route` (the registry's `where.routes`, the reports, the theme
  routes of `matrix.json`) and records `url_b`, `path_b` (the path and query side B must answer),
  `section`, `section_theme` and `root_b` in `result.json`.
- **What is compared.** Everything the pages mode compares inside the two roots: the tree, every
  attribute, the elements' own text, every computed style and pseudo-element, plus the documents'
  status and the same-origin rule. The head is not compared with roots (Known limits): Phase 3's
  head is criterion 8's (`static_checks.py`). The status record holds side A to its route and side B
  to `path_b`, with the same status. A side's cross-origin loads are its whole document's, the one
  page's included. Screenshots start at each root's top; they never gate.
- **What differs by design** (PLAN.md `merge-layout`; Divergence registry). The root pair is a section
  against a div, one `structure` record (`tag`), whose attributes and styles are not compared and
  whose children are. The hgroup pairs (a graft); its `h1` carries the section id on side B only (an
  `attribute` record, `id`), and the hgroup's own box differs, since on the old route it was a grid
  item of `main` (`grid-area: header`, `min-height: auto`, no bottom margin) and on the one page it
  is a block in its section (`margin-bottom` 32 to 105 px by width, `min-height` `0px`, grid
  placement `auto`); Modal's dialog and Nav's overflow nav likewise change box (and the dialog its
  `data-modal` attributes, the nav its links' `href`). The subheadings' `#` anchors are on side A
  only (`only-a`). The table of contents, breadcrumb and side nav are outside both roots.
  Phase 3's contract 5 keeps the content column's width at every width, except on the four routes
  that had no table of contents (`/docs/rtl`, `/docs/link`, `/docs/forms/range`, `/docs/loading`) at
  1300 px and, as built (the core agent's deviation from contract 5, which said 1300 px only: the
  oracle's table-of-contents routes kept `10.5rem 1fr 10.5rem` at 1600 px too), at 1600 px, where
  every box of the section is narrower: a section layout consequence per route (Divergence
  registry) registers those sizes. A space at a line end renders nothing (Collection), so a box that
  wraps its text elsewhere can also give a `text` record there (`/docs/link` at 1300 px); that is a
  text entry of its own (Known limits).
- **Comparison.** A sections run is a `one-page` comparison: only the registry entries that name
  `one-page` in `where.comparisons` apply (and skipped checks). The same target on both sides is a
  self comparison.

The whole pages whose links into the docs change are compared as pages, with the same comparison:
`pages --a static-femto --b dist --full --routes /,/examples,/demo,/does-not-exist` (the 404 page is
the kept route `/does-not-exist`, which answers 404 with `404.html` on both sides). From Phase 4
`dist/` is no longer the Phase 3 site, so Phase 6 reruns both comparisons between the tags, with
`--b static-one-page`, the Phase 3 commit (Harness proof, Phase 6; owner decision 18).

Planned with the harness's planner on 2026-11-04 (`--plan`, no server or browser started):

| Command | Browser | Cells | light | dark | theme-light | theme-dark | Per width |
|---|---|---|---|---|---|---|---|
| `sections` (fast) | Chrome, Firefox | 228 each, 456 | 100 | 100 | 14 | 14 | 114 at 375 and 1300 |
| `sections --full` | Chrome, Firefox, Safari | 684 each, 2,052 | 300 | 300 | 42 | 42 | 114 |
| `pages --a static-femto --b dist --full --routes /,/examples,/demo,/does-not-exist` | Chrome, Firefox, Safari | 60 each, 180 | 24 | 24 | 6 | 6 | 10 |

The theme legs run on the seven docs routes among `matrix.json`'s theme routes. Each Safari pass
runs 384 of its 684 section cells (the OS scheme's leg and both theme legs) and 36 of its 60 page
cells; the other leg is the registered skip `media:<scheme>`, which the owner's other pass runs.

Measured on the real one page (2026-11-04, Chrome Beta 158 and Firefox 160, a build of the working
tree in the middle of Phase 3, no Phase 3 entries yet):

| Run | Cells | Wall clock | Per cell | Harness errors |
|---|---|---|---|---|
| `sections` (fast), one session per browser (`p3-harness2-sections-fast-1`) | 456 | 224 s | 0.5 s mean | 0 |
| `sections --full --browsers chrome,firefox`, two sessions per browser (`p3-harness2-sections-full-1`) | 1,368 | 354 s | 1.0 s mean, 2.5 s max | 0 |
| `pages --a static-femto --b dist:<build> --routes /,/examples,/demo,/does-not-exist` (`p3-harness2-pages-1`) | 40 | 13 s once a slot is free | | 0 |

Every cell found its section. The full pass takes about as long as Phase 1's full pages gate in
Chrome and Firefox (332 s). The records were the kinds this section names: the root pair and the
hgroup in every cell, the subheading anchors on every route that had them, geometry on the four
routes without a table of contents at 1300 and 1600 px only, `href` attribute records for the links
into the docs, `id` and `aria-describedby` records for renamed ids, and what the site had not yet
finished (unscoped `main.page-<id>` rules, the picker's per-color content). With a trial registry of
the shapes Phase 3 needs (the root pair, the hgroup, the anchors as one structure entry
`:is(h2, h3, h4) > a.secondary[id][tabindex="-1"]`, and one section layout consequence for each of
the four routes at 1300 and 1600 px), every such record was registered with no breadth or coverage
error (`p3-harness2-sections-trialreg-1` and `-2`).

## Tokens and states

The `styles` mode's additions (`harness/styles.py`; `differ.js` `collectTokens`, `prepTarget`,
`afterState`), ported from femto's `tests/` at the vendored commit 7bcd5758 (its README's Tokens and
States, `differ.js` and `compare.py`'s `apply_state`). femto compares one fixture page under two
stylesheet lists; here side A and side B are two builds of the same markup, so each side reads its
own document after the pages mode's collect, and the two are compared by tree path. Every record of
this section goes through the registry like any other (Divergence registry).

### Tokens

- **Names**: every `--femto-*` custom property declared in either side's stylesheets: a CSSOM walk
  through `document.styleSheets`, `@import`ed sheets, nested and conditional rules (`@media`,
  `@supports`), `@property`, and every open shadow root's sheets and adopted sheets. A sheet whose
  rules cannot be read is a harness error.
- **Surface**: a name only side A declares is a `surface-missing` record, one only side B declares a
  `surface-added` record. Resolution and raw text are compared only for names on both sides.
- **Anchors**: femto's (`html`, `body`, every `[data-theme]` element, every `article` and `dialog`,
  each open shadow root, where a host's probes go in its shadow root) and the site's equivalents of
  femto's `[data-module]` wrappers (`styles.py` `ANCHORS`): `body > header`, `body > footer`,
  `main`, `main > aside` (the docs menu and the table of contents), `[role=document]` (the docs
  content) and `main > section` (the landing page's sections). These are the units the site's CSS
  styles as wholes (the fixed header, the docs grid and its columns, the landing's hero, features
  and comparison), so a token that resolves differently inside one of them shows at its anchor;
  every other element takes its tokens from one of them, from an article (every example card) or
  from a `[data-theme]` element (every code block's footer). The set stays small: 9 anchors on
  `/docs/forms/range` to 59 on `/docs/colors`. Anchors are matched by tree path, and an anchor on
  one side only is a harness error (the two documents align element for element).
- **Resolution**: under each anchor a hidden `harness-probe` container with `all: initial;
  color-scheme: inherit; display: none` holds one child per token whose inline style sets each probe
  property to `var(<token>)`: femto's 25 (`color`, `background-color`, `border-top-color`,
  `outline-color`, `box-shadow`, `background-image`, `filter`, `backdrop-filter`, `opacity`,
  `font-size`, `font-family`, `font-weight`, `line-height`, `letter-spacing`, `width`, `padding-top`,
  `margin-top`, `border-top-width`, `border-top-left-radius`, `outline-width`, `outline-offset`,
  `text-decoration-line`, `text-underline-offset`, `transition`, `content`). The computed values are
  compared per token, anchor and probe property (kind `token`, colors with the Diff rule's
  tolerance). Resolution depends only on the anchor's token values and its `color-scheme`, so
  anchors with the same signature share one probe set (3 to 10 sets a document on the kept
  routes). The probes are removed at once and are never collected (`harness-probe` is skipped like
  the other harness tags).
- **Raw text**: `getPropertyValue(<token>)` at each anchor, trimmed, compared exactly (kind
  `token-raw`).
- Chrome Beta 158 resolves a token that is no color, through a color probe, to the initial text
  color of the probe's scheme (black under a light anchor, white under a dark one); Firefox 160 keeps
  one initial color. So where an anchor's `color-scheme` differs between the sides, Chrome also
  reports every token that is no color through `color`, `border-top-color` and `outline-color`
  (control `token-resolution`, 2026-11-02).

### States

The site's markup carries no `data-states` attributes (Phase 2 changes no markup), so the targets
come from `harness/states.json` (`--states FILE` for another file; the selftest's is
`fixtures/states.json`):

| Field | Meaning |
|---|---|
| `id` | unique |
| `selector` | the target's elements; side A takes the first `max` (default 2) that render (a client rect, `visibility: visible`) and are not inside a contents mask, and side B replays exactly those, by tree path |
| `states` | some of `hover`, `focus`, `focus-visible`, `active`, replayed in this order |
| `routes` | exact routes or `/^regex/` patterns |
| `scope` | the closest ancestor matching it holds the subtree collected under each state, so `:focus-within` parents, `:has()` and tooltip pseudo-elements are caught; default the element's parent |
| `open` | details matching it are opened first and closed after (menu items in a dropdown) |
| `widths` | integers or `{"min", "max"}`: the widths where the elements render (the docs menu from 1024 px, the breadcrumb below it) |
| `why` | what the target covers |

For each target, element and state, on both sides in the same order, after the side's collect (side
B after the document's diff) and before its screenshot:

| State | Input | Asserted |
|---|---|---|
| `hover` | scroll the element into view inside the iframe (wait two frames if it scrolled), move the pointer to the centre of its largest line box that hit-tests to it | `:hover` |
| `active` | the same point, pointer down; collect; pointer up at the same point | `:active` |
| `focus` | `element.focus()` | `:focus` |
| `focus-visible` | focus the preceding keyboard-focusable element (or the document), then a real Tab key press; if that misses, the following element and Shift+Tab; if that misses too, `focus()` on the element, Shift+Tab and Tab, the browser's own order (Chrome and Firefox stop at a keyboard-focusable scroller, such as a `pre` that overflows at 375 px, which the harness's list of focusable elements cannot see). Safari uses Option+Tab, and after the Tabs miss calls `focus()` right after the key presses (femto) | `:focus-visible` |

- A state that does not match is a harness error (pointer states retry once; a point outside the
  iframe viewport after scrolling is reported as such and never moved to), unless a `skipped-check`
  entry names that exact check, `state:<state>:<tag>[type=<type>]`, for one browser (no pattern
  matches a state check: Divergence registry). An element side A took that does not render on
  side B is a harness error too; the document diff shows why.
- After the state is applied the harness waits, when the document's scroll position has moved since
  the last wait, until it holds for two frames (at most 1 s), so the page's scroll listeners have
  run; then it finishes transitions, reads the subtree under the scope exactly as a
  document's collect does (tree, attributes, own text, computed styles and pseudo-elements, masks
  applied) and keeps it (side A) or aligns and diffs it against side A's subtree of the same element
  and state (side B). Every record found there carries `state`; the cell's in-page breadth guard
  stays in force, and the coverage rule applies to the subtree, counting only what the state adds: a
  registered record equal to one of the document diff's (the same element, pseudo-element, property
  and values) was judged there and covers nothing in the subtree. Before that rule, a registered
  difference of the docs header (9 of its 31 elements at 600 px) failed every hover and focus-visible
  replay inside it (`p2-registry-full-2`: 256 such harness errors).
- Scrolling is instant while a side replays its states: from `armStates` to the end of the replay a
  transient harness style sets `html { scroll-behavior: auto !important }`, and it is removed before
  the screenshot. The scrolls of a real Tab, a `focus()` and a pointer move follow the page's own
  `scroll-behavior`, and side A's legacy CSS has `html { scroll-behavior: smooth }` where side B has
  none (registered), so side A's state was collected mid-scroll and the table of contents' scroll spy
  had marked another link (`p2-docs-5-button-1600-dist`: 8 `aria-current` records under hover and
  focus-visible, 0 with the same build plus `scroll-behavior: smooth`; 0 again after the fix,
  `p2-fix-harness-r1-button-1600`). `html`'s `scroll-behavior` is compared in the document's collect,
  before the replay, and `html` lies outside every state's scope; after the replay a cell records
  each side's `html` `scroll-behavior` (`scroll_behavior_a`, `scroll_behavior_b`), and a harness
  style left in the document is a harness error (control `scroll-smooth`). The wait and the override cost about 6 ms a replay
  in Chrome and 13 ms in Firefox (median 59 and 38 ms, `p2-fix-harness-r1-recheck`, against 53 and
  25 ms in `p2-review-parity-1-fast-1`).
- Between states the pointer parks on the host page's strip and the focused element is blurred.
  Each side's replay starts with a pointer click on that strip, outside the document, so both sides
  start from the same input modality (whether `focus()` matches `:focus-visible` follows the last
  input).
- Activation is cancelled in the document while states are replayed: capture-phase listeners on its
  window stop every `click`, `auxclick` and `submit` (`preventDefault()` and
  `stopImmediatePropagation()`, so neither the browser's default action nor the page's own
  listeners run: femto cancelled the defaults only, and this site's scripts act on clicks, such as
  the theme toggle and the copy button), and cancel every `mousedown` on a `select` (otherwise the
  native picker opens, stays open in Firefox and swallows later input).
- Safari replays states only with the screen unlocked and the automation window in front; a cell
  where `interactive()` fails is a harness error.

**What `states.json` covers** (50 targets, 112 target states, on 22 routes): the header's text and
icon links, theme toggle (Decision 16's emoji), logo, version dropdown and its item, and the skip
link, and the footer's text and icon links, on `/` and `/docs/button`; on `/docs/button` the docs
menu's summaries, its first two links (Typography and Link) and its current link (Button) (from
1024 px), the table of contents, the breadcrumb (below 1024 px), a
subheading permalink, the code copy button and its tooltip, the edit link, and the button variants,
outline buttons, input buttons and `role=button`; the link variants (`/docs/link`); form controls:
text inputs, a textarea, a select, two checked checkboxes and an unchecked one, radios (Tab enters a group on its checked radio, so
the unchecked one is hovered and pressed only), switches, a range and the forms overview's form; the
accordion, dropdowns and their items (one opened), nav links, a group's input and buttons, the
modal's buttons, and tooltips on a link, a button and an inline element; the color scheme switcher
(`/docs/color-schemes`) and the forced-theme examples' inputs; color swatches (`/docs/colors`); the
version picker's first two swatches (red and pink), its current swatch on
`/docs/version-picker/jade` and its themed preview form (`/docs/version-picker`,
`/docs/version-picker/jade`); the landing page's calls to action and feature links; the examples
page's card links. Each component is replayed on its own docs route and the shell on two routes, a
few elements per component rather than every match: 1 to 67 replays per side in a cell
(`/docs/button` has the most).

**Cost** (Chrome Beta 158, Firefox 160, 2026-11-02): a state replay takes about 60 ms per side in
Chrome and 35 ms in Firefox, the tokens 20 to 160 ms per side (`/docs/colors` the most).
The full Chrome and Firefox pass of the mode's self check (`styles --a static-multipage --b
static-multipage --full --browsers chrome,firefox`, run `p2-harness-styles-self-full`) took 502 s
for 1,488 cells: 7,320 state replays per side in 648 cells, tokens in 2,976 documents (up to 573
names, 45,072 anchors, 131 s of the four sessions' time), zero differences and zero harness errors.
That is 1.5 times the full pages pass of the Phase 1 gate (`owner-gate-pages-full`, 332 s).
The Phase 2 gate (`p2-gate-styles-full-2`, side B `dist`) took 553 s: 7,536 state replays per side
(the round 2 scroll check adds a little), tokens in 166 s of session time.

## Behavior

The pages mode reads each document as loaded; the behavior mode drives the widgets. It holds the
static site to every runtime behavior in `docs/research/01-site-inventory.md` §2 that Phase 1
rebuilds, and the Phase 1 gate needs it to pass in Chrome and Firefox ("the behavior suite for every
widget"). From Phase 3 it also holds the one docs page to criterion 7 (the `one-page` group: the
spy, deep links, nav clicks, back, forward, reload, smooth scrolling only for nav clicks, `?theme=`)
and to criterion 15's run-time check (`deep-link-cold`). The table of contents' Scrollspy, rebuilt in
`docs.js` for Phases 1 and 2 and held there by `toc-spy`, and the side menu's per-route marking
(`side-menu-current`) went with the per-route pages: the one page's spy replaces both, and the
`one-page` group's checks replace theirs. The
Logo animation is dropped by 01 §2 except where the static site still changes the route in place,
the version picker's swatches and links, so `picker-logo` holds it there. Remix's navigation
feedback is dropped. The version dropdown is a native `<details>` with no script, and the demo's
maximize controls are dead code, so neither has a check.

**Phase 4** (PLAN.md Workflow, 4 femto 3 content; criterion 7 rerun) changed what several checks
hold, and the suite follows the Phase 4 site; parity with the oracle no longer binds:
- The version picker is the Theme picker, section `#theme-picker`, with no base select, Conditional
  switch or Sass sample: `picker-configuration` and the Sass half of `picker-code-highlight` went
  with them, and `picker-options` (the option switches and the links they write), a new
  `picker-code-highlight`, `picker-unknown-theme` and `picker-popstate` hold the new picker.
- `/demo` is not built: `demo-page` went with it.
- The header's version dropdown is a plain label linking to `/docs` (no check had held the dropdown).
- The header toggle, the copy controls, the breadcrumb's Documentation control and the menu's Close
  are buttons: the checks select `:is(a, button)`, and `theme-toggle-button`, `copy-keyboard` and
  `pre-scroll-keyboard` hold what only a button or a focusable code block does. Only a code block
  that overflows stays a tab stop (a figure named "HTML code" or its language's): `copy-keyboard`
  holds that the others are skipped.
- The off-canvas menu makes the page behind it inert: `mobile-menu-inert`. Modal's demo is a true
  modal (`showModal()`), so the page behind it is inert too: `modal-two-dialogs` asserts that, and
  opens the color modal over it with a script's `click()` instead of Enter on a shade button.
- The typing demo has a Pause button and starts paused under reduced motion: `demo-pause` and
  `demo-reduced-motion`.
- Link's aria-current example is "Current link example" (the oracle's "Active link example"), and
  Input has no example forms: `link-examples` names both, `example-forms` dropped `/docs#input`.
- The Colors section's modal has five rows and its family colors are femto.colors.css's, Nav lost a
  stray copy of its focus-ring nav (28 example links), Progress' sample is valid HTML, and the nav
  has 40 sections: those checks assert the Phase 4 values on the one page and the oracle's on routes.
- `/examples` holds the site's own mockups: the `examples` group (12 checks) holds examples.js and the
  mockups' isolation in their shadow roots.

What Phase 4 reworked or added runs on the one page only (`layouts`, with the reason; on the oracle a
`SKIP`); the rest still runs against the oracle, whose own markup each branch asserts.

**Phase 6** (PLAN.md Workflow, 6 Final review) added three checks, all on the one page only:
`progress-pause` and `progress-reduced-motion` (the Progress example's new Pause button, a11y-8) and
`tooltip-link-same-hash` (a link to the URL's own hash on a `?theme=` URL, urls-1). It made five
assert more:
- `copy-button` and `color-modal-tab-cycle` read each button's computed name (WebDriver Get
  Computed Label, `computed_name()` and `expect_name()` in `__init__.py`), not the icon's
  `aria-label` attribute (a11y-1).
- `mobile-menu-focus` holds the page's scroll position when the menu closes, also with `focus()`
  made to ignore its options (verify-css-1).
- `spy-categories` holds that the spy scrolls the side nav, not the page, to show the current link
  (critic-8).
- `demo-loop` holds the Next button's missing `type` and the busy input's `disabled` in the code
  (content-c-3, content-c-4).

In Safari the checks whose `motion` is `reduce` now run in the owner's pass with Reduce Motion on
(Safari, below).

```sh
uv run tests/run.py behavior --target oracle                         # every check, Chrome and Firefox (routes layout)
uv run tests/run.py behavior --target dist --groups shell,landing    # some groups against the static site (one page)
uv run tests/run.py behavior --target dist --groups one-page         # criterion 7's checks of the one docs page
uv run tests/run.py behavior --target dist:/path/to/built --checks copy-button,grid-columns
uv run tests/run.py behavior --target http://127.0.0.1:8788 --ready static   # a server someone else runs
uv run tests/run.py behavior --list                                  # the checks and what each asserts; starts nothing
```

Options: `--target` (`oracle`, `dist`, `dist:<path>`, a base URL; the named targets of
`harness/targets.json`, started and stopped by the run like every mode's), `--groups`, `--checks`
(names), `--browsers chrome,firefox` (the default; `safari` too, below),
`--ready oracle|static|none` (the target's hook by default; `static` for a base URL), `--layout
one-page|routes` (the target's by default, below), `--workers
chrome=2,firefox=2` (sessions per browser, 1 by default), `--expect-oracle-bugs` (a base URL that
serves the oracle), `--expect-os-motion no-preference|reduce` (Safari: a session that reads another OS
motion stops before its first check, and the run fails; Phase 6), `--run-id`, `--label`,
`--no-shots`, `--list`.

**Layouts.** A target is `one-page` (the static site from Phase 3: a target whose `targets.json`
entry names its `one_page`, `dist`; and a base URL) or `routes` (one page per old docs route: the
oracle, `static-femto`, `static-multipage`, and a base URL with `--expect-oracle-bugs`); `--layout`
overrides it. A check's routes are written in the one page's URLs: `/docs#<id>`, `/docs` (Quick
start, the top) and `/docs?theme=<color>#version-picker`. On `routes` each is loaded at the old route
that showed it, through `static-femto`'s `menu.json` read from the tag (the map the sections mode
uses): `/docs#modal` at `/docs/modal`, `/docs` at `/docs`, `/docs#landmarks` at
`/docs/landmarks-section`, `/docs?theme=jade#version-picker` at `/docs/version-picker/jade`. A route
no old route showed (`/docs?theme=bogus`) is a setup error there, unless the check runs on the one
page only. Phase 4's `/docs?theme=<color>#theme-picker` is loaded at the old
`/docs/version-picker/<color>` (`harness/behavior.py` `SECTION_ALIASES`: the Theme picker is the
version picker reworked). Every script a check runs in the page sees `S`, the element its route's content lives in:
on the one page the section, `document.getElementById(<id>).closest("section")` (a check fails at
once, at "the page has the #<id> section", if it is missing); on routes the whole document
(`document.documentElement`, as the checks queried it before). So `S.querySelector(...)` finds the
route's own example and never another section's (`page.find`, `page.find_all`). Selectors outside the
content (the header, the side menu, the footer, `dialog.color`) stay document-wide. Where the two
layouts behave differently by design, a check says both in its docstring and branches on
`page.layout`: the picker's swatches push routes on one and `replaceState` `?theme=` on the other,
a link to the Grid section loads `/docs/grid` or scrolls to `#grid`. A check of what only one layout
has (the `one-page` group, and the shell group's `modal-two-dialogs`: Modal's demo and the color
modal share a page only there) or what Phase 4 added (the Theme picker, `/examples`, the typing
demo's pause button) is registered with `layouts=("one-page",)` and a `layout_reason`, and on
the other layout it is recorded as `SKIP` (`layout:routes`) with that reason in the summary, never
silently dropped.

On the one page the spy rewrites the URL's hash (`replaceState`, no history entry) whenever a check
scrolls, even to bring an example into view. So "the URL is unchanged" (`page.url_kept`, given a
`page.url()`, which carries `history.length` as it read the URL) means there: the same path and
query, and a hash that is the same, a section's id or none (the spy's plain `/docs` at the top);
elsewhere the exact URL; and on both, the same `history.length`. A `#close` or any other hash, and
any new history entry, still fail. `page.load(route)` reaches a route
that differs from the current URL only by its hash through `/favicon.svg` first, so it is a new
document (a hash on the same page is a fragment navigation, which runs no preload and no page
script).

**How a check runs.** A check drives a top-level document directly: no host page, iframe or proxy,
so the URL, history, focus, storage events between tabs and resizes are the browser's own. Each
browser runs headless (timers and animation frames at full rate; hidden or background tabs throttle
both to about once a second, 05) and holds one machine-wide harness slot for its whole life, with
WebDriver start-up serialized (Concurrency and locks). Before each check and route the page is
reset: a fresh tab, with every other tab closed (its own history, which both browsers cap at 50
entries, its own sessionStorage, and Chrome's per-tab focus and color-scheme emulation set again);
the viewport set exactly to the check's size with WebDriver BiDi
`browsingContext.setViewport` (headless windows are at least 500 px wide in both browsers, so a
window size cannot give 375; the page still gets real resize events and media queries);
`prefers-color-scheme` emulated as in the pages mode (CDP in Chrome, the content pref in Firefox);
storage emptied on the target's origin from a same-origin static file (`/favicon.svg`) and the
check's items stored; then the route loaded and the readiness hook run (`oracle`:
`oracle.wait_ready()`, with frames requested until the router is up, Rig notes, Chrome: idle
periods; `static`: load, fonts and two frames).

Input is real WebDriver input: pointer clicks at the element's center (scrolled into view first, and
only once the element holds still and the point hits it or a descendant, as a user's click would;
WebDriver's element click misplaces the point under an emulated viewport in Chrome), key presses to
the focused element, `<select>` choices, window resizes. A check asserts only what any side can be
held to: DOM state, focus, the URL, history and storage. It reads no React state, framework global
or script source, so one check runs against the oracle and the static site alike. Timings (the
modal's 400 ms, the copy link's 1 s, the progress' 5 s) are measured in the page with
`performance.now()` and MutationObserver timelines, not across WebDriver round trips.

Five mechanisms reach under the page, each for one check family and each without touching the
page's markup or styles:
- **Preload scripts** (BiDi `script.addPreloadScript`, removed after the check): a script that runs
  in every new document before the page's own, for the color-scheme flash.
- **The copy spy** (`behavior.COPY_SPY`): `document.execCommand("copy")` and
  `navigator.clipboard.writeText()`/`write()` are replaced in that document by recorders, so the
  copy buttons are checked without ever touching the machine's clipboard.
- **Classic scrollbars**: headless browsers on macOS draw overlay scrollbars of width 0; the modal's
  scrollbar compensation needs one that takes space. Chrome adopts a `::-webkit-scrollbar` sheet in
  every new document before its scripts run, Firefox gets `ui.useOverlayScrollbars` 0 for the check.
- **Held responses** (the check option `delay`, `Page.delay_responses`): a WebDriver BiDi
  `network.addIntercept` on each exact URL, whose request Selenium continues only after the wait,
  removed after the check; the load then goes over BiDi `browsingContext.navigate`, since
  ChromeDriver runs no BiDi command while a classic `get` waits for the load. `theme-first-frame`
  holds jade's file 300 ms, as 05's `serve.py` did: served at once, a theme `<link>` added by script
  arrived before the first paint too, and the check could not tell it from `document.write`.
- **The history and scroll recorder** (`one-page.py` `TRACK`): the page's own
  `history.replaceState` is wrapped to record each call's time and URL (the spike's way of counting
  them), and a MutationObserver and a scroll listener record the side nav's current links and every
  scroll event with `html`'s computed `scroll-behavior`. Nothing the page does is changed.

Five check options change the browser, not the page: `motion="reduce"` emulates
`prefers-reduced-motion` (Chrome: CDP `Emulation.setEmulatedMedia`, with the color scheme; Firefox:
the `ui.prefersReducedMotion` pref, cleared after); `javascript=False` turns the page's JavaScript
off (Chrome: CDP `Emulation.setScriptExecutionDisabled` for the tab; Firefox: `javascript.enabled`,
cleared after; WebDriver's own scripts still run, and the load waits for `readyState` complete
instead of the readiness hook); `cold=True` empties the HTTP cache before the route loads (Chrome:
CDP `Network.clearBrowserCache`; Firefox: `Services.cache2.clear()`); `delay={path: seconds}`
holds those responses (above); `preload_optional=True` lets Safari run a check without its preload
script (`page.preloaded` says which), where it would otherwise skip it; `safari_skip="<why>"` skips a
check in Safari for another reason Safari's WebDriver cannot meet (Safari, below).

**Expected failures.** A check may assert something the conversion fixes in the oracle (PLAN.md,
`oracle-bug`): it names the assertion and the reason, `oracle_bug={"fails": ..., "reason": ...}`.
Against `--target oracle` (or `--expect-oracle-bugs`) such a check must fail at exactly that
assertion, which is reported as `XFAIL`; if it passes there (`XPASS`) or fails at another assertion,
the run fails. Against any other target it is an ordinary check. Eleven checks carry one (`--list`
shows each with the assertion it fails): `color-scheme-flash` (two routes), `theme-stored-invalid`,
`mobile-menu-focus`, `picker-swatch-focus`, `color-modal-close-url`, `color-modal-focus`,
`color-modal-tab`, `color-modal-focus-small`, `font-size-restored-switch`, `progress-offscreen` and
`demo-offscreen`, so a full run against the oracle expects 12 `XFAIL` per browser, and 51 `SKIP`
(`layout:routes`: the `one-page` group's 15 checks over 19 routes, `modal-two-dialogs`, the 25
checks over 28 routes of what Phase 4 reworked or added: `theme-toggle-button`, `mobile-menu-inert`,
`copy-keyboard`, `pre-scroll-keyboard`, `color-modal-tab-cycle`, six of the picker's, `demo-pause`,
`demo-reduced-motion` and the 12 of the `examples` group, and Phase 6's `progress-pause`,
`progress-reduced-motion` and `tooltip-link-same-hash`, one route each). `mobile-menu-focus` is Phase 3's:
the oracle's off-canvas menu has no Escape and no focus handling (01 §2), which criterion 7 asks for.
Two kinds of fix are among the others.
The color-scheme flash, the invalid stored theme and the two off-screen intervals are what the
conversion fixes by being written to PLAN.md's rules (Decision 14; Conversion rules, intervals on
screen). The color modal's focus and Tab handling, the swatch focus and the restored font-size
switch are deliberate early fixes of 03 §5's widget plan (`<dialog>`-native focus for `colors.js`)
that PLAN.md's Workflow lists under Phase 3's per-dialog modal and widget fixes; Phase 1 landed them
with their widgets instead of porting the bugs first, and the owner confirmed that on 2026-10-31
(PLAN.md, Conversion rules, JavaScript). None of these is a pages-mode difference, so no registry entry records them. Nothing else is expected to fail, and nothing is
masked: the parity masks and the `blob:` rule belong to the pages mode. One check does fail there,
and it is no oracle bug: `copy-button` looks for the site's own icon (Decision 18's
`span[role=img]`), which the oracle's SVG is not, and fails at "link 1: clipboard icon before" in
both browsers (`p6-record-oracle-1`, 2026-11-07, with `mobile-menu-focus` an `XFAIL` and
`demo-loop` a `PASS` as expected). No full run against the oracle has been made since Decision 17,
so another check that looks for the icons may fail there too. Parity with the oracle stopped
binding at Phase 4. These expected failures
live in the checks, not in `tests/divergences/`, whose entries type pages-mode records; each
carries the same PLAN category, `oracle-bug`, and its reason.

**Safari** (`--browsers safari`, Phase 3) runs under femto's Safari rules, as every mode does (Rig
notes, Safari): one session at a time machine-wide, holding the Safari lock for its life; never
while the user's own Safari is open, and only on an unlocked screen (a locked one is a setup error,
exit 2: real input never reaches a hidden page); visible, not headless, with one worker. Safari cannot
emulate `prefers-color-scheme`, so a check whose `media` is not the OS scheme is not run: it is
recorded as `skip` (`media:<scheme>`, in the summary's SKIPPED list), and the owner's pass in the
other appearance runs it. Nor can it emulate `prefers-reduced-motion`. From Phase 6 the session reads
the OS motion with `matchMedia`, as it reads the scheme: `log.txt`'s session line ends `OS scheme
<scheme>, OS motion reduce` or `OS motion no-preference`, `result.json`'s `sessions[]` keep
`os_motion`, and a check whose `motion` is not the OS's is skipped (`motion:<motion>`). With Reduce
Motion off that skips the three `reduce` checks (`demo-reduced-motion`, `spy-nav-click-reduced` and
`progress-reduced-motion`, all light ones); with it on, every other check. `--expect-os-motion`
stops a session that read the wrong one before its first check: its jobs are reported as never
run, and the run fails. Until Phase 6 the `reduce` checks were skipped in Safari whatever macOS
said, so `spy-nav-click-reduced`, a criterion 7 item, had never run there (critic-3; owner decision
19). `nojs-deep-link` (`javascript:off`: WebDriver cannot turn JavaScript off in Safari, as in
05) is skipped there. Safari has no WebDriver BiDi: the viewport is sized through the window (a size Safari's window
cannot give fails the check), and a check that needs a preload script is skipped there (`preload`:
`color-scheme-flash`, `examples-first-frame` and `examples-first-frame-cold`), except
`theme-first-frame`, whose preload is optional (it reads paint timing in Safari) and whose held theme
file is not held there (no BiDi interception: noted), and `modal-two-dialogs`, which keeps Safari's
own scrollbar (an overlay one gives `0px`: noted). A check that needs something else Safari's WebDriver
cannot do says so (`safari_skip`) and is skipped there too (`safari`): `theme-os-live` switches the OS
scheme while the page is open, and `modal-scrollbar-width` forces a classic scrollbar, which the
harness can do only with a preload script or Firefox's pref (it never changes macOS's settings).
`font-size-restored-switch` ends in Safari once Safari has brought the switch back unchecked on the
reload with the px table (the restored switch needs a preload script). Its cache cannot be
emptied, so `deep-link-cold` and `theme-first-frame` note that their load may be warm; Safari has no
layout-shift entries, so `deep-link-cold` asserts the position only. Safari's Tab, by default, skips
links and buttons, so the harness presses Option+Tab there (`page.tab()`, and `page.key("TAB")`
through it), as the styles mode does. Every other check
uses only real input, page scripts and the history API, as the spike's Safari run did. The harness's
own proof is `--list`, argument parsing and, in Phase 6, `run_one` with stand-in Safari page and
session objects; the Safari runs are the owner's (`tests/owner-safari.sh final` and `reduced` from
Phase 6; `one-page` and `content` before it). `copy-button`, `color-modal-tab-cycle`,
`progress-pause` and `progress-reduced-motion` read computed names through WebDriver Get Computed
Label, which no Safari run of these checks has used yet.

**Output.** `tests/results/<run-id>/` (run id `YYYYMMDD-HHMMSS-behavior-<pid>` unless `--run-id`):
`result.json` (the run, the target and its side, the sessions' versions, totals per browser, every
check run with its status, the failing assertion's label, every assertion with its detail, notes,
duration and document loads), `summary.txt` (failures first with their detail, then the expected
failures with their reasons, then one line per check run) and `log.txt` (one line per check run as it
finishes); `shots/<browser>__<check>__<route>.png`, the viewport of every failed, errored or XPASS
check. Statuses: `PASS`, `XFAIL`, `FAIL`, `XPASS`, `ERROR` (an exception outside an assertion: a
covered click target, a WebDriver error, after which the session is restarted), and in Safari `SKIP`
(the other scheme's checks, or from Phase 6 the other motion's). Exit status: 0 when every check run is `PASS`, `XFAIL` or `SKIP`; 1
otherwise or after a harness error; 2 for a setup error (an unknown group, check, browser or target, a
missing `dist/`, the user's Safari open or the screen locked for a Safari run).

**Writing a check.** In a group module, `GROUP = "<group>"`, then:

```python
@check("name", ("/docs#modal", "/"), width=375, height=812, media="dark", storage={"femtoColorScheme": '"dark"'})
def name(page):
    """What it asserts, in terms of DOM state, focus, URL and storage (shown by --list)."""
    page.click(page.find("css selector"))            # S's first match; a string selector is document-wide
    page.wait("label", "S.querySelector('...').open", 1)   # poll until truthy, at most 1 s
    page.eq("label", page.js("return ..."), expected)
    page.url_kept("label", url_before)               # url_before = page.url(): no navigation, no new entry
```

`page` also has `ajs` (async scripts), `expect`, `holds`, `key` (`ESCAPE`, `ENTER`, `ARROW_LEFT`,
...), `focus`, `scroll_to`, `resize`, `new_tab`/`switch` (a second tab of the same browser),
`wait_navigated(path)` (a full load or a client-side route change, then the readiness hook; routes
only), `load(route)`, `find_all`, `address(route)` (where a route loads on this target),
`with_classic_scrollbars()`, `note` and `url`, and the route's `layout`, `section` and `theme`.
`behavior.HEADING_LINE` (a section heading's offset from its scroll-padding line), `nav_href` and
`self_href` are shared helpers. The first assertion that fails ends the check, and its
label names the failure, so labels say what should hold.

### The checks

Each check's docstring (`--list`) is its full statement; this is the summary. Viewport 1300 × 900,
light OS and nothing stored unless the table says otherwise. Routes are the one page's URLs (Layouts;
on routes, `/docs#modal` is `/docs/modal`, and so on). 97 checks over 119 check-routes, 238 runs in
Chrome and Firefox (`--list` prints the count): Phase 4's 94 checks over 116 check-routes, plus
Phase 6's `progress-pause`, `progress-reduced-motion` and `tooltip-link-same-hash`, one route each.
Phase 4's 94 are Phase 3's 74 checks over 94 check-routes, less
`picker-configuration`, `demo-page` and `example-forms`' `/docs#input` (whose forms Phase 4
removed), plus Phase 4's 22 checks over 25 routes (`theme-toggle-button`, `mobile-menu-inert`,
`copy-keyboard`, `pre-scroll-keyboard`, `color-modal-tab-cycle`, `picker-options`,
`picker-unknown-theme`, `picker-popstate`, `demo-pause`, `demo-reduced-motion` and the `examples`
group's 12), with `picker-code-highlight` and `modal-two-dialogs` rewritten. Against the oracle 44
checks over 51 routes are skipped
(`layout:routes`, Expected failures).

| Group | Check | Routes | Asserts |
|---|---|---|---|
| shell | `theme-toggle` | `/`, `/docs#typography` | No `data-theme` and nothing stored at first; the header toggle (a button from Phase 4, named by its `span[role=img]` icon since Decision 18) reads "Turn on dark mode" with ☀️ (`moon` before Decision 18). A click sets `data-theme="dark"`, stores `femtoColorScheme` `'"dark"'`, relabels "Turn off dark mode" with 🌙, URL unchanged; a second click gives `light` the same way. |
| shell | `theme-toggle-dark-os` | `/docs` (dark OS) | The toggle follows the OS ("Turn off dark mode", 🌙) with no `data-theme`; a click stores `'"light"'`, the next `'"dark"'`. |
| shell | `theme-toggle-keyboard` | `/`, `/docs#typography` | The toggle focused, Enter gives dark (data-theme, storage, label) and Enter again light, with no navigation and the document kept. |
| shell | `theme-toggle-button` | `/`, `/does-not-exist` (one page) | The toggle is a `<button type="button">` with no href; Tab from the GitHub link reaches it; Space gives dark and Enter light, no navigation. |
| shell | `theme-os-live` | `/`, `/docs#table` | With nothing stored, a live switch of `prefers-color-scheme` to dark and back relabels the toggle, turns the homepage comparison samples dark (`/`) or the inverse thead light (`/docs/table`) and back; no `data-theme` written, nothing stored. Skipped in Safari (`safari`). |
| shell | `theme-stored-dark` | `/`, `/docs#button` (stored dark) | A stored choice wins over a light OS: `data-theme="dark"`, toggle "Turn off dark mode". |
| shell | `theme-stored-light` | `/docs#button` (dark OS, stored light) | `data-theme="light"`, toggle "Turn on dark mode"; a click stores dark. |
| shell | `theme-stored-invalid` | `/docs#table` (dark OS, stored `'"blue"'`) | A stored value other than light or dark is left in storage and ignored: no `data-theme` (held 0.5 s), the page follows the OS (toggle "Turn off dark mode", the inverse thead `light`); a click stores light. **XFAIL on the oracle** at "a stored value other than light or dark sets no data-theme": it writes any stored value into `data-theme`. |
| shell | `theme-cross-tab` | `/docs#typography`, a tab on `/` | Toggling in tab A reaches tab B without a reload (dark, then light, B's toggle relabelled); removing the stored item in A removes `data-theme` in B. |
| shell | `color-scheme-flash` | `/`, `/docs` (stored dark) | Once a paint entry exists (Chrome can record it a few hundred ms after load), seen from a preload script, `data-theme` appears while the head is parsed (no `<body>` yet), before the first paint, and the first animation frame sees it. **XFAIL on the oracle** at "set while the head is parsed": it sets the attribute during hydration (the flash; whether that still precedes the first paint is a race). Skipped in Safari (`preload`). |
| shell | `header-fixed` | `/docs#modal` | Scrolled to the top first, `body > header` has `is-fixed-above-lg`; `is-fixed` exactly while `scrollY > 20` (off at 20, on at 21, off again at 20 and 0). |
| shell | `header-landing` | `/` | The landing header has no class, at the top and scrolled. |
| shell | `copy-button` | `/docs`, `/docs#modal` | The route's first and last copy controls (in `S`; buttons from Phase 4) each copy their own block's `pre code` textContent (copy spy), URL unchanged; in the page: "Copied" with the check ✓ within 100 ms, named as the copy icon ⧉ was, back to "Copy to clipboard" with ⧉ 900 to 1500 ms later (Decision 18's `span[role=img]`; `.icon-check` and `.icon-copy` at Decision 17, `svg.check` and `svg.clipboard` before it), no other step, focus not on the control after a pointer click. From Phase 6 the button's computed name (WebDriver Get Computed Label) is the icon's label, "Copy code", alone, before the click, while the ✓ shows and after the revert: site.js names it with `aria-labelledby` (owner decision 17), and neither tooltip's text joins it. The name is polled for up to 0.5 s, since Firefox 160 names the button "✓" for a few milliseconds after the swap, and the ✓ is checked to be still showing after the read. Fails on the oracle (Expected failures). |
| shell | `copy-button-repeat` | `/docs#modal` | Two clicks 500 ms apart copy twice; "Copied" reverts once, 900 to 1200 ms after the first click (Code.jsx: every click schedules its own revert), no other step, not focused. |
| shell | `copy-keyboard` | `/docs#button`, `/examples` (one page) | Tab reaches the first copy button; Enter copies its block, the tooltip and the visually hidden `role=status` line read "Copied", 1 s later they revert with keyboard focus kept; Space copies again. The block's `<pre>` is a tab stop only when its code overflows (site.js, Code block focus): one that does not has no `tabindex`, `role` or `aria-label` and Tab moves past it to the next control after it (both routes' first blocks, in both browsers); one that overflows has `tabindex="0"`, `role="figure"` and `aria-label` "HTML code" (or its language's) and Tab moves to it. |
| shell | `pre-scroll-keyboard` | `/docs` (375 × 812; one page) | Quick start's first code block that overflows is a figure in the tab order (`tabindex="0"`, `role="figure"`, `aria-label` "HTML code"), takes focus with Tab from its copy button, matches `:focus-visible` with an inset ring, and Right arrow scrolls it (each press held 0.1 s; the scroll waited for up to 2 s; the note gives the keydown events the `pre` saw). |
| shell | `modal-helper` | `/docs#modal` | Timed in the page: `modal-is-open modal-is-opening` within 100 ms of "Open modal", `modal-is-open` alone 350 to 700 ms later; Escape gives `modal-is-open modal-is-closing` within 100 ms and no class 350 to 700 ms later; Escape with nothing open does nothing. |
| shell | `modal-scrollbar-width` | `/docs#modal` (classic scrollbars) | While open, `<html>`'s `--femto-scrollbar-width` is the scrollbar's width (15px) and the page behind keeps its left edge; gone once closed. Skipped in Safari (`safari`). |
| shell | `modal-two-dialogs` | `/docs#modal` (classic scrollbars; one page only) | PLAN.md Conversion rules, one modal helper per dialog (site.js `createModal`), read from a MutationObserver: "Open modal" opens Modal's demo alone, `modal-is-open` and the scrollbar's width on `<html>`. The demo is a true modal (`showModal()`, from Phase 4): it matches `:modal` with focus inside, and the page behind is inert (Colors' red 500 shade button cannot take focus; focus stays in the demo). A script's `click()` on that button (inert stops user input, not a script's events) opens the color modal through colors.js's own helper and hides the demo at once: the first change, within 250 ms, is the color modal alone open with `modal-is-open modal-is-opening` and the same width, then `modal-is-open` 350 to 800 ms after the click, nothing else (no `modal-is-closing`, never both open, `modal-is-open` whenever one is); then the demo is closed, not `:modal`, and focus is in the color modal. Escape: `modal-is-closing modal-is-open` within 100 ms, then no dialog open (the static examples aside), no modal-is-* class and an empty `--femto-scrollbar-width` 350 to 800 ms after Escape, unchanged 0.6 s on. Each step is timed from the click or the key, not from the step before: colors.js starts the 400 ms timer and then focuses its close button, which lays out the long page, so the observer sees `modal-is-opening` 65 to 106 ms after it and the gap between the two steps fell to 342 to 349 ms in Firefox (`p3f-review-behavior-1`, `p3f-review-m2d-1`, `p3f-head-m2d-3`), while `modal-is-open` itself comes 438 to 454 ms after Enter (447 to 450 ms after the click in `p4-fix-checks-2-behavior-dev-1`). Until Phase 4 the scenario was Enter on the focused shade button behind the open demo, which a true modal makes impossible. Skipped on routes (`layout:routes`). |
| shell | `side-menu-max-height` | `/docs#grid` (375 × 812) | The menu nav's `--max-height` is `innerHeight` minus its top (within 0.5 px) on load and after resizes to 375 × 600, 1300 × 900 and, scrolled 500 px, 1300 × 700; each time `<body>`'s inline `min-height` is `innerHeight` px. |
| shell | `mobile-menu` | `/docs#modal` (375 × 812) | The breadcrumb's "Documentation" control (a button from Phase 4) adds `is-open-on-mobile` to `aside#documentation-menu`, `<html>` stops scrolling, URL unchanged; the menu's Close reverses all three. |
| shell | `mobile-menu-keyboard` | `/docs#modal` (375 × 812) | Enter on the focused "Documentation" control opens the menu, Enter on its focused Close closes it; no navigation either time. |
| shell | `mobile-menu-focus` | `/docs#modal` (375 × 812) | Criterion 7's Escape and focus: Enter on "Documentation" opens the menu with focus inside `aside#documentation-menu`; Escape closes it (scrolling back, URL kept) and returns focus to the Documentation link; opened by a click, focus is inside again, and Enter on the close link closes it with focus back on Documentation; Escape with it closed does nothing. From Phase 6 both closes leave `scrollY` within 1 px of where it was before that opening, and the whole sequence runs again with `focus()` made to drop its options (`FOCUS_NO_OPTIONS`), as Chrome Android and Samsung Internet ignore `preventScroll` (verify-css-1, css-1): Chrome scrolls the page to show the sticky breadcrumb's opener when it takes focus, 415 px with a bare `focus()` (`p6-f-checks-4`). Firefox never scrolls a sticky element on focus, so only Chrome can catch that. **XFAIL on the oracle** at "opening moves focus into the menu" (no Escape, no focus handling, 01 §2). |
| shell | `mobile-menu-inert` | `/docs#modal` (375 × 812; one page) | Criterion 7's mobile menu focus: opened with Enter, focus on Close, `aria-expanded="true"`, every sibling of the menu and of its ancestors inert and the menu not; 60 Tabs and 10 Shift+Tabs stay in the menu; Escape: nothing inert outside, the menu inert, `aria-expanded="false"`, focus on the opener; a nav link (Grid) closes it with nothing left inert; resized to 1300 nothing is inert, back at 375 the page is inert again. |
| shell | `mobile-menu-link` | `/docs#modal` (375 × 812) | With the menu open ("Layout" opened if closed), following "Grid" closes the menu: on routes it lands on `/docs/grid`, and back returns to the same `/docs/modal` document (client-side history, or the back-forward cache); on the one page the URL becomes `/docs#grid` with one new entry and Grid's heading on its line, and back returns to `/docs#modal` in the same document; the menu closed both times. |
| shell | `breadcrumb-sticky` | `/docs#modal` (375 × 812) | Scrolled to the top first; relative to the breadcrumb's own natural top t (the static site's sits about 37 px higher, with no banner): `is-sticky` within 1 s at 400 px and at ceil(t) + 2, gone at floor(t) - 1, floor(t) - 20 and the top. |
| shell | `breadcrumb-chapter` | 7 docs routes (375 × 812) | Within 1 s of the load the last item names the route's category (on the one page the spy sets it for the deep link's section); the first is "Documentation": on the one page a `type=button` button with `aria-controls="documentation-menu"`, on routes the oracle's link to `/docs`. |
| one-page | `spy-deep-link` | `/docs#input` | The browser's fragment scroll puts Input's heading on the scroll-padding line (within 2 px); the nav's one current link is `#input` (`aria-current="true"`), Forms open with its summary alone current, the chapter Forms, the title "Input • femto", the URL kept. |
| one-page | `spy-deep-link-small` | `/docs#input` (375 × 812) | The same under the sticky breadcrumb. |
| one-page | `deep-link-cold` | `/docs#input` (cold cache) | Criterion 15: Input's heading on its line, and in Chrome the buffered `layout-shift` entries without recent input sum below 0.01, read 1 s after the page is ready (Firefox and Safari have no such entries: noted, position only). |
| one-page | `nojs-deep-link` | `/docs#forms` (JavaScript off) | Forms' heading on its line, scrolled down, the title unchanged (no script ran). Chrome and Firefox; skipped in Safari. |
| one-page | `spy-scroll` | `/docs` | Grid's heading 40 px past its line: the nav marks `#grid` and the title is "Grid • femto" at once, and one `replaceState` writes `/docs#grid` 180 ms or more after the jump, no new entry; at the top plain `/docs`, "Documentation • femto", `#quick-start`; at the bottom `/docs#tooltip`. |
| one-page | `spy-fast-scroll` | `/docs` | 200 px every 16 ms, top to bottom, in the page: at most 3 `replaceState` calls, ending on `/docs#tooltip`. |
| one-page | `spy-categories` | `/docs` | The nav's links are menu.json's 40 sections in order; for each, the section's heading on its line: its link alone current, its category's summary alone current and open, the chapter its category, the title its own, and (Phase 6, critic-8) two frames later the current link's box inside the side nav's (1 px slack) with the page where the check scrolled it, every scroll event since then reporting that `scrollY` within 1 px (docs.js `revealInNav` scrolls the side nav, never the page); a closed Forms opens again when Input becomes current. |
| one-page | `spy-chapter-small` | `/docs` (375 × 812) | The breadcrumb's chapter follows the spy: Customization, Layout, Content, Forms, Components, and Getting started at the top. |
| one-page | `spy-nav-click` | `/docs#modal` | From 200 px into Modal, a real click on Container: `/docs#container`, one new entry, the heading on its line, the nav straight to `#container` (never a section in between), Layout current, the title; the scroll animated with `html` smooth during it, `auto` after. |
| one-page | `spy-nav-click-reduced` | `/docs#modal` (reduced motion) | The same click under `prefers-reduced-motion: reduce` jumps: at most 2 scroll positions, never smooth. In Safari it runs only in the owner's pass with macOS's Reduce Motion on (`tests/owner-safari.sh reduced`); skipped as `motion:reduce` otherwise. |
| one-page | `spy-back-forward` | `/docs#modal` | After that click, back: `/docs#modal` at the exact position or with Modal's heading on its line (Chrome), the nav `#modal`; forward: `/docs#container`; neither animated. |
| one-page | `spy-reload` | `/docs#css-variables` | 900 px into the section, `location.reload()` keeps the URL and the exact position or the heading on its line, the nav `#css-variables`; WebDriver's refresh keeps the URL and the section. |
| one-page | `theme-first-frame` | `/docs?theme=jade#grid` (cold cache, jade's file held 300 ms) | One theme stylesheet, jade's, in `<head>`, held (resource timing; not in Safari); `DOMContentLoaded` after it arrived (parser-inserted: it holds back the deferred scripts, a script-added `<link>` does not); `--femto-primary` not azure's. In Chrome and Firefox a first-contentful-paint entry within 3 s, the first contentful paint after the file arrived and the first animation frame already jade's; in Chrome also `renderBlockingStatus` `blocking`. Firefox holds its paint because the color-scheme head script, parser-blocking, comes after the `?theme=` one and waits for the stylesheet (Decisions 8 and 14): `p3f-head-tff-1` to `-3` paint at 492 to 498 ms, after the file's 355 to 359; with the two merged into one script, `p3f-head-neg-merged-1` paints at 181 ms, before it, and fails. Safari's paint asserted as Chrome's when it has the entries. |
| one-page | `theme-kept` | `/docs?theme=jade#grid` | `?theme=jade` survives the spy (`#modal`) and nav clicks (`#forms`); Quick start ends on plain `/docs?theme=jade` with its heading on its line and the page's title; jade the one theme stylesheet throughout. |
| one-page | `theme-unknown` | `?theme=bogus`, `azure`, `JADE`, `..%2Fthemes%2Fjade`, `jade.css` on `/docs` | No theme stylesheet, `--femto-primary` azure's; the query stays as given, through the spy too (`/docs?<query>#grid`). |
| shell | `example-forms` | `/docs#forms`, `/docs#group`, `/docs#color-schemes`, `/docs#theme-picker` | Enter in every enabled text-like input and a click on every submit button of every content form: no navigation, no reload, every submit event canceled. `/docs#input` left the list in Phase 4, when its two `<form>` wrappers (no submit button, `wcag/h32`) were removed. |
| getting-started | `picker-options` | `/docs#theme-picker` (one page) | Three option switches (responsive-spacings, fixed-typography, no-transitions; `role=switch`, each described by its helper), off on load; they regenerate the three samples exactly (the cdn links in load order then `styles.css`, the combine URL or femto's link alone, the template's links) on load and after five sets of options, and leave the page's own stylesheets as loaded. |
| getting-started | `picker-code-highlight` | `/docs#theme-picker` (one page) | The three samples are exactly Prism's markup tokens for their `<link>` lines on load and after option changes and swaps (all options; jade with all; jade with fixed-typography; azure with none), the template's other lines keeping their load-time tokens; azure with no options gives the load-time tokens. |
| getting-started | `picker-swatch` | `/docs#theme-picker` (one page) | Each swatch is labeled with its own color. Pumpkin's swatch: scroll kept, `/docs?theme=pumpkin#theme-picker` with no new entry (criterion 7: the picker swaps the theme and updates `?theme=`), and the theme example, samples, labels, every `aria-current` outside the side menu, `--femto-primary` and theme stylesheets as a fresh load of pumpkin has them (tree snapshots); the example form keeps what was typed; options survive a swap to jade; a reload keeps jade; azure's swatch (no `?theme=`, no theme stylesheet) works. |
| getting-started | `picker-logo` | `/docs#theme-picker` | The header logo is `femto-logo` on load; pumpkin's swatch (a route change on routes, `?theme=` on the one page) makes it `femto-logo animated` within 2 s and `femto-logo` again 900 to 1500 ms later, no other step. |
| getting-started | `picker-swatch-focus` | `/docs#theme-picker` | Enter on pumpkin's focused swatch swaps to pumpkin with focus kept on it; Tab reaches orange's, Enter swaps to orange with focus on it. **XFAIL on the oracle** at "focus stays on pumpkin's swatch" (its remount drops focus to `<body>`). |
| getting-started | `picker-links` | `/docs#theme-picker` (one page) | With fixed-typography on, the side menu's `#theme-picker` from pumpkin (`?theme=` kept), the footer's `/docs#theme-picker` from azure, and the footer's from jade (`?theme=jade` kept: docs.js makes it the fragment navigation) put the heading on its line, a new entry only for a new URL, the options kept; back from jade's returns in the same document, jade kept, to the bottom or the entry's section heading. |
| getting-started | `picker-unknown-theme` | `/docs?theme=bogus#theme-picker`, `/docs?theme=JADE#theme-picker` (one page) | An unknown `?theme=` is ignored by the picker as by the head script: no theme stylesheet, azure's swatch current, "Azure", azure's samples, the query as given; jade's swatch then sets `?theme=jade`. |
| getting-started | `picker-popstate` | `/docs#theme-picker` (one page) | Jade's swatch, a fragment navigation to `#themes` and pumpkin's swatch: back shows jade (current swatch, stylesheet, samples), forward pumpkin, in the same document. |
| getting-started | `color-schemes-toggle` | `/docs#color-schemes` | The page's own switcher toggles the scheme and storage and relabels itself and the header toggle; the header toggle drives it too. |
| customization | `color-modal-open` | `/docs#colors` | Red 500's button (in `div.shades`; the oracle's `main`) opens one `dialog.color` (header class, "Red 500", "Shōjōhi Red", glow of the family's main color, femto.colors.css's red 550 on the one page, and the five labelled values: hex, RGB, the two utility classes, the custom property; on routes the oracle's six, with the Sass variable); Escape closes; Slate's family header opens slate 600. |
| customization | `color-modal-arrows` | `/docs#colors` | Right and Left step shades, Down and Up step families, wrapping at both ends (red 50 to slate 950 and back). |
| customization | `color-modal-close` | `/docs#colors` | The close control (a button from Phase 4), a backdrop click and Escape close it (no open dialog, no modal class); a click inside the article does not. |
| customization | `color-modal-close-url` | `/docs#colors` | The close control leaves the URL and history as they were. **XFAIL on the oracle** (`#close`). |
| customization | `color-modal-focus` | `/docs#colors` | Enter on a focused shade button opens the modal with focus inside it; Escape returns focus to the button. **XFAIL on the oracle** (no focus management). |
| customization | `color-modal-tab` | `/docs#colors` | Tab and Shift+Tab in the open modal keep focus inside the dialog and leave `scrollY` as it was; Escape returns focus to the button. **XFAIL on the oracle** at "Tab keeps focus inside the dialog". |
| customization | `color-modal-arrows-small` | `/docs#colors` (375 × 480) | Where the open modal's article overflows, the arrow keys step colors without scrolling the article or the page. |
| customization | `color-modal-focus-small` | `/docs#colors` (375 × 480) | Enter opens the modal with focus on its close control (`header .close`), not the scrollable article; Escape returns focus to the button. **XFAIL on the oracle** at "focus moves to the close link". |
| customization | `color-modal-resize` | `/docs#colors` | The open modal's article has `max-height: calc(<innerHeight>px - 2rem)` at 1300 × 900 and after resizes to 1300 × 600 and 1300 × 760. |
| customization | `color-modal-tab-cycle` | `/docs#colors` (one page) | In the open modal focus starts on the close button; Tab steps through the five copy buttons and wraps to it; Shift+Tab goes back to the last; Enter there copies `var(--femto-color-red-500)`; Escape returns focus to the shade button. From Phase 6 each button's computed name is its icon's label alone (a11y-1): "Close", then "Copy hexadecimal color", "Copy RGB color", "Copy color utility class", "Copy background utility class" and "Copy custom property", the last also while its ✓ shows after the copy. In Safari each Tab is Option+Tab, which colors.js treats as Tab. |
| customization | `palette-download` | `/docs#colors` | The Download link (text "Download the palette (JSON)"; on routes the oracle's "Download") points at a same-origin resource that holds the 20 × 19 palette as two-space JSON, with the SHA-256 of the oracle's download. |
| layout | `grid-columns` | `/docs#grid` | Add and Remove column from 4 up to 10 and down to 1 (clamped both ways): the columns, the code text and its highlighted tokens follow every click. |
| content | `font-size-units` | `/docs#typography` | The "Display in rem" switch turns the px table (values and formula tooltips) into percentages and multipliers without tooltips, and back to the exact load-time tree. |
| content | `font-size-restored-switch` | `/docs#typography` | With the "Display in rem" switch restored as checked on a reload (Firefox; a preload script in Chrome; Safari, which brings it back unchecked, ends at the px table), the table shows rem from load, and one click restores the exact px table. **XFAIL on the oracle** at "with the switch restored as checked, the table shows rem". |
| content | `table-inverse-thead` | `/docs#table` | The color-schemes example's thead and its sample read `data-theme="dark"` on a light page and follow the header toggle. |
| content | `table-inverse-thead-dark-os` | `/docs#table` (dark OS) | They read `light`. |
| content | `link-examples` | `/docs#link` | The 6 example links ("Links example": Primary, Secondary, Contrast; "Current link example": Regular link, Current link, Regular link, which the oracle on routes calls "Active link example" and "Active link"; each pointing at its own route, or on the one page at `/docs` or `/docs#link`) go nowhere, clicked and with Enter: the document, URL, history, scroll position and tabs unchanged, every click canceled. |
| forms | `checkbox-indeterminate` | `/docs#checkboxes` | The example checkbox is indeterminate after load with no added attributes; a click checks it. |
| components-a | `dropdown-items` | `/docs#dropdown` | The 45 example links (four items in each of the eleven link dropdowns, plus the nav example's "Services") go nowhere. Pointer: each dropdown is opened once from its summary and its items are clicked in turn. Keyboard: Enter on the summary, Tab to each item, Enter. After each click or Enter, the window marker, URL, history.length and scroll position are unchanged, the dropdown stays open and the click is defaultPrevented; after an Enter, focus stays on the item. |
| components-b | `modal-demo` | `/docs#modal` | "Open modal" opens the demo dialog ("Confirm your membership"; on routes the oracle's "Confirm Your Membership"); once its opening animation ends, Cancel, Confirm and the backdrop close it and a click inside does not; the two example dialogs stay open and their buttons do nothing. |
| components-b | `progress-value` | `/docs#progress` | Watched 16 s on screen: an integer 5 to 94 with `max="100"`, the sample printing the same value (`<progress value="N" max="100"></progress>`; on routes the oracle's `/>`), at least two changes, each a whole number of 5 s periods (± 400 ms) after the last. |
| components-b | `progress-offscreen` | `/docs#progress` (1300 × 300) | No change for 10.5 s while the bar is below the viewport; on screen, changes 5 s and 10 s later; above the viewport, none for 10.5 s (intervals run only on screen). **XFAIL on the oracle** at "no change for 10.5 s while the example is below the viewport". |
| components-b | `progress-pause` | `/docs#progress` (one page) | Phase 6 (a11y-8, WCAG 2.2.2): `button[data-progress-pause]`, before the example in its section and hidden in the markup, is shown once docs.js runs: rendered, `type="button"`, "Pause", no `aria-pressed` or `aria-label`, its computed name its text. On screen the value changes within 10.4 s; a click gives "Play" and no change for 10.5 s; a second click gives "Pause" and a change 5 s after it (10 s when a draw repeated the value, ± 400 ms), the sample printing each value. |
| components-b | `progress-reduced-motion` | `/docs#progress` (`prefers-reduced-motion: reduce`; one page) | The example starts paused: the button reads "Play", the value drawn on load is a whole number from 5 to 94 that the sample prints, and nothing changes for 10.5 s on screen; Play gives "Pause" and a change 5 s after the click. In Safari, the owner's Reduce Motion pass. |
| components-b | `nav-example-links` | `/docs#nav` | The 28 example links of the examples' navs, dropdown items included (on routes 31, with the oracle's `overflow-with-focus` nav's 3, which Phase 4 removed from the section), go nowhere, clicked and with Enter: document, URL, history and scroll kept, dropdowns open, every click canceled. |
| components-b | `tooltip-link` | `/docs#tooltip` (1300 × 500) | On routes the example link (`href="/docs/tooltip"`), clicked scrolled down, ends at `/docs/tooltip` at scrollY 0 with no new history entry; on the one page it points at `/docs#tooltip`, and the click, in the same document, ends there with Tooltip's heading on its line and a new entry only for a new URL. The oracle keeps the document (Remix's client-side navigation); the static site's plain link loads it again, which the check notes and does not assert (PLAN.md Conversion rules: plain `<a>` replaces Link). |
| components-b | `tooltip-link-same-hash` | `/docs?theme=jade#tooltip` (1300 × 700; one page) | Phase 6 (urls-1): scrolled 200 px past the heading's line, with the URL still the deep link's, a real click on the example link (`/docs#tooltip`, the URL's own hash) puts Tooltip's heading on its line within 3 s, keeps the URL and `history.length`, the document and jade's stylesheet; `<html>` gains `is-scrolling-to-link` within 100 ms of the click and loses it within 250 ms of the last scroll event, not after the 1 s `SCROLL_STALL`. Before the fix, docs.js cancelled the click and set the same hash, which does nothing. |
| landing | `demo-loop` | `/` | Up to 100 s: the form's phases are exactly the demo's 15 (email ... range-50) and then email and invalid again; each phase's markup shows in the code while the form is in it; the fields carry each phase's values; at least 50 typed characters. From Phase 6, on the one page only (the oracle's form differs): the date-next phase's Next button has no `type`, as the code's `<button>Next</button>` has none, and during search-busy the code holds `placeholder="Search" disabled`, as the form's input is disabled (content-c-3, content-c-4). |
| landing | `demo-variant` | `/` (1280 × 800) | The large code layout at 1280, the small one at 1279 and 375 and the large again at 1280, each within 3 s and each time started over at the first phase. |
| landing | `comparison-toggle` | `/` | The comparison's code samples read `light`, then `dark` and `light` after header-toggle clicks. |
| landing | `demo-offscreen` | `/` | The demo changes on screen; above the viewport (after 2 s to settle) no change for 7 s; back on screen it changes within 5 s. **XFAIL on the oracle** at "no change for 7 s while the demo is above the viewport" (TypeIt runs off screen). |
| landing | `demo-pause` | `/` (one page) | `button[data-demo-pause]`, hidden in the markup, is shown once demo.js runs (rendered, `type="button"`, "Pause", the cursor's blink running) and the demo changes within 4 s. A click relabels it "Play": the code and the form (markup and values) do not change for 6 s and the blink is paused. A second click relabels it "Pause", the blink runs and the demo changes within 4 s. |
| landing | `demo-reduced-motion` | `/` (`prefers-reduced-motion: reduce`; one page) | The demo starts paused: the button reads "Play", the blink is paused, the code shows the first phase's markup and the form its one empty, valid email input, and nothing changes for 6 s (unpaused, the first phase would start at 1.75 s). A click on Play relabels it "Pause", the blink runs and the demo changes within 4 s. In Safari, the owner's Reduce Motion pass (Phase 6). |
| examples | `examples-structure` | `/examples` | Each `section.example` has one `div[data-example]` whose shadow root holds only a div with its own shadow root: there femto's `dist/femto.min.css` link (loaded, nothing else styled) and then exactly the Markup sample's markup; no id repeats on the page, shadow roots included. |
| examples | `examples-isolation` | `/examples` | Every element of every mockup (host and pseudo-elements included) has the computed style, every property and every custom property femto names, of a document that loads femto alone around the same markup: no site CSS reaches in. |
| examples | `examples-isolation-dark` | `/examples` (dark OS) | The same with the OS dark. |
| examples | `examples-isolation-stored` | `/examples` (stored dark) | With a stored dark choice on a light OS, every inner host has `data-theme="dark"` and the styles equal the femto-only document's with it. |
| examples | `examples-scheme` | `/examples` | The inner hosts follow `<html>`'s `data-theme`: none on load, dark and light again with the header toggle, their background with them. |
| examples | `examples-forms` | `/examples` | Each mockup form submitted with a real click on its submit button (and the search with Enter): every submit canceled, document, URL and history kept. |
| examples | `examples-links` | `/examples` | Every visible mockup link, clicked and with Enter, goes nowhere: canceled, document, URL and history kept. |
| examples | `examples-dialog` | `/examples` | The confirmation dialog opens as a modal with focus inside; Escape, its close button, Cancel, Delete project and a backdrop click close it with focus back on the opener (examples.js puts it there: in Safari a click does not focus the button); a click on its text keeps it open. |
| examples | `examples-dropdown` | `/examples` | The navigation bar's Account dropdown opens on its summary and closes on a click outside. |
| examples | `examples-fit` | `/examples` (375 × 812) | At 375 × 812 the page does not scroll sideways and no mockup element leaves its frame (outside a scrolling `.overflow-auto`). |
| examples | `examples-first-frame` | `/examples` (stored dark) | With a stored dark choice, the first frame that has the mockups already shows them dark with femto applied; no transition runs after load. Skipped in Safari (`preload`). |
| examples | `examples-first-frame-cold` | `/examples` (cold cache) | With the cache emptied, the first frame that has the mockups already has femto applied in every root; no transition after load. Skipped in Safari (`preload`). |

### Proof

Phase 6's runs, and the runs that show each new assertion failing where it should, are in Harness
proof, Phase 6.

Phase 4 (2026-11-05, the same rig: Chrome Beta 158.0.8127.18, Firefox 160.0, Selenium 4.52.0; the
working tree after the Phase 4 writers and the a11y agent, built by the checks agent into its scratch
folder, `dist:<build>`):

| Run id | Command | Runs | Result |
|---|---|---|---|
| `p4-checks-behavior-dev-1` | `behavior --target dist:<build> --workers chrome=2,firefox=2 --checks` the 17 new and changed checks | 52 | PASS: 52 PASS; 29 s |
| `p4-checks-behavior-1` | `behavior --target dist:<build>`, every check (criterion 7 in Chrome and Firefox) | 230 | **PASS: 230 PASS** (115 per browser), 0 FAIL, 0 ERROR; 349 s |
| `p4-checks-behavior-neg-1` | `picker-options`, `picker-code-highlight` and `mobile-menu-inert` against a copy of the build whose picker.js writes the options' links in another order (`fixed-typography` first) and whose docs.js leaves the page behind the open menu not inert | 6 | FAIL as intended, all six: the two picker checks at "codes regenerated" with all three options on, `mobile-menu-inert` at "every element outside the menu is inert" |
| `p4-checks-behavior-oracle-1` | `behavior --target oracle` (routes layout) | 230 | **PASS: 114 PASS, 24 XFAIL** (12 per browser, each at its named assertion), **92 SKIP** (46 per browser, `layout:routes`), 0 FAIL, 0 XPASS; 248 s. The branches that assert the oracle's own markup (five modal rows against six, 28 nav links against 31, the copy links, the breadcrumb link) hold it |
| `p4-checks-a11y-1` | `a11y --target dist:<build>` (criterion 10) | 40 cells | FAIL on 2 targets in 1 rule (Accessibility, Phase 4), 0 errors; 39 s |
| `p4-checks-selftest-1` | `selftest --browsers chrome,firefox` | 70 controls | **PASS: 70 of 70** |
| — | `registry`; `static_checks.py --phase 4 --dist <build>` | 246 entries; 15 criteria and the link check | valid; 3, 4, 5, 6, 8, 11, 12, 13, 14 and the link check PASS (the link check's 6 controls fail as intended), 9 and 15 FAIL (site content: the rules turned back on, and the `/docs` budget), 1, 2, 7 and 10 NOT-YET (the harness's) |
| `p4-fix-checks-1-modal-1` to `-5` | `behavior --target dist:<build> --checks modal-demo` after its clicks were made to wait for the opening animation to end (`-2` to `-5` while `p4-fix-checks-1-behavior-1` ran; review finding: Firefox FAILed once in a loaded full run at "a click inside the article keeps it open") | 2 each | PASS: 10 of 10; the new waits took 0.36 to 0.45 s |
| `p4-fix-checks-1-modal-neg-1` | `modal-demo` against a copy of the build whose site.js closes the demo on any click inside the dialog | 2 | FAIL as intended, both browsers, at "a click inside the article keeps it open: the demo dialog is open" |
| `p4-fix-checks-1-behavior-1` | `behavior --target dist:<build> --workers chrome=2,firefox=2`, every check | 230 | FAIL: 228 PASS, 2 FAIL, both `link-examples` at "the six example links": the Link section now names its example "Current link example" and its link "Current link", and the check still wants "Active link"; `modal-demo` PASS in both browsers |
| `p4-fix-checks-2-behavior-dev-1` | `behavior --target dist:<build> --workers chrome=2,firefox=2 --checks` the seven fixed and new checks (`link-examples`, `copy-keyboard`, `pre-scroll-keyboard`, `modal-two-dialogs`, `example-forms`, `demo-pause`, `demo-reduced-motion`) | 22 | PASS: 22 PASS. `copy-keyboard`: both routes' first blocks do not overflow, and Tab moved on to the Secondary button (`/docs#button`) and the next mockup's frame (`/examples`); `pre-scroll-keyboard`: the overflowing block is `tabindex="0"`, `role="figure"`, "HTML code"; `modal-two-dialogs`: `modal-is-opening` 95 and 100 ms and `modal-is-open` 447 and 450 ms after the `click()` (Chrome, Firefox) |
| `p4-fix-checks-2-neg-1` | `copy-keyboard`, `modal-two-dialogs` and `demo-pause` against a copy of the build whose site.js keeps every code block a tab stop (`if (true)` for `overflows[i]`) and gives the demo dialog no `modal: true`, and whose demo.js ignores the pause (`running = () => onScreen`) | 8 | FAIL as intended, all eight: `copy-keyboard` at "the block does not overflow: no tab stop, role or name" (both routes), `modal-two-dialogs` at "the demo is a true modal (:modal) with focus inside it", `demo-pause` at "paused: no change to the code or the form for 6 s" |
| `p4-fix-checks-2-neg-2` | `demo-reduced-motion` against a copy whose demo.js does not start paused under reduced motion | 2 | FAIL as intended, both browsers, at "the script shows it reading Play" |
| `p4-fix-checks-2-neg-3` | `modal-two-dialogs` against a copy whose site.js `createModal` no longer hides the dialog that holds `<html>`'s classes when another opens | 2 | FAIL as intended, both browsers, at "the color modal is open with modal-is-open alone" (the demo stays open under it) |
| `p4-fix-checks-2-behavior-1` | `behavior --target dist:<build> --workers chrome=2,firefox=2`, every check (04:13 build) | 232 | FAIL: 228 PASS, 4 FAIL, text another writer changed in the same round: `modal-demo` at "the demo is 'Confirm Your Membership'" (now "Confirm your membership") and `palette-download` at "its text" (now "Download the palette (JSON)"); both now take the Phase 4 text on the one page and the oracle's on routes |
| `p4-fix-checks-2-behavior-2` | `behavior --target dist:<build> --workers chrome=2,firefox=2`, every check (04:23 build), criterion 7 in Chrome and Firefox | 232 | **PASS: 232 PASS** (116 per browser), 0 FAIL, 0 ERROR; 231 s |
| `p4-fix-checks-2-oracle-1` | `behavior --target oracle --checks` the nine changed checks (routes layout) | 26 | PASS: 14 PASS (`link-examples` "Active link", `modal-demo` "Confirm Your Membership", `palette-download` "Download", `example-forms` on four routes), 12 SKIP (`layout:routes`) |
| `p4-fix-checks-2-a11y-1` | `a11y --target dist:<build>` (04:23 build, criterion 10) | 40 cells | FAIL on 2 targets in 1 rule, 0 errors: `color-contrast` on Group's current button (`button[aria-current="true"]` "Week") in the dark cells of `/docs` (white on `#017fc0`, 4.37:1) and `/docs?theme=jade` (white on `#00895a`, 4.44:1); site content, not the harness; 26 s |
| — | `npx html-validate` with `.htmlvalidate.mjs` on the build's four pages; the same with `no-redundant-role`'s `exclude` emptied; `static_checks.py --phase 4 --criteria 9,13,14 --dist <build>`; `npm run lint` | 4 pages; 3 criteria | exit 0 with `exclude: ["button"]` (the unused `"group"` dropped); 13 `no-redundant-role` errors on `/docs` with it emptied (every one `summary[role=button]`, in Accordion and Dropdown), so the one left is used; 9, 13 and 14 PASS; lint exit 0 |

Phase 3 (2026-11-04, the rig as Phase 2: Chrome Beta 158.0.8127.18, Firefox 160.0, Selenium 4.52.0;
the one page built from the working tree while the other Phase 3 agents were still changing it, into
the behavior agent's scratch folder, `dist:<build>`; run ids under `tests/results/`):

| Run id | Command | Runs | Result |
|---|---|---|---|
| `p3-behavior-oracle-1` | `behavior --target oracle` (routes layout) | 186 | **PASS: 124 PASS, 24 XFAIL** (12 per browser: the eleven oracle-bug checks, `color-scheme-flash` on two routes, each at its named assertion), **38 SKIP** (the `one-page` group, 19 per browser, `layout:routes`), 0 FAIL, 0 ERROR; 290 s |
| `p3-behavior-dev-5` | `behavior --target dist:<build>` (18:23 build) | 186 | FAIL: 177 PASS, 9 FAIL. Check bugs, fixed since: `link-examples`, `dropdown-items` and `nav-example-links` wanted `/docs#<section>` where the site writes the page's own `/docs` for its do-nothing links (`self_href` takes both). Site bugs: `picker-swatch` (azure's swatch does nothing after a load with `?theme=`) and Firefox's `spy-nav-click` (below) |
| `p3-behavior-dist-1`, `p3-behavior-dist-2` | `behavior --target dist:<build>` (18:44 and 18:55 builds), final checks | 186 each | FAIL: 184 PASS (92 per browser), 2 FAIL, both `picker-swatch` at "azure: the URL's query is empty", a site bug: picker.js sets the swap's `target` to the file's color (azure) before it shows the `?theme=` color, so after a load with `?theme=` azure's swatch does nothing. 351 s and 344 s |
| `p3-behavior-navclick-1` to `-4` | `behavior --target dist:<build> --checks spy-nav-click` | 2 each | Chrome PASS 4 of 4; Firefox PASS 3 of 4 (and FAIL in 4 of 6 earlier runs while other agents' runs loaded the machine) at "the nav never shows a section in between": headless Firefox draws this page's smooth scroll at 80 to 160 ms a frame, its first frame came more than 150 ms after the click, and docs.js's lock (150 ms without a scroll event) let go first. A site robustness issue, not a check bug |
| `p3-behavior-neg-nospy-1` | the `one-page` group against a copy of the build with the spy's `widgets("spy", spy)` call and the head script's `document.write` removed | 38 | FAIL as intended: 34 FAIL; the 4 PASS are `deep-link-cold` and `nojs-deep-link`, which hold the browser's own fragment scroll |
| `p3-behavior-neg-smooth-1`, `-2` | four spy checks against a copy with `html { scroll-behavior: smooth }` added to docs.css | 8 and 4 | `spy-back-forward` FAILs in both browsers at "back is not animated", `spy-nav-click` in Chrome at "html scrolls instantly again", and `spy-deep-link` (both widths) in Chrome at "the load's jump to #input is not animated" (05's finding); `spy-nav-click-reduced` passes, since femto's own `prefers-reduced-motion: reduce` rule turns any smooth scrolling off |
| `p3-fix-behavior-r1-tff-2` | `theme-first-frame` against the build, jade's file held 300 ms (fix round 1) | 2 | PASS. Chrome: held 318 ms, `blocking`, DOMContentLoaded 408 ms after the file's 351, first contentful paint 456, first frame jade's. Firefox: held 338 ms, DOMContentLoaded 427 ms after the file's 382; its first contentful paint at 155 ms, before the file (noted) |
| `p3-fix-behavior-r1-neg-append-1`, `-2` | `theme-first-frame` against a copy whose head script adds the theme `<link>` with `createElement` and `document.head.append` | 2 each | FAIL as intended, all four at "DOMContentLoaded waits for the theme stylesheet (parser-inserted)"; Chrome's detail has `non-blocking`, an azure first frame and a paint before the file too. Without the hold (the review's `p3-review-behavior-r1-neg-append-1`, `-2`) this variant passed |
| `p3-fix-behavior-r1-neg-1` | `picker-links` and `mobile-menu` against a copy whose docs.js pushes a history entry when the mobile menu opens and never rewrites a `/docs#<id>` link clicked on `/docs?theme=` | 4 | FAIL as intended: `mobile-menu` at "opening leaves the URL" (the same URL, `history.length` one more: `url_kept` before fix round 1 passed it), `picker-links` at "footer from jade link: the URL is the picker's" (the page reloaded at `/docs#version-picker`, the theme lost) |
| `p3-fix-behavior-r1-oracle-1` | `behavior --target oracle` with fix round 1's checks | 186 | **PASS: 124 PASS, 24 XFAIL, 38 SKIP**, as `p3-behavior-oracle-1`; 662 s (waiting for slots) |
| `p3-fix-behavior-r1-dist-1` | `behavior --target dist:<build>` (20:05 build) | 186 | FAIL: 184 PASS, 2 FAIL, both `picker-swatch` at "azure: current as on a fresh load": a check bug, fixed since. Azure's swatch was clicked with its own scroll into view, from the select below, which left the picker's heading under the line, so the spy rightly marked Quick start; the swatch is now clicked from the check's starting position (`p3-fix-behavior-r1-swatch-4`, `-5`: PASS, with `picker-links` and `theme-first-frame`; `p3-fix-behavior-r1-oracle-swatch-1`: PASS on the oracle) |
| `p3-fix-behavior-r1-dist-2` | `behavior --target dist:<build>` (20:38 build, every fix round 1 change) | 186 | **PASS: 186 PASS** (93 per browser), 0 FAIL, 0 ERROR; 348 s |
| `p3f-head-checks-1`, `p3f-head-tff-1` to `-3` | `theme-first-frame` (Firefox's paint now asserted) and the new `modal-two-dialogs` against a build with the two inline head scripts (the Phase 3 finish, 22:17 build) | 4 each | PASS 4 of 4 each time. `theme-first-frame`: jade's file held 310 to 327 ms; Chrome's first contentful paint at 468 to 476 ms, Firefox's at 492 to 498 ms, each after the file's responseEnd (352 to 365 ms), both first frames jade's. `modal-two-dialogs`: the color modal open and the demo closed in one step 67 to 86 ms after Enter, `modal-is-open` 360 to 367 ms later in `p3f-head-checks-1` (then timed from the step before, with a 350 ms floor: see `p3f-head-m2d-1` to `-7`); Escape's steps at 0 ms and 433 to 440 ms |
| `p3f-head-neg-merged-1` | `theme-first-frame` against a copy whose `docs.html` has the two head scripts merged into one again (the color-scheme part first, as before the split) | 2 | FAIL as intended in Firefox at "the first contentful paint comes after the theme stylesheet arrived" (paint at 181 ms, the file's responseEnd at 357, azure's first frame); Chrome PASS (it holds the paint for the render-blocking stylesheet either way) |
| `p3f-head-neg-nohide-1` | `modal-two-dialogs` against a copy whose site.js `createModal` no longer hides the dialog that holds `<html>`'s classes when another opens | 2 | FAIL as intended in both browsers at "the color modal is open with modal-is-open alone" (the demo stays open under it) |
| `p3f-head-behavior-1` | `behavior --target dist:<build>` (the 22:17 build), every check | 188 | **PASS: 188 PASS** (94 per browser), 0 FAIL, 0 ERROR; 350 s |
| `p3f-head-oracle-1` | `behavior --target oracle --checks modal-two-dialogs,theme-first-frame` (routes layout) | 4 | PASS: 4 SKIP (`layout:routes`), as a full oracle run's 20 per browser |
| `p3f-head-m2d-1` to `-7` | `modal-two-dialogs` with each step timed from the key (`modal-is-open` 350 to 800 ms after Enter, no class 350 to 800 ms after Escape), against the 23:02 build. The review found it flaky in Firefox (`p3f-review-behavior-1`: 187 of 188; `p3f-review-m2d-1` to `-5`: FAIL 1 of 5) at "`modal-is-open` after 350 to 700 ms", then timed from the `modal-is-opening` step: colors.js starts the 400 ms timer and then focuses the close link, which lays out the long page, so the observer saw that step late and the gap was 343 and 349 ms | 2 each | PASS 14 of 14 (`-7` after the last docstring edit). After Enter: `modal-is-opening` at 67 to 77 ms in Chrome and 81 to 105 ms in Firefox, `modal-is-open` at 440 to 449 ms in both (`p3f-head-m2d-3`'s Firefox gap between the two was 342 ms, which the old floor would have failed); after Escape: `modal-is-closing` at 0 to 1 ms, no class at 433 to 485 ms |
| `p3f-head-neg-fast-1` | `modal-two-dialogs` against a copy whose site.js has `MODAL_DURATION = 250` | 2 | FAIL as intended in both browsers at "the color modal over the demo: color, modal-is-open 350 to 800 ms after the key" (287 ms in Chrome, 304 ms in Firefox) |
| `p3f-head-behavior-2` | `behavior --target dist:<build>` (the 23:02 build), every check, with the timing fix | 188 | **PASS: 188 PASS** (94 per browser), 0 FAIL, 0 ERROR; 347 s. `modal-two-dialogs`: `modal-is-open` 438 ms (Chrome) and 442 ms (Firefox) after Enter |

Phase 1 runs, on 2026-10-31 on the rig (Chrome Beta 158.0.8127.2, Firefox 160.0, Selenium 4.52.0), the
oracle at `remix-final` (`tests/results/<run id>/`, gitignored), with the Phase 1 checks:

| Run id | Command | Runs | Result | Wall clock |
|---|---|---|---|---|
| `p1-behavior-oracle-1` | `behavior --target oracle` | 108 (54 per browser) | FAIL: 98 PASS, 8 XFAIL, 2 FAIL, both `picker-swatch` at "one new history entry" (50 against 51: the session's one tab had reached the 50-entry history cap). Fixed in the harness: every check now starts in a fresh tab | 189 s |
| `p1-behavior-oracle-2` | the same, final code | 108 | **PASS: 100 PASS, 8 XFAIL** (the three oracle-bug checks, each at its named assertion, in both browsers), 0 FAIL, 0 XPASS, 0 ERROR | 401 s (about 190 s of checks per browser; the rest waiting for harness slots other runs held) |
| `bh-negative-nojs-2` | a negative control, final code: every check against a scratch proxy that serves the oracle with every `<script>` removed, as a base URL (`--ready static`), so every widget is dead | 108 | FAIL: 85 FAIL, 0 ERROR, 23 PASS, and the PASSes are only the checks of server-rendered state (`breadcrumb-chapter`, `side-menu-current`, `header-landing`) plus `example-forms` on `/docs/forms/input` in Chrome, whose forms Chrome never submits on Enter (several text fields, no submit button); in Firefox that route FAILs (it submits from the date field) | 211 s |
| `p1-int-bh-oracle-1` | `behavior --target oracle`, at the Phase 1 integration (50 checks) | 132 (66 per browser) | **PASS: 112 PASS, 20 XFAIL** (the nine oracle-bug checks, `color-scheme-flash` on two routes, each at its named assertion in both browsers), 0 FAIL, 0 XPASS, 0 ERROR | 259 s |
| `p1-int-bh-dist-1` | `behavior --target dist`, the same checks against the integrated build | 132 | **PASS: 132 PASS**, 0 FAIL, 0 ERROR | 294 s |

Found while proving: 01 §2's last paragraph says the handler-less form at
`docs.forms._index.jsx:118` navigates on Enter. In Chrome 158 and Firefox 160 it does not: it has two
text fields and no submit button, which blocks implicit submission. The oracle's other example forms
cancel their submit events themselves (React `onSubmit` or a submit button's `onClick`), which is
why the static site needs the one delegated `submit` handler.

### Editing docs.js

Phase 1's route groups each owned a region of `site/assets/js/docs.js`, the text between their own
two marker lines `// region:<group>` and `// endregion:<group>`, for their small widgets
(getting-started, layout, content, forms, components-a, components-b). The protocol, moved here from
the file's header in round 1 of the Phase 1 fixes (it had shipped in `dist/`):

- Change only the text between your own two markers: never the marker lines, the base or another
  group's region.
- Hold an exclusive fcntl lock on `tests/results/.locks/docs-js.lock` (create the folder if it is
  missing) for the whole read, splice and write, and read the file again under the lock: never write
  back a copy read earlier. Do not use an editor that writes the whole file outside the lock. For
  example, with the region's new text (without the marker lines) in `<file>`, from the repository
  root:

  ```sh
  uv run - <group> <file> <<'PY'
  # /// script
  # requires-python = ">=3.12"
  # dependencies = []
  # ///
  import fcntl, pathlib, sys
  group, body = sys.argv[1], pathlib.Path(sys.argv[2]).read_text().strip("\n")
  locks = pathlib.Path("tests/results/.locks"); locks.mkdir(parents=True, exist_ok=True)
  with open(locks / "docs-js.lock", "w") as lock:
      fcntl.flock(lock, fcntl.LOCK_EX)
      js = pathlib.Path("site/assets/js/docs.js"); text = js.read_text()
      start, end = f"// region:{group}\n", f"// endregion:{group}\n"
      i, j = text.index(start) + len(start), text.index(end)
      js.write_text(text[:i] + (body + "\n" if body else "") + text[j:])
  PY
  ```
- Write the region as one call, `widgets("<group>", () => { ... })`, that holds all of it. Declare
  nothing at the module's top level (two regions must never clash) and add no import: site.js's
  exports are the `site` namespace (`site.pageTheme`, `site.switchTheme`, `site.onThemeChange`,
  `site.createModal`, `site.perFrame`). Keep no state shared between widgets (PLAN.md Conversion
  rules).
- Each widget returns at once when its markup is absent. From Phase 3 (PLAN.md Conversion rules) it
  binds to a `data-` hook on its root element, written in the file that holds the markup (a section
  file in `site/docs/sections/`, or `site/docs.html` for the base), and may narrow with selectors
  under the hook (`[data-font-size-demo] input[type=checkbox]`). A hook is named after what it is,
  never after an attribute femto's own CSS or JS uses (`data-theme`, `data-tooltip`,
  `data-placement`). Every hook a comparison sees is registered as one `merge-layout` attribute
  entry for `one-page` in `tests/divergences/p3-merge-layout.json`, shaped like
  `p3-picker-data-version-picker`: `kind` `attribute`, a selector ending in the hook, `property` the
  hook's name, `a` `null`, `b` its value, and the exact routes of the section comparison (a hook on
  `/`, `/examples`, `/demo` or the 404 page takes those page routes instead, as
  `p3-footer-docs-link-href-*` do). In Phases 1 and 2 widgets bound to the oracle's own markup (ids,
  classes, `aria-` attributes, structure) without adding attributes, since any added attribute was a
  parity difference with no category. From Phase 4 the parity comparisons no longer gate (PLAN.md
  Workflow), so a hook added or renamed in Phase 4 gets no registry entry; the Phase 3 entries stay
  for the Phase 3 comparisons. `widgets()` reports an exception without stopping the regions after
  it.
- The hooks: the base's `main[data-docs-spy]`, `aside[data-docs-menu]` (its Close button
  `button[data-menu-close]`) and `nav[data-docs-breadcrumb]` (its Documentation button
  `button[data-menu-open]`), in `site/docs.html`, outside every compared root, so no entry; the
  regions' `button[data-scheme-switcher]` (getting-started), `section[data-grid-example]` (layout),
  `section[data-font-size-demo]`, `section[data-inverse-thead]` and `article[data-link-example]`
  (content), `article[data-indeterminate-example]` (forms; on the example, since
  `checkbox-indeterminate` holds the checkbox to its own two attributes),
  `article[data-dropdown-example]` (components-a), `nav[data-nav-example]` and
  `article[data-progress-example]` (components-b), with the Progress section's
  `button[data-progress-pause]` (Phase 6: hidden in the markup and shown by docs.js, its box laid
  out invisibly by docs.css under `(scripting: enabled)` until then; `progress-pause`,
  `progress-reduced-motion`); and beside them site.js's `button[data-copy-link]`
  (a link until Phase 4; from Phase 6 named by `aria-labelledby` its icon's `copy-icon-<n>` id, which
  site.js assigns), the header's `button[data-scheme-toggle]`, `data-modal`, `data-modal-open`
  and `data-modal-close`, colors.js's `data-color-modal`, picker.js's `article[data-version-picker]`
  (the Theme picker's swatches; the hook keeps its Phase 3 name), `section[data-picker-options]` and
  `section[data-picker-usage]` (`cdn`, `combine`, `template`; Phase 4 removed
  `section[data-picker-configuration]` and `sass`), examples.js's `div[data-example]` on
  `/examples`, demo.js's `[data-comparison]` and `article[data-typing-demo]` on `/` with the demo's
  `button[data-demo-pause]` (Phase 4: hidden in the markup, shown by demo.js; `demo-pause`,
  `demo-reduced-motion`), and `pre[data-scroll-focus]`, which build.mjs writes on every highlighted
  `<pre>` (with `tabindex="0"`) and site.js reads to keep only a block that overflows in the tab
  order (Phase 4; `copy-keyboard`, `pre-scroll-keyboard`).

## Accessibility

The a11y mode holds the site to criterion 10: axe-core finds no serious or critical violation on any
page, in Chrome and Firefox, light and dark, at 375 and 1300.

```sh
uv run tests/run.py a11y --target dist                    # the criterion's 40 cells (48 until Phase 4, with /demo)
uv run tests/run.py a11y --target static-femto --pages /,/docs
uv run tests/run.py a11y --plan
```

- **axe-core** is the repository's own: `node_modules/axe-core/axe.min.js` at the exact version
  `package.json` pins (4.14.0), never downloaded; a missing or mispinned copy is a setup error (exit 2).
- **Pages** (`--pages`): `/`, `/examples`, the 404 page (`/does-not-exist`), `/docs`, and
  `/docs?theme=jade`, so a theme stylesheet's colors are checked too. `/demo` was one until Phase 4,
  which does not build it (PLAN.md Open questions 5).
- **Cells**: browser × page × scheme × width, 20 per browser. Each is loaded as a behavior check is
  (`harness/behavior.py` `Page.reset`: a fresh headless tab, the viewport set exactly with WebDriver
  BiDi to the width × 800, `prefers-color-scheme` emulated, storage emptied, the page loaded and the
  static readiness hook run). Then axe's source runs in the document through Selenium and
  `axe.run(document)` checks it whole. The script is injected, not loaded, so it makes no request.
  Each browser's session holds one machine-wide harness slot (Concurrency and locks), one session
  per browser unless `--workers` says more.
- **Verdict.** A serious or critical violation fails the run; moderate and minor ones are listed and
  do not. `result.json` keeps every cell's violations (rule, impact, help, each node's target selector,
  HTML and failure summary) and lists the findings once per impact, rule, page and target with the
  cells they were found in (`failing`, `listed`); `summary.txt` prints them in that order. Exit status
  0 when nothing fails, 1 otherwise or after a harness error, 2 for a setup error.

Found on 2026-11-04 against `static-femto` on `/` and `/docs` (`p3-harness-a11y-femto-1`, 16 cells,
8 s; not expected to pass, Phase 3 fixes the site): FAIL on two serious rules, `color-contrast` (the
doctype tokens of a code sample on `/docs`, in every cell) and `scrollable-region-focusable` (code
blocks whose `pre` scrolls but takes no focus, on `/` and `/docs`, more of them at 375); listed,
`landmark-unique` (moderate: two unnamed `nav` landmarks, and the docs menu `aside`).

Criterion 10 is gated in Phase 4, not Phase 3 (PLAN.md Workflow; the owner, 2026-11-04). On the one
page every serious or critical violation comes from the oracle's markup or femto's tokens, which
parity keeps through Phase 3, and each also fires on `static-femto`'s per-route pages
(`p3-harness2-a11y-femto-routes-1`). Phase 3's last run (`p3-review-behavior-3-a11y-1`, 48 cells,
0 errors) fails on 314 targets in 5 rules, which are Phase 4's accessibility items:
- `label` (critical): the Input section's `input[type=file]` has no label.
- `select-name` (critical): the Version picker's `select[name=configuration]` has no accessible name.
- `label-title-only` (serious): examples in Input and Textarea are named only by `title`.
- `color-contrast` (serious): Prism's comment and doctype tokens (`--femto-code-comment`), the Colors
  section's shade buttons on their own swatch color, and Group's `button[aria-current=true]` in dark.
  The swatches and Group's button are femto's styles, so their fix may belong in femto.
- `scrollable-region-focusable` (serious): `pre` code blocks and `div.overflow-auto` scroll but take
  no focus.

Phase 4's gate (`p4-gate-a11y-2`, the 40 cells, and `p4-gate-a11y-widths-2`, the same pages at
320, 768 and 1024: 100 cells, Chrome Beta 158 and Firefox 160, 0 errors) **passes: no serious or
critical violation**. Phase 4 fixed all five rules. Their last target, Group's
`button[aria-current="true"]` in dark (white on `#017fc0`, 4.37:1; jade's `#00895a`, 4.44:1), was
femto's own hover background, which femto's c608ee06 fixed (owner decision 15; amended into
33d4dc6f, the vendored commit, owner decision 2). Listed (moderate):
`landmark-unique` on the breadcrumb examples and the docs breadcrumb (femto styles breadcrumbs
through `nav[aria-label="breadcrumb"]`, so they share the name) and on the Dropdown section's nav
example.

axe reads each document once, as loaded, in the default color mode, so it says nothing about
forced colors, WCAG 1.4.12's text spacing, reflow at 320 px, computed names after a script changes
them, or content that updates on its own. Phase 6's accessibility review measured those by hand,
with WebDriver's computed labels, Firefox's `browser.display.document_color_use` and Chrome's CDP
forced-colors emulation (Harness proof, Phase 6). Its gate (`p6-final-a11y-1` and
`p6-final-a11y-widths-1`, 40 and 60 cells) passes as Phase 4's did, with the same 16 and 24
moderate `landmark-unique` cell findings.

## Link check

Phase 4's gate includes a link check of `dist/` (PLAN.md Workflow, 4 femto 3 content). It is part of
`static_checks.py` (`check_links`), runs with every default run of the static checks, and alone with
`--criteria links`:

```sh
uv run tests/static_checks.py --criteria links --dist /path/to/build             # internal links, and the external ones listed
uv run tests/static_checks.py --criteria links --external --dist /path/to/build  # and every external URL fetched once
uv run tests/run.py static --criteria links                                      # the same on dist/
```

- **Internal links.** Every URL a dist page links to or loads (`href`, `src`, `srcset`, `poster`,
  `data`, `action`, `formaction`, `cite`, SVG `href`, the `og:` and `twitter:` URL metas, JSON-LD's
  site URLs), declarative shadow roots included, resolved against the page's URL as Cloudflare Pages
  serves it, plus every `url()` and `@import` in dist CSS and the web app manifest's icons and
  `start_url`. A URL on `https://femto.style` (or relative) must name a page of the URL inventory
  (`/`, `/docs`, `/examples`: each dist page at its extensionless URL) or a file in `dist/`; a page's
  `.html` name or `/docs/` fails, since Pages answers it with a 308; a query is allowed only as
  `/docs?theme=<one of femto's 20 colors>`; a fragment must be an id or an `<a name>` in the target
  page's own tree, outside every `<template>` (a fragment never reaches into a shadow root; `#` and
  `#top` are the top of the page). A fragment alone (`href="#content"`) is looked up in the page
  that holds it, with no path resolved, since the 404 page is served at every missing URL. An SVG
  `<use href="#id">` names an element of its own tree, shadow roots included. Code samples are text
  and are not read.
- **External links** are listed. With `--external` each distinct URL is fetched once (HEAD, then GET
  when HEAD fails, redirects followed, a browser's User-Agent: Figma and npm answer 403 to a
  script's), and one that answers 400 or more, or not at all, fails the check, except two kinds,
  which are listed: femto's npm and jsDelivr URLs before its first publish (PLAN.md Risks), and the
  "Edit this page on GitHub" links to files this branch adds, which answer once the owner merges and
  pushes `main` (Decision 15).
- **Controls.** Every run first copies `dist/` and plants six broken links, one per copy (a missing
  asset, a missing page, a missing fragment on another page, a missing fragment on the page itself,
  a page's `.html` name, an unknown `?theme=`); each copy must fail with exactly its planted link and
  nothing else new, or the check fails (`LINK_CONTROLS`).

## Lint

`npm run lint` is criterion 11's lint (`eslint.config.js`): `@eslint/css`'s `use-baseline` at
`widely` on `site/**/*.css`, and on `site/**/*.js` eslint-plugin-baseline-js's `use-baseline` at
`widely` (`COMPAT_LINT`, owner decision 5) with a never-list of `no-restricted-syntax` and
`no-restricted-globals` rules for what Decision 12 names. `site/vendor/` is ignored (criterion 12).
`static_checks.py`'s criterion 11 proves what the lint reads, in a temporary copy of the tree, never
the repository:
- a feature that is Baseline newly but not widely available, planted in each site CSS and JS file
  in turn, must fail the lint at `widely` (`CSS_PROBES`, `JS_PROBES`, calibrated against the
  installed tools first);
- each of the 12 `NEVER_PROBES`, planted alone, must draw a `no-restricted-*` report: the
  `navigation` global; `scrollend` as a string, as a template literal and as `onscrollend`;
  `content-visibility`; `blocking="render"` as an attribute and as a member;
  `scrollIntoView({container})` inline and through a variable; `focus({preventScroll})` with a name
  key and with a string key; and FontFaceSet's `loadingdone`;
- the two inline head scripts, written to files, lint clean as site JS (`sourceType` script) and
  report the first never-list probe planted in each.

**What the lint cannot see** (css-3, css-4; Phase 6). eslint-plugin-baseline-js 0.7.7 checks syntax
and the globals and static members of JavaScript's built-ins and the Web APIs (`Promise.try`,
`navigator.clipboard`). It does not see instance members (`Set.prototype.union`,
`element.moveBefore()`), event names passed as strings (`"loadingdone"`) or members of an options
object (`focus()`'s `preventScroll`). Its README leaves instance members to a type-aware preset that
needs TypeScript type information, from tools beyond PLAN.md's Repo changes. So `JS_PROBES` are
static members, the only kind the plugin reports, and that is how css-1's `preventScroll` and
css-2's `loadingdone` passed the lint until Phase 6. The never-list catches the Decision 12 cases by
spelling, not by meaning:
- an event name anywhere as a string or a template literal, and as an `on<event>` property;
- an option (`container`, `preventScroll`) as a key of any object, a name or a string, so an options
  object built ahead of the call is caught too, and also an unrelated object with such a key
  (`site/assets/js` has none);
- `blocking` as a string and as a member.

An event name built from parts (`"scroll" + "end"`), or an option key computed at run time, still
passes. The lint never reads the site's other CSS: the `<style>` in
`site/docs/sections/css-variables.html` and `style=""` in `site/docs/sections/nav.html`, which only
the forbidden-syntax scans read, and the CSS that site JS writes (six places, listed by criterion
11's note). Phase 6's review checked all of these, and the site's JS for instance members, event
names and options, by hand against @mdn/browser-compat-data 8.1.8 and web-features 3.45.0
(2026-11-06), and criterion 11's note says so on every run.

## Divergence registry: `tests/divergences/`

Each `<name>.json` is a JSON array of entries; `schema.json` is the JSON Schema. `uv run
tests/run.py registry` validates them, and every run validates them again.

| Field | Meaning |
|---|---|
| `id` | unique across all files, `^[a-z0-9][a-z0-9._-]*$` |
| `kind` | `structure`, `attribute`, `text`, `style`, `head`, `status`, `skipped-check`; the styles mode's `token`, `token-raw`, `surface-missing`, `surface-added` (Tokens and states) |
| `selector` | element kinds: a CSS selector the element must match, evaluated on side B, or on side A when side B has no element at that path (`*` for any). Element kinds need `selector` or `path`; `head` entries take no selector. |
| `path` | element kinds: the record's tree path; `head`: the head key (`title`, `meta[name=description]`, `link[rel=canonical]`, `script[type=application/ld+json]`), required; `status`: the route. Exact, `*` or `/regex/` |
| `pseudo` | `style` only: `""` for the element itself, `::before`, `::after`, `::marker`, `::placeholder`, `::file-selector-button`, `::backdrop`, `*` or `/regex/`; omitted means any |
| `property` | `style`: the longhand; `attribute`: the attribute name; `head`: `text` (the title), the attribute (`content`, `href`), or a JSON leaf (`$.version`); `token`: the probe property the token resolves through. Required for all four. Exact, `*` or `/regex/` |
| `token` | the token kinds (required): the token's name (`--femto-primary`) or a `/regex/` of names, never `*`. A `token` or `token-raw` entry may also take a `selector` (the anchor must match it, on side B, else side A) and a `path` (the anchor's tree path); a surface entry takes neither, nor `a` or `b`. `token-raw` and surface entries take no `property` |
| `a`, `b` | side A's (the oracle's) and side B's values: exact (style values with the color tolerance), `*`, `/regex/`, or `null` for absent (an attribute or element missing on that side) |
| `check` | `skipped-check` (required): `media:dark`, `media:light`, `pseudo:::backdrop`, ...; exact or `/regex/` |
| `where` | optional filters, all of which must match the cell: `browsers`, `routes` (exact, or `/^regex/`), `schemes` (legs), `widths` (integers or `{"min", "max"}`), `comparisons` (`pages`, `styles`, `one-page`; `self` for skipped-check entries only), and `states` (element kinds only: `base`, the document as loaded, `hover`, `focus`, `focus-visible`, `active`; matched per record in the page, a record found under no state being `base`) |
| `category` | PLAN.md's Divergence categories: `dropped-route`, `femto-divergence`, `merge-layout`, `id-rename`, `oracle-bug`, `highlight`, `asset-path`, `browser-limit` (skipped checks must use `browser-limit`), `owner-change` (a change the owner asked for: Decision 16) |
| `reason` | non-empty: why the difference is intended (criterion 3) |
| `notes` | optional |

Patterns: a plain string matches exactly, `*` anything, `/body/flags` is a regular expression
(flags `i`, `m`, `s`, `u`): JavaScript's `RegExp` in the fields `differ.js` matches (an element or
head entry's `path`, `pseudo`, `property`, `a` and `b`), Python's `re` in routes, `status` records
and skipped checks. Routes start with a slash themselves, so in route patterns
(`where.routes`, a `status` entry's `path`) a regular expression must start with `^`
(`/^\/docs\/forms/`); `/docs/forms/input` is always the route. A `where.routes` item is an exact
route (it starts with `/`) or such a regular expression, never `*` or another word (a registry
error), and a `status` entry's `path` is a route, `*` or such a regular expression. A difference is registered when at least one entry matches;
every entry that matches counts a hit. The summary lists entries with no hit in the run as unused
(informational; a fast run leaves most entries unused). Unregistered differences, and unregistered
skipped checks, fail the run.

**Comparisons.** A pages comparison applies the entries without `where.comparisons` or naming
`pages`. A styles comparison (Phase 2) applies only the entries whose `where.comparisons` names
`styles`, and skipped checks: the Phase 1 entries explain the oracle against the static site, and
none of them may hide a difference between two builds of the static site. Token, token-raw and
surface entries apply only there, so they must name it (a registry error otherwise), and they take
no `where.states` (tokens are read in the document as loaded). Every Phase 2 entry, the seeded
`femto-divergence` ones included, therefore carries `"where": {"comparisons": ["styles"]}`. The
summary of a styles run says so. A one-page comparison (Phase 3: the sections mode, and a pages run
whose side A is `static-femto`) likewise applies only the entries whose `where.comparisons` names
`one-page`, and skipped checks: neither Phase 1's entries (the oracle against the static site) nor
Phase 2's (the frozen CSS against femto) explain the Phase 2 site against the one page. Every Phase 3
entry carries `"where": {"comparisons": ["one-page"]}`, and a section cell's `where.routes` is side
A's route (`/docs/forms/input`, `/docs/version-picker/jade`), whose records carry side B's tree paths
(and `path_a`). The union and kind-budget limits count each comparison's entries apart: those that
apply in pages runs, in styles runs and in one-page runs.

Three rules keep the registry from hiding what it must not:

- **Self comparisons apply skipped-check entries only.** Criterion 1 asks for zero differences
  between the oracle and itself, so no element, head or status entry registers anything in a `self`
  run, whatever its `where`; an entry with `where.comparisons` naming `self` is a registry error
  unless it is a skipped check.
- **Breadth: every entry is specific** (`harness/registry.py`, `_judge`). It is judged on what it
  would actually match, not on how its patterns are written: its selector, path and route scope are
  evaluated on the **reference documents**, the oracle's captured DOMs (`dom.html`, `dom-dark.html`
  and `dom-375.html` of all 64 routes, read as serialized DOMs), the fixture site unchanged and
  under every control, and the pages of `dist/` and of every `dist:<path>` folder a run serves
  (`<route>.html`, `<route>/index.html`, `404.html` for the 404 route). Page sources are read with
  the HTML standard's tree construction (implied `html`, `head`, `body` and `tbody`, `p`, `li`,
  `dd`, `dt`, `option` and table cells closed by what follows, end tags that never close past a
  special element, `</template>` closing all that is open in its template, SVG and MathML content
  with their integration points and ended by an HTML tag; `_StaticBuilder`), so a page that omits
  optional tags gives the tree a browser builds. A stdlib CSS selector engine evaluates the
  selectors exactly, with Kleene logic for pseudo-classes a static document cannot settle (`:hover`,
  `:checked`, ...: they count as matches, so reach is never under-stated), and each document again
  with `data-theme` light and dark when the selector tests `data-theme`. Path patterns are
  evaluated with JavaScript's `RegExp` (one `node` call over every tree path and head key), the
  engine `differ.js` applies them with, since Python's `re` reads some patterns otherwise (`\Z` and
  `\A` are anchors in Python and the letters Z and A in JavaScript; `{,2}` is a quantifier in Python
  3.13 and text in JavaScript); every regex an element or head entry carries (`path`, `pseudo`,
  `property`, `a`, `b`) must also compile in JavaScript. Every element or head entry
  - reaches at most 25% of the compared elements (head: head keys) of any one document, past 4 of
    them, route-scoped or not: a route scope narrows where an entry applies, not how much of a page
    it may cover, so a catch-all that names one route is one too. The one allowance is a **pinned**
    entry (`_pinned`): a `femto-divergence` style entry for styles runs only that names one exact
    route in `where.routes`, one exact `property`, and exact `a` and `b` values (no `*`, no regex,
    no `null`). It registers one value change and nothing else, so it may reach up to 40% of a
    document when every element it reaches there has one shape, the same tree path but for its
    sibling indices (the repeats of one example). femto's button `max-width: 100%` reaches the 380
    color swatch buttons of `/docs/colors`, 29.3% of its 1,297 compared elements, all
    `html > body > main > div > section > article > main > button`; the swatches take one pinned
    entry for each of `max-width` and `max-inline-size` (`none` to `100%`), beside the entry for
    every other button;
  - together with every other entry of its kind (route-scoped ones included) reaches at most 50% of
    any one document, past 4 elements;
  - unless it names at most 3 routes (`where.routes`: an exact route counts once, a regex counts the
    known routes it matches), also reaches at most 5% of the compared elements (head: 10% of the head
    keys) of a complete site over the routes in its scope, in each document variant, and those
    entries together at most 25%;
  - **kind budget**: all the entries of a kind together, route-scoped ones included, reach at most
    25% of each complete site's compared elements (past it, the route-scoped ones that reach that
    site are rejected), so a catch-all split by route, or by selector, cannot cover the site;
  - names at most 3 routes without a reference document (a v1 page, say), whose reach cannot be
    judged, and so does the whole registry, so a scope of uncaptured routes split three to an entry
    is rejected.

  **Complete sites** are the oracle's 64 routes, fixed, and a `dist` build (or `dist:<path>`
  folder) once it holds a page for every kept route: until then its pages count document by
  document only, so whether an entry is valid never depends on how much of `dist/` is built. A
  status entry names at most 3 routes; a skipped-check entry names one or two browsers and at most 2
  of the 8 known checks. A skipped check for a replayed state is the exact check string,
  `state:<state>:<tag>[type=<type>]`, and names one browser; a pattern that matches any state check
  (of every state, HTML tag and input type, `registry.py` `STATE_CHECKS`) is a registry error, and a
  state check is never matched by a pattern, so no entry switches the state assertion off. A selector with a pseudo-element, a namespace prefix other than `*|`, or
  text the engine cannot parse is an error. An entry that breaks a rule is a registry error and is
  never applied, so what it would have hidden is reported as unregistered. `Registry.breadth` keeps
  each entry's figures.
- **Token entries** are judged in the page: in every cell, a token entry whose `token` pattern
  names more than 50% of either side's token names (past 4) is a harness error (`breadth:`) and is
  not applied there, and so are the `token` entries, and the `token-raw` entries, of a cell that
  together name more than 60% of them (all of that kind are then taken out), so a catch-all split by
  name is caught (`p2-fix-harness-r1-probe-evade-2`: four `token-raw` entries splitting the names
  `a-b`, `c`, `d-l`, `m-z`, which had registered every raw text record of `/docs/button`). One
  explained difference can span many names: femto's `light-dark()` raw text, two entries, names 82
  of the 404 page's 163 names (50.3%; a union limit of 50% took both out there,
  `p2-fix-harness-r1-widths`), hence 60%. An entry need not carry a value pattern; `a` and `b` narrow what it
  registers within its names. Surface entries share the same limits, with one allowance: a surface
  entry whose `token` pattern is a **closed set** (`registry.py` `_closed_set`: an exact name, or a
  regex without flags, anchored with `^` and `$`, of literal characters, groups of alternatives and
  character classes of letters and digits only, no quantifier, dot or negated class, that expands
  to at most 1,000 names) may name up to 70% of either side's names, since a reader sees every name
  it can match. The surface entries of a kind together name at most 60% of them, counting those
  whose pattern is open (a prefix such as `/^--femto-[a-m]/`, which names whatever a stylesheet
  adds), and at most 70% with the closed sets included, so neither a split by name nor a list of
  every name registers a whole cell (`p2-fix-harness-r2-surface-split`: three `surface-missing`
  entries `/^--femto-[a-e]/`, `[f-o]` and `[p-z]`, all of `/docs/button`'s 171 names, are taken out
  of the cell, and its 5 `--femto-scale-color-*` records stay unregistered). femto's color bundle
  adds its 380 shades to the 190 names of `/docs/version-picker` and its color routes (66.7% of the
  570 names there; on `/docs/colors` both sides declare them), one closed-set entry: 20 hues and the
  shades `(50|[1-9]50|[1-9]00)`. The union and kind-budget limits below count the entries of each
  comparison apart: those that apply in pages runs together, and those that name `styles` together.
- **In every cell, on the live documents** (`differ.js`, `breadthGuard` and `coverage`), the same
  per-document limits apply again: an entry whose selector and path reach more than 25% of either
  side's compared elements (head: head keys), past 4, and the entries of a kind that together reach
  more than 50%, are a harness error (`breadth:`) and are not applied in that cell, so their
  records are reported as unregistered (a pinned entry: past 40%, or past 25% over more than one
  shape of tree path). This sees what the reference documents cannot: markup a
  script adds (a class set on load reaches 0% of a page's source and 100% of the live page), and
  JavaScript's own reading of every pattern. Then the registered records of the cell together may
  cover at most 25% of either document, past 4 elements: a registered structure record covers its
  whole subtree, any other element record the element on each side, a head record its key
  (`coverage:`, a harness error naming the entries by what they cover). Entries explain
  differences; they never stand in for most of a page, so a page one side does not have fails
  however narrow the entries are. Two kinds of entry cover nothing (`differ.js` `consequences`),
  as an inherited record covers nothing: a pinned entry, and a **layout consequence**, a
  `femto-divergence` style entry for styles runs only that names one exact route and only longhands
  whose computed value is what layout makes of the box (`GEOMETRY`: `width`, `height`,
  `inline-size`, `block-size`, the four insets and their logical forms, `transform-origin`,
  `perspective-origin`, `grid-template-rows` and `grid-template-columns`, judged on the cell's
  property list). Such an entry registers the sizes and positions a registered change elsewhere
  moves on one page; the coverage rule counts what the registry explains, not the layout it moves,
  and every breadth limit still applies to it. A record another entry also registers still covers.
  On `/docs/typography` at 600 px the registered records cover 191 of the 740 compared elements
  (25.8%; `p2-review-parity-r2-full-1`, 16 harness errors in Chrome and Firefox), 132 of them
  through `femto-small-font-size-table-widths` and 96 through `femto-small-font-size-tooltip-insets`,
  the widths, insets and origins of the font size table that the larger `small` moves. Both are
  layout consequences for that route, and without them the cell passes the coverage rule
  (`p2-fix-harness-r2-site-1`, 375, 600 and 1300 px, light and dark, Chrome and Firefox, with a
  copy of the registry that adds the two pinned swatch entries and merges the two shade entries
  into one closed set: no harness error on that route, nor on `/docs/colors` and the picker routes,
  and the swatch and shade records all registered).
  **A section layout consequence** (Phase 3; `registry.py` `_section_geometry`) is the one entry the
  breadth limits do not judge by its reach. Phase 3's contract 5 keeps the content column's width,
  except at 1300 px (and 1600 px as built; Sections) on the four routes that had no table of
  contents, where every box of the section is narrower: geometry records on every element of
  the section, which no entry under the 25% limit can register. A `merge-layout` style entry is one when its `where` names exactly `comparisons`
  `["one-page"]`, one exact route, and one or two exact widths (integers, no range; `browsers` and
  `schemes` may narrow it further, nothing else) and its `property` is an exact `GEOMETRY` longhand or
  an anchored list of them (a closed set, `_closed_set`, of `width`, `height`, `inline-size`,
  `block-size`, the eight insets, `transform-origin`, `perspective-origin`, `grid-template-rows`,
  `grid-template-columns`); its selector, path, pseudo-element and values are free. It applies only in
  section cells of its route and widths (not in a whole-page cell, not in any other comparison); it is
  exempt from the per-document limit, statically and in every cell, and from the union and budget
  limits, where its reach would take every other style entry of the cell out; its records cover
  nothing; and the registry's section layout consequences together name at most 4 routes
  (`GEOMETRY_ROUTES_MAX`, the four of contract 5; past it all of them are registry errors). It
  registers sizes and positions and nothing else: a color, text, attribute or structure change in
  the same cell stays unregistered, and so does the same size change at another width or route
  (controls `sections-geometry` and `sections-geometry-evasion`). The `registry-evasion`, `registry-route-scope`,
  `registry-runtime`, `registry-missing-page` and `registry-root-path` controls prove these rules,
  and `registry-styles` the token and state fields and the comparisons rule, `registry-token-split`
  and `registry-surface-split` the token and surface union limits, `registry-surface-closed` the
  closed-set allowance, `registry-pinned` the pinned entry, `registry-consequence` and
  `registry-consequence-unscoped` the layout consequence, `sections-geometry` and
`sections-geometry-evasion` the section layout consequence, and `state-coverage` the state rule below
  (Selftest). Under a replayed state
  the guard's choices for the cell stay in force, and the coverage rule applies to the state's
  subtree, counting only the registered records the state adds: one equal to a record of the
  document diff (element, pseudo-element, property and values) was judged there.
- **Inherited records** (`differ.js`, `inheritedFrom`): a style record no entry matches, of an
  inherited longhand (CSS's "Inherited: yes", `INHERITED`), on an element whose parent pair holds a
  registered record of the same longhand with the same value on each side, or on an inheriting
  pseudo-element (`::before`, `::after`, `::marker`, `::placeholder`, `::file-selector-button`) of
  an element that holds one, is that difference inherited. It is folded into the parent's record:
  counted under the parent's entries as `inherited` (`result.json` `totals.inherited`,
  `inherited_by_entry`; the summary's `(+N inherited by descendants)`), apart from `registered`, and
  it covers nothing; a folded record passes the fold on to its own descendants. So an entry names
  the element femto's rule styles and not every descendant that inherits the value: on
  `/docs/button` at 1600 px the `overflow-wrap` that
  `femto-pre-code-scroll-end-padding-overflow-wrap` registers on `pre > code` is inherited by the
  highlighted spans, 1,463 records in the document and under its states
  (`p2-fix-harness-r1-button-1600`), more than the breadth and coverage limits let any entry register. A descendant with another value, on either side, is a
  record of its own (control `inherited`). The harness cannot see whether the descendant has a rule
  of its own for the longhand; one that gives it its parent's values on both sides is the same
  difference.

The summary shows, for each entry, how many cells it registered records in and the most it
registered in one cell, and flags an entry with 100 or more in one cell as `BROAD`: check that it
hides nothing unrelated. A registered `structure` record covers only the element it names (its
subtree has no counterpart, or, for a tag change, is still compared).

Seed: `rig.json` holds `safari-no-media-dark` (`browser-limit`), as femto's does. Phase 1 adds
`dropped-route`, `highlight` and `oracle-bug` entries (among them PLAN's `og:url` example: the
oracle's `meta[property=og:url]` is `https://v2.picocss.com/` on 63 of its 64 routes, a `head`
record once the static site fixes it); Phase 2 seeds `femto-divergence` from femto's
`tests/divergences/` at the vendored commit (each naming `where.comparisons` `styles`); Phase 3 adds
`merge-layout`, `id-rename` and `asset-path` entries in `p3-*.json`, each naming `where.comparisons`
`one-page`.
`owner.json` holds the `owner-change` entries for PLAN Decision 16, the theme toggle's emoji icon
(2026-11-01): the SVG-to-span tag change and the SVG's two parts.

## Output

`tests/results/<run-id>/` (run id `YYYYMMDD-HHMMSS-<mode>-<pid>` unless `--run-id`):

- `result.json`: `run_id`, `mode`, `comparison` (`self`, `pages`, `styles` or `one-page`), `full`, `argv`, `git`,
  `sides` (each side's target, base URL of the last chunk, readiness hook and root; a `dist` side's
  folder and wrangler; a `build_tag` side's `build.json`), `styles` (the styles mode: token prefix,
  probe properties, anchors, and the states file with its target and target-state counts),
  `server_chunks`
  (cells per server life and chunk sizes), `masks`, `planned` (cells per
  browser, leg and width), `status` (`PASS`/`FAIL`), `duration_s`, `totals` (cells per browser,
  cells run and skipped, elements compared, differences by kind, unregistered, registered, harness
  errors, unregistered skipped checks, pixel-diff cells, readiness reloads, alignment fallbacks,
  cross-origin loads, `head_repeat_documents`: per side, the documents whose head held an exact copy
  of a data block; `styles`: state replays per side, cells with states, token documents, the most
  names, anchors and seconds), `cross_origin_loads` (cell, side, URL: the failing ones), `site_origin_loads`
  (side, URL, cells: loads from `https://femto.style` by a `same_origin` side, never failing),
  `cross_origin_reported` (side, URL, routes: sides not held to same-origin loading), `caps`,
  `masked_elements`, `rig` (one record per session: versions, launch time, OS scheme,
  pseudo-element support), `harness_errors`, `ready_retries`, `skipped_checks` (check, browser,
  cells, matching entries), `registered_by_entry`, `registered_spread` (per entry: cells, the most
  records in one cell and that cell, `broad`), `registered_samples` (up to 3 records per entry),
  `unused_entries`, `pixels`, `groups` (per browser and route), and `cells` (every cell with its
  unregistered records, registered counts, errors, timings, per side the final path and status,
  request count, subresource errors, element, pseudo-element and head-entry counts, `head_repeats`,
  Resource Timing entries, cross-origin URLs, `frames_read` and `frames_unreadable`, `csp_reports`,
  `csp_cross_origin` and `csp_other` (the proxy's CSP reports), masked elements
  and freeze counts, and the pixel result; in the styles mode per side `tokens` (names, anchors,
  probe groups, milliseconds), `states_a` and `states_b` (state replays), `state_targets` (each
  target's tree paths), `scroll_behavior_a` and `scroll_behavior_b` (`html`'s `scroll-behavior`
  after the replay) and the `a_states` and `b_states` timings; in the sections mode `section`,
  `section_theme`, `url_b`, `path_b` and `root_b`).
- `summary.txt`: status line, both sides, the styles mode's tokens and state replays, unregistered
  differences first (5 records per cell, 40 cells; a record found under a state starts with it, as
  `[hover] style ...`), harness errors, cross-origin loads (failing, then loads from the deployed site, then
  reported), readiness reloads, skipped checks, registered counts per entry, unused
  entries, masks, matrix caps, pixel diffs, then one line per browser and route.
- `log.txt`: the sides, the sessions, one line per cell as it finishes.
- `shots/`: for each cell with pixels off by more than 8/255, both screenshots
  (`<browser>__<route>__<leg>__<width>-a.png`, `-b.png`) and a mask.
- `server-<target>-<port>.log`: the output of each command target the run started,
  `wrangler-debug-<port>.log`, the `dist` target's wrangler debug log (`targets.json` `env` sets
  `WRANGLER_LOG_PATH`; the oracle's servers log to `tests/oracle/logs/`), and
  `wrangler-state-<port>/`, its `--persist-to` folder.

Exit status: 0 PASS; 1 unregistered differences, harness errors, unregistered skipped checks,
registry errors or cross-origin loads on a `same_origin` side; 2 a setup error before any browser started (an unknown target or control, a missing
`dist/` or `dist:<path>` folder, a missing or mispinned wrangler, a missing routes file, a side whose server would not start, the user's Safari running).

## The oracle

`harness/oracle.py` builds, serves and captures the Remix site at tag `remix-final` (PLAN.md
Decision 6, Risks: the oracle must build).

- **Build.** A detached worktree of the tag at `tests/oracle/worktree`, then `npx yarn@1.22.22
  install --frozen-lockfile` and `npm run build` under the Node on `PATH` (24.22.0). If that fails it
  tries Node 20, then 18.19.0, with node and yarn in one npx environment: `npx -p node@<v> -p
  yarn@1.22.22 -- yarn install --frozen-lockfile` and `... -- yarn run build` (the first form,
  `npx -p node@<v> -- npx yarn@1.22.22`, finds no `yarn` there). Both fallbacks were proved on
  2026-10-30 in scratch clones of the tag through `install_and_build()`: Node 20.20.2 (install
  24.8 s, build 7.3 s) and Node 18.19.0 (21.4 s, 6.6 s), each giving the same Remix manifest
  (`manifest-32F0910B.js`) as the Node 24 build. `FEMTO_ORACLE_NODE=<v>` (or `path`) tries only
  that runtime. `tests/oracle/build.json` records the runtime, versions, timings and
  `outputs_digest`.
- **Staleness.** A build is redone when the tag moved; the worktree's HEAD, tracked files or
  untracked files that are not ignored differ from the tag; an output is missing; or the sha256 of
  every file under `public/`, `functions/` and `app/styles/css/`, plus each installed package's name
  and version and yarn's integrity file, differs from `outputs_digest`. A rebuild starts from `git
  clean -ffdx`.
- **Locks.** `tests/oracle/build.lock`: a build holds it exclusively, and every running
  `oracle.serve()` holds it shared for its whole life, so no process runs `git checkout --force` or
  `git clean` under a live server. A process that would rebuild while it is serving itself stops
  with an error instead of waiting on its own lock.
- **Capture** (`uv run tests/run.py oracle`, `tests/oracle/capture/`): per route `server.html`,
  `meta.json`, `dom.html` (hydrated, 1300×900, light), `dom-2.html` (a fresh session),
  `dom-dark.html` (the same session under `prefers-color-scheme: dark`), `dom-375.html` (375×900,
  light) and full-page shots at 1300 and 375; `_css/` (every stylesheet once), `_fonts/` (the font
  files a cross-origin stylesheet references), `_run.json`, `_determinism.json` and
  `_variants.json`. The 20 static Pico v1 pages are listed in `oracle-routes.json` (kind `v1-page`,
  not kept), checked for status 200 and not captured; they are old paths that criterion 6 expects to
  answer 404.
- **Markup that depends on the color scheme or the viewport** (`_variants.json`, 2026-10-30). The
  hydrated DOM is not one document: under a dark scheme the `div.maintenance-notice` flips
  `data-theme` from `dark` to `light` and the theme toggle reads "Turn off dark mode" with another
  icon (62 routes), both `section.comparison div.code` on `/` flip `data-theme` to `dark`, and the
  `/docs/table` example's `thead` flips `data-theme` and its label; at 375 px the docs side nav's
  `--max-height` is 813px instead of 742.75px (59 docs routes; `innerHeight` minus the nav's top),
  and the typing demo's code gains line breaks (inside the masked demo). Phase 1's converters must
  rebuild these in JavaScript; the parity runs compare them in every leg and width.
- **Network.** `/docs/css-variables` loads Google Fonts' Pacifico stylesheet and its woff2 files
  cross-origin, so every oracle run of that route needs the network. The capture keeps the
  stylesheet and the five woff2 files (`_fonts/`, 80,604 bytes) for Phase 1 to self-host
  (criterion 15).

## Concurrency and locks

The same locks as femto's harness, in the same place and under the same names, so the two harnesses
(and `oracle.py`'s capture) share them:

- **Slots**: at most `FEMTO_HARNESS_SLOTS` (default 4) browser sessions run at once on the machine,
  across all harness processes. Each worker (one WebDriver session, rig included) holds a slot for
  its lifetime and waits, logging once a minute, when all are taken.
- **Safari**: one Safari session at a time machine-wide (`safari.lock`). Only the harness starts
  Safari, and only through this lock.
- **Driver start**: WebDriver start-up is serialized (`driver-start.lock`), because concurrent
  Selenium Manager runs corrupt `~/.cache/selenium/se-metadata.json`.
- Locks are `flock`s on files in `FEMTO_HARNESS_LOCK_DIR` (default `~/.cache/femto-harness/locks`);
  each holds the pid and label of its owner and is released when the process exits.
- **Tag builds**: `tests/builds/<tag>.lock` (`harness/tagbuild.py`), held exclusively while a run
  builds the tag (the `static-multipage` and `static-femto` targets) and shared by every server of its folder and every
  freshness check, so two runs never build it at once and none rebuilds it under a running server.

Servers do not take slots. Each `self` run starts two oracle servers (wrangler plus workerd, about
0.7 s each once built); ports are free ports from the OS, never 8790. A target may set
`max_documents` in `targets.json` (the oracle: 400; see Rig notes, oracle server): a run with more
cells is split into chunks of at most that many cells per server, and each chunk starts fresh
servers and fresh browser sessions (`--max-documents N` overrides it). The log prints
`chunk k/n` lines, and `result.json` records the chunk sizes under `server_chunks`.

Environment variables: `FEMTO_HARNESS_SLOTS`, `FEMTO_HARNESS_LOCK_DIR`, `FEMTO_CHROME_BINARY`
(default `/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta`),
`FEMTO_FIREFOX_BINARY` (default `/Applications/Firefox.app/Contents/MacOS/firefox`),
`FEMTO_SAFARIDRIVER` (default `/usr/bin/safaridriver`).

## Rig notes

The machine is femto's rig: macOS 27.2, 10 CPUs, 16 GB, Google Chrome Beta, Firefox and Safari.
`uv run tests/run.py rig` repeats the checks and writes `rig.json`. On 2026-10-30 it passed in
Chrome Beta 158.0.8127.2 (chromedriver 158.0.8127.2) and Firefox 160.0 (geckodriver 0.37.1) with
Selenium 4.52.0: all six pseudo-elements readable, `innerWidth`, `matchMedia` and CSS `(width)`
exact at all six widths, every leg's `prefers-color-scheme` and `data-theme` as asked (the stored
theme applied by the probe's own script), hover, active and Tab-to-`:focus-visible` input working.
`rig` has not run in Safari yet: its input checks need an unlocked screen, and the screen was locked
all day. macOS here uses the Auto appearance (`AppleInterfaceStyleSwitchesAutomatically` 1), so the
OS scheme is light by day and dark after sunset; every session records the scheme it read. Safari 27.2 (safaridriver 22625.2.8.11.9) did run the pages comparisons on the locked screen
on 2026-10-30 (Harness proof); each session's rig record shows all six pseudo-elements readable and
the OS scheme light. The notes below are femto's (verified there on 2026-10-27 to 2026-10-29) where
they still apply, plus this harness's own.

**Chrome Beta (headless).**
- Options: `--headless`, window 1800×1000, `--force-device-scale-factor=1`,
  `--force-color-profile=srgb`, `--hide-scrollbars`, no background throttling.
  `Emulation.setFocusEmulationEnabled` keeps `:focus` working.
- `prefers-color-scheme`: CDP `Emulation.setEmulatedMedia` applies inside the same-origin iframe.
  It overrides the iframe's own rule that its `prefers-color-scheme` follows the embedding element's
  used `color-scheme`, which is why the host leaves the iframe at `color-scheme: normal`.
- Chrome Beta updates itself; the version is recorded in each run's rig line, not flagged.
- **Skipped subtrees.** The content of a closed `<details>` is `content-visibility: hidden` in
  Chrome, so its style is updated only when something reads it, and a transition that such a read
  starts stays at its start value (it never ticks there) until `finish()`. A probe confirmed both on
  Chrome Beta 158. On 2026-10-30 (`p0-gate-self-cf-2`, `/docs/overflow-auto` dark 800, the second
  cell of a fresh session) side A read the links in the closed header dropdown and side-nav details
  at their UA colors and the dropdown list at opacity 1: 699 records. So the collector reads every
  element's style (and `::before`, `::after`) once, freezes again, and only then collects; an
  animation that still starts while the styles are read is a harness error for the cell.
- **Idle periods.** Headless Chrome can stop scheduling idle periods: `requestIdleCallback` then
  never fires until a frame is produced. The oracle hydrates from `requestIdleCallback`
  (`app/entry.client.jsx`), so on 2026-10-30 every oracle load after `/docs/loading` in one session
  stalled with `__remixContext` set, every module loaded and no Remix router (reproduced twice, at
  the same cell; a fresh session loading the routes in another order never stalled). During a stall
  the host page's own `requestIdleCallback` did not fire within 3 s, and one
  `requestAnimationFrame` released it and the oracle hydrated at once. So the host page requests a
  frame every frame from each load until the readiness hook returns; the host shares the document's
  thread, so its frames give the document idle periods, and the document itself is not touched.
  With it, the same 108 cells passed with no reload. A side that is still not ready after 30 s is
  loaded once more (`ready_retries` in `result.json`).

**Firefox (headless).**
- `prefers-color-scheme`: pref `layout.css.prefers-color-scheme.content-override` (0 dark, 1 light),
  set at runtime from the chrome context, which needs geckodriver's `--allow-system-access`. The new
  value reaches content asynchronously, so the harness polls `matchMedia` in the host page before
  loading a document. Cells are sorted by media to keep switches rare.
- An iframe's `prefers-color-scheme` follows its embedding element's used `color-scheme`; the host
  keeps `normal`.
- Firefox reports `transform-origin` and `perspective-origin` of inline boxes from their size, where
  Chrome does not: a text change inside an inline element shows there, on that element and on any
  inline ancestor (why the progress code mask leaves out those two longhands on the value token; the
  oracle's `pre > code` is a block, so nothing above the token changes size, and the fixture mirrors
  that).
- **System font fallback.** By default Firefox finds fallback faces asynchronously: for about 2 s
  after startup, text that needs one is laid out with a provisional face. On 2026-10-30
  (`p0-gate-self-cf-2`, the first cells of fresh sessions) the oracle's italic Arabic `cite` on
  `/docs/rtl` measured 83.5 px on side A and 80.45 px on side B, which shows as `transform-origin`
  and `perspective-origin` records. A probe reproduced it on a bare page (83.5 px until 2.1 s, then
  80.45 px); with `gfx.font_rendering.fallback.async` false the first layout is already 80.45 px
  (three runs). The harness sets that pref.

**Safari (visible, serialized).**
- Starts in about 1.4 s. The iframe gives exact widths, so Safari's minimum window width never
  matters.
- No `prefers-color-scheme` emulation. The OS scheme is read with `matchMedia` in the host page at
  session start. The other media leg is a registered skipped check.
- No `prefers-reduced-motion` emulation either. From Phase 6 the OS motion is read the same way and
  logged beside the scheme: the behavior mode runs only the checks of that motion
  (`--expect-os-motion` stops a session that read the other one), and the comparison modes refuse
  `reduce` (Known limits). The harness reads the setting only through Safari's `matchMedia` and
  never changes it; the shell cannot read it reliably (`defaults read com.apple.universalaccess
  reduceMotion` found no key on this Mac).
- While your own Safari is open, a new WebDriver session never starts (Safari 27.2): the harness
  refuses to start one and exits 2. Quit Safari (Cmd-Q) before every Safari run. Before each session
  the harness terminates leftover `Safari ... --automation` processes (only safaridriver starts
  Safari with that flag; your own Safari is never touched), and a session refused as "already paired"
  is retried once after terminating them again.
- On a locked screen the page reports `visibilityState: hidden`, `requestAnimationFrame` never runs
  and pointer and keyboard input never arrive, while `getComputedStyle`, `getAnimations().finish()`
  and element screenshots work. The pages mode needs no input and its frame waits fall back to
  100 ms timers, so Safari comparisons run on a locked screen; `rig`'s input checks and the behavior
  mode need it unlocked, the automation window in front and nobody using the machine (Screen
  Sharing included). The screen locks once the display sleeps; `caffeinate -d -i` holds it awake
  for the duration of a run. On 2026-10-30 the Safari light pass ran on a locked screen
  (`lsappinfo front` reported `loginwindow`) at about 4 to 7 s a cell (see Harness proof).
- **Closed `<details>`.** Safari 27.2 computes the style of a closed `<details>`' content anew for
  every `getPropertyValue()` call (about 0.07 ms a call, measured on `/docs/css-variables` on a
  locked screen; under 0.001 ms for rendered elements). That page keeps its code samples in closed
  details (4,358 highlighted spans), so collecting one side reads about 1.8 million values there and
  takes about two minutes, where Chrome and Firefox take under a second. Safari sessions therefore
  use a 600 s script timeout and a 660 s WebDriver client timeout (120 s and 180 s elsewhere). The
  first light pass (`p0-gate-self-safari-light-1`) still had the old 120 s and 150 s: the collect
  call on `/docs/css-variables` timed out, Safari kept running the script, and every later command
  timed out too.
- **Long scripts on a locked screen.** With the longer timeouts (`p0-gate-self-safari-light-2`) the
  `/docs/css-variables` collect still never finished on the locked screen: the WebContent process
  sat at 0% CPU for over ten minutes in the middle of the script, its threads frozen (one mid
  garbage collection), until the 660 s client timeout restarted the session. That is consistent
  with macOS suspending a hidden page's process during a long script; a probe in a fresh session
  read the same page's styles at full CPU (1,614 elements in 30 s). So `/docs/css-variables` runs in
  Safari only on an unlocked screen with the automation window in front; the other routes collect
  in seconds and ran locked.
- A command that times out (no reply within the client timeout) now ends the session like a
  WebDriver error: the cell is a harness error, the session is quit with a 10 s limit, its driver
  process is killed, and for Safari the automation instance is terminated (the run holds the Safari
  lock); the next cell starts a new session. Runs that unwind early quit every session the same way.
- safaridriver leaves its `--automation` Safari running even after a clean quit (seen twice on
  2026-10-30), so every Safari session's quit terminates it, still under the Safari lock
  (`p0-gate-safari-quit-check` left no Safari, safaridriver or oracle process behind).
- **Speculative loading.** At the start of a load, Safari requests the subresources the last load
  of the same URL used, `Cache-Control: no-store` notwithstanding, and serves the responses to the
  next document that asks for them. Phase 0's Safari runs couldn't show it, since both sides there
  served the same files. In the first styles runs (2026-11-03) it caused over 99% of the
  records: 23 cells in Light and 14 in Dark rendered without stylesheets that had answered 404 from
  the other side's server. So every Safari document load gets a URL of its own (The proxy,
  `harness-load`), and the stylesheet check reloads a side whose own stylesheet didn't load.

**Oracle server (wrangler 4.0.0, the tag's locked toolchain).**
- wrangler's `InspectorProxyWorker` enables the worker's DevTools `Network` domain and keeps every
  event in `runtimeMessageBuffer` until a DevTools client connects, which never happens here. On
  2026-10-30 (run `p0-gate-self-cf`) both oracle servers died together after about 1,240 page loads
  (about 43,000 requests, 377 s): workerd reached the V8 heap limit at about 1.4 GB ("Reached heap
  limit ... JavaScript heap out of memory"), and every later cell failed with "Connection refused".
  So the oracle target sets `max_documents: 400`, and a run restarts its servers (and browser
  sessions) in chunks; the full Chrome and Firefox matrix runs in 4 chunks of 372 cells.
- The same proxy echoes every event into wrangler's own debug log, about 300 MB per 1,200 page loads.
  `oracle.serve()` points `WRANGLER_LOG_PATH` at `tests/oracle/logs/wrangler-debug-<port>.log`
  instead of `~/Library/Preferences/.wrangler/logs/`, and deletes it when the server ran until it
  was stopped; it is kept when wrangler exited on its own. The `dist` target writes its log into
  the run's folder and static check 6 into its temporary folder, so no harness run writes to
  `~/Library/Preferences/.wrangler/logs/` any more.

**The site's server (`wrangler pages dev` 4.158.0 from `node_modules`, on macOS).** Two answers
differ from what criterion 6 says of "any other path", and both come from looking files up on this
Mac's disk; `static_checks.py` probes neither:
- A path below a file answers 502, with only `[wrangler] Could not serve static asset: Error:
  ENOTDIR` as its body: `/_headers` (wrangler looks up `dist/_headers/index.html`; Phase 5, Hosting),
  `/robots.txt/x`, `/favicon.svg/x`, `/docs.html/`, `/docs.html/x`, `/examples.html/`,
  `/index.html/`, `/404.html/`, `/favicon.svg/` and `/sitemap.xml/`, and also `/docs%00`.
- A page path in other letter case answers 200 with the page, since APFS is case-insensitive and
  `dist/DOCS.html` resolves: `/DOCS`, `/Docs`, `/docs.HTML` and `/EXAMPLES` (`/Docs.html` answers
  308 to `/Docs`). The GitHub check serves `dist/` on Linux, where these should be 404; that was not
  run (urls-6, Phase 6). Whether Cloudflare Pages itself matches paths in a case-sensitive way was
  not checked either (Harness proof, Phase 6, Not verified here). The `?theme=` head script and,
  from Phase 6, picker.js apply a theme only on the exact path `/docs` (urls-5), so such a spelling
  shows azure.

**The styles mode (Chrome Beta 158, Firefox 160, 2026-11-02).**
- Both browsers make a scroller with no focusable content a Tab stop: at 375 px a code block's `pre`
  overflows, and Tab from the control before a dropdown's summary on `/docs/dropdown` landed on the
  `pre` between them, not on the summary. The focus-visible replay's last method (`focus()`,
  Shift+Tab, Tab) follows the browser's own order and reaches it.
- Tab enters a radio group on its checked radio only, so an unchecked radio never matches
  `:focus-visible` from the keyboard; `states.json` hovers and presses it instead.
- A token that is no color, read through a color probe, resolves in Chrome to the initial text color
  of the probe's scheme, in Firefox to one fixed color (Tokens and states).
- A state replay takes about 60 ms per side in Chrome and 35 ms in Firefox (a pointer move or key
  press, the subtree's collect, and on side B its diff); the tokens 20 to 160 ms per side.

**All three.**
- `getComputedStyle()` returns an empty declaration for an unknown pseudo-element, reads
  `::backdrop` on a closed dialog too, and accepts single-colon `:before`.
- Selenium's default pointer move lasts 250 ms; the harness uses duration 0.
- Headless Chrome and Firefox draw overlay scrollbars that fade after scrolling; screenshots hide
  them with a transient `* { scrollbar-width: none }` (plus `--hide-scrollbars` in Chrome).
- Firefox applies `scrollTo()` asynchronously; before a screenshot the harness scrolls to the top
  until the position holds for two frames.
- Chrome's raster varies by 1/255 in places between identical loads, and femto saw isolated cells
  above 8/255 in self runs; the summary counts pixels off by more than 8/255 separately, and images
  are saved only for those.
- The oracle's pages hold 18 (`/demo`) to 5,176 (`/docs/css-variables`) compared elements; a cell
  takes 0.3 to 2 s in Chrome and Firefox. The fast self run on 2026-10-30
  (`p0-harness-fast-self-2`: 496 cells, 338,408 elements compared, one session per browser) took
  218 s, 0.86 s per Chrome cell and 0.73 s per Firefox cell, so the full matrix's 1,488 Chrome and
  Firefox cells should take about 10 minutes with two sessions per browser, and Safari's 420 cells
  per pass about 6 minutes at Chrome's rate.
- **Resource Timing** (the same-origin check). A probe page on 2026-10-30 (`p0r2-rt-probe`, a
  scratch server on a free port, read as a base-URL side) made six cross-origin loads: a parsed
  stylesheet and a `no-cors` fetch to a refused port, a CORS-mode `fetch()` without
  `Access-Control-Allow-Origin`, a `no-cors` fetch answering 200, an `<img>` answering 404 and a
  script-inserted stylesheet answering 200. Chrome Beta 158 listed all six; Firefox 160 listed the
  four that reached a server and neither refused one; Safari 27.2 (`p0r2-rt-probe-safari`, locked
  screen, dark OS) listed three, leaving out the CORS failure too. All three list a cross-origin
  entry's URL without `Timing-Allow-Origin`.

## Selftest: proving detection

`uv run tests/run.py selftest [--browsers ...] [--cases ...]` runs these controls, each through the
real CLI as `run.py pages --a fixture --b fixture:<control>` (the sections controls as `run.py
sections`, below; the styles controls as `run.py styles`
with `--states tests/fixtures/states.json`: the link `#link` hovered, pressed and reached by Tab,
the form's text input focused, two header links hovered, the progress example's footer hovered,
whose scope, the example's `article`, holds 21 elements, and on `/other.html` the link `#far`
below the fold focused, reached by Tab from `#near` and hovered, in that order). `/other.html` has a
scroll spy like the site's table of contents: it counts the scroll positions the page has been at
in `p#spy`'s `data-positions`, which a smooth scroll raises (control `scroll-smooth`). The fixture site
(`fixtures/site/`) has the oracle's nondeterminism in miniature: a "typing demo" that rewrites its
`.demo > article.component` every 30 ms, and a random progress value (one or two digits) printed in
the highlighted code under it (Prism-style tokens, as on the oracle's `/docs/progress`), replaced
every 500 ms, so the `self` and `masked-only` controls also prove that the masks hide exactly those
areas, and `progress-code-token` that they hide nothing more. Every control runs with a registry
of its own (`--registry`): those that need none get a copy of `divergences/rig.json` only, so the
phase agents' entries in `tests/divergences/`, and whether the breadth rule accepts them as `dist/`
grows, never decide whether detection is proved.

| Control | Expectation |
|---|---|
| `self` | the site against itself (two servers), every leg, widths 375 and 1300, two routes: zero differences, no errors, no cross-origin loads |
| `color-2-of-255` | h1 color `rgb(45, 49, 56)` to `rgb(47, 49, 56)`: style records, all on the h1 and its descendants |
| `color-1-of-255` | `rgb(46, 49, 56)`: tolerated, zero differences |
| `attribute` | the lead paragraph's `title` changes: one `attribute` record per cell and nothing else |
| `added-element` | a fourth list item on side B: exactly one `structure` record per cell (`only-b`, `li`) |
| `removed-element` | the third list item gone on side B: exactly one `structure` record per cell (`only-a`, `li`) |
| `changed-tag` | `<b>` to `<strong>` (both bold, same text): one `structure` record (`tag`) and nothing else |
| `changed-tag-content` | `<b>fixture</b>` to `<strong>fixtures</strong>`: the `tag` record and a `text` record on the same element, nothing else (a tag change still compares what is below it) |
| `inserted-early` | a paragraph inserted as the first child of `<main>`: one `structure` record (`only-b`) naming that paragraph; every other record is a style of `html`, `body` or `main` (their heights), so the h1 and everything after it still pair |
| `inserted-same-tag` | a `<section>` inserted before two sections: one `only-b` record naming the new section, the rest as above |
| `pseudo-content` | the `::before` content changes: style records on `::before` only, `content` among them |
| `width-only` | a rule for 790 to 810px: differences at width 800 only, of the six widths |
| `dark-only` | a rule under `prefers-color-scheme: dark` without `data-theme`: differences in leg `dark` only, of all four legs (in Safari on a light OS: none, with every dark cell a registered skip) |
| `theme-dark-only` | a rule under `html[data-theme=dark]`: differences in leg `theme-dark` only (the stored theme applied by the page) |
| `text` | one word of the lead paragraph: `text` records on `p.lead` and nothing else |
| `whitespace` | one rendered space added between the lead paragraph's link and the period after it, at 375 and 1300: one `text` record per cell on `p.lead` (`"Lead text with ."` against `"Lead text with  ."`) and nothing else. FAILs with the old own-text rule (`p1f1-selftest-ws-oldrule`) |
| `whitespace-collapsed` | source whitespace that renders nothing changes, at 375 and 1300: the list items lose the newline and indentation between them, and the h1's space before `<b>` becomes a newline and indentation (still one rendered space): zero differences |
| `whitespace-nbsp` | no-break spaces, which CSS never collapses, at 375 and 1300: the space after "Lead" becomes `&nbsp; ` and the space before the link two `&nbsp;`: one `text` record per cell on `p.lead` (`"Lead text with ."` against `"Lead\u00a0 text with\u00a0\u00a0."`) and nothing else. FAILs with round 1's rule, which read U+00A0 as collapsible whitespace (`p1f2-selftest-nbsp-oldrule`) |
| `pseudo-elements` | changes on `::marker`, `::placeholder`, `::file-selector-button`, `::backdrop` and `::after`: detected on exactly those five |
| `masked-only` | changes inside the masked areas only (the typing demo's content, the progress value and its code token): zero differences |
| `progress-code-token` | the `max` token of the progress code (outside the value mask) from 100 to 200: a `text` record on that token, and nothing on any other element |
| `head` | the title, the meta description and the canonical link change: three `head` records per cell and nothing else |
| `head-data` | the fixture's JSON-LD block re-indented with its keys reordered and `version` and `url` changed, and a `<base target="_top">` added: three `head` records per cell (`$.url`, `$.version`, `base` `target`) and nothing else |
| `head-data-copy` | a second copy of the JSON-LD block at the end of `<body>`, re-indented with its keys reordered but the same leaves (what React adds on the oracle's `/docs/progress`): zero differences, equal head-entry counts, and `head_repeats` 1 on side B and 0 on side A |
| `head-data-near-copy` | a second JSON-LD block that differs from the first in one leaf (`version` 1.0.1): not a copy, so it is its own entry `script[type=application/ld+json]#2`, nine `head` records per cell (one per leaf, side B only) and nothing else |
| `cross-origin` | a script inserts a stylesheet `<link>` to the fixture's own server under another host name (`localhost` for `127.0.0.1`), its URL built at run time with no URL literal; the stylesheet is the page's own, so nothing renders differently: one cross-origin load per cell (side B), zero differences, and the run fails |
| `cross-origin-frame` | a hidden same-origin `<iframe srcdoc>` whose script inserts the same cross-origin stylesheet: the load is in the frame's own Resource Timing, so it proves the nested read: one cross-origin load per cell (side B), `frames_read` 1, and the iframe's own `only-b` record as the only difference |
| `cross-origin-worker` | a dedicated worker (`fixtures/site/worker.js`) that `fetch()`es the same cross-origin stylesheet, a URL built at run time: no page's Resource Timing lists a worker's loads, so it proves the proxy's CSP reports: one cross-origin load per cell (side B, `via` a CSP report), zero differences, and the run fails |
| `cross-origin-closed-shadow` | a hidden `<iframe srcdoc>` inside a closed shadow root, whose script inserts the same cross-origin stylesheet: no script outside can reach that frame, so only the CSP report shows the load: one cross-origin load per cell (side B), and the shadow host's own `only-b` record as the only difference |
| `status-404` | `/other.html` answers 404 on side B: a `status` record `200` against `404` |
| `stylesheet-404` | `/fixture.css` answers 404 on side B: side B fails the stylesheet check, is loaded once more (`ready_retries`, side B only), and every cell's error is `b ready: stylesheet /fixture.css has no rules (after one reload)` |
| `registry-suppression` | the color and attribute changes together, with a registry holding one entry for the h1: the h1 records are registered, the attribute record stays unregistered |
| `registry-evasion` | one change of each element and head record kind, with a registry of 69 catch-alls written to pass (the reviews' own, two skipped checks over the state checks (`/^state:/` for Chrome and Firefox, which turned every state that did not match into a silent skip, and an exact state check for two browsers), a side-B-only scope, a theme-leg scope, a route hidden in a selector, a catch-all split in twelve, `*` as a route, a scope of uncaptured v1 routes, a style catch-all split by route into 29 entries of three routes, four path patterns JavaScript reads otherwise than Python (`\Z`, `\A`, `{,1}`, for a style, text, attribute and head entry), and the 20 uncaptured v1 routes split three to an entry) beside one narrow entry: every catch-all is a registry error and registers nothing, every record kind stays unregistered, and the narrow entry still registers its two records |
| `registry-runtime` | the `registry-evasion` changes, and an inline script that adds class `js-added` to `<html>` on load, with four entries keyed to `.js-added, .js-added *`: valid statically (the page source has no such class), they reach every element of side B's live document, so the in-page guard reports each (`breadth:`), applies none, and every record kind stays unregistered |
| `registry-missing-page` | `/index.html` answers 404 on side B, with `--root-a body --root-b body` (no head records) and seven entries each under every limit (a status entry for the route; structure entries for `main#content`, `footer.site`, `header > nav` and `pre`; text for `pre`; style for `body`) that register every record: the registered records cover all 48 compared elements of side A's document, so the coverage guard (`coverage:`) fails the run |
| `registry-route-scope` | the color and attribute changes on `/index.html` and `/other.html`, with an entry for the h1 scoped to `/index.html` and a style catch-all scoped to `/other.html`: the catch-all is a registry error (a route scope does not exempt an entry from the per-document limits); the h1 entry registers the h1 records on `/index.html` and nothing on `/other.html`, whose h1 records stay unregistered, and the attribute record stays unregistered |
| `inherited` | `tab-size` 4 on the lead paragraph and the list (no tab in their text, so nothing moves) and 2 on the list's first item, with entries for `.lead` and `ul.list`: each registers its element's record, the link's record is folded under `.lead` and the other two items' and their markers' under `ul.list` (`inherited` 1 and 4), and the first item's own value and its marker's stay unregistered |
| `registry-root-path` | the `registry-evasion` changes with `--root-a body --root-b body` and entries keyed to the old root path form (`path: "/\\{/"`): every record's path starts `html > body:0`, the entries register nothing, and every element kind stays unregistered (no head records under a root) |

The styles controls (the fixture's `fixture.css` declares nine `--femto-*` tokens: on `:root`, in a
nested rule, under `@media` and `@supports`, and through `@property`; only `::selection`, which the
collector does not read, uses `--femto-accent`):

| Control | Expectation |
|---|---|
| `styles-self` | the styles mode, the site against itself, every leg, widths 375 and 1300, two routes: 10 token names in every cell, 7 state replays per side on `/index.html`, zero differences, no errors |
| `token-resolution` | `main` gets `color-scheme: dark`: `--femto-scheme-color`, a `light-dark()` pair, keeps its raw text and resolves to its dark color: `token` records for it through the four color probes, at the anchors in `main` only, and no `token-raw` record (in Chrome the other tokens' `color`, `border-top-color` and `outline-color` probes follow the scheme too; Tokens) |
| `token-raw` | `--femto-raw` written `#f00` instead of `#ff0000`: one `token-raw` record per anchor and nothing else (no probe property reads them differently; `red` would not do, being a font-family and transition-property name) |
| `token-added` | a token only side B declares: one `surface-added` record per cell and nothing else |
| `token-missing` | a token only side A declares: one `surface-missing` record per cell and nothing else |
| `hover-only` | a rule under `#link:hover:not(:active)`: records in the `hover` replay only, on the link only |
| `focus-visible-only` | a rule under `#link:focus-visible`: records in the `focus-visible` replay (a real Tab) only, on the link only |
| `active-only` | a rule under `#link:active`: records in the `active` replay (pointer down) only, on the link only |
| `focus-only` | a rule under the text input's `:focus`: records in the `focus` replay (`focus()`) only, on the input only (its own and its `::placeholder`'s) |
| `dark-only-token` | `--femto-spacing` changed only under `prefers-color-scheme: dark` without `data-theme`, every leg: `token` and `token-raw` records for it in leg `dark` only |
| `token-color-2-of-255` | `--femto-accent` from `rgb(1, 106, 168)` to `rgb(3, 106, 168)`, read only by `::selection`: `token` records through the color probes and `token-raw` records, and no style record |
| `token-color-1-of-255` | `rgb(2, 106, 168)` (1/255): token resolution tolerates it, and only `token-raw` records remain (the raw text differs) |
| `minified-equal` | `h1`'s `outline: none` and `background: none` written `outline: 0` and `background: 0 0`, and `--femto-shadow` written `0 0 .5rem rgba(0,0,0,.25)`, as clean-css wrote the oracle's: zero differences (Diff rule) |
| `minified-exact` | the same control with `--exact-minified`: `h1`'s `outline-width` and background position records (the shorthand in Chrome, `-x` and `-y` in Firefox) and `--femto-shadow`'s `token-raw` records, nothing else |
| `minified-real` | `h1`'s `outline: 2px solid` and `background: 0 1px`, and `--femto-shadow`'s blur `0.5rem` to `.3rem`: `outline-width` and `outline-style`, the position's `1px`, and `--femto-shadow`'s `token` and `token-raw` records are found; `background-position-x` (`0%` against `0px`) is not |
| `state-coverage` | word-spacing on the progress example's 8 punctuation tokens, with one entry for them: 16% of the document and 38% of the `article` the footer's hover collects; the state's records repeat the document's, so they cover nothing there, and the run has no coverage error and no unregistered record (16 registered: 8 in the document, 8 under hover) |
| `registry-styles` | two token values change, two tokens are added and the link gets a `:hover` rule (which `:active` matches too), with a registry of four narrow entries (a `token` entry for one token at `main` through `color`, a `token-raw` entry for it by `main`'s path, a `surface-added` entry for one token, a style entry with `where.states` `hover`), one style entry naming no comparison, and four that must not apply (`token: "*"`, a token entry without `where.comparisons` `styles`, one with `where.states`, and `token: "/./"`): each narrow entry registers exactly what it names, and the same token through other probes, at other anchors, the other changed and added tokens and the `active` records stay unregistered; the entry naming no comparison registers nothing; the first three bad ones are registry errors and `/./` is taken out of the cell by the in-page breadth guard |
| `registry-token-split` | the `registry-styles` changes, with three `token-raw` entries that split the names by first letter (`a-m`, `n-r`, `s-z`), each under half of the cell's names and together all of them: the in-page union limit takes all three out of the cell (`breadth:`), and the raw text records of `--femto-accent` and `--femto-spacing` stay unregistered |
| `registry-surface-split` | the same split for three `surface-added` entries with open patterns: the in-page union limit takes all three out of the cell (`breadth: the 3 surface-added entries with an open token pattern`), and the `--femto-new` and `--femto-other` records stay unregistered |
| `registry-surface-closed` | the `registry-styles` changes, with a `surface-added` entry that writes out 7 names (`/^--femto-(new\|other\|accent\|gone\|media\|nested\|raw)$/`: 7 of side B's 11 names, 64%, and 5 of side A's 9) and its twin with one open alternative (`r.w`): the closed set registers the two added tokens, and the twin, held to 50%, is taken out of the cell (`breadth: registry entry`) |
| `registry-pinned` | the progress example's 17 code tokens get `tab-size: 4`, `cursor: pointer` and `touch-action: manipulation`, 35% of the document's 49 elements, all one shape of tree path: a pinned entry (`/index.html`, `tab-size`, `8` to `4`) registers the `tab-size` records (32 per cell: the 16 tokens outside the value mask, and again under the footer's hover) with no breadth or coverage error; a pinned `cursor` entry over two shapes (12 tokens and the 3 list items, 31%) and a `touch-action` entry with `a` and `b` `*` are registry errors, so their records stay unregistered |
| `registry-consequence` | ten elements get `cursor: pointer` and the list `padding-block: 4px`, which makes the list, `main`, `body` and `html` taller: entries for the cursor and the padding (11 elements) and a layout consequence for `/index.html` (their heights, block sizes and origins) register every record; together they reach 14 of the 49 elements (29%), and the consequence covers nothing, so the cell has no coverage error and no unregistered record |
| `registry-consequence-unscoped` | the same, with the consequence naming no route: it covers what it registers, and the coverage rule fails the cell (`coverage:`) |
| `scroll-smooth` | side B gets `html { scroll-behavior: smooth }`, one registered record; the replays of `#far` on `/other.html` scroll instantly on both sides (`differ.js` `armStates`), so the spy's count is the same and nothing is unregistered, and after the replay `html`'s `scroll-behavior` is each side's own again (`result.json` cells' `scroll_behavior_a` `auto`, `scroll_behavior_b` `smooth`). With the override switched off in a copy of the harness, Chrome's `focus()` scrolls smoothly from the top and every state of `#far` shows `data-positions` `2` against `38` (`p2-fix-harness-r2-mutant-noscroll-2`); Firefox 160 scrolls a `focus()` and a Tab instantly whatever the page's `scroll-behavior`, so there the control passes either way |

The sections controls run `run.py sections --a fixture --b fixture:<control>` on the fixture's
one-page docs site in miniature (`fixtures/site/sections/`): three route pages
(`/sections/alpha.html`, `/sections/beta.html`, `/sections/picker.html`, each an hgroup beside a
`div#content[role=document]`, as the Phase 2 site's routes are), a color variant
(`/sections/picker/jade.html`, which links `jade.css`), the one page `/sections/docs.html` (each
section's hgroup, with the `h1` that carries its id, inside its `<section>`; a head script that
writes `jade.css` for `?theme=jade`), and `menu.json` in the shape of `site/docs/menu.json` at
`static-femto`, which `targets.json` names as the fixture's `menu`. Four routes, widths 375 and 1300,
the light leg (Alpha and Beta only for the two geometry controls and `sections-graft-changed`). Alpha's
route page also holds a `dialog.note` in its `main`, which the one page puts at the end of Alpha's
section, so both of side A's grafts (the hgroup before the content, the dialog after it) are
exercised; `sections.css` gives the hgroup the same box as a grid item and as a block. The registry of
every control but `sections-bare` holds two `merge-layout` entries naming `one-page`: the root pair
(`#content > section`, `div` against `section`) and the section id on the hgroup's `h1` (`attribute`
`id`, `null` against `*`).

| Control | Expectation |
|---|---|
| `sections-bare` | the one page as it is (`sections-unchanged`: a comment changes, so the run is no self comparison) and no entry: every cell has exactly two records, the root pair (`structure` `tag` `div` to `section`) and the grafted hgroup's `h1` id (`attribute`, absent to the section's id), Alpha's grafted dialog matching, and side B's URLs are `docs.html#alpha`, `#beta-two`, `#picker` and `docs.html?theme=jade#picker` |
| `sections-same` | the same with the two entries: zero unregistered records in every cell, the color route included (its swatch takes `jade.css` on both sides), and no breadth or coverage error |
| `sections-graft-changed` | the one page's Alpha hgroup description and its note dialog change text: in each Alpha cell exactly two `text` records, one on each graft, and nothing in Beta's cells |
| `sections-changed` | one list item's text in the one page's Beta section: one `text` record in each Beta cell and nothing in the other sections' cells |
| `sections-missing` | the Beta heading loses its id: each Beta cell is a harness error (`root section around #beta-two (no element has the id beta-two) not found`), and the other cells pass |
| `sections-theme-ignored` | the one page's head script ignores `?theme=jade`: the color route's cells differ in the swatch's `background-color` and nothing else; the picker's own route does not |
| `sections-geometry` | a third grid track at 1300 px narrows every section there, the content column loses 16 px at 375 px, and Alpha's lead paragraph changes color, title and an item's text and gains a ninth item, at every width; with a section layout consequence for Alpha at 1300 (`selector` `*`, seven geometry longhands): at Alpha 1300 no geometry record is left unregistered (60 registered) while the color, attribute, text and structure records are, with no breadth or coverage error; at Alpha 375 and in Beta's cells the consequence registers nothing and the geometry records stay unregistered |
| `sections-geometry-evasion` | the same change with ten near misses of the consequence instead (any property; color beside geometry; an open property pattern; no comparison; a width range; no width; three widths; two routes; a route pattern; another category): each is a registry error (a `*` selector over a whole page is too broad), none registers anything, and Alpha's 60 geometry records at 1300 stay unregistered |

A control whose run has a harness error fails, whatever its records (the expected `not found` errors
of `sections-missing` and the registry errors of the controls that expect them aside).

## Known limits

- A section layout consequence registers sizes and positions only. Where the narrower box wraps a
  line elsewhere, a space that now ends a line renders nothing and its element's own text loses it
  (Collection's whitespace rule), a `text` record the consequence does not cover: on the real one
  page, `/docs/link` at 1300 px, the paragraph before the class-less version link, `' ... in the .'`
  against `' ... in the.'` (`p3-harness2-sections-full-1`, Chrome and Firefox, light and dark). It
  takes an ordinary `text` entry with an exact selector and that route and width.
- One Safari pass compares only the OS scheme's media leg (registered `media:*` skip), so each
  Safari gate needs the owner's dark pass.
- Interactive states (hover, focus, focus-visible, active) are compared only in the styles mode, and
  only for the elements `harness/states.json` names, on its routes and widths (Tokens and states): a
  few elements per component, not every match, and one state at a time (no hover and focus
  together, no `:checked` or `:invalid` the user would cause, no open menu but the dropdowns it
  opens). The pages mode reads each document as loaded; widgets and their behavior belong to the
  behavior mode.
- The replay's instant scrolling is proved in Chrome only (control `scroll-smooth`): Firefox 160
  scrolls a `focus()` and a Tab instantly whatever the page's `scroll-behavior` (with the override
  off, `p2-fix-harness-r2-mutant-noscroll-2`, the spy counted 38 positions in Chrome and 2 in
  Firefox, as on side A), so there a smooth page never scrolls mid-state, with or without it.
- Tokens are probed under the anchors only (Tokens and states): a token whose value an element below
  an anchor overrides shows only through that element's computed styles. Inline `style` attributes
  that declare tokens are not walked for names (femto's rule); their elements' styles are compared.
- Every document is read in its first-visit state: storage is emptied before each load, so only
  the stored color scheme of a data-theme leg ever reaches a page.
- Alignment pairs elements by content and keys (see Alignment and record kinds). When an element
  is both moved and changed, or several same-tag siblings change at once, the pairing can name a
  neighbour; every pair is still compared in full, so records are added, never lost.
- An exact copy of a data block counts once (Collection), on either side, so a page that writes the
  same JSON-LD twice equals one that writes it once; `head_repeats` shows it per side and
  `value_rules` lists the rule. A copy that differs in anything is compared.
- A line feed inside an element's text reads as one space. Firefox removes one between two CJK
  characters (CSS Text 3's segment break rules), so there a line feed against a space shows only as
  a width record, not a text record (`adv-p1f2-1`). No kept page holds CJK text.
- The head comparison covers the title, metas, non-stylesheet links, `<base>` and data-block
  scripts. Stylesheet and fetch-hint links, `<style>` elements, scripts that run (classic, module)
  and `<noscript>` show only through their effects (computed styles, the DOM they build, the request
  log); a fetch hint that changes nothing visible goes unseen. With `--root-a`/`--root-b` (Phase 3's
  section comparisons) the head is not compared at all.
- Cross-origin loads come from Resource Timing and the proxy's CSP reports, so a load that has not
  been made when the styles are read (a late `fetch()`, a lazy image below the iframe's 800 px, a
  click handler) is not seen. Resource Timing alone: Chrome Beta 158 lists every load the probe
  made; Firefox 160 lists none that failed at the network level (connection refused, an unknown
  host), and Safari 27.2 neither those nor a CORS-mode `fetch()` the server answered without
  `Access-Control-Allow-Origin`. A 404 and a `no-cors` load are listed in all three
  (`p0r2-rt-probe`, `p0r2-rt-probe-safari`). Firefox 160 also leaves out a cross-origin image it
  serves from its image cache after the first load in a session. The CSP reports cover those (the
  policy is checked before any fetch or cache), a worker's own loads and a frame in a closed shadow
  root, in Chrome and Firefox (`p0r4-rt-frames`, `p0r4-rt-nested`). Safari 27.2 reports a
  worker's loads but sent no report for a frame in a closed shadow root (Safari passes and
  Decision 16, 2026-11-01), so in Safari such a load is not seen. A frame the page cannot read is still a harness error on a `same_origin` side. Neither
  sees a WebRTC connection (no CSP directive governs one) or a page a script opens in a new window.
- The registry's breadth rule reads page sources with the HTML standard's tree construction for
  valid pages; it does not model the adoption agency for misnested formatting
  (`<p><b>x</p>y</b>`), foster parenting of content misplaced in a table, or the quirks-mode table
  rule. Round 4 checked it against html5lib 1.1 on 100 documents (the 64 oracle `server.html` pages,
  `dist/`, the fixture, the spike and 28 synthetic cases: optional tags, `<template>` with open
  cells and list items, MathML with its integration points, SVG `desc` and `title`): the same
  compared-element paths in 97; of the three others, the misnested case is the adoption agency, and
  in two (`</p>` in MathML, `</template>` with open list items) html5lib 1.1 predates the current
  standard, whose trees headless Chrome Beta 158 builds and the engine gives. It judges `dist`
  pages as written, before their scripts run, so a selector keyed to markup only a script adds (or
  to a state after an interaction) reaches about 0% of them there; the in-page guard judges it on
  the live documents of every cell (Divergence registry).
- The sections mode compares each section with its old route's `[role=document]` only: the head,
  the breadcrumb, the side nav and the table of contents are outside the roots (criteria 7 to 9 and
  the whole-page comparisons hold the rest of the page). A section is read where the browser's own
  fragment navigation puts it (`/docs#<id>`); what the page does as the reader scrolls (the spy, the
  `#hash`, `document.title`) is the behavior mode's.
- The registry's breadth rule judges a section entry on the reference documents by route: side A's
  route pages (the oracle's captures and `static-femto`'s pages, whole), and for `/docs` the one
  page's `docs.html` whole. The section a cell compares is judged by the in-page guard, on the live
  roots of every cell (Divergence registry).
- Whitespace counts where it renders a box of nonzero inline size (Collection), so a space that
  falls at a line's end or a wrap point in one width is not compared in that width, and whitespace
  inside a `display: none` subtree (Firefox's closed `<details>` content) is never compared. Where
  the line falls elsewhere at another of the six widths, the space is compared there.
- No box geometry is compared: no element's position (x, y offsets), only its computed styles, so
  a box that moves without changing size shows only through its ancestors' sizes, the grid tracks or
  the screenshots (the 404 page's footer: p1-shell-404-footer-track).
- The matrix has one viewport height, 800 px. A page shorter than the viewport differs from a taller
  one in where the free space goes; only the 404 page is shorter than 800 px at any matrix width.
- Computed styles cannot show `::-webkit-*`/`::-moz-*` vendor pseudo-elements (range thumbs,
  progress bars, spin buttons) or `:visited`; screenshots are the only signal for those, and
  `::selection` is not collected.
- Animations are finished before styles are read, so intermediate `@keyframes` steps are never
  compared. The typing demo is not compared at all; the behavior suite checks it.
- Screenshots cover the iframe viewport (the top 800 px after scrolling to the top), not the full
  page, and never gate.
- `prefers-reduced-motion` is not an axis; both sides run with the OS setting (no preference). From
  Phase 6 a Safari session of a comparison mode reads the OS motion through `differ.js`
  `H.hostStatus()`, logs `OS motion <value>` after `OS scheme` in `log.txt`, and refuses to start
  under Reduce Motion with a rig error ("Safari's OS motion is reduce, but the comparison modes run
  with no preference: turn macOS's Reduce Motion off ..."), since femto's reduce rule would flatten
  every transition and animation on both sides alike and hide their differences (rr-tests-2).
- The documents run in an iframe: a script that compares `window.top` with `window`, or that frames
  itself, would behave differently; neither the oracle nor the static site does.
- The proxy forwards HTTP only, not WebSocket.
- An inherited record is folded into its parent's registered record by value (Divergence registry,
  Inherited records): the harness cannot see whether the descendant has a rule of its own that gives
  it the parent's values on both sides; such a rule is the same difference.

## Harness proof

Proved on 2026-10-30, Phase 0 gate (acceptance criterion 1), on the test machine: macOS 27.2
(26B123), 10 CPUs, 16 GB, appearance Light, the screen locked all day (`lsappinfo front` reported
`loginwindow` at every check). Google Chrome Beta 158.0.8127.2 with chromedriver 158.0.8127.2,
Firefox 160.0 with geckodriver 0.37.1, Safari 27.2 with safaridriver 22625.2.8.11.9, Selenium
4.52.0, Pillow 13.0.0, uv 0.13.6 (CPython 3.15.2), Node 24.22.0. The oracle: tag `remix-final`
(507dcda), built in `tests/oracle/worktree` with its locked toolchain (yarn 1.22.22, wrangler 4.0.0,
miniflare 4.20250310.0, React 19.0.0, Remix 2.16.0) under Node 24.22.0.

Runs, in order (`tests/results/<run id>/`, gitignored):

| Run id | Command | Cells | Differences | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p0-gate-rig-cf` | `rig --browsers chrome,firefox` | 2 browsers | all checks pass | 0 | 4 s |
| (oracle capture) | `oracle` | 64 routes, 27 stylesheets, 46.3 MB | 0 capture errors | 0 | 39 s (twice: 14:59 and 15:44, the second with the final `oracle.py`) |
| `p0-gate-selftest-cf` | `selftest --browsers chrome,firefox` | 16 controls × 2 browsers | every control as expected | 0 | 66 s |
| `p0-gate-self-cf` | `self --full --browsers chrome,firefox` | 1,488 | 552 (24 `blob:` plus the server crash) | 503 | 429 s |
| `p0-gate-self-cf-2` | same, with server chunks | 1,488 | 731 in 29 cells | 0 | 410 s |
| `p0-gate-self-cf-3` | same, final code | 1,488 (1,015,224 elements) | **24, all the `/docs/colors` `blob:` href** | **0** | 418 s |
| `p0-gate-colors-blob-rule` | `self --full --browsers chrome,firefox --routes /docs/colors --blob-uuid-placeholder` | 24 | 0 | 0 | 14 s |
| `p0-gate-self-safari-light-1` | `self --full --browsers safari` (locked screen) | 453 of 744 (120 run, 324 skipped), stopped | 98 in 7 cells | 11 | 2,343 s |
| `p0-gate-self-safari-light-2` | same, with the Safari timeouts and session restarts | 445 of 744 (120 run, 324 skipped), stopped | 6 (`/docs/colors` `blob:`) | 2 | 2,461 s |
| `p0-gate-self-safari-light-3` | same, `--routes` every kept route but `/docs/css-variables` | 732 (414 run, 318 the registered skip `media:dark`; 261,924 elements) | **6, all the `/docs/colors` `blob:` href** | **0** | 2,723 s |
| `p0-gate-safari-quit-check` | `self --browsers safari --routes /demo --widths 375 --schemes light` | 1 | 0 | 0 | 9 s |
| — | `static` | 15 criteria | 2 PASS (3, 12), 3 FAIL (4, 5, 14), 10 NOT-YET | — | under 1 s |
| — | `registry` | 1 entry (`safari-no-media-dark`) | valid | — | under 1 s |

Integration smoke runs with the final code, all PASS with 0 differences and 0 harness errors:
`p0-gate-fast-smoke` (`fast --self`, 3 routes, 32 cells, 16 s), `p0-gate-pages-smoke` (`pages --a
oracle --b oracle`, a 404 route included, 6 cells, 7 s), `p0-gate-chunk-check` (`--max-documents 3`,
3 server chunks; it shows the `blob:` records by design). `pages --a oracle --b dist` exits 2 (no
`dist/` yet), as it should.

**Criterion 1 status.** Chrome and Firefox: over the full matrix the oracle equals itself except the
`/docs/colors` Download link, whose `href` is a `blob:` URL with a fresh UUID in every document (one
`attribute` record in each of the 24 cells; Diff rule). With the opt-in `--blob-uuid-placeholder`
those 24 cells pass. PLAN.md allows three masks only, so the harness does not hide it by default:
**the owner decides** whether the UUID placeholder becomes a default value rule, the `href` a fourth
mask, or neither (then criterion 1 cannot pass on `/docs/colors`). Safari, light OS, locked
screen: the same result over 53 of the 54 kept routes (`p0-gate-self-safari-light-3`: 6 `blob:`
records on `/docs/colors`, nothing else, 0 harness errors, no reloads, no pixel cell above
8/255); the 6 light `/docs/css-variables` cells could not run locked.
Safari dark: not run (the owner's pass, below).

What changed while proving, each found by a self run and fixed in the harness:

1. **The oracle servers ran out of memory.** In `p0-gate-self-cf` both wrangler 4.0.0 servers died
   together after about 1,240 page loads (workerd: "Reached heap limit", about 1.4 GB), and the
   last 241 cells hit "Connection refused" (503 harness errors). Cause: wrangler's
   inspector proxy buffers every DevTools event until a DevTools client connects (Rig notes,
   oracle server). Fix: `targets.json` `max_documents: 400` for the oracle and server chunks in
   `cli.py`/`runner.py` (fresh servers and sessions every 372 cells here). Its debug log, about
   300 MB per server per run, now goes to `tests/oracle/logs/` and is deleted after a clean stop.
2. **Chrome: transitions in closed `<details>`.** `p0-gate-self-cf-2`, `/docs/overflow-auto` dark
   800, side A: 699 style records on the links in the closed header dropdown and side-nav details
   (UA link colors, dropdown list opacity 1). Chrome updates a skipped subtree's style only when it
   is read, and a transition such a read starts never ticks there; probes on Chrome Beta 158
   confirmed both. Fix: the collector reads every element's style once, freezes again, then
   collects; an animation that still starts during collection is a harness error. In
   `p0-gate-self-cf-3` that extra freeze finished transitions in 504 of the 1,488 Chrome documents
   (744 cells, two sides each; none in Firefox), so Chrome had been reading start values inside
   closed details on both sides until then.
3. **Firefox: asynchronous font fallback.** `p0-gate-self-cf-2`, `/docs/rtl` at 375 and 600 in the
   first seconds of fresh sessions: 8 `transform-origin`/`perspective-origin` records on the italic
   Arabic `cite` (83.5 px wide on side A, 80.45 px on side B). A bare-page probe reproduced it
   (83.5 px until 2.1 s after startup) and showed `gfx.font_rendering.fallback.async` false lays it
   out at 80.45 px at once (three runs). Fix: the harness sets that pref.
4. **Safari: closed `<details>` cost and a wedged session.** In `p0-gate-self-safari-light-1` the
   collect call on `/docs/css-variables` timed out after 150 s (Safari recomputes the style of closed
   details content on every read; Rig notes, Safari), Safari kept running the script, every later
   command timed out, and the run was stopped with SIGTERM at cell 453 (it wrote its partial result
   and stopped its servers; the automation Safari and safaridriver it left were terminated by hand).
   Fixes: Safari script and client timeouts of 600 s and 660 s; a command timeout now restarts the
   session like a WebDriver error, with a forced quit that kills the driver and, for Safari, the
   automation instance. With them (`p0-gate-self-safari-light-2`) the restart worked, but the
   `/docs/css-variables` collect still never finished on the locked screen: Safari's WebContent
   process sat at 0% CPU mid-script for over ten minutes (Rig notes, Safari: long scripts on a
   locked screen). That route's 6 light cells therefore could not run locked; they are the owner's
   (below), and `p0-gate-self-safari-light-3` ran every other kept route.
5. **A stalled oracle response.** In the same run, side B's server answered one `/demo` request
   after 64 s (its debug log shows the worker idle meanwhile; no rebuild, no other load), past the
   proxy's 60 s, so side B collected the proxy's error page (92 records and a harness error). Fix:
   a document the proxy could not get counts as a readiness failure and is loaded once more.
6. **Leftover processes.** The first two Safari passes left their `--automation` Safari (and in the
   first, safaridriver) running; they were terminated by hand. Every Safari quit now terminates the
   automation instance.
7. **Smaller fixes.** `rig` reported the whole `lsappinfo` block as the front app (macOS 27's
   output format; now the name). The `blob:` value rule, first written on by default, is now opt-in
   (above), and the fixture's `blob:` link was removed so the `self` control proves only PLAN's
   masks. Chrome and Firefox WebDriver client timeouts went from 150 s to 180 s.

### Round 1: after the Phase 0 review (2026-10-30, evening)

A review tried to make the harness pass when it should not, with the real oracle behind a
passthrough proxy (side A) and a mutating proxy (side B). Every confirmed finding was fixed in the
harness; none was masked or registered:

1. **The head was never compared.** A wrong title, meta description, canonical link or `og:url` gave
   zero records. Now `head` records (Alignment and record kinds). Replayed: on `/docs/link` the four
   head changes are four `head` records in Chrome and Firefox (`adv-detection/r1-exp1`).
2. **Positional alignment hid content.** One element inserted early in `<main>` made a run of tag
   records and skipped over 700 elements, so a changed table cell below it went unseen once those
   records were registered. Now a keyed LCS. Replayed: on `/docs/table` the inserted paragraph is
   one `only-b` record naming it, and the changed cell `Mercury` to `Mercurius` is a `text` record in
   each of the page's three tables (`r1-exp2`, `r1-exp3`); a section inserted among sections on
   `/docs/grid` is one record (was 77 to 79), a removed docs-menu item on `/docs/button` one `only-a`
   record (was 11 with href and text noise). A tag change now still compares the text and children.
3. **The progress code mask was too wide.** It hid every token of the sample. Now only the value
   token's text and its two size-derived longhands; a changed `max` token and a changed token class
   on `/docs/progress` are now records (`r1-exp1`, `r1-exp2`).
4. **Self runs applied registry entries.** A plausible `id-rename` entry turned the `/docs/colors`
   self cell into PASS. Self comparisons now apply skipped-check entries only
   (`adv-detection/r1-self-registry-leak`: FAIL with the `blob:` record unregistered).
5. **Catch-all entries validated.** `selector: "*"` with `property: "*"`, `path: "*"` or `/./` are
   now registry errors unless scoped to named routes; the summary flags entries that register 100
   or more records in one cell (`BROAD`).

The oracle (`harness/oracle.py`): the Node 20 and 18.19.0 fallbacks used a command that cannot work
and now use one npx environment (both proved: The oracle); staleness now sees untracked files and a
digest of the outputs and installed packages, and builds and servers share `build.lock` (a test
showed an exclusive lock blocked while a server ran, and an edited ignored build file reported
stale); the capture adds the dark and 375 DOM of each route and `_variants.json`, the Pacifico font
files, and the 20 static Pico v1 pages as old paths. The static checks: criterion 12 fails when git
ignores a vendored file; 9 needs proof that html-validate ran; 11 checks that ESLint and
`css/use-baseline` at `widely` cover every site file and scans all site CSS; 4 requires the check
tools and allows only the recorded compat lint; 15 flags absolute URLs in JS and `blocking="render"`;
6 and the `dist` target keep wrangler's debug log out of `~/Library/Preferences`. Each was shown
failing on the review's violating tree and passing on a compliant one (scratch fixtures with eslint
10.14.0, @eslint/css 2.0.1 and html-validate 11.17.0 installed).

| Run id | Command | Cells | Differences | Harness errors | Wall clock |
|---|---|---|---|---|---|
| (oracle) | `oracle` (rebuilt first: the new digest was missing) | 64 routes, 27 stylesheets, 5 font files, 20 v1 pages at 200, 53.0 MB | 0 capture errors | 0 | 37 s build, 91 s capture |
| `p0r1-selftest-cf-2` | `selftest --browsers chrome,firefox` | 21 controls × 2 browsers | **21/21 as expected** | 0 | 86 s |
| `p0r1-self-cf` | `self --full --browsers chrome,firefox` | 1,488 (1,015,632 elements; 4 chunks of 372) | **24, all the `/docs/colors` `blob:` href** | **0** | 424 s |
| `p0r1-colors-blob-rule` | the same on `/docs/colors` with `--blob-uuid-placeholder` | 24 | 0 | 0 | 15 s |
| `p0r1-fast-smoke` | `fast --self --routes /,/docs/progress,/docs/loading` | 32 | 0 | 0 | 16 s |
| `p0r1-pages-smoke` | `pages --a oracle --b oracle --routes /docs/forms/input,/does-not-exist --widths 375 --browsers chrome` | 6 | 0 | 0 | 8 s |
| `p0r1-chunk-check` | `self --routes /demo,/docs/colors --widths 375 --browsers chrome,firefox --max-documents 3` | 8 (3 chunks) | 4 (`blob:`, by design) | 0 | 19 s |
| `p0r1-selftest-safari-dark` | `selftest --browsers safari --cases self,dark-only,theme-dark-only` (macOS dark by itself) | 3 controls | **3/3 as expected** | 0 | 31 s |
| `p0r1-safari-dark-control-*` | `pages --a fixture --b fixture:<c> --schemes dark --browsers safari` for head, inserted-early, inserted-same-tag, changed-tag-content, progress-code-token, masked-only, color-2-of-255 | 7 | each as in Chrome and Firefox | 0 | about 10 s each |
| `p0r1-self-safari-dark` | `self --full --browsers safari --routes` every kept route but `/docs/css-variables` (locked screen, macOS dark) | 732 (414 run, 318 the registered skip `media:light`; 262,026 elements) | **6, all the `/docs/colors` `blob:` href** | **0** | 3,151 s |
| — | `static` | 15 criteria | 1 PASS (3), 4 FAIL (4, 5, 12, 14), 10 NOT-YET | — | under 1 min |
| — | `registry` | 1 entry | valid | — | under 1 s |

`pages --a oracle --b dist` still exits 2 (no `dist/`). The first selftest (`p0r1-selftest-cf`)
failed `self` and `registry-suppression` in Firefox: the fixture's `<code>` was inline, so the
1-or-2-digit value changed its width and its `transform-origin`; the oracle's `pre > code` is a
block (Pico and its own CSS), and the fixture now is too. Criterion 12 now fails, rightly, until
`.gitignore` is fixed (Owner decisions, 3).

**Criterion 1 after round 1.** Chrome and Firefox: as before, only the `/docs/colors` `blob:` href
(24 cells), now with the head compared and the narrower mask; 1,015,632 elements, 0 harness errors,
0 reloads, 0 alignment fallbacks, 6 pixel cells above 8/255 (non-gating). Safari, light OS:
`p0-gate-self-safari-light-3` above (run with the round 0 differ). Safari, dark OS:
`p0r1-self-safari-dark`, the first Safari dark pass, run on a locked screen after macOS's Auto
appearance turned dark by itself (no setting changed): over 53 of the 54 kept routes the oracle
equals itself except the 6 `/docs/colors` `blob:` records, with 0 harness errors, 0 reloads and no
pixel cell above 8/255; every session read `OS scheme dark` and skipped `media:light` (registered).
Its first cells ran at 10 to 45 s each while Spotlight indexed (load average 24), then at about
6 s. The 6 dark `/docs/css-variables` cells need an unlocked screen, like the 6 light ones.

### Round 2: after the second review (2026-10-30, night)

The second review found two gaps. Both were confirmed (the first by replaying the review's own
case, the second by its scratch trees) and fixed in the harness; nothing was masked or registered:

1. **The JSON-LD structured data was never compared.** Every oracle route but `/docs/v1` and the
   404 holds a `<script type="application/ld+json">` (its `url`, `version`, `image`, `isBasedOn`),
   but `script` is a skipped tag and the head comparison read only the title, metas and links, so a
   page that dropped or changed it passed. Replayed with the review's passthrough and mutating
   proxies on `/docs/link` (the version to `9.9.9`, the url to `https://example.com`, the viewport
   meta and a marker attribute changed after hydration): the review's run had 2 records per browser
   (the viewport and the marker); now 4, adding `head script[type=application/ld+json] $.version`
   and `$.url` (`p0r2-replay-jsonld`). Every data-block `<script>` (a type that is not JavaScript)
   and `<base>` is now a `head` record, JSON compared leaf by leaf so that key order and whitespace
   never count (Alignment and record kinds); Known limits names what the head comparison still
   leaves to effects. New control `head-data`.
2. **Criterion 15 failed displayed text and missed real loads.** `static_checks.py` counted every
   absolute URL in dist JS as a cross-origin load, with no remedy for text a script only displays
   (the picker's CDN `<link>` sample, which Phase 3 may rebuild per `?theme=`), and it skipped
   inline `<script>` bodies, hosts without a dot and any URL built at run time. Now the harness
   reads each document's Resource Timing entries, and a cross-origin load on a `same_origin` side
   (`dist`, the fixture) fails the run outside the diff (Same-origin loads). The static check still
   fails on cross-origin URLs in markup, CSS and JS imports, and lists every other absolute URL in
   JS as a note (inline scripts and any host included). Shown on scratch trees: the picker sample
   alone gives NOT-YET and one note; a Google Fonts `<link>`, an inline dynamic `import()` and a
   module's static `import` fail; a `fetch()` to `localhost:8080` and to `192.168.1.5:3000` are
   notes. New control `cross-origin`, whose stylesheet URL is built at run time. The oracle's own
   cross-origin loads are reported, not judged: Google Fonts' Pacifico stylesheet and font file on
   `/docs/css-variables`.

| Run id | Command | Cells | Differences | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p0r2-replay-jsonld` | `pages --a <passthrough> --b <mutating> --ready-a oracle --ready-b oracle --routes /docs/link --browsers chrome,firefox --widths 1300 --schemes light` | 2 | 8 as intended (4 per browser, the 2 JSON-LD leaves among them) | 0 | 4 s |
| `p0r2-rt-probe`, `p0r2-rt-probe-safari` | `pages` of a scratch probe page against itself (Rig notes, Resource Timing) | 2, 1 | 0 | 0 | 4 s, 6 s |
| `p0r2-selftest-cf` | `selftest --browsers chrome,firefox` | 23 controls × 2 browsers | **23/23 as expected** | 0 | 94 s |
| `p0r2-self-cf` | `self --full --browsers chrome,firefox` | 1,488 (1,015,632 elements; 4 chunks of 372) | **24, all the `/docs/colors` `blob:` href**; 0 cross-origin loads judged | **0** | 421 s |
| `p0r2-colors-blob-rule` | the same on `/docs/colors` with `--blob-uuid-placeholder` | 24 | 0 | 0 | 16 s |
| `p0r2-fast-smoke` | `fast --self --routes /,/docs/progress,/docs/loading` | 32 | 0 | 0 | 17 s |
| `p0r2-pages-smoke` | `pages --a oracle --b oracle --routes /docs/forms/input,/does-not-exist --widths 375 --browsers chrome` | 6 | 0 | 0 | 8 s |
| `p0r2-chunk-check` | `self --routes /demo,/docs/colors --widths 375 --browsers chrome,firefox --max-documents 3` | 8 (3 chunks) | 4 (`blob:`, by design) | 0 | 17 s |
| `p0r2-rig-cf` | `rig --browsers chrome,firefox` | 2 browsers | all checks pass | 0 | about 5 s |
| `p0r2-selftest-safari-dark` | `selftest --browsers safari --cases self,dark-only,theme-dark-only` (macOS dark by itself) | 3 controls | **3/3 as expected** | 0 | 32 s |
| `p0r2-safari-dark-control-*` | `pages --a fixture --b fixture:<c> --routes /index.html --widths 1300 --schemes dark --browsers safari` for head, head-data, cross-origin | 3 | each as in Chrome and Firefox (cross-origin: 1 load, 0 differences) | 0 | 6 to 11 s each |
| `p0r2-self-safari-dark` | `self --full --browsers safari --routes` every kept route but `/docs/css-variables` (locked screen, macOS dark) | 732 (414 run, 318 the registered skip `media:light`; 262,026 elements) | **6, all the `/docs/colors` `blob:` href**; 0 cross-origin loads judged | **0** | 2,726 s |
| — | `static` | 15 criteria | 1 PASS (3), 4 FAIL (4, 5, 12, 14), 10 NOT-YET | — | under 1 min |
| — | `registry` | 1 entry | valid | — | under 1 s |

`pages --a oracle --b dist` still exits 2 (no `dist/`). The `head-data` and `cross-origin` controls
run the light leg, so in Safari on a dark OS they run as the `p0r2-safari-dark-control-*` runs
above; the owner's light `selftest` runs them as controls. The Chrome and Firefox self run's head
data held 20 entries per document (21 on `/docs/progress`, whose hydrated DOM had the JSON-LD
twice in that run's loads) and at most 40 Resource Timing entries per document, far from the 250-entry
buffer. Correction (round 3): not on every load. The block is doubled only when the page's random
progress value differs between server and client; the third review saw one block in 6 of 200 loads,
which made criterion 1 fail at random until round 3 counted exact copies once.

**Criterion 1 after round 2.** Unchanged in substance, now with the data blocks compared and each
document's loads read. Chrome and Firefox (`p0r2-self-cf`): over the full matrix the oracle equals
itself except the 24 `/docs/colors` `blob:` records; 1,015,632 elements, 0 harness errors, 0
reloads, 0 alignment fallbacks, 5 pixel cells above 8/255 (non-gating). Safari, dark OS
(`p0r2-self-safari-dark`, locked screen, both sessions `OS scheme dark`): over 53 of the 54 kept
routes the same, 6 `/docs/colors` `blob:` records and nothing else, 0 harness errors, 0 reloads, no
pixel cell above 8/255. Safari, light OS: still `p0-gate-self-safari-light-3`, run with the round 0
differ.

Not yet proved, all needing the owner (commands below): `rig` in Safari (its input checks need an
unlocked screen); the Safari light pass with the current differ (the light pass above ran before
round 1's head comparison and keyed alignment and round 2's data blocks; macOS was dark for the rest
of the evening); the full `selftest` in Safari on a light OS; the 12 `/docs/css-variables` Safari
cells, light and dark (they need an unlocked screen); and the spike in Safari (PLAN's Phase 0 gate: "the spike passes in
Safari"; `docs/research/05-spike.md` has no Safari result yet). The decision on the `blob:` URL
comes first, because every `/docs/colors` cell reports it until then. Phase 0's gate is not met
until these pass.

### Round 3: after the third review (2026-10-31, morning)

The third review left 13 findings open. Each was confirmed (by the review's own runs and trees,
replayed) and fixed in the harness; nothing was masked or registered:

1. **Criterion 1 was nondeterministic on `/docs/progress`** (the blocker). Round 2 compared the
   JSON-LD block, and the oracle's hydrated head holds it once or twice depending on its random
   progress value (Collection); the review's four runs failed three times, 39 one-sided `head`
   records under `script[type=application/ld+json]#2` per failing cell. Two runs here before the fix
   happened to pass (96 loads, all doubled). Now an exact copy of a data block counts once, before
   repeats are numbered, in `differ.js` and in the registry's head keys; `head_repeats` shows it per
   side. Controls `head-data-copy` (zero differences) and `head-data-near-copy` (a copy that
   differs in one leaf: nine records) prove it changes nothing else.
2. **The registry's breadth rule had four gaps** (`DET5-R2-1` to `-4`): `where.routes: ["*"]` was a
   one-route scope that matched every route; `--root-a`/`--root-b` records had paths of the form
   `body{body} > ...`, which no reference path has, so a path pattern on `{` reached 0%; route-scoped
   entries were exempt from every union, so a catch-all split into 29 entries of three routes passed;
   and a scope of routes with no reference document (the 20 v1 pages) was judged on nothing. Now a
   `where.routes` item must be a route or a `^`-regex; root runs carry the document's own paths from
   `html`; all the entries of a kind share the kind budget; and at most 3 routes of a scope may lack
   a reference document (Divergence registry, Breadth). The review's directories `star-route`,
   `route-split`, `uncaptured` and `uncaptured-v1` are now rejected entry by entry, and its
   end-to-end runs fail with every difference unregistered (`p0r3-e2e-*`).
3. **The breadth engine had no HTML tree construction** (`DET5-R2-5`): page sources (dist/, the
   fixture) were read as if every end tag were written, so a page that omits optional tags gave a
   tree no browser builds. They are now read with the standard's tree-construction rules
   (`_StaticBuilder`), cross-checked against html5lib 1.1 on 85 documents (Known limits).
4. **Nested loads** (`R2-NEW2-NESTED`): the run-time check read only the top document's Resource
   Timing. It now reads every frame the page can read, at any depth, and an unreadable frame is a
   harness error on a `same_origin` side; worker scripts are read strictly by the static check;
   Firefox's image cache is a Known limit. Replayed on the review's probe pages (`p0r3-rt-nested`):
   the iframe's stylesheet and the `srcdoc` image are now listed in both browsers (Firefox lists the
   image on side A only, the cache case); the worker's fetch is still unseen at run time, as
   documented. New control `cross-origin-frame`.
5. **The site-origin exemption was too wide** (`R2-NEW2-SITEHOST`): any URL on host `femto.style`
   was exempt; now only `https://femto.style` on the default port (http and other ports fail, as in
   `static_checks.same_origin()`), and the summary lists these loads.
6. **Static checks** (`C4`, `C9`, `PKG-1`, `R3-NEW-1`). Criterion 11 fails an inline ESLint rule
   configuration of a use-baseline rule and wants a reason on any other (the review's
   `c11/inline-allow` tree now fails on both files). Criterion 15 tells a regex from a division after
   the `)` of an `if`, `for`, `while` or `with` head and after `export default`, decodes CSS escapes,
   fails a classic script that `document.write()` writes, reads `data:` documents in iframes,
   frames, objects and embeds, reads `document["write"]`, `import(("x"))` and the legacy
   `background` attribute, and reads worker scripts strictly (the review's `c15-evade` and
   `c15-write-script` trees now fail on every planted load). Criterion 13 no longer reads CSS's
   `@import "femto.css"` as a package (the review's `false-fail` tree passes its package part), and
   now reads esm.sh, esm.run, Skypack, jspm and cdnjs URLs, a package named in prose, install
   commands in prose and across a backslash continuation, string literals joined with `+` and JSON
   data blocks (the `misses` tree fails on all three planted names); a sentence that only mentions
   Composer is listed, while a composer command, a Packagist URL or an offer to install with
   Composer still fails. The 23 fixture trees of round 2 keep their expected states.

Also new: **`dist:<path>`** (Modes, Named targets), any built folder served exactly as `dist`, so
Phase 1's agents can each compare their own build at once; the command targets' shutdown now reaps
`npm exec` before it reads the process group (it had waited 10 s and then failed with
`EPERM` at every stop); and the selftest runs every control with a registry of its own, so the
phase agents' entries in `tests/divergences/` cannot fail it (a `p1-shell.json` entry that the
breadth rule rejected while `dist/` held 5 pages failed 17 controls in a first selftest run).

| Run id | Command | Cells | Differences | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p0r3-progress-before-1`, `-2` | `self --full --routes /docs/progress --browsers chrome,firefox --no-shots`, before the fix | 24 each | 0 (all 96 loads had the block twice) | 0 | 12 s each |
| `p0r3-progress-1` to `-6` | `self --full --routes /docs/progress --browsers chrome,firefox`, with the fix | 24 each, 288 loads | **0 in every run**; 4 loads had one block (runs 2, 5 and 6, side A), each in a cell whose other side had two: the case that failed before | 0 | 12 s each |
| `p0r3-selftest-headcopy`, `p0r3-selftest-frame`, `p0r3-selftest-registry` | `selftest --browsers chrome,firefox --cases ...` for the new controls | 5, 3 and 4 controls | as expected | 0 | about 25 s each |
| `p0r3-selftest-cf` | `selftest --browsers chrome,firefox` | 29 controls × 2 browsers | **29/29 as expected** | 0 | 199 s |
| `p0r3-fast-distdir-2` | `fast --a dist:<scratch copy> --b dist:<another copy> --routes /,/docs,/demo,/examples,/does-not-exist`, the repository's wrangler 4.156.0 | 56 | 0 | 0 | 11 s |
| `p0r3-pages-femto-wrangler` | `pages --a dist --b dist:<scratch copy>` with `FEMTO_WRANGLER` (a scratch install of wrangler 4.156.0) | 4 | 0, and a `cap:` line per side | 0 | 7 s |
| `p0r3-rt-nested` | `pages` of the review's probe pages (`iframe.html`, `srcdoc.html`, `worker.html`) against themselves | 6 | 0; loads listed as above | 0 | 3 s |
| `p0r3-e2e-star-route`, `-route-split`, `-uncaptured`, `-root-path-x` | the review's end-to-end evasions (`pages --a fixture --b fixture:registry-evasion`, its registries) | 2 each | 106 (96 with the roots), **all unregistered**, FAIL | the registry errors (none for root-path, whose entries are valid and match nothing) | 6 s each |
| `p0r3-self-cf` | `self --full --browsers chrome,firefox` (criterion 1; Phase 1 agents shared the 4 slots) | 1,488 (1,015,632 elements; 4 chunks of 372) | **0** (the `blob:` href normalized by default); 47 of the 48 `/docs/progress` documents had the block twice, and the one cell with one block on side A passed | **0** | 1,016 s |
| `p0r3-progress-final-1` to `-4` | `self --full --routes /docs/progress --browsers chrome,firefox`, the final code | 24 each, 192 loads | **0 in every run**; 3 cells with one block on one side and two on the other | 0 | 16 to 19 s each |
| `p0r3-selftest-cf-final` | `selftest --browsers chrome,firefox`, the final code | 29 controls × 2 browsers | **29/29 as expected** | 0 | 131 s |
| — | `registry` | 17 entries (`rig.json` and the Phase 1 agents' `p1-shell.json` at the time) | valid | — | under 1 s |

**Criterion 1 after round 3.** Chrome and Firefox (`p0r3-self-cf`): over the full matrix the oracle
equals itself, 1,015,632 elements, 0 differences, 0 harness errors, 0 reloads, 0 alignment
fallbacks, 7 pixel cells above 8/255 (non-gating), at most 40 Resource Timing entries per document.
`/docs/progress` passed in all 11 runs of round 3 with the fix (10 route runs and the full matrix,
528 loads), and 8 of those loads had one JSON-LD block. Safari: unchanged since round 2, and the owner's
steps below still stand; they now need no flag for the `blob:` URL.

### Round 4: after the fourth review (2026-10-31, afternoon)

The fourth review left 12 items open. Each was confirmed with the review's own trees, registries and
runs, replayed against the round 3 code first, and fixed in the harness; nothing was masked or
registered:

1. **The breadth rule read patterns with Python's `re`, the differ with JavaScript's `RegExp`**
   (`NF-REGEX-DIALECT`, part of `DET-5`): `/^(?!.*\Z)/` matched nothing in Python and every path in
   JavaScript, so five such entries registered all 106 records of the review's run. Path patterns
   are now judged with JavaScript itself (one `node` call over every reference path and head key),
   and every regex the differ applies must compile there.
2. **A selector keyed to markup only a script adds** (`NF-RUNTIME-DOM`, part of `DET-5`): `.adv-js,
   .adv-js *` reached 0% of the page sources and every element of the live page. Every cell now
   applies the per-document limits again on its live documents (`breadthGuard` in `differ.js`): an
   entry, or a kind's entries together, over them is a harness error and is not applied there.
3. **Route-scoped catch-alls** (`DET5-R2-3`, `DET5-R2-4`): entries naming three routes each were
   exempt from every share limit, so 36 `*` entries covered 25 unbuilt routes under the kind budget,
   and seven covered the 20 uncaptured v1 routes; a page that did not exist passed. Now a route
   scope narrows only where an entry applies: every entry stays under the per-document limits, the
   whole registry names at most 3 routes without a reference document, and in every cell the
   registered records may cover at most 25% of either document, so a missing page fails however
   narrow the entries (control `registry-missing-page`).
4. **The kind budget followed how much of `dist/` was built** (`NF-KIND-BUDGET-SMALL-DIST`): site
   shares now count only complete sites (the oracle; a build holding every kept route), and the
   budget rejects only the route-scoped entries that reach the site over it.
5. **`</template>` and MathML in the tree builder** (`NF-TEMPLATE-TREE`): `</template>` now closes all
   that is open in its template, and MathML is foreign content with its integration points
   (`annotation-xml` with an HTML encoding, `mi`, `mo`, `mn`, `ms`, `mtext`), as are SVG `desc` and
   `title`. Cross-checked on 100 documents (Known limits), and the three disputed trees against
   headless Chrome Beta 158's.
6. **Loads the page cannot read** (`R2-NEW2-NESTED`): frames in open shadow roots, declarative ones
   included, are now read; and the proxy's report-only CSP reports a worker's loads, a frame in a
   closed shadow root and Firefox's cached image (The proxy). New controls `cross-origin-worker` and
   `cross-origin-closed-shadow`. Statically, a worker API used in a form the check cannot follow
   (`new (Worker)(...)`, `const W = Worker`, a `serviceWorker` in a variable) now reads every script
   strictly.
7. **Static checks** (`C4`, `C9`, `PKG-1`, `NF-CSS-IMPORT-PKG-PATH`). Criterion 11 reads quoted rule
   names (`"css/use-baseline": [...]`, ESLint's documented form) and ESLint's own description
   separator. Criterion 15 reads JavaScript with espree, ESLint's parser, so `{} / 2 +
   import("https://...")` is a division and then an import, and a script espree cannot read fails;
   `<image src>` is an image; `document.write.call()` and `.apply()` are writes; a `javascript:` URL is
   percent-decoded and its string result read as HTML; an HTML sink used in a form the check cannot
   follow reads every string that holds markup as HTML. Criterion 13 lists an offer its own clause
   denies ("You cannot install femto with Composer") instead of failing it, no longer reads
   `package.json` as a package, and fails a CSS `@import` path into a wrongly named package
   (`@import "femto/css/tokens/base.css"`).

Also changed: `registry-route-scope` now proves that a catch-all naming its one route is rejected
and that a narrow route-scoped entry applies on its route only, and `registry-evasion` holds 67
evasions (the dialect patterns and the split v1 scope added).

| Run id | Command | Cells | Differences | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p0r4-selftest-new-1` | `selftest --browsers chrome,firefox --cases` the 7 new and changed controls | 7 controls × 2 browsers | **7/7 as expected** | 0 | about 45 s |
| `p0r4-rt-frames` | `pages` of the review's frame probes plus closed shadow roots and workers (scratch site, another origin on a second port) against themselves | 22 | 0; every planted load listed on both sides in both browsers, the shadow and declarative-shadow frames by Resource Timing (`frames_read` 1), the closed-shadow frames, the sandboxed frame and both workers by CSP reports | 0 | 5 s |
| `p0r4-rt-nested` | `pages` of round 3's probe pages (`p0r3-rt-nested`) | 16 | 0; Firefox's cached `srcdoc` and `cache.png` images, missing from its Resource Timing, now listed by CSP reports; the worker's fetch listed in both browsers | 0 | 5 s |
| `p0r4-e2e-budget` | the review's `pages --a oracle --b dist --routes /docs/progress,/docs/brand` with its 38-entry registry | 4 | 487: **485 unregistered**, and the status record of the two `/docs/progress` cells registered by the one valid entry (the review's single-route status entry); 37 entries rejected | the registry errors | 7 s |
| `p0r4-e2e-dialect-Z` | the review's `pages --a fixture --b fixture:registry-evasion` with its `\Z` registry | 2 | 106, **all unregistered**; its 5 entries rejected | the registry errors | 4 s |
| `p0r4-e2e-runtime-class` | the review's `pages --a dist:rc/A --b dist:rc/B --routes /` with its `.adv-js` registry | 2 | 40, **all unregistered** (the 4 entries are valid statically) | 4 per cell (`breadth:`, one per entry) | 6 s |
| `p0r4-live-dist`, `p0r4-live-build` | `pages --a oracle --b dist` (and a scratch build of today's `site/`) on the five built routes, the live registry | 40 each | Phase 1's own open differences; the live registry's 17 entries valid, and no `breadth:` or `coverage:` error, no CSP report | 0 | 13 s each |
| `p0r4-selftest-cf` | `selftest --browsers chrome,firefox` | 33 controls × 2 browsers | **33/33 as expected** | 0 | about 200 s |
| `p0r4-self-cf` | `self --full --browsers chrome,firefox` (criterion 1, with the CSP header on every oracle response; Phase 1 agents shared the 4 slots) | 1,488 (1,015,632 elements; 4 chunks of 372) | **0**; CSP reports only on the 48 `/docs/css-variables` documents (its Google Fonts, reported for the oracle, as Resource Timing lists them), none of them `csp_other` | **0** | 508 s |
| — | the review's trees: `c11/quoted`, `c15/{brace,image,writecall,jsurl,worker-paren,worker-alias,sw-alias}`; `t_c13*.py`; the round 2 fixture trees; round 3's `c11/inline-allow`, `c15-evade`, `c15-write-script`, `c13-probes` | — | every planted case FAILs, every true sentence passes; the 23 round 2 fixture trees keep their states | — | — |

**Criterion 1 after round 4.** Chrome and Firefox (`p0r4-self-cf`): over the full matrix the oracle
equals itself, 1,015,632 elements, 0 differences, 0 harness errors, 0 reloads, 0 alignment
fallbacks, 7 pixel cells above 8/255 (non-gating). The report-only CSP changed nothing the harness
compares. Safari: unchanged since round 2 (the owner's steps below), and its CSP reports are not
probed yet (Known limits).

### Phase 1 gate (2026-10-31, afternoon)

PLAN's Phase 1 gate: criterion 2 (`pages --a oracle --b dist`, the Chrome and Firefox full matrix),
the behavior suite for every widget in Chrome and Firefox, and criteria 4, 5 (both except
`site/assets/legacy/`) and 6 (the Phases 1 and 2 column), with 3 and 12. Run from 15:26 to 15:46 on
the rig: Chrome Beta 158.0.8127.2 (chromedriver 158.0.8127.2), Firefox 160.0 (geckodriver 0.37.1),
Selenium 4.52.0, Node 24.22.0, the repository's wrangler 4.156.0 (`node_modules`, as pinned; no
`FEMTO_WRANGLER`), the oracle at `remix-final`. `dist/` was removed and rebuilt with `npm run
build` first (186 files). Nothing under `site/`, `build.mjs`, `package.json`, `tests/divergences/`,
`tests/harness/` or `tests/behavior/`, nor `run.py` or `static_checks.py`, changed between that build
and the last run, and the static checks' two rebuilds were byte-identical to it. No run had a
harness error, so the harness was not changed.

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p1-gate-pages-full-1` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2) | 1,488 (744 per browser; 978,384 elements; 4 chunks of 372) | **PASS**: 69,924 differences, **0 unregistered**; registered by category: `dropped-route` 68,412 (24 entries), `oracle-bug` 1,488 (`og:url`), `asset-path` 24; 0 cross-origin loads from `dist`, 0 reloads, 0 alignment fallbacks | **0** | 460 s |
| `p1-gate-static-1` | `static_checks.py --phase 1` (the inferred phase is 0: no Workflow commit yet) | 15 criteria | **3, 4, 5, 6 and 12 PASS**; 8, 9 and 14 FAIL (later phases' criteria, below); 1, 2, 7, 10, 11, 13 and 15 NOT-YET | — | 10 s |
| `p1-gate-bh-dist-1` | `behavior --target dist --browsers chrome,firefox` | 132 runs (50 checks, all 9 groups) | **PASS: 132 PASS**, 0 FAIL, 0 XFAIL, 0 XPASS, 0 ERROR | 0 | 273 s |
| `p1-gate-bh-oracle-1` | `behavior --target oracle --browsers chrome,firefox` | 132 runs | **PASS: 112 PASS, 20 XFAIL** (the nine oracle-bug checks, `color-scheme-flash` on two routes, each at its named assertion in both browsers), 0 FAIL, 0 XPASS, 0 ERROR | 0 | 261 s |
| `p1-gate-selftest-cf-1` | `selftest --browsers chrome,firefox` | 33 controls × 2 browsers | **33/33 as expected** | 0 | 205 s |
| — | `registry`, before and after the runs | 27 entries in 10 files | valid: `asset-path` 1, `browser-limit` 1, `dropped-route` 24, `oracle-bug` 1 | — | 2 s |

In `p1-gate-pages-full-1` every one of the 26 Phase 1 entries registered records; the only unused
entry is `safari-no-media-dark` (no Safari cell). The summary flags one entry `BROAD`:
`p1-shell-footer-dropped-links-current-color`, 102 records in each `/docs` cell, which is the six
footer links that point at `/docs` instead of a dropped route (current on `/docs`) times the 17 color
longhands its property pattern names; its samples are all on those links. Pixels (not gating): 1,464
of the 1,488 cells differ by more than 8/255, every route but `/demo`. Corrected in round 1 of the
fixes (below): this report first gave the dropped maintenance banner as the cause of all of them,
which holds for most routes (the page below it sits 37 to 49 px higher) but not for two: on `/` the
dropped Stats move everything below the hero up by 110 to 265 px more, and on the 404 page at 800,
1100 and 1300 px the footer sits 43 to 100 px higher than the banner explains, with blank space
under it (p1-shell-404-footer-track). The oracle's `/docs/progress` held its JSON-LD twice in 24
side A documents (Collection).

The static checks' three failures belong to later gates: 8, `docs.html` has no `og:title` or
`og:description` (Phase 3, Decision 9; its `/demo` is not in `sitemap.xml`, a note); 9,
html-validate's recommended rules report 1,154 errors in all 54 pages (no config in the repository,
Owner decisions 4) and 22 duplicate ids such as `check-icon` on the 19 color routes (Decision 13's
renames are Phase 3's); 14, 32 files outside the allow-list mention Pico (Phase 4 rewrites the
content). Criterion 15's static part found no cross-origin resource in the 54 pages and the inline
head script as the only render-blocking script.

**Phase 1 gate status.** Met in Chrome and Firefox: criterion 2 with zero unregistered differences
over the full Chrome and Firefox matrix, the behavior suite passing against `dist` and holding
against the oracle, and criteria 3, 4, 5, 6 and 12 passing. PLAN's Phase 1 gate has no Safari part;
Phase 0's Safari steps below are still open.

### Phase 1 fixes, round 1 (2026-10-31, evening)

The gate review left 26 findings (parity honesty PH-1 to PH-7, behavior coverage bh-1 to bh-9, PLAN
compliance plan-1 to plan-11). Each was confirmed against the review's own runs and trees first.

What changed:

1. **A rendered space the harness could not see** (PH-1). The footer's two inline `<p>`s had a
   newline between them that renders as a space; the oracle has none. The footer now writes them
   with no whitespace between, and the pages mode compares rendered whitespace: element text is read
   run by run, and whitespace counts as one space exactly where it renders an inline box
   (Collection; `value_rules` lists the rule). New controls `whitespace` (FAILs with the old rule,
   `p1f1-selftest-ws-oldrule`) and `whitespace-collapsed`. Replayed on a scratch copy of `dist/` with
   the old footer (`p1f1-fast-oldfooter`): 20 unregistered `text` records, one per 1300 cell
   (`section: '' -> ' '`, the footer's second section); at 375 the two `<p>`s wrap, the space falls at
   the line's end and renders nothing, so no record, as nothing differs there. The review's other
   innerText difference, whitespace between the full-width inputs of `/docs/forms/input`, falls at a
   wrap point too and is not a difference.
2. **Registry entries that said less than they registered** (PH-2 to PH-5). `p1-shell-body-grid-rows`
   now names four tracks against three and `0px` and leaves out `/` and the 404 page; the 404 page's
   footer displacement has its own entry, `p1-shell-404-footer-track`, whose reason states it, with
   Phase 2's fix in its notes; `/` has `p1-landing-body-grid-rows` and `p1-landing-page-height`, which
   name the Stats, and `p1-shell-page-height` no longer applies there; the menu's `--max-height`
   entries state the sub-pixel sticky offset from 1024 px; the footer's six links to `/docs` carry
   their accessibility cost in their notes (Known Phase 1 deviations). The gate report's pixel
   attribution is corrected above. The matrix keeps its one 800 px height (Known limits).
3. **The data-block copy rule** (PH-6) is listed in `value_rules`; the owner is asked about it (Owner
   decisions 7).
4. **The pre-JavaScript HTML** (PH-7): every page's `<body>` has the oracle's server-side
   `style="min-height:100vh"` (site.js then sets innerHeight in px, as before), and `build.mjs` writes
   the header theme toggle's `href` as the page's own path (`#` on the 404 page, which site.js sets on
   load). The woff fallbacks are on record (Known Phase 1 deviations).
5. **Behavior** (bh-1 to bh-8, plan-8). New checks: `toc-spy`, `theme-os-live`,
   `comparison-toggle`, `theme-toggle-keyboard`, `mobile-menu-keyboard`, `copy-button-repeat`,
   `color-modal-resize`, `demo-offscreen` (XFAIL on the oracle) and `picker-logo`; `mobile-menu-link`
   now goes back and checks the menu, `side-menu-max-height` checks `<body>`'s min-height. Two
   widget fixes: a copy link no longer restarts its timer on a second click (each click schedules its
   own revert, as Code.jsx's did), and `docs.js` no longer closes the mobile menu on Escape (the
   oracle has no Escape there; Phase 3 adds it). `picker.js` animates the header logo for 1 s on
   every in-place route change, as HeaderContext.jsx did. With the review's planted bugs and two more
   (a copy timer that restarts, no logo animation) in a scratch copy of `dist/` (`p1f1-bh-mut-1`), the
   new checks fail 35 of 38 runs: every planted bug fails in Chrome, and the three Firefox passes are
   the keyboard checks, whose bug (`event.detail === 0`) Firefox cannot show, since it gives an
   Enter-activated click a nonzero detail.
6. **Build** (plan-2): a route with no section file fails the build, and `--only` is refused for
   `dist/`. **Static checks** (plan-7): criterion 6 probes the Pages-inherent paths. **docs.js**
   (plan-9): the route-group protocol moved to Behavior, Editing docs.js.
7. **On record, not code** (bh-9, plan-1, plan-3 to plan-5, plan-10, plan-11): Known Phase 1
   deviations and Owner decisions 7. plan-6 (criterion 4 on the literal `git ls-files`) needs the
   Phase 1 commit, which is the orchestrator's: commit with `git add -A`, so the deletions and the new
   files (`.claude/launch.json` included) are in it.

Runs on the rig (Chrome Beta 158.0.8127.2, Firefox 160.0, Selenium 4.52.0, Node 24.22.0, the
repository's wrangler 4.156.0), the gate block from 16:36 to 16:59 after `dist/` was removed and
rebuilt (186 files), with no input changed between the build and the last run:

| Run id | Command | Cells or runs | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p1f1-selftest-ws-1` | `selftest --cases whitespace,whitespace-collapsed,text,self,changed-tag-content,progress-code-token,masked-only` | 7 controls × 2 browsers | **7/7 as expected** | 0 | about 45 s |
| `p1f1-selftest-ws-oldrule` | `selftest --browsers chrome --cases whitespace`, with the old own-text rule put back for the run | 1 control | FAIL, as it must: 0 records | 0 | about 10 s |
| `p1f1-fast-1` | `fast --a oracle --b dist` (every kept route) | 496 | PASS: 0 unregistered | 0 | 189 s |
| `p1f1-fast-oldfooter` | `fast --a oracle --b dist:<scratch copy with the old footer> --routes /docs,/does-not-exist,/docs/forms/input` | 40 | FAIL, as it must: 20 unregistered `text` records, one per 1300 cell, on the footer's second section | 0 | 19 s |
| `p1f1-bh-new-dist-1`, `p1f1-bh-new-oracle-1` | `behavior --checks` the new and changed checks, both targets | 42 each | dist **42 PASS**; oracle **40 PASS, 2 XFAIL** (`demo-offscreen`) | 0 | 91 s, 90 s |
| `p1f1-bh-mut-1` | the same checks against a scratch copy of `dist/` with the review's planted bugs and two more | 38 | FAIL, as it must: 35 FAIL; the 3 PASSes are Firefox's keyboard checks (above) | 0 | 92 s |
| `p1f1-gate-pages-full-1` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2) | 1,488 (978,384 elements; 4 chunks of 372) | **PASS: 0 unregistered**; 69,924 registered: `dropped-route` 68,412 (27 entries), `oracle-bug` 1,488, `asset-path` 24; 0 cross-origin loads from `dist`, 0 reloads, 0 alignment fallbacks; `value_rules` lists the two collection rules | **0** | 440 s |
| `p1f1-gate-bh-dist-1` | `behavior --target dist --browsers chrome,firefox` | 166 (59 checks, 9 groups) | **PASS: 166 PASS** | 0 | 350 s |
| `p1f1-gate-bh-oracle-1` | `behavior --target oracle --browsers chrome,firefox` | 166 | **PASS: 144 PASS, 22 XFAIL** (the ten oracle-bug checks, `color-scheme-flash` on two routes, each at its named assertion in both browsers) | 0 | 338 s |
| `p1f1-gate-selftest-cf-1` | `selftest --browsers chrome,firefox` | 35 controls × 2 browsers | **35/35 as expected** | 0 | 213 s |
| `p1f1-gate-static-1` | `static_checks.py --phase 1` | 15 criteria | **3, 4, 5, 6 and 12 PASS**; 8, 9 and 14 FAIL (later phases, as at the gate; 9 now reports 1,208 html-validate errors, 54 more: `no-inline-style` on each page's `<body style="min-height:100vh">`); 6 lists the six Pages-inherent paths as notes | — | 10 s |
| — | `registry`, before and after | 30 entries in 10 files | valid: `asset-path` 1, `browser-limit` 1, `dropped-route` 27, `oracle-bug` 1 | — | 2 s |

In the gate run every one of the 29 Phase 1 entries registered records (the only unused one is
`safari-no-media-dark`), and the summary flags one entry `BROAD`, as before:
`p1-shell-footer-dropped-links-current-color`, 102 records in each `/docs` cell (the six footer links
times 17 color longhands; Known Phase 1 deviations has their accessibility cost). The new
`p1-shell-404-footer-track` registered one record in each of the 24 404 cells.

**Phase 1 gate status after round 1.** Met in Chrome and Firefox, as before, now with the rendered
whitespace compared: criterion 2 with zero unregistered differences over the full matrix, the
behavior suite (59 checks) passing against `dist` and holding against the oracle, and criteria 3, 4,
5, 6 and 12 passing. Phase 0's Safari steps below are still open.

### Phase 1 gate after fix round 1 (2026-10-31, evening)

The whole gate again, from 17:16 to 17:37, on the same rig (Chrome Beta 158.0.8127.2, Firefox 160.0,
Selenium 4.52.0, Node 24.22.0, the repository's wrangler 4.156.0, no `FEMTO_WRANGLER`), the oracle at
`remix-final`. `dist/` was removed and rebuilt with `npm run build` first (186 files). A fingerprint
of every gate input (`site/`, `build.mjs`, `vendor.mjs`, `package.json`, `package-lock.json`,
`eslint.config.js`, `tests/divergences/`, `tests/harness/`, `tests/behavior/`, `tests/fixtures/`,
`run.py`, `static_checks.py`, `oracle-routes.json`) and of `dist/` was taken after the build, after
the pages run, before and after the static checks: the same four times, so nothing changed between
the build and the last run, and the static checks' two rebuilds left `dist/` as it was. No run had a
harness error, so the harness was not changed. Step log: `tests/results/p1g2-gate.log`.

| Run id | Command | Cells or runs | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p1g2-pages-full-1` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2) | 1,488 (744 per browser; 978,384 elements; 4 chunks of 372) | **PASS: 0 unregistered** (0 cells); 69,924 registered: `dropped-route` 68,412 (27 entries), `oracle-bug` 1,488 (1, `og:url`), `asset-path` 24 (1); by kind style 49,728, attribute 10,356, structure 8,352, head 1,488; 0 cross-origin loads from `dist`, 0 reloads, 0 alignment fallbacks, 0 skipped checks | **0** | 338 s |
| `p1g2-bh-dist-1` | `behavior --target dist --browsers chrome,firefox` | 166 (59 checks, 9 groups) | **PASS: 166 PASS**, 0 FAIL, 0 XFAIL, 0 XPASS, 0 ERROR | 0 | 348 s |
| `p1g2-bh-oracle-1` | `behavior --target oracle --browsers chrome,firefox` | 166 | **PASS: 144 PASS, 22 XFAIL** (the ten oracle-bug checks, `color-scheme-flash` on two routes, each at its named assertion in both browsers), 0 FAIL, 0 XPASS, 0 ERROR | 0 | 337 s |
| `p1g2-selftest-cf-1` | `selftest --browsers chrome,firefox` | 35 controls × 2 browsers | **35/35 as expected** | 0 | 207 s |
| `p1g2-static-1` | `static_checks.py --phase 1` | 15 criteria | **3, 4, 5, 6 and 12 PASS**; 8, 9 and 14 FAIL (later phases' criteria, as at the gate); 1, 2, 7, 10, 11, 13 and 15 NOT-YET. The output equals `p1f1-gate-static-1`'s line for line but for ports and build timings | — | 10 s |
| — | `registry`, before and after | 30 entries in 10 files | valid: `asset-path` 1, `browser-limit` 1, `dropped-route` 27, `oracle-bug` 1 | — | 2 s |

As in round 1, every one of the 29 Phase 1 entries registered records, the only unused entry is
`safari-no-media-dark` (no Safari cell), and the one entry flagged `BROAD` is
`p1-shell-footer-dropped-links-current-color` (102 records in each `/docs` cell). Pixels (not
gating): 1,464 of the 1,488 cells differ by more than 8/255, every route but `/demo`, as before. The
oracle's `/docs/progress` held its JSON-LD twice in 24 side A documents (Collection).

**Phase 1 gate status after fix round 1.** Met in Chrome and Firefox: criterion 2 with zero
unregistered differences over the full matrix, the behavior suite passing against `dist` and holding
against the oracle, the selftest proving detection, and criteria 3, 4, 5 (except
`site/assets/legacy/`), 6 (Phases 1 and 2 column) and 12 passing. Criterion 4 is read on the files
that would be tracked after committing the working tree; the literal `git ls-files` needs the
Phase 1 commit (plan-6). Phase 0's Safari steps below are still open.

### Phase 1 fixes, round 2 (2026-10-31, evening)

The adversarial review of round 1 left one finding (adv-p1f1-1, minor), confirmed first: round 1's
own-text rule found leading, trailing and inner whitespace with JavaScript's `\s`, which matches
U+00A0, so a visible extra no-break space gave no `text` record. Replayed on the review's scratch
copy of `dist/` (`/docs/forms/select`'s footer as `Code&nbsp;` plus a literal U+00A0 before
`licensed`, two no-break spaces), the review's run `adv-p1f1-verify-cx` had no record in Chrome and
only two indirect style records on the `<p>` in Firefox.

What changed: `ownText()` in `harness/differ.js` reads only CSS's document white space (space, tab,
line feed, carriage return) as whitespace, so U+00A0, U+FEFF and the other Unicode spaces are text
(Collection; `value_rules` says so). Form feed is left out on purpose, though the review suggested
it: CSS Text 3 renders it as a visible glyph. The class and `rel` token lists that key the
alignment and the head records now split on ASCII whitespace, as the DOM does, not on `\s`. New
control `whitespace-nbsp`. No page or registry entry changed: the oracle's and `dist/`'s 54 kept
pages hold no Unicode space but U+00A0 (written `&nbsp;`; no form feed or carriage return either),
and the full run below has the same 69,924 registered records as `p1g2-pages-full-1`.

| Run id | Command | Cells or runs | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p1f2-selftest-nbsp-1` | `selftest --cases whitespace-nbsp,whitespace,whitespace-collapsed,text,self,changed-tag-content,progress-code-token,masked-only` | 8 controls × 2 browsers | **8/8 as expected**; `whitespace-nbsp`: one `text` record per cell, side B `"Lead\u00a0 text with\u00a0\u00a0."` | 0 | about 50 s |
| `p1f2-selftest-nbsp-oldrule` | `selftest --cases whitespace-nbsp`, with round 1's `\s` put back for the run | 1 control × 2 browsers | FAIL, as it must: 0 records in both browsers | 0 | about 6 s |
| `p1f2-verify-cx-1` | `pages --a oracle --b dist:tests/results/adv-p1f1-verify/dist-cx --routes /docs/forms/input,/docs/forms/select --browsers chrome,firefox --schemes light --widths 1300` (the review's counter-example) | 4 | FAIL, as it must: `/docs/forms/select` has the `text` record `'Code licensed , docs .' -> 'Code\xa0\xa0licensed , docs .'` on the footer's `<p>` in both browsers (Firefox adds its two `perspective-origin` and `transform-origin` records); `/docs/forms/input` 0 | 0 | 8 s |
| `p1f2-pages-full-1` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2), after `rm -rf dist && npm run build` (186 files, `dist/` byte-identical to before) | 1,488 (978,384 elements) | **PASS: 0 unregistered**; 69,924 registered, by kind and entry as in `p1g2-pages-full-1`; 0 cross-origin loads from `dist`, 0 reloads, 0 alignment fallbacks, 0 skipped checks | **0** | 423 s |
| `p1f2-selftest-cf-2` | `selftest --browsers chrome,firefox`, on the final harness files | 36 controls × 2 browsers | **36/36 as expected** | 0 | 219 s |
| `p1f2-static-1` | `static_checks.py --phase 1` | 15 criteria | 3, 4, 5, 6 and 12 PASS; 8, 9 and 14 FAIL (later phases); 7 NOT-YET. The output equals `p1g2-static-1`'s line for line but for one port and build timings | — | 11 s |
| — | `registry` | 30 entries in 10 files | valid, unchanged | — | 2 s |

(`p1f2-selftest-cf-1`, 36/36 as expected, ran while a comment in `differ.js` was edited, so
`p1f2-selftest-cf-2` repeats it on the final files.) Step log: `tests/results/p1f2-rerun.log`; its
`exit` figures are `date`'s status, not the commands' (its last line says so), so the results above
are read from each run's own log and `result.json`. After `p1f2-selftest-cf-2`, `negative.py`'s
expected string was respelled with `\u00a0` escapes in place of literal no-break spaces: the same
syntax tree (checked against the hash in `tests/results/p1f2-selftest-cf-2.inputs`), and
`p1f2-selftest-nbsp-2` reran that control on it, 1/1 as expected in both browsers.

**Phase 1 gate status after round 2.** Unchanged: met in Chrome and Firefox, now with no-break
spaces compared as text. The behavior suite was not rerun: it does not load `differ.js`, and nothing
it runs changed. Phase 0's Safari steps below are still open.

### Phase 1 gate after fix round 2 (2026-10-31, evening)

The whole gate again on round 2's final files, from 18:15:02 to 18:37:55, run serially by one step
script on the same rig (Chrome Beta 158.0.8127.2 with chromedriver 158.0.8127.2, Firefox 160.0 with
geckodriver 0.37.1, Selenium 4.52.0, Node 24.22.0, the repository's wrangler 4.156.0, no
`FEMTO_WRANGLER`), the oracle at `remix-final`, HEAD 0799c81 with the Phase 1 working tree
uncommitted. `dist/` was removed and rebuilt with `npm run build` first (186 files). A fingerprint
(the sha256 of every file's path and content, sorted by path) of the gate inputs (`site/`,
`build.mjs`, `vendor.mjs`, `package.json`, `package-lock.json`, `eslint.config.js`,
`tests/divergences/`, `tests/harness/`, `tests/behavior/`, `tests/fixtures/`, `run.py`,
`static_checks.py`, `oracle-routes.json`) and of `dist/` was taken after the build, after the pages
run, before and after the static checks: inputs `8a76b109b2d93806` and `dist/` `2e37847cc42d733d`
all four times, and `dist/` equals the tree `p1f2-rerun.log` fingerprinted before and after round
2's rebuild. No input changed after round 2's last run (`p1f2-selftest-nbsp-2`, 18:01) and none during this block. No run had
a harness error, so the harness was not changed. Step log, with each command's own exit status:
`tests/results/p1g3-gate.log`; each step's output is `tests/results/p1g3-<step>.out`.

| Run id | Command | Cells or runs | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| — | `registry`, before the runs | 30 entries in 10 files | valid: `asset-path` 1, `browser-limit` 1, `dropped-route` 27, `oracle-bug` 1 | — | 2 s |
| `p1g3-pages-full-1` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2) | 1,488 (744 per browser; 978,384 elements; 4 chunks of 372) | **PASS: 0 unregistered** (0 cells, so no unregistered record group); 69,924 registered: `dropped-route` 68,412 (27 entries), `oracle-bug` 1,488 (1, `og:url`), `asset-path` 24 (1); by kind style 49,728, attribute 10,356, structure 8,352, head 1,488; 0 cross-origin loads from `dist`, 0 loads from the deployed origin, 0 reloads, 0 alignment fallbacks, 0 skipped checks | **0** | 444 s (446 s with start-up) |
| `p1g3-bh-dist-1` | `behavior --target dist --browsers chrome,firefox` | 166 (59 checks, all 9 groups; 83 per browser) | **PASS: 166 PASS**, 0 FAIL, 0 XFAIL, 0 XPASS, 0 ERROR | 0 | 349 s |
| `p1g3-bh-oracle-1` | `behavior --target oracle --browsers chrome,firefox` | 166 | **PASS: 144 PASS, 22 XFAIL** (the ten oracle-bug checks, `color-scheme-flash` on two routes, each at its named assertion in both browsers), 0 FAIL, 0 XPASS, 0 ERROR | 0 | 339 s |
| `p1g3-selftest-cf-1` | `selftest --browsers chrome,firefox` | 36 controls × 2 browsers | **36/36 as expected** | 0 | 224 s |
| `p1g3-static-1` | `static_checks.py --phase 1` | 15 criteria | **3, 4, 5, 6 and 12 PASS**; 8, 9 and 14 FAIL (later phases' criteria, as at every Phase 1 gate); 1, 2, 7, 10, 11, 13 and 15 NOT-YET. The output equals `p1f2-static-1`'s line for line but for one port and one build timing | — | 11 s |
| — | `registry`, after the runs | 30 entries in 10 files | valid, unchanged | — | 2 s |

As in every Phase 1 gate run, each of the 29 Phase 1 entries registered records, the only unused
entry is `safari-no-media-dark` (no Safari cell), and the one entry flagged `BROAD` is
`p1-shell-footer-dropped-links-current-color` (102 records in each `/docs` cell; Known Phase 1
deviations). The registered records equal `p1g2-pages-full-1`'s in total, by kind and by category.
Pixels (not gating): 1,464 of the 1,488 cells differ by more than 8/255 (1,469 by any amount), every
cell of every route but `/demo`, as before. The oracle's `/docs/progress` held its JSON-LD twice in
24 side A documents (Collection). From about 18:35 a harness run of another session (`run.py compare`,
femto's mode) held harness slots during `p1g3-selftest-cf-1`; the machine-wide slots kept the two
apart, and every control passed.

**Phase 1 gate status after fix round 2.** Met in Chrome and Firefox: criterion 2 with zero
unregistered differences over the full Chrome and Firefox matrix, the behavior suite passing against
`dist` and holding against the oracle (every group), the selftest proving detection, the registry
valid, and criteria 3, 4, 5 (except `site/assets/legacy/`), 6 (Phases 1 and 2 column) and 12
passing. Criterion 4 is read on the files that would be tracked after committing the working tree;
the literal `git ls-files` needs the Phase 1 commit (plan-6). Phase 0's Safari steps below are still
open.

### Safari passes and Decision 16 (2026-11-01, morning)

Phase 0's open Safari steps, run on HEAD a393112 (femto 7bcd5758) with the working tree's changes
below, on the same rig (Safari 27.2, safaridriver 22625.2.8.11.9). macOS was on its Auto
appearance, Dark until sunrise and Light after; no setting was changed. "Locked" means `lsappinfo
front` reported `loginwindow`.

| Run id | Command | Cells or runs | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p0-self-safari-dark-cssvars` | `self --full --browsers safari --routes /docs/css-variables` (dark OS, unlocked) | 12 (6 run, 6 the registered skip `media:light`; 31,056 elements) | **PASS: 0 differences** | 0 | 1,219 s |
| `p0-rig-safari` | `rig --browsers safari` (dark OS; the screen had relocked) | 1 session | widths, pseudo-elements and the dark scheme as expected; the input checks did not run (locked screen) | — | about 1 min |
| `p0-selftest-safari-light` | `selftest --browsers safari` (light OS, locked) | 36 controls | **35/36**: `cross-origin-closed-shadow` FAIL (no cross-origin load seen; the host's only-b record as expected) | 0 | 6.4 min |
| `p0-self-safari-light-locked` | `self --full --browsers safari --routes` every kept route but `/docs/css-variables` (light OS, locked) | 732 (414 run, 318 the registered skip `media:dark`; 262,026 elements) | **FAIL: 36 unregistered**, all `transform` on the oracle's toggle icon (`svg.icon-theme-toggle g > circle, path`) in 18 theme-dark cells, read mid-transition | 6 (`/docs/forms/input` theme-dark: "2 animations finished … after the styles were read") | 609 s |
| `p0-selftest-safari-light-shadow-recheck` | `selftest --browsers safari --cases cross-origin-closed-shadow,cross-origin-worker` | 2 controls | closed-shadow FAIL again; the worker's CSP report arrives (PASS) | 0 | 18 s |
| `p0-self-safari-light-themedark-recheck` | `self --full --browsers safari --routes /docs,/docs/button,/docs/forms/input,/docs/table,/docs/typography --schemes theme-dark` | 30 | FAIL: 20 unregistered in 10 cells, the same icon records: reproduces | 3 | 33 s |
| `owner-toggle-probe`, `-2` | `pages --a oracle --b dist` on `/`, `/docs/color-schemes` (and `/docs/typography`, a 404 in `-2`) at 375 and 1300, light and theme-dark, all three browsers | 24, 48 | with Decision 16's emoji in a free-sized box the nav, its list, item and link widths shift 2.5 to 5 px; with the SVG's box kept (`-2`), the only icon records are the tag change and the SVG's clipPath and g, in every browser | 0 | 45 s, 87 s |
| `owner-toggle-bh-dist` | `behavior --target dist --groups shell,getting-started` | 110 | **110 PASS** | 0 | 118 s |
| `owner-toggle-bh-oracle` | `behavior --target oracle --expect-oracle-bugs --groups shell,getting-started` | 110 | **102 PASS, 8 XFAIL** (the known oracle bugs) | 0 | 119 s |
| `owner-gate-pages-full` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2) | 1,488 (970,944 elements) | **PASS: 0 unregistered**; 74,388 registered, `owner-theme-toggle-icon` in 1,464 cells (every page with a header) and `owner-theme-toggle-svg-parts` with it | 0 | 332 s |
| `owner-selftest-cf` | `selftest --browsers chrome,firefox` | 36 controls × 2 | **36/36** | 0 | 3.6 min |
| `owner-selftest-safari-light` | `selftest --browsers safari` (light OS, locked) | 36 controls | **35/36**: `cross-origin-closed-shadow` FAIL, as above | 0 | 6.4 min |
| `owner-self-safari-light` | as `p0-self-safari-light-locked` | 732 (414 run, 318 skipped; 262,026 elements) | **PASS: 0 differences**; the freeze counted 8 late masked animations, all on `/docs/forms/input` | **0** | 1,072 s |
| — | `static_checks.py --phase 1` | 15 criteria | 3, 4, 5, 6, 11 and 12 PASS (11 now has site CSS to lint); 8, 9 and 14 FAIL (later phases' criteria); the rest NOT-YET | — | 11 s |
| — | `registry` | 32 entries in 11 files | valid: `asset-path` 1, `browser-limit` 1, `dropped-route` 27, `oracle-bug` 1, `owner-change` 2 | — | 2 s |

**The toggle icon.** The oracle sets its scheme in a React effect after hydration, so on a light OS
the theme-dark leg adds `moon` to the toggle icon then, and its circle and rays scale over 260 ms.
In Safari on a locked screen that transition can start after the collect's freezes, and the values
were read part way (scale 1.29 to 1.39 of 1.4). The owner chose to replace the icon (Owner
decisions, 8; PLAN.md Decision 16): `site/partials/nav-icons.html` and
`site/docs/sections/color-schemes.html` hold an empty `span.icon-theme-toggle` (`aria-hidden`),
`site/assets/css/common.css` draws ☀️ or 🌙 in it as a transparent glyph with a `--femto-color`
shadow in the SVG's own box, and `site.js` and `docs.js` toggle `moon` with `classList`. The
harness masks the oracle icon's animated longhands (Masks, `oracle-theme-toggle`), and the freeze
counts an animation a mask fully covers apart (Collection), so the oracle's self comparison no
longer depends on when Safari starts that transition. The behavior checks found the icon by its
class, not its tag, so they held for both. Since PLAN.md Decision 18 (2026-11-06) the icon is a
`span[role=img]` holding the emoji, which `site.js` and `docs.js` rewrite, and the checks read its
emoji and label. `eslint.config.js` allows femto's tokens as unknown
variables, as femto's own config does.

**The closed shadow root control in Safari.** `cross-origin-closed-shadow` failed in both full
Safari selftests and the recheck: Safari 27.2 sent the CSP report of a dedicated worker's
cross-origin `fetch()` (`cross-origin-worker` passes) but none, within the cell, for the stylesheet
that a frame inside a closed shadow root loads (Known limits, Same-origin loads: Safari's reports
were not probed before). Whether the report is never sent or only late is not established.

**Phase 0's gate in Safari after this block.** Light OS: criterion 1 passes over the 53 routes
(`owner-self-safari-light`); dark OS: `p0r2-self-safari-dark` and `p0-self-safari-dark-cssvars`
(an earlier differ; the dark pass with today's harness needs a dark evening). Still open: the 6 light
`/docs/css-variables` cells, `rig`'s input checks and the spike, all of which need an unlocked screen,
and the closed-shadow control above.

### The owner's Safari script and the banner mask (2026-11-01, late morning)

The owner ran `tests/owner-safari.sh` (Owner's Safari steps) on HEAD 161053b with the spike's
`test_spike.py` change uncommitted, Safari 27.2 on an unlocked screen, from 10:50 to 11:37. The
script set Light, then Dark, and put Light back.

| Run id | Command | Cells or runs | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p0-spike-safari.txt` | `test_spike.py 8794 safari --probes` (light OS) | 13 checks and the probes | **11/13**: `location.reload()` returns to the `#hash` heading, and the Quick start click puts the heading at its 80 px scroll padding, so y 30, against the check's cutoff of below 30 (`docs/research/05-spike.md`, Results) | — | 68 s |
| `p0-rig-safari-unlocked` | `rig --browsers safari` (light OS) | 1 session | widths, pseudo-elements, the light and theme-dark legs, and the input checks (hover, active, focus-visible) all as expected | — | about 5 s |
| `p0-self-safari-light-cssvars` | `self --full --browsers safari --routes /docs/css-variables` (light OS) | 12 (6 run, 6 the registered skip `media:dark`; 31,056 elements) | **PASS: 0 differences** | 0 | 1,178 s |
| `p0-self-safari-dark` | `self --full --browsers safari` (dark OS) | 744 (420 run, 324 the registered skip `media:light`; 293,082 elements) | **FAIL: 16 unregistered in 1 cell**, `/docs/link` dark 375: the color longhands of the maintenance banner's link | 0 | 1,555 s |
| `p0-selftest-safari-dark` | `selftest --browsers safari --cases self,dark-only,theme-dark-only` (dark OS) | 3 controls | **3/3** | 0 | about 30 s |
| `owner-mask-self-cf` | `self --full --browsers chrome,firefox` (criterion 1, with the banner mask) | 1,488 (1,015,632 elements) | **PASS: 0 differences**; `oracle-maintenance-notice` covered 2,928 links, both sides of every cell but `/demo`'s | 0 | 419 s |
| `owner-mask-pages-cf` | `pages --a oracle --b dist --full --browsers chrome,firefox` (criterion 2) | 1,488 (970,944 elements) | **PASS: 0 unregistered**; 74,388 registered, as in `owner-gate-pages-full`; the mask covered side A's 1,464 links, whose banner side B does not have | 0 | 328 s |
| — | `static_checks.py --phase 1`; `registry` | 15 criteria; 32 entries | as in the block above | — | — |
| `p0-spike-safari-2.txt` | `tests/owner-safari.sh spike`: `test_spike.py 8794 safari --probes` with the revised reload and Quick start checks (unlocked, 2026-11-02 16:45) | 13 checks and the probes | **13/13**; positions and probes as in the first run | — | 67 s |
| `p0-self-safari-dark-masked` | `tests/owner-safari.sh dark`: `self --full --browsers safari` (dark OS, unlocked, 2026-11-02 15:41 to 16:07) | 744 (420 run, 324 the registered skip `media:light`; 293,082 elements) | **PASS: 0 differences**; `oracle-maintenance-notice` covered 828 links (both sides of the 414 run cells with a banner); no late masked animation | 0 | 1,548 s |

**The banner link.** The oracle's maintenance banner takes the inverse of the page's theme, and React
sets its `data-theme` in the effect after hydration that also sets the toggle's `moon` (PageContext).
On a dark page it flips from dark to light, and the link's `color` and `text-decoration-color`
then transition over 0.2 s. On side A the freeze finished the two transitions; on side B it saw
none, and the link was read part way from the dark theme's secondary color to the light one's (side
A `rgb(93, 107, 137)`, side B `rgb(135, 145, 165)`; `text-decoration-color` the same at alpha 0.5).
The 16 records are `color` and the longhands that follow `currentColor`. The banner's own
`data-theme` matched, so the flip had happened on both sides. The site drops the banner
(PLAN.md Decision 5), so the owner chose to mask its link's colors (Masks,
`oracle-maintenance-notice`) rather than make the oracle's readiness wait for the theme effect. The
other elements that effect changes (the homepage comparison's code blocks, the `/docs/table` header)
have not differed in any pass.

**Phase 0's gate in Safari after this block.** Light OS: criterion 1 passes on every kept route
(`owner-self-safari-light`, `p0-self-safari-light-cssvars`), and `rig`'s input checks pass. Dark OS:
criterion 1 passes on every kept route with the mask (`p0-self-safari-dark-masked`), and the dark
selftest controls pass. The owner accepted Safari's reload to the `#hash` heading and the spike's
reload and Quick start checks were revised (2026-11-02; `docs/research/05-spike.md`, Verdict), and
the spike passes all 13 in Chrome, Firefox and Safari (`p0-spike-safari-2.txt`). Both parts of
PLAN's Phase 0 gate in Safari pass. The closed-shadow control is still a known Safari limit (Safari
passes and Decision 16, above).

### Phase 2: styles (2026-11-02)

PLAN's Phase 2: the site leaves the frozen `site/assets/legacy/` CSS for vendored femto (default
build plus `options/responsive-spacings.css`) and five site files written from the compiled output
(`fonts.css` 147 lines, `common.css` 562, `code.css` 172, `docs.css` 999, `landing.css` 957).
`femto.colors.min.css` replaces `color-utilities.css` on `/docs/colors` and `color-picker.css` on
`/docs/version-picker`, with `css/themes/<color>.css` after it on each color route. Its gate:
criterion 2 (`styles --full` against `static-multipage`, Chrome and Firefox), with criteria 4, 11 and
12. Rig as in the Safari passes above (Chrome Beta 158.0.8127.2, Firefox 160.0, Selenium 4.52.0,
Node 24.22.0, wrangler 4.156.0).

**How it ran.** One workflow (`wf_f6ca1e2c-b4e`, 19 agents, about 4 h 15 min). The harness agent
built the `styles` mode while the common agent switched the pages to femto. A registry agent ported
femto's `femto-divergence` entries. Then the docs and landing agents rewrote their files while
common fixed what traced to its files. Three reviewers (parity, CSS, harness) ran twice, each round
followed by fixes from the owners of the files. Round 1 had 19 findings (6 high, 9 medium, 4 low),
round 2 had 16. After it the lead:
- fixed `picker.js`, which no agent owned: its in-place theme switch still looked for
  `color-picker.css` and `custom-themes/`, so a swatch click threw (`p2-lead-picker-fix`:
  `picker-swatch` and `picker-logo` PASS in Chrome and Firefox);
- added the harness fixer's two drafted swatch entries (pinned, `/docs/colors`) and merged the two
  shade entries into one closed set;
- added the minifier value rule (owner decision 11, Diff rule) and its three controls, and wrote
  the site's own variables normally again;
- made the body rows `auto 1fr auto` (`p2-common-body-rows`), the fix Phase 1's registry left to
  Phase 2: on the 404 page at 800 px main's track is 269.7 px and the footer's 448.3 px, the
  oracle's footer track (`p2-lead-body-rows-probe`).

**Against PLAN's letter.**
- The tag `static-multipage` names `9383e6b` ("Pass Phase 0 Safari Gate"), not Phase 1's `de65ccf`:
  the later commit has Decision 16's emoji toggle, so the gate measures only the CSS change.
- The oracle's `html { scroll-behavior: smooth }` is gone now rather than in Phase 3: criterion 11
  allows it only under Decision 10's class, which Phase 3 adds (`p2-common-html-smooth-scroll`,
  `merge-layout`).
- The gate's runs used femto 7bcd5758; the commit vendors d4f8d1fd (owner decision 2). Its only
  change to the vendored files is a comment in `css/forms/input-date.css`, a file no page links,
  and `dist/` is unchanged, so the runs stand. Criterion 12 and the build were checked again on
  d4f8d1fd.

**What the harness gained** (Tokens and states, Divergence registry and Diff rule above): the
`styles` mode with the tag built by `tagbuild.py`, femto's token comparison (`token`, `token-raw`,
`surface-missing`, `surface-added`), interactive states from `states.json` (47 targets, 105 target
states, 22 routes), inherited records folded into their parent's registered record, pinned entries
and layout consequences, union limits for every token kind, an instant-scroll override while states
replay, and the minifier rule. The selftest went from 36 controls to 61.

**Registry.** 77 entries in 24 files: `femto-divergence` 40 (in the ten `femto-*.json` files),
`dropped-route` 30, `merge-layout` 2, `owner-change` 2, and `asset-path`, `browser-limit` and
`oracle-bug` 1 each. A styles comparison applies only the entries that name it (and skipped checks),
so Phase 1's pages-mode entries take no part; in the final gate all 43 entries that apply registered
records. Two femto entries apply to nothing here: `femto-modal-dialog-backdrop-tint` (the harness
never opens the modal) and `femto-nav-dropdown-block-details-safari-insets` (Safari only). The
summary flags 10 entries `BROAD`, the most 704 records in one cell
(`femto-dropdown-lone-label-fills-row`, the lone labels of the dropdown menus times their geometry
longhands). Each is a femto entry's own selector, scoped to femto's elements and properties; round 2's
parity reviewer compared the ported entries field by field with femto's.

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p2-gate-styles-full-1` | `styles --full --browsers chrome,firefox` (criterion 2), before the minifier rule | 1,488 (970,944 elements) | FAIL: **675,780 unregistered**, all the minifier's spellings (444,288 `token-raw`, 215,184 `outline-width`, 16,308 background position) | 0 | 551 s |
| `p2-gate-styles-full-2` | the same, with the minifier rule | 1,488 | **PASS: 0 unregistered**; 2,256,712 registered, 804,336 inherited | 0 | 553 s |
| `p2-gate-selftest-2` | `selftest --browsers chrome,firefox` | 61 controls × 2 browsers | **61/61** | 0 | about 6 min |
| `p2-gate-styles-full-3` | the same as `-2`, after the body rows change (final) | 1,488 (970,944 elements) | **PASS: 0 unregistered**; 2,258,364 registered (`p2-common-body-rows` 1,584 in every cell), 804,336 inherited; 0 cross-origin loads | 0 | 550 s |
| `p2-gate-selftest-3` | `selftest --browsers chrome,firefox` (final) | 61 controls × 2 browsers | **61/61** | 0 | about 6 min |
| — | `registry`; `npm run lint`; `static_checks.py --phase 2` | — | valid; exit 0; **4, 11 and 12 PASS** (3, 5 and 6 too); 8, 9 and 14 FAIL, later phases' criteria as in Phase 1 | — | — |

The gate doesn't include Safari. The `styles` mode needs an unlocked screen with the automation
window in front for its state replays, so a Safari styles pass is the owner's, as for Phase 0:
`tests/owner-safari.sh styles` (Owner's Safari steps).

**Safari (2026-11-03).** The owner ran `tests/owner-safari.sh styles` on Safari 27.2. Both runs
failed, almost entirely on a harness bug:

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p2-styles-safari-light` | `styles --full --browsers safari`, macOS Light | 744 (420 run, 324 skipped as `media:dark`) | FAIL: **786,021 unregistered in 63 cells** | 0 | 1,936 s |
| `p2-styles-safari-dark` | the same, macOS Dark | 744 (420 run, 324 skipped as `media:light`) | FAIL: **724,535 unregistered in 41 cells** | 0 | 1,922 s |

What the records were:
1. **Speculative loading** (Rig notes, Safari): over 99% of the records, in 23 cells in Light and 14
   in Dark. In those cells:
   - the request counts were off, for example 15 for side A and 8 for side B where the route's
     usual is 10 and 13;
   - on `/`, side A's server answered side B's `fonts.css`, `code.css` and `landing.css` with 404s;
   - a side whose own stylesheets had been served from the other side's 404s rendered without them.

   Chrome and Firefox had no failed subresource request in any of the gate's 1,488 cells.
2. **The docs menu's `--max-height`**: 29 cells in Light and 17 in Dark. Where nothing was
   cross-loaded it was 1 to 7 records per cell. `docs.js` measures the nav once, when the module
   runs (and again on resize). In Safari the measure sometimes saw an earlier layout of the page,
   on either side, in cells whose request logs are normal. For example, it measured 60.8 px where
   the other side measured 662.2 px at 1600 px. Both sides run the same script, so it isn't the CSS
   change. Whether it is the harness's timing or a Safari bug of the site's own script is open
   until the rerun.
3. **The `Login` text field under `:focus` at 375 px**: 277 px on one side and 250 px on the other,
   either side, on `/docs/color-schemes`, `/docs/version-picker/jade` and `/docs/forms`. That is 8
   cells in Light and 7 in Dark. The 27 px is the size of Safari's AutoFill button, which Safari
   shows on a field it takes for a login. This is not confirmed.
4. **`/docs/colors` at 800 and 1100 px, OS-scheme legs only**: the swatch grid's tracks are 1/64 px
   apart, which is WebKit's layout unit. For example, `55.609375px` against `55.59375px`. That is
   1,898 and 650 records, the same in both runs. It is the one real difference between the two
   stylesheets: invisible, and absent in Chrome and Firefox.
5. **A footer link's border colors under `:focus-visible`**: 1 to 2 of 255, in one cell.

**The fix** (The proxy; How one comparison works, step 4):
- Each Safari document load carries `harness-load=<tag>.<attempt>`. The proxy removes it before
  forwarding and logging.
- Both readiness hooks end with the stylesheet check, which reloads a side whose own stylesheet
  didn't load (control `stylesheet-404`).

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p2-selftest-sheets` | `selftest --browsers chrome,firefox --cases stylesheet-404,status-404,self` | 3 controls × 2 browsers | **3/3**; Chrome and Firefox both report `has no rules` | 0 | 21 s |
| — | `styles --browsers chrome` on `/`, `/docs`, `/docs/colors` and `/docs/version-picker/jade` at 375 and 1300 px, with `harness-load` turned on for Chrome for this run only | 28 | **PASS: 0 unregistered**; the cells' paths are the bare routes, no reloads, and neither server's log has the parameter (run deleted afterwards) | 0 | about 1 min |
| `p2-sfix-selftest-cf` | `selftest --browsers chrome,firefox` | 62 controls × 2 browsers | **62/62** | 0 | 376 s |
| `p2-sfix-styles-full-cf` | `styles --full --browsers chrome,firefox` | 1,488 (970,944 elements) | **PASS: 0 unregistered**; 2,258,364 registered and 804,336 inherited, as in `p2-gate-styles-full-3`; 0 reloads, 0 cross-origin loads | 0 | 546 s |

The owner then reran `tests/owner-safari.sh styles` with the fix (2026-11-03, afternoon):

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p2-styles-safari-light-2` | `styles --full --browsers safari`, macOS Light | 744 (420 run, 324 skipped as `media:dark`) | FAIL: **3,013 unregistered in 26 cells** | 0 | 1,935 s |
| `p2-styles-safari-dark-2` | the same, macOS Dark | 744 (420 run, 324 skipped as `media:light`) | FAIL: **2,638 unregistered in 20 cells** | 0 | 1,910 s |

Nothing was cross-loaded: every cell's request counts are its route's usual ones, with no failed
request, no reload and no cross-origin load. Item 5 did not recur. Three kinds of record are left,
all Safari's:
- **The docs menu's `--max-height`** (item 2): 13 cells in Light and 12 in Dark, 1 or 7 records
  each, or 184 on `/docs/button` at 1600 px, where the focus-visible replays add the nav's height
  and origins. At each width the value is one of two, the same on either side. For example,
  662.1875 px or 60.78125 px at 1600, and 688.75 or 140.015625 at 1300. So `docs.js` sometimes
  measures the nav in a layout where it sits several hundred pixels lower, most likely before the
  page's stylesheets apply. Chrome and Firefox never do. This is the site's script, not the
  harness, and Safari visitors would get it too. The behavior check `side-menu-max-height` has
  not run in Safari.
- **AutoFill** (item 3): 11 cells in Light and 6 in Dark, 4 records each. Under `:focus`, the
  width of the `Login` field is always 27 px more on one side, at every width:
  - on `/docs/color-schemes` and `/docs/version-picker/jade`;
  - also the `Email` field on `/docs/forms/input` and a field on `/docs/forms`.
- **`/docs/colors`' grid tracks** (item 4): the same 1,898 and 650 records at 800 and 1100 px as in
  the first runs. They are the 20 swatch grids, plus the grid of the swatch whose states replay,
  recorded again under each of its 6 replays. The value pairs are one per property and width.

**What the owner chose** (2026-11-03): fix `docs.js` and register the rest.
- `docs.js` measures the nav again on the window's `load` (when the module runs before it), so
  `dist/` no longer depends on when Safari applies the stylesheets. Side A is the frozen tag, so its
  value still varies.
- `p2-safari.json` holds 19 entries, which bring the registry to 96 entries in 25 files. Every one
  is for Safari and styles runs only:
  - side A's `--max-height` and the nav's geometry from 1024 px (`browser-limit`);
  - its consequence on `/docs/button`'s table of contents under replayed states: the current link's
    `aria-current`, colors and weight (`browser-limit`);
  - the AutoFill button's width on a focused `input[autocomplete]` (`browser-limit`);
  - `/docs/colors`' grid tracks at 800 and 1100 px in the OS scheme's legs: one layout-consequence
    entry per width for each grid's `grid-template-columns`, and 12 pinned entries for the swatches'
    six geometry longhands (`femto-divergence`). They are pinned because the swatches are 29.3% of
    the page.
- Replayed offline against the four Safari runs, the entries match every kept record of
  `p2-styles-safari-light-2` and `-dark-2`. Only the two `/docs/colors` cells kept fewer records
  than they had (300 of 1,898 and of 650), and the rest are repeats of the same pairs. Safari itself
  has not run them yet: that is the owner's next `tests/owner-safari.sh styles`, now as
  `p2-styles-safari-light-3` and `-dark-3`.

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| — | `registry`; `npm run lint` | — | valid (96 entries in 25 files); exit 0 | — | — |
| `p2-sfix2-behavior-dist` | `behavior --target dist`, after the `docs.js` change | 166 checks (Chrome and Firefox) | **PASS: 166/166**, `side-menu-max-height` included | 0 | 346 s |
| `p2-sfix2-styles-full-cf` | `styles --full --browsers chrome,firefox`, the same `dist/` | 1,488 (970,944 elements) | **PASS: 0 unregistered**; 2,258,364 registered and 804,336 inherited, as before; 0 reloads, 0 cross-origin loads | 0 | 543 s |
| — | `static_checks.py --phase 2` | — | 3, 4, 5, 6, 11 and 12 PASS; 8, 9 and 14 FAIL, later phases' criteria, as at the gate | — | — |

### Phase 3: one page (2026-11-04)

PLAN's Phase 3: the 31 docs routes and the 19 version-picker color routes become one page,
`dist/docs.html`, with no `dist/docs/` folder; every old route answers 404. `build.mjs` assembles it
from `menu.json` (id, title, description and label) and the section files (each an `hgroup` whose
`h1` carries the id, then its content and edit link), with the generated side nav and no per-route
scaffolding. `docs.js` starts from the spike: the `#hash`, `aria-current`, the title and the open
category follow the section being read, and Decision 10's class carries smooth scrolling only for nav
clicks. `?theme=<color>` takes the theme `<link>` from the first of two inline head scripts (owner
decision 13). The TOC and the subheading anchors are gone, Decision 13's renames make every id
unique, every link into the docs is `/docs#<id>`, the palette download is a static JSON file the
build writes, the modal helper is one per dialog, and widgets attach through `data-` hooks.
`.htmlvalidate.mjs` holds criterion 9's config. Its gate: each section's subtree against its route's
`[role=document]` at `static-femto` with zero unregistered differences, criteria 5 to 9 and 15 in
Chrome and Firefox, then the owner's Safari pass. Criterion 10 moved to Phase 4 (owner decision 12).
Rig as in Phase 2, plus axe-core 4.14.0.

**How it ran.** One workflow (`wf_a2f6cb0d-bda`, 29 agents, about 4 h 30 min):
1. The harness agent built the `sections` and `a11y` modes while the core agent built the one page.
2. Sections, widgets, CSS, shell, behavior and a harness proof ran in parallel.
3. html-validate, then the registry and triage, then a fix round.
4. Three reviewers (parity, site and behavior) ran three rounds: 24, 15 and 14 findings.
   The third round's findings were left to the lead.

A follow-up workflow (`wf_5f4d42b5-c2f`, 5 agents, about 1 h 5 min) then did three things:
- moved every docs-page widget onto `data-` hooks, the picker's included, with one exact entry per
  hook;
- split the head script, with criterion 15's static check and a Firefox first-paint assertion to
  match;
- added the `modal-two-dialogs` behavior check.

Its reviewer found a flaky timing bound in that check, the picker's lookups by heading text and four
stale comments, and the owners fixed all three. Last, the lead:
- put back the three explained separators (Known Phase 1 deviations);
- hooked the header toggle (`data-scheme-toggle`), the logo (`data-site-logo`), the typing demo
  (`data-typing-demo`) and the comparison (`data-comparison`), with four `pages` entries;
- amended PLAN.md for owner decisions 12 and 13.

**Against PLAN's letter, and the lead's calls.**
- The tag `static-femto` names `7587a7e`, the head of `dev` when Phase 3 began, not `f2f2351` ("Move
  Styles To femto 3"). The later commits are Phase 2's Safari follow-ups (the docs menu's measure on
  `load`) and the README, so the gate measures only Phase 3's change.
- The content column keeps the oracle's width at every width; from 1280 px the third track stays
  empty. So the four routes that had no table of contents (rtl, link, forms/range, loading) are
  narrower at 1300 and 1600 px. Each is one section layout consequence (`p3-geometry-*`, geometry
  longhands at those two widths), and nothing else in those cells. Widening the content is a Phase 4
  layout choice.
- The explained React separators stay through Phase 3. Without them Chrome shapes two labels
  0.016 px narrower, which no category covers.
- The example-form submit guard still uses `closest("main")`. It is a rule for every form on the
  site, not a widget's markup.
- The docs shell's hooks (`main[data-docs-spy]`, `aside[data-docs-menu]`,
  `nav[data-docs-breadcrumb]`, `header[data-fixed-header]`) sit outside every compared root, so they
  have no entries. `div#content` and the side nav take no hook: `build.mjs` replaces those two tags
  by their exact text.
- Phase 4 accessibility items found here, beyond Accessibility's five rules:
  - At 375 px, Tab can leave the open off-canvas menu for the page it covers.
  - PLAN's `href="#"` controls that are really buttons are still links.

**Registry.** 246 entries in 28 files. Phase 3 adds 150 in 3 files: `p3-merge-layout.json` 139,
`p3-id-rename.json` 10 and `p3-asset-path.json` 1. By category: merge-layout 141, femto-divergence
54, dropped-route 30, id-rename 10, browser-limit 6, asset-path 2, owner-change 2 and oracle-bug 1.
`/docs` is 804,126 bytes raw, 53,224 gzipped and 34,151 with Brotli. The budget in PLAN.md Risks
(Page size) is 900 KB, 60 KB and 40 KB.

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p3-gate-sections-full-1` | `sections --b dist --full --browsers chrome,firefox` (the section gate) | 1,368 (638,520 elements) | **PASS: 0 unregistered**; 48,460 registered | 0 | 348 s |
| `p3-gate-pages-full-1` | `pages --a static-femto --b dist --routes /,/examples,/demo,/does-not-exist --full --browsers chrome,firefox` | 120 (25,920 elements) | **PASS: 0 unregistered**; 672 registered, all attributes (the links into the docs and the four hooks) | 0 | 23 s |
| `p3-gate-behavior-1` | `behavior --target dist --browsers chrome,firefox` (criterion 7's checks, 15's layout shift) | 188 runs (74 checks) | **PASS: 188/188** | 0 | 346 s |
| `p3-gate-selftest-1` | `selftest --browsers chrome,firefox` | 70 controls × 2 browsers | **70/70** | 0 | about 6 min |
| — | `static_checks.py --phase 3`; `registry`; `npm run lint` | 15 criteria; 246 entries | **3, 4, 5, 6, 8, 9, 11 and 12 PASS**; 15's static part passes (its run-time parts are the runs above); 14 FAIL, Phase 4's criterion; 1, 2, 7, 10 and 13 NOT-YET; registry valid; lint exit 0 | — | — |

The gate's Safari part is the owner's: `tests/owner-safari.sh one-page` (Owner's Safari steps, about
1 h 45 min), on the Phase 3 commit.

### Phase 4: femto 3 content (2026-11-05)

PLAN's Phase 4: the docs are rewritten for femto 3 from femto's README at `8cd05767` (re-vendored
before the phase, and moved to `c608ee06` at its gate: owner decision 2), and the site drops what parity kept. `/docs` has 40 sections,
nine of them new (Classes and attributes, Browser support, Migrating from Pico, Files, Themes,
Options, Custom module set, Cascade layer, Shadow roots). The version picker is the Theme picker
(`#theme-picker`), the header's version dropdown is a plain version label, and each section's edit
link opens its own file. `/examples` is 11 mockups of widgets, forms and pages in vanilla femto, on
one page, each in a declarative shadow root that loads only `dist/femto.min.css`; `/demo` is not
built and answers 404 (PLAN.md Open questions). The explained separators are gone, every
accessibility item from Phase 3 is fixed, and the ten html-validate rules that were off for parity
are on again. Its gate: criteria 13 and 14, the link check, criterion 10, and criteria 7 to 9
rerun, in Chrome and Firefox; Safari is the owner's (`tests/owner-safari.sh content`). Rig as in
Phase 3.

**How it ran.** One workflow (`wf_027de50c-894`, 34 agents, about 4 h 50 min):
1. A scaffold agent renamed the picker, added the nine stubs in the menu's new order, pointed every
   edit link at its section file, deleted `site/demo.html` and removed the separators.
2. Seven writers ran in parallel, each on its own files: Getting started, theming (the picker,
   Themes, Options, Colors), Customization, layout and content, Forms and Components, the site
   shell, and `/examples`.
3. An accessibility agent, alone on `site/`:
   - links that act as buttons became buttons: the theme toggle, the 146 copy controls, the docs
     menu's Documentation and Close, and the color modal's close;
   - the open off-canvas menu makes the rest of the page `inert`;
   - a code block that scrolls is a named tab stop;
   - the landmarks have names.
4. A checks agent:
   - brought the behavior suite to 232 runs, with new checks for each new control;
   - wrote the link check and the Phase 4 parts of criteria 6, 9 and 13;
   - turned the parity-only html-validate rules back on;
   - added `owner-safari.sh content`.
5. Two review rounds, each of four lenses (accuracy against femto's README and CSS,
   accessibility, wording, completeness), found 79 and 58 findings. A fix round by each owner
   followed each round.

**The lead's calls, and the owner's.**
- The link check looked up a fragment-only link through the page's URL, so the 404 page's skip
  link (`#content`) was read as a link to `/404`. A fragment alone is now looked up in the page that
  holds it (Link check); the six controls still fail as intended.
- `/docs` is over Phase 3's gzip and Brotli budgets; the owner raised them (owner decision 14).
- Criterion 10's last failure is femto's dark hover color; the owner chose to fix it in femto
  (owner decision 15). A subagent made the fix in `../femto` (9 theme values, femto's divergence
  entries, its theme check, a CHANGELOG line; femto's static checks, its comparisons of every
  default page and all 20 themes, and its selftest pass in Chrome and Firefox), the lead committed
  it there on the owner's word as `c608ee06`, and `npm run vendor` moved the site to it. The CSS
  variables section's orange sample follows it, and Themes now says a custom theme's inverse text
  needs 4.5:1 on both backgrounds.
- The build fills `{{commit}}` from `SOURCE`, as it fills `{{version}}`, so the site's 19 links to
  femto's files at the vendored commit (14 on `/docs`, the footer's license on every page) follow a
  re-vendor.
- Criterion 15's run-time loads used to come from the parity comparisons, which Phase 4 no longer
  runs. `dist` against itself (`p4-gate-loads-1`) checks every load of the five pages instead.

**Owner items left for femto.** Found by the reviewers, not fixed here, and not failing a
criterion:
- An open dropdown's summary in dark, without focus, is `#7b8495` on `#1c212c` (4.27:1;
  `css/components/accordion.css` line 62). axe passes the page as it loads.
- A read-only input or textarea shows no focus indicator (`css/forms/basics.css`).
- CSS-only tooltips cannot be dismissed with Escape (WCAG 1.4.13), and on a copy button the
  tooltip covers the code next to it.
- The focus-ring tokens are 1.4:1 to 2.0:1 against the page background.
- femto's README says `dist/femto.min.css` is "about 74 KB"; the vendored file is 78,259 bytes
  (78,280 at 8cd05767, as this item first said; corrected in Phase 6, content-a-4), and Files repeats
  the README's number.
- femto's README says `.femto-background-*` gives "a readable text color", but 31 shades set white
  text below 4.5:1.

**Registry.** 246 entries in 28 files, as at Phase 3's gate: Phase 4 compares no route against the
oracle, so it adds none. `/docs` is 806,978 bytes raw, 63,158 gzipped and 42,115 with Brotli; the budget in
PLAN.md Risks (Page size) is 900 KB, 70 KB and 48 KB.

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p4-gate-behavior-1` | `behavior --target dist --browsers chrome,firefox` (criterion 7; femto at `8cd05767`) | 232 runs | **PASS: 232/232** | 0 | 361 s |
| `p4-gate-a11y-1`, `p4-gate-a11y-widths-1` | `a11y --target dist`, then `--widths 320,768,1024` (criterion 10; femto at `8cd05767`) | 40 and 60 | FAIL on 2 targets in 1 rule, Group's current button in dark (owner decision 15) | 0 | 41 s and 59 s |
| `p4-gate-selftest-1` | `selftest --browsers chrome,firefox` | 70 controls × 2 browsers | **70/70** | 0 | — |
| `p4-gate-a11y-2`, `p4-gate-a11y-widths-2` | the same two a11y runs, femto at `c608ee06` | 40 and 60 | **PASS: 0 serious or critical**; 16 and 24 moderate cell findings (`landmark-unique`), listed | 0 | 41 s and 60 s |
| `p4-gate-behavior-2` | `behavior --target dist --browsers chrome,firefox`, femto at `c608ee06` | 232 runs | **PASS: 232/232** | 0 | 360 s |
| `p4-gate-loads-1` | `pages --a dist --b dist --routes /,/docs,/docs?theme=jade,/examples,/does-not-exist --browsers chrome,firefox` (criterion 15's run-time loads) | 56 (420,984 elements) | **0 cross-origin loads**. The run FAILs on 4 style records in one cell (Chrome, `/docs?theme=jade`, light, 375): the Progress example's code is one character wider on one side (344.5 against 352.906 px). Its random value had one digit on one side and two on the other; Phase 4's longer sample overflows its `pre` at 375, so the `code`'s width follows the value, and the `progress-value-code` mask covers only the token. Not a site difference, and Phase 4 gates on no comparison | 0 | 87 s |
| — | `static_checks.py --phase 4`; `registry`; `npm run lint` | 15 criteria and the link check; 246 entries | **3, 4, 5, 6, 8, 9, 11, 12, 13, 14 and the link check PASS** (451 internal links; its six controls fail as intended); 15's static part passes (its run-time parts are the runs above); 1, 2, 7 and 10 NOT-YET (the harness's); registry valid; lint exit 0 | — | — |
| — | `static_checks.py --criteria links --external` | 67 outside URLs | FAIL on 11, every link to femto's files at `c608ee06` (404 until the owner pushes femto's `dev`). Listed as pending: the edit links to files this branch adds, and npm's page before femto's first publish. At `8cd05767`, before the move, it passed | — | — |

The gate's Safari part is the owner's: `tests/owner-safari.sh content` (Owner's Safari steps), on
the Phase 4 commit.

**Safari.** The owner's first pass (2026-11-05, on `5b8c218`) failed: `p4-behavior-safari-light-1`
had 90 PASS, 10 FAIL, 8 ERROR and 8 SKIP of 116 runs (396 s), and `p4-behavior-safari-dark-1` 4 PASS,
1 FAIL and 111 SKIP (12 s). What failed, and what changed:
- Six FAIL were the harness's Tab, which skips links and buttons in Safari: `theme-toggle-button` and
  `copy-keyboard` on both routes, `picker-swatch-focus` and `dropdown-items`. The behavior mode now
  presses Option+Tab there, as the styles mode does. That showed a site bug: colors.js left a Tab
  with Alt held to the browser, so in Safari the color modal's Tab did not cycle. It now treats
  Alt+Tab as Tab.
- The eight ERROR were checks Safari's WebDriver cannot run: the preload scripts of
  `color-scheme-flash` (two routes), `examples-first-frame` and `examples-first-frame-cold`,
  `modal-scrollbar-width`'s classic scrollbar, `font-size-restored-switch`'s restored switch, and
  `theme-os-live`'s live switch of the OS scheme (two routes). They are now skipped in Safari, with
  the reason (`preload`, `safari`), and `font-size-restored-switch` ends once Safari brings the switch
  back unchecked over the px table.
- `examples-dialog`: Escape closed the dialog, but focus was not on its opener: in Safari a click
  does not focus a button, so the dialog gave focus back to `<body>`. examples.js now puts it on the
  opener when the dialog closes (in Chrome, with the opener clicked by script, which focuses nothing
  either, focus went to `<body>` without it and to the opener with it).
- `examples-isolation`, `examples-isolation-stored` and `examples-isolation-dark`: 51 values each,
  every one a rem at 16 px in the reference frame where the page had 20 px. The reference now adds
  the examples after its root is styled, and the note gives both roots' font size.
- `pre-scroll-keyboard`: the focused code block did not scroll with the Right arrow. Each press is
  now held 0.1 s and the scroll waited for up to 2 s, and the note lists the keydown events the
  `pre` saw. If it still fails, the note says whether the keys reached it.

In Chrome and Firefox, `p4-safari-fix-behavior-1` (`behavior --target dist --browsers
chrome,firefox`) passed 232/232 in 369 s, with both roots at 20 px in every `examples-isolation`
note; after the keydown record moved to `window` (it sees a cancel by any handler), its four keyboard
and dialog checks passed again (`p4-safari-fix-behavior-2`, 8/8). The Safari paths cannot run
here: run through `run_one` with a stand-in Safari page, the Light pass runs 101 checks and skips 15
(5 `media:dark`, 4 `preload`, 3 `safari`, 2 `motion:reduce`, 1 `javascript:off`), and the Dark pass
runs 5 and skips 111 (`media:light`).

The owner's second pass (2026-11-05, on `5b8c218` with these fixes uncommitted) passed:
`p4-behavior-safari-light-2` 101 PASS and 15 SKIP of 116 runs (411 s), `p4-behavior-safari-dark-2`
5 PASS and 111 SKIP (12 s), 0 FAIL and 0 ERROR in both, the skips as the stand-in run predicted.
Each session's log says the OS scheme it was meant to run in. The notes: `examples-isolation` had
both roots at 20 px and every compared value equal (355 elements and pseudo-elements); `pre-scroll-keyboard`'s eight Right arrows all reached the
`pre`, none canceled, and it scrolled to 234 px; `font-size-restored-switch` ended at the px table.
With Chrome and Firefox's runs above, criterion 7 passes in all three browsers.

### Phase 5: cleanup (2026-11-05)

PLAN's Phase 5: packaging, hosting files, docs and a GitHub check. `package.json` pins the latest of
each tool on npm (eslint-plugin-baseline-js 0.7.7, html-validate 11.18.0 and wrangler 4.158.0
moved; the other four and Node 26.13.0 were current), and `package-lock.json` follows.
`.prettierrc` keeps only `printWidth`, and `.gitignore` keeps every line, with `.env` under the
Cloudflare heading. `site/_headers` gives the 15 `.woff2` files in `/assets/fonts/` a year
(`immutable`) in place of the dead `/build/*` rule; `OFL.txt` beside them keeps Pages' default. The
new `site/robots.txt` names the sitemap, and `404.html` has `noindex` in place of its canonical and
`og:url`. README describes the GitHub check, the headers and robots.txt, says axe-core runs in
Chrome and Firefox, and says another host needs Pages' rules. `LICENSE.md` keeps CC BY-SA and names
the parts under their own licenses: femto (MIT), the fonts (OFL), the GitHub, npm and X icons (Font
Awesome Free, CC BY 4.0) and the line icons (Tabler Icons and, for Grid's plus and minus, Feather;
both MIT). PLAN.md's File tree adds `.github/workflows/check.yml` and catches up with Phase 4
(`examples.css`, `examples.js`, `{{commit}}`). `check.yml` fetches femto at `SOURCE`'s commit into
`../femto`, then runs `npm ci`, `npm run build`, `npm run lint` and `uv run tests/static_checks.py`
on Linux, and never deploys. Criterion 6 now serves `dist/` with the wrangler in `node_modules` when
its version is `package.json`'s pin, so the check runs the lockfile's, and with `npx wrangler@<pin>`
otherwise. During the phase the owner amended femto's `c608ee06` into `33d4dc6f`, on femto's `dev`
and `main` and on GitHub, and `npm run vendor` moved the site to it: one comment line goes from each
of nine files in `css/themes/` and from `css/tokens/schemes.css`, and femto's `dist/` is unchanged
(owner decision 2). Its gate: criteria 4, 5, 6, 11, 12 and 14.

**How it ran.** Two writers, one on packaging and the hosting files and one on the check and the
docs; a review and a first gate run; a fix round (the `.woff2` rule, README's browsers, the File
tree, the icons' licenses, a comment in `check.yml`); a second gate run; a second review and fix
round (Feather for Grid's two icons, criterion 6's wrangler, README's sentence on Pages' rules);
then this third gate run.

| Run | Command | Result | Wall clock |
|---|---|---|---|
| Static checks | `uv run tests/static_checks.py --json <scratch>` (phase 5, inferred from "Describe femto 3") | **4, 5, 6, 11, 12 and 14 PASS**; 3, 8, 9, 13 and the link check PASS (449 internal links; its six controls fail as intended); 15's static part passes (806,978 bytes raw, 63,164 gzipped, 42,073 with Brotli); 1, 2, 7, 10 and 15 NOT-YET; exit 0. Criterion 6 ran `node_modules`' wrangler 4.158.0: 23 URLs answer 200, two 308 and 84 paths 404 with the 404 body. A first run on Python 3.12.2 (the cached environment in the next row) gave the same | 18 s |
| External links | `static_checks.py --criteria links --external` | **PASS: 67 of 67 outside URLs answer below 400**, the 11 links to femto's files at `33d4dc6f` among them (at Phase 4's gate, those 11 failed at `c608ee06`) and the 41 edit links on this repository's `main`; none pending. Run first on a script environment that uv had cached on python.org's Python 3.12.2, which has no CA certificates, it failed all 67 with `CERTIFICATE_VERIFY_FAILED`; `uv run --python 3.15` rebuilt the environment on uv's 3.15.2, and the same command then passed | 3 s |
| Hosting | `node build.mjs --out <scratch>` (119 files, equal to `dist/`), `wrangler pages dev` 4.158.0 from `node_modules`, `curl` | The 15 `.woff2` files answer `public, max-age=31536000, immutable`. `OFL.txt`, `/`, `/docs`, `/examples`, `/404`, `common.css`, `fonts.css`, `site.js`, `femto.min.css`, `sitemap.xml`, `robots.txt`, `site.webmanifest` and `favicon.svg` answer Pages' `public, max-age=0, must-revalidate`. `/robots.txt` is 200 `text/plain`, the source file byte for byte, and names `https://femto.style/sitemap.xml`. `/no-such-page` is 404 with the 404 body (one `noindex` in its head, no canonical or `og:url`). The sitemap lists `/`, `/docs` and `/examples`, each 200. **`/_headers` answers 502, not 404**: wrangler's dev server looks up `dist/_headers/index.html` and fails with `ENOTDIR`, and its body is only that error. A build of `e03815b`, before Phase 5, answers the same, and so do `/robots.txt/x` and `/favicon.svg/x`; `/_redirects`, `/_routes.json` and `/_worker.js`, which `dist/` lacks, answer 404 | — |
| GitHub check, simulated | check.yml's steps in a clone of the working tree, committed there as "Finish Static Site", with the three local-only tags removed (GitHub's `femto.style` has no tags, and its `dev` and `main` are at `e03815b`); each `run:` as written, under GitHub's default `bash --noprofile --norc -eo pipefail`, with no global git config and an empty npm cache; femto fetched from GitHub into the clone's `../femto` (one commit); Node 26.13.0, as `.node-version` says (Homebrew's `node@26`, npm 11.20.0; the machine's default is 24.22.0), and uv 0.13.6 | Fetch, `npm ci` (132 packages), build, lint and `static_checks.py` all exit 0. Phase 6 (commit "Finish Static Site"); **11 PASS, 0 FAIL, 5 NOT-YET**, with 12 (66 files equal the fetched commit) and 13 PASS, and criterion 6 on `node_modules`' wrangler 4.158.0 | 0.5 s, 2.8 s, 0.3 s, 0.9 s, 22 s |
| actionlint | `uvx --from actionlint-py --with shellcheck-py actionlint .github/workflows/check.yml` (1.7.12) | Exit 0, no errors; the three action tags exist on GitHub (`checkout@v7`, `setup-node@v7`, `setup-uv@v10.3.3`) | 0 s |

**Not verified here.**
- `/_headers` on Cloudflare Pages itself: `wrangler pages deploy` leaves `_headers` out of the
  uploaded files and sends it as configuration, so Pages should answer 404. Only the owner's deploy
  can show it. Answered in Phase 6: it answers 404 on `femto.style` and `femto-style.pages.dev`, and
  the fonts carry the year's caching, from the Git integration's deploy of `76d0e92`.
- The check on GitHub's own runner: `ubuntu-latest`, the latest uv and the Python it picks there,
  and `@cloudflare/workerd-linux-64` and `@esbuild/linux-x64` (both in the lockfile) for
  criterion 6. A `pull_request` run checks out GitHub's merge commit, which the simulation did not.
  The runner user owns the checkout and `../femto`, so git's `safe.directory` should not apply.
  Linux file names are case-sensitive, and macOS's are not; no root-relative link in the build
  differs from its file in case (315 checked).
- The check runs only once the owner pushes the commit that adds it. Answered in Phase 6: the
  owner pushed `76d0e92` to `dev` and `main`, and the workflow Check passed on GitHub's runner on
  both (`gh run list`: `dev` at 22:26:14Z and `main` at 22:33:50Z, 2026-11-06).
- Criteria 7 and 10 were not rerun. Phase 5 changed the 404 page's head and comments in femto's
  CSS, and no other markup, CSS or script.
- `npm ci` reports 4 vulnerabilities in dev dependencies: 3 moderate, from `minimatch` under
  eslint, and 1 high, `source-map-js` under `@eslint/css`. No criterion covers them. Corrected in
  Phase 6 (repo-7): the high one had a fix inside `@eslint/css-tree`'s `^1.2.1` range before Phase
  5's gate, and a lockfile-only `npm audit fix` now moves `source-map-js` from 1.2.1 to 1.2.2, which
  closes it (GHSA-68fv-2mgg-jv7q). The 3 moderate `minimatch` advisories (GHSA-g3hv-75wg-m249)
  remain: the first patched `minimatch` is 11.0.1, outside eslint 10.14.0's `^10.2.6` and
  `@eslint/config-array` 0.23.5's `^10.2.4`, so npm's only fix is `--force` down to eslint 9.39.5.
  An `overrides` entry forcing `minimatch` 11 would also clear them, untested with eslint 10.14.0.

### Decision 17: character icons (2026-11-05)

On branch `unicode-icon-swap`, the owner replaced the site's third-party icons (PLAN.md Decision
17). The 207 Tabler and Feather SVGs in `site/` (147 copy buttons, 40 edit links and 20 others),
and `site.js`'s check, became empty `<span class="icon icon-<name>" aria-hidden="true">` elements
whose character `common.css` draws: text characters with no emoji form (✓ ✕ ⧉ ✎ ☰ → ⊕ ⊖ ⤢ ◐ and
`</>`), and the homepage's ⚙️ and ⚡ as one-color silhouettes, as Decision 16's toggle is. The four
Font Awesome brand marks (GitHub twice, npm, X) became Simple Icons' CC0 SVGs; jsDelivr's already was
one, byte for byte. `site.js` makes the copy
button's check as a span, `picker.js` clones the swatch's `.icon-check`, `colors.js` writes the color
modal's two spans, and the `copy-button` checks look for `.icon-copy` and `.icon-check`. Each
character sits on its line's baseline; centered in an SVG's box, as a first draft did, it sat about
0.2em high. A first draft also drew copy and edit as 📋 and ✏️ silhouettes, which read as a block
and a slash at 1rem; ⧉ and ✎ match the old outline icons. `/docs` dropped from 806,978 to 747,008
bytes raw. No registry entry records it: parity with the oracle stopped binding at Phase 4.
Coverage, checked in the fonts themselves: every character is in Android's merged symbol font
(`NotoSansSymbols-Regular-Subsetted.ttf`, AOSP `external/noto-fonts`); on Windows, Cambria Math
has ⧉, ⤢, ⊕ and ◐, and Segoe UI Symbol ⧉ and ✎ (zuga.net's tables); on macOS, Apple Symbols and
STIX draw ⧉ and ⤢. iOS and Linux were not checked.

| Run | Command | Result | Wall clock |
|---|---|---|---|
| Static checks | `uv run tests/static_checks.py` | **11 PASS, 0 FAIL**, 5 NOT-YET (browsers); 9 (html-validate 11.18.0) and 11 (lint, `container-type` and `cqi` at widely) included | 20 s |
| Behavior | `uv run tests/run.py behavior --target dist --browsers chrome,firefox` (`20261105-182747-behavior-913`) | **PASS: 232/232** | 6 min |
| Accessibility | `uv run tests/run.py a11y --target dist` (`20261105-183347-a11y-1639`) | **PASS: 0 serious or critical**; 1 moderate on `/docs` per cell (`landmark-unique`, as at Phase 4) | 40 s |
| Before and after | element screenshots of every icon's context, the build of `5bdb790` against this one, in Chrome Beta 158 and Firefox 160, light and dark, and in Safari, light | Each icon in its old place, size and color; the arrow moves on hover; the copy button's box does not change when its check shows | — |

**Not verified here.** In Safari, the screenshot after a click or a scroll came back black on both
sides, so the copy button's check and the picked swatch's check were not seen there; the behavior
suite and the owner's dark pass were not run in Safari. Other platforms draw these characters
with their own fonts (Windows' Segoe UI Symbol, Android's Noto), which this Mac-only rig cannot
show.

### Decision 18: icon markup (2026-11-06)

On branch `unicode-icon-swap`, the owner chose markup over classes for the icons (PLAN.md Decision
18). Each of Decision 17's characters, and Decision 16's emoji, is now the text of a
`<span role="img">` with no class, and `span[role=img]` is the stylesheets' hook. An icon that is a
control's only content took the control's `aria-label`: the 146 copy buttons, the menu's Close
button, the header's theme toggle and the Nav example's Menu link, and in `colors.js` the color
modal's close button and five copy buttons. Every other icon is `aria-hidden="true"`: the 40 edit
links, the 8 arrows, the homepage's five feature icons, the breadcrumb's ☰, Grid's ⊕ and ⊖, the
picked swatch's ✓ and the Color schemes switcher's emoji. `site.js` writes the copy button's ✓ with
the ⧉ icon's name (the button still copies; the status region still says "Copied"), and the
toggle's emoji and label; `docs.js` writes the switcher's emoji; `picker.js` clones the swatch's
`span[role=img]`; `code.css` styles the check by the "Copied" tooltip. Two glyphs keep a hook of
their own: ⤢'s `scale(1.25)`, found by its feature's link (`article:has(a[href="/docs#typography"])`),
and the first feature's `</>`, marked up as `<code>` for its font. The checks read each icon's text
and label: `copy-button` its ⧉ or ✓, and that the ✓ keeps the button's name; the toggle checks the
🌙 and the label on the icon; the breadcrumb check the text beside the ☰; and the toggle and Close
selectors find their buttons by their icon's label. `/docs` dropped from 747,008 to 742,723 bytes
raw. The characters are now page text, so a reader who copies a link's text copies its arrow too.

axe now reads the characters as text. Its `color-contrast` rule lists each symbol-only icon on `/`
and `/docs` as needing review ("only non-text characters"; each is in its link's or button's own
color), and on `/docs` `label-content-name-mismatch` lists the picked swatch, named "Azure" and
showing an `aria-hidden` ✓. Both are incomplete results, not violations.

| Run | Command | Result | Wall clock |
|---|---|---|---|
| Static checks | `uv run tests/static_checks.py` | **11 PASS, 0 FAIL**, 5 NOT-YET (browsers); 9 (html-validate) and 11 (lint, `width: fit-content` and `:has()` at widely) included | 20 s |
| Behavior | `uv run tests/run.py behavior --target dist --browsers chrome,firefox` (`20261106-080028-behavior-22995`; Chrome 158.0.8127.18, Firefox 160.0) | **PASS: 232/232** | 6 min |
| Behavior, after the last edit (the JS's characters written as escapes) | the same with `--checks` for the 14 copy, toggle, picker and color modal checks (`20261106-080647-behavior-23976`) | **PASS: 42/42** | 31 s |
| Accessibility | `uv run tests/run.py a11y --target dist` (`20261106-080742-a11y-24599`) | **PASS: 0 serious or critical**; 1 moderate on `/docs` per cell (`landmark-unique`, as at Phase 4) | 41 s |
| Before and after | element screenshots of every icon's context, the build of `f8f065f` against this one, in Chrome and Firefox, light and dark, and in Safari, light | Each icon in its place, size and color, ⤢ with its scale; the arrow moves on hover | — |
| Safari, in the page | the swatch's and the copy button's icons read through WebDriver, before a click, after it and after the revert, and the toggle after a click | The check is ✓, bold, in `--femto-code-copied`, named "Copy code", and reverts to ⧉; the toggle shows 🌙 and is named "Turn off dark mode" | — |

**Not verified here.** Safari's automation window is hidden (`document.visibilityState` is
"hidden"): its document timeline stood at 111 ms after 1.5 s and no animation frame ran, so the
check's pop-in sat at its first frame (half size) and the element screenshots of the copy button and
the swatches came back blank, on both builds. Whether the check finishes popping in, in a visible
Safari window, was not seen. Safari's behavior suite and the owner's dark pass were not run, and iOS
and Linux fonts were not checked, as for Decision 17.

### Phase 6: final review (2026-11-06)

PLAN's Phase 6. PLAN.md's Workflow table names it "Final review": a completeness critic and
adversarial reviewers, every gate a fix touched rerun, then the full matrix in all three browsers,
with all criteria as the gate and "Address Final Review" as the commit. The owner asked for "Phase
6, the cleanup", but the cleanup was Phase 5 ("Finish Static Site"), so this record follows the
table. Rig as in Decision 18's record: Chrome Beta 158.0.8127.18 (chromedriver 158.0.8127.18),
Firefox 160.0 (geckodriver 0.37.1), Selenium 4.52.0, axe-core 4.14.0, wrangler 4.158.0 and, from
this phase, html-validate 11.19.0. Every run below is on `dev` at `76d0e92` with Phase 6's work
uncommitted. No agent ran Safari, changed a macOS setting, pushed or deployed.

**How it ran.**
1. A baseline of every gate on `76d0e92`, before any change (`p6-base-*`): all passed.
2. A review in eight lenses, each by one reviewer and checked by one verifier:
   - `critic`: completeness, against 01 §2's behavior list and every criterion;
   - `a11y`: accessibility and keyboard;
   - `urls`: URL and history behavior across browsers;
   - `content-a`, `content-b` and `content-c`: content accuracy against femto's README and CSS,
     in three parts;
   - `css`: CSS and JavaScript against Decision 12's target;
   - `repo`: packaging, hosting and the live site.

   The reviewers made 74 findings. The verifiers confirmed 60 and partly confirmed 14, refuted
   none, and added 9 of their own (`verify-*`). Of the 83, 6 are blockers, 15 major, 31 minor and 31
   nits (the reviewers' 74: 5, 13, 26 and 30; the verifiers' 9: 1, 2, 5 and 1). The baseline added
   two notes of its own: criterion 2's NOT-YET named Phase 3's gate command with `/demo`, and Phase
   4's femto item gave a stale file size.
3. The owner's decisions of 2026-11-06 (owner decisions 16 to 21).
4. Seven fix agents in parallel, each on its own files: the section files, the pages and partials,
   the site JS, the site CSS, the behavior checks, the harness and static checks, and the docs and
   packaging. Then the parity reruns in Chrome and Firefox, and the gate, which added one mask.
5. A re-review of the fixes in three lenses (site, tests, docs), each checked by a verifier: 13
   defects (10 found by the reviewers, 3 added by the verifiers; 5 minor and 8 nits) and 2 questions
   for the owner. One agent, alone in the tree, fixed the 13 (fix 2).
6. The final runs, one after another with no other agent running (`p6-final-*`), then this record.

**The owner's decisions** (2026-11-06; owner decisions 16 to 21, at the end of this file):
Decision 11 moves to Cloudflare Pages' Git integration and the `deploy` script goes (16); the copy
buttons are named by `aria-labelledby` (17); criterion 2's Safari legs are rerun between the tags
with `owner-safari.sh parity` (18); the harness reads Safari's Reduce Motion and the owner runs a
`reduced` pass (19); going live before femto's first publish needs no site change (20); and the
local tags name the gates' commits (21). `remix-final` 507dcda, `static-multipage` 9383e6b and `static-femto` 7587a7e
were recreated, and `static-one-page` 7b90883 was added. All four are local, not pushed.

**The fixes, by area**, with their finding ids:
- **Docs sections and menu** (`site/docs/sections/`, `menu.json`):
  - the CSS variables example: its sample's button rule is `button[type=button]` and its live
    `<style>` selects `#css-var-example > h1`, `> p` and `> button`, so it no longer reaches the
    footer's copy button (content-a-2, verify-content-a-2);
  - the token files named as those that "declare the tokens' defaults", with a sentence on the
    seven names set only in their own modules (content-a-5);
  - Classes and attributes' samples match their live examples (content-a-7);
  - Typography's xxl tooltips open to the left, so the table no longer scrolls into blank space
    from 768 px (content-b-2), and the sizes in `em` name `<small>`, `<sub>`, `<sup>` and code
    (content-b-8);
  - Button's and Link's live examples lose the `.grid` wrappers and `<br>`s their samples lack
    (content-b-3);
  - Input's and Forms' descriptions say which inputs share one field style (content-b-4);
  - Grid no longer says `.grid` "only" makes equal columns (content-b-6);
  - Select says "a size above 1" (content-b-7);
  - the six overflowing scroll wrappers at 320 and 375 px are named regions (a11y-13);
  - the Nav example's X icon is `aria-hidden` (a11y-9);
  - Remix's `data-discover="true"` is gone from every section (content-b-9).
- **Pages and partials**: `og:title` and `og:description` on `/` and `/examples` (content-c-6),
  `aria-hidden` on the footer's, logo's, header's and homepage's decorative SVGs (a11y-9), and no
  `data-discover` (content-b-9; also `build.mjs:133`).
- **Site JavaScript**:
  - copy buttons named by `aria-labelledby` (a11y-1, owner decision 17), in `site.js`
    (`nameCopyButton()`) and in `colors.js`;
  - the Progress example's Pause button, paused from the start under reduced motion (a11y-8); fix 2
    lays out its box before docs.js runs, so a cold load of `/docs#progress` or `/docs#tooltip` no
    longer shifts the page (Chrome's layout shift was 0.041 to 0.073, by route and width, and is 0;
    rr-site-4);
  - a link to the URL's own `#hash` on a `?theme=` URL scrolls to the heading (urls-1);
  - the picker's `replaceState` is wrapped in `try` (urls-2), it keeps the reader's other query
    items byte for byte (urls-4), and it shows the URL's theme only on the exact path `/docs`, as the
    head script does (urls-5); `docs.js`'s comments on when the hash is written are corrected
    (urls-3), and so is `colors.js`'s on Space (a11y-14);
  - the menu's refocus saves and restores the scroll position in place of `focus({preventScroll})`
    (css-1), and the code-block refit waits for `document.fonts.load()` in place of `loadingdone`,
    which Safari never fires (css-2);
  - the spy's take-over listens to `pointerdown` from touch in place of `touchstart`, and keeps
    `wheel` (verify-css-2; the owner question rr-site-5 below);
  - the typing demo's code matches its form: no `type` on Next (content-c-3), a plain select and no
    space in the small layout's date step (content-c-4 (c), (e)), and `disabled` on the busy search
    input (content-c-4 (a), rr-site-2).
- **Site CSS**:
  - in forced colors, the theme toggle's, the switcher's and the homepage's glyphs and marks are
    drawn in system colors (a11y-2);
  - in forced colors, the Theme picker's swatches keep their colors and get a `CanvasText` border,
    which is all a visited swatch keeps in Firefox (a11y-3, rr-site-1);
  - the site's own focus rings have a transparent outline beside the box-shadow, which forced colors
    paints (a11y-5);
  - the Grid example's cells reach 5.5:1 and 6.1:1 (a11y-6);
  - inline code in prose wraps at 320 px (a11y-7);
  - the copy button's icon box keeps its height under WCAG 1.4.12's text spacing (a11y-12,
    rr-site-3);
  - backdrop-filter's lint allowance is one disable comment beside its pair, and the text-wrap and
    background-clip reasons are corrected (css-5, css-6, css-7).
- **Lint** (`eslint.config.js`): the comment says what eslint-plugin-baseline-js checks, and the
  never-list covers `loadingdone`, `scrollend` as a template literal and `onscrollend`,
  `preventScroll` and `container` as any key, and `blocking` as a member (css-1, css-2, css-3,
  rr-tests-1; Lint).
- **Behavior checks** (The checks): `copy-button` and `color-modal-tab-cycle` read computed names
  (a11y-1); `mobile-menu-focus` holds the scroll position (verify-css-1); `progress-pause` and
  `progress-reduced-motion` are new (a11y-8), and so is `tooltip-link-same-hash` (urls-1);
  `demo-loop` holds the demo's code (content-c-3, rr-site-2); `spy-categories` holds the side nav's
  reveal (critic-8); `spy-scroll`'s and `spy-fast-scroll`'s docstrings follow urls-3.
- **Harness and static checks**:
  - criterion 4's scripts are `build`, `dev`, `vendor` and `lint`, and a script that runs `wrangler
    pages deploy` or `publish` fails (owner decision 16, rr-tests-m1);
  - from Phase 4, criterion 2's NOT-YET calls the Phase 1 to 3 gates historical and names their
    records, criterion 15 names the loads command, and criterion 7 names the `final` and `reduced`
    modes (verify-critic-1, critic-7, baseline-1);
  - criterion 11 plants 12 never-list probes, lints the two inline head scripts, and notes what the
    lint never reads (css-3, css-4, rr-tests-1);
  - `tests/owner-safari.sh` has the modes `final`, `reduced`, `parity` and `spike`, a guard against
    overwriting a result folder, and Reduce Motion checks; its old modes refuse to run (critic-6,
    critic-7, rr-tests-2, rr-tests-3);
  - Safari's OS motion is read by the behavior mode (`--expect-os-motion`) and by the comparison
    modes, which refuse `reduce` (critic-3, owner decision 19, rr-tests-2);
  - the `static-one-page` target (owner decisions 18 and 21);
  - at the gate, the mask `progress-value-code-width` (Masks).
- **Packages, PLAN.md, README.md and `check.yml`**:
  - Decision 11, criterion 4, Repo changes and Risks (Cloudflare) are rewritten for the Git
    integration, the `deploy` script is gone, README's Deploy section lists the build settings and
    the zone settings, and `check.yml`'s header says Pages deploys and the check only checks (owner
    decision 16);
  - html-validate 11.19.0 (critic-10, repo-6);
  - a lockfile-only `npm audit fix` (repo-7);
  - PLAN's Parity harness lists every mode (critic-13);
  - its File tree adds `.node-version` and `.prettierrc` and gives `build.mjs` as 212 lines
    (critic-15, repo-8);
  - its Conversion rules record the breadcrumb's per-frame check (critic-16, rr-docs-1);
  - Decision 11's wording, the Tool versions row, the Page size row and the Matrix line are
    corrected (rr-docs-2, rr-docs-3, rr-docs-m1, rr-docs-m2);
  - Risks records going live before femto's publish (repo-4, content-c-2, owner decision 20).
- **This file**: the Layout rows (critic-9), the historical Quick start commands (critic-12),
  Phase 5's open items answered (critic-14), the wrangler notes (urls-6), the npm audit note
  (repo-7, rr-docs-2), the Lint section (css-3, css-4), the corrected femto size (content-a-4) and
  the rows of every changed check.

**Skipped, and why.**
- content-a-6, Themes' "Built in" for Azure: optional, and the site follows femto's README.
- content-c-4 (b), the date phase's value, which the code does not show: changing it means
  changing `phase.date` and `landing.py` together, and the verifier allowed leaving it.
  content-c-4 (d), `<fieldset role="group">` in the code against `<form role="group">`: wording
  only, with the same sizes.
- critic-11's fallback paths get no new checks; they are listed under Not verified here.
- The optional `wrangler.toml`, which would pin the output directory in the repository: the owner's
  choice, and not among the decisions of 2026-11-06.
- PLAN.md's Decision 3 ("`dist/` is generated, gitignored and deployed") and the Workflow's Phase
  5 row: still true, or historical.
- The femto-owned findings and femto's other defects (below): nothing in `site/vendor/femto` or
  `../femto` changed, and the site's text keeps following femto's README.
- The Cloudflare dashboard findings (below): the owner's steps, outside the repository.
- rr-site-5 and rr-docs-4: the owner's questions (below).

**Against PLAN's letter, and the lead's calls.**
- The Workflow row asks for the full matrix in all three browsers. Chrome and Firefox ran it here;
  Safari is the owner's (Owner's Safari steps), so criteria 1, 2 and 7 are not yet passed in Safari.
- The Phase 1 to 3 gates compared each phase's own build, so from Phase 4 they cannot be rerun on
  `dist/` (Decision 6). Criterion 2's Phase 2 and 3 comparisons were rerun between the tags
  (owner decision 18). Phase 1's gate, in Chrome and Firefox only by PLAN, was not rerun.
- The mask `progress-value-code-width` is a third masks.json entry for "the random progress value",
  which PLAN's Masked line already names, so PLAN is unchanged. It is the flake `p4-gate-loads-1`
  recorded, which `p6-base-loads-1` missed by chance.
- The copy icons' ids exist only with JavaScript (`site.js`), since the buttons work only with it;
  owner decision 17 left where they come from open.
- The Progress button's box is reserved before docs.js runs by `@media (scripting: enabled)`, with
  one `!important` over femto's `[hidden] { display: none !important }`, not taken out of flow as
  rr-site-4's verifier preferred: no place out of flow fits at 375 px. Without JavaScript it takes
  no space.
- a11y-2 is two `@media (forced-colors: active)` blocks, one in `common.css` and one in
  `landing.css`, because `landing.css` loads only on `/` and `/examples`.
- PLAN's Page size sentence gives gzip without the stored file name (`gzip -9 -n`), as its earlier
  measures did; `gzip -9` with the name gives 61,020.
- content-c-4 (e) needed three step counts changed in the small layout, not one.
- The picker's query rewrite drops empty items (`&&`), as `URLSearchParams` did.
- Owner decision 16 changes no Decision 15 text: Decision 11 now says that, since a push deploys,
  "Never push" and "Deploying is the owner's step" are one rule.

**Registry.** 246 entries in 28 files, unchanged. The parity reruns registered exactly what the
gates did. `/docs` is 743,761 bytes raw, 61,010 gzipped and 41,446 with Brotli (PLAN.md Risks, Page
size: 900 KB, 70 KB and 48 KB).

Baseline, on `76d0e92` before any change:

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p6-base-behavior-1` | `behavior --target dist --browsers chrome,firefox` (criterion 7) | 232 runs | **PASS: 232/232** | 0 | 369 s |
| `p6-base-a11y-1`, `p6-base-a11y-widths-1` | `a11y --target dist`, then `--widths 320,768,1024` (criterion 10) | 40 and 60 | **PASS: 0 serious or critical**; 16 and 24 moderate cell findings (`landmark-unique`), listed | 0 | 43 s and 65 s |
| `p6-base-loads-1` | `pages --a dist --b dist --full --routes '/,/docs,/docs?theme=jade,/examples,/does-not-exist' --browsers chrome,firefox` (criterion 15's run-time loads) | 168 (1,230,840 elements) | **PASS: 0 differences, 0 cross-origin loads**; the progress value happened to draw alike | 0 | 151 s |
| `p6-base-self-1` | `self --browsers chrome,firefox` (criterion 1, fast axes) | 496 (338,544 elements) | **PASS: 0 differences**; the oracle's Google Fonts loads reported | 0 | 242 s |
| `p6-base-selftest-1` | `selftest --browsers chrome,firefox` | 70 controls × 2 browsers | **70/70** | 0 | 412 s |
| — | `npm run build`; `static_checks.py`; `registry`; `npm run lint` | 15 criteria and the link check; 246 entries | 119 files; **11 PASS, 0 FAIL, 5 NOT-YET** (1, 2, 7, 10 and 15 need browsers; 449 internal links, the six controls failing as intended); registry valid; lint exit 0 | — | 20.5 s |
| — | `static_checks.py --criteria links --external` | 67 outside URLs | **PASS**: 66 below 400; npm's package page pending (403, and the package is unpublished) | — | 6 s |

Parity, Chrome and Firefox (owner decision 18), the commands `tests/owner-safari.sh parity` runs in
Safari:

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p6-parity-styles-1` | `styles --full --a static-multipage --b static-femto --browsers chrome,firefox` (Phase 2's gate) | 1,488 (970,944 elements) | **PASS: 0 unregistered**; 2,258,364 registered and 804,336 inherited, with 7,536 state replays per side, the totals of `p2-gate-styles-full-3` and `p2-sfix2-styles-full-cf`, and the same 43 entries with the same counts | 0 | 587 s |
| `p6-parity-sections-1` | `sections --full --a static-femto --b static-one-page --browsers chrome,firefox` (Phase 3's gate) | 1,368 (638,520 elements) | **PASS: 0 unregistered**; 48,460 registered, every total and all 141 entries' counts as in `p3-gate-sections-full-1` | 0 | 378 s |
| `p6-parity-pages-1` | `pages --full --a static-femto --b static-one-page --routes /,/examples,/demo,/does-not-exist --browsers chrome,firefox` | 120 (25,920 elements) | **PASS: 0 unregistered**; 672 registered, all attributes, as in `p3-gate-pages-full-1` (the same 9 entries) | 0 | 37 s |

Only the screenshot diffs, which never gate, differ from the gates' runs: 460 styles cells against
438 in `p2-sfix2-styles-full-cf`, and 16 pages cells against 4, nearly all with no pixel above
8/255, on `/`, `/demo` and `/docs` in Chrome. The cells change between runs, so this reads as
anti-aliasing and the typing demo, not a style or DOM difference, which the records would show.
The stubbed dry run of `owner-safari.sh parity` runs exactly these three commands with `--browsers
safari`, Light then Dark, and the Safari `--plan` of each gives 744, 684 and 60 cells.

The gate, after the first fixes:

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p6-gate-behavior-1` | `behavior --target dist --browsers chrome,firefox` (97 checks) | 238 runs | **PASS: 238/238** | 0 | 406 s |
| `p6-gate-a11y-1`, `p6-gate-a11y-widths-1` | the two a11y runs | 40 and 60 | **PASS: 0 serious or critical**; 16 and 24 moderate, as at the baseline | 0 | 50 s and 71 s |
| `p6-gate-loads-1` | the loads command | 168 (1,234,800 elements) | FAIL: **4 unregistered** style records in one cell (Chrome, `/docs`, theme-light, 375): the Progress example's `code` is 352.906 px on one side and 344.5 on the other, its `width`, `inline-size`, `transform-origin` and `perspective-origin`; 0 cross-origin loads | 0 | 146 s |
| `p6-gate-mask-proof-1` | `pages --a dist:<copy drawing 7> --b dist:<copy drawing 72> --routes /docs --widths 375 --schemes light,theme-light --browsers chrome,firefox`, with the new mask | 4 (61,248 elements) | **PASS: 0 differences**; the mask covered 8 elements | 0 | 16 s |
| `p6-gate-loads-2` | the loads command, with the mask | 168 (1,234,800 elements) | **PASS: 0 differences, 0 cross-origin loads** | 0 | 146 s |
| `p6-gate-selftest-1`, `p6-gate-selftest-2` | `selftest --browsers chrome,firefox`, before and after the mask | 70 controls × 2 browsers | **70/70** each | 0 | 538 s and 532 s (sharing slots with the loads runs) |
| — | `npm run build`; `npm run lint`; `static_checks.py`; `registry` | 15 criteria and the link check; 246 entries | 119 files; lint exit 0; **11 PASS, 0 FAIL, 5 NOT-YET** (12: 66 files equal femto 33d4dc6f; 450 internal links); registry valid | — | 25 s |

The new assertions, each shown to fail where it should (`dist:<build>` copies in the fix agents'
scratch folders):

| Run id | Command | Runs | Result |
|---|---|---|---|
| `p6-f-checks-3` | `copy-button`, `color-modal-tab-cycle` and `mobile-menu-focus` against a build of `76d0e92` | 8 | FAIL as intended, 7 of 8: the names read "Copy to clipboard Copy code" and "Copy to clipboard Copy hexadecimal color" in both browsers, and Chrome's `mobile-menu-focus` fails at "focus() without options: Escape: the page keeps its scroll position" (-415 px); Firefox's passes, since Firefox does not scroll on focus |
| `p6-f-checks-4` | the four mobile-menu checks against a copy whose refocus is a bare `opener?.focus()` | 8 | FAIL as intended in Chrome's `mobile-menu-focus` at "Escape: the page keeps its scroll position" (-415 px); the other 7 pass |
| `p6-f-checks-6` | `tooltip-link-same-hash`, `progress-pause` and `progress-reduced-motion` against the `76d0e92` build | 6 | FAIL as intended, 6 of 6: the two progress checks at "the Progress section has a pause button", the link check at "Tooltip's heading is on the scroll-padding line" (-199.7 px in Chrome, -200 in Firefox) |
| `p6-f-checks-8` | `demo-loop` against the `76d0e92` build, Chrome | 1 | FAIL as intended at "date-next at 30875 ms: the Next button has no type, as in the code" (`submit`) |
| `p6-f-harness-neg-reveal-off-1` | `spy-categories` against a copy with `revealInNav` turned off | 2 | FAIL as intended at "overflow-auto: the current link is inside the side nav's box" |
| `p6-f-harness-neg-reveal-into-1` | `spy-categories` against a copy whose reveal is `link.scrollIntoView({ block: "center" })` | 2 | FAIL as intended at "classes: the reveal scrolled the side nav, not the page" (scroll events at 3050, 2734 and 3050) |
| `p6-f-checks-7` | `behavior --target dist:<build>`, every check | 238 | **PASS: 238/238**; 715 s with slot waits |
| — | `static_checks.py --criteria 11` with `76d0e92`'s `eslint.config.js`, then with only the three selectors before rr-tests-1; `--criteria 4` with a build script running `wrangler pages deploy dist`, `wrangler pages publish dist` or `npx wrangler@4.158.0 pages deploy dist` | — | FAIL as intended each time: 4 never-list probes (the template literal, `onscrollend`, `preventScroll`, `loadingdone`), then exactly the 3 new probes (`blocking` as a member, `container` through a variable, a string-key `preventScroll`), then criterion 4 in all three variants |

Fix 2, after the re-review, alone in the tree:

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p6-fix2-behavior-1` | `behavior --target dist --browsers chrome,firefox` | 238 runs | **PASS: 238/238** | 0 | 417 s |
| `p6-fix2-a11y-1` | `a11y --target dist` | 40 | **PASS: 0 serious or critical**; 16 moderate | 0 | 57 s |
| `p6-fix2-loads-1` | the loads command | 168 (1,234,800 elements) | **PASS: 0 differences, 0 cross-origin loads** | 0 | 148 s |
| `p6-fix2-selftest-1` | `selftest --browsers chrome,firefox` (the runner and `differ.js` changed) | 70 controls × 2 browsers | **70/70** | 0 | 430 s |
| — | `npm run build`; `npm run lint`; `static_checks.py`; `registry` | 15 criteria and the link check; 246 entries | 119 files; lint exit 0; **11 PASS, 0 FAIL, 5 NOT-YET**, criterion 11 with 12 of 12 never-list probes and its new note; registry valid | — | — |

The final runs, on the final tree, one after another with no other agent running:

| Run id | Command | Cells | Result | Harness errors | Wall clock |
|---|---|---|---|---|---|
| `p6-final-self-full-1` | `self --full --browsers chrome,firefox` (criterion 1, on the current harness) | 1,488 (1,015,632 elements), 4 server chunks | **PASS: 0 differences**; one side loaded twice (Chrome, `/docs/progress`, dark, 375, side B: the oracle's `main-DE3LIIRG.css` did not load the first time), then passed; the oracle's Google Fonts loads on `/docs/css-variables` reported, not gating | 0 | 466 s |
| `p6-final-behavior-1` | `behavior --target dist --browsers chrome,firefox` (criterion 7, and 15's layout shift) | 238 runs (97 checks) | **PASS: 238/238** | 0 | 411 s |
| `p6-final-a11y-1`, `p6-final-a11y-widths-1` | `a11y --target dist`, then `--widths 320,768,1024` (criterion 10) | 40 and 60 | **PASS: 0 serious or critical**; 16 and 24 moderate cell findings, all `landmark-unique` on `nav[data-docs-breadcrumb]` and the Breadcrumb example's nav, listed | 0 | 43 s and 63 s |
| `p6-final-loads-1` | `pages --a dist --b dist --full --routes '/,/docs,/docs?theme=jade,/examples,/does-not-exist' --browsers chrome,firefox` (criterion 15) | 168 (1,234,800 elements) | **PASS: 0 differences, 0 cross-origin loads**, no site-origin loads | 0 | 149 s |
| `p6-final-selftest-1` | `selftest --browsers chrome,firefox` | 70 controls × 2 browsers | **70/70** | 0 | 412 s |
| — | `npm run build`; `static_checks.py`; `registry`; `npm run lint` | 15 criteria and the link check; 246 entries | 119 files; **3, 4, 5, 6, 8, 9, 11, 12, 13, 14 and the link check PASS** (450 internal links; the six controls fail as intended); 1, 2, 7, 10 and 15 NOT-YET (their browser runs are above); registry valid; lint exit 0 | — | 28 s |
| — | `static_checks.py --criteria links --external` | 67 outside URLs | **PASS: 67 of 67** below 400, none pending | — | 6 s |

**The criteria at the end of Phase 6**, for the final report (critic-17). The report gives each
criterion per browser and lists the 18 commits from `remix-final` to `76d0e92`: 12 of them carry
subjects outside the Workflow table, among them the owner's Decision 16, 17 and 18 commits.

| Criterion | Chrome and Firefox | Safari |
|---|---|---|
| 1 | PASS, `p6-final-self-full-1` | waits on `final` (`p6-self-safari-*-1`); the last passes ran on the harness of `161053b` and `a393112` (critic-6) |
| 2 | PASS: Phases 2 and 3 rerun between the tags (`p6-parity-*`), equal to the gates; Phase 1's gate is `p1g3-pages-full-1` | waits on `parity`; Phases 2 and 3 never passed in Safari (critic-1) |
| 3, 4, 5, 6, 8, 9, 11, 12, 13 and 14 | PASS, `static_checks.py` | — |
| 7 | PASS, `p6-final-behavior-1` | waits on `final` and `reduced`; the last passes, `p4-behavior-safari-*-2`, predate Decisions 17 and 18 (critic-2) |
| 10 | PASS, `p6-final-a11y-1` and `-widths-1` | not in the criterion |
| 15 | PASS: the static part, `p6-final-loads-1`, and `deep-link-cold` in Chrome | waits on `final`'s loads; production fails it while Web Analytics injects its beacon (the owner's step 5 below) |

**The owner's steps outside the repository** (the Cloudflare dashboard). No agent logged in, used the
dashboard or changed the live site; these are recorded here, in README's Deploy section and in
PLAN.md Risks (Cloudflare). On 2026-11-06 the Git integration's deploy of `76d0e92` served the
unbuilt `site/` folder. 112 of the build's 119 files were the same on both hosts, all of them copied
assets, and every page was `site/`'s source: `/docs` was 2,540 bytes with raw include markers, an
empty side nav and an empty `#content`. `/sitemap.xml` and the palette JSON answered 404, while
`/docs/menu.json`, `/partials/head` and the section files were public. The GitHub check-run
"Cloudflare Pages" on `76d0e92` said "Deployed successfully".
1. **The build settings** (repo-1, critic-5, content-c-1). In Workers & Pages > `femto-style` >
   Settings > Build > Build configuration: Framework preset None, Build command `npm run build`,
   Build output directory `dist`, Root directory empty, Build system version v3. Node comes from
   `.node-version`. Then retry the latest production deployment, or push `main` again. Recheck the
   first build log for Node 26.13.0 and the installed devDependencies, `prismjs` among them. Then
   compare the live files with a fresh local build, never `dist/` while the harness serves it:

   ```sh
   out="$TMPDIR/femto-live"; node build.mjs --out "$out"
   for host in https://femto.style https://femto-style.pages.dev; do
     for pair in /:index.html /docs:docs.html /examples:examples.html /no-such-page:404.html /sitemap.xml:sitemap.xml; do
       live=$(curl -sS -H 'Accept: text/html' "$host${pair%%:*}" | shasum -a 256 | cut -c1-64)
       built=$(shasum -a 256 < "$out/${pair#*:}" | cut -c1-64)
       echo "$host${pair%%:*} $([ "$live" = "$built" ] && echo same || echo DIFFERENT)"
     done
   done
   curl -sS -o /dev/null -w '%{http_code}\n' https://femto.style/docs/menu.json   # 404 once dist/ is served
   ```

   `Accept: text/html` matters: the zone injects step 5's beacon only into a response to a request
   that sends it, as a browser does, and curl's default `Accept: */*` hides it. So on `femto.style`
   the pages hash the same only once steps 2 (for `/examples`) and 5 are done as well; on
   `femto-style.pages.dev` they should once this step is.
2. **Email Address Obfuscation** (repo-2, verify-content-c-1). In the `femto.style` zone, Security >
   Settings (Scrape Shield) > Email Address Obfuscation: Off, or a Configuration Rule for
   `femto.style` and `/examples` that turns it off. It rewrites the six addresses on `/examples` and
   adds a decoder script, which cannot reach the two in the Sign up and Contact mockups' shadow
   roots, so those show "[email protected]" to every reader. Nothing in the repository fixes it
   cleanly: `Cache-Control: no-transform` also turns off compression, and `<!--email_off-->` cannot
   go in a code block (`build.mjs`). Recheck: `/examples` hashes as the build's `examples.html`, and
   `curl -sS -H 'Accept: text/html' https://femto.style/examples | grep -c __cf_email__` prints 0.
3. **Browser Cache TTL** (repo-3, verify-content-c-3). In the zone, Caching > Configuration > Browser
   Cache TTL: Respect Existing Headers, with no Cache Rule that sets a browser TTL. On 2026-11-06 it
   gave 93 of the 119 files (CSS, JavaScript, PNG, SVG and `robots.txt`) `max-age=14400` in place of
   Pages' `max-age=0`, so for 4 hours after a deploy a returning reader can get new HTML with old CSS
   and JavaScript. Recheck: `curl -sSI https://femto.style/assets/css/common.css` shows `public,
   max-age=0, must-revalidate`, as `femto-style.pages.dev` does, and a `.woff2` font still shows
   `public, max-age=31536000, immutable`.
4. **Always Use HTTPS** (repo-5). In the zone, SSL/TLS > Edge Certificates > Always Use HTTPS: On.
   Or widen the `www` Redirect Rule to match the host over http too. On 2026-11-06
   `http://www.femto.style/` hung about 20 s and answered Cloudflare's 522, while
   `https://www.femto.style/` answered 301 to the apex. Recheck: `curl -sS -o /dev/null -w
   '%{http_code} %{redirect_url}\n' 'http://www.femto.style/docs?x=1'` answers 301 at once.
5. **Web Analytics' automatic setup** (verify-repo-1, verify-content-c-2). In Analytics & Logs >
   Web Analytics > the `femto.style` site > Manage site, set the automatic setup to Disable. For
   every request that sends `Accept: text/html` it injects a script from
   `static.cloudflareinsights.com` and a beacon to `/cdn-cgi/rum`, a cross-origin load against
   criterion 15 (`femto-style.pages.dev` has neither). Recheck: `curl -sS -H 'Accept: text/html'
   https://femto.style/docs | grep -c cloudflareinsights` prints 0. Keeping analytics instead would
   be a change to criterion 15, for the owner to make.
6. **Speed Brain** adds a `speculation-rules: "/cdn-cgi/speculation"` header on `femto.style`,
   same-origin and conservative prefetch: harmless, no step (verify-repo-1).

Pages builds and deploys a push to `main` whether or not `check.yml` passes: it does not wait for
GitHub's checks. A Git-connected project cannot switch to Direct Upload.

**femto's items.** The site's text follows femto's README at 33d4dc6f, and nothing in
`site/vendor/femto` or `../femto` changed. Where the README and femto's CSS disagree, the owner
decides on femto's side, and the site follows its README:
- **`data-theme` and `.contrast`'s chevron and spinner** (content-a-1, verify-content-a-1, major).
  README lines 212 and 216: `data-theme` switches the chevron and the loading spinner on
  `.contrast` buttons, and an element that carries `data-theme` keeps its own colors in that scheme.
  CSS: the dark filter rules (`css/tokens/schemes.css:137-144`, `:154-161`) use a descendant
  combinator, and nothing resets them under a nested `[data-theme=light]`. So a light island in a
  dark page gives its `.contrast` busy button and summary a black spinner and chevron on `#181c25`.
  And `data-theme="dark"` on the button, the `<details>` or the `<summary>` itself, in a light page,
  gives a white one on `#eff1f4`: both invisible. Pico 2.1.1 has the same rules. No page of the site
  has such an element; only `color-schemes.html:59`, `:61` and `:77` repeat the README. Question:
  fix femto's CSS (for example a scheme token for the filter, set on every `[data-theme]` element),
  or qualify README lines 212 and 216?
- **The not-allowed cursor** (content-a-3, content-b-5, minor). README line 113: `disabled` and
  `aria-disabled="true"` give "A not-allowed cursor". CSS: `cursor: not-allowed` is set
  (`css/utilities/accessibility.css:11-14`). But disabled buttons (`css/components/button.css:159-163`),
  and disabled inputs, selects, textareas and `label[aria-disabled=true]`
  (`css/forms/basics.css:139-146`), get `pointer-events: none`. The pointer then reaches a parent
  whose cursor is `auto`, so the cursor shows only on aria-disabled links, buttons and
  `[role=button]`, and over a disabled fieldset. The aria-disabled label computes `cursor: pointer`
  (`css/forms/checkbox-radio-switch.css:6-9`). Pico 2.1.1 has the same rules, and `classes.html:252`
  repeats the README. Question: narrow README line 113 to what happens, or change femto so the
  cursor shows?
- **Right-to-left form field icons** (content-b-1, major). README line 115: `dir="rtl"` mirrors "the
  form field icons". CSS: `textarea[aria-invalid] { background-position: top right 0.75rem
  !important }` (`css/forms/basics.css:226-230`) outranks the RTL rule at `:186-188`. So a textarea's
  valid or invalid icon stays at the top right, over the text, while the padding kept for it moves
  to the left. `rtl.html:11` and `classes.html:289` repeat the README. Question: add a
  `[dir=rtl] textarea[aria-invalid]` rule to femto, or leave textareas out of the README's sentence?
- **`dist/femto.min.css`'s size** (content-a-4, content-c-5; Phase 4's item). README line 131:
  "about 74 KB, 11 KB gzipped and 10 KB with Brotli". The vendored file is 78,259 bytes, 11,746 to
  11,833 gzipped (by tool and level) and 10,301 with Brotli: about 78, 12 and 10 KB. The README's
  numbers are an earlier commit's (73,627 bytes at 9d4c2610), and `files.html:47` repeats them.
  Question: should femto's README say about 78 KB and 12 KB gzipped?
- **A select with `size="1"`** (content-b-7's chevron part, nit). `select:not([multiple], [size])`
  (`css/forms/basics.css:203`, `:218`) drops the chevron for any select with a `size` attribute.
  So `<select size="1">`, still a one-row drop-down, has no chevron and, with `appearance: none`, no
  native arrow either. The site now says "a size above 1" and nothing about `size="1"`. Question:
  should femto keep the chevron there?

femto's CSS defects that no README sentence describes, for femto's owner:
- **Focus in forced colors** (a11y-4, major). femto draws focus only as a box-shadow, with `outline:
  none` on links, buttons, inputs, selects, switches, range, file inputs and dropdown summaries.
  Forced colors removes box-shadows: in Firefox none of these changes a pixel when focused, and in
  Chrome links, the switch, range and the dropdown summary show nothing and buttons barely change. A transparent outline beside each ring, which forced colors paints, fixes it; the
  site's own rules do this from Phase 6 (a11y-5).
- **Tooltip text in names** (a11y-10, minor). `[data-tooltip]::before { content: attr(data-tooltip) }`
  joins the accessible name of an element named by its content: a tooltip button "Top" is named
  "Top Top", and a labelled switch takes its helper text. It was the cause of a11y-1. femto could
  say so in its README, or use `content: attr(data-tooltip) / ""` once that is Widely Available
  (January 2027).
- **The range input's focus** (a11y-11, minor). `[type=range]` draws no ring: focus only switches the
  thumb and track to their active colors (`css/forms/input-range.css:47-50`), 1.16:1 to 1.32:1
  against the unfocused pixels. The rest of a11y-11 is Phase 4's item on the focus-ring tokens
  (1.4:1 to 2.0:1; amber's 1.65:1 lies inside it).

**The owner's Safari steps for Phase 6** (Owner's Safari steps). Criteria 1, 2 and 7's Safari
results wait on them, on the Phase 6 commit:
- `tests/owner-safari.sh final`, Reduce Motion off: `p6-behavior-safari-light-1` and `-dark-1`,
  `p6-self-safari-light-1` and `-dark-1`, `p6-loads-safari-light-1` and `-dark-1`. About 1 h 25 min.
- `tests/owner-safari.sh reduced`, with Reduce Motion on: `p6-behavior-safari-reduced-light-1`.
  About 2 minutes. Then turn Reduce Motion off.
- `tests/owner-safari.sh parity`, Reduce Motion off: `p6-styles-safari-light-1` and `-dark-1`,
  `p6-sections-safari-light-1` and `-dark-1`, `p6-pages-safari-light-1` and `-dark-1`. About 2 h
  40 min.

A rerun takes the next number (`final 2`). Each light run's log must say `OS scheme light`, each
dark one `OS scheme dark`, and the motion as above.

**The owner's open questions.**
- The Cloudflare steps above, and whether Web Analytics stays (criterion 15).
- femto's items above.
- rr-site-5: the spy's take-over keeps a `wheel` listener beside `keydown` and touch `pointerdown`.
  `wheel` is Baseline limited (Safari on iOS never fires it) and has no Widely Available
  substitute; its reason is only in `docs.js`'s comment. Does Decision 12's "uses nothing outside
  the target" allow a listener that complements Widely Available ones? If so, it belongs in
  PLAN.md once; if not, the listener goes.
- rr-docs-4: Decision 5 ends "Nothing is live, so nothing needs redirecting", and production has
  been live since 2026-11-06. The conclusion holds, since none of the dropped pages was ever served
  at `femto.style`. Leave it as dated text, or reword its last sentence?
- css-3's optional question: eslint-plugin-baseline-js's type-aware preset would see instance
  members, but it needs TypeScript, beyond PLAN.md's Repo changes.

**Not verified here.**
- **Safari.** No Safari run was made in Phase 6. The Safari paths were checked only with stand-ins:
  - `run_one` with fake Safari page and session objects (the motion skips and the refusal);
  - `tests/owner-safari.sh` with `osascript`, `caffeinate`, `pgrep`, `sleep`, `uv` and `npm`
    stubbed (run ids, the folder guard, the motion stops, the restored appearance, the reminder).

  Nor seen in Safari:
  - whether safaridriver answers WebDriver Get Computed Label, which `copy-button`,
    `color-modal-tab-cycle` and the two progress checks use;
  - `document.fonts.load()`'s refit in WebKit (only the review's `race.py` emulation);
  - whether the copy check's pop-in finishes in a visible window (Decision 18's record).

  Also unseen: `focus()` scrolling on Chrome Android and Samsung Internet (only Chrome's CDP mobile
  emulation, where a bare `focus()` jumps 415 px and the new refocus does not), real touch input
  (only synthetic `PointerEvent`s), and forced colors other than Firefox's
  `browser.display.document_color_use` and Chrome's CDP emulation.
- **Production after the owner's steps.** Nothing here shows the live site once the build settings
  are fixed: the hashes, the headers and the beacon are the owner's rechecks above.
- **Pages' Node.** `.node-version` names 26.13.0, and build system v3 should read it in place of its
  default, 22.23.4. Only the first build log shows which Node Pages used, and whether the
  devDependencies, `prismjs` among them, were installed.
- **`/DOCS` on production** (urls-6). Under `wrangler pages dev` on this Mac, `/DOCS`, `/Docs`,
  `/docs.HTML` and `/EXAMPLES` answer 200 with the page (Rig notes, the site's server). Whether
  Cloudflare Pages matches paths in a case-sensitive way was not checked; the head script and the
  picker show azure there either way (urls-5).
- **The fallback paths no check reaches** (critic-11):
  - a theme stylesheet that fails to load, after which the picker loads the swatch's URL instead
    (`picker.js:233` and `:258`);
  - the typing demo and the Progress example pausing when reduced motion turns on while the page is
    open (`demo.js:709`, `docs.js:618`; `demo-reduced-motion` and `progress-reduced-motion` load
    under it);
  - a color-scheme choice that storage refuses, which holds for the page (`site.js:106-108`);
  - a stored value that is not JSON (`partials/head.html:45`, `site.js:58`; `theme-stored-invalid`
    stores `'"blue"'`, which is JSON);
  - the code blocks' refit once Fira Code has loaded, when it arrives after the first check
    (`site.js:273`).
- **The lint's blind spots** (css-3, css-4; Lint): instance members, event names built at run time
  and computed option keys; the `<style>` and `style=""` sources, which `use-baseline` never reads;
  and the six places site JS writes CSS. All were checked by hand in Phase 6, not mechanically.
- `copy-button` against the oracle fails since the icons changed (Behavior, Expected failures), and
  no full oracle run of the behavior suite was made after Decision 17.
- Phase 5's GitHub check items for a `pull_request` run (GitHub's merge commit) still hold.

**Phase 5's "Not verified here", answered** (critic-14). `/_headers` answers 404 on `femto.style`
and on `femto-style.pages.dev`, and the fonts carry `public, max-age=31536000, immutable`, so Pages
reads `_headers` as configuration from the Git integration's deploy too (a deploy of `site/`, which
holds the same `_headers`). The GitHub check ran on GitHub's own runner: the workflow Check passed on
`76d0e92` on `dev` (22:26:14Z) and `main` (22:33:50Z, 2026-11-06).

### Known Phase 1 deviations

What Phase 1 ships differently from the oracle or from PLAN.md's letter, each on record here so that a
later phase or the owner picks it up. Registry entries name the pages-mode differences; these are the
rest, and the registered ones with a consequence a later phase owns.

| Item | What | Owner |
|---|---|---|
| The 404 page's footer | Without the banner, main.css's `auto auto 1fr auto` body rows give the footer the free space: on the 404 page at 800 to 1300 px it sits 43 to 100 px higher, with blank space under it, and so would any page shorter than a taller window (p1-shell-404-footer-track). | Settled in Phase 2: `common.css` writes the rows `auto 1fr auto` (p2-common-body-rows) |
| Six footer links on `/docs` | The About column's five items and Class-less version point at `/docs` (PLAN.md Text: removed or pointed at `/docs`), so on `/docs` they carry `aria-current="page"` and a screen reader hears each as the current page (p1-shell-footer-dropped-links-current). Kept so the footer's columns and height stay the oracle's. | Settled in Phase 4: the footer's three columns link only real places; its one `/docs` link is Quick start, the top of the page |
| woff fallbacks | The frozen `main.css` names 10 `.woff` fallbacks under `/assets/fonts/` beside the woff2 files; only woff2 ships (PLAN.md File tree), so those URLs answer 404. Every target browser takes the woff2. | Settled in Phase 2: `fonts.css` names woff2 only, and `assets/legacy/` is gone |
| Pacifico on `/docs/css-variables` | The oracle loads Pacifico from Google Fonts; the static page links `/assets/legacy/pacifico.css` (menu.json `styles`), Google's stylesheet with its 5 `src` URLs pointed at the same woff2 files, byte-identical to the captured ones (`tests/oracle/capture/_fonts`), so the page loads only same-origin resources (criterion 15). The pages mode skips stylesheet links (head comparison), so this is the one stylesheet whose origin changed without a record. | Settled 2026-10-31, the owner keeps it: PLAN.md's File tree lists Pacifico 400, Phase 2's `fonts.css` took its `@font-face` rules (menu.json no longer links a stylesheet for it), and Phase 4 keeps the example |
| React text separators | Two section files keep React's `<!-- -->` separator (`color-schemes.html`, `version-picker.html` and its 19 colors: 22 copies in `dist/`), for a sub-pixel label width (tests/convert/README.md). PLAN.md's Conversion rules strip them. | Kept through Phase 3: removing them brought the sub-pixel width back in Chrome only (196 unregistered records in 46 of 1,368 cells, `p3-review-behavior-3-sections-full-1`: color-schemes' two "Remember me" labels at 1100 and 1300, 180.359 against 180.375 px, and "I agree to the" on the version picker and its 19 color routes at 1300, 299.859 against 299.875 px), which no category covers. `color-schemes.html` (two) and `version-picker.html` (one) carry the explained separator again, as at `static-femto` (`p3-registry-separator-probe-1` passes with them); `dist/docs.html` has three. Settled in Phase 4, where parity no longer binds: removed, and `dist/docs.html` has none |
| Per-route build scaffolding | In per-route mode `build.mjs` also swaps literal markup in `docs.html` per route (the `<main>` class, the breadcrumb's chapter, the Close link, canonical, `og:url`), fills two slot comments (`<!-- docs:menu -->`, `<!-- docs:sections -->`) and adds route stylesheets; `menu.json` carries `route`, `label`, `routeTitle`, `toc`, `styles` and `variants` beyond the File tree's id, title, description. PLAN.md allows only the include markers and three placeholders. | Settled 2026-10-31, accepted as scaffolding for Phases 1 and 2 (PLAN.md File tree, Per-route scaffolding). Settled in Phase 3: `build.mjs` has no slot comments or per-route swaps, and `menu.json` keeps only id, title, description and label |
| The palette download | 01 §2 and 03 §5 plan a static JSON file written by the build; Phase 1's `colors.js` makes an on-load `blob:` URL, for parity with the oracle's (normalized by the `blob:` value rule). No phase owns the switch. | Settled 2026-10-31: Phase 3 switches to the build's static JSON file (PLAN.md Workflow) and registers the URL as `asset-path`. Done in Phase 3: `build.mjs` writes `assets/femto-color-palette.json`, the Download link points at it, registered as p3-colors-palette-download |
| File tree extras | `site/partials/` holds `docs-header.html`, `logo.html`, `nav-icons.html` and `structured-data.html` beyond head, header and footer; the root holds `vendor.mjs` and `eslint.config.js`; `site/docs/sections/version-picker/<color>.html` are 19 per-route files. `.prettierrc` names a plugin no longer installed, `robots.txt` is absent, and `site/_headers` still caches `/build/*`. | Settled 2026-10-31: PLAN.md's File tree lists the extra partials, `vendor.mjs`, `eslint.config.js` and the color files; Phase 3 deletes the color files (done: `site/docs/sections/version-picker/` is gone), Phase 5 the rest. Settled in Phase 5: `.prettierrc` keeps only `printWidth` 100, `site/robots.txt` allows every crawler and names `https://femto.style/sitemap.xml`, and `site/_headers` caches only `/assets/fonts/*.woff2`, for a year (`immutable`); the `/build/*` rule is gone |
| Pages-inherent paths | `/404` answers 200 (the 404 page), and `/404.html`, `/index`, `/index.html`, `/docs/index` and a page's `.html` name redirect (Cloudflare Pages' pretty URLs). Criterion 6 says any other path answers 404; `static_checks.py` probes these and lists them as notes (`PAGES_INHERENT`). | Settled 2026-10-31: accepted in PLAN.md Risks (Cloudflare), and criterion 6 exempts them |
| Early widget fixes | The color modal's focus and Tab handling, the swatch focus and the restored font-size switch (Behavior, Expected failures). | Settled 2026-10-31: confirmed (PLAN.md, Conversion rules, JavaScript) |
| `<body style="min-height:100vh">` | The oracle's server HTML had it, so the static pages do (round 1 of the fixes, PH-7); site.js still sets innerHeight in px. html-validate's `no-inline-style` reports it on every page (criterion 9). | Settled in Phase 3: no page's `<body>` carries the attribute, and dropping it changed nothing on the five pages (p3-validate-pages-body-1: 64 cells, 0 differences) |
| Escape on the mobile menu | Not in Phase 1, as in the oracle (01 §2: no Escape); an earlier Phase 1 `docs.js` closed it on Escape, which round 1 of the fixes removed. | Settled in Phase 3: `docs.js` closes the menu on Escape and gives focus back, checked by `mobile-menu-focus` (p3-review-site-r2-behavior-1 and p3-review-behavior-2-behavior-1, Chrome and Firefox) |

### Owner's Safari steps

`tests/owner-safari.sh` runs them, and only the owner runs it, since it switches macOS's appearance
(to Light, then Dark) and puts back the one it found, even when stopped with Ctrl-C. Quit Safari
(Cmd-Q), unlock the screen and leave the Mac alone until it prints `done`. From Phase 6 it has four
modes. Each refuses to start when a result folder it would write already exists, and names the
next free run number, so a rerun never overwrites a pass's evidence; `N` (default 1) numbers the run
ids, as in `tests/owner-safari.sh final 2`:

```sh
tests/owner-safari.sh final      # criteria 1, 7 and 15's Safari legs at this commit, Reduce Motion off: about 1 h 25 min
tests/owner-safari.sh reduced    # criterion 7's prefers-reduced-motion checks, Reduce Motion on: about 2 minutes
tests/owner-safari.sh parity     # criterion 2's Safari legs, rerun between the tags, Reduce Motion off: about 2 h 40 min
tests/owner-safari.sh spike      # the spike alone, on whichever appearance is set: about a minute
```

- **`final [N]`** builds `dist/`, then in Light and again in Dark runs three steps. Each pass runs
  the OS scheme's leg and both theme legs, and skips the other leg as `media:<scheme>`, which the
  other pass runs.
  - The behavior suite, `behavior --target dist --browsers safari --expect-os-motion no-preference`,
    as `p6-behavior-safari-<scheme>-N` (criterion 7). The script stops here unless the run's
    `log.txt` says `OS motion no-preference`.
  - The oracle against itself over the full matrix, `self --full --browsers safari`, as
    `p6-self-safari-<scheme>-N`: 420 of Safari's 744 cells per pass (criterion 1, on the current
    harness; critic-6).
  - Criterion 15's run-time loads, `pages --a dist --b dist --full --routes
    '/,/docs,/docs?theme=jade,/examples,/does-not-exist' --browsers safari`, as
    `p6-loads-safari-<scheme>-N`: 54 of 84 cells per pass.

  The estimate comes from earlier passes: the behavior suite took 411 s in Light and 12 s in Dark
  (`p4-behavior-safari-light-2`, `-dark-2`). A dark `self --full` pass took 1,548 s
  (`p0-self-safari-dark-masked`). A light one took 1,072 s without `/docs/css-variables`
  (`owner-self-safari-light`), plus 1,178 s for that route's six light cells
  (`p0-self-safari-light-cssvars`).
- **`reduced [N]`** is owner decision 19. Turn macOS's Reduce Motion on first (System Settings >
  Accessibility > Display > Reduce motion). It builds `dist/` and runs the behavior suite in Light
  only, `behavior --target dist --browsers safari --expect-os-motion reduce`, as
  `p6-behavior-safari-reduced-light-N`. It runs the checks whose `motion` is `reduce`, which the
  `final` passes skip: `demo-reduced-motion`, `spy-nav-click-reduced` and
  `progress-reduced-motion`. Every one of them is a light check, so a Dark pass would run none
  (rr-tests-3). Every other check is skipped, as `motion:no-preference` (the `final` passes run
  it) or as `media:dark`. The script stops unless the log says `OS motion reduce`, and it always
  ends by reminding you to turn Reduce Motion off again.
- **`parity [N]`** is owner decision 18, criterion 2's Safari legs of the Phase 2 and Phase 3 gates.
  It reruns them on the current harness between the commits the gates compared, in Light and again
  in Dark. It builds nothing itself: the harness builds the tags into `tests/builds/`.
  - Phase 2's gate, `styles --full --a static-multipage --b static-femto --browsers safari`, as
    `p6-styles-safari-<scheme>-N`: 420 of 744 cells per pass. The script stops after it unless its
    log says `OS motion no-preference`; a comparison session refuses Reduce Motion anyway (Known
    limits).
  - Phase 3's gate, `sections --full --a static-femto --b static-one-page --browsers safari`, as
    `p6-sections-safari-<scheme>-N` (384 of 684 cells), then `pages --full --a static-femto --b
    static-one-page --routes /,/examples,/demo,/does-not-exist --browsers safari`, as
    `p6-pages-safari-<scheme>-N` (36 of 60).

  The styles passes took 1,910 to 1,936 s (`p2-styles-safari-*-2`). The section comparison has
  never run in Safari: Phase 3 estimated about 45 minutes a pass, the six `/docs/css-variables`
  cells among them. Chrome and Firefox ran the same three commands in Phase 6 with every total equal
  to the gates' (Harness proof, Phase 6). In Safari, the styles comparison relies on
  `p2-safari.json`'s 19 entries, which were replayed offline against `p2-styles-safari-*-2` but
  never run there, so a Safari-only difference may still need an entry.
- **`spike [N]`** runs only the spike, into `results/p6-spike-safari-N.txt`, and leaves the
  appearance as it is.

At the end the script prints, for each run, how often its `log.txt` says `OS scheme light` or
`OS scheme dark` and `OS motion reduce` or `OS motion no-preference`. The light runs must say light
and the dark runs dark. `final` and `parity` must say `no-preference`, and `reduced` must say
`reduce`. A run whose log has no OS motion at all started no Safari session, and the script stops
saying so, with no Reduce Motion advice: the run's HARNESS ERRORS give the cause (on 2026-11-07
`p6-behavior-safari-light-1` timed out waiting for safaridriver to launch Safari). A dark run's
skipped checks are `media:light`. Each step is one command under `caffeinate
-d -i`, so one can also be run by hand. The behavior suite and the styles mode's state replays need
the automation window in front the whole time. Criteria 1, 2 and 7's Safari results wait on these
three modes, and the owner's other steps are outside the repository (Harness proof, Phase 6).

**Historical modes.** The script's earlier modes now refuse to run (exit 2) and say what each ran.
They compared HEAD's `dist/` with the tags, which cannot pass from Phase 4, or they would write the
earlier phases' run ids again (critic-7). With no argument it ran the spike (into
`results/p0-spike-safari.txt`, for `docs/research/05-spike.md`), `rig` with its input checks, the
six light `/docs/css-variables` cells, the dark self pass over every kept route and the three
selftest controls that compare on a dark OS: about 70 minutes. `dark` ran only the dark self pass,
as `p0-self-safari-dark-masked`: about 26 minutes. `spike` wrote `results/p0-spike-safari-2.txt`
until Phase 6. `styles` was Phase 2's gate (criterion 2) in Safari: it built `dist/`, which the
harness serves as it finds it, then ran `styles --full --browsers safari` in Light as
`p2-styles-safari-light-3` and in Dark as `p2-styles-safari-dark-3`, which were never run. Each run
compares 420 of Safari's 744 cells, the OS scheme's leg and both theme legs, and the two together
cover all 744. The earlier pairs, kept as Phase 2's record, took 1,936 s and 1,922 s
(`p2-styles-safari-light` and `-dark`) and 1,935 s and 1,910 s (`-2`). `one-page` was Phase 3's gate
in Safari (criteria 2 and 7): it built `dist/`, then in Light and again in Dark ran the behavior
suite (as `p3-behavior-safari-light-1` and `-dark-1`), the full section comparison (`sections
--full --browsers safari`, as `p3-sections-safari-light-1` and `-dark-1`: 384 of Safari's 684 cells
per pass) and the whole pages (`pages --a static-femto --b dist --full --browsers safari --routes
/,/examples,/demo,/does-not-exist`, as `p3-pages-safari-light-1` and `-dark-1`: 36 of 60 cells per
pass); it was never run. `content` was Phase 4's gate in Safari (criterion 7): it built `dist/`,
then in Light and again in Dark ran only the behavior suite, as `p4-behavior-safari-light-2` and
`-dark-2` (`-1` was the first pass, Phase 4 record): 411 s in Light and 12 s in Dark, which runs only
the dark checks. Measured on an unlocked screen: dark self passes of 1,555 s and 1,548 s
(`p0-self-safari-dark`, `p0-self-safari-dark-masked`), and about 190 s for each
`/docs/css-variables` cell (closed `<details>` style recompute).

### Owner decisions and questions

1. **The `blob:` URL on `/docs/colors`**: settled 2026-10-30. The owner chose to normalize it, so
   the placeholder rule is the default (Diff rule); `--exact-blob-urls` turns it off.
2. **Which femto commit `SOURCE` names.** Settled 2026-10-30: the owner chose the latest commit on
   femto's `dev` for now, e3b141f3 ("Remove Composer Package", 3.0.0-alpha.1), vendored with
   `npm run vendor -- ../femto e3b141f3472a2860d1d8a50d23f313e64872d122`. Criterion 14 now allows
   everything under `site/vendor/femto/`, whose stylesheets carry femto's Pico copyright banner.
   Moved 2026-10-31: the owner chose the latest commit on femto's `main`, 7bcd5758 ("Register
   Safari-Only Computed Values From The Bug Fixes", still 3.0.0-alpha.1), vendored with
   `npm run vendor -- ../femto 7bcd57582671b2a8d2dcf15747e9ab851ce20b93`. It changes 14 files in
   `css/` and `dist/femto.css` and `femto.min.css`; `femto.colors.css`, the themes and `LICENSE.md`
   are unchanged. Moved 2026-11-03: the owner chose femto's latest commit, d4f8d1fd ("Add Android
   Browsers", on `dev` and `main`, still 3.0.0-alpha.1), vendored with
   `npm run vendor -- ../femto d4f8d1fd`. It changes only a comment in `css/forms/input-date.css`.
   Moved 2026-11-04, before Phase 4: the owner chose femto's latest commit, 8cd05767 ("Add A Script
   For Both Safari Passes", still 3.0.0-alpha.1), vendored with `npm run vendor`. Its only change to
   the vendored files is 1f7c75b2's "Drop The Bottom Margin On Typed Modal Footer Buttons"
   (`css/components/modal.css` and `dist/femto.css` and `femto.min.css`). Moved 2026-11-05, during
   Phase 4: c608ee06 ("Darken Dark Hover Backgrounds For Contrast", on femto's `dev`, still
   3.0.0-alpha.1), vendored with `npm run vendor`. It changes `css/tokens/schemes.css`, nine theme
   files and `dist/femto.css` and `femto.min.css` (owner decision 15). Moved 2026-11-05, during
   Phase 5: the owner amended c608ee06 into 33d4dc6f ("Darken Dark Hover Backgrounds For Contrast",
   on femto's `dev` and `main` and pushed to GitHub, still 3.0.0-alpha.1), so c608ee06 is on no
   branch, and the site was vendored at 33d4dc6f with `npm run vendor`. Its only change to the
   vendored files drops the one-line comment above `--femto-primary-hover-background` in
   `css/tokens/schemes.css` and the same nine theme files; `dist/` is unchanged. The GitHub check
   fetches this commit (PLAN.md Risks, femto's working tree).
3. **`.gitignore`**: settled 2026-10-30. It reads `/dist/`, so `site/vendor/femto/dist/` is no
   longer ignored.
4. **PLAN and its sources disagree** in four places the static checks had settled silently. All
   four are settled:
   - Criterion 5 and the frozen legacy CSS in `dist/` during Phase 1: PLAN.md's Workflow (Phase 1
     gate) exempts `site/assets/legacy/` until Phase 2, as `static_checks.py` does.
   - The package name: `@leoherzog/femto` for now (PLAN.md Decision 4, the owner, 2026-10-30).
   - Criterion 15's `/docs` budget: settled 2026-10-31. Phase 3 records it in the form the check
     reads, the first sentence in PLAN's Risks that says "budget" and gives sizes after it (PLAN.md
     Risks, Page size).
   - Criterion 9's html-validate config: settled 2026-10-31. Phase 3 adds `.htmlvalidate.mjs`
     extending `html-validate:recommended`, fixes the real errors (the 22 duplicate ids with
     Decision 13's renames) and turns off only rules that conflict with a deliberate choice, each
     with its reason (PLAN.md criterion 9 and Workflow). At Phase 1 the defaults report 1,208
     errors in 54 files, most of them `no-implicit-button-type` (423), `unique-landmark` (327),
     `wcag/h30` (159), `wcag/h71` (73) and `no-inline-style` (58).
5. **The JS compat lint** (PLAN Repo changes, "if one fits"; 03 §7, "Phase 0 checks"): on
   2026-10-30 eslint 10.14.0 is current, and both eslint-plugin-compat 7.0.2 (peer eslint ^9 ||
   ^10, browserslist targets) and eslint-plugin-baseline-js 0.7.6 (peer eslint >=9.29 <11, Baseline
   targets, published 2026-10-26) fit. `static_checks.py` accepts eslint-plugin-baseline-js
   (`COMPAT_LINT`), since Decision 12's target is Baseline Widely Available, and no other plugin;
   confirm, or change that constant.
6. **Old wrangler logs.** `~/Library/Preferences/.wrangler/logs/` holds about 1.5 GB of debug logs
   from 2026-10-30, written before the harness redirected them: the oracle servers' and 7 files
   from static check 6's temporary folders. Delete them if they are not wanted; agents did not.
7. **Raised by round 1 of the Phase 1 fixes** (2026-10-31). All settled the same day:
   - `dropped-route` now covers anything Decision 5 drops and its layout effects (PLAN.md,
     Divergence categories), so the maintenance banner, the homepage Stats and the heights and
     tracks they change fit its wording.
   - The data-block copy rule is accepted as it is, on both sides (PLAN.md Parity harness,
     "Counted once").
   - The early widget fixes are confirmed (PLAN.md, Conversion rules, JavaScript).
   - The Known Phase 1 deviations above: Phase 3 takes the palette download's JSON file; the
     per-route scaffolding, the extra partials and scripts, and the Pages-inherent paths are
     accepted (PLAN.md File tree, Per-route scaffolding, and Risks, Cloudflare).
8. **The theme toggle icon** (2026-11-01). The light Safari self pass found the oracle differing
   from itself on its animated toggle icon: in the theme-dark leg React adds `moon` after
   hydration, and Safari 27.2 can start the icon's 260 ms transform transition after the freeze
   (`p0-self-safari-light-locked`: 36 transform records in 18 cells, and 6 harness errors on
   `/docs/forms/input`; reproduced in `p0-self-safari-light-themedark-recheck`). The owner chose to
   replace the icon rather than keep it: PLAN.md Decision 16, a sun or moon emoji drawn in the
   text color by `site/assets/css/common.css`, registered in `divergences/owner.json`
   (`owner-change`, a new category), with the oracle's icon animation masked (Masks,
   `oracle-theme-toggle`) and the freeze counting a masked element's animations apart.
9. **The maintenance banner's link** (2026-11-01). The dark Safari self pass found the oracle
   differing from itself on the banner link's colors in one cell (`p0-self-safari-dark`,
   `/docs/link` dark 375): the banner's inverse `data-theme` is set after hydration, and Safari read
   the link's color transition part way. The owner chose to mask the link's colors (Masks,
   `oracle-maintenance-notice`) over making the oracle's readiness wait for its theme effect; the
   site drops the banner (PLAN.md Decision 5).
10. **Safari's reload in the spike** (2026-11-02). In Safari 27.2 `location.reload()` returns to the
   `#hash` section's heading rather than the exact position. The owner accepted it, as Chrome's
   back already is, and the spike's reload check now passes on either. The Quick start check reads
   the heading on the scroll-padding line instead of the page's y, which depends on the padding
   (`docs/research/05-spike.md`).
11. **The oracle minifier's spellings** (2026-11-02). Phase 2's styles gate found 675,780 records
   that differ only in how clean-css wrote the oracle's values (`.25rem`, `outline:0`,
   `background:0 0`), which no PLAN category covered. The owner chose a value rule over a new
   category (Diff rule), so the site's CSS writes its own values normally (`0.125rem`).
12. **Criterion 10 in Phase 3** (2026-11-04). axe-core's violations on `/docs` all come from the
   oracle's markup or femto's tokens, which parity keeps through Phase 3. The owner moved criterion
   10 to Phase 4's gate rather than fix them now (PLAN.md Workflow); Accessibility lists them.
13. **The `?theme=` first paint in Firefox** (2026-11-04). With one inline head script, Firefox paints
   femto's default color before the `document.write` theme `<link>` arrives: it holds its first
   paint only for a stylesheet that a later parser-blocking script waits on (a Phase 3 probe in
   headless Firefox 160, with the server holding `jade.css` 300 ms: a static inline script after the
   theme script moves the first contentful paint from 80 to 277 ms (before the theme's responseEnd)
   to 455 to 588 ms (after it); a script that `document.write` adds after the `<link>` does not). The owner chose two inline head scripts, the `?theme=` one first and the
   color-scheme one second (PLAN.md Decisions 8 and 14, criterion 15).
14. **The `/docs` size budget** (2026-11-05). With Phase 4's nine new sections and femto 3's text,
   `dist/docs.html` is 806,898 bytes raw, 63,085 gzipped and 41,990 with Brotli, over Phase 3's 60 KB
   and 40 KB. The owner raised those two limits to 70 KB and 48 KB rather than trim the page, for
   example by building the Colors section's 380 swatches from JSON, which would save about 4 KB
   (PLAN.md Risks, Page size).
15. **femto's dark hover color** (2026-11-05). Criterion 10's last failure was the Group example's
   current button in dark: white on `#017fc0`, 4.37:1 (jade's `#00895a`, 4.44:1). It comes from
   femto's `--femto-primary-hover-background`, whose dark value gave white text less than 4.5:1 in 9
   of the 20 themes (azure, blue, cyan, fuchsia, green, jade, orange, pink and zinc; green 3.76:1),
   on every hovered, focused, pressed or current button. The owner chose to fix it in femto, rather
   than record an exception or change the example. femto's c608ee06 gives those nine themes their
   light value in both schemes (5.41:1 to 6.54:1), registered in femto's own divergences, and the
   site vendors it (owner decision 2), since 2026-11-05 as 33d4dc6f, the amended commit.
16. **Decision 11, hosting by Git** (2026-11-06). Cloudflare Pages' Git integration replaces direct
   upload. The Pages project `femto-style` is connected to GitHub's `leoherzog/femto.style`:
   pushing `main` deploys production (`https://femto.style` and `https://femto-style.pages.dev`),
   and pushing any other branch deploys a preview. The `deploy` script is removed, so criterion 4's
   scripts are `build`, `dev`, `vendor` and `lint`, and `static_checks.py` fails a script that runs
   `wrangler pages deploy` or `publish` (PLAN.md Decision 11, criterion 4). The build settings live
   in the dashboard, which is the owner's (Harness proof, Phase 6, the owner's steps outside the
   repository).
17. **The copy buttons' names** (2026-11-06). Each copy button is named by `aria-labelledby`
   pointing at its icon's id, so femto's tooltip text no longer joins its name (a11y-1). Decision
   18's text stays: the `aria-label` stays on the icon. site.js gives the icons their
   `copy-icon-<n>` ids, since the buttons work only with JavaScript.
18. **Criterion 2's Safari legs** (2026-11-06). The owner reruns the Safari legs of the Phase 2 and
   Phase 3 gates between the commits those gates compared, with a new `tests/owner-safari.sh` mode,
   `parity`: `static-multipage` against `static-femto`, and `static-femto` against the new
   `static-one-page` (Owner's Safari steps).
19. **Reduce Motion in Safari** (2026-11-06). The harness reads Safari's OS `prefers-reduced-motion`,
   as it reads the OS scheme, and the owner runs one more Safari pass with macOS's Reduce Motion on:
   `tests/owner-safari.sh reduced` (Behavior, Safari).
20. **Live before femto's first npm publish** (2026-11-06). Production went live from `main` before
   `@leoherzog/femto` was published, so the docs' jsDelivr and npm instructions for the alpha fail
   until then (repo-4, content-c-2). The owner chose no site change: the docs keep following femto's
   README (PLAN.md Risks, femto is alpha and unpublished).
21. **Local tags** (2026-11-06). The parity tags name the commits the gates used again, as this file
   and `tests/harness/targets.json` say: `remix-final` 507dcda, `static-multipage` 9383e6b and
   `static-femto` 7587a7e, recreated (critic-4 found the last two at de65ccf and f2f2351). A new tag,
   `static-one-page`, names 7b90883, Phase 3's gate commit ("Merge Docs Into One Page"), for the
   Safari parity rerun. 7587a7e has the same `site/` as 17ec97d, Phase 2's Safari follow-up; only
   `README.md` differs. The tags are local and not pushed.
