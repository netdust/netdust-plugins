---
name: wp-security
description: Use when WordPress code touches user input ($_GET/$_POST/$_REQUEST/$_COOKIE/$_SERVER), AJAX handlers, REST endpoints, form processors, shortcodes, admin pages, settings pages, custom database queries, or any echo/print of dynamic content from the database or user-controlled sources. Triggers on PHP file edits in plugins, themes, or mu-plugins. Activates on keywords nonce, sanitize, escape, capability, current_user_can, wp_verify_nonce, check_admin_referer, $wpdb, shortcode, register_rest_route, permission_callback, wp_ajax_, add_settings_field. Symptoms include writing PHP that handles forms, building admin UI, exposing REST endpoints, echoing post meta or ACF fields, querying the database with user-provided values. Do not skip when the page is admin-only, when the change is small, when in a hurry, or when the value is "just from the database".
---

# WordPress Security

**Violating the letter of these rules is violating the spirit of these rules.**

The WordPress security model has four pillars. Every data flow touches at least one. Skip any and you have a vulnerability — not theoretically, in production, with public exploits.

## The four pillars

1. **Validate** — Is this data the right shape? (length, type, format, allowed values)
2. **Sanitize** — Strip dangerous content on input **before storage**. Context: storage. [SEC-06, SEC-10]
3. **Escape** — Encode for safe rendering on output **at the moment of use**. Context: HTML body / attribute / URL / inline JS / CSS.
4. **Authorize** — Verify the user is allowed (`current_user_can`) **and** that the request is intentional (`wp_verify_nonce` / `check_admin_referer` / `check_ajax_referer`). [SEC-08, SEC-09]

Sanitize and escape are not interchangeable. Sanitize answers "safe to store?". Escape answers "safe to render *here*?". A title sanitized into the database still needs `esc_html()` when echoed into HTML body, `esc_attr()` when echoed into an attribute, `esc_url()` when echoed into `href`, `wp_kses_post()` when limited HTML is allowed.

## WordPress fundamentals — upstream

The generic layer is the official `WordPress/agent-skills` set, installed at a pinned commit by
`bin/wp-upstream-skills.sh` into `~/.claude/skills/<name>/`; this skill does not restate it.

- `wp-plugin-development` — `### 4) Security baseline (always)` + `references/security.md`
  (sanitize on input, `wp_unslash()` and explicit keys, escape on output, `$wpdb->prepare()`,
  nonces are CSRF not authorization); `### 3) Settings and admin UI` (`sanitize_callback`).
- `wp-rest-api` — `### 2) Register routes safely` (`permission_callback` on every route),
  `### 3) Validate/sanitize request args`, `### 5) Authentication and authorization` +
  `references/authentication.md` (cookie auth needs the `wp_rest` nonce as `X-WP-Nonce`).
- The per-context function map (`esc_*` by context, `sanitize_*` by type): the WordPress handbook's
  Data Validation and Securing Output pages, linked under See also.

## NTDST projects (ntdst-core 5.x)

On a project running ntdst-core 5.x, the four pillars above are unchanged — the door they are applied at is not.

- **Routes register through `ntdst_rest()` only.** The gate is `permission` — a capability string, `->public()` (the one door to anonymous), or a callable. `permission` absent is the internal default (`is_user_logged_in`) — a READ that names nothing is logged-in-only, never open; a WRITE that names nothing does not register at all (structural enforcement, not a review catch). A hand-written `permission_callback => '__return_true'` is the canonical `__return_true` bug reached by bypassing `ntdst_rest()` with a raw `register_rest_route()`. See `ntdst-framework/SKILL.md`.
- **The nonce is WordPress's, not core's.** ntdst-core mints no `wp_rest` nonce and runs no origin check of its own, so the `X-WP-Nonce` rule (`wp-rest-api`) is what a cookie-authenticated caller satisfies — `wp.apiFetch` on the client, nothing hand-rolled.
- **Cross-origin (CORS)**: WP core's default reflects any `Origin` **and** sets `Access-Control-Allow-Credentials: true` (the reflection+credentials anti-pattern), so any origin can read authenticated responses. The answer is `cors()` on `ntdst_rest()` — origins are ADDED to WordPress's own `allowed_http_origins`, scoped to REST requests only (`admin-ajax.php` and other cookie-auth surfaces keep WordPress's defaults), and `'*'` is refused outright as an allow-list entry. **Never hand-roll `Access-Control-*` headers or a `rest_pre_serve_request` hook.** Note it is OPT-IN: a route declaring no `cors` is exactly as exposed as any other WP REST route. See `ntdst-framework/SKILL.md`.
- **`show_in_rest` on a Data-API field**: `'show_in_rest' => true` makes the field readable by anyone on `/wp/v2/<type>` — WordPress's own REST controller, no separate gate. A mis-declaration is a disclosure, not a bug a reviewer catches later.

## One excellent example

A custom AJAX handler that updates a post meta from a form. On ntdst-core 5.x this handler is drift — the same four pillars apply over an `ntdst_rest()` route instead:

```php
add_action( 'wp_ajax_netdust_update_meta', 'netdust_update_meta_handler' );

function netdust_update_meta_handler() {
    // 4. Authorize: nonce + capability
    check_ajax_referer( 'netdust_update_meta', '_nonce' );

    if ( ! current_user_can( 'edit_posts' ) ) {
        wp_send_json_error( [ 'msg' => 'forbidden' ], 403 );
    }

    // 1+2. Validate + sanitize
    $post_id = isset( $_POST['post_id'] ) ? absint( $_POST['post_id'] ) : 0;
    $value   = isset( $_POST['value'] )
        ? sanitize_text_field( wp_unslash( $_POST['value'] ) )
        : '';

    // Per-object capability (cap check above is coarse)
    if ( ! $post_id || ! current_user_can( 'edit_post', $post_id ) ) {
        wp_send_json_error( [ 'msg' => 'invalid' ], 400 );
    }

    update_post_meta( $post_id, '_netdust_status', $value );

    // 3. Escape on output (even in JSON — the consumer may render it as HTML)
    wp_send_json_success( [ 'value' => esc_html( $value ) ] );
}
```

All four pillars present. Notice: `wp_unslash()` before `sanitize_text_field()`, capability check **before and after** post resolution (coarse then per-object), and `esc_html()` on the response even though it ships as JSON.

## Rationalization table

| Excuse | Reality |
|---|---|
| "Admin-only page, no need to escape" | Admins get phished. Stored XSS in admin → full site compromise. Escape anyway. |
| "I sanitized on input, why escape on output?" | Sanitize is "safe to store". Escape is "safe to render *here*". Different output contexts need different escapers. |
| "It's just `$post->post_title` from the DB, it's clean" | Anyone with `edit_posts` can put HTML in a title. Other plugins write to it via filters. Escape. |
| "I'll add the nonce later" | "Later" = "the next commit, in two weeks, after a CSRF report". Add it now. |
| "Frontend-only public form, no nonce needed" | CSRF works on logged-out users too. Public state-changing forms need a nonce or equivalent. |
| "It's just an int — `(int) $_POST['id']` is fine" | `(int)` strips the trailing junk but accepts negatives. Use `absint()` for IDs. |
| "REST endpoint, WordPress handles auth" | Only if `permission_callback` is set. `__return_true` is the bug. On `ntdst_rest()` the option is `permission`: a route OPTION named `permission_callback` is one core does not know, and the route is refused outright (`ntdst-framework/references/traps.md`). [SEC-17] |
| "Trusted client JS sends this value" | The browser is not trusted. Anyone can curl your endpoint with any payload. |
| "It's a quick fix, ship it" | Quick fixes are how every WP breach happens. 30 seconds for a nonce is not the bottleneck. |
| "The user is logged in, so they're trusted" | Authentication ≠ authorization. Logged-in subscribers can still hit admin endpoints. |
| "Following the spirit not the letter" | The letter is the spirit. If the rule says nonce, you need a nonce. |

## Loophole closures

- **"Escape the whole template at the bottom"** → No. Escape at the point of output, in the right context. `esc_html` for body text, `esc_attr` for attributes, `esc_url` for hrefs — they are not interchangeable. [SEC-25, SEC-26]
- **"Sanitize once and forget"** → No. Sanitize on input, escape on output. Always both.
- **"Run input through `esc_*` before storage"** → No. `esc_*` functions are for output. Storing escaped values means they get double-escaped when re-rendered through a properly-escaping template later.
- **"Use `WP_REST_Request::get_param()`, it's safe"** → No. It returns raw values. Sanitize per-field.
- **"`wp_kses_post()` everywhere to keep formatting"** → Careful. It allows `<a href>`, which is XSS-able via `javascript:` URLs. Always `esc_url()` the href separately.
- **"ACF sanitizes its own fields"** → Partially. ACF sanitizes on save based on field type, but the value coming out of `get_field()` is **not** escaped for any specific output context. Escape on output yourself.
- **"`is_user_logged_in()` / `is_admin()` is enough for an admin action"** → No. Logged-in is authentication, `is_admin()` is a context flag (an admin screen is loading); authorization is `current_user_can()` with the specific capability. [SEC-09]
- **"`esc_url()` on the way into the database"** → No. Storage → `esc_url_raw()`; output → `esc_url()`.
- **"`add_query_arg()` returns a safe URL"** → No. It does not escape. Pipe it through `esc_url()`.
- **"`__()` is fine straight into HTML"** → No. Translations are file-writable; `esc_html__()` / `esc_attr__()` when the string lands in HTML.

## When in doubt — three questions

1. **What is the output context right now?** (HTML body / attribute / URL / JS / CSS) → determines the escaper.
2. **What capability is needed to do this action?** → determines the `current_user_can()` argument.
3. **Is this a state change?** → if yes, nonce required.

## See also

- `wp-plugin-development`, `wp-rest-api` (upstream, cited above); `references/wp-review-checklists.md` (vendored, `SEC-nn` / `MIG-nn`).
- `skills/wp-database` for `$wpdb->prepare()` patterns.
- WordPress codex: [Data Validation](https://developer.wordpress.org/apis/security/data-validation/), [Securing Output](https://developer.wordpress.org/apis/security/escaping/), [Nonces](https://developer.wordpress.org/apis/security/nonces/).
- `red-tests.md` in this skill folder: pressure scenarios for validating that this skill actually changes behavior.
