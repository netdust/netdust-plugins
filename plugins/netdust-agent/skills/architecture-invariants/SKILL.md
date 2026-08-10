---
name: architecture-invariants
description: Author or update ARCHITECTURE-INVARIANTS.md — name the convergence points (the single places each cross-cutting property is decided) so reviews flag bypasses instead of re-auditing. Fires at plan-time when work touches authorization, data access, live updates, error handling, or entity modeling; author the doc BEFORE the leak, not after.
---

# Architecture invariants — name the convergence points

An invariant is a cross-cutting property with ONE place that decides it — "what may this
actor see" decided in exactly one function, every write routed through one gate. The doc
(`ARCHITECTURE-INVARIANTS.md`, repo root) names those convergence points so reviews flag
BYPASSES mechanically instead of re-auditing the property each time.

**Author or update it at plan-time** when the work touches authorization, data access,
live updates/broadcast fan-out, error handling, or entity modeling — especially tenancy
and cross-actor surfaces (`traverse-clause`). An invariant authored after the leak is an
autopsy.

**Entry shape** (one per invariant, a few lines each):

```
## INV-n — <the property, one sentence>
**Convergence point:** <file/function that decides it>
**Bypass smell:** <what a violating diff looks like>
```

Plans cite touched invariants in `## Architecture invariants touched`; the `reviewer`
checks the diff against the named convergence points, and any path that routes around
one is a finding keyed to the invariant number. Use `/architecture-invariants audit` to
author the doc for an existing codebase.
