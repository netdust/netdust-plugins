# Golden Path — YOOtheme integration (custom Dynamic Content source)

**Read this before planning a YOOtheme Builder source/element.** Build to it; name any deviation in the plan.

> **Origin flag — NOT extracted from Stride.** Stride uses a Tailwind+Alpine+Vite/FSE theme (`stridence`) and has **zero** YOOtheme integration. This golden path is extracted from **Rossi** (`/home/ntdst/Sites/rossi/`, the NTDST-core gallery reference), verified drift-clean against the live `ntdstheme` theme. When a project actually adopts YOOtheme, this is the proven shape; when it doesn't, this doc doesn't apply. Genericised `ntdstheme` → `{theme}`, `artist_profile` → `{type}`.

The single rule that prevents the most painful failure (white-page crash in the Customizer): **resolvers are standalone namespace-prefixed functions referenced by explicit string — never class methods, never closures, never `__NAMESPACE__`.** YOOtheme serialises resolver references to JSON; anything non-serialisable breaks the builder.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `services/yootheme/{Type}SourcesService.php` | Source service + resolver fns | `Event::on('source.init')` registers a `queryType`; standalone resolver returns hydrated posts |
| `services/yootheme/YOOthemeDynamicContentService.php` | **Auto-registration engine (reference — do not copy)** | Reflects Data-Manager models → YOOtheme ObjectTypes; owns `attach_post_meta()` |
| `{theme}/theme-config.php` | Registration | Lists the source services with priorities |

The engine (679 lines in Rossi) auto-creates one ObjectType per Data-Manager model — **you don't write it, and you don't create your own `objectType()`** (drift: *Custom YOOtheme ObjectTypes*). You only add a `queryType` that returns one of those auto-registered types. This golden path extracts the small, teachable `{Type}SourcesService` and references the engine.

Governing reference: **`ntdst-yootheme/references/yootheme.md`** (full Dynamic Content guide, field mapping). This doc shows the source-service shape; the reference holds the field-type tables.

---

## The source service — `{Type}SourcesService.php`

A real `NTDST_Service_Meta` service (priority **21+**, after the engine's 20). It registers a `queryType` on `source.init`. Note the **single-type-not-listOf** trick: returning a single type makes YOOtheme expose the "Multiple Items Source" dropdown for that type's repeater fields.

```php
<?php
/**
 * YOOtheme {Type} Sources Service
 * Registers custom query types for {type} content in YOOtheme Builder.
 * Returning a SINGLE item lets YOOtheme show "Multiple Items Source" for repeater fields.
 */
namespace {theme}\services\yootheme;

defined('ABSPATH') || exit;

use YOOtheme\Event;

class {Type}SourcesService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name'       => '{Type} Sources',
            'admin_only' => false,
            'enabled'    => true,
            'priority'   => 21,                         // AFTER YOOthemeDynamicContentService (20)
            'sectors'    => ['{sector}' => 'essential'], // sector-gated loading (omit if not multi-sector)
        ];
    }

    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        // Wrap in init — Event::on outside an init hook never fires (anti-patterns table).
        add_action('init', function () {
            if (!function_exists('YOOtheme\app')) {     // MANDATORY guard — no YOOtheme, no source
                return;
            }

            Event::on('source.init', function ($source) {
                $source->queryType([                     // queryType, NOT objectType (engine owns objectTypes)
                    'fields' => [
                        'the{Type}Profile' => [
                            'type'     => '{Type}Profile',      // SINGLE type, not ['listOf' => …]
                            'metadata' => ['label' => 'The {Type} Profile', 'group' => '{Type} Platform'],
                            'extensions' => [
                                'call' => [
                                    // EXPLICIT STRING — never __NAMESPACE__, never [$this, 'method'].
                                    'func' => '{theme}\\services\\yootheme\\resolve_the_{type}_profile_single',
                                ],
                            ],
                        ],
                    ],
                ]);
            }, -10);                                     // krsort: -10 runs AFTER base types. Use -10 for most sources.
        });
    }
}

// ── RESOLVER — standalone function, outside the class ──

/**
 * Returns a SINGLE {type} profile so YOOtheme can inspect its repeater fields.
 */
function resolve_the_{type}_profile_single($root, array $args)
{
    $profiles = get_posts([
        'post_type'      => '{type}',
        'posts_per_page' => 1,
        'post_status'    => 'publish',
    ]);
    if (empty($profiles)) {
        return null;
    }
    // Hydrate meta onto the post object for YOOtheme field resolution.
    return attach_post_meta($profiles[0]);
}
```

**Why a standalone function and not a method:** YOOtheme stores `'func' => 'fully\\qualified\\function_name'` in the builder's serialised config. A `[$this, 'resolver']` or a closure can't survive JSON round-trip → white page. `__NAMESPACE__ . '\\fn'` *looks* equivalent but the macro doesn't always resolve at serialise time → same crash. Always the literal string.

**Why `Event::on(..., -10)`:** YOOtheme `krsort()`s listeners — **higher number runs first**. The engine registers base types; your source must run *after* them, so a *lower* priority (`-10`). (See `yootheme.md` → Event Priority.)

---

## The shared hydrator — `attach_post_meta()` (engine-owned, reference)

You call it; you don't write it. It lives in `YOOthemeDynamicContentService.php` and does the safety work that keeps the builder alive: schema-filters meta (only Data-Manager fields, drops `_`-prefixed internals), converts `DateTime` → string, and skips non-serialisable objects.

```php
// reference only — owned by the engine
function attach_post_meta($post)
{
    if (!$post) return $post;

    $meta = get_post_meta($post->ID);
    $post->meta = []; $post->fields = [];

    // Pull the Data-Manager schema so only declared fields are exposed (prevents leaking arbitrary meta).
    $schema_fields = [];
    if (function_exists('ntdst_data')) {
        try {
            $model = ntdst_data()->get($post->post_type);
            // … reflect $model->schema → array_keys …
            $schema_fields = array_keys($schema);
        } catch (\Exception $e) { /* schema not available — fail open to no fields */ }
    }

    foreach ($meta as $key => $val) {
        if (strpos($key, '_') === 0) continue;                           // drop WP internals
        if (!empty($schema_fields) && !in_array($key, $schema_fields)) continue;  // only schema fields
        $value = maybe_unserialize($val[0] ?? '');
        if ($value instanceof \DateTime) $value = $value->format('Y-m-d H:i:s');   // DateTime → string
        if (is_object($value) && !($value instanceof \stdClass)) continue;          // skip non-serialisable
        $post->meta[$key] = $value;
        $post->fields[$key] = $value;
    }
    return $post;
}
```

**Always run returned posts through `attach_post_meta()`.** A resolver that returns a raw `WP_Post` gives YOOtheme no `->fields`, and every mapped field renders empty.

---

## Registration — `theme-config.php`

Services are listed with full namespace strings; the loader respects `priority` and `sectors` metadata.

```php
// {theme}/theme-config.php
'global' => [
    // YOOtheme integration (framework — the engine, always needed)
    '{theme}\\services\\yootheme\\YOOthemeDynamicContentService',   // priority 20 — the engine
    '{theme}\\services\\yootheme\\YOOthemeAssetControlService',
    // Your sector sources (priority 21+, sector metadata gates loading)
    '{theme}\\services\\yootheme\\{Type}SourcesService',            // priority 21
],
```

---

## How to adapt — what changes per project, what never does

**Changes per project:**
1. **Type + post type** — `{Type}` class prefix, `{type}` post-type slug, the auto-registered ObjectType name (`{Type}Profile`).
2. **Query field name + label/group** — what shows in the builder's Dynamic Content dropdown.
3. **Resolver query** — `get_posts()` args (single vs list, filters, ordering).
4. **listOf vs single** — single type to expose repeater sub-fields; `['listOf' => 'Type']` for a collection (Grid/List of many items).
5. **Sector gating** — `sectors` metadata if the theme is multi-tenant; omit for single-sector.
6. **Priority** — 21+ for a normal source; nudge higher only if ordering against another custom source matters.

**Never changes:**
- No custom `objectType()` — use the engine's auto-registered types.
- Resolver is a **standalone namespace-prefixed function**, referenced by **explicit string** (never `__NAMESPACE__`, method, or closure).
- `function_exists('YOOtheme\app')` guard before any `Event::on`.
- `Event::on` wrapped in an `init` action.
- Returned posts hydrated via `attach_post_meta()`.
- `DateTime` → string; no non-serialisable objects in returned data.
- Source priority 21+ (engine is 20).

---

## Cross-references

- Governing reference: `ntdst-yootheme/SKILL.md` + `references/yootheme.md` (field-type mapping, repeater items, troubleshooting table).
- Anti-patterns this slice satisfies: `anti-patterns.md` → *Custom YOOtheme ObjectTypes*, *`__NAMESPACE__` in YOOtheme Resolvers*, *Wrong Config File Name* (use `theme-config.php`).
- Drift categories: the nine `ntdst-drift-reviewer` categories are PHP-layering rules; YOOtheme conformance is governed by the `yootheme.md` anti-pattern table (white-page-crash class), not the nine — verify against that table, not the drift greps.
- Source project for this exemplar: `rossi/app/content/themes/ntdstheme/services/yootheme/ArtistSourcesService.php` (the slice) + `YOOthemeDynamicContentService.php` (the engine).
