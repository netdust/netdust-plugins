# Data Layer Reference

## Model Registration

```php
ntdst_data()->register('artwork', [
    // WordPress post type args
    'label'       => 'Artworks',
    'public'      => true,
    'has_archive' => true,
    'supports'    => ['title', 'editor', 'thumbnail'],

    // NTDST-specific
    'meta_prefix' => '_art_',     // prefixes all meta keys in DB
    'cache_time'  => 3600,        // seconds (0 in WP_DEBUG)

    'fields' => [
        'medium'     => 'text',
        'dimensions' => 'text',
        'price'      => ['type' => 'float', 'required' => true, 'min' => 0],
        'year'       => 'integer',
        'featured'   => 'boolean',
        'images'     => ['type' => 'gallery', 'description' => 'Artwork images'],
        'artist'     => ['type' => 'relation', 'post_type' => 'artist', 'multiple' => false],
        'tags'       => 'array',
        'details'    => 'json',
        'bio'        => 'html',
        'slides'     => [
            'type' => 'repeater',
            'sub_fields' => [
                'image_url'   => ['type' => 'url'],
                'caption'     => ['type' => 'text'],
                'sort_order'  => ['type' => 'integer'],
            ],
        ],
    ],

    // Optional: group fields into separate metaboxes or tabs
    'field_groups' => [
        'details' => [
            'title'  => 'Artwork Details',
            'fields' => ['medium', 'dimensions', 'price', 'year'],
        ],
        'relations' => [
            'title'  => 'Relationships',
            'fields' => ['artist', 'images'],
        ],
    ],
    'use_tabs' => true,  // render field_groups as tabs instead of separate metaboxes
]);
```

### Field Types

| Type | PHP Cast | Sanitizer |
|------|----------|-----------|
| `text` / `string` | `(string)` | `sanitize_text_field` |
| `textarea` | `(string)` | `sanitize_textarea_field` |
| `html` / `content` | `(string)` | `wp_kses_post` |
| `int` / `integer` | `(int)` | `absint` |
| `float` / `double` | `(float)` | `floatval` |
| `bool` / `boolean` | `(bool)` | cast |
| `email` | `(string)` | `sanitize_email` |
| `url` | `(string)` | `esc_url_raw` |
| `array` | `array` | `array_map('sanitize_text_field')` |
| `json` | `array` | json decode |
| `relation` | `int[]` | `array_map('absint')` |
| `gallery` | `int[]` | `array_map('absint')` |
| `repeater` | `array[]` | per sub-field sanitization |
| `date` | input type=date | |
| `datetime` | input type=datetime-local | |
| `select` | string | options array required |
| `callback` | — | custom render callback |

### Validation (in field config array)

```php
'price' => [
    'type'     => 'float',
    'required' => true,
    'min'      => 0,
    'max'      => 999999,
    'validate' => fn($v) => $v > 0 ? true : 'Price must be positive',
],
```

---

## CRUD Operations

```php
$model = ntdst_data()->get('artwork');

// CREATE — returns WP_Post with ->fields or WP_Error
$artwork = $model->create([
    'title'   => 'Sunset',
    'content' => 'Oil on canvas',
    'medium'  => 'oil',
    'price'   => 2500.00,
    'post_status' => 'publish',  // use 'post_status' not 'status'
]);

// FIND — returns WP_Post with ->meta and ->fields, or WP_Error
$artwork = $model->find(42);
$artwork->post_title;          // WP_Post property
$artwork->fields['price'];     // typed, formatted meta value
$artwork->fields['artist'];    // relation: int[]
$artwork->meta;                // raw meta array

// UPDATE — returns WP_Post or WP_Error
$updated = $model->update(42, ['price' => 3000.00]);

// DELETE — returns true or WP_Error
$model->delete(42);            // trash
$model->delete(42, true);      // force delete
```

### Meta Convenience Methods

```php
$price  = $model->getMeta(42, 'price');            // single field
$all    = $model->getMeta(42);                     // all fields
$model->updateMeta(42, 'price', 3500.00);          // single field
$model->updateMetaBatch(42, [                      // multiple fields, one cache clear
    'price'  => 3500.00,
    'medium' => 'acrylic',
]);
$model->deleteMeta(42, 'temporary_note');
```

### Taxonomy Terms

```php
$model->attachTerms(42, 'artwork_type', [1, 2, 3]);        // append
$model->syncTerms(42, 'artwork_type', [1, 2, 3]);          // replace all
$model->detachTerms(42, 'artwork_type', [2]);               // remove specific
$model->detachTerms(42, 'artwork_type', []);                // remove all
```

### CRITICAL: Return Types

| Method | Returns |
|--------|---------|
| `find($id)` | `WP_Post` object (with `->fields`, `->meta`) or `WP_Error` |
| `create($data)` | `WP_Post` object or `WP_Error` |
| `update($id, $data)` | `WP_Post` object or `WP_Error` |
| `get()` | `array` of associative arrays (not objects) |
| `first()` | `WP_Post` object (same shape as `find()` — `->meta`, `->fields`) or `null` |
| `all()` | `array` of associative arrays |
| `count()` | `int` (cached via `NTDST_Query_Cache`) |
| `paginate()` | `['data' => [...], 'pagination' => [...]]` (both halves cached) |

**Always check `is_wp_error()` on find/create/update.**

`first()` returns the same shape as `find()`, not a `stdClass`. Access `$post->post_title`, `$post->fields['price']`, etc. — never `$post->title` / `$post->id`.

### Atomicity of `create()` / `update()`

Meta-write failures trigger an **application-level rollback** (best-effort, not a DB transaction):

- `create()` snapshots nothing — on meta-write failure it `wp_delete_post`s the new post and returns `WP_Error`.
- `update()` snapshots the affected post-table fields and each meta field (`exists` flag + previous value) *before* writing, and calls `restorePostData()` / `restoreMetaData()` on any failure.

This is best-effort: rollback writes can themselves fail under DB stress. For multi-table critical paths (capacity locks, voucher counts), wrap the whole business operation in `$wpdb->query('START TRANSACTION')` at the service layer — see `EnrollmentService::enroll()` in Stride for the pattern.

WordPress returns `false` from `update_post_meta` both on errors *and* on unchanged values. The data layer's `updateMetaValue()` verifies the stored value after a `false` return and treats unchanged values as success — so updating to the same value no longer triggers a spurious rollback.

### Builder state reset

`get()`, `count()`, and `paginate()` reset `$this->query_args = []` in a `finally` block. This matters because `ntdst_data()->get($name)` returns the same singleton instance — without the reset, a `where()` chain on one call would bleed into the next caller's query. `first()` and `all()` delegate to `get()`, so they inherit the reset.

`whereNot()` on an unsupported core field throws `InvalidArgumentException` (instead of silently returning wrong results) and resets `query_args` before throwing, so the next call on the same model starts clean. Supported negations: `post_status`, `post_author`, `post_parent`.

---

## Query Builder

```php
$model = ntdst_data()->get('artwork');

// Where (meta fields auto-prefixed)
$model->where('medium', 'oil')
      ->where('price', ['>=', 1000])
      ->get();

// Core WP fields (no prefix): post_status, post_author, post_parent, etc.
$model->where('post_status', 'draft')->get();

// post_name is mapped to WP_Query's `name` automatically — write the column
// name you expect (post_name), not WP_Query's slug alias.
$model->where('post_name', 'hello-world')->first();

// whereNot
$model->whereNot('post_status', 'trash')->get();
$model->whereNot('medium', 'digital')->get();

// whereIn
$model->whereIn('ID', [1, 2, 3])->get();

// OR condition
$model->where('featured', true)
      ->orWhere('price', ['<', 100])
      ->get();

// NOTE: orWhere() flips the entire meta_query into a flat OR group. It cannot
// express nested clauses like "A AND (B OR C)". For nested groups, build the
// meta_query manually and pass it via a custom where().

// Taxonomy
$model->whereTax('artwork_type', 'sculpture')->get();
$model->whereTax('artwork_type', ['sculpture', 'painting'], 'slug', 'AND')->get();

// Date
$model->whereDate('post_date', '>=', '2024-01-01')->get();
$model->whereDate('post_date', 'BETWEEN', ['2024-01-01', '2024-12-31'])->get();

// Ordering
$model->orderBy('date', 'DESC')->get();                    // core field
$model->orderBy('price', 'DESC', numeric: true)->get();    // meta field

// Limit
$model->limit(20)->get();

// Include meta/terms in results
$model->withMeta()->withTerms()->get();

// Custom cache time
$model->cache(7200)->get();   // 2 hours
$model->cache(0)->get();      // no cache

// Pagination
$result = $model->where('medium', 'oil')->paginate(page: 2, per_page: 12);
// $result['data'] = [...], $result['pagination'] = [total, per_page, current_page, ...]

// First result
$item = $model->where('featured', true)->first();

// Count
$total = $model->where('medium', 'oil')->count();
```

---

## Query Cache (`NTDST_Query_Cache`)

- Deterministic keys: sorted args + md5 hash + version number
- Version-based invalidation per post type (atomic increment via `wp_cache_incr`)
- Auto-invalidation on `save_post`, `delete_post`, `trashed_post`, meta changes
- **`count()` and `paginate()` now go through QueryCache too** — both halves of `paginate()` (total + data) hit the same versioned bucket. Older revisions of the data layer bypassed the cache for counts.
- Meta-change invalidation respects each model's registered `meta_prefix`. Calling `update_post_meta($id, '_ntdst_foo', ...)` directly (outside the ORM) still busts the cache because the model registered `_ntdst_` (or its custom prefix) at construction time. `_thumbnail_id`, `_price`, `_stock`, and `_stock_status` are also always-invalidating. Filter `ntdst_should_invalidate_meta` to add others.
- Dev mode: cache disabled when `WP_DEBUG` is true (unless `NTDST_ENABLE_CACHE_IN_DEBUG`)

```php
// Manual invalidation
ntdst_invalidate_post_type('artwork');

// Check if caching enabled
ntdst_query_cache()->isCachingEnabled();

// Extend the always-invalidate list
add_filter('ntdst_should_invalidate_meta', function ($should, $meta_key) {
    if ($meta_key === '_my_custom_volatile_key') return true;
    return $should;
}, 10, 2);
```

### Stale-cache cleanup on external deletes

`find()` and `hydratePostFromResult()` proactively call `NTDST_Data_Manager::clearCache($id)` when `get_post($id)` returns null — so a post deleted directly via SQL or `wp_delete_post()` outside the model doesn't leave a stale meta/terms cache entry behind.

---

## Metabox Generator

Auto-generates admin metaboxes from field definitions. Handles:
- Single metabox (all fields)
- Grouped metaboxes (via `field_groups`)
- Tabbed interface (via `use_tabs => true`)
- Relation fields with autocomplete search
- Gallery fields with drag-and-drop reorder
- Repeater fields with sortable rows
- Read-only/computed fields

Saving uses Data.php ORM for registered models, falls back to `update_post_meta()` for native post types.

Set `'auto_metabox' => false` in config to handle metabox rendering manually in your service.

The "is this an ORM-backed model?" check now uses MetaboxGenerator's own registry instead of calling `ntdst_data()->get($name)` — that call had a side effect of auto-creating a phantom empty model, which would persist across the request and shadow later schema-bearing registrations. Iterate post types defensively with `NTDST_Data_Manager::isRegistered($name)`:

```php
// Safe — does not auto-create a phantom model entry.
if (ntdst_data()->isRegistered('artwork')) {
    $schema = ntdst_data()->get('artwork')->getSchema();
}
```

---

## Hooks

```php
// Before/after model registration
do_action('ntdst/model/registering', $name, $config);
do_action('ntdst/model/registered', $name, $config);

// Before/after CRUD
do_action('ntdst_model_create_before', $post_type, $data);
do_action('ntdst_model_create_after', $post_type, $post_id, $data);
do_action('ntdst_model_update_before', $post_type, $id, $data);
do_action('ntdst_model_update_after', $post_type, $id, $data);
do_action('ntdst_model_delete_before', $post_type, $id);
do_action('ntdst_model_delete_after', $post_type, $id);

// Field injection
apply_filters("ntdst/{$name}/fields", $fields);
apply_filters("ntdst/{$name}/field_groups", $field_groups);

// Metabox saved
do_action("ntdst/metabox_saved/{$model_name}", $post_id, $data);
```
