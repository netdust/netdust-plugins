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
   - Deploy method:
     1. `rsync` — shared Makefile moves a closed payload over SSH (Combell / custom-app)
     2. `git-push` — shared Makefile pushes, pulls on the server, then runs
        `deploy.post_deploy` (Ploi / Bedrock). NOT auto-deploy: a push alone
        does nothing when Ploi has no repository connected to the site.
     3. `ftp` — PhpStorm auto-upload via FTP
     4. `autogit` — Combell autogit symlinks
     5. `manual` — no automation, direct edits
     6. `tbd` — not yet decided

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

5. Set up deploy. Every project that deploys over SSH gets the SAME workflow —
   the gate (clean tree, right branch, HEAD pushed), the ledger (`make deployed`,
   `deployed/<env>` tags, `make rollback`), and the promotion path. Only the
   transport differs.

   Copy `templates/Makefile`, `templates/scripts/` and
   `templates/skills/wp-workflow/` (to `.claude/skills/wp-workflow/`) into the
   project verbatim — none of them carry a project-specific value, so nothing is
   substituted. Then fill `site.yml`'s `environments:` and `deploy:` blocks.

   The skill is what makes "fix this", "push to staging" and "ship it" resolve to
   the right make target. Without it the Makefile still works, but only if
   someone remembers the target names.

   | Method | Scaffold action |
   |---|---|
   | `rsync` | `deploy.method: rsync`. Fill `deploy.payload` with the custom plugins/themes this project owns, plus `wp_path`, `content_dir`, `state_dir` and each environment's `path`. The environment directory is the web root. Supersedes the old `makefile`, `git-bundle-makefile` and `rsync-staging-prod` methods — the git-bundle deploy required a `.git` on the target and did not survive contact with production. |
   | `git-push` | `deploy.method: git-push` (Ploi/Bedrock). Fill `deploy.post_deploy` with the steps a push does not perform — typically `composer install --no-dev --no-interaction` and an FPM reload. A push alone does NOT deploy when Ploi has no repository connected, and FPM with `opcache.validate_timestamps=0` keeps the pull invisible until reloaded. |
   | `ftp` | No Makefile. Deploy is PhpStorm/IDE FTP auto-upload — note in `site.yml` `deploy.note` that there is no CLI deploy. |
   | `autogit` | No Makefile. Combell autogit symlinks handle deploy on push — note the watched branch in `site.yml`. |
   | `manual` | No Makefile. Note in `deploy.note` that deploys are manual — `/deploy` will refuse and tell the user. |


   For any "No Makefile" method, do NOT create a `Makefile`; instead make sure `site.yml` carries enough in `deploy.*` that a later session (or `/deploy`) knows what to do.

5b. **Ask the theme flavour**, and record it in `site.yml` as `stack.theme_flavour`:

   | Flavour | Meaning |
   |---|---|
   | `yootheme` | YOOtheme Pro parent + a thin child theme. The builder renders; styling lives in one LESS style. **Most Netdust marketing sites.** |
   | `custom` | A self-rendering theme with its own templates (Tailwind/Alpine/Vite or similar). |
   | `tbd` | Not decided yet — record it so the gap is explicit. |

   **If `yootheme`, do NOT scaffold a classic/Tailwind theme and convert it later.**
   That conversion is pure deletion — measured once at ~3,900 lines across 26 files
   (10 template files, Tailwind + PostCSS + stylelint configs, `src/css/*`, lockfile
   churn) — and it is entirely avoidable by starting in the right shape.

   Load **`netdust-wp:ntdst-yootheme`** and follow `references/yootheme-less.md`
   ("Converting a classic theme" in reverse — build it born-correct):

   - Child theme with **NO** template files. No `header/footer/front-page/page/
     single/index/404/searchform.php`, no `partials/`, no nav walker or fallback
     menu — they override the parent and bypass the builder.
   - `style.css` header carrying `Template: <parent-slug>` (this is what makes it
     a child; WordPress also needs the file to see the theme at all).
   - `less/theme.<slug>.less` from `templates/theme.child.less.md`.
   - **No CSS toolchain.** No Tailwind, PostCSS or stylelint. Keep Vite + Alpine
     for JS only, and set Vite's `base` to match the real content layout
     (`/content/…` on stackedWP — the Bedrock default `/app/themes/…` is wrong there).
   - `phpstan.neon` must **exclude the YOOtheme parent** (~41 MB of licensed vendor
     code → 1000+ errors otherwise).
   - `.gitignore` ignores `themes/*` and re-includes only the child — the parent is
     licensed, updates in place, and must be installed separately per host.
   - After activating: verify `get_template_directory()` points at the PARENT.
     Activating a child does not rewrite the `template` option, so a theme that was
     ever activated standalone silently never uses the parent.

   Note the E2E/smoke consequence: YOOtheme renders no header until a menu is
   assigned to one of ITS locations (`navbar`), not the theme's own `primary`.
   A fresh install therefore fails a "page has a header/nav" smoke test until a
   menu exists — seed one, or scope the test.

6. Initialize git if `.git/` does not exist, then commit the scaffold:
   ```bash
   git init -q && git add . && git commit -q -m "scaffold: netdust-wp harness project"
   ```

7. Print a summary of what was created and what to do next:
   - "Run `ddev start` to bring up local."
   - "Edit `site.yml` to fill in SSH aliases and remote paths."
   - "Open this project in a fresh Claude Code session — the SessionStart hook will load the new memory + site.yml."

**Do not** scaffold WordPress itself (Bedrock installer, composer init, etc.) — that's project-specific. The user runs `composer create-project roots/bedrock .` or copies from their own template after this command lays down the agent config.
