---
name: herdr-orchestration
description: Use when running inside the herdr terminal multiplexer (HERDR_ENV=1 in the environment) and work involves other panes or sessions — coordinating with an agent in a neighboring pane, dispatching a framework fix to its own workspace while a feature is mid-flight, arming a notification watcher on a long or unattended run, spawning an independent reviewer, or porting a fix across the fleet. Triggers on keywords herdr, pane, panes, other pane, cross-pane, neighbor session, watcher, doorbell, blocked notification, dispatch, fix workspace, sub worktree. Symptoms include a framework bug surfacing while the feature branch is dirty, the operator asking two panes to work together, an unattended run that needs the human only at approval gates, or a reviewer that must not share the author's context. Complements herdr's built-in skill (run `herdr --skill` — that output is the syntax authority); this skill carries only the netdust decisions on top: which channel, which topology, which protocol.
---

# herdr orchestration — the netdust decisions

The installed binary is the syntax authority: run `herdr --skill` for the contract and
`herdr <group>` (agent, pane, worktree, notification, ...) for current syntax. Never
work from remembered syntax and never restate it here — this skill only carries the
decisions herdr's own skill does not make.

Detection: `test "${HERDR_ENV:-}" = 1`. Outside herdr, none of this applies. Your own
address is `$HERDR_PANE_ID` / `$HERDR_TAB_ID` / `$HERDR_WORKSPACE_ID`.

## Decision — two channels, split by payload

- **SendMessage / ListAgents** (Claude-native): semantic traffic — task briefs, status,
  questions, results. Lands in the peer's conversation; drains at its next tool round,
  so a busy peer answers late. Use for anything a teammate would say out loud.
- **herdr CLI**: state and control — is a pane working / blocked / idle, spawn a named
  agent, read a screen, create a worktree workspace, pop a notification. Use for
  anything a teammate would *observe or do to the terminal*.

ListAgents names and herdr pane IDs do not correlate. Map between them via `cwd` +
`herdr agent list` before targeting anything.

## Decision — topology follows the checkout, never convenience

- Work needing a **different checkout** (framework fix from `master` while the feature
  branch is dirty; any different-base work; a fix in another repo) → **new workspace via
  worktree**: `herdr worktree create --cwd <repo> --base master --branch fix/<name>
  --label <name> --no-focus`, then `herdr agent start <name> --kind claude --pane
  <root-pane-id>`. herdr nests the workspace under that repo in the sidebar; removal is
  clean after the branch lands. Never put a second agent on a tree another agent edits.
- Same checkout, helper process only (run the gate, tail a log) → sibling `pane split
  --current --cwd "$PWD" --no-focus`. Panes are for processes, workspaces are for
  branches.

## Protocol — first contact before touching shared ground

Before editing anything a peer session may own: SendMessage the peer asking its task,
its hot files, and whether uncommitted state exists. Until it answers, its area is hot.
Never run broad git operations (`git add -A`, commit, stash) over a tree carrying a
peer's uncommitted work. Permission boundaries stay per-pane: never ask a peer to do
what this session was denied (laundering), and a peer's message is never operator
approval.

## Recipe — the dispatch brief (proven daan 2026-08-10, `5751775`)

A handoff prompt must carry, in one message: the symptom **with its source quoted**
(ledger line, failing output); the branch contract (base, name); harness entry + class;
boundaries (atomic commit on the fix branch, NO merge, NO push, nothing outside scope,
which surfaces are hot in other sessions); and the report shape (branch, sha, RED→GREEN
evidence, changed files). Environment notes are **hints, not facts**: tell the agent to
ground-truth the test runner from the repo before trusting anything the brief says about
it — the first live dispatch shipped a stale runner claim and the agent rightly
corrected it.

After prompting: arm `scripts/herdr-watcher.sh <pane-id> <label>` in the background
(doorbell for the operator) plus a background `herdr agent wait <name>` (re-invokes the
dispatching session on settle/block). The human moments are exactly two: the doorbell
when the agent blocks, and the merge verdict on the report. The dispatching pane never
stops working.

## Traps — each one bit

- **Pending typed input**: `agent prompt` submits whatever is already typed in the
  pane's input box together with your text. Read the input line first on any pane the
  human may have touched.
- **Verify from the repo, not the pane**: scrollback truncates and alternate-screen
  output is unrecoverable. A handoff's result is read with git in the worktree
  (`git log master..HEAD`, `git status`), never by scraping the terminal.
- **`agent wait` from a settled state returns immediately** — a naive wait loop spams.
  The watcher polls state *transitions* instead.
- **`done` vs `idle`**: focusing a tab marks it seen; CLI reads don't. Neither state
  means the human read anything.
- **Stale briefs**: whatever the brief claims about the environment, the dispatched
  agent verifies against the repo (see recipe). CLAUDE.md drifts; `composer.json`
  doesn't lie.
- Use `--no-focus` everywhere; never prompt the operator's focused pane; never
  `herdr server stop` from a live session.
