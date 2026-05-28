# netdust-statamic

Statamic 6 + Peak layer of the Netdust harness for Claude Code. Layers on top of [`netdust-core`](../netdust-core/README.md).

## What this plugin adds

| Layer | Contents |
|---|---|
| **Skills (4)** | `statamic-build`, `shake-out-statamic`, `peak-reference`, `statamic-mcp` |
| **Commands (6)** | `/new-feature`, `/new-collection`, `/new-block`, `/new-service`, `/cache-bust`, `/sync-content` |
| **Identity** | `CLAUDE.md` (Statamic-specific defaults), `RULES.md` (Statamic-specific rules + the Editor Iron Rules) |

## Install

**Install netdust-core first.** Then:

```bash
git clone <repo> ~/.claude/plugins/netdust-statamic
bash ~/.claude/plugins/netdust-statamic/install.sh
```

`install.sh` warns if netdust-core is missing, then registers + enables this plugin in the shared `netdust-local` marketplace.

Skills and commands load directly from this plugin via `${CLAUDE_PLUGIN_ROOT}`. No symlinks, no copies. Edit in place — picked up next session.

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
├── install.sh                       (soft-dep check on netdust-core)
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

## Relationship to netdust-core

netdust-statamic depends on netdust-core for:

- **Memory + hooks** (per-project STATE.md / lessons.md / tasks; tag scanner)
- **Voice + universal rules** (SOUL.md, RULES.md)
- **/deploy** command (9-method dispatcher; reads `site.yml.deploy.method`. Statamic projects typically use `git-push` to Ploi.)
- **`dev-stack` skill** (DDEV, git, Makefile verbs, `.env` discipline — generic)
- **`secure-server` + `ploi` skills + ploi MCP** (server management)
- **`code-audit`, `shake-out`, `testing-workflow`** (cross-stack workflow; `shake-out-statamic` here overrides the generic `shake-out` when triggered by Statamic signals)
- **`research`, `market-research`, `brand-voice`, `marketing`** (cross-domain)
- **7 code reviewer agents**
- **`/skill-audit`, `/pattern-miner`, `/red-test`**

The soft-dep check in install.sh warns but doesn't enforce.

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

All depend on `netdust-core`; all coexist in the shared `netdust-local` marketplace.

## Not in scope

- Memory, hooks, dev-stack, server, review agents — those are netdust-core.
- WordPress, Bun/React, etc. — those get their own plugins.
- Engineering process — defer to `obra/superpowers`.
- The actual ntdst-starter project content — this plugin encodes the harness knowledge about working WITH the starter, not the starter itself.
