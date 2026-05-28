# NTDST Response

Fast template rendering with automatic path discovery.

**Location:** `app/content/mu-plugins/ntdst-core/api/Response.php`

## Global Helpers

All wrapped in `function_exists()` guards.

```php
ntdst_response()                       // Get Response instance
ntdst_redirect($url, $status)          // Safe redirect (wp_safe_redirect)
ntdst_download($content, $filename)    // Force-download a generated file
ntdst_inline($content, $filename)      // Display a generated file inline
```

## Core Methods

### Passing Data

```php
// Single variable
ntdst_response()->with('key', $value);

// Multiple variables
ntdst_response()
    ->with('project', $project)
    ->with('related', $relatedItems)
    ->with('meta', $metadata);

// Array of variables
ntdst_response()->withData([
    'project' => $project,
    'related' => $relatedItems,
]);
```

### Rendering

```php
// Deferred rendering (for routing - returns Response object)
return ntdst_response()
    ->with('project', $project)
    ->template('portfolio/single');

// Immediate rendering (outputs and exits)
ntdst_response()
    ->with('projects', $projects)
    ->render('portfolio/archive');

// Get HTML as string (for emails, AJAX responses)
$html = ntdst_response()
    ->with('user', $user)
    ->html('emails/welcome');

// JSON response (outputs and exits)
ntdst_response()
    ->with('results', $results)
    ->with('total', $count)
    ->json();
```

## Template Resolution Order

Templates are searched in this order:

1. Custom paths added via `addPath()`
2. `{child-theme}/templates/`
3. `{parent-theme}/templates/`
4. `{child-theme}/views/`

## Usage Patterns

### In Router/Theme callbacks

```php
$theme->single('portfolio', function($post) {
    $related = ntdst_data()->get('portfolio')
        ->whereTax('category', get_the_terms($post->ID, 'category'))
        ->limit(3)
        ->get();

    return ntdst_response()
        ->with('project', $post)
        ->with('related', $related)
        ->template('portfolio/single');
});
```

### For Email Templates

```php
$html = ntdst_response()
    ->with('user_name', $user->display_name)
    ->with('order', $orderData)
    ->with('items', $lineItems)
    ->html('emails/order-confirmation');

ntdst_mail()
    ->to($user->user_email)
    ->subject('Order Confirmation')
    ->html($html)
    ->send();
```

### For AJAX/API Responses

```php
add_filter('ntdst/api_data/render_preview', function($data, $params) {
    $post = ntdst_data()->get('portfolio')->find($params['id']);

    if (!$post) {
        return new WP_Error('not_found', 'Item not found');
    }

    return [
        'html' => ntdst_response()
            ->with('item', $post)
            ->html('partials/preview-card'),
    ];
}, 10, 2);
```

### For Share Cards / OG Images

```php
ntdst_router()->get('share/:type/:slug', function($params) {
    $post = ntdst_data()->get($params['type'])
        ->where('post_name', $params['slug'])
        ->first();

    if (!$post) {
        return false;
    }

    // Render standalone HTML page
    ntdst_response()
        ->with('item', $post)
        ->with('type', $params['type'])
        ->render('share-cards/' . $params['type']);
});
```

## Custom Template Paths

```php
// Add custom search path
ntdst_response()->addPath('/path/to/custom/templates');

// Now templates in that path are found first
ntdst_response()->template('my-template');
```

## Template File Structure

```
ntdstheme/
├── templates/
│   ├── portfolio/
│   │   ├── single.php
│   │   └── archive.php
│   ├── pages/
│   │   └── about.php
│   └── partials/
│       └── card.php
└── views/
    ├── emails/
    │   ├── welcome.php
    │   └── order-confirmation.php
    └── share-cards/
        ├── layout.php
        └── artwork.php
```

## Inside Templates

Variables passed with `with()` are available directly:

```php
<!-- templates/portfolio/single.php -->
<article class="portfolio-item">
    <h1><?php echo esc_html($project->post_title); ?></h1>

    <?php if (!empty($related)): ?>
        <aside class="related-items">
            <?php foreach ($related as $item): ?>
                <div class="card">
                    <?php echo esc_html($item['title']); ?>
                </div>
            <?php endforeach; ?>
        </aside>
    <?php endif; ?>
</article>
```

## Method Reference

| Method | Returns | Description |
|--------|---------|-------------|
| `with($key, $value)` | `self` | Add template variable |
| `withData(array $data)` | `self` | Add multiple variables |
| `template($path)` | `self` | Set template (deferred) |
| `render($path)` | `never` | Render and exit |
| `html($path)` | `string` | Render to string |
| `json()` | `never` | Output JSON and exit. Falls back to a structured error body if `json_encode` fails (was: silent empty response). |
| `error($msg, $status)` | `self` | Set error state (used by `json()` / `render()` / `redirect()`) |
| `redirect($url)` | `never` | `wp_safe_redirect` to `$url`. Appends `?error=` if `error()` has been set. |
| `download($content, $filename, $mime = null)` | `never` | Stream as attachment. |
| `inline($content, $filename, $mime = null)` | `never` | Stream inline. |
| `addPath($path)` | `self` | Add template search path |

## Error Responses

```php
ntdst_response()->error('Not found', 404)->json();
ntdst_response()->error('Forbidden', 403)->render('error');

// Redirect with the error attached as a query param — handy for form
// submissions that need to bounce back to the originating page.
ntdst_response()->error('Invalid token.')->redirect(home_url('/login'));
```

## Batch Data

```php
ntdst_response()->withData([
    'projects' => $projects,
    'total'    => $count,
    'page'     => $page,
])->json();
```

## File Downloads (download / inline)

`download()` (attachment) and `inline()` (display in browser) send a generated body — useful for PDFs, calendar files, CSV exports.

```php
// Quote PDF
ntdst_response()->download($pdf_bytes, 'quote-2026-001.pdf');

// iCal feed
ntdst_response()->inline($ical, 'enrollment.ics');
```

**Filename handling** is hardened against header-injection:
- CRLF (`\r`, `\n`) and double-quotes are stripped — a filename like `"x\r\nSet-Cookie: y"` can't smuggle response headers.
- Non-ASCII filenames get both `filename="ascii_fallback"` and `filename*=UTF-8''...` per RFC 5987, so `factuur-Müller.pdf` renders correctly in every modern browser.

## Security Model

- **`redirect()` defaults to `wp_safe_redirect`** — restricts the destination to the same host as the site. Closes open-redirect attacks when the URL is derived from request input. (`ntdst_redirect()` helper uses the same.)
- **`sendFile()` filenames** are CRLF/quote stripped before they hit the `Content-Disposition` header.
- **`locate()` confines templates to their declared base directory** via `realpath` checks. Stride's template names are hardcoded strings today, but if any future caller passes a user-influenced template name (e.g. from a query parameter), this prevents `'../../../../etc/passwd'`-style inclusion. Any path that resolves outside the registered base is rejected.

## Performance

- Template paths cached statically (shared across Response instances).
- Located template files cached to avoid repeated `file_exists()` calls.
- Call `NTDST_Response::clearPathCache()` if paths change at runtime.
