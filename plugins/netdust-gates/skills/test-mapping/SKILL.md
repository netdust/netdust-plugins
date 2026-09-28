---
name: test-mapping
description: Use while writing a plan, after the threat model and before the tasks — produces the plan's `## Test map` (one row per unit: seam · tier · file · command · e2e flows) and cuts the tasks to those units. Invoked by netdust-gates:policy. Not for writing tests; `netdust-wp:wp-testing` owns how.
---

# Test mapping — the units and what proves them

Produce `## Test map` in the plan BEFORE the tasks. It is the plan's one answer to "where are
the tests and what do they test"; every consumer (`Review Focus`, `plan-reviewer`,
`shakeout-qa`, the threat model) reads it, and none re-decides it.

## The table

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| BookingService | `POST /ntdst/v1/bookings` | integration · `tests/Integration/BookingTest.php` · `ddev composer test:int` | book-table, booking-denied-without-nonce |
| Booking admin list | `wp-admin?page=bookings` | none — proven by flow | staff-sees-today |

- **Unit** — one thing a single test run can judge: a service or module together with what it
  needs to be judged. A unit that needs another unit's code to be judged is one unit.
- **Seam** — what a caller uses: a route, a render, a public method. Never a private one.
- **Tests** — the tier by one question: does this unit encode a rule THIS project chose (a
  window, a role, a price, a parse of guest input), or is it configuration over a framework that
  already carries the rule (a CPT, a field map, a template)? The first gets a behavioural test
  through its seam — integration when it needs WordPress or the database, unit otherwise. The
  second gets `none — proven by flow`. Every data flow's denial (the refused actor, the missing
  nonce) is a test in its unit's row, written RED first. A scaffold reads `scaffold — deleted by
  task N`. Runners, layout and what a test owes: `netdust-wp:wp-testing`. Edges: `edge-classes.md`.
- **E2E flows** — the flows a person drives, by name. `shakeout-qa` drives exactly these through
  the real browser or the un-mocked wire and commits them. The implementer never drives its own.

## The unit cut

A task is one row. It writes the unit and its tests in one pass, runs the row's command, then
`make gate`, quotes both in its report, and commits. No RED-first step inside a unit except the
denial test; RED-first also holds for every fix in the Close's fix pass. A row with an empty tests
cell is the plan saying that unit is unverified: fill it or say so. Order rows by the named ask,
riskiest first.
