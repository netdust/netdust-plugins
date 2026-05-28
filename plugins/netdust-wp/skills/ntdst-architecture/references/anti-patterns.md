# NTDST Anti-Patterns

Common mistakes to avoid when working with the NTDST framework.

## Critical Anti-Patterns

### Raw SQL in Application Code

```php
// WRONG
global $wpdb;
$wpdb->query("UPDATE {$wpdb->postmeta} SET meta_value = 'x' WHERE post_id = $id");

// CORRECT
$model = ntdst_data()->get('my_type');
$model->update($id, ['field' => 'x']);
```

### Direct Meta Access in Services

```php
// WRONG - bypasses ORM validation
get_post_meta($id, 'field', true);
update_post_meta($id, 'field', $value);
delete_post_meta($id, 'field');

// CORRECT - use Data Manager
$model = ntdst_data()->get('my_type');
$model->getMeta($id, 'field');
$model->update($id, ['field' => $value]);
```

### Treating find() as Array

```php
// WRONG - find() returns WP_Post object
$post = $model->find($id);
$title = $post['title'];  // ERROR!

// CORRECT - use object properties
$post = $model->find($id);
$title = $post->post_title;

// OR use get() for array format
$posts = $model->where('id', $id)->get();
$title = $posts[0]['title'];
```

### Returning false/null on Error

```php
// WRONG
if (!$valid) return false;
if (!$found) return null;
if ($error) return [];

// CORRECT
if (!$valid) return new WP_Error('invalid', 'Validation failed');
if (!$found) return new WP_Error('not_found', 'Not found');
if ($error) return new WP_Error('error', $error->getMessage());
```

### Direct wp_mail() Calls

```php
// WRONG
wp_mail($to, $subject, $message);

// CORRECT
ntdst_mail()
    ->to($to)
    ->subject($subject)
    ->template('template-name', $data)
    ->send();
```

### Manual fetch() in JavaScript

```javascript
// WRONG
fetch('/wp-json/ntdst/v1/action', {
    method: 'POST',
    body: JSON.stringify({ action: 'my_action', ...params })
});

// CORRECT
await ntdstAPI.call('my_action', params);
```

### Custom YOOtheme ObjectTypes

```php
// WRONG - breaks Dynamic Content dropdown
$source->objectType('MyCustomType', [
    'fields' => [...]
]);

// CORRECT - use existing auto-registered types
$source->queryType([
    'fields' => [
        'myQuery' => [
            'type' => ['listOf' => 'Artwork'],  // Existing type
            // ...
        ],
    ],
]);
```

### __NAMESPACE__ in YOOtheme Resolvers

```php
// WRONG - serialization fails
'func' => __NAMESPACE__ . '\\my_resolver',

// CORRECT - explicit string
'func' => 'ntdstheme\\services\\yootheme\\my_resolver',
```

### Wrong Config File Name

```
// WRONG - conflicts with YOOtheme
ntdstheme/config.php

// CORRECT (theme)
ntdstheme/theme-config.php

// CORRECT (mu-plugin — Stride, vad, etc.)
mu-plugins/<project>-core/plugin-config.php
```

Use `plugin-config.php` when the bootstrap is in a mu-plugin (`<project>-core`), `theme-config.php` when it's in a theme. Don't invent a different name.

## Performance Anti-Patterns

### N+1 Query Pattern

```php
// WRONG - N+1 queries
foreach ($posts as $post) {
    $meta = get_post_meta($post->ID, 'field', true);
}

// CORRECT - prime cache first
$post_ids = wp_list_pluck($posts, 'ID');
update_postmeta_cache($post_ids);

foreach ($posts as $post) {
    $meta = get_post_meta($post->ID, 'field', true);  // Now cached
}
```

### Unbounded Queries

```php
// WRONG - could return thousands
$posts = get_posts(['posts_per_page' => -1]);

// CORRECT - set reasonable limit
$posts = get_posts(['posts_per_page' => 100]);

// Or paginate
$model->paginate($page, $per_page);
```

### Random Order Without Limit

```php
// WRONG - sorts entire table
$posts = get_posts(['orderby' => 'rand']);

// CORRECT - limit first
$posts = get_posts([
    'orderby' => 'rand',
    'posts_per_page' => 10,
]);
```

## Security Anti-Patterns

### Unsanitized Input

```php
// WRONG
$id = $_POST['id'];
$title = $params['title'];

// CORRECT
$id = absint($_POST['id'] ?? 0);
$title = sanitize_text_field($params['title'] ?? '');
$email = sanitize_email($params['email'] ?? '');
$content = wp_kses_post($params['content'] ?? '');
```

### Missing Capability Checks

```php
// WRONG - anyone can call
add_filter('ntdst/api_data/delete', function ($data, $params) {
    $model->delete($params['id']);
});

// CORRECT - check permissions
add_filter('ntdst/api_data/delete', function ($data, $params) {
    $id = absint($params['id']);

    if (!current_user_can('delete_post', $id)) {
        return new WP_Error('forbidden', 'Permission denied');
    }

    return $model->delete($id);
});
```

### Unescaped Output

```php
// WRONG - XSS vulnerability
echo $user_input;
echo $post->post_title;

// CORRECT
echo esc_html($user_input);
echo esc_html($post->post_title);
echo esc_url($url);
echo esc_attr($attribute);
```

## Service Anti-Patterns

### Making Every Class a Service

```php
// WRONG - pure dependency with no hooks, no config, no lifecycle need
class ConversationStore implements NTDST_Service_Meta {
    public static function metadata(): array {
        return ['name' => 'Conversation Store', 'priority' => 15];
    }
    public function get(int $userId): array { /* ... */ }
}

class ToolExecutor implements NTDST_Service_Meta {
    public static function metadata(): array {
        return ['name' => 'Tool Executor', 'priority' => 20];
    }
    public function __construct(
        private readonly ClaudeClientInterface $client,
        private readonly ConversationStore $store,
    ) {} // No init(), no hooks — just a dependency
}

// These get eagerly instantiated on EVERY admin page load
// even when the assistant page is never visited.

// CORRECT - only classes with WordPress hooks are services
class ChatController implements NTDST_Service_Meta {
    public static function metadata(): array {
        return ['name' => 'Chat Controller', 'priority' => 16];
    }
    public function __construct(
        private readonly ToolExecutor $executor,  // autowired lazily
        private readonly ConversationStore $store, // autowired lazily
    ) { $this->init(); }

    private function init(): void {
        add_action('rest_api_init', [$this, 'registerRoutes']); // THIS is why it's a service
    }
}

// Plain classes — no interface, no metadata, resolved via DI autowiring
class ConversationStore { /* ... */ }
class ToolExecutor { /* ... */ }
```

**The test:** Does this class call `add_action()`, `add_filter()`, or `add_shortcode()` in its constructor/init? If no → it's not a service.

### Fat Service (Hooks + Business Logic Mixed)

```php
// WRONG - service does everything: hooks, validation, business logic, formatting
class EnrollmentService implements NTDST_Service_Meta {
    public function __construct() { $this->init(); }

    private function init(): void {
        add_action('wp_ajax_enroll', [$this, 'handleEnrollment']);
    }

    public function handleEnrollment(): void {
        // Nonce check, sanitization, capacity check, price calculation,
        // voucher validation, registration creation, email sending...
        // 80+ lines of mixed concerns
    }
}

// CORRECT - split into handler (thin) + service (orchestrator) + business class (logic)
// Handler: catches WP event, validates input, delegates
class EnrollmentHandler {
    public function ajaxEnroll(): void {
        if (!wp_verify_nonce($_POST['nonce'] ?? '', 'enroll')) {
            wp_send_json_error(['message' => 'Invalid token']);
        }
        $result = ntdst_get(EnrollmentService::class)->enroll(
            get_current_user_id(),
            absint($_POST['edition_id'] ?? 0)
        );
        is_wp_error($result) ? wp_send_json_error($result) : wp_send_json_success($result);
    }
}

// Service: orchestrates, has lifecycle hooks, no raw logic
class EnrollmentService implements NTDST_Service_Meta {
    public function __construct(
        private readonly RegistrationRepository $repo,
        private readonly PriceCalculator $calculator,
    ) { $this->init(); }
}

// Business class: pure domain logic, testable without WP
class PriceCalculator {
    public function calculate(int $base, ?string $voucher): int { /* pure math */ }
}
```

### Missing NTDST_Service_Meta Interface

```php
// WRONG - won't be discovered
class MyService {
    // ...
}

// CORRECT
class MyService implements NTDST_Service_Meta {
    public static function metadata(): array {
        return [
            'name' => 'My Service',
            'description' => 'What it does',
            'priority' => 10,
        ];
    }
}
```

### Wrong Priority

```php
// WRONG - UI feature at infrastructure priority
'priority' => 3,  // For a transitions service

// CORRECT
'priority' => 22,  // UI enhancements are 20+
```

### Initialization Outside Constructor

```php
// WRONG
class MyService implements NTDST_Service_Meta {
    public function register(): void {
        add_action('init', [$this, 'setup']);
    }
}

// CORRECT
class MyService implements NTDST_Service_Meta {
    public function __construct() {
        $this->init();
    }

    private function init(): void {
        add_action('init', [$this, 'setup']);
    }
}
```

### Missing Config Filter

```php
// WRONG - can't be customized
private function getConfig(): array {
    return ['option' => 'value'];
}

// CORRECT — use the project's own prefix, not 'netdust_'
private function getDefaultConfig(): array {
    // {project} = the project slug (e.g. stride_myservice_config, vad_myservice_config).
    return apply_filters('{project}_myservice_config', [
        'option' => 'value',
    ]);
}
```

### Pure Pass-Through Method (Service → Repository)

A service method that is literally `return $this->repository->X(...)` and nothing else is not a layer — it's drift surface. Callers will split between "go via service" and "go via repo", and the codebase will drift between the two paths over time.

```php
// WRONG - pure forwards add no value, multiply call paths
class EditionService {
    public function getEdition(int $id): WP_Post|WP_Error {
        return $this->repository->find($id);
    }
    public function getEditionsForCourse(int $courseId): array {
        return $this->repository->findByCourse($courseId);
    }
    public function getUpcomingEditions(int $limit = 10): array {
        return $this->repository->findUpcoming($limit);
    }
}

// CORRECT - service only owns business logic + typed/composed reads
class EditionService {
    // Typed/coerced read — enum coercion adds value
    public function getStatus(int $id): OfferingStatus {
        $value = $this->repository->getField($id, 'status', 'open');
        return OfferingStatus::tryFrom($value) ?? OfferingStatus::Open;
    }

    // Composite business decision — multi-source, real logic
    public function canEnroll(int $id): bool {
        return $this->getStatus($id)->allowsEnrollment()
            && $this->hasAvailableSpots($id)
            && !$this->isPast($id);
    }
}

// Callers go to the repository directly for plain reads:
$edition = $repository->find($id);  // NOT $service->getEdition($id)
```

**The test:** Open the method body. If it's `return $this->X->Y(...)` and nothing else — delete it.

**What's NOT a pass-through** (keep these):
- Typed/coerced reads: enum coercion, null-coercion, default fallbacks
- Composite reads: multi-source, derived values, cross-domain lookups
- Event firers: `createX()` that wraps repo + `do_action('domain/x/created', ...)`
- Business decisions: composite boolean checks across multiple inputs
- Cached reads with service-specific invalidation logic

**Naming alone is not justification.** "`getEdition` reads nicer than `find`" doesn't save the wrapper. **Forward-compat is not justification.** "We might add logic later" → add it WHEN you need it.

### CPT Data Access Outside the Repository

`ntdst_data()->get('post_type')` should appear in exactly one place: the corresponding repository. Every other file goes through the repository. This is the single-mediator rule.

```php
// WRONG - direct ntdst_data() from a service / handler / shortcode
class EnrollmentCompletion {
    public function someMethod(int $editionId): void {
        $startDate = ntdst_data()->get('vad_edition')->getMeta($editionId, 'start_date');
        // ...
    }
}

// WRONG - bypassing the repo to do "just one quick read"
function my_template_func(int $editionId): array {
    $model = ntdst_data()->get('vad_edition');
    return $model->where('status', 'open')->withMeta()->get();
}

// CORRECT - inject the repository, use its methods
class EnrollmentCompletion {
    public function __construct(
        private readonly EditionRepository $editions,
    ) {}

    public function someMethod(int $editionId): void {
        $startDate = $this->editions->getField($editionId, 'start_date');
        // ...
    }
}

// CORRECT - theme files use ntdst_get() to resolve the repo
$editions = ntdst_get(EditionRepository::class);
$open = $editions->findWithAvailability();
```

**Why this matters:**
- The repo centralizes caching, validation, audit hooks per domain
- Mocks become trivial — mock the repo, not `ntdst_data()`
- Code review has a single handle: "does this need a repo method?"
- Domain-typed returns possible later (value objects vs raw arrays)

**`AbstractRepository` already provides** `find`, `create`, `update`, `delete`, `all`, `count`, `getField`, `findFields`, `getMetaPrefix`. Don't reach for `ntdst_data()` if one of those fits.

**Documented exception — prefix-aware batch reads:** when reading batch-loaded meta (`getPostsFast()` / `withMeta()` envelope), the meta arrives with raw prefixed keys (`_ntdst_*`). Use `$this->repository->getMetaPrefix()` to read the prefix; never hardcode `_ntdst_` as a string. Acceptable in perf-critical paths (catalog pages, exports). See `data-orm.md`.

### Wrong Data API Vocabulary

The Data API has its own friendly key vocabulary. Passing raw `wp_posts` column names silently drops the value (and may misclassify it as meta).

```php
// WRONG - 'post_title' gets dropped from post-table extraction
$repository->create([
    'post_title'   => 'My Session',    // ❌ dropped — may write _ntdst_post_title meta
    'post_content' => 'Description',   // ❌ dropped
    'date'         => '2026-06-01',
]);

// CORRECT - friendly keys
$repository->create([
    'title'   => 'My Session',
    'content' => 'Description',
    'date'    => '2026-06-01',
]);
```

| Pass this | NOT this |
|---|---|
| `title` | ~~`post_title`~~ |
| `content` | ~~`post_content`~~ |
| `excerpt` | ~~`post_excerpt`~~ |

The full list (16 accepted keys) lives at `NTDST_Data_Model::WP_COLUMNS`. `post_status`, `post_author`, `post_parent`, `post_date`, `post_name`, `menu_order` etc. pass through unchanged.

**Safety net:** the framework now logs unregistered keys via `ntdst_log('data')->warning()` and drops them. Watch `logs/data-YYYY-MM-DD.log` after refactors. Zero warnings = clean.

**Fingerprint of this bug:** `_ntdst_post_*` keys in DB meta indicates a writer somewhere passing the wrong vocabulary.

## Response & Routing Anti-Patterns

### Echo in Services

```php
// WRONG - services should never output directly
echo '<div>' . $data . '</div>';
echo json_encode($result);

// CORRECT - use Response
ntdst_response()->with('data', $data)->render('partials/block');
ntdst_response()->with('result', $result)->json();
```

### Manual template_include

```php
// WRONG - bypasses Router
add_filter('template_include', function($template) {
    if (is_singular('portfolio')) {
        return __DIR__ . '/templates/portfolio.php';
    }
    return $template;
});

// CORRECT - use Router
ntdst_router()->single('portfolio', function($post) {
    return ntdst_response()
        ->with('project', $post)
        ->template('portfolio/single');
});
```

### Global $post in Services

```php
// WRONG - relies on global state
global $post;
$title = $post->post_title;

// CORRECT - pass data as parameters
public function formatProject(WP_Post $post): array
{
    return ['title' => $post->post_title];
}
```
