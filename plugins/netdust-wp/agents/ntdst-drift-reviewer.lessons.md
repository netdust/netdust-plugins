# ntdst-drift-reviewer — Calibration Notes

Cases where the agent flagged something that turned out NOT to be drift, OR rule nuances discovered mid-audit. Read this BEFORE running an audit. Apply as additional exception rules — never as new findings to make.

## Curation rules

- **Manual review only.** The agent suggests entries in its report; the human decides what lands here. The agent does not append to this file.
- **Size cap: ~15 entries.** When over, either: (a) promote a long-standing exception to a permanent rule in `ntdst-architecture/references/anti-patterns.md`, or (b) prune entries that are no longer relevant (the drifted file got refactored).
- **What goes in:** patterns that LOOK like drift but aren't, or rule nuances neither the agent prompt nor the skill references captured. Each entry must generalize beyond a single file — if it's "this one file in stride does X for a stride reason," it belongs in the project's memory directory, not here.
- **What does NOT go in:** project-specific exceptions (those go in `~/.claude/projects/<project>/memory/`), positive calibration ("the audit was clean"), or stylistic disagreements.

## Entry format

```markdown
### YYYY-MM-DD — <one-line description>

**Pattern that looked like drift:** <what the grep matched>

**Why it isn't:** <the actual reason — be specific>

**Example from a real audit:** <file:line — keep one concrete instance>

**Updated exception rule:** <when to NOT flag this in future audits, in one sentence>
```

---

### 2026-05-19 — Custom-table repositories override `AbstractRepository::find()` and return `?object`, not `WP_Post|WP_Error`

**Pattern that looked like drift:** `if (!$registration)` checks after `RegistrationRepository::find($id)` flagged as "Swallowed WP_Error treated as falsy null" — i.e. the agent assumed any `Repository::find()` follows the AbstractRepository signature `WP_Post|WP_Error`, where a `WP_Error` would silently pass the `!` check.

**Why it isn't:** Repositories backed by **custom tables** (not CPTs) override `find()` with a different signature. They return `?object` (`null` when not found) directly from `$wpdb->get_row()`. The `if (!$registration)` null-check is correct for these repos and does NOT swallow a `WP_Error`, because no `WP_Error` ever gets returned. The clue is the property `protected string $postType = …` — custom-table repos lack a `postType` and define a `table()` method instead.

**Example from a real audit:** `Stride/Modules/Enrollment/RegistrationRepository.php:161` — `public function find(int $id): ?object` (custom table `wp_vad_registrations`), called from `Stride/Modules/Invoicing/QuoteService.php:172-175`. Flagged as critical bug in 2026-05-19 Invoicing audit; verified false positive.

**Updated exception rule:** Before flagging `if (!$x)` after a `$repo->find($id)` call as a swallowed `WP_Error`, **verify the repository's actual `find()` signature**. If the repository extends `AbstractRepository` but does NOT override `find()`, the WP_Post|WP_Error rule applies. If the repository **overrides** `find()` (which custom-table repos typically do, returning `?object`), the null check is correct and not drift.

---

### 2026-05-19 — Template-render drift in a mu-plugin: check layer direction before picking a fix

**Pattern that looked like drift:** `ob_start() + stridence_template_part(...) + ob_get_clean()` inside `mu-plugins/stride-core/.../Renderer.php`. Surface reading: classic Category-4 "render template → string via ob buffer" — substitute with the project's blessed string-returning helper.

**Why it isn't (or rather: why the obvious fix is wrong):** `stridence_template_part()` and `stridence_template_html()` are **theme helpers** (`themes/stridence/helpers/templates.php`). A mu-plugin calling theme helpers inverts the dependency direction — `stride-core` becomes coupled to the active theme, breaking the rule that mu-plugins must be theme-agnostic (theme→plugin is fine; plugin→theme is not). The drift here is **two-layered**: (1) buffer-and-include is the wrong tool, AND (2) the obvious replacement (the theme's wrapper) violates layer separation. The real fix moves the partial *into* the mu-plugin's `templates/` dir, registers that dir with `NTDST_Template_Loader::addPath()` at boot, and calls `ntdst_response()->withData(['args' => $args] + $args)->html('slug')` directly — no theme helpers.

Auxiliary nuance about `ntdst_response()->html()`: it `extract()`s the data array as loose vars, but many existing partials read `$args['key']` (the `get_template_part` convention that `stridence_template_html` preserves with `withData(['args' => $args] + $args)`). When moving partials into a mu-plugin or calling `ntdst_response()` directly, **mirror the `$args` wrapper contract** if the partial reads `$args[...]`, otherwise the partial silently renders nothing.

**Example from a real audit:** `Stride/Modules/Questionnaire/QuestionnaireRenderer.php:26` (commit `043e1124`, 2026-05-19) — flagged as Category-4 drift. The naive fix was to swap in `stridence_template_html()`, but the correct fix moved 5 shared form-field partials from `themes/stridence/templates/forms/fields/` into `stride-core/templates/forms/fields/`, registered the path in `stride-core.php` boot, and switched call sites to `ntdst_response()->withData([...])->html('forms/fields/field-group')`.

**Updated exception rule:** When flagging Category-4 (`ob_start + include`) inside a **mu-plugin** or any plugin code, **before recommending the project's wrapper helper, check which file the helper lives in** (`grep -l "function <helper_name>"`). If the helper lives in the theme, do NOT recommend it as the fix — recommend (a) moving the partial into the plugin's own `templates/` dir + registering via `NTDST_Template_Loader::addPath()`, plus (b) calling `ntdst_response()->withData(...)->html(...)` directly. Surface the layer-direction concern explicitly in the finding so the human can decide scope (which partials are plugin-owned vs. theme-owned). Plugin→theme code calls are a separate, often larger drift than the original Category-4 finding.

---

### 2026-05-19 — `AbstractRepository::findFields()` is single-ID, not batch — don't suggest it as a batch-meta replacement

**Pattern that looked like drift:** Raw `$wpdb->get_results()` on `{$wpdb->postmeta}` inside a service to batch-fetch one meta key for a list of post IDs. The agent suggested replacing it with `EditionRepository::findFields($ids, ['course_id'])` as a typed batch-fetch.

**Why it isn't (in that exact shape):** `AbstractRepository::findFields(int $id): array` (at `Infrastructure/AbstractRepository.php:92`) takes a **single ID** and returns all meta for that one post — it's a singular operation. There is no batch-meta helper in the framework today. The signature `findFields($ids, ['field'])` does not exist; suggesting it produces a fix the human will discover doesn't compile.

**Example from a real audit:** `Stride/Modules/User/UserDashboardService.php:485-498` (commit `08c1e285`, 2026-05-19 User-module audit) — the agent suggested `$this->editionRepository->findFields(array_unique($editionIds), ['course_id'])`. The real fix kept the raw SQL (no batch helper exists) but replaced the hardcoded `'_ntdst_course_id'` literal with `$this->editionRepository->getMetaPrefix() . 'course_id'` (Cat 7's hardcoded-prefix concern), wrapped the key in `$wpdb->prepare()`, and added a comment explaining the trade-off. The batch SQL itself is acceptable under the "batch-meta perf exception" — only the prefix string was drift.

**Updated exception rule:** When considering Cat 1 / Cat 8 batch-meta drift suggestions, **verify the proposed `findFields` / batch-fetch helper actually exists with that signature in the framework** before recommending it. `findFields(int $id): array` is single-ID-only; surfacing it as a `findFields($ids, ['field'])` batch is a fabricated API. If a batch helper would genuinely simplify the call site, surface it as a "Framework gaps observed" candidate for `ntdst-core-gaps.md` rather than as a fix.

Auxiliary note: when a service holds a raw `$wpdb->get_results(... meta_key = 'literal')` for legitimate batch-meta perf reasons, the Cat 7 fix is **just** the prefix string (`$repo->getMetaPrefix() . 'name'` instead of `'_ntdst_name'`), not necessarily replacing the SQL. The exception is intentionally narrow — touch only what's drift.

---

### 2026-05-19 — Constructor-injection vs in-method `ntdst_get()` when at the 5-param soft cap

**Pattern that looked like drift:** A service calls `ntdst_get(QuoteService::class)` / `ntdst_get(EnrollmentCompletion::class)` inside multiple methods rather than constructor-injecting. Surface reading: should be constructor-injected per `ntdst-architecture/references/architecture.md`; in-method `ntdst_get` is the thin-handler pattern, not the service pattern.

**Why it isn't necessarily drift:** The architecture reference treats the 5-param constructor cap as a soft warning meaning "the class is doing too much, split it." When the constructor already sits at or near the cap, adding 2 more deps pushes well past it. The right alternative — splitting the class — is a separate, larger refactor. In-method `ntdst_get()` is the pragmatic middle ground that preserves DI testability (the test container resolves the dep) while not bloating the constructor.

**Example from a real audit:** `Stride/Modules/User/UserDashboardService.php` (User-module audit, 2026-05-19) — `QuoteService` used at 3 method sites, `EnrollmentCompletion` at 2 sites, both via `ntdst_get(...)`. Constructor already at 5–6 readonly deps. Adding the two would mean 7–8 constructor params and force the test fixture rebuild. The class IS over 800 lines (legitimately split-worthy) but the split is its own piece of work.

**Updated exception rule:** When flagging Cat-10 in-method `ntdst_get()` calls as "should be constructor-injected," **count the existing constructor params first**. If the constructor is at or above 5 deps, surface as **Borderline** (not Drift) and offer two paths in the finding: (a) inject anyway and accept the 7+ param signature, OR (b) leave the in-method calls and document the soft-cap reasoning in a class-level docblock. Flag as hard drift only when (i) the class is well under cap AND (ii) the dep is used in 3+ methods.

---

### 2026-05-19 — Ability / registrar / thin-handler shape: in-method `ntdst_get()` is correct even under the cap

**Pattern that looked like drift:** A class extends `AbstractService` (so structurally a service) with a zero-or-low-param constructor, but calls `ntdst_get()` inside multiple execute callbacks rather than constructor-injecting its domain dependencies. By the previous calibration (count params first), an audit would flag this as Cat-10: constructor is well under the 5-param cap, deps used in 3+ methods — looks like textbook constructor-injection drift.

**Why it isn't:** The shape matters more than the param count. Ability registrars, REST controllers wiring `register_rest_route` callbacks, and CLAUDE.md's "Thin Handler Pattern" classes (`Handlers/`) all share the same lifecycle: they register callbacks against a third-party hook (`wp_abilities_api_init`, `rest_api_init`, `wp_ajax_*`), and the callbacks fire lazily — once per HTTP request, or once per LLM tool invocation, never on a plain admin pageview. Eager constructor injection would resolve 4–6 domain services on **every** WP boot for a code path that is inactive on 99% of requests. CLAUDE.md explicitly documents the in-method `ntdst_get()` choice for `Handlers/` ("No constructor DI — use `ntdst_get()` inside methods").

**Example from a real audit:** `Stride/Modules/Assistant/ReadAbilityRegistrar.php` and `WriteAbilityRegistrar.php` (Assistant-module audit, 2026-05-19). Both extend `AbstractService` with zero-param constructors. `ReadAbilityRegistrar` resolves 6 unique deps via `ntdst_get()` across 24 call sites; `WriteAbilityRegistrar` resolves 4 deps across 10 call sites. By the param-count rule the audit flagged Cat-10, but the fix landed in commit `b752b677` was a class-level docblock declaring the lazy-resolve choice, not constructor injection.

**Updated exception rule:** Before flagging Cat-10 in-method `ntdst_get()` on a class with a zero/low-param constructor, **check the class shape**. If the class registers its execute callbacks with a third-party hook (`wp_abilities_api_init`, `rest_api_init`, `wp_ajax_*`, `admin_post_*`, `add_shortcode` — anything where the callback fires lazily), surface as **Borderline** (or skip entirely) and recommend a one-line class-level docblock declaring the choice. The "constructor is under cap → should inject" rule applies to orchestrating domain services, not to registrar / handler / shortcode shapes. The lifecycle, not the param count, is what determines whether eager DI is the right call.

Auxiliary note: this rule and the prior 5-param-cap rule compose, not conflict. The hierarchy is now: (1) handler/registrar shape → in-method `ntdst_get` is fine regardless of param count; (2) at/above 5-param cap → Borderline regardless of shape; (3) under cap AND not handler/registrar AND dep used in 3+ methods → Drift, suggest constructor injection.

---

### 2026-05-19 — Manual `new SomeClass(...)` inside a sibling service's hook callback — check the project's convention for that *kind* of class

**Pattern that looked like drift:** A service contains `add_action('init', fn() => new SomeOtherClass(...))` inside its `init()`. Surface reading: "service does too much, should not be constructing other classes" — Cat-10-ish ("dependency only used for one call") or Cat-2-ish ("service is a forwarder").

**Why it's drift in a specific shape that the existing rule books don't quite name:** The naive Cat-10 / Cat-2 fixes (inject the class, or move the construction up) miss the actual problem, which is that **the project usually has a convention for how that *kind* of class is wired**, and the manual `new` bypasses it. Shortcodes, handlers, controllers — each kind of class typically has a registration pattern (`ntdst_set + ntdst_get` from a bootstrap callback, `plugin-config.php` enumeration, etc.). Manually `new`-ing inside another service's hook (a) prevents the container from holding the instance, so `ntdst_get(That::class)` returns a fresh unwired one, (b) breaks mock-the-class testability, (c) creates a hidden coupling where deleting the host service silently breaks the constructed class.

**Example from a real audit:** `Stride/Modules/Audit/AuditBridge.php:32-34` (Audit-module audit, 2026-05-19) — `add_action('init', function () { new ActivityShortcode(...); })`. The drift wasn't "AuditBridge has too many responsibilities" (one extra line); it was that the project registers all other shortcodes via `ntdst_set + ntdst_get` in `stride-core.php:122-126` (`DashboardShortcode`, `QuotesShortcode`). The shortcode was the odd one out. Fix in commit `ac1db160` moved registration to the standard location and dropped the manual `new`.

**Updated exception rule:** When you see `new <SomeOtherClass>(...)` inside a service's hook callback or `init()`, **first grep the project for how other classes of the same kind are wired** (`grep -rn "ntdst_set.*<Kind>Shortcode\b"` or similar). If sibling classes of the same kind are container-registered (typically from a bootstrap file at `ntdst/features_ready` or `ntdst/core_ready`), the manual `new` is drift even though it doesn't trip any of the named anti-patterns. Surface as Cat-10 / sibling-mismatch and cite the project's bootstrap as evidence ("`stride-core.php:122-126` registers DashboardShortcode and QuotesShortcode this way; ActivityShortcode is the outlier"). If no sibling convention exists yet (e.g. the project has only one shortcode and the audit can't tell what the convention is), surface as **Borderline** rather than Drift — the human knows whether it's worth standardising.

Auxiliary note: this is distinct from "service constructs its repository" (which is legitimate — repositories are owned by their domain service). The rule is specifically about classes with their **own lifecycle** (shortcodes, ability registrars, handlers, REST controllers) that the project typically wires via the container.

---

### 2026-05-19 — `wp_ajax_*` is the right tool for direct-anchor download links (Cat-3 exception)

**Pattern that looked like drift:** A handler registering `wp_ajax_*` actions to serve PDF/CSV/etc. download responses. The naïve Cat-3 fix is "migrate to `add_filter('ntdst/api_data/{action}', ...)` + `ntdst_response()->download()` because a sibling handler (e.g. iCal export) does it that way." The Handlers-module audit on 2026-05-19 made exactly this suggestion against `AnnualReportHandler`.

**Why it isn't drift:** `NTDST_Endpoints` registers `/wp-json/ntdst/v1/action` as **POST-only** with a separately-fetched nonce (see `ntdst-core/api/Endpoints.php:88-103`). The whole `ntdst/api_data/*` filter chain runs only inside that POST handler. That makes the path incompatible with `<a href="...">click to download</a>` anchors — those are GET navigations with the nonce in the URL, not POSTs with a JSON body. The sibling `ICalHandler` works via `ntdstAPI.download()` (JS-driven POST + blob handoff), not via a direct anchor. Whenever an admin page presents download buttons as clickable links rather than JS-bound buttons, `wp_ajax_*` with `?action=…&_wpnonce=…` in the URL is the right tool, not drift.

**Example from a real audit:** `Stride/Handlers/AnnualReportHandler.php:28-29` flagged as Cat-3 drift in the 2026-05-19 Handlers audit, with the suggested fix being migration to `ntdst/api_data/stride_annual_report_pdf` modelled on `ICalHandler`. The fix was wrong — `AnnualReportPage` renders the PDF/CSV buttons as plain `<a href>` anchors (see `Modules/Reporting/Admin/AnnualReportPage.php:127-132`). Resolution was a docblock on the handler explaining the choice, not a migration.

**Updated exception rule:** When flagging Cat-3 (`wp_ajax_*` instead of `ntdst/api_data/*`), **check how the endpoint is invoked from the frontend** before suggesting migration. If the admin page or template renders a direct `<a href="…admin-ajax.php?action=…">` anchor (`grep -rn "admin-ajax\.php?action=<the_action>"` plus a glance at the template), the migration is incompatible — `ntdst/api_data/*` requires a POST + JSON body, which an anchor can't provide. Surface as documented Cat-3 exception: ask the human to add a docblock explaining the choice rather than to migrate. The sibling-handler analogy ("ICalHandler does it via ntdst/api_data, so AnnualReportHandler can too") is invalid when the sibling is JS-invoked and the new one is anchor-invoked — verify the invocation path, not just the response shape.

Auxiliary note: this composes with the earlier Cat-3 exception language. The full set of legitimate `wp_ajax_*` reasons is now (a) admin-area POST routing (`admin_post_*` is its own tool), (b) responses needing headers a JSON-filter wrapper precludes, AND (c) direct-anchor downloads as documented here. (a) is uncommon; (b) is rare (the framework's `download()` handles standard download headers); (c) is the one to expect in real codebases.
