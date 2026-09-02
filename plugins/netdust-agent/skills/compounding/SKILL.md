---
name: compounding
description: Close the learning loop at spec-close or on "compound this session" — harvest what the session taught into the places future sessions actually read (CODE-MAP, skill/agent lessons, evals), as PROPOSALS the human approves. Never auto-writes. This is how the agents and skills improve instead of re-deriving the same knowledge every session.
---

# Compounding — what did this session teach, and where does it land?

Knowledge not written at a boundary evaporates and gets re-derived. One pass at
spec-close (or when the human says "compound"), three destinations, all report-only —
you propose, the human approves, then you write.

## Pass A — the codebase record → `docs/architecture/CODE-MAP.md`

Decisions and traps only — the rules this session discovered about how THIS codebase
works and why. Never inventory (no method lists, counts, line numbers — those drift; a
wrong map is worse than none because it gets trusted). Skip anything mid-flight: map
what landed, not what's about to move.

## Pass B — the tools record → skill/agent `lessons.md` + evals

When the session exposed a skill or agent behaving wrong (a missed trigger, bad
guidance, a gap the session paid for):

- Append the lesson to that skill's `lessons.md` **in the marketplace SOURCE repo**
  (`~/.claude/plugins/marketplaces/netdust-plugins/plugins/<plugin>/skills/<skill>/`) —
  never the cache; cache edits are lost on update.
- **If the lesson changes what the skill should DO, the change ships with an eval case**
  (`evals/`) that would have caught the old behaviour — same RED-first discipline as
  code. A lesson without an eval is a hope; an eval is a regression pin.
- Structural fixes to a skill/agent body are proposed as diffs, not applied silently —
  `/skill-audit` is the review path.

**The session-review pane's proposals are Pass B input.** When
`memory/session-review/*-proposals.md` exists (written by the herdr session-review pane,
`netdust-core:herdr-orchestration`), read it and fold each proposal into the manifest
with its evidence — the pane observed what this session could not see about itself.
Same rule: propose, the human approves, then write.

## Pass C — already automatic, don't duplicate it

The session-stop hook captured `DECISION:` / `RISK:` / `LESSON:` / `TODO:` tags into the
project's `memory/` during the session. Compounding adds only what needs *judgment about
where it lands* — the cross-session, cross-project knowledge the hook can't route.

## The report

One manifest: proposed CODE-MAP delta · proposed lessons (per skill, with its eval case)
· what was deliberately NOT compounded and why. Human approves items; you apply exactly
those. Cadence: spec-close / session-close — never per sub-phase, never for trivia.
