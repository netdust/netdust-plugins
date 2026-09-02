# Netdust WordPress Harness

You are working on a Netdust **WordPress** project. This plugin layers on top of `netdust-core` (which defines the memory/dev-stack conventions, server management, and cross-domain skills) and `netdust-agent` (which provides the coding harness — `harnessed-development`, `planning`, `building`, `testing-workflow`, the reviewer agents, the `/integration` and `/shakeout` gate commands, and the live hooks: SessionStart injector, Stop-hook tag capture, PreToolUse guard). If `netdust-core` is not enabled, install it first — `/deploy` won't work otherwise.

## `site.yml` is the operating context — not the entry point

**The entry point for any code-changing request is `netdust-agent:harnessed-development`**,
which classifies the work and routes it. That is unchanged here and this file does not
compete with it. `site.yml` is what you read to ACT correctly once routed — and before
running anything path-dependent or destructive, at any stage.

Every Netdust WP project has a `site.yml` in its root. It is the single source of
truth for how that site is built, hosted and deployed. Do not infer these from the tree.

| Field | Why it decides your next command |
|---|---|
| `structure.type` | `bedrock` \| `custom-app` \| `custom-site` — sets `wpcli_path`, the webroot, and whether `config/environments/` exists |
| `structure.wpcli_path` | what `--path` every WP-CLI call needs (`web/wp`, `app/wp`, or `.`) |
| `structure.theme_flavour` | `yootheme` \| `custom` \| `tbd` — there is no default theme base on this fleet |
| `site.risk` | `high` means triple-check every destructive operation |
| `hosting.provider` | `ploi` \| `combell` \| other — different SSH and deploy shape |
| `deploy.method` | one of the canonical 9; `/deploy` dispatches on it |

Then `memory/STATE.md` for where the project actually stands.

## Where knowledge lives (three layers, do not conflate)

- **A — atomic recall**: `~/.claude/projects/<slug>/memory/`, injected at session start.
- **B — fleet / business**: `~/Sites/netdust-wp-manager/memory/` — cross-site
  priorities, deals, cross-project rules, `GLOBAL.md`, `projects/<site>/STATE.md`.
  **Stefan writes this by hand.** Update it only when something *fleet-level*
  changed, and commit from that workspace.
- **C — per-project**: `<project>/memory/STATE.md` · `lessons.md` — written
  automatically by the Stop hook from `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tags.

A single site's decision is Layer C and lands by itself. Do not hand-write it into B.

`netdust-wp-manager` is the toolbox workspace and the site registry — shared scripts
and the fleet brain. Per-project config and memory live in the project, never there.

## Default assumptions (project `CLAUDE.md` can override)

- **Stack**: Bedrock / Composer / PHP 8.2+ / MariaDB is the common case, not the only
  one — `structure.type` decides.
- **Framework**: ntdst-core **and** ntdst-baseline, both mu-plugins,
  both Composer-managed. See `ntdst-framework`.
- **Local**: DDEV, always.
- **Standards**: WordPress Coding Standards via PHPCS.

## What this plugin adds on top of netdust-core

- **`ntdst-framework`** — the ntdst-core + ntdst-baseline contract: boot, services,
  handlers, CPTs, routing, templates, assets, the four output surfaces, and
  `references/traps.md` (what the source will not tell you).
- **`ntdst-patterns`** — where files go, plus the four golden-path archetypes.
- **`ntdst-yootheme`** — the YOOtheme Pro stack.
- **Discipline** — `wp-security`, `wp-database`, `bedrock-composer` (each with RED tests).
- **Reference** — `wp-frontend`, `wp-testing`, `wp-infra`.
- **Plan gate** — `wp-plan-requirements`, fired at `harnessed-development` Stage 1.
- **Drift review** — the `ntdst-drift-reviewer` agent, which checks BOTH packages are
  used consistently: no repository bypass, no pass-through, no raw `wp_ajax_*`, and
  nothing re-implementing what an ntdst-baseline module already owns.

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
- **What the WP skills own inside that.** They **layer on** brainstorming, they do not replace it. Brainstorming + the human own INTENT — what we are building and why. `ntdst-framework` (service lifecycle, DI, boundaries), `ntdst-framework` (data layer, CPTs, repositories, REST) and `ntdst-patterns` (where files live) own the TECHNICAL DESIGN SHAPE on this stack. A netdust skill that restates upstream superpowers content is a defect, not thoroughness.
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
