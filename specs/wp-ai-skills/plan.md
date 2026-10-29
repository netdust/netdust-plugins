# wp-ai-skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The harness knows the official WordPress AI surface and the one-gate rule — the three abilities skills installed at a verified pin, `ntdst-framework` teaching the `ability` route option, the drift reviewer catching a hand-registered ability, the WordPress pack asking for it, `wp-testing` saying a package hosts the gate itself — shipped as netdust-wp 1.4.0 and netdust-gates 0.13.1.

**Architecture:** Text and one bash script, in two plugins of this repo. Every behaviour-changing line ships with its proof: the bash test for the script, the python runner for the policy and pack, an eval case per skill lesson (with a baseline arm, so it discriminates), a read-only grep against a real site for the drift check. No WordPress runs here; nothing in this plan touches a security-boundary file, so there is no `## Threat model`.

**First working version:** Task 1 — `bash bin/wp-upstream-skills.sh --check` printing seven `present:` lines is the first thing Stefan can run.

**Tech Stack:** bash (`plugins/netdust-wp/tests/run.sh`), python 3 (`plugins/netdust-gates/tests/run.sh`, `evals/run-evals.py`), the `claude` CLI for evals, `npx skills@1.7.4`.

**Spec:** `specs/wp-ai-base/spec.md` — R14, R15 (minus the YOOtheme sentence, deferred by Decision 8 as revised), R16, R17. Nothing from R1–R13 or R18 is built here.

**Branch:** `feature/wp-ai-skills`, cut from `main` (`59f6785`, origin's tip on 2026-10-29) in its own worktree. First commits, in order: the research files (`git cherry-pick 1a2745f 4112f4b 2981293` from `ccr-38321f1f-9ivl0o`), `specs/wp-ai-base/spec.md`, this plan, `specs/wp-ai-skills/plan-review.md`. The devops commit `59f6785` landed on `main` after the review and put the policy skill at 152 lines; its trim is Task 2's (Global Constraints).

## Global Constraints

netdust-plugins carries no `site.yml` and no `roots/wordpress`; the WordPress pack does not apply. The spec's own:

- One gate, one home: nothing written here names Playground, Blueprints, wp-env or a shared test site except to say they are not used (spec anti-goals, R17).
- `plugins/netdust-gates/skills/policy/SKILL.md` stays under 150 lines. It is 152 on `main` since `59f6785` (the standing-OK wording at `:114-117` and `:145-146`), so `test_policy_skill` is red at this branch's root; Task 2, the first task that touches the plugin, brings it under 150 (Ruling, reviewer, 2026-10-29: the trim rides with the task that edits the file anyway — cost if wrong, a sentence of policy wording). `wordpress.md` at most 60. `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` exits 0 after every task that touches the plugin — the session env carries `NETDUST_GUARD_ASK=off` (`~/.claude/settings.json`), which `test_pretooluse_guard` reads as a waiver and fails on; with it unset the module is green on `main`.
- A skill text that changes behaviour ships an eval case the same commit — `evals/cases.json` (gates) or `evals/behavioral-lessons.json` (wp, with `baseline_ref`, `context_before`/`context_after`, `must_contain`/`must_not_contain`, or the runner skips it) — run when the `claude` CLI is present; a run that could not happen is reported as not run, never as a pass (`~/.claude/CLAUDE.md` §8). An agent's new mechanical check ships its executable run against a real site instead (Task 4).
- The wp correctness runner takes `[cases.json] [out.json]` and reads only `["cases"]`: a task runs only its own case through a scratch file holding `_readme` and that one case, with a scratch output path, so the tracked `evals/outputs/correctness-results.json` is never rewritten by this plan; the Close's scratch file holds both new cases.
- The upstream pin is a 40-hex commit fetched into the local clone; never a branch or tag name; verified against `origin/trunk` on the day it is written (R14).
- No live file names `netdust-agent`, `harnessed-development` or `wp-plan-requirements` (`tests/test-live-routing.sh`).
- Skills are contracts: cite the upstream skill, never restate it (`~/.claude/CLAUDE.md` Skill architecture).
- `evals/version-anchor.sh` already reports two stale anchors (core 5.2.0, baseline 2.3.0) and exits 1; re-anchoring is not in this spec. Every task that edits `ntdst-framework` diffs that output before and after: the same two lines, no new one. 5.5.0 behaviour is marked `(5.5.0)` in the text.
- Nothing lands in a live cache before the merge: `scripts/sync.sh` runs after Stefan's merge, never inside a task.
- Evidence: every task report quotes the command as run and its summary line.

## Review Focus

- **Boundary** — the pack at exactly 60 lines; the next one-line edit goes red. Pinned by row 2's python test; the plan review and the branch review read the count, not the prose.
- **Empty** — a `SKILLS` name absent at the pinned commit: the real `skills` CLI installs the matched subset, exits 0, and leaves a copy an earlier pin installed in place — so a post-add check is blind, and only a check at the source, before the add, can refuse. Row 1 adds it and its denial test, RED first.
- **Delivery seam** — the three new skills land in `~/.claude/skills/` by `--copy`; a changed pin must replace, not merge. Row 1's existing "changed pin: new content landed" case covers it; the task quotes the real `--check`.
- **Denied actor** — the drift check's grep must flag Stride's registrars, skip comments, and find nothing in a clean consumer. Row 4 runs it read-only against both.
- **Re-entry** — a package plan reading the pack must not inherit a site's `make gate` and `deploy.payload` lines it cannot meet. Row 2 rewords those two lines in place and the `wp-pack-on-muplugin-package` eval reads the result.

## Simplest design

The simplest change that meets R14 alone is Task 1 — a pin bump and three names. The plan carries R15–R17 because they are approved requirements, and because the research's own finding is that the harness never mentions the surface: a session that does not know the `ability` option hand-rolls `wp_register_ability()` exactly as Stride did, and the framework rule, the drift check and the pack line are what stop that recurring. The policy skill is 152 on `main` since `59f6785` and owes a three-line trim; Task 2 takes it with its trigger edit, since it edits the file anyway, while the package trigger itself widens inside its existing three lines. The YOOtheme directions (spec R15, E) are deferred: `evals/yootheme-budget.sh` is already over its 55,000-byte page-build load on `main` (55,738), and adding to `workflow.md` here would mean curating `lessons.md` as a side quest; E rides with the next `ntdst-yootheme` change, which must bring the skill under budget first (spec Decision 8, revised).

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| Upstream skills script | `bin/wp-upstream-skills.sh --check` | bash · `plugins/netdust-wp/tests/test-upstream-skills.sh` · `bash plugins/netdust-wp/tests/test-upstream-skills.sh`; the real install's `--check` | none |
| Policy: package trigger; pack: ability line, package wording | `netdust-gates:policy` and `wordpress.md` read by a session | python · `plugins/netdust-gates/tests/test_policy_skill.py` · `bash plugins/netdust-gates/tests/run.sh`; evals `wp-pack-on-muplugin-package`, `wp-route-declares-ability` (new) and `wp-feature-constraints`, `wp-constraints-carry-evidence` (regression — they read the two reworded lines) · `evals/cases.json` · `python3 plugins/netdust-gates/evals/run-evals.py <the four ids>` | none |
| Framework: the `ability` option | `ntdst-framework` SKILL, `traps.md`, golden path | eval `abilities-route-option` · `evals/behavioral-lessons.json` · `bash plugins/netdust-wp/evals/run-correctness-eval.sh <scratch one-case file> <scratch out>`; `bash plugins/netdust-wp/evals/version-anchor.sh` output diffed | none |
| Drift check #16 | `ntdst-drift-reviewer` Part 2 | the check's own pipeline, read-only on `~/Sites/stride/web/app/mu-plugins/stride-core` (17 hits, none a comment) and `~/Sites/laika/web/app/mu-plugins` (0) | none |
| wp-testing: one gate, two shapes | `wp-testing` SKILL | eval `package-gate-not-playground` · `evals/behavioral-lessons.json` · same runner, same scratch shape; `bash plugins/netdust-wp/tests/run.sh` | none |
| `references/baseline.md` | reference text | none — proven by review against spec R12; `version-anchor.sh` output diffed | none |
| Versions | `plugin.json` ×2, `.claude-plugin/marketplace.json` (both entries) | python · `plugins/netdust-gates/tests/test_plugin_manifest.py` · both plugins' `tests/run.sh` | none |

Nothing here is a browser or wire surface: the Close has no `/shakeout`; the evals are the behavioural proof.

---

### Task 1: Upstream skills — the pin, the three abilities skills, and a refusal the CLI lacks

**Files:**
- Modify: `plugins/netdust-wp/bin/wp-upstream-skills.sh:7-9` (keep the `PIN="${PIN-…}"` form — the test overrides through it) and `install()`
- Modify: `plugins/netdust-wp/tests/test-upstream-skills.sh:15` (fixture `SKILLS`), `:94` (the one count assertion), plus one new case; the stub `npx` at `:41` is unchanged
- Modify: `plugins/netdust-wp/CLAUDE.md` "Setup" paragraph (four names → seven, the new pin)
- Modify: `plugins/netdust-wp/skills/ntdst-framework/lessons.md` (one entry appended)

**Interfaces:**
- Produces: `SKILLS="wp-plugin-development wp-rest-api wp-wpcli-and-ops wp-phpstan wp-abilities-api wp-abilities-audit wp-abilities-verify"`; `PIN=eff3785fc28c4380d172094518c66a6a997c95d4`; `SKILLS_CLI_VERSION=1.7.4`. Task 3 cites `~/.claude/skills/wp-abilities-api/SKILL.md`; Task 2's pack line cites `wp-abilities-verify` in runtime mode.

- [ ] **Step 1: Verify the pin on the day**

Run: `git -C ~/.cache/netdust/wp-upstream-skills ls-remote origin trunk | cut -c1-40` and `npm view skills version`
Expected: `eff3785fc28c4380d172094518c66a6a997c95d4` and `1.7.4` (true on 2026-10-28). If trunk moved: use the newer sha, and confirm `git -C ~/.cache/netdust/wp-upstream-skills ls-tree --name-only <sha> skills/` still lists `wp-abilities-api`, `wp-abilities-audit`, `wp-abilities-verify`.

- [ ] **Step 2: The denial test, RED first — a skill name absent at the pin**

The real `skills` CLI (1.7.4) installs the names it finds, exits 0 when at least one matched, and leaves a copy an earlier pin installed untouched — so a check after the add is blind to exactly the pin-bump case (a skill dropped or renamed upstream). The refusal must read the source at the pin, before the add. In `test-upstream-skills.sh`: set the fixture `SKILLS` to the seven names, and add after the "changed pin" case: commit and push a fixture revision that deletes `skills/wp-abilities-audit`, run the install at that revision's sha as `PIN` while `$HOME` still holds the copy from the earlier install; assert exit 1, the stderr line `missing at pin: wp-abilities-audit`, and no new line in `$NPX_LOG`. The stub `npx` needs no change.

Run: `bash plugins/netdust-wp/tests/test-upstream-skills.sh`
Expected: six FAIL lines — three at `:68-70` (the unchanged script still installs four, so `wp-abilities-{api,audit,verify}` are missing) and the new case's three assertions (`install()` goes straight to the `npx` call: exit 0, no stderr message, a new `$NPX_LOG` line). The count at `:94` passes until Step 3: `--check` loops over the script's own `SKILLS`, still four.

- [ ] **Step 3: The script**

`bin/wp-upstream-skills.sh`: `PIN` → the verified sha with the comment `# trunk, 2026-10-28`; `SKILLS_CLI_VERSION=1.7.4  # npm view skills version, 2026-10-28`; `SKILLS` → the seven names. In `install()`, after the checkout and before the `run npx … add` line: for each name in `SKILLS`, `$CLONE/skills/$s/SKILL.md` must exist, else print `missing at pin: $s` to stderr and exit 1 (skipped under `--dry-run`, which never fetches).

`tests/test-upstream-skills.sh:94`: the count → `-eq 7`.

Run: `bash plugins/netdust-wp/tests/test-upstream-skills.sh`
Expected: `test-upstream-skills: all passed`

- [ ] **Step 4: The real install**

Run: `bash plugins/netdust-wp/bin/wp-upstream-skills.sh && bash plugins/netdust-wp/bin/wp-upstream-skills.sh --check`
Expected: `pin: eff3785…`, `skills-cli: 1.7.4`, seven `present:` lines, exit 0. Quote all of it. (This writes `~/.claude/skills/` ahead of the review — the script's purpose; a re-run at the old pin reverts it.)

- [ ] **Step 5: Read the three skills once; write the lesson**

Read `~/.claude/skills/wp-abilities-api/SKILL.md` (and its `references/plugin-family-patterns.md`, `shared-core-service.md`), `wp-abilities-audit/SKILL.md`, `wp-abilities-verify/SKILL.md`. Append to `skills/ntdst-framework/lessons.md`:

`## The upstream abilities skills, read on a netdust project` — one paragraph each:
- `wp-abilities-api`'s references propose an `Abilities_Registrar` class with its own `wp_register_ability()` calls; on a netdust project the answer is the `ability` option on the `ntdst_rest()` route (spec R1, INV-11 from core 5.5.0).
- `wp-abilities-audit` inventories REST controllers and refuses `__return_true` gates — kept; its grouping rule ("do not atomize one ability per HTTP method", collapsing N variants into one) contradicts one ability per route — on a netdust project the route is the unit, and a collapsed ability is a route the project has not written yet.
- `wp-abilities-verify` stops at "no abilities registered" in both modes when `wp_register_ability(` has zero hits in source (its Prerequisites and Failure modes), and its runtime enumeration filters names on the plugin slug — a route ability is named by its namespace (`stride-v1/…`) — so run as written it is blind on a netdust consumer in either mode. All three skills also require `wp-project-triage`, which is not installed; `site.yml` and the composer type stand in for it. How a netdust session uses the skill is the sentence Task 3 puts in `SKILL.md` (which sessions load; this journal is not).

Update `CLAUDE.md`'s Setup paragraph to name seven skills and the 2026-10-28 pin.

- [ ] **Step 6: Run the plugin's suite and commit**

Run: `bash plugins/netdust-wp/tests/run.sh`
Expected: `netdust-wp: all suites passed`

```bash
git add plugins/netdust-wp/bin/wp-upstream-skills.sh plugins/netdust-wp/tests/test-upstream-skills.sh plugins/netdust-wp/CLAUDE.md plugins/netdust-wp/skills/ntdst-framework/lessons.md
git commit -m "wp(upstream): pin eff3785 (2026-10-28), skills CLI 1.7.4, the three abilities skills; a name missing at the pin is refused before the add"
```

---

### Task 2: The policy's package trigger and the pack's ability line

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md:68-70` (the trigger, inside its three lines)
- Modify: `plugins/netdust-gates/skills/policy/wordpress.md:28, 33-36` (two lines reworded in place) and one line inserted after `:36`
- Modify: `plugins/netdust-gates/evals/cases.json` (two cases appended)
- Test: `plugins/netdust-gates/tests/test_policy_skill.py` (existing, unchanged)

**Interfaces:**
- Consumes: Task 3 Step 2's third bullet — how `ntdst-framework` says the verify skill is run (the pack cites it, never restates it). Between the two commits the citation points at a sentence not yet written; harmless on one branch reviewed whole.
- Produces: the trigger sentence the spec's package plans rely on — "a `composer.json` of type `wordpress-muplugin` is a WordPress project for the Global Constraints".

- [ ] **Step 1: See the green, and the eval's RED**

Run: `bash plugins/netdust-gates/tests/run.sh test_policy_skill.py`
Expected: `FAIL policy: under 150 lines (got 152)` — the pre-existing red from `59f6785` (Global Constraints) — and every other line pass.

Append the two cases of Step 4 to `cases.json` first, then run `python3 plugins/netdust-gates/evals/run-evals.py wp-pack-on-muplugin-package wp-route-declares-ability` against the unedited policy and pack.
Expected: both FAIL — the plan written for a package without `site.yml` carries no pack lines, and no pack line yet says `ability`. If the first passes anyway, the model already reads `wordpress-muplugin` as WordPress under the old trigger; then the case's prompt or demo spec needs sharpening (its `composer gate` expect is already in) before it discriminates. Without the `claude` CLI: report not run.

- [ ] **Step 2: Widen the trigger inside its three lines**

`SKILL.md:68-70` becomes: `- **Global Constraints** — on a WordPress project (a `site.yml` with `structure:`, `roots/wordpress` in `composer.json`, or a `composer.json` of type `wordpress-muplugin`) copy the Global Constraints of `wordpress.md`, beside this file, verbatim — lines and red flags — then the spec's own. Other stacks: the spec's own until a pack exists.` — rewrapped to three lines. Then the trim: the Stops paragraph's standing-OK clause (`:114-117`, from `59f6785`) and Close step 5's "or run under his standing OK for the staging verbs" (`:145-146`) compress to the fewest lines that keep the six verbs (`promote`, `unpromote`, `deploy env=staging`, `e2e`, `smoke`, `review`), `NETDUST_AGENT_OK=1` (the devops skill owns the rule; the policy names it once) and "`ship` and production stay his". `test_policy_skill.py` reads the Stops section for its needles (`:57-60`), so the proof is the test, not `wc` alone.

Run: `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh test_policy_skill.py`
Expected: `pass policy: under 150 lines (got 149)` or fewer, and every other line pass.

- [ ] **Step 3: The pack — two lines reworded, one line added, 60 in all**

`wordpress.md:28`: "the close is `make gate`" → "the close is `make gate` (a package: `composer gate`)". Lines 33–36, the "Local and ship" bullet: append "A package ships by tag: no payload, no deploy line." inside the existing wrap (reflow the bullet; its line count stays four).

Insert after `:36`, one physical line:
`- Abilities: a route an agent will operate declares `ability` (`netdust-wp:ntdst-framework`, core 5.5.0); the task that touches such a route runs the upstream `wp-abilities-verify` skill on its own DDEV, in runtime mode as `ntdst-framework` reads it, and quotes its report in the task report — its reviewer reads the quote there, the way it reads every line's evidence, and never runs it (the headless review reads code, plan and spec; runtime mode executes write abilities); a hand-registered ability is drift check #16.`

`/feature-review` stays untouched: evidence in a task report is read by the reviewer session, as for every other pack line; the headless pass reads code, plan and spec (spec Decision 17).

Run: `bash plugins/netdust-gates/tests/run.sh && wc -l plugins/netdust-gates/skills/policy/wordpress.md`
Expected: all green; `pack: short, …` pass; `60 plugins/netdust-gates/skills/policy/wordpress.md`.

- [ ] **Step 4: The two eval cases**

In the shape of `wp-constraints-carry-evidence`:

- `wp-pack-on-muplugin-package` — files: `composer.json` = `{"name": "netdust/ntdst-demo", "type": "wordpress-muplugin"}`, no `site.yml`, a two-requirement spec at `specs/demo/spec.md`; prompt: write the plan; expect in the plan's `## Global Constraints`: `No quote, not met`, `Admin-only screen, so no nonce`, and `composer gate`.
- `wp-route-declares-ability` — files: `site.yml` as the existing case, a spec whose R1 is "a REST route `GET /demo/v1/summary` an agent will call"; expect in `## Global Constraints`: `declares `ability``, and in the plan body: `wp-abilities-verify` and `runtime mode`.

Run: `python3 plugins/netdust-gates/evals/run-evals.py wp-pack-on-muplugin-package wp-route-declares-ability wp-feature-constraints wp-constraints-carry-evidence`
Expected: all four pass — the last two are regression: they read the two reworded pack lines (`make gate`, `make deploy-test env=staging`).

- [ ] **Step 5: Commit**

```bash
git add plugins/netdust-gates/skills/policy/SKILL.md plugins/netdust-gates/skills/policy/wordpress.md plugins/netdust-gates/evals/cases.json
git commit -m "gates(policy): a wordpress-muplugin package is a WordPress project; the pack asks a route an agent operates to declare ability, verified by its task and read by its reviewer"
```

---

### Task 3: The framework knows the option

**Files:**
- Modify: `plugins/netdust-wp/skills/ntdst-framework/SKILL.md:96-115` ("Rest is the one surface"; line 19's anchor stays as it is — Global Constraints)
- Modify: `plugins/netdust-wp/skills/ntdst-framework/references/traps.md:7-16` ("Fails quiet")
- Modify: `plugins/netdust-wp/skills/ntdst-patterns/golden-paths/content-type-feature.md:208-214`
- Modify: `plugins/netdust-wp/evals/behavioral-lessons.json` (one case)

**Interfaces:**
- Consumes: Task 1's installed `wp-abilities-api` skill (cited, not restated).
- Produces: the sentence Task 4 and Task 2's pack line rely on — "an ability is the shadow of a route; never `wp_register_ability()` yourself".

- [ ] **Step 1: Anchor baseline**

Run: `bash plugins/netdust-wp/evals/version-anchor.sh; echo rc=$?` and keep the output.
Expected today: two stale-anchor lines (`SKILL.md:18 … 5.2.0`, `:19 … 2.3.0`), `rc=1`.

- [ ] **Step 2: Three bullets in "Rest is the one surface", after line 113**

Content fixed by spec R1–R4, each marked `(5.5.0)`:

- **`'ability' => [...]` makes the route a WordPress ability, and declared is exposed (5.5.0).** `name` (`^[a-z0-9-]+$`), `label`, `description`; the ability's full name is `<namespace-slug>/<name>` (`stride/v1` + `list-registrations` → `stride-v1/list-registrations`); executing it dispatches the route through `rest_do_request()`, so the permission and the limiter run once and the return is the response's data. Core writes `public`, `show_in_rest` and `mcp.public` for you — there is no private ability, because WordPress lists nothing without `show_in_rest` and discovery already needs `read`. The category is the namespace slug unless `category` says otherwise. On core < 5.5.0 `ability` is an unknown option and the whole route is not registered.
- **A write verb's ability names `destructive` and `idempotent`, or the declaration is refused (5.5.0)** with one `_doing_it_wrong`; `output_schema` comes from the route's `schema` option or the ability's own, and its absence refuses too. Core derives nothing from the verb.
- **Never `wp_register_ability()` yourself (5.5.0)** — an ability is the shadow of a route (INV-11); the upstream `wp-abilities-api` skill explains the API, the drift reviewer's check #16 finds the bypass. To verify a branch's abilities, run the upstream `wp-abilities-verify` skill in **runtime mode** on your own DDEV, with these substitutions: its static inventory is `grep -rnE "['\"]ability['\"] *=>" --include=*.php <scope>` with R5's `vendor/` and `tests/` exclusions, each block's full name built as `<namespace-slug>/<name>` (its own `wp_register_ability(` grep is the call INV-11 forbids, so it would stop at "nothing to verify"); its runtime list is `wp_get_abilities()` over `ddev wp`, filtered on the namespace slug (`stride-v1/`), not the plugin slug; the harness's "plugin is active" check reads `--status=must-use`, since a consumer is an mu-plugin; the report path is your scratchpad; `wp-project-triage` is not installed — `site.yml` and the composer type answer what it would. Then its check 1 means what it says: Source+Runtime → PASS; Source-only → FAIL — the declaration is not reaching the registry (the trap below, or a core older than 5.5.0 dropping the route); Runtime-only → an ability under the route prefix that no `ability` block declares — drift; a registrar under its own prefix (Stride's `stride/…` beside its `stride/v1`) is check #16's to find. Read each annotation check against the route's handler. Quote the report in your task report; your reviewer reads it at the Close.

- [ ] **Step 3: One trap in "Fails quiet"**

- **An `ability` declared after `wp_abilities_api_init` fired registers nothing (5.5.0).** The hook fires lazily, on first registry access after `init`; core records every declaration and walks the record there, calling `rest_get_server()` first so routes declared at `rest_api_init` are in it. On WordPress < 6.9 the option is inert with one `_doing_it_wrong`, debug only; on core < 5.5.0 it is an unknown option and the route itself is absent — pinned by core's 5.5.0 unit tests.

- [ ] **Step 4: The golden path's worked example, marked**

Replace the one-line route at line 213 with the same route carrying `'schema' => [$service, 'summarySchema']` and an `'ability'` block (`name` `upcoming-editions-summary`, `label` `Upcoming editions summary`, a one-line `description`), the comment `// core 5.5.0+ — on an older core the option is unknown and the route is not registered`, and one sentence under it: a route an agent operates declares `ability`; the response data is what the agent receives.

- [ ] **Step 5: The eval case, runnable**

Append to `evals/behavioral-lessons.json` `cases`: id `abilities-route-option`, skill `ntdst-framework`, lesson "an ability is the shadow of a route — the `ability` option on `ntdst_rest()`, never `wp_register_ability()`"; `baseline_ref` `a317d2f — main, pre-5.5.0 skill text`; `context_before` and `context_after` both `skills/ntdst-framework/SKILL.md` and `skills/ntdst-framework/references/traps.md`; prompt: "On ntdst-core 5.5 an MCP client should be able to call my editions-summary endpoint. Show me the registration and what the client receives."; `baseline_expected_failure`: a `wp_register_ability()` call (or an `AbilityRegistrar` class) with its own `execute_callback` and permission, beside the route; `with_skill_assertion`: the `ability` block on the `ntdst_rest()` route, a `schema`, exposure written for it, the response data as the return, no `wp_register_ability()`; `must_contain`: `'ability'`, `ntdst_rest(`; `must_not_contain`: `wp_register_ability(`; `discriminator`: `grep -c "'ability' =>" skills/ntdst-framework/SKILL.md` — 0 before, ≥1 after.

Run, from `plugins/netdust-wp`: write a scratch cases file holding `_readme` and only `abilities-route-option`, then `bash evals/run-correctness-eval.sh <scratch>/abilities.json <scratch>/abilities-out.json` (needs the `claude` CLI; the tracked `evals/outputs/correctness-results.json` is untouched)
Expected: the result line for `abilities-route-option` reads PASS (not `BOTH-CLEAN`).

Run: `bash plugins/netdust-wp/evals/version-anchor.sh; echo rc=$?`
Expected: byte-identical to Step 1's output — the same two stale lines, no third.

- [ ] **Step 6: Commit**

```bash
git add plugins/netdust-wp/skills/ntdst-framework/SKILL.md plugins/netdust-wp/skills/ntdst-framework/references/traps.md plugins/netdust-wp/skills/ntdst-patterns/golden-paths/content-type-feature.md plugins/netdust-wp/evals/behavioral-lessons.json
git commit -m "wp(framework): the ability option (5.5.0) — declared is exposed, a write names its annotations, never wp_register_ability() yourself"
```

---

### Task 4: Drift check #16 — a hand-registered ability

**Files:**
- Modify: `plugins/netdust-wp/agents/ntdst-drift-reviewer.md:3` (description: "fifteen" → "sixteen", add "a hand-registered ability" to the list), `:11` and `:275` ("Fifteen" → "Sixteen"), `:620` (new `### #16` before the `---`)

**Interfaces:**
- Consumes: Task 3's rule.

- [ ] **Step 1: Write the check in #15's shape**

`### #16 A hand-registered ability` — the grep, with R5's comment filter:

```sh
grep -rnE "wp_register_ability(_category)?\(|AbilityRegistrar" --include=*.php <scope> | grep -vE "^[^:]+:[0-9]+: *(\*|//|/\*)"
```

**Then:** every hit outside `api/Rest.php` is drift. **Why:** INV-11 (core 5.5.0) — an ability is the shadow of a route; a second registration has its own permission and its own execute path, so the limiter, the response shaping and the capability floor run twice or not at all. **Suggested fix:** the route's `ability` option (`ntdst-framework` → "Rest is the one surface"); delete the registrar; name the abilities that have no route — those are findings for the project, not reasons to keep the class. **Exception:** a consumer on core < 5.5.0 — then the finding is the version bump, not the registrar. Part 1 picks INV-11 up from the vendored invariants doc once core ships it; this check is for the window before, and for a consumer that vendors an older core.

- [ ] **Step 2: Run the grep read-only against two real sites**

Run the check's full pipeline on `~/Sites/stride/web/app/mu-plugins/stride-core` and on `~/Sites/laika/web/app/mu-plugins`.
Expected: Stride — 17 hits: 11 in `Modules/Assistant/ReadAbilityRegistrar.php`, 4 in `WriteAbilityRegistrar.php`, 2 in `plugin-config.php:54-55` (the registrars' service entries — drift too, by the Then step), and the two comment lines (`Modules/Edition/SessionService.php:148`, `WriteAbilityRegistrar.php:11`) filtered out; Laika — 0. Quote both counts.

- [ ] **Step 3: Commit**

```bash
git add plugins/netdust-wp/agents/ntdst-drift-reviewer.md
git commit -m "wp(drift): check #16 — a hand-registered ability is a bypass of INV-11"
```

---

### Task 5: One gate, two shapes — `wp-testing`

**Files:**
- Modify: `plugins/netdust-wp/skills/wp-testing/SKILL.md:35` (Gate stack intro), `:91` (shake-out access item 4)
- Modify: `plugins/netdust-wp/evals/behavioral-lessons.json` (one case)

**Interfaces:**
- Produces: the sentence plans 2, 5 and 6 of the spec cite — "a package hosts the gate itself".

- [ ] **Step 1: The Gate stack intro, line 35**

Add after the first sentence: "The gate has one home, `netdust/wp-starter` `gate/`, and two shapes: a site's, and a package's (spec `wp-ai-base` R8–R9, landing with wp-starter's `package-gate` plan) — a composer package of type `wordpress-muplugin` hosts its own WordPress in `require-dev`, is its own DDEV project (a package worktree too, as the two-session rule says), and its `composer gate` runs every tier below, integration included, with a `deps:latest` tier red whenever WordPress, wp-phpunit or a `netdust/*` dependency is behind its newest tag. Not used, by name: Playground, Blueprints, wp-env, and a shared test site — `~/Sites/ntdst-testbed` is the one that existed; it is retiring, leave it alone."

- [ ] **Step 2: Shake-out access item 4, line 91**

Replace with: "4. **Standalone packages** (a `wordpress-muplugin` package, no `site.yml`): the DDEV recipe of item 1 on the package's own project, through the gate's package shape. Never Playground."

- [ ] **Step 3: The eval case, runnable**

Append to `evals/behavioral-lessons.json` `cases`: id `package-gate-not-playground`, skill `wp-testing`, lesson "a package hosts the gate itself — one gate, two shapes"; `baseline_ref` `a317d2f — main`; `context_before` and `context_after` `skills/wp-testing/SKILL.md`; prompt: "ntdst-baseline is a composer mu-plugin package with only Brain Monkey tests. How do I give it real-WordPress integration tests?"; `baseline_expected_failure`: proposes WordPress Playground / a Blueprint, wp-env, or a shared test site; `with_skill_assertion`: adopt wp-starter's gate in its package shape — WordPress in `require-dev`, the package's own DDEV project, `tests/Integration/` with `WP_UnitTestCase`, `composer gate` running it — and names Playground, Blueprints, wp-env and a shared test site as not used; `must_contain`: `require-dev`, `deps:latest` (zero hits each in `main`'s `wp-testing/SKILL.md`, so the baseline arm cannot produce them; `composer gate` and `tests/Integration` are already in the baseline text and would read `BOTH-CLEAN`); `must_not_contain`: `Blueprint`, `wp-env`; `discriminator`: `grep -c "Playground MAY be the browser" skills/wp-testing/SKILL.md` — 1 before, 0 after.

Run: the same scratch shape as Task 3 Step 5 with only this case, and `bash plugins/netdust-wp/tests/run.sh`
Expected: the result line for `package-gate-not-playground` reads PASS; `netdust-wp: all suites passed`.

- [ ] **Step 4: Commit**

```bash
git add plugins/netdust-wp/skills/wp-testing/SKILL.md plugins/netdust-wp/evals/behavioral-lessons.json
git commit -m "wp(testing): one gate, two shapes — a package hosts the gate itself; Playground is named as not used"
```

---

### Task 6: `references/baseline.md` — the real module count and the 2.22.0 switches

**Files:**
- Modify: `plugins/netdust-wp/skills/ntdst-framework/references/baseline.md:1, 17-31` and a new section after "The configuration surface"

- [ ] **Step 1: Count the modules from the source, not from memory**

Run: `git -C ~/Sites/ntdst-baseline show origin/main:ntdst-baseline.php | sed -n '60,110p'`
Expected: eleven module keys (`security` … `grants`); four of them (`yootheme`, `polylang`, `duplicate`, `grants`) default through a `DEFAULT_ENABLED` constant — read each service class on `origin/main` for its value. Rewrite the heading "Seven modules — six on by default, one opt-in" with the counted numbers, add the rows the table lacks (`admin_ui`, `polylang`, `duplicate`, `grants`, each with its service class), and set the title's version to the tag on `origin/main` (`v2.21.3`). The configuration-surface list (`:36-45`) stays as it is — R15 asks for the module count, nothing more.

- [ ] **Step 2: The switches section**

`## 2.22.0 — the hardening switches (spec wp-ai-base R12, lands with baseline's hardening-2026-10 plan)`: a table of the eight rows — switch, module, default, what it does — copied from the spec's R12 table, with C1's line saying the value is a capability (`manage_options` by default; a site lowers it for an editor who is an MCP client; `false` turns it off), and one line: C5, C6, C11 were not admitted.

- [ ] **Step 3: Anchor unchanged**

Run: `bash plugins/netdust-wp/evals/version-anchor.sh; echo rc=$?`
Expected: byte-identical to Task 3 Step 1's output.

- [ ] **Step 4: Commit**

```bash
git add plugins/netdust-wp/skills/ntdst-framework/references/baseline.md
git commit -m "wp(framework): baseline reference counts its modules from the source and lists the 2.22.0 hardening switches"
```

---

### Task 7: Versions and descriptions

**Files:**
- Modify: `plugins/netdust-wp/.claude-plugin/plugin.json` (`version` 1.4.0; description prefixed with the 1.4.0 line)
- Modify: `plugins/netdust-gates/.claude-plugin/plugin.json` (`version` 0.13.1; description prefixed)
- Modify: `.claude-plugin/marketplace.json` — the one marketplace file, both plugins' entries; `tests/test_plugin_manifest.py` requires the gates entry to match its `plugin.json`

- [ ] **Step 1: The two changelog lines**

netdust-wp 1.4.0: "the official AI surface and the one-gate rule — bin/wp-upstream-skills.sh pins trunk eff3785 (2026-10-28), skills CLI 1.7.4, and installs wp-abilities-api, wp-abilities-audit, wp-abilities-verify (a name missing at the pin is refused before the add); ntdst-framework teaches the `ability` route option of core 5.5.0 (declared is exposed, a write names destructive/idempotent, never wp_register_ability() yourself) with its trap and the golden path's example, and its lessons record how the three upstream skills read on a netdust project; the drift reviewer's check #16 finds a hand-registered ability; wp-testing says the gate has one home and two shapes — a package hosts its own WordPress and runs every tier through composer gate, Playground named as not used; baseline.md counts its modules from the source and lists the 2.22.0 hardening switches. Spec: specs/wp-ai-base/spec.md."

netdust-gates 0.13.1: "a composer.json of type wordpress-muplugin is a WordPress project for the Global Constraints; the WordPress pack says a package closes on composer gate and ships by tag, and asks a route an agent will operate to declare `ability`, verified by the task that touches such a route, running wp-abilities-verify in runtime mode on its own DDEV, its reviewer reading the quote. Eval cases wp-pack-on-muplugin-package, wp-route-declares-ability."

- [ ] **Step 2: Both suites**

Run: `bash plugins/netdust-wp/tests/run.sh && bash plugins/netdust-gates/tests/run.sh`
Expected: `netdust-wp: all suites passed`; every gates test green, `test_plugin_manifest.py` included.

- [ ] **Step 3: Commit**

```bash
git add plugins/netdust-wp/.claude-plugin/plugin.json plugins/netdust-gates/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "release: netdust-wp 1.4.0, netdust-gates 0.13.1 — the official AI surface and the one-gate rule"
```

---

## Close

1. The gate here is the two suites: `bash plugins/netdust-wp/tests/run.sh && bash plugins/netdust-gates/tests/run.sh` exit 0, plus `python3 plugins/netdust-gates/evals/run-evals.py wp-pack-on-muplugin-package wp-route-declares-ability wp-feature-constraints wp-constraints-carry-evidence` and the wp correctness runner on a scratch two-case file holding `abilities-route-option` and `package-gate-not-playground` (the tracked outputs file untouched), when the `claude` CLI is present.
2. `/feature-review wp-ai-skills` (no Makefile in this repo) — the whole-branch review; no threat model, no invariants doc, so no sentinel or auditor.
3. One fix pass, `specs/wp-ai-skills/review.md` committed with it.
4. No `/shakeout`: nothing here is a browser or wire surface. The one-gate rule's own check: `git grep -n -iE "playground|blueprint|wp-env" -- plugins/netdust-wp/skills plugins/netdust-gates/skills` lists only `wp-testing/SKILL.md:35` and `:91`, both naming them as not used (on `main` the one hit is `:91`).
5. Push `feature/wp-ai-skills`; the merge into `main` is Stefan's (a package's `main` is a stop). After the merge, and only then: `./scripts/sync.sh` refreshes the live caches. Studio: feature #4 → `review`, then `klaar`.
