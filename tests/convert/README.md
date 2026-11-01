# tests/convert: the one-time route converter

Phase 1 turns each oracle route into a section file (PLAN.md Conversion rules). Nothing here ships.

| File | What it does |
|---|---|
| `convert.py` | `uv run tests/convert/convert.py <route>`: the route's captured hydrated DOM (`tests/oracle/capture/<slug>/dom.html`) into its section file. Its docstring lists every rule. |
| `highlight-check.mjs` | `node tests/convert/highlight-check.mjs [slug ...]`: build.mjs's highlighter against every highlighted code block of the oracle; on 2026-10-31 all 298 distinct blocks (343 in all, 56 routes) match run for run. |

## Converting a route

```sh
uv run tests/convert/convert.py /docs/forms/input --report      # writes site/docs/sections/input.html
uv run tests/convert/convert.py /docs/version-picker/jade        # writes site/docs/sections/version-picker/jade.html
uv run tests/convert/convert.py /examples --out -                # any route's <main> content, to stdout
```

- The output path comes from `site/docs/menu.json` (`sections/<id>.html`, or `sections/<id>/<color>.html` for a
  version picker color). An existing file is never overwritten without `--force`, since it may hold hand edits.
- The file holds what the route's `<main>` holds after the documentation menu: the `hgroup`, the table of contents,
  `div#content` with the sections and the edit link, and anything else the route put there (a `<dialog>`, an
  example `<nav>`). build.mjs puts the head, header, breadcrumb, menu and footer around it.
- The converter prints, on stderr, the links to Decision 5 routes (remove each or point it at `/docs`, then register
  it as `dropped-route`) and every hashed asset URL it rewrote (the attribute then differs from the oracle).
- `--report` lists the attributes and texts that differ between the oracle's server HTML and its hydrated DOM, and
  between the hydrated DOM in light and in dark and at 1300 and 375 px: the state the oracle's JavaScript set, which
  the route's module must set the same way. The table of contents' `aria-current` is in that list: the converter
  drops it, and docs.js sets it.
- `--raw` adds no line breaks. Without it the converter breaks lines only between siblings that are all block
  elements by tag (never inside `<pre>`, `<code>`, `<svg>`, `<select>` or around text), where whitespace renders
  nothing. If a parity run shows a size difference that `--raw` output does not, keep the raw markup there.

Then edit the file by hand into readable HTML, keeping the oracle's elements, classes, attributes (`data-discover`
included), text and order, and never adding whitespace inside inline content or `<pre>`. Code stays escaped text in
`<code class="language-X">` (`html`, `css`, `scss`, `bash`): build.mjs highlights it.

Two Phase 1 findings about text nodes, which Phases 2 and 3 must keep in mind when they edit the section files:
- The converter drops every React `<!-- -->` text separator. Inside a `<label>` that sizes to its content, the split
  between text nodes changes Chrome's text shaping by a few thousandths of a pixel (the version picker's "I agree
  to the<!-- --> Privacy Policy" label, 299.859 against 299.875 px at 1300; color-schemes' "<!-- -->Remember me").
  Those two files keep the marker, each with a comment that says why and when it can go; keep any such marker you
  find, and put one back where a label that mixes text and links shows a sub-pixel width difference.
- Whitespace between `<option>` elements counts as the `<select>`'s own text in Chrome (one `text` record per
  cell), so keep a `<select>` and its options on one line, as the converter writes them.

## Checking a route group

```sh
node build.mjs --only input,textarea --out <scratch>/forms           # the group's sections and the shared pages
uv run tests/run.py fast --a oracle --b dist:<scratch>/forms --routes /docs/forms/input,/docs/forms/textarea
```

`dist:<path>` serves any built folder exactly as the `dist` target serves `dist/` (tests/README.md, Modes), so each
agent compares its own build. The shell's differences, which every route shows (the dropped maintenance banner,
footer and menu items, og:url), are registered in `tests/divergences/p1-shell.json`; register a route's own
differences in the group's file, specific and with a reason.
