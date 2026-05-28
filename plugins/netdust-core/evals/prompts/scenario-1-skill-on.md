You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on the Stride LMS Bedrock site (PHP 8.3, mu-plugins/stride-core/). Add a service that sends a daily email digest to course instructors summarizing yesterday's new enrollments in their courses.

Requirements:
- Runs once per day via WP-Cron at 06:00 site-local time.
- Hooks into the existing `stride/registration/created` domain event for live tracking (so the digest aggregates without an extra DB scan).
- Exposes a public `sendDigestNow(int $instructor_user_id): WP_Error|true` method that other code can call to trigger a digest immediately (for testing or admin "send now" buttons).

Write the complete service class. Don't write the cron registration file or the email template — just the service.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
