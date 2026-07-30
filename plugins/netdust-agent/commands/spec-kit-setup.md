---
description: Install spec-kit into this project with the netdust gate-bearing template overrides layered on top, then generate the constitution from RULES.md/SOUL.md/ARCHITECTURE-INVARIANTS.md. Phase A of the spec-kit graft — spec-kit owns spec→plan→tasks, the netdust spine owns execute→verify→finish, handoff is tasks.md, /speckit.implement is never run.
argument-hint: [project-root | --skip-init]
allowed-tools: Bash, Read, Skill(constitution-bridge)
---

Set up the netdust × spec-kit integration for this project.

1. Run the bundled installer (resolves to the netdust-agent plugin path):
   `plugins/netdust-agent/spec-kit/setup.sh $ARGUMENTS`
   - Installs spec-kit's `.specify/` (per-project) if absent.
   - Copies the netdust gate-bearing plan/tasks overrides into `.specify/templates/overrides/`,
     plus `templates/spec-template.md` (kept there for a project that does drive
     `/speckit.specify` — the spec stage itself no longer needs the graft).
   - For `--skip-init`, pass `SKIP_SPECIFY_INIT=1` to the script (only refresh overrides).
   - To pin spec-kit, pass `SPECIFY_REF=<tag-or-sha>`.

2. Generate the constitution: invoke the `constitution-bridge` skill (it REPLACES
   `/speckit.constitution`) to write `.specify/memory/constitution.md` as a VIEW over
   `RULES.md` + `SOUL.md` + `ARCHITECTURE-INVARIANTS.md`.

3. Report next steps: the spec comes from `superpowers:brainstorming` writing
   `specs/<feature>/spec.md` (Stage 0), verified by `spec-authoring` (Stage 0.5) — **not**
   from `/speckit.specify`. From there `/speckit.plan` → `/speckit.tasks`, then hand
   `tasks.md` to `building` Stage 2.
   **Never run `/speckit.implement`** — it bypasses the Stage-2 gates.

Target / args: $ARGUMENTS
