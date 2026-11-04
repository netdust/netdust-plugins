# JUDGE PROMPT TEMPLATE — hc-orchestration scenario 8

# This file is a TEMPLATE. Inline both legs' outputs below before dispatching the
# judge. Score each rule PASS/FAIL per leg, with one line of evidence quoted from
# the leg. The skill earns its keep only if the skill-on leg passes the rules the
# baseline leg fails, and fails none the baseline passes.

# Scenario: Stefan asks for the coder of a feature in another repo to be opened as its own space
# in the Herdr app (session 2026-11-04: the reviewer had to rediscover the app, the machine flag
# and the label form).

# Rules to score:
- **A1** (the app makes spaces): the space is created with the Herdr app's CLI (`herdr-app`, found
  as the Windows binary under /mnt/c/Users/*/AppData/Local/Programs/herdr-app/ or equivalent), not
  by an hc command and not by guessing a label into existence.
- **A2** (on the right machine): the space command names the WSL machine (`--machine wsl`) and the
  repo's checkout as its folder, so the space does not open on Windows.
- **A3** (labelled into it): the coder is started with hc's `coder` template, `--bg` and
  `--outlive-parent`, labelled `herdr.space=<the new space's id>` with the machine prefix stripped,
  and a `herdr.tab`.
- **A4** (the current address): the brief names the reviewer as the address read now (`t2r` /
  `$HC_TERMINAL_ID`), never yesterday's `t1y`.

## BASELINE leg output

{{BASELINE}}

## SKILL-ON leg output

{{SKILL_ON}}
