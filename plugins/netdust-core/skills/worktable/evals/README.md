# worktable evals

Two A/B scenarios, run as `../../hc-orchestration/evals/README.md` describes: a baseline leg (skill not
loaded), a skill-on leg (SKILL.md read first), and a judge template whose rules the skill must make pass.
Every leg is a written answer; no tool is called.

## Scores

2026-10-31, both legs on sonnet, judges on opus. B = baseline, S = skill-on.

| Scenario | Rules | B fails | S fails | Verdict |
|---|---|---|---|---|
| 1 mid-plan stop, Studio a day behind a revised plan | K1–K6 | K2 K3 K5 | none | skill earns it |
| 2 a box without worktable | A1–A4 | A1 A3 A4 | none | skill earns it |

Baselines worth remembering: S1 wrote `voortgang: "2/5"` by hand and updated the werkpakket before the
Task 3 row, left the commit out of the done step, and retired the dropped task under a guessed status
with no reason. S2 kept a stop log in the repo for Stefan to mirror by hand — the workaround the skill
exists to prevent, since the plan and git already hold that record.
