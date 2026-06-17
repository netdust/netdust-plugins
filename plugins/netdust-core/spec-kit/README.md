# netdust × spec-kit integration

Phase A of the [spec-kit integration ADR](../docs/spec-kit-integration-adr.md). This directory
is the **graft mechanism**: it teaches [github/spec-kit](https://github.com/github/spec-kit)'s
planner to emit artifacts that already carry the netdust harness gates.

**Keystone invariant:** spec-kit owns **spec → plan → tasks**; the netdust spine owns
**execute → verify → finish**; the handoff is `tasks.md`. **`/speckit.implement` is never
run** — it bypasses Stage-2 gates (threat-model verify, test tiers, review-cluster HALT,
`subagent-stop.py`).

## What's here

```
spec-kit/
├── README.md            ← this file
├── setup.sh             ← per-project installer (spec-kit core + netdust overrides)
└── overrides/           ← BUNDLED gate-bearing template overrides
    ├── spec-template.md   (what/why; [NEEDS CLARIFICATION] HALT gate)
    ├── plan-template.md   (threat-model, invariants, spec-premise, review-cluster [GATE]s)
    └── tasks-template.md  (per-task test tiers + the [P] / REVIEW GATE reconciliation)
```

## Decision: bundled overrides, per-project spec-kit

The override templates are **bundled in netdust-core** (one gate definition, shared across
projects). spec-kit **core** is installed **per-project** by `setup.sh`, so each project can
pin/update spec-kit independently. Overrides resolve from `.specify/templates/overrides/`,
spec-kit's highest-priority template slot — so they win over spec-kit's core templates
without modifying them.

## Install

```bash
# from the project root:
/path/to/plugins/netdust-core/spec-kit/setup.sh
# then generate the constitution from your governance sources:
#   invoke the  constitution-bridge  skill   (replaces /speckit.constitution)
```

Or via the command: **`/spec-kit-setup`**.

Pin spec-kit in real projects: `SPECIFY_REF=<tag-or-sha> setup.sh`. If spec-kit's CLI flags
differ from the default, set `SPECIFY_INIT_CMD="…"`. Re-running is idempotent — it refreshes
the overrides without re-initializing spec-kit.

## The `[P]` vs `── REVIEW GATE ──` reconciliation (the Phase-A spike)

The one real design risk the ADR flagged: spec-kit's task model uses `[P]` parallel markers,
the netdust harness uses `── REVIEW GATE ──` review clusters (1f / Step 2.8). They are **not**
competing — they sit on orthogonal axes and compose:

| Marker | Axis | Means |
|---|---|---|
| `[P]` | scheduling | task has no dependency on a sibling **in the same cluster** + touches different files → subagents may run it concurrently |
| `── REVIEW GATE ──` | review | a **barrier**: join all parallel work, commit, `/integration` + `/code-review`, then release the next cluster |

**Rules that make them compose (enforced by `tasks-template.md` + verified by `spec-analysis`):**
1. `[P]` parallelism **never crosses** a `── REVIEW GATE ──`.
2. A cluster is **≤4 tasks**; `[P]` applies only *within* a cluster.
3. An **irreversible / security-boundary** task is **never `[P]`** — solo cluster, reviewed alone (+ `/security-review`).

So: `[P]` = "these can run together *now*"; `── REVIEW GATE ──` = "stop and review *here*."
Parallelism is a within-cluster optimization; the gate is the between-cluster barrier.

## Where this sits in the harness

```
Stage 0    brainstorm
Stage 0.5  spec-authoring    → spec.md     (Phase B skill — wraps /speckit.specify + /clarify)
Stage 1    writing-plans     → plan.md     (uses overrides/plan-template.md  ← THIS DIR)
Stage 1.5  spec-analysis     → consistency + gate-presence  (Phase B skill — wraps /speckit.analyze)
Stage 2    subagent-driven-development  ◄── HANDOFF: tasks.md   (NEVER /speckit.implement)
Stage 3    test-effectiveness → shake-out → finish
```

Phase A delivers the overrides + `constitution-bridge` + this installer. Phase B adds the
`spec-authoring` and `spec-analysis` skills. Phase C edits `harnessed-development` to
sequence Stages 0.5/1.5 and adds `standards-gate`.
