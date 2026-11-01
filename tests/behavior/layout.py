"""Layout: /docs/grid's column demo (01 §2, small widgets: docs.grid.jsx)."""
from behavior import TOKENS, check

GROUP = "layout"

GRID = """
const art = document.querySelector('article[aria-label="Grid example"]');
const code = art.querySelector("footer pre code");
return {cells: [...art.querySelectorAll(":scope > .grid > div")].map(d => d.textContent), code: code.textContent, tokens: tokens(code)};
"""
ADD, REMOVE = "#content p.btn-group button:first-child", "#content p.btn-group button:last-child"


def code_for(n):
    return '<div class="grid">\n' + "\n".join(f"  <div>{i}</div>" for i in range(1, n + 1)) + "\n</div>"


def tokens_for(initial, n):
    """The highlighted code for n columns, built from the load-time tokens (4 columns): the opening
    tag's tokens, then one row per column (the row tokens of column 1 with its number changed),
    then the closing tag's."""
    rows, start = [], None
    # A row is ["", "\n"], ["", "  "], < div >, ["", "<i>"], </ div >: 9 children starting at a "\n".
    for i in range(len(initial)):
        if initial[i] == ["", "\n"] and i + 8 < len(initial) and initial[i + 5][0] == "" and initial[i + 5][1].isdigit():
            rows.append(i)
    start, end = rows[0], rows[-1] + 9
    row = initial[start:start + 9]
    out = initial[:start]
    for k in range(1, n + 1):
        out += [r if j != 5 else ["", str(k)] for j, r in enumerate(row)]
    return out + initial[end:]


@check("grid-columns", "/docs/grid")
def grid_columns(page):
    """The grid example (`article[aria-label="Grid example"] > .grid`) starts with 4 columns
    (divs reading 1 to 4) and its code reads <div class="grid"> with one <div>N</div> line per
    column. "Add column" adds one up to 10 (an 11th click keeps 10), "Remove column" removes one
    down to 1 (a further click keeps 1); after every click the columns and the code text match, and
    the code stays highlighted like the load-time sample (its tokens, row by row)."""
    initial = page.js(TOKENS + GRID)
    page.eq("4 columns on load", initial["cells"], ["1", "2", "3", "4"])
    page.eq("the code on load", initial["code"], code_for(4))
    n = 4
    for button, times, step, lo, hi in ((ADD, 7, 1, 1, 10), (REMOVE, 10, -1, 1, 10), (ADD, 3, 1, 1, 10)):
        for _ in range(times):
            page.click(button)
            n = max(lo, min(hi, n + step))
            page.wait(f"{n} columns", "document.querySelectorAll('article[aria-label=\"Grid example\"] > .grid > div').length === arguments[0]",
                      1, args=(n,))
            g = page.js(TOKENS + GRID)
            page.eq(f"{n} columns read 1 to {n}", g["cells"], [str(i) for i in range(1, n + 1)])
            page.eq(f"the code for {n} columns", g["code"], code_for(n))
            page.eq(f"the code for {n} columns is highlighted", g["tokens"], tokens_for(initial["tokens"], n))
