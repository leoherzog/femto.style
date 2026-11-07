// npm run lint (eslint --max-warnings 0 --no-error-on-unmatched-pattern site): the site's own CSS and
// JavaScript against femto's browser target, Baseline Widely Available (PLAN.md Decision 12, acceptance
// criterion 11). It only checks; it never fixes. build.mjs, vendor.mjs and tests/ are tooling that ships
// nothing, and they are outside the linted folder. --no-error-on-unmatched-pattern dates from Phase 0,
// when site/ held no CSS or JS of its own; it no longer has any effect. static_checks.py's
// planted-violation probe proves that every site file is linted.
import { defineConfig } from "eslint/config";
import css from "@eslint/css";
import baselineJs from "eslint-plugin-baseline-js";

export default defineConfig([
  {
    ignores: [
      // femto's own files at the commit vendor/femto/SOURCE names, byte for byte (criterion 12).
      // femto lints its CSS against the same target in its own repository.
      "site/vendor/",
    ],
  },
  {
    files: ["site/**/*.css"],
    language: "css/css",
    plugins: { css },
    extends: ["css/recommended"],
    rules: {
      // Each allowance added here (allowProperties, allowSelectors, allowFunctions, ...) needs a
      // comment with its reason, as femto's eslint.config.mjs gives.
      "css/use-baseline": ["error", {
        available: "widely",
        allowProperties: [
          // The Theme picker's swatches (docs.css) keep their box-shadow focus ring in forced colors,
          // and the unvisited ones their colors; in Firefox a visited swatch keeps only the border
          // docs.css gives it there. forced-color-adjust is in Chrome 89 and Firefox 113, the browsers
          // with a forced-colors mode; Safari has neither the property nor the mode, so nothing is
          // lost there. backdrop-filter is not allowed here: its one use (common.css) carries an
          // eslint-disable-next-line comment beside the -webkit- form it follows.
          "forced-color-adjust",
        ],
        allowPropertyValues: {
          // The oracle's footer build info (common.css) and the homepage hero's h1 and p
          // (landing.css) balance their lines. A browser without it wraps the text as usual, a
          // progressive enhancement femto's feature tiers allow.
          "text-wrap": ["balance"],
        },
      }],

      // The site's CSS uses femto's tokens (--femto-color, --femto-spacing, ...), which the vendored
      // femto stylesheet defines, and the rule only traces custom properties defined earlier in the
      // same file; femto's own config allows them for the same reason. Property names and values
      // without var() are still validated.
      "css/no-invalid-properties": ["error", { allowUnknownVariables: true }],
    },
  },
  {
    files: ["site/**/*.js", "site/**/*.mjs"],
    languageOptions: { ecmaVersion: "latest", sourceType: "module" },
    plugins: { "baseline-js": baselineJs },
    rules: {
      // Syntax, and the globals and static members of JavaScript's built-ins and of the Web APIs
      // (Promise.try, navigator.clipboard), each checked against Baseline Widely Available.
      // eslint-plugin-baseline-js 0.7.7 does not see instance members (Set.prototype.union,
      // element.moveBefore()), event-name strings ("loadingdone") or members of an options object
      // (focus()'s preventScroll): its README leaves instance members to its type-aware preset, which
      // needs TypeScript type information, from tools beyond those PLAN.md's Repo changes list. The
      // never-list below covers the cases known to matter.
      "baseline-js/use-baseline": ["error", {
        available: "widely",
        includeJsBuiltins: { preset: "auto" },
        includeWebApis: { preset: "auto" },
      }],

      // Decision 12 names features the site's JavaScript never uses, Widely Available or not. The
      // Phase 6 review added two outside the target that the plugin above cannot see: the loadingdone
      // event and focus()'s preventScroll. An event name is matched as a string anywhere
      // (addEventListener's first argument among them), as a template literal and as an on<event>
      // handler property. An option (container, preventScroll) is matched as a property of any
      // object, its key a name or a string, so an options object built ahead of the call is caught
      // too, and blocking as a string and as a member (script.blocking = "render").
      "no-restricted-globals": ["error",
        { name: "navigation", message: "Decision 12: no Navigation API." }],
      "no-restricted-syntax": ["error",
        { selector: "Literal[value='scrollend']", message: "Decision 12: no scrollend event." },
        { selector: "Literal[value='loadingdone']", message: "Decision 12: Safari never fires loadingdone; use document.fonts.load()." },
        { selector: "TemplateElement[value.cooked=/^(scrollend|loadingdone)$/]", message: "Decision 12: no scrollend event, and Safari never fires loadingdone; use document.fonts.load()." },
        { selector: "MemberExpression[property.name=/^on(scrollend|loadingdone)$/]", message: "Decision 12: no scrollend event, and Safari never fires loadingdone; use document.fonts.load()." },
        { selector: ":matches(Property[key.name='preventScroll'], Property[key.value='preventScroll'])", message: "Decision 12: focus({ preventScroll }) is outside the target (Samsung Internet 27, Chrome Android); save and restore the scroll position." },
        { selector: "Literal[value=/^(content-visibility|scroll-target-group)$/]", message: "Decision 12: no content-visibility or scroll-target-group." },
        { selector: "MemberExpression[property.name=/^(contentVisibility|scrollTargetGroup)$/]", message: "Decision 12: no content-visibility or scroll-target-group." },
        { selector: "Literal[value='blocking']", message: "Decision 12: no blocking=\"render\"." },
        { selector: "MemberExpression[property.name='blocking']", message: "Decision 12: no blocking=\"render\"." },
        { selector: ":matches(Property[key.name='container'], Property[key.value='container'])", message: "Decision 12: scrollIntoView({container}) is Chrome only; set the container's scrollTop." },
      ],

      // ESLint core rules that need no browser globals list. The recommended set lives in
      // @eslint/js, which is not one of the pinned tools (PLAN.md Repo changes), and no-undef would
      // need the globals package for the same reason.
      "no-unused-vars": "error",
      "no-unreachable": "error",
      "no-dupe-keys": "error",
      "no-duplicate-case": "error",
      "no-dupe-else-if": "error",
      "no-self-assign": "error",
      "no-self-compare": "error",
      "no-const-assign": "error",
      "no-func-assign": "error",
      "no-import-assign": "error",
      "no-unsafe-finally": "error",
      "no-unsafe-negation": "error",
      "no-cond-assign": "error",
      "no-fallthrough": "error",
      "no-redeclare": "error",
      "no-sparse-arrays": "error",
      "use-isnan": "error",
      "valid-typeof": "error",
      "eqeqeq": "error",
      "no-var": "error",
      "prefer-const": "error",
    },
  },
]);
