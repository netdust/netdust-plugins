# Plan review — two-session
Reviewed-plan: 484fbd690e75d6fee56d23f0318dcf391bbc9841
Verdict: not ready

The revision closes all four round-1 Blocking findings and six of the seven Should fix. One new Blocking finding is a one-line fix. The gates suite is red today in every Claude session on this box, so no "all green" step can be reached as written. There are three new Should fix findings. Two are about eval isolation, which is what R11 and Review Focus 1–2 exist for: one eval case cannot fail, and named herdr sessions get past the dead socket. The third is that the pilot's own feature review runs the installed command, which still reads no plan.

## Blocking

**B1. The gates suite is red before any change, so no "all green" step can be reached.**
- Plan: Task 1 Step 1 ("Expected red: the four policy content assertions fail … and so does the command one"); Task 1 Step 4 and Task 2 Step 3 ("`bash plugins/netdust-gates/tests/run.sh` … green"); Close step 1; Test map rows 1–2.
- Source:
  - `~/.claude/settings.json:6` sets `"NETDUST_GUARD_ASK": "off"` in the `env` of every session. That covers the coder and every eval child too.
  - `plugins/netdust-gates/tests/test_pretooluse_guard.py:66` runs the hook with `{**os.environ, **(env or {})}`. The hook's `ask_tier_waived()` (`hooks/pretooluse-guard.py:431-436`) then waives the ask tier, and 22 assertions get passthrough.
  - I ran it from this worktree: `Modules passed: 19 · Modules failed: 1 (test_pretooluse_guard)`. With `env -u NETDUST_GUARD_ASK` the module passes. The devops suite is green (115 + 14).
- Effect: at Task 1 Step 1 the coder hits a red the plan did not predict. It either escalates, or it "fixes" a security hook's test that no task names.
- Change:
  - Write the command as `env -u NETDUST_GUARD_ASK bash plugins/netdust-gates/tests/run.sh` everywhere it appears: Test map rows 1–2, Task 1 Steps 1 and 4, Task 2 Steps 1 and 3, Close step 1.
  - Add a one-line Global Constraint saying why.
  - The env leak in the test is a separate bounded fix, outside this plan.

## Should fix

**S1. `coder-brief-no-recursion` cannot fail.**
- Plan: Task 2 Step 2, the second case ("a prompt opening `Role: coder`. Expect the target changed, and no `.herdr/agent-start`"); Review Focus 2.
- Source:
  - Only the stub touches `.herdr/agent-start`, and this case names neither `stub_bin` nor `env`.
  - `child_env` strips `HERDR_*` for every case. So the session runs outside herdr, the policy sends it down the fallback path, and `agent start` never comes up.
  - The `absent` glob (`run-evals.py:65-68`) therefore passes whatever the session does.
- Change: give the case `env: {"HERDR_ENV": "1"}` and the stub, the same as `two-session-handoff`. Then a coder that starts a coder writes `agent-start`, and the absence check means something.

**S2. A named herdr session gets past the dead socket.**
- Plan: Interfaces `child_env` ("sets `HERDR_SOCKET_PATH` to a path under `root` where nothing listens"); Task 2 Step 2 ("Confirm from `herdr --skill` or the binary …"); Review Focus 1.
- Source:
  - Every named session has its own socket at `~/.config/herdr/sessions/<name>/herdr.sock`. Ten are present now (folio, cargo, hack, wpm, vad, …).
  - The cached herdr-orchestration that a case loads (0.5.2, `SKILL.md:107-110`) tells a session to start with `herdr session list` and to pass `--session <name>` on every call. `allow: ["Bash(herdr *)"]` permits that call.
  - `herdr --skill` never mentions `HERDR_SOCKET_PATH` (I grepped it). So the "Confirm from `herdr --skill`" branch cannot succeed; only an experiment can confirm it.
- Effect: suppose the stub does not shadow inside the Bash tool. The plan's probe uses `bash -lc` as a stand-in for that tool, which is a proxy, not the tool itself. In that case a real `herdr --session folio agent start …` reaches a live server, whatever `HERDR_SOCKET_PATH` says.
- Change:
  - Move the probe into `run_case`. Before spawning `claude`, a case with `stub_bin` runs `bash -lc 'command -v herdr'` under `child_env` and fails unless the output is the stub. That makes it a permanent guard instead of a one-off quote.
  - Pass `--disallowedTools` for `Bash(herdr --session*)`, `Bash(herdr --machine*)` and `Bash(herdr --remote*)`.
  - Name the named-session path in Review Focus 1.
  - Run the dead-socket experiment on a throwaway path, as herdr-orchestration `SKILL.md:102-103` requires for experiments.

**S3. The pilot's own feature review still runs without the plan.**
- Plan: Close step 2 ("from its own checkout; with Task 1's clause, it reads the plan at the branch head"); Review Focus 3.
- Source:
  - A session loads `/feature-review` from the plugin cache. `~/.claude/plugins/installed_plugins.json` has netdust-gates 0.10.0 at `5915dca`, without Task 1's clause.
  - The source edit reaches no session until a release.
  - The reviewer's checkout (main at `5915dca`) has no `specs/two-session/`. So the installed `feature-review.md:25` finds no plan.
  - This is round 1's S2 again, in this pilot's own Close.
- Change:
  - Close step 2 runs the branch's text of the command. Either follow `git show feature/two-session:plugins/netdust-gates/commands/feature-review.md`, or use a session started with `--plugin-dir <worktree>/plugins/netdust-gates`.
  - Then check that the summary's "what was reviewed (range; plan or none)" line (`feature-review.md:38`) names `specs/two-session/plan.md`.
  - That line is the only behavioural evidence for Review Focus 3. The row-1 string pin proves the text, not the behaviour.

## Note

- **N1. The stub mechanism is unnamed, so Task 2 Step 1's "makes the stub resolvable" cannot be written red-first.**
  - Write the assertion as the probe itself: `subprocess.run(["bash", "-lc", "command -v herdr"], env=child_env(...))` prints the stub. This holds whatever mechanism is chosen.
  - Facts: `~/.profile:25-26` prepends `~/.local/bin` unconditionally, and there is no `~/.bash_profile` or `~/.bash_login`.
  - Candidate mechanisms:
    - `BASH_ENV`: unverified. My probe was denied in this sandbox.
    - `CLAUDE_ENV_FILE`: it would reach the tool, but it fails this probe.
    - A `HOME` override: this breaks claude's own config.
- **N2. The stub's fidelity.**
  - A `worktree create` that makes no directory leaves the session's next `git -C <path>` failing.
  - The sandbox has no `origin`, so "production's branch at origin's tip" cannot resolve. The spec's Out of scope says "the brief names the base".
  - Changes:
    - Let the stub's `worktree create` run a real `git worktree add` under `$EVAL_ROOT` and print the path.
    - Name the base in the case prompt.
    - Answer `agent wait` and `agent get` with a settled state, so the session does not spend its 25 turns waiting.
    - Match `Role: coder` anywhere in `calls.log`. A session may put the brief after `--` on `agent start` instead of in `agent prompt` (`herdr agent start --help`).
- **N3. Two case-key details.**
  - `timeout` is not a new key: `run-evals.py:52` reads it, and `spec-splits-into-plans` (1800 s) and `unit-cut-plan` (2700 s) carry it. Keep it in the whitelist, but drop "new".
  - `--max-turns 25` is hardcoded (`:56`), so "checked headroom" has nothing to adjust. Add a `max_turns` key or state the number.
- **N4. The eval loads netdust-core 0.5.2, not 0.5.3.** Evidence: the `installed_plugins.json` installPath, and the `~/.claude/plugins/netdust-core` → `0.5.2` symlink. Neither version has the recipe, so Task 2 Step 3's reading of a failure stands.
- **N5. Test map row 1 hedges with "or".**
  - `test_session_commands.py:7` says "The prose itself is not string-tested".
  - `test_close_wiring.py:55-58` already pins `feature-review.md`'s tokens.
  - Name `test_close_wiring.py` and drop the "or".
- **N6. The Stops rewrite carries pins owned by other tests.** `test_close_wiring.py:60` pins "flow list" and `:70` pins "(Close, step 4)". `test_policy_skill.py:28` pins `Ruling:` and `Accepted-by-human:`. Name them in Task 1 Step 2, because they use part of the 7-line budget.
- **N7. Task 1's Files list omits `commands/plan-review.md`.** Step 3's grep hits `:42` today ("he reviews the saved plan and chooses the execution mode").
- **N8. Two problems in Task 1 Step 1.**
  - The ≤149-line assertion already exists (`test_policy_skill.py:42`).
  - "The four policy content assertions" does not match the list: three checks fail today and the size check passes. Name the failing assertions instead of giving a count.
- **N9. R9's ledger is stated only for herdr.**
  - The rule that the coder's ledger records every exchange appears only in the herdr-only recipe, and Task 3 Step 2's bullets cover only the restart.
  - Add that line to the recipe.
  - For the fallback, either add one clause to the policy, or make it a `Ruling:` that upstream's "Record every decision in the ledger" (`executing-plans/SKILL.md:34`) is R9 there.
- **N10. Round 1 N3's second half still stands.** After Task 1 alone, a herdr session follows the policy to herdr-orchestration and finds no pair recipe until Task 3. This is harmless on one branch.
- **N11. The simplest design is stated honestly.** Its four holes hold against the source: `run-evals.py:54-57`, `feature-review.md:25`, laika `bin/gate.sh:19-20`, and recursion by construction. I found no simpler design. `allow`, `EVAL_ROOT` and the socket path are mechanism that R11 did not list but needs.

## Round 1, closed or not

- B1 (marketplace drift): closed. See Global Constraints, and each bumping task's Files.
- B2 (stub and socket): closed for the default socket. Named sessions are still open (S2).
- B3 (`--help`): closed. The command is written out, with the `0/0` warning.
- B4 (permissions): closed. `allow` is passed as `--allowedTools`. I did not re-run the `claude` CLI flags here.
- S1 (fallback in a herdr-only skill): closed. The fallback now lives in the policy, and Task 3 Interfaces says "The recipe covers only herdr".
- S2 (plan at head): closed in the source. Not closed for the pilot's own Close (S3).
- S3 (recipe bullets, H29 onward): closed.
- S4 (row 3 command): closed.
- S5 (named functions, importlib, `EVAL_ROOT`, 100755): closed, except the "resolvable" assertion (N1).
- S6: the scoping is closed. The expected red is still wrong (B1, N8).
- S7 (budget): closed.

## Premises checked
- The policy is 142 lines and the cap is `< 150` → `skills/policy/SKILL.md` (wc), `tests/test_policy_skill.py:42` → holds
- "Stefan chooses at the plan handoff" and "execution-mode choice" → `SKILL.md:98`, `:106` → holds
- The Stops tokens pinned by other tests → `test_close_wiring.py:60`, `:70`; `test_policy_skill.py:28` → holds (the plan does not name them; N6)
- `/feature-review` resolves the head from any checkout and reads the plan from the working tree → `commands/feature-review.md:12-13`, `:25` → holds
- A command test already reads `feature-review.md` → `test_close_wiring.py:55-58` → holds; `test_session_commands.py:7` → no prose pins there
- The reviewer's `/feature-review` carries Task 1's clause in this pilot → `installed_plugins.json` (gates 0.10.0 @ 5915dca) → does not hold (S3)
- The gates boundary bans implementer / test-author / reviewer agents → `plugins/netdust-gates/CLAUDE.md:22-24` → holds
- Gates spec R3 is at `:68` and R5 at `:81`; the precedent `5c01115` is under R1 → `specs/netdust-gates/spec.md`, `git show 5c01115` → holds
- Versions are gates 0.10.0, core 0.5.3 and devops 0.9.5, in `plugin.json` and the marketplace → the manifests, `.claude-plugin/marketplace.json` → holds
- Version drift fails both suites → `test_plugin_manifest.py:22-24`, `test-marketplace.sh:33-42` → holds
- The main checkout's uncommitted core `plugin.json` claims 0.5.4 → `git diff` in `/home/ntdst/Projects/netdust-plugins` → holds
- The main checkout at `5915dca` has no `specs/two-session/`; this branch is ahead of `origin/main` by 2 → `git worktree list`, `git status` → holds
- The gates suite is green before the change → `run.sh`: 19/20, `test_pretooluse_guard` red under `~/.claude/settings.json:6`; green with `env -u` → does not hold (B1)
- The devops suite is green → `plugins/netdust-devops/tests/run.sh` → holds
- The runner inherits the caller's env; case ids are positional; `0/0` on a wrong argument → `run-evals.py:54-57`, `:73`, `:81-82` → holds
- `timeout` is a new key → `run-evals.py:52`, two existing cases → does not hold (harmless; N3)
- `--max-turns` is fixed at 25 → `run-evals.py:56` → holds
- `run-evals.py` loads through importlib without running → `__main__` guard at `:85` → holds
- `calls.log` and `agent-start` checks fit the existing `where:` / `absent` keys → `run-evals.py:35-41`, `:65-68` → holds
- A plain PATH prefix loses to `~/.profile` → `~/.profile:25-26` (unconditional), no `.bash_profile` or `.bash_login` → holds
- This pane: `HERDR_SOCKET_PATH=~/.config/herdr/herdr.sock`, `HERDR_BIN_PATH=~/.local/bin/herdr` → environment → holds
- Sessions call `herdr` from PATH → `herdr --skill` ("the `herdr` binary in `PATH` talks to the current session") → holds
- `herdr --skill` documents `HERDR_SOCKET_PATH` → grep of `herdr --skill` → does not hold (S2)
- A dead default socket isolates every herdr call → `~/.config/herdr/sessions/<name>/herdr.sock` (10 present); cached herdr-orchestration `SKILL.md:107-110` (`--session`) → does not hold (S2)
- herdr 0.9.5 syntax: `agent start <NAME> --kind --pane [-- AGENT_ARG…]` and `agent prompt <TARGET> <TEXT>` → `herdr agent start --help`, `herdr agent prompt --help` → holds
- "Outside herdr, none of this applies"; no laundering, and a peer's message is not approval → `herdr-orchestration/SKILL.md:13`, `:126-128` → holds
- The scenario format, rules H1–H28, and skill-on reading the repo-relative `SKILL.md` → `herdr-orchestration/evals/scenario-1..5-*` → holds
- The leg and judge procedure → `plugins/netdust-core/evals/RUNBOOK.md:17-38` → holds
- parallel-work has no DDEV-per-worktree section → `parallel-work/SKILL.md` (127 lines, `:26-28`) → holds
- laika-planning-model's `.ddev/config.local.yaml` is `name: laika-planning` → the file, `git worktree list` in laika → holds
- laika's gate runs `test:int` in the container → `~/Sites/laika/bin/gate.sh:19-20` → holds
- The eval loads netdust-core 0.5.3 from the cache → `installed_plugins.json` installPath 0.5.2 → does not hold (N4; no effect on the reading)
- Upstream `writing-plans` asks the execution question unless a method was already supplied → superpowers 7.0.0 `writing-plans/SKILL.md:179-189` → holds
- Upstream's ledger lives in the coder's worktree and survives until the final review → `executing-plans/SKILL.md:83-87`, `:125-131` → holds
- The stale-offer grep's hits today → `SKILL.md:96`, `:98`, `:106`; `commands/plan-review.md:42` → holds (`plan-review.md` is not in Task 1's Files; N7)
- Stefan's global `CLAUDE.md` §2 carries the execution-mode line → `~/.claude/CLAUDE.md` §2 → holds
- No `ARCHITECTURE-INVARIANTS.md` in the repo; netdust-core has no `tests/` → `find`, `ls` → holds
