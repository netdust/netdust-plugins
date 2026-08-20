# netdust-wp — correctness eval, ntdst-core 4.x re-anchor

Run 2026-08-20 with `evals/run-correctness-eval.sh` over `evals/behavioral-lessons.json`.
Six runs; runs 1–4 were harness debugging, run 6 is the result.

## Result (run 6)

| case | discriminates | judge |
|---|---|---|
| pages-custom-route | PASS — baseline emitted `ntdst_router(` + `NTDST_Router` in code | PASS |
| rest-cors-gap | PASS — baseline emitted `NTDST_Cors_Policy`, `'cors'`, `max_body_bytes` | PASS |
| service-disable-filter | PASS | PASS |
| theme-facade-retired | PASS — baseline emitted `apiAction` in code | PASS |
| rest-handler-return | PASS — baseline emitted `toRestResponse` in code | PASS |
| route-response-refuses | PASS | PASS |
| router-decides-brainstorm | both-clean | FAIL (see below) |
| router-decides-brainstorm-control | both-clean — **this is the pass** (inverted) | PASS |

**6/8 discriminate · 7/8 judge PASS · 0 errored.**

## Method, and why it differs from netdust-agent's runner

`netdust-agent/evals/run-behavioral-eval.sh` uses NO SKILL as the baseline. Right for a
discipline skill ("does it make the agent do what it skips by default"), wrong here: a
no-skill arm never says `ntdst_router()` at all, so it cannot show a correctness
re-anchor landed. **Baseline here is the OLD SKILL TEXT**, read with `git show` from the
commit each case names in `baseline_ref`. Both arms get the same prompt; only the
reference documentation differs.

Scoring is mechanical first (`must_contain` / `must_not_contain`), judge second.

## What the eval found — in the docs

Two real defects, both in the fix, both now corrected:

1. **`pages.md` named the `>= 400` refuse branch but gave no worked alternative**, so the
   model reinvented `status_header(403)` + `render()` — the exact hand-rolling the
   status split exists to remove. Added the two clean options.
2. **The first attempt at that fix led with the escape hatch**, and the next run showed
   the model taking it and dropping the clean option entirely. Reordered: WP-owns-the-
   denial first, 2xx-Response-through-the-output-class second, `status_header()`
   explicitly called out as not-the-answer. The same case paid twice.

## What the eval found — in the eval

Four harness/test defects. Recording them because each produced a confident wrong number:

1. **`--max-turns 1`** returned the literal string `Error: Reached max turns (1)` for
   large-context prompts, and the probe scored an EMPTY ANSWER as a skill failure.
   Produced a bogus 0/8 and a PASS→FAIL flip between two identical runs. Now 14, and an
   unanswerable arm is reported ERRORED, never scored.
2. **Context leak — the serious one.** The runner `cd`'d into the repo, so `claude -p`
   inherited the project CLAUDE.md and repo context. The BASELINE arm answered *"those
   don't exist on current ntdst-core"* — it already knew the fix. A baseline that knows
   the answer measures nothing. Now runs in a clean room: neutral cwd, replaced system
   prompt, `--strict-mcp-config`.
3. **Substring probes cannot tell a USE from a WARNING.** Run 3 failed three cases on
   prose reading "`$theme->apiAction()` is retired, do not use it" and "there is no
   `toRestResponse()`" — the desired behaviour, counted as the violation. Violations are
   now counted only inside code fences (the failure mode is a session PASTING a dead
   symbol). That opened the opposite hole: run 5's baseline recommended
   `toRestResponse()` in PROSE as a valid terminal call and scored clean. Both are now
   reported — `violations` (code) and `prose_mentions` (prose, flagged READ THESE) — and
   the prose ones are read by hand. There is no probe that removes this step.
4. **A wrong assertion failed a correct answer.** `theme-facade-retired` asserted "no
   method on `$theme` outside the five wired mixins", which wrongly condemned
   `$theme->on('admin_enqueue_scripts', …)` — `on()` is a real `NTDST_Theme` method.
   The assertion, not the answer, was wrong.

## Open

- **`router-decides-brainstorm` is both-clean and judge-FAIL.** The after arm routes
  correctly (Class A → planning → brainstorming → the seam) but never states Stakes and
  defers entry rather than entering. The baseline also passed the mechanical probe, so
  the case does not yet discriminate. Suspect the `-p` framing ("answer using only the
  provided documentation") rather than the fix — the CLAUDE.md change is confirmed by
  the grep discriminator. Needs a better prompt, not a doc change.
- **Runtime.** 8 cases × 2 arms + 8 judges = 24 serial `claude -p` calls with up to 35KB
  of context each. Slow. Parallelise before the next run.
- The two lessons.md-pinning cases (`api-rate-budget`, `data-default-key`) carry no
  `baseline_ref` and were not run; they need the no-skill baseline the netdust-agent
  runner provides.
