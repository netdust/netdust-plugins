---
name: writing-tests
description: "CRAFT skill — layers the Netdust harness contract ON TOP of superpowers:test-driven-development. Reached for by the testing-workflow gate once it has ruled a task Tier A. Use when you are about to write a test: it sends you to superpowers:TDD for the generic RED→GREEN→REFACTOR mechanics (AAA, test pyramid, state-over-interactions, Real>Fakes>Stubs>Mocks), then adds the things superpowers cannot know — that you are downstream of the testing-workflow gate, the Tier-A denial-path contract, the un-mocked-seam rule, the ≥3× determinism rule, and assert-from-acceptance-criteria. Does NOT decide WHETHER a test is needed or at what tier (that is the testing-workflow gate) and does NOT restate the generic TDD cycle (that is superpowers). Covers PHP (PHPUnit/Codeception) and TypeScript (Vitest/Playwright)."
---

<objective>
This skill does NOT teach you how to write a test from scratch — `superpowers:test-driven-development` already does that, and does it well. This skill **layers the Netdust harness on top of it**: the conventions, the gate position, and the contracts superpowers has no way to know about.

Think of it the way `harnessed-development` relates to the superpowers process skills: superpowers owns the generic craft; the Netdust skill sequences it and adds the gate. Here, superpowers owns the RED→GREEN cycle; this skill adds the harness contract around the single test you're about to write.
</objective>

<first_load_the_base>
**Before writing anything, invoke `superpowers:test-driven-development`.** It owns the generic mechanics, and this skill deliberately does not duplicate them:

- the RED → GREEN → REFACTOR cycle (write the failing test, watch it fail, minimal pass, then refactor green)
- Arrange → Act → Assert structure
- assert **state/outcomes, not interactions** (no `toHaveBeenCalled` brittleness)
- the test pyramid + test sizes (Small/Medium/Large)
- double selection — **Real > Fakes > Stubs > Mocks**
- DAMP-over-DRY readability; name tests by behavior

If superpowers is not installed, those mechanics are the prerequisite — get them there, not here. This skill assumes you have them and adds the layer below.
</first_load_the_base>

<where_you_are>
You did not arrive here freely. The **`testing-workflow` gate** sent you, having already classified this task as **Tier A** (real branching logic, a security/auth/scope guard, untrusted-input parsing, a state machine, or a migration) — or handed you a **seam test** to write at a wiring task.

- If you have NOT been through the gate, stop and load `testing-workflow`. Writing a test the gate would have called **Tier B** (a pass-through, a classname-only render, an enum→label map) is itself the anti-pattern — superpowers' generic enthusiasm for "test everything" is exactly what the gate exists to temper.
- The gate decides *whether* and *at what tier*. This skill is the *how* for the test it asked for. **The gate owns the sign-off** — you hand the finished test back to it.
</where_you_are>

<what_superpowers_cannot_know>
These are the Netdust-specific contracts to apply on top of the generic cycle. Superpowers has no knowledge of your harness, so it cannot enforce any of them:

**1. The RED must be BEHAVIORAL, not "module not found."**
Superpowers says "watch it fail." The Netdust gate is stricter about *why* it fails. A `cannot find module './guard'` failure is not Tier-A RED — it is the litmus that the unit might be Tier B. Tier-A RED looks like `expected 403 for a member, got 200`: the *contract* is absent, not merely the file.

**2. Assert the CONTRACT from the acceptance criteria — and for any guard, the DENIAL path.**
Derive the assertion from what the task promised the caller (the acceptance criteria / the threat-model mitigation), never from the code you just wrote. For a security/auth/scope guard this is non-negotiable: the test must assert the **actor who is refused**, not only the actor who is allowed. A guard with only a happy-path test has no Tier-A test.

**3. Do not mock the seam you are wiring.**
If the task wires a route→handler, a client→server contract, or a reactor/trigger path, at least one assertion must cross the **un-mocked** boundary. Mocking the already-filtered server response and asserting on it lets both sides pass while the wire silently leaks — a real defect class in this project. (The gate calls this the seam test: one un-mocked-chain assertion + one negative/adversarial case.)

**4. ≥3× determinism for anything touching time/ordering/concurrency.**
If the unit touches a clock, ordering, concurrency, or a timestamp comparison, a single green run is not evidence — this project shipped a same-millisecond race that passed once by scheduling luck. Run the new/changed test file **≥3×**, green every run, before reporting done. Condition-based waits only; never `sleep(n)`.

**5. Stay at your altitude.**
This skill writes ONE Small (unit) test for the gate's Tier-A contract. Cross-task interaction is the phase gate's job; whether the *whole suite* would go RED is `test-effectiveness`; whether the *feature* behaves through the real browser/API is `feature-acceptance`. Do not pull a Large e2e test down to this altitude.
</what_superpowers_cannot_know>

<run_commands>
**TypeScript (Vitest):**
```bash
npx vitest run src/path/to/file.test.ts   # the file first
npx vitest run                              # then full suite for regressions
```

**PHP (PHPUnit):**
```bash
vendor/bin/phpunit --filter=TestClassName
vendor/bin/phpunit --testsuite=unit
```

**PHP (Codeception unit):** `vendor/bin/codecept run unit TestClassCest`

If `.ddev/` exists, prefix PHP commands with `ddev exec`. For concrete per-stack code examples, the gate ships pattern files: `testing-workflow/patterns-php.md` and `patterns-typescript.md`.
</run_commands>

<success_criteria>
A test written under this skill:
- Started from `superpowers:test-driven-development` for the generic cycle — not reinvented here.
- Was **RED first for a BEHAVIORAL reason** (not "module not found"), now GREEN.
- Asserts the **acceptance-criteria contract**, including the **denial path** for any guard.
- Crosses any **un-mocked seam** the task is responsible for wiring.
- Was run **≥3×** if it touches time/ordering/concurrency.
- Is handed back to the **`testing-workflow` gate**, which owns the tier line, the deferral line, and the task sign-off. This skill does not sign off.
</success_criteria>

<integration>
- **superpowers:test-driven-development** — the BASE this skill layers on. Owns the generic RED→GREEN→REFACTOR cycle, AAA, the pyramid, doubles, DAMP. This skill does not restate it; it adds the harness contract above.
- **`testing-workflow`** (the gate that reached for this skill) — decides WHETHER + AT WHAT TIER and owns the sign-off. Return there with the written test.
- **`test-effectiveness`** — phase-close audit: does every sibling guard have its denial test, is every wire crossed un-mocked. This skill writes ONE test; that audits the SET.
- **`feature-acceptance`** — owns proving the feature behaves end-to-end. A user-facing flow's Large test belongs there.
- **`driving-the-browser`** — the Chrome how-to if you must inspect a live failure to know what to assert.
- **Provenance** — generic craft from `superpowers` (+ concepts shared with `addyosmani/agent-skills`, MIT); the Netdust spine (behavioral-RED, denial path, un-mocked seam, ≥3× determinism, gate position) is what this file adds and is what makes it more than superpowers.
</integration>
