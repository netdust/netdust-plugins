---
description: Learn from a past session on demand — a read-only reviewer reads its transcript for Stefan's corrections, gates that fired or were bypassed, skills that should have loaded, rulings and failed premises, and proposes skill lessons with eval cases. Proposals only; nothing lands until Stefan approves each one.
argument-hint: [session id | transcript path]  (empty: pick from this project's recent sessions)
allowed_tools: ["Bash", "Read", "Glob", "Write", "Agent"]
---

Learn from one session. You coordinate; the `session-learner` reads.

## Step 1 — Find the session

With `$ARGUMENTS` a session id or a path, resolve it to the absolute transcript
`~/.claude/projects/<project slug>/<id>.jsonl` and its `<id>/subagents/*.jsonl`. With no
argument, list this project's sessions newest first — id, date, size, and the first thing
Stefan typed (a short slice, never the whole record) — and ask which one. Recency alone is not
identity: confirm by quoting the chosen session's first prompt back. Never read a transcript
whole; `superpowers:diagnosing-superpowers`' context-safety rules apply to you too.

## Step 2 — Dispatch `session-learner`

On the most capable available model, with the absolute transcript paths and the project root.
It is read-only and returns the proposals.

## Step 3 — File and present, then stop

Write the report to `~/.claude/netdust-gates/session-learn/<session id>.md` — it is about the
harness, not the project, so it is not committed to the project. Show Stefan each proposal,
numbered, with its evidence, and give the path.

**Stop there.** Stefan approves proposals one by one. Nothing is written to a skill, a
lessons file, an eval or a project file until he does.

## On his approval — apply, then ask again

- **netdust** proposals: in the marketplace source (`~/Projects/netdust-plugins`), on a new
  branch in its own worktree — each approved lesson in its skill's `lessons.md`, each with the
  eval case the proposal named, the plugin's tests run. Then show him the diff and wait: the
  merge is a second approval.
- **project** proposals: in the project, as he approved them.
- **superpowers** findings: nothing in netdust. If he wants the upstream report, invoke
  `superpowers:diagnosing-superpowers` with the evidence.
