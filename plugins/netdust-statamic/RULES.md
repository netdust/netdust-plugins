# Netdust Statamic Rules

**Statamic-specific rules.** Universal rules (no `.env` commits, no `vendor/` edits, no direct-to-`main`, etc.) live in `netdust-core/RULES.md` — they apply here too.

**Violating the letter of these rules is violating the spirit of these rules.**

## Editor experience (the Iron Rules)

These are non-negotiable because they prevent the "client can't use the CP" failure mode that kills projects.

1. **Every editable field has `instructions:`.** Plain-language, one line. No exceptions.
2. **Required fields use `validate: [required]`.** Optional fields hide behind `if:` or `revealer`, they don't sit empty in the form.
3. **≤ 5 fields per block.** Use `sections:` to group if approaching the limit. If a block needs >10 fields total, it's two blocks.
4. **≤ 10 blocks in the page-builder set picker.** The community-validated UX cliff.
5. **No developer jargon in CP labels.** "Blueprint", "fieldset", "stache", "slug", "handle" never appear in editor-facing labels.
6. **Live preview must keep working.** No SSR-only render paths that bypass Statamic's preview iframe.

## Code

7. **Use the starter as baseline. Domain stuff lives in addons.** Never inline collections/globals/blocks specific to one project into the starter. Build an addon.
8. **Services for business logic, not templates.** Antlers/Blade is for rendering. Move logic to a Service class (see `/new-service`).
9. **Use the Statamic MCP for content ops where possible** (entries, terms, globals, blueprints, assets). File edits as fallback.
10. **`vendor/bin/pint --dirty --format agent`** after any PHP edit. Don't skip.
11. **`ddev exec php artisan test --compact`** must pass before claiming work done.

## Statamic stache

12. **Warm the stache after blueprint changes.** `php please stache:warm` (or `/cache-bust`). Otherwise the editor sees stale field structures.
13. **In production**: stache is warmed automatically on deploy (see `/deploy` post-deploy hooks). Don't run `php please stache:warm` manually on prod unless debugging.
14. **`STATAMIC_GIT_ENABLED=true` in production** — content edits in the CP commit to git on the server. Treat the server's git as a source of truth that local must sync from (`/sync-content`).

## Editor roles

15. **Two-role default**: Admin (everything) + Editor (only collections opened by active addon, no Globals/Nav/Taxonomies/Assets mgmt/Fields/Tools). Strip rules in `app/Providers/AppServiceProvider.php::customizeNav()`.
16. **Don't grant Editor access to fields management.** If they need it, they need an Admin role; don't blur the line.

## When a rule seems to be in the way

The rule is not in the way. The work is. Find a path that respects the rule. If you genuinely think a rule should be overridden for this project, propose it in the project `CLAUDE.md` explicitly — do not silently violate it.
