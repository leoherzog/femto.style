// html-validate's rules for every HTML file in dist/ (PLAN.md acceptance criterion 9). It extends
// html-validate:recommended. Every rule turned off or changed here, and every change to the HTML5
// element metadata, carries its reason in the comment above it; static_checks.py checks that each
// one has one.
//
// Phases 1 to 3 keep the oracle's example markup and wording (Decision 6, PLAN.md Text): a fix that
// changes an example's elements, attributes or text adds a difference the parity comparison reports.
// So a rule whose fix would change the oracle's markup conflicts with that choice, and it is off or
// narrowed here. Those marked "Phase 4 candidate" can be fixed when Phase 4 rewrites the content;
// the others conflict with femto's own markup hooks and stay.
export default {
  root: true,
  extends: ["html-validate:recommended"],

  elements: [
    "html5",
    {
      // The oracle's examples nest a <main> in an <article> (the Colors section's color families, the
      // Tooltip section's placement example) and put a <style> in the CSS variables example's
      // <article>, which browsers apply. Only those two article rules are relaxed; every other
      // element's content model is html-validate's. Phase 4 candidate.
      article: {
        permittedContent: ["@flow", "style"],
        permittedDescendants: [{ exclude: [] }],
      },
    },
  ],

  rules: {
    // 423 example <button>s have no type, as in the oracle: the Colors section's 380 swatches and the
    // other sections' examples. Phase 4 candidate.
    "no-implicit-button-type": "off",

    // Example inputs without a type, as in the oracle (the Forms section, the landing page's and
    // /demo's form). Phase 4 candidate.
    "no-implicit-input-type": "off",

    // The oracle's example forms, which show their fields and are never submitted, have no submit
    // button (the landing page, /demo, the Forms and Input sections). Phase 4 candidate.
    "wcag/h32": "off",

    // The oracle's fieldsets without a <legend>: femto's group (fieldset role="group") and the
    // examples in the Version picker, Color schemes, Forms, Radios and Switch sections. Phase 4
    // candidate.
    "wcag/h71": "off",

    // The Typography section's responsive font sizes table has header cells in a row and a column
    // without scope, as in the oracle. Phase 4 candidate.
    "wcag/h63": "off",

    // The footer's GitHub, jsDelivr and npm links show only an icon and are named by their title,
    // which the accessible name computation uses (axe-core's link-name passes); this rule counts
    // only text, img alt and aria-label. The footer is the oracle's on every page. Phase 4 candidate.
    "wcag/h30": "off",

    // Landmarks without a unique name, all in the oracle's markup: the header's and footer's navs on
    // every page; on the docs page its own shell, which Phase 3 keeps as the oracle's routes had it
    // (the <main>, the breadcrumb nav, aside#documentation-menu and its side nav, whose links
    // build.mjs writes); and the examples' navs, mains and asides, which repeat the shell's (the
    // breadcrumb examples repeat its aria-label="breadcrumb"). The shell's landmarks sit outside
    // every comparison root, so naming them could come before Phase 4; the examples' cannot.
    // Phase 4 candidate.
    "unique-landmark": "off",

    // The docs page has its own <main> and the oracle's example mains (Colors and Tooltip, above).
    // Phase 4 candidate.
    "no-multiple-main": "off",

    // The one page holds every example in one document, outside any form, so names the oracle used
    // once per route repeat (name="valid" and "invalid" in the Input, Textarea and Checkboxes
    // sections), and the Select section's two examples share name="pizza-topping" as in the oracle.
    // Decision 13 renames ids, not names, and no repeated name is a radio or details name
    // (criterion 9's own check). Phase 4 candidate.
    "form-dup-name": "off",

    // The trailing spaces are inside code samples, whose text is the oracle's byte for byte (PLAN.md
    // Text); in a <pre> they are content. Phase 4 candidate.
    "no-trailing-whitespace": "off",

    // The oracle's React style props, kept as style attributes: /demo's header, hero and scaled demo,
    // and a paragraph's margin in the CSS variables section. Only their properties are allowed, with
    // html-validate's default display; custom properties stay allowed, as by default (the Nav
    // section's breadcrumb divider). Phase 4 candidate: move them into the site CSS.
    "no-inline-style": ["error", {
      allowedProperties: ["display", "padding", "margin-top", "row-gap", "transform", "transform-origin", "margin-bottom"],
    }],

    // femto styles summary[role="button"] as a button and fieldset[role="group"] as a group, and the
    // docs show both, so the roles are femto's hooks, not redundant. Other redundant roles still fail.
    "no-redundant-role": ["error", { exclude: ["button", "group"] }],

    // femto styles [role="button"] as a button, and the docs use it on links that navigate (the skip
    // link, Get started, the palette download) and show it on a <div> (the Button section), so a
    // <button> would be wrong for them. Other roles still fail.
    "prefer-native-element": ["error", { exclude: ["button"] }],

    // The Button, Forms and Group sections show that femto styles <input type="submit">, "button" and
    // "reset" like a <button>; that is the point of those examples.
    "prefer-button": ["error", { exclude: ["submit", "button", "reset"] }],
  },
};
