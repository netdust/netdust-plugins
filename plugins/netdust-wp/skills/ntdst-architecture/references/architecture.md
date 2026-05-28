# Architecture Rules & Patterns

Laravel-inspired architecture for WordPress plugins and NTDST services.

## Core Principles

- **Service Providers** manage lifecycle (register bindings, boot hooks)
- **Lightweight DI container** — no heavy frameworks
- **Configuration in files** — not scattered constants
- **Single Responsibility** — small classes, one job each
- **Composition over inheritance**
- **Type everything** — no `mixed`, no untyped arrays

## PHP 8.1+ Standards (ENFORCED)

- `declare(strict_types=1)` — every file
- `readonly` properties — default unless mutation needed
- Constructor promotion — always use promoted properties
- Enums for fixed sets — never string constants
- Named arguments — for 3+ params
- Interfaces for boundaries — repositories, external services
- Return early — guard clauses, not deep nesting

## Size Limits

Soft caps. Treat as warnings, not hard rules — if exceeding the cap is the cleanest way to keep closely-coupled logic in one place, exceed it.

| Element | Soft cap | Notes |
|---------|----------|-------|
| Class | ~400 lines | `init()` is the natural longest method. Admin controllers under `Admin/` are exempt — UI orchestrators (e.g., dashboard assembly, settings screen) routinely run 1000+ lines because fragmenting them obscures the wiring. |
| Method | ~30 lines | |
| Constructor params | 5 | More = service is doing too much; split. |

## DO NOT

- **No God classes** — no "PluginManager" doing everything
- **No scattered hooks** — `add_action`/`add_filter` only in provider `boot()` or service `init()`
- **No global state** — no `global $variable`
- **No raw arrays for structured data** — use DTOs, Value Objects
- **No business logic in templates** — views receive prepared data only
- **No direct DB queries in services** — use repositories or `ntdst_data()`
- **No `mixed` type** — if you can't type it, architecture is wrong
- **No `Utils`/`Helper` God classes** — small, focused utility classes
- **No `new` inside classes** — inject dependencies or use factories

## Anti-Pattern Detection

| Smell | Fix |
|-------|-----|
| Class > 400 lines (non-admin) | Split by responsibility |
| Method > 30 lines | Extract submethods |
| Constructor > 5 params | Class does too much |
| `add_action` outside provider/init | Move to proper location |
| Array with string keys as data | Create DTO or Value Object |
| `switch` on type strings | Use enum + strategy |
| Same query in multiple places | Extract to repository |
| `new SomeClass()` inside method | Inject via constructor |
| Config value hardcoded | Move to config file |

## Preferred Patterns

- **Repository** for data access (behind interfaces)
- **Strategy** for interchangeable algorithms
- **Value Objects** for domain concepts (immutable, readonly)
- **Factory methods** for complex object creation
- **Observer/Event** for loose coupling between modules
- **DTOs** for data transfer between layers

## Global Helper Index

| Layer | Helper | Returns |
|-------|--------|---------|
| DI (singleton) | `ntdst_get(Class::class)` | Cached instance |
| DI (fresh) | `ntdst_make(Class::class)` | New instance |
| DI (register) | `ntdst_set(Class::class)` | Container |
| Data/ORM | `ntdst_data()->get('type')` | `NTDST_Data_Model` |
| Router | `ntdst_router()` / `ntdst_route()` | `NTDST_Router` |
| Response | `ntdst_response()` | `NTDST_Response` |
| Logger | `ntdst_log()` | `NTDST_Logger` |
| Mailer | `ntdst_mail()` | `NTDST_Mailer` |
| Sectors | `ntdst_sectors()` | `NTDST_SectorRegistry` |
| Cache | `ntdst_query_cache()` | `NTDST_Query_Cache` |
| Metabox | `ntdst_metabox()` | `NTDST_MetaboxGenerator` |
| Endpoints | `ntdst_endpoints()` | `Endpoints` |

## Framework Tool Fit — Right Tool per Operation

A helper's name doesn't tell you when it's the wrong tool. Before refactoring "use `ntdst_X` here", verify the helper actually fits your operation. If it doesn't, identify the helper that does — don't force the named one.

| Operation | Right tool | NOT |
|---|---|---|
| Render template + output the response | `ntdst_response()->render('path/template')` | `ob_start + include` |
| Render template → string (for emails / AJAX HTML) | `ntdst_response()->html('path/template')` | `ob_start + include` |
| `template_include` callback (resolve template name → file path for WP) | `ntdst_router()->template('single', $cb, $post_type)` | Raw `add_filter('template_include', ...)` |
| URL pattern → callback | `ntdst_router()->get('pattern/:param', $cb)` | Raw `add_action('parse_request', ...)` |
| Pre-query interception (rewrite query vars BEFORE WP runs the query) | Raw `add_action('parse_request', ...)` — `ntdst_router()` fires too late | `ntdst_router()` |
| AJAX/REST endpoint | `add_filter('ntdst/api_data/{action}', ...)` (nonce + rate-limit + CSRF handled) | `add_action('wp_ajax_*', ...)` |
| Send email | `ntdst_mail()->to()->template()->send()` | `wp_mail()` |
| Log structured events | `ntdst_log('channel')->level(...)` | `error_log()`, swallowed `WP_Error` |
| Read/write CPT | per-domain Repository | `ntdst_data()` direct, raw `wp_insert_post` / `get_post_meta` |

**The two failure modes:**

- **Blind substitution.** Tool named in a memory ≠ tool that fits. `ntdst_response()` is for output; it has no public API for "give me a resolved file path." Forcing it into a `template_include` callback would be worse than the raw filter.
- **Sibling pattern-matching.** A file in the same directory using `add_action('wp_ajax_*')` is not authorization to do the same. The framework reference is canon; the neighbour may be drifted.

If NO framework helper fits, defend the raw-WP idiom explicitly. Not every operation has a wrapper, and not every wrapper should exist.

## Hook Priority Ranges

| Range | Purpose |
|-------|---------|
| 1–4 | Core infrastructure (security, cache) |
| 5–9 | Data layer, model registration |
| 10 | Default (features) |
| 11–19 | Late features (depends on others) |
| 20+ | Output modification, UI enhancements, cleanup |
| 999 | Emergency overrides |

## Hook Naming

Two distinct namespaces — don't mix them:

```php
// FRAMEWORK hooks (ntdst-core's own events — leave the prefix alone)
do_action('ntdst/services_registered', $bootstrap);
apply_filters('ntdst/{post_type}/fields', $fields);
add_filter('ntdst/api_data/{action}', $handler);  // ntdst_api router

// PROJECT-level service hooks (use the project's own prefix, NOT netdust_/ntdst_)
// Replace {project} with the project slug: stride, vad, atelier296, etc.
apply_filters('{project}_{slug}_config', $defaults);     // e.g. stride_edition_config
apply_filters('{project}_{slug}_enabled', true);         // e.g. stride_edition_enabled

// PROJECT-level domain events
do_action('{project}/{domain}/{action}', $array_payload);  // e.g. stride/registration/created
```

The `netdust_` prefix is **not** a framework reservation — it was an old placeholder. Real projects use their own slug: Stride uses `stride_*` / `stride/*`, VAD Vormingen uses `vad_*` / `vad/*`, etc. Use whatever the project's `mu-plugins/<project>-core/` directory implies.

Domain event payloads are **plain associative arrays**, not event-object classes — `do_action('stride/registration/created', ['user_id' => $uid, 'edition_id' => $eid])`, not `do_action(..., new RegistrationCreated($uid, $eid))`.

## Project Structure

```
theme-root/
├── config/theme-config.php       ← services, modules, assets config
├── services/                     ← auto-discovered
│   ├── SecurityService.php       ← root = sector-independent
│   ├── gallery/                  ← sector-specific (auto-discovered when enabled)
│   │   └── ExhibitionService.php
│   └── printshop/
├── templates/                    ← Response templates
├── views/emails/                 ← Mailer templates
├── helpers/                      ← Stateless functions
├── assets/src/ + dist/           ← Vite
├── functions.php                 ← Bootstrap wiring
└── vendor/ntdst-core/            ← Framework (don't edit)
```
