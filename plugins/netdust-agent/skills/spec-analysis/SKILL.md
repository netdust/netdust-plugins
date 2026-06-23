---
name: spec-analysis
description: Stage 1.5 of the harness — the pre-execution gate that verifies spec.md, plan.md, and tasks.md are consistent AND that the netdust Stage-1 gates actually landed in the artifacts, before any task is dispatched. Two parts: (a) spec-kit's /speckit.analyze for semantic cross-artifact consistency, and (b) spec-kit/gate-check.py for MECHANICAL gate-presence — threat model present iff a security surface was flagged, every required [GATE] heading present, every task carries a test tier, review clusters <=4 tasks, irreversible steps solo and non-[P]. This is what turns the harness's previously skill-honored non-test gates into a machine-checked barrier. Runs AFTER planning (Stage 1) and BEFORE execution (Stage 2). Triggers when a plan+tasks are ready to execute. Requires the spec-kit graft (/spec-kit-setup).
---

<objective>
Before `harnessed-development` Stage 2 dispatches a single task, confirm two things mechanically:

1. **Consistency** — the spec, plan, and tasks describe the *same* feature: every functional requirement has tasks, no task invents scope the spec doesn't have, no plan section contradicts the spec. This is spec-kit's `/speckit.analyze`.
2. **Gate-presence** — the Stage-1 gates the harness depends on are physically present in the artifacts. This is the load-bearing addition: the harness's threat-model (1a), invariants (1b), spec-premise (1c), per-task tiers (1d), and review-cluster sizing (1f) gates were previously *skill-honored* — they fired only because a skill sequenced them, and a session that under-honored the skill skipped them silently. `spec-kit/gate-check.py` makes them a **verifiable property of the files**, failing the gate if one is missing.

The pairing is deliberate: `/speckit.analyze` needs judgment (does this task satisfy that requirement?); gate-presence is mechanical (is `## Threat model` non-N/A when a security surface was flagged?). The mechanical half is the backstop — it cannot be talked out of a finding.
</objective>

<process>

**Step 1 — `/speckit.analyze` (semantic consistency).** Invoke spec-kit's analyze command over `specs/<feature>/`. It cross-checks spec ↔ plan ↔ tasks for coverage and contradiction. Resolve any inconsistency it raises (missing requirement coverage, orphan task, plan/spec disagreement) before continuing.

**Step 2 — `gate-check.py` (mechanical gate-presence) — BLOCKING.**

```bash
python3 <netdust-agent>/spec-kit/gate-check.py specs/<feature>
```

The checker FAILS (exit 1) on any of:
- a missing required `[GATE]` heading in `plan.md` (constitution / threat model / invariants / spec-premise / review clusters);
- **a security surface checked in `spec.md` but the plan's `## Threat model` left N/A or empty** — the proactive 1a gate not satisfied (this is the case the whole graft exists to catch);
- a task line with no `[Tier A|B]` marker (1d);
- a review cluster with >4 tasks, or an irreversible/solo cluster that isn't exactly one non-`[P]` task (1f / Step 2.8).

**If the checker reports FAIL, STOP. Do not dispatch any task.** Route back:
- missing/N/A threat model on a flagged surface → author it via `netdust-agent:threat-modeling`, embed in the plan.
- missing tiers → classify each task per `testing-workflow` and add the tier line.
- oversized/irreversible cluster → re-split per 1f and add `── REVIEW GATE ──` markers.
Re-run the checker until it passes.

**Step 3 — Record the result.** Note in the transcript: `spec-analysis: consistency OK, gate-check PASS` (or the findings fixed). This is the green light for Stage 2. The threat model (if present) is now the `/code-review` convergence target for the implementing clusters.

</process>

<extremely_important>
Gate-check is a backstop, not a substitute for authoring the gates well. A plan can pass the *mechanical* presence check with a shallow threat model (the checker verifies a numbered attack→mitigation exists, not that it is complete). The mechanical check catches the *skipped* gate — the catastrophic, common failure. Depth is still on the author and `/code-review`. Do not read a green gate-check as "the threat model is sufficient"; read it as "the gate was not skipped."
</extremely_important>

<red_flags>

| Thought | Reality |
|---|---|
| "Analyze passed, I'll start executing" | Analyze is only half. Run `gate-check.py` — the mechanical gate-presence check is the part that catches a skipped threat model or an un-tiered task. |
| "The checker flagged a missing threat model but the feature feels harmless" | The checker only flags it because a Security-relevant surface was checked in the spec. Either the box was wrong (fix the spec) or the threat model is genuinely missing (author it). It is never "ignore the finding." |
| "I'll fix the gate-check findings after the first cluster ships" | That is the retrospective failure mode the harness exists to kill (1a BLOCKING). Gate-presence is a pre-dispatch barrier. Fix before task one. |
| "One cluster has 6 tasks but they're all small" | Size is the cap, not effort. >4 tasks = an un-bisectable review diff (1f). Split it. The checker is right. |

</red_flags>

<success_criteria>
1. `/speckit.analyze` reports spec ↔ plan ↔ tasks consistent (inconsistencies resolved).
2. `gate-check.py` exits 0 — every required gate present; threat model present iff a surface was flagged; all tasks tiered; clusters ≤4 and irreversible steps solo/non-[P].
3. The pass is recorded in the transcript as the Stage-2 green light.
4. If anything was missing, it was authored/fixed in the artifacts BEFORE any task dispatch — not deferred.
</success_criteria>

<integration>

| Skill / artifact | Relationship |
|---|---|
| `superpowers:writing-plans` + override `plan-template.md` | **UPSTREAM (Stage 1).** Produces the plan this gate verifies. |
| `netdust-agent:spec-authoring` | **UPSTREAM (Stage 0.5).** Its Security-relevant surfaces flags are what the threat-model cross-check keys on. |
| spec-kit `/speckit.analyze` | **WRAPPED (part a).** Semantic consistency. |
| `spec-kit/gate-check.py` | **THE MECHANICAL GATE (part b).** Exit code is the barrier. |
| `netdust-agent:threat-modeling` / `architecture-invariants` / `testing-workflow` | **REMEDIATION.** Where the checker fails, these author the missing gate. |
| `superpowers:subagent-driven-development` | **DOWNSTREAM (Stage 2).** Only runs once this gate is green. |
| `netdust-agent:harnessed-development` | **SEQUENCER.** Inserts this as Stage 1.5 (Phase C edit). |

</integration>
