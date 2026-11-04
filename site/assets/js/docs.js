// docs.js: every docs page (loaded from docs.html). docs/research/01 §2 and 03 §5.
//
// The base (above the regions) rebuilds the docs layout's behaviors on the oracle's own markup, and
// in Phase 1 adds no attribute the oracle lacks (no aria-expanded; PLAN.md Conversion rules):
// - the side menu, #documentation-menu (DocumentationMenu.jsx): the current route's category open,
//   aria-current="true" on its summary and aria-current="page" on its link (the Version picker link
//   on a color route); the nav's --max-height (innerHeight minus its top, when the module runs, on
//   the window's load and on resize); the mobile off-canvas (is-open-on-mobile), opened by the
//   breadcrumb's Documentation link and closed by its Close link and by any of its links (scroll
//   lock is the CSS's :has()). Like the oracle's,
//   it has no Escape handler (01 §2); Phase 3's mobile menu adds Escape and focus (criterion 7);
// - the breadcrumb, nav[aria-label=breadcrumb] (Breadcrumb.jsx): is-sticky while its top is -1 px
//   or less, that is while it is stuck to the top of the viewport (its CSS sticks it at top: -1px);
// - the table of contents, #table-of-contents (TableOfContents.jsx, ghostui's Scrollspy): its n-th
//   link is the n-th section of #content, and aria-current="page" marks the first section in view
//   with the viewport shifted down by twice the header's height, or the last one at the page's end.
// Each part does nothing when its markup is absent. Phase 3 replaces the table of contents with the
// one-page spy and drives the menu from it.
//
// ROUTE-GROUP REGIONS. Below the base, each route group owns the text between its own two marker
// lines, `// region:<group>` and `// endregion:<group>`, written as one widgets("<group>", ...) call
// that declares nothing at the top level, adds no import (site.js's exports are the `site`
// namespace) and keeps no state shared between widgets. tests/README.md (Behavior, Editing docs.js)
// has the protocol Phase 1's agents used to edit their regions.

import * as site from "./site.js";

// Sets an attribute only when its value differs, so an unchanged state causes no mutation.
function setAttr(element, name, value) {
  if (element.getAttribute(name) !== value) element.setAttribute(name, value);
}

// Removes the attribute an empty class list leaves, as React does when className goes away.
function dropEmptyClass(element) {
  if (element.getAttribute("class") === "") element.removeAttribute("class");
}

// Runs one group's widgets; an exception is reported (window error event, console) and does not
// stop the code after it.
function widgets(group, init) {
  try {
    init();
  } catch (error) {
    reportError(new Error(`docs.js ${group}: ${error}`, { cause: error }));
  }
}

// The route as the oracle's NavigationContext reads it: the path without a trailing slash.
const path = location.pathname.replace(/\/\s*$/, "");

// --- Side menu (DocumentationMenu.jsx) -----------------------------------------------------------

function sideMenu() {
  const menu = document.getElementById("documentation-menu");
  const nav = menu?.querySelector(":scope > nav");
  if (!nav) return;

  // The current route's category and link. The build writes the same state for each route; this
  // keeps it right for whatever path served the page.
  const colorRoute = path.includes("/docs/version-picker/");
  for (const details of nav.querySelectorAll(":scope > details")) {
    const summary = details.querySelector(":scope > summary");
    const links = [...details.querySelectorAll("a")];
    const current = links.some((link) => link.getAttribute("href") === path)
      || (colorRoute && summary?.textContent.trim() === "Getting started");
    if (current) {
      details.open = true;
      if (summary) setAttr(summary, "aria-current", "true");
    }
    for (const link of links) {
      const href = link.getAttribute("href");
      if (href === path || (colorRoute && href === "/docs/version-picker")) setAttr(link, "aria-current", "page");
    }
  }

  // --max-height: what is left of the viewport below the nav's top.
  const fit = () => {
    const maxHeight = innerHeight - nav.getBoundingClientRect().top;
    if (maxHeight !== 0) nav.style.setProperty("--max-height", `${maxHeight}px`);
    else nav.style.removeProperty("--max-height");
  };
  fit();
  // Safari can run this module before the page's stylesheets apply, so the nav's top is not yet
  // its own (tests/README.md, Phase 2, Safari): measure again once the page has loaded.
  if (document.readyState !== "complete") addEventListener("load", fit, { once: true });
  addEventListener("resize", fit);

  // The off-canvas menu below lg.
  const setOpen = (open) => {
    menu.classList.toggle("is-open-on-mobile", open);
    dropEmptyClass(menu);
  };
  document.querySelector("main > nav[aria-label=breadcrumb] li:first-child > a")?.addEventListener("click", (event) => {
    event.preventDefault();
    setOpen(true);
  });
  menu.querySelector(":scope > header a[aria-label=Close]")?.addEventListener("click", (event) => {
    event.preventDefault();
    setOpen(false);
  });
  nav.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("a")) setOpen(false);
  });
}

// --- Breadcrumb (Breadcrumb.jsx) -----------------------------------------------------------------

function breadcrumb() {
  const crumb = document.querySelector("main > nav[aria-label=breadcrumb]");
  if (!crumb) return;
  // It is sticky at top: -1px, so stuck means a top of -1 px or less. A scroll and resize check
  // rather than an IntersectionObserver: a box that moves in sub-pixel steps can pass from not
  // stuck (top between -1 and 0) to stuck without crossing an observer threshold.
  const update = () => {
    crumb.classList.toggle("is-sticky", crumb.getBoundingClientRect().top <= -1);
    dropEmptyClass(crumb);
  };
  const queue = site.perFrame(update);
  addEventListener("scroll", queue, { passive: true });
  addEventListener("resize", queue);
  update();
}

// --- Table of contents (TableOfContents.jsx, ghostui Scrollspy) ----------------------------------

function tableOfContents() {
  const toc = document.getElementById("table-of-contents");
  const content = document.querySelector("#content[role=document]");
  if (!toc || !content) return;
  const links = [...toc.querySelectorAll("a")];
  const sections = [...content.querySelectorAll(":scope > section")].slice(0, links.length);
  const header = document.querySelector("body > header");
  const spy = () => {
    const page = document.documentElement;
    let current;
    if (page.scrollTop + innerHeight >= page.scrollHeight) {
      current = links.length - 1;
    } else {
      const offset = -2 * (header ? header.offsetHeight : 0);
      current = sections.findIndex((section) => {
        const { top, height } = section.getBoundingClientRect();
        return top + offset < innerHeight && top + offset + height > 0;
      });
    }
    links.forEach((link, index) => {
      if (index === current) setAttr(link, "aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  };
  addEventListener("scroll", site.perFrame(spy), { passive: true });
  spy();
}

widgets("side menu", sideMenu);
widgets("breadcrumb", breadcrumb);
widgets("table of contents", tableOfContents);

// region:getting-started
widgets("getting-started", () => {
  // /docs/color-schemes: the page's own theme switcher (docs.color-schemes.jsx), a button that
  // switches the page's scheme as the header toggle does, its icon's class and its label following
  // the scheme: "icon-theme-toggle theme-toggle" (" moon" added when dark; the emoji of Decision 16)
  // and "Turn on dark mode" or "Turn off dark mode", the text after the icon. The version picker is
  // picker.js's.
  const button = document.querySelector("#content article#theme-switcher > button");
  const icon = button?.querySelector(":scope > .icon-theme-toggle");
  const label = button && [...button.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
  if (!icon || !label) return;
  const show = (theme) => {
    const dark = theme === "dark";
    setAttr(icon, "class", dark ? "icon-theme-toggle theme-toggle moon" : "icon-theme-toggle theme-toggle");
    const text = dark ? "Turn off dark mode" : "Turn on dark mode";
    if (label.data !== text) label.data = text;
  };
  show(site.pageTheme());
  site.onThemeChange(show);
  button.addEventListener("click", () => site.switchTheme());
});
// endregion:getting-started

// region:layout
widgets("layout", () => {
  // Grid (docs.grid.jsx): "Add column" and "Remove column", the p.btn-group right before the
  // example, set its columns between 1 and 10 (4 on load), and the code sample follows. The sample
  // is rebuilt from its own load-time spans: the opening tag, one row per column (column 1's nine
  // spans, "\n", "  ", <, div, >, the number, </, div, >, with the number changed), then the
  // closing line, as the oracle re-highlights it.
  // The count lives as long as the page: a same-route link (the TOC's "Syntax", href="/docs/grid")
  // reloads it at 4, and back from another route restores it from the bfcache, where the oracle
  // keeps it and resets it, respectively. That follows from plain <a> and the browser's own history
  // (PLAN.md Conversion rules, Decision 2); Phase 3's fragment links on one page keep it.
  const example = document.querySelector('#content article.component[aria-label="Grid example"]');
  const grid = example?.querySelector(":scope > .grid");
  const code = example?.querySelector(":scope > footer.code > pre > code");
  const group = example?.previousElementSibling;
  const buttons = group?.matches("p.btn-group") ? group.querySelectorAll(":scope > button") : [];
  if (!grid || !code || buttons.length !== 2) return;

  const ROW = 9, NUMBER = 5, MIN = 1, MAX = 10;
  let columns = grid.querySelectorAll(":scope > div").length;
  const spans = [...code.childNodes];
  const first = spans.findIndex((span, i) => span.textContent === "\n" && /^\d+$/.test(spans[i + NUMBER]?.textContent ?? ""));
  // The markup is there, so a sample in another shape (a highlighting change) is a defect for
  // widgets() to report, not a page without the demo: it needs one row per column, numbered 1 to n.
  const isRow = (k) => spans[first + k * ROW]?.textContent === "\n" && spans[first + k * ROW + NUMBER]?.textContent === String(k + 1);
  let rowsFound = 0;
  while (first >= 0 && isRow(rowsFound)) rowsFound++;
  if (rowsFound < MIN || rowsFound !== columns) {
    throw new Error(`grid sample tokens not recognized: ${rowsFound} highlighted rows for ${columns} columns`);
  }
  const opening = spans.slice(0, first);
  const row = spans.slice(first, first + ROW);
  const closing = spans.slice(first + ROW * columns);

  const render = () => {
    const cells = [...grid.querySelectorAll(":scope > div")].slice(0, columns);
    while (cells.length < columns) {
      const cell = document.createElement("div");
      cell.textContent = String(cells.length + 1);
      cells.push(cell);
    }
    grid.replaceChildren(...cells);
    const rows = [];
    for (let n = 1; n <= columns; n++) {
      for (const [i, span] of row.entries()) {
        const copy = span.cloneNode(true);
        if (i === NUMBER) copy.textContent = String(n);
        rows.push(copy);
      }
    }
    code.replaceChildren(...opening, ...rows, ...closing);
  };
  const set = (n) => {
    const next = Math.min(Math.max(n, MIN), MAX);
    if (next === columns) return;
    columns = next;
    render();
  };
  const [add, remove] = buttons;
  add.addEventListener("click", () => set(columns + 1));
  remove.addEventListener("click", () => set(columns - 1));
});
// endregion:layout

// region:content
widgets("content", () => {
  // /docs/typography: the "Display in rem" switch of the responsive font-size table
  // (FontsizeTable.jsx). Off, each cell shows its size in px, with the formula as a tooltip; on, the
  // Base row shows the root size as a percentage and each element row its multiplier, with no
  // tooltip. The formula is the cell's own data: "<root>% * 16px" or "<root>% * <size><unit> * 16px".
  const fontSizes = document.querySelector("table#responsive-font-sizes");
  const inRem = document.querySelector('input[type=checkbox][name="toggle-font-size-in-rem"]');
  if (fontSizes && inRem) {
    const small = (text) => {
      const element = document.createElement("small");
      element.textContent = text;
      return element;
    };
    const cells = [];
    for (const td of fontSizes.querySelectorAll(":scope > tbody > tr > td")) {
      const terms = td.querySelector(":scope > span[data-tooltip]")?.getAttribute("data-tooltip").split(" * ");
      if (!terms) continue;
      // The px content as loaded, restored as is; the rem content, as the oracle renders it.
      const px = [...td.childNodes];
      const rem = () => {
        if (terms.length === 2) return [terms[0].replace(/%$/, ""), small("%")];
        const [, size, unit] = terms[1].match(/^(.*?)([a-z%]*)$/);
        return [small("x\u00a0"), size, small(unit)]; // "x&nbsp;"
      };
      cells.push({ td, px, rem });
    }
    const show = () => {
      for (const { td, px, rem } of cells) td.replaceChildren(...(inRem.checked ? rem() : px));
    };
    inRem.addEventListener("change", show);
    // An oracle-bug fix (PLAN.md, oracle-bug): Firefox restores the switch as checked on a reload,
    // and the oracle's useState(false) ignores it, so it shows the px table under a checked switch
    // and its first click unchecks the switch without changing the table. Here the table follows
    // the switch from the start (the font-size-restored-switch behavior check).
    if (inRem.checked) show();
  }

  // /docs/table, "Color schemes": the example table's thead takes the inverse of the page's scheme,
  // and the sample right after the example names that value (docs.table.jsx, inversedTheme). It is
  // the docs' only thead with a data-theme. Bound to the example's own markup, not to the
  // subheading's id="color-schemes", which collides with the Color schemes section's id (01 §1);
  // Phase 3 gives it a data- hook.
  const thead = document.querySelector("div.overflow-auto > table > thead[data-theme]");
  if (thead) {
    const sample = thead.closest("div.overflow-auto").nextElementSibling;
    const code = sample?.matches("div.code") ? sample.querySelector(":scope > pre > code") : null;
    // The sample's one attribute value token: `dark` in <thead data-theme="dark">.
    const token = [...(code?.querySelectorAll("span.attr-value") ?? [])].find((span) => /^(light|dark)$/.test(span.textContent));
    const show = (theme) => {
      const inverse = theme === "dark" ? "light" : "dark";
      setAttr(thead, "data-theme", inverse);
      if (token && token.textContent !== inverse) token.textContent = inverse;
    };
    show(site.pageTheme());
    site.onThemeChange(show);
  }

  // /docs/link: the example links are Link to="#" with an onClick that prevents the default
  // (docs.link.jsx), so they show the route's own path and go nowhere (the link-examples check).
  const examples = '#content article[aria-label="Links example"] > a, #content article[aria-label="Active link example"] > a';
  for (const link of document.querySelectorAll(examples)) link.addEventListener("click", (event) => event.preventDefault());
});
// endregion:content

// region:forms
widgets("forms", () => {
  // /docs/forms/checkboxes, "Indeterminate": the example's checkbox is indeterminate once the page
  // has loaded. docs.forms.checkboxes.jsx sets the property from a ref after hydration, so the markup
  // keeps no attribute for it and a click then checks the box as a native checkbox does.
  const box = document.querySelector('#content article[aria-label="Indeterminate checkbox example"] input[type=checkbox][name=indeterminate]');
  if (box) box.indeterminate = true;
});
// endregion:forms

// region:components-a
widgets("components-a", () => {
  // /docs/dropdown (docs.dropdown.jsx): the examples' menu items and the nav example's "Services"
  // are its Item, a Link to="#" with an onClick that prevents the default, so they show the route's
  // own path and go nowhere, clicked or activated with Enter (the dropdown-items check). Gated on
  // "Dropdowns as buttons", an example only this route has: /docs/nav repeats the "Dropdowns
  // inside nav" example, whose links the components-b region cancels, and /docs/forms/select's
  // "Dropdowns as selects" has no link.
  if (!document.querySelector('#content article.component[aria-label="Dropdowns as buttons"]')) return;
  const items = '#content article.component[aria-label^="Dropdowns "] a:not(.copy-to-clipboard)';
  for (const item of document.querySelectorAll(items)) item.addEventListener("click", (event) => event.preventDefault());
});
// endregion:components-a

// region:components-b
widgets("components-b", () => {
  // /docs/modal (docs.modal.jsx with ModalContext.jsx): the demo dialog, the <dialog> without class
  // "example" right in <main>, opens from "Open modal" (#modal-demo) and closes from its Cancel and
  // Confirm buttons, a click on its backdrop and Escape, through site.js's helper for this one
  // dialog. The two dialog.example are always open, and their buttons do nothing.
  const openModal = document.querySelector("#content article#modal-demo > button");
  const demo = document.querySelector("main > dialog:not(.example)");
  if (openModal && demo) {
    const modal = site.createModal(demo);
    openModal.addEventListener("click", () => modal.open());
    for (const button of demo.querySelectorAll(":scope > article > footer > button")) {
      button.addEventListener("click", () => modal.close());
    }
  }

  // /docs/nav (docs.nav.jsx): the example links are Link to="#" with an onClick that prevents the
  // default, so they show the route's own path and go nowhere: those of the examples' navs and of
  // the nav[aria-label=overflow-with-focus] that the route puts first in <main>.
  if (document.querySelector('main > nav[aria-label="overflow-with-focus"]')) {
    const links = document.querySelectorAll('main > nav[aria-label="overflow-with-focus"] a, #content > section > article.component nav a');
    for (const link of links) link.addEventListener("click", (event) => event.preventDefault());
  }

  // /docs/progress (docs.progress.jsx): the example's value is a random whole number from 5 to 94,
  // drawn again every 5 s, and its code sample prints it: the token right after value=" in
  // <progress value="N" max="100" />. A value is drawn on load (the oracle's client render draws its
  // own), and the interval runs only while the example is on screen (PLAN.md Conversion rules).
  const progress = document.querySelector('#content article[aria-label="Progress example"] > progress');
  const token = progress?.parentElement.querySelector(":scope > footer.code > pre > code > span.attr-value:not(.punctuation)");
  if (progress && token) {
    const draw = () => {
      const value = String(Math.floor(Math.random() * 90) + 5);
      setAttr(progress, "value", value);
      if (token.textContent !== value) token.textContent = value;
    };
    draw();
    let interval = 0;
    new IntersectionObserver((entries) => {
      const onScreen = entries.at(-1).isIntersecting;
      if (onScreen && !interval) {
        interval = setInterval(draw, 5000);
      } else if (!onScreen && interval) {
        clearInterval(interval);
        interval = 0;
      }
    }).observe(progress);
  }
});
// endregion:components-b
