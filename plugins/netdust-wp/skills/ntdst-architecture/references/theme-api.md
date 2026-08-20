# Theme API Reference

## `NTDST_Theme`

Instantiated once in `functions.php`. Provides fluent API wrapping ntdst-core services.

### Built-in Mixins

Wired in the constructor — access via `$theme->`. **This is the complete list.**

```php
$theme->data()      // → ntdst_data()      NTDST_Data_Manager
$theme->pages()     // → ntdst_pages()     NTDST_Pages
$theme->response()  // → ntdst_response()  NTDST_Response
$theme->log()       // → ntdst_log()       NTDST_Logger
$theme->mail()      // → ntdst_mail()      NTDST_Mailer
```

> **`__call` THROWS.** `NTDST_Theme::__call()` raises `BadMethodCallException` for any
> name that is neither a real method nor a wired mixin. There is no silent no-op and no
> catch-all forwarder, so a call to a retired wrapper fails at the call site.
>
> **Real methods:** `on`, `filter`, `style`, `script`, `when`, `templatePath`, `single`,
> `page`, `archive`, `mixin`, `get_config`, `setup_theme`. Everything else on `$theme->`
> is a mixin name from the list above, or an exception.

### Data Models

> **RETIRED — `$theme->register()` and `$theme->taxonomy()` do not exist.** Both throw
> `BadMethodCallException`. `Theme::taxonomy()`'s defaults were lifted verbatim into
> `NTDST_Data_Manager::registerTaxonomy()`, which is now the one implementation.
> Go through the data layer directly:

```php
ntdst_data()->register('project', [
    'label'  => 'Projects',
    'public' => true,   // explicit opt-in — register() is PRIVATE by default
    'fields' => ['client' => 'text', 'year' => 'integer'],

    // Taxonomies are declared WITH the model. `terms` is seeded idempotently.
    'taxonomies' => [
        'project_type' => [
            'label'        => 'Project Types',
            'hierarchical' => true,
        ],
    ],
]);
```

`register()` returns `NTDST_Data_Model|WP_Error` — a `register_post_type()` refusal is
returned, not swallowed. `registerTaxonomy($taxonomy, $post_types, $args, $terms)` is
also callable directly when a taxonomy outlives any one model.

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

> **RETIRED — `$theme->apiAction()` does not exist** and throws `BadMethodCallException`.
> The capability-floor idiom it carried was reconciled onto ONE path:
> `ntdst_actions()->register()`. See `api-endpoints.md`.

```php
// Public action — anonymous callers may mint a nonce AND dispatch it.
ntdst_actions()->register('get_portfolio', function($data, $params) {
    $category = sanitize_text_field($params['category'] ?? '');
    return ['posts' => ntdst_data()->get('project')
        ->where('category', $category)->get()];
}, ['public' => true]);

// Protected action. Prefer `cap_type` — the floor is DERIVED from the post type,
// so a per-type capability map narrows the gate with you. A literal `capability`
// is correct only while that type's `capability_type` is still 'post'.
ntdst_actions()->register('save_project', function($data, $params) {
    // save logic
}, ['cap_type' => 'project']);
```

The floor bites at DISPATCH, ahead of the handler, and **fails closed**: an empty or
unresolvable capability denies everyone, administrators included. It is a floor
ALONGSIDE the handler's own per-row check, never a replacement for it. With neither
opt the action is simply login-required.

### Module Configuration

> **RETIRED — there is no `$theme->module()`.** It throws `BadMethodCallException`, and
> with it go `->config()`, `->enable()`, `->disable()`, `->before()` and `->after()`.
> A service is configured and switched at the framework's own three levels, not
> through the theme:
>
> | Level | Control |
> |---|---|
> | Metadata | `metadata()['enabled'] => false` |
> | Filter | `add_filter("ntdst_service_{slug}_enabled", '__return_false')` |
> | Option | `update_option("ntdst_service_{slug}", '0')` |
>
> Config overrides go through `services.overrides.{slug}` in `plugin-config.php`,
> which core feeds to the framework-owned `ntdst_service_{slug}_config` filter.
> See `services.md` — including what `{slug}` actually is, and that the `_enabled`
> filter is a DENY filter that FAILS OPEN on a misspelled slug.

### Conditional Config

`when()` evaluates its condition **immediately, at call time** — it is not deferred to
a hook. Anything that depends on the query must already be resolved when it runs.

```php
$theme->when(fn() => is_front_page(), function($theme) {
    $theme->filter('body_class', fn($c) => [...$c, 'is-front']);
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

### Assets

> **DELETED — the `assets` config key enqueues NOTHING.** The config-driven asset
> loader, its `ntdst_theme_assets` filter and the `attrs` → loader-tag rewriting were
> removed: ~120 lines with zero consumers on the fleet. `validate_config()` does not
> know the key, so an `assets` block in `theme-config.php` is merged in, never read,
> and **fails silently** — the page simply loads without your CSS.

Enqueue explicitly instead. Both helpers defer to `wp_enqueue_scripts` and pass their
arguments to WordPress verbatim, so versions and conditions are computed at the call
site:

```php
$theme->style('ntdst-theme', $dist . '/theme.css', [], '1.0');
$theme->script('ntdst-theme', $dist . '/theme.js', [], '1.0', in_footer: true);

// $priority orders this enqueue among wp_enqueue_scripts listeners. A child theme
// overriding its parent's CSS needs a late one — YOOtheme children use 20.
$theme->style('child-theme', $dist . '/child.css', ['parent-theme'], null, 'all', 20);
```

Signatures: `style($handle, $src, $deps = [], $ver = false, $media = 'all', $priority = 10)`
and `script($handle, $src, $deps = [], $ver = false, $in_footer = true, $priority = 10)`.
`$ver`: `false` = WP version, `null` = no version.

**There is no admin variant.** For `admin_enqueue_scripts`, use `$theme->on()` directly.

The **config keys `validate_config()` actually reads** are `textdomain`,
`content_width`, `theme_support`, `image_sizes`, `menus`, `sidebars` and `excerpt`.
Anything else in `theme-config.php` is inert.
