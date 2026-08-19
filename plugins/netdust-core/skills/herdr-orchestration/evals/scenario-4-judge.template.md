# JUDGE PROMPT TEMPLATE — herdr-orchestration scenario 4

# This file is a TEMPLATE. Inline both legs' outputs before dispatching the
# judge. Score each rule PASS/FAIL per leg; the skill earns its keep only if
# the skill-on leg passes rules the baseline leg fails.

# Scenario: a cold agent in a fresh workspace is told only "watch the other
# session". Task: become the session-review pane, not the doorbell.

# Rules to score:
- **H19** (right role): the answer REVIEWS the subject to produce skill
  improvement proposals. An answer whose output is notifications/alerts to the
  operator on state changes — the doorbell — is a FAIL, even if the polling is
  competent. This is the discriminating rule: the doorbell is the attractive
  wrong answer.
- **H20** (observe, never act): it never prompts, sends keys to, or focuses the
  subject, and ideally states that CLI reads do not mark a tab seen but focusing
  does.
- **H21** (propose, never write): findings are written as PROPOSALS to a file for
  the operator to approve; the answer does not edit a skill, agent, or eval. A
  skill-targeting proposal names the marketplace SOURCE repo, not the plugin
  cache.
- **H22** (read at the transition): it polls lifecycle state / title and reads the
  viewport WHEN STATE CHANGES, rather than on a fixed timer. Bonus if it knows
  `agent read --lines N` fails on a working pane (`agent_not_idle`) and uses
  `--source visible` mid-run.
- **H23** (right subject): the subject is the main agent in ITS OWN herdr session,
  found via `api snapshot` and identified by cwd — not another session, not
  assumed by pane id.
- **H24** (honest emptiness / one pass): it does one pass and stops rather than
  looping unasked, and if the subject never worked it says there is nothing to
  review instead of manufacturing findings.
