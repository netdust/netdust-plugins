---
description: Audit memory/STATE.md, memory/lessons.md, and tasks/todo.md for staleness, and (with --apply) ARCHIVE the historical bloat to memory/ARCHIVE.md so the snapshot stays lean. Default run is dry — it shows the proposed archive diff and the findings report, and writes nothing. `/memory-audit --apply` performs the archive after you've seen the diff. Run on-demand when memory feels out of sync or STATE.md is over budget.
allowed_tools: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
---

Run the **memory audit**. The three files this command checks (`memory/STATE.md`, `memory/lessons.md`, `tasks/todo.md`) are the project's living state — they only stay useful if they evolve as the work evolves. This command finds where they've drifted AND, on `--apply`, prunes the historical bloat into `memory/ARCHIVE.md`.

Boundary:
- `/integration` audits whether the code works.
- `/evaluate` audits how a sub-phase was executed.
- **`/memory-audit` audits whether the project's memory files reflect current reality — and prunes them so they keep loading under the session-start budget.**

## Modes (read this FIRST)

This command has two modes, selected by the presence of `--apply` in the arguments (`$ARGUMENTS`):

- **DRY-RUN (default, no `--apply`)** — run the staleness audit (Steps 1–8 below) AND compute the proposed archive (Step A1–A4). Show the user the full proposed diff and the projected sizes. **Write NOTHING to STATE.md / lessons.md / ARCHIVE.md.** End by telling the user to re-run with `--apply` to perform it.
- **APPLY (`--apply` present)** — re-compute the archive plan and PERFORM it: append to `memory/ARCHIVE.md`, rewrite `memory/STATE.md` and `memory/lessons.md` to the pruned snapshot. Then print the before/after sizes and confirm the result is under budget.

The staleness findings report (Steps 1–8) is always written to `tasks/memory-audit-${DATE}.md` (it's a report, not one of the three living files). The ARCHIVE behavior (Steps A1–A4) is what `--apply` gates.

**Hard safety rule:** in APPLY mode, you MUST have shown the diff in a prior dry-run OR show it inline immediately before writing. Never write the pruned STATE.md without the user having seen what moves out. When in doubt, stay in dry-run and ask.

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

## Step A1 — Classify every STATE.md section as KEEP or ARCHIVE

Read `memory/STATE.md`. Today's date is `${DATE}`. Split the file into sections at `##` / `###` headers (content before the first header is the *preamble*). Classify each section (and the preamble) as **KEEP** or **ARCHIVE**:

Classification is **whitelist-driven**: a small, named set of sections is the live snapshot and is KEPT; everything else is historical and is ARCHIVED. This is deliberate — a "keep unless it looks old" rule fails on dated narrative blobs that describe shipped work but carry a recent date (e.g. a `## [2026-06-09] 🚢 ... MERGED + PUSHED` write-up is *history*, not current state, even though it's dated today). Recency does NOT protect a section; being a current-state section does.

**KEEP** — only these section classes:
- The **snapshot whitelist** (match on header keywords, case-insensitive): `current branch`, `phase` (the current-phase status section, NOT "Phase N commit list"), `what's working`, `what's not built`, `open threads` / `open questions`, `where things live`, `servers`, `live tests`, `next up`, `open ... issue` (an active UX/bug note), `deferrals` (intentional, still-pending). These describe the project's *present* — keep regardless of any date in them.
- **Tagged-capture** blocks (`### YYYY-MM-DD — tagged capture`) dated **within the last 14 days** of `${DATE}`.
- Any section that **describes work not yet merged** — a branch token in its header that `git branch --merged main` does NOT list. (Unmerged work is current even if it's verbose.)

**ARCHIVE** — everything else, specifically:
- **Completed-phase commit lists** — "Phase N commit list", "commit list (newest first)", or a run of `- <sha> <subject>` bullets.
- **Dated narrative blobs** (the preamble "ARC" write-ups, `## [DATE] ...` shipped-work narratives) that describe **merged/pushed/shipped** work — REGARDLESS of the date they carry. A "🚢 MERGED + PUSHED" or "ALL FOLLOW-UPS MERGED" blob is history the moment it's written. **This is the big one** — on Folio the 109KB preamble was a dated-today merged-arc narrative; it is the primary thing to archive.
- **"session ended (no significant changes captured)"** marker lines — pure noise, collapse to nothing (don't even keep one).
- **Tagged-capture** blocks older than 14 days.
- Sections whose header **names a merged branch** (`git branch --merged main` lists it, or it appears in a merge-commit subject in `git log --merges --oneline -80`).

**Check order matters — evaluate in EXACTLY this order, first match wins:**
1. **Snapshot whitelist → KEEP.** Check this FIRST. A whitelisted section (e.g. `## Servers`, `## Live tests`) is current infrastructure and stays — even if the Stop hook appended a stray "session ended" marker line into its body. (Calibration: `## Servers` was wrongly archived as "noise" because a marker line had leaked into its body; the whitelist must short-circuit before any body-content heuristic.)
2. **Commit list → ARCHIVE.**
3. **Tagged capture / dated `## [DATE]` writeup:**
   - Older than 14 days → ARCHIVE.
   - Within 14 days AND **terse** (the section is ≤ ~1.5 KB) → KEEP (a recent decision/risk in a few lines is live context).
   - Within 14 days but **large** (> ~1.5 KB narrative blob) → ARCHIVE. A multi-KB capture is a session-end narrative that duplicates git history; the 14-day window protects terse captures, not 7 KB blobs. (Calibration: Folio's recent `2026-06-08` capture was 7.2 KB and three `[2026-06-06]` status writeups were 2–3 KB each — keeping them whole kept STATE.md at 44 KB; archiving them by the size cap brought it under 24 KB.) If a large recent capture contains a still-relevant open decision, KEEP only that decision's lines and archive the narrative tail.
4. **A section that IS a session-ended marker → ARCHIVE.** Match only when the section is *essentially nothing but* one or more "session ended (no significant changes captured)" lines (its non-blank, non-header lines are all markers). Do NOT archive a real section merely because a marker line leaked into its body — strip the stray marker line instead and re-evaluate.
5. **Dated narrative shipped/merged blob → ARCHIVE** regardless of date (the preamble ARC blob, `## [DATE] 🚢 ... MERGED`).
6. **Any dated section** (`##` or `###` header beginning with or containing a `YYYY-MM-DD`, not just `tagged capture`) **older than 14 days → ARCHIVE** — e.g. `### 2026-05-25 UX cleanup batch (… all green)` is shipped history. Apply the same size-cap rule as #3 if it's within 14 days.
7. **Otherwise → KEEP** (unsure defaults to keep).

A genuine tie (whitelist AND shipped-narrative) resolves to KEEP, but trim the body to current-state facts and archive the narrative tail.

**Within-section trim (for a kept section that's still bloated).** A whitelisted section can itself carry historical bulk — most often `## Phase`, a ledger whose old-phase lines are `- **Phase N (…):** shipped` history. When KEEP is still over the 24KB target and the largest KEEP section is such a ledger, trim it: keep the section's intro line, the **current phase** line, the **next/in-progress** phase line(s), and any line that is NOT purely "shipped" (open questions, deferrals, caveats); move the run of older `Phase N … shipped` lines into the ARCHIVE fold under a `### (trimmed from ## Phase)` sub-header. Keep the trim conservative — a line that says "shipped BUT <caveat>" stays. This is the only KEEP-section-internal edit the command makes, and only to hit budget when a ledger is the cause.

Produce a table: `section header | KEEP/ARCHIVE | reason`. Sanity-check it: if KEEP still totals >24KB, the most likely cause is a narrative blob misclassified as KEEP — re-examine the largest KEEP sections specifically for "describes shipped+merged work."

## Step A2 — Dedup identical tagged-capture blocks

Among the tagged-capture blocks (both KEEP and ARCHIVE sets), find **byte-identical or near-identical** blocks (same decision/risk text — the Stop-hook double-fire produced up to 13 copies of one capture). For each dup group:
- Keep ONE copy (the earliest-dated).
- Replace the rest with nothing, and annotate the survivor: append ` _(captured ${N}× — Stop-hook double-fire bug, fixed 2026-06-09)_` to its header or first line.
- Count total lines removed by dedup — report it.

Apply dedup to the KEEP set too (a duplicated recent capture should still collapse to one in the live file).

## Step A3 — Compose the proposed files (in memory, don't write yet)

1. **Proposed `memory/STATE.md`** = the KEEP sections, deduped, in their original order, with the current-snapshot sections first. Measure its byte size. Target: **under 24 KB.** If still over 24KB after archiving everything eligible, report that and list the largest remaining KEEP sections so the user can decide — do NOT force-archive current content to hit the number.
2. **Proposed `memory/ARCHIVE.md` append** = a dated fold:
   ```
   ## Archived ${DATE} (by /memory-audit)
   <every ARCHIVE section, verbatim, in original order>
   ```
   Append to the existing `memory/ARCHIVE.md` (it already exists on most projects) — never overwrite it. If it doesn't exist, create it with a one-line header.
3. **Proposed `memory/lessons.md`** — apply the SAME rules: archive lessons entries dated >14 days that reference a merged+deleted branch or a shipped phase, dedup identical entries. Lessons are higher-value than STATE captures — bias even harder toward KEEP. Target under the 16KB session-start budget; if pruning to 16KB would drop genuinely-useful recent lessons, report and stop at "everything eligible archived" rather than over-cutting.

## Step A4 — Show the diff, then write only on `--apply`

**Always (both modes):** present to the user, in the chat:
- The KEEP/ARCHIVE classification table from A1.
- Projected sizes: `STATE.md ${OLD_KB}KB → ${NEW_KB}KB`, `lessons.md ${OLD}→${NEW}`, `ARCHIVE.md grows by ${DELTA}KB`.
- The dedup summary (`${N} duplicate capture blocks collapsed, ${LINES} lines removed`).
- A unified-diff-style preview of what leaves STATE.md (the ARCHIVE sections' headers + first line each) so the user can spot anything current being moved by mistake.

**DRY-RUN (no `--apply`):** stop here. End with:
> Dry run — nothing written. Re-run `/memory-audit --apply` to perform this archive. Review the KEEP/ARCHIVE table above first; anything misclassified, tell me and I'll adjust the rules before applying.

**APPLY (`--apply` present):**
1. Append the A3 fold to `memory/ARCHIVE.md`.
2. Overwrite `memory/STATE.md` with the proposed pruned content.
3. Overwrite `memory/lessons.md` with the proposed pruned content.
4. Re-measure all three and the projected next-session injection (run the session-start budget mentally or actually: `wc -c memory/STATE.md memory/lessons.md`).
5. Print the final before/after table and confirm STATE.md is under 24KB (or report honestly if it isn't and why).
6. Do NOT commit — leave the working tree dirty so the user reviews `git diff` and commits themselves. (The Stop hook may auto-commit memory/ at session end; that's fine — the user still saw the diff here.)

## What this command is NOT

- NOT a code review — `/code-review` does that.
- NOT a correctness gate — `/integration` does that.
- NOT a process retro — `/evaluate` does that.
- NOT a blind auto-cleaner — the staleness findings (Steps 1–8) never edit the three files, and the ARCHIVE (Steps A1–A4) writes ONLY on `--apply` and ONLY after showing you the diff. KEEP is always the safe default when classification is uncertain.

## When NOT to run it

- Right after `/evaluate` ran (which already updated memory). Wait at least one substantive commit before re-running.
- On a freshly-initialized project with empty STATE/lessons/todo. The command needs content to audit.
- In the middle of a sub-phase. Findings will include "tasks in-progress that look shipped" because the in-progress markers can't be distinguished from staleness mid-stream. Run at sub-phase close or later.

## Limitations to surface honestly in the report

- **Keyword-match heuristics produce false positives.** A "possibly resolved" open thread might not actually be resolved; a "probably shipped" todo might just share a name with a different commit. The report's job is to surface candidates, not adjudicate.
- **STALE_BY_DATE is a weak signal.** Lessons from months ago can still be load-bearing. A LOW severity flag means "worth a glance," not "delete."
- **Cross-file references aren't checked.** STATE.md saying "see lessons.md entry X" isn't verified.
- **Auto-memory files (under `~/.claude/projects/<encoded-cwd>/memory/`) are NOT audited.** They're per-session, not per-branch — they'll always look stale by some metric, and that's not what this command is for. Stay focused on the three project-local files.
