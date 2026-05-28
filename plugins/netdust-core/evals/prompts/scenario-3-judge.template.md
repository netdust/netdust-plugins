# JUDGE PROMPT TEMPLATE — scenario 3

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-3-baseline.md and outputs/scenario-3-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 3
#    This writes prompts/scenario-3-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. Add a REST endpoint to the existing admin REST namespace (`stride/v1/admin/`) that returns a paginated list of LearnDash courses, each with its enrollment count and completion percentage.

Requirements:
- Route: `GET /stride/v1/admin/courses`
- Query params: `page` (int, default 1, min 1), `per_page` (int, default 20, min 1, max 100), `search` (optional string, fragment-matched against course title).
- Response shape should follow the project's standard for paginated collections (look at existing admin endpoints for the convention).
- Admin-only (only users with `stride_view` capability).

Write the controller method that registers the route and the callback that returns the data. Don't write the full class — just the new route registration block and the callback method.

# Rules to score:
- **C1** (canonical): Routes registered via `register_rest_route()` inside a dedicated Controller class's `registerRoutes()` method, hooked to `rest_api_init`
- **C2** (canonical): `permission_callback` is always a real capability check or `WP_Error`-returning method — NEVER `__return_true`, NEVER `is_user_logged_in` as a function reference
- **C3** (canonical): Explicit `args` schema with `type`, `default`, `minimum`/`maximum`/`enum` declared in route registration. WordPress auto-validates and sanitizes before callback runs.
- **C4** (canonical): Responses wrapped in `WP_REST_Response`; errors as `WP_Error` with explicit HTTP status in third arg
- **C5** (canonical): Paginated collections use `{data: [...], total: int, page: int, per_page: int}` envelope
- **EX4** (canonical): LIKE patterns use `$wpdb->esc_like($needle)` before wrapping in `%`
- **EX5** (canonical): Context-specific escapers are NOT interchangeable: `esc_html` for body, `esc_attr` for attributes, `esc_url` for hrefs
- **EX9** (canonical): Per-object capability checks after coarse cap checks (e.g., `current_user_can('edit_posts')` then `current_user_can('edit_post', $post_id)`)
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
