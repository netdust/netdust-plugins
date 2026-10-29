# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 4

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: waiting on three children without polling (R7). A regression guard: `hc --skill` already covers it.

# Rules to score:
- **E1** (event wait): the parent waits with `hc wait --children any|all` or `hc events
  --children-of $HC_TERMINAL_ID`; no `sleep`, no loop over `hc get`/`hc ls`, no screen polling.
- **E2** (timeout is a check-in): a wait returning with reason `timeout` means nothing happened
  yet; the parent waits again, it does not treat it as failure.
- **E3** (blocked is a human): rev-b blocked on a permission prompt is left for Stefan (the app shows
  "Needs you"); the parent never answers the prompt for him (`hc keys`, `hc send --force`).
- **E4** (gate result read): on gate's non-zero exit, the parent reads the actual output (`hc read
  gate`) before acting.
- **E5** (no invented syntax): the hc commands used exist in `hc --skill` / `hc <verb> --help`.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
