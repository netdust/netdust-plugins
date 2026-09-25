---
description: Follow up a review, like commits on a PR — show the saved findings for a feature, Stefan picks which to act on, one fix pass on feature/<name>, push, then re-promote.
argument-hint: <feature>
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Edit", "Write", "Skill", "AskUserQuestion"]
---

1. **The review.** Read `$(git rev-parse --git-common-dir)/reviews/$ARGUMENTS.md`. None: say
   so, name `make review name=$ARGUMENTS` (`/feature-review $ARGUMENTS` on a project without
   devops, whose summary is then the review), change nothing, stop.
2. **The branch.** Work where `feature/$ARGUMENTS` is checked out: in another worktree, go
   there; a dirty checkout, stop and say what is dirty — never stash. Otherwise
   `git checkout feature/$ARGUMENTS && git pull --ff-only`.
3. **Stefan picks.** Show the findings, Blocking first, and ask which findings to act on. A
   finding that is a decision (which source, which behaviour) is a question to him, not a fix.
4. **The fix pass** is the `netdust-gates:policy` Close's fix pass, on the picked findings only.
   Copy the report to `specs/$ARGUMENTS/review.md` and commit it with the fixes.
5. **Push and hand back.** `git push`, then tell Stefan: `make promote name=$ARGUMENTS` puts
   the fixed tip on staging; it finds the saved review and skips it — no re-review of a fix pass
   (`review=low` if he wants the fixes looked at).
