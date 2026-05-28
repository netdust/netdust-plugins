You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on the Stride LMS Bedrock site (PHP 8.3, mu-plugins/stride-core/). Add a service that sends a daily email digest to course instructors summarizing yesterday's new enrollments in their courses.

Requirements:
- Runs once per day via WP-Cron at 06:00 site-local time.
- Hooks into the existing `stride/registration/created` domain event for live tracking (so the digest aggregates without an extra DB scan).
- Exposes a public `sendDigestNow(int $instructor_user_id): WP_Error|true` method that other code can call to trigger a digest immediately (for testing or admin "send now" buttons).

Write the complete service class. Don't write the cron registration file or the email template — just the service.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
