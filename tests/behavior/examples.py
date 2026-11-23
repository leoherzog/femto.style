"""Examples: the /examples page's mockups (PLAN.md Owner answers 1; examples.js). Each
mockup is vanilla femto in two declarative shadow roots: the outer one, in div[data-example], holds only
the inner host, so no page rule can match it; the inner one holds femto's stylesheet link and the
mockup, and a <details> under it, closed in the markup, holds the same markup to copy. examples.js
mirrors <html>'s data-theme onto each inner host, cancels the mockups' link clicks, opens and closes
their dialogs (where command and commandfor have not), copies an example as a page (Copy as page, in
femto's starter template), shows one alone in a modal (Pop out, which moves its frame into the
dialog and back) and links the theme color the page's select names in every inner root.
The mockups' forms have method="dialog", which keeps their submits from going anywhere."""
import re
from pathlib import Path

from behavior import COPY_SPY, PICKER_ORDER, check, expect_name

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
    """Each section.example holds one div[data-example], whose shadow root's only element is a div
    with a shadow root of its own; that root's first element is the one stylesheet link,
    /vendor/femto/dist/femto.min.css, loaded, with no other <link> or <style>; the markup after it
    is the code sample's text, node for node (whitespace collapsed), with no shadow host in it, since
    examples.js gives data-theme to the inner hosts alone; and no id repeats across the page, shadow
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
      // A live node. A live form's method="dialog", which keeps it from submitting, is not in the sample.
      const clone = (n) => {
        const c = n.cloneNode(false);
        if (n.nodeType !== 1) return c;
        if (c.localName === 'form' && c.getAttribute('method') === 'dialog') c.removeAttribute('method');
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
        out.shadowHosts = [...h.root.querySelectorAll('*')].filter(e => e.shadowRoot).length;
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
        page.eq(f"{h['id']}: no shadow host inside the example", h.get("shadowHosts"), 0)
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
// The frame's rules as they apply in a section (the Pop out dialog's own are left out), each
// selector for the frame, plain or in an :is() with the dialog's, made div[data-ref].
const frameRules = [...frameCss.cssRules].map(r => r.cssText).filter(t => t.includes('section.example') && t.includes('div[data-example]'))
  .map(t => t.replace(/(?::is\([^)]*\)|body > main > section\.example) > div\[data-example\]/g, 'div[data-ref]')).join('\n');
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
for (const h of [...hosts, ...refHosts]) await Promise.all([...h.root.querySelectorAll('link')].map(l => l.sheet ? null : new Promise(r => { l.onload = r; l.onerror = r; })));
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
    computed style equals the femto-only document's with data-theme="dark" on its inner hosts."""
    page.wait("every inner host is dark",
              "[...document.querySelectorAll('div[data-example]')].every(f => f.shadowRoot.firstElementChild.getAttribute('data-theme') === 'dark')")
    compare_styles(page, "dark")


@check("examples-scheme", "/examples")
def examples_scheme(page):
    """The inner hosts follow <html>'s data-theme: none on load (OS light, nothing stored), then dark
    with the header toggle, and none again when the toggle goes back to the OS's light (which removes
    the stored choice), and their background follows."""
    inner = "[...document.querySelectorAll('div[data-example]')].map(f => f.shadowRoot.firstElementChild)"
    background = f"getComputedStyle({inner}[0]).backgroundColor"
    page.eq("no data-theme on load", page.js(f"return {inner}.filter(h => h.hasAttribute('data-theme')).length"), 0)
    light = page.js(f"return {background}")
    page.click("button[data-scheme-toggle]")
    page.wait("toggle: every inner host dark", f"{inner}.every(h => h.getAttribute('data-theme') === 'dark')")
    dark = page.js(f"return {background}")
    page.expect("the background follows", dark != light, light=light, dark=dark)
    page.click("button[data-scheme-toggle]")
    page.wait("toggle again, to the OS's light: no inner host has data-theme", f"{inner}.every(h => !h.hasAttribute('data-theme'))")
    page.wait("the background is light again", f"{background} === arguments[0]", 2, args=(light,),
              got=page.js(f"return {background}"))


@check("examples-forms", "/examples")
def examples_forms(page):
    """Each example form, filled in, is submitted with a real click on its submit button (and the
    search form with Enter): each fires one submit event, and the document, URL and history stay. No
    script cancels the submits: every mockup form has method="dialog" (static criterion 9), whose
    submit does nothing outside a <dialog>, as examples-forms-nojs holds without JavaScript; the
    note counts the submits a handler canceled."""
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
    page.eq("same document after the submit buttons", page.js("return window.__marker"), 1)
    page.url_kept("no navigation after the submit buttons", before)
    pt = shadow_point(page, "hosts.find(h => h.id === 'search-results').root.querySelector('input[type=search]')")
    page.click_at(*pt)
    page.key("ENTER")
    page.sleep(0.3)
    subs = page.js("return window.__submits")
    page.eq("Enter in the search field submits it", [s["id"] for s in subs[len(forms):]], ["search-results"], submits=subs[-1:])
    page.eq("same document", page.js("return window.__marker"), 1)
    page.url_kept("no navigation", before)
    page.note(f"{len(subs)} submits, {sum(1 for s in subs if s['prevented'])} of them canceled")


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


# The deep-linked example: its section's and its chapter label's top, and whether the page is
# scrolled to its end.
DEEP_LINKED = """
const s = document.getElementById(location.hash.slice(1)), chapter = s.querySelector(':scope > header .chapter');
const root = document.documentElement;
return {top: s.getBoundingClientRect().top, chapter: chapter.getBoundingClientRect().top, y: scrollY,
        atEnd: Math.ceil(scrollY + innerHeight) >= root.scrollHeight - 1};
"""


def examples_deep_link(page):
    page.wait("the deep link scrolled the page", "scrollY > 0", 2)
    page.sleep(0.3)   # the load's scroll has settled
    r = page.js(DEEP_LINKED)
    if r["atEnd"]:
        page.expect("at the page's end, the section is at or below the top", r["top"] >= -1, **r)
        page.note("the page is scrolled to its end, so the section may sit lower")
    else:
        page.expect("the section is at the top of the viewport (within 1 px)", abs(r["top"]) <= 1, **r)
    page.expect("its chapter label is in view, not above the top edge", r["chapter"] >= -1, **r)
    page.eq("the URL is the deep link's", page.js("return location.pathname + location.hash"), page.route)


@check("examples-deep-link", ("/examples#navigation-bar", "/examples#sign-in", "/examples#dashboard"))
def examples_deep_link_large(page):
    """A link to an example (the footer's #sign-in and #dashboard, the index's, the docs' "Used
    in") is the browser's own fragment scroll: it lands its section at the top of the viewport,
    within 1 px, with its chapter label in view; the page has no sticky header, no scroll padding
    and no scroll margin. At the page's end a section may sit lower, which the note says. The URL
    keeps the hash."""
    examples_deep_link(page)


@check("examples-deep-link-small", ("/examples#navigation-bar", "/examples#sign-in", "/examples#dashboard"), width=375, height=812)
def examples_deep_link_small(page):
    """The same at 375 x 812, a phone's viewport."""
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


@check("examples-dialog-nojs", "/examples", javascript=False)
def examples_dialog_nojs(page):
    """With the page's JavaScript off (Chrome and Firefox; skipped in Safari), the confirmation
    dialog still opens and closes through its buttons' command and commandfor (Invoker Commands):
    its "Delete project" opener shows it as a modal (:modal), and each of its three closers (the
    header's close button and the footer's two buttons) closes it. No site script ran: the page has
    no copy status region, which site.js adds on load."""
    page.eq("no site script ran (no status region)", page.js("return document.querySelectorAll('[role=status]').length"), 0)
    state = f"(() => {{ {HOSTS} const d = {DIALOG}.querySelector('dialog'); return [d.open, d.matches(':modal')]; }})()"
    page.eq("closed on load", page.js(f"return {state}"), [False, False])
    for what, expr in [("the close button", "[rel=prev]"), ("its first footer button", "footer button:first-of-type"),
                       ("its last footer button", "footer button:last-of-type")]:
        page.click_at(*shadow_point(page, f"{DIALOG}.querySelector('[commandfor][command=show-modal]')"))
        page.wait(f"the opener shows it as a modal (before {what})", f"JSON.stringify({state}) === '[true,true]'", 1.5,
                  got=page.js(f"return {state}"))
        pt = page.js(HOSTS + f"const b = {DIALOG}.querySelector('dialog {expr}'); const r = b.getBoundingClientRect();"
                     " return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)];")
        page.click_at(*pt)
        page.wait(f"{what} closes it", f"JSON.stringify({state}) === '[false,false]'", 1.5, got=page.js(f"return {state}"))


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
    theme select and every Copy as page and Pop out button, which do nothing without JavaScript, are
    not rendered (examples.css, scripting: none)."""
    r = page.js(r"""const frames = [...document.querySelectorAll('div[data-example]')];
      return {frames: frames.length,
              styled: frames.filter(f => f.shadowRoot?.firstElementChild?.shadowRoot?.styleSheets[0]?.cssRules.length > 100).length,
              closed: document.querySelectorAll('main section.example > details:not([open])').length,
              select: document.querySelector('p[data-examples-theme]')?.getClientRects().length ?? null,
              buttons: [...document.querySelectorAll('button[data-copy-page]')].map(b => b.getClientRects().length),
              pops: [...document.querySelectorAll('button[data-pop-out]')].map(b => b.getClientRects().length)};""")
    page.expect("the page has examples", r["frames"] > 0)
    page.eq("every example styled by femto", r["styled"], r["frames"])
    page.eq("every sample folded", r["closed"], r["frames"])
    page.eq("the theme select is not rendered", r["select"], 0)
    page.eq("no Copy as page button is rendered, one in each example", r["buttons"], [0] * r["frames"])
    page.eq("no Pop out button is rendered, one in each example", r["pops"], [0] * r["frames"])


# femto's starter template as the docs' Quick start shows it: the text of the code block after the
# "Starter template" heading on /docs.
STARTER = r"""
const doc = new DOMParser().parseFromString(await (await fetch('/docs')).text(), 'text/html');
const h2 = [...doc.querySelectorAll('h2')].find(h => h.textContent.trim() === 'Starter template');
return h2 ? h2.parentElement.querySelector('pre code').textContent : null;
"""


def page_of(template, name, markup, color):
    """What Copy as page copies: the starter template with the example's name for its title, the
    chosen theme's link (none for azure) after femto's, and the sample in place of its <h1>, each
    line indented as the <h1> is but a <pre>'s lines after its first."""
    link = re.search(r'^( *)<link rel="stylesheet" href="(https://[^"]+/)dist/femto\.min\.css">$', template, re.M)
    indent, cdn = link.group(1), link.group(2)
    t = template[:link.end()] + (f'\n{indent}<link rel="stylesheet" href="{cdn}css/themes/{color}.css">' if color != "azure" else "") + template[link.end():]
    t = t.replace("<title>Hello, world!</title>", f"<title>{name}</title>", 1)
    h1 = re.search(r"^( *)<h1>Hello, world!</h1>$", t, re.M)
    lines, pre = [], False
    for line in markup.split("\n"):
        lines.append(line if pre or not line else h1.group(1) + line)
        opens, closes = bool(re.search(r"<pre[\s>]", line)), "</pre>" in line
        pre = True if opens and not closes else False if closes else pre
    return t[:h1.start()] + "\n".join(lines) + t[h1.end():]


# A copied page read as a browser reads it: its head, and its <main>'s content against the sample's.
READ_PAGE = r"""
const [text, sample] = arguments;
const d = new DOMParser().parseFromString(text, 'text/html');
const t = document.createElement('template'); t.innerHTML = sample;
const main = d.querySelectorAll('body > main.container');
return {doctype: d.doctype?.name ?? null, lang: d.documentElement.lang, charset: d.querySelector('head > meta[charset]')?.getAttribute('charset') ?? null,
        viewport: d.querySelector('head > meta[name=viewport]')?.content ?? null, scheme: d.querySelector('head > meta[name=color-scheme]')?.content ?? null,
        title: d.title, links: [...d.querySelectorAll('head > link[rel=stylesheet]')].map(l => l.getAttribute('href')),
        mains: main.length, body: [...d.body.children].map(c => c.localName),
        same: main.length === 1 && main[0].innerHTML.replace(/\s+/g, ' ').trim() === t.innerHTML.replace(/\s+/g, ' ').trim(),
        pre: main.length ? [...main[0].querySelectorAll('pre')].map(p => p.textContent) : null,
        samplePre: [...t.content.querySelectorAll('pre')].map(p => p.textContent)};
"""

# Records the button's data-tooltip and the status line on every change of the tooltip, and the
# click, with performance.now(), and the button's width and text at the click and at each change.
COPY_PAGE_TIMELINE = r"""
const b = arguments[0];
window.__bhPage = [];
window.__bhPageWidths = [];
window.__bhPageTexts = [];
const t = () => Math.round(performance.now());
const w = () => { __bhPageWidths.push(Math.round(b.getBoundingClientRect().width * 10) / 10); __bhPageTexts.push(b.textContent); };
const status = () => document.querySelector('body > p.visually-hidden[role=status]')?.textContent ?? null;
new MutationObserver(() => { __bhPage.push([t(), b.getAttribute('data-tooltip'), status()]); w(); })
  .observe(b, {attributes: true, attributeFilter: ['data-tooltip']});
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
    <h1>, indented as the <h1> is but for a <pre>'s later lines. No sample names a /vendor/femto/
    path, which a copied page could not load. Read back as a document, the copy has the template's
    doctype, lang, charset, viewport, color-scheme and femto link, one main.container holding the
    sample, and each <pre>'s text unchanged. With jade chosen in the theme
    select, the copy also links jade's css/themes/ file right after femto. Within 100 ms of a click
    the button's femto tooltip (data-tooltip, which it has only then) says "Copied", and 900 to 1500
    ms later it has none again, as a code block's copy button does (the owner, 2026-11-11); its label
    reads "Copy as page" throughout, at the width it had, so it does not move under the pointer, and
    its computed name stays "Copy as page" while the tooltip shows (its aria-label, so the tooltip's
    ::before text never joins it). The page's one status region, site.js's
    (body > p.visually-hidden[role=status]), says "Copied" (with a no-break space after it when it
    repeats the message before it, every other copy) and then nothing. The URL does not change."""
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
        page.expect(f"{x['id']}: the sample names no /vendor/femto/ path", '"/vendor/femto/' not in x["sample"])
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
        if k == len(buttons) - 1:
            page.wait(f"{x['id']}: the tooltip says Copied", "arguments[0].getAttribute('data-tooltip') === 'Copied'", 0.5,
                      args=(button,))
            expect_name(page, f"{x['id']}: named Copy as page while the tooltip says Copied", button, "Copy as page")
        text = page.js(f"return window.__bhCopied[{k}].text")
        page.eq(f"{x['id']}: exactly its sample in the starter template", text, page_of(template, x["name"], x["sample"], "azure"))
        d = page.js(READ_PAGE, text, x["sample"])
        page.expect(f"{x['id']}: read back, the template's head and one main.container holding the sample",
                    d["doctype"] == "html" and d["lang"] == "en" and d["charset"] == "utf-8"
                    and d["viewport"] == "width=device-width, initial-scale=1" and d["scheme"] == "light dark"
                    and d["title"] == x["name"] and d["links"] == [cdn + "dist/femto.min.css"] and d["mains"] == 1
                    and d["body"] == ["main"] and d["same"], **d)
        page.eq(f"{x['id']}: each <pre>'s text unchanged", d["pre"], d["samplePre"])
    page.wait("the last button's tooltip goes", "window.__bhPage.length >= 3 && !arguments[0].hasAttribute('data-tooltip')", 2.5,
              args=(buttons[-1],))
    tl = page.js("return window.__bhPage")
    # The region's text, its trailing no-break space dropped: the copies alternate "Copied" and
    # "Copied\u00A0" (copy-announce-twice holds the alternation).
    steps = [x[1:2] if x[1] == "click" else [x[1], x[2].strip() if x[2] else x[2]] for x in tl]
    page.eq("the steps: click, the tooltip Copied, no tooltip", steps, [["click"], ["Copied", "Copied"], [None, ""]], timeline=tl)
    page.expect("Copied within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
    page.expect("gone 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
    widths, texts = page.js("return window.__bhPageWidths"), page.js("return window.__bhPageTexts")
    page.eq("the label reads Copy as page throughout", sorted(set(texts)), ["Copy as page"], texts=texts)
    page.expect("the button keeps its width while its tooltip says Copied", len(widths) >= 3 and max(widths) - min(widths) <= 0.5,
                widths=widths)
    page.eq("one status region on the page", page.js("return document.querySelectorAll('[role=status]').length"), 1)
    choose_theme(page, "jade")
    k = len(buttons)
    x = next(i for i in info if i["id"] == "sign-in")
    page.click(buttons[info.index(x)])
    page.wait("sign-in, jade: copied", f"window.__bhCopied.length === {k + 1}", 1)
    text = page.js(f"return window.__bhCopied[{k}].text")
    page.eq("sign-in, jade: jade's link after femto's", text, page_of(template, x["name"], x["sample"], "jade"))
    page.eq("sign-in, jade: the two links", page.js(READ_PAGE, text, x["sample"])["links"],
            [cdn + "dist/femto.min.css", cdn + "css/themes/jade.css"])
    page.url_kept("no navigation", url)


# A clipboard that refuses every write (its calls recorded, its promise rejected); with arguments[0]
# true, no navigator.clipboard at all, as on an insecure origin.
COPY_REFUSED = r"""
window.__bhRefused = window.__bhRefused || [];
if (arguments[0]) Object.defineProperty(navigator, "clipboard", {value: undefined, configurable: true});
else navigator.clipboard.writeText = (t) => { __bhRefused.push(String(t)); return Promise.reject(new DOMException("refused", "NotAllowedError")); };
return navigator.clipboard === undefined;
"""


@check("examples-copy-page-failed", "/examples")
def examples_copy_page_failed(page):
    """A Copy as page that fails says so (examples.js): with a clipboard whose writeText rejects,
    the first example's Copy as page button tries to write its page once, its tooltip says "Copy
    failed" within 100 ms and is gone 900 to 1500 ms later, its label reading "Copy as page" at the
    width it had throughout, and the page's one status region says "Copy failed", then nothing.
    With no navigator.clipboard at all, a second click's tooltip says "Copy failed" again."""
    button = page.find_all("main section.example > header > button[data-copy-page]")[0]
    page.eq("the clipboard refuses", page.js(COPY_REFUSED, False), False)
    page.js(COPY_PAGE_TIMELINE, button)
    page.click(button)
    page.wait("the tooltip goes", "window.__bhPage.length >= 3 && !arguments[0].hasAttribute('data-tooltip')", 2.5, args=(button,))
    tl = page.js("return window.__bhPage")
    page.eq("it tried to write once", len(page.js("return window.__bhRefused")), 1)
    page.eq("the steps: click, the tooltip Copy failed, no tooltip", [x[1:] for x in tl],
            [["click"], ["Copy failed", "Copy failed"], [None, ""]], timeline=tl)
    page.expect("Copy failed within 100 ms", tl[1][0] - tl[0][0] <= 100, timeline=tl)
    page.expect("gone 1 s later", 900 <= tl[2][0] - tl[1][0] <= 1500, timeline=tl)
    widths, texts = page.js("return window.__bhPageWidths"), page.js("return window.__bhPageTexts")
    page.eq("the label reads Copy as page throughout", sorted(set(texts)), ["Copy as page"], texts=texts)
    page.expect("the button keeps its width while its tooltip says Copy failed", len(widths) >= 3 and max(widths) - min(widths) <= 0.5,
                widths=widths)
    page.eq("no navigator.clipboard", page.js(COPY_REFUSED, True), True)
    page.click(button)
    page.wait("no clipboard: the tooltip says Copy failed", "arguments[0].getAttribute('data-tooltip') === 'Copy failed'", 1,
              args=(button,))


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
    click; within 100 ms of the second it is emptied and says "Copied" again with a no-break space
    after it (U+00A0), a change a screen reader announces (the same text written over itself would
    be none, and VoiceOver skips a message that repeats the one before it even across the emptying);
    and it is emptied once, 900 to 1500 ms after the second click, not 1 s after the first. Timed in
    the page with a MutationObserver on the region."""
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
    page.eq("the region's steps: Copied, emptied, Copied and a no-break space, emptied", steps, ["Copied", "", "Copied\u00A0", ""],
            timeline=tl)
    first = next(x[0] for x in texts if x[1] == "Copied")
    again = next(x[0] for x in texts if x[1] == "Copied\u00A0" and x[0] >= clicks[1])
    end = texts[-1][0]
    page.expect("the first Copied within 100 ms of the first click", first - clicks[0] <= 100, timeline=tl)
    page.expect("Copied again within 100 ms of the second click", again - clicks[1] <= 100, timeline=tl)
    page.expect("emptied 900 to 1500 ms after the second click", 900 <= end - clicks[1] <= 1500, ms=end - clicks[1], timeline=tl)


# Every inner root's theme links and its host's --femto-primary-background, and the page's.
THEME_STATE = HOSTS + r"""
const themes = (root) => [...root.children].filter(e => e.localName === 'link' && e.getAttribute('href').includes('/css/themes/'));
const color = (host) => getComputedStyle(host).getPropertyValue('--femto-primary-background').trim().toLowerCase();
return {inner: hosts.map(h => ({id: h.id, second: h.root.children[1]?.outerHTML.slice(0, 90), themes: themes(h.root).map(l => [l.outerHTML, !!l.sheet]),
                                color: color(h.inner)})),
        page: color(document.documentElement), query: location.search};
"""


@check("examples-theme", "/examples")
def examples_theme(page):
    """The theme select (p[data-examples-theme] select) offers femto's 20 colors, azure selected, in
    the docs' Theme picker's order (read from /docs), each labeled with its name capitalized. On load
    no inner root links a theme, and every inner host has azure's primary background. Choosing jade
    links <link rel="stylesheet" href="/vendor/femto/css/themes/jade.css"> right after femto's in
    every inner root, loaded, and gives every inner host jade's primary background (its css/themes/
    file's); red then replaces jade's link with red's, one theme link a root; and azure removes it,
    back to azure's color. Throughout, the page itself keeps azure, and the URL gets no ?theme= and
    no new history entry (Decision 8)."""
    files = theme_files()
    opts = page.js("return [...document.querySelectorAll('p[data-examples-theme] select option')].map(o => [o.value, o.textContent.trim(), o.selected])")
    want = page.ajs(PICKER_ORDER)
    page.eq("the picker's colors are femto's 20", sorted(want), sorted(files))
    page.eq("the 20 colors, in the picker's order", [o[0] for o in opts], want)
    page.eq("each labeled with its name", [o[1] for o in opts], [c.capitalize() for c in want])
    page.eq("azure selected", [o[0] for o in opts if o[2]], ["azure"])
    url = page.url()
    s = page.js(THEME_STATE)
    page.eq("on load: no theme link in any inner root", [x["themes"] for x in s["inner"]], [[]] * len(s["inner"]))
    page.eq("on load: every inner host azure", {x["color"] for x in s["inner"]}, {files["azure"]})

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


NEWER = HOSTS + r"""
const root = (id) => hosts.find(h => h.id === id).root;
const kids = (el) => [...el.children].map(c => c.localName + [...c.classList].map(x => '.' + x).join(''));
const side = (a, b) => { const x = a.getBoundingClientRect(), y = b.getBoundingClientRect(); return x.right <= y.left && Math.abs(x.top - y.top) < 1; };
const land = root('landing-page'), docs = root('docs-layout'), out = root('checkout');
const dgrid = docs.children[1], cgrid = out.children[2];
return {
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
             table: [...cgrid.querySelectorAll('article table > *')].map(e => e.localName + ':' + e.rows.length), side: side(cgrid.children[0], cgrid.children[1])}
};
"""


@check("examples-newer", "/examples")
def examples_newer(page):
    """The index under the hero links every example, in page order, and the Landing page, Docs page
    and Checkout examples are among them and hold what they show (at 1300 px). Landing page
    (#landing-page): a header with a nav of two lists, the hero's hgroup and two call-to-action
    links, three feature cards in a grid, a quotation and a footer nav. Docs page (#docs-layout): a
    grid of an <aside>, whose nav holds two open groups of links (femto shows them as blocks), and an
    article with a heading and a footer nav, side by side. Checkout (#checkout): a form of four
    fieldsets, each led by its legend, with its own radio names and a submit button, beside a card
    whose table has a head, two body rows and three footer rows."""
    index = page.js("""return {links: [...document.querySelectorAll('main .examples-index a')].map(a => a.getAttribute('href')),
      examples: [...document.querySelectorAll('main section.example')].map(s => '#' + s.id)};""")
    page.eq("the index links every example, in page order", index["links"], index["examples"])
    for eid in ("landing-page", "docs-layout", "checkout"):
        page.expect(f"#{eid} is an example", f"#{eid}" in index["examples"])
    r = page.js(NEWER)
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


# --- Pop out ---------------------------------------------------------------------------------------

# The Pop out dialog and the example whose id is arguments[0]: the dialog, its title and focus, the
# frame's place (its section, or the card) and its email field's value, the placeholder, the
# section's children and its <details>' top, scrollY, <html>'s modal classes, and the card's edges
# with --femto-spacing in px (a probe sized by the token, in the card).
POP_STATE = r"""
const id = arguments[0];
const section = document.getElementById(id);
const dialogs = document.querySelectorAll('dialog[data-example-modal]');
const dialog = dialogs[0] ?? null;
const article = dialog?.querySelector(':scope > article') ?? null;
const close = article?.querySelector(':scope > header > button[rel=prev]') ?? null;
const title = document.getElementById('example-modal-title');
const frame = document.querySelector(`div[data-example="${id}"]:not([data-example-placeholder])`);
const root = frame?.shadowRoot?.firstElementChild?.shadowRoot ?? null;
const placeholder = section.querySelector(':scope > div[data-example-placeholder]');
const kids = (el) => [...el.children].map(c => c.localName + (c.hasAttribute('data-example-placeholder') ? '[data-example-placeholder]'
  : c.hasAttribute('data-example') ? '[data-example]' : ''));
const active = document.activeElement;
let bounds = null;
if (article) {
  const probe = document.createElement('div');
  probe.style.cssText = 'position: absolute; width: var(--femto-spacing); height: 0';
  article.append(probe);
  const spacing = probe.getBoundingClientRect().width;
  probe.remove();
  const r = article.getBoundingClientRect();
  bounds = {left: r.left, right: r.right, top: r.top, viewport: document.documentElement.clientWidth, spacing};
}
return {
  dialogs: dialogs.length, open: dialog?.open ?? false, modal: dialog?.matches(':modal') ?? false,
  inMain: dialog?.parentElement === document.querySelector('body > main'),
  labelledby: dialog?.getAttribute('aria-labelledby') ?? null,
  title: title && article?.contains(title) && title.matches('dialog > article > header > h2') ? title.textContent : null,
  closeName: close?.getAttribute('aria-label') ?? null,
  card: article ? kids(article) : null,
  focus: active === close ? 'close' : active === section.querySelector(':scope > header > button[data-pop-out]') ? 'pop out'
    : active?.outerHTML.slice(0, 80) ?? null,
  frame: frame?.parentElement === section ? 'section' : frame && frame.parentElement === article ? 'card' : null,
  shadow: !!root, value: root?.querySelector('input[type=email]')?.value ?? null,
  frameHeight: frame?.getBoundingClientRect().height ?? null,
  placeholders: document.querySelectorAll('[data-example-placeholder]').length,
  placeholder: placeholder ? {height: placeholder.getBoundingClientRect().height, inline: parseFloat(placeholder.style.height),
                              empty: !placeholder.shadowRoot && !placeholder.childNodes.length} : null,
  section: kids(section),
  details: section.querySelector(':scope > details').getBoundingClientRect().top, y: scrollY,
  classes: [...document.documentElement.classList].filter(c => c.startsWith('modal-')),
  bounds,
};
"""
# The Pop out dialog is open and its opening animation is done (createModal(): modal-is-open alone).
POPPED = ("(() => { const d = document.querySelector('dialog[data-example-modal]'), c = document.documentElement.classList;"
          " return !!d?.open && c.contains('modal-is-open') && !c.contains('modal-is-opening'); })()")
# The popped-out example's inner shadow root.
POPPED_ROOT = "document.querySelector('dialog[data-example-modal] > article > div[data-example]').shadowRoot.firstElementChild.shadowRoot"
# A point on the dialog, the overlay, halfway between the viewport's top left corner and the card's.
OVERLAY_POINT = r"""
const d = document.querySelector('dialog[data-example-modal]'), r = d.querySelector(':scope > article').getBoundingClientRect();
const x = Math.floor(r.left / 2), y = Math.floor(r.top / 2);
return document.elementFromPoint(x, y) === d ? [x, y] : null;
"""
TYPED = "sam@example.com"


def pop_open(page, eid, label):
    """Click the example's Pop out button, scrolled to the middle first, and wait until its dialog
    has opened; returns the example's POP_STATE before the click and once open."""
    button = page.el(f"#{eid} > header > button[data-pop-out]")
    page.js("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'})", button)
    page.sleep(0.05)
    before = page.js(POP_STATE, eid)
    page.click(button, scroll=False)
    page.wait(f"{label}: the Pop out dialog opens", POPPED, 1.5, got=page.js(POP_STATE, eid))
    return before, page.js(POP_STATE, eid)


def pop_closed(page, eid, label, value=None):
    """Wait until the Pop out dialog has left the page (createModal() closes after femto's animations,
    400 ms at most), then assert that the example's frame is back between its header and its
    details with its shadow roots (and Sign in's typed email), no placeholder is left, <html> has no
    modal class and focus is on the Pop out button."""
    page.wait(f"{label}: the Pop out dialog leaves the page", "!document.querySelector('dialog[data-example-modal]')", 1.5)
    s = page.js(POP_STATE, eid)
    page.eq(f"{label}: the frame back in its section, its shadow roots kept, no placeholder",
            {k: s[k] for k in ("frame", "shadow", "section", "placeholders")},
            {"frame": "section", "shadow": True, "section": ["header", "div[data-example]", "details"], "placeholders": 0})
    if value is not None:
        page.eq(f"{label}: the email field keeps what was typed", s["value"], value)
    page.eq(f"{label}: no modal class on <html>", s["classes"], [])
    page.eq(f"{label}: focus back on the Pop out button", s["focus"], "pop out")


def pop_out(page):
    n = page.js("return document.querySelectorAll('main section.example').length")
    page.eq("one Pop out button in each example header, reading Pop out",
            page.js("return [...document.querySelectorAll('main section.example')].map(s =>"
                    " [...s.querySelectorAll(':scope > header > button[data-pop-out]')].map(b => b.textContent).join('|'))"),
            ["Pop out"] * n)
    page.click_at(*shadow_point(page, "hosts.find(h => h.id === 'sign-in').root.querySelector('input[type=email]')"))
    page.key(TYPED)
    page.eq("Sign in: the email field holds what was typed", page.js(POP_STATE, "sign-in")["value"], TYPED)

    before, s = pop_open(page, "sign-in", "Sign in")
    page.eq("Sign in: one dialog, in <main>, open as a modal", {k: s[k] for k in ("dialogs", "inMain", "open", "modal")},
            {"dialogs": 1, "inMain": True, "open": True, "modal": True})
    page.eq("Sign in: named by #example-modal-title, its h2, which reads Sign in", [s["labelledby"], s["title"]],
            ["example-modal-title", "Sign in"])
    page.eq("Sign in: focus on the dialog's close button", [s["focus"], s["closeName"]], ["close", "Close"])
    page.eq("Sign in: the card holds its header and the frame, with its shadow roots and the typed email",
            [s["card"], s["frame"], s["shadow"], s["value"]], [["header", "div[data-example]"], "card", True, TYPED])
    page.eq("Sign in: an empty placeholder holds the frame's place", s["section"], ["header", "div[data-example-placeholder]", "details"])
    ph = s["placeholder"]
    page.expect("Sign in: the placeholder has the frame's height (within 1 px), inline, and no example",
                ph["empty"] and abs(ph["height"] - before["frameHeight"]) <= 1 and abs(ph["inline"] - before["frameHeight"]) <= 1,
                placeholder=ph, frame=before["frameHeight"])
    page.expect("Sign in: the section's details did not move (within 1 px) and the page did not scroll",
                abs(s["details"] - before["details"]) <= 1 and s["y"] == before["y"],
                details=[before["details"], s["details"]], y=[before["y"], s["y"]])
    b = s["bounds"]
    page.expect("Sign in: the card spans the viewport less --femto-spacing on each side (within 1 px)",
                b["spacing"] > 0 and abs(b["left"] - b["spacing"]) <= 1 and abs(b["right"] - (b["viewport"] - b["spacing"])) <= 1, **b)
    page.click(page.el("dialog[data-example-modal] > article > header > button[rel=prev]"))
    pop_closed(page, "sign-in", "the close button", TYPED)

    pop_open(page, "sign-in", "again")
    page.key("ESCAPE")
    pop_closed(page, "sign-in", "Escape", TYPED)

    _, s = pop_open(page, "sign-in", "once more")
    page.eq("once more: the frame in the card, the email kept", [s["frame"], s["value"]], ["card", TYPED])
    pt = page.js(OVERLAY_POINT)
    page.expect("a point on the overlay, outside the card", pt, bounds=s["bounds"])
    page.click_at(*pt)
    pop_closed(page, "sign-in", "a click on the overlay", TYPED)

    pop_open(page, "confirm-dialog", "Confirmation dialog")
    inner = (f"(() => {{ const r = {POPPED_ROOT}, d = r.querySelector('dialog');"
             " return {open: d.open, modal: d.matches(':modal'), opener: r.activeElement === r.querySelector('[aria-controls]')}; })()")
    page.click_at(*shadow_point(page, f"{POPPED_ROOT}.querySelector('[aria-controls]')"))
    page.wait("Confirmation dialog: its Delete project dialog opens as a modal in the card",
              f"(() => {{ const s = {inner}; return s.open && s.modal; }})()", 1.5)
    page.key("ESCAPE")
    page.wait("Escape closes the example's own dialog", f"!{inner}.open", 1.5)
    page.holds("the Pop out dialog stays open after that Escape", f"{POPPED} && !document.documentElement.classList.contains('modal-is-closing')", 0.6)
    page.expect("focus back on the example's opener", page.js(f"return {inner}")["opener"], state=page.js(f"return {inner}"))
    page.key("ESCAPE")
    pop_closed(page, "confirm-dialog", "a second Escape")


@check("examples-pop-out", "/examples")
def examples_pop_out(page):
    """Each example's header has one Pop out button (button[data-pop-out]). With an email typed into
    Sign in, its Pop out opens one dialog[data-example-modal] in <main> as a modal (:modal), named by
    aria-labelledby="example-modal-title", the card's h2, which reads "Sign in", with focus on the
    card's close button. The card holds its header and the frame itself, its shadow roots and the
    typed email kept; the section holds an empty placeholder frame in its place, of the frame's
    height (within 1 px), so the section's <details> keeps its top (within 1 px) and scrollY its
    value. The card spans the viewport less --femto-spacing (read from the page) on each side,
    within 1 px. The close button, Escape and a click on the overlay (press and release on the
    dialog, outside the card) each close it: once the dialog has left the page (createModal() waits
    for femto's animations, 400 ms at most), the frame is back between the section's header and its
    <details> with the email kept, no placeholder is left, <html> has no modal class and focus is
    on the Pop out button. With Confirmation dialog popped out and its Delete project dialog open
    inside the card, Escape closes only that dialog, focus going back to its opener, and the Pop
    out dialog stays open; a second Escape closes the Pop out dialog."""
    pop_out(page)


@check("examples-pop-out-small", "/examples", width=375, height=812)
def examples_pop_out_small(page):
    """The same at 375 x 812, a phone's viewport, where femto's card already takes the viewport's
    width less its margin."""
    pop_out(page)
