# 03: Static architecture, build and tooling

How the site is laid out once React, Remix and Sass are gone, what the one build step does, where femto, fonts and highlighting come from, and how femto's parity rig is reused to check the conversion.

## Verdict

Hand-author plain HTML fragments, plain CSS and plain ES modules in `site/`. One `build.mjs` (Node built-ins plus a pinned Prism) turns them into `dist/`. It does five things:
1. copies files;
2. expands includes for the head, header and footer;
3. assembles the one docs page from one file per section, with the side nav generated from a menu file;
4. pre-highlights code;
5. writes the sitemap.

It never transforms CSS or JavaScript: no bundling, no minifying, no hashing, no prefixing.

femto is vendored from a recorded femto commit and served from the site's own origin.

The site's CSS starts as the oracle's compiled CSS (Phase 1). It then becomes:
- femto's `dist/femto.min.css`, `options/responsive-spacings.css` and, on the docs page, `dist/femto.colors.min.css`;
- plus hand-authored site CSS moved from the compiled output (Phase 2).

That is the same "moved text" route femto took.

femto's Selenium rig runs the parity, behavior and Safari checks. Its harness gains a mode that compares two documents instead of two stylesheets.

## 1. File tree

```
build.mjs                 npm run build: site/ into dist/
site/                     hand-authored source; every file here is plain HTML, CSS, JS, JSON or an asset
  index.html  examples.html  demo.html  404.html
  docs.html               the docs shell: head, header, side nav slot, sections slot, footer
  docs/
    menu.json             categories and sections in order: id, title, description
    sections/<id>.html    one section each: its hgroup (the h1 carries the id), content and edit link
  partials/               head.html (inline scripts), header.html, footer.html
  assets/
    css/                  site CSS (Phase 2): common, code, fonts, docs, landing
    legacy/               the oracle's compiled CSS, frozen (Phase 1 only, deleted in Phase 2)
    js/                   site.js, docs.js, colors.js, picker.js, demo.js (ES modules)
    fonts/                Figtree 700 normal and italic, Fira Code 400, Pacifico 400, woff2 only, plus OFL.txt
    img/  brand/          images; femto logo files kept as plain assets
  vendor/femto/           femto's dist/, css/ and LICENSE.md at the commit named in SOURCE
  _headers  robots.txt  site.webmanifest  favicon.svg  apple-touch-icon.png  opengraph.png  …
dist/                     generated, gitignored, deployed
tests/                    harness ported from femto, oracle manifest, divergences, behavior tests, static checks
docs/research/            these reports and the spike
```

Pages are full HTML documents. `<!-- include partials/header.html -->` markers pull in the shared parts, and `{{title}}`, `{{description}}` and `{{version}}` are the only placeholders. That keeps the source readable as HTML and the build too small to need a template language.

## 2. The build

`npm run build` runs `node build.mjs`, which does only this:

1. **Copy.** Deletes `dist/`, then copies `site/` minus `partials/`, `docs/` and `assets/legacy/`. During Phase 1, `assets/legacy/` is copied.
2. **Include.** Replaces each include marker with the partial's text, and sets `aria-current="page"` on header and footer links to the page's own path.
3. **Assemble docs.**
   - Phases 1 and 2: each section is wrapped in the old per-route docs layout and written to its old route path, so the oracle can be compared route by route.
   - Phase 3 on: `menu.json` drives one `docs.html`, with the side nav (categories as `<details>`, one link per section) and the sections in menu order.

   The section files do not change between the two modes.
4. **Highlight.** Pre-highlights code, described in §4.
5. **Sitemap.** Writes `sitemap.xml` from the list of pages.

The output is deterministic: the same input gives byte-identical output, with no timestamps.

The build stays under about 200 lines. Its only dependency is `prismjs`, as a pinned devDependency.

`npm run dev` combines `node --watch-path=site build.mjs` with `wrangler pages dev dist`, which emulates `_headers` and Pages' HTML handling. `npm run deploy` is `npm run build && wrangler pages deploy dist`, the same direct-upload model as today's `pages:deploy`.

## 3. femto, vendored

- **Source.** `site/vendor/femto/` holds femto's `dist/`, `css/` and `LICENSE.md`, copied by `npm run vendor` from a femto checkout. The default checkout is `../femto`. The script refuses a dirty tree and writes `SOURCE` with the commit, the tag (if any) and `package.json`'s version.
- **Why vendored.** `@leoherzog/femto` is not on npm yet: `npm view @leoherzog/femto` returned 404 on 2026-10-30. jsDelivr's `npm/@leoherzog/femto@3` URLs therefore 404 too. (The package was planned as `femto.css`; the owner named it `@leoherzog/femto` on 2026-10-30, and femto removed its Composer package at e3b141f3.)
- **Check.** A static check compares every vendored file with `git show <commit>:<path>` in the femto repository when it is available.
- **Every page** loads `vendor/femto/dist/femto.min.css`, then `vendor/femto/css/options/responsive-spacings.css`, then the site CSS.
- **The docs page** also loads `dist/femto.colors.min.css` up front, and `css/themes/<color>.css` when the URL has `?theme=` (02 §5).
- **Sample code** that shows femto's files, such as the variable dumps on today's CSS variables page, is dropped in Phase 4 in favor of links to those files (04).

## 4. Highlighting

- **Prism at build time, class-only output.** Unfurlers, no-JS readers and the first paint all get colored code, and the page ships no highlighter. Prism is 7.3 KB gzipped for markup, CSS, clike and JS, plus 3 KB for bash, so client-side highlighting would have been cheap too. The build-time choice is about the first paint and parity, not size.
- **Matching the oracle's spans.** The oracle's spans are react-syntax-highlighter's: Prism tokens flattened so that each text run is one `span` whose classes are the union of its ancestors' (`token tag attr-name`). `_code.scss` selects on those unions. The build walks `Prism.tokenize()` and emits the same flattened spans.
- **Grammars.** The oracle's "html" is Prism's `markup` grammar (refractor's `html` alias, with CSS and JS inlined). prism-light's `registerLanguage` ignores its name argument, so the `jsx` registration only added `jsx`. Phase 1's pilot proved it: `markup` gives the oracle's spans on all 298 distinct code blocks. (Corrected 2026-10-31; this said `jsx`.)
- **How the build finds code.** It highlights the content of `<code class="language-…">`, whether in `<pre>` or inline. Source code blocks hold escaped text only (`&lt;`), which a static check enforces, so a simple scan suffices.
- **Alternatives.** Shiki is more accurate on new CSS syntax, but emits inline styles by default and is far larger. highlight.js uses different class names. Neither would reproduce the oracle's spans.

## 5. JavaScript

| Module | Pages | Replaces |
|---|---|---|
| inline in `partials/head.html` | all | The color-scheme flash: it reads `localStorage.femtoColorScheme` (JSON, same key and format as today) and sets `data-theme` before first paint. On the docs page only, it then writes the `?theme=` stylesheet with `document.write` (02 §5). |
| `site.js` | all | theme toggle, fixed header, copy buttons, the modal helper (classes, 400 ms animations, Escape, scrollbar width), `preventDefault` on example forms |
| `docs.js` | docs | Side menu (categories, mobile off-canvas, Escape, `aria-expanded`), sticky breadcrumb, small demo widgets. From Phase 3, the spy, the `#hash` and title sync, and click-scoped smooth scrolling (02 §4). |
| `colors.js` | docs | color modal (native `<dialog>` focus, arrow keys), static palette JSON |
| `picker.js` | docs | version picker (Phase 1 parity; reworked in Phase 4, with `?theme=`) |
| `demo.js` | home, demo | The typing demo, as a small hand-written type, move, delete, pause and exec queue in place of TypeIt. TypeIt is GPL-3.0 or commercially licensed. |

Widgets attach through `data-` attributes, so one module can serve several sections. Module scripts are deferred; the inline head script is the only render-blocking script.

## 6. CSS, moved from the compiled output

femto's lesson (femto `docs/research/01-sass-inventory.md` §4, `05-spike.md`) was that moving compiled text beats converting Sass. For the site:

- **Phase 1** links the oracle's compiled CSS files as they are, frozen in `site/assets/legacy/`. The only edits are font `url()`s pointing at `/assets/fonts/` and the removed source-map comments. Markup and JavaScript change while the CSS stays fixed, so any computed-style difference is a markup or script bug.
- **Phase 2** replaces the Pico part of `main.css` with vendored femto plus the responsive-spacings option, and the site part with hand-authored files.
  - **Starting text.** Compile `main.scss` once without its `@use "pico"` line, in a temporary folder at the oracle tag with its locked Sass. That isolates the commons rules. `docs.css` and `landings.css` hold no Pico rules already.
  - **Edits.** Restore comments from the SCSS. Drop the autoprefixer output that femto's prefix table drops. Write literal breakpoints. Keep computed colors as literals, or `color-mix(in srgb, …)` where a token is involved.
- **Phase 3** re-scopes the `main.page-<id>` rules to `#<id>` sections, and moves the docs grid from per-route children to the one page. That grid is the side nav and content; the right-hand table of contents goes.
- **Femto's rules apply to the site CSS:** flat, unlayered, no `@scope`, no relative color syntax, `color-mix(in srgb, …)`, and Baseline Widely Available lint through `@eslint/css`.
- **Expected differences.** Phase 2's comparison should show only femto's registered divergences from Pico 2.1.1, chiefly `light-dark()` token text and the Decision 12 natural fixes. Copy femto's `tests/divergences/` at the vendored commit as seed entries.
- **Smooth scrolling.** The oracle's `html { scroll-behavior: smooth }` becomes a class that only `docs.js` sets during a nav click (02 §4).

## 7. Checks, reusing femto's rig

The machine already runs femto's rig:
- Chrome Beta 158, Firefox 160 and Safari 27.2, driven by Selenium 4.52 under `uv`;
- `safaridriver` enabled;
- dark mode by CDP or by pref, with a separate Safari dark pass by the owner.

The site's `tests/` ports what it needs:

| Mode | Compares | Used in |
|---|---|---|
| `oracle` | Builds the oracle from tag `remix-final` in a temporary worktree, serves it with `wrangler pages dev`, and captures each route's server HTML, hydrated DOM, compiled CSS and screenshots. Output goes to `tests/oracle/` (gitignored, rebuilt from the tag). | Phase 0 |
| `self` | The oracle against itself. Must find nothing. | Phase 0 |
| `pages` | Two documents, oracle route against static route. Elements are aligned by tree path. Attribute sets and every computed style are compared, plus screenshots as a secondary check. Element-tree differences are their own record kind. In Phase 3, a section's subtree is compared with its route's content. | Phases 1 and 3 |
| `styles` | One document, two stylesheet lists (femto's native mode). | Phase 2 |
| `behavior` | Scripted checks of every widget and of the docs spy, URL, history and `?theme=`. The spike's `test_spike.py` grows into this. | Phases 1, 3, 5 |
| `static` | The checks listed in PLAN.md's acceptance criteria. | every phase |

The matrix: Chrome, Firefox and Safari; light and dark; one width per breakpoint band (375, 600, 800, 1100, 1300, 1600); `data-theme` legs on a subset.
- **Fast mode** for agents: Chrome and Firefox, at 375 and 1300.
- **Full mode** at each gate, with Safari serialized and the owner's dark pass.
- **Masked areas:** spinners, the typing demo and the random progress value.

Other dev-only checks:
- `html-validate` on `dist/`: no duplicate ids, valid nesting.
- `axe-core`, injected through Selenium: no serious or critical violations.
- `@eslint/css` with `use-baseline` at `widely` on `site/**/*.css`.
- ESLint on `site/**/*.js`, with a compat or Baseline plugin if a maintained one supports ESLint 10. Phase 0 checks.

Like femto, every tool is at its latest version, checked on the web when it is installed. The one approved exception is the oracle's locked toolchain (Sass 1.85.1 and the yarn lock), which only rebuilds the oracle.

Hidden or background tabs throttle `requestAnimationFrame` and timers, which made the spy look broken in a hidden browser pane during the spike. Behavior checks run in headless or foreground windows only.
