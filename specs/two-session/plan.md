# Two sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native, the default inside a coder session) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A planned netdust-gates feature runs as two sessions. The session Stefan talked to thinks and reviews; a coder session executes in its own worktree. Stefan is asked only at the stops.

**Architecture:**
- **The rule** lives in the policy skill's Execution mode and Stops sections, together with the fallback outside herdr.
- **The mechanics** inside herdr (spawn, brief, watch, review, restart, close) live in `netdust-core:herdr-orchestration` as **the pair recipe**. That is the one name both skills use.
- **The DDEV-per-worktree rule** lives in `netdust-devops:parallel-work`.
- **The eval runner** builds every child environment itself: no inherited `HERDR_*`, a dead sandbox socket, and an optional stub `herdr` that really shadows the binary. So no eval can reach the live herdr server.
- **`/feature-review`** reads the plan from the reviewed branch, so a reviewer in another checkout still reviews against the plan.
- **First working version:** Task 1, the policy rule and its pinned test. After it, a session entering `netdust-gates:policy` reads the two-session rule. No eval runs before Task 2 has made the runner safe.

**Tech Stack:** Markdown skills, Python 3 tests (`tests/run.sh`), the `claude` CLI evals (`evals/run-evals.py`), bash tests for netdust-devops.

**Spec:** `specs/two-session/spec.md`

## Global Constraints

- **The policy's size.** The policy skill stays at most 149 lines (`plugins/netdust-gates/tests/test_policy_skill.py:42` requires `< 150`). It is 142 today, so Execution mode and Stops together grow by at most 7 lines. To fit R5 and R8 completely, tighten other wording in the policy, never remove a rule. The mechanics go to the pair recipe.
- **The growth rule** (`plugins/netdust-gates/CLAUDE.md`). This is a spec amendment plus eval cases: no plan section, no check on plan grammar.
- **No restating superpowers.** A netdust skill restating superpowers is a defect. The coder runs upstream's executor unchanged, and gates ships no implementer prompt, no reviewer rubric and no review rounds (spec R10).
- **An eval case per behaviour change.** A lesson that changes a skill's behaviour ships with an eval case (global `CLAUDE.md` §8).
- **The source repo only.** Edit it, never the plugin cache (`~/.claude/plugins/cache/`).
- **Version bumps.** Bump each plugin once, and bump `.claude-plugin/marketplace.json` in the same commit as its `plugin.json`: `test_plugin_manifest.py:22-24` and `test-marketplace.sh:33-42` fail on any drift between the two.
  - **gates:** `0.11.0`.
  - **devops:** `0.9.6`.
  - **core:** `0.5.4`. The main checkout's uncommitted netdust-core `plugin.json` already claims `0.5.4` for discovery-briefing, so the report names the collision: whichever merges second takes `0.5.5`.
  - **Descriptions:** each description gains its version's one-line summary in front, in the existing style.
- **Hands off the main checkout.** `main` of `/home/ntdst/Projects/netdust-plugins` carries another session's uncommitted files. This branch is cut from `origin/main` in its own worktree, and the main checkout is never touched.
- **Requirement numbers.** Every requirement's wording comes from `specs/two-session/spec.md`. Quote its R-numbers in commit messages.
- **No eval before the safe runner.** No eval (`run-evals.py`) runs before Task 2's runner changes are committed.
- **The guard's environment.** Every run of the gates suite is `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh`: Stefan's `~/.claude/settings.json` sets `NETDUST_GUARD_ASK=off` for every session, and `tests/test_pretooluse_guard.py:66` passes the environment to the hook, which then waives its ask tier (22 assertions red). Never edit that test or the hook for it.

## Review Focus

1. **An eval run inside herdr reaching the live herdr server** (spec R11): the runner must give every child its own environment. Specifically: no inherited `HERDR_*`; `HERDR_SOCKET_PATH` inside the sandbox; with a stub, a `herdr` that resolves to the stub in the session's own login-shell Bash; and no route to a named session's socket (`~/.config/herdr/sessions/<name>/herdr.sock`) through `--session`, `--machine` or `--remote`. → Test map row 2: `test_evals_shape.py` through `child_env`, and a resolution probe inside `run_case` that refuses to start a case when `herdr` does not resolve to the stub.
2. **A coder starting a coder** (spec R4): the brief's `Role: coder` must stop recursion. → Test map row 2, eval `coder-brief-no-recursion`.
3. **A reviewer in another checkout reviewing with no plan** (spec R7): `/feature-review` must read the plan at the reviewed head. → Test map row 1, the command test.
4. **The policy outgrowing its cap, or restating upstream.** → Test map row 1, `test_policy_skill.py`.
5. **Stale offers of the execution-mode choice** in the three plugins. This is an absence; the repo has no `ARCHITECTURE-INVARIANTS.md`, so Task 1 Step 3's grep is the check, its output quoted.
6. **A coder's `make gate` testing the main checkout** (spec R3): the main checkout's DDEV container, or main URLs left in the worktree's database or `.env`. → Test map row 4, a documentation unit. Its proof for the first WordPress pair, which this plan does not run: `ddev wp option get home` in the worktree prints the worktree's URL.

## Simplest design

- **The simplest version:** one paragraph in the policy telling the session to start a coder through herdr.
- **What it would break:**
  - An eval started inside herdr could drive panes on the live server (R11).
  - A coder could start its own coder (R4).
  - The reviewer's `/feature-review` would run without the plan (R7).
  - On a WordPress project, `make gate` would test the main checkout's container (R3).
- **What this plan adds:** that paragraph, the pair recipe and its scenario (R4 requires the mechanics somewhere), and the pieces that close those four holes:
  - the role line;
  - the runner's environment;
  - one clause in `feature-review.md`;
  - the DDEV section.
- **Where it stops:** no new skill, no `make feature worktree=`, no `flock` (spec "Out of scope").

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| 1. The policy rule: Execution mode, Stops, fallback, boundary, spec amendment, `/feature-review` reading the plan at head, gates version | `plugins/netdust-gates/skills/policy/SKILL.md` and `commands/feature-review.md` as a session reads them | unit · `plugins/netdust-gates/tests/test_policy_skill.py` and `tests/test_close_wiring.py` (`:55-58` already reads `feature-review.md`; `test_session_commands.py:7` says prose is not string-tested there) · `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` | — |
| 2. The eval runner and the two cases | `child_env(case, base, root) -> dict` and `prepare_sandbox(case, root) -> None` in `plugins/netdust-gates/evals/run-evals.py`; the CLI `python3 plugins/netdust-gates/evals/run-evals.py <case-id> ...` | unit · `plugins/netdust-gates/tests/test_evals_shape.py`, loading `run-evals.py` through `importlib` · `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh`; behavioural · `python3 plugins/netdust-gates/evals/run-evals.py two-session-handoff coder-brief-no-recursion`. A `0/0 cases passed` line means a wrong invocation, never a pass. | — |
| 3. The pair recipe | `plugins/netdust-core/skills/herdr-orchestration/SKILL.md` | judged paper scenario · `plugins/netdust-core/skills/herdr-orchestration/evals/scenario-6-{baseline,skill-on,judge.template}.md` · dispatch the baseline and skill-on legs as two general-purpose subagents, inline both outputs into the judge template and dispatch a judge. It passes when the skill-on leg passes every rule from H29 on and the baseline fails at least one (the procedure of `plugins/netdust-core/evals/RUNBOOK.md:17-38`). Its outputs stay in the session scratchpad or the report, never `RUNBOOK.md`'s outputs path, which resolves into the plugin cache. | — |
| 4. DDEV project per coder worktree | `plugins/netdust-devops/skills/parallel-work/SKILL.md` | none — documentation; proven by the first WordPress pair · `bash plugins/netdust-devops/tests/run.sh` stays green | — |

## Tasks

### Task 1: The policy rule (first working version)

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md` (`## Execution mode`, `## Stops`)
- Modify: `plugins/netdust-gates/commands/feature-review.md` (`:25`, the plan is read at `<head>`: `git show <head>:specs/<name>/plan.md`, falling back to the working tree)
- Modify: `plugins/netdust-gates/commands/plan-review.md` (`:42`, if it still offers the execution-mode choice)
- Modify: `plugins/netdust-gates/CLAUDE.md` (Boundaries, the R10 sentence)
- Modify: `specs/netdust-gates/spec.md` (amendment lines under R3 `:68` and R5 `:81`, pointing at `specs/two-session/spec.md`, as test-mapping's amendment under R1 did, commit `5c01115`)
- Modify: `plugins/netdust-gates/.claude-plugin/plugin.json` (0.11.0) and `.claude-plugin/marketplace.json` (gates entry)
- Test: `plugins/netdust-gates/tests/test_policy_skill.py`, and the command test that reads `feature-review.md`

**Interfaces:**
- Produces: the policy names "the pair recipe" in `netdust-core:herdr-orchestration` (Task 3 creates it under that name). It also states the fallback outside herdr: one background subagent coder, Native, in the worktree, continued over SendMessage, keeping the same ledger of every exchange (R9). Until Task 3 lands on this branch, the policy names a recipe that does not exist yet; that is expected inside the branch.

- [ ] **Step 1:** add assertions to `test_policy_skill.py`:
  - the policy contains `Role: coder`, `netdust-core:herdr-orchestration` and "the pair recipe";
  - the text between `## Stops` and `## Close` names no execution-mode choice;
  - "chooses at the plan handoff" is gone;
  - the file is at most 149 lines.

  Add an assertion to the command test: `feature-review.md` reads the plan at `<head>`.

  Run `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh`. Expected red: the new content assertions and the command one fail (`SKILL.md:98` says "Stefan chooses at the plan handoff", `:106` names the "execution-mode choice"). The existing `< 150` line check stays; don't add a second. Quote the red as it prints.
- [ ] **Step 2:** rewrite `## Execution mode` and `## Stops` to spec R1–R8, within the size constraint, including "A coder asks its reviewer, never Stefan" and R8's full list. Keep every token other tests pin in Stops: "flow list", "(Close, step 4)", `Ruling:`, `Accepted-by-human:`. R8's sentence "the execution-mode choice is no longer a stop" goes in Execution mode, not Stops, so Step 1's Stops assertion pins the offer and not that sentence. The `commands/plan-review.md` rewrite must not say "implementer" (`test_close_wiring.py:8-9`'s stale list). The sparring draft in `specs/two-session/sparring-draft.md` is a starting point, not the text.

  Then make the remaining Task 1 edits:
  - the `feature-review.md` clause;
  - the R10 sentence in `CLAUDE.md`;
  - the amendment lines in the spec;
  - both version files.
- [ ] **Step 3:** grep for stale offers across the three plugins:
  `grep -rn -i -e 'execution.mode' -e 'native by default' -e 'Native\*\* by default' -e 'plan handoff' -e 'which approach would you prefer' plugins/netdust-gates plugins/netdust-core plugins/netdust-devops`.
  Fix each hit that still offers Stefan the choice, and quote the grep before and after in the report.
- [ ] **Step 4:** `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` all green; commit (`feat(gates): two sessions — spec R1–R8, R10`).

### Task 2: The eval runner and the two cases

**Files:**
- Modify: `plugins/netdust-gates/evals/run-evals.py`
- Modify: `plugins/netdust-gates/evals/cases.json`
- Create: `plugins/netdust-gates/evals/stubs/herdr`, committed executable (mode 100755)
- Test: `plugins/netdust-gates/tests/test_evals_shape.py`

**Interfaces:**
- Produces:
  - `child_env(case: dict, base: dict, root: Path) -> dict`:
    - removes every `HERDR_`-prefixed and every `CLAUDE_CODE_MESSAGING_`-prefixed key from `base`, so no child can reach a live herdr server or a live Claude session;
    - sets `HERDR_SOCKET_PATH` to a path under `root` where nothing listens;
    - sets `EVAL_ROOT` to `root`;
    - applies the case's `env`;
    - with `stub_bin`, makes the stub the `herdr` the session's Bash resolves, and sets `HERDR_BIN_PATH` to it.
  - `prepare_sandbox(case: dict, root: Path) -> None`: writes the case's files. With `commit: true`, it makes one commit on `main`, then checks out `feature/<case-id>` (or the case's `branch` key), so a coder that follows `superpowers:executing-plans` is not on a main branch.
  - New optional case keys:
    - `env` (object);
    - `stub_bin` (path relative to `evals/`);
    - `commit` (bool);
    - `allow` (list of tool rules, passed as `--allowedTools`; under `-p --permission-mode acceptEdits` an unlisted Bash command is denied, not prompted);
    - `max_turns` (int; replaces the hard-coded `--max-turns 25` for that case).
    - `branch` (string; with `commit: true`, the branch the sandbox ends on).
    - `timeout` already exists; use it.

- [ ] **Step 1:** in `test_evals_shape.py`, load `run-evals.py` with `importlib` and assert:
  - `child_env` leaves no inherited `HERDR_` value;
  - it puts `HERDR_SOCKET_PATH` under `root`;
  - it applies the case's `env`;
  - under `child_env(...)` with `stub_bin`, a login-shell `bash -lc 'command -v herdr'` prints the stub's path (the probe itself, not a statement about `PATH`);
  - `prepare_sandbox` with `commit: true` leaves a valid `HEAD`;
  - every case's keys are within the known set;
  - the two new case ids exist.

  Run `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh`; it fails (no such functions yet).
- [ ] **Step 2:** implement the runner functions and the stub. The stub:
  - appends its argument vector (and, for `agent prompt`, the text) to `$EVAL_ROOT/.herdr/calls.log`;
  - on `worktree create`, runs a real `git worktree add` under `$EVAL_ROOT` and prints a minimal JSON with that path, one workspace and one root pane id; on `api snapshot`, prints the same workspace and pane;
  - on `agent start`, touches `$EVAL_ROOT/.herdr/agent-start`;
  - contacts no server.

  herdr 0.9.5's shape is `agent start <NAME> --kind <KIND> --pane <ID> [-- AGENT_ARG…]`, and the prompt is a separate `agent prompt <TARGET> <TEXT>`.

  **Prove the shadowing:** one probe, quoted in the report, showing that under `child_env(...)` a login-shell `bash -lc 'command -v herdr'` resolves to the stub. `~/.profile:25-26` prepends `~/.local/bin` in a login shell, so a plain `PATH` prefix is not enough. Choose a mechanism that survives it, and say which.

  **Make the guard permanent:** `run_case` runs the same probe before every case that sets `stub_bin`, and refuses to start the case when it fails. Every case passes `--disallowedTools` for `Bash(herdr --session*)`, `Bash(herdr --machine*)`, `Bash(herdr --remote*)` (and their forms with the flag after a subcommand), `Bash(HERDR_*)` (an inline `HERDR_SESSION=<name> herdr …`), `SendMessage` and `ListAgents`, because a named session has its own socket and `Bash(herdr *)` would allow it. **Confirm by probe**, quoted in the report, that the real client with `HERDR_SOCKET_PATH` pointing at nothing fails rather than starting or reaching a server (`herdr --skill` does not document the variable). The stub also answers `agent wait` with a settled state.

  **Add both cases** with `allow: ["Bash(herdr *)", "Bash(git *)"]`, a `timeout` (`unit-cut-plan` needed 2700 s), and checked `--max-turns` headroom:
  - **`two-session-handoff`** (`commit: true`, `env: {"HERDR_ENV": "1"}`, the stub): an approved one-task plan. Expect `calls.log` to show `agent start`, and `Role: coder`, the plan path and `netdust-gates:policy` anywhere in it (a brief may travel as `-- AGENT_ARG` on `agent start` or through `agent prompt`). Expect the target file unchanged, and the reply with no execution-mode question.
  - **`coder-brief-no-recursion`** (`commit: true`, `env: {"HERDR_ENV": "1"}`, the stub, the same `allow`): a prompt opening `Role: coder` with a one-task plan. Expect the target changed, and no `.herdr/agent-start`. Only the stub writes that file, so the case can fail.
- [ ] **Step 3:** `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` green. Run `python3 plugins/netdust-gates/evals/run-evals.py two-session-handoff coder-brief-no-recursion` once and quote the result lines. The pair counts as passed only when `two-session-handoff`'s `calls.log` shows the stub was called in the same run. The `bash -lc` probe is a proxy for the Bash tool's shell, and without that log the no-recursion absence check could pass vacuously.

  Reading a failure: this eval loads netdust-core from the cache (0.5.2, which has no pair recipe), may see the installed gates 0.10.0 beside `--plugin-dir` (unverified which one takes precedence), and runs under Stefan's global `CLAUDE.md` §2, which still offers the execution-mode choice until R12 is applied. Upstream `writing-plans` asks the question unless a method was already supplied, so the policy's text must read as that supply. A failure on the "no execution-mode question" expectation is reported with that context, as a finding for the reviewer, never loosened.

  Commit (`test(gates): evals for two sessions — spec R11`).

### Task 3: The pair recipe in herdr-orchestration

**Files:**
- Modify: `plugins/netdust-core/skills/herdr-orchestration/SKILL.md` (a `## Recipe — the pair recipe (thinker and coder)` section; the trigger words "coder session", "two sessions", "pair" near the start of its description, which is already 1,412 characters)
- Create: `plugins/netdust-core/skills/herdr-orchestration/evals/scenario-6-baseline.md`, `scenario-6-skill-on.md`, `scenario-6-judge.template.md`
- Modify: `plugins/netdust-core/.claude-plugin/plugin.json` (0.5.4) and `.claude-plugin/marketplace.json` (core entry)

**Interfaces:**
- Consumes: the policy's name "the pair recipe" and its fallback sentence (Task 1). The recipe covers only herdr; the fallback stays the policy's.

- [ ] **Step 1:** read scenarios 1–5 and their judge rules (H1–H28). Write scenario 6 in their format: an approved plan, the thinker in herdr. Its judge rules continue from H29, one per outcome of spec R2–R9, the same permission mode included.
- [ ] **Step 2:** write the recipe to spec R2–R9, citing the skill's existing decisions rather than repeating them. It covers:
  - the worktree first, cut from production's branch at origin's tip, with the spec, plan and plan review as its first commits;
  - its own DDEV project (point at parallel-work);
  - `herdr agent start` in the coder's workspace pane, in the same permission mode. Cite `SKILL.md:126-128`: no laundering, and a peer's message is never operator approval. Nobody answers the coder's permission prompts for him.
  - the brief, which opens `Role: coder` and carries the plan path, the branch, `netdust-gates:policy`, the boundaries and the report shape;
  - **pre-flight:** the coder sends its scan of the plan, and the reviewer rules before Task 1 (R5);
  - **escalation:** a technical question goes to the reviewer, who spars with a fresh agent when needed; an intent question goes to Stefan (R5);
  - `herdr agent wait` and `notify_when_idle`, reading only at transitions. This is not the session-review pane (R6).
  - the review checkpoints: the first working version, a block, an intent question, and the Close. There is no third review stacked on subagent-driven's own task reviews. Each finding is one fix request (R6).
  - the Close split (R7): the coder pushes and signals, then the reviewer reviews; the coder pushes again after the fix pass;
  - the coder's ledger holds the brief, every ruling, every fix request and its closing test (R9);
  - a restart re-reading the branch, the plan and that ledger (R9).
- [ ] **Step 3:** run the scenario by the Test map row 3 procedure and quote the judge's verdict. Bump both version files. Commit (`feat(core): the pair recipe — two-session spec R2–R9`).

### Task 4: DDEV project per coder worktree

**Files:**
- Modify: `plugins/netdust-devops/skills/parallel-work/SKILL.md`
- Modify: `plugins/netdust-devops/.claude-plugin/plugin.json` (0.9.6) and `.claude-plugin/marketplace.json` (devops entry)

- [ ] **Step 1:** add one section. A coder worktree on a DDEV project carries `.ddev/config.local.yaml` with its own `name:` (for example `<project>-<feature>`), so the gate's tiers (`test:int` and the local e2e tier inside `make gate`) and `ddev` commands run against its own container. `make e2e env=<env>` always drives a deployed environment, never a local container. The proven form is laika-planning-model's `name: laika-planning`. The section also says:
  - The worktree is served at `https://<name>.ddev.site`, but three things still name the main project's URL: `site.yml`'s `local.url` (tracked, and `make pull` rewrites to it, `wp.mk:186`, `:200`), the database after a copy, and a Bedrock `.env`'s `WP_HOME`/`WP_SITEURL`. So: set the worktree's `.env` to its own URL. Seed from the main project with `ddev export-db` there and `ddev import-db` here, then `ddev wp search-replace <main url> <worktree url>`. Never run `make pull` in a worktree without that rewrite. Record as a `Ruling:` that seeding goes beyond R3's wording, because the gate's browser tier reads its URLs from WordPress (laika `bin/e2e.sh:55`).
  - The proof for the first pair: in the worktree, `ddev wp option get home` prints the worktree's URL.
  - How the worktree's project is started.
  - Removing it when the feature lands deletes its database, so it asks first.
- [ ] **Step 2:** `bash plugins/netdust-devops/tests/run.sh` green; bump both version files; commit (`docs(devops): a DDEV project per coder worktree — two-session spec R3`).

## Close

1. Both test runs are green: `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` and `bash plugins/netdust-devops/tests/run.sh`. The latter also checks netdust-core's manifest through `test-marketplace.sh`; netdust-core has no `tests/`.
2. The coder pushes `feature/two-session` and tells the reviewer. The reviewer session then runs the feature review by **the branch's own text** of the command (`git show origin/feature/two-session:plugins/netdust-gates/commands/feature-review.md`). Its own `/feature-review` loads gates 0.10.0 from the cache, which lacks Task 1's clause, and its checkout has no `specs/two-session/`. It checks that the summary's "plan or none" line names the plan. The coder makes one fix pass, each fix RED→GREEN, and keeps the review as `specs/two-session/review.md`.
3. After the fix pass the coder pushes again. The PR and the merge are Stefan's. The reviewer hands him the global `CLAUDE.md` §2 replacement text (spec R12) and the netdust-core version-collision note.
