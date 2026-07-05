# Tasks: [FEATURE NAME]

> **netdust override template.** Overrides spec-kit's core `tasks-template.md`. It is the
> **handoff artifact — THE SEAM**: `building` Stage 2 executes from this file, and refuses to start until `gate-check.py` is green and the plan is approved. spec-kit's
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
4. A step no agent may take alone (destructive-migration approval, credentials, a deploy
   confirmation) is marked **`[HUMAN]`** on its task line. Under an armed `/loop`, an
   unchecked `[HUMAN]` task is a *planned yield* — the loop stops there with the question
   instead of grinding past it. A `[HUMAN]` task is never `[P]`.

## Per-task format

> Every task carries a `Test-author:` mode line. The mode is set HERE, at plan time, by the
> planner — the controller reads it at dispatch; no run-time agent may change it (plan
> invariant #1).

```
- [ ] T<NN> [P?] [Tier A|B] <imperative description>  (files: <paths>)
      Test-author: <split | solo — reason>  (D1 rule: split iff Tier A on a security-boundary
                  category — auth/guards, untrusted parsing, migrations, money, 1a surface)
      Unit test: <what behavioral contract to verify — RED-first incl. denial path for Tier A;
                  or `no unit test: Tier B, <reason>` for glue/wrapper/presentational>
      Seam test: <only if this task WIRES a piece into the real chain — 1 un-mocked assertion
                  + 1 negative case; else omit>
```

> **Tier reminder (testing-workflow):** security/auth/scope guards, untrusted-input parsing,
> state machines, transforms, migrations = **Tier A always**, regardless of line count
> (erosion guard). Glue/wiring/pass-through wrappers/presentational/config = **Tier B**.
> A plan line's `Unit test:` prefix does NOT override the tier — classify by tier.

> **`Test-author:` decision rule (D1):** two forms — `Test-author: split` (an independent
> test-author is dispatched BEFORE the implementer — today's unchanged pair protocol) or
> `Test-author: solo — <one-line reason>` (a single implementer authors its own RED-first
> test; the reason is **mandatory for Tier A**). Use `split` **iff** the task is **Tier A**
> **and** falls in a security-boundary category — auth/guards/capability checks,
> untrusted-input parsing, migrations/schema, money/billing, or any 1a-trigger surface named
> in the plan's threat model. Tier A outside those categories ("A-lite": pure logic/transforms/
> thresholds) → `solo — <reason>`; Tier B → `solo — Tier B` (the reason may be the tier
> itself). The mode is the **planner's call at plan time**, **read** by the controller at
> dispatch, and **never re-decided by any run-time agent**.

---

## Phase 1 — [name]

### Cluster C1  (≤4 tasks)
- [ ] T01 [P] [Tier A] [task]  (files: …)
      Test-author: solo — [A-lite reason, e.g. pure transform/threshold logic]
      Unit test: [RED-first contract incl. denial path]
- [ ] T02 [P] [Tier B] [task]  (files: …)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, [pass-through over typed lib]
- [ ] T03 [Tier A] [task depending on T01]  (files: …)
      Test-author: split — [security-boundary category, e.g. auth/guard, untrusted parsing]
      Unit test: [contract]
      Seam test: [1 un-mocked-chain assertion + 1 negative case]

**Integration gate (C1):** [what to verify across C1's tasks]

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, hand back for `/code-review`; do not start C2 until clear)*

### Cluster C2 — *(irreversible: [e.g. teardown migration])*  — solo
- [ ] T04 [Tier A] [irreversible step]  (files: …)
      Test-author: split — migration/schema is a D1 security-boundary category
      Unit test: [migration up/down contract]

**Integration gate (C2):** [verify]

── REVIEW GATE ──  *(STOP: commit C2, `/integration` + **`/security-review`**; irreversible cluster reviewed alone)*

---

## Phase-complete gate

After all clusters: `testing-workflow` phase-complete (integration + acceptance) → `test-effectiveness` audit → `shake-out`. Then `superpowers:finishing-a-development-branch`. (building Stage 3.)

## Dependency notes

[Cross-task / cross-phase dependencies that constrain `[P]` scheduling — name them so the controller does not parallelize a real dependency.]
