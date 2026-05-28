You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

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
