# JUDGE PROMPT TEMPLATE — scenario 2a

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-2a-baseline.md and outputs/scenario-2a-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 2a
#    This writes prompts/scenario-2a-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. The Edition module wraps the `vad_edition` custom post type (a "scheduled offering" of a course). Edition has post meta fields including `course_id` (int), `start_date` (Y-m-d string), `end_date` (Y-m-d string), `status` (post_status — `publish`, `draft`, `archive`, `cancelled`).

Add a method `getUpcomingForCourse(int $course_id, int $limit = 10): array` to `EditionRepository`. It returns the next N published Editions for a given course, where `start_date` is today or later, ordered by start_date ascending. Each returned item should be a hydrated `WP_Post` with formatted meta (the framework's standard hydration shape).

Just write the new method. Don't rewrite the rest of EditionRepository or invent new dependencies.

# Rules to score:
- **B1** (canonical): Two-track model: `ntdst_data()` for CPT/post-meta. `$wpdb->prepare()` directly for high-volume / transactional custom tables.
- **B2** (canonical): `RepositoryInterface` defines `find(int $id): WP_Post|WP_Error`, `create(array): WP_Post|WP_Error`, `update(int, array): WP_Post|WP_Error`, `delete(int, bool): bool|WP_Error`
- **B3** (canonical): Errors propagate as `WP_Error` — never thrown exceptions, never `false`/`null` for failure
- **B9** (canonical): Per-request memoization in repositories for hot queries; transients for cross-request caching
- **EX7** (canonical): `find()` returns `WP_Post` object; `get()` returns array of arrays. Critical bug source if confused.
- **A4** (canonical): Constructor DI uses `readonly` properties (PHP 8.1+)
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
