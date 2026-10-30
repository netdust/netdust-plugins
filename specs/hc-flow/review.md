# Feature review — hc-flow

- **Range:** 340902be791b48e506049b231eed5a0c4d7fb616..7420726dd898d0fc858c82fab1d6b735bdf4cd06 (origin/feature/hc-flow)
- **Plan:** specs/hc-flow/plan.md (Spec: specs/hc-flow/spec.md, with its Threat model)
- **Level:** full
- **Reviewers:**
  - superpowers code reviewer (general-purpose, opus)
  - security-sentinel (opus; the plan carries a threat model)
  - No invariant-auditor: no ARCHITECTURE-INVARIANTS.md. No drift reviewer: not a WordPress project.
- **Suites, as re-run by the code reviewer:** gates 21/21 (under `env -u NETDUST_GUARD_ASK`), core 4/4 + 23/23, test-marketplace 14/14; `claude-md.diff` applies cleanly.
- **Threat-model mitigations verified as holding by security-sentinel:**
  - the allowlisted child env, with `HC_SOCKET`/`HC_TERMINAL_SOCKET` stripped and all paths scratch
  - a real hc under a custom XDG_RUNTIME_DIR never calls systemd-run and stays inside bwrap
  - the deny list covers the named verbs, and no case grants them
  - the stub wins `command -v hc`
  - the shape test never calls a real hc
  - the auto-start teaching matches the source

## Blocking

None.

## Should fix

**S1. `HC_SOCKET` defeats the scratch guard.** `plugins/netdust-core/tests/scratch-hc.sh:3-23` and `bin/hc-templates:12` as reached from `test-hc-templates.sh:40`. Raised by security-sentinel M1 and the code reviewer (Important 4).
- `HC_SOCKET` wins over `HC_SESSION` and XDG (paths.rs:27-33), and hc's own error hint tells users to set it (client.rs:112).
- With it set to the live socket, every guarded call reaches Stefan's core, and the EXIT trap's `hc server stop` stops it.
- `bin/hc-templates --on …` runs in a child `sh` without the guard function.
- **Fix:** `unset HC_TERMINAL_ID HC_SOCKET HC_TERMINAL_SOCKET` in `scratch_hc_start`, and require `[ -z "${HC_SOCKET:-}" ]` in the guard.
- **RED test:** with `HC_SOCKET=/x`, the guard refuses (97).

**S2. "Is a core running?" checks that a file exists, not that a core listens.** `plugins/netdust-core/skills/hc-orchestration/SKILL.md:12-13, 21-22`. Raised by security-sentinel M2 and the code reviewer (Minor 6).
- A stale socket from a crashed core passes the check. The next `hc` call then autostarts the core with the agent's environment: the exact leak the rule exists to prevent.
- The check also ignores `HC_SOCKET` and the config's `socket` key.
- An agent inside hc whose core died (it still has `HC_TERMINAL_ID`) skips the check entirely.
- **Fix:** probe with a connect, without hc. For example, `python3 -c 'import socket,sys; socket.socket(socket.AF_UNIX).connect(sys.argv[1])' "$sock"`; a refusal means no core.
- Apply the probe before the first `hc` call, and again after any hc connection error, inside hc too.
- **RED:** a stale-socket variant in scenario 6 whose judge rule fails without it.

**S3. A restarted reviewer loses its coder's reports.** `SKILL.md:65-66` (pair recipe, restart step) and `hc-templates/coder.md:12-13`. Raised by the code reviewer (Important 1); Review Focus 3.
- `--outlive-parent` keeps the coder alive, but its `parent` stays the dead terminal. hc has no reparent command.
- The coder keeps sending to the old address, the new reviewer's `hc wait --children` can't see it, and the coder stalls silently.
- **Fix:**
  - the restarted reviewer runs `hc send <f>-coder "your reviewer is now $HC_TERMINAL_ID"` (or sets a `reviewer=<id>` label the coder reads) and waits with `hc wait <f>-coder`
  - coder.md says a message naming a new reviewer address replaces the old one
- **RED:** a template/wiring assertion that fails without it.

**S4. Helpers write findings into the coder's tree, and "read-only" is overstated.** `hc-templates/reviewer.md:3,7,9`, `sparring.md:3,7,9`, `SKILL.md:33,40`. Raised by the code reviewer (Important 2) and security-sentinel L4.
- "never write" and "Write the findings to a file" contradict each other, with no location given, so the file lands in the cwd: the coder's checkout.
- `--disallowedTools Edit Write NotebookEdit` leaves Bash, so the helper is read-only by instruction only.
- **Fix:**
  - the body names an outside location (`$TMPDIR`, or a path the task gives)
  - the wording becomes "read-only by instruction; Bash can still write"
  - optionally, also disallow `Bash(git commit*)`, `Bash(git push*)` and `Bash(hc *)` in those two commands
- **RED:** a template-body assertion for the outside location.

**S5. parallel-work leads sessions outside hc into the core-start trap.** `plugins/netdust-devops/skills/parallel-work/SKILL.md:14, 19, 26, 68-71`. Raised by the code reviewer (Important 3).
- `hc run --bg --name gate make gate` and "a helper terminal" are prescribed unconditionally, and the skill triggers on generic phrases in TUI sessions.
- **Fix:** "inside hc only (`HC_TERMINAL_ID` set); outside hc, read the first rule of `netdust-core:hc-orchestration` before any `hc` call".
- **RED:** a wiring-test assertion.

**S6. coder.md doesn't say "no worktree".** `hc-templates/coder.md:8`. Raised by the code reviewer (Minor 9), promoted to Should fix here because it is spec R6's core.
- `superpowers:executing-plans` Setup asks for worktree consent in a main checkout, and the template's "Stay in this checkout" doesn't answer it. A coder could cut a worktree.
- **Fix:** "No worktree: work in place in this checkout (spec R6)".
- **RED:** a template assertion.

**S7. Task 4's behavioural evals have no recorded result.** Raised by the code reviewer (Important 5).
- Attach the `run-evals.py two-session-handoff coder-brief-no-recursion small-tweak-no-artifacts` output to this review file, from the final head after the fix pass.
- Check the stub's `wait` doesn't loop a session to max_turns: if it always answers `reason: timeout`, have it return ended after the first call.

## Note

- **N1 (security-sentinel L1):** the stub preflight checks `bash -lc`, while the child uses `$SHELL` plus Claude Code's snapshot. Set `env["SHELL"]="/bin/bash"` in `child_env`, and add a post-case canary that fails if `hc_home(root)/state/herdr-core` exists.
- **N2 (security-sentinel L2):** `DISALLOWED` and `HC_STATE_VERBS` miss `hc serve`, `hc hold`, `kill`, `rm`, `interrupt`, `attach`, and machine-qualified addresses (`Bash(hc * */*)`). Defense in depth; nothing reaches them today.
- **N3 (security-sentinel L3):** a case's `env` may set PATH, HOME, BASH_ENV, SHELL, LD_PRELOAD. Allow only `{"HC_TERMINAL_ID"}`.
- **N4 (security-sentinel Info):** the `LIVE` dict in test_evals_shape.py:29-35 lacks `HC_SOCKET` and `HC_TERMINAL_SOCKET`.
- **N5 (security-sentinel Info):** `bin/hc-templates:14` silently overwrites a customised template.
- **N6 (code reviewer Minor 7):** `plugins/netdust-gates/commands/session-learn.md:35` still says "on a new branch in its own worktree".
- **N7 (code reviewer Minor 8):** `policy/SKILL.md:104-105`, "from its own checkout", is stale wording.
- **N8 (code reviewer Minor 10):** hc names are 1-32 chars of `a-z0-9-_`. Note the limit for `<f>-coder` in the pair recipe.
- **N9 (code reviewer Minor 11):** `run-evals.py` `hc_home` falls back to a predictable `/tmp/hc<hash>` with `exist_ok=True`.
- **N10 (code reviewer Minor 12):** `bin/hc-templates` ignores unknown arguments (`--help` runs an install).
- **N11 (code reviewer Minor 13):** `test_hc_wiring.py:11` STALE misses `herdr agent prompt`, `herdr pane`, `herdr worktree` and `herdr api`.
- **N12 (code reviewer Minor 14):** the `.hc/wt` absent check is vacuous; `stray_worktrees` is the real guard.
- **N13 (security-sentinel Info):** a reviewer in default mode using the coder template escalates the coder to auto. This is accepted by the "Always auto" ruling.

Findings: 0 Blocking · 7 Should fix · 13 Note

## Fix pass

One pass, each Should fix RED→GREEN (commits e27e30a, 2407b16). Notes taken: N1, N3, N4, N6, N7;
the rest deferred. S2 landed per reviewer ruling A: probe before the first `hc` call outside hc;
inside hc, only after a connection error (Claude Code's Bash sandbox forbids AF_UNIX and the
permission layer refuses `${…}`, so a probe inside every stubbed eval cannot run).

Behavioural evals on 2407b16 (`python3 plugins/netdust-gates/evals/run-evals.py two-session-handoff coder-brief-no-recursion small-tweak-no-artifacts`):

```
PASS  small-tweak-no-artifacts
PASS  two-session-handoff
PASS  coder-brief-no-recursion

3/3 cases passed
```
