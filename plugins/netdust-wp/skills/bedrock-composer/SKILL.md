---
name: bedrock-composer
description: Use when working on a Bedrock-structured WordPress project (web/wp, web/app, .env, composer.json with roots/wordpress) — installing plugins or themes, modifying composer.json, editing .env or .env.example, configuring mu-plugins, scaffolding a new Bedrock site, debugging "plugin not found" or "wp not loading" issues. Triggers on file edits to composer.json, composer.lock, .env*, wp-cli.yml, mu-plugins/*, web/app/plugins/*, web/app/themes/*. Activates on keywords bedrock, roots/wordpress, wpackagist, mu-plugins, autoloader, env, .env, dotenv, composer install, composer require, composer update. Symptoms include receiving a plugin zip from a client, needing to add a premium plugin, editing wp-config.php (you should not), wondering whether to commit something. Do not skip when "just this one zip", when the client insists, when in a hurry, or when "the .env edit is just for local."
---

# Bedrock + Composer

**Violating the letter of these rules is violating the spirit of these rules.**

Bedrock's whole point is reproducible, dependency-managed WordPress. Every shortcut around Composer is technical debt that surfaces months later as "why is this plugin a different version on staging than prod?"

## Layout (Bedrock)

```
project/
├── composer.json              ← all dependencies declared here
├── composer.lock              ← committed, source of truth
├── .env                       ← NEVER commit
├── .env.example               ← committed, placeholder values
├── wp-cli.yml                 ← optional, sets --path=web/wp
└── web/
    ├── wp-config.php          ← Bedrock-supplied, do not edit
    ├── index.php              ← Bedrock-supplied, do not edit
    ├── wp/                    ← WordPress core (Composer-managed, gitignored)
    └── app/                   ← what wp-content is in vanilla WP
        ├── plugins/           ← Composer-managed, gitignored
        ├── themes/            ← Composer-managed if from WPackagist; custom themes committed
        ├── mu-plugins/        ← custom must-use plugins (committed)
        └── uploads/           ← user content, gitignored
```

## Non-negotiables

1. **Never commit a plugin or theme `.zip`.** All deps via Composer + WPackagist or a private Composer repository.
2. **Never commit `.env`.** Only `.env.example` with placeholder values.
3. **Never edit `web/wp/`.** It is WordPress core — Composer overwrites on every `composer install`.
4. **Never edit `wp-config.php`.** Bedrock supplies it; per-environment config goes in `config/environments/<env>.php`.
5. **`composer.lock` is committed.** It is the only way staging and prod see the same code.
6. **All `wp-cli` runs with `--path=web/wp`** (or via a `wp-cli.yml` that sets it). Without this, WP-CLI cannot find core.

## Quick reference

### Add a WPackagist plugin

```bash
composer require wpackagist-plugin/<plugin-slug>
```

WPackagist mirrors plugins from wordpress.org. Most free plugins are available.

### Add a premium plugin (Composer-installable)

Some premium plugin vendors (ACF Pro, Gravity Forms, WP Rocket) publish a Composer package gated by license:

```bash
composer config repositories.acf composer https://connect.advancedcustomfields.com
composer require advanced-custom-fields/advanced-custom-fields-pro
```

License key goes in `.env` (and `.env.example` as placeholder), read in `composer.json`'s authentication config.

### Add a premium plugin (zip-only, no Composer feed)

When the vendor only ships a zip:

1. Set up a private Satis or Packagist.com mirror, OR
2. Use the [`junaidbhura/composer-wp-pro-plugins`](https://github.com/junaidbhura/composer-wp-pro-plugins) bridge, OR
3. (Last resort) host the zip on the project's own private S3 + add a Composer repository with type `package` pointing at it.

**Do not** drop the zip in `web/app/plugins/` or commit it to the repo.

### .env workflow

- `.env.example` has every variable the project needs, with placeholder values (`DB_NAME=local_db`, `WP_SITEURL='${WP_HOME}/wp'`, etc.).
- `.env` (gitignored) has the real values per machine.
- On new clone: `cp .env.example .env` then fill in.
- For prod: Ploi/Combell injects env vars via their dashboard; `.env` is not deployed.

### mu-plugins

- Files at `web/app/mu-plugins/*.php` autoload (no activation required).
- Subdirectories require Bedrock's autoloader: `web/app/mu-plugins/bedrock-autoloader.php` (do NOT commit — it's Composer-generated; gitignored).
- Best pattern: a single `web/app/mu-plugins/netdust-loader.php` that `require_once`s subdirectory entry files explicitly. No autoloader needed; clearer load order.

### .gitignore (minimum for Bedrock)

```
.env
web/wp/
web/app/uploads/
web/app/mu-plugins/bedrock-autoloader.php
web/app/plugins/
web/app/themes/<wpackagist-themes>/   # custom themes are committed
vendor/
```

## One excellent example

Adding ACF Pro the right way:

```bash
# 1. Add the ACF Pro Composer repo
composer config repositories.acf composer https://connect.advancedcustomfields.com

# 2. Add HTTP basic auth (license key as the username, anything as password)
composer config http-basic.connect.advancedcustomfields.com "$ACF_LICENSE_KEY" "$(php -r 'echo getenv("WP_HOME");')"

# 3. Require the plugin
composer require advanced-custom-fields/advanced-custom-fields-pro

# 4. Commit composer.json + composer.lock (NOT the plugin code, NOT the license)
git add composer.json composer.lock
git commit -m "deps: add ACF Pro via Composer"
```

`.env.example` gets an `ACF_LICENSE_KEY=` line. Each environment fills in its own key. The plugin code lives in `web/app/plugins/advanced-custom-fields-pro/` (gitignored). On every deploy, `composer install --no-dev --optimize-autoloader` pulls it down.

## Rationalization table

| Excuse | Reality |
|---|---|
| "Client sent a zip, just commit it for now" | "For now" is forever. Next time the plugin updates, no one remembers it was hand-installed. Set up the Composer feed once; benefit forever. |
| "Quick `.env` edit on prod via SSH" | Now staging and prod diverge silently. Configure env vars via Ploi/Combell dashboard, not by editing `.env` on the server (which often doesn't exist there anyway). |
| "Composer install is slow, let me just download the plugin" | A slow install runs once per deploy. Hand-installed plugins create drift forever. |
| "I'll just edit `web/wp/wp-config.php` to add this constant" | `composer install` overwrites it. Per-environment config goes in `config/environments/<env>.php`. |
| "It's just my own private fork of the plugin" | Fork → push to your own GitHub → Composer `vcs` repository pointing at it. Fork-in-the-repo is bundling-by-another-name. |
| "The CI is failing because Composer can't reach the premium feed" | Set up an HTTP basic auth env var in CI. The auth-via-`.env` pattern works locally; CI needs its own credential. |
| "I'll commit `vendor/` so deploys don't need composer install" | Now the repo is 100MB and you lose Composer's auto-optimization. Run `composer install --no-dev --optimize-autoloader` on deploy instead. |
| "We can't use Composer for this client's site, they're on shared hosting" | Build the artifact locally or in CI; rsync the post-build directory. Don't run Composer on the shared host. Bedrock still works as an authoring layout. |
| "It's just a one-line `.env` change" | One-line changes that disappear into untracked files are how prod and staging diverge. Use version-controlled config (`config/environments/<env>.php`) for code config; use the platform's env-var dashboard for secrets. |
| "Following the spirit not the letter" | The letter is the spirit. Every dependency through Composer, every secret through env, every WP core through `web/wp/`. |

## Loophole closures

- **"Drop the plugin in `web/app/mu-plugins/` instead of `plugins/`, problem solved"** → No. mu-plugins is for custom code you own, not for stashing third-party plugins. The plugin's updater won't work, and you've lied to the project layout.
- **"Add it to `composer.json` but also keep the zip in `setup/` for the next dev"** → No. The Composer entry is the source of truth. Setup docs in README link to the vendor, not to a cached zip.
- **"Set `WP_PLUGIN_DIR` to `web/app/legacy-plugins/` for this one"** → No. Two plugin dirs is two sources of truth. Migrate the plugin to Composer or accept the technical debt cost.
- **"Disable Composer for this one project, full vanilla WP"** → Fine, but then you're not on Bedrock and this skill doesn't apply. Don't half-disable.
- **"I'll add the plugin via Composer but keep my old copy in `plugins/` just in case"** → No. `composer install` will overwrite `plugins/<slug>/`. The "just in case" copy is a ghost.

## Common mistakes

- Committing `composer.lock` *changes* without running `composer install` first — the lockfile reflects what you actually have. Sync them.
- Running `composer update` when you meant `composer install`. `update` rewrites the lockfile; `install` applies it. Use `update <package>` for a targeted bump.
- Forgetting `--no-dev` in production. Ships dev tools (phpunit, debug-bar) to prod.
- Forgetting `--optimize-autoloader` in production. PSR-4 autoload is significantly slower without it.
- `composer require` without specifying a constraint → caret-current is picked. Be explicit (`composer require foo/bar:^2.0`) so the lockfile reflects intent.
- WP-CLI commands without `--path=web/wp` → fails with "This does not seem to be a WordPress installation." Add a `wp-cli.yml`:
  ```yaml
  path: web/wp
  ```
- `.env` committed by mistake → rotate every secret in it before unstaging. The git history has it forever.
- New developer clones → forgets `composer install` → sees "wp not loading" because `web/wp/` is empty.

## When in doubt — three questions

1. **Is this a dependency?** → Composer it. Always.
2. **Is this a secret?** → `.env` (gitignored) for local, platform env vars for deploy.
3. **Am I about to edit a file Bedrock supplied (`web/index.php`, `web/wp-config.php`, `web/wp/*`)?** → Stop. Find the right config location.

## See also

- `wp-infra` (this plugin) — WP-CLI + Bedrock-specific Makefile patterns
- `dev-stack` (netdust-core) — generic dev-loop and the 9 deploy methods
- `wp-security` for the broader rule on never committing secrets.
- [Bedrock docs](https://roots.io/bedrock/docs/)
- [WPackagist](https://wpackagist.org/)
- `red-tests.md` in this skill folder.
