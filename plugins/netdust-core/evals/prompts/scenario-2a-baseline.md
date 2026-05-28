You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on Stride. The Edition module wraps the `vad_edition` custom post type (a "scheduled offering" of a course). Edition has post meta fields including `course_id` (int), `start_date` (Y-m-d string), `end_date` (Y-m-d string), `status` (post_status — `publish`, `draft`, `archive`, `cancelled`).

Add a method `getUpcomingForCourse(int $course_id, int $limit = 10): array` to `EditionRepository`. It returns the next N published Editions for a given course, where `start_date` is today or later, ordered by start_date ascending. Each returned item should be a hydrated `WP_Post` with formatted meta (the framework's standard hydration shape).

Just write the new method. Don't rewrite the rest of EditionRepository or invent new dependencies.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
