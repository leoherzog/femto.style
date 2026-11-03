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
          // The docs header's blur (common.css) is written after -webkit-backdrop-filter, which
          // femto keeps for Safari 17.5 to 17.x; backdrop-filter is Baseline 2024 (Safari 18), and
          // femto's config allows it for the same pair.
          "backdrop-filter",
        ],
        allowPropertyValues: {
          // The oracle's footer build info (common.css) and the landing pages' hero text and example
          // titles (landing.css) balance their lines. A browser without it wraps the text as usual,
          // a progressive enhancement femto's feature tiers allow.
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
      // Syntax, JavaScript built-ins and Web APIs, each checked against Baseline Widely Available.
      "baseline-js/use-baseline": ["error", {
        available: "widely",
        includeJsBuiltins: { preset: "auto" },
        includeWebApis: { preset: "auto" },
      }],

      // Decision 12 names features the site's JavaScript never uses, Widely Available or not.
      "no-restricted-globals": ["error",
        { name: "navigation", message: "Decision 12: no Navigation API." }],
      "no-restricted-syntax": ["error",
        { selector: "Literal[value='scrollend']", message: "Decision 12: no scrollend event." },
        { selector: "Literal[value=/^(content-visibility|scroll-target-group)$/]", message: "Decision 12: no content-visibility or scroll-target-group." },
        { selector: "MemberExpression[property.name=/^(contentVisibility|scrollTargetGroup)$/]", message: "Decision 12: no content-visibility or scroll-target-group." },
        { selector: "Literal[value='blocking']", message: "Decision 12: no blocking=\"render\"." },
        { selector: "CallExpression[callee.property.name='scrollIntoView'] Property[key.name='container']", message: "Decision 12: scrollIntoView({container}) is Chrome only; set the container's scrollTop." },
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
