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

5. Set up deploy according to the chosen method. Every one of the 9 methods has a defined outcome — never leave the user without an explanation:

   | Method | Scaffold action |
   |---|---|
   | `makefile` | Copy the **VARIANT: makefile** section from `templates/Makefile.tmpl` (the whole section between its banner and the next), substitute the `{{...}}` placeholders from `site.yml`. |
   | `git-bundle-makefile` | Copy the **VARIANT: git-bundle-makefile** section, substitute placeholders. |
   | `git-push` | Copy the **VARIANT: git-push** section, substitute placeholders (incl. `{{STAGING_BRANCH}}` / `{{PRODUCTION_BRANCH}}`). |
   | `rsync` | No Makefile. Deploy is a direct `rsync` — record the exact `rsync` command in `site.yml` `deploy.staging_command` / `production_command`. Tell the user it runs via `/deploy`. |
   | `rsync-staging-prod` | No Makefile. Same as `rsync` but with separate nested staging/production paths — record both commands in `site.yml`. |
   | `ftp` | No Makefile. Deploy is PhpStorm/IDE FTP auto-upload — note in `site.yml` `deploy.note` that there is no CLI deploy; the IDE handles it. |
   | `autogit` | No Makefile. Combell autogit symlinks handle deploy on push — note the watched branch in `site.yml`. |
   | `manual` | No Makefile. Note in `site.yml` `deploy.note` that deploys are manual/direct edits — `/deploy` will refuse and tell the user. |
   | `tbd` | No Makefile. Write `deploy.method: tbd` and a `deploy.note: "deploy method not yet decided — set before first ship"` so the gap is explicit, not silent. |

   For any "No Makefile" method, do NOT create a `Makefile`; instead make sure `site.yml` carries enough in `deploy.*` that a later session (or `/deploy`) knows what to do.

6. Initialize git if `.git/` does not exist, then commit the scaffold:
   ```bash
   git init -q && git add . && git commit -q -m "scaffold: netdust-wp harness project"
   ```

7. Print a summary of what was created and what to do next:
   - "Run `ddev start` to bring up local."
   - "Edit `site.yml` to fill in SSH aliases and remote paths."
   - "Open this project in a fresh Claude Code session — the SessionStart hook will load the new memory + site.yml."

**Do not** scaffold WordPress itself (Bedrock installer, composer init, etc.) — that's project-specific. The user runs `composer create-project roots/bedrock .` or copies from their own template after this command lays down the agent config.
