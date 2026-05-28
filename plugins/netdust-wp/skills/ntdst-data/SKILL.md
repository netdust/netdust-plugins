---
name: ntdst-data
description: >
  NTDST framework data layer, ORM, and API patterns. Use when planning,
  designing, or implementing data models, custom post types, field definitions,
  metaboxes, REST API endpoints, database queries, or CRUD operations. MUST be
  consulted during implementation planning to ensure Data Manager usage,
  correct return types, API handler structure, and caching strategy. Activates
  alongside ntdst-architecture for any data-related work.
---

# NTDST Data Layer — Domain Knowledge

Use when creating data models, custom post types, field definitions, metaboxes, API endpoints, database queries, or CRUD operations in the NTDST framework.

## Essential Principles

### Zero Raw SQL
All database operations go through `ntdst_data()`. Never use `$wpdb` directly.
Never use `get_post_meta()` / `update_post_meta()` directly — use Data Manager.

### JavaScript API Client
Never use `fetch()` directly. Always use `ntdstAPI.call()`.

### WP_Error on Failure
Every create/update/delete must check `is_wp_error($result)` and propagate errors.

### Use `post_status` Not `status`
For WordPress post status, always use `post_status` key (not `status`) to avoid collision with custom meta fields named `status`.

## Data Manager API

```php
$model = ntdst_data()->get('portfolio');

// CRUD
$post   = $model->create($data);        // Returns WP_Post or WP_Error
$post   = $model->find($id);            // Returns WP_Post (object access)
$post   = $model->find($id, true);      // Skip cache (use after mutations)
$result = $model->update($id, $data);   // Returns WP_Post or WP_Error
$result = $model->delete($id);          // Soft delete (trash)
$result = $model->delete($id, true);    // Force delete

// Meta operations
$value = $model->getMeta($id, 'field');           // Single field
$all   = $model->getMeta($id);                    // All meta
$model->updateMeta($id, 'field', $value);         // Single field
$model->updateMetaBatch($id, ['a' => 1, 'b' => 2]); // Batch update (single cache clear)
$model->deleteMeta($id, 'field');

// Query builder
$posts = $model->where('featured', true)->withMeta()->limit(10)->get();
$posts = $model->whereTax('category', 'web-design')->get();
$posts = $model->where('price', ['>', 1000])->orderBy('date', 'DESC')->get();
$page  = $model->paginate($page, $per_page);
$count = $model->where('featured', true)->count();
$first = $model->where('featured', true)->first();

// Model introspection
$schema = $model->getSchema();       // Get field definitions
$prefix = $model->getMetaPrefix();   // Get meta key prefix
```

## Global Helpers

```php
ntdst_data()                          // Data Manager singleton
ntdst_data()->isRegistered($name)     // Has a model been registered? (no side effect)
ntdst_get_posts_fast($args)           // Direct fast query
ntdst_clear_posts_cache($id)          // Clear cache for post
ntdst_invalidate_post_type('portfolio') // Invalidate all queries for post type
ntdst_query_cache()                   // Get QueryCache instance
```

`isRegistered()` is the safe way to check whether a model exists when iterating over post types — `ntdst_data()->get($name)` will auto-create an empty model entry as a side effect, which would persist and shadow a later schema-bearing registration.

## CRITICAL: find() vs get() Return Types

| Method | Returns | Access |
|--------|---------|--------|
| `find($id)` | `WP_Post` object (with `->meta`, `->fields`) or `WP_Error` | `$post->post_title`, `$post->fields['key']` |
| `first()` | `WP_Post` object (same shape as `find()`) or `null` | `$post->post_title`, `$post->fields['key']` |
| `get()` | Array of associative arrays | `$posts[0]['title']`, `$posts[0]['meta']['key']` |
| `count()` | `int` (cached via QueryCache) | — |
| `paginate()` | `['data' => [...], 'pagination' => [...]]` (both halves cached) | — |

`first()` and `find()` are now interchangeable in shape — both return WP_Post with `->fields` populated. Code that accessed `$item->id` (lowercase) on the old stdClass-cast `first()` result needs to become `$item->ID` (WP_Post property).

**Most common bug:** Treating `find()` result as array → fatal error.

```php
// WRONG
$post = $model->find($id);
$title = $post['title'];  // FATAL ERROR

// CORRECT
$post = $model->find($id);
if (is_wp_error($post)) {
    return $post; // Or handle the error.
}
$title  = $post->post_title;
$client = $post->fields['client_name'];

// first() — same access pattern; null when no rows match.
$featured = $model->where('featured', true)->first();
if ($featured !== null) {
    $title = $featured->post_title;
}
```

### Atomic create/update (best-effort)

`create()` and `update()` roll back on meta-write failure. `create()` deletes the new post if any meta write fails. `update()` snapshots prior post-table fields and meta state, then restores via `restorePostData()` / `restoreMetaData()` on failure. This is application-level rollback, not a DB transaction — for critical multi-table paths (capacity locks, voucher counts) still wrap the whole business operation in `$wpdb->query('START TRANSACTION')`.

`update_post_meta` returns `false` both on errors and on unchanged values. The data layer treats unchanged values as success, so re-saving the same value doesn't trigger a spurious rollback.

## Model Registration

```php
ntdst_data()->register('portfolio', [
    'label'       => 'Portfolio Items',
    'public'      => true,
    'has_archive' => true,
    'supports'    => ['title', 'editor', 'thumbnail'],
    'fields'      => [
        'client_name' => 'text',
        'year'        => 'integer',
        'featured'    => 'boolean',
        'price'       => ['type' => 'float', 'min' => 0],
        'email'       => ['type' => 'email', 'required' => true],
        'images'      => 'gallery',
        'related'     => ['type' => 'relation', 'post_type' => 'artist'],
        'links'       => 'repeater',
    ],
    'field_groups' => [
        'basic' => ['title' => 'Basic Info', 'fields' => ['client_name', 'year']],
        'media' => ['title' => 'Media', 'fields' => ['images']],
    ],
    'use_tabs' => true,
]);
```

Metaboxes are auto-generated from field definitions. Tabbed interface via `use_tabs`.

## Field Types

| Type | Sanitizer | Admin UI |
|------|-----------|----------|
| `text` | `sanitize_text_field` | Text input |
| `textarea` | `sanitize_textarea_field` | Textarea |
| `email` | `sanitize_email` | Email input |
| `url` | `esc_url_raw` | URL input |
| `html` | `wp_kses_post` | WP Editor |
| `integer` | `absint` | Number input |
| `float` | `floatval` | Number input with step |
| `boolean` | `(bool)` | Checkbox |
| `select` | — | Dropdown (needs `options`) |
| `relation` | — | Post selector (needs `post_type`) |
| `gallery` | — | Media library picker |
| `repeater` | — | Sortable rows (needs `fields`) |

**Validation options:** `required`, `min`, `max`, `validate` callback.

**Meta prefix:** Configure `meta_prefix` to auto-prefix all meta keys:
```php
ntdst_data()->register('portfolio', [
    'meta_prefix' => 'pf_',  // All meta stored as pf_field_name
    'fields' => ['client' => 'text'],  // Access as 'client', stored as 'pf_client'
]);
```

## API Endpoints

### Architecture
```
ntdstAPI.call('action', params)  →  POST /wp-json/ntdst/v1/action
    → Filter: ntdst/api_data/{action}  →  Handler returns data
```

Auto-nonce management, rate limiting (30/60s), CSRF protection.

### Handler Template (Every handler follows this)

```php
add_filter('ntdst/api_data/update_item', function ($data, $params) {
    // 1. Sanitize
    $id    = absint($params['id'] ?? 0);
    $title = sanitize_text_field($params['title'] ?? '');

    // 2. Validate
    if (!$id || empty($title)) {
        return new WP_Error('invalid_input', 'ID and title required');
    }

    // 3. Check permissions
    if (!current_user_can('edit_post', $id)) {
        return new WP_Error('forbidden', 'Permission denied');
    }

    // 4. Use Data Manager
    $model  = ntdst_data()->get('my_type');
    $result = $model->update($id, ['title' => $title]);

    // 5. Handle errors
    if (is_wp_error($result)) {
        return $result;
    }

    // 6. Return success
    return ['updated' => true, 'id' => $id];
}, 10, 2);
```

### Public vs Protected
Default public actions: `get_recent_posts`, `search_posts`, `search_users`, `send_magic_link`.
Add public actions: `add_filter('ntdst/api/public_actions', fn($a) => [...$a, 'my_action'])`.
Protected actions require login to get nonce.

### JavaScript Client

```javascript
// Built-in helpers
await ntdstAPI.call('my_action', params);
await ntdstAPI.getRecentPosts('portfolio', 10);
await ntdstAPI.searchPosts('query', ['post', 'page']);

// Error handling
try { await ntdstAPI.call('action', params); }
catch (error) { showError(error.message); }[SKILL.md](SKILL.md)
```

## Anti-Patterns

| Smell | Fix |
|-------|-----|
| `$wpdb->query(...)` | `ntdst_data()->get('type')->...` |
| `get_post_meta($id, 'key', true)` | `$model->getMeta($id, 'key')` |
| `update_post_meta(...)` | `$model->update($id, ['key' => $val])` or `$model->updateMeta()` |
| `$post['title']` after `find()` | `$post->post_title` (object, not array) |
| `return false` on error | `return new WP_Error(...)` |
| `fetch('/wp-json/...')` in JS | `ntdstAPI.call('action', params)` |
| `posts_per_page => -1` | Set reasonable limit or paginate |
| Meta in foreach loop | Use `->withMeta()->get()` (batch) |
| Missing `absint()` / `sanitize_*()` | Sanitize ALL API input |
| Missing `current_user_can()` | Check permissions for write actions |
| No `is_wp_error()` check | Always check create/update/delete results |
| `'status' => 'publish'` | Use `'post_status' => 'publish'` (avoid meta collision) |
| Multiple `updateMeta()` calls | Use `updateMetaBatch()` for multiple fields |

## Caching

Default: 1 hour. Custom: `$model->cache(7200)->get()`. No cache: `$model->cache(0)->get()`.

```php
ntdst_clear_posts_cache($id);           // Clear single post cache
ntdst_invalidate_post_type('portfolio'); // Invalidate all queries for type
```

**QueryCache**: Environment-aware caching via `NTDST_Query_Cache`. Automatically disabled in development (WP_DEBUG). Uses version-based invalidation for efficient cache busting.

Batch prime: `$model->withMeta()->get()` or `update_postmeta_cache($ids)`.

## Reference Files

| File | Content |
|------|---------|
| `references/data-orm.md` | Full CRUD, query builder, validation, field types, caching |
| `references/api.md` | REST endpoints, JS client, security, built-in actions |
| `references/metabox.md` | Auto-generated metaboxes, field options, tabs, conditionals |
