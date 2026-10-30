# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 3

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: an urgent hotfix during a running coder, plus a non-urgent planning request (R6).

# Rules to score:
- **W1** (urgent → worktree, right place): the production 500 gets a temporary worktree under
  `~/.herdr/worktrees/worktable/<branch>`, never in ~/Sites and never in the coder's checkout.
- **W2** (removed when landed): that worktree is removed once the hotfix lands.
- **W3** (DDEV): the hotfix worktree gets its own DDEV project name before anything runs in it.
- **W4** (non-urgent waits): planning the calendar sync gets NO worktree and does not write the
  coder's tree: it waits for the coder, or is planned without writing the tree.
- **W5** (coder untouched): the coder (t7) and its checkout are not interrupted or written to.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
