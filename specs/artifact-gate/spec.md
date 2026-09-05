# Spec — The artifact gate: shake-out decides, panels shrink, parity is grammar

**Repo:** `netdust-plugins` (marketplace source — never the cache) · **Plugins:** `netdust-agent`, `netdust-wp` · **Second repo:** `ntdst-baseline` (one cluster, executed there)
**Provenance:** Stefan's 2026-09-06 intake after the session study of 2–5 September ("should we adjust the harness? is it still to tight? for me most important is that code is same across projects and long runs, using ntdst-core, ntdst-baseline making sure that my wordpress projects are of high quality… what test did prove themseld, what reviews?"), his ruling on the four design questions the same session, the sixth part added after the WordPress skill-pack research ("yes, write the spec with all six"), and the auth remark ("agents are often stuck here.. auth mostly").

## Problem / why

The study read 43 local and 22 netdust-web sessions and scored 90 review-type dispatches
by one question: did the report change the code. The numbers, not the prose:

1. **Every bug Stefan found after a green panel was an artifact mismatch, never a code
   defect.** The audit rail missing seven components after shake-out + reviewer +
   invariant-auditor all passed; two bugs found minutes after the action-matrix shake-out;
   the josworld case singles rendering empty after 13 dispatches. In each case the
   shake-out manifest reads `Browser: not reached` or `not-reachable (worktree)` and every
   flow still says `pass`. The agent text already says "no UI flow passes without a
   browser" — nothing refuses the manifest that ignores it.
2. **The reviewers that found things are the narrow ones.** security-sentinel: 7 runs, a
   missing index (2.7 s scan), a pager never applied, a layout-JSON-destroying missing
   `wp_slash()`, an unvalidated tree. invariant-auditor: 4 runs, a duplicated resolver and
   an unused container mechanism. Generalist reviewer: 26 runs, zero Critical.
   code-simplicity: 15 runs, dead exports. drift-reviewer: 15 runs on every cluster panel,
   one Critical, and that one was a standalone module audit, not a panel. On netdust-web
   reviewer dispatches outnumbered implementer dispatches 53 to 50.
3. **Feature tests after a cluster mostly confirm.** 7 dispatches: one (N-B) committed three
   real failures; five found nothing at 50–107 turns each. Stride carries 195k lines of
   tests against 89k of source. The split-RED test-authors on Tier-A backend work, by
   contrast, produced 8 of 8 behavioural reds and the compiler/window/pagination/route
   floors drew zero corrections from Stefan.
4. **The plan never enumerated the reference.** "give audit the same rail as
   inschrijvingen" was built three times because no artifact listed what that rail is; the
   panel certified the diff against a plan that did not know either.
5. **The behaviour lane's one safeguard was too weak to bite.** josworld's cluster RED read
   "answers 200 and renders its builder layout" — an empty page passes it — and no
   `Artifact-diff:` line was ever recorded although `building` requires one.
6. **Browser shake-out stalls on authentication.** The Stride shake-outs only reached the
   browser after Stefan minted login links by hand; the audit shake-out recorded BLOCK-1
   for the same reason. Nothing in the plan names how the shake-out logs in.
7. **ntdst-baseline is now a shared dependency with no invariants and no pinned core.** The
   admin-app shell landed 2026-09-05 (`f696124`) with no review; the polylang drift
   reviews already flagged "no vendored core, version not pinned".
8. **netdust-wp restates WordPress knowledge that WordPress now maintains.** The official
   `WordPress/agent-skills` pack (16 skills, GPL, 2.1k stars; Automattic's pack merged
   into it 2026-02-01) carries plugin architecture, REST, WP-CLI, PHPStan and Playground.
   The skill-architecture rule already says a skill restating upstream content is a defect.

The harness is right where the work is a rule this project chose and wrong where the
work is a screen a human can judge by eye. This spec moves the gate to the artifact.

## User stories, prioritized

### P1 — A UI flow passes only when a browser drove it and I can see it
As the human partner, when a spec flags a screen, the shake-out manifest carries a URL and
a screenshot per browser flow, the machine refuses a manifest without them, and I see one
screenshot per surface before the branch panel runs. Nothing certifies a screen from the
diff.

### P2 — Reviews spend where they found things
As the human partner, a FULL cluster buys the two reviewers with a track record; a STANDARD
or LIGHT cluster buys none and is reviewed once at the branch; drift review runs where the
framework is touched; a cluster gets one fix round.

### P3 — The tests that stay are the ones that bit
As the human partner, the split-RED on Tier-A work stays untouched, the flows the shake-out
drove become the committed feature tests, and a post-cluster feature test-author is
dispatched only when the plan says why.

### P4 — "Same as X" is enumerated before it is built
As the human partner, a plan that references an existing surface lists that surface's
components from the running site, and the new surface's acceptance rows say which ones
they cover, so a rail with seven parts missing cannot pass.

### P5 — ntdst-baseline is auditable the way ntdst-core is
As the human partner, baseline carries its own `ARCHITECTURE-INVARIANTS.md` with grep
checks, requires a pinned core, and `invariant-auditor` runs against it on every consumer.

### P6 — WordPress knowledge comes from WordPress
As the human partner, the official skill pack is a named upstream of netdust-wp, netdust-wp
keeps only what is ours (ntdst-core, baseline, YOOtheme, DDEV, the netdust test harness),
and security-sentinel on WordPress reads a maintained review checklist.

## Functional requirements

### A — The shake-out artifact gate

- **FR-1:** The manifest has one home and one grammar: `specs/<feature>/shakeout.md`, a
  table with the columns `# | Flow | Layer | Verdict | Evidence`, one row per row of the
  plan's `## Acceptance flows` (same `#`). `Layer` is `browser`, `wire` or `cli`.
  Verdict is `pass`, `fail`, `not-reachable` or `unverified-no-browser`. Source: P1;
  design part 1, approved 2026-09-06.
- **FR-2:** A `browser` row is `pass` only when its Evidence cell carries
  `Browser: <url> · <screenshot path>` and the screenshot file exists under the feature
  dir. Any other `browser` row is not a pass, whatever the verdict word says. Source:
  "Machine check + screenshot to you at branch review" (ruling 2026-09-06).
- **FR-3:** `bin/gate-check.py --shakeout specs/<feature>` is a new mode. It reads the
  plan's acceptance rows and the manifest and FAILs when: a plan row has no manifest row;
  a `browser` row is not a pass under FR-2; a `wire` or `cli` row is `fail` or
  `unverified`. A row may instead carry `[HUMAN] accepted: <reason>` in Evidence, which
  passes it and is reported as a ruling. Exit 0 or the panel does not run. Source: same
  ruling.
- **FR-4:** The plan's `## Acceptance flows` rows gain a `Layer` cell. `check_acceptance_flows`
  FAILs when the spec flags a view/screen/admin surface and no row is `browser`, and
  WARNs on a row with no readable layer. Source: design part 1.
- **FR-5:** The plan carries `## Shake-out access`: the ONE command that yields an
  authenticated browser session on the environment the shake-out drives (a WP-CLI
  login-link command on DDEV, a saved Playwright storage state, or an application
  password for `wire` rows), and the environment it is valid on. `check_plan_gates`
  FAILs a plan with `browser` rows and no such section; the recipe itself lives in
  `netdust-wp:wp-testing` and is cited, not restated. A recipe that would run on a
  production host is refused by the devops floor. Source: "agents are often stuck here..
  auth mostly".
- **FR-6:** `shakeout-qa` gains `Edit`/`Write`, scoped by its prompt to `tests/**` and the
  manifest. Every `browser` flow it drove is committed as a Playwright spec, every `wire`
  flow as an integration test through the project's runner; the manifest row names the
  committed test. These are the cluster's feature tests. Source: "Acceptance flows become
  the committed tests" (ruling 2026-09-06).
- **FR-7:** `commands/shakeout.md` runs, in order: suite + telemetry; `shakeout-qa`;
  `gate-check --shakeout` (loop on FAIL: fix-dispatch, re-drive, re-check); the `[HUMAN]`
  screenshot yield — one screenshot per surface shown to the human, as a herdr tab under
  `HERDR_ENV=1`, inline otherwise; then the branch panel. Source: same ruling.
- **FR-8:** For a standalone package (a plugin or mu-plugin repo with no `site.yml`) the
  shake-out MAY boot WordPress Playground as its browser, with the Blueprint's `login`
  step as the access recipe. Named in `wp-testing`, never required. Source: design part 1
  plus the research verdict, approved 2026-09-06.

### B — Panels, drift, fix rounds

- **FR-9:** Cluster panel by tier: FULL — `security-sentinel` + `invariant-auditor`
  (when the project or its framework packages carry `ARCHITECTURE-INVARIANTS.md`; else
  `netdust-wp:ntdst-drift-reviewer` stands in on WordPress). STANDARD and LIGHT — no
  reviewer dispatch; the `── REVIEW GATE ──` marker still halts for the integration gate,
  the artifact look and the Artifact-diff. Source: "FULL = sentinel + invariant-auditor;
  others none" (ruling 2026-09-06).
- **FR-10:** Branch panel by tier: LIGHT — `reviewer`; STANDARD — `reviewer` +
  `code-simplicity-reviewer`; FULL — those plus `security-sentinel` + `invariant-auditor`.
  On WordPress, `ntdst-drift-reviewer` joins every branch panel. Source: same ruling.
- **FR-11:** Drift review also joins the cluster gate of any cluster whose `(files:)`
  segments match `Services?/`, `Handlers?/`, `Repositor(y|ies)/` or `Modules/`.
  `gate-check.py` prints a `✓ drift-panel: <clusters>` line naming them so the
  controller reads it rather than deciding it. Source: "Branch review +
  Services/Handlers/Repositories clusters" (ruling 2026-09-06).
- **FR-12:** The post-cluster feature `test-author` dispatch happens only on a cluster
  carrying `Feature-tests: yes — <reason>`; absent the line, the committed shake-out
  flows are the feature tests. `Test-author: split` on Tier-A tasks is unchanged.
  Source: FR-6's ruling.
- **FR-13:** One fix round per cluster gate; a second round is a `[HUMAN]` ruling or a
  parked finding for the branch review. `press-kit-five-generations` is re-cited with the
  new cap. Source: design part 2.
- **FR-14:** The 2026-09-03 ruling ("drift-reviewer on EVERY panel") is re-dated
  2026-09-06 in `building/lessons.md` and `netdust-wp/CLAUDE.md` with FR-9–FR-11 as the
  new shape and its prevention half (framework skills in every dispatch) kept verbatim.
  Source: ruling 2026-09-06.

### C — Parity, rendered content, Artifact-diff

- **FR-15:** When the spec or plan contains a parity phrase (`same <noun> as`,
  `identical to`, `mirror(s)`, `parity with`) and the spec flags a user-facing surface,
  the plan must carry `## Parity: <reference surface>` — a list of ≥3 components read from
  the RUNNING reference (URL named), and each acceptance row for the new surface names
  the components it covers. `check_parity` FAILs its absence. Source: "this is not the
  same rail as with inschrijvingen. identical, also option to create/Save list... that was
  what i asked" (Stefan, 2026-09-05); design part 3.
- **FR-16:** A behaviour-lane cluster on a user-facing surface must carry, in
  `Observable:`, a quoted literal or a selector (`"…"`, `'…'`, `#id`, `.class`,
  `[data-…]`) — rendered content, not a status. `check_behaviour_clusters` FAILs a
  user-facing behaviour cluster whose `Observable:` has neither. Source: design part 3.
- **FR-17:** A user-facing behaviour cluster whose members are all `[x]` and which carries
  no `Artifact-diff:` line is not FINISHED for `bin/loop-check.py`, and
  `gate-check --shakeout` FAILs on it. Source: design part 3.
- **FR-18:** `Artifact-diff:` names its source; when a `## Parity:` block exists it is the
  source, and the line reports `<n> of <m> components present`. Source: FR-15.

### D — ntdst-baseline

- **FR-19:** `ntdst-baseline` carries `ARCHITECTURE-INVARIANTS.md` authored with
  `netdust-agent:architecture-invariants` after pulling `f696124`: the admin-app shell as
  the one place admin apps, tabs, tables, filter bars and pagination compose; the
  `ntdst/baseline/*` filter namespace; the purge door; the login lockout; polylang shared
  slugs; YOOtheme sources. Each entry holds today or names its phase, with a grep check in
  core's `-E` form. Source: P5; "ntdst-core, ntdst-baseline are solid".
- **FR-20:** `composer.json` replaces `conflict: netdust/ntdst-core <4.2` with
  `require: netdust/ntdst-core ^5.2`; resolution is proven against one consumer site
  (`composer update --dry-run netdust/ntdst-baseline` in edushare). Source: the polylang
  drift finding "core version not pinned", accepted 2026-09-06.
- **FR-21:** Baseline releases 2.5.0 with the doc, the pin and a README line pointing
  `invariant-auditor` at the doc. Source: design part 4.

### E — WordPress upstream skills

- **FR-22:** `WordPress/agent-skills` is a named upstream of netdust-wp: a
  `bin/wp-upstream-skills.sh` installs the pinned set (`wp-plugin-development`,
  `wp-rest-api`, `wp-wpcli-and-ops`, `wp-phpstan`) at a pinned commit via
  `npx skills add`, and netdust-wp's CLAUDE.md names the install as part of setup.
  Source: research verdict, "yes, write the spec with all six".
- **FR-23:** netdust-wp's `wp-security` and `wp-infra` skills cite the upstream skills for
  generic WordPress content and keep only the netdust layer (four pillars as a plan
  requirement, ntdst-core routes, Bedrock/DDEV/WP-CLI paths). A section whose body is
  reproducible from an upstream skill is replaced by a citation. Source: skill-architecture
  rule ("A netdust skill restating superpowers content is a defect"), applied to WordPress.
- **FR-24:** `security-sentinel` on a WordPress project loads
  `netdust-wp/references/wp-review-checklists.md`: the pinned `wp-security-review` and
  `wp-migration-upgrade-review` checklists from `jorgerosal/wordpress-skills` (MIT),
  vendored with attribution and commit hash. Source: research verdict.

### F — Evals and release

- **FR-25:** Every new gate-check rule (FR-3, FR-4, FR-5, FR-11, FR-15, FR-16, FR-17)
  ships with fixture cases in `tests/test_spec_gate_check.py`, positive and negative.
  Source: CLAUDE.md §8.
- **FR-26:** Every skill/agent text change ships an eval case in
  `evals/artifact-gate-2026-09-06-cases.json` (trigger + behavioural). Source: §8.
- **FR-27:** netdust-agent → 0.27.0, netdust-wp → 1.2.0, `marketplace.json` synced; the
  existing green corpus (`specs/*` in this repo) produces zero NEW findings from the new
  checks when no manifest exists (back-compat lock). Source: design part 5.

## Acceptance criteria

- **AC-1:** A fixture plan with one `browser` row and a manifest whose row says `pass`
  without `Browser:` evidence → `gate-check --shakeout` exit 1 naming the row; add the
  evidence line and an existing screenshot → exit 0.
- **AC-2:** A fixture spec flagging a view with a plan whose acceptance rows have no
  `browser` layer → FAIL; with one → PASS; a plan with `browser` rows and no
  `## Shake-out access` → FAIL.
- **AC-3:** A fixture spec containing "same rail as inschrijvingen" and flagging a view,
  with no `## Parity:` block → FAIL; with a 3-item block → PASS; the phrase in a spec
  flagging no surface → no finding.
- **AC-4:** A behaviour cluster whose `Observable:` is "answers 200" on a user-facing spec →
  FAIL; `Observable: the hero renders "Onze energie"` → PASS.
- **AC-5:** A tasks.md with two clusters, one touching `Services/Foo.php` → the
  `drift-panel:` line names exactly that cluster.
- **AC-6:** This repo's existing `specs/*` run through `gate-check.py` produce zero new
  findings (the new checks are silent where their sections are absent and no manifest
  exists), except the WARN on missing `Layer` cells, which is listed per spec.
- **AC-7:** `agents/shakeout-qa.md` frontmatter declares `Edit, Write`; the agent
  frontmatter test passes; `commands/shakeout.md` lists the five steps in FR-7 order.
- **AC-8:** ntdst-baseline: `ARCHITECTURE-INVARIANTS.md` exists with ≥6 entries each
  carrying a runnable check; `composer validate` passes; edushare's dry-run resolves
  2.5.0 with core 5.2.x.
- **AC-9:** `bin/wp-upstream-skills.sh` installs the four skills into a temp HOME and
  exits 0; netdust-wp's `wp-security/SKILL.md` and `wp-infra/SKILL.md` each carry a
  citation line to the upstream skill and are shorter than before.
- **AC-10:** `building/SKILL.md` and `commands/shakeout.md` state the FR-9/FR-10 panel
  tables once each; no other file restates them (grep).

## Success criteria

- **SC-1:** `gate-check --shakeout` refuses 100% of fixture manifests whose browser rows
  lack `Browser:` evidence, in 1 command, exit non-zero.
- **SC-2:** The plugin test runner passes with 0 failed modules and ≥ 14 new cases across
  the checker, the agent-frontmatter test and the upstream installer.
- **SC-3:** Cluster reviewer dispatches per contract cluster drop from 3–5 today to ≤ 2 at
  FULL and 0 at STANDARD/LIGHT, by the text of `building/SKILL.md` and `shakeout.md`.
- **SC-4:** ntdst-baseline 2.5.0 resolves in 1 consumer dry-run with 0 conflicts.
- **SC-5:** ≥ 25% fewer lines under netdust-wp `skills/wp-security` + `skills/wp-infra`,
  with 4 upstream citations added.
- **SC-6:** 0 occurrences of the panel table outside its two homes (AC-10 grep count).
- **SC-7:** This spec's own `tasks.md` passes gate-check with exit 0 and carries
  `## Shake-out access` marked N/A with a stated reason (agent tooling, no screen).

## Security-relevant surfaces

- [ ] User-controlled URLs / server-side outbound requests
- [x] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [ ] None of the above

FR-5 names a command that mints an authenticated session for the shake-out. The plan's
threat model must cover: the recipe existing on a production host; a login link or
storage state landing in git, a manifest, or a screenshot; an application password
outliving the shake-out. Mitigations belong to `wp-testing` (dev-only, expiring, refused
by the devops floor on production) and to the manifest grammar (the Evidence cell never
carries a credential).

## User-facing surfaces

- [ ] A new or changed public page / view / listing
- [ ] A new or changed admin screen or editing surface
- [ ] An endpoint a client or agent will drive
- [x] None of the above

Developer/agent tooling; the human-facing artifact (the screenshot yield) is a file the
controller shows, not a page this spec builds.

## Clarifications

- Q: Drift review on every cluster panel (the 09-03 ruling) or narrower? → A: Branch
  review plus clusters touching Services/Handlers/Repositories/Modules. The 09-03
  ruling's prevention half stays; 15 panel runs found one Critical, outside a panel.
- Q: Browser gate as text, machine check, or machine check plus a human look? → A: machine
  check plus one screenshot per surface shown to the human before the branch panel. Every
  disputed verdict this week came from a manifest that never opened a browser.
- Q: What replaces post-cluster feature tests? → A: the shake-out's driven flows,
  committed; the test-author only on `Feature-tests: yes`. Split-RED on Tier A untouched.
- Q: Cluster panel size? → A: FULL = security-sentinel + invariant-auditor; STANDARD and
  LIGHT none; branch panel carries generalist, simplicity and drift.
- Q: Is wp-playground a browser driver? → A: No; it is a WordPress runtime whose Blueprint
  logs in as admin. Useful as the shake-out browser for a standalone package only (FR-8);
  a site still needs a real browser and an access recipe (FR-5).
- Q: Pin core in baseline by `require` or by a boot-time version check? → A: `require`;
  Composer resolves it and consumers already require core, so nothing double-installs.

## Assumptions

- Claude Code agent frontmatter accepts `tools: Read, Grep, Glob, Bash, Skill, Edit, Write`
  for `shakeout-qa`, and the prompt-level scope (`tests/**`, the manifest) is the
  restriction; no tool-level path allowlist exists. Ground-truthed in the plan.
- A WP-CLI login-link command exists as a Composer/WP-CLI package usable on DDEV; the plan
  ground-truths the package name and version before FR-5's recipe cites it, and falls back
  to Playwright storage state if it does not.
- `npx skills add WordPress/agent-skills --skill <name>` supports a pinned ref; if not,
  FR-22 pins by vendoring the four SKILL.md files with their commit hash.
- Screenshots live under `specs/<feature>/shakeout/` and are committed; size stays under
  the repo's tolerance (PNG, one per surface).
- The local `ntdst-baseline` clone is at `550d942`; the work happens after `git pull` to
  `f696124`.

## Out of scope

- The flow-floor guard's false positives, the auto-mode classifier denials, the devops
  first-bring-up runbook — separate work, already recorded in lessons.
- Installing netdust-devops on netdust-web; enabling `superpowers-chrome` there is a
  non-git step the plan names, not a change in this repo.
- Tier A/B definitions, the sensitive-path floor, the split rule — untouched.
- Re-shaping existing feature dirs in other repos to the new grammar; they read as today
  until their planners opt in (the new checks are silent where their sections are absent).
- Any change to ntdst-core.
