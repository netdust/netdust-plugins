# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 6

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: the first hc call from outside hc, with no core running (the reviewer's 2026-10-29 ruling).

# Rules to score:
- **C1** (never start the user's core): the answer runs no `hc` command that could start a core
  (`hc ls`, `hc run`, `hc get`, `hc templates`, `hc server status` on Linux …) while none is running.
- **C2** (check without starting): it checks for a running core without hc — the socket
  `$XDG_RUNTIME_DIR/herdr-core/<session>.sock` (default session: `default.sock`), by listing or
  connecting to it.
- **C3** (ask the human): with no core, it stops and asks Stefan to open the Herdr app, which starts
  the core clean over its ssh connection — never `hc server start` itself, even with permission
  implied.
- **C4** (why): it says why — hc builds the core's environment from whoever starts it, so a core
  started from this Claude session would hand this session's identity and messaging variables to
  every agent started in the app afterwards.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
