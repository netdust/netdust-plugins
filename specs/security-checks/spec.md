# security-checks — the exposure probe in `make health`, and a lint gate for ntdst-core

**Status:** DRAFT 2026-11-05, awaiting Stefan's approval. Replaces the Studio row `wp-security-gates`.
**Two plans, two repos:** `exposure-probe` (netdust-plugins, `netdust-devops`) and `core-lint-gate` (ntdst-core).
**Source of the scope:** the handoff of 2026-11-05 (`netdust-studio/specs/studio-checks/handoff.md`), cut down the same day after measuring what already exists.

## Why

The handoff asked for PHPCS security, Psalm taint and `composer audit` as per-feature gates. Reading the repos showed most of that is already there: wp-starter's gate runs PHPCS with `WordPress.Security` and `WordPress.DB` over our own mu-plugins and themes, and `audit:deps` runs `composer audit` (and `ship` runs the full gate). What is missing is two things the same day proved matter or leave untested:

- **No check that a deployed site does not serve what it must not.** On 2026-11-05 a one-line probe found `netdust.be` and `daan.be` (and both staging copies) serving the NTDST log directory `web/app/logs/` to the public: the documented Nginx rule existed only as text in a skill, written in a form that did not even work. Nothing in the flow would have caught it.
- **ntdst-core's own gate has no lint.** Core's `phpcs.xml` exists and phpcs is a dev dependency, but `composer gate` never runs it (`syntax`, `test`, `guard`, `audit:deps` only). Run once on 2026-11-05 it reports 328 findings: about 220 are PSR style noise core can never satisfy (global `NTDST_*` class names are deliberate), about 109 (89 errors, 20 warnings) are `WordPress.Security`/`WordPress.DB`/compatibility findings, clustered in `admin/MetaboxGenerator.php` (41), `api/Data.php` (18), `api/FieldTypes.php` (12), `core/Bootstrap.php` (11) and `core/Pages.php` (8).

## Requirements

### Plan `exposure-probe` (netdust-plugins, `plugins/netdust-devops`)

**R1 — `make health` gains an Exposure section.** For every environment in `site.yml` that has a `url` (`environments.<e>.url`, already read by `e2e` and `smoke`), it sends one `HEAD` request per path to `<url><path>` and reports each: `served` (HTTP 200, red), `not served` (403, 404, 410: green), `not conclusive` (yellow: any 3xx, 401, a 5xx, or a 200 on a site that answers 200 for everything), `unreachable` (no answer or timeout, yellow). A 405 or 501 on `HEAD` is retried once as a `GET` with the body discarded. To tell a real 200 from a catch-all site (a single-page app, a soft 404), one control request goes to a random non-existent path per environment: if the control answers 200, every 200 on that environment is `not conclusive`. An environment with no `url` prints one yellow line saying so, never silence. No body is kept, redirects are not followed, the user agent is generic, the timeout is short. It needs no SSH and no terminal, and runs against production, as the rest of `health` does.
*Source: Stefan, 2026-11-05: "is this extra security step needed or am I building extra steps for little gain" → "i follow your recommend" (the exposure probe in make health, option A); the paths, the status classes, the control request and the no-url line are my calls from the builder check — approved: pending.*

**R2 — The default path list.** `/app/logs/index.html` and `/wp-content/logs/index.html` (the marker file the NTDST logger drops beside its logs, so a 200 means the directory is served), `/wp-content/debug.log`, `/app/debug.log`, `/.env`, `/.git/HEAD`, `/composer.json`, `/composer.lock`. `site.yml` may add paths under `health.deny_paths`; it cannot remove a default. The marker is real: the logger drops an empty `index.html` (and an `.htaccess`) into its log directory on its first write, so a site where it never wrote has no log to leak, and on 2026-11-05 `netdust.be` and `daan.be` each served that 0-byte marker (`last-modified` 2026-09-22) until the rule landed. The probe asks for the marker file, not the directory, because a directory request answers 403 or 404 whether or not its files are served.
*Source: invented — approved: pending.*

**R3 — A `served` result fails `make health`.** Exposure runs last, as its own sub-make (`_health-exposure`, as `_health-disk` is), so the recipe's exit status is its status: non-zero when any environment shows `served`, and zero otherwise, `not conclusive` and `unreachable` included. Every other section keeps exiting 0, as today (a grep of the harness found nothing that reads `health`'s exit code). A machine (the later Studio checks, a deploy script) can read it. A line says which environment and path, and what to do (add the `^~` deny rule, restart Nginx, verify).
*Source: invented — approved: pending.*

**R4 — The probe is tested and documented.** `tests/test-makefile.sh` gains cases against a local fixture server (PHP's built-in server with a router script, PHP being already required; it answers 200, 404, 301, 401 and 405 for named paths and has a catch-all mode), the fixture `site.yml` giving the `url`; `_health-exposure` is called directly, as the disk tests call theirs; the `devops` skill's health paragraph names the section; `dist/VERSION` is bumped; one eval case in `evals/` covers "a production site serving its log directory is reported, not passed". `netdust-wp:wp-infra`'s Logs paragraph points at `make health` as the verification.
*Source: global CLAUDE.md, "a lesson that changes a skill's behaviour ships with an eval case"; the rest invented — approved: pending.*

### Plan `core-lint-gate` (ntdst-core)

**R5 — Core's lint is security-only.** `phpcs.xml` drops PSR12 and keeps `WordPress.Security`, `WordPress.DB` and `PHPCompatibilityWP`, the posture wp-starter's gate already uses for our own code ("PSR-12 style debt is not a reason to leave unescaped output unscanned"). The file list is unchanged. Measured on a scratch copy of 5.7.0 without PSR12: 109 findings, 89 errors and 20 warnings, in 12 files. "Zero" means errors and warnings both, since phpcs exits 1 on either. WPCS, PHPCompatibilityWP and the composer installer plugin are already dev dependencies, so `composer.json` does not change.
*Source: Stefan, 2026-11-05, "1: security-only ruleset, gated" (the core lint choice); the ruleset detail is invented — approved: pending.*

**R6 — Every remaining finding is fixed or annotated with a reason.** The ~108 security/DB findings are triaged to zero. A finding that is a real hole (unescaped output a user can influence) is fixed as a bug with a failing test first. A finding that is a false positive (framework-built HTML, an exception message that is never output, the advisory lock's `$wpdb` calls in `RunLog.php`) gets an inline `// phpcs:ignore <sniff> -- <reason>`, core's existing convention (`admin/MetaboxGenerator.php:2102`). No whole-sniff or whole-directory exclusion in the ruleset. A finding that cannot be classified is treated as real. An annotation on framework-built HTML cites where the escaping happens (`file:line`), and the whole-branch review's `security-sentinel` reads every annotation. A real hole is fixed and listed in the hand-over to Stefan; it is not a stop.
*Source: Stefan, 2026-11-05, "1: security-only ruleset, gated"; the no-blanket-exclusion rule and the triage rules are my calls from the builder check — approved: pending.*

**R7 — Lint joins `composer gate`.** The gate becomes `syntax`, `lint`, `test`, `guard`, `audit:deps` (cheapest first). The wiring is the plan's last task, added when the count is zero, so `main` and the branch's own gate are never red. Core's `ARCHITECTURE-INVARIANTS.md` header names it where it lists what the gate runs, if it does.
*Source: "1: security-only ruleset, gated"; the order is invented — approved: pending.*

**R8 — Release.** A patch release (5.7.1) if triage changes shipped code; docs and config only, none is needed beyond the merge. `CHANGELOG.md` lists any real escaping fix.
*Source: invented — approved: pending.*

## Non-goals

- **Psalm taint analysis.** Parked: PHPCS security already runs, the framework centralizes routes and data, and the setup cost (stubs, taint annotations for ntdst-core's sanitizers, a baseline, upkeep) is high against an unmeasured gain. If it is ever wanted, a one-hour spike on one site's mu-plugins decides it first.
- The daily CVE check (`baseline-vulnerability-check`), mutation testing and test pruning (`studio-checks`), the Studio panels.
- Fixing exposures the probe finds on other servers: the probe reports, the fix is the operator's.
- Changing wp-starter's gate or making the gate updatable through `make devops-update`. The gate reaches new scaffolds only; vendoring it is its own spec when wanted.
- Baseline's gate (it has its own) and any other package's.

## Anti-goals

A probe that reports green because it never reached the site (an unreachable site is yellow, never green). A lint gate that is green because the ruleset was widened to exclude what it found.

## Approaches

**Where the probe lives.** (A) a section of `make health` in netdust-devops, read-only, per environment, with a default list: chosen, because `health` is already the per-environment check that needs no terminal and runs on production, and a default list protects projects that would never write their own. (B) a per-project `@smoke` check in `specs/CHECKS.md`: rejected, no central default, and the gap it must catch is exactly the one nobody wrote a check for. (C) a tier in the site's gate: rejected, a local DDEV Nginx says nothing about the real server.

**What core's lint does.** (1) security-only ruleset, triaged to zero, gated: chosen. (2) an on-demand audit, never gated: rejected, an audit nobody runs finds nothing the next time. (3) skip: rejected, core's escaping is the framework every site runs.

Stefan chose A and 1 on 2026-11-05.

## Left to the builder

The probe's exact wording, colours and the `curl` flags; whether the probe lives in `health` itself or in a helper script under `scripts/`; the order the triage walks the files; whether false positives in `MetaboxGenerator.php` justify one annotation per line or a short block.

## Success

`make health env=production` on netdust.be and daan.be shows the Exposure section green; pointed at a fixture that serves a log marker file it exits non-zero and names the path; `composer gate` in ntdst-core runs lint and is green, with every annotation carrying a reason; the review's triage list shows how many findings were real.
