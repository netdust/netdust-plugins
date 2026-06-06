---
description: Prove a user-facing feature actually behaves the way it's meant to be used — every intended flow with edge/error/empty/concurrent cases — by driving it through the real browser AND the API layer, not just unit/integration tests. Authors an `## Acceptance flows` matrix at plan-time; drives that matrix at shake-out, emitting a pass/fail/not-reachable manifest. Sibling to test-effectiveness (code-bite) — this is feature-behavior.
argument-hint: [author | verify | <feature-or-flow-that-broke>]
allowed-tools: Skill(feature-acceptance)
---

Invoke the `feature-acceptance` skill.

- `author`, or invoked while writing a plan/spec → situation A: derive the intended-use flows from the spec and embed an `## Acceptance flows` matrix in the plan — one row per flow, each with a MANDATORY enumeration of the six edge classes (empty/zero state, denied actor, wrong-order/re-entry, concurrent/double, boundary value, mid-flow failure). A flow with no edges is an incomplete row.
- `verify`, or no argument at spec-complete → situation B: drive each flow + edge through its faithful layer (real browser for UI — Playwright spec or `use_browser` against the running dev server; un-mocked wire for backend). Emit the `pass`/`fail`/`not-reachable`/`unverified-no-browser` manifest. No UI flow is `pass` without a browser driving it.
- A description of a feature/flow that broke in use despite a green suite → situation C: reconstruct the flow + edge that broke (almost always an un-driven edge), add it to the matrix, drive it RED-first, fix, then sweep sibling flows for the same edge class.

Context / target: $ARGUMENTS
