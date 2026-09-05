# Artifact gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the harness's decisive gate from the diff to the artifact — a browser-driven, screenshot-backed shake-out the machine can refuse — and shrink review to the two reviewers with a record, while making "same as X" and "renders content" plan grammar, giving ntdst-baseline invariants and a pinned core, and sourcing WordPress knowledge from WordPress's own skill pack.

**Architecture:** Every new rule is an artifact property `bin/gate-check.py` checks (a new `--shakeout` mode over `specs/<feature>/shakeout.md`, three new plan/tasks checks) or a `bin/loop-check.py` FINISHED condition; the skill and agent texts cite those checks by name and restate nothing. One cluster runs in the `ntdst-baseline` repo; one adds an installer that pins `WordPress/agent-skills` by commit. No new hook, no new artifact type beyond the manifest that already existed informally.

**Tech Stack:** bare `python3` (gate-check, loop-check, the test modules under `tests/run.sh`), bash (`bin/wp-upstream-skills.sh`, `tests/test-*.sh`), markdown skills/agents/commands, Composer (`ntdst-baseline`), WP-CLI (`aaemnnosttv/wp-cli-login-command`), Playwright.

**Spec:** `specs/artifact-gate/spec.md`

## Global Constraints

- Marketplace SOURCE only (`~/Projects/netdust-plugins`), never the plugin cache; the baseline cluster runs in `~/Sites/ntdst-baseline` after `git pull --ff-only` to `f696124`.
- New checks are silent where their sections are absent: the existing `specs/*` corpus produces zero NEW findings except the FR-4 `Layer` WARN (spec AC-6).
- The manifest's Evidence cell never carries a credential (login link, token, app password) — FR-2/FR-3 and the threat model below.
- Skill text cites the mechanical check by exact name; no skill promises an enforcement the machine does not perform.
- Panel tables live in exactly two files: `skills/building/SKILL.md` and `commands/shakeout.md` (spec AC-10/SC-6).
- Versions at close: netdust-agent 0.27.0, netdust-wp 1.2.0, ntdst-baseline 2.5.0; `marketplace.json` synced (`tests/test-marketplace.sh` in netdust-devops and the plugin-version test pin it).

---

## Technical context

`gate-check.py` (2454 lines) is one file of `check_*(text, f: Findings)` functions over three shared parsers — `section_body()`, `parse_clusters()` / `parse_behaviour_clusters()`, `task_blocks()` — called in a fixed order from `run_checks(spec_dir)`; `main()` takes `spec_dir` and `--json` only. Tests are plain functions returning `(ok, desc)` tuples collected by `run()` in `tests/test_spec_gate_check.py`, executed by `tests/run.sh`; `_run(files)` writes a temp feature dir and runs the script as a subprocess. `loop-check.py` derives FINISHED at the all-boxes-checked branch (line ~219) from the ledger's suite-green sha. `shakeout-qa.md` declares `tools: Read, Grep, Glob, Bash, Skill` and `model: sonnet`; `test-author.md` already declares `Edit, Write`, so the frontmatter accepts them. `commands/shakeout.md` runs four steps (suite, shakeout-qa, panel, close). The manifest today is free-form prose under `specs/<feature>/shakeout.md` (Stride) or nowhere.

## Stakes

**Stakes: standard** — a wrong gate refuses or admits plans loudly and is reverted in one commit; a wrong skill text ships bad routing to the next session, visibly. The one auth-adjacent piece — the login recipe — is a documented procedure on DDEV/staging under the existing devops production floor, never code that runs on a server.

### Per-cluster stakes

| Cluster | Stakes | Why |
|---|---|---|
| A — the shake-out checker | **standard** | checker logic; a false refusal is loud, a false pass is what exists today |
| B — the spine texts and loop-check | **standard** | prose routing plus one FINISHED condition; every mechanical gate beneath holds |
| C — netdust-wp: access recipe, upstream, trim | **standard** | a procedure and an installer pinned by commit; the recipe is refused on production by the devops floor, and the mu-plugin it needs is a DDEV-only install |
| D — ntdst-baseline invariants + pin | **standard** | a doc, a script and a Composer constraint; a wrong pin fails `composer install` loudly on the next consumer update |
| E — the record | **low** | evals, versions, self-hosting lines |

## First working version

**Task:** T01
**Demonstrates:** a human writes a two-row manifest whose `browser` row says `pass` with no `Browser:` evidence, runs one command and watches the checker refuse it naming the row; adds `Browser: https://… · shakeout/af-1.png` with the file present and watches it pass. The gate that this spec exists for is real before any prose changes.
**Verify by:** `python3 plugins/netdust-agent/bin/gate-check.py --shakeout <fixture dir>` → exit 1 with a `shakeout-manifest` finding, then exit 0.

## Constitution check

Simplicity first: no new hook, no new script beyond one installer, no new artifact type — the manifest existed informally and gets a grammar. Every rule is a property the machine reads from a file; the texts point at the check. The panel change removes dispatches; the feature-test change removes a dispatch; drift moves rather than multiplies. Two things are added because they were missing, not because they are nice: the access recipe (the shake-out could not log in) and baseline's invariants doc (the auditor had nothing to run).

## Threat model [GATE]

**Assets:** (1) the magic login link / Playwright storage state / application password the shake-out uses; (2) the screenshots and the manifest, which are committed; (3) the skills installed from `WordPress/agent-skills` and the checklists vendored from `jorgerosal/wordpress-skills`, which future sessions read as instructions.

1. **Login recipe reachable on production** → an attacker with shell on a production host mints admin links. **Mitigation:** the companion `wp-cli-login-server` mu-plugin is installed by `bin/e2e.sh` on DDEV only and is never in `deploy.payload`; `wp-testing` states the recipe is valid on `WP_ENV != production` and cites the devops floor (`netdust-devops:devops` — a typed confirmation guards production, and the guard denies forged stdin). Verified by T07's grep: no `wp login` in any deploy-side script.
2. **Credential lands in git** → a magic link or app password in the manifest's Evidence cell or a screenshot of the login URL. **Mitigation:** FR-2 grammar takes the URL of the page AFTER login; T01's checker FAILs an Evidence cell matching `login=|token=|app[-_ ]password|storageState` (`shakeout-credential`); links expire (`--expires`, default 900 s) and `bin/e2e.sh` invalidates at teardown (`wp login invalidate --all`).
3. **Application password outlives the run** → a wire-flow credential stays valid. **Mitigation:** `bin/e2e.sh` creates it per run and deletes it at teardown; `wp-testing` names the pair of commands.
4. **Supply chain through skills** → an upstream skill or vendored checklist changes under us and rewrites what the sentinel or the implementer believes. **Mitigation:** `bin/wp-upstream-skills.sh` clones at a pinned commit and installs from the local path with `--copy`; the vendored checklist file carries its source commit hash; both pins are updated only by a commit in this repo (reviewed).
5. **Screenshots leak data** → a staging screenshot carries real user rows. **Mitigation:** shake-out drives seeded fixtures (`bin/e2e.sh` seeds via WP-CLI, per `wp-testing`); `shakeout-qa`'s prompt names the seeded actors and refuses a production URL.

## Acceptance flows [GATE]

N/A — the spec flags no user-facing surface. The behavioural contract is the per-task test cases and the self-hosting gate-check run (SC-7).

## Shake-out access

N/A — agent tooling, no screen to log in to.

## Architecture invariants touched [GATE]

This repo carries no `ARCHITECTURE-INVARIANTS.md`. The harness's load-bearing invariant — **no self-attestation: a gate is proven by an artifact property or a scraped result, never by an agent's claim** — is what this spec extends to the artifact: a `pass` on a browser row is a URL plus a file on disk, not a verdict word; FINISHED requires an `Artifact-diff:` line, not a ticked box; parity is an enumerated list, not "same as". The prose invariant "a netdust skill that restates upstream content is a defect" gains a WordPress upstream (FR-22/23). Cluster D CREATES `ntdst-baseline/ARCHITECTURE-INVARIANTS.md`; from then on `invariant-auditor` runs its checks on every baseline consumer.

## Spec-premise ground-truth [GATE]

- **G1 — checker structure:** `run_checks(spec_dir)` (`gate-check.py:2382`) reads the three files and calls checks in order; `main()` (`:2432`) parses `spec_dir` + `--json` only → T01 adds `--shakeout` as a second mode that calls a new `run_shakeout_checks(spec_dir)`. `_flow_rows()` (`:388`) returns a COUNT of rows with ≥3 filled cells → T02 adds `parse_flow_rows()` returning `[{n, flow, layer, cells}]` and leaves `_flow_rows` callers untouched.
- **G2 — test style:** `tests/test_spec_gate_check.py` collects `(ok, desc)` tuples in `run()`; `_run(files: dict) -> (rc, out)` runs the script on a temp dir; fixtures are module-level strings (`PLAN_GATES_FULL`, `TASKS_LANE_BEHAVIOUR_BARE`). Screenshot-on-disk cases write a PNG into the temp dir alongside the manifest.
- **G3 — loop-check FINISHED:** `bin/loop-check.py:219–243` — all boxes checked → suite-green sha current → `FINISHED`. T04 inserts one condition before the sha check: `artifact_diff_missing(tasks_text, spec_text)` → `CONTINUE — user-facing behaviour cluster closed without Artifact-diff`.
- **G4 — agent frontmatter:** `agents/test-author.md` declares `tools: Read, Grep, Glob, Bash, Edit, Write, Skill`; `shakeout-qa.md` declares `Read, Grep, Glob, Bash, Skill`, `model: sonnet`. `tests/test_agent_frontmatter.py` asserts `model:` only; T05 adds a `tools:` assertion for shakeout-qa.
- **G5 — the login package:** `aaemnnosttv/wp-cli-login-command` (MIT, 324★): `wp package install aaemnnosttv/wp-cli-login-command`; `wp login install` deploys the companion server plugin (required); `wp login create <user> --url-only --expires=<s>` (default 900); `wp login invalidate`. The companion plugin is the piece that must not ship — threat 1.
- **G6 — skills CLI:** `npx skills add <source> -s <skills…> -g -y --copy -a claude-code`; sources include GitHub shorthand AND local paths; NO ref pinning. T08 therefore `git clone --depth 1` + `git -C … checkout <sha>` then `npx skills add ./<clone> …`. Global install lands in `~/.claude/skills/<name>/`.
- **G7 — baseline state:** `~/Sites/ntdst-baseline` on netdust-web is at `f696124` (admin shell merged 2026-09-05 19:58): `services/admin/{AdminUIService,Shell}.php`; filters in use include `ntdst/baseline/booted` (14), `…/purge` (6), `…/admin/apps`, `…/admin/enqueue`, `…/seo/*`, `…/schema/*`, `…/polylang/*`, `…/security/config`; `bin/guard.sh` is the only script; `composer.json` has `conflict: netdust/ntdst-core <4.2`, no require. Local clone is at `550d942` — pull first.
- **G8 — e2e seam:** `netdust-wp/skills/wp-testing/SKILL.md:52` — `bin/e2e.sh` seeds fixtures via WP-CLI before Playwright runs; `E2E_PASS` is per-run; admin at `/wp/wp-admin` on Bedrock. The recipe attaches here (T07).
- **G9 — versions:** `plugin.json` netdust-agent `0.26.0`, netdust-wp `1.1.2`; `marketplace.json` carries per-plugin changelog descriptions; `netdust-devops/tests/test-marketplace.sh` and `test_plugin_version_resolution.py` pin the sync.
- **G10 — model ladder:** `_shared/model-ladder.md:23` — `shakeout-qa` sonnet on both lanes; `security-sentinel`/`invariant-auditor` inherit. Unchanged.
- **G11 — herdr moments:** `_shared/herdr-moments.md` table rows: seam, parallel dispatch, Stage 2 overview, unattended run, branch review, … → T05 adds one row: the screenshot yield (a `shakeout` tab paging the screenshots, unfocused).
- **G12 — netdust-wp sizes:** `wp-security/SKILL.md` 155 lines (sections: four pillars, quick reference, NTDST projects, database, example, rationalization table, loophole closures, mistakes, see-also); `wp-infra/SKILL.md` 177 lines (Bedrock layout, WP-CLI conventions, cache flush, logs, Makefile targets, Vite, custom-app, anti-patterns). Baseline for SC-5: 332 lines → ≤ 249.

## Deploy

- **Payload:** none — a marketplace repo and a Composer package; nothing in `deploy.payload`.
- **Non-git steps:** on netdust-web, set `"superpowers-chrome@superpowers-marketplace": true` in `~/.claude/settings.json` and `/reload-plugins`; on every box, `/plugin` update to netdust-agent 0.27.0 and netdust-wp 1.2.0 and run `bin/wp-upstream-skills.sh` once; consumers of baseline run `composer update netdust/ntdst-baseline` on their next feature branch.

## Phases & review clusters [GATE]

Single phase, five clusters, ordered so the gate the spec exists for lands first, the texts that cite it second, the WordPress layer third, the second repo fourth, the record last:

- **Cluster A — the shake-out checker** (T01–T03, standard, provisional tier STANDARD): `--shakeout` mode + manifest grammar + credential floor; `Layer` cell + `## Shake-out access`; parity, rendered-content observable, panel hints.
- **Cluster B — the spine texts and loop-check** (T04–T06, standard, STANDARD): loop-check Artifact-diff FINISHED rule; shakeout-qa agent + `/shakeout` five steps + herdr row; building panels + fix round + `Feature-tests:` + lessons re-date.
- **Cluster C — netdust-wp** (T07–T09, standard, STANDARD): access recipe in `wp-testing` + CLAUDE.md re-date + plan-requirements pointers; the upstream installer with its bash test; the trim + vendored checklists + sentinel reference.
- **Cluster D — ntdst-baseline** (T10–T11, standard, STANDARD; executed in `~/Sites/ntdst-baseline`): `ARCHITECTURE-INVARIANTS.md` + `bin/check-invariants.sh`; `require ^5.2` + consumer dry-run + release 2.5.0.
- **Cluster E — the record** (T12, low, LIGHT): eval cases, versions, marketplace sync, self-hosting lines, compounding proposal.

Task list, contracts and gates: `specs/artifact-gate/tasks.md`.

## The convergence contract

Reviews of this diff verify against: spec AC-6 (zero new findings on the existing corpus except the `Layer` WARN), threat items 1–4 (no `wp login` in a deploy-side script; the `shakeout-credential` FAIL; per-run app passwords; both pins are commit hashes), AC-10/SC-6 (the panel table has two homes), and the standing rule that no skill text promises an enforcement the machine does not perform. Free-form hunting is out of scope.

**Loop budget: ~19 iterations** (13 tasks + 4 review clusters + one fix round each on Clusters A and C).
