# Template: Namespaced Service

For services in sector subdirectories (gallery/, artist/, printshop/, etc.)

```php
<?php
/**
 * {ServiceName} Service
 *
 * {Description}
 *
 * @package ntdstheme\services\{sector}
 */
namespace ntdstheme\services\{sector};

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
            // Optional: restrict to specific sectors
            'sectors' => ['{sector}' => 'essential'],
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
| `{sector}` | Subdirectory name (gallery, artist, printshop) |
| `{Display Name}` | Human-readable name |
| `{Description}` | Brief description |
| `{slug}` | lowercase_underscore |

## Location

`app/content/themes/ntdstheme/services/{sector}/{ServiceName}Service.php`

## Required Registration

Namespaced services must be registered in `theme-config.php`:

```php
'services' => [
    'core' => [
        'ntdstheme\\services\\{sector}\\{ServiceName}Service',
    ],
],
```

## Sector Tiers

| Tier | Use For |
|------|---------|
| `essential` | Core features required by all users |
| `professional` | Premium features for paying users |
