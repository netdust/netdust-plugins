# building — Lessons

Execution incidents that became rules. The spine itself is `SKILL.md`; this file is the journal of what running it actually taught.

---

## Parallel dispatch needs isolation the FILE list cannot give you

**Problem (daan, 2026-08-09):** Two implementers were dispatched concurrently on the same feature branch, deliberately scoped to different files — `api/Data.php` for one, `admin/MetaboxGenerator.php` for the other. No file conflict was possible. Both then ran the project's full integration suite to check their work against a documented 7-failure baseline, and got **14 and 17 failures** with zero code changes between runs. Each agent spent real diagnostic effort — one reverted its own implementation to HEAD, re-ran, and isolated the flap before concluding it was not theirs — to rule out a regression that never existed.

The cause is not the files. This stack's integration suite loads the **real** WordPress instance and mutates the live database (`tests/Integration/bootstrap.php` → `web/wp/wp-load.php`), so two suite runs interleaving in one worktree corrupt each other's fixtures. Amplified by PHPUnit's `executionOrder="depends,defects"`, which reorders around prior failures and makes the noise non-reproducible.

**Rule:** file-level independence is **not** sufficient grounds for parallel dispatch. Before parallelising, ask what *shared mutable state* the agents will both touch — the test database, a dev server, a cache, a fixtures directory, a browser profile. If any is shared, either serialise the dispatches, or give each agent `isolation: "worktree"`.

**Corollary for the controller:** an "exactly N failures" acceptance criterion is **unmeasurable during a concurrent window**. Never verify a baseline while another agent is running; the number is noise. Both agents in this incident reported the hazard rather than hand-waving it, which is the behaviour to reinforce — but the dispatch was the controller's error, not theirs.

---

## verify-budget reads worst at a scaffold cluster — report it, do not relabel the stakes

**Problem (daan, 2026-08-09):** `verify-budget.py` HALTed a `low`-stakes cluster at **1.44×** (517 test lines / 358 implementation lines, ceiling 1.0×). The cluster was a CPT registration, a field-declaration array, one derived value and a tab layout — i.e. the *scaffold* cluster of a feature, where implementation is structurally at its thinnest and there is nothing yet for tests to be proportional to.

This is the same family as the already-known "HALTs on fix-shaped clusters" mis-fit (where implementation is 2 lines by nature). The ceiling is calibrated for feature work with real logic in it.

**Rule:** when the tripwire fires on a scaffold- or fix-shaped cluster, that is a **measurement-timing** artifact, not a verification problem — and it is still a genuine STOP-and-report. Put the number in front of the human with the three named causes, say which you believe applies, and let them choose. The correct outcomes are *proceed and re-measure at the first cluster with real logic*, or *raise the stakes line in a plan-correction commit*.

**The two wrong resolutions**, in order of how tempting they are:
1. **Deleting tests to clear the ratio.** The script says this explicitly and it is still the first instinct. Never.
2. **Relabelling the stakes to lift the ceiling.** Quieter and therefore worse — it silently re-decides the dial the whole harness reads downstream. Raising stakes is legitimate *only* when the work really is riskier than the plan said, and it happens in the open as a plan-correction commit.

**Also worth stating plainly:** a simplicity reviewer dispatched at that gate found ~6% trimmable (moving 1.44× → ~1.41×) and led with *"this does not rescue the budget and must not be done for that reason."* That is the right framing. Trimming is a readability decision; it is not a budget remedy.

---

## superpowers' task-brief script cannot parse netdust plan grammar — extract by hand

**Problem (ntdst-core 5.0.0, 2026-08-23):** `scripts/task-brief PLAN_FILE N` expects
`### Task N` headings; netdust `tasks.md` uses `- [ ] Tnn — …` task lines under
`### Cluster` headings. The script answered "task 9 not found" on a valid plan, and the
controller had to extract the task block by hand (slice from the `- [ ] Tnn` line to
the next task line / `Integration gate:` / `── REVIEW GATE ──` / heading).

**Rule:** on a netdust-grammar plan, build the brief by slicing `tasks.md` between the
task's own line and the next structural marker, write it to the plan's workspace as
`task-N-brief.md`, and append a controller ground-truth section (live line numbers,
signatures) before dispatching. Do not "fix" the plan's grammar to satisfy the script —
`gate-check.py` owns the grammar. The same applies to `review-package`'s BASE: record
BASE before dispatching; `HEAD~1` silently truncates multi-commit tasks.

## "The compiled artifact has the right values" is not "the page looks right"

**Problem (edushare, 2026-08-27):** A Cluster A close declared the plan's
`## First working version` reached, on this evidence: `lessc` exits 0, the
Customizer recompile changed the stylesheet's md5, and all six brand hex values
are present in the compiled CSS. Every one of those was true. The human opened
the page and found grey titles where the design has green and purple, and square
buttons where the design has pills. The audit that followed found **five**
divergences, two of them introduced by the very task that declared success.

The gate's `Artifact-load:` rule was satisfied — the page WAS loaded, and what
was seen was recorded. That is what makes this worth writing down. **Loading is
not comparing.** The artifact was read for confirmation of what had just been
mapped, not checked against the design element by element, so everything the
task never thought about stayed invisible. A screenshot glanced at proves the
page renders; it does not prove the page is right.

**Rule:** on a user-facing cluster, the integration gate closes on a
**comparison against the source of truth**, not an observation of the artifact.
Name the source (the design file, the spec's acceptance rows, the reference
implementation), enumerate the properties it constrains, and check each one.
Anything the source constrains that the diff never mentioned is exactly where
the misses live.

**What the check has to be made of:** computed values read from the running
artifact, asserted against the source's own numbers, committed as a test. Not
the compiled output, and not a look. Three separate mechanisms let a correct-
looking build render wrong here — a different variable won, a guard mixin
skipped the rule because the value was still `0`, and the file on disk was
stale — and grepping the build artifact is blind to all three. In a browser they
are one assertion each.

**Corollary — the deferral that eats the gate.** Two of the five failures were
component values a task DELETED while rewriting a section wholesale, on the
reasoning that a later cluster owned them. Deferring a value to a later task is
fine. Deferring it *and* declaring a working version in the same breath is not:
the human sees the whole page, not the task boundary. If a cluster's deliverable
is "a human can look at this", nothing visible in that frame is out of scope —
either fix it or say plainly, at the gate, what will still look wrong and why.

---

## The stack skills ride in every dispatch, and the panel matches the base (2026-09-03)

**Problem (ntdst-baseline polylang, Clusters A–B):** six tasks on a package that sits on
ntdst-core were dispatched without `netdust-wp:ntdst-framework` or `wp-testing`, and
reviewed by panels of reviewer + code-simplicity only. Every task built plain WordPress —
`new` instead of the container, silence instead of `ntdst_log()`, prose comments copied
from a bloated sibling — and every review approved it, because nobody on the panel owned
the framework. Stefan caught it reading the diff.

**Rule:** on a WordPress project (or any package that consumes ntdst-core) the controller
loads `netdust-wp:ntdst-framework` before the first dispatch and names it, plus
`wp-testing`, in every implementer prompt; the plan's `## Architecture invariants touched`
cites ntdst-core's `ARCHITECTURE-INVARIANTS.md` even when the repo has none of its own
(detection half re-ruled below, 2026-09-06). This is what
`netdust-wp/CLAUDE.md` already says; the failure was the controller not doing it.

**Re-ruled 2026-09-06** (`specs/artifact-gate/spec.md`, FR-9–FR-11): the prevention half
stands verbatim — the framework skills ride in every dispatch, and `## Architecture
invariants touched` cites core's doc. The detection half moves: drift review runs at the
branch review and on the clusters the gate's `panel-hints` line names (files under
`Services/`, `Handlers/`, `Repositories/`, `Modules/`), not on every panel. The week of
2–5 Sept ran 15 panels and found one Critical — outside a panel; the reviewers that found
defects were `invariant-auditor` and `security-sentinel`. So the cluster panel at FULL is
those two, and STANDARD and LIGHT dispatch none.

---

## `cluster-open` is a promise the machine layer does not keep yet (2026-09-03)

**Problem:** SKILL.md's behaviour lane says "write `cluster-open` to the loop ledger
naming it (the hook's tolerance reads that event)". Grep the 0.21.x cache:
`hooks/subagent-stop.py` and `bin/` contain no such tolerance — the string exists only in
the skill text. An implementer closing the first task of a behaviour cluster reports the
cluster RED as a red suite and the stop hook blocks the close.

**Until it is implemented:** dispatch a behaviour cluster's tasks as ONE implementer
dispatch with one commit per task, so the cluster RED is written first, watched failing,
and goes green inside the same dispatch; the evidence line is then honestly `exit=0`.
Never name a partial suite in `suite=` to dodge the hook. **To implement:** the stop hook
reads a `cluster-open <test path>` line from the plan workspace ledger and tolerates
exactly that file's failures for role=implementer until a `cluster-close` line follows.



## Seat the sentinel in the first panel when a cluster touches a floor (2026-09-06)

**Problem (artifact-gate Cluster A):** the credential floor shipped in T01, the STANDARD
panel (generalist + simplicity) ran first, escalation to FULL came after round one, and
the security-sentinel's four Importants cost a second round and a ruled third. The
sentinel is the reviewer that found the load-bearing gaps; it arrived last.
**Rule:** when any task in a cluster edits a guard, allowlist, credential scan or auth
recipe, the cluster's FIRST panel is FULL — `security-sentinel` sits in round one, not
after an escalation. Eval: `evals/artifact-gate-2026-09-06-cases.json` (`sentinel-first`).

## Two implementers on disjoint files in one tree is fine; shared suites are the hazard (2026-09-06)

**Observed (artifact-gate, four times):** an implementer ran beside a read-only review, and
twice beside another implementer, always on disjoint files, with file-local python/bash
suites — no phantom failures, commits interleaved cleanly by path. The 2026-08-09 failure
(14 and 17 phantom failures) was two implementers sharing an integration DATABASE.
**Rule:** the "never parallel" rule is about a shared suite or database, not about files.
Overlap is allowed when (a) the file sets are disjoint by the plan's `(files:)`, (b) each
suite is file-local (no DDEV/wp-phpunit DB), and (c) every commit is `git add` by path.
Ledger the overlap as a ruling. Eval: `evals/artifact-gate-2026-09-06-cases.json`
(`disjoint-overlap`).

## Reviewers without Write cannot file their reports — the controller files them (2026-09-06)

**Problem:** `reviewer` and `netdust-wp:ntdst-drift-reviewer` have no Write tool; two of
them returned full reports in the reply and the controller had to save them under
`.superpowers/sdd/<feature>/`. A report that lives only in a subagent's return is lost at
compaction.
**Rule (controller-side):** when a review dispatch's return carries the report, write it to
the workspace file the dispatch named before the next step; never leave a verdict only in
context. The agent body is unchanged (a Write tool on a reviewer is a `/skill-audit`
proposal, not a lesson).

## On a shared branch, `git add <path>` + `git commit` is not safe (2026-09-08)

A hook (the memory Stop hook, and any other that stages) can fire BETWEEN the two
commands. Hit twice in one session on `feature/course-taxonomy-filter`:

- one agent's `git add` + `git commit` pair silently lost its staged index and
  committed nothing of its own;
- another's commit swept up a concurrent agent's two files and omitted its own —
  despite having `git add`-ed only its own path.

Staging by explicit path is necessary but NOT sufficient; the window between the two
commands is the hazard.

**The durable form** (found by an implementer mid-run, now standard in every dispatch
brief on a shared branch):

    git add -N <path>                      # intent-to-add, so a new file is known
    git commit --only <path> -m "..."

`--only` pins commit contents to the pathspec regardless of what a hook staged in the
meantime. Recovery from a bad sweep is `git reset --soft HEAD~1` + `git restore
--staged`, which touches no file content.

Applies whenever 2+ dispatches share a working tree — i.e. any cluster without a
`**Placement:** worktree` line.
