# netdust-statamic

Statamic 6 + Peak layer of the Netdust harness for Claude Code. Layers on top of [`netdust-devops`](../netdust-devops/README.md) (branch flow, deploy, site.yml), [`netdust-core`](../netdust-core/README.md) (memory conventions, server management, cross-domain skills) and [`netdust-agent`](../netdust-agent/README.md) (the coding harness — `harnessed-development`, `testing-workflow`, `shake-out`, the reviewer agents, and the live hooks: SessionStart injector, Stop-hook tag capture, PreToolUse guard).

## What this plugin adds

| Layer | Contents |
|---|---|
| **Skills (4)** | `statamic-build`, `shake-out-statamic`, `peak-reference`, `statamic-mcp` |
| **Commands (6)** | `/new-feature`, `/new-collection`, `/new-block`, `/new-service`, `/cache-bust`, `/sync-content` |
| **Identity** | `CLAUDE.md` (Statamic-specific defaults), `RULES.md` (Statamic-specific rules + the Editor Iron Rules) |

## Install

**Install netdust-core first.** Then, with the marketplace already added (`claude plugin marketplace add netdust/netdust-plugins`):

```bash
claude plugin install netdust-statamic@netdust-plugins
```

Restart Claude Code to pick it up. To update later: `claude plugin update netdust-statamic@netdust-plugins`.

Skills and commands load **directly from the installed plugin directory** via Claude Code's plugin loader (`${CLAUDE_PLUGIN_ROOT}`). This plugin ships no `install.sh` — installation and updates go through `claude plugin` commands against the `netdust-plugins` marketplace.

## Per-project usage

```bash
cd ~/Sites/my-new-statamic-project
# Project's CLAUDE.md @-imports both core + statamic:
```

```markdown
@~/.claude/plugins/netdust-core/CLAUDE.md
@~/.claude/plugins/netdust-statamic/CLAUDE.md

# Project: <name>
```

The Netdust starter (`~/Sites/ntdst-starter`) is the canonical baseline for new Statamic projects. Clone it, customize, add domain addons.

## Layout

```
~/.claude/plugins/netdust-statamic/
├── .claude-plugin/plugin.json
├── CLAUDE.md, RULES.md, README.md
│
├── commands/                        ← 6 Statamic-specific commands
│   ├── cache-bust.md                /cache-bust — clear caches + warm stache
│   ├── new-block.md                 /new-block — scaffold a page-builder block
│   ├── new-collection.md            /new-collection — scaffold a collection
│   ├── new-feature.md               /new-feature — brainstorm → plan → build → shake-out
│   ├── new-service.md               /new-service — scaffold a Service class
│   └── sync-content.md              /sync-content — pull content + assets from remote
│
└── skills/
    ├── statamic-build/              ← build playbook (Iron Rules + rationalization table)
    ├── shake-out-statamic/          ← post-build QA — Statamic-flavored override of core/shake-out
    ├── peak-reference/              ← Peak partials, page-builder conventions, php please commands
    └── statamic-mcp/                ← Statamic MCP router tools guide
```

## Relationship to netdust-core + netdust-agent

netdust-statamic depends on netdust-core for:

- **Memory conventions** (per-project STATE.md / lessons.md / tasks; live tag-scanner hook runs in netdust-agent)
- **Voice + universal rules** (SOUL.md, RULES.md)
- **/deploy** command (9-method dispatcher; reads `site.yml.deploy.method`. Statamic projects typically use `git-push` to Ploi.)
- **`devops` skill** (DDEV, the branch flow, make verbs, deploy, `.env` — netdust-devops)
- **`secure-server` + `ploi` skills + ploi MCP** (server management)
- **`research`, `market-research`, `brand-voice`, `marketing`** (cross-domain)
- **`/skill-audit`, `/pattern-miner`, `/red-test`**

…and on netdust-agent for:

- **The coding harness** — `harnessed-development`, `testing-workflow`, `shake-out`, `test-effectiveness`, `threat-modeling`, `architecture-invariants`, `feature-acceptance`, `compounding` (cross-stack workflow; `shake-out-statamic` here overrides the generic `shake-out` when triggered by Statamic signals)
- **The 8 coding reviewer agents** — code review is done by the `reviewer` agent + the specialist reviewers

The dependency is soft — nothing enforces it at install time.

## Adding a Statamic skill

```bash
mkdir -p ~/.claude/plugins/netdust-statamic/skills/<skill-name>
cat > ~/.claude/plugins/netdust-statamic/skills/<skill-name>/SKILL.md <<'EOF'
---
name: <skill-name>
description: Use when ... [Statamic-specific triggers — php please, blueprints, antlers, blade, stache, etc.]
---

<body>
EOF
touch ~/.claude/plugins/netdust-statamic/skills/<skill-name>/lessons.md
```

No install step. Plugin loader picks it up on next session.

## Future siblings

- `netdust-wp` — WordPress (live)
- `netdust-bun-react` (future) — Folio-style single-binary Bun/React apps
- `netdust-laravel` (future, if scope grows) — pure Laravel apps without Statamic

All depend on `netdust-core`; all coexist in the `netdust-plugins` marketplace.

## Not in scope

- Memory conventions, server — netdust-core. Branch flow, deploy — netdust-devops.
- The coding harness, review agents, and live hooks (SessionStart injector, Stop-hook tag capture, PreToolUse guard) — those are netdust-agent.
- WordPress, Bun/React, etc. — those get their own plugins.
- Engineering process — defer to `obra/superpowers`.
- The actual ntdst-starter project content — this plugin encodes the harness knowledge about working WITH the starter, not the starter itself.
