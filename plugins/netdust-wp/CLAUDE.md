# Netdust WordPress Harness

You are working on a Netdust **WordPress** project. This plugin layers on top of `netdust-core` (which provides memory, hooks, dev-stack conventions, server management, and cross-domain skills) and `netdust-agent` (which provides the coding harness — `harnessed-development`, `testing-workflow`, `shake-out`, and the reviewer agents). If `netdust-core` is not enabled, install it first — `/skill-audit` and `/deploy` won't work otherwise.

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

## What lives in netdust-core / netdust-agent (not here)

For these, see `netdust-core/CLAUDE.md` and `netdust-agent/CLAUDE.md`:

- Per-project memory pattern + Stop-hook tag conventions (netdust-core)
- `dev-stack` skill (DDEV, git, Makefile verbs, `.env`) (netdust-core)
- `secure-server` + `ploi` skills + ploi MCP (netdust-core)
- `research`, `market-research`, `brand-voice`, `marketing` (netdust-core)
- The coding harness — `harnessed-development`, `testing-workflow`, `shake-out`, `test-effectiveness`, `threat-modeling`, `architecture-invariants`, `feature-acceptance`, `compounding` (netdust-agent)
- The 8 coding reviewer agents (netdust-agent) — code review is done by netdust-agent's `reviewer` agent + the specialist reviewers
- `/deploy`, `/skill-audit`, `/pattern-miner`, `/red-test` (netdust-core)
- The 9-method deploy catalog (`memory/deploy-patterns.md`) (netdust-core)
- Voice (`SOUL.md`) and universal rules (`RULES.md`) (netdust-core)

## How this plugin plugs into `harnessed-development`

`netdust-agent:harnessed-development` is the stack-agnostic entry skill that sequences the full harness (design → plan + gates → execute + tests → shake-out → finish). It defers to the loaded stack sub-plugin for stack-specific tools. On a WordPress project, those overrides are:

- **Design stage (Stage 0/1).** WP work does **not** use generic `superpowers:brainstorming`. The framework design skills replace it: `ntdst-architecture` (service lifecycle, DI, boundaries — self-triggers on "add a service" and is "MUST be consulted during implementation planning"), `ntdst-data` (data layer, CPTs, repositories, REST), and `ntdst-patterns` (where files live). Invoke these to design before planning.
- **Plan-time security/data gates.** The `netdust-agent:threat-modeling` + `netdust-agent:architecture-invariants` gates still fire per their triggers; on WP, `wp-security` and `wp-database` self-trigger on PHP edits and reinforce them.
- **Testing (Stage 2).** Already automatic — `netdust-agent:testing-workflow` detects `composer.json + WordPress` and selects Codeception/PHPUnit; `wp-testing` self-triggers on `phpunit.xml` / `Cest` / `WPTestCase`. No manual override needed.
- **Shake-out / review (Stage 3).** Already automatic — `/shakeout` detects WP and adds the 5th reviewer `netdust-wp:ntdst-drift-reviewer` alongside the generic four.

There is no `ntdst-brainstorm` skill (it was never built). For WP design, use the three framework skills above.

## WP-specific rules

See this plugin's `RULES.md`. Universal rules come from netdust-core's `RULES.md`.

## Slash commands (WP-specific)

- `/wp-new-project` — scaffold a new WP project (CLAUDE.md @-import, site.yml, memory/, tasks/, Bedrock-shaped Makefile)
- `/scaffold-plugin` — scaffold a new WP plugin with the ntdst-core architecture
- `/sync-db` — pull remote DB into local DDEV
- `/setup-tests` — set up Codeception + wp-browser test infrastructure
