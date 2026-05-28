# Template: Root Service

```php
<?php
/**
 * {ServiceName} Service
 *
 * {Description}
 */
defined('ABSPATH') || exit;

class {ServiceName}Service implements NTDST_Service_Meta
{
    private array $config;

    /**
     * Service metadata for auto-discovery
     */
    public static function metadata(): array
    {
        return [
            'name' => '{Display Name}',
            'description' => '{What this service does}',
            'admin_only' => false,
            'enabled' => true,
            'priority' => 10,
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
            // Default configuration options
            'enabled' => true,
        ]);
    }

    /**
     * Initialize service hooks
     */
    private function init(): void
    {
        // Register WordPress hooks
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
| `{ServiceName}` | PascalCase name (e.g., `Newsletter`) |
| `{Display Name}` | Human-readable name (e.g., `Newsletter Service`) |
| `{Description}` | Brief description of purpose |
| `{slug}` | lowercase_underscore (e.g., `newsletter`) |

## Location

`app/content/themes/ntdstheme/services/{ServiceName}Service.php`

Root services are auto-discovered - no registration needed.
