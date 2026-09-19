# Simple flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `netdust-agent:building`, which drives
> `superpowers:subagent-driven-development` task by task. The task list, contracts and gates live
> in `specs/devops-simple-flow/tasks.md`; this file carries the reasoning. Read both.

**Goal:** Features and hotfixes from main, staging as a disposable branch rebuilt from main plus
the promoted features, and a ship that fast-forwards production to the exact staging commit that
was deployed and gated — all inside `Makefile.netdust`.

**Architecture:** One canned recipe rebuilds staging in a throwaway worktree from a list it reads
off staging's own `promote: <name>` merge commits, and pushes it with a lease. `ship` checks three
commit equalities, runs the project's gate inline, asks, backs up, fast-forwards, deploys through
the existing chain, and rebuilds staging. No engine script, no custom refs, no `release` branch.

**Tech Stack:** GNU make + bash · git ≥ 2.20 · the existing `scripts/site` reader · the existing
bash harnesses (`flow-test.sh`, `tests/run.sh`) and the agent's Python guard tests.

**Spec:** `specs/devops-simple-flow/spec.md` — 16 FRs, 8 SCs.

**Loop budget:** ~20 iterations

## Global Constraints

- Branches: production = `environments.production.branch` (`BR_PROD`); staging =
  `environments.staging.branch` (`BR_REVIEW`). There is no third branch.
- Flow verbs: `feature · hotfix · save · promote · unpromote · gate · ship`. Nothing is aliased.
- A promote merge is `git merge --no-ff -m "promote: <name>" <sha>`; the list on staging is
  `git log --merges --first-parent --format='%s %P' origin/<prod>..origin/<staging>`, keeping lines
  whose subject is `promote: <name>`; the pinned commit is the merge's SECOND parent.
- A rebuild ends in ONE `git push --force-with-lease=<staging>:<old tip> origin <new>:refs/heads/<staging>`.
- Budgets (spec SC-4…SC-6): `Makefile.netdust` ≤ +100 lines over `main` (799); guard ≤ +20 over 616;
  `flow-test.sh` ≤ 500 lines and ≤ 2 minutes; 0 new files under `dist/scripts/`; 0 `refs/netdust/*`.
- `_need-tty` is the FIRST thing every writing verb does. `ship` ALWAYS asks for the typed `yes`.
- Tests contact no server: the server leaves (`_deploy-transport`, `_deploy-ledger`,
  `_deploy-opcache`, `_backup-data`, `_backup-payload`) are overridden in the test project's own
  `Makefile`; terminal-guarded verbs are driven through `script -qec` and the suite exits 2 — never
  skips — when `script(1)` is missing.
- Never the literal strings `make release` or `BR_INTEG` under `dist/`, `bin/` or `templates/`.
- Versions: `netdust-devops` 0.7.0 · `netdust-agent` 0.28.0 · `netdust-core` 0.5.2 · `netdust-wp` 1.2.1.
- A port is a PORT: copy the named hunk from `feature/devops-main-flow` with
  `git show feature/devops-main-flow:<path>`, keep what this spec needs, delete the rest. That
  branch is reference only — never merge or cherry-pick a whole commit from it.

## Technical context

`plugins/netdust-devops/dist/` is the vendored core. On `main` (`887a53d`): `Makefile.netdust` 799
lines, `flow-test.sh` 133 lines with no pty harness, the guard 616 lines, `dist/VERSION` 0.6.3.
`feature/devops-main-flow` (unmerged, `d615e75`) holds reviewed implementations of several things
this plan ports; its ledger (`.superpowers/sdd/tasks/progress.md` in that worktree) records why
each exists.

### The rebuild, as one canned recipe

`promote`, `unpromote` and `ship`'s last step all call it with two shell variables, `ADD` and
`DROP` (either may be empty). A `define … endef` block — not a sub-make with arguments, because
the ported command-line allowlist refuses undeclared variables at parse time:

1. `OLD` = `origin/<staging>`; read the list (`name sha` lines) as in Global Constraints.
2. Drop the line named `DROP`; drop the line named `ADD`; append `ADD <origin/feature/ADD tip>`;
   drop every line whose sha is already an ancestor of `origin/<prod>` (shipped — FR-8).
3. `git worktree add --detach <tmp> origin/<prod>` with a trap that removes it; merge each line in
   name order with `--no-ff -m "promote: <name>"`; a failed merge prints `✗ conflict: <name>` and
   exits 3 with nothing pushed.
4. FR-16: count `git rev-list --no-merges <OLD> --not <NEW> origin/<prod> <sha of DROP, if any>`;
   when it is not 0 print ONE line containing `dropped`, the count, and `<OLD>`'s short sha.
5. The one leased push. A rejected lease prints `origin changed — run it again` and exits 5.

If this does not fit one screen, stop and report (spec FR-12).

### Ship, in order

`_need-tty` → `HAS_PROD` → refuse `dryrun=` by name → `_ensure-clean-git verb=ship` →
`_worktree-guard rung=<prod> verb=ship` → `git fetch` → path: on `hotfix/*` the hotfix path, on
`<staging>` the feature path, anywhere else refuse naming both → the path's commit checks →
`$(MAKE) gate` (red = refuse) → typed `yes` → `_backup-data` → `_backup-payload` →
`git push origin HEAD:refs/heads/<prod>` (non-force) → checkout `<prod>`, `merge --ff-only` →
`_deploy-gate env=production` → transport → ledger → tag → opcache → the rebuild (`ADD=` `DROP=`).

Feature-path checks: `HEAD` = `origin/<staging>`; the exact `refs/tags/deployed/staging` on origin
names `HEAD`; `origin/<prod>` is an ancestor of `HEAD`. Hotfix-path check: `origin/<prod>` is an
ancestor of `HEAD`.

## Stakes

**Stakes: high** — these verbs decide what reaches production on every site that vendors the core.
A wrong rebuild puts unselected work on staging; a wrong ship puts an unseen commit on production.

### Per-cluster stakes

| Cluster | Stakes | Why |
|---|---|---|
| A — the flow: from main, rebuild, ship | **high** | the rebuild and the production gate |
| B — the core around it | **high** | a shell-injection fix and the unmigrated-project refusal |
| C — guard words, texts, the record | **standard** | wrong words are visible and reverted in one commit |

## First working version

**Task:** T02
**Demonstrates:** in a throwaway project on a bare origin, `make promote name=x` then
`make promote name=y` leaves `origin/staging` with the tree of a hand-merged main+x+y, and
`make unpromote name=x` leaves main+y — with nothing stored anywhere but the staging branch.
**Verify by:** `bash plugins/netdust-devops/dist/scripts/tests/flow-test.sh` → the
`flow — promote` section reports its assertions as `ok`.

## Constitution check

Simplicity is the requirement, so it is budgeted rather than hoped for: line ceilings on the
Makefile, the guard and the test (spec SC-4…SC-6), and a stop rule on the rebuild recipe (FR-12).
No new state store — the staging branch is the state. No new script. The deploy chain is reused
as it stands; only `_deploy-stamp` is split, because the tag half becomes load-bearing for `ship`.
What `feature/devops-main-flow` already built and reviewed is ported by hunk, not rebuilt; what
that branch needed only because evidence lived in forgeable refs is not ported at all.

**Review is budgeted too** (the lesson of the main-flow build, where review never converged): cluster
gates are STANDARD/LIGHT with no reviewer panel; ONE branch review at the end; ONE fix round on its
Criticals and in-boundary Importants; fixes verified by their named checks and the suites only —
no reviewer is re-dispatched to re-verify, and no second round runs without Stefan's word.
Everything else becomes a one-line follow-up.

## Threat model [GATE]

**Trust boundary.** The operator is trusted. Agent sessions are trusted not to be adversarial but
route around a verb that fails; the guard is a courtesy floor for that, not a sandbox. **For an
agent the rule is *don't*, not *can't*** — `script(1)` hands out a real pty, and nothing here
claims otherwise.

**Assets.** The production branch and the site behind it · the staging branch · the
`deployed/<env>` tags · both backups.

1. **Shipping a commit staging never ran** → `ship` requires `HEAD` = `origin/<staging>` = the
   commit origin's `deployed/staging` names, read by exact refname (T03); `_deploy-tag` fails the
   deploy when the tag cannot be pushed, so the tag never lags silently (T04).
2. **Shipping from a stale or dirty checkout** → clean-tree and free-production-branch pre-flight
   BEFORE the gate, the confirmation and the push (T03).
3. **A red suite shipping** → `ship` runs `commands.gate` itself and refuses on non-zero; nothing is
   recorded, so nothing can be forged (T03). Residual: `commands.gate` edited to `true` rides in the
   tree the operator is about to ship and is visible in the change list he confirms.
4. **A forged confirmation** → `_need-tty` first in every writing verb; the guard denies a piped or
   pty-wrapped confirming verb typed on the command line (T06). Residual, stated: a script file
   defeats it; the rule is *don't*.
5. **Shell injection through a make variable** (`make rollback env='a"; touch X; echo "'` executes on
   `main` today) → the command-line allowlist, ported as built (T04).
6. **Two sessions rebuilding staging at once** → one leased push; the loser exits non-zero (T02).
7. **A rebuild silently dropping work** — a migrated project's accumulated staging history, or a
   commit someone put on staging by hand → the one-line report with the old tip (T02, FR-16).
8. **Production advanced but not deployed** — a transport failure after the push → `ship` exits
   non-zero saying the branch is ahead of the site; `make deployed` shows it and
   `make deploy env=production` from the production checkout recovers (T03). Residual, stated.
   Every other failure — dirty tree, held branch, red gate, declined prompt, failed backup —
   happens BEFORE the push.
9. **An agent forging `deployed/staging` or pushing a rung by a spelling the guard misses** → out
   of scope by decision (spec *Assumptions*): no evidence floor is built. Stated, not mitigated.

## Acceptance flows [GATE]

Every row runs in `flow-test.sh` (AF-8 in the guard's test module) against a bare origin with the
server leaves overridden.

| # | Flow | Layer | Expected | Edges |
|---|---|---|---|---|
| AF-1 | Three features on staging, two shipped | cli | staging tree = main+A+B+C; after `unpromote C`, deploy, ship: production tree = main+A+B with 0 commits of C; after `promote C`: staging = new-main+C | unknown name refused · no terminal refused · empty staging = main |
| AF-2 | A promoted feature stays pinned | cli | after a new commit on `feature/A`, `promote B` leaves A at the commit first promoted | `promote A` again moves it to the new tip |
| AF-3 | A rebuild that cannot finish changes nothing | cli | conflict → exit 3 naming the feature, `ls-remote` byte-identical | lost lease → non-zero, `run it again`, byte-identical; re-run keeps both |
| AF-4 | Ship refuses before anything moves | cli | each refusal names its reason; `ls-remote` byte-identical; 0 leaves ran | staging not deployed since the rebuild · red gate · dirty tree · production held by another worktree · `no` typed · no terminal · `dryrun=1` · run from a feature branch |
| AF-5 | Hotfix ship | cli | production = main+H with 0 staging deploys; staging = main+H + what was on it | red gate refused · production moved since the hotfix branched refused |
| AF-6 | The rebuild reports what it drops | cli | one `dropped` line with the count and the old tip when old staging holds a commit nothing explains | everyday promote silent · unpromote silent · a 3-commit feature unpromoted silent |
| AF-7 | An unmigrated or half-updated project | cli | the five selection/ship verbs and `feature`/`hotfix` refuse naming the migration and the restore command; `status`, `gate`, `deploy-test`, `save` run | scaffolded project: no `development` branch, no refusal |
| AF-8 | The guard speaks the seven verbs | cli | a raw commit/merge/push on `main` or `staging` is denied naming a verb that exists; a piped confirmation into `ship`/`promote`/`unpromote`/`deploy` is denied | `make promote name=x` not inspected · `deploy-test` piped allowed |

## Architecture invariants touched [GATE]

No `ARCHITECTURE-INVARIANTS.md` in this repo. Two standing invariants are touched and kept:
**vendored, edited upstream only** (nothing new joins `MANAGED`; the core stays one Makefile plus
the existing scripts) and **the verbs are the only door to a rung** (the guard's existing floor,
unchanged in mechanism). This spec deliberately adds NO new invariant that needs enforcing.

## Spec-premise ground-truth [GATE]

Read against `main` (`887a53d`) on 2026-09-19:

1. **Features branch from the integration branch; promote is a plain merge.**
   `Makefile.netdust:104-112`, `:183-207` (`git merge --no-ff "$$BR"` into `$(BR_REVIEW)`). ✓
2. **`BR_INTEG`, `finish` (`:127-181`) and the release verb (`:210-227`) exist on main** — ~95 lines
   that T01 deletes, which is what pays for the additions inside SC-5's budget. ✓
3. **`ship` today** (`:244-259`): `_need-tty` → `_ship-branch` → `_deploy-gate` → backups → `deploy`
   (whose `_deploy-confirm` returns 0 without asking unless `environments.<env>.confirm` is `true`,
   `:565-575`). So today's ship can run with NO typed confirmation — T03 changes that. ✓
4. **`_deploy-stamp` swallows a failed tag push** (`:588-590`, `|| echo "(tag not pushed …)"`), and
   `ship` will read that tag → T04 splits it and makes the tag half fail closed. ✓
5. **No command-line allowlist on main** (no `_CLI_VARS`); `dryrun=--dry-run` is spliced into rsync
   (`:241`, `_deploy-transport`). The 49-line block at `feature/devops-main-flow:Makefile.netdust:18-66`
   and its `dryrun=1` boolean are ported by T04. ✓
6. **`flow-test.sh` on main has no pty helper** (133 lines, no `script -qec`) → T01 adds
   `Y() { script -qec "$*" /dev/null <<< yes; }` and `N()`; the guard already denies that wrapper
   on an agent's command line, so the harness is not a new bypass. ✓
7. **The guard on main**: `FLOW_CONFIRMING_VERBS = (?:ship|release|promote|deploy)` (`:321`), eleven
   `FLOW_VERB_FOR` values naming `make finish` as a merge (`:357-372`), `_flow_deny`'s closing
   sentence "feature → integration → review → production" (`:454`). T06 edits words only. ✓
8. **Scaffold and texts on main** still create and teach `development`: `bin/new-project:217,243,255`,
   `templates/site.yml.tmpl:48-60`, `templates/memory-STATE.md.tmpl:14`,
   `commands/new-project.md:30,54`, `netdust-wp/commands/wp-new-project.md:13`. ✓
9. **Test baseline on main** — run before T01 and record it: `plugins/netdust-devops/tests/run.sh`
   and `env -u NETDUST_GUARD_ASK bash plugins/netdust-agent/tests/run.sh` (one known failing module,
   `test_integration_contract`, a live-corpus baseline; the variable MUST be scrubbed — the shell
   exports `off` and the guard suite reads it).

## Deploy

N/A — `netdust-plugins` is a marketplace repo with no `site.yml` and no `deploy.payload`. Rolling
0.7 out to live projects is a separate, later step.

## Phases & review clusters [GATE]

One phase, three clusters, the asked-for thing first:

- **Cluster A — the flow** (T01–T03, high, STANDARD): features from main and the old verbs gone;
  the rebuild; ship.
- **Cluster B — the core around it** (T04–T05, high, STANDARD): the allowlist, the fail-closed tag
  and `dryrun=1`; the unmigrated refusal and the scaffold.
- **Cluster C — words and the record** (T06–T08, standard, LIGHT): guard verb list and hints; the
  texts; versions, evals and the budget check.

All three touch `Makefile.netdust` or `flow-test.sh` and run strictly in sequence; nothing is `[P]`.

Task list, contracts and gates: `specs/devops-simple-flow/tasks.md`.
