# netdust-wp harness design

_Spec date: 2026-05-17_
_Author: Stefan + Claude (brainstorm session)_
_Status: approved, building_

## Goal

Replace the scattered `~/.claude/skills/ntdst-*` + `~/.claude/hooks/*` + ad-hoc per-project memory pattern with a single versioned plugin at `~/.claude/plugins/netdust-wp/` that:

1. Encodes Netdust WordPress conventions and discipline as Claude Code skills.
2. Has a working observable per-project memory + self-learning loop (the current Stop hook silently doesn't write — sessions go undocumented).
3. Layers cleanly on top of `obra/superpowers` (defers TDD, planning, debugging, code review).
4. Integrates with the `netdust-wp-manager` Alpine.js dashboard for fleet visibility.

## Non-goals

- Replacing superpowers engineering process skills.
- Auto-curation of skills (Haiku rewriting skill bodies).
- Cross-harness portability (Cursor/Codex/OpenCode).
- Refactoring Stride's actual code — the harness encodes Stride's patterns into `ntdst-patterns`, doesn't touch Stride itself.

## Architecture — section 1

### Layout

```
~/.claude/plugins/netdust-wp/
├── .claude-plugin/plugin.json
├── CLAUDE.md            ← @-imported by every WP project's CLAUDE.md
├── SOUL.md              ← voice
├── RULES.md             ← non-negotiables
├── README.md
├── install.sh           ← symlinks hooks, updates settings.json, deletes stale STATE.md files
│
├── hooks/
│   ├── session-start.sh
│   └── session-stop.py
│
├── commands/
│   ├── wp-new-project.md
│   ├── deploy.md
│   ├── skill-audit.md
│   ├── pattern-miner.md
│   └── red-test.md
│
├── skills/
│   ├── _core/{ntdst-architecture, ntdst-data, ntdst-infra, ntdst-yootheme, ntdst-patterns}/
│   ├── _wp/{wp-security, wp-database, bedrock-composer, wp-frontend, wp-testing}/
│   ├── _workflow/{testing-workflow, shake-out, code-audit}/
│   ├── _research/{research, market-research}/
│   └── _marketing/{brand-voice, marketing}/
│
├── memory/
│   ├── GLOBAL.md
│   └── deploy-patterns.md
│
└── templates/
    ├── project-CLAUDE.md.tmpl
    ├── site.yml.tmpl
    └── Makefile.tmpl
```

Folder prefixes `_core` / `_wp` / `_workflow` / `_research` / `_marketing` are organizational; skills still resolve by their `name:` slug.

## Memory & hook fix — section 2

### The actual problem

Stop hook (`~/.claude/hooks/session-stop.py`) is mechanically running but never writing. The `except Exception: pass` in `git_commit_memory()` swallows everything; no logs exist. Stride's `memory/STATE.md` is fresh only because Stefan manually prompts for updates — not because the hook fires.

### Fix — three layers

**Layer 1 — observability**

- `~/.claude/logs/memory-hook.log` — every Stop fires writes: timestamp, cwd, decision, Haiku excerpt.
- `/memory-status` shows last 10 hook runs (deferred to post-Phase-4).

**Layer 2 — explicit signal in STATE.md**

- No-op: appends `[YYYY-MM-DD] — session ended (no significant changes captured)` to STATE.md.
- Error: appends `[YYYY-MM-DD] — ⚠ memory hook errored: <reason>` to STATE.md.

**Layer 3 — better Haiku contract**

- Structured prompt with explicit save-criteria.
- JSON schema required; prose response logged as error.
- Project's existing STATE.md last 80 lines included in prompt (avoid redundant writes).

### Layout (unchanged from current working pattern)

Per project:

```
<project>/
├── memory/{STATE.md, lessons.md}
├── tasks/todo.md
└── site.yml
```

Harness:

```
~/.claude/plugins/netdust-wp/memory/{GLOBAL.md, deploy-patterns.md}
```

### `netdust-wp-manager` integration

`netdust-wp-manager` is a separate Alpine.js dashboard (Sites / Projects / Servers / Scripts / Activity views). It is **not** a memory store.

- Reads each `~/Sites/<site>/site.yml` to enumerate sites.
- Syncs per-project `memory/STATE.md` into its data dir for display.
- "Activity" view reads `~/.claude/logs/memory-hook.log`.
- Sync is triggered by the Stop hook calling `~/Sites/netdust-wp-manager/scripts/sync-from-site.sh` if it exists.

### Stale data deletion

`install.sh` always deletes `~/Sites/netdust-wp-manager/memory/projects/*/STATE.md` — no more parallel source of truth.

## Skills inventory — section 3

14 skills total. 7 absorbed, 7 new.

### `_core` (5)

| Skill | Source | Type |
|---|---|---|
| ntdst-architecture | absorbed | reference |
| ntdst-data | absorbed | reference |
| ntdst-infra | absorbed + extended | reference + discipline |
| ntdst-yootheme | absorbed | reference |
| ntdst-patterns | new (replaces stride-patterns name) — folder/theme/ntdst-core structure, no LearnDash | reference |

### `_wp` (5)

| Skill | Source | Type |
|---|---|---|
| wp-security | drafted in handoff, RED-tested | discipline |
| wp-database | new — `$wpdb->prepare()` discipline | discipline |
| bedrock-composer | new | mixed |
| wp-frontend | new — theme.json, blocks, asset pipeline | reference |
| wp-testing | new — Codeception/wp-browser, Stride as reference | reference |

### `_workflow` (3)

| Skill | Source | Type |
|---|---|---|
| testing-workflow | absorbed | discipline |
| shake-out | absorbed | discipline |
| code-audit | absorbed | reference |

### `_research` (2)

| Skill | Source | Type |
|---|---|---|
| research | new — investigation, plugin source, docs | reference |
| market-research | new — competitor/audience research | reference |

### `_marketing` (2)

| Skill | Source | Type |
|---|---|---|
| brand-voice | new — Stefan/Netdust voice as artifact | reference |
| marketing | new — landing copy, SEO meta, blog posts | reference |

### Dropped / not coming over

- `mainwp`, `ntdst-brainstorm` — explicitly irrelevant per Stefan.
- `acf-patterns`, `learndash-patterns` — Stride uses native blocks + code-defined fields; LearnDash specifics live in project skills.

### RED-test priority

Discipline skills (need RED-GREEN-REFACTOR):
1. wp-security — re-validate
2. wp-database
3. bedrock-composer (discipline portion)
4. ntdst-infra deploy extension
5. testing-workflow, shake-out — existing usage validates these

Reference skills get usage validation only.

## Commands, hooks, install — section 4

### Commands (5)

| Command | Behavior |
|---|---|
| `/wp-new-project` | Scaffolds CLAUDE.md (`@-import` harness), site.yml, memory/, tasks/, Makefile (variant per deploy method). Prompts: site name, risk, deploy method (9 options). |
| `/deploy` | Reads `site.yml`'s `deploy.method`. Dispatches per method. Always asks env explicitly. Never deploys to prod without explicit "production" answer. |
| `/skill-audit` | Reads each skill's body + lessons + recent STATE.md mentions. Flags drift candidates. Doesn't auto-edit. |
| `/pattern-miner` | Reads `~/Sites/*/memory/STATE.md` + lessons. Surfaces patterns worth promoting. Doesn't auto-edit. |
| `/red-test <skill>` | Loads the skill's `red-tests.md`, runs scenarios without then with the skill, diffs. Regression check. |

### Hooks

`session-start.sh` fixes:
- Reads `~/.claude/plugins/netdust-wp/memory/GLOBAL.md` (the correct location — current hook points at missing `~/.claude/memory/GLOBAL.md`).
- Reads `<cwd>/site.yml`; surfaces site name, risk, deploy method.
- Logs to `~/.claude/logs/memory-hook.log`.

`session-stop.py` rewrites:
- Mandatory log line every fire.
- No-op visible in STATE.md.
- Errors visible in STATE.md.
- Structured Haiku prompt with JSON schema + existing STATE.md context.
- Per-skill `lessons.md` writeback when the agent reports an edge case.
- Calls `~/Sites/netdust-wp-manager/scripts/sync-from-site.sh` if present.

### install.sh

Idempotent. Steps:
1. Symlink hooks into `~/.claude/hooks/` (backs up existing).
2. Ensure `~/.claude/settings.json` has SessionStart + Stop entries.
3. Ensure `~/.claude/logs/` exists.
4. **Always** deletes `~/Sites/netdust-wp-manager/memory/projects/*/STATE.md` (no flag needed — Stefan said "always delete").
5. Prints summary of changes.

### Templates (3)

- `project-CLAUDE.md.tmpl` — starts with `@~/.claude/plugins/netdust-wp/CLAUDE.md`, then project-specific block.
- `site.yml.tmpl` — all 9 deploy methods commented; `/wp-new-project` uncomments chosen.
- `Makefile.tmpl` — variant per deploy method.

## Build order — section 5

Phase 0 — repo + manifest (~30 min)
Phase 1 — hooks + memory observable (~1–2h)
Phase 2 — absorb 7 existing skills (~2–3h)
Phase 3 — commands (~1–2h)
Phase 4 — new discipline skills (~2–4h each)
Phase 5 — new reference skills (~1–2h each)
Phase 6 — `netdust-wp-manager` integration (~2h)

Per `/goal` directive: deliver Phases 0–4 in this session.

## Open items deferred

- Phase 5 reference skills (ntdst-patterns, wp-frontend, wp-testing, research, market-research, brand-voice, marketing) — bodies seeded with description + skeleton, full content as time permits.
- Phase 6 dashboard sync script — stubbed in Stop hook; concrete script in netdust-wp-manager repo separately.
- `/memory-status` command — deferred to post-Phase-4.

## Verification at end of each phase

- Phase 0: `/plugin list` shows netdust-wp; `@-import` resolves.
- Phase 1: 1-message session in `~/Sites/stride/` produces log line + STATE.md timestamp update.
- Phase 2: skills resolve by name from the new location; old `~/.claude/skills/ntdst-*` paths deleted.
- Phase 3: `/wp-new-project` produces a working project; `/deploy` dry-runs on Stride.
- Phase 4: each discipline skill has a passing RED-test log.
