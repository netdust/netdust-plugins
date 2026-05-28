You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on Stride. The Enrollment module tracks user-course relationships in a custom table `wp_vad_registrations` (currently ~500k rows, growing ~2k/day, used in transactional flows like capacity checks during registration). Columns: `id` (PK), `user_id` (FK), `edition_id` (FK), `status` (ENUM: `pending`, `confirmed`, `cancelled`, `completed`), `registered_at` (datetime), `selections` (JSON column).

Add a method `findActiveByEditionIds(array $edition_ids, int $limit = 200): array` to `RegistrationRepository`. It returns registrations whose `edition_id` is in the given list AND `status` is `confirmed` OR `pending`, ordered by `registered_at` DESC, limited to N. Each row should be returned as a stdClass with the `selections` column decoded from JSON.

Just write the new method.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
