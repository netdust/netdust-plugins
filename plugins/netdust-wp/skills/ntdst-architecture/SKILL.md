---
name: ntdst-architecture
description: >
  NTDST framework architecture, service lifecycle, DI container, routing,
  templating, and code standards. Use any time you are about to add, write,
  create, scaffold, design, plan, or review a Service, Handler, Module, CPT
  class, Repository, sub-service, admin controller, AJAX endpoint, REST
  controller, or WP-CLI command in an NTDST project (anything under
  `mu-plugins/<project>-core/Modules/` or matching `class *Service implements
  NTDST_Service_Meta`). Triggers on phrases like "add a service", "write a
  service", "create a service", "implement a service", "new module", "service
  that does X", "service with cron / hooks / DI", and on the keywords
  `NTDST_Service_Meta`, `AbstractService`, `metadata()`, `ntdst_get`,
  `ntdst_set`, `plugin-config.php`. MUST be consulted during implementation
  planning AND at code-writing time to ensure correct service boundaries,
  bootstrap lifecycle, DI patterns, PHP 8.1+ standards, and anti-pattern
  avoidance. Also activates during code review to verify NTDST conventions.
---

# NTDST Architecture Skill

> **Reference files** live in `references/` next to this SKILL.md.
> Read the relevant reference before implementing — don't guess at APIs.
>
> **Anchored on ntdst-core 4.x** (2026-08-20). v3.0.0 renamed the whole routing
> surface with no aliases and no shims, and 4.0.0 removed the sector system —
> a caller of a retired symbol gets a fatal, deliberately. If you meet
> `ntdst_router()`, `ntdst_route()`, `NTDST_Endpoints`, `ntdst_api_action()`,
> `NTDST_SectorRegistry` or `NTDST_Cors_Policy` in a project, that project is
> on an older core or was written against one — none of them exist now.

## Reference Index

| File | Read when... |
|------|-------------|
| `references/architecture.md` | Core principles, PHP standards, size limits, design patterns, project structure |
| `references/services.md` | Creating services — when to/not to, lifecycle, priorities, config, discovery, enable/disable |
| `references/container.md` | DI container, autowiring, bootstrap lifecycle, functions.php wiring, `plugin-config.php` (mu-plugins) / `theme-config.php` (themes) |
| `references/data-layer.md` | Model registration (**private by default**), field types, CRUD, `find()`'s status argument, query builder, metaboxes, and why the layer keeps no cache |
| `references/pages.md` | URL routes, template hooks, rewrite rules, return values |
| `references/response.md` | Template rendering, JSON output, email HTML, template resolution |
| `references/api-endpoints.md` | Same-origin AJAX actions (`ntdst/api_data`), nonce flow, JS client, rate limiting, security |
| `references/rest-cors.md` | **Resource routes** — `ntdst_rest()`, the closed option list, required-permission default, the double-permission quirk, and **the CORS gap** (core ships none) |
| `references/logger.md` | Logging levels, channels, database persistence, custom handlers |
| `references/mailer.md` | Email templates, queuing, attachments, event notifications |
| `references/anti-patterns.md` | What NOT to do — data, security, performance, services, YOOtheme |
| `references/plugin-scaffold.md` | Standalone plugin structure (own Container, ServiceProvider, not on ntdst-core) |
| `references/theme-api.md` | Theme fluent API — mixins, module config, routing shortcuts, assets |

---

## What a service actually IS

**A service is a Bootstrap-instantiated class that adds a specific feature to the site.**

That sentence is the whole definition.

**Mental model: a service is a plugin you didn't have to package.** WordPress plugins are self-contained features you can toggle off without deleting code. An NTDST service is the same idea, scoped to inside a single codebase instead of zipped up under `wp-content/plugins/`. One feature per service, same way one feature per plugin. Hooks register on bootstrap, same way plugins register on `plugins_loaded`. You don't `new` a service any more than you `new WooCommerce()` — the container resolves it. If you already think in plugins, you already think in services; the rules below are how that intuition lands in code.

Expanded:

- **"Bootstrap-instantiated"**: listed in the plugin/theme config's `services` array. The `NTDST_Bootstrap` lifecycle creates exactly one instance at the declared priority.
- **"Adds a feature"**: the constructor calls `$this->init()` which **registers something on the site** — WP hooks, CPTs via `ntdst_data()->register()`, shortcodes, admin menus, widgets, cron, REST endpoints, template filters. If the class doesn't *add* anything at boot time, it's not a service.
- **"Specific"**: one feature, one service. `SeoService`, `PortfolioService`, `HardeningService`, `ImportService`. A class that owns multiple unrelated features should be split.

### The promotion test

Before listing a class in `services`, ask:

> **Would I want a config-level toggle to disable this feature without deleting code?**

If yes → service.
If no → it's a sub-component. Instantiate it inside a parent service's `init()`.

Examples of sub-components (NOT services, even though they have hooks):
- `FooAdminController` — owned by `FooService`, instantiated inside its `init()`
- `FooDashboardWidget` — owned by `FooService`
- A single `sports-leagues/game/after_save` listener — fold into the parent service's `init()` OR make it a sub-component
- A WP-CLI command registration (`\WP_CLI::add_command(...)`) — one line in plugin bootstrap, not worth a service

Examples of dependencies (plain classes, NOT services):
- API clients (`VblApiClient`, `StripeApiClient`)
- Repositories
- Mappers, calculators, classifiers (pure functions)
- Value objects / DTOs
- Query helpers

Dependencies are resolved via DI autowiring when a service injects them. They never appear in the `services` list.

### Quick Decision Tables

### What to create

| Need | Pattern | Location |
|------|---------|----------|
| New site feature (enable/disable-worthy, hooks + config + DI) | **Service** | `services/MyService.php` (or `Modules/My/MyService.php`) |
| Sub-component of a service (admin controller, widget, hook-bundle) | **Plain class** instantiated in parent's `init()` | Alongside the service |
| Pure domain logic (rules, math, classification) | **Business class** | Alongside the service |
| Stateless utility | **Helper** (plain functions) | `helpers/` |
| Data model + CRUD | **Model** via `ntdst_data()->register()` | Inside a service's `init()` |
| Custom URL | **Route** via `ntdst_pages()->path()` | Inside a service |
| Command (same-origin AJAX) | `ntdst_actions()->register()` | Inside a service |
| Resource route (REST) | `ntdst_rest('ns/v1')->get()` / `->post()` | Inside a service |
| File bytes to the browser | Filter on `ntdst/api_download/{action}` + `ntdst_download()` | Inside a service |
| Template output | **Response** via `ntdst_response()` | Never raw `echo` in services |
| Standalone plugin (not ntdst-core) | **Plugin scaffold** | See `plugin-scaffold.md` |

**Split rule:** If a class has both hooks AND business logic, split into handler (thin WP boundary) + business class (pure, WP-free, testable). Services orchestrate; they don't compute.

→ For the full "when to create a service" decision tree, read `services.md`.

### Critical anti-patterns (quick check)

| ❌ Don't | ✅ Do |
|----------|-------|
| `new MyService()` inside a class | `ntdst_get(MyService::class)` |
| `implements NTDST_Service_Meta` on a class with no hooks | Plain class, resolved via DI autowiring |
| Service that doesn't ADD anything to the site at boot (no CPT, no hook, no shortcode, no menu) | It's a dependency, not a service — drop `NTDST_Service_Meta`, remove from config's `services` list |
| One-hook-only class listed as its own service | Fold as a sub-component into the owning feature's service |
| Admin controller / dashboard widget / metabox as its own top-level service | Sub-component — instantiate inside the owning feature service's `init()` (stride pattern: see `TrajectoryService::init()` instantiating `TrajectoryAdminController`) |
| `update_post_meta()` / `get_post_meta()` | `$model->update()` / `$model->find()->fields` |
| Raw SQL queries | Data Manager query builder |
| `$model->cache(N)`, `ntdst_query_cache()`, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()` | **Deleted.** Core's caching is the caching — just query |
| `ntdst_get_posts_fast()` | `ntdst_get_formatted_posts()` (same function, honest name) |
| `$model->find($id, true)` | Throws. The 2nd arg is a **post status** — pass `'any'` or a status array |
| `register()` with no `public` key, assuming it's public | It is **private** now. Opt IN with `'public' => true` |
| `current_user_can('edit_posts')` as a READ gate | Contributors hold it. Use `edit_others_posts`, resolved off the post-type object |
| Returning a raw `WP_Post` from a public API handler | Project an allow-list built by iterating the declared schema — `WP_Post` serialises `post_password` and every `_`-prefixed meta key |
| `echo` in a service | `ntdst_response()->render()` / `->json()` |
| `add_action()` scattered across methods | Group in `registerHooks()` / `init()` |
| `return false` on error | `return new WP_Error(...)` |
| Manual `template_include` filter | `ntdst_pages()->single()` / `->archive()` |
| `wp_mail()` directly | `ntdst_mail()->to()->template()->send()` |

→ For the full list including YOOtheme, security, and performance, read `anti-patterns.md`.

---

## Plan Rules

When writing-plans generates tasks for NTDST projects, every task MUST:

- **Read the relevant reference file** before writing implementation code
- **Classify** the code unit: Service, Handler, Helper, Model, or Template
- **Require** `declare(strict_types=1)` as first line
- **Specify DI**: injection via constructor, resolved with `ntdst_get()` — never `new`
- **Reference** the correct global helper for the layer
- **State hook priority** for any hooks being registered
- **Enforce size limits**: soft cap ~400 lines/service, ~30 lines/method, 5 constructor params. `init()` is the natural longest method. Admin controllers under `Admin/` are a documented exception — orchestrators (e.g., `TrajectoryAdminController` in Stride at ~1500 lines) can exceed the cap when the alternative is fragmenting closely-coupled UI assembly
- **Use Data Manager** for all data ops — never raw meta/SQL
- **Use Response** for output — never raw `echo`
- **Route via `ntdst_pages()`** — never manual `template_include`
- **Return WP_Error** on failure — never `false`/`null`
- **Classify before implementing**: only classes that hook into WordPress at boot time (e.g., `admin_menu`, `rest_api_init`, `wp_enqueue_scripts`) should implement `NTDST_Service_Meta` and be listed in `services`. Pure dependencies (repositories, calculators, stores, executors, bridges) are plain classes resolved lazily via DI autowiring — never make them services
- **Use config filter** pattern: `apply_filters('{project}_{slug}_config', $defaults)` where `{project}` is the project slug (e.g., `stride_edition_config`, `vad_intake_config`). Framework-internal hooks under `ntdst/*` are for ntdst-core itself; per-project services use the project prefix
