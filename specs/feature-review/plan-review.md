# Plan review — feature-review R6–R8 (promote reviews first, levels, /review-fix)

Reviewed-plan: 973ef9c40a49d2bae9ea4972616adafea3a5892e specs/devops-promote-review/plan.md
Reviewed-plan: a5ba593cb08389384bd6d2d47afc721e83a60d2c specs/gates-review-fix/plan.md
Verdict: ready with fixes

**How I checked it.** I copied `plugins/netdust-devops/dist` into the session scratchpad. There I applied the devops plan's Step 1 and Step 3 exactly as written (the Makefile edits and the flow-test additions) and ran `flow-test.sh`. Result: **207 ok, 1 failed**. The unmodified copy gives 201 ok, 0 failed. Nothing in the repo was edited.

## Blocking
None. Every premise about the source holds (list below).

## Should fix

1. **devops Task 1 Step 1: the "promote reviews first … then asks" check fails as written. I ran it and it failed.** The plan's own `review` recipe prints the Findings line twice:
   - once through `cat "$$OUT.tmp"`, since the stub's output (and /feature-review's) ends with it;
   - once more through `grep -m1 '^Findings:' "$$OUT"`.

   So `grep -n 'Findings:' | cut -d: -f1` returns two line numbers. The captured run returned `58\n60`, with `Continue?` at 63. The `[ … -lt … ]` test then errors (`flow-test.sh: line 515: [: 58\n60: integer expression expected`), and the assertion gets `[0 name=rv scope=feature level=full ]` where it expects `…level=full 1`. Step 4 (GREEN) cannot pass.
   - **Smallest change:** use `grep -n -m1 'Findings:'` in the check. Or drop the re-printing `grep -m1` line from the recipe, because `cat` already shows the line.

2. **devops Task 1 Step 1: the restore changes origin, but the section says "origin untouched".** `step unpromote name=rv` rebuilds staging from `origin/main`. Staging's non-`promote:` commits are dropped: before the section `origin/staging` carried `local only | u | ahead`, and afterwards it carried nothing. The `git ls-remote origin` checksum changed across the section. Later sections still passed in my run, but every other section in the file restores origin: it captures `exact refs/heads/staging` first, force-pushes it back, and asserts `git ls-remote origin`. The plan's "Restore after it" does not do that.
   - **Smallest change:** at the section start, add `RORIG=$(git ls-remote origin); RSTG=$(exact refs/heads/staging)`.
   - Restore with `git branch -q -f staging "$RSTG"; git push -qf origin "$RSTG:refs/heads/staging"` plus the existing feature/rv cleanup, instead of `step unpromote`.
   - Make the final assertion also compare `$RORIG` with `$(git ls-remote origin)`.

3. **devops Task 1: a new guarded CLI sink has no injection pin.** `review=` joins `_CLI_GUARDED`. In `plugins/netdust-devops/tests/test-makefile.sh:566-573`, every other guarded variable gets `inject "$P" <target> <var>` (three payload forms) and a "run nothing" assertion. The allowlist (`off low full ultra`) makes injection impossible today, but the house pattern pins each sink, so a later loosening would show up.
   - **Smallest change:** add `inject "$P" review review name=x` to that block and name `review=` in its ok line. Add it to the plan's Files list.

4. **gates Task 1 Step 2: "ultra" says what, not how.** The text: "`staging-reviewer` on staging's promoted features with this feature added at its head". `agents/staging-reviewer.md` takes "the production base, the staging head and the features as `name:pin`". Its step 3 compares hunks "with staging's merged version", and no merged composition exists before promote.
   - **Smallest change:** spell out the dispatch. Base is production, head is `origin/<staging branch>`, and the features are staging's `promote:` merges plus `<name>:origin/feature/<name>`. If `<name>` is already on staging, the new pin replaces the old one. For files the new feature touches there is no merged version, so the reviewer reads the pins.

5. **gates Review Focus: both lines point at "(Task 2 text)", not at a test.** The Task 2 pin only checks that the strings `"never stash"` and `"which findings"` appear. That shows the words exist, not that the command stops. The harness already has a behavioural home: `evals/cases.json`, including `close-calls-make-review`. The global rule is that a skill's behaviour ships with an eval.
   - **Smallest change:** add one eval case, e.g. `review-fix-no-report`: there is no saved report, the reply names `make review name=X`, and no file is changed. Point the first Review Focus line at it. Say plainly that the dirty-checkout line is guarded by the prose pin only.

6. **gates Task 2 Step 3: the policy paragraph it extends would contradict itself.** `skills/policy/SKILL.md:124-127` ends "All three report; he approves what follows." Adding `/review-fix`, which edits code, as a fourth item makes that sentence wrong.
   - **Smallest change:** in the same edit, make the sentence say the three report, and that `/review-fix` changes only what Stefan picks.

7. **gates Global Constraint vs Task 2 Step 2.** The constraint says "/review-fix points at [Close step 4] and does not restate it". Step 4 of the command then restates it: "each picked finding one fix, RED→GREEN through the seam where it showed, then the suite (`make gate`)".
   - **Smallest change:** cut the step to "the fix pass is `netdust-gates:policy` Close step 4, on the picked findings only".

## Note

- **Re-review by default.** The `/review-fix` hand-back ("reviewing it again unless he adds `review=off`") makes a full re-review the default after a fix pass. Policy Close step 4 (`skills/policy/SKILL.md:118-119`) says "No re-review — named checks and the suites close it", and Stefan's memory has "no reviewer re-dispatch after fix rounds". The spec (R6, R8) allows either. Stefan may want the hand-back to suggest `review=off` or `review=low` for the re-promote. This is a wording choice, not enforcement.
- **No live output during the review.** `review` redirects the reviewer's stdout to `$OUT.tmp` and shows it only when it finishes. With a real `claude -p` reviewer, `promote` goes quiet for minutes before `Continue?`. A version that streams and keeps the exit code without `pipefail` (dash): `{ sh -c "$R"; echo $? > "$OUT.rc"; } | tee "$OUT.tmp"`. Take it or leave it.
- **A failed run replaces the last good report.** On a non-zero exit, `mv "$$OUT.tmp" "$$OUT"` still overwrites the previous report, so `/review-fix` would then read partial output. `[ $RC = 0 ] && mv … || rm -f "$OUT.tmp"` keeps the last good one.
- **"Did not run" is not quite true.** The promote warning says "the review did not run", but the case the test drives is a review that ran and exited non-zero. "the review failed — promote goes on" is accurate for both cases.
- **Findings line format.** The gates text asks for the line inside backticks. If the model echoes the backticks or bold, `grep '^Findings:'` finds nothing and make prints nothing (`|| true`), silently. Consider saying "a plain line, no formatting".
- **Name collision.** A feature named `staging` and `make review env=staging` both write `reviews/staging.md`. Negligible.
- **Worktrees.** `/review-fix` step 2 runs `git checkout feature/X`, which fails when that branch is checked out in another worktree. Say "work where `feature/X` is checked out", or refuse naming the worktree.
- **Without devops.** `/review-fix` step 1 tells the user to run `make review name=X`, which does not exist on a project without devops, and `/feature-review` saves nothing there. The executor may need a ruling.

## Premises checked
- `_CLI_GUARDED` at line 25 → `dist/Makefile.netdust:25` → holds
- `_dryrun-ok` ≈ line 53, with `_why-*` beside it → `Makefile.netdust:53,59` → holds
- `_cli-check` refuses a typed invalid value and drops an inherited one; its message contains "Refused review=" → `Makefile.netdust:61-62` → holds (the bogus case passed in the scratch run)
- The recursive `$(MAKE) --no-print-directory review name=$(name) review=…` inside promote passes the CLI guard: in the child `review` is typed and allowlisted, and `name`/`review` are in `_CLI_VARS`, so `_CLI_LOOSE` is empty → `Makefile.netdust:25-37` → holds (passed in the run)
- No `.SHELLFLAGS`/`-e`, so `RC=$$?` after a failing `sh -c` is reached → `Makefile.netdust` (no SHELLFLAGS; `/bin/sh` is dash) → holds ("a review that fails … still promotes" passed)
- `review` target ≈ line 499, last line `REVIEW_NAME=… sh -c "$$R"`, preceded by the BLUE echo → `Makefile.netdust:500-513` → holds
- The promote recipe has the `git --no-pager log` line directly before `read -p "Continue?` in one shell line → `Makefile.netdust:217-223` → holds
- Promote needs no clean tree; `_ensure-flow` refuses only local rung commits missing from origin → `Makefile.netdust:208-227, 947-977` → holds
- No existing make variable `review` in the core or mk/ → grep `(review)` / `review=` → holds
- flow-test "review: runs commands.review" section and its two expected lines → `flow-test.sh:493-507` → holds
- Helpers `Y`, `YF` (sets `YOUT`/`YRC`), `step`, `has`, `exact` → `flow-test.sh:72-73, 217-219, 29` → holds
- The uncommitted `sed` of site.yml survives `checkout -b feature/rv origin/main` (main == origin/main after the e2e section's restore) → `flow-test.sh:487-489` → holds (ran)
- The FLOW help's first column stays `review` and `promote`, so the `flowverbs` assertion is unaffected → `flow-test.sh:105-106`, `Makefile.netdust:109-110` → holds
- Devops `tests/run.sh` runs flow-test (through test-makefile.sh) and prints "netdust-devops: all suites passed" → `tests/run.sh:10`, `tests/test-makefile.sh:304-312` → holds
- dist/VERSION, plugin.json, marketplace are at 0.8.0; the marketplace test checks versions agree → `dist/VERSION`, `tests/test-marketplace.sh:33-42` → holds
- SKILL.md has `promote` and `review` verb rows and a "What gets said" table → `skills/devops/SKILL.md:68, 113, 116` → holds
- The `/feature-review` pin tuple exists in test_close_wiring, and the added strings appear in the planned text ("REVIEW_LEVEL" via `$REVIEW_LEVEL`, "ultra", "Findings: <b> Blocking") → `tests/test_close_wiring.py` (feature-review tuple) → holds
- "**What to review.**" and "**Report back**" headings exist → `commands/feature-review.md:9,32` → holds
- Task 2 pin strings ("git-common-dir", "Close step 4", "make promote name=", "which findings", "never stash") all appear in the planned review-fix.md → plan Task 2 Step 2 → holds
- test_session_commands scans only its PAIRS, so a command with no agent passes → `tests/test_session_commands.py:13-14` → holds
- Quote "becomes the fixer before Stefan approves anything" → `tests/test_session_commands.py:5-6` → holds
- Policy under 150 lines (127 now), with an "On demand" paragraph → `skills/policy/SKILL.md:124-127`, `tests/test_policy_skill.py:41` → holds
- Close step 4 is the fix pass, "No re-review" → `skills/policy/SKILL.md:118-119` → holds
- The gates suite is green at HEAD ("All harness tests passed.") → `tests/run.sh` → holds

## The cut
- specs/devops-promote-review/plan.md → one feature. It covers R6 and the saving/printing half of R7, and is testable alone because the flow-test stubs the reviewer.
- specs/gates-review-fix/plan.md → one feature. It covers the level semantics of R6, the Findings line of R7, and R8, and is testable alone because its pins and the no-report path need no devops change.

The two plans share only a text contract (`REVIEW_LEVEL`, the `Findings:` line, `<git-common-dir>/reviews/<name>.md`), not files. They are not artificially split, and no requirement is left without a plan.

---

## Applied

All seven Should-fix, plus the notes: keep the last good report on a failed run, "the review failed", a plain Findings line, the worktree case, no re-review after /review-fix (the saved review is skipped). Then, on Stefan's later asks: skip-if-reviewed promote (R6), the Close order by cost (R9, gates Task 3), artifacts in one obvious place (R10, gates Task 4). Not re-reviewed.
