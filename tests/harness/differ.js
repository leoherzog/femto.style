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
  const HARNESS_TAGS = new Set(["harness-mq", "harness-cover", "harness-probe"]);
  const ALL_PSEUDOS = ["::before", "::after", "::marker", "::placeholder", "::file-selector-button", "::backdrop"];
  const KEEP_SPACE = /^(preserve|preserve-breaks|break-spaces|preserve-spaces|pre|pre-wrap|pre-line)$/;

  // breadth: the registry's per-document limits (registry.py limits()), applied again in every cell
  // on the live documents (H.diff: breadthGuard, coverage).
  // tokens: the styles mode collects and compares tokens (collectTokens); tokenPrefix, probeProps
  // and anchors (the site's wrappers, an extra anchor selector) come from harness/styles.py.
  let cfg = { entries: [], masks: [], maxRecords: 300, pseudos: ALL_PSEUDOS.slice(), blobUuid: true, minified: true,
              breadth: { doc: 0.25, union: 0.5, floor: 4, cover: 0.25, token: 0.5, tokenUnion: 0.6, closed: 0.7,
                         pinned: 0.4, shapes: 1 },
              tokens: false, tokenPrefix: "--femto-", probeProps: [], anchors: null };
  let compiled = [];
  let maskDefs = [];
  let frame = null, win = null, doc = null;
  const store = { a: null, b: null };
  const stateRef = new Map();  // side A's state snapshots of the cell, by target and state (H.afterState)
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
    stateRef.clear();
    baseKeys = new Set();
    cellDisabled = new Set();
    return { ok: !errors.length, errors, entries: compiled.length, masks: maskDefs.length,
             valueRules: H.VALUE_RULES.filter((_, i) => i === 0 || (i === 1 ? cfg.blobUuid : cfg.minified))
               .concat(H.COLLECTION_RULES) };
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
  // The oracle's stylesheets went through clean-css, which writes some values differently from the
  // source it was given. The owner chose on 2026-11-02 to compare those spellings as equal rather
  // than register them, so this rule is ON unless a run passes --exact-minified (tests/README.md,
  // Diff rule):
  // - a token's raw text compares without a 0 before a decimal point and without the whitespace
  //   after a comma (.25rem and 0.25rem, rgba(0,0,0,.25) and rgba(0, 0, 0, 0.25));
  // - outline-width compares only when outline-style is not none on both sides: clean-css writes
  //   outline: none as outline:0, so one side reads 0px and the other medium (3px), and neither
  //   side draws an outline;
  // - background-position and its -x and -y longhands compare 0px as 0%: clean-css writes
  //   background: none as background:0 0, whose position reads 0px 0px against 0% 0%.
  const LEAD_ZERO_RE = /(^|[^\w.])0+(?=\.\d)/g;
  const ZERO_PX_RE = /(^|[\s,])0px(?=$|[\s,])/g;
  const POSITION = new Set(["background-position", "background-position-x", "background-position-y"]);
  function minText(s) { return s.replace(/,\s+/g, ",").replace(LEAD_ZERO_RE, "$1"); }
  function sameRaw(a, b) {
    if (a === b) return true;
    if (!cfg.minified || a == null || b == null) return false;
    return minText(a) === minText(b);
  }
  function sameMinified(prop, a, b, outlineA, outlineB) {
    if (!cfg.minified || a == null || b == null) return false;
    if (prop === "outline-width") return outlineA === "none" && outlineB === "none";
    if (POSITION.has(prop)) return a.replace(ZERO_PX_RE, "$10%") === b.replace(ZERO_PX_RE, "$10%");
    return false;
  }
  H.VALUE_RULES = [
    "colors in computed styles: numeric, 1/255 per channel and 0.004 alpha, the rest of the value exact",
    "blob: URLs in attributes and computed styles (off with --exact-blob-urls): the UUID is a placeholder, the rest of the value exact",
    "the oracle minifier's spellings (off with --exact-minified): a token's raw text without a 0 before a decimal point or the whitespace after a comma; outline-width only when outline-style is not none on both sides; 0px as 0% in background-position and its longhands",
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
      token: strPat(e.token),
      // where.states (registry.py for_cell): the states a record may be found in; "base" is the
      // document as loaded. null: any.
      states: Array.isArray(e.states) ? e.states : null,
      a: valPat(e.a, e.kind === "token" ? "style" : e.kind),
      b: valPat(e.b, e.kind === "token" ? "style" : e.kind),
      // The allowances registry.py for_cell marks (breadthGuard, coverage): a pinned entry, a style
      // entry that names one route, a surface entry whose token pattern writes its names out.
      pinned: !!e.pinned, oneRoute: !!e.oneRoute, closed: !!e.closed,
    };
  }
  // The longhands whose computed value is what layout makes of the box: its used size, insets, the
  // origins resolved against it and the grid's resolved tracks. A style entry that names one route
  // and only these (on the cell's property list) is a layout consequence (consequences): its records
  // cover nothing (coverage).
  const GEOMETRY = new Set([
    "width", "height", "inline-size", "block-size", "top", "right", "bottom", "left", "inset-block-start",
    "inset-block-end", "inset-inline-start", "inset-inline-end", "transform-origin", "perspective-origin",
    "grid-template-rows", "grid-template-columns",
  ]);
  // The entries whose records cover nothing in this cell: pinned entries, which register one exact
  // value change and nothing else, and layout consequences, which register the sizes and positions a
  // registered change elsewhere moves on one page. The coverage rule counts what the registry
  // explains, not the layout it moves; every breadth limit still applies to them.
  function consequences(props) {
    const out = new Set();
    for (const e of compiled) {
      if (e.kind !== "style") continue;
      if (e.pinned) { out.add(e.id); continue; }
      if (!e.oneRoute) continue;
      const named = props.filter((p) => e.prop(p));
      if (named.length && named.every((p) => GEOMETRY.has(p))) out.add(e.id);
    }
    return out;
  }
  // The inherited longhands (CSS's "Inherited: yes", the vendor-prefixed ones Chrome and Firefox list
  // in getComputedStyle included). A record of one of these on an element whose parent pair has the
  // same registered record, value for value, is that record inherited: it is folded into it (inheritedFrom).
  const INHERITED = new Set([
    "border-collapse", "border-spacing", "caption-side", "caret-color", "clip-rule", "color",
    "color-interpolation", "color-interpolation-filters", "color-rendering", "color-scheme", "cursor",
    "direction", "dominant-baseline", "dynamic-range-limit", "empty-cells", "fill", "fill-opacity",
    "fill-rule", "font-family", "font-feature-settings", "font-kerning", "font-language-override",
    "font-optical-sizing", "font-palette", "font-size", "font-size-adjust", "font-stretch", "font-style",
    "font-synthesis", "font-synthesis-position", "font-synthesis-small-caps", "font-synthesis-style",
    "font-synthesis-weight", "font-variant", "font-variant-alternates", "font-variant-caps",
    "font-variant-east-asian", "font-variant-emoji", "font-variant-ligatures", "font-variant-numeric",
    "font-variant-position", "font-variation-settings", "font-weight", "forced-color-adjust",
    "hanging-punctuation", "hyphenate-character", "hyphenate-limit-chars", "hyphens", "image-orientation",
    "image-rendering", "interpolate-size", "letter-spacing", "line-break", "line-height", "list-style",
    "list-style-image", "list-style-position", "list-style-type", "marker", "marker-end", "marker-mid",
    "marker-start", "math-depth", "math-shift", "math-style", "orphans", "overflow-wrap", "paint-order",
    "pointer-events", "print-color-adjust", "quotes", "ruby-align", "ruby-position", "shape-rendering",
    "speak", "stroke", "stroke-dasharray", "stroke-dashoffset", "stroke-linecap", "stroke-linejoin",
    "stroke-miterlimit", "stroke-opacity", "stroke-width", "tab-size", "text-align", "text-align-last",
    "text-anchor", "text-autospace", "text-combine-upright", "text-decoration-skip-ink", "text-emphasis-color",
    "text-emphasis-position", "text-emphasis-style", "text-indent", "text-justify", "text-orientation",
    "text-rendering", "text-shadow", "text-size-adjust", "text-spacing-trim", "text-transform",
    "text-underline-offset", "text-underline-position", "text-wrap", "text-wrap-mode", "text-wrap-style",
    "visibility", "white-space", "white-space-collapse", "widows", "word-break", "word-spacing", "word-wrap",
    "writing-mode", "-moz-osx-font-smoothing", "-webkit-font-smoothing", "-webkit-hyphenate-character",
    "-webkit-locale", "-webkit-rtl-ordering", "-webkit-tap-highlight-color", "-webkit-text-combine",
    "-webkit-text-emphasis-color", "-webkit-text-emphasis-position", "-webkit-text-emphasis-style",
    "-webkit-text-fill-color", "-webkit-text-orientation", "-webkit-text-security", "-webkit-text-stroke-color",
    "-webkit-text-stroke-width", "-webkit-user-modify", "-webkit-writing-mode", "-moz-text-size-adjust",
    "-webkit-text-size-adjust", "-webkit-border-horizontal-spacing", "-webkit-border-vertical-spacing",
    "-webkit-line-break", "-webkit-print-color-adjust",
  ]);
  // The pseudo-elements that inherit from their element (::backdrop does not in every browser).
  const INHERITING_PSEUDOS = new Set(["::before", "::after", "::marker", "::placeholder", "::file-selector-button"]);
  let disabled = new Set();  // entries the in-page breadth guard took out of this cell (H.diff)
  let exempt = new Set();  // the ids of the entries whose records cover nothing in this cell (consequences)
  let cellDisabled = new Set();  // the same set, kept for the cell's state diffs (H.afterState)
  // The two snapshots a record's nodes belong to: the documents (store) or, under a state, the
  // two subtree snapshots (H.afterState), whose selSets are their own.
  let pair = { a: null, b: null };
  // The state the records being added were found in (H.afterState); null for the document as loaded.
  let curState = null;
  function matchRecord(rec, na, nb) {
    const hits = [];
    for (const e of compiled) {
      if (e.kind !== rec.kind || disabled.has(e.k)) continue;
      if (e.states && !e.states.includes(rec.state || "base")) continue;
      if (!e.path(rec.path)) continue;
      if (rec.kind === "style" && !e.pseudo(rec.pseudo)) continue;
      if ((rec.kind === "style" || rec.kind === "attribute" || rec.kind === "head" || rec.kind === "token") && !e.prop(rec.prop)) continue;
      if (TOKEN_KINDS.has(rec.kind) && !e.token(rec.token)) continue;
      if (!e.a(rec.a) || !e.b(rec.b)) continue;
      if (e.sel) {
        // The selector is matched against the element on side B, or on side A when B has none (a
        // token record's element is its anchor; surface records have none, so a selector never
        // matches them).
        const ok = nb ? pair.b.selSets[e.k].has(nb.i) : (na ? pair.a.selSets[e.k].has(na.i) : false);
        if (!ok) continue;
      }
      hits.push(e.id);
    }
    return hits;
  }
  function newResult() {
    return { total: 0, unregisteredTotal: 0, unregistered: [], registered: {}, samples: {}, counts: {},
             inheritedTotal: 0, inherited: {} };
  }
  // Inherited records. inh holds, per element pair of the diff running (H.diff, diffState), the
  // inherited longhands whose record was registered there or folded into one, with its values and
  // the entries that registered it. A record no entry matches, of an inherited longhand, on a child
  // pair whose parent pair holds the same longhand with the same value on each side (or on an
  // inheriting pseudo-element of a pair that holds it) is that difference inherited: it is folded
  // into the parent's record. It counts under those entries in res.inherited, apart from
  // res.registered, and covers nothing (coverage), so one registered difference on an element is not
  // repeated by every descendant that inherits it. The harness cannot see whether the child has a rule
  // of its own for the longhand; a rule that gives it the parent's values on both sides is the same
  // difference, and any other value is a record of its own (tests/README.md, Divergence registry).
  let inh = null;
  function inheritedFrom(rec, na, nb) {
    if (!inh || rec.kind !== "style" || !na || !nb || !INHERITED.has(rec.prop)) return null;
    let at;
    if (rec.pseudo) {
      if (!INHERITING_PSEUDOS.has(rec.pseudo)) return null;
      at = na.i + "|" + nb.i;
    } else {
      if (na.parent === null || nb.parent === null) return null;
      at = na.parent + "|" + nb.parent;
    }
    const got = inh.has(at) ? inh.get(at).get(rec.prop) : null;
    return got && got.a === rec.a && got.b === rec.b ? got.hits : null;
  }
  function keepInherited(rec, na, nb, hits) {
    if (!inh || rec.kind !== "style" || rec.pseudo || !na || !nb || !INHERITED.has(rec.prop)) return;
    const at = na.i + "|" + nb.i;
    if (!inh.has(at)) inh.set(at, new Map());
    inh.get(at).set(rec.prop, { a: rec.a, b: rec.b, hits });
  }
  // A record's identity for the state coverage rule: element, pseudo-element, property and values.
  function recKey(rec) {
    return JSON.stringify([rec.kind, rec.path, rec.pseudo || "", rec.prop || "", rec.change || "", rec.a, rec.b]);
  }
  // The records of the cell's document diff (H.diff), by recKey: under a state, a record equal to one
  // of them is no difference the state adds, so it covers nothing in the state's subtree (coverage).
  let baseKeys = new Set();
  function addRecord(res, rec, na, nb) {
    if (curState) rec.state = curState;
    else baseKeys.add(recKey(rec));
    res.total++;
    res.counts[rec.kind] = (res.counts[rec.kind] || 0) + 1;
    const hits = matchRecord(rec, na, nb);
    if (!hits.length) {
      const from = inheritedFrom(rec, na, nb);
      if (from) {
        res.inheritedTotal++;
        for (const id of from) res.inherited[id] = (res.inherited[id] || 0) + 1;
        keepInherited(rec, na, nb, from);
        return;
      }
      res.unregisteredTotal++;
      if (res.unregistered.length < cfg.maxRecords) res.unregistered.push(rec);
      return;
    }
    for (const id of hits) {
      res.registered[id] = (res.registered[id] || 0) + 1;
      const s = (res.samples[id] = res.samples[id] || []);
      if (s.length < 2) s.push(rec);
    }
    keepInherited(rec, na, nb, hits);
    const covering = hits.filter((id) => !exempt.has(id));
    if (covering.length && !TOKEN_KINDS.has(rec.kind) && !(curState && baseKeys.has(recKey(rec)))) cover(rec, na, nb, covering);
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
    stEls = [];
    stOpened = [];
    armed = null;
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
  // An animation of an element (not a pseudo-element) whose every animated longhand a mask leaves
  // uncompared on it changes nothing the diff reads, so a late one does not make the cell
  // untrustworthy. Such animations are frozen like the others and counted apart, as masked.
  // masks.json's oracle-theme-toggle: the oracle's toggle icon can start its transform transition
  // after the first freeze in Safari (p0-self-safari-light-locked, 2026-11-01); its
  // oracle-maintenance-notice covers the banner link's color transitions the same way.
  function animatedProps(a) {
    if (typeof a.transitionProperty === "string") return [a.transitionProperty];
    const out = new Set();
    try {
      for (const k of a.effect.getKeyframes())
        for (const p of Object.keys(k))
          if (!["offset", "computedOffset", "easing", "composite"].includes(p)) out.add(p.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()));
    } catch (e) { /* no keyframes to read */ }
    return [...out];
  }
  function maskedAnimation(a) {
    const el = a.effect && a.effect.target;
    if (!el || !el.matches || a.effect.pseudoElement) return false;
    const props = animatedProps(a);
    return props.length > 0 && maskDefs.some((m) => m.properties.size && props.every((p) => m.properties.has(p)) && el.matches(m.sel));
  }
  H.freeze = function () {
    let finished = 0, paused = 0, masked = 0;
    if (!doc) return { finished, paused, masked };
    for (let round = 0; round < 3; round++) {
      let changed = 0;
      for (const a of allAnimations()) {
        const t = a.effect ? a.effect.getComputedTiming() : null;
        const m = maskedAnimation(a);
        if (t && t.endTime === Infinity) {
          if (a.playState !== "paused" || a.currentTime !== 0) { a.pause(); a.currentTime = 0; m ? masked++ : paused++; changed++; }
        } else if (a.playState !== "finished") {
          try { a.finish(); m ? masked++ : finished++; changed++; } catch (e) { a.cancel(); }
        }
      }
      if (!changed) break;
    }
    return { finished, paused, masked };
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

  // The compared elements under root, in tree order (an element, its open shadow root's children,
  // then its light children), with the masks applied; each node keeps its element (n.el) until the
  // caller has read it.
  function buildNodes(root, roots) {
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
    return { nodes, maskCounts };
  }

  // Chrome does not update the style of a skipped subtree (the content of a closed <details> is
  // content-visibility: hidden) until something reads it, and a transition that such a read starts
  // stays at its start value there and was not in getAnimations() when the freeze above ran. Seen
  // on 2026-10-30 (p0-gate-self-cf-2, Chrome, /docs/overflow-auto dark 800, side A): the links in
  // the closed header dropdown and side-nav details read their UA colors and the dropdown list
  // opacity 1. So read every element's style (and ::before, ::after) once, then freeze again.
  function touchStyles(nodes) {
    for (const n of nodes) {
      win.getComputedStyle(n.el).getPropertyValue("color");
      win.getComputedStyle(n.el, "::before").getPropertyValue("color");
      win.getComputedStyle(n.el, "::after").getPropertyValue("color");
    }
  }

  // Each node's computed styles, pseudo-elements, attributes, own text and label. Returns the
  // number of pseudo-elements read.
  function readNodes(nodes, P, rootLabel) {
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
      if (n.parent === null) n.rootLabel = rootLabel;
    }
    return pseudo;
  }

  // For each compiled entry with a selector (of the kinds in only, when given), the nodes
  // (indexes) whose element matches it: from entrySets (the document's matches) or el.matches().
  function selSetsOf(nodes, entrySets, only) {
    return compiled.map((e, k) => {
      if (!e.sel || (only && !only.has(e.kind))) return null;
      const out = new Set();
      const set = entrySets ? entrySets[k] : null;
      for (const n of nodes) {
        let ok = false;
        if (set) ok = set.has(n.el);
        else { try { ok = n.el.matches(e.sel); } catch (err) { ok = false; } }
        if (ok) out.add(n.i);
      }
      return out;
    });
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
    // Selector sets, evaluated once per side: registry entries (masks: buildNodes).
    const entrySets = compiled.map((e) => e.sel ? matchSet(roots, e.sel) : null);
    const { nodes, maskCounts } = buildNodes(root, roots);
    touchStyles(nodes);
    const fr1 = H.freeze();
    const settleMs = settleFileButtons(nodes);
    const P = props();
    const pseudo = readNodes(nodes, P, rootSel || "html");
    const selSets = selSetsOf(nodes, entrySets);
    // The styles mode's tokens (collectTokens) need the anchors' elements, so they are read before
    // the nodes let go of them.
    const t1 = performance.now();
    const tokens = cfg.tokens ? collectTokens(nodes) : null;
    const msTokens = performance.now() - t1;
    for (const n of nodes) n.el = null;  // keep no references into a document that will be removed
    const head = rootSel ? null : collectHead();
    // With --root-a/--root-b the records still carry the document's own tree paths (the root's path
    // from html, then down), so a registry path pattern means the same in a section comparison as
    // in a whole-page one and is judged on the same reference documents.
    const rootPath = rootSel ? treePath(root) : null;
    store[side] = { nodes, props: P, selSets, maskCounts, rootSel: rootSel || null, rootPath, head, tokens };
    store[side].reach = entryReach(store[side]);
    const fr = H.freeze();
    return {
      elements: nodes.length, pseudo, props: P.length, maskCounts, settleMs, freezeBefore: fr0, freezeTouched: fr1, freezeAfter: fr,
      head: head ? head.size : null, headRepeats: head ? head.repeats : null, requests: resources(),
      tokens: tokens ? { names: tokens.names.length, anchors: tokens.anchors.length, groups: tokens.groups, ms: msTokens } : null,
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
      if (TOKEN_KINDS.has(e.kind)) {
        // Token entries reach token names (breadthGuard judges them against the cell's names).
        if (snap.tokens) for (const n of snap.tokens.names) if (e.token(n)) out.push(n);
        return out;
      }
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
  // Tokens (the styles mode; femto's tests/harness/differ.js at 7bcd5758, collectTokens): names
  // from the CSSOM, resolution through real properties under each anchor, raw text at each anchor
  // ---------------------------------------------------------------------------------------
  // Every custom property with the token prefix that either side's stylesheets declare: a walk of
  // document.styleSheets, @import-ed sheets, nested and conditional rules, @property rules, and
  // every open shadow root's sheets and adopted sheets.
  function tokenNames() {
    const names = new Set(), seen = new Set();
    const prefix = cfg.tokenPrefix;
    const walkRules = (rules) => {
      for (const r of rules) {
        if (r.styleSheet) walkSheet(r.styleSheet);
        if (r.style) for (let i = 0; i < r.style.length; i++) { const n = r.style[i]; if (n.startsWith(prefix)) names.add(n); }
        if (typeof r.name === "string" && r.name.startsWith(prefix) && r.constructor && /Property/.test(r.constructor.name)) names.add(r.name);
        if (r.cssRules) walkRules(r.cssRules);
      }
    };
    const walkSheet = (s) => {
      if (!s || seen.has(s)) return;
      seen.add(s);
      let rules;
      try { rules = s.cssRules; } catch (e) { harnessErrors.push("tokens: cannot read cssRules of " + s.href + ": " + e.message); return; }
      walkRules(rules);
    };
    for (const s of doc.styleSheets) walkSheet(s);
    for (const r of shadowRoots(doc)) {
      for (const s of r.styleSheets) walkSheet(s);
      for (const s of r.adoptedStyleSheets || []) walkSheet(s);
    }
    return [...names].sort();
  }
  // The anchors: html, body, every [data-theme] element, every article and dialog, the site's
  // own wrappers (cfg.anchors, femto's [data-module] in this site: tests/README.md, Tokens), and
  // each shadow host's shadow root. A shadow host's own probes go in its shadow root: a light-DOM
  // child of a host is unslotted, and getComputedStyle() returns empty values for it (femto).
  const ANCHOR_SEL = "[data-theme], article, dialog";
  function tokenAnchors(nodes) {
    const list = [], seen = new Set();
    const snap = { nodes, rootPath: null };
    let extra = null;
    try { extra = cfg.anchors ? new Set(matchSet([doc, ...shadowRoots(doc)], cfg.anchors)) : null; }
    catch (e) { harnessErrors.push("tokens: anchor selector " + cfg.anchors + ": " + e.message); }
    const add = (n, root, tag) => {
      const key = pathOf(snap, n) + (tag || "");
      if (seen.has(key)) return;
      seen.add(key);
      list.push({ n, root, key, label: n.label + (tag || "") });
    };
    for (const n of nodes) {
      const el = n.el;
      if (el === doc.documentElement || el === doc.body || el.matches(ANCHOR_SEL) || (extra && extra.has(el))) add(n, el.shadowRoot || el);
      if (el.shadowRoot) add(n, el.shadowRoot, " >>> shadow root");
    }
    return list;
  }
  function collectTokens(nodes) {
    const names = tokenNames();
    const A = tokenAnchors(nodes);
    const P = cfg.probeProps;
    const raw = [], sig = [], groupOf = new Map();
    A.forEach((a, k) => {
      const cs = win.getComputedStyle(a.n.el);
      const r = names.map((n) => cs.getPropertyValue(n).trim());
      raw[k] = r;
      // Resolution depends only on the anchor's token values and its color-scheme, so anchors with
      // the same signature share one probe set.
      sig[k] = cs.getPropertyValue("color-scheme") + "\u0002" + r.join("\u0001");
      if (!groupOf.has(sig[k])) groupOf.set(sig[k], k);
    });
    const resolved = new Map();
    const tmpl = P.map((p) => p + ": var(\u0003)").join("; ");
    for (const [s, k] of groupOf) {
      const box = doc.createElement("harness-probe");
      box.setAttribute("style", "all: initial; color-scheme: inherit; display: none");
      const probes = names.map((n) => {
        const p = doc.createElement("harness-probe");
        p.setAttribute("style", tmpl.split("\u0003").join(n));
        box.appendChild(p);
        return p;
      });
      A[k].root.appendChild(box);
      resolved.set(s, probes.map((p) => read(win.getComputedStyle(p), P)));
      box.remove();
    }
    return { names, anchors: A.map((a) => ({ i: a.n.i, key: a.key, label: a.label })), raw, sig, resolved, groups: groupOf.size };
  }
  const TOKEN_KINDS = new Set(["token", "token-raw", "surface-missing", "surface-added"]);
  function diffTokens(res, A, B) {
    const r = A.tokens, t = B.tokens;
    const rs = new Set(r.names), ts = new Set(t.names);
    for (const n of r.names) if (!ts.has(n)) addRecord(res, { kind: "surface-missing", token: n, label: n, a: "declared", b: null }, null, null);
    for (const n of t.names) if (!rs.has(n)) addRecord(res, { kind: "surface-added", token: n, label: n, a: null, b: "declared" }, null, null);
    const common = r.names.filter((n) => ts.has(n));
    const ri = new Map(r.names.map((n, i) => [n, i])), ti = new Map(t.names.map((n, i) => [n, i]));
    const tAnch = new Map(t.anchors.map((a, k) => [a.key, k]));
    const P = cfg.probeProps;
    r.anchors.forEach((a, k) => {
      const tk = tAnch.get(a.key);
      if (tk === undefined) { harnessErrors.push("tokens: anchor missing on side B: " + a.label + " at " + a.key); return; }
      const na = A.nodes[a.i], nb = B.nodes[t.anchors[tk].i];
      const rr = r.resolved.get(r.sig[k]), tr = t.resolved.get(t.sig[tk]);
      for (const n of common) {
        const x = ri.get(n), y = ti.get(n);
        const rawA = r.raw[k][x], rawB = t.raw[tk][y];
        const base = { path: a.key, label: t.anchors[tk].label, token: n };
        if (!sameRaw(rawA, rawB)) addRecord(res, Object.assign({ kind: "token-raw", a: rawA, b: rawB }, base), na, nb);
        const va = rr[x], vb = tr[y];
        for (let j = 0; j < P.length; j++) {
          if (va[j] !== vb[j] && !same(va[j], vb[j]) && !sameValue(va[j], vb[j])) addRecord(res, Object.assign({ kind: "token", prop: P[j], a: va[j], b: vb[j] }, base), na, nb);
        }
      }
    });
    const bAnch = new Set(r.anchors.map((a) => a.key));
    for (const a of t.anchors) if (!bAnch.has(a.key)) harnessErrors.push("tokens: anchor missing on side A: " + a.label + " at " + a.key);
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
    const oi = P.indexOf("outline-style");
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
        if (a[j] !== b[j] && !same(a[j], b[j]) && !sameValue(a[j], b[j]) && !sameMinified(P[j], a[j], b[j], a[oi], b[oi]))
          addRecord(res, Object.assign({}, base, { prop: P[j], a: a[j], b: b[j] }), na, nb);
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
  // an entry applies, not how much of a page it may cover. A pinned entry (registry.py _pinned) may
  // reach up to lim.pinned, on the repeats of one example (at most lim.shapes tree paths, sibling
  // indices dropped).
  function breadthGuard(A, B, errors) {
    const lim = cfg.breadth || {};
    const off = new Set();
    const sides = [["A", A], ["B", B]];
    const total = (S, kind) => (kind === "head" ? (S.head ? S.head.size : 0) : TOKEN_KINDS.has(kind) ?
      (S.tokens ? S.tokens.names.length : 0) : S.nodes.length);
    const unit = (kind) => (kind === "head" ? "head keys" : TOKEN_KINDS.has(kind) ? "token names" : "compared elements");
    const surface = (kind) => kind === "surface-missing" || kind === "surface-added";
    const shapes = (S, reach) => new Set(reach.map((i) => pathOf(S, S.nodes[i]).replace(/:\d+/g, ""))).size;
    for (const e of compiled) {
      // A token entry may name at most lim.token of either side's token names: its value patterns
      // narrow it, and femto's light-dark() raw text spans about two in five of them. A surface entry
      // whose pattern writes its names out (closed) may name up to lim.closed.
      const share = TOKEN_KINDS.has(e.kind) ? (surface(e.kind) && e.closed ? lim.closed : lim.token) : lim.doc;
      for (const [name, S] of sides) {
        const n = S.reach[e.k].length, t = total(S, e.kind);
        if (!t || n <= lim.floor || n / t <= share) continue;
        let why = "more than " + pct(share) + " of one document";
        if (e.pinned) {
          const sh = shapes(S, S.reach[e.k]);
          if (n / t <= lim.pinned && sh <= lim.shapes) continue;
          why = n / t > lim.pinned ? "more than the " + pct(lim.pinned) + " a pinned entry may reach" :
            "more than " + pct(share) + " of one document, in " + sh + " shapes of tree path (a pinned entry passes " +
            pct(share) + " only on the repeats of one example)";
        }
        errors.push("breadth: registry entry " + e.id + " matches " + n + " of the " + t + " " + unit(e.kind) + " (" +
                    pct(n / t) + ") of side " + name + "'s document in this cell, " + why + ", so it is not applied here" +
                    BREADTH_REF);
        off.add(e.k);
        break;
      }
    }
    // Together: the entries of a kind applied in this cell. The token entries of a cell, and the
    // token-raw entries, name at most lim.tokenUnion of either side's token names (registry.py
    // TOKEN_UNION_MAX), so a catch-all split by name is caught. The surface entries of a kind do too,
    // counting those whose pattern is open, and all of them, closed sets included, name at most
    // lim.closed: a surface record is one name declared on one side only, and femto's color bundle
    // adds two thirds of the color picker routes' names (one closed-set entry).
    const unionCheck = (kind, members, share, what) => {
      if (members.length < 2) return;
      for (const [name, S] of sides) {
        const u = new Set();
        for (const e of members) for (const x of S.reach[e.k]) u.add(x);
        const t = total(S, kind);
        if (t && u.size > lim.floor && u.size / t > share) {
          errors.push("breadth: the " + members.length + " " + kind + " entries" + what + " applied in this cell (" +
                      members.map((e) => e.id).join(", ") + ") together match " + u.size + " of the " + t + " " +
                      unit(kind) + " (" + pct(u.size / t) + ") of side " + name + "'s document, more than " +
                      pct(share) + ", so none of them is applied here" + BREADTH_REF);
          for (const e of members) off.add(e.k);
          return;
        }
      }
    };
    for (const kind of new Set(compiled.map((e) => e.kind))) {
      const members = () => compiled.filter((e) => e.kind === kind && !off.has(e.k));
      if (surface(kind)) {
        unionCheck(kind, members().filter((e) => !e.closed), lim.tokenUnion, " with an open token pattern");
        unionCheck(kind, members(), lim.closed, "");
      } else {
        unionCheck(kind, members(), TOKEN_KINDS.has(kind) ? lim.tokenUnion : lim.union, "");
      }
    }
    return off;
  }

  // The registered records of a cell may cover at most lim.cover of either document (elements, a
  // structure record counting its whole subtree; head keys apart), past lim.floor: a registry stands
  // in for a few explained differences, never for most of a page (a page one side does not have).
  // Records only pinned entries and layout consequences register cover nothing (consequences).
  function coverage(A, B, errors, what) {
    const lim = cfg.breadth || {};
    const by = Object.entries(covered.by).sort((x, y) => y[1] - x[1]).slice(0, 4).map(([id, n]) => id + " " + n).join(", ");
    const check = (name, n, t, unit) => {
      if (t && n > lim.floor && n / t > lim.cover)
        errors.push("coverage: the registered differences of this cell cover " + n + " of the " + t + " " + unit + " (" +
                    pct(n / t) + ") of side " + name + "'s " + (what || "document") + ", more than " + pct(lim.cover) + ": registry entries " +
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
    cellDisabled = new Set(disabled);
    exempt = consequences(B.props);
    pair = { a: A, b: B };
    curState = null;
    covered = { a: new Uint8Array(A.nodes.length), b: new Uint8Array(B.nodes.length), headA: new Set(), headB: new Set(), by: {} };
    baseKeys = new Set();
    inh = new Map();
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
      if (A.tokens && B.tokens) diffTokens(res, A, B);
      else if (A.tokens || B.tokens) errors.push("tokens: collected on one side only");
      coverage(A, B, errors);
    } finally {
      covered = null;
      inh = null;
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
  // Interactive states (the styles mode): femto's replay at 7bcd5758 (H.stateTargets, pointAt,
  // prepTab, afterState), with targets from harness/states.json instead of data-states attributes,
  // and the subtree under each target's scope collected and diffed like a document.
  // ---------------------------------------------------------------------------------------
  const STATE_PSEUDO = { hover: ":hover", active: ":active", focus: ":focus", "focus-visible": ":focus-visible" };
  const STATE_KINDS = new Set(["structure", "attribute", "text", "style"]);
  let stEls = [];      // the elements the current target resolved to (H.prepTarget)
  let stOpened = [];   // the details the current target opened, closed again by H.unprepTarget
  let armed = null;    // the document whose activation is cancelled (H.armStates)

  function composedParent(el) {
    if (el.parentElement) return el.parentElement;
    const r = el.parentNode;
    return r && r.host ? r.host : null;
  }
  function composedContains(a, b) {
    for (let x = b; x; x = composedParent(x)) if (x === a) return true;
    return false;
  }
  function deepActive() {
    let a = doc.activeElement;
    while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement;
    return a;
  }
  // Every element in composed tree order (an element, its open shadow tree, its light children),
  // skipped and harness tags left out: the order Tab follows in the documents compared here.
  function walkAll() {
    const out = [doc.documentElement];
    const visit = (node) => {
      for (let c = node.firstElementChild; c; c = c.nextElementSibling) {
        const t = c.localName;
        if (SKIP_TAGS.has(t) || HARNESS_TAGS.has(t)) continue;
        out.push(c);
        if (c.shadowRoot) visit(c.shadowRoot);
        visit(c);
      }
    };
    visit(doc.documentElement);
    return out;
  }

  // Activation is cancelled in the document while states are replayed: capture-phase listeners on
  // its window stop every click, auxclick and submit before the page's own listeners see it and
  // cancel its default action (no navigation, toggle, submit, theme switch or copy), and cancel every
  // mousedown on a select (otherwise the native picker opens, stays open in Firefox and swallows
  // later input). femto cancelled the defaults only; this site's scripts act on clicks too.
  //
  // Scrolling is instant while states are replayed: a transient harness style sets html's
  // scroll-behavior to auto (H.disarmStates removes it). The browser's own scrolls of a real Tab, a
  // focus() and a pointer move follow the page's scroll-behavior, and side A's legacy CSS has html {
  // scroll-behavior: smooth } where side B has none (a registered difference): a state collected
  // while one side still scrolls catches the page's scroll-driven script (the table of contents' spy)
  // at another position. html's scroll-behavior is compared in the document's collect, before this,
  // and html lies outside every state's scope.
  H.armStates = function () {
    if (!doc) return false;
    restAt = null;
    if (!doc.getElementById("harness-scroll")) {
      const st = doc.createElement("style");
      st.id = "harness-scroll";
      st.textContent = "html { scroll-behavior: auto !important; }";
      (doc.head || doc.documentElement).appendChild(st);
    }
    if (armed === doc) return true;
    const stop = (e) => { e.preventDefault(); e.stopImmediatePropagation(); };
    for (const t of ["click", "auxclick", "submit"]) win.addEventListener(t, stop, true);
    win.addEventListener("mousedown", (e) => {
      if (e.target && e.target.closest && e.target.closest("select")) e.preventDefault();
    }, true);
    armed = doc;
    return true;
  };

  // Returns html's scroll-behavior once the harness style is gone (the page's own again), and
  // whether a harness style is left (styles.py reports one as a harness error).
  H.disarmStates = function () {
    restAt = null;
    if (!doc) return { left: false, behavior: null };
    const st = doc.getElementById("harness-scroll");
    if (st) st.remove();
    return { left: !!doc.getElementById("harness-scroll"),
             behavior: win.getComputedStyle(doc.documentElement).scrollBehavior };
  };
  // Wait until the document's scroll position holds for two frames (at most 1 s): the page's scroll
  // listeners (the table of contents' spy, the sticky breadcrumb) run in the frame that dispatches
  // the scroll event, so each side's state is collected at rest, after them. Scrolling is instant
  // here (armStates), so a position that has not moved since the last rest means no scroll is
  // pending, and nothing is waited for.
  let restAt = null;
  async function scrollRest() {
    let last = win.scrollX + "," + win.scrollY, still = 0;
    if (last === restAt) return;
    const t0 = performance.now();
    while (still < 2 && performance.now() - t0 < 1000) {
      await frames(1);
      const now = win.scrollX + "," + win.scrollY;
      still = now === last ? still + 1 : 0;
      last = now;
    }
    restAt = last;
  }

  // Resolve one states.json target in this document: open the details it names (spec.open), then
  // take the first spec.max elements matching spec.selector that render (a client rect) and are
  // not inside a contents mask. On side B, want holds the tree paths side A took, and exactly those
  // elements are taken, in that order; one that does not render here is left out, and Python
  // reports it. Returns their labels and tree paths.
  H.prepTarget = function (spec, want) {
    stEls = [];
    stOpened = [];
    const errors = [];
    const roots = [doc, ...shadowRoots(doc)];
    if (spec.open) {
      try {
        for (const d of matchSet(roots, spec.open)) if (d.localName === "details" && !d.open) { d.open = true; stOpened.push(d); }
      } catch (e) { errors.push("open " + spec.open + ": " + e.message); }
    }
    let found = [];
    try { found = [...matchSet(roots, spec.selector)]; } catch (e) { errors.push("selector " + spec.selector + ": " + e.message); }
    const hidden = maskDefs.filter((m) => m.contents);
    const usable = (el) => el.getClientRects().length && win.getComputedStyle(el).visibility === "visible" &&
      !hidden.some((m) => { try { return !!el.closest(m.sel); } catch (e) { return false; } });
    if (Array.isArray(want)) {
      const byPath = new Map(found.map((el) => [treePath(el), el]));
      for (const p of want) { const el = byPath.get(p); if (el && usable(el)) stEls.push(el); }
    } else {
      for (const el of found) {
        if (stEls.length >= (spec.max || 2)) break;
        if (usable(el)) stEls.push(el);
      }
    }
    return { errors, matched: found.length, targets: stEls.map((el, k) => ({ k, label: label(el), path: treePath(el),
             tag: el.localName, type: (el.getAttribute("type") || "").toLowerCase() })) };
  };
  H.unprepTarget = function () {
    for (const d of stOpened) d.open = false;
    stOpened = [];
    stEls = [];
    return H.freeze();
  };

  // Two animation frames let async scrolling (Firefox APZ) settle before input is hit-tested; a
  // 150 ms timer caps the wait, and a hidden page (Safari on a locked screen) never runs rAF.
  function settleFrames(n) {
    if (document.visibilityState === "hidden") return Promise.resolve();
    return new Promise((resolve) => {
      let k = 0;
      const step = () => (++k >= n ? resolve() : win.requestAnimationFrame(step));
      win.requestAnimationFrame(step);
      setTimeout(resolve, 150);
    });
  }
  // Scroll the target into view inside the iframe and return the host-page point at the centre of
  // its largest line box that hit-tests to it (femto's pointAt).
  H.pointAt = async function (k) {
    const el = stEls[k];
    const before = win.scrollX + "," + win.scrollY;
    el.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
    window.scrollTo(0, 0);
    const scrolled = before !== win.scrollX + "," + win.scrollY;
    if (scrolled) await settleFrames(2);
    const fr = frame.getBoundingClientRect();
    const root = el.getRootNode();
    const finder = root.elementFromPoint ? root : doc;
    const rects = [...el.getClientRects()].filter((r) => r.width >= 1 && r.height >= 1)
      .sort((a, b) => b.width * b.height - a.width * a.height);
    if (!rects.length) rects.push(el.getBoundingClientRect());
    let best = null;
    for (const r of rects) {
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const hit = finder.elementFromPoint(cx, cy);
      const ok = !!hit && (hit === el || composedContains(el, hit));
      // A point outside the iframe viewport cannot be reached by the pointer; report it instead.
      const inside = cx >= 0 && cy >= 0 && cx < frame.clientWidth && cy < frame.clientHeight;
      const cand = { x: Math.round(fr.left + cx), y: Math.round(fr.top + cy), size: [r.width, r.height], scrolled,
                     hit: ok && inside, outside: !inside, hitLabel: !inside ? "outside the viewport" : (hit ? label(hit) : null) };
      if (!inside) { if (!best) best = cand; continue; }
      if (!best) best = cand;
      if (ok) { best = cand; break; }
    }
    return best;
  };
  H.focusEl = function (k) {
    const el = stEls[k];
    el.focus();
    return { focused: deepActive() === el };
  };
  function focusables() {
    return walkAll().filter((el) => {
      if (el.tabIndex < 0 || el.disabled || el.inert || el.closest("[inert]")) return false;
      if (el.localName === "input" && el.type === "hidden") return false;
      if (!el.getClientRects().length) return false;
      const cs = win.getComputedStyle(el);
      return cs.visibility === "visible" && cs.display !== "none";
    });
  }
  // Focus the focusable before (dir 1) or after (dir -1) the target, so a Tab (or Shift+Tab) lands on it.
  H.prepTab = function (k, dir) {
    const el = stEls[k];
    const list = focusables();
    const i = list.indexOf(el);
    const other = i < 0 ? null : list[i - (dir || 1)];
    const a = deepActive();
    if (a && a.blur) a.blur();
    if (other) {
      other.focus();
      return { from: label(other), ok: deepActive() === other, inList: i >= 0 };
    }
    win.focus();
    return { from: null, ok: true, inList: i >= 0 };
  };
  // Focus the target itself, for a Shift+Tab and a Tab that come back to it in the browser's own
  // tab order (which also stops at keyboard-focusable scrollers, such as a pre that overflows at
  // 375 px, which focusables() cannot list).
  H.prepBack = function (k) {
    const el = stEls[k];
    const a = deepActive();
    if (a && a.blur) a.blur();
    el.focus();
    return { ok: deepActive() === el };
  };
  H.resetState = function () {
    const a = deepActive();
    if (a && a !== doc.body && a.blur) a.blur();
    return H.freeze();
  };

  // The registered and unregistered records between two snapshots of the same subtree under the
  // same state, each record carrying the state; the cell's breadth guard stays in force, and the
  // coverage rule applies to the subtree, counting only what the state adds: a registered record
  // equal to one of the document diff's (the same element, pseudo-element, property and values) was
  // judged there and covers nothing here (addRecord).
  function diffState(A, B) {
    const t0 = performance.now();
    const res = newResult();
    const errors = [];
    disabled = cellDisabled;
    pair = { a: A, b: B };
    curState = B.state;
    covered = { a: new Uint8Array(A.nodes.length), b: new Uint8Array(B.nodes.length), headA: new Set(), headB: new Set(), by: {} };
    inh = new Map();
    try {
      const ra = A.nodes[0], rb = B.nodes[0];
      if (ra.tag !== rb.tag) {
        structure(res, A, B, ra, rb);
        diffText(res, ra, rb, pathOf(B, rb));
        diffChildren(res, A, B, ra, rb, B.props);
      } else {
        diffPair(res, A, B, ra, rb, B.props);
      }
      coverage(A, B, errors, "subtree under " + B.state);
    } finally {
      covered = null;
      inh = null;
      disabled = new Set();
      curState = null;
      pair = { a: store.a, b: store.b };
    }
    res.ms = performance.now() - t0;
    res.errors = errors.concat(harnessErrors.splice(0));
    res.elements = { a: A.nodes.length, b: B.nodes.length };
    return res;
  }

  // The state is applied (Python's input): check it matches, finish transitions, collect the
  // subtree under the target's scope (its closest ancestor matching scopeSel, else its parent), and
  // keep it (side A) or diff it against side A's snapshot of the same target and state (side B).
  H.afterState = async function (side, k, state, key, scopeSel) {
    const el = stEls[k];
    const sel = STATE_PSEUDO[state];
    await scrollRest();
    const matched = !!sel && el.matches(sel);
    const info = { matched, active: deepActive() ? label(deepActive()) : null };
    if (!matched) return info;
    H.freeze();
    let scope = null;
    try { scope = scopeSel ? el.closest(scopeSel) : null; } catch (e) { info.error = "scope " + scopeSel + ": " + e.message; return info; }
    if (!scope) scope = el.parentElement || el;
    const { nodes } = buildNodes(scope, [doc, ...shadowRoots(doc)]);
    touchStyles(nodes);
    H.freeze();
    info.settleMs = settleFileButtons(nodes);
    if (!el.matches(sel)) { info.matched = false; info.error = "state was lost while transitions settled"; return info; }
    const P = props();
    readNodes(nodes, P, "scope");
    const snap = { nodes, props: P, rootPath: treePath(scope), state, target: treePath(el),
                   selSets: selSetsOf(nodes, null, STATE_KINDS) };
    for (const n of nodes) n.el = null;
    info.elements = nodes.length;
    info.scope = snap.rootPath;
    if (side === "a") {
      stateRef.set(key, snap);
      return info;
    }
    const ref = stateRef.get(key);
    if (!ref) { info.error = "no side A snapshot for state " + key; return info; }
    if (ref.rootPath !== snap.rootPath) { info.error = "scope differs between the sides: " + ref.rootPath + " against " + snap.rootPath; return info; }
    info.result = diffState(ref, snap);
    return info;
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
