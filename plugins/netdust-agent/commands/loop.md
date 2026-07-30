---
description: Arm the Stage-2 harness loop — the Stop-hook loop gate then drives execution through tasks.md unattended until every task is done, a [HUMAN] task yields, or the iteration budget runs out. Usage — /loop <feature-dir> (arm) · /loop off (disarm) · /loop status
allowed_tools: ["Bash", "Read", "Write"]
---

Arm, disarm, or inspect the harness loop for one feature. The loop is
the `loop-gate.py` Stop hook consuming `bin/loop-check.py` (the ledger):
while armed, the session cannot stop with unfinished non-`[HUMAN]` tasks — the
gate blocks the stop and names the next unit. FINISHED is derived from
artifacts, never from your own assertion.

## /loop <feature-dir>  (arm)

Preconditions — refuse to arm (say why) if any fails:

1. **Graft + artifacts:** `<feature-dir>/tasks.md` exists with `- [ ] Tnn` lines.
   No graft → no machine-readable ledger → no loop.
2. **Class A/B only.** C/D/E are single cycles; nothing to loop.
3. **Stage 1.5 green:** run `python3 <plugin>/bin/gate-check.py <feature-dir>`
   — exit 0 required. A loop on a gate-failing plan grinds a defective plan.

Then:

4. Read `Loop budget: ~N` from `<feature-dir>/plan.md` (planner-proposed);
   default 25 if absent.
5. Write `tasks/.harness-loop.json`:
   `{"feature_dir": "<feature-dir>", "iteration": 0, "max_iterations": N,
   "last_done": <current checked count>, "dry": 0}`
6. Ensure `.gitignore` contains `tasks/.harness-loop.json` (runtime state,
   never committed — same treatment as the stop-hook sidecar).
7. Emit `python3 <plugin>/bin/run-trace.py append <feature-dir> loop-armed budget=<N>`.
8. Confirm to the user in two lines: armed, budget, and how the loop ends
   (FINISHED → disarms, Stage 3 runs attended · `[HUMAN]` task → yields with
   the question · budget/dry-loop → disarms · `/loop off` anytime).

Then start (or continue) `building` Stage 2 normally. Nothing
else changes: review-gate HALTs, tiers, and the subagent-stop backstop all
still apply — the loop drives *through* the gates, never around them.

## /loop off  (disarm)

Emit `python3 <plugin>/bin/run-trace.py append <feature-dir> loop-disarmed reason=manual`
(feature dir from the marker), then delete `tasks/.harness-loop.json`. Confirm
in one line.

## /loop status

Run `python3 <plugin>/bin/loop-check.py <feature-dir>` (feature dir from
the marker) and report: armed/disarmed, iteration/budget, and the ledger's
verdict line verbatim.

Resolve `<plugin>` via the stable symlink `~/.claude/plugins/netdust-agent/`.
