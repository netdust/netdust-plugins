# REST Registration + CORS (`NTDST_Rest_Registrar` / `NTDST_Cors_Policy`)

The framework has **three** output-producing surfaces, separated by their auth model and request lifecycle — all emit through `NTDST_Response`:

| Surface | Class | Purpose | Auth |
|---|---|---|---|
| Front-end **pages** | `NTDST_Router` | template rendering via `template_include` | page-level, in the callback |
| **AJAX** (same-origin) | `NTDST_Endpoints` (`ntdst/api_data/{action}`) | in-page JS calls | shared WP nonce + `verifyOrigin` CSRF gate |
| **REST API** (incl. cross-origin) | `NTDST_Rest_Registrar` (`ntdst_router()->rest()`) | headless / third-party / SPA clients | required per-route `permission` callable + `NTDST_Cors_Policy` |

> **Choosing the surface.** Same-origin in-page JS → `NTDST_Endpoints` (see `api-endpoints.md`). A **cross-origin** caller (a Lovable/headless SPA on another domain, a third-party integration) → `ntdst_router()->rest()` + `NTDST_Cors_Policy`. Do **not** reach for `Endpoints` for cross-origin: an anonymous WP nonce is a shared, non-origin-bound token that authenticates nothing for a cookie-less cross-origin caller — it gives zero real security while looking like it does.

**Location:** `web/app/mu-plugins/ntdst-core/api/RestRegistrar.php`, `api/CorsPolicy.php`.

This is the convergence point INV-11 names: *every new REST route registers through `ntdst_router()->rest()`, never a raw `register_rest_route()`; every `Access-Control-*` decision is made in `NTDST_Cors_Policy`.*

## Registering a REST route

```php
ntdst_router()->rest('myproject/v1')
    ->post('/submissions', $handler, [
        'permission'     => $permissionCallable,   // REQUIRED — no default
        'args'           => [ /* register_rest_route args schema, passed through */ ],
        'cors'           => new NTDST_Cors_Policy([
            'origins' => ['https://app.example.com'],  // exact scheme://host[:port] — or a callable(string $origin, WP_REST_Request): bool
            'methods' => ['POST', 'OPTIONS'],
            'headers' => ['Content-Type'],
            'max_age' => 600,                          // optional
        ]),
        'max_body_bytes' => 262144,                    // optional; null = no cap
        'max_json_depth' => 20,                        // optional; null = WP core default (512)
    ]);
// also: ->get() ->put() ->patch() ->delete() ->route($route, $methods, $handler, $options)
```

- Route syntax is **WP-native REST regex** (`(?P<id>\d+)`), not Router's `:param`.
- `rest($namespace)` is cached per namespace — repeated calls return the same registrar, so routes accumulate on one instance safely.

### `permission` is required — no default

A route with a missing or non-callable `permission` is **not registered** (`_doing_it_wrong()` + `ntdst_log('api')->error()`). This is INV-1's failure mode moved to framework level: there is no implicit `__return_true`. A public-by-design route must supply its own explicit callable (e.g. an origin/key check).

### Handler return contract (D6)

The handler's return is normalized to a `WP_REST_Response`:

| Handler returns | Wire result |
|---|---|
| `array` | `{success:true, data:<array>}`, status 200 (via `NTDST_Response::apiSuccess()`) |
| `WP_Error` | WP-native error JSON — **the message reaches the wire**; log detail with `ntdst_log()`, return a generic message |
| `WP_REST_Response` | passed through as-is |
| `NTDST_Response` | `->toRestResponse()` (envelope + stored status, no exit) |
| anything else | `WP_Error('invalid_handler_return', …, 500)` + logged |

## `NTDST_Cors_Policy`

Exact-origin allow-listing that **overrides WP core's reflect-any-origin default**. WP core's `rest_send_cors_headers()` (priority 10) reflects any `Origin` and sets `Access-Control-Allow-Credentials: true` — the reflection+credentials anti-pattern. `NTDST_Cors_Policy` registers at **priority 20** (after core), route-scoped, and:

- **always removes** `Access-Control-Allow-Credentials`;
- on an **exact** origin match → echoes that origin + `Vary: Origin` + configured methods/headers;
- on non-match / absent / `Origin: null` → removes `Access-Control-Allow-Origin` so core's reflection can't survive.

Matching is byte-exact `in_array(..., true)` against full `scheme://host[:port]` strings (never substring, never case-folded, never `*` — `'*'` throws at construction). The literal `'null'` and `''` never match.

```php
new NTDST_Cors_Policy([
    'origins' => ['https://app.example.com', 'https://staging.example.com'],
    // or a resolver for dynamic lists:
    // 'origins' => fn(string $o, WP_REST_Request $r): bool => $registry->allows($o),
]);
```

The preflight `OPTIONS` is covered by the same filter (it fires on `rest_pre_serve_request` for all methods).

## The three WP-core quirks (handled centrally — you don't re-derive them)

The registrar + policy absorb three WP-core behaviors that bite every hand-rolled cross-origin endpoint. They are handled once, in the framework:

1. **`rest_send_cors_headers()` reflection** (quirk 1) — overridden by `NTDST_Cors_Policy` at priority 20 (above).
2. **`rest_send_allow_header()` double-invokes `permission_callback`** per request (to compute the `Allow` header). The registrar memoizes each permission result per-request in a **per-wrapper `WeakMap`**, so a side-effectful permission callback (a rate-limit counter) runs once, not twice. (Per-wrapper, not per-registrar — a shared map would leak one route's verdict to another route hit by the same request.)
3. **`WP_REST_Server::dispatch()` JSON-decodes the body at depth 512 before `permission_callback` runs** (quirk 3). `max_body_bytes` / `max_json_depth` enforce via a `rest_pre_dispatch` filter (priority 5) — the only hook that runs earlier — returning a `413`/`400` `WP_Error` before core's parse. The depth check is gated on JSON content-type (a form-encoded body isn't wrongly rejected); the byte cap is content-agnostic.

## Misconfiguration throws; requests never throw

Bad **configuration** (a `'*'` origin, a missing `permission`) is a programmer error caught at construction/registration via `InvalidArgumentException` / `_doing_it_wrong()` — the route/policy simply never goes live. A bad or malicious **request** (disallowed origin, oversized body, invalid JSON) is a normal `WP_Error` / denied-CORS response, never an exception.

## When NOT to use this

- Same-origin in-page AJAX → `NTDST_Endpoints` (`api_data`), not this.
- A front-end HTML page/route → `NTDST_Router` template hooks, not this.
- The pre-existing `PartnerAPIController` / `AdminAPIController` / Assistant ability registrars call `register_rest_route` directly and predate the registrar — that's accepted baseline, not a pattern to copy for new work.
