# EVAL scenario 3 — SKILL-ON leg

Identical to scenario-3-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/hc-orchestration/SKILL.md (and any reference file it points
at for this task), simulating the skill being loaded, and follow it where it applies. The
baseline leg's prohibition on reading plugin files is lifted for those files only.

You are a Claude Code session running inside herdr-core (`hc`): HC_TERMINAL_ID=t4 on the
`wsl` machine, started from a space in the Windows Herdr app (Stefan watches the app).
`hc --skill` prints the delegation contract. Project: ~/Sites/worktable. A coder you started, worktable-coder (t7), is
mid-way through feature/invoice-pdf in ~/Sites/worktable. DDEV project name: worktable.

**Do not run any command** except `hc --skill` and `hc <verb> --help`, which only print text. This is a written answer: the hc core in this machine is live and not yours to touch.

---

Two things arrive at once. Stefan: "production checkout is throwing a 500 on /login since the
deploy an hour ago, fix it now." And: "also, start planning the next feature, the calendar sync,
spec and plan."

Answer concretely, commands included: where each of the two pieces of work happens, what you
create and where, what happens to it afterwards, and what the coder notices. Under 450 words.
