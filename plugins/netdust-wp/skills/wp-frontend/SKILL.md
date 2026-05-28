---
name: wp-frontend
description: Use when working on WordPress theme frontend — block themes (FSE), classic themes, theme.json, Gutenberg block development, custom block patterns, theme part files, asset pipelines (Vite, wp-scripts, npm), Tailwind in themes, Alpine.js integration, enqueue_scripts, block.json, render.php. Triggers on file edits in themes/<theme>/, on .html template files, block.json, theme.json, package.json in a theme dir. Activates on keywords block theme, FSE, theme.json, block.json, render_callback, enqueue_script, enqueue_style, wp_register_script, Vite, hot module reload, wp-scripts, Tailwind, Alpine, Gutenberg, pattern. Symptoms include building a new block, configuring theme.json, setting up the asset pipeline for a child theme, debugging "style not loading", deciding between native blocks and ACF blocks (use native — see ntdst-patterns).
---

# WordPress Frontend (block themes + asset pipeline)

## Default stack (Netdust)

- **Theme base**: Kadence (or similar) — child theme overrides everything important.
- **Theme.json + block templates** (FSE) for layout structure.
- **Tailwind + Alpine.js** via Vite for styling and interactivity (Stride pattern).
- **Native Gutenberg blocks** for content, not ACF blocks (per `ntdst-patterns`).
- **No jQuery** unless a plugin forces it.

## Asset pipeline

### Vite (preferred, Stride's choice)

```
themes/<theme>/
├── vite.config.js              ← entry, output, HMR
├── package.json                ← devDependencies
├── assets/
│   ├── css/main.css            ← Tailwind + custom
│   ├── js/main.js              ← Alpine + modules
│   └── dist/                   ← built (gitignored)
└── inc/enqueue.php             ← wp_enqueue_scripts + manifest reader
```

`vite.config.js` outputs `assets/dist/.vite/manifest.json`. The PHP enqueue layer reads the manifest to find the hashed filenames.

```php
function netdust_enqueue_assets(): void {
    $manifest = json_decode(
        file_get_contents( get_stylesheet_directory() . '/assets/dist/.vite/manifest.json' ),
        true
    );
    $main = $manifest['assets/js/main.js'] ?? null;
    if ( $main ) {
        wp_enqueue_script(
            'netdust-main',
            get_stylesheet_directory_uri() . '/assets/dist/' . $main['file'],
            array(),
            null,
            true
        );
        foreach ( $main['css'] ?? array() as $css ) {
            wp_enqueue_style(
                'netdust-main',
                get_stylesheet_directory_uri() . '/assets/dist/' . $css,
                array(),
                null
            );
        }
    }
}
add_action( 'wp_enqueue_scripts', 'netdust_enqueue_assets' );
```

### wp-scripts (when you want zero config)

For block-only builds where you don't need Tailwind. Comes with Gutenberg's webpack config out of the box.

```bash
npm install --save-dev @wordpress/scripts
npx wp-scripts build src/blocks/my-block
```

## theme.json (FSE configuration)

Lives at theme root. Replaces `add_theme_support` calls + a lot of CSS.

```json
{
  "$schema": "https://schemas.wp.org/trunk/theme.json",
  "version": 3,
  "settings": {
    "color": {
      "palette": [
        { "slug": "navy", "color": "#1a2744", "name": "Navy" },
        { "slug": "copper", "color": "#c47d5d", "name": "Copper" }
      ],
      "custom": false,
      "customGradient": false
    },
    "typography": {
      "fontFamilies": [
        { "slug": "satoshi", "name": "Satoshi", "fontFamily": "'Satoshi', sans-serif" }
      ]
    },
    "layout": {
      "contentSize": "720px",
      "wideSize": "1200px"
    }
  },
  "styles": {
    "color": { "background": "var(--wp--preset--color--cream)" }
  }
}
```

## Custom blocks (when needed)

Most pages: native blocks + block patterns. Custom blocks: only when there's interactive state or computed content not expressible in core blocks.

```
themes/<theme>/blocks/my-block/
├── block.json              ← metadata + render
├── edit.js                 ← editor UI
├── view.js                 ← (optional) frontend JS
├── style.css               ← shared
├── editor.css              ← editor only
└── render.php              ← server-side rendering (preferred)
```

Server-render via `render.php` for SEO + accessibility. Avoid `save.js` returning HTML — once shipped, you can't iterate without deprecation handling.

## When YOOtheme instead

If the project uses YOOtheme Pro (marketing client sites), use the `ntdst-yootheme` skill instead. YOOtheme has its own page builder, custom element model, and child theme conventions. Block-theme rules above do not apply.

## Common mistakes

- Tailwind classes in the editor not visible → editor.css isn't loading; ensure both `editor_style` and `style` are registered in `block.json`.
- `wp_enqueue_script` called outside `wp_enqueue_scripts` hook → silently fails.
- Using `the_field()` from ACF without escaping → fix at output (`echo esc_html(get_field(...))`). See `wp-security`.
- Vite HMR not working over DDEV's https → set Vite `server.origin` to the DDEV URL and use `server.hmr.host`.
- Forgetting `'in_footer' => true` (or the `array( 'in_footer' => true )` arg array form on WP 6.3+) → blocking script at the top.
- Theme version not bumped → cache busting fails on deploy. Bump `Version:` in `style.css` AND pass a hash as the `$ver` arg to `wp_enqueue_script` (the manifest-driven approach above sidesteps this by using hashed filenames).

## See also

- `ntdst-yootheme` — when project uses YOOtheme Pro instead
- `wp-security` — escaping output in templates and block renders
- `ntdst-patterns` — where theme files belong in the project layout
- `bedrock-composer` — what gets committed vs gitignored in `themes/`
- WordPress: [theme.json reference](https://developer.wordpress.org/themes/global-settings-and-styles/), [Block API](https://developer.wordpress.org/block-editor/reference-guides/block-api/)
