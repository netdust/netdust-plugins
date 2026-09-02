---
name: ntdst-yootheme
description: Use when building, styling, or extending a YOOtheme Pro site — composing pages, menus, headers and footers; building symbols and templates in the builder; wiring dynamic content sources; writing a child theme's less/theme.<slug>.less style; mapping design tokens onto UIkit variables; or extending the builder with PHP sources and custom elements. Triggers on file edits under themes/*/less/theme.*.less, on yootheme child themes, and on keywords YOOtheme, YOOtheme Pro, builder, symbol, sublayout, fragment, customizer, styler, uikit, UIkit variables, theme.<slug>.less, dynamic content, content source, element.php, layout JSON, parallax, panel-slider, tile, uk-section, recompile style. Symptoms include "my LESS style does not show up", "the builder cannot do X", a style that compiles but renders wrong, a design token that changes nothing on screen, or needing to know whether a value is a setting, a variable, a hook, or a rule. Read lessons.md FIRST — it lists the traps that silently do the wrong thing.
---

# NTDST YOOtheme Integration — Domain Knowledge

Use when building, styling, or extending a YOOtheme Pro site: composing pages,
menus, headers and footers; wiring dynamic content and templates; writing a
`less/theme.<slug>.less` style; or extending the builder with PHP sources and
custom elements.

Four halves, four reference files. **Pick the one that matches the question —
most YOOtheme work needs no PHP at all.**

**Read `lessons.md` before you build anything.** The reference files describe what
the product CAN do; `lessons.md` is the list of things that silently do something
else — props that write into the layout JSON and emit nothing, defaults that hide
an element entirely, utilities that outrank your CSS. Every one of them was found
by shipping, and every one reads as "this feature is broken" until you know it.

| You are… | Read |
|---|---|
| **About to build / style / debug anything** | **`lessons.md` — traps first, then the file below** |
| Asking WHERE something lives (pages, menus, header, footer, templates, a demo package) | `references/yootheme-site-model.md` |
| Setting up SITE CHROME (header/mobile/top/bottom/sidebar layouts, post & blog defaults, Settings) | `references/yootheme-customizer.md` |
| Composing or editing a PAGE (layout JSON, elements, props, responsive grid) | `references/yootheme-builder-json.md` |
| Driving pages from DATA (model → module source → bindings → template routing) | `references/yootheme-content-binding.md` |
| Deciding how the site LOOKS (child theme, LESS, tokens, fonts) | `references/yootheme-less.md` + `templates/theme.child.less.md` |
| Getting a model's fields into the picker, or a curated query | `references/yootheme.md` |

## Orientation — the five facts that reframe everything

Learned from six official YOOtheme demo packages (theme 5.0.32) and verified
against the parent theme's source at **5.0.43** (2026-09-02). 5.0.38 → 5.0.43 changed
15 PHP files and nothing in the layout grammar except `button_item`'s modal condition
now reading `lightbox` and `grid_item`'s `{@content_expand}`. **5.0.41 is the floor**:
it closed CVE-2026-75115 (arbitrary file read) and CVE-2026-76613 (SQL injection), both
reachable by a contributor account. Detail in `yootheme-site-model.md`.

1. **A YOOtheme site lives in the database, not in theme files.** Page layouts
   are JSON in `wp_posts.post_content` (inside a trailing `<!-- {...} -->`
   comment). Templates are in the `yootheme` option. Header, footer, menu
   positions and style choice are in `theme_mods_<active-stylesheet>.config`
   (read it with `get_theme_mod('config')` — the option name follows the CHILD
   theme, not `yootheme`).
2. **One layout grammar, four homes.** The same node JSON is a page, a template,
   the footer (`config.footer.content`), *and* a Builder widget. Learn it once.
3. **Site chrome is assembled from named positions** — `navbar`, `header`,
   `dialog`, `top`, `bottom`, `builder-1…6`, each with a `*-mobile` twin.
   **Mobile is a separate config, not a media query.** Five ways to fill a
   header: built-in items (`"header:end"` strings), a WP menu, a per-item mega
   menu, a **Builder widget**, or the `menu` element. All six demos use Builder
   widgets for header CTAs and mobile panels — that is the answer to "how do I
   put arbitrary content in the header without touching `header.php`".
4. **The official demos register every CPT, taxonomy and field through ACF** —
   no custom plugin code, because YOOtheme auto-generates the queryable source
   from ACF's location rules. **This is NOT the netdust route, and it is not an
   option to weigh.** On this fleet content types are ntdst-core Data Manager
   models in a `<project>-core` mu-plugin, and the YOOtheme source is written
   against them (see `references/yootheme.md`). Read the ACF material to
   understand what a demo is doing; never propose ACF for a netdust build.
5. **Templates scale, pages don't.** Oakville renders a whole municipal portal
   from 5 pages + 35 templates; the brochure demo is 13 pages + 4 templates.
   "A page for each X" usually means one CPT + two templates.

`scripts/demo-mine.py` reads any demo package or YOOtheme dump and prints all of
the above — run it before guessing.

## Reading vs writing

**Reading** is free — `scripts/demo-mine.py` on a dump, or `wp option get`.

**Writing needs care for three verified reasons** (detail + the split of what is
and isn't scriptable in `yootheme-site-model.md` → "Writing settings"):

1. The Customizer's save runs `Event::emit('config.save|filter', …)`, whose
   listeners derive `nav_menu_locations` from `menu.positions[*].menu` and
   normalise footer / mega-menu layouts through the builder. A raw
   `set_theme_mod` skips both.
2. **There is no server-side LESS compiler** — less.js compiles in the browser
   and uploads the CSS. `style` / `less` / `custom_less` can be *set* but not
   *compiled* from CLI. Script the value, then `scripts/yoo-recompile.mjs` (it
   clicks the Styler's "Recompile style" and proves the md5 changed).
3. `config` is a JSON string inside a PHP-serialized theme_mod; a bad write
   loses the site's whole configuration silently.

Writing **pages and templates** adds two more, both found the hard way on a live
install:

4. **KSES destroys builder layouts.** Without `unfiltered_html`, a `<script>` or
   `<iframe>` anywhere in the JSON makes WordPress entity-encode the *whole*
   comment — the page becomes unparseable. Always `wp --user=<admin-id>`.
5. **Decode layout JSON without `assoc`.** `json_decode($j, true)` turns `{}` into
   `[]`, so re-encoding silently rewrites `"arguments":{}` as `"arguments":[]`
   with no change in byte count.

| Tool | Covers |
|---|---|
| `scripts/yoo-config.php` | the `config` theme_mod — get/set/unset/backup/restore |
| `scripts/yoo-content.php` | pages (`page get/set/list`) and templates (`template list/get/set/reorder/delete/export`) |

Both run the same builder/event pipeline the UI runs, back up before every write,
and are verified byte-identical against a live YOOtheme install (5.0.38, re-run on 5.0.43). Prefer
them over hand-rolled `wp option update` / `wp post update`.

## Data reaches the builder — no PHP

Content types are ntdst-core models. The **ntdst-baseline `yootheme` module** (≥ 2.3.0,
opt-in by assignment, OFF by default) publishes every declared field to the Dynamic
Content picker; query names are derived from the post type (`cases.customCases`,
`verhalen.singleVerhaal`). A project that hand-registers a source for ntdst-core fields is
drift. Detail, the type table and the one PHP escape hatch (a curated `queryType` that
returns the module's type): `references/yootheme.md`. The bridge itself is documented in
`netdust-wp:ntdst-framework` → `references/baseline.md`.

## Reference Files

| File | Content |
|------|---------|
| `references/yootheme-site-model.md` | **Where a site lives** — the four DB stores, the positions model, five ways into a header, the three header architectures, demo-package anatomy + how to mine one |
| `references/yootheme-customizer.md` | **Every setting** — complete panel-by-panel vocabulary extracted from the theme's own config: Site, Header (12 layouts), Mobile, Top/Bottom, Sidebar, Post/Blog fallbacks, Settings |
| `references/yootheme-builder-json.md` | **Page composition** — layout JSON grammar, 47-element catalogue, prop systems (spacing, responsive widths, parallax, visibility), card-family props |
| `references/yootheme-content-binding.md` | **Data → pages, no PHP** — field-type mapping, source naming rules, `#parent` repeats, the two repeat shapes, `_condition`, filters, template routing |
| `references/yootheme.md` | **Data → builder** — the ntdst-baseline `yootheme` module, the type table, derived query names, the curated-query escape hatch |
| `references/yootheme-less.md` | **Styling** — child themes, the styler, LESS discovery + browser compile, design tokens → UIkit mapping, font loading, the classic→child conversion |
| `templates/theme.child.less.md` | Copy-in skeleton for `less/theme.<slug>.less` (2-section shape + verification commands) |
| `golden-paths/yootheme-integration.md` (in `ntdst-patterns`) | Enable the module, bind a field, the escape hatch — verified against edushare 2026-09-02 |

### Before writing PHP, check it isn't already free

| Requirement | Built-in answer |
|---|---|
| New content type with editable fields | An ntdst-core Data Manager model in `<project>-core`; the baseline `yootheme` module publishes it (`references/yootheme.md`). NOT ACF — see orientation fact 4. |
| Listing of posts, filtered/sorted/paginated | Bind a `grid`/`list` container to a `custom<Type>s` query |
| Sort or date-filter by a custom field | `order: "field:<name>"`, `date_column: "field:<name>"` |
| Different layout per category | A second template of the same type, ordered before the catch-all |
| Archive page size | `params.posts_per_page` on the template — not `pre_get_posts` |
| Hide a block when a field is empty | `source.props._condition` with `condition: "!"` |
| Format a date / truncate / prefix | `filters.date` / `limit` / `before` on the binding |
| Mega menu | `config.menu.items.<id>.content` = a builder fragment |

## Styling — the five traps that cost the most

Full detail in `references/yootheme-less.md`; these are the ones that burn a day:

1. **YOOtheme compiles LESS in the BROWSER.** No PHP compile step exists — prove a style compiles with a local `less@4` + `lessc`, and beware SIGPIPE (piping to `head` fakes exit 1).
2. **A child theme must carry NO template files.** `header.php`/`page.php`/etc. override the parent and bypass the builder entirely.
3. **Activating a child does not rewrite the `template` option.** If the theme was ever activated standalone, the parent is silently never used. Fix: activate parent, re-activate child.
4. **Fonts belong to the Customizer's font selector**, which self-hosts them via `StyleFontLoader`. A `wp_enqueue_style` for the same family loads it twice, from Google's CDN.
5. **The Customizer edits section 2, never section 1.** Project `@prj-*` tokens are invisible to it, so a Customizer colour edit silently diverges from the token it came from — and the DB copy wins.
