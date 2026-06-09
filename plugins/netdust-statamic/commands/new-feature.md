---
description: Build a new Statamic feature through the full harness (harnessed-development) with the Statamic-specific overrides wired in — design → plan + gates → execute → shake-out → finish.
argument-hint: <one-line feature description>
---

Build a new Statamic feature: **$1**

This command runs the **one canonical harness** (`netdust-agent:harnessed-development`) so no gate gets skipped — threat-modeling, architecture-invariants, per-task testing-workflow, and the Step-2.5 plan-freshness check all apply on Statamic exactly as they do on every other stack. It does NOT reimplement the pipeline; it invokes it and supplies the Statamic-specific tools for each stage.

## Step 1 — Invoke the harness

Invoke `Skill("netdust-agent:harnessed-development")`. Classify the work (it's almost always **Class A — new feature**). Follow its stages. Apply the Statamic overrides below at the stages they name.

## Step 2 — Statamic overrides per stage

These replace or sharpen the generic skill the harness names at each stage. Hand them to the harness as you reach each stage.

- **Stage 0 — Design.** Use `superpowers:brainstorming` (Statamic has no rigid framework-design skill the way WP does). Produce clarity on user-facing intent: who it's for (editor / developer / end-visitor), one-sentence success, smallest viable shape, what's explicitly out of scope, and any constraints from the editor-profile rules in CLAUDE.md. **Checkpoint:** show the brainstorm, wait for "yes, that's it" before planning.

- **Stage 1 — Plan + gates.** The harness fires `writing-plans` + (when triggered) `threat-modeling` + `architecture-invariants`. The plan lands at `docs/superpowers/plans/YYYY-MM-DD-<feature-slug>.md` with files, order of operations, per-task test expectations, and a "done" definition matching the `statamic-build` success criteria. **If the feature touches the page builder, the plan MUST include:** the closest existing block as reference, the field list audited against the 6 editor-friendliness rules, and whether `sections:` are needed. **Threat-model triggers on Statamic:** forms, user/CP input, REST endpoints, file uploads, outbound URLs, multi-site. **Checkpoint:** show the plan, wait for approval.

- **Stage 2 — Execute.** The harness's executor is `statamic-build` — follow its PRE-WRITE → WRITE → VERIFY process for each plan step, under the harness's testing-workflow gate (each task closes with tests + the Step-2.5 ground-truth before dispatch). During execution: use `statamic-mcp` for content ops, `laravel-boost` `search-docs` for framework APIs, stache clear+warm after schema changes, and `superpowers:systematic-debugging` (one invocation per bug) for any mid-implementation bug. **Checkpoint after each plan step** — don't batch five steps then summarize.

- **Stage 3 — Shake-out + finish.** The harness's shake-out override is `shake-out-statamic` (sweep → manifest → per-bug fix). Then the Statamic verify gate:
  1. `ddev exec php artisan test --compact` — green
  2. `vendor/bin/pint --dirty --format agent` — clean
  3. `ddev exec php please stache:warm` — if schema changed
  4. Render affected pages, check console via chrome-devtools
  5. Update `tasks/todo.md` Review section; capture lessons in `tasks/lessons.md`
  Then `superpowers:finishing-a-development-branch`. **Don't auto-commit** — let the user review and say "commit"; the pre-commit hook runs Pint + tests.

## When NOT to use this command

- One-line content edits, pure docs — just do them.
- Bug fixes with a known cause — use `superpowers:systematic-debugging` directly.
- Refactors — use the `code-simplicity-reviewer` agent or edit + verify.

This is for **building something new** (a block, collection, service, page-level feature). The cost of the harness on a small thing is minutes; the cost of skipping it on a big thing is hours.
