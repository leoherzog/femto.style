---
name: femto
description: Guides writing HTML and CSS with femto, the semantic CSS framework that styles plain HTML elements (npm @leoherzog/femto, femto.style, the plain-CSS successor to Pico CSS 2). Use this skill whenever a project links or imports femto (femto.min.css, @leoherzog/femto, --femto-* custom properties), when the user asks for a page, form, dashboard, landing page or prototype built with femto, when customizing femto's colors, themes, dark mode or tokens, when femto looks wrong after a build, or when migrating a site from Pico CSS to femto. Explains femto's approach to semantic HTML and how to fetch its current documentation as Markdown, which to read before writing any femto markup or CSS.
license: MIT
metadata:
  repository: https://github.com/leoherzog/femto.style
---

# femto

femto is one stylesheet that makes plain HTML look clean and readable. It styles elements by their names, so the elements are its API: headings, links, buttons, forms and tables need no classes. A few classes and attributes cover what HTML has no element for, and `--femto-*` custom properties change the rest. It is plain CSS, with no JavaScript, no Sass and no build step.

This skill is not the reference: the few names in it are examples. femto publishes its documentation as Markdown, and that is the reference. Fetch the sections a task needs before you write anything ([Fetching the docs](#fetching-the-docs)).

## Semantic HTML

Semantic HTML means choosing each element for what the content is, not for how it should look. The page's regions are `<header>`, `<nav>`, `<main>` and `<footer>`. A self-contained piece of content is an `<article>`, something that opens and closes is a `<details>` with a `<summary>`, a modal is a `<dialog>`, and a field is a `<label>` with its control. Browsers, search engines and assistive technology read those same elements, so markup that means the right thing also works for them.

femto rewards that choice. An `<article>` is a card and a `<details>` is an accordion, with nothing added, and a `<dialog>` holding an `<article>` is a modal that your script opens. Markup that only describes looks gets nothing: `<div class="card">` is an unstyled box.

## Recommendations

- **Read before you write.** Do not write femto's names from memory, or from what you know of Pico CSS. An unknown class or custom property fails silently, and femto's names can change between versions.
- **Start from the element.** Ask what the content is, choose the element that means it, then look up what femto does with that element.
- **Bring no classes from other frameworks.** femto has no utility classes for spacing, alignment, columns or sizes, so `.btn`, `.row`, `.col-6`, `.text-center` and `.mt-2` do nothing. Use only the classes the docs list.
- **Let attributes carry state.** femto styles states from the attributes assistive technology already reads, such as `aria-invalid`, `aria-busy` and `aria-current`. Set those instead of inventing state classes, and the page both looks right and announces right.
- **Customize from your own stylesheet.** Load it after femto's files and set femto's custom properties there. Never edit femto's files.
- **Use femto's colors, not literals.** A hardcoded color looks right in one color scheme and wrong in the other. Read the color from a femto custom property, and look at the page in both schemes.
- **Write your own rule when a layout needs more.** Put it in the project's stylesheet and build it from femto's custom properties, so it follows femto's spacing and both color schemes.
- **Expect to write the scripts.** femto ships no JavaScript. Where a component needs one, such as opening a modal, its docs section has it.

## Fetching the docs

The docs are one Markdown file per section, with an index:

| URL | Holds |
|---|---|
| `https://femto.style/docs.md` | The index: every section, with a one-line summary and its URL |
| `https://femto.style/docs/<id>.md` | One section |
| `https://femto.style/docs-full.md` | Every section in one large file |

Fetch the index first, then only the sections the task touches:

```sh
curl -fsSL https://femto.style/docs.md
curl -fsSL https://femto.style/docs/quick-start.md
```

Read the files verbatim. If your fetch tool summarizes pages, use `curl` instead, because token names and code samples must arrive exact. Fetch `docs-full.md` only when a task spans most of the docs, such as a full audit.

Links inside a section are absolute. A link that ends in `.md` is another section's file, so fetch it the same way. Any other link is an HTML page, often a large one: never print one whole. Five sections answer most questions:

- [Elements](https://femto.style/docs/elements.md): what femto does to each HTML element, with a link to its section.
- [Classes and attributes](https://femto.style/docs/classes.md): every class and attribute femto reads.
- [Tokens](https://femto.style/docs/tokens.md): each token, what it sets, and whether it has a light and dark pair. It leaves out the pairs' own names and the palette, which [CSS variables](https://femto.style/docs/css-variables.md) and [Colors](https://femto.style/docs/colors.md) describe.
- [Migrating from Pico](https://femto.style/docs/migration.md): every change from Pico CSS 2.
- [Browser support](https://femto.style/docs/browser-support.md): the browsers femto needs. Read it when colors or `data-theme` break only in a production build: a bundler has rewritten femto's `light-dark()` colors for older browsers.

Whole-page examples are at [femto.style/examples](https://femto.style/examples): one large HTML page, each example a `<section>` with an id. A docs link to `/examples#<id>` names one of them, so print only that one:

```sh
curl -fsSL https://femto.style/examples | sed -n '/id="pricing"/,/<section class="example"/p'
```

### The version in use

The site documents the newest femto. Check which version the project loads, from its `package.json`, lockfile or CDN URL. For a new project, take the link or the install command from Quick start, with any note there about prereleases. When the project loads an older version, its own README describes it, with the CSS it ships beside it:

- `node_modules/@leoherzog/femto/README.md`, with `css/` and `dist/`
- `https://cdn.jsdelivr.net/npm/@leoherzog/femto@<version>/README.md`

`npm view @leoherzog/femto dist-tags` shows the current versions.

### Without network access

Read the README and CSS in the installed package: `dist/femto.css` and `dist/femto.colors.css` are unminified, and between them hold every selector and custom property. If neither the site nor the package can be read, tell the user, and keep to plain semantic HTML, which femto styles with no names to get wrong.

## Before you finish

Search the femto CSS the project loads for every femto class and `--femto-*` name you wrote. The CSS holds them all, and the docs' Tokens section does not, so a name missing there is not yet wrong.

Request every femto URL you linked and confirm it answers with CSS. A stylesheet that answers 404 leaves the page unstyled, with no error.

If you can open the page in a browser, look at it in both color schemes.
