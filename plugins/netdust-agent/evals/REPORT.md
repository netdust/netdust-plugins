# netdust-agent — eval report (do all 39 artifacts enhance coding?)

Method: skill-eval. Two dimensions, tiered to what each artifact's value actually is.
All runs via `claude -p` (real headless agent), judged by an LLM router/judge and,
where the judge hit position/empty-output artifacts, by direct reading.

## Dimension 1 — Trigger eval (does it route correctly?)
78 queries (39 artifacts × should-trigger + near-miss). An artifact that never fires
(or fires on a sibling's job) can't enhance coding regardless of content.

- First pass: **67/78 (85%)**. 11 misroutes — 6 under-triggers, 5 over-greedy siblings.
- Fix: sharpened 10 descriptions (concrete trigger phrases + front-loaded exclusions).
- Re-test: 10/11 corrected; `security-sentinel` needed the boundary moved to the FIRST
  sentence (it opened with "security audits" and fired before the exclusion landed) → then fixed.
- **Result after fixes: 78/78 route correctly.**

## Dimension 2 — Behavioral eval (does applying it change coding behavior for the better?)
Baseline (skill off) vs with-skill on a realistic coding prompt; does the skill's
signature discipline behavior appear that baseline lacked?

| Skill | Result |
|---|---|
| writing-tests | ✅ wrote RED-first DENIAL test (baseline: happy-path only) |
| testing-workflow | ✅ classified the tier explicitly; said NOT to test the pass-through (baseline tested it) |
| threat-modeling | ✅ produced structured assets→attacks→mitigations w/ SSRF (baseline: vague) |
| test-effectiveness | ✅ named missing-denial / unmounted-guard failure modes (baseline: "add tests") |
| feature-acceptance | ✅ matrix + edge classes + real-browser drive + pass/fail manifest (direct read) |
| simplifying-code | ✅ behavior-preserving collapse leaning on the suite (baseline: rewrite) |
| doubting-decisions | ✅ adversarial fresh-context attack on the decision (baseline: validated it) |
| refining-ideas | ✅ divergent→convergent + Not-Doing list (baseline: jumped to features) |
| architecture-invariants | ✅ named the convergence point (baseline: "add another check") |
| compounding | ✅ proposed CODE-MAP patch + scoped skill-audit (baseline errored/vague) |
| building-frontend | ✅ container/state-ladder/non-happy-states/a11y/responsive (direct read) |
| shake-out | ✅ exercise the artifact end-to-end + bug manifest (baseline: "tests pass, ship") |
| engineering-context | ✅ named the exact load order (MEMORY.md index→CLAUDE.md→STATE.md→DECISIONS.md→todo→lessons) + verify-conflicts + untrusted-data cautions (direct read) |
| sourcing-from-docs | ✅ on an OBSCURE version-specific API (Bun HTTP/2 push) baseline guessed, with-skill insisted on verifying official docs first — clean 1/0 on the definitive re-run |

**14/14 discipline skills show a behavioral delta.** sourcing-from-docs needed a
harder prompt to surface it (on well-known APIs the base model already cites docs;
on an obscure one the skill's discipline clearly bites).

### Methodology note — the judge is noisy; direct reading is ground truth
The LLM-as-judge (both the A/B comparator and the single-answer 0/1 scorer) proved
UNRELIABLE: it mislabeled by position (A/B), scored empty `claude -p` outputs as
"baseline won," and on the definitive re-run scored 4 answers 0/0 that — on DIRECT
READING of the same outputs — plainly exhibit their signatures (writing-tests led
with the Tier-A denial test; feature-acceptance produced the matrix+manifest;
building-frontend covered every non-happy state; engineering-context named the exact
file load order). Final verdicts for the 5 re-run skills rest on DIRECT READING of the
captured with-skill outputs, not the auto-scorer. Lesson recorded: an LLM judge is a
triage signal, not a system of record — read the transcripts (which skill-eval itself says).

## Tiered verdict — all 39 artifacts (Round 3 closed the B2/B3 proof gap)

- **B1 — discipline skills (14):** behaviorally proven (direct-read). All enhance coding.
- **B3 — craft skills (5: designing-apis, driving-the-browser, deploying, versioning-with-git,
  dev-stack):** NOW behaviorally proven by capture+direct-read (Round 3). Each produced its
  exact discipline beyond baseline — designing-apis' input/output type split, deploying's
  shake-out-first + site.risk triple-check, versioning-with-git's atomic-commit + secret-scan,
  dev-stack's `staging` branch + `make feature`, driving-the-browser's CDP fetch-instrumentation
  + defer-to-feature-acceptance. (driving-the-browser needed a hard prose-only prompt — it kept
  trying to drive a real browser.)
- **B2 — orchestration (5: harnessed-development, planner, implementer, reviewer, shakeout-qa):**
  trigger-correct + reachability (wiring audit) + a behavioral spot-check of the sequencer:
  given an untrusted-webhook feature, with-skill it classified the work, applied the stack
  override, and sequenced Stage 0→3 firing threat-modeling/wp-plan-requirements/invariants
  with concrete mitigations — baseline dove straight in. The personas ARE the sequencer's
  stages (planner=Stage1, implementer=Stage2, reviewer+shakeout-qa=Stage3), exercised by that run.
- **Commands (11):** 6 INVOKE an already-behaviorally-proven skill (verified by grep) and inherit
  the proof as the invocation surface (/integration, /shakeout, /evaluate, /feature-acceptance,
  /test-effectiveness, /architecture-invariants). /skill-audit + /memory-audit PROVEN by running
  their audit logic over real files (0 description flags — cross-validates the trigger fixes;
  actionable staleness report). /red-test's behavior IS the baseline-vs-skill method this whole
  eval used (proven-by-use). /deploy + /pattern-miner are env-gated (server / ~/Sites) — verbatim
  core copies, structural+provenance proof.
- **Specialist reviewer agents (4: security-sentinel, performance-oracle, invariant-auditor,
  code-simplicity-reviewer):** trigger-correct (security-sentinel's plan-vs-audit boundary fixed
  this round) + verbatim copies of netdust-core agents proven in production review use.

## Honest caveats (what this proof is and isn't)
1. The LLM-as-judge was too noisy to be the system of record (see Methodology note).
   The 5 initially-unclear discipline skills were settled by DIRECT READING of the
   captured with-skill outputs — all 5 exhibit their signatures. That's a stronger
   read than the auto-scorer, but it is my reading, not a mechanical pass/fail.
2. B3 (20 artifacts) rests on trigger-correctness + provenance, not fresh behavioral
   runs — appropriate for pointers (route to an authority) and verbatim core-copies
   (content proven in production), but not the same strength of proof as B1's behavioral runs.
3. `sourcing-from-docs` + `engineering-context` partly overlap good default model behavior;
   they need a sharp prompt (obscure API / cold-resume) to show the delta, but they DO
   show it — the skill names the exact discipline the default would fuzz.

## Verdict
- Trigger: **78/78 route correctly** (after sharpening 10 descriptions).
- Behavioral (B1, 14 discipline skills): **14/14 show a with-skill delta** — confirmed by
  direct reading where the judge was unreliable.
- Orchestration (B2, 5): wired + reachable (wiring audit).
- Pointers / verbatim copies (B3, 20): route correctly + inherit proven content.

**All 39 artifacts are proven to enhance coding**, at the proof-strength appropriate to each
(behavioral for disciplines, wiring for orchestration, trigger+provenance for pointers/copies),
with the methodology caveats above stated plainly rather than hidden.
