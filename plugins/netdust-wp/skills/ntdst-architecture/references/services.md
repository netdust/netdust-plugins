# NTDST Service Architecture

Complete guide to creating and managing services in the NTDST WordPress framework.

---

## Table of Contents

1. [When to Create a Service](#when-to-create-a-service)
2. [Service Structure](#service-structure)
3. [Lifecycle Phases](#lifecycle-phases)
4. [Dependency Injection](#dependency-injection)
5. [Enable/Disable Control](#enabledisable-control)
6. [Sector Awareness](#sector-awareness)
7. [Priority Guidelines](#priority-guidelines)
8. [Configuration](#configuration)
9. [Service Discovery](#service-discovery)
10. [Anti-Patterns](#anti-patterns)

---

## When to Create a Service

Not everything needs to be a service. This section helps you decide when a service is the right pattern.

### Decision Criteria

**Create a service when you need 2 or more of these:**

| Need | Why It Requires a Service |
|------|---------------------------|
| WordPress hooks | Services register hooks in `init()`, ensuring proper lifecycle |
| Configuration | Services use `apply_filters()` for customizable config |
| Dependency injection | Services are autowired by the container |
| Shared access | Other code retrieves the service via `ntdst_get()` |
| Enable/disable control | Services support `metadata()` and filter-based control |
| Boot priority | Services declare priority for ordered initialization |

**If you only need one of these**, consider a simpler pattern.

### Service vs Handler vs Helper vs Business Class

| Pattern | Purpose | Has Hooks? | Has Logic? | In Container? | WP-free testable? |
|---------|---------|------------|------------|---------------|-------------------|
| **Service** | Feature orchestrator — lifecycle, config, DI, integration | Yes | Minimal (delegates) | Yes (singleton) | No |
| **Handler** | Thin routing layer — catches WP events, validates, delegates | Minimal (AJAX/REST) | No | Optional | No |
| **Business class** | Pure domain logic — rules, calculations, transformations | No | Yes | Optional | **Yes** |
| **Helper** | Stateless utilities, pure functions | No | Trivial | No | Yes |
| **Repository** | Data access abstraction | No | Query logic | Yes | With stubs |
| **Value Object** | Immutable domain concept | No | Immutable | No | Yes |

### The Split Rule: Service → Handler + Business Logic

**When a class accumulates both hooks AND business logic, split it.** The handler is the boundary between WordPress and your domain. Business logic classes should never know they're in WordPress.

**Signs you need to split:**
- A service method does sanitization + validation + business logic + response formatting
- Business logic is hard to unit test because it's coupled to WP hooks
- A class is growing past ~400 lines with mixed concerns (admin controllers exempt — UI orchestrators routinely run longer)

**The pattern:**

```php
// Handler: thin, catches WP event, sanitizes, delegates
class EnrollmentHandler {
    public function ajaxEnroll(): void {
        if (!wp_verify_nonce($_POST['nonce'] ?? '', 'enroll')) {
            wp_send_json_error(['message' => 'Invalid token']);
        }
        $editionId = absint($_POST['edition_id'] ?? 0);
        $result = ntdst_get(EnrollmentService::class)->enroll(get_current_user_id(), $editionId);
        is_wp_error($result) ? wp_send_json_error($result) : wp_send_json_success($result);
    }
}

// Service: orchestrator with lifecycle, hooks, config
class EnrollmentService implements NTDST_Service_Meta {
    public function __construct(
        private readonly RegistrationRepository $repo,
        private readonly PriceCalculator $calculator,
    ) { $this->init(); }

    public function enroll(int $userId, int $editionId): array|WP_Error {
        // Orchestrate: check capacity, calculate price, create registration, grant access
    }
}

// Business class: pure domain logic, no WP dependency
class PriceCalculator {
    public function calculate(int $basePrice, ?string $voucherCode): int {
        // Pure math, easily testable without WordPress
    }
}
```

**Key insight:** If you tend to make a class with hooks and business logic, it's better to create a thin handler and then business logic classes. The service orchestrates; it doesn't compute.

### When NOT to Create a Service

❌ **Pure utility functions**
```php
// DON'T make this a service
class StringHelper {
    public static function slugify(string $text): string { /* ... */ }
    public static function truncate(string $text, int $length): string { /* ... */ }
}
```
→ Use a helper class or standalone functions.

❌ **Single API endpoint**
```php
// DON'T create a new service just for one endpoint
class GetUserQuotesService implements NTDST_Service_Meta { /* overkill */ }
```
→ Add the endpoint to an existing related service, or use a thin Handler.

❌ **Data transformation only**
```php
// DON'T make this a service
class InvoiceCalculator { /* no hooks, no config, just math */ }
```
→ Use a helper class or Value Object.

❌ **Simple CRUD wrapper**
```php
// DON'T wrap Data Manager for no reason
class PortfolioService {
    public function find($id) { return ntdst_data()->get('portfolio')->find($id); }
}
```
→ Use Data Manager directly unless you're adding business logic.

### When TO Create a Service

✅ **Feature with multiple hooks**
```php
// YES - registers multiple hooks, has config
class SeoService implements NTDST_Service_Meta {
    private function init(): void {
        add_action('wp_head', [$this, 'outputMetaTags']);
        add_filter('document_title_parts', [$this, 'filterTitle']);
        add_filter('the_content', [$this, 'addSchema']);
    }
}
```

✅ **Needs injectable dependencies**
```php
// YES - depends on other services
class NotificationService implements NTDST_Service_Meta {
    public function __construct(
        private readonly NTDST_Logger $logger,
        private readonly EmailService $mailer,
    ) {
        $this->init();
    }
}
```

✅ **Shared across codebase**
```php
// YES - other code needs to access this
$cart = ntdst_get(CartService::class);
$cart->addItem($productId, $quantity);
```

✅ **Needs enable/disable control**
```php
// YES - can be turned off per-site
public static function metadata(): array {
    return [
        'name' => 'Newsletter Popup',
        'enabled' => true,  // Can be disabled via filter
    ];
}
```

### Borderline Cases

**"I have 3 related functions"**
→ Start with a helper class. Promote to service if you later need hooks/config.

**"I need to register one hook"**
→ Add it to an existing related service. Don't create a service for one hook.

**"I need config but no hooks"**
→ Consider a configured helper: `new PriceFormatter($config)`. Only use service if you also need DI or enable/disable.

**"I need to fetch from external API"**
→ Service if: caching, rate limiting, credentials config, retry logic.
→ Helper if: simple stateless HTTP call.

**"I'm adding a custom post type"**
→ Use Data Manager registration, not a service. Only add a service if you need business logic hooks around that CPT.

### Quick Decision Flowchart

```
Does it need WordPress hooks?
├─ No → Does it need DI?
│       ├─ No → Helper class or function
│       └─ Yes → Consider Repository pattern
└─ Yes → Does it need config or enable/disable?
         ├─ No → Can it be added to existing service?
         │       ├─ Yes → Add to existing service
         │       └─ No → Create new service
         └─ Yes → Create new service
```

### Service Smell Test

Before creating a service, ask:

1. **"Can I describe this in one sentence?"** If not, it might be doing too much.
2. **"Would this make sense as a WordPress plugin?"** Services should be cohesive features.
3. **"Does this need to run at a specific point in the WP lifecycle?"** If yes, service. If no, maybe not.
4. **"Will other code need to call this?"** If yes and it has state, service. If stateless, helper.

---

## Service Structure

### Required Interface

All services must implement `NTDST_Service_Meta`:

```php
interface NTDST_Service_Meta
{
    /**
     * Get service metadata
     *
     * @return array [
     *   'name' => 'Service Name',
     *   'description' => 'What this service does',
     *   'enabled' => true,       // Default enabled state
     *   'priority' => 10,        // Boot priority (lower = earlier)
     * ]
     *
     * NOTE: an `admin_only` flag exists in older docs but is NOT the preferred
     * gating mechanism. Gate admin-only services at runtime instead — see
     * "Admin gating" below.
     */
    public static function metadata(): array;
}
```

### Standard Service Template

Location: `app/content/themes/ntdstheme/services/{ServiceName}Service.php`

```php
<?php
/**
 * {Service Name} Service
 *
 * A self-contained feature of the site — think of it as a plugin you didn't
 * have to package. The Bootstrap creates one instance at the declared
 * priority, the constructor calls init(), and init() registers everything
 * this feature adds (hooks, CPTs, shortcodes, cron, REST endpoints, menus).
 * Toggle the whole feature off via the *_enabled filter below — no deletes
 * required.
 *
 * {Description of what this service does}
 *
 * Available filters:
 * - {project}_{slug}_config - Customize service configuration (e.g. stride_example_config)
 * - {project}_{slug}_enabled - Enable/disable the service
 *
 * @package ntdstheme
 */

defined('ABSPATH') || exit;

class ExampleService implements NTDST_Service_Meta
{
    private array $config;

    public static function metadata(): array
    {
        return [
            'name' => 'Example',
            'description' => 'What this service does',
            'enabled' => true,
            'priority' => 10,
        ];
    }

    public function __construct()
    {
        $this->config = $this->getDefaultConfig();
        $this->init();
    }

    private function getDefaultConfig(): array
    {
        // Filter allows plugin-config.php / theme-config.php to override.
        // Replace 'project' below with your project slug (e.g. stride_example_config).
        return apply_filters('project_example_config', [
            'option1' => 'default_value',
            'option2' => true,
        ]);
    }

    private function init(): void
    {
        // Register WordPress hooks
        add_action('wp_enqueue_scripts', [$this, 'enqueueAssets']);
        add_filter('the_content', [$this, 'filterContent']);

        // Register API endpoints
        add_filter('ntdst/api_data/example_action', [$this, 'handleApiAction'], 10, 2);
    }

    public function enqueueAssets(): void
    {
        if (!$this->config['option2']) {
            return;
        }
        // Enqueue scripts/styles
    }

    public function filterContent(string $content): string
    {
        // Modify content
        return $content;
    }

    public function handleApiAction($data, array $params): array
    {
        // Handle API request
        return ['success' => true];
    }
}
```

### Namespaced Service Template

For services in subdirectories (e.g., `services/gallery/`):

```php
<?php
namespace ntdstheme\services\gallery;

defined('ABSPATH') || exit;

class ArtistService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return [
            'name' => 'Gallery Artists',
            'description' => 'Artist management for galleries',
            'priority' => 15,
            'sectors' => ['gallery' => 'essential'], // Sector requirement
        ];
    }

    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        // Hooks
    }
}
```

**Important:** Namespaced services must be registered in the bootstrap config file — `plugin-config.php` for a mu-plugin, `theme-config.php` for a theme:

```php
'services' => [
    'core' => [
        'ntdstheme\\services\\gallery\\ArtistService',
    ],
],
```

---

## Lifecycle Phases

The Bootstrap orchestrates service initialization in clear phases:

### Phase 1: Register (Immediate)

```php
$bootstrap = new NTDST_Bootstrap($config);
$bootstrap->register();
```

- Services added to DI container
- No instantiation yet
- Filters for enable/disable checked
- Sector requirements validated

### Phase 2: Boot Core (after_setup_theme:5)

```php
add_action('after_setup_theme', fn() => $bootstrap->bootCore(), 5);
```

- Services with `priority < 10` instantiated
- Critical infrastructure services only
- Config filters registered

### Phase 3: Boot Features (after_setup_theme:15)

```php
add_action('after_setup_theme', fn() => $bootstrap->bootFeatures(), 15);
```

- All remaining services instantiated
- Services sorted by priority
- Constructor runs `init()` which registers hooks

### Lifecycle Hooks

```php
// After all services registered (not yet booted)
add_action('ntdst/services_registered', function($bootstrap) {
    // Access registered services
});

// After core services booted
add_action('ntdst/core_ready', function($bootstrap) {
    // Core infrastructure available
});

// After all services booted
add_action('ntdst/features_ready', function($bootstrap) {
    // All services available
});

// Per-service hooks
add_action('ntdst/service_before_boot/MyService', function($bootstrap) {});
add_action('ntdst/service_after_boot/MyService', function($instance, $bootstrap) {}, 10, 2);
```

---

## Dependency Injection

The NTDST Container provides autowiring and caching.

### Global Helpers

```php
ntdst_container()              // Get container singleton
ntdst_set($id, $value)         // Register service
ntdst_get($id)                 // Get singleton (cached)
ntdst_make($id, $params)       // Create fresh instance (not cached)
```

### Registration Patterns

```php
// Primitive values
ntdst_set('api_key', 'abc123');
ntdst_set('posts_limit', 10);

// Classes (auto-resolved)
ntdst_set(PaymentGateway::class);

// Factory function
ntdst_set(Logger::class, function($container) {
    return new Logger($container->get('log_path'));
});
```

### Autowiring

Dependencies are automatically resolved via constructor type hints:

```php
class OrderService implements NTDST_Service_Meta
{
    private PaymentGateway $gateway;
    private NTDST_Logger $logger;

    public static function metadata(): array { /* ... */ }

    // Dependencies auto-injected by container
    public function __construct(PaymentGateway $gateway, NTDST_Logger $logger)
    {
        $this->gateway = $gateway;
        $this->logger = $logger;
        $this->init();
    }
}

// Container automatically resolves dependencies
$orders = ntdst_get(OrderService::class);
```

### Method Injection

```php
// Call method with auto-resolved dependencies
ntdst_container()->call([$service, 'processOrder'], [
    'orderId' => 123,  // Primitive passed explicitly
    // OrderRepository $repo - auto-resolved from type hint
]);
```

### Singleton vs Fresh Instance

```php
// Singleton (same instance every time)
$gateway1 = ntdst_get(PaymentGateway::class);
$gateway2 = ntdst_get(PaymentGateway::class);
// $gateway1 === $gateway2

// Fresh instance (new instance every time)
$logger1 = ntdst_make(Logger::class);
$logger2 = ntdst_make(Logger::class);
// $logger1 !== $logger2
```

---

## Enable/Disable Control

Services can be controlled at three levels (checked in order):

### Level 1: Metadata (Code-Level)

Most restrictive - set in service class:

```php
public static function metadata(): array
{
    return [
        'enabled' => false,  // Disabled by default
        // ...
    ];
}
```

### Level 2: Filter (Runtime)

Override at runtime:

```php
// In plugin-config.php / theme-config.php or functions.php.
// Use the project's own prefix — e.g. stride_example_enabled, vad_example_enabled.
add_filter('project_example_enabled', '__return_false');

// Or dynamically
add_filter('project_example_enabled', function($enabled) {
    return current_user_can('administrator');
});
```

### Level 3: Database Option (UI Control)

Least restrictive - controllable via admin UI:

```php
// Disable via database
update_option('ntdst_service_example', '0');

// Enable via database
update_option('ntdst_service_example', '1');
```

### Precedence

```
Metadata (enabled: false) → Service never loads
Filter returns false → Service never loads
Database option '0' → Service never loads
```

---

## Sector Awareness

Services can be conditionally loaded based on enabled platform sectors.

### Available Sectors

- `gallery` - Gallery platform features
- `artist` - Artist portfolio features
- `musician` - Musician platform features (future)

### Sector Tiers

Each sector has tiers that determine available features:

- `essential` - Basic features
- `professional` - Advanced features
- `premium` - All features (gallery only)

### Defining Sector Requirements

```php
public static function metadata(): array
{
    return [
        'name' => 'Artist Portfolio',
        'sectors' => [
            'artist' => 'professional',  // Requires artist sector at professional tier
        ],
    ];
}
```

### Multiple Sector Support

```php
'sectors' => [
    'gallery' => 'essential',   // OR
    'artist' => 'professional', // Loads if either condition is met
],
```

### Checking Sectors at Runtime

```php
$sectors = ntdst_sectors();

// Check if sector enabled
if ($sectors->isEnabled('gallery')) {
    // Gallery features available
}

// Check tier
$tier = $sectors->getTier('artist'); // 'essential', 'professional', or null

// Check tier meets minimum
if ($sectors->hasTier('artist', 'professional')) {
    // Artist at professional or higher
}
```

---

## Priority Guidelines

Priority determines boot order (lower = earlier):

| Priority | Usage | Examples |
|----------|-------|----------|
| 1-5 | Critical infrastructure | Security, Error handling |
| 6-9 | Core framework | Logging, Performance |
| 10-14 | Standard features | SEO, Schema, Analytics |
| 15-19 | Content features | Custom post types, Taxonomies |
| 20-29 | UI enhancements | Transitions, Animations |
| 30+ | Optional features | Social cards, Newsletters |

### Priority Examples

```php
// Security - must run first
'priority' => 2,

// Logging - needed by other services
'priority' => 6,

// SEO - standard feature
'priority' => 12,

// YOOtheme integration - depends on post types
'priority' => 18,

// Barba transitions - UI enhancement
'priority' => 22,
```

---

## Configuration

### Default Config Pattern

```php
private function getDefaultConfig(): array
{
    // Project prefix, not 'netdust_' — replace with your project slug.
    return apply_filters('project_myservice_config', [
        'option1' => 'default',
        'option2' => true,
        'nested' => [
            'setting' => 'value',
        ],
    ]);
}
```

### plugin-config.php / theme-config.php Integration

The Bootstrap automatically merges config from the bootstrap config file (`plugin-config.php` for mu-plugins, `theme-config.php` for themes):

```php
// theme-config.php
return [
    'modules' => [
        'myservice' => [
            'option1' => 'custom_value',
            'option2' => false,
        ],
    ],
];
```

Bootstrap registers a filter at priority 1 that merges these values:

```php
// Automatic - you don't need to write this
add_filter('project_myservice_config', function($defaults) {
    return array_merge($defaults, $moduleConfig);
}, 1);
```

### Accessing Config

```php
// In service
private array $config;

public function __construct()
{
    $this->config = $this->getDefaultConfig();

    // Use config
    if ($this->config['option2']) {
        // Feature enabled
    }
}
```

---

## Service Discovery

### Auto-Discovery (Root Services)

Services in `services/*.php` are auto-discovered when:

```php
// theme-config.php
'services' => [
    'auto_discover' => true,
    'discovery_paths' => [get_stylesheet_directory() . '/services'],
],
```

**Pattern matched:** `*Service.php`

### Sector Auto-Discovery

Services in sector directories are auto-discovered when that sector is enabled:

```
services/
├── gallery/        # Auto-discovered when gallery enabled
│   ├── ArtistService.php
│   └── ArtworkService.php
├── artist/         # Auto-discovered when artist enabled
│   └── PortfolioService.php
└── SeoService.php  # Always auto-discovered (root)
```

### Explicit Registration

Namespaced services must be explicitly registered:

```php
// theme-config.php
'services' => [
    'core' => [
        // Always loaded
        'ntdstheme\\services\\yootheme\\YOOthemeDynamicContentService',
    ],
    'admin' => [
        // Admin only
        'ntdstheme\\services\\admin\\AdminUIService',
    ],
    'conditional' => [
        'og_image' => [
            'service' => 'OgImageService',
            'condition' => fn() => extension_loaded('gd'),
        ],
    ],
],
```

---

## Admin gating

Services that only do work in `wp-admin` (admin controllers, dashboard widgets, settings screens, list tables) gate themselves with `is_admin()` at the top of `init()` — NOT via an `admin_only` metadata flag. Runtime gating keeps the gate visible in code where the hooks are registered, and lets the constructor still wire DI.

```php
final class EditionAdminController
{
    public function __construct(
        private readonly EditionRepository $repository,
    ) {
        $this->init();
    }

    private function init(): void
    {
        if (!is_admin()) {
            return;  // Frontend request — nothing to register.
        }

        add_action('admin_menu', [$this, 'registerMenu']);
        add_filter('manage_edition_posts_columns', [$this, 'addColumns']);
        add_action('manage_edition_posts_custom_column', [$this, 'renderColumn'], 10, 2);
    }

    // ...
}
```

Why not the `admin_only` metadata flag? Because it gates *bootstrap*, which means the class is never instantiated outside admin — so any frontend code that later wants to call into it (a partial admin badge in a frontend toolbar, an AJAX endpoint, a CLI command) can't. Runtime gating is the safer default.

Admin controllers are themselves usually NOT top-level services — they're sub-components owned by a parent service. See "Sub-services and admin controllers" below.

## Sub-services and admin controllers

Some classes have hooks but aren't promotion-worthy as top-level services. Two common shapes:

### Owned sub-services

A self-contained piece of a larger feature (Sessions inside Editions, EditionCompletion inside Editions). Register inside the parent's `init()` via `ntdst_set()`:

```php
final class EditionService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return ['name' => 'Editions', 'priority' => 10];
    }

    public function __construct(
        private readonly EditionRepository $repository,
    ) {
        $this->init();
    }

    private function init(): void
    {
        // Sub-services owned by this feature — singletons, not top-level services.
        ntdst_set(SessionService::class, fn() =>
            new SessionService($this->repository)
        );
        ntdst_set(EditionCompletion::class, fn() =>
            new EditionCompletion(ntdst_get(SessionService::class))
        );

        // Bootstrap them (they self-register their hooks)
        ntdst_get(SessionService::class);
        ntdst_get(EditionCompletion::class);

        // Parent's own hooks
        add_action('save_post_edition', [$this, 'onEditionSaved']);
    }
}
```

Sub-services are plain classes — no `NTDST_Service_Meta`, no `metadata()`, no entry in `plugin-config.php`. They're internal implementation. Stride's `SessionService` and `EditionCompletion` are the canonical examples.

### Admin controllers

Same shape, but instantiated with `new` because they don't need to be in the container — nothing else in the codebase needs to retrieve them:

```php
private function init(): void
{
    // Admin controller is a sub-component, not a service.
    new EditionAdminController($this->repository);
}
```

The controller's own `init()` does the `is_admin()` gate (see above). The owning service stays admin-agnostic.

## CPT registration

CPTs in an NTDST project are registered via **`ntdst_data()->register()`**, the framework's Data Manager wrapper around `register_post_type()`. The wrapper takes the same WordPress arg array plus framework keys (`meta_prefix`, `fields`, `auto_metabox`) that hook the CPT into the rest of the harness — typed field defs, auto-generated metaboxes, query-builder access via `ntdst_data()->get(POST_TYPE)`, repository hydration. **Calling `register_post_type()` directly bypasses all of that** and decouples the CPT from the data layer; don't do it.

The CPT lives in a **dedicated `*CPT` class** that owns the registration call and exposes the post-type slug as a `POST_TYPE` constant. Services, repositories, templates, queries, and tests reference the constant — never the literal string.

```php
// Stride's actual EditionCPT pattern. Replace `Stride\Modules\Edition` and
// `vad_edition` / `_ntdst_` with your project's namespace and slugs.
namespace {Project}\Modules\Edition;

final class EditionCPT
{
    public const POST_TYPE = 'vad_edition';

    public static function register(): void
    {
        ntdst_data()->register(self::POST_TYPE, [
            'meta_prefix'        => '_ntdst_',
            'label'              => 'Edities',
            'labels'             => [
                'name'          => 'Edities',
                'singular_name' => 'Editie',
                'add_new'       => 'Nieuwe editie',
                'add_new_item'  => 'Nieuwe editie toevoegen',
                'edit_item'     => 'Editie bewerken',
            ],
            'public'             => true,
            'publicly_queryable' => true,
            'has_archive'        => true,
            'show_ui'            => true,
            'show_in_menu'       => 'stride-dashboard',
            'menu_icon'          => 'dashicons-calendar-alt',
            'supports'           => ['title'],

            // Framework-specific keys (NOT in WP's register_post_type)
            'fields'             => self::getFields(),
            'auto_metabox'       => false, // custom UI via owning service's admin controller
        ]);
    }

    /** Typed field defs the Data Manager validates/casts/persists. */
    private static function getFields(): array
    {
        return [
            'course_id'  => ['type' => 'int',     'label' => 'Cursus',     'required' => true],
            'start_date' => ['type' => 'text',    'label' => 'Startdatum', 'required' => true],
            'capacity'   => ['type' => 'int',     'label' => 'Capaciteit', 'required' => true],
            'price'      => ['type' => 'float',   'label' => 'Prijs'],
            'documents'  => ['type' => 'json',    'label' => 'Documenten'],
            // ... see Stride's EditionCPT.php for the full shape.
        ];
    }
}
```

The owning service hooks the registration on `init` from its own `init()`:

```php
final class EditionService implements \NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return ['name' => 'Editions', 'priority' => 10];
    }

    public function __construct(
        private readonly EditionRepository $repository,
    ) {
        $this->init();
    }

    private function init(): void
    {
        add_action('init', [EditionCPT::class, 'register']);

        // Other hooks reference EditionCPT::POST_TYPE — never the literal string.
        add_filter('manage_' . EditionCPT::POST_TYPE . '_posts_columns', [$this, 'addColumns']);
    }
}
```

Repositories then query the CPT through the Data Manager rather than `WP_Query`:

```php
ntdst_data()->get(EditionCPT::POST_TYPE)
    ->where('course_id', $courseId)
    ->withMeta()
    ->get();
```

Why this shape (and not raw `register_post_type()`)?

- **Field defs in one place.** The `fields` array drives validation, metabox generation, REST exposure, and the query-builder's column knowledge. Raw `register_post_type()` gives you none of that.
- **Repository contract.** `ntdst_data()->get(POST_TYPE)` works only for CPTs registered via the wrapper. Calling `register_post_type()` directly means your repository has to fall back to `WP_Query` and `get_post_meta()` everywhere.
- **Constant reuse.** `EditionCPT::POST_TYPE` is the single source of truth — repos, queries, templates, admin, tests all import it.
- **Discoverability.** `grep '*CPT.php'` answers "where is this CPT defined?" in one hop.

Don't:
- Call `register_post_type()` directly — anywhere. The wrapper is the contract; bypassing it breaks the data layer.
- Put the registration in a service method instead of a `*CPT` class — the constant lives on the class, not the service.
- Make `EditionCPT` a service (no metadata, no DI — it's a static config holder called from the owning service's `init()`).

## Anti-Patterns

### Missing Interface

```php
// WRONG - Won't be recognized as service
class MyService
{
    // Missing NTDST_Service_Meta
}

// CORRECT
class MyService implements NTDST_Service_Meta
{
    public static function metadata(): array
    {
        return ['name' => 'My Service'];
    }
}
```

### Initialization Outside Constructor

```php
// WRONG - Init should be in constructor
class MyService implements NTDST_Service_Meta
{
    public function register(): void
    {
        add_action('init', [$this, 'setup']);
    }
}

// CORRECT - Constructor calls init()
class MyService implements NTDST_Service_Meta
{
    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        add_action('init', [$this, 'setup']);
    }
}
```

### Wrong Priority

```php
// WRONG - Too low priority for a UI feature
public static function metadata(): array
{
    return [
        'name' => 'Fancy Transitions',
        'priority' => 3,  // This is infrastructure priority!
    ];
}

// CORRECT - UI features should be 20+
public static function metadata(): array
{
    return [
        'name' => 'Fancy Transitions',
        'priority' => 22,
    ];
}
```

### Circular Dependencies

```php
// WRONG - ServiceA depends on ServiceB which depends on ServiceA
class ServiceA implements NTDST_Service_Meta
{
    public function __construct(ServiceB $b) { }
}

class ServiceB implements NTDST_Service_Meta
{
    public function __construct(ServiceA $a) { }  // Circular!
}

// CORRECT - Use events/hooks for loose coupling
class ServiceA implements NTDST_Service_Meta
{
    public function __construct()
    {
        add_action('service_b_ready', [$this, 'onServiceBReady']);
    }
}

class ServiceB implements NTDST_Service_Meta
{
    public function __construct()
    {
        do_action('service_b_ready', $this);
    }
}
```

### Direct Instantiation

```php
// WRONG - Bypasses DI container
$service = new MyService();

// CORRECT - Use container
$service = ntdst_get(MyService::class);
```

### Config Filter Not Applied

```php
// WRONG - No filter, can't be customized
private function getConfig(): array
{
    return [
        'option' => 'value',
    ];
}

// CORRECT - Filter allows customization
private function getDefaultConfig(): array
{
    return apply_filters('project_myservice_config', [
        'option' => 'value',
    ]);
}
```

---

## Quick Reference

### Service Checklist

- [ ] Implements `NTDST_Service_Meta`
- [ ] Has `metadata()` with name, description, priority
- [ ] Constructor calls `$this->init()`
- [ ] Uses `apply_filters()` for default config
- [ ] Appropriate priority (1-9 core, 10-19 features, 20+ UI)
- [ ] Sector requirements if applicable
- [ ] Namespaced services registered in the bootstrap config file (`plugin-config.php` for mu-plugins, `theme-config.php` for themes)

### Key Functions

```php
ntdst_get(Service::class)      // Get service singleton
ntdst_make(Service::class)     // Create fresh instance
ntdst_container()              // Access DI container
ntdst_sectors()->isEnabled()   // Check sector status
```

### Hook Conventions

Framework internals (ntdst-core's own events) use `ntdst/*`. Project-level service hooks and domain events use the project's own prefix (`stride_*`, `stride/*`, `vad_*`, etc.) — NOT `netdust_`.

```php
// Framework hooks (ntdst-core internals)
do_action('ntdst/services_registered', $bootstrap);

// Project-level service config — replace {project} with the project slug
// (e.g. stride_edition_config, vad_intake_config, atelier296_artwork_config).
apply_filters('{project}_{slug}_config', $defaults);
add_filter('{project}_{slug}_enabled', '__return_false');

// Project-level domain events — plain associative arrays as payloads.
// e.g. do_action('stride/registration/created', ['user_id' => ..., 'edition_id' => ...])
do_action('{project}/{domain}/{action}', [
    'user_id'    => $user_id,
    'edition_id' => $edition_id,
]);
```
