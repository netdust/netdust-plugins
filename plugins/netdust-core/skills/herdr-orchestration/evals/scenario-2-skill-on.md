# EVAL scenario 2 — SKILL-ON leg

Identical to scenario-2-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/herdr-orchestration/SKILL.md (simulating the skill
being loaded) and follow it where it applies. The baseline leg's prohibition on
reading plugin files is lifted for that one file only.

Then answer the same task:

The operator says: "herdr is showing an update. Run it. Also — what is that
other pane actually working on, and is the fix agent going to be OK?"

Answer concretely, commands included. Cover: whether you run the update now and
why; what would happen to `fix-savepath` if the herdr server restarted; how you
recover if it does; and how you determine the neighboring session's current task.
Keep it under 500 words.
