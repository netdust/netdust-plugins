You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on Stride. The Edition module wraps the `vad_edition` custom post type (a "scheduled offering" of a course). Edition has post meta fields including `course_id` (int), `start_date` (Y-m-d string), `end_date` (Y-m-d string), `status` (post_status — `publish`, `draft`, `archive`, `cancelled`).

Add a method `getUpcomingForCourse(int $course_id, int $limit = 10): array` to `EditionRepository`. It returns the next N published Editions for a given course, where `start_date` is today or later, ordered by start_date ascending. Each returned item should be a hydrated `WP_Post` with formatted meta (the framework's standard hydration shape).

Just write the new method. Don't rewrite the rest of EditionRepository or invent new dependencies.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
