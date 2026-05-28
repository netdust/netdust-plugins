---
name: peak-reference
description: Use when working with Statamic Peak — the opinionated Statamic starter kit. Reference for `php please peak:make:*` commands (block, set, collection, partial, global, taxonomy, nav), Peak's built-in partials (picture, typography, button, fluid grid), page builder set conventions, and Peak's directory structure. Triggers on `peak`, `php please peak:make`, partial names from Peak (picture, button, typography), `resources/views/peak/`, Peak's page builder block conventions. Symptoms include scaffolding a Statamic site from Peak, adding a page builder block, using Peak's picture partial for responsive images, customizing a Peak partial. Reference skill, not discipline.
---

# Peak Reference Guide

Comprehensive reference for Statamic Peak - the opinionated starter kit.

**Source:** https://peak.1902.studio

---

## Quick Reference

```bash
# Create things
php please peak:make:block        # Page builder block
php please peak:make:set          # Bard article set
php please peak:make:collection   # Collection + blueprint
php please peak:make:partial      # Component/layout/snippet
php please peak:make:global       # Global set
php please peak:make:taxonomy     # Taxonomy
php please peak:make:nav          # Navigation

# Install presets
php please peak:install:block     # Install premade block
php please peak:install:preset    # Install full preset
php please peak:install:set       # Install Bard set

# Maintenance
php please peak:clear-site        # Remove default content
php please static:warm --queue    # Pre-generate images
```

---

## Images

### Picture Partial

Use Peak's picture partial for responsive images with automatic sourcesets.

```antlers
{{ partial src="statamic-peak-tools::components/picture"
    :image="image"
    aspect_ratio="1/1 large:4/3"
    cover="true"
    sizes="(min-width: 768px) 35vw, 90vw"
    lazy="true"
}}
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `image` | asset | The image variable |
| `aspect_ratio` | string | Crop ratio like `16/9` or responsive `1/1 large:1/2` |
| `class` | string | CSS classes |
| `cover` | boolean | Whether image should cover container |
| `sizes` | string | Browser sizing hints |
| `quality` | integer | Image quality (default: 85) |
| `lazy` | boolean | Lazy loading |
| `bg` | string | Background color for transparent images |
| `blur` | integer | 0-100 blur effect |
| `brightness` | string | -100 to +100 |
| `contrast` | string | -100 to +100 |
| `filter` | string | `greyscale` or `sepia` |
| `gamma` | float | 0.1 to 9.99 |
| `sharpen` | integer | 0-100 |
| `pixelate` | integer | 0-1000 |

### Responsive Aspect Ratios

```antlers
{{# Different ratios at different breakpoints #}}
aspect_ratio="1/1 md:4/3 lg:16/9"
```

### Image Cache Warming

Pre-generate images during deployment:
```bash
php please static:warm --queue
```

### Customizing Picture Partial

```bash
php artisan vendor:publish --tag="statamic-peak-tools-views"
```

---

## Navigation

### Location
`resources/views/navigation/_main.antlers.html`

### Features
- Desktop/mobile responsive variants
- Two-level hierarchy
- AlpineJS interactivity

### Basic Navigation Loop

```antlers
{{ nav:main }}
    <a href="{{ url }}">{{ title }}</a>
    {{ if children }}
        <ul>
            {{ children }}
                <a href="{{ url }}">{{ title }}</a>
            {{ /children }}
        </ul>
    {{ /if }}
{{ /nav:main }}
```

---

## Fluid Grid

Full-bleed layout system with centered 12-column content area.

### Container Class

```html
<div class="fluid-grid">
    <!-- Content spans edge to edge with centered columns -->
</div>
```

### Span Utilities

| Class | Behavior |
|-------|----------|
| `.span-content` | Fits within content area |
| `.span-full` | Edge to edge |
| `.span-md` | Columns 3-10 at md breakpoint |
| `.span-lg` | Columns 2-11 at md breakpoint |
| `.span-xl` | Full width at md breakpoint |

### Manual Column Placement

```html
<div class="md:col-start-[col-3] md:col-span-8">
    <!-- Starts at column 3, spans 8 columns -->
</div>
```

### Gap Utility

```html
<div class="gap-fluid-grid-gap">
    <!-- Matches parent grid gap -->
</div>
```

---

## Stacks (Spacing)

Custom spacing system for page builder blocks.

### Parent Stack

```html
<main class="stack-16">
    <!-- Children get margin-top when preceded by sibling -->
</main>
```

### Child Overrides

| Class | Effect |
|-------|--------|
| `no-space-t` | Remove top margin from current element |
| `no-space-b` | Remove top margin from next sibling |
| `no-space-y` | Both (no space above or below) |
| `stack-space-8` | Custom margin top |
| `stack-space-collapse` | Enable margin collapsing |

### Example

```html
<main class="stack-16">
    <section></section>
    <section class="no-space-y"></section>  <!-- No space above or below -->
    <section></section>
    <section class="stack-space-8"></section>  <!-- Reduced space -->
</main>
```

---

## Typography

### Partials Location
`resources/views/typography/`

### Heading Partial

```antlers
{{ partial:typography/h1 :content="block:title" }}

{{# With customization #}}
{{ partial:typography/h1
    as="span"
    color="text-error-600"
    class="mb-8"
    :content="block:title"
}}
```

### Parameters

| Parameter | Description |
|-----------|-------------|
| `as` | Change HTML tag |
| `color` | Tailwind text color class |
| `class` | Additional utility classes |
| `content` | Text content |

### Prose Partial (for Bard)

```antlers
{{ partial:typography/prose as="article" class="prose-h4:text-neutral" }}
    {{ block:text }}
{{ /partial:typography/prose }}
```

---

## Buttons

### Files
- Fieldset: `resources/fieldsets/buttons.yaml`
- Partial: `resources/views/components/_buttons.antlers.html`

### Basic Usage

```antlers
{{# Link to URL #}}
{{ partial:components/button label="View all" link_type="url" url="/news" }}

{{# Link to mount URL #}}
{{ partial:components/button label="All news" link_type="url" url="{mount_url:news}" }}

{{# Link to entry #}}
{{ partial:components/button label="Read more" link_type="entry" :entry="entry" }}
```

### Custom Alpine Interactions

```antlers
{{ partial:components/button }}
    {{ slot:attributes }}
        @click="doSomething()"
    {{ /slot:attributes }}
{{ /partial:components/button }}
```

### Event Tracking

Button fieldset includes event field for GTM/GTAG/Fathom tracking (auto-logs on click).

---

## Page Builder

### Creating Blocks

```bash
php please peak:make:block
```

Creates:
- Fieldset in `resources/fieldsets/`
- Partial in `resources/views/page_builder/`
- Updates `page_builder.yaml`

### Block Variable Scoping

All fields in blocks require `block:` prefix:

```antlers
{{ block:title }}
{{ block:text }}
{{ block:image }}
```

### Block Partial Structure

Blocks extend `resources/views/page_builder/_block.antlers.html`:

```antlers
{{# resources/views/page_builder/_myblock.antlers.html #}}
{{ partial:typography/h2 :content="block:title" }}
{{ partial:typography/prose }}
    {{ block:text }}
{{ /partial:typography/prose }}
```

### Built-in Blocks

- **Article** - Long-form Bard content
- **Call to action** - Title, text, button
- **Collection** - Title with entry links
- **Forms** - Form integration
- **Link blocks** - Title/text linking to entries

### Installing Premade Blocks

```bash
php please peak:install:block
# Choose from: call-to-action, gallery, divider, etc.
```

---

## Bard (Article)

### Fieldset
`resources/fieldsets/article.yaml`

### Adding Sets

```bash
php please peak:make:set
```

Sets go in `resources/views/components/` with handle as filename.

### Sizing Utilities

| Class | Mobile | Medium+ |
|-------|--------|---------|
| `size-sm` | 12 cols | 4 cols |
| `size-md` | 12 cols | 6 cols (default) |
| `size-lg` | 12 cols | 8 cols |
| `size-xl` | 12 cols | 10 cols |

### Example Set Partial

```antlers
{{# resources/views/components/_figure.antlers.html #}}
<figure class="{{ size ?? 'size-md' }}">
    {{ partial src="statamic-peak-tools::components/picture" :image="image" }}
    {{ if caption }}
        <figcaption>{{ caption }}</figcaption>
    {{ /if }}
</figure>
```

---

## Forms

### Features
- Laravel Precognition live validation
- AlpineJS conditional fields
- Section support from blueprint builder

### Default Files
- Config: `resources/forms/contact.yaml`
- Blueprint: `resources/blueprints/forms/contact.yaml`
- Template: `resources/views/page_builder/_form.antlers.html`

### Success Hooks

```antlers
{{ partial:statamic-peak-tools::snippets/form_handler
    success_hook="console.log('Form submitted!')"
}}
```

### Hidden Fields with Alpine

```antlers
{{ form:create handle="contact" x-init="$data.source = document.referrer" }}
    <!-- Form fields -->
{{ /form:create }}
```

### Captcha Integration

```antlers
{{ form:create handle="contact" x-data='@{"captcha-response": "" }' }}
```

---

## SEO

### Features
- Page metadata (title, description, canonical)
- Open Graph & Twitter cards
- JSON-LD schemas (organization, person, breadcrumbs)
- Auto-generated sitemaps
- Hreflang for multi-locale
- Tracking (GA, GTM, Fathom, Cloudflare)
- No-index control per entry

### GDPR Consent Banner
- Google Consent API v2
- localStorage for consent
- Admin-configurable revoke dates
- Scripts load only after consent

### Consent Gate for Embeds

```antlers
{{ partial:components/consent_gate }}
    <!-- YouTube embed or tracking script -->
{{ /partial:components/consent_gate }}
```

### Customizing SEO Views

```bash
php artisan vendor:publish --tag="statamic-peak-seo-views"
php artisan vendor:publish --tag="statamic-peak-seo-fieldsets"
```

---

## Social Image Generation

### Requirements

```bash
composer require spatie/browsershot
npm install puppeteer
```

### Setup
1. Enable in SEO globals > Social Sharing
2. Select collections for auto-generation

### Template
`resources/views/vendor/statamic-peak-seo/components/_social_image.antlers.html`

### Preview URL
`/social-images/{entry-id}`

### Environment Config

```env
SOCIAL_IMAGE_FORMAT=png          # or jpg
SOCIAL_IMAGE_RESOLUTION=1200x630
SOCIAL_IMAGE_QUEUE_NAME=default
SOCIAL_IMAGE_CHROME_PATH=/usr/bin/chromium-browser  # ARM systems
```

### Publish Views

```bash
php artisan vendor:publish --tag="statamic-peak-seo-views"
```

---

## Globals

| Global | Purpose |
|--------|---------|
| Browser Appearance | Favicon, toolbar colors |
| Configuration | 404 entry, copyright, privacy |
| Redirects | 404-triggered redirects |
| SEO | Global SEO settings |
| Social Media | Social account links |

---

## Addons

### Browser Appearance
Favicon generation, browser styling, toolbar colors.

```bash
php artisan vendor:publish --tag="statamic-peak-browser-appearance-views"
php artisan vendor:publish --tag="statamic-peak-browser-appearance-fieldsets"
```

### SEO
Meta tags, OG images, sitemaps, redirects.

```bash
php artisan vendor:publish --tag="statamic-peak-seo-views"
php artisan vendor:publish --tag="statamic-peak-seo-fieldsets"
```

### Tools
Forms, images, pagination, skip-to-content, toolbar, missing alt widget.

```bash
php artisan vendor:publish --tag="statamic-peak-tools-views"
```

### Commands (Paid)
CLI commands for development acceleration.

```bash
php artisan vendor:publish --tag="statamic-peak-commands-stubs"
```

---

## Common Patterns

### Responsive Image Gallery

```antlers
<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
    {{ images }}
        {{ partial src="statamic-peak-tools::components/picture"
            :image="image"
            aspect_ratio="1/1"
            sizes="(min-width: 768px) 33vw, 50vw"
        }}
    {{ /images }}
</div>
```

### Entry Card

```antlers
<article class="card">
    {{ if featured_image }}
        {{ partial src="statamic-peak-tools::components/picture"
            :image="featured_image"
            aspect_ratio="16/9"
            sizes="(min-width: 768px) 33vw, 100vw"
        }}
    {{ /if }}
    {{ partial:typography/h3 :content="title" class="mt-4" }}
    {{ partial:typography/p :content="excerpt" class="text-neutral-600" }}
    {{ partial:components/button label="Read more" link_type="entry" :entry="id" }}
</article>
```

### Page Builder Template

```antlers
{{# resources/views/default.antlers.html #}}
{{ page_builder }}
    {{ partial src="page_builder/{type}" }}
{{ /page_builder }}
```

### Collection Listing

```antlers
{{ collection:artworks limit="12" sort="date:desc" }}
    <a href="{{ url }}">
        {{ partial src="statamic-peak-tools::components/picture"
            :image="images:0"
            aspect_ratio="1/1"
        }}
        {{ partial:typography/h3 :content="title" }}
    </a>
{{ /collection:artworks }}
```

---

## Resources

- **Documentation:** https://peak.1902.studio
- **GitHub:** https://github.com/studio1902/statamic-peak
- **Discord:** https://discord.gg/x3MNSH3nMz
- **Support:** https://1902.studio/en/peak-support
