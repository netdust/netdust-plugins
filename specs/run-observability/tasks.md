# Tasks: Run observability (in-loop trace + evaluator rubric)

> **netdust override template.** Overrides spec-kit's core `tasks-template.md`. It is the
> **handoff artifact — THE SEAM**: `building` Stage 2 executes from this file, and refuses to start until `gate-check.py` is green and the plan is approved. spec-kit's
> `/speckit.implement` is **never** run — it would bypass the Stage-2 gates (threat-model
> verify, test tiers, review-cluster HALT, `subagent-stop.py`). Execution is driven by
> `superpowers:subagent-driven-development` / `executing-plans` under the netdust spine.
>
> `spec-analysis` (Stage 1.5) verifies: every task carries a **test tier**, every phase a
> per-phase integration gate, clusters are ≤4 tasks, and irreversible steps are solo.

**Spec:** `specs/run-observability/spec.md` · **Plan:** `specs/run-observability/plan.md`

## Marker legend — `[P]` vs `── REVIEW GATE ──` (the reconciliation)

These two markers live on **orthogonal axes** and compose cleanly:

- **`[P]` = parallelizable** — a *scheduling* property. The task has no dependency on a
  sibling in the **same cluster** and touches different files, so subagents may run it
  concurrently. `[P]` says nothing about review.
- **`── REVIEW GATE ──` = review boundary** — a *serialization barrier*. It joins ALL
  parallel work in the cluster, commits it, runs `/integration` + `/code-review`, and only
  then releases the next cluster.

**Hard rules:**
1. `[P]` parallelism **never crosses** a `── REVIEW GATE ──`.
2. A **cluster is ≤4 tasks**.
3. An **irreversible / security-boundary task is never `[P]`** — solo cluster. (None in this feature.)
4. A step no agent may take alone is marked **`[HUMAN]`** — a planned yield under an armed `/loop`. (None in this feature — every step is reversible file work on a feature branch.)

## Per-task format

```
- [ ] T<NN> [P?] [Tier A|B] <imperative description>  (files: <paths>)
      Unit test: <what behavioral contract to verify — RED-first incl. denial path for Tier A;
                  or `no unit test: Tier B, <reason>` for glue/wrapper/presentational>
      Seam test: <only if this task WIRES a piece into the real chain — 1 un-mocked assertion
                  + 1 negative case; else omit>
```

> **Tier reminder (testing-workflow):** parsing, transforms, threshold logic = **Tier A always**.
> Prose/doc edits and description bumps = **Tier B**.

---

## Phase 1 — the trace primitive

### Cluster C1  (3 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] Build `spec-kit/run-trace.py` — `append <feature-dir> <event> [k=v ...]` writes one timestamped JSON line to `<feature-dir>/run-log.jsonl`; `show <feature-dir>` renders the log; this is the single-writer convergence point (plan 1b note)  (files: plugins/netdust-agent/spec-kit/run-trace.py, plugins/netdust-agent/tests/test_run_trace.py)
      Unit test: append → exactly one well-formed line with event+data+ts; second append → two lines, order preserved; denial: nonexistent feature dir → exit nonzero + one-line reason, no file created; malformed k=v → exit nonzero; show on empty/missing log → clean "no trace recorded" exit 0
- [ ] T02 [Tier A] Emit loop decisions from `hooks/loop-gate.py` — one `run-trace` event per decision site (bypass, disarm-finished, disarm-budget, disarm-dry, yield-blocked, block/continue) carrying iteration/done/total/reason; MUST be fail-open: any trace failure leaves the gate's decision and output byte-identical  (files: plugins/netdust-agent/hooks/loop-gate.py, plugins/netdust-agent/tests/test_loop_gate.py)
      Unit test: each decision site leaves its event in the fixture feature's run-log.jsonl (extend the existing block/disarm/yield cases); denial: unwritable log path → gate decision and stdout unchanged, no exception escapes
      Seam test: run the real hook via the existing test harness (un-mocked subprocess) on an armed fixture → block decision AND trace line both present; negative: marker absent → no trace line
- [ ] T03 [Tier B] Name the controller emission points in the spines' prose — `building` Stage 2 (stage-enter, review-gate crossing with stated tier, via `run-trace.py`), `planning` seam presentation (gate-check-green event), `/loop` arm/disarm  (files: plugins/netdust-agent/skills/building/SKILL.md, plugins/netdust-agent/skills/planning/SKILL.md, plugins/netdust-agent/commands/loop.md)
      Unit test: no unit test: Tier B, prose-only edits naming existing script invocations

**Integration gate (C1):** full suite green (`tests/run.sh`); simulated armed-loop block leaves a well-formed decision event; broken log path changes no gate decision.

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, `/code-review` — tier STANDARD; do not start C2 until clear)*

---

## Phase 2 — the rubric + surfacing

### Cluster C2  (4 tasks · provisional tier: STANDARD)
- [ ] T04 [Tier A] Build `spec-kit/run-score.py` — compile `<feature-dir>/run-log.jsonl` + `tasks.md` + `gate-check.py --json` into `<feature-dir>/run-rubric.md`, grading the five dimensions exactly per the plan's thresholds table (seam integrity, cluster discipline, loop efficiency, yield discipline, completion)  (files: plugins/netdust-agent/spec-kit/run-score.py, plugins/netdust-agent/tests/test_run_score.py)
      Unit test: one fixture per grade boundary per dimension (A/B/C/D and n/a where defined) → emitted grades match the table; planned vs unplanned yields counted separately, never conflated; denial: missing run-log → clean "no trace recorded" exit, NO rubric written (never fabricates grades)
- [ ] T05 [P] [Tier B] Surface the rubric in `/shakeout` — after Step 4's consolidated triage: if `specs/<feature>/run-log.jsonl` exists, run `run-score.py` and include the rubric table in the report; else one line "no run trace recorded". Report-only, never blocks  (files: plugins/netdust-agent/commands/shakeout.md)
      Unit test: no unit test: Tier B, command-prose edit routing to the T04-tested script
- [ ] T06 [P] [Tier B] Leave `/evaluate` the pointer — one paragraph: when a run-log exists, read it before git archaeology (Step 2) and cite the rubric in the retro; no behavior rewrite  (files: plugins/netdust-agent/commands/evaluate.md)
      Unit test: no unit test: Tier B, doc-only pointer
- [ ] T07 [Tier B] Describe + version — CLAUDE.md harness-layer list + README + plugin.json description gain the run-observability line; bump netdust-agent to 0.7.0 (plugin.json + marketplace.json — 0.6.0 was taken by the test/dev split merged 2026-07-04); note the L11 gap as partially closed in the course-eval doc  (files: plugins/netdust-agent/CLAUDE.md, plugins/netdust-agent/README.md, plugins/netdust-agent/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/netdust-core/docs/harness-engineering-course-eval.md)
      Unit test: no unit test: Tier B, docs/manifest edits (version-resolution test module already covers manifest shape)

**Integration gate (C2):** full suite green; fixture run-log → rubric grades match the plan's thresholds table; missing run-log → clean no-trace exit; `gate-check.py specs/run-observability` still green.

── REVIEW GATE ──  *(STOP: commit C2, `/integration`, `/code-review` — tier STANDARD)*

---

## Phase-complete gate

After all clusters: `testing-workflow` phase-complete (integration + acceptance) → `test-effectiveness` audit → `shake-out`. Then `superpowers:finishing-a-development-branch`. (building Stage 3.)

## Dependency notes

- T02 depends on T01 (emits through `run-trace.py`) — sequential within C1; T03 is prose and could interleave but names T01's CLI, so it follows T01 conceptually (kept non-`[P]` for honesty).
- T04 depends on T01's schema (reads the log) and on C1 being reviewed — it opens C2.
- T05/T06 are `[P]` (different files, both depend only on T04's existence for accuracy of what they describe — dispatch after T04 lands).
- T07 last — it describes everything shipped before it.
