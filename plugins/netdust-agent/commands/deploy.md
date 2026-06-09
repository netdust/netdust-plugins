---
description: Deploy current project via site.yml's deploy.method (9 methods supported). Never deploys to prod without explicit confirmation.
allowed_tools: ["Bash", "Read", "AskUserQuestion"]
---

Deploy the current project. Read `site.yml` first — it has the deploy method, hosting, SSH alias, and remote paths.

## Required pre-checks

1. **Read `site.yml`**. If it doesn't exist, stop and tell the user to scaffold it via `/wp-new-project` or write one manually.
2. **Surface what you found**: site name, risk level, deploy method, target env(s).
3. **Ask which environment**: `staging` or `production`. Never assume.
4. **If production AND risk is `high`**: require a second explicit "yes deploy to production" confirmation via `AskUserQuestion`. Mention the production URL.
5. **Confirm the current git branch is intended for this environment**. For Stride-style flow: `staging` branch → staging; `main` → production. If branches don't match, ask before proceeding.

## Dispatch by `deploy.method`

| Method | Action |
|---|---|
| `makefile` | Run the `staging_command` or `production_command` from site.yml. Dry-run preview first (`make -n <target>`), then confirm, then execute. |
| `git-push` | Confirm the current branch is pushed to the right remote. Run `git push <remote> <branch>` after confirmation. Mention Ploi's auto-deploy hook will fire. |
| `rsync` | Read the command from site.yml's `deploy.command`. Show it. Ask for confirmation. Then run with `--dry-run` first to preview file changes. Then run for real. |
| `rsync-staging-prod` | Nested config: `deploy.staging.command` / `deploy.production.command`. Same dry-run-then-real flow. |
| `manual` | Print: "This site uses `method: manual`. No automation. SSH to the server or use Combell's file manager: `<from site.yml note>`. I will not act." Stop. |
| `ftp` | Print: "This site uses `method: ftp` via PhpStorm auto-upload. Use PhpStorm's Deployment menu. I will not run an FTP command from here." Stop. |
| `autogit` | Print: "This site uses Combell autogit. Push to `master` branch — Combell's hook will rebuild the symlinks. Confirm before push." Then ask + push. |
| `git-bundle-makefile` | Treat like `makefile` — Makefile wraps the git bundle creation + push. |
| `tbd` | Print: "Deploy method is `tbd`. Update `site.yml` first." Stop. |

## Post-deploy hooks (run after the actual deploy command succeeds)

If `site.yml` has a `deploy.post_deploy_hooks` array, run each entry in order **on the target environment** (via the SSH alias from `hosting.ssh_<env>`).

```yaml
deploy:
  method: git-push
  post_deploy_hooks:
    - cd /home/ploi/<site>/current && php please stache:warm
    - cd /home/ploi/<site>/current && php artisan cache:clear
    - cd /home/ploi/<site>/current && composer install --no-dev --optimize-autoloader
```

Use this for stack-specific finishing steps:

- **Statamic projects** (Peak/Statamic 6): `php please stache:warm` after deploy. Editors see stale fields otherwise.
- **Laravel projects**: `php artisan config:cache && php artisan route:cache`.
- **WP projects** (Bedrock on Ploi auto-deploy): Ploi handles `composer install --no-dev` automatically; usually no post-deploy hooks needed.
- **Custom**: anything project-specific that must run server-side after files land.

If `deploy.post_deploy_hooks` is empty or missing, skip this phase. Don't invent hooks.

## After deploy

- If the deploy ran a real command (not just printed instructions), capture the result.
- Append a tag to the conversation: `DECISION: deployed <project> <env> via <method> at <timestamp>` so the Stop hook lifts it into STATE.md.
- For `production` deploys to `risk: high` sites, also append: `RISK: production deploy on <date> — monitor for next 30 minutes`.

## Hard rules

- **Never** deploy to production without explicit "production" answer to the env question.
- **Never** skip the dry-run preview for rsync (you can wipe files with `--delete`).
- **Never** assume the current branch is the right one for the target env.
- If anything in `site.yml` is missing or `tbd`, stop and ask — do not guess.
