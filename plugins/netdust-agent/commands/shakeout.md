---
description: Spec-complete gate. Run when all task groups in a spec are done — before merging the branch. Exercises the built artifact (shakeout-qa), then dispatches the reviewer panel on the full branch diff, panel size set by the branch's review tier (FULL = reviewer + security-sentinel + code-simplicity, STANDARD = reviewer + code-simplicity, LIGHT = reviewer alone).
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent"]
---

Run the **spec-complete gate** — the pre-merge sweep that uses the artifact instead of
trusting the suite. Steps, in order:

## Step 1 — Integration + telemetry

Re-run the full test suite(s) against the branch (the project's real runners — on WP the
netdust harness: `composer test:unit`, `ddev composer test:int`, or `composer gate`).
Any regression against the recorded baseline blocks the gate. Then print the ratio line
(never blocking):

```bash
PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$PLUGIN_DIR/bin/verify-budget.py" specs/<feature> --base "$(git merge-base HEAD main)" || true
```

Fold the `verify-ratio:` line into the final report — observability, not a gate
(decision 2026-08-09).

## Step 2 — Exercise the artifact

Dispatch **`shakeout-qa`**: it drives the plan's `## Acceptance flows` matrix through the
faithful layer — UI flows through a real browser (Playwright spec if present, else
`superpowers-chrome`), backend flows through the un-mocked wire — and returns a
pass/fail/not-reachable manifest with reproducible failing payloads. No UI flow counts
as `pass` without a browser having driven it.

## Step 3 — The reviewer panel, on the full branch diff

State the branch tier, then dispatch in parallel with fresh context (the author never
reviews its own diff):

- **FULL** (any security surface, invariant, or data-layer/migration touch): `reviewer` +
  `security-sentinel` + `code-simplicity-reviewer` (+ the stack's drift reviewer on WP).
- **STANDARD**: `reviewer` + `code-simplicity-reviewer`.
- **LIGHT** (doc/config only): `reviewer` alone.

Escalation is one-way: any finding on a security surface promotes to FULL. Reviewers
verify against the plan's `## Threat model` and `ARCHITECTURE-INVARIANTS.md` — named
targets, not free-form hunting.

## Step 4 — Close by ledger, then finish

Criticals become task lines closing on named checks; Importants triage fix-now / park /
reject (default park); a round with zero new Criticals CLOSES review (hard cap two
rounds). Then `superpowers:finishing-a-development-branch`, reporting the bug manifest,
the panel verdicts, and the ratio line together.
