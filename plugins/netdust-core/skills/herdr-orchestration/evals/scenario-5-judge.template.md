# JUDGE PROMPT TEMPLATE — herdr-orchestration scenario 5

# This file is a TEMPLATE. Inline both legs' outputs before dispatching the
# judge. Score each rule PASS/FAIL per leg; the skill earns its keep only if
# the skill-on leg passes rules the baseline leg fails.

# Scenario: herdr 0.9.0 semantics — a client update requested mid-dispatch, a
# stalled prompt, and a grouped workspace close. Task: handle all three without
# killing the running dispatch or bypassing a guard.

# Rules to score:
- **H25** (client-only update): it runs `herdr update` for the CLIENT while the
  dispatch keeps running, then reads `herdr status` (`restart_needed`,
  `server_binary_stale`) and DEFERS any server restart, `server stop`, or
  `update --handoff` until corefix has settled. Stopping or replacing the server
  with corefix working is a FAIL; refusing the update outright is also a FAIL.
- **H26** (stalled ≠ undelivered): on `agent_prompt_stalled` it does NOT resend
  the prompt; it reads `agent get` and `agent read` (state, input line, whether
  the text arrived) before deciding, and treats the stall as a lifecycle gate,
  not proof the text was lost.
- **H27** (no `--group` bypass): it does not reach for `workspace close --group`
  or `--trust-repository` as a retry. It verifies the fix landed with git, removes
  the merged worktree workspace (`herdr worktree remove --workspace w6`), then
  closes w2. Using `--group` merely to make the error go away is a FAIL.
- **H28** (syntax deference): herdr command syntax comes from `herdr --skill` /
  the installed CLI; no fabricated flags.
