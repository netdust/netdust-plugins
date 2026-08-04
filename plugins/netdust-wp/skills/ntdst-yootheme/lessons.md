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

## 1. Six traps that silently do the wrong thing

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

---

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

## 4. Layout recipes that need no CSS

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
