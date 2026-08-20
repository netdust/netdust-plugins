# Data Layer Reference

The layer is a chain API over `WP_Query` plus the CPT/field vocabulary the metabox
generator reads. **It holds no performance opinion** — no query flags of its own, no
priming, no cache. See [Caching](#caching--wordpress-own-only) below.

## Model Registration

> **PRIVATE BY DEFAULT — this was a security fix, do not "restore" the old defaults.**
> `register()` merges your config over
> `['public' => false, 'has_archive' => false, 'supports' => ['title','editor','thumbnail']]`.
> It used to be the reverse, so a model registered without visibility flags was
> published, archived and publicly queryable — which is why every non-public CPT on
> every ntdst-core site had to state six denials by hand, and why forgetting one was a
> disclosure. **Opt IN to public; never opt out of it.**
>
> `register()` returns `NTDST_Data_Model` **or `WP_Error`** when `register_post_type()`
> refuses the name (INV-4: it no longer swallows the failure and builds a model whose
> post type does not exist).

```php
ntdst_data()->register('artwork', [
    // WordPress post type args
    'label'       => 'Artworks',
    'public'      => true,        // explicit opt-in
    'has_archive' => true,        // explicit opt-in
    'supports'    => ['title', 'editor', 'thumbnail'],

    // NTDST-specific
    'meta_prefix' => '_art_',     // prefixes all meta keys in DB

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

Every type below is genuinely sanitized. `select`, `date` and `wysiwyg` used to be
advertised but unimplemented — they fell through to `sanitize_text_field` silently. **An
unknown type name now throws `InvalidArgumentException` at registration** rather than
becoming text.

| Type | Sanitizer (write) | Read cast |
|------|-------------------|-----------|
| `text` | `sanitize_text_field` | `(string)` |
| `textarea` | `sanitize_textarea_field` | `(string)` |
| `html` / `content` | `wp_kses_post` | `(string)` |
| `wysiwyg` | `wp_kses_post` | `(string)` |
| `int` / `integer` | `absint` — **strips the sign** | `(int)` |
| `signed_int` | `(int)` cast; 0 for an array | `(int)` |
| `float` / `double` | `floatval` | `(float)` |
| `bool` / `boolean` | `sanitizeBoolean()` (`wp_validate_boolean`) | `bool` |
| `email` | `sanitize_email` | `(string)` |
| `url` | `esc_url_raw` | `(string)` |
| `select` | `sanitize_text_field` | `(string)` — `options` required for the UI |
| `date` | `sanitizeDate()` → `Y-m-d`; junk → `''` | `(string)` |
| `array` | `sanitizeNestedArray()` (recursive, structure-preserving) | `array` |
| `json` | `sanitizeJson()` (invalid JSON → `[]`) | `array` |
| `relation` / `post_relation` / `person` | `absint` per id, always an array | `int[]` |
| `gallery` | `absint` per id, always an array | `int[]` |
| `image` / `file` | `sanitizeAttachmentId()` — verifies the id IS an attachment, else `0` | `(int)` |
| `repeater` | `sanitizeRepeater()` — per declared **`sub_fields`** type | `array[]` |

**Metabox-only aliases are not registerable.** `string`, `longtext`, `decimal`, `number`,
`datetime` and `callback` render in `MetaboxGenerator` but are absent from the sanitizer
map, so `register()` throws on them unless the field config supplies its own
`'sanitizer'`. `number` is a repeater SUB-FIELD type only — at top level it falls to a text input.
Conversely `image` and `file` DO have a control (the media-picker cell), while
`html`/`content`, `person` and `post_relation` sanitize correctly but have **no metabox
control** — they fall to a plain text input. Use `wysiwyg` when you want the WP editor.

The repeater sub-field key is **`sub_fields`**, not `fields`; a repeater declared with
`fields` sanitizes every sub-value as text and renders no rows.

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

// FIND — find(int $id, string|array $status = 'publish')
// Returns WP_Post with ->meta and ->fields, or WP_Error.
$artwork = $model->find(42);                       // PUBLISH ONLY — the safe default
$artwork = $model->find(42, 'any');                // every status (admin screens)
$artwork = $model->find(42, ['publish','draft']);  // an explicit set
// $model->find(42, true);                         // ✗ throws InvalidArgumentException

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
$model->updateMetaBatch(42, [                      // one existence check + one rollback
    'price'  => 3500.00,                           // snapshot covering all fields
    'medium' => 'acrylic',
]);
$model->deleteMeta(42, 'temporary_note');
```

`getMeta(int $id, ?string $key = null, $default = null, $status = 'publish')` takes
the SAME `$status` argument, with the SAME default, as `find()`. It used to hard-code
`find($id, 'any')` and was documented as a "raw accessor, not a visibility decision" —
so `find($id)` refused an unpublished row while `getMeta($id, 'x')` served its meta.
One model, one row, two read paths, opposite answers; a service that gated with the
first and read with the second had a bypass. Fixed 2026-08-07.

One rule for the layer: **the default answer is the safe one.** Pass `'any'` (or an
explicit status array) when an admin screen genuinely wants an unpublished row.
Authorization is still the caller's job — this default is a floor, not a gate.

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
| `count()` | `int` |
| `paginate()` | `['data' => [...], 'pagination' => [...]]` |

**Always check `is_wp_error()` on find/create/update.**

`find()`'s not-found and wrong-status cases return the **same** `WP_Error`, deliberately:
a caller who may not see this status learns nothing about whether the row exists. Don't
branch on the error to tell them apart, and when writing a denial test, assert the row is
REACHABLE first — otherwise the denial may be passing because the fixture never existed.

`create()` and `update()` hydrate their return with `find($id, 'any')` on purpose: they
return the row they just wrote, whatever status it was written with. Hydrating through
the publish-only default would make `create(['post_status' => 'draft'])` write the row and
then return `WP_Error`, orphaning it.

`first()` returns the same shape as `find()`, not a `stdClass`. Access `$post->post_title`, `$post->fields['price']`, etc. — never `$post->title` / `$post->id`.

### Atomicity of `create()` / `update()`

Meta-write failures trigger an **application-level rollback** (best-effort, not a DB transaction):

- `create()` snapshots nothing — on meta-write failure it `wp_delete_post`s the new post and returns `WP_Error`.
- `update()` snapshots the affected post-table fields and each meta field (`exists` flag + previous value) *before* writing, and calls `restorePostData()` / `restoreMetaData()` on any failure.

This is best-effort: rollback writes can themselves fail under DB stress. For multi-table critical paths (capacity locks, voucher counts), wrap the whole business operation in `$wpdb->query('START TRANSACTION')` at the service layer — see `EnrollmentService::enroll()` in Stride for the pattern.

WordPress returns `false` from `update_post_meta` both on errors *and* on unchanged values. The data layer's `updateMetaValue()` verifies the stored value after a `false` return and treats unchanged values as success — so updating to the same value no longer triggers a spurious rollback.

### Builder state reset

Two independent mechanisms:

1. `get()`, `count()`, and `paginate()` reset `$this->query_args = []` in a `finally`
   block. `first()` and `all()` delegate to `get()`, so they inherit it.
2. `ntdst_data()->get($name)` returns a **fresh clone** per acquisition. The model
   registry is `static`, so every caller used to share one mutable instance — an
   *abandoned* `->where()` (never reaching a terminal method, so never hitting the
   `finally`) stayed on it and silently narrowed the next query from anywhere in the
   process. The clone makes that leak unrepresentable.

`get()` also does **not** store a model for an unregistered name any more. It used to
auto-register a phantom into that static array, so a caller-supplied type name on a
public endpoint could register whatever it liked and `isRegistered()` could never tell a
real model from something someone once mistyped.

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
$model->withMeta()->withTerms()->get();   // `meta` is SCHEMA-PROJECTED: unprefixed, type-cast, declared fields only

// Pagination
$result = $model->where('medium', 'oil')->paginate(page: 2, per_page: 12);
// $result['data'] = [...], $result['pagination'] = [total, per_page, current_page, ...]

// First result
$item = $model->where('featured', true)->first();

// Count
$total = $model->where('medium', 'oil')->count();
```

---

## Caching — WordPress' own, only

> **REMOVED. `NTDST_Query_Cache` is DELETED** — the class, its file, its invalidation
> hooks, and with them `$model->cache(N)`, the `cache_time` config/query key,
> `ntdst_query_cache()`, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()`,
> `NTDST_Data_Manager::clearCache()` and the `ntdst_should_invalidate_meta` filter. Code
> or docs using any of them are dead — **delete the call, do not port it.** There is
> nothing left to invalidate.
>
> It was also inert wherever anyone could observe it: `resolveCacheTime()` returned `0`
> on every `WP_DEBUG` environment, so the whole bespoke cache was off in development.

What remains is core's own caching, which is the point:

- `NTDST_Data_Manager::getPostMeta()` prefers core's `post_meta` cache — primed by
  `WP_Query` on any read and **invalidated by core on any write, whoever performs it** —
  and falls back to one **prepared** SQL statement when cold.
- `getPostTerms()` does the same with core's `{$taxonomy}_relationships` cache.
- `find()` is `get_post()`; `get()` / `count()` / `paginate()` are `WP_Query`, served
  from core's `post-queries` cache (salted on `$last_changed`).
- `WP_Query`'s `update_post_meta_cache` / `update_post_term_cache` defaults are TRUE and
  the layer stopped overriding them, so nothing is primed on top. The thumbnail prime and
  the unconditional author prime (which ran `WHERE ID IN (0)` for `post_author = 0` rows)
  are gone with it.

**This is a security property, not just a simplification.** A layer-owned cache is one
core does not invalidate, so a write that bypassed the model — a raw
`update_post_meta()` — could leave a stale value being served. For a revocation flag that
means a revoked credential still reading as live. Using core's group means any writer's
invalidation counts. **Do not reintroduce a bespoke cache over post meta** without
solving that.

There is likewise **no stale-cache cleanup on external deletes**: there is no
layer-owned entry to clean. `find()` returns `WP_Error` when `get_post()` comes back
empty, and that is the whole behaviour.

### Core's query cache is actor-blind — an authorization hazard that did NOT go away

Core's `post-queries` cache keys on the query args and the generated SQL, **never on who
asked**. Two callers with different privileges issuing the identical query share one
entry, in both directions.

So any handler taking caller-supplied query input must **refuse the request** when the
caller may not query it, rather than querying first and filtering rows afterwards — a
post-hoc filter runs after the answer is already cached. Put the restriction in the ARGS
(a narrowed `post_type`, a `post_parent__not_in` exclusion list), so the two caller
classes cannot share a key.

### If you genuinely need an optimisation

Ask WordPress for it directly, at the call site that can justify it, with a measurement
attached: `update_post_thumbnail_cache()`, `wp_cache_*`, or a `no_found_rows` arg passed
through this API. The layer will not decide it for you.

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

The "is this an ORM-backed model?" check uses MetaboxGenerator's own registry instead of calling `ntdst_data()->get($name)` — that call used to auto-create a phantom empty model as a side effect, which persisted across the request and shadowed later schema-bearing registrations. `get()` no longer stores the phantom, but it still *returns* an empty model for an unknown name, so it can never answer "does this exist?". Iterate post types defensively with `ntdst_data()->isRegistered($name)` (an instance method on the manager, not static):

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
