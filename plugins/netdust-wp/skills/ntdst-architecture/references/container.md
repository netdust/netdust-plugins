# NTDST Container (Dependency Injection)

Lightweight DI container with automatic class resolution and caching.

**Location:** `app/content/mu-plugins/ntdst-core/core/Container.php`

## Conventions

- Register bindings **before** the `ntdst/features_ready` hook. After that, only mutate the container from tests.
- Rebinding an ID does NOT invalidate consumers that already resolved it. If a test needs fresh resolution after rebinding, call `flush()`.
- Circular dependencies throw `RuntimeException` with the resolution chain — see "Cycle detection" below.

## Global Helpers

All helpers are wrapped in `function_exists()` guards so they tolerate double-load when multiple plugins ship a copy of ntdst-core.

```php
ntdst_container()              // Get singleton container
ntdst_set($id, $value)         // Register service (see "set semantics" below)
ntdst_get($id)                 // Get singleton instance (cached)
ntdst_make($id, $params)       // Create fresh instance (not cached)
```

## Registration

### Primitive Values

```php
ntdst_set('api_key', 'abc123');
ntdst_set('max_items', 100);

// Retrieve
$key = ntdst_get('api_key');
```

### set() semantics: `null` vs no second arg

```php
// Shorthand — registers the ID as its own class. Equivalent to
// ntdst_set(PaymentGateway::class, PaymentGateway::class);
ntdst_set(PaymentGateway::class);

// Explicit null — stores null as the registered value. ntdst_get($id)
// returns null without re-resolving.
ntdst_set('legacy_handle', null);
```

These are distinct: the implementation uses `func_num_args()` to tell them apart. Passing a single argument never accidentally stores `null`.

### Factory Functions

```php
ntdst_set(PaymentGateway::class, function($container) {
    return new PaymentGateway(
        $container->get('api_key'),
        $container->get(Logger::class)
    );
});
```

**Factory parameter typing rule.** The container is passed as the first argument **only when** the factory's first parameter is untyped or typed as `NTDST_Container` (or a parent class). Other typed first parameters mean "I don't want the container" — the factory is called with no args.

```php
// container passed (untyped)
ntdst_set('svc', fn($c) => new Svc($c->get('cfg')));

// container passed (explicitly typed)
ntdst_set('svc', fn(NTDST_Container $c) => new Svc($c->get('cfg')));

// container NOT passed — $count uses its default
ntdst_set('limit', fn(int $count = 10) => $count);
```

### Class Aliases

```php
// Interface to implementation binding
ntdst_set(PaymentInterface::class, StripeGateway::class);
```

**Typo'd bindings fail loudly.** If you bind to a string that *looks like* a class name (contains `\` or starts uppercase) but doesn't exist, `ntdst_get()` throws `RuntimeException("Binding X points to non-existent class Y")` instead of silently returning the typo string. Primitive string values (e.g. `'on'`, `'production'`) still work.

## Resolution

### Get Singleton (Cached)

```php
// First call creates instance, subsequent calls return same instance
$service = ntdst_get(MyService::class);
$same = ntdst_get(MyService::class); // Same instance
```

### Make Fresh Instance

```php
// Always creates new instance
$fresh = ntdst_make(MyService::class);
$another = ntdst_make(MyService::class); // Different instance
```

### With Parameters

Keys in `$params` must match constructor parameter names exactly. Unknown keys throw `RuntimeException("Unknown parameter(s) for X: typo_name")` so typos surface at the call site instead of being silently autowired.

```php
$service = ntdst_make(ReportGenerator::class, [
    'format' => 'pdf',
    'date_range' => $range,
]);
```

## Autowiring

Classes with type-hinted constructor parameters are automatically resolved:

```php
class OrderService
{
    private PaymentGateway $gateway;
    private Logger $logger;
    private Mailer $mailer;

    public function __construct(
        PaymentGateway $gateway,
        Logger $logger,
        Mailer $mailer
    ) {
        $this->gateway = $gateway;
        $this->logger = $logger;
        $this->mailer = $mailer;
    }
}

// All dependencies auto-injected!
$orders = ntdst_get(OrderService::class);
```

## Method Invocation with DI

Call methods with automatic dependency injection:

```php
$container = ntdst_container();

// Call method, injecting any type-hinted parameters
$result = $container->call([$service, 'processOrder'], [
    'order_id' => 123,  // Non-typed params passed explicitly
]);
```

## Service Pattern in Services

```php
class AdvancedService implements NTDST_Service_Meta
{
    private NTDST_Theme $theme;
    private NTDST_Data_Manager $data;
    private NTDST_Logger $logger;

    public static function metadata(): array
    {
        return [
            'name' => 'Advanced Service',
            'priority' => 15,
        ];
    }

    // Dependencies auto-injected by Bootstrap
    public function __construct(
        NTDST_Theme $theme,
        NTDST_Data_Manager $data,
        NTDST_Logger $logger
    ) {
        $this->theme = $theme;
        $this->data = $data;
        $this->logger = $logger;
        $this->init();
    }

    private function init(): void
    {
        // Use injected dependencies
        $this->theme->apiAction('my_action', [$this, 'handleAction']);
    }
}
```

## Available Core Services

These are pre-registered and available for injection:

| Class | Description |
|-------|-------------|
| `NTDST_Container` | The container itself |
| `NTDST_Theme` | Theme fluent API |
| `NTDST_Data_Manager` | Data ORM |
| `NTDST_Router` | URL routing |
| `NTDST_Logger` | Logging service |
| `NTDST_Mailer` | Email service |

## Common Patterns

### Getting Framework Services

```php
// In any code
$theme = ntdst_get(NTDST_Theme::class);
$data = ntdst_get(NTDST_Data_Manager::class);
$router = ntdst_get(NTDST_Router::class);

// Or use global helpers
$data = ntdst_data();
$router = ntdst_router();
$logger = ntdst_log();
$mailer = ntdst_mail();
```

### Creating Service Factories

```php
// Register factory for complex initialization
ntdst_set(ReportService::class, function($c) {
    $service = new ReportService(
        $c->get(NTDST_Data_Manager::class)
    );
    $service->setFormat('pdf');
    $service->setLocale(get_locale());
    return $service;
});
```

### Conditional Registration

```php
// Register different implementations based on environment
if (defined('WP_DEBUG') && WP_DEBUG) {
    ntdst_set(CacheInterface::class, NullCache::class);
} else {
    ntdst_set(CacheInterface::class, FileCache::class);
}
```

## Container Methods Reference

| Method | Description |
|--------|-------------|
| `set($id, $value)` | Register service/value. One-arg form registers ID as its own class; explicit null stores null. |
| `get($id)` | Get singleton (cached). Throws on cycles and on bindings pointing to non-existent classes. |
| `make($id, $params)` | Create fresh instance. Unknown `$params` keys throw. |
| `has($id)` | **PSR-11 semantics:** true for registered IDs AND for autowirable classes that exist. Returns true iff `get($id)` will not throw a "not found" error. |
| `call($callable, $params)` | Invoke with DI. |
| `forget($id)` | Remove a service from the container. Also clears its cached reflection. |
| `flush()` | Reset the container (preserves the container's self-binding). Clears `services`, `resolved`, `reflections`, `callableReflections`, and `factoryCache` — safe to call between test cases. |

## Cycle detection

The container tracks an in-progress `$resolving` set and throws on re-entry with the full chain. The error is clear instead of opaque max-nesting-level fatals.

```php
class A { public function __construct(B $b) {} }
class B { public function __construct(A $a) {} }

ntdst_get(A::class);
// RuntimeException: Circular dependency detected: A -> B -> A
```

Fix by refactoring the constructor (extract a shared dependency) or wiring loose coupling via WordPress hooks rather than direct injection.

## Error messages

Unresolvable parameters produce a typed message: `"Cannot resolve parameter: $name (TypeStr) in ClassOrGlobal"`. For closures and functions outside a class, the location reads as `<global>` instead of crashing on `getDeclaringClass()->getName()`.

## Interface Binding

```php
// Bind interface to concrete implementation
ntdst_set(PaymentInterface::class, StripeGateway::class);

// Now any class type-hinting PaymentInterface gets StripeGateway
class OrderService {
    public function __construct(private readonly PaymentInterface $gateway) {}
}
```

## Conditional Registration

```php
if (defined('WP_DEBUG') && WP_DEBUG) {
    ntdst_set(CacheInterface::class, NullCache::class);
} else {
    ntdst_set(CacheInterface::class, FileCache::class);
}
```

---

# Bootstrap Lifecycle

The Bootstrap orchestrates service initialization. It's covered in detail in `services.md` (lifecycle phases), but here's the wiring reference.

## Where the bootstrap config lives

Two shapes, depending on layer:

| Layer | File | Bootstrapped from |
|-------|------|-------------------|
| **mu-plugin** (`mu-plugins/<project>-core/`) | `plugin-config.php` at the mu-plugin root | The plugin's loader (`<project>-coreloader.php` or `<project>-core.php`) |
| **Theme** | `config/theme-config.php` | `functions.php` |

The structure of the array is the same. Use the file that matches where the bootstrap call lives — Stride (mu-plugin) uses `plugin-config.php`; smaller theme-only projects use `theme-config.php`. Mixing them in one project is fine when both a mu-plugin and a theme bootstrap.

## Wiring in `<project>-coreloader.php` (mu-plugin)

```php
$config = require __DIR__ . '/<project>-core/plugin-config.php';

$bootstrap = new NTDST_Bootstrap($config);
$bootstrap->register();

add_action('after_setup_theme', [$bootstrap, 'bootCore'], 5);
add_action('after_setup_theme', [$bootstrap, 'bootFeatures'], 15);
```

## Wiring in `functions.php` (theme)

```php
require_once get_template_directory() . '/vendor/ntdst-core/load.php';

$config = require get_template_directory() . '/config/theme-config.php';

$bootstrap = new NTDST_Bootstrap($config);
$bootstrap->register();

add_action('after_setup_theme', [$bootstrap, 'bootCore'], 5);
add_action('after_setup_theme', function() use ($config) {
    $theme = new NTDST_Theme($config);
}, 10);
add_action('after_setup_theme', [$bootstrap, 'bootFeatures'], 15);
```

## Config Structure

```php
// plugin-config.php (mu-plugin) or config/theme-config.php (theme) — same shape
return [
    'services' => [
        'auto_discover' => true,
        'discovery_paths' => [get_stylesheet_directory() . '/services/'],
        'core' => [SecurityService::class, PerformanceService::class],
        'admin' => [AdminDashboardService::class],
        'conditional' => [
            'woocommerce' => [
                'condition' => fn() => class_exists('WooCommerce'),
                'service' => ShopService::class,
            ],
        ],
    ],
    'modules' => [
        'barba' => ['animationDuration' => 300],
        'security' => ['disable_xmlrpc' => true],
    ],
    'assets' => [
        'styles' => [
            'ntdst-theme' => [
                'src'     => $dist . '/theme.css',
                'version' => '1.0',
                'attrs'   => ['crossorigin' => 'anonymous'],
            ],
        ],
        'scripts' => [
            'ntdst-theme' => [
                'src'       => $dist . '/theme.js',
                'deps'      => [],
                'in_footer' => true,
                'attrs'     => ['type' => 'module'],
            ],
            'ntdst-admin' => [
                'src'   => $dist . '/admin.js',
                'admin' => true,  // only enqueued in wp-admin
            ],
        ],
    ],
    // theme_support, menus, sidebars, excerpt, etc.
];
```

Scripts/styles with `'admin' => true` are enqueued via `admin_enqueue_scripts`. Custom attributes (type, defer, crossorigin) are added via `script_loader_tag` / `style_loader_tag` filters automatically.

---

## Anti-Pattern

```php
// WRONG - creating dependencies manually
class MyService {
    public function __construct() {
        $this->data = new NTDST_Data_Manager(); // Don't do this!
        $this->logger = NTDST_Logger::getInstance(); // Or this!
    }
}

// CORRECT - use constructor injection
class MyService {
    public function __construct(
        NTDST_Data_Manager $data,
        NTDST_Logger $logger
    ) {
        $this->data = $data;
        $this->logger = $logger;
    }
}
```
