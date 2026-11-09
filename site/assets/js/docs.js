// docs.js: the one docs page, /docs (loaded from docs.html; PLAN.md Decisions 2 and 10).
//
// The base (above the regions) rebuilds the docs layout's behaviors:
// - the spy (Decision 2): the section being read is the last whose top
//   has passed a line just below the scroll padding (where a link to #<id> puts its heading), or at
//   the very bottom of the page the last section once its top is on screen. On a change it moves
//   aria-current="true" to its side-nav link and to its category's summary, opens that category's
//   <details> if the reader closed it (the build writes them open, so nothing in the nav moves on
//   load), scrolls the side nav (never the page) to show the link, sets the breadcrumb's chapter
//   to the category and its last item to the section's title, and sets document.title to
//   "<section> • femto" (the page's own title for the first section). 200 ms after scrolling last moved, once the section it settles on differs
//   from the URL's #hash, it writes the section's #<id> into the URL with replaceState (no hash for
//   the first section; the path and ?theme= stay), inside try: WebKit throws past 100 calls in 10 s.
//   Links, deep links, back, forward and reload are the browser's own fragment navigation. A click
//   on a link to a section marks it at once, locks the spy until the scroll reaches the section's
//   heading (or 1 s passes without a scroll event, or 150 ms once the reader's wheel, touch or key
//   takes over), and sets the class is-scrolling-to-link on <html> meanwhile, which docs.css gives
//   scroll-behavior: smooth unless the reader prefers reduced motion (Decision 10). popstate only
//   locks the spy, until 150 ms pass without a scroll event (except the popstate of a link's own
//   fragment navigation, which keeps the link's lock). Nothing here pushes a history entry of its own. The one link it cancels is a
//   link to /docs#<id> clicked on /docs?theme=<color>, whose #hash it then follows on this page;
// - the side menu, aside[data-docs-menu]: the mobile off-canvas (is-open-on-mobile), opened by the
//   breadcrumb's Documentation button and closed by its Close button, by any of its links and by
//   Escape, with the opener's aria-expanded, focus moved into the menu and back, and the rest of the
//   page inert while it is open, so focus stays in it (criterion 7; the Remix site had no Escape, no
//   aria-expanded and no focus handling). Its scroll lock is the CSS's :has(), and its nav's height
//   from lg up a calc() on 100dvh in docs.css.
// The breadcrumb's sticking and its border are docs.css's alone. The spy is main[data-docs-spy], the
// docs page's main: the sections in its div#content, the side menu's links and the breadcrumb's
// last two items. Each part does nothing when its markup is absent.
//
// ROUTE-GROUP REGIONS. Below the base, each route group owns the text between its own two marker
// lines, `// region:<group>` and `// endregion:<group>`, written as one widgets("<group>", ...) call
// that declares nothing at the top level, adds no import (site.js's exports are the `site`
// namespace) and keeps no state shared between widgets. Each widget finds its markup by a data-
// attribute on its root in the section's file (PLAN.md Rules, JavaScript), narrowed by selectors
// under it; tests/README.md (Behavior, Widget hooks) lists the hooks.

import * as site from "./site.js";

// Sets an attribute only when its value differs, so an unchanged state causes no mutation.
function setAttr(element, name, value) {
  if (element.getAttribute(name) !== value) element.setAttribute(name, value);
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

// --- The spy (Decision 2) ------------------------------------------------------------------------

// The URL is written this long after scrolling last moved (every scroll frame starts the wait
// again), once the section it settles on differs from the URL's #hash, so fast scrolling through
// many sections writes it once, well inside the browsers' history API rate limits.
const URL_DELAY = 200;
// Without scroll events for this long, a traversal's scroll is over.
const SCROLL_IDLE = 150;
// Without scroll events for this long, a link's scroll that has not reached its target never will
// (the reader took over, or the layout moved). Its frames can be far apart: headless Firefox under
// load drew the first 245 ms after the click and left a 194 ms gap in the middle.
const SCROLL_STALL = 1000;
// A section is current once its top is this far past the scroll padding: its heading's line.
const LINE_SLACK = 8;

function spy() {
  const root = document.querySelector("main[data-docs-spy]");
  if (!root) return;
  const nav = root.querySelector("[data-docs-menu] > nav");
  const sections = [...root.querySelectorAll(":scope > #content > section")].flatMap((element) => {
    const heading = element.querySelector(":scope > hgroup > h1[id]");
    if (!heading) return [];
    const link = nav?.querySelector(`a[href="#${CSS.escape(heading.id)}"]`) ?? null;
    const details = link?.closest("details") ?? null;
    return [{ element, id: heading.id, title: heading.textContent.trim(), link, details,
      summary: details?.querySelector(":scope > summary") ?? null }];
  });
  if (!sections.length) return;
  const page = document.documentElement;
  // The breadcrumb's second item names the category and its third the section.
  const chapter = root.querySelector("[data-docs-breadcrumb] li:nth-child(2)");
  const crumb = root.querySelector("[data-docs-breadcrumb] li:nth-child(3)");
  const baseTitle = document.title;
  const titleSuffix = " • femto";

  let current = null;
  let line = 0;
  let urlTimer = 0;
  let locked = false;
  let lockTimer = 0;
  let until = null; // the scrollY a link's scroll ends at, while it runs
  let untilHash = ""; // and that link's #hash

  const measure = () => {
    line = (parseFloat(getComputedStyle(page).scrollPaddingTop) || 0) + LINE_SLACK;
  };

  function sectionInView() {
    const atBottom = innerHeight + scrollY >= page.scrollHeight - 2;
    const last = sections.at(-1);
    if (atBottom && last.element.getBoundingClientRect().top < innerHeight) return last;
    let found = sections[0];
    for (const s of sections) {
      if (s.element.getBoundingClientRect().top > line) break;
      found = s;
    }
    return found;
  }

  // Scrolls the side nav, not the page, so the current link is visible in it.
  function revealInNav(link) {
    if (!nav || !link) return;
    const top = link.getBoundingClientRect().top - nav.getBoundingClientRect().top + nav.scrollTop;
    if (top < nav.scrollTop || top + link.offsetHeight > nav.scrollTop + nav.clientHeight) {
      nav.scrollTop = top - nav.clientHeight / 3;
    }
  }

  function show(next) {
    if (next === current) return;
    const previous = current;
    current = next;
    previous?.link?.removeAttribute("aria-current");
    next.link?.setAttribute("aria-current", "true");
    if (previous?.summary !== next.summary) {
      previous?.summary?.removeAttribute("aria-current");
      next.summary?.setAttribute("aria-current", "true");
    }
    if (next.details && !next.details.open) next.details.open = true;
    revealInNav(next.link);
    const category = next.summary?.textContent.trim();
    if (chapter && category && chapter.textContent !== category) chapter.textContent = category;
    if (crumb && crumb.textContent !== next.title) crumb.textContent = next.title;
    document.title = next === sections[0] ? baseTitle : next.title + titleSuffix;
  }

  // Replaces the #hash with the current section's id once scrolling has settled on it.
  function syncUrl() {
    clearTimeout(urlTimer);
    urlTimer = setTimeout(() => {
      const hash = current === sections[0] ? "" : `#${current.id}`;
      if (hash === location.hash) return;
      try {
        history.replaceState(history.state, "", location.pathname + location.search + hash);
      } catch {
        // WebKit's history limit (a SecurityError); the next settle writes it.
      }
    }, URL_DELAY);
  }

  const follow = site.perFrame(() => {
    if (locked) return;
    show(sectionInView());
    syncUrl();
  });

  // Where the browser scrolls for a link to the section: its heading on the scroll padding, or as
  // far as the page goes.
  function destination(target) {
    const heading = document.getElementById(target.id);
    const top = heading.getBoundingClientRect().top - (parseFloat(getComputedStyle(page).scrollPaddingTop) || 0)
      - (parseFloat(getComputedStyle(heading).scrollMarginTop) || 0);
    return Math.min(Math.max(scrollY + top, 0), page.scrollHeight - page.clientHeight);
  }

  const arrived = () => until !== null && Math.abs(scrollY - until) <= 1;

  // Holds the spy still while the browser scrolls to a link's target or restores a position, so the
  // nav does not flicker through every section in between, then picks up wherever the scroll ended.
  // A link's scroll ends when it reaches `to`, its destination, whatever the gaps between its
  // frames; a traversal's (no `to`) when SCROLL_IDLE passes without a scroll event.
  function lock(to = null, hash = "") {
    locked = true;
    until = to;
    untilHash = hash;
    clearTimeout(urlTimer);
    clearTimeout(lockTimer);
    lockTimer = setTimeout(unlock, until === null || arrived() ? SCROLL_IDLE : SCROLL_STALL);
  }

  function unlock() {
    locked = false;
    until = null;
    clearTimeout(lockTimer);
    page.classList.remove("is-scrolling-to-link");
    show(sectionInView());
    syncUrl();
  }

  addEventListener("scroll", () => {
    if (!locked) {
      follow();
      return;
    }
    if (arrived()) {
      unlock();
      return;
    }
    clearTimeout(lockTimer);
    lockTimer = setTimeout(unlock, until === null ? SCROLL_IDLE : SCROLL_STALL);
  }, { passive: true });
  // The reader's own wheel, touch or key ends a link's scroll early: from then on it is over once
  // the scroll goes idle. A touch is a pointerdown whose pointerType is "touch": Pointer Events are
  // Widely Available, and touchstart is not (Safari on macOS has no touch events; Decision 12). wheel
  // has no Widely Available substitute, so it stays: Safari on iOS never fires it, and there touch
  // pointers and keydown cover the reader's input without it.
  const takeOver = () => {
    until = null;
  };
  addEventListener("wheel", takeOver, { passive: true });
  addEventListener("keydown", takeOver, { passive: true });
  addEventListener("pointerdown", (event) => {
    if (event.pointerType === "touch") takeOver();
  }, { passive: true });

  // A click on a link to a section: the browser navigates and scrolls, smoothly because of the
  // class; mark the target now and lock until the scroll ends. A link another handler canceled (a
  // picker swatch) is not followed. A link to /docs#<id> from /docs?theme=<color> would
  // load the page again without its theme, so it becomes the fragment navigation it means, keeping
  // the query (Decision 8: the theme lasts as long as the URL carries it).
  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element ? event.target.closest("a[href*='#']") : null;
    if (!link || event.defaultPrevented || link.origin !== location.origin || link.pathname !== location.pathname) return;
    const target = sections.find((s) => s.id === decodeURIComponent(link.hash.slice(1)));
    if (!target) return;
    const keepQuery = link.search !== location.search;
    if (keepQuery) {
      const plain = event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey && !link.target;
      if (link.search || !plain) return;
      event.preventDefault();
    }
    page.classList.add("is-scrolling-to-link");
    show(target);
    lock(destination(target), link.hash);
    // location.assign(), not the hash setter, which does nothing when the hash is already the URL's:
    // assign() runs the fragment navigation either way, pushing an entry for another #hash and
    // replacing the entry for the same URL, as the browser's own click does on plain /docs.
    if (keepQuery) location.assign(location.pathname + location.search + link.hash);
  });

  // Back and forward: the browser restores the entry's position; the spy follows once it settles.
  // The link's own fragment navigation fires popstate too, at the link's #hash: its lock stays.
  addEventListener("popstate", () => {
    if (until === null || location.hash !== untilHash) lock();
  });
  addEventListener("resize", () => {
    measure();
    follow();
  });
  measure();
  show(sectionInView());
}

// --- Side menu (DocumentationMenu.jsx) -----------------------------------------------------------

function sideMenu() {
  const menu = document.querySelector("aside[data-docs-menu]");
  const nav = menu?.querySelector(":scope > nav");
  if (!nav) return;

  // The off-canvas menu below lg (docs.css's max-width: 1023px), opened by the breadcrumb's
  // Documentation button (data-menu-open) and closed by its Close button (data-menu-close), by any
  // of its nav links and by Escape. The opener's aria-expanded follows it. Opening moves focus to
  // the Close button; the Close button and Escape move it back to the opener, while a nav link leaves
  // it to the browser's fragment navigation. Closed below lg, the panel is only moved off screen, so
  // it is inert there to keep its links out of the tab order. Open below lg, it covers the page, so
  // the rest of the page is inert instead (every sibling of the menu and of each of its ancestors up
  // to <body> that is not inert already), and Tab and Shift+Tab stay within the menu; the page's
  // inert goes the moment the menu closes, before a nav link's fragment navigation runs.
  const opener = document.querySelector("[data-docs-breadcrumb] button[data-menu-open]");
  const close = menu.querySelector(":scope > header button[data-menu-close]");
  const offCanvas = matchMedia("(max-width: 1023px)");
  let open = false;
  let covered = []; // the elements made inert while the menu covers the page
  const cover = (on) => {
    if (on === (covered.length > 0)) return;
    if (!on) {
      for (const element of covered) element.inert = false;
      covered = [];
      return;
    }
    for (let node = menu; node.parentElement && node !== document.body; node = node.parentElement) {
      for (const sibling of node.parentElement.children) {
        if (sibling !== node && !sibling.inert) covered.push(sibling);
      }
    }
    for (const element of covered) element.inert = true;
  };
  const sync = () => {
    menu.inert = offCanvas.matches && !open;
    cover(offCanvas.matches && open);
  };
  // The opener sits in the sticky breadcrumb, always on screen below lg, and the browser scrolls the
  // page to the breadcrumb's place in the flow to show it when it takes focus. focus()'s
  // preventScroll option is outside Decision 12's target (Samsung Internet 27 and Chrome Android
  // ignore it), so the page's position is saved and put back: at once, for the scroll Chrome makes
  // inside focus(), and at each scroll for the next 250 ms, for the one Safari makes after the task
  // (p6-behavior-safari-light-2 found the page 66 px up). The reader's own wheel, key or pointer
  // ends the wait early.
  const focusInPlace = (element) => {
    const x = scrollX;
    const y = scrollY;
    const keep = () => {
      if (scrollX !== x || scrollY !== y) scrollTo(x, y);
    };
    const input = ["wheel", "keydown", "pointerdown"];
    let timer = 0;
    const done = () => {
      clearTimeout(timer);
      removeEventListener("scroll", keep);
      for (const type of input) removeEventListener(type, done, true);
    };
    element.focus();
    keep();
    addEventListener("scroll", keep, { passive: true });
    for (const type of input) addEventListener(type, done, { capture: true, passive: true });
    timer = setTimeout(done, 250);
  };
  const refocus = () => {
    if (opener) focusInPlace(opener);
  };
  const onKeydown = (event) => {
    if (event.key !== "Escape") return;
    setOpen(false);
    refocus();
  };
  function setOpen(next) {
    if (next === open) return;
    open = next;
    menu.classList.toggle("is-open-on-mobile", open);
    if (opener) setAttr(opener, "aria-expanded", String(open));
    if (open) {
      document.addEventListener("keydown", onKeydown);
      sync();
      if (close) focusInPlace(close); // in the fixed panel, on screen: kept in place all the same
    } else {
      document.removeEventListener("keydown", onKeydown);
      cover(false);
      // After the click that closes it has run its course: a nav link still navigates.
      setTimeout(sync);
    }
  }
  if (opener) setAttr(opener, "aria-expanded", "false");
  sync();
  offCanvas.addEventListener("change", sync);
  opener?.addEventListener("click", () => setOpen(true));
  close?.addEventListener("click", () => {
    setOpen(false);
    refocus();
  });
  nav.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("a")) setOpen(false);
  });
}

widgets("spy", spy);
widgets("side menu", sideMenu);

// region:getting-started
widgets("getting-started", () => {
  // The Color schemes section: its own theme switcher (docs.color-schemes.jsx),
  // button[data-scheme-switcher], which switches the page's scheme as the header toggle does, its
  // icon and its label following the scheme: the icon a decorative span[role=img] (Decision 18)
  // holding the header toggle's sun or moon emoji (Decision 16), and "Turn on dark mode" or "Turn off
  // dark mode", the text after the icon. The Theme picker is picker.js's.
  const button = document.querySelector("button[data-scheme-switcher]");
  const icon = button?.querySelector(":scope > span[role=img]");
  const label = button && [...button.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
  if (!icon || !label) return;
  const show = (theme) => {
    const dark = theme === "dark";
    const emoji = site.SCHEME_EMOJI[dark ? "dark" : "light"];
    if (icon.textContent !== emoji) icon.textContent = emoji;
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
  // Grid (docs.grid.jsx), section[data-grid-example]: "Add column" and "Remove column", in a femto
  // div.grid of their own, set the columns of its example between 1 and 10 (4 on load), and the code sample
  // follows. The sample is rebuilt from its own load-time lines as the build highlighted them (no
  // span holds a line break): the opening tag's line, one row per column (column 1's line,
  // <div>1</div>, with its number changed), then the closing line, as the Remix site re-highlighted it.
  // The count lives as long as the page: links within it are fragment links, which keep it, and
  // back from another page restores it from the bfcache.
  const demo = document.querySelector("[data-grid-example]");
  const example = demo?.querySelector(":scope > article");
  const grid = example?.querySelector(":scope > .grid");
  const code = example?.querySelector(":scope > footer.code > pre > code");
  const buttons = demo?.querySelectorAll(":scope > .grid > button") ?? [];
  if (!grid || !code || buttons.length !== 2) return;

  const MIN = 1, MAX = 10;
  let columns = grid.querySelectorAll(":scope > div").length;
  const lines = code.innerHTML.split("\n");
  const rowTexts = code.textContent.split("\n").slice(1, -1);
  // The markup is there, so a sample in another shape (a highlighting change) is a defect for
  // widgets() to report, not a page without the demo: it needs one row per column, numbered 1 to n.
  if (columns < MIN || rowTexts.length !== columns || rowTexts.some((text, i) => text !== `  <div>${i + 1}</div>`)
    || !lines[1].includes("&gt;1&lt;")) {
    throw new Error(`grid sample not recognized: ${rowTexts.length} rows for ${columns} columns`);
  }
  const [opening, row] = lines;
  const closing = lines.at(-1);

  const render = () => {
    const cells = [...grid.querySelectorAll(":scope > div")].slice(0, columns);
    while (cells.length < columns) {
      const cell = document.createElement("div");
      cell.textContent = String(cells.length + 1);
      cells.push(cell);
    }
    grid.replaceChildren(...cells);
    const rows = Array.from({ length: columns }, (_, i) => row.replace("&gt;1&lt;", `&gt;${i + 1}&lt;`));
    code.innerHTML = [opening, ...rows, closing].join("\n");
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
  // The Typography section, section[data-font-size-demo]: the "Display in rem" switch of the
  // responsive font-size table (FontsizeTable.jsx). Off, each cell shows its size in px, with the
  // formula as a tooltip; on, the Base row shows the root size as a percentage and each element row
  // its multiplier, with no tooltip. The formula is the cell's own data: "<root>% * 16px" or
  // "<root>% * <size><unit> * 16px".
  const fontSizeDemo = document.querySelector("[data-font-size-demo]");
  const fontSizes = fontSizeDemo?.querySelector("table");
  const inRem = fontSizeDemo?.querySelector("input[type=checkbox]");
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
      // The px content as loaded, restored as is; the rem content, as the Remix site rendered it.
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
    // A fix over the Remix site: Firefox restores the switch as checked on a reload, and the
    // Remix site's useState(false) ignored it, so it showed the px table under a checked switch
    // and its first click unchecked the switch without changing the table. Here the table follows
    // the switch from the start (the font-size-restored-switch behavior check).
    if (inRem.checked) show();
  }

  // The Table section, "Color schemes", section[data-inverse-thead]: the example table's thead takes
  // the inverse of the page's scheme, and the sample right after the example names that value
  // (docs.table.jsx, inversedTheme).
  const thead = document.querySelector("[data-inverse-thead] div.overflow-auto > table > thead[data-theme]");
  if (thead) {
    const sample = thead.closest("div.overflow-auto").nextElementSibling;
    const code = sample?.matches("div.code") ? sample.querySelector(":scope > pre > code") : null;
    // The sample's one attribute value: `"dark"` in <thead data-theme="dark">, with its quotes.
    const token = [...(code?.querySelectorAll("span.value") ?? [])].find((span) => /^"(light|dark)"$/.test(span.textContent));
    const show = (theme) => {
      const inverse = theme === "dark" ? "light" : "dark";
      setAttr(thead, "data-theme", inverse);
      if (token && token.textContent !== `"${inverse}"`) token.textContent = `"${inverse}"`;
    };
    show(site.pageTheme());
    site.onThemeChange(show);
  }

  // The Link section: the links of its two examples, article[data-link-example], are Link to="#"
  // with an onClick that prevents the default (docs.link.jsx), so they show the page's own path and
  // go nowhere (the link-examples check).
  for (const link of document.querySelectorAll("[data-link-example] > a")) link.addEventListener("click", (event) => event.preventDefault());
});
// endregion:content

// region:forms
widgets("forms", () => {
  // The Checkboxes section, "Indeterminate": the checkbox of its example,
  // article[data-indeterminate-example], is indeterminate once the page has loaded.
  // docs.forms.checkboxes.jsx sets the property from a ref after hydration, so the checkbox keeps no
  // attribute for it (the hook is on the example, not the checkbox) and a click then checks the box
  // as a native checkbox does.
  const box = document.querySelector("[data-indeterminate-example] input[type=checkbox]");
  if (box) box.indeterminate = true;
});
// endregion:forms

// region:components-a
widgets("components-a", () => {
  // The Dropdown section (docs.dropdown.jsx): the menu items of its examples with links,
  // article[data-dropdown-example], and the nav example's "Services" are its Item, a Link to="#"
  // with an onClick that prevents the default, so they show the page's own path and go nowhere,
  // clicked or activated with Enter (the dropdown-items check). Only the Dropdown section's: the Nav
  // section repeats the "Dropdowns inside nav" example, whose links the components-b region cancels,
  // and the Select section's "Dropdowns as selects" has no link.
  for (const item of document.querySelectorAll("[data-dropdown-example] a:not([data-copy-link])")) {
    item.addEventListener("click", (event) => event.preventDefault());
  }
});
// endregion:components-a

// region:components-b
widgets("components-b", () => {
  // The Modal section's demo dialog is site.js's (data-modal). Its two dialog.example are always
  // open, and their buttons do nothing.

  // The Nav section (docs.nav.jsx): the example links are Link to="#" with an onClick that prevents
  // the default, so they show the page's own path and go nowhere: the links of every example nav,
  // each a nav[data-nav-example] (the breadcrumbs and the two overflow examples among them).
  for (const link of document.querySelectorAll("[data-nav-example] a")) link.addEventListener("click", (event) => event.preventDefault());
});
// endregion:components-b
