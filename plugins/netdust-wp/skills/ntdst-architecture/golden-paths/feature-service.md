# Golden path — a feature service: hooks, DI, config, a route, a rendered page

**Verified against source:** 2026-08-09, `ntdst-core` @ daan `45b8158`
(`core/Bootstrap.php`, `core/Container.php`, `core/Router.php`, `core/Theme.php`, `api/Response.php`),
and against live consumers `daan-core/services/musician/CardService.php` and
`daan-core/services/admin/AdminUIService.php`.

This is the slice for a feature that is **not** primarily a data model — it registers hooks, takes
injected dependencies, owns a custom URL, and renders a template. For a CPT with fields and API
actions, use `ntdst-data`'s `golden-paths/model-and-api-action.md` instead; a real feature often needs
both.

---

## The service

```php
<?php

declare(strict_types=1);

namespace harbor\services\booking;

use NTDST_Service_Meta;
use NTDST_Template_Loader;

defined('ABSPATH') || exit;

final class BookingService implements NTDST_Service_Meta
{
    private const BOOKING_PATH = 'booking/:venue';

    /** @var array<string,mixed> */
    private array $config;

    public static function metadata(): array
    {
        return [
            'name'        => 'Booking',
            'description' => 'Public booking page and confirmation mail.',
            'priority'    => 12,   // standard feature band
        ];
    }

    // Dependencies are AUTOWIRED. Type-hint them; never `new` them here.
    public function __construct(
        private readonly VenueRepository $venues,
        private readonly BookingCalculator $calculator,
    ) {
        $this->config = $this->getDefaultConfig();
        $this->init();
    }

    /** @return array<string,mixed> */
    private function getDefaultConfig(): array
    {
        // Bootstrap fires `ntdst_service_{slug}_config` and feeds it from the
        // bootstrap config's services.overrides. Read THAT filter if you want
        // overrides to reach you. A project-prefixed filter of your own is a
        // second surface the framework knows nothing about — if you use one,
        // say so in the class docblock. Slug here is `booking`.
        return apply_filters('ntdst_service_booking_config', [
            'hold_minutes' => 15,
            'max_seats'    => 8,
        ]);
    }

    // init() registers things on the site. This is what makes it a service.
    private function init(): void
    {
        add_action('wp_enqueue_scripts', [$this, 'enqueue'], 20);

        $this->registerRoutes();

        // A sub-component: hooks of its own, but not toggle-worthy on its own,
        // so it is a PLAIN CLASS owned here — not a second service.
        new BookingAdminColumns($this->venues);
    }

    // =====================================================================
    // Routing — the route alone is enough; no rewrite rule required
    // =====================================================================

    private function registerRoutes(): void
    {
        // Register SPECIFIC routes before generic ones; first match wins.
        // The callback receives ($params, $template) — $params is an ASSOCIATIVE
        // ARRAY keyed by the :placeholder names, not positional arguments.
        ntdst_router()->get(self::BOOKING_PATH, function (array $params) {
            $venue = $this->venues->findBySlug(sanitize_title($params['venue'] ?? ''));

            if (is_wp_error($venue) || $venue === null) {
                return ntdst_response()->notFound();
            }

            // Hand the view model to the template loader; the template reads it
            // back with ntdst_page_data(). Build it ONCE per request.
            return NTDST_Template_Loader::page('booking/form', [
                'venue' => $venue,
                'seats' => $this->calculator->availableSeats($venue->ID),
            ]) ?? ntdst_response()->notFound();
        });
    }

    public function enqueue(): void
    {
        // …
    }
}
```

**The route callback MUST return.** A callback that falls off the end returns `null`, which **exits
the request** — a route that "isn't running" and renders a blank page is almost always a missing
`return`.

**Path parameters arrive as one associative array**, keyed by the `:placeholder` name — the callback
signature is `($params, $template)`, not one argument per placeholder.

**A route does not need a rewrite rule.** The router matches the request URI on `template_include`,
so `ntdst_router()->get('/card', …)` works on its own — verified against a live consumer that
registers routes and no rewrite rules at all. Add a rewrite rule only when you actually need WordPress
to populate query vars for the URL, or need it out of a 404 state before your route runs. (Older
framework docs said both were always required; they were wrong.) If you do add one, flush on
activation — never on every request.

**Query-string parameters are not in that array.** `?page=2` is read from `$_GET` inside the callback.

## The template

```php
<?php
// harbor-core/templates/booking/form.php
defined('ABSPATH') || exit;

$data  = ntdst_page_data();
$venue = $data['venue'] ?? null;
$seats = (int) ($data['seats'] ?? 0);
?>
<h1><?php echo esc_html($venue->post_title); ?></h1>
<p><?php printf(esc_html__('%d seats left', 'harbor'), $seats); ?></p>
```

Register the directory once, at plugin bootstrap, so the loader can find it:

```php
NTDST_Template_Loader::addPath(__DIR__ . '/templates');
```

**Escaping is the template author's job.** The loader hands you data; it does not escape it.

## Choosing the output call

| You want | Use |
|---|---|
| A route to render a page and finish | `NTDST_Template_Loader::page($tpl, $data)` |
| To read that data inside the template | `ntdst_page_data()` |
| Render to a **string** (email body, AJAX HTML fragment) | the response object's string-returning render |
| Output JSON and exit | the response object's JSON call |
| A 404 | `ntdst_response()->notFound()` |
| A redirect | the response redirect (safe/same-host by default; external is an explicit opt-in) |

`ob_start()` + `include` is the pattern all of this replaces — and it is gated.

**`render()` exits the request.** That is correct for a route, and a live bug inside an admin
callback: calling it in a dashboard widget or a settings-page renderer kills every panel after yours.
In an admin render callback, `include` the template directly — that is the documented exception, and
the drift it is distinguished from is `ob_start()` + `include` used to *capture into a string* (use
the string-returning render for that). See `ntdst-patterns`' `golden-paths/admin-settings-page.md`.

## Wiring, enabling, configuring

Bootstrap must be able to reach the class: list it under `services` in `plugin-config.php`
(mu-plugin) or `config/theme-config.php` (theme), **or** place it as `*Service.php` at a
discovery-path root or in an enabled sector directory. Those two locations are the only ones
discovery scans — a namespaced class anywhere else must be listed explicitly or it silently never
loads.

```php
// Slug comes from the CLASS NAME: BookingService -> `booking`. The derivation
// collapses acronyms (AdminUIService -> `admin_ui`) and strips EVERY occurrence
// of "Service" (ServiceService -> ''). Renaming metadata()['name'] does NOT
// rename any of these — the slug cache is warmed from the class name first.
add_filter('ntdst_service_booking_enabled', '__return_false');  // runtime off
update_option('ntdst_service_booking', '0');                    // UI / DB off

// Config override, from the bootstrap config array:
'services' => [
    'overrides' => [
        'booking' => ['hold_minutes' => 30],
    ],
],
```

Precedence, most restrictive first: **metadata (code) → filter (runtime) → DB option (UI)**.

## Admin-only work

Gate at **runtime**, at the top of `init()`:

```php
private function init(): void
{
    if (!is_admin()) {
        return;
    }
    add_action('admin_menu', [$this, 'registerPage']);
}
```

Not with an `admin_only` metadata flag — that gates *bootstrap*, so the class is never instantiated
outside admin and no frontend caller, AJAX action or CLI command can ever reach it.

## The shape rules this slice encodes

- **`init()` is called from the constructor.** There is no `register()` method the framework calls.
- **Dependencies are type-hinted constructor parameters**, autowired. `ntdst_get(Foo::class)` belongs
  at a composition root or in a template, not inside a class that could have injected it.
- **A sub-component is a plain class**, instantiated by its owner. It gets no interface, no
  `metadata()`, and no config entry. Promote it to a service only when you would want a config-level
  toggle for it on its own.
- **Services orchestrate; they don't compute.** A method that sanitizes, validates, runs business
  logic and formats a response is four responsibilities — split the WP boundary (handler) from the
  pure logic (a WP-free, testable class).
- **Return `WP_Error` on failure**, and check `is_wp_error()` at every call site. A swallowed error is
  invisible data loss.
- **Priority bands:** 1–5 critical infrastructure, 6–9 core framework and data models, 10–14 standard
  features, 15–19 content, 20–29 UI, 30+ optional.
