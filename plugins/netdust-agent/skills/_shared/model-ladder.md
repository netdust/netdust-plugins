# The model ladder — which model does each dispatch

**The single home of the ladder.** `building` and the commands cite this file at every
dispatch site and never restate the table. Agent files under `agents/` carry the
persona's DEFAULT in their `model:` frontmatter; the controller passes the ladder's
model on the dispatch itself where the lane says so, and per Claude Code's contract the
dispatch parameter wins over the file (then `CLAUDE_CODE_SUBAGENT_MODEL`, then the main
model). Aliases: `haiku` / `sonnet` / `opus` / `inherit` (`inherit` = the main session's
model, which is the operator's call and never set here).

## The table

| Dispatch | Behaviour lane | Contract lane |
|---|---|---|
| ground-truth read — signatures, a framework fact, "does X accept Y" (an Explore-type agent, read-only) | haiku | haiku |
| the cluster RED — the one behaviour test from `Observable:` | sonnet | — (per-task, below) |
| `implementer` | sonnet | inherit |
| `test-author` — split RED before the implementer | — | inherit |
| `test-author` — feature tests after a cluster | — (the cluster RED IS the feature test) | sonnet |
| `reviewer` — LIGHT / the branch review of an all-behaviour branch | sonnet | sonnet at LIGHT, inherit at STANDARD and FULL |
| `code-simplicity-reviewer` | not dispatched | sonnet |
| `security-sentinel`, `invariant-auditor` | not dispatched | inherit |
| `shakeout-qa` — drives the acceptance matrix | sonnet | sonnet |
| `convergence` read, session-review pane | sonnet | sonnet |

## The one override

**A dispatch that edits a path matching `bin/sensitive-globs.txt` (or the project's
`.claude/sensitive-globs.txt`) runs at `inherit`, whatever the lane says.** The
sensitive-path floor in `hooks/subagent-stop.py` already refuses a solo close on such a
path; the ladder never puts a smaller model in front of that floor.

## What this is and is not

- It is a ROUTING table for the controller: read the lane from `tasks.md`, look up the
  row, pass `model=` on the dispatch. Nothing here is a judgment of what a model can do
  in general — it is what each harness moment needs, priced by what a mistake costs
  there (the lane already priced that).
- It is MEASURED, not enforced. `bin/run-cost.py` prints a `── per-model ──` block per
  run; that is how a wrong row shows up. Whether a PreToolUse hook can see the dispatch
  `model` is not documented, so there is deliberately no hook that refuses a dispatch by
  model — a rule the machine cannot check would be one more echoed field.
- Raising a row is always allowed and never needs a plan change; lowering one below the
  table does, in a plan-correction commit, the same way stakes move.
