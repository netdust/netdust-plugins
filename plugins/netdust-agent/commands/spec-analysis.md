---
description: Stage 1.5 pre-execution gate — verify spec/plan/tasks consistency (/speckit.analyze) AND mechanically check the netdust Stage-1 gates landed (threat model, invariants, spec-premise, per-task tiers, review-cluster sizing) via spec-kit/gate-check.py, before any task is dispatched. Blocks execution on a skipped gate.
argument-hint: [path-to-specs/<feature> dir]
allowed-tools: Bash, Read, Skill(spec-analysis)
---

Invoke the `spec-analysis` skill over the feature spec directory ($ARGUMENTS, default the most recent `specs/<feature>/`).

Run both halves:
1. `/speckit.analyze` for semantic cross-artifact consistency (spec ↔ plan ↔ tasks).
2. The mechanical gate-presence check — BLOCKING:
   `python3 <netdust-agent>/spec-kit/gate-check.py <specs-dir>`

If `gate-check.py` exits non-zero, STOP: report the findings and route each to its
remediation skill (threat-modeling / architecture-invariants / testing-workflow / re-split
clusters), fix the artifacts, and re-run. Do NOT dispatch any Stage-2 task until the gate
is green. On pass, report `spec-analysis: consistency OK, gate-check PASS` as the Stage-2
green light.

Target: $ARGUMENTS
