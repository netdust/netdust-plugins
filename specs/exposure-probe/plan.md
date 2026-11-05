# exposure-probe Implementation Plan (plan 1 of 2: netdust-plugins, `netdust-devops`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `make health` ends with an Exposure section that reports, per environment, whether paths a server must never serve (log marker files, debug logs, `.env`, `.git/HEAD`, composer files) are publicly served, and exits non-zero when one is.

**Architecture:** One new vendored script, `dist/scripts/health-exposure`, holds the whole probe (classification, control request, input validation) so a test can drive it against a fixture server. `Makefile.netdust` gains a `_health-exposure` target that calls it and makes it the last command of `health`, so its exit status is the recipe's. Everything else in `health` is untouched.

**Tech Stack:** POSIX/bash, `curl`, PyYAML through `scripts/site`; tests in `tests/test-makefile.sh` against PHP's built-in server on 127.0.0.1.

**Spec:** `specs/security-checks/spec.md` (R1–R4). Plan 2 (`core-lint-gate`, ntdst-core) is independent and written after this one ships.

## Global Constraints

Not a WordPress project: the spec's own constraints, one line each.

- The probe sends one `HEAD` request per path per environment (a 405 or 501 is retried once as a `GET` with the body discarded), keeps no body, follows no redirect, sends a generic user agent and a short timeout (8 seconds), runs sequentially, and needs no SSH and no terminal. It runs against production.
- The default paths are exactly: `/app/logs/index.html`, `/wp-content/logs/index.html`, `/wp-content/debug.log`, `/app/debug.log`, `/.env`, `/.git/HEAD`, `/composer.json`, `/composer.lock`. `site.yml` adds paths under `health.deny_paths` and cannot remove a default.
- Classes: `served` = HTTP 200 on an environment whose control path does not also answer 200 (red); `not served` = 403, 404, 410 (green); `not conclusive` = any 3xx, 401, any 5xx, or a 200 on a catch-all environment (yellow); `unreachable` = no answer or timeout (yellow). An environment with no `url` prints one yellow line saying so.
- The control request is one random non-existent path per environment, sent first; if it answers 200 the environment is a catch-all.
- Exit status: `health` exits non-zero only when some environment shows `served`; the Exposure section runs last, as `_health-exposure`; every other section keeps exiting 0.
- Contacting only 127.0.0.1 in tests (the suite header says "contacts no server": it still contacts no remote one).
- `Makefile.netdust` recipe lines carry no backticks (`tests/test-makefile.sh` asserts it); `dist/scripts/*` is vendored with checksums by `make devops-update`.
- Release: `netdust-devops` 0.14.0 in `plugin.json`, `.claude-plugin/marketplace.json` and `dist/VERSION`, agreeing (`tests/test-marketplace.sh`); `netdust-wp` 1.4.1 in its `plugin.json` and the marketplace, carrying the `wp-infra` fix already on `main` plus its pointer to `make health`. Merge and push are Stefan's.

## Threat model

**Assets.** The correctness of a security signal (a false green is worse than no probe); the site's availability (the probe must not hammer a site); the operator's shell (the probe reads values from `site.yml` into a command).

**Attacks.**
1. A hostile or mistyped `site.yml` value (`url`, a `health.deny_paths` entry) injects shell syntax into the recipe → values are passed as quoted arguments to `curl`, never to `eval` or `sh -c`; a path must match `^/[A-Za-z0-9._~/%-]*$` and a url `^https?://[A-Za-z0-9._:/@%~-]+$`, else the entry is skipped with a yellow line.
2. A redirect or an auth wall or a catch-all site reads as "not served" and the exposure goes unseen → 3xx, 401 and 5xx are `not conclusive`, a 200 on a catch-all environment is `not conclusive`, an unreachable site is yellow, never green.
3. A large `deny_paths` list turns `health` into a request flood → at most 20 added paths are probed (the rest named and skipped), one request in flight, 8-second timeout.
4. The probe follows a redirect to an internal address (SSRF through a redirect) → no redirect is followed.
5. The probe's own output leaks what it found → it prints the path and the class, never a body.

**Mitigations and where they live.** 1: `scripts/health-exposure` `valid_path()` / `valid_url()` and the quoted `curl` call. 2: `classify()` and the control request. 3: the `MAX_EXTRA=20` cap. 4: `curl` without `-L`. 5: `-o /dev/null`.

**Deferrals.** A server that serves a path only to some clients (an IP allow-list, a header) is not seen; the probe sees what an anonymous client sees. A path outside the list is not probed: the list is the product, and `health.deny_paths` is how a project extends it.

## Simplest design

The simplest design is a few `curl` lines inside the `health` recipe. That puts the classification, the control request and the input validation in a Makefile recipe nobody can unit-test, which is the shape that let the log directory sit open. So the probe is a script a test can call directly, and the Makefile only calls it.

## First working version

Task 1: `bash dist/scripts/health-exposure`, run from a project root that has `scripts/site` and a `site.yml`, prints one line per path per environment and exits 1 on a served path. Stefan can run it from `~/Sites/netdust` before the wiring task exists.

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| Probe script | `scripts/health-exposure` (stdout, exit status) | integration · `tests/test-makefile.sh`, section `── health: exposure ──` · `bash tests/test-makefile.sh` | none — no screen |
| Wiring into `health` | `make health`, `make _health-exposure` | integration · `tests/test-makefile.sh`, same section · `bash tests/test-makefile.sh` | none |
| Docs, evals, release | skill text, `evals/`, version files | `tests/test-marketplace.sh` (versions agree) and `tests/run.sh` · `bash tests/run.sh` | none |

## Review Focus

1. A site that answers 200 for every path never produces `served`: the control path makes it `not conclusive` — Task 1 (`catch-all`).
2. A 301, a 401, a 500 and an unreachable host are each yellow, never green and never red — Task 1.
3. A `HEAD` the server answers 405 is retried as `GET` and a served path behind it is still caught — Task 1.
4. A hostile `deny_paths` entry (spaces, a quote, `;`, `$(…)`, a path not starting with `/`) is skipped and never reaches a shell; 25 added paths probe 20 and name the rest — Task 1.
5. An environment with no `url`, and a project with no `deny_paths` key at all, both run without error — Task 1.
6. `make health` exits 1 when only the Exposure section is red and 0 when only Drift or Patch-gone is red — Task 2 (the delivery seam: the status survives `make`).
7. The defaults cannot be removed: `deny_paths` containing a default does not duplicate it, and nothing in `site.yml` shortens the list — Task 1.

---

### Task 1: The probe script

**Files:**
- Create: `plugins/netdust-devops/dist/scripts/health-exposure`
- Modify: `plugins/netdust-devops/tests/test-makefile.sh` (new section before `── first bring-up: files before the database ──`)

**Interfaces:**
- Consumes: `scripts/site` (prints one list item per line; exits 1 on a missing key), run from the project root; `curl`.
- Produces: `scripts/health-exposure`, no arguments; stdout: per environment a heading `<env>  <url>` then one line per path `  <path>  <class>` (classes as in Global Constraints); exit 0, or 1 when any path is `served`. Environment variable `SITE` overrides the `scripts/site` path, as the Makefile's `$(SITE)` does.

- [ ] **Step 1: Write the fixture and the failing tests** in the new section. Fixture: a router file under `$WORK/exposure/router.php` for `php -S 127.0.0.1:<free port>`, started in the background (port chosen by binding port 0 through PHP, or by scanning from 18080) and killed in a trap; it answers by path: `/app/logs/index.html` 200 empty; `/composer.json` 301 to `/`; `/.env` 401; `/composer.lock` 403; `/.git/HEAD` 405 on `HEAD` and 200 on `GET`; `/app/debug.log` 500; everything else 404; and in `CATCHALL=1` mode (a second server instance) every path 200. The fixture `site.yml` is a copy of the suite's `$P` fixture with `environments.staging.url` set to `http://127.0.0.1:<port>`; a second copy points at the catch-all port; a third has an unreachable url (`http://127.0.0.1:1`) and an environment with no `url`. Tests, each asserting on stripped stdout and the exit code:
  - `testServedPathIsRedAndFailsTheExit`: `/app/logs/index.html` shows `served`, exit 1.
  - `testNotServedIsGreen`: `/composer.lock` shows `not served` (403) and `/wp-content/debug.log` shows `not served` (404).
  - `testRedirectAuthAndServerErrorAreNotConclusive`: `/composer.json` (301), `/.env` (401) and `/app/debug.log` (500) each show `not conclusive`.
  - `testHeadRefusedIsRetriedAsGet`: `/.git/HEAD` shows `served` although `HEAD` was answered 405.
  - `testCatchAllSiteIsNeverServed`: against the catch-all instance every path is `not conclusive` and the exit is 0.
  - `testUnreachableIsYellowNotGreen`: the unreachable environment shows `unreachable` and exit 0.
  - `testEnvironmentWithoutUrlSaysSo`: a line naming the environment and `no url`, exit 0.
  - `testHostilePathsAreSkipped`: `health.deny_paths` with `"/a b"`, `"/x;id"`, `"/$(id)"`, `"no-slash"` and `"/ok"` prints a skipped line for the first four, probes `/ok`, and creates no file or process (assert `$WORK/exposure/pwned` does not exist after an entry `"/x;touch $WORK/exposure/pwned"`).
  - `testMoreThanTwentyAddedPathsAreCapped`: 25 added paths probe 20 and print the names of the skipped five.
  - `testAddedPathIsProbedAndDefaultsStay`: an added `/extra.txt` appears after the eight defaults; a `deny_paths` entry equal to a default is not probed twice; a project with no `health` key at all lists exactly the eight defaults.
- [ ] **Step 2: Run** `bash plugins/netdust-devops/tests/test-makefile.sh`. Expected: the new section FAILS (script not found).
- [ ] **Step 3: Create `scripts/health-exposure`.** Signatures in the file: `valid_path()`, `valid_url()`, `fetch(url, path)` printing the HTTP status (`curl -sS -o /dev/null -w '%{http_code}' -I --max-time 8 -A 'netdust-health' -- "$url$path"`, retried once without `-I` as `GET` on 405 or 501, `000` when curl fails), `classify(code, catchall)` printing one of the four classes. Per environment: print the heading, probe the control path first (`/__exposure_control_$RANDOM$RANDOM`), then the defaults, then the added paths (valid, de-duplicated against the defaults, at most 20). No `eval`, no `sh -c`, every expansion quoted. Colours as the Makefile's (red `\033[31m`, green `\033[32m`, yellow `\033[33m`). The final exit status is 1 when any line was `served`.
- [ ] **Step 4: Run** `bash plugins/netdust-devops/tests/test-makefile.sh`. Expected: the new section PASSES and every earlier section still does. Quote the summary line.
- [ ] **Step 5: Run it for real, read-only:** `cd ~/Sites/netdust && bash ~/Projects/netdust-plugins/plugins/netdust-devops/dist/scripts/health-exposure`. Expected: both environments' log markers `not served` (the fix of 2026-11-05) and exit 0; quote the output. If a path shows `served`, stop and report it to the reviewer, do not fix a server.
- [ ] **Step 6: Commit:** `git add plugins/netdust-devops/dist/scripts/health-exposure plugins/netdust-devops/tests/test-makefile.sh && git commit -m "feat(devops): health-exposure — the probe for paths a server must not serve"`.

### Task 2: Wire it into `health`

**Files:**
- Modify: `plugins/netdust-devops/dist/Makefile.netdust` (the `health` recipe ends with a call to `_health-exposure`; a new `_health-exposure` target after `_health-disk`; the `health` line in `help`)
- Test: `plugins/netdust-devops/tests/test-makefile.sh` (same section)

**Interfaces:**
- Consumes: `scripts/health-exposure` (Task 1).
- Produces: `make _health-exposure` (runs the script, prints a `Exposure — paths a server must not serve` heading in `$(BLUE)`, and ends with a one-line fix hint when the script exits non-zero); `make health` whose last command is `@$(MAKE) --no-print-directory _health-exposure`.

- [ ] **Step 1: Write the failing tests:** `testHealthExitsOneWhenExposureIsRed`: `make _health-exposure` against the served fixture exits 1 and prints the hint naming `location ^~ /app/logs/ { deny all; return 404; }` and "restart Nginx" and "make health"; `testHealthExitsZeroWhenOnlyAnotherSectionIsRed`: `make health` against a fixture where the exposure URL answers 404 for everything and the ssh stub reports drift (the existing stubs) exits 0; `testHelpListsExposure`: `make help` names exposure on the `health` line.
- [ ] **Step 2: Run** `bash plugins/netdust-devops/tests/test-makefile.sh`. Expected: FAIL (`_health-exposure` has no rule).
- [ ] **Step 3: Implement** the target and the last line of `health`; no backtick in any recipe line; the help line reads `"ledger, server drift, guards, topology, patched files, exposed paths"`.
- [ ] **Step 4: Run** `bash plugins/netdust-devops/tests/run.sh`. Expected: all three suites pass; quote the final line.
- [ ] **Step 5: Commit:** `git add plugins/netdust-devops/dist/Makefile.netdust plugins/netdust-devops/tests/test-makefile.sh && git commit -m "feat(devops): make health ends with the exposure probe and exits non-zero on a served path"`.

### Task 3: Docs, the eval, the release

**Files:**
- Modify: `plugins/netdust-devops/skills/devops/SKILL.md` (the health paragraph near line 140), `plugins/netdust-devops/templates/site.yml.tmpl` (a commented `health.deny_paths` example beside `health.markers`), `plugins/netdust-devops/dist/VERSION`, `plugins/netdust-devops/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (both entries), `plugins/netdust-wp/skills/wp-infra/SKILL.md` (the Logs paragraph points at `make health`), `plugins/netdust-wp/.claude-plugin/plugin.json`
- Create: `plugins/netdust-devops/evals/devops-exposure-probe-2026-11-05-cases.json`

**Interfaces:**
- Produces: one eval case `exposure-served-is-a-failure` in the suite's shape (`id`, `skill`, `skill_path`, `query`, `signature`): the query is a session that ran `make health env=production` and sees `/app/logs/index.html` `served`; the signature is: reports it as a failure of the site (not healthy), gives the `location ^~ /app/logs/ { deny all; return 404; }` rule and the restart, re-runs `make health` to verify, and does not hand-edit the server outside Ploi or the Makefile.

- [ ] **Step 1: Edit the docs.** The `devops` skill's health paragraph names the Exposure section, the eight defaults, `health.deny_paths`, and that `health` now exits non-zero on a served path; the template gets the commented example; `wp-infra`'s Logs paragraph ends with "`make health` probes this on every environment".
- [ ] **Step 2: Bump versions:** `dist/VERSION` and both `netdust-devops` version fields to 0.14.0, the marketplace description gains a `0.14.0:` line at its head (the style of the existing ones), `netdust-wp` 1.4.1 in `plugin.json` and the marketplace with a `1.4.1:` line naming the `^~` rule, the restart-after-save note and the `make health` pointer.
- [ ] **Step 3: Run** `bash plugins/netdust-devops/tests/run.sh`, expected all pass including `test-marketplace.sh` (versions agree); and `bash plugins/netdust-devops/tests/test-makefile.sh` once more. Quote both final lines.
- [ ] **Step 4: Commit:** `git add -A plugins/netdust-devops plugins/netdust-wp .claude-plugin/marketplace.json && git commit -m "release: netdust-devops 0.14.0, netdust-wp 1.4.1 — the exposure probe in make health"`. Push the branch; do not merge.

## Hand-over

Stefan merges and pushes; the installed copies pick the release up through `scripts/sync.sh` and `make devops-update` in each project, which is how the probe reaches the fleet. The first real run is `make health` in `~/Sites/netdust` and `~/Sites/daan` after the update; their log markers must read `not served`. Plan 2 (`core-lint-gate`) is independent.
