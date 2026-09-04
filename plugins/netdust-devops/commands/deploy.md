---
description: Deploy the current project through its Makefile — gate, transport, stamp. Reads site.yml; never reaches production without an explicit ask in this turn.
allowed_tools: ["Bash", "Read", "AskUserQuestion"]
---

Deploy the project in the current working directory. Load the
`netdust-devops:devops` skill first if it is not already loaded.

## Before anything

1. **Confirm you are in a project, not the fleet manager.** A `site.yml` and a
   `Makefile` at the repo root. If you are in `netdust-wp-manager`, stop: the
   fleet layer never deploys. Name the project and `cd` there.

2. **Read the state, do not assume it.**
   ```bash
   make status        # branch, flow position, what runs on each environment
   ```
   Surface: project name, risk, current branch, target environment, and what
   is currently deployed there.

3. **Ask which environment.** Never assume. The valid names come from
   `scripts/site environments` — not from memory, and not from this file.

## Deploying

**Always dry-run first, and read the output — especially the deletions.**

```bash
make deploy-test env=<env>
```

Show the itemised output. A deletion the user did not expect is the signal to
stop and ask, not to proceed carefully.

Then:

```bash
make deploy env=<env>
```

Afterwards, read the stamp back:

```bash
make deployed
```

The stamp is the evidence a deploy landed. The absence of an error message is
not.

## Production

`make ship` — and **only when the user asked for it in this turn.** Not
because it follows from an earlier plan, not because staging looks right.

It checks for a terminal first, then gates, backs up the data and the payload,
and prompts for a typed `yes`. That confirmation is the user's:
**never pipe or redirect input into it.** If you are running without a
terminal, say so and stop — do not look for a way around it.

For a `risk: high` site, confirm once more via `AskUserQuestion` before
running it, naming the production URL.

## When something refuses

The verbs refuse by name and say what to run instead. That message is the
answer — follow it. **A verb that fails is a finding to file, not permission
to use raw git.** Reaching around the flow with `git push` or `git merge` is
what put the branches in the state this tooling exists to fix, and the
netdust-agent guard will deny it anyway.

If the refusal looks wrong, report it with the exact output. Do not work
around it.
