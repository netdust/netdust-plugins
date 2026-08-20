# Template: Namespaced Service

For services in a subdirectory (gallery/, artist/, printshop/, etc.). A
subdirectory is organisation only — it is never auto-discovered, so the class
is always listed explicitly in the bootstrap config.

```php
<?php
/**
 * {ServiceName} Service
 *
 * {Description}
 *
 * @package ntdstheme\services\{group}
 */
namespace ntdstheme\services\{group};

defined('ABSPATH') || exit;

class {ServiceName}Service implements \NTDST_Service_Meta
{
    private array $config;

    /**
     * Service metadata
     */
    public static function metadata(): array
    {
        return [
            'name' => '{Display Name}',
            'description' => '{What this service does}',
            'admin_only' => false,
            'enabled' => true,
            'priority' => 15,
        ];
    }

    public function __construct()
    {
        $this->config = $this->getDefaultConfig();
        $this->init();
    }

    /**
     * Get configuration with filter for customization
     */
    private function getDefaultConfig(): array
    {
        return apply_filters('netdust_{slug}_config', [
            'enabled' => true,
        ]);
    }

    /**
     * Initialize service hooks
     */
    private function init(): void
    {
        add_action('init', [$this, 'registerHooks']);
    }

    /**
     * Register hooks after WordPress init
     */
    public function registerHooks(): void
    {
        // Add your hook registrations here
    }
}
```

## Placeholders

| Placeholder | Replace With |
|-------------|--------------|
| `{ServiceName}` | PascalCase name |
| `{group}` | Subdirectory name (gallery, artist, printshop) |
| `{Display Name}` | Human-readable name |
| `{Description}` | Brief description |
| `{slug}` | lowercase_underscore |

## Location

`app/content/themes/ntdstheme/services/{group}/{ServiceName}Service.php`

## Required Registration

Namespaced services must be registered in `theme-config.php`:

```php
'services' => [
    'core' => [
        'ntdstheme\\services\\{group}\\{ServiceName}Service',
    ],
],
```

## Making it switchable

There are no sector tiers in ntdst-core 4.x. A service that must be
switchable per site uses the three-level enable/disable control:
`metadata()['enabled']`, the `ntdst_service_{slug}_enabled` filter, or the
`ntdst_service_{slug}` option.
