# Feature review — wp-ai-skills

Reviewed: `origin/feature/wp-ai-skills` at `9db2d271adca20218881b8e03c7d31e711b09d26`, base `59f6785200d268624ecd5f2d94e5acef258746d6` (origin/main, merge-base). Plan `specs/wp-ai-skills/plan.md`, spec `specs/wp-ai-base/spec.md` (R14–R17). Level: full. Reviewers: superpowers' code reviewer (fresh `general-purpose` subagent, most capable model) on a detached checkout of the head. No joiners applied: no `## Threat model`, no `ARCHITECTURE-INVARIANTS.md`, not a WordPress project. Dispatched by `/feature-review wp-ai-skills` from the reviewer session on 2026-10-29.

Findings: 0 Blocking · 1 Should fix · 5 Note

Reviewer's rulings on the findings (2026-10-29): Issue 1 fixed by steering the prompt and keeping both needles; Issue 2 taken in the same fix commit; Issues 3–6 are notes, nothing to change on this branch (3 stays consistent with #15; 4 is for the executor of every WordPress plan on core < 5.5.0; 5 and 6 need nothing).

---

## Review — feature/wp-ai-skills (59f6785..9db2d27)

Everything below was verified on the detached checkout; nothing was mutated. Commands run and their summary lines are quoted where they matter.

### Strengths

- **Both suites green, as claimed.** `bash plugins/netdust-wp/tests/run.sh` → `netdust-wp: all suites passed` (29 upstream-skills assertions incl. the three new `missing at pin:` lines; live-routing clean). `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` → `Modules passed: 20 / Modules failed: 0`, including `pass policy: under 150 lines (got 149)`, `pass pack: short…`, `pass marketplace.json carries a netdust-gates entry … version matches plugin.json`.
- **Boundary held exactly:** `wc -l` → policy 149, `wordpress.md` 60. The new pack line (`wordpress.md:37`) is one physical line (524 chars), carries no `specs/` path (`grep specs/` → none; `test_artifact_layout` green), and names its owner and its evidence as the pack header demands.
- **The script change is minimal and right** (`bin/wp-upstream-skills.sh:25-29`): the source check runs after the checkout and before the `npx … add`, skipped only under `--dry-run` (which never fetches), `exit 1` on stderr with the name. The test (`tests/test-upstream-skills.sh:87-96`) exercises the exact blind spot — `$HOME` still holds `wp-abilities-audit` from the earlier install when the PIN3 run is refused — and asserts behaviour (rc, message, no new `$NPX_LOG` line), not prose; the stub is untouched. Pin is a 40-hex sha (`:7`), guarded by the existing `^[0-9a-f]{40}$` refusal.
- **Real install verified:** `--check` → `pin: eff3785…`, `skills-cli: 1.7.4`, seven `present:` lines, rc 0; `ls-tree` of the cache at `eff3785` lists all three `wp-abilities-*` skills.
- **Drift check #16 reproduced read-only:** Stride 19 raw → 17 after the comment filter (11 `ReadAbilityRegistrar.php`, 4 `WriteAbilityRegistrar.php`, `plugin-config.php:54-55`); the two filtered lines are the docblock at `WriteAbilityRegistrar.php:11` and `SessionService.php:148`. Laika 0. The check follows #15's shape (grep · Then · Why · Fix · Exception) and gives a real command.
- **`baseline.md` matches `origin/main` (v2.21.3):** eleven module keys in `ntdst-baseline.php:67-95`, seven `true`, four through `DEFAULT_ENABLED = false` (`DuplicateService.php:30`, `GrantService.php:15`, `PolylangService.php:48`, `YOOthemeSourcesService.php:43`); every service class named exists; the Polylang `POLYLANG_VERSION` door and the `ntdst/baseline/admin/apps` filter are real. The switches table is R12's eight rows verbatim, with Decision 15's C1 line and the C5/C6/C11 sentence.
- **`version-anchor.sh` byte-identical** on main and head (same two stale lines, rc 1) — diffed, not eyeballed.
- **One-gate grep:** only `wp-testing/SKILL.md:35` and `:91`, both naming Playground/Blueprints/wp-env/the testbed as not used.
- **Task 7 complete:** `.claude-plugin/marketplace.json` bumped for *both* entries (0.13.1, 1.4.0), matching both `plugin.json` files. `scripts/sync.sh` was not run — the live cache still reads 1.3.2 / 0.13.0.
- **Policy trim keeps its sense** (`policy/SKILL.md:111-118`): the six verbs, `NETDUST_AGENT_OK=1`, "`ship` and production stay his"; every needle in `test_policy_skill.py` present. The trigger widening sits inside its three lines (`:67-69`).
- **Framework text matches spec R1–R4 and the installed upstream:** full name `<namespace-slug>/<name>`, `rest_do_request()` dispatch, the three exposure spellings written by core, write-verb annotations, `output_schema` from `schema` or the block, category from the namespace, `< 5.5.0` drops the route (confirmed against `~/Sites/ntdst-core/api/Rest.php:748`, 5.4.1). The verify substitutions cite the upstream skill's real facts (static default at `SKILL.md:53`, zero-hit stop at `:63-68`, `--status=active` and the plugin-slug filter in `runtime-harness.md:52,75,99`) and state only the netdust deltas — citation, not restatement. The golden path's three-argument `->get(path, handler, options)` exists (`Rest.php:422`), `schema` is a known option, and the 5.5.0 comment marks the block.
- `lessons.md:384-390` cites the SKILL.md section, no task number. The `abilities-route-option` rewording to "exposure left to core" is what the skill says ("Core writes `public`, `show_in_rest` and `mcp.public` for you") — the earlier wording contradicted it.

### Issues

#### Critical (Must Fix)
None.

#### Important (Should Fix)

1. **`plugins/netdust-wp/evals/behavioral-lessons.json:349-352` — do not apply the coder's proposed drop of `deps:latest`.** Token counts on main's `wp-testing/SKILL.md` (the baseline arm's context): `require-dev` 0, `deps:latest` 0, `composer gate` 2, `tests/Integration` 3. But `require-dev` is generic Composer knowledge — a model asked "how do I give a composer package real-WordPress integration tests" writes "put WordPress in `require-dev`" unaided — and `must_not_contain` is probed in code fences only (`run-correctness-eval.sh:101-115`), so a baseline answer that proposes wp-env in prose reads clean. With `require-dev` alone the case will read `BOTH-CLEAN`. `deps:latest` is the only netdust-specific needle; it is what makes the case discriminate. The after-arm miss (4/6) is a prompt problem, not a needle problem: the prompt never asks about staying current, so the tier is optional in the answer. Fix: keep both needles and add one clause to the prompt ("…and keep them running on the newest WordPress?"), or replace `deps:latest` with `package shape` (0 on main, twice in the after text at `:35` and `:91`). Either keeps the baseline arm unable to produce the string. The committed definition is sound as it stands; the proposal would weaken it.

#### Minor (Nice to Have)

2. **`behavioral-lessons.json:325` — the `abilities-route-option` judge assertion is narrower than the skill.** "a `schema`" reads as the route option; the skill (`ntdst-framework/SKILL.md:115`) allows `output_schema` in the block instead. Five sub-assertions in one judge line is why it flips while the probes PASS 5/5. Suggest "a `schema` on the route or an `output_schema` in the block". Same for the testing case's "*names* Playground, Blueprints, wp-env and a shared test site as not used" (`:348`): an answer that simply does not propose them should not fail — "does not propose …".
3. **`agents/ntdst-drift-reviewer.md:623` — #16's grep has no `(^|/)vendor/|(^|/)tests/` tail**, unlike R5's mechanical check it mirrors (spec `:137`). The Then-step's `api/Rest.php` exception covers vendored core at a `mu-plugins` scope; a consumer's `tests/` fixture that calls `wp_register_ability(` would be reported as drift. #15 is shaped the same way, so this is consistent with its siblings — optional.
4. **`policy/wordpress.md:37` — "(…, core 5.5.0)" on a fleet that is on 5.4.1.** Every WordPress plan written before core 5.5.0 ships copies a line whose literal reading drops the route (unknown option). The citation chain covers it (the framework bullet, `traps.md:17`, the golden-path comment, #16's Exception "the finding is the version bump"), and the line has no room at the 60-line boundary. Nothing to change; the executor should know a plan on 5.4.1 must name the deviation — the spec's cut (plan 1 before plan 3) accepted this.
5. **Coder's deferred minor on line width:** main's widest body line was 136 (`policy/SKILL.md:146`, Close 5), not 120; the rewrap at 122–123 narrows the file. Nothing to do.
6. **Script state after a refusal:** the clone is left at the missing pin while `$HOME` holds the previous pin's copies, and `--check` then reads green with the script's `PIN`. Harmless (the next good run re-fetches); the contract never claimed otherwise. Optionally the denial test could assert the stale copy survived, though (b)'s "seven present" covers it indirectly.

### Declined to judge

- `ntdst-framework/SKILL.md:19` still says "2.3.0 … seven modules" while `baseline.md` says eleven — the plan's Global Constraints keep `version-anchor.sh` output identical; re-anchoring is out of this spec.
- `baseline.md:36-45` configuration-surface list (six filters for eleven modules) — Task 6 Step 1 keeps it on purpose; R15 asks for the count only.
- YOOtheme §0 directions (R15 E) — Decision 8 defers them.
- `wp-project-triage` not installed though all three upstream skills require it — R14 names only the three; the skill text substitutes `site.yml` and the composer type.
- `wp-testing/SKILL.md:35` naming the local path `~/Sites/ntdst-testbed` — R17 asks for the testbed by name.
- The `UPSTREAM` env override in the script — pre-existing, not in the diff.
- The real install writing `~/.claude/skills/` ahead of review — the script's purpose, named in the plan.
- The eval runs themselves — not run here per instructions; the coder's 4/4, 5/5 and 4/6 are taken as claims. The case *definitions* were judged (above) and the gates regexes were exercised with `python3 -I`: in-section match true, cross-heading leak blocked, the `declares \`ability\`` needle matches the pack line.
- "bar `promote` …" wording in Stops — style; the needles pass.

### Recommendations

- Rule on Issue 1 before the fix pass: keep `deps:latest` (steer the prompt) or swap it for `package shape`; never `require-dev` alone. Re-run only that case through a scratch one-case file, as the plan prescribes.
- Optionally take Issue 2 in the same fix commit; the rest are notes.
- After Stefan's merge, and only then: `./scripts/sync.sh`, then `bash plugins/netdust-wp/bin/wp-upstream-skills.sh --check` on the box (Close 5).

### Assessment

**Ready to merge?** With fixes

**Reasoning:** The implementation matches the plan task for task, both suites and every mechanical constraint (149/60, pin shape, anchor output, one-gate grep, drift #16 counts, baseline source, both manifests, no sync) verify clean, and the skill texts cite rather than restate. The one thing to settle is the open eval question: the coder's proposed `deps:latest` drop would make `package-gate-not-playground` stop discriminating, so the answer is a one-clause prompt fix, not a weaker needle.
