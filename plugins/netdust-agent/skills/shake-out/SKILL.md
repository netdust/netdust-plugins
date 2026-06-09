---
name: shake-out
description: Post-build QA phase that sweeps the built artifact end-to-end, compiles a bug manifest, then fixes systematically. Use after executing-plans or subagent-driven-development completes when unit tests pass but the artifact hasn't been exercised in a real environment — this is the spec-complete / pre-merge gate. Triggers on "shake it out", "shakeout", "does it work", "QA this", "find the bugs", "what's broken", "spec-complete gate", "pre-merge gate", "final QA before merge".
---

<objective>
Structured post-build phase that bridges "tests pass" and "it actually works." Exercises the built artifact in a real environment, compiles every failure into a manifest, then fixes them one at a time using systematic-debugging.

Sits between build completion and finishing-a-development-branch:

```
brainstorm → plan → execute → SHAKE-OUT → finishing-branch
```

Takes a build from ~80% done to ~90%. The remaining 10% is human judgment.
</objective>

<essential_principles>

**The Iron Law**

```
NO FIXES DURING SWEEP
```

Find a bug → LOG IT. Do not fix it. Do not "quickly adjust" it. Do not refactor around it.
Finding and fixing in the same breath is the exact behavior this skill prevents.
Violating the letter of this rule is violating the spirit of shake-out.

**Red Flags — STOP immediately if you catch yourself:**

During SWEEP:
- "Let me just fix this quick while I'm here"
- "I'll note it AND fix it, saves time"
- Modifying any source file during Phase 1
- Proposing solutions before the manifest is complete
- Fixing one bug before all bugs are found

During FIX:
- Fixing two bugs in one commit
- "While I'm in this file, I'll also..."
- Not re-sweeping after a fix
- Skipping systematic-debugging because "this one is obvious"

**ALL of these mean: STOP. You are violating protocol.**

**Common Rationalizations**

| Excuse | Reality |
|--------|---------|
| "This fix is obvious" | Obvious fixes cause cascading bugs. That's why you're reading this. |
| "I'll fix as I sweep, it's faster" | You never see the full picture. Three quick fixes later you're debugging patches. |
| "Only one bug, don't need a manifest" | One visible bug often hides three. Sweep fully. |
| "Re-sweep is overkill for a minor fix" | Minor fixes in the wrong place cause critical bugs. |
| "The tests pass, it's fine" | Tests passing is what triggered this skill. They don't cover everything. |
| "I can see the fix, no need for systematic-debugging" | That's the #1 cause of cascading patches. Invoke the skill. Every time. |
| "I'll just change this one line" | You're editing code without the debugging protocol. Stop. Invoke the skill. |

</essential_principles>

<quick_start>

Three phases, always in order:

1. **SWEEP** — Run the artifact. Find everything broken. Fix nothing.
2. **MANIFEST** — Present the complete bug list. Cluster by root cause. **Verify before fixing:** for each candidate bug, run the adversarial check in `_shared/finding-verification.md` (default N=3 votes; N=1 for a tiny sweep) so the FIX loop spends effort only on confirmed bugs and an accepted-deferral (exclusion rule 16) isn't re-opened. Get human sign-off on the confirmed list.
3. **FIX** — Work through the confirmed manifest using `systematic-debugging` per bug.

Before starting: read the plan, resolve the environment, detect project type, load the right sweep reference.

</quick_start>

<process>

**Input requirements:**
- All plan tasks marked complete
- Code committed on feature branch
- Unit tests passing
- Plan file path known (from executing-plans or subagent-driven-development)

**Step 0: Preparation**

1. Read the plan document to understand what was built — endpoints, pages, features, integrations, expected behaviors
2. Resolve the environment:
   - Read project's CLAUDE.md for site structure, WP-CLI paths, SSH patterns
   - **WordPress/DDEV local:** Use `ddev wp` (wp-cli.yml handles `--path`)
   - **WordPress remote:** Use SSH patterns from CLAUDE.md (`ploi-staging`, `combell-[site]-staging`)
   - **Node.js:** Check `package.json` for start script, identify port
   - Determine site URL, admin URL, key page URLs from project config
3. Detect project type and load ONE sweep reference:

| Signal | Load |
|--------|------|
| `composer.json` with WP deps, `wp-config.php`, `.ddev/` | `references/sweep-wordpress.md` |
| `package.json` with Node/Bun entry, no WordPress | `references/sweep-node.md` |
| Neither | `references/sweep-generic.md` |

4. **Detect test framework** — check if Codeception/wp-browser is available:

```bash
# Check for Codeception
test -f codeception.yml && echo "CODECEPTION AVAILABLE" || echo "NO CODECEPTION"
# Check for wp-browser
composer show lucatume/wp-browser 2>/dev/null && echo "WP-BROWSER AVAILABLE"
# Check for Selenium
test -f .ddev/docker-compose.selenium*.yaml && echo "SELENIUM AVAILABLE"
```

If Codeception is available: run existing test suites FIRST (see sweep reference), then do exploratory checks for what tests don't cover. If not available: full manual sweep using the pattern library.

**Phase 1: SWEEP**

Two tracks, in sequence.

*Track A — Automated (Claude runs):*

Follow the loaded sweep reference checklist. The pattern is always:

1. **Smoke test** — Does it start? Does it respond? Is the process alive?
2. **Happy path** — Walk through the primary use case end-to-end
3. **Integration points** — Every boundary where this code talks to something else
4. **Configuration** — Env vars, API keys, file paths, permissions
5. **Error handling** — Bad input, missing data, auth failure

Available tools:

| Tool | What it checks |
|------|----------------|
| `chrome-devtools` MCP | Pages load, JS errors, forms work, elements render, screenshots |
| WP-CLI (`ddev wp` / SSH) | Plugin state, options, cron, transients, database |
| `curl` / HTTP | Status codes, headers, REST API, redirects |
| CLI execution | Scripts run, exit codes, stdout/stderr |
| Log scanning (Read tool) | PHP errors, debug.log, application logs |
| File system (Glob/Read) | Permissions, config files, output files |
| Database queries | Tables exist, data integrity |

For each check, record:
- What was tested
- What was expected
- What actually happened
- Severity: **CRITICAL** / **IMPORTANT** / **MINOR**

*Track B — Manual (human runs):*

After Track A, generate a focused checklist specific to what was built. NOT a generic QA list.

```
## Manual Checks Needed

These need a browser/device. Report what you find — I'll add to the manifest.

1. [ ] Open [URL] — does the layout render correctly?
2. [ ] Check [specific visual element] on mobile
3. [ ] Click through [specific flow] — does it feel right?
4. [ ] Try [edge case needing human judgment]
```

5-10 items max. Only things Claude genuinely cannot verify.

**Wait for human to report back before proceeding to Phase 2.**

**Phase 2: MANIFEST**

After both tracks complete:

1. Write manifest to `tasks/shake-out-manifest.md` using `templates/manifest.md`
2. Cluster bugs by suspected root cause — multiple symptoms that likely share one fix
3. Assign severity:

| Severity | Meaning | Example |
|----------|---------|---------|
| **CRITICAL** | Doesn't work at all, data loss, security | 500 error, form loses data, auth bypass |
| **IMPORTANT** | Works but with significant problems | Wrong data, broken flow, missing validation |
| **MINOR** | Cosmetic, non-blocking, edge case | Styling off, console warning, slow |

4. Present manifest to human. Ask:
   - "Anything missing from what you observed?"
   - "Do the clusters make sense?"
   - "Agree with priority order?"

**Do not proceed to Phase 3 until human confirms the manifest.**

If manifest is empty (zero bugs): skip Phase 3, proceed to Completion.

**Phase 3: FIX**

Work through the manifest: all CRITICAL first, then IMPORTANT, then MINOR.

```
MANDATORY: Every bug MUST be fixed via Skill("superpowers:systematic-debugging").
Do NOT fix bugs inline. Do NOT "just change this one line."
If you are editing code without having invoked the skill, you are violating protocol.
```

For each bug (or cluster):

1. **Use the Skill tool to invoke `superpowers:systematic-debugging`.**
   This is a hard gate — not a suggestion. Call `Skill("superpowers:systematic-debugging")` with the bug details from the manifest as context. The skill enforces:
   - Phase 1: Root cause investigation (read errors, reproduce, trace)
   - Phase 2: Pattern analysis (find working examples, compare)
   - Phase 3: Hypothesis and testing (one hypothesis, smallest change)
   - Phase 4: Implementation (failing test first, single fix, verify)

   **If you skip this step, any fix you write is unauthorized and likely wrong.**

   **Failing test requirement:** When Codeception/wp-browser is available, the "failing test first" in Phase 4 MUST be a proper Codeception test — not a throwaway assertion. Place it in the project's existing test structure (`tests/acceptance/`, `tests/frontend/`, etc.). This grows the regression suite with every shake-out.

   When Codeception is NOT available, use the testing approach from `testing-workflow` (PHPUnit or inline verification).

2. **Re-sweep the affected area** — If Codeception tests exist for this area, run them: `ddev exec vendor/bin/codecept run acceptance [TestCest]`. Otherwise re-run the specific sweep check that found this bug. Did the fix resolve it *in the real environment*?

3. **Check for collateral** — Run the full relevant test suite if available (`ddev exec vendor/bin/codecept run`). Otherwise quick targeted re-sweep of related areas.

4. **Update `tasks/shake-out-manifest.md`** — Mark resolved with root cause notes. If new bugs surfaced, add them.

5. **If 3+ fix attempts fail on the same bug:** STOP. Present to human with options:
   - Continue trying (different approach)
   - Defer this bug
   - **Abort shake-out → return to planning** (see `<abort_and_replan>`)

Fix rules:
- **SYSTEMATIC-DEBUGGING PER BUG. NO EXCEPTIONS.** Not even "obvious" ones.
- **ONE bug at a time.** No batch fixes.
- **Cluster bugs fix once.** Fix the root cause, verify all cluster symptoms resolve.
- **No "while I'm here" improvements.** Fix the bug. Only the bug.
- **Don't remove bugs from manifest.** Mark resolved with notes. The manifest is the record.
- **Re-sweep after every CRITICAL fix.** Full subsystem re-sweep, not just the specific bug.

**Completion**

When all bugs are resolved or explicitly deferred by the human:

1. Run abbreviated final sweep — focus on previously broken areas
2. Update manifest with final status
3. Present to human: "All [N] resolved. [N] deferred. Here's what changed."
4. Invoke `superpowers:verification-before-completion`
5. Invoke `superpowers:finishing-a-development-branch`

</process>

<abort_and_replan>

If shake-out reveals the implementation approach is fundamentally wrong — not just bugs, but wrong architecture — offer these options:

1. **Continue fixing** — The bugs are fixable within current architecture
2. **Defer and ship** — Known issues, ship with caveats
3. **Abort → re-plan** — Architecture is wrong. Return to brainstorming with lessons learned.

Option 3 writes `tasks/shake-out-abort-context.md` with:
- What was built
- What failed and why
- Architectural insight gained
- Recommendation for the re-plan

Then invoke `superpowers:brainstorming` with this file as context input.

</abort_and_replan>

<integration>

**Pipeline position:**
```
brainstorm → plan → execute → SHAKE-OUT → finishing-branch
```

| Skill | Relationship |
|-------|-------------|
| `executing-plans` / `subagent-driven-development` | **UPSTREAM.** Shake-out runs after these complete. |
| `superpowers:systematic-debugging` | **REQUIRED.** Invoked per bug during Phase 3. |
| `superpowers:verification-before-completion` | **REQUIRED.** Invoked before declaring done. |
| `superpowers:finishing-a-development-branch` | **DOWNSTREAM.** Invoked after shake-out passes. |
| `chrome-devtools` MCP | **REQUIRED for web projects.** Browser-level verification in Phase 1. |

**Trigger phrases:**
- "shake it out" / "shake-out" / "shakeout"
- "does it actually work" / "QA this" / "check everything"
- "find the bugs" / "what's broken" / "bug hunt"
- "it doesn't work" (when said after a build, not mid-build)

**Do NOT use when:**
- Mid-build debugging (use `systematic-debugging` directly)
- Writing new features (use TDD)
- The project hasn't been built yet

</integration>

<reference_index>

**Sweep playbooks** (load ONE based on project type):
- `references/sweep-wordpress.md` — WordPress / Bedrock / DDEV sweep checklist
- `references/sweep-node.md` — Node.js / Bun sweep checklist
- `references/sweep-generic.md` — HTTP, filesystem, process, log checks

**Templates:**
- `templates/manifest.md` — Bug manifest structure

</reference_index>

<success_criteria>

Shake-out is complete when:
- All automated sweep checks executed (Phase 1 Track A)
- Human reviewed manual checks (Phase 1 Track B)
- Bug manifest compiled and confirmed by human (Phase 2)
- All bugs resolved or explicitly deferred (Phase 3)
- Final re-sweep passes on previously broken areas
- Manifest file updated with final status
- `verification-before-completion` invoked and passing
- `finishing-a-development-branch` invoked

</success_criteria>
