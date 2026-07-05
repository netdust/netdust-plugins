# Tasks: Harness efficiency tuning (empirical adjustments from the 2026-07-04 runs)

> **netdust override template.** Overrides spec-kit's core `tasks-template.md`. It is the
> **handoff artifact — THE SEAM**: `building` Stage 2 executes from this file, and refuses to start until `gate-check.py` is green and the plan is approved. spec-kit's
> `/speckit.implement` is **never** run — it would bypass the Stage-2 gates (threat-model
> verify, test tiers, review-cluster HALT, `subagent-stop.py`). Execution is driven by
> `superpowers:subagent-driven-development` / `executing-plans` under the netdust spine.
>
> `spec-analysis` (Stage 1.5) verifies: every task carries a **test tier**, every phase a
> per-phase integration gate, clusters are ≤4 tasks, and irreversible steps are solo.

**Spec:** `specs/harness-efficiency/spec.md` · **Plan:** `specs/harness-efficiency/plan.md`

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

> This file dogfoods the D1 field this feature introduces: every task carries a
> `Test-author:` mode line. The mode is set HERE, at plan time, by the planner —
> the controller reads it at dispatch; no run-time agent may change it (plan invariant #1).

```
- [ ] T<NN> [P?] [Tier A|B] <imperative description>  (files: <paths>)
      Test-author: <split | solo — reason>  (D1 rule: split iff Tier A on a security-boundary
                  category — auth/guards, untrusted parsing, migrations, money, 1a surface)
      Unit test: <what behavioral contract to verify — RED-first incl. denial path for Tier A;
                  or `no unit test: Tier B, <reason>` for glue/wrapper/presentational>
      Seam test: <only if this task WIRES a piece into the real chain — 1 un-mocked assertion
                  + 1 negative case; else omit>
```

> **Tier reminder (testing-workflow):** parsing, transforms, threshold logic = **Tier A always**.
> Prose/doc edits and description bumps = **Tier B**.

---

## Phase 1 — tier-conditional test/dev split

### Cluster C1  (3 tasks · provisional tier: STANDARD)
- [x] T01 [Tier A] Extend `spec-kit/gate-check.py` with the `test-author-mode` check — implement the D1 rules table verbatim (WARN when the field is wholly absent so pre-0.8 feature dirs never retro-fail; FAIL on partial presence naming bare task ids; FAIL on invalid value; FAIL on `[Tier A]` + `solo` without a reason after a dash; WARN on `[Tier B]` + `split`; fenced examples stripped via the existing `strip_fenced`)  (files: plugins/netdust-agent/spec-kit/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
      Test-author: split — this check IS the mechanical enforcement point of the no-self-downgrade invariant; the guard against self-grading must not itself be self-graded
      Unit test: one fixture per D1 rules-table row → exact verdict + detail text; denial paths: partial presence FAILs naming the bare tasks, Tier-A-solo-without-reason FAILs; retro-compat: a run-observability-shaped tasks.md (zero `Test-author:` lines) stays GATE: PASS with the WARN; a fenced `Test-author:` example never counts
      Seam test: run the real script (un-mocked subprocess) on `specs/run-observability` → still exit 0; on this feature's own dir → exit 0; negative: a fixture dir violating D1 → exit 1
- [x] T02 [P] [Tier B] Add the `Test-author:` line to the per-task format in `spec-kit/overrides/tasks-template.md` — extend the format block (as dogfooded at the top of this file) and add the D1 decision-rule guidance blockquote (split iff Tier A on a security-boundary category; solo needs a reason for Tier A; the mode is the planner's call, read by the controller, never re-decided at run time)  (files: plugins/netdust-agent/spec-kit/overrides/tasks-template.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, template-prose edit; T01's fixtures assert the grammar it documents
- [x] T03 [Tier B] Rewrite `skills/building/SKILL.md` Stage 2 to the tier-conditional dispatch per plan D2 — the controller reads each task's `Test-author:` mode from `tasks.md` (never lets any agent re-decide it): `split` keeps today's pair protocol byte-for-byte (Step 2.1b ordering, both addenda, Step 2.6 reconciliation); `solo` dispatches ONE implementer doing RED-first TDD itself with the solo evidence lines (`Contract test author: self — solo mode (plan: Test-author: solo)`, `Weakened? n/a — self-authored (solo mode)`); update `<test_dev_split>`, the enforcement-honesty ledger (solo self-authorship stated openly; independent check = cluster review + test-effectiveness; the boundary is machine-checked by T01), `<stage_personas>`, precondition Class E row + Step 2.0 Class E row (solo default; security-boundary = Class D = split), Step 2.7 Class C rule (1a-surface finding = split reproduction), the addenda (add the solo implementer variant), red flags (retarget the "never fuse the pair" rows at SPLIT tasks; add "the implementer decides its own task is solo" as the new red flag), success criteria, and integration table  (files: plugins/netdust-agent/skills/building/SKILL.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, skill-prose edit; contract verified at the C1 review gate against plan D2

**Integration gate (C1):** full suite green (`tests/run.sh`); gate-check verdicts match the D1 rules table on every fixture; `python3 plugins/netdust-agent/spec-kit/gate-check.py specs/run-observability` still exits 0 (retro-compat live); `… specs/harness-efficiency` exits 0 (dogfood green).

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, `/code-review` — tier STANDARD; do not start C2 until clear)*

### Cluster C2  (3 tasks · provisional tier: LIGHT)
- [x] T04 [Tier B] Update the agent preambles to the tier-conditional protocol — `agents/test-author.md`: dispatched ONLY for `Test-author: split` tasks; its tier-classification duty is scoped to challenging a misclassified CONTRACT, never to converting a solo task to split or back (the plan owns the mode); `agents/implementer.md`: add the solo-mode protocol (when the controller's dispatch states `Test-author: solo`, author your own RED-first behavioral test — RED still mandatory, watched RED→GREEN, denial path for any guard/parser — and record the solo evidence lines per plan D2; you NEVER choose solo yourself — the mode arrives from the plan via the controller)  (files: plugins/netdust-agent/agents/test-author.md, plugins/netdust-agent/agents/implementer.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, agent-prose edits; contract verified at the C2 review gate against plan D2
- [x] T05 [P] [Tier B] Make `skills/testing-workflow/SKILL.md` ("Who authors vs who greens" table + the "How This Connects to Superpowers" diagram) and `skills/writing-tests/SKILL.md` (handoff sentence) tier-conditional per D2 — the tier RULE is untouched; only WHO applies it becomes mode-dependent; append calibration `tier-conditional-split` to `skills/_shared/calibrations.md` (2026-07-04 evidence: 2× dispatches + 4–6 min/task; the only incident was the test-author's own defective fixtures on T04, ~15 min + 3 dispatches; review gates + test-effectiveness caught all real bugs) — calibrations are APPEND-ONLY, `self-grading-split` stays as history  (files: plugins/netdust-agent/skills/testing-workflow/SKILL.md, plugins/netdust-agent/skills/writing-tests/SKILL.md, plugins/netdust-agent/skills/_shared/calibrations.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, skill-prose edits; sibling grep at the C2 gate is the check
- [x] T06 [P] [Tier B] Add the field-authoring duty to the PLAN spine — `skills/planning/SKILL.md` 1d facet (task-shaping): every task also carries a `Test-author:` mode line set by the D1 decision rule, machine-checked by gate-check at Stage 1.5; a Tier-A task on a security-boundary category is ALWAYS `split` (the planner may not talk a 1a-surface task down to solo)  (files: plugins/netdust-agent/skills/planning/SKILL.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, skill-prose edit; T01's checker is the mechanical half

**Integration gate (C2):** sibling grep (plan D2 list): `grep -rn "test-author\|test/dev split" plugins/netdust-agent/skills plugins/netdust-agent/agents plugins/netdust-agent/README.md` shows no remaining unconditional-split claim (plugin.json/marketplace.json wait for T12); building/testing-workflow/planning/agents tell one consistent story — same grammar, same single reader (the controller), same independent-check statement for solo.

── REVIEW GATE ──  *(STOP: commit C2, `/integration`, `/code-review` — tier LIGHT)*

---

## Phase 2 — presence-aware planning + Class F intake

### Cluster C3  (3 tasks · provisional tier: LIGHT)
- [x] T07 [Tier B] Add the presence rule to `skills/planning/SKILL.md` per plan D3 — in `<stage_persona>`: inline planning while the human is present and actively steering; background `planner`/plan-correction dispatch only when the human has stepped away or the output feeds an unattended run (armed `/loop`, tmux loop, scheduled); in the seam/Stage-1.5 text: the review ladder before UNATTENDED execution (gate-check + human approval + `doubting-decisions` on the key decision) is MANDATORY regardless of planning mode — presence changes where planning happens, never which gates fire; add the red-flag row ("the user is mid-pivot and I'm dispatching a background planner"); append calibration `background-planner-pivots` (Sofie 2026-07-04: two <10-min pivots invalidated finished background plans; the pre-unattended ladder caught 4 loop-breakers — highest-ROI gate of the day)  (files: plugins/netdust-agent/skills/planning/SKILL.md, plugins/netdust-agent/skills/_shared/calibrations.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, skill-prose edit; contract verified at the C3 review gate against plan D3
- [x] T08 [Tier B] Add Class F to `skills/harnessed-development/SKILL.md` per plan D4 — intake-table row **F — Shaping / vision-stage exploration** (no code will change this session → `superpowers:brainstorming` + `refining-ideas` only; at most a scope sketch / notes doc; explicitly NO spec/plan/tasks artifact, NO gate ceremony, NO feature dir; promotion path: re-enter intake as Class A when it becomes real work); extend the dial line (`F = brainstorm only, notes at most`); add the red-flag row ("the user is describing a vision → don't manufacture a plan artifact"); update the frontmatter description (A–E → A–F) and objective text; append calibration `vision-brief-ceremony` (teacher-app 2026-07-04: a "we don't implement today" brief routed into full planning; 30+ min wait)  (files: plugins/netdust-agent/skills/harnessed-development/SKILL.md, plugins/netdust-agent/skills/_shared/calibrations.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, skill-prose edit; contract verified at the C3 review gate against plan D4
- [x] T09 [Tier B] Update `agents/planner.md` for all three protocol changes — protocol step 1 class list gains F (classify it, route to brainstorm-only, produce NO plan artifact, name the promotion path); protocol gains the `Test-author:` field-authoring duty (D1 rule, security-boundary Tier A never solo); add the presence note (this persona is the BACKGROUND planning mode — when dispatched, the presence decision was already made by the root session per D3)  (files: plugins/netdust-agent/agents/planner.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, agent-prose edit; consistency with T06/T07/T08 checked at the C3 gate

**Integration gate (C3):** class-enumeration grep (plan Sibling audit): `grep -rn "A–E\|Class E\|Class F" plugins/netdust-agent/skills plugins/netdust-agent/agents plugins/netdust-agent/CLAUDE.md plugins/netdust-agent/README.md` — every hit gained F or is confirmed class-specific; `building`'s precondition table deliberately unchanged (F never reaches it); presence rule reads identically in spine and persona; NO new gate/HALT introduced anywhere in P2.

── REVIEW GATE ──  *(STOP: commit C3, `/integration`, `/code-review` — tier LIGHT)*

---

## Phase 3 — cost telemetry + version

### Cluster C4  (2 tasks · provisional tier: STANDARD)
- [x] T10 [Tier A] Add `--durations` to `spec-kit/run-trace.py show` per plan D5 — consecutive-event segment table (event names + key data for review-gate/stage-enter rows) with wall-clock deltas + a first→last total; corrupt/unparseable-ts lines skipped consistent with `show`; <2 parseable events → `durations: not derivable (<2 timestamped events)`, exit 0; WITHOUT the flag, output byte-identical to today  (files: plugins/netdust-agent/spec-kit/run-trace.py, plugins/netdust-agent/tests/test_run_trace.py)
      Test-author: split — A-lite by the D1 letter (harness-authored input), deliberately promoted to split by the plan: this cluster is the feature's highest-risk logic and its own dogfood of the pair protocol; over-ceremony on Tier A is always permitted (the plan owns the mode)
      Unit test: fixture log with known timestamps → exact segment rows + total; denial: single-event log → "not derivable" exit 0; corrupt line skipped without crashing; empty/missing log → existing "no trace recorded" behavior unchanged; no-flag invocation → byte-identical output to the pre-change rendering (captured fixture)
- [x] T11 [P] [Tier A] Build `spec-kit/run-cost.py` per plan D6 — `run-cost.py <feature-dir> [--transcript-dir <dir>]`; default dir from the ground-truthed cwd-slug rule; walks main-session `*.jsonl` + `<session>/subagents/agent-*.jsonl` (+ `meta.json` for agentType/description); sums `.message.usage` token fields over assistant lines; per-dispatch table + per-stage table joined to `run-log.jsonl` timestamp windows (same boundary-event vocabulary as D5; run-cost segments over boundary events only — a subset of D5's all-events segmentation; on boundary-only fixtures the windows coincide); normalizes `Z` and `+00:00` timestamps; STRICTLY read-only on the transcript dir; stdout only, counts + metadata only — never message content  (files: plugins/netdust-agent/spec-kit/run-cost.py, plugins/netdust-agent/tests/test_run_cost.py)
      Test-author: split — parses foreign-format files this repo does not author (Claude Code transcripts) and guards the transcript-dir read-only integrity boundary; the D1 nearest-category call (untrusted-format parsing + an integrity boundary) goes to split
      Unit test: fixture transcript dir + fixture run-log → per-dispatch totals equal hand-summed usage per transcript, agentType/description from meta.json, window attribution to the correct stage segment, both timestamp forms parsed; denial: missing transcript dir → exit 0 `no transcript found: <dir>` and no report; transcripts but no run-log → per-dispatch only + `per-stage attribution skipped` note, exit 0; malformed transcript line skipped without crash; absent meta.json → dispatch labeled `unknown`, no crash; read-only proven: transcript-dir listing + mtimes byte-identical before/after the run
      Seam test: run the real script (un-mocked subprocess) against the fixture dir → exit 0 + expected table; negative: nonexistent feature dir → nonzero usage error

**Integration gate (C4):** full suite green; same boundary-event vocabulary; run-cost segments over boundary events only (a subset of D5's all-events segmentation); on boundary-only fixtures the windows coincide (a shared boundary-only fixture run-log yields the same window boundaries in D5 and D6 outputs); every degradation path exits 0 with its one-line note; the read-only assertion holds; no file written anywhere but stdout.

── REVIEW GATE ──  *(STOP: commit C4, `/integration`, `/code-review` — tier STANDARD)*

### Cluster C5  (1 task · provisional tier: LIGHT)
- [x] T12 [Tier B] Describe + version — bump netdust-agent 0.7.0 → 0.8.0 (minor: behavior change in the agent dispatch protocol) in `plugin.json` + root `marketplace.json`, and CORRECT both descriptions where they state the unconditional split ("an independent test-author writes each task's RED test…" → tier-conditional per the plan's Test-author field); add the four adjustments to `README.md` + plugin `CLAUDE.md` harness-layer lines; mirror run-observability T07's shape  (files: plugins/netdust-agent/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/netdust-agent/README.md, plugins/netdust-agent/CLAUDE.md)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, docs/manifest edits (existing `test_plugin_version_resolution.py` covers manifest shape)

**Integration gate (C5):** full suite green (incl. `test_plugin_version_resolution.py`); both manifests read 0.8.0; description grep shows no unconditional-split claim anywhere in the repo; `python3 plugins/netdust-agent/spec-kit/gate-check.py specs/harness-efficiency` exits 0.

── REVIEW GATE ──  *(STOP: commit C5, `/integration`, `/code-review` — tier LIGHT)*

---

## Phase-complete gate

After all clusters: `testing-workflow` phase-complete (integration + acceptance) → `test-effectiveness` audit (pay special attention to T10/T11: threshold/segmentation logic and the seven green-but-blind modes) → `shake-out`. Then `superpowers:finishing-a-development-branch`. (building Stage 3.)

## Dependency notes

- T01 defines the D1 grammar mechanically; T02 documents it and T03 wires the controller to it. T02 is `[P]` against T01 (different files, both build to the plan's D1 table verbatim — the plan, not T01's code, is the shared source of truth). T03 follows T01 conceptually (its prose cites the machine check) — kept non-`[P]` for honesty.
- C2 (T04/T05/T06) are sibling-site propagations of D2 — all cite the plan, not each other; T05/T06 are `[P]` (disjoint files); T04 leads because the agent files are what the C1-reviewed spine dispatches.
- C3: T07/T08 are disjoint edits; T09 consolidates both into the persona, so it runs last (kept non-`[P]`; T07 and T08 both touch `calibrations.md` — sequential T07→T08 avoids the append collision, T08 not `[P]`).
- T10/T11 are `[P]` as pairs (disjoint files); both split — dispatch two test-authors, then two implementers. T11's fixture builder must never point tests at a real transcript dir — fixtures only, in the tests' tmp dir.
- T12 last — it describes everything shipped before it. Its description edits complete the sibling sweep started at C2 (plugin.json/marketplace.json were deliberately deferred to keep the version + description change atomic, matching run-observability T07).
