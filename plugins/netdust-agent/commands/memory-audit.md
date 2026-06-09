---
description: Audit memory/STATE.md, memory/lessons.md, and tasks/todo.md for staleness. Report-only — never auto-edits the three files. Surfaces stale references, contradictions, completed-but-unchecked items, and untouched-since dates. Run on-demand when memory feels out of sync; no recommended cadence.
allowed_tools: ["Bash", "Read", "Write", "Glob", "Grep"]
---

Run the **memory audit**. The three files this command checks (`memory/STATE.md`, `memory/lessons.md`, `tasks/todo.md`) are the project's living state — they only stay useful if they evolve as the work evolves. This command finds where they've drifted.

Boundary:
- `/integration` audits whether the code works.
- `/evaluate` audits how a sub-phase was executed.
- **`/memory-audit` audits whether the project's memory files reflect current reality.**

This command **never** auto-edits the three files. It produces a findings report at `tasks/memory-audit-${DATE}.md` for the human to triage.

## What this command does, in one line

> Read STATE/lessons/todo, cross-reference against the live filesystem + git log, write a findings report listing every detectable drift, file by file.

## Step 1 — Confirm the three files exist

If any of the three is missing, this command isn't applicable — abort and tell the user:

```
/memory-audit requires:
  - memory/STATE.md      <found | MISSING>
  - memory/lessons.md    <found | MISSING>
  - tasks/todo.md        <found | MISSING>

If a file is missing because the project doesn't use that convention, that's
fine — but this command can't audit what isn't there. Skip the missing-file
checks or initialize the file via the project's normal flow.
```

Continue with whichever files DO exist; report only on those.

## Step 2 — Gather context the audit needs

1. **Current branch + most-recent commit**: `git rev-parse --abbrev-ref HEAD` and `git log -1 --format='%H|%aI|%s'`.
2. **Recent commit list** (last 50 commits, for cross-referencing claims in STATE/lessons/todo against actual work):
   `git log -50 --format='%H|%aI|%s'`.
3. **File mtimes** for the three files:
   `stat -c '%Y %n' memory/STATE.md memory/lessons.md tasks/todo.md` (or `stat -f '%m %N'` on macOS — detect).
4. **Most recent commit that touched each of the three files**:
   `git log -1 --format='%H %aI' -- <file>` per file.

Cache these — every audit step references them.

## Step 3 — Audit `memory/STATE.md`

Read the file. Apply these checks:

1. **mtime vs. branch activity.** If `STATE.md` has not been modified for >5 commits since its last edit on the branch, flag as STALE_MTIME: "STATE.md last modified at commit X, but Y commits have landed since." Cite the commit SHAs.

2. **Branch reference.** Find any line that references a branch name (e.g. `phase-3/agent-runner`). Compare against `git rev-parse --abbrev-ref HEAD`. Mismatch = STALE_BRANCH.

3. **Commit SHA references.** Find any `[0-9a-f]{7,40}` patterns in the file. For each: run `git rev-parse --verify <sha> 2>/dev/null`. If it exists but is no longer reachable from HEAD (e.g. on a branch that's been merged + deleted), flag as ORPHAN_SHA. If it doesn't exist at all, flag as BROKEN_SHA.

4. **"Currently working on" / "Active task" patterns.** Grep for lines matching: `currently|active|in[- ]progress|working on|next:`. For each match, check whether the named task/sub-phase/file has been shipped (look for a commit message containing the task ID). If shipped, flag as COMPLETED_BUT_STATED_ACTIVE.

5. **File-path references.** Find any `[a-zA-Z0-9_/-]+\.(ts|tsx|md|sql|json|sh)` patterns. For each, check `test -e <path>`. Missing file = BROKEN_PATH.

6. **Test-count claims.** Grep for `\d+\s*(pass|tests?|server|web|shared)`. If the claim is more than 5 commits old AND the suite has changed since, flag as STALE_TEST_COUNT (note: don't run the test suite here — too expensive; just compare against test-count claims in recent commit messages).

7. **"Open threads" / "Open questions" sections.** For each bullet, search recent commits' messages and file diffs for resolution signals (e.g. a commit message containing the same keyword phrase). If matched, flag as POSSIBLY_RESOLVED.

## Step 4 — Audit `memory/lessons.md`

Read the file. The expected format is per-entry headers (`## YYYY-MM-DD — <title>`). Apply these checks:

1. **Duplicate-topic detection.** For each entry, extract the topic (the part of the title after `—`). Compare topic strings pairwise with simple normalization (lowercase, strip punctuation). Pairs with high overlap → flag as POSSIBLE_DUPLICATE.

2. **Superseded entries.** Find entries whose body contains "SUPERSEDED" or "REPLACED BY" or "outdated by" (case-insensitive). The README says these should be deleted, but enforcement is manual. Flag as SHOULD_DELETE.

3. **Stale-by-date.** Find entries dated >180 days ago. For each, check whether any commit in the last 30 days references the same topic (via keyword match in commit messages). If no recent reference, flag as STALE_BY_DATE. (This is a weak signal — old lessons can still be valid. Surface as low-confidence.)

4. **Broken references.** Same as STATE.md check #5: file-path patterns that don't resolve = BROKEN_PATH.

5. **References to skills or commands that no longer exist.** Find patterns like `superpowers:<name>` or `netdust-*:<name>` or `Skill("<name>")`. For each, check whether the skill/command file exists under `~/.claude/plugins/*/skills/<name>/SKILL.md` or `~/.claude/plugins/*/commands/<name>.md` or `~/.claude/skills/<name>/SKILL.md`. Missing = MISSING_SKILL_REF.

6. **Conflicting rules.** Pairs of entries whose `**Rule:**` lines contradict each other (e.g. one says "always do X" and another says "never do X"). Hard to detect mechanically — surface entries with matching topic + opposing keywords ("always" vs "never", "must" vs "must not"). Flag as POSSIBLE_CONFLICT, low-confidence.

## Step 5 — Audit `tasks/todo.md`

Read the file. Expected format is markdown checkboxes (`- [ ]` and `- [x]`). Apply these checks:

1. **Unchecked items that look completed.** For each `- [ ]` line, extract task-identifier-like substrings (e.g. `A-3`, `Phase 2.5`, `BUG-007`, `task 3`). Search the last 50 commit messages for the same identifier in a "shipped" context (commits whose subject matches `phase-N: ... \(A-3\)` or similar). If matched, flag as PROBABLY_SHIPPED.

2. **Checked items referencing missing files.** For each `- [x]` line that mentions a file path, check `test -e <path>`. Missing = ORPHANED_DONE.

3. **mtime vs. branch activity.** Same as STATE check #1. If todo.md hasn't been touched in >10 commits, flag as STALE_MTIME (more lenient threshold than STATE because todo is more granular).

4. **Headings referencing wrong phase.** Grep for "Phase N" patterns. Compare against the most recent phase referenced in `docs/PHASES.md` (if exists) or the most recent `phase-N:` commit prefix in the last 50 commits. Mismatch = WRONG_PHASE_HEADING.

5. **Items older than the file's introduction.** This is harder — skip unless the file is fully version-controlled with mature history. Defer.

## Step 6 — Synthesize findings + severity

Each finding gets a severity:

- **HIGH** — references something that has demonstrably moved or vanished. The file is actively misleading.
  Examples: BROKEN_SHA, BROKEN_PATH, MISSING_SKILL_REF, COMPLETED_BUT_STATED_ACTIVE, PROBABLY_SHIPPED on an unchecked todo, STALE_BRANCH.

- **MEDIUM** — drift is plausible but not proven. Human should check.
  Examples: ORPHAN_SHA, POSSIBLY_RESOLVED, POSSIBLE_DUPLICATE, WRONG_PHASE_HEADING, ORPHANED_DONE.

- **LOW** — soft signal. Probably worth knowing, probably doesn't need action.
  Examples: STALE_MTIME, STALE_BY_DATE, STALE_TEST_COUNT, POSSIBLE_CONFLICT.

Count findings per severity per file.

## Step 7 — Write the report

Write `tasks/memory-audit-${DATE}.md` (where ${DATE} is today, YYYY-MM-DD). Overwrite if a previous run wrote it today.

```markdown
# Memory audit — ${DATE}

**Branch:** ${BRANCH} (at ${HEAD_SHA_SHORT})
**Audited files:** memory/STATE.md, memory/lessons.md, tasks/todo.md
**Findings:** ${TOTAL} (${HIGH_COUNT} high, ${MEDIUM_COUNT} medium, ${LOW_COUNT} low)

---

## memory/STATE.md

**Last modified:** ${STATE_MTIME} (commit ${STATE_LAST_COMMIT})
**Commits since last edit:** ${N}

[For each finding:]

### ⚠ ${SEVERITY}: ${CHECK_NAME}

**Where:** line ${LINE}: `${EXCERPT}`
**Why flagged:** ${REASON}
**Evidence:** ${EVIDENCE} (e.g. "commit `13c76d8` shipped A-2 but STATE.md still lists it as in-progress")
**Suggested action:** ${ACTION}

---

## memory/lessons.md

**Last modified:** ${LESSONS_MTIME} (commit ${LESSONS_LAST_COMMIT})
**Total entries:** ${N}
**Commits since last edit:** ${N}

[For each finding, same shape as above]

---

## tasks/todo.md

[Same shape]

---

## Summary

[Bullet list, prioritized HIGH → MEDIUM → LOW:]

1. **HIGH** [STATE]: <one-line>
2. **HIGH** [todo]: <one-line>
3. **MEDIUM** [lessons]: <one-line>
...

[End with the recommended action sentence:]

Recommended next step: review HIGH findings first. Each high-severity finding
is a place where a memory file is actively misleading a future session. Apply
edits in the file, then re-run /memory-audit to confirm clean. The audit
report itself (this file) is NOT committed by default — review, edit the
three files, then either commit the cleaned files or delete this report.

[If no findings at all:]

All three files are in sync with the current branch state. No drift detected.
```

## Step 8 — Report to user

Final message (under 150 words):

```
## /memory-audit — ${DATE}

Report: ${REPORT_PATH}
Findings: ${TOTAL} (${HIGH_COUNT} high · ${MEDIUM_COUNT} medium · ${LOW_COUNT} low)

[Top 3 highest-severity findings, one line each:]
- HIGH [STATE.md:42]: STATE references shipped task A-2 as "currently working on" (commit 13c76d8 shipped it 2 days ago)
- HIGH [todo.md:18]: unchecked "[ ] A-4: agent_run schema" but commit 02c4564 shipped it
- MEDIUM [lessons.md:309]: possible duplicate of lesson at line 245

This report is NOT committed. Review the three files, apply edits, then
either commit your cleanups or delete the report. Re-run /memory-audit to
confirm clean.
```

## What this command is NOT

- NOT a code review — `/code-review` does that.
- NOT a correctness gate — `/integration` does that.
- NOT a process retro — `/evaluate` does that.
- NOT an auto-cleaner — never edits the three files. The human applies the changes.

## When NOT to run it

- Right after `/evaluate` ran (which already updated memory). Wait at least one substantive commit before re-running.
- On a freshly-initialized project with empty STATE/lessons/todo. The command needs content to audit.
- In the middle of a sub-phase. Findings will include "tasks in-progress that look shipped" because the in-progress markers can't be distinguished from staleness mid-stream. Run at sub-phase close or later.

## Limitations to surface honestly in the report

- **Keyword-match heuristics produce false positives.** A "possibly resolved" open thread might not actually be resolved; a "probably shipped" todo might just share a name with a different commit. The report's job is to surface candidates, not adjudicate.
- **STALE_BY_DATE is a weak signal.** Lessons from months ago can still be load-bearing. A LOW severity flag means "worth a glance," not "delete."
- **Cross-file references aren't checked.** STATE.md saying "see lessons.md entry X" isn't verified.
- **Auto-memory files (under `~/.claude/projects/<encoded-cwd>/memory/`) are NOT audited.** They're per-session, not per-branch — they'll always look stale by some metric, and that's not what this command is for. Stay focused on the three project-local files.
