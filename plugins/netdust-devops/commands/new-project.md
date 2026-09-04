---
description: Scaffold a new Netdust project — site.yml, Makefile, vendored devops core, memory/, tasks/, CLAUDE.md, and the three rung branches.
allowed_tools: ["Bash", "Read", "Write", "AskUserQuestion"]
---

Scaffold the Netdust project layer. Load the `netdust-devops:devops` skill
first if it is not already loaded.

**Confirm the target directory is empty, or that nothing there will be
overwritten.**

## 1. Ask, via `AskUserQuestion`

- **name** — lowercase, letters/digits/dashes
- **stack** — `wp` · `statamic` · `node` · `generic`
- **production domain**
- **risk** — `low` · `medium` · `high`

## 2. Run the scaffolder

```bash
~/.claude/plugins/netdust-devops/bin/new-project <name> --stack=<stack> --domain=<domain>
```

Plugin `bin/` is not on `PATH`; call it by path, or alias it once in your
shell profile.

It renders `site.yml` and `Makefile` from the plugin templates, vendors the
devops core, creates `memory/`, `tasks/`, `CLAUDE.md` and `.gitignore`, and
creates the `development` / `staging` / `main` branches.

**Do not hand-write any of these files.** One renderer, one set of templates —
a hand-written `site.yml` is how the schema forked last time.

## 3. Fill in what the scaffolder cannot know

Walk the `TODO`s in `site.yml` with the user:

- `environments.<env>.path` — absolute paths on the server
- `deploy.ssh_host` — the SSH alias
- `deploy.state_dir` — the ledger, **outside every web root**
- `deploy.payload` — for `rsync`: the closed list of directories that deploy.
  Every entry must exist locally **and be tracked in git**.
- `site.description`, `site.risk`

Leave `environments.production.path` out if production is not provisioned yet.
Keep the entry and its `branch: main` — `make ship` refuses by name, and the
promotion ladder stays intact.

## 4. Wire up git and verify

```bash
git remote add origin <url>
git push -u origin main staging development
make doctor
```

`make doctor` checks tools, SSH reachability, the payload, and the vendored
devops version. Read its output before telling the user the project is ready.

## 5. Report

What was created, what is still `TODO` in `site.yml`, and the next verb
(`make setup`, then `make dev`).

**The application itself is not installed by this.** No composer, no WordPress
install, no `ddev start`. For a WordPress site, `netdust-wp-manager`'s
`new-site.sh` does that and calls this for the project layer.
