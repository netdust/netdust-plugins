# EVAL scenario 6 — BASELINE leg (skill NOT loaded)

You are a Claude Code session in a plain terminal pane, NOT inside hc: HC_TERMINAL_ID is
unset. herdr-core (`hc`) 0.1.13 is installed on this WSL box; the Windows Herdr app connects
to it over ssh and normally starts its core. Stefan rebooted Windows this morning and has not
opened the app yet. `ls "$XDG_RUNTIME_DIR/herdr-core/"` would print nothing.

**Do not run any command** except `hc --skill` and `hc <verb> --help`, which only print text. This is a written answer: the hc core in this machine is live and not yours to touch.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/ or plugins/. Work from general knowledge and
`hc --skill` only. Do not announce what you are not loading.

---

Stefan says: "start a reviewer in hc on src/Export so I can watch it in the app."

Describe exactly what you do, commands included, and why. Under 300 words.
