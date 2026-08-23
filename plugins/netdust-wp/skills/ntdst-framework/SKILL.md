---
name: ntdst-framework
description: >
  Use when writing, reviewing or planning ANY PHP in an NTDST WordPress project —
  a service, handler, CPT, route, template, admin screen, REST or AJAX endpoint,
  asset enqueue, or the plugin's own boot. Covers ntdst-core AND ntdst-baseline.
  Triggers on "add a service", "new module", "register a CPT", "add an endpoint",
  "custom URL", "enqueue", and on the symbols NTDST_Service_Meta, ntdst_data(),
  ntdst_pages(), ntdst_actions(), ntdst_rest(), ntdst_response(), plugin-config.php.
---

# NTDST framework — the contract

Two packages, both mu-plugins, both Composer-managed:

- **ntdst-core** (4.2.0) — DI container, boot, data layer, the four output surfaces.
- **ntdst-baseline** (2.0.0) — the WordPress-gaps layer: security headers, head
  cleanup, SEO, schema, maintenance, cache headers. See `references/baseline.md`.

**Read the source before you write.** This file is the contract — the decisions and
the convergence points. It is deliberately not an API inventory: core throws
`InvalidArgumentException` naming every valid field type, `NTDST_Theme::__call()`
throws for every retired wrapper, and `NTDST_Rest` refuses a route carrying an
option it does not know. The framework tells you what exists. What it cannot tell
you is in `references/traps.md`, and you should read that.

## Retired — a caller of any of these gets a fatal, deliberately

v3.0.0 renamed the routing surface with **no aliases and no shims**; 4.0.0 removed
the sector system. There is no `class_alias()` anywhere in the package.

`ntdst_router()` · `ntdst_route()` · `NTDST_Router` · `NTDST_Endpoints` ·
`ntdst_api_action()` · `NTDST_SectorRegistry` · `ntdst_sectors()` · the `sectors`
metadata key · `NTDST_Query_Cache` · `ntdst_query_cache()` · `ntdst_clear_posts_cache()` ·
`ntdst_invalidate_post_type()` · `ntdst_get_posts_fast()` · `$model->cache(N)` ·
`NTDST_Cors_Policy` (never existed in any version) · `api/Endpoints.php` (now `api/Actions.php`)

On `NTDST_Theme`, whose `__call()` **throws `BadMethodCallException`**:
`apiAction()` · `register()` · `taxonomy()` · `module()` · the `assets` config key
(deleted — an `assets` block in theme-config.php enqueues nothing, silently).

Meeting one in a project means that project is on an older core or was written
against one.

## Pick the door

| Need | Door |
|---|---|
| A front-end page / custom URL | `ntdst_pages()->path()` |
| Same-origin in-page JS command | `ntdst_actions()->register()` |
| A resource route, headless or third-party caller | `ntdst_rest($ns)` |
| File bytes | `add_filter('ntdst/api_download/{action}', …)` + `ntdst_download()` |

Never reach for `ntdst/api_data` for a cross-origin caller: an anonymous WP nonce is
a shared, non-origin-bound token that authenticates nothing for a cookie-less client.

**A custom URL needs BOTH a rewrite rule and a route.** `NTDST_Pages` matches on
`REQUEST_URI`; the rewrite exists only so WordPress does not 404 the URL before
routing runs. The query var's name is yours and is never read.

```php
add_rewrite_rule('^share/items/([^/]+)/?$', 'index.php?myproject_route=1', 'top');
add_filter('query_vars', fn($v) => [...$v, 'myproject_route']);
ntdst_pages()->path('share/items/:slug', $cb);          // GET
ntdst_pages()->path('share/items', $cb, 'POST');        // method is the THIRD arg
```

Flush after adding rules: `ddev wp rewrite flush`. There is no `->get()`/`->post()`.

**`ntdst_actions()->register($action, $handler, $opts)`** takes exactly four opts —
`public`, `cap_type`, `capability`, `priority`. `'public' => true` puts the action on
`ntdst/api/public_actions` and is **never floored**: anonymous reachability is not
conditional on a capability. A `cap_type` floor is DERIVED from the post type and is
the one to prefer; a literal `capability` is correct only while that type's
`capability_type` is still `'post'`. Either floor bites at **dispatch**, ahead of the
handler, **fails closed** on an empty or unresolvable cap, and sits ALONGSIDE the
handler's own per-row check — never replacing it. With neither opt the action is
login-required.

**`ntdst_rest($ns)->post($route, $handler, $opts)`** consumes exactly `permission`,
`rate_limit`, `rate_window` and `cors`, and passes `args`, `schema`, `show_in_index`,
`allow_batch` to WordPress. `permission` is **required and must be callable** or the
route is refused. **`cors` (4.1.0) is the real CORS answer** — declare the exact
origin there; do not hand-roll `Access-Control-*` headers and do not reach for
`NTDST_Cors_Policy`, which has never existed in any version.

## Boot

`plugin-config.php` returns the config; Bootstrap reads only these keys under
`services`: `core`, `admin`, `conditional`, `auto_discover`, `discovery_paths`,
`overrides`.

Three phases, each with a hook to hang on:
`register()` → `ntdst/services_registered` → `bootCore()` → `ntdst/core_ready` →
`bootFeatures()` → `ntdst/features_ready`.

**Bootstrap calls only `metadata()`.** There is no `boot()` or `init()` lifecycle
method — a service's constructor runs its own `init()` by convention, and that is
where hooks get registered.

## Service, or plain class?

A **service** hooks into WordPress at boot (`admin_menu`, `rest_api_init`,
`wp_enqueue_scripts`, cron). It implements `NTDST_Service_Meta` and is listed in
`plugin-config.php` or auto-discovered from a `discovery_paths` root.

Everything else — repositories, calculators, stores, handlers, bridges — is a
**plain class**, resolved lazily by DI autowiring. Do not make it a service. An
admin controller or a metabox is a sub-component: instantiate it inside the owning
service's `init()`.

Auto-discovery scans the **root** of each `discovery_paths` entry, never
subdirectories. A namespaced service in a subdirectory must be listed explicitly.

## Enable / disable / configure a service

Three levels, all keyed on the service **slug**, all framework-owned names:

```php
metadata()['enabled'] => false                              // never loads
add_filter("ntdst_service_{$slug}_enabled", '__return_false');
update_option("ntdst_service_{$slug}", '0');
apply_filters("ntdst_service_{$slug}_config", $defaults);   // in YOUR service
```

Resolved, for `AdminUIService` (slug `admin_ui`): `ntdst_service_admin_ui_enabled`,
`ntdst_service_admin_ui_config`, option `ntdst_service_admin_ui`. `plugin-config.php`'s
`services.overrides.admin_ui` is hung on the `_config` hook by Bootstrap at priority 1 —
so a service applying any other name **never receives its own override**.

The slug is a pure function of the class: `Service` stripped, camelCase →
snake_case, a run of capitals kept as one token — `AdminUIService` → `admin_ui`.
A declared `metadata()['name']` pins it instead (whitespace-split, lowercased).

**Never project-prefix these two hooks.** `netdust_{slug}_*` was the retired shape;
there is no shim. See `references/traps.md` — the `_enabled` one fails open.

## Data

**All CPT data access goes through the domain's repository.** A service, template or
handler reaching for `ntdst_data()` directly is drift — it bypasses the repository's
validation and its vocabulary, and it is how the same query ends up written four
ways. Templates cannot use constructor DI, so they resolve it:
`ntdst_get(FooRepository::class)->…`.

**A pass-through method is drift, not abstraction.** A repository method that only
forwards to `ntdst_data()` with no added meaning earns nothing and hides the real
call site.

**Never swallow a `WP_Error`.** Every `create`/`update`/`delete` returns one on
failure; check it and propagate. `return false` loses the reason.

`ntdst_data()->register($type, $config)` returns `NTDST_Data_Model|WP_Error`.
Registration is **private by default** — opt in with `'public' => true`. Taxonomies
are declared with the model under `taxonomies`, with optional idempotent `terms`.

Reads are **publish-only by default**, on both `find()` and `getMeta()`. An admin
screen that wants a draft says so: `find($id, 'any')`. Authorization is the
caller's job, in the handler, every time.

`find()` and `first()` return `WP_Post` with `->fields` populated — not an array.
`get()` returns arrays.

**Query scopes** (named, reusable query fragments):

```php
// per model, in its config
'scopes' => ['upcoming' => fn($m) => $m->whereDate('post_date', '>=', 'now')],
// or globally, for any model
NTDST_Data_Manager::addScope('published', fn($m) => $m->where('post_status','publish'));

$model->scope('upcoming')->limit(10)->get();
```

Resolution is **model-first, then global** — a model shadows a global of the same
name. An unknown scope throws.

**A filterable field over `/wp/v2/<type>` is a parked core feature, not a site
hand-roll.** When a site wants `GET /wp-json/wp/v2/gigs?venue_city=Ghent`, do not
write `rest_{type}_collection_params` + `rest_{type}_query` in the site and do not
add a list route whose only job is "filtered by one meta key". Read
`ntdst-core/docs/parked/rest-query.md`: the design (`'rest_query' => true` on the
field, `register()` hands it to WordPress) is waiting for exactly this consumer —
the site IS the named consumer §6.1 of `philosophy.md` asks for. Open the one-task
spec in core; the site declares the key once core ships it.

## Templates and assets

`ntdst_response()` is the one place the `{success,…}` envelope is built.
`render()` echoes and exits; `html()` returns a string; `page()` hands a path back
to `template_include` so `wp_head()`/`wp_footer()` still fire.

Template paths are registered live and read on every `locate()` — there is no path
cache to clear. Resolved files are cached, positive hits only.

Assets are **explicit**, never config:

```php
$theme->style('handle', $src, $deps, $ver, 'all', $priority);
$theme->script('handle', $src, $deps, $ver, $in_footer, $priority);
```

A child theme overriding its parent needs a late `$priority` (YOOtheme children
use 20). For `admin_enqueue_scripts`, use `$theme->on()` — there is no admin variant.

## Reference

| File | Content |
|---|---|
| `references/traps.md` | What the source will not tell you. Read before writing. |
| `references/baseline.md` | ntdst-baseline: its services and its filter surface. |
