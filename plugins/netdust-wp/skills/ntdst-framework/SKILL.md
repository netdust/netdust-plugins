---
name: ntdst-framework
description: >
  Use when writing, reviewing or planning ANY PHP in an ntdst-core 5.x WordPress
  project — a service, data model, CPT field, route, page URL, template, admin
  screen, REST endpoint, or the plugin's own boot. Covers ntdst-core AND
  ntdst-baseline. Triggers on "add a service", "new module", "register a CPT",
  "publish a field", "add an endpoint", "custom URL", "make it public", "why is
  this 404", and on the symbols ntdst_rest(), ->public(), show_in_rest,
  NTDST_FieldTypes, ntdst_data(), ntdst_pages()->path(), ntdst_response(),
  NTDST_Service_Meta, plugin-config.php.
---

# NTDST framework — the contract

ntdst-core 5.0.0 — anchored on specs core-shape rev 3 / field-types rev 3 / core-trim rev 2, README @ 5284cfb; pre-tag

- **ntdst-core** (5.0.0) — boot, container, data layer, one HTTP surface, pages, templates.
- **ntdst-baseline** (2.0.0) — the WordPress-gaps layer. See `references/baseline.md`.

**Read the source before you write.** This file carries the decisions and the convergence points, not an API inventory: core refuses what it does not know, and names the replacement when it refuses. `NTDST_FieldTypes::get()` throws and names the canonical type; a write verb with no capability does not register; a listed class PHP cannot resolve is refused at `register()`. What a signature cannot tell you is in `references/traps.md`. Read that before writing. 5.0.0 shrank core to what only a framework can own; a primitive WordPress already ships is not one, and the admission test is `docs/philosophy.md` §6.

## Retired — a caller gets a fatal, deliberately

There is no `class_alias()` and no shim anywhere in the package. A renamed HOOK is worse than a fatal: it is silently inert. Check every listener before you bump.

**v3/v4, still retired:** `ntdst_router()` · `ntdst_route()` · `NTDST_Router` · `NTDST_Endpoints` · `ntdst_api_action()` · `NTDST_SectorRegistry` · `ntdst_sectors()` · the `sectors` metadata key · `NTDST_Query_Cache` · `ntdst_query_cache()` · `ntdst_clear_posts_cache()` · `ntdst_invalidate_post_type()` · `ntdst_get_posts_fast()` · `$model->cache(N)` · `NTDST_Cors_Policy` (never existed) · `api/Endpoints.php` · on `NTDST_Theme`: `apiAction()` · `register()` · `taxonomy()` · `module()` · the `assets` config key.

**The command dispatcher — there is ONE HTTP surface now:** `ntdst_actions()` · `NTDST_Actions` · `ntdst/api_data/{action}` · `ntdst/api/public_actions` · `ntdst/api/allowed_origins` · `ntdst/api/rate_limit/{action}` · `ntdst/api/rate_window/{action}` · `ntdst_api_floor_cap()` · `POST /ntdst/v1/get_nonce` · `assets/js/ntdst-api.js` · `window.ntdstAPI` · `ntdst_enqueue_api_client()`.

**Route surface:** `'permission' => 'public'` (the STRING — `->public()` is the one door) · per-route `'cors'` · `before_dispatch` · `corsFor()` · `corsDecisionFor($route, $origin)` · `chargePreflight` · `surface()` · `publicSurface()` · `opaqueSurface()` · `forgetSurface()` · `$surface` · `public_fields` · `publicRows` · `publicRow` · `getPublicShape` · `restSubFields()` · `restSchemaFor()`.

**Response and templates:** `apiSuccess()` · `apiError()` · `apiSuccessResponse()` · `apiErrorResponse()` · `json()` · `jsonPayload()` · `render()` · `renderError()` · `getErrorHtml()` · `commitRenderStatus()` · `$mimeTypes` · `getMimeType()` · `registerMimeType()` · `ntdst_redirect()` · `NTDST_Response::addPath()` · `NTDST_Template_Loader::templateInclude()`.

**Field types — 13 names, each a fatal at `register()` naming its canonical:** `integer`, `signed_int`, `number` → `int` · `double`, `decimal` → `float` · `boolean` → `bool` · `string` → `text` · `longtext` → `textarea` · `wysiwyg`, `content` → `html` · `datetime` → `date` · `person`, `post_relation` → `relation`. With them: `getDefaultSanitizer()` · `sanitizeBoolean()` · `sanitizeDate()` · `sanitizeJson()` · `sanitizeRepeater()` · `sanitizeNestedArray()` · `sanitizeAttachmentId()` · `MARKER_ONLY_REQUIRED_TYPES` · `render_repeater_media_cell()` · `NTDST_RelationField::metadata()`.

**Boot:** `discoverServices()` · `discoverServicesInPath()` · `getClassNameFromFile()` · `isInConditionalConfig()` · `services.auto_discover` · `services.discovery_paths` · `services.handlers` · `isServiceEnabled()` · `getServiceConfig()` · `getServices()` · `getBootedServices()` · `hasService()` · `isBooted()` · option `ntdst_service_{slug}` · filter `ntdst_service_{slug}_enabled` (**it FAILED OPEN** — a service kept off through it BOOTS after the upgrade) · filters `netdust_{slug}_config` and `ntdst_service_{slug}_config`, both now `ntdst/service/{slug}/config` · slug `admin_u_i`, now `admin_ui`.

**Container:** `ntdst_make()` · `make()` · `call()` · `forget()` · `flush()` · `keys()`.

**Logger:** the `log_entry` post type · the `database` handler · `ntdst_log_database_enabled` · `ensureModelRegistered()` · `recent()` · `clearOld()` · `addHandler()` · `removeHandler()` · `setMinLevel()` · `setBatchingEnabled()` · `ntdst_log_debug()` · `ntdst_log_info()` · `ntdst_log_error()` · the `ntdst_log*` hooks.

**Query:** `ntdst_get_formatted_posts()` · `getFormattedPosts()` · `getPostMeta()` · `getPostTerms()` · `attachTerms()` · `syncTerms()` · `detachTerms()` · `whereDate()` · `orWhere()`.

**Model hooks — renamed, and a listener on an old name is inert:** `ntdst_model_create_before` / `_after` · `ntdst_model_update_before` / `_after` · `ntdst_model_delete_before` / `_after`, all now `ntdst/model/{creating,created,updating,updated,deleting,deleted}`.

**Scheduler, gone from core:** `NTDST_Scheduler` · `ntdst_scheduler()` · `ntdst_schedule_recurring()` · `ntdst_clear_recurring()`.

**Mailer, moved to `netdust-mail`:** `NTDST_Mailer` · `ntdst_mail()` · `ntdst_send_mail()` · `ntdst_notify()` · `ntdst_wrap_email_in_layout()` · `queue()` · `toArray()` · `header()` · cron `ntdst_send_queued_mail` (**a pending event survives the upgrade with no listener; queued mail is dropped silently**) · `ntdst_wrap_all_emails` · `ntdst_mail_attachment_bases` · `ntdst_email_layout_paths` · `ntdst_mail_before_send` · `ntdst_mail_sent` · the `ntdst_notification*` hooks · `templates/emails/`.

**Theme:** `mixin()` · `__call()` · `wireMixins()` · `$theme->mail()` · `Theme::when()` · `templatePath()` · `Theme::style()` · `Theme::script()` · `Theme::single()` · `Theme::page()` · `Theme::archive()`. These are the THEME's copies only — `NTDST_Pages` keeps its own `single()`, `page()`, `archive()`, `template()` and `when()`, which are a different thing and stay. `$theme->style()` has no replacement on the theme: enqueue with WordPress's own functions.

## Pick the door

| Door | What it is for — and the invariant it establishes |
|---|---|
| `show_in_rest => true` on the field | A field the front end reads. WordPress serves it on `/wp/v2/<type>`; core shapes no response. Rule: a plain collection of your own post type answers the question — INV-1. |
| `ntdst_rest($ns)` with a capability | A command, or a list WordPress's collection cannot express. Rule: the caller asks for an ACTION, or for rows `/wp/v2` cannot select — INV-2, INV-3. |
| `ntdst_pages()->path()` | A URL that is not a post. Rule: a human types it and expects HTML, and no post type owns it — INV-6. |

Three doors, and no fourth. There is no command dispatcher and no `admin-ajax` handler. A route whose permission is decided anywhere but its own registration is the bypass INV-2 catches.

## Data declares, WordPress reads

**The vocabulary is 17 names, closed:** `int` · `float` · `bool` · `text` · `textarea` · `html` · `email` · `url` · `date` · `select` · `array` · `json` · `relation` · `gallery` · `image` · `file` · `repeater`. There are no aliases. `NTDST_FieldTypes::get($name)` is the one public read: one entry says what cleans a value, what it publishes, what draws it, whether it may sit in a repeater row, and how it reads back. No filter and no registration method — a pluggable vocabulary is one a plugin widens with a type whose sanitizer is a no-op (INV-8).

**A field leaves the model only when it says so.** `'show_in_rest' => true` on the field description, with WordPress's meaning: opt in, nobody-named-nobody-leaves. Core adds `custom-fields` to the type's `supports` once one field is declared. `declaresRest()` is the one reader, and the model never shapes a response (INV-1). A field declared by mistake is a disclosure — `references/traps.md` says what that `custom-fields` support widens.

- **A repeater publishes all-or-nothing.** Every sub-field must declare itself, or the whole repeater is unpublishable and warns once per model.
- **`json` and `array` never publish.** `rest_is_array()` refuses a keyed map and WordPress nulls the value, so neither was ever readable over `/wp/v2`.
- **`int` is signed.** `-500` stores as `-500`; a discount in cents is a negative int.
- **`html` is `wp_kses_post()`'d before anything else sees it**, on a REST write too. A declared `sanitizer` COMPOSES on the registry's, never replaces it, and must be idempotent — `register_post_meta()` runs it again on every write.
- **Four types cannot sit in a repeater row: `html`, `relation`, `gallery`, `repeater`.** A `sub_fields` declaration naming one is refused at `register()`, nested repeaters included. A sub-field may not declare a `sanitizer` at all — nothing ever ran it, and a security declaration that does nothing is worse than none.

**Model lifecycle hooks** are `ntdst/model/creating` · `created` · `updating` · `updated` · `deleting` · `deleted`, plus `registering` and `registered` — same arguments as the retired names, and no shim.

**One query API: the chain.** `ntdst_data($type)->where(…)->withMeta()->get()`. There is no formatted-posts helper and no term helper — terms are `wp_set_object_terms()` and `wp_get_object_terms()`, WordPress's own.

**All CPT data access goes through the domain's repository.** A service, template or handler reaching for `ntdst_data()` directly is drift: it bypasses the repository's validation and vocabulary, and it is how one query ends up written four ways. Templates have no constructor DI, so they resolve `ntdst_get(FooRepository::class)`.

**A pass-through method is drift, not abstraction.** A repository method that only forwards to `ntdst_data()` with no added meaning hides the real call site.

**Never swallow a `WP_Error`.** Every `create`/`update`/`delete` returns one on failure. `return false` loses the reason.

**Registration is private by default** — opt in with `'public' => true`. **Reads are publish-only by default**, on `find()` and `getMeta()` alike; an admin screen wanting a draft says `find($id, 'any')`. Authorization is the caller's job, in the handler, every time. `find()` and `first()` return `WP_Post` with `->fields`; `get()` returns arrays.

**Query scopes** are named, reusable query fragments — per model under `scopes`, or globally with `NTDST_Data_Manager::addScope()`. Resolution is model-first, then global, so a model shadows a global of the same name. An unknown scope throws.

**A filterable field over `/wp/v2/<type>` is a parked core feature, not a site hand-roll.** Do not write `rest_{type}_collection_params` + `rest_{type}_query` in the site, and do not add a list route whose only job is "filtered by one meta key". Read `ntdst-core/docs/parked/rest-query.md`: the design waits for this consumer. Open the one-task spec in core; the site declares the key once it ships.

## Rest is the one surface

```php
ntdst_rest('shop/v1')
    ->get('/prices', [$c, 'prices'])->public()          // anonymous
    ->get('/orders', [$c, 'index'])                     // internal, the default
    ->post('/orders', [$c, 'store'], ['permission' => 'edit_shop_orders']);
```

- **Internal is the default.** A route that says nothing gets the string `'is_user_logged_in'` as its `permission_callback`.
- **`->public()` is the one door to anonymous**, and it marks only the declaration its verb just returned. No option VALUE opens a route — that is why the string was dropped: a value reaches config, a constant and a merge; a chained call does not.
- **A string permission is a CAPABILITY**, asked as `current_user_can($cap)`, never a function name. `'logged_in'` is the one word that is not. `'Public'` and `' public '` are capabilities nobody holds, not near misses normalised into an opening. A callable is used as given.
- **A write verb with only a posture does not register.** Reads are `GET`, `HEAD` and `OPTIONS`; every other verb is a write, custom ones included. A write names a capability or hands over its own callable, or it is refused with one `_doing_it_wrong` and is absent from the route table (INV-3).
- **`defaults()` may narrow, never open.** A namespace default may set `'logged_in'` or a capability; `'public'` or a callable is refused and dropped.
- **`cors()` is site-wide, declared apart from any route.** Origins are ADDED to WordPress's own `allowed_http_origins`, and every allowed question goes to `is_allowed_http_origin()` — core keeps no second list (INV-5). `'*'` is refused, credentials belong to the declaration that NAMED the origin, and the declaration is scoped to REST requests only.
- **`rate_limit` and `rate_window`** are the route's own options. Nothing is metered unless the route asks. A limit is charged from the permission callback (INV-7).
- **The client is `wp.apiFetch`.** It sends the `wp_rest` nonce in `X-WP-Nonce` and refreshes a stale one. Core mints no nonce and runs no origin check — CSRF is WordPress's (INV-4). A nonce is a CSRF token, never access control.
- **A handler returns `WP_REST_Response` or `WP_Error`.** There is no envelope: WordPress builds the body, so a client that read `response.data.thing` reads `response.thing` now.

To assert your anonymous surface, ask the server: `rest_get_server()->get_routes($ns)` filtered on `permission_callback === '__return_true'`. A capability route and a rate-limited route both register a CLOSURE, so never settle a route by the TYPE of its callback — settle it by reading what the route declared.

## Pages on rewrite rules

```php
ntdst_pages()->path('/card/:slug', $cb);            // GET
ntdst_pages()->path('/card', $cb, 'POST');          // method is the THIRD arg
```

`path()` compiles `:param` placeholders into `add_rewrite_rule()` plus registered query vars, and dispatches on `template_redirect` reading `get_query_var()`. You write no rewrite rule and no `query_vars` filter yourself — that was the v4 shape.

- **The callback returns a template path, `null`, or `false`.** A path goes to WordPress; `null` does nothing; `false` is a refusal and calls `$wp_query->set_404()` so WordPress's own 404 runs. A callback never exits inside a filter (INV-6).
- **A pattern whose first segment is a placeholder is refused** with `_doing_it_wrong` and adds no rule. `/:slug` would shadow every URL on the site.
- **Rules flush when their hash changes**, not on every request.
- **`template()` · `single()` · `page()` · `archive()` · `when()`** stay as filter wraps whose callback returns a path.

**One loader.** `NTDST_Template_Loader::locate()` is the only search over the registry and `addPath()` the only registration. `html()` returns a string; `page()` plus `ntdst_page_data()` is the one way data reaches a template. `download()` and `inline()` send bytes with WordPress's own MIME table (`wp_check_filetype()` + `wp_get_mime_types()`) and `send_nosniff_header()`. Name files the way WordPress names them — `single-gig.php`, `page-about.php`; `{$type}_template_hierarchy` is the candidate list core reads.

## Boot: you load, core resolves

**Core loads nothing by guessing** (INV-10). It installs no autoloader, scans no directory, parses no PHP source and derives no path from a class name. You `require_once` your service files or autoload them with Composer, then list the class names in `services`. A listed class PHP cannot already resolve is refused at `register()` with a `_doing_it_wrong` naming the class and the sector, plus an error-level log line — `_doing_it_wrong()` is `WP_DEBUG`-gated, and a missing service would otherwise be silent on a live site.

`plugin-config.php` returns the config. Bootstrap reads `core`, `admin`, `conditional` and `overrides` under `services`.

**Two switches, and there is no third:** `metadata()['enabled'] => false`, or a `services.conditional` entry whose condition returns false.

**Overrides reach a service through one filter**, which the service applies itself:

```php
$config = apply_filters("ntdst/service/{$slug}/config", $defaults);
```

Bootstrap hangs `services.overrides.{slug}` on that exact hook. An overrides key naming no listed service is REFUSED at `register()`; a key naming a listed service that simply did not boot is silent, on purpose. The slug is a pure function of the class — `Service` stripped, camelCase to snake_case, a run of capitals kept as one token — so `AdminUIService` is `admin_ui` and `APIRouterService` is `api_router`. A declared `metadata()['name']` pins it instead, and CHANGES that service's config-filter key.

**Three lifecycle hooks:** `ntdst/services_registered` → `ntdst/core_ready` → `ntdst/features_ready`. **Bootstrap calls only `metadata()`** — there is no `boot()` or `init()` lifecycle method. A service's constructor runs its own `init()` by convention, and that is where hooks get registered.

**Service, or plain class?** A **service** hooks into WordPress at boot (`admin_menu`, `rest_api_init`, `wp_enqueue_scripts`, cron). It implements `NTDST_Service_Meta` and is listed in `plugin-config.php`. Everything else — repositories, calculators, stores, handlers, bridges — is a **plain class**, resolved lazily by autowiring. Do not make it a service. An admin controller or metabox is a sub-component: instantiate it inside the owning service's `init()`.

**Load order.** `ntdst-core.php` is the BASE mu-plugin. An mu-plugin that constructs `NTDST_Theme` while core is a regular plugin fatals on 5.0.0.

## One of each

**Logger.** `ntdst_log($channel)`, then `debug()` · `info()` · `warning()` · `error()` · `critical()`. Lines land in a batched file under `WP_CONTENT_DIR/logs` and in `error_log`. Two handlers, both built in. A log line is not an event bus and not content.

**Container.** `set()` · `get()` · `has()`, reached as `ntdst_set()` · `ntdst_get()` · `ntdst_container()`. Constructor autowiring resolves what you did not register. To reset, build a fresh one: `new NTDST_Container()`.

**Theme.** Config plus `setup_theme()`, and `on()` / `filter()` for chainable configuration. There is no assets API and there are no mixins — write the globals directly: `ntdst_data()`, `ntdst_pages()`, `ntdst_response()`, `ntdst_log()`. Enqueue with WordPress's own `wp_enqueue_style()` / `wp_enqueue_script()` on `wp_enqueue_scripts`; a child theme overriding its parent needs a late priority.

**Mail.** Not core. `\Netdust\Mail\Mailer` in the `netdust-mail` plugin, or `wp_mail()` for a plain send.

**Scheduling.** Not core. WordPress ships the primitive:

```php
if (!wp_next_scheduled($hook)) {
    wp_schedule_event(time(), 'daily', $hook);
}
add_action($hook, $cb);
```

## Reference

| File | Content |
|---|---|
| `references/traps.md` | What the source will not tell you. Read before writing. |
| `references/baseline.md` | ntdst-baseline: its services and its filter surface. |
