---
name: harnessed-development
description: The single entry point for any code-changing work in a Netdust project — an intake ROUTER that classifies the work (Class A–F) and routes it to the two harness spines, `planning` (brainstorm → spec → plan + gates → analyze, stops at an approved gate-checked tasks.md) and `building` (execute → test → review → shake-out → finish, refuses to start without that artifact). It scales the ceremony to the work via the class dial — a big feature runs both spines with a human approval at the seam (Class A); a small self-contained change goes STRAIGHT to one TDD cycle in `building` — red/green only, no plan (Class E); a review-finding bundle is one TDD cycle per behavior finding (Class C); a security-boundary one-liner adds just the diff threat-model gate before building (Class D); a vision-stage brief that will change no code this session goes to brainstorm-only, notes at most, no plan/tasks artifact (Class F). Triggers on "build a feature", "start a feature", "implement X", "work the plan", "execute the plan", "execute todo.md", "start building", "do this properly", "the whole harness", "ship X", "fix the code-review findings", "address the review feedback" — AND on smaller asks that still change code — "tweak X", "fix this bug", "small change to X", "refactor this function", "add a helper for X", "just change X". Use it for the tweak too — it will route the tweak to the light path (Class E), not drag it through a plan. The intake class table is the first thing it does; that is the dial. NOT for read-only questions, pure formatting/whitespace, dependency bumps, prose, or research — those change no behavior and need no harness. Stack-agnostic; the spines defer to the loaded stack sub-plugin. Replaces the deleted `ntdst-execute-with-tests` skill (its "execute the plan" / "work the plan" triggers resolve here, routed to `building`).
---

<objective>
Make one truth hold: **if this skill was invoked, every gate the work's class warrants fired — and none was left to "remember to do it."**

This skill no longer sequences the stages itself. It does exactly one job — classify the work and route it to the right spine — because the gate-coverage durability it used to buy by sequencing everything in one file is now enforced **structurally at the seam**: `planning` cannot end without an approved `tasks.md` + `bin/gate-check.py` GREEN, and `building` refuses to start Class A/B work without exactly that artifact. One skill remembering every gate has been replaced by a boundary that checks them mechanically.

```
planning   brainstorm → spec → plan(+gates 1a–1g, task-shaping) → analyze
           OUTPUT: tasks.md + gate-check GREEN → STOP. Human approves.
           ═══════════════════ the seam ═══════════════════
building   PRECONDITION: that approved, gate-checked artifact
           execute → test → standards → review clusters → shake-out → finish
```

Do NOT do stage work here — no brainstorming, no plan gates, no dispatching, no pre-flight greps. Classify, route, done. The spines own everything else.
</objective>

<intake>
Before any other action, classify the work in one sentence in your transcript. The class determines the route.

| Work class | Route |
|---|---|
| **A — New feature / multi-task change** (most common) | `planning` (full spine: Stage 0 → 1.5) → **STOP at the seam; human approves** → `building` (Stage 2 → 3) |
| **B — Executing an existing written plan** | `planning` in **freshness-review mode** (run the gates against the plan, confirm task shaping, reconcile against current source) → seam → `building` |
| **C — Bug-fix bundle from /code-review or /security-review** | `building` directly — one TDD cycle per behavior finding (non-behavioral fixes close on the existing suite green, no new RED test); if any finding touches a security boundary, the 1a diff threat model first |
| **D — Ad-hoc edit to a named security-boundary file** (auth/session/token, URL-allow-list, crypto) — even a one-liner, even with no plan | The thin plan gate — `threat-modeling` on the *diff* (`planning` 1a) — then `building` for the TDD cycle + verify. This closes the 2026-06-03 gap (calibration: `class-d-gap`). |
| **E — Small self-contained change, no plan warranted** (a logic tweak, a small helper, a localized refactor, a single bug not from a review) — touches **one area**, no design questions, NOT a security-boundary file (that's D) | `building` directly — one TDD cycle, no plan, no spec, no shake-out. The per-task testing gate still applies there. |
| **F — Shaping / vision-stage exploration** (no code will change this session) | `superpowers:brainstorming` + `refining-ideas` **only**. Output is at most a scope sketch / notes doc (`docs/notes/…` or the conversation itself). Explicitly **NO** spec/plan/tasks artifact, **NO** gate ceremony, **NO** feature dir. Promotion path: when it becomes real work, re-enter intake as **Class A** — the notes feed Stage 0, they are not a shortcut around it. |

State your class and one-sentence reason before routing. If you cannot classify, the request is ambiguous — ask your human partner. Do not improvise.

**State the stakes too — it is a second, independent dial.** Alongside the class, declare: `Stakes: high | standard | low — <one-sentence reason>`. The two dials answer different questions and they do not track each other: class asks **how big is this work**, stakes asks **what breaks if it's wrong**. A contact page is a genuine Class A (new feature, several tasks) at `low`/`standard` stakes; a one-line change to a token store is Class D at `high`.

| Stakes | A failure… |
|---|---|
| **high** | loses money, data, access or privacy, or cannot be undone — payment/billing, the product's own auth and tenancy rules, PII, destructive operations, live-data migrations |
| **standard** | breaks a working feature for real users, visibly and recoverably. **The default** |
| **low** | shows a broken or empty page, and is caught by looking at it |

The class dial routes the work; the stakes dial scales what VERIFYING it buys — `testing-workflow`'s tier obligations, `feature-acceptance`'s edge driving, `test-effectiveness`'s audit depth, and `verify-budget.py`'s ceiling all read it. On Class A/B this statement is provisional: `planning` gate 1i records the binding value in the plan, where `gate-check.py` checks it and every later gate reads it. On C/D/E there is no plan, so the statement you make here IS the value — carry it into `building`.

**Under-calling stakes is the dangerous direction, exactly as with class** — and one rule makes it safe to relax the rest: **stakes never waives a guard.** It governs how much evidence *beyond a guard's proven presence* the work buys. A `low`-stakes feature still proves every guard is present and still tests any predicate encoding a rule this project chose. (Skipping the dial entirely is not neutral either: it was the state of the harness until 2026-07-31, and it is why a contact page bought an auth subsystem's verification — calibration: `contact-page-8k`.)

**The dial, in one line:** F = brainstorm only, notes at most · E = red/green only · C = TDD-cycle-per-finding · D = + diff threat model · B = + freshness review · A = both spines, seam in between. Match the class to the *actual* work — a tweak is Class E, not a small Class A; a vision brief is Class F, not a head start on a plan. Over-calling the class wastes ceremony; under-calling A/D (skipping a plan or a security gate that was warranted) is the dangerous direction. When the change is genuinely small and self-contained, **E is not cutting a corner — it is the correct class.** The one rule that never relaxes with class: anything touching a named security-boundary file is D (never E), and any non-trivial logic still gets its Tier-A RED test.
</intake>

<the_seam>
For Class A/B, the plan/build boundary is a **human review checkpoint, not a formality**: `planning` presents the approved artifacts and stops; `building` starts only on your human partner's go — and re-verifies `gate-check.py` itself at entry (the artifact admits the work, not anyone's assertion). Never bridge the seam autonomously "to keep momentum." The seam IS the harness's strongest gate.
</the_seam>

<red_flags>

| Thought | Reality |
|---|---|
| "It's just a one-line edit to the URL allow-list, no plan needed" | Correct that it needs no plan — but it is Class D, never E. The threat model runs on the diff before `building` touches it. |
| "This is small-ish, I'll run it as a lightweight Class A" | Wrong direction of laziness. A tweak is Class E — route it light. Ceremony is scaled by class, not by mood. |
| "The plan is approved in spirit, I'll start building while the human reads it" | The seam is a hard stop. `building` will re-run gate-check and demand the approval; don't pre-empt it. |
| "I'll just do the work here instead of routing — it's faster than loading another skill" | This file has no gates. Work done "here" is work done ungated — the exact failure the harness exists to prevent. Route. |
| "The user is describing a vision — I'll get a head start on the plan" | Don't manufacture a plan artifact for work that won't change code this session. A vision brief is Class F: brainstorm-only, notes at most. Ceremony for work that isn't executing yet is pure wait-time (calibration: `vision-brief-ceremony` — teacher-app, 2026-07-04: 30+ min of unwanted planning). |
| "It's a real feature with real tasks — Class A, so full verification" | Class A says how the work is PLANNED, not what verifying it is worth. A contact page and a billing engine are both Class A; they are not both `high` stakes. State the second dial (calibration: `contact-page-8k`). |
| "It touches a nonce and a sanitizer, so it's high stakes" | Those are framework primitives, present on every form in the stack. Calling a primitive is not making a decision — stakes is about what a FAILURE COSTS, not which functions appear in the diff. A contact form that leaks nothing and loses at most a lead is not an auth subsystem. |

</red_flags>

<integration>

| Skill | Relationship |
|---|---|
| `planning` | **PLAN spine.** Stage 0 (brainstorm) → 0.5 (spec) → 1 (plan + gates 1a/1b/1c/1e/1g + task-shaping 1d/1f/1h) → 1.5 (spec-analysis + gate-check). Stops at the seam. Classes A, B (freshness mode); Class D borrows its 1a gate for the diff. |
| `building` | **BUILD spine.** Precondition (the seam artifact) → Stage 2 (execute, per-task testing + standards gates, review-cluster HALTs, optional armed `/loop`) → Stage 3 (test-effectiveness, acceptance drive, shake-out, finish, compounding). Classes A, B after the seam; C, D, E directly. |
| `ntdst-execute-with-tests` (historical) | **DELETED (2026-06-05)** — absorbed into this skill when it was the single sequencer; its execution half now lives in `building`. Old trigger phrases still resolve here and route correctly. |
| *(historical note)* | Until 2026-07-04 this skill WAS the full sequencer — all stages, gates 1a–1h, Stage 2/3 inline (the "god skill"). Split per `docs/plan-build-split-handoff.md`: the stages moved verbatim-in-substance into the two spines; the class dial stayed here. Older handoff docs citing "harnessed-development Stage N" resolve via the table above: Stages 0–1.5 → `planning`, Stages 2–3 → `building`. |

</integration>
