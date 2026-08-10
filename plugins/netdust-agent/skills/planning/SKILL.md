---
name: planning
description: The PLAN overlay — superpowers does the planning; this adds the netdust gates and stops at the seam (an approved tasks.md with gate-check GREEN). Use for Class A features and Class B freshness reviews of existing plans. Triggers on "plan a feature", "write a plan for X", "spec this out". NOT for executing — that is `building`.
---

# Planning — the netdust overlay on superpowers

**Superpowers is the workhorse. This skill adds netdust gates around it and STOPS at the seam.** It never dispatches a task and never writes implementation code.

```
superpowers:brainstorming → spec  →  superpowers:writing-plans → plan + tasks
                    + the netdust gates below, checked by bin/gate-check.py
────────────────────────── THE SEAM ──────────────────────────
tasks.md exists · gate-check.py exit 0 · human approved  →  `building` takes over
```

## Stage 0 — Brainstorm (invoke `superpowers:brainstorming`)

Actually invoke it — its job is interrogating user intent, which is what prevents invented
requirements. The spec it produces lands at `specs/<feature>/spec.md`. Netdust adds ONE
rule on top: **every FR carries a `Source:` line** — a quote from the ask, or
`invented — approved <date>`. An invention nobody approved is an open question for the
human, never a default you pick (checked: `check_fr_sources`).

On WordPress work the stack sub-plugin's design skills (architecture / data / patterns)
own the *technical* shape — but they never replace the INTENT interrogation: the open
decisions (payment? stock? who sees what?) go to the human as explicit questions BEFORE
the spec is written, and their rulings are recorded in the spec (the record-shop spec's
`## Intent decisions` table is the reference shape). Skipping the questions because the
stack skills "replace brainstorming" is the loophole this sentence used to allow.

## Stage 1 — Plan (invoke `superpowers:writing-plans`)

Write the reasoning to `specs/<feature>/plan.md` and the executable list to
`specs/<feature>/tasks.md` — two files, no duplicated task list. **The grammar is defined
by `bin/gate-check.py` and nowhere else** — read its findings, not a template. What the
gates require, beyond upstream's own craft:

- **Threat model** (`## Threat model`) — required when the spec flags a security surface:
  user-controlled URLs, auth/session/token, untrusted parsing, stored credentials,
  tenancy boundaries, outbound-to-user-supplied addresses. Named assets → attacks →
  mitigations, BEFORE task breakdown; it becomes the review convergence target. A Class D
  ad-hoc security edit runs this on the diff. Proactive or it didn't count
  (calibrations: `drop-workspace-retrofit`, `class-d-gap`).
- **Architecture invariants** (`## Architecture invariants touched`) — cite the
  convergence points the work touches from `ARCHITECTURE-INVARIANTS.md`; author that doc
  first if the work touches tenancy/authorization and it doesn't exist.
- **Premise ground-truth** (`## Spec-premise ground-truth`) — every "reuse X for Y"
  premise is read against X's real source before the plan ships (`tableview-premise`).
- **Stakes** (`## Stakes`) — `high | standard | low` by blast radius of a failure, never
  by which functions appear in the diff; per-cluster refinement when clusters genuinely
  differ. Downstream verification scales against it; no run-time agent re-decides it.
- **First working version** (`## First working version`) — names the task (within the
  first 3, producing at least one non-test file) after which a human can SEE or RUN
  something, and the command/URL that shows it (`check_deliverable_first`; calibration:
  `deliverable-last` ×3).
- **Task shaping** — every task: tier (`[Tier A|B]`), `Test-author:` mode (split only for
  Tier-A security-boundary work at effective-high stakes), `Proven by:` evidence rung,
  a test contract line, `(files:)`. Clusters ≤4 tasks, each closed by an
  `Integration gate:` line and a `── REVIEW GATE ──` marker with a provisional tier.
  A cluster may declare a behaviour block (`Behaviour:` / `Observable:` /
  `RED until: <test>`) — one RED per behaviour, observable from OUTSIDE the file (a URL
  and status, a command and output, a query count — never a config/array shape); member
  tasks may then state `covered by cluster behaviour` (`behaviour-cluster` check).
- **Acceptance flows** (`## Acceptance flows`) — required when the spec flags a
  user-facing surface: one row per intended flow, edges enumerated (empty, denied,
  re-entry, concurrent, boundary, mid-flow failure). Stage 3 drives this matrix.

Order clusters by the named ask, riskiest first — when a session dies mid-plan, what
survives must be the thing that was asked for.

## Stage 1.5 — The machine check

```bash
python3 <plugin>/bin/gate-check.py specs/<feature>
```

Exit 0 or fix the artifacts and re-run. No checklist substitutes; `building` re-runs this
at entry. Then read spec/plan/tasks against each other once for what no script judges:
does the task citing FR-2 actually satisfy it; does any task invent scope.

## The seam — STOP

Present: plan path, tasks.md, the gate-check verdict, cluster tiers, `[HUMAN]` yield
points. Do not dispatch anything, do not invoke `building` — the human bridges the seam.
Class B (existing/external plan): run the gates against it as a freshness review,
reconcile code samples against current source, then the same seam.
