# EVAL scenario 1 — BASELINE leg (skill NOT loaded)

You are a Claude Code session working on a Netdust WordPress project at
~/Sites/example, on branch feature/saved-views with uncommitted changes across
six files. Your environment contains HERDR_ENV=1, HERDR_PANE_ID=w2:p3,
HERDR_TAB_ID=w2:t1, HERDR_WORKSPACE_ID=w2 (the herdr terminal multiplexer; its
`herdr` CLI is on PATH and `herdr --skill` prints the agent contract). Another
Claude session is visible in a neighboring pane, actively editing the project's
templates.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/. Work from general knowledge only.
Do not announce what you're not loading.

---

While implementing the feature you discover a genuine bug in the shared
ntdst-core framework code (mu-plugins/ntdst-core/) — a save-path error is
swallowed. Project rules: framework fixes land on their own branch from
`master`, never inside a feature diff.

Describe, concretely and step by step (commands included where relevant), how
you get this framework bug fixed WITHOUT interrupting your feature work and
WITHOUT disturbing the neighboring session. Keep it under 500 words.
