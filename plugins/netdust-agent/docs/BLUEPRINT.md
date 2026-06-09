# `netdust-agent` — Blueprint

> **Status:** proposal for review. Nothing built yet. This doc is the layer map you approve before any `SKILL.md` is written.

## The model (one sentence)

> **Harness = the skeleton** (steps, gates, ordering, "don't skip"). **Craft = the how-to** the harness reaches for at each step.

`netdust-agent` is a **standalone** plugin that holds the *full two-layer harness*. It is intended to eventually **replace the harness pieces** of `netdust-core`. `netdust-core` keeps the non-harness infra it owns today: per-project memory, session hooks, the reviewer agents, the ploi MCP, and `/deploy`. We build `netdust-agent` clean; retiring the old harness skills from core is a later, separate call.

---

## Naming convention (the legibility rule)

No subfolders. **The name carries the role.** You read the skill list and know instantly which layer a skill is in:

| Layer | Name shape | Reads like | Examples |
|---|---|---|---|
| **Harness** (control flow — when/whether) | phase / gate **noun** | a *checkpoint* | `harnessed-development`, `testing-workflow`, `threat-modeling`, `shake-out` |
| **Craft** (how-to — the actual doing) | **gerund** (`-ing`) | a *capability* | `writing-tests`, `designing-apis`, `building-frontend`, `engineering-context`, `versioning-with-git` |

Scan rule: **gerund = how-to (craft); phase/gate noun = when/whether (harness).**

---

## Authority rule (whose file, whose citation)

When one of *your* skills and an addy/superpowers skill cover the same ground:

> **Your skill is the authoritative `SKILL.md`. The addy/superpowers content is woven IN as reinforcement — not added as a parallel file.**

So `writing-tests` is *one* file, in your voice, following your harness — with addy's red-green mechanics, test-pyramid, DAMP-over-DRY, and rationalizations table folded into the body where they strengthen it. Superpowers is the base; addy fills gaps; your discipline is the spine.

---

## Layer 1 — Harness (the skeleton)

These are **sequencers and gates**, not how-to. They decide *when* something fires and *prove* it fired. `harnessed-development` stays the single entry point (a pure sequencer — at each stage it loads the right craft skill and wraps a gate around it; it does not itself teach craft).

| Skill | Role | Source |
|---|---|---|
| `harnessed-development` | **Entry point.** Sequences the full pipeline: brainstorm → plan(+gates) → execute → shake-out → finish. | yours (port from core) |
| `writing-plans` *(harness)* | Gate: spec → plan → tasks. The "how to go from spec to a task list" step you asked for. | superpowers base + your structure |
| `testing-workflow` | Gate: per-task, *what tier of test does this need, prove it's RED-first*. | yours |
| `threat-modeling` | Gate: inject `## Threat model` into the plan when triggers match. | yours |
| `architecture-invariants` | Gate: name convergence points; review flags bypasses. | yours |
| `feature-acceptance` | Gate: author + drive the acceptance-flows matrix. | yours |
| `test-effectiveness` | Gate: would the green suite actually go RED? (audit altitude) | yours |
| `shake-out` | Gate: spec-complete pre-merge sweep. | yours |
| `finishing-a-branch` *(harness)* | Gate: merge / PR / cleanup decision. | superpowers base |
| `compounding` | Gate: spec-close harvest into CODE-MAP + skills. | yours |
| `evaluating` *(harness)* | Gate: process retro — how the work was executed. | yours (`/evaluate`) |

> Note: a few of these keep noun names that already read as gates (`testing-workflow`, `shake-out`). The convention is about *legibility*, not forcing `-ing` onto gates — gerunds are reserved for craft so the contrast stays sharp.

## Layer 2 — Craft (the how-to the harness reaches for)

Gerund-named. These are what the harness *loads* at each step. Superpowers = base; addy = fills; your content folded in where yours is better.

| Craft skill | Reached for at harness step | Base | Reinforced by (addy/sp) | Your authority folded in |
|---|---|---|---|---|
| `writing-tests` | `testing-workflow` gate | superpowers:TDD | addy `test-driven-development` (red-green, test-pyramid, DAMP, Real>Fakes>Stubs>Mocks, AAA) | your risk-tier A/B model is the spine; the seven green-but-blind failure modes from `test-effectiveness` |
| `designing-apis` | plan stage, when brainstorm concludes "we need an API" | addy `api-and-interface-design` | Hyrum's Law, contract-first, additive-only, branded types, structured errors | your convergence-point vocabulary (errors converge in one place, validation at the boundary) |
| `building-frontend` | execute stage, UI tasks | frontend-design plugin + addy `frontend-ui-engineering` | component architecture, state-tool ladder, a11y WCAG-AA, responsive breakpoints, anti-AI-aesthetic | — (genuinely new how-to your harness lacks; mostly faithful) |
| `engineering-context` | session start / task switch | addy `context-engineering` | context hierarchy, packing strategies, surface-ambiguity-not-guess | **re-point at YOUR three-layer memory model** (atomic recall / fleet / per-project) — do NOT let it invent a parallel memory scheme |
| `versioning-with-git` | execute + finish stages | addy `git-workflow-and-versioning` | atomic commits, conventional messages, save-point pattern, worktrees, bisect | **defer infra to your `dev-stack`** (Makefile/branching/DDEV) — this skill is commit *craft*, not your branch *flow* |
| `driving-the-browser` | `feature-acceptance` + debugging | superpowers-chrome:browsing (CDP mechanics) + addy `browser-testing-with-devtools` (mechanics half only) | DevTools tool table, console/network/perf inspection, screenshot verification | **test-STRATEGY half stripped out** → defers to `feature-acceptance`. This skill = *how to operate the browser*, not *what to verify* |
| `refining-ideas` | Stage 0, beside brainstorming | addy `idea-refine` | divergent→convergent, inversion/10x lenses, "Not Doing" list, assumption surfacing | sits *next to* superpowers:brainstorming (refine vs generate) — cross-link, don't merge |
| `deploying` | finish stage | your `/deploy` + `dev-stack` | — | your 9-method dispatcher is the authority; this is a thin how-to pointer |
| `simplifying-code` | review stage | your `code-simplicity-reviewer` agent + `/simplify` | addy `code-simplification` (reduce complexity, preserve behavior) | your agent stays the doer; skill is the how-to it embodies |
| `sourcing-from-docs` | any stage making an API/behavior claim | addy `source-driven-development` | cite official docs before asserting; context7 MCP | **NEW discipline you lack** — high-value, cheap |
| `doubting-decisions` | post-plan / post-build | addy `doubt-driven-development` | adversarial fresh-context review of *decisions* | distinct from your devils-advocate (business) / thinking-deeply (technical) |

---

## Collisions resolved (the ones that needed real thought)

1. **browser**: `driving-the-browser` (craft: how to operate Chrome) vs `feature-acceptance` (harness gate: what flows to prove) vs superpowers-chrome (CDP base). → addy's *test-strategy* half is stripped; the skill keeps only mechanics and **defers strategy to `feature-acceptance`**. No three-way trigger fight.
2. **git**: `versioning-with-git` (craft: commit hygiene) vs your `dev-stack` (infra: branch flow, Makefile). → split on commit-craft vs branch-flow; cross-link.
3. **ideation**: `refining-ideas` vs superpowers:brainstorming. → refine-vs-generate; siblings, cross-linked, not merged.
4. **memory**: `engineering-context` must point at YOUR three-layer memory, not invent one.

---

## Plugin skeleton (files to create)

```
plugins/netdust-agent/
  .claude-plugin/plugin.json        # manifest (mirror netdust-core's shape)
  CLAUDE.md                          # the two-layer model, the naming + authority rules
  README.md
  skills/
    harnessed-development/SKILL.md   # entry sequencer (port + point at craft layer)
    writing-plans/SKILL.md
    writing-tests/SKILL.md
    designing-apis/SKILL.md
    building-frontend/SKILL.md
    engineering-context/SKILL.md
    versioning-with-git/SKILL.md
    driving-the-browser/SKILL.md
    refining-ideas/SKILL.md
    sourcing-from-docs/SKILL.md
    doubting-decisions/SKILL.md
    simplifying-code/SKILL.md
    deploying/SKILL.md
    # (harness gates — testing-workflow, threat-modeling, shake-out, etc. —
    #  ported from core or referenced; see "relationship to core" open question)
  + register in .claude-plugin/marketplace.json
```

## Decisions (resolved 2026-06-09) — built

- **A. RESOLVED → copied in.** Gate skills (`testing-workflow`, `threat-modeling`, `architecture-invariants`, `feature-acceptance`, `test-effectiveness`, `shake-out`, + the `harnessed-development` sequencer and `_shared/`) are copied into `netdust-agent` — true standalone. Caveat: until netdust-core's harness copies are retired, do not let the two drift silently. `compounding` was NOT copied; the sequencer still references `netdust-core:compounding` for the spec-close step.
- **B. RESOLVED → slice first, then batched.** `writing-tests` ↔ `testing-workflow` was proven first (thin-delegate to `superpowers:test-driven-development`, wired both ways), then the remaining 10 craft skills were batched via parallel subagents to that pattern.
- **C. RESOLVED → both included.** `sourcing-from-docs` and `doubting-decisions` are built (Stefan: all of addy is fair game).

## Craft-layering rule (locked, applied to all 11)

A craft skill LAYERS ON TOP of its base, never replaces it:
- **Has a superpowers/plugin base** (thin-delegate): `writing-tests`→`superpowers:test-driven-development`; `refining-ideas`→`superpowers:brainstorming`; `driving-the-browser`→`superpowers-chrome:browsing`; `building-frontend`→`frontend-design` plugin; `versioning-with-git`→`superpowers:using-git-worktrees` (worktrees only). These load the base for generic mechanics, add only the Netdust harness layer.
- **No strong base** (restate-and-extend from addy): `designing-apis`, `engineering-context`, `sourcing-from-docs`, `doubting-decisions`, `simplifying-code`. Carry more of their own content but still frame as the how-to a harness step reaches for.
- **Thin pointer to a Netdust authority**: `deploying`→`/deploy` + `dev-stack`.

The `harnessed-development` sequencer carries a `<craft_routing>` table mapping each stage's GATE (when/whether) to the CRAFT skill (how-to) it reaches for. That table is the mechanism that satisfies "use general skills to improve HOW the agent implements the gates."

## Still open

- Retire netdust-core's harness skill copies once `netdust-agent` is adopted (the standalone-replacement endgame).
- `writing-plans` and `finishing-a-branch` were NOT copied as local harness skills — the sequencer references `superpowers:*` for those directly (they are pure superpowers bases with no Netdust gate wrapper needed). Revisit if a Netdust wrapper becomes warranted.
- Eval/red-test the new craft skills' descriptions for trigger accuracy (`/skill-audit`, `netdust-core:red-test`).
