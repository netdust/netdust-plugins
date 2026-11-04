# EVAL scenario 8 — SKILL-ON leg

Identical to scenario-8-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/hc-orchestration/SKILL.md (and any reference file it points
at for this task), simulating the skill being loaded, and follow it where it applies. The
baseline leg's prohibition on reading plugin files is lifted for those files only.

You are a Claude Code session running inside herdr-core (`hc`) on the `wsl` machine: this session
was resumed today, and `echo $HC_TERMINAL_ID` prints `t2r`. Stefan watches the Windows Herdr app.
Yesterday's notes say this session's address was `t1y`. Your own space is named `ntdst-baseline`.
You planned a feature with Stefan for a DIFFERENT repo: `/home/ntdst/Sites/ntdst-core`, branch
`feature/model-revisions` (spec, plan and plan review already committed there). Herdr has no space
named `ntdst-core`.

**Do not run any command** except `hc --skill`, `hc <verb> --help`, and the Herdr app's own
`--skill` and `commands` (which only print text). This is a written answer: the hc core and the app
on this machine are live and not yours to touch.


---

Stefan says: "ok, open it as a space in herdr and start".

Describe exactly what you do, commands included: how the space is made, how the coder is started
and where it appears, and how the coder is told who its reviewer is. Under 350 words.
