# netdust-agent — the overlay on superpowers

One idea, decided 2026-08-10 (the re-thinning):

> **Superpowers is the workhorse.** It brainstorms, plans, writes tests-first code,
> reviews, and finishes branches. **netdust-agent guides and gates that work** — it adds
> netdust best practices to each superpowers stage and verifies them mechanically. It
> never replaces upstream content; a netdust skill that restates superpowers is a defect
> (that drift is how 27 skills and 3,900 lines accumulated by 0.17).

## The eight skills

| Skill | Adds to | What it adds |
|---|---|---|
| `harnessed-development` | intake | the class dial (A–F, priced by open decisions) + the stakes dial; routes, does no stage work. |
| `planning` | `superpowers:brainstorming` + `writing-plans` | the plan-time gates: Source: per FR, threat model, invariants, ground-truth, stakes, deliverable-first, task shaping, behaviour clusters — all checked by `bin/gate-check.py`; stops at the seam |
| `building` | `superpowers:subagent-driven-development` / `executing-plans` + `test-driven-development` | the seam precondition, ground-truth per dispatch, the evidence contract the stop hook parses, feature tests after each cluster, review gates with independent reviewers |
| `testing-workflow` | `superpowers:test-driven-development` | the tier decision (A/B, evidence ladder) and the WP runners — Brain Monkey / wp-phpunit via the netdust-wp-manager template, which superpowers doesn't know |
| `threat-modeling` | `planning` | the trigger list + the `## Threat model` section shape |
| `architecture-invariants` | `planning` / review | the convergence-point doc shape reviews check bypasses against |
| `compounding` | spec-close | the learning loop: session lessons land in CODE-MAP + skill lessons + evals as approved proposals — how the agents and skills improve |
| `convergence` | resumed/stalled work, pre-`/shakeout` | the spec-completeness question no other gate asks: code read against `specs/<feature>/`, gaps (missing/partial/contradicts/unrequested) appended to `tasks.md` as a PROPOSED phase behind gate-check + the seam; `unrequested` hands off to `invariant-auditor`; `/converge` |

## Agents (7)

`implementer` (greens tasks, TDD), `test-author` (feature tests after each task group;
rare pre-task RED on split tasks), `reviewer` (whole-diff generalist),
`security-sentinel`, `code-simplicity-reviewer`, `invariant-auditor` (the no-drift
agent: convergence-point bypasses AND reinvented solutions, against
ARCHITECTURE-INVARIANTS.md + CODE-MAP.md — restored 2026-08-10 after its transcript
record proved it out), `shakeout-qa` (drives the artifact).
Reviewers ship without Edit/Write — a finder can never quietly become the fixer.

## The machine layer (the part that is NOT prose)

- `hooks/` — SessionStart memory injection, Stop-hook tag capture, PreToolUse guard,
  `subagent-stop.py` (blocks a code-editing close whose suite didn't run or exited
  non-zero; sensitive-path floor), `loop-gate.py` (armed `/loop`).
- `bin/` — `gate-check.py` (the single definition of the spec/plan/tasks grammar),
  `loop-check.py`, `run-trace.py`, `run-score.py`, `run-cost.py`, `verify-budget.py`
  (telemetry line, never a HALT — decision 2026-08-09).
- `tests/` — `bash plugins/netdust-agent/tests/run.sh`, 22 self-runner modules. The
  hooks and scripts are tested code; keep it that way.

## Evals

Every skill ships with eval cases (`evals/`): test prompts + assertions that a session
following the skill produces the required artifacts. A skill edit without a passing eval
doesn't ship — skills get the same RED-first discipline as code.

## Commands

`/shakeout` (spec-complete gate), `/integration` (group gate), `/converge`
(spec-completeness gate), `/loop`, `/deploy`, `/skill-audit`, `/evaluate`,
`/architecture-invariants`.
