# NTDST YOOtheme Integration — Domain Knowledge

Use when creating YOOtheme Dynamic Content sources, working with YOOtheme Builder, or integrating custom post types with YOOtheme's content system.

## Essential Principles

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
| `references/yootheme.md` | Full Dynamic Content guide, resolver patterns, field mapping |
| `golden-paths/yootheme-integration.md` (in `ntdst-patterns`) | Worked source slice, verified against Rossi source |
