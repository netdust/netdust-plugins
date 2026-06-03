---
name: shake-out-statamic
description: Post-build QA phase for Statamic 6 + Peak projects. Sweeps the built artifact end-to-end (stache, blueprints, page builder, Peak partials, Antlers/Blade rendering), compiles a bug manifest, then fixes systematically. Use after executing-plans or subagent-driven-development completes when unit tests pass but the artifact hasn't been exercised in a real environment. Triggers on "shake it out", "shakeout", "does it work", "QA this", "find the bugs", "what's broken" — local override of the generic shake-out skill for Statamic projects.
---

<objective>
Statamic-flavoured shake-out. Mirrors the discipline of the global `shake-out` skill (SWEEP → MANIFEST → FIX, three phases, no inline fixing) but adapts the checklist to Statamic 6 + Peak: `please` CLI, the `cboxdk/statamic-mcp` routers, blueprints, stache, Glide, page builder blocks, Peak partials, and Antlers/Blade rendering.

Pipeline position is identical:

```
brainstorm → plan → execute → SHAKE-OUT → finishing-branch
```

This skill **replaces** `shake-out` for this project. When the global skill is loaded alongside, this one wins.
</objective>

<essential_principles>

**The Iron Law**

```
NO FIXES DURING SWEEP
```

Find a bug → LOG IT. Do not fix it. Do not "quickly adjust" it. Do not refactor around it.
Finding and fixing in the same breath is the exact behavior this skill prevents.

**Red Flags — STOP immediately if you catch yourself:**

During SWEEP:
- "Let me just fix this quick while I'm here"
- "I'll note it AND fix it, saves time"
- Modifying any source file during Phase 1
- Proposing solutions before the manifest is complete
- Fixing one bug before all bugs are found
- Editing a blueprint to "smoke test" something — that IS a fix

During FIX:
- Fixing two bugs in one commit
- "While I'm in this file, I'll also..."
- Not re-sweeping after a fix
- Skipping systematic-debugging because "this one is obvious"
- Forgetting to clear the stache after a blueprint change — the bug isn't fixed if the stache is stale

**Common Rationalizations**

| Excuse | Reality |
|--------|---------|
| "This blueprint typo is obvious, one-line fix" | Blueprint typos cascade into stache rebuild + template breakage. Manifest it. |
| "I'll just clear the stache and re-test" | Cache-clearing IS a fix step. Goes through Phase 3. |
| "The page renders, it's fine" | Statamic renders empty content silently. Verify the *content* is there, not just `200`. |
| "Tests pass" | PHPUnit doesn't exercise stache, Glide, page builder rendering, or Antlers tags. |
| "I can see what's wrong, no need for systematic-debugging" | #1 cause of cascading patches. Invoke the skill. Every time. |

</essential_principles>

<quick_start>

Three phases, always in order:

1. **SWEEP** — Run the artifact. Find everything broken. Fix nothing.
2. **MANIFEST** — Present the complete bug list. Cluster by root cause. Get human sign-off.
3. **FIX** — Work through the manifest using `superpowers:systematic-debugging` per bug.

Before starting: read the plan, ensure DDEV is up, warm the stache, then load `references/sweep-statamic.md`.

</quick_start>

<process>

**Input requirements:**
- All plan tasks marked complete
- Code committed on the working branch (`staging` or a feature branch)
- Unit tests passing (`php artisan test --compact`)
- Plan file path known (typically under `docs/superpowers/plans/`)

**Step 0: Preparation**

1. Read the plan document — what was built? Which collections, blueprints, blocks, globals, routes, page templates?
2. Resolve the environment:
   - Check `CLAUDE.md` for project-specific commands
   - Confirm DDEV is up: `ddev status`. If not: `ddev start`
   - Resolve site URL: `ddev describe | grep -oP 'https://[^ ]+\.ddev\.site' | head -1`
   - Warm the stache so checks aren't misleading: `ddev exec php please stache:warm`
3. Detect what flavour of Statamic site this is by reading `composer.json` and `config/statamic/`:
   - Page-builder driven (replicator on `pages` collection) → emphasise block rendering checks
   - Headless / API-only → emphasise REST/GraphQL endpoint checks
   - Multi-site → run smoke checks per site handle
4. Detect available test infrastructure:
   ```bash
   test -f phpunit.xml && echo "PHPUNIT AVAILABLE"
   test -f tests/Feature && echo "FEATURE TESTS DIR EXISTS"
   composer show pestphp/pest 2>/dev/null && echo "PEST AVAILABLE"
   composer show statamic/cms 2>/dev/null | grep versions
   ```

5. Load `references/sweep-statamic.md` and follow it.

**Phase 1: SWEEP**

Two tracks, in sequence.

*Track A — Automated (Claude runs):*

Follow `references/sweep-statamic.md`. The pattern is always:

1. **Smoke** — Does the site respond? Stache warm? No PHP fatals in logs?
2. **Content layer** — Collections list, blueprints valid, entries countable, globals present
3. **Rendering layer** — Each route in the plan returns 200 *and* contains expected content
4. **Page builder** — Each block partial renders (no raw `{{ }}` tags leaking, no missing partials)
5. **Assets / Glide** — Images resolve, no broken `glide:` URLs, asset containers respond
6. **Forms** — Statamic form endpoints accept submissions, validation works, submissions persist
7. **CP** — Control Panel loads, blueprints editable in the UI, no JS console errors

For each check, record:
- What was tested
- What was expected
- What actually happened
- Severity: **CRITICAL** / **IMPORTANT** / **MINOR**

Available tools:

| Tool | What it checks |
|------|----------------|
| `chrome-devtools` MCP | Pages load, JS errors, forms work, CP behaviour, screenshots |
| `statamic-mcp` routers | Entry/blueprint/global state via the action-based router API |
| `php please` (via `ddev exec`) | Stache, search index, glide cache, addon list, sites list |
| `php artisan` (via `ddev exec`) | Routes, config, log inspection, queue state |
| `curl` / HTTP | Status codes, headers, REST API, redirects |
| Log scanning (Read tool) | `storage/logs/laravel.log` for PHP errors |
| File system (Glob/Read) | Blueprint YAML validity, content file frontmatter, partial existence |

*Track B — Manual (human runs):*

After Track A, generate a focused checklist for things Claude can't verify — visual layout in CP, scroll-reveal animations actually animating, video embeds playing, Dutch copy reading naturally, mobile breakpoints. 5–10 items max.

**Wait for human to report back before proceeding to Phase 2.**

**Phase 2: MANIFEST**

After both tracks complete:

1. Write manifest to `tasks/shake-out-manifest.md` using `templates/manifest.md`
2. Cluster bugs by suspected root cause — many Statamic bugs share a stache or blueprint origin and look like five different bugs but are one
3. Assign severity:

| Severity | Meaning | Statamic example |
|----------|---------|---------|
| **CRITICAL** | Doesn't render, data loss, security, broken on every page | Blueprint loads with PHP error, missing required partial, exposed `.env`, stache build fails |
| **IMPORTANT** | Works but with significant problems | One block renders empty, glide returns 404 for hero, form submits but doesn't email |
| **MINOR** | Cosmetic, edge case | Stale meta description, console warning, unused field still in blueprint |

4. Present to human. Ask:
   - "Anything missing from what you observed?"
   - "Do the clusters make sense?"
   - "Agree with priority order?"

**Do not proceed to Phase 3 until human confirms.**

If manifest is empty: skip Phase 3, proceed to Completion.

**Phase 3: FIX**

Work through the manifest: all CRITICAL first, then IMPORTANT, then MINOR.

```
MANDATORY: Every bug MUST be fixed via Skill("superpowers:systematic-debugging").
Do NOT fix bugs inline. Do NOT "just clear the stache and call it done."
If you are editing code without having invoked the skill, you are violating protocol.
```

For each bug (or cluster):

1. **Invoke `superpowers:systematic-debugging`** with the bug details from the manifest.
   The skill enforces:
   - Phase 1: Root cause investigation (read errors, reproduce, trace)
   - Phase 2: Pattern analysis (compare against working blocks/blueprints/partials)
   - Phase 3: Hypothesis and testing (one hypothesis, smallest change)
   - Phase 4: Implementation (failing test first, single fix, verify)

   **Failing-test requirement:** Where the bug is reachable via HTTP, write a PHPUnit feature test in `tests/Feature/` that exercises the route or content path and would have caught the bug. Place it next to existing feature tests (see `tests/Feature/HomepageTest.php` as reference). Some Statamic bugs (CP-only, Glide, scheduling) aren't easily HTTP-testable — note that explicitly in the fix log instead of forcing a brittle test.

2. **Re-sweep the affected area:**
   - Always run `ddev exec php please stache:clear && ddev exec php please stache:warm` after blueprint, fieldset, global, or collection changes — otherwise the bug isn't actually fixed, the stache is just lying
   - If a feature test exists for this area, run it: `ddev exec php artisan test --filter=[TestName]`
   - Otherwise re-run the specific sweep check that found the bug
   - Did the fix resolve it *in the rendered output*?

3. **Check for collateral** — Run the full feature test suite (`ddev exec php artisan test --compact`). Hit related routes with curl. Glance at `storage/logs/laravel.log`.

4. **Update `tasks/shake-out-manifest.md`** — Mark resolved with root-cause notes. If new bugs surfaced, add them.

5. **If 3+ fix attempts fail on the same bug:** STOP. Present to human with options:
   - Continue trying (different approach)
   - Defer this bug
   - **Abort shake-out → return to planning** (see `<abort_and_replan>`)

Fix rules:
- **SYSTEMATIC-DEBUGGING PER BUG. NO EXCEPTIONS.**
- **ONE bug at a time.** No batch fixes.
- **Cluster bugs fix once.** Fix the root cause, verify all symptoms resolve.
- **No "while I'm here" improvements.** Fix the bug. Only the bug.
- **Always clear + warm stache after content schema changes.** Treat it as part of the fix, not optional.
- **Don't remove bugs from the manifest.** Mark resolved with notes. The manifest is the record.
- **Re-sweep after every CRITICAL fix.** Full subsystem re-sweep.

**Completion**

When all bugs are resolved or explicitly deferred:

1. Run abbreviated final sweep — focus on previously broken areas
2. Run `ddev exec php please stache:warm && ddev exec php please search:update --all`
3. Run `vendor/bin/pint --dirty --format agent`
4. Update manifest with final status
5. Present to human: "All [N] resolved. [N] deferred. Here's what changed."
6. Invoke `superpowers:verification-before-completion`
7. Invoke `superpowers:finishing-a-development-branch`

</process>

<abort_and_replan>

If shake-out reveals the implementation approach is fundamentally wrong — e.g., the page-builder block model can't express the design, or the blueprint hierarchy fights the editorial workflow — offer:

1. **Continue fixing** — bugs are fixable within current architecture
2. **Defer and ship** — known issues, ship with caveats
3. **Abort → re-plan** — write `tasks/shake-out-abort-context.md` with: what was built, what failed and why, the architectural insight gained, recommendation for the re-plan. Then invoke `superpowers:brainstorming` (or the stack sub-plugin's design skills if relevant) with that file as context.

</abort_and_replan>

<integration>

**Pipeline position:**
```
brainstorm → plan → execute → SHAKE-OUT-STATAMIC → finishing-branch
```

| Skill | Relationship |
|-------|-------------|
| `executing-plans` / `subagent-driven-development` | **UPSTREAM.** This runs after them. |
| `superpowers:systematic-debugging` | **REQUIRED.** Invoked per bug during Phase 3. |
| `superpowers:verification-before-completion` | **REQUIRED.** Invoked before declaring done. |
| `superpowers:finishing-a-development-branch` | **DOWNSTREAM.** After the manifest is closed. |
| `chrome-devtools` MCP | **REQUIRED.** Browser-level verification of rendering and CP. |
| `statamic-mcp` routers | **REQUIRED.** Content/blueprint state inspection. |
| Generic `shake-out` | **OVERRIDDEN.** This skill replaces it for Statamic projects. |

**Trigger phrases:**
- "shake it out" / "shake-out" / "shakeout"
- "does it actually work" / "QA this" / "check everything"
- "find the bugs" / "what's broken" / "bug hunt"
- "it doesn't work" (when said after a build, not mid-build)

**Do NOT use when:**
- Mid-build debugging (use `systematic-debugging` directly)
- Writing new features (use TDD)
- The project hasn't been built yet
- The project is not Statamic — use the global `shake-out` skill instead

</integration>

<reference_index>

- `references/sweep-statamic.md` — Statamic 6 + Peak sweep checklist (load this in Phase 1)
- `templates/manifest.md` — Bug manifest structure

</reference_index>

<success_criteria>

Shake-out is complete when:
- All automated sweep checks executed (Phase 1 Track A)
- Human reviewed manual checks (Phase 1 Track B)
- Bug manifest compiled and confirmed by human (Phase 2)
- All bugs resolved or explicitly deferred (Phase 3)
- Final re-sweep passes on previously broken areas
- Stache warmed and search index updated
- Pint clean
- Manifest file updated with final status
- `verification-before-completion` invoked and passing
- `finishing-a-development-branch` invoked

</success_criteria>
