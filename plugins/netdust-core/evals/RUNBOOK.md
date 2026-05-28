# Eval runbook — task 1.6 orchestration

_This document is the step-by-step workflow Claude (the orchestrator) follows when running the full eval pass. Estimated runtime: 45–60 min._

## Pre-flight

1. Confirm rubric + scenarios are current:
   ```bash
   ls -la ~/Sites/netdust-wp-manager/tasks/eval-rubric.md ~/Sites/netdust-wp-manager/tasks/eval-scenarios.md
   ```
2. Confirm helper is healthy and prompts are fresh:
   ```bash
   python3 ~/.claude/plugins/netdust-core/evals/run-eval.py --prepare
   ```
   Expected output: `Parsed 55 rules, 8 scenarios. Wrote 24 files to .../prompts/`

## Phase 1 — Generations (8 scenarios × 2 legs = 16 subagent dispatches)

For each scenario id in `1, 2a, 2b, 3, 4, 5, 6, 7`:

### Baseline leg

1. Read the prompt:
   ```bash
   cat ~/.claude/plugins/netdust-core/evals/prompts/scenario-<id>-baseline.md
   ```
2. Dispatch via Agent tool with `subagent_type: general-purpose`. Pass the prompt verbatim as the agent's task.
3. Wait for the agent's response. Save it verbatim to:
   ```
   ~/.claude/plugins/netdust-core/evals/outputs/scenario-<id>-baseline.md
   ```

### Skill-on leg

Same steps, but use `prompts/scenario-<id>-skill-on.md` → `outputs/scenario-<id>-skill-on.md`.

### Parallelization

Baseline and skill-on legs for the **same scenario** can be dispatched in parallel (single message, two Agent tool calls). Going across scenarios in the same batch is fine if context budget allows — generations are independent. Recommended: dispatch 4 scenarios at a time (8 parallel subagent calls), then move to phase 2 for those before dispatching the next 4.

### Anti-contamination checks

After each baseline response:
- Did the agent invoke the Skill tool? If yes, the leg is contaminated — rerun.
- Did the agent read from `~/.claude/plugins/` or `~/Sites/stride/`? If yes, rerun.
- The agent's response should be code + brief commentary, ≤600 words. If it's longer, that's a flag — over-explanation often means the agent was struggling.

For skill-on, the inverse: if the agent did NOT invoke any harness skill on a scenario where the rubric expects one (e.g., scenario 2 should plausibly trigger wp-database), that's worth noting in the eval-log as "skill_on didn't actually load skills."

## Phase 2 — Judges (8 subagent dispatches)

For each scenario id (after both legs have landed in `outputs/`):

1. Build the inlined judge prompt:
   ```bash
   python3 ~/.claude/plugins/netdust-core/evals/run-eval.py --build-judge <id>
   ```
2. Read the resulting prompt:
   ```bash
   cat ~/.claude/plugins/netdust-core/evals/prompts/scenario-<id>-judge.md
   ```
3. Dispatch a third subagent with `subagent_type: general-purpose`. Pass the verbatim judge prompt.
4. Save the response to:
   ```
   ~/.claude/plugins/netdust-core/evals/outputs/scenario-<id>-judge.md
   ```

### Judge quality checks

After each judge response, eyeball it:
- Does it have ~one `RULE_ID: coverage | evidence` line per rule listed in the prompt? (Should match the count.)
- Does it end with a `SUMMARY:` line in the exact format?
- Are the coverage values from the enum (`both`, `baseline_only`, `skill_only`, `neither`, `na`)?

If any of the above is off, the score parser will fail or produce garbage. Re-dispatch the judge with a stricter "follow the exact output format" reminder.

### Parallelization

All 8 judges can run in parallel — they're independent. Single message with 8 Agent tool calls is the ideal shape if the context budget allows. Otherwise batch by 4.

## Phase 3 — Score and log

```bash
python3 ~/.claude/plugins/netdust-core/evals/run-eval.py --score
```

This reads all judge outputs, writes the scored log to `~/Sites/netdust-wp-manager/tasks/eval-log.md`, and prints a summary to stdout.

### Sanity checks before declaring 1.6 done

1. `eval-log.md` has all 8 scenarios.
2. Each scenario has a parsed summary (not "WARNING: no summary line parsed").
3. The "Aggregate — canonical rules only" section is populated.
4. The terminal summary shows `skill_delta` per scenario plus the total.

If any scenario's row says "NO SUMMARY PARSED", that judge output was malformed — re-dispatch the judge and re-run `--score`.

## Phase 4 — Hand off to 1.7

The eval log is now the input to task 1.7 ("Read the results honestly"). Don't act on the results inline — just confirm the log is complete and clean, then mark 1.6 done in `harness-improvement-plan.md` with a progress entry that captures:

- Total `skill_delta` (the headline number)
- Any scenarios where `skill_delta` was negative or zero (warrants investigation)
- Any rule that was `baseline_only` across multiple scenarios (skill ACTIVELY misled the agent)
- Time taken

Task 1.7 reads the log and produces `tasks/skill-eval-findings.md` — that's where the rewrite/delete decisions live, not here.

## Common failure modes (and fixes)

| Symptom | Likely cause | Fix |
|---|---|---|
| Baseline agent loaded a skill anyway | The skill's trigger description was too pull-y for a Sonnet doing PHP work; instructions weren't strong enough | Rerun with a stricter prefix prompt; if it keeps happening, note "leg contaminated" in eval-log manually |
| Skill-on agent didn't load any skill | Skills' description triggers didn't fire for that scenario shape | Note in eval-log; it's a real finding about skill trigger coverage |
| Judge gave per-rule lines but no SUMMARY | Agent ran out of space or forgot the protocol | Rerun the judge; if it keeps failing, the rule list is too long — split the scenario's rules across two judge runs |
| Judge marked everything `both` | Lazy judging — agent didn't read the outputs carefully | Rerun with a harsher prompt: "If you can't cite specific code, the rule is not covered." |
| Parser crashed on `--score` | Judge output didn't match the regex | Eyeball the offending file in `outputs/`; fix manually or rerun judge |

## Idempotency

- `--prepare` overwrites `prompts/` cleanly (safe to rerun if rubric/scenarios change).
- `--build-judge` overwrites a specific judge prompt (safe to rerun after rewriting outputs).
- `--score` APPENDS to `eval-log.md` (safe — historical runs are preserved with timestamps).
- `outputs/` is not auto-cleaned. Manually `rm` if you want a fresh re-run.
