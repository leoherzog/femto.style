// colors.js: the Colors section of /docs (loaded from docs.html; it does nothing where its markup is
// absent). docs/research/01 §2 (docs.colors.jsx, ColorModal.jsx) and 03 §5.
//
// It rebuilds the section's color modal, attached through data-color-modal (PLAN.md Conversion
// rules: data- attributes from Phase 3). A click on a shade button (.family > .shades > button) or on a
// family's header (its main shade) inside that element opens dialog.color, with ColorModal.jsx's
// markup less its Sass variable row (femto has no Sass), appended to the Colors section (the oracle
// appended it to #content, its route's content) and removed again once closed. Its five rows are the
// color's hex and RGB values, its two utility classes and its custom property, as femto.colors.css
// names them. The arrow keys move through the 380 colors while it is
// shown: Right and Left the next and previous shade (across families, wrapping at both ends), Down
// and Up the next and previous family at the same shade. The close button, Escape and a click on the
// dialog outside its article close it, with ModalContext's classes and 400 ms animations from
// site.js's createModal, the dialog's own helper.
//
// Fixes over the oracle (PLAN.md oracle-bug, tests/behavior/customization.py):
// - the close control is a <button type="button"> (the oracle's was a link to #close), so the URL
//   keeps no #close;
// - focus is managed as a modal <dialog>'s would be: on open it moves to the close button; Tab and
//   Shift+Tab move through the dialog's own focus stops (the close button, then each value's copy
//   button) and wrap around at both ends, as showModal()'s inert page would, instead of reaching the
//   page behind (whose scroll position they would move); and when the dialog closes with focus
//   inside (or lost to <body>), focus returns to the element that had it before, as dialog.close()
//   does. The dialog itself stays non-modal (the open attribute, as the oracle's): showModal() would
//   put it in the top layer with a ::backdrop the oracle lacks;
// - the dialog is named by its title, says aria-modal (focus cannot leave it), and its title and the
//   color's name are a polite live region, so a screen reader reads each color an arrow key shows
//   (the oracle's dialog had no name and changed silently). The shade buttons get their color's
//   name too ("Red 50"), not the shade alone.
// The arrow keys only change the color, as in the oracle, whose focus stayed behind the dialog:
// their default action is cancelled, so they never scroll an overflowing article. Space, Page Up,
// Page Down, Home and End still scroll it from the close button: the keyboard's way to its lower
// rows.

import { createModal } from "./site.js";

// The palette download needs no script since Phase 3: its link points at the static file
// /assets/femto-color-palette.json, which build.mjs writes from SHADES and PALETTE below (the JSON the
// oracle's DownloadColorPalette made, in a blob: URL on load). build.mjs reads the two literals by
// their shape, so keep it: SHADES one array ending `];`, and each family `  <name>: ["<main>",`,
// then its colors, then `],`.

// --- The palette (app/data/colors.json at remix-final) -------------------------------------------
// family: [its main shade, then each of SHADES' colors as "<hex without #> <name>"]. The hex values
// are femto.colors.css's --femto-color-<family>-<shade>, and families and shades are in its order.
// The main shade is the one femto.colors.css gives the family's unshaded names (--femto-color-<family>,
// .femto-background-<family>, which the family's header shows): jade-550, for one (femto's README,
// Color utilities). colors.json's "main" was another shade for seven families (500 for red, fuchsia,
// blue, azure, cyan, jade and zinc).

const SHADES = ["50", "100", "150", "200", "250", "300", "350", "400", "450", "500", "550", "600", "650",
  "700", "750", "800", "850", "900", "950"];

const PALETTE = {
  red: ["550",
    "faeeeb Salt Pebble", "f8dcd6 Pale Shrimp", "f6cabf Sandblast", "f5b7a8 Pink Mimosa",
    "f5a390 Poppy Petal", "f38f79 Corralize", "f17961 Akebono Dawn", "f06048 Connect Red", "ee402e Cascara",
    "d93526 Shōjōhi Red", "c52f21 Bloody Red", "af291d Carnelian", "9b2318 Antique Port Wine",
    "861d13 Netherworld", "72170f Prune", "5c160d Cherrywood", "45150c Bean", "30130a Root Brew",
    "1c0d06 Bighorn Sheep"],
  pink: ["500",
    "fbedef Pale Cherry Blossom", "f9dbdf Carousel Pink", "f9c8ce Rosey Afterglow", "f9b4be Powder Rose",
    "f99eae Sweet 60", "f8889e Posy Petal", "f7708e Pink Explosion", "f6547e Macaroon Rose",
    "f42c6f Vivid Raspberry", "d92662 Qing Dynasty Fire", "c72259 Bright Rose",
    "b21e4f Minted Blueberry Lemonade", "9d1945 Berry Rossi", "88143b Atlas Red", "740f31 Deep Claret",
    "5f0e28 Plum Cheese", "4b0c1f What We Do in the Shadows", "380916 Ilvaite Black", "25060c Ponzu Brown"],
  fuchsia: ["550",
    "fbedf4 Lavender Blush", "f9daea Cherry Flower", "f9c6e1 Sugarwinkle", "f9b1d8 Hot Aquarelle Pink",
    "fa9acf Himalayan Balsam", "f983c7 Aries Hot Pink", "f869bf Kisses", "f748b7 Major Magenta",
    "ed2aac Magnificent Magenta", "d9269d Melodramatic Magenta", "c1208b Loulou's Purple",
    "ac1c7c Fabric of Love", "98176d Romantic Vampire", "84135e Cardinal Pink", "700e4f Velvet",
    "5c0d41 Plum Purple", "480b33 Dark Sanctuary", "360925 Vienna Roast", "230518 Belladonna"],
  purple: ["600",
    "f8eef9 Perfume Haze", "f2dcf4 Grape Taffy", "edc9f1 Sugar High", "e7b6ee Lovecloud",
    "e2a3eb Herb Robert", "db90e8 Bright Lilac", "d47de4 Lavender Perceptions", "cd68e0 Sensual Fumes",
    "c652dc Thick Pink", "b645cd Ultraviolet Berl", "aa40bf Fuchsia Pheromone", "9236a4 Purple Ink",
    "802e90 Druchii Violet", "6f277d Berry Blackmail", "5e206b Violethargic", "4d1a57 Shani Purple",
    "3d1545 Velvet Cosmos", "2d0f33 Synallactida", "1e0820 Meški Black"],
  violet: ["600",
    "f3eff7 Greek Goddess", "e8dff2 Lingering Lilac", "decfed Plum's the Word", "d3bfe8 York Plum",
    "c9afe4 Perfume", "bd9fdf Enchanted Lavender", "b290d9 Middy's Purple", "a780d4 Lavender Blossom",
    "9b71cf Iridescent Purple", "9062ca Amethyst", "8352c5 Fuchsia Blue", "7540bf Purple Rain",
    "6935b3 Purple Emperor", "5b2d9c Royalty", "4d2585 Spanish Violet", "3f1e6d Explorer of the Galaxies",
    "321856 Fabric of Space", "251140 Shadow Planet", "190928 Space Grey"],
  indigo: ["600",
    "f2f0f9 Sugar Crystal", "e5e0f4 Lingering Lilac", "d8d0f1 Japan Blush", "cac1ee Violet Gems",
    "bdb2ec Purple Sand", "b0a3e8 Dull Lavender", "a294e5 Dull Lavender", "9486e1 Perrywinkle",
    "8577dd Kickstart Purple", "7569da C64 Purple", "655cd6 Dark Periwinkle", "524ed2 Iris",
    "4040bf Early Spring Night", "3838ab Purple Cabbage", "2f2f92 Royal Night", "272678 Snorlax",
    "1f1e5e Intergalactic Cowboy", "181546 Tetsu-Kon Blue", "110b31 Spanish Roast"],
  blue: ["550",
    "f0f0fb Silver Phoenix", "e0e1fa Lavender Mist", "d0d2fa Miami White", "bfc3fa Light Periwinkle",
    "aeb5fb Greyish Lavender", "9ca7fa Widowmaker", "8999f9 Periwinkle Blue", "748bf8 Punch Out Glove",
    "5c7ef8 C64 NTSC", "3c71f7 Hailey Blue", "2060df Old Gungeon Red", "1d59d0 Bnei Brak Bay",
    "184eb8 Mourning Blue", "1343a0 Space Explorer", "0f3888 Magnus Blue", "0f2d70 Old Glory Blue",
    "0e2358 Fibonacci Blue", "0c1a41 Navy", "080f2d Mysterious Depths"],
  azure: ["550",
    "e9f2fc First Snow", "d1e5fb Veiling Waterfalls", "b7d9fc Broad Daylight", "9bccfd Apocyan",
    "79c0ff Broken Blue", "51b4ff Tiān Lán Sky", "01aaff Protoss Pylon", "029ae8 Pervenche",
    "018cd4 Zürich Blue", "017fc0 Honolulu Blue", "0172ad Cloisonné", "02659a Wavy Navy", "015887 Baby Shoes",
    "014c75 Blue Meridian", "014063 Lush Aqua", "033452 Dark Denim Blue", "052940 Nato Blue",
    "061e2f The Count's Black", "04121d Kuretake Black Manga"],
  cyan: ["550",
    "c3fcfa VIC 20 Blue", "58faf9 CGA Blue", "3deceb Phosphorescent Blue", "25dddd Fish Boy",
    "0ccece Tilla Kari Mosque", "0ac2c2 Cala Benirrás Blue", "0ab1b1 Swagger", "05a2a2 Pleasant Stream",
    "059494 Paradise Landscape", "058686 Green Moblin", "047878 Prismarine", "046a6a Mayan Blue",
    "025d5d Dark Turquoise", "015050 Wool Turquoise", "014343 Warm Black", "043737 Shrub Green",
    "052b2b Roof Tile Green", "051f1f Stellar Explorer", "041413 Black Glaze"],
  jade: ["550",
    "cbfce1 Out of Blue", "70fcba Ineffable Green", "39f1a6 Hyperpop Green", "21e299 Aqua Green",
    "00cc88 Retro Lime", "00c482 Píng Gǔo Lǜ Green", "00b478 Green Teal", "00a66e Sesame Street Green",
    "029764 Green Cyan", "00895a Vital Green", "007a50 Poplar Forest", "006d46 Clover Green",
    "005f3d Aotake Bamboo", "015234 Permanent Green", "00452b Alaskan Moss", "033823 Off-Road Green",
    "042c1b Bush", "052014 Clock Chimes Thirteen", "04140c Jedi Night"],
  green: ["500",
    "d7fbc1 Herbal Vapors", "95fb62 Stadium Lawn", "77ef3d Lush Greenery", "62d926 Green Apple",
    "5dd121 Verminal", "55c21e Frog", "4eb31b Luigi", "47a417 Lawn Green", "409614 Planter",
    "398712 Chlorophyll", "33790f Odd Pea Pod", "2c6c0c Tatzelwurm Green", "265e09 Lincoln Green",
    "205107 Patch of Land", "1a4405 Forest Green", "173806 Elite Green", "152b07 Lindworm Green",
    "131f07 Midnight Pines", "0b1305 Blackn't"],
  lime: ["200",
    "defc85 Mystic Green", "c1f335 Yellowy Green", "b2e51a Akhdhar Green", "a5d601 Vivid Lime Green",
    "99c801 Bergamot", "8eb901 Seasoned Apple Green", "82ab00 UFO Defense Green", "779c00 Green Thumb",
    "6c8f00 Canopy", "628100 Jungle Vibes", "577400 Over the Hills", "4d6600 Serrano Pepper",
    "435a00 Lustrian Undergrowth", "394d00 Godzilla", "304100 Garden Shadow", "273500 Blind Forest",
    "202902 Lindworm Green", "191d03 Black Mesa", "101203 Chinese Black"],
  yellow: ["100",
    "fdf1b4 Swiss Cheese", "f2df0d Xanthic", "e8d600 Holy Grail", "d9c800 Ryoku-Ou-Shoku Yellow",
    "caba01 Olive Ocher", "bbac00 Muddy Yellow", "ad9f00 Nuclear Fallout", "9e9200 Smoothie Green",
    "908501 Thicket Green", "827800 Soft Fig", "756b00 Brown Green", "685f00 Green Brown",
    "5b5300 Scorzonera Brown", "4e4700 Scorzonera Brown", "423c00 Storm", "363100 Wasabi Nori",
    "2b2600 Swamp of Sorrows", "1f1c02 Black Mesa", "141103 Darkness"],
  amber: ["200",
    "fcefd9 Desert Powder", "fddea6 Bachimitsu Gold", "fecc63 Qing Yellow", "ffbf00 Amber",
    "e8ae01 Sun Drops", "d8a100 Golden Beryl Yellow", "c79400 Retro Vibe", "b78800 Kenyan Sand",
    "a77c00 Hornet Yellow", "977000 Sandy Taupe", "876400 Alligator", "785800 Blackfire Earth",
    "694d00 Pickled Grape Leaves", "5b4200 Mud Brown", "4d3700 Night in the Woods",
    "3f2d00 Night in the Woods", "312302 Black Swan", "231a03 Cannon Black", "161003 Soulless"],
  pumpkin: ["300",
    "fceee3 Natural White", "fcdcc1 Karry", "fcca9b Orpiment Yellow", "feb670 Durazno Maduro",
    "ffa23a Blazing Bonfire", "ff9500 Barcelona Orange", "e48500 Fulvous", "d27a01 Autumn Leaf Orange",
    "bf6e00 Indocile Tiger", "ad6400 Ginger", "9c5900 Charlie Brown", "8b4f00 Plain Old Brown",
    "7a4400 Dusky Brown", "693a00 Bestial Brown", "593100 Eyelash Camel", "482802 Stirland Mud",
    "372004 Powdered Cocoa", "271805 Cannon Black", "180f04 Crowshead"],
  orange: ["500",
    "faeeea Rose White", "f9dcd2 Peony Prize", "f8cab9 Delicate Sweet Apricot", "f8b79f Pallid Orange",
    "f8a283 Creamy Peach", "f68e68 Melon Red", "f56b3d Chinese Orange", "f45d2c Raw Sunset",
    "e74b1a Nasturtium Flower", "d24317 Fire Bolt", "bd3c13 Devil’s Butterfly", "a83410 Shakshuka",
    "942d0d Dark Umber", "7f270b Mahogany Brown", "6b220a Moussaka", "561e0a Peaty Brown",
    "411a0a Chocolate Brown", "2d1509 Darkout", "1b0d06 Bighorn Sheep"],
  sand: ["200",
    "f2f0ec White Shoulders", "e8e2d2 Bud's Sails", "dad4c2 Stonewashed", "ccc6b4 Sapphire Light Yellow",
    "beb8a7 Historical Ruins", "b0ab9b Chatroom", "a39e8f Wooster Smoke", "959082 Stony Creek",
    "888377 Roller Coaster", "7b776b Slippery Shale", "6e6a60 Secret Passageway", "615e55 Office Grey",
    "55524a Masala", "49463f Whiskey and Wine", "3d3b35 Black Olive", "32302b Dryad Bark", "272622 Petroleum",
    "1c1b19 Siyâh Black", "111110 Dreamless Sleep"],
  grey: ["300",
    "f1f1f1 Snowflake", "e2e2e2 Titanium White", "d4d4d4 Disco Ball", "c6c6c6 Silver Polish",
    "b9b9b9 Baby Talk Grey", "ababab Dhūsar Grey", "9e9e9e Cold Grey", "919191 Tin", "808080 Grey",
    "777777 Lucky Grey", "6a6a6a Dim Grey", "5e5e5e Iron", "525252 Cavernous", "474747 Wood Charcoal",
    "3b3b3b Black Liquorice", "303030 Off Black", "262626 Nero", "1b1b1b Eerie Black",
    "111111 Dreamless Sleep"],
  zinc: ["550",
    "f0f1f3 Errigal White", "e0e3e7 White Iris", "d1d5db Angel Hair Silver", "c2c7d0 Cemetery Ash",
    "b3b9c5 Blunt", "a4acba Atelier", "969eaf Vesper Violet", "8891a4 Dusty Heather", "7b8495 Stowaway",
    "6f7887 Lunar Shadow", "646b79 Magic", "5c6370 Blue Metal", "4d535e Extinct Volcano",
    "424751 Midnight Sky", "373c44 Antarctic Deep", "2d3138 Suit Blue", "23262c Black Beauty",
    "191c20 Satin Deep Black", "0f1114 Ruined Smores"],
  slate: ["600",
    "eff1f4 Paper White", "dfe3eb December Dawn", "cfd5e2 Morning Chill", "bfc7d9 Himalayan Poppy",
    "b0b9d0 Cold Winter's Morn", "a0acc7 Foxflower Viola", "909ebe Periwinkle Blossom", "8191b5 Luxury",
    "7385a9 Berwick Berry", "687899 Chicory Flower", "5d6b89 Allegiance", "525f7a Award Night",
    "48536b Snoop", "3d475c Anthracite Blue", "333c4e Burka Black", "2a3140 Diamond Black",
    "202632 Sky Captain", "181c25 River Styx", "0e1118 Dark Rift"],
};

const FAMILIES = Object.keys(PALETTE);

function color(family, shade) {
  const entry = PALETTE[family][SHADES.indexOf(shade) + 1];
  const hex = `#${entry.slice(0, 6)}`;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(entry.slice(i, i + 2), 16));
  return { family, shade, hex, rgb: `rgb(${r}, ${g}, ${b})`, name: entry.slice(7) };
}

const mainShade = (family) => PALETTE[family][0];
const sentenceCase = (word) => word.charAt(0).toUpperCase() + word.slice(1);

// useFemtoPalette.js's getNextColor, getPreviousColor and getColorFrom{Next,Previous}ColorFamily.
function step({ family, shade }, key) {
  const f = FAMILIES.indexOf(family);
  const s = SHADES.indexOf(shade);
  const last = { f: FAMILIES.length - 1, s: SHADES.length - 1 };
  switch (key) {
    case "ArrowRight":
      if (s < last.s) return { family, shade: SHADES[s + 1] };
      return { family: FAMILIES[f === last.f ? 0 : f + 1], shade: SHADES[0] };
    case "ArrowLeft":
      if (s > 0) return { family, shade: SHADES[s - 1] };
      return { family: FAMILIES[f === 0 ? last.f : f - 1], shade: SHADES[last.s] };
    case "ArrowDown":
      return { family: FAMILIES[f === last.f ? 0 : f + 1], shade };
    case "ArrowUp":
      return { family: FAMILIES[f === 0 ? last.f : f - 1], shade };
    default:
      return null;
  }
}

// --- Color modal (ColorModal.jsx) -----------------------------------------------------------------
// The markup is ColorModal.jsx's as React renders it: the close icon is Close.jsx, and each value is
// Code.jsx's block (className "small", language html), its copy button carrying data-copy-link as
// the docs' own do, so site.js's copy handler takes it. Prism's markup grammar finds no token in any
// of the five values, so each is one plain text run, which react-syntax-highlighter writes as
// <span class="">.

const CLOSE_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round" class="icon-close"><path d="M18 6l-12 12"></path><path d="M6 6l12 12"></path></svg>';
const COPY_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round" class="clipboard"><path d="M8 8m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"></path><path d="M16 8v-2a2 2 0 0 0 -2 -2h-8a2 2 0 0 0 -2 2v8a2 2 0 0 0 2 2h2"></path></svg>';

// The five rows: label, and the value shown for a color.
const ROWS = [
  ["Hexadecimal color", (c) => c.hex.toUpperCase()],
  ["RGB color", (c) => c.rgb],
  ["Color utility class", (c) => `femto-color-${c.family}-${c.shade}`],
  ["Background utility class", (c) => `femto-background-${c.family}-${c.shade}`],
  ["Custom property", (c) => `var(--femto-color-${c.family}-${c.shade})`],
];

const families = document.querySelector("[data-color-modal]");
if (families) {
  const content = families.parentElement; // the Colors section
  // Each shade button is named by its color and shade ("Red 50"), not by the shade it shows alone.
  // The names are set here, not in colors.html, to keep the /docs HTML within its budget (PLAN.md
  // Risks); the buttons do nothing without this script anyway.
  for (const button of families.querySelectorAll(".family > .shades > button")) {
    const match = /(?:^|\s)femto-background-([a-z]+)-(\d+)(?:\s|$)/.exec(button.className);
    if (match && match[1] in PALETTE) button.setAttribute("aria-label", `${sentenceCase(match[1])} ${match[2]}`);
  }
  const dialog = document.createElement("dialog");
  dialog.className = "color";
  // Named by its title ("Red 500"). aria-modal: focus stays inside it, as the Tab handling below
  // keeps it. The title and the color's name are a polite live region, so a screen reader reads the
  // new color when an arrow key changes it while focus stays on the close button.
  dialog.setAttribute("aria-labelledby", "color-dialog-title");
  dialog.setAttribute("aria-modal", "true");
  // Each copy button is named by its row ("Copy hexadecimal color", "Copy RGB color"), so a screen
  // reader can tell the five apart; the row's label is a separate <p>.
  const copyButton = (label) => `<button type="button" class="copy-to-clipboard" aria-label="Copy ${label.replace(/^[A-Z](?=[a-z])/, (c) => c.toLowerCase())}" data-tooltip="Copy to clipboard" data-placement="left" data-copy-link>${COPY_ICON}</button>`;
  dialog.innerHTML = `<article><header><button type="button" aria-label="Close" class="close">${CLOSE_ICON}</button>`
    + '<hgroup aria-live="polite" aria-atomic="true"><h3 class="color-family" id="color-dialog-title"></h3>'
    + '<p class="color-shade"></p></hgroup></header><div class="grid">'
    + ROWS.map(([label]) => `<p>${label}</p><div class="code small" data-theme="dark">${copyButton(label)}`
      + '<pre class="prismjs"><code class="language-html"><span class=""></span></code></pre></div>').join("")
    + "</div></article>";
  const article = dialog.querySelector(":scope > article");
  const header = article.querySelector(":scope > header");
  const title = header.querySelector("h3.color-family");
  const name = header.querySelector("p.color-shade");
  const values = [...article.querySelectorAll(".grid pre code > span")];
  const closeButton = header.querySelector("button.close");
  // The dialog's focus stops, in document order: the close button, then each row's copy button. The
  // values fit their code blocks, so the blocks take no focus.
  const stops = [closeButton, ...article.querySelectorAll(".grid .code > button")];

  let current = null; // the color shown, while the dialog is in the page
  let opener = null; // the element that had focus when it opened

  // Fills the dialog in place (as React patches it), so focus inside it stays where it is.
  function show(family, shade) {
    current = color(family, shade);
    article.style.setProperty("--femto-glowing-color", `${color(family, mainShade(family)).hex}26`);
    fitHeight();
    header.className = `femto-background-${family}-${shade}`;
    title.textContent = `${sentenceCase(family)}\u00a0${shade}`; // a no-break space, as the JSX's &nbsp;
    name.textContent = current.name;
    ROWS.forEach(([, value], i) => {
      values[i].textContent = value(current);
    });
  }

  // react-div-100vh: the article's max-height follows innerHeight, on open and on every resize.
  function fitHeight() {
    article.style.maxHeight = `calc(${innerHeight}px - 2rem)`;
  }

  // While the dialog is in the page. Keys held with Alt, Control or Meta keep their default action
  // (the browser's own shortcuts); the arrows still step, as the oracle's did. Tab with Alt is still
  // Tab: Option+Tab is how Safari, by default, moves to links and buttons.
  function onKeydown(event) {
    const shortcut = event.altKey || event.ctrlKey || event.metaKey;
    if (event.key === "Tab") {
      if (event.ctrlKey || event.metaKey) return;
      event.preventDefault();
      const at = stops.indexOf(document.activeElement);
      const next = at < 0 ? 0 : (at + (event.shiftKey ? stops.length - 1 : 1)) % stops.length;
      stops[next].focus();
      return;
    }
    const next = current && step(current, event.key);
    if (!next) return;
    if (!shortcut) event.preventDefault();
    show(next.family, next.shade);
  }

  const modal = createModal(dialog, {
    onClosed() {
      removeEventListener("resize", fitHeight);
      document.removeEventListener("keydown", onKeydown);
      // Focus inside the dialog (or already dropped to <body> as it hid) goes back to the opener.
      const focused = document.activeElement;
      const lost = !focused || focused === document.body || dialog.contains(focused);
      if (lost && opener?.isConnected && opener !== document.body) opener.focus();
      dialog.remove();
      current = opener = null;
    },
  });

  function open(family, shade) {
    if (current) return; // shown, or still closing
    show(family, shade);
    content.append(dialog);
    addEventListener("resize", fitHeight);
    document.addEventListener("keydown", onKeydown);
    opener = document.activeElement;
    modal.open(); // the open attribute
    // The close button, in every browser and at every size: dialog.show()'s focusing steps would pick
    // the article instead where Chrome makes an overflowing one focusable (short viewports).
    closeButton.focus();
  }

  families.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest(".family > .shades > button");
    const familyHeader = target?.closest(".family > header");
    const match = /(?:^|\s)femto-background-([a-z]+)(?:-(\d+))?(?:\s|$)/.exec((button ?? familyHeader)?.className ?? "");
    if (!match || !(match[1] in PALETTE)) return;
    const family = match[1];
    const shade = button ? match[2] : mainShade(family);
    if (SHADES.includes(shade)) open(family, shade);
  });

  closeButton.addEventListener("click", () => modal.close());
}
