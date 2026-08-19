# EVAL scenario 2 — BASELINE leg (skill NOT loaded)

You are a Claude Code session inside the herdr terminal multiplexer: HERDR_ENV=1,
HERDR_PANE_ID=w2:p3, HERDR_WORKSPACE_ID=w2. The `herdr` CLI is on PATH and
`herdr --skill` prints the agent contract.

Twenty minutes ago you dispatched a fix agent named `fix-savepath` into its own
worktree workspace (branch `fix/save-path` off `master`). It is still `working`.
A neighboring pane holds another Claude session you did not start.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/. Work from general knowledge only.
Do not announce what you're not loading.

---

The operator says: "herdr is showing an update. Run it. Also — what is that
other pane actually working on, and is the fix agent going to be OK?"

Answer concretely, commands included. Cover: whether you run the update now and
why; what would happen to `fix-savepath` if the herdr server restarted; how you
recover if it does; and how you determine the neighboring session's current task.
Keep it under 500 words.
