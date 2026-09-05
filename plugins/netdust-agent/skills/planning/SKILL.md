---
name: planning
description: The PLAN overlay — superpowers does the planning; this adds the netdust gates and stops at the seam (an approved tasks.md with gate-check GREEN). Use for Class A features and Class B freshness reviews of existing plans. Triggers on "plan a feature", "write a plan for X", "spec this out". NOT for executing — that is `building`.
---

# Planning — the netdust overlay on superpowers

**Superpowers is the workhorse. This skill adds netdust gates around it and STOPS at the seam.** It never dispatches a task and never writes implementation code.

```
superpowers:brainstorming → spec  →  superpowers:writing-plans → plan + tasks
                    + the netdust gates below, checked by bin/gate-check.py
────────────────────────── THE SEAM ──────────────────────────
tasks.md exists · gate-check.py exit 0 · human approved  →  `building` takes over
```

## Stage 0 — Brainstorm (invoke `superpowers:brainstorming`)

Actually invoke it — its job is interrogating user intent, which is what prevents invented
requirements. The spec it produces lands at `specs/<feature>/spec.md`. Netdust adds ONE
rule on top: **every FR carries a `Source:` line** — a quote from the ask, or
`invented — approved <date>`. An invention nobody approved is an open question for the
human, never a default you pick (checked: `check_fr_sources`). The invocation itself is
machine-enforced: creating `spec.md` without `superpowers:brainstorming` in the session
transcript is denied by the PreToolUse guard (the upstream-invocation floor).

On WordPress work the stack sub-plugin's design skills (architecture / data / patterns)
own the *technical* shape — but they never replace the INTENT interrogation: the open
decisions (payment? stock? who sees what?) go to the human as explicit questions BEFORE
the spec is written, and their rulings are recorded in the spec (the record-shop spec's
`## Intent decisions` table is the reference shape). Skipping the questions because the
stack skills "replace brainstorming" is the loophole this sentence used to allow.

## Stage 1 — Plan (invoke `superpowers:writing-plans`)

Write the reasoning to `specs/<feature>/plan.md` and the executable list to
`specs/<feature>/tasks.md` — two files, no duplicated task list. (Creating either
without `superpowers:writing-plans` invoked is denied by the same guard floor.) **The grammar is defined
by `bin/gate-check.py` and nowhere else** — read its findings, not a template. What the
gates require, beyond upstream's own craft:

- **Threat model** (`## Threat model`) — required when the spec flags a security surface:
  user-controlled URLs, auth/session/token, untrusted parsing, stored credentials,
  tenancy boundaries, outbound-to-user-supplied addresses. Named assets → attacks →
  mitigations, BEFORE task breakdown; it becomes the review convergence target. A Class D
  ad-hoc security edit runs this on the diff. Proactive or it didn't count
  (calibrations: `drop-workspace-retrofit`, `class-d-gap`).
- **Architecture invariants** (`## Architecture invariants touched`) — cite the
  convergence points the work touches from `ARCHITECTURE-INVARIANTS.md`; author that doc
  first if the work touches tenancy/authorization and it doesn't exist.
- **Premise ground-truth** (`## Spec-premise ground-truth`) — every "reuse X for Y"
  premise is read against X's real source before the plan ships (`tableview-premise`).
- **Stakes** (`## Stakes`) — `high | standard | low` by blast radius of a failure, never
  by which functions appear in the diff; per-cluster refinement when clusters genuinely
  differ. Downstream verification scales against it; no run-time agent re-decides it.
- **First working version** (`## First working version`) — names the task (within the
  first 3, producing at least one non-test file) after which a human can SEE or RUN
  something, and the command/URL that shows it (`check_deliverable_first`; calibration:
  `deliverable-last` ×3).
- **The lane, per cluster** (`Lane: behaviour | contract`, checked by
  `check_cluster_lanes`) — ask of each cluster: *does a task here encode a rule THIS
  project chose (a role, a window, an ownership test, a threshold, untrusted parsing,
  money, a migration), or is it configuration over a framework that already has the
  rule?* The second is **`Lane: behaviour`** — the default, and the honest lane for CPTs,
  field maps, templates and services wired onto ntdst-core: the cluster carries the full
  behaviour block (`Behaviour:` / `Observable:` / `RED until: <test>` — one RED,
  observable from OUTSIDE the file: a URL and status, a command and output, a query
  count, never a config/array shape), an `Integration gate:` line, and members that
  carry ONLY `(files:)`. No tier, no `Test-author:`, no `Proven by:`, no contract line,
  no `── REVIEW GATE ──`; the file ends at one `── BRANCH REVIEW ──` marker with a tier.
  The checker refuses `behaviour` on a member touching a security-boundary path or under
  `high` stakes — put that task in its own **`Lane: contract`** cluster (state the reason
  after a dash: `Lane: contract — encodes the return window`).
- **Task shaping, contract lane** — every task: tier (`[Tier A|B]`), `Test-author:` mode
  (split only for Tier-A security-boundary work at effective-high stakes), `Proven by:`
  evidence rung, a test contract line, `(files:)`. Clusters ≤4 tasks, each closed by an
  `Integration gate:` line and a `── REVIEW GATE ──` marker with a provisional tier.
  A contract cluster may also declare a behaviour block; member tasks may then state
  `covered by cluster behaviour` (`behaviour-cluster` check).
- **Acceptance flows** (`## Acceptance flows`) — required when the spec flags a
  user-facing surface: one row per intended flow, edges enumerated (empty, denied,
  re-entry, concurrent, boundary, mid-flow failure). Stage 3 drives this matrix.

Do not copy the shape of an existing `tasks.md` in the project: an earlier plan is a
snapshot of the harness version that wrote it, and plans before 0.21 carry no `Lane:`
and read as all-contract. The grammar is `bin/gate-check.py` and this file
(`lessons.md`: *An older tasks.md in the project is not the grammar*).

Order clusters by the named ask, riskiest first — when a session dies mid-plan, what
survives must be the thing that was asked for.

### Two fields the plan owes the executor (2026-09-04)

The plan already decides reviews, tiers, lanes and batching. Two more decisions
belong here rather than being improvised at dispatch time, because the planner
has the information and `gate-check.py` can check an artifact — a skill is only
advice the executor may skip.

**`**Placement:**` on a cluster that dispatches 2+ `[P]` tasks.** `[P]` says the
controller MAY run those concurrently; the default dispatch is a Task subagent,
which runs in the controller's own working tree. Two implementers in one tree
is not a hazard to weigh — it happened on 2026-08-09 and produced 14 and 17
phantom test failures. Declare the isolation:

```
### Cluster C2  (3 tasks · provisional tier: STANDARD)
**Placement:** worktree — T05 and T06 both edit, and share a suite
```

Only the dangerous direction is enforced. Nothing asks for a placement on a
single `[P]` task, on sequential work, or anywhere else, and the executor may
still move any dispatch to a pane it did not plan to — a gate that refused over
a placement guess would teach everyone to write `worktree` everywhere. A
cluster whose `[P]` tasks are all `[x]` is finished and never asked.

**`## Deploy`, when tasks create a custom plugin or theme.** `deploy.payload` is
a CLOSED list: a path missing from it deploys as an EMPTY DIRECTORY, and a
rollback `--delete`s it off the server. A plan that creates one and never says
so produces code that passes every gate and ships nowhere.

```
## Deploy

- **Payload:** + `app/plugins/ntdst-booking` — add to `deploy.payload` in site.yml
- **Non-git steps:** re-import the seed widgets after the first deploy
```

The second line matters as much as the first: anything git does not carry — a
gitignored build artifact, a database change, widgets — must be re-applied on
the target in the same sitting, or the environment ships half-updated.

This one **warns, never blocks**, and the difference from placement is the
point. Placement is an invariant the gate can prove from the artifact: two open
`[P]` tasks share a tree, definitively. "Is this plugin NEW?" is a guess — a
plan touching `content/themes/yootheme/` is reading the licensed parent theme,
gitignored and installed per host, not adding a payload path. A gate that
refuses plans over a guess gets routed around, and takes the real invariants
with it.

`netdust-devops:parallel-work` owns the placement rule; `netdust-devops:devops`
owns the payload one.

## Stage 1.5 — The machine check

```bash
python3 <plugin>/bin/gate-check.py specs/<feature>
```

Exit 0 or fix the artifacts and re-run. No checklist substitutes; `building` re-runs this
at entry. Then read spec/plan/tasks against each other once for what no script judges:
does the task citing FR-2 actually satisfy it; does any task invent scope; do two FR/SC
lines ask for the same thing twice; does a vague adjective (*fast, secure, robust*) stand
where a threshold should be; does one concept wear two names across the three files. Fix
in the artifact or hand back — never carry a finding into Stage 2 as a mental note.

## The seam — STOP

Present: plan path, tasks.md, the gate-check verdict, cluster lanes and tiers, `[HUMAN]`
yield points. Under herdr (`HERDR_ENV=1`) present them where the operator reads: one
`spec` tab in the project's workspace, unfocused, paging `plan.md` and `tasks.md` with the
verdict, and SAY the tab exists (`skills/_shared/herdr-moments.md`, seam row). Do not
dispatch anything, do not invoke `building` — the human bridges the seam.
Class B (existing/external plan): run the gates against it as a freshness review,
reconcile code samples against current source, then the same seam.
