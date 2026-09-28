# Spec — test mapping

**Repo:** `netdust-plugins` · **Plugin:** `netdust-gates`
**Provenance:** Stefan, 2026-09-28, brainstormed in a Claude Code session after the Cargo Velo build
(cargovelo-core: a bounded package written in one pass per unit, tests beside the code, browser
flows driven afterwards; about an hour).

## Problem / why

Where a feature is tested, at which tier, and what proves it end to end is decided in six files of
netdust-gates that do not all say the same thing: the policy's Review Focus rule, the WordPress
pack's `Tests:` line and Plan shape, `edge-classes.md`, `threat-modeling`'s last paragraph,
`shakeout-qa` deriving its own flow list, and `plan-reviewer`'s coverage question. The bar for a
single test exists three times (`wp-testing`, `test-pruner`, `plan-reviewer`).

The per-task red/green that turns a bounded website service into a day of ceremony does not come
from netdust-gates at all: it comes from superpowers' `writing-plans` task steps and from the
implementer prompt in `subagent-driven-development`. Nothing in the plan today says how big a task
is, or that its tests are written and run with it.

Stefan: *"I do wonder if red/green is still correct way of working? Why not let the agent do this
in one go and at the same time write integration and E2E tests?"* · *"All I want is secure, high
quality code (use ntdst-core, simple first, less code, di and good reusable abstraction)."*

## Requirements

**R1 — A plan section, `## Test map`, written by a skill.** `netdust-gates:test-mapping` is
invoked by the policy while the plan is written, beside `netdust-gates:threat-modeling`, and
produces one table, one row per unit:

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|

The seam is what a caller uses (route, render, public method). A row with an empty tests cell is
the plan saying that unit is unverified before any code exists.
*Source: "So we add a skill, testing map... It instructs the planner to write up a table indicating where tests should be written and what kind of tests?" · "I think that's exactly what I am looking for, a new plan section. Agents have a hard time to ignore."*

**R2 — The unit cut lives in the same skill.** A task is one unit a single test run can judge: a
service or module with its seam, its tests and the one command that runs them, written in one
pass and closed by that command, then `make gate`. RED-first stays only where it proves
something: the denial test of a data flow, and every fix in the Close's fix pass. A unit that
needs another unit's code to be judged is one unit.
*Source: "one go per unit that a single test run can judge — That's a rule I want to keep for now" · "The unit-cut rule is part of that skill right?" · "When possible the plan is executed in one go like you did with cargo velo tool, but next to it sit targeted tests so we know code is healthy and code is working?"*

**R3 — The tier, by one question per unit.** Does the unit encode a rule this project chose (a
window, a role, a price, a parse of guest input), or is it configuration over a framework that
already carries the rule (a CPT, a field map, a template)? The first gets a behavioural test
through its seam, integration tier when it needs WordPress or the database. The second gets no
test of its own and is proven by the e2e flow that renders it. Edges per row come from
`edge-classes.md`.
*Source: invented — approved 2026-09-28 ("I think that's exactly what I am looking for")*

**R4 — Evidence, never prose.** Each row names the test file and the runner command
(`netdust-wp:wp-testing` owns the commands). "Tested" means that command ran after the unit's
last edit and its output is quoted, the same evidence rule the WordPress pack already applies to
every constraint.
*Source: invented — approved 2026-09-28 (same)*

**R5 — The end result is testable code: integration tests and Playwright user flows.** The
implementer writes the unit and integration tests in the same pass as the code. The e2e flows
named in the table are driven afterwards by `shakeout-qa` through the real browser, committed as
tests and registered in `specs/CHECKS.md` as today. The implementer never drives its own flows:
the separate driver is the outside signal a same-author test cannot give.
*Source: "End result is testable code ( integration and playwright e2e user flows )"*

**R6 — Consumers read the map; none of them decides.**
- `skills/policy/SKILL.md`: one invocation line under `## The plan`; Review Focus becomes
  "each line points at a row"; the Scaffolding bullet becomes a row whose tier reads
  "scaffold, deleted by task N".
- `skills/policy/wordpress.md`: the denial bullet under Plan shape becomes a row rule; the
  `Tests:` constraint stays.
- `agents/shakeout-qa.md`: "Which flows" reads the flows column; the self-derivation paragraph
  goes; `flows.md` stays for a branch with no plan.
- `agents/plan-reviewer.md`, question 2: every row has its test in a task, every Review Focus
  line points at a row, every mitigation has a row.
- `skills/threat-modeling/SKILL.md`: its last paragraph points mitigations at rows.
*Source: "We clean up scattered prose. I like it."*

**R7 — One home for the test-quality bar.** `netdust-wp:wp-testing`'s "What a test owes" is the
bar; `test-pruner` and `plan-reviewer` cite it and stop carrying their own copies.
*Source: same.*

**R8 — Superpowers is never edited; execution mode says what that costs.** Everything lives in
netdust-plugins. The policy's `## Execution mode` states that Native runs each unit as the plan
wrote it, and that subagent-driven implementers follow superpowers' per-task TDD prompt, which
undoes the unit cut, so it is recommended only for a security-boundary unit or a plan that
outlives one context.
*Source: "We can't change superpowers files, ok?" · "Does that mean I need to skip superpowers?" (no)*

**R9 — The growth rule keeps its teeth.** `CLAUDE.md`'s "never as a new plan field" becomes "never
as a plan section a skill does not own": the threat model and the test map are the two sections,
each owned by one skill. Incidents still land as a gate tier, a pack line, an edge class or an
eval case.
*Source: invented — approved 2026-09-28 ("a new plan section")*

**R10 — An eval case, `unit-cut-plan`.** A three-requirement booking spec on a WordPress project
plans with a `## Test map`, at most four tasks, a threat model for its guest form, and no
"run the test to verify it fails" step inside a task.
*Source: the growth rule (`plugins/netdust-gates/CLAUDE.md`)*

## Security-relevant surfaces

- [x] None of the above — prose skills, agents and their pin tests.

## Constraints carried from the plugin

The policy skill stays under 150 lines; the new skill is a contract, well under 50, and cites
`wp-testing` and `edge-classes.md` rather than restating them. `bash plugins/netdust-gates/tests/run.sh`
stays green; `test_policy_skill.py` gains the `Test map` token. Version bump with a description
line, per the plugin's convention.

## Out of scope

- Making the integration tier runnable in a cloud session (a session-start hook on the project).
  Without it the map's integration rows are written but not run, which is the one honest gap of
  the Cargo Velo build; it is a project setup problem, not a plan problem.
- Any edit to superpowers, and anything under `plugins/netdust-agent/` (retired).
- The Stride family's legacy Codeception stack: the map names its runners through `wp-testing`'s
  legacy section unchanged.
