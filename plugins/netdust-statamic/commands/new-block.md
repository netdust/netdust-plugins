---
description: Scaffold a new page builder block by copying from an existing one (no Peak CLI dependency)
argument-hint: <block_handle> [display name]
---

Scaffold a new page builder block named `$1` ($2 for display name).

**Don't run `php please peak:make:block`** — that requires the paid Peak CLI. We scaffold from the 17 existing blocks instead.

Steps:

1. **Pick a reference block** that's structurally close to what's needed. Read its fieldset and partial:
   - `resources/fieldsets/[reference].yaml`
   - `resources/views/page_builder/_[reference].antlers.html`

   Common references:
   - Hero-like (variants, image, CTAs) → `hero.yaml`
   - Feature/benefit grid → `feature_grid.yaml` or `column_grid.yaml`
   - Image+text alternating → `feature_detail.yaml`
   - Card grid → `cards.yaml`
   - Pricing layout → `pricing_tiers.yaml` or `pricing_split.yaml`
   - Single CTA section → `cta_banner.yaml`
   - List/checklist → `interactive_checklist.yaml` (interactive) or `feature_detail.yaml` (static)

2. **Create the fieldset** at `resources/fieldsets/$1.yaml`:
   - Top-level `title: '$2'`
   - Each field: `handle`, `display`, `instructions` (always — write a one-line plain-Dutch hint), `listable: false` for content fields
   - Use `width: 50` / `width: 33` to pair short fields on one row instead of stacking
   - Use `if:` to hide fields that depend on a variant choice
   - Required fields get `validate: [required]`
   - Repeatable items: `grid` (simple rows) or nested `replicator` (complex rows like buttons/tiers)
   - **Ask the user what fields the block needs** before writing — don't guess.

3. **Register the block** in `resources/fieldsets/page_builder.yaml` under the appropriate group (`content` or `interactive`):
   ```yaml
   $1:
     display: '$2'
     instructions: 'One-line plain-Dutch description of what this block does.'
     icon: [pick-from-statamic-icon-set]
     fields:
       -
         import: $1
   ```

4. **Create the partial** at `resources/views/page_builder/_$1.antlers.html`:
   - Use Tailwind 4 utility classes consistent with the design system (`navy`, `copper`, `cream`, Satoshi/DM Sans)
   - Use the `picture` partial for responsive imagery
   - Use Alpine `x-intersect` for scroll-reveal where the design uses `.reveal`
   - Reference the chosen block's partial for structure

5. **Verify**:
   ```bash
   ddev exec php please stache:clear
   ddev exec php please stache:warm
   ```
   Then add the block to a test page in the CP and confirm it renders.

**Pre-flight rule:** Before writing fields, ask: *"What's the minimum an editor needs to fill in to make this block useful?"* Cut anything that's nice-to-have. Hide rarely-used fields behind a `revealer` or a variant `if:`.
