# 05 Spike: one page, URL following the scroll

## Verdict

The one-page mechanism the plan adopts works in Chrome Beta 158.0.8127.2 and Firefox 160.0, both headless. In that mechanism, the `#hash` follows the section being read and `?theme=` sets a theme color. All 13 checks pass in each browser, plus a deep-link check in Chrome with JavaScript off.

It needs about 130 lines of plain JavaScript, using only features that are Widely available by 2026-11-13. The browser's own fragment navigation does the rest: links, deep links, back, forward and reload.

Safari 27.2 ran it in Phase 0 (2026-11-01, `tests/results/p0-spike-safari.txt`, under femto's rig rules: Safari quit first, the screen unlocked, the machine idle). It passed 11 of the 13 checks as first written. The other two were Safari's own geometry and behavior, not a fault in the mechanism: `location.reload()` returns to the `#hash` section's heading instead of the exact position, and the Quick start click put the heading exactly at the scroll-padding line, as in Chrome, but Safari's padding there is 80 px, which left the page at y 30 where the check wanted below 30. On 2026-11-02 the owner accepted the reload behavior, as Chrome's back already is, and the two checks were revised: reload passes on the exact position or on the `#hash` heading, and the Quick start check reads the heading's position instead of the page's y. All three browsers pass all 13 revised checks; Safari's run is `tests/results/p0-spike-safari-2.txt` (2026-11-02, `tests/owner-safari.sh spike`), with the same positions and probe results as the first (Results, below).

The spike ran twice on 2026-10-30. Round 1 tested section paths (`/docs/modal`), before the owner chose hashes. Round 2 tested hashes, and it is what `spike/` holds now.

## What was built (round 2)

Everything is in `docs/research/spike/`:

| File | What it is |
|---|---|
| `make.py` | Writes `docs.html`: 12 stand-in sections modeled on real routes, of varying length. Two are much shorter than the viewport, and the last one is short. Each section's `h1` carries its one-or-two-word id; subheadings carry none. The inline head script adds the `?theme=` stylesheet by one of three methods, chosen by `?method=` for comparison, and records `--femto-primary` in the first animation frame. |
| `docs.js` | The spy from 02 §4: scroll math per animation frame, a `replaceState` of `#id` after 200 ms (no hash for the first section), and the spy locked until 150 ms without scroll events after a click or a traversal. Smooth scrolling is on only during a nav click. |
| `spike.css` | A fixed header and a sticky side nav beside one `main`. |
| `femto.min.css`, `femto.colors.min.css`, `themes/` | Copied from `../femto` commit 65453b74 ("Prepare 3.0.0 Alpha 1", 3.0.0-alpha.1): its `dist/femto.min.css`, `dist/femto.colors.min.css` and `css/themes/`. |
| `serve.py` | A static server that behaves like Cloudflare Pages for this case. `/x` serves `x.html`, and anything else that is not a file is a 404. It sends Pages' `Cache-Control: public, max-age=0, must-revalidate`, and delays `/themes/*` by 300 ms so a late theme shows up. |
| `test_spike.py` | Selenium 4.52.0 under `uv`, driving the rig's Chrome Beta and Firefox headless at 1280×800, Chrome with JavaScript off, and Safari in a visible window (`safari`, run alone). `--probes` adds the measurements below. Nav clicks are WebDriver element clicks, which are real input (Safari, below). |

To run it:

```sh
python3 -I docs/research/spike/make.py
python3 -I docs/research/spike/serve.py 8790 &
uv run docs/research/spike/test_spike.py 8790
```

## Results (round 2)

| Check | Chrome 158 | Firefox 160 | Safari 27.2 |
|---|---|---|---|
| `/docs#input` lands on Input's heading, below the header, with the right nav link and title | pass | pass | pass |
| The same with JavaScript off (the browser's own fragment scroll) | pass | not run | not run (WebDriver cannot turn JavaScript off in Safari) |
| Scrolling into Grid writes `#grid` and the title "Grid • femto" | pass | pass | pass |
| Scrolling back to the top leaves plain `/docs` and the page's own title | pass | pass | pass |
| Scrolling to the very bottom makes the short last section current | pass | pass | pass |
| A fast scroll from top to bottom (200 px every 16 ms) makes at most 3 `replaceState` calls and ends on `#tooltip` | pass | pass | pass |
| A nav click pushes exactly one history entry, lands on the heading, and the nav never shows a section in between | pass | pass | pass |
| Back returns to the previous entry, and the spy follows | pass (to the `#hash` heading) | pass (to the exact position) | pass (to the exact position) |
| Forward returns to the clicked section | pass | pass | pass |
| `location.reload()` mid-section returns to the exact position or to the `#hash` heading (revised 2026-11-02; it was "keeps the position") | pass (exact) | pass (exact) | to the `#hash` heading: y 4,149 before, 3,240 after, the `#css-variables` heading at 80 px, where a fragment link puts it. Failed the first check; **passes** the revised one (`p0-spike-safari-2.txt`) |
| WebDriver's refresh (a hard reload in Firefox) shows the `#hash` section | pass | pass | pass (y 3,240, the heading at 80 px) |
| `?theme=jade` is applied in the first frame, with `document.write` | pass | pass | pass |
| `?theme=` survives the spy's URL writes and nav clicks | pass | pass | pass |
| Clicking "Quick start" ends on plain `/docs` with its heading on the scroll-padding line (revised 2026-11-02; it was "at y below 30") | pass (y 10, the heading at 100 px) | pass (y 10, the heading at 100 px) | plain `/docs?theme=jade&method=write`, the right title, the heading at its 80 px scroll padding, so y 30. Failed the first check's cutoff; **passes** the revised one (`p0-spike-safari-2.txt`) |

How each method of adding the theme stylesheet fared, with the theme file served 300 ms late:

| Method | Chrome 158 | Firefox 160 | Safari 27.2 |
|---|---|---|---|
| `createElement("link")` appended to `<head>` | after the first frame | after the first frame | before |
| the same with `blocking="render"` | before | after | before |
| `document.write` of the `<link>` | before | before | before |

## What the spike found

- **`scroll-behavior: smooth` on `<html>` (today's site) animates far too much in Chrome.**
  - Chrome animated the load-time jump to a deep link's `#hash` for about 1.2 s from the top of the page, with or without JavaScript. Sampled every 100 ms, the heading moved from 7,899 px away to 100 px.
  - It animated back and forward the same way.
  - The first round of checks failed on this until smooth scrolling became a class that `docs.js` sets only during a nav click.
- **Chrome and Firefox differ on back.** Going back to a `#hash` entry, Chrome scrolls to the hash's heading, while Firefox restores the exact position. Both are acceptable: Chrome lands at the start of the section the reader was in.
- **A theme stylesheet added by script arrives after the first frame.** Only parser-inserted `<link>`s are implicitly render-blocking. `blocking="render"` fixes it in Chrome only (and it is not Baseline). `document.write` fixes it in both browsers.
- **Safari 27.2 (Phase 0, 2026-11-01).**
  - It applies a theme stylesheet added by script before the first frame by every method, `append` included: with the theme served 300 ms late, the first frame came 10 ms after the theme's response ended and was already in the theme, and so was the first contentful paint. `document.write` stays the method, since it is the one that works in all three.
  - WebKit's history limit is 100 `replaceState` calls in 10 seconds: of 250 at once, call 101 and every later one threw a `SecurityError`. The spy's `try` kept it working (the nav kept following, no window errors), and 11.3 s later the URL was right again. A fast scroll through the page made 1 call, far under the limit.
  - Back to a `#hash` entry restores the exact position, as in Firefox. `location.reload()` does not: it returns to the `#hash` section's heading, at the scroll padding (80 px), as Chrome's back does. The reader lands at the start of the section they were in; the owner accepted this on 2026-11-02.
  - Back skips a history entry that a script's `element.click()` made, since it carries no user gesture: from the entry such a click pushed, back went two entries back. A reader's click is real input, and the checks now use WebDriver's element click (`click_nav`), which is too. The real `docs.js` must not push entries on its own.
  - Smooth scrolling animates only the nav click under the spike's class (deep link, back and forward jump), and `docs-smooth.html` animates the deep link too, so Safari needs the click-only class as Chrome does.
  - On a locked screen `requestAnimationFrame` never runs. The spike holds femto's Safari lock and runs only with the screen unlocked.
- **Hidden tabs throttle `requestAnimationFrame` and timers** to about once a second. In the desktop app's hidden browser pane the spy appeared to lag a full step behind; headless and foreground windows behave normally. The behavior checks must not run in a hidden or background tab.

## Round 1: section paths

The first round used `/docs/<path>` URLs: `pushState` on clicks, `replaceState` while scrolling, and a server that rewrote each path to the docs page with exact `_redirects` 200 rules. All 12 of its checks passed in both browsers, once two things were fixed:
- a fallback for Firefox's hard reload, which restores no position;
- `try` around `replaceState`, because WebKit throws past 100 calls in 10 seconds.

The round also found that on Cloudflare Pages a rewrite to `/docs.html` (rather than `/docs`) would 308 and lose the path (02 §4, rejected options).

The owner chose hashes over paths on 2026-10-30. With hashes, the browser itself handles the deep-link scrolling, `pushState`, the reload fallback and the rewrite rules that round 1 needed code for.

## Open for the real implementation

- **Scale.** Run these checks against the merged page, which is about 30 real sections plus code, live examples and 400 color swatches.
  - Measure the `scroll` handler's cost per frame. It walks the section list, which could become a binary search over cached tops.
  - Measure the time to a correct deep-link position on a cold load.
  - Measure layout shift while fonts load.
- **Safari.** Run against the merged page too, under the revised reload and Quick start checks. The JavaScript-off deep link runs only in Chrome, since WebDriver cannot turn JavaScript off in Safari.
- **Mobile.** Test widths below 1024 px: the off-canvas menu, the sticky breadcrumb showing the current category, and the scroll padding under the breadcrumb.
- **Reduced motion.** Under `prefers-reduced-motion: reduce`, nav clicks jump without animating.
- **Keyboard.** A fragment navigation moves the sequential focus starting point to the heading; check the Tab order after a nav click in each browser.
