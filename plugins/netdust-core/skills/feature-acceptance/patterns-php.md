# Feature-acceptance driving patterns — PHP (WordPress / Statamic)

Concrete ways to *drive* an acceptance flow + its edges through the faithful layer in a Codeception + wp-browser project. Pick the layer per flow (see SKILL.md `<driving_layers>`); these are the tools. Prefix runners with `ddev exec ` when `.ddev/` exists.

## UI flow — Codeception acceptance (real browser, durable)

`tests/acceptance/` with the WPWebDriver module drives a real Chrome. Drive the EDGES, not just the happy path.

```php
// tests/acceptance/CreateOrderCest.php
public function createOrder(AcceptanceTester $I)
{
    $I->loginAs('shopmanager', 'pass');
    $I->amOnPage('/wp-admin/admin.php?page=orders');

    // happy path
    $I->click('New order');
    $I->fillField('#order-title', 'Order 1001');
    $I->click('Save');
    $I->see('Order 1001');
    $I->reloadPage();
    $I->see('Order 1001');                       // persisted

    // EDGE: empty submit → validation error, no row, no fatal
    $I->click('New order');
    $I->click('Save');
    $I->see('Title is required');
    $I->dontSee('(untitled)');

    // EDGE: denied actor → a subscriber cannot reach the create flow
    $I->logout();
    $I->loginAs('subscriber', 'pass');
    $I->amOnPage('/wp-admin/admin.php?page=orders');
    $I->seeResponseCodeIs(403);                  // or: dontSeeElement('New order')

    // EDGE: boundary — 255+ char title is rejected or truncated, not a DB error
    $I->loginAs('shopmanager', 'pass');
    $I->amOnPage('/wp-admin/admin.php?page=orders');
    $I->click('New order');
    $I->fillField('#order-title', str_repeat('x', 300));
    $I->click('Save');
    $I->dontSee('database error');
}
```

## UI flow — `use_browser` (one-shot, no acceptance suite)

When no acceptance infra exists and you need to drive the flow once at shake-out: `ddev start`, then drive `superpowers-chrome` `use_browser` against the DDEV URL (see `superpowers-chrome:browsing`). Read back rendered DOM to assert. If the site can't come up, mark the flow `unverified-no-browser` — never `pass`.

## Backend flow — un-mocked through WordPress (functional / WPLoader)

Drive the real handler against a real (test) DB. Assert the persisted row + the side effect (hook fired, meta written) — do not mock the repository you're verifying.

```php
// tests/wpunit/AssignOrderTest.php  (WPLoader — full WP loaded)
public function test_assign_order_happy_and_denial(): void
{
    $manager = $this->factory()->user->create(['role' => 'shop_manager']);
    $order   = $this->makeOrder();

    // happy: drive the REST route through the mounted server
    wp_set_current_user($manager);
    $req = new WP_REST_Request('PATCH', "/myplugin/v1/orders/{$order}");
    $req->set_body_params(['assignee' => $manager]);
    $res = rest_do_request($req);                          // real dispatch, not a mock
    $this->assertSame(200, $res->get_status());
    $this->assertSame($manager, get_post_meta($order, 'assignee', true));

    // EDGE denied actor: a subscriber is refused — drive the FULL request, not the handler fn
    $sub = $this->factory()->user->create(['role' => 'subscriber']);
    wp_set_current_user($sub);
    $denied = rest_do_request($req);
    $this->assertSame(403, $denied->get_status());

    // EDGE nonexistent id → 404, not a fatal
    $missing = rest_do_request(new WP_REST_Request('PATCH', '/myplugin/v1/orders/999999'));
    $this->assertSame(404, $missing->get_status());
}
```

**Mid-flow-failure edge:** force the failure (filter a dependency to return `WP_Error`, or make the meta write fail) and assert the handler returns a real error response and leaves no half-written state — never a swallowed `WP_Error` that reports success. **Concurrency edge:** where two requests can race a single row, assert the deterministic resolution and re-run ≥3×.
