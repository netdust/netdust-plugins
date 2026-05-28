You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on Stride. Set up a new `Notifications` module that:

1. Registers a new custom post type `stride_notification` (statuses: `unread`, `read`, `archived` — use post_status). Title required, content optional. Author = the user being notified.
2. Exposes a top-level `NotificationService` (public API: `notifyUser(int $user_id, string $message): WP_Post|WP_Error`).
3. Owns an internal `NotificationDispatcher` (handles the actual delivery — email, web push later). This is NOT a top-level service — it's an internal implementation detail of NotificationService and shouldn't be discoverable on its own.
4. Wires the module into stride-core's bootstrap.

Write all the files (file path + content for each). Mention where each file lives in the project tree.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
