# NTDST MetaboxGenerator

Auto-generates WordPress metaboxes from field definitions.

**Location:** `app/content/mu-plugins/ntdst-core/api/MetaboxGenerator.php`

## Automatic Generation

When you register a model with fields and a label, metaboxes are automatically generated:

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio Items',
    'fields' => [
        'client_name' => 'text',
        'year' => 'integer',
        'images' => ['type' => 'gallery', 'required' => true],
    ],
]);
// Metabox automatically created in admin!
```

## Field Type Rendering

Each field type renders appropriate admin UI:

| Type | Admin UI |
|------|----------|
| `text` | Text input |
| `textarea` | Textarea |
| `email` | Email input with validation |
| `url` | URL input |
| `html` | WordPress editor (TinyMCE) |
| `integer` | Number input |
| `float` | Number input with decimals |
| `boolean` | Checkbox |
| `date` | Date picker |
| `select` | Dropdown |
| `relation` | Post selector |
| `gallery` | Media gallery picker |
| `repeater` | Repeatable rows |

## Field Options

### Labels and Descriptions

```php
'fields' => [
    'client_name' => [
        'type' => 'text',
        'label' => 'Client Name',
        'description' => 'Enter the client or company name',
        'placeholder' => 'e.g., Acme Corporation',
    ],
]
```

### Required Fields

```php
'fields' => [
    'email' => [
        'type' => 'email',
        'required' => true,  // Shows asterisk, validates on save
    ],
]
```

### Default Values

```php
'fields' => [
    // Custom meta field named 'status' (e.g., approval workflow)
    // Note: This is different from WordPress post_status
    'status' => [
        'type' => 'select',
        'options' => ['pending' => 'Pending', 'approved' => 'Approved'],
        'default' => 'pending',
    ],
    'featured' => [
        'type' => 'boolean',
        'default' => false,
    ],
]
```

**Note:** When setting WordPress post status in `create()` or `update()`, use `'post_status'` key (not `'status'`) to avoid collision with custom meta fields.

### Select Options

```php
'fields' => [
    'category' => [
        'type' => 'select',
        'options' => [
            'design' => 'Design',
            'development' => 'Development',
            'branding' => 'Branding',
        ],
    ],
]
```

### Relation Fields

```php
'fields' => [
    // Single relation
    'author_profile' => [
        'type' => 'relation',
        'post_type' => 'artist_profile',
        'multiple' => false,
    ],
    // Multiple relations
    'related_artworks' => [
        'type' => 'relation',
        'post_type' => 'artwork',
        'multiple' => true,
    ],
]
```

### Gallery Fields

```php
'fields' => [
    'images' => [
        'type' => 'gallery',
        'required' => true,
        'min' => 1,   // Minimum images
        'max' => 20,  // Maximum images
    ],
]
```

### Repeater Fields

```php
'fields' => [
    'social_links' => [
        'type' => 'repeater',
        'fields' => [
            'platform' => [
                'type' => 'select',
                'options' => [
                    'instagram' => 'Instagram',
                    'twitter' => 'Twitter',
                    'linkedin' => 'LinkedIn',
                ],
            ],
            'url' => 'url',
        ],
    ],
]
```

## Tabbed Interface

Organize fields into tabs for better UX:

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio',
    'fields' => [
        'client_name' => 'text',
        'year' => 'integer',
        'description' => 'textarea',
        'images' => 'gallery',
        'featured' => 'boolean',
        'related' => ['type' => 'relation', 'post_type' => 'portfolio'],
    ],
    'field_groups' => [
        'basic' => [
            'title' => 'Basic Info',
            'fields' => ['client_name', 'year', 'description'],
        ],
        'media' => [
            'title' => 'Media',
            'fields' => ['images'],
        ],
        'settings' => [
            'title' => 'Settings',
            'fields' => ['featured', 'related'],
        ],
    ],
    'use_tabs' => true,
]);
```

## Conditional Fields

Show/hide fields based on other field values:

```php
'fields' => [
    'has_video' => [
        'type' => 'boolean',
        'label' => 'Include Video?',
    ],
    'video_url' => [
        'type' => 'url',
        'label' => 'Video URL',
        'condition' => ['has_video' => true],  // Only shows when checked
    ],
]
```

## Validation Display

Validation errors are shown inline:

```php
'fields' => [
    'website' => [
        'type' => 'url',
        'validate' => fn($v) => str_starts_with($v, 'https://') ?: 'Must be HTTPS URL',
    ],
]
// If validation fails, error message appears below field
```

## Metabox Position

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio',
    'fields' => [...],
    'metabox' => [
        'context' => 'normal',   // 'normal', 'side', 'advanced'
        'priority' => 'high',    // 'high', 'low', 'default'
    ],
]);
```

## Custom Metabox Title

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio',
    'fields' => [...],
    'metabox' => [
        'title' => 'Project Details',  // Custom title instead of "Portfolio Fields"
    ],
]);
```

## Accessing Field Values

After saving, fields are stored as post meta:

```php
// Via Data Manager (recommended)
$model = ntdst_data()->get('portfolio');
$post = $model->find($id);
$client = $model->getMeta($id, 'client_name');

// Or with query
$items = $model->where('featured', true)->withMeta()->get();
foreach ($items as $item) {
    echo $item['meta']['client_name'];
}
```

## Field Type Reference

| Type | Storage | Admin Input |
|------|---------|-------------|
| `text` | string | `<input type="text">` |
| `textarea` | string | `<textarea>` |
| `email` | string | `<input type="email">` |
| `url` | string | `<input type="url">` |
| `html` | string | WP Editor |
| `integer` | int | `<input type="number">` |
| `float` | float | `<input type="number" step="0.01">` |
| `boolean` | bool | `<input type="checkbox">` |
| `date` | string (Y-m-d) | Date picker |
| `select` | string | `<select>` |
| `relation` | int/array | Post search/select |
| `gallery` | array | Media library picker |
| `repeater` | array | Sortable rows |

## Rendering and save-time hardening

- **Defense-in-depth escaping at render.** `$field_id`, `$field_name`, and the derived label are `esc_attr`/`esc_html`'d. Field-config keys are developer-controlled, but defensive escaping prevents a typo'd or third-party CPT registration from introducing an XSS path.
- **Nonce reads use `wp_unslash`** before `wp_verify_nonce` (WP does this internally too; explicit for clarity).
- **JSON-decode failures don't log the payload.** Stride users paste personal data into form fields; logging the raw value would write PII to plaintext logs. The save handler routes through `ntdst_log('metabox')->error()` with the error message only.
- **`isDataModel()` checks the MetaboxGenerator's own registry** rather than calling `ntdst_data()->get($name)`. That call auto-creates a phantom empty model as a side effect. When iterating post types from your own code, use `ntdst_data()->isRegistered($name)` for the same reason.
