---
description: Scaffold a new Netdust WordPress project — delegates the project layer to netdust-devops, then adds the WP-specific harness rules.
allowed_tools: ["Bash", "Read", "Write", "AskUserQuestion"]
---

Scaffold a Netdust **WordPress** project in the current working directory.

**Confirm the directory is empty, or that nothing there will be overwritten.**

## 1. The project layer is not yours to write

Run the devops scaffolder. It owns `site.yml`, `Makefile`, the vendored devops
core, `memory/`, `tasks/`, `.gitignore` and the three rung branches:

```bash
~/.claude/plugins/netdust-devops/bin/new-project <name> --stack=wp --domain=<domain>
```

**Do not hand-write `site.yml` or a `Makefile`.** One renderer, one set of
templates — a hand-written `site.yml` is how the schema forked last time, and
the Makefile is vendored so a fix made once reaches every project. See
`netdust-devops:devops`; load it if it is not already loaded.

## 2. Add the WordPress harness layer

Render `CLAUDE.md` from `~/.claude/plugins/netdust-wp/templates/project-CLAUDE.md.tmpl`
— it carries the WP-specific rules (harnessed-development routing, the
framework skills, the plan gates, the test bindings) and imports
`@~/.claude/plugins/netdust-wp/CLAUDE.md`. This **replaces** the generic
`CLAUDE.md` the scaffolder wrote.

Append `~/.claude/plugins/netdust-wp/templates/gitignore.tmpl` to `.gitignore`.

## 3. Fill in the WordPress-shaped `site.yml` values

Ask via `AskUserQuestion` where you cannot infer:

- `structure.type` — `bedrock` (webroot `web`, WP at `web/wp`, content at
  `web/app`) or `custom-app` (webroot `app`, WP at `app/wp`)
- `structure.wpcli_path` — must match `wp-cli.yml`'s `--path`
- `deploy.wp_path` / `deploy.content_dir` — the same two, **on the server**,
  relative to each environment's `path`
- `deploy.payload` — the closed list of custom plugins and themes this project
  owns. Every entry must exist locally **and be tracked in git**: an untracked
  one deploys as an empty directory and a rollback `--delete`s it off the
  server. `make test` asserts this.
- `deploy.state_dir` — the ledger, **outside every web root**
- `environments.<env>.path` — absolute paths on the server
- `site.risk`

### Deploy method

`rsync` unless the host dictates otherwise. `git-push` for Ploi/Bedrock — and
then `deploy.post_deploy_hooks` must carry what a push does not do (typically
`composer install --no-dev --no-interaction` and an FPM reload). A push alone
does NOT deploy when Ploi has no repository connected, and FPM with
`opcache.validate_timestamps=0` keeps the pull invisible until reloaded.

For a site with no CLI deploy at all (IDE FTP upload, Combell autogit, manual),
say so in `deploy.note` and leave `environments.<env>.path` empty. The verbs
refuse by name rather than pretending.

## 4. Verify, then report

```bash
make doctor
```

Read its output — tools, SSH reachability, payload, devops version — before
telling the user the project is ready. Then report what was created, what is
still `TODO` in `site.yml`, and the next verb.

**The WordPress install itself is not done here.** No composer, no
`wp core install`. `netdust-wp-manager`'s `new-site.sh` does that and calls
this layer for the project config.
