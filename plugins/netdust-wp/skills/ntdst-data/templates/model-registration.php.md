# Template: Model Registration

## In theme-config.php

> **`register()` is PRIVATE BY DEFAULT.** It merges your config over
> `['public' => false, 'has_archive' => false, 'supports' => ['title','editor','thumbnail']]`.
> The `'public' => true` below is a real opt-in decision — delete it for anything
> that should not be anonymously enumerable, and never assume silence means public.
>
> **`register()` can return `WP_Error`** when `register_post_type()` refuses the name
> (invalid or reserved). Check it if the registration is load-bearing.

```php
$model = ntdst_data()->register('{post_type}', [
    'label' => '{Display Label}',
    'public' => true,        // explicit opt-in — omit for a private type
    'has_archive' => true,   // explicit opt-in
    'menu_icon' => 'dashicons-{icon}',
    'supports' => ['title', 'editor', 'thumbnail'],
    'meta_prefix' => '',  // Optional: prefix for all meta keys (e.g., 'pf_')

    'fields' => [
        // Text field
        '{field_name}' => 'text',

        // Field with options
        '{field_name}' => [
            'type' => 'text',
            'required' => true,
        ],

        // Email with validation
        'email' => [
            'type' => 'email',
            'required' => true,
        ],

        // Integer with range
        'year' => [
            'type' => 'integer',
            'min' => 2000,
            'max' => 2100,
        ],

        // Select dropdown ('options' is required for the admin UI)
        'status' => [
            'type' => 'select',
            'options' => [
                'draft' => 'Draft',
                'pending' => 'Pending',
                'published' => 'Published',
            ],
        ],

        // Boolean toggle
        'featured' => 'boolean',

        // URL with custom validation
        'website' => [
            'type' => 'url',
            'validate' => fn($v) => str_starts_with($v, 'https://') ?: 'Must be HTTPS',
        ],

        // Relation to another post type
        'related_items' => [
            'type' => 'relation',
            'post_type' => 'other_type',
            'multiple' => true,
        ],

        // Image gallery
        'images' => [
            'type' => 'gallery',
            'required' => true,
        ],

        // Repeater field — the sub-field map key is `sub_fields`, NOT `fields`.
        // Both Data.php (setupSanitizers) and MetaboxGenerator read `sub_fields`;
        // a repeater declared with `fields` gets an EMPTY sub-field config, so
        // every sub-value falls back to sanitize_text_field and the admin UI
        // renders no rows.
        'links' => [
            'type' => 'repeater',
            'sub_fields' => [
                'title' => 'text',
                'url' => 'url',
            ],
        ],
    ],

    // Optional: tabbed metabox interface
    'field_groups' => [
        'basic' => [
            'title' => 'Basic Info',
            'fields' => ['field1', 'field2'],
        ],
        'media' => [
            'title' => 'Media',
            'fields' => ['images', 'gallery'],
        ],
        'advanced' => [
            'title' => 'Advanced',
            'fields' => ['related_items', 'featured'],
        ],
    ],
    'use_tabs' => true,
]);
```

## Field Types Reference

This is the **complete registerable vocabulary** (`NTDST_Data_Model::getDefaultSanitizer()`).
Every entry is genuinely sanitized. **An unrecognised type name now throws
`InvalidArgumentException` at registration** rather than silently falling through to
`sanitize_text_field` — a typo'd `wysiwig` fails loudly instead of quietly losing markup.

| Type | Sanitizer (write) | Read cast | Use For |
|------|-------------------|-----------|---------|
| `text` | `sanitize_text_field` | string | Short text, names |
| `textarea` | `sanitize_textarea_field` | string | Long text, descriptions |
| `email` | `sanitize_email` | string | Email addresses |
| `url` | `esc_url_raw` | string | URLs, links |
| `html` / `content` | `wp_kses_post` | string | Rich content |
| `wysiwyg` | `wp_kses_post` | string | Rich content **with a WP editor in the metabox** |
| `int` / `integer` | `absint` — **strips the sign** | int | Counts, ids, anything non-negative |
| `signed_int` | `(int)` cast; 0 for an array | int | **Anything that can be negative** — deltas, adjustments, discounts |
| `float` / `double` | `floatval` | float | Decimals, prices |
| `bool` / `boolean` | `sanitizeBoolean()` | bool | Yes/No, toggles |
| `date` | `sanitizeDate()` → `Y-m-d`, junk → `''` | string | Dates |
| `select` | `sanitize_text_field` | string | Dropdown choices (`options` required) |
| `array` | `sanitizeNestedArray()` | array | Simple/nested arrays |
| `json` | `sanitizeJson()` | array | JSON payloads |
| `relation` / `post_relation` / `person` | `absint` per id, always an array | int[] | Related posts/users |
| `gallery` | `absint` per id, always an array | int[] | Multiple images |
| `image` / `file` | `sanitizeAttachmentId()` — verifies the id IS an attachment, else `0` | int | Single attachment |
| `repeater` | `sanitizeRepeater()` — sub-values sanitized as their **declared `sub_fields` type** | array[] | Repeatable rows |

**Metabox aliases are NOT registerable types.** `MetaboxGenerator` renders `string`,
`longtext`, `decimal`, `number`, `datetime` and `callback`, but none of those exist in
the sanitizer map — registering one throws unless you also supply your own
`'sanitizer' => fn($v) => …` in the field config (which bypasses the throw).

`image` and `file` DO have a renderer — the media-picker cell, storing a plain
attachment-ID int. **`html`/`content`, `person` and `post_relation` have no dedicated
metabox renderer** — they fall to the `default` arm, a plain text input. Use `wysiwyg`
when you want the WP editor. `number` renders only as a repeater sub-field.

## Validation Options

| Option | Description |
|--------|-------------|
| `required` | Field must have value |
| `min` | Minimum value (numbers), minimum length (strings), minimum items (arrays) |
| `max` | Maximum value (numbers), maximum length (strings), maximum items (arrays) |
| `validate` | Custom validation callback returning `true` or error message string |

**Note:** `min`/`max` dispatch on the **runtime value**, not the declared type — string
→ length, numeric → value, array → item count. `required` is enforced on `create()`
only; `update()` is a partial write, so a field absent from the payload keeps its
existing value instead of failing validation.

**There is no `default` option.** `'default' => …` in a field config is read by nothing
in `Data.php` or `MetaboxGenerator.php` — an unset field is simply empty. Apply defaults
in your own code (e.g. `$model->getMeta($id, 'status') ?: 'pending'`).

## Usage After Registration

```php
$model = ntdst_data()->get('{post_type}');

// Create (use 'post_status' for WP status, not 'status')
// Returns the created WP_Post (with ->meta / ->fields) or WP_Error — NOT an id.
$post = $model->create([
    'title' => 'New Item',
    'post_status' => 'publish',  // WordPress post status
    '{field_name}' => 'value',
]);
if (is_wp_error($post)) {
    return $post;
}
$id = $post->ID;

// Read — find(int $id, string|array $status = 'publish')
$post = $model->find($id);                          // PUBLISH ONLY (the safe default)
$post = $model->find($id, 'any');                   // any status — an admin screen wants this
$post = $model->find($id, ['publish', 'draft']);    // an explicit set
// $model->find($id, true);                         // ✗ throws InvalidArgumentException
$items = $model->where('featured', true)->get();    // Returns array of arrays

// Update
$model->update($id, ['{field_name}' => 'new value']);

// Update meta (batch for multiple fields)
$model->updateMetaBatch($id, ['field1' => 'a', 'field2' => 'b']);

// Delete
$model->delete($id);
```

> **No cache invalidation step exists any more.** `ntdst_clear_posts_cache()` and
> `ntdst_invalidate_post_type()` are **DELETED** along with `NTDST_Query_Cache` and
> `$model->cache(N)`. The layer keeps no cache of its own; WordPress's post,
> `post_meta`, `post-queries` and term caches are the caching, and core invalidates
> them on every write — including writes that never went through the model. Do not
> reintroduce a bespoke cache over post meta.

> **`find()`'s second argument is a post status, not the removed `$skipCache` flag.**
> Passing a bool throws deliberately, because a silently-denying signature change is
> the worst shape available. A not-found row and a wrong-status row return the **same**
> `WP_Error`, so the error tells a caller nothing about whether the row exists.

## Taxonomy Registration

```php
$theme->taxonomy('{taxonomy_slug}', '{post_type}', [
    'label' => '{Taxonomy Label}',
    'hierarchical' => true,  // Categories (true) vs Tags (false)
    'public' => true,
]);
```

## Placeholders

| Placeholder | Replace With |
|-------------|--------------|
| `{post_type}` | lowercase_underscore slug |
| `{Display Label}` | Human-readable name |
| `{icon}` | Dashicon name |
| `{field_name}` | lowercase_underscore field name |
| `{taxonomy_slug}` | lowercase_underscore taxonomy |
| `{Taxonomy Label}` | Human-readable taxonomy name |
