# gates-quality-loop Implementation Plan (plan 1: netdust-plugins)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new e2e test is proven to fail without the feature (a revert run on the base code), the shake-out's screenshots land in the repo, a feature report is generated from the artifacts, the Close is a fixed order of make verbs with capped loops, and large features are cut into slices.

**Architecture:** Two new scripts in netdust-gates' `bin/`: `revert-run` (swap the branch's changed non-test files back to the base, run one test, always restore, write a classified log) and `feature-report.py` (artifacts in, `report.md` out). `shakeout-check.py` gains one rule: every new e2e row names its test (`Test: <path>`), and that test's revert log must show an assertion failure. The shake-out agent and command use them; netdust-devops gains `make shakeout` (the check) and `make report`; the policy, the reviewers' prompts and the plan reviewer get the order, the caps and the slice rule.

**Tech Stack:** Python 3 (stdlib), bash, Make; the plugins' own test runners.

**Spec:** `specs/gates-quality-loop/spec.md` (approved 2026-11-06). This plan covers R2, R4, R6, R7, R8, R9, R12, R13, R14, R15. Not here: **R10** (Studio artifact links) waits on a Studio change and is its own later plan; **R11** (the invariants gate tier) is plan 2 in wp-starter, and its drift-reviewer half is a small plan 3 here once that tier exists. Two review rounds are in `plan-review.md` (the policy's cap); this text answers both.

## Global Constraints

Not a WordPress project: the spec's own constraints.

**The row and its test.**
- Every `browser` and `wire` row's Evidence names its ONE test first, as `Test: <project-relative path> :: <test title>` (before `Browser:`, so `Accepted-by-human:`'s greedy reason never swallows it): a file holds many flows in real registries (laika: five rows on `productions.spec.ts`), so the key is the file AND the title. Its revert log is derived, never pointed at: `specs/<feature>/shakeout/<stem>.revert.log`, `<stem>` = the path with `/` as `__`, then `--`, then the title slugged (lowercase, non-alphanumerics as `-`). Two NEW rows cannot share one key; re-driven rows may share a file.
- A row is new or re-driven by the REGISTRY, never by a word in the row: a test file named by any `specs/CHECKS.md` row whose `first feature` is this feature, or by none, is new (the shake-out registers every new flow under this feature, `shakeout-qa.md`), and the proof is required; a file named only by rows of earlier features is re-driven and exempt. The registry's `test` cell may be backticked; the join strips it as `shakeout-check.py:173` does. Only `Accepted-by-human:` excuses a new row without its proof.

**The revert run.**
- The base is the merge-base of `HEAD` with production's branch: `scripts/site environments.production.branch` when the project has `scripts/site`, else `main`, else `master`.
- `revert-run` never commits, never pushes, never touches an untracked file, and restores the tree in a trap on every exit, an interrupt included. It refuses to start when a tracked file in the swap set has uncommitted changes, or when an untracked file sits at a path the branch deleted (the base checkout would overwrite it). The agent calls it as `~/.claude/plugins/netdust-gates/bin/revert-run` (the link the session-start hook makes; agents have no `CLAUDE_PLUGIN_ROOT`), passing a command that runs that ONE test (Playwright `--grep "<title>"`, PHPUnit `--filter`).
- The log's first line is its classification: `revert-run: assertion-failed`, `revert-run: passed` or `revert-run: error`. `assertion-failed` needs a non-zero exit and an `expect` failure in the output: Playwright's `Error: expect(` with `Expected`/`Received` (including `toBeVisible()` on an element the base does not render: that IS the proof, the test passed with the feature and fails without it), or PHPUnit's `Failed asserting`. A non-`expect` timeout (`locator.click`, `page.goto`, `waitForSelector`, `Test timeout of`), a login or a seeding error, with no `expect` failure, is `error`.
- The log keeps the classification, the base sha, the swapped paths, the command, the exit code and at most 20 lines around the first assertion marker, never the raw output. `shakeout-check.py` scans every revert log for credentials with the same pattern it runs over `shakeout.md`.

**The Close and its stops**, written once in `skills/policy/SKILL.md` and stated nowhere else:
1. `make gate` · 2. `make review name=<feature>` · 3. one fix pass · 4. `/shakeout` in a session, then `make shakeout name=<feature>` · 5. one fix round for a failed shake-out row · 6. `make report name=<feature>`, committed · 7. `make gate` on that tip (the stamp `promote` needs) · 8. STOP: Stefan reads `report.md`: its screenshots, every `Accepted-by-human:` row (an agent-written one is reverted) and the hunt's `not ours:` / `rejected:` lines, each his to overrule · 9. finish (`make promote` / `make land`).
Per slice of a sliced plan: `make gate`, the slice's own flows (appended to the one `shakeout.md`), `make report`; the review, the fix pass, the hunt, the final gate and the stop run once, at the feature's end.
Caps: plan review 2 rounds, coder 3 attempts per task, fix pass 1, shake-out fix round 1; a cap hit is a `Ruling:` and a stop for Stefan. Every other prompt that loops ("until it exits 0", "run /plan-review again") defers to these caps by reference, never restating a number.

**Make verbs.** `make shakeout name=X` and `make report name=X` read `commands.shakeout` / `commands.report` from `site.yml` and pass the name as `SHAKEOUT_NAME` / `REPORT_NAME`, as `review` passes `REVIEW_NAME`; a missing key exits 1 with the line to add.

**Budgets.** `skills/policy/SKILL.md` stays under 150 lines (`tests/test_policy_skill.py:43`), `skills/policy/wordpress.md` at most 60 (`:47`).

**Release.** netdust-gates 0.19.0, netdust-devops 0.15.0: each in `plugin.json`, the marketplace entry (both description heads) and, for devops, `dist/VERSION`. Merge and push are Stefan's.

## Threat model

`revert-run` is the one part that writes a working tree another session owns.

1. **Uncommitted work overwritten** → it refuses on any modified tracked file in the swap set, and on an untracked file at a branch-deleted path, naming it.
2. **A crash leaves the base code in the tree** and the next commit ships it → one idempotent restore function, called from `trap … EXIT INT TERM`; restore by status: modified (`M`, and a typechange `T`, treated as `M`) and added (`A`) paths `git checkout HEAD -- <p>` (added files were removed for the run, they are in HEAD), deleted (`D`) paths `git rm -q --cached --ignore-unmatch -- <p>; rm -f -- <p>`, so a second restore is a no-op. A test kills the process group mid-run and proves the tree equals HEAD.
3. **Renames, spaces, a leading dash** → `git diff -z --no-renames --name-status`, every path after `--`.
4. **A false pass from built assets** → untracked build output (compiled JS/CSS) is not swapped, so a browser test can pass on the base; that is the safe direction (the row is refused, Stefan accepts it or the test is sharpened), and the agent prompt says so.
5. **Credentials in a committed log** → excerpt only, and the checker's credential scan covers the logs. The scan skips the `Test:` value itself (`app-password.spec.ts` is a file name, not a secret).

## Simplest design

The simplest design for R2 is a second checkout (a git worktree with its own DDEV project). That needs Stefan's Windows UAC step for every new DDEV project, so it cannot run unattended. Swapping only the changed non-test files in the one checkout, behind a trap, needs nothing new. For R8 the simplest report is the manifest itself; it has no slices, no gaps and no link to the tests, so a small script joining plan, manifest and registry on the `Test:` path is the smallest thing that answers Stefan's question.

## First working version

Task 1: `bin/revert-run` swaps, runs and restores in a scratch repo and writes a classified log; the coder quotes one `assertion-failed` log (Playwright's real `toBeVisible` text) and one `error` log (a click timeout) from its test run.

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| `revert-run` | the script: exit code, log, the tree after | integration (scratch git repo) · `plugins/netdust-gates/tests/test_revert_run.py` · `bash plugins/netdust-gates/tests/run.sh test_revert_run.py` | none |
| `shakeout-check.py`: the `Test:` marker, derived logs, registry exemption, log credentials | `check(spec_dir)` / the CLI exit | unit · `plugins/netdust-gates/tests/test_shakeout_check.py` · `bash plugins/netdust-gates/tests/run.sh test_shakeout_check.py` | none |
| `feature-report.py` | the CLI: `report.md`, the trial line | unit (fixture feature dirs) · `plugins/netdust-gates/tests/test_feature_report.py` · `bash plugins/netdust-gates/tests/run.sh test_feature_report.py` | none |
| shake-out agent, command, policy Close, plan-review command, reviewer prompts, pack, CLAUDE.md | the prompt files | wiring · `plugins/netdust-gates/tests/test_close_wiring.py` (pins `studio-checks` in the three reviewer prompts, `INV-2` in the pack, the revert-proof trial label in `CLAUDE.md`, `layer` in `plan-reviewer.md`, `Slice` in the policy, and the yield's `overrule` / `the hunt's tally` moved from `commands/shakeout.md` into the policy's step 8), `test_artifact_layout.py`, `test_policy_skill.py` · `bash plugins/netdust-gates/tests/run.sh` | none |
| `make shakeout` / `make report` | the make targets | integration · `plugins/netdust-devops/tests/test-makefile.sh` · `bash plugins/netdust-devops/tests/run.sh` | none |
| evals, release | `evals/cases.json`, versions | `test_evals_shape.py`, `test-marketplace.sh` | none |

## Review Focus

1. A crash or a Ctrl-C in `revert-run` leaves the base code in the coder's tree — Task 1 (`test_interrupt_restores_the_tree`).
2. A login or setup failure on the base counted as proof; a missing element under `expect` not counted — Task 1 (`test_click_timeout_is_error`, `test_expect_on_a_missing_element_is_assertion_failed`), Task 2 (`test_error_log_does_not_prove_a_row`).
3. Uncommitted work overwritten by the swap — Task 1 (`test_refuses_on_a_modified_tracked_file`).
4. One proof log satisfying several new rows, a new test in an older file going unproven, or a new row exempted by a word — Task 2 (`test_two_new_rows_cannot_share_one_key`, `test_redriven_rows_may_share_a_file`, `test_new_test_in_an_older_file_needs_its_proof`, `test_redriven_is_read_from_the_registry_not_the_word`).
5. A magic link in a committed revert log — Task 2 (`test_credential_in_a_revert_log_fails`).
6. `make promote` refusing after a correct Close because the last gate ran before the report's commit — Task 6 (`test_close_wiring.py` pins `make report` before the last `make gate`, before the finish, in that order).

---

### Task 1: `bin/revert-run`

**Files:**
- Create: `plugins/netdust-gates/bin/revert-run` (bash), `plugins/netdust-gates/tests/test_revert_run.py`

**Interfaces:**
- Produces: `revert-run <feature> <test-path> <test-title> -- <test command…>`, run from the project root; writes `specs/<feature>/shakeout/<stem>.revert.log` (stem as in Global Constraints); exit 0 when the log was written, whatever the classification; 2 on refusal or a git error.

- [ ] **Step 1: Write the tests** in the suite's style (a test file exposes `run()`, `tests/run.sh:12-25`; read `test_shakeout_check.py` first). Each builds a scratch repo: `main`, then a feature branch that changes `src/a.txt`, adds `src/new.txt`, deletes `src/old.txt`, renames `src/r1.txt` → `src/r2.txt`, changes `src/-x y.txt` and adds `tests/t.sh`. Cases: `test_expect_on_a_missing_element_is_assertion_failed` (the command prints Playwright's real `toBeVisible()` failure text, `Error: expect(locator).toBeVisible() failed … Expected: visible … Received: <element(s) not found>`, and exits 1); `test_phpunit_failed_asserting_is_assertion_failed`; `test_click_timeout_is_error` (`TimeoutError: locator.click: Timeout 5000ms exceeded`, no `expect`); `test_test_that_passes_on_base_is_passed`; `test_added_deleted_and_renamed_files_round_trip` (during the run the base layout, after it HEAD's, `git status --porcelain` empty); `test_refuses_on_a_modified_tracked_file` (exit 2, the file named, nothing swapped); `test_refuses_on_an_untracked_file_at_a_deleted_path`; `test_typechange_round_trips`; `test_interrupt_restores_the_tree` (the command sleeps; the test starts it with `start_new_session=True` and `os.killpg(…, SIGINT)`; afterwards every file equals HEAD byte for byte, and running the restore twice is harmless); `test_tests_and_specs_are_never_swapped`; `test_log_keeps_an_excerpt_not_the_output` (a 500-line output leaves at most 20 output lines in the log).
- [ ] **Step 2: Run** `bash plugins/netdust-gates/tests/run.sh test_revert_run.py`. Expected: FAIL (no script); quote it.
- [ ] **Step 3: Write `revert-run`** per the Global Constraints and the Threat model: the swap set from `git diff -z --no-renames --name-status <base>...HEAD` minus `tests/` and `specs/`; the refusal; for the run, `git checkout <base> -- <M and D paths>` and `rm -f -- <A paths>`; the restore by status in one idempotent function under the trap (`--ignore-unmatch` on the `D` restore); the classification; the log.
- [ ] **Step 4: Run** the test file (GREEN), then `bash plugins/netdust-gates/tests/run.sh` (all green). Quote both, plus one `assertion-failed` and one `error` log. Commit: `feat(gates): revert-run — a new test is run on the base code, the tree always restored`.

### Task 2: `shakeout-check.py` reads the test, the proof and the logs

**Files:**
- Modify: `plugins/netdust-gates/bin/shakeout-check.py`, `plugins/netdust-gates/tests/test_shakeout_check.py`

**Interfaces:**
- Consumes: Task 1's log format; `specs/CHECKS.md`'s `first feature` (already parsed, `shakeout-check.py:141-142,196`).
- Produces: a `TEST` marker regex beside `ACCEPTED` (`Test:\s*(?P<path>\S+)\s*::\s*(?P<title>[^·]+?)\s*(?:·|$)`); findings `shakeout-revert` (a separate pass over the rows, honouring `Accepted-by-human:` as `check():231-234` does) and `shakeout-credential` extended to every revert log a row derives.

- [ ] **Step 1: Tests first:** `test_new_browser_row_with_assertion_failed_log_passes`; `test_new_wire_row_without_test_marker_fails`; `test_new_row_without_its_log_fails`; `test_error_log_does_not_prove_a_row`; `test_passed_log_does_not_prove_a_row`; `test_two_new_rows_cannot_share_one_key` (two new rows naming the same file and title fail, naming both); `test_redriven_rows_may_share_a_file` (five re-driven rows on one file, as laika's registry has, pass); `test_new_test_in_an_older_file_needs_its_proof` (a file registered under an older feature AND under this one: its new row needs its log); `test_redriven_is_read_from_the_registry_not_the_word` (a row with `Re-driven` written in Evidence but its file registered to THIS feature still needs its log); `test_unregistered_test_counts_as_new`; `test_test_marker_survives_accepted_by_human_order`; `test_password_in_a_test_file_name_is_not_a_credential`; `test_accepted_by_human_excuses_a_missing_revert`; `test_cli_row_needs_no_revert`; `test_credential_in_a_revert_log_fails`. Run: RED, quoted. Add `test_scratchpad_screenshot_path_fails` as a PIN (it is already green: `_screenshot_problem`, `:90-92`, accepts only `shakeout/` paths); say so in the report.
- [ ] **Step 2: Implement** the marker, the derived log path, the registry lookup, the separate pass and the scan. GREEN; whole suite green. Quote. Commit: `feat(gates): shakeout-check proves every new e2e row by its own test's revert log`.

### Task 3: The shake-out uses it, and its stop moves to the end

**Files:**
- Modify: `plugins/netdust-gates/agents/shakeout-qa.md`, `plugins/netdust-gates/commands/shakeout.md`, `plugins/netdust-gates/tests/test_close_wiring.py`

- [ ] **Step 1: Wiring tests first** (the file's style): the agent prompt's write list allows `specs/<feature>/shakeout/*.revert.log` and names `revert-run` as the one command allowed to swap non-test files, because it restores them; it names the `Test: <path> :: <title>` marker written first in Evidence, the `~/.claude/plugins/netdust-gates/bin/revert-run <feature> <test-path> <title> -- <command running that one test>` call after a new test passes, the capture path `specs/<feature>/shakeout/<name>.png` and the ban on the scratchpad, the built-assets caveat (Threat model 4), and "the policy's fix round, then its stop" in place of "until the checker exits 0" (no number here: the caps live in the policy); `commands/shakeout.md` runs `make shakeout name=<feature>` when the project has the verb, else the checker by path, carries no "until it exits 0" loop, and its old Step 4 yield is gone: its tail points at the policy's Close steps 5-9, and the yield's content (the screenshots, the `Accepted-by-human:` rows, the hunt's `not ours:` / `rejected:` lines, Stefan's overrule) moves to the policy's step 8, the pins `test_close_wiring.py:72-73` moving with it. RED quoted.
- [ ] **Step 2: Edit the two prompts** to match: new tests get a revert run and a `Test:` marker, re-driven rows only a `Test:` marker; slices append rows to the one `shakeout.md`; the hunt runs once, at the feature's end. GREEN; suite green. Commit: `feat(gates): the shake-out proves each new test on the base, keeps its screenshots in the repo, and leaves the yield to the Close`.

### Task 4: `bin/feature-report.py`

**Files:**
- Create: `plugins/netdust-gates/bin/feature-report.py`, `plugins/netdust-gates/tests/test_feature_report.py`, fixtures under `plugins/netdust-gates/tests/fixtures/report/`

**Interfaces:**
- Produces: `feature-report.py specs/<feature>` writes `specs/<feature>/report.md`: one section per slice (read from `### Task N · Slice M: …`; a plan with none is one section); per section the task titles and each E2E flow of its Test map rows; two named joins: a Test map row belongs to the task whose heading carries the row's Unit text (a row with no matching task is a named gap), and a flow name joins the manifest row whose `Flow` cell carries it (the agent copies it, `shakeout-qa.md:25`), then that row's `Test:` key joins its `@e2e` registry row and its revert log; the report also lists the manifest's `Accepted-by-human:` rows and the hunt's `not ours:` / `rejected:` lines for Stefan's step-8 read; a flow with no test, or a new test with no `assertion-failed` log, is a named gap; a `Close: <minutes>` line from `git log --diff-filter=A --format=%ct -- specs/<feature>/review.md` to the report's run; and in `specs/CHECKS.md` under `## Trial log`, ONE line per feature, replaced on every run: `<feature> · revert-passed: <n> · revert-errors: <n> · report-gaps: <n>` (`revert-passed` counts logs classified `passed`, tests that could not fail without the feature; `revert-errors` counts `error` logs, friction, not catches). This departs from the spec's single `revert-fails` label on purpose (round 1's S10: "fails" could mean either); `CLAUDE.md`'s removal rule uses these same words. Exit 0, or 1 when the plan is missing.

- [ ] **Step 1: Tests first** with fixture dirs: `test_two_slices_two_sections` (including a Test map row whose Unit matches no task, reported as a gap), `test_unsliced_plan_is_one_section`, `test_lists_accepted_rows_and_hunt_lines`, `test_missing_revert_is_a_named_gap`, `test_trial_line_is_replaced_not_appended`, `test_counts_follow_the_log_classes`, `test_reads_artifacts_only` (a cell an artifact lacks says `missing`, never a guess). RED quoted.
- [ ] **Step 2: Implement** (stdlib only). GREEN; suite green. Commit: `feat(gates): feature-report.py — the report generated from plan, manifest and registry`.

### Task 5: `make shakeout` and `make report`

**Files:**
- Modify: `plugins/netdust-devops/dist/Makefile.netdust` (two targets in `review`'s shape after it; `help` lines; `_DOCTOR_COMMANDS` and a `_doctor-line-*` each, `$$HOME`/`$$SHAKEOUT_NAME` escaped as `:1188` does), `plugins/netdust-devops/templates/site.yml.tmpl` (two DECLARED keys with a comment above each: `shakeout: python3 "$HOME/.claude/plugins/netdust-gates/bin/shakeout-check.py" "specs/$SHAKEOUT_NAME"`, `report: python3 "$HOME/.claude/plugins/netdust-gates/bin/feature-report.py" "specs/$REPORT_NAME"`; the `~/.claude/plugins/netdust-gates` link is made by gates' session-start hook), `plugins/netdust-devops/tests/test-makefile.sh`

- [ ] **Step 1: Tests first:** with a fixture `site.yml` whose two keys run a stub that records its env: `make shakeout name=x` runs it with `SHAKEOUT_NAME=x`, `make report name=x` with `REPORT_NAME=x`; without the key each exits 1 and prints the line to add; without a name, the usage; `make doctor` names a missing key; the every-expected-key template check grows to both. RED quoted.
- [ ] **Step 2: Implement.** GREEN; `bash plugins/netdust-devops/tests/run.sh` green. Commit: `feat(devops): make shakeout (the check) and make report`.

### Task 6: Policy, reviewers, plan reviewer, evals, release

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, `plugins/netdust-gates/tests/test_close_wiring.py`, `plugins/netdust-gates/tests/test_artifact_layout.py`, `plugins/netdust-gates/commands/plan-review.md`, `plugins/netdust-gates/commands/feature-review.md`, `plugins/netdust-gates/agents/security-sentinel.md`, `plugins/netdust-gates/agents/invariant-auditor.md`, `plugins/netdust-gates/agents/plan-reviewer.md`, `plugins/netdust-gates/skills/policy/wordpress.md`, `plugins/netdust-gates/CLAUDE.md`, `plugins/netdust-gates/evals/cases.json`, the version files

- [ ] **Step 1: The policy, within 150 lines.** The Close becomes the nine steps of the Global Constraints with the caps once and the per-slice line; the slice rule in two lines under The plan (vertical cut, `### Task N · Slice M:`, per slice `make gate` · its own flows · `make report`, one `shakeout.md`, hunt and stop once at the end); the artifact table gains `report.md`. Lines cut to make room, none pinned by a test (keep `/review-fix`, pinned at `test_close_wiring.py:81`): the `shakeout-bugs.md`/`shakeout-abort.md` and `test-prune/<date>.md` rows folded into one (`:28,30`), `:32` folded into the table's lead, the "On demand" paragraph (`:145-149`) folded to two lines, the Execution-mode paragraph (`:95-107`) from 13 to 9 lines at the file's width keeping the phrases `test_policy_skill.py:52-54` and `test_hc_wiring.py:65` pin, the duplicate sentence in `:85-91`, and the `commands.gate` explanation in the Close's step 1. Count with `wc -l` and quote it. The Stops line names "the report yield (Close, step 8)".
- [ ] **Step 2: Pins.** `test_close_wiring.py:83-85` move to the new numbering ("9. Every change:" or the finish step's new text, "(Close, step 8)"), `:72-73` move to the policy's step 8 with the yield, `:74-79`'s "what remains" sentence follows the new steps, and pins are added that `make shakeout`, `make report` and the second `make gate` appear in that order before the finish, plus the Test map row's new tokens; `test_artifact_layout.py`'s `ALLOWED` gains `report` (`shakeout/*.revert.log` is already allowed by its pattern).
- [ ] **Step 3: The other prompts.** `commands/plan-review.md` Step 3 defers to the policy's cap instead of "run /plan-review again"; `feature-review.md`, `security-sentinel.md` and `invariant-auditor.md` gain R4's line, worded for review time: "every E2E-flows entry in the Test map names a test that exists; a flow an earlier slice already drove has its revert log; missing logs are `make shakeout`'s to refuse, not yours; do not re-judge assertions or redundancy, that is studio-checks'"; `plan-reviewer.md` judges a layer-shaped slice as a finding; `wordpress.md`'s Drift line (`:26-27`) absorbs R12's sentence (baseline's invariants are its own, INV-2 is drift check #11), staying at 60 lines; `CLAUDE.md` gains R15's removal rule beside the hunt's, and one sentence beside the growth rule naming `### Task N · Slice M:` as the approved exception, read by `feature-report.py`; `evals/cases.json` gains R13's two cases in the existing shape.
- [ ] **Step 4: Run** `bash plugins/netdust-gates/tests/run.sh` and `bash plugins/netdust-devops/tests/run.sh`; quote. `test_stop_hook_dedup` already fails on this branch before any change (pre-existing, unrelated): report it as such, every task, and do not fix it here. Bump versions; run both again; quote. Commit: `release: netdust-gates 0.19.0, netdust-devops 0.15.0 — revert proof, feature report, the Close as make verbs`. Push the branch; do not merge.

## Hand-over

Stefan merges and pushes, then `scripts/sync.sh`; projects get the verbs through `make devops-update` (the updater replaces itself since 0.14.1) and add the two `commands.*` lines `make doctor` names. The first planned WordPress feature after this runs the full Close. Plan 2 (wp-starter, R11's tier) and plan 3 (the drift reviewer's half) follow; R10 waits on Studio.
