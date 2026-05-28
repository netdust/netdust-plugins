You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on Stride. Add a WP-CLI command `wp stride backfill-completions <user-id>` that recomputes LearnDash course completions from scratch for a single user (useful when LearnDash's completion table has drifted from the real lesson/quiz state).

The command should support a dry-run mode (preview what would change without writing) and verbose output (log per-course details, not just the summary). Should also validate that the user ID exists before doing anything.

Add the command and its handler. You can assume the recompute logic itself exists as a method `recomputeForUser(int $user_id, bool $dry_run, bool $verbose): array` on `CourseCompletionService` — your job is to wire it up as a WP-CLI command following the project's conventions.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
