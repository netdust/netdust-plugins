# Golden Path — Content-type feature (CPT → Repository → Service → frontend)

> **Rewritten for ntdst-core 5.0.0** — anchored on `api/Data.php` (`NTDST_Data_Manager::register()`, `NTDST_Data_Model`), `api/FieldTypes.php`. Re-verify with the drift-reviewer grep set when the source moves; `/skill-audit` flags this after 90 days.

**Read this before planning a CPT-backed domain object.** Build to this slice, not to the nearest sibling file (siblings drift — see `lessons.md`). Deviations are allowed but must be *named* in the plan.

5.0.0 closed the field vocabulary to **17 names**: `int` · `float` · `bool` · `text` · `textarea` · `html` · `email` · `url` · `date` · `select` · `array` · `json` · `relation` · `gallery` · `image` · `file` · `repeater`. No aliases, no filter, no registration method — a name outside this list is a fatal at `register()`. It also moved field-level publication from a whole-model flag to a per-field opt-in: **`show_in_rest => true` on the field**, not on the model.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `Modules/{Module}/{Type}CPT.php` | CPT registration | One `ntdst_data()->register()` call: post type, meta prefix, field schema, `rest_base` |
| `Modules/{Module}/{Type}Repository.php` | Repository | The only place that calls `ntdst_data()->get('{type}')` |
| `Modules/{Module}/{Type}Service.php` | Service | Business logic only — typed/composite/event/cached reads, no pass-throughs |
| `Modules/{Module}/{Type}ListRoute.php` (only if needed) | Custom REST route | Logic `/wp/v2/{type}` cannot express — see "When `/wp/v2` is not enough" |
| `themes/{theme}/single-{type}.php` | Frontend template | Resolves the repository via `ntdst_get()`, escapes on output |

Governing reference: **`ntdst-framework/SKILL.md`** (`## Pick the door`, `## Data declares, WordPress reads`), **`ntdst-framework/references/traps.md`**. This doc does not restate those rules — it shows the shape they produce.

The code below is one worked example (`Acme\Modules\Editions`, a course-edition CPT) so every block is real, lintable PHP — rename the namespace, class and post type to your own project's.

---

## 1. CPT registration — `{Type}CPT.php`

Static `register()`, called from the owning service's `init()`. The field schema is **the single source of truth** for this type's meta — declare a field here once, never in a second place.

```php
<?php
declare(strict_types=1);

namespace Acme\Modules\Editions;

final class EditionCPT
{
    public const POST_TYPE = '{type}';   // referenced everywhere via the constant — never the raw string

    public static function register(): void
    {
        ntdst_data()->register(self::POST_TYPE, [
            'meta_prefix' => '_{prefix}_',
            'label'       => 'Edities',
            'labels'      => [ /* singular_name, add_new, edit_item, … */ ],

            // PRIVATE BY DEFAULT (5.0.0) — register() merges 'public' => false
            // over whatever is not stated. Opt IN explicitly.
            'public'             => true,
            'publicly_queryable' => true,
            'show_ui'            => true,
            'show_in_menu'       => '{project}-dashboard',
            'menu_icon'          => 'dashicons-calendar-alt',
            'rewrite'            => ['slug' => 'edities', 'with_front' => false],

            // rest_base names the /wp/v2 collection this type reads through —
            // 'edities' here, so plain reads go to /wp/v2/edities.
            'rest_base' => 'edities',

            'fields' => self::getFields(),
        ]);
    }

    /**
     * Field schema = single source of truth. Only the fields the FRONT END
     * READS carry `show_in_rest => true` — that flag is WordPress's own
     * meaning, "opt in", and it is per FIELD, never inherited from the model:
     * a declared field with `show_in_rest => true` is public to anyone who
     * can read `/wp/v2/{type}`, whether or not the post itself is public.
     */
    private static function getFields(): array
    {
        return [
            'course_id'  => ['type' => 'int',   'label' => 'Cursus',      'required' => true],
            'start_date' => ['type' => 'date',  'label' => 'Startdatum',  'required' => true, 'show_in_rest' => true],
            'capacity'   => ['type' => 'int',   'label' => 'Capaciteit',  'required' => true],
            'price'      => ['type' => 'float', 'label' => 'Prijs',       'show_in_rest' => true],
            'venue'      => ['type' => 'text',  'label' => 'Locatie',     'show_in_rest' => true],
            'notes'      => ['type' => 'html',  'label' => 'Interne notities'],   // NOT show_in_rest — internal only

            // A repeater publishes ALL-OR-NOTHING: every sub_field must
            // declare its own show_in_rest, or the whole repeater is
            // unpublishable (warns once, reads back null on /wp/v2).
            'session_slots' => [
                'type'       => 'repeater',
                'label'      => 'Sessie slots',
                'show_in_rest' => true,
                'sub_fields' => [
                    'starts_at' => ['type' => 'date', 'label' => 'Start', 'show_in_rest' => true],
                    'seats'     => ['type' => 'int',  'label' => 'Plaatsen', 'show_in_rest' => true],
                ],
            ],
        ];
    }
}
```

**Why declare `show_in_rest` per field, deliberately, and not "on everything":** `custom-fields` support is per TYPE, not per key — one declared field turns it on for the whole post type, and WordPress then also emits every OTHER key some unrelated code registered globally with `register_post_meta('post', …, 'show_in_rest' => true)`, plus the editor's Custom Fields panel for anyone holding `edit_post`. `notes` above stays off `show_in_rest` on purpose: it is internal, and the model constructor still refuses a `json`/`array` field that claims it (neither ever publishes — no closed schema names their keyed values), so the vocabulary catches the mistake you cannot make by accident, only the one you make on purpose.

---

## 2. Repository — `{Type}Repository.php`

The **single mediator** for `{type}` data. `ntdst_data()->get('{type}')` is called nowhere else — a service, template or handler reaching for it directly bypasses the repository's vocabulary.

```php
<?php
declare(strict_types=1);

namespace Acme\Modules\Editions;

final class EditionRepository
{
    public function findByCourse(int $courseId): array
    {
        return ntdst_data()->get(EditionCPT::POST_TYPE)
            ->where('course_id', $courseId)
            ->where('post_status', 'publish')
            ->orderBy('start_date', 'ASC')
            ->withMeta()
            ->get();
    }

    /** @return object|\WP_Error no native union declared: `object` already encompasses `WP_Error`, so PHP refuses that as a return TYPE. */
    public function find(int $id)
    {
        return ntdst_data()->get(EditionCPT::POST_TYPE)->find($id);
    }

    /** @return object|\WP_Error */
    public function create(array $data)
    {
        return ntdst_data()->get(EditionCPT::POST_TYPE)->create($data);
    }

    /** @return object|\WP_Error */
    public function update(int $id, array $data)
    {
        return ntdst_data()->get(EditionCPT::POST_TYPE)->update($id, $data);
    }
}
```

**Reads are publish-only by default** — `find()` and `getMeta()` alike. An admin screen that wants a draft says `find($id, 'any')` explicitly; the repository does not decide that for its callers.

---

## 3. Service — `{Type}Service.php`

Business logic only: typed coercion, composite decisions, event firing, cached reads. **No method that is only `return $this->repository->X(...)`.**

```php
<?php
declare(strict_types=1);

namespace Acme\Modules\Editions;

final class EditionService
{
    public function __construct(private readonly EditionRepository $repository) {}

    public function init(): void
    {
        EditionCPT::register();
    }

    // Composite decision — multi-source, real logic, so it earns its place.
    public function canEnroll(int $editionId): bool
    {
        $edition = $this->repository->find($editionId);

        return !is_wp_error($edition)
            && $edition->post_status === 'publish'
            && (int) ($edition->fields['capacity'] ?? 0) > 0;
    }
}
```

---

## 4. Reads go to `/wp/v2/{type}` — never a custom route for a plain list

A declared field's `show_in_rest => true` is the WHOLE of what a plain collection needs. WordPress serves it on `/wp/v2/{rest_base}`; core shapes no response of its own.

```js
// theme JS — a plain, unfiltered collection read
const editions = await wp.apiFetch({ path: '/wp/v2/edities?per_page=20' });
```

### When `/wp/v2` is not enough

A custom route through `ntdst_rest()` earns its place only for logic the collection cannot express — an aggregate, a cross-type join, a computed field no schema names. **A single meta-key filter is not that case.** Do not hand-roll `rest_{type}_collection_params` + `rest_{type}_query`, and do not add a list route whose only job is "filtered by one meta key" — read `ntdst-core/docs/parked/rest-query.md`: a filterable field over `/wp/v2/{type}` is a parked core feature waiting for its first real consumer, not a site hand-roll.

```php
<?php
declare(strict_types=1);

// A route that earns its place: cross-type aggregation /wp/v2 cannot do.
ntdst_rest('{project}/v1')->get('/editions/upcoming-summary', [$service, 'upcomingSummary']);
```

---

## 5. Frontend template — `single-{type}.php`

Resolve the repository via `ntdst_get()` (themes have no constructor DI); never call `ntdst_data()` directly from a template.

```php
<?php
/** single-{type}.php — theme presentation only, no business logic. */
defined('ABSPATH') || exit;

$edition_id = get_the_ID();

$editions = ntdst_get(\Acme\Modules\Editions\EditionRepository::class);
$edition  = $editions->find($edition_id);

if (is_wp_error($edition)) {
    return;
}

// Output: escape everything (netdust-wp:wp-security's Escape pillar).
echo esc_html($edition->fields['venue'] ?? '');
```

---

## How to adapt — what changes per project, what never does

**Changes per project:**
1. **Names** — `{Project}` namespace, `{Module}` folder, `{Type}` class prefix.
2. **Post type slug + `rest_base`** — the `POST_TYPE` constant and the `/wp/v2/{rest_base}` it reads on.
3. **Meta prefix** — `_{prefix}_`, declared once in the CPT.
4. **Field schema** — the `getFields()` array; which fields carry `show_in_rest => true` is a per-field security decision, not a blanket one.
5. **Domain queries** — which `findByX()` methods the repository needs.
6. **Custom list route** — only if the collection genuinely cannot express the query; check `rest-query.md` first.

**Never changes (the framework spine):**
- `ntdst_data()->get()` appears **only** in `*Repository.php`.
- The service injects the repository, not a sibling service to reach one.
- No pure pass-through service methods.
- `show_in_rest` is declared per field, and a repeater is all-or-nothing.
- Plain reads go to `/wp/v2/{type}`; a custom route earns its place on logic the collection cannot express.
- Theme resolves the repository via `ntdst_get()`; never `ntdst_data()` in a template.
- Output escaped at the template boundary.

---

## Cross-references

- Governing references: `ntdst-framework/SKILL.md` (`## Data declares, WordPress reads`, `## Pick the door`), `ntdst-framework/references/traps.md`.
- `docs/parked/rest-query.md` (in `ntdst-core`) — the filterable-collection feature waiting for its first consumer; read it before writing a meta-filter list route.
- The admin edit/list screen for this CPT is its own slice — see `golden-paths/admin-settings-page.md` for the framework-clean admin pattern.
- A write route on this type (a create/update form) is `golden-paths/form-data-flow.md` — the repository is the same one this slice builds.
