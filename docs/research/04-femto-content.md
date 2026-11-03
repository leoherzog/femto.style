# 04: From Pico-era content to femto 3

What happens to each page and section, so that the site ends up using and describing femto 3.0. The sources of truth are femto's `README.md` and `PLAN.md` at the vendored commit (d4f8d1fd, 3.0.0-alpha.1, since 2026-11-03). This report was written against e3b141f3 on 2026-10-30; by 7bcd5758 the README has a new tagline, "Semantic HTML made beautiful", and adds right-to-left, striped-row and switch-tooltip details to five class-table rows and a line on 2.1.1's rendering bug fixes under Other changes. By d4f8d1fd the feature list mentions vendor-only rules, the npm section adds `ios17.5` to the Vite `cssTarget` example and says why, and Browser support names the features some minimum versions lack or prefix, what `npm run lint` checks (web-features 3.42.0), and the versions without `light-dark()`. Where the docs and the README disagree, the README wins. A disagreement found while writing is reported to the owner, not resolved here.

## Verdict

Nine of the 40 docs routes go in Phase 1, because femto has nothing for them to describe:
- the six About pages (Decision 5);
- classless and conditional, whose builds femto dropped;
- Sass, whose toolchain femto dropped.

Nothing is live, so they need no redirects; they are simply not built.

The other 31 sections survive the conversion and the merge at parity. Phase 4 then rewrites them:
- **Rewritten:** six sections (Quick start, Version picker, Color schemes, CSS variables, Colors, Container).
- **Lightly edited:** two (Landmarks & section, Modal).
- **"Class-less" asides removed:** eight more.

Phase 4 also adds sections for what femto 3 has and Pico's docs never described:
- classes and attributes;
- files;
- themes;
- options;
- custom module sets;
- cascade layers;
- shadow roots;
- browser support;
- migrating from Pico.

Most of their text comes straight from femto's README.

## 1. Disposition

Section ids are from 02 §1.

| Section (id) | Phase 1 | Phase 4 |
|---|---|---|
| Quick start (`quick-start`) | convert | **Rewrite** from README "Quick start": the alpha note, jsDelivr `dist/femto.min.css`, `npm install @leoherzog/femto` (`@alpha` until 3.0.0), the GitHub zip and the starter template with `<meta name="color-scheme">`. Remove "import Pico into your SCSS". |
| Version picker (`version-picker`) | convert (picker at parity; the 19 color routes become `?theme=` in Phase 3) | **Rework** into a theme and options picker: the 20 colors and the 3 option files. Choosing a color swaps the page's theme `<link>` and sets `?theme=` (02 §5). Output the `<link>` tags in load order (femto, theme, options, then "your stylesheet"), the jsDelivr combine URL with the README's "not yet confirmed" caveat, and a starter template. Remove the base select (classless), the conditional switch and the Sass output. Its title and id are the owner's call. |
| Color schemes (`color-schemes`) | convert | **Rewrite** from README "Color schemes": `data-theme` on `<html>` or on an element, what it switches and what it does not, Decision 12's consequences, and `color-scheme` on an element. |
| RTL (`rtl`) | convert | check wording |
| Class-less version, Conditional styling | **not built** | their content becomes Migrating from Pico, "Dropped builds" |
| CSS variables (`css-variables`) | convert | **Rewrite.** The prefix is fixed at `--femto-`, with no Sass recompile. Tokens are declared once on `:root, :host` with `light-dark()`, replacing the three-selector light/dark structure. The examples become `:root { --femto-… }` overrides. The pasted dumps of every variable are dropped in favor of links to `css/tokens/base.css` and `css/tokens/schemes.css` in femto's repository at the vendored commit. |
| Sass | **not built** | → Migrating from Pico, "Sass settings". Its 20-color list moves to Themes and its settings to Options. |
| Colors (`colors`) | convert | **Rewrite.** Use `femto.colors.css` (`dist/femto.colors.min.css`, about 78 KB, 4.4 KB with Brotli), `.femto-color-*`, `.femto-background-*` and `var(--femto-color-<family>-<shade>)`. Remove "Usage with Sass", and the Sass variable row in the color modal. The Figma import section must be checked: it may point at Pico's Figma file. |
| Container (`container`) | convert | **Rewrite** the breakpoints paragraph: literal 576, 768, 1024, 1280 and 1536 px, no Sass. Remove "Semantic containers" and the class-less notes. |
| Landmarks & section (`landmarks`) | convert | Remove "Root container" (`$semantic-root-element`). Say that responsive spacings are opt-in through `css/options/responsive-spacings.css`; the site itself loads that option. |
| Grid, Overflow auto, Typography, Link, Button, Table | convert | Remove the "not available in the class-less version" asides. Check the font-size table against `css/tokens/breakpoints.css`. |
| Forms (8 sections) | convert | check wording |
| Accordion, Card, Dropdown, Group, Loading, Nav, Progress, Tooltip | convert | Remove the class-less asides. |
| Modal (`modal`) | convert | Remove the picocss/examples CodeSandbox links. Check the helper script against README "Classes and attributes" (`.modal-is-open`, `-opening`, `-closing`, `--femto-scrollbar-width`). |
| About: Maintenance, What's new in v2, Mission, Usage scenarios, Brand, Built with | **not built** | The femto logo files stay as plain assets under `/assets/brand/`; no page links them. |
| Stats (homepage) | **removed** | — |
| Maintenance banner | **removed** | — |
| Pico v1 docs `/docs/v1/` | **not built** | The version dropdown loses its v1 entry. |

New sections in Phase 4, all from femto's README. The menu placement is a proposal, and the owner settles it at the Phase 4 gate:

| Section (id) | Category | README source |
|---|---|---|
| Classes and attributes (`classes`) | Getting started | "Classes and attributes" |
| Migrating from Pico (`migration`) | Getting started | "Migrating from Pico". Every subsection: file names and URLs, find and replace, dropped builds, Sass settings, color scheme changes. This is the one docs section allowed to name Pico. It is not an About page; it is how femto 3 is adopted. The owner can still veto it. |
| Browser support (`browser-support`) | Getting started | "Browser support" |
| Files (`files`) | Customization | "Files", with the `@import` cost table |
| Themes (`themes`) | Customization | "Themes" |
| Options (`options`) | Customization | "Options" |
| Custom module set (`modules`) | Customization | "Custom module set" |
| Cascade layer (`cascade-layer`) | Customization | "Cascade layer" |
| Shadow roots (`shadow-roots`) | Customization | "Shadow roots" |

## 2. Outside the docs page

- **Head and structured data.** Fix `og:url`, which is hard-coded to `v2.picocss.com`. `StructuredData` becomes femto's `SoftwareSourceCode`, pointing at `github.com/leoherzog/femto` and `@leoherzog/femto` on npm. Align `site.webmanifest`'s `theme_color` with the head.
- **Homepage.**
  - Features: remove the class-less card link and the "Pico directly styles" wording.
  - Comparison: check its claims.
  - Hero: unchanged apart from wording.
- **Footer.**
  - Remove the About column.
  - Docs column: replace "Class-less version" with "Migrating from Pico", or with nothing.
  - Examples column: see below.
  - Keep the CC BY-SA attribution to the Pico CSS documentation. The license requires it, and it is one of the allowed places to name Pico.
  - Footer links into the docs become `/docs#<id>`.
- **Header.** The version dropdown has one entry left. It becomes a plain version label linking to `/docs`, unless the owner wants the dropdown kept for future versions.
- **Examples page.** All seven entries in `examples.json` point at picocss/examples on CodeSandbox. The page is open: drop it with its header and footer links, or replace it with femto examples the owner supplies. Phase 1 converts it at parity either way.
- **Links into the docs** from any page (homepage features, footer, header) become `/docs#<id>`.
- **`_redirects`** is deleted in Phase 1. It holds only picocss.com's v1 rules, which femto.style never served, and nothing is live.

## 3. Keeping the content true to femto

These are static checks, run on the built docs page from Phase 4 on:

- **Custom properties.** Every `--femto-*` name in docs prose and code samples is declared in `vendor/femto/dist/femto.css` or `dist/femto.colors.css`. Site-internal tokens never appear in docs content.
- **Files and URLs.** Every femto file path or jsDelivr URL path in the docs (`dist/…`, `css/themes/…`, `css/options/…`) names a file in `vendor/femto/`. Links to femto's repository point at the vendored commit or tag.
- **Classes.** Every femto class used in example markup is either one README "Classes and attributes" lists, or a color utility class that `femto.colors.css` declares.
- **Version.** Every version string matches `vendor/femto/SOURCE`.
- **No Pico.** `git grep -il pico` matches only the allowed places: `LICENSE.md`, `README.md`, the footer attribution partial, the vendored `site/vendor/femto/LICENSE.md`, the Migrating from Pico section, `docs/research/`, `tests/`, `PLAN.md` and `PROMPT.md`.

**Release timing.** The Quick start URLs (`npm/@leoherzog/femto@3/…`) work only after femto is published to npm. The docs follow the README's own alpha note until then. The site should go live after femto's first publish, or say plainly that the CDN URLs await it.
