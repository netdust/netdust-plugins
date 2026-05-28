You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on Stride. Add a REST endpoint to the existing admin REST namespace (`stride/v1/admin/`) that returns a paginated list of LearnDash courses, each with its enrollment count and completion percentage.

Requirements:
- Route: `GET /stride/v1/admin/courses`
- Query params: `page` (int, default 1, min 1), `per_page` (int, default 20, min 1, max 100), `search` (optional string, fragment-matched against course title).
- Response shape should follow the project's standard for paginated collections (look at existing admin endpoints for the convention).
- Admin-only (only users with `stride_view` capability).

Write the controller method that registers the route and the callback that returns the data. Don't write the full class — just the new route registration block and the callback method.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
