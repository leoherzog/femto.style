"""Examples: the /examples page's mockups (Phase 4; PLAN.md Open questions 1; examples.js). Each
mockup is vanilla femto in two declarative shadow roots: the outer one, in div[data-example], holds only
the inner host, so no page rule can match it; the inner one holds femto's stylesheet link and the
mockup, and a Markup disclosure under it shows the same markup to copy. examples.js mirrors <html>'s
data-theme onto each inner host, cancels the mockups' submits and link clicks, and opens and closes
the confirmation dialog.

The oracle's /examples lists CodeSandboxes, so every check here runs on the one page only (the static
site's layout)."""
from behavior import check

GROUP = "examples"
ONLY = ("one-page",)
WHY = ("Phase 4's /examples mockups (PLAN.md Open questions 1); the oracle's /examples links to Pico's CodeSandboxes "
       "and has none")

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


@check("examples-structure", "/examples", layouts=ONLY, layout_reason=WHY)
def examples_structure(page):
    """Each section.example holds one div[data-example] (11 on 2026-11-05), whose shadow root's only element is a div with a shadow root of
    its own; that root's first element is the one stylesheet link, /vendor/femto/dist/femto.min.css,
    loaded, with no other <link> or <style>; the markup after it is the code sample's text, node for
    node (whitespace collapsed); and no id repeats across the page, shadow roots included."""
    r = page.js(HOSTS + r"""
      const norm = (node) => {
        const walk = (n) => {
          for (const c of [...n.childNodes]) {
            if (c.nodeType === 3) { const t = c.data.replace(/\s+/g, ' ').trim(); if (!t) c.remove(); else c.data = t; }
            else if (c.nodeType === 8) c.remove();
            else walk(c);
          }
        };
        walk(node);
        const div = document.createElement('div'); div.append(node); return div.innerHTML;
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
        for (const n of nodes.slice(nodes.indexOf(link) + 1)) live.append(n.cloneNode(true));
        const code = h.frame.closest('section').querySelector('details pre code').textContent;
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
# included, as [path, pseudo, {property: value}]. Custom properties are kept only if femto.css
# declares or reads them (FEMTO_TOKENS, filled in by the check).
STYLES = r"""
const tokens = new Set(arguments[0]);
const props = (cs) => { const o = {}; for (const p of cs) { if (p.startsWith('--') && !tokens.has(p)) continue; o[p] = cs.getPropertyValue(p); } return o; };
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
  const code = h.frame.closest('section').querySelector('details pre code').textContent;
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
for (const h of refHosts) await Promise.all([...h.root.querySelectorAll('link')].map(l => l.sheet ? null : new Promise(r => l.onload = r)));
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
              roots: [getComputedStyle(document.documentElement).fontSize, refRoot]};
    """, femto_tokens(), theme, list(LAYOUT_ONLY))
    page.note(f"compared {res['elements']} elements and pseudo-elements; {res['skipped']} layout-resolved inset values differ (not compared); "
              f"root font size {res['roots'][0]} on the page, {res['roots'][1]} in the reference before its examples")
    page.eq("every computed style equals a femto-only page's", res["total"], 0, diffs=res["diffs"])


@check("examples-isolation", "/examples", layouts=ONLY, layout_reason=WHY)
def examples_isolation(page):
    """Every element of every example, its host and pseudo-elements included, has the same computed
    style (every property, and every custom property femto.css names) as in a document that loads
    femto alone and holds the same markup in the same two shadow roots: no site CSS reaches in."""
    compare_styles(page, None)


@check("examples-isolation-dark", "/examples", media="dark", layouts=ONLY, layout_reason=WHY)
def examples_isolation_dark(page):
    """As examples-isolation, with the OS in dark."""
    compare_styles(page, None)


@check("examples-isolation-stored", "/examples", storage={"femtoColorScheme": '"dark"'}, layouts=ONLY, layout_reason=WHY)
def examples_isolation_stored(page):
    """With a stored dark choice on a light OS, every inner host carries data-theme="dark", and every
    computed style equals the femto-only document's with data-theme="dark" on its inner hosts."""
    page.wait("every inner host is dark",
              "[...document.querySelectorAll('div[data-example]')].every(f => f.shadowRoot.firstElementChild.getAttribute('data-theme') === 'dark')")
    compare_styles(page, "dark")


@check("examples-scheme", "/examples", layouts=ONLY, layout_reason=WHY)
def examples_scheme(page):
    """The inner hosts follow <html>'s data-theme: none on load (OS light, nothing stored), then dark
    and light again with the header toggle, and their background follows."""
    inner = "[...document.querySelectorAll('div[data-example]')].map(f => f.shadowRoot.firstElementChild)"
    page.eq("no data-theme on load", page.js(f"return {inner}.filter(h => h.hasAttribute('data-theme')).length"), 0)
    light = page.js(f"return getComputedStyle({inner}[0]).backgroundColor")
    page.click("button[data-scheme-toggle]")
    page.wait("toggle: every inner host dark", f"{inner}.every(h => h.getAttribute('data-theme') === 'dark')")
    dark = page.js(f"return getComputedStyle({inner}[0]).backgroundColor")
    page.expect("the background follows", dark != light, light=light, dark=dark)
    page.click("button[data-scheme-toggle]")
    page.wait("toggle again: every inner host light", f"{inner}.every(h => h.getAttribute('data-theme') === 'light')")


@check("examples-forms", "/examples", layouts=ONLY, layout_reason=WHY)
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


@check("examples-links", "/examples", layouts=ONLY, layout_reason=WHY)
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


DIALOG = "hosts.find(h => h.id === 'confirm-dialog').root"


@check("examples-dialog", "/examples", layouts=ONLY, layout_reason=WHY)
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


@check("examples-dropdown", "/examples", layouts=ONLY, layout_reason=WHY)
def examples_dropdown(page):
    """The navigation bar's Account dropdown opens on a click on its summary, shows its menu, and
    closes on a click outside it."""
    nav = "hosts.find(h => h.id === 'navigation-bar').root.querySelector('details.dropdown')"
    page.click_at(*shadow_point(page, f"{nav}.querySelector('summary')"))
    page.wait("open", f"(() => {{ {HOSTS} const d = {nav}; return d.open && d.querySelector('ul').getBoundingClientRect().height > 50; }})()")
    page.click_at(5, 5)
    page.wait("closed by a click outside", f"(() => {{ {HOSTS} return !{nav}.open; }})()")


@check("examples-fit", "/examples", width=375, height=812, layouts=ONLY, layout_reason=WHY)
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


@check("examples-first-frame", "/examples", storage={"femtoColorScheme": '"dark"'}, preload=FIRST_FRAME_PRELOAD, layouts=ONLY, layout_reason=WHY)
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


@check("examples-first-frame-cold", "/examples", preload=FIRST_FRAME_PRELOAD, cold=True, layouts=ONLY, layout_reason=WHY)
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
