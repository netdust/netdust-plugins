# Theme API Reference

## `NTDST_Theme`

Instantiated once in `functions.php`. Provides fluent API wrapping ntdst-core services.

### Built-in Mixins

Wired in constructor — access via `$theme->`:

```php
$theme->data()      // → ntdst_data()      NTDST_Data_Manager
$theme->router()    // → ntdst_router()    NTDST_Router
$theme->response()  // → ntdst_response()  NTDST_Response
$theme->log()       // → ntdst_log()       NTDST_Logger
$theme->mail()      // → ntdst_mail()      NTDST_Mailer
```

### Data Models

```php
$theme->register('project', [
    'label'  => 'Projects',
    'public' => true,
    'fields' => ['client' => 'text', 'year' => 'integer'],
]);

$theme->taxonomy('project_type', 'project', [
    'label'        => 'Project Types',
    'hierarchical' => true,
]);
```

### Template Routing

```php
$theme->single('project', function($post) {
    return ntdst_response()->with('project', $post)->template('project/single');
});

$theme->archive('project', function() {
    return ntdst_response()
        ->with('projects', ntdst_data()->get('project')->all())
        ->template('project/archive');
});

$theme->page('about', function($post) {
    return get_template_directory() . '/templates/about.php';
});
```

### API Actions

```php
// Public action
$theme->apiAction('get_portfolio', function($data, $params) {
    $category = sanitize_text_field($params['category'] ?? '');
    return ['posts' => ntdst_data()->get('project')
        ->where('category', $category)->get()];
});

// Protected action (requires capability)
$theme->apiAction('save_project', function($data, $params) {
    // save logic
}, ['capability' => 'edit_posts']);
```

### Module Configuration

```php
// Runtime config override
$theme->module('barba')->config(function($config) {
    $config['animationDuration'] = 400;
    return $config;
});

// Enable/disable
$theme->module('barba')->disable();
$theme->module('schema')->enable();

// Lifecycle hooks
$theme->module('analytics')->before(function() { /* ... */ });
$theme->module('analytics')->after(function() { /* ... */ });

// Direct method call on service
$theme->module('analytics')->track('page_view');
```

### Conditional Config

```php
$theme->when(fn() => is_front_page(), function($theme) {
    $theme->module('barba')->config(fn($c) => array_merge($c, [
        'animationDuration' => 400,
    ]));
});
```

### WordPress Hooks (Fluent)

```php
$theme->on('wp_footer', function() { echo '<div>Footer</div>'; });
$theme->filter('body_class', function($classes) {
    $classes[] = 'custom';
    return $classes;
});
```

### Custom Mixin

```php
// Instance proxy
$theme->mixin('stripe', new StripeClient());
$theme->stripe()->charge(1000);

// Method injection (copies public methods)
$theme->mixin(new ThemeHelpers());
$theme->formatDate('2024-01-01');
```

### Template Paths

```php
$theme->templatePath(__DIR__ . '/custom-templates');
```

### Asset Config (in theme-config.php)

```php
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
```

Scripts/styles with `'admin' => true` are enqueued via `admin_enqueue_scripts`. Custom attributes (type, defer, crossorigin) are added via `script_loader_tag` / `style_loader_tag` filters automatically.
