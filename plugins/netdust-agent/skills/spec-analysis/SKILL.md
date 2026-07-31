---
name: spec-analysis
description: Stage 1.5 of the harness — the pre-execution gate that verifies spec.md, plan.md, and tasks.md are consistent AND that the netdust Stage-1 gates actually landed in the artifacts, before any task is dispatched. Two parts: (a) a semantic cross-artifact consistency read, and (b) bin/gate-check.py for MECHANICAL gate-presence — threat model present iff a security surface was flagged, every required [GATE] heading present, every task carries a test tier, review clusters <=4 tasks, irreversible steps solo and non-[P]. This is what turns the harness's previously skill-honored non-test gates into a machine-checked barrier. Runs AFTER planning (Stage 1) and BEFORE execution (Stage 2). Triggers when a plan+tasks are ready to execute. Part (b) is BLOCKING on every project — gate-check.py reads specs/<feature>/ directly and depends on no external tooling; part (a) is judgment and no script verifies it.
---

<objective>
Before `building` Stage 2 dispatches a single task, confirm two things mechanically:

1. **Consistency** — the spec, plan, and tasks describe the *same* feature: every functional requirement and success criterion has tasks, no task invents scope the spec doesn't have, no plan section contradicts the spec. You read the three files against each other — this is **judgment, not a script**, and it is the one part of this gate that is an assertion.
2. **Gate-presence** — the Stage-1 gates the harness depends on are physically present in the artifacts. This is the load-bearing addition: the harness's threat-model (1a), invariants (1b), spec-premise (1c), per-task tiers (1d), and review-cluster sizing (1f) gates were previously *skill-honored* — they fired only because a skill sequenced them, and a session that under-honored the skill skipped them silently. `bin/gate-check.py` makes them a **verifiable property of the files**, failing the gate if one is missing.

The pairing is deliberate: coverage needs judgment (does this task satisfy that requirement?); gate-presence is mechanical (is `## Threat model` non-N/A when a security surface was flagged?). The mechanical half is the backstop — it cannot be talked out of a finding.
</objective>

<process>

**Step 1 — semantic consistency.** Cross-check spec ↔ plan ↔ tasks for coverage and contradiction: every `FR-n` and `SC-n` traced to at least one task, every task traced back to something the spec asks for, no plan section disagreeing with the spec. Read the three files against each other. Resolve any inconsistency (missing requirement coverage, orphan task, plan/spec disagreement) before continuing.

  - **Coverage is now partly mechanical — know which part.** `gate-check.py`'s `requirement-coverage` check answers the weaker question: is each `FR-n` / `SC-n` cited **anywhere** in `tasks.md`. It cannot tell you whether the task that cites `FR-2` actually satisfies it, and it does not hunt orphan tasks in the reverse direction. So read the artifacts for *substance* and say plainly that the judgement half is yours: a green `requirement-coverage` means nothing was left untraced, not that the tasks are adequate.

**Step 2 — `gate-check.py` (mechanical gate-presence) — BLOCKING.**

```bash
python3 <netdust-agent>/bin/gate-check.py specs/<feature>
```

The checker FAILS (exit 1) on any of:
- a missing required `[GATE]` heading in `plan.md` (constitution / threat model / invariants / spec-premise / review clusters);
- **a security surface checked in `spec.md` but the plan's `## Threat model` left N/A or empty** — the proactive 1a gate not satisfied (this is the case the whole gate exists to catch);
- an unresolved `[NEEDS CLARIFICATION: …]` marker in `spec.md` (the Stage-0.5 HALT, re-asserted here);
- a `## Success criteria` line carrying no number, or a section holding only bracketed placeholder text — shake-out cannot sign off against prose;
- a `## Security-relevant surfaces` section that is missing, has zero boxes checked, or checks a real surface alongside `None of the above` — blank silently disarms the 1a gate below rather than failing loudly;
- a task line with no `[Tier A|B]` marker, no `Test-author:` mode, or no test contract (`Unit test:` or `Integration test:`) while its siblings carry one; a Tier A task waiving its test with `no unit test:` (1d);
- an `FR-n` / `SC-n` traced to no task, once the task list cites any requirement id at all (a list citing none is pre-convention and WARNs);
- a review cluster with >4 tasks, or an irreversible/solo cluster that isn't exactly one non-`[P]` task; a cluster ending with no `── REVIEW GATE ──` marker, or declaring no provisional review tier (1f / 1h / Step 2.8).

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
| "The consistency check passed, I'll start executing" | That is only half — and the half no script verifies. Run `gate-check.py`; the mechanical gate-presence check is what catches a skipped threat model or an un-tiered task. |
| "The checker flagged a missing threat model but the feature feels harmless" | The checker only flags it because a Security-relevant surface was checked in the spec. Either the box was wrong (fix the spec) or the threat model is genuinely missing (author it). It is never "ignore the finding." |
| "I'll fix the gate-check findings after the first cluster ships" | That is the retrospective failure mode the harness exists to kill (1a BLOCKING). Gate-presence is a pre-dispatch barrier. Fix before task one. |
| "One cluster has 6 tasks but they're all small" | Size is the cap, not effort. >4 tasks = an un-bisectable review diff (1f). Split it. The checker is right. |

</red_flags>

<success_criteria>
1. spec ↔ plan ↔ tasks are consistent (inconsistencies resolved), and the transcript separates what the `requirement-coverage` check proved (nothing untraced) from what only the read can judge (the tasks actually satisfy the requirements they cite).
2. `gate-check.py` exits 0 — every required gate present; no unresolved clarification marker; success criteria measurable; threat model present iff a surface was flagged; all tasks tiered; clusters ≤4 and irreversible steps solo/non-[P].
3. The pass is recorded in the transcript as the Stage-2 green light.
4. If anything was missing, it was authored/fixed in the artifacts BEFORE any task dispatch — not deferred.
</success_criteria>

<integration>

| Skill / artifact | Relationship |
|---|---|
| `superpowers:writing-plans` | **UPSTREAM (Stage 1).** Produces the plan this gate verifies, to `planning` Stage 1's output contract. |
| `netdust-agent:spec-authoring` | **UPSTREAM (Stage 0.5).** Its Security-relevant surfaces flags are what the threat-model cross-check keys on. |
| `bin/gate-check.py` | **THE MECHANICAL GATE (part b).** Exit code is the barrier. Reads the feature dir directly, no external tooling. |
| `netdust-agent:threat-modeling` / `architecture-invariants` / `testing-workflow` | **REMEDIATION.** Where the checker fails, these author the missing gate. |
| `superpowers:subagent-driven-development` | **DOWNSTREAM (Stage 2).** Only runs once this gate is green. |
| `netdust-agent:planning` | **SEQUENCER.** Fires this as Stage 1.5 — the machine check the plan/build seam rests on; `building`'s precondition re-runs `gate-check.py` at entry. |

</integration>
