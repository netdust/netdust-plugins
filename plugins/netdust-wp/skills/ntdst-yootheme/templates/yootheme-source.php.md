# Template: YOOtheme Source Service

```php
<?php
/**
 * {Name} Sources Service
 *
 * Custom YOOtheme Dynamic Content sources for {description}
 *
 * @package ntdstheme\services\yootheme
 */
namespace ntdstheme\services\yootheme;

defined('ABSPATH') || exit;

use YOOtheme\Builder\Source;
use function YOOtheme\app;

class {Name}SourcesService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name' => '{Display Name} Sources',
            'description' => 'YOOtheme sources for {description}',
            'priority' => 18,
        ];
    }

    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        add_action('init', function () {
            if (!function_exists('YOOtheme\app')) {
                return;
            }

            $this->registerSources();
        });
    }

    private function registerSources(): void
    {
        app(Source::class)->listen('source.init', function ($source) {
            $source->queryType([
                'fields' => [
                    '{queryName}' => [
                        // Use EXISTING type - never create custom ObjectType
                        'type' => ['listOf' => '{ExistingType}'],
                        'metadata' => [
                            'label' => '{Source Label}',
                            'group' => '{Menu Group}',
                            'fields' => [
                                '_count' => [
                                    'label' => 'Limit',
                                    'type' => 'number',
                                    'default' => 10,
                                ],
                            ],
                        ],
                        'extensions' => [
                            'call' => [
                                // MUST use explicit namespace string
                                'func' => 'ntdstheme\\services\\yootheme\\resolve_{query_slug}',
                            ],
                        ],
                    ],
                ],
            ]);
        }, -10);
    }
}

/**
 * Resolver function for {queryName}
 *
 * @param mixed $root Root value
 * @param array $args Query arguments from YOOtheme
 * @return \WP_Post[] Array of WP_Post objects
 */
function resolve_{query_slug}($root, array $args): array
{
    $count = absint($args['_count'] ?? 10);

    // Use Data Manager, return WP_Post objects
    return ntdst_data()->get('{post_type}')
        ->where('post_status', 'publish')
        ->orderBy('date', 'DESC')
        ->limit($count)
        ->getRaw();
}
```

## Placeholders

| Placeholder | Replace With |
|-------------|--------------|
| `{Name}` | PascalCase name (e.g., `Featured`) |
| `{Display Name}` | Human-readable (e.g., `Featured Items`) |
| `{description}` | Brief description |
| `{queryName}` | camelCase query name (e.g., `featuredArtworks`) |
| `{query_slug}` | snake_case for function (e.g., `featured_artworks`) |
| `{ExistingType}` | YOOtheme type (e.g., `Artwork`, `ArtistProfile`) |
| `{Source Label}` | Label in dropdown (e.g., `Featured Artworks`) |
| `{Menu Group}` | Group name (e.g., `Gallery`, `Artists`) |
| `{post_type}` | WordPress post type slug |

## Available Types

Auto-registered by YOOthemeDynamicContentService:

- `ArtistProfile`, `Artwork`, `Artist`
- `Exhibition`, `Project`, `Portfolio`
- `Post`, `Page`, `User`

## Location

`app/content/themes/ntdstheme/services/yootheme/{Name}SourcesService.php`

## Required Registration

```php
// theme-config.php
'services' => [
    'core' => [
        'ntdstheme\\services\\yootheme\\{Name}SourcesService',
    ],
],
```

## Critical Rules

1. **Never use `$source->objectType()`** - breaks Dynamic Content dropdown
2. **Never use `__NAMESPACE__`** - serialization failure
3. **Always return `WP_Post[]`** via `getRaw()` - not arrays
4. **Always use priority `-10`** on source.init event
