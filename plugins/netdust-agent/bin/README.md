# netdust-agent — harness tooling

The deterministic scripts the harness gates on, plus the report-only observability tools.
Everything here runs on a bare `python3` with no third-party imports and no external
tooling: each script reads the project's own files and answers with an exit code or a table.

That property is the point. A gate whose verdict depends on an installed toolchain is a
gate that quietly stops existing on the projects that lack it — which is exactly how the
spec gate came to degrade into self-attestation before this directory was made
self-sufficient.

## What's here

```
bin/
├── README.md         ← this file
├── gate-check.py     ← THE GATE. Lints specs/<feature>/: clarify-halt, success criteria,
│                       security surfaces answered, [GATE] headings, threat-model-iff-
│                       flagged, task tiers, Test-author: modes, Unit test: contracts,
│                       review-cluster sizing, REVIEW GATE markers + provisional tiers.
│                       Exit 1 = blocked.
├── loop-check.py     ← the loop ledger: derives FINISHED from tasks.md boxes + gate-check,
│                       never from an agent's assertion
├── run-trace.py      ← in-loop event trace (single-writer append; `show --durations`)
├── run-score.py      ← deterministic 5-dimension evaluator rubric over the trace
└── run-cost.py       ← read-only transcript miner: per-dispatch / per-stage token tables
```

**There are no artifact templates.** The scripts here are the only definition of what
`spec.md` / `plan.md` / `tasks.md` must carry, and the authoring skills state that contract in
prose: `spec-authoring`'s `<artifact_contract>` for the spec, `planning` Stage 1's output
contract for the plan and task list. A template restating those requirements would be a second
implementation of one rule, free to drift from the script that actually decides — and a
skeleton whose *untouched* state passes the gate is how the security-surface checkboxes came to
be disarmed by default. The artifacts are authored, not filled in.

## Usage

```bash
# the blocking gate — run it, do not trust a transcript that says it was run
python3 plugins/netdust-agent/bin/gate-check.py specs/<feature>
python3 plugins/netdust-agent/bin/gate-check.py --json specs/<feature>

# report-only
python3 plugins/netdust-agent/bin/run-trace.py show --durations specs/<feature>
python3 plugins/netdust-agent/bin/run-score.py specs/<feature>
python3 plugins/netdust-agent/bin/run-cost.py
```

`gate-check.py` checks whatever of `spec.md` / `plan.md` / `tasks.md` exists in the
directory, so the same script serves Stage 0.5 (spec only) and Stage 1.5 (all three).
WARN findings never fail the gate; FAIL findings exit 1.

## The `[P]` vs `── REVIEW GATE ──` reconciliation

Two markers on the task list, on orthogonal axes — they compose rather than compete:

| Marker | Axis | Means |
|---|---|---|
| `[P]` | scheduling | task has no dependency on a sibling **in the same cluster** + touches different files → subagents may run it concurrently |
| `── REVIEW GATE ──` | review | a **barrier**: join all parallel work, commit, `/integration` + `/code-review`, then release the next cluster |

**Rules that make them compose** (stated in `planning` Stage 1's contract, verified by `gate-check.py`):

1. `[P]` parallelism **never crosses** a `── REVIEW GATE ──`.
2. A cluster is **≤4 tasks**; `[P]` applies only *within* a cluster.
3. An **irreversible / security-boundary** task is **never `[P]`** — solo cluster, reviewed alone (+ `/security-review`).

So: `[P]` = "these can run together *now*"; `── REVIEW GATE ──` = "stop and review *here*."
Parallelism is a within-cluster optimization; the gate is the between-cluster barrier.

## Where this sits in the harness

```
Stage 0    brainstorm        → spec.md   (superpowers:brainstorming, to spec-authoring's artifact contract)
Stage 0.5  spec-authoring    → GATES that spec.md      (gate-check.py: clarify-halt + success-criteria)
Stage 1    writing-plans     → plan.md + tasks.md      (to planning Stage 1's output contract)
Stage 1.5  spec-analysis     → consistency read + gate-presence   (gate-check.py, BLOCKING)
           ─────────────────── THE SEAM: approved tasks.md + gate-check GREEN ───────────────────
Stage 2    building          ◄── executes tasks.md task-by-task, through the gates
Stage 3    test-effectiveness → feature-acceptance → shake-out → finish
```

Stages 0–1.5 live in the `planning` skill; Stages 2–3 in `building`. The seam between them
is enforced by this directory: `building` refuses to start until `gate-check.py` exits 0.
