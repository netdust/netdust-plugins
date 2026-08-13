---
name: convergence
description: The spec-completeness gate — read the CODEBASE against specs/<feature>/ (spec + plan + tasks) and find what was promised but never built. Gaps classified missing / partial / contradicts / unrequested with file evidence, appended to tasks.md as a PROPOSED convergence phase that must pass gate-check.py and seam approval before building executes it. Use on resumed or stalled branches, finishing work, or before /shakeout — "what did the spec promise that isn't built yet", "is anything missing or half-implemented", "check the code against the spec", "what's left to build here". NOT shake-out (that drives what exists; this finds what doesn't, cheaper and earlier) and NOT Stage 1.5 (that reads artifact against artifact before execution; this reads code against intent after). Read-only on code; append-only on tasks.md; never dispatches what it proposes.
---

# Convergence — the completeness question

A green suite over 60% of a feature looks exactly like a green suite over 100%. Tests
prove the built part works; shake-out drives the built part; the invariant-auditor checks
the built part's conventions. Nothing else asks what was never built. This gate does, and
turns the answer into proposed work that re-enters the harness through the same seam all
work enters.

## Preconditions

`specs/<feature>/` with all three artifacts — `spec.md`, `plan.md`, `tasks.md`. Any
missing → HALT and name the stage that authors it (`planning`); there is nothing to
converge against. Read `ARCHITECTURE-INVARIANTS.md` and the plan's `## Threat model`
where present — they set CRITICAL severity below.

## The assessment

1. **Intent inventory.** Every `FR-n`; every `SC-n` naming buildable work (skip
   post-launch KPIs no code change satisfies); each story's acceptance scenarios
   (`US<n>/AC<m>`); the plan's architecture decisions, threat-model mitigations, and
   cited invariants.
2. **Scope.** Only what the plan and task `(files:)` lines name, plus targeted search on
   the inventory's vocabulary. Out-of-scope defects are fleet findings — park to
   `memory/STATE.md`, never assess them here.
3. **Read the present state** — no git archaeology; the question is what exists now.
   A finding only where a gap exists:

   | Gap | Meaning | Fate |
   |---|---|---|
   | `missing` | promised, entirely absent | proposed task |
   | `partial` | exists, incompletely satisfies the promise | proposed task |
   | `contradicts` | conflicts with a promise, an invariant, or a threat-model mitigation | proposed task, listed first |
   | `unrequested` | work no artifact asked for | awareness only — hand to `invariant-auditor`; never delete here |

   Each finding: source ref (`FR-n`/`SC-n`/`US/AC`/invariant), gap type, severity
   (CRITICAL = invariant/threat-model contradiction or a P1 baseline blocked; HIGH =
   core FR/AC missing; MEDIUM = partial/secondary; LOW = polish), one line of file
   evidence.
4. **Independence.** If this session authored the implementation, dispatch the read to a
   fresh-context read-only agent and take its table — the author is the worst-placed
   reader of their own completeness.

## The verdict

Report the findings table BEFORE writing anything. **Zero findings** → say
`convergence: CONVERGED`, leave `tasks.md` byte-for-byte untouched, route to `/shakeout`.

Otherwise append — never rewrite spec, plan, existing tasks, or any code — a final
section to `tasks.md`:

```
## Phase N — Convergence (PROPOSED — awaiting seam approval)
```

One task per actionable finding, `contradicts` first, task ids and phase number
continuing the file's own. **The task grammar is defined by `bin/gate-check.py` and
nowhere else** — author each line to `planning`'s task-shaping rules (tier, `Test-author:`,
`Proven by:`, test contract, `(files:)`, source FR/SC cited; clusters ≤4 with
`Integration gate:` + `── REVIEW GATE ──`; a security-boundary task solo, never `[P]`),
then run `python3 <plugin>/bin/gate-check.py specs/<feature>` and fix until exit 0. A gap
that cannot be written to the grammar is a plan question — hand it back, don't
approximate.

Then STOP. The appended phase is a proposal at the seam: the human approves or strikes
lines; `building` executes later, task by task, through its normal gates.

## Refusals

| Thought | Reality |
|---|---|
| "Suite's green, so it's complete" | Green proves the built part works. This gate asks what was never built — no test run answers that. |
| "Small gaps, I'll implement them while I'm here" | Work enters through the seam or not at all. Converge-then-dispatch bypasses approval, gate-check, and the review clusters. |
| "This unrequested code is wrong, I'll remove it" | Awareness only. Deletion is its own classed work; hand the finding to `invariant-auditor`. |
| "The spec is stale, I'll assess against what the code intends" | The spec is the intent record. A stale spec is a spec correction across the seam, never a silent rebase. |
| "One obvious task, I'll skip the grammar" | A line gate-check refuses is not a proposal. The appended phase must be dispatchable as-is. |
