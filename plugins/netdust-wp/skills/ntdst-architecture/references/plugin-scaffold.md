# Plugin Scaffold Templates

When creating standalone WordPress plugins (not NTDST services), use these templates.

## Directory Structure

```
plugin-name/
├── plugin-name.php              # Bootstrap (minimal)
├── composer.json                 # PSR-4 autoloading
├── config/
│   ├── plugin.php               # General config + provider list
│   └── assets.php               # Script/style registration
├── src/
│   ├── Plugin.php               # Thin orchestrator
│   ├── Container.php            # Lightweight DI container
│   ├── ServiceProvider.php      # Abstract base provider
│   ├── Providers/
│   ├── Services/
│   ├── Repositories/
│   │   └── Contracts/           # Interfaces
│   ├── Models/
│   ├── ValueObjects/
│   ├── DTOs/
│   ├── Http/
│   │   ├── Controllers/
│   │   └── Middleware/
│   ├── Admin/
│   │   ├── Pages/
│   │   └── MetaBoxes/
│   └── Support/
├── resources/
│   ├── views/
│   ├── assets/
│   └── languages/
└── tests/
```

## Bootstrap File Template

```php
<?php
/**
 * Plugin Name: {Plugin Name}
 * Description: {Description}
 * Version: 1.0.0
 * Requires PHP: 8.1
 * Author: Netdust
 * Text Domain: {text-domain}
 */

declare(strict_types=1);

if (! defined('ABSPATH')) exit;

require_once __DIR__ . '/vendor/autoload.php';

use {Namespace}\Plugin;

function {function_name}(): Plugin
{
    static $plugin = null;
    if ($plugin === null) {
        $plugin = new Plugin(__FILE__);
    }
    return $plugin;
}

{function_name}()->boot();
```

## Container Template

```php
<?php
declare(strict_types=1);

namespace {Namespace};

use Closure;
use InvalidArgumentException;

class Container
{
    private array $bindings = [];
    private array $instances = [];

    public function bind(string $abstract, Closure $factory): void
    {
        $this->bindings[$abstract] = $factory;
    }

    public function singleton(string $abstract, Closure $factory): void
    {
        $this->bindings[$abstract] = function () use ($abstract, $factory) {
            if (! isset($this->instances[$abstract])) {
                $this->instances[$abstract] = $factory($this);
            }
            return $this->instances[$abstract];
        };
    }

    public function instance(string $abstract, object $concrete): void
    {
        $this->instances[$abstract] = $concrete;
    }

    public function get(string $abstract): mixed
    {
        if (isset($this->instances[$abstract])) {
            return $this->instances[$abstract];
        }
        if (isset($this->bindings[$abstract])) {
            return ($this->bindings[$abstract])($this);
        }
        throw new InvalidArgumentException("No binding for [{$abstract}]");
    }

    public function has(string $abstract): bool
    {
        return isset($this->bindings[$abstract]) || isset($this->instances[$abstract]);
    }
}
```

## ServiceProvider Base Template

```php
<?php
declare(strict_types=1);

namespace {Namespace};

abstract class ServiceProvider
{
    public function __construct(
        protected readonly Container $container
    ) {}

    /** Register bindings. No hooks, no side effects. */
    abstract public function register(): void;

    /** Boot after ALL providers registered. Hooks go here. */
    public function boot(): void {}
}
```

## Plugin Orchestrator Template

```php
<?php
declare(strict_types=1);

namespace {Namespace};

class Plugin
{
    private Container $container;
    private string $basePath;
    private string $baseUrl;
    private array $providers = [];

    public function __construct(string $pluginFile)
    {
        $this->basePath = plugin_dir_path($pluginFile);
        $this->baseUrl = plugin_dir_url($pluginFile);
        $this->container = new Container();
        $this->container->instance(self::class, $this);
        $this->container->instance(Container::class, $this->container);
    }

    public function boot(): void
    {
        $this->loadConfig();
        $this->registerProviders();
        $this->bootProviders();
    }

    public function container(): Container { return $this->container; }
    public function basePath(string $path = ''): string { return $this->basePath . ltrim($path, '/'); }
    public function baseUrl(string $path = ''): string { return $this->baseUrl . ltrim($path, '/'); }

    public function config(string $key, mixed $default = null): mixed
    {
        $segments = explode('.', $key);
        $file = array_shift($segments);
        $config = $this->container->get("config.{$file}");
        foreach ($segments as $segment) {
            if (! is_array($config) || ! array_key_exists($segment, $config)) return $default;
            $config = $config[$segment];
        }
        return $config;
    }

    private function loadConfig(): void
    {
        $configPath = $this->basePath('config/');
        if (! is_dir($configPath)) return;
        foreach (glob($configPath . '*.php') as $file) {
            $name = basename($file, '.php');
            $this->container->instance("config.{$name}", require $file);
        }
    }

    private function registerProviders(): void
    {
        foreach ($this->config('plugin.providers', []) as $class) {
            $provider = new $class($this->container);
            $provider->register();
            $this->providers[] = $provider;
        }
    }

    private function bootProviders(): void
    {
        foreach ($this->providers as $provider) $provider->boot();
    }
}
```

## Config Template

```php
<?php
// config/plugin.php
return [
    'name'    => '{Plugin Name}',
    'version' => '1.0.0',
    'prefix'  => '{prefix}',
    'providers' => [
        \{Namespace}\Providers\AssetServiceProvider::class,
    ],
];
```

## Composer Template

```json
{
    "name": "netdust/{slug}",
    "type": "wordpress-plugin",
    "license": "GPL-2.0-or-later",
    "require": { "php": ">=8.1" },
    "autoload": {
        "psr-4": { "{Namespace}\\": "src/" }
    }
}
```

## Scaffold Checklist

When creating a new plugin, ALWAYS generate:
1. Bootstrap file with plugin headers
2. `composer.json` with PSR-4 autoloading
3. `src/Plugin.php` orchestrator
4. `src/Container.php` DI container
5. `src/ServiceProvider.php` abstract base
6. `config/plugin.php` with providers list
7. At least one concrete provider
8. At least one service demonstrating DI
