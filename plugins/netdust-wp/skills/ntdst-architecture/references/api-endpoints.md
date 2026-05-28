# API Endpoints Reference

## Architecture

Two-step nonce flow via WordPress REST API:

```
1. POST /wp-json/ntdst/v1/get_nonce  {action: "my_action"}
   → {success: true, data: {nonce: "abc123"}}

2. POST /wp-json/ntdst/v1/action     {action: "my_action", nonce: "abc123", ...params}
   → {success: true, data: {...}}
```

Requires `ALLOW_RESTAPI_AJAX` constant in wp-config.php.

The class is `NTDST_Endpoints` (formerly unprefixed `Endpoints`). `class_alias('NTDST_Endpoints', 'Endpoints')` is kept for back-compat — new code should reference `NTDST_Endpoints::class`. The REST namespace constant is `REST_NAMESPACE` (formerly `NAMESPACE`).

## Registering Actions

```php
// In a service constructor or via $theme->apiAction():
add_filter('ntdst/api_data/get_artworks', function($data, $params) {
    // 1. Extract & sanitize
    $medium   = sanitize_text_field($params['medium'] ?? '');
    $per_page = absint($params['per_page'] ?? 10);

    // 2. Validate
    if (empty($medium)) {
        return new WP_Error('missing_medium', 'Medium required');
    }

    // 3. Query via Data Manager
    $artworks = ntdst_data()->get('artwork')
        ->where('medium', $medium)
        ->limit($per_page)
        ->get();

    // 4. Format response — empty arrays are now valid successes (see "Empty
    //    results" below). Return WP_Error for failures, an array for success.
    return ['artworks' => $artworks, 'total' => count($artworks)];
}, 10, 2);
```

### Empty results are now valid

`handle_action` distinguishes "no handler registered" (`has_filter('ntdst/api_data/{$action}')` returns false → `unknown_action` error) from "handler returned empty array" (legitimate success body). A search that yields zero results gets a normal success response, not a 404.

### Via Theme API

```php
$theme->apiAction('get_artworks', function($data, $params) {
    // ... same handler
    return ['artworks' => $artworks];
});

// With capability check — note that on failure this now returns a WP_Error,
// which Endpoints::handle_action converts to a proper error response.
// (Old behavior wrapped the failure as an array, which looked like a success
// body to the client.)
$theme->apiAction('delete_artwork', function($data, $params) {
    $id = absint($params['id'] ?? 0);
    return ntdst_data()->get('artwork')->delete($id);
}, ['capability' => 'delete_posts']);
```

## Public vs Protected Actions

```php
// Public actions are listed in NTDST_Endpoints::$public_actions and
// extensible via the `ntdst/api/public_actions` filter. A public action
// only means "no auth required for nonce generation" — handlers must
// NOT assume the caller is authenticated and must treat all input as
// untrusted.
//
// Default public actions (out of the box): get_recent_posts, search_posts,
// search_users, send_magic_link.

// Add custom public action:
add_filter('ntdst/api/public_actions', function($actions) {
    $actions[] = 'get_artworks';
    return $actions;
});
```

### `search_users` requires `list_users` capability

The default `search_users` handler enforces `current_user_can('list_users')` before returning results. Listing users by email/login is a PII leak; without the capability, an authenticated caller with a valid nonce would have been able to enumerate the user base. If your project needs broader access, override the action with a custom handler that applies your own capability check.

## JavaScript Client

```javascript
// ntdstAPI is provided by endpoints-client.js
ntdstAPI.call('get_artworks', { medium: 'oil', per_page: 20 })
    .then(data => {
        console.log(data.artworks);
    })
    .catch(err => {
        console.error(err.message);
    });
```

## Security

- **Nonce verification**: `wp_verify_nonce` on every action call.
- **CSRF protection**: `Origin` / `Referer` header validation. The referer prefix check uses `home_url('/')` and `site_url('/')` (with trailing slash) so attacker-controlled subdomains like `example.com.evil.com` can't pass a prefix match on `https://example.com`.
- **Rate limiting**: default 30 requests per 60 seconds, per-action, **per `(user_id, action)`** for logged-in users and **per `(ip, action)`** for anonymous. The user-id keying avoids false positives for users behind shared NAT (offices, schools, mobile carriers) — they no longer share a bucket.
- **Trusted proxies**: `X-Forwarded-For` is honored only when `REMOTE_ADDR` is in the trusted-proxy list.

### Per-action rate limits

Sensitive operations should be much stricter than the default 30/min. Use the `ntdst/api/rate_limit/{action}` and `ntdst/api/rate_window/{action}` filters. Setting the limit to `0` disables rate limiting for that action (use for trusted background workflows).

```php
// Magic-link send: 3 per hour per user/IP. Closes a real abuse vector —
// without this, an attacker can POST send_magic_link 30x/minute to spam
// a victim's inbox and exhaust SMTP quota.
add_filter('ntdst/api/rate_limit/send_magic_link', fn() => 3);
add_filter('ntdst/api/rate_window/send_magic_link', fn() => 3600);

// Password reset: 5 per 15 minutes.
add_filter('ntdst/api/rate_limit/password_reset', fn() => 5);
add_filter('ntdst/api/rate_window/password_reset', fn() => 900);

// Internal background action: unrestricted.
add_filter('ntdst/api/rate_limit/cron_sync', fn() => 0);
```

### Custom allowed origins

```php
add_filter('ntdst/api/allowed_origins', function($origins) {
    $origins[] = 'https://external-app.com';
    return $origins;
});

// Custom trusted proxies (filter name is historical — keep `netdust_*` for
// back-compat, but don't propagate the prefix to new filters).
add_filter('netdust_trusted_proxies', function($proxies) {
    $proxies[] = '10.0.0.1';
    return $proxies;
});
```

## Cache Clearing

Per-post entries (`post_meta_{id}`, `post_terms_{id}`) auto-clear on `save_post`, `deleted_post`, `trashed_post`. **Query caches invalidate via `NTDST_Query_Cache`'s per-post-type version bump** — there is no longer a `wp_cache_flush_group` on every mutation. Manual clear of the per-post entries:

```php
ntdst_endpoints()->clear_post_cache($post_id);
```

Manual clear is only needed when you've made changes outside the normal CRUD flow (raw SQL writes, bulk imports). For per-post-type invalidation use `ntdst_invalidate_post_type('artwork')`.
