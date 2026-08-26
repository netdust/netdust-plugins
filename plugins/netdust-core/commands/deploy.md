---
description: Deploy current project via site.yml's deploy.method. Projects with the shared Makefile deploy through it (gate + ledger); the rest print instructions. Never deploys to prod without explicit confirmation.
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

**If the project has the shared `Makefile` and `scripts/site` (check first), use
them.** They carry the gate and the ledger, which no ad-hoc command does:

| Method | Action |
|---|---|
| `rsync` | `make deploy-test env=<env>` first — always. Show the itemised output, especially deletions. Then `make deploy env=<env>`, or `make ship` for production (it takes a DB + payload backup and prompts for a typed `yes`). |
| `git-push` | `make deploy-test env=<env>`, then `make deploy env=<env>`. The Makefile pushes, pulls on the server, and runs `deploy.post_deploy_hooks`. |

Afterwards run `make deployed` and read the sha back. The stamp is the evidence,
not the absence of an error message.

**A push alone does NOT deploy on Ploi.** Do not tell the user "Ploi's
auto-deploy hook will fire" — verified false on `daan` 2026-08-19: Ploi reported
`has_repository=False`, there is no webhook, and POSTing the deploy endpoint
returns "queued" then does nothing. Worse, PHP-FPM commonly runs
`opcache.validate_timestamps=0`, so a `git pull` stays **invisible** until FPM is
reloaded — static assets update while PHP does not, which looks like a cache bug
and is not. Those steps belong in `deploy.post_deploy_hooks`.

**If the project has no shared Makefile:**

| Method | Action |
|---|---|
| `rsync` | Read the command from `site.yml`. Show it. Run with `--dry-run` first, always — `--delete` can wipe files. Then confirm, then run for real. Offer to install the shared Makefile (`netdust-wp/templates/`), which makes this repeatable and recorded. |
| `manual` | Print: "This site uses `method: manual`. No automation. SSH to the server or use the host's file manager: `<from site.yml note>`. I will not act." Stop. |
| `ftp` | Print: "This site uses `method: ftp` via PhpStorm auto-upload. Use PhpStorm's Deployment menu. I will not run an FTP command from here." Stop. |
| `autogit` | Print: "This site uses Combell autogit. Push to the watched branch — Combell's hook rebuilds the symlinks. Confirm before push." Then ask + push. |
| `tbd` | Print: "Deploy method is `tbd`. Update `site.yml` first." Stop. |

Retired: `makefile`, `git-bundle-makefile` and `rsync-staging-prod`. The
git-bundle deploy required a `.git` on the deploy target. Production usually had
none, so those deploys failed or silently never ran — on VAD Vormingen every
production change went out by hand for months while `make ship` looked correct.
If you meet one of these in an old `site.yml`, migrate it to `rsync`.

## Post-deploy hooks (run after the actual deploy command succeeds)

With the shared Makefile these run automatically as part of `git-push`. Only run
them by hand for a project that has no Makefile: each entry in order **on the
target environment**, in the environment's path, via the SSH alias from
`environments.<env>.ssh_host` (falling back to `deploy.ssh_host`).

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
- **WP projects** (Bedrock on Ploi): `composer install --no-dev --no-interaction`
  AND an FPM reload (`sudo service php8.4-fpm reload`). Do not assume Ploi runs
  these — see above; on `daan` Ploi has never deployed the site at all.
- **Custom**: anything project-specific that must run server-side after files land.

If `deploy.post_deploy_hooks` is empty or missing, skip this phase. Don't invent hooks.

## After deploy

- If the deploy ran a real command (not just printed instructions), capture the result.
- Append a tag to the conversation: `DECISION: deployed <project> <env> via <method> at <timestamp>` so the Stop hook lifts it into STATE.md.
- For `production` deploys to `risk: high` sites, also append: `RISK: production deploy on <date> — monitor for next 30 minutes`.

## Hard rules

- **Never** deploy to production without explicit "production" answer to the env question.
- **Never** skip the dry-run preview for rsync (you can wipe files with `--delete`).
- **Never** pipe a confirmation into `make ship`. The prompt is the human's.
- **Never** assume the current branch is the right one for the target env.
- If anything in `site.yml` is missing or `tbd`, stop and ask — do not guess.
