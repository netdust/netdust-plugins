---
description: Clear all Statamic + Laravel caches and warm the stache (use after content blueprint changes)
---

Clear all caches and warm the stache.

Run, in order (inside DDEV — `make` targets handle that automatically):

```bash
make cache-clear      # clears Laravel caches + stache:clear
make stache-warm      # php please stache:warm
ddev exec php please search:update --all   # rebuild search index (only if search is configured)
```

If `make cache-clear` / `make stache-warm` aren't in this project's Makefile, the equivalents are:

```bash
ddev exec php artisan cache:clear
ddev exec php artisan config:clear
ddev exec php artisan route:clear
ddev exec php artisan view:clear
ddev exec php please stache:clear
ddev exec php please stache:warm
```

Use this after:
- Editing blueprints, fieldsets, or collections (stache must be rebuilt)
- Editing globals
- Pulling fresh content via `make sync-down`
- Switching branches

If a page still shows stale content, also clear the browser cache and any Cloudflare/static cache layers — Statamic's static caching strategy in production is `full`.
