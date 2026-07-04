# 2026-07-04 — Stage 2 test/dev split: independent test-author

## The flaw

The harness claimed testing was mandatory, gated, and performed by subagents.
The first two held; the third was misleading. The `implementer` subagent wrote
the code AND authored its own Tier-A test AND self-reported the Test-evidence
block that *was* the gate. RED-first reordered the same author's two acts but
did not remove the conflict: a coder who writes both sides grades their own
homework —

- the test drifts to fit the code it was written against,
- the denial/negative path quietly goes missing,
- a risky guard gets self-classified "Tier B, just wiring" by the very agent
  that benefits from skipping the test.

Independent verification existed only at phase-close (test-effectiveness,
shakeout-qa, the reviewer panel) — never at the per-task authorship altitude
where the test that gates the task is written.

## The decision

**Split test authorship/execution off the implementer into a dedicated
per-task `test-author` agent, dispatched BEFORE the implementer** (mechanism:
"test-author writes RED first" — the classic test/dev split, chosen over
test-after-verify because it preserves behavioral RED-first while removing
self-grading).

Per task, Stage 2 is now a hard-ordered pair:

1. **`test-author`** (independent, first) — classifies the risk tier from the
   acceptance criteria + threat model (not the code), writes the Tier-A
   RED-first behavioral test incl. the denial path, and proves RED. For a
   brand-new symbol it creates ONLY a minimal **signature shell** (declaration
   + sentinel body) so the RED is behavioral, not "module not found" — never
   the logic. For Tier B it records the `no unit test: Tier B, <reason>`
   justification (and the seam assertion at a wiring task). Commits the test as
   its own commit; reports `## Test contract` + `RED_READY`.
2. **`implementer`** (second) — greens that same test with real logic, WITHOUT
   editing, weakening, deleting, or skipping it. May ADD edge tests. If the
   test is wrong it escalates `NEEDS_CONTEXT` — it does not rewrite the test to
   pass. Reports Test-evidence with `Weakened? NO`.

The gate is the reconciled PAIR (independent RED + unweakened GREEN, two
commits). Applies to every code-writing class including Class E; the one narrow
exception is a trivial inline Class E, where the **controller** (not the coder)
authors the RED before dispatching the implementer.

### Enforcement honesty

- The `subagent-stop.py` hook still backstops both halves (a test command must
  have run) — but it CANNOT verify authorship independence (one invocation sees
  one transcript). Independence is **sequencer-enforced**: the controller's
  dispatch order + the two separate commits are the audit trail. Documented as
  such alongside the existing plan-time-gate honesty note.

## Files changed

Originally authored against the pre-split sequencer (`harnessed-development` as
the god-skill, v0.3.4 → 0.4.0). Main's plan/build refactor (0.5.0) landed in
parallel and moved Stage 2/3 into the `building` spine, so at merge the split
was PORTED into the new structure and shipped as **0.6.0**:

- **NEW** `agents/test-author.md` — the independent RED-authoring persona
  (owns the FRONT half of `building` Stage 2).
- `agents/implementer.md` — receives an immutable RED test; greens without
  weakening; evidence block cites the independent author + a `Weakened?` line.
- `skills/building/SKILL.md` — the split's home: `<test_dev_split>` section
  (slug `self-grading-split`); enforcement-honesty bullet; objective #2;
  precondition Class E row; craft-routing; stage-personas; pair dispatch order
  (Steps 2.1, 2.1b, 2.6, 2.7); split dispatch addenda (test-author +
  implementer); red-flags; success-criteria #3; integration + calibration.
- `skills/harnessed-development/SKILL.md` — unchanged from main's intake
  router; the split lives downstream in `building`.
- `skills/testing-workflow/SKILL.md` — flow diagram; "Who authors vs who
  greens" section; two anti-pattern rows; split sign-off checklist; integration
  bullets.
- `skills/writing-tests/SKILL.md` — reframed as loaded by the test-author;
  behavioral-RED-via-signature-shell for new symbols; success criteria +
  integration.
- `skills/_shared/calibrations.md` — new `self-grading-split` slug entry.
- `hooks/subagent-stop.py` — docstring only (logic unchanged; hook tests stay
  green) reflecting the two-agent backstop + the authorship-independence limit.
- `README.md` — agent-personas table (nine agents, five stage personas) + the
  split explainer; project-structure comment.
- `.claude-plugin/plugin.json` + root `.claude-plugin/marketplace.json` —
  version 0.5.0 → 0.6.0 + description clause.
