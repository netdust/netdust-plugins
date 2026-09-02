# sections/ — verified shapes to copy, not to reason from

Each file is one `section` node lifted from a shipped site (josworld's `Test — secties`
page, 2026-09-02), stripped of project copy, images and `jw-*` classes, and linted clean
against YOOtheme 5.0.43. Copy one, swap content and bindings, **keep every prop** — the
props that look like noise are the builder's own defaults.

| File | Shape | The setting that carries it |
|---|---|---|
| `hero-text.json` | two columns, h1 left, lead text bottom-right | `height: viewport` + `height_viewport`; column `vertical_align: bottom` |
| `header-page.json` | eyebrow + h1 (3-5) beside a bottom-aligned intro (2-5), wide image beneath | both columns `vertical_align: bottom`; row `layout` + column `width_medium` agree |
| `logo-marquee.json` | logo wall drifting on scroll | `panel-slider` with `slider_width: ""` + `slider_parallax`; a grid cannot bleed |
| `faq-accordion.json` | 2-5 intro + 3-5 accordion | the rule-between-items look is the default accordion — variables, no CSS |
| `grid-cpt-cards.json` | title + "see all" row, then a 3-up card grid bound to a CPT | the list query sits on the `grid_item`; `panel_link` + blank `link_text` |
| `cta-band.json` | centred eyebrow + h2 + button | column `text_align: center` (a universal prop) |

Load with `scripts/yoo_layout.py`:

```python
import yoo_layout as y
lib = y.library("sections/grid-cpt-cards.json")   # or a page dump
```

`_source` on the root is metadata; the linter and the builder ignore it (the builder
drops unknown node keys on save).
