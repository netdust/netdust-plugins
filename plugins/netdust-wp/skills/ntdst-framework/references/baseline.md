# ntdst-baseline (2.3.0)

The WordPress-gaps layer: the things every Netdust site needs and WordPress does
not ship. A sibling mu-plugin to ntdst-core, Composer-managed, **not** a fork of it.

**No site-specific value lives in this package.** Everything is injected through
`ntdst/baseline/*` filters. If you find a domain, a company name or a schema value
hardcoded in it, that is drift — put it behind the filter.

It defers all wiring to `after_setup_theme` (after `plugins_loaded:5`) so the core
container is guaranteed to exist, and **fails quiet** if the framework is absent —
it never fatals a site that has ntdst-baseline without ntdst-core.

It conflicts with `ntdst-core < 4.2` — Composer refuses the pair rather than
booting a baseline against a core that lacks what it calls.

## Seven modules — six on by default, one opt-in

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
| `yootheme` | `YOOthemeSourcesService` | **OFF by default** — ntdst-core models as YOOtheme builder sources |

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

## The yootheme module (2.2.0, working since 2.3.0)

Custom fields are invisible in the YOOtheme builder: YOOtheme discovers post meta
through its ACF package only, and this fleet never uses ACF. The module registers
every ntdst-core model as a builder source, so binding a field becomes layout work
instead of PHP.

**It is the one module that is off by default** — this package installs on every
site, and publishing a site's fields into a builder nobody opened is a change nobody
asked for. Opt in by ASSIGNMENT:

```php
add_filter('ntdst/baseline/modules', static function (array $modules): array {
    $modules['yootheme'] = true;

    return $modules;
});
```

Never `$modules + ['yootheme' => true]`. The union keeps the existing key, and this
module's default IS a key — so the union form reads as "enable" and changes nothing.

Type coverage: `int`/`float`/`bool` and the string family; `repeater` as a `listOf`
over an emitted row type; `relation` as a `listOf` of the related post type,
resolving **published posts only**; `image`/`file`/`gallery` as YOOtheme's own
`Attachment`, resolving to the attachment ID that type consumes, with
`thumbnail`/`medium`/`large` added beside its built-in `url`/`alt`/`caption`.
`array` and `json` are NOT mapped and their fields are dropped rather than defaulted
to `String` — a field missing from the picker is a question an editor asks, a field
rendering "Array" on a live page is one a visitor sees.

**A `relation` scoped to `attachment` resolves EMPTY through this module.** The
relation resolver keeps only `publish` posts and an attachment is `inherit`, so the
picker accepts a file (core's admin picker widens to `inherit`) and the page renders
nothing, silently. Declare `file`, `image` or `gallery` — the native media types
resolve through the `Attachment` closure with no status gate (josworld, 2026-09-03).

Two boundaries: the model DECLARATION is the allow-list, so undeclared meta is
unreachable; and a model whose `meta_prefix` is empty is refused whole, because its
declared names would compose to bare keys another plugin may own.

**Do not pin below 2.3.0.** `2.2.0` shipped this module inert — it booted after
models had registered, so it collected nothing, and read raw post meta instead of
core's decoded read. `2.2.1` fixed the boot order but still wrote a field's label to
`name` and its resolver to `resolve`, neither of which YOOtheme reads: no custom
field resolved on a page. Both fixed in 2.3.0, and `^2.2` resolves past neither.

## The purge door is a route, not an action (2.1.0)

Providers still attach to `do_action('ntdst/baseline/purge', $scope, $context)`, and
baseline still ships no destructive provider of its own. What changed is the manual
trigger. Until 2026-08-21 it was a command-router action, `ntdst/api_data/baseline_purge`
— a symbol core 5.0.0 retired. It is now a resource route:

```php
ntdst_rest('ntdst-baseline/v1')->post('/purge', $handler, ['permission' => 'manage_options']);
```

`POST /wp-json/ntdst-baseline/v1/purge`, plus an admin-bar node, firing scope `all`.
Gated twice on purpose: `NTDST_Rest` refuses to register a route declaring no
permission, and the handler re-checks `current_user_can()` and fails closed with an
error envelope (INV-4). Neither control replaces the other.

The old INV-2 warning — never add `baseline_purge` to `ntdst/api/public_actions` — is
obsolete by construction: there is no action to add, and a route with no permission
does not register at all. **If you find that warning repeated anywhere, it is
describing a door that no longer exists.**

Content-scope fires stay automatic and unauthenticated-safe (WordPress's own
content-mutation hooks are capability-gated upstream). A same-status repeat save is
rate-limited per `(scope, post_id)`; a genuine `post_status` transition always fires,
never counted against the limit — the one purge a cache provider can least afford to
miss.

## Reviewing a site for consistency

The question is not "does it work" but **"is this solved here, or twice?"**

- A theme or project service re-emitting a security header, a canonical tag, a
  JSON-LD block or a cache header that a baseline module already owns → drift.
  Either configure the module or turn it off; never both.
- A hardcoded site value inside the package → drift.
- A project hand-registering YOOtheme dynamic-content sources for ntdst-core fields
  → drift since 2.3.0; enable the `yootheme` module instead.
- A project reaching for its own login throttle or client-IP resolution → drift.
  Both converged onto ntdst-core (`NTDST_RateLimiter`, `NTDST_ClientIp`); the
  duplicate is the thing to remove. See the limiter's three verbs in `traps.md` —
  a lockout CHECK must not spend budget.
