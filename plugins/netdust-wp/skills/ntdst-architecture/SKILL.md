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

## Reference Index

| File | Read when... |
|------|-------------|
| `references/architecture.md` | Core principles, PHP standards, size limits, design patterns, project structure |
| `references/services.md` | Creating services — when to/not to, lifecycle, sectors, priorities, config, discovery |
| `references/container.md` | DI container, autowiring, bootstrap lifecycle, functions.php wiring, `plugin-config.php` (mu-plugins) / `theme-config.php` (themes) |
| `references/data-layer.md` | Model registration, fields, CRUD, query builder, metaboxes, caching |
| `references/router.md` | URL routes, template hooks, rewrite rules, return values |
| `references/response.md` | Template rendering, JSON output, email HTML, template resolution |
| `references/api-endpoints.md` | REST API actions, nonce flow, JS client, rate limiting, security |
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
| Custom URL | **Route** via `ntdst_route()` | Inside a service |
| REST API action | **Filter** on `ntdst/api_data/{action}` | Inside a service |
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
| `echo` in a service | `ntdst_response()->render()` / `->json()` |
| `add_action()` scattered across methods | Group in `registerHooks()` / `init()` |
| `return false` on error | `return new WP_Error(...)` |
| Manual `template_include` filter | `ntdst_router()->single()` / `->archive()` |
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
- **Route via Router** — never manual `template_include`
- **Return WP_Error** on failure — never `false`/`null`
- **Classify before implementing**: only classes that hook into WordPress at boot time (e.g., `admin_menu`, `rest_api_init`, `wp_enqueue_scripts`) should implement `NTDST_Service_Meta` and be listed in `services`. Pure dependencies (repositories, calculators, stores, executors, bridges) are plain classes resolved lazily via DI autowiring — never make them services
- **Specify sector requirements** if platform-specific
- **Use config filter** pattern: `apply_filters('{project}_{slug}_config', $defaults)` where `{project}` is the project slug (e.g., `stride_edition_config`, `vad_intake_config`). Framework-internal hooks under `ntdst/*` are for ntdst-core itself; per-project services use the project prefix
