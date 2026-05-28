---
description: Set up Codeception + wp-browser test infrastructure in a WordPress project
argument-hint: [site-directory-path]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Set up Codeception and wp-browser test infrastructure in the WordPress project at: $ARGUMENTS

## Instructions

Use ~/Sites/stride/ as the reference implementation. That project has a complete, working Codeception + wp-browser + Selenium setup. Read its config files to understand the patterns, then adapt them for the target project.

### Step 0: Detect project

1. Read the target project's CLAUDE.md or site config to understand its structure
2. Detect the WordPress structure:
   - Bedrock: `web/wp/` — admin path is `/wp/wp-admin`
   - Custom app/: `app/wp/` — admin path is `/wp-admin`
   - Custom site/: `site/wp/` — admin path is `/wp-admin`
3. Get the DDEV site URL from `.ddev/config.yaml` (the `name` field → `{name}.ddev.site`)
4. Get the table prefix from wp-config.php or `ddev wp config get table_prefix`
5. Determine the mu-plugins path and theme/plugin source directories

### Step 1: Install composer dependencies

```bash
cd [project-path]
ddev composer require --dev lucatume/wp-browser:^4.5 phpunit/phpunit:^10.5 brain/monkey:^2.6 mockery/mockery:^1.6 dg/bypass-finals:^1.9
```

### Step 2: Create directory structure

```
tests/
├── Unit/
├── Integration/
├── acceptance/
├── Stubs/
├── _support/
│   └── Helper/
├── _data/
├── _envs/
├── _output/        (gitignore this)
├── .env
├── bootstrap.php
├── TestCase.php
└── acceptance.suite.yml
```

### Step 3: Create config files

Read these files from stride and adapt for the target project:

| Stride file | Adapt what |
|-------------|-----------|
| `codeception.yml` | Namespace (use project name) |
| `tests/acceptance.suite.yml` | Table prefix, WP admin path |
| `tests/.env` | WP_URL, WP_ROOT_FOLDER, WP_ADMIN_PATH, table prefix |
| `tests/bootstrap.php` | WordPress path for integration loading |
| `tests/TestCase.php` | Namespace |
| `tests/Stubs/wordpress-stubs.php` | Copy as-is |
| `tests/_support/AcceptanceTester.php` | Namespace |
| `tests/_support/Helper/Acceptance.php` | DDEV project name in test secret |
| `phpunit.xml.dist` | Source directories (theme/plugin paths) |
| `.ddev/docker-compose.selenium.yaml` | Copy as-is |

### Step 4: Create test login helper

Read `~/Sites/stride/web/app/mu-plugins/test-login-helper.php` and adapt:
- Change the DDEV project name check
- Place in the correct mu-plugins path for this site structure
- Update the test secret to be unique per project

### Step 5: Add composer scripts

Add to composer.json scripts section:
```json
{
  "test": "phpunit",
  "test:unit": "phpunit --testsuite Unit",
  "test:integration": "phpunit -c phpunit-integration.xml.dist"
}
```

### Step 6: Add gitignore entries

Add to .gitignore:
```
tests/_output/
tests/_support/_generated/
```

### Step 7: Generate Codeception support

```bash
cd [project-path]
ddev exec vendor/bin/codecept build
```

### Step 8: Verify

```bash
# Selenium container running?
ddev restart
ddev exec curl -s http://selenium:4444/wd/hub/status | head -20

# Codeception recognizes suites?
ddev exec vendor/bin/codecept run --list-suites

# PHPUnit works?
ddev exec vendor/bin/phpunit --version

# Create a smoke test to verify the setup
```

Write a `tests/acceptance/SmokeTestCest.php` that verifies:
- Site loads (HTTP 200)
- Admin login works via test helper
- WPDb can read from database

Run it: `ddev exec vendor/bin/codecept run acceptance SmokeTestCest`

### Step 9: Report

Tell the user:
- What was created
- How to run tests (`composer test`, `ddev exec vendor/bin/codecept run acceptance`)
- What the smoke test verified
- Suggest first real tests to write based on the project's features
