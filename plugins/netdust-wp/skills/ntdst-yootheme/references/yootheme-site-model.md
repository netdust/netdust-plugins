# YOOtheme Site Model — where a site actually lives

Everything a YOOtheme Pro site *is* — pages, menus, header, footer, templates,
style choice — lives in **four options in the database**, not in theme files.
This file maps them. Verified against six official YOOtheme demo packages
(Glowbar, Kojiro, Quantum Flares, FC Greenfield, Oakville, Woolberry — theme
5.0.32, Woolberry 5.0.37), against the parent theme's own source (5.0.43), and
against live child-theme installs (josworld 5.0.38 + Polylang, edushare 5.0.43) for
the write path. The 5.0.38 → 5.0.43 diff touched 15 PHP files and no store, no
position and no element vocabulary beyond `button_item`'s `lightbox` condition.

Read this before: cloning/inspecting a demo, scripting site setup, debugging
"where is that footer coming from", or migrating a YOOtheme site.

---

## The four stores

| What | Where | Format |
|---|---|---|
| **Page layouts** | `wp_posts.post_content` of each page/post | HTML, then the layout JSON in a trailing HTML comment |
| **Dynamic-content templates** (single/archive/taxonomy/404/search) | `wp_options` → `yootheme` | JSON: `{"library":{},"templates":{…}}` |
| **Site config** — header, footer, menu positions, style, blog/post defaults | `wp_options` → `theme_mods_<active-stylesheet>` | PHP-serialized array; its `config` key is a **JSON string** |
| **Builder widgets** — arbitrary layouts dropped into header/dialog/bottom positions | `wp_options` → `widget_builderwidget` + `sidebars_widgets` | PHP-serialized; each widget's `content` is a builder layout |

There is no `yootheme_*` postmeta. A builder layout can therefore live in **four**
places — a post, a template, `config.footer.content`, or a builder widget — and
all four use the identical node grammar.

### 1. Page layouts — `post_content`

`packages/builder-wordpress/src/PageController.php` writes:

```php
$data['post_content'] = wp_slash("{$introtext}\n<!--more-->\n<!-- {$fulltext} -->");
```

* `$introtext` — the builder rendered in `context: 'content'`. **Plain HTML, for
  search/excerpt/RSS only.** It is *output*, never the source of truth. Editing it
  by hand changes nothing on screen.
* `$fulltext` — the layout JSON, `JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE`.

Detection (`packages/builder-wordpress/src/PostHelper.php`):

```php
const PATTERN = '/<!--\s?(\{.*})\s?-->/';
```

Greedy `.*` up to the last `}` — so the JSON must be the **last** comment in the
content. A page with no such comment simply is not a builder page (the demos'
"Blog" page has empty `post_content`; it renders from the archive template).

> **Consequence for search & replace.** A URL migration that rewrites
> `post_content` touches the layout JSON too. That is usually what you want, but
> the JSON is escaped — a naive `sed` over `wp-content/uploads` will miss
> `wp-content\/uploads` in dumps that escape slashes. Use `wp search-replace`,
> which handles serialized data, and verify a page still opens in the builder.

### 2. Templates — the `yootheme` option

```json
{
  "library": {},
  "templates": {
    "8Ka5T8vQ": { "type": "single-post", "name": "Post 2 Columns",
                  "query": {"category_include_children":"only","terms":[20]},
                  "layout": [ …builder nodes… ],
                  "status": "", "params": {"posts_per_page": 14} }
  }
}
```

* Key = an 8-char template id. `library` is the saved-layouts library (empty in
  every shipped demo).
* `layout` is a **`{"type":"layout","children":[…],"version":"…"}` object** —
  the *same* root shape as a page's. `Builder::load()` enforces this: it
  `json_decode`s and returns `null` unless the result `is_object()`, so a bare
  node array is rejected outright.
* The rest of the template (`type`, `name`, `query`, `status`, `params`) is the
  routing envelope around it. `id` and `url` are **not** stored — `saveTemplate`
  strips them (`Arr::omit($template, ['id','url'])`).

See `yootheme-content-binding.md` for the routing rules (types, `query`
matching, ordering, `params`, `status`).

### 3. Site config — `theme_mods_<active-stylesheet>`

```
theme_mods_<stylesheet> (PHP-serialized) = {
  0                  => false,              // WP's own placeholder, ignore
  config             => "<JSON string>",    // ← everything YOOtheme
  nav_menu_locations => ['navbar'=>33, 'dialog-mobile'=>34, …]
}
```

> ⚠ **The option name follows the ACTIVE theme, not the parent.** The demos run
> the parent standalone, so theirs is `theme_mods_yootheme` — but on a normal
> project with a child theme it is `theme_mods_<child-slug>`. Verified on a live
> child-theme install: `get_stylesheet()` → `josworld`, config in
> `theme_mods_josworld` (`theme_mods_yootheme` also exists, stale and unused).
> **Always go through `get_theme_mod()`**, which resolves the active stylesheet
> for you, rather than naming the option.

To read it:

```bash
wp eval 'echo get_theme_mod("config");' | jq .      # ← theme-agnostic, prefer this
wp option get theme_mods_$(wp eval 'echo get_stylesheet();') --format=json
```

> ⚠ **On a Polylang/WPML site, `get_theme_mod("nav_menu_locations")` is a
> FILTERED view.** It returns language variants (`navbar#nl`, `footer___en`) and
> zero-valued positions that are **not in the stored option**. When debugging an
> assignment, read the raw option:
> `wp eval 'echo json_encode(get_option("theme_mods_<slug>")["nav_menu_locations"]);'`
> Comparing filtered reads before and after a write will show no change even
> when the stored value changed.

---

## The `config` map

Top-level keys observed in every demo. **This is the index — for the complete
field vocabulary of each panel (all 12 header layouts, the mobile gate, Top/Bottom,
Sidebar, Post/Blog, Settings) see `yootheme-customizer.md`.**

| Key | Holds |
|---|---|
| `style` | the style id — a `less/theme.<id>.less` filename (see `yootheme-less.md`) |
| `less` / `custom_less` | Customizer variable overrides / raw LESS. **Empty in all six demos** — shipped styles are used unmodified |
| `logo` | `text`, `image`, `image_inverse`, `image_mobile`, `image_width`, `image_svg_inline` |
| `site` | layout (`full`/`boxed`), padding, breadcrumbs, `main_section.height` |
| `header` | desktop header — see below |
| `navbar` | `sticky` (1\|2), `dropbar`, `dropdown_align`, `dropdown_boundary`, `style` |
| `dialog` | the dropdown/offcanvas panel that menus open into |
| `mobile` | `breakpoint` + a **parallel** `header` / `navbar` / `dialog` / `search` config |
| `menu` | `positions` (per-position rendering) + `items` (per-menu-item settings) |
| `top` / `bottom` | the two widget-ish sections above/below main content |
| `main_sidebar`, `sidebar` | sidebar width/breakpoint/divider |
| `footer` | `{"content": <builder layout>, "config": null}` |
| `post` / `blog` | single-post and archive rendering defaults |
| `scripts` | e.g. `[{"type":"script-maps-google-maps","options":{"apiKey":""}}]` or `script-maps-openstreetmap` |
| `webp`, `bootstrap`, `fontawesome`, `disable_wpautop`, `media_folder`, `highlight`, `consent`, `version`, `yootheme_apikey` | misc toggles |

### Header

```json
"header": { "layout": "horizontal-right", "width": "expand",
            "transparent": true, "search": "header:start", "social": "header:end" }
```

* `layout` — **12 options**; the demos use five of them. Full list plus the
  `split_index` / `push_index` companions: `yootheme-customizer.md`.
* **Element placement uses `"<position>:<start|end>"` strings.** Positions are
  `toolbar`, `header`, `navbar`, `header-mobile`, `navbar-mobile`. So
  `"social": "header:end"` puts social icons at the end of the header row, and
  `"toggle": "navbar-mobile:end"` puts the burger at the end of the mobile navbar.
* `transparent: true` lets a section overlap the header — paired with the section
  prop `header_transparent`.
* Search: `search_layout` (`input-dropdown` / `input-dropbar` / `dropbar`),
  `search_icon`, `search_dropdown.stretch`, `search_expand`.
* `mobile.header` mirrors these keys independently. **Mobile is a separate
  configuration, not a media query** — expect to set both.

### Footer — usually a builder layout

```json
"footer": { "content": { "type": "layout", "children": [ …sections… ] }, "config": null }
```

`config.footer.content` is a **full builder tree**, same grammar as a page (see
`yootheme-builder-json.md`), edited in Customizer → Footer. Five of the six demos
use it. It can bind dynamic content like any layout — Glowbar's footer nav pulls
a WP menu via the `customMenuItems` source.

**But it is not the only way.** FC Greenfield has `footer.content: null` and puts
its footer in a **Builder widget** in the `bottom` position instead (see below).
When hunting for a footer, check both.

Either way: **not a widget-free `footer.php`, and not a classic widget area you
fill with text widgets.** Copying a footer between sites = copying a JSON subtree.

---

## Positions — the one idea behind headers, menus and chrome

Everything outside the main content is assembled from **named positions**, listed
authoritatively in the parent's `config.php`:

**Menu positions** (a WP nav menu can be assigned here) — 8:

```
toolbar-left  toolbar-right  navbar  header  dialog
navbar-mobile  header-mobile  dialog-mobile
```

**Widget positions** (any widget, including a Builder widget) — 19:

```
toolbar-left  toolbar-right  logo  navbar  header  dialog
logo-mobile  navbar-mobile  header-mobile  dialog-mobile
top  sidebar  bottom
builder-1 … builder-6          ← free-form, for reusable blocks
```

Note the mobile duplicates. **Mobile is a separate set of positions with a
separate config, not a media query.** Set both.

`dialog` / `dialog-mobile` are the panel a menu toggle opens into — its shape is
`config.dialog.layout`: `dropbar-top` · `dropbar-center` · `offcanvas-top` ·
`offcanvas-center`.

### Five ways to get something into a header

This is the question the demos answer most clearly. All five appear across them.

| # | Mechanism | Where it lives | Use for |
|---|---|---|---|
| 1 | **Built-in items** placed by config string | `config.header.*`, `config.mobile.header.*` | logo, search, social, the dialog toggle |
| 2 | **A WP nav menu** on a menu position | `nav_menu_locations` + `config.menu.positions.<pos>` | the actual navigation |
| 3 | **Per-item mega menu** | `config.menu.items.<id>.content` | a rich dropdown |
| 4 | **A Builder widget** in a widget position | `widget_builderwidget` + `sidebars_widgets` | a CTA button, contact block, membership panel — *anything* |
| 5 | **The `menu` builder element** | inside any layout | a menu rendered in a page, footer or mega menu |

**1 — built-in items** use `"<position>:<start|end>"` strings:

```json
"header":  { "layout": "horizontal-right", "search": "header:start",
             "social": "header:end", "transparent": true },
"dialog":  { "toggle": "header:end", "layout": "dropbar-top" },
"mobile":  { "dialog": { "toggle": "navbar-mobile:end" } }
```

`header.layout` has **12 values** — five `horizontal-*` and seven `stacked-*`
(`split_index` / `push_index` set the break point in the stacked ones). The
dialog has 6, search has 5. Complete enumerations in `yootheme-customizer.md`.

⚠ **`config.mobile.breakpoint` is the master switch for the whole mobile
config.** Empty means there is no separate mobile header at all — the desktop
one is used at every width, and every `mobile.*` setting is inert.

**2 — menu assignment and rendering** are two separate keys:

```json
"_nav_menu_locations": { "navbar": 135, "header": 137, "dialog-mobile": 136 }
"menu": { "positions": {
    "navbar":        { "menu": 135, "style": "default", "image_svg_inline": true },
    "header":        { "menu": 137, "image_height": "20", "image_align": "center" },
    "dialog-mobile": { "menu": 136, "type": "nav", "divider": false, "image_align": "top" }
}}
```

**`menu.positions.<pos>.menu` is the source of truth; `nav_menu_locations` is
derived from it on save** by `theme-wordpress-menus/src/Listener/SaveMenuLocations.php`:

```php
foreach ($config['menu']['positions'] ?? [] as $name => $position) {
    if (!empty($position['menu'])) { $locations[$name] = $position['menu']; }
}
set_theme_mod('nav_menu_locations', $locations);
```

(Skipped entirely when WPML is active.) So they always *look* duplicated in a
dump — but if you write config directly, write `menu.positions[].menu` and let
the save event derive the other. See "Writing settings" below.

`type` (`nav` / `accordion` / ``) controls how a mobile menu expands.

**3 — mega menus** are `config.menu.items.<menu_item_id>`:

| Key | Effect |
|---|---|
| `content` | **a builder `fragment`** → the mega-menu body |
| `dropdown` | `{columns, stretch: "navbar", size, width, align, padding_remove_*}` |
| `image` / `image_only` | icon beside (or instead of) the label |
| `language` | `{dropdown, full_name, show_active}` — Polylang switcher item |
| `woocommerce_cart_quantity` | cart badge on a menu item |
| `justify`, `icon` | layout tweaks |

A mega menu is **not a special object** — it is the same builder grammar as a
page, stored on the menu item. Woolberry and FC Greenfield both do this.

**4 — Builder widgets are how the demos put arbitrary content in the chrome.**
Every one of the six uses them:

```
option sidebars_widgets      { "navbar": ["builderwidget-5"], "header-mobile": ["builderwidget-4"],
                               "dialog-mobile": ["builderwidget-3"], "bottom": ["builderwidget-2"] }
option widget_builderwidget  { "5": { "title": "Navbar Membership", "content": <builder layout> }, … }
```

Observed titles tell the story: *Navbar Membership*, *Header Reservation*,
*Dialog Menu*, *Dialog Mobile Contact*, *Dialog Mobile Collections*, *Footer*.
So: a booking button in the header, a contact block in the mobile panel, a
promo grid in the dropdown — all builder layouts, no PHP.

A builder widget entry may also carry `filter`, `visual` and `conditions` keys —
per-widget display conditions.

**5 — the `menu` element** (`packages/builder-wordpress/elements/menu`, title
"Menu") renders a WP menu — or a taxonomy rendered as a menu — inside any
layout, with `menu_base_item` to pin it to a fixed branch instead of following
the current page. Its siblings in that package: `module_position` ("Widget
Area", drops a widget position into a layout — this is what `builder-1…6` are
for), `search`, `breadcrumbs`, `module`.

### The three header architectures in the demos

Read across all six, headers fall into three shapes. Pick one deliberately —
they are not variations of one thing, they differ in *whether a WP menu is
involved at all*.

| | **A. Classic nav bar** | **B. Toggle-only** | **C. Stacked + utility** |
|---|---|---|---|
| Demos | FC Greenfield, Woolberry | Glowbar, Kojiro, Quantum Flares | Oakville |
| `header.layout` | `horizontal-justify` / `horizontal-left` | `horizontal-right` / `-center` / `-left` | `stacked-justify` |
| Desktop nav | **WP menu on `navbar`** | **none** — no menu assigned | WP menu on `navbar` |
| Utility row | — | — | second WP menu on `header` |
| The dialog | mobile only | **holds the whole desktop nav**, as a Builder widget | mobile only |
| `dialog.toggle` | `header:end` | `header:end` | `header:end` |
| `dialog.layout` | `offcanvas-top` | `dropbar-top` / `dropbar-center` | `offcanvas-top` |

**B is the one people don't expect.** Quantum Flares has *zero* WP menus
assigned to any position — `nav_menu_locations` is all `null`. Its navigation is
a Builder widget titled "Dialog Menu" sitting in the `dialog` position, opened
by a toggle at `header:end`. Kojiro does the same and adds a "Header
Reservation" widget for the booking CTA. This is how you get a fully designed,
image-rich, full-screen menu: **it is a builder layout, not a styled `<ul>`.**

So "how do I build header X" resolves to three decisions:

1. `config.header.layout` — the row arrangement (and `mobile.header.layout`).
2. Does the desktop nav come from a **WP menu on `navbar`** (A/C) or a **Builder
   widget in `dialog`** (B)?
3. `config.dialog.layout` + `toggle` — how the panel reveals, and from where.

Then dress it: mega menus on individual items (`menu.items.<id>.content`),
Builder widgets for CTAs (`navbar` / `header` positions), `header.transparent`
for a hero that runs under it.

### Desktop and mobile menus are usually *different WP menus*

Every multi-level demo ships two or three menus — "Main Menu", "Mobile Menu",
sometimes "Header Menu" — with different item sets, assigned to `navbar` and
`dialog-mobile` respectively. Oakville: 45 items desktop, 41 mobile, 5 header.
Don't assume one menu drives both.

Item types the demos rely on: `post_type` (a page), **`post_type_archive`** (a
CPT archive — this is how a menu entry lands on an `archive-<type>` template),
`taxonomy` (a term archive → `taxonomy-<tax>` template), `custom`.

---

## The shape of a real site

| Demo | Pages | Templates | Menus | CPTs (all via ACF) |
|---|--:|--:|--:|---|
| Glowbar (salon) | 13 | 4 | 1 | — |
| Quantum Flares | 7 | 4 | 1 | — |
| Kojiro (restaurant) | 4 | 6 | 1 | dish |
| FC Greenfield (club) | 6 | 11 | 2 | match, person, team |
| Woolberry (shop) | 18 | 17 | 3 | product, product_variation |
| Oakville (city portal) | 5 | 35 | 3 | announcement, authority, download, event, official, place, service, topic |

**The inversion is the lesson.** A brochure site is pages with almost no
templates. A content-driven site is a handful of pages plus a large template
set — Oakville renders a whole municipal portal from 5 static pages and 35
templates. When a client asks for "a page per service", the YOOtheme answer is
usually *one template + a CPT*, not thirty pages.

---

## Writing settings — what's scriptable and what isn't

Reading is trivial; **writing has three traps**, all verified in the theme source.

### 1. The UI save path is not just a write

`packages/theme-wordpress/src/CustomizerController.php::save`:

```php
$values  = Event::emit('config.save|filter', $values);   // ← listeners run here
$encoded = json_encode($values, JSON_UNESCAPED_SLASHES);
set_theme_mod('config', $encoded);
```

Two listeners are registered on `config.save`:

| Listener | Does |
|---|---|
| `SaveMenuLocations` | derives `nav_menu_locations` from `menu.positions[*].menu` |
| `SaveBuilderLayouts` | runs `builder->withParams(['context'=>'save'])->load()` over `footer.config` and every `menu.items[*].content` — this is where element version-migrations and normalisation happen |

A raw `wp option update` / `set_theme_mod` **skips both** and leaves a config the
UI would never have produced. Emit the event instead — that's what
`scripts/yoo-config.php` does.

### 2. There is no server-side LESS compiler

`packages/styler/src/StyleController.php::save` **receives already-compiled CSS**
— a base64 JSON payload uploaded from less.js in the browser — and writes
`~theme/css/theme.<id>.css`. Nothing on the server can regenerate it.

**Therefore `style`, `less` and `custom_less` cannot be compiled from PHP.**
You can write the value; the stylesheet stays stale until a browser recompiles
it — and `scripts/yoo-recompile.mjs` does that: it drives the Styler's
**"Recompile style"** button (load → compile → save → refresh) headlessly against
`/wp/wp-admin/admin-ajax.php?action=yootheme&yootheme=customizer` — the Customizer
is NOT at `customize.php` — and prints the stylesheet md5 before and after. Plan any
style change as script-then-recompile, or do it entirely in the LESS file
(`yootheme-less.md`).

### 3. `config` is JSON inside a serialized theme_mod

`theme_mods_<active-stylesheet>` is PHP-serialized; its `config` key is a JSON **string**.
A malformed write loses the whole site configuration silently — there is no
schema validation on read. Always back up first.

### The resulting split

| Target | Scriptable? |
|---|---|
| Templates (`yootheme` option) | ✅ freely — `scripts/yoo-content.php template …` |
| Builder widgets (`widget_builderwidget` + `sidebars_widgets`) | ✅ freely |
| Page layouts (`post_content`) | ✅ **as an admin** — `scripts/yoo-content.php page …` (see the KSES trap) |
| Layout / Settings config keys | ✅ **via the `config.save` event** — `scripts/yoo-config.php` |
| Menu assignment | ✅ write `menu.positions[].menu`; the listener derives the rest |
| `style` / `less` / `custom_less` | ⚠️ value only — CSS needs a browser Customizer save |

### 4. Writing a page: KSES will destroy the layout

`wp_update_post()` runs `content_save_pre`. Unless the current user can
`unfiltered_html`, KSES processes `post_content` — and a `<script>` or `<iframe>`
**anywhere inside the layout JSON** makes it entity-encode the *entire* comment:

```
in : <!-- {"type":"layout","children":[{"type":"text","props":{"content":"<script>…"}}]} -->
out: &lt;!-- {&quot;type&quot;:&quot;layout&quot;,&quot;children&quot;:…        ← unparseable, page destroyed
```

Measured on a live install: a comment with no HTML in it survives; one with a
`<script>` or `<iframe>` prop is mangled; introtext `<script>` is stripped. Note
that YOOtheme's own demo content hits this — Glowbar's footer uses an inline
`<script>` for the copyright year.

**Always `wp --user=<admin-id> eval-file …` when writing pages.**
`yoo-content.php` refuses to write without `unfiltered_html`.

### 5. Decode layout JSON WITHOUT assoc

`json_decode($json, true)` turns every empty object into an empty array, so
re-encoding writes `"arguments":[]` where the builder stored `"arguments":{}`.
The byte count can stay identical while the content silently drifts — it
corrupted 2 of 10 nodes on the first live test. `PageController` decodes with
`json_decode($page)` (no second arg) for exactly this reason. Keep it as
`stdClass` end to end.

`scripts/yoo-config.php` implements this:

```bash
wp eval-file yoo-config.php get header.layout
wp eval-file yoo-config.php set header.layout '"stacked-justify"'
wp eval-file yoo-config.php set menu.positions.navbar.menu 33
wp eval-file yoo-config.php backup / restore <file>
```

It always backs up, emits `config.save|filter`, verifies the JSON round-trip
before writing, and warns when you touch a style key.

**Verified on a live DDEV site** (YOOtheme 5.0.38 and again on 5.0.43, child theme + Polylang):

* `Event::emit('config.save|filter', …)` **does fire under WP-CLI** — the
  YOOtheme app is booted and `config.save` has its listeners registered.
* Causal proof of the listener: setting `menu.positions.header.menu = 2` made
  the stored `nav_menu_locations` go `{navbar:2,footer:3}` →
  `{navbar:2,header:2,footer:3}` with no other action. `unset` reverted it.
* `restore` round-trips **byte-identically** to the pre-test config.
* Invalid JSON and unknown commands exit non-zero without writing.

Run it from the project root so backups land somewhere you can find them
(`getcwd()` inside the container — `/var/www/html` on DDEV). With DDEV, take a
`ddev snapshot` first for anything non-trivial; the script's own backup covers
`config` only, not the rest of the database.

### Pages and templates — `scripts/yoo-content.php`

```bash
wp eval-file yoo-content.php page list
wp eval-file yoo-content.php page get 44          > layout.json
wp --user=1 eval-file yoo-content.php page set 44 layout.json     # ← admin required

wp eval-file yoo-content.php template list        # order == routing priority
wp eval-file yoo-content.php template get <id>    > tpl.json
wp --user=1 eval-file yoo-content.php template set new tpl.json
wp --user=1 eval-file yoo-content.php template reorder id1,id2
wp --user=1 eval-file yoo-content.php template delete <id>
wp eval-file yoo-content.php template export      > all-templates.json
```

Both writers run the builder pipeline the UI runs, so output matches a real
save. **Verified end to end on a live install** (YOOtheme 5.0.38, re-run on 5.0.43):

* `page get` → `page set` with no edits is **byte-identical** to the stored
  `post_content` (after the assoc-decode fix above).
* An edited layout renders on the front end immediately.
* A template created purely from CLI routed correctly (`single-post` +
  `terms:[1]`), rendered its section style, and resolved a dynamic binding with
  a `before` filter applied.
* `status: "disabled"` correctly falls through to the next matching template.
* `reorder` moves a specific template ahead of the catch-all; `delete` removes it.
* `TemplateHelper::match()` can be called directly to debug routing:
  ```bash
  wp eval 'var_dump(\YOOtheme\app(\YOOtheme\Builder\Templates\TemplateHelper::class)
             ->match(["type"=>"single-post","query"=>["terms"=>[1]]]));'
  ```

The `yootheme` option is written by `Storage` on the **shutdown** hook — verified
to fire under WP-CLI. Don't `exit()` early in a script that touches it.

---

## Demo package anatomy — and how to install one

An official `<name>_demo_package_wordpress.zip` is a **complete WordPress
install**, not a content export:

```
wp-admin/ wp-includes/ …                     full WP core
wp-content/plugins/advanced-custom-fields/   ACF (+ woocommerce, polylang, jetpack per demo)
wp-content/themes/yootheme/                  the parent theme, incl. all 49 style LESS files
wp-content/uploads/yootheme/demo/            all demo media
wp-content/sample_yootheme.json              the entire database, as JSON
wp-content/install.php                       a WP drop-in that loads it
```

`wp-content/install.php` overrides WordPress's `wp_install_defaults()`:

```php
$queries = json_decode(file_get_contents(__DIR__ . '/sample_yootheme.json'));
$replace = ['@@SITES_URL@@' => get_option('siteurl'),
            '@@ADMIN_EMAIL@@' => get_option('admin_email'),
            '@@TABLE_PREFIX@@' => $wpdb->prefix];
foreach ($queries as $query) { $wpdb->query(strtr($query, $replace)); }
// …WooCommerce thumbnail regen, flush_rules, cache flush…
unlink($example); unlink(__FILE__);          // self-destructs
```

**So installing a demo = run the normal WordPress web installer.** Unzip, create
an empty DB, write `wp-config.php`, hit `/wp-admin/install.php`. The drop-in
replaces the default "Hello World" content with the demo's entire database, then
deletes itself and the JSON.

Three things to know:

1. **It runs at install time only.** There is no "import demo" button afterwards.
   To re-run it, restore both files and re-install into an empty DB.
2. **It DROPs and CREATEs the WP tables.** Never point it at a database with real
   content.
3. **It self-cleans.** Copy `sample_yootheme.json` out *before* installing if you
   want to study it.

### Mining a demo package without installing it

`sample_yootheme.json` is a JSON array of SQL statements. Everything above can be
read straight out of it:

```python
import json, re

stmts = json.load(open('sample_yootheme.json'))

def rows(table):
    """Yield column-mapped rows from `insert into <table> (cols) values (…)`.
       NB: the dumps use an EXPLICIT, non-standard column order —
       postmeta is (meta_id, meta_key, meta_value, post_id). Always honour
       the column list; never index by position."""
    pat = re.compile(r'^\s*insert into\s+`?@@TABLE_PREFIX@@' + table +
                     r'`?\s*\(([^)]*)\)\s*values\s*', re.I | re.S)
    ...   # split VALUES tuples respecting quotes/escapes, zip with the col list

options = {r['option_name']: r['option_value'] for r in rows('options')}
config  = json.loads(...)   # unserialize options['theme_mods_yootheme'], then json.loads its 'config'
layout  = json.loads(re.search(r'<!--\s?(\{.*})\s?-->', post_content, re.S).group(1))
```

`theme_mods_yootheme` is PHP-serialized, so unserialize it first —
`php -r '$d=unserialize(file_get_contents("php://stdin")); echo json_encode($d);'`
is the least error-prone way.

**Why bother:** the demos are the only authoritative worked examples of the
layout grammar, the binding syntax and the template-routing conventions. When a
prop's meaning is unclear, grep for it across six real sites rather than
guessing.

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Edit the HTML in `post_content` | It is generated output; edit in the builder or the JSON comment |
| Look for the footer in `footer.php` | `config.footer.content` — or a Builder widget in `bottom` |
| Assume one menu serves desktop and mobile | Check `nav_menu_locations`; demos ship 2–3 distinct menus |
| Build a mega menu with a plugin | `config.menu.items.<id>.content` = a builder fragment |
| Hack `header.php` to add a header CTA | A Builder widget in the `navbar` / `header` position |
| Style the mobile menu by overriding desktop CSS | `config.mobile.*` + the `*-mobile` positions are a separate config |
| Create one page per catalogue entry | One template + a CPT (see the Oakville ratio) |
| Re-run `install.php` on a live DB | It DROPs the tables; only ever into an empty DB |
| Hand-`sed` a URL migration over `post_content` | `wp search-replace` — the layout JSON is escaped and serialized data is nearby |
| Index demo SQL rows by position | The dumps carry an explicit, reordered column list |
