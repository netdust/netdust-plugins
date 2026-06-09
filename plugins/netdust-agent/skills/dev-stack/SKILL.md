---
name: dev-stack
description: Use when working in any Netdust project — DDEV environment, git branching, Makefile workflows, generic deploy patterns, .env conventions. Triggers on file edits to Makefile, .env*, .ddev/config.yaml, package.json scripts that look like dev/build/deploy. Fires on 'fresh clone / new laptop setup — how do I get the dev env up', 'which make target gets the dev environment running', 'how do I start the dev env', 'which branch do I start work on', 'what's the branching here'. Activates on keywords DDEV, ddev start, ddev describe, ddev wp, make dev, make save, make deploy, make ship, make feature, make finish, .env, .env.example, staging branch, git-flow, hotfix. Symptoms include setting up a new project locally on a fresh clone or new laptop, deciding what to commit, choosing a branch to start work on, deploying to staging, rolling back. Stack-agnostic — applies to WordPress, Statamic, Bun/Node, Laravel projects equally. For WP-specific infra (WP-CLI, Vite-for-WP, Bedrock Makefile patterns), see wp-infra. For stack-specific deploy variants, see the /deploy command + memory/deploy-patterns.md.
---

# Netdust dev-stack

The shared dev-environment baseline across all Netdust projects, regardless of stack. WordPress, Statamic, Bun, Laravel — the local-loop, the branching, the Makefile shape, the `.env` discipline are the same.

## Local-loop topology

```
Browser
  → DDEV (Docker: web + database + mailhog)
     OR Bun/Node dev server (for non-DDEV projects like Folio)
  → optional Vite (HMR, asset bundling)
```

DDEV is the default. Some Bun/Node projects skip DDEV entirely (Folio, the dashboard). Statamic projects use DDEV. WP projects use DDEV.

## DDEV cheatsheet

```bash
ddev start / stop / restart        # container lifecycle
ddev describe                      # status + URLs (site, mailhog, phpMyAdmin)
ddev ssh                           # shell into web container
ddev composer <command>            # composer in container (PHP projects)
ddev wp <command>                  # WP-CLI in container (WP projects only)
ddev exec npm install              # run any command in the container
ddev export-db --file=backup.sql.gz
ddev import-db --src=backup.sql
ddev mysql                         # interactive MySQL
ddev logs -f                       # tail container logs
```

URLs follow `https://<ddev-project>.ddev.site`. Per-project, the project name is in `.ddev/config.yaml` `name:` and in `site.yml` `local.ddev_project`.

## Git branch strategy

```
main (protected, production)
  └── staging (active development base)
        ├── feature/<name>     (from staging, merged back to staging)
        └── hotfix/<name>      (from main, merged to main AND staging)
```

- All merges use `--no-ff` to preserve history.
- Direct commits to `main` are blocked (branch protection where supported).
- `staging` is the working branch — daily work lives here.
- `feature/*` for non-trivial work, deleted after merge.
- `hotfix/*` only when prod is on fire — cherry-pick back to staging too.

## Makefile contract — Netdust convention

Every Netdust project's `Makefile` exposes the same top-level verbs, regardless of stack:

| Command | Intent |
|---|---|
| `make dev` | Start the local loop (DDEV up + watcher/HMR). |
| `make save` (alias `make s`) | Commit current branch with an interactive message + push. |
| `make feature NAME=xyz` | `git checkout staging && git pull && git checkout -b feature/xyz`. |
| `make finish` | Merge current feature → staging with `--no-ff`, push, delete branch. |
| `make deploy` (alias `make d`) | Deploy current branch to staging (per `site.yml`'s `deploy.method`). |
| `make ship` | Deploy to production after merging staging → main. Requires explicit confirmation. |
| `make rollback` | Revert production to previous deployment marker. |

Implementations differ per stack (Bedrock git-bundle, Statamic rsync, Bun single-binary scp, etc.). The verbs are the same. See `memory/deploy-patterns.md` for the 9 actual deploy method variants.

## `.env` discipline

- **Never commit `.env`.** Only `.env.example` with placeholder values.
- Each environment has its own `.env`:
  - **Local**: copied from `.env.example` on first clone.
  - **Staging / production**: deployed via the platform's env-var dashboard (Ploi, Combell). Not via committed files.
- `.env.example` is committed and is the canonical list of required vars.
- On first clone after `git clone`: `cp .env.example .env`, fill in, then `ddev start`.

## Common workflows

### Starting new work

```bash
git checkout staging && git pull
make feature NAME=my-feature
make dev
# ... code ...
make save     # commit + push
```

### Daily cycle on staging

```bash
make dev      # start local
# ... code ...
make save     # commit + push to staging
make deploy   # deploy staging branch to staging environment
```

### Ship to production

```bash
make finish   # if on a feature branch, merge to staging
# verify staging.<domain> looks right
make ship     # merge staging → main, deploy to production (with confirmation)
```

### Hotfix

```bash
git checkout main && git pull
git checkout -b hotfix/critical-bug
# ... fix ...
make save
git checkout main && git merge --no-ff hotfix/critical-bug && git push
make deploy ENV=production     # or `make ship`
git checkout staging && git merge --no-ff hotfix/critical-bug && git push  # backport
```

## Anti-patterns

| Smell | Fix |
|---|---|
| Direct commits to `main` | Always through staging. `make feature` + `make finish` or hotfix flow. |
| `.env` committed | Rotate every secret, then untrack. Use `.env.example` only. |
| Running `composer install` / `npm install` outside the container | Use `ddev composer …` / `ddev exec npm install` so the version matches the runtime. |
| Manual file upload deployment | Use `/deploy` (reads site.yml's deploy.method, dispatches). |
| Branch named `develop` | Netdust convention is `staging`, not `develop`. |
| Multiple `.env*` variants in repo (`.env.dev`, `.env.prod`) | One `.env.example` + per-environment runtime injection. |
| `ddev wp` on a non-WP project | WP-CLI is WP-only. Use `ddev composer …` or `ddev exec …` for other stacks. |

## site.yml — operational config (per project)

Every Netdust project has a `site.yml` at the repo root. Read it before any operational command.

```yaml
site:
  name: <project>
  domain: <prod-domain>
  risk: low | medium | high
  description: "..."

structure:
  type: bedrock | custom-app | custom-site | statamic | bun-react | …
  webroot: <relative path>

hosting:
  provider: ploi | combell | other
  ssh_staging: <ssh alias>
  ssh_production: <ssh alias>
  remote_path_staging: <path>
  remote_path_production: <path>

deploy:
  method: makefile | git-push | rsync | rsync-staging-prod | manual | ftp | autogit | git-bundle-makefile | tbd
  # method-specific config follows...

local:
  ddev_project: <name>
  start: ddev start
  url: https://<name>.ddev.site
```

The `/deploy` command reads `deploy.method` and dispatches. `/wp-new-project` (and future `/bun-new-project`, etc.) scaffolds this file.

## See also

- `memory/deploy-patterns.md` — the 9 deploy methods + per-site mapping
- `/deploy` — slash command that dispatches per `site.yml`
- `wp-infra` (in `netdust-wp`) — WP-CLI, Vite-for-WP, Bedrock Makefile patterns
- `secure-server` — when standing up a fresh VPS to host these
- `ploi` — when the hosting provider is Ploi
