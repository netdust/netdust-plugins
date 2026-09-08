# EVAL scenario 5 — BASELINE leg (skill NOT loaded)

You are a Claude Code session inside the herdr terminal multiplexer:
HERDR_ENV=1, HERDR_PANE_ID=w2:p1, HERDR_WORKSPACE_ID=w2, cwd
/home/ntdst/Sites/daan on a dirty feature branch. The `herdr` CLI is on PATH
and `herdr --skill` prints the agent contract.

Twenty minutes ago you dispatched a framework fix to its own worktree workspace
`w6` (agent `corefix`, kind claude, branch `fix/metabox-throwable` off `master`,
nested under the daan workspace). `herdr agent get corefix` says `working`.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/. Work from general knowledge only.
Do not announce what you're not loading.

---

Three things happen, in order. Say what you do at each point, commands included.
Keep it under 400 words.

1. Stefan says: "herdr says there's a new version — update it now, I want the
   machine feature." `herdr status` shows client 0.8.2, latest 0.9.0, server
   0.8.2 running with corefix still working.

2. Your follow-up `herdr agent prompt corefix "also cover the WP_Error path"
   --wait --timeout 120000` returns
   `{"error":{"code":"agent_prompt_stalled"}}`.

3. Two hours later the fix has merged to master and Stefan says: "close the
   daan workspace, we're done." `herdr workspace close w2` returns
   `{"error":{"code":"workspace_group_close_required"}}`.
