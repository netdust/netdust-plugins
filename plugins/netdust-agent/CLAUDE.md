# netdust-agent — the two-layer harness

This plugin holds the full Netdust development harness, organized around one idea:

> **Harness = the skeleton** (steps, gates, ordering, "don't skip").
> **Craft = the how-to** the harness reaches for at each step.

The harness decides *when* and *whether*. The craft is *how to actually do it*. Keeping them as distinct, legibly-named layers is the whole point of this plugin.

---

## The two layers

### Layer 1 — Harness (control flow)

These skills are **sequencers and gates**. They do not teach craft; they decide what fires, in what order, and prove it fired. `harnessed-development` is the single entry point — an intake ROUTER that classifies the work (Class A–F) and routes it to the two spines, which meet at an enforced seam: an approved `tasks.md` with `spec-kit/gate-check.py` GREEN. `planning` stops there; `building` refuses to start without it.

- `harnessed-development` — entry point; intake router only (class dial A–F → spine; F = vision-brief, brainstorm-only, no plan/tasks artifact)
- `planning` — PLAN spine; sequences brainstorm → (spec-authoring) → plan(+gates 1a–1g, task-shaping 1d/1f/1h) → (spec-analysis); STOPS at the seam for human approval. Presence-aware: inline in the main conversation while the human is steering, dispatched background `planner` once unattended — the pre-unattended ladder (gate-check GREEN, seam approval, doubting-decisions) gates either way.
- `building` — BUILD spine; precondition = the seam artifact; sequences execute (per-task testing + standards gates, review-cluster HALTs, optional armed `/loop`) → shake-out → finish → compounding. Stage 2's test/dev split is tier-conditional: an independent test-author writes the RED test first for Tier-A security-boundary tasks (the plan's `Test-author: split` field, machine-checked by `gate-check.py`'s test-author-mode check); other tasks run solo RED-first TDD.
- `superpowers:writing-plans` (upstream base, not a local skill) — gate: spec → plan → tasks
- `spec-authoring` — gate (spec-kit graft, Stage 0.5): wraps `/speckit.specify` + `/clarify`; HALTs on unresolved `[NEEDS CLARIFICATION]`
- `spec-analysis` — gate (spec-kit graft, Stage 1.5): `/speckit.analyze` + mechanical `gate-check.py` — the pre-execution barrier that machine-checks 1a/1b/1d/1f
- `run-trace.py` / `run-score.py` (spec-kit) — in-loop event trace + evaluator rubric: `loop-gate.py` emits decision events automatically (fail-open); `/shakeout` surfaces the graded rubric at spec-close; report-only, no new gate. `run-trace.py show --durations` adds per-segment timing; `run-cost.py` is a strictly read-only transcript miner emitting per-dispatch/per-stage token tables — same report-only posture, no new gate
- `standards-gate` — gate (Step 2.6b): runs the project linter at each code-task close; backstopped by `subagent-stop.py`
- `constitution-bridge` — setup: generates the spec-kit constitution as a view over RULES/SOUL/invariants
- `testing-workflow` — gate: per-task, *what tier of test does this need, prove it's RED-first*
- `threat-modeling` — gate: inject `## Threat model` when triggers match
- `architecture-invariants` — gate: name convergence points; flag bypasses
- `feature-acceptance` — gate: author + drive the acceptance-flows matrix
- `test-effectiveness` — gate: would the green suite actually go RED?
- `shake-out` — gate: spec-complete pre-merge sweep
- `superpowers:finishing-a-development-branch` (upstream base, not a local skill) — gate: merge / PR / cleanup
- `compounding` — gate: spec-close harvest into CODE-MAP + skills
- `/evaluate` (a command, not a skill) — gate: process retro

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

Scan rule: **gerund = how-to (craft); phase/gate noun = when/whether (harness).** Gerunds are reserved for craft so the contrast stays sharp — a few gates keep noun names that already read as checkpoints. Named exceptions on the harness side: the two spines `planning` and `building` (named for the lifecycle halves they own, per the plan/build split) and the pre-existing `threat-modeling`/`compounding`.

## The authority rule (whose file, whose citation)

When a Netdust skill and an upstream skill (superpowers, addyosmani/agent-skills) cover the same ground:

> **The Netdust skill is the authoritative `SKILL.md`.** Upstream content is woven IN as reinforcement — never added as a competing parallel file.

Superpowers is the base; addyosmani fills genuine gaps; Netdust discipline is the spine. A craft skill cites the gate that reaches for it, and the gate cites the craft it loads — wired both ways.

## The calibration rule (tell a war story once)

Every gate traces to a real incident — that's the test for a gate's existence. But an
incident has **ONE full home** (usually the owning skill's body, `references/`, or
`lessons.md`); everywhere else cites its slug, e.g. `(calibration: traverse-clause)`.
The index of all slugs + canonical homes is `skills/_shared/calibrations.md`. New skill
prose never retells an indexed incident — it cites. This keeps the hot path (SKILL.md
bodies loaded per stage) lean while losing no lesson.

## Provenance

- Harness discipline + risk-tiering + the gate sequence: Netdust harness discipline.
- Base process skills: `superpowers:*`.
- Craft fills: concepts learned from `addyosmani/agent-skills` (MIT) — folded into Netdust-voiced skills, not copied verbatim.

## Standalone harness

This plugin is fully self-contained. It holds the complete two-layer harness — the `harnessed-development` intake router, the `planning` + `building` spines it routes to, every gate they fire (testing-workflow, threat-modeling, architecture-invariants, feature-acceptance, test-effectiveness, shake-out, compounding, standards-gate), the optional spec-kit graft (`spec-kit/` + `/spec-kit-setup` → gate-bearing spec/plan/tasks override templates + `gate-check.py`; keystone: handoff is `tasks.md`, `/speckit.implement` is never run — see `docs/spec-kit-integration-adr.md`), the craft skills the gates reach for, the reviewer/specialist agents, the session + guard hooks, and its own commands (`/deploy`, `/shakeout`, `/evaluate`, `/spec-kit-setup`, …). Nothing here depends on or defers to another Netdust plugin: every skill, gate, command, and agent it references resolves WITHIN this plugin (or to an external `superpowers:*` / `superpowers-chrome` base). It supersedes the older Netdust core harness — this plugin is now the sole home for that discipline.

One documented exception: netdust-core canonically owns the two memory-maintenance commands — `/memory-audit` (named by the session-start hook's truncation warning) and `/pattern-miner` (referenced by `memory/GLOBAL.md` and the `compounding` skill as the cross-project promotion path). Both are best-effort pointers, not load-bearing — everything the harness actually gates on resolves within this plugin.
