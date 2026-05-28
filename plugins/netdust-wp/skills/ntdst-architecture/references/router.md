# NTDST Router

Minimal URL routing with WordPress template integration.

**Location:** `app/content/mu-plugins/ntdst-core/core/Router.php`

## Global Helpers

Both helpers are wrapped in `function_exists()` guards.

```php
ntdst_router()                              // Get Router singleton
ntdst_route('/path/:param', $callback)      // Quick route registration
```

## URL Pattern Routes

Pattern-based routing with named parameters:

```php
// GET route with parameter
ntdst_router()->get('api/items/:id', function($params, $template) {
    $item = get_item($params['id']);
    return ntdst_response()->with('item', $item)->template('item/detail');
});

// POST route
ntdst_router()->post('api/items', function($params, $template) {
    // Handle POST request
    return ['success' => true];
});
```

### Pattern compilation

Literal segments in route patterns are `preg_quote`'d, so regex meta characters in URLs are matched literally. `/v1.0/users` matches that exact path — it does NOT also match `/v1Xusers`. Same for `+`, `(`, `)`, `?`, etc.

### What the callback receives

Two arguments: `($params, $template)`. `$params` holds the named URL placeholders captured from the pattern. **Query-string params are NOT passed** — handlers that need `?page=2` must read `$_GET` directly.

## Template Hooks

Hook into WordPress template types:

```php
// Single post template
ntdst_router()->single('portfolio', function($post) {
    return ntdst_response()
        ->with('project', $post)
        ->template('portfolio/single');
});

// Archive template
ntdst_router()->archive('portfolio', function() {
    $projects = ntdst_data()->get('portfolio')->all();
    return ntdst_response()
        ->with('projects', $projects)
        ->template('portfolio/archive');
});

// Specific page by slug
ntdst_router()->page('about', function($post) {
    return ntdst_response()->template('pages/about');
});
```

## Conditional Routes

Execute when condition is true:

```php
ntdst_router()->when(
    fn() => get_query_var('my_action') === 'special',
    fn() => $this->handleSpecialAction()
);
```

> **Don't loop `when()`.** Every call registers a new `template_include` filter that runs on every request. Call once per condition.

## Custom URL Endpoints

For custom URLs like `/share/exhibitions/:slug`, you need **both** rewrite rules AND router:

```php
class ShareCardService implements NTDST_Service_Meta
{
    private function init(): void
    {
        $this->registerRewriteRules();
        $this->registerRoutes();
    }

    // Rewrite rules tell WordPress the URL is valid (prevents 404)
    private function registerRewriteRules(): void
    {
        add_action('init', function() {
            // Pattern → index.php with query var
            add_rewrite_rule(
                '^share/items/([^/]+)/?$',
                'index.php?ntdst_route=1',
                'top'
            );
        });

        // Register query var
        add_filter('query_vars', fn($vars) => array_merge($vars, ['ntdst_route']));
    }

    // Router handles the actual logic
    private function registerRoutes(): void
    {
        ntdst_router()->get('share/items/:slug', function($params) {
            return $this->renderCard($params['slug']);
        });
    }

    private function renderCard(string $slug)
    {
        $post = ntdst_data()->get('item')
            ->where('post_name', $slug)
            ->first();

        if (!$post || is_wp_error($post)) {
            return false; // Continue to next route or 404
        }

        return ntdst_response()
            ->with('item', $post)
            ->render('share-cards/item'); // Exits
    }
}
```

**Important:** After adding rewrite rules, flush with:
```bash
ddev wp rewrite flush
```

## Return Values

A route callback's return value drives what the router does next. The contract is documented on `register()` and applies to `get()`, `post()`, `when()`, `template()` callbacks alike.

| Return Value | Router Behavior |
|--------------|-----------------|
| `null` or `true` | Callback handled output itself — the request is `exit`ed |
| `false` | Fall through to the next matching route (or default WP behavior) |
| String (existing file path) | Used as the resolved template |
| `NTDST_Response` (from template hook callbacks) | Response is rendered and the request exits |
| Anything else | Ignored — the original `$template` is returned |

> A common footgun: a callback that forgets to return anything implicitly returns `null`, which **exits the request**. If you see a blank page from a route that "isn't running", check for missing `return` statements first.

## Route Priority

Routes are matched in order of registration. More specific routes should be registered first:

```php
// Register specific route first
ntdst_router()->get('items/featured', $featuredHandler);
// Then generic route
ntdst_router()->get('items/:id', $itemHandler);
```

## Using with Theme Fluent API

The Theme class wraps Router for convenience:

```php
$theme = ntdst_get(NTDST_Theme::class);

$theme->single('portfolio', function($post) {
    return ntdst_response()->template('portfolio/single');
});

$theme->archive('portfolio', function() {
    return ntdst_response()->template('portfolio/archive');
});

$theme->page('contact', function($post) {
    return ntdst_response()->template('pages/contact');
});
```

## Common Patterns

### API-style JSON endpoint

```php
ntdst_router()->get('api/search/:term', function($params) {
    $results = ntdst_data()->get('post')
        ->search($params['term'])
        ->limit(20)
        ->get();

    return ntdst_response()
        ->with('results', $results)
        ->json(); // Returns JSON and exits
});
```

### Redirect route

`Router::redirect()` defaults to `wp_safe_redirect` — it restricts the target to the same host as the site, blocking open-redirect attacks when the URL is derived from user input. The `$allowExternal` flag opts into `wp_redirect` for trusted off-site destinations.

```php
ntdst_router()->get('old-path/:slug', function($params) {
    ntdst_router()->redirect('/new-path/' . $params['slug'], 301);
    // exits
});

// Trusted external redirect (e.g. handoff to a payment provider you control)
ntdst_router()->get('checkout/:order', function($params) {
    $url = build_external_checkout_url($params['order']);
    ntdst_router()->redirect($url, 302, allowExternal: true);
});
```

### Generating URLs

`Router::url()` substitutes `:placeholders` and URL-encodes each value so slashes, spaces, and hashes can't break the path. Extra keys that don't match a placeholder are silently dropped — they are NOT appended as query string.

```php
ntdst_router()->url('items/:slug', ['slug' => 'hello world']);
// → https://example.com/items/hello+world

ntdst_router()->url('items/:slug', ['slug' => 'a/b']);
// → https://example.com/items/a%2Fb  (slash encoded; route still matches)
```

### Protected route

```php
ntdst_router()->get('dashboard/:section', function($params) {
    if (!is_user_logged_in()) {
        ntdst_router()->redirect(wp_login_url(home_url('/dashboard/' . $params['section'])));
    }

    return ntdst_response()
        ->with('section', $params['section'])
        ->template('dashboard/section');
});
```

## CLI / test SAPI safety

`$_SERVER['REQUEST_URI']` and `$_SERVER['REQUEST_METHOD']` are absent under CLI and many test SAPIs. The router reads them with `?? ''` / `?? 'GET'` guards and `?? ''`s around `parse_url`, so it doesn't TypeError when invoked from `wp-cli` or PHPUnit integration tests.
