---
name: testing-workflow
description: "Use when verifying a task before marking it done, or a phase before sign-off, in the superpowers workflow — risk-tiers what each task needs (RED-first test for logic/auth/parsing/migrations; no bespoke test for glue/wrappers/UI), and adds the seam test that catches wiring/wire-mock/concurrency bugs per-task unit tests miss. Covers PHP (WordPress/Codeception/PHPUnit) and TypeScript (Vitest/Playwright)."
---

# Testing Workflow

Two trigger points, no exceptions:

1. **After every task** — subagent VERIFIES the task before marking done
2. **After every phase** — controller runs integration and acceptance tests before sign-off

**Verification is not optional. A task that is not verified is not done. A phase without integration tests is not verified.**

But *verification* is not the same as *a new unit test on every task*. The discipline is **risk-tiered**: a behavioral RED→GREEN unit test is mandatory where bugs are actually caught (logic, transforms, state machines, security/auth predicates, untrusted parsing, migrations) — and is **not** to be manufactured on units that have no logic of their own (glue, wiring, pass-through wrappers, presentational UI, config/enum/seed additions). On those, verification is "full suite green + the change is reachable by an existing or new integration/seam assertion," not a bespoke tautological test.

> **Why tiered, not uniform.** A binary "test exists or not done" gate fires identically for a one-line `clsx` wrapper and a multi-tenancy authorization guard. The evidence is that this (a) manufactures tautological tests on trivial units the project then never trusts, and (b) gives *false confidence* on the units that matter — every high-severity defect in this project's history (cross-tenant auth never mounted, wire-mocked UI green against a leaking server, a same-millisecond race that passed by scheduling luck) **passed a green per-task unit test and was caught one gate later**. Tiering routes effort to where it catches bugs and redirects the rest to the seam/integration/holistic gates that actually catch the escaped classes.

See **Task risk tier** below for how to classify, and **What the per-task gate cannot catch** for what to hand downstream instead of over-testing.

## How This Connects to Superpowers

```
superpowers:writing-plans
  └─ Each task includes: "Unit test: [what to verify]"
  └─ Each phase ends with: "Integration gate: [what to verify across tasks]"

superpowers:subagent-driven-development
  └─ Subagent picks up task
  └─ Writes code
  └─ Classifies task risk tier → verifies (Tier A: RED→GREEN unit test; Tier B: full suite + seam reach)
  └─ Reports done (only if verified + suite green)

Controller after phase tasks complete:
  └─ Invokes testing-workflow:phase-complete  ← integration + acceptance
  └─ Fix loop if red
  └─ Phase signed off
```

Plans MUST include test expectations. Every task needs a line stating what the unit test should verify. Every phase needs a line stating what the integration test should verify across tasks.

## Project Detection

Run once at start. Cache the result.

| Marker | Stack | Unit Runner | E2E Runner |
|--------|-------|-------------|------------|
| `composer.json` + WordPress | WP PHP | Codeception unit / PHPUnit | Codeception acceptance |
| `composer.json` (no WP) | PHP | PHPUnit | Codeception acceptance |
| `package.json` + TypeScript | TS | Vitest | Playwright |
| `package.json` (JS only) | JS | Jest / Vitest | Playwright |

**Monorepo:** Both `composer.json` and `package.json` exist → run both stacks.

Config file check:
- `codeception.yml` → Codeception suites available
- `phpunit.xml` → PHPUnit available
- `vitest.config.ts` → Vitest available
- `playwright.config.ts` → Playwright available

### DDEV / Docker

If `.ddev/` exists, prefix PHP commands with `ddev exec`.

```bash
ddev exec vendor/bin/phpunit --testsuite=unit
ddev exec vendor/bin/codecept run acceptance --steps
```

For acceptance tests, verify WebDriver is running:
```bash
ddev exec curl -s http://selenium:4444/status | grep ready
```

If not running, start it — this is a prerequisite, not an excuse to skip.

---

## Task-Complete: Verify at the Tier

Triggered by subagent after implementing a task. Tier A is the RED → GREEN → REFACTOR cycle; Tier B is suite-green + seam reach. Classify first.

### Task risk tier (classify BEFORE you test)

Every task is one of two tiers. **Name the tier in your task-close report** and justify it in one sentence, so the controller/reviewer can challenge a misclassification.

| Tier | What it covers | Verification required |
|------|----------------|------------------------|
| **A — must have a behavioral RED→GREEN unit test** | Pure functions with branching logic, data transforms, state machines, **any security/auth/scope predicate**, **any code parsing untrusted input** (frontmatter, AI tool-call args, webhook/JSON payloads, file uploads), **DB migrations**, anything in the threat-modeling predicate. | A test that was **RED first** (you watched it fail against the absent/old behavior), asserts the **contract from the acceptance criteria** (incl. the denial/negative path for guards), now GREEN. No skip. |
| **B — do NOT manufacture a bespoke unit test** | Glue / wiring / mount, pass-through wrapper over a typed library, presentational UI (classname/layout-only render), config / enum / seed additions, docs. | Full unit suite green + the change is **reachable** by an existing or new integration/seam assertion. Record one line: `no unit test: Tier B, <reason>`. |

**The litmus for Tier B:** if the only RED you can produce is *"the module/component doesn't exist yet"* (not a behavioral failure), the unit is Tier B — do **not** dress a tautology up as a contract test. A pure pass-through over typed third-party libraries (`cn = twMerge(clsx(x))`) has no contract of its own; testing it re-asserts the library, which the anti-patterns forbid. **But first check the Erosion guard below: a security/auth/scope guard, untrusted-input parser, or state machine is ALWAYS Tier A even when it looks like a one-line pass-through — it always yields a real behavioral RED (a denied actor was previously allowed), so it can never pass this litmus.**

**Erosion guard — these are ALWAYS Tier A, no matter how few lines:** security/auth/scope guards, untrusted-input parsing, state machines. A 3-line `if (role === 'member') return 403` is Tier A. "It's just wiring" is not a license to under-test a guard; short ≠ trivial. If you are tempted to call a guard Tier B, that is a red flag — stop and write the RED-first denial test.

### What the per-task gate cannot catch (hand these downstream, don't over-test)

A per-task unit test proves one unit correct **in isolation**. It is structurally blind to bugs that only manifest across a seam. Do **not** pile on more per-task unit tests trying to cover these — they belong to the **seam test** (below), the **phase-complete integration gate**, `/code-review`, the **invariant-auditor**, and `/shakeout`:

| Escaped class | Why per-task tests miss it | Owned by |
|---------------|----------------------------|----------|
| **Wiring / mounting** | The unit works but is never installed in the real chain (middleware unit-green but unmounted → cross-tenant 200) | Seam test + integration gate |
| **Wire-mocking** | The test stubs the server to return the right shape, so it only proves the client wires up *given* server correctness | Seam test crossing the un-mocked wire + shake-out |
| **Concurrency / timing** | A single happy-path run can't express a race; one green run passes by scheduling luck | Determinism re-run (≥3×) + `/code-review` |
| **Adversarial input on a boundary** | Happy-path parse passes while malformed input aborts the run / leaks / DoSes | Tier-A negative-path test + threat-model review |
| **Masking payload** | The test seeds the easy/wrong actor, so the broken path never runs | Negative/cross-actor case + invariant-auditor |

### Seam test at the wiring task

When a task **mounts, wires, or integrates** a previously-built piece into the real app chain — registering a route, mounting middleware, wiring a reactor/trigger path, composing a multi-component layout, joining a cross-binary type union — the close requires:

1. **≥1 assertion through the REAL chain with NO mock of the boundary being wired.** For an HTTP route: drive a real request through the mounted app and assert the status/shape. For a wire contract: cross the actual client→server boundary (or add a shake-out `curl`), do not stub the response.
2. **≥1 negative / adversarial case:** denied actor, malformed input, a *second tenant*, or the masking-payload alternative the happy path didn't seed.

**Forbidden:** satisfying a wiring task with a test that mocks the very seam it wires, or by pointing at a pre-existing isolated unit test of the piece (that test stays green even if the mount is mis-pathed and the guard never fires). The seam is the delta this task introduced — it is the one thing that must be exercised.

Keep it cheap: **one** real-chain assertion + **one** negative case. This is not a full integration suite; it is the minimum that proves the wire is live.

### What to test

Unit tests verify **one unit of behavior in isolation**. The test must come from the task's acceptance criteria, not from the code you just wrote.

Ask: "What does this task promise to the caller?" Test that contract.

| Task type | What to unit test |
|-----------|-------------------|
| Service / utility class | Public methods: correct output for given input, edge cases, error handling |
| API endpoint handler | Request parsing, response shape, validation rules, error responses |
| Data transformation | Input → output mapping, null/empty handling, type coercion |
| WordPress hook/filter | Hook fires, filter modifies data correctly, priority order |
| State logic | State transitions, guard conditions, side effects |
| Configuration | Defaults applied, overrides respected, invalid config rejected |

### Tasks that need NO unit test (do not write one)

This is a **hard exclusion**, not advice. Writing a bespoke unit test for any item below is itself an anti-pattern — it manufactures ceremony the project will not trust and gives false coverage. These are Tier B: verify via the full suite + a seam/integration assertion, and record `no unit test: Tier B, <reason>`.

- **Pure pass-through over a typed third-party lib** — `cn = twMerge(clsx(x))`. Any assertion you write is re-asserting the library's behavior; the lib's own suite + TypeScript cover it. *(A one-line **security/auth/scope guard** is NOT a pass-through — it is always Tier A; see the Erosion guard. "It forwards an already-tested helper's decision" does not make a guard Tier B.)*
- **Classname/style-only presentational render** — assert *behavior* or skip. A test asserting `/bg-info/` is on an element proves nothing the user cares about, and the real bug in this category (overflow/layout) is invisible to jsdom — it needs live-DOM measurement, not a unit test.
- **Trivial key/array mappings, enum→label lookups, config/seed additions** — no branching logic to fail.
- **Private methods** (test through the public interface).
- **Framework internals** (WordPress core, Hono/Express middleware mechanics — but the *guard you wrote on top* is Tier A).
- **Simple getters/setters with no logic.**

Each exclusion is narrow: "classname-**only**", "**no** logic", "pure pass-through". The moment a unit carries a branch, a transform, a guard, or parses untrusted input, it is Tier A and back in scope.

### Writing good unit tests

**Structure every test as Arrange → Act → Assert.**

Name tests by behavior, not by method name:
- ✅ `it calculates shipping cost for orders over threshold`
- ❌ `it tests calculateShipping()`

**Cover these paths for every unit:**
1. Happy path — expected input produces expected output
2. Edge cases — empty input, boundary values, nulls
3. Error path — invalid input throws/returns error correctly

**Isolation rules:**
- Mock external dependencies (database, API, filesystem)
- Each test must run independently — no shared state between tests
- No network calls, no filesystem access, no database queries

### Run commands

**PHP (PHPUnit):**
```bash
vendor/bin/phpunit --filter=TestClassName
```

**PHP (Codeception unit suite):**
```bash
vendor/bin/codecept run unit TestClassCest
```

**TypeScript (Vitest):**
```bash
npx vitest run src/path/to/file.test.ts
```

Run the specific test file first. If green, run the full unit suite to catch regressions:

```bash
# PHP
vendor/bin/phpunit --testsuite=unit

# TypeScript
npx vitest run
```

### Value-gate question (answer before writing OR skipping a test)

> **"If I delete this test, what real bug ships undetected? Name it — concretely and falsifiably."**

If the honest answer is *"none — it re-asserts a library, a classname, or a tautology,"* the test is the wrong test: it is Tier B, skip it. If the answer is *"a real defect, but my unit test can't reach it (it's a seam / race / cross-actor / adversarial-input bug),"* don't fake a green test — write the **seam test** or record the **deferral line** below. Only when you can name a real bug the *unit* test catches do you write the unit test.

### Task sign-off checklist

The subagent MUST confirm ALL of these before reporting done:

- [ ] **Tier named** (A or B) with a one-sentence justification — and security/auth/parsing/state-machine units are Tier A regardless of line count
- [ ] **Tier A:** a behavioral test that was **RED first** (you watched it fail), asserting the contract incl. the **denial/negative path** for guards, is now green — *OR* — **Tier B:** `no unit test: Tier B, <reason>` recorded
- [ ] **If this task WIRES a piece into the real chain:** a seam test exists — ≥1 assertion through the un-mocked chain **+** ≥1 negative/adversarial case
- [ ] **If this task touches time, ordering, concurrency, or any `Date.now()`/timestamp comparison:** the new/changed test file was run **≥3×** and was green every run (a single green run is not evidence of determinism)
- [ ] **Deferral line recorded:** `Risk this test does NOT cover: <concurrency | adversarial-input | cross-actor | multi-component | un-mocked-seam | none> — deferred to <integration-gate | /code-review | invariant-auditor | /shakeout>`
- [ ] Full unit suite still green (no regressions)
- [ ] Static analysis clean on changed files

If any box is unchecked → not done. Fix it.

The deferral line must name a **specific gate AND a specific risk class** — a vague "deferred to QA" is a failed box. The controller collects every deferral line at phase-complete and confirms each named risk was actually exercised before sign-off.

> **Count is not quality.** A Tier-B task legitimately adds 0 tests; a Tier-A task adding **one sharp RED-first denial test outranks four happy-path mirror tests**. Keep the `Test count: <before> -> <after>` line in the commit body for observability, but do not treat count growth as a quality signal or a target — the right count is contract-driven.

---

## Phase-Complete: Integration + Acceptance Tests

Triggered by controller after all tasks in a phase are done. This verifies the tasks work together and the feature works from the user's perspective.

### Integration tests

Integration tests verify that **components built in separate tasks interact correctly**. Unlike unit tests, they DO use real dependencies — database, WordPress hooks firing in sequence, API calls between modules.

Ask: "Now that tasks A, B, and C are done, do they actually work together?"

| Phase delivered | What to integration test |
|----------------|--------------------------|
| Form + handler + database | Submit form → handler processes → data persists → confirmation shown |
| API endpoint + auth + validation | Authenticated request → validated → correct response + DB state |
| WordPress plugin feature | Hooks fire in order → settings saved → frontend renders correctly |
| Scanner module + scoring | Detection runs → zones scored → output format correct |

### Writing integration tests

**Integration tests touch real systems.** They need:
- A test database (DDEV provides this)
- Actual WordPress loaded (for WP projects)
- Real HTTP requests (for API tests)

**Structure: Scenario → Setup → Execute → Verify state across systems.**

Use the scenario format:

```
SCENARIO: [what the user/system does end-to-end]
  GIVEN: [starting state — fixtures, config, existing data]
  WHEN:  [the action that spans multiple components]
  THEN:  [expected state across ALL systems touched]
         - Browser shows: [what the user sees]
         - Database contains: [what persisted]
         - API returns: [response shape]
         - Side effects: [emails sent, hooks fired, cache cleared]
```

Every scenario MUST verify both **visible output** AND **persisted state**. A success message with nothing saved is a bug.

### Acceptance tests (browser)

Acceptance tests load a real browser and interact like a user. They are the final proof that the feature works.

**Derive scenarios from what "working" means to the user, not from code.**

Cover three flows minimum:
1. **Happy path** — user completes the intended action successfully
2. **Error path** — user makes a mistake, gets clear feedback, nothing breaks
3. **Edge case** — empty state, permissions, unexpected input

### Run commands

**PHP integration (Codeception):**
```bash
vendor/bin/codecept run acceptance --steps
```

**TypeScript acceptance (Playwright):**
```bash
npx playwright test
```

**Full regression (both suites):**
```bash
# PHP
vendor/bin/phpunit --testsuite=unit && vendor/bin/codecept run acceptance --steps

# TypeScript
npx vitest run && npx playwright test
```

### Phase sign-off checklist

The controller MUST confirm ALL of these before signing off a phase:

- [ ] Integration tests cover cross-task interactions
- [ ] Acceptance tests cover happy path, error path, edge case
- [ ] All acceptance tests verify BOTH browser state AND persistence
- [ ] Full regression green (unit + integration + acceptance)
- [ ] Static analysis clean
- [ ] Manual smoke test checklist provided to user

### Smoke test checklist format

After all automated tests pass, provide the user with:

```markdown
## Smoke Test

- [ ] Visit: [URL]
      Expected: [what renders, no console errors]
- [ ] Action: [what to do]
      Expected: [visible result + data result]
- [ ] Admin: [where to check]
      Expected: [what should be there]
- [ ] Console: DevTools > Console
      Expected: No red errors
```

---

## Fix Loop

Same at both levels:

```
FAIL → read error → diagnose root cause → fix → re-run failed test → PASS → continue
```

Rules:
- Do NOT skip a failing test
- Do NOT delete a failing test
- Do NOT mark task/phase done with red tests
- If fixing one test breaks another, go back and fix that too
- If stuck after 3 attempts, escalate to user with: what failed, what you tried, what you think the issue is

---

## Test Anti-Patterns

These apply at every level. Subagents and controller must both avoid:

| Anti-Pattern | Why it's wrong | Do this instead |
|--------------|----------------|-----------------|
| Testing implementation details | Breaks on refactor, proves nothing | Test behavior and contracts |
| Deriving tests from your own code | You'll test your bugs | Derive from acceptance criteria |
| **Tautological test on a zero-logic unit** | RED is only "module not found"; the test re-asserts a library/classname and proves nothing | It's Tier B — skip the unit test, record the reason, verify via the suite + seam |
| **Mocking the already-filtered server response** | Test goes green while the server filter is untested — both sides pass, the wire leaks | For any client↔server wire contract, add one test (or shake-out `curl`) that crosses the **un-mocked** wire |
| `sleep(5)` / `wait(5000)` | Flaky, slow | Condition-based waits |
| Happy path only | Error paths break too | Always test happy + error + edge |
| Browser assertion without persistence check | "Success" message + empty database = bug | Assert both UI and data |
| Mocking everything in integration tests | Defeats the purpose | Use real dependencies for integration |
| One giant test | Can't diagnose failures | One scenario per test |
| Shared state between tests | Order-dependent, flaky | Each test sets up and tears down its own state |

---

## No Test Framework? Set It Up.

If the project has no test tooling, the FIRST task is setting it up. This is not deferred — it blocks everything else.

### PHP (WordPress) minimal setup

```bash
composer require --dev lucatume/wp-browser
vendor/bin/codecept init wpbrowser
```

This gives you `unit`, `wpunit`, `functional`, and `acceptance` suites.

### TypeScript minimal setup

```bash
npm install -D vitest @playwright/test
npx playwright install
```

Add to `package.json`:
```json
{
  "scripts": {
    "test:unit": "vitest run",
    "test:e2e": "playwright test"
  }
}
```

---

## Pattern References

Load the appropriate patterns file for concrete code examples:

| Project | File | Contents |
|---------|------|----------|
| PHP | `patterns-php.md` | PHPUnit unit patterns + Codeception acceptance patterns |
| TypeScript | `patterns-typescript.md` | Vitest unit patterns + Playwright acceptance patterns |

---

## What the discipline actually is (not Skill-tool ceremony)

Re-invoking the Skill tool once per task is **not** the discipline, and neither is a new bespoke test on every task. The discipline is, at each task close:

1. **Classify the tier** and record it (one line).
2. **Verify at the tier:** Tier A → a RED-first behavioral test incl. the negative path; Tier B → suite-green + seam reach.
3. **Run the FULL unit suite** + static analysis. This is the load-bearing audit step — the full suite is what catches cross-file regressions a per-task test never sees; it caught real breaks in this project where the new per-task test did not.
4. **Record the deferral line** so the later gate inherits a targeted checklist.

Auditability is satisfied by the **full-suite run + the tier/deferral report in the commit body**, not by a Skill-tool re-invocation per task. (Read the skill once per session to internalize it; you need not re-invoke it as a ritual between every task.) The relaxation is **only** on ceremony — verification (suite green, static analysis clean, tier/deferral recorded, Tier-A RED-first, seam test where wired) stays a hard, unskippable gate, and the controller's phase-complete integration gate stays fully mandatory.

## Integration with Other Skills

- **writing-plans** — Plans MUST include test expectations per task and per phase; each task line should make its tier obvious (a guard/transform line implies Tier A). A plan line that says `Unit test: …` does **not** override the tier — if the task is Tier B (pass-through/glue/presentational), obeying that prefix literally and writing a tautological test IS the anti-pattern; classify by tier, not by the plan's prefix.
- **subagent-driven-development** — Every subagent verifies at-tier before reporting done
- **test-driven-development** — Governs RED→GREEN within a task; this skill governs the workflow around it. For **Tier A**, RED-first is mandatory (not the soft "or covers the new behavior" escape).
- **threat-modeling** — Any unit in the threat-modeling predicate is Tier A; its named mitigations are the denial-path contracts your Tier-A tests assert
- **test-effectiveness** — SIBLING at a different altitude. This skill is write-time + per-task ("does this task need a test, at what tier, is the RED-first/denial path written?"). `test-effectiveness` is audit-time + per-phase ("across the whole diff, would the suite go RED if any dangerous path broke?"). This skill WRITES the Tier-A denial test; test-effectiveness AUDITS that it exists across every sibling guard and crosses every un-mocked wire — and names the seven green-but-blind failure modes (stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, missing-denial, no-coverage, concurrency) that a passing per-task suite still ships. Fired at harnessed-development Stage 3, before shake-out.
- **ntdst-architecture / ntdst-data / ntdst-patterns** (WP design skills) — design must still yield per-task tier + test expectations; rigorous review adds deeper checks
