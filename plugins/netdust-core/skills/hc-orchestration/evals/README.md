# hc-orchestration evals

Seven A/B scenarios. Each has a baseline leg (skill not loaded), a skill-on leg (SKILL.md read
first) and a judge template whose rules the skill must make pass.

## Procedure

1. Dispatch each leg as a fresh general-purpose subagent, both legs on the same model:
   "Read `evals/scenario-N-<leg>.md` and do exactly what it says; your final reply is only
   your answer." Every leg is a written answer: it runs no command but `hc --skill` and
   `hc <verb> --help`, because the hc core on the machine is live.
2. Inline both outputs into `scenario-N-judge.template.md` (`{{BASELINE}}`, `{{SKILL_ON}}`).
3. Dispatch a fresh judge subagent with the filled template. It scores every rule PASS/FAIL per
   leg with one quoted line of evidence.
4. The skill earns its keep when the skill-on leg passes every rule the baseline fails and
   fails none the baseline passes. Record the scores below.

S1 and S4 are regression guards: `hc --skill` already teaches delegation (template, file report,
wait, cleanup) and event waits (timeout as a check-in, blocked as a human), so their baselines
pass. The skill must not make them worse.

## Scores

2026-10-29, both legs on sonnet, judges on opus. B = baseline, S = skill-on.

| Scenario | Rules | B fails | S fails | Verdict |
|---|---|---|---|---|
| 1 delegate + gate (guard) | D1–D6 | none | none | guard holds |
| 2 the pair handoff | P1–P5 | P1 P2 P3 P4 P5 | none | skill earns it |
| 3 urgent hotfix + planning | W1–W5 | W1 W4 | none | skill earns it |
| 4 waiting on children (guard) | E1–E5 | none | none | guard holds |
| 5 the observer | O1–O5 | O3 O4 | none | skill earns it |
| 6 no core running | C1–C4 | C1 C2 C3 C4 | none | skill earns it |
| 7 stale socket file (review S2) | C5–C7 | C5 C6 C7 | none | skill earns it |

Baselines worth remembering: S2 cut `~/Sites/stride-greeting` and started the coder without
`--outlive-parent`; S3 put both the hotfix and the planning in `~/Sites/*` worktrees; S5 wrote a
running digest and looped until told to stop; S6 ran `hc server status` and `hc ls` to "confirm"
no core, which would have started it.

Feature review fix pass, same day: S7's baseline slot holds the skill-on leg run on the PRE-fix
skill (socket-file check), which took `default.sock` as a running core (the RED for review S2).
S6 re-run on the fixed skill (connect probe): C1–C4 still pass.
