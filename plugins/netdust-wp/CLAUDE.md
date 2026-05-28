# Netdust WordPress Harness

You are working on a Netdust **WordPress** project. This plugin layers on top of `netdust-core` (which provides memory, hooks, dev-stack conventions, server management, code review, and cross-stack skills). If `netdust-core` is not enabled, install it first — `/skill-audit` and `/deploy` won't work otherwise.

## Default assumptions (project `CLAUDE.md` can override)

- **Stack**: Bedrock / Composer / PHP 8.2+ / MariaDB (the common case)
- **Non-Bedrock WP** also supported via `site.yml`'s `structure.type: custom-app` — `wp-cli.yml` adjusts the `--path`
- **Framework**: ntdst-core conventions (`mu-plugins/<project>-core/Modules/`, `Stride\Modules\…` namespaces) — see `ntdst-architecture` and `ntdst-patterns`
- **Common plugins**: LearnDash on Stride family, YOOtheme Pro on marketing sites, FluentCRM/FluentForms where forms are needed
- **Standards**: WordPress Coding Standards (WPCS) via PHPCS

## What this plugin adds on top of netdust-core

- **WP discipline skills** — `wp-security`, `wp-database`, `bedrock-composer` (each with RED tests)
- **WP reference skills** — `wp-frontend`, `wp-testing`, `wp-infra`
- **ntdst-core framework skills** — `ntdst-architecture`, `ntdst-data`, `ntdst-patterns`, `ntdst-yootheme`
- **WP commands** — `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests`
- **Templates** — `Makefile.tmpl` with Bedrock-shaped deploy variants

## What lives in netdust-core (not here)

For these, see `netdust-core/CLAUDE.md`:

- Per-project memory pattern + Stop-hook tag conventions
- `dev-stack` skill (DDEV, git, Makefile verbs, `.env`)
- `secure-server` + `ploi` skills + ploi MCP
- `research`, `market-research`, `brand-voice`, `marketing`
- `code-audit`, `shake-out`, `testing-workflow`
- 7 code review agents
- `/deploy`, `/skill-audit`, `/pattern-miner`, `/red-test`
- The 9-method deploy catalog (`memory/deploy-patterns.md`)
- Voice (`SOUL.md`) and universal rules (`RULES.md`)

## WP-specific rules

See this plugin's `RULES.md`. Universal rules come from netdust-core's `RULES.md`.

## Slash commands (WP-specific)

- `/wp-new-project` — scaffold a new WP project (CLAUDE.md @-import, site.yml, memory/, tasks/, Bedrock-shaped Makefile)
- `/scaffold-plugin` — scaffold a new WP plugin with the ntdst-core architecture
- `/sync-db` — pull remote DB into local DDEV
- `/setup-tests` — set up Codeception + wp-browser test infrastructure
