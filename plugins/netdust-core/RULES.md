# Netdust Core Rules

**Universal rules — apply to every Netdust project regardless of stack.** Stack-specific rules (WordPress, etc.) live in the relevant stack plugin's `RULES.md`.

These hold regardless of: time pressure, sunk cost, "admin-only" framing, client requests, or "it's a quick fix".

## Code + secrets

1. **Never commit `.env`.** Only `.env.example` with placeholder values.
2. **Never edit `vendor/` or `node_modules/`.** Dependencies via the language's package manager (Composer, npm, bun, etc.) — never hand-edited.
3. **Never commit secrets** in any form (API keys, license keys, DB passwords, OAuth tokens). Even "just for testing." Use `.env` (gitignored) for local, platform env vars (Ploi dashboard, Combell control panel) for deploy.
4. **Never `print_r`, `var_dump`, `dd()`, `console.log` in committed code.** Use proper logging (`error_log`, structured logger, `WP_CLI::log`).

## Git + deploy

5. **Never commit directly to `main`.** Work through `staging` branch via the Makefile verbs (`make feature`, `make finish`, `make ship`). Hotfix flow only for prod emergencies — backport to staging.
6. **Never deploy to production without explicit "production" confirmation.** `/deploy` enforces this. Manual deploys must follow the same discipline.
7. **Always read `site.yml` first.** It tells you the deploy method, SSH alias, remote paths, risk level. Confirm site + environment before any destructive operation.

## Operational

8. **Local-first.** DDEV (or stack equivalent) locally. Never edit files directly on production. No "just this one fix" via SSH.
9. **Database changes flow forward.** local → staging → production. Never reverse-sync prod content into a feature branch.
10. **Never flush Redis globally** — VAD Vormingen (and other LMS sites) has cache exclusions that get destroyed by `wp cache flush` / `redis-cli FLUSHALL`. Always check `object-cache.php` exclusions first. See `memory/GLOBAL.md`.

## Memory + skill discipline

11. **Use the tag conventions** — `DECISION:`, `RISK:`, `LESSON:`, `TODO:`, `SKILL-EDGE:` — when something important happens during a session. The Stop hook captures them deterministically. Don't rely on Haiku to guess what mattered.
12. **Per-project `memory/lessons.md` is append-only** — once a lesson is written, it doesn't get overwritten, only superseded.
13. **Per-skill `lessons.md` accumulates edge cases** — append when a skill doesn't cover a real case you hit.

## When a rule seems to be in the way

The rule is not in the way. The work is. Find a path that respects the rule. If you genuinely think a rule should be overridden for this project, propose it in the project `CLAUDE.md` explicitly — do not silently violate it.
