"""Forms: the Checkboxes section's indeterminate checkbox and the Select section's option groups."""
from behavior import check

GROUP = "forms"

BOX = 'article[aria-label="Indeterminate checkbox example"] input[type=checkbox][name=indeterminate]'


@check("checkbox-indeterminate", "/docs#checkboxes")
def checkbox_indeterminate(page):
    """The indeterminate example's checkbox (`input[name=indeterminate]` in
    `article[aria-label="Indeterminate checkbox example"]`) is indeterminate once the page has
    loaded (its indeterminate property is true and it matches :indeterminate), unchecked, with no
    indeterminate or checked attribute in the markup. A click makes it checked and no longer
    indeterminate, as a native checkbox does."""
    s = page.js(f"""const b = S.querySelector('{BOX}');
      return b && {{ind: b.indeterminate, matches: b.matches(':indeterminate'), checked: b.checked,
                   attrs: [...b.attributes].map(a => a.name).sort()}}""")
    page.expect("the checkbox exists", s is not None)
    page.eq("indeterminate after load", [s["ind"], s["matches"]], [True, True])
    page.eq("not checked", s["checked"], False)
    page.eq("its attributes are the markup's own", s["attrs"], ["name", "type"])
    page.click(page.find(BOX))
    page.wait("a click checks it", f"S.querySelector('{BOX}').checked && !S.querySelector('{BOX}').indeterminate", 1)


OPTGROUP = 'article[aria-label="Select option groups example"] select[name="favorite-dish"]'


@check("select-optgroup", "/docs#select")
def select_optgroup(page):
    """The Select section's option groups example is a select (`select[name=favorite-dish]` in
    `article[aria-label="Select option groups example"]`) with two <optgroup>s, Italian (Pizza,
    Risotto) and Japanese (Ramen, Sushi). Each optgroup has the select's computed font family, font
    size and line height (femto's reboot), and no margin. Choosing Ramen selects it, with no
    navigation."""
    from selenium.webdriver.support.select import Select
    state = f"""const s = S.querySelector('{OPTGROUP}');
      if (!s) return null;
      const font = (e) => {{ const cs = getComputedStyle(e); return [cs.fontFamily, cs.fontSize, cs.lineHeight]; }};
      return {{groups: [...s.querySelectorAll(':scope > optgroup')].map(g => [g.label, [...g.querySelectorAll('option')].map(o => o.textContent)]),
               select: font(s), optgroups: [...s.querySelectorAll('optgroup')].map(font),
               margins: [...s.querySelectorAll('optgroup')].map(g => getComputedStyle(g).marginTop + ' ' + getComputedStyle(g).marginBottom),
               value: s.value}}"""
    s = page.js(state)
    page.expect("the select exists", s is not None)
    page.eq("two option groups", s["groups"], [["Italian", ["Pizza", "Risotto"]], ["Japanese", ["Ramen", "Sushi"]]])
    page.eq("each optgroup has the select's font", s["optgroups"], [s["select"], s["select"]])
    page.eq("no optgroup margin", s["margins"], ["0px 0px", "0px 0px"])
    before = page.url()
    Select(page.find(OPTGROUP)).select_by_visible_text("Ramen")
    page.wait("choosing Ramen selects it", f"S.querySelector('{OPTGROUP}').value === 'Ramen'", 1)
    page.url_kept("no navigation", before)
