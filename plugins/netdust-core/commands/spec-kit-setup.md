---
description: Install spec-kit into this project with the netdust gate-bearing template overrides layered on top, then generate the constitution from RULES.md/SOUL.md/ARCHITECTURE-INVARIANTS.md. Phase A of the spec-kit graft — spec-kit owns spec→plan→tasks, the netdust spine owns execute→verify→finish, handoff is tasks.md, /speckit.implement is never run.
argument-hint: [project-root | --skip-init]
allowed-tools: Bash, Read, Skill(constitution-bridge)
---

Set up the netdust × spec-kit integration for this project.

1. Run the bundled installer (resolves to the netdust-core plugin path):
   `plugins/netdust-core/spec-kit/setup.sh $ARGUMENTS`
   - Installs spec-kit's `.specify/` (per-project) if absent.
   - Copies the netdust gate-bearing overrides into `.specify/templates/overrides/`.
   - For `--skip-init`, pass `SKIP_SPECIFY_INIT=1` to the script (only refresh overrides).
   - To pin spec-kit, pass `SPECIFY_REF=<tag-or-sha>`.

2. Generate the constitution: invoke the `constitution-bridge` skill (it REPLACES
   `/speckit.constitution`) to write `.specify/memory/constitution.md` as a VIEW over
   `RULES.md` + `SOUL.md` + `ARCHITECTURE-INVARIANTS.md`.

3. Report next steps: `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` →
   `/speckit.tasks`, then hand `tasks.md` to `harnessed-development` Stage 2.
   **Never run `/speckit.implement`** — it bypasses the Stage-2 gates.

Target / args: $ARGUMENTS
