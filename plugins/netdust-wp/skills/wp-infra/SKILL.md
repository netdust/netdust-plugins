---
name: wp-infra
description: Use when working on WordPress-specific infra — WP-CLI commands, ddev wp, Bedrock project layout (web/wp + web/app), Vite-for-WP asset pipelines, WP-aware Makefile targets, rewrite flush, cache flush, wp db, plugin/theme management via WP-CLI. Triggers on file edits to wp-cli.yml, web/wp/* (you should not edit core), web/app/themes/*/vite.config.*, mu-plugins/* loader files. Activates on keywords WP-CLI, wp cli, ddev wp, --path=web/wp, --path=app/wp, wp cache flush, wp rewrite flush, wp db, wp plugin, wp theme, wp option, Bedrock-Makefile, ntdstheme, theme-config. Symptoms include needing a WP-CLI command, debugging "wp not loading", configuring DDEV's WP-CLI integration, setting up Vite for a WP theme, Bedrock layout questions. For the branch flow, make verbs, deploy and site.yml, see netdust-devops:devops. For Bedrock + Composer dependency rules, see bedrock-composer.
---

# WordPress infrastructure

WP-specific bits of the Netdust dev stack. The branch flow, the make verbs, the deploy gate and `.env` discipline live in `netdust-devops:devops` — this one only covers what's WP-flavored.

## Project layout (Bedrock)

```
project/
├── composer.json, composer.lock, .env
├── wp-cli.yml                       ← path: web/wp
├── Makefile                          ← WP-aware targets (see below)
└── web/
    ├── wp/                           ← WP core (Composer-managed, gitignored)
    └── app/
        ├── plugins/                  ← Composer-managed (gitignored)
        ├── themes/<theme>/           ← custom committed; WPackagist themes gitignored
        │   ├── vite.config.js        ← asset pipeline
        │   └── inc/enqueue.php       ← manifest-driven script enqueue
        ├── mu-plugins/<project>-core/  ← business logic (the ntdst-core layer)
        └── uploads/                  ← user content (gitignored)
```

## WP-CLI conventions

Generic WP-CLI — the command set, `search-replace`, plugin/theme ops, cron, multisite, scripting
guardrails — is the upstream `wp-wpcli-and-ops` skill (`WordPress/agent-skills`, installed at a
pinned commit by `bin/wp-upstream-skills.sh`; `### 2) Choose the right workflow`, `### 3)
Automation patterns`, `references/safety.md`). The netdust layer: always `ddev wp …` (PHP and DB
must match the container) and one `wp-cli.yml` at the repo root fixing `--path` per
`structure.type` (table below) — without it `ddev wp` fails with "This does not seem to be a
WordPress installation." Both are rows in Anti-patterns; never hardcode `--path` in a script.

### Cache flush — read this carefully

`ddev wp cache flush` clears the object cache. **On servers with LMS/Tin-Canny data (VAD, Stride), this destroys cached LMS state that has exclusions in `object-cache.php`**. Always check `object-cache.php` for excluded keys before flushing on prod. See GLOBAL.md cross-project rules.

**There is no ntdst-side cache left to flush.** `NTDST_Query_Cache` and its per-post-type
versioned buckets (`ntdst_data_{post_type}_v{n}_…`) are **DELETED**, along with
`ntdst_invalidate_post_type()`, `ntdst_clear_posts_cache()` and `ntdst_query_cache()` —
`ddev wp eval "ntdst_invalidate_post_type(...)"` is now a fatal error, not a fix. The
data layer keeps no cache of its own; WordPress's post, `post_meta`, `post-queries` and
term caches are the caching, and core invalidates them on every write.

So after bulk changes outside the normal CRUD flow (raw SQL writes, import scripts) that
bypassed WordPress entirely, `ddev wp cache flush` — subject to the LMS warning above —
is the whole remedy. Anything written through `wp_insert_post()` / `update_post_meta()`
needs no flush at all.

## Logs

NTDST writes channel logs to `wp-content/logs/{channel}-{YYYY-MM-DD}.log`. Under Bedrock that's **`web/app/logs/` — inside the webroot.**

- The logger drops `.htaccess` (`Deny from all`) **and** an empty `index.html` into the directory on first write.
- `.htaccess` is **inert on Nginx**. Ploi / Combell / any Nginx-fronted host MUST add an explicit deny in server config:

```nginx
location ~ ^/app/logs/ { deny all; return 404; }
```

- The database log handler is now **opt-in** (default: only on under `WP_DEBUG`). In production, ERROR+ entries still hit the file log and PHP's `error_log()` — they don't disappear. Force on with `add_filter('ntdst_log_database_enabled', '__return_true')` if you have an observability stack reading from `log_entry`.
- Don't log user-submitted values that may contain PII (emails, names, form content). Log identifiers and structural metadata only.

## Makefile targets

The verbs — `deploy`, `deploy-test`, `ship`, `deployed`, `rollback`, `refresh`, `pull`, `gate` —
are `netdust-devops:devops`'s table, identical on WordPress. `templates/Makefile` +
`templates/scripts/` are copied verbatim and carry no project value; the WP data verbs live in
`netdust-devops` `dist/mk/wp.mk`.

## Asset pipeline (Vite in a WP theme)

`themes/<theme>/vite.config.js` builds `assets/` into `assets/dist/.vite/manifest.json`
(gitignored), which `inc/enqueue.php` reads for the hashed filenames — `wp-frontend` owns that.
The DDEV part: the dev loop is `ddev start && (cd web/app/themes/<theme> && npm run dev)`, and
HMR needs DDEV's origin (5173 is exposed via its router):

```js
// vite.config.js
export default {
  server: {
    origin: 'https://<ddev-project>.ddev.site:5173',
    hmr: { host: '<ddev-project>.ddev.site' },
  },
};
```

## Custom-app variant (non-Bedrock)

`site.yml`'s `structure.type` names one of **three** layouts, and it is the field to
read before running any path-dependent command:

| `structure.type` | WP core | content | `wpcli_path` |
|---|---|---|---|
| `bedrock` | `web/wp/` | `web/app/` | `web/wp` |
| `custom-app` | `app/wp/` | `app/content/` | `app/wp` |
| `custom-site` | site root | `wp-content/` | `.` |

`custom-app` is a handful of legacy sites (some VAD subsites). `custom-site` is a
plain WordPress tree with no Composer webroot split — no `config/environments/`, so
per-env config lives wherever that site put it; check before assuming Bedrock's
answer. `wp-cli.yml` mirrors `wpcli_path` in every case, and the `Makefile` paths
shift with it. Composer rules, WP-CLI and Vite work the same across all three.

## Anti-patterns

| Smell | Fix |
|---|---|
| `wp` without `ddev wp` prefix in a DDEV project | Use `ddev wp …` so PHP version + DB connection match the container |
| Hardcoded `--path=web/wp` in scripts instead of `wp-cli.yml` | One canonical path declaration in `wp-cli.yml` |
| `wp cache flush` on a site with object-cache exclusions | Always inspect `object-cache.php` first; for VAD/LMS sites, use targeted invalidation |
| Vite dev server on `localhost:5173` instead of DDEV URL | Use the DDEV-aware `server.origin` (see Vite section above) |
| `composer install` without `--no-dev --optimize-autoloader` on a deploy | Deploy variants must use the optimized form (Bedrock relies on the optimized autoloader) |
| Editing `web/wp/wp-config.php` directly | Bedrock supplies it; per-env config goes in `config/environments/<env>.php` (see bedrock-composer) |

## See also

- `netdust-devops:devops` — the branch flow, make verbs, deploy gate and ledger, site.yml
- `bedrock-composer` — Bedrock layout fundamentals, Composer dependency rules
- `wp-frontend` — theme.json, blocks, asset pipeline details
- `wp-security` / `wp-database` — discipline skills for WP-specific work
- `ntdst-framework` / `ntdst-patterns` / `ntdst-framework` — the framework conventions inside `<project>-core`
- `/deploy` — slash command that dispatches per `site.yml`'s `deploy.method`
- `netdust-devops` — `dist/mk/wp.mk` carries the WP data verbs (pull, refresh, block-mail)
