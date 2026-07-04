# The harness as a loop that runs until finished

**Date:** 2026-07-04
**Status:** Phases 1–2 IMPLEMENTED 2026-07-04 (agent 0.4.0) — see execution record at
bottom. Phase 3 (eval on a real feature) pending. Stop-hook driver chosen for v1
(remote-first, ~zero token overhead); csd stays a documented alternative, not built.
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

**Alternative driver — obra/claude-session-driver (`csd`).** Jesse's session-driver
plugin (v3.0.0, 2026-05-18) lets one Claude Code session launch and supervise other
full sessions as tmux workers (`csd launch` / `converse` / `read-events` /
`wait-for-turn` / `handoff`). That is an *externalized* M2: a controller session loops
"launch worker for next cluster → wait-for-turn → run `loop-check.py` → iterate until
exit 0," with no Stop-hook needed. Trade-offs vs. the Stop-hook gate:

- csd workers are full sessions — own context window, own compaction, own hooks, and
  `handoff` gives a native answer to `[HUMAN]` yields (hand the worker's tmux session
  to Stefan, resume after). The Stop-hook gate needs none of tmux/Node and works in a
  single session, including remote/headless ones.
- **Guard implication:** csd workers run with permissions bypassed, so the PreToolUse
  guard's `ask` has no human to ask — under a csd driver, the destructive-command
  denylist must escalate from `ask` to `deny` for worker sessions (exactly the case
  `pretooluse-guard.py` v1 reserved `deny` for).
- Both drivers consume the same M1 ledger. Build `loop-check.py` first and the choice
  of driver stays open — Stop-hook for single-session/remote, csd for a local
  controller supervising parallel workers (and it maps 1:1 onto the plan/build split:
  controller = planner, workers = builders).

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

**v1 scope:** Class A/B features with the spec-kit graft installed, only. `loop-check.py`
needs deterministic artifacts (`tasks.md` checkboxes, `[GATE]` sections) to derive
FINISHED from; a non-graft plan has no machine-readable task ledger. Class C/D/E are
single cycles — there is nothing to loop. Arming the loop on anything else is a
`/loop-arm` refusal, not a degraded mode.

## 4. Does the planner need to know it's in a loop?

**No — and keeping it that way is load-bearing.** The whole seam design says the plan
artifact is execution-mode-agnostic: spec-kit owns spec→plan→tasks, and whoever drives
the build (interactive session or armed loop) consumes the same `tasks.md`. A "loop mode"
in the planner would couple planning to execution shape and fork the artifact.

**But the loop raises the stakes on plan quality it cannot fix at runtime.** In an
interactive session, an ambiguous task gets resolved by asking mid-course; in a loop it
becomes a BLOCKED yield at best and rationalized completion at worst. So the plan's
*content* needs two additions — both useful even without the loop:

- **4a. Explicit human-yield markers.** Any step that inherently needs a human — a
  destructive-migration approval, credentials, a deploy confirmation, the shake-out
  manifest sign-off — gets a `[HUMAN]` marker in `tasks.md` at plan time. The loop
  treats `[HUMAN]` as a *planned* BLOCKED: it yields there with the specific question
  instead of discovering mid-iteration that it is stuck. `── REVIEW GATE ──` markers
  stay agent-driven (the loop runs the tiered review itself); `[HUMAN]` is only for
  steps no agent may take alone. Lands in `tasks-template.md` + `planner.md`;
  `loop-check.py` treats an unpassed `[HUMAN]` as exit 2.
- **4b. Planner proposes the iteration budget.** `max_iterations` defaults are dumb;
  the planner knows the task count, cluster count, and expected review rounds. One line
  in the plan (`Loop budget: ~N iterations`) that `/loop-arm` reads instead of a global
  default. Keeps the runaway guard calibrated to the actual feature size.

Everything else the loop needs from a plan — machine-checkable per-task exit criteria
(1d test expectations, `[Tier A|B]` markers), small atomic tasks, explicit dependencies
(`[P]`), sized clusters (1f) — **the gates already demand.** The loop doesn't add new
planning requirements; it removes the human safety net that made skipping them
survivable. `gate-check.py` staying green at Stage 1.5 is precisely what makes a plan
loop-safe.

One runtime rule completes the picture: a mid-loop *plan defect* has two shapes. Drift
caught at Step 2.5 → plan-correction commit, loop continues (exists today). Architecture
wrong → shake-out's abort-and-replan path fires → the loop **disarms and yields**;
re-planning is never driven by an unattended loop.

## 5. Failure modes this design must not introduce

- **Rationalized completion** — the loop pressures the agent to *look* finished. Defense:
  FINISHED is exit codes only (M1); the hook never reads prose.
- **Infinite/dry spin** — max-iterations + dry-iteration counter + BLOCKED-yields (M2).
- **Gate erosion under loop pressure** — an iteration must still HALT at review-gate
  markers; the loop drives *through* the gates, never around them. `loop-check.py`
  counts an unreviewed cluster as not-finished.
- **Human locked out** — marker delete always disarms; BLOCKED always yields with a
  question; the PreToolUse guard still `ask`s on destructive commands mid-loop.

## 6. Phasing

Each phase ships with its own tests and an execution record (same discipline as the
2026-07-03 phase plans), and is built *through* the harness, not around it.

1. **Phase 1 — `loop-check.py` + the plan-side contract (M1 + §4).** The ledger
   checker, deterministic, tested like `gate-check.py` — plus the two plan-content
   additions it must read: `[HUMAN]` markers in `tasks-template.md` + `planner.md`
   (4a) and the `Loop budget:` line (4b). These belong together: shipping the checker
   without the markers hard-codes "no human steps exist," and retrofitting markers
   later re-opens plans the checker already judged. Valuable standalone: `/shakeout`
   and `/evaluate` can call `loop-check.py` immediately, loop or no loop.
2. **Phase 2 — Stop-hook loop gate + marker + `/loop-arm` (M2), WITH the re-entry
   protocol text (M3).** These two are coupled and land together: a loop gate without
   the rebuild-from-disk rule produces loops that die of compaction mid-feature — the
   hook forces continuation into a session that no longer knows where it is. Includes:
   the graft-only/Class-A-B arming refusal, disarm-on-abort-and-replan, `[HUMAN]` →
   yield-with-question, and tests mirroring the `subagent-stop.py` suite
   (block/pass/bypass/disarm/dry-spin/budget-exhausted). The protocol text goes into
   `harnessed-development` Stage 2 — or into the `building` half if the plan/build
   split lands first; this loop is that split's natural driver and strengthens the
   case for executing it.
3. **Phase 3 — eval.** Run a real feature with the loop armed; measure iterations to
   FINISHED, dry iterations, yields at planned vs. unplanned points, gates fired vs.
   warranted. Feeds the outcome-eval frontier.

## 7. Answers, in one breath

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

---

## Execution record (2026-07-04, agent 0.4.0)

Shipped lean — 2 new scripts, 1 command, 1 hook registration, 4 small doc/template
touches, 2 test modules. Deliberately NOT built: csd integration, any orchestrator
skill/agent, Mode D scheduling, manifest parsing (Stage 3 stays attended), suite-running
inside loop-check (the per-task subagent-stop hook already forces tests to run).

- `spec-kit/loop-check.py` — the ledger. Artifact-only FINISHED/CONTINUE/BLOCKED
  (exit 0/1/2) from `tasks.md` + a `gate-check.py` subprocess; skips fenced examples;
  emits a `progress: done=N total=M` line for dry detection. Stage 3 is out of loop
  scope by design (human-judgment phase) — FINISHED means "Stage 2 complete, disarm,
  run /shakeout attended."
- `hooks/loop-gate.py` + `hooks.json` Stop registration (before session-stop.py) —
  the driver. No marker → silent no-op. Armed: FINISHED disarms; BLOCKED yields with
  the marker kept; CONTINUE blocks the stop with the next unit. Guardrails all in:
  stop_hook_active bypass, max_iterations budget, 2-strike dry-loop disarm,
  marker-delete abort, fail-open.
- `commands/loop.md` — /loop arm (graft + Class A/B + gate-check-green preconditions,
  budget from the plan's `Loop budget:` line, marker gitignored) · /loop off ·
  /loop status.
- Plan-side contract (§4): `[HUMAN]` marker rule in `tasks-template.md` (hard rule 4),
  `Loop budget:` line in `plan-template.md`, planner.md step 7b (planner stays
  loop-agnostic; plan becomes loop-auditable).
- `harnessed-development` Stage 2: 8-line armed-loop note (thin scheduler,
  rebuild-from-disk on re-entry, gates unchanged, loop ends at Stage 2).
- Drive-by fix: `gate-check.py` now strips fenced code blocks before parsing task
  lines — previously a fenced `- [ ] Tnn` example (which the shipped template carries)
  counted as a real task and failed the tier check.
- Tests: `test_loop_check.py` (8 cases) + `test_loop_gate.py` (10 cases); full suite
  13 modules / 158 cases green.

Remote note: on a disposable remote runner the PreToolUse guard's `ask` degrading is
acceptable (repo-scoped box, no prod creds); the ask→deny escalation remains reserved
for csd-style local workers only.
