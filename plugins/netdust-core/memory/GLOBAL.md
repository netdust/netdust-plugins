# Global Memory — Netdust / Stefan

Harness-level facts. Loaded into every WP session by `session-start.sh`.

## Stack

- WordPress: Bedrock / Composer / PHP 8.2+ / MariaDB
- Framework: ntdst-core conventions — Stride is the canonical implementation
- Local: DDEV (always — no exceptions for "just this site")
- Hosting: Hetzner VPS via Ploi, OR Combell hosting (per site)
- Common plugins: LearnDash (Stride family), YOOtheme Pro (marketing sites), FluentCRM/FluentForms (forms)
- WP-CLI: `--path=web/wp` (Bedrock) or `--path=app/wp` (custom-app) — check `wp-cli.yml` per project
- Backups: Synology NAS + Hetzner Object Storage (S3-compatible)

## Cross-project hard rules

- **Never flush Redis globally** — VAD Vormingen has LMS cache exclusions that get destroyed by `wp cache flush`. Always check `object-cache.php` exclusions first.
- **Always test on DDEV before deploying** to Ploi staging or Combell.
- **Bedrock**: `composer install` before any WP-CLI commands on a fresh clone (otherwise `wp-config.php` symlinks break).
- **Confirm site + environment** before any destructive operation. `site.yml` has `site.risk` — `high` means triple-check.
- **Never deploy to prod without explicit "production" confirmation.** `/deploy` enforces this.
- **Never use `git stash` as temporary holding.** Audit on 2026-05-18 found 17 abandoned stashes across multiple sessions (unrecoverable real work — kebab redesign, 545-line tab-offertes redesign, 289-line AdminAPIController changes). Pattern: `git stash` → operation → `git stash pop` fails on a cache file → work re-applied manually → original stash later `drop`'d → commit becomes unreachable. Instead: (a) leave the tree dirty, (b) commit a `wip:` to the current branch and amend/reset later, (c) `git worktree add ../<name> <branch>` for parallel exploration, (d) `git checkout <commit> -- <file>` + `git checkout HEAD -- <file>` for single-file inspection. The `session-stop.py` auto-capture hook only commits `memory/` + `tasks/` and is NOT the cause. Recovery: `git fsck --unreachable` + `git update-ref refs/recovery/<name> <sha>` to pin before gc.

## SSH aliases (pattern)

- `ploi-staging` / `ploi-<sitename>-staging` — Hetzner via Ploi
- `combell-<sitename>-staging` / `combell-<sitename>-prod` — Combell hosting
- Check `~/.ssh/config` per project, or `site.yml`'s `hosting.ssh_*` fields.

## Active priorities (rolls forward — update as priorities shift)

1. **Stride LMS** — Phase 1 finishing work + multi-brand demo for sales.
2. **VAD Vormingen** — stable production, zero downtime, LTI development.
3. **Atelier 296** — gallery client pipeline (Statamic, out of WP harness scope).

## Harness self-meta

- Built 2026-05-17 from previous handoff. Spec at `~/.claude/plugins/netdust-wp/docs/superpowers/specs/2026-05-17-harness-design.md`.
- 14 skills across 5 groups. See plugin CLAUDE.md.
- Self-learning loop: per-skill `lessons.md` + `/skill-audit` + `/pattern-miner`.
- **2026-05-20**: Added a "Memory discipline" prompt block to `hooks/session-start.sh`. Fires only when `memory/` exists in the project. Tells Claude exactly when to update STATE/lessons/CLAUDE/site.yml and what NOT to write. Closes the gap between "memory is loaded" and "memory is maintained." If a session feels like memory isn't being updated, check `~/.claude/logs/memory-hook.log` for the SessionStart fire and grep the output for "Memory discipline".
- **2026-05-20**: Fixed ploi MCP startup failure (had been failing silently every session). Two bugs: (1) `node_modules/` missing under `~/mcp/ploi-mcp-server/ploi-mcp-server/` — fixed with `npm ci` in that folder. (2) Server expects `PLOI_API_TOKEN` env var but plugin.json never forwarded one and the ploi skill docs called it `PLOI_TOKEN` (wrong). Added `env.PLOI_API_TOKEN: ${PLOI_API_TOKEN}` to mcpServers.ploi in plugin.json, corrected the skill doc. Stefan needs to `export PLOI_API_TOKEN="..."` in his shell rc and restart Claude for it to fully wire up.
