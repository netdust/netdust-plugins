---
name: wp-testing
description: Use when setting up or writing tests for a WordPress project — two stacks. Gate stack (born-gated projects, 2026-07+) — Brain Monkey unit tests, wp-phpunit integration on the wptests DB, Vitest theme tests, Playwright e2e, the composer gate umbrella. Legacy stack (Stride family) — Codeception, wp-browser, acceptance tests. Triggers on file edits in tests/, on phpunit.unit.xml, phpunit.integration.xml, phpunit.xml, bin/gate.sh, codeception.yml, playwright.config.ts. Activates on keywords PHPUnit, Brain Monkey, wp-phpunit, wptests, composer gate, gate tier, Vitest, Codeception, wp-browser, WPTestCase, WPUnit, WPAcceptance, Cest, $I->haveOptionInDatabase, WP_UnitTestCase, factory, fixture, Playwright, e2e, dataProvider, mocking $wpdb. Symptoms include writing the first test for a new module, deciding between unit/integration/e2e tiers, debugging a flaky acceptance test, adding coverage to a legacy plugin.
---

# WordPress Testing — gate stack (primary) + legacy Codeception

## Stack detection (first thing, every time)

- `phpunit.unit.xml` / `bin/gate.sh` present → **gate stack**. All born-gated projects (2026-07+). Primary, below.
- `codeception.yml` present → **legacy stack** (Stride family). Section at the end.
- Both present (not expected): the gate stack wins — write new tests there.
- The project's own `README-testing.md` is the always-current per-project reference; read it before the first test. `netdust-agent:testing-workflow` LOCATES the runner/commands (`site.yml` `commands:` binding first, markers as fallback); this skill teaches how to WRITE the tests.

## Gate stack

Every check is a tier of `composer gate` (`bin/gate.sh`: cheapest-first, fail-fast, lint → analyse → audits → unit tests (PHP + JS) → build → integration → e2e; the gate's exit code is the truth). The test tiers:

| Tier | Where | Tool | What | Run |
|---|---|---|---|---|
| PHP unit | `tests/Unit/` | PHPUnit + Brain Monkey | Pure PHP logic, WP functions stubbed. No WordPress, no DB. <10 s. | `composer test:unit` |
| PHP integration | `tests/Integration/` | wp-phpunit (`WP_UnitTestCase`) | Real WP APIs on the dedicated `wptests` DB. | `ddev composer test:int` (in-container — DB host `db` only exists there) |
| JS unit | theme `src/*.test.js` | Vitest | Theme JS logic, next to the code. | `composer test:js` |
| E2E | `tests/E2E/*.spec.ts` | Playwright (host-side) | User-visible flows on the live DDEV URL. | `composer test:e2e` |

### Writing a unit test

Extend the tier's base `TestCase` (`tests/Unit/TestCase.php`): it wires `Brain\Monkey\setUp()/tearDown()` around every test, and `MockeryPHPUnitIntegration` turns `Functions\expect` into counted PHPUnit assertions. Patterns (see `tests/Unit/BrainMonkeyFunctionsTest.php`):

```php
use Brain\Monkey\Functions;

Functions\when('esc_html')->returnArg();                          // stub: don't care how it's called
Functions\expect('update_post_meta')->once()->with(7, 'k', 'v');  // verify: exact call is the assertion
```

- **ABSPATH trap**: every ntdst-core file opens with `defined('ABSPATH') || exit;`. The unit bootstrap defines `ABSPATH` before requiring units under test — if a class mysteriously "doesn't exist" at unit tier, check `tests/bootstrap-unit.php` requires it after that define (mu-plugins have no autoloader).
- **Behavioral assertions with denial paths** — `tests/Unit/ContainerTest.php` is the model: the singleton/fresh-instance/forget contracts, plus `expectException` for the unknown-service and bad-constructor-parameter denials.

### Writing an integration test

Extend `WP_UnitTestCase` and exercise REAL WordPress — `tests/Integration/DataLayerRoundTripTest.php` is the model: prove persistence through WordPress itself (`get_post`, `get_post_meta`), assert the real hook dispatcher fired the lifecycle action, and include a denial case that also proves nothing was written to the DB.

- **`wptests` isolation is mechanical, not a convention**: the bootstrap's ALLOW-LIST guard dies before install unless `DB_NAME` is `wptests` (or a DB explicitly named via the `WP_TESTS_ALLOW_DB` env escape hatch). Never the dev DB — wp-phpunit DROPS AND RECREATES tables in `DB_NAME`. Re-runs are idempotent (fresh install into `wptests` each run). Guard contract test: `tests/Unit/IntegrationBootstrapGuardTest.php`.

### PHPUnit ceiling — never bump blind

**PHPUnit is pinned `^9.6` because NO wp-phpunit release runs under PHPUnit ≥ 10** (PHPUnit removed internals wp-phpunit depends on). This is invisible to composer — wp-phpunit declares no PHPUnit constraint, so a bump resolves cleanly and then the integration tier breaks at runtime. Check wp-phpunit support before touching the PHPUnit version.

### E2E

Plain `@playwright/test` — on Bedrock the admin lives at `/wp/wp-admin`. Fixtures (users, posts) are seeded by `bin/e2e.sh` via wp-cli BEFORE the suite runs — never created through the UI. Credentials are per-run (`E2E_PASS` generated random unless provided) and arrive via env, as do fixture URLs; add new fixtures to `bin/e2e.sh` and export them the same way. Run one gate at a time — parallel runs collide on the rotating e2e password.

### Falsifiability culture

Every gate tier has a recorded red demonstration — deliberate violation, non-zero exit, green re-run — in the project's `docs/gate-falsifiability.md`. If you add a gate or check, prove it can fail before you trust it green. (Projects that ADOPT the gate later won't have `docs/gate-falsifiability.md` — the doc ships with template-scaffolded projects; adopters inherit the discipline, not the file.)

Deeper detail (DDEV topology, tier timings, known limitations) lives in the project's `README-testing.md` and the real example tests in `tests/` — point there, don't duplicate here.

## Legacy stack (Stride family) — do not migrate as a side quest

Codeception + wp-browser. **Canonical implementation: `~/Sites/stride/`** — 706 unit / 261 integration / 102 acceptance tests, all green. Mirror its `codeception.yml`, suite configs, and bootstrap; wp-browser docs at https://wpbrowser.wptestkit.dev.

| Level | Tool | What |
|---|---|---|
| Unit | PHPUnit via Codeception WPUnit (`tests/unit/`) | Pure PHP logic — no DB. |
| Integration | Codeception WPIntegration (`tests/integration/`) | `$wpdb`, hooks, options, transients — real isolated test DB. |
| Acceptance | Codeception WPBrowser/WPWebDriver (`tests/acceptance/`) | User-facing flows in a real browser. |
| Frontend e2e | Playwright | JS-heavy flows where Codeception is awkward (Alpine/Vue reactive state; trace-on-failure debugging; faster iteration than WebDriver). Stride: Stridence theme interactivity. |

Setup: `composer require --dev codeception/codeception lucatume/wp-browser && vendor/bin/codecept init wpbrowser`, then edit `codeception.yml` + `tests/<suite>.suite.yml`. Layout: `tests/_bootstrap.php`, `_data/` (fixtures), `_support/` (Cest helpers, page objects), plus the three suites above.

Integration tests extend `\Codeception\TestCase\WPTestCase` and use `self::factory()->post->create([...])` / `->user->create()` for one-off objects; shared `_data/` SQL fixtures load via the `WPDb` module; role/capability setup goes in a helper trait once per class. Acceptance is Cest-style:

```php
class DashboardCest {
    public function userSeesEnrolledCourses(AcceptanceTester $I): void {
        $I->haveUserInDatabase('student', 'subscriber');
        $I->loginAs('student', 'password');
        $I->amOnPage('/dashboard');
        $I->see('My Courses');
    }
}
```

Discipline (unchanged): no mocking `$wpdb` in integration tests; no skipped/xfail checked in without a written "remove after X"; unit green after every task, integration + acceptance green after every phase; tests stay green on `staging`. Don't test WP core, third-party plugins, pure rendering, or the same thing at multiple levels.

Known traps: WPTestCase reset doesn't roll back transients in object cache (flush in `tearDown`); `actAsUser()` (acceptance) ≠ `wp_set_current_user()` (integration); don't assert translated human strings — use slugs/data-attributes; huge `setUp` datasets belong in a fixture file or `@dataProvider`; acceptance runs fail silently without a browser driver — Stride drives Playwright's browser via wp-browser instead of Chromedriver/Selenium.

## See also

- `netdust-agent:testing-workflow` — stack/runner detection, per-task tier decision (it locates; this skill teaches)
- `netdust-agent:building` — the build overlay that dispatches this skill into every WP task, and owns the review + feature-test gates
- `/shakeout` (netdust-agent command) — the spec-complete gate: `shakeout-qa` drives the artifact, then the reviewer panel runs on the branch diff
- Gate stack reference: the project's `README-testing.md` + `tests/` (canonical template: github netdust/bedrock)
- Legacy reference: `~/Sites/stride/codeception.yml` + `~/Sites/stride/tests/`
