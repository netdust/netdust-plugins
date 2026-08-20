# netdust-wp — correctness eval, ntdst-core 4.x re-anchor

Run 2026-08-20 with `evals/run-correctness-eval.sh` over `evals/behavioral-lessons.json`.
Six runs; runs 1–4 were harness debugging, run 6 is the result.

## Result (run 6)

| case | discriminates | judge |
|---|---|---|
| pages-custom-route | PASS — baseline emitted `ntdst_router(` + `NTDST_Router` in code | PASS |
| rest-cors-option | PASS — baseline emitted `NTDST_Cors_Policy` + `max_body_bytes` | PASS |
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

## Superseded after the run: ntdst-core 4.1.0 landed CORS

Run 6 scored a case called `rest-cors-gap`, whose assertion was that the session must
surface "core ships no CORS" and NOT pass a `cors` route option. **ntdst-core tagged
v4.1.0 with a real `cors` option**, so that assertion inverted: passing `cors` is now the
correct answer. The case was re-cut on main as `rest-cors-option` (commit `d80aafa`) and
this branch takes that version.

The run 6 PASS still stands for what it measured — the baseline emitted
`NTDST_Cors_Policy` (a class that has never existed in ANY version) and `max_body_bytes`,
and the current text emits neither. What no longer stands is the "no CORS" half. The
re-cut probes drop `'cors'` from `must_not_contain` and keep `NTDST_Cors_Policy`,
`max_body_bytes` and a hand-rolled `Access-Control-Allow-Origin`. **Not re-run since the
re-cut** — the CORS row above is from the pre-4.1.0 assertion.

The general lesson, worth more than the case: an eval that pins an ABSENCE has a shelf
life measured in releases. `rest-cors-gap` would have failed a future session for being
right, and looked authoritative doing it.

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


---

# Re-baseline after the collapse — 2026-08-21

`ntdst-architecture` + `ntdst-data` merged into `ntdst-framework`, so every case's
`context_before` pointed at paths that no longer exist. Re-baselined: **`context_before`
is now spelled as its own `baseline_ref` COMMIT spelled it**, `context_after` reads the
working tree. All 33 paths verified to resolve before running. Runner parallelised —
**2m37s**, down from ~20 minutes serial.

## The collapse cut four things it should not have

The run found them; the greps could not have. All four are now restored in SKILL.md:

1. **A custom URL needs BOTH a rewrite rule and a route.** Dropped entirely — the model
   then called the pairing "drift" and rejected it. `NTDST_Pages` matches on
   `REQUEST_URI`; the rewrite exists only so WordPress does not 404 first.
2. **`path()`'s third argument** for non-GET. Gone with it.
3. **The `cors` route option (4.1.0).** The collapsed contract named `ntdst_rest()` as a
   door and nothing else, so the model *denied any route option existed* and refused to
   give a CORS answer at all — one release after core shipped one.
4. **`ntdst_actions()->register()`'s opts** (`public` / `cap_type` / `capability` /
   `priority`) and the dispatch-floor reasoning. The model hand-resolved the capability
   inside the handler instead, losing the fail-closed gate.

Plus one tension I introduced: CLAUDE.md's "Read `site.yml` FIRST" competed with
`harnessed-development` being the entry point, and the model put site.yml ahead of the
router. Reconciled — site.yml is the operating context, not the entry point.

Judge score across the three runs: **5/9 → 8/9** once those were restored.

## Read this before trusting a single run

| run | discriminate | judge |
|---|---|---|
| A — re-baselined | 7/9 | 5/9 |
| B — after restorations | 5/9 | 8/9 |
| C — after probe fix | 7/9 | 7/9 |

The **mechanical** signal is stable at 7/9. The **judge** oscillates by ±2 between
identical inputs, and cases swap which side they fail on. That is single-sample LLM
judging, not the skills moving — `skill-eval` says 5+ reps per variant and it is right.
Treat one judge FAIL as a prompt to READ the answer, never as a result.

The two cases that never discriminate are understood, not outstanding:
`router-decides-brainstorm` (both arms answer correctly; the CLAUDE.md fix is confirmed
by its grep, not by this prompt) and `router-decides-brainstorm-control`, where
both-clean **is** the pass — it is inverted, and it proves the fix did not make every WP
task brainstorm.

Two probe lessons, both of which produced a wrong number first:

- A violation counts only inside a code fence, because prose that WARNS against a symbol
  is the desired behaviour. But that opens the reverse hole — a baseline recommending
  `toRestResponse()` in prose scores clean — so `prose_mentions` is reported separately
  and read by hand. No probe removes that step.
- `must_contain` on a literal is brittle: the control scored FAIL for writing
  **`Class: E`** when the probe wanted `Class E`. The answer was right. Class-letter
  judgement is the judge's job; the mechanical half only checks that a class was
  assigned and no brainstorming happened.
