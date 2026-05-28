<overview>
WordPress / Bedrock / DDEV sweep playbook. Loaded when shake-out detects a WordPress project.

Read the project's CLAUDE.md first for:
- Site structure (Bedrock `web/wp`, Custom `app/wp`, Custom `site/wp`)
- WP-CLI path handling (DDEV uses `wp-cli.yml` for `--path`)
- SSH patterns for remote checks (`ploi-staging`, `combell-[site]-staging`)
- Which site you're working on and its risk level
</overview>

<tool_tiers>
**Use the fastest tool that can answer the question.**

| curl / WP-CLI (fast) | chrome-devtools (slower, but essential) |
|-----------------------|-----------------------------------------|
| Does the page load? HTTP status codes | Does the **interaction** work? |
| Is the element in the server-rendered HTML? | Does clicking/submitting do the right thing? |
| Does the REST API return correct JSON? | Does a form validate, submit, and save? |
| PHP errors in the response? | JS errors in the console? |
| Plugin/theme state, options, cron, DB | Filters, pagination, dropdowns (JS-driven) |
| File system, config, permissions | Multi-step flows (enrollment, checkout, wizards) |
| **Static checks — "is it there?"** | **Behavior checks — "does it work?"** |

**Rule of thumb:** If it needs a click, a form fill, or JavaScript to execute — use chrome-devtools. If you're just checking presence or status — use curl/WP-CLI.

WordPress + YOOtheme server-renders most content, so **static checks** are fast via curl. But any feature with user interaction needs the browser.
</tool_tiers>

<prerequisites>
```bash
# Is DDEV running?
ddev status

# Can WP-CLI reach WordPress?
ddev wp option get siteurl

# Store site URL for reuse
SITE_URL=$(ddev wp option get siteurl)

# Can we reach the site?
curl -sI "$SITE_URL" | head -5
```

If DDEV is not running: `ddev start`
If WP-CLI fails: check wp-cli.yml path config matches site structure
</prerequisites>

<sweep_checklist>

<existing_tests>
**0. Run Existing Test Suites FIRST** (if available)

Before any manual checks, run what's already automated:

```bash
# Codeception acceptance tests (browser-level)
ddev exec vendor/bin/codecept run acceptance --no-interaction 2>&1

# Codeception frontend tests (if they exist)
ddev exec vendor/bin/codecept run frontend --no-interaction 2>&1

# PHPUnit unit + integration tests
ddev exec vendor/bin/phpunit 2>&1
# or: composer test

# Run specific suite related to what was built
ddev exec vendor/bin/codecept run acceptance [FeatureCest] --no-interaction 2>&1
```

**Log every test failure as a sweep finding.** These are bugs found by existing tests — the test suite is doing shake-out's job for you.

After running existing tests, continue with the manual checks below — but **skip any check already covered by a passing test.** Focus exploratory effort on what tests DON'T cover.

If Codeception is NOT available: skip this section, proceed to manual checks.
</existing_tests>

<smoke_test>
**1. Smoke Test — Is it alive?** (curl + WP-CLI)

```bash
SITE_URL=$(ddev wp option get siteurl)

# Site responds
curl -sI "$SITE_URL" | grep "HTTP/"
# Expected: HTTP/2 200

# Admin responds
curl -sI "$SITE_URL/wp-admin/" | grep "HTTP/"
# Expected: 302 (redirect to login) or 200

# REST API base
curl -s "$SITE_URL/wp-json/" | head -20
# Expected: JSON with site info, not 404 or 500

# Batch check multiple pages from the plan
for page in "/" "/page-1" "/page-2"; do
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL$page")
  echo "$page: $STATUS"
done

# PHP error log
ddev exec cat wp-content/debug.log 2>/dev/null | tail -50 || echo "No debug.log"
# Expected: No recent fatal errors

# WP-CLI health check
ddev wp eval "echo 'PHP OK';"
# Expected: "PHP OK" with no warnings above it
```
</smoke_test>

<plugin_theme_state>
**2. Plugin / Theme State** (WP-CLI only)

```bash
# All expected plugins active
ddev wp plugin list --status=active --format=table

# No unexpected deactivated plugins
ddev wp plugin list --status=inactive --format=table

# Active theme correct
ddev wp theme list --status=active --format=table

# No PHP fatal on eval
ddev wp eval "echo 'EVAL OK';"
```
</plugin_theme_state>

<custom_endpoints>
**3. Custom Endpoints / REST API** (curl only)

For each custom REST API endpoint the build created:

```bash
SITE_URL=$(ddev wp option get siteurl)

# Endpoint exists and responds
curl -s -w "\nHTTP %{http_code}" "$SITE_URL/wp-json/[namespace]/[route]"
# Expected: 200 with expected JSON

# POST with expected data
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"key": "value"}' \
  "$SITE_URL/wp-json/[namespace]/[route]"

# Bad input returns 400, not 500
curl -s -X POST -d '{}' "$SITE_URL/wp-json/[namespace]/[route]"
# Expected: 4xx with validation error, NOT 500

# Auth-required endpoint — generate nonce via WP-CLI
NONCE=$(ddev wp eval "echo wp_create_nonce('wp_rest');")
curl -s -H "X-WP-Nonce: $NONCE" "$SITE_URL/wp-json/[namespace]/[route]"
```
</custom_endpoints>

<page_content>
**4. Page Content Checks** (curl + grep — NO browser needed)

WordPress with YOOtheme is server-rendered. Check HTML response directly:

```bash
SITE_URL=$(ddev wp option get siteurl)

# Check specific element exists on page
curl -s "$SITE_URL/[page]" | grep -c '[expected-class-or-id]'
# Expected: 1 or more

# Check page title
curl -s "$SITE_URL/[page]" | grep -oP '<title>\K[^<]+'

# Check for PHP errors/warnings in HTML output
curl -s "$SITE_URL/[page]" | grep -i "fatal\|warning\|notice.*:" | head -5
# Expected: nothing

# Check multiple pages for errors in one shot
for page in "/" "/page-1" "/page-2" "/page-3"; do
  ERRORS=$(curl -s "$SITE_URL$page" | grep -ci "fatal\|error.*:")
  echo "$page: $ERRORS errors in HTML"
done

# Verify specific content rendered
curl -s "$SITE_URL/[page]" | grep -c 'expected-text-or-heading'

# Check form exists on page
curl -s "$SITE_URL/[page]" | grep -c '<form.*[form-identifier]'

# Check shortcode rendered (not raw)
curl -s "$SITE_URL/[page]" | grep -c '\[shortcode'
# Expected: 0 (shortcodes should be rendered, not raw)
```
</page_content>

<database_integrity>
**5. Database Integrity** (WP-CLI only)

```bash
# Custom tables exist (if build created any)
ddev wp db query "SHOW TABLES LIKE '%custom_table%';"

# Expected options set
ddev wp option get [option_name]

# Transients not stale
ddev wp transient list --format=table 2>/dev/null || echo "No transient command"

# Custom post type has data
ddev wp post list --post_type=[cpt_name] --format=table

# No orphaned postmeta (sanity check)
ddev wp db query "SELECT COUNT(*) FROM wp_postmeta WHERE post_id NOT IN (SELECT ID FROM wp_posts);"
```
</database_integrity>

<cron_scheduled>
**6. Cron & Scheduled Tasks** (WP-CLI only)

```bash
# Cron events registered
ddev wp cron event list --format=table

# Specific hook exists
ddev wp cron event list --fields=hook,next_run_relative --format=table | grep "[expected_hook]"

# Handler function hooked
ddev wp eval "echo has_action('[hook_name]') ? 'HOOKED' : 'NOT HOOKED';"
```
</cron_scheduled>

<filesystem_config>
**7. File System & Config** (bash only)

```bash
# Uploads directory writable
ddev exec test -w wp-content/uploads && echo "WRITABLE" || echo "NOT WRITABLE"

# Composer autoload intact (Bedrock)
ddev exec test -f /var/www/html/vendor/autoload.php && echo "EXISTS" || echo "MISSING"

# Expected config values present
ddev wp config get [CONSTANT_NAME] 2>/dev/null || echo "NOT DEFINED"
```
</filesystem_config>

<cache_performance>
**8. Cache & Performance** (curl + WP-CLI)

```bash
# Object cache status (if Redis)
ddev wp redis status 2>/dev/null || echo "No Redis"

# Page not serving stale content
curl -sI $(ddev wp option get siteurl) | grep -i "cache-control"

# Query Monitor active (if available)
ddev wp eval "echo defined('SAVEQUERIES') ? 'Query logging ON' : 'OFF';"
```
</cache_performance>

<browser_checks>
**9. Interaction & Behavior Checks** (chrome-devtools MCP)

**What to test here comes from the plan.** Read the plan document and identify every feature that involves user interaction. Then apply the matching pattern below.

Always start with setup + JS error baseline:

```
mcp__chrome-devtools__new_page  url: SITE_URL
mcp__chrome-devtools__list_console_messages  level: "error"
```

Then for each interactive feature the plan describes, use the matching pattern:

<pattern name="admin-login">
**When:** Feature involves admin panel, settings page, or any authenticated area.

```
mcp__chrome-devtools__navigate_page  url: SITE_URL/wp-login.php
mcp__chrome-devtools__fill  selector: "#user_login"  value: "[from env/config]"
mcp__chrome-devtools__fill  selector: "#user_pass"   value: "[from env/config]"
mcp__chrome-devtools__click  selector: "#wp-submit"
mcp__chrome-devtools__evaluate_script  expression: "window.location.href.includes('wp-admin') ? 'ADMIN OK' : 'LOGIN FAILED'"
```
</pattern>

<pattern name="form-submission">
**When:** Feature creates, edits, or submits data through a form (contact, settings, CRUD, enrollment).

```
# Navigate to the form
mcp__chrome-devtools__navigate_page  url: [url-from-plan]
# Fill each field the plan specifies
mcp__chrome-devtools__fill  selector: [selector]  value: [test-value]
# ... repeat for each field
# Submit
mcp__chrome-devtools__click  selector: [submit-selector]
# Wait for response
mcp__chrome-devtools__wait_for  selector: [success-or-error-selector]
# Verify outcome
mcp__chrome-devtools__evaluate_script  expression: [check for success/error message]
# Check console
mcp__chrome-devtools__list_console_messages  level: "error"
```

**Then verify side effects with WP-CLI:**
```bash
# Did the data persist? (adapt query to what the form saves)
ddev wp db query "SELECT * FROM [table] ORDER BY id DESC LIMIT 1;"
# or: ddev wp post list --post_type=[cpt] --orderby=date --order=DESC --posts_per_page=1
# or: ddev wp option get [option]
# or: ddev wp user meta get [user_id] [key]
```
</pattern>

<pattern name="filter-search-sort">
**When:** Feature has filtering, search, sorting, or any UI that dynamically updates content.

```
# Load the page with filterable content
mcp__chrome-devtools__navigate_page  url: [url-from-plan]
# Record initial state
mcp__chrome-devtools__evaluate_script  expression: "document.querySelectorAll('[item-selector]').length"
# Trigger the filter/search/sort
mcp__chrome-devtools__click  selector: [filter-trigger]
# or: mcp__chrome-devtools__fill + click for search
# Wait for content update
mcp__chrome-devtools__wait_for  selector: [results-container]
# Verify results changed
mcp__chrome-devtools__evaluate_script  expression: "document.querySelectorAll('[item-selector]').length"
```
</pattern>

<pattern name="pagination">
**When:** Feature has paginated content or load-more.

```
mcp__chrome-devtools__navigate_page  url: [url-from-plan]
# Capture first page content
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('[first-item]')?.textContent"
# Navigate to next page
mcp__chrome-devtools__click  selector: [next-page-selector]
mcp__chrome-devtools__wait_for  selector: [content-container]
# Verify content changed
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('[first-item]')?.textContent"
```
</pattern>

<pattern name="multi-step-flow">
**When:** Feature is a wizard, checkout, enrollment, onboarding, or any flow with sequential steps.

```
# For each step in the flow (from the plan):
# Step N:
mcp__chrome-devtools__navigate_page  url: [flow-entry-from-plan]  # (only step 1)
mcp__chrome-devtools__click  selector: [trigger-from-plan]
mcp__chrome-devtools__wait_for  selector: [next-step-indicator]
mcp__chrome-devtools__fill  selector: [fields-from-plan]  value: [test-data]
mcp__chrome-devtools__click  selector: [proceed-selector]
# ... repeat per step ...
# Final: verify completion
mcp__chrome-devtools__wait_for  selector: [completion-indicator]
mcp__chrome-devtools__evaluate_script  expression: [verify final state]
mcp__chrome-devtools__list_console_messages  level: "error"
```

**Then verify all side effects:**
```bash
# Adapt to what the flow creates — posts, meta, invoices, emails, status changes
ddev wp eval "[PHP check from plan context]"
```
</pattern>

<pattern name="modal-overlay">
**When:** Feature opens modals, lightboxes, offcanvas panels, or overlays.

```
mcp__chrome-devtools__navigate_page  url: [url-from-plan]
mcp__chrome-devtools__click  selector: [trigger]
mcp__chrome-devtools__wait_for  selector: [modal-selector]
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('[modal-selector]')?.offsetHeight > 0 ? 'VISIBLE' : 'HIDDEN'"
# Interact with modal content (fill, click, etc.)
# Close modal
mcp__chrome-devtools__click  selector: [close-selector]
# or: mcp__chrome-devtools__press_key  key: "Escape"
```
</pattern>

<pattern name="screenshot-batch">
**When:** Always — at the end of browser checks, screenshot key pages for human review.

```
# Screenshot each page the plan identifies as important
mcp__chrome-devtools__navigate_page  url: [page-from-plan]
mcp__chrome-devtools__take_screenshot
# ... repeat for each key page
```
</pattern>

**Selecting patterns:** Read the plan. For each feature listed, ask: "Does this involve user interaction?" If yes, pick the closest pattern. Features may combine patterns (e.g., a form inside a modal = modal + form-submission). Unknown interaction types: describe what the plan says and construct the test from first principles using navigate → interact → wait → verify → check-console.

</browser_checks>

<remote_checks>
**10. Remote Environment (if checking staging/production)**

Only run these if the build was deployed to a remote environment.
Use SSH patterns from CLAUDE.md:

```bash
# Ploi sites
ssh ploi-staging "cd /home/ploi/[site.tld] && wp --path=web/wp option get siteurl"

# Combell sites
ssh combell-[site]-staging "cd [site-path] && wp --path=app/wp option get siteurl"

# Check remote debug log
ssh [server] "tail -50 [path]/web/wp-content/debug.log 2>/dev/null || echo 'No debug.log'"

# Remote plugin state
ssh [server] "cd [path] && wp --path=[wp-path] plugin list --status=active --format=table"
```
</remote_checks>

</sweep_checklist>

<manual_checklist_guidance>

After automated sweep, generate manual checks ONLY for:

1. Visual layout verification (YOOtheme Pro rendering, custom CSS)
2. Responsive behavior (mobile/tablet)
3. Interactive UX flows requiring human judgment
4. Cross-browser rendering (if relevant)
5. Content/copy verification

Be specific — not "check the page" but "verify the hero section shows the gradient overlay on /about."
Keep to 5-10 items.

</manual_checklist_guidance>
