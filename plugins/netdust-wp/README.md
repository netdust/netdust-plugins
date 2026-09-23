# netdust-wp

WordPress layer of the Netdust harness for Claude Code. Layers on top of [`netdust-devops`](../netdust-devops/README.md) (branch flow, deploy, site.yml), [`netdust-core`](../netdust-core/README.md) (memory conventions, server management, cross-domain skills) and [`netdust-gates`](../netdust-gates/CLAUDE.md) (the coding policy over superpowers — `policy`, `threat-modeling`, `/plan-review`, `/shakeout`, the review agents, and the live hooks: SessionStart injector, Stop-hook tag capture, PreToolUse guard).

## What this plugin adds

| Layer | Contents |
|---|---|
| **WP discipline skills** | `wp-security`, `wp-database`, `bedrock-composer` (each with RED tests) |
| **WP reference skills** | `wp-frontend`, `wp-testing`, `wp-infra` |
| **ntdst-core framework skills** (ntdst-core 5.2.0) | `ntdst-framework`, `ntdst-patterns`, `ntdst-yootheme` |
| **WP commands** | `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests` |
| **Templates** | portable `Makefile` + `scripts/` (gate, ledger, rollback; rsync or git-push transport) |
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
├── skills/                          ← 9 WP skills, flat layout
│   ├── bedrock-composer/            (discipline + RED tests)
│   ├── ntdst-framework/             ntdst-core + ntdst-baseline contract
│   │                                  SKILL.md · references/traps.md
│   │                                  references/baseline.md · lessons.md
│   ├── ntdst-patterns/              (+ golden-paths/)
│   ├── ntdst-yootheme/              (+ references/, scripts/, templates/)
│   ├── wp-database/                 (discipline + RED tests)
│   ├── wp-frontend/
│   ├── wp-infra/
│   ├── wp-security/                 (discipline + RED tests)
│   └── wp-testing/
│
├── agents/                          ← ntdst-drift-reviewer, ntdst-core-gaps
├── evals/                           ← behavioral-lessons.json + runner
├── memory/                          ← STATE.md, lessons.md
│
└── templates/
    ├── Makefile
    ├── scripts/
    ├── project-CLAUDE.md.tmpl
    └── site.yml.tmpl
```

## Relationship to netdust-core, netdust-devops + netdust-gates

- **netdust-core** — memory conventions, voice + universal rules (`SOUL.md`, `RULES.md`),
  `secure-server` + `ploi` + the ploi MCP, the cross-domain skills, `/memory-audit`, `/pattern-miner`.
- **netdust-devops** — the `devops` skill (DDEV, the branch flow, make verbs, `.env`,
  `site.yml`), `/deploy`, `/new-project`.
- **netdust-gates** — the coding policy (`netdust-gates:policy`, whose WordPress pack carries
  the WP plan requirements), `threat-modeling`, `/plan-review`, `/shakeout`, `/session-review`,
  `/session-learn`, the agents `plan-reviewer`, `security-sentinel`, `invariant-auditor`,
  `shakeout-qa`, and the live hooks.

The dependency is soft — nothing enforces it at install time.

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

- Memory conventions, server — netdust-core. Branch flow, deploy — netdust-devops.
- The coding policy, review agents, and live hooks (SessionStart injector, Stop-hook tag capture, PreToolUse guard) — those are netdust-gates.
- Non-WP work — Statamic, Bun/React, etc. — those get their own plugins (`netdust-statamic`, `netdust-bun-react`).
- Engineering process — defer to `obra/superpowers`.
