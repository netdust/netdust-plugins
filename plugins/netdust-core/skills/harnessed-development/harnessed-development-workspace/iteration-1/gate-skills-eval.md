# Harness gate skills — skill-eval (companion to harnessed-development iteration 1)

Skills evaluated (the six gates `harnessed-development` sequences):
threat-modeling, architecture-invariants, testing-workflow, test-effectiveness,
feature-acceptance, shake-out. Judges/runners: Sonnet 4.6 subagents. Date 2026-06-07.

Method: per skill, 20 trigger queries (10 should / 10 should-not, should-not slots
loaded with SIBLING-GATE near-misses since that's the real confusion zone) × 3 blind
judges, query order shuffled per judge. Plus baseline-vs-skill behavioral probes.

## Part A — Trigger eval (majority of 3 judges)

| skill | should-trigger | should-NOT suppressed | FP | FN | flaky |
|---|---|---|---|---|---|
| threat-modeling | 10/10 | 10/10 | 0 | 0 | 0 |
| architecture-invariants | 10/10 | 10/10 | 0 | 0 | 0 |
| testing-workflow | 10/10 | **9/10** | **1** | 0 | 1 |
| test-effectiveness | 10/10 | 10/10 | 0 | 0 | 0 |
| feature-acceptance | 10/10 | 10/10 | 0 | 0 | 0 |
| shake-out | **9/10** | 10/10 | 0 | **1** | 1 |

**Two real defects, both at the testing-workflow ↔ test-effectiveness ↔ shake-out boundary** (exactly where I aimed the near-misses):

1. **testing-workflow over-triggers on a suite-AUDIT query** (FP):
   *"Audit whether my existing green suite would actually bite if the guard regressed."*
   That's **test-effectiveness's** job (audit-time / per-phase). testing-workflow fired (maj.)
   because its description owns "verify a task… before sign-off" and the boundary against its
   audit-time sibling isn't drawn. A second audit-flavored query ("which failure mode let the
   bug through") drew a 1/3 over-fire (correctly majority-suppressed, but leaky).

2. **shake-out under-triggers on gate-language phrasing** (FN):
   *"We finished executing the plan — run the spec-complete gate before merge."*
   Only 1/3 fired. shake-out IS the spec-complete / pre-merge gate, but its description leads with
   colloquial keywords ("shake it out", "QA this", "find the bugs", "what's broken") and never
   says **"spec-complete gate"** or **"pre-merge gate."** When the request is phrased in gate
   language — which is exactly how `harnessed-development` Stage 3 refers to it ("run the
   spec-complete gate") — judges route it to finishing-a-branch instead. This is a harness-internal
   miss: the orchestrator's own vocabulary doesn't match the gate's trigger list.

All four other gates: clean, no FP/FN, no flaky. The sibling near-misses (threat-model vs
invariants, audit vs write-time, feature-behave vs code-bite) were correctly separated.

## Part B — Behavioral (baseline-vs-skill), the consistent finding

The Sonnet baseline is **strong on spirit** for every gate: it produces convergence-point
reasoning, denial-path tests, the comment-out-the-guard mutation check, real-browser edge tables,
manifest-then-fix QA — unprompted. What baseline reliably OMITS is the **named structured
artifact** and the **altitude/boundary discipline** each skill enforces:

| skill | baseline HAS (spirit) | baseline OMITS (what the skill adds) |
|---|---|---|
| threat-modeling | SSRF + concrete IP classes, redirect re-validation | structured assets→attacks→mitigations→**deferrals** block; framing as the review-convergence artifact |
| architecture-invariants | convergence point, grep-the-bypass, "canonical gate" | committed **ARCHITECTURE-INVARIANTS.md** doc; explicit attacks-vs-property distinction (weak miss — baseline near-complete) |
| testing-workflow | Tier-A instinct, denial path | explicit **tier label + RED-first + deferral line** structure |
| test-effectiveness | 3 failure modes, mutation bite-check | **covered/blind/fixed manifest**; audit-time-vs-write-time altitude |
| feature-acceptance | real browser, edge table | **pass/fail/not-reachable manifest**; feature-behaves-vs-code-bites distinction |
| shake-out | manifest-then-fix, e2e sweep, integration re-run | reviewer-agent dispatch framing (weak miss — baseline near-complete) |

Interpretation: these gates are **not teaching skills, they're discipline skills** — their value
is converting "the agent does the right thing *when it remembers*" into "the structured artifact
exists, auditably, *every time*, at the right altitude, without colliding with its sibling." That
is the same conclusion as the harnessed-development behavioral eval, and it holds across all six.
The two strongest baselines (architecture-invariants, shake-out) are the two where the skill's
marginal behavioral lift is smallest — their value is the *durable doc / dispatched reviewers*,
not the reasoning.

## Recommended changes

Only the two trigger defects warrant a code change; the behavioral findings are working-as-intended
(the artifacts are the point). Proposed one-line description edits:

- **testing-workflow** — add an exclusion pointing audit-time queries to its sibling, e.g.:
  *"…before sign-off (write-time, per-task). For AUDITING whether an existing green suite would
  actually catch a regression — that's test-effectiveness, not this."*
- **shake-out** — add the gate-language triggers to the list:
  *"…Triggers on 'shake it out', 'shakeout', 'does it work', 'QA this', 'find the bugs', 'what's
  broken', 'spec-complete gate', 'pre-merge gate', 'final QA before merge'."*
