You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on Stride. Set up a new `Notifications` module that:

1. Registers a new custom post type `stride_notification` (statuses: `unread`, `read`, `archived` — use post_status). Title required, content optional. Author = the user being notified.
2. Exposes a top-level `NotificationService` (public API: `notifyUser(int $user_id, string $message): WP_Post|WP_Error`).
3. Owns an internal `NotificationDispatcher` (handles the actual delivery — email, web push later). This is NOT a top-level service — it's an internal implementation detail of NotificationService and shouldn't be discoverable on its own.
4. Wires the module into stride-core's bootstrap.

Write all the files (file path + content for each). Mention where each file lives in the project tree.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
