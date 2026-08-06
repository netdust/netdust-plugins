# API Endpoints Reference (same-origin AJAX)

> **Scope: this is the same-origin, nonce-gated `ntdst/api_data/{action}` dispatcher — in-page JS talking to its own site.** It is NOT for cross-origin callers: an anonymous WP nonce is a shared, non-origin-bound token that authenticates nothing for a cookie-less cross-origin request. For a headless/SPA/third-party client on another domain, use `ntdst_router()->rest()` + `NTDST_Cors_Policy` — see `rest-cors.md`.

## Architecture

Two-step nonce flow via WordPress REST API:

```
1. POST /wp-json/ntdst/v1/get_nonce  {action: "my_action"}
   → {success: true, data: {nonce: "abc123"}}

2. POST /wp-json/ntdst/v1/action     {action: "my_action", nonce: "abc123", ...params}
   → {success: true, data: {...}}
```

`ntdst_endpoints()` is instantiated unconditionally by the core loader — there is no `ALLOW_RESTAPI_AJAX` gate (that requirement is obsolete; ignore any older doc that mentions it).

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
}, ['capability' => 'delete_others_posts']);
```

> **Capability choice, not just presence.** The `edit_posts` / `delete_posts` family means
> "may act on MY OWN posts" and is held by Contributors and Authors. A handler acting on
> an arbitrary id acts on *someone else's* row, and the capability that implies is the
> `_others_` variant. Better still, resolve it off the type object
> (`get_post_type_object('artwork')->cap->delete_others_posts`, validated as a non-empty
> string first) so a per-type capability map narrows the gate with you — a literal is
> correct only while `capability_type === 'post'`. Best of all for a single row, use the
> meta capability: `current_user_can('delete_post', $id)`.

## Public vs Protected Actions

```php
// Public actions are listed in NTDST_Endpoints::$public_actions and
// extensible via the `ntdst/api/public_actions` filter. A public action
// only means "no auth required for nonce generation" — handlers must
// NOT assume the caller is authenticated and must treat all input as
// untrusted.
//
// Default public actions (out of the box): get_recent_posts, search_posts,
// send_magic_link. NOTE: search_users is NOT public — it is cap-gated
// in-handler (current_user_can('list_users')); see below.

// Add custom public action:
add_filter('ntdst/api/public_actions', function($actions) {
    $actions[] = 'get_artworks';
    return $actions;
});
```

### `search_users` requires `list_users` capability

The default `search_users` handler enforces `current_user_can('list_users')` before returning results. Listing users by email/login is a PII leak; without the capability, an authenticated caller with a valid nonce would have been able to enumerate the user base. If your project needs broader access, override the action with a custom handler that applies your own capability check.

## JavaScript Client

The client is `ntdst-core/assets/js/ntdst-api.js`, enqueued by
`ntdst_enqueue_api_client()` (which localizes the required `wp_rest` nonce as
`window.ntdstAPIConfig.restNonce`). It exposes exactly `call(action, params)`,
`upload(action, formData)` and `download(action, params)` — no `getRecentPosts()` /
`searchPosts()` wrappers; call built-in actions by name. It self-skips when
`window.ntdstAPI` already exists, so loading it beside a theme bundle that inlines its
own copy is a no-op.

```javascript
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
- **Auth gate**: `check_action_permission()` refuses a non-public action from an
  anonymous caller, symmetric with `check_nonce_permission()`. This used to rely
  indirectly on "anon can't mint a nonce for a non-public action" plus per-handler login
  checks — so a handler that forgot its own check, combined with any nonce leak, became
  an exposed surface.
- **CSRF protection**: `Origin` / `Referer` header validation. The referer prefix check uses `home_url('/')` and `site_url('/')` (with trailing slash) so attacker-controlled subdomains like `example.com.evil.com` can't pass a prefix match on `https://example.com`.

> **`verifyOrigin()` fails open.** With **no `Origin`, no `Referer` and no auth cookie**
> it returns `true`. That is coherent for what it is — a defence for a logged-in user's
> browser against cross-site request forgery — but it is not an authentication gate: a
> non-browser client simply omits both headers and is admitted. **Public actions are
> internet-facing**, and must carry their own authorization (the post-type gate below,
> plus an in-handler capability check for anything sensitive).
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

> This filter widens the **same-origin CSRF gate**'s `Origin`/`Referer` allow-list for the `api_data` path — it does NOT turn `Endpoints` into a cross-origin JSON API. A real cross-origin endpoint (CORS preflight, `Access-Control-*` headers, cookie-less caller) is `ntdst_router()->rest()` + `NTDST_Cors_Policy` — see `rest-cors.md`.

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

### The post-type gate (`canQueryPostType`) — the convergence point

`get_recent_posts` and `search_posts` are **public**, so the post type is named by an
unauthenticated caller and the router builds its query straight from that string. No
registry flag governs anything on this surface unless *this* gate reads it. It is the
single place the question is decided; do not answer it a second way elsewhere.

What it reads, exhaustively:

- **`public === true` AND `exclude_from_search === false`** → admitted outright. Not
  `public` alone: `public => true, exclude_from_search => true` is WordPress's standard
  "reachable by its own URL, never surfaced by search" idiom — an embargoed press kit —
  and short-circuiting on `public` served every row of such a type to anonymous callers,
  the precise opposite of the registration's meaning. Nothing upstream closes this:
  `WP_Query` consults `exclude_from_search` only on the `post_type => 'any'` branch, and
  this router always names the type. `is_post_type_viewable()` closes nothing either — it
  reads `publicly_queryable ?? public`, neither of which is `exclude_from_search`.
- **Otherwise: BOTH the type's own `cap->edit_posts` AND `cap->edit_others_posts`**, read
  off the registered object, each validated as a non-empty string *before*
  `current_user_can()` is called. An unregistered type, or a type whose map omits a
  capability, denies.
- `publicly_queryable` and `show_in_rest` are deliberately **not** consulted — they govern
  the front-end query var and the wp-json controller, and this router goes through
  neither. Honouring another flag means editing the predicate, never assuming.
- Filterable: `ntdst/api/queryable_post_type`. Opening a non-public type here exposes
  every row of it to anonymous callers.

`edit_others_posts` is the load-bearing half. `edit_posts` means "may create and edit MY
OWN posts" — Contributor and Author both hold it — and this handler returns EVERY row of
the type. Requiring only the weaker one once shipped a fix for an anonymous read while
simultaneously handing every non-public type, GDPR `user_request` rows included, to the
lowest content role.

**Callers must refuse the request when the gate returns an empty list**, not query first
and filter after. Core's `post-queries` cache keys on the args and the SQL, never on who
asked, so a post-hoc filter lets one actor's answer be served to the other.

### Unpublished media

`attachment` is a public type, so the gate admits it for everyone — correctly, since
public media is public. But attachments are stored as `post_status = 'inherit'`, so
`search_posts` widens the status when attachments are searched; and `inherit` is a
*pointer* to the parent's status, not a status, so `WP_Query` matches the literal column
and the widening reaches every attachment row, children of drafts included.

`canQueryUnpublishedMedia()` (same both-capabilities test, read off the attachment type's
own map) decides who keeps the full widening. Everyone else gets non-viewable parents
excluded via `post_parent__not_in` — **in the query args**, so the two caller classes can
never share a cache entry and the key changes by itself when a parent's status changes.
Viewability is delegated to `is_post_type_viewable() && is_post_status_viewable()`, not
hand-rolled: a `post_status === 'publish'` test gets the orphan wrong, and the orphan
(`post_parent = 0`, media uploaded straight to the library) is the common case.

## Caching

**There is none, and that is deliberate.** The endpoints layer registers no
cache-invalidation hooks, and `ntdst_endpoints()->clear_post_cache()`,
`NTDST_Query_Cache`, `ntdst_clear_posts_cache()` and `ntdst_invalidate_post_type()` are
all **DELETED**. Core already invalidates its post, `post_meta` and object-term entries
on save, delete and trash — including for writes that never went through the model, which
a layer-owned cache could not see. If you find one of these calls in older code, delete
it; there is nothing left to invalidate. See `data-layer.md` → Caching.
