---
description: Spec-completeness gate — read the codebase against specs/<feature>/ and find what was promised but never built (missing / partial / contradicts / unrequested, with file evidence); append the remaining work to tasks.md as a PROPOSED convergence phase behind gate-check.py + seam approval. Read-only on code; append-only on tasks.md; never dispatches what it proposes.
allowed_tools: ["Bash", "Read", "Grep", "Glob", "Edit", "Skill"]
---

Invoke the `convergence` skill over the feature spec directory ($ARGUMENTS, default the
most recent `specs/<feature>/`), and follow it exactly:

1. All three artifacts required (spec.md, plan.md, tasks.md); a missing one HALTs and
   routes to `planning`.
2. Build the intent inventory (`FR-n`, buildable `SC-n`, `US/AC` scenarios, plan
   decisions, threat-model mitigations, invariants); read the PRESENT-STATE code against
   it, scope bound to the plan/tasks `(files:)` surface. Findings only where a gap
   exists: missing / partial / contradicts / unrequested — `unrequested` is handed to
   `invariant-auditor`, never acted on here. If this session wrote the code, dispatch
   the read fresh-context.
3. Report the findings table BEFORE writing. Zero findings → `convergence: CONVERGED`,
   tasks.md untouched byte-for-byte.
4. Otherwise append `## Phase N — Convergence (PROPOSED — awaiting seam approval)` to
   tasks.md, every line authored to the gate-check grammar (`planning` task shaping),
   then `python3 <plugin>/bin/gate-check.py <specs-dir>` until exit 0.
5. STOP at the seam. The human approves the proposed phase; `building` executes it
   later. Never implement a finding in the same breath as the assessment.

Target: $ARGUMENTS
