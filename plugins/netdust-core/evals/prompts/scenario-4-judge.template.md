# JUDGE PROMPT TEMPLATE — scenario 4

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-4-baseline.md and outputs/scenario-4-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 4
#    This writes prompts/scenario-4-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. Add a WP-CLI command `wp stride backfill-completions <user-id>` that recomputes LearnDash course completions from scratch for a single user (useful when LearnDash's completion table has drifted from the real lesson/quiz state).

The command should support a dry-run mode (preview what would change without writing) and verbose output (log per-course details, not just the summary). Should also validate that the user ID exists before doing anything.

Add the command and its handler. You can assume the recompute logic itself exists as a method `recomputeForUser(int $user_id, bool $dry_run, bool $verbose): array` on `CourseCompletionService` — your job is to wire it up as a WP-CLI command following the project's conventions.

# Rules to score:
- **D1** (canonical): Registration guarded by `if (defined('WP_CLI') && WP_CLI) { WP_CLI::add_command(...) }` inside owning service's `init()`
- **D2** (canonical): Command handler is a method on the service, NOT a separate Command class
- **D3** (canonical): Method signature `($args, $assocArgs)` — positional via `$args`, flags via `$assocArgs`
- **D4** (canonical): Dry-run is the DEFAULT; `--commit` is the explicit opt-in to write
- **D5** (canonical): Output: `WP_CLI::log()` for info, `WP_CLI::success()` for completion. `WP_CLI::error()` exits the process — use sparingly.
- **D6** (aspirational): Declare `shortdesc` / `synopsis` in `WP_CLI::add_command()` for `wp help` output
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
