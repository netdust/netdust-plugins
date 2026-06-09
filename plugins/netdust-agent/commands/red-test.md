---
description: Run a discipline skill's RED-test pressure scenarios — baseline (skill off) vs verified (skill on) — to check for regression after editing a skill
allowed_tools: ["Bash", "Read", "Agent"]
arguments: "skill-name"
---

Run the RED-test regression check for a discipline skill.

## Pre-check

- Argument required: skill name (e.g. `wp-security`).
- Resolve the skill: glob `~/.claude/plugins/netdust-*/skills/<skill-name>/red-tests.md` — works across core, wp, and statamic.
- If missing → stop. Tell the user: "No red-tests.md for `<skill>`. Reference skills don't need this. Discipline skills should have one."

## Method

For each scenario in `red-tests.md`:

1. **Baseline run** — spawn a subagent (via the `Agent` tool, `subagent_type: general-purpose`) with a system-prompt prefix that tells it the `<skill-name>` skill is OFF (do not invoke it). Paste the scenario prompt verbatim. Capture the output verbatim.

2. **Skill-on run** — spawn another subagent with the same scenario but no skill-disable. Capture output verbatim.

3. **Compare**: did the baseline exhibit the failure modes the skill is meant to prevent? Did the skill-on run avoid them?

4. **Record** to the same plugin's `~/.claude/plugins/netdust-*/skills/<skill-name>/red-tests-log.md` (append; create if missing):
   ```
   ## YYYY-MM-DD HH:MM — <skill> regression test
   ### Scenario N — <one-line>
   Baseline behavior: <summary>
   Skill-on behavior: <summary>
   Regression? yes | no
   ```

## Output to the user

After all scenarios:

```
RED-test result — <skill>
=========================
Scenarios run: N
Regressions: M

[if M > 0]
Regressions found:
1. Scenario N — <one-line>: skill-on failed to prevent <pillar>. See red-tests-log.md.

Suggested action: open <skill>/SKILL.md and harden the rationalization table or loophole closures for the failing case.

[if M == 0]
No regressions. Skill holds up under all <N> pressure scenarios.
```

## Boundaries

- Do not edit the skill body — only diagnose.
- Do not append to lessons.md (that's for real session edge cases, not synthetic tests).
- Spawn subagents one at a time, not in parallel — the comparison must be apples-to-apples.
- If a scenario produces no clear baseline failure (the agent already does the right thing without the skill), note that as "scenario may be too easy — needs harder pressure" rather than passing the skill on it.
