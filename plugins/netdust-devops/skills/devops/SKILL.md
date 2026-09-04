---
name: devops
description: Use for EVERY branch, environment or deploy action in a Netdust project — the make verbs, the promotion path, the deploy gate and ledger, site.yml, .env and DDEV. Load it BEFORE the first `make` call or the first git command on a project carrying site.yml; name it rather than waiting for it to trigger. Triggers on file edits to Makefile, site.yml, .env*, mk/*.mk, .ddev/config.yaml. Activates on make dev, make save, make feature, make hotfix, make finish, make promote, make release, make deploy, make deploy-test, make ship, make deployed, make health, make doctor, make rollback, make refresh, make pull, make audit, make devops-update, ddev start, ddev wp, ddev describe, site.yml, environments, deploy gate, deploy ledger, staging branch, rung branch, git-flow, hotfix, .env.example. Fires on how the work is actually spoken, not just target names — "we work on X", "fix this", "we have a bug", "hotfix", "put it on dev", "test this", "ready for review", "colleagues can look", "push to staging", "promote", "deploy", "ship it", "go live", "release", "roll it back", "what's on prod", "what's live", "what isn't live yet", "sync from live", "staging is stale", "pull the database", "set up a new project". Symptoms include starting work, choosing a branch, deciding what to commit, deploying anywhere, rolling back, refreshing a non-production environment, or scaffolding a project. Stack-agnostic — WordPress, Statamic, Node and static projects use the same verbs. For WP-CLI, Bedrock layout and Vite see netdust-wp:wp-infra. For server provisioning see netdust-core:ploi and secure-server.
---

# Netdust devops

One way to set up a project. One set of verbs. The same on every stack.

**The rule that makes this work:** `site.yml` describes, the Makefile executes,
you drive. No host, path, branch or domain is ever written in a command you
type or a Makefile you edit — it is read from `site.yml`, always.

---

## Two layers, and which one you are in

Everything here happens **inside one project repo**: branch, build, deploy,
ship, roll back, pull, refresh. The verbs read that project's `site.yml` and
act on that project's environments.

A fleet or overview tool that reports across many projects is a *reader*. It
can run the read-only verbs (`deployed`, `status`, `health`, `doctor`) and it
can show you what needs doing — but the doing happens here, in the project,
where the gate and the ledger record it. If you are about to deploy, ship,
pull or refresh from somewhere that is not this project, `cd` here first.

---

## The branch model

Three rungs. One branch per environment, named for it. This is the only
topology; there is no second version of it anywhere.

```
main            PRODUCTION   — never worked in directly
  └── staging   REVIEW       — client-visible; a deploy here is outward-facing
        └── development      INTEGRATION — daily work lands here
              ├── feature/<name>   from development, merged back to development
              └── hotfix/<name>    from main, merged to main AND back down
```

The exact names come from `site.yml` — `environments.<env>.branch`. Read them
with `scripts/site environments.staging.branch`, never assume. `make status`
prints the whole topology and the next verb before you type anything.

**A project with fewer servers still keeps the rungs.** Declare
`environments.production` with its `branch: main` and leave `path:` out;
`make ship` refuses by name while the ladder stays true. Collapsing two rungs
onto one branch is how `staging` ends up meaning `main`.

**A rung is deploy-only.** You never commit on `development`, `staging` or
`main`. The verbs are the only door, and two machines hold it: the Makefile
refuses by name, and netdust-agent's PreToolUse guard denies raw
`git commit` / `merge` / `rebase` / `push` / `checkout -b` on a rung, naming
the verb that does it instead.

**A verb that fails is a finding to file, not permission to use raw git.**
If `make finish` breaks, fix the Makefile or report it. Reaching around it is
how the branches became a mess in the first place.

---

## What gets said, and what to run

| Said | Run | Lands on |
|---|---|---|
| "we work on X" | `make feature name=X` | nothing yet |
| "put it on dev", "test this" | `make finish`, then `make deploy env=development` | development |
| "ready for review", "colleagues can look" | `make finish`, then `make deploy env=staging` | staging |
| "just feature X is ready" | `make promote name=X`, then `make deploy env=staging` | staging |
| "fix this", "we have a bug", "hotfix X" | `make hotfix name=X` | nothing yet |
| "that's fixed" (on a hotfix branch) | `make finish` | main + back down |
| "ship it", "go live" | `make ship` | **production** |
| "release" | `make release`, then `make ship` | **production** |
| "what's on prod", "what's live" | `make deployed` | — |
| "what isn't live yet" | `git diff deployed/production` | — |
| "roll it back" | `make rollback env=<name>` | — |
| "sync from live", "staging is stale" | `make refresh env=<name>` | staging or development |
| "pull the database" | `make pull env=production` | local |
| "is anything unpushed?" | `make audit` | — |

**Always run `make deploy-test env=<name>` first** and read the output,
especially the deletions.

### Production

**Never run `make ship` unless the user asked for it in that turn.** Not
because it follows from an earlier plan, not because the work looks finished.
The typed confirmation is the user's. It cannot be piped: `make ship` checks
for a terminal before it does anything at all, so `echo yes | make ship` and
`make ship < answers` both refuse without touching a server.

### The rule that matters most

**A bug fix branches from the production branch**, never from the integration
or review branch — branching elsewhere ships every unfinished change sitting
there. `make hotfix` does this correctly. `make finish` then merges it back
down so the fix is not reverted by the next release.

---

## The verbs

| Verb | What it does |
|---|---|
| `make` | the verb list, with your flow position at the top |
| `make setup` | first clone: `.env`, containers, dependencies |
| `make dev` | start the local loop |
| `make save` | commit the current branch |
| `make feature name=X` | branch `feature/X` from the integration branch |
| `make hotfix name=X` | branch `hotfix/X` from **origin/production** |
| `make finish` | merge one step up. On a `hotfix/*`: to production and back down |
| `make promote name=X` | send ONE feature to review, leaving the others behind |
| `make release` | merge review into production |
| `make deploy env=E` | gate, transport, stamp |
| `make deploy-test env=E` | the same path, `--dry-run` |
| `make ship` | production: terminal check, gate, data + payload backup, typed confirm, deploy |
| `make rollback env=E` | redeploy the previously stamped commit |
| `make deployed` | which commit runs on each environment |
| `make status` | branch, flow position, what runs where |
| `make health` | ledger vs branch head, per-env drift, deploy guards, topology, patched files |
| `make doctor` | tools, SSH reachability, payload, devops version |
| `make audit` | work that exists only on this machine |
| `make test` | the deploy tooling's own tests — contacts no server |
| `make gate` | this project's suite (`commands.gate`) |
| `make pull env=E` | copy an environment's data down to local |
| `make refresh env=E` | copy production's data down to a non-production environment |
| `make devops-update` | re-vendor the shared core from the plugin |

`pull`, `refresh` and `block-mail` exist only on stacks that have data ops.
`make` lists what this project actually has.

**Run `make health` after ANY third-party plugin update** — it is the check a
deploy cannot do.

---

## Three guarantees, whatever the transport

1. **The gate.** A deploy refuses unless the tree is clean, the branch matches
   `environments.<env>.branch`, and `HEAD` is already on `origin`. Nothing
   uncommitted or unpushed reaches a server.
2. **The ledger.** Each deploy stamps `<state_dir>/<env>.json` on the server
   (outside every web root — environment directories are web-served) and moves
   a `deployed/<env>` tag. `make deployed` answers "what is live";
   `git diff deployed/production` answers "what is not live yet".
3. **Rollback.** Reads the previous stamp, checks that commit out in a
   throwaway worktree and redeploys from it — no server-side git required.

Only `deploy.method` differs: `rsync` moves a closed payload; `git-push`
pushes, pulls on the server, and runs `deploy.post_deploy_hooks`.

**A push alone does NOT deploy on Ploi.** Ploi may have no repository
connected, and PHP-FPM commonly runs `opcache.validate_timestamps=0`, so a
`git pull` stays invisible until FPM is reloaded — static assets update while
PHP does not, which looks like a cache bug and is not. Those steps belong in
`deploy.post_deploy_hooks`.

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
does this for you.

Creates `site.yml`, `Makefile`, the vendored core, `memory/`, `tasks/`,
`CLAUDE.md`, and the three rung branches. It does **not** install the
application — that is the stack's own installer, which calls this for the
project layer so there is one renderer and one set of templates.

Then: fill in the `TODO`s in `site.yml`, add `origin`, push the three rungs,
and run `make doctor`.

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
| Reaching for raw git because a verb failed | file the failure; fix the verb |
| A hotfix branched from `development` or `staging` | `make hotfix` — it branches from origin/production |
| Editing `Makefile.netdust` or `mk/*.mk` in a project | fix it upstream in the plugin, then `make devops-update` |
| Deploying, pulling or refreshing from outside the project | `cd` to the project; the verbs act on the repo they stand in |
| `.env` committed | rotate every secret, then untrack. `.env.example` only |
| Multiple `.env*` variants (`.env.dev`, `.env.prod`) | one `.env.example` + per-environment injection |
| `composer install` / `npm install` outside the container | `ddev composer …` / `ddev exec …` so the version matches the runtime |
| Manual file upload to a server | `make deploy env=<name>` — it gates and stamps |
| Branch named `develop` | the rung is `development`, and the name comes from `site.yml` |
| A session ends with commits unpushed | `make audit` |
| `ddev wp` on a non-WP project | WP-CLI is WP-only |

---

## See also

- `netdust-wp:wp-infra` — WP-CLI, Bedrock layout, Vite in a WP theme
- `netdust-core:ploi` — provisioning and managing the servers these deploy to
- `netdust-core:secure-server` — hardening a fresh VPS
