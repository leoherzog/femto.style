"""Examples: the /examples page's mockups (PLAN.md Owner answers 1; examples.js). Each
mockup is vanilla femto in two declarative shadow roots: the outer one, in div[data-example], holds only
the inner host, so no page rule can match it; the inner one holds femto's stylesheet link and the
mockup, and a <details> under it, closed in the markup, holds the same markup to copy. examples.js
mirrors <html>'s data-theme onto each inner host, cancels the mockups' submits and link clicks, opens
and closes their dialogs, copies an example as a page (Copy as page, in femto's starter template) and
links the theme color the page's select names in every inner root."""
import re
from pathlib import Path

from behavior import COPY_SPY, PICKER_ORDER, check

GROUP = "examples"

# The example hosts: [frame, inner host, inner shadow root] per example, in page order.
HOSTS = """
const hosts = [...document.querySelectorAll('div[data-example]')].map(frame => {
  const inner = frame.shadowRoot?.firstElementChild ?? null;
  return {id: frame.closest('section')?.id, frame, inner, root: inner?.shadowRoot ?? null};
});
"""

# A point inside the element (its center), in viewport coordinates, after scrolling it to the middle.
CENTER = """
const center = (el) => { el.scrollIntoView({block: 'center', behavior: 'instant'}); const r = el.getBoundingClientRect();
  return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)]; };
"""


def shadow_point(page, expr):
    """Scroll the element the expression names (inside a shadow root) into view and return its center."""
    return page.js(HOSTS + CENTER + f"const el = {expr}; return el ? center(el) : null;")


@check("examples-structure", "/examples")
def examples_structure(page):
    """Each section.example holds one div[data-example] (16 on 2026-11-09), whose shadow root's only element is a div with a shadow root of
    its own; that root's first element is the one stylesheet link, /vendor/femto/dist/femto.min.css,
    loaded, with no other <link> or <style>; the markup after it is the code sample's text, node for
    node (whitespace collapsed), a shadow root inside it (the All theme colors example's) read as the
    <template shadowrootmode="open"> the sample writes; and no id repeats across the page, shadow
    roots included."""
    r = page.js(HOSTS + r"""
      const norm = (node) => {
        const walk = (n) => {
          for (const c of [...n.childNodes]) {
            if (c.nodeType === 3) { const t = c.data.replace(/\s+/g, ' ').trim(); if (!t) c.remove(); else c.data = t; }
            else if (c.nodeType === 8) c.remove();
            else walk(c);
          }
          if (n.content) walk(n.content);
        };
        walk(node);
        const div = document.createElement('div'); div.append(node); return div.innerHTML;
      };
      // A live node, its shadow root written as the declarative <template> that made it. A live
      // form's method="dialog", which keeps it from submitting, is not in the sample.
      const clone = (n) => {
        const c = n.cloneNode(false);
        if (n.nodeType !== 1) return c;
        if (c.localName === 'form' && c.getAttribute('method') === 'dialog') c.removeAttribute('method');
        if (n.shadowRoot) {
          const t = document.createElement('template');
          t.setAttribute('shadowrootmode', 'open');
          for (const k of n.shadowRoot.childNodes) t.content.append(clone(k));
          c.append(t);
        }
        for (const k of n.childNodes) c.append(clone(k));
        return c;
      };
      const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
      return hosts.map(h => {
        const out = {id: h.id, s1: !!h.frame.shadowRoot, s1Elements: h.frame.shadowRoot?.children.length, s2: !!h.root};
        if (!h.root) return out;
        const els = [...h.root.children];
        const link = els[0];
        out.link = link?.outerHTML;
        out.rules = h.root.styleSheets[0]?.cssRules.length ?? 0;
        out.sheets = h.root.styleSheets.length;
        out.otherStyles = h.root.querySelectorAll('link, style').length - 1;
        const live = document.createDocumentFragment();
        const nodes = [...h.root.childNodes];
        for (const n of nodes.slice(nodes.indexOf(link) + 1)) live.append(clone(n));
        const code = h.frame.closest('section').querySelector(':scope > details > .code pre code').textContent;
        const t = document.createElement('template'); t.innerHTML = code;
        const [x, y] = [norm(live), norm(t.content.cloneNode(true))];
        out.same = x === y && x.length > 100;
        if (!out.same) out.sample = [x.slice(0, 300), y.slice(0, 300)];
        out.part = h.inner.getAttribute('part');
        ids.push(...[...h.root.querySelectorAll('[id]')].map(e => e.id));
        return out;
      }).concat([{dupIds: ids.filter((id, i) => ids.indexOf(id) !== i)}]);
    """)
    dup = r.pop()["dupIds"]
    n = page.js("return document.querySelectorAll('main section.example').length")
    page.expect("the page has examples", n > 0)
    page.eq("one div[data-example] in each section.example", len(r), n)
    for h in r:
        page.expect(f"{h['id']}: two shadow roots, one element in the outer", h["s1"] and h["s2"] and h["s1Elements"] == 1, **h)
        page.eq(f"{h['id']}: the femto link", h["link"], '<link rel="stylesheet" href="/vendor/femto/dist/femto.min.css">')
        page.expect(f"{h['id']}: femto loaded, one sheet, nothing else", h["rules"] > 100 and h["sheets"] == 1 and h["otherStyles"] == 0, **h)
        page.expect(f"{h['id']}: the code sample is the markup", h["same"], **h)
    page.eq("no duplicate id, shadow roots included", dup, [])


# Computed styles of every element in each inner root (and ::before, ::after), the inner host
# included, as [path, pseudo, {property: value}]: every property the declaration lists, and every
# custom property femto.css declares or reads (femto_tokens(), the check's first argument), each read
# by its name. Other custom properties, the site's own among them, are left out: they inherit into
# the shadow roots from the page, and femto never reads them.
# The tokens are read by name, not taken from the declaration's list, because Firefox's list is not
# complete. On 2026-11-09 Firefox 160 listed 66,454 of the 94,785 pairs of an element and one of
# the 267 tokens on /examples (Chrome listed 91,368), and 120 more on the page than in the
# reference: four of femto's root tokens, --femto-light-contrast-hover, --femto-dark-contrast-hover
# and their -background versions, on elements where the reference's list left them out. Read by
# name, every one of the pairs had the same value on both sides.
STYLES = r"""
const tokens = arguments[0];
const props = (cs) => {
  const o = {};
  for (const p of cs) if (!p.startsWith('--')) o[p] = cs.getPropertyValue(p);
  for (const t of tokens) o[t] = cs.getPropertyValue(t);
  return o;
};
const collect = (hosts) => hosts.map(h => {
  const out = [['host', '', props(getComputedStyle(h.inner))]];
  const els = [...h.root.querySelectorAll('*')].filter(e => e.localName !== 'link' && !e.closest('details:not([open]) > :not(summary), dialog:not([open])'));
  els.forEach((e, i) => {
    out.push([i + ':' + e.localName, '', props(getComputedStyle(e))]);
    for (const pseudo of ['::before', '::after']) {
      const cs = getComputedStyle(e, pseudo);
      if (cs.content !== 'none' && cs.content !== 'normal') out.push([i + ':' + e.localName, pseudo, props(cs)]);
    }
  });
  return {id: h.id, styles: out};
});
"""

# The reference: the same examples in an iframe whose document loads femto alone, each in the same
# two shadow roots, with the frame given only the geometry examples.css gives it. The examples go in
# once that document has loaded, its root styled by femto (setHTMLUnsafe, which attaches declarative
# shadow roots). Parsed with the document, they gave 51 values in Safari 27.2 that differed from the
# page's, each a rem resolved at 16 px (an unstyled root's) where the page and the rest of the
# reference had 20 px (p4-behavior-safari-light-1), most likely values Safari resolved before the
# reference's root had femto's font size and never resolved again. The note gives both roots' size.
REFERENCE = r"""
const theme = arguments[1];
const frameCss = [...document.styleSheets].find(s => s.href?.endsWith('/assets/css/examples.css'));
const frameRules = [...frameCss.cssRules].map(r => r.cssText).filter(t => t.includes('div[data-example]'))
  .map(t => t.replaceAll('body > main.examples > section.example > div[data-example]', 'div[data-ref]')).join('\n');
const sections = hosts.map(h => {
  const code = h.frame.closest('section').querySelector(':scope > details > .code pre code').textContent;
  return `<div data-ref><template shadowrootmode="open"><div${theme ? ` data-theme="${theme}"` : ''}><template shadowrootmode="open"><link rel="stylesheet" href="/vendor/femto/dist/femto.min.css">${code}</template></div></template></div>`;
}).join('\n');
const html = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="/vendor/femto/dist/femto.min.css"><style>${frameRules}</style></head><body><main class="container"></main></body></html>`;
const iframe = document.createElement('iframe');
iframe.style.cssText = `position: fixed; top: 0; left: 0; width: ${innerWidth}px; height: ${innerHeight}px; border: 0; visibility: hidden;`;
document.body.append(iframe);
await new Promise(res => { iframe.onload = res; iframe.srcdoc = html; });
const doc = iframe.contentDocument;
const refRoot = getComputedStyle(doc.documentElement).fontSize;
doc.querySelector('main').setHTMLUnsafe(sections);
const refHosts = [...doc.querySelectorAll('div[data-ref]')].map((frame, i) => {
  const inner = frame.shadowRoot.firstElementChild; return {id: hosts[i].id, frame, inner, root: inner.shadowRoot};
});
// Every <link> in a root and in the shadow roots inside it (the All theme colors example's). A shadow
// host inside an example takes the scheme as the inner host does (examples.js).
const allLinks = (r) => [...r.querySelectorAll('link'), ...[...r.querySelectorAll('*')].filter(e => e.shadowRoot).flatMap(e => allLinks(e.shadowRoot))];
if (theme) for (const h of refHosts) for (const e of h.root.querySelectorAll('*')) if (e.shadowRoot) e.setAttribute('data-theme', theme);
for (const h of [...hosts, ...refHosts]) await Promise.all(allLinks(h.root).map(l => l.sheet ? null : new Promise(r => { l.onload = r; l.onerror = r; })));
for (let i = 0; i < 60; i++) {
  const running = refHosts.flatMap(h => h.root.getAnimations()).filter(a => a.playState === 'running' && a.constructor.name === 'CSSTransition');
  if (!running.length) break;
  await new Promise(r => setTimeout(r, 50));
}
await doc.fonts.ready;
await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
"""


def femto_tokens():
    import re
    from pathlib import Path
    css = (Path(__file__).resolve().parents[2] / "site/vendor/femto/dist/femto.css").read_text()
    return sorted(set(re.findall(r"(--femto-[\w-]+)", css)))


SETTLED = r"""
await document.fonts.ready;
for (let i = 0; i < 60; i++) {
  const running = hosts.flatMap(h => h.root.getAnimations()).filter(a => a.playState === 'running' && a.constructor.name === 'CSSTransition');
  if (!running.length) break;
  await new Promise(r => setTimeout(r, 50));
}
await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
"""

# Layout-resolved insets of positioned boxes (the breadcrumb's ::after dividers) depend on where the
# document puts them, which the reference iframe does not reproduce.
LAYOUT_ONLY = ("top", "right", "bottom", "left", "inset-block-start", "inset-block-end", "inset-inline-start", "inset-inline-end")


def compare_styles(page, theme):
    page.ajs(HOSTS + SETTLED + "return 1;")
    res = page.ajs(HOSTS + STYLES + REFERENCE + r"""
      let skipped = 0;
      // A running CSS animation (the indeterminate progress bar's) is at another point on each side:
      // every one is paused at its start on both, so the values compared are its first keyframe's.
      const animations = [...hosts, ...refHosts].flatMap(h => h.root.getAnimations()).filter(x => x.constructor.name === 'CSSAnimation');
      for (const x of animations) { x.pause(); x.currentTime = 0; }
      const a = collect(hosts), b = collect(refHosts);
      iframe.remove();
      const diffs = [];
      a.forEach((ex, i) => {
        const ref = b[i];
        if (ex.styles.length !== ref.styles.length) { diffs.push({id: ex.id, count: [ex.styles.length, ref.styles.length]}); return; }
        ex.styles.forEach(([path, pseudo, st], k) => {
          const [, , rt] = ref.styles[k];
          for (const p of new Set([...Object.keys(st), ...Object.keys(rt)])) {
            if (st[p] === rt[p]) continue;
            if (arguments[2].includes(p)) { skipped++; continue; }
            diffs.push({id: ex.id, path, pseudo, prop: p, page: st[p], ref: rt[p]});
          }
        });
      });
      return {diffs: diffs.slice(0, 40), total: diffs.length, skipped, elements: a.reduce((n, e) => n + e.styles.length, 0),
              roots: [getComputedStyle(document.documentElement).fontSize, refRoot], paused: animations.length};
    """, femto_tokens(), theme, list(LAYOUT_ONLY))
    page.note(f"compared {res['elements']} elements and pseudo-elements; {res['paused']} CSS animations paused at their start on both sides; "
              f"{res['skipped']} layout-resolved inset values differ (not compared); "
              f"root font size {res['roots'][0]} on the page, {res['roots'][1]} in the reference before its examples")
    page.eq("every computed style equals a femto-only page's", res["total"], 0, diffs=res["diffs"])


@check("examples-isolation", "/examples")
def examples_isolation(page):
    """Every element of every example, its host and pseudo-elements included, has the same computed
    style (every property, and every custom property femto.css names) as in a document that loads
    femto alone and holds the same markup in the same two shadow roots: no site CSS reaches in."""
    compare_styles(page, None)


@check("examples-isolation-dark", "/examples", media="dark")
def examples_isolation_dark(page):
    """As examples-isolation, with the OS in dark."""
    compare_styles(page, None)


@check("examples-isolation-stored", "/examples", storage={"femtoColorScheme": '"dark"'})
def examples_isolation_stored(page):
    """With a stored dark choice on a light OS, every inner host carries data-theme="dark", and every
    computed style equals the femto-only document's with data-theme="dark" on its inner hosts and on
    the shadow hosts inside them (the All theme colors example's)."""
    page.wait("every inner host is dark",
              "[...document.querySelectorAll('div[data-example]')].every(f => f.shadowRoot.firstElementChild.getAttribute('data-theme') === 'dark')")
    compare_styles(page, "dark")


@check("examples-scheme", "/examples")
def examples_scheme(page):
    """The inner hosts, and the shadow hosts inside them (the All theme colors example's 20), follow
    <html>'s data-theme: none on load (OS light, nothing stored), then dark and light again with the
    header toggle, and their backgrounds follow."""
    inner = "[...document.querySelectorAll('div[data-example]')].map(f => f.shadowRoot.firstElementChild)"
    nested = f"{inner}.flatMap(h => [...h.shadowRoot.querySelectorAll('*')].filter(e => e.shadowRoot))"
    page.eq("20 shadow hosts inside the examples", page.js(f"return {nested}.length"), 20)
    page.eq("no data-theme on load", page.js(f"return [...{inner}, ...{nested}].filter(h => h.hasAttribute('data-theme')).length"), 0)
    light = page.js(f"return [getComputedStyle({inner}[0]).backgroundColor, getComputedStyle({nested}[0]).backgroundColor]")
    page.click("button[data-scheme-toggle]")
    page.wait("toggle: every inner host dark", f"{inner}.every(h => h.getAttribute('data-theme') === 'dark')")
    page.wait("toggle: every shadow host inside them dark", f"{nested}.every(h => h.getAttribute('data-theme') === 'dark')")
    dark = page.js(f"return [getComputedStyle({inner}[0]).backgroundColor, getComputedStyle({nested}[0]).backgroundColor]")
    page.expect("the backgrounds follow", dark[0] != light[0] and dark[1] != light[1] and dark[1] == dark[0], light=light, dark=dark)
    page.click("button[data-scheme-toggle]")
    page.wait("toggle again: every inner host light", f"{inner}.every(h => h.getAttribute('data-theme') === 'light')")
    page.wait("toggle again: every shadow host inside them light", f"{nested}.every(h => h.getAttribute('data-theme') === 'light')")


@check("examples-forms", "/examples")
def examples_forms(page):
    """Each example form, filled in, is submitted with a real click on its submit button (and the
    search form with Enter): every submit event is canceled, and the document, URL and history stay."""
    page.js("window.__marker = 1;")
    before = page.url()
    forms = page.js(HOSTS + r"""
      window.__submits = [];
      const out = [];
      hosts.forEach((h, i) => {
        h.root.addEventListener('submit', e => __submits.push({id: h.id, prevented: e.defaultPrevented}));
        h.root.querySelectorAll('form').forEach((f, k) => {
          for (const el of f.elements) {
            if (el.type === 'email') el.value = 'sam@example.com';
            else if (el.localName === 'textarea' || el.type === 'text' || el.type === 'password' || el.type === 'search') el.value ||= 'Example text';
            else if (el.localName === 'select' && !el.value) el.selectedIndex = 1;
          }
          if (f.querySelector('button[type=submit]')) out.push([i, k, h.id]);
        });
      });
      return out;""")
    page.note(f"{len(forms)} forms with a submit button")
    for i, k, ex in forms:
        pt = shadow_point(page, f"hosts[{i}].root.querySelectorAll('form')[{k}].querySelector('button[type=submit]')")
        page.click_at(*pt)
        page.sleep(0.15)
    page.sleep(0.3)
    subs = page.js("return window.__submits")
    page.eq("one submit per form", len(subs), len(forms), submits=subs)
    page.expect("every submit canceled", all(s["prevented"] for s in subs), submits=subs)
    pt = shadow_point(page, "hosts.find(h => h.id === 'search-results').root.querySelector('input[type=search]')")
    page.click_at(*pt)
    page.key("ENTER")
    page.sleep(0.3)
    subs = page.js("return window.__submits")
    page.expect("Enter in the search field: canceled", len(subs) == len(forms) + 1 and subs[-1]["prevented"], submits=subs[-1:])
    page.eq("same document", page.js("return window.__marker"), 1)
    page.url_kept("no navigation", before)


@check("examples-forms-nojs", "/examples", javascript=False)
def examples_forms_nojs(page):
    """With the page's JavaScript off (Chrome and Firefox; skipped in Safari), each example form,
    filled in, is submitted with a real click on its submit button, and the search form with Enter:
    none navigates, so nothing typed (a password included) reaches the URL. Every mockup form has
    method="dialog" (static criterion 9), whose submit does nothing outside a <dialog>; no script
    cancels anything here, so the document, URL and history must stay."""
    page.js("window.__marker = 1;")
    before = page.url()
    forms = page.js(HOSTS + r"""
      const out = [];
      hosts.forEach((h, i) => {
        h.root.querySelectorAll('form').forEach((f, k) => {
          for (const el of f.elements) {
            if (el.type === 'email') el.value = 'sam@example.com';
            else if (el.localName === 'textarea' || el.type === 'text' || el.type === 'password' || el.type === 'search') el.value ||= 'Example text';
            else if (el.localName === 'select' && !el.value) el.selectedIndex = 1;
          }
          if (f.querySelector('button[type=submit]')) out.push([i, k, h.id]);
        });
      });
      return out;""")
    page.expect("the mockups have forms with a submit button", len(forms) > 0)
    page.note(f"{len(forms)} forms with a submit button")
    for i, k, ex in forms:
        pt = shadow_point(page, f"hosts[{i}].root.querySelectorAll('form')[{k}].querySelector('button[type=submit]')")
        page.click_at(*pt)
        page.sleep(0.3)
        page.eq(f"{ex}: same document after its submit button", page.js("return window.__marker"), 1)
    pt = shadow_point(page, "hosts.find(h => h.id === 'search-results').root.querySelector('input[type=search]')")
    page.click_at(*pt)
    page.key("ENTER")
    page.sleep(0.3)
    page.eq("same document after Enter in the search field", page.js("return window.__marker"), 1)
    page.url_kept("no navigation", before)


@check("examples-links", "/examples")
def examples_links(page):
    """Every visible link in every example goes nowhere, clicked and with Enter: the click is
    canceled and the document, URL and history stay."""
    page.js("window.__marker = 1;")
    before = page.url()
    links = page.js(HOSTS + r"""
      window.__clicks = [];
      const out = [];
      hosts.forEach((h, i) => {
        h.root.addEventListener('click', e => { { const a = e.target.closest('a'); if (a) __clicks.push([a.textContent.trim(), e.defaultPrevented]); } });
        h.root.querySelectorAll('a[href]').forEach((a, k) => { if (a.getClientRects().length && !a.closest('details:not([open])') && getComputedStyle(a).pointerEvents !== 'none') out.push([i, k, h.id, a.textContent.trim()]); });
      });
      return out;""")
    for i, k, ex, text in links:
        pt = shadow_point(page, f"hosts[{i}].root.querySelectorAll('a[href]')[{k}]")
        page.click_at(*pt)
        page.sleep(0.05)
    page.js(HOSTS + "hosts[0].root.querySelector('a[href]').focus()")
    page.key("ENTER")
    page.sleep(0.3)
    clicks = page.js("return window.__clicks")
    page.eq("every link click (and the Enter) seen", len(clicks), len(links) + 1, missed=[l[3] for l in links if l[3] not in [c[0] for c in clicks]], clicks=clicks)
    page.expect("every one canceled", all(c[1] for c in clicks), clicks=clicks)
    page.eq("same document", page.js("return window.__marker"), 1)
    page.url_kept("no navigation", before)


# The deep-linked example: its section's and its chapter label's top, its scroll-margin-top, a femto
# spacing in px (read from a hidden probe), and whether the page is scrolled to its end.
DEEP_LINKED = """
const s = document.getElementById(location.hash.slice(1)), chapter = s.querySelector(':scope > header .chapter');
const probe = document.createElement('div');
probe.style.cssText = 'position: absolute; visibility: hidden; width: var(--femto-spacing)';
document.body.append(probe);
const spacing = probe.getBoundingClientRect().width;
probe.remove();
const root = document.documentElement;
return {top: s.getBoundingClientRect().top, chapter: chapter.getBoundingClientRect().top,
        margin: parseFloat(getComputedStyle(s).scrollMarginTop), spacing, y: scrollY,
        atEnd: Math.ceil(scrollY + innerHeight) >= root.scrollHeight - 1};
"""


def examples_deep_link(page):
    page.wait("the deep link scrolled the page", "scrollY > 0", 2)
    page.sleep(0.3)   # the load's scroll has settled
    r = page.js(DEEP_LINKED)
    if r["atEnd"]:
        page.expect("at the page's end, the section is at least a femto spacing below the top", r["top"] >= r["spacing"] - 1, **r)
        page.note("the page is scrolled to its end, so the section may sit lower")
    else:
        page.expect("the section is a femto spacing below the top (within 1 px)", abs(r["top"] - r["spacing"]) <= 1, **r)
    page.expect("its chapter label is clear of the top edge", r["chapter"] >= r["spacing"] - 1, **r)
    page.expect("the section's scroll-margin-top is a femto spacing", r["spacing"] > 0 and abs(r["margin"] - r["spacing"]) <= 0.5, **r)
    page.eq("the URL is the deep link's", page.js("return location.pathname + location.hash"), page.route)


@check("examples-deep-link", ("/examples#every-element", "/examples#sign-in", "/examples#dashboard"))
def examples_deep_link_large(page):
    """A link to an example (the footer's #sign-in and #dashboard, the index's, the docs' "Used
    in") lands its section a femto spacing (--femto-spacing, its scroll-margin-top in examples.css)
    below the top of the viewport, within 1 px, with its chapter label clear of the top edge; the
    page has no sticky header and no scroll padding. At the page's end a section may sit lower, which
    the note says. The URL keeps the hash."""
    examples_deep_link(page)


@check("examples-deep-link-small", ("/examples#every-element", "/examples#sign-in", "/examples#dashboard"), width=375, height=812)
def examples_deep_link_small(page):
    """The same at 375 x 812, where a femto spacing is smaller."""
    examples_deep_link(page)


DIALOG = "hosts.find(h => h.id === 'confirm-dialog').root"


@check("examples-dialog", "/examples")
def examples_dialog(page):
    """The confirmation dialog: the opener's click shows it as a modal with focus inside; Escape, the
    close button, Cancel, Delete project and a click on the backdrop each close it, and focus goes
    back to the opener; a click on its text keeps it open."""
    state = f"(() => {{ {HOSTS} const r = {DIALOG}; const d = r.querySelector('dialog'); return {{open: d.open, modal: d.matches(':modal'), focus: r.activeElement?.outerHTML.slice(0, 60) ?? null, opener: r.activeElement === r.querySelector('[aria-controls]')}}; }})()"

    def open_it(label):
        page.click_at(*shadow_point(page, f"{DIALOG}.querySelector('[aria-controls]')"))
        s = page.wait(f"{label}: open as a modal, focus inside", f"(() => {{ const s = {state}; return s.open && s.modal && !s.opener && s.focus ? s : null; }})()")
        return s

    def closed(label):
        page.wait(f"{label}: closed, focus on the opener", f"(() => {{ const s = {state}; return !s.open && s.opener; }})()")

    open_it("first open")
    page.key("ESCAPE")
    closed("Escape")
    for what, expr in [("close button", "[rel=prev]"), ("Cancel", "footer button:first-of-type"), ("Delete project", "footer button:last-of-type")]:
        open_it(f"before {what}")
        pt = page.js(HOSTS + f"const b = {DIALOG}.querySelector('dialog {expr}'); const r = b.getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)];")
        page.click_at(*pt)
        closed(what)
    open_it("before text")
    pt = page.js(HOSTS + f"const p = {DIALOG}.querySelector('dialog p'); const r = p.getBoundingClientRect(); return [Math.round(r.left + 5), Math.round(r.top + r.height / 2)];")
    page.click_at(*pt)
    page.sleep(0.3)
    page.expect("a click on its text keeps it open", page.js(f"return {state}.open"))
    page.click_at(5, 5)
    closed("backdrop")


@check("examples-dropdown", "/examples")
def examples_dropdown(page):
    """The navigation bar's Account dropdown opens on a click on its summary, shows its menu, and
    closes on a click outside it."""
    nav = "hosts.find(h => h.id === 'navigation-bar').root.querySelector('details.dropdown')"
    page.click_at(*shadow_point(page, f"{nav}.querySelector('summary')"))
    page.wait("open", f"(() => {{ {HOSTS} const d = {nav}; return d.open && d.querySelector('ul').getBoundingClientRect().height > 50; }})()")
    page.click_at(5, 5)
    page.wait("closed by a click outside", f"(() => {{ {HOSTS} return !{nav}.open; }})()")


@check("examples-fit", "/examples", width=375, height=812)
def examples_fit(page):
    """At 375 px the page does not scroll sideways, and every element of every example (outside a
    scrolling .overflow-auto) stays inside its frame's border box."""
    r = page.js(HOSTS + r"""
      const out = [];
      for (const h of hosts) {
        const box = h.frame.getBoundingClientRect();
        for (const e of h.root.querySelectorAll('*')) {
          if (e.closest('.overflow-auto') && !e.matches('.overflow-auto')) continue;
          if (!e.getClientRects().length) continue;
          const r = e.getBoundingClientRect();
          if (r.right > box.right + 0.5 || r.left < box.left - 0.5) out.push({id: h.id, el: e.outerHTML.slice(0, 80), left: r.left, right: r.right, box: [box.left, box.right]});
        }
      }
      const wider = [];
      for (const h of hosts) for (const e of [h.inner, ...h.root.querySelectorAll("*")]) {
        if (e.closest(".overflow-auto") && !e.matches(".overflow-auto") || !e.getClientRects().length) continue;
        if (e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflowX === "visible" && e.clientWidth > 0) wider.push({id: h.id, el: (e.outerHTML ?? "host").slice(0, 60), scroll: e.scrollWidth, client: e.clientWidth});
      }
      return {scroll: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth, Math.round(document.querySelector("body > header").getBoundingClientRect().width)), width: innerWidth, out: out.slice(0, 20), n: out.length, wider};
    """)
    page.expect("no sideways scroll", r["scroll"] <= r["width"], **{k: r[k] for k in ("scroll", "width")})
    page.eq("every element inside its frame", r["n"], 0, out=r["out"])
    page.note(f"boxes whose content overhangs them (femto nav margins, hidden tooltips): {r['wider']}")


# Records, in every animation frame of the first second, the first frame in which the inner hosts
# exist: their computed color-scheme and data-theme, an h3's color, and whether their femto sheet
# is applied (cssRules), so a check can see what the first paint showed.
FIRST_FRAME_PRELOAD = """() => {
  window.__exFrames = [];
  const t0 = performance.now();
  const tick = () => {
    const frames = [...document.querySelectorAll('div[data-example]')];
    if (frames.length) {
      const hosts = frames.map(f => f.shadowRoot?.firstElementChild).filter(Boolean);
      window.__exFrames.push({at: performance.now(), n: hosts.length, done: document.readyState,
        schemes: [...new Set(hosts.map(h => getComputedStyle(h).colorScheme))],
        themes: [...new Set(hosts.map(h => h.getAttribute('data-theme')))],
        sheets: hosts.map(h => h.shadowRoot?.styleSheets[0]?.cssRules.length ?? 0).every(n => n > 100),
        h3: (() => { const h = hosts.find(x => x.shadowRoot?.querySelector('h3')); return h ? getComputedStyle(h.shadowRoot.querySelector('h3')).color : null; })()});
    }
    if (performance.now() - t0 < 1000) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}"""


@check("examples-first-frame", "/examples", storage={"femtoColorScheme": '"dark"'}, preload=FIRST_FRAME_PRELOAD)
def examples_first_frame(page):
    """With a stored dark choice on a light OS, the first animation frame that has the examples
    already shows them dark (color-scheme dark on every inner host) with femto's sheet applied, and
    no color transition runs after load."""
    page.wait("frames recorded", "window.__exFrames && window.__exFrames.length > 0", 3)
    frames = page.js("return window.__exFrames")
    first = frames[0]
    page.note(f"first frame with examples: {first}; last: {frames[-1]}")
    page.eq("first frame: every inner host dark", first["schemes"], ["dark"], first=first)
    page.expect("first frame: femto applied in every root", first["sheets"], first=first)
    running = page.js(HOSTS + "return hosts.flatMap(h => h.root.getAnimations()).filter(a => a.constructor.name === 'CSSTransition').length")
    page.eq("no transition running after load", running, 0)


@check("examples-first-frame-cold", "/examples", preload=FIRST_FRAME_PRELOAD, cold=True)
def examples_first_frame_cold(page):
    """With the HTTP cache emptied, the first animation frame that has the examples already has
    femto's sheet applied in every inner root, and no transition runs after load (no unstyled
    flash)."""
    page.wait("frames recorded", "window.__exFrames && window.__exFrames.length > 0", 3)
    frames = page.js("return window.__exFrames")
    page.note(f"first frame with examples: {frames[0]}")
    page.expect("first frame: femto applied in every root", frames[0]["sheets"], first=frames[0])
    running = page.js(HOSTS + "return hosts.flatMap(h => h.root.getAnimations()).filter(a => a.constructor.name === 'CSSTransition').length")
    page.eq("no transition running after load", running, 0)


# --- The folded markup, Copy as page, the theme color and the newer examples ----------------------

ROOT = Path(__file__).resolve().parents[2]


def theme_files():
    """femto's css/themes/ files, vendored: {color: its --femto-primary-background}, azure's included."""
    out = {}
    for p in sorted((ROOT / "site/vendor/femto/css/themes").glob("*.css")):
        m = re.search(r"--femto-primary-background:\s*([^;]+);", p.read_text())
        out[p.stem] = m.group(1).strip().lower()
    return out


@check("examples-fold", "/examples")
def examples_fold(page):
    """Each example's markup is folded under it: a section.example's children are its <header>, its
    div[data-example] and one <details>, closed on load, whose summary reads "HTML" and whose only
    other child is the div.code with its copy button and the sample, not rendered while closed
    (checkVisibility(): Chrome hides a closed details' content with content-visibility). A
    click on the first and the last summary opens it and shows the sample, and the copy button inside
    copies exactly that sample's text."""
    r = page.js(r"""return [...document.querySelectorAll('main section.example')].map(s => {
      const d = s.querySelector(':scope > details');
      return {id: s.id, children: [...s.children].map(c => c.localName + (c.hasAttribute('data-example') ? '[data-example]' : '')),
              open: d ? d.open : null, summary: d?.querySelector(':scope > summary')?.textContent ?? null,
              inside: d ? [...d.children].map(c => c.localName + (c.classList.contains('code') ? '.code' : '')) : null,
              copy: !!d?.querySelector(':scope > .code > button[data-copy-link]'), code: !!d?.querySelector(':scope > .code > pre > code'),
              shown: d?.querySelector('pre')?.checkVisibility() ?? null};
    });""")
    page.expect("the page has examples", len(r) > 0)
    for x in r:
        page.eq(f"{x['id']}: a header, the frame and a details", x["children"], ["header", "div[data-example]", "details"], **x)
        page.expect(f"{x['id']}: closed, its summary HTML, the code block alone after it",
                    x["open"] is False and x["summary"] == "HTML" and x["inside"] == ["summary", "div.code"] and x["copy"] and x["code"], **x)
        page.eq(f"{x['id']}: the sample is not rendered while closed", x["shown"], False)
    page.js(COPY_SPY)
    summaries = page.find_all("main section.example > details > summary")
    for n, summary in ((1, summaries[0]), (len(summaries), summaries[-1])):
        page.click(summary)
        page.wait(f"summary {n}: open, the sample shown", "arguments[0].parentElement.open && "
                  "arguments[0].parentElement.querySelector('pre').checkVisibility()", 1, args=(summary,))
        button = page.js("return arguments[0].parentElement.querySelector('button[data-copy-link]')", summary)
        code = page.js("return arguments[0].parentElement.querySelector('pre code').textContent", summary)
        page.js("window.__bhCopied.length = 0")
        page.click(button)
        page.wait(f"summary {n}: its copy button copies", "window.__bhCopied.length === 1", 1)
        page.eq(f"summary {n}: exactly its sample", page.js("return window.__bhCopied[0].text"), code)


@check("examples-nojs", "/examples", javascript=False)
def examples_nojs(page):
    """With the page's JavaScript off (skipped in Safari), every example still renders, its two roots
    declarative with femto's sheet applied, each sample is folded in its closed <details>, and the
    theme select and every Copy as page button, which do nothing without JavaScript, are not
    rendered (examples.css, scripting: none)."""
    r = page.js(r"""const frames = [...document.querySelectorAll('div[data-example]')];
      return {frames: frames.length,
              styled: frames.filter(f => f.shadowRoot?.firstElementChild?.shadowRoot?.styleSheets[0]?.cssRules.length > 100).length,
              closed: document.querySelectorAll('main section.example > details:not([open])').length,
              select: document.querySelector('p[data-examples-theme]')?.getClientRects().length ?? null,
              buttons: [...document.querySelectorAll('button[data-copy-page]')].map(b => b.getClientRects().length)};""")
    page.expect("the page has examples", r["frames"] > 0)
    page.eq("every example styled by femto", r["styled"], r["frames"])
    page.eq("every sample folded", r["closed"], r["frames"])
    page.eq("the theme select is not rendered", r["select"], 0)
    page.eq("no Copy as page button is rendered, one in each example", r["buttons"], [0] * r["frames"])


# femto's starter template as the docs' Quick start shows it: the text of the code block after the
# "Starter template" heading on /docs.
STARTER = r"""
const doc = new DOMParser().parseFromString(await (await fetch('/docs')).text(), 'text/html');
const h2 = [...doc.querySelectorAll('h2')].find(h => h.textContent.trim() === 'Starter template');
return h2 ? h2.parentElement.querySelector('pre code').textContent : null;
"""


def page_of(template, name, markup, color):
    """What Copy as page copies: the starter template with the example's name for its title, the
    chosen theme's link (none for azure) after femto's, and the sample, its /vendor/femto/ paths made
    the template's jsDelivr ones, in place of its <h1>, each line indented as the <h1> is but a
    <pre>'s lines after its first."""
    link = re.search(r'^( *)<link rel="stylesheet" href="(https://[^"]+/)dist/femto\.min\.css">$', template, re.M)
    indent, cdn = link.group(1), link.group(2)
    t = template[:link.end()] + (f'\n{indent}<link rel="stylesheet" href="{cdn}css/themes/{color}.css">' if color != "azure" else "") + template[link.end():]
    t = t.replace("<title>Hello, world!</title>", f"<title>{name}</title>", 1)
    h1 = re.search(r"^( *)<h1>Hello, world!</h1>$", t, re.M)
    lines, pre = [], False
    for line in markup.replace('"/vendor/femto/', f'"{cdn}').split("\n"):
        lines.append(line if pre or not line else h1.group(1) + line)
        opens, closes = bool(re.search(r"<pre[\s>]", line)), "</pre>" in line
        pre = True if opens and not closes else False if closes else pre
    return t[:h1.start()] + "\n".join(lines) + t[h1.end():]


# A copied page read as a browser reads it: its head, and its <main>'s content against the sample's.
READ_PAGE = r"""
const [text, sample, cdn] = arguments;
const d = new DOMParser().parseFromString(text, 'text/html');
const t = document.createElement('template'); t.innerHTML = sample.replaceAll('"/vendor/femto/', '"' + cdn);
const main = d.querySelectorAll('body > main.container');
return {doctype: d.doctype?.name ?? null, lang: d.documentElement.lang, charset: d.querySelector('head > meta[charset]')?.getAttribute('charset') ?? null,
        viewport: d.querySelector('head > meta[name=viewport]')?.content ?? null, scheme: d.querySelector('head > meta[name=color-scheme]')?.content ?? null,
        title: d.title, links: [...d.querySelectorAll('head > link[rel=stylesheet]')].map(l => l.getAttribute('href')),
        mains: main.length, body: [...d.body.children].map(c => c.localName),
        same: main.length === 1 && main[0].innerHTML.replace(/\s+/g, ' ').trim() === t.innerHTML.replace(/\s+/g, ' ').trim(),
        pre: main.length ? [...main[0].querySelectorAll('pre')].map(p => p.textContent) : null,
        samplePre: [...t.content.querySelectorAll('pre')].map(p => p.textContent)};
"""

# Records the button's text and the status line on every change, and the click, with performance.now(),
# and the button's width at the click and at each change.
COPY_PAGE_TIMELINE = r"""
const b = arguments[0];
window.__bhPage = [];
window.__bhPageWidths = [];
const t = () => Math.round(performance.now());
const w = () => __bhPageWidths.push(Math.round(b.getBoundingClientRect().width * 10) / 10);
const status = () => document.querySelector('body > p.visually-hidden[role=status]')?.textContent ?? null;
new MutationObserver(() => { __bhPage.push([t(), b.textContent, status()]); w(); }).observe(b, {childList: true, characterData: true, subtree: true});
b.addEventListener('click', () => { __bhPage.push([t(), 'click']); w(); }, true);
"""


def choose_theme(page, color):
    from selenium.webdriver.support.select import Select
    Select(page.el("p[data-examples-theme] select")).select_by_value(color)


@check("examples-copy-page", "/examples")
def examples_copy_page(page):
    """Each example's Copy as page button (button[data-copy-page] in its header, "Copy as page")
    copies exactly its sample in femto's starter template, as the docs' Quick start shows the
    template (read from /docs): the example's name (its h2) for the title, the sample in place of the
    <h1>, indented as the <h1> is but for a <pre>'s later lines, and the page's /vendor/femto/ paths
    (the All theme colors example's) as the template's jsDelivr ones. Read back as a document, the
    copy has the template's doctype, lang, charset, viewport, color-scheme and femto link, one
    main.container holding the sample, and each <pre>'s text unchanged. With jade chosen in the theme
    select, the copy also links jade's css/themes/ file right after femto. The button reads "Copied"
    within 100 ms of a click and "Copy as page" again 900 to 1500 ms later, at the width it had, so
    it does not move under the pointer; the page's one status region, site.js's
    (body > p.visually-hidden[role=status]), says "Copied" and then nothing. The URL does not change."""
    page.js(COPY_SPY)
    template = page.ajs(STARTER)
    page.expect("the docs' starter template has its <h1> and title", template and "<h1>Hello, world!</h1>" in template
                and "<title>Hello, world!</title>" in template, template=template)
    cdn = re.search(r'href="(https://[^"]+/)dist/femto\.min\.css"', template).group(1)
    buttons = page.find_all("main section.example > header > button[data-copy-page]")
    page.eq("a Copy as page button in each example", len(buttons), page.js("return document.querySelectorAll('main section.example').length"))
    url = page.url()
    info = page.js("""return arguments[0].map(b => { const s = b.closest('section');
      return {id: s.id, text: b.textContent, name: s.querySelector(':scope > header h2').textContent.trim(),
              sample: s.querySelector(':scope > details pre code').textContent}; });""", buttons)
    for k, (button, x) in enumerate(zip(buttons, info)):
        page.eq(f"{x['id']}: the button reads Copy as page", x["text"], "Copy as page")
        if k == len(buttons) - 1:
            # The region empties 1 s after the latest copy, so the last one starts from an empty region.
            # A copy while it still says Copied empties it and writes Copied a frame later
            # (copy-announce-twice), so the wait starts once that frame has passed.
            page.sleep(0.1)
            page.wait("the status region is empty before the last copy",
                      "document.querySelector('body > p.visually-hidden[role=status]').textContent === ''", 2)
            page.js(COPY_PAGE_TIMELINE, button)
        page.click(button)
        page.wait(f"{x['id']}: copied", f"window.__bhCopied.length === {k + 1}", 1)
        text = page.js(f"return window.__bhCopied[{k}].text")
        page.eq(f"{x['id']}: exactly its sample in the starter template", text, page_of(template, x["name"], x["sample"], "azure"))
        d = page.js(READ_PAGE, text, x["sample"], cdn)
        page.expect(f"{x['id']}: read back, the template's head and one main.container holding the sample",
                    d["doctype"] == "html" and d["lang"] == "en" and d["charset"] == "utf-8"
                    and d["viewport"] == "width=device-width, initial-scale=1" and d["scheme"] == "light dark"
                    and d["title"] == x["name"] and d["links"] == [cdn + "dist/femto.min.css"] and d["mains"] == 1
                    and d["body"] == ["main"] and d["same"], **d)
        page.eq(f"{x['id']}: each <pre>'s text unchanged", d["pre"], d["samplePre"])
    page.wait("the last button reverts", "window.__bhPage.length >= 3 && arguments[0].textContent === 'Copy as page'", 2.5, args=(buttons[-1],))
    tl = page.js("return window.__bhPage")
    page.eq("the steps: click, Copied, Copy as page", [x[1:] for x in tl], [["click"], ["Copied", "Copied"], ["Copy as page", ""]], timeline=tl)
    page.expect("Copied within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
    page.expect("back 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
    widths = page.js("return window.__bhPageWidths")
    page.expect("the button keeps its width while it reads Copied", len(widths) >= 3 and max(widths) - min(widths) <= 0.5, widths=widths)
    page.eq("one status region on the page", page.js("return document.querySelectorAll('[role=status]').length"), 1)
    choose_theme(page, "jade")
    for eid in ("sign-in", "all-themes"):
        k = len(buttons) + (eid == "all-themes")
        x = next(i for i in info if i["id"] == eid)
        page.click(buttons[info.index(x)])
        page.wait(f"{eid}, jade: copied", f"window.__bhCopied.length === {k + 1}", 1)
        text = page.js(f"return window.__bhCopied[{k}].text")
        page.eq(f"{eid}, jade: jade's link after femto's", text, page_of(template, x["name"], x["sample"], "jade"))
        page.eq(f"{eid}, jade: the two links", page.js(READ_PAGE, text, x["sample"], cdn)["links"],
                [cdn + "dist/femto.min.css", cdn + "css/themes/jade.css"])
    page.url_kept("no navigation", url)


# Records every change of the status region's text, and each click on the two buttons, with
# performance.now() times.
ANNOUNCE_TIMELINE = r"""
const [code, page] = arguments;
window.__bhAnnounce = [];
const t = () => Math.round(performance.now());
const region = document.querySelector('body > p.visually-hidden[role=status]');
new MutationObserver(() => __bhAnnounce.push([t(), region.textContent])).observe(region, {childList: true, characterData: true, subtree: true});
code.addEventListener('click', () => __bhAnnounce.push([t(), 'click code']), true);
page.addEventListener('click', () => __bhAnnounce.push([t(), 'click page']), true);
return !!region;
"""


@check("copy-announce-twice", "/examples")
def copy_announce_twice(page):
    """Two copies 500 ms apart are both announced. The Sign in example's code copy button (site.js),
    then 500 ms later its Copy as page button (examples.js), which share the page's one status region
    (body > p.visually-hidden[role=status]): the region says "Copied" within 100 ms of the first
    click; within 100 ms of the second it is emptied and says "Copied" again, a change a screen
    reader announces (the same text written over itself would be none); and it is emptied once, 900
    to 1500 ms after the second click, not 1 s after the first. Timed in the page with a
    MutationObserver on the region."""
    page.js(COPY_SPY)
    code = page.js("const s = document.getElementById('sign-in'); s.querySelector(':scope > details').open = true;"
                   " const b = s.querySelector(':scope > details button[data-copy-link]'); b.scrollIntoView({block: 'center'}); return b;")
    copy_page = page.el("#sign-in > header > button[data-copy-page]")
    page.expect("the page has its status region", page.js(ANNOUNCE_TIMELINE, code, copy_page))
    page.click(code, scroll=False)
    page.sleep(0.5)
    page.click(copy_page)
    page.wait("both copied", "window.__bhCopied.length === 2", 1)
    page.sleep(1.8)   # past the 1 s after the second click, and a later, wrong step would show by now
    tl = page.js("return window.__bhAnnounce")
    clicks = [x[0] for x in tl if x[1].startswith("click")]
    texts = [x for x in tl if not x[1].startswith("click")]
    steps = [x[1] for k, x in enumerate(texts) if k == 0 or x[1] != texts[k - 1][1]]
    page.eq("two clicks", len(clicks), 2, timeline=tl)
    page.expect("the clicks are 300 to 900 ms apart", 300 <= clicks[1] - clicks[0] <= 900, timeline=tl)
    page.eq("the region's steps: Copied, emptied, Copied, emptied", steps, ["Copied", "", "Copied", ""], timeline=tl)
    first = next(x[0] for x in texts if x[1] == "Copied")
    again = next(x[0] for x in texts if x[1] == "Copied" and x[0] >= clicks[1])
    end = texts[-1][0]
    page.expect("the first Copied within 100 ms of the first click", first - clicks[0] <= 100, timeline=tl)
    page.expect("Copied again within 100 ms of the second click", again - clicks[1] <= 100, timeline=tl)
    page.expect("emptied 900 to 1500 ms after the second click", 900 <= end - clicks[1] <= 1500, ms=end - clicks[1], timeline=tl)


# Every inner root's theme links and its host's --femto-primary-background, and each of the All theme
# colors example's own roots' links and colors.
THEME_STATE = HOSTS + r"""
const themes = (root) => [...root.children].filter(e => e.localName === 'link' && e.getAttribute('href').includes('/css/themes/'));
const color = (host) => getComputedStyle(host).getPropertyValue('--femto-primary-background').trim().toLowerCase();
const own = hosts.find(h => h.id === 'all-themes').root.querySelectorAll('.grid > div');
return {inner: hosts.map(h => ({id: h.id, second: h.root.children[1]?.outerHTML.slice(0, 90), themes: themes(h.root).map(l => [l.outerHTML, !!l.sheet]),
                                color: color(h.inner)})),
        own: [...own].map(d => ({links: themes(d.shadowRoot).map(l => l.getAttribute('href')), color: color(d)})),
        page: color(document.documentElement), query: location.search};
"""


@check("examples-theme", "/examples")
def examples_theme(page):
    """The theme select (p[data-examples-theme] select) offers femto's 20 colors, azure selected, in
    the docs' Theme picker's order (read from /docs), each labeled with its name capitalized; the
    All theme colors example's 20 roots follow the same order. On load no inner root links a theme, and every inner host has azure's primary
    background. Choosing jade links <link rel="stylesheet" href="/vendor/femto/css/themes/jade.css">
    right after femto's in every inner root, loaded, and gives every inner host jade's primary
    background (its css/themes/ file's); red then replaces jade's link with red's, one theme link a
    root; and azure removes it, back to azure's color. Throughout, the page itself keeps azure, each of
    the All theme colors example's 20 roots keeps its own theme file and color, and the URL gets no
    ?theme= and no new history entry (Decision 8)."""
    files = theme_files()
    opts = page.js("return [...document.querySelectorAll('p[data-examples-theme] select option')].map(o => [o.value, o.textContent.trim(), o.selected])")
    want = page.ajs(PICKER_ORDER)
    page.eq("the picker's colors are femto's 20", sorted(want), sorted(files))
    page.eq("the 20 colors, in the picker's order", [o[0] for o in opts], want)
    page.eq("each labeled with its name", [o[1] for o in opts], [c.capitalize() for c in want])
    page.eq("azure selected", [o[0] for o in opts if o[2]], ["azure"])
    url = page.url()
    s = page.js(THEME_STATE)
    own = [x["links"] for x in s["own"]]
    page.eq("on load: no theme link in any inner root", [x["themes"] for x in s["inner"]], [[]] * len(s["inner"]))
    page.eq("on load: every inner host azure", {x["color"] for x in s["inner"]}, {files["azure"]})
    page.eq("the All theme colors example: 20 roots of the 20 colors, in the picker's order", [h[0].rsplit("/", 1)[1][:-4] for h in own], want)

    def holds(color):
        link = f'<link rel="stylesheet" href="/vendor/femto/css/themes/{color}.css">'
        page.wait(f"{color}: its link loaded in every inner root",
                  f"(() => {{ const s = (() => {{ {THEME_STATE} }})(); return s.inner.every(x => x.themes.length === 1 && x.themes[0][1] "
                  "&& x.themes[0][0] === arguments[0] && x.second === arguments[0]); })()", 3, args=(link,))
        s = page.js(THEME_STATE)
        page.eq(f"{color}: every inner host's primary background is {color}'s", {x["color"] for x in s["inner"]}, {files[color]})
        return s

    def kept(s, label):
        page.eq(f"{label}: the page keeps azure", s["page"], files["azure"])
        page.eq(f"{label}: the All theme colors roots keep their links", [x["links"] for x in s["own"]], own)
        page.eq(f"{label}: and their colors", [x["color"] for x in s["own"]], [files[h[0].rsplit("/", 1)[1][:-4]] for h in own])
        page.eq(f"{label}: no ?theme=", s["query"], "")

    choose_theme(page, "jade")
    kept(holds("jade"), "jade")
    choose_theme(page, "red")
    kept(holds("red"), "red")
    choose_theme(page, "azure")
    page.wait("azure: no theme link in any inner root",
              f"(() => {{ const s = (() => {{ {THEME_STATE} }})(); return s.inner.every(x => x.themes.length === 0); }})()", 3)
    s = page.js(THEME_STATE)
    page.eq("azure: every inner host azure again", {x["color"] for x in s["inner"]}, {files["azure"]})
    kept(s, "azure")
    page.url_kept("no navigation, no new entry", url)


EVERY_ELEMENT = ["h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "section", "p", "a[href]", "a.secondary", "a.contrast", "strong",
                 "b", "em", "i", "u", "s", "del", "ins", "mark", "small", "abbr[title]", "sub", "sup", "code", "kbd", "samp",
                 "var", "dfn", "q", "cite", "time", "address", "hr", "ul ul", "ol", "dl dt", "dl dd", "blockquote footer cite",
                 "figure img", "figure figcaption", "pre code", ".overflow-auto table.striped", "thead", "tbody", "tfoot",
                 "th[scope=row]", ".grid", "form", "fieldset legend", "select:not([multiple])", "select[multiple]",
                 "textarea", "input[type=checkbox]:not([role])", "input[type=radio]", "input[type=checkbox][role=switch]",
                 "input[aria-invalid=true] + small", "input[aria-invalid=false] + small", "input[disabled]", "input[readonly]",
                 "label[aria-disabled=true]", "[role=group] input", "form[role=search] input[type=search]", "input[type=submit]",
                 "input[type=reset]", "button[type=submit]", "button.secondary", "button.contrast", "button.outline",
                 "button[disabled]", "button[aria-busy=true]", "a[role=button]", "details[open] > summary",
                 "summary[role=button]", "details.dropdown > summary + ul", "article > header", "article > footer",
                 "dialog > article > header > button[rel=prev]", "dialog > article > footer > button", "progress[value]",
                 "progress:not([value])", "p[aria-busy=true]", "[data-tooltip]", "nav ul + ul"]
INPUT_TYPES = ["text", "email", "password", "number", "tel", "url", "date", "time", "datetime-local", "month", "week",
               "color", "search", "file", "range", "checkbox", "radio", "submit", "reset"]

NEWER = HOSTS + r"""
const root = (id) => hosts.find(h => h.id === id).root;
const kids = (el) => [...el.children].map(c => c.localName + [...c.classList].map(x => '.' + x).join(''));
const side = (a, b) => { const x = a.getBoundingClientRect(), y = b.getBoundingClientRect(); return x.right <= y.left && Math.abs(x.top - y.top) < 1; };
const every = root('every-element');
const land = root('landing-page'), docs = root('docs-layout'), out = root('checkout'), all = root('all-themes');
const dgrid = docs.children[1], cgrid = out.children[2];
const grids = [...all.children].filter(e => e.matches('div.grid'));
return {
  every: {missing: arguments[0].filter(s => !every.querySelector(s)), types: [...new Set([...every.querySelectorAll('input')].map(i => i.getAttribute('type')))]},
  landing: {kids: kids(land), nav: kids(land.children[1].querySelector(':scope > nav')), hero: kids(land.children[1]),
            ctas: land.children[1].querySelectorAll(':scope > p > a[role=button]').length,
            features: [...land.querySelectorAll('section > .grid > article')].map(a => a.querySelector('h4')?.textContent ?? null),
            footer: !!land.lastElementChild.querySelector(':scope > nav > ul + ul')},
  docs: {kids: kids(docs), grid: kids(dgrid), groups: dgrid.querySelectorAll('aside > nav > details[open] > summary + ul').length,
         display: [...dgrid.querySelectorAll('aside nav ul, aside nav li')].map(e => getComputedStyle(e).display),
         current: dgrid.querySelector('aside nav a[aria-current=page]')?.textContent ?? null,
         article: !!dgrid.querySelector('article > hgroup > h3') && !!dgrid.querySelector('article > footer > nav'),
         side: side(dgrid.children[0], dgrid.children[1])},
  checkout: {kids: kids(out), grid: kids(cgrid), legends: [...cgrid.children[0].querySelectorAll(':scope > fieldset')].map(f => f.firstElementChild?.localName === 'legend' ? f.firstElementChild.textContent : null),
             radios: [...new Set([...cgrid.querySelectorAll('input[type=radio]')].map(i => i.name))], submit: !!cgrid.children[0].querySelector('button[type=submit]'),
             table: [...cgrid.querySelectorAll('article table > *')].map(e => e.localName + ':' + e.rows.length), side: side(cgrid.children[0], cgrid.children[1])},
  all: {kids: kids(all).length, grids: grids.map(g => g.children.length),
        hosts: grids.flatMap(g => [...g.children]).map(d => {
          const r = d.shadowRoot;
          if (!r) return null;
          const cards = [...r.querySelectorAll('.grid > article')];
          return {links: [...r.children].slice(0, 2).map(l => l.localName === 'link' ? l.getAttribute('href') : null),
                  loaded: [...r.querySelectorAll('link')].every(l => l.sheet?.cssRules.length > 0), sheets: r.styleSheets.length,
                  schemes: cards.map(c => c.getAttribute('data-theme') + ':' + getComputedStyle(c).colorScheme),
                  names: cards.map(c => c.querySelector('h4')?.textContent ?? null),
                  parts: cards.map(c => ['button:not(.outline)', 'button.outline', 'a[href]', 'input[type=checkbox][role=switch]', 'progress[value]'].filter(s => c.querySelector(s)).length),
                  side: cards.length === 2 && side(cards[0], cards[1]),
                  color: getComputedStyle(d).getPropertyValue('--femto-primary-background').trim().toLowerCase()};
        })}
};
"""


@check("examples-newer", "/examples")
def examples_newer(page):
    """The index under the hero links every example, in page order, and the five examples added on
    2026-11-09 are among them, by the ids the docs link to. They hold what they show (at 1300 px). Every element
    (#every-element): every element and pattern femto styles (EVERY_ELEMENT: headings, text-level
    elements, lists, a quotation, a figure, code, a striped table, form controls of every input type
    INPUT_TYPES names, a select of each kind, valid and invalid fields with helper text, a group, a
    search form, every button style, an accordion, a dropdown, a card, a modal, progress bars, a
    loading paragraph, a tooltip and a nav; the breadcrumbs are the Navigation bar's, since a page has
    one nav named "breadcrumb", femto's hook, and html-validate's unique-landmark rule holds every
    landmark's name to one), and its "Open a modal" opens its dialog as a
    modal and Confirm closes it, focus back on the opener. Landing page (#landing-page): a header with
    a nav of two lists, the hero's hgroup and two call-to-action links, three feature cards in a grid,
    a quotation and a footer nav. Docs page (#docs-layout): a grid of an <aside>, whose nav holds two
    open groups of links (femto shows them as blocks), and an article with a heading and a footer nav,
    side by side. Checkout (#checkout): a form of four fieldsets, each led by its legend, with its own
    radio names and a submit button, beside a card whose table has a head, two body rows and three
    footer rows. All theme colors (#all-themes): ten grids of two shadow hosts, each host's own root
    linking femto.min.css then one css/themes/<color>.css, both loaded and nothing else, with a light
    and a dark card side by side (data-theme and color-scheme), each named for the color and holding a
    button, an outline button, a link, a switch and a progress bar, the host taking its theme file's
    primary background; the 20 colors are femto's css/themes/ files, once each."""
    index = page.js("""return {links: [...document.querySelectorAll('main .examples-index a')].map(a => a.getAttribute('href')),
      examples: [...document.querySelectorAll('main section.example')].map(s => '#' + s.id)};""")
    page.eq("the index links every example, in page order", index["links"], index["examples"])
    for eid in ("every-element", "landing-page", "docs-layout", "checkout", "all-themes"):
        page.expect(f"#{eid} is an example", f"#{eid}" in index["examples"])
    r = page.js(NEWER, EVERY_ELEMENT)
    page.eq("every element: nothing missing", r["every"]["missing"], [])
    page.eq("every element: every input type", sorted(t for t in r["every"]["types"] if t in INPUT_TYPES), sorted(INPUT_TYPES), types=r["every"]["types"])
    land = r["landing"]
    page.eq("landing page: header, two sections, footer", land["kids"], ["link", "header", "section", "section", "footer"])
    page.eq("landing page: the header's nav, two lists", land["nav"], ["ul", "ul"])
    page.eq("landing page: the hero", land["hero"], ["nav", "hgroup", "p"])
    page.eq("landing page: two calls to action", land["ctas"], 2)
    page.eq("landing page: three features", len([f for f in land["features"] if f]), 3, features=land["features"])
    page.expect("landing page: a footer nav", land["footer"])
    docs = r["docs"]
    page.eq("docs page: a grid", docs["kids"], ["link", "div.grid"])
    page.eq("docs page: an aside and an article", docs["grid"], ["aside", "article"])
    page.eq("docs page: two open groups of links", docs["groups"], 2)
    page.expect("docs page: the aside's lists and items are blocks", docs["display"] and set(docs["display"]) == {"block"}, display=docs["display"])
    page.eq("docs page: the current page marked", docs["current"], "Installation")
    page.expect("docs page: the article's heading and footer nav", docs["article"])
    page.expect("docs page: side by side", docs["side"])
    out = r["checkout"]
    page.eq("checkout: heading and grid", out["kids"], ["link", "hgroup", "div.grid"])
    page.eq("checkout: a form and a card", out["grid"], ["form", "article"])
    page.eq("checkout: four fieldsets, each with its legend", out["legends"], ["Contact", "Shipping address", "Delivery", "Payment"])
    page.eq("checkout: its own radio names", out["radios"], ["checkout-delivery", "checkout-payment"])
    page.expect("checkout: a submit button", out["submit"])
    page.eq("checkout: the order summary table", out["table"], ["thead:1", "tbody:2", "tfoot:3"])
    page.expect("checkout: side by side", out["side"])
    files = theme_files()
    a = r["all"]
    page.eq("all themes: an hgroup and ten grids of two", a["grids"], [2] * 10)
    hosts = a["hosts"]
    page.expect("all themes: 20 shadow hosts", len(hosts) == 20 and all(hosts), count=len(hosts))
    colors = []
    for h in hosts:
        c = h["links"][1].rsplit("/", 1)[1][:-4] if h["links"][1] else None
        colors.append(c)
        page.eq(f"{c}: femto, then its theme file", h["links"], ["/vendor/femto/dist/femto.min.css", f"/vendor/femto/css/themes/{c}.css"])
        page.expect(f"{c}: both loaded, no other sheet", h["loaded"] and h["sheets"] == 2, **h)
        page.eq(f"{c}: a light and a dark card", h["schemes"], ["light:light", "dark:dark"])
        page.eq(f"{c}: each named for the color", h["names"], [c.capitalize()] * 2)
        page.eq(f"{c}: a button, an outline button, a link, a switch and a progress bar in each", h["parts"], [5, 5])
        page.expect(f"{c}: side by side", h["side"])
        page.eq(f"{c}: its theme's primary background", h["color"], files.get(c))
    page.eq("all themes: femto's 20 colors, once each", sorted(colors), sorted(files))
    dialog = "hosts.find(h => h.id === 'every-element').root"
    state = f"(() => {{ {HOSTS} const r = {dialog}; const d = r.getElementById('every-element-dialog'); return {{open: d.open, modal: d.matches(':modal'), opener: r.activeElement === r.querySelector('[aria-controls=every-element-dialog]')}}; }})()"
    page.click_at(*shadow_point(page, f"{dialog}.querySelector('[aria-controls=every-element-dialog]')"))
    page.wait("every element: the modal opens", f"(() => {{ const s = {state}; return s.open && s.modal; }})()")
    pt = page.js(HOSTS + f"const b = {dialog}.querySelector('#every-element-dialog footer button:last-of-type'); const r = b.getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)];")
    page.click_at(*pt)
    page.wait("every element: Confirm closes it, focus on the opener", f"(() => {{ const s = {state}; return !s.open && s.opener; }})()")

