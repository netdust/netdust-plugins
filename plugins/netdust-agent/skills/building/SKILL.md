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

**On a project carrying `site.yml`, every branch decision is `netdust-devops:devops`'s**
— `make feature` / `make hotfix` to start, `make finish` to close, a worktree based on
the integration branch read from `site.yml` (never a hard-coded `master`); the
superpowers finish skill's merge/PR options are not offered there. Models per dispatch
come from `skills/_shared/model-ladder.md`; herdr moments (isolation, the status tab, the
branch-review pane) from `skills/_shared/herdr-moments.md` — both cited, never restated.

**Enter and leave through the flow (FR-25).** On a `site.yml` project, Stage 2 does not
dispatch until the current branch is `feature/*` or `hotfix/*` — run `make feature
name=<x>` (`make hotfix` for Class D) first, or hand back; a rung branch is deploy-only
and `hooks/pretooluse-guard.py` denies a raw `git commit` / merge / push there, naming
the verb. Stage 3 closes with `make finish`; `make health` runs before any `make
release`; `make ship` and a production `/deploy` happen only on the operator's explicit
ask in that turn (the devops rule). The flow itself is tested — `make test` runs
`scripts/tests/flow-test.sh` — so "the Makefile is broken" is a finding to file, never a
reason to route around it.

**The handoff is `tasks.md`, and it is never run flat.** Any flat executor over the task
list bypasses the per-task gates and the review-cluster stops — execute task by task
through the overlay below, whatever tool proposes to do the walking.

## Stage 2 — Execute (invoke `superpowers:subagent-driven-development`, or `superpowers:executing-plans` for sequential work)

The upstream skill owns dispatch and status handling. What Netdust adds depends on the lane.

### Placement — READ it from the plan, do not re-derive it (2026-09-04)

Dispatch answers *what* runs. Placement answers *where*, and the harness used to
skip it: every dispatch became a Task subagent, which runs in YOUR pane, YOUR
context and YOUR working tree. Right for most work, wrong for two cases, one of
which already cost a run — two implementers in one working tree, 14 and 17
phantom failures (2026-08-09).

**The plan decides this, not you.** `planning` writes `**Placement:**` on any
cluster that dispatches 2+ `[P]` tasks, and `bin/gate-check.py` refuses a plan
that omits it — so by the time you are here, the decision exists and has passed
the seam. Read it; do not re-derive it and do not overrule it.

**1. Before the cluster's first dispatch, read its placement line.**

```bash
awk '/^### Cluster/{c=$0} /^\*\*Placement:/{print c" -> "$0}' specs/<feature>/tasks.md
```

A cluster with a `worktree` placement means its `[P]` siblings each get their own
checkout. A cluster with no line has none that needed declaring — the gate would
have refused it otherwise — so its tasks are subagents here.

**2. What the plan cannot foresee, you place — and only these.** A plan is
written before the work; three things surface during it. This is the whole list:

| Surfaced during the run | Placement | Why |
|---|---|---|
| A gate or suite slower than you want to wait on | **its own pane**, same cwd, same branch | it reads and executes, so it cannot collide, and its output lands there instead of in your context |
| A bug in another repository (a `--prefer-source` package under `vendor/`) | **a worktree on THAT repo** | a subagent cannot have a different checkout at all; the PreToolUse guard will ask before the edit |
| A reviewer or watcher whose report is long | a pane | keeps the report out of your context; a short one stays a subagent |

Anything else is a subagent. If you find yourself wanting a worktree for a
reason not on this list or in the plan, the plan was wrong — say so and hand
back. Do not quietly re-place work the seam already approved.

**Outside herdr (`HERDR_ENV` unset) none of this exists: every dispatch is a
subagent, exactly as before, and a `**Placement:** worktree` line is satisfied by
running those tasks in SEQUENCE rather than concurrently.** That is the honest
fallback — the plan's constraint is "these must not share a tree", and one at a
time also satisfies it.

`netdust-devops:parallel-work` owns the rule behind that table — *does this need
a different checkout?* — and `skills/_shared/herdr-moments.md` maps each answer
onto its primitive. Cite them; do not restate them here.

**Syntax lives in `skills/_shared/herdr-moments.md`**, which carries the two
recipes verified against herdr v0.8.2 — the gate-in-a-pane (one blocking
`wait-output` that returns the output, no polling) and `herdr worktree create`.
Read it rather than reconstructing the flags; `herdr --skill` is the authority
if it has moved.

One trap worth knowing before you write a sentinel: the pane's text includes the
command line, so `--match 'GATE-EXIT='` matches the echo of the command that
will produce it and returns early. Anchor it — `--regex '^GATE-EXIT=[0-9]+'`.

**Three rules that make placement safe rather than clever:**

1. **`--no-focus`, always.** Placement must never move the operator's cursor
   mid-run. Then TELL them the pane exists — they will not find it otherwise.
2. **Read the result from the artefact, never from the pane's pixels.** A gate's
   verdict is its exit code and its suite output; a worktree dispatch's result is
   what is committed in that worktree. `pane read` is for showing a human.
3. **Placement never changes the contract.** A dispatch in a pane still owes the
   same `HARNESS-EVIDENCE:` close-out line, and `hooks/subagent-stop.py` still
   governs a subagent close. Moving work does not exempt it.

If a placement call fails — herdr not running, a flag this file got wrong — fall
back to a subagent and say so. A failed placement is a finding to file, never a
reason to skip the dispatch.

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
  reinvented solutions). **On a WordPress project, or any package that consumes
  ntdst-core, `netdust-wp:ntdst-drift-reviewer` sits on EVERY panel — LIGHT, STANDARD and
  FULL, and the branch review — not only at shake-out** (Stefan's ruling 2026-09-03, after
  six approved tasks built plain WordPress on top of the framework). The author never
  reviews its own diff; escalation to FULL is one-way. Record the verify-budget telemetry line
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
   (herdr-moments). Then finish: `make finish` on a `site.yml` project (devops), else
   `superpowers:finishing-a-development-branch`.
3. Report the whole-branch verify-budget line with the summary. Then invoke `compounding`
   — the learning loop: what the spec taught lands in CODE-MAP / skill lessons / evals as
   approved proposals.

## Armed loop

`/loop` + `hooks/loop-gate.py` may drive Stage 2 unattended: the ledger
(`bin/loop-check.py`) derives FINISHED from checked boxes PLUS green evidence, never
assertion. The loop changes nothing above — gates apply exactly as written.
