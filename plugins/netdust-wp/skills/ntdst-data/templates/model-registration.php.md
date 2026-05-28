# Template: Model Registration

## In theme-config.php

```php
ntdst_data()->register('{post_type}', [
    'label' => '{Display Label}',
    'public' => true,
    'has_archive' => true,
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
            'label' => 'Field Label',
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

        // Select dropdown
        'status' => [
            'type' => 'select',
            'options' => [
                'draft' => 'Draft',
                'pending' => 'Pending',
                'published' => 'Published',
            ],
            'default' => 'draft',
        ],

        // Boolean toggle
        'featured' => [
            'type' => 'boolean',
            'default' => false,
        ],

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

        // Repeater field
        'links' => [
            'type' => 'repeater',
            'fields' => [
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

| Type | PHP Type | Use For |
|------|----------|---------|
| `text` | string | Short text, names |
| `textarea` | string | Long text, descriptions |
| `email` | string | Email addresses |
| `url` | string | URLs, links |
| `html` | string | Rich content, WYSIWYG |
| `integer` | int | Numbers, counts |
| `float` | float | Decimals, prices |
| `boolean` | bool | Yes/No, toggles |
| `date` | string | Dates (Y-m-d format) |
| `select` | string | Dropdown choices |
| `relation` | int/array | Related posts |
| `gallery` | array | Multiple images |
| `repeater` | array | Repeatable rows |

## Validation Options

| Option | Description |
|--------|-------------|
| `required` | Field must have value |
| `min` | Minimum value (numbers), minimum length (strings), minimum items (arrays) |
| `max` | Maximum value (numbers), maximum length (strings), maximum items (arrays) |
| `validate` | Custom validation callback returning `true` or error message string |

**Note:** For string length validation, use `min`/`max` - they automatically apply to string length when the field type is `text` or `textarea`.

## Usage After Registration

```php
$model = ntdst_data()->get('{post_type}');

// Create (use 'post_status' for WP status, not 'status')
$id = $model->create([
    'title' => 'New Item',
    'post_status' => 'publish',  // WordPress post status
    '{field_name}' => 'value',
]);

// Read
$post = $model->find($id);  // Returns WP_Post
$post = $model->find($id, true);  // Skip cache (after mutations)
$items = $model->where('featured', true)->get();  // Returns array

// Update
$model->update($id, ['{field_name}' => 'new value']);

// Update meta (batch for multiple fields)
$model->updateMetaBatch($id, ['field1' => 'a', 'field2' => 'b']);

// Delete
$model->delete($id);

// Cache invalidation
ntdst_clear_posts_cache($id);
ntdst_invalidate_post_type('{post_type}');
```

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
