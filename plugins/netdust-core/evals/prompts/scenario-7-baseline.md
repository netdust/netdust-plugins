You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

You're working on Stride. Build a `QuoteService` for generating PDF quotes. The service should:

1. Be a top-level service registered in plugin-config.php.
2. Own two sub-services internally: `QuoteNumberGenerator` (formats unique quote numbers like `OFF-2026-0042`) and `QuotePdfRenderer` (renders the PDF). These should NOT be top-level services — they're internal to QuoteService.
3. Expose `createQuote(array $line_items, int $customer_id): WP_Post|WP_Error` as its public method (creates a `stride_quote` post + renders + saves PDF).

Write the QuoteService class, the two sub-services, and show how QuoteService wires them up internally. Don't write the PDF rendering implementation itself or the database calls — those are the sub-services' jobs, we're testing the wiring pattern.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
