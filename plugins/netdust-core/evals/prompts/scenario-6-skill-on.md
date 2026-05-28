You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on Stride. The frontend has a "subscribe to weekly digest" form on the user profile page. When submitted via AJAX, it should:

1. Add the current logged-in user to a digest subscriber list (use `update_user_meta` with key `stride_digest_subscribed` set to `1`).
2. Return a success message safe to render in the DOM.

Use Stride's ntdst_api action pattern (the project's internal AJAX router — handlers register via `add_filter('ntdst/api_data/{action}', ...)`). The action name should be `stride_subscribe_to_digest`. The frontend sends `{action: 'stride_subscribe_to_digest'}` with a nonce.

Write the handler class.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
