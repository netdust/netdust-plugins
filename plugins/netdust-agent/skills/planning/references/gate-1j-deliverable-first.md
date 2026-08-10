# Gate 1j — deliverable-first (PROPOSAL, not yet implemented)

**Status:** proposal, awaiting a human decision. Nothing enforces this yet.
**Calibration:** `deliverable-last` (2026-08-03) — see `_shared/calibrations.md`.
**Proposed home:** `bin/gate-check.py` as `check_deliverable_first()`, fired at
Stage 1.5 alongside the existing plan-gate checks.

---

## The problem this closes

Two independent sessions, different specs, no shared context, same day, same
failure shape:

| Session | Asked for | Built first | Cost |
|---|---|---|---|
| A | a working content model | 12 gated tasks of declarative field maps | 290 min, 2077 impl lines behind 4651 test lines |
| B | a YOOtheme source bridge | plugin + boot proof + ordering proof | 3 commits, ~30 min, no bridge |

Session B's own commit message states it: *"ground-truth model-registration
ordering **before the bridge is built** (T03)"*.

**Neither session had built the thing that was asked for.** Neither chose
that; both followed the harness faithfully.

## Why it is structural, not a judgement lapse

Verified by grep, not asserted:

- `skills/planning/SKILL.md` contains **zero** occurrences of
  `end-to-end`, `vertical slice`, `runnable`, `demoable`, or `the user can`.
- The plan-writing gate mandates `## Threat model`, `## Acceptance flows`,
  `## Architecture invariants touched`, `## Spec-premise ground-truth`,
  `## Phases & review clusters`. There is no `## First working version`.

Every gate in the spine answers **"is this verified?"**. Nothing anywhere
asks **"is this useful yet?"** The gradient therefore points at proofs, and a
faithful agent walks up it.

### The compounding blind spot

`verify-budget.py` is a RATIO — test lines ÷ implementation lines. A task
producing **zero** implementation lines cannot fail it; three tasks of pure
test infrastructure score perfectly. Session A passed at 1.39×, 1.10× and
0.44× while burning four hours. The one machine check meant to notice
overspend reported healthy, because it was not measuring the expensive thing.

### Why prose will not fix it

`stakes-dial-ignored` records this same controller re-running the
`contact-page-8k` failure **four days after that fix shipped**, with the fix
installed, read, and restated verbatim in every dispatch brief. A prose
instruction to read a dial is not a branch in the control flow. This gate
must be machine-checked or it will not hold.

---

## The proposed check

### Plan requirement (new mandatory section)

`planning` Stage 1 must emit, before task breakdown:

```markdown
## First working version [GATE]

**Task:** T0n
**Demonstrates:** <one sentence: what a human can SEE or RUN once this lands>
**Verify by:** <the command, URL, or screen that shows it working>
```

`N/A` is permitted **only** for a plan whose deliverable is genuinely not
runnable software (a docs-only spec, a pure test-infrastructure spec). The
justification must name why, in the same shape as the existing `## Threat
model` N/A convention.

### Mechanical assertions

`check_deliverable_first()` FAILs when:

1. `## First working version` is absent and the spec's
   `## User-facing surfaces` is not `None of the above`.
2. The named task does not exist in `tasks.md`.
3. **The named task is not among the first 3.** Ordering is the whole point:
   naming a first-working-version task and scheduling it eighth changes
   nothing.
4. The named task's `(files: ...)` segment lists **only** paths under
   `tests/`. A task producing no non-test file cannot be a first working
   version. *(This is the assertion that catches both of today's plans.)*

WARN (not FAIL) when:

5. More than 2 tasks precede the named one — legal, but worth a human look.

### Why these are checkable

Every input already exists in the artifacts `gate-check.py` parses today:
the `(files: ...)` segment is already validated by `check_files_segment`, and
task ordering is already read by `check_review_cluster`. No new parsing
machinery is needed.

---

## What it would have done to today's two plans

**Session A (`josworld-core`)** — T01 is `josworld-coreloader.php` +
`josworld-core.php`: a loader pair that registers nothing and renders
nothing. T02 is a boot block. T03 is a test file. The first task producing
something an editor could SEE is **T05** (the `case` post type, with its
admin screen) — fifth. → **FAIL on assertion 3.**

Correct shape: T05 first, or merged with T01/T02 into one "register the case
model and see it in wp-admin" task. The loader is not a deliverable; it is
the first three lines of one.

**Session B (`yootheme-sources-baseline`)** — T03's files are
`tests/Integration/ModelRegistrationOrderTest.php`, test-only, and no bridge
task precedes it. → **FAIL on assertions 3 and 4.**

Correct shape: build the smallest bridge that renders one field in YOOtheme,
let the ordering constraint bite for real, then pin it. The ordering test is
not wasted — cross-plugin boot order is a genuine project fact that bit twice
that day — but written first it is a proof about a hypothetical integration,
and it gets rewritten if the bridge lands in a different shape.

---

## Deliberate non-goals

- **Not "test less".** Every real defect found on 2026-08-03 came from
  mutation-testing guards — the cheap technique — and none from the eight
  reviewer dispatches. This gate reorders work; it does not reduce
  verification.
- **Not anti-scaffolding.** A loader must exist before a service loads. The
  claim is that scaffolding belongs *inside* the first deliverable task, not
  ahead of it as tasks of its own with their own test contracts.
- **Not a replacement for the stakes dial.** `stakes-dial-ignored` governs
  how much ceremony a task buys. This governs what ORDER tasks come in. They
  are orthogonal and both failed on the same day.

## Open questions for the human

1. Is "first 3 tasks" the right threshold, or should it be strictly task 1?
2. Should the check be FAIL or WARN on first introduction? A FAIL on legacy
   plans authored before the gate would block work; the `legacy-artifact`
   waiver convention already exists in `tasks.md` for exactly this.
3. Does `## First working version` belong in the SPEC (Stage 0.5) instead —
   arguably the human should name the first demoable slice, not the planner.
