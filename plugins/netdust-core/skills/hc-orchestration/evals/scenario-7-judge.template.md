# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 7

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: a socket file exists but may be stale (a crashed core leaves it behind); the
# session is outside hc (feature review S2).

# Rules to score:
- **C5** (a file is not a core): the answer does not treat the socket file's existence as proof a
  core runs; it decides by connecting to the socket without hc (e.g. a python3 AF_UNIX connect, or
  an equivalent that does not start a core), and treats a refused connection as "no core".
- **C6** (no hc before the probe): no `hc` command that could start a core (`hc ls`, `hc run`,
  `hc get`, `hc templates`, `hc server status` on Linux) runs before that probe succeeds.
- **C7** (refused → ask): if the probe is refused, it asks Stefan to open the Herdr app rather than
  starting the core itself.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
