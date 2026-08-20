# API Endpoints Reference (same-origin AJAX)

> **Scope: this is the same-origin, nonce-gated `ntdst/api_data/{action}` dispatcher — in-page JS talking to its own site.** It is NOT for cross-origin callers: an anonymous WP nonce is a shared, non-origin-bound token that authenticates nothing for a cookie-less cross-origin request. For a headless/SPA/third-party client on another domain, use `ntdst_rest()` with a `cors` route option (ntdst-core 4.1.0 — see `rest-cors.md`).

## Architecture

Two-step nonce flow via WordPress REST API:

```
1. POST /wp-json/ntdst/v1/get_nonce  {action: "my_action"}
   → {success: true, data: {nonce: "abc123"}}

2. POST /wp-json/ntdst/v1/action     {action: "my_action", nonce: "abc123", ...params}
   → {success: true, data: {...}}
```

`ntdst_actions()` is instantiated unconditionally by the core loader — there is no `ALLOW_RESTAPI_AJAX` gate (that requirement is obsolete; ignore any older doc that mentions it).

The class is `NTDST_Actions`, in `api/Actions.php` (formerly unprefixed `Endpoints`, in `api/Endpoints.php`). **There is no back-compat alias** — ntdst-core calls `class_alias()` nowhere, so `Endpoints::` is a fatal and `api/Endpoints.php` is a path that no longer exists. Reference `NTDST_Actions::class`. The REST namespace constant is `REST_NAMESPACE` (formerly `NAMESPACE`).

The `ntdst/api_data/{action}` FILTER name is deliberately unchanged from v2: adopters' handlers hang off it, and renaming it would silently unmount every one of them while the code still looked correct.

## Registering Actions

```php
// In a service constructor. (`$theme->apiAction()` is RETIRED — NTDST_Theme has
// no such method or mixin, and its __call() throws BadMethodCallException.)
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
ntdst_actions()->register('get_artworks', function($data, $params) {
    // ... same handler
    return ['artworks' => $artworks];
});

// With a capability floor — on failure the floor returns WP_Error('forbidden',
// …, ['status' => 403]) BEFORE your handler runs, and NTDST_Actions::handle_action()
// converts it to a proper error response. (Old behavior wrapped the failure as an
// array, which looked like a success body to the client.)
//
// `cap_type` is the type-DERIVED form and the one to prefer; a literal
// `capability` is correct only while that type's capability_type is 'post'.
ntdst_actions()->register('delete_artwork', function($data, $params) {
    $id = absint($params['id'] ?? 0);
    return ntdst_data()->get('artwork')->delete($id);
}, ['cap_type' => 'artwork']);
```

`register(string $action, callable $handler, array $opts = [])` takes exactly four
opts — `public`, `cap_type`, `capability`, `priority`:

| Opt | Effect |
|---|---|
| `'public' => true` | Adds the action to `ntdst/api/public_actions`. **Public wins and is NEVER floored** — anonymous reachability is not conditional on a capability |
| `'cap_type' => 'artwork'` | Floor derived from the post type via `ntdst_api_floor_cap()` |
| `'capability' => 'edit_others_posts'` | Literal floor |
| `'priority' => 10` | Filter priority |

The floor bites at DISPATCH, ahead of the handler, and **fails closed**: an empty or
unresolvable capability denies everyone, administrators included. It is ALONGSIDE the
handler's own per-row check, never a replacement. With neither opt the action is
login-required — the router already refuses anonymous callers for anything not on
`public_actions`.

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
// Public actions are listed in NTDST_Actions::$public_actions and
// extensible via the `ntdst/api/public_actions` filter. A public action
// only means "no auth required for nonce generation" — handlers must
// NOT assume the caller is authenticated and must treat all input as
// untrusted.
//
// The framework ships NO public actions and no data actions at all.
// $public_actions is EMPTY: NTDST_Actions is a router (origin, rate limit,
// nonce, auth gate, dispatch) with no opinion about anyone's data. Anonymous
// exposure is a per-site decision, made only via this filter.

// Add custom public action:
add_filter('ntdst/api/public_actions', function($actions) {
    $actions[] = 'get_artworks';
    return $actions;
});
```

### `search_users`, `get_recent_posts`, `search_posts` — RETIRED 2026-08-07

`get_recent_posts` and `search_users` are **deleted**. `send_magic_link` was removed
from the public list (it never had a handler in any tree — an allow-list entry naming
nothing is a standing grant waiting for whoever later registers that action name).
`search_posts` **moved** to `NTDST_RelationField` as the non-public `relation_search`.

The framework provides exactly one data action now, `relation_search`, and it is not
public. Everything else belongs to the service that knows what its rows mean. Older
project copies may still carry the retired actions until ported.

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
- **Gate order — registration, then AUTH, then the bucket, then the nonce.** Registration first (4.0.0): the gate establishes that an action is REGISTERED before anything else. **Auth moved ahead of the limiter in 4.1.0 (M2)**, on both the `/get_nonce` door and the dispatch door: an anonymous caller who could never dispatch a non-public action must not be able to make the site write storage by asking. Charging first meant every doomed anonymous request left two `wp_options` rows behind, reaped only by a daily cron. **The CSRF/origin check deliberately stays BELOW the limiter** — a caller who fails it has already passed auth, so it is a real session being driven from another site, and a CSRF flood is exactly the traffic a throttle should charge; hoisting it would hand an attacker an uncharged path. Registered means listed in `ntdst/api/public_actions`, or having a handler mounted on the dispatch filter. An unregistered action is refused with a bare `false` (401, same as an auth denial), gets **no rate bucket at all**, and cannot obtain a nonce from `/get_nonce`. Until 4.0.0 the raw `action` parameter went straight into the bucket key, so varying it per request bought a fresh bucket every time and defeated the throttle entirely.
- **Rate limiting**: default 30 requests per 60 seconds, per-action, **per `(user_id, action)`** for logged-in users and **per `(ip, action)`** for anonymous. The user-id keying avoids false positives for users behind shared NAT (offices, schools, mobile carriers) — they no longer share a bucket.
- **Counting anything else**: `NTDST_RateLimiter` is the one counter — build the key yourself, pass finished numbers, it resolves no identity of its own. **Three verbs, and picking the wrong one is a real bug:**

  | Call | Does | Use for |
  |---|---|---|
  | `attempt($key, $limit, $window, $memoScope)` | spend a unit AND decide | a **request budget** — every question IS a request |
  | `exceeded($key, $limit)` *(4.2.0)* | ask, spend **nothing** | a **failure counter** — asked far more often than incremented |
  | `reset($key)` | forgive | the caller succeeded; clears the bucket |

  **Do not check a lockout with `attempt()`.** It spends on every question, so the check causes the lockout it is checking for. That is not hypothetical: a login lockout consults `isLockedOut()` twice per attempt (once in the `authenticate` filter, once re-asserting after core auth) while the failure path increments once — asking with `attempt()` locks a user out for trying to log in correctly. `exceeded()` exists for exactly this and is why `reset()` alone was not enough.

  **The `>= $limit` boundary lives IN `exceeded()`.** Do not re-implement it as `$count >= $max` at the call site: a duplicated boundary drifts, and `>` in one of two places turns a three-strike lockout into a four-strike one silently. A limit of `<= 0` is switched OFF and can never be exceeded — `exceeded()` returns `false`, agreeing with `attempt()`, which treats it as always-allow.
- **What the bucket key actually bounds (M3).** Only the ACTION axis is bounded. Be precise here, because a false bound is worse than none — it is what the next reviewer checks against instead of the code: an **unregistered** action reaches no bucket at all; a registered **non-public** action reaches no bucket without credentials (the auth gate runs first); a registered **public** action DOES let an anonymous caller create one bucket per client IP. That last one is not a leak, it is what a public throttle IS — a counter has to be per-caller or it cannot count anybody. The caller axis is unbounded by construction (an attacker on an IPv6 /64 has 2^64 caller values), as in every per-IP throttle ever written. A site that publishes an action accepts per-IP row growth on it; the daily transient cron reaps it.
- **Trusted proxies**: `X-Forwarded-For` is honored only when `REMOTE_ADDR` is in the trusted-proxy list.

### Per-action rate limits

Sensitive operations should be much stricter than the default 30/min. Use the `ntdst/api/rate_limit/{action}` and `ntdst/api/rate_window/{action}` filters. Setting the limit to `0` disables rate limiting for that action (use for trusted background workflows).

```php
// Any action that SENDS something on a caller's say-so: 3 per hour per
// user/IP. Closes a real abuse vector — without this, an attacker POSTs it
// 30x/minute to spam a victim's inbox and exhaust SMTP quota. (The action
// name here is a site's own; the framework ships no such handler.)
add_filter('ntdst/api/rate_limit/my_magic_link', fn() => 3);
add_filter('ntdst/api/rate_window/my_magic_link', fn() => 3600);

// Password reset: 5 per 15 minutes.
add_filter('ntdst/api/rate_limit/password_reset', fn() => 5);
add_filter('ntdst/api/rate_window/password_reset', fn() => 900);

// Internal background action: unrestricted.
add_filter('ntdst/api/rate_limit/cron_sync', fn() => 0);
```

**Budget arithmetic — `get_nonce` consumes the TARGET action's bucket** (daan
record-shop, 2026-08-10). `check_nonce_permission()` resolves the `action` param and
rate-checks it, so an anonymous client's nonce mint costs one unit of that action's
budget. A first-visit public flow (mint + call) costs **2 units**; with a cached
nonce, subsequent calls cost 1. Size per-action limits with that arithmetic — a
"3/60" checkout allows ~2 first-window completions, not 3. (Each HTTP request counts
exactly once: WP core invokes `permission_callback` twice per request — dispatch +
`rest_send_allow_header` — and the limiter memoizes per request-object to compensate.
Do not add side effects to permission callbacks expecting single invocation.)

**Denial statuses are asymmetric on purpose.** A rate-limited request gets `WP_Error
'rate_limited'` → HTTP **429** (clients must know to back off); an auth/origin denial
stays bare `false` → 401 `rest_forbidden` (attackers learn nothing). In handlers:
**refuse with `WP_Error` (with `['status' => n]`), never an `apiError()` array** — the
router intercepts `WP_Error` into a single-wrapped `{success:false}` with the real
4xx, while a returned array rides out as HTTP 200 `success:true`. Successes are
double-wrapped on the wire (handler `apiSuccess()` + router wrap); the JS client
unwraps the outer layer only.

### Custom allowed origins

> This filter widens the **same-origin CSRF gate**'s `Origin`/`Referer` allow-list for the `api_data` path — it does NOT turn `Endpoints` into a cross-origin JSON API. A real cross-origin endpoint (CORS preflight, `Access-Control-*` headers, cookie-less caller) belongs on `ntdst_rest()` with a `cors` route option (ntdst-core 4.1.0 — see `rest-cors.md`).

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

### The post-type gate — DELETED 2026-08-07, with the surface it guarded

`canQueryPostType()`, `filterQueryablePostTypes()`, `canQueryUnpublishedMedia()`,
`nonViewableMediaParentIds()` and `normalizePostTypes()` are **gone**. Do not
reintroduce them, and do not write anything that needs them.

They existed to answer one question — *"an anonymous caller named a post type; may
they query it?"* — for the framework's own `get_recent_posts` and `search_posts`.
Answering it meant re-deriving WordPress's visibility semantics from the registry, a
flag at a time, in a predicate whose own docblock had to list the flags it did NOT
consult. Five consecutive generations of security review went into it: anonymous
enumeration of every non-public type, then a fix gated on `edit_posts` (which
Contributors hold), then draft-attached media, then `exclude_from_search` types, then
an uncached full-attachment scan, then a latent fail-open in a `WP_Query` `elseif`
chain.

Ground truth killed it: `get_recent_posts` had **zero** consumers, `search_users` had
zero, `send_magic_link` had no handler at all, and `search_posts` had exactly one —
the admin relation autocomplete, authenticated by definition. The framework was
defending a surface with no user.

**The lesson, which generalises past this file:** a question that cannot be answered
safely is usually a sign the surface should not exist. The fix was not a better
predicate; it was deleting the caller-parameterised query and moving the one real
consumer somewhere the question is answerable.

### `relation_search` — what replaced it

`NTDST_RelationField::handleRelationSearch()`. **Not public**, so the router requires
a logged-in caller before it runs. Two conditions, and they are the entire gate:

1. **The type must be a declared relation TARGET.** The allow-list is DERIVED from the
   registered schemas — every `post_type` named by a `relation`-typed field. A type
   nobody points a relation field at is unreachable, and nobody has to remember to
   exclude it. Derived, never maintained.
2. **The caller must hold that type's own `edit_others_posts`**, read off the type
   object so a CPT that remaps its capabilities narrows this with it. `edit_posts` is
   deliberately not enough — it means "may edit MY OWN posts", Contributors and Authors
   hold it, and this returns every row of the type.

Empty or non-string capabilities deny. An unregistered type denies.

Attachments keep the `post_status => ['publish', 'inherit']` widening (they are stored
`inherit`, never `publish`, so without it a picker scoped to `attachment` renders and
can never return a result) — but it now needs no media-specific gate of its own.
Everyone who reaches this point may already edit others' posts of the type, which is
the same claim the deleted gates were computing the hard way.


## Caching

**There is none, and that is deliberate.** The endpoints layer registers no
cache-invalidation hooks, and `ntdst_actions()->clear_post_cache()`,
`NTDST_Query_Cache`, `ntdst_clear_posts_cache()` and `ntdst_invalidate_post_type()` are
all **DELETED**. Core already invalidates its post, `post_meta` and object-term entries
on save, delete and trash — including for writes that never went through the model, which
a layer-owned cache could not see. If you find one of these calls in older code, delete
it; there is nothing left to invalidate. See `data-layer.md` → Caching.
