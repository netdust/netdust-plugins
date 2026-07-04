# Handoff — 2026-07-04 session (harness lifecycle audit → loop → calibration rule)

**Merged to main:** agent **0.4.1** · core 0.2.6 · wp 0.4.1 · statamic 0.1.1.
Full suite green: 13 modules / 158 cases (`plugins/netdust-agent/tests/run.sh`).

## What this session shipped (three commits' worth of behavior)

1. **Lifecycle drift fixes (0.3.5)** — full-harness audit, then: feature-acceptance gate
   label unified to **1g** everywhere; shake-out SKILL synced with its wrappers
   (test-effectiveness + feature-acceptance steps, `superpowers-chrome` `use_browser`);
   CLAUDE.md phantom-skill list corrected; constitution provenance fixed in
   plan-template; push-to-main guard no longer trips on `feature/main-*` branches;
   dashboard-sync path env-overridable (`NETDUST_DASHBOARD_SYNC`).
2. **The Stage-2 loop (0.4.0)** — `spec-kit/loop-check.py` (ledger: FINISHED derived
   from tasks.md + gate-check, exit 0/1/2), `hooks/loop-gate.py` (Stop hook blocks
   session stop while armed and unfinished; disarms on FINISHED / budget / 2-strike
   dry-loop; yields on `[HUMAN]`), `/loop` command (arm/off/status), `[HUMAN]` marker
   + `Loop budget:` in templates + planner 7b. Design + decisions:
   `plans/2026-07-04-harness-loop-until-finished.md` (execution record at bottom).
   Drive-by: gate-check.py now strips fenced code blocks (a fenced task example
   previously failed the tier check).
3. **Calibration rule (0.4.1)** — `skills/_shared/calibrations.md` (index of ~24
   incidents: slug → one-line lesson → canonical home); long duplicate retellings
   trimmed to slug cites; CLAUDE.md rule: *a war story has one full home, everywhere
   else cites the slug; new prose never retells.*

## First actions on Stefan's machine (not doable from remote)

- **Update the plugins** (marketplace → agent 0.4.1) so the loop hooks are live.
- **Check superpowers version** — latest upstream is **v6.1.1** (2026-07-02). If a
  major jump, run `/skill-audit` once to confirm all `superpowers:*` names the harness
  pins still resolve. Note v6.0.3 moved SDD scratch files to `.superpowers/sdd/`.
- Optional, decided this session in principle: install **private-journal-mcp** as the
  *recall* (pull) layer beside the deterministic tag-capture (push) layer. Rule adopted:
  **own what encodes discipline (ledger, gates, templates, tag capture); rent transport
  and recall (session driving, semantic memory, base skills).** csd stays on the
  watchlist — adopt only when parallel workers are actually wanted; both loop drivers
  consume the same ledger, so no rework either way.

## Next session priorities (in order)

1. **The plan/build split** — the one big open architecture decision, now *more*
   valuable because the building half is the natural owner of the loop protocol.
   Stefan must pick the shape: the 3 options are in
   `plugins/netdust-agent/docs/plan-build-split-handoff.md` (status OPEN). Constraints
   established this session: harnessed-development is at gate capacity (1a–1h) — the
   split should *merge* gates where possible (1d/1f/1h are all "shape the task list"),
   never add; the `tasks.md` + gate-check seam already exists and is loop-consumed, so
   the split formalizes a boundary that is now real. Run this WITH Stefan present.
2. **Loop Phase 3 — eval on a real feature.** Arm `/loop` on the next genuine Class-A
   feature (not synthetic). Measure: iterations to FINISHED, dry stops, yields at
   planned (`[HUMAN]`) vs unplanned points, gates fired vs warranted. Criteria in
   `plans/2026-07-04-harness-loop-until-finished.md` §6 Phase 3. Also the first live
   test of the tmux always-stopping fix.
3. **Carried open items** (unchanged priority, do not let them silently rot):
   outcome eval / defect-replay (the "highest leverage" gap per
   `netdust-core/docs/harness-engineering-course-eval.md`); repo-level
   `ARCHITECTURE-INVARIANTS.md` still unwritten; `pattern-miner` agent/core copy drift;
   stale "PARKED" header on `harness-engineering-hardening-plan.md`. Note: the old
   "no session-boundary gates" gap is now PARTIALLY closed — loop-gate covers
   "session ends mid-feature" *when armed*; an unarmed session still ends silently.

## Context to load next session

- `plans/2026-07-04-harness-loop-until-finished.md` — loop design + execution record
- `plugins/netdust-agent/docs/plan-build-split-handoff.md` — the split options
- `plugins/netdust-agent/skills/_shared/calibrations.md` — cite slugs, don't retell
- This session's verdict on bloat, for the split's guiding line: architecture lean
  (lazy loading, clean seams, honest enforcement ladder), fat was in prose duplication
  (now ruled) and the god-skill (the split fixes it). New gates must replace or merge,
  never append. New code follows the loop pattern: small deterministic checker + thin
  hook.
