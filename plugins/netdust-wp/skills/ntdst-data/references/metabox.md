# NTDST MetaboxGenerator

Auto-generates WordPress metaboxes from field definitions.

**Location:** `mu-plugins/ntdst-core/admin/MetaboxGenerator.php` (under the project's
content dir — `web/app/` on Bedrock, `app/content/` elsewhere).

## Automatic Generation

Metaboxes are generated when a model is registered with **both** a `label` and a
non-empty `fields` map (a `label` is what makes `register()` call `register_post_type()`
at all). Set `'auto_metabox' => false` to opt out.

> The registration below is **private** — `register()` merges your config over
> `['public' => false, 'has_archive' => false, …]`. Add `'public' => true` deliberately
> if the type should be publicly queryable.

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

`render_field()` is a `switch` with a `default` arm. A type with no case falls through to
a **plain text input** — it is not an error, just silently the wrong control.

| Type | Admin UI |
|------|----------|
| `text` / `string` | Text input |
| `textarea` / `longtext` | Textarea |
| `email` | `<input type="email">` |
| `url` | `<input type="url">` |
| `wysiwyg` | **WordPress editor** (`wp_editor`, teeny mode, no media buttons) |
| `integer` / `int` | Number input, `step="1"` |
| `float` / `decimal` | Number input, `step="0.01"` |
| `boolean` / `bool` | Checkbox |
| `date` | `<input type="date">` |
| `datetime` | `<input type="datetime-local">` |
| `select` | Dropdown (needs `options`) |
| `array` / `json` | JSON textarea |
| `relation` | Autocomplete post/user selector |
| `gallery` | Media library picker with drag-reorder |
| `repeater` | Sortable rows |
| `callback` | Your own callable renders everything |
| `image` / `file` | **Media-picker cell** (`render_repeater_media_cell()`, reused verbatim from the repeater arm). Storage stays an INT — `sanitizeAttachmentId()` returns 0 for nothing, not the repeater arm's empty-string marker. |
| **`person`, `post_relation`** | **No case — plain text input.** They sanitize correctly, they just have no control. |
| **`html` / `content`** | **No case — plain text input.** Use `wysiwyg` for the editor. |
| **`number`** | **No case at top level — plain text input.** `number` is a REPEATER SUB-FIELD type only. Use `integer` or `float` on a top-level field. |

### The two vocabularies are not the same set

The **registerable** vocabulary is `NTDST_Data_Model::getDefaultSanitizer()`; the
**renderable** one is this switch. They overlap but neither contains the other.

`string`, `longtext`, `decimal`, `datetime` and `callback` render fine but are
**not** in the sanitizer map (`number` renders only as a repeater sub-field) — `register()` now **throws `InvalidArgumentException`** on
an unknown type, so declaring one of them fails at registration unless the field config
also supplies its own `'sanitizer' => fn($v) => …` (which short-circuits the lookup).

## Field Options

### Labels, descriptions, placeholders — mostly NOT implemented

> **The admin label is always derived from the field KEY**:
> `ucwords(str_replace('_', ' ', $name))`. A `'label' => …` on a top-level field is read
> by nothing. `client_name` renders as "Client Name" whatever you write.
> (`label` **is** honoured for **repeater sub-fields**.)
>
> `'description'` is read only by the `relation`, `gallery` and `repeater` renderers.
> `'placeholder'` is read only by `relation`. On a scalar field both are ignored.
>
> To change a scalar field's visible label today, rename the field key — or render the
> group yourself with `'auto_metabox' => false`.

```php
'fields' => [
    // The label here is decorative; the UI shows "Client Name" from the key.
    'client_name' => [
        'type' => 'text',
        'required' => true,
    ],
    // description/placeholder DO reach the renderer for these three types:
    'related' => [
        'type' => 'relation',
        'post_type' => 'artist',
        'description' => 'Pick the credited artist',
        'placeholder' => 'Search artists…',
    ],
]
```

### Required Fields

```php
'fields' => [
    'email' => [
        'type' => 'email',
        'required' => true,  // enforced by validateData() on create()
    ],
]
```

`required` is enforced in TWO places, and they are not the same control.

**Save-time (the contract):** `NTDST_Data_Model::validateData()`, and only on `create()`.
`update()` is a partial write, so a field absent from the payload keeps its existing
value rather than failing.

**Render-time (the affordance):** the metabox DOES mark it. `render_field()` emits a
`*` marker in the label and, where the browser can honour it, the native `required`
attribute plus `aria-required="true"` on the control. Native validation is withheld —
marker and `aria-required` on the wrapper only — for a `readonly` field and for
`MARKER_ONLY_REQUIRED_TYPES`: `boolean`, `bool`, `wysiwyg`, `relation`, `gallery`,
`repeater`, `image`, `file`. Those are controls the browser cannot focus, or that do not
carry the value themselves, so a native `required` on them blocks the form with nothing
the editor can click.

### Default Values — NOT IMPLEMENTED

> **`'default' => …` is read by nothing** in `Data.php` or `MetaboxGenerator.php`
> (verified against source). An unset field is simply empty; a `select` renders with its
> first option selected because that is what a `<select>` does, not because a default was
> applied. Apply defaults in your own code:
> `$status = $model->getMeta($id, 'status') ?: 'pending';`

**Note:** When setting WordPress post status in `create()` or `update()`, use the
`'post_status'` key (not `'status'`) to avoid collision with a custom meta field named
`status`.

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
        'min' => 1,   // save-time validation (item count), NOT a UI limit
        'max' => 20,  // ditto — the picker will not stop the user at 20
    ],
]
```

### Repeater Fields

The sub-field map key is **`sub_fields`**, not `fields`. Both `Data.php`
(`setupSanitizers`, `sanitizeRepeater`) and `MetaboxGenerator` (`render_repeater_field`,
save-side sanitization) read `sub_fields`. A repeater declared with `fields` gets an
**empty** sub-field config: the admin renders no row inputs, and every sub-value falls
back to `sanitize_text_field` on save — so an `image` sub-field stores an unverified
number and a `wysiwyg` sub-field loses its markup.

```php
'fields' => [
    'social_links' => [
        'type' => 'repeater',
        'sub_fields' => [
            'platform' => [
                'type' => 'select',
                'label' => 'Platform',   // labels ARE honoured on sub-fields
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

Sub-field types are sanitized as their declared type on write. They are **not** filtered
on read: `formatRepeaterField()` returns rows largely as stored, so a top-level
allow-list projection does not filter sub-keys. Project repeater rows explicitly before
sending them to an anonymous caller.

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

> **⚠ NOT IMPLEMENTED IN ntdst-core (verified 2026-08-03).** `MetaboxGenerator.php`
> contains **zero** references to `condition` in any deployed copy of the framework
> (checked across five projects, 1572–1672 lines each), and the canonical
> `metabox-fields.js` handles none either. The API below is the *intended* contract,
> not working behaviour.
>
> If a project needs conditional fields, it must implement the JS layer itself —
> and it should do so **under this exact key and shape**, so the work converges on
> the framework's contract and can be upstreamed into ntdst-core later instead of
> becoming per-project drift. Verify before relying on it:
> `grep -c condition <project>/…/ntdst-core/admin/MetaboxGenerator.php`

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

## Validation

```php
'fields' => [
    'website' => [
        'type' => 'url',
        'validate' => fn($v) => str_starts_with($v, 'https://') ?: 'Must be HTTPS URL',
    ],
]
```

`validate` (and `required` / `min` / `max`) run in `NTDST_Data_Model::validateData()`,
which is called from `create()` and `update()` and returns a
`WP_Error('validation_failed')` carrying a per-field error map in its error data. **The
metabox save path does not render those messages inline** — treat validation as a data
contract enforced on write, and surface failures yourself if the editor needs to see
them.

## Metabox Placement and Title

These are **flat top-level config keys**, not a nested `'metabox' => [...]` array:

```php
ntdst_data()->register('portfolio', [
    'label' => 'Portfolio',
    'fields' => [...],

    // Single (ungrouped) metabox:
    'metabox_title'    => 'Project Details',  // default: "<Model Name> Fields"
    'metabox_context'  => 'normal',           // 'normal' | 'side' | 'advanced'
    'metabox_priority' => 'high',             // 'high' | 'low' | 'default'

    // When use_tabs is on, the tabbed box uses these instead:
    'tabs_context'  => 'normal',
    'tabs_priority' => 'high',
]);
```

With `field_groups` and **no** `use_tabs`, each group becomes its own metabox and takes
`context` / `priority` / `title` from **that group's** config (defaults: `normal`,
`default`, and the group key title-cased). Any field not named in a group lands in an
automatic **"Other Fields"** box at `normal`/`low`.

`'auto_metabox' => false` skips generation entirely so a service can render its own.

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

## Other field options that ARE implemented

| Option | Applies to | Effect |
|--------|-----------|--------|
| `readonly` | scalar fields | Renders the value as static text plus a hidden input. On `select`: rendered `disabled` plus a hidden input. On `array`/`json`: **ignored** — the textarea stays editable |
| `options` | `select` | The `value => label` map |
| `post_type` | `relation` | Type to search. `'user'` switches the control to a user search |
| `user_role` | `relation` with `post_type => 'user'` | Restricts the user lookup and the `data-user-role` attribute the JS searches with |
| `multiple` | `relation` | Single vs multi select (default **true**) |
| `callback` | `callback` | Called as `$callback($post, $fieldKey, $value)`; renders everything itself, including its own label |
| `sanitizer` | any | Overrides the type's default sanitizer — and bypasses the unknown-type throw |
| `sub_fields` | `repeater` | Sub-field type map (see above) |

## Accessing values / field type reference

See `data-orm.md` → **Field Types Reference** for the canonical write-sanitizer and
read-cast per type. Do not maintain a second copy here; the two lists diverging is how
`select`, `date` and `wysiwyg` came to be documented as sanitized while they were not.

## Rendering and save-time hardening

- **Defense-in-depth escaping at render.** `$field_id`, `$field_name`, and the derived label are `esc_attr`/`esc_html`'d. Field-config keys are developer-controlled, but defensive escaping prevents a typo'd or third-party CPT registration from introducing an XSS path.
- **Nonce reads use `wp_unslash`** before `wp_verify_nonce` (WP does this internally too; explicit for clarity).
- **JSON-decode failures don't log the payload.** Stride users paste personal data into form fields; logging the raw value would write PII to plaintext logs. The save handler routes through `ntdst_log('metabox')->error()` with the error message only.
- **`isDataModel()` checks the MetaboxGenerator's own registry** rather than calling `ntdst_data()->get($name)` — asking a question should not be a registration. `get()` no longer creates a phantom (it returns an unstored empty model on a miss, and a CLONE on a hit), but it still answers "yes, here is a model" for a name nobody registered. When iterating post types from your own code, use `ntdst_data()->isRegistered($name)`, which is the only one that distinguishes them.
