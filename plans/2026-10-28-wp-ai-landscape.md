# Research — WordPress + AI landscape vs the ntdst stack

**Date:** 2026-10-28
**Repo:** `github.com:netdust/netdust-plugins`, filed under `plans/` as the brief behind `2026-10-28-abilities-hardening-gate-plan.md`
**Class:** research, no implementation.
**Status:** RESEARCH — read the plan next; this is its evidence.
**Origin:** cloud session 2026-10-28 (Stefan: "research repos on git that have the same philosophy… a base for all websites, cleans up WordPress, makes it easier to work with"). Written from the live READMEs and dev notes fetched that day; star counts and versions are as of that day.

---

# WordPress + AI landscape vs the ntdst stack (2026-10-28)

Baseline for comparison: ntdst-core (wrap WordPress, never replace it; features
enter only with a named consumer; invariants enforced by grep), ntdst-baseline
(switchable housekeeping modules, zero site values, five-question admission
test), netdust-plugins (Claude Code marketplace: gates on superpowers, skills,
drift reviewer, memory layers, specs per feature).

## Verdict

Nobody has published the same thing: a layered composer mu-plugin framework with
written admission tests AND a gated AI harness on top. What exists is partial
overlap in three camps:

1. The official WordPress AI surface (Abilities API in core since 6.9, MCP
   Adapter, Playground + Blueprints, WordPress/agent-skills). This is where
   "AI builds the site" is being standardised. The ntdst stack is one small
   bridge away from plugging into it.
2. The Roots camp (Bedrock/Acorn/Sage) which has both a layered composer stack
   and an AI move (acorn-ai, kivo-wise, Claude WP Kit, Substrate). Acorn is
   Laravel-in-WordPress, the opposite of philosophy.md §1, so it is a source
   of ideas, not a dependency.
3. Skill packs and harnesses for Claude Code. None has a plan/gate/review loop;
   netdust-gates is ahead of all of them on discipline.

## Tier 1: act on these

### WordPress/agent-skills (GPL-2.0, 2.3k stars, 18 skills, WP 7.0+)
https://github.com/WordPress/agent-skills
You pin d87ee69 (2026-09-06) and install 4 of 18. Added since or beyond your set:
wp-abilities-api, wp-abilities-audit, wp-abilities-verify, blueprint,
wp-playground (now a router over blueprint/CLI/debug/website refs), wp-env,
wp-block-themes, wp-block-development, wp-interactivity-api, wp-performance,
wpds, wp-plugin-directory-guidelines, wordpress-router, wp-project-triage.
wp-abilities-audit: inventories REST controllers, traces permission_callback to
current_user_can, proposes one ability per intent with readonly/destructive/
idempotent annotations, writes a planning doc, refuses to copy __return_true
gates. Directly applicable to ntdst_rest().
Repo has eval/scenarios and a validator (metadata only, scenarios manual).

### WordPress/mcp-adapter + Abilities API
https://github.com/WordPress/mcp-adapter
https://developer.wordpress.org/news/2026/02/from-abilities-to-ai-agents-introducing-the-wordpress-mcp-adapter/
Abilities are private by default; meta.mcp.public exposes one. Default server
ships discover / get-info / execute meta-tools. Transports: HTTP under
/wp-json/mcp/..., STDIO via WP-CLI. Requires WP 6.9+. 0.6/0.7 as of Aug 2026.
Fail-closed by default matches core's "route names no permission registers as
is_user_logged_in" posture.
Stride already hand-rolls ReadAbilityRegistrar / WriteAbilityRegistrar
(ntdst-core specs/field-types/ground-truth.md:174). That is the named consumer
core's brake requires.

### galatanovidiu/abilities-rest-adapter (MIT, 0 stars, 47 commits)
https://github.com/galatanovidiu/abilities-rest-adapter
wp_register_ability_from_rest_route(): wraps an existing route, dispatches via
rest_do_request(), derives input/output schema from the route, uses the route's
own permission check (extra check can only restrict), requires destructive +
idempotent annotations on non-readonly, reshapes collections with X-WP-Total.
"Standalone now, core later." Exactly the one-surface shape INV-2 demands: no
second door. Too small to depend on; the design is worth copying into
ntdst_rest() as a route option.

### Automattic/wordpress-agent-skills: create-wp-site (beta, 120 stars)
https://github.com/Automattic/wordpress-agent-skills
Claude Code plugin + Cowork plugin + Studio MCP server. /quick-build and
/design-site: describe site -> review specs -> pick 1 of 3 design directions ->
style tokens -> page layouts -> full block theme -> deploy to local Studio.
README: "not production-ready". Studio-bound (not DDEV), block-theme only
(not YOOtheme). The spec-first shape is yours already; the "three design
directions before building" step is worth lifting into ntdst-yootheme's
Figma -> LESS -> sections loop.

### @wp-playground/mcp + blueprint skill
https://make.wordpress.org/playground/2026/03/17/connect-ai-coding-agents-to-wordpress-playground-with-mcp/
https://make.wordpress.org/playground/2026/07/28/one-playground-three-workflows-consistent-agent-guidance-across-surfaces/
claude mcp add --transport stdio --scope user wordpress-playground -- npx -y @wp-playground/mcp
16 tools (sites, execute_php, request, files). SQLite, no persistent state.
Blueprints are the declarative site spec; the blueprint skill owns the JSON.
Your artifact-gate spec already allows Playground as the shake-out browser for
standalone packages. Natural fit for ntdst-core's own gate: boot core +
baseline from a Blueprint and run the shake-out with no DDEV.

## Tier 2: same philosophy, read for ideas

### inpsyde/modularity (GPL-2.0, Syde, active, PHP 7.4+)
https://github.com/inpsyde/modularity
PSR-11 modules: ServiceModule (services), FactoryModule, ExtendingModule
(decorate another module's service, type-targeted with @instanceof<T>),
ExecutableModule (run(), returns bool). Package::new($props)->addModule()->boot().
Same "modules each switchable" idea as baseline, generic container.
Idea to borrow: ExtendingModule. Baseline has no way for one module to
decorate another's service; everything goes through filters.

### generoi/gds-security-hardening (mu-plugin, 0 stars, updated 2026-08)
https://github.com/generoi/gds-security-hardening
13 unconditional modules: XmlRpc, Rest (no JSONP, no read->write override, no
discovery), ApplicationPasswords (manage_options only, no remote auth flow),
Headers (HSTS, nosniff, XFO, Referrer-Policy), Uploads (PDF/SVG/EPS/HEIC/TIFF/
macro-Office editors+ only), UserEnumeration, Passwords (12 min), Credentials
(revoke app passwords + sessions after reset), Roles (pin default_role),
Version (generator + salted ?ver), ContentSecurityPolicy (wp-admin limited,
wp-login nonce-strict), Filesystem (no .htaccess rewrite), TwoFactor (opt-in).
Stance is the inverse of baseline's ("takes no per-site configuration; a per-
site answer belongs in the site's own mu-plugins"). Tests are real-WP PHPUnit +
Playwright on wp-env. Use as a checklist diff against SecurityService.

### Roots: acorn-ai, acorn-prettify, Log1x/poet
https://github.com/roots/acorn-ai  (MIT, PHP 8.4+, WP 6.9+, Acorn 5)
  wraps laravel/ai; abilities as container-resolved classes; make:ability,
  ability:list; mcp.public meta hands off to mcp-adapter. Not an MCP server.
https://github.com/roots/acorn-prettify (MIT) = Soil's successor; clean-up,
  nice-search, relative-urls; config/prettify.php toggles. Baseline head_cleanup.
https://github.com/Log1x/poet (MIT, 219 stars) = config/poet.php declares post
  types, taxonomies, blocks, patterns, palette; false unregisters. Closest
  published analogue to core's declared model, but Blade/Acorn bound.
Roots forum feedback on Substrate (always-on MCP for the stack): "the stack is
CLI-native; skills are lighter than an always-on MCP server". Validates the
skills-first choice in netdust-wp.

### johnbillion/extended-cpts (GPL-2.0, ~1k stars, maintainer-wanted)
https://github.com/johnbillion/extended-cpts
Wrap-not-replace done right: admin_cols, admin_filters, sortables, query vars,
archive overrides, taxonomy meta boxes, generated labels. Check what the Data
layer's register() misses on the admin side.

## Tier 3: harnesses to compare with netdust-gates / netdust-wp

- hekivo/kivo-wise (ex superpowers-sage, MIT, 215 commits): Roots Claude Code
  plugin; roots-router + roots-triage write .roots-stack.json; 22 skills;
  read-only reviewer agents; hooks guard protected files, remind cache clears,
  flag AI attribution before commit. No plan/gate loop.
- alessioarzenton/claude-code-wp-toolkit "Claude WP Kit" (GPL-3.0, 6 commits):
  bin/init.sh generates .claude/; Figma bridge; hooks block dangerous bash and
  scan staged secrets; Stop prompt to update memory.md. No gate.
- digitalnodecom/substrate: MCP server for Roots (Acorn 5). See above.
- respira-press/agent-skills-wordpress (MIT, 55 skills): audit/optimise/migrate
  between page builders; depends on Respira's commercial MCP (220+ tools).
- mralaminahamed/wp-dev-skills (MIT, 19 skills): plugin lifecycle, release,
  .org submission, Freemius. Pairs with the official set.
- jorgerosal/wordpress-skills: already vendored (review checklists).

## Dead or not worth time

- Automattic/wordpress-mcp: archived 2026-01-19 (superseded by mcp-adapter).
- Automattic/agent-skills: archived 2026-02-01 into WordPress/agent-skills.
- mcp-wp/ai-command (wp ai): archived 2026-03-18.
- WordPress/abilities-api standalone: archived 2026-02-05, lives in core.
- WordPress/wp-ai-client: deprecated; WP 7.0 ships wp_ai_client_prompt() and
  the Connectors screen. Any in-site AI feature should call that, not a vendor
  HTTP API.
- roots/soil: archived 2024 (use acorn-prettify).
- humanmade/altis: closed platform, no AI.
- alleyinteractive/mantle: Laravel-style replace (testkit is independent and ok).
- 10up/wp-scaffold: solid conventional scaffold, zero AI/agent content.
- wecodemore/wpstarter: PHP 7.1-era alternative to Bedrock.
- pollora/* (abilities, portcullis): Laravel-ish WP framework, PHP 8.3, 0 stars.
- WordPress Studio (Automattic/studio): Studio Code agent defaults to Sonnet 5;
  CLI dependency-free; relevant only if you leave DDEV.

## Recommended moves, in order

A. Bump bin/wp-upstream-skills.sh PIN and add wp-abilities-api,
   wp-abilities-audit, wp-abilities-verify, blueprint, wp-playground to SKILLS.
   Cheap, immediate.
B. Decide abilities in core: an 'ability' option on ntdst_rest() routes that
   registers wp_register_ability() from the route (dispatch through
   rest_do_request, permission = the route's, readonly from GET, destructive /
   idempotent declared or derived from verb), private unless mcp.public is
   named. Stride is the named consumer. Every netdust site becomes an MCP
   target with zero site code, INV-2 stays intact, and wp-abilities-verify
   becomes a gate check. Highest leverage item on this list.
C. Diff SecurityService against gds-security-hardening's 13 modules; admit what
   passes the five questions (ApplicationPasswords, Uploads, Credentials revoke,
   wp-login CSP look like candidates).
D. Lift the "three design directions before building" step from create-wp-site
   into ntdst-yootheme's workflow.md.
E. Add a Blueprint to ntdst-core and ntdst-baseline so the package gate can boot
   a real WordPress via Playground without DDEV.

---

# Addendum: the narrower lens — "a base for all websites that cleans up WordPress and makes it easier to work with"

## What exists publicly, grouped by what it is

### Cleanup / hardening mu-plugins (baseline analogs)
| Repo | Scope | Config model | Signals |
|---|---|---|---|
| vinkla/headache (MIT) | Broadest single cleanup: head tags, emojis, oEmbed, feeds->home, XML-RPC, users REST, comments off, attachment 404 + UUID slugs, block CSS, font library, roles removed, JPEG 100, noindex on non-prod, login tweaks | All-on, no filters, no constants | 141 stars, 103 commits; bundled by WordPlate |
| roots/acorn-prettify (MIT) | clean-up (7 switches), nice-search, relative-urls | config/prettify.php | 62 stars; Acorn 3+ |
| generoi/gds-security-hardening | 13 hardening modules (XML-RPC, REST, app passwords, headers, uploads, enumeration, passwords, credential revoke, roles, version, CSP, .htaccess, 2FA opt-in) | Unconditional by design; per-site answers belong in the site's own mu-plugins; 3 hooks | 0 stars, updated 2026-08, real-WP PHPUnit + Playwright |
| Instance-Studio/lumbermill instance-* | 8 hardening mu-plugins: login limiter, enumeration, headers, disable REST, force-active plugins, 2FA key guard, audit log, Simple History config | Filters, WP_ENV-aware (limiter + 2FA off in dev), "config lives in version control" | Reference set inside a Bedrock project, not a package |
| devgeniem/wp-geniem-project-bells-and-whistles (GPL-3) | 2 fixes | GENIEM_DISABLE_BELLS_AND_WHISTLES class list | 2 stars |
| innocode-digital/wp-normalize (MIT) | "disables probably unnecessary features" | undocumented | 1 star |
| Automattic/vip-go-mu-plugins (GPL-2) | Platform defaults for every VIP site: cache, security, perf, search, wp-cli | VIP-bound | 258 stars, 13.9k commits |
| Seravo/seravo-plugin (GPL-2) | Canonical URL + HTTPS enforcement, login logging, maintenance tooling | Host-bound | 40 stars |
| humanmade/hm-platform | S3, SES, Tachyon, Cavalcade, Batcache... | archived 2023-11 | dead |

### Zero-config single modules (one baseline module each)
- kovshenin/surge (GPL-3, 179 stars): disk page cache, "no configuration, no options", SURGE_ constants, DONOTCACHEPAGE, s-maxage / stale-while-revalidate, `wp surge flush`. ~ cache_headers.
- elightup/slim-seo (93 stars, 1.6k commits, commercial Pro): "no settings page, everything automatic" meta/OG/schema/sitemap/redirects/breadcrumbs; AI meta generation with own key. ~ seo + schema.

### DX layers (core analogs)
- timber/timber 2.x (MIT, 5.6k stars): Twig views + Post/Term/User wrappers; "meant to build a theme on", not a replacement; Composer-only.
- johnbillion/extended-cpts (GPL-2, ~1k stars, maintainer-wanted): declarative CPT/taxonomy with admin cols, filters, sortables, query vars.
- Log1x/poet (MIT, 219 stars): config/poet.php for CPT/tax/blocks/patterns/palette; Acorn-bound.
- inpsyde/modularity (GPL-2): PSR-11 modules; ExtendingModule is the idea baseline lacks.

### Whole-base boilerplates
- vinkla/wordplate v12 (MIT, 2.2k stars, PHP 8.4): Composer WP, .env, public webroot, WP Packages, mu-plugins on by default, headache + clean-image-filenames bundled, Vite + Tailwind, dump()/dd(), cleaner admin. The closest single-repo expression of "a base for all websites". The old wordplate/framework is archived.
- roots/bedrock: structure only; cleanup moved to acorn-prettify.
- 10up/wp-scaffold (GPL-2, 299 stars): structure + lint + build; no cleanup layer, no AI.

## Reading

1. The public world splits in two: zero-config all-on bundles (headache, Surge, Slim SEO, gds) and platform-bound bundles (VIP, Seravo, hm-platform). Nobody publishes configurable housekeeping as a composer package. The stars go to zero-config: WordPlate 2.2k, Timber 5.6k, headache 141 vs gds 0. Configurability is an agency need (many clients, one package), which is exactly why the agency bundles (Geniem, Genero, Instance Studio, Seravo) are each small and internal. Baseline is the same species as those, more complete than any of them.
2. Nothing in this space is AI-aware. headache, WordPlate, Surge, Timber ship no skills, no abilities, no CLAUDE.md. Slim SEO's AI is a meta-description button. The "base layer that ships with its own agent skills" slot is empty; netdust-wp already occupies it privately.
3. Use headache and gds as checklists against HeadCleanupService and SecurityService (attachment 404 + UUID slugs, font library off, auto-sizes off, users REST endpoint, app-password remote flow, upload MIME by role, credential revoke after reset, wp-login CSP). WordPlate is the benchmark for "what a base ships with" (Vite/Tailwind, dd(), clean admin). Timber only matters if you leave YOOtheme.
