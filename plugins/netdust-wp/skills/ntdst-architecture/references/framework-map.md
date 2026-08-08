# ntdst-core — what each layer decides, and what has bitten

**This file replaces eleven API-reference files and two code templates.** They carried 4,400 lines of
method catalogue that drifted; everything below is the part that does not drift — why each layer
exists, the rule it enforces, and the trap that has actually cost someone a day.

**Read source for signatures.** Each section names the file that owns the surface. `git grep` the
symbol; do not trust a remembered signature, and do not trust another site's copy (see the fork note
in `SKILL.md`).

---

## Boot & DI — `core/Bootstrap.php`, `core/Container.php`

**Decides:** whether a service exists, when it boots, with what config, and how its dependencies are
supplied.

- **Init belongs in the constructor.** A service's constructor calls `init()`, which registers hooks.
  A separate `register()` method that the framework is expected to call is not the contract.
- **Enable/disable precedence is deliberate and ordered, most-restrictive first:** metadata (code) →
  filter (runtime) → DB option (UI). A service disabled in code cannot be re-enabled from the UI.
- **Register bindings before features are ready.** After the framework's features-ready point, only
  tests should mutate the container.
- **Gate admin-only work with `is_admin()` at the top of `init()`, not with an `admin_only` metadata
  flag.** The flag gates *bootstrap*, so the class is never instantiated outside admin — and any
  frontend code that later wants to call in (a badge in a frontend toolbar, an AJAX endpoint, a CLI
  command) then cannot. Runtime gating is the safer default and keeps the gate visible where the
  hooks are registered, while the constructor still wires DI.
- **Sub-services are plain classes** — no interface, no `metadata()`, no config entry. They are
  internal implementation, registered in the *parent's* `init()`. Admin controllers usually go one
  step further and are plain `new`, because nothing else in the codebase needs to retrieve them.
- **Bad wiring fails loudly, by design.** A binding to a class-shaped string that does not exist
  throws rather than silently returning the string. An unknown parameter key throws so typos surface
  at the call site instead of being silently autowired. A dependency cycle raises with the full chain
  rather than an opaque max-nesting fatal — **fix a cycle with events or hooks for loose coupling,
  never by injecting both ways.**
- **Global helpers are wrapped in `function_exists()` guards** because several plugins may each ship
  a copy of ntdst-core in the same request. Double-load tolerance is intentional; preserve it.

**Traps**

- **The service slug is derived from the class name, and the derivation is lossy.** It collapses
  acronyms, but stripping `Service` strips **every** occurrence, and it is many-to-one — two classes
  can collide on one slug and silently share an enable filter and a DB option.
- **`metadata()['name']` does not win.** The enable-check warms the slug cache from the class name
  before the metadata-aware call happens, so the metadata argument is never read. Renaming a service
  in `metadata()` renames nothing that matters.
- **Two config-filter surfaces exist and do not meet** — see the trap list in `SKILL.md`. The one
  Bootstrap actually fires is `ntdst_service_{slug}_config` / `_enabled`; a project-prefixed filter a
  service applies to itself is invisible to `config['services']['overrides']`.
- **Namespaced services are not auto-discovered.** Discovery matches `*Service.php` at the discovery
  root plus enabled sector directories only. A namespaced class in a subdirectory must be listed in
  the bootstrap config or it silently never loads.
- **Re-binding does not invalidate already-resolved consumers.** A test that needs fresh resolution
  must flush the container.
- **A one-argument registration is not the same as passing `null`.** The implementation distinguishes
  them by argument count: one argument registers the ID as its own class; an explicit `null` stores
  `null`.
- **A factory receives the container only when its first parameter is untyped or typed as the
  container.** Any other typed first parameter means "I don't want the container" and the factory is
  called with no arguments — a silent behavioral fork.
- **Wrong priority band is a real defect class.** Roughly: 1–5 critical infrastructure, 6–9 core
  framework, 10–14 standard features, 15–19 content, 20–29 UI, 30+ optional. A UI feature at
  priority 3 is sitting in infrastructure territory and will boot before what it depends on.

**Config file name is layer-dependent:** `plugin-config.php` at a mu-plugin root, `theme-config.php`
for a theme. Both in one project is fine when both bootstrap. Do not invent a third name, and do not
call it `config.php` — that collides with YOOtheme.

## CPT registration — the wrapper is the contract

**Never call `register_post_type()` directly, anywhere.** Bypassing the data layer's wrapper breaks
four things at once: field definitions no longer drive validation, metabox, and query building; the
repository contract (`ntdst_data()->get(POST_TYPE)`) only works for wrapper-registered types; the
post-type constant stops being reusable; and the type stops being discoverable by convention.

A CPT lives in a dedicated `*CPT` class that owns its registration and exposes the `POST_TYPE`
constant. **It is not a service** — it is a static config holder called from the owning service's
`init()`. The constant lives on the class, not on the service.

→ Registration defaults, taxonomies, and the fail-closed rules: `ntdst-data`.

## Router — `core/Router.php`

**Decides:** which callback owns a URL or a template, and how a route's return value becomes output.

- **Routes match in registration order** — register specific before generic.
- **A route alone is enough for a custom URL.** The router matches the request URI on
  `template_include`, so no rewrite rule is required — verified against a live consumer that
  registers routes and no rewrite rules. Older framework docs claimed both were always needed; they
  were wrong. Add a rewrite rule only when you need WordPress query vars populated for that URL, and
  flush on activation only.
- **Redirects default to the safe, same-host form.** The external opt-in is explicit, because route
  URLs are routinely derived from request input and the default closes open-redirect.
- **A Router JSON route is same-origin only.** It runs on the front-end template pipeline and has no
  CORS or preflight handling — fine for a same-origin fetch, wrong for a real API.

**Traps**

- **Do not loop `when()`.** Every call registers another `template_include` filter that then runs on
  every request.
- **The blank-page footgun:** a callback that forgets to `return` implicitly returns `null`, which
  **exits the request**. A route that "isn't running" and renders blank — check for a missing
  `return` first.
- **Query-string parameters are not passed to the callback.** Read them from `$_GET`.
- **URL building silently drops keys that match no placeholder** — they are not appended as a query
  string. Values are URL-encoded, so a slash becomes `%2F` and the route still matches.
- **`ntdst_router()` fires at `template_include` — too late to rewrite query vars.** Pre-query
  interception is a legitimate raw `parse_request` hook; that is not drift.
- CLI and test SAPIs have no request URI or method; the guards exist so wp-cli and PHPUnit don't fail.

## Response & templates — `api/Response.php`

**This one file declares two classes** — the response object and the template loader. A
file-per-class assumption here produced a wrong plan premise. Grep the symbol.

**Decides:** the JSON envelope, and where a template resolves from.

- **Response is the single owner of the success/error envelope.** Every output surface routes through
  it.
- **Two error shapes coexist deliberately — do not "unify" them.** One shape serves the JS API
  client, the other serves REST consumers. Merging them silently breaks one consumer set. This has
  been attempted.
- **Template resolution is confined to declared base directories via `realpath`.** Template names are
  hardcoded strings today; the confinement exists so that a future caller passing a user-influenced
  name cannot climb out with `../../../`.
- **`template()` defers (returns self, for routing), `render()` outputs and exits, and the
  string-returning variant is for emails and AJAX HTML.** Choosing the wrong one is the single most
  common Response mistake.
- **The template loader is the home for page/page-data resolution.** Forwarders on Response that
  merely called through to it were deleted — a forwarder is a second surface that drifts
  independently, and these two drifted twice in one week.

**Traps**

- **Path and located-file caches are static and shared across instances.** If paths change at
  runtime, clear the cache explicitly. The registry only grows — there is no remove-path.
- **Download/inline filenames are header-injection hardened** (CRLF and double-quotes stripped,
  RFC 5987 encoding for non-ASCII). Do not hand-roll a `Content-Disposition` header.
- **JSON encoding failure returns a structured error body**, not the silent empty response it used to.

## Same-origin API actions — `api/Endpoints.php`

**Decides:** whether a caller may dispatch an action at all, before any handler sees it.

The framework ships a **router** — origin check, rate limit, nonce, auth gate, dispatch — and no
opinion about anyone's data. Actions belong to the services that know what their rows mean.

- **Default-deny.** The anonymous-action list ships empty and the framework never adds to it.
- **"Public" means only "no auth required to mint a nonce".** A public handler must still treat every
  input as untrusted and must not assume a caller identity.
- **An empty result is a valid success.** "No handler registered" and "handler returned nothing" are
  different outcomes; a zero-result search is a success, not a 404.
- **A capability failure returns a `WP_Error`.** Older behavior wrapped it as an array, which looked
  like a success body to the client.
- **Listing users by email or login is a PII leak** and requires a user-listing capability. Any
  search surface over users, in any copy, inherits this rule.

→ Registration, the fail-closed capability floor, and the raw-filter bypass: `ntdst-data`.

**Traps**

- **The CSRF referer check compares against a trailing slash**, so an attacker-controlled subdomain
  like `example.com.evil.com` cannot pass a prefix match on `https://example.com`. Preserve the slash.
- **Rate limiting is keyed per `(user, action)` when logged in and per `(ip, action)` when not** —
  IP-only keying produces false positives for everyone behind shared NAT (offices, schools, mobile
  carriers). **Per-action limits are mandatory for sensitive operations**: without one, an attacker
  can hammer a magic-link-style action to spam a victim's inbox and exhaust the SMTP quota.
- **The allowed-origins filter widens the same-origin CSRF gate. It does not turn this into a
  cross-origin API.**
- `X-Forwarded-For` is honored only when the remote address is a trusted proxy.

## Cross-origin REST — **stride only, not ported**

A REST registrar and a CORS policy exist in **one** site's copy and were never ported. Do not assume
them. The decisions are recorded because they are the correct answers when this is next built, and
because the WordPress quirks below are true of WordPress itself and never drift:

- **Do not reach for the same-origin action dispatcher cross-origin.** An anonymous WP nonce is a
  shared, non-origin-bound token that authenticates nothing for a cookie-less cross-origin caller —
  zero real security, while looking like it has some.
- **A per-route permission callback is required; there is no default.** A missing or non-callable
  permission means the route is *not registered*. A public-by-design route supplies its own explicit
  callable.
- **Misconfiguration throws; requests never throw.** Bad config is a programmer error caught at
  registration, so the route never goes live. A malicious request is an ordinary denied response.
- **`WP_Error` messages reach the wire** — log the detail, return something generic.

**The three WordPress-core quirks any cross-origin work must handle:**

1. **Core's own CORS handler reflects any `Origin` and sets `Access-Control-Allow-Credentials:
   true`** — the reflection-plus-credentials anti-pattern. A policy must register *after* it, always
   remove the credentials header, and on a non-match **remove** the allow-origin header so core's
   reflection cannot survive. Match byte-exactly on full `scheme://host[:port]` — never substring,
   never case-folded, never `*`; literal `'null'` must never match.
2. **Core double-invokes `permission_callback`** per request (once for the `Allow` header). Memoize
   per route — a side-effectful permission callback, such as a rate-limit counter, otherwise runs
   twice. Memoize **per route, not globally**, or one route's verdict leaks to another.
3. **The REST server JSON-decodes the request body at depth 512 *before* `permission_callback`
   runs.** Body-size and depth caps must be enforced on the pre-dispatch hook — the only one that
   runs earlier. Gate the depth check on JSON content-type so form bodies aren't wrongly rejected.

**Baseline exemption for reviewers:** controllers that predate a registrar and call
`register_rest_route()` directly are accepted baseline, not a pattern to copy for new work.

## Logging — `services/Logger.php`

**Decides:** where an event goes, and what it is allowed to contain.

- **The database handler is opt-in, and the reason is the point.** Every error written to the DB
  triggers a post insert plus N meta writes plus the whole save cascade — exactly the wrong load
  profile during an incident. Production errors must not generate write storms. With it off, errors
  still reach the file log and PHP's error log; they do not disappear.
- **Never log raw user-submitted values.** Log identifiers and structural metadata — a post ID, not
  the failing payload. Users paste personal data into form fields, and a plaintext log is the wrong
  place for it.
- Errors bypass batching for immediate visibility; both paths append with an exclusive lock so
  concurrent writes are safe.
- **Handler failures are caught as `\Throwable`, not `Exception`, and reported through the raw PHP
  error log to avoid recursion.** A custom handler throwing a `TypeError` must not crash the request.

**Deployment trap, and it is the one that actually leaks:** the dropped `.htaccess` is **inert on
Nginx**. On Bedrock the content directory is inside the webroot, so **log files are publicly
addressable** unless the server config denies them. Any Nginx host — Ploi, Combell, anything — needs
an explicit deny rule for the logs path. The `.htaccess` and index file are Apache-only
defense-in-depth, not the control.

## Mail — `services/Mailer.php`

**Decides:** what may be attached, and what may reach a header.

- **Attachments are allow-listed to the uploads directory** (extensible by filter); anything else is
  refused and logged. Without this, a caller passing user input could attach `wp-config.php` or
  `/etc/passwd`. **Write to uploads first, then attach.**
- **CRLF is stripped from subject, from-address and every header.** Core's own protection varies by
  WordPress version, and a CRLF in any of these smuggles `Bcc:` or `Set-Cookie:`.
- **The escaping boundary is explicit:** the built-in default template escapes scalar substitutions,
  so user-controlled values cannot inject HTML — but **in a full template file, escaping is the
  template author's job**. Message content is treated as HTML by contract.
- **Do not pattern-match on rendered error output** to detect a missing template. Template existence
  is pre-checked across the search paths; older code string-matched the error HTML and that coupling
  was removed deliberately.
- The mailer helper returns a **new instance per call**, not a singleton — relevant when reusing a
  fluent chain.
- Calling `wp_mail()` directly bypasses logging, templating, and all of the hardening above.

## Admin UI — `admin/`

**Decides:** how a model's edit screen renders, and **who may write its fields**.

Admin UI has its own directory: `api/` is data and transport, `services/` is infrastructure, and the
metabox generator and relation field live in neither. The write-authorization gate is here.

- **Name this convergence point by class and method, never by path.** It survived a whole-directory
  move completely untouched for exactly that reason.
- **Escape defensively at render even for developer-controlled config keys** — a typo'd or
  third-party type registration should not be able to open an XSS path.
- **A decode failure must not log the payload.** Users paste personal data into fields.
- **Read access to an error notice is gated by the same predicate as write access**, so read ⊆ write
  by construction — and the gate sits *before* a destructive read.

## Theme — `core/Theme.php`

**Decides:** theme wiring, and nothing else.

**A method belongs on `Theme` iff its subject dies when you switch themes.** A CPT, a taxonomy or an
API action outlives a theme switch and belongs to its owner. A hook binding, a template path, a
template helper does not, and belongs here.

The wrappers that violated this — post-type registration, taxonomy registration, API-action
registration, and the whole module DSL — were **retired**; their owners are the data layer and the
API-action helper. Most other copies still have them.

**The fluent chain was kept deliberately.** The first attempt at this deleted the whole surface,
having diagnosed chainability as the god-object smell. That was wrong: the defect was *incoherence* —
a facade over five unrelated subsystems — not chaining. Retained: hook and filter binding,
conditional wiring, template path, the routing shortcuts, mixins, and config/assets.

**Traps**

- **The theme object is instantiated once.** It is a wrapper over the core helpers, not a service.
- **Do not run hook names through `sanitize_key()`.** It strips `/` and `.`, so binding one of the
  framework's own namespaced filters through the facade registered a name nothing ever fires. This
  was a live bug.
- The module concept is retired; mixins supersede it.

## Standalone plugins — deliberately *not* this architecture

A standalone WordPress plugin (its own container, its own provider pattern) is a **different
architecture** from an ntdst-core service, on purpose. Its one real invariant is the two-phase
provider contract:

- **`register()` — bindings only. No hooks, no side effects.**
- **`boot()` — runs after *all* providers have registered. Hooks go here.**

Baseline: PHP 8.1+, `declare(strict_types=1)`, PSR-4, `type: wordpress-plugin`, GPL-2.0-or-later.
