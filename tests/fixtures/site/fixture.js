// Nondeterminism that only the harness masks may hide (tests/harness/masks.json), like the oracle's:
// a "typing demo" that rewrites its article on a timer, and a random progress value printed in the
// code below it.
(function () {
  var art = document.querySelector(".demo > article.component");
  var typing = art.querySelector(".typing");
  var n = 0;
  setInterval(function () {
    n++;
    typing.textContent = Math.random().toString(36).slice(2, 3 + (n % 9));
    if (art.children.length < 12) {
      var s = document.createElement(n % 2 ? "span" : "em");
      s.textContent = String(n);
      s.className = "t" + n;
      art.appendChild(s);
    }
  }, 30);
  var bar = document.querySelector('article[aria-label="Progress example"] > progress');
  // The first attr-value token that is not punctuation, as in the oracle's Prism output (masks.json).
  var printed = document.querySelector('article[aria-label="Progress example"] > footer > pre > code > :nth-child(1 of .attr-value:not(.punctuation))');
  function randomize() {
    var v = Math.floor(Math.random() * 90) + 5;   // one or two digits, like the oracle's
    bar.value = v;
    printed.textContent = String(v);
  }
  randomize();
  setInterval(randomize, 500);
})();
