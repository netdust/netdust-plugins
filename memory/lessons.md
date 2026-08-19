
### 2026-07-03
- the netdust-core `hooks/` scripts are dead copies (`hooks.json` registers nothing) — any future hook fix belongs in `plugins/netdust-agent/hooks/` in `~/Projects/netdust-plugins`, delivered by version bump + `claude plugin update`, never by editing the cache.

### 2026-07-03
- netdust-agent's session-start.sh resolves the project via `$(pwd)`, not the stdin JSON `cwd` field — asymmetric with session-stop.py; harmless in the real hook lifecycle but a trap when firing it manually for tests.

### 2026-08-13
- Two file-handling rules burned this session: (1) NEVER `open(path,'w')` with the old content read inside the same expression — 'w' truncates before the read runs; read to a variable first, then write. STATE.md was destroyed this way and had to come back from the restic backup. (2) In this shared source repo, `git fetch` and re-anchor on origin/main BEFORE authoring — the clone was 35 commits stale (pre-0.18 re-thinning), and everything built against it targeted deleted files and had to be re-landed from a worktree.

### 2026-08-19
- systemd `EnvironmentFile=` loads after `Environment=` and overrides it. Reading only a `.service` file's inline `Environment=` line gave me a wrong diagnosis (collie pointed at a dead socket). Read the `.env`, or verify from the process's actual behaviour.

### 2026-08-19
- herdr sessions are separate servers with separate ID spaces — a bare `herdr` command targets the session the calling pane lives in, not the project's session. Creating topology without first checking `herdr session list` puts it in whatever session you happen to be sitting in. There is no move between sessions; the only fix is rebuild in the right one and close the wrong one.
- the session-review watcher observes the main agent's pane/tab live through herdr — lifecycle transitions, terminal title, viewport at the transition — not the session's transcript JSONL. Transcripts are complete but post-hoc; the point is watching the process as it runs, which also works on panes whose transcripts aren't readable (remote boxes, other agent kinds).
- `herdr agent prompt --wait` can return a settled state produced by agent STARTUP rather than by your prompt, with no `agent_prompt_stalled` error. `done` immediately after `agent start` is not evidence the text ran. Verify by the terminal title changing from the generic `✳ Claude Code` to a conversation title, or by `agent get` reporting `agent_session`.
