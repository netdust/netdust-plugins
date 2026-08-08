---
name: ntdst-architecture
description: >
  Use when adding, writing, creating, scaffolding, planning, or reviewing a
  Service, Handler, Module, CPT class, Repository, sub-service, admin
  controller, AJAX endpoint, REST controller, or WP-CLI command in an NTDST
  WordPress project — anything under `mu-plugins/<project>-core/` or matching
  `class *Service implements NTDST_Service_Meta`. Triggers on phrases like "add
  a service", "write a service", "create a service", "implement a service",
  "new module", "service that does X", "service with cron / hooks / DI", "why
  isn't my service booting", "how do I disable this service", "add a custom
  URL / route", "render a template", "replace this ob_start", and on the
  keywords `NTDST_Service_Meta`, `metadata()`, `ntdst_get`, `ntdst_set`,
  `ntdst_service_{slug}_config`, `plugin-config.php`, `theme-config.php`,
  `ntdst-core`, `NTDST_Bootstrap`, `ntdst_router`, `ntdst_response`. Also use
  when reviewing NTDST code for framework drift, or when a framework call is
  missing and you need to know whether this project's copy of ntdst-core has it.
---

# NTDST Architecture

## What this skill carries, and what it deliberately does not

Three things, and nothing else:

1. **Mechanical rules → a gate**, not paragraphs. If a grep can decide it, `bin/drift-check.py`
   decides it (below).
2. **Judgment calls → this skill.** When is a raw read legitimate? Is this a service or a
   sub-component? Those cannot be grepped, so they are argued here.
3. **How to actually build the thing → a golden path.** A worked vertical slice you copy.

**No inventory.** A decision — *"a method belongs on `Theme` iff its subject dies when you switch
themes"* — is still true next year. A method list, a signature, "the available options are…" is false
the moment someone edits the file. This skill previously ran **94% reference-and-template inventory**,
and every documentation defect found during the last framework refactor was a stale restatement of an
API, never a wrong decision.

So: **decide the case from this skill, build from the golden path, read source for the signature.**

*Why the gate exists at all:* exhaustive, accurate skills did not prevent drift. Across 13 consumer
projects, 13/13 hand-roll `get_post_meta()`/`get_posts()` and 11/13 hand-roll `ob_start()` — every one
of them correctly documented the whole time. Accuracy was never the binding constraint.

## Before you trust any API claim: ntdst-core is a per-project fork

There is **no shared upstream**. Twelve-plus sites each carry their own copy of `ntdst-core`, forked
40%+ apart. A survey across eight working copies:

| feature | present in |
|---|---|
| `NTDST_Query_Cache` / `ntdst_get_posts_fast()` | 7 of 8 copies — **absent in daan**, deleted with the cache it served |
| `Theme::module()` DSL | 7 of 8 copies — **retired in daan** |
| `ntdst_router()->rest()`, `NTDST_Cors_Policy` | **stride only** — never ported to the others |

**This is why a canonical API inventory is not merely stale, it is impossible.** Any method list is
right for some sites and wrong for others, and a reader on the wrong site is misled with confidence.
Decisions survive the fork; surfaces do not.

**The rule:** before calling a framework method, confirm it exists in *this project's* copy. daan is
HEAD on Data, Response, Endpoints and Metabox — port from it, don't assume from it.

## The mechanical rules are a gate, not prose

The framework conventions a grep can decide are enforced by `bin/drift-check.py` in this plugin —
repository bypasses, raw meta and post writes, `ob_start()` rendering, raw `wp_ajax_*`, raw
`ntdst/api_data` filter registration, direct `register_post_type()`/`register_taxonomy()`, manual
`template_include`, hardcoded meta prefixes, wrong Data API vocabulary, unprepared `$wpdb`, and
`permission_callback => __return_true`.

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py"              # staged files
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py" --since HEAD~1
```

**Run it before closing any task that touched PHP.** Annotate a deliberate exception on the line —
`// ntdst-allow: <check-key> — <why>` — and an allow with no reason is itself a finding. The
framework's own directory is exempt: `ntdst-core` *implements* these primitives.

This exists because accuracy was never the binding constraint. Measured across 13 consumer projects,
**13/13** hand-roll `get_post_meta()`/`get_posts()`, 11/13 hand-roll `ob_start()`, 5/13 call
`register_taxonomy()` directly — every one of them documented, accurately, the whole time. If a rule
is grep-decidable it belongs in the gate; this skill keeps the judgment calls.

## Start here — build to the worked slice

Don't assemble a feature from rules, and don't copy the nearest sibling file (siblings drift). Open
the slice that matches the shape of the work and **build to it**. Each one is complete, end-to-end,
and carries a `Verified against source:` date so staleness is visible instead of silent.

| What you're building | Open |
|---|---|
| A feature service — hooks, DI, config, a custom URL, a rendered template | `golden-paths/feature-service.md` |
| A content type — CPT, fields, taxonomy, metabox, API actions | `ntdst-data`'s `golden-paths/model-and-api-action.md` |
| Where the files go, project layout, a new module folder | `ntdst-patterns` |

A deviation from the slice is allowed — name and justify it in the plan. An unnamed deviation is the
drift the reviewer flags.

**The one-line recipes**, when you only need to remember which door to use:

| To do this | Call this |
|---|---|
| Register a CPT or taxonomy | `ntdst_data()->register($name, $config)` — taxonomies go in the `taxonomies` key |
| Register an API action | `ntdst_api_action($action, $handler, $opts)` |
| Resolve a dependency at a composition root | `ntdst_get(Foo::class)` |
| Own a URL | `ntdst_router()->get(...)` / `->single(...)` / `->archive(...)` |
| Render a page from a route | `NTDST_Template_Loader::page($tpl, $data)`, read back with `ntdst_page_data()` |
| Output JSON, a 404, a redirect, a file | `ntdst_response()` |
| Send mail | `ntdst_mail()` |
| Log an event | `ntdst_log($channel)` |

## Reference index

| File | Read when… |
|---|---|
| `golden-paths/feature-service.md` | **Building a service** — the worked slice |
| `references/framework-map.md` | What each ntdst-core layer decides, and the traps that have bitten |
| `references/architecture.md` | PHP standards, size limits, design patterns, hook naming |
| `references/anti-patterns.md` | The drift canon — the `ntdst-drift-reviewer` agent's checklist |

---

## What a service actually IS

**A service is a Bootstrap-instantiated class that adds a specific feature to the site.**

That sentence is the whole definition.

**Mental model: a service is a plugin you didn't have to package.** WordPress plugins are
self-contained features you can toggle off without deleting code. An NTDST service is the same idea,
scoped to inside a single codebase. One feature per service, same way one feature per plugin. Hooks
register on bootstrap, same way plugins register on `plugins_loaded`. You don't `new` a service any
more than you `new WooCommerce()` — the container resolves it.

- **"Bootstrap-instantiated"**: listed in the plugin/theme config's `services` array, or discovered.
  The lifecycle creates exactly one instance at the declared priority.
- **"Adds a feature"**: the constructor calls `$this->init()`, which **registers something on the
  site** — WP hooks, a CPT, a shortcode, an admin menu, cron, an API action. If the class doesn't
  *add* anything at boot, it isn't a service.
- **"Specific"**: one feature, one service. A class owning multiple unrelated features gets split.

### The promotion test

> **Would I want a config-level toggle to disable this feature without deleting code?**

Yes → service. No → sub-component; instantiate it inside a parent service's `init()`.

Sub-components (NOT services, even though they have hooks): admin controllers, dashboard widgets,
a single domain-event listener, a WP-CLI registration.

Dependencies (plain classes, NOT services): API clients, repositories, mappers, calculators,
value objects, query helpers. They are autowired when a service injects them, and never appear in
the `services` list.

### What to create

| Need | Pattern | Location |
|---|---|---|
| New site feature (toggle-worthy: hooks + config + DI) | **Service** | `services/MyService.php` or `Modules/My/MyService.php` |
| Sub-component of a service | **Plain class** instantiated in parent's `init()` | Alongside the service |
| Pure domain logic (rules, math, classification) | **Business class** | Alongside the service |
| Stateless utility | **Helper** (plain functions) | `helpers/` |
| Data model + CRUD | **Model** registered inside a service's `init()` | see `ntdst-data` |
| Custom URL | **Route** | Inside a service |
| API action | **`ntdst_api_action()`**, not a raw `wp_ajax_*` handler | Inside a service |
| Template output | **Response**, never raw `echo` | Inside a service |

**Split rule:** a class with both hooks AND business logic splits into a handler (thin WP boundary)
plus a business class (pure, WP-free, testable). Services orchestrate; they don't compute.

---

## Where each decision is made

Name a convergence point by **class + method, never by path.** The metabox authorization invariant
survived a whole-directory `git mv` completely untouched for exactly this reason, while every
path-shaped reference in the tree needed updating.

| Decision | Made in | Rule |
|---|---|---|
| does this belong on `Theme`? | `core/Theme.php` | **a method belongs iff its subject dies when you switch themes.** A CPT, taxonomy or API action outlives a theme switch and belongs to its owner; a hook binding, template path or template helper does not |
| does this service boot, and with what config? | `core/Bootstrap.php` | `ntdst_service_{slug}_enabled` → DB option `ntdst_service_{slug}`; config via `ntdst_service_{slug}_config`, overrides at `config['services']['overrides'][$slug]` |
| may this action be called anonymously? | the API router's public-actions filter | **default-deny.** The framework ships an empty public list and never adds to it |
| what capability floors an API action? | the action-registration helper | type-derived from the post type, resolved at dispatch, **fail-closed** |
| how does a class get its dependencies? | the DI container | constructor autowiring; `ntdst_get()` at the composition root, never `new` inside a class |
| where does a template resolve from? | the template loader | one live registry, read at resolution time |

→ Layer-by-layer detail and the traps: `references/framework-map.md`.

---

## Traps that have actually bitten

- **A file is not a class.** `api/Response.php` declares **two** classes. A file-per-class assumption
  produced a wrong plan premise (a helper was called dead; a live template consumes it every render).
  Grep for the symbol, not the filename.
- **Loading is an explicit `require_once` list, not a directory scan.** The service-discovery
  `glob('*Service.php')` runs over *consumer* directories only — the configured discovery paths at
  root level, plus enabled sector subdirectories — and no framework filename matches that pattern. A
  moved framework file therefore fails **loudly** (fatal), never silently.
- **The service slug is derived from the class name, and the derivation is lossy.** It collapses
  acronyms (`AdminUIService` → `admin_ui`), but stripping `Service` removes **every** occurrence, so
  `ServiceService` yields an empty slug. It is also many-to-one: two classes can collide on one slug
  and silently share an enable filter.
- **`metadata()['name']` does not win.** Through the real discovery flow the enable-check warms the
  slug cache from the class name *first*, so the metadata argument passed later is never read.
  Renaming a service in `metadata()` does not rename its filters or its DB option.
- **Two config-filter surfaces exist and do not meet.** Bootstrap fires `ntdst_service_{slug}_config`
  and feeds it from `config['services']['overrides']`. Services also conventionally apply their own
  `{project}_{slug}_config`. A service that reads only its project-prefixed filter is **invisible to
  the framework's override mechanism**, and `add_filter('{project}_{slug}_enabled', '__return_false')`
  **does not disable it** — Bootstrap only checks `ntdst_service_{slug}_enabled`. Pick deliberately;
  document which one the service honors.
- **`edit_post` is a meta-capability.** A CPT gets `map_meta_cap` only via WordPress's back-compat
  rule (`class-wp-post-type.php`, the `capability_type` in `('post','page')` branch). Adding an
  explicit `capabilities` array turns that off, and an `edit_post` gate then denies everyone.
- **A forwarder is a second surface.** A method kept "for compatibility" that just calls the real one
  drifts independently of it — two such forwarders drifted twice in a single week before being
  deleted. Delete as you move.

---

## Judgment — the calls a grep cannot make

| The excuse | The reality |
|---|---|
| *"It has a hook, so it's a service."* | The promotion test is the toggle question, not the hook count. A dashboard widget, an admin controller and a single listener all have hooks and are all sub-components. |
| *"Make it a service so it's in the container."* | Eager instantiation on every request, for a class nothing retrieves. A sub-component is a plain `new` in its owner's `init()`; a dependency is autowired lazily. |
| *"I'll wrap the repo method so the service reads nicer."* | A one-line forward is a second equally-correct path, and the codebase drifts between them. Naming is not a justification; the verb can live on the repo method. |
| *"We might add logic to that wrapper later."* | Add it when you need it. Until then the wrapper is pure cost — and it will be copied before it is filled. |
| *"`admin_only` metadata is cleaner than `is_admin()`."* | It gates *bootstrap*, so no AJAX action, CLI command or frontend caller can ever reach the class. Gate at runtime inside `init()`. |
| *"I'll add my own `{project}_{slug}_config` filter."* | Bootstrap never fires it. Your service becomes invisible to `config['services']['overrides']`, and the matching `_enabled` filter disables nothing. |
| *"The framework must have a helper for this."* | Sometimes it does not, and a defended raw-WP idiom is correct — pre-query interception is a real example. Defend it explicitly; don't force a helper that doesn't fit, and don't pretend the gap isn't one. |

**Red flags:** a class implementing the service interface with no `add_*` call in `init()`; a service
method whose whole body is `return $this->x->y(...)`; a `new SomeService()` anywhere; a config filter
whose name doesn't start `ntdst_service_`; reaching for the nearest sibling file as your template.

## Plan rules

When a plan generates tasks for an NTDST project, every task MUST:

- **Classify** the code unit: Service, Handler, Helper, Model, or Template — before implementing.
  Only classes that hook into WordPress at boot implement `NTDST_Service_Meta` and get listed in
  `services`. Pure dependencies are plain classes, resolved lazily.
- **Verify the framework surface it calls against this project's `ntdst-core`** — not against memory,
  and not against another site's copy. State the file the symbol lives in.
- **Require** `declare(strict_types=1)` as the first line.
- **Specify DI**: constructor injection, resolved with `ntdst_get()` — never `new` inside a class.
- **State hook priority** for any hook registered.
- **Enforce size limits**: soft caps of ~400 lines/service, ~30 lines/method, 5 constructor params.
  `init()` is the natural longest method. Admin controllers under `Admin/` are a documented
  exception — UI orchestrators can exceed the cap when the alternative fragments the wiring.
- **Route data through a repository**, output through Response, URLs through Router.
- **Return `WP_Error` on failure** — never `false` or `null`.
- **Name the config/enable surface** the service honors, per the two-surfaces trap above.
- **Specify sector requirements** if platform-specific.

## Method note for whoever extends the framework

Derive seams from the **corpus** — how many of the twelve-plus consumers hand-roll a thing — not from
one site's tree. Asking "does *this* site call it?" answers *what does this site use*, not *what does
the framework owe its consumers*, and it made the last framework map look smaller than it was. Sites
are evidence about requirements; they are not constraints on implementation.
