"""Forms: /docs/forms/checkboxes' indeterminate checkbox (01 §2, small widgets)."""
from behavior import check

GROUP = "forms"

BOX = 'article[aria-label="Indeterminate checkbox example"] input[type=checkbox][name=indeterminate]'


@check("checkbox-indeterminate", "/docs/forms/checkboxes")
def checkbox_indeterminate(page):
    """The indeterminate example's checkbox (`input[name=indeterminate]` in
    `article[aria-label="Indeterminate checkbox example"]`) is indeterminate once the page has
    loaded (its indeterminate property is true and it matches :indeterminate), unchecked, with no
    indeterminate or checked attribute in the markup. A click makes it checked and no longer
    indeterminate, as a native checkbox does."""
    s = page.js(f"""const b = document.querySelector('{BOX}');
      return b && {{ind: b.indeterminate, matches: b.matches(':indeterminate'), checked: b.checked,
                   attrs: [...b.attributes].map(a => a.name).sort()}}""")
    page.expect("the checkbox exists", s is not None)
    page.eq("indeterminate after load", [s["ind"], s["matches"]], [True, True])
    page.eq("not checked", s["checked"], False)
    page.eq("its attributes are the markup's own", s["attrs"], ["name", "type"])
    page.click(BOX)
    page.wait("a click checks it", f"document.querySelector('{BOX}').checked && !document.querySelector('{BOX}').indeterminate", 1)
