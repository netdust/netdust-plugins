# JUDGE PROMPT TEMPLATE — scenario 1

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-1-baseline.md and outputs/scenario-1-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 1
#    This writes prompts/scenario-1-judge.md with both outputs inlined.

# Scenario prompt:
You're working on the Stride LMS Bedrock site (PHP 8.3, mu-plugins/stride-core/). Add a service that sends a daily email digest to course instructors summarizing yesterday's new enrollments in their courses.

Requirements:
- Runs once per day via WP-Cron at 06:00 site-local time.
- Hooks into the existing `stride/registration/created` domain event for live tracking (so the digest aggregates without an extra DB scan).
- Exposes a public `sendDigestNow(int $instructor_user_id): WP_Error|true` method that other code can call to trigger a digest immediately (for testing or admin "send now" buttons).

Write the complete service class. Don't write the cron registration file or the email template — just the service.

# Rules to score:
- **A1** (canonical): Implements `NTDST_Service_Meta` (directly or via `AbstractService`)
- **A2** (canonical): Static `metadata()` returning `{name, description, priority, admin_only?, enabled?}`
- **A3** (canonical): Hooks registered ONLY in `init()` or a provider's `boot()` — never in `__construct()`
- **A4** (canonical): Constructor DI uses `readonly` properties (PHP 8.1+)
- **A5** (canonical): Config arrives via `apply_filters("{project}_{slug}_config", [])` — per-project prefix
- **A9** (canonical): Domain events as `do_action('{project}/{event}', $data)` with plain associative array payloads
- **A10** (canonical): Service files: soft cap ~400 lines, methods soft cap ~30 lines. `init()` is the natural longest method. Admin UI orchestrators (under `Admin/`) are documented exceptions.
- **A11** (canonical): Priority convention: `<10 = critical/early`, `10–15 = standard`, `20+ = late`
- **A12** (canonical): Handlers (HTTP/AJAX/request handlers) NOT services. Instantiated explicitly; no metadata; no priority; lazy DI via `ntdst_get()` inside methods
- **B3** (canonical): Errors propagate as `WP_Error` — never thrown exceptions, never `false`/`null` for failure
- **E5** (canonical): Bootstrap timing: `after_setup_theme:5` for priority <10 (core), `after_setup_theme:15` for ≥10 (features)
- **X1** (canonical): PHP 8.1+ features throughout: readonly properties, enums, typed properties, named arguments where useful
- **X2** (canonical): No `add_action`/`add_filter` outside `init()` / `boot()` lifecycle methods
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
- **X4** (canonical): `WP_Error` universal for errors. Exceptions NOT thrown from service methods.
- **EX1** (canonical): `declare(strict_types=1);` as first line of every PHP file
