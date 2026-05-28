You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on Stride. The frontend has a "subscribe to weekly digest" form on the user profile page. When submitted via AJAX, it should:

1. Add the current logged-in user to a digest subscriber list (use `update_user_meta` with key `stride_digest_subscribed` set to `1`).
2. Return a success message safe to render in the DOM.

Use Stride's ntdst_api action pattern (the project's internal AJAX router — handlers register via `add_filter('ntdst/api_data/{action}', ...)`). The action name should be `stride_subscribe_to_digest`. The frontend sends `{action: 'stride_subscribe_to_digest'}` with a nonce.

Write the handler class.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
