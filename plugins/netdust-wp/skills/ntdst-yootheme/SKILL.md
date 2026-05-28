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

## Reference Files

| File | Content |
|------|---------|
| `references/yootheme.md` | Full Dynamic Content guide, resolver patterns, field mapping |
