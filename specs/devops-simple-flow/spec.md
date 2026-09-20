# Spec — Simple flow: features from main, staging is the release

**Repo:** `netdust-plugins` · **Plugins:** `netdust-devops` (`dist/Makefile.netdust`, `dist/scripts/tests/flow-test.sh`, `skills/devops`, `bin/new-project`, `templates/`) · `netdust-agent` (`hooks/pretooluse-guard.py` — a verb-list edit only, `skills/building`) · `netdust-core` (`RULES.md`)
**Replaces:** `specs/devops-main-flow` (branch `feature/devops-main-flow`, built and reviewed 2026-09-16…19, never merged). That branch stays as a reference; this spec starts from `main`.
**Provenance:** Stefan, 2026-09-19, after reading the main-flow build: "this is a super complex setup, not just a makefile but script with it too"; on the server-side alternative: "i don't like CI per site, paid github, mariadb etc... either. simple simple". The original trigger stands (2026-09-16): "ik werk aan A, staat op development... A werkt nog niet maar B wel".

## Problem / why

The three-rung flow leaks unfinished work to staging, because features branch from an integration
branch that only grows. `devops-main-flow` fixed that, and cost a 538-line engine, three custom
ref namespaces, a `release` composition, tree-evidence, and an agent guard that grew from 616 to
1160 lines re-implementing the policy as text matching — which never converged under review.

Two decisions caused nearly all of it: state and evidence lived in refs that anyone can write (so
they needed a guard), and "accepted" was a state separate from "on staging" (so it needed a second
composition and a way to prove the two equal). With ONE staging server neither is necessary.

## The idea

**Staging is the release.** Staging is a disposable branch: `main` plus the features promoted onto
it. What ships is the exact staging commit that was deployed and looked at. To ship B but not A,
take A off staging first. There is no `release` branch, no `finish`, no stored selection, no
evidence ref.

## User stories

- **US-1 (P1)** — I work on A, B and C in parallel, each from main. All three can sit on staging
  together; I ship two and the third stays out of production.
- **US-2 (P1)** — What I ship is the commit staging runs. Nothing else reaches production.
- **US-3 (P1)** — A hotfix goes main → production without a staging round, never without the gate.
- **US-4 (P2)** — I take a feature off staging with a verb.
- **US-5 (P3)** — A project still declaring a development branch is told how to go back.

## Functional requirements

- **FR-1:** `make feature name=<x>` and `make hotfix name=<x>` branch from `origin/<production>`.
  Source: Stefan, 2026-09-16 — "hotfix/feature start with main"
- **FR-2:** The flow verbs are `feature · hotfix · save · promote · unpromote · gate · ship`.
  The integration branch, `BR_INTEG`, and the old `finish` and release verbs are removed, not aliased.
  Source: Stefan, 2026-09-19 — "simple simple"
- **FR-3:** `make promote name=<x>` rebuilds staging as `origin/<production>` + every feature
  already on staging + `feature/<x>` at its origin tip, each as one `--no-ff` merge with the subject
  `promote: <name>`, in name order. `make unpromote name=<x>` rebuilds without `<x>`. Neither deploys.
  Source: Stefan, 2026-09-19 — "do i keep ability to test 3 features at once, but ship 2 to production?"
- **FR-4:** The list of features on staging is read from staging itself: the `promote: <name>`
  merge commits between production and the staging tip. A feature that is not being re-promoted is
  merged again at the SAME commit as before (the merge's second parent), so promoting B never
  pulls new, unseen commits of A onto staging. No other state is stored anywhere.
  Source: invented — approved 2026-09-19 (Stefan approved the spec with this choice flagged to him: a promoted feature stays pinned, as in the main-flow spec, without refs)
- **FR-5:** A rebuild happens in a throwaway worktree and ends in ONE
  `git push --force-with-lease=<staging>:<old tip>`. A merge conflict aborts naming the feature, and
  nothing is pushed. A lost lease exits non-zero and says to run it again.
  Source: the main-flow spec's atomic-rebuild and two-sessions requirements, kept because they cost one flag
- **FR-6:** `make ship`, feature path: run with the staging branch checked out, clean tree.
  It refuses unless `HEAD` = `origin/<staging>` = the commit `deployed/staging` names on origin, and
  `origin/<production>` is an ancestor of it. It then runs `commands.gate` there; on a green gate
  it asks for the typed `yes`, takes both backups, fast-forwards the production branch to that
  commit, and deploys production through the existing chain.
  Source: Stefan, 2026-09-16 — "what I ship is exactly … what was deployed on staging"; the suite
  runs inside ship because there is no evidence to store — Stefan, 2026-09-19, "simple simple"
- **FR-7:** `make ship`, hotfix path: from a `hotfix/*` branch, clean tree, `origin/<production>` an
  ancestor of `HEAD`. Gate, typed `yes`, backups, fast-forward, deploy. No staging condition.
  Source: the main-flow spec's hotfix exception, unchanged in intent — Stefan, 2026-09-16: "Hotfix: ship"; a hotfix still requires the gate
- **FR-8:** After any ship, staging is rebuilt on the new production tip from the features still on
  it; a feature whose pinned commit is now contained in production is dropped from the list.
  Source: the main-flow spec's post-ship rebuild, without refs — "No merge-down choreography."
- **FR-9:** Every production guard survives: `_need-tty` first in every writing verb, the clean-tree
  and free-branch checks BEFORE anything is pushed, `_deploy-gate`, both backups, and a typed
  confirmation that `ship` ALWAYS asks for (`environments.production.confirm` governs `deploy` only).
  Source: Stefan's global rules §9; his ruling R49-1 on the main-flow branch review ("Always prompt on ship") and that review's ship-ordering finding
- **FR-10:** On a project declaring `environments.development.branch`, the flow verbs refuse, naming
  the migration and the command shape that restores the previously vendored core
  (`git checkout <commit before the update> -- Makefile.netdust mk scripts .netdust-devops`, with
  `git log --oneline -- .netdust-devops` to find it). Every other verb keeps working.
  Source: the main-flow spec's unmigrated-project requirement (Stefan's 2026-09-16 ruling on migration), minus the history walk
- **FR-11:** `bin/new-project` scaffolds `main` and `staging` only; the templates declare no
  development environment.
  Source: Stefan, 2026-09-16 — "hebben we wel een branch zoals development nodig?"; ported as built on the main-flow branch
- **FR-12:** The flow lives in `Makefile.netdust`. No engine script, no `refs/netdust/*`, no
  `release` branch. If the rebuild recipe does not fit one screen, the design is wrong — stop.
  Source: Stefan, 2026-09-19 — "not just a makefile but script with it too"
- **FR-13:** The agent guard keeps the floor it had on `main` before this work (raw commit, merge,
  push on a branch bound to an environment) and updates its confirming-verb list and hints to
  FR-2's verbs. The evidence-ref floor, the `.git/` floor, the `make _<leaf>` rule and the `cd`
  inference built on `feature/devops-main-flow` are NOT ported.
  Source: the final simplicity review, 2026-09-19 — "how many more spellings is a text-matching
  floor expected to swallow"; Stefan — "simple simple"
- **FR-14:** `flow-test.sh` exercises every verb and refusal against a bare origin, contacts no
  server, and stays under ~500 lines and 2 minutes.
  Source: the vendored flow test's own contract ("exercised for real in a throwaway repo with a bare origin … Never contacts a server"), with a size budget — Stefan, 2026-09-19: "simple simple"
- **FR-16:** Before it pushes, a rebuild reports — on one line, never a refusal — how many commits on
  the OLD staging branch are in neither the new staging nor production nor the feature being taken
  off, and prints the old tip so they stay recoverable. An everyday promote or unpromote prints
  nothing. (A project migrated from the old flow loses its accumulated staging history on the first
  rebuild; this is the line that says so.)
  Source: Stefan, 2026-09-19 — ruling R49-3 on the main-flow branch review: "Report it"

- **FR-15:** The devops skill, `building`, `herdr-moments` and `RULES.md` describe this flow.
  Source: Stefan, 2026-09-16 — "Ja, alles in deze spec": every text moves to the vocabulary that exists

## Acceptance criteria

- **US-1** — *Given* A, B, C promoted, *then* staging's tree = main+A+B+C. *When* I unpromote C,
  deploy staging and ship, *then* production = main+A+B and C is in neither. *When* I promote C
  again, *then* staging = new-main+C.
- **US-1** — *Given* A promoted, then a new commit pushed to `feature/A`, *when* I promote B,
  *then* staging carries A at the commit I promoted, not the new one.
- **US-2** — *Given* staging promoted but not deployed since, *when* I ship, *then* it refuses
  naming `deployed/staging`, and nothing is pushed. *Given* a red gate, *then* the same.
- **US-3** — *Given* a hotfix with a green gate, *when* I ship, *then* production = main+H with 0
  staging deploys, and staging = main+H + what was on it.
- **US-4** — *Given* a conflict between A and B, *when* I promote B, *then* it exits non-zero
  naming B and `git ls-remote origin` is unchanged.

## Success criteria

- **SC-1:** 0 servers contacted by `flow-test.sh`.
- **SC-2:** 3 features on staging at once; 2 shipped; 0 commits of the third in production.
- **SC-3:** 0 remote changes after a conflicting promote, a lost lease, a red gate, a declined
  confirmation, a dirty tree (5 refusals, each `ls-remote` byte-identical).
- **SC-4:** 0 files under `dist/scripts/` added by this spec; 0 refs under `refs/netdust/`.
- **SC-5:** `Makefile.netdust` grows by ≤ 100 lines over `main`; the guard by ≤ 20.
- **SC-6:** `flow-test.sh` ≤ 500 lines and ≤ 2 minutes. (Raised from 350 by Stefan, 2026-09-19, after T02: the
  estimate predated the first test; the 2-minute ceiling is the one that guards against the old suite.)
- **SC-8:** 1 report line when a rebuild drops a commit nothing explains; 0 on an everyday promote and 0
  on an unpromote.
- **SC-7:** 0 lines in the four plugins teach the integration rung, the old `finish`, or the
  release verb.

## Security-relevant surfaces

- [x] Production release gate — `ship` and its hotfix path
- [ ] everything else

## User-facing surfaces

- [x] Operator CLI — the seven verbs and their refusals

## Assumptions — read these; each is a thing the complex version did and this one does not

- **The operator is trusted and the gate result is not stored.** `ship` runs the suite itself,
  so there is nothing to forge. Cost: every ship waits for the suite.
- **An agent's rule is *don't*, not *can't*.** The terminal check is a speed bump. No floor guards
  `deployed/staging`; forging it buys an agent nothing it could not do with a raw deploy.
- **"Accepted" is not a state.** Staging's contents are the release. While a release is being
  looked at, a feature that is not shipping is off the staging server — true of the complex version
  too (`candidate` overwrote staging); here it is simply visible.
- **Both deploys run from a real checkout** (staging's, then production's), so git-ignored build
  output is the same in both — main-flow's candidate-worktree payload difference disappears.
- A project with no staging environment gets `feature`, `hotfix`, `save`, `gate` and the hotfix
  `ship`; `promote` and `unpromote` refuse by name.
- Requires git ≥ 2.20 (worktrees, `--force-with-lease`); no `merge-tree`, no Python beyond the
  existing `scripts/site`.
- Version 0.7.0 — nothing of main-flow was released.

## What is ported from `feature/devops-main-flow`, and what is dropped

**Ported** (already built, tested, reviewed): features from production and the removal of
`BR_INTEG` and the old verbs · the scaffold and templates without a development branch · the
`_CLI_VARS` command-line allowlist (a real shell-injection fix, Makefile-only) · the fail-closed
`_deploy-tag` and `rollback` moving the tag · `ship`'s pre-flight and unconditional confirmation ·
the texts, rewritten for seven verbs.
**Dropped:** `dist/scripts/flow` · `refs/netdust/promoted|finished|gated` · the `release` branch ·
`finish`, `unfinish`, `candidate` · tree evidence and SHIP-1's two-part check · the guard's
GUARD-1/GUARD-2 floors and everything review gates B and D added to them · ~2 500 test lines.

## Task sketch (for `planning` to turn into tasks.md if this is approved)

1. Features and hotfixes from production; remove the integration rung and old verbs; help and
   flow-state for seven verbs. *(port)*
2. `promote` / `unpromote`: the rebuild recipe, the pinned list read from staging, lease, conflict.
3. `ship` (feature and hotfix paths) with the inline gate, and the post-ship rebuild.
4. Unmigrated-project refusal; scaffold and templates. *(port, simplified)*
5. Guard verb list and hints; the four texts.
6. `flow-test.sh` within its budget; versions; two eval cases.

## Out of scope

Migrating vad-vormingen and todai-client · CI · per-branch previews · anything that protects the
flow from an adversarial agent.
