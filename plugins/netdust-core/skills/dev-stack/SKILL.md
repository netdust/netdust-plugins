---
name: dev-stack
description: Use when working in any Netdust project — DDEV environment, git branching, Makefile workflows, generic deploy patterns, .env conventions. Triggers on file edits to Makefile, .env*, .ddev/config.yaml, package.json scripts that look like dev/build/deploy. Activates on keywords DDEV, ddev start, ddev describe, ddev wp, make dev, make save, make deploy, make deploy-test, make ship, make deployed, make health, make rollback, make refresh, make pull, make feature, make hotfix, make promote, make release, make finish, .env, .env.example, staging branch, git-flow, hotfix, deploy gate, deploy ledger. Fires on how the work is actually spoken, not just target names: "we work on X", "fix this", "we have a bug", "hotfix", "put it on dev", "test this", "ready for review", "colleagues can look", "push to staging", "promote", "deploy", "ship it", "go live", "release", "roll it back", "what's on prod", "what's live", "what isn't live yet", "sync from live", "staging is stale", "pull the database". Symptoms include setting up a new project locally, deciding what to commit, choosing a branch to start work on, deploying to staging, shipping to production, rolling back, refreshing a non-production environment from live. Stack-agnostic — applies to WordPress, Statamic, Bun/Node, Laravel projects equally. For WP-specific infra (WP-CLI, Vite-for-WP, Bedrock Makefile patterns), see wp-infra. For the WordPress deploy pipeline itself (gate, ledger, transports), the shared Makefile lives in netdust-wp/templates. For other stacks see /deploy + memory/deploy-patterns.md.
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
| `make save` | Commit current branch with an interactive message. |
| `make feature name=xyz` | Branch `feature/xyz` from the integration branch. |
| `make finish` | Merge one step up the promotion path. On a `hotfix/*` it merges to production and back down. |
| `make hotfix name=xyz` | Branch from **`origin/<production branch>`** — never from the integration branch. |
| `make promote name=xyz` | Send ONE feature to the review branch, leaving the others behind. |
| `make deploy env=<name>` | Gate, transport, stamp. |
| `make deploy-test env=<name>` | The same path with `--dry-run`. Run it first. |
| `make release` | Merge the review branch into the production branch. |
| `make ship` | Production: gate, DB + payload backup, typed confirmation, deploy. |
| `make deployed` | Which commit runs on each environment. |
| `make health` | Fleet check the deploy CANNOT do: ledger vs branch head, per-env drift (someone edited a server), the `/memory/` + `/tasks/` guards, branch topology, and `health.markers` — patched third-party files outside the payload. Read-only. **Run it after ANY third-party plugin update.** |
| `make rollback env=<name>` | Redeploy the previously stamped commit. |
| `make refresh env=<name>` | Copy production's data DOWN to a non-prod environment. |
| `make pull env=<name>` | Same, down to local DDEV. |
| `make gate` | The project's own suite (`commands.gate` in `site.yml`). |
| `make rollback` | Revert production to previous deployment marker. |

## What gets said, and what to run

Read the environment names and branches from `site.yml` — never hardcode them:
`scripts/site environments`, `scripts/site environments.<env>.branch`,
`scripts/site deploy.method`, `make deployed`.

| Said | Run | Lands on |
|---|---|---|
| "we work on X" | `make feature name=X` | nothing yet |
| "put it on dev", "test this" | `make finish`, then `make deploy env=development` | development |
| "push to staging", "ready for review" | merge up, then `make deploy env=staging` | staging |
| "just feature X is ready" | `make promote name=X`, then `make deploy env=staging` | staging |
| "fix", "we have a bug", "hotfix X" | `make hotfix name=X` | nothing yet |
| "that's fixed" (on a hotfix branch) | `make finish` | production + back down |
| "ship it", "go live" | `make ship` | **production** |
| "release" | `make release`, then `make ship` | **production** |
| "what's on prod", "what's live" | `make deployed` | — |
| "what isn't live yet" | `git diff deployed/production` | — |
| "roll it back" | `make rollback env=<name>` | — |
| "sync from live", "staging is stale" | `make refresh env=<name>` | staging or development |
| "pull the database" | `make pull env=production` | local DDEV |

**Always run `make deploy-test env=<name>` first** and read the output,
especially deletions.

### The rule that matters most

**A bug fix branches from the production branch**, never from the integration or
review branch — branching elsewhere ships every unfinished change sitting there.
`make hotfix` does this correctly. Afterwards `make finish` merges it back down,
or the next release reverts the fix.

### Production

**Never run `make ship` unless the user asked for it in that turn.** Not because
it follows from an earlier plan, not because the work looks finished. The typed
confirmation is the user's — never pipe input into it.

### WordPress specifics

- `deploy.payload` is a closed list; a new custom plugin or theme must join it or
  it never deploys. Every payload path must exist locally **and be tracked in
  git** — an untracked one deploys as an empty directory and a rollback
  `--delete`s it off the server. `make test` asserts this.
- **Never add `*.map` to `deploy.exclude`** — font-encoding tables are not
  JavaScript source maps.
- Before `make refresh`, run `make block-mail env=<name>`. FluentSMTP's
  `simulate_emails` lives in the database, so an import overwrites it; the
  mu-plugin is file-based and survives. Production databases carry real
  addresses and working SMTP credentials.

On WordPress projects these come from one shared Makefile
(`netdust-wp/templates/`) that carries no project-specific value — layout,
hosts, branches, transport and payload all resolve from `site.yml`. Only
`deploy.method` differs: `rsync` moves a closed payload, `git-push` pushes then
pulls on the server and runs `deploy.post_deploy_hooks`.

**Three guarantees hold whatever the transport:**

1. **The gate.** A deploy refuses unless the tree is clean, the branch matches
   `environments.<env>.branch`, and `HEAD` is already on `origin`. Nothing
   uncommitted or unpushed reaches a server.
2. **The ledger.** Each deploy stamps `<state_dir>/<env>.json` on the server
   (outside every web root — environment directories are web-served) and moves a
   `deployed/<env>` tag. `make deployed` answers "what is live"; `git diff
   deployed/production` answers "what is not live yet".
3. **Rollback.** Reads the previous stamp, checks that commit out in a throwaway
   worktree and redeploys from it — no server-side git required.

Other stacks (Statamic, Bun, Laravel) keep their own implementations; the verbs
are the same. See `memory/deploy-patterns.md`.

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
make feature name=my-feature
make dev
# ... code ...
make save     # commit
```

### Daily cycle on staging

```bash
make dev      # start local
# ... code ...
make save     # commit
make deploy env=staging
```

### Ship to production

```bash
make finish   # if on a feature branch, merge to staging
# verify staging.<domain> looks right
make release  # merge review branch → production branch
make ship     # deploy to production (backups + typed confirmation)
```

### Hotfix

```bash
git checkout main && git pull
git checkout -b hotfix/critical-bug
# ... fix ...
make save
git checkout main && git merge --no-ff hotfix/critical-bug && git push
make ship                      # production is always `make ship`
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
  method: rsync | git-push | manual | ftp | autogit | tbd
  # retired: makefile, git-bundle-makefile, rsync-staging-prod — the bundle
  # deploy needed a .git on the target, which production usually lacked
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
