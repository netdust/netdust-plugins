# two-session — feature review

**Range:** `1c2c402..1e3247a` (`origin/feature/two-session`), run by the reviewer session (laika-db) using the branch's own text of `commands/feature-review.md`.
**Plan:** `specs/two-session/plan.md` (head's).
**Reviewers** (opus):
- superpowers' code reviewer;
- `security-sentinel`, on the eval runner's isolation: the runner touches the messaging token, sockets and permissions.

No `invariant-auditor` (the repo has no `ARCHITECTURE-INVARIANTS.md`); not WordPress.
**Suites at head:** gates 20/20 (`env -u NETDUST_GUARD_ASK`), devops 14/14.

## Blocking

1. **Every eval inherits Stefan's user settings** (security H1). `run-evals.py:95-98` passes no `--setting-sources`, `--settings` or `--restricted`, so every case loads `~/.claude/settings.json`. That brings in:
   - unscoped Write/Edit/Read, `Bash(curl *)` and the browser MCP;
   - the user MCP servers;
   - `NETDUST_GUARD_ASK=off`, which waives the destructive-command guard.

   A case can overwrite `evals/stubs/herdr` with an `exec` of the real binary and reach the live server, or write into any repo under `~/Sites` or `~/Projects`. Fix:
   - run cases with `--restricted --strict-mcp-config`, a `--tools` allowlist, and a runner-built `--settings` (the plugins the cases need, `permissions.allow` = the case's `allow`, `NETDUST_GUARD_ASK=on`);
   - add a canary case that tries to write `$HOME/eval-canary` (`absent`).

   Verify each flag against `claude --help` first.
2. **`Bash(git *)` is arbitrary execution as Stefan** (security H2). Two routes:
   - `git -c alias.x='!sh x.sh' x`. From that shell, `env -u HERDR_SOCKET_PATH ~/.local/bin/herdr`, `/proc/$PPID/environ` (the runner's unstripped messaging token, then `nc -U` into a live session) and `~/.ssh` are all reachable.
   - With no trick at all, `git -C ~/Sites/laika …`. evalruns2's coder ran `git -C $R worktree add $R-greeting`.

   Fix:
   - replace the rule with the exact git commands the cases use (the list in the sentinel report);
   - deny `Bash(git -C *)`, `Bash(git -c *)`, `Bash(git --*)`, `Bash(git push*)`, `Bash(git config*)` and `Bash(git worktree add*)`; only the stub cuts worktrees.

## Should fix

3. **Reviewers read the wrong tree** (code review 1). `commands/feature-review.md:25-28` fixes only the plan: every reviewer that greps files still reads the reviewer's own checkout. Fix:
   - reviewers read a detached checkout of the head (`git worktree add <tmp>/review-<sha> <head>`, removed afterwards) or the coder's worktree, read-only;
   - extend the clause to the spec the plan's `**Spec:**` line names.
4. **A stale execution-choice offer** (code review 2). `plugins/netdust-wp/templates/project-CLAUDE.md.tmpl:13` still says "…`/plan-review`, then your execution choice." Fix the template and bump netdust-wp (plugin.json and marketplace). laika's and laika-planning-model's copies go to Stefan with R12.
5. **Upstream's four stops routed to the reviewer** (code review 3). `skills/policy/SKILL.md:112-117`: "…and takes intent to Stefan" lets the reviewer rule on a destructive op, a security action, a side effect outside the worktree, or a broken plan. That is laundering (`herdr-orchestration:126-128`). Fix: "…and takes intent and upstream's four stops to Stefan" (no extra line), and the same at recipe step 4.
6. **The coder's rulings never reach Stefan** (code review 4). Upstream's Finish puts "Rulings I made" and "Deferred minors" in the coder's final message, which lands in the coder's pane. Fix: the coder sends that list to the reviewer, and the reviewer's hand-over carries it (recipe step 7, and the policy's "list in the final message").
7. **Same mode is unchecked** (code review 5). `run-evals.py:96` loads only gates through `--plugin-dir`, so the herdr cases test against core 0.5.2 from the cache. Fix:
   - load `plugins/netdust-core` as a second `--plugin-dir` for the herdr cases;
   - expect `(?m)^agent start .*--permission-mode` in `calls.log`;
   - run once.
8. **The environment is passed whole, minus two prefixes** (security M1). `PLOI_API_TOKEN`, `SSH_AUTH_SOCK`, `XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`, `NETDUST_GUARD_ASK` and the parent-session ids (`CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_SESSION_ATTENDED`, `CLAUDE_PID`, `CLAUDECODE`, `AI_AGENT`) all reach every case. Also, `Bash(printenv *)` matches a bare `printenv`. Fix:
   - build the env from an allowlist (HOME, USER, LOGNAME, SHELL, LANG, TERM, PATH, TMPDIR), with `XDG_RUNTIME_DIR` inside the sandbox;
   - narrow the rule to `Bash(printenv HERDR_ENV)`;
   - pin the new keys in `tests/test_evals_shape.py`'s `LIVE`.
9. **The herdr deny list leaves state verbs open** (security M2). Fix:
   - allow only the verbs the stub serves (`worktree create`, `api snapshot`, `pane split`, `agent start|prompt|wait|read|get`, `--help`, `--skill`);
   - deny `session*`, `plugin*`, `update*`, `server*`, `machine*`, `config*` and `integration*`;
   - refuse a `stub_bin` outside `evals/stubs/`;
   - hash-check `stubs/herdr` and `stubs/bash-env` before and after each case.
10. **Cleanup, timeout and path confinement** (security L1–L3).
    - **Cleanup:** remove only paths under the temp parent, print every path found and every failure, then `git worktree prune`.
    - **Timeout:** run `claude` in its own process group (`start_new_session=True`) and kill the group on timeout, before cleanup.
    - **Path confinement:** `_write` and `stub_bin` must stay inside the sandbox and `evals/stubs/`, and a case's `env` may not set `HERDR_*` (except `HERDR_ENV`) or `CLAUDE_*`.

## Note

- **Deny by allowlist** (security L4). `Agent` with `isolation: "worktree"` is a second worktree route. ListPeers, TeamCreate, RemoteTrigger, CronCreate and PushNotification are not denied. The `--tools` allowlist in Blocking 1 closes this.
- **Upstream's Final Review is the reviewer's `make review`** (code review 6). Recipe step 3 or 7 says so: the coder pushes and signals instead. The CLAUDE.md R10 line "runs upstream's executor unchanged" is not quite true.
- **The `herdr worktree create` test** (`tests/test_evals_shape.py`) goes through PATH even when resolution failed. Call the stub by its absolute path (code review 7).
- **A sibling worktree escapes the R2 check** (code review 9). A stubbed case that leaves any worktree other than `.herdr/wt` fails, or at least prints the list.
- **The no-recursion prompt** should be shaped like the real brief (`Role: coder`, the plan path, `netdust-gates:policy`), so it tests the exemption (code review 10).
- **"Its per-task TDD undoes the unit cut"** is now nowhere. Put it in recipe step 3 (code review 11).
- **The thinker's untracked originals** of the spec, plan and plan review stay behind. Recipe step 1 says to move them (code review 12).
- **Rollout:** a feature already running in one session finishes as it runs (code review 13).
- **The reviewer's DECISION/LESSON tags** land in its own checkout's `memory/`. Say where they belong (code review 14).
- **Policy readability** (code review 15): Execution mode is one 14-line paragraph, and the file is at the 149-line cap.
- **Decisions for Stefan** (not this fix pass):
  - an OS-level boundary for evals, which is the real fix for Blocking 1 and 2 (security H2): Claude Code's `sandbox` setting needs `bubblewrap` and `socat` installed, or a separate Unix user or a container;
  - the R12 text for his `~/.claude/CLAUDE.md` §2, whose third subagent-driven trigger ("a task encodes a rule this project chose") the policy has never had;
  - the netdust-core 0.5.4 collision with discovery-briefing.

Findings: 2 Blocking · 8 Should fix · 11 Note
