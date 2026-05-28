# JUDGE PROMPT TEMPLATE — scenario 2b

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-2b-baseline.md and outputs/scenario-2b-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 2b
#    This writes prompts/scenario-2b-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. The Enrollment module tracks user-course relationships in a custom table `wp_vad_registrations` (currently ~500k rows, growing ~2k/day, used in transactional flows like capacity checks during registration). Columns: `id` (PK), `user_id` (FK), `edition_id` (FK), `status` (ENUM: `pending`, `confirmed`, `cancelled`, `completed`), `registered_at` (datetime), `selections` (JSON column).

Add a method `findActiveByEditionIds(array $edition_ids, int $limit = 200): array` to `RegistrationRepository`. It returns registrations whose `edition_id` is in the given list AND `status` is `confirmed` OR `pending`, ordered by `registered_at` DESC, limited to N. Each row should be returned as a stdClass with the `selections` column decoded from JSON.

Just write the new method.

# Rules to score:
- **B1** (canonical): Two-track model: `ntdst_data()` for CPT/post-meta. `$wpdb->prepare()` directly for high-volume / transactional custom tables.
- **B3** (canonical): Errors propagate as `WP_Error` — never thrown exceptions, never `false`/`null` for failure
- **B4** (canonical): Every dynamic value in SQL goes through `$wpdb->prepare()` with typed placeholder (`%d` / `%s` / `%i`)
- **B5** (canonical): `IN(...)` clauses use placeholder array: `implode(',', array_fill(0, count($ids), '%d'))` then `$wpdb->prepare($sql, ...$ids)`
- **B6** (canonical): `ORDER BY` and column-identifier contexts use only hardcoded column names — never user input, even sanitized
- **B8** (aspirational): JSON columns (not serialized PHP) for optional structured data, auto-decoded in repository
- **B9** (canonical): Per-request memoization in repositories for hot queries; transients for cross-request caching
- **B10** (canonical): Caching disabled in `WP_DEBUG` unless `NTDST_ENABLE_CACHE_IN_DEBUG` is set
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
