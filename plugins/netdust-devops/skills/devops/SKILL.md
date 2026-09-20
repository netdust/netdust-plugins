---
name: devops
description: Use for EVERY branch, environment or deploy action in a Netdust project — the make verbs, the promotion path, the deploy gate and ledger, site.yml, .env and DDEV. Load it BEFORE the first `make` call or the first git command on a project carrying site.yml; name it rather than waiting for it to trigger. Triggers on file edits to Makefile, site.yml, .env*, mk/*.mk, .ddev/config.yaml. Activates on make dev, make save, make feature, make hotfix, make promote, make unpromote, make gate, make deploy, make deploy-test, make ship, make deployed, make health, make doctor, make rollback, make refresh, make pull, make audit, make devops-update, ddev start, ddev wp, ddev describe, site.yml, environments, deploy gate, deploy ledger, staging branch, rung branch, git-flow, hotfix, .env.example. Fires on how the work is actually spoken, not just target names — "we work on X", "fix this", "we have a bug", "hotfix", "put it on staging", "test this", "colleagues can look", "take it off staging", "promote", "ship it", "go live", "release", "roll it back", "what's on prod", "what's live", "what isn't live yet", "sync from live", "staging is stale", "pull the database", "set up a new project". Symptoms include starting work, choosing a branch, deciding what to commit, deploying anywhere, rolling back, refreshing a non-production environment, or scaffolding a project. Stack-agnostic — WordPress, Statamic, Node and static projects use the same verbs. For WP-CLI, Bedrock layout and Vite see netdust-wp:wp-infra. For server provisioning see netdust-core:ploi and secure-server.
---

# Netdust devops

One way to set up a project. One set of verbs. The same on every stack.

**The rule that makes this work:** `site.yml` describes, the Makefile executes,
you drive. No host, path, branch or domain is ever written in a command you
type or a Makefile you edit — it is read from `site.yml`, always.

---

## Two layers, and which one you are in

Everything here happens **inside one project repo**: branch, build, deploy,
ship, roll back, pull, refresh, reading that project's `site.yml` and acting
on its environments. A fleet or overview tool that reports across many
projects is a *reader* — it can run the read-only verbs (`deployed`, `status`,
`health`, `doctor`) but the doing happens here, where the gate and the ledger
record it. If you are about to deploy, ship, pull or refresh from somewhere
that is not this project, `cd` here first.

---

## The branch model

Two rungs, one of them disposable. `main` is production, the only branch that
accumulates. `staging` is production plus whatever is promoted — rebuilt from
scratch on every `promote` / `unpromote` / `ship`, never merged into.
**Staging IS the release**: there is no separate branch a "ready" feature
graduates to.

```
main                PRODUCTION   — the only branch that accumulates
  ├── feature/<name>  from origin/main; promoted onto staging, or not
  └── hotfix/<name>   from origin/main; ships straight to production

staging  REVIEW = main + every PROMOTED feature   ← rebuilt on promote/unpromote/ship
```

The exact names come from `site.yml` — `environments.<env>.branch`. Read them
with `scripts/site environments.staging.branch`, never assume. `make status`
prints the topology and the next verb before you type anything.

**A project with fewer servers still keeps both branches.** Declare
`environments.production` with its `branch: main` and leave `path:` out;
`make ship` refuses by name while the ladder stays true. Collapsing staging
onto `main` is how `staging` ends up meaning production.

**A rung is deploy-only.** You never commit on `staging` or `main`. The verbs
are the only door: the Makefile refuses by name, and netdust-agent's
PreToolUse guard denies raw `git commit` / `merge` / `rebase` / `push` /
`checkout -b` on a rung, naming the verb that does it instead.

**A verb that fails is a finding to file, not permission to use raw git** —
if `make promote` breaks, fix the Makefile or report it.

---

## What gets said, and what to run

| Said | Run | Lands on |
|---|---|---|
| "we work on X" | `make feature name=X` | nothing yet |
| "put it on staging", "colleagues can look" | `make promote name=X`, then `make deploy env=staging` | staging |
| "take it off staging" | `make unpromote name=X`, then `make deploy env=staging` | staging |
| "fix this", "we have a bug" | `make hotfix name=X`, then `make ship` | **production** |
| "ship it", "go live" | take what is not shipping off staging, `make deploy env=staging`, look — then `make ship` from the staging checkout | **production** |
| "what's on prod", "what's live" | `make deployed` | — |
| "what isn't live yet" | `git diff deployed/production` | — |
| "roll it back" | `make rollback env=<name>` | — |
| "sync from live", "staging is stale" | `make refresh env=<name>` | staging |
| "pull the database" | `make pull env=production` | local |
| "is anything unpushed?" | `make audit` | — |

**Always run `make deploy-test env=<name>` first** and read the output,
especially the deletions.

### Typed confirmations, and why an agent hands the verb over

**Never run `make ship` unless the user asked for it in that turn.** Not
because it follows from an earlier plan, not because the work looks finished.
`save`, `promote`, `unpromote` and `ship` check for a terminal before doing
anything at all, so `echo yes | make ship` and `make ship < answers` refuse
without touching a server; `rollback` and a `confirm: true` deploy only read
first, then refuse. That check is a speed bump against automation, not a control — a
session that wanted one could hand itself a pty, so **for an agent the rule is
*don't*, not *can't*.** An agent gets the state ready and hands the verb over.

### The rule that matters most

**A bug fix branches from the production branch**, never from staging —
branching there ships every unfinished feature sitting on it. `make hotfix`
reaches production without a staging round; staging is rebuilt over the fix
afterwards, so it is never reverted by the next promote.

---

## The verbs

`make` prints the full list, with your flow position at the top. The ones
that carry a decision:

| Verb | What it does |
|---|---|
| `make feature name=X` | branch `feature/X` from **origin/production** |
| `make hotfix name=X` | branch `hotfix/X` from **origin/production** |
| `make promote name=X` | rebuild staging as production + every promoted feature, X pinned at its current tip |
| `make unpromote name=X` | the same rebuild, without X |
| `make ship` | from the staging checkout, or a `hotfix/*` branch: the checks below, the gate, typed confirm, both backups, deploy, then rebuild staging on the new production |
| `make rollback env=E` | redeploy the previously stamped commit — no server-side git required |

`pull`, `refresh` and `block-mail` exist only on stacks that have data ops;
`make` lists what this project actually has.

**Run `make health` after ANY third-party plugin update** — it is the check a
deploy cannot do.

**What `ship` checks** — three equalities, read from **origin**, since a local
ref proves nothing: HEAD is `origin/staging`, so no local-only commit ships (a `hotfix/*`
branch skips to the last check, and ship pushes it); `deployed/staging`
on origin names this commit (staging was deployed and looked at since its
last rebuild, never before); `origin/production` is an ancestor of HEAD
(staging still contains it). Then `ship` runs `commands.gate` itself — a red
gate ships nothing — and re-checks HEAD and the tree right after, so a gate
that commits or checks out cannot slip a different tree past the checks above.

**What the command line may carry.** The core takes
`name env verb dryrun rung uploads` and refuses anything else **by name, at
parse time**; `make -e` is refused too — every command-line variable reaches
a shell somewhere inside a double-quoted string. A project target with its
own input declares it before the include, or that target starts refusing its
own input:

```make
_CLI_EXTRA := NAME
include Makefile.netdust
```

**When the flow refuses to start.** A `site.yml` still declaring
`environments.development.branch` is the old three-rung topology. `feature`,
`hotfix`, `promote`, `unpromote` and `ship` refuse by name; everything else
keeps working. Migrate by dropping `environments.development`, or go back:

```bash
git log --oneline -- .netdust-devops
git checkout <commit before the update> -- Makefile.netdust mk scripts .netdust-devops
```

---

## Three guarantees, whatever the transport

1. **The gate.** A deploy refuses unless the tree is clean, the branch matches
   `environments.<env>.branch`, and `HEAD` is already on `origin`.
2. **The ledger.** Each deploy stamps `<state_dir>/<env>.json` on the server
   and moves a `deployed/<env>` tag — `make deployed` / `git diff
   deployed/production` read it back.
3. **Rollback.** Checks out the previous stamp in a throwaway worktree and
   redeploys from it — no server-side git required.

Only `deploy.method` differs: `rsync` moves a closed payload; `git-push`
pushes, pulls on the server, and runs `deploy.post_deploy_hooks`.

**A push alone does NOT deploy on Ploi.** Ploi may have no repository
connected, and PHP-FPM commonly runs `opcache.validate_timestamps=0`, so a
`git pull` stays invisible until FPM is reloaded — static assets update while
PHP does not, which looks like a cache bug and is not. Those steps belong in
`deploy.post_deploy_hooks`.

---

## The FIRST bring-up of an environment is not a deploy

A deploy moves the payload — a closed list of **tracked directories**. On an
empty webroot that carries almost nothing that matters: WP core, `vendor/`,
`.env`, `wp-config.php`, `index.php`, `.htaccess`, third-party plugins, uploads
and the database are gitignored, outside the payload, or both. Shipping the
payload alone yields a dead site *and* stamps the ledger as deployed. Enumerate
what you need BEFORE touching the server — DB credentials, GitHub access for
any private composer package, licensed assets, DNS, TLS — in one pass, or a
bring-up turns into a dozen round trips.

The order that works:

```
.env  →  wp core download  →  wp-config.php / index.php / .htaccess
      →  composer install  →  MAIL BLOCK  →  db import  →  search-replace
      →  wp rewrite flush --hard  →  payload deploy  →  licensed assets  →  uploads
```

- **Mail block before the database** — the import brings its source mail settings with it.
- **`composer install --prefer-source` for private repos** — the dist zipball needs an
  API token an SSH deploy key cannot give it.
- **`wp rewrite flush --hard` is mandatory** — search-replace empties `rewrite_rules`.
- **Licensed assets are gitignored, not missing** — look in `content/themes/` and
  `content/plugins/` before asking for a zip; no verb carries them.
- **Diff every route against local before calling it broken** — a 404 often predates the migration.

---

## The project is vendored, not copied

`Makefile.netdust`, `mk/*.mk` and `scripts/*` are **vendored** from this plugin
and listed in `.netdust-devops` with their checksums. They are not yours to
edit.

```bash
make devops-update      # pull the current core in
make doctor             # says if this project is behind, or edited in place
```

A fix belongs upstream in the plugin, where every project gets it. Editing a
vendored file in a project means the next update silently reverts it — which
is exactly how "the deploy template carries the fixes projects had to
re-apply" happened. `make doctor` names any file that has been edited in
place, so it stops being invisible.

**Your project's own `Makefile` is never touched.** Project-specific targets
and overrides go there.

---

## site.yml — schema 2

The one operational description of this project. The Makefile reads it, and so
does anything else that needs to know this project's shape — a session-start
hook, a tool reporting across many projects. Read it before any operational
command.

```bash
scripts/site environments                    # the environment names
scripts/site environments.staging.branch     # one value
scripts/site deploy.method
```

**Retired keys — do not reintroduce them, the Makefile cannot read them:**

| Retired | Replaced by |
|---|---|
| `hosting.remote_path_staging` / `remote_path_production` | `environments.<env>.path` |
| `deploy.staging_command` / `production_command` | the make verbs |
| `deploy.method: makefile`, `git-bundle-makefile`, `rsync-staging-prod` | `rsync` or `git-push` |

`environments:` is the only place a branch is bound to a server. Anything that
resolves a host or path from somewhere else is reading a schema that no longer
exists.

### WordPress specifics

- `deploy.payload` is a closed list; a new custom plugin or theme must join it
  or it never deploys. Every payload path must exist locally **and be tracked
  in git** — an untracked one deploys as an empty directory and a rollback
  `--delete`s it off the server. `make test` asserts this.
- **Never add `*.map` to `deploy.exclude`** — font-encoding tables are not
  JavaScript source maps.
- Before `make refresh`, the mail block is installed automatically.
  FluentSMTP's `simulate_emails` lives in the database, so an import overwrites
  it; the mu-plugin is file-based and survives. Production databases carry real
  addresses and working SMTP credentials.

---

## Starting a project

```bash
~/.claude/plugins/netdust-devops/bin/new-project <name> --stack=wp|statamic|node|generic [--domain=example.com]
```

Plugin `bin/` is not on `PATH` — call it by path, or alias it. `/new-project`
does this for you. Creates `site.yml`, `Makefile`, the vendored core,
`memory/`, `tasks/`, `CLAUDE.md`, and the `main` and `staging` branches — not
the application itself, which is the stack's own installer's job.

Then: fill in the `TODO`s in `site.yml`, add `origin`, push `main staging`,
and run `make doctor`.

### A project that predates this plugin

`--adopt`, from inside it:

```bash
~/.claude/plugins/netdust-devops/bin/new-project <name> --stack=<stack> --adopt
```

It vendors the core and writes a `Makefile`, and leaves `site.yml`, `CLAUDE.md`,
`memory/`, `tasks/` and git exactly as they are. An existing `Makefile` is moved
to `Makefile.pre-devops` rather than deleted — move any project-specific targets
across, then remove it. `make doctor` names whatever `site.yml` is still missing.

After that the project is on the vendored core, so `make devops-update` keeps it
current and `make doctor` reports when it drifts.

---

## `.env` discipline

- **Never commit `.env`.** Only `.env.example`, with placeholder values.
- `.env.example` is the canonical list of required variables.
- Local: copied from `.env.example` on first clone by `make setup`.
- Staging / production: injected by the platform's env-var dashboard (Ploi,
  Combell). Never via committed files.

---

## DDEV

```bash
ddev start / stop / restart        # or: make dev / make stop / make restart
ddev describe                      # status + URLs
ddev ssh                           # shell into the web container
ddev composer <cmd>                # composer in the container
ddev wp <cmd>                      # WP-CLI in the container (WP only)
ddev exec npm install              # any command in the container
ddev exec 'DRY=1 wp eval-file x.php'   # an env var in front of `ddev wp` never reaches the container
```

URLs follow `https://<ddev-project>.ddev.site`; the name is `local.ddev_project`
in `site.yml`.

---

## Anti-patterns

| Smell | Fix |
|---|---|
| Raw `git commit` / `merge` / `push` on a rung branch | the make verb it names. The guard denies these. |
| A feature or hotfix branched from `staging` | `make feature` / `make hotfix` — both branch from origin/production |
| Editing `Makefile.netdust` or `mk/*.mk` in a project | fix it upstream in the plugin, then `make devops-update` |
| Deploying, pulling or refreshing from outside the project | `cd` to the project; the verbs act on the repo they stand in |
| `.env` committed | rotate every secret, then untrack. `.env.example` only |
| Multiple `.env*` variants (`.env.dev`, `.env.prod`) | one `.env.example` + per-environment injection |
| `composer install` / `npm install` outside the container | `ddev composer …` / `ddev exec …` so the version matches the runtime |
| Manual file upload to a server | `make deploy env=<name>` — it gates and stamps |
| A session ends with commits unpushed | `make audit` |
| `ddev wp` on a non-WP project | WP-CLI is WP-only |

---

## See also

- `netdust-wp:wp-infra` — WP-CLI, Bedrock layout, Vite in a WP theme
- `netdust-core:ploi` — provisioning and managing the servers these deploy to
- `netdust-core:secure-server` — hardening a fresh VPS
