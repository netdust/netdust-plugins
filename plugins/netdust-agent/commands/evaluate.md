---
description: Process retrospective — audits HOW a sub-phase was executed, not WHETHER the code works. Reconstructs from git + plan + memory. Emits a markdown retro, commits plan corrections for defects discovered, appends lessons to skill + project memory. Runs at sub-phase close, after /integration passes.
allowed_tools: ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
---

Run the **process retrospective**. This is the discipline-side companion to `/integration` — `/integration` proves the work works; `/evaluate` proves the harness worked while doing it.

Boundary:
- `/integration` is fired at sub-phase close to verify correctness.
- `/evaluate` is fired immediately AFTER `/integration` passes, BEFORE moving to the next sub-phase. It looks backward at the sub-phase that just shipped.
- For the spec-complete equivalent, the future `/evaluate-phase` would roll up all sub-phase retros at branch close. (Not built yet — defer until we have 3+ sub-phase retros to roll up.)

## What this command does, in one line

> Reconstruct from git artifacts how the just-finished sub-phase was actually executed, score the harness against its own discipline, commit defect corrections back to the plan, write the lessons into skill memory.

## Step 1 — Scope the work

The sub-phase that just finished is the commit range `<last-evaluate-sha>..HEAD` filtered to actual implementation commits (excluding pure memory/STATE/handoff commits).

1. Read `.claude/.last-evaluate` from the repo root. It contains the SHA captured at the end of the previous `/evaluate` run.
2. If missing → use the range `$(git merge-base HEAD main)..HEAD` (entire branch). Note in the report that this is the FIRST evaluation on this branch.
3. Capture `git rev-parse HEAD` into `NEW_SHA`.
4. Identify the sub-phase letter by reading the plan file. Find the most recent active plan at `docs/superpowers/plans/*.md` (most recent mtime). Search it for the phase pattern (e.g. `Sub-phase A`, `Sub-phase B`). Cross-reference against commit messages in the range — most commit messages will have a `(<task-id>)` suffix like `(A-3)` that names the sub-phase letter.
5. Set:
   - `PHASE` (e.g. `phase-3`)
   - `SUB_PHASE` (e.g. `A`, or `unspecified` if commits don't carry task IDs)
   - `DATE` (today, YYYY-MM-DD)
   - `RETRO_PATH = docs/superpowers/retros/${DATE}-${PHASE}-sub-phase-${SUB_PHASE}-retro.md`

If the retro file already exists, abort with: "Retro already exists at <path>. Delete or rename before re-running."

## Step 2 — Pull evidence from git

For the commit range, capture:

1. **Commit list** with timestamps and messages:
   `git log --format='%H|%aI|%s' <RANGE>` → parse into structured rows.

2. **Per-commit stats** (files + insertions + deletions):
   `git log --format='%H' <RANGE> | xargs -I{} git show --stat {} | ...`
   Or use `git log --stat <RANGE>` and parse.

3. **Per-commit file lists**:
   `git diff --name-only <prev>..<commit>` for each commit.

4. **Test count deltas from commit messages**. Look for the pattern `\d+\s*->\s*\d+` in each commit message body (the convention is `Test count: 526 -> 530 server (+4)`). Capture before/after numbers per commit.

5. **Migration commits**: any commit touching `apps/server/src/db/migrations/*.sql`. Cross-check that the same commit also touched `meta/_journal.json` (per `[[drizzle-migration-journal]]`).

6. **Commit classification** by message prefix:
   - `phase-N:` (implementation)
   - `phase-N: BUG-*` (shake-out fix)
   - `phase-N: <letter><digit>` like F1, G14, H22 (review-fix pass)
   - `phase-N: plan` or `plan correction` (meta-work on the plan)
   - `memory(*)` (auto-memory, skip in classification but note count)
   - `fix:` / `chore:` / `docs:` (per-CLAUDE.md convention)

## Step 3 — Compute timing

1. **Session boundaries**: any gap > 90 minutes between commits = session break. Group commits into sessions.
2. **Per-session metrics**: span (first→last commit), commit count, average gap.
3. **Total active dev time**: sum of session spans. NOT calendar time.
4. **Per-commit min/avg/max**.
5. **Cleanup ratio**: (BUG-* + letter-prefix-fix commits) / total implementer commits. Plan-correction commits are excluded from the numerator AND the denominator — they are audit-side meta-work, not implementer cleanup, and counting them inflates the implementer's apparent cleanup rate. Report as percentage.
6. **First-commit cold-start tax**: time between branch HEAD-at-start-of-session and first commit. If the first session is the first session of the sub-phase, this is the warm-up tax.

## Step 4 — Cross-reference plan vs. shipped

For each task in the sub-phase (read the plan, find the `### Task <letter>-<N>` headings):

1. **Locate the shipping commit**. Match commit message against task ID (e.g. `(A-2)` matches `Task A-2`).
2. **Read the plan's task body** (Steps + expected files + expected commit shape).
3. **Read the shipped diff** for the matched commit. Compare:
   - Files touched: matches plan's `Files:` block?
   - Test count delta: matches plan's "Expected: ~N tests"?
   - Commit message body: does it mention divergences explicitly?
4. **Classify each task as one of**:
   - `MATCHED` — shipped exactly as planned
   - `DIVERGED_DEFECT` — plan was wrong, commit message documents the correction
   - `DIVERGED_SCOPE` — plan was right but shipped extra/less
   - `MISSING` — task is in the plan but no commit found

For each `DIVERGED_DEFECT`, capture:
   - Defect description (from commit message body or by reading the diff)
   - Shipping commit SHA
   - Plan line(s) that need a correction callout

## Step 5 — Audit discipline gates

For each implementation commit, check:

1. **Test-count delta in message**: present (Y/N).
2. **Migration discipline**: if touches `*.sql`, also touches `_journal.json` (Y/N).
3. **Test:code file ratio**: count `*.test.*` files vs. non-test files touched. Flag any code-touching commit with zero test files (excluding pure docs/SQL-only).
4. **DONE_WITH_CONCERNS markers**: scan commit messages for "concerns" or "divergences" — these were honestly flagged at commit time.
5. **Reviewer-fix commits chained to a primary commit**: are F/G/H/BUG commits explicitly linked to the primary task they remediate? (Look for `(<task-id>)` references inside the fix commit message body.)

Produce a discipline-compliance summary table per commit.

## Step 6 — Identify harness gaps

Harder to detect from git alone; here are the heuristics:

1. **Plan defects that shipped via DIVERGED_DEFECT classification**: each one is a case where the harness did NOT catch the defect at plan-write time. That's a planning-skill gap candidate.
2. **Migration commits without journal updates** (pre-A-4b only — A-4b shipped the hook): structural gap that A-4b's hook now closes. Note as resolved.
3. **Test-count regressions or stagnation**: any sub-phase where test count went down or stayed flat across multiple commits is a discipline gap.
4. **Cleanup-ratio > 40%**: signals plan or review discipline issues — too many bugs slipping past the per-task gates.
5. **First-commit cold-start tax > 30 min**: signals harness-warmup overhead worth investigating (could be a startup-skill or memory-loading gap).
6. **No commits referencing `Skill("testing-workflow")` in their bodies**: signals the subagent invocation discipline isn't working. (Won't always be detectable since the Skill invocation lives in transcripts, not commits. Flag as "unable to verify from git alone — investigate in next session.")

**Each gap MUST declare its own resolution disposition.** Use one of:

- **SHOULD_FIX** — gap has a concrete remediation that should land before the next sub-phase starts. Goes in §Recommendations as an action item. Auto-actionable: the retro itself (or a follow-up commit) ships the fix.
- **MONITOR** — gap is real but discipline held by other means, OR sample size too small to act yet. Goes in §Harness gaps only, NOT in §Recommendations and NOT in §Follow-ups. Re-evaluated at the next /evaluate run.
- **HUMAN_DECISION** — gap involves a tradeoff the retro can't unilaterally decide (e.g., "drop a reviewer stage given low blocker rate"). Goes in §Follow-ups for human review AND `tasks/retro-follow-ups.md`, NOT in §Recommendations.

**A gap MUST appear in exactly one of those three destinations — never two.** If the retro flags the same finding as both a recommendation (auto-actionable) and a follow-up (human decision), one of the two is wrong. Pick one.

## Step 7 — Write the retro

Write `${RETRO_PATH}` with this structure verbatim:

```markdown
# Retro — ${PHASE} Sub-phase ${SUB_PHASE}

**Date:** ${DATE}
**Commit range:** ${RANGE}
**Total commits:** ${N}
**Active dev time:** ${HOURS} hours across ${SESSIONS} session(s)

## Timing

[Table: per-session breakdown — span, commits, avg gap, dominant work type]

[Per-commit stats — min/avg/max, distribution]

[Cleanup ratio: X% of commits were BUG-*/F/G/H/plan-correction]

[First-commit cold-start tax: ${MINUTES}]

## Plan vs. shipped

[Per-task table:]
| Task | Plan vs shipped | Notes |
|---|---|---|
| ${PHASE}-${SUB_PHASE}-N | MATCHED \| DIVERGED_DEFECT \| DIVERGED_SCOPE \| MISSING | … |

[For each DIVERGED_DEFECT, a paragraph with defect description, shipping commit, and the plan-correction callout that will land.]

## Discipline compliance

[Table per commit:]
| Commit | Test delta in msg | Migration+journal paired | Test:code ratio | DONE_WITH_CONCERNS |
|---|---|---|---|---|

[Cleanup-commit chaining: which BUG/F/G/H commits link back to which primary task]

## Harness gaps identified

[Numbered list of gaps. Each MUST declare a disposition: SHOULD_FIX | MONITOR | HUMAN_DECISION. See Step 6 of the command spec.]

1. **<Gap name>** — <evidence>. **Disposition:** SHOULD_FIX | MONITOR | HUMAN_DECISION. **Remediation:** <concrete change to a skill / hook / plan template — only if SHOULD_FIX>.

## Recommendations

[Only gaps with disposition SHOULD_FIX go here. If a gap is MONITOR or HUMAN_DECISION, it does NOT appear in this section.]

1. **Action:** … **Why:** … **Cost:** …

## Follow-ups for human review

[Only gaps with disposition HUMAN_DECISION go here. Also written to tasks/retro-follow-ups.md per Step 10.]

[If zero HUMAN_DECISION gaps: write the literal sentence "No human-decision items this sub-phase." Do not omit the section.]

## Memory updates

[Mandatory section. List every memory file modified, with line counts. See Step 9.]

[If zero memory writes: write the literal sentence "No memory updates this sub-phase." Do not omit the section.]
```

## Step 8 — Auto-commit plan corrections

For each `DIVERGED_DEFECT` from Step 4:

1. Open the plan file at `docs/superpowers/plans/*.md` (most recent active plan).
2. Locate the task's section in the plan.
3. Locate the specific lines/code-block that diverged (the broken SQL, the broken test pattern, etc.).
4. Insert a callout block ABOVE the broken section using this exact shape (matches the `a9b3ae8` pattern):

```
> **⚠ Plan defect noted during <PHASE>-${SUB_PHASE} execution (shipped fix in `<sha>`):**
> <One-sentence description of what the plan got wrong.>
> <One-sentence description of how the shipped artifact fixes it.>
> Refer to commit `<sha>` for the actual pattern; the block below is preserved as historical context but should not be copied.
```

5. Stage and commit each correction in a SEPARATE commit (one commit per defect, for clean audit trail). Commit message:

```
phase-N: plan correction — <defect short name> (post-${SUB_PHASE} retro)

<Two-line description of what was wrong + what shipped.>

Surfaced by ${RETRO_PATH}. Original shipping commit: <sha>.
```

If multiple defects, multiple commits. Do NOT batch them — atomic per defect.

## Step 9 — Write lessons to memory

For each significant finding, decide which memory file gets the entry:

1. **Project memory** (`memory/lessons.md` in the repo, if exists; else create) — for findings specific to this codebase/team/conventions. Format per the existing project memory convention.

2. **Skill lessons** — append to the relevant skill's `lessons.md`. For example:
   - If the retro found that `testing-workflow` wasn't invoked → append to `~/.claude/plugins/netdust-agent/skills/testing-workflow/lessons.md`
   - If a plan-writing pattern keeps producing defects → append to the relevant brainstorming/writing-plans skill's lessons
   - If a hook fired silently → append to the hook's plugin lessons

Skill-lessons entries use this shape:

```
### ${DATE} — <short trigger>
- Source: ${PHASE} sub-phase ${SUB_PHASE}
- Observation: <what happened>
- Recommendation: <what the skill should say or check that it doesn't today>
- Severity: low | medium | high (high = blocks future runs if unaddressed)
```

3. **Project auto-memory** (`~/.claude/projects/<encoded-cwd>/memory/`) — for findings that should auto-load into future sessions. Write a new `project_retro_<PHASE>-${SUB_PHASE}.md` entry using the standard auto-memory schema.

DO NOT write the same finding to multiple memory files. Pick the most specific scope.

**The retro's "Memory updates" section in Step 7 MUST list every file modified by this step, with line counts.** Example:

```
## Memory updates

- `+12 lines` to ~/.claude/plugins/netdust-agent/skills/testing-workflow/lessons.md (skill-invocation gap entry)
- `+8 lines` to ~/.claude/projects/-home-ntdst-Projects-folio/memory/feedback_drizzle-migrate-is-idempotent.md (new project auto-memory)
- `+6 lines` to memory/lessons.md (project-local: workspaces.test.ts assertion drift on builtin flips)
```

If the section is empty, the retro found nothing worth memory — that's a valid signal too, but the empty section must be PRESENT in the retro, not omitted. Empty = audited and found nothing; missing = step skipped.

## Step 10 — Write follow-ups for human review

**Mandatory file write.** For every gap classified `HUMAN_DECISION` in Step 6, append a bullet to `tasks/retro-follow-ups.md` (create if missing). This file is the input to the next planning session — without it, the inline "Follow-ups for human review" section in the retro will not be re-read.

Each bullet contains:

- The finding (1 sentence)
- The decision the human needs to make (1 sentence with YES/NO framing)
- The skill or file that would change if the decision is YES (concrete path)
- Link back to the retro: `(surfaced by ${RETRO_PATH})`

If Step 6 classified zero gaps as `HUMAN_DECISION`, write nothing to this file. But the retro's §Follow-ups section MUST then explicitly say "No human-decision items this sub-phase." — empty is a valid result; missing is a skipped step.

**Failure mode the wording above closes:** the first `/evaluate` run wrote follow-ups inline in the retro but did NOT create `tasks/retro-follow-ups.md`. The inline section was unreachable by future sessions. Both writes are required.

## Step 11 — Stamp + commit the retro

This step has three sub-steps, all REQUIRED. If any fails or is skipped, the retro is incomplete and the next /evaluate will misbehave.

1. **Write `NEW_SHA` to `.claude/.last-evaluate`.** Create the directory + file if missing. Verify the write succeeded by reading the file back. **Without this stamp, the next /evaluate falls back to `merge-base HEAD main` and retrospects over already-evaluated commits, producing duplicate findings.**

2. `git add ${RETRO_PATH} .claude/.last-evaluate` (+ `tasks/retro-follow-ups.md` if modified).

3. Commit:
   ```
   ${PHASE}: retro — sub-phase ${SUB_PHASE} (${HOURS}h, ${N} commits, ${DEFECTS} plan defects surfaced)
   ```

**Failure mode this wording closes:** the first /evaluate run on Folio's phase-3 branch did NOT write `.claude/.last-evaluate`. Treating the stamp as optional is what allowed the skip. It is not optional.

## Step 12 — Report

Final message to the user (concise — under 200 words):

```
## /evaluate — ${PHASE} sub-phase ${SUB_PHASE}

Retro: ${RETRO_PATH}
Range: ${RANGE} (${N} commits, ${HOURS}h active)
Cleanup ratio: ${RATIO}%

Plan corrections committed: ${DEFECTS}
- <sha1>: <defect short name>
- <sha2>: <defect short name>

Memory updates: ${MEMORY_COUNT} entries written
- ${list of files updated}

Follow-ups for review: ${FOLLOWUPS} item(s) at tasks/retro-follow-ups.md

Next sub-phase ready to start? Run /integration when its tasks finish, then /evaluate again.
```

## What this command is NOT

- NOT a code review (`/code-review` does that).
- NOT a correctness gate (`/integration` does that).
- NOT a shake-out (`/shakeout` does that — but `/shakeout` is also process-aware in its own way).
- NOT a place to write new code logic. Only meta-corrections to the plan, lessons to memory, follow-ups to a task list.

## When to skip running it

- A sub-phase with fewer than 3 commits (too little signal to retrospect on).
- Pure-docs sub-phases (no implementation to evaluate).
- Hot-fix sub-phases on production branches (different discipline entirely; out of scope for v1).

In all skip cases, just don't run the command. There's no "skip" mode — the absence of a retro IS the signal that the sub-phase was too small or wrong-shape to evaluate.
