# JUDGE PROMPT TEMPLATE — scenario 6

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-6-baseline.md and outputs/scenario-6-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 6
#    This writes prompts/scenario-6-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. The frontend has a "subscribe to weekly digest" form on the user profile page. When submitted via AJAX, it should:

1. Add the current logged-in user to a digest subscriber list (use `update_user_meta` with key `stride_digest_subscribed` set to `1`).
2. Return a success message safe to render in the DOM.

Use Stride's ntdst_api action pattern (the project's internal AJAX router — handlers register via `add_filter('ntdst/api_data/{action}', ...)`). The action name should be `stride_subscribe_to_digest`. The frontend sends `{action: 'stride_subscribe_to_digest'}` with a nonce.

Write the handler class.

# Rules to score:
- **A12** (canonical): Handlers (HTTP/AJAX/request handlers) NOT services. Instantiated explicitly; no metadata; no priority; lazy DI via `ntdst_get()` inside methods
- **EX10** (canonical): ntdst_api is the structured AJAX router — NOT a generic REST replacement
- **EX8** (canonical): AJAX always uses `check_ajax_referer()`
- **EX9** (canonical): Per-object capability checks after coarse cap checks (e.g., `current_user_can('edit_posts')` then `current_user_can('edit_post', $post_id)`)
- **EX5** (canonical): Context-specific escapers are NOT interchangeable: `esc_html` for body, `esc_attr` for attributes, `esc_url` for hrefs
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
- **X4** (canonical): `WP_Error` universal for errors. Exceptions NOT thrown from service methods.
