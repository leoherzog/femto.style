# femto Documentation

[femto.style](https://femto.style) is the documentation site of [femto](https://github.com/leoherzog/femto). It is plain HTML, CSS and JavaScript: `site/` is the source, and `npm run build` writes the site to `dist/`. Nothing from npm ships: `dist/` is static files, and Node and npm are only needed to build, preview and check it.

[PLAN.md](PLAN.md) is the site's spec: its decisions, the acceptance criteria the checks hold, and the open risks. The site was converted from a Remix site, and the tag `conversion-final` holds the record of that conversion. Its text is written for femto 3 from femto's README.

`/docs` is one page. `build.mjs` assembles it from `site/docs/menu.json`, which orders its 43 sections in 8 categories, and one file per section in `site/docs/sections/<id>.html`. It ends each section with an "Edit this section on GitHub" link to its file, written from its id; a section file holds no edit link of its own (the build fails on one). `/examples` is `site/examples.html`: 16 examples in four chapters (Overview, Widgets, Forms and Pages), each one's markup written twice, live in a shadow root and escaped in its code sample, folded in the `<details>` under it. A static check and a behavior check fail if the two differ. Each example has a Copy as page button, which copies its markup in femto's starter template (the page's `template[data-starter-page]`), and a theme select links one of femto's `css/themes/` files into every example, with no URL parameter, unlike the docs page's `?theme=` (Decision 8).

## Develop

You need Node 26.13 or later (`.node-version`). First install the dependencies:

```bash
npm install
```

Next, build the site and run the development server at <http://127.0.0.1:8723>. It rebuilds on every change under `site/` or to `build.mjs`:

```bash
npm run dev
```

To build `dist/` without a server, or into another folder:

```bash
npm run build
node build.mjs --out /path/to/folder
```

To lint the site's CSS and JavaScript:

```bash
npm run lint
```

## femto

The site serves its own copy of femto from `site/vendor/femto/`: femto's `dist/`, `css/` and `LICENSE.md`, with `SOURCE` naming the commit they came from, the tags that point at it, the refs that reach it and femto's version. It is copied from femto's git repository, from its release tags, also once femto is on npm (PLAN.md Decision 4). To vendor a release, fetch its tag into the femto checkout at `../femto` and name it:

```bash
git -C ../femto fetch --tags
npm run vendor -- ../femto v3.0.0
```

`npm run vendor` alone copies `../femto`'s `HEAD`, and `npm run vendor -- <checkout> [<commit>]` names another checkout and a commit, branch or tag. It refuses a checkout with uncommitted changes, and copies the committed files, never the working tree. A tag the checkout lacks fails with a hint to fetch the tags. The build writes `SOURCE`'s version and commit wherever a page says `{{version}}` or `{{commit}}`, so the docs' version label and their links to femto's files follow the vendored copy.

After copying, it prints what to review in the docs, from the commit the old `SOURCE` named to the new one:

- `git diff --stat` of femto's `README.md`, `CHANGELOG.md` and `css/`;
- each README H2 and H3 whose section changed, with the docs sections that name it, or "no section names it";
- the README H2s that no docs section names, and the names that match no README heading.

A docs section names the README section it covers with its `readme` key in `site/docs/menu.json`: the heading's exact text at the vendored commit. Nothing in the list fails the run. The static checks do fail on what must follow femto (criterion 13's drift and femto's facts): the theme colors, the palette, the option files, the `readme` keys, the Tokens table, each section's list of the tokens its module reads, the module map, the Elements index and the counts the prose gives.

### When femto 3.0.0 is released

1. Vendor the release tag, `git -C ../femto fetch --tags` then `npm run vendor -- ../femto v3.0.0`, and review what it prints.
2. Delete the prerelease note: the `<section>` in `site/docs/sections/quick-start.html` that begins "The `@3` links and commands in these docs work once 3.0.0 is released", with its `@alpha` commands, and the "Until 3.0.0 is released" paragraph in `site/docs/sections/theme-picker.html`. Once `SOURCE`'s version is a release, criterion 13's prerelease wording check fails until both are gone.
3. The docs' `@3` links work once 3.0.0 is on npm. Once `SOURCE` says 3.0.0, the link check no longer exempts them, so `uv run tests/static_checks.py --criteria links --external` passes only after femto is published.

## Tests

`tests/` holds the checks that hold the site: the static checks and a link check, which need no browser; the behavior suite, in real Chrome, Firefox and Safari on macOS; and axe-core accessibility, in Chrome and Firefox. They run with [uv](https://docs.astral.sh/uv/); [tests/README.md](tests/README.md) has the setup, every mode and every check.

```bash
uv run tests/static_checks.py                  # criteria 4 to 15's static parts, and the link check
uv run tests/run.py behavior --target dist     # criterion 7 and 15's run-time checks, in Chrome and Firefox
uv run tests/run.py a11y --target dist         # criterion 10
uv run tests/run.py rig                        # the browser mechanisms the harness relies on
```

Besides the criteria, the static checks hold the docs to femto at the vendored commit (the drift checks and femto's facts), compare every example's live markup with its code sample, keep the prerelease wording in step with `SOURCE`'s version, and measure `/docs` at the compression Cloudflare Pages serves it with. `uv run tests/static_checks.py --criteria release --external` asks femto's GitHub repository for a release tag newer than `SOURCE`'s version. Safari's runs are the owner's: `tests/owner-safari.sh final` and `reduced`.

On every push and pull request, GitHub runs `.github/workflows/check.yml` on Linux: `npm ci`, `npm run build`, `npm run lint` and `uv run tests/static_checks.py`. It fetches femto at the commit `SOURCE` names into `../femto`, beside the checkout, so the vendored copy and the docs are checked against that commit. The criteria that need the browsers report NOT-YET there, and any failing criterion fails the run. The checks that ask the network, every external link and a newer femto release, run only by hand (tests/README.md). The workflow never deploys.

## Deploy

Cloudflare Pages builds and deploys the site from this repository on GitHub (PLAN.md Decision 11). Pushing `main` deploys production at <https://femto.style> (also `femto-style.pages.dev`), and pushing any other branch deploys a preview at `<branch>.femto-style.pages.dev`. There is no deploy script.

A GitHub ruleset on `main`, "main requires Check", requires the Check workflow's `check` status before `main` accepts a push (the owner, 2026-11-09; on since that day), so a change ships in two steps:

1. Push `dev`, and wait for its Check run to pass.
2. Push the same commit to `main`.

The ruleset has no bypass. Pages builds every push without waiting for the Check, so a preview of `dev` deploys at once.

`wrangler.jsonc` pins the Pages project's name and its build output directory, `dist`, so the build never serves the unbuilt `site/` again. Once a deployment has read it, its fields win over the dashboard's. Criterion 4 checks it: its three fields, and that the pinned wrangler reads `dist` from it as Pages' build does. `wrangler pages dev` reads it too, though a folder named on its command line still wins. The rest of the build settings stay in the Pages project `femto-style` in the Cloudflare dashboard:

- Framework preset: None
- Build command: `npm run build`
- Root directory: empty
- Build system version: v3
- Production branch `main`, with preview deployments for every other branch
- The project's own Web Analytics: off

Pages takes Node's version from `.node-version`: build system v3 reads the `NODE_VERSION` variable, `.node-version` or `.nvmrc`, never `package.json`'s `engines`. It installs the dependencies itself before the build. The first build after `wrangler.jsonc` arrives on `main` should log "Found wrangler.jsonc file" and `pages_build_output_dir: dist`; if it does not, the dashboard's output directory still applies. Confirm it there, with the Node the build used and whether the devDependencies, `prismjs` among them, were installed.

The site relies on Pages' own rules (PLAN.md Decision 11): Pages serves `docs.html` at `/docs` and `examples.html` at `/examples`, answers unknown paths with `404.html` and applies `_headers`, so another host needs the same rules. `site/_headers` gives the fonts in `/assets/fonts/` a year of caching; everything else keeps Pages' default, which revalidates on every request. On `femto.style` that holds only once the zone's Browser Cache TTL is set to Respect Existing Headers. `site/robots.txt` names the sitemap that the build writes, `https://femto.style/sitemap.xml`.

Some settings of the femto.style zone act on `femto.style` but not on `femto-style.pages.dev`, and each is the owner's in the dashboard (PLAN.md Risks, Cloudflare). On 2026-11-09 production showed Email Address Obfuscation off (it rewrites the addresses on `/examples` and cannot reach the two in the mockups' shadow roots) and Always Use HTTPS on (without it `http://www.femto.style/` times out). One step is still open: set Browser Cache TTL to Respect Existing Headers (it still sent `max-age=14400`). Keep the Pages project's own Web Analytics off, so only the zone's is left. The zone's Web Analytics stays on: its beacon is the one cross-origin script production loads, criterion 15's exception. Speed Brain's `speculation-rules` header is harmless. To recheck production against a fresh build:

```bash
out="$TMPDIR/femto-live"; node build.mjs --out "$out"
for pair in /:index.html /docs:docs.html /examples:examples.html /no-such-page:404.html /sitemap.xml:sitemap.xml; do
  live=$(curl -sS "https://femto-style.pages.dev${pair%%:*}" | shasum -a 256 | cut -c1-64)
  built=$(shasum -a 256 < "$out/${pair#*:}" | cut -c1-64)
  echo "${pair%%:*} $([ "$live" = "$built" ] && echo same || echo DIFFERENT)"
done
curl -sS -H 'Accept: text/html' https://femto.style/examples | grep -c __cf_email__   # 0 with Email Address Obfuscation off
curl -sSI https://femto.style/assets/css/common.css | grep -i cache-control          # max-age=0 with Respect Existing Headers
curl -sS -o /dev/null -w '%{http_code}\n' http://www.femto.style/                     # 301 with Always Use HTTPS
```

On `femto.style` itself the pages never hash the same as the build when the request sends `Accept: text/html`, as a browser does, since the zone injects its beacon into those responses.

## License

femto.style is adapted from the [Pico CSS documentation](https://github.com/picocss/picocss.com) by [Lucas Larroche](https://lucaslarroche.com/), licensed under [CC BY-SA 4.0](https://github.com/picocss/picocss.com/blob/main/LICENSE.md), and has been changed to document [femto](https://github.com/leoherzog/femto). This adaptation is also licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); see [LICENSE.md](LICENSE.md).

Some parts keep their own licenses: femto itself, in `site/vendor/femto/`, is MIT-licensed (its [LICENSE.md](site/vendor/femto/LICENSE.md)); the font in `site/assets/fonts/` (Pacifico, subset to the CSS variables example's heading) is under the SIL Open Font License 1.1 ([OFL.txt](site/assets/fonts/OFL.txt)); and the GitHub, npm and jsDelivr icons are [Simple Icons](https://simpleicons.org)' SVGs, under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). The site's other icons, apart from femto's own logo, are Unicode characters (PLAN.md Decision 17).
