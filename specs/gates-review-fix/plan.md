# review levels and /review-fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/feature-review` honours `REVIEW_LEVEL` and ends its report with a `Findings:` line. `/review-fix X` turns a saved review into follow-up commits on `feature/X`, the way a PR's review comments become commits.

**Architecture:** Text changes to the existing command, plus one new interactive command that reuses the policy's fix-pass rule. It has no agent of its own.

**Tech Stack:** Markdown commands; Python pin tests.

**Spec:** specs/feature-review/spec.md (R6, R7, R8)

## Global Constraints

- The report's last line is exactly `Findings: <b> Blocking · <s> Should fix · <n> Note`, because `make` prints it.
- `/review-fix` changes nothing Stefan did not pick. A finding that is a decision comes back as a question, never as a guess.
- The fix pass is the policy's Close step 4 (each fix RED→GREEN through the seam, no re-review). `/review-fix` points at it and does not restate it.
- The policy stays under 150 lines.

## Review Focus

- No saved report for X: say so, name `make review name=X`, change nothing. (Task 2 text)
- A dirty checkout: stop before switching branches, never stash. (Task 2 text)

**First working version:** Task 1.

**Simplest design:** reuse the fix pass the policy already defines. I rejected a fixer agent because a reviewer that edits "becomes the fixer before Stefan approves anything" (tests/test_session_commands.py docstring).

---

### Task 1: levels and the Findings line in `/feature-review`

**Files:** Modify `plugins/netdust-gates/commands/feature-review.md` and `plugins/netdust-gates/tests/test_close_wiring.py`.

- [ ] **Step 1: Failing pin.** Add `"REVIEW_LEVEL"`, `"ultra"` and `"Findings: <b> Blocking"` to the tuple of the `/feature-review` pin in `test_close_wiring.py`. Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -2`. Expected: `test_close_wiring` fails.
- [ ] **Step 2: Text.** After "**What to review.**", add:

```markdown
**How much.** `$REVIEW_LEVEL` (`printenv REVIEW_LEVEL`), default `full`: `low` dispatches
superpowers' reviewer only; `full` adds the joiners below that apply; `ultra` adds, for a
feature, `staging-reviewer` on staging's promoted features with this feature added at its head, so
what it would collide with shows before it lands.
```

At the end of "**Report back**", add: "End with exactly one line: `Findings: <b> Blocking · <s> Should fix · <n> Note`."

- [ ] **Step 3: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1`. Expected: `All harness tests passed.` Then commit: `git commit -am "feat(gates): /feature-review levels and a Findings line"`.

### Task 2: `/review-fix`

**Files:**
- Create: `plugins/netdust-gates/commands/review-fix.md`
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, the "On demand" paragraph: add "`/review-fix <feature>` turns a saved review into follow-up commits on the branch"
- Modify: `plugins/netdust-gates/tests/test_close_wiring.py`, one pin
- Modify: version 0.9.0 in `.claude-plugin/marketplace.json` and `plugins/netdust-gates/.claude-plugin/plugin.json`

- [ ] **Step 1: Failing pin.**

```python
        (all(t in _read("commands/review-fix.md") for t in (
            "git-common-dir", "Close step 4", "make promote name=", "which findings", "never stash"))
         and "/review-fix" in policy,
         "/review-fix: the saved report, Stefan picks, the policy's fix pass, re-promote"),
```

Run the suite. Expected: `test_close_wiring` fails (a missing file).

- [ ] **Step 2: `commands/review-fix.md`.**

````markdown
---
description: Follow up a review, like commits on a PR — show the saved findings for a feature, Stefan picks which to act on, one fix pass on feature/<name>, push, then re-promote.
argument-hint: <feature>
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Edit", "Write", "Skill", "AskUserQuestion"]
---

1. **The review.** Read `$(git rev-parse --git-common-dir)/reviews/$ARGUMENTS.md`. None: say
   so, name `make review name=$ARGUMENTS`, stop.
2. **The branch.** A dirty checkout: stop and say what is dirty — never stash. Otherwise
   `git checkout feature/$ARGUMENTS && git pull --ff-only`.
3. **Stefan picks.** Show the findings, Blocking first, and ask which findings to act on. A
   finding that is a decision (which source, which behaviour) is a question to him, not a fix.
4. **The fix pass** — exactly the `netdust-gates:policy` Close step 4: each picked finding one
   fix, RED→GREEN through the seam where it showed, then the suite (`make gate`).
5. **Push and hand back.** `git push`, then tell Stefan: `make promote name=$ARGUMENTS` puts
   the fixed tip on staging, reviewing it again unless he adds `review=off`.
````

- [ ] **Step 3: Policy line, version 0.9.0.** The description starts "0.9.0: /feature-review honours REVIEW_LEVEL (low · full · ultra, which checks collisions with staging before landing) and ends with a Findings line; /review-fix <feature> turns a saved review into follow-up commits on the branch, the way a PR's review comments become commits. "
- [ ] **Step 4: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1`. Expected: `All harness tests passed.` Then commit: `git add .claude-plugin/marketplace.json plugins/netdust-gates && git commit -m "feat(gates): /review-fix — follow-up commits on the branch (0.9.0)"`.
