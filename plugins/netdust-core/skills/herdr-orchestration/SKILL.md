---
name: herdr-orchestration
description: "Use when running inside the herdr terminal multiplexer (HERDR_ENV=1 in the environment) and work involves other panes or sessions — coordinating with an agent in a neighboring pane, dispatching a framework fix to its own workspace while a feature is mid-flight, arming a notification watcher on a long or unattended run, spawning an independent reviewer, or porting a fix across the fleet. Triggers on keywords herdr, pane, panes, other pane, cross-pane, neighbor session, watcher, doorbell, blocked notification, dispatch, fix workspace, sub worktree, server restart, agent resume, remote box, api snapshot. Symptoms include a framework bug surfacing while the feature branch is dirty, the operator asking two panes to work together, an unattended run that needs the human only at approval gates, a server restart or update proposed while a dispatch is running, or a reviewer that must not share the author's context. Complements herdr's built-in skill (run `herdr --skill` — that output is the syntax authority); this skill carries only the netdust decisions on top: which channel, which topology, which protocol."
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

herdr holds no shared memory. Upstream is explicit that it orchestrates processes and
never merges agent context. Nothing reaches another pane unless one of these two
channels carries it.

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

herdr does not isolate file changes: two panes in one directory edit the same file. The
worktree IS the isolation, and using it safely stays a git decision — herdr only creates
it for you.

## Decision — remote boxes run their own server

For agent work on a fleet box, name the session and go in with one command:

```bash
ssh -t <host> herdr --session <name>      # e.g. ssh -t netdust-web herdr --session stride
```

`-t` is required — herdr is a TUI and needs a PTY. The server, the agents and the shells
all live on that box, so a dropped connection is only a detach: reconnect with the same
command and the work is still running.

That is also the reason to go through herdr at all. `ssh -t <host> claude` puts the agent
straight on the connection, and a drop kills it silently — a frozen screen locally, no
process remotely. Check `pgrep` on the box, never the pane.

Do not attach from the workstation with `herdr --remote <host>`: the thin client buys
nothing here and adds a transport plus a keybinding question. Fleet operations that are
not agent work stay on plain SSH with `netdust-core:ploi`.

## Decision — detach freely, never restart mid-dispatch

Detach keeps every process alive. Stopping the server does not. The workspace, tab,
pane, cwd and focus all return; the processes are gone.

- Never run `herdr update` or `herdr server stop` while a dispatch is in flight. If an
  update cannot wait, `herdr update --handoff` is the only live path and it is
  experimental — settle the dispatch first.
- A dispatch's durable artifact is the branch, never the pane. After a restart the
  worktree workspace and its commits survive. Re-start the agent, then re-read state
  from git.
- Install the integration for every kind you dispatch, and check it with
  `herdr integration status`. It records the agent's native session id, so the
  conversation can resume after a full restart. It does not change lifecycle detection.
- Experiments, skill evals and anything that might stop a server run on their own
  session: `herdr --session <name>`. Never the default session that carries live work.

## Protocol — first contact before touching shared ground

`herdr api snapshot` returns every agent, layout and focus in one call — prefer it to a
sweep of list commands. Agents the human started carry no unique name; the `agent` field
holds the kind, not an identity. Join a herdr pane to a ListAgents peer on `cwd`, and
read `terminal_title_stripped` for the peer's own conversation title. That title names
the peer's task without reading its screen or spending a message.

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

The watcher polls on a timer. A `herdr-plugin.toml` plugin can react to blocked and done
as events instead — not built. A plugin runs local commands with your permissions, so
read one before you install it.

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
- **A state you doubt**: Claude Code and Codex panes are classified by screen detection,
  integration installed or not. A changed prompt shape can leave a pane `unknown`, which
  never proves completion. `herdr agent explain <target> --verbose` names the rule that
  matched, the detection manifest behind it, and whether that manifest is current. If the
  agent shipped a new UI against a stale manifest, refresh with
  `herdr server update-agent-manifests`. Never infer the state from scrollback.
- **Stale briefs**: whatever the brief claims about the environment, the dispatched
  agent verifies against the repo (see recipe). CLAUDE.md drifts; `composer.json`
  doesn't lie.
- Use `--no-focus` everywhere; never prompt the operator's focused pane; never
  `herdr server stop` from a live session.
