# femto.style static conversion plan

Convert femto.style from a Remix and React app with Sass into a plain HTML, CSS and JavaScript static site. Merge the docs routes into one page whose side nav and URL `#hash` follow the section being read as the reader scrolls. Finish with a site that uses femto 3.0 and describes it. This file is the spec. The research behind every decision is in `docs/research/`.

## Decisions

Decisions 1 to 9 are the owner's, made on 2026-10-30. Decisions 10 to 15 follow from the research, and the owner approved them on 2026-10-30. Decision 16 is the owner's, made on 2026-11-01, Decision 17 the owner's, made on 2026-11-05, and Decision 18 the owner's, made on 2026-11-06. The owner changed Decision 11 on 2026-11-06: Cloudflare Pages' Git integration replaces direct upload, and `npm run deploy` is gone. Do not reopen any of them without asking the owner.

| # | Decision |
|---|---|
| 1 | Plain HTML, CSS and JavaScript. No React, Remix, Sass, PostCSS, bundler or framework, at runtime or at build time. |
| 2 | **The docs are one page, `/docs`.** The side nav lists the sections, grouped by category, and highlights the one being read. As the reader scrolls, the URL's `#hash` becomes that section's id, written with `replaceState` once the section has been stable for 200 ms. The first section has no hash, so the top of the page is plain `/docs`. Links, deep links, back, forward and reload are the browser's own fragment navigation (02 §4, proven in 05). |
| 3 | **One build step.** `npm run build` runs `build.mjs`, which only does five things: copies files, expands the head, header and footer includes, assembles the docs page from one source file per section with a generated side nav, pre-highlights code with a pinned Prism, and writes the sitemap (03 §2). It writes no per-path copies, includes no femto files as sample code, and never transforms CSS or JavaScript. `site/` is the hand-authored source. `dist/` is generated, gitignored and deployed. |
| 4 | **femto is vendored.** `site/vendor/femto/` holds femto's `dist/`, `css/` and `LICENSE.md`, copied from a recorded femto commit by `npm run vendor`, and is served from the site's own origin (03 §3). Switch to the npm package only after `@leoherzog/femto` is published (the package name, the owner, 2026-10-30, "for now"). |
| 5 | **Dropped, not built:** the About pages (Maintenance, What's new in v2, Mission, Usage scenarios, Brand, Built with), the homepage Stats, the maintenance banner, Class-less version, Conditional styling, Sass and the Pico v1 docs. Nothing is live, so nothing needs redirecting. |
| 6 | **Parity first.** The oracle is the Remix site at tag `remix-final`. Phases 1 to 3 change structure while matching the oracle, which is the parity reference as femto's 2.1.1 build was. Phase 4 then rewrites the content for femto 3. |
| 7 | **Ids.** Each section's id is one or two lowercase hyphenated words (`input`, `forms`, `overflow-auto`; the full list is in 02 §1) and sits on the section's top heading. Subheadings carry no ids, no `#` permalinks and no nav entries, and there is no "On this page" column. |
| 8 | **Themes are a URL parameter, `?theme=<color>`.** The docs page always loads femto, its responsive-spacings option and `femto.colors.css`. With `?theme=`, the first of two inline head scripts writes that theme's `<link>` with `document.write`, so it applies before the first paint (02 §5). The second script, the color-scheme one (Decision 14), follows it because Firefox holds its first paint only for a stylesheet that a later parser-blocking script waits on; with one script, Firefox paints the default color first (Phase 3, the owner, 2026-11-04). The script accepts only the 20 known color names. The picker swaps the `<link>` and `replaceState`s the parameter; azure, the default, has none. |
| 9 | **One URL to share and to index.** `docs.html` has one title, description, `og:*` and `rel=canonical` (`https://femto.style/docs`). Shared deep links preview as the docs page, which the owner accepted. In the browser, `document.title` follows the section being read. |
| 10 | **Smooth scrolling only for nav clicks.** `docs.js` sets a class on `<html>` during a click, and CSS gives that class `scroll-behavior: smooth` inside `prefers-reduced-motion: no-preference`. Never on `html` itself: Chrome then animates every deep link and every back and forward from the top of the page (05). |
| 11 | **Host on Cloudflare Pages, deployed by its Git integration.** The Pages project `femto-style` is connected to the GitHub repository `leoherzog/femto.style`. Pushing `main` deploys production, at `https://femto.style` and `https://femto-style.pages.dev`. Pushing any other branch deploys a preview, also at the alias `<branch>.femto-style.pages.dev` (the branch name lowercased, each character other than a letter or digit a hyphen); a branch has the alias only once it is pushed after the integration was connected. Every deployment, production's included, has its own `<hash>.femto-style.pages.dev` URL, which answers `x-robots-tag: noindex`; the production URLs answer without it. Since a push deploys, Decision 15's "Never push" and "Deploying is the owner's step" are one rule (PROMPT.md: "Never push, and never deploy"). The build settings live in the Cloudflare dashboard, not in the repository: Framework preset None, build command `npm run build`, build output directory `dist`, root directory empty, build system v3, and Node from `.node-version` (build system v3 reads the `NODE_VERSION` variable, `.node-version` or `.nvmrc`, never `package.json`'s `engines`). There is no `deploy` script. Dropping it is the owner's choice, not a limit of Pages: Wrangler can still upload to the project once its automatic deployments are turned off. A Git-connected project cannot switch to Direct Upload, though. No `_redirects`. Always ship a top-level `404.html`, and never write `docs/index.html` (02 §2). Moving to Workers Static Assets is a separate, later choice: `dist/` moves unchanged (the owner, 2026-11-06). |
| 12 | **Browser target: femto's.** Baseline Widely Available on 2026-11-13: Chrome and Edge 125, Firefox 128, Safari 17.5, Samsung Internet 27. The site's CSS follows femto's feature tiers and never-use list (femto `PLAN.md`, Browser target). The site's JavaScript uses nothing outside the target: no `scrollend`, Navigation API, `content-visibility`, `scroll-target-group`, `blocking="render"` or `scrollIntoView({container})`. |
| 13 | **Headings and other ids.** Each section keeps its `h1` (in its `hgroup`) and its `h2`s, so femto's element-based sizes are unchanged. Every other id on the page is unique and never equals a section id: form controls, `aria-describedby` targets, example ids and SVG internals. A repeated one takes its section id as a prefix (01 §1). |
| 14 | **The site's own state keeps its names.** The color-scheme choice stays in localStorage `femtoColorScheme` as JSON, and `data-theme` on `<html>` is set only when a choice is stored. The second inline head script applies it before first paint, which fixes today's flash. |
| 15 | **Work on `dev`**, branched from `main`. Its first commit is the owner's in-progress rebrand, "Rebrand To femto", tagged `remix-final` (the owner, 2026-10-30). The plan and research follow in one commit; after that, commit only at passed gates, with the subjects in the Workflow table. Never push. Deploying is the owner's step. |
| 16 | **The theme toggle is a sun or moon emoji.** The header toggle and the `/docs/color-schemes` switcher show ☀️ while the page is light and 🌙 while it is dark, drawn in one color (the element's text color, by a transparent glyph and its shadow) by `site/assets/css/common.css`, in place of the oracle's animated SVG (the owner, 2026-11-01). Its box, label and behavior stay as the oracle's; its `moon` class did too, until Decision 18 wrote the emoji into the markup. It is registered as `owner-change`; the oracle's icon animation is masked, since Safari can read it mid-transition (tests/README.md, Masks). |
| 17 | **Icons are Unicode characters.** Every icon the site took from Tabler Icons and Feather is a character, which `site/assets/css/common.css` drew into an empty `<span class="icon icon-<name>" aria-hidden="true">` until Decision 18 put it in the markup: text characters with no emoji form (check ✓, close ✕, copy ⧉, edit ✎, menu ☰, arrow →, Grid's ⊕ and ⊖, and the homepage's ⤢, ◐ and `</>`), and two emoji drawn in one color as Decision 16's toggle is (the homepage's ⚙️ and ⚡). Brand marks have no Unicode form, so Font Awesome's GitHub, npm and X icons become Simple Icons' SVGs (CC0 1.0), as jsDelivr's already was, and femto's own logo stays an SVG. It is not registered as an `owner-change` divergence: parity with the oracle stopped binding at Phase 4. The SVG icons' animations become a check that pops in and an arrow that moves right on hover (the owner, 2026-11-05, on branch `unicode-icon-swap`). |
| 18 | **An icon is a `<span role="img">` holding its character.** Each of Decision 17's characters, and Decision 16's emoji, is written in the markup as `<span role="img">…</span>`, with no class: the role is the stylesheets' hook (`span[role=img]` in `site/assets/css/common.css`, an inline-block at least 1em wide and one 1em line tall, which each context sizes and colors). An icon that is a control's only content names the control, with the `aria-label` moved onto it from the control: the copy buttons, the menu's and the color modal's close buttons, the header's theme toggle and the Nav example's Menu link. Every other icon sits beside a label of its own and is hidden with `aria-hidden="true"`, as an `<img alt="">` would be. A copy button's check keeps the button's name, since the button still copies, and the status region still says "Copied". `site.js` and `docs.js` write the theme toggle's emoji and label into its icon, in place of the `moon` class. Two glyphs still need a hook of their own: the Responsive feature's ⤢, drawn larger and found by its feature's link, and the first feature's `</>`, which is marked up as `<code>` for its font. It stands in for an icon feature femto may take up later; femto is not changed (the owner, 2026-11-06, on branch `unicode-icon-swap`). |

## File tree

```
build.mjs                 npm run build: site/ into dist/ (03 §2)
vendor.mjs                npm run vendor: a femto commit into site/vendor/femto/
eslint.config.js          npm run lint (criterion 11)
.htmlvalidate.mjs         html-validate's rules, from Phase 3 (criterion 9)
.node-version             the Node version, read by Pages' build image (Decision 11) and check.yml's setup-node
.prettierrc               kept from the oracle, printWidth 100 only; prettier is not a dependency, and no tool runs it
.github/workflows/
  check.yml               the GitHub check, from Phase 5: build, lint and static_checks.py; never deploys
site/
  index.html  examples.html  demo.html (until Phase 4)  404.html  docs.html
  docs/menu.json          categories and sections in order: id, title, description and an optional nav label (until Phase 3, also per-route fields)
  docs/sections/<id>.html one section each: its hgroup (the h1 carries the id), content, edit link
  docs/sections/version-picker/<color>.html  one per color route, until Phase 3
  partials/               head.html (inline scripts), header.html, footer.html, docs-header.html, logo.html, nav-icons.html, structured-data.html
  assets/css/             site CSS (from Phase 2): common.css, code.css, fonts.css, docs.css, landing.css, examples.css (from Phase 4)
  assets/legacy/          the oracle's compiled CSS, frozen (Phase 1; deleted in Phase 2)
  assets/js/              site.js, docs.js, colors.js, picker.js, demo.js (the homepage's widgets), examples.js (from Phase 4)
  assets/fonts/           Figtree 700 normal and italic, Fira Code 400, Pacifico 400, woff2, OFL.txt
  assets/img/ (until Phase 4), assets/brand/
  vendor/femto/           femto dist/, css/, LICENSE.md, SOURCE (commit, tag, version)
  _headers  robots.txt  site.webmanifest  favicon.svg  apple-touch-icon.png  android-chrome-*.png  opengraph.png
dist/                     generated, gitignored
tests/                    harness ported from femto, divergences/, behavior/, static_checks.py, oracle manifest
docs/research/            01 to 05 and spike/
```

`build.mjs` uses Node built-ins and `prismjs` only, and stays under about 200 lines (212 at Phase 6, by `wc -l`).
- **Includes.** `<!-- include partials/<file> -->` markers are the only include syntax.
- **Placeholders.** `{{title}}`, `{{description}}`, `{{version}}` and, from Phase 4, `{{commit}}` are the only placeholders. The build fills `{{version}}` and `{{commit}}` from `site/vendor/femto/SOURCE`, so links to femto's files follow a re-vendor.
- **Per-route scaffolding, Phases 1 and 2 only.** Per-route mode also swaps literal markup in `docs.html` for each route (the `<main>` class, the breadcrumb's chapter, the Close link, canonical and `og:url`), fills the `<!-- docs:menu -->` and `<!-- docs:sections -->` slots, and adds route stylesheets, so `build.mjs` may run past about 200 lines until then (229 at Phase 1). Phase 3's one-page assembly removes all of it (accepted by the owner, 2026-10-31).
- **Code blocks.** They hold escaped text only, in `<code class="language-…">`.

## URL inventory

| URL | Phases 1 and 2 | From Phase 3 |
|---|---|---|
| `/`, `/examples`, `/demo` | static pages | same; from Phase 4 `/examples` holds femto's own examples and `/demo` is not built (404; Open questions 1 and 5) |
| `/docs` | the Quick start page, per route | the one docs page |
| `/docs#<id>` | — | that section |
| `/docs?theme=<color>` | — | the docs page in that color |
| `/docs/<route>` for the 30 other kept routes | one static page each, at parity | 404 (not built) |
| `/docs/version-picker/<color>` ×19 | one static page each, at parity | 404; the same view is `/docs?theme=<color>#version-picker`, and from Phase 4 `/docs?theme=<color>#theme-picker` (Open question 3) |
| `/docs/`, `/docs.html` | 308 to `/docs` | same |
| The Decision 5 routes, and anything else | 404 | 404 |

The per-route pages of Phases 1 and 2 exist only to compare with the oracle route by route.

## Conversion rules

**Source of truth.** For markup, the oracle's hydrated DOM for each route, captured in Phase 0. A one-time script turns each route's captured `<main>` into a section file:
- it strips React's comment markers, Remix's scripts and preloads, and hashed asset URLs;
- it replaces highlighted spans with escaped source text in `<code class="language-…">`.

The script's output is then edited by hand into readable HTML. Use the JSX only for intent: which parts are interactive, and which text is generated. The script lives in `tests/` and ships nothing.

**Markup.**
- Keep the oracle's elements, classes, attributes and order through Phase 2.
- Plain `<a>` replaces Remix `Link`. External links keep `target="_blank" rel="noopener noreferrer"`. `aria-current="page"` on header and footer links is written by the build for the page's own path.
- **Phase 3 changes.** It removes the subheading anchors, the per-route table of contents and the per-route wrappers, applies Decision 13's id renames, and points every link into the docs at `/docs#<id>`.
- Icons stay inline SVG, with any internal id made unique, until Decision 17 makes all but the brand marks and femto's logo characters, which Decision 18 writes into `<span role="img">`.
- `href="#"` controls that are really buttons stay as they are through Phase 3, for parity, and are listed as Phase 4 accessibility candidates.

**JavaScript.**
- ES modules with `type="module"`. Widgets attach through `data-` attributes from Phase 3. In Phases 1 and 2 they bind to the oracle's own markup (ids, classes, `aria-` attributes, structure), because any added attribute is a parity difference with no category.
- No global state shared between widgets. One modal helper per dialog. Intervals run only while their element is on screen.
- Every behavior in 01 §2 is either rebuilt or listed there as dropped.
- Phase 1 already makes some of Phase 3's widget fixes, with their widgets: the color modal's focus and Tab handling, the swatch focus and the restored font-size switch (tests/README.md, Behavior, Expected failures; confirmed by the owner, 2026-10-31).
- The typing demo is hand-written (Risks: TypeIt license).
- The one-page spy starts from `docs/research/spike/docs.js`.
- The breadcrumb's `is-sticky` class comes from a per-frame scroll and resize check, not 01 §2's IntersectionObserver: the breadcrumb is sticky at `top: -1px`, and a box that moves in sub-pixel steps can pass from not stuck to stuck without crossing an observer threshold (`breadcrumb()` in `site/assets/js/docs.js`).

**CSS.**
- Phase 1 changes no CSS. Only font `url()`s in the frozen copies point at `/assets/fonts/`.
- Phase 2 replaces Pico with vendored femto plus `options/responsive-spacings.css`, and moves the site rules out of the compiled output (03 §6) into flat, unlayered files that follow femto's color, prefix and never-use rules. `fonts.css` also takes the Pacifico `@font-face` rules from `assets/legacy/pacifico.css`.
- Phase 3 re-scopes `main.page-<id>` rules to `#<id>` sections, rebuilds the docs grid as side nav plus content, and replaces the oracle's `html { scroll-behavior: smooth }` with Decision 10's class.

**Text.** Phases 1 to 3 change no wording, except links to dropped routes, which are removed or pointed at `/docs`. Phase 4 rewrites content per 04, with femto's README at the vendored commit as the source of truth. The CSS variables example keeps its Pacifico heading (the owner's choice, 2026-10-31).

## Parity harness

Port femto's harness (femto `tests/`, its rig notes and Safari rules included) into `tests/`, keeping the femto owner's conventions:
- Python only through `uv run`, Selenium pinned;
- one result folder per run;
- a divergence registry where any unregistered difference fails.

Modes are in 03 §7: `oracle`, `self`, `pages`, `styles`, `behavior` and `static`. `pages` is new. It compares two documents by aligning elements on their tree path, and reports a structural difference (an element added, missing or of another tag) as its own record kind. Phase 3 added `sections`, its gate, and `a11y`, for criterion 10. The harness also has `rig`, `fast`, `selftest` and `registry`, and `uv run tests/run.py --help` lists every mode.

**Matrix:**
- **Browsers:** Chrome Beta, Firefox and Safari. Safari is serialized, and the owner does the dark pass. The harness reads Safari's `prefers-reduced-motion` from macOS, as it reads the scheme: the behavior suite runs only the checks of that motion, and the comparison modes refuse Reduce Motion. So the owner also runs the behavior suite in Light with Reduce Motion on, for the reduced-motion checks (`tests/owner-safari.sh reduced`), and reruns criterion 2's Safari legs between the tags (`tests/owner-safari.sh parity`; the owner, 2026-11-06). In the self mode a Safari cell with unregistered differences is read once more in the same session, and only a difference that repeats counts: Safari can read the oracle mid-transition, for transitions the harness cannot finish (the owner, 2026-11-07; tests/README.md, Modes).
- **Schemes:** light and dark through `prefers-color-scheme`, plus `data-theme` light and dark on `<html>` for a kitchen-sink subset.
- **Widths:** 375, 600, 800, 1100, 1300 and 1600.
- **Masked:** spinners, the typing demo, the random progress value, the `transform` and `d` of the oracle's theme-toggle SVG parts (Decision 16), the color of the link in the oracle's maintenance banner (Decision 5), and the `stroke-dashoffset` of the oracle's animated check in the version picker (Decision 17). Safari can read the last three mid-animation (2026-11-01, and the owner, 2026-11-07, for the check).
- **Normalized:** a `blob:` URL's random UUID compares as a placeholder; the rest of the value, and the element, are compared as usual. The oracle's `/docs/colors` Download link is one, made on load (the owner, 2026-10-30). It is a value rule, not a mask.
- **Normalized:** the spellings clean-css gave the oracle's minified stylesheets. A token's raw text compares without a `0` before a decimal point or the whitespace after a comma; `outline-width` compares only when `outline-style` is not `none` on both sides (`outline:0` against `outline: none`); `0px` compares as `0%` in a background position (`background:0 0` against `background: none`). The rest of each value is exact (the owner, 2026-11-02; tests/README.md, Diff rule).
- **Counted once:** an exact copy of a head data block (the JSON-LD structured data), on either side. React's hydration-error re-render on the oracle's `/docs/progress` writes the block a second time on some loads (accepted by the owner, 2026-10-31; tests/README.md, Collection).

Fast mode, for agents, is Chrome and Firefox at 375 and 1300.

**Divergence categories:**
- `dropped-route`: anything Decision 5 drops, and its layout effects: a link, menu item or footer item for a dropped route, the maintenance banner, the homepage Stats, and the page and grid heights, the menu's `--max-height` and the footer track that change without them (widened 2026-10-31).
- `femto-divergence`: one of femto's own registered differences from Pico 2.1.1, seeded from femto's `tests/divergences/` at the vendored commit.
- `merge-layout`: an intended one-page change, such as the side nav, the removed TOC and subheading anchors, the per-section `hgroup`, the breadcrumb, or smooth scrolling.
- `id-rename`: a Decision 13 rename.
- `oracle-bug`: an oracle bug the conversion fixes naturally, such as the `og:url`, the `#close` URL, or the color-scheme flash.
- `highlight`: a difference from Prism's version or grammars.
- `asset-path`: a hashed Remix build URL (`/build/_assets/<name>-<HASH>.<ext>`) that the conversion rewrites to its stable `/assets/` path, such as the palette importer image on `/docs/colors` (added 2026-10-31, when Phase 1's shell agent found it had no category). Also the palette download's on-load `blob:` URL on `/docs/colors`, which Phase 3 replaces with the build's static JSON file. Only the URL value; anything else about the element is compared as usual.
- `browser-limit`: as in femto.
- `owner-change`: a change the owner asked for that departs from the oracle: Decision 16's theme toggle icon (added 2026-11-01).

## Acceptance criteria

Each criterion is checked mechanically, and the final report gives the evidence for each.

1. The harness compares the oracle against itself with zero differences in Chrome, Firefox and Safari.
2. Each parity gate (Phases 1, 2 and 3) reports zero unregistered differences in its full matrix.
3. Every registry entry has a category from the list and a reason.
4. **Tree and packages.**
   - `git ls-files` shows none of these: `app/`, `*.jsx`, `*.scss`, `remix.config.js`, `server.js`, `jsconfig.json`, `.eslintrc.cjs`, `yarn.lock`, `scripts/`, `public/`, `functions/`, `_redirects`, `site/assets/legacy/`.
   - `package.json` has no `dependencies`.
   - Its devDependencies are `prismjs`, `wrangler` and the check tools, all pinned.
   - Its scripts are `build`, `dev`, `vendor` and `lint`, with no `deploy` script (Decision 11). `wrangler` stays a devDependency for `npm run dev` and criterion 6.
5. **Build output.**
   - `npm run build` run twice gives byte-identical `dist/` trees.
   - `dist/` contains nothing from `partials/`, `docs/sections/` or `assets/legacy/`.
   - From Phase 3 it has no `docs/` folder of per-route pages.
6. **URLs served.** Under `wrangler pages dev dist`:
   - every page in the URL inventory's last column answers 200 with no redirect;
   - `/docs/` and `/docs.html` 308 to `/docs`;
   - every old docs route path and any other path answers 404 with the `404.html` body, except the Pages-inherent paths in Risks (Cloudflare).
7. **Docs behavior.** The suite passes in Chrome, Firefox and Safari:
   - every check in 05's round 2 results, run on the real page, with the JavaScript-off deep link in each browser the rig can run without JavaScript;
   - the mobile menu opening and closing, including Escape and focus;
   - the category `<details>` and the breadcrumb chapter following the spy;
   - nav clicks jumping without animation under reduced motion;
   - the picker swapping the theme and updating `?theme=`;
   - an unknown `?theme=` value being ignored.
8. **Head.**
   - `docs.html` has its title, description, `og:title`, `og:description`, `og:url` and `rel=canonical` to `https://femto.style/docs`.
   - `sitemap.xml` lists only page URLs.
9. **Valid HTML and ids.**
   - `html-validate` passes on every HTML file in `dist/`, under `.htmlvalidate.mjs` from Phase 3: it extends `html-validate:recommended`, and every rule it turns off or changes carries a comment with the reason.
   - No page has a duplicate id.
   - Every section heading's id matches `^[a-z]+(-[a-z]+)?$`. No other heading in `docs.html` has an id.
   - Every side-nav link targets a section id, and every section has exactly one nav link.
   - No radio `name` or `details name` repeats across separate examples.
10. **Accessibility.** axe-core finds no serious or critical violation on any page, in Chrome and Firefox, light and dark, at 375 and 1300.
11. **Lint.**
    - `npm run lint` passes: `@eslint/css` `use-baseline` at `widely` on `site/**/*.css`, and ESLint on `site/**/*.js`. Every exception carries a reason.
    - No file in `site/assets/css/` contains `@layer`, `@scope`, `if(`, `@function`, `@mixin`, `@apply`, `@custom-media` or `@container style(`.
    - No color function uses `from`, and every `color-mix(` uses `in srgb`.
    - `scroll-behavior: smooth` appears only under Decision 10's class.
12. **Vendored femto.** Every file in `site/vendor/femto/` equals the commit named in its `SOURCE`, byte for byte.
13. **Content.** The content checks in 04 §3 pass.
14. **No Pico.** `git grep -il pico -- . ':!docs/research' ':!tests' ':!PLAN.md' ':!PROMPT.md'` lists only:
    - `LICENSE.md` and `README.md`;
    - `site/partials/footer.html` (the CC BY-SA attribution);
    - anything under `site/vendor/femto/`: femto's own files, pinned by criterion 12, whose `LICENSE.md` and stylesheet banners keep Pico's copyright line as its MIT license requires;
    - `site/docs/sections/migration.html`.
15. **Performance.**
    - Every page loads only same-origin resources.
    - The only render-blocking scripts are the two inline head scripts: the `?theme=` script, then the color-scheme script (Decisions 8 and 14).
    - The `/docs` HTML stays within the budget Phase 3 measures and records in Risks.
    - A cold load of `/docs#input` in Chrome records layout shift below 0.01 and ends with Input's heading within 2 px of its scroll-padding line.

## Workflow

The executing agent writes and runs a Workflow script. It scouts first, then runs one workflow per phase, and reads each result before starting the next. Agents share nothing but files, so every agent owns distinct files.

| Phase | Work | Agents | Gate | Commit |
|---|---|---|---|---|
| 0 Setup | Check the preconditions in `PROMPT.md` and stop to ask if any is missing. Branch `dev` from `main`, commit the rebrand there and tag that commit `remix-final`. Build the oracle from the tag in a temporary worktree with its locked toolchain, serve it with `wrangler pages dev`, and capture every route (HTML, hydrated DOM, CSS, screenshots, a route list). Port the harness. Write `static_checks.py` with every criterion, most of them expected to fail for now. Vendor femto (`npm run vendor`). Run the spike in Safari. | 3 or 4 | Criterion 1 in all three browsers, Safari on a light and a dark OS; the spike passes in Safari | "Add Oracle And Parity Harness" |
| 1 Static pages | First, serially: the `site/` shell, partials, `build.mjs` (per-route mode, highlighting included), the frozen legacy CSS, fonts and `site.js`. Then a pipeline over route groups (Getting started, Customization, Layout, Content, Forms, Components, plus home, examples and demo): convert to section files, then the group's widgets in `docs.js`, `colors.js`, `picker.js` and `demo.js`, then fast-mode `pages` parity, then review and up to 2 fix rounds. Then delete the Remix, React and Sass tree, `public/` and `_redirects`. | 1, then 6 to 8 | Criterion 2 for Phase 1 (`pages` against the oracle, Chrome and Firefox full matrix). The behavior suite for every widget passes in Chrome and Firefox. Criteria 4 and 5 (both except `site/assets/legacy/`, which 03 §2 copies into `dist/` until Phase 2) and 6 (Phases 1 and 2 column). | "Convert Pages To Static HTML" |
| 2 Styles | Tag the Phase 1 commit `static-multipage`. Write the site CSS files from the compiled output (03 §6), switch to vendored femto plus the responsive-spacings option, seed `femto-divergence` entries, delete `site/assets/legacy/`. Agents split by file: common and code and fonts, docs, landing. | 3, then 3 reviewers | Criterion 2 for Phase 2 (`styles` against `static-multipage`), criteria 4, 11 and 12 | "Move Styles To femto 3" |
| 3 One page | Tag the Phase 2 commit `static-femto`. Serially: switch `build.mjs` to the one-page assembly with the generated side nav, then write `docs.js` from the spike, with the inline `?theme=` script and Decision 10's class. Then in parallel: section ids, id renames and re-scoped CSS (by category); the TOC and subheading anchors removed; links into the docs pointed at `#<id>`; the per-dialog modal and the remaining widget fixes; the palette download turned from the on-load `blob:` URL into a static JSON file the build writes (01 §2, 03 §5); the picker's color links turned into `?theme=`; the mobile menu and breadcrumb. Add `.htmlvalidate.mjs` (criterion 9): fix the real errors, the 22 duplicate ids among them with Decision 13's renames, and turn off only rules that conflict with a deliberate choice, each with its reason; `static_checks.py` checks that each has one. Measure the performance budget and record it in Risks (Page size). | 1, then 4, then 3 reviewers | `pages` mode: each section's subtree against its route's `[role=document]` at `static-femto`, zero unregistered differences. Criteria 5 to 9 and 15 in Chrome and Firefox, then the behavior suite and a full `pages` pass in Safari (light and dark). Criterion 10 moved to Phase 4 (the owner, 2026-11-04): every axe violation on `/docs` comes from the oracle's markup or femto's tokens, which parity keeps through Phase 3; tests/README.md lists them. | "Merge Docs Into One Page" |
| 4 femto 3 content | Owner review of 04 §1 and the Open questions first. Then one agent per category rewrites and adds sections from femto's README, with the picker rework, homepage, footer and header. Run the content checks. | 1 scout, 6 writers, 3 reviewers (accuracy against the README, accessibility, wording) | Criteria 13 and 14, link check of `dist/`, criterion 10 (moved here from Phase 3), criteria 7 to 9 rerun | "Describe femto 3" |
| 5 Cleanup | `package.json` (Decision 3 scripts and pins), `.gitignore`, `_headers` (long caching for fonts only), `robots.txt`, `404.html`, README (develop, build, vendor, deploy) and `LICENSE.md` (keep CC BY-SA; note femto's MIT and the fonts' OFL in their folders). A `.github/workflows/check.yml` that builds and runs the static checks and lint, with no deploy. | 1 or 2 | Criteria 4, 5, 6, 11, 12 and 14 | "Finish Static Site" |
| 6 Final review | A completeness critic against 01's behavior list and every criterion. Adversarial reviewers for accessibility and keyboard, URL and history behavior across browsers, content accuracy against femto's README, and CSS target compliance. Rerun every gate touched by a fix, then the full matrix in all three browsers. | 4 or 5 | All criteria | "Address Final Review" |

Each reviewer is told to refute the work.

A route-group agent returns:

```
{group, files, status: "pass" | "fail", diffs, divergences, notes}
```

The orchestrator logs every failure. A `log()` line names every route or matrix cell that was skipped or capped.

Commit messages use a Title Case subject under 60 characters, with no body unless the diff cannot explain itself and no trailers. Commit only at passed gates. Never push.

## Repo changes

- **Delete in Phase 1:**
  - `app/`, `remix.config.js`, `server.js`, `jsconfig.json`, `.eslintrc.cjs`, `.nvmrc`, `yarn.lock`, `scripts/`;
  - `public/`: its files move to `site/`, minus `_routes.json`, `_redirects` and the unreferenced `logo.png` and `logo.svg`;
  - every Remix, React and Sass package.
  - The brand asset files the rebrand added move to `site/assets/brand/`.
- **Delete in Phase 2:** `site/assets/legacy/`.
- **`package.json`:**
  - name `femto.style`, `private: true`, `type: "module"`;
  - scripts `build`, `dev`, `vendor` and `lint`, with no `deploy` script since 2026-11-06 (Decision 11);
  - devDependencies: `prismjs`, `wrangler` (for `npm run dev`'s `wrangler pages dev` and criterion 6, no longer for deploys), `eslint`, `@eslint/css`, `html-validate`, a JS compat lint if one fits (03 §7), and `axe-core` for the harness;
  - every version pinned exactly and checked as the latest on the web;
  - `engines` and `.node-version` at the current Node LTS;
  - `package-lock.json` replaces `yarn.lock`.
- **`.gitignore`:** `dist/`, `tests/oracle/`, `tests/results/`, `.wrangler/`.
- **`LICENSE.md` and README:** keep the CC BY-SA 4.0 notice and the attribution to the Pico CSS documentation. Note femto's MIT license and the fonts' OFL in their folders.
- **`.claude/launch.json`:** holds the spike server. Replace it in Phase 1 with the `npm run dev` server.
- **The Pages project's settings, in the Cloudflare dashboard** (the owner's, outside the repository): the build settings Decision 11 records (Framework preset None, build command `npm run build`, output directory `dist`, root directory empty, build system v3), production branch `main`, and preview deployments for every other branch.
- **The femto.style zone's settings, in the Cloudflare dashboard** (the owner's): the zone features that act on `femto.style` but not on `femto-style.pages.dev`, each with its step in Risks (Cloudflare): Email Address Obfuscation off, Browser Cache TTL at Respect Existing Headers, Always Use HTTPS on, and Web Analytics' automatic setup disabled.

## Risks and items to verify first

| Item | Why it matters |
|---|---|
| The oracle must build | `.node-version` says 18.19.0; the machine has Node 24.22.0 and no yarn. Phase 0 tries `npx yarn@1.22.22 install --frozen-lockfile` under Node 24, then under an 18 or 20 runtime fetched with `npx -p node@…`. `build:fetch-stats` needs the network (stats fall back to 0) and `build:v1-documentation` needs `rsync`. |
| The rebrand was uncommitted | The oracle must include it. Resolved 2026-10-30: the owner chose to commit it as the first commit on `dev`, which `remix-final` tags. |
| femto's working tree | `npm run vendor` refuses a dirty tree. Resolved 2026-10-30: the owner first approved 65453b74 ("Prepare 3.0.0 Alpha 1"), then rewrote femto's `dev` and chose its latest commit "for now": e3b141f3 ("Remove Composer Package", 3.0.0-alpha.1), vendored from a clean `../femto`. On 2026-10-31 the owner moved it to the latest commit on femto's `main`: 7bcd5758 ("Register Safari-Only Computed Values From The Bug Fixes", still 3.0.0-alpha.1), 30 commits of rendering fixes later. On 2026-11-03 the owner moved it to femto's latest commit, d4f8d1fd ("Add Android Browsers", on `dev` and `main`, still 3.0.0-alpha.1), whose only change to the vendored files is a comment in `css/forms/input-date.css`. On 2026-11-04, before Phase 4, the owner moved it to femto's latest commit, 8cd05767 ("Add A Script For Both Safari Passes", still 3.0.0-alpha.1); its only change to the vendored files is 1f7c75b2's "Drop The Bottom Margin On Typed Modal Footer Buttons" (`css/components/modal.css` and `dist/`). On 2026-11-05, during Phase 4, the owner moved it to c608ee06 ("Darken Dark Hover Backgrounds For Contrast", on femto's `dev`, still 3.0.0-alpha.1), femto's fix for criterion 10's last failure: in azure and eight other themes `--femto-primary-hover-background` takes its light value in both schemes, so white text on a hovered, focused or current button reaches 4.5:1 in dark (`tests/README.md`, owner decision 15). On 2026-11-05, during Phase 5, the owner amended c608ee06 into 33d4dc6f ("Darken Dark Hover Backgrounds For Contrast", on femto's `dev` and `main`, still 3.0.0-alpha.1), whose only change to the vendored files drops ten comment lines from `css/themes/` and `css/tokens/schemes.css`, and moved the site to it, so `SOURCE` names a commit on femto's branches that the GitHub check can fetch. Re-vendor when femto moves on; `SOURCE` records the commit and the refs that reach it. The vendored commit sets what Phase 4 describes. |
| femto is alpha and unpublished | Names and files may change before 3.0.0, and `npm/@leoherzog/femto@3` URLs 404 until the first publish. Re-vendoring is one command, and criterion 13 then flags stale docs. The plan was to go live after femto's first publish (04 §3), but production went live from `main` on 2026-11-06, before it (Decision 11). The owner chose no site change, so the docs keep femto's README's wording, whose jsDelivr and npm instructions for the alpha fail until the alpha is published (the owner, 2026-11-06). |
| Safari | The spike ran only in Chrome and Firefox. Phase 0 must establish three Safari behaviors: whether `document.write` of the theme `<link>` applies before the first paint, what back does for a `#hash` entry, and the 100-calls-in-10-seconds history limit, past which WebKit throws (the spy wraps `replaceState` in `try`). Safari gates need femto's rig rules: Safari quit, the machine idle, and the owner's dark pass. Established in Safari 27.2 (2026-11-01, `docs/research/05-spike.md`): `document.write` of the theme `<link>` applies before the first frame (so do the other two methods); back restores a `#hash` entry's exact position; call 101 within 10 seconds throws a `SecurityError`, and the spy keeps working through it. `location.reload()` returns to the `#hash` heading, which the owner accepted on 2026-11-02. |
| `document.write` | It is the only way the spike found to apply `?theme=` before the first paint in both Chrome and Firefox (02 §5). Lighthouse flags `document.write`; the warning targets cross-origin scripts, and this one writes a same-origin `<link>` from an allow-list. If a browser ever blocks it, the fallback is a script-inserted `<link>`, which shows azure for one frame. |
| Back in Chrome | Chrome returns to the `#hash` heading, the start of the section, rather than the exact position, as Firefox does. Accepted (05). |
| Hidden tabs throttle the spy | rAF and timers run about once a second in background tabs (05). Behavior checks run headless or in a foreground window. |
| Highlighting parity | The oracle flattens Prism tokens through react-syntax-highlighter. Its "html" resolves to refractor's `html` alias, Prism `markup` with CSS and JS inlined: prism-light's `registerLanguage` ignores its name, so `jsx` was registered only as `jsx`. The build must reproduce the same spans, or register `highlight` differences. Proven in Phase 1's pilot: `build.mjs` with Prism 1.30 `markup` matches all 298 distinct oracle code blocks (`node tests/convert/highlight-check.mjs`). |
| TypeIt license | TypeIt is GPL-3.0 or commercially licensed. The static site uses a hand-written typing loop instead. The animation is masked in parity runs and checked by behavior tests (it types, loops, and the form state follows). |
| Page size | About 5,900 lines of route JSX, about 250 highlighted code blocks, about 84 live examples and 400 color swatches on one page, with `femto.colors.min.css` (4.4 KB with Brotli) loaded up front. Phase 3 measures transfer size, DOM size and the spy's cost per frame, records the budget here in the form criterion 15's check reads (one sentence that says "budget" and then gives each limit as a size, raw or "with Brotli" or "gzipped"), and only then considers trimming, such as building the swatches from JSON on first view. `content-visibility` stays out (Decision 12). Measured in Phase 3 (2026-11-04, headless Chrome Beta 158): `dist/docs.html` is 800,000 bytes raw, 52,594 gzipped (level 9) and 33,497 with Brotli (quality 11); its DOM has 17,151 elements, 13,160 of them Prism's token spans in the 126 code blocks; scrolled from top to bottom at 200 px a frame, the spy's frame callback takes 0.06 ms a frame on average and at most 0.8 ms at 1300 px (2.8 ms with the CPU slowed 4 times), all the site's scroll work at most 2.2 ms at 375 px, and no frame is a long animation frame, so nothing is trimmed. Measured again in Phase 4 (2026-11-05), with nine more sections and femto 3's content: 806,898 bytes raw, 63,085 gzipped and 41,990 with Brotli, over Phase 3's gzip and Brotli limits, so the owner raised those two rather than trim (2026-11-05). The `/docs` HTML budget is 900 KB raw, 70 KB gzipped and 48 KB with Brotli. With Decision 17's character icons (2026-11-05) it is 747,008 bytes raw, 60,551 gzipped and 41,179 with Brotli. With Decision 18's icon markup (2026-11-06) it is 742,723 bytes raw, 60,582 gzipped and 41,150 with Brotli. With Phase 6's fixes (2026-11-06) it is 743,761 bytes raw, 61,010 gzipped and 41,446 with Brotli. |
| The picker recolors the page | femto themes are `:root, :host` rules, so a theme color recolors the whole page, as the oracle's color routes did. With `?theme=` in the URL, reloads and shared links keep it. Phase 4 may scope a preview to a shadow root instead, which femto supports through `:host`. |
| Search and previews | One URL, by choice (Decision 9). Sections will not rank as separate pages, and every shared link previews as the docs page. |
| Cloudflare | Pages still works and has no sunset date, but Cloudflare steers new projects to Workers (02 §2). Check where femto.style's DNS lives before any move. Without a top-level `404.html`, Pages serves `/` for unknown paths. Pages also answers some paths itself, and Decision 11 leaves no `_redirects` to change them: `/404` serves the 404 page with status 200, and `/404.html`, `/index`, `/index.html`, `/docs/index` and any page's `.html` name 308 to the clean URL. Accepted (the owner, 2026-10-31); criterion 6 exempts them, and `static_checks.py` probes each one (`PAGES_INHERENT`). Since 2026-11-06 Pages builds from Git (Decision 11), and its build settings live in the dashboard, outside the repository. They were wrong on the first Git deploy: on 2026-11-06 the output was the unbuilt `site/` folder, so production showed raw include markers and an empty `/docs`, had no `sitemap.xml`, and served `partials/` and `docs/` as public files. The owner's step is to set them as Decision 11 records and redeploy. Pages builds and deploys a push to `main` whether or not `check.yml` passes: it does not wait for GitHub's checks. Some features of the femto.style zone change `femto.style`'s responses but not `femto-style.pages.dev`'s, each with the owner's step in the dashboard. Email Address Obfuscation rewrites `/examples`' addresses into `[email protected]` placeholders and adds a decoder script, which cannot reach the two in the Sign up and Contact mockups' shadow roots: turn it off. Browser Cache TTL gives CSS, JavaScript, PNG, SVG and `robots.txt` 4 hours (`max-age=14400`) in place of Pages' `max-age=0`, so a returning reader can get new HTML with old CSS and JavaScript: set it to Respect Existing Headers. The `www` redirect to the apex matches only https, so `http://www.femto.style/` times out with a 522: turn on Always Use HTTPS. Web Analytics' automatic setup injects a beacon script from `static.cloudflareinsights.com` into every page, a cross-origin load against criterion 15: disable the automatic setup. Speed Brain adds a `speculation-rules` header for same-origin prefetch, which is harmless. |
| Tool versions | The owner wants the latest version of every tool, checked on the web at install; Phase 5 checked every pin again on 2026-11-05 and moved three (eslint-plugin-baseline-js to 0.7.7, html-validate to 11.18.0 and wrangler to 4.158.0). Phase 6 checked them again on 2026-11-06 and moved html-validate to 11.19.0, published that day; `npm audit fix` moved source-map-js, under `@eslint/css`, from 1.2.1 to 1.2.2 in `package-lock.json` only, which closes its high advisory. That leaves 3 moderate `minimatch` advisories under eslint, with no fix inside eslint 10.14.0's dependency ranges (the first patched `minimatch` is 11.0.1), and no criterion covers them. The one exception is the oracle's own locked toolchain, which only rebuilds the oracle. |

## Open questions for the owner

Answered by the owner on 2026-11-04, before Phase 4, with 04 §1's disposition and its new sections and menu placement approved as proposed:

1. **Examples page.** Neither: replace the Pico CodeSandboxes with the site's own set of simple mockups of web page widgets, forms and pages, all in vanilla femto, ideally all on the one `/examples` page.
2. **Migrating from Pico.** Yes, a docs section under Getting started, from the README.
3. **Picker.** "Theme picker", section id `theme-picker` (`/docs?theme=<color>#theme-picker`).
4. **Header.** A plain version label linking to `/docs`.
5. **`/demo`.** Dropped: not built from Phase 4 (404). The homepage keeps its typing demo.

## References

| File | Contents |
|---|---|
| `docs/research/01-site-inventory.md` | Routes, colliding ids, behaviors to rebuild, libraries, styles and their Pico Sass dependencies, build and hosting |
| `docs/research/02-one-page-docs.md` | URLs and section ids, Cloudflare Pages behavior, search and link previews, the scroll spy, `?theme=` |
| `docs/research/03-static-architecture.md` | File tree, the build, vendored femto, highlighting, JavaScript modules, CSS route, checks and rig |
| `docs/research/04-femto-content.md` | Per-section disposition, new sections, content checks |
| `docs/research/05-spike.md`, `docs/research/spike/` | The one-page prototype and its results in Chrome and Firefox |
| `../femto/PLAN.md`, `../femto/tests/README.md` | femto's conversion spec, rig and harness, which this plan reuses |
