# netdust-wp — correctness eval, ntdst-core 5.2.0 re-anchor

Run **2026-08-24** with `evals/run-correctness-eval.sh` over `evals/behavioral-lessons.json`
(T05 of `core-v5-skills`). Three runs; runs 1 and 2 were defect-finding, **run 3 is the
result**. Every case is pinned to `baseline_ref` **`391eb0f — pre-v5 skill text`**.

The case file holds **19 cases**. Two of them (`data-default-key`, `rest-query-parked`)
carry no `context_*` and are lessons-pins the runner skips, so **17 run**.

## Result (run 3)

| case | discriminates | judge | why |
|---|---|---|---|
| `api-rate-budget` | PASS | PASS | baseline missed `apiFetch`; it built the whole answer on `ntdst_actions()` + `ntdstAPI` |
| `pages-custom-route` | PASS | PASS | baseline emitted `add_rewrite_rule` + `add_filter('query_vars'` in code |
| `rest-cors-option` | PASS | PASS | baseline missed `cors(` and `allowed_http_origins`; it declared CORS per-route |
| `service-disable-filter` | PASS | PASS | baseline emitted `ntdst_service_` in code |
| `theme-facade-retired` | PASS | PASS | baseline emitted `$theme->style(` in code |
| `rest-handler-return` | PASS | PASS | baseline emitted `apiSuccessResponse` in code |
| `route-response-refuses` | PASS | PASS | baseline never reached the `false` refusal |
| `router-decides-brainstorm` | both-clean | FAIL | known, unchanged — see *Understood, not outstanding* |
| `router-decides-brainstorm-control` | both-clean | PASS | **both-clean IS the pass** (inverted control) |
| `limiter-exceeded-not-attempt` | PASS | PASS | baseline missed `exceeded(` |
| `declared-field-exposure` | PASS | PASS | baseline missed `show_in_rest` and `register_meta('post'` |
| `write-verb-refused` | both-clean | FAIL | mechanically undecidable — see *Understood, not outstanding* |
| `custom-url-path-only` | PASS | PASS | baseline emitted `add_rewrite_rule`, `template_include`, `add_filter('query_vars'` |
| `alias-refused` | PASS | PASS | baseline emitted `'integer'` as a valid type |
| `html-template-args` | PASS | PASS | baseline missed `$args[` entirely |
| `anonymous-write-callable` | PASS | PASS | baseline emitted `ntdst_actions(` + `ntdstAPI` in code |
| `drift-part1-honesty` | PASS | PASS | baseline never printed the skip line |

**14/17 discriminate · 15/17 judge PASS · 0 errored.**

**No after-arm carries a single code-fence violation.** Every flag the runner raised on a
`context_after` answer is a PROSE mention, and all seven were read by hand: each one names
a retired symbol in order to say it is retired. That is the behaviour the cases want.

## The machine half — `evals/retired-symbols.sh`

New in T05, and written RED before the case work. It greps the plan's 24-entry `RETIRED`
array over every `*.md` / `*.json` under the plugin, blanking `## Retired` blocks (blanking,
not deleting, so printed line numbers stay real) and skipping `*lessons.md` and `evals/`.

- On the pre-v5 skill text: `bash evals/retired-symbols.sh /tmp/old-skill.md` → **exit 1, 13 hits**.
- On the finished branch: **exit 0, 41 files scanned**.

It carries a per-file, per-symbol `ALLOW` list with a written reason on each line — the
drift reviewer must be able to spell the drift it hunts, `traps.md` must be able to warn
about a hook that failed open, and `wysiwyg` is a live ACF type in the YOOtheme skills.
Everything else is a hit.

**It found a real defect on its first green run:** `golden-paths/yootheme-integration.md`
taught `ntdst_service_{slug}_enabled` / the `ntdst_service_{slug}` option as the way to
switch a YOOtheme source off. Both are retired, and that filter FAILED OPEN — a source
somebody switched off through it boots after the upgrade. Fixed to the two real switches
(`metadata()['enabled'] => false`, or a `services.conditional` entry) rather than
allowlisted, because allowlisting it would have been switching off the gate that caught it.

It also carries the Cluster A structural check: every `ntdst_data()->register(` block in a
golden path that declares a field-level `'show_in_rest' => true` must declare the
type-level flag too, or WordPress mounts no `/wp/v2` route and every field flag publishes
nothing. Proven by mutation both ways — deleting the type-level line fails the gate,
deleting all the field flags correctly stays clean.

## Method, and why it differs from netdust-agent's runner

`netdust-agent/evals/run-behavioral-eval.sh` uses NO SKILL as the baseline. Right for a
discipline skill ("does it make the agent do what it skips by default"), wrong here: a
no-skill arm never says `ntdst_router()` at all, so it cannot show a correctness
re-anchor landed. **Baseline here is the OLD SKILL TEXT**, read with `git show` from the
commit each case names in `baseline_ref`. Both arms get the same prompt; only the
reference documentation differs.

Scoring is mechanical first (`must_contain` / `must_not_contain`), judge second.
`must_contain` is checked against the whole answer; `must_not_contain` only inside code
fences, because prose that WARNS against a dead symbol is the desired behaviour.

**Every case was written against a verified asymmetry.** Before a probe went in the file,
the symbol was counted in the 391eb0f text and in the branch text; a probe with no
0-in-old / >=1-in-new gap cannot discriminate and is not worth an API call. That check is
what made `write-verb-refused` predictable — see below.

## What the eval found — in the eval

Run 1 scored **7/17**. Almost none of it was real.

1. **A transport failure is not an answer, and the runner counted it as one.** `claude -p`
   prints `API Error: 529 Overloaded` to STDOUT as prose and exits 0, so it arrives looking
   exactly like a short reply. Five arms across five cases came back as 529 banners, and
   four cases then read as "the skill fails to teach `ntdst_rest()`" when the arm had never
   run. `ask()` now detects transport banners, retries twice with backoff (20s, 40s), and
   reports ERRORED rather than scoring them. This is the same defect class as the
   `--max-turns 1` bug — a non-answer scored as a failure — caught a second time in a new
   disguise.
2. **A substring probe cannot tell a use from a warning, even inside a fence.**
   `pages-custom-route` failed a textbook-correct answer whose only fenced `query_vars` was
   the comment *"`load_template()` extracts `$wp_query->query_vars`"* — the warning the
   skill wants. Fence-scoping does not save you when the warning IS a comment. The probe
   now targets the v4 SHAPE, `add_filter('query_vars'`, which a comment about the WordPress
   global cannot match.
3. **The same trap, one layer up: an assertion that forbids NAMING.** Four cases scored
   judge FAIL for correct answers, because the assertion said "does not name
   `$theme->style()`" / "`apiSuccessResponse()`" / "`ntdst_actions()`" / "the
   `ntdst_service_{slug}_enabled` filter" — while the PROMPT asked what replaced them. The
   judge applied the assertion exactly as written and was right to. Every one now reads
   *may and should NAME it as retired; the test is that it does not RECOMMEND it.*
   **This is the fourth run in this file's history to lose a case to that wording.**
4. **An assertion may not grade what the prompt never asked.** `route-response-refuses`
   failed for not reciting the whole return-value table on a prompt that asked two
   questions. Demoted to a bonus.
5. **A `must_contain` literal is a paraphrase lottery.** `declared-field-exposure`
   described the `register_meta('post', …)` widening perfectly, in its own words, and
   missed the literal. Fixed by sharpening the PROMPT to ask for the call by name, not by
   loosening the probe — the baseline still cannot answer it.
6. **A probe that forbids a variable name forbids its own correct answer.**
   `html-template-args` banned `$slots` in fences to catch a loose read; the correct answer
   writes `$slots = $args['slots'] ?? [];` and was scored as the bug it avoids.

Runs 2 and 3 were re-runs after those corrections: **7/17 -> 12/16 -> 14/17**. Every case
edit between runs is recorded in that case's `probe_note`, with the reason, so the
adjustments are auditable rather than merely asserted. **No skill text was changed to make
a case pass**, and the only source edit this task made is the yootheme-integration fix the
gate demanded.

## Understood, not outstanding

Three cases do not discriminate, and all three are explained:

- **`router-decides-brainstorm-control`** — inverted. Both-clean **is** the pass: it proves
  the router fix did not make every WP task brainstorm. Its after-arm says "no plan, no
  brainstorming" in prose, which is the negation, read by hand and correct.
- **`router-decides-brainstorm`** — both-clean since 2026-08-21, unchanged by this task and
  reproduced at exactly its prior result. Both arms route correctly; the CLAUDE.md fix is
  confirmed by its grep discriminator, not by this prompt. Needs a better prompt, not a doc
  change. Its judge flipped PASS (run 2) -> FAIL (run 3) on identical input, which is the
  oscillation this file has measured before.
- **`write-verb-refused`** — the interesting one, and it stays on the record rather than
  being tuned green. The baseline reaches the **wrong conclusion** on the capability-string
  route (it says a string is not callable, so the route is refused — the v4 rule) while
  using the words `current_user_can` inside the closure workaround it proposes. The words
  are present, the conclusion is inverted, and **no substring probe scores a conclusion.**
  It also recommends `__return_true` in PROSE, where the fence-scoped `must_not_contain`
  cannot see it. Read the judge on this case, not the probe.

## Read this before trusting a single run

The **mechanical** signal is stable. The **judge** oscillates by ±2 between identical
inputs and cases swap which side they fail on; `skill-eval` asks for 5+ reps per variant
and it is right. Treat one judge FAIL as a prompt to READ the answer, never as a result —
in this task, doing exactly that turned four judge FAILs into four assertion defects.

Two standing lessons, each of which produced a wrong number first:

- **An eval that pins an ABSENCE has a shelf life measured in releases.** The 4.x-era
  `rest-cors-gap` asserted "core ships no CORS" and inverted the week core shipped one; it
  would have failed a future session for being right, and looked authoritative doing it.
- **A baseline that already knows the answer measures nothing.** The runner asks in a clean
  room — neutral cwd, replaced system prompt, `--strict-mcp-config` — because an early run
  had the baseline arm answering *"those don't exist on current ntdst-core"*, the fixed
  knowledge leaking in from the repo's own `CLAUDE.md`.

## Prior runs

The 4.x re-anchor history (runs 1–6 of 2026-08-20, the 2026-08-21 re-baseline after
`ntdst-architecture` + `ntdst-data` collapsed into `ntdst-framework`, and the four
harness defects each of those cost) is in this file's git history. The durable lessons
from it are folded into the two sections above; the run numbers are not, because they
scored a skill text that no longer exists.
