# JUDGE PROMPT TEMPLATE — herdr-orchestration scenario 3

# This file is a TEMPLATE. Inline both legs' outputs before dispatching the
# judge. Score each rule PASS/FAIL per leg; the skill earns its keep only if
# the skill-on leg passes rules the baseline leg fails.

# Scenario: build a project's dev workspace from a pane that lives in a
# DIFFERENT herdr session. Task: put it in the right session, and know the
# recovery when it lands in the wrong one.

# Rules to score:
- **H13** (look before you create): the answer runs `herdr session list` (or
  equivalent discovery) BEFORE creating any workspace, and establishes which
  session the stride work lives in. Creating topology first and checking after
  is a FAIL.
- **H14** (explicit session on every call): every command that targets the
  stride session carries `--session stride`. The answer states that a bare
  `herdr` resolves to the CALLING pane's session, not the project's.
- **H15** (irreversibility): asked what went wrong, the answer identifies that
  the panes were built in the caller's own session, and that there is NO
  cross-session move — the fix is rebuild in the right session and close the
  wrong one, re-seating the agent by hand. Any answer proposing a `move`,
  `migrate`, or `--session` retarget of an existing workspace is a FAIL.
- **H16** (topology): workspace at the repo with sibling panes for the helper
  processes — panes for processes, workspaces for branches. It does not create
  a worktree (same checkout, no different base).
- **H17** (no stolen focus): `--no-focus` on creation; the operator's focus is
  never moved.
- **H16b** (artifacts get a tab): if the answer proposes showing a document — a
  spec, a plan, a report — it opens a TAB in the project's workspace rather than
  adding a fourth pane to the work layout, and it tells the operator the tab
  exists because it was created `--no-focus`. Not scored if the leg never raises
  showing a document.
- **H18** (syntax deference): herdr syntax comes from `herdr --skill` / the
  installed CLI. No fabricated flags, no invented `workspace move --session`.
