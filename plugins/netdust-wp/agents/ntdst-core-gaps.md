# ntdst-core — Framework Gaps & Bug Reports

Issues, gaps, or inconsistencies in the **framework itself** (`ntdst-core/`), surfaced incidentally during project audits. Distinct from project drift — these are findings the framework maintainer should address, not the project author.

## What goes here

- **Missing helpers** — places where every project re-implements the same thing because the framework doesn't provide it (e.g. `findIdsByX` on `AbstractRepository`, batch-meta read helper).
- **API inconsistencies** — methods with similar names but different contracts (e.g. `find()` returning `WP_Post|WP_Error` in one repo type vs `?object` in another).
- **Documentation gaps** — patterns that work but aren't documented in `references/*.md`, forcing audits to read framework source to verify.
- **Real framework bugs** — silent failures, race conditions, contract violations in `ntdst-core/` code.
- **Friction patterns** — places where the framework's choice forces awkward project-level code (e.g. having to use `getMetaPrefix()` for batch reads instead of the framework providing a typed batch-read).

## What does NOT go here

- **Project drift** — that's `ntdst-drift-reviewer.lessons.md` (false positives) or the project's own memory directory (project-specific quirks).
- **Wishlist features** — "the framework should have X" without a concrete pain point that surfaced in an audit.
- **Stylistic preferences** — "I'd name this differently" is not a framework gap.

## Curation rules

- **Manual review only.** The agent surfaces candidate entries in its audit reports under a "Framework gaps observed" section. The human decides what lands here. The agent does not append directly.
- **One entry per gap.** If the same gap surfaces across multiple audits, append observations to the existing entry rather than creating duplicates.
- **Resolution tracking.** When a gap gets fixed in `ntdst-core/`, move the entry to a `## Resolved` section at the bottom with a date and commit reference. Eventually prune resolved entries that are >6 months old.

## Entry format

```markdown
### YYYY-MM-DD — <one-line description>

**Where surfaced:** <which project audit found this; can be multiple if observed elsewhere>

**The gap:** <what's missing / inconsistent / buggy — be specific, cite framework file:line if possible>

**Project-side workaround:** <what projects currently do to cope, if anything>

**Suggested framework change:** <one paragraph — what would close the gap>

**Severity:** Bug | Gap | Friction | Documentation
```

---

### 2026-05-19 — No batch aggregate helpers on `AbstractRepository` for custom-table repos

**Where surfaced:** Stride Assistant audit (`ReadAbilityRegistrar::batchRegisteredCounts`, `batchStatusBreakdown`). Same shape observed earlier in Stride Edition module (`EditionService::getRegisteredCount` single-ID version) and in `RegistrationRepository::countByTrajectoryIds`. Three distinct inline implementations across the codebase by the time the gap was named.

**The gap:** Custom-table repositories extend `AbstractRepository` but only inherit CPT-shaped helpers (`find`, `create`, `update`, `delete`, `all`, `count`, `getField`, `findFields` — see `Infrastructure/AbstractRepository.php:82-107`). When a caller needs aggregate counts grouped by an FK column (e.g. "give me confirmed counts for these 50 edition IDs in one query") or grouped by an enum column (e.g. "give me status → count for these editions"), there is no framework primitive. Per the 2026-05-19 calibration note on the drift-reviewer side, `findFields` is single-ID. Result: callers either drop to raw `$wpdb->get_results('... GROUP BY ...')` and bypass the repository (the Assistant audit's actual finding), or each project repo invents its own `countByXIds(array)` helper with a near-identical signature.

**Project-side workaround:** Each repository implements `countByXIds(array $ids): array<int,int>` inline, parameterising only the column. Stride landed `RegistrationRepository::countByEditions` and `statusBreakdownByEditions` in commit `640cb1ce` to close the Assistant audit's drift, alongside the pre-existing `countByTrajectoryIds`. Three near-identical methods on one repo class signals the gap.

**Suggested framework change:** Add to `AbstractRepository`:
- `countGroupedBy(string $column, array $whereIn, array $extraConditions = []): array<int|string,int>` — generic "count rows grouped by one column, with an IN(…) filter on another." Custom-table repos override `table()`; CPT repos point at `wp_posts` + meta join. Closes the `countByEditions` / `countByTrajectoryIds` / `batchRegisteredCounts` shape.
- Optional sibling: `breakdownBy(string $column, array $whereIn, string $groupBy): array<string,int>` — same operation but the grouping column is different from the filter column. Closes the `statusBreakdownByEditions` shape (filter `edition_id IN (...)`, group by `status`).

Both can be expressed as a single more-general `aggregateGroupedBy(string $groupBy, array $where, ?string $countColumn = null): array` if the framework prefers one primitive over two.

**Severity:** Friction — forces well-formed code to bypass the repository; no bug, but multiplies drift surface across projects and confuses junior code-readers ("why are some counts on the repo and some on the service?"). Closing it would also let `ntdst-drift-reviewer` flag *any* `$wpdb->get_results('... GROUP BY ...')` against a known-repo table as drift, without false positives for "no framework helper exists."

### 2026-06-09 — No public schema accessor on Data-Manager models forces reflection in theme/YOOtheme code

**Where surfaced:** Golden-path mining of Rossi's YOOtheme layer (`ntdstheme/services/yootheme/YOOthemeDynamicContentService.php:403` `attach_post_meta()`, and `ArtistSourcesService.php:156` `clean_meta_for_yootheme()`). Both need the registered field list for a post type to (a) filter exposed meta to declared fields only and (b) coerce by field type.

**The gap:** A Data-Manager model registered via `ntdst_data()->register($type, ['fields' => [...]])` exposes its field schema only through a **private `schema` property**. There is no public `getSchema()` / `getFields()` / `getFieldType($field)` accessor. Code that needs the schema does this:

```php
$model = ntdst_data()->get($post_type);
$reflection = new \ReflectionClass($model);
$schema_property = $reflection->getProperty('schema');
$schema_property->setAccessible(true);            // reach into a private — fragile
$schema = $schema_property->getValue($model);
```

This is brittle (breaks silently if the property is renamed) and appears in **two** Rossi YOOtheme files independently. Any project doing schema-aware meta hydration (YOOtheme, exporters, REST shaping) hits the same wall.

**Project-side workaround:** Reflection into the private property, wrapped in a `try/catch` that fails open to "no schema" (so a rename degrades to exposing *all* meta — a quiet security/serialisation regression, not a hard error).

**Suggested framework change:** Add a public read accessor to the Data-Manager model — `getSchema(): array` and a convenience `getFieldType(string $field): ?string`. The CPT field schema is already the single source of truth (CLAUDE.md INV-3); exposing it read-only removes the reflection and lets the framework own the "declared fields only" filter that `attach_post_meta()` re-implements by hand.

**Severity:** Friction / Documentation — works today via reflection, but the private-property reach is fragile and undocumented, and the fail-open `catch` is a latent meta-exposure risk if the internal name changes.

### 2026-06-09 — Theme templates have no ergonomic repository read, so they drift to `ntdst_data()`

**Where surfaced:** Golden-path mining of Stride's content-type slice (`themes/stridence/single-vad_edition.php:88`). The template does `$editionModel = ntdst_data()->get('vad_edition'); $editionModel->getMeta($id, 'start_date')` directly — drift cat 1 (CPT access outside the repository). Its own inline comment admits the gap: *"these could be added to EditionService if needed frequently."*

**The gap:** Themes can't use constructor DI, so the documented path is `ntdst_get(FooRepository::class)->getField($id, 'x')`. That works, but `ntdst_data()->get($type)->getMeta(...)` is **shorter to type and discoverable from any WP tutorial**, so production theme code keeps drifting to it. The framework provides the *correct* path but not an equally-frictionless one — and the repository class name a template must know is long and project-specific (`\Stride\Modules\Edition\EditionRepository`). The result is that even a clean module's *frontend* drifts at the last hop (this exact line is the only drift in an otherwise spotless Edition spine).

**Project-side workaround:** Use `ntdst_get(Repository::class)->getField(...)` and hope reviewers catch the templates that didn't. The golden-path doc (`content-type-feature.md`) now shows the correct pattern and explicitly marks Stride's drifted line "do not copy" — but that's documentation papering over an ergonomics gap.

**Suggested framework change:** Provide a thin theme-facing read helper that resolves the repository by post type, e.g. `ntdst_repo('vad_edition')->getField($id, 'start_date')` (a registry keyed on the post-type slug the CPT already declares), or a template helper `ntdst_field($id, 'start_date')` that infers the repo from `get_post_type($id)`. Either gives templates a path as short as `ntdst_data()` that still routes through the repository's caching/validation — removing the incentive to drift.

**Severity:** Friction — the correct path exists but loses the ergonomics race against `ntdst_data()`, so frontend drift recurs at the last hop of otherwise-clean slices. Closing it would let `ntdst-drift-reviewer` treat *any* `ntdst_data()` in a theme file as unambiguous drift with a one-token fix.

## Resolved

*Empty for now.*
