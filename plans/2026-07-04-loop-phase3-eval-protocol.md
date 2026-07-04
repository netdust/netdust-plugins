# Loop Phase 3 — eval protocol (armed run on a genuine Class-A feature)

**Status:** READY — seam artifact green, awaiting Stefan's approval + the armed run on his machine
**Target feature:** `specs/run-observability/` (in-loop trace + evaluator rubric — course-eval fix #4, the carried "highest leverage" item)
**Criteria source:** `plans/2026-07-04-harness-loop-until-finished.md` §6 Phase 3
**Branch:** `claude/handoff-split-god-skill-ueb1kd`

The scorecard below is written BEFORE the run — criteria before execution, same discipline
as every gate. The recursion is deliberate: the feature being built IS the instrument that
will grade runs like this one; from T02 onward the run partially records itself, and the
finished T04 rubric can be pointed back at this run's own log as its first real input.

---

## 1. Why this split of environments (recorded honestly)

The remote session that produced the seam artifact has **no plugin install** — no
`~/.claude/plugins/netdust-agent`, therefore no Stop-hook `loop-gate.py`, therefore the
armed loop cannot drive it, and the tmux always-stopping fix cannot be observed there.
So: **PLAN spine ran remotely to the seam; the armed BUILD run happens on Stefan's
machine** where the hooks are live. This is not a workaround — it is the seam working as
designed (the artifact crosses machines; the assertion doesn't have to).

Environment degradations during the remote PLAN run (for the eval record):
- spec-kit CLI not initialized (`SKIP_SPECIFY_INIT=1`, documented path) — `spec.md` was
  authored directly from the override template; the `/speckit.clarify` questioning loop was
  replaced by explicit Q→A entries under Clarifications. `gate-check.py` verified the result
  mechanically (PASS), so the seam's guarantee is intact.
- `superpowers:*` upstream skills not loadable remotely — the spine's stages were followed
  from the repo's own SKILL.md files. Worth watching: whether plan quality suffered
  (Class B freshness review on Stefan's machine is the natural check — see step 2).

## 2. Preconditions on Stefan's machine (in order)

1. **Update plugins** — marketplace → netdust-agent **0.5.0** (the plan/build split; the
   loop hooks were already live since 0.4.0). Restart the session so hooks re-register.
2. **Pull the branch** `claude/handoff-split-god-skill-ueb1kd` in the netdust-plugins repo.
3. **The seam, properly:** read `specs/run-observability/{spec,plan,tasks}.md` and
   approve (or amend — any amendment re-runs `gate-check.py`). This doubles as the
   Class-B freshness review of a remotely-authored plan — the first live test of that mode.
4. **Arm:** `/loop specs/run-observability` — the command re-checks graft + Class A/B +
   gate-check green, reads `Loop budget: ~12`, writes the gitignored marker.
5. **Run:** invoke the harness ("execute the plan" → routes to `building`). `building`'s
   precondition re-runs gate-check itself — expect and verify that it does (measurement M7).
6. Work in tmux as usual — this run is the first live test of the tmux always-stopping fix.

## 3. Scorecard (fill during/after the run)

| # | Measurement | Prediction (pre-run) | Actual |
|---|---|---|---|
| M1 | Iterations to FINISHED (budget 12) | 7–10 (7 tasks + 2 review-gate iterations) | |
| M2 | Dry iterations (no progress-delta) | 0–1 | |
| M3 | Planned yields (`[HUMAN]` tasks) | 0 — the plan honestly has none; the yield path goes unexercised this run (noted, not fabricated) | |
| M4 | Unplanned yields (BLOCKED off-plan) | 0 | |
| M5 | Budget/dry disarms | 0 | |
| M6 | Gates fired vs warranted | warranted: 2 review-gate HALTs (C1, C2 — both STANDARD), 7/7 tasks with Test-evidence blocks (5× Tier B `no unit test` lines are correct per tier), standards `n/a — no linter`, subagent-stop backstop fires 0 times | |
| M7 | Seam behavior | `building` re-runs gate-check at entry (exit 0) before any dispatch; refuses if artifacts were amended without re-check | |
| M8 | Loop drives THROUGH gates, not around | execution HALTs at both `── REVIEW GATE ──` markers even while armed | |
| M9 | tmux always-stopping fix | session no longer stops after every tool batch; loop-gate blocks stops only at real stop events | |
| M10 | Re-entry protocol | after any compaction/re-entry, controller rebuilds from tasks.md + plan (thin scheduler), not scrollback | |

Success (from §6 Phase 3 + the 2026-07-04 handoff): FINISHED within budget, zero
gate erosion (M8), yields only where planned (M3/M4), and the measurements themselves
recorded — feeding the outcome-eval frontier. A failed prediction is a finding, not a
failure of the eval.

## 4. After the run

1. `/loop status` output + the scorecard above → fill the Actual column (edit this file).
2. Stage 3 runs **attended** (loop disarms at FINISHED by design): test-effectiveness →
   feature-acceptance (N/A — no UI; the acceptance criteria's Tier-A tests + the dogfood
   run itself are the drive) → `/shakeout` → finish. From T05 onward `/shakeout` will
   surface the rubric — point it at this feature's own run-log as its first real input.
3. `/evaluate` on the sub-phase; its retro cites this scorecard.
4. Record the verdict here (append an "Execution record" section, same convention as the
   loop plan) and update `plans/2026-07-04-handoff-next-session.md` item 2.

## 5. Abort criteria

Disarm (`/loop off`) and stop the eval if: the loop grinds a defective plan (gate-check
red mid-run after an amendment), any gate is skipped while armed (M8 violation — that is
a Phase-2 bug, file it before continuing), or the marker has to be hand-edited to keep
the loop alive (ledger bug — same).
