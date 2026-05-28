# Netdust WordPress Rules

**WordPress-specific rules.** Universal rules (no `.env` commits, no `vendor/` edits, no direct-to-`main`, etc.) live in `netdust-core/RULES.md` — they apply here too.

**Violating the letter of these rules is violating the spirit of these rules.**

## WordPress core + dependencies

1. **Never edit WordPress core or `web/wp/`** (or `app/wp/` for custom-app projects). Customizations go in `mu-plugins/`, the child theme, or a Composer-installed custom plugin.
2. **Never bundle plugin or theme `.zip` files into the repo.** All dependencies via Composer + WPackagist. Premium plugins via private Composer repository (Satis, vendor's own feed, etc.). See `bedrock-composer`.
3. **Never edit `web/wp-config.php`** — Bedrock supplies it. Per-environment config goes in `config/environments/<env>.php`.

## Security pillars

4. **Never use raw `$_GET` / `$_POST` / `$_REQUEST` / `$_COOKIE` / `$_SERVER` values.** Sanitize on input, escape on output, verify nonce, check capability. See `wp-security`.
5. **Never build dynamic SQL via concatenation or interpolation.** `$wpdb->prepare()` always. See `wp-database`.
6. **Never set REST `permission_callback => '__return_true'`** unless the endpoint is genuinely public and idempotent.

## Standards

7. **WPCS via PHPCS.** `composer lint` before commit. CI enforces.
8. **i18n always.** All user-facing strings through `__()` / `_e()` / `esc_html__()` with the project text domain. No hardcoded English (or Dutch).
9. **Prefix everything.** Custom actions, filters, functions, options, post types, taxonomies, meta keys → `netdust_*`, `stride_*`, or project-specific prefix. No bare `wp_*` overrides.
10. **Namespaces preferred** in plugins (`Netdust\StrideLMS\…`, `Stride\Modules\Edition\…`). Procedural style allowed in theme template files only.
11. **ntdst-core conventions** apply to all new Netdust WP work — Modules / Handlers / Admin / Integrations / Contracts / Domain / Infrastructure layering. See `ntdst-architecture` and `ntdst-patterns`.

## Database

12. **Custom tables only when post meta cannot fit** (high write volume, structured relational data, query patterns post meta cannot serve). Default to post meta.
13. **Transients for any expensive computation.** `wp_cache_get` / `wp_cache_set` if the value is reusable mid-request.
14. **Migrations: WP-CLI commands, or a migration plugin. Never manual SQL on production.**
15. **Never flush Redis globally** on a WP site with object-cache exclusions — see `netdust-core/RULES.md` rule #10. Especially VAD Vormingen and other LMS sites.

## Deploy (WP-specific additions; universal rules in netdust-core)

16. `.gitignore` excludes: `web/wp/`, `web/app/uploads/`, `vendor/`, `web/app/mu-plugins/bedrock-autoloader.php`, plus stack defaults (`node_modules/`, `.env`, etc.).
17. **`composer install --no-dev --optimize-autoloader` on every deploy.** Bedrock requires the optimized autoloader.

## When a rule seems to be in the way

The rule is not in the way. The work is. Find a path that respects the rule. If you genuinely think a rule should be overridden for this project, propose it in the project `CLAUDE.md` explicitly — do not silently violate it.
