"""Components: Modal's demo modal and its static examples, Nav's example links and Progress' random
value (01 §2, ModalContext with docs.modal.jsx; small widgets: docs.nav.jsx, docs.progress.jsx), and
Tooltip's example link. Phase 6 added Progress' pause button and its paused start under reduced
motion (WCAG 2.2.2), which the oracle lacks: progress-pause and progress-reduced-motion hold them on
the one page only, as tooltip-link-same-hash holds the one page's ?theme= URL.

The Tooltip example's link (docs.tooltip.jsx: Link to="#" with no onClick) renders the route's own
path, href="/docs/tooltip". In the oracle a click is a client-side navigation to the same URL: the
document is kept and the router scrolls to the top. The static site keeps it a plain <a> (PLAN.md
Conversion rules, Markup), so on routes the same click loads the page again. The end state is the
same (the same URL, no new history entry, the top of the page), and tooltip-link holds both sides to
it, but the two are not the same behavior: the static click is a full load. Do not cancel the click
to hide the load, which would also drop the scroll to the top. On the one page the link points at
the section, /docs#tooltip, and a click is a fragment navigation in the same document to the
section's heading."""
from behavior import HEADING_LINE, check, expect_name, self_href

GROUP = "components-b"

DIALOGS = """
const ds = [...S.querySelectorAll("main dialog")];
return {demo: ds.filter(d => !d.classList.contains("example")).map(d => d.open),
        examples: ds.filter(d => d.classList.contains("example")).map(d => d.open),
        classes: [...document.documentElement.classList].filter(c => c.startsWith("modal-is-")).sort().join(" "),
        url: location.pathname + location.search + location.hash};
"""
DEMO = "main dialog:not(.example)"


def expect_demo(page, open_, label):
    if open_:
        page.wait(f"{label}: the demo dialog is open", f"S.querySelector('{DEMO}').open", 1)
    else:
        page.wait(f"{label}: the demo dialog is closed", f"!S.querySelector('{DEMO}').open && "
                  "![...document.documentElement.classList].some(c => c.startsWith('modal-is-'))", 1.5)
    s = page.js(DIALOGS)
    page.eq(f"{label}: one demo dialog", len(s["demo"]), 1)
    page.eq(f"{label}: the two examples stay open", s["examples"], [True, True])
    return s


@check("modal-demo", "/docs#modal")
def modal_demo(page):
    """Modal's demo: "Open modal" (`#modal-demo button`) opens the demo dialog (the `main
    dialog` without class example: "Confirm your membership", in sentence case from Phase 4; on
    routes the oracle's "Confirm Your Membership"); once its opening animation ends, its
    Cancel and Confirm buttons close it, a click on the dialog outside its article (the backdrop)
    closes it, and a click inside the article does not. The two always-open example dialogs
    (`dialog.example`) stay open throughout, and their own buttons (the first's Close, the second's
    Cancel and Confirm) change nothing: no dialog closes, the URL stays."""
    url = page.url()
    title = "Confirm Your Membership" if page.layout == "routes" else "Confirm your membership"
    expect_demo(page, False, "on load")
    for how in ("Cancel", "Confirm", "backdrop"):
        page.click("#modal-demo button")
        expect_demo(page, True, f"before {how}")
        # femto's opening animation moves the article: after a 0.2 s delay it slides in from
        # translateY(-100%) over 0.2 s, and site.js drops modal-is-opening at 400 ms, which ends the
        # animation wherever it is (in headless Firefox well short of its end, so the article jumps).
        # A point sampled before that, aimed inside the article, can land on the backdrop by the
        # time the click arrives, and the backdrop closes the dialog. So every click below waits.
        page.wait(f"before {how}: the opening ends",
                  "!document.documentElement.classList.contains('modal-is-opening')", 1)
        page.eq(f"before {how}: the demo is {title!r}",
                page.js(f"return S.querySelector('{DEMO}').querySelector('h2').textContent.replace('#', '').trim()"),
                title)
        if how == "backdrop":
            page.click(page.find(f"{DEMO} > article > p"))
            page.sleep(0.6)
            expect_demo(page, True, "a click inside the article keeps it open")
            pt = page.js(f"""const d = S.querySelector("{DEMO}"), a = d.querySelector(":scope > article").getBoundingClientRect();
              for (const [x, y] of [[8, innerHeight / 2], [innerWidth - 8, innerHeight / 2], [innerWidth / 2, 8], [innerWidth / 2, innerHeight - 8]]) {{
                const inA = x >= a.left && x <= a.right && y >= a.top && y <= a.bottom;
                if (!inA && document.elementFromPoint(x, y) === d) return [Math.round(x), Math.round(y)]; }}
              return null;""")
            page.expect("a point on the dialog outside its article", pt is not None)
            page.click_at(*pt)
        else:
            button = page.js(f"return [...S.querySelectorAll('{DEMO} footer button')].find(b => b.textContent.trim() === arguments[0])", how)
            page.click(button)
        expect_demo(page, False, f"{how} closes it")
    page.url_kept("the URL is unchanged", url)
    for sel, text in (("dialog.example:nth-of-type(1) header button[aria-label=Close]", None),
                      ("dialog.example footer button", "Cancel"), ("dialog.example footer button", "Confirm")):
        el = page.js("return [...S.querySelectorAll(arguments[0])].find(b => !arguments[1] || b.textContent.trim() === arguments[1])",
                     sel, text)
        page.expect(f"example button {text or 'Close'} exists", el is not None)
        page.click(el)
        page.sleep(0.5)
        s = page.js(DIALOGS)
        page.eq(f"example {text or 'Close'}: the examples stay open", s["examples"], [True, True])
        page.eq(f"example {text or 'Close'}: the demo stays closed", s["demo"], [False])
        page.eq(f"example {text or 'Close'}: no modal class", s["classes"], "")
        page.url_kept(f"example {text or 'Close'}: the URL stays", url)


# Records every change of the example's progress value (and the code token that prints it) while
# the check waits, with performance.now() times.
PROGRESS = """
const p = S.querySelector('article[aria-label="Progress example"] > progress');
const code = p.parentElement.querySelector("footer pre code");
p.scrollIntoView({block: "center"});
window.__bhProgress = [];
const value = () => [Math.round(performance.now()), p.getAttribute("value"), p.getAttribute("max"),
  (code.textContent.match(/value="([^"]*)"/) || [])[1], code.textContent];
__bhProgress.push(value());
new MutationObserver(() => __bhProgress.push(value())).observe(p, {attributes: true, attributeFilter: ["value"]});
return __bhProgress[0];
"""


@check("progress-value", "/docs#progress")
def progress_value(page):
    """Progress' example (`article[aria-label="Progress example"] > progress`, kept on screen)
    shows a random integer value from 5 to 94 with max="100", and its code sample reads
    <progress value="N" max="100"></progress> with the same N (from Phase 4, valid HTML; the
    oracle's JSX-style <progress value="N" max="100" /> on routes). Watched for 16 s, the value changes at least
    twice; every change is a whole number of 5 s periods after the previous one (within 400 ms),
    every value stays in 5 to 94, and the sample always matches it."""
    first = page.js(PROGRESS)
    page.eq("max is 100", first[2], "100")
    page.sleep(16)
    log = page.js("return window.__bhProgress")
    page.note(f"values: {[x[1] for x in log]}")
    for t, v, mx, code_v, code in log:
        page.expect(f"value {v} is an integer from 5 to 94", v is not None and v.isdigit() and 5 <= int(v) <= 94, value=v)
        page.eq(f"the sample prints {v}", code, f'<progress value="{v}" max="100" />' if page.layout == "routes"
                else f'<progress value="{v}" max="100"></progress>')
    page.expect("the value changed at least twice in 16 s", len(log) >= 3, changes=len(log) - 1, log=[x[:2] for x in log])
    for (t0, *_), (t1, *_) in zip(log[1:], log[2:]):
        gap = t1 - t0
        k = round(gap / 5000)
        page.expect(f"changes {gap} ms apart: a whole number of 5 s periods", k >= 1 and abs(gap - 5000 * k) <= 400, gap=gap)


# The example's place relative to the viewport: "below", "above" or "on" (any overlap).
WHERE = """
const r = S.querySelector('article[aria-label="Progress example"] > progress').getBoundingClientRect();
return r.top >= innerHeight ? "below" : r.bottom <= 0 ? "above" : "on";
"""

# Records every change of the example's value (and the value its code sample prints) from now on,
# with performance.now() times; returns the time it started. A later call starts a new record and
# stops the earlier observer, so no change is recorded twice.
WATCH = """
const p = S.querySelector('article[aria-label="Progress example"] > progress');
const code = p.parentElement.querySelector("footer pre code");
window.__bhProgressObserver?.disconnect();
window.__bhProgress = [];
window.__bhProgressObserver = new MutationObserver(() => __bhProgress.push([Math.round(performance.now()), p.getAttribute("value"),
  (code.textContent.match(/value="([^"]*)"/) || [])[1]]));
window.__bhProgressObserver.observe(p, {attributes: true, attributeFilter: ["value"]});
return Math.round(performance.now());
"""


@check("progress-offscreen", "/docs#progress", height=300, oracle_bug={
    "fails": "no change for 10.5 s while the example is below the viewport",
    "reason": "the oracle's interval (docs.progress.jsx, setInterval in a useEffect) draws a new value "
              "every 5 s whether or not the example is on screen; PLAN.md Conversion rules: intervals "
              "run only while their element is on screen"})
def progress_offscreen(page):
    """Progress at 1300 x 300, scrolled to the top of the page, where the example's progress bar
    (`article[aria-label="Progress example"] > progress`) is below the viewport: its value does not change for 10.5 s while it
    is below the viewport; scrolled on screen, it changes 5 s later and again 5 s after that (within
    400 ms; 10 s when a draw repeated the value, 1 in 90), each value a whole number from 5 to 94
    that the code sample prints too; scrolled to the page's end, where the bar is above the
    viewport, it does not change for 10.5 s. The interval runs only while the example is on screen
    (PLAN.md Conversion rules)."""
    page.scroll_to(0)
    page.eq("the example starts below the viewport", page.js(WHERE), "below")
    page.js(WATCH)
    page.sleep(10.5)
    log = page.js("return window.__bhProgress")
    page.eq("no change for 10.5 s while the example is below the viewport", log, [])

    on = page.js("""S.querySelector('article[aria-label="Progress example"] > progress')
                      .scrollIntoView({block: "center", behavior: "instant"});
                    return Math.round(performance.now());""")
    page.eq("scrolled, the example is on screen", page.js(WHERE), "on")
    # A draw can repeat the value it replaces (1 in 90), which changes nothing; the next draw, 5 s
    # later, then shows. So each change is 1 or 2 periods of 5 s after the last.
    page.wait("a change within 10.4 s of coming on screen", "window.__bhProgress.length >= 1", 10.6)
    page.wait("a second change", "window.__bhProgress.length >= 2", 10.6)
    log = page.js("return window.__bhProgress")
    page.note(f"on screen: changes at {[t - on for t, *_ in log]} ms, values {[v for _, v, _ in log]}")
    first, gap = log[0][0] - on, log[1][0] - log[0][0]
    for label, ms in (("the first change is 5 s after coming on screen", first), ("the second change is 5 s after the first", gap)):
        k = round(ms / 5000)
        page.expect(f"{label}, or 10 s when a draw repeated the value (within 400 ms)",
                    k in (1, 2) and abs(ms - 5000 * k) <= 400, ms=ms)
    for _, v, code_v in log:
        page.expect(f"value {v} is an integer from 5 to 94", v is not None and v.isdigit() and 5 <= int(v) <= 94, value=v)
        page.eq(f"the sample prints {v}", code_v, v)

    page.scroll_to(page.js("return document.documentElement.scrollHeight"))
    page.eq("at the page's end, the example is above the viewport", page.js(WHERE), "above")
    page.sleep(0.3)
    page.js(WATCH)
    page.sleep(10.5)
    page.eq("no change for 10.5 s while the example is above the viewport", page.js("return window.__bhProgress"), [])


# The Progress example's pause button (docs.js, Phase 6: WCAG 2.2.2, the redraw every 5 s is
# auto-updating content), as the homepage demo's button[data-demo-pause] (landing.py).
PROGRESS_PAUSE = "button[data-progress-pause]"
PROGRESS_PAUSE_WHY = ("the Progress example's pause button and its paused start under reduced motion are new in Phase 6 "
                      "(WCAG 2.2.2, Pause, Stop, Hide); the oracle's example has neither")
PROGRESS_PAUSE_STATE = """
const b = S.querySelector(arguments[0]);
return b && {hidden: b.hidden, shown: b.getClientRects().length > 0 && getComputedStyle(b).visibility !== "hidden",
             type: b.getAttribute("type"), text: b.textContent.trim(), pressed: b.getAttribute("aria-pressed"),
             label: b.getAttribute("aria-label")};
"""
# Records each click on the pause button, with its performance.now() time (after docs.js's own
# listener, which was added first, has run).
PROGRESS_CLICKS = """
const b = S.querySelector(arguments[0]);
window.__bhPauseClicks = [];
b.addEventListener("click", () => __bhPauseClicks.push(Math.round(performance.now())));
"""
# The example scrolled to the middle of the viewport, so it stays on screen while the check watches.
PROGRESS_CENTER = """
S.querySelector('article[aria-label="Progress example"] > progress').scrollIntoView({block: "center", behavior: "instant"});
"""


def expect_progress_button(page, label, text):
    """The pause button reads `text` (within 1 s), its computed name is the same text, and the bar
    is on screen."""
    page.wait(f"{label}: the button reads {text}", "S.querySelector(arguments[0]).textContent.trim() === arguments[1]", 1,
              args=(PROGRESS_PAUSE, text))
    expect_name(page, f"{label}: the button's computed name is {text}", page.find(PROGRESS_PAUSE), text)
    page.eq(f"{label}: the example is on screen", page.js(WHERE), "on")


def expect_values(page, log):
    for _, v, code_v in log:
        page.expect(f"value {v} is an integer from 5 to 94", v is not None and v.isdigit() and 5 <= int(v) <= 94, value=v)
        page.eq(f"the sample prints {v}", code_v, v)


def expect_play(page, label):
    """A click on the button (reading Play) relabels it Pause, and the value changes 5 s after the
    click, or 10 s when that draw repeated the value (within 400 ms), as the 5 s interval starts
    again from the click."""
    page.js(WATCH)
    page.click(page.find(PROGRESS_PAUSE))
    expect_progress_button(page, f"{label}: Play clicked", "Pause")
    page.wait(f"{label}: a change within 10.4 s of Play", "window.__bhProgress.length >= 1", 10.6)
    log = page.js("return window.__bhProgress")
    clicked = page.js("return window.__bhPauseClicks.at(-1)")
    ms = log[0][0] - clicked
    page.note(f"{label}: the first change {ms} ms after Play, value {log[0][1]}")
    k = round(ms / 5000)
    page.expect(f"{label}: the first change is 5 s after Play, or 10 s when a draw repeated the value (within 400 ms)",
                k in (1, 2) and abs(ms - 5000 * k) <= 400, ms=ms)
    expect_values(page, log)


@check("progress-pause", "/docs#progress", layouts=("one-page",), layout_reason=PROGRESS_PAUSE_WHY)
def progress_pause(page):
    """The Progress example's `button[data-progress-pause]` (in its section, before the example),
    hidden in the markup (nothing changes without JavaScript), is shown once docs.js runs: rendered,
    type="button", reading "Pause", with no aria-pressed and no aria-label, its computed name the same
    text. With the example kept on screen its value changes within 10.4 s (the 5 s redraw, or 10 s
    when a draw repeated the value). A click relabels the button "Play" (its computed name too) and
    stops the redraw: no change for 10.5 s. A second click relabels it "Pause" and resumes it: the
    value changes 5 s after that click, or 10 s when that draw repeated the value (within 400 ms),
    each value a whole number from 5 to 94 that the code sample prints too."""
    s = page.js(PROGRESS_PAUSE_STATE, PROGRESS_PAUSE)
    page.expect("the Progress section has a pause button", s is not None)
    page.eq("the script shows it: not hidden, rendered, type=button, reading Pause, no aria-pressed or aria-label",
            [s["hidden"], s["shown"], s["type"], s["text"], s["pressed"], s["label"]],
            [False, True, "button", "Pause", None, None])
    page.js(PROGRESS_CENTER)
    page.js(PROGRESS_CLICKS, PROGRESS_PAUSE)
    expect_progress_button(page, "playing", "Pause")
    page.js(WATCH)
    page.wait("playing: the value changes within 10.4 s", "window.__bhProgress.length >= 1", 10.6)
    expect_values(page, page.js("return window.__bhProgress"))
    page.click(page.find(PROGRESS_PAUSE))
    expect_progress_button(page, "Pause clicked", "Play")
    page.js(WATCH)   # record from here
    page.sleep(10.5)
    page.eq("paused: no change for 10.5 s", page.js("return window.__bhProgress"), [])
    expect_progress_button(page, "still paused", "Play")
    expect_play(page, "resumed")


@check("progress-reduced-motion", "/docs#progress", motion="reduce", layouts=("one-page",), layout_reason=PROGRESS_PAUSE_WHY)
def progress_reduced_motion(page):
    """Under prefers-reduced-motion: reduce the Progress example starts paused: once docs.js runs,
    its `button[data-progress-pause]` is shown reading "Play" (its computed name too), the value drawn
    on load is a whole number from 5 to 94 that the code sample prints, and with the example kept on
    screen the value does not change for 10.5 s. A click on Play relabels the button "Pause", and the
    value changes 5 s after the click, or 10 s when that draw repeated the value (within 400 ms): the
    reader can still start it."""
    s = page.js(PROGRESS_PAUSE_STATE, PROGRESS_PAUSE)
    page.expect("the Progress section has a pause button", s is not None)
    page.eq("the script shows it reading Play", [s["hidden"], s["shown"], s["type"], s["text"]], [False, True, "button", "Play"])
    page.js(PROGRESS_CENTER)
    page.js(PROGRESS_CLICKS, PROGRESS_PAUSE)
    expect_progress_button(page, "reduced motion", "Play")
    first = page.js("""const p = S.querySelector('article[aria-label="Progress example"] > progress');
      return [0, p.getAttribute("value"), (p.parentElement.querySelector("footer pre code").textContent.match(/value="([^"]*)"/) || [])[1]];""")
    expect_values(page, [first])
    page.js(WATCH)
    page.sleep(10.5)
    page.eq("paused from the start: no change for 10.5 s", page.js("return window.__bhProgress"), [])
    expect_play(page, "started")


# /docs/nav's example links, in document order: on routes those of the nav[aria-label=overflow-with-focus]
# that the oracle's route puts first in <main> (a hydration leftover that Phase 4 removed from the
# section), then those of every nav inside an example (article.component): 31 on routes, 28 on the
# one page. Each comes with its dropdown's summary (or null), its text, its example's label and the
# index of its nav.
NAV_LINKS = """
const navs = [];
return [...S.querySelectorAll('main nav[aria-label="overflow-with-focus"] a, #content article.component nav a')].map(a => {
  const details = a.closest("details"), article = a.closest("article"), nav = a.closest("nav");
  if (!navs.includes(nav)) navs.push(nav);
  return [a, details && details.querySelector(":scope > summary"), a.textContent.trim() || a.getAttribute("aria-label"),
          article ? article.getAttribute("aria-label") : "main > nav", navs.indexOf(nav)];
});
"""

# Every click event, in the capture phase, records whether it was canceled once its dispatch is
# over; a marker on window shows that the document was not replaced.
CLICK_SPY = """
window.__bhClicks = [];
addEventListener("click", (e) => { const a = e.target.closest && e.target.closest("a");
  if (a) setTimeout(() => __bhClicks.push(e.defaultPrevented), 0); }, true);
window.__bhMarker = "kept";
"""

LINK_STATE = """
const [summary] = arguments;
return {marker: window.__bhMarker, url: location.pathname + location.search + location.hash,
        history: history.length, scroll: Math.round(scrollY), clicks: window.__bhClicks.splice(0),
        open: summary ? summary.parentElement.open : null};
"""

# Brings the element into view, clear of the fixed header, unless it already is; returns scrollY.
INTO_VIEW = """
const el = arguments[0], r = el.getBoundingClientRect();
const header = document.querySelector("body > header"), h = header ? header.getBoundingClientRect().bottom : 0;
if (r.top < Math.max(h, 0) + 8 || r.bottom > innerHeight - 8) el.scrollIntoView({block: "center", behavior: "instant"});
return Math.round(scrollY);
"""


@check("nav-example-links", "/docs#nav")
def nav_example_links(page):
    """Every example link of Nav (the 28 inside the examples' navs, dropdown items included, and on
    routes also the 3 of the oracle's nav[aria-label=overflow-with-focus] first in <main>, which
    Phase 4 removed from the section: 28 links on the one page, 31 on routes, each pointing at its
    own place: href="/docs/nav" on routes, /docs or /docs#nav on the one page) goes nowhere. A real click on each (its dropdown opened
    first with a click on the summary), and Enter on the first link of each nav outside a dropdown,
    leave the document (a marker set on window survives), the URL, history.length and the scroll
    position as they were, keep the dropdown open, and the click event is canceled
    (defaultPrevented)."""
    links = page.js(NAV_LINKS)
    want = 31 if page.layout == "routes" else 28
    page.eq(f"{want} example links", len(links), want, labels=[f"{x[3]}: {x[2]}" for x in links])
    page.expect("every example link points at the route itself", all(self_href(page, x[0]) for x in links))
    page.js(CLICK_SPY)
    url, history = page.url(), page.js("return history.length")

    def goes_nowhere(label, summary, before):
        page.sleep(0.3)
        try:
            st = page.js(LINK_STATE, summary)
        except Exception as e:   # the document went away: the link navigated
            page.expect(label, False, error=f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        page.expect(label, st["marker"] == "kept" and st["history"] == history
                    and st["scroll"] == before and st["clicks"] == [True] and st["open"] in (True, None),
                    url_before=url, history_before=history, scroll_before=before, **st)
        page.url_kept(label, url)

    clicked, summary = 0, None
    for link, owner, text, example, _ in links:
        if owner is not summary:
            if summary is not None:
                page.click(summary)
            summary = owner
            if summary is not None:
                page.click(summary)
                page.wait(f"{example}: the dropdown opens", "arguments[0].parentElement.open", 1, args=(summary,))
        before = page.js(INTO_VIEW, link)
        page.click(link, scroll=False)
        goes_nowhere(f"{example}: a click on {text!r} goes nowhere", summary, before)
        clicked += 1
    if summary is not None:
        page.click(summary)
    page.eq("every example link was clicked", clicked, want)

    entered, seen = 0, set()
    for link, owner, text, example, nav in links:
        if owner is not None or nav in seen:
            continue
        seen.add(nav)
        page.js(INTO_VIEW, link)
        page.eq(f"{example}: {text!r} takes focus",
                page.js("arguments[0].focus(); return document.activeElement === arguments[0]", link), True)
        before = page.js("return Math.round(scrollY)")
        page.key("ENTER")
        goes_nowhere(f"{example}: Enter on {text!r} goes nowhere", None, before)
        entered += 1
    page.note(f"{clicked} example links clicked and Enter on the first link of {entered} navs: every click canceled, nothing navigated")


TOOLTIP_LINK = 'article[aria-label="Tooltip example"] a[data-tooltip]'


@check("tooltip-link", "/docs#tooltip", height=500)
def tooltip_link(page):
    """Tooltip's example link (`article[aria-label="Tooltip example"] a[data-tooltip]`) goes to its
    own place. On routes it has href="/docs/tooltip": with the page scrolled so the link is in view
    (scrollY over 50 past where the route starts), a real click ends, within 10 s, at /docs/tooltip
    with no search or hash, history.length as it was and scrollY 0. Whether the document was kept
    (the oracle's client-side navigation) or loaded again (the static site's plain link) is noted,
    not asserted (this module's docstring). On the one page it points at /docs#tooltip, and the same
    click is a fragment navigation in the same document (a marker set on window survives): it ends at
    /docs#tooltip with no new history entry (the URL was already the section's, or the spy's
    replaceState had made it another section's and the click pushes one) and Tooltip's heading on the
    scroll-padding line (within 2 px; at the page's end where the page cannot scroll so far)."""
    link = page.find(TOOLTIP_LINK)
    page.expect("the link points at the route itself", self_href(page, link, section_only=True),
                href=page.js("return arguments[0].getAttribute('href')", link))
    start = 0 if page.layout == "routes" else page.js("return Math.round(scrollY)")
    # The link just below the fixed header, so the page is scrolled as far as the link allows.
    page.scroll_to(page.js("""const header = document.querySelector('body > header');
      return Math.round(arguments[0].getBoundingClientRect().top + scrollY
                        - Math.max(header ? header.getBoundingClientRect().bottom : 0, 0) - 24);""", link))
    before = page.js(INTO_VIEW, link)
    page.expect("scrolled down before the click", before - start > 50, scroll=before, start=start)
    history = page.js("window.__bhMarker = 'kept'; return history.length")
    url = page.url()
    page.click(link, scroll=False)
    if page.layout == "one-page":
        page.wait("at /docs#tooltip", "location.pathname + location.search + location.hash === '/docs#tooltip'", 3, url_before=url)
        page.wait("Tooltip's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('tooltip')) <= 2", 3,
                  offset=page.js(f"return ({HEADING_LINE})('tooltip')"))
        page.eq("the same document", page.js("return window.__bhMarker || null"), "kept")
        page.eq("a new history entry only for a new URL", page.js("return history.length"),
                history + (url != "/docs#tooltip"), url_before=url)
        return
    page.wait("at the top of /docs/tooltip again",
              "location.pathname === '/docs/tooltip' && document.readyState === 'complete' && Math.round(scrollY) === 0 && "
              "(!window.__remixRouter || window.__remixRouter.state.navigation.state === 'idle')", 10)
    page.wait_ready()
    st = page.js("return {url: location.pathname + location.search + location.hash, history: history.length,"
                 "scroll: Math.round(scrollY), kept: window.__bhMarker === 'kept'}")
    page.eq("the URL is the route's own", st["url"], "/docs/tooltip")
    page.eq("no new history entry", st["history"], history)
    page.eq("at the top of the page", st["scroll"], 0)
    page.note(f"scrolled {before} px before the click; the document was {'kept' if st['kept'] else 'loaded again'}")


# Records, from now on, the time of every click (in the capture phase on window, before docs.js's
# own listener on document), of every scroll event, and of the first time <html> gains and then loses
# the class is-scrolling-to-link (docs.js, Decision 10), in performance.now() ms.
LINK_SCROLL = """
const html = document.documentElement, t = () => Math.round(performance.now());
window.__bhLink = {click: null, before: null, after: null, added: null, removed: null, scrolls: []};
// The click's own dispatch: the class before any handler (capture on window, first) and once every
// handler has run (bubble on window, last).
addEventListener("click", () => {
  __bhLink.click = t();
  __bhLink.before = html.classList.contains("is-scrolling-to-link");
}, true);
addEventListener("click", () => { __bhLink.after = html.classList.contains("is-scrolling-to-link"); });
addEventListener("scroll", () => __bhLink.scrolls.push(t()), {passive: true});
new MutationObserver(() => {
  const on = html.classList.contains("is-scrolling-to-link");
  if (on && __bhLink.added === null) __bhLink.added = t();
  if (!on && __bhLink.added !== null && __bhLink.removed === null) __bhLink.removed = t();
}).observe(html, {attributes: true, attributeFilter: ["class"]});
return true;
"""
SAME_HASH = "/docs?theme=jade#tooltip"


@check("tooltip-link-same-hash", SAME_HASH, height=700, layouts=("one-page",),
       layout_reason="?theme= exists only on the one page (Decision 8); no old route shows /docs?theme=jade#tooltip")
def tooltip_link_same_hash(page):
    """On /docs?theme=jade#tooltip at 1300 x 700, scrolled 200 px past where the deep link put
    Tooltip's heading (the URL still /docs?theme=jade#tooltip once the spy has settled), a real
    click on the example link (`href="/docs#tooltip"`: the URL's own hash, without its query) is
    the fragment navigation docs.js makes of it to keep the query, which runs although the hash is
    already the URL's (the hash setter would do nothing): within 3 s Tooltip's heading is on the
    scroll-padding line (within 2 px), the URL is still /docs?theme=jade#tooltip with
    history.length as it was, in the same document (a marker set on window survives) with jade's
    stylesheet kept. <html> gains is-scrolling-to-link from the click (absent as the click's dispatch
    begins, present once its handlers have run) and loses it when the scroll arrives: within 250 ms
    of the scroll's last event, not after SCROLL_STALL's 1 s without one, which ends a link's scroll
    that never arrives. The MutationObserver's time for the class can trail the click: its callback
    runs only after the handler, whose location.assign() Safari 27 spends about 160 ms in
    (p6-behavior-safari-light-2), so that time is reported, not judged."""
    link = page.find(TOOLTIP_LINK)
    page.eq("the link points at /docs#tooltip", page.js("return arguments[0].getAttribute('href')", link), "/docs#tooltip")
    page.wait("the deep link puts Tooltip's heading on its line", f"Math.abs(({HEADING_LINE})('tooltip')) <= 2", 3)
    y = page.scroll_to(page.js(f"return scrollY + ({HEADING_LINE})('tooltip') + 200"))
    page.sleep(0.5)   # past the spy's URL_DELAY (200 ms): a hash it would write is written
    offset = page.js(f"return ({HEADING_LINE})('tooltip')")
    page.expect("scrolled 200 px past the heading's line", abs(offset + 200) <= 2, offset=offset, y=y)
    url = page.url()
    page.eq("scrolled: the URL is still the deep link's", str(url), SAME_HASH)
    clear = page.js("""const r = arguments[0].getBoundingClientRect(), h = document.querySelector('body > header');
      const top = Math.max(h ? h.getBoundingClientRect().bottom : 0, 0);
      return {clear: r.top >= top && r.bottom <= innerHeight, top: r.top, header: top};""", link)
    page.expect("the link is in view, clear of the fixed header", clear["clear"], **clear)
    page.js("window.__bhMarker = 'kept'")
    page.js(LINK_SCROLL)
    page.click(link, scroll=False)
    page.wait("Tooltip's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('tooltip')) <= 2", 3,
              offset=page.js(f"return ({HEADING_LINE})('tooltip')"))
    page.wait("html loses is-scrolling-to-link", "window.__bhLink.removed !== null", 2, record=page.js("return window.__bhLink"))
    page.url_kept("the same URL, and no new history entry", url)
    page.eq("the URL is still /docs?theme=jade#tooltip", str(page.url()), SAME_HASH)
    page.eq("the same document", page.js("return window.__bhMarker || null"), "kept")
    page.eq("jade's stylesheet is kept", page.js("""return [...document.querySelectorAll("link[rel=stylesheet]")]
      .map(l => l.getAttribute("href")).filter(h => h.includes("/css/themes/")).map(h => h.replace(/^.*\\//, ""))"""), ["jade.css"])
    r = page.js("return window.__bhLink")
    after = [s for s in r["scrolls"] if s >= r["click"]]
    page.note(f"is-scrolling-to-link from {r['added'] - r['click']} to {r['removed'] - r['click']} ms after the click; "
              f"{len(after)} scroll events, the last {after[-1] - r['click'] if after else None} ms after it")
    page.expect("the click sets is-scrolling-to-link", r["before"] is False and r["after"] is True and r["added"] is not None, **r)
    page.expect("the page scrolls after the click", bool(after), **r)
    page.expect("is-scrolling-to-link goes within 250 ms of the scroll's last event", r["removed"] - after[-1] <= 250,
                ms_after_last_scroll=r["removed"] - after[-1], ms_after_click=r["removed"] - r["click"])
