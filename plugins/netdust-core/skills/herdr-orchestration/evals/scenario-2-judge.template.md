# JUDGE PROMPT TEMPLATE — herdr-orchestration scenario 2

# This file is a TEMPLATE. Inline both legs' outputs before dispatching the
# judge. Score each rule PASS/FAIL per leg; the skill earns its keep only if
# the skill-on leg passes rules the baseline leg fails.

# Scenario: an update is proposed while a dispatch is in flight, inside herdr,
# with an unidentified neighbor pane. Task: protect the dispatch, identify the
# neighbor, state the recovery path.

# Rules to score:
- **H8** (restart boundary): the update is DEFERRED until the dispatch settles.
  The answer distinguishes detach (processes survive) from a server restart
  (layout, cwd and focus return; processes do not). It does not treat
  `herdr update --handoff` as a safe default — at most an experimental
  exception.
- **H9** (durable artifact): the dispatch's durable output is named as the
  branch / worktree commits, NOT the pane or its scrollback. Recovery after a
  restart is re-starting the agent and re-reading state from git — not scraping
  terminal history.
- **H10** (peer identification): the neighbor's task is determined from herdr
  state — `herdr api snapshot` (or `agent list`) joined on `cwd`, reading
  `terminal_title_stripped` for the conversation title — rather than by reading
  its screen, guessing, or messaging it as the FIRST move.
- **H11** (integration honesty): if agent integrations are mentioned, the answer
  states they supply native session identity for resumption and do NOT make
  lifecycle detection reliable; Claude Code panes stay screen-detected. No claim
  that installing an integration fixes `blocked`/`unknown` classification.
- **H12** (no invented syntax): herdr commands are taken from `herdr --skill` /
  the installed CLI. No fabricated flags or subcommands.
