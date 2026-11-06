# gates-quality-loop Implementation Plan (plan 1: netdust-plugins)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new e2e test is proven to fail without the feature (a revert run on the base code), the shake-out's screenshots land in the repo, a feature report is generated from the artifacts, the Close is a fixed order of make verbs with capped loops, and large features are cut into slices.

**Architecture:** Two new scripts in netdust-gates' `bin/` — `revert-run` (swap the branch's changed non-test files back to the base, run one test, always restore, write a classified log) and `feature-report.py` (artifacts in, `report.md` out) — plus one extension of `shakeout-check.py` (a new row needs an assertion-failure revert log). The shake-out agent and command use them; netdust-devops gains `make shakeout` (the check) and `make report`; the policy, the reviewers' prompts and the plan reviewer get the order, the caps and the slice rule.

**Tech Stack:** Python 3 (stdlib), bash, Make; the plugins' own test runners.

**Spec:** `specs/gates-quality-loop/spec.md` (approved 2026-11-06). This plan covers R2, R4, R6, R7, R8, R9, R12, R13, R14, R15. Not here: **R10** (Studio artifact links) waits on a Studio change and is its own later plan; **R11** (the invariants gate tier) is plan 2 in wp-starter, and its drift-reviewer half is a small plan 3 here once that tier exists, so the agent never has two homes for its greps.

## Global Constraints

Not a WordPress project: the spec's own constraints.

- `revert-run` never commits, never pushes, never touches an untracked file it did not move itself, and restores the working tree in a trap on every exit, an interrupt included. It refuses to start when a non-test tracked file has uncommitted changes (they would be overwritten).
- The base is the merge-base of `HEAD` with production's branch: `scripts/site environments.production.branch` when the project has `scripts/site`, else `main`, else `master`.
- A revert log's first line is its classification, one of `revert-run: assertion-failed`, `revert-run: passed`, `revert-run: error`; `assertion-failed` needs a non-zero exit AND an assertion marker in the output (Playwright `expect(` with `Expected`/`Received`, PHPUnit `Failed asserting`); a timeout, an unmatched locator, a login or seeding error is `error`.
- `shakeout-check.py` requires, for every `browser` and `wire` row whose Evidence does not say `Re-driven`, `Revert: specs/<feature>/shakeout/<stem>.revert.log` naming an existing log classified `assertion-failed`; only `Accepted-by-human:` excuses a row.
- No evidence path may point outside the project (the session scratchpad, `/tmp`): screenshots and logs live under `specs/<feature>/shakeout/`.
- The Close order, written once in `skills/policy/SKILL.md`: `make gate` → `make review` → one fix pass → `/shakeout` then `make shakeout` → one shake-out fix round → `make report` → `make gate` (the stamp `promote` needs). Caps: plan review 2 rounds, coder 3 attempts per task, fix pass 1, shake-out fix round 1; a cap hit is a `Ruling:` and a stop for Stefan. `skills/policy/SKILL.md` stays under 150 lines (`tests/test_policy_skill.py`).
- `make shakeout name=X` and `make report name=X` read `commands.shakeout` / `commands.report` from `site.yml` and pass the name as `SHAKEOUT_NAME` / `REPORT_NAME`, the way `review` passes `REVIEW_NAME`; a missing key exits 1 with the line to add, as `review` does.
- Release: netdust-gates 0.19.0 and netdust-devops 0.15.0, each in `plugin.json`, the marketplace entry (both description heads) and, for devops, `dist/VERSION`; `tests/test-marketplace.sh` and the `dist/VERSION == plugin.json` assertion green. Merge and push are Stefan's.

## Risk model

`revert-run` is the one part that writes a working tree someone else owns (the coder's checkout).

1. **Uncommitted work is overwritten** by the base files → it refuses on any modified tracked non-test file, and names them.
2. **A crash leaves the tree on the base code**, and the next commit ships it → the restore runs in a `trap … EXIT INT TERM`; files added on the branch are moved aside and moved back, files deleted on the branch are restored from the base and removed again; a test kills the script mid-run and proves the tree is back (`git status --porcelain` empty, file hashes equal).
3. **A path with spaces or a leading dash** confuses `git checkout` → every path is passed after `--`, NUL-separated (`git diff -z`).
4. **The test command is a shell string from the agent** → it runs as given, in the project root; `revert-run` adds nothing to it. It is the agent's own command, the one its Test map row names.

## Simplest design

The simplest design for R2 is a second checkout (a git worktree with its own DDEV project). That needs Stefan's Windows UAC step for every new DDEV project (memory: a new DDEV project needs a hosts entry), so it cannot run unattended. Swapping only the changed non-test files in the one checkout, behind a trap, needs nothing new and is what the plan does. For R8 the simplest report is the shake-out manifest itself; it has no slices, no gaps and no link to the tests, so a small script that joins the plan, the manifest and the registry is the smallest thing that answers Stefan's question.

## First working version

Task 1: `bin/revert-run` swaps, runs and restores in a scratch repo and writes a classified log; the coder quotes one `assertion-failed` and one `passed` log from its test run.

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| `revert-run` | the script: exit code, log, the tree after | integration (scratch git repo) · `plugins/netdust-gates/tests/test_revert_run.py` · `bash plugins/netdust-gates/tests/run.sh test_revert_run.py` | none |
| `shakeout-check.py` revert rows and in-project paths | `check(spec_dir)` / the CLI exit | unit · `plugins/netdust-gates/tests/test_shakeout_check.py` · `bash plugins/netdust-gates/tests/run.sh test_shakeout_check.py` | none |
| `feature-report.py` | the CLI: `report.md` and the CHECKS.md trial line | unit (fixture feature dirs) · `plugins/netdust-gates/tests/test_feature_report.py` · `bash plugins/netdust-gates/tests/run.sh test_feature_report.py` | none |
| shake-out agent and command text | the prompt files | wiring · `plugins/netdust-gates/tests/test_close_wiring.py` (extended) · `bash plugins/netdust-gates/tests/run.sh test_close_wiring.py` | none |
| `make shakeout` / `make report` | the make targets | integration · `plugins/netdust-devops/tests/test-makefile.sh` · `bash plugins/netdust-devops/tests/run.sh` | none |
| policy, reviewers, evals, release | text, `evals/cases.json`, versions | `test_policy_skill.py`, `test_evals_shape.py`, `test-marketplace.sh` · `bash plugins/netdust-gates/tests/run.sh` | none |

## Review Focus

1. A crash or a Ctrl-C in `revert-run` leaves the coder's tree on the base code — Task 1 (`test_interrupt_restores_the_tree`).
2. A test that fails at login or setup on the base counts as "proven" — Task 1 (`test_setup_error_is_error_not_proof`), Task 2 (`test_error_log_does_not_prove_a_row`).
3. Uncommitted work overwritten by the swap — Task 1 (`test_refuses_on_a_modified_tracked_file`).
4. A file the branch added or deleted is left wrong after the run — Task 1 (`test_added_and_deleted_files_round_trip`).
5. A re-driven row forced to have a revert log, or a new row passing without one — Task 2.
6. `make promote` refusing after a correct Close because the last gate ran before the report's commit — the order in Task 6, and Task 5's help text.

---

### Task 1: `bin/revert-run`

**Files:**
- Create: `plugins/netdust-gates/bin/revert-run` (bash), `plugins/netdust-gates/tests/test_revert_run.py`

**Interfaces:**
- Produces: `revert-run <feature> <log-stem> -- <test command…>`, run from the project root. Writes `specs/<feature>/shakeout/<log-stem>.revert.log` (first line the classification, then the base sha, the swapped paths, the command and its output); exit 0 when the log was written (whatever the classification), 2 on refusal or a git error.

- [ ] **Step 1: Write the tests** in the suite's own style (read `test_shakeout_check.py` first for how the runner calls a test file), each building a scratch git repo with a `main` branch and a feature branch that changes `src/a.txt`, adds `src/new.txt`, deletes `src/old.txt` and adds `tests/t.sh`: `test_feature_present_test_fails_on_base_is_assertion_failed` (the test command greps `src/a.txt` for the feature line and prints `Failed asserting that` when it is missing); `test_test_that_passes_on_base_is_passed`; `test_setup_error_is_error_not_proof` (non-zero exit, no assertion marker); `test_added_and_deleted_files_round_trip` (during the run `src/new.txt` is absent and `src/old.txt` present; after it, the reverse, and `git status --porcelain` is empty); `test_refuses_on_a_modified_tracked_file` (exit 2, the file named, nothing swapped); `test_interrupt_restores_the_tree` (the test command sleeps; the test sends SIGINT; afterwards the tree equals HEAD byte for byte); `test_paths_with_spaces_and_dashes` (a file `src/-x y.txt` changed on the branch round-trips); `test_tests_and_specs_are_never_swapped`.
- [ ] **Step 2: Run** `bash plugins/netdust-gates/tests/run.sh test_revert_run.py`. Expected: FAIL (no script).
- [ ] **Step 3: Write `revert-run`:** base via the Global Constraints rule; the changed non-test paths via `git diff -z --name-status <base>...HEAD` excluding `tests/` and `specs/`; refuse on `git status --porcelain` showing a modified tracked file in that set; move added files aside to a `mktemp -d`, `git checkout <base> -- <modified and deleted paths>`, run the command, classify, write the log; the restore (`git checkout HEAD -- <paths>`, move the added files back, remove the base-only files) in one function the trap calls.
- [ ] **Step 4: Run** the test file (GREEN), then `bash plugins/netdust-gates/tests/run.sh` (all green). Quote both, and one `assertion-failed` and one `passed` log. Commit: `feat(gates): revert-run — a new test is run on the base code, the tree always restored`.

### Task 2: `shakeout-check.py` checks the revert proof and in-project paths

**Files:**
- Modify: `plugins/netdust-gates/bin/shakeout-check.py`, `plugins/netdust-gates/tests/test_shakeout_check.py`

**Interfaces:**
- Consumes: the log format of Task 1.
- Produces: findings named `shakeout-revert` (one per new row: pass, or fail with the reason) and `shakeout-paths` (fail when an Evidence path is absolute or leaves the project).

- [ ] **Step 1: Tests first:** `test_new_browser_row_with_assertion_failed_log_passes`; `test_new_wire_row_without_revert_fails`; `test_error_log_does_not_prove_a_row`; `test_passed_log_does_not_prove_a_row`; `test_redriven_row_needs_no_revert_log`; `test_accepted_by_human_excuses_a_missing_revert`; `test_scratchpad_screenshot_path_fails` (Evidence `Browser: http://x · /tmp/claude-1000/…/a.png`); `test_cli_row_needs_no_revert` (layer `cli`). Run the file: RED, quoted.
- [ ] **Step 2: Implement** in the existing shape (`_row_problem` gains the revert rule for `browser`/`wire`; a path helper rejects absolute or `..` paths and anything outside `spec_dir`'s project). Run: GREEN; whole suite green. Quote. Commit: `feat(gates): shakeout-check requires an assertion-failure revert log for every new e2e row`.

### Task 3: The shake-out uses it

**Files:**
- Modify: `plugins/netdust-gates/agents/shakeout-qa.md`, `plugins/netdust-gates/commands/shakeout.md`, `plugins/netdust-gates/tests/test_close_wiring.py`

- [ ] **Step 1: Wiring tests first** (the file's existing style): the agent prompt names `revert-run` with its `-- <test command>` form, the `Revert:` evidence and the `Re-driven` marker; it names `specs/<feature>/shakeout/<name>.png` as the capture path and forbids the scratchpad; the command's Step 3 runs `make shakeout name=<feature>` when the project has the verb, else the checker by path. RED quoted.
- [ ] **Step 2: Edit the two files:** after a NEW test passes on the feature, run `revert-run` with that test's command and record `Revert: …` in its row; a re-driven row says `Re-driven` and gets no revert run; screenshots are captured straight to the committed path; slices append rows to the one `shakeout.md`; the hunt runs once, at the feature's end. GREEN; suite green. Commit: `feat(gates): the shake-out proves each new test on the base and keeps its screenshots in the repo`.

### Task 4: `bin/feature-report.py`

**Files:**
- Create: `plugins/netdust-gates/bin/feature-report.py`, `plugins/netdust-gates/tests/test_feature_report.py`, fixtures under `plugins/netdust-gates/tests/fixtures/report/`

**Interfaces:**
- Produces: `feature-report.py specs/<feature>` writes `specs/<feature>/report.md` (one section per slice, read from `### Task N · Slice M: …` headings, a plan with none is one section; per section: what was built (the task titles), and each flow from the Test map's E2E column with its test file, its `@e2e` row in `specs/CHECKS.md`, its screenshot and its revert log from `shakeout.md`; a flow with no test, or a test with no revert log, is a named gap); a `Close: <minutes>` line from the commit times of the first `make review` report to now; and one appended line in `specs/CHECKS.md` under `## Trial log`: `<date> <feature> · revert-fails: <n> · report-gaps: <n>`. Exit 0, or 1 when the plan is missing.

- [ ] **Step 1: Tests first** with fixture feature dirs: a two-slice plan, a manifest with one flow lacking a revert log, a CHECKS.md: `test_two_slices_two_sections`, `test_missing_revert_is_a_named_gap`, `test_unsliced_plan_is_one_section`, `test_trial_line_appended_once_per_run_date`, `test_reads_artifacts_only` (no field filled when an artifact lacks it: the cell says `missing`). RED quoted.
- [ ] **Step 2: Implement** with the stdlib only. GREEN; suite green. Commit: `feat(gates): feature-report.py — the feature report generated from plan, manifest and registry`.

### Task 5: `make shakeout` and `make report`

**Files:**
- Modify: `plugins/netdust-devops/dist/Makefile.netdust` (two targets after `review`; `help` lines; `doctor`'s expected `commands.*` keys), `plugins/netdust-devops/templates/site.yml.tmpl` (the two commented keys, e.g. `shakeout: python3 "$HOME/.claude/plugins/netdust-gates/bin/shakeout-check.py" "specs/$SHAKEOUT_NAME"` and `report: python3 "$HOME/.claude/plugins/netdust-gates/bin/feature-report.py" "specs/$REPORT_NAME"`), `plugins/netdust-devops/tests/test-makefile.sh`

- [ ] **Step 1: Tests first:** a fixture `site.yml` with both keys pointing at a stub that records its env: `make shakeout name=x` runs it with `SHAKEOUT_NAME=x`; without the key it exits 1 and prints the line to add; `make report name=x` likewise; `make shakeout` without a name exits 1 with the usage; the template carries both keys (the existing every-expected-key check grows). RED quoted.
- [ ] **Step 2: Implement** in `review`'s shape (name check, read the key, refuse with the doctor line, export the name, run). GREEN; `bash plugins/netdust-devops/tests/run.sh` green. Commit: `feat(devops): make shakeout (the check) and make report`.

### Task 6: Policy, reviewers, plan reviewer, evals, release

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md` (the Close as the Global Constraints order and caps; the slice rule in one line under The plan; nothing restated elsewhere; stay under 150 lines), `plugins/netdust-gates/commands/feature-review.md` and `plugins/netdust-gates/agents/security-sentinel.md`, `agents/invariant-auditor.md` (R4's one line each), `plugins/netdust-gates/agents/plan-reviewer.md` (judges a layer-shaped slice as a finding), `plugins/netdust-gates/skills/policy/wordpress.md` (R12's sentence), `plugins/netdust-gates/CLAUDE.md` (R15's removal rule beside the shake-out hunt's), `plugins/netdust-gates/evals/cases.json` (R13's two cases), versions (Global Constraints)

- [ ] **Step 1:** Edit the texts; run `bash plugins/netdust-gates/tests/run.sh` (incl. `test_policy_skill.py` under 150 lines and `test_evals_shape.py`), `bash plugins/netdust-devops/tests/run.sh`. Quote the final lines.
- [ ] **Step 2:** Bump versions as the Global Constraints say. Run both suites again; quote. Commit: `release: netdust-gates 0.19.0, netdust-devops 0.15.0 — revert proof, feature report, the Close as make verbs`. Push the branch; do not merge.

## Hand-over

Stefan merges and pushes, then `scripts/sync.sh`; projects get the verbs through `make devops-update` (the updater replaces itself since 0.14.1) and add the two `commands.*` lines `make doctor` names. The first planned WordPress feature after this exercises the full Close. Plan 2 (wp-starter, R11's tier) and plan 3 (the drift reviewer's half) follow; R10 waits on Studio.
