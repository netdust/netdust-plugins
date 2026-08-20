# ntdst-baseline (2.0.0)

The WordPress-gaps layer: the things every Netdust site needs and WordPress does
not ship. A sibling mu-plugin to ntdst-core, Composer-managed, **not** a fork of it.

**No site-specific value lives in this package.** Everything is injected through
`ntdst/baseline/*` filters. If you find a domain, a company name or a schema value
hardcoded in it, that is drift — put it behind the filter.

It defers all wiring to `after_setup_theme` (after `plugins_loaded:5`) so the core
container is guaranteed to exist, and **fails quiet** if the framework is absent —
it never fatals a site that has ntdst-baseline without ntdst-core.

## Six modules, all on by default

```php
add_filter('ntdst/baseline/modules', fn($m) => [...$m, 'schema' => false]);
```

| Module | Service | Owns |
|---|---|---|
| `security` | `SecurityService` | security headers (`SecurityHeaderPolicy`) |
| `head_cleanup` | `HeadCleanupService` | stripping WP's `wp_head` noise |
| `seo` | `SeoService` | meta tags |
| `schema` | `SchemaService` | JSON-LD (`JsonLd`) |
| `maintenance` | `MaintenanceService` | maintenance mode |
| `cache_headers` | `CacheHeadersService` | cache headers (`CacheHeaderPolicy`) |

Turning a module off is how you hand its job to something else — a plugin, a host,
a CDN. Two things writing the same header is the drift to look for.

## The configuration surface

Each module takes one `config` filter, merged over its defaults by
`Config::merge()`:

```
ntdst/baseline/security/config        ntdst/baseline/seo/config
ntdst/baseline/head_cleanup/config    ntdst/baseline/schema/config
ntdst/baseline/maintenance/config     ntdst/baseline/cache_headers/config
```

Schema carries a richer surface, because a site's structured data is the part that
genuinely differs: `schema/website`, `schema/webpage`, `schema/article`,
`schema/main_entity`, `schema/faq_items`, `schema/custom`, and
`schema/post_type/{type}`.

Also: `ntdst/baseline/seo/meta`, `ntdst/baseline/purge`, and
`ntdst/baseline/booted` (fired once, for anything that must run after the layer is
up).

## Reviewing a site for consistency

The question is not "does it work" but **"is this solved here, or twice?"**

- A theme or project service re-emitting a security header, a canonical tag, a
  JSON-LD block or a cache header that a baseline module already owns → drift.
  Either configure the module or turn it off; never both.
- A hardcoded site value inside the package → drift.
- A project reaching for its own login throttle or client-IP resolution → drift.
  Both converged onto ntdst-core (`NTDST_RateLimiter`, `NTDST_ClientIp`); the
  duplicate is the thing to remove. See the limiter's three verbs in `traps.md` —
  a lockout CHECK must not spend budget.
