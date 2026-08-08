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

## Prefix awareness is a documented trade-off, not drift

**Problem (Stride, 2026-05-19):** Formatters and sort callbacks hardcoded `_ntdst_*` meta key names. A future config change would silently break them.

**Context:** Normally callers never see the prefix — `getField('date')` uses unprefixed names. But there's one case where you DO see it: batch query results from `getPostsFast()` / `->withMeta()` return meta nested under a `meta` key, with raw prefixed keys. That's the framework's design — single-query meta load. The alternative is N+1.

**Rule:** When you have to read from a batch-loaded `meta` envelope:

```php
// ❌ Don't hardcode the prefix string
$date = $row['meta']['_ntdst_date'] ?? '';

// ✅ Pull the prefix from the model so a config change can't break this
$prefix = $this->repository->getMetaPrefix();
$date   = $row['meta'][$prefix . 'date'] ?? '';
```

**When prefix awareness is OK to keep:**
- Path is performance-critical (catalog pages, completion math, batch exports)
- Alternative is N+1 — per-row `getField()` would multiply queries
- Magic string is replaced by `getMetaPrefix()` — no hardcoded `_ntdst_`

**When it IS drift** (refactor it away):
- Single-record paths — use `getField()` / `findFields()`
- Sites that touch only 1-2 fields — `getField` is fine, no batch needed
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
obvious cause as the failure mode). Stamp the grant with a version option so it doesn't write on
every request.

**Related:** `edit_post` is a *meta* capability. A CPT gets `map_meta_cap` only via WordPress's
back-compat rule for `capability_type` in `('post','page')`. Adding an explicit `capabilities` array
turns that off, and an `edit_post` gate then denies everyone.

---

## Note on this skill's structure (2026-08-08)

`references/` and `templates/` were **86% API inventory** (2,451 of 2,837 lines) with three files
carrying false claims, and the two API references had drifted into contradicting each other on
whether an empty result is a success and whether a user-search action was public. All of it was
collapsed into `SKILL.md` (decisions + traps) and `golden-paths/model-and-api-action.md` (a worked
slice, with a `Verified against source:` date). Retired: `references/{api,data-orm,metabox}.md` and
both `templates/*.php.md`. Read the golden path for how, `SKILL.md` for why, and **source** for any
signature.
