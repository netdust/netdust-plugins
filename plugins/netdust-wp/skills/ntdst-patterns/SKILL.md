---
name: ntdst-patterns
description: Use when scaffolding new Netdust WordPress projects, creating new mu-plugins, organizing themes, adding domain modules, deciding where new files go, or onboarding to an existing Netdust codebase. Triggers on questions like "where does this go", "what should I name this folder", "is this in the right place". Activates on keywords stride-core, ntdst-core, mu-plugins, Modules, Handlers, Domain, Infrastructure, themes, child theme, file structure, project layout, scaffolding, where do I put. Symptoms include adding a new feature module, creating a new service, deciding between mu-plugin vs plugin vs theme, setting up a child theme, structuring assets. Companion to ntdst-architecture (which covers the DI container + service lifecycle) — this skill is about WHERE files live, not HOW classes wire together.
---

# NTDST Patterns — folder & file structure

This skill covers WHERE things go in a Netdust WordPress project. For HOW classes wire together (DI container, bootstrap, routing), see `ntdst-architecture`. For data + APIs, see `ntdst-data`. For deploy + infra, see `wp-infra` (this plugin) and `dev-stack` (netdust-core).

**Canonical implementation: `~/Sites/stride/`.** When in doubt, copy what Stride does.

## Golden paths — open the worked slice before planning

For a medium feature, don't assemble from rules and don't copy the nearest sibling file (siblings drift — see `lessons.md`: *match the framework, not siblings*). Open the matching **golden path** under `golden-paths/` — a complete, verified, end-to-end vertical slice extracted from real Stride/Rossi source — and **build to it**. Each slice names what changes per project and what never does.

| Feature request shape | Open this golden path |
|---|---|
| New CPT/model with admin + frontend ("add a Testimonials/Events/Products section", "a new domain object", "register a custom post type with a list and a single page") | `golden-paths/content-type-feature.md` |
| A form, AJAX action, or write-flow ("submit/save X", "an AJAX endpoint", "process this form", anything touching the four security pillars) | `golden-paths/form-data-flow.md` |
| An admin settings/options page ("a settings screen", "an options page", "store config in the admin", "manage X from wp-admin") | `golden-paths/admin-settings-page.md` |
| A YOOtheme Builder source/element (YOOtheme Pro projects only — Dynamic Content source, custom query in the builder) | `golden-paths/yootheme-integration.md` |

**The instruction:** read the golden path *before* writing the plan, then build the feature to its structure. A deviation from the slice is allowed — but it must be **named and justified in the plan** (per `wp-plan-requirements`); an unnamed deviation is the drift the reviewer will flag. If a request spans two shapes (e.g. a CPT *with* a settings page *and* an enrollment form), open each relevant slice.

## Project layout (Bedrock + NTDST)

```
project/
├── composer.json, composer.lock
├── .env, .env.example
├── site.yml                              ← harness — operational config
├── memory/{STATE.md, lessons.md}         ← harness — per-project memory
├── tasks/todo.md                         ← harness — carried-forward tasks
├── Makefile                              ← deploy (variant per site.yml deploy.method)
├── CLAUDE.md                             ← @-imports harness
│
└── web/
    ├── wp/                               ← Bedrock core (gitignored)
    └── app/
        ├── plugins/                      ← Composer-managed (gitignored)
        ├── themes/
        │   ├── stridence/                ← custom child theme (committed)
        │   └── kadence/                  ← parent theme (Composer-managed, may be gitignored)
        ├── mu-plugins/
        │   ├── netdust-loader.php        ← explicit require_once entry (committed)
        │   ├── <project>-core/           ← business logic (committed) — the NTDST core layer
        │   └── <project>-<client>/       ← client-specific mu-plugins (committed)
        └── uploads/                      ← user content (gitignored)
```

## The `<project>-core` mu-plugin (the NTDST core layer)

This is where all business logic lives. Theme is presentation only. Plugin (composer-installed) is third-party. mu-plugin is yours.

```
mu-plugins/<project>-core/
├── <project>-core.php                    ← entry, bootstraps the DI container
├── composer.json                         ← PSR-4 autoload
├── Contracts/                            ← Interfaces (LMSAdapterInterface, …)
├── Domain/                               ← Value objects (Money, EditionStatus, …)
├── Infrastructure/                       ← Abstract bases (AbstractRepository, …)
├── Modules/                              ← Domain modules — ONE FOLDER PER BOUNDED CONTEXT
│   ├── Enrollment/
│   │   ├── EnrollmentService.php
│   │   ├── EnrollmentRepository.php
│   │   ├── Hooks/                        ← WP hooks for this module only
│   │   └── DataModels/
│   ├── Edition/
│   ├── Invoicing/
│   └── …
├── Handlers/                             ← AJAX + REST handlers (thin layer over services)
├── Admin/                                ← Admin dashboard pages, settings, metaboxes
├── Integrations/                         ← Third-party adapters (LearnDash, FluentCRM, …)
├── templates/                            ← Server-side templates the core renders (admin, PDF)
└── assets/                               ← Built CSS/JS for admin or PDF (theme owns frontend)
```

Namespace pattern: `<Project>\Modules\<Module>\<Class>`, e.g. `Stride\Modules\Enrollment\EnrollmentService`.

## Theme structure

```
themes/<project>ence/                     ← child theme of Kadence (or similar)
├── style.css, functions.php
├── templates/                            ← block templates (.html) for FSE
├── parts/                                ← block parts
├── patterns/                             ← reusable patterns
├── components/                           ← reusable PHP partials (course-card, etc.)
├── services/frontend/                    ← frontend-only classes (no business logic — call core)
│   └── <ThemeName>\services\frontend\…
├── helpers/                              ← template helper functions
├── assets/
│   ├── css/, js/                         ← source
│   └── dist/                             ← built by Vite, gitignored
└── vite.config.js                        ← asset pipeline
```

Theme rules:
- **Presentation only.** No business logic. Call services from `<project>-core` via the DI container.
- **Procedural in template files is fine** (`templates/course-card.php`); classes in `services/frontend/` for stateful work.
- **No direct DB access from theme.** Always through a core repository.

## Client-specific mu-plugins

When a client has unique styling, copy, or behavior (e.g. Stride's Kindred / Care Community / SafeAndSound):

```
mu-plugins/<project>-<client>/            ← e.g. stride-kindred
├── stride-kindred.php
├── assets/                               ← client palette CSS, logos
├── overrides/                            ← template overrides (specific to this client)
└── ClientConfig.php                      ← hooks into Core's brand registry
```

Activated/deactivated per environment via the loader.

## File naming

| Type | Convention |
|---|---|
| PHP classes | `PascalCase.php` matching the class name |
| PHP template/partial files | `kebab-case.php` |
| CSS/JS source | `kebab-case.css/js` |
| Tests | `<ClassUnderTest>Test.php` (unit) or `<Feature>Cest.php` (Codeception) |
| Hooks subdirectories | `<Module>/Hooks/<HookGroup>Hooks.php` |
| Admin pages | `Admin/<PageName>Page.php` + `templates/admin/<page-name>.php` |

## Where things should NOT live

| Don't put | Where it goes instead |
|---|---|
| Business logic in the theme | `mu-plugins/<project>-core/Modules/<Module>/` |
| Third-party plugin code in mu-plugins | `composer require` → `web/app/plugins/` |
| Per-environment config in `wp-config.php` | `config/environments/<env>.php` (Bedrock) |
| Secrets anywhere committed | `.env` (local) or platform env vars (deploy) |
| One-off scripts | `tasks/scripts/` (gitignored), or WP-CLI commands in `<project>-core/Cli/` |
| Frontend asset source mixed with theme PHP | `themes/<theme>/assets/{css,js}/` (src) → Vite builds to `dist/` |
| ACF JSON syncs (if using ACF) | `themes/<theme>/acf-json/` (committed) — but Netdust default is code-defined fields, not ACF |
| Client-specific brand overrides in core | A separate mu-plugin `stride-<client>` (Stride's pattern) |

## Adding a new module — checklist

1. `mu-plugins/<project>-core/Modules/<NewModule>/`
2. `<NewModule>Service.php` (the public API) with namespace `<Project>\Modules\<NewModule>`
3. `<NewModule>Repository.php` extending `AbstractRepository` (if it has persistence)
4. `Hooks/<NewModule>Hooks.php` (if it needs WP integration points)
5. Register the service in the DI container via the module's bootstrap (`<Project>\Modules\<NewModule>\Bootstrap`)
6. Tests: `tests/Unit/Modules/<NewModule>/<NewModule>ServiceTest.php`
7. Document the module's responsibility in a brief class docblock — what is it for, what is it NOT for

## Adding a new client brand mu-plugin

1. `mu-plugins/<project>-<client>/<project>-<client>.php`
2. Copy a working sibling (e.g. `stride-kindred`) and rename/reskin
3. Hook into the core's brand registry: `add_action('<project>_register_brands', fn($r) => $r->add($brand_config))`
4. Brand-specific CSS in `assets/`, theme overrides in `overrides/`
5. Activate per environment via the loader

## See also

- `ntdst-architecture` — DI container, service lifecycle, routing, templating
- `ntdst-data` — data models, repositories, REST API
- `wp-infra` — WP-CLI, Vite-for-WP, Bedrock Makefile patterns
- `dev-stack` (netdust-core) — generic DDEV, git, Makefile verbs, .env
- `ntdst-yootheme` — YOOtheme variant (when project uses YOOtheme Pro instead of FSE/block theme)
- `bedrock-composer` — Bedrock layout fundamentals
- `~/Sites/stride/` — canonical implementation
