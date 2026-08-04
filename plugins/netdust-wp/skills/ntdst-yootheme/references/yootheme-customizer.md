# The YOOtheme Customizer — every panel and its vocabulary

The full setting surface of a YOOtheme Pro site, extracted from the parent
theme's own panel definitions (`packages/*/config/customizer.php`) rather than
observed values — so these are complete enumerations, not "what the demos
happened to use".

All of it serialises into `theme_mods_<active-stylesheet>` → `config` (see
`yootheme-site-model.md`). **Field keys below are the literal JSON paths in that
config**, so `site.boxed.header_transparent` is
`config["site"]["boxed"]["header_transparent"]`.

To regenerate this table against an install:

```bash
php -r '$c = include "packages/theme/config/customizer.php";
        foreach ($c["panels"] as $id => $p) { echo "$id: ", $p["title"] ?? "", "\n"; }'
```

---

## The five sections

The Customizer's own top-level nav (`theme-wordpress/config/customizer.php`):

| Section | Panels |
|---|---|
| **Layout** | Site · Header · Mobile · Top · Sidebar · Bottom · Footer |
| **Styler** | Style selection + the LESS variable editor (`yootheme-less.md`) |
| **Builder Pages** | the page/layout list |
| **Builder Templates** | the template list — drag order **is** the routing priority |
| **Settings** | Favicon · CSS · Scripts · External Services · API Key · Advanced · Image Quality · System Check |

---

## Site

Logo, page frame, toolbar, breadcrumbs, site background.

| Key | Type | Values |
|---|---|---|
| `logo.text` | text | used as `alt` when an image is set |
| `logo.image` / `logo.image_inverse` / `logo.image_mobile` / `logo.image_mobile_inverse` / `logo.image_dialog` | image | inverse variants auto-swap on dark backgrounds |
| `logo.image_width` / `_height` (+ `_mobile_*`) | number | one value preserves proportions; hi-res auto-generated |
| `logo.image_svg_inline` | checkbox | inject the SVG so it inherits `currentColor` |
| `site.layout` | select | `full` · `boxed` |
| `site.boxed.alignment` · `.margin_top` · `.margin_bottom` | checkbox | boxed frame |
| `site.boxed.header_outside` · `.header_transparent` · `.header_text_color` | checkbox/select | `''` · `light` · `dark` |
| `site.boxed.media` | image | the backdrop behind a boxed site |
| `site.toolbar_width` | select | `default` · `small` · `large` · `xlarge` · `expand` |
| `site.toolbar_center` · `site.toolbar_transparent` | checkbox | |
| `site.breadcrumbs` · `_show_current` · `_show_home` · `_home_text` | checkbox/text | |
| `site.main_section.height` | checkbox | force main to fill the viewport |

**Site background** (panel *Image*, keys still under `site.`): `image_width`,
`image_height`, `image_focal_point`, `image_size` (`''`·`cover`·`contain`),
`image_position` (9-way `top-left` … `bottom-right`), `image_effect`
(`''`·`parallax`·`fixed`), `image_parallax_bgx`/`bgy`/`easing`/`breakpoint`,
`image_visibility` (`''`·`s`·`m`·`l`·`xl`), `media_background`,
`media_blend_mode` (`multiply`·`screen`·`overlay`·`darken`·`lighten`·
`color-dodge`·`color-burn`·`hard-light`…), `media_overlay`.

---

## Header

**12 layouts** (`header.layout`):

```
horizontal-left   horizontal-center   horizontal-right   horizontal-justify   horizontal-center-logo
stacked-center-a  stacked-center-b    stacked-center-c
stacked-center-split-a   stacked-center-split-b   stacked-left   stacked-justify
```

`header.split_index` appears for `stacked-center-split-*` / `stacked-center-c`;
`header.push_index` for `stacked-left`. Both are "how many items before the
break", `''`–`10`.

| Key | Values |
|---|---|
| `header.width` | `default` · `small` · `large` · `xlarge` · `expand` |
| `header.transparent` | let a hero run under the header |
| `header.transparent_color_separately` | colour navbar parts independently |
| `header.blend` | mix-blend the header with page content |
| `header.logo_padding_remove` | |
| `navbar.sticky` | `0` off · `1` · `2` (two sticky behaviours) |
| `navbar.style` | `''` · `primary` |
| `navbar.dropdown_align` | `left` · `right` · `center` |
| `navbar.dropdown_target` · `dropbar` · `dropdown_preserve_color` · `parent_icon` · `dropdown_click` | checkboxes |

**Dialog** — the panel a toggle opens. **6 layouts** (`dialog.layout`):
`dropbar-top` · `dropbar-center` · `offcanvas-top` · `offcanvas-center` ·
`modal-top` · `modal-center`. A sub-panel (`dialog._dropbar` / `._offcanvas` /
`._modal`) appears to match. Plus `dialog.toggle`
(`navbar:start|end`, `header:start|end`), `dialog.toggle_text`,
`dialog.text_center`, `dialog.push_index`.

**Search** — `header.search` places it (`''` or `<position>:<start|end>` across
navbar/header/dialog/toolbar). **5 layouts** (`header.search_layout`):
`input-dropdown` · `dropdown` · `input-dropbar` · `dropbar` · `modal`, each with
its own sub-panel. Plus `search_expand`, `search_prevent_submit`,
`search_icon` (`''`·`left`·`right`).

**Social** — `header.social` (same position vocabulary), `social_items`
(a list of `{link}`), `social_target`, `social_style` (render as buttons),
`social_image_svg_inline`, `social_width`, `social_gap`
(`collapse`·`small`·`medium`·`large`·`''`).

---

## Mobile

> **`mobile.breakpoint` is the master switch.** Every other mobile field is
> gated `[show: mobile.breakpoint]`. Empty → **no separate mobile header
> exists** and the desktop one is used at all sizes. Values: `''` · `s` · `m` · `l`.

Below that breakpoint the site uses `*-mobile` positions and a parallel config:

* `mobile.header.layout` — **5 layouts**: `horizontal-left` · `horizontal-center` ·
  `horizontal-right` · `horizontal-justify` · `horizontal-center-logo`
* `mobile.navbar.sticky`, `mobile.header.transparent`,
  `transparent_color_separately`, `blend`, `logo_padding_remove`
* `mobile.dialog.layout` — the same 6 as desktop, `mobile.dialog.toggle`
  (`navbar-mobile:start|end`, `header-mobile:start|end`),
  `toggle_text`, `text_center`, `push_index`, and **`mobile.dialog.close`**
  (show a close button — only for `offcanvas*` / `modal*`)
* `mobile.header.search*` and `mobile.header.social*` — same vocabulary as
  desktop, scoped to the mobile positions

**The trap:** these are independent settings, not overrides. Changing the desktop
header does nothing to mobile. Set both, always.

---

## Top and Bottom

Two widget bands wrapping the main content — `top` renders above, `bottom`
below. Both take the **same vocabulary**, which is deliberately the builder
`section` vocabulary (see `yootheme-builder-json.md`):

| Key | Values |
|---|---|
| `<pos>.style` | `''` · `default` · `muted` · `primary` · `secondary` |
| `<pos>.preserve_color` | keep text colour despite the style |
| `<pos>.overlap` | overlap the following section |
| `<pos>.background_color` · `.image` · `.video` | `image` and `video` are mutually exclusive |
| `<pos>.text_color` | `''` · `light` · `dark` |
| `<pos>.width` | `default` · `xsmall` · `small` · `large` · `xlarge` · `expand` · `''` |
| `<pos>.height` | `''` · `viewport` · `section` · `page` (+ a numeric companion) |
| `<pos>.vertical_align` | `''` · `middle` · `bottom` |
| `<pos>.padding` | `''` · `xsmall` · `small` · `large` · `xlarge` · `none` |
| `<pos>.padding_remove_top` / `_bottom` | |
| `<pos>.column_gap` / `.row_gap` | `collapse` · `small` · `medium` · `large` · `''` |
| `<pos>.divider` · `.match` | dividers between widgets; `match` renders them as equal-height panels |
| `<pos>.breakpoint` | `s` · `m` · `l` · `xl` — when widgets go side-by-side |

`top` additionally has `height_offset_top`, `header_transparent`,
`header_transparent_noplaceholder` and `header_transparent_text_color` — because
it is the band that can sit under a transparent header.

**These panels style the band; the content is widgets** placed in the `top` /
`bottom` positions — including Builder widgets. FC Greenfield's whole footer is
a Builder widget in `bottom`.

---

## Sidebar

| Key | Values |
|---|---|
| `main_sidebar.width` | `1-5` · `1-4` · `1-3` · `2-5` · `1-2` |
| `main_sidebar.breakpoint` | `s` · `m` · `l` |
| `main_sidebar.first` | put the sidebar before the content |
| `main_sidebar.gutter` | `''` · `small` · `large` · `collapse` |
| `main_sidebar.divider` | |

(`sidebar.min_width` also exists, set outside this panel.)

---

## Post and Blog — the non-builder fallbacks

These render posts and archives **when no builder template matches**. On a
template-driven site most of them never fire — but they are what you see before
you build the templates, and a stray archive with no template falls back here.

**Post** (`config.post.*`): `width`, `padding`, `padding_remove`,
`content_width` (`''`·`xsmall`·`small`), `image_align` (`top`·`between`),
`image_margin` / `title_margin` / `meta_margin` / `content_margin`
(`remove`·`xsmall`·`small`·`default`·`medium`·`large`·`xlarge`),
`image_width` / `image_height`, `header_align`, `meta_align` (`top`·`bottom`),
`meta_style` (`list`·`sentence`), `content_dropcap`, `navigation`,
and the meta toggles `date` · `author` · `categories` · `tags`.

**Blog** (`config.blog.*`): everything above plus
`column` (`1`–`4`), `grid_column_gap` / `grid_row_gap`, `grid_breakpoint`,
`grid_masonry`, `grid_parallax`, `title_style` (`''`·`h1`–`h4`),
`content_excerpt`, `content_length`, `content_align`,
`button_style` (`default`·`primary`·`secondary`·`danger`·`text`),
`button_margin`, `navigation` (`pagination` · `previous/next`),
and toggles `date` · `author` · `categories` · `comments` · `content` · `tags` ·
`button` · `category_title`.

---

## Settings

| Panel | Keys |
|---|---|
| **Favicon** | `favicon` (PNG), `favicon_svg`, `touchicon` |
| **CSS** | `custom_less` — raw LESS appended to the style. Empty in all six demos |
| **Scripts** | `scripts[]` — typed entries, e.g. `{"type":"script-maps-google-maps","options":{"apiKey":"…"}}` or `script-maps-openstreetmap`; `script-custom` holds arbitrary head/body code |
| **External Services** | `mailchimp_api`, `cmonitor_api` — feed the `newsletter` element |
| **API Key** | `yootheme_apikey` — enables the AI/asset services |
| **Advanced** | `webp`, `avif`, `image_urls`, `highlight` (`''`·`github`·`monokai`), `clear_cache` |
| **Image Quality** | `image_quality_jpg`, `image_quality_png_webp`, `image_quality_jpg_webp`, `image_quality_png_avif`, `image_quality_jpg_avif` |
| **System Check / About** | diagnostics, no stored values |

Also in `config` but set elsewhere: `media_folder` (default `yootheme` — the
uploads subfolder builder images go to), `bootstrap`, `fontawesome`,
`disable_wpautop`, `consent` (cookie-consent options, `theme-consent` package),
`version`, `style`, `less`, `custom`.

> `disable_wpautop: true` in every demo. YOOtheme emits its own markup;
> leaving `wpautop` on injects stray `<p>` tags into builder output.

---

## Conditional fields — reading `show`

Panel fields carry a `show` expression evaluated against the live config:

```php
'show' => "mobile.breakpoint && \$match(mobile.dialog.layout, '^offcanvas|^modal')"
'show' => "site.layout == 'boxed' && site.boxed.media"
```

Useful when a setting "isn't there" — it usually exists but its `show`
predicate is false. Grep the panel definition for the key to find out what
unlocks it.

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Style the mobile header with CSS overrides | It's a separate config — set `mobile.*`; `mobile.breakpoint` enables it at all |
| Tune `post.*` / `blog.*` on a template-driven site | Build an `archive-`/`single-` template; these are the fallback path |
| Put site-wide CSS in a builder element's `css` prop | Settings → CSS (`custom_less`) or the style's LESS |
| Add a tracking script via a plugin or `wp_head` | Settings → Scripts (`script-custom`) |
| Treat `top`/`bottom` as content areas you edit directly | They're *styled bands*; the content is widgets placed in those positions |
| Turn `wpautop` back on to fix spacing | It breaks builder markup — fix the spacing props |
| Assume a missing setting doesn't exist | Check its `show` expression in the panel definition |
