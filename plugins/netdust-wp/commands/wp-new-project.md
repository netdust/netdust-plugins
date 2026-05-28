---
description: Scaffold a new Netdust WordPress project (CLAUDE.md, site.yml, memory/, tasks/, Makefile)
allowed_tools: ["Bash", "Read", "Write", "AskUserQuestion"]
---

Scaffold a new Netdust WordPress project in the current working directory using the harness templates.

**Confirm cwd is empty or has nothing to overwrite first.**

1. Ask the user (via `AskUserQuestion`):
   - Project name (kebab-case, becomes the SSH alias suffix and DDEV project name)
   - Risk level: `low` / `medium` / `high`
   - Stack type: `bedrock` / `custom-app` / `custom-site`
   - Hosting provider: `ploi` / `combell` / `other`
   - Deploy method (the canonical 9):
     1. `makefile` — git-bundle Makefile, no GitHub required (Stride/VAD pattern)
     2. `git-push` — Ploi auto-deploy on push
     3. `rsync` — direct rsync local→remote
     4. `rsync-staging-prod` — nested staging/production rsync (VAD style)
     5. `manual` — no automation, direct edits
     6. `ftp` — PhpStorm auto-upload via FTP
     7. `autogit` — Combell autogit symlinks
     8. `git-bundle-makefile` — explicit git-bundle variant (Netdust style)
     9. `tbd` — not yet decided

2. Generate `site.yml` from `~/.claude/plugins/netdust-wp/templates/site.yml.tmpl`, substituting the answers.

3. Generate `CLAUDE.md` from `~/.claude/plugins/netdust-wp/templates/project-CLAUDE.md.tmpl`, with the project name and `@~/.claude/plugins/netdust-wp/CLAUDE.md` import.

4. Create:
   ```
   memory/
   ├── STATE.md     (seeded with: "# <project> — Project State\n_Created YYYY-MM-DD_\n\n## Current Phase: bootstrap\n")
   └── lessons.md   (empty)
   tasks/
   └── todo.md      (empty)
   ```

5. If deploy method is `makefile` / `git-bundle-makefile` / `git-push`, copy the matching variant from `~/.claude/plugins/netdust-wp/templates/Makefile.tmpl` (find the section for the chosen method). For other methods, do not create a Makefile.

6. Initialize git if `.git/` does not exist, then commit the scaffold:
   ```bash
   git init -q && git add . && git commit -q -m "scaffold: netdust-wp harness project"
   ```

7. Print a summary of what was created and what to do next:
   - "Run `ddev start` to bring up local."
   - "Edit `site.yml` to fill in SSH aliases and remote paths."
   - "Open this project in a fresh Claude Code session — the SessionStart hook will load the new memory + site.yml."

**Do not** scaffold WordPress itself (Bedrock installer, composer init, etc.) — that's project-specific. The user runs `composer create-project roots/bedrock .` or copies from their own template after this command lays down the agent config.
