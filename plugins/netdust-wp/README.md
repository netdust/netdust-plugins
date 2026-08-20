# netdust-wp

WordPress layer of the Netdust harness for Claude Code. Layers on top of [`netdust-core`](../netdust-core/README.md) (memory conventions, dev-stack, server management, cross-domain skills) and [`netdust-agent`](../netdust-agent/README.md) (the coding harness — `harnessed-development`, `testing-workflow`, `shake-out`, the reviewer agents, and the live hooks: SessionStart injector, Stop-hook tag capture, PreToolUse guard).

## What this plugin adds

| Layer | Contents |
|---|---|
| **WP discipline skills** | `wp-security`, `wp-database`, `bedrock-composer` (each with RED tests) |
| **WP reference skills** | `wp-frontend`, `wp-testing`, `wp-infra` |
| **ntdst-core framework skills** | `ntdst-framework`, `ntdst-patterns`, `ntdst-yootheme` |
| **WP commands** | `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests` |
| **Templates** | `Makefile.tmpl` with Bedrock-shaped deploy variants |
| **Identity** | `CLAUDE.md` (WP-specific defaults), `RULES.md` (WP-specific rules — universal rules come from netdust-core) |

## Install

**Install netdust-core first.** Then, with the marketplace already added (`claude plugin marketplace add netdust/netdust-plugins`):

```bash
claude plugin install netdust-wp@netdust-plugins
```

Restart Claude Code to pick it up. To update later: `claude plugin update netdust-wp@netdust-plugins`.

Skills, commands, templates load **directly from the installed plugin directory** via Claude Code's plugin loader (`${CLAUDE_PLUGIN_ROOT}`). This plugin ships no `install.sh` — installation and updates go through `claude plugin` commands against the `netdust-plugins` marketplace.

## Per-project usage

```bash
cd ~/Sites/my-new-wp-project
# In Claude Code:
/wp-new-project
```

Scaffolds `CLAUDE.md` (with `@-import` of the core CLAUDE.md), `site.yml`, `memory/`, `tasks/`, and a Bedrock-shaped `Makefile` matching the chosen deploy method.

Or manually, in any WP project's `CLAUDE.md`:

```markdown
@~/.claude/plugins/netdust-core/CLAUDE.md
@~/.claude/plugins/netdust-wp/CLAUDE.md

# Project: <name>

[project-specific notes here]
```

Both imports — core for memory conventions/cross-stack, wp for WP-specific defaults.

## Layout

```
~/.claude/plugins/netdust-wp/
├── .claude-plugin/plugin.json
├── CLAUDE.md, RULES.md, README.md
│
├── commands/                        ← 4 WP-specific commands
│   ├── scaffold-plugin.md
│   ├── setup-tests.md
│   ├── sync-db.md
│   └── wp-new-project.md
│
├── skills/                          ← 10 WP skills, flat layout
│   ├── bedrock-composer/            (discipline + RED tests)
│   ├── ntdst-framework/             ntdst-core + ntdst-baseline contract
│   │                                  SKILL.md · references/traps.md
│   │                                  references/baseline.md · lessons.md
│   ├── ntdst-patterns/              (+ golden-paths/)
│   ├── ntdst-yootheme/              (+ references/, scripts/, templates/)
│   ├── wp-database/                 (discipline + RED tests)
│   ├── wp-frontend/
│   ├── wp-infra/
│   ├── wp-plan-requirements/        (the Stage-1 plan gate)
│   ├── wp-security/                 (discipline + RED tests)
│   └── wp-testing/
│
├── agents/                          ← ntdst-drift-reviewer, ntdst-core-gaps
├── evals/                           ← behavioral-lessons.json + runner
├── memory/                          ← STATE.md, lessons.md
│
└── templates/
    ├── Makefile.tmpl
    ├── project-CLAUDE.md.tmpl
    └── site.yml.tmpl
```

## Relationship to netdust-core + netdust-agent

netdust-wp depends on netdust-core for:

- **Memory conventions** (per-project STATE.md / lessons.md / tasks; live tag-scanner hook runs in netdust-agent)
- **Voice + universal rules** (SOUL.md, RULES.md)
- **/deploy** command (9-method dispatcher; reads `site.yml.deploy.method`)
- **`dev-stack` skill** (DDEV, git, Makefile verbs, `.env` discipline — generic)
- **`secure-server` + `ploi` skills + ploi MCP** (server management)
- **`research`, `market-research`, `brand-voice`, `marketing`** (cross-domain)
- **`/memory-audit`, `/pattern-miner`** (`/skill-audit` lives in netdust-agent)

…and on netdust-agent for:

- **The coding harness** — `harnessed-development` (the intake router), `planning` and `building` (the two overlays), `testing-workflow`, `threat-modeling`, `architecture-invariants`, `convergence`, `compounding` (cross-stack workflow)
- **The gate commands** — `/integration` at a task-group boundary, `/shakeout` at spec-complete, `/converge`, `/skill-audit`
- **The 7 harness agents** — `implementer` and `test-author` build; `reviewer`, `security-sentinel`, `code-simplicity-reviewer` and `invariant-auditor` review; `shakeout-qa` drives the built artifact

You can technically use netdust-wp without these, but you'll miss memory, observability, deploy, server management, the coding harness, and review agents. The dependency is soft — nothing enforces it at install time.

## Adding a WP skill

```bash
mkdir -p ~/.claude/plugins/netdust-wp/skills/<skill-name>
cat > ~/.claude/plugins/netdust-wp/skills/<skill-name>/SKILL.md <<'EOF'
---
name: <skill-name>
description: Use when ... [WP-specific triggers — symbols like $wpdb, wp_, theme.json, etc.]
---

<body>
EOF
touch ~/.claude/plugins/netdust-wp/skills/<skill-name>/lessons.md
```

No install step. Picked up on next session.

For discipline skills, add `red-tests.md` and run `/red-test <skill>` from core.

## Not in scope

- Memory conventions, dev-stack, server — those are netdust-core.
- The coding harness, review agents, and live hooks (SessionStart injector, Stop-hook tag capture, PreToolUse guard) — those are netdust-agent.
- Non-WP work — Statamic, Bun/React, etc. — those get their own plugins (`netdust-statamic`, `netdust-bun-react`).
- Engineering process — defer to `obra/superpowers`.
