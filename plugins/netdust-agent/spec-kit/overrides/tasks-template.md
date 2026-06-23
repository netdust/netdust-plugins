# Tasks: [FEATURE NAME]

> **netdust override template.** Overrides spec-kit's core `tasks-template.md`. It is the
> **handoff artifact**: `harnessed-development` Stage 2 executes from this file. spec-kit's
> `/speckit.implement` is **never** run — it would bypass the Stage-2 gates (threat-model
> verify, test tiers, review-cluster HALT, `subagent-stop.py`). Execution is driven by
> `superpowers:subagent-driven-development` / `executing-plans` under the netdust spine.
>
> `spec-analysis` (Stage 1.5) verifies: every task carries a **test tier**, every phase a
> per-phase integration gate, clusters are ≤4 tasks, and irreversible steps are solo.

**Spec:** `specs/[feature-name]/spec.md` · **Plan:** `specs/[feature-name]/plan.md`

## Marker legend — `[P]` vs `── REVIEW GATE ──` (the reconciliation)

These two markers live on **orthogonal axes** and compose cleanly:

- **`[P]` = parallelizable** — a *scheduling* property. The task has no dependency on a
  sibling in the **same cluster** and touches different files, so subagents may run it
  concurrently. `[P]` says nothing about review.
- **`── REVIEW GATE ──` = review boundary** — a *serialization barrier*. It joins ALL
  parallel work in the cluster, commits it, runs `/integration` + `/code-review`, and only
  then releases the next cluster.

**Hard rules:**
1. `[P]` parallelism **never crosses** a `── REVIEW GATE ──`. The gate is a barrier: every
   `[P]` task above it must complete, commit, and pass review before any task below starts.
2. A **cluster is ≤4 tasks**. Within a cluster, independent tasks may be `[P]`; dependent
   ones are sequential.
3. An **irreversible / security-boundary task is never `[P]`** — it sits alone in its own
   cluster (1f), so it is reviewed in isolation, never bundled with a refactor.

## Per-task format

```
- [ ] T<NN> [P?] [Tier A|B] <imperative description>  (files: <paths>)
      Unit test: <what behavioral contract to verify — RED-first incl. denial path for Tier A;
                  or `no unit test: Tier B, <reason>` for glue/wrapper/presentational>
      Seam test: <only if this task WIRES a piece into the real chain — 1 un-mocked assertion
                  + 1 negative case; else omit>
```

> **Tier reminder (testing-workflow):** security/auth/scope guards, untrusted-input parsing,
> state machines, transforms, migrations = **Tier A always**, regardless of line count
> (erosion guard). Glue/wiring/pass-through wrappers/presentational/config = **Tier B**.
> A plan line's `Unit test:` prefix does NOT override the tier — classify by tier.

---

## Phase 1 — [name]

### Cluster C1  (≤4 tasks)
- [ ] T01 [P] [Tier A] [task]  (files: …)
      Unit test: [RED-first contract incl. denial path]
- [ ] T02 [P] [Tier B] [task]  (files: …)
      Unit test: no unit test: Tier B, [pass-through over typed lib]
- [ ] T03 [Tier A] [task depending on T01]  (files: …)
      Unit test: [contract]
      Seam test: [1 un-mocked-chain assertion + 1 negative case]

**Integration gate (C1):** [what to verify across C1's tasks]

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, hand back for `/code-review`; do not start C2 until clear)*

### Cluster C2 — *(irreversible: [e.g. teardown migration])*  — solo
- [ ] T04 [Tier A] [irreversible step]  (files: …)
      Unit test: [migration up/down contract]

**Integration gate (C2):** [verify]

── REVIEW GATE ──  *(STOP: commit C2, `/integration` + **`/security-review`**; irreversible cluster reviewed alone)*

---

## Phase-complete gate

After all clusters: `testing-workflow` phase-complete (integration + acceptance) → `test-effectiveness` audit → `shake-out`. Then `superpowers:finishing-a-development-branch`. (harnessed-development Stage 3.)

## Dependency notes

[Cross-task / cross-phase dependencies that constrain `[P]` scheduling — name them so the controller does not parallelize a real dependency.]
