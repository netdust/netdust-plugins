# ntdst-yootheme — lessons, by task

Symptom → cause → fix, verified on live installs (josworld 5.0.38→5.0.43, edushare
5.0.43). Mechanical traps carry a `yoo-lint:` code — run the linter instead of
remembering them. **Posture: reach for a SETTING, then a VARIABLE, then a HOOK, and
only then a rule.** Across two full sites the only un-settable things were image
grayscale, image max-height, flex-centring in a card, and one re-laid-out panel.

## 1. Authoring layout JSON

Caught by `scripts/yoo-lint.php` (run before every write; `yoo-content.php` runs it):

| symptom | cause | `yoo-lint:` |
|---|---|---|
| a prop sits in the JSON and changes nothing | the element never declared it (`padding`, `margin`, `border`, `alt`, column `position: center` = absolute!) | `unknown-prop` |
| props vanish on every save (a grid losing `parallax`) | no root `version` → every migration runs | `no-version` |
| the whole site 500s | an `X_item` without its `X` parent (`fragment > button_item`) | `orphan-item` |
| one column runs edge to edge despite `uk-width-1-2@m` | row `layout` declares more columns than exist, or a lone column with no row `alignment` (`tm-grid-expand`) | `layout-count`, `lone-column` |
| `block_align: right` and the image stays left | it needs `maxwidth`; use the column's `text_align` | `block-align-no-maxwidth` |
| `background_color` ignored | the save re-adds `style: "default"`; pass `style: ""` | `bgcolor-needs-empty-style` |
| an 8-column grid renders 6 | UIkit child-width stops at `1-6` | `grid-over-6` |
| a nested row shows a broken icon in the tree | bare `row` in a column; nest through `fragment` | `row-in-column` |
| a section lists as bare SECTION | no `name` | `unnamed-section` |

Not mechanical:

- **`layout` is the builder's column spec; the render reads each column's `width_*`.**
  Set both. Copy a working section and keep every prop rather than reasoning from
  `element.php` — the fields list is the UI, the template is what renders.
- **Nested containers break `width_expand`.** A real bleed needs section `width: ""`,
  row `width: "default"` + `width_expand: "right"`, and `container_padding_remove: true`
  on the bleeding element — all three, or the row shifts ~70px and still stops.
- **A background, radius or clip spanning several columns is one column holding a
  `fragment` (Sublayout) with a row inside.** The `class` prop lands on the column
  WRAPPER; the visible box is the inner `.uk-tile` — style that.
- **An absolute element collides once columns stack.** Pair two copies on `visibility`
  (`m` absolute, `hidden-m` in flow). A percent `position_top` on a zero-height panel
  computes to 0 — use px.
- **Full-bleed `vw` × `vh` hero crops by viewport ASPECT, not width.** Pre-crop the
  source to the band's ratio and pick `image_position`; `media_focal_point` only drives
  thumbnails.
- **A panel cannot put the image beside the title with the content full-width.** Keep
  `image_align: top` (parts stay siblings of `.el-item`) and re-place with CSS grid; the
  image child is a `<picture>`; the `uk-margin-top` on `.el-title/.el-meta/.el-content`
  is `!important`, so the override is too.
- **Scroll animation is native**: `animation: "parallax"` + `parallax_x/y/opacity`
  (`"from,to"` or `"v pos%"` stops) + `parallax_target: "!.uk-section"`. A logo marquee
  is a `panel-slider` with `slider_width: ""` + `slider_parallax` (a grid cannot bleed);
  omit `slider_parallax_start/end` on a short band or the track never moves.
  `slidenav_breakpoint` defaults to `xl` — arrows are absent below 1600px until lowered.
- Every element takes `class` and `attributes` (one `name=value` per line) — the way
  to attach a JS effect to a native element and keep its srcset.
- Settings people rebuild in CSS: `content_align` ("Force left alignment") for centred
  title + left body; `meta_style: h3` + `meta_align: above-title` for a display number;
  a column with `background_color` gets the "Round corners" checkbox; `title_margin_auto`
  pins a card part to the bottom; `image_width` AND `image_height` on a grid crop every
  card image alike; `height: viewport` is a MIN height.

## 2. Bindings

| symptom | cause | `yoo-lint:` |
|---|---|---|
| four one-card grids stacked, every count right | the list query sits on the `grid`; bind the `grid_item` | `list-on-container` |
| an element renders empty at a template root | `#parent` with no bound ancestor; use `<base>.single<Type>` | `parent-at-root` |
| `show_link: false` under `args` changes nothing | the key is `arguments` | `binding-args` |
| an image binding renders nothing | `featuredImage` is an object; bind `.url` / `.alt` | `bare-featured-image` |
| a box vanishes on every record, populated ones too | `_condition` on a repeater/relation (an array) | `condition-on-list` (with `schema=`) |

- **The empty-state gate for a list field is the SOURCE query**: the container takes the
  list with a `slice` directive of limit 1 and one `_condition` on a scalar sub-field —
  a source with `query` and no `props` is inert. `references/yootheme-content-binding.md`.
- **Query names derive from the post type** (`cases.customCases`, `teams.customTeams`,
  `verhalen.singleVerhaal`); custom fields bind by BARE schema key; `order: "field:x"`
  wants the STORED prefixed key. Read the live schema when unsure —
  `references/yootheme.md`.
- **`<taxonomy>String` is a LINKED term list.** `panel_link` (needs `show_link`) runs
  `striptags()` over title/meta/content, which flattens it — and a blank `link_text`
  suppresses "Read more". A `grid_item` has exactly three text slots.
- **Section `style` inverts the whole subtree** (`uk-light`): a white card inside a
  `secondary` band renders its title white on white. `preserve_color` on the section
  + `text_color: light` on the heading's column — both, and assert both colours.
- **"Behind the next section" is the NEXT section's job**: give it `position: relative;
  z-index: 1` via `css`; `z-index: -1` on the decoration hides it behind its own band.
- **A CPT archive shadows a same-slug page** — the layout belongs in an
  `archive-<type>` template. Templates match in stored order; the catch-all goes last.
- Templates and library items are COPIES on insert; `patch` the live copy for one-prop
  edits — a get → edit → set cycle loses a concurrent human save.

## 3. Site chrome

- **Re-read the config before every write** (`yoo-config.php get`): the Customizer
  rewrites the whole JSON on every human save; a snapshot from yesterday replaced a live
  style and API key.
- A menu item with `href="#"` is dropped from the markup, no empty `<li>`; WP puts
  menu-item classes on the `<li>`, never the `<a>`, so a CTA pill wraps an anchor UIkit
  stretches to the row height (`@navbar-nav-item-height` is a MIN).
- A builderwidget's content is echoed RAW — no `.tm-*` wrapper; assert on its own
  sections. `config.footer.content` is invisible to translation plugins — a footer that
  must translate is a builder widget in `bottom`.
- `.uk-svg` forces `fill: currentcolor` on the ROOT (`uk-preserve` does not protect it):
  give a stroked-only shape an explicit `fill="none"`. An SVG coloured by an internal
  `<style>` class is immune to the recolour — target its paths. Inlining the same file
  twice (desktop + mobile logo) duplicates ids.
- Theme static assets are served with a 10-year cache: VERSION the filename
  (`logo.<md5-8>.svg`); cold-cache tools cannot see the stale-cache bug the human sees.
- Polylang: `get_theme_mod('nav_menu_locations')` is a filtered view; read the raw option
  when debugging, and the `polylang` option's `nav_menus` mapping decides whether a
  header renders at all.

## 4. Styling — change values, not rules

- The Customizer edits section 2 (`@global-*`, `@button-*`, …), never section 1 tokens;
  the DB copy wins. Decide the source of truth in the file header.
- **`@global-secondary-font-family` is the UI role**, feeding ~18 `master/typo/` files
  (buttons, labels, navbar, forms, tabs). Keep it on the body face; re-state the display
  face on `@base-h4-font-family`. `@global-secondary-background` claims the toolbar and
  offcanvas; `@global-muted-color` tints toolbar, offcanvas and footer nav.
- **Per-heading colour, family, weight, tracking, transform are variables**
  (`@base-h1-color` … `@base-h6-text-transform`); `@article-title-color` is separate.
  Radii: `@button-border-radius` (+ `-small`/`-large`), `@card-border-radius`,
  `@card-default-box-shadow`, `@border-rounded-border-radius` (the column checkbox) —
  pin all panel radii to one token. Tiles have no radius variable: `.hook-tile-muted()`.
- **Text sizes are the four roles** (`lead` / `large` / `small` / `meta` — dropdown AND
  Styler variables) plus `h1`–`h6`. `lead` and `large` both default to 40px, which is
  why a bespoke class tempts; map `@text-lead-*` / `@text-large-*` instead. A font-size
  class in content HTML is invisible to the builder and the client.
- The FAQ "rule between items" look is the DEFAULT accordion (`@accordion-default-item-*`
  — the margin is spent twice per gap); only the icon needs a rule (`1em`).
- Non-obvious names: navbar spacing `@navbar-nav-gap-m`; grid dividers
  `@grid-divider-border`; `<mark>` `@base-mark-*`; `uk-label` is fully variable-driven.
  `@slidenav-*` cannot make a circle. `.hook-*()` mixins ACCUMULATE with the theme's.
- A `@line` token equal to the muted background is invisible on a muted band — un-blend
  the design's rule; it is often full ink.
- **LESS does not error on an assignment nothing reads** — `lessc` exit 0 is not
  evidence. Check names: `grep -rqE "^@$v:" vendor/assets/uikit{/src/less,-themes/master}/`.
- `.uk-container` is `box-sizing: content-box`: `@container-max-width` IS the content
  width; do not add the padding.
- Fonts: the Customizer selector self-hosts Google Fonts; an Adobe kit needs the theme
  to enqueue it and the family SLUGS (`dunbar-text`). Figma optical-size cuts are not
  families. Recompile with `scripts/yoo-recompile.mjs` — the Customizer is
  `admin-ajax.php?action=yootheme&yootheme=customizer`, not `customize.php`.

## 5. Verification

- **Measure, never grep.** `scripts/yoo-measure.mjs` — rects and computed styles at
  the design width, compared to Figma geometry. A class being present is not a check
  (`uk-position-center` is `position: absolute`).
- Compiled is not rendered: a different variable winning, a master-theme guard skipping
  the rule at `0`, or a stale stylesheet all pass a grep of the build.
- A passing measurement can be a coincidence — force the unequal case. A test derived
  from the same assumption as the code cannot falsify it — assert the measured box.
- Lazy-loading and un-painted images look broken: scroll into view, `await img.decode()`
  before a capture (`complete` and `naturalWidth` are not enough).
- CDP viewport screenshots go stale after a programmatic scroll — capture fullpage and
  crop; a fullpage capture can come back 2× wide. `--virtual-time-budget` does not
  advance the SMIL clock — `svg.pauseAnimations()` + `setCurrentTime(t)`.
- PNG-only references: derive the scale from two knowns that must agree (gutter and
  body line-pitch; it varies per export), un-blend a 1px rule per channel
  (`true = bg + Σ(row − bg)`), prefer the smaller of two candidate tokens.
- Don't `tail` test output — it hides `1 failed` behind "N passed".

## 6. Singles built in the builder (josworld, 2026-09-03)

A post that carries a builder layout renders through `page.php`
(`builder-wordpress/src/Listener/RenderBuilderPage.php`) and its `single-<type>`
template never runs. A single is template-rendered OR builder-rendered, never both;
keep the template as the trimmed fallback for a post without a layout.

| symptom | cause | fix |
|---|---|---|
| a built single loses the template's sections | the template does not apply once the post has a layout | expected — the starter layout carries the header; the template is the fallback |
| a text element bound to `content` duplicates the page or destroys the prose on save | on a builder page `content` IS the layout's own rendered introtext — a **self-echo** | never bind `content` on a builder page; use a plain text element |
| a "pick a post" item shows the wrong post before anyone picked one | `custom<Type>` with `id: 0` is "no filter" → the first published post | placeholder `id: -1` renders empty; the editor selects via "Select Manually" |
| a `relation` field to `attachment` resolves empty through the module | attachments are `inherit`, the resolver gates on `publish` | declare `file` / `image` / `gallery` — the native media types |

Starter layouts per type live in the builder library as `type: layout` entries with a
`name` (`Single · Tool`): `yoo-content.php library set starter.json` upserts by name.
The library lists both layouts and sections; a layout entry is offered with
"Replace / Insert at the top / Insert at the bottom".
