// One-page docs: marks the section being read in the side nav, keeps the title and the URL's #hash
// in step with it, and holds still while the browser scrolls to a link's target. Links, deep links,
// back and forward are the browser's own fragment navigation; this only follows the scroll.

const header = document.querySelector("body > header");
// Each section is the parent of the heading that carries its id.
const sections = [...document.querySelectorAll("main > section > hgroup > h1[id]")].map(
  (heading) => heading.closest("section"),
);
const idOf = (section) => section.querySelector("hgroup > h1[id]").id;
const navLinkById = new Map(
  [...document.querySelectorAll("#docs-nav a[href^='#']")].map((link) => [link.hash.slice(1), link]),
);
const titleSuffix = " • femto";
const baseTitle = document.title;

// The URL is written this long after the current section last changed, so fast scrolling through
// many sections writes it once, well inside the browsers' history API rate limits.
const URL_DELAY = 200;
// Without scroll events for this long, a scroll the browser runs for a link or a traversal is over.
const SCROLL_IDLE = 150;

let current = null;
let urlTimer = 0;
let frame = 0;
let locked = false;
let lockTimer = 0;

// The section being read: the last whose top has passed a line just below the fixed header. At the
// very bottom of the page, a short last section that can never reach the line wins once its top is
// on screen.
function sectionInView() {
  const atBottom = innerHeight + scrollY >= document.documentElement.scrollHeight - 2;
  const last = sections.at(-1);
  if (atBottom && last.getBoundingClientRect().top < innerHeight) return last;
  const line = header.offsetHeight + 24;
  let found = sections[0];
  for (const section of sections) {
    if (section.getBoundingClientRect().top > line) break;
    found = section;
  }
  return found;
}

function show(section) {
  if (section === current) return;
  navLinkById.get(current && idOf(current))?.removeAttribute("aria-current");
  current = section;
  const link = navLinkById.get(idOf(section));
  link?.setAttribute("aria-current", "true");
  revealInNav(link);
  document.title = section === sections[0] ? baseTitle : section.dataset.title + titleSuffix;
}

// Scrolls the side nav, not the page, so the current link is visible in it.
function revealInNav(link) {
  const nav = link?.closest("aside");
  if (!nav) return;
  const top = link.offsetTop - nav.offsetTop;
  if (top < nav.scrollTop || top + link.offsetHeight > nav.scrollTop + nav.clientHeight) {
    nav.scrollTop = top - nav.clientHeight / 3;
  }
}

// Replaces the #hash with the current section's id once scrolling has settled on it. The first
// section has no hash, so the top of the page is plain /docs. The query (?theme=) stays.
function syncUrl() {
  clearTimeout(urlTimer);
  urlTimer = setTimeout(() => {
    const hash = current === sections[0] ? "" : `#${idOf(current)}`;
    if (hash !== location.hash) {
      // Safari throws past 100 history calls in 10 seconds; the next settle retries.
      try {
        history.replaceState(history.state, "", location.pathname + location.search + hash);
      } catch {}
    }
  }, URL_DELAY);
}

function onScroll() {
  if (locked) {
    clearTimeout(lockTimer);
    lockTimer = setTimeout(unlock, SCROLL_IDLE);
    return;
  }
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = 0;
    show(sectionInView());
    syncUrl();
  });
}

// Holds the spy still while the browser scrolls to a link's target or restores a position, so the
// nav does not flicker through every section in between, then picks up wherever the scroll ended.
function lock() {
  locked = true;
  clearTimeout(urlTimer);
  clearTimeout(lockTimer);
  lockTimer = setTimeout(unlock, SCROLL_IDLE);
}

function unlock() {
  locked = false;
  document.documentElement.classList.remove("is-scrolling-to-link");
  show(sectionInView());
  syncUrl();
}

// A click on a link to a section: the browser navigates and scrolls, smoothly because of the class
// (see spike.css); mark the target now and lock until the scroll ends.
document.addEventListener("click", (event) => {
  const link = event.target.closest("a[href*='#']");
  if (!link || link.origin !== location.origin || link.pathname !== location.pathname) return;
  const heading = document.getElementById(decodeURIComponent(link.hash.slice(1)));
  const section = heading?.matches("hgroup > h1") && heading.closest("section");
  if (!section) return;
  document.documentElement.classList.add("is-scrolling-to-link");
  show(section);
  lock();
});

// Back and forward: the browser restores the entry's position; the spy follows once it settles.
addEventListener("popstate", lock);
addEventListener("scroll", onScroll, { passive: true });
show(sectionInView());
