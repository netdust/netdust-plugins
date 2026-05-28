You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on Stride. The Enrollment module tracks user-course relationships in a custom table `wp_vad_registrations` (currently ~500k rows, growing ~2k/day, used in transactional flows like capacity checks during registration). Columns: `id` (PK), `user_id` (FK), `edition_id` (FK), `status` (ENUM: `pending`, `confirmed`, `cancelled`, `completed`), `registered_at` (datetime), `selections` (JSON column).

Add a method `findActiveByEditionIds(array $edition_ids, int $limit = 200): array` to `RegistrationRepository`. It returns registrations whose `edition_id` is in the given list AND `status` is `confirmed` OR `pending`, ordered by `registered_at` DESC, limited to N. Each row should be returned as a stdClass with the `selections` column decoded from JSON.

Just write the new method.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
