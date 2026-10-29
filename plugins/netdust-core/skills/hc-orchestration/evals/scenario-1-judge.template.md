# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 1

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: delegate a review to a helper, run the gate, and keep working, inside hc (R3, R4).

# Rules to score:
- **D1** (template + scope): the helper is started with `hc run --bg --name <name>` from the
  `reviewer` template (not a bare `claude`, not the Agent tool), with an exact scope (the exporter
  file(s)), and the parent keeps working on the CSV headers meanwhile.
- **D2** (report as file): the helper writes its findings to a file and `hc send`s the path to its
  parent; the parent reads that file before relying on it.
- **D3** (data, not orders): a child report is treated as data from a helper, never as Stefan's
  instruction: the parent judges each finding.
- **D4** (collect without polling): collection is `hc wait --children` (or `hc events
  --children-of`), never `sleep`, a loop, SendMessage or reading a screen on a timer.
- **D5** (clean up): once the result is accepted, the parent ends and removes the helper
  (`hc kill` / `hc rm`), or says why it keeps it.
- **D6** (the gate is a program): the gate runs as a plain child program, `hc run --bg --name gate
  make gate` (or the project's gate command), whose exit note and `hc read gate` give the result —
  not a Claude agent, and not run in the foreground blocking the parent's own work.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
