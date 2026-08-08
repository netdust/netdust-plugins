# NTDST Architecture — Lessons

Project incidents that became framework rules. Each entry: what happened, what we learned, where the rule now lives.

For canonical rules and code patterns, read the `references/` files. This file is the journal — it explains *why* the references say what they say.

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
| Resolve template name → file path for WP | `ntdst_router()->template('single', $cb, $post_type)` | Raw `add_filter('template_include', ...)` |
| URL pattern → callback | `ntdst_router()->get('pattern/:param', $cb)` | Raw `add_action('parse_request', ...)` |
| Pre-query interception (rewrite query vars BEFORE WP runs the query) | Raw `add_action('parse_request', ...)` | `ntdst_router()` (fires on `template_include`, too late) |
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

**Documented prefix-awareness exception:** when callers read batch-loaded meta (`getPostsFast` / `withMeta` envelope), the meta arrives with raw prefixed keys (`_ntdst_*`). That's the framework's design — single-query meta load. Use `$this->repository->getMetaPrefix()` to read the prefix; never hardcode `_ntdst_` as a string literal. Acceptable trade-off in perf-critical batch paths (catalog pages, exports, completion math). NOT acceptable in single-record code paths.

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

## A method belongs on `Theme` iff its subject dies when you switch themes

**Problem (daan, 2026-08-08):** `NTDST_Theme` had grown into a facade over five unrelated
subsystems — it registered post types, registered taxonomies, registered API actions, and carried a
whole module DSL, alongside its actual job of wiring hooks, template paths and assets. Nothing about
a CPT or an API action dies when you switch themes, so none of it belonged there.

**Rule:** *a method belongs on `Theme` iff its subject dies when you switch themes.* A hook binding,
a template path, a template helper — yes. A post type, a taxonomy, an API action — no; those have
owners elsewhere and outlive the theme.

**The correction that matters more than the rule.** The first draft of this refactor deleted the
whole surface, having diagnosed *chainability* as the god-object smell. That was wrong, and it was
caught at the seam: the defect was **incoherence**, not chaining. The fluent wiring surface was
retained deliberately. When something feels like a god object, name which property is actually
offensive before you delete on the strength of the feeling.

---

## A forwarder is a second surface, and it drifts

**Problem (daan, 2026-08-08):** Two methods kept "for compatibility" did nothing but call the real
implementation on another class. Both drifted from their targets **twice in a single week** — once
in signature, once in null-handling — because nothing forced them to move together.

**Rule:** a pass-through kept for compatibility is not a courtesy, it is a second equally-correct
path that the codebase will drift between. **Delete as you move.** If a forwarder must survive a
migration window, give it an explicit removal date and a test that asserts it agrees with its target.

**Corollary for docs:** the same is true of documentation. A reference file restating an API is a
forwarder for that API, and it drifts exactly the way code forwarders do. That is why this skill's
references were collapsed — see the note at the end of this file.

---

## A grep bounded by a hypothesis finds what the hypothesis predicts

**Problem (daan, 2026-08-08):** This error recurred **three times in one refactor**, each time in a
different disguise:

1. *"Does daan call `->module()`?"* — grep says no, so the DSL looked dead. It was alive across the
   corpus; the question scoped the evidence to one site.
2. *"Is `ntdst_page_data()` dead?"* — grep over `*Service.php` said yes. A **template** called it on
   every render. The file-type filter encoded the hypothesis.
3. *"Do these CPTs derive their own capabilities?"* — an auth-surface map asserted they did. Source
   said three of them register `capability_type => 'post'` and inherit generic caps.

**Rule:** a grep is a test of a hypothesis, not a survey. Before trusting a negative result, ask
**what would this search miss if I were wrong** — which paths, which file types, which callers, which
*other repositories* — and widen it until the answer is "nothing material". Confirm a linchpin claim
against source, not against a previous agent's summary.

**Specifically for framework work:** derive seams from the **corpus across all consumer sites**, not
from one site's tree. "Does *this* site use it?" answers what this site uses, never what the
framework owes its consumers.

---

## Note on this skill's structure (2026-08-08)

The `references/` tree was **94% API inventory** (4,442 of 4,714 lines) and carried five files whose
claims were false. Inventory was collapsed into `references/framework-map.md` (decisions + traps) and
`golden-paths/feature-service.md` (a worked slice); `anti-patterns.md` and `architecture.md` were
kept and corrected. The retired files were `services.md`, `container.md`, `router.md`, `response.md`,
`logger.md`, `mailer.md`, `data-layer.md`, `theme-api.md`, `api-endpoints.md`, `rest-cors.md`,
`plugin-scaffold.md`, and both `templates/*.php.md`. Where a lesson above points at one of them, read
`framework-map.md` instead — and read **source** for any signature.
