---
description: Author or update a project's ARCHITECTURE-INVARIANTS.md — name the convergence points (the single places each cross-cutting property is decided) so /code-review + /shakeout can flag bypasses instead of re-auditing. Sibling to threat-modeling.
argument-hint: [audit | plan | path-to-plan]
allowed-tools: Skill(architecture-invariants)
---

Invoke the `architecture-invariants` skill.

- No argument, or `audit` → situation B: grep the codebase for each cross-cutting property's convergence point and author `ARCHITECTURE-INVARIANTS.md` at the project root.
- `plan` or a path to a plan → situation A: identify which invariants the planned feature touches and add a `## Architecture invariants touched` note to the plan (authoring the invariants doc first if it doesn't exist yet).

Context / target: $ARGUMENTS
