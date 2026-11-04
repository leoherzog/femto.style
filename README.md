# femto Documentation

[femto.style](https://femto.style) is the documentation site of [femto](https://github.com/leoherzog/femto). It is plain HTML, CSS and JavaScript: `site/` is the source, and `npm run build` writes the site to `dist/`.

The site is being converted from the Remix site it replaces, and [PLAN.md](PLAN.md) is the plan, with its research in `docs/research/`. The pages already use femto 3's stylesheets but still carry the old site's text, which Phase 4 of the plan rewrites for femto 3.

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

Or name another checkout and a commit: `npm run vendor -- <checkout> [<commit>]`. It refuses a checkout with uncommitted changes, and copies the committed files, never the working tree.

## Tests

`tests/` holds the parity harness, which compares the static site with the Remix site it replaces (tag `remix-final`) in real Chrome, Firefox and Safari on macOS. It runs with [uv](https://docs.astral.sh/uv/); [tests/README.md](tests/README.md) has the setup and every mode. For example, the static checks and the behavior suite against `dist/`:

```bash
uv run tests/run.py static
```

```bash
uv run tests/run.py behavior --target dist
```

## Deploy

`npm run deploy` builds the site and uploads `dist/` to Cloudflare Pages with `wrangler pages deploy`, which needs a Cloudflare account signed in with `npx wrangler login`.

## License

femto.style is adapted from the [Pico CSS documentation](https://github.com/picocss/picocss.com) by [Lucas Larroche](https://lucaslarroche.com/), licensed under [CC BY-SA 4.0](https://github.com/picocss/picocss.com/blob/main/LICENSE.md), and has been changed to document [femto](https://github.com/leoherzog/femto). This adaptation is also licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); see [LICENSE.md](LICENSE.md).

Two parts keep their own licenses: femto itself, in `site/vendor/femto/`, is MIT-licensed (its [LICENSE.md](site/vendor/femto/LICENSE.md)), and the fonts in `site/assets/fonts/` (Figtree, Fira Code and Pacifico) are under the SIL Open Font License 1.1 ([OFL.txt](site/assets/fonts/OFL.txt)).
