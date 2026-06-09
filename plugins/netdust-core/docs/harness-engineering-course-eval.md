# Harness-Engineering Course — netdust-core Gap Analysis

**Created:** 2026-06-07
**Source rubric:** [walkinglabs/learn-harness-engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) — a 12-lecture course on harness engineering for AI coding agents (the *pedagogical* sibling of the `awesome-harness-engineering` list that drove [`harness-engineering-hardening-plan.md`](./harness-engineering-hardening-plan.md)).
**Method:** Each of the 12 lectures distilled to (thesis · failure mode · prescribed artifacts · single testable criterion), then scored against the netdust-core harness as it stands at HEAD. Every ✅/⚠️/❌ is keyed to a file. No code changed in producing this report.
**Ground-truth checked this session:** agent `tools:` lines (all 8 scoped), `hooks/hooks.json` events (4, incl. `PreToolUse`), `hooks/pretooluse-guard.py` exists (commit `eb9b675`), agent-scoping landed (commit `9a6b643`).

---

## Scorecard at a glance

| # | Lecture (principle) | Verdict | Convergence point in netdust-core |
|---|---------------------|---------|-----------------------------------|
| 01 | Strong models ≠ reliable execution | ✅ Covered | `harnessed-development` is the whole-pipeline thesis made operational |
| 02 | A harness is 5 subsystems, not a prompt | ✅ Covered | Instructions (CLAUDE.md/RULES.md) · Tools (allowed-tools) · Env (dev-stack) · State (memory/) · Feedback (integration→shakeout) |
| 03 | Repo = single source of truth | ✅ Covered | `memory/STATE.md` + `lessons.md` + `tasks/todo.md`, loaded by SessionStart |
| 04 | Split instructions across files | ✅ Covered | CLAUDE.md (entry) → skills/ (topic docs) → RULES.md (hard constraints) |
| 05 | Keep context alive across sessions | ✅ Covered | SessionStart load + SessionStop tag-scanner + `DECISIONS.md` convention |
| 06 | Initialization is its own phase | ⚠️ **Partial** | Stack `*-new-project` scaffolds; no *fresh-session readiness check* phase |
| 07 | Draw clear task boundaries (WIP=1) | ⚠️ **Partial** | Review-gate markers + group sizing bound *batches*; no explicit WIP=1 / active-task lock |
| 08 | Feature lists are harness primitives | ⚠️ **Partial** | Prose plan + acceptance-flow matrix; **no machine-readable feature registry with pass-gates** |
| 09 | Don't let the agent declare victory early | ✅ Covered | testing-workflow tiers · feature-acceptance · separate reviewer agents · SubagentStop gate |
| 10 | Only a full pipeline run counts | ✅ Covered | feature-acceptance drives real browser + un-mocked wire; test-effectiveness audits blindness |
| 11 | Observability belongs inside the harness | ⚠️ **Partial / weakest** | Hook log + memory tags exist; **no per-run trace, sprint-contract, or evaluator rubric** in the build loop |
| 12 | Every session leaves a clean state | ⚠️ **Partial** | SessionStop captures *memory*; no enforced **session-exit checklist** (build/tests green, no debug code) |

**Tally:** 6 ✅ fully covered · 6 ⚠️ partial · 0 ❌ absent. The course validates the spine of netdust-core. The six partials cluster into three genuinely new ideas the harness does not yet have a named home for (see "What the course surfaces that we lack").

---

## Lecture-by-lecture

### L01 — Strong models don't mean reliable execution · ✅ Covered
**Course thesis:** Reliability is a harness property, not a model property; same model + harness beats same model bare (Anthropic's 2D-editor experiment: $9/broken vs $200/playable).
**netdust-core:** This *is* the founding premise of `skills/harnessed-development/SKILL.md` — "the single entry point … so no session can skip a gate." The whole plugin is the harness the lecture argues for.
**Testable criterion (course):** same model, qualitatively different reliability with/without harness → satisfied by design; the `evals/` RUNBOOK + archived baseline-vs-skill-on runs are exactly this A/B.
**Gap:** none.

### L02 — What a harness actually is (5 subsystems) · ✅ Covered
**Course thesis:** Instructions + Tools + Environment + State + Feedback; missing any one plateaus at 40–60%.
**netdust-core mapping:**
- *Instructions* → `CLAUDE.md`, `RULES.md`, `SOUL.md`, per-skill SKILL.md
- *Tools* → commands declare `allowed-tools`; agents declare `tools:` (now scoped)
- *Environment* → `skills/dev-stack` (DDEV, Makefile, `.env`, `site.yml`)
- *State* → `memory/STATE.md` + `lessons.md` + `tasks/todo.md`
- *Feedback* → `/integration` → `/shakeout`, testing-workflow, reviewer agents
**Gap:** none — all five subsystems are present and named.

### L03 — Repository as single source of truth · ✅ Covered
**Course thesis:** "Information not in the repo doesn't exist for the agent." Prescribes `AGENTS.md`, per-module `ARCHITECTURE.md`, `CONSTRAINTS.md`, `PROGRESS.md`.
**netdust-core:** Equivalent set — `CLAUDE.md` (entry), `ARCHITECTURE-INVARIANTS.md` (constraints, authored by `skills/architecture-invariants`), `memory/STATE.md` (progress). SessionStart loads them every session.
**Testable criterion (course):** a fresh session answers "what is this / how built / how run / how verify / where are we" from repo alone → satisfied: STATE.md + CLAUDE.md + site.yml cover all five.
**Gap:** minor — the course wants per-module `ARCHITECTURE.md`; netdust-core centralizes in one `ARCHITECTURE-INVARIANTS.md`. Equivalent intent, different granularity. Not worth changing.

### L04 — One giant instruction file fails · ✅ Covered
**Course thesis:** Keep entry file 50–200 lines; split topics into `docs/`; put hard constraints at top/bottom (never the lost-in-the-middle); each rule documents its source + applicability + expiry.
**netdust-core:** Entry `CLAUDE.md` delegates to ~17 topic skills; hard constraints isolated in `RULES.md`. The skill-description-as-trigger pattern is the split the lecture asks for, taken further (skills load *on demand*, so they don't even occupy context until relevant).
**Gap:** the "every rule documents its **expiry condition**" discipline is not enforced. Skills rarely state when a rule can be retired — `skill-audit` flags 90-day-stale skills but doesn't require an expiry field. Minor, optional.

### L05 — Long-running tasks lose continuity · ✅ Covered
**Course thesis:** `PROGRESS.md` + `DECISIONS.md` + git checkpoints + clock-in/clock-out routines; rebuild cost should drop from ~15min to <3min.
**netdust-core:** SessionStart "clock-in" loads STATE.md/lessons.md/todo.md; SessionStop "clock-out" lifts `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tags deterministically (`hooks/session-stop.py`). This is *stronger* than the course version — the course relies on the agent remembering to update PROGRESS.md; netdust-core's tag scanner is a deterministic regex that runs whether or not the agent remembers.
**Gap:** none. This is an area where netdust-core exceeds the rubric.

### L06 — Initialization needs its own phase · ⚠️ Partial
**Course thesis:** Init and implementation have different targets; mixing them fails both. A dedicated init session must produce: runnable env, ≥1 passing example test, a **Startup Readiness Checklist** (can-start / can-test / can-see-progress / can-pick-up-next), an ordered task breakdown, and a clean checkpoint commit.
**netdust-core:** Stack commands (`/wp-new-project`, etc.) scaffold CLAUDE.md/site.yml/memory/tasks/Makefile — that covers *new-repo* init. But there is **no fresh-session readiness gate**: nothing verifies, at the start of a session on an *existing* repo, that the four readiness conditions hold before work begins. SessionStart *loads* memory but doesn't *assert* "the build is green and you can run the tests right now."
**Gap (real):** no "session-readiness checklist" step. See fix #2 below. This is the entry-side mirror of L12's exit-side gap.

### L07 — Agents overreach and under-finish (WIP=1) · ⚠️ Partial
**Course thesis:** Reasoning budget C split across k active tasks → C/k each → all fail below threshold. Enforce **one task in `active` status at a time**; track Verified Completion Rate; block new activation when VCR < 1.0.
**netdust-core:** `harnessed-development` Stage 1f (review-group sizing, ~3–4 tasks/cluster) and Stage 2.8 (HALT at `── REVIEW GATE ──`) bound how much ships *between checkpoints* — a batch-level discipline. But there is **no per-task WIP=1 lock**: nothing prevents an implementer dispatch from activating several tasks at once, and there's no VCR metric gating the next activation.
**Gap (real):** the harness controls *review batch size*, not *concurrent-active-task count*. These are related but not the same lever. The course's WIP=1 is a sharper, cheaper constraint. See fix #3.

### L08 — Feature lists are harness primitives · ⚠️ Partial — the sharpest divergence
**Course thesis:** A `feature_list.json` (machine-readable) is read by the scheduler (pick task), the verifier (judge done), and the handoff reporter (summarize). Each item is a triple: `(behavior, verification_command, state)` with a state machine `not_started → active → blocked → passing`, transitions **controlled by the harness, not the agent**, and `passing` reachable only when the verification command exits 0.
**netdust-core:** Tasks live as **prose** in the written plan + `tasks/todo.md` checkboxes. There is rich per-task structure (test expectations, acceptance-flow matrix, STATUS blocks) but it is **not machine-readable and not state-gated** — "done" is asserted in a STATUS block the agent writes, not derived from a verification command the harness ran.
**Why this matters:** the course's whole argument is that completion should be *externally derived from an exit code*, not *agent-reported*. netdust-core gets the same guarantee for the *whole phase* (via `/integration` exit codes) and for *acceptance flows* (driven through the real wire) — but **not per-feature**, and not in a form the scheduler/handoff can read mechanically. This is a deliberate netdust-core stance ("discipline is baked into plan-*writing*, not a post-hoc registry" — hardening plan §8), and it's defensible. But it's the one place the course names a primitive netdust-core genuinely does not have. See fix #1 — proposed as **opt-in**, not a default.
**Gap (real, philosophical):** prose plan vs machine-readable pass-gated registry.

### L09 — Agents declare victory too early · ✅ Covered
**Course thesis:** Models are systematically overconfident; replace feelings with execution. Three validation layers (static → runtime → system); a **separate evaluator agent** (not self-eval); actionable error messages (CHECK/FIX, not "test failed").
**netdust-core:** Directly covered, and well:
- three layers → testing-workflow tiers + `/integration` (static+runtime) + feature-acceptance (system)
- separate evaluator → the 8 reviewer agents, dispatched by `/shakeout`, now read-only (`tools: Read, Grep, Glob, Bash`) so they *structurally cannot* rubber-stamp by editing
- the SubagentStop hook (`hooks/subagent-stop.py`) blocks an implementer that edited code but skipped testing-workflow — a hard, deterministic anti-victory gate the course doesn't even propose
**Gap:** the course's "actionable error message format (CHECK:/FIX:)" is a nice convention not standardized in netdust-core's gate outputs. Minor.

### L10 — Only a full pipeline run counts · ✅ Covered
**Course thesis:** Unit tests are blind to component-boundary defects; only E2E proves system-level absence-of-defects. Promote each new defect category into a permanent automated check.
**netdust-core:** This is exactly `skills/feature-acceptance` (drive the real browser + un-mocked wire) plus `skills/test-effectiveness` (the seven green-but-blind failure modes: stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, missing-denial, no-coverage, concurrency). The "promote a defect into a permanent check" loop is institutionalized as `lessons.md` + the `── REVIEW GATE ──` discipline. netdust-core is **ahead** of the lecture here — the seven-failure-mode taxonomy is more specific than the course's prose.
**Gap:** none.

### L11 — Observability belongs inside the harness · ⚠️ Partial — the weakest dimension
**Course thesis:** Two layers — *runtime signals* (what the system did: lifecycle, feature-path execution, errors; OpenTelemetry trace per session / span per task) and *process artifacts* (why a change should be accepted: a negotiated **Sprint Contract** of scope+verification+exclusions, and an **Evaluator Rubric** scoring table A/B/C/D per dimension).
**netdust-core:** Has the *logging* half — `~/.claude/logs/memory-hook.log` records every hook fire, and memory tags make decisions queryable later. It does **not** have:
- a per-run/per-task **trace** of the build loop (no span-per-task decision path)
- a **Sprint Contract** artifact negotiated before coding (closest analog: the threat-model + acceptance-flow sections, but those are security/behavior, not a scope+exclusions contract)
- an **Evaluator Rubric** scoring table applied to each phase (the reviewer agents emit prose findings, not graded dimensions; `/evaluate` exists but is a discipline-assessment command run *on demand*, not woven into every build)
**Gap (real):** observability is *post-hoc and log-shaped*, not *in-loop and trace/rubric-shaped*. This is the dimension where the course offers the most that netdust-core lacks. See fix #4. (Note: this overlaps the hardening plan's parked Item 3 "context-budget/observability" but is broader — that item was about compaction, this is about run-scoring.)

### L12 — Every session must leave a clean state · ⚠️ Partial
**Course thesis:** Entropy is the default; without an enforced **Session Exit Checklist** debt compounds. Five non-negotiables at clock-out: build passes · all tests pass · feature list updated · no debug code (console.log/debugger/stray TODO) · standard startup path works. 12-week comparison: 68%→97% build-pass with the checklist.
**netdust-core:** SessionStop (`hooks/session-stop.py`) handles the *memory* dimension of clean exit (lifts tags into STATE/lessons/todo) — but it does **not** assert the build is green, tests pass, or that no debug code was left. The full clean-state discipline exists *within* a feature flow (`/shakeout` before merge) but **not as a session-boundary gate**: a session can end mid-feature with red tests and the harness won't object.
**Gap (real):** SessionStop captures knowledge but doesn't enforce hygiene. The course wants both. See fix #5. (Mirror image of L06's missing entry-gate.)

---

## What the course surfaces that netdust-core genuinely lacks

Stripping the six partials of overlap, three distinct ideas remain — none is a "you're doing it wrong," all are "here's a named primitive you haven't adopted":

1. **Externally-derived per-feature completion** (L08). Today "feature done" is agent-asserted in a STATUS block; the course wants it *derived from a verification command's exit code* in a machine-readable registry the scheduler/handoff can read. netdust-core has this guarantee at phase granularity (`/integration`) and for acceptance flows, but not per-feature and not machine-readable.

2. **Session-boundary gates, both ends** (L06 + L12). netdust-core has rich *feature-boundary* gates (plan-time and pre-merge) but treats the *session* as transparent. The course argues the session itself is a unit that should open with a readiness check and close with a hygiene check. The SessionStart/SessionStop hooks are the natural homes — they already fire, they just don't *assert*.

3. **In-loop observability: traces + contracts + rubrics** (L11). netdust-core logs hook fires but doesn't trace the build loop or score runs against a rubric. This is the genuinely missing capability, and it dovetails with the parked hardening-plan Item 3.

Everything else the course teaches, netdust-core already does — and in three places (L05 deterministic tag-scanner, L09 read-only reviewers + SubagentStop gate, L10 seven-failure-mode taxonomy) does it *more rigorously than the lecture prescribes*.

---

## Reconciliation with the existing hardening plan

[`harness-engineering-hardening-plan.md`](./harness-engineering-hardening-plan.md) (from the *list*, 2026-05-31) named three Control-bucket gaps. Their **actual** status at HEAD (verified this session, the doc header is stale — it still says "PARKED"):

| Hardening-plan item | Doc says | **Actual** |
|---------------------|----------|------------|
| 1. Reviewer agents → least privilege | parked | ✅ **DONE** — all 8 agents carry `tools: Read, Grep, Glob, Bash` (commit `9a6b643`) |
| 2. PreToolUse guard | parked | ✅ **DONE** — `hooks/pretooluse-guard.py` registered (commit `eb9b675`) |
| 3. Context-budget / compaction | parked | ⏸ still open — overlaps L11 observability below |

> **Doc-hygiene action (no code):** update the hardening-plan header from `PARKED` to reflect Items 1–2 shipped. (Flagged, not done — this report changes no files but its own.)

The course's three new ideas are **orthogonal** to the list's three Control gaps — the list was about *least privilege + pre-action guards + context budget*; the course adds *completion derivation + session gates + run observability*. Together they form a coherent next-iteration backlog.

---

## Suggested backlog (report only — nothing implemented)

Ordered by impact ÷ effort. All optional; several are deliberately opt-in to preserve netdust-core's "prose plan" stance.

1. **[MED impact / LOW effort] Session-exit hygiene assertion (L12).** Extend `hooks/session-stop.py` to *report* (not block) build/test status + a debug-code grep at clock-out, appending a one-line health note to the memory write. Cheapest path to the highest-ROI lecture (L12's 68%→97% claim). Non-blocking keeps it friction-free.
2. **[MED / LOW] Session-readiness note at SessionStart (L06).** Symmetric to #1: SessionStart already loads memory; have it surface "last integration: <green/red/unknown>" from `.claude/.last-integration` so a session opens knowing whether it inherits a clean tree.
3. **[MED / MED] WIP=1 line in harnessed-development (L07).** Add an explicit "one task in `active` at a time; do not dispatch task N+1 until task N's STATUS=passing" rule to the Stage 2 addendum. Pure prose, composes with existing review-gate markers, sharpens the cheapest reliability lever in the course.
4. **[HIGH / HIGH] In-loop run observability (L11 + hardening Item 3).** The real project. A per-phase trace + an evaluator rubric (graded dimensions) emitted by `/shakeout` into a run log. Largest lift, but it's the one capability the course offers that netdust-core has no analog for. Worth a dedicated brainstorm before committing.
5. **[LOW / HIGH] Opt-in machine-readable feature registry (L08).** Only if a future project actually wants scheduler/handoff automation. netdust-core's prose-plan stance is defensible; don't adopt `feature_list.json` as a default — offer it as a stack-command opt-in if/when an agent-run product needs mechanical task-picking. Lowest priority precisely because the current approach is a *choice*, not a *gap*.

---

*This report evaluates netdust-core against an external rubric and recommends; it changes no harness code. Implementation of any backlog item is a separate, harnessed task.*
