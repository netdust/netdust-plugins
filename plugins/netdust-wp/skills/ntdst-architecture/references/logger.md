# NTDST Logger

PSR-3 inspired logging with batched writes and (optionally) database persistence.

**Location:** `app/content/mu-plugins/ntdst-core/services/Logger.php`

## Global Helpers

All four helpers are wrapped in `function_exists()` guards so they tolerate double-load when multiple plugins ship a copy of ntdst-core.

```php
ntdst_log()                      // Get Logger instance (default channel)
ntdst_log('payments')            // Get Logger for named channel
ntdst_log_debug($msg, $ctx)      // Quick debug
ntdst_log_info($msg, $ctx)       // Quick info
ntdst_log_error($msg, $ctx)      // Quick error
```

## Usage

```php
ntdst_log()->debug('Processing started', ['batch' => 42]);
ntdst_log()->info('User logged in', ['user_id' => 123]);
ntdst_log()->warning('Rate limit approaching');
ntdst_log()->error('Payment failed', ['order_id' => 456]);
ntdst_log()->critical('Database connection lost');

// Named channel
ntdst_log('payments')->error('Charge declined', ['amount' => 50.00]);

// Message interpolation
ntdst_log()->info('User {user_id} placed order {order_id}', [
    'user_id' => 123,
    'order_id' => 456,
]);
```

## Behavior

| Level | Min Environment | Persistence |
|-------|----------------|-------------|
| DEBUG | WP_DEBUG only | File (batched) |
| INFO | WP_DEBUG only | File (batched) |
| WARNING | Production | File (batched) |
| ERROR | Production | File (immediate) + `error_log()` + DB (opt-in) |
| CRITICAL | Production | File (immediate) + `error_log()` + DB (opt-in) |

- **File handler**: batched writes flushed on shutdown via `register_shutdown_function`. ERROR+ entries bypass batching for immediate visibility. Uses `file_put_contents(..., FILE_APPEND | LOCK_EX)` for concurrent-write safety on both paths. Files land at `wp-content/logs/{channel}-{date}.log`.
- **Error log handler**: ERROR+ → PHP `error_log()`.
- **Database handler**: ERROR+ → `log_entry` custom post type via Data.php. **Opt-in** (see below).

### Handler exceptions

Handler errors are caught as `\Throwable` (not just `Exception`) and logged via PHP's raw `error_log()` to avoid recursion. Custom handlers that throw `TypeError` or `Error` subclasses won't crash the surrounding request.

## Database handler is opt-in

Every error written to the DB triggers `wp_insert_post` + N `update_post_meta` calls + the `save_post` action cascade. That is exactly the wrong load profile during an incident — production errors should not generate write storms. The DB handler is now registered **only when** `apply_filters('ntdst_log_database_enabled', WP_DEBUG)` returns true.

```php
// Default: on under WP_DEBUG, off in production.

// Force on (e.g. observability stack reads from log_entry):
add_filter('ntdst_log_database_enabled', '__return_true');

// Force off, even in debug:
add_filter('ntdst_log_database_enabled', '__return_false');
```

Without the DB handler, ERROR+ entries still hit the file log and PHP's `error_log()` — they don't disappear.

## Log directory protection

The logger drops both `.htaccess` (Apache `Deny from all`) and an empty `index.html` into `wp-content/logs/` on the first write. On Bedrock, `wp-content` is `web/app/` — **inside the webroot**, which means logs are publicly addressable unless server config blocks them.

> **Production caveat:** `.htaccess` is inert on Nginx. Ploi / Combell / any Nginx host MUST add a `location ~ /logs { deny all; }` (or equivalent) to the server config. The `.htaccess` + `index.html` files are defense-in-depth on Apache only.

## Database Queries

```php
// Recent logs from DB (errors+ only)
$logs = ntdst_log()->recent(50, NTDST_Logger::ERROR);

// Clean old logs
ntdst_log()->clearOld(30); // delete logs older than 30 days
```

These methods require the DB handler to be enabled (otherwise the `log_entry` post type is empty).

## Custom Handler

```php
ntdst_log()->addHandler('slack', function($level, $message, $context) {
    if ($level >= NTDST_Logger::CRITICAL) {
        // send to Slack webhook
    }
});
```

Custom handlers can throw — failures are caught as `\Throwable` and won't propagate to the calling code.

## In Services

```php
class PaymentService implements NTDST_Service_Meta
{
    public function __construct(
        private readonly NTDST_Logger $logger, // auto-injected
    ) {
        $this->init();
    }

    public function charge(int $amount): bool
    {
        $this->logger->info('Charging {amount}', ['amount' => $amount]);

        try {
            // ... payment logic
            $this->logger->info('Payment succeeded');
            return true;
        } catch (\Throwable $e) {
            $this->logger->error('Payment failed', [
                'amount' => $amount,
                'error'  => $e->getMessage(),
            ]);
            return false;
        }
    }
}
```

## Conventions

- Filter `netdust_trusted_proxies` is historical — keep it for compatibility, but don't propagate the `netdust_*` prefix to new filters. Use `ntdst_*` instead.
- Never log raw user-submitted values that may contain PII (email addresses, names, content). Log identifiers + structural metadata only — example: `ntdst_log('intake')->error('JSON decode failed', ['post_id' => 42])` rather than including the failing payload.
