# Handoff — netdust harness verification

_Created 2026-05-17, end of session that built and split the harness._

## What you're walking into

Stefan just split a single `netdust-wp` plugin into a 3-plugin harness:

| Plugin | Version | Purpose |
|---|---|---|
| `netdust-core` | 0.1.0 | Stack-agnostic: memory, hooks, dev-stack, secure-server, ploi, research, marketing, code-audit, shake-out, testing-workflow, 7 reviewer agents, `/deploy` + 3 meta commands, ploi MCP |
| `netdust-wp` | 0.2.0 | WordPress: wp-security, wp-database, bedrock-composer (all 3 with RED tests), wp-frontend, wp-testing, wp-infra, ntdst-architecture/data/patterns/yootheme, `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests`, Bedrock Makefile template |
| `netdust-statamic` | 0.1.0 | Statamic 6 + Peak: statamic-build, shake-out-statamic, peak-reference, statamic-mcp, `/new-feature`, `/new-collection`, `/new-block`, `/new-service`, `/cache-bust`, `/sync-content` |

All three registered in shared `netdust-local` marketplace, all enabled. Stefan is starting a fresh Claude Code session to verify everything loads. This doc is what you check first.

## Verification checklist — run in this order

### 1. All three plugins enabled

```bash
python3 -c "
import json
s = json.load(open('/home/ntdst/.claude/settings.json'))
for k, v in s.get('enabledPlugins', {}).items():
    if 'netdust' in k:
        print(f'  {k}: {v}')
"
```

Expect:
```
  netdust-wp@netdust-local: True
  netdust-core@netdust-local: True
  netdust-statamic@netdust-local: True
```

If any is missing or false → re-run that plugin's `install.sh` (idempotent).

### 2. Skills resolve from each plugin

Check that the system-reminder skill list in your context includes:

- **From core**: `dev-stack`, `secure-server`, `ploi`, `research`, `market-research`, `brand-voice`, `marketing`, `code-audit`, `shake-out`, `testing-workflow`
- **From wp**: `wp-security`, `wp-database`, `bedrock-composer`, `wp-frontend`, `wp-testing`, `wp-infra`, `ntdst-architecture`, `ntdst-data`, `ntdst-patterns`, `ntdst-yootheme`
- **From statamic**: `statamic-build`, `shake-out-statamic`, `peak-reference`, `statamic-mcp`

24 total. If you see `ntdst-statamic-build` (with the `ntdst-` prefix), that's a stale cache — restart Claude Code.

### 3. Commands resolve

In the available-skills list (commands appear there with short descriptions):

- **From core**: `/deploy`, `/skill-audit`, `/pattern-miner`, `/red-test`
- **From wp**: `/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests`
- **From statamic**: `/new-feature`, `/new-collection`, `/new-block`, `/new-service`, `/cache-bust`, `/sync-content`

14 total.

### 4. Agents resolve

```bash
# Should NOT be empty
ls ~/.claude/plugins/netdust-core/agents/
```

Expect 7 agents. They should appear in the Agent tool's `subagent_type` enum or be otherwise discoverable.

### 5. Hooks fire + write logs

```bash
tail -3 ~/.claude/logs/memory-hook.log
```

The fresh session should produce a `session-start` line — and when you eventually end it, a `session-stop done` line. If you see `missing=[harness_global]`, the hook is pointing at the wrong path (was a bug, was fixed end of session — should be `found=[harness_global,...]`).

### 6. ploi MCP loaded

The MCP is registered in `netdust-core/.claude-plugin/plugin.json` under `mcpServers.ploi`. When Claude starts with the plugin enabled, the MCP tools should be available as `mcp__ploi__*`. Verify by trying `list_servers` (won't work without a Ploi API token — see `~/mcp/ploi-mcp-server/README.md` — but should at least be discoverable).

### 7. Tag conventions still work

If you (or Stefan) write `DECISION: ...`, `RISK: ...`, `LESSON: ...`, `TODO: ...`, `SKILL-EDGE: <skill>: ...` in a response during the session, the Stop hook lifts them into the right memory file. The SKILL-EDGE scanner was fixed to glob all `netdust-*` plugins (not just netdust-wp), so SKILL-EDGE for a core or statamic skill should now work too.

## What's solid

- Plugin architecture: marketplace install, no symlinks, hooks via `${CLAUDE_PLUGIN_ROOT}`.
- Soft-dep model: wp and statamic check for core, warn if missing, don't enforce.
- Discipline skills (wp-security/wp-database/bedrock-composer) all have RED tests.
- Memory pattern: per-project `<site>/memory/{STATE.md, lessons.md}` + `tasks/todo.md` + `site.yml`.
- Tag scanner is deterministic + zero-cost; Haiku is opt-in via `ANTHROPIC_API_KEY`.

## Known gaps (not bugs — explicit deferrals)

Stefan reviewed these and chose to defer:

1. **No `/statamic-new-project`** — symmetric to `/wp-new-project` but not built. Manual scaffold (clone ntdst-starter, customize) for now.
2. **No `statamic-addon-development` skill** — wait until Stefan actually builds the first addon (`netdust/portfolio-art`).
3. **No `netdust-bun-react` plugin** — wait until Stefan focuses on Folio. Folio's existing `CLAUDE.md` is the canonical reference content to lift later.
4. **No `marketing/` mu-plugin pattern in `ntdst-patterns`** — Stefan's call whether Stride's `marketing/` directory is a project-specific quirk or a Netdust pattern worth documenting.
5. **Spec doc `docs/superpowers/specs/2026-05-17-harness-design.md` in netdust-wp has historical `ntdst-infra` references** — intentional; the spec describes the original architecture before the split.
6. **`netdust-wp/memory/STATE.md` + `lessons.md`** are harness-self-memory left over from earlier sessions. Cosmetic; not broken.
7. **3 install.sh scripts duplicate ~60% of their content** — could extract to `lib/install-common.sh`. Cosmetic.

## What to do if Stefan asks "did it work?"

Run the 7-step checklist above, then report:

- Number of skills loaded per plugin (vs expected 10/10/4)
- Number of commands loaded per plugin (vs expected 4/4/6)
- Whether hook log shows `found=[harness_global,...]` (not `missing=[harness_global]`)
- Whether the `ploi` MCP shows up (or at least lists in `~/.claude/plugins/installed_plugins.json`)

If everything's green, the split worked. If anything's red, the fix is usually re-run the relevant `install.sh` and restart Claude Code.

## Where to look if you need to understand the architecture

- `~/.claude/plugins/netdust-core/CLAUDE.md` — the always-on identity
- `~/.claude/plugins/netdust-core/README.md` — full plugin reference + layout
- `~/.claude/plugins/netdust-core/docs/superpowers/specs/` — design specs (currently empty; future architectural decisions land here)
- `~/.claude/plugins/netdust-wp/CLAUDE.md` — WP layer + soft-dep on core
- `~/.claude/plugins/netdust-statamic/CLAUDE.md` — Statamic layer + Editor Iron Rules

## What NOT to do

- **Don't add symlinks in `~/.claude/skills/`** pointing at the plugin dirs. The plugin loader reads from each plugin's own `skills/` dir via `${CLAUDE_PLUGIN_ROOT}` — symlinks create duplicates. Stefan explicitly chose plugin-marketplace mode for this reason.
- **Don't write to `~/.claude/settings.json` hook entries** for session-start/stop. The plugin's `hooks/hooks.json` handles registration via `${CLAUDE_PLUGIN_ROOT}`. Hand-injected entries would fire the hooks twice.
- **Don't extend `/wp-new-project` to know about Statamic** or vice versa. Each command is correctly stack-scoped.
- **Don't re-list per-site deploy methods in `deploy-patterns.md`** — Stefan trimmed that intentionally; `site.yml` is the source of truth.

## Last session's final state

- All commits pushed in each plugin's own git repo.
- 3 plugins, 24 skills, 14 commands, 7 agents, 1 MCP, all enabled.
- Hooks fixed (was pointing at the post-split missing path), tag scanner multi-plugin aware.
- ntdst-starter's `.claude/skills/` and `.claude/commands/` deleted (content now lives in `netdust-statamic` plugin).

Good luck.
