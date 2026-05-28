# netdust-core — eval runner

Eval infrastructure for measuring whether the wp-* / ntdst-* harness skills change agent behavior on Stride-shaped tasks.

## Why

Per the 2026-05-17 audit: the harness has 24 skills across 3 plugins. Some have RED tests; none have ever been measured for whether they actually change code output vs. a Sonnet baseline. The eval here closes that gap.

Source-of-truth files:
- **Rubric:** `~/Sites/netdust-wp-manager/tasks/eval-rubric.md` (55 rules, 51 canonical)
- **Scenarios:** `~/Sites/netdust-wp-manager/tasks/eval-scenarios.md` (8 distinct prompts)
- **Plan:** `~/Sites/netdust-wp-manager/tasks/harness-improvement-plan.md` (Tier 1 task 1.5)

## Architecture (hybrid: Python helper + Claude orchestrator)

The Agent tool (subagent dispatch) only exists inside a Claude Code session. A pure Python script can't dispatch subagents. So:

- **Python helper** does the deterministic work: parse rubric + scenarios, build per-scenario prompts, score judge outputs against rule lists, write the eval log.
- **Claude orchestrator** (the running session) does the subagent dispatch: 8 baseline + 8 skill-on + 8 judge runs, paste each output into a known path.

## Flow

```
1. Run:  python3 run-eval.py --prepare
        → Writes prompts/scenario-{N}-{baseline|skill-on|judge}.md

2. Claude orchestrator (per scenario, can parallelize across scenarios):
   a. cat prompts/scenario-1-baseline.md → dispatch Agent → paste to outputs/scenario-1-baseline.md
   b. cat prompts/scenario-1-skill-on.md → dispatch Agent → paste to outputs/scenario-1-skill-on.md
   c. cat prompts/scenario-1-judge.md → dispatch Agent (with both outputs included) → paste to outputs/scenario-1-judge.md

3. Run:  python3 run-eval.py --score
        → Reads outputs/, parses judge scoring, writes ../../../Sites/netdust-wp-manager/tasks/eval-log.md
```

## Files

| File | Purpose |
|---|---|
| `run-eval.py` | The helper. Two modes: `--prepare` (writes prompts) and `--score` (parses outputs, writes log). |
| `prompts/` | Generated. One file per agent dispatch (24 expected). |
| `outputs/` | Orchestrator writes here. One file per agent output (24 expected). |
| `README.md` | This file. |

## Rerunning

`run-eval.py --prepare` is idempotent — re-running overwrites `prompts/` (in case rubric or scenarios change).

`--score` reads whatever's in `outputs/` and writes a fresh `eval-log.md` (with a timestamp header so old runs aren't lost — appends, doesn't overwrite).

## What this doesn't do

- **No automatic subagent dispatch.** That's the orchestrator's job — see Flow above.
- **No retries.** If a subagent fails or returns garbage, the orchestrator re-dispatches manually and re-pastes.
- **No automatic skill-disable enforcement.** The baseline prompt includes explicit "do not load any harness skill" instructions, but the orchestrator must verify by checking the agent's behavior. We accept the risk of contamination because the alternative (a separate eval environment) is way more work.
- **Not a test runner.** Tests live at `~/.claude/plugins/netdust-core/tests/`. This is eval infrastructure — different goal.
