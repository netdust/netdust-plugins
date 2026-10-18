# Two sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native, the default inside a coder session) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A planned netdust-gates feature runs as two sessions. The session Stefan talked to thinks and reviews; a coder session executes in its own worktree. Stefan is asked only at the stops.

**Architecture:**
- **The rule** lives in the policy skill's Execution mode and Stops sections: about 11 lines, under the 150-line cap.
- **The mechanics** (spawn, brief, watch, review, restart, close, fallback) live in `netdust-core:herdr-orchestration` as a pair recipe.
- **The DDEV-per-worktree rule** lives in `netdust-devops:parallel-work`.
- **The eval runner** stops inheriting `HERDR_*`, so the new cases cannot drive the live herdr server.
- **First working version:** Task 1 (the policy rule and its pinned test). After it, a session entering `netdust-gates:policy` on any project reads the two-session rule.

**Tech Stack:** Markdown skills, Python 3 tests (`tests/run.sh`), the `claude` CLI evals (`evals/run-evals.py`), bash tests for netdust-devops.

**Spec:** `specs/two-session/spec.md`

## Global Constraints

- The policy skill stays under 150 lines (`plugins/netdust-gates/tests/test_policy_skill.py:42`). The Execution mode body is at most 11 lines; mechanics go to herdr-orchestration.
- The growth rule (`plugins/netdust-gates/CLAUDE.md`): this is a spec amendment plus eval cases. It adds no plan section and no check on plan grammar.
- A netdust skill restating superpowers is a defect. The coder runs upstream's executor unchanged, and gates ships no implementer prompt, no reviewer rubric and no review rounds (spec R10).
- A lesson that changes a skill's behaviour ships with an eval case (the global `CLAUDE.md` §8).
- Edit the source repo only, never the plugin cache (`~/.claude/plugins/cache/`).
- `main` of `/home/ntdst/Projects/netdust-plugins` carries another session's uncommitted files, among them `plugins/netdust-core/.claude-plugin/plugin.json`. This branch is cut from `origin/main` in its own worktree. Never touch the main checkout; name the merge conflict on netdust-core's `plugin.json` in the report.
- Bump the version once per plugin: gates `0.11.0`, core `0.5.4`, devops `0.9.6`. Each `plugin.json` description gains its version's one-line summary in front, in the existing style.
- Every requirement's wording comes from `specs/two-session/spec.md`; quote its R-numbers in commit messages.

## Review Focus

1. **A coder starting a coder** (spec R4): the brief's `Role: coder` must stop recursion. → Test map row 2, eval `coder-brief-no-recursion`.
2. **An eval run inside herdr spawning real panes** (spec R11): the runner must strip `HERDR_*`. → Test map row 2, `test_evals_shape.py`, plus eval `two-session-handoff` run with a stub `herdr`.
3. **The policy outgrowing its cap, or restating upstream:** → Test map row 1, `test_policy_skill.py`.
4. **Stale cross-references:** another skill, command or agent of the three plugins still offers "the execution-mode choice" or "Native by default" as Stefan's choice at the plan handoff. → Task 1 step 3's grep, its output quoted in the report.
5. **A coder's `make gate` testing the main checkout's DDEV container** (spec R3): → Test map row 4. It is a documentation unit, proven by the first WordPress pair, which this plan does not run.

## Simplest design

- **The simplest version:** one paragraph in the policy telling the session to start a coder through herdr.
- **Why it alone is not enough:** it would let an eval started inside herdr spawn panes on the live server (R11), and let a coder start its own coder (R4). On a WordPress project it would report `make gate` results from the main checkout's container (R3).
- **What this plan adds:** that paragraph plus the three pieces that close those holes: the role line, the runner's environment fix, and the DDEV rule. It stops there. There is no new skill, no `make feature worktree=` verb and no `flock` (follow-ups, spec "Out of scope").

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| 1. The policy rule (Execution mode, Stops, boundary, spec amendment, gates version) | `plugins/netdust-gates/skills/policy/SKILL.md` as a session reads it | unit · `plugins/netdust-gates/tests/test_policy_skill.py` (pins `Role: coder`, `netdust-core:herdr-orchestration`, no "execution mode" stop, under 150 lines) · `bash plugins/netdust-gates/tests/run.sh test_policy_skill.py` | — |
| 2. The eval runner and the two cases | `python3 plugins/netdust-gates/evals/run-evals.py` | unit · `plugins/netdust-gates/tests/test_evals_shape.py` (the case keys `env`, `stub_bin`, `commit`; the runner strips `HERDR_*`) · `bash plugins/netdust-gates/tests/run.sh`; behavioural · cases `two-session-handoff`, `coder-brief-no-recursion` · `python3 plugins/netdust-gates/evals/run-evals.py` (filter flag per the runner's own `--help`) | — |
| 3. The pair recipe | `plugins/netdust-core/skills/herdr-orchestration/SKILL.md` | judged paper scenario · `plugins/netdust-core/skills/herdr-orchestration/evals/scenario-6-{baseline,skill-on,judge.template}.md` · run as scenarios 1–5 are run (read one first) | — |
| 4. DDEV project per coder worktree | `plugins/netdust-devops/skills/parallel-work/SKILL.md` | none — documentation; proven by the first WordPress pair · `bash plugins/netdust-devops/tests/run.sh` stays green | — |

## Tasks

### Task 1: The policy rule (first working version)

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md` (sections `## Execution mode`, `## Stops`)
- Modify: `plugins/netdust-gates/CLAUDE.md` (Boundaries)
- Modify: `specs/netdust-gates/spec.md` (amendment lines under R3 and R5, pointing at `specs/two-session/spec.md`, as test-mapping's amendment under R1 did, commit `5c01115`)
- Modify: `plugins/netdust-gates/.claude-plugin/plugin.json` (0.11.0)
- Create: `specs/two-session/claude-md-section-2.md`, the replacement text for Stefan's `~/.claude/CLAUDE.md` §2 (spec R12)
- Test: `plugins/netdust-gates/tests/test_policy_skill.py`

- [ ] **Step 1:** in `test_policy_skill.py`, add the assertions: the policy contains `Role: coder` and `netdust-core:herdr-orchestration`; it does not contain "chooses at the plan handoff" or "execution-mode choice" as a stop; it stays under 150 lines. Run `bash plugins/netdust-gates/tests/run.sh test_policy_skill.py`; it fails on the first two.
- [ ] **Step 2:** rewrite `## Execution mode` and `## Stops` to spec R1–R8, at most 11 lines for the Execution mode body. The sparring draft at the laika session's `scratchpad/two-session/spar-1.md` §7 is a starting point, not the text. Add the R10 boundary sentence to `CLAUDE.md` and the amendment lines to the spec. Bump `plugin.json`. Write `claude-md-section-2.md`.
- [ ] **Step 3:** grep for stale offers across the three plugins: `grep -rn -i "execution mode\|native by default\|which approach would you prefer" plugins/netdust-gates plugins/netdust-core plugins/netdust-devops`. Fix each hit that still offers Stefan the choice, and quote the grep before and after in the report.
- [ ] **Step 4:** `bash plugins/netdust-gates/tests/run.sh` all green; commit (`feat(gates): two sessions — spec R1–R8, R10, R12`).

### Task 2: The eval runner and the two cases

**Files:**
- Modify: `plugins/netdust-gates/evals/run-evals.py`
- Modify: `plugins/netdust-gates/evals/cases.json`
- Create: `plugins/netdust-gates/evals/stubs/herdr` (an executable shell stub that appends its arguments, and the prompt text when there is one, to `.herdr/calls.log` in the case directory, and on `agent start` touches `.herdr/agent-start`; it contacts no server)
- Test: `plugins/netdust-gates/tests/test_evals_shape.py`

- [ ] **Step 1:** in `test_evals_shape.py`, assert:
  - every case's optional keys are within `{env, stub_bin, commit}` plus the existing ones;
  - `run-evals.py` removes every `HERDR_`-prefixed variable before it starts `claude`, read through the function that builds the child environment, not by grepping the source;
  - the two new case ids exist.

  The test fails.
- [ ] **Step 2:** implement the runner changes:
  - build the environment by stripping `HERDR_*`, then apply the case's `env`;
  - put `stub_bin` first on `PATH`;
  - with `commit: true`, make one commit in the sandbox.

  Add both cases with their assertions, per spec R11:
  - **`two-session-handoff`:** the log holds `agent start`, and a prompt with `Role: coder`, the plan path and `netdust-gates:policy`; the target file is unchanged; the reply asks no execution-mode question.
  - **`coder-brief-no-recursion`:** the target is changed, and there is no `.herdr/agent-start`.
- [ ] **Step 3:** `bash plugins/netdust-gates/tests/run.sh` green. Run the two cases with the runner's own filter, once each, and quote the result lines. A case that fails on behaviour is a finding for the reviewer, not something to loosen. Commit (`test(gates): evals for two sessions — spec R11`).

### Task 3: The pair recipe in herdr-orchestration

**Files:**
- Modify: `plugins/netdust-core/skills/herdr-orchestration/SKILL.md` (a `## Recipe — the thinker/coder pair` section, plus the trigger words "coder session", "two sessions", "pair" in its description)
- Create: `plugins/netdust-core/skills/herdr-orchestration/evals/scenario-6-baseline.md`, `scenario-6-skill-on.md`, `scenario-6-judge.template.md`
- Modify: `plugins/netdust-core/.claude-plugin/plugin.json` (0.5.4)

- [ ] **Step 1:** read scenarios 1–5 and write scenario 6 in their format: an approved plan, the thinker in herdr; the judge checks the recipe's outcomes.
- [ ] **Step 2:** write the recipe to spec R2–R9. It covers:
  - the worktree first, cut from production's branch at origin's tip, with the spec, plan and plan review committed as its first commits;
  - its own DDEV project (point at parallel-work);
  - `herdr agent start` in the coder's workspace pane, in the same permission mode;
  - the brief, which opens `Role: coder` and carries the plan path, the branch, `netdust-gates:policy`, the boundaries and the report shape;
  - `herdr agent wait` and `notify_when_idle`, reading only at transitions;
  - the review checkpoints (first working version, block, intent question, Close), one fix request per finding;
  - the Close split;
  - a restart re-reading the branch and the coder's ledger;
  - the fallback outside herdr: one background subagent coder, Native, continued over SendMessage.

  Keep the existing decisions intact; cite them, don't repeat them.
- [ ] **Step 3:** run scenario 6 the way the existing scenarios are run (their files say how), and quote the judge's verdict. Bump `plugin.json`. Commit (`feat(core): herdr pair recipe — two-session spec R2–R9`).

### Task 4: DDEV project per coder worktree

**Files:**
- Modify: `plugins/netdust-devops/skills/parallel-work/SKILL.md`
- Modify: `plugins/netdust-devops/.claude-plugin/plugin.json` (0.9.6)

- [ ] **Step 1:** add one section. A coder worktree on a DDEV project carries `.ddev/config.local.yaml` with its own `name:` (for example `<project>-<feature>`), so `make gate`, `make e2e` and `ddev` commands run against its own container. The proven form is laika-planning-model's `name: laika-planning`. The section also covers how the worktree's DDEV project is started, seeded from the main project's database by the project's own verb when one exists, and removed when the feature lands.
- [ ] **Step 2:** `bash plugins/netdust-devops/tests/run.sh` green; bump `plugin.json`; commit (`docs(devops): a DDEV project per coder worktree — two-session spec R3`).

## Close

1. All three plugins' test runs are green: `bash plugins/netdust-gates/tests/run.sh` and `bash plugins/netdust-devops/tests/run.sh`.
2. The reviewer session runs the feature review (`/feature-review two-session`) from its own checkout. The coder makes one fix pass, each fix RED→GREEN, and keeps the review as `specs/two-session/review.md`.
3. The coder pushes `feature/two-session`. Opening the PR and the merge are Stefan's. The reviewer hands him the global `CLAUDE.md` §2 text and the netdust-core `plugin.json` merge-conflict note.
