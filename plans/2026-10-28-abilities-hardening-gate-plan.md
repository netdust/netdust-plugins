# Hand-off — for the laptop session that takes this over

**Date:** 2026-10-28
**Repo:** `github.com:netdust/netdust-plugins`, branch `ccr-38321f1f-9ivl0o` (cloud session branch; merge or cherry-pick these two files to `main`, nothing else is on it)
**Class:** A — one framework change (ntdst-core), one baseline pass, harness upkeep across four repos.
**Status:** PLAN ONLY — a cross-repo draft, pre-spec. Nothing implemented, nothing in `specs/` yet.

**How to start on the laptop:**
1. Read `plans/2026-10-28-wp-ai-landscape.md` once for the why (ten minutes).
2. Put rulings R1–R6 (table below) to Stefan first; they shape A01, A02, C01, C02 and B02.
3. Then `netdust-gates:policy` per cluster, in this order: D (netdust-wp 1.4.0, an afternoon),
   then A (ntdst-core 5.5.0, `feature/abilities-bridge`) and C (ntdst-baseline 2.22.0,
   `feature/hardening-2026-10`) in parallel, then B (`gate:wp` in both packages, after A has
   landed), then E. Each cluster becomes its own `specs/<feature>/{spec,plan,tasks}.md` in its
   own repo; this file is the brief, not the spec.
4. Cluster A's A05 is a Stride branch that is never merged by this plan; it is the proof.
5. Verify the two pins in D01 against trunk on the day you run it; they were current on 2026-10-28.

---

# Plan — abilities bridge, hardening pass, upstream skills, Playground gate

**Status:** draft for Stefan's approval, 2026-10-28. Lives in `netdust-plugins/plans/`. On approval each
cluster becomes `specs/<feature>/{spec,plan,tasks}.md` in its own repo as the first commits of
its branch, per `netdust-gates:policy`.
**Source:** the landscape research of 2026-10-28
(`wp-ai-landscape-2026-10-28.md`, same folder) and Stefan's rulings in that thread:
"all seem good", one framework change (core), the rest baseline upkeep and harness maintenance.
**Repos:** CORE `ntdst-core` 5.4.1 → 5.5.0 · BASELINE `ntdst-baseline` 2.21.3 → 2.22.0 ·
WP `netdust-plugins/plugins/netdust-wp` 1.3.2 → 1.4.0.
**Order:** D (skills) first, it is an afternoon and the abilities skills are tools for A.
Then A (core) and C (baseline) in parallel, they touch no shared file. B (Playground gate)
after A lands in core, so the first integration test can be the ability round-trip.
E (design directions) any time.

## What the second look changed

1. `wp_register_ability()` refuses any call made before `wp_abilities_api_init` has fired,
   and that hook fires lazily, inside `WP_Abilities_Registry::get_instance()`, on first
   access after `init`. So the bridge cannot register inline from `registerOne()`. It
   records the declaration and walks the record when the hook fires. Trac #65583 would relax
   the window; the design does not depend on it.
2. Exposure has three spellings. 6.9/7.0 read `meta.show_in_rest`; 7.1 adds `meta.public`
   which seeds it; the MCP Adapter reads `meta.mcp.public` (its docs also accept
   `meta.public`). The bridge writes all three from one option, so a site on any of the
   three WordPress versions gets the same answer.
3. WordPress/agent-skills trunk is `eff3785fc28c4380d172094518c66a6a997c95d4` today;
   the script pins `d87ee69` (2026-09-06). The `skills` CLI is 1.7.4; the script pins 1.5.23.
4. The Playground CLI page documents `server --mount=host:vfs`, `--mount-before-install`,
   `--blueprint`, `--php`, `--wp`, `--login`, `--wordpress-install-mode`, SQLite only, and
   `run-blueprint` for a headless run. It documents a plugin mount, not an mu-plugin mount.
   The gate's first task is therefore a spike that proves the mu-plugins mount, not a script.

## Rulings needed from Stefan before execution

| # | Question | My recommendation |
|---|---|---|
| R1 | A write route's ability must declare `destructive` and `idempotent`, or core refuses the declaration. Alternative: derive from the verb (DELETE destructive, PUT idempotent). | Refuse. Deriving is guessing, and the audit skill and abilities-rest-adapter both refuse too. |
| R2 | An ability needs an `output_schema`. Take it from the route's `schema` option when present; when absent, refuse, or fall back to a permissive schema? | Refuse. It also pushes consumers to declare `schema` on the route, which the REST surface should have had anyway. |
| R3 | On WordPress < 6.9 the `ability` option is inert. Silent, or one `_doing_it_wrong` per declaration? | One `_doing_it_wrong`, debug only. Silent inert is the trap `traps.md` exists to list. |
| R4 | Ability category: one per REST namespace, derived (`stride/v1` → `stride-v1`), or named in the option? | Derived, overridable by `category` in the option. |
| R5 | Baseline new switches default ON or OFF? | ON for the ones with no visible site effect (app-password flow, credential revoke, JSONP, pingbacks, font library, auto-sizes). OFF for the ones a site can notice (upload MIME by role, attachment 404 for logged-in, min password length). Each row below says which. |
| R6 | The Playground gate in `composer gate` from day one, or a separate `composer gate:wp` until it has run green for a month? | Separate first. A Node dependency in the package gate is new, and the gate must not go red for a reason that is not the code. |

---

## Cluster A — CORE: an ability is the shadow of a route (5.5.0, additive)

Stakes: high. It is a new public surface on every consumer, and an MCP client acts as a
logged-in user.

Behaviour: a route declared through `ntdst_rest()` with an `ability` option is also a
WordPress ability. Executing the ability dispatches the route through `rest_do_request()`,
so the route's permission callback, the rate limiter charge and the response shaping run
once and in the one place they already run. The ability is private unless the declaration
says `public`. Nothing else in core, baseline or a consumer calls `wp_register_ability()`.

Observable: on a WP 7.0 site with the MCP Adapter active,
`wp eval 'print_r(array_keys(wp_get_abilities()));'` lists `stride-v1/list-registrations`
after Stride declares it, `GET /wp-json/wp-abilities/v1/abilities` omits it while
`public` is unset and lists it after, and `wp mcp-adapter` over STDIO answers
`discover-abilities` with the same name and its schema. On DDEV: one `rest_do_request()`
per execution, the limiter transient incremented once.

RED until: `tests/Unit/NtdstRestAbilityTest.php`.

Invariant: **INV-11 — An ability is the shadow of a route.** Convergence point
`api/Rest.php`. Bypass smell: `wp_register_ability(` or `wp_register_ability_category(`
outside `api/Rest.php`; an ability whose `execute_callback` is not a REST dispatch; a
consumer class named `*AbilityRegistrar`. Mechanical check:
`grep -rn "wp_register_ability" --include=*.php . | grep -vE "^(\./)?api/Rest\.php|(^|/)vendor/|(^|/)tests/" | grep -vE "^[^:]+:[0-9]+: *(\*|//|/\*)"` → EMPTY.

The option, as a consumer writes it:

```php
ntdst_rest('stride/v1')
    ->get('/registrations', [$c, 'index'], [
        'permission' => 'edit_registrations',
        'args'       => ['status' => ['type' => 'string', 'enum' => ['pending', 'confirmed']]],
        'schema'     => [$c, 'itemSchema'],
        'ability'    => [
            'name'        => 'list-registrations',   // required: lowercase, digits, dashes
            'label'       => 'List registrations',   // required by WordPress
            'description' => 'Registrations for the current event, optionally by status.',
            'public'      => false,                  // default; true writes public, show_in_rest, mcp.public
        ],
    ])
    ->post('/registrations/(?P<id>\d+)/confirm', [$c, 'confirm'], [
        'permission' => 'edit_registrations',
        'schema'     => [$c, 'itemSchema'],
        'ability'    => [
            'name' => 'confirm-registration', 'label' => '…', 'description' => '…',
            'destructive' => false, 'idempotent' => true,   // required on a write verb (R1)
        ],
    ]);
```

Tasks (every task closes with `composer gate` exit 0 and one commit by pathspec):

- [ ] A01 [Tier A] `registerOne()` accepts `ability` in `$known`; validates it with the
  existing `refuse()` path: `name` matches `^[a-z0-9-]+$`, `label` and `description`
  non-empty strings, a write verb carries boolean `destructive` and `idempotent` (R1), an
  `output_schema` exists from the route's `schema` or the option (R2); records the
  declaration in a private static buffer keyed by `namespace/name`; a duplicate name
  refuses. Nothing is registered yet.
  (files: api/Rest.php, tests/Unit/NtdstRestAbilityTest.php)
  Unit test: each refusal names its reason; a valid declaration is recorded once; the
  recorded shape carries route, methods, resolved permission, args, schema, public.
- [ ] A02 [Tier A] The walk. Core hooks `wp_abilities_api_categories_init` once to
  register one category per namespace present in the buffer (R4), and
  `wp_abilities_api_init` once to call `rest_get_server()` (flushes declarations hooked at
  `rest_api_init`) and then `wp_register_ability()` per record: `input_schema` built from
  `args` (type, description, enum, default, required → properties + required), `output_schema`
  from the route `schema` callable's result, `permission_callback` = the UNGUARDED resolved
  permission (capability or callable; never the limiter guard, so discovery does not charge),
  `execute_callback` = `rest_do_request(new WP_REST_Request($method, '/'.$ns.$route))` with
  input mapped to params, errors returned as `WP_Error` with the REST status, `meta` =
  `['annotations' => ['readonly' => <GET/HEAD>, 'destructive' => …, 'idempotent' => …],
  'public' => $p, 'show_in_rest' => $p, 'mcp' => ['public' => $p]]`. Hooks are added only
  when the buffer is non-empty and `function_exists('wp_register_ability')`; otherwise R3.
  (files: api/Rest.php, tests/Unit/NtdstRestAbilityTest.php, tests/Support/RestApiInitHarness.php)
  Unit test: Brain Monkey `Functions\expect('wp_register_ability')->once()` with the exact
  args array for the GET and the POST declarations above; `rest_get_server` expected before
  it; on `function_exists` false, zero calls and one `_doing_it_wrong`.
- [ ] A03 [Tier A] The dispatch is one dispatch. Executing the ability charges the limiter
  once and runs the permission once (INV-7). `->public()` routes register with
  `__return_true` and `readonly` true; a `->public()` write cannot exist (INV-3), so no
  anonymous destructive ability can either; test pins it.
  (files: api/Rest.php, tests/Unit/NtdstRestAbilityTest.php, tests/Unit/NtdstRestAuthBeforeLimitTest.php)
- [ ] A04 [Tier B] INV-11 in `ARCHITECTURE-INVARIANTS.md` with the check run verbatim at the
  commit; `bin/guard.sh` gains the grep; `docs/philosophy.md` §1 gains the sentence "an
  ability is a route's shadow, core registers no ability of its own"; README `## Versions`
  gets `### 5.5.0 — abilities` with the option table and the three exposure spellings;
  CHANGELOG; `Version: 5.5.0`; branch-alias `5.5.x-dev`.
  (files: ARCHITECTURE-INVARIANTS.md, bin/guard.sh, docs/philosophy.md, README.md, CHANGELOG.md, ntdst-core.php, composer.json)
- [ ] A05 [Tier A, STRIDE, never merged by this plan] Branch `chore/abilities-bridge`:
  delete `Modules/Assistant/ReadAbilityRegistrar.php` and `WriteAbilityRegistrar.php`,
  move each ability onto its route's `ability` option, run the drift reviewer (D04's new
  check) and the `wp-abilities-verify` skill on the branch. The diff is the proof the
  option covers a real consumer. If one Stride ability has no route behind it, that is a
  finding for the plan, not a reason to add a second door.
  (files: stride tree only)
- [ ] A06 [Tier B] Threat model, `docs/threat-models/2026-10-abilities-bridge.md`: an MCP
  client is a logged-in user, so an application password is the credential and the
  route's capability is the floor; `public` governs discovery, never authorization;
  prompt-injection through ability descriptions is out of scope for core and named as such.
  (files: docs/threat-models/)

Out of scope for A: shipping the MCP Adapter. It stays a per-site composer dependency
(`wordpress/mcp-adapter`) until a second site wants it; then it is a baseline question.

---

## Cluster B — CORE and BASELINE: a Blueprint boots the package (gate:wp)

Stakes: standard. It adds a check; it changes no shipped code.

Behaviour: each package carries a `blueprint.json` and `bin/playground-gate.sh`.
`composer gate:wp` boots a real WordPress through the Playground CLI with the package
mounted as an mu-plugin, runs the smoke assertions inside it, and exits non-zero on any
failure. Brain Monkey stays the first gate step and is untouched.

Observable: `composer gate:wp` in `ntdst-core` prints `ok: ntdst_get`, `ok: route 200`,
`ok: ability listed`, `ok: textarea newline kept` and exits 0; a deliberate
`sanitize_text_field()` in place of `sanitize_textarea_field()` in `FieldTypes.php` turns
the last line into `FAIL` and exit 1.

RED until: the spike (B01) decides the shape; the RED is the exit code of B02's script
against the broken `FieldTypes.php`.

- [ ] B01 [Tier A, spike, time-boxed to one session] Prove the mount:
  `npx @wp-playground/cli@latest server --php=8.3 --mount=.:/wordpress/wp-content/mu-plugins/ntdst-core --blueprint=blueprint.json`
  with a Blueprint `writeFile` step that drops `mu-plugins/00-ntdst.php` requiring
  `ntdst-core/ntdst-core.php` (mu-plugins load top-level files only; there is no Bedrock
  autoloader here), a `runPHP` step asserting `function_exists('ntdst_get')`, and
  `--wordpress-install-mode` left default. Record in `docs/gate.md` what worked: the mount
  path, whether `run-blueprint` suffices without `server`, the SQLite caveats.
  Falsifier: if the mu-plugins mount cannot be made to load, the plan falls back to
  `wp-env` (Docker, MySQL) and says so; B02 onward then target wp-env.
  (files: docs/gate.md, blueprint.json)
- [ ] B02 [Tier A] `bin/playground-gate.sh` + `composer gate:wp` in CORE. Assertions as
  `runPHP` steps, each printing `ok:` or `FAIL:` and the script failing on any `FAIL:`:
  boot without notices; a declared model registers its meta; `ntdst_rest('ntdst-gate/v1')
  ->get('/ping')` answers 200 through `rest_do_request` and 401 anonymously;
  the 5.1.1 case, a `json` field leaf with `\n` reads back with `\n`; A's ability appears in
  `wp_get_abilities()` and executes. (R6: not in `gate` yet.)
  (files: bin/playground-gate.sh, blueprint.json, composer.json, docs/gate.md)
- [ ] B03 [Tier A] The same in BASELINE: mount `vendor/netdust/ntdst-core` and `.`,
  loader requires both, assertions: six modules report in `ntdst/baseline/booted`; a
  response carries the security headers; `/wp-json/wp/v2/users` is 404 for anonymous;
  `wp_head` output has no emoji script and no generator.
  (files: bin/playground-gate.sh, blueprint.json, composer.json)
- [ ] B04 [Tier B] Move, do not copy: list the Brain Monkey tests in each repo whose
  mocked WordPress return value is itself the thing under test (`sanitize_*`,
  `register_post_meta` re-sanitize, REST schema null-read). Each gets a `runPHP` twin in
  the Blueprint; the mock test stays only if it also pins core logic. The list is a task
  file, not a judgement made in the commit.
  (files: docs/gate.md, tests/, blueprint.json)
- [ ] B05 [Tier B] netdust-wp `wp-testing` SKILL: the package recipe (B01's findings),
  the SQLite line ("meta_query and collation stay on DDEV"), and the login step for a
  package shake-out. The sentence "Playground MAY be the browser" becomes "is the runtime;
  Playwright is the browser".
  (files: netdust-plugins/plugins/netdust-wp/skills/wp-testing/SKILL.md)

---

## Cluster C — BASELINE: the hardening and cleanup pass (2.22.0, additive)

Stakes: high on the security rows (SecurityService is INV-4's owner); standard on cleanup.

Admission: every row below passes the five questions on paper. Question 1 (two sites want
the identical behaviour) is asserted per row in the spec with two site names, by Stefan,
before the task runs. A row that cannot name two sites is dropped, not deferred.

What baseline already has (so nothing below duplicates it): xmlrpc off + direct block,
file editor off, user enumeration (users REST routes + author archive probe), media
enumeration (media REST routes + attachment probe, anonymous), login limiter via
`NTDST_RateLimiter`, generic login errors, security headers, HSTS, CSP, emojis, embeds,
head links, generator, version strings, dashicons, jquery, block styles, global styles.

| Row | Module | Switch (default per R5) | Source | Note |
|---|---|---|---|---|
| C1 | security | `close_application_password_flow` → ON | gds | `wp_is_application_passwords_available` false for < `manage_options`; `/wp-admin/authorize-application.php` 403 |
| C2 | security | `revoke_sessions_after_reset` → ON | gds | on `after_password_reset` and `profile_update` with a password: destroy other sessions, delete application passwords |
| C3 | security | `disable_rest_jsonp` → ON | gds | `rest_jsonp_enabled` false |
| C4 | security | `close_pingbacks` → ON | headache | `pings_open` false, `X-Pingback` header gone, `pingback.ping` XML-RPC method unset (belt for sites that re-enable xmlrpc) |
| C5 | security | `upload_types_by_role` → OFF | gds | PDF/SVG/EPS/HEIC/TIFF/macro-Office only for `edit_others_posts`+; a site turns it on |
| C6 | security | `min_password_length` → OFF (value 12 when on) | gds | server-side on `user_profile_update_errors` and `validate_password_reset` |
| C7 | security | `pin_default_role` → ON | gds | `default_role` forced to `subscriber` via `pre_option_default_role` |
| C8 | security | `block_htaccess_rewrite` → ON | gds | `flush_rewrite_rules_hard` false |
| C9 | head_cleanup | `disable_font_library` → ON | headache | `font_library_enabled` false |
| C10 | head_cleanup | `disable_auto_sizes` → ON | headache | `wp_img_tag_add_auto_sizes` false |
| C11 | security | `attachment_pages_404` → OFF | headache | today the probe is anonymous-only; this is for everyone, plus `wp_unique_post_slug` → UUID for attachments. A site with a gallery that links attachment pages must stay off |
| C12 | seo | verify, no code unless missing | headache, WordPlate | noindex on non-production: check `SeoService` reads `WP_ENV`; if it does not, one row |

- [ ] C01 [Tier A] Rows C1–C4, C7, C8 in `SecurityService` (one method per row, one
  `add_*` per method, registered under the switch, listed in `DEFAULTS` with a comment in
  the file's existing voice). INV-4 holds: nothing counts logins outside the limiter.
  (files: services/SecurityService.php, tests/Unit/BaselineSecurityHardeningTest.php)
  Unit test: per row, switch on → the hook is mounted and the filter answers as the table
  says; switch off → not mounted. Brain Monkey.
- [ ] C02 [Tier A] Rows C5, C6, C11 (OFF by default) with the same shape; their README
  paragraph says what a site notices when it turns them on.
  (files: services/SecurityService.php, tests/Unit/BaselineSecurityHardeningTest.php, README.md)
- [ ] C03 [Tier B] Rows C9, C10 in `HeadCleanupService`; C12 verified and recorded.
  (files: services/HeadCleanupService.php, services/SeoService.php, tests/Unit/)
- [ ] C04 [Tier B] README config table, `Version: 2.22.0`, `bin/check-invariants.sh` still
  green; netdust-wp `references/baseline.md` gains the twelve switches (D05).
  (files: README.md, ntdst-baseline.php, netdust-plugins/.../references/baseline.md)
- [ ] C05 [Tier B] Playground assertions for C1, C3, C7 added to B03's blueprint once B
  exists; until then the Brain Monkey tests are the proof.

Explicitly not admitted: removing user roles (headache) fails question 2; forced 2FA
(gds) is product; disabling the REST API (lumbermill) contradicts INV-2 of core; JPEG
quality 100 (headache) is a taste.

---

## Cluster D — netdust-wp 1.4.0: upstream skills and the harness follow-through

Stakes: standard.

- [ ] D01 [Tier B] `bin/wp-upstream-skills.sh`: `PIN=eff3785fc28c4380d172094518c66a6a997c95d4`
  (trunk, 2026-10-28), `SKILLS_CLI_VERSION=1.7.4`, `SKILLS` += `wp-abilities-api
  wp-abilities-audit wp-abilities-verify blueprint wp-playground`. Run `--check` and the
  bash test. Read the five new SKILL.md files once and note in `lessons.md` anything that
  contradicts `ntdst-framework` (the audit skill proposes `wp_register_ability()` calls;
  on a netdust project the answer is the route option, never the call).
  (files: plugins/netdust-wp/bin/wp-upstream-skills.sh, tests/, skills/ntdst-framework/lessons.md)
- [ ] D02 [Tier B] `ntdst-framework` SKILL + `references/traps.md`: the `ability` option,
  the three exposure spellings, "private by default", the write-verb annotation rule,
  "the ability permission is the route's, the limiter charges once", and the trap: a
  declaration hooked after `wp_abilities_api_init` fired registers nothing on < 7.2.
  (files: skills/ntdst-framework/SKILL.md, references/traps.md)
- [ ] D03 [Tier B] `ntdst-patterns` golden path `content-type-feature.md`: the list route
  gains its `ability` block as the worked example.
  (files: skills/ntdst-patterns/golden-paths/content-type-feature.md)
- [ ] D04 [Tier A] `ntdst-drift-reviewer` Part 2 check #16: `wp_register_ability(` or
  `*AbilityRegistrar` in consumer code is a bypass of INV-11; the fix is the route
  option. Part 1 picks INV-11 up by itself once core ships it (that is the point of
  parsing the vendored doc).
  (files: agents/ntdst-drift-reviewer.md)
- [ ] D05 [Tier B] `references/baseline.md` → 2.22.0 switches (from C04).
- [ ] D06 [Tier B] netdust-gates `policy/wordpress.md` pack: one Global Constraint, "a
  route an agent will operate declares `ability`; `wp-abilities-verify` runs in the
  feature review on a branch that touches routes".
  (files: netdust-gates/skills/policy/wordpress.md)
- [ ] D07 [Tier B] plugin.json 1.4.0 with the changelog line; `./scripts/sync.sh`.

---

## Cluster E — ntdst-yootheme: three directions before the first section

Stakes: low. Conditional: it applies only when there is no Figma file.

- [ ] E01 [Tier B] `references/workflow.md` §0 gains "When there is no design": before
  §1, write three one-paragraph design directions (type pairing, palette as five tokens,
  density, one reference site each), render each as a single hero section on the test
  page from `sections/hero-text.json` with the tokens applied, and stop for the client's
  pick. The pick becomes the `@prj-*` token block of §1. With a Figma file this section is
  skipped, by name.
  (files: skills/ntdst-yootheme/references/workflow.md, lessons.md)

---

## Loop budget

A: 6 tasks + threat model + plan review + one fix round ≈ 9. B: 5 + the spike ≈ 7.
C: 5 + plan review ≈ 7. D: 7 ≈ 4 (small). E: 1. Total ≈ 28 iterations across four repos.

## What is deliberately not in this plan

- Shipping the MCP Adapter from baseline (one consumer).
- inpsyde's ExtendingModule idea for the container (no consumer).
- Admin columns and filters in the Data layer after Extended CPTs (no consumer asked).
- Timber, WordPlate, Studio: reference only.
