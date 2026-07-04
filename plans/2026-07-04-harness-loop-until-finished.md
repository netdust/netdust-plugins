# The harness as a loop that runs until finished

**Date:** 2026-07-04
**Status:** PLAN ONLY — no implementation yet
**Origin:** Stefan: "I want the harness to become a loop that runs until finished. Is that
possible, what does it mean? More subagents to protect context?"

---

## 1. What "loop until finished" actually means

Today `harnessed-development` is a **sequencer executed inside one conversation**. It
fires the right gates in the right order — but the *drive* comes from the conversation
itself. The run ends whenever the model decides to stop, the session ends, or context
compacts. Nothing outside the conversation asserts "the feature is not finished — keep
going." A session can end mid-feature with red tests and open tasks, and the harness
does not object (the course-eval already names this: no session-boundary gates, L06+L12).

A loop-until-finished harness adds three things the sequencer lacks:

1. **A machine-readable definition of FINISHED** — derived from command exit codes,
   never from the agent asserting "done" (course-eval L08).
2. **A driver that re-enters** — something outside the model's own volition that says
   "not finished → continue with the next unit of work."
3. **State that lives on disk, not in the context window** — so the loop survives
   compaction, session restarts, and (with Mode D below) machine restarts.

The good news: **the harness is already ~70% of a loop.** It has the work queue
(`tasks.md`), disposable per-task workers (implementer subagents), a blocking gate at
worker close (`subagent-stop.py`), a machine gate at the plan→build seam
(`gate-check.py`), and cross-session memory (the Stop/SessionStart round-trip). What is
missing is the *outer* loop: the ledger, the re-entry driver, and the re-entry protocol.

## 2. The three missing mechanisms

### M1 — The feature ledger (machine-readable FINISHED)

A deterministic checker, sibling to `gate-check.py`:

    spec-kit/loop-check.py <feature-dir>   # exit 0 = FINISHED, 1 = not finished, 2 = BLOCKED

FINISHED is a conjunction, every clause derived from an artifact or an exit code:

- every `- [ ] Tnn` in `tasks.md` is checked, **and** each checked task's commit body
  carries the Test-evidence block (greppable, same trick as `gate-check.py`);
- the project's test suite exits 0 (run it — do not read a STATUS block);
- `gate-check.py` exits 0;
- at spec-close: `tasks/shake-out-manifest.md` exists with zero unresolved CRITICAL/IMPORTANT;
- no task is marked `BLOCKED`/`NEEDS_CONTEXT` (that's exit 2 — the loop must *stop and
  ask*, not spin).

This closes the "done is agent-asserted" gap independently of the loop — it is worth
building even if nothing else in this plan ships.

### M2 — The Stop-hook loop gate (the re-entry driver)

The exact mechanism that already works at subagent level, lifted to the session:
a **Stop hook can block the main agent's stop** the same way `subagent-stop.py` blocks
a subagent's. New hook logic (extend `session-stop.py` or add `loop-gate.py` before it):

- The loop is **armed explicitly** by a marker file `tasks/.harness-loop.json`:
  `{feature, mode, iteration, max_iterations, armed_by}`. No marker → hook is a no-op
  (today's behavior). Arming happens via a `/loop-arm <feature>` command or a
  harnessed-development Stage-2 offer — never implicitly.
- On Stop with an armed marker: run `loop-check.py`.
  - exit 0 (FINISHED) → disarm marker, allow stop, memory capture proceeds.
  - exit 2 (BLOCKED) → allow stop, but inject the blocking question into the final
    message context. A loop that needs human input must *surface it and yield*, not spin.
  - exit 1 (not finished) → `{"decision": "block", "reason": "<next unit from tasks.md>,
    iteration N of MAX"}` — the session continues with the next task.
- **Guardrails (all mandatory):**
  - `stop_hook_active` bypass (same one-block-per-cycle rule as `subagent-stop.py`);
  - `max_iterations` in the marker (default ~25); exceeded → disarm, stop, report;
  - a **dry-iteration counter**: if an iteration closes zero new tasks twice in a row,
    disarm and stop — that is a stuck loop, not progress;
  - human abort: deleting the marker (or `.no-loop` in the project) always wins;
  - the hook stays fail-open — any internal error allows the stop.

### M3 — The thin-orchestrator re-entry protocol (context protection)

This is the honest answer to "more subagents to protect context?": **not more subagents —
stricter roles for the ones already there, plus a rebuild-from-disk rule.**

- Stage 2 already dispatches one implementer per task and forbids the controller from
  doing pre-flight exploration (`<extremely_important>`). The loop hardens this into a
  protocol: the orchestrator context holds **only** scheduling state, and each iteration is
  read ledger → pick next unit → dispatch subagent → verify by exit code → update ledger.
  All heavy context (source reading, implementing, reviewing, sweeping) burns in
  disposable subagent windows that return structured blocks and die.
- **Compaction-invariance rule** (new text in `harnessed-development` Stage 2): the
  orchestrator must be able to rebuild its entire working state from disk —
  `tasks.md` + `loop-check.py` output + the plan + `memory/STATE.md` — and must never
  depend on conversation memory for loop position. After a compaction or a fresh
  session, "where was I?" is answered by the ledger, not by scrollback. (This also
  discharges the outstanding compaction-invariant doc item from the 2026-06-07 plan.)
- Budget intuition: an orchestrator that only schedules spends a few hundred tokens per
  iteration on decisions; a 20-task feature fits in one session-context comfortably.
  Without the discipline, task residue accumulates in the main window and the loop dies
  of compaction mid-feature — that, not subagent count, is the real context risk.

## 3. Loop granularities (what "one iteration" is)

| Loop | Unit | Driver | Status |
|---|---|---|---|
| Inner | one task (TDD cycle) | `subagent-stop.py` | EXISTS |
| Cluster | ~3–4 tasks → `── REVIEW GATE ──` | sequencer Step 2.8 | EXISTS (prose) |
| **Outer** | **feature: loop clusters until ledger says FINISHED** | **M2 Stop-hook gate** | **NEW** |
| Cross-session (Mode D, optional) | one session per firing | remote trigger / scheduled resume re-arms the session until FINISHED | LATER — only for remote/headless runs; M1–M3 must exist first |

## 4. Failure modes this design must not introduce

- **Rationalized completion** — the loop pressures the agent to *look* finished. Defense:
  FINISHED is exit codes only (M1); the hook never reads prose.
- **Infinite/dry spin** — max-iterations + dry-iteration counter + BLOCKED-yields (M2).
- **Gate erosion under loop pressure** — an iteration must still HALT at review-gate
  markers; the loop drives *through* the gates, never around them. `loop-check.py`
  counts an unreviewed cluster as not-finished.
- **Human locked out** — marker delete always disarms; BLOCKED always yields with a
  question; the PreToolUse guard still `ask`s on destructive commands mid-loop.

## 5. Phasing

1. **Phase 1 — `loop-check.py` (M1).** Deterministic, tested like `gate-check.py`.
   Valuable standalone: `/shakeout` and `/evaluate` can call it immediately.
2. **Phase 2 — Stop-hook loop gate + marker + `/loop-arm` (M2).** Tests mirror the
   `subagent-stop.py` suite (block/pass/bypass/disarm/dry-spin).
3. **Phase 3 — orchestrator protocol text (M3).** Stage-2 additions to
   `harnessed-development` (or to the `building` half if the plan/build split lands
   first — this loop is the natural driver for that split's build side and strengthens
   the case for executing it).
4. **Phase 4 — eval.** Run a real feature with the loop armed; measure iterations to
   FINISHED, dry iterations, gates fired vs. warranted. Feeds the outcome-eval frontier.

## 6. Answers, in one breath

**Is it possible?** Yes — the enforcement primitive (a Stop hook that blocks and says
"keep going") is the same one `subagent-stop.py` already uses in production, one level up.

**What does it mean?** Finished becomes a *derived fact* (exit codes over artifacts), the
session cannot end while an armed feature is unfinished-and-unblocked, and the harness
drives itself cluster by cluster to that fact instead of relying on conversational
momentum.

**More subagents to protect context?** Same subagents, harder boundary: the main window
becomes a thin scheduler that can be rebuilt from disk at any moment; every heavy read or
write happens in a disposable worker. Context is protected by *where state lives* (disk
ledger, not scrollback), not by worker count.
