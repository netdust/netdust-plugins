# WordPress review checklists — vendored

Source: https://github.com/jorgerosal/wordpress-skills — commit `8c964424d05ba34b3ea5641f7181d4c13829e06f` (`main`)
Files: `claude-skills/wp-security-review/SKILL.md`, `claude-skills/wp-migration-upgrade-review/SKILL.md`
License: MIT — Copyright (c) 2026 Jorge Rosal (full text: the source repo's `LICENSE`)
Vendored: 2026-09-06. Re-vendor by bumping the hash above in a reviewed commit (plan threat model item 4).
Keys: `SEC-nn` / `MIG-nn` are assigned here (upstream keys sections, not items); cite them in findings.
Trimmed: items restating `wp-security`'s four pillars (sanitize-by-type and escape-by-context tables) are dropped — that skill owns them.

## wp-security-review

Severity: CRITICAL = exploitable unauthenticated, or leads to breach / RCE / privilege escalation.
WARNING = needs authentication or specific conditions. INFO = defense in depth.
Context: admin-only code lowers one level; WP-CLI / cron need no nonce; REST authorizes by
`permission_callback`, not nonces; public-facing code is highest.

### Plugin / theme PHP files
- SEC-01 WARNING — no `defined( 'ABSPATH' ) || exit;` at the top → direct file access
- SEC-02 CRITICAL — `eval(` (CWE-95)
- SEC-03 CRITICAL — `exec(` / `shell_exec(` / `system(` / `passthru(` reachable by user input (CWE-78)
- SEC-04 CRITICAL — `base64_decode( $_` → encoded payload execution
- SEC-05 CRITICAL — `unserialize( $_` → object injection (CWE-502)
- SEC-06 WARNING — `$_GET[` / `$_POST[` / `$_REQUEST[` read without `sanitize_*` (CWE-20)
- SEC-07 CRITICAL — `include` / `require` / `*_once` on a `$_` value → path traversal / inclusion (CWE-22)

### Form handlers (`admin-post.php`, `admin_post_*`) — all three, or it is a vulnerability
- SEC-08 CRITICAL — no `wp_verify_nonce()` / `check_admin_referer()` (CWE-352)
- SEC-09 CRITICAL — no `current_user_can()` (CWE-862); wrong capability for the action (CWE-863)
- SEC-10 WARNING — input not sanitized (CWE-20)

### AJAX handlers (`wp_ajax_*`, `wp_ajax_nopriv_*`)
- SEC-11 CRITICAL — state change without `check_ajax_referer()` (CWE-352)
- SEC-12 CRITICAL — no `current_user_can()` where a capability is required (CWE-862)
- SEC-13 CRITICAL — `wp_ajax_nopriv_*` without a nonce → public endpoint, no CSRF protection
- SEC-14 WARNING — `$_POST` used without `sanitize_*` (CWE-20)
- SEC-15 WARNING — `wp_send_json()` echoing user input unescaped → JSON injection

### REST endpoints (`register_rest_route`)
- SEC-16 CRITICAL — no `permission_callback` (CWE-862)
- SEC-17 CRITICAL — `'permission_callback' => '__return_true'` on a write route (public GET: not a finding)
- SEC-18 WARNING — permission callback without `current_user_can()` (CWE-863)
- SEC-19 WARNING — `$request->get_param()` consumed without validation (CWE-20)
- SEC-20 INFO — cookie-authenticated client: verify it sends `X-WP-Nonce`

### Database (`$wpdb`)
- SEC-21 CRITICAL — `$wpdb->query(` / `get_results(` / `get_var(` / `get_row(` with concatenation or interpolation (CWE-89)
- SEC-22 CRITICAL — user input present, no `$wpdb->prepare()` (CWE-89)
- SEC-23 WARNING — `LIKE '%{$term}%'` inside `prepare()` → `$wpdb->esc_like()` first
- SEC-24 WARNING — double-preparing an already prepared string
- not findings: `{$wpdb->prefix}` in a query; hardcoded admin-only SQL with no user input

### Templates / output
- SEC-25 CRITICAL — `echo $` / `print $` without an escaper (CWE-79)
- SEC-26 CRITICAL — `<input value="<?php echo $` → `esc_attr()`; `<a href="<?php echo $` → `esc_url()`; `<script>` with PHP values → `wp_json_encode()` / `wp_localize_script()` (CWE-79)
- SEC-27 WARNING — rich HTML output without `wp_kses()` / `wp_kses_post()`

### File uploads
- SEC-28 CRITICAL — `move_uploaded_file(` instead of `wp_handle_upload()` (CWE-434)
- SEC-29 CRITICAL — upload with no `current_user_can()` (CWE-862)
- SEC-30 WARNING — no MIME validation / no `wp_check_filetype_and_ext()` → type spoofing (CWE-434)
- SEC-31 INFO — no file size limit

### JavaScript (`*.js`, `*.jsx`)
- SEC-32 WARNING — `fetch()` / `$.ajax()` to the REST API without `X-WP-Nonce` (CWE-352)
- SEC-33 WARNING — `$.post( ajaxurl, …)` without a nonce in the data (CWE-352)
- SEC-34 CRITICAL — `innerHTML = userInput` / `dangerouslySetInnerHTML` (CWE-79); `eval(` (CWE-95)

### Config constants (`wp-config.php`; on Bedrock `config/application.php` + `.env`)
- SEC-35 INFO — `DISALLOW_FILE_EDIT`, `FORCE_SSL_ADMIN`, `DISALLOW_UNFILTERED_HTML`, `DISALLOW_FILE_MODS` unset
- SEC-36 CRITICAL — default `AUTH_KEY` … `NONCE_SALT` values

### Not findings (upstream SEC-24)
- no nonce in a WP-CLI command; `wp_kses_post()` on trusted content; admin-only hardcoded SQL;
  `current_user_can()` inside `permission_callback`; `esc_html( get_the_title() )`;
  `update_option()` after a capability check; `__return_true` on a GET; `sanitize_callback` on `register_setting()`

### Quick detection (upstream SEC-20)
```bash
grep -rn "\$wpdb->\(query\|get_results\|get_var\|get_row\)(" . | grep -v prepare   # SEC-21/22
grep -rn "echo \$_\|print \$_" . ; grep -rn "<?php echo \$" . | grep -v "esc_"      # SEC-25/26
grep -rn "eval(\|exec(\|shell_exec(\|system(\|passthru(\|base64_decode(\$_\|unserialize(\$_" .  # SEC-02..05
grep -rn "move_uploaded_file(" .                                                     # SEC-28
grep -rn "register_rest_route" . | grep -v "permission_callback"                     # SEC-16
grep -rn "include \$_\|require \$_\|include_once \$_\|require_once \$_" .           # SEC-07
grep -rn "\$_GET\[\|\$_POST\[\|\$_REQUEST\[" . | grep -v "sanitize_"                 # SEC-06/14
grep -rn "wp_ajax_nopriv_" .                                                         # SEC-13
grep -rn "admin_post_\|wp_ajax_" . | grep -v "current_user_can"                      # SEC-09/12
```

## wp-migration-upgrade-review

Severity: CRITICAL = no version guard, destructive write without checks, long-running upgrade on
page load. WARNING = no batching, no rollback consideration, untracked partial state. INFO =
clearer registry or logging. Surface to locate: activation hook, `version_compare` routine,
background backfill, manual repair tool.

### Safety first
- MIG-01 CRITICAL — no version guard
- MIG-02 CRITICAL — destructive operation not explicit and justified
- MIG-03 WARNING — routine not idempotent (a re-run changes state again)
- MIG-04 WARNING — large data work not chunked

### Versioned upgrade routines
- MIG-05 CRITICAL — upgrade logic runs on every request without `version_compare`
- MIG-06 WARNING — several migration steps but no ordered upgrade map
- MIG-07 INFO — no central migration registry

### Schema changes
- MIG-08 CRITICAL — raw `CREATE TABLE` / `ALTER TABLE` without care for existing installs
- MIG-09 WARNING — `dbDelta()` without table-version tracking
- MIG-10 INFO — schema and data migration not separated into phases

### Data backfills
- MIG-11 CRITICAL — full-table backfill on a normal page load
- MIG-12 WARNING — no batching or progress option
- MIG-13 WARNING — no retry, not resumable
- MIG-14 INFO — no Action Scheduler / WP-CLI runner

### Data flow
- MIG-15 WARNING — option rename / copy / delete in an order that loses data on failure
- MIG-16 WARNING — no upgrade completion flag
- MIG-17 — every finding states whether it risks production timeouts, partial state, or irreversible loss (upstream MIG-23)

### Quick detection (upstream MIG-21)
```bash
rg -n "version_compare|get_option\s*\(.*version|update_option\s*\(.*version" . -g '*.php'   # MIG-01/05
rg -n "dbDelta|CREATE TABLE|ALTER TABLE|DROP TABLE" . -g '*.php'                            # MIG-08/09
rg -n "register_activation_hook|upgrader_process_complete" . -g '*.php'                     # surface
rg -n "wp_schedule_event|as_schedule_single_action|WP_CLI" . -g '*.php'                     # MIG-14
rg -n "delete_option|rename|migrate|backfill" . -g '*.php'                                  # MIG-15
```
