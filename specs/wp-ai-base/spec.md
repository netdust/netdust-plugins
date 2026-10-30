# Spec — wp-ai-base: the base that AI can operate, proven on real WordPress

**Parent spec** of seven plans in four repos. No plan lives beside this file; each plan is
`specs/<feature>/plan.md` in its own repo, its `**Spec:**` header naming this file by repo
path (`netdust-plugins/specs/wp-ai-base/spec.md`).

**Repos:** `ntdst-core` 5.4.1 → 5.5.0 · `ntdst-baseline` 2.21.3 → 2.22.0 ·
`netdust-plugins` (`netdust-wp` 1.3.2 → 1.4.0, `netdust-gates` 0.13.0 → 0.13.1) ·
`netdust/wp-starter`.
**Provenance:** the 2026-10-28 cloud session's research (`plans/2026-10-28-wp-ai-landscape.md`)
and draft (`plans/2026-10-28-abilities-hardening-gate-plan.md`); this spec is the laptop
session of the same day, Stefan steering. The draft is the brief; this file is the authority.
The draft's Cluster B (a Playground gate) is replaced here, twice over: first by the testbed
the draft did not know about, then — Stefan's call — by the gate itself.
**Approved:** Stefan, 2026-10-28. **Tracked in netdust-studio:** project `wp-ai-base` (#4),
one feature per plan (#4–#10); a session moves a feature's `fase`, `laatste_stap` and
`volgende_stap` at every stop it passes.

## Problem / why

Thirteen sites pin ntdst-core. The research compared the stack against everything public
with the same philosophy and found two gaps the packages can close and nobody else has:

- *"Real-WordPress tests. gds runs PHPUnit against a real install plus Playwright. Mantle
  ships a testkit. Your packages are Brain Monkey only."* — the packages prove themselves
  only against mocked WordPress; a `sanitize_*` mock returning what the test expects is not a
  proof. Sites are better off: every scaffolded site is born with wp-starter's gate (wp-phpunit
  on DDEV, Playwright). A package is not a site, so it has no WordPress around it to run that
  gate — which is why a session on 2026-10-19 built `~/Sites/ntdst-testbed`, a shared host
  that swaps a package's working copy in; nobody designed it as the package leg and the
  harness never mentions it. Stefan: *"i feel my testing framework is on 2 legs, something is
  off..."* · *"i don't know what testbed is... if we use it, wordpress and all packages must
  always be latest"* · *"can't gate contain a complete deep wordpress testing system?"* — it
  already does; the package only has to host it. *"ok, the first then"*: each package adopts
  the gate.
- *"The official AI surface. Zero mentions of Abilities, MCP Adapter or Blueprints across all
  three repos."* — WordPress standardised how an agent operates a site (Abilities API in core
  since 6.9, MCP Adapter). Stride hand-rolls two ability registrars; nothing in core,
  baseline or the harness knows the surface exists.

Stefan: *"goal is to improve quality of all projects and integrate AI better"* · *"all my
websites yes, i will update core and baseline when i work on the projects again, new projects
ofcourse use latest"* · on the research's five moves, *"all seem good"* · *"does the plan take
into account that i also have a wp-starter repo? this is where the whole testing frameworks
are etc"*.

## Goals

1. Every netdust site is an MCP target through the routes it already has, with zero site code
   beyond one option per route.
2. Both packages prove themselves on a real WordPress with the one gate sites already stand
   on, always against the latest WordPress and the latest of each other.
3. Baseline closes the hardening and cleanup rows the public checklists (gds, headache) have
   and it lacks.
4. The harness knows all of it: the upstream skills, the framework rule, the drift check, the
   constraints pack, the gate's package shape, the starter's example tests.

## Non-goals

- A fleet rollout. Sites move to 5.5 / 2.22 when Stefan next works on them; new sites get both
  at `"*"` from the scaffold (`netdust-wp-manager/scripts/scaffold-meta.sh:281-303`).
- Shipping the MCP Adapter from baseline or the starter (one consumer today).
- Browser clients (Claude.ai, ChatGPT) connecting over OAuth 2.1 — deferred until WordPress
  7.2 shows whether core ships an OAuth server.
- "A client edits YOOtheme texts by chat" — a later, consumer-named feature on top of R1.
- Playground, Blueprints, wp-env, and the `blueprint` / `wp-playground` upstream skills.
- Building E (the YOOtheme directions) in this spec's plans — Decision 8; it is a Studio task
  on the `ntdst-yootheme` skill, after that skill is back under its load budget.
- Moving atelier and studio-plugin off the testbed. They adopt the gate the same way when
  next touched; the testbed retires then. Named here so it is a decision, not an omission.
- inpsyde's ExtendingModule, Extended-CPTs-style admin columns, Timber, WordPlate, Studio.

## Anti-goals

- A second door: any `wp_register_ability()` outside `api/Rest.php`, in any repo.
- A second test system. One gate, one home (wp-starter's `gate/`, INV-1 of
  netdust-wp-manager), two shapes: site and package. No shared host, no Playground, no wp-env.
- A package gate pinned behind the newest WordPress or the newest neighbour.
- A baseline switch a site can notice, ON by default.

## Requirements

### Core — an ability is the shadow of a route

**R1 — The `ability` option.** A route declared through `ntdst_rest()` with an `ability`
option is also a WordPress ability. Executing the ability dispatches the route through
`rest_do_request()`, so the route's permission callback, the limiter charge and the response
shaping run once, in the one place they already run. Observable on a WP 7.0 site with the MCP
Adapter: `wp_get_abilities()` lists `stride-v1/list-registrations` after Stride declares it;
`wp mcp-adapter` over STDIO answers `discover-abilities` with the same name and schema; one
`rest_do_request()` per execution, the limiter transient incremented once.
*Source: research move B ("highest leverage item"), Stefan "all seem good"; "all my websites
yes" to "every netdust site is an MCP target through the routes it already has".*

**R2 — Declared is exposed.** WordPress has no anonymous discovery: its abilities endpoints
require `read` and list only abilities with `meta.show_in_rest`; the MCP Adapter serves only
`meta.mcp.public`; 7.1's `meta.public` merely seeds `show_in_rest`; and Stride's in-process
consumer (ntdst-assistant's `AbilityBridge`) filters on `show_in_rest` too. A "private"
ability is therefore reachable by nobody. So the `ability` block is the opt-in: the bridge
writes all three spellings `true`, with no `public` option, and 6.9, 7.0, 7.1 and the
Adapter answer the same. Authorization is the route's permission, always; discovery needs a
logged-in user with `read`.
*Source: the builder check of 2026-10-28 against the 6.9.4 and 7.1 source (the draft's
"private by default" described nothing WordPress does) — Decision 12.*

**R3 — Refuse rather than guess.** Through the existing `refuse()` path in `api/Rest.php`:
`name` matches `^[a-z0-9-]+$`; `label` and `description` are non-empty; a write verb carries
boolean `destructive` and `idempotent`; an `output_schema` exists from the route's `schema`
option or the ability's own; a duplicate `namespace/name` refuses. On WordPress < 6.9 the
option is inert with one `_doing_it_wrong` per declaration, debug only. The category is one
per REST namespace, derived (`stride/v1` → `stride-v1`), overridable by `category` in the
option.
*Source: Decisions 1–4 below.*

**R4 — The walk, not inline registration.** `wp_register_ability()` refuses calls before
`wp_abilities_api_init`, which fires lazily inside `WP_Abilities_Registry::get_instance()`.
So `registerOne()` records the declaration; core hooks `wp_abilities_api_categories_init`
and `wp_abilities_api_init` once at boot whenever `function_exists('wp_register_ability')`
— unconditionally, because the named consumer declares its routes inside `rest_api_init`
callbacks, which on a STDIO or admin request have not fired when the abilities hook fires
lazily, so the buffer is empty at hook time. The walk calls `rest_get_server()` first (fires
`rest_api_init`, fills the buffer), then registers each record; an empty buffer registers
nothing. Core mounting after `did_action('wp_abilities_api_init')` refuses loudly — the
trap R15 names for consumers holds for core too. `permission_callback` is the UNGUARDED
resolved permission (never the limiter guard, so discovery does not charge).
`execute_callback` returns the response's data (`get_data()`), never the
`WP_REST_Response`, which fails WordPress's output validation; a `WP_Error` keeps the REST
status. A `->public()` write cannot exist (INV-3), so no anonymous destructive ability can
either; a test pins it.
*Source: the draft's second look, item 1, corrected by the builder check (Stride's
`AdminAPIController.php:47`, `PartnerAPIController.php:43`) — Decision 13.*

**R5 — INV-11.** *An ability is the shadow of a route.* Convergence point `api/Rest.php`.
Bypass smell: `wp_register_ability(` or `wp_register_ability_category(` outside it; an
`execute_callback` that is not a REST dispatch; a consumer class named `*AbilityRegistrar`.
Mechanical check, run verbatim at the commit and added to `bin/guard.sh`:
`grep -rn "wp_register_ability" --include=*.php . | grep -vE "^(\./)?api/Rest\.php|(^|/)vendor/|(^|/)tests/" | grep -vE "^[^:]+:[0-9]+: *(\*|//|/\*)"` → EMPTY.
`docs/philosophy.md` §1 gains one sentence: an ability is a route's shadow; core registers no
ability of its own.
*Source: core's own rule (invariants enforced by grep); invented — approved with this spec.*

**R6 — Stride is the proof, never merged by this work.** A Stride branch
`chore/abilities-bridge` deletes `Modules/Assistant/ReadAbilityRegistrar.php` and
`WriteAbilityRegistrar.php`, moves each ability onto its route's `ability` option, and runs
the drift reviewer and `wp-abilities-verify`. The diff is the evidence the option covers a
real consumer. The bar: Stride's twelve abilities are LLM-shaped and call services directly;
its routes are admin-table-shaped; three (`get-stats`, `get-attendance`, `get-enrollments`)
have no route. The proof is every ability that has a route, moved, with ntdst-assistant still
working on the branch for those; the three without a route and every shape mismatch are
findings in plan 3's review, not Stride routes added by this work. A second door is never the
answer. The MCP Adapter is required on that branch's DDEV for the R1 observable (no site has
it today).
*Source: core's brake — a feature enters only with a named consumer; Stride named in the
research; the bar is Decision 14.*

**R7 — Threat model before the tasks.** `docs/threat-models/2026-10-abilities-bridge.md`:
an MCP client is a logged-in user, the application password is the credential, the route's
capability is the floor; discovery needs `read` and charges nothing; baseline's C1 decides
who may hold an application password at all (administrators by default — R12); prompt
injection through ability descriptions is out of scope for core and named as such. Its
mitigations become Test map rows; `security-sentinel` joins the review.
*Source: `netdust-gates:policy` — a new public surface is a security boundary.*

### The gate — a package shape, and both packages on it

**R8 — The gate grows a package shape.** wp-starter's `gate/` gains what a package needs to
host its own WordPress, beside the site shape it has: `roots/wordpress`, `roots/wp-config`
and `wp-phpunit/wp-phpunit` in `require-dev` with the installer paths that put WordPress at
`web/wp`; a `web/wp-config.php` + `config/application.php` reading DDEV's environment
(bedrock-lite — the testbed's `config/` and `web/` are the worked instance to lift); a
committed `web/app/mu-plugins/<package>loader.php` that requires the repo root's main file
instead of a composer-installed copy; `web/` otherwise gitignored; `.gitattributes`
export-ignoring everything the gate added, so a site installing the package receives none of
it. The scaffold renders it with the same two tokens (`{{GATE_CONTENT_DIR}}`,
`{{GATE_WP_DIR}}`). One home: a package never patches its gate by hand (INV-1).
*Source: "can't gate contain a complete deep wordpress testing system?" · "ok, the first
then"; the file list is invented — approved with this spec.*

**R9 — Latest, or red.** A gate tier `deps:latest`, in both shapes' `bin/gate.sh` before the
integration tier: red when `roots/wordpress`, `wp-phpunit/wp-phpunit` or any `netdust/*`
dependency in the lock is behind its newest tag; the fix is `composer update <those>`
committed. The package under test is the working copy; its neighbour (core, for baseline) is
`"*"` in `require-dev`. A red caused by a neighbour moving is a finding, not noise.
*Source: "if we use it, wordpress and all packages must always be latest" — carried over to
the gate; the tier shape is invented — approved with this spec.*

**R10 — `tests/Integration/` in each package, run by `composer gate`.** wp-phpunit tests
(`WP_UnitTestCase`, the same class sites use) on the package's own DDEV project. Core
asserts: boot without notices; a declared model registers its meta and a round trip persists
prefixed meta; `ntdst_rest('ntdst-gate/v1')->get('/ping')` answers 200 through
`rest_do_request` and 401 anonymously; the 5.1.1 case — a `json` field leaf with `\n` reads
back with `\n`; R1's ability appears in `wp_get_abilities()` and executes through one
dispatch. Baseline asserts: the modules report in `ntdst/baseline/booted`;
`/wp-json/wp/v2/users` is 404 anonymously; `wp_head` has no emoji script and no generator;
each R12 switch answers as its row says; and, as Playwright e2e on the wire, a response
carries the security headers and a failed login shows the generic error. Falsifier:
`sanitize_text_field()` in place of `sanitize_textarea_field()` in `FieldTypes.php` turns the
textarea test red. `composer gate` exit 0 is the whole Close; no second command.
*Source: "Real-WordPress tests … Your packages are Brain Monkey only. Cluster B."*

**R11 — Move, do not copy.** Each package lists the Brain Monkey tests whose mocked WordPress
return value is itself the thing under test (`sanitize_*`, `register_post_meta`
re-sanitise, REST schema null-read). Each gets a twin in `tests/Integration`; the mock test
stays only if it also pins core logic. The list is a task file, not a judgement made in the
commit.
*Source: the research's reading of gds (real-WP PHPUnit); invented — approved with this spec.*

### Baseline — the hardening and cleanup pass

**R12 — The admitted rows, all ON by default.** One method per row in the owning service,
one `add_*` per method, registered under its switch, listed in `DEFAULTS` in the file's
existing voice. INV-4 holds: nothing counts logins outside the limiter.

| Row | Service | Switch | What it does |
|---|---|---|---|
| C1 | security | `application_passwords_capability` → `manage_options` | `wp_is_application_passwords_available` false for users without the capability; `authorize-application.php` 501. The value is the capability; a site onboarding an editor as an MCP client lowers it (`edit_posts`); `false` turns the row off. Default: administrators only |
| C2 | security | `revoke_sessions_after_reset` | on `after_password_reset` and a `profile_update` carrying a password: destroy other sessions, delete application passwords |
| C3 | security | `disable_rest_jsonp` | `rest_jsonp_enabled` false |
| C4 | security | `close_pingbacks` | `pings_open` false, `X-Pingback` header gone, `pingback.ping` unset from XML-RPC |
| C7 | security | `pin_default_role` | `default_role` forced to `subscriber` via `pre_option_default_role` |
| C8 | security | `block_htaccess_rewrite` | `flush_rewrite_rules_hard` false |
| C9 | admin_ui | `disable_font_library` | `block_editor_settings_all` → `fontLibraryEnabled = false`, and the font-library REST routes unregistered. Not `head_cleanup`: that service returns on `is_admin()` before reading config, and the Font Library is an editor surface; `font_library_enabled` (the draft's filter) exists in no WordPress |
| C10 | head_cleanup | `disable_auto_sizes` | `wp_img_tag_add_auto_sizes` false |

C12 — no row: every Bedrock site carries `roots/bedrock-disallow-indexing` (`blog_public` 0
off production) and `SeoService` already respects `blog_public`; a row would be a second
home. The verification is recorded in plan 4. Already in baseline, so not here: xmlrpc, file editor, user and media enumeration, the
login limiter, generic login errors, headers, HSTS, CSP, emojis, embeds, head links,
generator, version strings, dashicons, jquery, block and global styles.
*Source: research move C and "all seem good"; the two-sites admission is "every site" for
rows with no visible effect (Decision 5).*

**R13 — Dropped, not deferred.** Upload MIME by role (C5), minimum password length (C6) and
attachment pages 404 for everyone (C11) are out: the admission rule needs two named sites
wanting the identical behaviour, and none were named. Also not admitted: removing roles
(headache), forced 2FA (gds), disabling the REST API (lumbermill), JPEG quality 100.
*Source: baseline's five questions; the rows were put to Stefan twice on 2026-10-28 with no
sites named — Decision 7, approved with this spec.*

### Harness — netdust-wp 1.4.0, netdust-gates 0.13.1

**R14 — Upstream skills.** `bin/wp-upstream-skills.sh` pins trunk
`eff3785fc28c4380d172094518c66a6a997c95d4` (2026-10-28; verify on the day) and `skills`
CLI 1.7.4; `SKILLS` gains `wp-abilities-api wp-abilities-audit wp-abilities-verify`. The
three new SKILL.md files are read once; anything contradicting `ntdst-framework` lands in its
`lessons.md` — the audit skill proposes bare `wp_register_ability()` calls; on a netdust
project the answer is the route option.
*Source: research move A; "The official AI surface … Clusters A and D."*

**R15 — The framework knows the option.** `ntdst-framework` SKILL and `references/traps.md`:
the `ability` option, declared is exposed (the three spellings written for you), the
write-verb annotation rule, "the permission is the route's, the limiter charges once", the
return is the response's data, and the trap: a declaration after `wp_abilities_api_init`
fired registers nothing. `ntdst-patterns`' `golden-paths/content-type-feature.md` list route
gains its `ability` block. `references/baseline.md` gains the eight switches of R12 and its
stale "Seven modules" (baseline `origin/main` has eleven) is corrected from the source while
there. Deferred (Decision 8): `ntdst-yootheme`'s `references/workflow.md` gains §0 "When
there is no design" — three one-paragraph directions (type pairing, five palette tokens,
density, one reference site each), each rendered as one hero section from
`sections/hero-text.json`, stop for the client's pick; skipped by name when a Figma file
exists — with the next change to that skill, which brings it under its load budget first.
*Source: research moves A and D; the YOOtheme step from create-wp-site ("worth lifting").*

**R16 — The drift check and the pack line.** `ntdst-drift-reviewer` Part 2 gains check #16:
`wp_register_ability(` or `*AbilityRegistrar` in consumer code is a bypass of INV-11; the
fix is the route option (Part 1 picks INV-11 up from the vendored doc once core ships it).
`netdust-gates/skills/policy/wordpress.md` gains one Global Constraint: a route an agent will
operate declares `ability`; the task that touches such a route runs the upstream
`wp-abilities-verify` skill in runtime mode on its own DDEV and quotes its report in the task
report, where its reviewer reads it — as it reads every pack line's evidence; the headless
review reads code, plan and spec (Decision 17). The skill is run as `ntdst-framework` says:
its static inventory is the `'ability' =>` grep (its own `wp_register_ability(` grep is the
call INV-11 forbids), its runtime list is `wp_get_abilities()` over `ddev wp` filtered on the
namespace slug, and its check 1 then means what it says — Source+Runtime is PASS, Source-only
is the declaration not reaching the registry, Runtime-only is a hand-registered ability.
*Source: the growth rule (an incident lands as a line in a constraints pack); invented —
approved with this spec.*

**R17 — One gate, two shapes.** `wp-testing` SKILL says it in one place: the gate is
wp-starter's `gate/` for sites and packages alike; a package hosts its own WordPress through
the package shape (R8) and its `composer gate` runs every tier, integration included, on its
own DDEV project; `deps:latest` keeps it on the newest WordPress and neighbours. A package
worktree is its own DDEV project, as the two-session rule already says. Named as not used:
Playground, Blueprints, wp-env, and a shared test site (the testbed, retiring). The pack's
trigger in `netdust-gates:policy` gains the package case: a `composer.json` of type
`wordpress-muplugin` is a WordPress project for the Global Constraints.
*Source: "does the plan take into account that i also have a wp-starter repo? this is where
the whole testing frameworks are etc"; "i feel my testing framework is on 2 legs"; "can't gate
contain a complete deep wordpress testing system?".*

### wp-starter — every new site is born with the proof

**R18 — The abilities example.** `gate/tests/Integration/AbilityShadowTest.php` beside
`DataLayerRoundTripTest.php`: a route declared with `ability` in the test bootstrap is listed
by `wp_get_abilities()` and executing it returns the route's data; executing it as a user
without the route's capability is refused by the route's permission, not by anything the
ability adds. The existing example tests are re-checked against core 5.5
(`netdust-wp/memory/lessons.md:75` — two already drifted once). The README's `^2.2` / `^1.0`
example block is corrected to what the scaffold writes.
*Source: the same quote as R17; invented in the detail — approved with this spec.*

## Constraints

- Core's philosophy: wrap WordPress, never replace it; a feature enters only with a named
  consumer; invariants are enforced by grep. Baseline's five-question admission; zero site
  values.
- `wp_register_ability()` is callable only during `wp_abilities_api_init`, which fires lazily
  (R4). Exposure has three spellings across 6.9 / 7.0 / 7.1 (R2). Both facts are from the
  draft's second look and are verified by the plan reviewer against the WordPress source on
  the day.
- Both packages commit `composer.lock` and export-ignore `tests/` already; core's
  `require-dev` is PHPUnit, Brain Monkey and PHPCS. The gate has one home — a gate change
  lands in wp-starter's `gate/`, never in a single package (netdust-wp-manager INV-1); an
  existing project adopts it by hand (`/setup-tests`).
- `netdust-gates:policy`: one plan = one `feature/<feature>` branch = one promotable unit; no
  plan declares another as a dependency. The package repos carry no `site.yml`; their gate is
  `composer gate` and the review is `/feature-review`.
- The policy skill's budget is 150 lines; it is 152 on `main` since the devops commit
  `59f6785` landed on 2026-10-29, so the budget test is red there. Plan 1's Task 2 trims
  it while editing the file (reviewer's ruling at the coder start; the plan carries it).
  R17's trigger change rides inside the existing trigger lines, adding none. The
  pack (`wordpress.md`) is at 59 of 60: R16's constraint is one physical line, and the two
  lines a package cannot meet (`make gate`, `deploy.payload`) are reworded in place.
- `evals/yootheme-budget.sh` is over its 55,000-byte page-build load on `main` (55,738);
  `evals/version-anchor.sh` already reports two stale anchors and exits 1. Neither is
  re-anchored or trimmed here; a plan diffs their output, never claims their exit code.

## Approaches

**The cut**

1. **Seven plans, one branch each, under this parent spec** — *picked.* Each threat model stays
   on the surface it belongs to; core's new public surface is never reviewed in the same pass
   as a new test suite; each branch is one promotable unit. Cost: seven reviews, seven promotes.
2. **Three plans, one per repo.** Fewer branches, but core's plan outlives one context, mixes
   a security-boundary change with test scaffolding, and 5.5.0 carries two unrelated changes.
   Rejected.
3. **One cross-repo plan.** No branch can hold it. Rejected.

**The package runtime**

1. **The package hosts the gate** — *picked.* One system; packages born gated exactly like
   sites; a worktree has its own DDEV project; "latest" is Composer's job. Cost: the package
   shape in wp-starter (one plan) and about six dev-only files per package.
2. **A shared host** (the testbed). Already built, but one run at a time (`flock` — parallel
   plans collide), a mirror copy with caveats, 90 lines of bash, a third thing to know that
   nobody knew. Rejected: "on 2 legs".
3. **Playground + Blueprint** (the draft's Cluster B). SQLite, a Node dependency, assertions
   as `runPHP` strings, a spike just to mount an mu-plugin. Rejected.

Stefan picked cut 1 on 2026-10-28, runtime 1 ("ok, the first then") with the always-latest
rule.

## The cut

| # | Feature (branch) | Repo | Delivers | Order |
|---|---|---|---|---|
| 1 | `wp-ai-skills` | netdust-plugins | R14–R17 minus E (netdust-wp 1.4.0, netdust-gates 0.13.1) | first — its skills are the tools for 3 |
| 2 | `package-gate` | wp-starter | R8–R9 (the package shape, `deps:latest`) | with 1 |
| 3 | `abilities-bridge` | ntdst-core | R1–R7 (5.5.0) | with 4 |
| 4 | `hardening-2026-10` | ntdst-baseline | R12–R13 (2.22.0) | with 3 |
| 5 | `integration-suite` | ntdst-core | R10–R11, core half | after 2 and 3 are on main |
| 6 | `integration-suite` | ntdst-baseline | R10–R11, baseline half | after 2 and 4 are on main |
| 7 | `abilities-example` | wp-starter | R18 | after 3 is on main |

R15's `references/baseline.md` rows and R16's check #16 describe switches and an invariant that
land in plans 4 and 3; plan 1 writes them from this spec, and plan 3 / 4's reviews read them.
The order is a recommendation, not a dependency a plan declares.

## Decisions (mine; veto any)

| # | Decision | Why |
|---|---|---|
| 1 | A write verb's ability must declare `destructive` and `idempotent`; core refuses otherwise | Deriving from the verb is guessing; the audit skill and abilities-rest-adapter both refuse |
| 2 | `output_schema` comes from the route's `schema` or the option; absent, refuse | Pushes consumers to declare `schema`, which the REST surface should have had |
| 3 | On WordPress < 6.9: one `_doing_it_wrong` per declaration, debug only | Silent inert is the trap `traps.md` exists to list |
| 4 | Category derived from the namespace, overridable by `category` | One obvious default, one escape |
| 5 | Every admitted baseline row defaults ON | None has a visible site effect; a visible one was not admitted |
| 6 | `composer gate` runs every tier in the package, integration included; one command is the Close | The gate is one system; a second command is a second leg |
| 7 | C5, C6, C11 dropped | The admission rule; no sites named |
| 8 | E (YOOtheme directions) is deferred to the next `ntdst-yootheme` change, not built by plan 1 | The yootheme skill is already over its page-build load budget on `main`; adding to `workflow.md` means curating `lessons.md` first, which is that skill's own work (revised 2026-10-28 after the plan review) |
| 9 | This spec lives in netdust-plugins; plans point at it by repo path | The harness repo is the one place all four repos already refer to |
| 10 | The package shape is lifted from the testbed into wp-starter's `gate/`, then the testbed retires | INV-1: one home; the testbed is a worked instance, not a second home |
| 11 | "Always latest" is a red gate tier, not a `composer update` inside the gate | The packages commit their lock; a gate that rewrites the tree is not a gate |
| 12 | Declared is exposed; no `public` option | WordPress has no anonymous discovery and a non-`show_in_rest` ability is reachable by nobody; the block is the opt-in |
| 13 | Core hooks the abilities init unconditionally and fills the buffer inside the walk | The named consumer declares routes at `rest_api_init`, which has not fired on a STDIO or admin request |
| 14 | The Stride proof is "every ability with a route, moved"; the rest are findings | Adding Stride routes is Stride's feature work, not evidence for core |
| 15 | C1 is a capability value defaulting to `manage_options` | Administrators are MCP clients by default; a site lowers it the day an editor is one, and the threat model says so |
| 16 | C9 lives in `admin_ui` via `block_editor_settings_all`; C12 is no row | The draft's filter does not exist; `head_cleanup` is frontend-only; Bedrock already disallows indexing off production |
| 17 | `wp-abilities-verify` is run by the task that touches the route, on its own DDEV, with the `'ability' =>` grep as its static inventory; the quote goes in the task report, which the reviewer session reads; the headless review never runs it | `/feature-review` is headless on a detached checkout with no DDEV, reads code, plan and spec, and runtime mode executes write abilities; a task report is where every pack line's evidence already lives, and the reviewer session is its reader (plan reviews 2 and 3, 2026-10-28). Keeping the skill's source-vs-runtime check is what catches a declaration that never reaches the registry |

## Left to the builder

- The exact `input_schema` mapping from `args` (type, description, enum, default, required →
  properties + required) and the error mapping from a `WP_Error` response to the ability's
  return.
- The package shape's file names and how the scaffold selects it (a preset flag or a second
  folder); how `deps:latest` reads the newest tag (`composer outdated --direct` or the VCS).
- Test file names beyond those named here; changelog wording.
- Which Brain Monkey tests go on R11's list.
- netdust-gates' version line and `plugin.json` wording for two one-line pack changes.

## Out of scope

Everything under Non-goals. Also: the Stride branch of R6 is evidence, not a deliverable of
any plan here, and is never merged by this work.
