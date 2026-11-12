// html-validate's rules for every HTML file in dist/ (PLAN.md acceptance criterion 9). It extends
// html-validate:recommended. Every rule turned off or changed here, and every change to the HTML5
// element metadata, carries its reason in the comment above it; static_checks.py checks that each
// one has one.
//
// Every other rule is on, as html-validate:recommended has it. What is left here follows from
// femto's own markup hooks and from one example's design.
export default {
  root: true,
  extends: ["html-validate:recommended"],

  elements: [
    "html5",
    {
      // The CSS variables example keeps the CSS it demonstrates in a <style> inside its <article>,
      // so the live example and its code sample are one block; browsers apply it. Only <style> is
      // added to <article>'s content; every other content model is html-validate's.
      article: {
        permittedContent: ["@flow", "style"],
      },
    },
  ],

  rules: {
    // femto styles summary[role="button"] as a button, and the Accordion and Dropdown sections show
    // it, so the role is femto's hook, not redundant. Other redundant roles still fail.
    "no-redundant-role": ["error", { exclude: ["button"] }],

    // femto styles [role="button"] as a button, and the docs use it on links that navigate (Get
    // started, the palette download) and show it on a <div> (the Button section), so a
    // <button> would be wrong for them. Other roles still fail; a scrolling div.overflow-auto named
    // as a region carries its own inline directive with its reason.
    "prefer-native-element": ["error", { exclude: ["button"] }],

    // The Button, Forms and Group sections show that femto styles <input type="submit">, "button" and
    // "reset" like a <button>; that is the point of those examples.
    "prefer-button": ["error", { exclude: ["submit", "button", "reset"] }],
  },
};
