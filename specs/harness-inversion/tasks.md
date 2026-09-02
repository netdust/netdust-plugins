# Tasks — Harness inversion

**Spec:** `specs/harness-inversion/spec.md` · **Plan:** `specs/harness-inversion/plan.md`
**Loop budget: ~21 iterations** (14 tasks + 5 review clusters + one fix round each on Clusters A and E).

**Standing line for every checker task (T01–T03):**
> New checks follow the house shape — a `check_*(text, f: Findings)` function reading the
> shared parsers, fixtures in `tests/test_spec_gate_check.py`'s existing style, fenced-block
> stripping inherited. RED-first against the real script. Existing cases stay untouched;
> AC-2 is the lock: an artifact with no `Lane:` line anywhere produces byte-identical findings.

**Standing line for every text task (T07–T10):**
> Text cites the mechanical check or the single-home file by exact name; no skill text may
> promise an enforcement the machine doesn't perform (the ladder is MEASURED by run-cost,
> not hook-enforced — say so). No herdr subcommand strings and no ladder rows outside their
> single homes (SC-4, SC-6).

---

## Phase 1 — all five clusters

### Cluster A — the checker lane grammar (3 tasks · effective stakes: standard · provisional tier: STANDARD)

Lane: contract — checker logic with RED-first contracts of its own

Behaviour: `gate-check.py` accepts a behaviour-lane cluster whose member tasks carry only `(files:)`, and refuses the same cluster the moment one member touches a security-boundary path.
Observable: two commands — the bare-members fixture exits 0; the fixture with `auth/Guard.php` in one member's files exits 1 with a `cluster-lane` finding naming the task and the term.
RED until: `plugins/netdust-agent/tests/test_spec_gate_check.py::test_lane_behaviour_bare_members_pass`

- [x] T01 [Tier A] Parse `Lane: behaviour | contract` on a cluster (heading label or a line between the heading and the first task) and implement `check_cluster_lanes()`: presence rule (no lanes anywhere → silent, today's behaviour; some → every cluster must declare one, FAIL naming the bare cluster); FR-3 FAIL when a behaviour-lane member hits `_boundary_hit()` or the cluster's effective stakes are `high`; FR-4 WARN on a contract-lane cluster with no boundary hit under non-high stakes unless the lane line carries a dash-reason.  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T01 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) fixture with two lane-declared clusters, no boundary hits → pass; (b) one cluster lane-declared, sibling bare → FAIL naming the sibling; (c) `Lane: behaviour` with a member whose files hit `auth/` → FAIL naming task + term; (d) `Lane: behaviour` under a per-cluster stakes row of `high` → FAIL; (e) `Lane: contract` with no boundary hit and no reason → WARN; (f) same with `Lane: contract — encodes the return window` → silent; (g) no `Lane:` anywhere → zero findings from this check (AC-2 lock).
  (FR-1, FR-3, FR-4)

- [x] T02 [Tier A] Make the four per-task checks lane-aware: `check_task_tiers`, `check_test_author_mode`, `check_proven_by`, `check_unit_test_contract` skip members of a behaviour-lane cluster; a behaviour-lane member that DOES carry any of those lines gets one `lane-drift` WARN; a behaviour-lane cluster MUST carry the full behaviour block and an `Integration gate:` line (FAIL otherwise, reusing `_block_status`).  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T02 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) behaviour-lane cluster, 4 bare members, full block + integration gate → all four per-task checks pass and report the skipped count; (b) same members but one carries `Test-author: solo` → `lane-drift` WARN naming it; (c) behaviour-lane cluster with a partial block → FAIL naming the missing line; (d) behaviour-lane cluster with no `Integration gate:` → FAIL; (e) contract-lane cluster in the same file keeps every per-task check exactly as today.
  (FR-2, SC-1)

- [x] T03 [Tier A] Lane-aware review markers: `check_review_gates` and `check_review_tiers` require `── REVIEW GATE ──` + tier only on contract-lane clusters; when any behaviour-lane cluster exists the file must end with exactly one `── BRANCH REVIEW ──` marker carrying a tier (FAIL when absent or tier-less; WARN when a behaviour-lane cluster carries a review marker anyway).  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T03 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) behaviour-lane clusters without review markers + one tiered branch marker → pass; (b) no branch marker → FAIL; (c) branch marker without a tier → FAIL; (d) a behaviour-lane cluster carrying a review marker → WARN; (e) a lane-less file → today's marker findings unchanged (AC-2).
  (FR-5)

**Integration gate (Cluster A):** three commands after T01–T03: (1) the bare-members fixture → exit 0 (SC-1); (2) the `auth/Guard.php` fixture → exit 1 naming `cluster-lane`; (3) `bash plugins/netdust-agent/tests/run.sh` → 0 failed modules except the recorded live-corpus skip, and `gate-check.py` over every dir in `specs/` produces findings identical to the pre-change run captured at T01 step 0 (AC-2).

── REVIEW GATE ── (tier: STANDARD — checker logic, no 1a surface; escalates one-way to FULL if any finding touches FR-3's refuse path.)

---

### Cluster B — machine layer (3 tasks · effective stakes: standard · provisional tier: STANDARD)

Lane: contract — read-only tooling and an env-gated hook, each with a RED-first contract

- [x] T04 [Tier A] `run-cost.py` per-model totals block beside the per-dispatch table (whose `model=` column already existed — ground-truth correction; there is no `--json` mode to extend); a dispatch without the field reads `unknown`; fixture transcripts in the existing test extended, never rewritten.  (files: plugins/netdust-agent/bin/run-cost.py, plugins/netdust-agent/tests/test_run_cost.py)
  Test-author: solo — standard stakes, read-only reporting over local files, not a security-boundary category.
  Proven by: new test — the model-column cases in `test_run_cost.py`.
  Unit test: RED-first. (a) two dispatches on two models → both names in the table and a per-model total; (b) a record lacking `model` → `unknown`, exit 0; (c) `--json` carries `model` per dispatch; (d) the transcript dir is byte-identical after the run (the existing read-only assertion, re-asserted).
  (FR-12, SC-5, AC-3)

- [x] T05 [Tier A] `session-start.sh` appends, only when `HERDR_ENV=1`, two lines to the injected context — the pane/tab/workspace ids and a pointer to `skills/_shared/herdr-moments.md` — and stays byte-identical otherwise.  (files: plugins/netdust-agent/hooks/session-start.sh, plugins/netdust-agent/tests/test_session_start.py)
  Test-author: solo — standard stakes, an env-gated two-line append with no attacker-supplied input; the `session` token in the path is the hook's name, not a session surface.
  Proven by: new test — the herdr cases in `test_session_start.py`.
  Unit test: RED-first. (a) `HERDR_ENV=1` + the three ids → the two lines present, ids echoed; (b) `HERDR_ENV` unset → output identical to the existing golden case; (c) `HERDR_ENV=1` with ids unset → the pointer line only, no empty-id noise.
  (FR-19, AC-5)

- [x] T06 [Tier B] Declare `model:` in every `agents/*.md` frontmatter per the spec's defaults, author `skills/_shared/model-ladder.md` (dispatch kind × lane → model, the sensitive-path floor as the one override, the honest line that the ladder is measured by run-cost and not hook-enforced), and add `tests/test_agent_frontmatter.py` pinning that every agent declares one of the allowed values.  (files: plugins/netdust-agent/agents/implementer.md, plugins/netdust-agent/agents/test-author.md, plugins/netdust-agent/agents/reviewer.md, plugins/netdust-agent/agents/code-simplicity-reviewer.md, plugins/netdust-agent/agents/security-sentinel.md, plugins/netdust-agent/agents/invariant-auditor.md, plugins/netdust-agent/agents/shakeout-qa.md, plugins/netdust-agent/skills/_shared/model-ladder.md, plugins/netdust-agent/tests/test_agent_frontmatter.py)
  Test-author: solo — Tier B.
  Proven by: new test — `test_agent_frontmatter.py` (7/7 agents declare an allowed value; the ladder file names every agent it routes).
  Unit test: declarative frontmatter pinned by the new module: (a) each of the 7 files parses with `model:` in {haiku, sonnet, opus, inherit}; (b) `model-ladder.md` mentions every agent name once in its table; (c) no other file under `skills/**` contains the table's first row (SC-4).
  (FR-10, FR-11, SC-4, AC-4)

**Integration gate (Cluster B):** `bash plugins/netdust-agent/tests/run.sh` green (live-corpus skip excepted); `run-cost.py` against this box's own session transcripts prints a `model` on every row; `HERDR_ENV=1 bash hooks/session-start.sh` shows the two lines and the plain run shows none.

── REVIEW GATE ── (tier: STANDARD)

---

### Cluster C — the spine texts (4 tasks · effective stakes: standard)

Lane: behaviour
Behaviour: every changed skill and command cites its single home and its mechanical check by name, and restates neither.
Observable: `grep -rE 'herdr (worktree|tab|agent)\b' plugins/netdust-agent --include='*.md'` hits only `_shared/herdr-moments.md`; `grep -rl '| ground-truth read' plugins/netdust-agent/skills plugins/netdust-agent/agents plugins/netdust-agent/commands` hits only `_shared/model-ladder.md`.
RED until: `plugins/netdust-agent/tests/test_agent_frontmatter.py::run`

- [x] T07 `building` SKILL.md: the behaviour-lane execution path (cluster RED first, one implementer per task with no per-task RED, no post-cluster test-author, no cluster panel, close on RED-green + integration gate + `Artifact-diff:`), the contract lane stated as today's path unchanged, the Stage 3 rule (shake-out only with real acceptance flows; LIGHT branch review for all-behaviour branches under non-high stakes), dispatch sites citing `model-ladder.md` by name, the herdr moments cited from `herdr-moments.md` (isolation rule for `[P]` and split pairs; the status tab; the branch-review pane), and every branch decision on a `site.yml` project routed to `netdust-core:dev-stack` (`make feature` / `make hotfix` / `make finish`; worktree base = the integration branch from `site.yml`, never a hard-coded `master`).  (files: plugins/netdust-agent/skills/building/SKILL.md)
  (FR-6, FR-8, FR-11, FR-15, FR-16, FR-17, FR-21)

- [x] T08 Agent bodies: `implementer` gains the `behaviour` dispatch mode (no self-authored RED, suite green except the ledger-named cluster RED, STATUS block + `HARNESS-EVIDENCE:` line, `NEEDS_CONTEXT` when the task edits a sensitive-glob path — said before the hook blocks it); `test-author` Mode 1 is scoped to contract-lane clusters and behaviour-lane cluster REDs on request; `reviewer` notes the branch-review-only posture for behaviour-lane branches and where its report lands under herdr.  (files: plugins/netdust-agent/agents/implementer.md, plugins/netdust-agent/agents/test-author.md, plugins/netdust-agent/agents/reviewer.md)
  (FR-7)

- [x] T09 `planning` seam (under herdr: the `spec` tab with `bat` over plan + tasks + the gate verdict, `--no-focus`, announced), `harnessed-development` (one sentence: lane is decided per cluster at plan time, machine-refused in the unsafe direction, the class dial unchanged), and `testing-workflow` (question 0 — a rule of this project, or config over a framework that already has the rule? — routing to lane before tier; the tier table applies inside the contract lane only).  (files: plugins/netdust-agent/skills/planning/SKILL.md, plugins/netdust-agent/skills/harnessed-development/SKILL.md, plugins/netdust-agent/skills/testing-workflow/SKILL.md)
  (FR-9, FR-14)

- [x] T10 `skills/_shared/herdr-moments.md` (moment → primitive → when NOT to; cites `netdust-core:herdr-orchestration` sections for channels/topology/traps and `netdust-core:dev-stack` for the worktree base rule; no syntax), `/loop` arms `scripts/herdr-watcher.sh` on the working pane under herdr, `compounding` Pass B reads `memory/session-review/*-proposals.md`, `/shakeout` runs `shakeout-qa` only when `## Acceptance flows` is not N/A and takes the branch tier from the lane rule.  (files: plugins/netdust-agent/skills/_shared/herdr-moments.md, plugins/netdust-agent/commands/loop.md, plugins/netdust-agent/skills/compounding/SKILL.md, plugins/netdust-agent/commands/shakeout.md)
  (FR-13, FR-16, FR-18, SC-6, AC-6)

**Integration gate (Cluster C):** coherence greps across `plugins/netdust-agent/**`: 0 herdr subcommand strings outside `_shared/herdr-moments.md` (SC-6); 0 ladder table rows outside `_shared/model-ladder.md` (SC-4); every new claim in the four skill texts names its check (`check_cluster_lanes`, `run-cost`, `test_agent_frontmatter`, the ledger events); `gate-check.py specs/deliverable-first` and `specs/harness-efficiency` still exit as before (AC-2 on the live corpus).


---

### Cluster D — the record (1 task · effective stakes: low · provisional tier: LIGHT)

Lane: contract — one task that closes on the self-hosting gate, no behaviour to observe from outside

- [x] T11 [Tier B] Close the record: `_shared/calibrations.md` gains `yootheme-6-of-6-tier-a` (the corpus evidence: 6/6 Tier A, 6/6 `new test`, incl. a module-wire and a lookup table; 6 reviewer dispatches → 2 findings on the josworld run); `evals/trigger-queries.json` gains cases for `testing-workflow` ("this cluster is just CPT config on ntdst-core — do the tasks need tests?" → trigger) and `building` ("run the plan; the clusters are behaviour lane" → trigger); bump `plugin.json` 0.20.0 → 0.21.0 with the lane named in the description; re-shape THIS feature's `tasks.md` so Cluster C becomes `Lane: behaviour` (bare members, the existing block) and the file ends with `── BRANCH REVIEW ──` — the first self-hosting artifact — and re-run gate-check to exit 0.  (files: plugins/netdust-agent/skills/_shared/calibrations.md, plugins/netdust-agent/evals/trigger-queries.json, plugins/netdust-agent/.claude-plugin/plugin.json, specs/harness-inversion/tasks.md)
  Test-author: solo — Tier B.
  Proven by: machine gate — `gate-check.py specs/harness-inversion` exit 0 after the re-shape (SC-3) and the full runner green (SC-2).
  Unit test: no unit test: Tier B, documentation, eval cases and version metadata.
  (FR-20, SC-2, SC-3)

**Integration gate (Cluster D):** `python3 plugins/netdust-agent/bin/gate-check.py specs/harness-inversion` → exit 0 with one behaviour-lane cluster reported (SC-3); `bash plugins/netdust-agent/tests/run.sh` → 0 failed modules beyond the recorded live-corpus skip (SC-2); `git diff --stat` shows no edit under `plugins/netdust-core/` other than T14's dev-stack paragraph.

── REVIEW GATE ── (tier: LIGHT)

---

### Cluster E — the flow floor (3 tasks · effective stakes: high · provisional tier: FULL)

Lane: contract

- [x] T12 [Tier A] Makefile refusals and the flow test: every flow verb exits non-zero naming the fix when `origin` is absent; `_ensure-safe-branch` refuses on a rung branch (never switches, never creates); `doctor` and `status` print the flow state first; `scripts/tests/flow-test.sh` builds a temp repo + bare origin + minimal `site.yml` and asserts the flow and its refusals; `make test` runs it.  (files: plugins/netdust-wp/templates/Makefile, plugins/netdust-wp/templates/scripts/tests/flow-test.sh)
  Test-author: solo — A-lite: the contract is a table of shell exit codes over a temp repo, enumerable from the spec; no attacker-supplied input; high stakes are carried by the FULL review and by T13's split, not by a second author on a Makefile.
  Proven by: new test — `flow-test.sh` (SC-7), RED against the current template first.
  Unit test: RED-first, in the temp repo. (a) `feature`+`finish` → commit on integration only; (b) `hotfix`+`finish` → on production, review and integration; (c) `finish` on a rung → refused; (d) deploy gate refuses dirty / wrong branch / unpushed; (e) origin removed → each of feature/finish/promote/release/deploy refuses naming the fix; (f) `_ensure-safe-branch` on `main` → refused with `make feature` named, branch unchanged; (g) `doctor` prints the flow block first.
  (FR-22, FR-23, AC-7, SC-7)

- [x] T13 [Tier A] The guard's rung floor: in a `site.yml` project, deny the raw git writes FR-24 lists and any piped input into `make ship|release|promote|deploy`, naming the make verb; rung names via `scripts/site`, fallback list when absent; no `site.yml` → today's behaviour byte-for-byte; every tooling failure fails open.  (files: plugins/netdust-agent/hooks/pretooluse-guard.py, plugins/netdust-agent/tests/test_pretooluse_guard.py)
  Test-author: split
  Proven by: new test — the rung-floor cases in `test_pretooluse_guard.py`.
  Unit test: RED-first, denial paths mandatory. (a) `git commit -m x` on `development` → deny naming `make save`/`make feature`; (b) `git merge feature/x` on `staging` → deny naming `make finish`/`make promote`; (c) `git push origin development` → deny; (d) `git checkout -b feature/y` while on `development` → deny naming `make feature`; (e) `echo yes | make ship` and `make release <<< yes` → deny; (f) `git commit` on `feature/x` → allow; (g) same commands with no `site.yml` → allow (today); (h) `scripts/site` missing → fallback rung list applies; (i) unreadable cwd → fail open.
  (FR-24, AC-8, SC-7)

- [x] T14 [Tier B] Enter and leave through the flow: `building` Stage 2 entry asserts `feature/*` or `hotfix/*` on a `site.yml` project (runs `make feature`/`make hotfix` or hands back), Stage 3 closes with `make finish` and never offers `finishing-a-development-branch`'s merge/PR options there, `make health` precedes `make release`; `/loop` refuses to arm on a rung branch; `netdust-core:dev-stack` gains one paragraph naming the floor as the machine half of its intent table.  (files: plugins/netdust-agent/skills/building/SKILL.md, plugins/netdust-agent/commands/loop.md, plugins/netdust-core/skills/dev-stack/SKILL.md)
  Test-author: solo — Tier B.
  Proven by: machine gate — T12's flow test and T13's guard cases are the enforcement; this text cites `flow-test.sh` and the guard floor by name (standing line).
  Unit test: no unit test: Tier B, prose over mechanics landed in T12/T13.
  (FR-25)

**Integration gate (Cluster E):** in a scratch WordPress project scaffolded from the template with a bare origin: `make test` green including `flow-test.sh`; with the netdust-agent hook active, `git commit` on `development` is denied and `make feature name=x && git commit` is allowed; `bash plugins/netdust-agent/tests/run.sh` green (live-corpus skip excepted); `make ship` is NOT run.

── REVIEW GATE ── (tier: FULL — `security-sentinel` on the guard diff; the floor is the harness's own enforcement boundary.)

── BRANCH REVIEW ── (tier: LIGHT — the behaviour-lane cluster's only panel; contract clusters carried their own gates)
