ultracode

Convert this repository from a Remix, React and Sass site into a plain HTML, CSS and JavaScript static site. Merge the docs into one page whose side nav and URL `#hash` follow the section being read, and finish with a site that uses femto 3.0 and describes it. `PLAN.md` is the spec, and its Decisions table is binding. The research behind it is in `docs/research/`.

You are on macOS with Google Chrome Beta, Firefox and Safari installed, the same rig femto's parity tests use (`../femto/tests/README.md`). Parity and behavior checks must pass in all three real browsers.

Before any other work, confirm these preconditions. Stop and ask me if any is missing:

- `dev` exists, its first commit is the rebrand ("Rebrand To femto"), and that commit is tagged `remix-final`. The working tree is clean apart from `.claude/launch.json`.
- `../femto` is a clean checkout at the commit to vendor. Name the commit and its `package.json` version back to me before you vendor it. On 2026-10-30 I approved 65453b74 (3.0.0-alpha.1).
- `safaridriver --enable` has been run, and Safari's Allow Remote Automation is on.
- `uv`, Node and `npx` are available, and the network is reachable for installing the oracle's locked toolchain.

Non-negotiables, all detailed in `PLAN.md`:

- **What ships.** Ship plain HTML, CSS and ES modules. The one build step only copies, expands includes, assembles the docs page with its side nav, highlights code and writes the sitemap. It never transforms CSS or JavaScript.
- **The oracle.** The Remix site at tag `remix-final` is the reference. Phases 1 to 3 change structure, not appearance or wording, and every difference is registered with a category and a reason.
- **One docs page.** One `docs.html` at `/docs`. Sections carry one-or-two-word ids on their top heading, and subheadings carry none. The scroll spy writes only the section `#hash`; links, deep links and history are the browser's own. There are no per-path copies, no `_redirects`, and no smooth scrolling on `html` itself.
- **Themes.** A theme color is `?theme=<color>`, written as a `<link>` before the first paint by the inline head script.
- **The spy.** Use only Widely available features as of 2026-11-13: no `scrollend`, Navigation API, `content-visibility`, `blocking="render"` or CSS scroll markers.
- **femto.** femto is vendored from a recorded commit. Docs content about femto comes from femto's README at that commit. When the two disagree, stop and tell me.
- **CSS.** Use `--femto-*` names everywhere, and femto's CSS rules for the site's own CSS: flat, unlayered, `color-mix(in srgb, …)`, and never `@layer`, `@scope`, `if()`, `@function`, `@mixin`, `@custom-media`, style queries or relative color syntax.
- **Tools.** Use the latest upstream version of every tool, checked on the web, except the oracle's locked toolchain. Run Python only through `uv run`.

How to work:

1. Read `PLAN.md` in full, then the reports it cites as you reach each phase.
2. Run one workflow per phase in `PLAN.md`'s Workflow table, in order. Scout before writing each script, and read each result before starting the next phase.
3. Build and prove the oracle and the harness in Phase 0 before converting anything.
4. Work on `dev`. Commit at each passed gate with the subjects in the Workflow table. Never push, and never deploy.
5. Before Phase 4, stop and bring me `PLAN.md`'s Open questions with your recommendation for each.
6. If a decision in `PLAN.md` proves wrong or impossible, stop and ask me. Do not work around it.
7. Keep `PLAN.md` current: record the measured performance budget, any change of mechanism, and new risks.

When you finish, or stop at a cap, report:

- Each acceptance criterion as pass or fail, with the command or result that shows it.
- The divergence registry, summarized by category.
- What remains unverified, especially anything Safari-specific.
- The commits made on `dev`.
