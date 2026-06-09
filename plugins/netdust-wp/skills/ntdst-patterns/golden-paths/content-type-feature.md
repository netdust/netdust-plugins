# Golden Path — Content-type feature (CPT → Repository → Service → Router → frontend)

> **Verified against source: 2026-06-09** — Stride `Modules/Edition/` (CPT/Repo/Service/Router). Re-verify with the drift-reviewer grep set (check #11) when the source moves or drifts; `/skill-audit` flags this after 90 days.

**Read this before planning a CPT-backed domain object.** Build to this slice, not to the nearest sibling file (siblings drift — see `lessons.md`). Deviations are allowed but must be *named* in the plan.

**Extracted from** Stride's `Edition` module (`Stride\Modules\Edition\*`), verified drift-clean against the live source on the CPT/Repo/Service/Router spine. The two parts that drift in Stride are called out explicitly below — **do not copy those parts.**

Genericised `Stride` → `{Project}`, `vad_edition` → `{type}`, `_ntdst_` → the project's meta prefix. Everything else is real Stride code.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `Modules/{Module}/{Type}CPT.php` | CPT registration | One `ntdst_data()->register()` call: post type, meta prefix, field schema, rewrite slug |
| `Modules/{Module}/{Type}Repository.php` | Repository | `extends AbstractRepository` — **the only** place that touches `ntdst_data()->get('{type}')` |
| `Modules/{Module}/{Type}Service.php` | Service | Business logic ONLY — typed/composite/event/cached reads. No plain pass-throughs. |
| `Modules/{Module}/{Type}Router.php` | Router | Slug resolution / redirects for `/{slug}/...` (uses `parse_request`) |
| `Domain/{Type}Status.php` | Value object | Status enum; `tryFrom()` coercion lives here |
| `themes/{theme}/single-{type}.php` | Frontend template | Single-object render — resolves the repo via `ntdst_get()` |

Governing reference: **`ntdst-architecture/references/services.md`** (service lifecycle), **`ntdst-data/references/data-orm.md`** (Data API + repository contract). This doc does not restate those rules — it shows the shape they produce.

---

## 1. CPT registration — `{Type}CPT.php`

Static `register()`, called from the owning service's `init()`. The field schema here is **the single source of truth** for this type's meta (per `ARCHITECTURE-INVARIANTS.md` INV-3 — no central field registry).

```php
<?php
declare(strict_types=1);

namespace {Project}\Modules\{Module};

use {Project}\Admin\{Project}SettingsService;

final class {Type}CPT
{
    public const POST_TYPE = '{type}';            // referenced everywhere via the constant — never the raw string

    public static function register(): void
    {
        ntdst_data()->register(self::POST_TYPE, [
            'meta_prefix' => '_{prefix}_',         // THE meta prefix. Repositories read it via getMetaPrefix();
                                                   // nothing else hardcodes it. (drift cat 7)
            'label'  => 'Edities',
            'labels' => [ /* singular_name, add_new, edit_item, … */ ],
            'public'             => true,
            'publicly_queryable' => true,
            'has_archive'        => false,         // discovery handled by dedicated catalog pages
            'show_ui'            => true,
            'show_in_menu'       => '{project}-dashboard',
            'menu_icon'          => 'dashicons-calendar-alt',
            'supports'           => ['title'],
            'rewrite'            => [
                'slug'       => {Project}SettingsService::getEditionSlug(),  // slug is a setting, not a literal
                'with_front' => false,
            ],
            'fields'        => self::getFields(),
            'auto_metabox'  => false,              // custom admin UI owns the edit screen (see admin-settings golden path)
        ]);
    }

    private static function getFields(): array
    {
        // Field schema = single source of truth. Type drives Data API coercion + YOOtheme mapping.
        return [
            'course_id'  => ['type' => 'int',     'label' => 'Cursus', 'required' => true],
            'start_date' => ['type' => 'text',    'label' => 'Startdatum', 'required' => true],
            'capacity'   => ['type' => 'int',     'label' => 'Capaciteit', 'required' => true],
            'price'      => ['type' => 'float',   'label' => 'Prijs'],
            'status'     => ['type' => 'text',    'label' => 'Status'],
            'session_slots' => ['type' => 'json', 'label' => 'Sessie slots'],
            'requires_approval' => ['type' => 'boolean', 'label' => 'Goedkeuring vereist'],
            // … one entry per meta field; the `type` is what the Data API and YOOtheme read
        ];
    }
}
```

**Why a `json` and `boolean` type matter:** the Data API coerces on the way in/out by this declared type. Passing `'post_title'` as a field key here (or in `create()`) silently drops it — use the friendly vocabulary (`title`/`content`/`excerpt`). See `anti-patterns.md` → *Wrong Data API Vocabulary*.

---

## 2. Repository — `{Type}Repository.php`

`extends AbstractRepository`. This is the **single mediator** for `{type}` data (drift cat 1 + cat 8). `AbstractRepository` already gives you `find/create/update/delete/all/count/getField/findFields/getMetaPrefix` — only add a method when it expresses a *domain query*.

```php
<?php
declare(strict_types=1);

namespace {Project}\Modules\{Module};

use {Project}\Domain\OfferingStatus;
use {Project}\Infrastructure\AbstractRepository;

final class {Type}Repository extends AbstractRepository
{
    protected string $postType = {Type}CPT::POST_TYPE;   // binds the repo to the type

    /** Domain query — not a CRUD wrapper, so it earns its place. */
    public function findByCourse(int $courseId): array
    {
        return $this->model()
            ->where('course_id', $courseId)
            ->where('post_status', 'publish')
            ->orderBy('start_date', 'ASC')
            ->withMeta()
            ->get();
    }

    public function findActiveIdsByCourse(int $courseId): array
    {
        $rows = $this->model()
            ->where('course_id', $courseId)
            ->where('post_status', 'publish')
            ->whereIn('status', OfferingStatus::activeValues())
            ->get();

        return array_map(static fn(array $row): int => (int) ($row['id'] ?? $row['ID'] ?? 0), $rows);
    }

    /**
     * Batch-prefixed meta read. The meta arrives with raw prefixed keys, so we
     * read the prefix via getMetaPrefix() — NEVER hardcode '_{prefix}_'.
     * (This is the documented cat-1 / cat-7 exception for perf-critical batch paths.)
     */
    public function findCourseIdsForEditions(array $editionIds): array
    {
        if (empty($editionIds)) {
            return [];
        }
        $rows = $this->model()
            ->whereIn('ID', array_map('intval', $editionIds))
            ->where('post_status', 'publish')
            ->withMeta()
            ->get();

        $prefixedKey = $this->getMetaPrefix() . 'course_id';   // <-- the rule: prefix from the repo, not a literal
        $map = [];
        foreach ($rows as $row) {
            $editionId = (int) ($row['id'] ?? $row['ID'] ?? 0);
            $courseId  = (int) ($row['meta'][$prefixedKey] ?? 0);
            if ($editionId > 0 && $courseId > 0) {
                $map[$editionId] = $courseId;
            }
        }
        return $map;
    }

    public function updateStatus(int $editionId, OfferingStatus $status): void
    {
        $this->model()->updateMetaBatch($editionId, ['status' => $status->value]);
    }
}
```

**`get_posts()` inside a repository is fine** (Stride's real `findManyById()` uses it for a `post__in` batch) — the cat-8 rule bans raw post access *outside* repositories. Inside, the repo is the mediator, so it may use whatever WP primitive fits.

---

## 3. Service — `{Type}Service.php`

`extends AbstractService implements NTDST_Service_Meta` (the abstract supplies `metadata()` plumbing). The constructor injects the **repository** (not another service to reach a repo — drift cat 10). `init()` does all hook wiring. Every public method earns its place: typed coercion, composite decision, event firing, or cached read. **No method is `return $this->repository->X(...)` and nothing else** (drift cat 2).

```php
<?php
declare(strict_types=1);

namespace {Project}\Modules\{Module};

use {Project}\Contracts\EditionQueryInterface;
use {Project}\Domain\OfferingStatus;
use {Project}\Infrastructure\AbstractService;

class {Type}Service extends AbstractService implements EditionQueryInterface
{
    public function __construct(
        private readonly {Type}Repository $repository,         // inject the REPO, not a sibling service
        private readonly SessionRepository $sessions,
        private readonly \{Project}\Modules\Membership\MembershipService $membership,
    ) {
        parent::__construct();   // AbstractService calls init()
    }

    public static function metadata(): array
    {
        return ['name' => 'Edition Service', 'description' => 'Manages scheduled offerings', 'priority' => 10];
    }

    protected function init(): void
    {
        {Type}CPT::register();                                  // CPT registration is owned by the service
        SessionCPT::register();

        // Hook wiring lives here — this is what makes the class a service (anti-patterns.md → "is it a service?")
        add_action('{project}/registration/created',   [$this, 'onRegistrationCreated']);
        add_action('{project}/registration/cancelled', [$this, 'onRegistrationCancelled']);
        add_action('before_delete_post',                [$this, 'onEditionDeleted']);

        ntdst_get({Type}Router::class)->register();             // router wired here too
    }

    // Typed/coerced read — enum coercion adds value, so it's NOT a pass-through.
    public function getStatus(int $editionId): OfferingStatus
    {
        $status = $this->repository->getField($editionId, 'status', 'open');
        return OfferingStatus::tryFrom($status) ?? OfferingStatus::Open;
    }

    public function getCourseId(int $editionId): ?int
    {
        $courseId = $this->repository->getField($editionId, 'course_id');
        return $courseId ? (int) $courseId : null;   // null-coercion = not a pass-through
    }

    // Composite business decision — multi-source, real logic.
    public function canEnroll(int $editionId): bool
    {
        return $this->getEffectiveStatus($editionId)->allowsEnrollment()
            && $this->hasAvailableSpots($editionId)
            && !$this->isPast($editionId);
    }

    // Cached read with its own invalidation — the cache logic is the value-add.
    public function getRegisteredCount(int $editionId): int
    {
        $cacheKey = '{project}_edition_reg_count_' . $editionId;
        $cached = get_transient($cacheKey);
        if ($cached !== false) {
            return (int) $cached;
        }
        // High-volume CUSTOM TABLE (not a CPT) → $wpdb->prepare is correct here,
        // and it's NOT a repository-bypass: custom tables don't go through the CPT repo.
        global $wpdb;
        $table = $wpdb->prefix . 'vad_registrations';
        $count = (int) $wpdb->get_var($wpdb->prepare(
            "SELECT COUNT(*) FROM {$table} WHERE edition_id = %d AND status IN ('confirmed','completed','pending')",
            $editionId
        ));
        set_transient($cacheKey, $count, 60);
        return $count;
    }
}
```

---

## 4. Router — `{Type}Router.php`

A plain class (not a service) wired by the service. Uses `parse_request` — **the documented exception to drift cat 9**: it needs pre-query timing to redirect before WP resolves the query, which is too early for `ntdst_router()->template()`.

```php
<?php
declare(strict_types=1);

namespace {Project}\Modules\{Module};

final class {Type}Router
{
    public function __construct(private readonly {Type}Repository $editions) {}

    public function register(): void
    {
        add_action('parse_request', [$this, 'maybeRedirectCourseSlug']);
    }

    public function maybeRedirectCourseSlug(\WP $wp): void
    {
        $path = trim((string) ($wp->request ?? ''), '/');
        if ($path === '' || !str_starts_with($path, 'edities/')) {
            return;
        }
        $slug = trim(substr($path, strlen('edities/')), '/');
        if ($slug === '' || str_contains($slug, '/')) {
            return; // sub-paths owned by other routers
        }
        if (get_page_by_path($slug, OBJECT, '{type}')) {
            return; // real edition slug → native CPT routing handles it
        }
        // … domain redirect logic via $this->editions->findActiveIdsByCourse(...)
        // wp_safe_redirect(...) + exit
    }
}
```

> **If your feature has NO pre-query redirect logic** (most CPTs), skip the router and register a template through the framework instead:
> `ntdst_router()->single('{type}', fn($post) => ntdst_response()->with('project', $post)->template('{type}/single'));`
> See `anti-patterns.md` → *Manual template_include* and `references/router.md`.

---

## 5. Frontend template — `single-{type}.php`

⚠️ **Stride's real `single-vad_edition.php` DRIFTS here — do not copy it.** It does `$editionModel = ntdst_data()->get('vad_edition')` directly in the theme (its own comment even says *"these could be added to EditionService if needed"*). That is drift cat 1: the theme reaches past the repository.

**The correct pattern** — resolve the repository via `ntdst_get()` (themes can't use constructor DI) and read through it:

```php
<?php
/** single-{type}.php — theme presentation only, no business logic. */
defined('ABSPATH') || exit;

$edition_id = get_the_ID();

// CORRECT: resolve the repo + service via the container, read through them.
$editions = ntdst_get(\{Project}\Modules\{Module}\{Type}Repository::class);
$service  = ntdst_get(\{Project}\Modules\{Module}\{Type}Service::class);

$start_date = $editions->getField($edition_id, 'start_date', '');   // NOT ntdst_data()->get(...)->getMeta(...)
$venue      = $editions->getField($edition_id, 'venue', '');
$status     = $service->getEffectiveStatus($edition_id);             // typed read for display

// Output: escape everything (drift / wp-security pillar 4).
echo esc_html($start_date);
echo esc_html($venue);
```

`getField()` is on `AbstractRepository`, so no new repo method is needed for single-record reads.

---

## How to adapt — what changes per project, what never does

**Changes per project (the 6–8 decisions):**
1. **Names** — `{Project}` namespace, `{Module}` folder, `{Type}` class prefix.
2. **Post type slug** — `{type}` (the `POST_TYPE` constant).
3. **Meta prefix** — `_{prefix}_` (declared once in the CPT, read via `getMetaPrefix()`).
4. **Field schema** — the `getFields()` array; each field's `type` drives coercion.
5. **Domain queries** — which `findByX()` methods the repository needs (delete the ones you don't).
6. **Status enum** — the `Domain/{Type}Status.php` cases + which are "active".
7. **Service hooks** — which `add_action()`/events the service fires in `init()`.
8. **Routing** — router with `parse_request` *only* if you need pre-query redirects; otherwise `ntdst_router()->single()`.

**Never changes (the framework spine):**
- Data access goes through the repository; `ntdst_data()->get()` appears **only** in `*Repository.php`.
- The service injects the repository, never a sibling service to reach a repo.
- No pure pass-through service methods.
- Meta prefix read via `getMetaPrefix()`, never hardcoded.
- Friendly Data API vocabulary (`title`/`content`/`excerpt`), never raw column names.
- Theme resolves the repo via `ntdst_get()`; never `ntdst_data()` in a template.
- Output escaped at the template boundary.

---

## Cross-references

- Governing references: `ntdst-architecture/references/services.md`, `.../router.md`, `ntdst-data/references/data-orm.md`.
- Anti-patterns this slice satisfies: `anti-patterns.md` → *Direct Meta Access in Services*, *Pure Pass-Through Method*, *CPT Data Access Outside the Repository*, *Wrong Data API Vocabulary*, *Manual template_include*.
- Drift categories satisfied (per `ntdst-drift-reviewer`): **1** (ntdst_data outside repo), **2** (pass-through), **6** (Data API vocab), **7** (hardcoded prefix), **8** (raw post access), **9** (template_include), **10** (over-injected service).
- The admin edit/list screen for this CPT is its own slice — see `golden-paths/admin-settings-page.md` for the framework-clean admin pattern (Stride's `Edition/Admin/` subfolder is drifted; do not copy it).
