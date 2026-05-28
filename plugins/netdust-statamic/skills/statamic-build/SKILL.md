---
name: statamic-build
description: Use when implementing a feature in any Netdust Statamic project — adding a page-builder block, scaffolding a collection, wiring a Service, adding fields to a blueprint, building an addon. Triggers on file edits to resources/blueprints/, resources/fieldsets/, content/collections/, resources/views/, app/Services/, app/Providers/, app/Listeners/, or use of the `please` CLI. Activates on keywords statamic, peak, blueprint, fieldset, page builder, page_builder, set, partial, antlers, blade, php please, ddev exec php please, stache, replicator, bard, sections, instructions:, validate:, revealer, content dashboard, addon, php please install. Symptoms include "add a block", "new feature", "build a", "implement", "wire up", "add a field", "scaffold a collection", "make this editable". Codifies the editor-friendliness Iron Rules, the MCP-first pattern for content ops, and the build phase tooling. Companion to shake-out-statamic (post-build QA).
---

<objective>
Disciplined feature implementation in an ntdst-starter project. Mirrors how a Netdust senior would build: editor profile constraints first, copy from existing patterns second, MCP for content ops third, write fields before partials, partials before logic. The skill complements the post-build `shake-out-statamic` skill — this one runs *during* the build phase.
</objective>

<essential_principles>

**The Editor Profile Iron Rules**

These constrain everything. If a decision violates one, redesign the decision.

1. **Field instructions are mandatory.** Every editable field has a one-line plain-language hint via the `instructions:` key. No exceptions.
2. **Required fields validate.** Use `validate: [required]`. Optional fields hide behind variant `if:` or a `revealer` field.
3. **≤ 5 fields per block.** Beyond that, use `sections:` to group. Beyond ~10 fields total even with sections, the block is doing too much — split it.
4. **≤ 10 blocks in the picker.** Beyond that, the set selector becomes a usability problem (community-validated UX cliff).
5. **Live preview must work.** Don't introduce server-side rendering that breaks Statamic's live preview iframe.
6. **No technical jargon in CP labels.** No "blueprint", "fieldset", "stache", "slug", "handle" surfaced to editors. "Title", "Description", "Image", "Layout" — terms editors recognize.

**Red flags during build — STOP if you catch yourself:**

- Adding a 6th field to a block without using `sections:`
- Writing a field with no `instructions:`
- Naming a CP-visible field with a developer term
- Inlining business logic in an Antlers/Blade template instead of a service
- Creating a block to handle one specific page's design (build it as a one-off in the template instead)
- Skipping the existing-blocks reference scan because "this is different"

**Common rationalizations:**

| Excuse | Reality |
|---|---|
| "This block has 8 fields but they're all important" | Then it's two blocks, or three sections of three. |
| "Editors will figure out what 'slug' means" | They will not. They will email you. Use plain words. |
| "I'll add instructions later" | You will not. They will ship missing. Add them now. |
| "This logic is small enough to inline in the template" | Templates are for rendering. Move it to a service. |
| "I'll skip the existing-blocks scan, this is a new pattern" | If it's truly new, scan to confirm. If it's not, you save 30 minutes. |

</essential_principles>

<quick_start>

Three phases:

1. **PRE-WRITE** — Understand intent, scan existing patterns, draft the smallest viable shape. Don't write code yet.
2. **WRITE** — Field-first (fieldset YAML), then partial (Antlers HTML), then service (PHP) if needed. Use MCP for content ops, not raw file edits where avoidable.
3. **VERIFY** — Stache clear/warm, run smoke + blueprint tests, render the page, run shake-out-statamic skill if the change is non-trivial.

Each phase has a checklist below.

</quick_start>

<process>

## Phase 1 — PRE-WRITE

### Step 1.1: Read the user's intent

Confirm what's being built in one sentence. Examples:
- "Add a video-with-text block to the page builder"
- "Add an exhibitions field to the Artist global"
- "Wire the contact form to send to a different inbox"

If the intent is fuzzy ("make the page builder better"), stop and ask the user for the specific outcome before proceeding.

### Step 1.2: Decide where the work lives

| Type of change | Where it lives |
|---|---|
| New universal block | `resources/fieldsets/<handle>.yaml` + `resources/views/page_builder/_<handle>.antlers.html` + register in `page_builder.yaml` |
| New domain block (portfolio-specific, studio-specific) | The relevant addon, NOT the starter |
| New global | `content/globals/<handle>.yaml` + blueprint |
| New collection | `content/collections/<handle>.yaml` + blueprint at `resources/blueprints/collections/<handle>/` |
| Business logic | `app/Services/<Name>Service.php`, registered in `AppServiceProvider::register()` |
| HTTP handling | `app/Http/Controllers/<Name>Controller.php`, thin — delegates to a service |
| Event reaction | `app/Listeners/<VerbNoun>.php`, registered in `AppServiceProvider::boot()` |

If the work fits in an existing service or block, prefer extension over new files.

### Step 1.3: Scan existing patterns

Before writing one line:

1. **Find the closest existing block to what you're building.** Read its fieldset and partial.
   - `hero.yaml` — variants + sections
   - `gallery.yaml` — repeatable items + layout choice
   - `cards.yaml` — repeatable items + per-item button
   - `cta.yaml` — short content + style variant
   - `article.yaml` — Bard with sub-sets
   - `pull_quote.yaml` (used as `quote` block) — minimal, focused

2. **Read CLAUDE.md** if you haven't this session. Architecture rules and Quick Reference live there.

3. **Read the project's `PEAK.md`** (if present in the project root — ships with `ntdst-starter`, may be absent in greenfield projects) if you'll use Peak partials (`picture`, `typography/h1..h6`, `components/button`, `statamic-peak-tools::snippets/button_attributes`). If no project `PEAK.md`, fall back to the `peak-reference` skill for partial signatures.

### Step 1.4: Draft the field list

Before writing YAML, list the fields on a scratch:

```
Hero
├── eyebrow      [text, optional]
├── heading      [text, REQUIRED]
├── subheading   [textarea, optional]
├── image        [asset, optional, container=images]
└── buttons      [replicator of button, optional]
```

Then audit against the 6 rules. If it fails, redesign before writing. **Cheaper to redesign on paper than in YAML.**

### Step 1.5: Decide what to use MCP for

For content operations (creating/reading/updating entries, blueprints, globals), prefer the `statamic-mcp` router over file edits:

- `mcp: statamic-blueprints action=get handle=page` — read blueprint as JSON, easier than parsing YAML
- `mcp: statamic-entries action=create collection=pages data={...}` — create entries idempotently
- `mcp: statamic-globals action=update handle=site_settings data={...}` — update globals

For *schema* changes (adding fieldsets, blueprints, partials), use file edits — the MCP router is for content, not source code.

## Phase 2 — WRITE

### Step 2.1: Fieldset first

Always start with the YAML. Field shape determines everything downstream.

Template:

```yaml
title: 'Block Display Name'
sections:                       # Optional — only for blocks with > 5 fields or distinct concern groups
  primary:
    display: 'Section Name'
    instructions: 'What this group of fields covers.'
    fields:
      - handle: heading
        field:
          type: text
          display: Heading
          instructions: 'Plain-language hint about what this field is for.'
          validate: [required]
          listable: false
      # more fields
  secondary:
    display: 'Another Group'
    fields:
      # more fields
```

Or without sections:

```yaml
title: 'Block Display Name'
fields:
  - handle: heading
    field:
      type: text
      display: Heading
      instructions: 'Plain-language hint.'
      validate: [required]
      listable: false
  # 4 more fields max
```

**After writing the fieldset, re-audit against the 6 rules.** It's faster to fix YAML than fix YAML *and* a partial *and* a service.

### Step 2.2: Register the block (page builder only)

Open `resources/fieldsets/page_builder.yaml`. Add the new set to the appropriate group (`content`, `media`, `interactive`):

```yaml
my_block:
  display: 'My Block'
  instructions: 'One-line plain-language description.'
  icon: <icon-from-statamic-set>
  fields:
    - import: my_block
```

### Step 2.3: Partial second

Convention: `resources/views/page_builder/_<handle>.antlers.html`. Always wrap in `{{ partial:page_builder/block }}`. Use existing partials wherever possible:

- Headings: `{{ partial:typography/h1 }}` … `h6`
- Body: `{{ partial:typography/p }}`
- Images: `{{ partial:components/image :asset="..." }}`
- Buttons: `{{ partial:components/button }}` (inside a `{{ buttons }}` loop)
- Pull quote: `{{ partial:components/pull_quote }}`

Template:

```antlers
{{#
    @name <Display Name>
    @desc <One-line description>
    @set page.page_builder.<handle>
#}}

<!-- /page_builder/_<handle>.antlers.html -->
{{ partial:page_builder/block class="gap-y-N" }}
    <!-- Content here. Use the fluid-grid columns: span-content, md:col-span-N, etc. -->
{{ /partial:page_builder/block }}
<!-- End: /page_builder/_<handle>.antlers.html -->
```

### Step 2.4: Service (only if business logic exists)

If the feature has logic beyond rendering (calculations, external API calls, complex queries):

```php
<?php

namespace App\Services;

class FeatureService
{
    public function __construct(
        protected SomeDependency $dep
    ) {}

    public function publicOperation(array $data): mixed
    {
        // Logic here
    }

    private function helperMethod(): void
    {
        // Internal
    }
}
```

Register in `app/Providers/AppServiceProvider.php::register()`:

```php
$this->app->singleton(\App\Services\FeatureService::class);
```

### Step 2.5: Use MCP for content seeding

If the build needs sample/seed content (e.g. demo entries for a new collection), use `statamic-mcp` action=create rather than hand-writing YAML:

```
mcp: statamic-entries action=create collection=works data={title: "Sample Work", year: 2026, ...}
```

This is more reliable than producing the right Markdown frontmatter shape.

## Phase 3 — VERIFY

### Step 3.1: Stache rebuild

Schema changes (blueprints, fieldsets, globals, collections) require a stache rebuild before they're visible:

```bash
ddev exec php please stache:clear
ddev exec php please stache:warm
```

Without this, the CP shows old schema and pages may render with stale data.

### Step 3.2: Run the test suite

```bash
ddev exec php artisan test --compact
```

The pre-commit hook runs this anyway, but catching failures here is faster than at commit time. **Specifically:** the `BlueprintValidationTest` will catch broken YAML in any blueprint or fieldset.

### Step 3.3: Render the page in DDEV

```bash
curl -s -o /dev/null -w '%{http_code}\n' "$(ddev describe -j | jq -r .raw.primary_url)/<path>"
```

200 = good. 500 = read `storage/logs/laravel.log`. 404 = check the route or stache.

### Step 3.4: Visual check via chrome-devtools

If the change affects rendering, open the page in chrome-devtools and look:
- No console errors
- Layout matches intent
- Live preview iframe in CP shows the same thing

### Step 3.5: Run shake-out-statamic if change is non-trivial

For multi-file changes, new collections, or anything that touches the page builder structure: invoke `Skill("shake-out-statamic")`. The three-phase sweep catches regressions in adjacent areas you didn't think to test.

For single-file content edits or one-line fieldset adjustments: skip shake-out, the smoke test + render check is enough.

### Step 3.6: Pint

```bash
vendor/bin/pint --dirty --format agent
```

Pre-commit hook enforces this, but running it manually before staging keeps the diff clean.

</process>

<integration>

**Pipeline position:**

```
brainstorm → plan → ntdst-statamic-build → shake-out-statamic → finishing-branch
```

| Skill | Relationship |
|---|---|
| `superpowers:brainstorming` | **UPSTREAM.** Use before this skill for any non-trivial feature. |
| `superpowers:writing-plans` | **UPSTREAM.** Multi-step features get a plan before invoking this skill per step. |
| `shake-out-statamic` | **DOWNSTREAM.** Post-build QA. Invoke after this skill for non-trivial changes. |
| `superpowers:systematic-debugging` | **PARALLEL.** Mid-build bugs go through this, not inline guess-and-fix. |
| `statamic-mcp` (MCP server) | **REQUIRED for content ops.** Use the routers, not file edits, when creating/updating entries/blueprints/globals. |
| `laravel-boost` (MCP server) | **REQUIRED for docs lookups.** `search-docs` before guessing at framework APIs. |

**Trigger phrases:**
- "add a block" / "new block"
- "implement" / "build a" / "wire up"
- "add a field" / "extend the blueprint"
- "create a collection" / "add a global"
- Any feature-implementation request inside an `ntdst-starter` project

**Do NOT use when:**
- Mid-build debugging — use `systematic-debugging`
- Post-build QA — use `shake-out-statamic`
- Architectural decisions about *whether* to build something — use `brainstorming`
- Rewriting / refactoring (different mode of work, different rules)

</integration>

<reference_index>

- `CLAUDE.md` — full project conventions
- `PEAK.md` — frontend partial reference
- `resources/fieldsets/` — every existing block as a copy-from reference
- `resources/views/page_builder/` — every existing block partial
- `app/Services/` — service pattern (NavCustomizer is the simplest example)
- `tests/Feature/BlueprintValidationTest.php` — the YAML guard the pre-commit hook runs
- `docs/superpowers/specs/` — feature specs go here
- `docs/superpowers/plans/` — implementation plans go here

</reference_index>

<success_criteria>

A build is complete when:

- [ ] The 6 editor-friendliness rules are met
- [ ] Fieldset has `instructions:` on every editable field
- [ ] Required fields validate; optional fields hide via `if:` where appropriate
- [ ] Block count in `page_builder.yaml` is ≤ 10 (per group, the picker stays scannable)
- [ ] Stache cleared and warmed after schema changes
- [ ] All tests pass (`php artisan test --compact`)
- [ ] Pint clean
- [ ] Page renders 200 with the expected content visible
- [ ] No JS console errors when viewed in chrome-devtools
- [ ] If non-trivial: shake-out-statamic invoked and manifest empty
- [ ] If feature added new docs needs: spec/plan files in `docs/superpowers/`

</success_criteria>
