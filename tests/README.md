# femto.style tests

This folder holds the checks that hold the site to PLAN.md's acceptance criteria: the browser
harness (`run.py`, with the behavior, a11y and rig modes) and the static checks
(`static_checks.py`), which need no browser and also run in GitHub's Check workflow. Nothing here
ships. The parity harness that compared the static site with the Remix site during the conversion,
with its oracle, comparison modes and divergence registry, is gone; its record, this file's gate log
included, is at tag `conversion-final` (the owner, 2026-11-09).

## Quick start

```sh
uv run tests/static_checks.py                                  # criteria 4 to 15's static parts and the link check, on dist/
uv run tests/static_checks.py --dist /path/to/build            # the same on another build (node build.mjs --out /path/to/build)
uv run tests/static_checks.py --criteria links --external      # the link check, every external URL fetched once
uv run tests/static_checks.py --criteria release --external    # femto has no release tag newer than SOURCE's version
uv run tests/run.py static                                     # the static checks through run.py (the same options)
uv run tests/run.py behavior --target dist                     # the behavior suite (criteria 7 and 15), Chrome and Firefox
uv run tests/run.py behavior --target dist:/path/to/build      # the same against another build
uv run tests/run.py behavior --target dist --groups loads      # criterion 15's run-time loads
uv run tests/run.py behavior --list                            # the checks and what each asserts; starts nothing
uv run tests/run.py a11y --target dist                         # criterion 10: axe-core, Chrome and Firefox
uv run tests/run.py rig                                        # the browser mechanisms the harness relies on
tests/owner-safari.sh final                                    # the owner's Safari passes, Light then Dark
```

Every harness run writes `tests/results/<run-id>/` (gitignored) and prints its summary. Every run,
the static checks' included, exits 0 when it passes, 1 when a check fails or the harness errs, and 2
for a setup or usage error.

## Setup

- **Python** runs only through `uv`. `run.py` carries PEP 723 metadata pinning `selenium==4.52.0`
  and `pillow==13.0.0`. `static_checks.py` has no Python dependencies (Python 3.11 or later), so
  `run.py static` can load it in run.py's own environment and the Check workflow has no Python
  cache (it caches only npm's downloads).
- **Node.** Run `npm install` first: the harness and the static checks use the pinned tools in
  `node_modules` (wrangler, axe-core, eslint, html-validate) and never download one.
- **Browsers**, on the macOS test machine: Google Chrome Beta and Firefox, headless, and Safari,
  visible. Selenium Manager fetches chromedriver and geckodriver into `~/.cache/selenium`; Safari
  uses `/usr/bin/safaridriver`, with Safari's Develop > Allow Remote Automation on.
- **Environment variables:** `FEMTO_CHROME_BINARY` (default `/Applications/Google Chrome
  Beta.app/Contents/MacOS/Google Chrome Beta`), `FEMTO_FIREFOX_BINARY` (default
  `/Applications/Firefox.app/Contents/MacOS/firefox`), `FEMTO_SAFARIDRIVER` (default
  `/usr/bin/safaridriver`), `FEMTO_HARNESS_SLOTS` and `FEMTO_HARNESS_LOCK_DIR` (Concurrency and
  locks), `FEMTO_WRANGLER` (another wrangler executable, to test the harness without
  `node_modules`), and `FEMTO_REPO` (a femto checkout for the static checks).

## Layout

| Path | Contents |
|---|---|
| `README.md` | this file |
| `run.py` | the harness CLI: `uv run tests/run.py <mode> [options]`, modes `rig`, `behavior`, `a11y` and `static` |
| `harness/cli.py` | the modes and their parsers |
| `harness/behavior.py` | the behavior mode: the `Page` API the checks drive, sessions, the runner and the report |
| `harness/a11y.py` | the a11y mode (Accessibility) |
| `harness/rig.py`, `harness/probe.html`, `harness/probe-loads.html` | the rig mode and its probe pages (Rig) |
| `harness/browsers.py` | the browser launch and Safari helpers |
| `harness/targets.py`, `harness/targets.json` | the `dist` target and its server (Targets) |
| `harness/locks.py`, `harness/paths.py` | the machine-wide locks, shared with femto's harness, and the folder paths |
| `behavior/` | the behavior suite: `__init__.py` (the `@check` registry and shared in-page helpers) and one module per group (Behavior) |
| `static_checks.py` | the static checks: criteria 4 to 15's static parts, the link check and the release check (Static checks) |
| `owner-safari.sh` | the owner's Safari passes (Owner's Safari steps) |
| `results/` | generated, gitignored: one folder per run |

## Targets

`--target` names what the behavior and a11y modes load:

- **`dist`**: `wrangler pages dev dist`, with the wrangler `package.json` pins (`npm exec --no --
  wrangler`; `targets.py` checks `node_modules/wrangler` against the exact pin first), on free
  ports of `127.0.0.1`. The run starts it in its own process group and stops it with every child.
  Its `--persist-to` state and its debug log (`WRANGLER_LOG_PATH`) go into the run's folder, so
  concurrent servers share nothing and nothing is written to `~/Library/Preferences/.wrangler/logs`.
- **`dist:<path>`**: any built folder (`node build.mjs --out <path>`), served exactly like `dist`, so
  several agents can each test their own build at once.
- **A base URL**: a server someone else runs, with `--ready static`.

The readiness hook `static` waits for the document's `load`, `document.fonts.ready` and two
animation frames (a 100 ms timer stands in for a frame where rAF never runs); `none` waits for
nothing. `wrangler pages dev <folder>` serves the folder named, whatever `wrangler.jsonc` says.

## Behavior

The behavior mode drives the site's widgets and pages with real WebDriver input and asserts what a
reader sees and can do. It holds the site to criterion 7 (every widget, and the one docs page: the
spy, deep links, nav clicks, back, forward, reload, smooth scrolling only for nav clicks,
`?theme=`), and to criterion 15's run-time parts (the `loads` group and `deep-link-cold`).

```sh
uv run tests/run.py behavior --target dist                         # every check, Chrome and Firefox
uv run tests/run.py behavior --target dist --groups shell,landing  # some groups
uv run tests/run.py behavior --target dist --groups one-page       # criterion 7's checks of the one docs page
uv run tests/run.py behavior --target dist:/path/to/build --checks copy-button,grid-columns
uv run tests/run.py behavior --target http://127.0.0.1:8788 --ready static   # a server someone else runs
uv run tests/run.py behavior --target dist --browsers safari       # Safari, serialized, on an unlocked screen
uv run tests/run.py behavior --list                                # the checks and what each asserts
```

Options: `--target` (required), `--groups`, `--checks` (names), `--browsers` (default
`chrome,firefox`; `safari` too), `--expect-os-motion no-preference|reduce` (Safari only, below),
`--ready static|none` (the target's hook by default), `--workers chrome=2,firefox=2` (sessions per
browser, 1 by default), `--run-id`, `--label` (stored in `result.json`), `--no-shots` and `--list`.
The groups, in order: shell, one-page, getting-started, customization, layout, content, forms,
components-a, components-b, landing, examples and loads. On 2026-11-10 the suite holds 136 checks
over 186 check-routes: 372 runs in Chrome and Firefox (`--list` prints the count).

**How a check runs.** A check drives a top-level document directly, so the URL, history, focus,
storage events between tabs and resizes are the browser's own. Each browser runs headless (timers
and animation frames at full rate; hidden or background tabs throttle both to about once a second)
and holds one machine-wide harness slot for its whole life, with WebDriver start-up serialized
(Concurrency and locks). Before each check and route the page is reset:

- a fresh tab, with every other tab closed (its own history, which both browsers cap at 50 entries,
  its own sessionStorage, and Chrome's per-tab focus and color-scheme emulation set again);
- the viewport set exactly to the check's size with WebDriver BiDi `browsingContext.setViewport`
  (headless windows are at least 500 px wide, so a window size cannot give 375; the page still gets
  real resize events and media queries);
- `prefers-color-scheme` and `prefers-reduced-motion` emulated (Chrome: CDP
  `Emulation.setEmulatedMedia`; Firefox: the `layout.css.prefers-color-scheme.content-override` and
  `ui.prefersReducedMotion` prefs);
- storage emptied on the target's origin from a same-origin static file (`/favicon.svg`) and the
  check's items stored;
- the route loaded and the readiness hook run.

Input is real WebDriver input: pointer clicks at the element's center, scrolled into view first and
only once the element holds still and the point hits it or a descendant, as a user's click would
(WebDriver's element click misplaces the point under an emulated viewport in Chrome); key presses to
the focused element; `<select>` choices; window resizes. A check asserts only DOM state, focus, the
URL, history, storage and the page's loads, and never reads a script's source. Timings (the modal's
400 ms, the copy button's 1 s) are measured in the page with `performance.now()` and
MutationObserver timelines, not across WebDriver round trips.

On the docs page the spy rewrites the URL's hash (`replaceState`, no history entry) whenever a check
scrolls, even to bring an example into view. So `page.url_kept(label, before)`, given a `page.url()`
(which carries `history.length`), means there: the same path and query, and a hash that is the same,
a section's id or none; elsewhere the exact URL; and on both, the same `history.length`.
`page.load(route)` reaches a route that differs from the current URL only by its hash through
`/favicon.svg` first, so it is a new document. Every script a check runs in the page sees `S`, the
section its route names (`document.getElementById(<id>).closest("section")`; the whole document off
the docs page), so `page.find()` finds the route's own example and never another section's.
Selectors outside the content (the header, the side menu, the footer, `dialog.color`) stay
document-wide.

**What reaches under the page**, each for one check family and each without touching the page's
markup or styles:

- **Preload scripts** (BiDi `script.addPreloadScript`, removed after the check): a script that runs
  in every new document before the page's own, for the color-scheme flash and first-frame checks.
- **The copy spy** (`behavior.COPY_SPY`): `document.execCommand("copy")` and
  `navigator.clipboard.writeText()`/`write()` are replaced in that document by recorders, so the
  copy buttons are checked without touching the machine's clipboard.
- **Classic scrollbars**: headless browsers on macOS draw overlay scrollbars of width 0, and the
  modal's scrollbar compensation needs one that takes space. Chrome adopts a `::-webkit-scrollbar`
  sheet in every new document before its scripts run; Firefox gets `ui.useOverlayScrollbars` 0.
- **Held responses** (`delay`, `Page.delay_responses`): a BiDi `network.addIntercept` on each exact
  URL, continued only after the wait. The load then goes over BiDi `browsingContext.navigate`, since
  ChromeDriver runs no BiDi command while a classic `get` waits for the load. `theme-first-frame`
  holds jade's file 300 ms: served at once, a theme `<link>` added by script arrived before the
  first paint too, and the check could not tell it from `document.write`.
- **The request log** (`netlog`, `Page.start_netlog`, `Page.requests()`): a session-wide BiDi
  subscription to `network.beforeRequestSent` and `network.fetchError`, which returns
  `[{event: request|error, url, error?}]`. Safari has none, and says so in a note.
- **The history and scroll recorder** (`one-page.py` `TRACK`): the page's own
  `history.replaceState` is wrapped to record each call's time and URL, and a MutationObserver and a
  scroll listener record the side nav's current links and every scroll event with `html`'s computed
  `scroll-behavior`. Nothing the page does is changed.
- **Print** (`print-light`, `print-light-os-dark`): Chrome's print media through CDP
  `Emulation.setEmulatedMedia` (`media: "print"`, with `prefers-color-scheme` light and dark), and
  in both browsers WebDriver's Print command, which runs the page's `beforeprint` and `afterprint`.
  Firefox has no WebDriver way to emulate print media, so only the real print runs there.
- **Forced colors** (`behavior.expect_forced_focus`): Chrome's CDP `Emulation.setEmulatedMedia`
  with `forced-colors: active`, while a control has keyboard focus; the check's own scheme and
  motion are put back after. Firefox has no WebDriver way to turn forced colors on for one page,
  so there the check records a note.
- **Reference documents** (`examples-isolation`, `media-femto`): a hidden same-origin `srcdoc`
  iframe that loads only femto's stylesheets around the same markup, whose computed styles the
  check compares with the page's.

**Check options** change the browser, not the page: `width`, `height`, `media` (light or dark) and
`storage` (localStorage items, as raw strings); `motion="reduce"`; `javascript=False` (Chrome: CDP
`Emulation.setScriptExecutionDisabled`; Firefox: `javascript.enabled`, cleared after; WebDriver's own
scripts still run, and the load waits for `readyState` complete instead of the readiness hook);
`cold=True`, which empties every cache before the route loads (Chrome: CDP
`Network.clearBrowserCache`; Firefox: `Services.clearData.deleteData(CLEAR_ALL_CACHES)`, since
`Services.cache2.clear()` leaves a stylesheet in memory); `delay={path: seconds}`; `netlog=True`;
`preload` (a preload script); `preload_optional=True`, which lets Safari run a check without its
preload script (`page.preloaded` says which); and `safari_skip="<why>"`, which skips a check in
Safari for something else its WebDriver cannot do.

**Safari** (`--browsers safari`) runs under the Safari rules (Rig notes, Safari): one session at a
time machine-wide, holding the Safari lock for its life; never while the user's own Safari is open,
and only on an unlocked screen (a locked one is a setup error: real input never reaches a hidden
page); visible, with one worker.
- Safari cannot emulate `prefers-color-scheme` or `prefers-reduced-motion`. The session reads both
  from macOS with `matchMedia`: `log.txt`'s session line ends `OS scheme <scheme>, OS motion
  <motion>`, and `result.json`'s `sessions[]` keep them. A check of another scheme is skipped
  (`media:<scheme>`) and one of another motion too (`motion:<motion>`), so the owner runs a Light and
  a Dark pass, and a Light pass with Reduce Motion on for the two `reduce` checks
  (`demo-reduced-motion` and `spy-nav-click-reduced`, both light ones; owner decision 19).
  `--expect-os-motion` stops a session that read the other motion before its first check: its jobs
  are reported as never run, and the run fails.
- WebDriver cannot turn JavaScript off there, so the checks with JavaScript off are skipped
  (`javascript:off`): `nojs-deep-link`, `nojs-focus`, `nojs-focus-small`, `nojs-menu`,
  `nojs-menu-small`, `color-grid-nojs`, `femto-block-nojs`, `examples-nojs` and
  `examples-dialog-nojs`.
- Safari has no WebDriver BiDi: the viewport is sized through the window (a size its window cannot
  give fails the check); a check that needs a preload script is skipped (`preload`:
  `color-scheme-flash`, `examples-first-frame`, `examples-first-frame-cold`), except
  `theme-first-frame`, whose preload is optional (it reads paint timing there) and whose theme file
  is not held, and `spy-deep-link` and `spy-deep-link-small`, which then skip their not-animated
  assertion; and the loads checks read the pages' own entries only.
- `theme-os-live` switches the OS scheme while the page is open and `modal-scrollbar-width` forces a
  classic scrollbar, which the harness can do only with a preload script or Firefox's pref (it never
  changes macOS's settings), and `print-light` and `print-light-os-dark` print through WebDriver's
  Print command and Chrome's media emulation, so all four are skipped (`safari`). Safari cannot
  emulate forced colors either, so `expect_forced_focus` records a note there, as in Firefox.
- Its cache cannot be emptied, so the cold checks note that their load may be warm. Safari has no
  layout-shift entries, so `deep-link-cold` asserts the position only.
- Safari's Tab skips links and buttons by default, so the harness presses Option+Tab there
  (`page.tab()`).
- The Safari runs are the owner's (Owner's Safari steps). No Safari run has yet used WebDriver Get
  Computed Label, which `copy-button`, `breadcrumb-chapter`, `color-modal-tab-cycle`,
  `color-grid-tab`, `hero-link-copy`, `femto-switch` and `theme-swatches` read.

**Output.** `tests/results/<run-id>/` (run id `YYYYMMDD-HHMMSS-behavior-<pid>` unless `--run-id`):
- `result.json`: the run, the target, the sessions' versions (and Safari's OS scheme and motion),
  totals per browser, the checks selected, and every run with its status, the failing assertion's
  label, every assertion with its detail, notes, duration and document loads;
- `summary.txt`: failures first with their detail, then the skips with their reasons, then one line
  per run;
- `log.txt`: the sessions, then one line per run as it finishes;
- `shots/<browser>__<check>__<route>.png`: the viewport of every failed or errored run.

Statuses: `PASS`, `FAIL`, `ERROR` (an exception outside an assertion, such as a covered click target
or a WebDriver error, after which the session is restarted) and, in Safari, `SKIP`. A run passes
when every run is `PASS` or `SKIP`. Exit status 2 is a setup error: an unknown group, check, browser
or target, a missing build, the user's Safari open or the screen locked for a Safari run.

**Writing a check.** In a group module, `GROUP = "<group>"`, then:

```python
@check("name", ("/docs#modal", "/"), width=375, height=812, media="dark", storage={"femtoColorScheme": '"dark"'})
def name(page):
    """What it asserts, in terms of DOM state, focus, URL and storage (shown by --list)."""
    page.click(page.find("css selector"))                  # S's first match; a string selector is document-wide
    page.wait("label", "S.querySelector('...').open", 1)   # poll until truthy, at most 1 s
    page.eq("label", page.js("return ..."), expected)
    page.url_kept("label", url_before)                     # url_before = page.url(): no navigation, no new entry
```

`page` also has `ajs` (async scripts), `expect`, `holds` (true for a whole duration), `key`
(`ESCAPE`, `ENTER`, `ARROW_LEFT`, ...), `tab`, `focus`, `scroll_to`, `resize`, `new_tab`/`switch`
(a second tab of the same browser), `wait_navigated(path)`, `load(route)`, `find_all`, `el`, `els`,
`click_at`, `with_classic_scrollbars()`, `requests()`, `screenshot`, `note` and `url`, and the
route's `section` and `theme`. `behavior.HEADING_LINE` (a section heading's offset from its
scroll-padding line), `LOADS` (every frame's performance entries), `computed_name()` and
`expect_name()` (WebDriver Get Computed Label), `PICKER_ORDER` (the Theme picker's color order, read
from `/docs`), `nav_href` and `self_href` are shared helpers. The
first assertion that fails ends the check, and its label names the failure, so labels say what
should hold. Add the check to the table below.

### The checks

Each check's docstring (`--list`) is its full statement; this is the summary. Viewport 1300 × 900,
light OS and nothing stored unless the table says otherwise.

| Group | Check | Routes | Asserts |
|---|---|---|---|
| shell | `theme-toggle` | `/`, `/docs#typography` | No `data-theme` and nothing stored at first; the header toggle reads "Turn on dark mode" with ☀️. A click sets `data-theme="dark"`, stores `'"dark"'`, relabels "Turn off dark mode" with 🌙, URL unchanged; a second click, back to the OS's light, removes the stored choice and `data-theme` and restores the label and ☀️. |
| shell | `theme-toggle-dark-os` | `/docs` (dark OS) | The toggle follows the OS with no `data-theme`; a click stores `'"light"'`, and the next, back to the OS's dark, removes it and `data-theme`. |
| shell | `theme-toggle-keyboard` | `/`, `/docs#typography` | Enter on the focused toggle gives dark, and again the OS's light with nothing stored and no `data-theme`, with no navigation. |
| shell | `theme-os-live` | `/`, `/docs#table` | With nothing stored, a live switch of the OS scheme relabels the toggle and gives the homepage's femto off and on block the OS's color-scheme, or flips the inverse thead; nothing written. Skipped in Safari. |
| shell | `theme-stored-dark` | `/`, `/docs#button` (stored dark) | A stored choice wins over a light OS. |
| shell | `theme-stored-light` | `/docs#button` (dark OS, stored light) | `data-theme="light"`; a click, to the OS's dark, removes the stored choice and `data-theme`. |
| shell | `theme-stored-invalid` | `/docs#table` (dark OS, stored `'"blue"'`) | A stored value other than light or dark is ignored and left in storage: no `data-theme`, the page follows the OS. |
| shell | `theme-color-meta` | `/`, `/docs#table` (stored dark) | The two theme-color metas hold femto's light and dark backgrounds, `#fff` and `rgb(19, 22.5, 30.5)`, with their `prefers-color-scheme` media; a stored choice applies its own scheme's meta (media `all`, the other `not all`); the toggle to the OS's light removes the choice and gives both their media back, and a second click stores dark again; a light choice stored in another tab swaps them, and removing it there gives both their media back. |
| shell | `theme-cross-tab` | `/docs#typography`, a tab on `/` | A toggle in one tab reaches the other without a reload, and so does a second toggle, back to the OS's light, which removes the stored item and with it `data-theme` there; a light choice stored, then removed, in one tab does the same in the other. |
| shell | `color-scheme-flash` | `/`, `/docs` (stored dark) | Seen from a preload script, `data-theme` appears while the head is parsed, before the first paint, and the first frame sees it. Skipped in Safari. |
| shell | `header-fixed` | `/docs#modal` | `body > header` (`is-fixed-above-lg`) is sticky: its top is 0 at the top and scrolled to 21, 600, 0 and 300 px; its bottom border (femto's muted border color) is drawn and the same everywhere; its class never changes. |
| shell | `header-landing` | `/` | The landing header has no class, at the top and scrolled 600 px, and scrolls away with the page. |
| shell | `print-light` | `/`, `/docs#colors`, `/examples` (stored dark) | Print is light, and the controls that only work on screen have no box (PLAN.md Rules, CSS: In print), the Theme picker's swatches with their sentence and option switches, the Color schemes switcher, Grid's Add and Remove column, Typography's rem switch, the Modal demo's opener and the Colors palette's help among them (Chrome's print media emulated over CDP, with the OS light and then dark; Firefox has no way to emulate it, so there only the print below runs); on `/docs` every example's code footer and every standalone code block prints white, and the Colors swatches and the Themes dots keep `print-color-adjust: exact`; on `/examples` every inner and nested host is light with no `data-theme`, and a real WebDriver Print takes `data-theme` off the hosts and gives it back. Skipped in Safari. |
| shell | `print-light-os-dark` | `/docs#colors` (dark, nothing stored) | The same print assertions as `print-light` on `/docs`, with a dark OS and no stored choice. Chrome only (Firefox records a note); skipped in Safari. |
| shell | `reflow-320` | `/`, `/docs`, `/examples`, `/does-not-exist` (320 × 640) | No page is wider than the viewport (`<html>`'s scrollWidth is its clientWidth), and no element, open shadow roots included, ends past the viewport's right edge outside a box that scrolls or clips it (WCAG 1.4.10). |
| shell | `copy-button` | `/docs`, `/docs#modal` | The first and last copy buttons, whose tooltip is "Copy code", the words of their name, copy their block's text; "Copied" with ✓ within 100 ms, back to the button's own tooltip with ⧉ 900 to 1500 ms later; the button's computed name is "Copy code" throughout (owner decision 17). |
| shell | `copy-button-repeat` | `/docs#modal` | Two clicks 500 ms apart copy twice and revert once, 900 to 1200 ms after the last (one timer per button, restarted by every copy). |
| shell | `copy-failed` | `/docs#modal` | With a clipboard that refuses the write, a click tries to write the block's code and reads "Copy failed" with ⧉ kept, the status line says "Copy failed", and the tooltip is the button's own again 900 to 1500 ms later; with no `navigator.clipboard` at all, a second click fails the same way, the status line repeating its message with a trailing U+00A0. |
| shell | `modal-helper` | `/docs#modal` | `modal-is-opening` then `modal-is-open` 350 to 700 ms later; Escape closes the same way. |
| shell | `modal-scrollbar-width` | `/docs#modal` (classic scrollbars) | While open, `--femto-scrollbar-width` is the scrollbar's width and the page keeps its left edge. Skipped in Safari. |
| shell | `modal-two-dialogs` | `/docs#modal` (classic scrollbars) | One modal helper per dialog (PLAN.md Rules): Modal's demo is a true modal with the page inert; a script opening the color modal hides the demo at once, with one holder of `<html>`'s classes; Escape clears them. |
| shell | `side-menu-max-height` | `/docs#grid` (375 × 812) | From lg up the menu nav ends a femto spacing above the viewport's bottom (its `max-height` is `innerHeight` minus its top minus `--femto-spacing`, docs.css's `calc()` on `100dvh`), at 1300 × 900 and at 1300 × 700 scrolled; below lg it has none; `<body>`'s `min-height` is `innerHeight` (`100dvh`). |
| shell | `mobile-menu` | `/docs#modal` (375 × 812) | The breadcrumb's Documentation button opens the off-canvas menu and stops the page scrolling; Close reverses both; URL unchanged. |
| shell | `mobile-menu-keyboard` | `/docs#modal` (375 × 812) | Enter opens and closes it, with no navigation. |
| shell | `mobile-menu-focus` | `/docs#modal` (375 × 812) | Criterion 7's Escape and focus: focus moves into the menu and back to the opener, and `scrollY` stays put, also when `focus()` ignores its options (as Chrome Android does) and when focusing scrolls the page a frame later (as Safari 27 does). |
| shell | `mobile-menu-link` | `/docs#modal` (375 × 812) | Following Grid in the open menu closes it, with one new entry; back returns to `/docs#modal` in the same document. |
| shell | `breadcrumb-sticky` | `/docs#modal` (375 × 812) | Sticky at `top: -1px`: from its natural top it moves with the page until it sticks, then stays; its bottom border is drawn and the same everywhere; its class never changes. |
| shell | `breadcrumb-chapter` | 7 docs routes (375 × 812) | The breadcrumb reads "Documentation > <category> > <section>": after the Documentation button (it opens the menu), the items name the route's category and its section (the h1's text). Below 576 px the button shows ☰ alone, its computed name still "Documentation"; at 700 px the label shows. |
| shell | `example-forms` | `/docs#forms`, `#group`, `#color-schemes`, `#theme-picker` | Enter in every text-like input and a click on every submit button: no navigation, URL, history and document kept. No script cancels the submits: `method="dialog"` stops them (the note counts any a handler canceled). |
| shell | `example-forms-nojs` | `/`, `/docs#forms`, `#group`, `#color-schemes`, `#theme-picker` | The same with the page's JavaScript off (skipped in Safari): no navigation, since every example form has `method="dialog"`. |
| shell | `theme-toggle-button` | `/`, `/does-not-exist` | The toggle is a `<button type="button">`; Tab from the GitHub link reaches it; Space gives dark and Enter the OS's light again, with no `data-theme`. |
| shell | `mobile-menu-inert` | `/docs#modal` (375 × 812) | While open, everything outside the menu is inert and Tab stays in it; Escape, a nav link and a resize to 1300 all leave nothing inert. |
| shell | `copy-keyboard` | `/docs#button`, `/examples` | Tab reaches the first copy button; Enter and Space copy, with the tooltip and the `role=status` line reading "Copied" and focus kept, the tooltip back to "Copy code" after each; Space's copy repeats the status line's last message, so it ends in U+00A0. A block's `<pre>` is a tab stop only when its code overflows. The element before the button is looked for inside open shadow roots too, since on `/examples` the button follows its mockup's shadow root. |
| shell | `pre-scroll-keyboard` | `/docs` (375 × 812) | Quick start's first overflowing code block is a figure in the tab order with a `:focus-visible` inset ring, and Right arrow scrolls it. |
| one-page | `spy-deep-link` | `/docs#input` | The fragment scroll puts Input's heading on its line in one jump; the nav's one current link is `#input`, Forms open, the breadcrumb Forms > Input, the title "Input • femto". |
| one-page | `spy-deep-link-small` | `/docs#input` (375 × 812) | The same under the sticky breadcrumb. |
| one-page | `deep-link-cold` | `/docs#input` (cold) | Criterion 15: the heading on its line, and in Chrome layout shift below 0.01. |
| one-page | `nojs-deep-link` | `/docs#forms` (JavaScript off) | The heading on its line, the title unchanged. Skipped in Safari. |
| one-page | `nojs-focus` | `/docs`, `/`, `/examples` (JavaScript off) | Every tabbable element, the document's and its open shadow roots', is on screen and seen once focused; the controls that need JavaScript (PLAN.md Rules, CSS: the copy buttons, the header toggle and each page's own, on `/docs` the Theme picker's swatches with their sentence among them) are in the markup with no box. Skipped in Safari. |
| one-page | `nojs-focus-small` | the same (375 × 812, JavaScript off) | The same, where the menu's links sat off screen before docs.css's `(scripting: none)` rules. Skipped in Safari. |
| one-page | `nojs-menu` | `/docs` (JavaScript off) | The side nav's links, one per section, are all seen and inside the page's width; a click on Grid is the browser's own fragment navigation: `/docs#grid`, one new entry, the heading on its line, the title unchanged. Skipped in Safari. |
| one-page | `nojs-menu-small` | `/docs` (375 × 812, JavaScript off) | The same, where the menu is a static block before the sections, and the heading's line leaves room for its chapter label. Skipped in Safari. |
| one-page | `spy-scroll` | `/docs` | Grid's heading past its line: the nav and title at once, one `replaceState` of `/docs#grid` 180 ms or more later, no new entry; plain `/docs` at the top; the last section at the bottom. |
| one-page | `spy-fast-scroll` | `/docs` | 200 px every 16 ms, top to bottom: at most 3 `replaceState` calls, ending on the last section. |
| one-page | `spy-categories` | `/docs` | The nav's links are `menu.json`'s sections in order; at each section its link and category alone are current, the breadcrumb's chapter and section and the title follow, and the side nav, never the page, scrolls to show the link. |
| one-page | `spy-chapter-small` | `/docs` (375 × 812) | The breadcrumb's category and section follow the spy through every category, each section's name in full on one line beside the ☰ (one cut would be cut with an ellipsis). |
| one-page | `opener-shift-tab-small` | `/docs#grid`, `/docs#input` (375 × 812) | After a click on the breadcrumb's section item (the breadcrumb stuck at the top), Shift+Tab focuses the Documentation button (`button[data-menu-open]`) and the page stays where it is: no scroll event, `scrollY` within 1 px, and 600 ms later the hash, the breadcrumb's chapter and section, the title and `history.length` unchanged. The stuck button sits inside `html`'s scroll padding, which Chrome takes for out of view: without docs.css's scroll margin on it, Chrome scrolled the page 420 to 520 px up and the spy moved to the section before (Firefox did not scroll). |
| one-page | `opener-shift-tab` | the same (800 × 1000) | The same in the md container, where the root font size, and so the scroll padding, is larger. |
| one-page | `spy-nav-click` | `/docs#modal` | A click on Container: one new entry, the heading on its line, the nav straight to `#container`, the scroll smooth during it and `auto` after. |
| one-page | `spy-nav-click-reduced` | `/docs#modal` (reduced motion) | The same click jumps, never smooth. |
| one-page | `spy-back-forward` | `/docs#modal` | Back and forward after that click return to each section, not animated. |
| one-page | `spy-reload` | `/docs#css-variables` | A reload keeps the URL and the position or the heading. |
| one-page | `theme-first-frame` | `/docs?theme=jade#grid` (cold, jade's file held 300 ms) | Jade's stylesheet is parser-inserted and holds `DOMContentLoaded`, and the first contentful paint and first frame are already jade's (Decisions 8 and 14; owner decision 13). |
| one-page | `theme-kept` | `/docs?theme=jade#grid` | `?theme=jade` survives the spy and nav clicks. |
| one-page | `theme-unknown` | `?theme=bogus`, `azure`, `JADE`, `..%2Fthemes%2Fjade`, `jade.css` | No theme stylesheet, azure's colors, the query kept as given. |
| getting-started | `picker-options` | `/docs#theme-picker` | The three option switches regenerate the three samples exactly, and the page's option stylesheets follow them. |
| getting-started | `picker-code-highlight` | `/docs#theme-picker` | The samples are exactly the build's highlighting (one span per color run, plain text between) after every change. |
| getting-started | `picker-swatch` | `/docs#theme-picker` | Each swatch is labeled with its color; pumpkin's gives `/docs?theme=pumpkin#theme-picker` with no new entry and the page as a fresh load of pumpkin has it; azure's removes the parameter. |
| getting-started | `picker-logo` | `/docs#theme-picker` | A swatch animates the header logo once. |
| getting-started | `picker-swatch-focus` | `/docs#theme-picker` | Enter on a swatch keeps focus on it; Tab reaches the next. |
| getting-started | `picker-unknown-theme` | `/docs?theme=bogus#theme-picker`, `/docs?theme=JADE#theme-picker` | The picker ignores an unknown theme as the head script does. |
| getting-started | `picker-popstate` | `/docs#theme-picker` | Back and forward between swatch choices restore each theme in the same document. |
| getting-started | `picker-links` | `/docs#theme-picker` | Links to `#theme-picker` from the side menu and the footer keep `?theme=` and the options. |
| getting-started | `color-schemes-toggle` | `/docs#color-schemes` | The section's switcher and the header toggle drive each other; the switcher's second click, back to the OS's light, removes the stored choice and `data-theme`. |
| customization | `color-modal-open` | `/docs#colors` | Red 500 opens one `dialog.color` with its names and five values; Escape closes; Slate's header opens slate 600. |
| customization | `color-modal-arrows` | `/docs#colors` | The arrow keys step shades and families, wrapping at both ends. |
| customization | `color-modal-close` | `/docs#colors` | The modal, a true modal (`:modal`), closes on its close button, a backdrop click and Escape; a click inside does not. |
| customization | `color-modal-close-url` | `/docs#colors` | Closing leaves the URL and history as they were. |
| customization | `color-modal-focus` | `/docs#colors` | Enter on a shade opens a true modal with focus inside; Escape returns focus (`dialog.close()`). |
| customization | `color-modal-tab` | `/docs#colors` | The page behind is inert; Tab and Shift+Tab stay in the modal and keep `scrollY`. |
| customization | `color-modal-arrows-small` | `/docs#colors` (375 × 480) | Where the article overflows, the arrows step colors without scrolling. |
| customization | `color-modal-focus-small` | `/docs#colors` (375 × 480) | Focus starts on the close button, not the scrollable article. |
| customization | `color-modal-resize` | `/docs#colors` | The article's computed `max-height` is `innerHeight` minus two `--femto-spacing` (femto's `100svh` rule) as the window resizes, its bottom inside the viewport. |
| customization | `palette-download` | `/docs#colors` | The Download link points at a same-origin JSON file of the vendored `femto.colors.css`'s palette (20 × 19), byte for byte. The modal checks take their hex and RGB values from that file too; only the color names are the site's own. |
| customization | `color-modal-tab-cycle` | `/docs#colors` | Tab goes from the close button through the five copy buttons, each named by its icon's label alone; Enter copies, and the page's one status region says Copied from inside the dialog, where site.js moves it while the dialog is shown (in Chrome, CDP `Accessibility.getPartialAXTree` has it as a status, not ignored), and is back in `<body>` after the close; Tab past the last never reaches the inert page (focus stays in the dialog or leaves the document) and comes back in. |
| customization | `color-grid-tab` | `/docs#colors` | Each family's shades are a `role=toolbar` named by the family, with one Tab stop (its 50 at first); Tab visits the 20 families' stops and leaves the grid, and Shift+Tab comes back the same way. |
| customization | `color-grid-arrows` | `/docs#colors` | With a swatch focused, Right and Left move within its family, wrapping at its ends, and Home and End go to them; each of those keys' default is cancelled; the swatch reached is its family's stop and draws a ring with 3:1 contrast against it. Down and Up are not handled (a horizontal toolbar): their default is kept and focus stays. Each family keeps its own stop, reached by Tab and Shift+Tab; in forced colors (Chrome) the focused swatch shows an outline. |
| customization | `color-grid-ring-dark` | `/docs#colors` (dark OS) | Every swatch the keyboard reaches at 50 and at 950 in the 20 families, each family's 50 by Tab and its 950 by End, draws a ring with 3:1 contrast against it. |
| customization | `color-grid-modal` | `/docs#colors` | Enter and Space open the modal on the focused shade; closing gives focus to the swatch of the color shown last (after the modal's arrows too), which becomes its family's stop; a family header opens its main shade. |
| customization | `color-grid-nojs` | `/docs#colors` (JavaScript off) | The markup's 380 shade buttons, each a Tab stop, with no toolbar role or name added. Skipped in Safari. |
| layout | `grid-columns` | `/docs#grid` | Add and Remove column, from 4 up to 10 and down to 1: the columns, the code and its highlighting (the model `tokens_for`, on load too) follow. |
| content | `font-size-units` | `/docs#typography` | The "Display in rem" switch turns the table to rem and back to the exact load-time tree. |
| content | `font-size-restored-switch` | `/docs#typography` | With the switch restored as checked on a reload, the table shows rem from load. |
| content | `table-inverse-thead` | `/docs#table` | The example's thead reads `data-theme="dark"` on a light page and follows the toggle. |
| content | `table-inverse-thead-dark-os` | `/docs#table` (dark OS) | It reads `light`. |
| content | `link-examples` | `/docs#link` | The 6 example links go nowhere, clicked and with Enter. |
| content | `media-femto` | `/docs#media` | Every element of the Media section's four example cards has the computed styles of the same markup in a document that loads only the page's femto stylesheets, in a card of the same width; the image fits at 1200:630, each SVG fills with its text's color, and nothing scrolls sideways. |
| content | `media-femto-small` | `/docs#media` (375 × 812, dark OS) | The same. |
| content | `tokens-table` | `/docs#tokens` | 150 distinct tokens in row groups whose headers link to sections; Pair reads Yes exactly when `<html>` has both `--femto-light-*` and `--femto-dark-*` values (58), and every token not "set on" or "set per" elements has a root value. |
| forms | `checkbox-indeterminate` | `/docs#checkboxes` | The example checkbox is indeterminate after load; a click checks it. |
| forms | `select-optgroup` | `/docs#select` | Two optgroups, Italian (Pizza, Risotto) and Japanese (Ramen, Sushi), with the select's font and no margin; choosing Ramen selects it with no navigation. |
| components-a | `dropdown-items` | `/docs#dropdown` | The 21 example links in five dropdowns go nowhere, by pointer and by keyboard, and the dropdown stays open. |
| components-b | `modal-demo` | `/docs#modal` | "Open modal" opens the demo; Cancel, Confirm and the backdrop close it, a click inside does not. |
| components-b | `progress-examples` | `/docs#progress` | Both examples render from their markup alone: value 25 of 100 with its sample, and the indeterminate bar (`<progress></progress>`), each as wide as its card; nothing redraws them. |
| components-b | `nav-example-links` | `/docs#nav` | The 22 example links of the navs go nowhere. |
| components-b | `tooltip-link` | `/docs#tooltip` (1300 × 500) | The example link to `/docs#tooltip` puts Tooltip's heading on its line in the same document. |
| components-b | `tooltip-link-same-hash` | `/docs?theme=jade#tooltip` (1300 × 700) | A link to the URL's own hash still scrolls to it, keeping the URL, history and theme, and `is-scrolling-to-link` clears within 250 ms of the last scroll. |
| landing | `demo-loop` | `/` | The typing demo runs its 15 phases and loops, the code showing each phase's markup and the form its values. |
| landing | `demo-variant` | `/` (1280 × 800) | The large and small code layouts switch at 1280 px, each starting over. |
| landing | `demo-offscreen` | `/` | The demo pauses off screen and resumes on screen. |
| landing | `demo-pause` | `/` | The Pause button, shown once demo.js runs, stops the demo and the cursor's blink, and Play resumes them. |
| landing | `demo-reduced-motion` | `/` (reduced motion) | The demo starts paused at its first phase; Play starts it. |
| landing | `demo-inert` | `/` | The demo's form is inert with no `tabindex` in it, on load and once more controls show: each control refuses focus, and in Chrome the input is ignored in the accessibility tree; Pause sits outside the form. |
| landing | `hero-link-copy` | `/` | The hero's one code block is Quick start's @3 jsDelivr `<link>` line; its copy button, named "Copy code", copies exactly it. |
| landing | `femto-switch` | `/` | The femto off and on block: two declarative shadow roots, femto's link first and alone in the inner one, the markup after it the code sample's, with no class; the `role=switch` "femto", shown by demo.js, turns femto off in the block alone and on again; URL kept, nothing stored. |
| landing | `femto-switch-keyboard` | `/` | Tab from Pause reaches the switch, which in forced colors (Chrome) shows an outline; Space turns femto off and on, with focus kept. |
| landing | `femto-block-nojs` | `/` (JavaScript off) | The block renders in femto's styles; the switch and the swatches keep their `hidden` attribute, with no swatch. Skipped in Safari. |
| landing | `femto-block-scheme` | `/` | The block follows the header toggle, femto on and off (with femto off, the browser's own text color and no background). |
| landing | `femto-block-stored-dark` | `/` (stored dark) | The block is dark on a light OS from load. |
| landing | `theme-swatches` | `/` | 20 radios in the Theme picker's order (read from `/docs`), azure checked, each named by its color and drawn in its theme file's `--femto-primary-background`; Jade, Pumpkin and Azure recolor the page and the block in place (the theme `<link>` right after femto's in each); URL kept, nothing stored. |
| landing | `theme-swatches-keyboard` | `/` | Tab from the switch reaches the checked swatch, which in forced colors (Chrome) shows an outline; Right and Left arrows move to blue and back, recoloring. |
| examples | `examples-structure` | `/examples` | Each example's shadow root holds one div, whose own shadow root has femto's stylesheet alone and exactly the sample's markup (a nested shadow root read as its declarative template); no id repeats, shadow roots included. |
| examples | `examples-isolation` | `/examples` | Every mockup element has the computed styles of a femto-only document around the same markup in the same shadow roots: every property, and each of femto's tokens read by name (Rig notes, Firefox), with running CSS animations paused at their start on both sides. No site CSS reaches in. |
| examples | `examples-isolation-dark` | `/examples` (dark OS) | The same, dark. |
| examples | `examples-isolation-stored` | `/examples` (stored dark) | Every inner host, and every shadow host inside one, has `data-theme="dark"`, and the styles match. |
| examples | `examples-scheme` | `/examples` | The inner hosts, and the All theme colors example's 20 nested hosts, follow `<html>`'s `data-theme`: dark with the toggle, and none again, light, when it goes back to the OS's light. |
| examples | `examples-forms` | `/examples` | A click on every mockup form's submit button and Enter in the search field each submit once, with no navigation: no script cancels them, and `method="dialog"` stops them. |
| examples | `examples-forms-nojs` | `/examples` | With the page's JavaScript off (skipped in Safari), a click on every mockup form's submit button and Enter in the search field: no navigation, since every mockup form has `method="dialog"`. |
| examples | `examples-links` | `/examples` | Every visible mockup link goes nowhere. |
| examples | `examples-deep-link` | `/examples#every-element`, `#sign-in`, `#dashboard` | A link to an example lands its section a femto spacing below the viewport's top (`--femto-spacing`, its `scroll-margin-top` in examples.css), within 1 px, with its chapter label clear of the top edge; at the page's end a section may sit lower (noted). The URL keeps the hash. |
| examples | `examples-deep-link-small` | the same (375 × 812) | The same, where a femto spacing is smaller (16 px against 20). |
| examples | `examples-dialog` | `/examples` | The confirmation dialog opens as a modal and every way of closing it returns focus to the opener. |
| examples | `examples-dialog-nojs` | `/examples` (JavaScript off) | Both mockup dialogs open as modals from their openers and close from each of their three closers through `command` and `commandfor` alone. Skipped in Safari. |
| examples | `examples-dropdown` | `/examples` | The Account dropdown opens and closes on a click outside. |
| examples | `examples-fit` | `/examples` (375 × 812) | Nothing scrolls sideways or leaves its frame. |
| examples | `examples-first-frame` | `/examples` (stored dark) | The first frame with the mockups shows them dark with femto applied. Skipped in Safari. |
| examples | `examples-first-frame-cold` | `/examples` (cold) | The same with the cache emptied. Skipped in Safari. |
| examples | `examples-fold` | `/examples` | Each example's children are its header, its mockup and one closed `<details>`, whose summary reads "HTML" and whose `div.code` is not rendered while closed; the first and last open on a click, and their copy buttons copy exactly the sample. |
| examples | `examples-nojs` | `/examples` (JavaScript off) | Every example renders from its declarative roots with femto applied, each sample folded, and the theme select and the Copy as page buttons are not rendered. Skipped in Safari. |
| examples | `examples-copy-page` | `/examples` | Each Copy as page button copies exactly its sample in Quick start's starter template (read from `/docs`: the h2 for the title, `/vendor/femto/` paths as the template's jsDelivr ones), with jade's theme link after femto when jade is chosen; it reads "Copied" within 100 ms and "Copy as page" 900 to 1500 ms later, at the same width, and the page's one status region says Copied (ending in U+00A0 every other copy, as each repeats the one before), then nothing. Its timed last copy starts once the status region is empty again, 1 s after the copy before it. |
| examples | `examples-copy-page-failed` | `/examples` | With a clipboard that refuses the write, Copy as page tries once and reads "Copy failed" within 100 ms and "Copy as page" 900 to 1500 ms later, at the same width, the status region saying "Copy failed" too; with no `navigator.clipboard`, a second click fails the same way. |
| examples | `copy-announce-twice` | `/examples` | Two copies 500 ms apart are both announced: the Sign in example's code copy button (site.js), then its Copy as page button (examples.js), which share the page's one status region (`body > p.visually-hidden[role=status]`). Timed in the page with a MutationObserver on the region: Copied within 100 ms of the first click; within 100 ms of the second it is emptied and says "Copied" and a no-break space (U+00A0), since a screen reader such as VoiceOver skips a message that repeats the one before it; it is emptied once more, 900 to 1500 ms after the second click, not 1 s after the first. |
| examples | `examples-theme` | `/examples` | The select offers femto's 20 colors in the Theme picker's order (read from `/docs`), azure selected, each labeled with its name capitalized; a choice links its theme right after femto in every inner root, one theme link a root, and azure removes it; the page and the All theme colors roots keep their own; no `?theme=` and no new entry (Decision 8). |
| examples | `examples-newer` | `/examples` | The index links every example in page order; the five examples added on 2026-11-09 (`every-element`, `all-themes`, `checkout`, `landing-page`, `docs-layout`) hold what they show; Every element's modal opens and closes as a modal; All theme colors has 20 roots, one per theme file, each with a light and a dark card. |
| loads | `same-origin-loads` | `/`, `/docs`, `/docs?theme=jade`, `/examples`, `/does-not-exist` (cold, request log) | Criterion 15: nothing loads from another origin (Criterion 15's run-time check, below). |
| loads | `render-blocking-scripts` | the same five | Criterion 15: the only render-blocking scripts are the two inline head scripts. |

### Widget hooks

Each widget binds to a `data-` hook on its root element, written in the file that holds the markup,
and may narrow with selectors under it (PLAN.md Rules). The hooks:
- `site/docs.html`: `main[data-docs-spy]`, `aside[data-docs-menu]` (its Close button
  `button[data-menu-close]`) and `nav[data-docs-breadcrumb]`, which holds the Documentation button
  `button[data-menu-open]` (☰ and `<span>Documentation</span>`, which docs.css hides visually below
  576 px), then the category, then the section, the last two written by docs.js;
- docs.js's regions: `section[data-grid-example]` (layout), `section[data-font-size-demo]`, `section[data-inverse-thead]` and
  `article[data-link-example]` (content), `article[data-indeterminate-example]` (forms),
  `article[data-dropdown-example]` (components-a) and `nav[data-nav-example]` (components-b);
- site.js: `button[data-copy-link]` (named by `aria-labelledby` its icon's `copy-icon-<n>` id, which
  site.js assigns), the theme toggles `button[data-scheme-toggle]` (the header's) and
  `button[data-scheme-switcher]` (the Color schemes section's), `data-modal`, `data-modal-open`,
  `data-modal-close`, and `pre[data-scroll-focus]`, which build.mjs writes on every highlighted
  `<pre>` and site.js reads to keep only a block that overflows in the tab order. site.js also keeps
  the page's one copy status region, `body > p.visually-hidden[role=status]` (at the end of the
  shown dialog while `createModal()` shows one), which it exports as `announceCopy()`, and
  switches the two theme-color metas' media to follow a stored choice;
- colors.js: `data-color-modal`; picker.js: `article[data-version-picker]` (the Theme picker's
  swatches; the hook keeps its old name), `section[data-picker-options]` and
  `section[data-picker-usage]`; examples.js: `div[data-example]`, `button[data-copy-page]`,
  `p[data-examples-theme]` and `template[data-starter-page]`; demo.js: `article[data-typing-demo]`,
  `button[data-demo-pause]`, `div[data-femto-demo]` (its inner host `div[part=page]`),
  `label[data-femto-switch]` and `fieldset[data-swatches]`;
- a CSS hook only: `p[data-palette-help]` (colors.html), which docs.css hides without JavaScript.

demo.js's pause button, femto switch and swatches are hidden in the markup and shown by their
script, so they never show without one.
`docs.js` keeps one region per group, between `// region:<group>` and `// endregion:<group>`: one
`widgets("<group>", () => { ... })` call that declares nothing at the module's top level and adds no
import (site.js's exports are the `site` namespace). `widgets()` reports an exception without
stopping the regions after it.

## Criterion 15's run-time check

The `loads` group (`behavior/loads.py`) reads what the browser actually loaded on `/`, `/docs`,
`/docs?theme=jade`, `/examples` and the 404 page (`/does-not-exist`); `static_checks.py` reads the
same two rules from the markup, the CSS and the scripts.

```sh
uv run tests/run.py behavior --target dist --groups loads
uv run tests/run.py behavior --target dist --checks deep-link-cold   # the layout-shift part
```

- **`same-origin-loads`** (cold, request log). Each page is loaded three times: with nothing
  stored, then with `femtoColorScheme` `'"light"'`, then `'"dark"'`; with a stored choice,
  `data-theme` must follow it. In each load the location stays on the page's origin; every width
  (375, 600, 800, 1100, 1300 and 1600) is shown in light and in dark (Safari: its OS scheme); then
  the page is scrolled to its end and back. Then `behavior.LOADS` reads the navigation and resource
  entries of the document and of every frame it can reach, frames in open shadow roots included:
  every frame must be readable, no document's buffer full (250 entries), the navigation entry
  present, and every http(s) and ws(s) URL on the page's origin. Then, in Chrome and Firefox, the
  request log must hold at least 3 requests for the page's own path and no URL on another origin.
- **`render-blocking-scripts`**. Of the document's classic scripts (no type, or a JavaScript MIME
  type), those that block rendering (inline, or with a source and neither `async` nor `defer`) are
  exactly two, inline and in `<head>`: the `?theme=` script (its text has `document.write`), then the
  color-scheme script (its text has `femtoColorScheme`). There are exactly 2 classic scripts in all.
  In Chrome, which reports `renderBlockingStatus`, no loaded script is render-blocking.

URLs on `https://femto.style` (that scheme, host and default port only, as
`static_checks.same_origin()` reads it) are the site's own origin once deployed: noted, never
failed. Production adds one cross-origin load no build has, the zone's analytics beacon, criterion
15's exception, so a run against production fails on it, as it should.

A negative control on 2026-11-09 failed exactly the faults planted in a copy of the build (a
cross-origin `<img>` on `/`, a CSS background loaded only when dark and narrow on `/docs`, a
worker's fetch on `/examples` and a blocking classic script on the 404 page), in both browsers; only
the request log caught the worker's fetch. What the check cannot see is under Known limits.

## Accessibility

The a11y mode holds the site to criterion 10: axe-core finds no serious or critical violation on any
page, in Chrome and Firefox, light and dark, at 375 and 1300.

```sh
uv run tests/run.py a11y --target dist                    # the criterion's 40 cells
uv run tests/run.py a11y --target dist:/path/to/build --pages /,/docs
uv run tests/run.py a11y --plan                           # the cells; starts nothing
```

- **axe-core** is the repository's own: `node_modules/axe-core/axe.min.js` at the exact version
  `package.json` pins, never downloaded; a missing or mispinned copy is a setup error.
- **Pages** (`--pages`): `/`, `/examples`, the 404 page (`/does-not-exist`), `/docs`, and
  `/docs?theme=jade`, so a theme stylesheet's colors are checked too. `--schemes` and `--widths`
  change the other axes.
- **Cells**: browser × page × scheme × width, 20 per browser. Each is loaded as a behavior check is
  (a fresh headless tab, the viewport set exactly to the width × 800, the scheme emulated, storage
  emptied, the static readiness hook). Then axe's source runs in the document and `axe.run(document)`
  checks it whole; the script is injected, not loaded, so it makes no request.
- **Verdict.** A serious or critical violation fails the run; moderate and minor ones are listed. On
  2026-11-09 it passes with 16 moderate `landmark-unique` findings in 4 rows: the Nav section's
  Breadcrumb example at 1300 and the docs breadcrumb at 375, on `/docs` and `/docs?theme=jade`
  (femto styles breadcrumbs through `nav[aria-label="breadcrumb"]`, so they share the name).
- `result.json` keeps every cell's violations (rule, impact, help, each node's target, HTML and
  failure summary) and lists the findings once per impact, rule, page and target with the cells they
  were found in; `summary.txt` prints them in that order.

axe reads each document once, as loaded, in the default color mode, so it says nothing about forced
colors, WCAG 1.4.12's text spacing, reflow at 320 px, names a script changes later, or content that
updates on its own. The final review of the conversion measured those by hand, with WebDriver's
computed labels, Firefox's `browser.display.document_color_use` and Chrome's CDP forced-colors
emulation; the behavior suite holds the computed names, the pause buttons and, in Chrome, the forced-colors
focus of the Colors grid and the homepage's switch and swatches (`expect_forced_focus`).

## Static checks

`static_checks.py` checks criteria 4 to 15's static parts, the link check and, when named, the
release check. `--help` prints its full statement, with every interpretation where PLAN's wording
leaves a choice.

```sh
uv run tests/static_checks.py                        # every criterion and the link check
uv run tests/static_checks.py --criteria 4,5,12      # some of them
uv run tests/static_checks.py --json out.json        # also write the results as JSON
uv run tests/static_checks.py --strict               # NOT-YET counts as a failure
uv run tests/static_checks.py --femto DIR            # the femto checkout for 12 and 13 (default: SOURCE's source, $FEMTO_REPO, ../femto)
uv run tests/static_checks.py --root DIR             # check another checkout
uv run tests/static_checks.py --dist DIR             # check a built folder instead of ROOT/dist; criterion 5 builds into DIR
```

Each criterion reports PASS, FAIL or NOT-YET (with why), with evidence lines and notes. A criterion
with several parts fails if any part fails, is NOT-YET if none fails and some part cannot run, and
passes only when every part ran and passed. The exit status is 1 if any criterion fails (or, with
`--strict`, is not yet checkable), 2 on a usage error, and 0 otherwise. The check ids are 4 to 15,
`links` and `release`; `--criteria 1`, `2` or `3` is a usage error, since those criteria were
retired (the owner, 2026-11-09). Criteria 7 and 10, and 15's run-time parts, need a browser and
report NOT-YET with the harness command, in the Check workflow too. `run.py static` passes its
arguments to `static_checks.main(argv)`.

- **4, Packages and Pages configuration.** No dependencies, and no optional, peer or bundle
  dependencies. devDependencies must include `prismjs`, `wrangler`, `eslint`, `@eslint/css`,
  `html-validate` and `axe-core`, each pinned exactly; `eslint-plugin-baseline-js` (`COMPAT_LINT`,
  owner decision 5), `@eslint/js` and `globals` are accepted too, and any other package fails. The
  scripts are exactly `build`, `dev`, `vendor` and `lint`, and none runs `wrangler pages deploy` or
  `publish`. Decision 11's Pages files:
  - No file tracked or to be tracked (the index minus deletions, plus untracked files git does not
    ignore) is a `_redirects`, `_routes.json` or `_worker.js` at any depth, a folder of that name
    included (`PAGES_FEATURES`), or sits under a `functions/` folder at the root, which Pages' build
    compiles into Functions. `_redirects` and `functions/` were in the conversion's list of Remix
    paths, but they are Decision 11's, so they stayed when the list was retired.
  - `wrangler.jsonc` is there, not ignored, and the only Wrangler configuration file at the root (no
    `wrangler.json`, which wrangler 4.158.0 reads in its place, and no `wrangler.toml`). Read as JSON
    with comments and trailing commas, a repeated key failing, it has exactly `name` `femto-style`,
    `pages_build_output_dir` `dist` (`./dist` and `dist/` too) and a `compatibility_date` that is a
    real YYYY-MM-DD day. The pinned wrangler's `pages functions build-env`, run on a copy in a
    temporary folder so nothing is written into the repository, must exit 0 and write
    `pages_build_output_dir` `dist`. It exits 1 on a Workers key such as `main` or a missing `name`,
    and 159 without `pages_build_output_dir`; a wrong `name` passes it, so the field check holds that.
  - Proven on 2026-11-09 in a scratch copy of the repository: a planted `site/_redirects`,
    `site/_routes.json`, `site/_worker.js/index.js` and `functions/hello.js` each failed (the first
    three in criterion 5 too), and so did a deleted, ignored or repeated-key `wrangler.jsonc`, a
    `wrangler.json` beside it, a wrong `name`, a key typo, a `main` key, `./site`, and the dates
    2026-11-31 and "next week". `dist/`, a trailing comma and comments holding quotes passed.
- **5, Build output.** Two builds are byte-identical; `dist/` holds no copy of a partial or a section
  file, no per-route docs page, and no `_redirects`, `_routes.json` or `_worker.js` at any depth
  (Decision 11), wherever the build copied it from. The build's copies (`build_copy_checks`; the
  build strips comments from the site's own CSS and JavaScript, the owner, 2026-11-10): each
  `site/assets/**/*.js` in `dist/` has its source's espree tokens, each on its source line, with no
  comment left and the same line count; each `site/assets/**/*.css` parses with `@eslint/css-tree`
  (`@eslint/css`'s parser) with no error and no comment, keeps its line count and generates the same
  CSS as its source (`generate()` drops comments and normalizes whitespace). Every other file the
  build copies from `site/` (all but `partials/`, `docs/`, dot paths and the four pages at the root),
  `vendor/femto/` among them, is byte-identical to its source, and `dist/assets/` holds no CSS or JS
  without a source. espree and `@eslint/css-tree` come with `eslint` and `@eslint/css` from
  `node_modules`. On 2026-11-10 copies of `dist/` with a changed string, a planted comment and a
  token moved to the next line in `site.js`, a changed value and a planted comment in the CSS, a
  vendored file with one byte added, a missing `robots.txt` and an extra script each failed, with
  the file named.
- **6, URLs.** It starts `wrangler pages dev` on the build itself and probes every URL of PLAN's URL
  inventory: the pages and every `?theme=` color answer 200; `/docs/` and `/docs.html` 308; the old
  Remix docs routes, the 19 version-picker color routes, the 9 dropped routes, `/demo`,
  `/docs/forms/input.html`, `/docs/v1/` and its 20 pages (`V1_PAGES`) and other paths answer 404
  with the `404.html` body. The Pages-inherent paths (`PAGES_INHERENT`) must answer exactly as
  recorded, and are listed as notes.
- **8, Head.** `docs.html`'s title, description, `og:*` and canonical; `sitemap.xml` lists only page
  URLs. Also `shell_checks`: `site/partials/head.html` has exactly two `meta[name=theme-color]`,
  media `(prefers-color-scheme: light)` and `(prefers-color-scheme: dark)`, whose content equals,
  compared as a color (hex, `rgb()` and `rgba()` read to channels, exactly),
  `--femto-light-background-color` and `--femto-dark-background-color` in femto's
  `css/tokens/schemes.css` at the vendored commit, read with git (site.js may change the media at
  run time). `site/site.webmanifest` is valid JSON with `display` `"browser"`, a non-empty `id` and
  a non-empty `description`. `site/opengraph.png`'s IHDR is 1200 × 630, equal to `og:image:width`
  and `og:image:height` in the head partial, and the file is at most `OG_IMAGE_MAX` (32,000 bytes).
- **9, Valid HTML and ids.** `html-validate` under `.htmlvalidate.mjs`, shown to run (its version,
  and a JSON report that parses and names only the files given); every rule the config turns off or
  changes needs a reason in a comment above or beside it. Ids across declarative shadow roots count
  page-wide; the section ids, their headings and the side nav. Also `structure_checks`: every link
  in the Elements index's cells (`site/docs/sections/elements.html`) is `#<id>` of a section in
  `menu.json`. Every `section.example` in `site/examples.html` has exactly one direct, closed
  `<details>` holding `<summary>HTML</summary>` and `div.code` (`button[data-copy-link]`, `pre >
  code.language-html`) and nothing else, and a header with exactly one
  `button[type=button][data-copy-page]`. No `<select multiple>` or `<select size>` inside a
  declarative shadow root there has a preselected `<option>` (Firefox starts its layout before the
  head stylesheets apply). No element inside `section[data-color-modal]` in `colors.html` has
  `tabindex`, `role` or `aria-label` (`colors.js` adds them at run time). The Media section's live
  `<pre>`s hold a `<code>` with no class and a `<samp>`, so the build never highlights them. Every
  live `<form>` in `site/` (a literal `<form`, since a code sample is escaped) has
  `method="dialog"`, so no example form submits, with JavaScript or without: no script cancels a
  submit.
- **11, Lint.** The lint, its coverage and the forbidden syntax (Lint, below). Also
  `site_rule_checks`: no file in `site/assets/js` sets `role="group"` (read as tokens:
  `setAttribute("role", "group")`, `.role = "group"`, `{ role: "group" }`, or `role="group"` in a
  string's markup; comments are not code), and no dist page has `role=group` outside example markup
  (an article on `/docs` and `/`, a `section.example`, a shadow root), since femto styles
  `[role=group]` as its Group component. In the `/assets/css/` stylesheets more than one dist page
  links, no top-level rule's selector list holds a bare `section`, `article` or `footer`.
- **12, Vendored femto.** Every file equals the commit `SOURCE` names, read from the femto checkout
  with git; it also fails when git ignores a vendored file. Decision 4 (`release_tag_checks`): when
  `SOURCE`'s version has no `-`, `SOURCE`'s tag must name `v<version>` and its commit must be that
  tag's commit in the femto checkout; until then the check says it runs only for a release.
- **13, Content.** The content checks on the docs page (custom properties, files and URLs, classes,
  version strings, the package name and no Composer package, No Pico), plus:
  - **Prerelease wording**, keyed to `SOURCE`'s version. While it is a prerelease (it has a `-`),
    Quick start must keep the paragraph that names "prereleases" and `@<tag>` (`@alpha` for
    3.0.0-alpha.1, the tag taken from the version) and `@leoherzog/femto@<version>`, and any other
    prerelease dist-tag (`@beta`, `@rc`) fails. Once it is a release, no dist page or script
    outside `dist/vendor/` may contain `PRERELEASE_WORDING`: `@alpha`, `@beta` or `@rc`,
    "prerelease(s)", "until/once/before X.Y.Z is released", "the alpha", "a later alpha" or "is in
    alpha". That wording is today in Quick start's note and in the Theme picker's "Until 3.0.0 is
    released" paragraph.
  - **Drift**: the docs follow femto at the vendored commit, read with git. Each failure line starts
    with `drift:` and names the file to change. (a) Every hand-written list of theme colors
    (`THEME_LISTS`) equals `css/themes/*.css`'s names plus azure: the array in
    `site/partials/head.html`'s inline script (which may leave azure out), the Theme picker's swatch
    links (each with its class, its capitalized `aria-label` and its href,
    `/docs?theme=<c>#theme-picker` or `/docs#theme-picker` for azure), the Themes table's rows (the
    swatch, the name and `css/themes/<c>.css`, or "Built in" for azure), the Colors section's
    `article.family > header`s, `colors.js`'s PALETTE families, and any JavaScript string array of 3
    or more color names in site JS or inline scripts, `/examples`' `p[data-examples-theme]` select
    (each option's text its value capitalized, azure the one selected) and the All theme colors
    example's `css/themes/<c>.css` links. The lists a reader chooses from (the select, those roots,
    and `demo.js`'s `THEMES`, which `SWATCHES` follows, with azure checked) must follow the Theme
    picker's swatch order; the Themes table and the head script's array may be in any order. (b)
    `colors.js`'s SHADES, every PALETTE hex value and each family's main shade equal
    `css/femto.colors.css`'s `--femto-color-<family>-<shade>` and `--femto-color-<family>`, and the
    Colors grid's swatch buttons cover each family's shades. (c) Every `css/options/<name>.css` is
    named as `<name>.css` in the docs page's main. (d) The `readme` keys in `site/docs/menu.json` (a
    string, or a list of strings) name every femto README H2 but Contributing and License, and each
    is the exact text of a README H2 or H3: the heading line after its `#`s, trimmed, closing `#`s
    dropped, fenced code skipped, as `vendor.mjs` reads them. A section whose `readme` is `true`
    names its file's h1: the migration section, so that "Migrating from Pico" stays out of
    `menu.json` (criterion 14). A `readme` of any other kind, or `true` on a section file with no
    h1, fails.
  - Each drift check was proven to fail on altered copies on 2026-11-09: 16 variants of the site and
    a scratch femto clone with a new theme, a new option, a new README H2 and a changed red 500.
  - **femto's facts** (`femto_fact_checks`), read at the vendored commit with git, each failure
    starting `drift:`: the Tokens table's `<code>` tokens are, each once, the names declared
    (`--femto-x:`) in the files `css/femto.css` imports, minus every `--femto-light-*` and
    `--femto-dark-*` name (150 at 3be36bef), and a row's Pair cell is Yes exactly when both
    `--femto-light-<rest>` and `--femto-dark-<rest>` are declared (58). Each
    `<p><small><code>MODULE</code> reads <code>T</code>, …` line lists exactly the sorted
    `var(--femto-…)` names that module reads, or says "reads no tokens", and each of
    `READS_SECTIONS` has one (29 lines in 22 sections). The module map's rows are `css/femto.css`'s
    36 `@import`s in order, each Bytes cell the file's size, each summary the first sentence of its
    opening comment (lines joined, ` * ` dropped, whitespace collapsed, up to the first `. `), the
    tfoot total their sum (111,155), and the copyable list its `@import` lines. Every element in an
    Elements index row's first cell (62) is a type selector in an imported module (`INHERITED_ONLY`,
    empty, would list one styled only through inheritance, with its reason). `demo.js`'s
    `SWATCHES[i]` is the 6-digit lowercase hex of `--femto-primary-background` in
    `css/themes/<THEMES[i]>.css`. Every prose count `PROSE_COUNTS` reads in site HTML (tags dropped)
    and JS equals the measured number: N theme colors, N other theme colors, N color names, The N
    colors, N families, N swatches, N shades each, On N shades (white text below 4.5:1, 31), N
    shades, shade buttons or colors (the palette, 380), N options, N modules, @import lines or files
    instead of one, N (tokens) with a pair, N tokens, N pair properties and N custom properties (27
    counts on 2026-11-09, each phrase's number of matches in the PASS line).
  - **Example markup** (`markup_pair_checks`): each `/docs` example, an `<article>` whose last child
    is its `footer.code` sample, shows the sample's markup, compared as femto reads it. That means
    the same elements, text (whitespace collapsed; the sample's `...` stands for any text or
    content), classes and attributes, but `id`, `name`, `for`, `href`, `src`, `alt`, `placeholder`,
    `list`, `form`, `aria-label`, `aria-labelledby`, `aria-describedby`, `aria-controls`, `loading`
    and the site's `data-` hooks, which the live copy changes on purpose, and a live `<form>`'s
    `method="dialog"`, which its sample leaves out. Comments are dropped, and
    a sample that is one `<article>` is compared with the live article itself. Of the 78 pairs, 71
    are compared and 7 are in `MARKUP_DIFFERS`, each with the reason it differs on purpose. An entry
    that names no pair fails, and one whose pair now matches its sample is a note. Each `/examples` mockup's inner shadow root after exactly
    femto's `<link>` equals its HTML sample, whitespace collapsed, and so does the homepage's femto
    off/on block with `section.proof`'s sample, with no class in it, a live form's
    `method="dialog"` aside (the static form of `examples-structure` and `femto-switch`).
  - **Homepage and `/examples`** (`homepage_checks`): the hero's `section.hero .hook .code pre code`
    is Quick start's From a CDN block, `/examples`' `<template data-starter-page>` text is its
    Starter template, and the homepage states no size (a number before KB, kB, KiB, MB or bytes)
    unless "N KB gzipped" with N the gzip size of `dist/femto.min.css` at `WIRE_GZIP_LEVEL`, in KB.
  - **Used in** (`used_in_checks`): every `/examples#<id>` link in a section names an id in
    `site/examples.html`, and each example a "Used in" line links holds what `USED_IN` says its
    section shows (`details.dropdown` for Dropdown, `progress` for Progress, and so on).
  - **Pacifico** (`pacifico_checks`): `site/assets/fonts/pacifico-music-fest-mania.woff2`'s cmap
    (its WOFF2 table directory parsed and its stream inflated with Node's zlib) maps every character
    of the elements that a dist CSS file, `<style>` or `style` attribute gives a `font-family` or
    `--femto-font-family` naming Pacifico (today `#css-var-example > h1`, "Music fest mania"). A
    selector `simple_select()` cannot resolve (anything but tags, ids and classes with descendant or
    child combinators) fails.
  - Each of these, and criteria 8, 9, 11 and 12's new parts, was proven on 2026-11-09 by 45 planted
    mutations in a scratch copy, each failing with its file named, and a positive control (a correct
    homepage size sentence) that passed.
- **14, No Pico.** `git grep -il pico -- . ':!tests' ':!PLAN.md'`, run on tracked files and with
  `--untracked`, lists only `PICO_ALLOWED` and `site/vendor/femto/`.
- **15, Performance (static parts).** Same-origin loading as markup, CSS and scripts write it, the
  render-blocking scripts, and the `/docs` HTML budget, read from PLAN.md's Risks section: the first
  sentence there that says "budget" and gives sizes after it ("900 KB raw", "70 KB gzipped", "66 KB
  with Brotli"). The compressed sizes are on the wire (the owner, 2026-11-09): gzip at level 7 and
  Brotli at quality 3 (`WIRE_GZIP_LEVEL`, `WIRE_BROTLI_QUALITY`), with Node's zlib, so the sizes
  follow `.node-version` and need no Python package. On 2026-11-09 Cloudflare Pages served `/docs`
  between Brotli quality 3 and 4 and gzip level 7 and 8 on both hosts, and the check takes the
  closest level that is not smaller than what Pages serves. That day a build of the working tree
  gives `/docs` 420,408 bytes raw, 61,185 gzipped and 62,476 with Brotli, within the budget (PLAN.md
  Risks, Page size). The run-time parts point at the behavior suite.
- **Release** (`--criteria release --external`, never in the default run; NOT-YET without
  `--external`). `git ls-remote --tags --refs https://github.com/leoherzog/femto` must list no
  version tag newer than `SOURCE`'s version by semver precedence. A prerelease tag counts only
  while `SOURCE`'s version is a prerelease too, since the site vendors release tags (PLAN.md
  Decision 4). A failure says to vendor the newest with `npm run vendor -- ../femto <tag>`.

`--json` writes every result, with its evidence and notes, as JSON. The Check workflow
(`.github/workflows/check.yml`) runs the default set on every push and pull request. No workflow
runs `--criteria release --external` or `--criteria links --external`: they ask the network, so
they run by hand, and the `check` status the ruleset on `main` requires (PLAN.md Decision 11) means
only that the commit's static checks passed.

## Link check

The link check of `dist/` (`check_links`) runs with every default run of the static checks, and
alone with `--criteria links`:

```sh
uv run tests/static_checks.py --criteria links --dist /path/to/build             # internal links, and the external ones listed
uv run tests/static_checks.py --criteria links --external --dist /path/to/build  # and every external URL fetched once
```

- **Internal links.** Every URL a dist page links to or loads (`href`, `src`, `srcset`, `poster`,
  `data`, `action`, `formaction`, `cite`, SVG `href`, the `og:` and `twitter:` URL metas, JSON-LD's
  site URLs), declarative shadow roots included, resolved against the page's URL as Cloudflare Pages
  serves it, plus every `url()` and `@import` in dist CSS and the web app manifest's icons and
  `start_url`. A URL on `https://femto.style` (or relative) must name a page of the URL inventory or
  a file in `dist/`; a page's `.html` name or `/docs/` fails, since Pages answers it with a 308; a
  query is allowed only as `/docs?theme=<one of femto's 20 colors>`; a fragment must be an id or an
  `<a name>` in the target page's own tree, outside every `<template>` (`#` and `#top` are the top
  of the page). A fragment alone is looked up in the page that holds it, since the 404 page is
  served at every missing URL. An SVG `<use href="#id">` names an element of its own tree, shadow
  roots included. Code samples are text and are not read.
- **The same tab** (`same_tab_checks`; PLAN.md Rules, Markup, the owner, 2026-11-10). The site's own
  links to other origins (prose, header, footer, the edit links, the homepage's and `/examples`'
  own) have no `target` and no `rel` `noopener` or `noreferrer`, so they open in the same tab.
  Example markup that criterion 13 compares with its sample (a declarative shadow root, or a
  `/docs` article whose last element is its `footer.code`) keeps what femto's examples have and is
  not judged. A planted `target="_blank"` on an edit link and on the homepage's Baseline link both
  failed on 2026-11-10.
- **External links** are listed. With `--external` each distinct URL is fetched once (HEAD, then GET
  when HEAD fails, redirects followed, with a browser's User-Agent, since Figma and npm answer 403
  to a script's), and one that answers 400 or more, or not at all, fails, except one kind, which is
  listed:
  - femto's npm and jsDelivr URLs while they cannot answer yet, keyed to `SOURCE`'s version
    (`awaits_publish`). A range or tag URL (`@3`, `@alpha`, or no version, package pages included)
    is exempt only while the version is a prerelease. An exact-version URL is exempt only while that
    version is not on npm: `--external` asks `https://registry.npmjs.org/@leoherzog%2ffemto`, and
    when the registry does not answer, the exemption holds only while the version is a prerelease.

  An "Edit this section on GitHub" link (`EDIT_LINK`) that answers 404 fails, a file this branch
  adds included: it answers once the owner pushes `main` (Decision 11). The sections `tokens`,
  `elements` and `media` are not on `main` yet, so `--criteria links --external` fails for their
  edit links until the owner pushes `main`.
- **Controls.** Every run first copies `dist/` and plants six broken links, one per copy (a missing
  asset, a missing page, a missing fragment on another page, a missing fragment on the page itself,
  a page's `.html` name, an unknown `?theme=`); each copy must fail with exactly its planted link and
  nothing else new, or the check fails (`LINK_CONTROLS`).

## Lint

`npm run lint` is criterion 11's lint (`eslint.config.js`): `@eslint/css`'s `use-baseline` at
`widely` on `site/**/*.css`, and on `site/**/*.js` ESLint's recommended rules
(`js.configs.recommended`, `no-undef` among them, with `globals.browser`), `no-self-compare`,
`eqeqeq`, `no-var` and `prefer-const`, eslint-plugin-baseline-js's `use-baseline` at `widely`
(`COMPAT_LINT`, owner decision 5) and a never-list of `no-restricted-syntax` and
`no-restricted-globals` rules for what Decision 12 names. `site/vendor/` is ignored (criterion 12).
`static_checks.py`'s criterion 11 proves what the lint reads, in a temporary copy of the tree, never
the repository:
- a feature that is Baseline newly but not widely available, planted in each site CSS and JS file in
  turn, must fail the lint at `widely` (`CSS_PROBES`, `JS_PROBES`, calibrated against the installed
  tools first);
- each of the 12 `NEVER_PROBES`, planted alone, must draw a `no-restricted-*` report: the
  `navigation` global; `scrollend` as a string, as a template literal and as `onscrollend`;
  `content-visibility`; `blocking="render"` as an attribute and as a member;
  `scrollIntoView({container})` inline and through a variable; `focus({preventScroll})` with a name
  key and with a string key; and FontFaceSet's `loadingdone`;
- the two inline head scripts, written to files, lint clean as site JS (`sourceType` script) and
  report the first never-list probe planted in each.

The forbidden-syntax scans (`@layer`, `@scope`, `if(`, ...; `from` in color functions; `color-mix(`
without `in srgb`; smooth scrolling outside Decision 10's class) read code only, with comments
removed and strings blanked, in `site/**/*.css` outside `site/vendor/`, `<style>` and `style=""`.

**What the lint cannot see.** eslint-plugin-baseline-js checks syntax and the globals and static
members of JavaScript's built-ins and the Web APIs (`Promise.try`, `navigator.clipboard`). It does
not see instance members (`Set.prototype.union`, `element.moveBefore()`), event names passed as
strings (`"loadingdone"`) or members of an options object (`focus()`'s `preventScroll`); its README
leaves instance members to a type-aware preset that needs TypeScript. So `JS_PROBES` are static
members, and the never-list catches Decision 12's cases by spelling, not by meaning:
- an event name anywhere as a string or a template literal, and as an `on<event>` property;
- an option (`container`, `preventScroll`) as a key of any object, a name or a string, so an options
  object built ahead of the call is caught too, and also an unrelated object with such a key
  (`site/assets/js` has none);
- `blocking` as a string and as a member.

An event name built from parts (`"scroll" + "end"`), or an option key computed at run time, still
passes. The lint never reads the `<style>` in `site/docs/sections/css-variables.html`, `style=""`
in `site/docs/sections/nav.html`, or the CSS site JS writes (criterion 11's note lists each place:
five in site JS on 2026-11-09). The conversion's final review checked all of these, and the site's
JS for instance members, event names and options, by hand against @mdn/browser-compat-data 8.1.8
and web-features 3.45.0 (2026-11-06), and criterion 11's note says so on every run. JS written
since then was not part of that review.

## Output

`tests/results/<run-id>/`, one folder per run (gitignored):
- the behavior mode: `result.json`, `summary.txt`, `log.txt`, `shots/` (Behavior, Output);
- the a11y mode: `result.json`, `summary.txt` and `log.txt` (run id `YYYYMMDD-HHMMSS-a11y-<pid>`);
- the rig: `rig.json` (run id `YYYYMMDD-HHMMSS-rig`);
- every mode that starts the `dist` target: `server-dist-<port>.log`, `wrangler-debug-<port>.log`
  and `wrangler-state-<port>/`.

`static_checks.py` writes nothing unless `--json FILE` names a file.

## Concurrency and locks

The same locks as femto's harness, in the same place and under the same names, so the two harnesses
share them:

- **Slots**: at most `FEMTO_HARNESS_SLOTS` (default 4) browser sessions run at once on the machine,
  across all harness processes. Each worker (one WebDriver session, the rig's included) holds a slot
  for its lifetime and waits, logging once a minute, when all are taken.
- **Safari**: one Safari session at a time machine-wide (`safari.lock`). Only the harness starts
  Safari, and only through this lock.
- **Driver start**: WebDriver start-up is serialized (`driver-start.lock`), because concurrent
  Selenium Manager runs corrupt `~/.cache/selenium/se-metadata.json`.
- Locks are `flock`s on files in `FEMTO_HARNESS_LOCK_DIR` (default `~/.cache/femto-harness/locks`);
  each holds the pid and label of its owner and is released when the process exits.

Servers take no slot. Each run starts its own `wrangler pages dev` on free ports, with its own state
folder, so runs against different builds never share a server.

## Rig

`uv run tests/run.py rig [--browsers chrome,firefox,safari] [--run-id ID]` proves the mechanisms the
behavior and a11y modes rely on. It needs no build: it serves `harness/probe.html` and
`harness/probe-loads.html` from two servers on `127.0.0.1`, the second on another port, so another
origin, and drives them with the behavior mode's own `Session` and `Page`, as a check would:
- **viewports**: 375, 600, 800, 1100, 1300 and 1600 wide, 812 tall: exact `innerWidth` and
  `innerHeight`, and `matchMedia` agrees;
- **color scheme and motion**: light and dark, each with no-preference and reduce, seen by
  `matchMedia` and by a `light-dark()` color (Safari: the OS's, read);
- **scripts**: the inline page script runs, and a preload script runs before it (not Safari);
- **input**: hover, `:active`, Tab to `:focus-visible`, and `document.hasFocus()`;
- a viewport **screenshot**;
- **JavaScript off** (not Safari);
- **the cache** (not Safari): `probe.css` loads with `transferSize` 0 warm and above 0 once the cache
  is emptied;
- **a held response** (not Safari): `probe.css` held 0.6 s takes at least 500 ms;
- **loads**: four loads from the other origin (an `<img>`, an `<img>` to a port nothing listens on,
  an `<img>` in a `srcdoc` iframe inside a closed shadow root, and a `fetch()` from a dedicated
  worker). The pages' entries must see the image, and the request log (not Safari) the image and the
  failed load. A request-log miss of the closed frame or the worker is listed under `limits`, which
  does not fail the rig.

It writes `tests/results/<run>/rig.json` and exits 1 when a mechanism fails. On 2026-11-09 it passed
in Chrome Beta 158 and Firefox 160: the entries saw the image and the failed load, and the request
log saw all four. It has not run in Safari since the rewrite, since the screen was locked.

### Rig notes

The machine is femto's rig: macOS 27.2, 10 CPUs, 16 GB, Google Chrome Beta, Firefox and Safari.
macOS here uses the Auto appearance, so the OS scheme is light by day and dark after sunset; every
Safari session records the scheme it read.

**Chrome Beta (headless).**
- Options: `--headless`, window 1800 × 1100, `--force-device-scale-factor=1`,
  `--force-color-profile=srgb`, no background throttling, BiDi on. CDP
  `Emulation.setFocusEmulationEnabled` keeps `:focus` working in a headless tab.
- Chrome Beta updates itself; each run's result records the version.
- The content of a closed `<details>` is `content-visibility: hidden` in Chrome, so its style is
  updated only when something reads it, and `getClientRects()` still reports its boxes:
  `checkVisibility()` tells whether it is rendered.

**Firefox (headless).**
- `prefers-color-scheme` is the pref `layout.css.prefers-color-scheme.content-override` (0 dark, 1
  light), set at runtime from the chrome context, which needs geckodriver's `--allow-system-access`.
  The new value reaches content asynchronously, so the harness polls `matchMedia` before loading.
- **System font fallback.** By default Firefox finds fallback faces asynchronously: for about 2 s
  after startup, text that needs one is laid out with a provisional face (the italic Arabic `cite`
  in RTL measured 83.5 px, then 80.45 px). The harness sets `gfx.font_rendering.fallback.async`
  false, so the first layout is already final.
- **A preselected list box.** A `<select multiple>` or `<select size>` with a preselected option on
  load starts layout before the head stylesheets apply: an animation frame then sees no sheets, and
  transitions run after load. So Every element's multiple select on `/examples` has none, which
  criterion 9's structure check holds.
- **The cache.** `Services.cache2.clear()` empties the HTTP cache but leaves a stylesheet a page
  loaded in memory, so the cold checks' CSS used to load warm. `Page.clear_cache` now runs
  `Services.clearData.deleteData(CLEAR_ALL_CACHES)`; the rig's cache check shows the difference.
- **Computed custom properties.** A computed declaration's list of property names is not complete
  for custom properties in Firefox 160. On 2026-11-09, over the 94,785 pairs of a mockup element on
  `/examples` (355, pseudo-elements included) and one of the 267 tokens femto.css names, Firefox
  listed 66,454 and Chrome 91,368. Firefox listed 120 more on the page than in the femto-only
  reference, all four of femto's root tokens (`--femto-light-contrast-hover`,
  `--femto-dark-contrast-hover` and their `-background` versions) that the reference's twin element
  did not list, so the three `examples-isolation` checks failed there. `getPropertyValue()` gave the
  same value for every one of the 94,785 pairs on both sides. The checks now read each femto token
  by name. They still fail in both browsers on a planted `--femto-form-label-font-weight` on
  `section.example` (the one token femto reads but does not declare on `:host`, so the one that
  inherits into a mockup) and on a `letter-spacing` set through `::part(example)`.

**Safari (visible, serialized).**
- No `prefers-color-scheme` or `prefers-reduced-motion` emulation: the session reads both from macOS
  with `matchMedia`. The harness never changes them; the shell cannot read Reduce Motion reliably
  (`defaults read com.apple.universalaccess reduceMotion` finds no key on this Mac).
- While your own Safari is open, a new WebDriver session never starts (Safari 27.2), so the harness
  refuses to start one and exits 2. Quit Safari (Cmd-Q) before every Safari run. Before each session
  the harness terminates leftover `Safari ... --automation` processes (only safaridriver starts
  Safari with that flag; your own Safari is never touched), and a session refused as "already
  paired" is retried once after terminating them again. safaridriver leaves its automation Safari
  running even after a clean quit, so every session's quit terminates it, under the Safari lock.
- On a locked screen the page reports `visibilityState: hidden`, `requestAnimationFrame` never runs
  and pointer and keyboard input never arrive. The behavior mode and the rig's input checks need the
  screen unlocked, the automation window in front and nobody using the machine (Screen Sharing
  included). The screen locks once the display sleeps; `caffeinate -d -i` holds it awake for a run.
- A command that times out ends the session like a WebDriver error: the run is an error, the
  session is quit with a 10 s limit, its driver process is killed, and the automation instance is
  terminated; the next run starts a new session.
- **Speculative loading.** At the start of a load, Safari requests the subresources the last load of
  the same URL used, `Cache-Control: no-store` notwithstanding, and serves the responses to the next
  document that asks for them.

**The site's server** (`wrangler pages dev` 4.158.0 from `node_modules`, on macOS). Two answers
differ from what criterion 6 says of "any other path", and both come from looking files up on this
Mac's disk; `static_checks.py` probes neither:
- A path below a file answers 502, with only `[wrangler] Could not serve static asset: Error:
  ENOTDIR` as its body: `/_headers` (wrangler looks up `dist/_headers/index.html`), `/robots.txt/x`,
  `/favicon.svg/x`, `/docs.html/`, `/docs.html/x`, `/examples.html/`, `/index.html/`, `/404.html/`,
  `/favicon.svg/` and `/sitemap.xml/`, and also `/docs%00`. On Cloudflare Pages `/_headers` answers
  404.
- A page path in other letter case answers 200 with the page, since APFS is case-insensitive:
  `/DOCS`, `/Docs`, `/docs.HTML` and `/EXAMPLES`. The Check workflow serves `dist/` on Linux, where
  these should be 404. The `?theme=` head script and picker.js apply a theme only on the exact path
  `/docs`, so such a spelling shows azure.

**All three.**
- `getComputedStyle()` returns an empty declaration for an unknown pseudo-element and reads
  `::backdrop` on a closed dialog too.
- Selenium's default pointer move lasts 250 ms; the harness uses duration 0.
- **Performance entries.** A probe on 2026-10-30 made six cross-origin loads: a parsed stylesheet
  and a `no-cors` fetch to a refused port, a CORS-mode `fetch()` without
  `Access-Control-Allow-Origin`, a `no-cors` fetch answering 200, an `<img>` answering 404 and a
  script-inserted stylesheet answering 200. Chrome Beta 158 listed all six; Firefox 160 listed the
  four that reached a server and neither refused one; Safari 27.2 listed three, leaving out the
  CORS failure too. All three list a cross-origin entry's URL without `Timing-Allow-Origin`.

## Known limits

- **What the loads check cannot see.**
  - In Safari there is no request log, so a worker's loads, a frame in a closed shadow root, a load
    that fails before any response and a load served from memory go unseen there. Safari still
    reads every page's own entries at every width.
  - In Chrome and Firefox, a resource served from an in-memory cache without a request (an image
    Firefox serves from its image cache) might produce neither an entry nor a request event. The
    first of the three loads is cold, so every resource is requested at least once; only something
    new on the warm stored-theme reloads could slip past. The rig does not prove this case.
  - Each load starts at 1300 px in light and then resizes, switches schemes and scrolls in place,
    so a resource chosen only at load time at a narrow width (none on the site today) could be
    missed.
  - Neither way sees a WebRTC connection or a page a script opens in a new window.
- **Storage.** Every check starts with `localStorage` and `sessionStorage` emptied on the target's
  origin. Cookies are not cleared within a session; the site sets none.
- **Not seen in any run:** whether safaridriver answers WebDriver Get Computed Label; `focus()`
  scrolling on Chrome Android and Samsung Internet (only Chrome's CDP mobile emulation, where a bare
  `focus()` jumps 415 px and the site's refocus does not); real touch input (only synthetic
  `PointerEvent`s); forced colors other than Firefox's `browser.display.document_color_use` and
  Chrome's CDP emulation; and whether Cloudflare Pages matches paths case-sensitively.
- **Fallback paths no check reaches:** a theme stylesheet that fails to load, after which the picker
  loads the swatch's URL instead (`picker.js`), the homepage's swatches drop the link and check the
  swatch of the color still shown again (`demo.js`), and `/examples` keeps the color shown and puts
  its select back (`examples.js`); the typing demo pausing when reduced motion turns on while the
  page is open, and waiting while the page is hidden (`demo.js`); a color-scheme choice that storage
  refuses (`site.js`); and a stored value that is not JSON (`partials/head.html`, `site.js`). The
  copy buttons' and Copy as page's "Copy failed" are reached with a stubbed clipboard
  (`copy-failed`, `examples-copy-page-failed`), never with a browser's own refusal.
- **Not checked:** the All theme colors example's first frame with a stored scheme that differs
  from the OS, before `examples.js` gives its 20 nested hosts `data-theme` (PLAN.md Risks); a screen
  reader's own handling of the copy status region, where `copy-announce-twice` asserts only the DOM
  mutations; in Firefox, print media on `/` and `/docs` (`print-light`, `print-light-os-dark`); and,
  in Firefox and Safari, forced colors (`expect_forced_focus`).
- **The lint's blind spots** (Lint): instance members, event names built at run time and computed
  option keys, the `<style>` and `style=""` sources, and the CSS site JS writes.

## Owner's Safari steps

`tests/owner-safari.sh` runs them, and only the owner runs it, since it switches macOS's appearance
(to Light, then Dark) and puts back the one it found, even when stopped with Ctrl-C. Quit Safari
(Cmd-Q), unlock the screen and leave the Mac alone until it prints `done`. Each mode refuses to start
when a result folder it would write already exists, and names the next free run number, so a rerun
never overwrites a pass's evidence; `N` (default 1) numbers the run ids, as in
`tests/owner-safari.sh final 2`:

```sh
tests/owner-safari.sh final      # criteria 7 and 15 in Safari, Reduce Motion off: about 10 minutes
tests/owner-safari.sh reduced    # the prefers-reduced-motion checks, Reduce Motion on: about 2 minutes
uv run tests/run.py rig --browsers safari   # the rig's Safari mechanisms
```

- **`final [N]`** builds `dist/`, then runs the behavior suite, `behavior --target dist --browsers
  safari --expect-os-motion no-preference`, in Light as `behavior-safari-light-N` and in Dark as
  `behavior-safari-dark-N`. Each pass runs its scheme's checks and skips the other's as
  `media:<scheme>`, which the other pass runs. The suite's `loads` group is criterion 15's run-time
  half; in Safari it reads the pages' own entries only. The script stops unless the run's `log.txt`
  says `OS motion no-preference`.
- **`reduced [N]`** is owner decision 19. Turn macOS's Reduce Motion on first (System Settings >
  Accessibility > Display > Reduce motion). It builds `dist/` and runs the behavior suite in Light
  only, `behavior --target dist --browsers safari --expect-os-motion reduce`, as
  `behavior-safari-reduced-light-N`: the two `reduce` checks (`demo-reduced-motion` and
  `spy-nav-click-reduced`), which the `final` passes skip. Both are light checks, so a Dark pass
  would run none. Every other check is skipped. The script
  stops unless the log says `OS motion reduce`, and always ends by reminding you to turn Reduce
  Motion off again.

At the end the script prints, for each run, how often its `log.txt` says `OS scheme light` or `OS
scheme dark` and `OS motion reduce` or `OS motion no-preference`. A run whose log has no OS motion at
all started no Safari session, and the script stops saying so: the run's HARNESS ERRORS give the
cause. Each step is one command under `caffeinate -d -i`, so one can also be run by hand. The
behavior suite needs the automation window in front the whole time. Before the `loads` group was
added the Light pass took 411 s and the Dark one 12 s.

## Owner decisions

The owner's decisions that the checks still follow, numbered as at `conversion-final`, whose record
holds the rest.

- **3. `.gitignore`** (2026-10-30). It reads `/dist/`, so `site/vendor/femto/dist/` is not ignored;
  criterion 12 also fails when git ignores a vendored file.
- **5. The JS compat lint** (2026-10-30). `static_checks.py` accepts eslint-plugin-baseline-js
  (`COMPAT_LINT`) and no other plugin, since Decision 12's target is Baseline Widely Available, the
  target `@eslint/css`'s `use-baseline` checks too.
- **10. Safari's reload** (2026-11-02). In Safari 27.2 `location.reload()` returns to the `#hash`
  section's heading rather than the exact position. The owner accepted it, as Chrome's back
  already is, so `spy-reload` passes on either.
- **13. The `?theme=` first paint in Firefox** (2026-11-04). With one inline head script, Firefox
  paints femto's default color before the `document.write` theme `<link>` arrives: it holds its
  first paint only for a stylesheet that a later parser-blocking script waits on. The owner chose
  two inline head scripts, the `?theme=` one first and the color-scheme one second (PLAN.md
  Decisions 8 and 14, criterion 15); `theme-first-frame` holds it.
- **14. The `/docs` size budget** (2026-11-05). The owner raised the gzip and Brotli limits to 70 KB
  and 48 KB rather than trim the page, both at their maximum levels. On 2026-11-09 the owner moved
  the measure to the wire (Static checks, 15). The lead agent, not the owner, restated the same
  Brotli limit as 66 KB at quality 3 (PLAN.md Risks, Page size); the owner can tighten it.
- **15. femto's dark hover color** (2026-11-05). Criterion 10's last failure was white text on femto's
  dark `--femto-primary-hover-background` in 9 of the 20 themes. The owner fixed it in femto
  rather than record an exception, and the site vendors the fix.
- **16. Hosting by Git** (2026-11-06). Cloudflare Pages' Git integration deploys, with no `deploy`
  script (PLAN.md Decision 11, criterion 4). On 2026-11-09 the owner added `wrangler.jsonc`, which
  pins the build output directory (criterion 4 checks it), and chose a GitHub ruleset on `main` to
  require the Check, on since that day (PLAN.md Decision 11).
- **17. The copy buttons' names** (2026-11-06). Each copy button is named by `aria-labelledby`
  pointing at its icon's id, so femto's tooltip text never joins its name. Decision 18's text
  stays: the `aria-label` stays on the icon. site.js gives the icons their `copy-icon-<n>` ids,
  since the buttons work only with JavaScript.
- **19. Reduce Motion in Safari** (2026-11-06). The harness reads Safari's OS `prefers-reduced-motion`,
  as it reads the OS scheme, and the owner runs one more Safari pass with Reduce Motion on:
  `tests/owner-safari.sh reduced`.
- **20. Live before femto's first npm publish** (2026-11-06). Production went live from `main` before
  `@leoherzog/femto` was published, so the docs' jsDelivr and npm instructions for the alpha fail
  until then. The owner chose no site change: the docs keep following femto's README (PLAN.md
  Risks, femto is alpha and unpublished).
- **23. The steady state** (2026-11-09). The conversion's scaffolding is retired, its record at tag
  `conversion-final`: the oracle, the parity harness and its modes, the divergence registry, the
  converter, the research, `PROMPT.md`, criteria 1 to 3 and the phases. The behavior suite, the
  a11y run, the static checks and the link check stay. femto stays vendored from git, from release
  tags (PLAN.md Decision 4), and criterion 15's budget is measured on the wire.
