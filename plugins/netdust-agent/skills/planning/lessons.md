# planning — Lessons

Plan-authoring incidents that became rules. The spine is `SKILL.md`; this file is the journal.

---

## A findings block goes AFTER the target cluster's review gate, never between its tasks and its gate

**Problem (daan, 2026-08-09):** Cluster A's review produced four confirmed findings, which correctly became new task lines in `tasks.md`. They were inserted by anchoring on the text `**Integration gate (Cluster B):**` — which put the whole block *between Cluster B's task list and Cluster B's own `Integration gate:` line and `── REVIEW GATE ──` marker*.

`gate-check.py` parses clusters as "tasks under a `### Cluster` heading until the next cluster heading". The new `### Cluster A review findings` heading therefore **terminated Cluster B early**, orphaning its gate and marker into the following section. Two checks failed — `review-gate-marker` and `integration-gate` — both naming **Cluster B**, a cluster nobody had touched.

**Rule:** insert a findings block immediately **after** the reviewed cluster's own `── REVIEW GATE ──` line, not before the next thing that mentions it. When appending any `### Cluster`-headed section, ask what it now separates: everything between a cluster's last task and its marker belongs to that cluster, and a heading dropped in there silently reassigns the marker.

**The real lesson is about the diagnosis, not the placement.** The failure named the wrong cluster — the checker reports where the *parse* broke, which is not where the *edit* happened. A finding against a cluster you did not touch is a signal that a heading moved, not that that cluster regressed. Re-run `gate-check.py` after **any** structural edit to `tasks.md`, not only after content edits; this was caught in one round precisely because it was re-run before committing.

---

## Ground-truth the framework's own extension points, not just the code you plan to call

**Problem (daan, 2026-08-09):** A plan's gate-1c ground-truth pass verified seven premises against real source and caught three that would have changed the plan's shape — including that an existing CPT already carried every field the feature was asked to add, and that a metabox config key the sibling service used was silently discarded by the framework. Good. But two defects still reached implementation, and both were the *same shape*: a framework surface that behaves differently than its declaration reads.

- A field declared `'required' => true` was enforced only on create.
- A derived field hooked to `ntdst/metabox_saved/*` covered only the admin write path, leaving every programmatic write (`create()`, `update()`, WP-CLI, REST) unpopulated.

Neither is visible from reading the *calling* code. Both are visible from reading the *framework's* implementation of the thing being relied on.

**Rule:** 1c's "read X's source and confirm X accepts Y" extends to the framework's **extension points and declarative keys**, not only to the classes and methods the plan calls. When a plan leans on a declaration (`required`, `validate`, a scope, a capability map) or a hook seam (`*_saved`, `*_after`), read what actually reads that key or fires that hook, and **enumerate every write path that must reach it**. A hook that covers one of three write paths is a premise, and it was wrong here.

**Cheap test for the second half:** for any derived or maintained value, name every path that writes the thing it is derived from. If the maintenance hook does not cover all of them, the value is not maintained — it is maintained *sometimes*, which for a query predicate means rows silently vanishing from both sides of the filter.

---

## An integration-gate curl that reads only the status code passes a mid-render fatal

**Problem (ntdst-core 5.0.0, 2026-08-23):** core-shape Cluster 4a's gate line was
`curl -s -o /dev/null -w '%{http_code}' https://daan.ddev.site/` and it printed **200
on a broken homepage** — the consumer's theme helper called a method the branch had
deleted, the fatal hit mid-render, and WordPress had already flushed the 200 header.
The gate reported PASS over a page whose body was a stack trace. The task review
caught it only because a reviewer ran the gate's own command and then read the body.

**Rule:** an `Observable:` or `Integration gate:` line that drives a page must assert
the BODY, not the status alone — at minimum
`[ "$(curl -sS <url> | grep -c 'Stack trace\|Fatal error')" = 0 ]` beside the status
check. A status-only curl proves the server started answering, not that the page
rendered. The same applies to any gate whose success channel can be committed before
the failure happens (headers before render, exit codes of pipelines, queue acks).

---

## An older tasks.md in the project is not the grammar

**Problem (ntdst-baseline polylang, 2026-09-03):** the plan was written with
`planning` 0.21.1 loaded — the text that says `Lane: behaviour` is the default — and
still came out all-contract with no `Lane:` line on any cluster. The model copied the
shape of `specs/edushare-verhaal-template/tasks.md`, a plan from before the lane
existed. `gate-check` passed it silently (the AC-2 backward-compatibility silence),
so nothing pushed back until Stefan asked whether the new skills were being used.
A second pass re-laned two of five clusters as behaviour and dropped two review panels.

**Rule:** the grammar is `bin/gate-check.py` plus this skill's text, never a
neighbouring plan. A project's earlier `tasks.md` is a snapshot of the harness version
that wrote it. Before copying any shape from it, check the plan's own date against the
convention's (the lane: 2026-09-02). Since this lesson, a lane-less `tasks.md` WARNs
unless it carries the legacy-artifact marker, so the silence no longer hides the miss —
but a WARN is read only by someone who reads the findings, so read them.

**Cheap test:** for each cluster ask the skill's question out loud in the plan — "does
a task here encode a rule THIS project chose, or is it configuration over a framework
that already has the rule?" — and write the answer after the dash of the `Lane:` line.
A cluster whose reason you cannot finish in one sentence is behaviour.


## Enumerate the external unknowns in ONE pass, and inspect before asking

A first-time environment bring-up (josworld → Combell, 2026-09-05) cost four
sequential blocking questions — SSH host key, database host, GitHub auth for a
private composer package, licensed plugin zips — each raised only when the
previous step hit it. Every one was foreseeable at intake.
Rule: for any task touching an environment this session has not used before,
list every credential, permission and asset it will need BEFORE the first
remote command, and ask for all of them together.
Second rule, from the fourth question: **inspect before asking the human for a
file.** "Gitignored and outside `deploy.payload`" means it will never deploy —
it does NOT mean it is missing locally. The licensed theme and plugin were
sitting in the project's own working tree at exactly the right versions; one
`ls` would have saved a round trip. Eval: `evals/bringup-2026-09-05-cases.json`.


## Two grammar tokens the checker reads out of prose (2026-09-06)

**Problem (artifact-gate plan):** a task body that mentioned `[HUMAN] accepted:` as a
manifest form made the checker treat five tasks as yield points (`HAS_HUMAN` matches the
token anywhere in the task text) — loop-check would have BLOCKED on them. A separate task
wrote "clusters whose `(files:)` match …" inside its prose and the files-segment parser
took that empty `(files:)` as the task's segment, reporting no files.
**Rule:** inside a `- [ ] Tnn` body, never write the literal `[HUMAN]` or `(files:` except
as the real marker/segment. Name a manifest ruling `Ruling:`; describe a files segment in
words ("the files segments"). Eval: `evals/artifact-gate-2026-09-06-cases.json`
(`planning-tokens`).

## A plan that changes a shared entry point must enumerate its CONSUMERS (2026-09-08)

`FilterTreeParams`' own class docblock named exactly two readers — the grid handler
AND `BulkRunner`. The CR-2 dispatch said "fix the reopen path"; the implementer fixed
the one path named, and the FULL branch review found the Critical: an admin opened a
saved list naming a deleted term, saw its 15 surviving rows, then every one of 15 bulk
routes plus the mail preview returned 400. The rail promised, the grid delivered, the
bulk bar refused — a three-way split where the fix reached two.

The answer was in the file before the work started. A shared entry point has readers,
not just callers, and a change to its contract is a change to every reader's contract.

**Check, at plan time:** for any task touching a shared param, entry point or wire
format, grep its own docblock AND the codebase for readers, then name each reader's
disposition on the task line — fixed, unaffected, or deferred with the reason. "The X
path" in a task description is a smell when X has more than one consumer.

Corollary, from the same fix: the implementer put the new door-picking rule in
`FilterTreeParams` rather than inlining it in `BulkRunner` as the brief specified,
because that class already claims to be the one home of the rule for both readers.
Inlining would have made a THIRD copy — the same drift that caused the Critical.
Eval: `evals/shared-entry-point-2026-09-08-cases.json` (`consumer-enumeration`).

## Never carry a mechanism claim forward from an existing comment (2026-09-08)

Two inherited claims were false in one branch, and both reached a spec, a plan, a
threat model and a new docblock before anything tested them:

1. *"The CAST to UNSIGNED preserves the `object_id` index"* — copied from
   `AdminAPIController::buildCourseTaxonomyJoin()`'s comment. MEASURED on MySQL 8.0.46:
   identical EXPLAIN either way (`tr` eq_ref PRIMARY), no warning, uncast marginally
   FASTER. The cast is fine to keep; the stated reason was wrong.
2. *"The discovered taxonomy is the ONLY options map that can shrink under a stored
   tree"* — written into the rationale for a security tolerance. False:
   `AuditFieldCatalog` derives three `select` vocabularies from `SELECT DISTINCT` over
   the audit log, and a 7-year retention cron DELETES rows.

A wrong justification is worse than none. A reader who tests it finds it false and may
delete the guarded code as cargo-cult — which is precisely how claim 1 propagated in
the first place.

**Check:** the `## Spec-premise ground-truth` table records the MEASUREMENT, never the
source comment. "`buildCourseTaxonomyJoin` says Y" is not evidence for Y. If a claim
cannot be measured in the same sitting, write it as an open question and say what would
settle it. A control run with the thing removed is what turns an assertion into
evidence.
Eval: `evals/shared-entry-point-2026-09-08-cases.json` (`unmeasured-premise`).
