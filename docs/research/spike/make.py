# Writes the spike's docs.html: a dozen stand-in docs sections on one page, sized like the real ones
# (some longer than the viewport, two much shorter, the last one short). Each section's top heading
# carries the section's one-or-two-word id; subheadings carry none.
# Run: python3 -I docs/research/spike/make.py
from html import escape
from pathlib import Path

HERE = Path(__file__).parent

# (id, title, category, description, [(subheading, paragraphs), ...])
SECTIONS = [
    ("quick-start", "Quick start", "Getting started", "Link femto from a CDN, install it from npm, or download it.",
     [("Usage", 3), ("Install from npm", 2), ("Starter HTML template", 4)]),
    ("version-picker", "Version picker", "Getting started", "Choose a theme color and options.",
     [("Theme color", 3), ("Options", 2), ("Usage", 2)]),
    ("color-schemes", "Color schemes", "Getting started", "Light and dark.",
     [("Usage", 2)]),
    ("css-variables", "CSS variables", "Customization", "Over 130 custom properties.",
     [("Usage", 3), ("Examples", 4), ("All variables", 6)]),
    ("container", "Container", "Layout", "Centered or fluid widths.",
     [("Breakpoints", 1)]),
    ("grid", "Grid", "Layout", "A minimal grid.",
     [("Syntax", 2), ("Examples", 3)]),
    ("forms", "Forms", "Forms", "Every form element, styled.",
     [("Syntax", 3), ("Validation states", 3), ("Disabled", 2)]),
    ("input", "Input", "Forms", "Text fields and friends.",
     [("Syntax", 3), ("Examples", 5), ("Validation states", 3)]),
    ("switch", "Switch", "Forms", "A checkbox with role=switch.",
     [("Syntax", 1)]),
    ("accordion", "Accordion", "Components", "Toggles made with details and summary.",
     [("Syntax", 2), ("Examples", 3)]),
    ("modal", "Modal", "Components", "A dialog holding an article.",
     [("Syntax", 3), ("Examples", 3), ("Utilities", 2)]),
    ("tooltip", "Tooltip", "Components", "Short labels on hover and focus.",
     [("Syntax", 1)]),
]

FILLER = (
    "This paragraph stands in for a paragraph of the real documentation, long enough to wrap across "
    "a few lines at desktop widths so that the section lengths here resemble the routes they model. "
    "It says nothing; it only takes up the space that prose, code samples and live examples take up."
)

# The inline head script the site's head partial would carry: the ?theme= stylesheet. Three insertion
# methods, chosen by ?method= for the spike's comparison: a script-inserted <link> (append, the
# default), the same with blocking="render" (blocking), or a parser-inserted one (write).
# __firstFrame records --femto-primary at the first animation frame, which runs only once rendering
# is allowed.
HEAD_SCRIPT = """<script>
(() => {
  const params = new URLSearchParams(location.search);
  const theme = params.get("theme");
  if (theme && /^[a-z]+$/.test(theme)) {
    const href = `/themes/${theme}.css`;
    if (params.get("method") === "write") {
      document.write(`<link rel="stylesheet" href="${href}">`);
    } else {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      if (params.get("method") === "blocking") link.setAttribute("blocking", "render");
      document.head.append(link);
    }
  }
  requestAnimationFrame(() => {
    window.__firstFrame = getComputedStyle(document.documentElement).getPropertyValue("--femto-primary").trim();
  });
})();
</script>"""


def main():
    nav, body = [], []
    category = None
    for sid, title, cat, desc, subs in SECTIONS:
        if cat != category:
            if category:
                nav.append("</ul></details>")
            nav.append(f"<details open><summary>{escape(cat)}</summary><ul>")
            category = cat
        nav.append(f'<li><a href="#{sid}">{escape(title)}</a></li>')

        body.append(f'<section data-title="{escape(title)}">')
        body.append(f'<hgroup><p>{escape(cat)}</p><h1 id="{sid}">{escape(title)}</h1><p>{escape(desc)}</p></hgroup>')
        for text, paragraphs in subs:
            body.append(f"<h2>{escape(text)}</h2>")
            body.extend(f"<p>{FILLER}</p>" for _ in range(paragraphs))
        body.append("</section>")
    nav.append("</ul></details>")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Documentation • femto</title>
<link rel="stylesheet" href="/femto.min.css">
<link rel="stylesheet" href="/femto.colors.min.css">
<link rel="stylesheet" href="/spike.css">
{HEAD_SCRIPT}
<script type="module" src="/docs.js"></script>
</head>
<body>
<header class="container-fluid"><nav><ul><li><a href="/"><strong>femto</strong></a></li></ul>
<ul><li><a href="/docs" aria-current="page">Docs</a></li><li><a href="/examples.html">Examples</a></li></ul></nav></header>
<div class="docs container">
<aside><nav id="docs-nav" aria-label="Documentation">
{chr(10).join(nav)}
</nav></aside>
<main id="content">
{chr(10).join(body)}
</main>
</div>
<footer class="container"><small>Spike footer</small></footer>
</body>
</html>
"""
    (HERE / "docs.html").write_text(page)


main()
