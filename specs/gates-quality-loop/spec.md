# gates-quality-loop — spec (trimmed)

2026-11-04, trimmed 2026-11-06 · amends `specs/netdust-gates/spec.md` R6 and the Close in `skills/policy/SKILL.md` · status: approved by Stefan 2026-11-06 ("approved, write plan 1"), the approved 2026-11-06 items included

## What the trim changed

The 2026-11-04 draft put mutation testing and test pruning into every feature's Close. The handoff of 2026-11-05 (`netdust-studio/specs/studio-checks/handoff.md`) and Stefan's choice that day moved them out of the build: "Move mutation testing out of the per-feature flow"; "Mutation + pruning triggered by changed lines after deploys … No point testing tests when nothing changed"; "Pruning judged by Stefan or a strong model … never auto-deleted". They now belong to `studio-checks` (run locally from Studio when enough lines changed). Kept from the draft: the revert proof, slices, the generated report, screenshots in the repo, the Close as make verbs, the loop caps and the trial rule, each without its mutation or pruning parts. The static security gates the handoff also named shipped separately (`security-checks`: the exposure probe in `make health`, core's lint gate).

Removed, with where they went: R1 (a mutation tier in `make gate`) and R3 (the pruner as a Close step) → `studio-checks`; R5 (the mutation re-run after the fix pass) → gone with R1; the `prune` verb of R14, the pruner and mutation caps of R6, the mutation and prune evals of R13, and the mutation and pruner counters of R15 → gone with them.

## Intent

Stefan, 2026-11-04: *"I want the build process as autonomous as possible but following guidelines how to code, review security, drift, efficiency, etc so output quality is meeting my standards, is always the same."* and *"I want every features to be E2E testable in shakeouts with tests that are proven to work."*

netdust-gates already enforces the first half by executables (`make gate`, `shakeout-check.py`, the guard hooks). Two places where "proven" is still prose:

- **An e2e test is never shown to be able to fail.** `shakeout-check.py` proves a PNG exists, that the manifest is well-formed and that no credential leaked. It cannot tell a browser test that catches a regression from one that always passes.
- **Architecture drift against core is checked by an agent running greps.** `netdust-wp:ntdst-drift-reviewer` is thorough, but a misread or skipped command is invisible, and none of it is in `make gate`.

This spec closes both, adds the feature report Stefan asked for, and writes the loop limits down so none of it can spin.

## The flow after this spec

```
intake → spec → plan → plan-review ─(cap 2 rounds)→ STOP: Stefan approves the plan
  → build, per slice (coder session, RED→GREEN, cap 3 attempts per task)
      per slice: make gate · that slice's own shake-out flows · make report
  → Close, once per feature (each step is a make verb or names one, R14):
      make gate   (… lint → analyse → invariants → … test:e2e)
      make review (whole-branch review, plus security-sentinel and invariant-auditor where they apply; checks the right tests EXIST)
      one fix pass (each fix RED→GREEN; no re-review)
      /shakeout in a session (real browser; screenshots and revert logs committed), then make shakeout (the check)
      one shake-out fix round if a row failed (R6)
      make report (generated from artifacts; one section per slice; committed)
      make gate   once more, on the final tip — the green run stamps gate/feature/<name>, which promote requires
  → STOP: Stefan sees the screenshots → make promote
Mutation testing and test pruning run outside this flow: studio-checks.
```

## Requirements

**R2 — Every new e2e test is proven to fail without the feature.** For each `browser` and `wire` test the shake-out COMMITS (re-driven rows of surfaces already registered are exempt: they should pass on the base), a script (`bin/revert-run`) puts the base version of the branch's changed non-test files back in the working tree (`git checkout <base> -- <paths>`, the base being the merge-base with production's branch), runs that one test against the same DDEV site, and restores the files in a trap whatever happens; nothing is committed and no second DDEV project is needed. The run is recorded as `specs/<feature>/shakeout/<test-file-stem>.revert.log`, the row matched to its log by the test file the row names. `bin/shakeout-check.py` requires, for each such row, a log whose run failed on an ASSERTION; a non-zero exit from a timeout, an unmatched locator, a login or a seeding error does not count (the hunt rule's own standard). A row the base cannot run at all (the feature changed the schema, so setup fails) needs Stefan's `Accepted-by-human:`, as any excused row does today.
*Source: "tests that are proven to work."*
*Mechanism (base-commit run, log file as evidence): approved 2026-11-05 (the trim kept it: "Revert proof: keep it in the build"). Swap-and-restore, assertion-only, new rows only, the base: invented in answer to the builder check — approved 2026-11-06.*

**R4 — Reviewers check that the right tests exist, not how good they are.** The `make review` prompt, `security-sentinel` and `invariant-auditor` each gain one line: test quality is `studio-checks`' job (mutation and pruning, run outside the build); check that every Review Focus line has a Test map row with a test that covers the risk, and that every e2e flow has its revert log (R2); do not re-judge assertions or redundancy.
*Source: "the prune is a reviewer for the tests, no? So the reviewers after it, do they again review test code?" — approved 2026-11-04 ("Ok"); the pointer to studio-checks follows the trim.*

**R6 — Every loop in the flow is capped, and a cap ends in a stop for Stefan.** Plan review: two rounds, then Stefan gets the plan with the open findings. Coder, per task: three failed attempts at a green gate tier, then it asks its reviewer session. Fix pass: one pass, no re-review. Shake-out: one fix round for a failed row, then Stefan. The final `make gate` runs once. A cap hit is ledgered as `Ruling:` with the cost if wrong, and listed in the final message. The caps are written once in `skills/policy/SKILL.md` and stated nowhere else.
*Source: "as long as we don't end up in endless loop, good".*
*The numbers (2, 3, 1): invented — approved 2026-11-06.*

**R7 — Large features are cut into slices; each slice closes with a report.** The plan may divide its tasks into slices. A slice is a vertical cut: it ends in something Stefan can see or run. A layer ("database first") is not a slice. A slice with no visible surface has no flows and its report says only what was built. The plan review judges the cut, as it already judges a spec's cut into plans. Per slice, only the cheap steps run: `make gate`, the slice's own shake-out flows, and the slice's report. The whole-branch review, the one fix pass, the final gate and the full registered `@e2e` set run once, at the end of the feature. A feature of one slice runs exactly the Close it has today. Reviews are not multiplied by slices. One plan stays one branch and one promotable unit; slices do not change that or add dependencies between plans. The slice is named in the task heading (`### Task 4 · Slice 2: …`), the one exception to "no change to plan grammar", because a report per slice needs it; a flow belongs to the slice of the task whose Test map row names it. One `shakeout.md` per feature, its rows appended slice by slice; the hunt for surfaces nobody named runs once, at the feature's end; Stefan's screenshot yield is one stop, at the end, the per-slice reports linking their screenshots as they land.
*Source: "features can be large. If they get [split] up in meaningful steps, this happens after each step…"; "I wouldn't change what we have now, we just need to make sure that everything is logical".*
*Slice = vertical cut: approved 2026-11-04. Per-slice steps limited to gate, own flows, report; the label exception; one shakeout.md; one yield: invented in answer to that condition and the builder check — approved 2026-11-06.*

**R8 — The feature report is generated, not written.** `bin/feature-report.py <feature dir>` writes `specs/<feature>/report.md`, one section per slice, from `plan.md` (the test map and tasks), `shakeout.md` and `specs/CHECKS.md`. Each section lists what was built and the user flows, and each flow links its test file, its `@e2e` entry, its screenshot and its revert log. A flow with no test, or a test with no revert log, appears as a named gap. The script reads artifacts only; an agent never fills in a field from memory.
*Source: "after a feature is done, I need a report telling me what has been build and what E2E test are added for a shakeout. Naming the user flows etc."*

**R9 — Screenshots are captured straight to the committed path.** `shakeout-qa` captures to `specs/<feature>/shakeout/<name>.png`, never to the session scratchpad, and shows Stefan that path. `shakeout-check.py` already rejects a manifest without a real PNG there; the fix is the explicit destination in the agent prompt, and a test in `test_shakeout_check.py` that a scratchpad path in the Evidence column fails.
*Source: "the screenshots are stored outside the project in tmp folder which is a hassle" — "it's an easy fix we'll do together with this bigger plan".*

**R10 — Studio holds links to the artifacts of a feature.** `netdust-core:worktable` gains one step at each stop and at Close: write onto the `werkpakket` a pointer per artifact (spec, plan, plan-review, review, shakeout, report, screenshots), each as repo-relative path plus the commit sha it was read at. Git stays the source of truth; Studio links to it. A session without Studio loses nothing and the next one catches up. Studio probably has no fields for the pointers yet (Stefan: "possibly not yet, easy to change"). Adding them is a Studio change outside this repo; R10 is built last and waits for it. Nothing else in this spec depends on it.
*Source: "Now that I have netdust studio… there every branch is recorded. The specs, plans, the screenshots and report can be linked? So I use studio to track state and easy access?"*
*Which fields: invented — approved 2026-11-06, blocked on the Studio change.*

**R11 — Consumer-side architecture drift becomes a gate tier.** The mechanical checks that `ntdst-drift-reviewer` runs as greps become one script that runs in `make gate` as an `invariants` tier, between `analyse` and `audit:deps`. It covers Part 1 (core's `ARCHITECTURE-INVARIANTS.md` checks, run against the consumer's tree with the path rewriting the agent's `locate()`/`parse()`/`run()` sections already define; core 5.7.1 has thirteen) and the grep-able Part 2 checks (#1 repository bypass, #3 second HTTP door, #8 raw post and meta functions, #9 raw `template_include`, #11 baseline re-emitted, #15 `function_exists()` around a core helper, #16 hand-registered ability). A non-empty hit fails the tier and names the invariant, file and line. The script's expectation handling follows the agent's rules: an expectation of empty or 0 is hard, and a count with a named list is compared as written; each Part 2 grep carries its "Then:" filter from the agent (the repository files, the `scripts/` bulk exception, the `ntdst_get()`-in-template shape) into the script. It scans the site's own code (its mu-plugins and themes, never `vendor/` or the framework packages). A legitimate exception is waived inline where it stands, `// ntdst-drift: allow #<n> -- <reason>`, the shape `phpcs:ignore` uses; there is no allow-list file and no baseline, so an existing site adopting the tier fixes or waives each hit once, by hand.
The script has one home. `ntdst-drift-reviewer` runs it, reads its output, and keeps only the checks that need judgment (#2 pass-through, #4, #5, #6, #7, #10, #12, #13, #14) and the "borderline" triage. The agent's own copy of the mechanical greps is deleted, so the two cannot diverge.
*Source: "Check if nothing likes this exists already" (answer: the agent exists, the gate tier does not); "Add solutions for the 2 gaps".*
*Home of the script: wp-starter's `gate/bin/check-invariants.sh`. Stefan, 2026-11-04: "core is pure php, gate/ makes more sense." It renders into every new site and, through `package-gate/`, into packages; existing sites adopt it by hand, as every gate tier.*
*Kept here at the trim: on 2026-11-05 it was to move to the static-gates spec, which became `security-checks` without it. The filters, scope and inline waiver: invented in answer to the builder check — approved 2026-11-06.*

**R12 — Baseline's invariants are not run against sites.** `ntdst-baseline`'s invariants describe baseline's own internals and are already enforced inside baseline's own `composer gate`. Running them against a site would report baseline's code, or nothing. The one rule baseline holds for consumers, INV-2 ("one configuration door: `ntdst/baseline/*` filters, never an option; a module is configured or turned off, never shadowed"), is already drift-reviewer check #11, and R11 moves its grep part into the gate script. The reasoning is recorded in `skills/policy/wordpress.md` so the question is not reopened.
*Source: "Add solutions for the 2 gaps". Decision that INV-2 alone crosses over: invented — approved 2026-11-06.*

**R13 — Evals.** Two behavioural cases join `evals/cases.json`: a shake-out whose revert log shows exit 0 fails `shakeout-check.py`; a plan with a layer-shaped slice is flagged by the plan review.
*Source: global CLAUDE.md, "every skill ships with evals."*

**R14 — Every Close step is a `make` verb, and the Makefile is the one interface for human and agent.** `netdust-devops`'s `dist/Makefile.netdust` gains `shakeout name=X` and `report name=X`, each reading `commands.<verb>` from `site.yml` the way `review` reads `commands.review` (`commands.shakeout`: `python3 bin/shakeout-check.py specs/$name`, the deterministic check of the committed manifest, screenshots and revert logs; `commands.report`: `python3 bin/feature-report.py specs/$name`). Driving the browser stays `/shakeout` in a session, Stefan's or the coder's, because it has stops only Stefan answers; `make shakeout` checks what it left. `make doctor` lists them, `help` documents them, and the devops `VERSION` is bumped. `skills/policy/SKILL.md`'s Close names the steps in the order of the flow above, so a human running the Close by hand and a coder session run the same commands in the same order. A box without a `commands.<verb>` fails that verb with the line to add, as `review` does, so a step cannot be skipped unseen. The policy file stays under its 150-line limit (`tests/test_policy_skill.py`): existing text is cut to make room.
*Source: "the make file is human memory and human tool, but i want the agents to implement same code and that the flow is logical, with tests and reviews there where we need them."; `make shakeout` as the check: Stefan, 2026-11-06 ("make verb = the check").*

**R15 — Every step this spec adds is on trial.** The revert proof (R2) carries a removal condition in the growth rule's own shape: when the last five features show it did nothing — no revert log failed unexpectedly and no gap in a report traced to it — it comes out. `bin/feature-report.py` appends one line per feature to `specs/CHECKS.md`'s trial log (`revert-fails: <n> · report-gaps: <n>`) so the count is a grep, not a memory; the plugin's `CLAUDE.md` gains the removal rule beside the shake-out hunt's. The report records the Close's wall-clock, from the commit times of the first Close step to the report commit; over the first three features, if the revert proof costs more time than the review it protects, it is cut back before any new step is added. (The token counter `run-cost.py` belongs to the retired netdust-agent and is not brought back.)
*Source: "as long as we don't go back to endless writing test and testing. netdust-agent used something similar and things slowed down a lot." The removal count (five features): invented — approved 2026-11-06.*

## Where each change lands

| Change | Repo | Files |
|---|---|---|
| R11 | wp-starter | `gate/bin/gate.sh`, `gate/composer.json` scripts, `gate/bin/check-invariants.sh` |
| R2, R9 | netdust-plugins | `bin/shakeout-check.py`, `agents/shakeout-qa.md`, `tests/test_shakeout_check.py` |
| R4, R6, R7 | netdust-plugins | `skills/policy/SKILL.md`, `CLAUDE.md`, `commands/feature-review.md`, `agents/plan-reviewer.md` |
| R8, R15 | netdust-plugins | `bin/feature-report.py`, `commands/shakeout.md`, `CLAUDE.md` |
| R14 | netdust-plugins | `netdust-devops/dist/Makefile.netdust`, `dist/VERSION`, `site.yml` schema docs, `skills/policy/SKILL.md` |
| R10 | netdust-plugins (+ Studio) | `netdust-core/skills/worktable/SKILL.md` |
| R11 | netdust-plugins | `netdust-wp/agents/ntdst-drift-reviewer.md` |
| R12 | netdust-plugins | `skills/policy/wordpress.md` |
| R13 | netdust-plugins | `evals/cases.json` |

Two repos, so two plans: one in netdust-plugins (R2, R4, R6–R10, R12–R15 and R11's agent half) and one in wp-starter (R11's script and tier). The netdust-plugins plan can land first; the agent keeps its greps until the wp-starter tier exists.

## Not in this spec

- **Mutation testing and test pruning** — `studio-checks`, outside the build.
- **The static security gates** — shipped in `security-checks` (exposure probe, core lint).
- **The project-setup brainstorm** (what a new project needs). Stefan's vision names it as a separate plugin.
- Any change to plan grammar (growth rule), apart from R7's slice label. Auto-merging or auto-promoting: `promote` and `ship` stay Stefan's.

## Open questions

None left for planning. Studio mirrors the slice label (R7) in each `Taak`'s `notities` until a real grouping field exists (R10).

## Success

On the next planned feature in a WordPress project: `make gate` has an invariants tier, green; every new e2e flow has a revert log with a non-zero exit; `report.md` exists and names no gaps; the screenshots are under `specs/<feature>/shakeout/`; no loop ran past its cap. If a vacuous e2e test reaches Stefan's screenshot yield anyway, the revert proof is wrong, not the process.
