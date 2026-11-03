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
uv run tests/run.py fast --a oracle --b dist --routes /docs/forms,/docs/forms/input   # a route group agent's check
uv run tests/run.py fast --a oracle --b dist:build/forms --routes /docs/forms   # an agent's own build folder
uv run tests/run.py pages --a oracle --b dist --full      # a parity gate (criterion 2)
uv run tests/run.py styles --full                         # the Phase 2 gate: static-multipage against dist, tokens and states
uv run tests/run.py styles --b dist:build/p2 --routes /docs/button   # an agent's own build, fast axes
uv run tests/run.py registry                              # validate tests/divergences/
uv run tests/run.py oracle                                # build, serve and capture the oracle
uv run tests/run.py static                                # the static checks
uv run tests/run.py behavior --target oracle              # the behavior suite (tests/behavior/), Chrome and Firefox
uv run tests/run.py behavior --target dist --groups shell # one group against the static site
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
| `static_checks.py` | static | the mechanical acceptance criteria (`run.py static` calls its `main(argv)`) |
| `divergences/` | harness (schema, rig seed); phase agents add entries | divergence registry, `schema.json` |
| `fixtures/` | harness | the selftest site (`site/`), its named controls (`controls.json`) and its state targets for the styles controls (`states.json`) |
| `harness/states.json` | harness | the styles mode's interactive state targets (Tokens and states) |
| `behavior/` | behavior | the behavior suite: `__init__.py` (the `@check` registry and shared in-page helpers) and one module per route group (`shell.py`, `getting-started.py`, `customization.py`, `layout.py`, `content.py`, `forms.py`, `components-a.py`, `components-b.py`, `landing.py`); see Behavior |
| `harness/behavior.py` | behavior | the `behavior` mode: its subcommand, the page API checks drive, sessions, runner and report |
| `oracle/`, `results/`, `builds/` | generated | gitignored; `builds/<tag>/` holds a tag's build (`harness/tagbuild.py`) |

Python modules in `harness/`: `cli.py` (modes and the planner), `matrix.py` (legs, widths, routes,
cells), `targets.py` (sides, their servers and readiness hooks), `proxy.py` (the per-session reverse
proxy), `server.py` (the fixture server), `runner.py` (worker pool and session start-up),
`compare.py` (one cell, pixel diff), `browsers.py` (drivers and the color-scheme and input
mechanisms), `registry.py`, `report.py`, `negative.py` (selftest), `rig.py`, `locks.py` (femto's,
unchanged), `paths.py`, `behavior.py` (the behavior mode; Behavior), `styles.py` (the styles mode's
tokens and state replay; Tokens and states), `tagbuild.py` (a tag of this repository built for a
target such as `static-multipage`).

## How one comparison works

A **cell** is one comparison: browser × route × scheme leg × width. Side A's document is
`<base A><route>` and side B's is `<base B><route>`.

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
   the route and waits for its `load` event. From the load until the readiness hook returns, the
   host page requests an animation frame every frame (see Rig notes, Chrome: idle periods).
4. The side's **readiness hook** runs: `oracle` (`oracle.wait_ready(driver)`, run inside the iframe:
   the Remix router initialized, React attached to `<body>`, the `use100vh` effect run,
   `document.fonts.ready` resolved and two animation frames passed), `static` (the document is
   complete, `document.fonts.ready` resolved and two animation frames passed, with a 100 ms timer
   standing in for a frame where rAF never runs), or `none`. A side that is still not ready after
   30 s is loaded once more; the cell records the first attempt under `ready_retries`, and a second
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
whole-page one.
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

`harness/masks.json` holds the only masked areas, PLAN's five, and every run copies them into
`result.json` (`masks`) with the number of elements each covered (`masked_elements`, and per cell
under `sides`). A mask applies to an aligned element when its selector matches it on either side.
Masked parts are also left out of the alignment's subtree signatures.

| Mask | Selector | What is not compared |
|---|---|---|
| `spinner` | `[aria-busy=true]` | pixels only (its SVG animation cannot be frozen; its computed styles stay compared) |
| `typing-demo` | `.demo > article.component` | its contents: descendants and own text are not collected; the article's own attributes and styles (its height is fixed) stay compared; pixels covered |
| `progress-value` | `article[aria-label="Progress example"] > progress` | the `value` attribute; pixels covered |
| `progress-value-code` | `article[aria-label="Progress example"] > footer > pre > code > :nth-child(1 of .attr-value:not(.punctuation))` | the one token that prints the value (`value="NN"` comes before `max="100"`): its text, and the `transform-origin` and `perspective-origin` Firefox derives from its size. Every other token, its classes, the `pre` and the copy button stay compared. The screenshot covers the whole `pre`, since the digits shift the rest of the line |
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

Common options for `self`, `pages`, `fast` and `styles`: `--browsers chrome,firefox,safari`, `--routes`,
`--widths`, `--schemes light,dark,theme-light,theme-dark` (those legs on every route instead of the
matrix's legs), `--no-shots`, `--workers chrome=2,firefox=2`, `--max-records N`, `--run-id`,
`--label`, `--registry DIR`, `--exact-blob-urls` and `--exact-minified` (see Diff rule), and `--plan`
(print the planned cells per browser and exit, starting no server and no browser). `pages` and `fast` take `--a` and `--b` (a named target, `dist:<path>` or a base URL),
`--ready-a`/`--ready-b` (`oracle`, `static`, `none`) and `--root-a`/`--root-b` (CSS selectors of the
alignment roots, for Phase 3's section-against-route comparisons). Without `--routes` the routes
are the oracle's kept routes from `tests/oracle-routes.json`.

| Mode | What it runs |
|---|---|
| `rig` | Starts each browser (`--browsers`, default all three) and reports versions, pseudo-element support, the six widths, each scheme leg's mechanism, screenshot timing and input checks to `results/<run>/rig.json`. |
| `self` | The oracle against itself, from two separate oracle servers (`--one-server` for one). Fast axes; `--full` runs the full matrix (acceptance criterion 1). |
| `pages` | `--a` against `--b`. Fast axes; `--full` runs the full matrix (criterion 2 at each parity gate). Phase 1 runs `pages --a oracle --b dist`. |
| `fast` | For agents: Chrome and Firefox at widths 375 and 1300 (PLAN.md, Fast mode), with the matrix's legs for each route. `--self`, or `--a` and `--b`. The same as `self` or `pages` without `--full`. |
| `selftest` | The negative controls (below), each a real `run.py pages` subprocess. `--cases`, `--browsers`. |
| `registry` | Validates `tests/divergences/` and lists the entries by category. Every comparison run validates them again (a registry error is a harness error). |
| `oracle` | `harness/oracle.py`'s `main(argv)`: build the oracle if missing or stale, serve it, capture every route into `tests/oracle/`. |
| `static` | `tests/static_checks.py`'s `main(argv)`. |
| `styles` | The Phase 2 gate (criterion 2), femto's native mode ported to this site: one document, two stylesheet lists. `--a` (default `static-multipage`, the tag's build: the frozen legacy CSS) against `--b` (default `dist`: vendored femto, the responsive-spacings option and the site CSS). Phase 2 changes no markup apart from the stylesheet links, so the two documents align element for element, and everything `pages` compares is compared (tree, attributes, text, computed styles, head, status, same-origin loads, with the same routes, legs, widths, masks, value rules, chunking, Safari handling and `--full` matrix), plus femto's tokens and interactive states (Tokens and states). `--states FILE` replaces `harness/states.json`, `--no-states` replays none (a `cap:` line). The same target on both sides (`--a static-multipage --b static-multipage`) is a self comparison: no registry entry but a skipped check applies, the mode's criterion-1 check. A styles comparison applies only the registry entries that name it (Divergence registry). Fast axes; `--full` runs the full matrix. |
| `behavior` | Scripted checks of every widget in 01 §2 that Phase 1 rebuilds, against one target (`--target oracle`, `dist`, `dist:<path>` or a base URL), in headless Chrome and Firefox; see Behavior. Phase 3 adds the docs spy, `#hash` and history behavior and `?theme=` (criterion 7), growing from the spike's `test_spike.py`, and Safari. |

Named targets (`harness/targets.json`):

| Target | Side | Readiness |
|---|---|---|
| `oracle` | the Remix site at `remix-final`, built if needed and served by `oracle.serve()` | `oracle` |
| `dist` | `npm exec --no -- wrangler pages dev dist` on free ports, with the wrangler pinned in `package.json` (`--no` never downloads one; before starting, the harness checks that `node_modules/wrangler` is the exact version `package.json` pins, else exit 2), its debug log and its own `--persist-to` state folder in the run's folder; needs `dist/index.html`; `same_origin` | `static` |
| `dist:<path>` | any built folder, served exactly as `dist` serves `dist/`: the same wrangler, options, readiness and same-origin rule; `<path>` is absolute or relative to the repository root, and needs `<path>/index.html`. Several agents can each compare their own build at once (`fast --a oracle --b dist:build/forms`), since every server has its own ports, log and state folder. The folder's pages are also reference documents for the registry's breadth rule, like `dist/`'s | `static` |
| `static-multipage` | the static site at tag `static-multipage` (the Phase 1 commit), built by the harness into `tests/builds/static-multipage/dist` (gitignored) and served exactly as `dist` serves `dist/`; `same_origin`. The build (`harness/tagbuild.py`): a detached `git worktree add` of the tag's commit in a temporary folder, the repository's `node_modules` linked into it, `node build.mjs --out <folder>`, then `git worktree remove --force` and `git worktree prune`. `build.json` beside the folder records the tag, commit, Node version, the prismjs version the build highlighted with (`node_modules/prismjs/package.json`, 1.30.0), file count, a SHA-256 of the built tree (every file's path and content) and seconds (0.3 s on 2026-11-02: 187 files). A run rebuilds when the folder's `index.html` or `build.json` is missing, the tag's commit is not the recorded one, the repository's prismjs is another version, or the folder no longer hashes to the recorded tree (a file under it edited, added or removed); the server start checks all of it again; `tests/builds/static-multipage.lock` is held exclusively by a build and shared by every server of the folder, so two runs never build at once and none rebuilds under a running server. `result.json` records `sides.<a|b>.build` | `static` |
| `fixture`, `fixture:<control>` | the selftest site, optionally changed by a control from `fixtures/controls.json`; `same_origin` | `static` |
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
widget"). The table of contents' Scrollspy is rebuilt in `docs.js` (01 §2 names it there) and held by
`toc-spy` until Phase 3's one-page spy replaces it (criterion 7 is Phase 3's); an earlier version of
this section said it was left out, which was wrong (round 1 of the Phase 1 fixes, finding bh-1). The
Logo animation is dropped by 01 §2 except where the static site still changes the route in place,
the version picker's swatches and links, so `picker-logo` holds it there. Remix's navigation
feedback is dropped. The version dropdown is a native `<details>` with no script, and the demo's
maximize controls are dead code, so neither has a check.

```sh
uv run tests/run.py behavior --target oracle                         # every check, Chrome and Firefox
uv run tests/run.py behavior --target dist --groups shell,landing    # some groups against the static site
uv run tests/run.py behavior --target dist:/path/to/built --checks copy-button,grid-columns
uv run tests/run.py behavior --target http://127.0.0.1:8788 --ready static   # a server someone else runs
uv run tests/run.py behavior --list                                  # the checks and what each asserts; starts nothing
```

Options: `--target` (`oracle`, `dist`, `dist:<path>`, a base URL; the named targets of
`harness/targets.json`, started and stopped by the run like every mode's), `--groups`, `--checks`
(names), `--browsers chrome,firefox` (the default; Safari is Phase 3's and exits 2 for now),
`--ready oracle|static|none` (the target's hook by default; `static` for a base URL), `--workers
chrome=2,firefox=2` (sessions per browser, 1 by default), `--expect-oracle-bugs` (a base URL that
serves the oracle), `--run-id`, `--label`, `--no-shots`, `--list`.

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

Three mechanisms reach under the page, each for one check family and each without touching the
page's markup or styles:
- **Preload scripts** (BiDi `script.addPreloadScript`, removed after the check): a script that runs
  in every new document before the page's own, for the color-scheme flash.
- **The copy spy** (`behavior.COPY_SPY`): `document.execCommand("copy")` and
  `navigator.clipboard.writeText()`/`write()` are replaced in that document by recorders, so the
  copy buttons are checked without ever touching the machine's clipboard.
- **Classic scrollbars**: headless browsers on macOS draw overlay scrollbars of width 0; the modal's
  scrollbar compensation needs one that takes space. Chrome adopts a `::-webkit-scrollbar` sheet in
  every new document before its scripts run, Firefox gets `ui.useOverlayScrollbars` 0 for the check.

**Expected failures.** A check may assert something the conversion fixes in the oracle (PLAN.md,
`oracle-bug`): it names the assertion and the reason, `oracle_bug={"fails": ..., "reason": ...}`.
Against `--target oracle` (or `--expect-oracle-bugs`) such a check must fail at exactly that
assertion, which is reported as `XFAIL`; if it passes there (`XPASS`) or fails at another assertion,
the run fails. Against any other target it is an ordinary check. Ten checks carry one (`--list`
shows each with the assertion it fails): `color-scheme-flash` (two routes), `theme-stored-invalid`,
`picker-swatch-focus`, `color-modal-close-url`, `color-modal-focus`, `color-modal-tab`,
`color-modal-focus-small`, `font-size-restored-switch`, `progress-offscreen` and `demo-offscreen`,
so a full run against the oracle expects 11 `XFAIL` per browser. Two kinds of fix are among them.
The color-scheme flash, the invalid stored theme and the two off-screen intervals are what the
conversion fixes by being written to PLAN.md's rules (Decision 14; Conversion rules, intervals on
screen). The color modal's focus and Tab handling, the swatch focus and the restored font-size
switch are deliberate early fixes of 03 §5's widget plan (`<dialog>`-native focus for `colors.js`)
that PLAN.md's Workflow lists under Phase 3's per-dialog modal and widget fixes; Phase 1 landed them
with their widgets instead of porting the bugs first, and the owner confirmed that on 2026-10-31
(PLAN.md, Conversion rules, JavaScript). None of these is a pages-mode difference, so no registry entry records them. Nothing else is expected to fail, and nothing is
masked: the parity masks and the `blob:` rule belong to the pages mode. These expected failures
live in the checks, not in `tests/divergences/`, whose entries type pages-mode records; each
carries the same PLAN category, `oracle-bug`, and its reason.

**Output.** `tests/results/<run-id>/` (run id `YYYYMMDD-HHMMSS-behavior-<pid>` unless `--run-id`):
`result.json` (the run, the target and its side, the sessions' versions, totals per browser, every
check run with its status, the failing assertion's label, every assertion with its detail, notes,
duration and document loads), `summary.txt` (failures first with their detail, then the expected
failures with their reasons, then one line per check run) and `log.txt` (one line per check run as it
finishes); `shots/<browser>__<check>__<route>.png`, the viewport of every failed, errored or XPASS
check. Statuses: `PASS`, `XFAIL`, `FAIL`, `XPASS`, `ERROR` (an exception outside an assertion: a
covered click target, a WebDriver error, after which the session is restarted). Exit status: 0 when
every check run is `PASS` or `XFAIL`; 1 otherwise or after a harness error; 2 for a setup error
(an unknown group, check, browser or target, a missing `dist/`).

**Writing a check.** In a group module, `GROUP = "<group>"`, then:

```python
@check("name", ("/route", "/other"), width=375, height=812, media="dark", storage={"femtoColorScheme": '"dark"'})
def name(page):
    """What it asserts, in terms of DOM state, focus, URL and storage (shown by --list)."""
    page.click("css selector")                       # or an element; page.click_at(x, y) for a point
    page.wait("label", "js expression", 1)          # poll until truthy, at most 1 s
    page.eq("label", page.js("return ..."), expected)
```

`page` also has `ajs` (async scripts), `expect`, `holds`, `key` (`ESCAPE`, `ENTER`, `ARROW_LEFT`,
...), `focus`, `scroll_to`, `resize`, `new_tab`/`switch` (a second tab of the same browser),
`wait_navigated(path)` (a full load or a client-side route change, then the readiness hook),
`with_classic_scrollbars()`, `note` and `url`. The first assertion that fails ends the check, and its
label names the failure, so labels say what should hold.

### The checks

Each check's docstring (`--list`) is its full statement; this is the summary. Viewport 1300 × 900,
light OS and nothing stored unless the table says otherwise. 59 checks over 83 check-routes, 166
runs in Chrome and Firefox (`--list` prints the count).

| Group | Check | Routes | Asserts |
|---|---|---|---|
| shell | `theme-toggle` | `/`, `/docs/typography` | No `data-theme` and nothing stored at first; the header toggle reads "Turn on dark mode" without `moon`. A click sets `data-theme="dark"`, stores `femtoColorScheme` `'"dark"'`, relabels "Turn off dark mode" with `moon`, URL unchanged; a second click gives `light` the same way. |
| shell | `theme-toggle-dark-os` | `/docs` (dark OS) | The toggle follows the OS ("Turn off dark mode", `moon`) with no `data-theme`; a click stores `'"light"'`, the next `'"dark"'`. |
| shell | `theme-toggle-keyboard` | `/`, `/docs/typography` | The toggle focused, Enter gives dark (data-theme, storage, label) and Enter again light, with no navigation and the document kept. |
| shell | `theme-os-live` | `/`, `/docs/table` | With nothing stored, a live switch of `prefers-color-scheme` to dark and back relabels the toggle, turns the homepage comparison samples dark (`/`) or the inverse thead light (`/docs/table`) and back; no `data-theme` written, nothing stored. |
| shell | `theme-stored-dark` | `/`, `/docs/button` (stored dark) | A stored choice wins over a light OS: `data-theme="dark"`, toggle "Turn off dark mode". |
| shell | `theme-stored-light` | `/docs/button` (dark OS, stored light) | `data-theme="light"`, toggle "Turn on dark mode"; a click stores dark. |
| shell | `theme-stored-invalid` | `/docs/table` (dark OS, stored `'"blue"'`) | A stored value other than light or dark is left in storage and ignored: no `data-theme` (held 0.5 s), the page follows the OS (toggle "Turn off dark mode", the inverse thead `light`); a click stores light. **XFAIL on the oracle** at "a stored value other than light or dark sets no data-theme": it writes any stored value into `data-theme`. |
| shell | `theme-cross-tab` | `/docs/typography`, a tab on `/` | Toggling in tab A reaches tab B without a reload (dark, then light, B's toggle relabelled); removing the stored item in A removes `data-theme` in B. |
| shell | `color-scheme-flash` | `/`, `/docs` (stored dark) | Once a paint entry exists (Chrome can record it a few hundred ms after load), seen from a preload script, `data-theme` appears while the head is parsed (no `<body>` yet), before the first paint, and the first animation frame sees it. **XFAIL on the oracle** at "set while the head is parsed": it sets the attribute during hydration (the flash; whether that still precedes the first paint is a race). |
| shell | `header-fixed` | `/docs/modal` | `body > header` has `is-fixed-above-lg`; `is-fixed` exactly while `scrollY > 20` (off at 20, on at 21, off again at 20 and 0). |
| shell | `header-landing` | `/` | The landing header has no class, at the top and scrolled. |
| shell | `copy-button` | `/docs`, `/docs/modal` | The first and last copy links each copy their own block's `pre code` textContent (copy spy), URL unchanged; in the page: "Copied" with `svg.check` within 100 ms, back to "Copy to clipboard" with `svg.clipboard` 900 to 1500 ms later, no other step, focus not on the link. |
| shell | `copy-button-repeat` | `/docs/modal` | Two clicks 500 ms apart copy twice; "Copied" reverts once, 900 to 1200 ms after the first click (Code.jsx: every click schedules its own revert), no other step, not focused. |
| shell | `modal-helper` | `/docs/modal` | Timed in the page: `modal-is-open modal-is-opening` within 100 ms of "Open modal", `modal-is-open` alone 350 to 700 ms later; Escape gives `modal-is-open modal-is-closing` within 100 ms and no class 350 to 700 ms later; Escape with nothing open does nothing. |
| shell | `modal-scrollbar-width` | `/docs/modal` (classic scrollbars) | While open, `<html>`'s `--femto-scrollbar-width` is the scrollbar's width (15px) and the page behind keeps its left edge; gone once closed. |
| shell | `side-menu-current` | `/docs`, `/docs/forms/input`, `/docs/version-picker/jade` | Only the route's category `details` is open, only its `summary` has `aria-current="true"`, and the only current link is the route's (the Version picker link on a color route). |
| shell | `toc-spy` | 7 docs routes | Scrolled through the page in 40 steps, the one current table-of-contents link is the first section in view with the viewport shifted down by twice the header's height, the last link at the page's end, none when no section is in view (ghostui's rule); the current link changes. |
| shell | `side-menu-max-height` | `/docs/grid` (375 × 812) | The menu nav's `--max-height` is `innerHeight` minus its top (within 0.5 px) on load and after resizes to 375 × 600, 1300 × 900 and, scrolled 500 px, 1300 × 700; each time `<body>`'s inline `min-height` is `innerHeight` px. |
| shell | `mobile-menu` | `/docs/modal` (375 × 812) | The breadcrumb's "Documentation" link adds `is-open-on-mobile` to `aside#documentation-menu`, `<html>` stops scrolling, URL unchanged; the menu's close link reverses all three. |
| shell | `mobile-menu-keyboard` | `/docs/modal` (375 × 812) | Enter on the focused "Documentation" link opens the menu, Enter on its focused close link closes it; no navigation either time. |
| shell | `mobile-menu-link` | `/docs/modal` (375 × 812) | With the menu open, opening "Layout" and following "Grid" lands on `/docs/grid` with the menu closed; back returns to the same `/docs/modal` document (client-side history, or the back-forward cache) with its menu closed. |
| shell | `breadcrumb-sticky` | `/docs/modal` (375 × 812) | Relative to the breadcrumb's own natural top t (the static site's sits about 37 px higher, with no banner): `is-sticky` within 1 s at 400 px and at ceil(t) + 2, gone at floor(t) - 1, floor(t) - 20 and the top. |
| shell | `breadcrumb-chapter` | 7 docs routes (375 × 812) | The last item names the route's category; the first is the "Documentation" link to `/docs`. |
| shell | `example-forms` | `/docs/forms`, `/docs/forms/input`, `/docs/group`, `/docs/color-schemes`, `/docs/version-picker` | Enter in every enabled text-like input and a click on every submit button of every content form: no navigation, no reload, every submit event canceled. |
| getting-started | `picker-configuration` | `/docs/version-picker` | The select and the Conditional Styling switch regenerate the four samples (footer link, CDN, Sass, starter template; exact text) and the two descriptions, over six configurations. |
| getting-started | `picker-code-highlight` | `/docs/version-picker` | The regenerated samples keep the load-time highlighting: links with only the file name's token changed, the template plus the `class="pico"` tokens, Sass as Prism's scss output. |
| getting-started | `picker-swatch` | `/docs/version-picker` | Pumpkin's swatch: URL `/docs/version-picker/pumpkin`, one history entry, scroll kept, and the theme example, samples, reset form values, every `aria-current` outside the table of contents (header, footer, side menu, swatches), title and `--femto-primary` as that route has them on load (tree snapshots); the configuration survives a swap to jade; back and azure's swatch work. |
| getting-started | `picker-logo` | `/docs/version-picker` | The header logo is `femto-logo` on load; pumpkin's swatch makes it `femto-logo animated` within 2 s and `femto-logo` again 900 to 1500 ms later, no other step. |
| getting-started | `picker-swatch-focus` | `/docs/version-picker` | Enter on pumpkin's focused swatch swaps to pumpkin with focus kept on it; Tab reaches orange's, Enter swaps to orange with focus on it. **XFAIL on the oracle** at "focus stays on pumpkin's swatch" (its remount drops focus to `<body>`). |
| getting-started | `picker-links` | `/docs/version-picker` | The table of contents' Theme link (the page itself), the footer's and the side menu's Version picker links, back and forward: each renders in place with no page load, the configuration (base 2) kept, the URL, history and page as that route has them on load. |
| getting-started | `color-schemes-toggle` | `/docs/color-schemes` | The page's own switcher toggles the scheme and storage and relabels itself and the header toggle; the header toggle drives it too. |
| customization | `color-modal-open` | `/docs/colors` | Red 500's button opens one `dialog.color` (header class, "Red 500", "Shōjōhi Red", glow, the six labelled values); Escape closes; Slate's family header opens slate 600. |
| customization | `color-modal-arrows` | `/docs/colors` | Right and Left step shades, Down and Up step families, wrapping at both ends (red 50 to slate 950 and back). |
| customization | `color-modal-close` | `/docs/colors` | The close link, a backdrop click and Escape close it (no open dialog, no modal class); a click inside the article does not. |
| customization | `color-modal-close-url` | `/docs/colors` | The close link leaves the URL and history as they were. **XFAIL on the oracle** (`#close`). |
| customization | `color-modal-focus` | `/docs/colors` | Enter on a focused shade button opens the modal with focus inside it; Escape returns focus to the button. **XFAIL on the oracle** (no focus management). |
| customization | `color-modal-tab` | `/docs/colors` | Tab and Shift+Tab in the open modal keep focus inside the dialog and leave `scrollY` as it was; Escape returns focus to the button. **XFAIL on the oracle** at "Tab keeps focus inside the dialog". |
| customization | `color-modal-arrows-small` | `/docs/colors` (375 × 480) | Where the open modal's article overflows, the arrow keys step colors without scrolling the article or the page. |
| customization | `color-modal-focus-small` | `/docs/colors` (375 × 480) | Enter opens the modal with focus on its close link (`header a.close`), not the scrollable article; Escape returns focus to the button. **XFAIL on the oracle** at "focus moves to the close link". |
| customization | `color-modal-resize` | `/docs/colors` | The open modal's article has `max-height: calc(<innerHeight>px - 2rem)` at 1300 × 900 and after resizes to 1300 × 600 and 1300 × 760. |
| customization | `palette-download` | `/docs/colors` | The Download link's same-origin resource is the 20 × 19 palette, two-space JSON, with the SHA-256 of the oracle's download. |
| layout | `grid-columns` | `/docs/grid` | Add and Remove column from 4 up to 10 and down to 1 (clamped both ways): the columns, the code text and its highlighted tokens follow every click. |
| content | `font-size-units` | `/docs/typography` | The "Display in rem" switch turns the px table (values and formula tooltips) into percentages and multipliers without tooltips, and back to the exact load-time tree. |
| content | `font-size-restored-switch` | `/docs/typography` | With the "Display in rem" switch restored as checked on a reload (Firefox; a preload script in Chrome), the table shows rem from load, and one click restores the exact px table. **XFAIL on the oracle** at "with the switch restored as checked, the table shows rem". |
| content | `table-inverse-thead` | `/docs/table` | The color-schemes example's thead and its sample read `data-theme="dark"` on a light page and follow the header toggle. |
| content | `table-inverse-thead-dark-os` | `/docs/table` (dark OS) | They read `light`. |
| content | `link-examples` | `/docs/link` | The 6 example links go nowhere, clicked and with Enter: the document, URL, history, scroll position and tabs unchanged, every click canceled. |
| forms | `checkbox-indeterminate` | `/docs/forms/checkboxes` | The example checkbox is indeterminate after load with no added attributes; a click checks it. |
| components-a | `dropdown-items` | `/docs/dropdown` | The 45 example links (four items in each of the eleven link dropdowns, plus the nav example's "Services") go nowhere. Pointer: each dropdown is opened once from its summary and its items are clicked in turn. Keyboard: Enter on the summary, Tab to each item, Enter. After each click or Enter, the window marker, URL, history.length and scroll position are unchanged, the dropdown stays open and the click is defaultPrevented; after an Enter, focus stays on the item. |
| components-b | `modal-demo` | `/docs/modal` | "Open modal" opens the demo dialog; Cancel, Confirm and the backdrop close it, a click inside does not; the two example dialogs stay open and their buttons do nothing. |
| components-b | `progress-value` | `/docs/progress` | Watched 16 s on screen: an integer 5 to 94 with `max="100"`, the sample printing the same value, at least two changes, each a whole number of 5 s periods (± 400 ms) after the last. |
| components-b | `progress-offscreen` | `/docs/progress` (1300 × 300) | No change for 10.5 s while the bar is below the viewport; on screen, changes 5 s and 10 s later; above the viewport, none for 10.5 s (intervals run only on screen). **XFAIL on the oracle** at "no change for 10.5 s while the example is below the viewport". |
| components-b | `nav-example-links` | `/docs/nav` | The 31 example links (the `overflow-with-focus` nav's 3 and the examples' 28, dropdown items included) go nowhere, clicked and with Enter: document, URL, history and scroll kept, dropdowns open, every click canceled. |
| components-b | `tooltip-link` | `/docs/tooltip` (1300 × 500) | The example link (`href="/docs/tooltip"`), clicked scrolled down, ends at `/docs/tooltip` at scrollY 0 with no new history entry. The oracle keeps the document (Remix's client-side navigation); the static site's plain link loads it again, which the check notes and does not assert (PLAN.md Conversion rules: plain `<a>` replaces Link). |
| landing | `demo-loop` | `/` | Up to 100 s: the form's phases are exactly the demo's 15 (email ... range-50) and then email and invalid again; each phase's markup shows in the code while the form is in it; the fields carry each phase's values; at least 50 typed characters. |
| landing | `demo-variant` | `/` (1280 × 800) | The large code layout at 1280, the small one at 1279 and 375 and the large again at 1280, each within 3 s and each time started over at the first phase. |
| landing | `demo-page` | `/demo` | The first four phases in order with their markup, the email typed letter by letter. |
| landing | `comparison-toggle` | `/` | The comparison's code samples read `light`, then `dark` and `light` after header-toggle clicks. |
| landing | `demo-offscreen` | `/` | The demo changes on screen; above the viewport (after 2 s to settle) no change for 7 s; back on screen it changes within 5 s. **XFAIL on the oracle** at "no change for 7 s while the demo is above the viewport" (TypeIt runs off screen). |

### Proof

Run on 2026-10-31 on the rig (Chrome Beta 158.0.8127.2, Firefox 160.0, Selenium 4.52.0), the
oracle at `remix-final` (`tests/results/<run id>/`, gitignored):

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
- Each widget returns at once when its markup is absent, and binds to the oracle's markup (ids,
  classes, `aria-` attributes, structure) without adding attributes. `widgets()` reports an exception
  without stopping the regions after it.

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
| `where` | optional filters, all of which must match the cell: `browsers`, `routes` (exact, or `/^regex/`), `schemes` (legs), `widths` (integers or `{"min", "max"}`), `comparisons` (`pages`, `styles`; `self` for skipped-check entries only), and `states` (element kinds only: `base`, the document as loaded, `hover`, `focus`, `focus-visible`, `active`; matched per record in the page, a record found under no state being `base`) |
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
summary of a styles run says so.

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
  and the swatch and shade records all registered). The `registry-evasion`, `registry-route-scope`,
  `registry-runtime`, `registry-missing-page` and `registry-root-path` controls prove these rules,
  and `registry-styles` the token and state fields and the comparisons rule, `registry-token-split`
  and `registry-surface-split` the token and surface union limits, `registry-surface-closed` the
  closed-set allowance, `registry-pinned` the pinned entry, `registry-consequence` and
  `registry-consequence-unscoped` the layout consequence and `state-coverage` the state rule below
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
`merge-layout` and `id-rename`.
`owner.json` holds the `owner-change` entries for PLAN Decision 16, the theme toggle's emoji icon
(2026-11-01): the SVG-to-span tag change and the SVG's two parts.

## Output

`tests/results/<run-id>/` (run id `YYYYMMDD-HHMMSS-<mode>-<pid>` unless `--run-id`):

- `result.json`: `run_id`, `mode`, `comparison` (`self`, `pages` or `styles`), `full`, `argv`, `git`,
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
  after the replay) and the `a_states` and `b_states` timings).
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
  builds the tag (the `static-multipage` target) and shared by every server of its folder and every
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
real CLI as `run.py pages --a fixture --b fixture:<control>` (the styles controls as `run.py styles`
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

A control whose run has a harness error fails, whatever its records.

## Known limits

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
- `prefers-reduced-motion` is not an axis; both sides run with the OS setting (no preference).
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
longer depends on when Safari starts that transition. The behavior checks find the icon by its
class, not its tag, so they hold for both. `eslint.config.js` allows femto's tokens as unknown
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

Not run: Safari. The `styles` mode needs an unlocked screen with the automation window in front for
its state replays, so a Safari styles pass is the owner's, as for Phase 0.

### Known Phase 1 deviations

What Phase 1 ships differently from the oracle or from PLAN.md's letter, each on record here so that a
later phase or the owner picks it up. Registry entries name the pages-mode differences; these are the
rest, and the registered ones with a consequence a later phase owns.

| Item | What | Owner |
|---|---|---|
| The 404 page's footer | Without the banner, main.css's `auto auto 1fr auto` body rows give the footer the free space: on the 404 page at 800 to 1300 px it sits 43 to 100 px higher, with blank space under it, and so would any page shorter than a taller window (p1-shell-404-footer-track). | Settled in Phase 2: `common.css` writes the rows `auto 1fr auto` (p2-common-body-rows) |
| Six footer links on `/docs` | The About column's five items and Class-less version point at `/docs` (PLAN.md Text: removed or pointed at `/docs`), so on `/docs` they carry `aria-current="page"` and a screen reader hears each as the current page (p1-shell-footer-dropped-links-current). Kept so the footer's columns and height stay the oracle's. | Phase 4's footer rewrite removes them |
| woff fallbacks | The frozen `main.css` names 10 `.woff` fallbacks under `/assets/fonts/` beside the woff2 files; only woff2 ships (PLAN.md File tree), so those URLs answer 404. Every target browser takes the woff2. | Settled in Phase 2: `fonts.css` names woff2 only, and `assets/legacy/` is gone |
| Pacifico on `/docs/css-variables` | The oracle loads Pacifico from Google Fonts; the static page links `/assets/legacy/pacifico.css` (menu.json `styles`), Google's stylesheet with its 5 `src` URLs pointed at the same woff2 files, byte-identical to the captured ones (`tests/oracle/capture/_fonts`), so the page loads only same-origin resources (criterion 15). The pages mode skips stylesheet links (head comparison), so this is the one stylesheet whose origin changed without a record. | Settled 2026-10-31, the owner keeps it: PLAN.md's File tree lists Pacifico 400, Phase 2's `fonts.css` took its `@font-face` rules (menu.json no longer links a stylesheet for it), and Phase 4 keeps the example |
| React text separators | Two section files keep React's `<!-- -->` separator (`color-schemes.html`, `version-picker.html` and its 19 colors: 22 copies in `dist/`), for a sub-pixel label width (tests/convert/README.md). PLAN.md's Conversion rules strip them. | Phase 3 removes them with the per-route artifacts |
| Per-route build scaffolding | In per-route mode `build.mjs` also swaps literal markup in `docs.html` per route (the `<main>` class, the breadcrumb's chapter, the Close link, canonical, `og:url`), fills two slot comments (`<!-- docs:menu -->`, `<!-- docs:sections -->`) and adds route stylesheets; `menu.json` carries `route`, `label`, `routeTitle`, `toc`, `styles` and `variants` beyond the File tree's id, title, description. PLAN.md allows only the include markers and three placeholders. | Settled 2026-10-31, accepted as scaffolding for Phases 1 and 2 (PLAN.md File tree, Per-route scaffolding); Phase 3's one-page assembly removes them |
| The palette download | 01 §2 and 03 §5 plan a static JSON file written by the build; Phase 1's `colors.js` makes an on-load `blob:` URL, for parity with the oracle's (normalized by the `blob:` value rule). No phase owns the switch. | Settled 2026-10-31: Phase 3 switches to the build's static JSON file (PLAN.md Workflow) and registers the URL as `asset-path` |
| File tree extras | `site/partials/` holds `docs-header.html`, `logo.html`, `nav-icons.html` and `structured-data.html` beyond head, header and footer; the root holds `vendor.mjs` and `eslint.config.js`; `site/docs/sections/version-picker/<color>.html` are 19 per-route files. `.prettierrc` names a plugin no longer installed, `robots.txt` is absent, and `site/_headers` still caches `/build/*`. | Settled 2026-10-31: PLAN.md's File tree lists the extra partials, `vendor.mjs`, `eslint.config.js` and the color files; Phase 3 deletes the color files, Phase 5 the rest |
| Pages-inherent paths | `/404` answers 200 (the 404 page), and `/404.html`, `/index`, `/index.html`, `/docs/index` and a page's `.html` name redirect (Cloudflare Pages' pretty URLs). Criterion 6 says any other path answers 404; `static_checks.py` probes these and lists them as notes (`PAGES_INHERENT`). | Settled 2026-10-31: accepted in PLAN.md Risks (Cloudflare), and criterion 6 exempts them |
| Early widget fixes | The color modal's focus and Tab handling, the swatch focus and the restored font-size switch (Behavior, Expected failures). | Settled 2026-10-31: confirmed (PLAN.md, Conversion rules, JavaScript) |
| `<body style="min-height:100vh">` | The oracle's server HTML had it, so the static pages do (round 1 of the fixes, PH-7); site.js still sets innerHeight in px. html-validate's `no-inline-style` reports it on every page (criterion 9). | Phase 2 or 3: once the site CSS gives `<body>` its minimum height, drop the attribute |
| Escape on the mobile menu | Not in Phase 1, as in the oracle (01 §2: no Escape); an earlier Phase 1 `docs.js` closed it on Escape, which round 1 of the fixes removed. | Phase 3 (criterion 7) |

### Owner's Safari steps

`tests/owner-safari.sh` runs them, and only the owner runs it, since it switches macOS's appearance
(to Light, then Dark) and puts back the one it found, even when stopped with Ctrl-C. Quit Safari
(Cmd-Q), unlock the screen and leave the Mac alone until it prints `done`:

```sh
tests/owner-safari.sh
tests/owner-safari.sh dark
tests/owner-safari.sh spike
```

With no argument it runs the spike (into `results/p0-spike-safari.txt`, for
`docs/research/05-spike.md`), `rig` with its input checks, the six light `/docs/css-variables` cells,
the dark self pass over every kept route and the three selftest controls that compare on a dark OS:
about 70 minutes. `dark` runs only the dark self pass, as `p0-self-safari-dark-masked`: about 26
minutes. `spike` runs only the spike, into `results/p0-spike-safari-2.txt`, and leaves the
appearance as it is: about a minute. Each step is one `uv run` command in the script under `caffeinate -d -i`, so one can also
be run by hand. At the end the script prints how often each self run's `log.txt` says
`OS scheme light` or `OS scheme dark`: the light run must say light and the dark run dark, and the
dark run's skipped checks are `media:light`. Measured on an unlocked screen: a full dark pass
1,555 s, and about 190 s for each `/docs/css-variables` cell (closed `<details>` style recompute).

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
