/*
 * femto.style parity harness: in-page collector and differ. Runs in the host page
 * (/__harness/host.html on the session's proxy) and loads each side of a comparison into a fresh
 * same-origin iframe of exact width. Ported from femto's tests/harness/differ.js (femto 65453b74):
 * the value rule, registry patterns, animation freezing, pseudo-element collection, environment
 * checks and screenshot preparation are femto's; the tree alignment of two documents is new.
 *
 * Python calls window.H.* through WebDriver. Snapshots stay in this page's memory; only
 * differences (already matched against the divergence registry) go back to Python.
 *
 * Alignment: each element's path is its tag plus its index among its compared element siblings,
 * from html (with --root-a/--root-b only that element's subtree is compared, and its paths still
 * start at html: the root's own path, then down). head, meta, title, script, link, style,
 * template, base and noscript are skipped and never counted. Open shadow roots are a separate child
 * list (path step "#shadow"). Two sibling lists are aligned by a keyed longest common subsequence,
 * in three passes: whole-subtree signatures (tag, attributes, own text and children, masked parts
 * left out), then tag plus id, class, type, name and role, then the tag alone; whatever is left in a
 * gap pairs by position. So an inserted or removed element is one "structure" record (only-b,
 * only-a) naming that element, and its later siblings still pair with their true counterparts. Two
 * elements paired with different tags are a "structure" record (tag); their own text and their
 * children are still compared. Paired elements compare their attribute sets (exact), their own text
 * (CSS document white space read as it renders, unless white-space preserves it; a no-break space
 * is text: ownText()) and every enumerated computed longhand of
 * the element and its ::before, ::after, ::marker, ::placeholder, ::file-selector-button and
 * ::backdrop. The alignment only decides which elements pair; every paired element is compared in
 * full, so a poor alignment can add records but never hide one.
 *
 * Head: when the root is html, the document's title, every <meta>, every <link> that is not a
 * stylesheet or a fetch hint (preload, modulepreload, prefetch, preconnect, dns-prefetch, prerender),
 * <base>, and every data-block <script> (application/ld+json and any other non-JavaScript type, its
 * JSON compared leaf by leaf) are compared as "head" records, keyed by tag and their identifying
 * attributes (meta[name=description], meta[property=og:url], link[rel=canonical],
 * script[type=application/ld+json]).
 *
 * Requests: each collect also returns the document's cross-origin loads from its Resource Timing
 * entries and those of every frame it can read (criterion 15); compare.py adds the proxy's CSP
 * reports and judges them with report.py, outside the diff.
 *
 * Registry breadth: each collect also records what every registry entry reaches on the live
 * document (entryReach), and H.diff applies the registry's per-document limits to it before any
 * record is matched (breadthGuard), then limits what the registered records cover (coverage).
 */
(function () {
  "use strict";
  const H = (window.H = {});

  // ---------------------------------------------------------------------------------------
  // Configuration and state
  // ---------------------------------------------------------------------------------------
  const SKIP_TAGS = new Set(["head", "meta", "title", "script", "link", "style", "template", "base", "noscript"]);
  const HARNESS_TAGS = new Set(["harness-mq", "harness-cover"]);
  const ALL_PSEUDOS = ["::before", "::after", "::marker", "::placeholder", "::file-selector-button", "::backdrop"];
  const KEEP_SPACE = /^(preserve|preserve-breaks|break-spaces|preserve-spaces|pre|pre-wrap|pre-line)$/;

  // breadth: the registry's per-document limits (registry.py limits()), applied again in every cell
  // on the live documents (H.diff: breadthGuard, coverage).
  let cfg = { entries: [], masks: [], maxRecords: 300, pseudos: ALL_PSEUDOS.slice(), blobUuid: true,
              breadth: { doc: 0.25, union: 0.5, floor: 4, cover: 0.25 } };
  let compiled = [];
  let maskDefs = [];
  let frame = null, win = null, doc = null;
  const store = { a: null, b: null };
  let harnessErrors = [];

  H.configure = function (c) {
    cfg = Object.assign({}, cfg, c || {});
    const errors = [];
    compiled = [];
    // k is the entry's index in compiled (selSets and reach are indexed the same way), so an entry
    // that does not compile shifts nothing.
    (cfg.entries || []).forEach((e) => {
      try { compiled.push(compileEntry(e, compiled.length)); }
      catch (err) { errors.push("registry entry " + e.id + ": " + err.message); }
    });
    maskDefs = [];
    for (const m of cfg.masks || []) {
      try {
        document.createDocumentFragment().querySelector(m.selector);
        if (typeof m.pixels === "string") document.createDocumentFragment().querySelector(m.pixels);
        maskDefs.push({ id: m.id, sel: m.selector, contents: !!m.contents, text: !!m.text,
                        cover: typeof m.pixels === "string" ? m.pixels : (m.pixels ? m.selector : null),
                        attributes: new Set(m.attributes || []), properties: new Set(m.properties || []) });
      } catch (err) { errors.push("mask " + m.id + ": " + err.message); }
    }
    store.a = store.b = null;
    return { ok: !errors.length, errors, entries: compiled.length, masks: maskDefs.length,
             valueRules: H.VALUE_RULES.slice(0, cfg.blobUuid ? 2 : 1).concat(H.COLLECTION_RULES) };
  };

  H.hostStatus = function () {
    return {
      visibility: document.visibilityState,
      hasFocus: document.hasFocus(),
      dark: matchMedia("(prefers-color-scheme: dark)").matches,
      inner: [innerWidth, innerHeight],
      dpr: devicePixelRatio,
      ua: navigator.userAgent,
    };
  };

  // ---------------------------------------------------------------------------------------
  // Value comparison: exact, except colors (numeric, 1/255 per channel, 0.004 alpha). femto's rule.
  // ---------------------------------------------------------------------------------------
  const ctx = document.createElement("canvas").getContext("2d");
  const namedCache = new Map();
  const NOT_NAMED = new Set(["currentcolor", "inherit", "initial", "unset", "revert", "none", "auto"]);
  function namedColor(word) {
    const w = word.toLowerCase();
    if (namedCache.has(w)) return namedCache.get(w);
    let rgba = null;
    if (!NOT_NAMED.has(w)) {
      ctx.fillStyle = "#010203";
      ctx.fillStyle = w;
      const v = ctx.fillStyle;
      if (v !== "#010203" || w === "#010203") rgba = parseColor(v, true);
    }
    namedCache.set(w, rgba);
    return rgba;
  }
  function num(s, scale) {
    s = s.trim();
    if (s === "none") return 0;
    if (s.endsWith("%")) return (parseFloat(s) / 100) * scale;
    const v = parseFloat(s);
    return Number.isFinite(v) ? v : NaN;
  }
  function parseColor(s, noNamed) {
    s = s.trim();
    let m;
    if ((m = /^#([0-9a-f]{3,8})$/i.exec(s))) {
      let h = m[1];
      if (h.length === 3 || h.length === 4) h = h.split("").map((c) => c + c).join("");
      if (h.length !== 6 && h.length !== 8) return null;
      const n = (i) => parseInt(h.slice(i, i + 2), 16);
      return [n(0), n(2), n(4), h.length === 8 ? n(6) / 255 : 1];
    }
    if ((m = /^rgba?\((.*)\)$/i.exec(s))) {
      const parts = m[1].replace(/\//, ",").split(/[\s,]+/).filter(Boolean);
      if (parts.length < 3) return null;
      const c = [num(parts[0], 255), num(parts[1], 255), num(parts[2], 255), parts.length > 3 ? num(parts[3], 1) : 1];
      return c.some((x) => Number.isNaN(x)) ? null : c;
    }
    if ((m = /^color\(\s*srgb\s+(.*)\)$/i.exec(s))) {
      const [chan, alpha] = m[1].split("/");
      const parts = chan.trim().split(/\s+/);
      if (parts.length !== 3) return null;
      const c = [num(parts[0], 1) * 255, num(parts[1], 1) * 255, num(parts[2], 1) * 255, alpha ? num(alpha, 1) : 1];
      return c.some((x) => Number.isNaN(x)) ? null : c;
    }
    if (!noNamed && /^[a-z]+$/i.test(s)) return namedColor(s);
    return null;
  }
  // Split a value into color tokens and the remainder; quoted strings and url() stay in the remainder.
  const TOKEN_RE = /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|url\([^)]*\)|rgba?\([^()]*\)|color\(\s*srgb[^()]*\)|#[0-9a-fA-F]{3,8}\b|\b[a-zA-Z]+\b/g;
  function tokenize(v) {
    const colors = [];
    const rest = v.replace(TOKEN_RE, (t) => {
      const c0 = t.charAt(0);
      if (c0 === '"' || c0 === "'" || /^url\(/i.test(t)) return t;
      const c = parseColor(t);
      if (!c) return t;
      colors.push(c);
      return "\u0000";
    });
    return { rest, colors };
  }
  function same(a, b) {
    if (a === b) return true;
    if (typeof a !== "string" || typeof b !== "string") return false;
    const ta = tokenize(a), tb = tokenize(b);
    if (!ta.colors.length || ta.rest !== tb.rest || ta.colors.length !== tb.colors.length) return false;
    for (let i = 0; i < ta.colors.length; i++) {
      const x = ta.colors[i], y = tb.colors[i];
      for (let k = 0; k < 3; k++) if (Math.abs(x[k] - y[k]) > 1 + 1e-6) return false;
      if (Math.abs(x[3] - y[3]) > 0.004 + 1e-9) return false;
    }
    return true;
  }
  H.same = same;

  // A blob: URL names an object of its own document, with a random UUID, so two loads can never
  // share one (the oracle's /docs/colors download link is a blob: URL made on load). The owner chose
  // on 2026-10-30 to normalize it rather than mask it, so this rule is ON unless a run passes
  // --exact-blob-urls (tests/README.md, Diff rule): the UUID compares as a placeholder and the rest
  // of the value, the origin included, stays exact.
  const BLOB_RE = /blob:([^\s"'()]*?)\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
  function sameValue(a, b) {
    if (a === b) return true;
    if (!cfg.blobUuid || a == null || b == null) return false;
    if (a.indexOf("blob:") < 0 || b.indexOf("blob:") < 0) return false;
    return a.replace(BLOB_RE, "blob:$1/<uuid>") === b.replace(BLOB_RE, "blob:$1/<uuid>");
  }
  H.VALUE_RULES = [
    "colors in computed styles: numeric, 1/255 per channel and 0.004 alpha, the rest of the value exact",
    "blob: URLs in attributes and computed styles (off with --exact-blob-urls): the UUID is a placeholder, the rest of the value exact",
  ];
  // Always in force, so listed in every result beside the value rules (tests/README.md, Collection).
  H.COLLECTION_RULES = [
    "element text: an element's own text nodes, whitespace kept where the element preserves it; elsewhere a run's whitespace is one space where it renders an inline box (a Range client rect of nonzero inline size) and nothing where it collapses, and whitespace inside the text collapses to one space; whitespace is space, tab and line feed only, so a carriage return (Firefox renders it as nothing), a no-break space (U+00A0) and the other Unicode spaces are text, compared exactly",
    "data blocks: an exact copy of an earlier data block (same key, attributes and content, JSON leaf by leaf) counts once, on either side; head_repeats counts the copies per side",
  ];

  // ---------------------------------------------------------------------------------------
  // Registry matching. Patterns: omitted = any, "*" = any, "/re/flags" = regex, null = absent
  // (a/b only), other strings exact (style values with the color tolerance).
  // ---------------------------------------------------------------------------------------
  function isRe(p) { return typeof p === "string" && /^\/.+\/[imsu]*$/s.test(p); }
  function strPat(p) {
    if (p === undefined || p === "*") return () => true;
    if (isRe(p)) {
      const k = p.lastIndexOf("/");
      const re = new RegExp(p.slice(1, k), p.slice(k + 1));
      return (v) => v != null && re.test(String(v));
    }
    return (v) => v === p;
  }
  function valPat(p, kind) {
    if (p === undefined || p === "*") return () => true;
    if (p === null) return (v) => v === null || v === undefined;
    if (isRe(p)) return strPat(p);
    if (kind === "style") return (v) => v != null && same(p, String(v));
    return (v) => v === p;
  }
  function compileEntry(e, k) {
    const sel = e.selector && e.selector !== "*" ? e.selector : null;
    if (sel) document.createDocumentFragment().querySelector(sel); // throws on invalid selectors
    return {
      id: e.id, kind: e.kind, k, sel,
      path: strPat(e.path),
      pseudo: strPat(e.pseudo),
      prop: strPat(e.property),
      a: valPat(e.a, e.kind),
      b: valPat(e.b, e.kind),
    };
  }
  let disabled = new Set();  // entries the in-page breadth guard took out of this cell (H.diff)
  function matchRecord(rec, na, nb) {
    const hits = [];
    for (const e of compiled) {
      if (e.kind !== rec.kind || disabled.has(e.k)) continue;
      if (!e.path(rec.path)) continue;
      if (rec.kind === "style" && !e.pseudo(rec.pseudo)) continue;
      if ((rec.kind === "style" || rec.kind === "attribute" || rec.kind === "head") && !e.prop(rec.prop)) continue;
      if (!e.a(rec.a) || !e.b(rec.b)) continue;
      if (e.sel) {
        // The selector is matched against the element on side B, or on side A when B has none.
        const ok = nb ? store.b.selSets[e.k].has(nb.i) : (na ? store.a.selSets[e.k].has(na.i) : false);
        if (!ok) continue;
      }
      hits.push(e.id);
    }
    return hits;
  }
  function newResult() {
    return { total: 0, unregisteredTotal: 0, unregistered: [], registered: {}, samples: {}, counts: {} };
  }
  function addRecord(res, rec, na, nb) {
    res.total++;
    res.counts[rec.kind] = (res.counts[rec.kind] || 0) + 1;
    const hits = matchRecord(rec, na, nb);
    if (!hits.length) {
      res.unregisteredTotal++;
      if (res.unregistered.length < cfg.maxRecords) res.unregistered.push(rec);
      return;
    }
    for (const id of hits) {
      res.registered[id] = (res.registered[id] || 0) + 1;
      const s = (res.samples[id] = res.samples[id] || []);
      if (s.length < 2) s.push(rec);
    }
    cover(rec, na, nb, hits);
  }

  // Coverage: what the registered records of a cell hide, per side. A structure record that pairs
  // nothing (only-a, only-b) hides its whole subtree; any other element record hides the element on
  // each side; a head record hides its key. H.diff turns too much of a document into a harness error.
  let covered = null;
  function cover(rec, na, nb, hits) {
    if (!covered) return;
    let n = 0;
    const mark = (arr, node, whole) => {
      const end = whole ? node.i + node.size : node.i + 1;
      for (let i = node.i; i < end; i++) if (!arr[i]) { arr[i] = 1; n++; }
    };
    if (rec.kind === "head") {
      if (store.a.head && store.a.head.has(rec.path) && !covered.headA.has(rec.path)) { covered.headA.add(rec.path); n++; }
      if (store.b.head && store.b.head.has(rec.path) && !covered.headB.has(rec.path)) { covered.headB.add(rec.path); n++; }
    } else {
      const whole = rec.kind === "structure" && rec.change !== "tag";
      if (na) mark(covered.a, na, whole);
      if (nb) mark(covered.b, nb, whole);
    }
    for (const id of hits) covered.by[id] = (covered.by[id] || 0) + n;
  }

  // ---------------------------------------------------------------------------------------
  // Labels
  // ---------------------------------------------------------------------------------------
  function label(el) {
    let s = el.localName;
    if (el.id) s += "#" + el.id;
    if (el.classList && el.classList.length) s += "." + [...el.classList].join(".");
    const attrs = [];
    for (const a of ["type", "role", "data-theme", "aria-label", "aria-busy", "aria-current", "href", "open", "disabled", "checked"]) {
      if (el.hasAttribute && el.hasAttribute(a)) {
        const v = el.getAttribute(a);
        attrs.push(v === "" ? a : a + "=" + (v.length > 24 ? v.slice(0, 24) + "~" : v));
      }
    }
    if (attrs.length) s += "[" + attrs.join(" ") + "]";
    let text = "";
    for (const n of el.childNodes) if (n.nodeType === 3) text += n.textContent;
    text = text.trim().replace(/\s+/g, " ");
    if (text) s += ' "' + (text.length > 24 ? text.slice(0, 24) + "~" : text) + '"';
    return s;
  }

  // ---------------------------------------------------------------------------------------
  // Loading a side into a fresh iframe
  // ---------------------------------------------------------------------------------------
  function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }
  function withTimeout(p, ms, what) {
    return Promise.race([p, sleep(ms).then(() => { throw new Error("timeout: " + what); })]);
  }
  function frames(n) {
    // n animation frames of the document; a 100 ms timer stands in for a frame where rAF does not
    // run (a hidden page: Safari on a locked screen).
    let p = Promise.resolve();
    for (let i = 0; i < n; i++) {
      p = p.then(() => new Promise((resolve) => {
        let done = false;
        const go = () => { if (!done) { done = true; resolve(); } };
        try { win.requestAnimationFrame(go); } catch (e) { /* detached */ }
        setTimeout(go, 100);
      }));
    }
    return p;
  }

  // Headless Chrome can stop scheduling idle periods: requestIdleCallback then never fires until
  // a frame is produced (seen on 2026-10-30: after /docs/loading, every later oracle load stalled,
  // because the oracle hydrates from requestIdleCallback; one requestAnimationFrame released it).
  // While a document loads and its readiness hook runs, the host page requests a frame every
  // frame. The host shares the document's thread, so its frames give the document idle periods;
  // the document itself is not touched. Python stops it before the environment check.
  let kicking = false;
  function kickLoop() { if (kicking) requestAnimationFrame(kickLoop); }
  H.kick = function (on) {
    if (on && !kicking) { kicking = true; requestAnimationFrame(kickLoop); }
    if (!on) kicking = false;
    return kicking;
  };

  H.unload = function () {
    H.kick(false);
    const box = document.getElementById("box");
    if (box) box.textContent = "";
    frame = win = doc = null;
    return true;
  };

  H.load = async function (url, width, height, opts) {
    const t0 = performance.now();
    harnessErrors = [];
    H.unload();
    const errors = [];
    // The host shares the documents' origin: start every load with empty storage, then store what
    // the leg asks for (a data-theme leg's femtoColorScheme).
    try {
      localStorage.clear();
      sessionStorage.clear();
      for (const [k, v] of Object.entries((opts && opts.storage) || {})) localStorage.setItem(k, v);
    } catch (e) { errors.push("storage: " + e.message); }
    window.scrollTo(0, 0);
    H.kick(true);
    const box = document.getElementById("box");
    frame = document.createElement("iframe");
    frame.id = "frame";
    frame.style.width = width + "px";
    frame.style.height = height + "px";
    const loaded = new Promise((resolve) => frame.addEventListener("load", resolve, { once: true }));
    frame.src = url;
    box.appendChild(frame);
    try {
      await withTimeout(loaded, 60000, "iframe load " + url);
      win = frame.contentWindow;
      doc = frame.contentDocument;
      if (!doc) throw new Error("cannot read the iframe document of " + url + " (not same-origin?)");
    } catch (e) {
      errors.push(String(e && e.message ? e.message : e));
      return { errors, ms: performance.now() - t0 };
    }
    let finalUrl = null, finalPath = null;
    try { finalUrl = win.location.href; finalPath = win.location.pathname + win.location.search; } catch (e) { errors.push("location: " + e.message); }
    return { errors, url: finalUrl, path: finalPath, readyState: doc.readyState, contentType: doc.contentType, ms: performance.now() - t0 };
  };

  // The static readiness hook: the document is complete, its fonts are loaded and two frames passed.
  H.ready = async function (ms) {
    const errors = [];
    const t0 = performance.now();
    try {
      while (doc.readyState !== "complete") {
        if (performance.now() - t0 > ms) throw new Error("document.readyState is still " + doc.readyState);
        await sleep(25);
      }
      if (doc.fonts && doc.fonts.ready) await withTimeout(doc.fonts.ready, Math.max(1000, ms - (performance.now() - t0)), "document.fonts.ready");
      await frames(2);
    } catch (e) { errors.push("ready: " + (e && e.message ? e.message : e)); }
    return { errors, ms: performance.now() - t0 };
  };

  H.check = function (width, expect) {
    const errors = [];
    const head = doc.head || doc.documentElement;
    const style = doc.createElement("style");
    style.textContent =
      "harness-mq{order:1;z-index:1}" +
      "@media (prefers-color-scheme: dark){harness-mq{order:2}}" +
      "@media (width: " + width + "px){harness-mq{z-index:7}}";
    const probe = doc.createElement("harness-mq");
    head.appendChild(style);
    head.appendChild(probe);
    const cs = win.getComputedStyle(probe);
    const info = {
      innerWidth: win.innerWidth,
      mqWidth: win.matchMedia("(width: " + width + "px)").matches,
      cssWidth: cs.getPropertyValue("z-index") === "7",
      dark: win.matchMedia("(prefers-color-scheme: dark)").matches,
      cssDark: cs.getPropertyValue("order") === "2",
      theme: doc.documentElement.getAttribute("data-theme"),
      visibility: doc.visibilityState,
    };
    probe.remove();
    style.remove();
    if (info.innerWidth !== width) errors.push("viewport: innerWidth " + info.innerWidth + " != " + width);
    if (!info.mqWidth || !info.cssWidth) errors.push("viewport: (width: " + width + "px) media query does not match (matchMedia " + info.mqWidth + ", CSS " + info.cssWidth + ")");
    if (expect && expect.media) {
      const want = expect.media === "dark";
      if (info.dark !== want || info.cssDark !== want)
        errors.push("color scheme: expected prefers-color-scheme " + expect.media + ", matchMedia dark=" + info.dark + ", CSS dark=" + info.cssDark);
    }
    if (expect && "theme" in expect && (expect.theme || null) !== info.theme)
      errors.push("data-theme on html is " + info.theme + ", expected " + expect.theme);
    info.errors = errors;
    return info;
  };

  // ---------------------------------------------------------------------------------------
  // Animations: finish transitions and finite animations, pause infinite ones at 0 (femto's rule)
  // ---------------------------------------------------------------------------------------
  function shadowRoots(root) {
    const out = [];
    const visit = (r) => {
      for (const el of r.querySelectorAll("*")) if (el.shadowRoot) { out.push(el.shadowRoot); visit(el.shadowRoot); }
    };
    visit(root);
    return out;
  }
  function allAnimations() {
    const set = new Set(doc.getAnimations());
    for (const r of shadowRoots(doc)) for (const a of r.getAnimations()) set.add(a);
    return set;
  }
  H.freeze = function () {
    let finished = 0, paused = 0;
    if (!doc) return { finished, paused };
    for (let round = 0; round < 3; round++) {
      let changed = 0;
      for (const a of allAnimations()) {
        const t = a.effect ? a.effect.getComputedTiming() : null;
        if (t && t.endTime === Infinity) {
          if (a.playState !== "paused" || a.currentTime !== 0) { a.pause(); a.currentTime = 0; paused++; changed++; }
        } else if (a.playState !== "finished") {
          try { a.finish(); finished++; changed++; } catch (e) { a.cancel(); }
        }
      }
      if (!changed) break;
    }
    return { finished, paused };
  };

  // Chrome and Safari run ::file-selector-button transitions on a UA shadow element that
  // getAnimations() does not return; a transient "transition: none !important" cancels them (jumps
  // to the end value), and removing it restarts nothing. femto's settle().
  function settleFileButtons(nodes) {
    if (!cfg.pseudos.includes("::file-selector-button")) return 0;
    const files = nodes.map((n) => n.el).filter((el) => el.localName === "input" && (el.getAttribute("type") || "").toLowerCase() === "file");
    if (!files.length) return 0;
    const t0 = performance.now();
    const roots = new Set(files.map((el) => el.getRootNode()));
    const styles = [];
    for (const r of roots) {
      const st = doc.createElement("style");
      st.textContent = "input[type=file]::file-selector-button { transition: none !important; }";
      (r === doc ? doc.head || doc.documentElement : r).appendChild(st);
      styles.push(st);
    }
    for (const el of files) win.getComputedStyle(el, "::file-selector-button").getPropertyValue("background-color");
    for (const st of styles) st.remove();
    for (const el of files) win.getComputedStyle(el, "::file-selector-button").getPropertyValue("background-color");
    return performance.now() - t0;
  }

  // ---------------------------------------------------------------------------------------
  // Collection: the element tree, attributes, own text, computed styles and pseudo-elements
  // ---------------------------------------------------------------------------------------
  let PROPS = null;
  function props() {
    if (PROPS) return PROPS;
    const cs = win.getComputedStyle(doc.documentElement);
    const list = [];
    for (let i = 0; i < cs.length; i++) if (!cs[i].startsWith("--")) list.push(cs[i]);
    return (PROPS = list);
  }
  function read(cs, P) {
    const v = new Array(P.length);
    for (let j = 0; j < P.length; j++) v[j] = cs.getPropertyValue(P[j]);
    return v;
  }
  function absent(c) { return c === "none" || c === "normal" || c === ""; }
  function collectStyles(el, P, iDisplay) {
    const base = read(win.getComputedStyle(el), P);
    const s = { "": base };
    const want = cfg.pseudos;
    for (const ps of ["::before", "::after"]) {
      if (!want.includes(ps)) continue;
      const cs = win.getComputedStyle(el, ps);
      const c = cs.getPropertyValue("content");
      s[ps] = absent(c) ? { absent: c || "none" } : read(cs, P);
    }
    const t = el.localName;
    const disp = base[iDisplay] || "";
    if (want.includes("::marker") && (t === "li" || t === "summary" || disp.includes("list-item"))) s["::marker"] = read(win.getComputedStyle(el, "::marker"), P);
    if (want.includes("::placeholder") && el.hasAttribute("placeholder")) s["::placeholder"] = read(win.getComputedStyle(el, "::placeholder"), P);
    if (want.includes("::file-selector-button") && t === "input" && (el.getAttribute("type") || "").toLowerCase() === "file") s["::file-selector-button"] = read(win.getComputedStyle(el, "::file-selector-button"), P);
    if (want.includes("::backdrop") && t === "dialog") s["::backdrop"] = read(win.getComputedStyle(el, "::backdrop"), P);
    return s;
  }
  // An element's own text: its child text nodes, read run by run. A run is a stretch of adjacent
  // text nodes (a comment between them, React's <!-- --> separator, renders nothing and does not end
  // it); an element child ends it. Where the element preserves whitespace (pre, pre-wrap, ...) the
  // runs are joined as they are. Elsewhere each run's whitespace counts only where it renders: a
  // whitespace-only run, or a run's leading or trailing whitespace, is one space when the browser
  // gives it a box with an inline size (a Range client rect wider than 0, or taller in a vertical
  // writing mode), and nothing when it collapses away (between blocks, flex or grid items, table
  // parts, at the start or end of a line, after another space, inside display: none); whitespace
  // inside a run's text collapses to one space. So a space that shows between two inline siblings
  // (the footer's two inline <p>s) is compared, and source whitespace that renders nothing is not.
  // "Whitespace" here is space, tab and line feed, CSS's document white space (CSS Text 3, section 4)
  // less the carriage return: CSS treats a CR as a space, but Firefox 160 renders it as nothing, so
  // it is text and compared exactly. Parsing turns every source CR into a line feed, so a CR in the
  // DOM comes only from &#13; or a script. JavaScript's \s also matches U+00A0
  // (no-break space), U+FEFF and the other Unicode space separators, which CSS never collapses, so
  // they are text and compared as they are ("Code&nbsp; licensed" is not "Code licensed"). Form feed
  // is not document white space either (a control character CSS renders as a visible glyph).
  const DOC_WS_LEAD = /^[ \t\n]*/, DOC_WS_TRAIL = /[ \t\n]*$/, DOC_WS_RUN = /[ \t\n]+/g;
  function rendersInline(run, from, to, vertical) {
    const r = doc.createRange();
    let at = 0, started = false;
    for (const node of run) {
      const len = node.data.length;
      if (!started && from <= at + len) { r.setStart(node, from - at); started = true; }
      if (started && to <= at + len) { r.setEnd(node, to - at); break; }
      at += len;
    }
    for (const rect of r.getClientRects()) if ((vertical ? rect.height : rect.width) > 0) return true;
    return false;
  }
  function ownText(el, cs) {
    const ws = cs.getPropertyValue("white-space-collapse") || cs.getPropertyValue("white-space");
    if (KEEP_SPACE.test(ws)) {
      let t = "";
      for (const c of el.childNodes) if (c.nodeType === 3) t += c.data;
      return t;
    }
    const vertical = !/^horizontal/.test(cs.getPropertyValue("writing-mode") || "horizontal-tb");
    let out = "", run = [];
    const flush = () => {
      const data = run.map((n) => n.data).join("");
      if (data) {
        const lead = DOC_WS_LEAD.exec(data)[0].length, trail = DOC_WS_TRAIL.exec(data)[0].length;
        if (lead === data.length) {
          if (rendersInline(run, 0, data.length, vertical)) out += " ";
        } else {
          if (lead && rendersInline(run, 0, lead, vertical)) out += " ";
          out += data.slice(lead, data.length - trail).replace(DOC_WS_RUN, " ");
          if (trail && rendersInline(run, data.length - trail, data.length, vertical)) out += " ";
        }
      }
      run = [];
    };
    for (const c of el.childNodes) {
      if (c.nodeType === 3) run.push(c);
      else if (c.nodeType !== 8) flush();
    }
    flush();
    return out;
  }
  // An element's tree path from <html> (as pathOf() names compared elements): each step its tag and
  // its index among its parent's element children that are compared (skipped tags left out), with
  // "#shadow" where the path enters an open shadow root.
  function treePath(el) {
    const steps = [];
    let e = el;
    while (e && e !== doc.documentElement) {
      const p = e.parentNode;
      if (!p) break;
      const shadow = p.nodeType === 11 && !!p.host;
      let k = 0;
      for (let c = p.firstElementChild; c && c !== e; c = c.nextElementSibling) {
        if (!SKIP_TAGS.has(c.localName) && !HARNESS_TAGS.has(c.localName)) k++;
      }
      steps.unshift((shadow ? "#shadow > " : "") + e.localName + ":" + k);
      e = shadow ? p.host : p;
    }
    return [doc.documentElement.localName, ...steps].join(" > ");
  }
  function matchSet(roots, sel) {
    const set = new Set();
    for (const r of roots) for (const e of r.querySelectorAll(sel)) set.add(e);
    return set;
  }

  // The document's head data, compared as "head" records when the root is html: the title, every
  // <meta>, every <link> that is not a stylesheet or a fetch hint (their effects are in the
  // computed styles and the request log), <base>, and every data-block <script> (a type that is not
  // JavaScript: the oracle's application/ld+json structured data, an importmap, any other). Keyed by
  // tag and identifying attributes, with #2, #3 for repeats; the value is the element's other
  // attributes (the title's: its text). A data block's content is compared too: JSON as one value
  // per leaf ("$.version", "$.author.name", "$.keywords[2]", each JSON-encoded), so key order and
  // whitespace never count and a changed leaf is one record; other content (or JSON that does not
  // parse) as its text, under "(text)". Like meta and link, these are read from the whole document
  // outside <template>, wherever they sit.
  //
  // A data block that repeats an earlier one of the same key exactly (the same attributes and the
  // same leaves, or the same text) is counted once, before repeats are numbered: an identical copy
  // adds no data. The oracle needs it: on /docs/progress React's client render after a hydration
  // mismatch (error #418, whenever the server's and the client's random progress values differ)
  // inserts a second, identical JSON-LD block, so the hydrated head holds one block on some loads
  // and two on others (round 3, 2026-10-31). A copy that differs in anything is still its own #2
  // entry. The collapsed copies are counted per side (headRepeats), never hidden.
  function canon(vals) {
    return JSON.stringify(Object.keys(vals).sort().map((k) => [k, vals[k]]));
  }
  const HEAD_SKIP_RELS = new Set(["stylesheet", "preload", "modulepreload", "prefetch", "preconnect", "dns-prefetch", "prerender"]);
  const XHTML = "http://www.w3.org/1999/xhtml";
  // The HTML standard's JavaScript MIME type essences, plus "" (no type) and "module": these scripts
  // run, and only their effects are compared.
  const JS_TYPES = new Set(["", "module", "application/ecmascript", "application/javascript", "application/x-ecmascript",
    "application/x-javascript", "text/ecmascript", "text/javascript", "text/javascript1.0", "text/javascript1.1",
    "text/javascript1.2", "text/javascript1.3", "text/javascript1.4", "text/javascript1.5", "text/jscript",
    "text/livescript", "text/x-ecmascript", "text/x-javascript"]);
  function flattenJson(v, path, out) {
    if (Array.isArray(v)) {
      if (!v.length) out[path] = "[]";
      v.forEach((x, i) => flattenJson(x, path + "[" + i + "]", out));
    } else if (v !== null && typeof v === "object") {
      const ks = Object.keys(v);
      if (!ks.length) out[path] = "{}";
      for (const k of ks) flattenJson(v[k], path + (/^[A-Za-z_$@][\w$@-]*$/.test(k) ? "." + k : "[" + JSON.stringify(k) + "]"), out);
    } else {
      out[path] = JSON.stringify(v);
    }
  }
  function collectHead() {
    const out = new Map();
    out.repeats = 0;
    const put = (key, vals, dataBlock) => {
      let k = key, n = 1;
      const c = dataBlock ? canon(vals) : null;
      while (out.has(k)) {
        if (dataBlock && canon(out.get(k)) === c) { out.repeats++; return; }
        k = key + "#" + ++n;
      }
      out.set(k, vals);
    };
    put("title", { text: doc.title });
    for (const el of doc.querySelectorAll("meta, link, base, script")) {
      if (el.namespaceURI !== XHTML || el.closest("template")) continue;
      const attrs = Object.create(null);
      for (const a of el.attributes) attrs[a.name] = a.value;
      let key;
      if (el.localName === "script") {
        const type = (attrs.type || "").split(";")[0].trim().toLowerCase();
        if (!("type" in attrs) || JS_TYPES.has(type)) continue;
        key = "script[type=" + type + "]";
        delete attrs.type;
        const text = el.textContent;
        let parsed;
        if (/(^|[/+])json$/.test(type) || type === "importmap" || type === "speculationrules") {
          try { parsed = JSON.parse(text); } catch (e) { parsed = undefined; }
        }
        if (parsed !== undefined) flattenJson(parsed, "$", attrs);
        else attrs["(text)"] = text;
        put(key, attrs, true);
        continue;
      }
      if (el.localName === "base") {
        put("base", attrs);
        continue;
      }
      if (el.localName === "meta") {
        const id = ["name", "property", "http-equiv", "itemprop"].find((a) => a in attrs);
        key = id ? "meta[" + id + "=" + attrs[id] + "]" : ("charset" in attrs ? "meta[charset]" : "meta");
        if (id) delete attrs[id];
      } else {
        const rels = (attrs.rel || "").toLowerCase().split(/[ \t\n\f\r]+/).filter(Boolean).sort();
        if (rels.some((r) => HEAD_SKIP_RELS.has(r))) continue;
        key = "link[rel=" + rels.join(" ") + "]";
        delete attrs.rel;
        for (const a of ["sizes", "hreflang"]) if (a in attrs) { key += "[" + a + "=" + attrs[a] + "]"; delete attrs[a]; }
      }
      if ("media" in attrs) { key += "[media=" + attrs.media + "]"; delete attrs.media; }
      put(key, attrs);
    }
    return out;
  }

  H.collect = async function (side, rootSel) {
    const t0 = performance.now();
    const errors = [];
    const fr0 = H.freeze();
    PROPS = null;
    const root = rootSel ? doc.querySelector(rootSel) : doc.documentElement;
    if (!root) {
      errors.push("root " + rootSel + " not found");
      store[side] = null;
      return { errors };
    }
    const roots = [doc, ...shadowRoots(doc)];
    // Selector sets, evaluated once per side: registry entries and masks.
    const entrySets = compiled.map((e) => e.sel ? matchSet(roots, e.sel) : null);
    const maskSets = maskDefs.map((m) => matchSet(roots, m.sel));
    const nodes = [];
    const maskCounts = {};
    const visitList = (parent, container, shadow, inheritedNoText) => {
      const list = [];
      let k = 0;
      for (let c = container.firstElementChild; c; c = c.nextElementSibling) {
        const t = c.localName;
        if (SKIP_TAGS.has(t) || HARNESS_TAGS.has(t)) continue;
        list.push(add(c, parent, k++, shadow, inheritedNoText));
      }
      return list;
    };
    const add = (el, parent, k, shadow, inheritedNoText) => {
      const n = { i: nodes.length, el, tag: el.localName, parent, k, sh: shadow, kids: [], skids: null,
                  mc: false, mt: inheritedNoText, ma: null, mp: null, size: 1 };
      nodes.push(n);
      maskDefs.forEach((m, j) => {
        if (!maskSets[j].has(el)) return;
        maskCounts[m.id] = (maskCounts[m.id] || 0) + 1;
        if (m.contents) n.mc = true;
        if (m.text) n.mt = true;
        if (m.attributes.size) { n.ma = n.ma || new Set(); for (const a of m.attributes) n.ma.add(a); }
        if (m.properties.size) { n.mp = n.mp || new Set(); for (const p of m.properties) n.mp.add(p); }
      });
      if (!n.mc) {
        if (el.shadowRoot) n.skids = visitList(n.i, el.shadowRoot, true, n.mt);
        n.kids = visitList(n.i, el, false, n.mt);
      }
      return n.i;
    };
    add(root, null, 0, false, false);
    for (let i = nodes.length - 1; i > 0; i--) nodes[nodes[i].parent].size += nodes[i].size;
    // Chrome does not update the style of a skipped subtree (the content of a closed <details> is
    // content-visibility: hidden) until something reads it, and a transition that such a read starts
    // stays at its start value there and was not in getAnimations() when the freeze above ran. Seen
    // on 2026-10-30 (p0-gate-self-cf-2, Chrome, /docs/overflow-auto dark 800, side A): the links in
    // the closed header dropdown and side-nav details read their UA colors and the dropdown list
    // opacity 1. So read every element's style (and ::before, ::after) once, then freeze again.
    for (const n of nodes) {
      win.getComputedStyle(n.el).getPropertyValue("color");
      win.getComputedStyle(n.el, "::before").getPropertyValue("color");
      win.getComputedStyle(n.el, "::after").getPropertyValue("color");
    }
    const fr1 = H.freeze();
    const settleMs = settleFileButtons(nodes);
    const P = props();
    const iDisplay = P.indexOf("display");
    let pseudo = 0;
    for (const n of nodes) {
      const el = n.el;
      n.s = collectStyles(el, P, iDisplay);
      for (const k of Object.keys(n.s)) if (k && Array.isArray(n.s[k])) pseudo++;
      const attrs = Object.create(null);
      for (const a of el.attributes) attrs[a.name] = a.value;
      n.attrs = attrs;
      n.text = n.mt ? "" : ownText(el, win.getComputedStyle(el));
      n.label = label(el);
      if (n.parent === null) n.rootLabel = rootSel || "html";
    }
    const selSets = entrySets.map((set) => {
      if (!set) return null;
      const out = new Set();
      for (const n of nodes) if (set.has(n.el)) out.add(n.i);
      return out;
    });
    for (const n of nodes) n.el = null;  // keep no references into a document that will be removed
    const head = rootSel ? null : collectHead();
    // With --root-a/--root-b the records still carry the document's own tree paths (the root's path
    // from html, then down), so a registry path pattern means the same in a section comparison as
    // in a whole-page one and is judged on the same reference documents.
    const rootPath = rootSel ? treePath(root) : null;
    store[side] = { nodes, props: P, selSets, maskCounts, rootSel: rootSel || null, rootPath, head };
    store[side].reach = entryReach(store[side]);
    const fr = H.freeze();
    return {
      elements: nodes.length, pseudo, props: P.length, maskCounts, settleMs, freezeBefore: fr0, freezeTouched: fr1, freezeAfter: fr,
      head: head ? head.size : null, headRepeats: head ? head.repeats : null, requests: resources(),
      ms: performance.now() - t0, errors: errors.concat(harnessErrors.splice(0)),
    };
  };

  // What each registry entry reaches on this side's live document, whatever records there are: the
  // compared elements its selector and path match, or the head keys its path matches. H.diff's
  // breadth guard judges them, so markup only a script adds (a class set at run time) and the
  // pattern dialect (JavaScript's RegExp) count exactly as they apply.
  function entryReach(snap) {
    return compiled.map((e, k) => {
      const out = [];
      if (e.kind === "head") {
        if (snap.head) for (const key of snap.head.keys()) if (e.path(key)) out.push(key);
        return out;
      }
      const set = snap.selSets[k];
      for (const n of snap.nodes) if ((!set || set.has(n.i)) && e.path(pathOf(snap, n))) out.push(n.i);
      return out;
    });
  }

  // What the document fetched, from its own Resource Timing entries and those of every frame inside
  // it that the page can read (same-origin iframes, srcdoc and about:blank frames included, at any
  // depth, those in open shadow roots included): the browser's network log of each document, so it
  // sees every load that finished before the collect (fetch() and XHR, parsed and script-inserted
  // <link>s, <script>s, <img>s and iframes, CSS url()s and fonts) whatever code or markup started it,
  // and no URL that is only text. It does not see a worker's loads (a worker keeps its own timeline),
  // a frame in a closed shadow root, or a frame it cannot read (another origin, or sandboxed without
  // allow-same-origin), which it lists under unreadable; the proxy's CSP reports cover the first
  // two (compare.py csp_loads), and static_checks.py also judges worker scripts. Returns the http(s) URLs on another origin than the top
  // document's (criterion 15; compare.py decides which sides must have none). Each document's
  // default buffer holds 250 entries and drops later ones, so a full buffer is reported.
  const RT_BUFFER = 250;
  function resources() {
    const out = { origin: null, total: 0, cross: [], full: false, frames: 0, unreadable: [] };
    try {
      const origin = win.location.origin;
      const seen = new Set();
      const seenWin = new Set();
      out.origin = origin;
      const visit = (w, where) => {
        let entries;
        try { entries = w.performance.getEntriesByType("resource"); }
        catch (e) { out.unreadable.push(where); return; }
        out.total += entries.length;
        if (entries.length >= RT_BUFFER) out.full = true;
        for (const e of entries) {
          let u;
          try { u = new URL(e.name); } catch (x) { continue; }
          if ((u.protocol !== "http:" && u.protocol !== "https:") || u.origin === origin || seen.has(u.href)) continue;
          seen.add(u.href);
          out.cross.push(u.href);
        }
        // Child frames: window.frames lists those of the document tree only, so the iframe, frame,
        // object and embed elements of every open shadow root (declarative ones included) are read
        // as well. A closed shadow root cannot be read; the proxy's CSP reports cover it.
        const kids = [];
        let n = 0;
        try { n = w.frames.length; } catch (e) { n = 0; }
        for (let i = 0; i < n; i++) kids.push(() => w.frames[i]);
        let d = null;
        try { d = w.document; } catch (e) { d = null; }
        if (d) {
          for (const r of shadowRoots(d)) {
            for (const el of r.querySelectorAll("iframe, frame, object, embed")) {
              kids.push(() => {
                if (el.localName === "embed") {
                  const sd = el.getSVGDocument ? el.getSVGDocument() : null;
                  return sd ? sd.defaultView : (el.contentWindow || null);
                }
                return el.contentWindow;
              });
            }
          }
        }
        kids.forEach((get, i) => {
          let f, label;
          try {
            f = get();
            if (!f || seenWin.has(f)) return;
            seenWin.add(f);
            label = f.location.href;
          } catch (e) { out.unreadable.push("frame " + i + " of " + where); return; }
          out.frames++;
          visit(f, label);
        });
      };
      seenWin.add(win);
      visit(win, win.location.href);
    } catch (e) {
      out.error = String(e && e.message ? e.message : e);
    }
    return out;
  }

  // ---------------------------------------------------------------------------------------
  // Diff: align sibling lists by keyed LCS, then compare paired elements
  // ---------------------------------------------------------------------------------------
  function pathOf(snap, n) {
    if (n.p) return n.p;
    if (n.parent === null) return (n.p = snap.rootPath || n.tag);
    const up = pathOf(snap, snap.nodes[n.parent]);
    return (n.p = up + " > " + (n.sh ? "#shadow > " : "") + n.tag + ":" + n.k);
  }

  // Two 32-bit FNV-1a hashes of a string, folded into running state h ([h1, h2]).
  function mix(h, str) {
    let a = h[0], b = h[1];
    for (let i = 0; i < str.length; i++) {
      const c = str.charCodeAt(i);
      a = Math.imul(a ^ c, 16777619) >>> 0;
      b = Math.imul(b ^ c, 2246822519) >>> 0;
    }
    a = Math.imul(a ^ 0x1f, 16777619) >>> 0;  // separator, so "ab"+"c" differs from "a"+"bc"
    b = Math.imul(b ^ 0x1f, 2246822519) >>> 0;
    return [a, b];
  }
  // A whole-subtree signature: tag, attributes, own text and the children's signatures, without what
  // a mask hides (masked attributes, masked text, a contents mask's subtree). Equal signatures mean
  // equal compared content apart from computed styles.
  function sigOf(snap, n) {
    if (n.sg !== undefined) return n.sg;
    let h = mix([2166136261, 3735928559], n.tag);
    for (const name of Object.keys(n.attrs).sort()) if (!(n.ma && n.ma.has(name))) h = mix(h, name + "=" + n.attrs[name]);
    if (!n.mt && !n.mc) h = mix(h, "\u0001" + n.text);
    for (const c of n.kids) h = mix(h, sigOf(snap, snap.nodes[c]));
    if (n.skids) {
      h = mix(h, "#shadow");
      for (const c of n.skids) h = mix(h, sigOf(snap, snap.nodes[c]));
    }
    return (n.sg = h[0].toString(36) + ":" + h[1].toString(36));
  }
  const SOFT_ATTRS = ["id", "class", "type", "name", "role"];
  function softKey(n) {
    let k = n.tag;
    for (const a of SOFT_ATTRS) if (a in n.attrs) k += "\u0001" + a + "=" + (a === "class" ? n.attrs[a].split(/[ \t\n\f\r]+/).filter(Boolean).sort().join(" ") : n.attrs[a]);
    return k;
  }

  // Longest common subsequence of two key lists: [[i, j], ...] in order. Matching equal heads
  // greedily during the walk back is always optimal. Lists too long for the table (after the
  // common prefix and suffix are trimmed) fall back to pairing by position, counted in the result.
  const LCS_MAX_CELLS = 4e6;
  let alignFallbacks = 0;
  function lcsPairs(a, b) {
    const n = a.length, m = b.length;
    if (!n || !m) return [];
    if (n * m > LCS_MAX_CELLS) {
      alignFallbacks++;
      return null;
    }
    const W = m + 1;
    const L = new Uint32Array((n + 1) * W);
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        L[i * W + j] = a[i] === b[j] ? L[(i + 1) * W + j + 1] + 1 : Math.max(L[(i + 1) * W + j], L[i * W + j + 1]);
      }
    }
    const out = [];
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (a[i] === b[j]) { out.push([i, j]); i++; j++; }
      else if (L[(i + 1) * W + j] >= L[i * W + j + 1]) i++;
      else j++;
    }
    return out;
  }

  // Align two sibling lists (node indexes into A.nodes and B.nodes): [[ia | null, ib | null], ...].
  function alignLists(A, B, ka, kb) {
    const out = [];
    const keys = [(S, i) => sigOf(S, S.nodes[i]), (S, i) => softKey(S.nodes[i]), (S, i) => S.nodes[i].tag];
    const byPosition = (as, bs) => {
      const k = Math.min(as.length, bs.length);
      for (let i = 0; i < k; i++) out.push([as[i], bs[i]]);
      for (let i = k; i < as.length; i++) out.push([as[i], null]);
      for (let i = k; i < bs.length; i++) out.push([null, bs[i]]);
    };
    const pass = (as, bs, level) => {
      if (!as.length || !bs.length || level === keys.length) return byPosition(as, bs);
      const fa = as.map((i) => keys[level](A, i)), fb = bs.map((i) => keys[level](B, i));
      let p = 0;
      while (p < as.length && p < bs.length && fa[p] === fb[p]) p++;
      let q = 0;
      while (q < as.length - p && q < bs.length - p && fa[as.length - 1 - q] === fb[bs.length - 1 - q]) q++;
      for (let i = 0; i < p; i++) out.push([as[i], bs[i]]);
      const ma = as.slice(p, as.length - q), mb = bs.slice(p, bs.length - q);
      const pairs = lcsPairs(fa.slice(p, as.length - q), fb.slice(p, bs.length - q));
      if (pairs === null) byPosition(ma, mb);
      else {
        let i0 = 0, j0 = 0;
        for (const [i, j] of pairs) {
          pass(ma.slice(i0, i), mb.slice(j0, j), level + 1);
          out.push([ma[i], mb[j]]);
          i0 = i + 1;
          j0 = j + 1;
        }
        pass(ma.slice(i0), mb.slice(j0), level + 1);
      }
      for (let i = q; i > 0; i--) out.push([as[as.length - i], bs[bs.length - i]]);
    };
    pass(ka, kb, 0);
    return out;
  }

  function diffStyles(res, na, nb, path, P) {
    const keys = new Set([...Object.keys(na.s), ...Object.keys(nb.s)]);
    const skip = (na.mp || nb.mp) ? new Set([...(na.mp || []), ...(nb.mp || [])]) : null;
    for (const ps of keys) {
      const a = na.s[ps], b = nb.s[ps];
      // ::marker is collected by display; a display difference is reported on the element itself.
      if (!a || !b) continue;
      const base = { kind: "style", path, label: nb.label, pseudo: ps };
      const aAbs = !Array.isArray(a), bAbs = !Array.isArray(b);
      if (aAbs || bAbs) {
        if (aAbs && bAbs) continue;
        const ci = P.indexOf("content");
        addRecord(res, Object.assign(base, { prop: "content", a: aAbs ? a.absent : a[ci], b: bAbs ? b.absent : b[ci], presence: true }), na, nb);
        continue;
      }
      for (let j = 0; j < P.length; j++) {
        if (skip && skip.has(P[j])) continue;
        if (a[j] !== b[j] && !same(a[j], b[j]) && !sameValue(a[j], b[j])) addRecord(res, Object.assign({}, base, { prop: P[j], a: a[j], b: b[j] }), na, nb);
      }
    }
  }

  function diffText(res, na, nb, path) {
    if (!na.mc && !nb.mc && !na.mt && !nb.mt && na.text !== nb.text) addRecord(res, { kind: "text", path, label: nb.label, a: na.text, b: nb.text }, na, nb);
  }

  function diffChildren(res, A, B, na, nb, P) {
    if (na.mc || nb.mc) return;
    diffKids(res, A, B, na.kids, nb.kids, P);
    if (na.skids || nb.skids) diffKids(res, A, B, na.skids || [], nb.skids || [], P);
  }

  function diffPair(res, A, B, na, nb, P) {
    const path = pathOf(B, nb);
    pathOf(A, na);
    const skip = new Set([...(na.ma || []), ...(nb.ma || [])]);
    const names = new Set([...Object.keys(na.attrs), ...Object.keys(nb.attrs)]);
    for (const name of [...names].sort()) {
      if (skip.has(name)) continue;
      const va = name in na.attrs ? na.attrs[name] : null;
      const vb = name in nb.attrs ? nb.attrs[name] : null;
      if (!sameValue(va, vb)) addRecord(res, { kind: "attribute", path, label: nb.label, prop: name, a: va, b: vb }, na, nb);
    }
    diffText(res, na, nb, path);
    diffStyles(res, na, nb, path, P);
    diffChildren(res, A, B, na, nb, P);
  }

  function structure(res, A, B, ca, cb) {
    const one = cb || ca;
    const rec = { kind: "structure", path: cb ? pathOf(B, cb) : pathOf(A, ca), label: one.label,
                  a: ca ? ca.tag : null, b: cb ? cb.tag : null,
                  change: !ca ? "only-b" : !cb ? "only-a" : "tag", size_a: ca ? ca.size : 0, size_b: cb ? cb.size : 0 };
    if (ca && cb) {
      rec.label_a = ca.label;
      rec.path_a = pathOf(A, ca);
    }
    addRecord(res, rec, ca, cb);
  }

  function diffKids(res, A, B, ka, kb, P) {
    for (const [x, y] of alignLists(A, B, ka, kb)) {
      const ca = x === null ? null : A.nodes[x];
      const cb = y === null ? null : B.nodes[y];
      if (ca && cb && ca.tag === cb.tag) { diffPair(res, A, B, ca, cb, P); continue; }
      structure(res, A, B, ca, cb);
      if (ca && cb) {
        // Another element in the same place: its attributes and styles belong to another element
        // type, but its own text and everything below it are still compared.
        diffText(res, ca, cb, pathOf(B, cb));
        diffChildren(res, A, B, ca, cb, P);
      }
    }
  }

  function diffHead(res, A, B) {
    const keys = [...new Set([...A.head.keys(), ...B.head.keys()])];
    for (const key of keys) {
      const va = A.head.get(key), vb = B.head.get(key);
      const names = new Set([...Object.keys(va || {}), ...Object.keys(vb || {})]);
      if (!names.size) names.add("(element)");
      for (const name of [...names].sort()) {
        const a = va ? (name in va ? va[name] : (name === "(element)" ? "present" : null)) : null;
        const b = vb ? (name in vb ? vb[name] : (name === "(element)" ? "present" : null)) : null;
        if (!sameValue(a, b)) addRecord(res, { kind: "head", path: key, label: key, prop: name, a, b }, null, null);
      }
    }
  }

  function pct(x) { return (x * 100).toFixed(1) + "%"; }
  const BREADTH_REF = " (tests/README.md, Divergence registry, Breadth)";

  // The registry's per-document limits, again on the live documents of this cell: an entry whose
  // selector and path reach more than lim.doc of either side's compared elements (head: head keys),
  // past lim.floor, is a harness error and is not applied here; so are the entries of a kind that
  // together reach more than lim.union. Route-scoped entries included: a route scope narrows where
  // an entry applies, not how much of a page it may cover.
  function breadthGuard(A, B, errors) {
    const lim = cfg.breadth || {};
    const off = new Set();
    const sides = [["A", A], ["B", B]];
    const total = (S, kind) => (kind === "head" ? (S.head ? S.head.size : 0) : S.nodes.length);
    const unit = (kind) => (kind === "head" ? "head keys" : "compared elements");
    for (const e of compiled) {
      for (const [name, S] of sides) {
        const n = S.reach[e.k].length, t = total(S, e.kind);
        if (t && n > lim.floor && n / t > lim.doc) {
          errors.push("breadth: registry entry " + e.id + " matches " + n + " of the " + t + " " + unit(e.kind) + " (" +
                      pct(n / t) + ") of side " + name + "'s document in this cell, more than " + pct(lim.doc) +
                      " of one document, so it is not applied here" + BREADTH_REF);
          off.add(e.k);
          break;
        }
      }
    }
    for (const kind of new Set(compiled.map((e) => e.kind))) {
      const members = compiled.filter((e) => e.kind === kind && !off.has(e.k));
      if (members.length < 2) continue;
      for (const [name, S] of sides) {
        const u = new Set();
        for (const e of members) for (const x of S.reach[e.k]) u.add(x);
        const t = total(S, kind);
        if (t && u.size > lim.floor && u.size / t > lim.union) {
          errors.push("breadth: the " + members.length + " " + kind + " entries applied in this cell (" +
                      members.map((e) => e.id).join(", ") + ") together match " + u.size + " of the " + t + " " +
                      unit(kind) + " (" + pct(u.size / t) + ") of side " + name + "'s document, more than " +
                      pct(lim.union) + ", so none of them is applied here" + BREADTH_REF);
          for (const e of members) off.add(e.k);
          break;
        }
      }
    }
    return off;
  }

  // The registered records of a cell may cover at most lim.cover of either document (elements, a
  // structure record counting its whole subtree; head keys apart), past lim.floor: a registry stands
  // in for a few explained differences, never for most of a page (a page one side does not have).
  function coverage(A, B, errors) {
    const lim = cfg.breadth || {};
    const by = Object.entries(covered.by).sort((x, y) => y[1] - x[1]).slice(0, 4).map(([id, n]) => id + " " + n).join(", ");
    const check = (name, n, t, what) => {
      if (t && n > lim.floor && n / t > lim.cover)
        errors.push("coverage: the registered differences of this cell cover " + n + " of the " + t + " " + what + " (" +
                    pct(n / t) + ") of side " + name + "'s document, more than " + pct(lim.cover) + ": registry entries " +
                    "explain differences, they never stand in for most of a page (a structure record covers its " +
                    "whole subtree; the entries by what they cover: " + by + "; tests/README.md, Divergence registry)");
    };
    const count = (arr) => { let n = 0; for (let i = 0; i < arr.length; i++) n += arr[i]; return n; };
    check("A", count(covered.a), A.nodes.length, "compared elements");
    check("B", count(covered.b), B.nodes.length, "compared elements");
    if (A.head && B.head) {
      check("A", covered.headA.size, A.head.size, "head keys");
      check("B", covered.headB.size, B.head.size, "head keys");
    }
  }

  H.diff = function () {
    const t0 = performance.now();
    const res = newResult();
    const A = store.a, B = store.b;
    if (!A || !B) throw new Error("diff needs both snapshots");
    const errors = [];
    alignFallbacks = 0;
    if (A.props.join() !== B.props.join()) errors.push("computed property lists differ between the sides");
    disabled = breadthGuard(A, B, errors);
    covered = { a: new Uint8Array(A.nodes.length), b: new Uint8Array(B.nodes.length), headA: new Set(), headB: new Set(), by: {} };
    const ra = A.nodes[0], rb = B.nodes[0];
    try {
      if (A.head && B.head) diffHead(res, A, B);
      if (ra.tag !== rb.tag) {
        structure(res, A, B, ra, rb);
        diffText(res, ra, rb, pathOf(B, rb));
        diffChildren(res, A, B, ra, rb, B.props);
      } else {
        diffPair(res, A, B, ra, rb, B.props);
      }
      coverage(A, B, errors);
    } finally {
      covered = null;
      disabled = new Set();
    }
    res.ms = performance.now() - t0;
    res.errors = errors.concat(harnessErrors.splice(0));
    res.elements = { a: A.nodes.length, b: B.nodes.length };
    res.alignFallbacks = alignFallbacks;
    return res;
  };

  // ---------------------------------------------------------------------------------------
  // Screenshots: scroll to the top, cover the masked boxes (pixels: true) of the live side
  // ---------------------------------------------------------------------------------------
  H.prepShot = async function () {
    const a = doc.activeElement;
    if (a && a !== doc.body && a.blur) a.blur();
    H.freeze();
    const scrolled = win.scrollX !== 0 || win.scrollY !== 0;
    // Overlay scrollbars fade in and out after scrolling; hide them for the shot only.
    const hide = doc.createElement("style");
    hide.id = "harness-shot";
    hide.textContent = "* { scrollbar-width: none !important; }";
    (doc.head || doc.documentElement).appendChild(hide);
    // Firefox applies and paints scrolling asynchronously; scroll to the top until it stays there.
    let settled = 0;
    for (let k = 0; k < 20 && settled < 2; k++) {
      win.scrollTo({ left: 0, top: 0, behavior: "instant" });
      await frames(scrolled ? 2 : 1);
      settled = win.scrollX === 0 && win.scrollY === 0 ? settled + 1 : 0;
    }
    H.freeze();
    const roots = [doc, ...shadowRoots(doc)];
    let n = 0;
    for (const m of maskDefs) {
      if (!m.cover) continue;
      for (const el of matchSet(roots, m.cover)) {
        for (const r of el.getClientRects()) {
          const c = doc.createElement("harness-cover");
          c.setAttribute("style", "all: initial; position: absolute; z-index: 2147483647; background: #f0f; pointer-events: none;" +
            "left:" + (r.left + win.scrollX - 2) + "px; top:" + (r.top + win.scrollY - 2) + "px; width:" + (r.width + 4) + "px; height:" + (r.height + 4) + "px");
          doc.documentElement.appendChild(c);
          n++;
        }
      }
    }
    return { covers: n };
  };
  H.unmask = function () {
    if (doc) doc.querySelectorAll("harness-cover, style#harness-shot").forEach((c) => c.remove());
    return true;
  };

  // ---------------------------------------------------------------------------------------
  // Rig probe: which pseudo-elements getComputedStyle supports, and whether input arrives
  // ---------------------------------------------------------------------------------------
  H.probePseudos = function () {
    const out = {};
    const g = (id, ps, p) => {
      try { return win.getComputedStyle(doc.getElementById(id), ps).getPropertyValue(p); } catch (e) { return "ERR " + e.message; }
    };
    const dlg = doc.getElementById("dlg");
    out["::before"] = g("b", "::before", "color") === "rgb(13, 14, 15)" && g("b", "::before", "content") === '"b"';
    out["::after"] = g("b", "::after", "color") === "rgb(16, 17, 18)";
    out["::marker"] = g("li", "::marker", "color") === "rgb(1, 2, 3)" && g("sum", "::marker", "color") === "rgb(19, 20, 21)";
    out["::placeholder"] = g("ph", "::placeholder", "color") === "rgb(4, 5, 6)";
    out["::file-selector-button"] = g("fb", "::file-selector-button", "color") === "rgb(7, 8, 9)";
    const closed = g("dlg", "::backdrop", "background-color");
    dlg.showModal();
    const open = g("dlg", "::backdrop", "background-color");
    dlg.close();
    out["::backdrop"] = open === "rgb(10, 11, 12)";
    out.backdropClosed = closed;
    out.props = props().length;
    out.lightDark = g("cs", null, "color");
    return out;
  };
  // Host-page coordinates of an element's centre in the document (for pointer input).
  H.pointOf = function (id) {
    const el = doc.getElementById(id);
    const fr = frame.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    return { x: Math.round(fr.left + r.left + r.width / 2), y: Math.round(fr.top + r.top + r.height / 2) };
  };
  H.matches = function (id, sel) { return doc.getElementById(id).matches(sel); };
  H.focusId = function (id) {
    const a = doc.activeElement;
    if (a && a.blur) a.blur();
    if (id) doc.getElementById(id).focus();
    return doc.activeElement ? doc.activeElement.id : null;
  };
})();
