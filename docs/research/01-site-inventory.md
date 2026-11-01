# 01: Inventory of the Remix site

What the static conversion has to carry over: every route, every behavior that runs after hydration, every library, the styles and their Pico Sass dependencies, and the build. Paths are relative to the repository root at the start of the conversion (main, 2026-10-30, with the uncommitted rebrand in place).

## Verdict

The site is small and mostly static. About 7,850 lines of route JSX, 3,355 lines of SCSS and 25 icon components produce pages whose only real JavaScript is:
- a theme toggle;
- copy buttons;
- one global modal;
- the docs menu and table of contents;
- the version picker;
- the colors modal;
- a handful of demo widgets;
- the homepage typing demo.

Everything else is markup that React renders once.

Three things make the merge into one docs page harder than concatenation:
- **Colliding ids.** Hand-written heading ids collide across routes: `validation-states` 7 times, `disabled` 5 times, and 15 more. This stopped mattering once subheadings lost their ids (02 §1). Form control ids collide too, and still need renaming.
- **Shared modal state.** One global modal flag is shared by two routes' dialogs.
- **Per-route scoping.** Twelve page stylesheets are scoped by a per-route class on `<main>`.

All of these are mechanical to fix.

The site's CSS is Pico 2.1.1 compiled with `$css-var-prefix: "--femto-"` and `$enable-responsive-spacings: true`, plus about 3,300 lines of site SCSS. That is femto's `dist/femto.min.css` plus `options/responsive-spacings.css`, plus the site's own rules. The site's own rules use Pico's Sass only for:
- the prefix;
- the breakpoint map;
- the palette variables;
- the color utility and theme generators.

## 1. Routes

Docs routes render inside `app/routes/docs.jsx` (fixed header, breadcrumb, side menu). Each route then renders its own `hgroup`, an optional table of contents, and `div#content[role=document]` holding `<section>`s and an "Edit on GitHub" link.

| Group | Routes (URL under `/docs`) | Lines | Notes |
|---|---|---|---|
| Getting started | `` (Quick start), `version-picker`, `color-schemes`, `classless`, `conditional`, `rtl` | 162, 94 + 7 + 19×21, 182, 180, 228, 61 | The version picker is a nested layout plus 20 color routes (azure is the index) that differ only in color name and stylesheet. |
| Customization | `css-variables`, `sass`, `colors` | 256, 269, 276 | `colors` loads `color-utilities.css` and drives the color modal. |
| Layout | `container`, `landmarks-section`, `grid`, `overflow-auto` | 187, 130, 139, 72 | |
| Content | `typography`, `link`, `button`, `table` | 223, 85, 212, 198 | |
| Forms | `forms` (overview), `forms/input`, `textarea`, `select`, `checkboxes`, `radios`, `switch`, `range` | 272, 322, 189, 252, 213, 179, 147, 59 | `/docs/forms` is a sibling of the `forms/*` routes, not a layout. |
| Components | `accordion`, `card`, `dropdown`, `group`, `loading`, `modal`, `nav`, `progress`, `tooltip` | 222, 72, 467, 208, 73, 276, 537, 88, 105 | |
| About | `maintenance`, `v2`, `mission`, `usage-scenarios`, `brand`, `built-with` | 79, 247, 81, 99, 176, 97 | Dropped (Decision 5). |

Other pages:
- **`/`:** hero with the typing demo, stats, features and comparison.
- **`/examples`:** cards from `app/data/examples.json`, which all point at `github.com/picocss/examples` and CodeSandbox.
- **`/demo`:** a noindex capture page for the hero demo.
- **Pico v1 docs:** `/docs/v1/`, copied by `scripts/build-pico-v1-documentation.js` from `@picocss/pico-v1`.

The menu (`app/data/documentationMenu.json`) lists the 40 docs routes in the order above. The 19 color routes are not in it.

### Ids that collide when the routes share one page

The heading ids below are dropped in Phase 3: on the one page only section headings carry ids (02 §1). They are listed because they explain that choice. The form-control, wrapper and SVG ids further down still have to be made unique.

`Heading.jsx` puts the id on an inner `<a href="#id" id="id">#</a>`, not on the heading. Every id is a hand-written string, repeated by hand in the route's table of contents data.

| Id | Routes |
|---|---|
| `validation-states` | dropdown, forms/checkboxes, forms/input, forms/radios, forms/select, forms/switch, forms/textarea |
| `disabled` | button, forms/input, forms/select, forms/switch, forms/textarea |
| `usage-from-cdn`, `starter-html-template`, `usage-with-sass` | three each: Quick start, conditional, version picker (and colors for the Sass one) |
| `readonly`, `horizontal-stacking`, `indeterminate`, `search`, `buttons`, `button-variants`, `usage-with-group`, `usage`, `example`, `root-container`, `demo` | two each |
| `overflow` | twice inside `docs.nav.jsx` alone |

Three anchors equal a route slug, so they collide with section ids if sections are named after their routes:
- `dropdown`, in forms/select;
- `version-picker`, in v2;
- `color-schemes`, in table.

Other duplicate ids on a merged page:
- **Form controls.** The labels `for` `hindi`, `swahili` and `navi` appear in both checkboxes and radios, so clicking the radios' labels would toggle the checkboxes. The `aria-describedby` targets `valid-helper` and `invalid-helper` appear in both input and textarea.
- **Per-route wrappers.** `div#content` appears 40 times and `aside#table-of-contents` 31 times.
- **SVG internals.** `path#check-icon` repeats per animated check icon, and `clipPath#theme-toggle-cutout` per theme toggle.

Radio group names and the one `details name` group are already unique across routes.

Links that point into another route's anchors:
- group → `/docs/forms/input#search`;
- input → `/docs/button#variants`;
- container → `#semantic-containers`, a classless-only section.

`docs.v2.jsx:240` has a relative link without a leading slash.

## 2. Runtime behavior to rebuild

"Static" means nothing to do once the HTML exists.

| Where | Behavior | Static replacement |
|---|---|---|
| `contexts/PageContext.jsx` | Theme stored in localStorage `femtoColorScheme` as JSON (`"dark"`), synced across tabs. `data-theme` is set on `<html>` only when a value is stored. The toggle stores the opposite of the current theme. Until hydration the server renders no `data-theme`, so a stored choice flashes. | A blocking inline `<head>` script that sets `data-theme` from the same key and format, plus a toggle in `site.js`. |
| `components/Nav.jsx` | The theme toggle `a[href=#]` swaps its `aria-label` and the `moon` class on its icon. The version dropdown is a `details.dropdown`. | `site.js` |
| `components/Header.jsx` | On docs only: `is-fixed-above-lg`, plus `is-fixed` after `scrollY > 20` (an unthrottled listener). | `site.js`, passive and rAF-throttled |
| `components/Code.jsx` | A copy link (`a.copy-to-clipboard`, `data-tooltip="Copy to clipboard"`). On click it copies, swaps the copy icon for an animated check, sets the tooltip to "Copied", then reverts after 1 s and blurs. | `site.js` with `navigator.clipboard.writeText` (Widely available). |
| `contexts/ModalContext.jsx` | **One global flag.** Open sets `html.modal-is-open.modal-is-opening`, then drops `-opening` after 400 ms. Close uses `-closing` for 400 ms. Escape closes. `--femto-scrollbar-width` is measured with a buggy `screen.height` test. `docs.modal.jsx` and `docs.colors.jsx` both bind dialogs to this flag, so on one page they would open together. | A per-dialog helper in `site.js`. femto's `css/components/modal.css` already styles the classes. |
| `docs/DocumentationMenu.jsx` | Opens the category that contains the current route and marks its summary and link `aria-current`. Mobile off-canvas: `.is-open-on-mobile`, opened from the breadcrumb and closed by its own close link or any menu link. Scroll lock is CSS `:has()`. `--max-height` is measured on mount and resize. There is no Escape and no `aria-expanded`. | `docs.js`. Phase 3 drives it from scroll. |
| `docs/Breadcrumb.jsx` | Its "Documentation" link opens the mobile menu. `.is-sticky` comes from a debounced scroll test. The chapter label is the route's category. | `docs.js`, with an IntersectionObserver for stickiness |
| `docs/TableOfContents.jsx` | ghostui `Scrollspy`. The active entry is the **first** section whose box is in view, with an offset of −2 × header height, and the last section at the page bottom. | `docs.js`. Phase 3 replaces it with the one-page spy. |
| `docs/ColorModal.jsx` | Opens from 400 swatch buttons. Arrow keys move through families and shades. Clicking the backdrop or the close link (which leaves `#close` in the URL, a bug) closes it. No focus management. | `colors.js`, with `<dialog>`-native focus |
| `routes/docs.colors.jsx` | Palette JSON download from a Blob URL made on mount. | A static JSON file written by the build. |
| Version picker (`VersionPickerContext`, `…Customization`, `…Usage`, `ThemePreview`) | A select (3 bases), a conditional switch and 20 swatch links (route changes). Generated, re-highlighted code for CDN, Sass and the starter template. The color route loads `custom-themes/<color>.css`, which recolors the whole page. | `picker.js`, swapping one theme `<link>`. Phase 4 reworks it for femto 3. |
| Small widgets | Grid column ± demo (`docs.grid.jsx`). Random progress value every 5 s, with an interval recreated on every render (`docs.progress.jsx`). Indeterminate checkbox set from a ref. Font-size table px/rem switch. `thead` that takes the inverse theme (`docs.table.jsx`). The color-schemes page's own toggle. | small `data-`-hooked functions in `docs.js` |
| `homepage/Demo/*` | TypeIt types a code sample and drives about 30 pieces of form state through `exec` callbacks, looping forever. The large or small code variant is picked at 1280 px. Maximize controls are dead code. | `demo.js`, a hand-written typing loop (see Risks in PLAN.md: TypeIt is GPL-3.0) |
| `Logo.jsx` | `animated` for 1 s after a client-side route change. | Dropped: a static site has no client-side route changes. |
| Remix `is-loading`, swatch `aria-busy` during navigation | Navigation feedback. | Dropped |

Forms in examples with no submit handler navigate on Enter: `docs.forms._index.jsx:118`, and both forms in conditional. Example forms on the static site need one delegated `submit` handler that calls `preventDefault`.

## 3. Libraries

| Package | Use | Replacement |
|---|---|---|
| react, react-dom, @remix-run/* | Everything | Static HTML plus ES modules |
| react-syntax-highlighter 15.6.1 (refractor 3.6, Prism 1.29 grammars) | The Prism light build with `bash`, `css`, `scss`, and `jsx` registered. `html` resolves to refractor's `html` alias, Prism `markup` (corrected 2026-10-31: prism-light's `registerLanguage` ignores its name argument, so registering jsx "as html" only added `jsx`). `useInlineStyles={false}`, so classes only. Tokens are flattened: each text run is one `span` whose class list is the union of its ancestors', e.g. `token tag attr-name`. `_code.scss` selectors depend on that. | Prism (pinned, latest) at build time, emitting the same flattened spans (03 §4). |
| @makotot/ghostui 2.0.0 | TOC `Scrollspy` | `docs.js` |
| typeit-react 2.7.8 (typeit 8.8.7) | Homepage demo | Hand-written loop |
| react-copy-to-clipboard | Copy | `navigator.clipboard.writeText` |
| react-div-100vh | `innerHeight` in px for the body and the color modal | `100dvh` (Widely available) |
| html-react-parser | Literal HTML strings (`<mark>New</mark>`, stats labels, `<noscript>`) | Plain HTML |
| use-debounce, use-local-storage-state, use-prefers-color-scheme | Breadcrumb debounce, theme storage, matchMedia | A few lines each |
| isbot | Unused | Dropped |
| @fontsource/figtree, @fontsource/fira-code | Sass `faces()` mixins: Figtree 700 normal and italic, and Fira Code 400, all subsets, woff2 and woff | Self-hosted woff2 with hand-written `@font-face` (OFL-1.1) |
| Google Fonts Pacifico 400 | The CSS variables example's heading, loaded from fonts.googleapis.com on `/docs/css-variables` only | Self-hosted woff2, the same 5 subset files (OFL-1.1) |

## 4. Styles

The SCSS is compiled by `sass --load-path=node_modules/@picocss/pico/scss/`, then autoprefixer (browserslist `defaults`) and clean-css. All output is gitignored.

| Entry | Contents | Used by |
|---|---|---|
| `main.scss` (tree about 834 lines) | All of Pico 2.1.1 (`$css-var-prefix: "--femto-"`, `$enable-responsive-spacings: true`), plus commons: theme tokens, fonts, header, footer, document grid, code and token colors, skip link, logo, theme toggle, chapter, card-component | every page |
| `docs.scss` (about 1,325) | docs theme tokens, `main` grid, breadcrumb, asides, menu, page header, TOC, `pages/*`, docs components | `/docs/*` |
| `landings.scss` (about 1,091) | landing tokens, hero, demo, stats, features, comparison, examples, Figtree headings | `/`, `/examples`, `/demo` |
| `docs/color-utilities.scss` | Pico color utilities with the femto prefix | `/docs/colors`. Same as femto's `femto.colors.css` |
| `docs/color-picker.scss` | Main-shade background classes for the 20 swatches | version picker |
| `custom-themes/<color>.scss` ×20, `utils/_css-vars-from-theme.scss` | Primary-token overrides in three blocks (light, auto dark, forced dark) on `:root` | the 19 color routes. Same as femto's `css/themes/<color>.css` |
| `snippets/*.scss` | Pico's default schemes and styles, compiled only to be shown as code | css-variables route via `app/data/code-snippets/*.txt` |
| `docs/utilities/_colors.scss` | Orphan, never used | — |

Pico Sass the site's own SCSS depends on (file and line lists are in the inventory transcript; the counts are what matters):
- **`#{$css-var-prefix}`.** 469 uses, always the literal `--femto-`.
- **`$breakpoints`.** Used through `map.get(...)` and `@each` loops in about 30 partials. The values are Pico's defaults, matching femto's literals: 576/510, 768/700, 1024/950, 1280/1200, 1536/1450 px.
- **The Pico palette (`$azure-550` and the rest), with `mix()` and `rgba()`.** Used in the commons, docs and landings light and dark theme files.
- **`$semantic-root-element`.** Always `body`.
- **Pico's generators.** `colors/utilities`, `themes/default/schemes` and `styles`, and `$color-mappings`. Each is replaced by a femto file.

Page-scoped styles in `docs/pages/*.scss` are scoped by `main.page-<id>`, a class `docs/Main.jsx` derives from the route. Four of them would hit the whole page if left unscoped:
- `_card` restyles every `article`;
- `_grid` every `.grid > div`;
- `_usage-scenarios` every table;
- `_v2` every `h3`.

The docs layout grid (`docs/layout/_main.scss`) expects exactly one `hgroup`, one TOC aside and one `[role=document]` per `<main>`.

Dead or buggy selectors to drop rather than port:
- `svg.theme-toggle` in `_header.scss:44`;
- `h1 h1` in `_main-header.scss:22`.

## 5. Build and hosting

`yarn build` runs these steps, in order:
1. `build:sort-scss` rewrites the SCSS in place.
2. Sass compiles `app/styles/css/**`.
3. Autoprefixer.
4. clean-css.
5. `scripts/copy-code-snippets.js` copies Pico Sass and compiled snippets into `app/data/code-snippets/*.txt` (tracked).
6. `scripts/fetch-stats.js` writes `app/data/stats.json` (gitignored; the homepage import fails without it).
7. The Pico v1 docs are copied into `public/docs/v1`.
8. `remix build` writes `public/build/**` and the Pages Function `functions/[[path]].js`.

Deploy is `wrangler pages deploy ./public`. Every request except `/build/*` runs the Function (`public/_routes.json`).

`public/`:
- **`_redirects`.** 28 rules for picocss.com's v1 URLs, which femto.style never served.
- **`_headers`.** One year of caching for `/build/*`.
- **`site.webmanifest`.** `theme_color` is `#ffffff`, while the head uses `#2a3140`.
- **Icons:** `favicon.svg`, `apple-touch-icon.png`, `opengraph.png`.

`logo.png` and `logo.svg` are not referenced.

Head and metadata bugs to fix during the conversion:
- `og:url` is hard-coded to `https://v2.picocss.com/` (`Head.jsx:22`).
- `StructuredData.jsx` describes Pico CSS.
