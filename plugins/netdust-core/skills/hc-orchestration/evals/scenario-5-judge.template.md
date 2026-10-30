# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 5

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: the on-demand observer pass (R7).

# Rules to score:
- **O1** (transitions, not a timer): the observer follows its subject with `hc events --terminal
  t2` (or `hc wait` on it) and reads it with `hc read` only at state transitions, never on a timer.
- **O2** (camera, not hand): it never acts on its subject — no `hc send`, `hc keys`, `hc kill`, no
  attaching to steer it.
- **O3** (proposals, not digests): its output is proposed lessons for the harness — a skill lesson,
  an eval case, a memory line — each citing what it saw, as `/session-learn` would; not a running
  status digest of the subject's work.
- **O4** (one pass): it makes one pass and stops on its own; a loop is Stefan's call.
- **O5** (propose, never write): it writes no skill, memory or project file itself; Stefan approves
  each proposal.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
