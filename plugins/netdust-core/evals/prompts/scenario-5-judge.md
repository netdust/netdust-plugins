You are scoring an eval. Two PHP code outputs were produced by different agents for the same prompt — one baseline (no harness skills), one with the netdust-wp/netdust-core harness skills available. Your job: for each rule in the list, judge which outputs covered it.

**The prompt that was given to both agents:**

---
You're working on Stride. Set up a new `Notifications` module that:

1. Registers a new custom post type `stride_notification` (statuses: `unread`, `read`, `archived` — use post_status). Title required, content optional. Author = the user being notified.
2. Exposes a top-level `NotificationService` (public API: `notifyUser(int $user_id, string $message): WP_Post|WP_Error`).
3. Owns an internal `NotificationDispatcher` (handles the actual delivery — email, web push later). This is NOT a top-level service — it's an internal implementation detail of NotificationService and shouldn't be discoverable on its own.
4. Wires the module into stride-core's bootstrap.

Write all the files (file path + content for each). Mention where each file lives in the project tree.
---

**Output A (baseline — no harness skills loaded):**

---
# Stride Notifications Module

## File Tree

```
web/app/mu-plugins/stride-core/src/Modules/Notifications/
├── NotificationsModule.php
├── NotificationService.php
├── PostType/NotificationPostType.php
└── Internal/NotificationDispatcher.php
```

---

### `NotificationsModule.php`

```php
<?php
declare(strict_types=1);

namespace Stride\Core\Modules\Notifications;

use Stride\Core\Modules\Notifications\Internal\NotificationDispatcher;
use Stride\Core\Modules\Notifications\PostType\NotificationPostType;

final class NotificationsModule
{
    public function register(): void
    {
        $dispatcher = new NotificationDispatcher();
        $service    = new NotificationService($dispatcher);

        // Expose only the public service in the container.
        stride_core()->container()->singleton(
            NotificationService::class,
            static fn () => $service
        );

        (new NotificationPostType())->register();
    }
}
```

### `PostType/NotificationPostType.php`

```php
<?php
declare(strict_types=1);

namespace Stride\Core\Modules\Notifications\PostType;

final class NotificationPostType
{
    public const POST_TYPE = 'stride_notification';

    public function register(): void
    {
        add_action('init', [$this, 'registerPostType']);
        add_action('init', [$this, 'registerStatuses']);
    }

    public function registerPostType(): void
    {
        register_post_type(self::POST_TYPE, [
            'label'        => __('Notifications', 'stride'),
            'public'       => false,
            'show_ui'      => false,
            'show_in_rest' => false,
            'supports'     => ['title', 'editor', 'author'],
            'capability_type' => 'post',
        ]);
    }

    public function registerStatuses(): void
    {
        foreach (['unread', 'read', 'archived'] as $status) {
            register_post_status($status, [
                'label'                     => ucfirst($status),
                'public'                    => false,
                'internal'                  => true,
                'exclude_from_search'       => true,
                'show_in_admin_all_list'    => false,
                'show_in_admin_status_list' => false,
            ]);
        }
    }
}
```

### `Internal/NotificationDispatcher.php`

```php
<?php
declare(strict_types=1);

namespace Stride\Core\Modules\Notifications\Internal;

use WP_Post;

/**
 * Internal — do not depend on directly. Use NotificationService.
 *
 * @internal
 */
final class NotificationDispatcher
{
    public function dispatch(WP_Post $notification): void
    {
        $user = get_userdata((int) $notification->post_author);
        if (! $user) {
            return;
        }

        wp_mail(
            $user->user_email,
            (string) $notification->post_title,
            (string) $notification->post_content
        );

        // Web push hook for later implementation.
        do_action('stride/notifications/dispatched', $notification, $user);
    }
}
```

### `NotificationService.php`

```php
<?php
declare(strict_types=1);

namespace Stride\Core\Modules\Notifications;

use Stride\Core\Modules\Notifications\Internal\NotificationDispatcher;
use Stride\Core\Modules\Notifications\PostType\NotificationPostType;
use WP_Error;
use WP_Post;

final readonly class NotificationService
{
    public function __construct(
        private NotificationDispatcher $dispatcher,
    ) {}

    public function notifyUser(int $user_id, string $message): WP_Post|WP_Error
    {
        if ($user_id <= 0 || ! get_userdata($user_id)) {
            return new WP_Error('stride_notify_invalid_user', __('Invalid user.', 'stride'));
        }

        $message = trim($message);
        if ($message === '') {
            return new WP_Error('stride_notify_empty', __('Message required.', 'stride'));
        }

        $title = wp_trim_words($message, 12, '…');

        $id = wp_insert_post([
            'post_type'    => NotificationPostType::POST_TYPE,
            'post_status'  => 'unread',
            'post_author'  => $user_id,
            'post_title'   => wp_strip_all_tags($title),
            'post_content' => $message,
        ], true);

        if (is_wp_error($id)) {
            return $id;
        }

        $post = get_post($id);
        if (! $post instanceof WP_Post) {
            return new WP_Error('stride_notify_fetch_failed', __('Created but not retrievable.', 'stride'));
        }

        $this->dispatcher->dispatch($post);

        return $post;
    }
}
```

### Bootstrap wiring

In `web/app/mu-plugins/stride-core/src/Plugin.php` (or wherever modules are registered):

```php
use Stride\Core\Modules\Notifications\NotificationsModule;

// In the module-registration section:
(new NotificationsModule())->register();
```

---

**Notes**
- `NotificationDispatcher` lives under `Internal\` and is marked `@internal`; only `NotificationService` is bound in the container, so it's not auto-discoverable.
- `readonly` service + constructor-injected dispatcher keeps it testable (swap dispatcher in unit tests).
- All failure paths return `WP_Error`; happy path returns `WP_Post`.

---

**Output B (skill-on — harness skills available):**

---
Existing service uses audit-log-derived notifications (no CPT). The task asks for a CPT-backed notification system — different design. I'll write the new module under a parallel namespace `Stride\Modules\Notifications` (plural) to avoid colliding with the existing `Notification` singular module. Here's the implementation.

---

**1. `web/app/mu-plugins/stride-core/Modules/Notifications/NotificationsCPT.php`**

```php
<?php
declare(strict_types=1);

namespace Stride\Modules\Notifications;

/**
 * Registers the stride_notification CPT + custom post statuses via ntdst_data().
 * Sub-component of NotificationService — not a top-level service.
 */
final class NotificationsCPT
{
    public const POST_TYPE = 'stride_notification';
    public const STATUS_UNREAD   = 'unread';
    public const STATUS_READ     = 'read';
    public const STATUS_ARCHIVED = 'archived';

    public function register(): void
    {
        ntdst_data()->register(self::POST_TYPE, [
            'labels'   => ['name' => __('Notifications', 'stride')],
            'public'   => false,
            'show_ui'  => true,
            'supports' => ['title', 'editor', 'author'],
            'fields'   => [], // title required (core), content optional (core)
        ]);

        foreach ([self::STATUS_UNREAD, self::STATUS_READ, self::STATUS_ARCHIVED] as $status) {
            register_post_status($status, [
                'label'                     => ucfirst($status),
                'public'                    => false,
                'internal'                  => false,
                'show_in_admin_status_list' => true,
            ]);
        }
    }
}
```

**2. `web/app/mu-plugins/stride-core/Modules/Notifications/NotificationDispatcher.php`** — internal, NOT a service.

```php
<?php
declare(strict_types=1);

namespace Stride\Modules\Notifications;

use WP_Post;

/**
 * Internal delivery component. Owned by NotificationService.
 * Not registered in plugin-config.php; not resolvable via ntdst_get().
 */
final class NotificationDispatcher
{
    public function dispatch(WP_Post $notification, int $user_id): void
    {
        do_action('stride/notifications/dispatch', $notification, $user_id);
        // Email/web-push wired here later (via ntdst_mail()).
    }
}
```

**3. `web/app/mu-plugins/stride-core/Modules/Notifications/NotificationService.php`**

```php
<?php
declare(strict_types=1);

namespace Stride\Modules\Notifications;

use WP_Error;
use WP_Post;

final class NotificationService implements \NTDST_Service_Meta
{
    private NotificationDispatcher $dispatcher;

    public static function metadata(): array
    {
        return [
            'name'        => 'Notifications Service',
            'description' => 'CPT-backed user notifications',
            'priority'    => 20,
        ];
    }

    public function __construct(private readonly NotificationsCPT $cpt)
    {
        $this->dispatcher = new NotificationDispatcher(); // internal, hidden from DI
        $this->init();
    }

    private function init(): void
    {
        add_action('init', [$this->cpt, 'register']);
    }

    public function notifyUser(int $user_id, string $message): WP_Post|WP_Error
    {
        if ($user_id <= 0 || !get_userdata($user_id)) {
            return new WP_Error('invalid_user', __('Invalid user.', 'stride'));
        }
        $title = wp_trim_words(wp_strip_all_tags($message), 12, '…');
        if ($title === '') {
            return new WP_Error('empty_title', __('Title required.', 'stride'));
        }

        $id = wp_insert_post([
            'post_type'    => NotificationsCPT::POST_TYPE,
            'post_status'  => NotificationsCPT::STATUS_UNREAD,
            'post_title'   => $title,
            'post_content' => $message,
            'post_author'  => $user_id,
        ], true);

        if (is_wp_error($id)) return $id;

        $post = get_post($id);
        if (!$post instanceof WP_Post) {
            return new WP_Error('not_found', __('Failed to load notification.', 'stride'));
        }
        $this->dispatcher->dispatch($post, $user_id);
        return $post;
    }
}
```

**4. Wire into `web/app/mu-plugins/stride-core/plugin-config.php`** — add to `services`:

```php
\Stride\Modules\Notifications\NotificationService::class,
```

`NotificationsCPT` is autowired into the service constructor by the container; `NotificationDispatcher` is `new`'d internally so it stays an implementation detail (not in `services`, not resolved via `ntdst_get`).

---

**Rules to score** (each from `~/Sites/netdust-wp-manager/tasks/eval-rubric.md` — read that file for full definitions; brief reminders below):

- **E1** (canonical): Modules live at `mu-plugins/{project}-core/Modules/<Name>/`. Folder structure NOT fixed — modules organize by concern
- **E3** (canonical): Services listed in `plugin-config.php`'s `'services'` array; NTDST Bootstrap auto-instantiates + resolves constructor DI
- **E4** (canonical): CPT registration lives in dedicated `*CPT` class (e.g., `EditionCPT`), called from owning service's `init()`. Class exposes `POST_TYPE` constant. **Registration MUST use `ntdst_data()->register()`, NOT raw `register_post_type()`.**
- **A1** (canonical): Implements `NTDST_Service_Meta` (directly or via `AbstractService`)
- **A2** (canonical): Static `metadata()` returning `{name, description, priority, admin_only?, enabled?}`
- **A3** (canonical): Hooks registered ONLY in `init()` or a provider's `boot()` — never in `__construct()`
- **A4** (canonical): Constructor DI uses `readonly` properties (PHP 8.1+)
- **A6** (canonical): Sub-services owned by parent registered as singletons inside parent's `init()` via `ntdst_set()`
- **A7** (canonical): Admin controllers NOT registered as Services. Instantiated with `new` inside owning service's `init()`
- **A11** (canonical): Priority convention: `<10 = critical/early`, `10–15 = standard`, `20+ = late`
- **X1** (canonical): PHP 8.1+ features throughout: readonly properties, enums, typed properties, named arguments where useful
- **X2** (canonical): No `add_action`/`add_filter` outside `init()` / `boot()` lifecycle methods
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
- **EX1** (canonical): `declare(strict_types=1);` as first line of every PHP file

---

**Scoring protocol:**

For EACH rule above, output ONE line in this exact format (machine-parsed):

```
RULE_ID: <coverage> | <evidence>
```

Where `<coverage>` is one of:
- `both` — both outputs satisfy the rule
- `baseline_only` — only baseline satisfies
- `skill_only` — only skill-on satisfies
- `neither` — neither satisfies (rule not applicable OR both failed)
- `na` — rule is not exercisable by this scenario (the rule list may be over-inclusive; flag and skip)

And `<evidence>` is ≤25 words explaining your judgment, citing concrete code patterns ("uses `$wpdb->prepare` with %d placeholder", "missing nonce check", "registers via add_filter not WP_CLI::add_command", etc.).

**Be strict.** "The agent could have done X" is not coverage. The code on the page either does X or it doesn't. Code that says `// TODO: add nonce check` is not coverage.

**Be honest about NEGATIVE rules.** Some rule notes say "anti-pattern to detect" — if the output produces the anti-pattern, that's a fail (not coverage). E.g., if D4 says "dry-run is the default" and the output uses `--dry-run` opt-in (writes by default), that's `neither`, not `both`.

After scoring all rules, end with EXACTLY this one-line summary (don't change the format — it gets parsed):

```
SUMMARY: scenario_id=5 baseline_covered=N skill_covered=N skill_delta=N
```

Where N is the count, and `skill_delta` = number of rules where coverage is `skill_only` (NOT `baseline_only` and NOT `both`).

Don't add prose before or after the scoring lines and summary. The output will be parsed by a script.
