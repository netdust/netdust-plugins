# EVAL scenario 1 — SKILL-ON leg

Identical to scenario-1-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/herdr-orchestration/SKILL.md (simulating the skill
being loaded) and follow it where it applies. The baseline leg's prohibition on
reading plugin files is lifted for that one file only.

Then answer the same task:

While implementing the feature you discover a genuine bug in the shared
ntdst-core framework code (mu-plugins/ntdst-core/) — a save-path error is
swallowed. Project rules: framework fixes land on their own branch from
`master`, never inside a feature diff.

Describe, concretely and step by step (commands included where relevant), how
you get this framework bug fixed WITHOUT interrupting your feature work and
WITHOUT disturbing the neighboring session. Keep it under 500 words.
