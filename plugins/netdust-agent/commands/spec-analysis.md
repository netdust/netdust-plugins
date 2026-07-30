---
description: Stage 1.5 pre-execution gate — cross-check spec/plan/tasks consistency AND mechanically check the netdust Stage-1 gates landed (clarify-halt, measurable success criteria, threat model, invariants, spec-premise, per-task tiers, review-cluster sizing) via bin/gate-check.py, before any task is dispatched. Blocks execution on a skipped gate.
argument-hint: [path-to-specs/<feature> dir]
allowed-tools: Bash, Read, Skill(spec-analysis)
---

Invoke the `spec-analysis` skill over the feature spec directory ($ARGUMENTS, default the most recent `specs/<feature>/`).

Run both halves:
1. Semantic cross-artifact consistency: read spec ↔ plan ↔ tasks against each other —
   every `FR-n` and `SC-n` traced to a task, every task traced back to the spec, no
   contradiction. Judgment, not a script; say so when reporting.
2. The mechanical gate-presence check — BLOCKING:
   `python3 <netdust-agent>/bin/gate-check.py <specs-dir>`

If `gate-check.py` exits non-zero, STOP: report the findings and route each to its
remediation skill (threat-modeling / architecture-invariants / testing-workflow / re-split
clusters), fix the artifacts, and re-run. Do NOT dispatch any Stage-2 task until the gate
is green. On pass, report `spec-analysis: consistency OK, gate-check PASS` as the Stage-2
green light.

Target: $ARGUMENTS
