# Feature Specification: Run observability (in-loop trace + evaluator rubric)

<!-- gate-check: legacy-artifact — authored 2026-07-04, before the `## Success criteria` contract existed; shipped and signed off via its C2 integration gate -->

> **netdust override template.** Overrides spec-kit's core `spec-template.md`. Produced by
> `/speckit.specify` (wrapped by the `spec-authoring` skill, Stage 0.5). Describes **what**
> and **why** — **no technology stack** (that is deferred to `plan.md`). All
> `[NEEDS CLARIFICATION]` markers must be resolved by `/speckit.clarify` before a plan is
> written — that is the Stage 0.5 HALT gate.

**Branch:** `claude/handoff-split-god-skill-ueb1kd` · **Created:** 2026-07-04 · **Status:** Clarified

## Problem / why

The harness's observability is post-hoc and log-shaped: `/evaluate` laboriously reconstructs how a sub-phase was executed from git archaeology, and the memory-hook log records hook fires — but nothing records the run *as it happens*, and nothing scores a finished run against the harness's own discipline in a graded, comparable form. This is the weakest dimension in the harness-engineering course eval (L11, fix #4 — "the one capability the course offers that the harness has no analog for"). Concretely and immediately: Loop Phase 3 needs to measure iterations-to-FINISHED, dry stops, planned-vs-unplanned yields, and gates-fired-vs-warranted — today those numbers exist only as scrollback impressions.

## User stories

- As the harness operator (Stefan), I want every armed-loop decision and review-gate crossing recorded to a machine-readable per-feature run log, so that a run can be audited and scored without reconstructing it from git or scrollback.
- As the harness operator, I want a graded rubric (per-dimension letter grades) emitted at spec-close from that log, so that runs are comparable across features and the loop eval (Phase 3) has real numbers.
- As a future session (or `/evaluate`), I want the trace on disk beside the feature's spec artifacts, so that a retro can consume events instead of re-deriving them.

## Functional requirements

- **FR-1:** The system MUST provide a way to append a structured event (name + key=value data, timestamped) to a per-feature run log, and a way to display that log.
- **FR-2:** Every armed-loop gate decision (block/continue, disarm-finished, disarm-budget, disarm-dry, yield-blocked, bypass) MUST be recorded to the run log automatically, without changing any gate's behavior; recording failures MUST never break the gate (fail-open).
- **FR-3:** The harness spines MUST name the controller-level emission points (stage entry, review-gate crossing with stated tier) so a session records them as it executes.
- **FR-4:** The system MUST compile the run log plus the existing seam artifacts (`tasks.md`, gate-check verdict) into a per-feature rubric with letter grades derived mechanically from stated thresholds — no self-assessment, no agent judgment in the grades.
- **FR-5:** The rubric dimensions MUST cover at least: seam integrity, review-cluster discipline, loop efficiency (iterations vs budget, dry stops), yield discipline (planned `[HUMAN]` vs unplanned), and task completion.
- **FR-6:** `/shakeout` MUST surface the rubric in its spec-close report when a run log exists, and MUST proceed normally (with a one-line note) when none exists. The rubric is report-only — it never blocks.

## Acceptance criteria

> These become the contracts the Tier-A tests assert (testing-workflow). Write them so a
> test can be derived from each — concrete and falsifiable, including denial/negative paths.

- [ ] Given a feature dir, when an event is appended, then the run log contains exactly one new well-formed line carrying the event name, data, and timestamp; given a nonexistent feature dir, the append is rejected with a nonzero exit and a one-line reason.
- [ ] Given an armed loop marker and unfinished tasks, when the loop gate blocks a stop, then the run log gains a corresponding decision event; given a read-only/broken log path, the gate's decision is unchanged (fail-open) and the gate still emits its block/disarm output.
- [ ] Given a run log with N loop decisions and a `tasks.md` with M declared clusters and a `Loop budget: ~B`, when the rubric compiles, then each dimension's grade matches the documented thresholds for those inputs (fixture-driven, at least one fixture per grade boundary).
- [ ] Given NO run log for a feature, when the rubric compiler runs, then it exits cleanly with a "no trace recorded" note and writes no rubric (denial path — never fabricates grades).
- [ ] Given a completed run log fixture, the rubric records planned yields (`[HUMAN]` tasks yielded) separately from unplanned yields (BLOCKED without `[HUMAN]`), and neither is counted as the other.

## Security-relevant surfaces  [pre-flag for the plan's threat model]

> Not a threat model (that is authored at plan-time). This is an early flag so the planner
> knows the `threat-modeling` gate (1a) will fire. Check any that apply:

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [x] None of the above — *all inputs are harness-authored repo artifacts (`tasks.md`, the run log this feature itself writes, gate-check JSON) in the same trust domain `loop-check.py` already parses; no network, no credentials, no cross-actor data.*

## Clarifications

> Filled by `/speckit.clarify`. Each resolved ambiguity recorded as Q→A. The Stage-0.5 gate
> HALTS if any `[NEEDS CLARIFICATION: …]` marker remains anywhere in this spec.

- Q: Trace transport — OpenTelemetry (course's suggestion) or a local file? → A: A local per-feature JSONL file. Rule adopted 2026-07-04: *own what encodes discipline, rent transport* — the discipline is the event record; OTel export can wrap the file later if ever wanted.
- Q: Who grades the rubric — an evaluator agent or a deterministic compiler? → A: Deterministic compiler, same pattern as `gate-check.py`/`loop-check.py` (small checker + thin hook). Judgment-shaped assessment stays in `/evaluate`; the rubric grades only what artifacts can prove.
- Q: Is the run log committed or runtime-only (like the gitignored loop marker)? → A: Committed at spec close — it is a process artifact (the course's whole point), not runtime state. The loop *marker* stays gitignored; the *log* is the record.
- Q: Per-task spans (course's span-per-task) in v1? → A: No — controller/hook-level events only (stage, review gate, loop decision). Per-task evidence already lives in the Test-evidence + STATUS blocks and commit bodies; duplicating it as spans is bloat before validated need.

## Out of scope

- OpenTelemetry / any network export, dashboards, or daemons — the artifact is a file.
- A new evaluator agent or any change to reviewer agents — grades are mechanical.
- Rewriting `/evaluate` — it may consume the trace in a future pass; v1 only leaves it a pointer.
- A sprint-contract artifact (course L11's other half) — spec.md + plan.md already carry scope + exclusions; revisit only if a real gap shows up in practice.
- Grading code quality — that is the reviewers' job; the rubric grades harness discipline.
- Any new gate or HALT — this feature records and reports; it never blocks (standing rule: new gates must replace or merge, never append).

## Open questions / [NEEDS CLARIFICATION]

(none — section intentionally empty; all shape questions resolved under Clarifications)
