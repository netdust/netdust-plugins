# netdust-agent — the two-layer harness

This plugin holds the full Netdust development harness, organized around one idea:

> **Harness = the skeleton** (steps, gates, ordering, "don't skip").
> **Craft = the how-to** the harness reaches for at each step.

The harness decides *when* and *whether*. The craft is *how to actually do it*. Keeping them as distinct, legibly-named layers is the whole point of this plugin.

---

## The two layers

### Layer 1 — Harness (control flow)

These skills are **sequencers and gates**. They do not teach craft; they decide what fires, in what order, and prove it fired. `harnessed-development` is the single entry point — a pure sequencer that, at each stage, loads the right craft skill and wraps a gate around it.

- `harnessed-development` — entry point; sequences brainstorm → plan(+gates) → execute → shake-out → finish
- `writing-plans` — gate: spec → plan → tasks
- `testing-workflow` — gate: per-task, *what tier of test does this need, prove it's RED-first*
- `threat-modeling` — gate: inject `## Threat model` when triggers match
- `architecture-invariants` — gate: name convergence points; flag bypasses
- `feature-acceptance` — gate: author + drive the acceptance-flows matrix
- `test-effectiveness` — gate: would the green suite actually go RED?
- `shake-out` — gate: spec-complete pre-merge sweep
- `finishing-a-branch` — gate: merge / PR / cleanup
- `compounding` — gate: spec-close harvest into CODE-MAP + skills
- `evaluating` — gate: process retro

### Layer 2 — Craft (the how-to the harness reaches for)

These are what the harness **loads** at each step. Gerund-named.

- `writing-tests` — reached for by `testing-workflow`; RED→GREEN-within-a-task mechanics
- `designing-apis` — reached for at plan stage when an API is needed
- `building-frontend` — reached for at execute stage for UI tasks
- `engineering-context` — reached for at session start / task switch
- `versioning-with-git` — commit-craft (branch *flow* stays in the stack's dev-stack)
- `driving-the-browser` — how to operate Chrome (test *strategy* stays in feature-acceptance)
- `refining-ideas` — divergent→convergent ideation (sibling to brainstorming)
- `sourcing-from-docs` — cite official docs before asserting API behavior
- `doubting-decisions` — adversarial fresh-context review of a decision
- `simplifying-code` — reduce complexity, preserve behavior
- `deploying` — thin how-to over the stack's deploy dispatcher

---

## The naming convention (the legibility rule)

No subfolders. **The name carries the role.** Read the skill list, know the layer:

| Layer | Name shape | Reads like |
|---|---|---|
| Harness | phase / gate **noun** | a checkpoint (`testing-workflow`, `shake-out`) |
| Craft | **gerund** (`-ing`) | a capability (`writing-tests`, `designing-apis`) |

Scan rule: **gerund = how-to (craft); phase/gate noun = when/whether (harness).** Gerunds are reserved for craft so the contrast stays sharp — a few gates keep noun names that already read as checkpoints.

## The authority rule (whose file, whose citation)

When a Netdust skill and an upstream skill (superpowers, addyosmani/agent-skills) cover the same ground:

> **The Netdust skill is the authoritative `SKILL.md`.** Upstream content is woven IN as reinforcement — never added as a competing parallel file.

Superpowers is the base; addyosmani fills genuine gaps; Netdust discipline is the spine. A craft skill cites the gate that reaches for it, and the gate cites the craft it loads — wired both ways.

## Provenance

- Harness discipline + risk-tiering + the gate sequence: Netdust harness discipline.
- Base process skills: `superpowers:*`.
- Craft fills: concepts learned from `addyosmani/agent-skills` (MIT) — folded into Netdust-voiced skills, not copied verbatim.

## Standalone harness

This plugin is fully self-contained. It holds the complete two-layer harness — the `harnessed-development` sequencer, every gate it fires (testing-workflow, threat-modeling, architecture-invariants, feature-acceptance, test-effectiveness, shake-out, compounding), the craft skills the gates reach for, the reviewer/specialist agents, the session + guard hooks, and its own commands (`/deploy`, `/shakeout`, `/evaluate`, …). Nothing here depends on or defers to another Netdust plugin: every skill, gate, command, and agent it references resolves WITHIN this plugin (or to an external `superpowers:*` / `superpowers-chrome` base). It supersedes the older Netdust core harness — this plugin is now the sole home for that discipline.
