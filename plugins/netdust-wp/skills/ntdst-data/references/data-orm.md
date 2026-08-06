# NTDST Data ORM Cookbook

Complete guide to the NTDST Data Layer — a minimal chain API over `WP_Query`, plus the
CPT/field vocabulary the metabox generator reads. **Nothing else.** The layer holds no
performance opinion: it sets no query flags of its own, primes no caches, and keeps no
cache of its own. See [Caching](#caching--performance) for why that is a security
property and not just a simplification.

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
ntdst_data()->get('model')                // Get a model instance (a fresh CLONE)
ntdst_data()->isRegistered('model')       // Has a model been registered? (no side effect)
ntdst_data()->register(...)               // Register new model
ntdst_get_formatted_posts($args)          // Run a WP_Query with core's defaults, format the rows
```

> **REMOVED — these no longer exist anywhere in ntdst-core.**
> `ntdst_get_posts_fast()` → renamed to **`ntdst_get_formatted_posts(array $args): array`**
> (the old name advertised a speed property it did not have — the priming it did *was*
> the cost, and it is gone).
> `ntdst_query_cache()`, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()` →
> **deleted outright** with `NTDST_Query_Cache`. If you meet one of these in older code,
> that code is dead: replace it with the chain API
> (`ntdst_data()->get($type)->where(...)->get()`) or `ntdst_get_formatted_posts()`, and
> delete the invalidation call rather than replacing it — there is nothing left to
> invalidate.

`isRegistered()` is the safe way to check whether a model exists when iterating over
post types. It reads the registry directly; `get()` does not.

`ntdst_data()->get($name)` returns a **clone** of the registered model (or a fresh empty
model for an unregistered name — it does **not** store a phantom entry). The clone is
why an abandoned `->where()` chain can no longer narrow the next caller's query from
somewhere else in the process.

---

## Model Registration

> **Defaults are PRIVATE, and that was a security fix — do not "restore" them.**
> `register()` merges your config over
> `['public' => false, 'has_archive' => false, 'supports' => ['title','editor','thumbnail']]`.
> It used to be the reverse, which is why every non-public CPT on every ntdst-core site
> was anonymously enumerable. **Opt IN to public; never opt out of it.** Silence must
> mean private.
>
> `register()` returns the `NTDST_Data_Model`, **or a `WP_Error`** when
> `register_post_type()` refuses the name. It no longer swallows that failure and hands
> back a model whose post type does not exist.

### Basic Registration

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio Items',
    'public' => true,        // explicit opt-in — say it or you don't get it
    'has_archive' => true,   // explicit opt-in
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

`find(int $id, string|array $status = 'publish')`.

**The second parameter used to be a `bool $skipCache`. It is now a post status**, and
passing a bool throws `InvalidArgumentException` deliberately — a leftover
`find($id, true)` would otherwise mean "accept the status `true`", which matches nothing
and denies every row. Fail-closed but invisible is the worst shape available, so it
fails loudly instead.

**The layer no longer half-decides visibility.** It applies the status you asked for and
nothing else — it does not guess, cache, or filter on your behalf. Authorization is the
CALLER's job, in the handler, every time. Pass an explicit `$status` when you genuinely
want unpublished rows (an admin screen does; a public read does not).

```php
$model = ntdst_data()->get('portfolio');

$project = $model->find(123);                        // PUBLISH ONLY — the safe default
$project = $model->find(123, 'any');                 // every status
$project = $model->find(123, ['publish', 'draft']);  // an explicit set
// $model->find(123, true);                          // ✗ throws InvalidArgumentException

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

A not-found row and a wrong-status row return the **same** `WP_Error` — a caller who may
not see this status learns nothing about whether it exists. Do not rely on the error to
distinguish them, and remember it when writing a denial test: assert the row is
REACHABLE first, or your denial may be passing because the fixture never existed.

`create()` and `update()` hydrate their return value with `find($id, 'any')` on purpose
— they return the row they just wrote, whatever status it was written with. Without
that, `create(['post_status' => 'draft'])` would write the row and then return
`WP_Error`, and the caller would conclude nothing was written.

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

Two independent mechanisms, both needed:

1. `get()`, `count()`, and `paginate()` reset `$this->query_args = []` in a `finally`
   block, so a completed chain leaves nothing behind.
2. `ntdst_data()->get($name)` returns a **fresh clone** of the registered model per
   acquisition. The registry is `static`, so every caller used to share one mutable
   instance — an *abandoned* `->where()` (one that never reached a terminal method, and
   so never hit the `finally`) stayed on it and silently narrowed the next query from
   anywhere in the process. The clone makes that leak unrepresentable.

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
| `ntdst_get_formatted_posts()` | `array` of arrays | `$posts[0]['title']` |

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

### CORRECT - Array Access with ntdst_get_formatted_posts()

```php
// CORRECT - ntdst_get_formatted_posts() returns array with meta
// (this is ntdst_get_posts_fast() under its honest name — see Global Helpers)
$posts = ntdst_get_formatted_posts([
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

### The row shape `get()` / `ntdst_get_formatted_posts()` returns

Every row is an associative array with these keys, always:

| Key | Value |
|---|---|
| `id` | `int` |
| `title`, `content`, `slug` | `string` (from `post_title` / `post_content` / `post_name`) |
| `excerpt` | `post_excerpt`, or a 55-word trim of the content when empty |
| `permalink` | `get_permalink()` |
| `date`, `modified` | **ISO 8601** (`mysql2date('c', …)`), not the raw MySQL datetime |
| `author` | `['id' => int, 'name' => string]` |
| `thumbnail` | `['id' => int, 'url' => medium, 'full' => full]`, or **`null`** when there is none |
| `meta` | only when `'include_meta' => true` |
| `terms` | only when `'include_terms' => true`, grouped by taxonomy, each `['id','name','slug']` |

Defaults applied when you don't pass them: `post_type => 'post'`,
**`post_status => 'publish'`**, `posts_per_page => 10`, `orderby => 'date'`,
`order => 'DESC'`, `ignore_sticky_posts => true`. Those are the SHAPE of the answer;
everything WordPress decides about priming, counting and caching, WordPress keeps
deciding.

> `post_status => 'publish'` is right for every ordinary content type and silently wrong
> for **attachments**, which are stored as `inherit` and never promoted. A relation field
> scoped to `attachment` renders an autocomplete that can never return a result unless
> the caller widens `post_status`. And `inherit` is a *pointer* to the parent's status,
> not a status — naming it dereferences nothing, so the widening reaches every attachment
> row including children of drafts. If you widen it, exclude non-viewable parents from
> the **query args** (`post_parent__not_in`), never from the answer.

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

// Batch update (multiple fields, one existence check, one rollback snapshot)
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

Every type below is **genuinely sanitized**. That was not always true: `select`, `date`
and `wysiwyg` were advertised but never implemented and fell through to
`sanitize_text_field` silently. A CPT helper that accepts a type name and then ignores it
is lying about its own vocabulary, so the vocabulary was made real. Use the type that
means what you mean.

**An unrecognised type name now throws `InvalidArgumentException` at registration.** A
typo that silently became `sanitize_text_field` is how a `wysiwig` field loses its markup
with nothing failing.

### Basic Types

| Type | Sanitizer (write) | Read cast |
|------|-------------------|-----------|
| `text` | `sanitize_text_field` | `string` |
| `textarea` | `sanitize_textarea_field` | `string` |
| `email` | `sanitize_email` | `string` |
| `url` | `esc_url_raw` | `string` |
| `html` / `content` | `wp_kses_post` | `string` |
| `wysiwyg` | `wp_kses_post` | `string` |
| `select` | `sanitize_text_field` | `string` |
| `date` | `sanitizeDate()` — parses, stores `Y-m-d`; junk becomes `''` | `string` |

### Numeric Types

| Type | Sanitizer (write) | Read cast |
|------|-------------------|-----------|
| `integer` / `int` | `absint` | `int` |
| `float` / `double` | `floatval` | `float` |
| `boolean` / `bool` | `sanitizeBoolean()` — `wp_validate_boolean`, so the string `"false"` is `false` | `bool` |

### Complex Types

| Type | Sanitizer (write) | Read cast |
|------|-------------------|-----------|
| `array` | `sanitizeNestedArray()` — recursive, preserves structure, `sanitize_key` on string keys | `array` |
| `json` | `sanitizeJson()` — decodes, rejects invalid JSON to `[]` | `array` |
| `relation` / `post_relation` / `person` | `absint` per id, **always an array** | `int[]` |
| `gallery` | `absint` per id, always an array | `int[]` |
| `image` / `file` | `sanitizeAttachmentId()` — verifies the id IS an attachment, else `0` | `int` |
| `repeater` | `sanitizeRepeater()` — each sub-value sanitized as its **declared `sub_fields` type** | `array[]` |

**Repeater sub-fields go under `sub_fields`, not `fields`.** Both `Data.php` and
`MetaboxGenerator.php` read `sub_fields`; a repeater declared with `fields` gets an empty
sub-field config, every sub-value falls back to `sanitize_text_field`, and the admin UI
renders no rows.

**Repeater read-back caveat — know this before you expose one publicly:** sub-fields are
sanitized on write, but rows come back through `formatRepeaterField()` largely as stored.
An allow-list projection applied at the top level does **not** filter sub-keys. If you
project a payload for anonymous callers, project the repeater's rows too, or an
undeclared sub-key ships.

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

    // Repeater (e.g., social links) — declare sub_fields so the sub-values are
    // sanitized as their own types instead of all falling back to text.
    'social_links' => [
        'type' => 'repeater',
        'sub_fields' => [
            'platform' => 'text',
            'url'      => 'url',
        ],
    ],

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

### The layer has no cache of its own any more

**`NTDST_Query_Cache` is DELETED.** So are `$model->cache(N)`, the `cache_time`
config/query key, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()` and
`ntdst_query_cache()`. Older code and docs using them are dead — delete the call, do not
port it. The layer stopped having a performance opinion.

It was also inert where anyone could observe it: the old `resolveCacheTime()` returned
`0` on every `WP_DEBUG` environment, so the whole bespoke cache was off wherever a
developer had ever looked at it.

What remains is **WordPress's own** caching, which is the point:

- `getPostMeta()` prefers core's `post_meta` cache — primed by `WP_Query` on any read,
  and **invalidated by core on any write, whoever performs it** — and falls back to one
  prepared SQL statement when cold.
- `getPostTerms()` does the same with core's `{$taxonomy}_relationships` cache.
- `find()` is `get_post()`, which is core's own cached read.
- `get()` / `count()` / `paginate()` run `WP_Query`, which core serves from its
  `post-queries` cache (salted on `$last_changed`).

**This is a security property, not just a simplification.** A layer-owned cache is one
core does not invalidate, so a write that bypassed the model (a raw
`update_post_meta()`) could leave a stale value being served — which for a revocation
flag means a revoked credential still reading as live. Using core's group means any
writer's invalidation counts. **Do not reintroduce a bespoke cache over post meta**
without solving that.

There is also **no stale-cache cleanup step** on external deletes any more: there is no
layer-owned entry left to clean up. `find()` simply returns `WP_Error` when `get_post()`
comes back empty.

### Core's query cache is actor-blind — that is an authorization hazard

Core's `post-queries` cache keys on the query args and the generated SQL, **never on who
asked**. So two callers with different privileges who issue the identical query share the
identical cache entry, and one actor's answer is served to the other, in both directions.

Consequence for any handler taking caller-supplied query input: **refuse the request when
the caller may not query it, instead of querying first and filtering the rows
afterwards.** A post-hoc filter runs after the query has already been cached. Put the
restriction in the ARGS (an exclusion list, a narrowed `post_type`), so the two caller
classes cannot share a key.

### Formatted-query function

```php
$posts = ntdst_get_formatted_posts([
    'post_type' => 'portfolio',
    'posts_per_page' => 20,
    'post_status' => 'publish',
    'orderby' => 'date',
    'order' => 'DESC',
    'include_meta' => true,      // attach a `meta` key to each row
    'include_terms' => true,     // attach a `terms` key to each row

    // Standard WP_Query args also work:
    'meta_query' => [...],
    'tax_query' => [...],
]);
```

`include_meta` / `include_terms` are the only non-`WP_Query` args; they are stripped
before the query runs. Everything else is passed straight through, so a caller that
genuinely needs `no_found_rows`, or a warm thumbnail cache
(`update_post_thumbnail_cache()`), asks for it **at the call site that can justify it**,
with a measurement attached.

### Performance Tips

1. **`include_meta` does not prime anything** — `WP_Query` already primes the post, meta
   and term caches for its result set (`update_post_meta_cache` /
   `update_post_term_cache` default to true, and the layer stopped overriding them).
   The flag only controls whether meta is *attached to the returned rows*.
2. **Set appropriate limits** — avoid `posts_per_page => -1`.
3. **Prime caches before loops** — see "Batch Loading" below.
4. **Measure before optimizing.** The layer will not do it for you, on purpose.

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
// WRONG - re-checks the post exists on every call, and each write stands alone:
// if the third fails, the first two are already committed.
$model->updateMeta($id, 'field1', 'value1');
$model->updateMeta($id, 'field2', 'value2');
$model->updateMeta($id, 'field3', 'value3');

// CORRECT - one existence check, and one rollback snapshot covering all three:
// a failure part-way through restores the fields already written.
$model->updateMetaBatch($id, [
    'field1' => 'value1',
    'field2' => 'value2',
    'field3' => 'value3',
]);
```

### Reaching for a deleted cache API

```php
// WRONG - none of these exist. The layer keeps no cache to invalidate.
$posts = $model->cache(3600)->get();
ntdst_clear_posts_cache($id);
ntdst_invalidate_post_type('portfolio');
ntdst_query_cache()->isCachingEnabled();

// CORRECT - just query. Core's caches are already correct because core
// invalidates them on every write, including writes the model never saw.
$posts = $model->get();
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
