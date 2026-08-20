# NTDST Pages

Minimal URL routing with WordPress template integration.

**Location:** `app/content/mu-plugins/ntdst-core/core/Pages.php`

## Global Helpers

Both helpers are wrapped in `function_exists()` guards.

```php
ntdst_pages()                              // Get the Pages singleton
ntdst_pages()->path('/path/:param', $callback)      // Quick route registration
```

## URL Pattern Routes

Pattern-based routing with named parameters:

```php
// GET route with parameter
ntdst_pages()->path('api/items/:id', function($params, $template) {
    $item = get_item($params['id']);
    return ntdst_response()->with('item', $item)->template('item/detail');
});

// POST route — the METHOD is path()'s third argument. There is no ->post()
// (nor ->get(), nor ->register()); path() is the only pattern-route entry point.
ntdst_pages()->path('api/items', function($params, $template) {
    // Handle POST request
    return ['success' => true];
}, 'POST');
```

### Pattern compilation

Literal segments in route patterns are `preg_quote`'d, so regex meta characters in URLs are matched literally. `/v1.0/users` matches that exact path — it does NOT also match `/v1Xusers`. Same for `+`, `(`, `)`, `?`, etc.

### What the callback receives

Two arguments: `($params, $template)`. `$params` holds the named URL placeholders captured from the pattern. **Query-string params are NOT passed** — handlers that need `?page=2` must read `$_GET` directly.

## Template Hooks

Hook into WordPress template types:

```php
// Single post template
ntdst_pages()->single('portfolio', function($post) {
    return ntdst_response()
        ->with('project', $post)
        ->template('portfolio/single');
});

// Archive template
ntdst_pages()->archive('portfolio', function() {
    $projects = ntdst_data()->get('portfolio')->all();
    return ntdst_response()
        ->with('projects', $projects)
        ->template('portfolio/archive');
});

// Specific page by slug
ntdst_pages()->page('about', function($post) {
    return ntdst_response()->template('pages/about');
});
```

## Conditional Routes

Execute when condition is true:

```php
ntdst_pages()->when(
    fn() => get_query_var('my_action') === 'special',
    fn() => $this->handleSpecialAction()
);
```

> **Don't loop `when()`.** Every call registers a new `template_include` filter that runs on every request. Call once per condition.

## Custom URL Endpoints

For custom URLs like `/share/exhibitions/:slug`, you need **both** rewrite rules AND a page route:

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
            // Pattern → index.php with a query var. The NAME is yours —
            // NTDST_Pages matches on REQUEST_URI, not on this var. The rule
            // exists only so WordPress does not 404 the URL first.
            add_rewrite_rule(
                '^share/items/([^/]+)/?$',
                'index.php?myproject_route=1',
                'top'
            );
        });

        // Register query var
        add_filter('query_vars', fn($vars) => array_merge($vars, ['myproject_route']));
    }

    // NTDST_Pages handles the actual logic
    private function registerRoutes(): void
    {
        ntdst_pages()->path('share/items/:slug', function($params) {
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

A route callback's return value drives what NTDST_Pages does next. The contract applies to `path()`, `when()` and `template()` callbacks alike.

| Return Value | NTDST_Pages Behavior |
|--------------|-----------------|
| `null` or `true` | Callback handled output itself — the request is `exit`ed |
| `false` | Fall through to the next matching route (or default WP behavior) |
| String (existing file path) | Used as the resolved template |
| `NTDST_Response`, status **2xx** | The 404 WordPress pre-set is cleared, the Response is rendered, and the request exits — on `path()` pattern routes as well as template-hook callbacks (a Response returned from a pattern route used to silently fall through to the default template; that latent bug is fixed) |
| `NTDST_Response`, status **>= 400** | **REFUSE.** The status is sent, WordPress's not-found state is left intact and **its own 404 template renders** — your Response's template is NOT used. This is how a route says "no" through the output class instead of hand-rolling `status_header()`. Do not expect an error page you named here to appear |
| Anything else | Fall through to the next matching route (unrecognized types continue scanning, matching the original loop behavior) |

> A common footgun: a callback that forgets to return anything implicitly returns `null`, which **exits the request**. If you see a blank page from a route that "isn't running", check for missing `return` statements first.

### Rendering your OWN denied page

The `>= 400` branch is how a route REFUSES; it is not a way to name an error page.
A Response carrying both a 4xx status and a template gets the status honoured and the
template dropped. Two clean options, in order of preference:

```php
// 1. WP owns the denial. Return the >= 400 Response; WordPress renders its own
//    not-found template. Customise 404.php if the denial needs to read differently.
return ntdst_response()->error('Not yours', 403);

// 2. YOUR page, through the output class. Return a 2xx Response naming your
//    template — the 2xx arm clears the pre-set 404 and renders it. The page says
//    "denied"; the STATUS says 200, which is the trade you are making.
return ntdst_response()->with('reason', 'not_yours')->template('errors/denied');
```

**Do not hand-roll `status_header()` in the callback.** That is precisely what the
status split exists to remove — it was the old shape, where a route had to send 404
back after a premature 200. If you genuinely need a 403 status AND your own body,
you are asking for something the return contract does not express: render and exit
inside the callback (`->render()` exits) and accept that you now own the status
yourself, with nothing checking that status and page agree.

## Route Priority

Routes are matched in order of registration. More specific routes should be registered first:

```php
// Register specific route first
ntdst_pages()->path('items/featured', $featuredHandler);
// Then generic route
ntdst_pages()->path('items/:id', $itemHandler);
```

## Using with Theme Fluent API

The Theme class wraps NTDST_Pages for convenience:

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

### API-style JSON endpoint (same-origin, front-end pipeline)

```php
ntdst_pages()->path('api/search/:term', function($params) {
    // NB: the chain API has NO search() method — there is no full-text
    // search on the model. Free-text goes through WP_Query's own `s`, which
    // ntdst_get_formatted_posts() passes straight through.
    $results = ntdst_get_formatted_posts([
        's'              => $params['term'],
        'post_type'      => 'post',
        'posts_per_page' => 20,
    ]);

    return ntdst_response()
        ->with('results', $results)
        ->json(); // Returns JSON and exits
});
```

> This runs on the front-end `template_include` pipeline and has **no CORS/preflight handling** — fine for a same-origin fetch, wrong for a real API. A **cross-origin** JSON endpoint (a headless SPA, a third-party integration, anything needing preflight + an origin allow-list) belongs on `ntdst_rest()`, which registers through native WP REST dispatch with a required `permission` callable. **CORS itself has no home in ntdst-core 4.x** — see the warning at the top of `rest-cors.md` before you design one.

### Redirect route

`NTDST_Pages::redirect()` defaults to `wp_safe_redirect` — it restricts the target to the same host as the site, blocking open-redirect attacks when the URL is derived from user input. The `$allowExternal` flag opts into `wp_redirect` for trusted off-site destinations.

```php
ntdst_pages()->path('old-path/:slug', function($params) {
    ntdst_pages()->redirect('/new-path/' . $params['slug'], 301);
    // exits
});

// Trusted external redirect (e.g. handoff to a payment provider you control)
ntdst_pages()->path('checkout/:order', function($params) {
    $url = build_external_checkout_url($params['order']);
    ntdst_pages()->redirect($url, 302, allowExternal: true);
});
```

### Generating URLs

`NTDST_Pages::url()` substitutes `:placeholders` and URL-encodes each value so slashes, spaces, and hashes can't break the path. Extra keys that don't match a placeholder are silently dropped — they are NOT appended as query string.

```php
ntdst_pages()->url('items/:slug', ['slug' => 'hello world']);
// → https://example.com/items/hello+world

ntdst_pages()->url('items/:slug', ['slug' => 'a/b']);
// → https://example.com/items/a%2Fb  (slash encoded; route still matches)
```

### Protected route

```php
ntdst_pages()->path('dashboard/:section', function($params) {
    if (!is_user_logged_in()) {
        ntdst_pages()->redirect(wp_login_url(home_url('/dashboard/' . $params['section'])));
    }

    return ntdst_response()
        ->with('section', $params['section'])
        ->template('dashboard/section');
});
```

## CLI / test SAPI safety

`$_SERVER['REQUEST_URI']` and `$_SERVER['REQUEST_METHOD']` are absent under CLI and many test SAPIs. NTDST_Pages reads them with `?? ''` / `?? 'GET'` guards and `?? ''`s around `parse_url`, so it doesn't TypeError when invoked from `wp-cli` or PHPUnit integration tests.
