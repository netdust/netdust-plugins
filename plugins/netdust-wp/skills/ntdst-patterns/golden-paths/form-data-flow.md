# Golden Path — Form / data-flow feature (AJAX with all four security pillars)

> **Verified against source: 2026-06-09** — Stride `Handlers/ProfileHandler.php` + `ntdst-core/api/Endpoints.php`. Re-verify with the drift-reviewer grep set (check #11) when the source moves or drifts; `/skill-audit` flags this after 90 days.

**Read this before planning any form, AJAX, or write-flow.** It shows where each of the four security pillars fires in the NTDST AJAX path. Build to it; name any deviation in the plan.

**Extracted from** Stride's `ProfileHandler` (`Stride\Handlers\ProfileHandler`) + the framework edge `ntdst-core/api/Endpoints.php`. Verified drift-clean. Genericised `Stride` → `{Project}`.

The single most important thing this golden path teaches: **the nonce and login pillars fire at the framework edge, not in your handler.** A handler that re-checks the nonce is redundant; a handler that *omits* capability/sanitize/escape is a vulnerability. Know which pillar is yours.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `Handlers/{Feature}Handler.php` | Thin handler | Registers `ntdst/api_data/{action}` filter; validates input, delegates, returns array\|WP_Error |
| `Modules/{Module}/{Feature}Service.php` | Service | Owns the business logic the handler delegates to |
| `themes/{theme}/src/main.js` (`ntdstAPI`) | Frontend driver | `ntdstAPI.call('{action}', params)` — fetches nonce, posts to the REST edge |
| `ntdst-core/api/Endpoints.php` | **Framework edge (do not copy — reference)** | Verifies nonce + login + origin + rate-limit, then dispatches the `ntdst/api_data/{action}` filter |

Governing reference: **`netdust-wp:wp-security`** (the four pillars + exact sanitize/escape/authorize functions), **`ntdst-architecture/references/api-endpoints.md`** (the `ntdst/api_data` contract). This doc does not restate the pillar tables — it shows where each pillar lands.

---

## Where the four pillars fire

```
 Browser                          Framework edge                      Your handler
 ───────                          (Endpoints.php)                     ({Feature}Handler)
 ntdstAPI.call(action, params)
   │  GET /ntdst/v1/get_nonce  ─────▶ issues per-action nonce
   │  POST /ntdst/v1/action    ─────▶ ① wp_verify_nonce(nonce, action)   [PILLAR 1: NONCE]
   │     {action, nonce, …}          ② is_user_logged_in() unless        [auth gate]
   │                                     action ∈ public_actions
   │                                  ③ verifyOrigin() (CSRF)
   │                                  ④ rate-limit per action
   │                                  ⑤ apply_filters("ntdst/api_data/$action", [], $params)
   │                                                              │
   │                                                              ▼
   │                                          ③ current_user_can(...) / ownership  [PILLAR 2: CAPABILITY]
   │                                          ④ sanitize_*() every $param          [PILLAR 3: SANITIZE]
   │                                          ⑤ delegate to service, return array|WP_Error
   ◀─────────────────────────── JSON ◀──────────────────────────────┘
        x-text binding (no raw HTML)                                  [PILLAR 4: ESCAPE — at the render]
```

**Pillars 1 (nonce) + the login gate are the framework's** — `Endpoints.php` verifies them *before* your filter runs, so your handler never sees an unauthenticated/forged request. **Pillars 2, 3, 4 are yours.**

---

## The handler — `{Feature}Handler.php`

Thin handler pattern: no constructor DI of services (resolve via `ntdst_get()` when needed), registers its own `ntdst/api_data/*` filters in `init()`, returns `array|WP_Error` (never echoes, never `wp_send_json_*` — the framework edge serialises the return).

```php
<?php
declare(strict_types=1);

namespace {Project}\Handlers;

use WP_Error;

/**
 * Thin handler — validates input, delegates, returns. No business logic, no output.
 */
final class {Feature}Handler
{
    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        // FRAMEWORK AJAX PATH (drift cat 3) — never add_action('wp_ajax_...').
        // The framework verifies nonce+login BEFORE this filter is applied.
        add_filter('ntdst/api_data/{project}_update_profile', [$this, 'handleUpdateProfile'], 10, 2);
    }

    /**
     * @param mixed $data    Existing filter data (unused — we own the response).
     * @param array<string,mixed> $params  Request params (already past nonce+login at the edge).
     * @return array<string,mixed>|WP_Error
     */
    public function handleUpdateProfile(mixed $data, array $params): array|WP_Error
    {
        // PILLAR 2 — CAPABILITY / OWNERSHIP. Here the resource is the user's own
        // profile, so "logged in" + "acting on self" IS the authorization.
        // For a CPT write you'd use current_user_can('edit_post', $id) instead.
        $userId = get_current_user_id();
        if (!$userId) {
            return new WP_Error('not_logged_in', __('Je moet ingelogd zijn.', '{project}'));
        }

        // PILLAR 3 — SANITIZE ON INPUT. Every param is sanitised by type before use.
        $formType = sanitize_text_field($params['form_type'] ?? 'personal');

        return match ($formType) {
            'billing'       => $this->updateBilling($userId, $params),
            'notifications' => $this->updateNotifications($userId, $params),
            default         => $this->updatePersonal($userId, $params),
        };
    }

    /**
     * Partial update: only posted keys are written; missing keys untouched.
     */
    private function updatePersonal(int $userId, array $params): array|WP_Error
    {
        $userUpdate = ['ID' => $userId];
        if (isset($params['first_name'])) {
            $userUpdate['first_name'] = sanitize_text_field($params['first_name']);   // PILLAR 3
        }
        if (isset($params['last_name'])) {
            $userUpdate['last_name'] = sanitize_text_field($params['last_name']);      // PILLAR 3
        }

        if (count($userUpdate) > 1) {
            $result = wp_update_user($userUpdate);
            if (is_wp_error($result)) {     // never swallow WP_Error (drift cat 5) — propagate it
                return $result;
            }
        }

        // Map of input key → [meta key, sanitiser]. The sanitiser is chosen per field type.
        $metaFields = ['phone' => 'phone', 'organisation' => 'organisation'];
        foreach ($metaFields as $inputKey => $metaKey) {
            if (isset($params[$inputKey])) {
                update_user_meta($userId, $metaKey, sanitize_text_field($params[$inputKey]));  // PILLAR 3
            }
        }

        ntdst_log('profile')->info('Personal profile updated', ['user_id' => $userId]);

        return ['success' => true, 'message' => __('Gegevens bijgewerkt.', '{project}')];
    }

    private function updateBilling(int $userId, array $params): array|WP_Error
    {
        // PILLAR 3 — sanitiser per field. Note sanitize_email for the email field.
        $billingMap = [
            'company'       => ['billing_company',   'sanitize_text_field'],
            'vat_number'    => ['billing_vat',       'sanitize_text_field'],
            'address'       => ['billing_address_1', 'sanitize_text_field'],
            'invoice_email' => ['invoice_email',     'sanitize_email'],
        ];
        foreach ($billingMap as $inputKey => [$metaKey, $sanitiser]) {
            if (isset($params[$inputKey])) {
                update_user_meta($userId, $metaKey, $sanitiser($params[$inputKey]));
            }
        }
        return ['success' => true, 'message' => __('Facturatiegegevens bijgewerkt.', '{project}')];
    }
}
```

> **`update_user_meta` here is NOT a repository bypass.** Users are not a CPT and have no `*Repository` — WP's user-meta API is the correct primitive. The cat-1/cat-8 repository rule applies to CPT data. For a CPT write, the handler would delegate to a service that goes through `{Type}Repository`. See the content-type golden path.

### PILLAR 4 — ESCAPE ON OUTPUT, and why it's `n/a` here

This handler returns a **JSON array**, not HTML. The frontend binds it with Alpine `x-text` (which sets `textContent`, never `innerHTML`), so there is no HTML sink to escape. **State this explicitly in the plan — `escape: n/a (JSON response, x-text binding)` — never silently omit the pillar.** If your handler returned a string that lands in HTML, you would `esc_html()` it at the render boundary (see the admin-settings golden path, which *does* echo and *does* escape).

---

## The framework edge — `Endpoints.php` (reference only, do not copy)

You don't write this — `ntdst-core` owns it. Know what it guarantees so you don't duplicate or assume:

```php
// ntdst-core/api/Endpoints.php — the contract your handler sits behind
'permission_callback' => [$this, 'check_action_permission'],   // every action route
// …
if (!wp_verify_nonce($nonce, $action)) {        // PILLAR 1 — fires here, not in your handler
    return new WP_Error('invalid_nonce', …);
}
// public_actions is an opt-in allow-list; everything else requires login:
$public = apply_filters('ntdst/api/public_actions', $this->public_actions);
if (!in_array($action, $public, true) && !is_user_logged_in()) {
    return new WP_Error('not_logged_in', …);
}
// origin/referer CSRF check + per-action rate limit, then:
return apply_filters("ntdst/api_data/{$action}", [], $params);   // → your handler
```

**Consequence for the plan:** a handler on a non-public action is reached only by a logged-in user with a valid nonce. So the plan's security line for such a flow reads: *nonce + login = framework edge; capability + sanitize = handler; escape = n/a or at render.* If the action must be public (`nopriv`), it has to be added to the `ntdst/api/public_actions` allow-list explicitly — name that in the plan, because it removes the login gate.

---

## The frontend driver — `ntdstAPI`

Never raw `fetch()` to a WP endpoint (drift / `anti-patterns.md` → *Manual fetch()*). `ntdstAPI` fetches a fresh per-action nonce, posts with `credentials: 'same-origin'`, and retries on nonce expiry.

```js
// in an Alpine component
async save() {
    const res = await ntdstAPI.call('{project}_update_profile', {
        form_type: 'personal',
        first_name: this.firstName,
        last_name: this.lastName,
    });
    this.message = res.message;   // bound via x-text — no innerHTML, so no XSS sink
}
```

---

## How to adapt — what changes per project, what never does

**Changes per project:**
1. **Action name** — `{project}_update_profile` (the filter tag + the `ntdstAPI.call` string must match).
2. **Capability check** — own-resource (`get_current_user_id`) vs `current_user_can('edit_post', $id)` vs a custom cap. Pick per resource.
3. **Sanitisers** — one per field, chosen by type (`sanitize_text_field` / `sanitize_email` / `absint` / `wp_kses_post` / `esc_url_raw`).
4. **Delegation target** — which service/repository the handler calls (or, for user-meta, the WP user API directly).
5. **Public vs authenticated** — if the action needs `nopriv`, add it to `ntdst/api/public_actions` and re-derive the auth pillar.
6. **Escape decision** — `n/a` (JSON + x-text) vs `esc_html` at a render boundary. Always stated, never omitted.

**Never changes:**
- Use the `ntdst/api_data/{action}` filter — never `add_action('wp_ajax_*')`.
- Nonce + login are the framework edge's job; don't re-implement, don't assume absent.
- Handler returns `array|WP_Error`; never echoes, never `wp_send_json_*`.
- Never swallow a `WP_Error` — propagate it (cat 5).
- Frontend uses `ntdstAPI.call()`, never raw `fetch()`.
- All four pillars are accounted for in the plan; a missing one is the bug pre-shipped.

---

## Cross-references

- Governing references: `netdust-wp:wp-security` (four pillars + functions), `ntdst-architecture/references/api-endpoints.md` (the `ntdst/api_data` contract), `references/response.md`.
- Anti-patterns this slice satisfies: `anti-patterns.md` → *Unsanitized Input*, *Missing Capability Checks*, *Unescaped Output*, *Manual fetch() in JavaScript*, *Returning false/null on Error*.
- Drift categories satisfied (per `ntdst-drift-reviewer`): **3** (no raw `wp_ajax_*`), **5** (no swallowed `WP_Error`). The four security pillars map to `wp-plan-requirements` Block 1.
- For a REST (not AJAX) flow with `permission_callback`, the shape is the same minus the nonce edge — Stride's `Modules/PartnerAPI/PartnerAPIController.php` is the worked REST example (`register_rest_route` + role/company scoping).
