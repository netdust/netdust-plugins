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
