# Golden path — a content type with fields, a taxonomy, and two API actions

**Verified against source:** 2026-08-08, `ntdst-core` @ daan `45b8158`
(`api/Data.php`, `api/Endpoints.php`, `admin/MetaboxGenerator.php`), and against a live consumer,
`daan-core/services/musician/DiscographyService.php`.

This is the complete vertical slice for the most common ntdst-core feature: **a custom post type with
typed fields, a taxonomy, an auto-generated metabox, an anonymous read action, and a
capability-gated write action.** Build to it. A deviation is fine — name and justify it in the plan.

If a call below does not exist in *this project's* `ntdst-core`, you are on an older fork. Check the
file named above before working around it.

---

## The whole thing

```php
<?php

declare(strict_types=1);

namespace harbor\services\venue;

use NTDST_Data_Manager;
use NTDST_Response;
use NTDST_Service_Meta;

defined('ABSPATH') || exit;

final class VenueService implements NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name'        => 'Venue',
            'description' => 'Venues, their capacity, and the public venue list.',
            'priority'    => 8, // data models register early — see the priority bands
        ];
    }

    public function __construct(
        private readonly NTDST_Data_Manager $data,
    ) {
        $this->init();
    }

    private function init(): void
    {
        $this->registerModel();
        $this->registerApiActions();
    }

    // =====================================================================
    // 1. THE MODEL — CPT + fields + taxonomy + metabox, in one declaration
    // =====================================================================

    private function registerModel(): void
    {
        $model = $this->data->register('venue', [
            // `label` is the switch that makes this a real post type. Without
            // it you get a field schema with no CPT behind it.
            'label'  => 'Venues',
            'labels' => [
                'name'          => 'Venues',
                'singular_name' => 'Venue',
                'add_new_item'  => 'Add New Venue',
                'edit_item'     => 'Edit Venue',
            ],

            // PRIVATE BY DEFAULT — opt IN to visibility, every time.
            'public'      => true,
            'has_archive' => true,
            'show_in_rest' => true,
            'supports'    => ['title', 'editor', 'thumbnail'],
            'rewrite'     => ['slug' => 'venues'],
            'menu_icon'   => 'dashicons-location',

            // Give the type its OWN capabilities so a capability floor can be
            // derived for it. With 'post' you inherit the generic caps and
            // every floor collapses to `edit_others_posts`.
            'capability_type' => ['venue', 'venues'],
            'map_meta_cap'    => true,

            // Fields drive validation, the metabox, and the query builder.
            // Short form is `'name' => 'type'`; long form adds label/options.
            'fields' => [
                'capacity' => [
                    'type'        => 'integer',
                    'label'       => 'Capacity',
                    'description' => 'Maximum standing attendance.',
                    'min'         => 0,
                ],
                'address' => [
                    'type'  => 'text',
                    'label' => 'Address',
                ],
            ],

            // Optional: group fields into a tabbed metabox.
            'field_groups' => [
                'location' => ['title' => 'Location', 'fields' => ['address']],
                'capacity' => ['title' => 'Capacity', 'fields' => ['capacity']],
            ],
            'use_tabs'       => true,
            'metabox_title'  => 'Venue Details',

            // The PUBLIC SHAPE, declared once. Every anonymous read narrows to
            // exactly this, so no handler hand-rolls a projection.
            'public_fields' => [
                'id', 'title', 'excerpt', 'content', 'permalink',
                'slug', 'date', 'thumbnail', 'terms', 'meta',
            ],

            // The public CONSTRAINT, kept independent of the shape above.
            'scopes' => [
                'public' => fn($q) => $q->where('post_status', 'publish'),
            ],

            // Taxonomies declared WITH the model. Registered on this post type
            // only after the CPT itself registers. `terms` are seeded
            // idempotently — no ensureDefaultTerms() helper needed.
            'taxonomies' => [
                'venue_region' => [
                    'label'             => 'Region',
                    'hierarchical'      => true,
                    'public'            => true,
                    'show_admin_column' => true,
                    'show_in_rest'      => true,
                    'rewrite'           => ['slug' => 'region'],
                    'terms'             => [
                        'north' => 'North',
                        'south' => 'South',
                    ],
                ],
            ],
        ]);

        // Registration FAILS CLOSED and LOUDLY. An invalid or reserved name
        // returns WP_Error; swallowing it leaves a half-registered phantom
        // that reports healthy. Never ignore this return value.
        if (is_wp_error($model)) {
            ntdst_log('venue')->error('Venue model failed to register', [
                'error' => $model->get_error_code() . ': ' . $model->get_error_message(),
            ]);
        }
    }

    // =====================================================================
    // 2. THE API ACTIONS
    // =====================================================================

    private function registerApiActions(): void
    {
        // -----------------------------------------------------------------
        // ANONYMOUS READ. `public => true` is the ONLY way an action becomes
        // reachable logged-out, and it is never floored by a capability.
        // -----------------------------------------------------------------
        ntdst_api_action('list_venues', function ($data, $params) {
            // A caller may narrow the page size, not name it. The ceiling is
            // what stops `limit=100000`.
            $limit  = min(absint($params['limit'] ?? 20), 100);
            $region = isset($params['region']) ? sanitize_text_field($params['region']) : null;

            $query = $this->data->get('venue')
                ->scope('public')          // publish-only, stated not inherited
                ->orderBy('title', 'ASC');

            if ($region !== null && $region !== '') {
                $query->whereTax('venue_region', $region);
            }

            // publicRows() emits the model's declared public_fields shape.
            return NTDST_Response::apiSuccess($query->limit($limit)->publicRows());
        }, ['public' => true]);

        // -----------------------------------------------------------------
        // GATED WRITE. `cap_type` derives the capability FROM THE POST TYPE
        // and enforces it AT DISPATCH, ahead of this handler — so the gate
        // holds even if the handler below is later edited badly. It is
        // FAIL-CLOSED: an unresolvable capability denies everyone, admins too.
        // -----------------------------------------------------------------
        ntdst_api_action('update_venue_capacity', function ($data, $params) {
            $id       = absint($params['id'] ?? 0);
            $capacity = absint($params['capacity'] ?? 0);

            if ($id === 0) {
                return new \WP_Error('invalid_id', 'Venue ID is required', ['status' => 400]);
            }

            // The floor is defense in depth, ALONGSIDE this per-row check —
            // never instead of it.
            if (!current_user_can('edit_post', $id)) {
                return new \WP_Error('forbidden', 'Permission denied', ['status' => 403]);
            }

            // Friendly vocabulary: `title`, not `post_title`. Unknown keys are
            // logged and dropped, never written.
            $result = $this->data->get('venue')->update($id, ['capacity' => $capacity]);

            if (is_wp_error($result)) {
                return $result;
            }

            return NTDST_Response::apiSuccess(['id' => $id, 'capacity' => $capacity]);
        }, ['cap_type' => 'venue']);
    }
}
```

## If you give the type its own `capability_type`, you must grant the caps

**WordPress does not do this for you, and the trap is that it looks like it does.** `map_meta_cap`
maps *meta* capabilities (`edit_post`) onto primitives; it never *invents* primitive ones. A custom
`capability_type` therefore produces capability names held by **no role at all — administrator
included**. Probed live on a real site: with `capability_type => ['access_grant','access_grants']`
and nothing else, an administrator's `edit_access_grants` check returns **deny**.

So the registration alone does not narrow access to administrators — it denies everyone, which breaks
the operator as thoroughly as an over-permissive type exposes the data.

Grant on **`init`**, not `after_setup_theme`. Services boot on `after_setup_theme` (core at priority
5, features at 15), and a CPT registered in a service constructor exists only from that moment — so a
grant hooked on `after_setup_theme:10` runs *before* a feature service registered its type,
`get_post_type_object()` returns `null`, and the grant silently no-ops. `init` fires after all of
`after_setup_theme` and is unconditionally safe.

```php
add_action('init', function (): void {
    // Version-stamp it: this runs on EVERY request, so it must not write on every request.
    if (get_option('harbor_venue_caps_version') === '1') {
        return;
    }

    $type = get_post_type_object('venue');
    $role = get_role('administrator');

    if (!$type instanceof \WP_Post_Type || !$role instanceof \WP_Role) {
        return;
    }

    // Read the capability list OFF THE REGISTERED OBJECT — never hardcode it.
    // WordPress derives the set from capability_type and that set has grown
    // across releases; a hardcoded copy silently stops covering one and the
    // failure mode is a denied administrator with no obvious cause.
    foreach ((array) $type->cap as $cap) {
        if (is_string($cap) && $cap !== '') {
            $role->add_cap($cap);
        }
    }

    update_option('harbor_venue_caps_version', '1');
});
```

**Which capability does `cap_type` actually resolve to?** The post type object's own
`cap->edit_others_posts`. With `capability_type => ['venue','venues']` that is **`edit_others_venues`**;
with the default `capability_type => 'post'` it is the generic `edit_others_posts`. It is read off the
registered type at dispatch, never hardcoded — and if it cannot be resolved to a non-empty string the
floor denies everyone.

**Decide deliberately:** `capability_type => 'post'` (the default) means every capability floor for
this type collapses to the generic `edit_others_posts` — simple, and correct when the type carries no
data more sensitive than a post. Its own `capability_type` gives a distinct, separately grantable
capability — required when the type holds something a generic Editor should not reach. Pick the
second only if you are also going to grant the caps.

## Wiring it so the framework boots it

The service must be reachable by the bootstrap. Either list it in the project's bootstrap config
(`plugin-config.php` in a mu-plugin, `config/theme-config.php` in a theme) under `services`, or place
it as `*Service.php` at a discovery-path root or in an enabled sector directory — **discovery matches
`*Service.php` at those two places only; a namespaced class in any other subdirectory must be listed
explicitly or it silently never loads.**

Disable it without deleting code, in precedence order (most restrictive first):

```php
// Slug is derived from the CLASS NAME: VenueService -> `venue`.
// metadata()['name'] does NOT change it.
add_filter('ntdst_service_venue_enabled', '__return_false');   // runtime
update_option('ntdst_service_venue', '0');                     // UI / DB
```

Override its config from the bootstrap config array:

```php
'services' => [
    'overrides' => [
        'venue' => ['default_limit' => 50],   // reaches ntdst_service_venue_config
    ],
],
```

## Reading the data back

```php
$venues = ntdst_data()->get('venue');

$one = $venues->find($id);              // WP_Post or WP_Error — an OBJECT
if (is_wp_error($one)) { /* handle */ }
$cap = $one->fields['capacity'];        // fields are unprefixed

$rows = $venues->where('capacity', ['>', 500])  // [operator, value] for comparisons
               ->withMeta()                     // batch the meta — avoids N+1
               ->limit(20)
               ->get();                         // ARRAY of arrays, not objects
$title = $rows[0]['title'];
```

**`find()` returns an object; `get()` returns arrays of arrays.** Array-accessing a `find()` result is
a fatal, and it is the most common bug in this layer.

In production code, put these reads behind that domain's repository — `ntdst_data()->get('venue')`
should appear in one file per post type.

## What this slice deliberately does not do

- **No `register_post_type()` / `register_taxonomy()` call.** The wrapper is the contract; bypassing
  it breaks validation, the metabox, the query builder, and the repository contract.
- **No `add_action('wp_ajax_*')`.** `ntdst_api_action()` carries the nonce, origin, rate-limit and
  capability gates. Registering the underlying filter by hand forfeits all of them.
- **No metabox code.** The metabox is generated from `fields`; set `'auto_metabox' => false` only if
  you are deliberately rendering your own.
- **No cache calls.** This copy has no query cache; core already invalidates post, meta and term
  entries on save and delete.
