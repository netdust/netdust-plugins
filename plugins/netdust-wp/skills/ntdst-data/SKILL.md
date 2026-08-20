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

> ## Reference implementation: daan's `ntdst-core` (as of 2026-08-07)
>
> There is ONE ntdst-core. Copies of it live in each project and they are at
> different versions — **daan's is the most current, and this skill describes
> it.** Other projects (stride, stride-output-reshape) are behind and will be
> brought up; until a project is ported, its copy may still carry the older
> behaviour listed under "was" below.
>
> **What changed on 2026-08-07** — if you are reading older code, this is what
> you are looking at, and each change is a narrowing you should not undo:
>
> | | now | was |
> |---|---|---|
> | `->withMeta()` row meta | schema-projected: **unprefixed**, type-cast, declared fields only | raw bag: **prefixed**, every meta row |
> | `getMeta($id, …)` | publish-only by default; 4th arg `$status`, same as `find()` | `find($id, 'any')` — read drafts silently |
> | public actions shipped by the framework | **none** — `$public_actions` is empty | `get_recent_posts`, `search_posts`, `send_magic_link` |
> | `search_posts` | retired → `relation_search` on `NTDST_RelationField`, non-public | present, and public |
> | `getFormattedPosts()` on a protected post | withholds `content`/`excerpt`, sets `protected` | served the body a post password withholds |
>
> **Still verify against the project's own `api/Data.php` and `api/Actions.php`
> before writing.** This skill is a map, not the territory — it drifted from the
> code for six weeks (2026-06-23 → 2026-08-06) describing a deleted API, and the
> fix is always to read the source.

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
$post   = $model->find($id);            // PUBLISH-ONLY. Returns WP_Post or WP_Error
$post   = $model->find($id, 'any');     // Any status — an admin screen wants this
$post   = $model->find($id, ['publish', 'draft']);  // An explicit set
$result = $model->update($id, $data);   // Returns WP_Post or WP_Error
$result = $model->delete($id);          // Soft delete (trash)
$result = $model->delete($id, true);    // Force delete

// Meta operations
$value = $model->getMeta($id, 'field');           // PUBLISH-ONLY, like find()
$all   = $model->getMeta($id);                    // All declared fields
$value = $model->getMeta($id, 'field', null, 'any');  // Explicit status to read a draft
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
ntdst_get_formatted_posts($args)      // Direct query returning formatted arrays
```

> **REMOVED — do not write these, they no longer exist.** `ntdst_get_posts_fast()`,
> `ntdst_query_cache()`, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()`.
> The free-function "second door" into the query layer was swept onto the chain API,
> and the layer's own cache was deleted outright. If you find a call to one of these,
> it is dead code from before that sweep — replace it with the chain API
> (`ntdst_data()->get($type)->where(...)->get()`) or `ntdst_get_formatted_posts()`.

`isRegistered()` is the way to ask whether a model exists when iterating over post types. **`get()` no longer auto-registers a phantom** — that was the v2 behaviour, and it meant a caller-supplied type name on a public endpoint could register whatever it liked. It now returns a CLONE of a registered model, or an unstored empty `NTDST_Data_Model` for an unknown name, and writes nothing to the static registry either way. The clone matters too: `$models` is static, so callers used to share one mutable instance and an abandoned `->where()` silently narrowed the next query from anywhere in the process.

## CRITICAL: `find()` decides NOTHING about visibility except status

`find(int $id, $status = 'publish')`. The second parameter used to be a
`bool $skipCache`. **It is now a post status**, and passing a bool throws
`InvalidArgumentException` deliberately — a silently-denying signature change is
the worst shape available, so it fails loudly instead.

```php
$model->find($id);              // publish only — the SAFE default
$model->find($id, 'any');       // every status
$model->find($id, ['publish','draft']);
$model->find($id, true);        // ✗ throws InvalidArgumentException
```

**The layer no longer half-decides.** It applies the status you asked for and
nothing else — it does not guess, cache, or filter on your behalf. Authorization
is the CALLER's job, in the handler, every time. Pass an explicit `$status` when
you genuinely want unpublished rows (an admin screen does; a public read does not).

| Method | Returns | Access |
|--------|---------|--------|
| `find($id)` | `WP_Post` (with `->meta`, `->fields`) or `WP_Error` | `$post->post_title`, `$post->fields['key']` |
| `first()` | `WP_Post` (same shape as `find()`) or `null` | `$post->post_title`, `$post->fields['key']` |
| `get()` | Array of associative arrays; `meta` is **schema-projected** | `$posts[0]['title']`, `$posts[0]['meta']['declared_field']` |
| `count()` | `int` | — |
| `paginate()` | `['data' => [...], 'pagination' => [...]]` | — |

A not-found row and a wrong-status row return the **same** `WP_Error` — a caller
who may not see this status learns nothing about whether it exists. Do not rely on
the error to distinguish them, and remember it when writing a denial test: assert
the row is REACHABLE first, or your denial may be passing because the fixture
never existed.

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

> **Defaults are PRIVATE, and this was a security fix — do not "restore" them.**
> `register()` now merges your config over `['public' => false, 'has_archive' => false]`.
> It used to be the reverse, which meant a CPT registered with no opinion was
> published, archived and publicly queryable — that default is exactly why every
> non-public CPT on every ntdst-core site was anonymously enumerable. **Opt IN to
> public; never opt out of it.** Silence must mean private.

```php
ntdst_data()->register('portfolio', [
    'label'       => 'Portfolio Items',
    'public'      => true,   // explicit opt-in — say it or you don't get it
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

Every type in this table is genuinely sanitized. That was not always true: `select`,
`date` and `wysiwyg` were **advertised but never implemented** and fell through to
`sanitize_text_field` silently. A CPT helper that accepts a type name and then
ignores it is lying about its own vocabulary — so the vocabulary was made real.
Use the type that means what you mean.

| Type | Sanitizer | Admin UI |
|------|-----------|----------|
| `text` | `sanitize_text_field` | Text input |
| `textarea` | `sanitize_textarea_field` | Textarea |
| `email` | `sanitize_email` | Email input |
| `url` | `esc_url_raw` | URL input |
| `html`, `content` | `wp_kses_post` | WP Editor |
| `wysiwyg` | `wp_kses_post` | WP Editor |
| `int`, `integer` | `absint` — **strips the sign** | Number input |
| `signed_int` | `(int)` cast; 0 for an array. **Use this for any value that can be negative** | Number input |
| `float`, `double` | `floatval` | Number input with step |
| `bool`, `boolean` | `sanitizeBoolean()` | Checkbox |
| `date` | `sanitizeDate()` | Date input |
| `select` | `sanitize_text_field` | Dropdown (needs `options`) |
| `array` | `sanitizeNestedArray()` | — |
| `json` | `sanitizeJson()` | — |
| `relation` | `absint` per id, always an array | Post selector (needs `post_type`) |
| `gallery` | `absint` per id, always an array | Media library picker |
| `repeater` | `sanitizeRepeater()` — **rows carry their own sub-types** | Sortable rows (needs `fields`) |

**Repeater caveat, know this before you expose one publicly:** sub-fields are
sanitized on write, but rows are read back through `formatRepeaterField()` largely
as stored. An allow-list projection applied at the top level does **not** filter
sub-keys. If you project a payload for anonymous callers, project the repeater's
rows too, or an undeclared sub-key ships.

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

### Public vs Protected — read this before adding a public action

`api_data` is a **fast-AJAX read layer**, not a general-purpose public API. That is a
legitimate design, but it means an action you add to `public_actions` is reachable by
anyone, with caller-supplied params, and `verifyOrigin()` does **not** save you — it
returns true when there is no Origin, no Referer and no auth cookie. It fails open.
Treat every public handler as internet-facing.

**The framework ships NO public actions and no data actions at all.**
`$public_actions` is empty; `NTDST_Actions` is a router — origin, rate limit,
nonce, auth gate, dispatch — with no opinion about anyone's data. Anonymous
exposure is a per-site decision made in exactly one place:

```php
add_filter('ntdst/api/public_actions', fn($a) => [...$a, 'my_action']);
```

Everything not listed there requires a logged-in caller before the handler runs.

> **Retired 2026-08-07 — do not write these, they no longer exist.**
> `get_recent_posts` and `search_users` are DELETED. `send_magic_link` was
> removed from the public list (it never had a handler). `search_posts` MOVED to
> `NTDST_RelationField::handleRelationSearch()` as the non-public
> `relation_search`. Older projects may still carry them until ported.
>
> These were "example" actions that made every site's data anonymously queryable
> by a caller-supplied post type. Defending that surface took five generations of
> security review; retiring it let the whole gate stack be deleted rather than
> fixed. **Do not reintroduce a generic, caller-parameterised query action.**

**The relation autocomplete.** `relation_search` is the one framework-provided
data action, and it is not public. Its gate is two questions, both cheap: is the
requested type a **declared relation target** (an allow-list DERIVED from the
registered schemas — every `post_type` named by a `relation` field), and does the
caller hold that type's own `edit_others_posts`? A type nobody points a relation
field at is unreachable, and nobody has to remember to exclude it.

### Authorization idiom — three rules, each learned the hard way

**1. `edit_posts` is NOT authorization.** It means "may create and edit MY OWN
posts", and **Contributors and Authors hold it**. Gating a read path on it hands
every non-public row to the lowest content role. This shipped twice, in different
files, both times with a comment claiming it meant "editors only". Use
`edit_others_posts` — "may edit posts belonging to someone else" — which is what a
handler returning other people's rows actually implies.

**2. Read the capability OFF THE TYPE, never as a literal.**

```php
// ✓ follows the type; survives a per-type capability map
$type = get_post_type_object('release');
$cap  = ($type instanceof WP_Post_Type && is_string($type->cap->edit_others_posts ?? null))
      ? $type->cap->edit_others_posts : '';
$mayReadOthers = $cap !== '' && current_user_can($cap);

// ✗ correct only while capability_type === 'post'
if (!current_user_can('edit_others_posts')) { ... }
```

The literal and the mapped answer coincide for a `capability_type => 'post'` type —
and stop coinciding the moment anyone gives that type its own capability type, which
is a standard hardening. Then the literal silently admits every generic Editor to a
type that no longer means to grant them anything. **Resolve and validate BEFORE
calling `current_user_can()`** — a non-string capability must deny, not be passed in.

**3. Defence in depth: gate the FETCH as well as the response.** Decide the
capability first, then let it choose the status you fetch:

```php
$release = $model->find($id, $mayReadOthers ? 'any' : ['publish']);
// ... then the handler gate STAYS, as an independent second control
```

An unprivileged caller's embargoed row is then never loaded at all, so a later
mistake in the gate has nothing left to leak.

### Never return a raw `WP_Post` from a public handler

`find()` populates `->meta` with **every** meta row including protected
`_`-prefixed keys, and `json_encode` serialises all of `WP_Post`'s public
properties — `post_password` among them. Nothing downstream filters. Project an
explicit **allow-list**, and build it by iterating the declared schema rather than
filtering `->fields`:

```php
$declared = [];
// getSchema() is the model's schema accessor. There is no getFields().
foreach (array_keys($model->getSchema()) as $field) {
    $declared[$field] = $formatted[$field] ?? null;
}
return array_merge($declared, [
    'id' => (int) $post->ID, 'title' => $post->post_title,
    'excerpt' => $post->post_excerpt, 'permalink' => get_permalink($post->ID),
]);
```

Iterating the schema makes the projection the contract in both directions: a
declared field can never go missing, and an undeclared one can never leak even if
the layer later hands back more than it was asked for. A denylist of known-bad keys
fails the moment someone adds a field.

### JavaScript Client

The client has exactly **three** methods — `call`, `upload`, `download`
(`ntdst-core/assets/js/ntdst-api.js`). There are no per-action helper wrappers;
`getRecentPosts()` / `searchPosts()` / `getPostDetails()` / `getTaxonomyTerms()`
were documented for years and never existed. Call the action by name.

```javascript
await ntdstAPI.call('my_action', params);
await ntdstAPI.upload('import_csv', formData);
await ntdstAPI.download('export_zip', { id: 12 });

// Error handling
try { await ntdstAPI.call('action', params); }
catch (error) { showError(error.message); }
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
| `find($id, true)` | Throws. Second arg is `$status` — pass `'any'` or a status array |
| `ntdst_get_posts_fast()`, `ntdst_query_cache()`, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()` | Deleted. Chain API, or `ntdst_get_formatted_posts()` |
| `$model->cache(3600)->get()` | Deleted. Core's caching is the caching |
| `current_user_can('edit_posts')` as a READ gate | Contributors hold it. Use `edit_others_posts`, read off the type object |
| `current_user_can('edit_others_posts')` as a literal | Resolve `$type->cap->edit_others_posts`; fail closed on empty/non-string |
| `'data' => $post` from a public handler | Project an allow-list built from the declared schema — raw `WP_Post` leaks `post_password` + all meta |
| `register()` with no `public` key, expecting private | It IS private now — but say `'public' => false` anyway if privacy is load-bearing |
| Registering a type `public => true, exclude_from_search => true` | That is the "reachable by URL, hidden from search" idiom — it needs an explicit review, not silence |

## Caching — the layer has no cache of its own any more

**`NTDST_Query_Cache` is DELETED.** So are `$model->cache(N)`, the `cache_time`
property, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()` and
`ntdst_query_cache()`. If you are reading older code or docs that use them, that
code is dead. The layer stopped having a performance opinion.

What remains is **WordPress's own** caching, which is the point:

- `getPostMeta()` prefers core's `post_meta` cache — primed by `WP_Query` on any
  read, and **invalidated by core on any write, whoever performs it** — and falls
  back to one prepared SQL statement when cold.
- `find()` is `get_post()`, which is core's own cached read.

This is a security property, not just a simplification. A layer-owned cache is one
core does not invalidate, so a write that bypassed the model (a raw
`update_post_meta()`) could leave a stale value being served — which for a
revocation flag means a revoked credential still reading as live. Using core's group
means any writer's invalidation counts. **Do not reintroduce a bespoke cache over
post meta** without solving that.

Batch prime with `$model->withMeta()->get()` or `update_postmeta_cache($ids)`.

## Reference Files

| File | Content |
|------|---------|
| `references/data-orm.md` | Full CRUD, query builder, validation, field types, caching |
| `references/api.md` | REST endpoints, JS client, security, built-in actions |
| `references/metabox.md` | Auto-generated metaboxes, field options, tabs, conditionals |
