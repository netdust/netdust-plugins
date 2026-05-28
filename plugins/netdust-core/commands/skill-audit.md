---
description: Audit harness skills for drift — flag skills with stale lessons, contradictions vs recent project STATE.md, or no activity in 90 days
allowed_tools: ["Bash", "Read"]
---

Audit all harness skills across `~/.claude/plugins/netdust-*/skills/*/` for drift. Output: numbered list of candidates for the user to review. **Do not auto-edit skills.**

## What to check

For each skill in `~/.claude/plugins/netdust-*/skills/*/`:

1. **Lessons activity**: when was `lessons.md` last modified? If never modified (still empty) or > 90 days, flag as "no recent lessons added."
2. **Body vs lessons consistency**: read SKILL.md and lessons.md. If any lesson entry contradicts a rule in the body (e.g. body says "always X", lesson says "X failed when Y, do Z"), flag with the specific contradiction.
3. **Body vs reality**: grep recent `~/Sites/*/memory/STATE.md` for the skill's name. If the skill is mentioned often but its body hasn't been edited in 90 days, flag as "high-usage skill, stale body."
4. **Description quality**: read the SKILL.md frontmatter `description:`. If it summarizes workflow instead of listing triggers/symptoms/keywords (per Obra's writing-skills convention), flag as "description summarizes workflow — should be trigger-shaped."

## Output format

```
Skill audit — YYYY-MM-DD
========================

Skills checked: N
Flagged: M

1. <skill-name> — <flag type>
   <one-line detail>
   Path: <skill SKILL.md path>

2. ...
```

If nothing is flagged, output: "All skills look healthy. No drift detected."

## Boundaries

- Do not edit any skill file.
- Do not delete or rename anything.
- This is a reporting command. The user decides what to act on.
