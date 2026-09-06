---
description: Spec-complete gate. Run when all task groups in a spec are done — before merging the branch. Five steps in order — suite + telemetry; shakeout-qa drives the artifact, writes specs/<feature>/shakeout.md and commits the flows it drove as tests; gate-check.py --shakeout must exit 0 (fix, re-drive, re-check) before anything else runs; the human is shown one screenshot per surface; then the reviewer panel on the full branch diff, panel size set by the branch tier (table in Step 5).
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent"]
---

Run the **spec-complete gate** — the pre-merge sweep that uses the artifact instead of
trusting the suite. Five steps, in order (artifact-gate FR-7).

## Step 1 — Suite + telemetry

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

## Step 2 — Exercise the artifact (only when `## Acceptance flows` is not N/A)

A plan whose acceptance-flows matrix is N/A has no user-facing surface to drive; say so
and go to Step 5 — a shake-out over nothing is a token sink, not a gate. Otherwise
dispatch **`shakeout-qa`** (model per `skills/_shared/model-ladder.md`): it drives the
plan's `## Acceptance flows` matrix through the faithful layer — UI flows through a real
browser (Playwright spec if present, else `superpowers-chrome`), backend flows through the
un-mocked wire — logging in with the plan's `## Shake-out access` recipe, and returns
with two things committed: `specs/<feature>/shakeout.md`, one row per acceptance row with
a screenshot under `specs/<feature>/shakeout/` for every browser pass, and the flows it
drove as tests (`browser` → a Playwright spec, `wire` → an integration test through the
project's runner), each named in its row. No UI flow counts as `pass` without a browser
having driven it.

## Step 3 — The manifest gate

```bash
python3 "$PLUGIN_DIR/bin/gate-check.py" --shakeout specs/<feature>
```

It enforces the manifest grammar `agents/shakeout-qa.md` defines under `## The manifest`
— four findings: `shakeout-manifest`, `shakeout-credential` (no override),
`shakeout-artifact-diff`, `shakeout-ruling` (a human `Ruling:` passes its row). On exit 1:
dispatch one `implementer` per `fail` row (one TDD cycle each, Class C), re-dispatch
`shakeout-qa` to re-drive the affected flows, re-run the check — and loop until it exits 0.
**The panel does not run while this fails.**

## Step 4 — `[HUMAN]` The screenshot yield

Show the human what the artifact looks like — one screenshot per surface, the PNGs the
manifest's browser rows name, never a per-flow slideshow. Under `HERDR_ENV=1` open them as
a `shakeout` tab per the screenshot-yield row in `skills/_shared/herdr-moments.md`; outside
herdr, Read each PNG inline. Skipped when Step 2 was skipped. The human looks before the
panel spends.

## Step 5 — The branch panel, then close by ledger

The branch tier is the `── BRANCH REVIEW ──` marker's when `tasks.md` carries
behaviour-lane clusters (an all-behaviour branch under non-high stakes is LIGHT), else
the branch's tier as planned. State it, then dispatch in parallel with fresh context
(the author never reviews its own diff; models per `skills/_shared/model-ladder.md`):

- **LIGHT** — `reviewer`.
- **STANDARD** — `reviewer` + `code-simplicity-reviewer`.
- **FULL** — those plus `security-sentinel` + `invariant-auditor` (when an
  `ARCHITECTURE-INVARIANTS.md` exists, else the stack's drift reviewer).
- On WordPress, `netdust-wp:ntdst-drift-reviewer` joins every branch panel.

Escalation is one-way: any finding on a security surface promotes to FULL. Reviewers
verify against the plan's `## Threat model` and `ARCHITECTURE-INVARIANTS.md` — named
targets, not free-form hunting.

Then close by ledger: Criticals become task lines closing on named checks; Importants
triage fix-now / park / reject (default park); a round with zero new Criticals CLOSES
review. One fix round; a second is a `[HUMAN]` ruling. Then
`superpowers:finishing-a-development-branch`, reporting the manifest, the panel verdicts,
and the ratio line together.
