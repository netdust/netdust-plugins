---
name: building
description: The BUILD overlay — superpowers executes; this adds the netdust gates. Refuses Class A/B work without the seam artifact (approved tasks.md + gate-check GREEN). Home of the plan-less classes (C bug-fix bundle, D security diff, E small tweak). Triggers on "execute the plan", "work the plan", "start building", "fix the code-review findings". NOT for writing plans — that is `planning`.
---

# Building — the netdust overlay on superpowers

**Superpowers is the workhorse. This skill adds the netdust gates around it.** It never
re-plans — a wrong plan shape goes back across the seam as a plan correction.

## Precondition (before anything else)

| Class | Entry ticket |
|---|---|
| A/B (plan-driven) | `tasks.md` exists · `python3 <plugin>/bin/gate-check.py specs/<feature>` exits **0, run NOW by you** · human approved. Any part missing → refuse, route to `planning`. |
| C (review-finding bundle) | no plan; one TDD cycle per *behaviour* finding (non-behavioural fixes close on the existing suite green) |
| D (ad-hoc security-boundary edit) | a `## Threat model` on the diff FIRST, then one TDD cycle — even for a one-liner (`class-d-gap`) |
| E (small self-contained tweak) | one TDD cycle, no plan, no shake-out; a security-boundary file makes it D, never E |

**The lane is read from `tasks.md`, never re-decided here.** Every cluster carries
`Lane: behaviour` or `Lane: contract` (`check_cluster_lanes` refused the unsafe direction
at the seam). The lane sets the dispatch shape, the model, the tests owed and the review
owed — the two paths are spelled out below; nothing in this skill applies to both lanes
unless it says so.

**On a project carrying `site.yml`, every branch decision is `netdust-core:dev-stack`'s**
— `make feature` / `make hotfix` to start, `make finish` to close, a worktree based on
the integration branch read from `site.yml` (never a hard-coded `master`); the
superpowers finish skill's merge/PR options are not offered there. Models per dispatch
come from `skills/_shared/model-ladder.md`; herdr moments (isolation, the status tab, the
branch-review pane) from `skills/_shared/herdr-moments.md` — both cited, never restated.

**The handoff is `tasks.md`, and it is never run flat.** Any flat executor over the task
list bypasses the per-task gates and the review-cluster stops — execute task by task
through the overlay below, whatever tool proposes to do the walking.

## Stage 2 — Execute (invoke `superpowers:subagent-driven-development`, or `superpowers:executing-plans` for sequential work)

The upstream skill owns dispatch and status handling. What Netdust adds depends on the lane.

### Behaviour lane — the default for declarative work

The cluster's behaviour block is the whole test contract: ONE RED, observable from
outside the file, named by `RED until:`. Execute it as:

1. **The cluster RED first.** Write the one test from `Observable:` — by the first task's
   implementer, or inline by the controller when it is a one-assertion smoke. Run it,
   watch it fail, write `cluster-open` to the loop ledger naming it (the hook's tolerance
   reads that event). Ground-truth the named dependencies once here for the whole cluster
   (a haiku Explore read — ladder), not per task.
2. **One implementer per task, `behaviour` mode** (ladder: sonnet). No per-task RED, no
   Test-evidence block — the task's proof is that the suite stays green except the named
   cluster RED, and the close-out line `HARNESS-EVIDENCE: role=implementer suite="<cmd>"
   exit=<code>`. `hooks/subagent-stop.py` still blocks a close whose suite did not run or
   exited red beyond the tolerated RED, and its sensitive-path floor still blocks a
   behaviour-mode close on a sensitive path — that block is the signal the task belongs
   in a contract cluster; correct the plan, don't argue with the hook.
3. **Close the cluster on three things and nothing else:** the cluster RED is GREEN
   (`cluster-close`), the `Integration gate:` line holds, and — on a user-facing cluster —
   the `Artifact-diff:` comparison below. No `test-author` feature-test dispatch (the
   cluster RED IS the feature test), no reviewer dispatch, no review-gate stop.

### Contract lane — today's grammar, unchanged

`superpowers:test-driven-development` is the implementer's law — RED first, watched,
never weakened. Netdust adds:

- **Ground-truth before each dispatch** — read the real signatures of the task's named
  dependencies and bake them into the prompt; the plan is a hypothesis, the source is
  truth (`plan-drift-4x`).
- **The dispatch contract** — every code-editing dispatch ends with a Test-evidence block
  (tier, RED/GREEN proof or the Tier-B waiver line, suite delta, `Standards:` line) and
  the machine-parsed close-out line `HARNESS-EVIDENCE: role=<test-author|implementer>
  suite="<cmd>" exit=<code> [lint=<code>]` — `hooks/subagent-stop.py` blocks a code-editing
  close whose suite didn't run, exited non-zero (implementer), or skipped a configured
  linter. **On WordPress the suite is the netdust harness** — Brain Monkey / wp-phpunit
  per the netdust-wp-manager template; load `netdust-wp:wp-testing` into any WP dispatch,
  because superpowers has no knowledge of that environment.
- **`Test-author:` mode is read from the plan, never re-decided at run time.** Default is
  solo (the implementer authors its own RED); `split` — an independent test-author writes
  the RED first, and the implementer greens it unweakened — is reserved for Tier-A
  security-boundary tasks at effective-high stakes. The sensitive-path floor in the hook
  backstops misclassification against the paths actually edited.
- **Feature tests after each contract-lane cluster** — when its tasks are green, dispatch the
  `test-author` to write the cluster's FEATURE tests: the behaviour the cluster promised
  (its `Behaviour:`/`Observable:` block, or its integration-gate line), driven through the
  real harness, denial paths included. Features get independent tests; tasks get the
  implementer's own TDD. Then run the cluster's `Integration gate:` line.
- **A user-facing cluster's integration gate closes on a COMPARISON, not a look.** Name
  the source of truth (the design file, the spec's acceptance rows, the reference
  implementation), enumerate the properties it constrains, and check each against values
  read from the RUNNING artifact — committed as a test, not observed once. Record
  `Artifact-diff: <source> → <n> properties checked, <n> divergent`. Build-output evidence
  (it compiled; the values are in the bundle) never closes this gate — it cannot see a
  different variable winning, a guard skipping the rule, or a stale file on disk. Any
  value deferred to a later cluster is named HERE as "will still look wrong", never left
  for the human to find (`compiled-not-rendered`).

## The review gate (every `── REVIEW GATE ──` marker is a hard stop — contract-lane clusters only)

A behaviour-lane cluster carries no marker and buys no panel: its review is the ONE
`── BRANCH REVIEW ──` at the end of the file (Stage 3). For contract-lane clusters:

- **Artifact first**: before any reviewer is dispatched on a user-facing cluster, load the
  artifact once — page, screen, or command — and record `Artifact-load: <what> → <seen>`.
  Ten seconds of looking beats a dispatch of reasoning about markup. This is the
  reviewer's cheap prior, NOT the correctness check — that happened at the integration
  gate above.
- **Independent reviewers, tier-scaled**: LIGHT — one generalist `reviewer`; STANDARD —
  `reviewer` + `code-simplicity-reviewer`; FULL (any security surface, invariant, or
  data-layer/migration touch) — add `security-sentinel`, and `invariant-auditor` whenever
  the project carries an `ARCHITECTURE-INVARIANTS.md` (the no-drift check: bypasses AND
  reinvented solutions). The author never reviews its own
  diff; escalation to FULL is one-way. Record the verify-budget telemetry line
  (`bin/verify-budget.py` — reports, never interrupts) in the cluster evidence.
- **Findings close by ledger arithmetic**: Criticals (and Importants at effective-high
  stakes) become task lines closing on a named check; other Importants are triaged
  fix-now / park / reject — default park. Fleet findings (defects not reachable through
  this feature's surfaces) are parked to `memory/STATE.md`, never fixed in-branch
  (`press-kit-fleet-bleed`).
- **The stop rule**: a round with zero new Criticals closes review — verify fixes by their
  named checks only. Hard cap two rounds per cluster (`press-kit-five-generations`).

## Stage 3 — Close (spec-complete only; Class E/C skip it)

1. Drive the plan's `## Acceptance flows` matrix through the real browser / un-mocked
   wire (`shakeout-qa` agent, ladder: sonnet; no UI flow passes without a browser having
   driven it). **Only when the matrix is not N/A** — a branch with no user-facing surface
   has nothing to drive, and a shake-out dispatch over nothing is a token sink.
2. **The branch review** at the `── BRANCH REVIEW ──` marker's tier: an all-behaviour
   branch under `standard` or `low` stakes is LIGHT — one `reviewer`, ladder: sonnet; a
   branch carrying contract-lane clusters takes the branch's tier with the panel rules
   above. Under herdr the branch reviewer runs in its own pane with the report in a tab
   (herdr-moments). Then finish: `make finish` on a `site.yml` project (dev-stack), else
   `superpowers:finishing-a-development-branch`.
3. Report the whole-branch verify-budget line with the summary. Then invoke `compounding`
   — the learning loop: what the spec taught lands in CODE-MAP / skill lessons / evals as
   approved proposals.

## Armed loop

`/loop` + `hooks/loop-gate.py` may drive Stage 2 unattended: the ledger
(`bin/loop-check.py`) derives FINISHED from checked boxes PLUS green evidence, never
assertion. The loop changes nothing above — gates apply exactly as written.
