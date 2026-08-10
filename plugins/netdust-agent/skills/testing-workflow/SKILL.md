---
name: testing-workflow
description: "The per-task test decision — what tier of test a task owes before it closes, and through which runner. Fires on 'does this need a test', 'is this Tier A or B', 'do I need a test for this nonce/capability/sanitize call', 'this feature is drowning in tests'. Layers the netdust tier rule onto superpowers:test-driven-development, which owns the RED→GREEN mechanics. On WordPress the runner is the netdust harness (Brain Monkey / wp-phpunit — the netdust-wp-manager template); superpowers has no knowledge of that environment, so this skill is what routes tests through it."
---

# Testing workflow — the tier decision

`superpowers:test-driven-development` owns HOW to write a test. This decides WHETHER and
AT WHAT TIER, in three questions asked in order:

**1. What does a failure cost?** Read the plan's `Stakes:` line (effective per-cluster
value when a table exists). Never re-decide it.

**2. What already proves this?** The evidence ladder, cheapest-broadest first — record the
answer as the task's `Proven by:` line, naming the evidence:
`machine gate > framework guarantee > existing test > new test`.
A project gate proving a property across the whole diff beats a unit test proving it at
one call site. Only reach "new test" when the cheaper rungs genuinely don't cover it.

**3. What tier, then?**

| The change is… | Tier | It owes |
|---|---|---|
| a predicate/parser/state-machine encoding a rule THIS PROJECT chose (a role, a window, an ownership test, a threshold, a derivation) | **A** — regardless of line count | a RED-first behavioural test incl. the denial path |
| a direct call to a hardened framework primitive that decides nothing (`wp_verify_nonce`, `current_user_can`, `sanitize_*`, `schema.parse`) | **B** | a PRESENCE proof named on `Proven by:` — never a behavioural test re-proving the framework |
| glue, wrappers, declarative config, pass-through UI | **B** | `no unit test: Tier B, <reason>` — or `covered by cluster behaviour` inside a valid behaviour block |
| wiring a piece into a real chain | either | one un-mocked seam assertion + one negative case |

Risk that only exists in real WordPress — hook lifecycle, CPT registration effects,
DB/schema behaviour — is an `Integration test: <contract>` line: name the real-WP
behaviour Brain Monkey cannot express, and prove it through the integration runner, never
the unit suite.

## Runners (auto-detect; the WP harness is mandatory on WP)

| Stack | Unit | Integration |
|---|---|---|
| WordPress (netdust-wp-manager template) | `composer test:unit` — Brain Monkey, no WP needed | `ddev composer test:int` — wp-phpunit through DDEV |
| WordPress (full gate) | `composer gate` / `bin/gate.sh` | included |
| TypeScript | Vitest | Playwright |

Anything needing WordPress or the database runs through DDEV. `hooks/subagent-stop.py`
backstops the close: suite ran, implementer-green, linter not skipped.

Feature-level tests — the behaviour a task GROUP promised — are the `test-author`'s job
after the cluster lands (see `building`), not extra weight on each task. When a suite
feels oversized, the ladder was skipped: check what rung 1–3 already proved.
