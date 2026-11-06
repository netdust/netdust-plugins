---
description: Drive a user-facing change — make gate, shakeout-qa drives the artifact, proves each new test on the base and writes the manifest, then make shakeout (bin/shakeout-check.py) must exit 0. The review and its fix pass came before it; the report and Stefan's read follow it (netdust-gates:policy Close).
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent", "Write", "Edit"]
---

Run the shake-out for `specs/<feature>/`. Three steps, in order — after one read; what follows
them is the policy's Close, steps 5-9.

## Step 0 — The registry

Read `specs/CHECKS.md` if it exists: every surface this project has shipped, its `@e2e`
flows and its `@smoke` check. A surface the branch diff touches is re-driven in Step 2
alongside the new flows, and its `verified` cell bumped — a registered check that now fails
blocks the close like a new one. The registry is what `make e2e env=staging` and
`make smoke env=<env>` run after a deploy. This shake-out writes the checks for one feature;
`make e2e env=staging` re-runs every one of them on the composition staging carries, and
`make ship` refuses a commit they have not passed on — that run is the gate.

## Step 1 — `make gate`

Run the project's own suite: `make gate`. It must exit 0. Exit 1 with "No commands.gate in
site.yml" means the project has no declared gate — declare it (`commands.gate`) as the first
fix, then run it; that is not a reason to skip.

## Step 1b — A branch with no spec: propose the flows, then stop

When `specs/<feature>/` holds no `plan.md` and no `spec.md` — a planned feature cut from a split
spec has a `plan.md` whose `**Spec:**` header names its spec, and takes the planned path — nothing
records what this feature should do except Stefan. Derive a proposal:

1. What changed: `git diff --name-only $(git merge-base origin/<production> HEAD)..HEAD` and
   `git log --format=%s` over the same range — the routes, templates, forms, REST endpoints,
   admin screens and shortcodes the branch touched. None user-facing: say so and go to the Close.
2. Explore only those surfaces on the running dev site (`superpowers-chrome:browsing`, or the
   Playwright planner against those URLs).
3. Write `specs/<feature>/flows.md`: one line per flow — surface, what a person does, what they
   should see — with its edges from `edge-classes.md`.

**Stop.** Show Stefan the list. He confirms, strikes or adds; the file is edited to what he
approved. Only then Step 2, with `flows.md` as the flow source.

## Step 2 — Drive the artifact

Dispatch **`shakeout-qa`** on the most capable available model for the flows: it drives the
flows the plan's `## Test map` names in its `E2E flows` column — or `flows.md` on a branch with no spec — each through its faithful layer
(browser for UI, un-mocked wire for backend), commits the flows as tests, and writes
`specs/<feature>/shakeout.md` with a screenshot under `specs/<feature>/shakeout/` for every
browser pass — and registers what it leaves in `specs/CHECKS.md`: the driven flows as `@e2e`
(`make e2e env=staging` re-runs them after every deploy) and a read-only `@smoke` spec per
surface (`make smoke`, production too). Each new test it commits is proven on the base with
`revert-run` (its log committed beside the screenshots, the row's `Test:` marker naming the test);
a re-driven row carries the marker only. It reports the flow list it drove; read it for what is
missing. With a browser flow it also runs the hunt, once — exploratory charters whose confirmed
bugs arrive as `fail` rows like any other. On a sliced plan each slice's flows are appended to the
one `shakeout.md`, and the hunt runs once, at the feature's end (an intermediate slice records
`Hunt: deferred — runs at the feature's end`).

A change with no user-facing surface has nothing to drive: say so and go to the Close.

## Step 3 — The manifest gate

`make shakeout name=<feature>` when the project declares `commands.shakeout` (netdust-devops);
without the verb, the checker by path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/shakeout-check.py" specs/<feature>
```

On exit 1: each `fail` row and each `✗ [shakeout-revert]` is one fix, RED→GREEN, in the policy's
shake-out fix round; re-dispatch `shakeout-qa` for the affected flows and run the check again.
`✗ [shakeout-hunt]` is not a row: re-dispatch `shakeout-qa` to record the hunt, or why it could
not run. Nothing after this runs while it fails; a row still refused after the round is the
policy's stop, Stefan's `Accepted-by-human:` or a sharper test.

## Then the Close

The review and its fix pass came before this shake-out; what remains is the `netdust-gates:policy`
Close, steps 5-9: the fix round, `make report name=<feature>`, the final `make gate`, Stefan's read
of `report.md` — the screenshots, every `Accepted-by-human:` row, the hunt's `not ours:` and
`rejected:` lines — and `superpowers:finishing-a-development-branch`: on a project with `site.yml`,
push and run `make promote name=<feature>` under his standing OK (it finds the saved review); a
feature never merges into production by hand. Report the manifest and every `Ruling:` from the
ledger together.
