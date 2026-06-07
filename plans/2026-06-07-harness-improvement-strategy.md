# Plan — Harness improvement strategy (eval-informed) — netdust-core

**Date:** 2026-06-07
**Repo:** `github.com:netdust/netdust-plugins`, plugin path `plugins/netdust-core/`
**Branch for this work:** `claude/harness-evaluation-IXMMd`
**Class:** A — multi-task change to the harness itself.
**Status:** PLAN ONLY — no implementation yet.

**Relates to (does not duplicate):** `plans/2026-06-07-harness-completeness-and-rigor.md` owns the *axis-completeness* items (reviewer tool-scoping = Item 1, PreToolUse guard = Item 2, compaction = Item 3, rigor dial = Item 4). This doc is the *strategy layer* on top — what to build, in what order, and why — informed by evidence that didn't exist when that plan was written: the 2026-06-07 blind behavioral eval of `harnessed-development` + the six gate skills.

---

## What changed: we now have process-layer evidence

The `harnessed-development-workspace` eval (2026-06-07, blind Sonnet judges, shuffled order, sibling near-misses in the should-not slots, pass-in-both assertions dropped) established two things:

1. **Fidelity is proven.** `harnessed-development` triggers 20/20 (0 FP, 0 FN). The six gates are 4/6 clean; the 2 defects are one-line description fixes (already in hand). Behaviorally, with-skill produces every structured artifact (work-class label, `## Threat model` section, ARCHITECTURE-INVARIANTS.md, tier/RED/deferral blocks, acceptance matrix, review-cluster STOP markers, Class-D recognition); baseline produces **none**.

2. **The value is artifact + tail + audit, NOT teaching.** On a strong baseline (Sonnet 4.6) the model already does the *spirit* of every gate unprompted — convergence reasoning, denial-path tests, mutation checks, real-browser edge tables. What it omits is the *named, committed, auditable artifact*. As models strengthen, the teaching value of skill prose decays toward zero; the durable value concentrates in (a) the artifact, (b) tail-coverage (firing the time the model would skip), and (c) auditability.

---

## Organizing insight (the thesis this plan is built on)

The harness has proven it *fires*. The frontier is what it *produces and prevents*. That collapses improvement into two moves and rules out a third:

- **Move 1 — Deterministic, not honored.** Push the highest-value gates from "the model honors them" to "a machine enforces them." Proven-reliable firing is good; deterministic enforcement covers the case where the model's judgment fails entirely (prompt injection, hallucinated path, the moment it skips).
- **Move 2 — Outcome, not firing.** We measured *fidelity* (gates fire). We have not measured *outcome* (code has fewer bugs). That is the gap between the question ("clean, secure, bug-free") and what's proven ("the artifact exists").
- **Anti-goal (default lean, not invariant) — more teaching.** Adding skill prose that explains *how to think* to a model that already thinks is **usually negative ROI** — it dilutes attention on the gates that matter. The default improvement is *less* harness prose, *more* measurement and *more* deterministic floors: no new "teaching" skills, and no prose expansion of skills the eval showed baseline already complies with (architecture-invariants, shake-out were flagged "baseline near-complete"). **This is a lean, not a law** — it rests on the *fidelity* eval (which showed Sonnet has the spirit), not on an outcome A/B of prose-rich vs prose-lean skills, which we have not run. So Improvement 1 is explicitly *allowed to revise it*: if a non-circular replay shows a bug class is caught only when a skill teaches X, that is evidence *for* one targeted prose addition. Don't let this anti-goal pre-close the door the outcome eval exists to open.

---

## Improvement 1 — Defect-replay outcome eval `[HIGHEST LEVERAGE]`

**Source pattern:** SWE-bench — credibility comes from *resolving a known issue*, not from process fidelity.

**The asset we already own:** every entry in `netdust-wp/skills/ntdst-architecture/lessons.md` and `netdust-wp/skills/ntdst-data/lessons.md` is a real, characterized production bug with a known fingerprint:
- `post_title` → `_ntdst_post_title` orphan-meta (60 corrupted posts; fingerprint: `_ntdst_post_*` keys in DB)
- swallowed `WP_Error` → vanishing orphan registrations (fingerprint: `WP_Error`-returning call with no `is_wp_error()`)
- `ntdst_data()->get()` direct access outside a repository / pass-through service drift
- 867 passing unit tests, 15 wiring bugs found only by shake-out

**Consequence — this is a netdust-wp-stack outcome eval.** The fingerprinted dataset lives in the `netdust-wp` sub-plugin, not in core. So Improvement 1 measures the harness *as exercised through netdust-wp* (the core gates firing against WordPress-stack work), not core in isolation. That's the right first target — it's where the labeled defects are — but the catch-rate table's verdict is stack-scoped: "the harness caught N/M on the netdust-wp stack." Generalizing to other stacks (Statamic, Bun) needs a labeled defect set for those, which doesn't exist yet. State the scope on the result; don't read a netdust-wp catch rate as a core-wide one.

**Build:** replay each historical bug as a scenario, **harness-on vs harness-off**, and measure **caught-vs-escaped** in the final diff. Reuse the proven blind-judge method from the workspace eval. Judge checks the final diff against the bug's fingerprint, not "did the agent think about it."

**Attribution (requires Improvement 2's trajectory log):** record *which* gate caught each bug (reviewer / shake-out / testing-workflow / threat-model). A gate that catches nothing across the replay set is ceremony — cut it.

**Guard against self-deception (the same discipline the workspace eval showed by dropping pass-in-both assertions):**
- **Circular (low value):** replaying a bug whose fix is now *documented in a knowledge skill* mostly re-tests knowledge injection, which the +15 rubric eval already covers. Mark these and weight them low.
- **Non-circular (high value):** plant a bug class **not** covered by any knowledge skill (a wiring/state-machine bug like the 867/15 class) and see if the **process gates** (shake-out, two-stage review, testing-workflow) catch it. *This is the real test of the process layer* — the one piece of the harness still unmeasured for outcome.

**Why first:** it answers the actual question ("is the code better"), and it directs every other investment — it tells you which gates to keep before you build more. Cheap now that the method is proven; the dataset is already in the repo.

**Acceptance:** a scenario suite (one per replayed incident, tagged circular/non-circular); a harness-on-vs-off catch-rate table per bug class; per-gate attribution. **Verification:** the suite reproduces each historical bug in the harness-off leg (if it can't reproduce the bug, the scenario is wrong).

---

## Improvement 2 — Execution-Control floor + trajectory log `[HIGHEST SAFETY]`

**Owns:** `plans/2026-06-07-harness-completeness-and-rigor.md` Items 1 + 2 (reviewer tool-scoping; PreToolUse destructive-action guard). Not restated here — see that doc for the denylist, threat model, and failure-mode invariants.

**New framing from the eval:** the PreToolUse guard is the *ultimate tail-coverage mechanism* — the deterministic floor for the moment the model's judgment fails completely (prompt injection, hallucinated path, autonomous-loop overrun). It is the same "discipline-not-teaching" philosophy the eval validated, applied to the irreversible-action boundary. This is not a Control checkbox bolted on; it is the proven philosophy extended to the one boundary where "honored by the model" is not good enough because the failure is unrecoverable.

**Add here — PostToolUse JSONL trajectory log.** Source: OpenHands event stream. Previously deferred; now a **prerequisite for Improvement 1** — you cannot attribute *which gate caught (or missed)* a planted bug without a per-tool-call record to replay. Graduates from "nice to have" to "build it to enable the outcome eval."

**Acceptance / verification:** per Items 1+2 in the completeness plan, plus: the JSONL log captures per-subagent tool calls sufficient to answer "which gate fired on this scenario."

---

## Improvement 3 — Architecture-lint (ACI applied to convergence points) `[BUILD AFTER Improvement 1 VALIDATES IT]`

**Source pattern:** SWE-agent ACI — the *interface* enforces, not the prose.

**Problem:** `architecture-invariants` names "the ONE place authorization / data-access / live-update is decided," and `/code-review` *reads* the doc and a reviewer *manually* hunts bypasses. That is prose-checked enforcement — exactly the class the PreToolUse guard replaces for destructive commands.

**Fix:** for each named convergence point, write a **deterministic check** — a grep rule, a small AST lint, or a fixed-query reviewer — that mechanically flags any serve/write path not routed through the named function (e.g. "every CPT write that doesn't go through a `*Repository`", "every `WP_Error` return with no `is_wp_error()` caller", "every `wp_ajax_*` outside the framework handler"). Converts "the reviewer *should* catch the bypass" into "the bypass *fails a check*."

**Note:** the fingerprints for the first checks already exist in the `lessons.md` "Fingerprint of this bug" lines — the outcome eval (Improvement 1) will tell you which are worth automating.

**Acceptance:** at least the three highest-frequency drift classes from `lessons.md` have a deterministic check that fails on a planted bypass and passes on clean code. **Effort:** medium; start with grep-level rules before AST.

---

## Improvement 4 — Hygiene `[CHEAP, FOLD IN]`

- **Memory dedup.** `netdust-core/evals/memory/STATE.md` and `netdust-wp/memory/STATE.md` each contain the identical tagged-capture block 3–4× verbatim — the Stop hook double-writes. The "best-in-class Remember" design is leaking in its own dogfood. Add dedup (skip a capture whose `(date, text)` already exists). Add a regression test in `tests/`.
- **Evidence-in-repo convention.** The efficacy evidence kept living off-repo (`~/Sites/.../eval-log.md`, the workspace) until pushed manually — which violates the harness's own `architecture-invariants` principle ("make confidence a PROPERTY OF THE REPO"). Convention: eval results commit *beside* the skill they measure (as `harnessed-development-workspace` now does). Document it so the next skill-eval lands in-repo by default.

---

## Mapped to the 8 axes + framework source

| Axis | Status now | This plan's improvement | Source |
|---|---|---|---|
| Observe & Plan | strong (plan = convergence target) | machine-check the artifacts (Imp 3) | SWE-agent ACI |
| Verify | **fidelity proven, outcome unmeasured** | **defect-replay outcome eval (Imp 1)** | SWE-bench |
| Control (execution) | the one true axis gap | tool-scoping + PreToolUse floor (Imp 2) | Codex / awesome-harness |
| Observe (trajectory) | none | PostToolUse JSONL (Imp 2, prereq for Imp 1) | OpenHands event stream |
| Remember | best design, dedup bug | dedup + evidence-in-repo (Imp 4) | — |
| Repo-context / ACI | efficiency-only | subsumed by Imp 3 | Aider |
| Act / Collaborate / Runtime | adequate / folds into Control | no new work | — |
| Control (design) | strong + eval-proven to fire | hold; do NOT add teaching prose | — (anti-goal) |

---

## Recommended order

1. **Improvement 1 — defect-replay outcome eval** (with a minimal slice of Imp 2's trajectory log to enable attribution). Answers the question, directs all other investment.
2. **Improvement 2 — execution-Control floor** (completeness-plan Items 1+2). Highest safety; the one structural axis gap.
3. **Improvement 3 — architecture-lint**, on the drift classes the outcome eval proves worth automating.
4. **Improvement 4 — hygiene**, folded in opportunistically.

## What this plan deliberately does NOT do

- No new teaching skills, no prose expansion of skills the eval showed baseline already follows. The harness gets *leaner*, not bigger.
- Does not restate completeness-plan Items 1–4 — references them.
- Does not chase Act / Runtime / Collaborate to framework parity — out of scope for this shop's scale (see completeness plan framing).

## Key sources

- `harnessed-development-workspace/iteration-1/` — the fidelity eval this plan reacts to
- SWE-bench — outcome measurement (Imp 1) ; SWE-agent ACI — interface-as-enforcement (Imp 3)
- OpenAI Codex / `ai-boost/awesome-harness-engineering` — pre-action authorization (Imp 2)
- OpenHands — event-stream trajectory observability (Imp 2)
- `netdust-wp/skills/*/lessons.md` (esp. `ntdst-architecture`, `ntdst-data`) — the labeled defect dataset for Imp 1 and the fingerprints for Imp 3 (WordPress-stack — see Imp 1's scope consequence)
