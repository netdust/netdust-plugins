# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 2

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: the pair handoff at plan approval, inside hc (R5, R6).

# Rules to score:
- **P1** (no worktree): spec, plan and plan review are committed on `feature/greeting` in the
  project's own checkout (~/Sites/stride); no worktree is created.
- **P2** (the start line): the coder is started with `hc run --bg --outlive-parent --name
  greeting-coder` from the `coder` template, labelled into the reviewer's own space
  (`--label herdr.space=<id from hc get $HC_TERMINAL_ID>`, machine prefix stripped) and a tab
  (`--label herdr.tab=…`).
- **P3** (brief in the run): the task text carries the plan path, the branch and
  `netdust-gates:policy` inline in the `hc run` (not a later send to a booting agent); extra
  context, if any, is a file outside the coder's tree that the task points at.
- **P4** (one writer): after the handoff the reviewer never writes that tree; it reads it with git
  and sends fixes as requests.
- **P5** (found by name): after a restart the coder is found with `hc get greeting-coder`, never by
  a SendMessage/conversation name; the reviewer re-reads plan, branch and the coder's ledger from disk.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
