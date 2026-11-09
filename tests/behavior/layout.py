"""Layout: the Grid section's column demo (the Remix site's docs.grid.jsx)."""
from behavior import TOKENS, check

GROUP = "layout"

GRID = """
const art = S.querySelector('article[aria-label="Grid example"]');
const code = art.querySelector("footer pre code");
return {cells: [...art.querySelectorAll(":scope > .grid > div")].map(d => d.textContent), code: code.textContent, tokens: tokens(code)};
"""
# The demo's two buttons, in a div.grid of their own (a p.btn-group, then a div[role=group], until
# 2026-11-09), found in the Grid section only, so a grid or group added to another section is never clicked.
DEMO = "#content > section:has(> hgroup > h1#grid) > section > .grid"
ADD, REMOVE = f"{DEMO} > button:first-child", f"{DEMO} > button:last-child"


def code_for(n):
    return '<div class="grid">\n' + "\n".join(f"  <div>{i}</div>" for i in range(1, n + 1)) + "\n</div>"


def tokens_for(n):
    """The highlighted code for n columns as the build writes it (TOKENS: [class, text] per child,
    "#text" for plain text): the tag names in span.tag, the attribute name in span.attr, the quoted
    value in span.value, and the rest plain text, each run between two spans one text node."""
    out = [["#text", "<"], ["tag", "div"], ["#text", " "], ["attr", "class"], ["#text", "="], ["value", '"grid"'],
           ["#text", ">\n  <"]]
    for k in range(1, n + 1):
        out += [["tag", "div"], ["#text", f">{k}</"], ["tag", "div"], ["#text", ">\n  <" if k < n else ">\n</"]]
    return out + [["tag", "div"], ["#text", ">"]]


@check("grid-columns", "/docs#grid")
def grid_columns(page):
    """The grid example (`article[aria-label="Grid example"] > .grid`) starts with 4 columns
    (divs reading 1 to 4) and its code reads <div class="grid"> with one <div>N</div> line per
    column. "Add column" adds one up to 10 (an 11th click keeps 10), "Remove column" removes one
    down to 1 (a further click keeps 1); after every click the columns and the code text match. On
    load and after every click the code is highlighted as the build highlights it (its tokens, the
    model tokens_for)."""
    initial = page.js(TOKENS + GRID)
    page.eq("4 columns on load", initial["cells"], ["1", "2", "3", "4"])
    page.eq("the code on load", initial["code"], code_for(4))
    page.eq("the code on load is highlighted", initial["tokens"], tokens_for(4))
    n = 4
    for button, times, step, lo, hi in ((ADD, 7, 1, 1, 10), (REMOVE, 10, -1, 1, 10), (ADD, 3, 1, 1, 10)):
        for _ in range(times):
            page.click(page.find(button))
            n = max(lo, min(hi, n + step))
            page.wait(f"{n} columns", "S.querySelectorAll('article[aria-label=\"Grid example\"] > .grid > div').length === arguments[0]",
                      1, args=(n,))
            g = page.js(TOKENS + GRID)
            page.eq(f"{n} columns read 1 to {n}", g["cells"], [str(i) for i in range(1, n + 1)])
            page.eq(f"the code for {n} columns", g["code"], code_for(n))
            page.eq(f"the code for {n} columns is highlighted", g["tokens"], tokens_for(n))
