---
description: The weekly fleet read-out — production health, what needs updating, and open todos across all projects. Read-only; never writes into a project.
allowed_tools: ["Bash", "Read"]
---

The weekly sweep across every managed site. Load the `netdust-devops:devops`
skill first if it is not already loaded.

**This command reads and reports. It never writes into a project.** When
something needs doing, name the project and hand over the command to run
*there* — do not run it from here. The one exception is remote WordPress
plugin updates, which touch servers rather than project repos.

Run from `netdust-wp-manager`.

## 1. Health

For each configured site, report:

- what is deployed on production, and whether it matches the branch head
- any environment drift (someone edited a server by hand)
- anything unreachable

The per-project source of truth is `make health` run **in that project**.
Where the fleet layer has a cached view, say it is cached and when it was
taken.

## 2. Updates

```bash
./scripts/plugin-update --sla      # lists updates, confirms per site
```

This is the one fleet verb that writes. It asks per site; let it. Report what
was updated and what was skipped.

**After any third-party plugin update, `make health` in that project** — it
catches a patched file an update reverted, which no update log shows.

## 3. Todos

Collect, per project:

- `tasks/todo.md` — the active list
- `memory/STATE.md` — open decisions and risks

Report them grouped by project, newest first. Do not edit them from here.

## 4. Hand-off

End with a short list of "what needs doing, and where":

```
acme        staging 6 commits behind main    → cd acme && make deploy env=staging
vad         patched file reverted on prod    → cd vad && make health
josworld    3 plugin updates pending         → done this sweep
```

Each line names a project and one command to run in it. That is the deliverable
— not a wall of status.
