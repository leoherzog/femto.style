"""Components: Modal's demo modal and its static examples, Nav's example links, Progress' examples
(the Remix site's ModalContext with docs.modal.jsx, docs.nav.jsx and docs.progress.jsx), and
Tooltip's example link. Progress' examples are plain markup since 2026-11-09: the example's value is
25 in the HTML, where docs.js once drew a random one every 5 s behind a pause button.

The Tooltip example's link is a plain <a> that points at its section, /docs#tooltip, so a click is a
fragment navigation in the same document to the section's heading."""
from behavior import HEADING_LINE, check, self_href

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
    """Modal's demo: "Open modal" (`button[data-modal-open=modal-demo]`) opens the demo dialog (the `main
    dialog` without class example: "Confirm your membership", in sentence case); once its opening
    animation ends, its
    Cancel and Confirm buttons close it, a click on the dialog outside its article (the backdrop)
    closes it, and a click inside the article does not. The two always-open example dialogs
    (`dialog.example`) stay open throughout, and their own buttons (the first's Close, the second's
    Cancel and Confirm) change nothing: no dialog closes, the URL stays."""
    url = page.url()
    title = "Confirm your membership"
    expect_demo(page, False, "on load")
    for how in ("Cancel", "Confirm", "backdrop"):
        page.click("button[data-modal-open=modal-demo]")
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


# Progress' two examples: each one's <progress> (its value and max attributes, its position, and
# its box beside its article's content box) and the code sample under it.
PROGRESS = """
return ["Progress example", "Indeterminate progress example"].map(label => {
  const art = S.querySelector(`article[aria-label="${label}"]`), p = art && art.querySelector(":scope > progress");
  if (!p) return {label, missing: true};
  const r = p.getBoundingClientRect(), cs = getComputedStyle(art), a = art.getBoundingClientRect();
  const content = a.width - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
  return {label, value: p.getAttribute("value"), max: p.getAttribute("max"), position: p.position,
          height: r.height, width: Math.round(r.width), content: Math.round(content), shown: getComputedStyle(p).display !== "none",
          code: art.querySelector(":scope > footer pre code").textContent};
});
"""


@check("progress-examples", "/docs#progress")
def progress_examples(page):
    """Progress' examples render femto's bar from their markup alone. The first
    (`article[aria-label="Progress example"] > progress`) is determinate, value="25" max="100"
    (position 0.25), and its code sample reads <progress value="25" max="100"></progress>; the
    second (`article[aria-label="Indeterminate progress example"] > progress`) has no value
    (position -1) and its sample reads <progress></progress>. Each bar is displayed, at least 1 px
    tall and as wide as its article's content box (within 1 px). After 1 s the first still reads 25:
    nothing redraws it."""
    first, second = page.js(PROGRESS)
    for r in (first, second):
        page.expect(f"{r['label']}: it has a <progress>", not r.get("missing"))
        page.expect(f"{r['label']}: the bar is displayed, at least 1 px tall, as wide as the article's content",
                    r["shown"] and r["height"] >= 1 and abs(r["width"] - r["content"]) <= 1, **r)
    page.eq("the example's value, max and position", [first["value"], first["max"], first["position"]], ["25", "100", 0.25])
    page.eq("its sample", first["code"], '<progress value="25" max="100"></progress>')
    page.eq("the indeterminate example has no value (position -1)", [second["value"], second["position"]], [None, -1])
    page.eq("its sample", second["code"], "<progress></progress>")
    page.sleep(1)
    page.eq("1 s later the value is still 25", page.js(PROGRESS)[0]["value"], "25")


# Nav's example links, in document order: those of every nav inside an example (each of the
# section's articles is one). Each comes with its dropdown's summary (or null), its text, its
# example's label and the index of its nav.
NAV_LINKS = """
const navs = [];
return [...S.querySelectorAll('#content article nav a')].map(a => {
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
    """Every example link of Nav (those inside the examples' navs, dropdown items included: 22,
    since the 2026-11-07 cleanup moved the nav dropdown example's 5 links to Dropdown alone and
    2026-11-09 dropped the buttons example's "Services", so it fits 320 px; each
    href="#", as its sample has it) goes nowhere. A real click on each (its dropdown opened
    first with a click on the summary), and Enter on the first link of each nav outside a dropdown,
    leave the document (a marker set on window survives), the URL, history.length and the scroll
    position as they were, keep the dropdown open, and the click event is canceled
    (defaultPrevented)."""
    links = page.js(NAV_LINKS)
    want = 22
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
    own place, /docs#tooltip: with the page scrolled so the link is in view (scrollY over 50 past
    where the deep link put it), a real click is a fragment navigation in the same document (a marker
    set on window survives): it ends at /docs#tooltip with no new history entry (the URL was already the section's, or the spy's
    replaceState had made it another section's and the click pushes one) and Tooltip's heading on the
    scroll-padding line (within 2 px; at the page's end where the page cannot scroll so far)."""
    link = page.find(TOOLTIP_LINK)
    page.expect("the link points at the route itself", self_href(page, link, section_only=True),
                href=page.js("return arguments[0].getAttribute('href')", link))
    start = page.js("return Math.round(scrollY)")
    # The link just below the fixed header, so the page is scrolled as far as the link allows.
    page.scroll_to(page.js("""const header = document.querySelector('body > header');
      return Math.round(arguments[0].getBoundingClientRect().top + scrollY
                        - Math.max(header ? header.getBoundingClientRect().bottom : 0, 0) - 24);""", link))
    before = page.js(INTO_VIEW, link)
    page.expect("scrolled down before the click", before - start > 50, scroll=before, start=start)
    history = page.js("window.__bhMarker = 'kept'; return history.length")
    url = page.url()
    page.click(link, scroll=False)
    page.wait("at /docs#tooltip", "location.pathname + location.search + location.hash === '/docs#tooltip'", 3, url_before=url)
    page.wait("Tooltip's heading is on the scroll-padding line", f"Math.abs(({HEADING_LINE})('tooltip')) <= 2", 3,
              offset=page.js(f"return ({HEADING_LINE})('tooltip')"))
    page.eq("the same document", page.js("return window.__bhMarker || null"), "kept")
    page.eq("a new history entry only for a new URL", page.js("return history.length"),
            history + (url != "/docs#tooltip"), url_before=url)


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


@check("tooltip-link-same-hash", SAME_HASH, height=700)
def tooltip_link_same_hash(page):
    """On /docs?theme=jade#tooltip at 1300 x 700, scrolled past where the deep link put Tooltip's
    heading as far as the example link allows (the link 24 px below the fixed header, and the
    heading at least 50 px past its line; a fixed 200 px put the link under the header once the
    header grew, 2026-11-11), with the URL still /docs?theme=jade#tooltip once the spy has settled,
    a real click on the example link (`href="/docs#tooltip"`: the URL's own hash, without its query) is
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
    # The link just below the fixed header, so the page is scrolled past the heading as far as the
    # link allows: how far depends on the header's height and the text above the link.
    y = page.scroll_to(page.js("""const header = document.querySelector('body > header');
      return Math.round(arguments[0].getBoundingClientRect().top + scrollY
                        - Math.max(header ? header.getBoundingClientRect().bottom : 0, 0) - 24);""", link))
    page.sleep(0.5)   # past the spy's URL_DELAY (200 ms): a hash it would write is written
    offset = page.js(f"return ({HEADING_LINE})('tooltip')")
    page.expect("scrolled at least 50 px past the heading's line", offset <= -50, offset=offset, y=y)
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
