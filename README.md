# femto Documentation

[femto.style](https://femto.style) is the documentation site of [femto](https://github.com/leoherzog/femto). It is plain HTML, CSS and JavaScript: `site/` is the source, and `npm run build` writes the site to `dist/`. Nothing from npm ships: `dist/` is static files, and Node and npm are only needed to build, preview and check it.

The site was converted from the Remix site it replaces, and [PLAN.md](PLAN.md) is the plan, with its research in `docs/research/`. Its text is written for femto 3 from femto's README.

`/docs` is one page. `build.mjs` assembles it from `site/docs/menu.json`, which orders the sections, and one file per section in `site/docs/sections/<id>.html`; each section's "Edit this page on GitHub" link opens its file. `/examples` is `site/examples.html`: each example's markup is written twice, live in a shadow root and escaped in its code sample, and a behavior check fails if the two differ.

## Develop

You need Node 26.13 or later (`.node-version`). First install the dependencies:

```bash
npm install
```

Next, build the site and run the development server at <http://127.0.0.1:8723>. It rebuilds on every change under `site/` or to `build.mjs`:

```bash
npm run dev
```

To build `dist/` without a server:

```bash
npm run build
```

To lint the site's CSS and JavaScript:

```bash
npm run lint
```

## femto

The site serves its own copy of femto from `site/vendor/femto/`: femto's `dist/`, `css/` and `LICENSE.md`, with `SOURCE` naming the commit they came from. To change it, commit in a femto checkout at `../femto` and copy its `HEAD`:

```bash
npm run vendor
```

Or name another checkout and a commit: `npm run vendor -- <checkout> [<commit>]`. It refuses a checkout with uncommitted changes, and copies the committed files, never the working tree. The build writes `SOURCE`'s version and commit wherever a page says `{{version}}` or `{{commit}}`, so the docs' version label and their links to femto's files follow the vendored copy.

## Tests

`tests/` holds the parity harness, which compared the static site with the Remix site it replaces (tag `remix-final`) through the conversion, and the checks that hold the site now: the behavior suite, in real Chrome, Firefox and Safari on macOS; axe-core accessibility, in Chrome and Firefox; and the static checks and a link check, which need no browser. It runs with [uv](https://docs.astral.sh/uv/); [tests/README.md](tests/README.md) has the setup and every mode. For example, the static checks, the behavior suite and the accessibility check against `dist/`:

```bash
uv run tests/run.py static
```

```bash
uv run tests/run.py behavior --target dist
```

```bash
uv run tests/run.py a11y --target dist
```

On every push and pull request, GitHub runs `.github/workflows/check.yml` on Linux: `npm ci`, `npm run build`, `npm run lint` and `uv run tests/static_checks.py`. It fetches femto at the commit `SOURCE` names into `../femto`, beside the checkout, so the vendored copy and the docs are checked against that commit. The criteria that need the browsers report NOT-YET there, and any failing criterion fails the run. It never deploys: Cloudflare Pages deploys the same push separately (Deploy, below), and it does not wait for this check.

## Deploy

Cloudflare Pages builds and deploys the site from this repository on GitHub (PLAN.md Decision 11). Pushing `main` deploys production at <https://femto.style> (also `femto-style.pages.dev`), and pushing any other branch deploys a preview at `<branch>.femto-style.pages.dev`. There is no deploy script.

The build settings live in the Pages project `femto-style` in the Cloudflare dashboard, not in the repository:

- Framework preset: None
- Build command: `npm run build`
- Build output directory: `dist` (never `site` or the repository root)
- Root directory: empty
- Build system version: v3

Pages takes Node's version from `.node-version`: build system v3 reads the `NODE_VERSION` variable, `.node-version` or `.nvmrc`, never `package.json`'s `engines`. It installs the dependencies itself before the build. The first build log shows which Node it used and whether the devDependencies, `prismjs` among them, were installed; confirm both there.

The site relies on Pages' own rules (PLAN.md Decision 11): Pages serves `docs.html` at `/docs` and `examples.html` at `/examples`, answers unknown paths with `404.html` and applies `_headers`, so another host needs the same rules. `site/_headers` gives the fonts in `/assets/fonts/` a year of caching; everything else keeps Pages' default, which revalidates on every request. On `femto.style` that holds only once the zone's Browser Cache TTL is set to Respect Existing Headers. `site/robots.txt` names the sitemap that the build writes, `https://femto.style/sitemap.xml`.

Some settings of the femto.style zone act on `femto.style` but not on `femto-style.pages.dev`, and each is the owner's step in the dashboard (PLAN.md Risks, Cloudflare): turn Email Address Obfuscation off, since it rewrites the addresses on `/examples` and cannot reach the two in the mockups' shadow roots; set Browser Cache TTL to Respect Existing Headers; turn on Always Use HTTPS, since `http://www.femto.style/` otherwise times out; and keep the Pages project's own Web Analytics off, so only the zone's is left. The zone's Web Analytics stays on: its beacon is the one cross-origin script production loads, criterion 15's exception. Speed Brain's `speculation-rules` header is harmless.

## License

femto.style is adapted from the [Pico CSS documentation](https://github.com/picocss/picocss.com) by [Lucas Larroche](https://lucaslarroche.com/), licensed under [CC BY-SA 4.0](https://github.com/picocss/picocss.com/blob/main/LICENSE.md), and has been changed to document [femto](https://github.com/leoherzog/femto). This adaptation is also licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); see [LICENSE.md](LICENSE.md).

Some parts keep their own licenses: femto itself, in `site/vendor/femto/`, is MIT-licensed (its [LICENSE.md](site/vendor/femto/LICENSE.md)); the fonts in `site/assets/fonts/` (Fira Code and Pacifico) are under the SIL Open Font License 1.1 ([OFL.txt](site/assets/fonts/OFL.txt)); and the GitHub, npm, jsDelivr and X icons are [Simple Icons](https://simpleicons.org)' SVGs, under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). The site's other icons, apart from femto's own logo, are Unicode characters (PLAN.md Decision 17).
