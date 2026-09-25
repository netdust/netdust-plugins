---
description: Close a user-facing change — make gate, shakeout-qa drives the artifact and writes the manifest, bin/shakeout-check.py must exit 0, the human sees one screenshot per surface. Then the whole-branch review per the netdust-gates:policy close.
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent", "Write", "Edit"]
---

Run the close for `specs/<feature>/`. Four steps, in order — after one read.

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
   admin screens and shortcodes the branch touched. None user-facing: say so and go to Step 4.
2. Explore only those surfaces on the running dev site (`superpowers-chrome:browsing`, or the
   Playwright planner against those URLs).
3. Write `specs/<feature>/flows.md`: one line per flow — surface, what a person does, what they
   should see — with its edges from `edge-classes.md`.

**Stop.** Show Stefan the list. He confirms, strikes or adds; the file is edited to what he
approved. Only then Step 2, with `flows.md` as the flow source.

## Step 2 — Drive the artifact

Dispatch **`shakeout-qa`** on the most capable available model for the flows: it derives the
flow list from the spec and the plan's `Review Focus`, or `flows.md` on a branch with no spec, drives each through its faithful layer
(browser for UI, un-mocked wire for backend), commits the flows as tests, and writes
`specs/<feature>/shakeout.md` with a screenshot under `specs/<feature>/shakeout/` for every
browser pass — and registers what it leaves in `specs/CHECKS.md`: the driven flows as `@e2e`
(`make e2e env=staging` re-runs them after every deploy) and a read-only `@smoke` spec per
surface (`make smoke`, production too). It reports the
flow list it derived; read it for what is missing.

A change with no user-facing surface has nothing to drive: say so and go to Step 4.

## Step 3 — The manifest gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/shakeout-check.py" specs/<feature>
```

On exit 1: each `fail` row is one fix, RED→GREEN; re-dispatch `shakeout-qa` for the affected
flows; re-run the check until it exits 0. Nothing after this runs while it fails.

## Step 4 — The screenshot yield, then the branch review

Show Stefan one screenshot per surface — the PNGs the manifest's browser rows name, never a
per-flow slideshow. Beside them list every `✓ [shakeout-accepted]` row the check printed:
`Accepted-by-human:` is agent-writable, so one Stefan did not write is reverted and its row
re-driven. This is a stop; wait for him.

Then the whole-branch review (`superpowers:requesting-code-review`, a fresh reviewer) and the
single fix pass exactly as the `netdust-gates:policy` Close section states them, and `superpowers:finishing-a-development-branch`. Report the
manifest, the review verdicts and every `Ruling:` from the ledger together.
