---
name: wp-testing
description: Use when setting up, writing or judging tests for a WordPress project — two stacks. Gate stack — Brain Monkey unit tests, wp-phpunit integration on the wptests DB, Vitest theme tests, Playwright e2e, composer gate. Legacy stack (Stride family) — Codeception, wp-browser, acceptance tests. Triggers on file edits in tests/, on phpunit.unit.xml, phpunit.integration.xml, phpunit.xml, bin/gate.sh, codeception.yml, playwright.config.ts, infection.json5. Activates on keywords PHPUnit, Brain Monkey, wp-phpunit, wptests, composer gate, gate tier, Vitest, Codeception, wp-browser, WPTestCase, Cest, WP_UnitTestCase, factory, Playwright, e2e, dataProvider, mocking $wpdb, falsify, mutation testing, Infection, reflection, snapshot. Symptoms include writing the first test for a new module, deciding between unit/integration/e2e tiers, a green suite while the feature is broken, a test that fails on every refactor, debugging a flaky acceptance test, adding coverage to a legacy plugin.
---

# WordPress Testing — gate stack (primary) + legacy Codeception

## Stack detection (first thing, every time)

- `phpunit.unit.xml` / `bin/gate.sh` present → **gate stack**. All born-gated projects (2026-07+). Primary, below.
- `codeception.yml` present → **legacy stack** (Stride family). Section at the end.
- Both present (not expected): the gate stack wins — write new tests there.
- The project's own `README-testing.md` is the always-current per-project reference; read it before the first test. `make gate` runs the project's `commands.gate` from `site.yml`; this skill teaches how to WRITE the tests it runs.

## What a test owes (both stacks)

The gate is only as good as the tests it runs. A green gate over weak tests is false evidence, so every new test meets this bar before it is written, not after:

1. **It pins a decided behaviour.** Name the requirement, bug, or rule it protects. If the behaviour is only "what the code happens to do", the test freezes an accident — don't write it.
2. **Its expected value can disagree with the implementation.** Write expected values by hand from the requirement or a worked example. Never compute them with the production logic or the WordPress function it calls (`assertSame(sanitize_email($in), …)` is the implementation again), and never assert that a stub returns what you arranged.
3. **It asserts outcomes, not call shape.** Assert return values, persisted state, rendered output, HTTP responses. Asserting that a collaborator was called a certain way is allowed only when that call IS the contract (see Brain Monkey below).
4. **It acts through a seam a caller uses** — a request, route, render, or public method. Reaching a private method or property through reflection pins the implementation, not the behaviour; drive the public path that reaches it.
5. **It can fail.** Before trusting it green, break the production behaviour it claims to pin, watch it go red, restore. A test that has never been red is not yet evidence.

Shape assertions are the common way to break rule 5 without noticing. `[12 => 'x']` and `['12' => 'x']` are the same PHP array (numeric string keys canonicalise to int), so "the map is string-keyed" can never fail — pin the contract through the behaviour that consumes it instead. Likewise a "nothing leaks" assertion passes vacuously when the thing that would leak is dropped upstream; make sure the guarded path is actually reachable in the test.

Three things that look like tests and are not:

- **A property that something is absent or unique** ("never calls `mt_rand`", "exactly one call site") is a mechanical grep in `ARCHITECTURE-INVARIANTS.md`, run by `invariant-auditor` at review (`netdust-gates:policy`) — not a test that reads source files. Its test is the behaviour the absence protects.
- **A snapshot or characterization test** that holds output still through a refactor is scaffolding: the refactor's last task deletes it.
- **ntdst-core and ntdst-baseline behaviour** is tested in their own repos. A site's tests cover its own code and its configuration of those packages.

## Gate stack

Every check is a tier of `composer gate` (`bin/gate.sh`: cheapest-first, fail-fast, lint → analyse → audits → unit tests (PHP + JS) → build → integration → e2e; the gate's exit code is the truth). The test tiers:

| Tier | Where | Tool | What | Run |
|---|---|---|---|---|
| PHP unit | `tests/Unit/` | PHPUnit + Brain Monkey | Pure PHP logic, WP functions stubbed. No WordPress, no DB. <10 s. | `composer test:unit` |
| PHP integration | `tests/Integration/` | wp-phpunit (`WP_UnitTestCase`) | Real WP APIs on the dedicated `wptests` DB. | `ddev composer test:int` (in-container — DB host `db` only exists there) |
| JS unit | theme `src/*.test.js` | Vitest | Theme JS logic, next to the code. | `composer test:js` |
| E2E | `tests/E2E/*.spec.ts` | Playwright (host-side) | User-visible flows on the live DDEV URL. | `composer test:e2e` |

### Choosing the tier

Put each behaviour at the lowest tier that can prove it: pure rules at unit, persistence/hooks/capabilities at integration, user-visible flows at e2e. Don't prove the same thing at two tiers.

**A stubbed unit suite proves the code matches the stubs, not that the feature works.** So: every task that claims a user-visible behaviour owes at least one assertion through the real entry point — the route, the REST response, or the rendered page — not only the service behind it. Unit tests cover the rule's cases; the entry-point assertion proves the rule is actually wired in.

### Writing a unit test

Extend the tier's base `TestCase` (`tests/Unit/TestCase.php`): it wires `Brain\Monkey\setUp()/tearDown()` around every test, and `MockeryPHPUnitIntegration` turns `Functions\expect` into counted PHPUnit assertions. Patterns (see `tests/Unit/BrainMonkeyFunctionsTest.php`):

```php
use Brain\Monkey\Functions;

Functions\when('esc_html')->returnArg();                          // stub: the default
Functions\expect('update_post_meta')->once()->with(7, 'k', 'v');  // verify: only when the call IS the contract
```

- **`when()` by default, `expect()` by exception.** Use `expect()` only when the WordPress call is the observable effect of the unit — a write, a scheduled event, a fired action. If the unit returns a value, assert the value and stub the WP calls with `when()`. Verifying incidental calls produces change detectors that fail on refactors and catch no bugs.

- **ABSPATH trap**: every ntdst-core file opens with `defined('ABSPATH') || exit;`. The unit bootstrap defines `ABSPATH` before requiring units under test — if a class mysteriously "doesn't exist" at unit tier, check `tests/bootstrap-unit.php` requires it after that define (mu-plugins have no autoloader).
- **Behavioural assertions with denial paths** — `tests/Unit/ContainerTest.php` is the model: the singleton/fresh-instance/forget contracts, plus `expectException` for the unknown-service and bad-constructor-parameter denials.

### Writing an integration test

Extend `WP_UnitTestCase` and exercise REAL WordPress — `tests/Integration/DataLayerRoundTripTest.php` is the model: prove persistence through WordPress itself (`get_post`, `get_post_meta`), assert the real hook dispatcher fired the lifecycle action, and include a denial case that also proves nothing was written to the DB.

- **`wptests` isolation is mechanical, not a convention**: the bootstrap's ALLOW-LIST guard dies before install unless `DB_NAME` is `wptests` (or a DB explicitly named via the `WP_TESTS_ALLOW_DB` env escape hatch). Never the dev DB — wp-phpunit DROPS AND RECREATES tables in `DB_NAME`. Re-runs are idempotent (fresh install into `wptests` each run). Guard contract test: `tests/Unit/IntegrationBootstrapGuardTest.php`.

### PHPUnit ceiling — never bump blind

**PHPUnit is pinned `^9.6` because NO wp-phpunit release runs under PHPUnit ≥ 10** (PHPUnit removed internals wp-phpunit depends on). This is invisible to composer — wp-phpunit declares no PHPUnit constraint, so a bump resolves cleanly and then the integration tier breaks at runtime. Check wp-phpunit support before touching the PHPUnit version.

### E2E

Plain `@playwright/test` — on Bedrock the admin lives at `/wp/wp-admin`. Fixtures (users, posts) are seeded by `bin/e2e.sh` via wp-cli BEFORE the suite runs — never created through the UI. Credentials are per-run (`E2E_PASS` generated random unless provided) and arrive via env, as do fixture URLs; add new fixtures to `bin/e2e.sh` and export them the same way. Run one gate at a time — parallel runs collide on the rotating e2e password.

Find controls by role and accessible name; assert the outcome of the task (state change, saved data, navigation), not exact prose, dimensions or layout — unless the wording itself is a requirement.

### Shake-out access — the recipe the plan cites

The plan's `## Shake-out access` section names ONE command and the environment it is valid on, and cites this recipe (`shakeout-access`); it never restates it. The shake-out drives only the actors `bin/e2e.sh` seeds — never a real user, so a staging screenshot never carries real rows.

1. **DDEV (the default).** Once per project: `ddev wp package install aaemnnosttv/wp-cli-login-command`, then `ddev wp login install --activate`. The companion `wp-cli-login-server` plugin is DDEV-only: `bin/e2e.sh` installs it, it is never in `deploy.payload`, and no deploy-side script carries a `wp login` command — the recipe is valid on `WP_ENV != production`; production sits behind the typed confirmation in `netdust-devops:devops`, which refuses piped input. Per run, at the top of `bin/e2e.sh`: `ddev wp login create <seeded-admin> --url-only --expires=900`. The Playwright spec opens that URL once and saves `storageState` to `tests/e2e/.auth/` — the one path `templates/gitignore.tmpl` already ignores. Teardown: `ddev wp login invalidate` — the command takes no flags and voids every link.
2. **`wire` rows.** Per run: `ddev wp user application-password create <user> shakeout --porcelain`, exported to the spec as env. Teardown deletes by uuid: `ddev wp user application-password list <user> --fields=uuid,name --format=csv`, then `ddev wp user application-password delete <user> <uuid>` — `--all` would take a developer's own passwords with it.
3. **Staging.** The same two commands through `wp --ssh=<host>`, the host being `site.yml`'s `environments.<env>.ssh_host`. `wp --ssh` is raw WP-CLI with no netdust guard in front of it; the floors that exist are these: on production `wp login create` fails because the server plugin is never in `deploy.payload`; never `wp login install` over `--ssh`; `shakeout-qa` refuses a production URL (`netdust-gates`' `agents/shakeout-qa.md`). An application password created over `--ssh` on production has NO machine floor — this recipe forbids it in words, and nothing else will.
4. **Standalone packages** (a plugin repo with no `site.yml`): WordPress Playground MAY be the browser, its Blueprint `login` step the recipe. Named, not required.

Never in git: the link, the app password, the state file — the `.env` rule in `netdust-devops:devops` applies (a secret arrives per run through the environment, never through a committed file). The manifest's Evidence cell carries the URL of the page AFTER login; `bin/shakeout-check.py` (netdust-gates) scans the whole manifest and fails on a login link, an application password, the `storageState` token or a `wordpress_logged_in_*` cookie name — it matches those tokens, not file paths (`shakeout-credential`, no override).

### After a deploy — `make e2e` and `make smoke`

The specs the shake-out commits are the project's stability proof: `netdust-devops`'s
`make e2e env=staging` runs `commands.e2e` with `E2E_URL` and `E2E_ENV` set, and the tests are
registered in `specs/CHECKS.md` (netdust-gates). `bin/e2e.sh` reads `E2E_ENV`: unset or `local`
seeds through `ddev wp`, a deployed environment seeds through `wp --ssh=<environments.<env>.ssh_host>`
(recipe item 3 above), then runs `playwright test --grep @e2e` with `PLAYWRIGHT_BASE_URL=$E2E_URL`.
The verb refuses production; nothing seeds there. `@smoke` specs need none of this — they are
read-only, log in nowhere, and `make smoke env=<env>` runs them anywhere.

### Falsifiability — gates and tests

**Gates.** Every gate tier has a recorded red demonstration — deliberate violation, non-zero exit, green re-run — in the project's `docs/gate-falsifiability.md`. If you add a gate or check, prove it can fail before you trust it green. (Projects that ADOPT the gate later won't have `docs/gate-falsifiability.md` — the doc ships with template-scaffolded projects; adopters inherit the discipline, not the file.)

**Tests.** The same rule applies per test (rule 5 above): break the production behaviour, see red, restore. Mutation testing is the mechanical version — Infection (PHP) and StrykerJS (JS/TS) mutate production code and report which mutants no test caught. Where a project has Infection configured, run it diff-scoped (`--git-diff-filter=AM`) on the changed code; a surviving mutant in new code means a missing or vacuous assertion. Don't chase a global mutation score, and never add change-detector tests to raise one.

Deeper detail (DDEV topology, tier timings, known limitations) lives in the project's `README-testing.md` and the real example tests in `tests/` — point there, don't duplicate here.

## Legacy stack (Stride family) — do not migrate as a side quest

Codeception + wp-browser. **Canonical implementation: `~/Sites/stride/`** — 706 unit / 261 integration / 102 acceptance tests, all green. Mirror its `codeception.yml`, suite configs, and bootstrap; wp-browser docs at https://wpbrowser.wptestkit.dev. The "What a test owes" bar applies here too; a large green count is not evidence on its own.

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
        $I->seeElement('[data-course-id]');
    }
}
```

Discipline: no mocking `$wpdb` in integration tests; no skipped/xfail checked in without a written "remove after X"; unit green after every task, integration + acceptance green after every phase; tests stay green on `staging`. Don't test WP core, third-party plugins, pure rendering, or the same thing at multiple levels.

Known traps: WPTestCase reset doesn't roll back transients in object cache (flush in `tearDown`); `actAsUser()` (acceptance) ≠ `wp_set_current_user()` (integration); don't assert translated human strings — use slugs/data-attributes; huge `setUp` datasets belong in a fixture file or `@dataProvider`; acceptance runs fail silently without a browser driver — Stride drives Playwright's browser via wp-browser instead of Chromedriver/Selenium.

## See also

- `netdust-gates:policy` — its WordPress pack puts `make gate` and these tiers in every WP plan's Global Constraints
- `/shakeout` (netdust-gates) — the close on user-facing work: `shakeout-qa` drives the artifact, then the whole-branch review
- Gate stack reference: the project's `README-testing.md` + `tests/` (single home: the `gate/` payload of github netdust/wp-starter)
- Legacy reference: `~/Sites/stride/codeception.yml` + `~/Sites/stride/tests/`
