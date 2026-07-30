---
name: planning
description: The PLAN spine of the Netdust harness — brainstorm → spec → plan (with every plan-time gate baked in) → spec-analysis, ending at THE SEAM, an approved `tasks.md` with `gate-check.py` GREEN. It STOPS there. It never dispatches a task, never writes implementation code — the `building` skill refuses to start without the artifact this skill produces, which is what makes the boundary enforced rather than honored. Normally entered via `harnessed-development` intake (Class A — full spine; Class B — freshness review of an existing plan). Also triggers directly on "plan a feature", "write a plan for X", "spec this out", "design this feature", "brainstorm X", "turn this idea into a plan", "review this plan before we execute it". NOT for executing anything — "execute the plan" / "work the plan" belong to `building`; a tweak or bug-fix that warrants no plan is Class E/C and never comes through here. Stack-agnostic; defers to the loaded stack sub-plugin for stack-specific design and plan-requirements skills.
---

<objective>
One job: turn intent into an **approved, gate-checked task list — and STOP**.

The output contract (the seam):

```
tasks.md exists · gate-check.py GREEN · human has approved
────────────────────── THE SEAM ──────────────────────
everything below the line belongs to `building`, which
REFUSES to start Class A/B work without this artifact
```

Within this spine, every plan-time gate the work warrants fires because this skill sequences it — threat model, invariants, premise ground-truth, acceptance flows, task shaping — and Stage 1.5 machine-checks the result. The win is not "always run everything"; it is "never silently skip a gate the work called for," proven at the boundary instead of remembered in prose.

This skill is a **sequencer**: at each stage it loads the right upstream skill (`superpowers:brainstorming`, `superpowers:writing-plans`, the local gate skills) and adds the netdust-specific gate around it. Do NOT duplicate upstream content. It is stack-agnostic by design — see `<stack_overrides>`.
</objective>

<how_the_gates_are_actually_enforced>
Be honest about enforcement strength:

- **The plan-time gates (1a threat-modeling, 1b architecture-invariants, 1g feature-acceptance) are SEQUENCER-ENFORCED at authoring time.** No hook blocks a plan lacking its `## Threat model` while you write it. They fire because this skill sequences them — honor-system at the point of authoring.
- **Stage 1.5 is the MACHINE CHECK.** `spec-kit/gate-check.py` turns the skill-honored gates (1a/1b/1d/1f) into artifact properties that cannot be talked out of a finding — and `building`'s precondition re-runs it, so a skipped gate cannot cross the seam. That is the layered defense: sequencer fires it, the checker proves it, the seam enforces it.

The practical upshot: treat the authoring-time gates with full seriousness precisely BECAUSE nothing hard-stops you until Stage 1.5 — a gate skipped at authoring surfaces one stage later, where it is more expensive.
</how_the_gates_are_actually_enforced>

<extremely_important>
This skill is a sequencer. If you find yourself running Bash, Read, or Grep to "understand the task" BEFORE invoking the stage's upstream skill, **stop** — that reasoning belongs to the upstream skill or to the planner persona. The one allowed read is Stage 1c premise ground-truthing, which is explicitly a post-upstream-load obligation.

And the hard boundary: **this skill never executes.** No task dispatch, no implementation edit, no "quick start on task 1 while the human reviews." Producing the seam artifact and presenting it IS the completion state.
</extremely_important>

<stack_overrides>
**Standing rule — this skill names only generic skills; a loaded stack sub-plugin replaces them.** When a stack sub-plugin (`netdust-wp`, `netdust-statamic`, any future `netdust-<stack>`) offers a sharper skill for a stage, use it in place of the generic — same stage, same gate, sharper tool:

- **Brainstorm / plan / domain conventions** — if the sub-plugin provides a domain skill for the artifact you're designing (framework-architecture, data-layer, patterns), invoke it alongside or instead of the generic.
- **Plan requirements** — if the sub-plugin provides a *plan-requirements* skill (one that injects mandatory stack-specific requirement sections into the plan, the way `threat-modeling` injects `## Threat model`), fire it at Stage 1 alongside 1a/1b so its sections are baked in **before task breakdown**. (On WordPress that skill injects WP-security four-pillar + ntdst-core layering requirements; this skill never names it — the override rule picks it up.)

Do not hardcode any stack's skill names in this file.
</stack_overrides>

<craft_routing>
GATES decide *whether/when*; CRAFT skills are the *how-to* loaded to do that step's work well. Craft layers on its superpowers base, never replaces it. You need both at each step.

| Stage / step | Gate (when/whether) | Craft skill to load (how-to) |
|---|---|---|
| Stage 0 — brainstorm | `superpowers:brainstorming` | `refining-ideas` (sharpen a vague idea: divergent→convergent) |
| Stage 1 — write the plan | `superpowers:writing-plans` | `sourcing-from-docs` (when a plan premise rests on external lib/API behavior — verify via context7 before asserting; pairs with 1c) |
| Stage 1 — API / boundary design | `architecture-invariants` (1b) | `designing-apis` (contract-first; name the convergence points the invariant doc will check) |
| Stage 1c — premise ground-truth | 1c | `sourcing-from-docs` (external dep) + `engineering-context` (sibling code from the 3-layer memory) |
| The seam — a big decision about to be committed | — | `doubting-decisions` (adversarial fresh-context attack on the plan's key decision, while a correction is still a plan edit, not a re-build) |

If a stack sub-plugin offers a sharper craft skill for a stage, prefer it — same rule as `<stack_overrides>`.
</craft_routing>

<stage_persona>
The `planner` agent persona owns this whole spine (Stage 0 → the seam): it classifies, fires the gates by trigger, ground-truths premises, shapes the task list, and never hand-writes a gate section — it loads the skill that produces it. Dispatch `planner`, or run the stages inline yourself; the gates fire the same either way.

**Presence decides WHERE, not WHETHER.** When the human is present and actively steering — an interactive session, requirements still moving — plan INLINE in the main conversation: a pivot must cost a sentence, not a background-agent round-trip. Dispatch the background `planner` (or a plan-correction agent) only when the human has stepped away, or the output feeds an unattended run (an armed `/loop`, a tmux loop, a scheduled run). The persona is not retired by this — it remains the background mode, and is exactly right for those unattended cases; presence just decides which of the two you reach for.
</stage_persona>

<process>

## Stage 0 — Brainstorm (when intent is not yet concrete)

If the feature's intent, scope, or shape is not already pinned down, invoke `superpowers:brainstorming` **before** any plan exists (prefer the stack sub-plugin's brainstorming/domain skill when loaded — see `<stack_overrides>`). Skip only when the work is a well-specified change with no open design questions.

Brainstorming is what **authors the spec**, and it writes it to `specs/<feature>/spec.md` from `templates/spec-template.md` — the location preference in `memory/GLOBAL.md` overrides its `docs/superpowers/specs/` default. Content is upstream's job; Stage 0.5 only verifies. If the spec lands anywhere else, the whole spec gate silently no-ops, so check the path before moving on.

## Stage 0.5 — Gate the spec (always)

Invoke `netdust-agent:spec-authoring` **before** writing the plan. Stage 0 wrote `specs/<feature>/spec.md` from `templates/spec-template.md` (what/why, prioritized P1/P2/P3 user stories, acceptance criteria, measurable `SC-n` success criteria — no tech stack); Stage 0.5 is the gate over it. It HALTS on any unresolved `[NEEDS CLARIFICATION]` and on any success criterion carrying no number, both enforced mechanically by `spec-kit/gate-check.py`. The Stage-1 plan is then written against a clarified spec, the spec's Security-relevant-surfaces flags pre-arm the 1a threat-model gate, and its story boundaries become the review clusters in 1d.

**This stage is unconditional — it does not depend on the spec-kit graft.** `gate-check.py` reads whatever of `spec.md` / `plan.md` / `tasks.md` sits in the feature dir and imports nothing from spec-kit. The one prerequisite is that the spec is at `specs/<feature>/spec.md`, which is a standing preference in `memory/GLOBAL.md` rather than a per-project choice — a spec at brainstorming's upstream default path is a spec no gate ever reads. Skip this stage only in Class B freshness-review mode (where the spec predates you).

## Stage 1 — Write the plan, with the plan-time gates baked in

Invoke `superpowers:writing-plans`. Follow its checklist. **The plan is written against the Stage-0.5 `spec.md`** — and if the spec-kit graft is installed, from the override `plan-template.md`, whose gate sections are pre-structured as `[GATE]` headings. Without the graft you author those same headings yourself; `gate-check.py` requires them either way, so the template is a convenience and never the thing that makes the gate exist. Then layer the netdust gates below **before task breakdown is finalized** — they are not optional add-ons, they change what tasks the plan contains.

**Stack plan-requirements (override layer).** If a stack sub-plugin provides a plan-requirements skill (see `<stack_overrides>`), invoke it HERE, alongside 1a/1b — it injects the stack's mandatory requirement sections into the plan before task breakdown, so those become per-task acceptance criteria and the `/code-review` convergence target.

**1a. Threat-modeling gate.** Invoke `threat-modeling` and embed its `## Threat model` section inline in the plan IF the feature touches any of: user-controlled URLs (webhooks, BYOK provider URLs, OAuth redirects, embed/CMS endpoints), auth/session/token surfaces, untrusted parsing (frontmatter from external sources, AI tool-call args, webhook payloads, file uploads), BYOK credentials, multi-tenancy / workspace boundaries, or any path where the server makes outbound requests to user-supplied addresses. Named assets → named attacks → named mitigations → explicit deferrals, BEFORE task breakdown. The threat model then becomes the `/code-review` convergence target (reviews verify against named mitigations instead of free-form hunting — converging in one round instead of probabilistically over many).

  - This gate ALSO fires for a Class D ad-hoc security edit — there is no plan to embed it in; run the threat model on the *diff* before any implementation, then hand to `building`. (2026-06-03: a `validatePublicUrl` SSRF-guard edit shipped without this because the CLAUDE.md trigger was plan-only. The guard held by luck, not by a gate. Never again. Slug: `class-d-gap`.)

  - **BLOCKING — proactive, not retrospective.** The `## Threat model` must exist **BEFORE the first task is ever dispatched**, not be back-filled once `/code-review` surfaces findings. A threat model written *for the fix* is documentation of pain already taken, not prevention — and it does NOT earn the one-round convergence this gate exists to buy. (Calibration: phases whose threat model was written proactively converged `/code-review` in a single round, 3–4 findings each; the one phase whose threat model was retrofitted after review — `drop-workspace-tenancy`, even though the surface plainly triggered the gate — took two rounds and 11 findings, including cross-tenant leaks the catalog *already named*. The catalog wasn't the hole; **applying it late was**. Slug: `drop-workspace-retrofit`.)

**1b. Architecture-invariants gate.** If the plan touches a convergence point named in the project's `ARCHITECTURE-INVARIANTS.md` (authorization, data access, live updates, error handling, entity modeling), invoke `architecture-invariants` and cite the touched invariants in the plan.

  - **If the doc doesn't exist yet, author it via `/architecture-invariants audit` NOW, at plan-time — not after `/code-review` finds the bypass.** An invariant authored after the leak is an autopsy.
  - **Front-load it for tenancy / multi-actor surfaces.** When the work touches multi-tenancy, scope-narrowing checks, cross-actor visibility, or a live-update/broadcast path fanning data out to differently-scoped consumers, author or refresh the doc at plan-time and name the *one* place "what may this actor see" is decided — in the stack's own idiom. This is the structural twin of threat-modeling's traverse-clause-bypass attack class; naming the convergence point in the plan turns the next bypass into a one-line review finding instead of a multi-round leak hunt. *(Calibration: `traverse-clause` — index: `skills/_shared/calibrations.md`.)*

**1c. Spec-level premise ground-truth (the cheapest catch there is).** Before the plan ships, if its core approach is "reuse existing infrastructure X (a component, endpoint, table, helper) for new data-type/use Y," READ X's source and confirm X actually accepts Y. This catches a *wrong architectural premise* two documents earlier than task-dispatch, where it is far cheaper. (2026-05-30, Sub-phase E: "the runs table renders through the existing TableView" survived spec + plan-expansion + handoff and was false — one grep falsified it. Caught only at dispatch, forcing a mid-execution re-plan. Slug: `tableview-premise`.)

**1e. Sibling-site audit blocks.** For any task touching a cross-cutting concern (a TS union/enum/discriminator, a SQL predicate on a JSON-extract→column field, an event scope, a cross-route guard, a closed-enum literal), add a `## Sibling-site audit` block enumerating the surface to check. (Sub-phase C.1: every cross-cutting fix had 1–2 sibling sites needing the same change, missed by the primary fix. Slug: `sibling-sites`.)

**1g. Acceptance-flow matrix (does the FEATURE behave, not just the code).** Invoke `feature-acceptance` (Situation A) and embed an `## Acceptance flows` matrix in the plan IF the work adds or changes a **user-facing feature** (a view, a form, a wizard, an interactive flow, a CRUD surface, an endpoint a client/agent will drive). One row per intended-use flow; each row's **Edges** column MANDATORY — enumerate the six edge classes (empty/zero state, denied actor, wrong-order/re-entry, concurrent/double, boundary value, mid-flow failure) or name why one is excluded. This is the behavioral twin of the threat model: written before code, it becomes the contract `building` Stage 3 / `/shakeout` *drives* instead of shake-out re-discovering broken flows free-form. (Calibration: the empty-state / guard-gap / double-submit / no-rollback / jsdom-race escapes all shipped past a green suite — each an intended-use edge nobody drove; slugs in `skills/_shared/calibrations.md`.)

**1d. Task-shaping gate (one gate, three facets — absorbs the former 1f and 1h).** The content gates above decide what the plan must contain; this gate shapes the task list those contents break into. The labels 1d/1f/1h survive in the templates and `gate-check.py`; treat them here as one gate:

  - **(1d) Test expectations.** Per `testing-workflow`: every task gets its tier marker — a Tier-A task carries a "Unit test: [what the RED-first test must assert]" line (including the denial path for a guard); a Tier-B task carries `no unit test: Tier B, <reason>`. Every phase gets an "Integration gate: [what to verify across tasks]" line. A plan without these is not ready to execute.
  - **(1d) Test-author mode.** Every task also carries a `Test-author:` mode line, set HERE at plan time by the decision rule (D1): `split` **iff** the task is **Tier A** **and** falls in a security-boundary category — auth/guards/capability checks, untrusted-input parsing, migrations/schema, money/billing, or any 1a-trigger surface named in the plan's threat model. Tier A outside those categories ("A-lite": pure logic/transforms/thresholds) → `solo — <one-line reason>` (the reason is mandatory for Tier A); Tier B → `solo — Tier B` (the reason may be the tier itself). **Hard rule: a Tier-A task on a security-boundary category is ALWAYS `split`** — you may not talk a 1a-surface task down to solo to save a dispatch. The mode is decided HERE, read by the controller at dispatch, and never re-decided by any run-time agent (the no-self-downgrade invariant) — the field is machine-checked by `gate-check.py`'s `test-author-mode` check at Stage 1.5.
  - **(1f) Review-group sizing.** A single review group is **~3–4 tasks max**. When a phase exceeds that, OR contains an irreversible / security-boundary step (a schema drop, a teardown migration, an auth/token rewrite), split it into sub-group **review clusters**, each declared with an explicit `── REVIEW GATE ──` STOP marker in the plan — the executing agent HALTs there for `/integration` + `/code-review` on that cluster's diff; an irreversible-migration cluster reviews alone and also gets `/security-review`. Without this, execution runs a long phase flat and the first review is an un-bisectable mega-diff. (2026-06-05, Folio drop-workspace-tenancy Phase 4: a 7-task `__system`-teardown phase behind one end-of-phase gate ran straight through, merged two tasks into an uncommitted blob, and would have reviewed the irreversible `memberships`/`__system` drops in the same pass as refactors. Slug: `teardown-cluster`; the `traverse-clause` disaster — 7.7× review-to-implementation time — was the same shape.)
  - **(1h) Provisional review tier per cluster.** Beside each `── REVIEW GATE ──` marker, assign a provisional tier from the **same surface triggers the 1a gate already names** (never a second list): **FULL** — the diff touches any 1a trigger surface, a named architecture invariant, or the data layer/migrations; **STANDARD** — multi-file behavior changes outside those surfaces; **LIGHT** — doc/copy/config/skill-body only. `building` restates the tier at each gate (and may override with justification), and escalation there is one-way — a finding on a 1a surface promotes the unit to FULL. Tier governs finder/persona fan-out only; it never cancels the `/security-review` obligation a plan-time threat model created.
  - **Loop-auditability (stay loop-agnostic).** The plan is execution-mode-agnostic — you never know whether `building` will run it under an armed `/loop`. Two content lines make it loop-safe either way: mark any step no agent may take alone (destructive-migration approval, credentials, deploy confirmation) with `[HUMAN]` on its task line (a planned yield point, never `[P]`), and write a `Loop budget: ~N iterations` line in the plan's technical context (task count + clusters + slack).

**Class B — freshness review of an existing plan.** When the plan was written by someone else (or an earlier session), run Stage 1 as a **critical freshness review** instead of authoring: read the plan, run 1a–1c + 1g against it, confirm the task-shaping gate — if a phase is >~4 tasks or contains an irreversible/security step with no `── REVIEW GATE ──` marker, add the markers; add a provisional tier where missing — reconcile its code samples against current source, and raise concerns with your human partner before the seam. A plan is a snapshot of conventions at authoring time; the codebase has moved since.

## Stage 1.5 — Spec-analysis gate (the machine check)

Invoke `netdust-agent:spec-analysis`. Two parts:

1. **Semantic consistency — the one item here that is NOT mechanical.** Cross-check spec ↔ plan ↔ tasks: every `FR-n` and `SC-n` covered by a task, no orphan task tracing to nothing in the spec, no contradiction between the three. With the spec-kit graft, `/speckit.analyze` does this; without it, you read the three files against each other yourself. Be honest about the difference — **no script checks requirement coverage today**, so this part is sequencer-enforced, and it is the one place in Stage 1.5 where saying "done" is an assertion rather than an artifact property. (Open follow-up: a mechanical `FR-n`/`SC-n` → task coverage check in `gate-check.py` would close it.)
2. **Mechanical gate-presence — BLOCKING.** Run `spec-kit/gate-check.py specs/<feature>`. It FAILS (and you do NOT proceed) on: a missing `[GATE]` heading; a security surface flagged in `spec.md` but the plan's `## Threat model` left N/A; an unresolved `[NEEDS CLARIFICATION]`; an `SC-n` line carrying no number; a task with no `[Tier A|B]` marker or no `Test-author:` mode; a review cluster >4 tasks or an irreversible step that isn't a solo non-`[P]` task.

On FAIL, route each finding to its remediation (`threat-modeling` / `architecture-invariants` / `testing-workflow` / re-split clusters), fix the artifacts, re-run until green. **There is no graft-less fallback and no manual-checklist substitute:** `gate-check.py` is the arbiter on every project, and `building`'s precondition re-runs it. A checklist an agent says it applied is precisely the self-attestation this gate replaced.

## The seam — STOP here

When Stage 1.5 is green, present to your human partner, in one compact block: the plan path, `tasks.md`, the gate-check verdict line, each cluster's provisional tier, the `Loop budget`, and any `[HUMAN]` yield points. If the feature has a run-log seam artifact, emit `python3 <plugin>/spec-kit/run-trace.py append specs/<feature> gate-check-green` as you present it. Then **stop**.

- **Do not dispatch a task.** Not even "task 1 while you look this over."
- **Do not invoke `building`.** The go/no-go on an approved plan is the human's; `building` runs on their word (and re-verifies the seam itself — the artifact, not your assertion, is what admits it).
- Approval may come back as changes — fold them in, re-run `gate-check.py`, re-present.

This stop is the reason the split exists: the plan/build boundary is a **review checkpoint**, and a checkpoint an agent can roll through is not a checkpoint.

**The ladder before UNATTENDED execution is mandatory regardless of planning mode.** Whether the plan above was written inline (human present) or by a dispatched `planner` (human away), the same review ladder gates any run that will proceed without a human watching: the Stage 1.5 `gate-check.py` GREEN, human approval at the seam, and `doubting-decisions` run on the plan's key decision. Presence changes WHERE the planning happened; it never changes WHICH gates fire before the run is left to execute unattended. (This ladder is a sequencer-enforced obligation of the pre-unattended path — restated here, not newly added; no new machine gate or HALT is introduced.)

</process>

<red_flags>

These thoughts mean you are about to skip a plan-time gate. Stop.

| Thought | Reality |
|---|---|
| "This feature doesn't really touch security, I'll skip the threat-model check" | Run the 1a trigger list literally. "BYOK + encrypted" is a property statement, not a threat model. The trigger list decides, not your gut. |
| "I'll write the threat model / invariant later if review flags something" | That is the retrospective failure mode (1a BLOCKING). A threat model written for the fix documents pain already taken (calibration: `drop-workspace-retrofit`). Write the section BEFORE the seam. |
| "We'll reuse the existing X for this, obviously it fits" | Read X's source NOW (1c). The TableView-for-runs premise survived three documents and was false (`tableview-premise`). |
| "Let me grep the codebase to understand the task before invoking the upstream skill" | The upstream skill IS how you understand the task. Invoke it first. (1c ground-truthing is the one allowed post-load read.) |
| "The plan is done and green — I'll just get task 1 moving while the human reviews" | The seam is a hard STOP. An agent that rolls through the checkpoint has deleted the checkpoint. Present, stop, wait. |
| "The semantic cross-check passed, the plan is ready" | That is half of Stage 1.5, and the half no script verifies. Run `gate-check.py` — it is what catches a skipped threat model, an un-tiered task, or an oversized cluster. Green checker + human approval = the seam. |
| "No spec-kit here, so I'll apply the gates as a checklist and note that I did" | That degradation is deleted. `gate-check.py` needs no graft — it reads `specs/<feature>/` directly. A stated checklist is the self-attestation the gate exists to replace. |
| "Brainstorming already wrote the design doc, so Stage 0.5 has nothing to do" | Stage 0.5 never authored the spec; it verifies it. Check the path first (`specs/<feature>/spec.md`) — at the upstream default path every check silently no-ops. |
| "One 7-task phase with a review at the end keeps the plan simple" | That is the un-bisectable mega-diff (`teardown-cluster`). Clusters of ~3–4; irreversible steps review alone. |
| "The user is mid-pivot and I'm dispatching a background planner" | A background plan finished during live steering has a shelf life of minutes — two sub-10-minute pivots each invalidated a just-finished background plan (calibration: `background-planner-pivots`). Plan inline while requirements are still moving; dispatch background only once the human has stepped away or the run is unattended. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. For any feature touching the 1a trigger surface, a `## Threat model` exists in the plan BEFORE the seam (or on the diff, for a Class D hand-through).
2. For any feature touching a named convergence point, the relevant invariants were cited (1b).
3. Every "reuse X for Y" premise was ground-truthed against X's source before the plan shipped (1c).
4. User-facing work carries an `## Acceptance flows` matrix with mandatory per-flow edges (1g).
5. The task list is shaped (1d): every task tiered, every phase gated, clusters ≤~4 tasks with `── REVIEW GATE ──` markers + provisional tiers, `[HUMAN]` steps marked, a `Loop budget` line present.
6. `gate-check.py` is GREEN — on every project, graft or no graft. No manual-checklist substitute.
7. The spine STOPPED at the seam — artifacts presented, human approval awaited, zero tasks dispatched, `building` not invoked.

If a gate that should have fired did not, this skill failed at its specific job — even if the plan reads well.

</success_criteria>

<integration>

| Skill | Relationship |
|---|---|
| `harnessed-development` | **ROUTER / UPSTREAM.** Classifies the work (A–F) and enters this spine for Class A (full) and Class B (freshness review). Class D borrows exactly one gate from here: 1a on the diff. Class F never enters — brainstorm-only, no plan artifact. |
| `building` | **DOWNSTREAM — the other spine.** Consumes the seam artifact. Its precondition re-runs `gate-check.py`; it refuses Class A/B work without the approved `tasks.md`. Never invoked by this skill — the human bridges the seam. |
| `superpowers:brainstorming` | **STAGE 0.** Front-loaded when intent is unclear; stack sub-plugin brainstorming/domain skills replace it when loaded. |
| `spec-authoring` | **STAGE 0.5 — unconditional.** Gates the spec brainstorming authored at `specs/<feature>/spec.md`; HALTs on unresolved `[NEEDS CLARIFICATION]` and on unmeasurable success criteria. Owns the hand-back-ambiguity rule. |
| `superpowers:writing-plans` | **STAGE 1.** The plan this spine wraps the gates around; with the graft, written from the override `plan-template.md`. |
| `threat-modeling` | **GATE 1a.** Fired by trigger list at plan-time, or on an ad-hoc security diff (Class D). Becomes the `/code-review` convergence target. |
| `architecture-invariants` | **GATE 1b.** Fired when a convergence point is touched; authored at plan-time if the doc is missing. |
| `feature-acceptance` | **GATE 1g (author).** Plan-time acceptance-flows matrix; `building` Stage 3 drives it. |
| `testing-workflow` | **GATE 1d source of truth.** Owns the tier rule the task-shaping gate applies per task; do not re-encode it here. |
| `spec-analysis` | **STAGE 1.5.** `/speckit.analyze` + mechanical `gate-check.py` — the machine check the seam rests on. |
| stack sub-plugins | **OVERRIDE LAYER.** Domain/design/plan-requirements skills replace the generics per `<stack_overrides>`. |
| `doubting-decisions` | **SEAM-TIME CRAFT.** Adversarial fresh-context attack on the plan's key decision before it's committed to execution. |
| `planner` agent | **PERSONA.** Owns this spine when dispatched; loads the gates, never hand-writes their sections. |

**Calibration data behind these gates** (full stories live at the gate text above or the named homes; index: `skills/_shared/calibrations.md`): `drop-workspace-retrofit`, `class-d-gap` (1a) · `tokens-mint-bypass`, `traverse-clause` (1b) · `tableview-premise` (1c) · `sibling-sites` (1e) · `teardown-cluster` (1f facet).

</integration>
