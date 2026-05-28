# NTDST Data ORM Cookbook

Complete guide to the NTDST Data Layer - a minimal, fast, cached ORM for WordPress.

---

## Table of Contents

1. [Global Helpers](#global-helpers)
2. [Model Registration](#model-registration)
3. [CRUD Operations](#crud-operations)
4. [Query Builder](#query-builder)
5. [Critical: find() vs get()](#critical-find-vs-get)
6. [Meta Operations](#meta-operations)
7. [Taxonomy Methods](#taxonomy-methods)
8. [Field Types Reference](#field-types-reference)
9. [Validation](#validation)
10. [Caching & Performance](#caching--performance)
11. [Anti-Patterns](#anti-patterns)

---

## Global Helpers

```php
ntdst_data()                              // Get Data Manager singleton
ntdst_data()->get('model')                // Get model instance
ntdst_data()->register(...)               // Register new model

ntdst_get_posts_fast($args)               // Direct fast query execution
ntdst_clear_posts_cache($id)              // Clear cache for post
ntdst_invalidate_post_type('portfolio')   // Invalidate all queries for post type
ntdst_query_cache()                       // Get QueryCache instance
```

---

## Model Registration

### Basic Registration

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio Items',
    'public' => true,
    'has_archive' => true,
    'supports' => ['title', 'editor', 'thumbnail'],
    'menu_icon' => 'dashicons-portfolio',
    'fields' => [
        'client_name' => 'text',
        'project_year' => 'integer',
        'featured' => 'boolean',
    ],
]);
```

### With Validation

```php
ntdst_data()->register('artwork', [
    'label' => 'Artworks',
    'public' => true,
    'fields' => [
        'title' => [
            'type' => 'text',
            'required' => true,
        ],
        'year_created' => [
            'type' => 'integer',
            'min' => 1900,
            'max' => 2100,
        ],
        'price' => [
            'type' => 'float',
            'min' => 0,
        ],
        'email' => [
            'type' => 'email',
            'required' => true,
            'validate' => fn($v) => filter_var($v, FILTER_VALIDATE_EMAIL)
                ? true
                : 'Invalid email format',
        ],
    ],
]);
```

### With Tabbed Metabox

```php
ntdst_data()->register('exhibition', [
    'label' => 'Exhibitions',
    'public' => true,
    'fields' => [
        'start_date' => 'text',
        'end_date' => 'text',
        'venue' => 'text',
        'description' => 'textarea',
        'gallery' => 'gallery',
    ],
    'field_groups' => [
        'dates' => [
            'title' => 'Dates',
            'fields' => ['start_date', 'end_date'],
        ],
        'venue' => [
            'title' => 'Venue',
            'fields' => ['venue', 'description'],
        ],
        'media' => [
            'title' => 'Media',
            'fields' => ['gallery'],
        ],
    ],
    'use_tabs' => true,
]);
```

### With Meta Prefix

Use `meta_prefix` to auto-prefix all meta keys (useful for avoiding collisions):

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio',
    'meta_prefix' => 'pf_',  // All meta stored with this prefix
    'fields' => [
        'client_name' => 'text',  // Stored as 'pf_client_name'
        'year' => 'integer',       // Stored as 'pf_year'
    ],
]);

// Access fields using unprefixed names (prefix applied automatically)
$model->getMeta($id, 'client_name');  // Reads 'pf_client_name'
$model->where('client_name', 'Acme')->get();  // Queries 'pf_client_name'
```

### Model Hooks

```php
// Before registration
add_action('ntdst/model/registering', function($name, $config) {
    // Modify config before registration
}, 10, 2);

// After registration
add_action('ntdst/model/registered', function($name, $config) {
    // Post-registration actions
}, 10, 2);

// Add fields dynamically
add_filter('ntdst/artwork/fields', function($fields) {
    $fields['custom_field'] = 'text';
    return $fields;
});

// Add field groups dynamically
add_filter('ntdst/artwork/field_groups', function($groups) {
    $groups['custom'] = [
        'title' => 'Custom',
        'fields' => ['custom_field'],
    ];
    return $groups;
});
```

---

## CRUD Operations

### Create

```php
$model = ntdst_data()->get('portfolio');

$result = $model->create([
    'title' => 'New Project',
    'content' => 'Project description...',
    'post_status' => 'publish',  // publish, draft, pending, private
    'client_name' => 'Acme Corp',
    'project_year' => 2024,
    'featured' => true,
]);

if (is_wp_error($result)) {
    ntdst_log()->error('Failed to create', [
        'error' => $result->get_error_message()
    ]);
    return $result;
}

// $result is WP_Post object with ->meta and ->fields attached
$post_id = $result->ID;
```

### Accepted keys — friendly vocabulary, NOT wp_posts column names

`create()` and `update()` accept the Data API's friendly vocabulary, not raw `wp_posts` column names. Passing the wrong vocabulary is silently dropped (and may be misclassified as meta).

| Pass this | Writes to wp_posts column |
|---|---|
| `title` | `post_title` |
| `content` | `post_content` |
| `excerpt` | `post_excerpt` |
| `post_status` | `post_status` |
| `post_author` | `post_author` |
| `post_parent` | `post_parent` |
| `post_date` / `post_date_gmt` | `post_date` / `post_date_gmt` |
| `post_name` | `post_name` (slug — auto-generated if omitted) |
| `menu_order` | `menu_order` |
| `comment_status`, `ping_status`, `post_password`, `post_content_filtered`, `to_ping`, `pinged` | passed through unchanged |

Full canonical list lives at `NTDST_Data_Model::WP_COLUMNS`.

**❌ Wrong vocabulary** (silently dropped before the WP_COLUMNS hardening; now also logged):

```php
$model->create([
    'post_title' => 'X',      // ❌ → dropped, may write _ntdst_post_title meta
    'post_content' => 'Y',    // ❌ → dropped
]);
```

**✅ Correct:**

```php
$model->create([
    'title'   => 'X',
    'content' => 'Y',
]);
```

### Warnings on unknown keys

Any key passed to `create()`/`update()` that is neither a registered schema field nor a recognized WP column is logged via `ntdst_log('data')->warning()` and dropped before the write. Watch `logs/data-YYYY-MM-DD.log` after refactors — zero warnings = clean vocabulary. Typos like `staart_date` (vs `start_date`) surface as warnings, not as silent failures.

### Read (find)

```php
$model = ntdst_data()->get('portfolio');

// Find by ID - returns WP_Post object
$project = $model->find(123);

// Skip cache (use after mutations for fresh data)
$project = $model->find(123, true);

if (is_wp_error($project)) {
    // Handle not found
}

// Access post properties
echo $project->post_title;
echo $project->post_content;

// Access meta via attached properties
echo $project->fields['client_name'];
echo $project->meta['project_year'];
```

### Update

```php
$model = ntdst_data()->get('portfolio');

$result = $model->update(123, [
    'title' => 'Updated Title',
    'featured' => false,
]);

if (is_wp_error($result)) {
    return $result;
}
```

### Delete

```php
$model = ntdst_data()->get('portfolio');

// Trash (soft delete)
$result = $model->delete(123);

// Force delete (bypass trash)
$result = $model->delete(123, true);

if (is_wp_error($result)) {
    return $result;
}
```

### CRUD Hooks

```php
// Before create
add_action('ntdst_model_create_before', function($post_type, $data) {
    // Modify data or perform checks
}, 10, 2);

// After create
add_action('ntdst_model_create_after', function($post_type, $post_id, $data) {
    // Post-creation actions (e.g., send notification)
}, 10, 3);

// Before update
add_action('ntdst_model_update_before', function($post_type, $id, $data) {
    // Pre-update checks
}, 10, 3);

// After update
add_action('ntdst_model_update_after', function($post_type, $id, $data) {
    // Post-update actions
}, 10, 3);

// Before delete
add_action('ntdst_model_delete_before', function($post_type, $id) {
    // Cleanup related data
}, 10, 2);

// After delete
add_action('ntdst_model_delete_after', function($post_type, $id) {
    // Post-deletion cleanup
}, 10, 2);
```

---

## Query Builder

### Basic Queries

```php
$model = ntdst_data()->get('portfolio');

// Get all (default limit: 10)
$projects = $model->get();

// Get all with no limit
$projects = $model->all(-1);

// Limit results
$projects = $model->limit(5)->get();

// Order results
$projects = $model->orderBy('date', 'DESC')->get();
$projects = $model->orderBy('title', 'ASC')->get();
$projects = $model->orderBy('menu_order', 'ASC')->get();
```

### Where Clauses

```php
// Simple equality
$projects = $model->where('featured', true)->get();
$projects = $model->where('client_name', 'Acme Corp')->get();

// Comparison operators
$projects = $model->where('price', ['>', 1000])->get();
$projects = $model->where('price', ['<=', 5000])->get();
$projects = $model->where('year', ['>=', 2020])->get();

// NOT equal — for meta fields, builds meta_query with '!='.
// For core fields, only post_status, post_author, post_parent are supported.
// Any other core field throws InvalidArgumentException (and resets the
// builder so the next call on the same model starts clean).
$projects = $model->whereNot('post_status', 'trash')->get();
$projects = $model->whereNot('archived', true)->get();

// where('post_name', ...) is mapped to WP_Query's `name` automatically —
// use the column name (post_name), not WP_Query's slug alias.
$post = $model->where('post_name', 'hello-world')->first();

// IN clause (for post IDs)
$projects = $model->whereIn('ID', [1, 2, 3])->get();

// OR clause — flips the ENTIRE meta_query into one flat OR group.
// Cannot express nested clauses like "A AND (B OR C)".
$projects = $model
    ->where('featured', true)
    ->orWhere('price', ['<', 100])
    ->get();
```

### Builder state reset

`get()`, `count()`, and `paginate()` reset `$this->query_args = []` in a `finally` block. `ntdst_data()->get($name)` returns the same singleton model instance, so without the reset a `where()` chain would bleed into the next caller's query. `first()` and `all()` delegate to `get()` and inherit the reset.

```php
$model = ntdst_data()->get('artwork');

// Both calls are independent — the second is not constrained by 'oil'.
$oils = $model->where('medium', 'oil')->get();
$all  = $model->get();
```

### Taxonomy Queries

```php
// Single term (by slug)
$projects = $model->whereTax('category', 'web-design')->get();

// Single term (by ID)
$projects = $model->whereTax('category', 5, 'term_id')->get();

// Multiple terms (OR)
$projects = $model->whereTax('category', ['web', 'mobile'], 'slug', 'IN')->get();

// Multiple terms (AND - must have all)
$projects = $model->whereTax('category', ['web', 'mobile'], 'slug', 'AND')->get();

// NOT IN
$projects = $model->whereTax('category', ['archived'], 'slug', 'NOT IN')->get();
```

### Date Queries

```php
// After date
$projects = $model->whereDate('post_date', '>=', '2024-01-01')->get();

// Before date
$projects = $model->whereDate('post_date', '<', '2024-12-31')->get();

// Between dates
$projects = $model->whereDate('post_date', 'BETWEEN', ['2024-01-01', '2024-06-30'])->get();

// Modified date
$projects = $model->whereDate('post_modified', '>=', '2024-01-01')->get();
```

### Including Meta and Terms

```php
// Include all post meta
$projects = $model->withMeta()->get();

// Include taxonomy terms
$projects = $model->withTerms()->get();

// Both
$projects = $model->withMeta()->withTerms()->get();
```

### Pagination

```php
// Get paginated results
$result = $model->where('featured', true)->paginate($page = 1, $per_page = 10);

// Result structure:
// [
//     'data' => [...posts...],
//     'pagination' => [
//         'total' => 45,
//         'per_page' => 10,
//         'current_page' => 1,
//         'total_pages' => 5,
//         'from' => 1,
//         'to' => 10,
//     ],
// ]

// Access data
foreach ($result['data'] as $project) {
    echo $project['title'];
}

// Pagination info
echo "Page {$result['pagination']['current_page']} of {$result['pagination']['total_pages']}";
```

### Count

```php
$count = $model->where('featured', true)->count();
```

### First Result

```php
// Returns WP_Post (same shape as find()) or null
$featured = $model->where('featured', true)->first();

if ($featured !== null) {
    echo $featured->post_title;
    echo $featured->fields['price'];
}
```

`first()` is hydrated through the same path as `find()` — `->meta` and `->fields` are populated.

---

## Critical: find() vs get()

**This is the most common source of bugs!**

### Return Type Differences

| Method | Returns | Access Pattern |
|--------|---------|----------------|
| `find($id)` | `WP_Post` object (with `->meta`, `->fields`) or `WP_Error` | `$post->post_title`, `$post->fields['key']` |
| `first()` | `WP_Post` object (same shape as `find()`) or `null` | `$post->post_title`, `$post->fields['key']` |
| `get()` | `array` of arrays | `$posts[0]['title']` |
| `ntdst_get_posts_fast()` | `array` of arrays | `$posts[0]['title']` |

### WRONG - Array Access on WP_Post

```php
// WRONG!
$post = $model->find($id);
$title = $post['title'];  // FATAL ERROR: Cannot use object as array
```

### CORRECT - Object Access on WP_Post

```php
// CORRECT - find() returns WP_Post
$post = $model->find($id);
$title = $post->post_title;
$content = $post->post_content;

// Meta via attached properties
$client = $post->fields['client_name'];
$meta = $post->meta['any_meta_key'];
```

### CORRECT - Array Access with get()

```php
// CORRECT - get() returns array of arrays
$posts = $model->where('featured', true)->withMeta()->get();

foreach ($posts as $post) {
    echo $post['title'];
    echo $post['meta']['client_name'];
}
```

### CORRECT - Array Access with ntdst_get_posts_fast()

```php
// CORRECT - ntdst_get_posts_fast() returns array with meta
$posts = ntdst_get_posts_fast([
    'post_type' => 'portfolio',
    'posts_per_page' => 5,
    'include_meta' => true,
]);

foreach ($posts as $post) {
    echo $post['id'];
    echo $post['title'];
    echo $post['meta']['client_name'];
}
```

---

## Meta Operations

### Get Meta

```php
$model = ntdst_data()->get('portfolio');

// Get single meta value
$client = $model->getMeta(123, 'client_name');

// Get with default value
$price = $model->getMeta(123, 'price', 0);

// Get all meta
$all_meta = $model->getMeta(123);
```

### Update Meta

```php
$model = ntdst_data()->get('portfolio');

// Single field
$result = $model->updateMeta(123, 'client_name', 'New Client');

if (is_wp_error($result)) {
    // Handle error
}
// Note: WordPress's update_post_meta returns false BOTH on errors AND when
// the value is unchanged. The data layer verifies the stored value after a
// false return and treats unchanged values as success — so a no-op save no
// longer triggers a spurious WP_Error.

// Batch update (multiple fields, single cache clear)
$model->updateMetaBatch(123, [
    'client_name' => 'New Client',
    'project_year' => 2025,
    'featured' => true,
]);
```

### Delete Meta

```php
$model = ntdst_data()->get('portfolio');

$model->deleteMeta(123, 'temporary_field');
```

### Model Introspection

```php
$model = ntdst_data()->get('portfolio');

// Get field schema definitions
$schema = $model->getSchema();
// ['client_name' => 'text', 'year' => ['type' => 'integer', 'min' => 1900], ...]

// Get meta prefix (if configured)
$prefix = $model->getMetaPrefix();
// e.g., 'pf_' - all meta keys are prefixed automatically
```

---

## Taxonomy Methods

### Attach Terms (Add)

```php
$model = ntdst_data()->get('portfolio');

// Add terms (keeps existing)
$model->attachTerms(123, 'category', [1, 2, 3]);
```

### Sync Terms (Replace)

```php
// Replace all terms
$model->syncTerms(123, 'category', [4, 5]);
```

### Detach Terms (Remove)

```php
// Remove specific terms
$model->detachTerms(123, 'category', [1, 2]);

// Remove all terms
$model->detachTerms(123, 'category', []);
```

---

## Field Types Reference

### Basic Types

| Type | Sanitizer | PHP Type |
|------|-----------|----------|
| `text` | `sanitize_text_field` | `string` |
| `textarea` | `sanitize_textarea_field` | `string` |
| `email` | `sanitize_email` | `string` |
| `url` | `esc_url_raw` | `string` |
| `html` / `content` | `wp_kses_post` | `string` |

### Numeric Types

| Type | Sanitizer | PHP Type |
|------|-----------|----------|
| `integer` / `int` | `absint` | `int` |
| `float` / `double` | `floatval` | `float` |
| `boolean` / `bool` | `(bool)` cast | `bool` |

### Complex Types

| Type | Description | PHP Type |
|------|-------------|----------|
| `array` | Simple array (sanitized) | `array` |
| `json` | JSON data | `array` |
| `relation` | Post IDs (single or array) | `array` |
| `gallery` | Attachment IDs | `array` |
| `repeater` | Array of row arrays | `array` |

### Field Definition Examples

```php
'fields' => [
    // Simple definition
    'client_name' => 'text',
    'description' => 'textarea',
    'website' => 'url',

    // With validation
    'email' => [
        'type' => 'email',
        'required' => true,
    ],

    'price' => [
        'type' => 'float',
        'min' => 0,
        'max' => 100000,
    ],

    'rating' => [
        'type' => 'integer',
        'min' => 1,
        'max' => 5,
    ],

    // Relation to other posts
    'related_artists' => [
        'type' => 'relation',
        'post_type' => 'artist',
    ],

    // Gallery of images
    'images' => 'gallery',

    // Repeater (e.g., social links)
    'social_links' => 'repeater',

    // Custom validation
    'phone' => [
        'type' => 'text',
        'validate' => function($value) {
            if (!preg_match('/^[+]?[\d\s-]+$/', $value)) {
                return 'Invalid phone number format';
            }
            return true;
        },
    ],
],
```

---

## Validation

### Automatic Validation

Validation runs automatically on `create()` and `update()`:

```php
$result = $model->create([
    'title' => '',  // Required field empty
    'price' => -100, // Below min
]);

if (is_wp_error($result)) {
    echo $result->get_error_message();
    // "title is required; price must be at least 0"

    // Get detailed errors
    $errors = $result->get_error_data()['errors'];
    // ['title' => ['title is required'], 'price' => ['price must be at least 0']]
}
```

### Validation Options

```php
'fields' => [
    'field_name' => [
        'type' => 'text',
        'required' => true,           // Must have value
        'min' => 5,                   // Min length (string), min value (number), min items (array)
        'max' => 100,                 // Max length (string), max value (number), max items (array)
        'validate' => fn($v) => ...,  // Custom validation callback
    ],
],
```

### Custom Validation

```php
'email' => [
    'type' => 'email',
    'validate' => function($value) {
        // Must return true or error message string
        if (!str_ends_with($value, '@company.com')) {
            return 'Must be a company email address';
        }
        return true;
    },
],
```

---

## Caching & Performance

### Default Caching

All queries are cached for 1 hour by default:

```php
// Default cache: 3600 seconds (1 hour)
$posts = $model->get();
```

### Custom Cache Duration

```php
// Cache for 2 hours
$posts = $model->cache(7200)->get();

// No caching
$posts = $model->cache(0)->get();
```

### Cache Clearing

```php
// Clear cache for specific post (meta and terms)
ntdst_clear_posts_cache(123);

// Clear all query caches (if supported by cache backend)
ntdst_clear_posts_cache(null);

// Invalidate all cached queries for a post type (version-based)
ntdst_invalidate_post_type('portfolio');
```

### QueryCache

The `NTDST_Query_Cache` class handles intelligent caching:

- **Environment-aware**: caching disabled when `WP_DEBUG` is true (unless `NTDST_ENABLE_CACHE_IN_DEBUG` is defined). The `resolveCacheTime()` helper is the single source of truth for the dev-zero rule and is called by every data-layer entry point.
- **Version-based invalidation**: atomic `wp_cache_incr` per post type, cheaper than enumerating keys.
- **`count()` and `paginate()` are cached.** Both halves of `paginate()` (count + data) share the same versioned bucket. Older revisions bypassed the cache for counts.
- **Configurable**: override cache time per-query with `->cache($seconds)`.
- **Meta-prefix-aware invalidation.** Every model registers its `meta_prefix` (e.g. `_ntdst_`) at construction time. Direct `update_post_meta($id, '_ntdst_foo', ...)` calls outside the ORM still bust the cache. `_thumbnail_id`, `_price`, `_stock`, `_stock_status` are always-invalidating; add others via `ntdst_should_invalidate_meta`.

```php
// Access QueryCache directly (rarely needed)
$cache = ntdst_query_cache();
$cache->invalidatePostType('portfolio');  // Bump version, invalidate queries

// Add a meta key to the always-invalidate list
add_filter('ntdst_should_invalidate_meta', function ($should, $meta_key) {
    return $should || $meta_key === '_my_volatile_key';
}, 10, 2);
```

### Stale-cache cleanup on external deletes

When `find()` / `first()` discover that `get_post($id)` returns null (post deleted directly via SQL or `wp_delete_post()` outside the model), the data layer proactively clears the manager's cached meta/terms entries for that ID. No stale `post_meta_{id}` left behind.

### Fast Query Function

For optimal performance, use `ntdst_get_posts_fast()` directly:

```php
$posts = ntdst_get_posts_fast([
    'post_type' => 'portfolio',
    'posts_per_page' => 20,
    'post_status' => 'publish',
    'orderby' => 'date',
    'order' => 'DESC',
    'include_meta' => true,      // Include all meta
    'include_terms' => true,     // Include taxonomy terms
    'cache_time' => 3600,        // Cache duration (0 = no cache)

    // Standard WP_Query args also work:
    'meta_query' => [...],
    'tax_query' => [...],
]);
```

### Performance Tips

1. **Use `include_meta` only when needed** - it primes the meta cache
2. **Set appropriate limits** - avoid `posts_per_page => -1`
3. **Use `cache()` for expensive queries**
4. **Prime caches before loops** - see "Batch Loading" below

### Batch Loading (Avoid N+1)

```php
// WRONG - N+1 queries
$posts = $model->get();
foreach ($posts as $post) {
    $meta = get_post_meta($post['id'], 'field', true);  // Query per iteration!
}

// CORRECT - Batch load
$posts = $model->withMeta()->get();  // Meta included in single query
foreach ($posts as $post) {
    $meta = $post['meta']['field'];  // From cached data
}

// CORRECT - Manual batch priming
$posts = get_posts(['post_type' => 'portfolio']);
$post_ids = wp_list_pluck($posts, 'ID');
update_postmeta_cache($post_ids);  // Prime cache once

foreach ($posts as $post) {
    $meta = get_post_meta($post->ID, 'field', true);  // Served from cache
}
```

---

## Anti-Patterns

### Raw SQL Queries

```php
// WRONG - Direct database access
global $wpdb;
$results = $wpdb->get_results("SELECT * FROM {$wpdb->posts} WHERE post_type = 'portfolio'");

// CORRECT - Use Data ORM
$results = ntdst_data()->get('portfolio')->get();
```

### N+1 Query Pattern

```php
// WRONG - Query per iteration
foreach ($posts as $post) {
    $client = get_post_meta($post->ID, 'client_name', true);
}

// CORRECT - Batch load meta
$posts = ntdst_data()->get('portfolio')->withMeta()->get();
foreach ($posts as $post) {
    $client = $post['meta']['client_name'];
}
```

### Unbounded Queries

```php
// WRONG - No limit (dangerous on large sites)
$all_posts = ntdst_data()->get('portfolio')->all(-1);

// CORRECT - Always limit or paginate
$posts = ntdst_data()->get('portfolio')->limit(100)->get();
$paginated = ntdst_data()->get('portfolio')->paginate(1, 20);
```

### Treating find() as Array

```php
// WRONG - find() returns WP_Post object
$post = $model->find($id);
echo $post['title'];  // ERROR!

// CORRECT
echo $post->post_title;
```

### Not Checking WP_Error

```php
// WRONG - No error check
$post = $model->create($data);
$id = $post->ID;  // May fail if $post is WP_Error

// CORRECT - Always check
$post = $model->create($data);
if (is_wp_error($post)) {
    ntdst_log()->error('Create failed', ['error' => $post->get_error_message()]);
    return $post;
}
$id = $post->ID;
```

### Ignoring Validation Errors

```php
// WRONG - Validation errors not returned
$model->create($data);

// CORRECT - Check and return errors
$result = $model->create($data);
if (is_wp_error($result)) {
    return $result;  // Let caller handle validation errors
}
```

### Using 'status' Instead of 'post_status'

```php
// WRONG - 'status' may collide with custom meta field named 'status'
$model->create(['title' => 'Test', 'status' => 'publish']);

// CORRECT - Use 'post_status' for WordPress post status
$model->create(['title' => 'Test', 'post_status' => 'publish']);
```

### Multiple updateMeta Calls

```php
// WRONG - Multiple cache clears, inefficient
$model->updateMeta($id, 'field1', 'value1');
$model->updateMeta($id, 'field2', 'value2');
$model->updateMeta($id, 'field3', 'value3');

// CORRECT - Single cache clear
$model->updateMetaBatch($id, [
    'field1' => 'value1',
    'field2' => 'value2',
    'field3' => 'value3',
]);
```

---

## Quick Reference

### Common Patterns

```php
// Get model
$model = ntdst_data()->get('my_type');

// Create with validation
$result = $model->create($data);
if (is_wp_error($result)) return $result;

// Find single post (WP_Post)
$post = $model->find($id);
$title = $post->post_title;
$meta = $post->fields['field_name'];

// Query multiple (arrays)
$posts = $model->where('featured', true)->withMeta()->limit(10)->get();
foreach ($posts as $post) {
    echo $post['title'];
    echo $post['meta']['field_name'];
}

// Paginate
$result = $model->paginate($page, $per_page);
$posts = $result['data'];
$total = $result['pagination']['total'];

// Update
$result = $model->update($id, ['field' => 'value']);

// Delete
$result = $model->delete($id);
```
