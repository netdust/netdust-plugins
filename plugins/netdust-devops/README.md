# netdust-devops

The single source of truth for Netdust devops: the branch flow, the deploy
gate and ledger, and the site.yml schema they read.

## Why it exists

The flow was previously spread across four places that disagreed: two `/deploy`
commands with contradicting instructions, a `dev-stack` skill that gave three
different answers about which branch a feature comes from, a `site.yml` schema
two readers interpreted differently, and a
Makefile that projects **copied** at scaffold time and then forked silently.

Agents followed whichever source they read last. So did people.

## What it owns

| | |
|---|---|
| `dist/Makefile.netdust` | the flow, deploy, ledger and health verbs — stack-agnostic |
| `dist/mk/*.mk` | the local loop and data ops per stack: `wp`, `statamic`, `node`, `generic`, plus shared `ddev` |
| `dist/scripts/` | `site` (the one `site.yml` reader), `devops-version`, `work-audit.sh`, the remote helpers and the tooling tests |
| `templates/site.yml.tmpl` | schema 2 — `environments:` is the only place a branch is bound to a server |
| `bin/new-project` | the one scaffolder (call by path — plugin `bin/` is not on `PATH`) |
| `skills/devops/` | the flow, in one voice, with no raw-git recipes |
| `commands/` | `/deploy`, `/new-project`, `/fleet` |

## Vendored, not copied

A project gets the core with `make devops-update`, which writes
`.netdust-devops` — the version plus a checksum per managed file. `make doctor`
then reports two things nothing used to catch:

- this project is **behind** the plugin
- this project has a managed file **edited in place**, which the next update
  would silently revert

A project's own `Makefile` is never touched. Project-specific targets go there.

## Layering

```
Makefile              project — STACK + project-specific targets   (yours)
  └── Makefile.netdust      flow · deploy · ledger · health        (vendored)
        └── mk/$(STACK).mk  local loop · data ops                  (vendored)
```

An unknown `STACK` falls back to `mk/generic.mk` rather than failing to parse.

## Scope

Everything here acts on **one project**, from inside its repo. The verbs read
that project's `site.yml` and touch that project's environments.

This plugin has no opinion about what invokes it — a person, an agent, or a
fleet tool reporting across many repos. It exposes verbs and refuses by name
when a precondition fails; who called is not its concern. Read-only verbs
(`deployed`, `status`, `health`, `doctor`, `audit`) are safe for anything to
run; the ones that write are gated on a clean tree, the right branch, a pushed
HEAD, and — for production — a confirmation typed by a human at a terminal.

## Tests

```bash
bash tests/test-makefile.sh    # structure + behaviour; contacts no server
bash tests/test-work-audit.sh
```

The behaviour tests build a throwaway project with a bare origin and assert
every refusal: the terminal guard, the deploy gate, the rung-branch floor, the
unknown-environment and unknown-stack paths, and the vendoring drift check.
