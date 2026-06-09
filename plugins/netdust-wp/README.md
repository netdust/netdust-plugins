# netdust-wp

WordPress layer of the Netdust harness for Claude Code. Layers on top of [`netdust-core`](../netdust-core/README.md) (memory, hooks, dev-stack, server management, cross-domain skills) and [`netdust-agent`](../netdust-agent/README.md) (the coding harness — `harnessed-development`, `testing-workflow`, `shake-out`, and the reviewer agents).

## What this plugin adds

| Layer | Contents |
|---|---|
| **WP discipline skills** | `wp-security`, `wp-database`, `bedrock-composer` (each with RED tests) |
| **WP reference skills** | `wp-frontend`, `wp-testing`, `wp-infra` |
| **ntdst-core framework skills** | `ntdst-architecture`, `ntdst-data`, `ntdst-patterns`, `ntdst-yootheme` |
| **WP commands** | `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests` |
| **Templates** | `Makefile.tmpl` with Bedrock-shaped deploy variants |
| **Identity** | `CLAUDE.md` (WP-specific defaults), `RULES.md` (WP-specific rules — universal rules come from netdust-core) |

## Install

**Install netdust-core first.** Then:

```bash
git clone <repo> ~/.claude/plugins/netdust-wp
bash ~/.claude/plugins/netdust-wp/install.sh
```

`install.sh` warns if netdust-core is missing, then registers + enables this plugin in the shared `netdust-local` marketplace.

Skills, commands, templates load **directly from this plugin directory** via Claude Code's plugin loader (`${CLAUDE_PLUGIN_ROOT}`). No symlinks, no copies. Edit files in place — they're picked up on the next session.

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

Both imports — core for memory/hooks/cross-stack, wp for WP-specific defaults.

## Layout

```
~/.claude/plugins/netdust-wp/
├── .claude-plugin/plugin.json
├── CLAUDE.md, RULES.md, README.md
├── install.sh                       (soft-dep check on netdust-core)
│
├── commands/                        ← 4 WP-specific commands
│   ├── scaffold-plugin.md
│   ├── setup-tests.md
│   ├── sync-db.md
│   └── wp-new-project.md
│
├── skills/                          ← 10 WP skills, flat layout
│   ├── bedrock-composer/            (discipline + RED tests)
│   ├── ntdst-architecture/
│   ├── ntdst-data/
│   ├── ntdst-patterns/
│   ├── ntdst-yootheme/
│   ├── wp-database/                 (discipline + RED tests)
│   ├── wp-frontend/
│   ├── wp-infra/                    (WP-CLI, Vite-for-WP, Bedrock Makefile patterns)
│   ├── wp-security/                 (discipline + RED tests)
│   └── wp-testing/
│
└── templates/
    └── Makefile.tmpl                (Bedrock variants: makefile, git-push, git-bundle-makefile)
```

## Relationship to netdust-core + netdust-agent

netdust-wp depends on netdust-core for:

- **Memory + hooks** (per-project STATE.md / lessons.md / tasks; tag scanner)
- **Voice + universal rules** (SOUL.md, RULES.md)
- **/deploy** command (9-method dispatcher; reads `site.yml.deploy.method`)
- **`dev-stack` skill** (DDEV, git, Makefile verbs, `.env` discipline — generic)
- **`secure-server` + `ploi` skills + ploi MCP** (server management)
- **`research`, `market-research`, `brand-voice`, `marketing`** (cross-domain)
- **`/skill-audit`, `/pattern-miner`, `/red-test`**

…and on netdust-agent for:

- **The coding harness** — `harnessed-development`, `testing-workflow`, `shake-out`, `test-effectiveness`, `threat-modeling`, `architecture-invariants`, `feature-acceptance`, `compounding` (cross-stack workflow)
- **The 8 coding reviewer agents** — code review is done by the `reviewer` agent + the specialist reviewers

You can technically use netdust-wp without these, but you'll miss memory, observability, deploy, server management, the coding harness, and review agents. The soft-dep check in install.sh warns but doesn't enforce.

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

- Memory, hooks, dev-stack, server — those are netdust-core.
- The coding harness + review agents — those are netdust-agent.
- Non-WP work — Statamic, Bun/React, etc. — those get their own plugins (`netdust-statamic`, `netdust-bun-react`).
- Engineering process — defer to `obra/superpowers`.
