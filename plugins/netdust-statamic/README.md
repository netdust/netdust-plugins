# netdust-statamic

Statamic 6 + Peak layer of the Netdust harness for Claude Code. Layers on top of [`netdust-devops`](../netdust-devops/README.md) (branch flow, deploy, site.yml), [`netdust-core`](../netdust-core/README.md) (server management, cross-domain skills) and [`netdust-gates`](../netdust-gates/CLAUDE.md) (the delivery policy — `netdust-gates:policy` over superpowers, the reviews, `/shakeout` — and the live hooks: SessionStart memory injector, Stop-hook tag capture, PreToolUse guard).

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
│   ├── new-feature.md               /new-feature — the policy with Statamic overrides
│   ├── new-service.md               /new-service — scaffold a Service class
│   └── sync-content.md              /sync-content — pull content + assets from remote
│
└── skills/
    ├── statamic-build/              ← build playbook (Iron Rules + rationalization table)
    ├── shake-out-statamic/          ← Statamic sweep at the Close's shake-out step
    ├── peak-reference/              ← Peak partials, page-builder conventions, php please commands
    └── statamic-mcp/                ← Statamic MCP router tools guide
```

## Relationship to netdust-core, netdust-devops + netdust-gates

netdust-statamic depends on netdust-core for:

- **Voice + universal rules** (SOUL.md, RULES.md)
- **`secure-server` + `ploi` skills + ploi MCP** (server management)
- **`research`, `market-research`, `brand-voice`, `marketing`** (cross-domain)
- **`/pattern-miner`**

…on netdust-devops for:

- **`devops` skill + `/deploy`** (DDEV, the branch flow, make verbs, deploy, `.env`; `site.yml` `deploy.method` is `rsync` or `git-push` — Statamic projects on Ploi typically use `git-push`)

…and on netdust-gates for:

- **The delivery policy** — `netdust-gates:policy` (entry for any code change), `threat-modeling`, `/plan-review`, `/feature-review`, `/review-fix`, `/shakeout`, `/session-review`, `/session-learn` (`shake-out-statamic` here is the Statamic sweep that runs at `/shakeout`'s step)
- **Code review** — superpowers' whole-branch review via `make review name=<feature>`, with `security-sentinel` / `invariant-auditor`
- **The live hooks** — memory injector, Stop-hook tag capture (per-project STATE.md / lessons.md), PreToolUse guard

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
- The delivery policy, reviews, and live hooks (SessionStart injector, Stop-hook tag capture, PreToolUse guard) — those are netdust-gates.
- WordPress, Bun/React, etc. — those get their own plugins.
- Engineering process — defer to `obra/superpowers`.
- The actual ntdst-starter project content — this plugin encodes the harness knowledge about working WITH the starter, not the starter itself.
