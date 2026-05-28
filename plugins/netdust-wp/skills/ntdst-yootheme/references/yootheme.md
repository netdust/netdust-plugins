# YOOtheme Integration Guide

Complete guide to integrating custom content with YOOtheme Builder's Dynamic Content system.

---

## Table of Contents

1. [How Dynamic Content Works](#how-dynamic-content-works)
2. [Auto-Registered Types](#auto-registered-types)
3. [Custom Query Sources](#custom-query-sources)
4. [Resolver Functions](#resolver-functions)
5. [Field Type Handling](#field-type-handling)
6. [Multiple Items Pattern](#multiple-items-pattern)
7. [Troubleshooting](#troubleshooting)
8. [Anti-Patterns](#anti-patterns)

---

## How Dynamic Content Works

YOOtheme's Dynamic Content system allows page builder elements to be populated from WordPress data. It uses a GraphQL-like type system internally.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **ObjectType** | Defines structure of a data type (fields and their types) |
| **QueryType** | Defines how to fetch data (sources in the dropdown) |
| **Resolver** | Function that returns data for a field or query |
| **Source** | Entry point in the Dynamic Content dropdown |

### Event Priority

YOOtheme uses `krsort()` for event listeners, meaning **higher numbers run first**:

```php
Event::on('source.init', $callback, -10);  // Runs AFTER 0
Event::on('source.init', $callback, 0);    // Default
Event::on('source.init', $callback, 10);   // Runs FIRST
```

Use `-10` for most sources to ensure base types are registered first.

---

## Auto-Registered Types

`YOOthemeDynamicContentService` automatically creates YOOtheme types for all NTDST Data models.

### How It Works

1. Service reads all registered models from Data Manager
2. For each model with fields, creates an ObjectType
3. Type name is PascalCase of post type (e.g., `artist_profile` → `ArtistProfile`)
4. All schema fields become queryable in Dynamic Content

### Standard Fields (Auto-Included)

Every auto-registered type includes these WordPress fields:

| Field | Description |
|-------|-------------|
| `id` | Post ID |
| `title` | Post title |
| `content` | Post content (with `the_content` filter) |
| `excerpt` | Post excerpt or trimmed content |
| `permalink` | Full URL to post |
| `featured_image` | Featured image URL (full size) |

### Available Types

Types are auto-registered for any model with fields:

```
ArtistProfile      → artist_profile
Artwork            → artwork
Exhibition         → exhibition
GalleryProfile     → gallery_profile
Project            → project
PressKit           → press_kit
```

Plus WordPress built-in types: `Post`, `Page`, `User`, `Attachment`

---

## Custom Query Sources

Custom query sources add entries to the Dynamic Content dropdown without creating new ObjectTypes.

### Basic Pattern

```php
namespace ntdstheme\services\yootheme;

use YOOtheme\Event;

class MySourcesService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name' => 'My Sources',
            'priority' => 21, // After YOOthemeDynamicContentService (20)
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

            Event::on('source.init', function ($source) {
                $source->queryType([
                    'fields' => [
                        'myCustomQuery' => [
                            'type' => ['listOf' => 'Artwork'],  // Use EXISTING type
                            'metadata' => [
                                'label' => 'My Custom Artworks',
                                'group' => 'My Custom Sources',
                            ],
                            'extensions' => [
                                'call' => [
                                    'func' => 'ntdstheme\\services\\yootheme\\resolve_my_query',
                                ],
                            ],
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
        'post_type' => 'artwork',
        'posts_per_page' => 10,
        'post_status' => 'publish',
    ]);

    // Attach meta for field resolution
    return array_map(function ($post) {
        return attach_post_meta($post);
    }, $posts);
}
```

### Query Type Structure

```php
$source->queryType([
    'fields' => [
        'queryName' => [
            'type' => 'TypeName',           // Single item
            // OR
            'type' => ['listOf' => 'Type'], // Multiple items

            'metadata' => [
                'label' => 'Display Name',
                'group' => 'Dropdown Group',
            ],

            'extensions' => [
                'call' => [
                    'func' => 'namespace\\resolver_function',
                    'args' => ['key' => 'value'],  // Optional
                ],
            ],
        ],
    ],
]);
```

### Priority Ordering

| Service | Priority | Purpose |
|---------|----------|---------|
| YOOthemeDynamicContentService | 20 | Base types |
| Custom sources | 21+ | Query types that reference base types |

---

## Resolver Functions

Resolvers must be **namespace-prefixed functions**, not class methods.

### Why Functions?

YOOtheme serializes resolver references to JSON. Class methods and closures don't serialize properly, causing:
- White page crashes
- Missing dropdown options
- Broken Dynamic Content panel

### Correct Pattern

```php
// In the service file, OUTSIDE the class

function resolve_featured_artworks($root, array $args)
{
    $posts = get_posts([
        'post_type' => 'artwork',
        'posts_per_page' => $args['limit'] ?? 10,
        'meta_key' => 'featured',
        'meta_value' => '1',
    ]);

    return array_map('ntdstheme\\services\\yootheme\\attach_post_meta', $posts);
}
```

### Resolver Parameters

| Parameter | Description |
|-----------|-------------|
| `$root` | Parent object (null for query roots) |
| `$args` | Arguments from `extensions.call.args` |

### Function Reference Syntax

Always use double-escaped backslashes in the string:

```php
'func' => 'ntdstheme\\services\\yootheme\\my_function',
```

**NOT:**
```php
'func' => __NAMESPACE__ . '\\my_function',  // BREAKS!
```

---

## Field Type Handling

### Attaching Meta to Posts

Use `attach_post_meta()` to hydrate posts with metadata:

```php
use function ntdstheme\services\yootheme\attach_post_meta;

$post = get_post($id);
$post = attach_post_meta($post);

// Now $post->meta['field_name'] and $post->fields['field_name'] are available
```

### What attach_post_meta() Does

1. Gets all post meta
2. Filters out WordPress internal fields (`_edit_lock`, `_edit_last`, etc.)
3. Only includes fields from Data Manager schema
4. Converts DateTime objects to strings
5. Attaches to `$post->meta` and `$post->fields`

### Field Type Mapping

| NTDST Type | YOOtheme Type |
|------------|---------------|
| `text`, `textarea`, `email`, `select`, `date` | `String` |
| `integer`, `int` | `Int` |
| `float`, `double` | `Float` |
| `boolean`, `bool` | `Boolean` |
| `gallery` | `['listOf' => 'Attachment']` |
| `relation` | Related type or `['listOf' => Type]` |
| `repeater` | `['listOf' => 'TypeNameFieldNameItem']` |
| `array`, `json` | `String` |

### Gallery Fields

Gallery fields return arrays of Attachment objects:

```php
// Resolver handles this automatically
// Returns: [{url, thumbnail, medium, large, full, alt, caption, description, width, height}, ...]
```

### Relation Fields

Relations return actual post objects:

```php
// Single relation
'type' => 'Artist'

// Multiple relation
'type' => ['listOf' => 'Artist']
```

### Repeater Fields

Repeaters create a child ObjectType for the row structure:

```php
// artist_profile with education_history repeater
// Creates: ArtistProfileEducationHistoryItem type
// Returns: [{year, institution, degree}, ...]
```

---

## Multiple Items Pattern

To enable the "Multiple Items Source" dropdown for repeater fields:

### Return Single Type (Not listOf)

```php
$source->queryType([
    'fields' => [
        'theArtistProfile' => [
            'type' => 'ArtistProfile',  // Single, NOT ['listOf' => ...]
            'metadata' => [
                'label' => 'The Artist Profile',
                'group' => 'Artist Platform',
            ],
            'extensions' => [
                'call' => [
                    'func' => 'ntdstheme\\services\\yootheme\\resolve_the_artist_profile_single',
                ],
            ],
        ],
    ],
]);
```

### How Users Access Repeater Data

1. Select "The Artist Profile" as source
2. "Multiple Items Source" dropdown appears
3. Select repeater field: `education_history`
4. Map sub-fields: `year`, `institution`, `degree`
5. Use in Grid/List element

### Resolver Returns Single Post

```php
function resolve_the_artist_profile_single($root, array $args)
{
    $profiles = get_posts([
        'post_type' => 'artist_profile',
        'posts_per_page' => 1,
        'post_status' => 'publish',
    ]);

    if (empty($profiles)) {
        return null;
    }

    return attach_post_meta($profiles[0]);
}
```

---

## Troubleshooting

### White Page in Customizer

**Symptoms:** Page goes blank when opening Dynamic Content panel

**Causes & Fixes:**

| Cause | Fix |
|-------|-----|
| `__NAMESPACE__` in resolver | Use full string path |
| DateTime object in data | Convert to string |
| Non-serializable object | Filter out or convert |
| WordPress internal meta | Filter out `_` prefix fields |
| Missing type reference | Ensure base types registered first |

### Missing Dynamic Content Dropdown

**Symptoms:** Source doesn't appear in dropdown

**Causes & Fixes:**

| Cause | Fix |
|-------|-----|
| YOOtheme not active | Check `function_exists('YOOtheme\app')` |
| Wrong event priority | Use `-10` for most sources |
| Syntax error in resolver | Check PHP error log |
| Missing `init` hook | Wrap in `add_action('init', ...)` |

### Fields Return Empty

**Symptoms:** Fields show placeholder or empty

**Causes & Fixes:**

| Cause | Fix |
|-------|-----|
| Meta not attached | Use `attach_post_meta()` |
| Wrong field name | Check schema matches meta key |
| Null value | Return `"\u{00A0}"` (non-breaking space) |

### Debug Logging

Enable in `theme-config.php`:

```php
'modules' => [
    'yootheme_dynamic_content' => [
        'debug' => true,
    ],
],
```

Check logs: `app/content/logs/app-YYYY-MM-DD.log`

---

## Anti-Patterns

### Creating Custom ObjectTypes for Content

```php
// WRONG - Breaks Dynamic Content dropdown
$source->objectType('MyCustomType', [
    'fields' => [...]
]);
```

**Fix:** Use auto-registered types from YOOthemeDynamicContentService:

```php
// CORRECT - Reference existing type
$source->queryType([
    'fields' => [
        'myQuery' => [
            'type' => ['listOf' => 'Artwork'],  // Use existing type
            // ...
        ],
    ],
]);
```

### Using __NAMESPACE__ in Resolvers

```php
// WRONG - Causes serialization issues
'func' => __NAMESPACE__ . '\\my_resolver',
```

**Fix:** Use explicit string:

```php
// CORRECT
'func' => 'ntdstheme\\services\\yootheme\\my_resolver',
```

### Returning DateTime Objects

```php
// WRONG - Breaks JSON serialization
return $post; // Contains DateTime in meta
```

**Fix:** Convert DateTime to string:

```php
// CORRECT
if ($value instanceof \DateTime) {
    $value = $value->format('Y-m-d H:i:s');
}
```

### Including WordPress Internal Meta

```php
// WRONG - May contain non-serializable data
$post->meta = get_post_meta($post->ID);
```

**Fix:** Filter internal fields:

```php
// CORRECT
foreach ($meta as $key => $value) {
    if (strpos($key, '_') === 0) {
        continue;  // Skip _edit_lock, _edit_last, etc.
    }
    $cleaned[$key] = $value;
}
```

### Class Methods as Resolvers

```php
// WRONG - Won't serialize
'func' => [$this, 'myResolver'],
```

**Fix:** Use standalone function:

```php
// CORRECT
function my_resolver($root, array $args) {
    // ...
}

// Reference:
'func' => 'namespace\\my_resolver',
```

### Missing Hook Wrapper

```php
// WRONG - May run before YOOtheme is loaded
Event::on('source.init', ...);
```

**Fix:** Wrap in init hook:

```php
// CORRECT
add_action('init', function () {
    if (!function_exists('YOOtheme\app')) {
        return;
    }
    Event::on('source.init', ..., -10);
});
```

---

## Quick Reference

### Creating a Custom Query Source

1. Create service with priority > 20
2. Wrap in `add_action('init', ...)`
3. Check `function_exists('YOOtheme\app')`
4. Use `Event::on('source.init', ..., -10)`
5. Define `queryType()` with existing types
6. Create resolver function (not method)
7. Use `attach_post_meta()` on returned posts

### Resolver Function Template

```php
function resolve_my_source($root, array $args)
{
    $posts = get_posts([
        'post_type' => 'my_type',
        'posts_per_page' => $args['limit'] ?? 10,
        'post_status' => 'publish',
    ]);

    return array_map(
        'ntdstheme\\services\\yootheme\\attach_post_meta',
        $posts
    );
}
```

### Service Template

```php
<?php
namespace ntdstheme\services\yootheme;

use YOOtheme\Event;

class MySourcesService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name' => 'My Sources',
            'priority' => 21,
        ];
    }

    public function __construct() { $this->init(); }

    private function init(): void
    {
        add_action('init', function () {
            if (!function_exists('YOOtheme\app')) return;

            Event::on('source.init', function ($source) {
                $source->queryType([
                    'fields' => [
                        'myQuery' => [
                            'type' => ['listOf' => 'ExistingType'],
                            'metadata' => ['label' => 'My Query', 'group' => 'My Group'],
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
    return array_map(
        'ntdstheme\\services\\yootheme\\attach_post_meta',
        get_posts(['post_type' => 'my_type', 'posts_per_page' => 10])
    );
}
```
