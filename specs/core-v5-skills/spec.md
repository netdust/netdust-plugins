# core-v5-skills — netdust-wp teaches ntdst-core 5.0.0

**Status:** spec, revision 0 — written 2026-08-23 from the brainstorm of the same
day (Stefan present; Q1 one contract skill, Q2 the drift reviewer reads core's
invariants live, sections 1–2 approved). Awaiting review, then `writing-plans`.
**Repo:** `netdust-plugins` (marketplace source), plugin `netdust-wp`, branch
`feat/core-v5` off `main` @ `391eb0f`.
**Source of truth:** `~/Sites/ntdst-core` on `feat/core-shape` — the three specs
(`core-shape` rev 3, `field-types` rev 3, `core-trim` rev 2), `README.md`'s 5.0.0
section as landed so far, `ARCHITECTURE-INVARIANTS.md` INV-1…10,
`docs/philosophy.md`, `docs/parked/rest-query.md`.

---

## Intent decisions

| # | Question | Ruling | Source |
|---|---|---|---|
| D1 | Why now | **Skills must know how core works and the conventions for consumers before the fleet migrates.** | Stefan 2026-08-23: "we have to update netdust-plugins again, so skills know how core works and what best conventions are for consumers" |
| D2 | Skill structure | **One contract skill, `ntdst-framework`, rewritten on the v5 doors.** No split by door. | Stefan 2026-08-23: "A" |
| D3 | Drift reviewer's punch list | **Part 1 reads the consumer's vendored `ntdst-core/ARCHITECTURE-INVARIANTS.md` and runs its `Mechanical check:` lines at run time; Part 2 is the consumer-only list the agent owns.** No copy of core's rules in the agent. | Stefan 2026-08-23: "A" |
| D4 | Which version the skills describe | **v5 only.** An older core is recognised by its retired symbols (the skill's existing rule), not documented twice. | brainstorm, unchallenged (the skill's own "Meeting one in a project means that project is on an older core") |
| D5 | Stale eval cases | **Rewritten to their v5 counterparts under the same ids; `baseline_ref` = the pre-refresh commit.** | proposed 2026-08-23 (section 2), unchallenged |
| D6 | Version | **`netdust-wp` 0.9.0 → 1.0.0** — its contract becomes core 5.0.0. | proposed 2026-08-23, unchallenged |
| D7 | Timing against core-shape T13 | **Write now against specs + README-as-landed; one re-anchor task at core-shape's T13 commit / the tag.** | Stefan 2026-08-23 "ok" on section 2 |

---

## Context — measured 2026-08-23 on `main` @ `391eb0f`

Retired-surface mentions (`ntdst/api_data`, `ntdstAPI`, `ntdst_actions`, `public_fields`,
`getFormattedPosts`, `sectors`, `ntdst_service_*`, `auto_discover`, `apiSuccess`/`apiError`,
`->json(`, `->render(`, `ntdst_mail`, `ntdst_schedule`, `ntdst_model_*`, type aliases,
`template_include`, `get_nonce`, `mixin(`), per file:

| File | hits | What it is |
|---|---|---|
| `skills/ntdst-framework/SKILL.md` | 13 | the contract: `ntdst_actions()` door, rewrite-rule-plus-route, `auto_discover`, `_enabled` switch, `$theme->style()`, `render()` |
| `skills/ntdst-framework/lessons.md` | 10 | history — stays as history |
| `skills/ntdst-framework/references/traps.md` | 7 | "The api_data / REST surfaces", routing traps |
| `skills/ntdst-patterns/golden-paths/form-data-flow.md` | 24 | the api_data flow end to end (`ntdstAPI.call` → `get_nonce` → `ntdst/api_data/*`) |
| `…/golden-paths/admin-settings-page.md` | 11 | `render()`, `api_data` save |
| `…/golden-paths/content-type-feature.md` | 4 | field declarations with aliases |
| `agents/ntdst-drift-reviewer.md` | 9 | checks #3 (`wp_ajax_` → "the framework path is `ntdst/api_data`"), #4 (`->render()`), #9 (`template_include`) |
| `agents/ntdst-drift-reviewer.lessons.md` | 5 | history — stays |
| `skills/wp-security/SKILL.md` | 2 | "`ntdst_api` actions: the router…", CORS line |
| `skills/wp-plan-requirements/SKILL.md` | 1 | drift-category example |
| `evals/behavioral-lessons.json` | 12 | 6 of 12 cases assert v3/v4 symbols (`api-rate-budget`, `pages-custom-route`, `rest-cors-option`, `service-disable-filter`, `theme-facade-retired`, `rest-handler-return`, `route-response-refuses`) |
| `netdust-core/evals/prompts/scenario-5/6*` | 1 each | netdust-core plugin's, not this spec's |
| `skills/ntdst-yootheme/references/yootheme-content-binding.md` | 1 | the bridge; its own spec |

What v5 actually is (the seven facts the skills must carry):

1. **Declare in Data, WordPress reads** — `show_in_rest => true` per field → `register_post_meta()` → `/wp/v2/<type>`; `custom-fields` support added by core; a repeater is all-or-nothing; `json`/`array` never publish (INV-1). 17 types, no aliases, `int` signed, `html` = `wp_kses_post` (INV-8). `rest_query` parked (`docs/parked/rest-query.md`).
2. **Rest is the one surface** — `ntdst_rest($ns)->get()/post()…`; no `permission` = `is_user_logged_in`; `->public()` = `__return_true`; a string is a capability; a write verb with only a posture does not register; `cors()` feeds `allowed_http_origins`, REST-only; `wp.apiFetch` + `X-WP-Nonce` is the client (INV-2…5, 7).
3. **Pages on rewrite rules** — `path(':param' pattern, cb, method)` → `add_rewrite_rule` + `query_vars` + `template_redirect`; callback returns a path / `null` / `false`; placeholder-first refused; one template loader (INV-6).
4. **Boot: you load, core resolves** — `require_once` or Composer, never a scan; `metadata()['enabled']` and `conditional` are the switches; `ntdst/service/{slug}/config` (INV-10).
5. **One of each** — one query API (the chain), one logger (`ntdst_log()` file + error_log), one hook spelling (`ntdst/…`), `Container` = `set/get/has`, `Theme` = config + `on()/filter()`; `Mailer` lives in netdust-mail, `Scheduler` is two WordPress lines (INV-9).
6. **Response** — `html()` + `page()` + the file policy (`download()/inline()`); no JSON envelope, no `render()`, no MIME table.
7. **Consumers migrate by README's three tables**; nothing is shimmed.

---

## Functional requirements

- **FR-1:** `skills/ntdst-framework/SKILL.md` is rewritten as the v5 contract: header names core 5.0.0 and its anchor (spec revisions + README commit); `## Retired` lists every v5 removal by name (the README tables' left columns); `## Pick the door` has exactly three doors — a declared field, a route, a page — each with the one-line rule that decides it; `## Boot`, `## Data`, `## Rest`, `## Pages`, `## Templates` carry the seven facts above and nothing that contradicts them; the description's trigger list names v5 symbols (`ntdst_rest`, `->public()`, `show_in_rest`, `NTDST_FieldTypes`, `path()`) and drops `ntdst_actions()`. The skill stays a contract, not an inventory: no method list that core's own refusals already teach.
  Source: D1, D2 — Stefan 2026-08-23 "skills know how core works", "A"
- **FR-2:** `references/traps.md` is rewritten around what v5 source will not tell a consumer: `custom-fields` support widens the `meta` object to every globally registered key; a partially declared repeater reads back `null`; `int` is signed; `bool` stores `false` for the string `"false"`; a renamed hook listener is silently inert; the origin list is REST-only (admin-ajax keeps WordPress's); a placeholder-first `path()` is refused; `select` still does not validate its options; `required` is three things. Each trap names the core test or invariant that pins it.
  Source: D1; the traps are core-shape threat rows #1, #2, #9, #10, field-types requirements 2 and 5, core-trim threat #4
- **FR-3:** The three golden paths are rewritten on the v5 doors. `form-data-flow.md`: a form posts through `wp.apiFetch` to an `ntdst_rest()` route that names a capability (or `->public()` for a truly anonymous form, with `rate_limit`), the handler returns a `WP_REST_Response`/`WP_Error`, the repository writes through the chain; no nonce fetch, no `api_data`, no envelope. `content-type-feature.md`: the model declares canonical types and `show_in_rest` on exactly the fields the front end reads; `/wp/v2/<type>` is the read surface; a custom list route exists only for logic WordPress's collection cannot express (and `rest_query` is named as the parked path for a plain meta filter). `admin-settings-page.md`: the save path is a capability-gated `ntdst_rest()` route or the Settings API; no `render()`. Every code block in the three files runs against core 5.0.0 as written.
  Source: D1, D4; core-shape requirements 4, 8, 9 and 11, field-types requirement 1, `docs/parked/rest-query.md`
- **FR-4:** `agents/ntdst-drift-reviewer.md` becomes two parts. **Part 1 — core's invariants, live:** locate the consumer's vendored `ntdst-core/ARCHITECTURE-INVARIANTS.md` (mu-plugins path or Composer vendor path — the agent greps for the file, never assumes the location), parse every `**Mechanical check:**` line, run each over the consumer's own code scope with the scope substituted for core's paths, and report each INV number with its expected result and the actual hits; a core without the file (pre-4.x) is reported as "no invariants doc — Part 1 skipped", never as a pass. **Part 2 — consumer-only checks** the agent owns: repository bypass (`ntdst_data()->get(` outside `*Repository.php`), pass-through methods, swallowed `WP_Error`, hardcoded meta prefix, raw post/meta functions outside repositories, baseline-solved-it, golden-path conformance, and three new ones — a public symbol with zero readers in the consumer, a second API for a job the consumer already solved (two ways to do one thing), and `function_exists()` load-order guards around core helpers. Retired checks #3 (`wp_ajax_` → api_data), #4 (`->render()`), #9 (`template_include`) are replaced by their v5 forms: any `wp_ajax_`/`admin-post` handler or `register_rest_route()` call is drift toward `ntdst_rest()`; `ob_start + include` is drift toward `html()`/`page()`; a `template_include` filter is drift toward `path()`/`template()`.
  Source: D3 — Stefan 2026-08-23 "A"; yesterday's lesson (Stefan 2026-08-22: "this should have been picked up by drift reviewers")
- **FR-5:** `skills/wp-security/SKILL.md`'s NTDST section states the v5 posture: REST routes through `ntdst_rest()` only; the gate is `permission` (a capability string, `->public()`, or a callable); cookie callers carry `X-WP-Nonce` through `wp.apiFetch` and core mints nothing; a write verb without a capability does not register; `cors()` is REST-only and never `'*'`; declared fields are public to anyone once `show_in_rest` is on (a mis-declaration is a disclosure). `skills/wp-plan-requirements/SKILL.md`'s drift-category example points at the reviewer's two parts instead of naming a retired surface.
  Source: D1; core-shape requirements 4, 6 and 7, INV-1/INV-3/INV-4
- **FR-6:** `evals/behavioral-lessons.json`: the seven cases that assert v3/v4 symbols are rewritten to their v5 counterpart under the same `id` (e.g. `api-rate-budget` → the `rate_limit` option on a route; `pages-custom-route` → `path()` is the rewrite rule, no hand-written `add_rewrite_rule`; `service-disable-filter` → `metadata()['enabled']`/`conditional`, the filter is gone; `theme-facade-retired` → `$theme->pages()` is a fatal, `ntdst_pages()`; `rest-handler-return` / `route-response-refuses` → `WP_REST_Response`/`WP_Error` shapes), each with `baseline_ref` = `391eb0f` and `must_contain`/`must_not_contain` literal symbols; four new cases are added — a declared-field exposure question (answer names `show_in_rest` and the all-or-nothing repeater), a write-verb-without-capability question (answer: it does not register), a custom-URL question (answer: `path()` alone, callback returns a path), an alias question (`'integer'` → fatal naming `int`). `evals/retired-symbols.sh` greps the plugin for every retired symbol and exits non-zero on a hit outside `## Retired` blocks, `lessons.md` files and `evals/`. `REPORT.md` is re-run and rewritten.
  Source: D5; CLAUDE.md §8 "a lesson that changes a skill's behaviour ships with an eval case"
- **FR-7:** `netdust-wp/.claude-plugin/plugin.json` and the marketplace catalog entry move to `1.0.0`; the plugin README's one-line description says "ntdst-core 5.0.0". Nothing is pushed or tagged by this spec.
  Source: D6
- **FR-8:** After core-shape's T13 commit (README 5.0.0 complete) and again at the `v5.0.0` tag, a re-anchor pass re-reads `README.md`'s three migration tables and `ARCHITECTURE-INVARIANTS.md` against FR-1…FR-5's text, fixes every disagreement, updates the skill header's anchor, and re-runs FR-6's proofs. Until then the header says "pre-tag, anchored on specs".
  Source: D7 — Stefan 2026-08-23 "ok" on section 2

---

## Success criteria

- **SC-1:** `bash evals/retired-symbols.sh` exits 0: 0 hits for the 24 retired symbols (`ntdst/api_data`, `ntdstAPI`, `ntdst_actions`, `get_nonce`, `public_fields`, `publicRows`, `getFormattedPosts`, `ntdst_get_formatted_posts`, `sectors`, `ntdst_service_`, `auto_discover`, `discovery_paths`, `apiSuccess`, `apiError`, `->json(`, `->render(`, `ntdst_redirect`, `ntdst_mail`, `ntdst_schedule_recurring`, `ntdst_notify`, `ntdst_model_`, `mixin(`, `signed_int`, `wysiwyg`) in `plugins/netdust-wp/` outside `## Retired` blocks, `*lessons.md`, and `evals/`.
- **SC-2:** `run-correctness-eval.sh` over the rewritten file: 11 of 11 v5 cases discriminate (baseline emits the retired symbol, skill-on does not) and ≥ 10 of 11 pass the judge; the 2 router-decides control cases keep their prior result; 0 errored.
- **SC-3:** `ntdst-framework/SKILL.md` ≤ 260 lines; contains exactly 3 rows in the `## Pick the door` table; `grep -c "ntdst_rest\|->public()\|show_in_rest\|path(" SKILL.md` ≥ 8; `grep -c "ntdst_actions\|api_data" SKILL.md` = the count inside `## Retired` only.
- **SC-4:** The drift reviewer, run on daan's `chore/core-path-repo` working copy: Part 1 prints 10 INV lines, each with its expected result and actual hit count, and the run's Part 2 still reports the repository-bypass hits the previous version reported on the same working copy (count equal or greater, 0 lost).
- **SC-5:** The three golden paths contain 0 retired symbols (SC-1's list) and every PHP block in them passes `php -l`; `form-data-flow.md`'s sequence diagram has `wp.apiFetch` and `permission` in it and no `get_nonce`.
- **SC-6:** `plugin.json` version = `1.0.0`; marketplace catalog entry = `1.0.0`; `git log --oneline main..feat/core-v5 | wc -l` ≥ 6 (one commit per task); 0 pushes.
- **SC-7:** After FR-8's re-anchor: `diff` between README's three migration tables' left columns and the skill's `## Retired` list = 0 missing names.

---

## Security-relevant surfaces

The plan owes a `## Threat model`.

- [ ] Authorization / tokens / tenancy / untrusted parsing / outbound to user-supplied addresses — none: this spec edits Markdown, JSON and a shell script in a plugin repo; no runtime code.
- [x] None of the above

## User-facing surfaces

The plan owes `## Acceptance flows`.

- [ ] A page, form, admin screen or API a person uses — none: the readers are agents.
- [x] None of the above

---

## Assumptions

- core's `README.md` 5.0.0 section is complete for field-types and core-trim at `ff078f5`+ and incomplete for core-shape until its T13; FR-8 closes that gap.
- `run-correctness-eval.sh` still runs as documented in `evals/REPORT.md` (ground-truthed by the plan's first eval task before anything is asserted on it).
- The drift reviewer can find the vendored core on every D6 site: `web/app/mu-plugins/ntdst-core/` (daan, todai, netdust), `app/content/mu-plugins/ntdst-core/` (josworld), `vendor/netdust/ntdst-core/` (stride, Composer).
- `netdust-core` plugin's eval prompts and `ntdst-yootheme`'s binding reference keep their single mentions; flagged in the plan, not edited.

---

## Out of scope

- stride's v5 migration; the YOOtheme bridge promotion (`ntdst-yootheme`); the `netdust-core` plugin's own evals.
- Any new skill. D2 rules one contract skill; `wp-database`, `wp-frontend`, `wp-infra`, `wp-testing`, `bedrock-composer` are untouched (0 stale hits).
- Pushing or tagging the marketplace; the catalog version bump is local until Stefan pushes.
