# NTDST YOOtheme Integration — Domain Knowledge

Use when building, styling, or extending a YOOtheme Pro site: composing pages,
menus, headers and footers; wiring dynamic content and templates; writing a
`less/theme.<slug>.less` style; or extending the builder with PHP sources and
custom elements.

Four halves, four reference files. **Pick the one that matches the question —
most YOOtheme work needs no PHP at all.**

| You are… | Read |
|---|---|
| Asking WHERE something lives (pages, menus, header, footer, templates, a demo package) | `references/yootheme-site-model.md` |
| Setting up SITE CHROME (header/mobile/top/bottom/sidebar layouts, post & blog defaults, Settings) | `references/yootheme-customizer.md` |
| Composing or editing a PAGE (layout JSON, elements, props, responsive grid) | `references/yootheme-builder-json.md` |
| Driving pages from DATA (ACF → sources → bindings → template routing) | `references/yootheme-content-binding.md` |
| Deciding how the site LOOKS (child theme, LESS, tokens, fonts) | `references/yootheme-less.md` + `templates/theme.child.less.md` |
| Extending the builder with PHP (custom sources, resolvers, elements) | this file + `references/yootheme.md` |

## Orientation — the five facts that reframe everything

Learned from six official YOOtheme demo packages (theme 5.0.32) and verified
against the parent theme's source. Detail in `yootheme-site-model.md`.

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
   no custom plugin code. YOOtheme auto-generates the queryable source from
   ACF's location rules. Reach for PHP only when that runs out.
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
   *compiled* from CLI. Script the value, then a browser Customizer save.
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
and are verified byte-identical against a live YOOtheme 5.0.38 install. Prefer
them over hand-rolled `wp option update` / `wp post update`.

## Essential Principles (PHP extension)

### No Custom ObjectTypes
Never create custom `objectType()` for content. Use existing auto-registered types from `YOOthemeDynamicContentService`. Types are auto-created from Data Manager models (PascalCase of post type slug).

### Resolvers Must Be Functions
Resolvers must be **namespace-prefixed standalone functions**, not class methods or closures. YOOtheme serializes resolver references to JSON — class methods and closures break serialization (white page crash).

### Never Use __NAMESPACE__
```php
// WRONG — serialization fails
'func' => __NAMESPACE__ . '\\my_resolver',

// CORRECT — explicit string
'func' => 'ntdstheme\\services\\yootheme\\my_resolver',
```

## Auto-Registered Types

`YOOthemeDynamicContentService` (priority 20) automatically creates ObjectTypes for all Data Manager models. Every type includes standard fields: `id`, `title`, `content`, `excerpt`, `permalink`, `featured_image`.

Field type mapping:

| NTDST Type | YOOtheme Type |
|------------|---------------|
| `text`, `textarea`, `email`, `select`, `date` | `String` |
| `integer` | `Int` |
| `float` | `Float` |
| `boolean` | `Boolean` |
| `gallery` | `['listOf' => 'Attachment']` |
| `relation` | Related type or `['listOf' => Type]` |
| `repeater` | `['listOf' => 'TypeNameFieldNameItem']` |

## Custom Query Source Pattern

```php
<?php
namespace ntdstheme\services\yootheme;

use YOOtheme\Event;

class MySourcesService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name'     => 'My Sources',
            'priority' => 21,  // After YOOthemeDynamicContentService (20)
        ];
    }

    public function __construct() { $this->init(); }

    private function init(): void
    {
        add_action('init', function () {
            if (!function_exists('YOOtheme\app')) {
                return;
            }

            Event::on('source.init', function ($source) {
                $source->queryType([
                    'fields' => [
                        'myQuery' => [
                            'type'       => ['listOf' => 'ExistingType'],
                            'metadata'   => [
                                'label' => 'My Query',
                                'group' => 'My Group',
                            ],
                            'extensions' => ['call' => [
                                'func' => 'ntdstheme\\services\\yootheme\\resolve_my_query',
                            ]],
                        ],
                    ],
                ]);
            }, -10);
        });
    }
}

function resolve_my_query($root, array $args)
{
    $posts = get_posts([
        'post_type'      => 'my_type',
        'posts_per_page' => $args['limit'] ?? 10,
        'post_status'    => 'publish',
    ]);

    return array_map(
        'ntdstheme\\services\\yootheme\\attach_post_meta',
        $posts
    );
}
```

## Event Priority

YOOtheme uses `krsort()` — **higher numbers run first**:
```php
Event::on('source.init', $callback, 10);   // Runs FIRST
Event::on('source.init', $callback, 0);    // Default
Event::on('source.init', $callback, -10);  // Runs AFTER (use this for most sources)
```

## Multiple Items Pattern (Repeaters in Builder)

To enable "Multiple Items Source" dropdown for Grid/List elements:

1. Return **single type** (not `listOf`) from query
2. User selects repeater field as "Multiple Items Source"
3. Maps sub-fields in Builder

```php
'type' => 'ArtistProfile',  // Single, NOT ['listOf' => ...]
```

## attach_post_meta()

Always use on returned posts to hydrate meta for field resolution:
```php
$post = attach_post_meta($post);
// Now $post->meta['field'] and $post->fields['field'] available
```

Filters out WordPress internal fields (`_edit_lock`, etc.), converts DateTime to strings, only includes Data Manager schema fields.

## Anti-Patterns

| Smell | Fix |
|-------|-----|
| `$source->objectType('Custom', [...])` | Use auto-registered types from Data Manager |
| `__NAMESPACE__ . '\\resolver'` | Explicit string: `'namespace\\resolver'` |
| `[$this, 'resolver']` as func | Standalone function outside class |
| `Event::on(...)` without init hook | Wrap in `add_action('init', ...)` |
| Missing YOOtheme check | `if (!function_exists('YOOtheme\app')) return;` |
| DateTime in returned data | Convert to `$value->format('Y-m-d H:i:s')` |
| WordPress internal meta in data | Filter out `_` prefix fields |
| Source priority same as base types | Use priority 21+ (base types are 20) |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| White page in Customizer | `__NAMESPACE__` in resolver, DateTime, non-serializable | Use explicit strings, convert types |
| Missing dropdown option | Wrong event priority, syntax error, no init hook | Use `-10`, check PHP log, wrap in init |
| Fields return empty | Meta not attached, wrong field name | Use `attach_post_meta()`, check schema |

Debug: Set `'debug' => true` in `theme-config.php` → `modules.yootheme_dynamic_content`.
Logs: `app/content/logs/app-YYYY-MM-DD.log`.

## Custom Builder Elements (not just content sources)

A Dynamic Content *source* feeds existing elements. A custom **Builder element** (your own draggable component with its own fields + render template) is registered differently — via a `builder/bootstrap.php` the theme loads through `YOOtheme\app()->load()`:

```php
// A service loads the builder module when YOOtheme initialises:
class FormElementsService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return ['name' => 'Form Elements', 'priority' => 5];
    }
    public function __construct() { $this->init(); }
    private function init(): void
    {
        add_action('after_setup_theme', [$this, 'loadBuilderModule'], 5);
    }
    public function loadBuilderModule(): void
    {
        if (!function_exists('YOOtheme\app')) {
            return;                                 // mandatory guard
        }
        $bootstrap = get_stylesheet_directory() . '/builder/bootstrap.php';
        if (file_exists($bootstrap)) {
            \YOOtheme\app()->load($bootstrap);       // YOOtheme's module loader, NOT require
        }
    }
}
```

```php
// builder/bootstrap.php — extends the Builder with your element types
namespace YOOtheme;
use YOOtheme\Builder;
return [
    'extend' => [
        Builder::class => function (Builder $builder) {
            foreach (['form', 'form_field', 'form_submit'] as $element) {
                $file = __DIR__ . "/{$element}/element.php";
                if (file_exists($file)) {
                    $builder->addType("ntdst_{$element}", $file);   // namespaced type name
                }
            }
        },
    ],
];
```

```php
// builder/<element>/element.php — the element definition (fields + render template)
namespace YOOtheme;
return [
    'name'    => 'ntdst_form_field',
    'title'   => 'Form Field',
    'group'   => 'ntdst',                                   // your group in the element picker
    'element' => true,
    'defaults'  => ['field_type' => 'text', 'required' => false],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields'    => [                                        // the Builder settings panel
        'field_type' => ['label' => 'Type', 'type' => 'select', 'options' => [/* … */]],
        'field_name' => ['label' => 'Name', 'type' => 'text'],
    ],
];
```

## Asset Control — YOOtheme ignores `wp_dequeue_*`

YOOtheme uses its own **Metadata system**, not `wp_enqueue_*`, so the standard `wp_dequeue_script/style` calls do nothing to YOOtheme's own assets. To strip them you hook **before** YOOtheme prints, at `wp_head` / `admin_print_scripts` priority 5:

```php
private function init(): void
{
    add_action('wp_head', [$this, 'remove_yootheme_assets'], 5);
    add_action('admin_print_scripts', [$this, 'remove_yootheme_assets'], 5);
}
```

This is a real Rossi service (`YOOthemeAssetControlService`) — note it if a project needs to drop YOOtheme's bundled JS/CSS and the usual dequeue does nothing.

## Golden path

For a complete, verified end-to-end source slice (service + resolver + `attach_post_meta` + `theme-config.php` registration), see **`netdust-wp:ntdst-patterns` → `golden-paths/yootheme-integration.md`** — extracted from Rossi (`ArtistSourcesService`). Read it before planning a new source.

## Reference Files

| File | Content |
|------|---------|
| `references/yootheme-site-model.md` | **Where a site lives** — the four DB stores, the positions model, five ways into a header, the three header architectures, demo-package anatomy + how to mine one |
| `references/yootheme-customizer.md` | **Every setting** — complete panel-by-panel vocabulary extracted from the theme's own config: Site, Header (12 layouts), Mobile, Top/Bottom, Sidebar, Post/Blog fallbacks, Settings |
| `references/yootheme-builder-json.md` | **Page composition** — layout JSON grammar, 47-element catalogue, prop systems (spacing, responsive widths, parallax, visibility), card-family props |
| `references/yootheme-content-binding.md` | **Data → pages, no PHP** — ACF field-type mapping, source naming rules, `#parent` repeats, `_condition`, filters, template routing |
| `references/yootheme.md` | **PHP extension** — custom Dynamic Content sources, resolver patterns, field mapping |
| `references/yootheme-less.md` | **Styling** — child themes, the styler, LESS discovery + browser compile, design tokens → UIkit mapping, font loading, the classic→child conversion |
| `templates/theme.child.less.md` | Copy-in skeleton for `less/theme.<slug>.less` (2-section shape + verification commands) |
| `golden-paths/yootheme-integration.md` (in `ntdst-patterns`) | Worked source slice, verified against Rossi source |

### Before writing PHP, check it isn't already free

| Requirement | Built-in answer |
|---|---|
| New content type with editable fields | ACF post type + field group (`yootheme-content-binding.md`) |
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
