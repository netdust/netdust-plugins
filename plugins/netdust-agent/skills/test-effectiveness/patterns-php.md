# Test-Effectiveness Patterns — PHP (PHPUnit / Codeception / wp-browser)

Concrete forms of the author-fix for each failure mode, in WordPress idioms. Copy and adapt. Unit/wpunit via PHPUnit/Codeception; functional/acceptance via Codeception + wp-browser. The seven modes are identical to the TypeScript file; the dangerous paths here are WP-shaped: capability checks, nonces, `$wpdb` predicates, transients, WP-Cron, REST permission callbacks.

The rule under all of them: **the test must execute the DANGEROUS path** — the user who lacks the cap, the second site/blog, the un-mocked DB read, the actually-registered hook, the forced cron re-entry — not the privileged happy path.

---

## Mode 1 — Stale fixture: assert the NEW shape at a consumer

```php
// After a meta key or serialized shape changed (e.g. author stored as user ID, not login):
// BAD (stale): fixture posts the old login form, the round-trip stays green
update_post_meta($post_id, '_author_ref', 'user:admin');     // ← lying fixture (old form)

// GOOD: fixture uses the NEW form, and a consumer assertion proves it resolves
update_post_meta($post_id, '_author_ref', 'user:' . $user_id);
public function test_author_display_resolves_id_form_to_display_name(): void {
    $html = render_author_badge(get_post_meta($post_id, '_author_ref', true));
    $this->assertStringContainsString('Jane Doe', $html);     // id → display name
}
```

Audit grep before closing the change:
```bash
grep -rn "user:" wp-content/ tests/   # every match: a consumer OR a stale fixture
```

---

## Mode 2 — Test-world ≠ real-world: test against a pre-existing world

The WP test harness installs a fresh DB and runs `dbDelta` migrations every run — so it can't catch "the live site's table predates the new column." Where the contract is "old data is migrated/backfilled", seed an OLD row first.

```php
public function test_upgrade_routine_backfills_existing_rows(): void {
    global $wpdb;
    // seed a row in the OLD shape (no new column), as a live site would have:
    $wpdb->query("INSERT INTO {$wpdb->prefix}myplugin_items (name) VALUES ('legacy')");
    myplugin_run_upgrade('1.2.0');                            // the dbDelta + backfill routine
    $row = $wpdb->get_row("SELECT * FROM {$wpdb->prefix}myplugin_items WHERE name='legacy'");
    $this->assertNotNull($row->status);                      // legacy row got the new column populated
}
```

And assert the plugin self-heals on load: a test that calls the version-gated upgrade hook (`plugins_loaded` / `admin_init` version check) against a stale `option('myplugin_db_version')` and confirms the schema is corrected — the structural fix, mirroring migrate-at-boot.

---

## Mode 3 — Wire-mock leak: don't stub the thing you verify

```php
// BAD: stubs the data layer it claims to test — proves nothing about the query
$repo = $this->createMock(ItemRepository::class);
$repo->method('visible_for')->willReturn([$allowed_item]);   // ← testing the mock

// GOOD: hit the REAL query with a real $wpdb, assert the predicate filters
public function test_visible_for_excludes_other_users_private_items(): void {
    $mine   = self::factory()->post->create(['post_author' => $me,    'post_status' => 'private']);
    $theirs = self::factory()->post->create(['post_author' => $other, 'post_status' => 'private']);
    wp_set_current_user($me);
    $ids = (new ItemRepository())->visible_for($me);          // real WP_Query / $wpdb
    $this->assertContains($mine, $ids);
    $this->assertNotContains($theirs, $ids);                 // the un-mocked predicate actually excludes
}
```

For a JS↔PHP wire (an AJAX/REST endpoint a script calls), add a Codeception functional test that sends the REAL request, rather than mocking the response in JS.

---

## Mode 4 — Unmounted / unwired: assert the hook is registered, drive the real callback

The WP-specific trap: a `register_rest_route` permission callback, an `add_action`, or a capability check that exists in a function but was never hooked — or hooked on one path, not its twin.

```php
// Assert the guard is actually WIRED, not just defined:
public function test_rest_route_has_a_permission_callback(): void {
    $routes = rest_get_server()->get_routes();
    $this->assertArrayHasKey('/myplugin/v1/items', $routes);
    foreach ($routes['/myplugin/v1/items'] as $handler) {
        $this->assertNotSame('__return_true', $handler['permission_callback']);  // not wide open
    }
}

// Drive the guard through the REAL dispatch (catches "callback defined but not enforced"):
public function test_create_item_denied_for_subscriber(): void {
    wp_set_current_user(self::factory()->user->create(['role' => 'subscriber']));
    $req = new WP_REST_Request('POST', '/myplugin/v1/items');
    $req->set_param('title', 'x');
    $res = rest_get_server()->dispatch($req);                // real dispatch, not a direct call
    $this->assertSame(403, $res->get_status());
}

// Sibling sweep: the admin-ajax twin of the same action must ALSO be guarded
public function test_ajax_twin_also_checks_capability(): void { /* same denial via wp_ajax_ handler */ }
```

---

## Mode 5 — Happy-path-only: the RED-first denial (cap + nonce), across siblings

```php
// Write the DENIAL first. Two WP denial axes: capability AND nonce — assert both.
public function test_save_settings_denied_without_manage_options(): void {
    wp_set_current_user(self::factory()->user->create(['role' => 'editor']));  // lacks manage_options
    $_POST['_wpnonce'] = wp_create_nonce('myplugin_save');
    $this->expectException(WPDieException::class);            // current_user_can() → wp_die
    myplugin_handle_save();
}

public function test_save_settings_denied_with_bad_nonce(): void {
    wp_set_current_user(self::factory()->user->create(['role' => 'administrator']));
    $_POST['_wpnonce'] = 'bogus';
    $this->expectException(WPDieException::class);            // check_admin_referer() fails
    myplugin_handle_save();
}

// Sibling sweep: every admin action / AJAX handler / REST write of the same plugin
// must have BOTH the cap-denial and nonce-denial test — enumerate them, don't test one.
```

---

## Mode 6 — No coverage: test rendered output + forced failure, not internals

```php
// Render contract (what the user sees), not just the data:
public function test_shortcode_renders_a_visible_price(): void {
    $html = do_shortcode('[myplugin_price id="' . $id . '"]');
    $this->assertStringContainsString('€', $html);           // the rendered, formatted output
    $this->assertStringNotContainsString('{{', $html);       // no unrendered template token
}

// Forced-failure contract: exercise the error branch, not only success
public function test_swallowed_wp_error_is_surfaced(): void {
    add_filter('pre_http_request', fn() => new WP_Error('http_fail', 'down'));  // force the failure
    $result = myplugin_fetch_remote();
    $this->assertWPError($result);                           // the error is RETURNED, not swallowed to null
}
```

WP-specific masking to defeat: a handler that `try { } catch { return null; }` or ignores a `WP_Error` — the happy test never triggers the failure, so force it with a filter.

---

## Mode 7 — Concurrency / timing: WP-Cron re-entry, transient races, run ≥3×

```php
// WP-Cron / scheduled task re-entry: assert the lock prevents overlap
public function test_cron_task_does_not_run_concurrently(): void {
    set_transient('myplugin_job_lock', 1, 60);               // simulate a prior run still holding the lock
    $ran = myplugin_run_scheduled_job();                     // second invocation
    $this->assertFalse($ran);                                // skipped — lock held (no double-processing)
}

// Transient/option read-modify-write race: assert the atomic path
public function test_counter_increment_is_atomic(): void {
    // prefer a single SQL UPDATE … SET n = n + 1 over get_option/update_option (read-modify-write loses races)
    myplugin_increment_counter(); myplugin_increment_counter();
    $this->assertSame(2, (int) get_option('myplugin_counter'));
}
```

Determinism box — the new/changed timing test green every run:
```bash
for i in 1 2 3; do vendor/bin/phpunit --filter=test_cron_task_does_not_run_concurrently || exit 1; done
```

---

## Acceptance (Codeception + wp-browser) — the un-mocked crossing

When a mode only proves out against the real browser/site (Mode 6 interaction, a JS↔PHP wire in Mode 3), a wpbrowser acceptance step is the un-mocked crossing:

```php
public function subscriber_cannot_reach_settings_page(AcceptanceTester $I): void {
    $I->loginAs('subscriber_user', 'pass');
    $I->amOnAdminPage('admin.php?page=myplugin-settings');
    $I->see('Sorry, you are not allowed to access this page');   // the real cap gate, end to end
}
```

Use acceptance sparingly — it's the slow layer (WebDriver cold-start dominates). One un-mocked crossing per dangerous wire, not a full suite.
