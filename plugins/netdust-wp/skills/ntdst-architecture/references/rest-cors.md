# REST registration and CORS (`NTDST_Rest`)

> **Re-anchored on ntdst-core 4.1.0, 2026-08-20.**
> This file once described `NTDST_Rest_Registrar` and `NTDST_Cors_Policy` with
> `cors`, `max_body_bytes` and `max_json_depth` options. **Those two classes
> never existed in ntdst-core**, and `max_body_bytes` / `max_json_depth` still
> do not — `NTDST_Rest` refuses any route carrying an option it does not know,
> so a route copied from that version never went live at all.
> **`cors` IS real as of 4.1.0** — the shape below, not the old one.

The framework has **three** output-producing surfaces, separated by auth model
and request lifecycle:

| Surface | Class | Purpose | Auth |
|---|---|---|---|
| Front-end **pages** | `NTDST_Pages` | template rendering via `template_include` | page-level, in the callback |
| **Commands** (same-origin AJAX) | `NTDST_Actions` (`ntdst/api_data/{action}`) | in-page JS calls | per-action WP nonce + `verifyOrigin` CSRF gate + registration gate |
| **Resource routes** | `NTDST_Rest` (`ntdst_rest()`) | REST resources, headless / third-party clients | required per-route `permission` callable |

> **Choosing the surface.** Same-origin in-page JS → `NTDST_Actions` (see
> `api-endpoints.md`). Anything resource-shaped, or any caller that is not the
> site's own page → `ntdst_rest()`. Never reach for the `ntdst/api_data` path
> for a **cross-origin** caller: an anonymous WP nonce is a shared,
> non-origin-bound token that authenticates nothing for a cookie-less caller —
> zero real security, while looking like it has some.

**Location:** `api/Rest.php`.

Convergence point: *every new REST route registers through `ntdst_rest()`,
never a raw `register_rest_route()`.*

## Registering a route

```php
ntdst_rest('myproject/v1')
    ->post('/submissions', $handler, [
        'permission'  => $permissionCallable,  // REQUIRED — no default
        'rate_limit'  => 20,                   // optional; omit = no throttle
        'rate_window' => 60,                   // optional; seconds, default 60
        'args'        => [ /* passed through to register_rest_route */ ],
    ]);
// also: ->get() ->put() ->patch() ->delete() ->route($route, $methods, $handler, $options)
```

**The option list is closed.** `NTDST_Rest` consumes `permission`,
`rate_limit`, `rate_window`; it passes `args`, `schema`, `show_in_index` and
`allow_batch` through to WordPress. **Any other key refuses the route** — a
typo'd option is a control the author believes is on, so it fails loudly
instead of registering an unprotected route that reviews as protected.

- Route syntax is **WP-native REST regex** (`(?P<id>\d+)`), not `NTDST_Pages`' `:param`.
- `ntdst_rest($namespace)` is cached per namespace — repeated calls return the
  same instance, so routes accumulate safely.
- Registration defers to `rest_api_init` on its own. Call it whenever you like.

### `permission` is required — no default

A route with a missing or non-callable `permission` is **not registered**
(`_doing_it_wrong()` + `ntdst_log('api')->error()`). There is no implicit
`__return_true`. A public-by-design route supplies its own explicit callable.

### Handler return: WordPress's contract, not a framework one

**`NTDST_Rest` wraps the permission callback, not the handler.** The handler is
registered as a plain WP REST `callback`, so WP core's rules apply and there is
no automatic `{success,data}` envelope:

| Handler returns | Wire result |
|---|---|
| `WP_REST_Response` | passed through as-is — **the explicit choice** |
| `array` | serialized as-is by WP core, status 200. No envelope |
| `WP_Error` | WP-native error JSON — **the message reaches the wire**; log the detail, return a generic message |
| an `NTDST_Response` object | **not handled** — WP serializes the object's public state. There is no `toRestResponse()`; use the static builders below |

To emit the `{success,data}` envelope the `ntdstAPI` JS client reads, return
`NTDST_Response::apiSuccessResponse($data)` / `::apiErrorResponse($msg, $code,
$status)`. Both return a real `WP_REST_Response` carrying the envelope and the
HTTP status.

### Rate limiting

`rate_limit` / `rate_window` delegate to `NTDST_RateLimiter`. The bucket is
(namespace + route + verbs + user-or-IP), so GET polling cannot drain a POST
route's budget. Only the handler whose verb **matched** the request spends a
unit — WP invokes every sibling handler's permission callback to build the
`Allow` header.

Two things to know before relying on it:

- It is only sound when `ntdst/trusted_proxies` matches the deployment **and**
  the proxy overwrites `X-Forwarded-For`. Otherwise a caller picks their bucket.
- **Known gap (F4, open):** a CORS preflight is never charged. `OPTIONS` never
  matches a route's registered verb list, so preflights cost zero budget while
  still running the permission callback. Measured: 40 consecutive preflights
  left the bucket unset, and 5 preflights carrying a 1.1 MB body returned 200
  each for free. Do **not** "fix" this locally by requiring a content type on
  `OPTIONS` — that refuses every preflight with a 415 and breaks CORS entirely.

### The WP-core quirk it absorbs for you

`rest_send_allow_header()` **double-invokes `permission_callback`** on every
request, to compute the `Allow` header. `NTDST_Rest` memoizes each permission
result per request in a **per-wrapper `WeakMap`**, so a side-effectful
permission (a rate-limit counter) runs once, not twice. Per-wrapper, not
per-instance: a shared map would leak one route's verdict to another route hit
by the same request. Unmemoized, every configured limit halves on the wire.

## CORS — the `cors` route option (4.1.0)

WP core's default is actively wrong: `rest_send_cors_headers()` (priority 10)
**reflects any `Origin`** and sets `Access-Control-Allow-Credentials: true` —
the reflection-plus-credentials anti-pattern, so any origin can read
authenticated responses. It also never sends `Access-Control-Allow-Headers`, so
a cross-origin JSON POST fails its preflight out of the box.

**Never hand-roll `Access-Control-*` headers.** Declare the policy:

```php
ntdst_rest('my/v1')->post('/thing', $handler, [
    'permission' => $permission,
    'cors'       => ['https://app.example.com'],   // exact origins
]);

// full form
'cors' => [
    'origins'     => ['https://app.example.com'],  // or fn(string $o): bool
    'headers'     => ['Content-Type', 'X-Tenant'], // default: Content-Type, Authorization, X-WP-Nonce
    'credentials' => true,                         // default FALSE
    'max_age'     => 600,
],
```

What it guarantees, so you do not re-derive it:

- byte-exact match on the full `scheme://host[:port]` — never a substring,
  never case-folded;
- `Origin: null` (a `file://` page, a sandboxed iframe) is **never** allowed,
  even if a policy lists it;
- credentials are OFF unless asked, and only ever granted beside an exact match;
- `Vary: Origin` is sent — without it a shared cache serves one origin the
  response computed for another;
- on a NON-match core's grant is actively **removed**, which is the whole point;
- a policy naming `'*'` **refuses the route**, the same as a missing
  `permission`. It is a misconfiguration, not a shorthand.

**Opt-in.** A route declaring no `cors` keeps WordPress's default — meaning it
is exactly as exposed as any other WP REST route. Core does not make that worse
and does not fix it unless asked.

Two traps the option already absorbs, both bought with real incidents — listed
because a consumer scoping its OWN filters still has to avoid them:

1. **A route-scope check must be case-INSENSITIVE.** WP matches routes with
   `preg_match('@^…$@i')`. A consumer scoped two filters with `str_starts_with()`
   on the raw route, so `/todai/v1/SUBMISSIONS` reached the handler with every
   guard declining to run — including the CORS correction, which restored WP
   core's reflect-any-origin-with-credentials default.
2. **A non-2xx preflight is as broken as a missing `Allow-Origin`.** A
   content-type gate that does not exempt `OPTIONS` refuses every preflight
   with a 415 while emitting perfect CORS headers. Testing the CORS function in
   isolation cannot see a status code; only driving the route catches it.

## Misconfiguration refuses; requests never throw

Bad **configuration** (a missing `permission`, an unknown option, a
non-callable handler) is a programmer error caught at registration — the route
never goes live, loudly. A bad or malicious **request** is a normal `WP_Error`
response, never an exception.

## When NOT to use this

- Same-origin in-page AJAX → `NTDST_Actions` (`api_data`), not this.
- A front-end HTML page/route → `NTDST_Pages` template hooks, not this.
- File bytes → `add_filter('ntdst/api_download/{action}', …)` + `ntdst_download()`.
