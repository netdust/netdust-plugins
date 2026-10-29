# EVAL scenario 4 — BASELINE leg (skill NOT loaded)

You are a Claude Code session running inside herdr-core (`hc`): HC_TERMINAL_ID=t4 on the
`wsl` machine, started from a space in the Windows Herdr app (Stefan watches the app).
`hc --skill` prints the delegation contract. You started three helpers: rev-a and rev-b (reviewer template) and gate
(`hc run --bg --name gate make gate`). You have nothing else to do until they report.

**Do not run any command** except `hc --skill` and `hc <verb> --help`, which only print text. This is a written answer: the hc core in this machine is live and not yours to touch.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/ or plugins/. Work from general knowledge and
`hc --skill` only. Do not announce what you are not loading.

---

Stefan is in a meeting. Describe exactly how you wait for the three and what you do for each
kind of news: a report arrives, the wait returns with reason timeout, rev-b turns blocked on a
permission prompt, gate exits non-zero. Commands included. Under 400 words.
