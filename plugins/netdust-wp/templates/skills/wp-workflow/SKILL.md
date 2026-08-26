---
name: wp-workflow
description: Use when work on this site starts, moves between environments, or goes live — starting a feature, starting a bug fix or hotfix, deploying to development or staging, shipping to production, rolling back, refreshing data from production, or answering "what is running on prod". Triggers on "we work on", "fix", "we have a bug", "hotfix", "put it on dev", "test this", "ready for review", "colleagues can look", "push to staging", "deploy", "ship it", "go live", "release", "roll back", "what's on prod", "sync from live".
---

# How work moves to the servers

`site.yml` describes. The `Makefile` executes. This skill decides which target
to call. **Never hardcode a host, path, branch or environment name** — read it:

```bash
scripts/site environments                    # the environment names
scripts/site environments.<env>.branch       # which branch may deploy there
scripts/site deploy.method                   # rsync | git-push
make deployed                                # what runs where, right now
```

## The promotion path

```
feature/* → integration branch → review branch → production branch
```

Linear: a branch never skips a step. The one exception is a hotfix, which
branches from the production branch and merges back down. A site without a
development environment integrates on its review branch; one without production
yet simply has no `ship`.

## What gets said, and what to run

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

**Always run `make deploy-test env=<name>` before a real deploy** and read the
output — especially deletions.

## The rule that matters most

**A bug fix branches from the production branch, never from the integration or
review branch.** Branching elsewhere ships every unfinished change sitting
there. `make hotfix` does this correctly — use it rather than creating the
branch by hand. Afterwards `make finish` merges it back down, or the next
release reverts the fix.

## Production

**Never run `make ship` unless the user asked for it in that turn.** Not because
it follows from an earlier plan. Not because the work is obviously finished.
Every production deploy gets a fresh yes, and the typed confirmation is the
user's to give — never pipe input into it.

## Two rules about drift

1. **Code moves forward only, through git only.** Never `rsync` or edit by hand
   on a server. If it is not committed and pushed, it reaches no server — the
   gate enforces this.
2. **Data moves backward only.** production → staging → development → local.
   `make refresh` and `make pull` do this; nothing pushes data upward.

## What deploys (rsync sites)

`deploy.payload` is a closed list. Nothing outside it crosses the wire — not
`wp/`, not `vendor/`, not uploads, not a third-party plugin. A new custom plugin
or theme must join `deploy.payload` or it will never deploy.

Every payload path must exist locally **and be tracked in git**. An untracked
one deploys as an empty directory, and a rollback then `--delete`s it off the
server. `make test` asserts this.

**Never add `*.map` to `deploy.exclude`.** Font-encoding tables are not
JavaScript source maps; excluding them breaks PDF rendering and leaves stale
copies undeleted.

## What deploys (git-push sites)

A push alone does **not** deploy. The server must pull, and the steps in
`deploy.post_deploy_hooks` must run — typically `composer install --no-dev` and
an FPM reload. With `opcache.validate_timestamps=0` a pull stays invisible until
FPM restarts, while static assets update, which looks like a cache bug and is
not. `make deploy` does all of it.

## Mail on non-production environments

Before refreshing production data into staging or development, ensure
`make block-mail env=<name>` has been run. FluentSMTP's `simulate_emails` lives
in the database, so an import overwrites it; the mu-plugin is file-based and
survives. Production databases carry real addresses and working SMTP
credentials.

## Before claiming a deploy worked

Run `make deployed` and read the sha back. The stamp is the evidence, not the
absence of an error message.
