"""Components, first half (accordion, card, dropdown, group, loading). Their examples are
native HTML: the accordions and dropdowns are <details>, the loading indicators are CSS, and the
group forms have method="dialog", which keeps their submits from going anywhere (shell's
example-forms covers Group). The one widget is the
Dropdown section's menu items: docs.dropdown.jsx's Item is a Link to="#" with an onClick that
prevents the default, so each renders the route's own path (href="/docs/dropdown"; on the one page
the page's, /docs, or the section's, /docs#dropdown) and goes nowhere, whether it is clicked or activated with Enter."""
from behavior import check, self_href

GROUP = "components-a"

# The example links of /docs/dropdown, in document order: every <a> inside an example (each of the
# section's articles is one) but the copy links of the code footers. That is the four Items of each of the
# link dropdowns and the nav example's "Services" Item (21 links in five dropdowns). Each link comes
# with the index of its dropdown's summary in `summaries` (-1 outside a dropdown), so a dropdown is told
# apart by its index, never by comparing the WebElements that two script calls return.
ITEMS = """
const summaries = [];
const items = [...S.querySelectorAll("#content article a:not([data-copy-link])")].map(a => {
  const details = a.closest("details");
  const summary = details ? details.querySelector(":scope > summary") : null;
  if (summary && !summaries.includes(summary)) summaries.push(summary);
  return [a, summary ? summaries.indexOf(summary) : -1, a.textContent,
          a.closest("article").getAttribute("aria-label")];
});
return [items, summaries, summaries.map(s => s.textContent)];
"""

# Every click event, in the capture phase, records whether it was canceled once its dispatch is
# over (Enter on a link dispatches one too); a marker on window shows that the document was not
# replaced.
CLICK_SPY = """
window.__bhClicks = [];
addEventListener("click", (e) => { const a = e.target.closest && e.target.closest("a");
  if (a) setTimeout(() => __bhClicks.push(e.defaultPrevented), 0); }, true);
window.__bhMarker = "kept";
"""

STATE = """
const [summary, link] = arguments;
return {marker: window.__bhMarker, url: location.pathname + location.search + location.hash,
        history: history.length, scroll: Math.round(scrollY), clicks: window.__bhClicks.splice(0),
        open: summary ? summary.parentElement.open : null, focused: document.activeElement === link};
"""

# Brings an element fully into view at once (the docs' CSS sets scroll-behavior: smooth, under which
# a focus or a Tab would scroll it in with an animation still running when the next step reads the
# scroll position).
INTO_VIEW = """
const [el] = arguments;
const r = el.getBoundingClientRect();
if (r.top < 0 || r.bottom > innerHeight) el.scrollIntoView({block: "center", behavior: "instant"});
"""

# Focuses an element, brought into view at once first.
FOCUS = INTO_VIEW + """
el.focus();
return document.activeElement === el;
"""

# The scroll position once it has held for three animation frames (at most about two seconds).
SETTLED = """
const frame = () => new Promise(res => requestAnimationFrame(() => res()));
let last = scrollY, same = 0;
for (let i = 0; i < 120 && same < 3; i++) { await frame(); same = scrollY === last ? same + 1 : 0; last = scrollY; }
return Math.round(scrollY);
"""


def _state(page, label, summary, link):
    try:
        return page.js(STATE, summary, link)
    except Exception as e:   # the document went away: the link navigated
        page.expect(label, False, error=f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")


@check("dropdown-items", "/docs#dropdown")
def dropdown_items(page):
    """Every example link of Dropdown (the four menu items of each link dropdown and the nav
    example's "Services": five dropdowns and 21 links since the 2026-11-07 cleanup dropped the
    six-dropdown button-variants gallery; each points at its own place, /docs or /docs#dropdown) goes nowhere,
    with the pointer and with the keyboard. Pointer: each dropdown is opened once with a click on its
    summary, then each of its items is clicked in turn inside that open dropdown, and the dropdown is
    closed with its summary again. Keyboard: each dropdown's summary is focused and Enter opens it,
    Tab moves focus to each of its items in turn and Enter activates it, and Enter on the focused
    summary closes it ("Services" is focused directly). After every click and every Enter on an
    item: the document is the same (a marker set on window survives), the URL, history.length and
    the scroll position are as they were, its dropdown is still open, and the click event was
    canceled (defaultPrevented); after an Enter, focus is still on the item."""
    items, summaries, names = page.js(ITEMS)
    want, dropdowns = 21, 5
    page.eq(f"{want} example links", len(items), want, labels=[f"{i[3]}: {i[2]}" for i in items])
    page.eq(f"{dropdowns} link dropdowns", len(summaries), dropdowns, summaries=names)
    page.expect("every example link points at the route itself", all(self_href(page, i[0]) for i in items))
    page.js(CLICK_SPY)
    url, history = page.url(), page.js("return history.length")

    # A dropdown is named by its example and its summary's text.
    examples = {owner: example for _, owner, _, example in items if owner >= 0}

    def where(owner, example=None):
        return f"{examples[owner]}, {names[owner]!r}" if owner >= 0 else example

    def nowhere(label, owner, link, before, keyboard):
        st = _state(page, label, summaries[owner] if owner >= 0 else None, link)
        page.expect(label, st["marker"] == "kept" and st["history"] == history
                    and st["scroll"] == before and st["clicks"] == [True] and st["open"] in (True, None)
                    and (st["focused"] or not keyboard),
                    url_before=url, history_before=history, scroll_before=before, **st)
        page.url_kept(label, url)

    # Pointer: open each dropdown once and click its items in turn.
    current, opened, clicked = -1, 0, 0
    for link, owner, text, example in items:
        if owner != current:
            if current >= 0:
                page.click(summaries[current])
                page.wait(f"{where(current)}: a click on its summary closes it",
                          "!arguments[0].parentElement.open", 1, args=(summaries[current],))
            current = owner
            if current >= 0:
                page.click(summaries[current])
                page.wait(f"{where(current)}: a click on its summary opens it",
                          "arguments[0].parentElement.open", 1, args=(summaries[current],))
                opened += 1
        # Bring the item into view first, so the click itself scrolls nothing.
        page.js(INTO_VIEW, link)
        before = page.ajs(SETTLED)
        page.click(link, scroll=False)
        page.sleep(0.3)
        nowhere(f"{where(owner, example)}: a click on {text!r} goes nowhere", owner, link, before, False)
        clicked += 1
    if current >= 0:
        page.click(summaries[current])
        page.wait(f"{where(current)}: a click on its summary closes it",
                  "!arguments[0].parentElement.open", 1, args=(summaries[current],))
    page.eq("every dropdown was opened once", opened, dropdowns)
    page.eq("every example link was clicked", clicked, want)

    # Keyboard: Enter on each summary, Tab to each item, Enter on it.
    current, opened, pressed = -1, 0, 0
    for link, owner, text, example in items:
        if owner != current:
            if current >= 0:
                page.expect(f"{where(current)}: its summary takes focus", page.js(FOCUS, summaries[current]))
                page.key("ENTER")
                page.wait(f"{where(current)}: Enter on its summary closes it",
                          "!arguments[0].parentElement.open", 1, args=(summaries[current],))
            current = owner
            if current >= 0:
                page.expect(f"{where(current)}: its summary takes focus", page.js(FOCUS, summaries[current]))
                page.key("ENTER")
                page.wait(f"{where(current)}: Enter on its summary opens it",
                          "arguments[0].parentElement.open", 1, args=(summaries[current],))
                opened += 1
        if current >= 0:
            # In view first, so the focus that Tab moves scrolls nothing.
            page.js(INTO_VIEW, link)
            page.key("TAB")
            page.expect(f"{where(owner, example)}: Tab moves focus to {text!r}",
                        page.js("return document.activeElement === arguments[0]", link),
                        focused=page.js("return document.activeElement.outerHTML.slice(0, 120)"))
        else:
            page.expect(f"{example}: {text!r} takes focus", page.js(FOCUS, link))
        before = page.ajs(SETTLED)
        page.key("ENTER")
        page.sleep(0.3)
        nowhere(f"{where(owner, example)}: Enter on {text!r} goes nowhere", owner, link, before, True)
        pressed += 1
    if current >= 0:
        page.expect(f"{where(current)}: its summary takes focus", page.js(FOCUS, summaries[current]))
        page.key("ENTER")
        page.wait(f"{where(current)}: Enter on its summary closes it",
                  "!arguments[0].parentElement.open", 1, args=(summaries[current],))
    page.eq("every dropdown was opened once from the keyboard", opened, dropdowns)
    page.eq("Enter was pressed on every example link", pressed, want)
    page.note(f"{clicked} example links clicked and {pressed} activated with Enter, in {opened} dropdowns:"
              " every click canceled, nothing navigated")
