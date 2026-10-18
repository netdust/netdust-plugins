# Plan review — two-session
Reviewed-plan: e3c2f5dc926b395b909facff9bb68e771dbe9aab
Verdict: not ready

The plan gives each of R1–R12 a task. Four premises do not hold in the source or in the environment the evals run in. Each one needs a single line in the plan to fix. B2 matters most: the stub does not isolate the live herdr server, which is the exact failure R11 and Review Focus 2 exist to prevent.

## Blocking

**B1. The version bumps leave `marketplace.json` behind, so the "green" steps cannot be reached.**
- Plan: Global Constraints ("Bump the version once per plugin…"), Task 1 Files and Step 4 ("all green"), Task 3 Files and Step 3, Task 4 Files and Step 2.
- Source: `plugins/netdust-gates/tests/test_plugin_manifest.py:22-24` requires the marketplace entry's version to equal `plugin.json`. `plugins/netdust-devops/tests/test-marketplace.sh:33-42` fails on DRIFT for every plugin. `.claude-plugin/marketplace.json` still says gates 0.10.0, core 0.5.3, devops 0.9.5. Both suites are green today only because the two files agree.
- Change: add `.claude-plugin/marketplace.json` to the Files of each bumping task, bumped in the same commit as its `plugin.json`.

**B2. `stub_bin` first on PATH does not shadow the real herdr, and stripping `HERDR_*` points the real binary at the live server.**
- Plan: Task 2 Step 2 ("put `stub_bin` first on `PATH`"), Review Focus 2.
- Source, PATH: `~/.profile:25-26` prepends `~/.local/bin` in a login shell. Claude Code's Bash snapshot is a login-shell capture: the newest file in `~/.claude/shell-snapshots/` carries `/etc/profile.d`'s gawk functions and an `export PATH=` line (line 147), and no `.bashrc` interactive section. I ran `env PATH=<stub>:$PATH bash -lc 'echo $PATH'`: `~/.local/bin` came 1st, the stub 2nd.
- Source, binary and socket: `~/.local/bin/herdr` is the real 0.9.5 binary (`$HERDR_BIN_PATH`). This pane's `$HERDR_SOCKET_PATH` is `~/.config/herdr/herdr.sock`, the default path. Stripping it leaves the real client on that same live socket.
- Effect: in `two-session-handoff` (`HERDR_ENV=1` re-added), the session's `herdr agent start` can reach the live server.
- Change: after stripping, the runner sets `HERDR_SOCKET_PATH` to a path inside the sandbox for every case (no server listens there). When `stub_bin` is set it also sets `HERDR_BIN_PATH` to the stub. Task 2 Step 1 asserts both on the child environment. Confirm from `herdr --skill` that API helpers fail, and do not start a server, when nothing listens on the socket.

**B3. The runner has no `--help` and no filter flag.**
- Plan: Test map row 2 ("filter flag per the runner's own `--help`"), Task 2 Step 3.
- Source: `plugins/netdust-gates/evals/run-evals.py:4` (`run-evals.py [case-id ...]`) and `:73`: the filter is positional case ids. `--help` (or `--filter x`) selects no case, prints `0/0 cases passed` and exits 0 (`:81-82`). That looks like a green run.
- Change: write the command, `python3 plugins/netdust-gates/evals/run-evals.py two-session-handoff coder-brief-no-recursion`, and say a `0/0` line means a wrong invocation.

**B4. Both new cases need Bash calls that `claude -p --permission-mode acceptEdits` denies.**
- Plan: Task 2 Step 2 (the two cases) and Step 3 ("a case that fails on behaviour is a finding… not something to loosen").
- Source: `run-evals.py:55-56` runs `claude -p` with `--permission-mode acceptEdits`. `SETTINGS` (`:23`) carries no permissions. `~/.claude/settings.json` and `settings.local.json` allow no `git` or `herdr` command.
- Effect: acceptEdits approves file edits, not `herdr …`, `git worktree add` or `git commit`. In print mode an unapproved call is denied, not prompted. None of the 12 existing cases runs Bash, so none has hit this. `two-session-handoff`'s core expectation (an `agent start` in `calls.log`) cannot appear. Step 3 would then report a permission denial as a behaviour failure.
- Change: give both cases' `files` a `.claude/settings.local.json` that allows `Bash(herdr *)` and `Bash(git *)`; this does not overwrite the runner's `settings.json`. The alternative is a per-case `allow` key passed as `--allowedTools`, added to Step 1's key whitelist.

## Should fix

**S1. The fallback outside herdr is homed in a skill that says it does not apply outside herdr.**
- Plan: Architecture bullet 2 ("…close, fallback) live in `netdust-core:herdr-orchestration`") and Task 3 Step 2's last bullet.
- Source: `plugins/netdust-core/skills/herdr-orchestration/SKILL.md:13` says "Outside herdr, none of this applies", and the description (`:3`) triggers on `HERDR_ENV=1`.
- Change: the policy (Task 1) carries the fallback's operative sentence. The sparring draft in `spar-1.md` §7 already has "else as one background subagent there". Task 3 either drops the bullet or amends `:13` to carve out the pair recipe's fallback.

**S2. The reviewer's review, run from its own checkout, silently loses the plan.**
- Plan: Close step 2 (`/feature-review two-session` "from its own checkout"), Task 3 Step 2 ("the Close split").
- Source: `plugins/netdust-gates/commands/feature-review.md:12-13` resolves head to `origin/feature/<name>`, else the local branch, which works from any checkout. But `:25` ("When `specs/<name>/plan.md` exists…") reads the working tree. Under R2 the plan exists only on `feature/<f>`; the main checkout at 5915dca has no `specs/two-session/`. So R7's review runs as a review with no plan: no requirements, no Review Focus, no threat model. It does this in this very pilot.
- Change: Task 1 adds one clause to `feature-review.md:25` (read the plan at `<head>`, i.e. `git show <head>:specs/<name>/plan.md`) and pins it in an existing command test.

**S3. Task 3's recipe list and scenario 6 skip parts of R5 and R6.**
- Plan: Task 3 Step 2's bullets; Step 1 says only "the judge checks the recipe's outcomes".
- Missing from the bullets:
  - R5's pre-flight ruling before Task 1;
  - R5's escalation split: technical questions go to the reviewer, who spars with a fresh agent; intent questions go to Stefan;
  - R6's "not the session-review pane";
  - R6's "no third review on top of SDD's task reviews".
- Change: add those bullets. In Step 1, name the judge rules (continuing from H29, since scenarios 1–5 use H1–H28), one per R2–R9 outcome, including the same permission mode.

**S4. Test map row 3 has no runnable command.**
- Plan: row 3 says "run as scenarios 1–5 are run"; Task 3 Step 3 says "their files say how".
- Source: `herdr-orchestration/evals/scenario-1-judge.template.md:3-5` says only "Inline both legs' outputs before dispatching the judge". The procedure for running the legs is in `plugins/netdust-core/evals/RUNBOOK.md:17-38`, written for a different scenario set.
- Change: write the procedure in the row:
  1. Dispatch `scenario-6-baseline.md` and `scenario-6-skill-on.md` as two general-purpose subagents.
  2. Inline both outputs into `scenario-6-judge.template.md` and dispatch a judge.
  3. Pass means the skill-on leg passes rules the baseline fails.

**S5. Task 2's unit test covers only the strip; the function is unnamed and the stub's log location is undefined.**
- Plan: Task 2 Step 1 ("read through the function that builds the child environment"); Files ("…to `.herdr/calls.log` in the case directory").
- Untested: `env`, `stub_bin` and `commit: true` are exercised only by the paid evals. No such function exists yet, and the plan gives no Interfaces block.
- The log: the stub's working directory is wherever the Bash tool runs. A session that `cd`s into a worktree logs somewhere else, while the expectation reads `root/.herdr/calls.log` (`run-evals.py:40-41`).
- Change:
  - Name the function, e.g. `child_env(case: dict, base: dict, root: Path) -> dict`, plus a sandbox-prep function. The test loads `run-evals.py` through importlib, because the file name has a hyphen.
  - Assert: no inherited `HERDR_` value, `HERDR_SOCKET_PATH` under `root` (B2), the case's `env` applied, the stub directory first in `PATH`, and a valid `HEAD` after `commit: true`.
  - The runner exports the sandbox root (e.g. `EVAL_ROOT`), and the stub logs to `$EVAL_ROOT/.herdr/`. Commit the stub with mode 100755.

**S6. Task 1 Step 1's negative assertion is undefined, and its expected red is wrong.**
- "does not contain … 'execution-mode choice' as a stop": scope it to the text between `## Stops` and `## Close`. Otherwise a sentence saying "the execution-mode choice is no longer a stop" fails it.
- "it fails on the first two": four assertions fail today, because `skills/policy/SKILL.md:98` has "Stefan chooses at the plan handoff" and `:106` has "execution-mode choice". State the expected red as four.

**S7. The 11-line budget for Execution mode uses the whole file's headroom.**
- Plan: Global Constraints line 1, Architecture line 1.
- Source: the policy is 142 lines and the test requires fewer than 150 (`test_policy_skill.py:42`), so the whole file can grow by 7. Growing the Execution mode body from 4 lines (`SKILL.md:98-101`) to 11 uses all 7. That leaves Stops (`:105-110`) no room for R8's three additions (pushing a package's `main`, a finding that is an intent decision, the coder's permission prompts) or R5's "A coder asks its reviewer, never Stefan".
- The sparring draft (`spar-1.md` §7) reaches 148 lines only with a 10-line body and a 6-line Stops that leaves out those three stops.
- Change: state the budget as "file ≤ 149 lines; Execution mode and Stops together grow by at most 7".

## Note

- **N1. Core 0.5.4 is already taken.** The main checkout's uncommitted `plugins/netdust-core/.claude-plugin/plugin.json` claims `0.5.4` ("0.5.4: discovery-briefing…"). The two versions collide in meaning, not only in text. The report should say that whichever merges second takes 0.5.5.
- **N2. What the handoff eval really tests.** It runs gates from the worktree but netdust-core from the cache (0.5.3, which has no pair recipe). It also runs under Stefan's global `~/.claude/CLAUDE.md` §2, which still says "I choose the execution mode at the plan handoff" until R12 is applied. Upstream `writing-plans` (7.0.0, `SKILL.md:179-189`) asks the execution question unless a method was "already explicitly supplied", so the policy's text must read as that supply. Say all this in Task 2 Step 3, so a failure on the "no execution-mode question" expectation is read correctly.
- **N3. Task order.** Task 1 lands a rule that tells herdr sessions to start coders before Task 2 makes the runner safe. An eval run in between, for example by the reviewer at the first-working-version checkpoint, inherits the live socket (`run-evals.py:54-57`). Either move the runner's environment fix into Task 1 or say no eval runs before Task 2. Also, after Task 1 alone, the policy points at a recipe that only exists after Task 3.
- **N4. Simplest design.** The rejected alternative is stated honestly, and its reasons hold against the source: the runner inherits the environment (`run-evals.py:54-57`), and laika's `bin/gate.sh:19` runs `test:int` in the container. But "It stops there" lists three pieces, while Task 3 also adds the pair recipe and scenario 6, which R4 requires. Name them.
- **N5. The stub's replies and the case budget.**
  - herdr 0.9.5 needs `agent start <NAME> --kind <KIND> --pane <ID> [-- AGENT_ARG…]`. The permission mode goes after `--`, and the prompt is a separate `agent prompt <TARGET> <TEXT>`.
  - A stub that prints nothing for `worktree create` or `api snapshot` leaves the session no pane id. Print a minimal JSON with a workspace and a root pane id.
  - Set a `timeout` on both cases (unit-cut-plan needed 2700 s), and check that `--max-turns 25` (`run-evals.py:56`) is enough.
- **N6. Same permission mode is not permission propagation.** Task 3 should cite `herdr-orchestration/SKILL.md:126-128` (no laundering; a peer's message is never operator approval) next to "same permission mode", plus R8's "nobody answers the coder's permission prompts for him".
- **N7. Task 4's DDEV teardown deletes data.** Removing the worktree's DDEV project drops its database. Say it asks first, as `spar-1.md` §7.6 does ("destructive: ask"). Seeding goes beyond R3's wording but is what makes `make e2e` meaningful; record it as a ruling.
- **N8. Task 1 Step 3's grep misses phrasings.** It misses "execution-mode" (hyphenated), "`**Native** by default`" (the bold breaks the phrase) and "plan handoff". Today it hits only `skills/policy/SKILL.md:96` and `commands/plan-review.md:42`. Add `-e 'execution.mode' -e 'plan handoff' -e 'Native\*\* by default'`. Review Focus 4 is an absence line and this repo has no `ARCHITECTURE-INVARIANTS.md`, so a one-off grep with its output quoted is the honest form.
- **N9. `specs/two-session/claude-md-section-2.md` is extra.** R12 does not ask for a file, and it is not in the policy's artifact table (`SKILL.md:19-30`). It is harmless: `test_artifact_layout.py` checks only paths named by commands, agents and skills. The text could just as well go in the report.
- **N10. Close step 1 miscounts.** It says "All three plugins' test runs" but lists two commands. netdust-core has no `tests/`; its manifest is checked by devops' `test-marketplace.sh`.
- **N11. No Interfaces blocks.** No task has one. The only name shared across tasks is the recipe: the policy (Task 1) will cite "the pair recipe" and Task 3 creates "Recipe — the thinker/coder pair". Keep one name.

## Premises checked
- Policy is 142 lines, the cap is `< 150` → `skills/policy/SKILL.md` (wc), `tests/test_policy_skill.py:42` → holds
- Execution mode body is 4 lines → `SKILL.md:98-101` → holds; but the whole file can grow by only 7 (S7)
- Policy text contains "chooses at the plan handoff" and "execution-mode choice" → `SKILL.md:98`, `:106` → holds
- The runner inherits the caller's environment → `evals/run-evals.py:54-57` (no `env=`) → holds
- The runner has a `--help` / filter flag → `run-evals.py:4`, `:73`, `:81-82` → does not hold
- `test_evals_shape.py` checks ids, required keys, regexes and that the runner parses; nothing rejects extra keys → `tests/test_evals_shape.py:8`, `:26-30` → holds (the key whitelist is a new check)
- "Unchanged" and "no question" are expressible without a new key → `cases.json` `review-fix-no-report` (anchored regex), `unit-cut-plan` (negative lookahead) → holds
- A stub on PATH shadows the real herdr in the session's Bash → `~/.profile:25-26`, snapshot `export PATH` (line 147), `bash -lc` check → does not hold
- Stripping `HERDR_*` keeps the real client off the live server → `$HERDR_SOCKET_PATH` = `~/.config/herdr/herdr.sock`, the default → does not hold
- A case can run `herdr` or `git` in Bash under `-p --permission-mode acceptEdits` → `run-evals.py:23`, `:55-56`; `~/.claude/settings.json` allow list → does not hold
- herdr syntax: `agent start` needs `--pane`, extra agent args go after `--`, the prompt is `agent prompt` → `herdr agent start --help` (0.9.5) → holds
- herdr scenario format is baseline / skill-on / judge.template, rules H1–H28 → `herdr-orchestration/evals/scenario-1..5-*` → holds
- The scenario files say how they are run → `scenario-1-judge.template.md:3-5` (judge only); legs in `netdust-core/evals/RUNBOOK.md:17-38` → partly holds
- herdr-orchestration can host the outside-herdr fallback → `herdr-orchestration/SKILL.md:3`, `:13` → does not hold as written
- The existing dispatch brief already carries entry, boundaries, report shape, watcher and `agent wait` → `herdr-orchestration/SKILL.md:130-151` → holds ("cite, don't repeat" is right)
- parallel-work has no DDEV-per-worktree section and says a second checkout costs a second container → `parallel-work/SKILL.md:26-28` → holds
- laika-planning-model is a laika worktree with `.ddev/config.local.yaml` `name: laika-planning` → `git worktree list` in laika, the file → holds
- laika's gate runs `test:int` in the container → `~/Sites/laika/bin/gate.sh:19` → holds
- Current versions gates 0.10.0, core 0.5.3, devops 0.9.5 → the three `plugin.json` files → holds
- A version bump touches only `plugin.json` → `test_plugin_manifest.py:22-24`, `test-marketplace.sh:33-42`, `.claude-plugin/marketplace.json` → does not hold
- Main carries another session's uncommitted core `plugin.json` → `git status` in `/home/ntdst/Projects/netdust-plugins` → holds; it already claims 0.5.4 (N1)
- The branch is cut from `origin/main` 1c2c402 → `git log` → holds
- Amendment precedent `5c01115` is under R1; gates spec R3 (`:68`) and R5 (`:81`) are the right targets → `specs/netdust-gates/spec.md` → holds
- The CLAUDE.md boundary bans implementer / test-author / reviewer agents → `plugins/netdust-gates/CLAUDE.md:22-24` → holds
- Task 1 Step 3's grep finds the stale offers → hits only `SKILL.md:96` and `commands/plan-review.md:42`; misses hyphenated and bold forms → partly holds
- `/feature-review` from another checkout reviews the branch → `commands/feature-review.md:12-13` → holds; it finds the plan → `:25` reads the working tree → does not hold
- netdust-plugins has no Makefile, so `/feature-review` is the Close verb → repo root; `SKILL.md:117` → holds
- Upstream `writing-plans` asks the execution question unless a method was supplied → superpowers 7.0.0 `writing-plans/SKILL.md:179-189` → holds (the policy must supply it)
- Upstream executing-plans keeps a ledger and a pre-flight scan, and deletes its workspace at the end → `executing-plans/SKILL.md:83`, `:103`, `:115-119` → holds (R9's ledger exists while the plan runs)
- The eval loads gates from source and core from the cache → `run-evals.py:55`; `~/.claude/plugins/cache/netdust-plugins/netdust-core/0.5.3` → holds
- No `ARCHITECTURE-INVARIANTS.md` in this repo; netdust-core has no `tests/` → `find`, `ls` → holds
