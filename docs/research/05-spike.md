# 05 Spike: one page, URL following the scroll

## Verdict

The one-page mechanism the plan adopts works in Chrome Beta 158.0.8127.2 and Firefox 160.0, both headless. In that mechanism, the `#hash` follows the section being read and `?theme=` sets a theme color. All 13 checks pass in each browser, plus a deep-link check in Chrome with JavaScript off.

It needs about 130 lines of plain JavaScript, using only features that are Widely available by 2026-11-13. The browser's own fragment navigation does the rest: links, deep links, back, forward and reload. Safari has not run it yet; Phase 0 runs it under femto's rig rules.

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
| `test_spike.py` | Selenium 4.52.0 under `uv`, driving the rig's Chrome Beta and Firefox headless at 1280×800, plus Chrome with JavaScript off. |

To run it:

```sh
python3 -I docs/research/spike/make.py
python3 -I docs/research/spike/serve.py 8790 &
uv run docs/research/spike/test_spike.py 8790
```

## Results (round 2)

| Check | Chrome 158 | Firefox 160 |
|---|---|---|
| `/docs#input` lands on Input's heading, below the header, with the right nav link and title | pass | pass |
| The same with JavaScript off (the browser's own fragment scroll) | pass | not run |
| Scrolling into Grid writes `#grid` and the title "Grid • femto" | pass | pass |
| Scrolling back to the top leaves plain `/docs` and the page's own title | pass | pass |
| Scrolling to the very bottom makes the short last section current | pass | pass |
| A fast scroll from top to bottom (200 px every 16 ms) makes at most 3 `replaceState` calls and ends on `#tooltip` | pass | pass |
| A nav click pushes exactly one history entry, lands on the heading, and the nav never shows a section in between | pass | pass |
| Back returns to the previous entry, and the spy follows | pass (to the `#hash` heading) | pass (to the exact position) |
| Forward returns to the clicked section | pass | pass |
| `location.reload()` mid-section keeps the position | pass | pass |
| WebDriver's refresh (a hard reload in Firefox) shows the `#hash` section | pass | pass |
| `?theme=jade` is applied in the first frame, with `document.write` | pass | pass |
| `?theme=` survives the spy's URL writes and nav clicks | pass | pass |
| Clicking "Quick start" ends on plain `/docs` | pass | pass |

How each method of adding the theme stylesheet fared, with the theme file served 300 ms late:

| Method | Chrome 158 | Firefox 160 |
|---|---|---|
| `createElement("link")` appended to `<head>` | after the first frame | after the first frame |
| the same with `blocking="render"` | before | after |
| `document.write` of the `<link>` | before | before |

## What the spike found

- **`scroll-behavior: smooth` on `<html>` (today's site) animates far too much in Chrome.**
  - Chrome animated the load-time jump to a deep link's `#hash` for about 1.2 s from the top of the page, with or without JavaScript. Sampled every 100 ms, the heading moved from 7,899 px away to 100 px.
  - It animated back and forward the same way.
  - The first round of checks failed on this until smooth scrolling became a class that `docs.js` sets only during a nav click.
- **Chrome and Firefox differ on back.** Going back to a `#hash` entry, Chrome scrolls to the hash's heading, while Firefox restores the exact position. Both are acceptable: Chrome lands at the start of the section the reader was in.
- **A theme stylesheet added by script arrives after the first frame.** Only parser-inserted `<link>`s are implicitly render-blocking. `blocking="render"` fixes it in Chrome only (and it is not Baseline). `document.write` fixes it in both browsers.
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
- **Safari.** Run every check under femto's rig rules: Safari quit first, machine idle, then a light pass and the owner's dark pass. Safari's handling of `document.write` and of back to a `#hash` entry is still unknown.
- **Mobile.** Test widths below 1024 px: the off-canvas menu, the sticky breadcrumb showing the current category, and the scroll padding under the breadcrumb.
- **Reduced motion.** Under `prefers-reduced-motion: reduce`, nav clicks jump without animating.
- **Keyboard.** A fragment navigation moves the sequential focus starting point to the heading; check the Tab order after a nav click in each browser.
