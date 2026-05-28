---
description: Sequenced workflow for building a new feature in ntdst-starter — brainstorm → plan → execute → shake-out with checkpoints
argument-hint: <one-line feature description>
---

Implement a new feature: **$1**

This is the canonical workflow for non-trivial features. Don't skip steps — each guards against a specific failure mode.

---

## Phase 1 — Brainstorm (5–15 min)

Invoke `Skill("superpowers:brainstorming")` with the feature description.

What you're producing here is **clarity on the user-facing intent**, not a plan. Output:
- Who is this for (editor / developer / end-visitor)?
- What does success look like in one sentence?
- What's the smallest viable shape?
- What's explicitly NOT in scope?
- Any constraints from the editor-profile rules in CLAUDE.md?

**Checkpoint:** Show the brainstorm output to the user. Wait for "yes, that's it" or revisions before continuing. Do not write a plan from a fuzzy brainstorm.

---

## Phase 2 — Plan (10–30 min)

Invoke `Skill("superpowers:writing-plans")` with the brainstorm output as input.

The plan should be a `docs/superpowers/plans/YYYY-MM-DD-<feature-slug>.md` file with:
- Files to create/modify
- Order of operations
- Test strategy
- What "done" looks like (matches the success criteria from `ntdst-statamic-build` skill)

If the feature touches the page builder, the plan must include:
- Which existing block is the closest reference
- Field list with audit against the 6 editor-friendliness rules
- Whether `sections:` are needed

**Checkpoint:** Show the plan to the user. Wait for approval. **Do not start writing code from an unapproved plan.**

---

## Phase 3 — Execute (varies)

Invoke `Skill("ntdst-statamic-build")` and follow its three-phase process (PRE-WRITE → WRITE → VERIFY) for each plan step.

Key reminders during execution:
- Use `statamic-mcp` for content operations
- Use `laravel-boost` `search-docs` when unsure about framework APIs
- Stache clear+warm after schema changes
- Mid-implementation bugs go through `superpowers:systematic-debugging`, not inline guess-and-fix
- Mark each plan task complete in `tasks/todo.md` as you go

**Checkpoint after each plan step:** Show the user what changed. Don't batch-implement five steps then summarize — the user can't course-correct from a 500-line diff.

---

## Phase 4 — Shake out (15–60 min depending on change scope)

Invoke `Skill("shake-out-statamic")`.

Three-phase sweep → manifest → fix. The shake-out skill enforces:
- No fixing during sweep
- Bug manifest with severity
- Per-bug `systematic-debugging` invocation

For trivial changes (one-line edits, simple content updates): you can skip shake-out and use the smoke test + render check from the build skill instead. **Default to running shake-out.** Skipping is the exception, not the rule.

---

## Phase 5 — Verify and finish

1. `ddev exec php artisan test --compact` — must be green
2. `vendor/bin/pint --dirty --format agent` — must be clean
3. `ddev exec php please stache:warm` — required if schema changed
4. Render the affected pages, check for console errors via chrome-devtools
5. Update `tasks/todo.md` with a Review section (what worked, what didn't, follow-ups)
6. Capture lessons in `tasks/lessons.md` if the user corrected anything significant

**Checkpoint:** Present the final state to the user. Don't auto-commit — let them review and approve, then they say "commit" if they want. The pre-commit hook will run Pint + tests automatically.

---

## When NOT to use this command

- One-line content edits (just do them)
- Pure documentation changes (just do them)
- Bug fixes with a known cause (use `superpowers:systematic-debugging` directly)
- Refactors (different mode — use `code-simplicity-reviewer` agent or just edit + verify)

This workflow is for **building something new** — a block, a collection, a service, a page-level feature. Default to using it. The cost of running it on a small thing is minutes; the cost of skipping it on a big thing is hours.
