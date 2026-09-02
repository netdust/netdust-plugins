# ntdst-yootheme — lessons

Hard-won corrections and recipes, all verified against a live YOOtheme Pro 5.0.38
install (josworld, 2026-08-04): symptom → cause → fix. Read §1 first; between
them those traps cost most of a session.

---

## 0. The default posture

**Reach for a SETTING, then a VARIABLE, then a HOOK, and only then a rule.**

Across one session building a header, footer, hero, logo strip, two-column band
and case grid, the only genuinely un-settable things were: image grayscale, image
max-height, and flex-centring inside a card. Everything else — including
scroll-linked animation — was already in the product.

When you think "YOOtheme can't do X", you are usually wrong. Check
`packages/builder/elements/<type>/element.php` → `fields`, and the shared set in
`packages/builder/config/builder.php`, before writing anything.

---

## 1. Traps that silently do the wrong thing

### 1.1 Hand-authored layout JSON MUST carry a root `version`

```json
{"type":"layout","children":[…],"version":"5.0.38"}
```

Without it the save pipeline runs EVERY migration in `elements/*/updates.php`
from the beginning, rewriting props with no error. Real case: a `grid` with
`animation:"parallax"` lost it on every save because `grid/updates.php` does
`$node->props['animation'] = $node->props['item_animation'] ?? ''`. Two of four
parallax props survived — which reads as "this element doesn't support
parallax". Copy the version from an existing page: `yoo-content.php page get <id>`.

### 1.2 `.uk-svg` forces `fill: currentcolor` on the ROOT

```css
.uk-svg, .uk-svg:not(.uk-preserve) [fill*="#"]:not(.uk-preserve) { fill: currentcolor }
```

The first selector is a bare `.uk-svg` — **`uk-preserve` does not protect the
root**. Any descendant without its own `fill` then inherits the theme colour
instead of the root's `fill="none"`. Symptom: an inlined logo renders as a solid
blob while being correct as `<img>` and correct rendered standalone — so it looks
like a masking or ID bug. Fix in the ASSET: explicit `fill="none"`. Diagnose with
`getComputedStyle(svgRoot).fill`.

### 1.3 A section's `background_color` needs `style: ""`

The template gates it on `{@!style}`, and the save re-adds the element default
`style: "default"` — so *removing* the key does nothing. Pass an explicit empty
string.

### 1.4 UIkit child-width stops at `1-6`

`grid_medium: "8"` emits `uk-child-width-1-8@m`, which does not exist, and the
grid silently falls back to the next breakpoint down. Verify class names against
the compiled CSS, never against assumption.

### 1.5 `media_focal_point` is inert for a cover background

It only drives server-side *thumbnail* cropping. For a section background it
changes nothing — `image_position` is what maps to `uk-background-<pos>`. Setting
the focal point and getting pixel-identical output is the tell.

### 1.6 Inlining an SVG duplicates its IDs

`logo.image_svg_inline` inlines the same file for the desktop AND mobile header,
so ids collide and `mask="url(#i1)"` in the second copy resolves to the first
copy's mask. It renders only because they are identical. Namespace ids per
instance before touching inlined SVGs from JS.

### 1.7 UIkit's margin utilities are `!important` — your override loses

```less
.uk-margin-top { margin-top: @margin-margin !important; }   // margin.less:44
```

The builder stamps `uk-margin-top` on `.el-title`, `.el-meta` AND `.el-content` of
every panel. So a component class that sets `margin: 0` does nothing — at ANY
specificity. Symptom: a name/role pair sitting a full `@global-margin` apart while
your rule is visibly applied in DevTools and the computed value is still 24px.
Fix: `margin: 0 !important`. That is not a shortcut, it is the only thing that
beats an `!important` utility — assume it for every `.el-*` margin you override.

### 1.8 `block_align` does nothing unless `maxwidth` is also set

`'enable' => "position != 'absolute' && maxwidth"` (`config/builder.php`), and the
description is precise: it aligns the element *"in case the container exceeds the
element max-width"*. With no `maxwidth` the prop is still written into the layout
JSON and emits no class. Symptom: `"block_align": "right"` sitting in the JSON,
image still hard left in its column. Fix: set the COLUMN's `text_align` instead —
the image is inline and follows it.

### 1.9 `slidenav_breakpoint` defaults to `xl`

`panel-slider`'s own defaults are `'slidenav_breakpoint' => 'xl'` and
`'slidenav_outside_breakpoint' => 'xl'`, so the arrows are wrapped in
`uk-visible@xl` and are simply absent below 1600px. Symptom: you set
`slidenav: center-right`, the markup is in the DOM, nothing renders at 1440.
Its sibling `nav_breakpoint` defaults to `s`, so the DOTNAV does show — which
makes it read as "the slidenav specifically is broken". Fix: lower it to `m`.

Related: `slider_finite: true` greys the prev arrow on slide 1 and collapses the
dotnav to (items ÷ per-view) dots. For a testimonial carousel `false` is usually
what the design shows.

### 1.10 `grid_divider` is not a rule per item

"Show a divider between grid columns" means literally that:
`.uk-grid-divider > :not(.uk-first-column)::before` is a VERTICAL line BETWEEN
columns, and it also doubles the gutter
(`margin-left: -(@grid-gutter-horizontal * 2)`). A rule ABOVE each item — the
classic stat-column look — is a `border-top` on `.el-item` and nothing else.

### 1.11 A nested container silently breaks `width_expand`

Row `width_expand: left|right` emits `uk-container-expand-{side}`, whose max-width
is `calc(50% + (@container-max-width / 2) - @container-padding-horizontal-m)`.
That `50%` is of the PARENT. Put the row inside a section that ALSO has a
container and you get two nested containers: UIkit zeroes the inner one's padding,
the `50%` resolves against the wrong box, and the row shifts ~70px toward the
expanding side **without bleeding**. Symptom: "expand-right is broken" — the
content moved sideways and still stops at the container edge.

A real bleed needs all three, and they only work together:

| where | setting |
|---|---|
| section | `width: ""` (None — no container at all) |
| row | `width: "default"` + `width_expand: "right"` |
| the element that bleeds | `container_padding_remove: true` |

The last one emits `uk-container-item-padding-remove-right`; without it the
element stops one container-padding short of the viewport edge.


---

### 1.12 An invented prop name is not an error — it is a missing class

YOOtheme stores whatever you write. A prop the element does not declare is
persisted into the layout JSON, emits nothing, and the element falls back to a
default that looks like a styling bug. Three of these in ONE hand-authored
section (edushare Verhaal detail, 2026-09-02):

| written | what it actually is |
|---|---|
| column `position: "center"` | **absolute positioning** — emits `uk-position-center` (`position:absolute; top:50%; left:50%`). The body section floated on top of the hero. The prop that centres a column is the ROW's `alignment`. |
| row `width` / `flex_align`, column `width_default` | not props at all. The row falls back to `uk-child-width-1-1`, so two auto-width items stretched to full width and a `uk-label` chip became a page-wide bar. |
| image `border: "rounded"` | the image element's own prop is **`image_border`**; the shared `border` belongs to columns. |

The whole vocabulary is small and readable from a working project's template
store (`yoo-templates-backup-*.json` in the repo root). Across every josworld
template, rows carry only `alignment` / `layout` / `column_gap` / `row_gap` /
`margin_top`, and columns only `width_medium` / `vertical_align` / `text_align`
/ `padding` / `class` / `background_color` / `border`.

**`layout` is the BUILDER's column spec, not the renderer's.** A row's
`layout: "3-5,2-5"` is what the UI writes; the render reads each COLUMN's own
`width_*`, which is why every josworld column also carries `width_medium`. Set
one and not the other and the row silently collapses to `1-1`.

When unsure, do not reason from the element definition — copy a working section
out of another project's template store and swap content and bindings, keeping
every prop.

### 1.13 Binding paths: the query name is derived, and objects need a sub-field

`Helper::getBase()` decides the query prefix: `rest_base`, unless it is empty or
equal to the post type name, in which case `name . 's'`. So `case`+rest_base
`cases` → `cases.`, `team`+rest_base `team` → `team**s**.`, `tool` with no
rest_base → `tools.`, and `verhaal`+rest_base `verhalen` → `verhalen.`. The
single-post field is `Str::camelCase(['single', $type->name])`, giving
`verhalen.singleVerhaal`.

`featuredImage` is an **`Attachment` OBJECT**, not a URL. Binding an image needs
the sub-field path — `featuredImage.url`, with `featuredImage.alt` for alt text.
Binding the bare object renders nothing at all.

A custom `queryType` is only needed if you want your own query. Registering an
`objectType` under the name YOOtheme already uses for that post type MERGES into
it (`SchemaBuilder::objectType()` reuses `$this->types[$name]` and appends to
`$this->configs[$name][]`), so custom fields ride on the built-in
`single<Type>` query with no PHP.


## 2. Scroll animation is native — do not write JS

```json
{"animation":"parallax","parallax_x":"18vw,-18vw",
 "parallax_target":"!.uk-section","parallax_easing":"0"}
```

* Props: `parallax_x` `parallax_y` `parallax_scale` `parallax_rotate`
  `parallax_opacity` `parallax_blur`, plus `parallax_transform_origin`,
  `parallax_easing` (−2…2), `parallax_target`, `parallax_breakpoint`.
* Multi-stop with optional positions: `"1 30%,0 60%"`. Units `%`, `vw`, `vh`.
* `parallax_target: "!.uk-section"` scopes the scroll range to the closest
  section (`!` = closest ancestor).
* The element-level `animation` field only exists where the element declares
  `${builder.animation}`; the SECTION must have animations enabled.
* Emits `uk-parallax="x: …; easing: …; target: …"`. Attribute missing ⇒ the props
  were stripped ⇒ see trap 1.1.

### A scroll-linked horizontal MARQUEE is a slider, not a grid

For a logo wall that drifts sideways as the page scrolls, use **`panel-slider`
with its OWN `slider_parallax`** — not a grid carrying the generic element
parallax. Reference implementation: Glowbar's homepage service section.

```json
{"type":"panel-slider","props":{
  "slider_width":"",                 // Auto — each slide is only as wide as its
                                     // content, so far more logos fit on screen
  "slider_gap":"large",
  "slider_finite":false,             // loops; never runs out
  "slider_parallax":true,
  "slider_parallax_target":"!.uk-section",
  "slider_parallax_easing":"0",
  "nav":"", "slidenav":"",           // a logo wall has no controls
  "panel_match":false,
  "show_image":true,"show_title":false,"show_meta":false,
  "show_content":false,"show_link":false}}
```

Why not a grid: a grid caps at 6 columns (see 1.4) and is exactly
container-width, so translating it opens a visible gap at one edge. **A slider
track overflows the viewport**, which is what produces the design's
cut-at-both-edges marquee. A grid simply cannot express that.

**Gotcha — do not copy Glowbar's offsets.** It sets
`slider_parallax_start` / `_end` to `"100vh"`, which suits its full-height
section. On a ~100px logo strip those offsets push the active range outside any
reachable scroll position and the track NEVER moves: `transform` stays `none`
while the component happily reports `parallax: true` with a correctly resolved
target — so it looks like the feature is broken rather than mis-tuned. Omit
start/end and let them default to 0.

Probe a live slider with
`UIkit.getComponent(el,'slider')` → `.parallax`, `.parallaxTarget`, `.length`.

**Mine the official demos for real examples** — they are the only authoritative
corpus, and `~/Sites/yootheme-template` holds all six:

```bash
unzip -p <demo>_demo_package_wordpress.zip 'wp-content/sample_yootheme.json' > demo.json
grep -o 'parallax_x' demo.json | wc -l     # quantum-flares 61, kojiro 15, glowbar 2
```

`unzip -p` the single JSON; never unpack the archives (up to 2 GB).

---

## 3. Builder elements take arbitrary classes and attributes

Every element has shared `class` and `attributes` fields (Advanced panel). In
layout JSON the prop names are **`class`** and **`attributes`** — NOT the config's
internal `cls` / `attrs` keys. The render path is `ElementTransform::__invoke`,
which reads `props['class']`. `attributes` is one `name=value` per line.

This is the clean way to attach third-party behaviour to native elements — e.g.
`class: "image-scroll-effect"` + `attributes: "data-effect=clip-up"` on a real
image element, keeping YOOtheme's responsive srcset. No PHP, no HTML element.

---

## 4. Layout recipes

Everything down to the Sublayout note is a SETTING — reach for these before
writing anything. The last two (`image_align: top` + CSS grid, and the rounded
band) are the only two layouts in a full marketing site that genuinely needed a
rule; they are here so the next session recognises the shape instead of
rediscovering that the builder cannot express it.


| Want | Setting |
|---|---|
| Card images all the same height | Set **both** `image_width` AND `image_height` on the grid → cropped thumbnail at that exact ratio |
| A card part pinned to the card's bottom | `title_margin_auto: true` (the title absorbs the slack). **Not** `content_margin_auto` — that emits `uk-margin-auto-bottom`, which pushes *up* |
| Arbitrary column content pinned to the bottom | Column `class: "uk-flex uk-flex-column"` + the element's `margin_top: "auto"`. UIkit grid children already stretch to the tallest |
| Full-bleed band at a fixed height | Section `width: expand`, `height: viewport` + `height_viewport: <n>` |
| Exact NNvh across a multi-band block | Give EVERY band a `height: viewport` value. `uk-height-viewport` is a MIN-height, so wrapped text still grows on mobile |

### Nesting: the `fragment` element is a SUBLAYOUT

The builder spine reads `layout → section → row → column → element`, so it is easy
to conclude a row cannot be nested. It can: the **`fragment`** element is titled
**"Sublayout"** (`container: true, fragment: true`) and renders its `children` as a
full layout, rows included.

```
column  (style: tile-muted, class: jw-tile-card)   <- ONE element = the card
└ fragment (Sublayout)
  └ row (1-2,1-2)
    ├ column   <- imagery
    └ column   <- text
```

Reach for it whenever **a background, border-radius or clip must span several
columns**. The alternative — two collapsed `tile-*` columns — forces per-corner
radii AND a media query to swap which corners round once the columns stack, plus a
separate `overflow: hidden` to clip anything bleeding past the edge. With a
Sublayout it is two declarations on one element and correct at every breakpoint:

```less
.jw-tile-card > .uk-tile { border-radius: @jw-r-lg; overflow: hidden; }
```

**Mind the selector.** A `class` prop lands on the column WRAPPER, which is
transparent and wider than the styled box inside it (grid gutter). Rounding the
wrapper clips nothing you can see — the visible panel is the inner `.uk-tile`, so
the radius and the clip belong there. Symptom: computed `border-radius: 16px`
with `overflow: hidden` on the element you classed, and square corners on screen.
Check `getComputedStyle(el).backgroundColor` — if it is `rgba(0,0,0,0)` you are
styling the wrong box.

### An absolutely-positioned element WILL collide once columns stack

Absolute elements reserve no space. A portrait card layered over a square
decorative shape fits fine beside it on desktop, then prints straight over the
next column's heading on mobile, because the shape (in flow) is what sets the
column height. YOOtheme's own idiom fixes it with no CSS — pair two copies on
complementary `visibility`:

| copy | position | visibility |
|---|---|---|
| desktop | `absolute` (exact placement) | `m` — show from medium up |
| mobile | in flow (reserves space) | `hidden-m` — hide from medium up |

Related: to shift a decorative element that must ALSO drive its column's height,
use `position: relative`, not `absolute` — it keeps its layout box so the column
cannot collapse, while `position_left/top` nudge it visually.

### Full-bleed hero cropping

When a band's width is `vw` and its height `vh`, the crop depends on the
**viewport's aspect ratio, not its width** — every 16:9 screen crops identically
whether it is 1366 or 2560 wide. Measuring by widening at a fixed pixel height
is misleading: that simulates ever-more-ultrawide screens, not bigger monitors.

You cannot have full-bleed width + fixed `vh` height + constant framing — pick
two. Tying height to width (`clamp()`/`max()` on `vw`) fixes framing but the hero
stops fitting the screen. The cheapest real fix is **a source pre-cropped to the
band's aspect** (~3:1), plus `image_position` to choose what is lost.

### Re-laying out a panel: `image_align: top` is the ENABLING setting

A panel is either a flat stack or — with `image_align: left|right` — a `uk-grid`
wrapper holding the image in one column and title + meta + content + link ALL in
the other (`elements/panel/templates/template.php:106`). So the common review-card
shape (avatar beside the name, quote BELOW at full card width) is not expressible
as settings: `left` drags the quote into the right column with the name.

The way through is to KEEP `image_align: top` — that is the setting which leaves
the four parts as SIBLINGS of `.el-item` — and re-place them with CSS grid:

```less
.el-item          { display: grid; grid-template-columns: auto 1fr;
                    grid-template-rows: auto auto 1fr; }
.el-item > picture,
.el-item > .el-image  { grid-column: 1; grid-row: 1 / span 2; align-self: center; }
.el-item > .el-title  { grid-column: 2; grid-row: 1; align-self: end;   }
.el-item > .el-meta   { grid-column: 2; grid-row: 2; align-self: start; }
.el-item > .el-content{ grid-column: 1 / -1; grid-row: 3; }
```

Four things that are easy to get wrong:

* **The image child is a `<picture>`, not the `<img>`.** YOOtheme wraps every
  image for its webp source, so `.el-image` is on the INNER element and a
  `> .el-image` child selector misses entirely. Match both.
* **`end` + `start` either side of a shared row boundary centres the title/meta
  pair as a UNIT.** The image spans both rows, grid splits its leftover height
  equally between them, and the two lines park against the split. Setting both to
  `center` spreads them to opposite ends of the image instead.
* Their margins will fight you — see trap 1.7.
* Make the content row `1fr` and turn on `panel_match` (`uk-grid-match`); then a
  last child with `margin-top: auto` pins to the bottom of every equal-height
  card instead of hanging under a short one.

### Three settings people rebuild in CSS

| Want | Setting |
|---|---|
| Centred title/image with LEFT-aligned body copy | `content_align` on the grid — it is labelled **"Force left alignment"** |
| A big display number above a label | `meta` field at `meta_style: h3` (meta_style takes h1–h6) + `meta_align: above-title` |
| A white panel with round corners and padding, without a card | a COLUMN with `background_color` set — it gains a `border` checkbox labelled **"Round corners"** (`uk-border-rounded`) and picks up `uk-tile` padding automatically |

### A band that reads as "laid over" the next section

Rounding only the BOTTOM of a section opens two corner notches that show whatever
is behind the section — the page background, not the next section. One
pseudo-element painted behind the section's own background fills them, with no
extra element in the builder:

```less
.band  { position: relative;
         border-bottom-left-radius: @r; border-bottom-right-radius: @r; }
.band::before { content: ""; position: absolute; left: 0; right: 0; bottom: 0;
                height: @r; background-color: @next-section-colour; z-index: -1; }
```

`position: relative` with `z-index: auto` does NOT open a stacking context, so
`z-index: -1` lands under the parent's own background but still above the page
canvas. Take the colour from the same variable the next section uses
(`@global-primary-background` for a `style: primary` footer) so it tracks it
instead of drifting.


---

## 5. Styling: change values, don't write rules

* **UIkit's `.hook-<component>-<part>()` mixins are the sanctioned extension
  point.** Redefining one ACCUMULATES with the empty default and the theme
  layer's copy (LESS applies every same-name mixin in source order), so the
  theme's own declarations survive. Needed for `.hook-subnav-item()` (subnav has
  no resting `text-decoration` variable) and `.hook-label()` (no border variable).
* **Check the variable surface before concluding there isn't one.** `uk-label` is
  fully variable-driven — `@label-background`, `@label-color`,
  `@label-border-radius`, `@label-padding-*`, `@label-font-size`,
  `@label-text-transform`. An outlined pill is a value change plus one hook.
* Non-obvious names that cost time:
  * navbar item spacing is **`@navbar-nav-gap-m`**, not
    `@navbar-nav-item-padding-horizontal` (the theme layer zeroes that and spaces
    the navbar with flex gaps).
  * grid dividers are **`@grid-divider-border`** — a different variable from
    `@base-hr-border`, which drives `<hr>`.
  * `<mark>` is `@base-mark-background` / `@base-mark-color`; a highlight needs no
    CSS at all.
* **Cards ship FLAT, and both fixes are variables.** The master theme exposes
  `@card-border-radius` (`border-radius/card.less`) and `@card-default-box-shadow`
  (`box-shadow/card.less`), defaulting to `0` and `none` — so a rounded, lifted
  card is two values, not a rule. Roomy cards:
  `@card-large-body-padding-{horizontal,vertical}-l`, behind `panel_padding: large`.
  **The same `when not (@<c>-border-radius = 0)` guard covers the rest of the
  family**, which is the part that costs time: `@button-border-radius`,
  `@label-border-radius`, `@form-border-radius` and the `-small`/`-large` button
  pairs. A square button is an unset variable, never a rule — but it presents as
  "this theme has no radius option". `master/border-radius/` ships one file per
  component, so that directory listing IS the answer to "is there a variable for
  this". Tiles are the one exception: no `tile.less` there, so a tile radius
  really does need `.hook-tile-muted()`.
* **`@border-rounded-border-radius` (5px) is the radius behind the column
  "Round corners" checkbox** — a DIFFERENT variable from your card and tile radii,
  so rounded columns come out visibly tighter than every other panel until you
  pin all three to one token.
* **`@slidenav-*` exists but cannot make a circle.** `@slidenav-background`,
  `@slidenav-border-radius` and `@slidenav-padding-vertical|horizontal` are all
  settable, but the padding pair works against a 14x24 icon, so no combination
  yields width == height. A circular slidenav needs one rule.
* **Check your `@line` token against your muted-background token before using it.**
  They are commonly the same 10% tint — in which case every border on a
  `uk-section-muted` band is invisible and reads as "the border never applied".
  Un-blend the design's line (see section 7) rather than assuming it is the light
  one; a 1px rule that looks grey on screen is often full ink.

* **`@global-secondary-font-family` is the UI ROLE, not "the second brand face".**
  The master theme routes h1-h3 through `@global-primary-*` and h4-h6 through
  `@global-secondary-*` — so setting secondary to a display face to make h4 look
  right is the obvious move, and it is wrong. That variable also feeds **18
  files** under `master/typo/`: button, label, navbar, nav, form, tab, subnav,
  pagination, breadcrumb, dropdown, badge, comment, description-list, text,
  card, article, base, variables. One assignment puts the display face on every
  control on the site — buttons in a 60px-scale serif, nav items, form labels —
  and each of them looks like its own separate bug.

  ```bash
  grep -rl "@global-secondary-font-family" vendor/assets/uikit-themes/master/typo/
  ```

  Keep secondary on the BODY face and re-state the display face on the one or
  two headings that ride it (`@base-h4-font-family`, `@base-h4-font-weight`).
* **Per-heading colour, family, weight, tracking and transform are ALL variables**
  (`master/typo/base.less`): `@base-h1-color` … `@base-h6-color`,
  `@base-h*-font-family`, `@base-h*-font-weight`, `@base-h*-letter-spacing`,
  `@base-h*-text-transform`, each defaulting to the `@base-heading-*` value. A
  design with "H1 green, H2-H4 purple" and a tracked H1 therefore needs **zero
  rules** — set `@base-heading-color` to the common one and override the odd one
  out. The scaffold's commented-out `h1, .uk-h1 { font-weight; letter-spacing }`
  rule is a trap: it suggests these are not settable.
  * **`@article-title-color` is SEPARATE** and defaults to `@global-emphasis-color`.
    On a design whose headings are branded, article titles silently stay ink-grey
    while every other heading is correct — which reads as "the blog layout is
    unstyled" rather than "one variable is unset".
* **Why `references/yootheme-less.md`'s "verify names against the install" is not
  optional: LESS does not error on an assignment nothing reads.**
  `@buton-border-radius: 50px;` compiles clean, exits 0 and does nothing — as
  does any name you half-remembered or that this UIkit version renamed. Nothing
  distinguishes it from a correct line, so a style can be 90% inert and still
  pass every check short of the browser. Same silent class as section 1, and
  `lessc` exit 0 is not evidence. Check every name before the recompile — one
  at a time, or a whole block at once:

  ```bash
  for v in button-border-radius label-background card-default-box-shadow; do
    grep -rqE "^@$v:" vendor/assets/uikit{/src/less,-themes/master}/ || echo "MISSING @$v"
  done
  ```

* Genuinely NOT settable so far: image grayscale (`blend` is a boolean "blend with
  page content", not a mode selector), image max-height, flex-centring in a card.

---

## 6. The Customizer, and recompiling WITHOUT a human

**It is not `customize.php`** — that shows the stock WordPress customizer with no
YOOtheme panel. It is:

```
/wp/wp-admin/admin-ajax.php?action=yootheme&yootheme=customizer
```

Resolve with `wp eval 'echo \YOOtheme\Url::route("customizer");'`.

**A style change CAN be completed end to end without the user.** The Styler has a
first-class **"Recompile style"** button (beside "Download Less") that runs
load → compile → save → refresh — so no fake edit is needed to dirty the
customizer, and `config.less` stays untouched:

1. Log in as a throwaway admin (never repoint the real user's account; note a
   test-suite run that resets that user's password invalidates the session
   cookie).
2. Open the URL above → click **Stijl / Style** → scroll the sidebar → click
   **"Recompile style"**. Allow ~25 s; less.js compiles the whole UIkit tree and
   POSTs base64 CSS to `…&yootheme=theme/style`.
3. Avoid the adjacent "Reset to defaults".
4. **Prove it landed**: md5 `themes/yootheme/css/theme.<n>.css` before/after, then
   grep the minified result for the expected declarations.

> Supersedes the older "you can write the value but a human must open the
> Customizer and save" note in `references/yootheme-site-model.md`.

Verify with a local `lessc` first, and diff compiled-before vs compiled-after to
prove the delta is only what you intended.

---

## 7. Verification discipline (where I actually went wrong)

* **A passing measurement can be a coincidence.** Two CTAs aligning proves nothing
  if both columns' text happens to wrap to the same height. Force the unequal case
  before believing an alignment fix.
* **Cold-cache tools cannot see stale-cache bugs.** Theme static assets may be
  served `cache-control: max-age=315360000`; Playwright/curl always fetch fresh,
  so an edit looks applied while the human still sees the old file. **Version the
  filename** (`logo.<md5-8>.svg`) rather than editing in place.
* **Don't `tail` test output** — it hides `Test Files 1 failed` while showing
  "N passed".
* **Lazy-loading looks like broken images.** Scroll the section into view, wait,
  and check `img.complete` / `naturalWidth` before reporting a failure.
* **`--virtual-time-budget` does not advance the SMIL clock.** Every budget
  returns the identical frame, so an animated SVG looks reassuringly "stable"
  while you measure one frame repeatedly. Use `svg.pauseAnimations()` +
  `setCurrentTime(t)` across the period.
* **If the design lives in Figma and the MCP is reachable, do not measure a
  screenshot at all.** `get_metadata` returns exact node geometry in design units
  and `get_design_context` returns exact radius, shadow, padding and colour — so
  the scale is 1.0 by construction, there is no export to calibrate and no 1px
  rule to un-blend. Prove the read anyway with two independent knowns (a page
  gutter and a column grid that must agree), because that is what catches reading
  the wrong frame. The masking technique below stays correct for a PNG-only
  reference, which is the case it was written for.
* **Measure the design, don't eyeball it.** Colour-masking a design screenshot
  gives exact numbers to build against — and catches things the eye slides over.
  On this build it produced: card inset 7.7% of the container, tool height 75%,
  and a tool rotation of **−5°** (top edge rising to the right) where I had baked
  **+4°** the other way. A coarse ASCII map of the masks (`G`/`L`/`W` per cell)
  is the fastest way to see which region is which before trusting any bbox:

  ```python
  grey  = lambda c: abs(c[0]-234)<7 and abs(c[1]-230)<7 and abs(c[2]-231)<7
  # bbox of a single mask lies when two regions share a colour — map first.
  ```
* Assert on **rendered pixels or computed styles**, not on the fact that a prop
  was written — traps 1.1–1.5 all store fine and render wrong.
* **A class being PRESENT is not the same as being CORRECT, and grep cannot tell
  the difference.** 2026-09-02: I dumped the rendered DOM, saw
  `uk-position-center` on the body column, ticked it off as "the class is there"
  and shipped a page whose body floated over the hero — that class *is*
  `position:absolute; top:50%; left:50%`. One `getBoundingClientRect()` would
  have shown two sections occupying the same y-range. Grepping for class names
  is not verification; it is the same mistake as asserting the prop was written,
  one layer further out.
* **Read ALL of this file, not the first screen.** The bullet above this one
  already said exactly what I got wrong, and I had read to §1.10 and stopped.
  §7 is the section that would have saved the session, and it is at the bottom.

* **Derive a design screenshot's SCALE before measuring anything on it.** It
  varies per export, even within one project and one day (0.669 and 1:1 on the
  same afternoon). Two knowns pin it: the container gutter and the body
  line-pitch — and they must AGREE, or the frame is not the width you assumed.
  Measuring at the wrong scale gets radii, type and gutters all wrong in the same
  direction, which reads as "the design system is off" rather than "the ruler is
  off", and sends you editing tokens that were already right.
* **Un-blend an antialiased 1px line to recover its true colour.** A 1px rule at a
  fractional position paints across two rows; per channel,
  `true = bg + SUM(row - bg)` over the covered rows. This turned what looked like
  a grey hairline into `#35070c` — full ink. Eyedropping a screenshot is
  unreliable in exactly this case, because no pixel ever holds the real value.
* **CDP viewport screenshots go stale after a programmatic scroll.**
  `getBoundingClientRect()` reports the new position while the captured frame is
  still the old one, so you get a blank band and conclude the section did not
  render. Take a FULLPAGE shot and crop by the measured `top + scrollY`. Check
  the canvas first: a fullpage capture can come back 2x wide with 1x-scaled
  content in the top-left — probe a pixel beyond the CSS width before trusting
  any crop arithmetic.
