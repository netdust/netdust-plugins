---
name: wp-testing
description: Use when setting up or writing tests for a WordPress project — PHPUnit, Codeception, wp-browser, Playwright frontend tests, acceptance tests, integration tests, unit tests for services. Triggers on file edits in tests/, on phpunit.xml*, codeception.yml, playwright.config.ts. Activates on keywords PHPUnit, Codeception, wp-browser, WPTestCase, WPUnit, WPAcceptance, Cest, $I->haveOptionInDatabase, WP_UnitTestCase, factory, fixture, db-fixture, Playwright, e2e, dataProvider, mocking $wpdb. Symptoms include writing first test for a new module, debugging a flaky acceptance test, adding test coverage to a legacy plugin, deciding between unit/integration/acceptance levels. Stride is the canonical reference — 706 unit / 261 integration / 102 acceptance tests, all green.
---

# WordPress Testing (Codeception + wp-browser)

## Test pyramid (Netdust default)

| Level | Tool | Speed | What |
|---|---|---|---|
| Unit | PHPUnit (via Codeception WPUnit) | Fast (ms) | Pure PHP logic — services, value objects, helpers. No DB. |
| Integration | Codeception WPIntegration | Medium (s) | Code that touches `$wpdb`, hooks, options, transients. Real DB, isolated test DB. |
| Acceptance | Codeception WPWebDriver / WPBrowser | Slow (10s+) | User-facing flows in a real browser. |
| Frontend e2e | Playwright | Slow | JS-heavy flows where Codeception is awkward. |

**Canonical implementation: `~/Sites/stride/`.** Mirror its `codeception.yml`, suite configs, and bootstrap.

## Stack

```
project/
├── codeception.yml                       ← root config
├── phpunit.xml.dist                      ← if also using bare phpunit
├── tests/
│   ├── _bootstrap.php
│   ├── _data/                            ← fixtures
│   ├── _support/                         ← Cest helpers, page objects
│   ├── unit/                             ← WPUnit suite — pure PHP, no DB
│   ├── integration/                      ← WPIntegration — real WP + DB
│   └── acceptance/                       ← WPBrowser/WPWebDriver — real browser
└── playwright.config.ts                  ← (optional) frontend tests
```

## Setup (new project)

```bash
composer require --dev codeception/codeception lucatume/wp-browser
vendor/bin/codecept init wpbrowser
```

Then edit `codeception.yml` and `tests/<suite>.suite.yml`. wp-browser docs are at `wpbrowser.wptestkit.dev`. Stride's setup is the working reference.

## Writing tests

### Unit (no WP)

```php
class MoneyTest extends \Codeception\Test\Unit {
    public function testAddSameCurrency(): void {
        $a = new Money(100, 'EUR');
        $b = new Money(50, 'EUR');
        $sum = $a->add($b);
        $this->assertEquals(150, $sum->getAmount());
    }
}
```

### Integration (WP + DB)

```php
class EnrollmentRepositoryTest extends \Codeception\TestCase\WPTestCase {
    public function testSaveAndFetchEnrollment(): void {
        $course_id = self::factory()->post->create(['post_type' => 'sfwd-courses']);
        $user_id   = self::factory()->user->create();

        $repo = new EnrollmentRepository();
        $enrollment = new Enrollment($user_id, $course_id);
        $id = $repo->save($enrollment);

        $fetched = $repo->find($id);
        $this->assertSame($user_id, $fetched->getUserId());
    }
}
```

### Acceptance (browser)

```php
class DashboardCest {
    public function userSeesEnrolledCourses(AcceptanceTester $I): void {
        $I->haveUserInDatabase('student', 'subscriber');
        $I->loginAs('student', 'password');
        $I->amOnPage('/dashboard');
        $I->see('My Courses');
        $I->seeElement('.course-card');
    }
}
```

## Test discipline (from `netdust-agent:testing-workflow`)

- **Unit tests after every task.** Don't move on with broken unit tests.
- **Integration + acceptance after every phase.** Don't move on with broken integration.
- **No mocking `$wpdb` in integration tests.** Real DB or it's not an integration test.
- **No skipped/xfail tests checked in without a written "remove after X" condition.**
- **Tests stay green on `staging` branch.** A red `staging` is everyone's problem.

## Fixture patterns

- **In-test factory**: `self::factory()->post->create(['post_type' => 'sfwd-courses'])` for one-off objects.
- **Shared `_data/` fixtures**: SQL dumps loaded via `WPDb` module for complex setup.
- **Module/role fixtures**: helper trait that sets up the role + capabilities once per test class.

## What NOT to test

- WordPress core itself (already tested by core).
- Third-party plugins (your test surface stops at your code's boundary).
- Pure rendering (test logic, not HTML — unless an acceptance test).
- The same thing at multiple levels (one good unit + one acceptance > five duplicated integration tests).

## Playwright (when Codeception is awkward)

Use Playwright when:
- The flow is Alpine/Vue-heavy and needs real reactive state.
- You want trace-on-failure with full UI screenshots.
- Codeception's WebDriver mode is too slow for the iteration cycle.

Stride uses Playwright for the Stridence theme's interactive parts; Codeception for the core's PHP-driven flows.

## Common mistakes

- **WPTestCase reset between tests doesn't roll back transients in object cache.** Flush at `tearDown` if your test sets transients.
- **`actAsUser($id)` in acceptance ≠ `wp_set_current_user($id)` in integration.** Don't mix.
- **Acceptance test asserts text that's translated.** Use the slug or a data-attribute, not the human string.
- **Integration test that creates 1000 posts in `setUp`.** Either factor it into a fixture file or use `@dataProvider` with smaller scopes.
- **Forgetting to install the browser**: `vendor/bin/codecept run acceptance` fails silently without Chromedriver/Selenium. Stride uses Playwright's browser instead via wp-browser's `WPBrowserPlaywright` module.

## See also

- `netdust-agent:testing-workflow` — the broader discipline (when to run which level)
- `netdust-agent:shake-out` — post-build QA when tests alone aren't enough
- netdust-agent's reviewer agents — review existing code against framework patterns (the `reviewer` agent + specialist reviewers; on WP also `netdust-wp:ntdst-drift-reviewer`)
- `~/Sites/stride/codeception.yml` + `~/Sites/stride/tests/` — the canonical implementation
- wp-browser docs: https://wpbrowser.wptestkit.dev
