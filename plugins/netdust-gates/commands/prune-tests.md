---
description: Audit a project's tests on demand — every suspect test gets DELETE, REWRITE, KEEP or DELETE-CONFLICT against the behavioural bar, with evidence, and a fresh reader spot-checks the verdicts. Reports only. Nothing is deleted until Stefan approves.
argument-hint: [path or suite — the whole suite when empty]
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Write", "Agent"]
---

Audit the tests under `$ARGUMENTS` (every test directory when empty). You coordinate; you do
not judge tests yourself, and this command edits no test.

## Step 1 — Slice

List the test files in scope with their line counts (skip `vendor/`, `node_modules/`, the
framework's own `mu-plugins/*/tests`). Cut them into slices of about 8,000 lines, keeping one
subject together — a feature's files, a vendor package's tests, the e2e specs. Name the
governing sources once: `ARCHITECTURE-INVARIANTS.md`, `specs/*/`, the project `CLAUDE.md`, and
the upstream specs of a forked project.

## Step 2 — Dispatch `test-pruner`, one per slice, in parallel

Each gets the repository root, its file list and the governing sources. Wait for all of them.

## Step 3 — Spot-check

Dispatch a fresh general-purpose agent, read-only, on 15–20 claims chosen where a wrong call
costs most: DELETEs justified as "duplicate", "covered upstream" or "dead code", every
"cannot fail" finding, and three DELETE-CONFLICTs. It returns CONFIRMED / PARTLY / REFUTED
with `file:line`. Apply its corrections: a REFUTED or PARTLY DELETE becomes a REWRITE or gains
an "assertions to move" line.

## Step 4 — Reconcile, file, stop

Settle rulings that differ between slices (one rule, applied to both), and check every
"covered by X" against X's own disposition. Write `specs/test-prune/<YYYY-MM-DD>.md`: totals,
the DELETE-CONFLICT table with quoted lines, the KEEPs and REWRITEs with their evidence, the
DELETEs grouped by file, assertions to move, dead support code, the spot-check result, and
findings outside the brief. Show Stefan the totals, the conflicts and the questions only he
can answer, and give the path.

**Stop there.** Stefan approves dispositions — per group, per conflict. The cleanup that
follows is a code change and enters through `netdust-gates:policy`: move the named assertions
first, each REWRITE RED→GREEN through its new seam, each conflict converted to its
`ARCHITECTURE-INVARIANTS.md` grep before its test goes, then `make gate`.
