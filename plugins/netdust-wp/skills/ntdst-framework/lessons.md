# NTDST framework — lessons

Project incidents that became framework rules. The journal: it explains *why*
`SKILL.md` and `references/traps.md` say what they say. Merged 2026-08-21 when
`ntdst-framework` and `ntdst-framework` collapsed into one skill.

---

## From ntdst-architecture


---

## Match the framework reference, not the closest sibling

**Problem (Stride, 2026-05-19):** A code review found two dialects coexisting in the same module:
- 8 files used `ntdst/api_data/*` correctly
- 5 admin controllers used raw `add_action('wp_ajax_*')`
- Newer code copied the wrong (sibling) pattern because that's what was nearby

**Rule:** When writing a new class, identify which framework layer it touches (endpoints, response, data, logger, router, mailer) and read the corresponding `references/*.md`. Do NOT pattern-match against the closest existing file in the directory — that file may be drifted.

**How to apply:**
1. Before writing, ask: which references apply? (api-endpoints, response, data-layer, router, logger, mailer)
2. Read the actual reference. Don't skim.
3. If a neighbouring file uses a different pattern, the neighbour is suspect. Build to the reference, not the neighbour.
4. After writing, scan for: raw `add_action('wp_ajax_*')`, `ob_start + include`, `get_post_meta`, swallowed `WP_Error`. If any present — refactor before commit.

---

## Pure pass-through methods are drift, not abstraction

**Problem (Stride, 2026-05-19):** `EditionService` had three methods that were literally `return $this->repository->X(...)` — no logic, no transformation. 21 call sites split between `$service->getEdition()` and `$repository->find()`. Same operation, two paths. Drift.

**Rule:** A service method that's a one-liner forward to a repository (or another service) does not add a layer. It adds a second equally-correct way to do the same thing — and the codebase will drift between the two.

**The test:** Open the method body. If it's `return $this->X->Y(...)` and nothing else, the method shouldn't exist. Callers go to `$this->X` directly.

**What's NOT a pass-through** (keep these):
- Typed/coerced reads: `getStatus(): OfferingStatus` (enum coercion from string)
- Composite reads: `getPrice($id, $userId)` (member-aware), `isOnline($id)` (cross-domain lookup)
- Business decisions: `canEnroll`, `hasAvailableSpots`, `isEnrollmentOpen`
- Event firers: `createX()` that wraps repo + `do_action('domain/x/created', ...)`
- Cached reads with service-specific invalidation

**Naming alone is not a justification.** "`getEdition` reads nicer than `find`" doesn't save the wrapper — the verb just lives on the repo method (`find`) under a different name.

**Forward-compat is not a justification.** "We might add logic later" → add it WHEN you need the logic, not in anticipation. Until then, the wrapper is pure cost.

---

## Right tool per operation, not blanket adoption of one helper

**Problem (Stride, 2026-05-19):** Asked to "use `ntdst_response()` here" inside a `template_include` filter callback. But `ntdst_response()`'s public API is `render()` (output+exit), `html()` (return string), `json()`, etc. — none return a resolved file path that `template_include` can use. Forcing it would have been worse than the raw filter.

**Rule:** When a user (or a memory) says "use `ntdst_X` here", verify the helper actually fits the operation BEFORE refactoring. Don't blindly substitute. If the named helper doesn't fit, identify the framework helper that does (the underlying intent — "align with framework" — is still right).

**Tool-fit cheat sheet:**

| Operation | Right tool | NOT |
|---|---|---|
| Render template + output | `ntdst_response()->render(...)` | `ob_start + include` |
| Render template → string | `ntdst_response()->html(...)` | `ob_start + include` |
| Resolve template name → file path for WP | `ntdst_pages()->template('single', $cb, $post_type)` | Raw `add_filter('template_include', ...)` |
| URL pattern → callback | `ntdst_pages()->path('pattern/:param', $cb)` | Raw `add_action('parse_request', ...)` |
| Pre-query interception (rewrite query vars BEFORE WP runs the query) | Raw `add_action('parse_request', ...)` | `ntdst_pages()` (fires on `template_include`, too late) |
| AJAX/REST endpoint | `add_filter('ntdst/api_data/{action}', ...)` | `add_action('wp_ajax_*', ...)` |
| Send email | `ntdst_mail()->to()->template()->send()` | `wp_mail()` |
| Log | `ntdst_log('channel')->level(...)` | `error_log()`, swallowed `WP_Error` |
| Read/write CPT | per-domain repository | `ntdst_data()` direct, raw `wp_insert_post`/`get_post_meta` |

If NO framework helper fits, explicitly defend the raw-WP idiom. Not every operation has a wrapper, and not every wrapper should exist.

---

## All CPT data access goes through the per-domain repository

**Problem (Stride, 2026-05-19):** A grep found `ntdst_data()->get('vad_edition')` called directly in 5+ places, while `EditionRepository` was used in 6+ other places. Two patterns for the same operation = drift.

**Rule:** No file outside `Modules/{Domain}/{Domain}Repository.php` should call `ntdst_data()->get(...)` directly. CRUD and queries go through the corresponding repository. The repository is the single mediator per CPT.

**Why this matters:**
- Centralizes caching, validation, audit hooks per domain
- Trivial mocks in tests (mock the repo, not `ntdst_data()`)
- Code-review handle: "does this need a repo method?"
- Domain-typed returns possible later (value objects vs raw arrays)

**`AbstractRepository` provides for free** (don't reach for `ntdst_data()` if any of these fit):
`find`, `create`, `update`, `delete`, `all`, `count`, `getField`, `findFields`, `getMetaPrefix`.

**Domain repos add only their business-logic queries** (`findUpcoming`, `findByCourse`, `findActiveIdsByCourse`, `updateStatus(StatusEnum)`).

**Prefix-awareness exception — REMOVED 2026-08-07.** Batch-loaded meta (`->withMeta()` envelope) used to arrive with raw prefixed keys (`_ntdst_*`), and callers compensated with `getMetaPrefix()`. `get()` / `all()` / `paginate()` now project each row's `meta` through the declared schema, so it carries **unprefixed, type-cast, declared fields only** — the same set `find()->fields` reports. Read `$row['meta']['date']`, not `$row['meta'][$prefix . 'date']`; the prefixed form now returns null SILENTLY, and a filter built on it fails open. Never hardcode `_ntdst_` either way. Projects on an older ntdst-core copy keep the old behaviour until ported — check that project's `api/Data.php`. Full story: `ntdst-framework/lessons.md`.

---

## Data API vocabulary: `title`, not `post_title`

**Problem (Stride, 2026-05-19):** `SessionRepository::create()` passed `$data['post_title']` to the Data API. The framework's `extractPostData()` accepted only `title`/`content`/`excerpt`/`post_status` at the time — `post_title` was silently dropped from post-table extraction AND silently re-prefixed into meta as `_ntdst_post_title`. 60 session posts ended up with that orphan meta key. The bug was invisible because the sessions still displayed correctly via a different read path.

**Rule:** The Data API has its own friendly key vocabulary. Pass friendly keys, not raw `wp_posts` column names.

| Pass this | NOT this |
|---|---|
| `title` | ~~`post_title`~~ |
| `content` | ~~`post_content`~~ |
| `excerpt` | ~~`post_excerpt`~~ |

The full canonical list is `NTDST_Data_Model::WP_COLUMNS` in `api/Data.php` — 16 columns total. See `references/data-layer.md`.

**Safety net (since 2026-05-19):** `NTDST_Data_Model::warnUnregisteredKeys()` logs unknown keys via `ntdst_log('data')->warning()` and drops them. Watch `logs/data-YYYY-MM-DD.log` after refactors. Zero warnings = correct vocabulary.

**Fingerprint of this bug:** if you see `_ntdst_post_*` keys in DB meta (post_title/post_content/post_excerpt), some writer is passing the wrong vocabulary somewhere.

---

## State-machine shakeout — unit tests pass ≠ system works

**Problem (Stride, 2026-05-18):** Registration lifecycle had 867 passing unit tests but a full end-to-end shakeout found 15 wiring bugs. Unit tests verify methods in isolation; they don't verify that the right listeners are registered to the right events with the right side effects.

**Rule:** For any system with significant state (registrations, attendance, orders, anything with transitions), do a shakeout pass that walks the FULL state machine before declaring the feature done.

**Method:**
1. List every state.
2. List every transition (who fires it, under what condition).
3. List every listener on each transition (and what side effects each listener has).
4. Write a scenario per transition that drives the system through it.
5. Assert every side effect (DB write, hook fire, notification sent, cache invalidated, log entry).

**Test files become the documentation of the state machine.** In Stride, `tests/manual/shake-*.php` are the reusable shakeout scripts.

**When to use:** Before launch, after major refactors of a stateful system, before merging code that adds or removes listeners.

---

For project-specific incidents (e.g. "this LearnDash integration quirk", "this Stride business rule"), see the originating project's `memory/` directory — not this file.

---

## Rate-limit budget arithmetic and refusal shapes on the api_data wire

**Problem (daan record-shop, 2026-08-10):** the first anonymous public WRITE action shipped with a 3/60s limit and the wire gate found only 2 requests landing per window, with denials surfacing as 401 `rest_forbidden`. Three framework truths were paid for over the wire: (1) WP core invokes `permission_callback` twice per request (dispatch + `rest_send_allow_header`) — the limiter double-counted until a per-request-object memo landed, and the fleet default 30/60 had effectively been 15 forever; (2) `get_nonce` rate-checks the TARGET action, so a first-visit flow costs 2 budget units; (3) `getClientIp()` honoured the attacker-authored leftmost `X-Forwarded-For` — bucket identity must be the rightmost untrusted hop.

**Rules:** size per-action limits knowing mint+call = 2 units on first visit; never add side effects to a REST permission callback expecting single invocation; refuse from handlers with `WP_Error` (+`['status']`) only — an `apiError()` array rides out as HTTP 200 `success:true`; 429/`rate_limited` vs bare-false/401 is a deliberate asymmetry, keep it. Full mechanics: `references/api-endpoints.md` §Per-action rate limits.

**Eval:** `netdust-wp/evals/behavioral-lessons.json` → `api-rate-budget`.

--## From ntdst-dataork

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

## A parked core design beats a site hand-roll — `rest_query`

**Problem (ntdst-core, 2026-08-23):** Stefan drew the roadmap `Data_Model → Queryable
Collection → Response → Export` and asked whether it changes `Data.php` again. The
answer was: WordPress's collection (`/wp/v2/<type>` + `rest_{type}_query`) already is
the queryable collection, and the one legitimate addition — a declared field that
becomes a collection filter — has no consumer yet. He parked it: "document it well
so agents see it when a consumer needs it."

**Rule:** When a site needs to filter a post type by a declared meta field over
WordPress's collection endpoint, that site is the named consumer
(`philosophy.md` §6.1) for `ntdst-core/docs/parked/rest-query.md`. Do not hand-roll
the two WordPress filters in the site and do not build a "queryable collection"
layer in core (deleted in v4, ruled out by core-shape D1).

**How to apply:**
1. Recognise the trigger: `?field=value` filtering on `/wp/v2/<type>`, or a custom
   list route whose only job is one meta-key filter.
2. Read the parked doc — design, rules (needs `show_in_rest`; scalars only; `=`),
   threat rows and the tests the task owes are already written.
3. Open the one-task spec in `ntdst-core` (`specs/rest-query/`), citing the site as
   the consumer. The site's change is one key on the field description.


## v5 re-anchor (2026-08-23)

`SKILL.md` and `references/traps.md` described a package that no longer exists. Three
breaking specs — `core-shape`, `field-types` and `core-trim` — merged into ntdst-core
5.0.0, and the skill still taught v3/v4: the command dispatcher, `api_data`, the
`{success,data}` envelope, auto-discovery, the `_enabled` switch, `Theme::style()` and
21 field-type names. A consumer agent reading it would have written code that fatals at
`init`. The rewrite re-anchors every claim on the source (README `### 5.0.0`,
`ARCHITECTURE-INVARIANTS.md` INV-1…INV-10, the three specs, and the code where a spec is
silent), reorganises the file around the three doors a consumer actually picks between,
and re-pins every trap to the core unit test or invariant that would catch its
regression. Four doors became three; the fourth was never a door, it was a second HTTP
surface. Where README's own rows are not written yet (Response, Theme, the exposure
helpers), the specs are cited as the authority and the header says `pre-tag`.

- **The command dispatcher** — `ntdst_actions()`, `ntdst/api_data/{action}`, the minted
  nonce route and the JS client are gone. There is ONE HTTP surface, `ntdst_rest()`, and
  a command is a `->post()` route reached with `wp.apiFetch` (INV-2, INV-4).
- **`'permission' => 'public'`** — the STRING is refused and the route does not register.
  `->public()` on the verb is the one door to anonymous, because a value reaches config,
  a constant and a merge, and a chained call does not (INV-3).
- **Internal by default** — a route that says nothing is `is_user_logged_in`, and a write
  verb carrying only a posture does not register at all. v4 required a callable permission.
- **The surface registry** — `surface()`, `publicSurface()`, `opaqueSurface()`,
  `forgetSurface()`, `public_fields`, `publicRow`. WordPress keeps the register; ask
  `rest_get_server()->get_routes($ns)` (INV-5).
- **Auto-discovery** — `auto_discover`, `discovery_paths` and the source-parsing loader
  are gone. You load, core resolves; a writable directory on that list was code execution
  (INV-10).
- **The `_enabled` filter and its option** — retired, and they FAILED OPEN. A service kept
  off through them BOOTS after the upgrade. Two switches now: `metadata()['enabled']` or a
  conditional entry. The config filter is `ntdst/service/{slug}/config`.
- **The v2 model hooks** — `ntdst_model_*` renamed to `ntdst/model/{creating,…}` with no
  shim; a listener on an old name is silently inert. Same for the old config-filter spellings.
- **13 field-type names** — a retired name is now a fatal at `register()` naming its
  canonical. The vocabulary is 17, closed, in one table (INV-8). `int` is signed.
- **`render()`, the envelope, `Theme::style()`/`script()`, `Scheduler`, `Mailer`** — the
  renderer and the envelope left with the dispatcher; assets, scheduling and mail are
  WordPress primitives or another package's job (`docs/philosophy.md` §6).
