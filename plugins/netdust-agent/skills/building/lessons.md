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
