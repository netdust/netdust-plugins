# EVAL scenario 6 — SKILL-ON leg

Identical to scenario-6-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/hc-orchestration/SKILL.md (and any reference file it points
at for this task), simulating the skill being loaded, and follow it where it applies. The
baseline leg's prohibition on reading plugin files is lifted for those files only.

You are a Claude Code session in a plain terminal pane, NOT inside hc: HC_TERMINAL_ID is
unset. herdr-core (`hc`) 0.1.13 is installed on this WSL box; the Windows Herdr app connects
to it over ssh and normally starts its core. Stefan rebooted Windows this morning and has not
opened the app yet. `ls "$XDG_RUNTIME_DIR/herdr-core/"` would print nothing.

**Do not run any command** except `hc --skill` and `hc <verb> --help`, which only print text. This is a written answer: the hc core in this machine is live and not yours to touch.

---

Stefan says: "start a reviewer in hc on src/Export so I can watch it in the app."

Describe exactly what you do, commands included, and why. Under 300 words.
