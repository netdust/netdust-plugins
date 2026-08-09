# NTDST Data Layer — Lessons

Data-layer incidents that became framework rules. For canonical patterns, read `references/`. This file is the journal.

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
