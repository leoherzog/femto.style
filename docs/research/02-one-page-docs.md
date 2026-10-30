# 02: One docs page whose #hash follows the reader

How to merge the docs routes into one page whose side nav and URL `#hash` follow the reader as they scroll. It covers URLs, ids, hosting, search and link previews, the scroll spy, and the `?theme=` parameter. Web findings were checked on 2026-10-30; sources are linked inline. The mechanism was prototyped in `spike/` (see 05).

## Verdict

One file, `docs.html`, served at `/docs`.

**URLs.**
- Each section's top heading carries a one-or-two-word id (`#input`, `#forms`, `#overflow-auto`).
- While the reader scrolls, a small script writes that id into the URL with `replaceState` once the section has been stable for 200 ms.
- The first section has no hash, so the top of the page is plain `/docs`.
- Subheadings carry no ids, and the side nav lists sections only.

**The browser does the rest.** Links, deep links, back, forward and reload are its own fragment navigation, and deep links work with JavaScript off.

**Themes** are a query parameter, `/docs?theme=jade#modal`. An inline script in `<head>` writes the theme's `<link>` with `document.write`, the only method that applied before the first paint in both Chrome and Firefox.

**Smooth scrolling is limited to nav clicks.** On `<html>` it makes Chrome animate every deep link and every back and forward from the top of the page.

Nothing needs a feature that is not Widely available by 2026-11-13. Every check passed in Chrome Beta 158 and Firefox 160; Safari is still to run.

## 1. URLs and ids

| URL | Shows |
|---|---|
| `/docs` | the top: Quick start |
| `/docs#<id>`, e.g. `/docs#input`, `/docs#overflow-auto` | that section, scrolled to by the browser |
| `/docs?theme=<color>` (with or without a hash) | the same, in that theme color (§5) |
| `/docs/`, `/docs.html` | 308 to `/docs` (Pages' HTML handling, §2) |
| anything else under `/docs/` | 404 |

Section ids are one or two words, lowercase and hyphenated, and unique on the page. Proposed ids for the 31 sections that survive Phase 1:

| Category | Ids |
|---|---|
| Getting started | `quick-start`, `version-picker`, `color-schemes`, `rtl` |
| Customization | `css-variables`, `colors` |
| Layout | `container`, `landmarks`, `grid`, `overflow-auto` |
| Content | `typography`, `link`, `button`, `table` |
| Forms | `forms` (the overview), `input`, `textarea`, `select`, `checkboxes`, `radios`, `switch`, `range` |
| Components | `accordion`, `card`, `dropdown`, `group`, `loading`, `modal`, `nav`, `progress`, `tooltip` |

Phase 4 adds `classes`, `migration`, `browser-support`, `files`, `themes`, `options`, `modules`, `cascade-layer` and `shadow-roots`, as listed in 04. It may also rename `version-picker` with the picker's rework.

The id goes on the section's top heading (the `h1` in its `hgroup`), not on the `<section>`. That way the browser's fragment scroll lands on the heading, below the fixed header through `scroll-padding-top`.

**Categories have no anchors.** They group the nav, so `#forms` means the Forms overview section.

**Subheadings have no ids and no `#` permalinks.** The owner chose this on 2026-10-30 over hashes that follow every heading. That would have meant renaming about 15 repeated subheading names, such as `validation-states`, which appears in seven sections. Today's three links into another route's subheading (group → input's Search, input → button's Variants, container → a class-less section) point at the section instead.

**Other ids must be unique too.** That covers form controls, `aria-describedby` targets, example ids and SVG internals. A repeated one takes its section id as a prefix (01 §1 lists them), and none may equal a section id. A static check enforces this.

## 2. Hosting on Cloudflare Pages

- **Nothing needs rewriting.** `docs.html` is served at `/docs`. `/docs.html` and `/docs/` 308 to it (https://developers.cloudflare.com/pages/configuration/serving-pages/). Never write `docs/index.html`: it would make `/docs/` the canonical form, with a trailing slash.
- **Always ship a top-level `404.html`.** Without one, Pages assumes a single-page app and serves `/` with a 200 for every unknown path.
- **No `_redirects`.** Nothing is live yet (the owner, 2026-10-30), so no old URL needs one, and the file can go.
- **Pages or Workers.** Pages has no sunset date, but its docs now open with "Start new projects with Workers" (https://blog.cloudflare.com/full-stack-development-on-cloudflare-workers/). A static `dist/` with no rewrites moves to Workers Static Assets unchanged, so the conversion stays on Pages, deployed by direct upload as today.

## 3. Search and link previews

- **Google treats the page as one URL.** It ignores fragments when indexing, and its guidance prefers the History API over fragments for content that changes (https://developers.google.com/search/docs/crawling-indexing/url-structure, updated 2026-10-21). Here the content does not change; one page scrolls. Google can still show "jump to" links from heading ids. Ranking sections as separate pages would need separate URLs with separate content, which is out of scope.
- **Unfurlers do not run JavaScript, and the server never sees a fragment.**
  - Apple Messages says so (TN3156).
  - Slack, Facebook and LinkedIn read the served `<title>` and `og:*`. X and Discord are reported, not documented, to do the same.
  - So every shared docs link previews as the docs page, whatever its `#hash`. The owner accepted this on 2026-10-30.
- **Cloudflare edge code** could rewrite the head per path, through a Pages Function or Snippet with HTMLRewriter. It cannot help here, because a fragment never reaches the server.

## 4. The scroll spy

The spike's `docs.js` (about 130 lines) does only what the browser does not:

1. **Current section.** On each `scroll` (passive, at most once per animation frame), walk the sections in order. The current one is the last whose top is at or above `header height + 24px`. At the page bottom (`innerHeight + scrollY >= scrollHeight - 2`), the last section wins once its top is on screen, so a short final section can become current.
2. **On a change.**
   - Move `aria-current="true"` to its nav link.
   - Scroll the side nav, not the page, so the link is visible. `scrollIntoView({container})` is Chrome-only, so set the nav's `scrollTop` directly.
   - Set `document.title` to "<Section> • femto", or the page's own title for the first section.
   - In the real site, also open its category's `<details>` and set the mobile breadcrumb's chapter.
3. **URL.** 200 ms after the last change, `replaceState` to `#<id>`, or to no hash for the first section. The pathname and query (`?theme=`) stay, and the call sits inside `try`. The limits are:
   - Chromium: 200 calls per 10 s, ignored past that.
   - Firefox: 200 per 10 s.
   - WebKit: 100 per 10 s, and it **throws** `SecurityError` (WebKit `History.cpp`).

   In the spike a fast scroll through the whole page made at most three calls. `replaceState` fires no `hashchange` and moves no `:target`, which is intended.
4. **Links.**
   - The browser navigates and scrolls; nothing calls `preventDefault`.
   - A delegated `click` listener marks the target section at once, locks the spy until 150 ms pass with no `scroll` event, and adds a class on `<html>` that enables `scroll-behavior: smooth` (inside `prefers-reduced-motion: no-preference`).
   - The lock stops the nav flickering through the sections passed on the way. `scrollend` would be cleaner, but it is Baseline only since 2025-12-12 (Safari 26.2).
   - A click pushes one history entry. Unlocking removes the class, re-reads the position and writes the URL. Clicking "Quick start" therefore ends on plain `/docs`.
5. **Back and forward.**
   - `popstate` only locks the spy.
   - Firefox restores the exact position.
   - Chrome scrolls to the entry's `#hash` heading. That is the start of the section the reader was in, and acceptable.
6. **Load and reload.** No code is needed.
   - The browser scrolls to a deep link's `#hash` itself, with or without JavaScript.
   - It restores the position on a normal reload.
   - It scrolls to the hash on a hard reload.

**Smooth scrolling.** Today's site sets `html { scroll-behavior: smooth }`. With it, Chrome animated the jump to a deep link's `#hash` for about 1.2 s from the top of the page, even with JavaScript off. It animated back and forward the same way. Firefox did not. Scoping smooth scrolling to nav clicks keeps it where it helps.

Rejected options:
- **Hashes that follow every heading:** see §1.
- **Per-section paths with one copy of the page per path, or `_redirects` 200 rewrites.** The first spike round proved both work (05, round 1). They exist only to give link previews per section, at the cost of 50 copies of the page or a set of rewrite rules. The owner chose hashes on 2026-10-30.
- **IntersectionObserver.** It works, but it needs the same bottom-of-page fallback. Its `scrollMargin` option is not Widely available.
- **CSS `scroll-target-group` and `:target-current`.** Chrome-only, and they update neither the URL nor `aria-current`.
- **Navigation API.** Baseline only since 2026-01-13.
- **`content-visibility: auto`.** Not Widely available, and its estimated sizes move deep-link targets.

`aria-current="true"` marks the active nav link. MDN gives no normative value for a table of contents, and `true` is the safe reading for "current item in a set".

## 5. `?theme=`

The docs page always loads:
- `vendor/femto/dist/femto.min.css`;
- `css/options/responsive-spacings.css`;
- `dist/femto.colors.min.css`, for the palette and the `.femto-color-*` and `.femto-background-*` classes.

A theme color is a separate file, `css/themes/<color>.css`, which sets ten tokens on `:root, :host`. With `?theme=<color>`, an inline script in `<head>` adds that file after the options file.

How the stylesheet is added decides whether the first frame is already in the theme. The spike served the theme file 300 ms late and read `--femto-primary` in the first animation frame:

| Method | Chrome 158 | Firefox 160 |
|---|---|---|
| `link` made with `createElement` and appended to `<head>` | after the first frame | after the first frame |
| the same, with `blocking="render"` | before | after (ignored) |
| `document.write('<link rel="stylesheet" href="…">')` from the inline script | before | before |

**Why `document.write` wins.** A stylesheet added by script is not render-blocking (HTML: only parser-inserted `<link>`s are implicitly potentially render-blocking), and `blocking="render"` is not Baseline. `document.write` makes the `<link>` parser-inserted. Browsers discourage `document.write` for cross-origin scripts, which this is not. The script accepts only the 20 known color names, so nothing from the URL reaches the markup unchecked.

**Changing color in the picker.** It swaps the `<link>` (no flash concern after load) and `replaceState`s the query, keeping the hash. Azure, the default, removes the parameter.

The theme lasts as long as the URL carries it: reloads and copied links keep it, and the spy and nav clicks never drop it.

## 6. What the build writes for the docs

From `site/docs/menu.json` (categories, and per section its id, title and description) and `site/docs/sections/<id>.html`, the build writes:
- one `docs.html`, with the side nav generated from the menu;
- the sections in menu order, with code highlighted;
- `404.html`.

`docs.html` has one `<title>`, description, `og:*` and `rel=canonical` (`https://femto.style/docs`).
