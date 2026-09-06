# Tasks — The artifact gate

**Spec:** `specs/artifact-gate/spec.md` · **Plan:** `specs/artifact-gate/plan.md`
**Loop budget: ~19 iterations** (13 tasks + 4 review clusters + one fix round each on Clusters A and C).

**Standing line for every checker task (T01–T04):**
> New checks follow the house shape — a `check_*(text, f: Findings)` function over the
> shared parsers (`section_body`, `parse_clusters`, `parse_behaviour_clusters`,
> `task_blocks`), fenced-block stripping inherited, fixtures as module-level strings in
> `tests/test_spec_gate_check.py`, run through `_run()` and collected in `run()`. RED-first
> against the real script. Existing cases stay untouched. Spec AC-6 is the lock: this repo's
> `specs/*` produce zero NEW findings from the new checks except the FR-4 `Layer` WARN.

**Standing line for every text task (T05–T07, T09):**
> Text cites the mechanical check or the single-home file by exact name (`shakeout-manifest`,
> `shakeout-credential`, `shakeout-access`, `parity`, `observable-content`, `panel-hints`,
> `bin/loop-check.py`); no skill text promises an enforcement the machine does not perform.
> The panel tables appear in `skills/building/SKILL.md` and `commands/shakeout.md` only
> (spec AC-10).

---

## Phase 1 — all five clusters

### Cluster A — the shake-out checker (3 tasks · effective stakes: standard · provisional tier: STANDARD)

Lane: contract — checker logic with RED-first contracts of its own

Behaviour: `gate-check.py --shakeout` refuses a manifest whose browser flow was not driven by a browser, and the plain mode refuses a plan that cannot be shaken out (no `browser` row for a flagged screen, no access recipe, an un-enumerated "same as").
Observable: two commands — a fixture manifest with a `browser` row marked `pass` and no `Browser:` evidence exits 1 with a `shakeout-manifest` finding naming the row; the same fixture with `Browser: https://x.ddev.site/wp/wp-admin/admin.php?page=audit · shakeout/af-1.png` and the PNG present exits 0.
RED until: `plugins/netdust-agent/tests/test_spec_gate_check.py::test_shakeout_browser_row_without_evidence_fails`

- [x] T01 [Tier A] Add the `--shakeout` mode: `main()` gains `--shakeout` (mutually exclusive with `--json` is NOT required — both may be given); it calls `run_shakeout_checks(spec_dir) -> Findings`, which reads `plan.md` and `shakeout.md`, parses the manifest table (`# | Flow | Layer | Verdict | Evidence`, header + separator + rows, fences stripped) into `[{n, flow, layer, verdict, evidence}]` via `parse_manifest_rows(text)`, joins on `#` with the plan's acceptance rows from `parse_flow_rows()` (T02 — until T02 lands, join on the manifest alone and accept a missing plan), and emits: FAIL `shakeout-manifest` per plan row with no manifest row; FAIL `shakeout-manifest` per `browser` row whose verdict is not `pass` or whose evidence lacks `Browser: <url> · <path>` with `<path>` existing under `spec_dir`; FAIL `shakeout-manifest` per `wire`/`cli` row with verdict `fail` or `unverified*`; PASS `shakeout-ruling` per row whose evidence carries `Ruling: <reason>` — a human's accepted exception — (overrides the FAIL for that row); FAIL `shakeout-credential` per evidence cell matching `login=|token=|app[-_ ]?password|storageState` (never overridden); FAIL `shakeout-manifest` `no shakeout.md` when the plan has ≥1 `browser` row and the file is absent; PASS summary line `shakeout: <n> rows, <b> browser rows driven`. Exit 1 on any FAIL. (FR-1, FR-2, FR-3; threat 2)  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py, plugins/netdust-agent/bin/README.md)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T01 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) `browser` row `pass` without `Browser:` → exit 1, `✗ [shakeout-manifest]` naming `AF-1`; (b) same with `Browser: <url> · shakeout/af-1.png` and the PNG written into the temp dir → exit 0 with the summary line; (c) evidence names a PNG that does not exist → FAIL naming the path; (d) `browser` row `unverified-no-browser` → FAIL; (e) `Ruling: no browser on this box, driven by Stefan 09-06` → exit 0 with `✓ [shakeout-ruling]`; (f) evidence cell containing `?login=abc123` → `✗ [shakeout-credential]` even with a ruling; (g) `wire` row `pass` with `curl` evidence → pass; (h) `wire` row `fail` → FAIL; (i) plan has a `browser` row, `shakeout.md` absent → FAIL `no shakeout.md`; (j) plain mode (no `--shakeout`) on a feature dir with a manifest → zero shakeout findings (mode isolation).

- [x] T02 [Tier A] Acceptance rows carry a `Layer`: add `parse_flow_rows(body_lines) -> list[dict]` reading the header row to locate `#`, `Flow` and `Layer` columns (case-insensitive; `Layer` may be absent) and returning `{n, flow, layer, cells}` per filled row; `check_acceptance_flows` gains: FAIL `acceptance-flows` when the spec flags a view/screen/admin surface (the existing `spec_user_facing_triggered`) and no row has `layer == 'browser'`; WARN `acceptance-flows` per row whose layer cell is missing or not in `{browser, wire, cli}`. Add `check_shakeout_access(plan_text, f)`: when any row is `browser`, `## Shake-out access` must exist with a non-empty body that is not `N/A` → else FAIL `shakeout-access`; a section marked `N/A` with a reason and no `browser` rows → PASS; absent section and no `browser` rows → silent. Register both in `run_checks`. (FR-4, FR-5)  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T02 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) spec flags a view, plan rows all `wire` → FAIL naming the missing `browser` layer; (b) one `browser` row → PASS; (c) a row with no Layer cell → WARN naming the row; (d) `browser` rows + no `## Shake-out access` → `✗ [shakeout-access]`; (e) `browser` rows + `## Shake-out access` with `wp login create shakeout --url-only --expires=900` → PASS; (f) N/A section, no browser rows → PASS with the reason echoed; (g) `PLAN_GATES_FULL` and every existing plan fixture → findings unchanged except the new WARN (AC-6 lock, asserted by diffing the finding list minus `acceptance-flows` WARNs).

- [x] T03 [Tier A] Three plan/tasks checks: `check_parity(spec_text, plan_text, f)` — when spec or plan (fences stripped) matches `PARITY_PHRASE = r"\b(same\s+\w+\s+as|identical\s+to|mirrors?\b|parity\s+with)\b"` AND `spec_user_facing_triggered()` is non-empty, `## Parity:` must exist in the plan with ≥3 list items and a `http` URL in its body → else FAIL `parity` quoting the phrase and its file; phrase without a flagged surface → silent; block present → PASS naming the reference. `check_observable_content(tasks_text, spec_text, f)` — for each `Lane: behaviour` cluster when the spec flags a user-facing surface, `Observable:` must contain a quoted literal (`"…"` / `'…'`) or a selector (`#\w`, `\.\w`, `\[data-`) → else FAIL `observable-content` naming the cluster. `check_panel_hints(tasks_text, f)` — PASS line `panel-hints: drift-panel: <clusters whose files segments match Services?/|Handlers?/|Repositor(y|ies)/|Modules/> · feature-tests: <clusters carrying Feature-tests: yes>` (`none` when empty); never FAILs. Register all three. (FR-11, FR-12, FR-15, FR-16, FR-18)  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T03 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) spec "same rail as inschrijvingen" + view flagged + no block → FAIL quoting the phrase; (b) block with 3 items and a URL → PASS; (c) 2 items → FAIL naming the count; (d) phrase in a spec flagging no surface → no `parity` finding; (e) behaviour cluster `Observable: the page answers 200` on a view-flagged spec → FAIL; (f) `Observable: the hero renders "Onze energie"` → PASS; (g) same cluster on a spec flagging no surface → silent; (h) two clusters, one with `(files: Services/Foo.php)` → the hints line names exactly that cluster; (i) `Feature-tests: yes — the export has no acceptance flow` on a cluster → named under feature-tests; (j) `TASKS_LANE_BEHAVIOUR_BARE` → hints line `none · none`, no other change.

**Integration gate (Cluster A):** four commands after T01–T03: (1) the FWV fixture → `--shakeout` exit 1 then exit 0 (SC-1); (2) `python3 plugins/netdust-agent/bin/gate-check.py specs/artifact-gate` → exit 0; (3) `for d in specs/*; do python3 plugins/netdust-agent/bin/gate-check.py $d; done` → no new `✗` versus the pre-branch run recorded at `.superpowers/sdd/artifact-gate/corpus-baseline.txt` (AC-6); (4) `bash plugins/netdust-agent/tests/run.sh` → 0 failed modules.

── REVIEW GATE ── (tier: STANDARD — checker logic; escalates one-way to FULL if any finding touches the `shakeout-credential` floor.)

---

### Cluster B — the spine texts and loop-check (3 tasks · effective stakes: standard · provisional tier: STANDARD)

Lane: contract — one FINISHED condition with a RED-first contract, and the texts that cite Cluster A by name

- [x] T04 [Tier A] `bin/loop-check.py`: before the suite-green sha check at the all-boxes-checked branch, call `artifact_diff_missing(tasks_text, spec_text) -> list[str]` — the names of `Lane: behaviour` clusters whose members are all `[x]`, on a spec that flags a user-facing surface, with no line matching `^\s*(?:[-*]\s+)?\**Artifact-diff\**:` between the cluster heading and the next heading; non-empty → print `LOOP: CONTINUE — user-facing behaviour cluster(s) closed without Artifact-diff: <names>` and return 1. `run_shakeout_checks` (T01) emits the same as FAIL `shakeout-artifact-diff`. (FR-17, FR-18)  (files: plugins/netdust-agent/bin/loop-check.py, plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_loop_check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, ledger logic over local files, not a security-boundary category.
  Proven by: new test — the T04 case blocks in `test_loop_check.py` and `test_spec_gate_check.py`.
  Unit test: RED-first. (a) all-checked behaviour cluster, view-flagged spec, no `Artifact-diff:` → `CONTINUE` naming the cluster, rc 1; (b) with `Artifact-diff: Figma frame 625-2790 → 12 of 12 components present` → falls through to today's sha check; (c) contract-lane cluster without the line → untouched; (d) spec flags no surface → untouched; (e) `--shakeout` on the same fixture → `✗ [shakeout-artifact-diff]`.

- [ ] T05 [Tier B] `agents/shakeout-qa.md`: frontmatter `tools: Read, Grep, Glob, Bash, Skill, Edit, Write`; body gains the manifest grammar (FR-1/FR-2 verbatim, one table, the `Browser:` evidence form, the `Ruling:` form), the write scope (`tests/**` and `specs/<feature>/shakeout.md` + `shakeout/*.png` only — anything else is a finding for the implementer), the rule that every driven `browser` flow is committed as a Playwright spec and every `wire` flow as an integration test through the project's runner with the manifest row naming the test file, the access recipe read from the plan's `## Shake-out access` (never invented; production URL refused), and the seeded-actors rule (threat 5). `commands/shakeout.md`: five steps in FR-7 order — suite + telemetry; `shakeout-qa`; `python3 <plugin>/bin/gate-check.py --shakeout specs/<feature>` looping fix-dispatch → re-drive → re-check until exit 0; the human screenshot yield (one per surface; a `shakeout` tab under `HERDR_ENV=1` per `_shared/herdr-moments.md`, inline otherwise); the branch panel per the FR-10 table. `_shared/herdr-moments.md`: one new row, the screenshot yield. `tests/test_agent_frontmatter.py`: assert shakeout-qa's `tools` include `Edit` and `Write`. (FR-1, FR-2, FR-6, FR-7, FR-10)  (files: plugins/netdust-agent/agents/shakeout-qa.md, plugins/netdust-agent/commands/shakeout.md, plugins/netdust-agent/skills/_shared/herdr-moments.md, plugins/netdust-agent/tests/test_agent_frontmatter.py)
  Test-author: solo — standard stakes, prose plus one frontmatter assertion.
  Proven by: machine gate — `test_agent_frontmatter.py` (tools assertion) and the AC-10 grep (`grep -l "security-sentinel.*invariant-auditor" plugins/netdust-agent/**/*.md` lists exactly building + shakeout).
  Unit test: RED-first on the frontmatter assertion (shakeout-qa without `Edit` → FAIL line); the bodies are prose (Tier B).

- [ ] T06 [Tier B] `skills/building/SKILL.md`: the review-gate section becomes the FR-9 table (FULL: `security-sentinel` + `invariant-auditor`, drift-reviewer standing in on WP without an invariants doc; STANDARD/LIGHT: no dispatch — the marker halts for the integration gate, the artifact look and the `Artifact-diff:`), the FR-11 rule reading the `panel-hints:` line, the FR-12 rule (`Feature-tests: yes — <reason>` on a cluster is the only trigger for the post-cluster `test-author`; the committed shake-out flows are the feature tests otherwise), the FR-13 stop rule (one fix round; a second is a human ruling or parked to the branch review), and Stage 3 pointing at `commands/shakeout.md`'s five steps. `skills/testing-workflow/SKILL.md`: the closing paragraph names the shake-out flows as the feature tests and `Feature-tests:` as the opt-in. `skills/planning/SKILL.md`: the acceptance-flows bullet names the `Layer` cell, `## Shake-out access` and `## Parity:` with their check names. `skills/building/lessons.md`: the 2026-09-03 entry gains a dated 2026-09-06 paragraph (drift moves to the branch review + framework-path clusters; prevention half kept verbatim); `press-kit-five-generations` cited with the one-round cap. (FR-9, FR-11, FR-12, FR-13, FR-14, SC-3, SC-6)  (files: plugins/netdust-agent/skills/building/SKILL.md, plugins/netdust-agent/skills/building/lessons.md, plugins/netdust-agent/skills/testing-workflow/SKILL.md, plugins/netdust-agent/skills/planning/SKILL.md)
  Test-author: solo — standard stakes, prose.
  Proven by: machine gate — the AC-10 grep and `grep -c "two rounds" skills/building/SKILL.md` = 0.
  Unit test: no unit test: Tier B, prose; the enforcement it cites is T01–T04's.

**Integration gate (Cluster B):** (1) `bash plugins/netdust-agent/tests/run.sh` → 0 failed; (2) `grep -rn "REVIEW GATE\|panel" plugins/netdust-agent/skills plugins/netdust-agent/commands | grep -c "security-sentinel.*invariant-auditor"` = 2 (building, shakeout); (3) `grep -c "Feature-tests:" plugins/netdust-agent/skills/building/SKILL.md` ≥ 1 and `grep -c "Browser:" plugins/netdust-agent/agents/shakeout-qa.md` ≥ 1.

── REVIEW GATE ── (tier: STANDARD — one ledger rule plus prose; no 1a surface.)

---

### Cluster C — netdust-wp: access recipe, upstream, trim (3 tasks · effective stakes: standard · provisional tier: STANDARD)

Lane: contract — an installer with its own bash test, a procedure that touches auth on DDEV, and a trim measured by count

- [ ] T07 [Tier B] `skills/wp-testing/SKILL.md` gains `## Shake-out access — the recipe the plan cites`: (1) DDEV — `ddev wp package install aaemnnosttv/wp-cli-login-command` once, `ddev wp login install --activate` (the companion server plugin, DDEV-only: `bin/e2e.sh` installs it, it is never in `deploy.payload`, and the recipe is valid on `WP_ENV != production` — cite `netdust-devops:devops` for the production floor), then `ddev wp login create <seeded-admin> --url-only --expires=900` at the start of `bin/e2e.sh`, `ddev wp login invalidate --all` at teardown; the Playwright spec saves `storageState` to a gitignored path; (2) wire rows — `wp user application-password create <user> shakeout --porcelain` per run, deleted at teardown; (3) staging — the same two commands over the project's SSH alias, refused when the alias maps to production in `site.yml`; (4) standalone packages — WordPress Playground with a Blueprint `login` step MAY be the browser (FR-8), named, not required. Add `wp login` and `application-password` to `.gitignore`-adjacent guidance: the link and the state file are never committed; the manifest's Evidence carries the post-login URL. `netdust-wp/CLAUDE.md` line 87: the 09-03 ruling re-dated 2026-09-06 to FR-9–FR-11's shape, prevention half verbatim. `skills/wp-plan-requirements/SKILL.md`: Block 3's acceptance line drops the per-task drift pre-check and names the `panel-hints:` rule; a new Block 4 names `## Parity:` (FR-15) and `## Shake-out access` (FR-5) as WP plan sections with their check names. (FR-5, FR-8, FR-14, FR-15; threats 1–3)  (files: plugins/netdust-wp/skills/wp-testing/SKILL.md, plugins/netdust-wp/CLAUDE.md, plugins/netdust-wp/skills/wp-plan-requirements/SKILL.md)
  Test-author: solo — standard stakes, a documented procedure; the boundary is the devops production floor, which this task cites and does not edit.
  Proven by: machine gate — `grep -rn "wp login" plugins/netdust-devops/dist plugins/netdust-devops/templates` = 0 (the recipe never enters a deploy-side script) and `grep -c "Shake-out access" plugins/netdust-wp/skills/wp-testing/SKILL.md` ≥ 1.
  Unit test: no unit test: Tier B, prose; the commands are ground-truthed against the package README (G5) before the text is written.

- [ ] T08 [Tier A] `plugins/netdust-wp/bin/wp-upstream-skills.sh`: `set -euo pipefail`; constants `UPSTREAM=https://github.com/WordPress/agent-skills.git`, `PIN=<sha read at implementation from origin/main and written into the file>`, `SKILLS="wp-plugin-development wp-rest-api wp-wpcli-and-ops wp-phpstan"`; clones shallow into `${XDG_CACHE_HOME:-$HOME/.cache}/netdust/wp-upstream-skills`, `git fetch --depth 1 origin $PIN && git checkout -q $PIN`, then `npx -y skills add "$CLONE" -s $SKILLS -a claude-code -g -y --copy`; `--check` prints the pinned sha and the installed skill dirs under `~/.claude/skills/` and exits 1 if any is missing; `--dry-run` prints the commands. `tests/test-upstream-skills.sh`: runs against a temp `HOME` and a local bare fixture repo standing in for the upstream (three fake `SKILL.md` dirs) with `npx` stubbed on `PATH` to copy dirs — asserts the pinned checkout, the four dirs land, `--check` exit codes, and that an unpinned `PIN=` refuses. `tests/run.sh` includes it. `CLAUDE.md` names the installer under setup. (FR-22; threat 4)  (files: plugins/netdust-wp/bin/wp-upstream-skills.sh, plugins/netdust-wp/tests/test-upstream-skills.sh, plugins/netdust-wp/tests/run.sh, plugins/netdust-wp/CLAUDE.md)
  Test-author: solo — standard stakes, an installer over a pinned public repo; the pin is the boundary and it is a constant reviewed in-diff.
  Proven by: new test — `tests/test-upstream-skills.sh`.
  Unit test: RED-first. (a) fixture upstream + stub npx → four dirs under `$HOME/.claude/skills/`, exit 0; (b) `--check` after install → exit 0 listing four; (c) one dir removed → `--check` exit 1 naming it; (d) `PIN=` empty → exit 2 `refusing: no pin`; (e) `--dry-run` → prints the clone/checkout/add lines, touches nothing.

- [ ] T09 [Tier B] Trim and vendor: `skills/wp-security/SKILL.md` — `## Quick reference` (sanitize/escape/authorize tables) and `## Common mistakes` are replaced by one citation block naming the upstream `wp-plugin-development` and `wp-rest-api` skills (installed by T08's script) and keeping `## The four pillars`, `### NTDST projects`, `## Rationalization table`, `## Loophole closures`, the RED tests; `skills/wp-infra/SKILL.md` — `## WP-CLI conventions`/`### Common WP-CLI commands` cite `wp-wpcli-and-ops` and keep only the DDEV/Bedrock path rules and the cache-flush warning; target ≤ 249 lines across the two (SC-5). `references/wp-review-checklists.md` (new): the `wp-security-review` and `wp-migration-upgrade-review` checklists from `jorgerosal/wordpress-skills` at a pinned commit, MIT attribution and hash in the header, trimmed to the checklist items. `netdust-agent/agents/security-sentinel.md`: one paragraph — on a WordPress project load `netdust-wp/references/wp-review-checklists.md` and verify against it, keyed items. (FR-23, FR-24; threat 4)  (files: plugins/netdust-wp/skills/wp-security/SKILL.md, plugins/netdust-wp/skills/wp-infra/SKILL.md, plugins/netdust-wp/references/wp-review-checklists.md, plugins/netdust-agent/agents/security-sentinel.md)
  Test-author: solo — standard stakes, prose and a vendored reference with a pinned hash.
  Proven by: machine gate — `wc -l` over the two skills ≤ 249 and `grep -c "WordPress/agent-skills" <each>` ≥ 1; `head -5 references/wp-review-checklists.md` carries `MIT` and a 40-hex commit.
  Unit test: no unit test: Tier B, prose; the existing `wp-security/red-tests.md` cases still pass (they are the netdust layer, untouched).

**Integration gate (Cluster C):** (1) `bash plugins/netdust-wp/tests/run.sh` → 0 failed (T08's test included); (2) `bash plugins/netdust-wp/bin/wp-upstream-skills.sh --dry-run` prints a 40-hex pin; (3) `grep -rn "wp login" plugins/netdust-devops/` = 0; (4) `wc -l plugins/netdust-wp/skills/wp-security/SKILL.md plugins/netdust-wp/skills/wp-infra/SKILL.md` total ≤ 249.

── REVIEW GATE ── (tier: STANDARD — a pinned installer plus prose; escalates to FULL if the recipe text reaches any deploy-side script.)

---

### Cluster D — ntdst-baseline: invariants + pinned core (3 tasks · effective stakes: standard · lane: behaviour)

Lane: behaviour — a doc, a script and a Composer constraint over a framework that already has the rule; executed in `~/Sites/ntdst-baseline` on branch `feature/invariants`, after `git pull --ff-only` to `f696124`

Behaviour: ntdst-baseline can be audited mechanically and declares the core it runs on.
Observable: `bash bin/check-invariants.sh` in `~/Sites/ntdst-baseline` prints one `PASS INV-n` line per invariant (≥6) and exits 0; `composer validate` exits 0; in `~/Sites/edushare`, `composer update --dry-run netdust/ntdst-baseline` resolves `netdust/ntdst-baseline 2.5.0` with 0 conflicts and core `5.2.x` unchanged.
RED until: `bin/check-invariants.sh`

- [ ] T10 `ARCHITECTURE-INVARIANTS.md` authored with `netdust-agent:architecture-invariants`, mirroring core's shape (holds today / established by, convergence point, mechanical check in the `-E` grep form): INV-1 the admin-app shell (`services/admin/Shell.php` is the only composer of `.ntdst-admin` markup; every admin page under `ntdst/baseline/admin/apps` renders through it); INV-2 the filter namespace (`ntdst/baseline/*` is the only configuration door — no `get_option` for a baseline setting); INV-3 the purge door (`ntdst/baseline/purge` is the one cache-invalidation path); INV-4 the lockout (`SecurityService` owns login throttling; no second `wp_login_failed` handler); INV-5 shared slugs (`services/polylang/SharedSlugs.php` is the one slug reconciler); INV-6 YOOtheme sources (`services/yootheme/` is the only bridge into the builder); INV-7 the boot loop (`ntdst-baseline.php` resolves every service through `ntdst_get()`, no `new` for a service). `bin/check-invariants.sh` runs each check and prints `PASS INV-n` / `FAIL INV-n <hits>`; `composer.json` `scripts.gate` adds it. README: one paragraph pointing `invariant-auditor` at the doc. (FR-19)  (files: ARCHITECTURE-INVARIANTS.md, bin/check-invariants.sh, composer.json, README.md)

- [ ] T11 `composer.json`: replace `conflict: {"netdust/ntdst-core": "<4.2"}` with `require: {"php": ">=8.1", "netdust/ntdst-core": "^5.2"}`; add the `repositories` entry for `git@github.com:netdust/ntdst-core.git` (vcs) so the package resolves standalone; `composer validate` and `composer update --dry-run` in the baseline repo; then in `~/Sites/edushare` `composer update --dry-run netdust/ntdst-baseline` against the branch (temporary `dev-feature/invariants` constraint, reverted). Version bump to `2.5.0` in `ntdst-baseline.php`'s header and README changelog. (FR-20, FR-21, SC-4)  (files: composer.json, composer.lock, ntdst-baseline.php, README.md)

- [ ] T12 [HUMAN] Release: Stefan merges `feature/invariants` to `main`, tags `2.5.0` and pushes (`git tag 2.5.0 && git push origin main --tags`); then on netdust-web sets `"superpowers-chrome@superpowers-marketplace": true` in `~/.claude/settings.json` and runs `/reload-plugins` (plan `## Deploy`, non-git steps). (FR-21)

**Integration gate (Cluster D):** the three Observable commands, plus `composer gate` in the baseline repo → exit 0 (guard, tests, and the new invariants script).

---

### Cluster E — the record (1 task · effective stakes: low · provisional tier: LIGHT)

Lane: contract — versions, evals and the self-hosting lines

- [ ] T13 [Tier B] `evals/artifact-gate-2026-09-06-cases.json`: ≥8 cases in the house shape (`skill`, `skill_path`, `query`, `signature`) — a shake-out asked to pass a screen without a browser (signature: refuses, names `gate-check --shakeout`); a plan saying "same rail as" (signature: writes `## Parity:` from the running reference); a STANDARD cluster close (signature: no reviewer dispatch, integration gate + artifact look); a FULL cluster (signature: sentinel + invariant-auditor only); a second fix round request (signature: human ruling or park); a behaviour cluster `Observable: answers 200` on a screen (signature: rewrites with rendered content); a WordPress sentinel dispatch (signature: loads the checklists reference); a shake-out on a site with no access recipe (signature: hands back for `## Shake-out access`). `manifest.json` lists the file. Versions: `plugins/netdust-agent/.claude-plugin/plugin.json` → `0.27.0`, `plugins/netdust-wp/.claude-plugin/plugin.json` → `1.2.0`, `.claude-plugin/marketplace.json` descriptions prefixed with the 0.27.0 / 1.2.0 paragraphs (what changed, one paragraph each, same voice as 0.26.0's). Self-hosting: this feature's `plan.md` already carries `## Shake-out access` N/A with its reason (SC-7) — re-run `gate-check.py specs/artifact-gate` and record the PASS in the ledger. Then `netdust-agent:compounding` proposes the CODE-MAP/lessons harvest (report only). (FR-25, FR-26, FR-27, SC-2)  (files: plugins/netdust-agent/evals/artifact-gate-2026-09-06-cases.json, plugins/netdust-agent/evals/manifest.json, plugins/netdust-agent/.claude-plugin/plugin.json, plugins/netdust-wp/.claude-plugin/plugin.json, .claude-plugin/marketplace.json)
  Test-author: solo — low stakes, declarative.
  Proven by: machine gate — `bash plugins/netdust-devops/tests/test-marketplace.sh` and `python3 plugins/netdust-agent/tests/test_plugin_version_resolution.py` (the sync pins) plus `python3 -m json.tool` on the two JSON files.
  Unit test: no unit test: Tier B, declarative config; the sync gates above are the proof.

**Integration gate (Cluster E):** (1) `bash plugins/netdust-agent/tests/run.sh` and `bash plugins/netdust-wp/tests/run.sh` and `bash plugins/netdust-devops/tests/run.sh` → 0 failed each; (2) `python3 plugins/netdust-agent/bin/gate-check.py specs/artifact-gate` → exit 0; (3) `git diff --stat main` names no file under `plugins/netdust-core/` or `plugins/netdust-statamic/`.

── REVIEW GATE ── (tier: LIGHT — versions and evals.)

---

── BRANCH REVIEW ── (tier: STANDARD — `reviewer` + `code-simplicity-reviewer`, plus `ntdst-drift-reviewer` on the Cluster D diff in the baseline repo; convergence targets per plan `## The convergence contract`.)
