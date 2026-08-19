# EVAL scenario 3 — BASELINE leg (skill NOT loaded)

You are a Claude Code session inside the herdr terminal multiplexer:
HERDR_ENV=1, HERDR_PANE_ID=w5:p2, HERDR_WORKSPACE_ID=w5, cwd /home/ntdst.
The `herdr` CLI is on PATH and `herdr --skill` prints the agent contract.

The machine runs several herdr sessions. The project you are asked about,
`stride`, has its own long-running session; your own pane does not live in it.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/. Work from general knowledge only.
Do not announce what you're not loading.

---

Stefan says: "Set up the dev workspace for stride — a pane with Claude in the
repo, a shell for the gate, and one tailing ddev logs. Put it where the stride
work lives."

Describe, concretely and with commands, how you build it. Then answer: an hour
later you notice the panes are not where Stefan expected them. What went wrong
and how do you fix it? Keep it under 500 words.
