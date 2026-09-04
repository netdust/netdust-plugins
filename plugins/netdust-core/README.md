# netdust-core

The always-on **business + ops + content + memory** layer for Claude Code. Stack-agnostic — applies to WordPress, Statamic, Bun/Node, plain HTML alike. Stack-specific plugins (`netdust-wp`, `netdust-statamic`) layer on top, and the coding/build harness lives in the separate **netdust-agent** plugin.

This is **not** a coding harness. For any non-trivial coding work (gates, craft skills, reviewer agents, TDD/threat-model/shake-out, `/integration` + `/shakeout`), load the **netdust-agent** plugin.

## What this plugin provides

| Layer | Contents |
|---|---|
| **Identity** | `CLAUDE.md` (default agent context), `SOUL.md` (voice), `RULES.md` (universal non-negotiables) |
| **Memory + hooks** | Per-project `memory/STATE.md` + `lessons.md` + `tasks/todo.md` convention and memory discipline. The live hooks — SessionStart loader, Stop-hook `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tag scanner, PreToolUse destructive-command guard — live in **netdust-agent** (registration AND scripts). Core ships no hook scripts. |
| **Content + marketing skills** | `brand-voice`, `marketing`, `market-research`, `research` |
| **Ops + infra skills** | `secure-server` (VPS hardening), `ploi` (server/site lifecycle) |
| **Slash commands** | `/memory-audit`, `/pattern-miner` — `/deploy` moved to **netdust-devops** |
| **MCP** | `ploi` MCP server (server + site management via Ploi API) |
| **Templates** | `project-CLAUDE.md.tmpl`, `site.yml.tmpl` (stack-neutral scaffolds) |
| **Memory (harness-level)** | `GLOBAL.md` ships in **netdust-agent** (`plugins/netdust-agent/memory/GLOBAL.md`) — its `session-start.sh` is the live injector. The deploy methods now live in **netdust-devops** |

## Install

Add the marketplace once, then install the plugin:

```bash
claude plugin marketplace add netdust/netdust-plugins
claude plugin install netdust-core@netdust-plugins
```

Restart Claude Code to pick it up. To update later: `claude plugin update netdust-core@netdust-plugins`.

Skills, commands, agents, hooks, and the MCP load **directly from the installed plugin directory** via Claude Code's plugin loader (`${CLAUDE_PLUGIN_ROOT}`). This plugin ships no `install.sh` — installation and updates go through `claude plugin` commands against the `netdust-plugins` marketplace.

## Layered plugins

| Plugin | When to install |
|---|---|
| **netdust-agent** | For any non-trivial coding work. Carries the build harness — `harnessed-development` sequencer, the gate skills (threat-modeling, architecture-invariants, feature-acceptance, testing-workflow, test-effectiveness, shake-out, compounding), the reviewer agents, and the harness commands (`/integration`, `/shakeout`, etc.). |
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
├── commands/
│   ├── memory-audit.md             /memory-audit — STATE/lessons/todo staleness report
│   └── pattern-miner.md            /pattern-miner — cross-project pattern mining
│
├── skills/                         ← 7 stack-agnostic skills, flat layout
│   ├── brand-voice/                ← Stefan/Netdust voice as artifact
│   ├── marketing/                  ← SEO + copy structure + meta/schema
│   ├── market-research/            ← audiences, competitors, pricing
│   ├── research/                   ← technical + business investigation
│   ├── secure-server/              ← VPS hardening
│   └── ploi/                       ← Ploi + Hetzner lifecycle
│
├── memory/
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
│   ├── STATE.md       ← updated by Stop hook each session (deterministic tag capture)
│   └── lessons.md     ← gotchas + edge cases, append-only
├── tasks/
│   └── todo.md        ← carried-forward tasks
└── site.yml           ← operational config (deploy method, SSH, paths)
```

netdust-agent's SessionStart hook injects all of these + the harness-level `GLOBAL.md`, which now ships in **netdust-agent** (`plugins/netdust-agent/memory/GLOBAL.md`). netdust-agent's Stop hook captures via tags.

## Operations

### Verify the hook is firing

```bash
tail -f ~/.claude/logs/memory-hook.log
```

Every Claude session start + stop writes one line. The hooks that write this log (SessionStart injector, Stop-hook tag capture, PreToolUse guard) live in **netdust-agent**, not here — they fire only if `netdust-agent` is enabled. If you don't see anything appearing after starting/ending a session:

```bash
grep netdust-agent ~/.claude/settings.json
# Should show: "netdust-agent@netdust-plugins": true
```

If missing or false, install/enable `netdust-agent` from the `netdust-plugins` marketplace (`claude plugin install netdust-agent@netdust-plugins`; this plugin has no `install.sh`).

### Tag conventions in conversation

When something important happens, write any of these tags in your response — the Stop hook captures them deterministically:

- `DECISION: <text>` → `memory/STATE.md`
- `RISK: <text>` → `memory/STATE.md`
- `LESSON: <text>` → `memory/lessons.md`
- `TODO: <text>` → `tasks/todo.md`
- `SKILL-EDGE: <skill-name>: <text>` → `skills/<name>/lessons.md`

No AI guessing, no Anthropic API call needed.

### Roll back

```bash
# Disable the plugin without uninstalling:
#   /plugin disable netdust-core@netdust-plugins
# OR in ~/.claude/settings.json set enabledPlugins.netdust-core@netdust-plugins to false.
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
