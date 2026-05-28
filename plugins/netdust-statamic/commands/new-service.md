---
description: Scaffold a Service class following the project's thin-controller / service-layer pattern
argument-hint: <ServiceName>
---

Create a new service class named `$1Service`.

Steps:
1. Run `make service NAME=$1` (this generates `app/Services/$1Service.php`).
2. Open the generated file and:
   - Use PHP 8 constructor property promotion for dependencies.
   - Add explicit return types and parameter type hints.
   - Keep public methods focused on one business operation each; extract helpers as `private`.
3. Register the service as a singleton in `app/Providers/AppServiceProvider.php` under `register()`:
   ```php
   $this->app->singleton(\App\Services\$1Service::class);
   ```
4. If the service handles HTTP, also create a thin controller via `make controller NAME=$1` and inject the service.
5. If the service responds to Statamic events, create a listener via `make listener NAME=Sync$1` and register it in `boot()`.
6. Run `vendor/bin/pint --dirty --format agent` before finishing.

Reference: `CLAUDE.md` "Service Architecture" section for the canonical patterns.
