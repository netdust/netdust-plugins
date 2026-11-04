# gates-quality-loop — spec

2026-11-04 · amends `specs/netdust-gates/spec.md` R6 and the Close in `skills/policy/SKILL.md` · status: DRAFT, awaiting Stefan's approval

## Intent

Stefan, 2026-11-04: *"I want the build process as autonomous as possible but following guidelines how to code, review security, drift, efficiency, etc so output quality is meeting my standards, is always the same."* and *"I want every features to be E2E testable in shakeouts with tests that are proven to work."*

netdust-gates already enforces the first half by executables (`make gate`, `shakeout-check.py`, the guard hooks). Reading the repos on 2026-11-04 showed two places where "proven" is still prose:

- **A test is never shown to be able to fail.** `shakeout-check.py` proves a PNG exists, that the manifest is well-formed and that no credential leaked. It cannot tell a browser test that catches a regression from one that always passes. The policy asks for RED→GREEN, but no script checks it. `test-pruner` runs on demand only and judges by reading.
- **Architecture drift against core and baseline is checked by an agent running greps.** `netdust-wp:ntdst-drift-reviewer` (Part 1: core's invariants run against the site; Part 2: 16 consumer checks) is thorough, but a misread or skipped command is invisible, and none of it is in `make gate`.

This spec closes both, adds the feature report Stefan asked for, and writes the loop limits down so none of it can spin.

## The flow after this spec

```
intake → spec → plan → plan-review ─(cap 2 rounds)→ STOP: Stefan approves the plan
  → build, per slice (coder session, RED→GREEN, cap 3 attempts per task)
  → Close, per slice (each step is a make verb, R14):
      make gate  (… test:unit → test:int → MUTATION → …)
      make prune (fresh agent; reverted automatically if a killed mutant returns; 1 attempt)
      make review (whole-branch review, plus security-sentinel and invariant-auditor where they apply; checks that the right tests EXIST)
      one fix pass (each fix RED→GREEN; no pruner, no re-review)
      make gate  again on the final tip — mutation re-runs; a green run stamps gate/feature/<name>
      make shakeout (real browser; screenshots committed; revert proof; shakeout-check.py exits 0)
      make report (generated from artifacts; one section per slice)
  → STOP: Stefan sees the screenshots → make promote
```

## Requirements

**R1 — A diff-scoped mutation tier in `make gate`.** wp-starter's `gate/bin/gate.sh` gains a `test:mutation` tier after `test:int`: Infection for PHP, Stryker for JS, restricted to files the branch changed against production's branch. A surviving mutant exits non-zero and names the file and mutator. The tier runs only where `make gate` writes a stamp: a clean `feature/*` or `hotfix/*` tree. `deploy` and `ship` run the same gate on a composed commit with `NETDUST_GATE_STAMP=off`; there the mutation tier is skipped and says so, so a deploy never waits for it or fails on its cap. A branch that changes no source file skips the tier and says so. The tier has a time cap, 10 minutes by default and set in the project's gate config: at the cap it stops, exits non-zero as `incomplete`, and names the files it did not reach. An incomplete run is a stop for Stefan, not a retry. Mutating the e2e tier is not done: it is too slow and too flaky; R2 proves e2e another way.
*Source: "I want every features to be E2E testable in shakeouts with tests that are proven to work."*
*Cap: "I can't wait for hours just for this" — approved 2026-11-04; the 10-minute value is invented, approved: pending.*
*Tool choice (Infection, Stryker): invented — approved: pending.*

**R2 — Every new e2e test is proven to fail without the feature.** `shakeout-qa` runs each test it commits against the base commit's non-test code and records the run as `specs/<feature>/shakeout/<name>.revert.log` with the exit code. `bin/shakeout-check.py` requires, for each `browser` and `wire` row, that the log exists and shows a non-zero exit; a row without one fails the check. Only the human's `Accepted-by-human:` excuses a row, as today.
*Source: "tests that are proven to work."*
*Mechanism (base-commit run, log file as evidence): invented — approved: pending.*

**R3 — The pruner becomes a Close step.** Between the green gate and the reviews, a fresh-context `test-pruner` runs with a narrow prompt: it may delete or merge tests, never edit production code, and it files `specs/<feature>/prune.md` with the mutation score before and after and the reason for each removal. After it, the mutation tier runs again; if any previously killed mutant now survives, the prune is reverted and `prune.md` says so. One attempt: a reverted prune is not retried. No approval from Stefan is needed. The plugin's `CLAUDE.md` boundary "their agents are read-only; every change after them is Stefan's approval first" is rewritten to name `test-pruner` as the one agent in the Close that commits its own changes, bounded by the automatic revert.
*Source: "I don't need to approve the pruning. Have, just like a plan, an other agent look at it, fresh context but maybe a specific prompt."*

**R4 — Reviewers check that the right tests exist, not how good they are.** The `make review` prompt, `security-sentinel` and `invariant-auditor` each gain one line: test quality was decided by the mutation tier and the pruner; check that every Review Focus line has a Test map row with a test that covers the risk, and do not re-judge assertions or redundancy. A finding about a test the pruner kept on purpose is out of scope.
*Source: "the prune is a reviewer for the tests, no? So the reviewers after it, do they again review test code?" — approved 2026-11-04 ("Ok").*

**R5 — The fix pass is followed by one more `make gate`, never by the pruner.** `promote` and `land` take only a tip a green gate stamped, and the prune and the fix pass both move the tip, so the final `make gate` after the fix pass is required by devops already; its mutation tier is the re-run. It runs once. A failure goes to Stefan as a stop, not to another agent. The pruner does not run again: a fix test exists because a reviewer found a specific problem, and pruning it would undo the fix.
*Basis: `netdust-devops/dist/Makefile.netdust` (`promote`, `land`, `gate` stamp).*
*Source: "What do you think? Should it?" — answered with the position above, approved 2026-11-04 ("Ok as long as we don't end up in endless loop, good").*

**R6 — Every loop in the flow is capped, and a cap ends in a stop for Stefan.** Plan review: two rounds, then Stefan gets the plan with the open findings. Coder, per task: three failed attempts at a green gate tier, then it asks its reviewer session. Pruner: one attempt. Fix pass: one pass, one mutation re-run, no re-review. A cap hit is ledgered as `Ruling:` with the cost if wrong, and listed in the final message. The caps are written once in `skills/policy/SKILL.md` and stated nowhere else.
*Source: "as long as we don't end up in endless loop, good".*
*The numbers (2, 3, 1): invented — approved: pending.*

**R7 — Large features are cut into slices; each slice closes with a report.** The plan may divide its tasks into slices. A slice is a vertical cut: it ends in something Stefan can see or run. A layer ("database first") is not a slice. A slice with no visible surface has no flows and its report says only what was built. The plan review judges the cut, as it already judges a spec's cut into plans. The Close runs per slice: gate, prune, reviews, fix pass, and the slice's own shake-out flows. The full registered `@e2e` set runs once more at the end of the feature. One plan stays one branch and one promotable unit; slices do not change that or add dependencies between plans.
*Source: "features can be large. If they get [split] up in meaningful steps, this happens after each step…"; "I wouldn't change what we have now, we just need to make sure that everything is logical".*
*Slice = vertical cut, full suite once at the end: invented — approved: pending.*

**R8 — The feature report is generated, not written.** `bin/feature-report.py <feature dir>` writes `specs/<feature>/report.md`, one section per slice, from `plan.md` (the test map and tasks), `shakeout.md` and `specs/CHECKS.md`. Each section lists what was built and the user flows, and each flow links its test file, its `@e2e` entry, its screenshot and its revert log. A flow with no test, or a test with no revert log, appears as a named gap. The script reads artifacts only; an agent never fills in a field from memory.
*Source: "after a feature is done, I need a report telling me what has been build and what E2E test are added for a shakeout. Naming the user flows etc."*

**R9 — Screenshots are captured straight to the committed path.** `shakeout-qa` captures to `specs/<feature>/shakeout/<name>.png`, never to the session scratchpad, and shows Stefan that path. `shakeout-check.py` already rejects a manifest without a real PNG there; the fix is the explicit destination in the agent prompt, and a test in `test_shakeout_check.py` that a scratchpad path in the Evidence column fails.
*Source: "the screenshots are stored outside the project in tmp folder which is a hassle" — "it's an easy fix we'll do together with this bigger plan".*

**R10 — Studio holds links to the artifacts of a feature.** `netdust-core:worktable` gains one step at each stop and at Close: write onto the `werkpakket` a pointer per artifact (spec, plan, plan-review, review, prune, shakeout, report, screenshots), each as repo-relative path plus the commit sha it was read at. Git stays the source of truth; Studio links to it. A session without Studio loses nothing and the next one catches up. Studio probably has no fields for the pointers yet (Stefan: "possibly not yet, easy to change"). Adding them is a Studio change outside this repo; R10 is built last and waits for it. Nothing else in this spec depends on it, and until it lands the artifacts are reachable in git as before.
*Source: "Now that I have netdust studio… there every branch is recorded. The specs, plans, the screenshots and report can be linked? So I use studio to track state and easy access?"*
*Which fields: invented — approved: pending, blocked on the Studio change.*

**R11 — Consumer-side architecture drift becomes a gate tier (gap 1).** The mechanical checks that `ntdst-drift-reviewer` runs as greps become one script that runs in `make gate` as an `invariants` tier, between `analyse` and `audit:deps`. It covers Part 1 (core's `ARCHITECTURE-INVARIANTS.md` checks, run against the consumer's tree with the path rewriting the agent's `locate()`/`parse()`/`run()` sections already define) and the grep-able Part 2 checks (#1 repository bypass, #3 second HTTP door, #8 raw post and meta functions, #9 raw `template_include`, #11 baseline re-emitted, #15 `function_exists()` around a core helper, #16 hand-registered ability). A non-empty hit fails the tier and names the invariant, file and line. The script's expectation handling follows the agent's rules: an expectation of empty or 0 is hard, and a count with a named list is compared as written.
The script has one home. `ntdst-drift-reviewer` runs it, reads its output, and keeps only the checks that need judgment (#2 pass-through, #4, #5, #6, #7, #10, #12, #13, #14) and the "borderline" triage. The agent's own copy of the mechanical greps is deleted, so the two cannot diverge.
*Source: "Check if nothing likes this exists already" (answer: the agent exists, the gate tier does not); "Add solutions for the 2 gaps".*
*Home of the script: wp-starter's `gate/bin/check-invariants.sh`. Stefan, 2026-11-04: "core is pure php, gate/ makes more sense. If the whole setup needs rearranging to have this better, ok." It renders into every site and, through `package-gate/`, into packages. Core's invariants stay in core's doc; the script reads the doc from the vendored copy, as the agent does today.*

**R12 — Baseline's invariants are not run against sites (gap 2).** `ntdst-baseline`'s INV-1…14 describe baseline's own internals (`Shell`, `SharedSlugs`, `PostCopier`, `PrivateFiles`, `GrantRepository`) and are already enforced where they belong: `bin/check-invariants.sh` runs inside baseline's own `composer gate`. Running them against a site would report baseline's code, or nothing. The one rule baseline holds for consumers, INV-2 ("one configuration door: `ntdst/baseline/*` filters, never an option; a module is configured or turned off, never shadowed"), is already drift-reviewer check #11, and R11 moves its grep part into the gate script. Nothing else from baseline's list crosses over. The reasoning is recorded in `skills/policy/wordpress.md` so the question is not reopened.
*Source: "Add solutions for the 2 gaps".*
*Decision that INV-2 alone crosses over: invented — approved: pending.*

**R13 — Evals.** Four behavioural cases join `evals/cases.json`: a fix-pass test that is vacuous makes the gate fail at the mutation re-run and the result reaches Stefan, not a second fix pass; a prune that lowers the mutation score is reverted; a shake-out whose revert log shows exit 0 fails `shakeout-check.py`; a plan with a layer-shaped slice is flagged by the plan review.
*Source: global CLAUDE.md, "every skill ships with evals."*

## Where each change lands

| Change | Repo | Files |
|---|---|---|
| R1, R11 | wp-starter | `gate/bin/gate.sh`, `gate/composer.json` scripts, `gate/bin/check-invariants.sh`, mutation configs |
| R2, R9 | netdust-plugins | `bin/shakeout-check.py`, `agents/shakeout-qa.md`, `tests/test_shakeout_check.py` |
| R3, R4, R5, R6, R7 | netdust-plugins | `skills/policy/SKILL.md`, `agents/test-pruner.md`, `CLAUDE.md`, `commands/feature-review.md`, `agents/plan-reviewer.md` |
| R8 | netdust-plugins | `bin/feature-report.py`, `commands/shakeout.md` |
| R14 | netdust-plugins | `netdust-devops/dist/Makefile.netdust`, `dist/VERSION`, `site.yml` schema docs, `skills/policy/SKILL.md` |
| R10 | netdust-plugins (+ Studio) | `netdust-core/skills/worktable/SKILL.md` |
| R11 | netdust-plugins | `netdust-wp/agents/ntdst-drift-reviewer.md` |
| R12 | netdust-plugins | `skills/policy/wordpress.md` |
| R13 | netdust-plugins | `evals/cases.json` |

**R14 — Every Close step is a `make` verb, and the Makefile is the one interface for human and agent.** `netdust-devops`'s `dist/Makefile.netdust` gains `prune name=X`, `shakeout name=X` and `report name=X`, each reading `commands.<verb>` from `site.yml` the way `review` reads `commands.review` (`commands.prune`: `claude -p "/netdust-gates:prune-tests …"`; `commands.shakeout`: `claude -p "/netdust-gates:shakeout"`; `commands.report`: `python3 bin/feature-report.py`). `make doctor` lists them, `help` documents them, and the devops `VERSION` is bumped. `skills/policy/SKILL.md`'s Close names the verbs in order — `make gate`, `make prune`, `make review`, the fix pass, `make gate`, `make shakeout`, `make report` — and never the agents behind them, so a human running the Close by hand and a coder session run the same commands in the same order. The agent behind a verb can change without the policy changing. A box without a `commands.<verb>` says so, as `review` does, and never fails the Close for it.
*Source: "the make file is human memory and human tool, but i want the agents to implement same code and that the flow is logical, with tests and reviews there where we need them."*

## Not in this spec

- **The project-setup brainstorm** (what a new project needs, architecture, user flows, UX, features). Stefan's vision names it as a separate plugin; this spec leaves it alone and changes nothing in intake. It wants its own spec.
- Mutating e2e tests, and any change to plan grammar (growth rule).
- Auto-merging or auto-promoting. `promote` and `ship` stay Stefan's.

## Open questions

Resolved 2026-11-04: mutation gets a time cap (R1); Studio fields are a later, easy change (R10); the consumer script lives in wp-starter (R11).

1. **Slices and Studio** (R7, R10): proposal is that the plan's tasks carry a slice label (`### Task 4 · Slice 2: …`), and Studio mirrors it in each `Taak`'s `notities` until a real grouping field exists. Awaiting Stefan's confirmation of what a slice is (R7).

## Success

On the next planned feature in a WordPress project: `make gate` has a mutation tier and an invariants tier, both green; every new e2e flow has a revert log with a non-zero exit; `prune.md` and `report.md` exist and `report.md` names no gaps; the screenshots are under `specs/<feature>/shakeout/`; no loop ran past its cap. If a vacuous test reaches Stefan's screenshot yield anyway, the mutation tier or the revert proof is wrong, not the process.
