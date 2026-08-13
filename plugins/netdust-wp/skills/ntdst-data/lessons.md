# NTDST Data Layer — Lessons

Data-layer incidents that became framework rules. For canonical patterns, read `SKILL.md` (judgment) and `golden-paths/model-and-api-action.md` (how). This file is the journal. Anything a grep can decide is enforced by `bin/drift-check.py`, not argued here.

---

## Friendly key vocabulary: `title`, NOT `post_title`

**Problem (Stride, 2026-05-19):** Calling `$repository->create(['post_title' => 'X', 'date' => '2026-06-01'])`. The framework dropped `post_title` from post-table extraction AND silently re-prefixed it into meta as `_ntdst_post_title`. 60 session posts ended up with that orphan meta. The bug was invisible because the post displayed correctly via a different read path.

**Rule:** The Data API has its own friendly vocabulary. Pass `title`/`content`/`excerpt`, not the WordPress column names.

| Pass this | The framework writes |
|---|---|
| `title` | `wp_posts.post_title` |
| `content` | `wp_posts.post_content` |
| `excerpt` | `wp_posts.post_excerpt` |
| `post_status` | `wp_posts.post_status` (already prefixed) |
| `post_author`, `post_parent`, `post_date`, `post_name`, `menu_order`, etc. | pass through unchanged |

Full canonical list: `NTDST_Data_Model::WP_COLUMNS` in `api/Data.php`. 16 columns total.

**Safety net:** since the WP_COLUMNS refactor (2026-05-19), `warnUnregisteredKeys()` logs unknown keys via `ntdst_log('data')->warning()` and drops them. Watch `logs/data-YYYY-MM-DD.log` after refactors. Zero warnings = correct vocabulary.

**Fingerprint of this bug:** if a DB meta dump shows `_ntdst_post_title` (or any `_ntdst_post_*`), some writer is using the wrong vocabulary somewhere.

---

## Repository is the single mediator for CPT data access

**Problem (Stride, 2026-05-19):** A grep found `ntdst_data()->get('vad_edition')` called directly in 5+ places, alongside 6+ places using `EditionRepository`. Two paths for the same operation. Drift.

**Rule:** No file outside `Modules/{Domain}/{Domain}Repository.php` calls `ntdst_data()->get(...)` directly. CRUD and queries go through the corresponding repository.

**What `AbstractRepository` already provides** (don't reach for `ntdst_data()` if any of these fit):

| Method | Returns | Description |
|---|---|---|
| `find(int $id)` | `WP_Post\|WP_Error` | full record with `->fields` and `->meta` |
| `create(array $data)` | `WP_Post\|WP_Error` | sanitized + validated via schema |
| `update(int $id, array $data)` | `WP_Post\|WP_Error` | partial update, rolls back on meta-write failure |
| `delete(int $id, bool $force=false)` | `bool\|WP_Error` | trash or force-delete |
| `all(array $filters=[], int $limit=-1)` | `array` | list with simple where filters |
| `count(array $filters=[])` | `int` | matching count |
| `getField(int $id, string $field, mixed $default=null)` | `mixed` | single registered field, typed |
| `findFields(int $id)` | `array<string,mixed>` | all registered fields, typed |
| `getMetaPrefix()` | `string` | model's prefix (e.g. `_ntdst_`) |

**Domain repos add only domain-shaped queries** — `findByCourse`, `findUpcoming`, `findActiveIdsByCourse`, `updateStatus(StatusEnum)`. They do NOT re-export the generic CRUD with different names.

---

## Pass-through methods on services are drift

**Problem (Stride, 2026-05-19):** `EditionService` exposed `getEdition()`, `getEditionsForCourse()`, `getUpcomingEditions()` — each was literally `return $this->repository->X(...)`. 21 call sites had to choose between "go via service" or "go via repo." Some did one, some did the other. Drift compounding.

**Rule:** A service method that's a one-liner forward to a repository does not add a layer. It adds a second way to do the same thing. Delete the wrapper. Callers go to the repository directly.

**The test:** open the method body. If it's `return $this->repository->X(...)` and nothing else — it shouldn't exist.

**What's NOT a pass-through** (keep):
- Typed/coerced reads: `getStatus(): OfferingStatus` (enum coercion), `getCourseId(): ?int` (0 → null)
- Composite reads: `getPrice($id, $userId)` (member-aware), `isOnline($id)` (cross-domain)
- Event firers: `createX()` that wraps `$repo->create()` + `do_action(...)`
- Business decisions: `canEnroll`, `hasAvailableSpots`

---

## Batch-read prefix awareness — RESOLVED 2026-08-07, the exception is gone

> **This lesson has INVERTED. Read the new rule; the old one now breaks silently.**

**What it used to say (correct until 2026-08-07):** batch query results from
`getPostsFast()` / `->withMeta()` returned meta under a `meta` key with **raw
prefixed** keys, so callers had to compensate with
`$row['meta'][$this->repository->getMetaPrefix() . 'date']`. It was framed as a
documented performance trade-off — the alternative was N+1.

**What is true now.** `get()` / `all()` / `paginate()` project each row's `meta`
through the model's declared schema, so it carries **unprefixed, type-cast,
declared fields only** — the same set `find()->fields` reports. The prefix is a
storage detail again and never reaches a caller.

```php
// ❌ WRONG NOW — returns null. There is no prefixed key in the projected bag.
$prefix = $this->repository->getMetaPrefix();
$date   = $row['meta'][$prefix . 'date'] ?? '';

// ✅ Read the declared field name, exactly as you would off find()->fields
$date = $row['meta']['date'] ?? '';
```

**Why it changed, because the reason is the lesson.** The "documented trade-off"
was a missing API wearing a justification. The query builder had NO projected
form at all — only `find()` did — so a list handler could not get a safe shape
from `get()`. That is not a discipline problem, and the codebase proved it: the
one correct list handler paid an N+1 to re-fetch every row through `find()`,
while four others returned the raw rows and shipped **every undeclared meta key
to anonymous callers**. The obvious path was the unsafe one and the safe path
needed a workaround. Both are now the same path.

**Migration.** Any surviving `$row['meta'][$prefix . 'x']` read is a silent
null — it will not throw, and a filter or sort built on it fails OPEN (two such
sites were found: a cancelled-gig filter and an exclude-from-catalogue flag).
Grep `\['meta'\]\[` and drop the prefix. Projects still on an older `ntdst-core`
copy keep the old behaviour until ported — check that project's `api/Data.php`.

**Still true:** never hardcode `_ntdst_` as a literal anywhere. If you genuinely
need the raw bag, `NTDST_Data_Manager::getPostMeta($id)` is the explicit door,
and `find()->meta` still carries every row unfiltered — which is exactly why a
public handler must project before returning.
- ANY hardcoded `_ntdst_` string literal — replace with `getMetaPrefix()` even if you keep the prefix-aware shape

---

## WP_Error must be checked, not swallowed

**Problem (Stride, 2026-05-19):** `EditionCompletion::processCompletion()` returns `true|WP_Error`. Two callers (`CompletionTaskHandler:235`, `EditionCompletion::onAttendanceMarked`) ignored the return value. When errors fired — orphan registrations, missing courses — they vanished. No log, no trace.

**Rule:** Every `WP_Error`-returning method call gets `is_wp_error()` checked. If swallowed, log via `ntdst_log('channel')->error(...)` with structured context.

**Pattern:**

```php
$result = $service->doSomething();
if (is_wp_error($result)) {
    ntdst_log('enrollment')->error('Operation failed', [
        'context_id' => $id,
        'error'      => $result->get_error_code() . ': ' . $result->get_error_message(),
    ]);
    return; // or return $result to propagate
}
```

**When to skip logging:** when the `WP_Error` is a normal flow state (e.g. `not_complete` fires on every attendance mark for not-yet-finished users — that's not an error worth logging every time). Log at call sites where the error means a real anomaly. Don't log inside business-logic classes that return `WP_Error` for routine outcomes.

---

## `required` was enforced only on CREATE — and validation runs BEFORE sanitization

**Problem (daan, 2026-08-09):** `'required' => true` on a field declaration reads like an invariant. It was not one. `validateData()` gated the check behind `!$isUpdate`, with a comment rationalising it — *"For updates, missing fields keep existing values."* That reasoning is correct for an **omitted** field and wrong for an **explicitly empty** one, and the code could not tell them apart. So `$model->update($id, ['venue_city' => ''])` was accepted and blanked a field the schema declared un-emptyable. On every NTDST site, on every CPT, silently. Compounding it: `MetaboxGenerator` read the `required` key **zero** times — no HTML attribute, no `aria-required`, no visual marker — so an editor got no indication either.

**Rule (fixed in ntdst-core 2026-08-09; older copies still carry the hole):** a required field that is **omitted** from an update keeps its existing value; a required field **supplied** as `''`/`null`/`[]` is refused, on create and update alike. The discriminator is `array_key_exists`, not `isset` — `isset` reports false for an explicit `null` and would misclassify it as omitted.

**Do NOT "simplify" the guard by deleting `!$isUpdate`.** That enforces `required` on every partial update and breaks every code path that writes one field to a post that has required fields — far more damage than the bug. The regression lock for this is `DataModelRequiredOnUpdateTest::testUpdateThatOmitsARequiredFieldStillSucceedsAndPreservesIt`.

**`required` is still not a layer-wide invariant.** `updateMeta()` and `updateMetaBatch()` write meta with type sanitization and **no** `validateData()` call at all, so `$model->updateMeta($id, 'venue_city', '')` still blanks a required field. Do not read "required is enforced on update" as a guarantee the layer makes everywhere.

**Second, separate trap in the same method: `validateData()` runs BEFORE `sanitizeData()`.** So a required field whose raw value is non-empty but *sanitizes away* still lands empty — an unparseable `date` (`sanitizeDate` → `''`), invalid `json` (`sanitizeJson` → `[]`), a `relation` given `['']` (`array_filter` → `[]`). The metabox path is protected, because its own `sanitize_field` collapses these before `update()` sees them; a programmatic caller or crafted POST is not.

**What is NOT empty, and this matters:** `false`, `0`, `0.0` and `'0'` all pass. A required boolean may be `false` and a required integer may be `0`. The metabox posts a hidden `value="0"` ahead of each checkbox, which sanitizes to PHP `false` rather than `''`, so an unticked required checkbox validates correctly.

---

## `'default'` field keys are INERT, and `select` does not enforce its `options`

**Problem (daan record-shop, 2026-08-10):** `record_product` declared `'available' => ['type' => 'boolean', 'default' => true]` and the task contract said "defaults to true". The rule extraction reads only `required`/`min`/`max`/`validate`; `MetaboxGenerator` has no default handling either. A fresh product's checkbox rendered unticked, an ORM `create()` omitting the key stored nothing — proven with a failing probe while the key was still present. Three musician services (`ProjectService`, `DiscographyService`, `TourService`) still carry the same inert keys, drifting as "behaviour" that never was.

**Rule:** never write a `'default'` key in a field config — state omission semantics in the field description and make writers explicit. In the review direction: a `'default'` key in a diff is dead config, flag it.

**Same session, same table:** `select` sanitizes (`sanitize_text_field`) but does **not** validate against its `options`. A closed set (`new|handled`) needs an explicit `validate` closure, on create AND update, or any string is storable.

**Eval:** `netdust-wp/evals/behavioral-lessons.json` → `data-default-key`.

---

## `find($id, true)` no longer means "skip the cache" — it throws

**Problem (daan, 2026-08-08):** The record lookup's second parameter used to be a `$skipCache`
boolean. The cache it served was deleted, and a `$status` parameter took that position. A leftover
`find($id, true)` would then have quietly meant "accept the post status `true`" — matching nothing,
and denying every row.

**Rule:** the framework now **throws** on a boolean there rather than failing invisibly.
*Fail-closed but invisible is the worst shape available* — worse than failing open, because nobody
goes looking. When you remove a parameter, do not let the next one silently inherit its position:
either keep the slot reserved or make the old call shape raise.

**Fork warning:** most other `ntdst-core` copies still have the cache and still honour the boolean.
The same line of code means two different things depending on the site.

---

## Registration must fail loudly, and privately by default

**Problem (daan, 2026-08-08):** Two defects in one call. Model registration merged the caller's
config *over* `public => true, has_archive => true`, so any model registered without explicit
visibility flags was published, archived and queryable — which is why every non-public CPT carried
six hand-written denials, and why forgetting one was a disclosure. Separately, a `WP_Error` from
`register_post_type()` was discarded and the model built anyway, leaving a half-registered phantom:
`isRegistered()` true while `post_type_exists()` was false.

**Rule:** **opt in to public, never out of it.** And never swallow a registration failure — a thing
that reports healthy while being broken costs more than a thing that refuses to start.

---

## A custom `capability_type` grants nothing — WordPress only *maps*, it never *invents*

**Problem (daan, 2026-08-08):** A CPT was given its own `capability_type` to narrow access. Probed
live afterwards: **administrator `can('edit_access_grants')` = DENY.** `map_meta_cap` maps *meta*
capabilities onto primitives; it never creates primitive ones, so the new capability names were held
by no role at all.

**Rule:** giving a type its own `capability_type` does not narrow access — it denies everyone until
something calls `add_cap()`. Grant the caps explicitly, **reading the capability list off the
registered post-type object** rather than hardcoding it (WordPress has grown that set across
releases, and a hardcoded copy silently stops covering one — with a denied administrator and no
obvious cause as the failure mode). Grant on `init`, not `after_setup_theme`: services boot on
`after_setup_theme`, so a grant at that priority runs before the type exists and silently no-ops.
Stamp the grant with a version option so it doesn't write on every request.

**Related:** `edit_post` is a *meta* capability. A CPT gets `map_meta_cap` only via WordPress's
back-compat rule for `capability_type` in `('post','page')`. Adding an explicit `capabilities` array
turns that off, and an `edit_post` gate then denies everyone.

---

## Registering the action is not the same as declaring what may reach it

**Problem (daan, 2026-08-08):** The `ntdst/api_data/{action}` hook is an ordinary WordPress filter,
so `add_filter()` registers a working action — and forfeits, silently, the declared capability floor,
the public-allowlist entry, and the dispatch-time gate. The whole burden lands on the handler, and
handlers get edited.

**Rule:** register through `ntdst_api_action($action, $handler, $opts)`. The floor it declares bites
at **dispatch, ahead of the handler**, so it protects a handler that later forgets to check — defense
in depth *alongside* the per-row check, never instead of it. Prefer the type-derived `cap_type` floor
over a literal capability: it resolves the post type's own `edit_others_posts` and is **fail-closed**,
where the literal form kept the retired wrapper's fail-**open**-on-empty semantics. The raw-filter
bypass is now gated as `raw-api-filter`.

---

## Note on this skill's structure (2026-08-08)

`references/` and `templates/` were **86% API inventory** with three files carrying false claims, and
the two API references had drifted into contradicting each other on whether an empty result is a
success and whether a user-search action was public. All of it was collapsed into `SKILL.md`
(decisions + traps) and `golden-paths/model-and-api-action.md` (a worked slice, with a
`Verified against source:` date). Retired: `references/{api,data-orm,metabox}.md` and both
`templates/*.php.md`. Read the golden path for how, `SKILL.md` for why, and **source** for any
signature.
