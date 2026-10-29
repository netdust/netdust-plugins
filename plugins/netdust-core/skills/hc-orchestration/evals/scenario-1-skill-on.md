# EVAL scenario 1 — SKILL-ON leg

Identical to scenario-1-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/hc-orchestration/SKILL.md (and any reference file it points
at for this task), simulating the skill being loaded, and follow it where it applies. The
baseline leg's prohibition on reading plugin files is lifted for those files only.

You are a Claude Code session running inside herdr-core (`hc`): HC_TERMINAL_ID=t4 on the
`wsl` machine, started from a space in the Windows Herdr app (Stefan watches the app).
`hc --skill` prints the delegation contract. Project: ~/Sites/stride, branch feature/edition-export. You just finished
src/Export/EditionExporter.php and its tests.

**Do not run any command** except `hc --skill` and `hc <verb> --help`, which only print text. This is a written answer: the hc core in this machine is live and not yours to touch.

---

Stefan says: "get a second pair of eyes on the exporter and make sure the gate is green before I
look at it, and keep going on the CSV headers meanwhile."

Answer concretely, commands included: how you start the helper and with what, what you do
while it works, how you collect its result and what you do with it, and what happens to the
helper afterwards. Under 400 words.
