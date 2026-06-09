# netdust-core

The always-on **business + ops + content + memory** layer for Claude Code. Stack-agnostic — applies to WordPress, Statamic, Bun/Node, plain HTML alike. Stack-specific plugins (`netdust-wp`, `netdust-statamic`) layer on top, and the coding/build harness lives in the separate **netdust-agent** plugin.

This is **not** a coding harness. For any non-trivial coding work (gates, craft skills, reviewer agents, TDD/threat-model/shake-out, `/integration` + `/shakeout`), load the **netdust-agent** plugin.

## What this plugin provides

| Layer | Contents |
|---|---|
| **Identity** | `CLAUDE.md` (default agent context), `SOUL.md` (voice), `RULES.md` (universal non-negotiables) |
| **Memory + hooks** | `session-start.sh` (loads project memory) + `session-stop.py` (tag capture) + `pretooluse-guard.py` (destructive-command guard), wired in `hooks.json`. Per-project `memory/STATE.md` + `lessons.md` + `tasks/todo.md`. Deterministic tag scanner (`DECISION:`/`RISK:`/`LESSON:`/`TODO:`). Optional Haiku summary if `ANTHROPIC_API_KEY` set. |
| **Content + marketing skills** | `brand-voice`, `marketing`, `market-research`, `research` |
| **Ops + infra skills** | `dev-stack` (DDEV, git branching, Makefile verbs, `.env`), `secure-server` (VPS hardening), `ploi` (server/site lifecycle) |
| **Slash commands** | `/deploy` (9-method dispatcher), `/memory-audit`, `/pattern-miner` |
| **MCP** | `ploi` MCP server (server + site management via Ploi API) |
| **Templates** | `project-CLAUDE.md.tmpl`, `site.yml.tmpl` (stack-neutral scaffolds) |
| **Memory (harness-level)** | `memory/GLOBAL.md` (cross-project facts, Redis exclusions, etc.), `memory/deploy-patterns.md` (the 9 deploy methods + per-site mapping) |

## Install

```bash
git clone <repo> ~/.claude/plugins/netdust-core
bash ~/.claude/plugins/netdust-core/install.sh
```

`install.sh` is idempotent. It registers a local marketplace at `~/.claude/plugins/marketplaces/netdust-local/` and enables the plugin in `settings.json`. Restart Claude Code to pick it up.

Skills, commands, agents, hooks, and the MCP load **directly from this plugin directory** via Claude Code's plugin loader (`${CLAUDE_PLUGIN_ROOT}`). No symlinks, no copies. Edit files in place — they're picked up on the next session.

## Layered plugins

| Plugin | When to install |
|---|---|
| **netdust-agent** | For any non-trivial coding work. Carries the build harness — `harnessed-development` sequencer, the gate skills (threat-modeling, architecture-invariants, feature-acceptance, testing-workflow, test-effectiveness, shake-out, compounding, code-audit), the reviewer agents, and the harness commands (`/integration`, `/shakeout`, etc.). |
| **netdust-wp** | When you work on WordPress projects (Bedrock or custom-app). Adds wp-security, wp-database, ntdst-architecture, etc. + WP-specific commands. |
| **netdust-statamic** | For Statamic + Peak marketing sites. |

All depend on `netdust-core`. Install order: core first, then any stack/agent plugins.

## Per-project usage

```bash
cd ~/Sites/my-new-project
# In Claude Code:
/wp-new-project           # if WP — netdust-wp provides this
# OR (future)
/bun-new-project          # if Bun/React
```

Either command scaffolds `CLAUDE.md` (with `@-import` of the core CLAUDE.md), `site.yml`, `memory/`, `tasks/`, and a stack-appropriate `Makefile`.

In any existing project, you can manually add to its `CLAUDE.md`:

```markdown
@~/.claude/plugins/netdust-core/CLAUDE.md

# Project: <name>

[project-specific notes here]
```

## Layout

```
~/.claude/plugins/netdust-core/
├── .claude-plugin/plugin.json
├── CLAUDE.md, SOUL.md, RULES.md, README.md
│
├── hooks/
│   ├── hooks.json                  ← plugin loader fires SessionStart + Stop + PreToolUse
│   ├── session-start.sh            ← loads project memory (STATE/lessons/CLAUDE/GLOBAL)
│   ├── session-stop.py             ← captures DECISION:/RISK:/LESSON:/TODO: tags
│   └── pretooluse-guard.py         ← destructive-command guard (Bash)
│
├── commands/
│   ├── deploy.md                   /deploy — 9-method dispatcher
│   ├── memory-audit.md             /memory-audit — STATE/lessons/todo staleness report
│   └── pattern-miner.md            /pattern-miner — cross-project pattern mining
│
├── skills/                         ← 7 stack-agnostic skills, flat layout
│   ├── brand-voice/                ← Stefan/Netdust voice as artifact
│   ├── marketing/                  ← SEO + copy structure + meta/schema
│   ├── market-research/            ← audiences, competitors, pricing
│   ├── research/                   ← technical + business investigation
│   ├── dev-stack/                  ← DDEV, git, Makefile verbs, .env
│   ├── secure-server/              ← VPS hardening
│   └── ploi/                       ← Ploi + Hetzner lifecycle
│
├── memory/
│   ├── GLOBAL.md                   ← cross-project facts (stack, Redis exclusions)
│   └── deploy-patterns.md          ← 9 deploy methods + per-site mapping
│
├── templates/
│   ├── project-CLAUDE.md.tmpl
│   └── site.yml.tmpl
│
└── docs/                           ← specs + plans for this plugin's evolution
```

The coding/build harness — reviewer agents, gate skills, `harnessed-development`, `/integration` + `/shakeout` — is **not** here; it lives in the **netdust-agent** plugin.

The plugin also registers the **`ploi` MCP server** (from `~/mcp/ploi-mcp-server/`) via `plugin.json`'s `mcpServers`. Auto-loaded when this plugin is enabled. Tools: `ploi_list_servers`, `ploi_restart_service`, `ploi_deploy_site`, `ploi_restore_database_backup`, and ~30 more.

## Per-project memory pattern

```
<project>/
├── memory/
│   ├── STATE.md       ← updated by Stop hook each session (deterministic + optional Haiku)
│   └── lessons.md     ← gotchas + edge cases, append-only
├── tasks/
│   └── todo.md        ← carried-forward tasks
└── site.yml           ← operational config (deploy method, SSH, paths)
```

The SessionStart hook injects all of these + `memory/GLOBAL.md` (harness-level) into the initial context. The Stop hook captures via tags + (optionally) Haiku.

## Operations

### Verify the hook is firing

```bash
tail -f ~/.claude/logs/memory-hook.log
```

Every Claude session start + stop writes one line. If you don't see anything appearing after starting/ending a session, the plugin isn't enabled:

```bash
grep netdust-core ~/.claude/settings.json
# Should show: "netdust-core@netdust-local": true
```

If missing or false, re-run `bash ~/.claude/plugins/netdust-core/install.sh` (idempotent).

### Tag conventions in conversation

When something important happens, write any of these tags in your response — the Stop hook captures them deterministically:

- `DECISION: <text>` → `memory/STATE.md`
- `RISK: <text>` → `memory/STATE.md`
- `LESSON: <text>` → `memory/lessons.md`
- `TODO: <text>` → `tasks/todo.md`
- `SKILL-EDGE: <skill-name>: <text>` → `skills/<name>/lessons.md`

No AI guessing, no Anthropic API call needed.

### Recover from broken Haiku

Haiku is opt-in via `ANTHROPIC_API_KEY`. If failing:
- Errors logged to `~/.claude/logs/memory-hook.log` always.
- Persistent errors (401/403/timeout) also annotate STATE.md as `⚠ memory hook (haiku) errored`.
- To disable: `unset ANTHROPIC_API_KEY`. Tag scanner still works.

### Roll back

```bash
# Disable the plugin without uninstalling:
#   /plugin disable netdust-core@netdust-local
# OR in ~/.claude/settings.json set enabledPlugins.netdust-core@netdust-local to false.
```

Plugin dir stays on disk; nothing in the project memory dirs is destroyed.

## Adding a new skill

```bash
mkdir -p ~/.claude/plugins/netdust-core/skills/<skill-name>
cat > ~/.claude/plugins/netdust-core/skills/<skill-name>/SKILL.md <<'EOF'
---
name: <skill-name>
description: Use when ... [triggers, keywords, symptoms — NOT a workflow summary]
---

<body>
EOF
touch ~/.claude/plugins/netdust-core/skills/<skill-name>/lessons.md
```

No install step. Plugin loader picks it up on next session.

## Not in scope

- Stack-specific knowledge — that's the role of `netdust-wp`, `netdust-statamic`, etc.
- The coding/build harness — gates, reviewer agents, TDD/threat-model/shake-out — lives in `netdust-agent`.
- Engineering process — defer to `obra/superpowers`.
- Cross-harness portability (Cursor / OpenCode / Codex) — Claude Code only.
