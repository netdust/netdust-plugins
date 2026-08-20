# Netdust WordPress Harness

You are working on a Netdust **WordPress** project. This plugin layers on top of `netdust-core` (which defines the memory/dev-stack conventions, server management, and cross-domain skills) and `netdust-agent` (which provides the coding harness — `harnessed-development`, `planning`, `building`, `testing-workflow`, the reviewer agents, the `/integration` and `/shakeout` gate commands, and the live hooks: SessionStart injector, Stop-hook tag capture, PreToolUse guard). If `netdust-core` is not enabled, install it first — `/deploy` won't work otherwise.

## Default assumptions (project `CLAUDE.md` can override)

- **Stack**: Bedrock / Composer / PHP 8.2+ / MariaDB (the common case)
- **Non-Bedrock WP** also supported via `site.yml`'s `structure.type: custom-app` — `wp-cli.yml` adjusts the `--path`
- **Framework**: ntdst-core conventions (`mu-plugins/<project>-core/Modules/`, `Stride\Modules\…` namespaces) — see `ntdst-architecture` and `ntdst-patterns`
- **Common plugins**: LearnDash on Stride family, YOOtheme Pro on marketing sites, FluentCRM/FluentForms where forms are needed
- **Standards**: WordPress Coding Standards (WPCS) via PHPCS

## What this plugin adds on top of netdust-core

- **WP discipline skills** — `wp-security`, `wp-database`, `bedrock-composer` (each with RED tests)
- **WP reference skills** — `wp-frontend`, `wp-testing`, `wp-infra`
- **WP plan gate** — `wp-plan-requirements` (fired by `harnessed-development` Stage 1; injects the four security pillars + ntdst-core drift categories into the plan as per-task requirements)
- **ntdst-core framework skills** — `ntdst-architecture`, `ntdst-data`, `ntdst-patterns`, `ntdst-yootheme`
- **WP commands** — `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests`
- **Templates** — `Makefile.tmpl` with Bedrock-shaped deploy variants

## What lives in netdust-core / netdust-agent (not here)

For these, see `netdust-core/CLAUDE.md` and `netdust-agent/CLAUDE.md`:

- Per-project memory pattern + Stop-hook tag conventions (netdust-core)
- `dev-stack` skill (DDEV, git, Makefile verbs, `.env`) (netdust-core)
- `secure-server` + `ploi` skills + ploi MCP (netdust-core)
- `research`, `market-research`, `brand-voice`, `marketing` (netdust-core)
- The coding harness — `harnessed-development`, `planning`, `building`, `testing-workflow`, `threat-modeling`, `architecture-invariants`, `convergence`, `compounding` (netdust-agent 0.19 — thin overlays on superpowers, which does the process work)
- The reviewer agents (netdust-agent): `reviewer`, `security-sentinel`, `code-simplicity-reviewer`, `invariant-auditor`, `shakeout-qa` — plus this plugin's `ntdst-drift-reviewer` on WP
- `/deploy`, `/memory-audit`, `/pattern-miner` (netdust-core); `/skill-audit`, `/integration`, `/shakeout`, `/converge` (netdust-agent)
- The 9-method deploy catalog (`memory/deploy-patterns.md`) (netdust-core)
- Voice (`SOUL.md`) and universal rules (`RULES.md`) (netdust-core)

## How this plugin plugs into `harnessed-development`

`netdust-agent:harnessed-development` is the stack-agnostic **intake router**: it classifies the work (Class A–F, priced by open decisions) and routes it to `planning` or `building`. It does not sequence stages itself, and it is the first action for **any** code-changing request on this stack. It defers to the loaded stack sub-plugin for stack-specific tools. On a WordPress project, those overrides are:

- **Design.** Whether the work brainstorms at all is the ROUTER's decision, never a stack carve-out — Class A/B routes to `planning`, which invokes `superpowers:brainstorming`; Class C/D/E go straight to `building` and brainstorm nothing. Do not skip brainstorming on the grounds that this is WordPress.
- **What the WP skills own inside that.** They **layer on** brainstorming, they do not replace it. Brainstorming + the human own INTENT — what we are building and why. `ntdst-architecture` (service lifecycle, DI, boundaries), `ntdst-data` (data layer, CPTs, repositories, REST) and `ntdst-patterns` (where files live) own the TECHNICAL DESIGN SHAPE on this stack. A netdust skill that restates upstream superpowers content is a defect, not thoroughness.
- **Plan-time security/data gates.** The `netdust-agent:threat-modeling` + `netdust-agent:architecture-invariants` gates still fire per their triggers; on WP, `wp-security` and `wp-database` self-trigger on PHP edits and reinforce them.
- **Testing (Stage 2).** Already automatic — `netdust-agent:testing-workflow` picks the tier and the runner; `wp-testing` self-triggers on `phpunit.unit.xml` / `bin/gate.sh` / `Cest` / `WPTestCase` and routes to the right stack. **The gate stack is primary** (Brain Monkey unit + wp-phpunit integration + Vitest + Playwright, under `composer gate`); Codeception/wp-browser is the LEGACY stack, Stride family only.
- **Shake-out / review (Stage 3).** `/shakeout` detects WP and adds `netdust-wp:ntdst-drift-reviewer` to the panel.

There is no `ntdst-brainstorm` skill and there should not be one — `superpowers:brainstorming` is the workhorse, reached through the router. The three framework skills above are what gets layered on top of it.

## WP-specific rules

See this plugin's `RULES.md`. Universal rules come from netdust-core's `RULES.md`.

## Slash commands (WP-specific)

- `/wp-new-project` — scaffold a new WP project (CLAUDE.md @-import, site.yml, memory/, tasks/, Bedrock-shaped Makefile)
- `/scaffold-plugin` — scaffold a new WP plugin with the ntdst-core architecture
- `/sync-db` — pull remote DB into local DDEV
- `/setup-tests` — route a project to its test stack (gate-stack projects are born gated and need no setup; this scaffolds Codeception + wp-browser for legacy Stride-family projects only)
