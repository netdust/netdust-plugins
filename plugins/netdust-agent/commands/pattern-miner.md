---
description: Mine ~/Sites/*/memory/STATE.md + lessons.md for recurring patterns worth promoting to a harness skill
allowed_tools: ["Bash", "Read"]
---

Read every `~/Sites/*/memory/STATE.md` and `~/Sites/*/memory/lessons.md` that exists. Surface recurring patterns across projects that might deserve:

- A new harness skill
- An addition to an existing skill body
- A new entry in `~/.claude/plugins/netdust-wp/memory/GLOBAL.md`

**Do not auto-edit anything.** Surface candidates; the user decides.

## What counts as a "recurring pattern"

- The same gotcha appears in lessons.md of 2+ projects
- The same decision pattern appears in STATE.md of 2+ projects (e.g. "we always disable plugin X in staging")
- A skill is referenced in STATE.md but the agent had to re-derive its content because the skill body was missing that case
- A class of risk (e.g. "Redis cache exclusions", "FluentCRM webhook timing") appears across multiple projects

## Method

1. Enumerate: `find ~/Sites -maxdepth 3 -path '*/memory/STATE.md' -o -path '*/memory/lessons.md'`
2. Read each. (Skip if >500 lines — too big to compare; flag separately as "candidate for curation".)
3. Look for keyword/phrase overlap across files.
4. Group findings by theme.

## Output format

```
Pattern mining — YYYY-MM-DD
Sites scanned: N (S with STATE.md, L with lessons.md)

CANDIDATES (M)
==============

1. <theme>
   Pattern: <one-line description>
   Seen in: project-a (lessons.md), project-b (STATE.md L42), project-c (lessons.md)
   Suggested action: new skill OR add to <existing-skill>/lessons.md OR add to GLOBAL.md
   Confidence: high | medium | low

2. ...

OVERSIZED FILES (need curation):
- <path> (<N> lines)
```

If no patterns are found across multiple projects: "No cross-project patterns surfaced this run. Each project is on its own island, which is normal for diverse client work."

## Boundaries

- Read-only. Never edit STATE.md, lessons.md, or any skill file.
- Do not include single-project observations — those belong in that project's STATE.md, not as harness candidates.
- Confidence is your honest signal: if two mentions could be coincidence, say `low`.
