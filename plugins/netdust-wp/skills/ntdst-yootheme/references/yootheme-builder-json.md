# YOOtheme Builder Layouts — the JSON grammar and prop vocabulary

The builder's storage format is plain JSON: read a layout, diff two pages, script a
change, or author a section in `scripts/yoo_layout.py`. Grammar and prop vocabulary as
the official demos use it, verified against the parent's element definitions (5.0.43).
`scripts/yoo-lint.php` checks a layout against those definitions — run it before every
write. Where layouts are stored: `yootheme-site-model.md`; real shapes to copy: `sections/`.

---

## The node

Every node is the same shape:

```json
{
  "type": "headline",
  "name": "optional editor label",
  "props":    { "content": "Hello", "title_style": "h3" },
  "children": [ … ],
  "source":   { … }
}
```

* `type` — the element (see catalogue below). Required.
* `props` — everything configurable. All values are strings, booleans or numbers;
  **there is no nesting inside `props`** except a handful of arrays.
* `children` — containers only.
* `source` — dynamic-content binding (see `yootheme-content-binding.md`).
* `name` — the label shown in the builder tree. Cosmetic.

A page root is `{"type":"layout","children":[…],"version":"5.0.32"}`. **A
template's `layout` is the same shape** — `Builder::load()` returns `null` for
anything that isn't an object, so a bare node array is rejected.

### The structural spine

```
layout → section → row → column → element
```

`section` sets the full-bleed band (background, padding, height). `row` is the
UIkit grid. `column` is a grid cell. Elements live in columns.

`fragment` is the fifth structural type: a transparent group inside a column,
used to bind a whole block to a query or a condition, and used as the root of
mega-menu content.

---

## Element catalogue

**51 core element types** ship in `packages/builder/elements/`. Container
elements are marked `▸`; the rest are leaves.

| Group | Elements |
|---|---|
| Structure | ▸`layout` ▸`section` ▸`row` ▸`column` ▸`fragment` |
| Text | `headline` `text` `quotation` `code` `html` `divider` |
| Media | `image` `video` ▸`gallery`+`gallery_item` ▸`slideshow`+`slideshow_item` ▸`map`+`map_item` |
| Cards & lists | ▸`grid`+`grid_item` `panel` ▸`list`+`list_item` ▸`description_list`+`description_list_item` ▸`table`+`table_item` |
| Navigation | ▸`nav`+`nav_item` ▸`subnav`+`subnav_item` ▸`button`+`button_item` `totop` |
| Interaction | ▸`accordion`+`accordion_item` ▸`switcher`+`switcher_item` ▸`popover`+`popover_item` ▸`overlay-slider`+`overlay-slider_item` ▸`panel-slider`+`panel-slider_item` `overlay` `countdown` `alert` `icon` |
| Social | ▸`social`+`social_item` |

Four more packages contribute elements — check these before concluding something
isn't available:

| Package | Elements |
|---|---|
| `builder-wordpress/elements` | `breadcrumbs` `menu` `module` `module_position` `search` |
| `builder-wordpress-source/elements` | `comments` `pagination` |
| `builder-wordpress-woocommerce/elements` | registered as `woo_<name>`: `add_to_cart` `additional_information` `description` `filter` `images` `meta` `notices` `pages` `price` `products` `rating` `related_products` `stock` `tabs` `title` `upsell_products` |
| `builder-newsletter/elements` | `newsletter` |

That last group shows the registration convention — `$builder->addType("woo_{$element}", …/elements/{$element}/element.php)`. Custom elements register the
same way from a `builder/bootstrap.php`; see SKILL.md.

**The `_item` pattern is universal.** A container holds `<container>_item`
children; the container carries all the *styling* props and the items carry only
*content*. `grid` has ~30 props; `grid_item` typically has two. When binding
dynamic content you bind the **item** and repeat it (see the `#parent` pattern).

---

## The prop systems

These recur across nearly every element. Learn them once.

### Spacing

| Prop | Where | Values |
|---|---|---|
| `margin_top` / `margin_bottom` | every element & row | `remove` · `small` · `default` · `medium` · `large` · `xlarge` |
| `padding_top` / `padding_bottom` | section | `none` · `small` · `default` · `large` · `xlarge` |
| `column_gap` / `row_gap` | row, grid | `collapse` · `small` · `medium` · `large` |

`remove`/`none` are explicit values, not omissions — the demos set them
constantly to butt sections together.

### Widths and the responsive grid

**Column widths are per-breakpoint props**, rendered straight to UIkit classes
(`packages/builder/elements/column/templates/template.php`):

```
width_default → uk-width-{v}        (all sizes)
width_small   → uk-width-{v}@s      (≥ 640px)
width_medium  → uk-width-{v}@m      (≥ 960px)
width_large   → uk-width-{v}@l      (≥ 1200px)
width_xlarge  → uk-width-{v}@xl     (≥ 1600px)
```

Values are UIkit fractions — `1-1`, `1-2`, `1-3`, `2-3`, `1-4`, `3-4`, `1-5`,
`2-5` … — plus `auto` (shrink to content) and `expand` (fill the rest). If none
is set the column gets `uk-width-1-1`. An unset breakpoint inherits the next
smaller one.

> **⚠ The row `layout` prop does not size anything.** `"layout": "1-2,1-2"` (and
> the two-group form `"1-4,1-4,1-4,1-4|1-2,1-2,1-2,1-2"`) is the *preset picker's*
> record of which grid was chosen. The row template only uses it as a boolean:
> `uk-child-width-1-1 {@!layout}`. **The authoritative widths are the column
> props.** Changing `layout` in the JSON without changing every child column
> changes nothing on screen — and in the builder UI, changing the layout preset
> *resets* the customised column widths. Edit the columns.

`section.width` / `row.width` control the container: `` (none) · `default` ·
`xsmall` · `small` · `large` · `xlarge` · `expand`.

### Visibility and order

* `visibility`: `s` · `m` · `l` · `xl` (show **from** that breakpoint) or
  `hidden-s` · `hidden-m` · `hidden-l` · `hidden-xl` (hide from it). Pair them to swap
  a desktop and a mobile variant of the same block.
* `column.order_first`: `xs` · `s` · `m` · `l` — pull a column first from that
  breakpoint up, leaving natural order below. This is the idiomatic
  "image above text on mobile, beside it on desktop".

### Section media and background

```json
{"type":"section","props":{
  "image": "wp-content/uploads/yootheme/demo/home-hero-bg.jpg",
  "image_size": "cover", "image_position": "center-center", "image_width": 2560,
  "image_effect": "parallax", "image_parallax_bgy": "40vh",
  "media_overlay": "rgba(0, 0, 0, 0.75)",
  "media_overlay_parallax_opacity": "0,1",
  "video": "…/home-hero-bg.mp4",
  "height": "viewport", "height_viewport": "80", "height_viewport_offset": true,
  "text_color": "light", "header_transparent": true, "sticky": "cover"
}}
```

* Media paths are **site-root-relative, no leading slash** —
  `wp-content/uploads/yootheme/demo/…`. Not absolute URLs, not IDs.
* `image_width`/`image_height` drive YOOtheme's own image resizing; set them or
  you ship the original.
* `image_effect`: `parallax` · `fixed` · `` .
* `height`: `viewport` · `expand` · `page`; `height_viewport` is a percentage
  ("80"), `height_viewport_offset` subtracts the header.
* `header_transparent` pairs with `config.header.transparent` to let a hero sit
  under the header. `header_transparent_noplaceholder` removes the reserved space.
* `sticky`: `cover` · `reveal` — the section sticks as the next one scrolls over.
* `style`: `default` · `muted` · `primary` · `secondary` · `` — these are the
  UIkit section styles your LESS defines (see `yootheme-less.md`).

`column` accepts most of the same media props plus `style`
(`tile-default` · `tile-muted` · `card-default` · `card-primary` …) to turn a
column into a card.

### Parallax and scroll animation

The biggest single source of "premium feel" in these demos, and entirely
declarative. Set `animation: "parallax"`, then:

| Prop | Meaning | Real values |
|---|---|---|
| `parallax_y` / `parallax_x` | translate over the scroll range | `"100,-100"`, `"15vh,-15vh"`, `"0,-7vw"` |
| `parallax_opacity` | fade | `"1,0"`, `"0 0%,0 20%,1 40%"` |
| `parallax_blur`, `parallax_scale` | px / factor | `"0 70%,100"`, `"2,100%"` |
| `parallax_start` / `parallax_end` | when the range begins/ends | `"-100vh"`, `"50vh + 50%"`, `"100%+10vh"` |
| `parallax_target` | which ancestor's scroll drives it | `"!.uk-section"`, `"!.tm-grid-expand"` |
| `parallax_breakpoint` | enable from | `s` · `m` · `l` |

Syntax: `"from,to"`, or keyframes as `"value position%"` pairs. `parallax_target`
uses UIkit's selector syntax where `!` means "closest ancestor matching".

`animation` also takes plain entrance values on sections —
`fade`, `slide-bottom-small`, `slide-left-small`.

### Positioning

`position: absolute|relative` + `position_top/right/bottom/left`
(`"50%"`, `"-15vw"`, `"190"`) + `position_z_index`. Used to overlap decorative
images across section boundaries. `blend: true` applies mix-blend-mode.

Sticky columns: `position_sticky: column|row|section` plus
`position_sticky_offset` — which accepts **calc-style expressions**
(`"50vh - 50%"`, `"100vh - 150%"`), not just pixels.

### Per-element custom CSS

Any element takes a `css` prop, scoped to that element:

```json
"css": "@media(min-width: 1200px) {\n    .el-element { margin-top: 100px; }\n}"
```

Selectors are `.el-element` (the wrapper), plus `.el-row`, `.el-column`, `.el-image`,
`.el-title`, `.el-content`. **Reach for it last** — it is invisible to the style system.

### Anchors

`id` on a section or row emits the DOM id — `"id": "philosophy"` — which is how
in-page nav links (`link: "#philosophy"`) work.

---

## Card-family props (`grid`, `panel`, `list`, sliders)

The card elements share one vocabulary. Every part is independently toggled and
styled on the **container**:

```
show_image / show_title / show_meta / show_content / show_link / show_video / show_hover_image
title_element (h2|h3|div)   title_style (h1…h6, heading-small…heading-xlarge)   title_align   title_hover_style
meta_element  meta_style (text-meta|h5|…)  meta_align (above-title|below-title)  meta_margin
image_align (top|left|right|bottom)  image_width  image_grid_width  image_grid_breakpoint  image_svg_color
link_style (default|text|primary|link-text)  link_text ("Read more")
grid_default / grid_small / grid_medium / grid_large  ← columns per breakpoint
grid_column_gap / grid_row_gap / grid_divider
filter_style / filter_position / filter_align / filter_all  ← the built-in filter bar
item_animation
```

`grid_default: "1"`, `grid_medium: "4"` means one column on mobile, four from
960px. `grid_*: "auto"` sizes to content.

This is why a dynamic listing needs almost no markup work: bind `grid_item` to a
query, then dress the whole listing from the `grid`'s props.

---

## Typography values

`title_style` and `text_style` take the theme's type scale, not raw sizes:

* Headings: `h1` … `h6`
* Display: `heading-small` · `heading-medium` · `heading-large` · `heading-xlarge` · `heading-2xlarge` · `heading-3xlarge`
* Body: `lead` · `large` · `small` · `default` · `meta`

`title_element` is chosen **independently** of `title_style` — `{"title_element":"div",
"title_style":"heading-2xlarge"}` keeps `h1`/`h2` for document structure while any
element can *look* like a heading. Keep that discipline.

Colours: `title_color` / `text_color` take `primary` · `secondary` · `muted` ·
`emphasis` · `background` · `light` · `dark` — semantic slots your LESS defines,
never hex.

`maxwidth` (`small` … `2xlarge`) + `block_align` (`center` · `right`) constrain
measure — the standard way to keep body copy readable in a wide section.

---

## A real section to copy

`sections/` holds six shapes lifted from a shipped site and linted clean — hero, page
header, logo marquee, FAQ, CPT card grid, CTA band. Copy one, swap content and
bindings, **keep every prop**: `image_position: center-center` on every column,
`position_sticky_breakpoint: "m"`, `image_align`/`image_margin` on headlines are the
builder's own defaults. Strip them and a builder save puts them back, churning the diff.

## Reading element definitions

When a prop is unclear, the element defines it:

```
packages/builder/elements/<type>/element.php        fields, defaults, templates
packages/builder/elements/<type>/templates/*.php    how props become markup
packages/builder/elements/<type>/updates.php        migrations between versions
```

`element.php` `fields` entries carry `label`, `type` (`select`, `checkbox`,
`image`, `video`, …), `options`, `show`/`enable` (conditional visibility), and
`source: true` (the prop can be dynamically bound).

Templates use YOOtheme's attribute mini-language:

```php
'uk-container-{width}{@width: xsmall|small|large|xlarge|expand}'
```

`{prop}` interpolates; `{@prop}` includes the class only if `prop` is truthy;
`{@prop: a|b}` only if the value is in the list; `{@!prop}` negates. Useful to
read, and required if you write a custom element.

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Change a row's `layout` string to resize columns | Set `width_*` on each column; `layout` is only the preset marker |
| Hard-code pixel widths in `css` | `width_small/medium/large` + `maxwidth` |
| Use `h2` markup just to get a big size | `title_element: "div"` + `title_style: "heading-large"` |
| Put hex colours in `title_color` | Semantic slots (`primary`, `muted`, `emphasis`) defined in LESS |
| Write absolute URLs or attachment IDs in `image` | Site-root-relative path, `wp-content/uploads/…` |
| Reach for the `css` prop first | Exhaust props; `css` is invisible to the style system |
| Strip "redundant" default props when hand-editing | The builder rewrites them; you'll churn every diff |
| Duplicate a block to make a mobile variant blindly | `visibility` + `hidden-*` is the idiom — but prefer one block that reflows |
| Bind the container when you meant the repeat | Style on the container, bind the `_item` |
