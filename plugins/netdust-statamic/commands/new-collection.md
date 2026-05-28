---
description: Scaffold a new Statamic collection by copying from blog/pages (no Peak CLI dependency)
argument-hint: <collection_handle>
---

Create a new Statamic collection named `$1`.

**Don't run `php please peak:make:collection`** — that requires the paid Peak CLI. We scaffold from existing collections instead.

Steps:

1. **Pick a reference collection:**
   - Index-style content stream (date desc, slug-routed) → `blog`
   - Top-level navigation pages (manual sort) → `pages`

2. **Create the collection config** at `content/collections/$1.yaml`:
   - Copy from `content/collections/blog.yaml` or `content/collections/pages.yaml`
   - Update `title`, `route`, `sort_field`, `sort_dir`, `template`, `layout`
   - Route conventions: `/$1/{slug}` for indexed collections, `/{slug}` for top-level pages

3. **Create the blueprint** at `resources/blueprints/collections/$1/$1.yaml`:
   - Copy from `resources/blueprints/collections/blog/blog.yaml` or `pages/page.yaml`
   - Keep the `title` field required
   - Keep the SEO tab — the project uses Peak SEO globally, every URL-routed collection should include it
   - Add domain-specific fields (description, featured image, taxonomy refs, body)
   - For long-form content use `bard` with the same button set as `article.yaml`

4. **Create the templates** at `resources/views/$1/`:
   - `index.antlers.html` (collection landing) and `show.antlers.html` (single entry)
   - Reference `resources/views/blog/` for structure
   - Use the design system tokens and existing partials (`picture`, typography, button)

5. **Create at least one entry** so the routes resolve:
   ```bash
   ddev exec php please make:content $1
   ```
   Or use the MCP: `mcp: statamic-entries action=create collection=$1 data={...}`

6. **Add navigation** if editors should reach this from the CP nav (it auto-appears in the collections list, but custom CP nav lives in `app/Providers/AppServiceProvider.php::customizeNav`).

7. **Verify**:
   ```bash
   ddev exec php please stache:clear
   ddev exec php please stache:warm
   curl -sI https://$(basename $(pwd)).ddev.site/$1
   ```

**Editor-friendly check:** Once the blueprint is built, open it in the CP as a non-admin user. If a field's purpose isn't obvious from its label + instructions in 3 seconds, the blueprint isn't done.
