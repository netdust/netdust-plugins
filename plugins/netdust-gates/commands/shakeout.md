---
description: Close a user-facing change — make gate, shakeout-qa drives the artifact and writes the manifest, bin/shakeout-check.py must exit 0, the human sees one screenshot per surface. Then the whole-branch review per the netdust-gates:policy close.
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent"]
---

Run the close for `specs/<feature>/`. Four steps, in order.

## Step 1 — `make gate`

Run the project's own suite: `make gate`. It must exit 0. Exit 1 with "No commands.gate in
site.yml" means the project has no declared gate — declare it (`commands.gate`) as the first
fix, then run it; that is not a reason to skip.

## Step 2 — Drive the artifact

Dispatch **`shakeout-qa`** on the most capable available model for the flows: it derives the
flow list from the spec and the plan's `Review Focus`, drives each through its faithful layer
(browser for UI, un-mocked wire for backend), commits the flows as tests, and writes
`specs/<feature>/shakeout.md` with a screenshot under `specs/<feature>/shakeout/` for every
browser pass. It reports the flow list it derived; read it for what is missing.

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

Then the whole-branch review and the single fix pass exactly as the `netdust-gates:policy`
Close section states them, and `superpowers:finishing-a-development-branch`. Report the
manifest, the review verdicts and every `Ruling:` from the ledger together.
