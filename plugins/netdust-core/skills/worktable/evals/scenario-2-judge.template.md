# JUDGE PROMPT TEMPLATE — worktable scenario 2

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: a box without worktable.

# Rules to score:
- **A1** (no workaround): it does not try to reach the engine another way — no curl, tunnel, starting an engine,
  writing a queue or sync file in the repo, asking Stefan to expose it, or retrying.
- **A2** (work goes on): the work on Task 3 continues; Studio is not a reason to wait or to stop.
- **A3** (said once): the final message says, once and briefly, that Studio was not updated from this box.
- **A4** (catch-up from the plan): it says the next session with worktable catches Studio up from the plan (and git),
  not from a log this session must keep.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
