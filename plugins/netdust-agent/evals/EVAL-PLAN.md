# netdust-agent — eval plan (proving each artifact enhances coding)

Goal: prove every skill / agent / command enhances coding, via skill-eval methodology.

## Two dimensions (both required for "enhances coding")

1. **Trigger eval** — does the artifact's description fire on should-trigger coding
   prompts and stay quiet on near-misses? An artifact that never fires (or fires on
   the wrong thing) cannot enhance coding regardless of its content.
   - Harness: `run-trigger-eval.sh` over `trigger-queries.json` (78 = 39×2).
   - `claude -p` acts as router-judge: "given this request + this tool desc, YES/NO use it?"
   - PASS bar per artifact: both its queries route correctly (trigger fires, near-miss doesn't).
   - Mixed/failing → description needs sharpening (the highest-leverage fix per skill-eval).

2. **Behavioral eval** — when applied, does the artifact change the output for the
   better vs baseline (skill off)? Run on the DISCRIMINATING artifacts only:
   the ones whose value is a behavior change you can observe. Tiered by how much
   behavioral proof each needs:

   | Tier | Artifacts | Why | Proof |
   |---|---|---|---|
   | **B1 — behavior change is the whole point** | writing-tests, testing-workflow, threat-modeling, test-effectiveness, feature-acceptance, architecture-invariants, simplifying-code, doubting-decisions, refining-ideas, sourcing-from-docs, engineering-context | each is a discipline whose value = it makes the agent DO something it skips by default | baseline vs with-skill on a realistic prompt; assertion = the discipline's signature behavior appears with-skill, absent baseline |
   | **B2 — sequencer/orchestration** | harnessed-development, planner, implementer, reviewer, shakeout-qa | value = it routes/gates correctly | reachability already proven (wiring audit); trigger eval + a dispatch dry-run |
   | **B3 — thin pointer / battle-tested copy** | deploying, dev-stack, versioning-with-git, building-frontend, driving-the-browser, the 4 specialist agents (security-sentinel, performance-oracle, invariant-auditor, code-simplicity-reviewer), all 11 commands | value = routes to an authority OR is a verbatim, already-proven core artifact | trigger eval suffices; behavioral value inherited / pointer-only |

## Verdict rule (when is an artifact "proven to enhance coding"?)

- B1: trigger correct AND behavioral comparison shows the signature behavior with-skill that baseline lacked.
- B2: trigger correct AND reachable in the sequencer/dispatch (wiring audit, done).
- B3: trigger correct (the artifact is a pointer or a verbatim proven copy; its content was proven in core).

An artifact that fails trigger eval is NOT proven — its description gets sharpened and re-run until it routes.
