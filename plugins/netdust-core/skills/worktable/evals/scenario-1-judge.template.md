# JUDGE PROMPT TEMPLATE — worktable scenario 1

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: a mid-plan stop, with Studio a day behind a revised plan.

# Rules to score:
- **K1** (missing steps created right): Task 3 and Task 5 are created as taak rows with `stap` "Task 3" / "Task 5",
  `werkpakket_id` 12, `wie` claude and NO deadline.
- **K2** (finished step): row 41 (Task 2) goes to `gedaan`, with a one-line note that names commit 4f1c2a9.
- **K3** (revisions mirrored, nothing deleted): row 43 gets the new title "Order summary"; row 44 (dropped Task 6)
  is set to `overgeslagen` with a reason — no delete call anywhere.
- **K4** (Stefan's row): row 45 is not touched at all.
- **K5** (feature last, derived fields untouched): the werkpakket update (laatste_stap / volgende_stap) comes after
  every taak write, and no call sends `voortgang` or `bijgewerkt`.
- **K6** (next step started): Task 3's row goes to `bezig`.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
