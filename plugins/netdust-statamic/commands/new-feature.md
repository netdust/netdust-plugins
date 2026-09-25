---
description: Build a new Statamic feature through netdust-gates:policy with the Statamic-specific overrides wired in — brainstorm → plan → execute → gate → review → fix → shake-out → promote.
argument-hint: <one-line feature description>
---

Build a new Statamic feature: **$1**

This command runs the **one canonical policy** (`netdust-gates:policy`) so no gate gets skipped — threat-modeling, `/plan-review`, the feature review and the shake-out all apply on Statamic exactly as they do on every other stack. It does NOT reimplement the pipeline; it invokes it and supplies the Statamic-specific tools for each stage.

## Step 1 — Invoke the policy

Invoke `Skill("netdust-gates:policy")` and follow its path (a new feature is almost always the architectural one). Start the branch with `make feature name=<feature>` — `feature/<feature>`, cut from production. Apply the Statamic overrides below at the stages they name.

## Step 2 — Statamic overrides per stage

These replace or sharpen the generic skill the policy names at each stage.

- **Stage 0 — Design.** Use `superpowers:brainstorming` (Statamic has no rigid framework-design skill the way WP does). Produce clarity on user-facing intent: who it's for (editor / developer / end-visitor), one-sentence success, smallest viable shape, what's explicitly out of scope, and any constraints from the editor-profile rules in CLAUDE.md. **Checkpoint:** show the brainstorm, wait for "yes, that's it" before planning.

- **Stage 1 — Plan.** The policy fires `writing-plans` + (when triggered) `netdust-gates:threat-modeling`. The plan lands at `specs/<feature>/plan.md` with files, order of operations, per-task test expectations, and a "done" definition matching the `statamic-build` success criteria. **If the feature touches the page builder, the plan MUST include:** the closest existing block as reference, the field list audited against the 6 editor-friendliness rules, and whether `sections:` are needed. **Threat-model triggers on Statamic:** forms, user/CP input, REST endpoints, file uploads, outbound URLs, multi-site. Then `/plan-review`. **Checkpoint:** show the plan, wait for approval.

- **Stage 2 — Execute.** The executor is `statamic-build` — follow its PRE-WRITE → WRITE → VERIFY process for each plan step, each task closing with its tests green. During execution: use `statamic-mcp` for content ops, `laravel-boost` `search-docs` for framework APIs, stache clear+warm after schema changes, and `superpowers:systematic-debugging` (one invocation per bug) for any mid-implementation bug. **Checkpoint after each plan step** — don't batch five steps then summarize.

- **Stage 3 — Close, by cost.** First the Statamic verify: `ddev exec php artisan test --compact` green, `vendor/bin/pint --dirty --format agent` clean, `ddev exec php please stache:warm` if schema changed, affected pages rendered with a clean console. Then the policy Close:
  1. `make gate` — exits 0
  2. `make review name=<feature>` — the feature review
  3. One fix pass on every Blocking / Should fix; the review kept as `specs/<feature>/review.md`
  4. `shake-out-statamic` sweep, then `/shakeout` once on the fixed code (`specs/<feature>/shakeout.md`, `bin/shakeout-check.py` exits 0)
  5. Push and hand over `make promote name=<feature>` — a feature never merges into production by hand

## When NOT to use this command

- One-line content edits, pure docs — just do them.
- Bug fixes with a known cause — use `superpowers:systematic-debugging` directly.
- Refactors — `netdust-gates:policy` directly (its bounded path).

This is for **building something new** (a block, collection, service, page-level feature). The cost of the policy on a small thing is minutes; the cost of skipping it on a big thing is hours.
