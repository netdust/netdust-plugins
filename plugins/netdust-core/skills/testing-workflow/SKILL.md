---
name: testing-workflow
description: "Enforces test discipline across the superpowers workflow. Subagents invoke after every task (unit tests). Controller invokes after every phase (integration + acceptance tests). Covers PHP (WordPress/Codeception/PHPUnit) and TypeScript (Vitest/Playwright)."
---

# Testing Workflow

Two trigger points, no exceptions:

1. **After every task** — subagent writes and runs unit tests before marking done
2. **After every phase** — controller runs integration and acceptance tests before sign-off

This is not optional. A task without unit tests is not done. A phase without integration tests is not verified.

## How This Connects to Superpowers

```
superpowers:writing-plans
  └─ Each task includes: "Unit test: [what to verify]"
  └─ Each phase ends with: "Integration gate: [what to verify across tasks]"

superpowers:subagent-driven-development
  └─ Subagent picks up task
  └─ Writes code
  └─ Invokes testing-workflow:task-complete  ← unit tests
  └─ Reports done (only if green)

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

## Task-Complete: Unit Tests

Triggered by subagent after implementing a task. This is the RED → GREEN → REFACTOR cycle.

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

### What NOT to unit test

- Private methods (test through public interface)
- Framework internals (WordPress core, Express middleware)
- Simple getters/setters with no logic
- Third-party library behavior

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

### Task sign-off checklist

The subagent MUST confirm ALL of these before reporting done:

- [ ] Unit test exists for this task's behavior
- [ ] Test was red before implementation (TDD) or covers the new behavior
- [ ] Test is green
- [ ] Full unit suite still green (no regressions)
- [ ] Static analysis clean on changed files

If any box is unchecked → not done. Fix it.

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

## Integration with Other Skills

- **writing-plans** — Plans MUST include test expectations per task and per phase
- **subagent-driven-development** — Every subagent invokes task-complete before reporting done
- **test-driven-development** — Governs RED→GREEN within a task; this skill governs the workflow around it
- **ntdst-architecture / ntdst-data / ntdst-patterns** (WP design skills) — design must still yield per-task unit-test expectations; rigorous review adds deeper checks