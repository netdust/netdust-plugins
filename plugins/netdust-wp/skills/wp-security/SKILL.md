---
name: wp-security
description: Use when WordPress code touches user input ($_GET/$_POST/$_REQUEST/$_COOKIE/$_SERVER), AJAX handlers, REST endpoints, form processors, shortcodes, admin pages, settings pages, custom database queries, or any echo/print of dynamic content from the database or user-controlled sources. Triggers on PHP file edits in plugins, themes, or mu-plugins. Activates on keywords nonce, sanitize, escape, capability, current_user_can, wp_verify_nonce, check_admin_referer, $wpdb, shortcode, register_rest_route, permission_callback, wp_ajax_, add_settings_field. Symptoms include writing PHP that handles forms, building admin UI, exposing REST endpoints, echoing post meta or ACF fields, querying the database with user-provided values. Do not skip when the page is admin-only, when the change is small, when in a hurry, or when the value is "just from the database".
---

# WordPress Security

**Violating the letter of these rules is violating the spirit of these rules.**

The WordPress security model has four pillars. Every data flow touches at least one. Skip any and you have a vulnerability — not theoretically, in production, with public exploits.

## The four pillars

1. **Validate** — Is this data the right shape? (length, type, format, allowed values)
2. **Sanitize** — Strip dangerous content on input **before storage**. Context: storage.
3. **Escape** — Encode for safe rendering on output **at the moment of use**. Context: HTML body / attribute / URL / inline JS / CSS.
4. **Authorize** — Verify the user is allowed (`current_user_can`) **and** that the request is intentional (`wp_verify_nonce` / `check_admin_referer` / `check_ajax_referer`).

Sanitize and escape are not interchangeable. Sanitize answers "safe to store?". Escape answers "safe to render *here*?". A title sanitized into the database still needs `esc_html()` when echoed into HTML body, `esc_attr()` when echoed into an attribute, `esc_url()` when echoed into `href`, `wp_kses_post()` when limited HTML is allowed.

## Quick reference

### Sanitize on input (storage-bound)

| Input type | Function |
|---|---|
| Plain text | `sanitize_text_field()` |
| Textarea | `sanitize_textarea_field()` |
| Email | `sanitize_email()` |
| URL (storing) | `esc_url_raw()` |
| Filename | `sanitize_file_name()` |
| Slug/key | `sanitize_key()` |
| Integer ID | `absint()` |
| Limited HTML | `wp_kses_post()` or `wp_kses()` with allow-list |
| Array of values | Loop + sanitize per element |

Always `wp_unslash()` first on `$_POST`/`$_GET`/`$_REQUEST`/`$_COOKIE` — WP applies magic-quote-style slashes; without unslashing, apostrophes become `\'` in storage.

### Escape on output (rendering-bound)

| Context | Function |
|---|---|
| HTML body text | `esc_html()` / `esc_html_e()` |
| HTML attribute | `esc_attr()` / `esc_attr_e()` |
| URL in `href` / `src` | `esc_url()` |
| Inline JS value | `wp_json_encode()` |
| Translated string in HTML | `esc_html__()`, `esc_attr__()` |
| Trusted limited HTML | `wp_kses_post()` |
| Raw `<textarea>` content | `esc_textarea()` |

### Authorize

- **Capability**: `current_user_can( 'edit_posts' )`. Never use `is_admin()` for permission — it is a context flag, not an authorization check.
- **Nonce**: every state-changing action. `wp_create_nonce()` → `wp_verify_nonce()` or `check_admin_referer()`.
- **Legacy AJAX (`wp_ajax_*` / `wp_ajax_nopriv_*`)**: `check_ajax_referer()` is **required per handler**.
- **`ntdst_api` actions**: the router (`mu-plugins/ntdst-core/api/Endpoints.php`) verifies the nonce centrally before dispatching to your `add_filter('ntdst/api_data/{action}', ...)` handler, and validates request `Origin`/`Referer` for CSRF in `permission_callback`. **Handlers registered via `ntdst_api` therefore do NOT need their own `wp_verify_nonce()` / `check_ajax_referer()` call** — it's already done. Capability checks (`current_user_can()`) and per-object authorization are still on you.
- **REST**: `permission_callback` is **required** on every route. `__return_true` is the canonical security bug.

### Database

Any dynamic value into a query → `$wpdb->prepare()`. No exceptions. See `skills/wp-database` for details.

## One excellent example

A custom AJAX handler that updates a post meta from a form:

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
| "REST endpoint, WordPress handles auth" | Only if `permission_callback` is set. `__return_true` is the bug. |
| "Trusted client JS sends this value" | The browser is not trusted. Anyone can curl your endpoint with any payload. |
| "It's a quick fix, ship it" | Quick fixes are how every WP breach happens. 30 seconds for a nonce is not the bottleneck. |
| "The user is logged in, so they're trusted" | Authentication ≠ authorization. Logged-in subscribers can still hit admin endpoints. |
| "Following the spirit not the letter" | The letter is the spirit. If the rule says nonce, you need a nonce. |

## Loophole closures

- **"Escape the whole template at the bottom"** → No. Escape at the point of output, in the right context. `esc_html` for body text, `esc_attr` for attributes, `esc_url` for hrefs — they are not interchangeable.
- **"Sanitize once and forget"** → No. Sanitize on input, escape on output. Always both.
- **"Run input through `esc_*` before storage"** → No. `esc_*` functions are for output. Storing escaped values means they get double-escaped when re-rendered through a properly-escaping template later.
- **"Use `WP_REST_Request::get_param()`, it's safe"** → No. It returns raw values. Sanitize per-field.
- **"`wp_kses_post()` everywhere to keep formatting"** → Careful. It allows `<a href>`, which is XSS-able via `javascript:` URLs. Always `esc_url()` the href separately.
- **"ACF sanitizes its own fields"** → Partially. ACF sanitizes on save based on field type, but the value coming out of `get_field()` is **not** escaped for any specific output context. Escape on output yourself.
- **"`is_user_logged_in()` is enough for an admin action"** → No. Use `current_user_can()` with the specific capability for that action.

## Common mistakes

- `esc_url()` vs `esc_url_raw()` swap. **Storage → `esc_url_raw()`. Output → `esc_url()`.**
- Forgetting `wp_unslash()` before sanitize on `$_POST` / `$_GET` / `$_REQUEST` / `$_COOKIE`.
- Using `esc_html()` inside an HTML attribute. Use `esc_attr()`.
- Outputting `get_post_meta()` or `get_option()` raw. Both are user-writable in some flows; treat as untrusted.
- `add_query_arg()` does **not** escape. Pipe its return through `esc_url()`.
- ACF: `the_field()` outputs raw, no escaping. Use `echo esc_html( get_field( 'foo' ) )` (or the appropriate escaper for the context).
- Echoing translated strings without escaping. Use `esc_html__()` / `esc_attr__()`, not bare `__()`, when output goes into HTML.
- Missing capability check on `admin_post_*` actions — these are reachable by any logged-in user including subscribers.
- Settings API: forgetting the `sanitize_callback` argument on `register_setting()`.

## When in doubt — three questions

1. **What is the output context right now?** (HTML body / attribute / URL / JS / CSS) → determines the escaper.
2. **What capability is needed to do this action?** → determines the `current_user_can()` argument.
3. **Is this a state change?** → if yes, nonce required.

## See also

- `skills/wp-database` for `$wpdb->prepare()` patterns.
- WordPress codex: [Data Validation](https://developer.wordpress.org/apis/security/data-validation/), [Securing Output](https://developer.wordpress.org/apis/security/escaping/), [Nonces](https://developer.wordpress.org/apis/security/nonces/).
- `red-tests.md` in this skill folder: pressure scenarios for validating that this skill actually changes behavior.
