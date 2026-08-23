# Golden Path — Form / data-flow feature (a write route on `ntdst_rest()`)

> **Rewritten for ntdst-core 5.0.0** — anchored on `api/Rest.php` (`NTDST_Rest`), `api/Data.php`. Re-verify with the drift-reviewer grep set when the source moves; `/skill-audit` flags this after 90 days.

**Read this before planning any form, write flow, or REST write endpoint.** 5.0.0 removed the old AJAX command dispatcher outright, with no shim — see `ntdst-framework/SKILL.md`'s `## Retired` section for what it was. **There is now ONE HTTP surface: `ntdst_rest()`.** A form posts straight to a REST route; `wp.apiFetch` is the one frontend driver.

The write/posture refusal is `ntdst-framework/SKILL.md` `## Rest is the one surface`; this doc shows the two shapes it produces — the capability write and the anonymous write.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `Modules/{Module}/{Feature}Handler.php` | Thin handler | Shapes the `WP_REST_Request`, delegates to the repository, returns `WP_REST_Response`\|`WP_Error` |
| `Modules/{Module}/{Type}Repository.php` | Repository | The only place that calls `ntdst_data()->get('{type}')->create()` |
| the owning service's `init()` | Route registration | `ntdst_rest($ns)->post(...)` — `NTDST_Rest`, the ONE HTTP surface |
| `assets/js/{feature}.js` | Frontend driver | `wp.apiFetch({ path, method: 'POST', data })` |

Governing reference: **`ntdst-framework/SKILL.md`** (`## Rest is the one surface`, `## Retired`), **`ntdst-framework/references/traps.md`** (`## Rest`), **`netdust-wp:wp-security`** (Validate/Sanitize/Escape/Authorize). This doc does not restate those rules — it shows where each one lands on a write route.

The code below is one worked example (`Acme\Modules\Contact`, an anonymous contact form) so every block is real, lintable PHP — rename the namespace, class and route to your own project's.

---

## The sequence — capability write and anonymous write, side by side

```
Browser                                        ntdst-core (NTDST_Rest)                Your code
────────                                       ────────────────────────                ─────────
wp.apiFetch({ path, method: 'POST', data })
   │  sets X-WP-Nonce itself (the wp_rest nonce — CSRF only, INV-4;
   │  refreshed automatically on expiry — nothing for you to fetch)
   ▼
POST /{project}/v1/{route}
   │
   ▼
permission — resolved from what the route DECLARED, never from a value
that "reads like" open:
   • a capability string   → current_user_can($cap)     [internal write]
   • your own callable     → run exactly as you wrote it [the ONE door to an anonymous write]
   │  (+ rate_limit / rate_window, charged from inside this same check — INV-7)
   ▼
                                                                          {Feature}Handler::handle($request)
                                                                             │
                                                                             ▼
                                                                          {Type}Repository::create($data)
                                                                             │
                                                                             ▼
                                                                          ntdst_data()->get('{type}')->create($data)
   ◀───────────────────────────  WP_REST_Response | WP_Error  ──────────────┘
```

---

## The handler — thin, no envelope

A handler takes a `WP_REST_Request`, does its own Validate/Sanitize (`netdust-wp:wp-security`), delegates to the repository, and returns **`WP_REST_Response` or `WP_Error`** — never an array, never `wp_send_json_*`. `NTDST_Rest` and WordPress build the response body; a client that expects `response.data.thing` reads `response.thing`. Pass failure status through `WP_Error`'s own `['status' => …]` args (`new WP_Error('code', 'message', ['status' => 422])`) — never `return false` and never swallow a repository's `WP_Error`.

```php
<?php
declare(strict_types=1);

namespace Acme\Modules\Contact;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Thin handler: shapes the request, delegates, returns. No output, no
 * business logic beyond turning request params into the repository's
 * vocabulary.
 */
final class ContactHandler
{
    public function __construct(private readonly MessageRepository $messages) {}

    /** Internal write — reached only by a user holding 'edit_posts'. */
    public function store(WP_REST_Request $request): WP_REST_Response|WP_Error
    {
        $message = $this->messages->create([
            'title'   => sanitize_text_field((string) $request->get_param('subject')),
            'content' => wp_kses_post((string) $request->get_param('body')),
            'email'   => sanitize_email((string) $request->get_param('email')),
        ]);

        if (is_wp_error($message)) {
            return $message; // never swallowed — the repository's WP_Error propagates as-is
        }

        return new WP_REST_Response(['id' => $message->ID], 201);
    }
}
```

**`submit()`, the anonymous variant, is `store()` with ONE line changed** — the status. Everything else (the same sanitisers, the same `is_wp_error` propagation, the same 201) is identical, so only the delta is worth showing:

```php
$message = $this->messages->create([
    // …the three fields store() sends, unchanged…
    'post_status' => 'pending',   // THE DELTA
]);
```

`create()` defaults `post_status` to `'publish'` (`api/Data.php:639`), so without that line an unauthenticated stranger's submission is live on the site the moment it is accepted. A row written by a caller nobody authenticated waits for a human.

Every key the handler sends must be DECLARED on the model. An unregistered key is dropped from `create()` with an `Unregistered key(s) passed to create` line in `logs/data-*.log` and nothing else (`api/Data.php:502-520`) — so `email` is declared here, not assumed:

```php
<?php
ntdst_data()->register('message', [
    'label'       => 'Berichten',
    'meta_prefix' => '_acme_',
    'fields'      => ['email' => ['type' => 'email', 'label' => 'E-mail']],
]);
```

```php
<?php
declare(strict_types=1);

namespace Acme\Modules\Contact;

use WP_Error;
use WP_Post;

/**
 * The only place `ntdst_data()->get('message')` is called for this type —
 * a handler, a template or a service reaching for it directly is drift.
 * CRUD forwarding INSIDE a repository is the mediator boundary, not a
 * pass-through: it fixes the model name and the status default.
 */
final class MessageRepository
{
    public function create(array $data): WP_Post|WP_Error
    {
        return ntdst_data()->get('message')->create($data);
    }
}
```

---

## Route registration — the owning service's `init()`

```php
<?php
declare(strict_types=1);

use Acme\Modules\Contact\ContactHandler;

$handler = ntdst_get(ContactHandler::class);

ntdst_rest('{project}/v1')
    // INTERNAL WRITE — a real WP capability names who may act. This is
    // the default shape: nothing special to declare beyond the capability.
    ->post('/messages', [$handler, 'store'], [
        'permission' => 'edit_posts',
    ])
    // ANONYMOUS WRITE — see "The anonymous-form variant" below.
    ->post('/contact', [$handler, 'submit'], [
        'permission'  => static function (WP_REST_Request $request): bool {
            // Honeypot: a real visitor never FILLS this hidden field, but the
            // form always SENDS it. `?? ''` is load-bearing — get_param()
            // returns null for a field that is absent, and a bare `=== ''`
            // would then deny every submission that omits it.
            return ($request->get_param('website') ?? '') === '';
        },
        'rate_limit'  => 5,
        'rate_window' => 60,
    ]);
```

`'permission' => 'edit_posts'` resolves to `current_user_can('edit_posts')` — a STRING is always asked as a capability, never as a function name (no `is_callable()` check runs first: WordPress itself ships capability slugs that are also function names, and asking `is_callable()` first would execute one as a gate). There is no "logged in, no specific capability" shorthand for a write — see the variant below for that exact case.

---

## The anonymous-form variant

An anonymous write has exactly one door: **hand `permission` your own callable.** A callable is used exactly as given — never wrapped, never asked `is_callable()` twice — so it is free to run its own gate (a honeypot field, a Turnstile/hCaptcha token, a signed one-time link) and return `bool`. `rate_limit`/`rate_window` are charged from inside that same permission check (`api/Rest.php`, `guard()` — auth before the bucket, so a caller who could never pass the gate never makes the route write a rate-limit row).

**A honeypot is spam deterrence, not authorization.** It is a bot filter sitting in the permission slot; anyone who reads your form's HTML can satisfy it. Everything downstream — the `'pending'` status, the sanitisers, the rate limit — must hold on the assumption that an attacker passed the gate on purpose.

This is also the shape for "any logged-in user, no specific capability" — WordPress has no capability that means only "is logged in". The callable is simply `static fn(WP_REST_Request $r): bool => is_user_logged_in();` instead of a honeypot check.

---

## The frontend driver — `wp.apiFetch`

Never raw `fetch()` against a REST route (it re-derives the nonce header and the credentials mode by hand, and both already ship with `wp.apiFetch`). Enqueue with `wp-api-fetch` as a script dependency; `wp.apiFetch` reads WordPress's own localized nonce and refreshes it on a 403 — there is nothing to fetch first.

The honeypot is a contract between three places — the markup that renders the field, the payload that always sends it, and the permission callable that reads it. Miss any one and every real submission is refused.

```html
<!-- the markup: present, hidden from humans, never `type="hidden"`
     (a bot skips those) and never `display:none` alone if your CSS is
     inlined by a plugin — pair it with an off-screen label. -->
<input type="text" name="website" value="" tabindex="-1" autocomplete="off"
       class="acme-hp" aria-hidden="true">
```

```js
// assets/js/contact-form.js
async function submitContactForm(fields) {
    return await wp.apiFetch({
        path: '/{project}/v1/contact',
        method: 'POST',
        // `website: ''` is ALWAYS sent. The permission callable reads it, and
        // an absent param arrives as null, which is not ''.
        data: { ...fields, website: '' },
    });
}
```

```php
wp_enqueue_script(
    '{project}-contact-form',
    plugins_url('assets/js/contact-form.js', __FILE__),
    ['wp-api-fetch'],                 // dependency — no manual nonce plumbing
    (string) filemtime($jsFile),
    true,
);
```

---

## Where Validate/Sanitize/Escape/Authorize land

`netdust-wp:wp-security`'s four pillars, mapped onto this slice:

- **Authorize** — the route's `permission` (capability or your own callable), checked by `NTDST_Rest` before the handler ever runs. CSRF is separate and automatic: `wp.apiFetch` sends the nonce, WordPress verifies it (INV-4) — a nonce proves the request came from this browser session, it is never an access-control decision.
- **Validate + Sanitize** — the handler's job, per parameter (`sanitize_text_field`, `sanitize_email`, `wp_kses_post`, …), before the value reaches the repository. The repository's own model schema sanitizes again on write (defence in depth), but the handler must not hand it raw request params and assume that catches everything — see `wp-security`'s function table for the sanitizer per type.
- **Escape** — `n/a` here: the response is `WP_REST_Response` JSON, never HTML, so there is no render-time sink. State that explicitly in the plan (`escape: n/a — JSON response`) rather than silently omitting the pillar. A route that also renders HTML (a settings page save) escapes at the render boundary — see `golden-paths/admin-settings-page.md`.

---

## How to adapt — what changes per project, what never does

**Changes per project:**
1. **Namespace + route** — `{project}/v1`, `/messages`, `/contact`.
2. **Permission** — a capability for an internal write; your own callable for an anonymous one.
3. **Sanitisers** — one per field, matching its type (see the handler above).
4. **Rate limit** — only on a route that needs one; it is a route option, nothing is metered by default.
5. **Delegation target** — which repository/model the handler writes through.

**Never changes:**
- Register through `ntdst_rest()` — never a raw `register_rest_route()` and never the retired AJAX dispatcher.
- Handler returns `WP_REST_Response`\|`WP_Error`; never an array envelope, never `wp_send_json_*`.
- Never swallow a `WP_Error` — propagate it.
- `ntdst_data()->get('{type}')` appears only inside the repository.
- Frontend uses `wp.apiFetch`, never raw `fetch()`.

---

## Cross-references

- Governing references: `ntdst-framework/SKILL.md` (`## Rest is the one surface`), `ntdst-framework/references/traps.md` (`## Rest`), `netdust-wp:wp-security`.
- For cross-origin, declare `cors()` once at the namespace (`ntdst_rest($ns)->cors([...])`) — never a hand-rolled `Access-Control-*` filter; it is REST-scoped and additive onto WordPress's own `allowed_http_origins` (INV-5).
- For a CPT write that also needs an admin screen around it, see `golden-paths/content-type-feature.md`.
- A settings-page save is itself a write route with the same shape — see `golden-paths/admin-settings-page.md`.
