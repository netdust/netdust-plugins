# Spec — Harness inversion: behaviour lane by default, contract lane by exception

**Repo:** `netdust-plugins` (marketplace source — never the cache) · **Plugin:** `netdust-agent` (+ one shared reference consumed from `netdust-core:herdr-orchestration`)
**Provenance:** Stefan's 2026-09-02 intake ("my netdust-agent still forces the agent to
create tests and does a lot of reviews on that code, slowing things down and blowing through
tokens… for the type of work they do 80% of the time the tests are getting overkill"), plus
two follow-ups the same session: cheaper models where possible ("my skills never really
mention this or plan for it in a smart way"), and herdr baked into the harness ("tabs/panes/
worktrees, agents communicating with each other, bat to let me read files… in the most
efficient way possible to improve my overview… and avoid git/dev-stack errors").

## Problem / why

The harness has been recalibrated FOUR times on the verification axis (`tier-diagnosis`
06-04, `contact-page-8k` 07-31, `deliverable-last` 08-03, verify-budget demotion 08-09).
Every fix added a field the planner fills in; `stakes-dial-ignored` records the same
overspend recurring four days after a fix shipped and names why: **a field is echoed, not
branched on.** The structural cause, read from the code rather than the prose:

1. **The seam cannot be crossed without a test decision on every task.** `gate-check.py`
   FAILs a `tasks.md` lacking `[Tier]`, `Test-author:`, `Proven by:` or a `Unit test:`
   contract on any task, and forbids Tier A from waiving. `harnessed-development` says
   under-calling is "the dangerous direction". A faithful agent therefore over-calls: in
   `ntdst-baseline/specs/yootheme-sources` 6/6 tasks are Tier A — including "wire the
   opt-in module" and "a pure lookup table" — and 6/6 chose `Proven by: new test`, the
   most expensive rung of a ladder built to steer them to cheaper ones.
2. **Verification is priced per task, review per cluster, both regardless of lane.** A
   12-task website feature (CPTs, field maps, services on ntdst-core) buys three review
   panels, three test-author feature-test dispatches, integration gates, a shake-out and a
   branch panel. The record: 6 reviewer dispatches → 2 unique findings; the 5 real defects
   that day came from mutation-testing guards, the cheap technique.
3. **The behaviour-cluster grammar that fixes this already exists and is opt-in.** FR-6/7 of
   `deliverable-first` moved the RED to the behaviour level — but a member task must STILL
   carry Tier, Test-author and Proven-by lines, and the cluster still ends at a review
   panel. The cheap path costs the same paperwork as the expensive one.
4. **No skill plans model choice.** Zero agent files declare a `model:`; no skill names which
   dispatches a smaller model serves. `run-cost.py` counts tokens per dispatch but not the
   model that spent them, so the ladder is unmeasurable.
5. **herdr is invisible to the harness.** `netdust-core:herdr-orchestration` carries the
   decisions (two channels, topology-per-working-tree, `bat` tabs, watcher doorbell,
   session-review pane); no netdust-agent skill, command or hook mentions herdr. The
   `building` lesson of 2026-08-09 (two implementers in one working tree corrupting each
   other's integration DB) is exactly the failure a worktree workspace prevents, and the
   spine never reaches for one.

## User stories, prioritized

### P1 — Declarative work pays declarative prices
As the human partner, when a cluster of work is CPT config, field maps, templates or a
service wired onto ntdst-core with no rule of this project's own inside it, the plan
declares it a **behaviour lane** cluster: one outside-observable RED for the cluster, no
per-task test lines, no per-cluster review panel, one review at branch end. The machine
refuses the lane where it is not honest (a security-boundary file, `high` stakes) — never
the other way round.

### P2 — Rules of this project still get the contract lane
As the human partner, a task that encodes a rule this project chose (a role, a window, an
ownership test, a threshold, untrusted parsing, money, a migration) keeps today's grammar:
tier, test-author mode, proven-by, RED-first contract, review panel at the cluster's tier.
Nothing in this spec weakens that lane.

### P3 — The cheapest capable model does each dispatch
As the human partner, every agent persona declares a default model, the building spine
names the model per dispatch kind and lane, and the cost report shows model per dispatch so
the ladder is a measured decision rather than a guess.

### P4 — herdr gives me the overview and the agents the isolation
As the human partner running in herdr, the seam opens the plan for me in a `bat` tab, an
unattended run rings the doorbell, parallel dispatches get their own worktree workspace
instead of sharing a working tree, and a status tab shows the ledger and the tree. Outside herdr
nothing changes.

## Functional requirements

### The lane (kills links 1–3)
- **FR-1:** A `### Cluster` heading (or a `Lane:` line directly beneath it) declares
  `Lane: behaviour` or `Lane: contract`. `gate-check.py` FAILs a cluster with no lane once
  any cluster in the file declares one; a file with no lanes anywhere is a pre-convention
  artifact and reads as all-`contract` (today's behaviour, byte-for-byte). Source: "maybe
  the phases that get tested can be different, maybe the what to test can be different"
  (Stefan, 2026-09-02); the mechanism follows the harness's existing opt-in-then-required
  convention for `Test-author:`.
- **FR-2:** A **behaviour-lane** cluster MUST carry the full behaviour block (`Behaviour:`,
  `Observable:`, `RED until:` — the existing FR-6 grammar) and an `Integration gate:` line;
  its member tasks carry a `(files:)` segment and NOTHING ELSE from the test grammar —
  `gate-check.py` skips `task-tier`, `test-author-mode`, `proven-by` and
  `unit-test-contract` for those members, and WARNs if a member carries any of those lines
  (paperwork drift). Source: invented — approved 2026-09-02 ("ok sounds good" to "the
  per-task test grammar should apply only to tasks gate-check already flags as
  security-boundary… everything else verified at cluster level only").
- **FR-3:** `gate-check.py` FAILs `Lane: behaviour` when any member task's `(files:)`
  segment hits `FILES_SECURITY` or its prose hits `PROSE_SECURITY` (the existing
  detectors), or when the cluster's effective stakes are `high`. The finding names the
  task and the matched term; the fix is to move that task into a contract-lane cluster.
  Source: "A security-boundary file is always D, never E" (harnessed-development, kept);
  approval 2026-09-02.
- **FR-4:** `gate-check.py` WARNs `Lane: contract` on a cluster with no boundary hit under
  non-`high` stakes unless the heading states a reason after a dash (`Lane: contract — encodes
  the 14-day return window`). A stated reason silences the WARN; the planner remains the
  control, the WARN makes over-ceremony visible. Source: invented — approved 2026-09-02;
  mirrors the existing `security-boundary-mode` WARN-never-FAIL posture.
- **FR-5:** A behaviour-lane cluster carries NO `── REVIEW GATE ──` marker; `check_review_gates`
  and `check_review_tiers` require the marker and tier only on contract-lane clusters, and
  the file must end with ONE `── BRANCH REVIEW ──` marker carrying a tier when any
  behaviour-lane cluster exists. Source: invented — approved 2026-09-02 ("one review at
  branch end rather than a panel per cluster").
- **FR-6:** The `building` spine executes a behaviour-lane cluster as: the cluster's RED is
  written first (by the first task's implementer, or inline by the controller when it is a
  one-assertion smoke), every task is one implementer dispatch with no per-task RED and no
  Test-evidence block beyond the `HARNESS-EVIDENCE:` close-out line, the suite stays green
  except the named cluster RED (the hook's existing FR-8 tolerance), and the cluster closes
  on the RED going green + the `Integration gate:` line + the existing `Artifact-diff:`
  comparison when user-facing. No `test-author` feature-test dispatch and no reviewer
  dispatch at the cluster. Source: "Tasks below a behaviour boundary don't need their own
  proof, they need to not break the proof that's already running" (Stefan, 2026-08-09,
  carried); approval 2026-09-02.
- **FR-7:** The `implementer` agent gains a `behaviour` dispatch mode beside `split`/`solo`:
  no self-authored RED, keeps the suite green, closes with the STATUS block and the
  evidence line; it escalates `NEEDS_CONTEXT` when the task edits a path the sensitive-glob
  floor names (`hooks/subagent-stop.py` blocks such a close — after T11's branch review
  taught its mode resolver the lane, see plan G5 — the agent says why before the hook
  does). Source: invented — approved 2026-09-02.
- **FR-8:** Stage 3 runs the shake-out only when the plan's `## Acceptance flows` is not
  N/A, and the branch review at `LIGHT` (one `reviewer`) for a branch whose clusters are
  all behaviour-lane under `standard` or `low` stakes; contract-lane clusters keep their
  cluster panels and the branch review takes the branch's tier as today. Source: invented —
  approved 2026-09-02 ("reviewed once at branch end").
- **FR-9:** `harnessed-development` and `testing-workflow` state the lane rule in one
  sentence each and cite the checker by name; `testing-workflow`'s three questions gain a
  question 0: "is this cluster's work a rule of this project, or config over a framework
  that already has the rule?" Source: "with capable models and for the type of work they do
  80% of the time the tests are getting overkill" (Stefan, 2026-09-02).

### The model ladder (kills link 4)
- **FR-10:** Every agent file under `agents/` declares a `model:` in its frontmatter
  (`haiku` / `sonnet` / `opus` / `inherit`, per Claude Code's subagent contract). Defaults:
  `implementer` inherit; `test-author` sonnet; `reviewer` inherit; `code-simplicity-reviewer`
  sonnet; `security-sentinel` inherit; `invariant-auditor` inherit; `shakeout-qa` sonnet.
  Source: "cheaper models are used where possible… my skills never really mention this or
  plan for it in a smart way" (Stefan, 2026-09-02); the specific defaults are invented —
  approved 2026-09-02.
- **FR-11:** `skills/_shared/model-ladder.md` is the single home of the ladder: per dispatch
  kind × lane, the model the controller passes on the dispatch (behaviour-lane implementer
  → sonnet; ground-truth reads → haiku Explore; contract-lane implementer and split
  test-author → inherit; LIGHT reviewer → sonnet; FULL panel → inherit; shakeout-qa →
  sonnet), with the one rule that overrides it: a dispatch that edits a sensitive-glob path
  never runs below inherit. `building` cites the file at every dispatch site and never
  restates the table. Source: same request; the table is invented — approved 2026-09-02.
- **FR-12:** `bin/run-cost.py` prints a per-model totals block beside its per-dispatch
  table (which already carries `model=` per row, read from the transcript's
  assistant-message `model` field); absent field → `unknown`, never a crash. *(Ground-truth
  correction at T04: the per-dispatch column already existed and run-cost has no `--json`
  mode, so the block is the whole change.)* Source: invented — approved 2026-09-02 (the ladder must be
  measurable or it is another echoed field).

### herdr, at the harness moments (kills link 5)
- **FR-13:** `skills/_shared/herdr-moments.md` is the single home of the harness's herdr
  usage: a table of harness moment → herdr action → when NOT to. It carries only netdust-agent's
  decisions; syntax stays with `herdr --skill` and channel/topology rules stay with
  `netdust-core:herdr-orchestration`, which it cites. Detection is `HERDR_ENV=1`; outside
  herdr every moment is a no-op and the spine reads exactly as today. Source: "using herdr's
  functionality… should be baked in, of course in the most efficient way possible" (Stefan,
  2026-09-02).
- **FR-14:** (seam) `planning`'s seam step, under herdr, opens ONE `spec` tab in the project's
  workspace (`--no-focus`) running `bat` over `plan.md` and `tasks.md` with the gate-check
  verdict, and tells the operator the tab exists. Source: "bat to let me read files"
  (Stefan, 2026-09-02).
- **FR-15:** (isolation) `building`'s Stage 2, under herdr, refuses to dispatch two
  code-editing agents into one working tree: a parallel `[P]` sibling or a contract-lane split
  pair runs in a worktree workspace (`herdr worktree create … --no-focus`) and its result is
  read from git in that worktree, never from the pane. Sequential behaviour-lane work stays
  in the main pane with subagents — no topology is built for work that needs no isolation.
  Source: "avoid git/dev stack errors" (Stefan, 2026-09-02) + the 2026-08-09 building lesson
  (two implementers, one working tree, 14 and 17 phantom failures).
- **FR-16:** (overview) `building` under herdr opens ONE `status` tab per feature
  (`--no-focus`) running `watch` over `bin/loop-check.py <feature>` and `git status --short`
  — the ledger and the tree in one glance — and `/loop` arms
  `scripts/herdr-watcher.sh` on the working pane so an unattended run rings the doorbell on
  block and settle. Source: "improve my overview of what's going on and agents' ability to
  track work" (Stefan, 2026-09-02).
- **FR-17:** (branch review) under herdr, the Stage 3 branch reviewer runs as a herdr agent
  in its own pane with its report opened in a `review` tab, so the operator watches the
  review and reads the findings without scrolling a subagent transcript; cluster-level
  contract reviews stay subagents. Source: invented — approved 2026-09-02 (overview at the
  one review that remains for most work).
- **FR-18:** (compounding) `compounding` Pass B reads `memory/session-review/*-proposals.md`
  when present and folds those proposals into its manifest, so the session-review pane's
  output reaches the learning loop instead of sitting in a file. Source: invented — approved
  2026-09-02 (the pane already exists; its output has no consumer).
- **FR-19:** `hooks/session-start.sh`, when `HERDR_ENV=1`, appends two lines to the injected
  context: the pane/tab/workspace ids and a pointer to `herdr-moments.md`. Source: invented —
  approved 2026-09-02 (cheapest possible detection, no per-skill re-checking).

### dev-stack, at the same moments
- **FR-21:** On a project carrying a `site.yml`, `building` takes every branch decision from
  `netdust-core:dev-stack`, never from a herdr example or a superpowers default: feature
  work starts with `make feature name=<x>` (or a worktree whose `--base` is the integration
  branch read from `site.yml`), a Class D fix starts with `make hotfix` from the production
  branch, atomic commits use `make save` or a plain commit on that branch, and the branch
  finishes with `make finish` — `superpowers:finishing-a-development-branch` is subordinate
  to dev-stack's verbs there. `herdr-moments.md` states the worktree base rule in one line
  and cites dev-stack for the ladder. Source: "avoid git/dev stack errors" + "dev stack is
  important" (Stefan, 2026-09-02); the conflict it resolves is ground-truthed in the plan
  (G9).

### The flow floor — the Makefile is the only door to a rung branch
- **FR-22:** The shared Makefile (`netdust-wp/templates/Makefile`) refuses, with the fix
  named, instead of assuming or self-healing: `feature` / `hotfix` / `finish` / `promote` /
  `release` / `deploy` exit non-zero when `origin` is absent ("no origin — add the remote,
  then re-run"); `_ensure-safe-branch` never creates a rung branch and never silently
  switches — on a rung branch it refuses and names `make feature name=<x>`; `make doctor`
  and `make status` print the flow state first (origin present, current branch role
  feature / hotfix / rung, the next verb). Source: "agents are confused and not always
  following it. sometimes because remote doesn't exist or they just skip it" (Stefan,
  2026-09-02).
- **FR-23:** The branch flow is TESTED, never contacting a server: a
  `scripts/tests/flow-test.sh` sibling of `deploy-test.sh`, run by `make test`, builds a
  temp repo with a bare `origin` and a minimal `site.yml`, and asserts: `feature` then
  `finish` lands the commit on the integration branch only; `hotfix` then `finish` lands
  it on production AND back down into review and integration; `finish` refuses on a rung
  branch; the deploy gate refuses a dirty tree, a wrong branch and an unpushed HEAD; every
  verb refuses without `origin` and names the fix. Source: "this can only be the case when
  the makefile works" (Stefan, 2026-09-02).
- **FR-24:** On a project carrying `site.yml`, `hooks/pretooluse-guard.py` DENIES (not
  asks) a raw git write that bypasses the flow: `git commit` while on a rung branch,
  `git merge` / `git rebase` / `git reset --hard` on a rung branch, `git push` of a rung
  branch, `git checkout -b` / `git switch -c` while on a rung branch, `git branch -D` of a
  rung, and any piping of input into `make ship|release|promote|deploy` (`echo yes |`,
  `yes |`, `<<<`). The denial names the make verb that does it right. Rung names are read
  from `site.yml` through `scripts/site`, falling back to `main|master|staging|development`
  when the script is absent; every tooling failure fails OPEN like the rest of the hook.
  `make` invocations are never inspected — the verbs are the door. Source: "the flow in it
  is used and respected and thus files are in correct branch" (Stefan, 2026-09-02); the
  deny-not-ask posture follows the upstream-invocation floor's reasoning (agent-side
  correction, one tool call, no human arbitration).
- **FR-25:** On a `site.yml` project the harness enters and leaves through the flow:
  `building` Stage 2 refuses to dispatch unless the current branch is `feature/*` or
  `hotfix/*` (it runs `make feature` / `make hotfix` first, or hands back); `/loop` refuses
  to arm on a rung branch; Stage 3 closes with `make finish`, and
  `superpowers:finishing-a-development-branch`'s merge/PR options are never offered on such
  a project; `make health` runs before `make release`; `make ship` and `/deploy` to
  production only on the operator's explicit ask in that turn (dev-stack's existing rule,
  cited, not restated). `netdust-core:dev-stack` gains one paragraph naming this floor as
  the machine half of its own "what gets said, what to run" table. Source: "going through
  the flow until shipping to production" (Stefan, 2026-09-02).

### Record
- **FR-20:** The plugin version bumps 0.20.0 → 0.21.0; the manifest description names the
  lane; `_shared/calibrations.md` gains `yootheme-6-of-6-tier-a` (the corpus evidence above);
  this spec's own `tasks.md` is re-shaped to the lane grammar as the first self-hosting
  artifact once T01 lands. Source: invented — approved 2026-09-02.

## Acceptance criteria

- **AC-1:** A fixture `tasks.md` with a `Lane: behaviour` cluster whose members carry only
  `(files:)` segments passes gate-check; the same fixture with one member touching
  `auth/Guard.php` FAILs naming the task and the term.
- **AC-2:** The existing green corpus (this repo's `specs/*`, the checker's fixture set)
  produces zero new findings — no lane lines means today's checker, byte-for-byte.
- **AC-3:** `run-cost.py` on a fixture transcript with two dispatches on different models
  prints both models and a per-model total; a transcript lacking the field prints `unknown`.
- **AC-4:** Every `agents/*.md` frontmatter parses with a `model:` key holding one of the
  four allowed values (tested).
- **AC-5:** `session-start.sh` with `HERDR_ENV=1` and the three ids set emits the two lines;
  without it, its output is byte-identical to today (tested).
- **AC-7:** In a temp repo with a bare origin, `flow-test.sh` passes; with `origin`
  removed, every flow verb exits non-zero naming the fix (tested, never a server).
- **AC-8:** The guard denies `git commit` on `development` and `echo yes | make ship` in a
  `site.yml` project, and allows both when no `site.yml` exists (tested).
- **AC-6:** No skill text restates herdr syntax or the ladder table — each cites its single
  home (grep at the Cluster D gate).

## Success criteria

- **SC-1:** `gate-check.py` accepts a behaviour-lane cluster whose 4 member tasks carry 0
  per-task test lines, in 1 command, exit 0.
- **SC-2:** The plugin's own test runner passes with 0 failed modules on this box (the
  `test_integration_contract` live-corpus seam counts as skipped, as today), with ≥ 12 new
  cases across the checker, run-cost, agent-frontmatter and session-start surfaces.
- **SC-3:** This spec's re-shaped `tasks.md` (FR-20) contains 1 behaviour-lane cluster and
  passes gate-check with exit 0 — self-hosting.
- **SC-4:** 7 of 7 agent files declare a `model:`; 0 skill files restate the ladder table
  (grep count of the table's first row outside `_shared/model-ladder.md` is 0).
- **SC-5:** `run-cost.py --help` and a fixture run both exit 0 and the fixture table has a
  `model` column on 100% of its rows.
- **SC-7:** `flow-test.sh` asserts ≥ 8 flow cases and 5 refusal cases and exits 0 on the
  template; the guard test module adds ≥ 8 rung-floor cases (deny × 6, allow × 2).
- **SC-6:** 0 occurrences of a herdr subcommand string (`herdr worktree`, `herdr tab`,
  `herdr agent`) outside `_shared/herdr-moments.md` within `plugins/netdust-agent/**`.

## Security-relevant surfaces

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [x] None of the above

The artifacts parsed are repo-local files the team authors; `run-cost.py` reads local
transcripts strictly read-only and emits counts plus a model name, never message content;
herdr commands run with the operator's own permissions in the operator's own session.
The one guard this spec touches — the sensitive-path floor — is kept, not relaxed: FR-3
and FR-7 both route sensitive paths to the contract lane.

## User-facing surfaces

- [ ] A new or changed public page / view / listing
- [ ] A new or changed admin screen or editing surface
- [ ] An endpoint a client or agent will drive
- [x] None of the above

Developer/agent tooling; its behavioural contract lives in the pytest-style cases each task
names and in the self-hosting gate-check run.

## Clarifications

- Q: Lane on the task or on the cluster? → A: the cluster. The 80% work is whole features
  of declarative clusters; a rule-encoding task goes into its own contract-lane cluster,
  which the harness already prefers ("riskiest first", "irreversible = solo").
- Q: Does the behaviour lane drop the cluster RED too? → A: No. One outside-observable RED
  per cluster is the cheapest proof that the cluster did anything; it is what the
  integration gate closes on. What goes is the per-task RED, the per-task paperwork, the
  post-cluster test-author dispatch and the per-cluster panel.
- Q: Machine-decided lane or planner-decided? → A: planner-decided, machine-refused in the
  unsafe direction only (FR-3), machine-warned in the wasteful direction (FR-4). The
  detectors are keyword heuristics; a FAIL on a false positive would teach people to route
  around the gate, so the wasteful direction stays a WARN.
- Q: Model override — agent file or dispatch? → A: both, per Claude Code's contract: the
  file holds the persona's default, the controller passes the ladder's model on the
  dispatch where the lane says so. The plan's ground-truth section records the documented
  precedence before T07 relies on it.
- Q: Should herdr become a hard dependency of netdust-agent? → A: No. `HERDR_ENV=1` gates
  every moment; the plugin stays standalone and the moments file cites
  `netdust-core:herdr-orchestration` the way `building` already cites
  `netdust-wp:wp-testing`.

## Assumptions

- Claude Code subagent frontmatter accepts `model:`; the dispatch-time `model` parameter of
  the Agent tool exists. Ground-truthed in the plan (G6) against the docs before T07.
- `hooks/subagent-stop.py`'s FR-8 tolerance (`cluster-open` / `cluster-close` ledger
  events) is already shipped and tested; the behaviour lane reuses it unchanged.
- herdr's CLI syntax is read from `herdr --skill` on the operator's machine at run time;
  this spec never pins it.

## Out of scope

- Changing Tier A/B definitions, the erosion guard, D1's split rule, or the sensitive-path
  floor — the contract lane is today's grammar untouched.
- Any netdust-wp / netdust-statamic SKILL change; the netdust-wp Makefile template and
  its `scripts/tests/` ARE in scope (FR-22, FR-23), as is one paragraph in
  `netdust-core:dev-stack` (FR-25).
- Dollar pricing in `run-cost.py`; model choice for the MAIN session (the operator's call).
- A herdr plugin (`herdr-plugin.toml`) reacting to agent state as events — the watcher
  script stays the doorbell.
- Re-shaping existing feature dirs in other repos to the lane grammar (they read as
  all-contract until their planners opt in).
