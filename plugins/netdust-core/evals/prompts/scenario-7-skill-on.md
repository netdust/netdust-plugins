You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

You're working on Stride. Build a `QuoteService` for generating PDF quotes. The service should:

1. Be a top-level service registered in plugin-config.php.
2. Own two sub-services internally: `QuoteNumberGenerator` (formats unique quote numbers like `OFF-2026-0042`) and `QuotePdfRenderer` (renders the PDF). These should NOT be top-level services — they're internal to QuoteService.
3. Expose `createQuote(array $line_items, int $customer_id): WP_Post|WP_Error` as its public method (creates a `stride_quote` post + renders + saves PDF).

Write the QuoteService class, the two sub-services, and show how QuoteService wires them up internally. Don't write the PDF rendering implementation itself or the database calls — those are the sub-services' jobs, we're testing the wiring pattern.

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
