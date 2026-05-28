# JUDGE PROMPT TEMPLATE — scenario 7

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-7-baseline.md and outputs/scenario-7-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 7
#    This writes prompts/scenario-7-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. Build a `QuoteService` for generating PDF quotes. The service should:

1. Be a top-level service registered in plugin-config.php.
2. Own two sub-services internally: `QuoteNumberGenerator` (formats unique quote numbers like `OFF-2026-0042`) and `QuotePdfRenderer` (renders the PDF). These should NOT be top-level services — they're internal to QuoteService.
3. Expose `createQuote(array $line_items, int $customer_id): WP_Post|WP_Error` as its public method (creates a `stride_quote` post + renders + saves PDF).

Write the QuoteService class, the two sub-services, and show how QuoteService wires them up internally. Don't write the PDF rendering implementation itself or the database calls — those are the sub-services' jobs, we're testing the wiring pattern.

# Rules to score:
- **A1** (canonical): Implements `NTDST_Service_Meta` (directly or via `AbstractService`)
- **A2** (canonical): Static `metadata()` returning `{name, description, priority, admin_only?, enabled?}`
- **A4** (canonical): Constructor DI uses `readonly` properties (PHP 8.1+)
- **A6** (canonical): Sub-services owned by parent registered as singletons inside parent's `init()` via `ntdst_set()`
- **A10** (canonical): Service files: soft cap ~400 lines, methods soft cap ~30 lines. `init()` is the natural longest method. Admin UI orchestrators (under `Admin/`) are documented exceptions.
- **B3** (canonical): Errors propagate as `WP_Error` — never thrown exceptions, never `false`/`null` for failure
- **X1** (canonical): PHP 8.1+ features throughout: readonly properties, enums, typed properties, named arguments where useful
- **X2** (canonical): No `add_action`/`add_filter` outside `init()` / `boot()` lifecycle methods
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
- **X4** (canonical): `WP_Error` universal for errors. Exceptions NOT thrown from service methods.
