# Plan review — wp-ai-skills
Reviewed-plan: d436304dced06648e2a87f573c798d3c03662871 specs/wp-ai-skills/plan.md
Verdict: ready with fixes

Nothing is Blocking. Every fix from round 3 landed, and the new verify design is consistent with the upstream skill. Two Should-fix items are left: a wrong RED count, and three lines still worded for the old design.

**Round 3's findings, checked against this blob:**
- **Landed as written:**
  - B1, option (b): the pack line at plan :149, Task 3's sentence at :198, and :151.
  - S2: all five lines.
  - N1: runtime mode, `--status=must-use`, the report path, and the full name `<namespace-slug>/<name>` in bullet 1.
  - N2: adopted, and spec R16 matches it.
  - N3: the grep is in Close 4.
  - N4: Global Constraints bullet 4 and Task 3 Step 5.
  - N5: Task 2 Step 1.
  - N6: Task 6 Step 1 now keeps `:36-45` on purpose.
- **Partly landed:**
  - S1: `:94` now correctly passes at RED, but the total is still wrong (S1 below).
  - N4: Test map row 3 still says "two-case" (S2 below).

## Blocking
None.

## Should fix

**S1. The RED count in Task 1 Step 2 (plan :81) is six FAIL lines, not four.**
- **Plan:** "four FAILs — three at `:68-70` … and the new case (`install()` goes straight to the `npx` call: exit 0, no message, a new `$NPX_LOG` line)".
- **Why six:** the case asserts three things (Step 2: exit 1, the stderr line, no new `$NPX_LOG` line). The test's style is one `ok`/`bad` line per assertion (`test-upstream-skills.sh:8-9`; three per value in case (d), `:50-52`).
- **Simulated** under `/tmp/claude-1000/-home-ntdst-Projects-netdust-plugins/f07572ac-69e7-49a9-aa74-73907cf6b5c6/scratchpad/sim4/`, on copies of the main script and test, with TMPDIR set to the scratchpad and nothing written to the repo or the real HOME:
  - **RED:** three `FAIL missing …/wp-abilities-{api,audit,verify}/SKILL.md`, then `FAIL missing at pin: exit 0 (want 1)`, `FAIL missing at pin: stderr:` and `FAIL missing at pin: npx was called`. `:94` passes.
  - **GREEN:** Step 3 applied (the source check before `run npx`, skipped when `$DRY`) and `:94` set to `-eq 7`. Result: `test-upstream-skills: all passed`, with the stub unchanged.
- **Smallest change:** "six FAIL lines — three at `:68-70` (…) and the new case's three assertions (exit 0, no message, a new `$NPX_LOG` line)".

**S2. Three lines still describe the design B1 and N4 replaced.**
- **Task 7 Step 1, netdust-gates changelog (plan :331):** "verified by wp-abilities-verify in runtime mode on a branch that touches routes". The pack line (:149) now gives the run to the task that touches a route an agent will operate, on its own DDEV, and its reviewer reads the quote. Change it to "verified by the task that touches such a route, running wp-abilities-verify in runtime mode on its own DDEV, its reviewer reading the quote".
- **Task 2 Step 5, commit message (plan :170):** "verified by its task and read by the review". "The review" is the headless pass, which is exactly the reader B1 removed. Change it to "read by its reviewer".
- **Test map row 3 (plan :50):** "`<scratch two-case file>`". Task 3 Step 5 runs a one-case file, as Global Constraints bullet 4 says; only the Close's file holds two. Change it to "`<scratch one-case file>`".

## Note

**N1. The reviewer session reads only at checkpoints, so the quote reaches it at the Close.**
- **Plan:** the pack line (:149) says "its reviewer reads the quote there, the way it reads every line's evidence"; Task 3 (:198) says "your reviewer reads it there".
- **Source:**
  - `main:plugins/netdust-gates/skills/policy/SKILL.md:104-105`: "The reviewer reads only the first working version, a block and the Close".
  - `plugins/netdust-core/skills/herdr-orchestration/SKILL.md` recipe item 6: "Review at checkpoints, not tasks … never after every task". Item 7: the coder's final list carries "every `Ruling:` and its deferred minors", not the evidence.
- **Why the claim still holds:** at the Close the reviewer can open the coder's ledger (`.superpowers/sdd/<plan>/progress.md`, which herdr item 8 names). It still exists then, because executing-plans deletes the workspace only after the final review is clean. The pack already works this way (`wordpress.md:10-11`, red flag `:42`).
- **Change:** none required. Optionally, Task 3's sentence could end "your reviewer reads it at the Close".

**N2. A Runtime-only result catches only hand registrations under the route's prefix.**
- **Plan:** Task 3 :198 says "Runtime-only → a hand-registered ability, drift"; spec R16 says the same.
- **Stride, the one real consumer:**
  - Its registrars name `stride/enroll-user` (`Modules/Assistant/WriteAbilityRegistrar.php:37`) and `stride/search-users` (`ReadAbilityRegistrar.php:50`).
  - Its namespace is `stride/v1` (`Modules/Notification/NotificationService.php:60`).
  - The `stride-v1/` filter therefore never lists those 13 registrations, and check 1 reads clean while they exist.
- **Not wrong as written:** the sentence already names check #16 as the bypass finder.
- **Smallest change, if wanted:** "Runtime-only → an ability under the route prefix that no `'ability' =>` declares — drift; a registrar under its own prefix is #16's to find".

**N3. The static inventory grep will need one ruling when it runs.**
- `grep -rn "'ability' =>"` "over the consumer" has no scope. Unlike R5's grep (spec :137), it does not exclude `vendor/` and `tests/`.
- It yields file:line locations, not names. Check 1 compares names, so the session builds `<namespace-slug>/<name>` from each block, using bullet 1's rule.
- It misses a `"ability" =>` or `'ability'=>` spelling, and such a declaration would then read as Runtime-only.
- **Optional:** give it a `<scope>` and R5's exclusions.

**N4. Task 2 uses a sentence Task 3 writes, but runs first.**
- Task 2's Interfaces (:129) consume Task 3 Step 2's third bullet. Between the two commits, the pack cites a framework sentence that does not exist yet.
- This is harmless on one branch that is reviewed whole. Swapping Tasks 2 and 3 removes it; Task 3 needs nothing from Task 2.

**N5. Task 5 Step 1 (:270) drops two small parts of R17.**
- R17 (spec :282-284) names the shared test site as "(the testbed, retiring)" and says "A package worktree is its own DDEV project".
- The problem section's point is that the harness never mentions the testbed. Naming it in the not-used list is what lets a session that finds `~/Sites/ntdst-testbed` know to leave it alone.
- One clause each.

**N6. Simplest design.**
- The paragraph is honest, and its reasons still hold: the policy is 149 lines on main, and the YOOtheme load is 55,738 bytes against the 55,000 limit.
- N2's design, which keeps check 1's Source-only FAIL, is now in.
- No simpler design is left unconsidered.

## Premises checked
- The verify skill defaults to static mode → `eff3785:skills/wp-abilities-verify/SKILL.md:53` → holds (the bullet says runtime mode)
- The skill requires an explicit report path → `SKILL.md:61`, `:152-153` → holds ("your scratchpad")
- The zero-hit stop keys on `wp_register_ability(` → `SKILL.md:66-68`, `:187` → holds (the substitution replaces it)
- Check 1: Source-only is FAIL, Runtime-only is WARN, counts match is OK → `SKILL.md:94-96`; `runtime-harness.md:86-90` → holds. The bullet's PASS is the report's top-line word for an all-OK run (`SKILL.md:179-180`), and its Runtime-only → drift is a stated netdust reading (N2).
- The harness filters on the plugin slug → `runtime-harness.md:75`, `:99` → holds (the substitution is the namespace slug)
- "Plugin is active" uses `--status=active` and halts on "no" → `runtime-harness.md:52`, `:59`, `:63` → holds. `--status=must-use` finds Stride's top-level `stride-coreloader.php` (`~/Sites/stride/web/app/mu-plugins/`) → holds.
- The env-up command is read from AGENTS.md, else ask the user → `runtime-harness.md:24-42` → answered by "on your own DDEV … `ddev wp`" → holds
- `wp-project-triage` is a prerequisite → `SKILL.md:65` → holds
- Runtime mode executes abilities → `SKILL.md:36` → holds
- The pack line is one physical line, 521 characters, with no `specs/` path and no banned grammar → plan :149; `test_artifact_layout.py:7-12`; `test_policy_skill.py:7` → holds
- The pack is 59 lines; `:28` holds `make gate`; `:33-36` is "Local and ship" and has room for the added sentence in four lines; the inserted line makes 60; the test allows ≤ 60 → `main:…/wordpress.md`, `test_policy_skill.py:47` → holds
- The headless review reads code, plan and spec → `feature-review.md:7`, `:25-31`; `test_close_wiring.py:59-61` → holds
- "Its reviewer reads the quote there" → `policy/SKILL.md:104-105`; herdr-orchestration recipe items 6-8 → holds at the Close only (N1)
- The policy is 149 lines; the trigger is at `:68-70`; the 340-character sentence wraps to three lines at 120 characters, the file's widest line (`:134`) → holds
- The two regression cases read `make gate` and `make deploy-test env=staging` → `cases.json` (`wp-feature-constraints`, `wp-constraints-carry-evidence`) → holds
- Pin `eff3785` is the trunk tip; skills CLI 1.7.4; all seven skills exist at the pin → `git ls-remote` and `npm view` run today; `ls-tree` → holds
- Script `:7-9`, `install()` `:15-25`, `--check` loops over the script's own `SKILLS` at `:31` → `bin/wp-upstream-skills.sh` → holds
- Test file: fixture `:15`, install assertions `:68-70`, changed-pin case `:78-86`, count `:94`, stub `:41` unchanged → holds; the RED total → **does not hold** (S1)
- GREEN with the stub unchanged → simulated → holds
- Framework anchors at `:18-19`; "Rest is the one surface" at `:96-115`; last bullet at `:113` → holds
- `version-anchor.sh` reads only `SKILL.md`'s `**name** (X.Y.Z)` lines → `version-anchor.sh:20`, `:45-48` → holds (insertions after `:113`, and edits to `baseline.md`, do not move them)
- "Fails quiet" at `traps.md:7-16`; an unknown option drops the route → `traps.md:16`; `~/Sites/ntdst-core/api/Rest.php:748` (5.4.1) → holds
- The golden path's route at `:213` → `content-type-feature.md:208-214` → holds
- The drift reviewer says "fifteen" at `:3`, "Fifteen" at `:11` and `:275`; #15 at `:597`; the `---` at `:620` → holds
- Check #16 pipeline: Stride 19 raw hits, 17 after the comment filter (11 / 4 / `plugin-config.php` 2); Laika 0 → run read-only today → holds
- Stride's hand registrations use the `stride/` prefix while its namespace is `stride/v1` → `WriteAbilityRegistrar.php:37`, `ReadAbilityRegistrar.php:50`, `NotificationService.php:60` → holds (N2)
- wp-testing `:35` is one physical line and `:91` is item 4; "Playground MAY be the browser" has 1 hit; `require-dev` and `deps:latest` have 0 → holds
- Close 4's grep finds only `wp-testing/SKILL.md:91` on main → `git grep` → holds
- Correctness runner: arguments `[cases] [out]`, reads only `["cases"]`, keeps only cases with `context_after`, prints the PASS / BOTH-CLEAN mark → `run-correctness-eval.sh:16`, `:19`, `:23`, `:131`, `:161` → holds
- `behavioral-lessons.json` has the keys `_readme` and `cases`, and its case keys match what the plan specifies → holds
- Baseline `origin/main` is `v2.21.3` with eleven module keys, four defaulting through `DEFAULT_ENABLED` → `ntdst-baseline.php` → holds
- `baseline.md:1` reads "(2.3.0)", `:17` "Seven modules", the table at `:23-31`, the configuration list at `:36-45` → holds
- netdust-wp `CLAUDE.md` Setup is at `:9-17` → holds
- The cherry-picks `1a2745f` and `4112f4b` touch only `plans/`; `a317d2f` is their ancestor → holds
- `test-live-routing.sh` bans names and stack-template gates; Task 5's text trips neither → holds

_After this review, S1 and S2 were applied, with N1 ("at the Close"), N2 (the Runtime-only wording), N3 (scope and exclusions on the static grep) and N5 (the testbed named, a package worktree its own DDEV project); N4 is noted in Task 2's Interfaces. No finding was Blocking, so this is the review that travels with the plan; the plan's blob after those edits is recorded in Studio feature #4._

---

# Earlier review (superseded by the one above)
Reviewed-plan: 7b46c40874f14fbbd5e3be5c455fd781aa5a156a specs/wp-ai-skills/plan.md
Verdict: not ready

The plan is close. One Blocking finding remains: the verify output ends up where the feature review never looks. The other fixes are one line each.

**What happened to the second review's findings.**
- **Landed as written:** B1 (the verify sentence in Task 3, which the pack line cites), B2 (option b; Decision 17 and the reworded R16 are in the spec), S1 (the script checks the source at the pin, before the add), S2, S4 in Task 7, and N1 to N6.
- **Partly landed:**
  - S3: Task 3 no longer edits `:19`, but Task 6 Step 1 still says it does (S2 below).
  - S4: the Test map still says `marketplace.json ×2` (S2 below).
  - N8: the RED count is still wrong, for a new reason (S1 below).
- **New gap from B2's option (b):** the quote is put where the review never reads it (B1 below).

## Blocking

**B1. The feature review cannot read the quote.**
- **Plan lines:**
  - Task 2 Step 3, the pack line ("the review reads the quote").
  - Task 2 Step 3, line 151: "the pack's evidence rule … already makes the task the runner and the review the reader".
  - Task 3 Step 2, third bullet: "Quote the output in the task report; the review reads it."
- **Where task reports live:**
  - The pack puts evidence "in the task report" (`wordpress.md:10-11`).
  - Task reports sit in `.superpowers/sdd/<plan>/`. That is scratch, "deleted at finish" (`main:…/policy/SKILL.md:32`; `agents/session-reviewer.md:13`, `:19-20`), and it is never committed.
- **What `/feature-review` actually gives its reviewers:**
  - A detached checkout of the head, the plan's requirements, Review Focus and threat model, and the diff (`commands/feature-review.md:25-31`).
  - Commit messages only for a feature with no plan (`:29`), and "a headless subagent may not be allowed to run git" (`:30`).
  - `test_close_wiring.py:59-61` pins this as "code, plan and spec".
  - superpowers' `code-reviewer.md` takes a description, the plan and a range. It never takes a task report.
- **Result:** on a route branch the verify output never reaches the review that R16 and Decision 17 name as its reader, so "No quote, not met" cannot be judged there.
- **Not a free fix:** if the pack named a committed `specs/<feature>/abilities-verify.md`, `test_artifact_layout.py:7-10` would fail. Adding a row to the policy's table would push the policy from 149 lines to 150, and its test requires fewer than 150.
- **Smallest change, one of:**
  - (a) No ruling needed; keeps Decision 17's split between runner and reader.
    - The pack line says "…quotes the output in the task report and in the commit that touches the route — the review reads it there, never runs it…". The Task 3 sentence says the same.
    - `feature-review.md:29` passes the commit messages (`git log --format=%B <base>..<head>`) with the diff whether or not a plan exists. Add that file to Task 2's Files and drop line 151's "stays untouched". The needles at `test_close_wiring.py:55-61` are unaffected.
  - (b) Stefan rules that "the review" means the reviewer session, which reads the coder's task reports while they still exist. The pack line then says "its reviewer reads the quote".

## Should fix

**S1. Task 1 Step 2's expected RED result is wrong; the test itself is right.**
- **Plan:** "Expected: two FAILs — the new case … and the count at `:94` (still `-eq 4` against seven)."
- **Why `:94` passes at RED:** `--check` loops over the script's own `SKILLS` (`bin/wp-upstream-skills.sh:31`), not the fixture's. At RED the script still names four, so 4 = 4.
- **Where the extra FAILs come from:** the fixture `SKILLS` (`:15`) also drives the install assertions at `:68-70`. The unchanged script installs four, so three FAILs appear there: `missing …/wp-abilities-{api,audit,verify}/SKILL.md`.
- **Simulated** on copies of the script and test under `/tmp/claude-1000/-home-ntdst-Projects-netdust-plugins/f07572ac-69e7-49a9-aa74-73907cf6b5c6/scratchpad/sim/`, with TMPDIR set there and nothing written to the repo or the real HOME:
  - RED: those three FAILs plus the new case's (exit 0, no message, npx called). `:94` passes.
  - GREEN: Step 3 applied (the check between `:23` and `:24`, skipped under `--dry-run`) and `:94` set to `-eq 7`. Result: `test-upstream-skills: all passed`, with the stub unchanged.
- **The fixture-revision test can be written against the harness as specified:**
  - `git rm -rq skills/wp-abilities-audit`, commit, and push to `$TMP/upstream.git`.
  - Run with `PIN=<new sha>`, and compare `wc -l < "$NPX_LOG"` before and after.
  - Fetching by sha works the same way as the existing changed-pin case (`:78-86`).
  - The stale copy left by case (a) makes the test fail on a post-add check, so it really tests the source check.
- **Smallest change:** Expected becomes "three FAILs at `:68-70` (the script still installs four) and the new case's; `:94` passes until Step 3".

**S2. Five lines still contradict the fixes they follow.**
- **Task 1 Files** lists "`:41` (the stub's copy loop)", but Step 2 says "The stub `npx` needs no change", and the simulation confirms it. Drop `:41`.
- **Task 6 Step 1, last sentence:** "Task 3's edit of `SKILL.md:19` uses the same count." But Task 3 Files says "line 19's anchor stays as it is". Drop the sentence.
- **Task 7 Step 1, the netdust-wp changelog:** "(a name missing after the add is refused)". Task 1 refuses before the add, at the source (Step 3, and the commit message on plan line 115). Change it to "(a name missing at the pin is refused before the add)".
- **Test map row 7:** "`plugin.json` ×2, `marketplace.json` ×2". There is one file, `.claude-plugin/marketplace.json`. Change it to "`marketplace.json` (both entries)".
- **Task 2 Interfaces:** "Consumes: Task 1's lesson on `wp-abilities-verify`". Task 1 Step 5 itself says the lessons journal is not loaded and the how-to lives in Task 3's sentence, which is what the pack cites ("as `ntdst-framework` reads it"). Change it to "Consumes: Task 3 Step 2's third bullet".

## Note

**N1. Task 3's verify sentence can be followed, but a literal session will need four rulings.**
- The sentence never says "runtime mode", and the skill defaults to static if unspecified (verify `SKILL.md:53`). Add the two words here, where sessions read it.
- Harness Step 1 checks that "The plugin being verified is active" via `wp plugin list --status=active`, and "Any 'no' answer halts the harness" (`runtime-harness.md:52`, `:59`, `:63`). A netdust consumer is an mu-plugin, listed as `must-use`, so that list does not show it. One clause fixes it.
- The skill requires an explicit report path (`SKILL.md:61`, `:150-153`). Name one, for example the scratchpad.
- The namespace filter needs the full ability name, `<namespace-slug>/<name>`. Bullet 1 gives only `name` (`^[a-z0-9-]+$`) and the category, never the full name (R1: `stride-v1/list-registrations`).

**N2. A stronger design than skipping static enumeration.**
- `grep -rn "'ability' =>"` over the consumer gives a static inventory that INV-11 allows.
- Check 1 then keeps "Source-only → FAIL (registration not firing)" (`SKILL.md:94-96`; harness `:86-87`).
- That is the only check that catches Task 3 Step 3's trap ("registers nothing") and a route dropped by a core older than 5.5.0. As written, a missing ability just doesn't appear, in a list with no expected count.
- This contradicts R16's "`Runtime-only → WARN` is the expected shape", so it is Stefan's call.

**N3. The one-gate rule has no check.**
- Global Constraints bullet 1 is a "never" line, but no step greps for it.
- Add one line to the Close: `git grep -n -iE "playground|blueprint|wp-env" -- plugins/netdust-wp/skills plugins/netdust-gates/skills`. After Task 5 the only hits should be `wp-testing/SKILL.md:35` and `:91`; on main the only hit is `:91`.

**N4. "Two-case file" means one case.** Global Constraints bullet 4 and Task 3 Step 5 count `_readme` as a case, but it is a top-level key; the runner reads only `["cases"]` (`run-correctness-eval.sh:23`). Tasks 3 and 5 each run one case; only the Close's file holds two.

**N5. Task 2 Step 1's fallback is already applied.** It says that if the RED run passes, the case "needs a stronger expect (the `composer gate` wording of Step 3)". But Step 4's case already expects `composer gate`, and Step 1 appends Step 4's cases first. If RED still passes, the fix is the prompt or the demo spec.

**N6. Carried over from the last review (N7).** Task 6 sets baseline.md's title to v2.21.3, but its configuration surface (`baseline.md:36-45`) still lists six filters for eleven modules.

**N7. Simplest design.**
- The paragraph is honest, and its reasons hold: the policy is 149 lines on main, and the YOOtheme load is 55,738 bytes against the 55,000 limit.
- Last round's two simpler pieces, the source check and the scratch eval runs, are both in.
- N2 is the only alternative left.

## Premises checked
- Policy is 149 lines on main; trigger at `:68-70`; the new 340-char sentence wraps to three lines at a 120-character width → `main:…/policy/SKILL.md` → holds
- `tests/run.sh` takes a test-file argument → `tests/run.sh:12` → holds
- Pack is 59 lines; `:28` "the close is `make gate`"; `:33-36` "Local and ship"; the test allows ≤ 60; no `specs/` path in the new text → `wordpress.md`, `test_policy_skill.py:47`, `test_artifact_layout.py:7-10` → holds
- Gates eval case shape and allowed keys; case ids chosen from argv; gates and core load from source → `test_evals_shape.py:17-18`, `run-evals.py:34`, `:180`, `:244` → holds
- The two regression cases read `make gate` and `make deploy-test env=staging` → `cases.json` (`wp-feature-constraints`, `wp-constraints-carry-evidence`) → holds
- Pin `eff3785` is the trunk tip; skills CLI 1.7.4 is the latest; all seven SKILL.md files exist at the pin → `git ls-remote`, `npm view`, `git cat-file -e` → holds
- The CLI installs the matched subset and exits 1 only when nothing matches → `cli.mjs:4815-4826` (1.7.4) → holds
- Script `:7-9`, `install()` `:15-25`, the `PIN="${PIN-…}"` form → `bin/wp-upstream-skills.sh` → holds
- Test file references: fixture `:15`, stub `:41`, install assertions `:68-70`, changed-pin case `:78-86`, count `:94` → `test-upstream-skills.sh` → holds
- The fixture-revision test can be written, and passes GREEN with the stub unchanged → simulated in the scratchpad → holds
- Step 2's RED tally ("the count at `:94`" fails) → `bin/wp-upstream-skills.sh:31` with the simulation → **does not hold** (S1)
- The stub needs no change, so Files `:41` is wrong → simulation → holds; Files is stale (S2)
- The zero-hit stop and static enumeration key on `wp_register_ability(`; Runtime-only → WARN; static is the default; a report path is required; the harness filters on the plugin slug; the harness halts on an inactive plugin → verify `SKILL.md:53`, `:61`, `:63-68`, `:81-88`, `:90-96`; `runtime-harness.md:52`, `:59`, `:63`, `:75`, `:99` → holds (the sentence can be followed, N1)
- `wp-project-triage` is required by all three skills; it exists at the pin but is not in `SKILLS` → verify `:65`, audit `:32`, `:42`, api `:20`, `ls-tree` → holds
- `Abilities_Registrar` and its own `wp_register_ability()` calls; the audit's grouping rule; the audit refuses `__return_true` → `plugin-family-patterns.md:34`, `:44`; `shared-core-service.md:109`; audit `SKILL.md:84`, `:181-183` → holds
- The review is headless, on a detached checkout, and runtime mode executes write abilities → `feature-review.md:7`, `:25-27`; verify `SKILL.md:36` → holds
- "The review reads the quote" → `feature-review.md:25-31`, `main:…/policy/SKILL.md:32`, `session-reviewer.md:13`, `:19-20`, `test_close_wiring.py:59-61`, superpowers `code-reviewer.md` → **does not hold** (B1)
- Framework anchors at `:18-19`; "Rest is the one surface" at `:96-115`; last bullet at `:113` → `ntdst-framework/SKILL.md` → holds
- "Fails quiet" at `:7-16`; `:16` an unknown option drops the route; `schema` is a known option → `traps.md`, `~/Sites/ntdst-core/api/Rest.php:748` (5.4.1) → holds
- The golden path's route at `:213` → `content-type-feature.md:208-214` → holds
- `version-anchor.sh` prints two stale lines and exits 1; insertions after `:113` do not move them → run read-only → holds
- Drift reviewer: "fifteen" at `:3`, "Fifteen" at `:11` and `:275`; #15 at `:597`; the `---` at `:620` → holds
- Check #16 pipeline: Stride 19 raw hits, 17 after the comment filter (11 / 4 / `plugin-config.php:54-55`), the comments `SessionService.php:148` and `WriteAbilityRegistrar.php:11` dropped; Laika 0 → run read-only → holds
- wp-testing `:35`, `:91`; `require-dev` and `deps:latest` have 0 hits on main; "Playground MAY be the browser" has 1 → holds
- Correctness runner: arguments, `["cases"]`, the `context_after` filter, the baseline sha, the PASS / BOTH-CLEAN line, writes only the given output path → `run-correctness-eval.sh:16`, `:19`, `:23`, `:131`, `:137`, `:161`, `:168` → holds
- `'ability' =>` has 0 hits at `a317d2f` → holds
- Baseline `origin/main` = `v2.21.3`; eleven modules; four `DEFAULT_ENABLED = false` → `ntdst-baseline.php:66-95`, the four service classes → holds
- `baseline.md:1`, `:17-31`, `:36` → holds
- One marketplace file; the gates version must match → `.claude-plugin/marketplace.json`, `test_plugin_manifest.py:22-24` → holds (the Test map row is stale, S2)
- netdust-wp `CLAUDE.md` Setup at `:9-17` says "four" twice (`:13`, `:16`) → holds
- YOOtheme load is 55,738 on main; the netdust-wp suite does not run the budget → computed; `tests/yootheme/run.sh` → holds
- No `composer.json`, Makefile, `site.yml` or `ARCHITECTURE-INVARIANTS.md` at the root → holds

---

# Earlier review (superseded by the one above)
Reviewed-plan: a0759a44d569f94d2e3a83f0560db5a15ce653d2 specs/wp-ai-skills/plan.md
Verdict: not ready

**Status of the first review's findings.** All of them landed as written: B1–B4, S1–S5 and N1–N12. Three of the proposals were incomplete:
- **B5 (runtime mode):** runtime mode still stops at the skill's zero-hit check. That is B1 below, and B2 is a related gap in the same line.
- **S1 (the script refuses):** the new check is satisfied by a copy an earlier pin left behind. That is S1 below.
- **B4 (eval fields):** the fields are in, but one case's probes cannot tell the two arms apart. That is S2 below.

Coverage of R14, R15 (minus E), R16 and R17 is otherwise complete, and every Test map row has its task. Each fix below is one or two lines of the plan.

## Blocking

**B1. `wp-abilities-verify` still reports "nothing to verify" in runtime mode.** Plan lines: Task 1 Step 5, third lesson bullet; Task 2 Step 3, the pack line.
- In `~/.cache/netdust/wp-upstream-skills` at `eff3785`, the zero-hit stop applies in both modes:
  - `skills/wp-abilities-verify/SKILL.md:63-68` (Prerequisites, no mode qualifier): "The plugin has at least one registered ability in source. Zero hits on `wp_register_ability(` → return a clear 'no abilities registered' report".
  - `:187` (Failure modes): "No abilities in source — return a clear 'nothing to verify' report."
  - Runtime mode "does everything static does PLUS" (`:34`; `references/runtime-harness.md:3`).
- Runtime enumeration filters names on `strpos($n, "<plugin-slug>/")` (`runtime-harness.md:75`, `:99`). A route ability is named by its namespace (`stride-v1/…`, spec R1), so a filter on the plugin slug counts 0.
- All three skills require `wp-project-triage` first (verify `SKILL.md:65`, audit `SKILL.md:42`, api `SKILL.md:20`). It is not in `SKILLS`.
- Result: on a consumer that follows INV-11, runtime mode returns the same empty answer as static mode, which is the original B5.
- The lesson also lands in `ntdst-framework/lessons.md`, which no SKILL.md loads.
- Smallest change:
  - Task 3's third bullet (SKILL.md, which sessions do load) gets one sentence: on a netdust consumer, skip the zero-hit stop and the static enumeration; enumerate `wp_get_abilities()` over `ddev wp`, filtered on the namespace prefix (`stride-v1/`); every route ability is `Runtime-only → WARN` by design; triage is not installed, and `site.yml` / the composer type stand in for it.
  - The pack line then cites that ("…in runtime mode as `netdust-wp:ntdst-framework` reads it…"). The pack's own header says to cite, never restate.

**B2. The pack line names an owner that never runs the skill.** Plan line: Task 2 Step 3, "on a branch that touches routes the feature review runs the upstream `wp-abilities-verify` skill in runtime mode on the branch's DDEV … and quotes the result".
- `plugins/netdust-gates/commands/feature-review.md` cannot do this:
  - `:7`: "You change nothing and ask nothing — this runs headless".
  - `:25-27`: reviewers read a `git worktree add --detach` checkout, which has no DDEV project.
  - `:31-36`: it dispatches exactly four reviewers (superpowers' reviewer, `security-sentinel`, `invariant-auditor`, the drift reviewer).
  - Runtime mode "executes each ability with curated inputs" (verify `SKILL.md:36`), write abilities included.
- No task touches `feature-review.md`. So R16's "runs in the feature review" has no task. Under the pack's "No quote, not met", every route branch would carry a line nobody can meet.
- Smallest change, one of:
  - (a) Task 2 adds one dispatch line at `feature-review.md:36`, naming the DDEV it runs on (the coder's worktree project).
  - (b) The pack line gives the run to the task that touches the route, on the coder's own DDEV, and the review reads the quoted output. This rewords R16, so Stefan rules on it.

## Should fix

**S1. The "Empty" refusal passes on a stale copy, and its test either never goes green or proves the stub.** Plan lines: Task 1 Steps 2–3; Review Focus "Empty".
- What the real CLI does (skills 1.7.4, `package/dist/cli.mjs` from the registry tarball, unpacked at `/tmp/claude-1000/-home-ntdst-Projects-netdust-plugins/f07572ac-69e7-49a9-aa74-73907cf6b5c6/scratchpad/skills174/package/dist/cli.mjs`):
  - `:4820-4826` installs the matched subset and touches no name it did not match.
  - `:2230` `cleanAndCreateDirectory` replaces only the skills it installs.
- So the post-add check (`$HOME/.claude/skills/$s/SKILL.md` exists) passes whenever an earlier pin installed that name. That is exactly the pin-bump case this plan is: a skill dropped or renamed upstream.
- The new test runs after case (c). At that point `$HOME` still holds `wp-abilities-audit` from case (a) (`test-upstream-skills.sh:64-70`). Two ways to place the stub's `continue`:
  - Before the stub's `rm -rf`, which is how the real CLI behaves: Step 3 never turns GREEN.
  - Between the `rm -rf` and the `cp`: the stub deletes a copy the CLI would keep, so the test proves the stub again.
- Smallest change: check the source at the pin instead, after the checkout and before the add: `[ -f "$CLONE/skills/$s/SKILL.md" ] || { echo "missing at pin: $s" >&2; exit 1; }`, skipped under `--dry-run`.
  - The test commits and pushes a fixture revision without `wp-abilities-audit`, then runs at that PIN with the old copy still in `$HOME`.
  - It asserts exit 1, the message, and no new line in `$NPX_LOG`.
  - The stub needs no change.

**S2. `package-gate-not-playground` cannot discriminate.** Plan line: Task 5 Step 3.
- Its `must_contain` items, `composer gate` and `tests/Integration`, are already in the baseline arm's context (main `wp-testing/SKILL.md:3`, `:35`, `:40`, `:70`).
- `must_not_contain` is probed only inside code fences (`run-correctness-eval.sh:110-112`). Main names Playground and Blueprint only for the shake-out browser (`:91`), never for tests.
- So the baseline arm is very likely clean, and the result line reads `BOTH-CLEAN` (`:161`), not the expected PASS.
- Smallest change: add `require-dev` and `deps:latest` to `must_contain`. Main's wp-testing has 0 hits for each; Task 5 Step 1's new sentence carries both.

**S3. Task 3 lists an edit that no step makes.** Plan line: Task 3 Files, `SKILL.md:19` "seven modules" → "the count Task 6 reads from source".
- No step in Task 3 edits `:19`, and Task 6 runs after Task 3.
- R15 asks for the corrected count only in `references/baseline.md`.
- `:19` is the anchor line `**ntdst-baseline** (2.3.0)`, which the plan deliberately leaves stale (Global Constraints, bullet 7). Writing eleven there makes it read "2.3.0 — eleven modules", but 2.3.0 had seven.
- Smallest change: drop `:19` from Task 3's Files. Or move the edit into Task 6 Step 1 as "eleven on 2.21.3", with `SKILL.md` added to Task 6's Files and its `git add`.

**S4. Task 7 names two marketplace files; there is one.** Plan lines: Task 7 Files and Step 3.
- `git ls-tree -r main` shows one file, `.claude-plugin/marketplace.json`, with entries for both plugins. The plan's own grep lists it plus the two `plugin.json` files.
- `plugins/*/.claude-plugin/marketplace.json` matches nothing. An unmatched pathspec makes `git add` abort with "did not match any files", so nothing is staged.
- Smallest change: Files becomes "`.claude-plugin/marketplace.json` (both entries)", and the `git add` names the three real paths.

## Note

- **N1. Stride counts (Task 4 Step 2).** The check's pipeline finds 19 raw hits and 17 after the comment filter:
  - 11 in `ReadAbilityRegistrar.php`, 4 in `WriteAbilityRegistrar.php`, 2 in `plugin-config.php:54-55`.
  - Filtered as comments: `SessionService.php:148` and `WriteAbilityRegistrar.php:11`.
  - Laika: 0.
  - Expected should state 17 / 0 and name `plugin-config.php`, since the Then step calls those hits drift too.
- **N2. The correctness runner runs in full three times** (Task 3 Step 5, Task 5 Step 3, Close 1): 28 runnable cases, two answers and a judge call each. The runner takes `[cases.json] [out.json]` (`run-correctness-eval.sh:16`, `:19`). A two-case file and a scratch output path would run only the new ids and leave the tracked `evals/outputs/correctness-results.json` alone. This is a simpler design the plan did not consider.
- **N3. Regression ids.** Lines 28 and 33–36 of the pack are what `wp-feature-constraints` (`make gate`) and `wp-constraints-carry-evidence` (`make deploy-test env=staging`) read. Add both ids to Task 2 Step 4 and Close 1. Step 1's RED run could include `wp-route-declares-ability` too.
- **N4. The Boundary count is never printed.** `test_policy_skill.py:47-48` prints no number. Add `wc -l plugins/netdust-gates/skills/policy/wordpress.md` → 60 to Task 2 Step 3's Expected, since Review Focus "Boundary" says the count is what gets read.
- **N5. (5.5.0) marks.** Task 3 Step 2 says each bullet is marked `(5.5.0)`, but as written only the first one is.
- **N6. No eval for the drift check.** Global Constraints bullet 3 says behaviour-changing text ships an eval; Task 4 ships a grep instead, which the Architecture line states. `drift-part1-honesty` in `behavioral-lessons.json` already shows an agent case in the same shape. Either add one or scope the bullet to skills.
- **N7. baseline.md's title.** Task 6 sets the title to v2.21.3, but the configuration surface (`baseline.md:36-45`) still lists six filters. R15 asks only for the module count.
- **N8. Task 1 Step 2's RED run.** With the fixture at seven names and `:94` still `-eq 4`, the run shows two FAILs, not one.
- **N9. Simplest design.** The paragraph is honest now, and its reasons hold: the policy is 149 lines on main, and the YOOtheme load is 55,738 against 55,000. The simpler pieces it did not consider are S1's source check and N2's filtered run.
- **N10. The trigger rewrap is tight.** The new sentence is 340 characters, so three lines need about 115–120 characters each. The widest body line today is 120 (`SKILL.md:134`). It holds, and there is no width test.

## Premises checked
- Policy is 149 lines on main; trigger at `:68-70`, three lines → `main:…/policy/SKILL.md` → holds (rewrap fits narrowly, N10)
- Step 1's runner call with a test-file argument → `tests/run.sh:12` → holds
- Pack is 59 lines; `:28` "the close is `make gate`"; `:33-36` "Local and ship"; test allows ≤ 60 → `wordpress.md`, `test_policy_skill.py:47` → holds; both edits fit on their existing lines
- Gates case shape and keys; ids chosen from argv; the "plan" target reads `specs/**/plan.md` → `test_evals_shape.py:18`, `:252-254`; `run-evals.py:72`, `:244` → holds
- Pin `eff3785` is the trunk tip; the three abilities skills exist at it → `git ls-remote`, `ls-tree` → holds
- skills CLI 1.7.4 is the latest; same flags; installs the matched subset and exits 0 → registry, `cli.mjs:4820-4826`, `:5942-5977` → holds
- A changed pin replaces rather than merges (Delivery seam) → `cli.mjs:2230` → holds
- The post-add check catches a name missing at the pin → `cli.mjs:4820-4826` with the stale copy from `test-upstream-skills.sh:64-70` → **does not hold** (S1)
- Fixture `:15`, stub `:41`, count `:94`, the `PIN="${PIN-…}"` form at `:7` → holds
- `Abilities_Registrar` at `plugin-family-patterns.md:34` and `shared-core-service.md:109`; audit refuses `__return_true` (`:181-183`); audit's grouping rule (`:84-89`) → holds
- Runtime mode gets past the zero-hit stop → verify `SKILL.md:63-68`, `:187`, `runtime-harness.md:3`, `:75` → **does not hold** (B1)
- The feature review runs the verify skill → `feature-review.md:7`, `:25-27`, `:31-36` → **does not hold** (B2)
- The pin bump leaves netdust-wp's citations valid → upstream diff `d87ee69..eff3785`: only `wp-plugin-development/references/security.md` changed, and the `wp-security/SKILL.md:26` citation still resolves → holds
- `version-anchor.sh` prints `:18` (5.2.0) and `:19` (2.3.0) and exits 1; line numbers unaffected by insertions after `:113` → run read-only → holds
- `ntdst-framework/SKILL.md:19` "seven modules"; `:96-115` the Rest section; `:113` last bullet → holds; the `:19` edit has no step (S3)
- `traps.md:7-16` "Fails quiet"; `:16` unknown option drops the route → holds; `api/Rest.php:748` known options (5.4.1) → holds
- Golden path's route at `content-type-feature.md:213` → holds
- Correctness runner: `context_after` filter, `baseline_ref.split()[0]`, must probes, writes the tracked outputs file → `run-correctness-eval.sh:131`, `:137`, `:110-115`, `:168`; `git ls-files` → holds
- The testing case discriminates → baseline `wp-testing/SKILL.md:3`, `:35`, `:40`, `:70` already contain both `must_contain` tokens → **does not hold** (S2)
- The framework case discriminates (`'ability'` absent at `a317d2f`) → holds
- WordPress facts: lazy `wp_abilities_api_init` → Stride WP 7.1 `class-wp-abilities-registry.php:283`, `:313`; `abilities-api.php:291` → holds
- Drift reviewer `:3`, `:11`, `:275` "fifteen"; `:620` the `---` before Output format → holds
- Check #16 pipeline: Stride 17 after the filter, both comments dropped; Laika 0 → holds (N1)
- Baseline `origin/main` = `v2.21.3`, eleven modules, four `DEFAULT_ENABLED = false` → `ntdst-baseline.php:66-95`, the four service classes → holds
- `baseline.md:1`, `:17`, `:23-31` → holds
- Only live mention of Playground is `wp-testing/SKILL.md:91` → `git grep` → holds
- Two `marketplace.json` files → one file, `.claude-plugin/marketplace.json` → **does not hold** (S4)
- `test_plugin_manifest.py` checks the gates version against the marketplace entry → `:22-24` → holds
- YOOtheme load is 55,738 on main → computed from main → holds
- Cherry-picks `1a2745f` and `4112f4b` touch only `plans/` → holds
- No Makefile, `site.yml` or `ARCHITECTURE-INVARIANTS.md`; `/feature-review` exists → holds
- `claude`, `php`, `npx` present for the evals and suites → holds

---

# Earlier review (superseded by the one above)

Reviewed-plan: 02d537a417b89afd4422009a72dde0d16543a7d7 specs/wp-ai-skills/plan.md
Verdict: not ready

Coverage is complete. Each of R14–R17 and Decision 8 has a task, and each Test map row has a task. Five premises are false in source, and each needs only a small fix. Three of them are reds the plan never ran: the policy runner, which is green on the plan's own base, `version-anchor.sh` and `yootheme-budget.sh`. The other two: the eval runner skips the case shape the plan specifies, and the upstream verify skill cannot see a route-option ability.

## Blocking

**B1. The base: policy runner and Task 1 edits 3–4.** Plan lines affected: the Branch line, First working version, and Task 1 Steps 1–2.
- The plan cuts from `main` and leaves `59f6785` on the ccr branch. But `59f6785` is the commit that adds the three lines.
- `git show main:plugins/netdust-gates/skills/policy/SKILL.md | wc -l` gives 149, so `test_policy_skill.py` passes on main.
- `git diff main HEAD` shows the +3 lines:
  - the standing-OK clause in Stops (HEAD :114–117);
  - ", or run under his standing OK…" in Close 5 (HEAD :145–146).
- On main, "a review finding about intent;" already ends line 114. The Close-5 phrase does not exist. Stops grants no standing OK.
- So on main, Step 1's expected `FAIL … (got 152)` is wrong, edits 3 and 4 have nothing to edit, and edit 4's justification ("Stops 114–116 already grants it") is false. The spec's Constraints entry carries the same false premise.
- Smallest change: keep `main`.
  - Step 1 expects `pass policy: under 150 lines (got 149)`.
  - Drop edits 3 and 4.
  - Widen the trigger inside its three lines (149, no trim needed), or keep edit 2 to make room (148).
  - Task 2 can then be first.
  - Add one line: when `59f6785` lands (+3) it needs its own trim.
- The alternative is to cherry-pick `59f6785` too. Task 1 then stands as written, but the branch carries an unrelated devops feature.

**B2. `version-anchor.sh` already exits 1.** Plan lines affected: Global Constraints bullet 7, Task 3 Step 4, Task 6 Step 3, rows 3 and 7.
- Run today, it prints:
  - `SKILL.md:18: anchors ntdst-core 5.2.0, but ntdst-core ships 5.4.1`
  - `:19: anchors ntdst-baseline 2.3.0, but ntdst-baseline ships 2.16.0`
- The second line comes from `~/Sites/ntdst-baseline`, which is on `feature/seo-archives-og`; origin/main is 2.21.3.
- So "exits 0 or 2 — never 1" fails before any edit, "never goes from 0 to 1" checks nothing, and "stays at the version that shipped" is untrue.
- Smallest change: expect the same two stale-anchor lines before and after each edit, with no new line. Diff the output, not the exit code. Re-anchoring is not in this spec.

**B3. `yootheme-budget.sh` is over budget on main.** Plan lines affected: Task 7 Step 2, row 8.
- `yootheme-budget.sh:19-20` caps the page-build load at 55,000 bytes.
- On main the load is 6401 + 6175 + 13365 + 14016 + 15781 = 55,738, so the script prints `OVER`. In the planning tree, with the uncommitted lessons.md change, it is 56,481.
- The plan read only workflow.md's own 9,000 ceiling. But workflow.md is part of the load, and Task 7 adds up to eight lines to it plus a lessons.md line.
- Smallest change: decide in the plan now. Either Task 7 moves at least 738 bytes plus its own additions out of the five load files, or Stefan rules on the 55,000 ceiling. Expected should quote the `page-build load` line.

**B4. The netdust-wp eval cases would never run.** Plan lines affected: Task 3 Step 4, Task 5 Step 3, rows 3 and 5, Close 1.
- `run-correctness-eval.sh:130` keeps only cases with `context_after` (`runnable=[c for c in cases if "context_after" in c]`).
- `:135` loads the baseline arm from `baseline_ref`. Without one, both arms read the new text, so a case can never discriminate.
- `:101-115` probes `must_contain` / `must_not_contain`.
- The two cases as specified carry none of these fields, so they are skipped and "the case passes" cannot be observed.
- The runner also takes no case filter: it runs all 26 runnable cases × 2 arms + a judge. And it rewrites the tracked `evals/outputs/correctness-results.json`.
- Smallest change: add these fields to both cases:
  - `baseline_ref`: the branch base, main `a317d2f`.
  - `context_before` / `context_after`: `skills/ntdst-framework/SKILL.md` + `references/traps.md` for the framework case; `skills/wp-testing/SKILL.md` for the testing case.
  - `must_contain`: e.g. `'ability'`, `ntdst_rest(` / `composer gate`, `tests/Integration`.
  - `must_not_contain`: `wp_register_ability(` / `Blueprint`, `wp-env`.
  - Expected names the two ids' result lines; the outputs file is not committed.

**B5. The pack line asks for a `wp-abilities-verify` result that is empty by construction.** Plan lines affected: Task 1 Step 3, eval `wp-route-declares-ability`, Task 2 Step 5.
- In `~/.cache/netdust/wp-upstream-skills` at `eff3785`, `skills/wp-abilities-verify/SKILL.md`:
  - Static mode is the default ("Default to static if unspecified").
  - Its Prerequisites say: "Zero hits on `wp_register_ability(` → return a clear 'no abilities registered' report".
  - Step 2 enumerates by grepping `wp_register_ability(`.
  - Step 4 reads the registered execute-callback body.
- Under INV-11 a consumer has no such call (Task 4 makes one drift), and core's execute callback is a dispatcher, not the route handler.
- Every WordPress plan copies this line verbatim, so every branch that touches routes would quote "nothing to verify".
- Runtime mode does work: step 3 enumerates through `wp_get_abilities()` over wp-cli, and `references/runtime-harness.md` Step 0 takes the env command from AGENTS.md, so `ddev wp` serves.
- Smallest change, still one physical line: "…runs `wp-abilities-verify` in runtime mode on the branch's DDEV (`ddev wp`), its annotation check read against the route's handler…".
- Task 2 Step 5's lesson should also record two things: static mode is blind on a netdust consumer, and `Runtime-only → WARN (dynamic registration path)` is the expected shape for a route-option ability.

## Should fix

**S1. Task 2's denial test proves the stub, not the script** (Steps 2–3, Review Focus "Empty").
- In `test-upstream-skills.sh:41` the stub's loop exits with the status of the last `cp`. The test goes red only because the omitted `wp-abilities-verify` is the last name; omit the fifth name and the stub exits 0.
- The real CLI does not refuse. In the cached skills 1.5.18, `~/.npm/_npx/ac0ed6aa23b37c1e/node_modules/skills/dist/cli.mjs:955-962` (`filterSkills`) with `:3877-3885` installs the matched subset and exits 0. It exits 1 only when nothing matches.
- Step 4's real install has all seven skills present, so the plan's "If the real npx … does not exit non-zero" is never observed.
- Smallest change:
  - Make the check in `install()` unconditional: after the add, each `$HOME/.claude/skills/$s/SKILL.md` must exist, else exit 1 naming the missing one.
  - Make the stub skip a missing source (`[ -d "$src/skills/$n" ] || continue`), as the real CLI does.

**S2. The golden-path `ability` example removes the route on today's core** (Task 3 Step 3, also Steps 1–2).
- `~/Sites/ntdst-core/api/Rest.php:748-755` (5.4.1) refuses the whole route on any option outside `OWN` + `args`/`schema`/`show_in_index`/`allow_batch`. `traps.md:16` says the same.
- Every site is on core ≤ 5.4.1 (spec non-goal: no fleet rollout). The golden path is the copy-paste exemplar, so copying it today yields a route that "reviews as protected and 404s on the wire".
- Smallest change: mark the block "(core 5.5.0+)". Add to Step 1's first bullet, or to the trap: "on core < 5.5.0 `ability` is an unknown option and the route is not registered at all".

**S3. Task 4 leaves "Fifteen" in two places.** `ntdst-drift-reviewer.md:11` ("Fifteen checks about things core's own invariants cannot see") and `:275` ("Fifteen checks, in this order.") would still say fifteen while `:3` says sixteen. Add both lines to Files.

**S4. A package plan would copy pack lines it cannot meet** (Task 1 trigger + pack).
- With the new trigger, a package plan copies `wordpress.md:28` ("the close is `make gate`") and `:33-36` (Makefile, `deploy.payload`, `make deploy-test env=staging`) verbatim.
- Spec Constraints: "their gate is `composer gate` and the review is `/feature-review`".
- The `wp-pack-on-muplugin-package` eval locks this in, and plans 3–6 inherit it.
- Smallest change: reword those two lines in place, still 60 lines (e.g. "`make gate` (a package: `composer gate`)", "a package ships by tag, no payload"). Or have Stefan rule on it now.

**S5. Task 8 Step 2 runs `scripts/sync.sh` before review.**
- `scripts/sync.sh:87-115` mirrors every `plugins/*/` from the working tree into the live install caches with `rsync -a --delete`. Its header (`:20`) says to run it AFTER `git push`.
- In Task 8 it would put unreviewed branch text into every session on the box, including the reviewer's, before Close 2–5 and before Stefan's merge.
- Smallest change: move it after the merge, or out of the plan. Step 2 becomes the two suites only.

## Note

- **N1. Task 1 edit 1 says "same two lines".** The trigger is three lines (`SKILL.md:68-70`). Simulated on HEAD, "149" holds only if it grows to four; at three it is 148.
- **N2. Edit 2 is a real dedupe, but the Review Focus overclaims.** The rule is owned by `threat-modeling/SKILL.md:8`. But `## Threat model` is not a needle in `test_policy_skill.py`, so "Mid-flow"'s claim that the needles pin every Netdust addition is too strong. The existing `security-surface-review-focus` eval is that sentence's behavioural pin; if edit 2 stays, run that eval.
- **N3. Task 2 file references.** The fixture `SKILLS` is `test-upstream-skills.sh:15`, not `:16`. "four dirs land" (`:64`) is a comment; the only count assertion is `:94`. Keep the `PIN="${PIN-…}"` form at `bin/wp-upstream-skills.sh:7` — the test overrides through it.
- **N4. The Task 2 lesson credits the registrar class to the wrong skill.** `Abilities_Registrar` is in `wp-abilities-api/references/plugin-family-patterns.md:34` and `shared-core-service.md:109`. The audit skill writes an audit doc of ability shapes, each with a REST `backing`. Its step 4 grouping rule ("Do NOT atomize one ability per HTTP method… collapsing N variants into 1") contradicts one ability per route; name that in the lesson.
- **N5. The trap cites a test name plan 3 has not chosen.** `NtdstRestAbilityTest.php` fits core's naming, but the spec leaves test names to the builder. Cite "core's 5.5.0 unit tests" instead.
- **N6. Check #16 flags a comment.** Stride gives 19 hits, including a docblock (`Modules/Edition/SessionService.php:148`), which "every hit outside api/Rest.php is drift" would flag. Add R5's comment filter (`grep -vE "^[^:]+:[0-9]+: *(\*|//|/\*)"`) to the Then step.
- **N7. Module defaults are constants.** On origin/main, yootheme, polylang, duplicate and grants default through `DEFAULT_ENABLED` constants (`ntdst-baseline.php:83-93`); read each service class for the value. Origin/main has 11 modules, not the spec's ten; the plan rightly counts from source. `ntdst-framework/SKILL.md:19` also says "seven modules", and Task 3 edits that file anyway.
- **N8. No sources heading in yootheme lessons.md.** There is no "sources/verification" heading (§5 Verification is about page checks). Name the intro at `lessons.md:3`.
- **N9. Task 5 states plan 2's work as present.** It describes `deps:latest` and the package shape, which plan 2 (wp-starter) delivers. Mark them the way Task 3 marks 5.5.0.
- **N10. Simplest design.**
  - The rejected alternative (Task 2 alone) does not meet the plan's own scope, because R15–R17 are approved requirements.
  - The stated reason for Task 1 ("a pre-existing red") is false on main.
  - A simpler design the plan did not consider: on main, widen the trigger within its three lines and trim nothing.
- **N11. The gates eval cases have no RED-first run.** A model may read `wordpress-muplugin` as WordPress even under the old trigger. Run `wp-pack-on-muplugin-package` once against main's policy to show it discriminates.
- **N12. Task 2 Step 4 changes the live skills before review.** It writes `~/.claude/skills` (the four re-copied at the new pin, plus three new ones). That is the script's purpose, but it happens ahead of the review.

## Premises checked
- Policy at 152, red on main → `main:…/policy/SKILL.md` is 149 lines; 152 only at HEAD via `59f6785` → **does not hold**
- Intake (46–49) and "The spec" (59–62) as quoted → `SKILL.md:46-49`, `:59-62`, same on main → holds; dedupe backed by `threat-modeling/SKILL.md:8` → holds
- Trigger at 68–70 is "two lines" → `SKILL.md:68-70` is three lines → partly
- Lines 116–117 / 144–146 and "Stops 114–116 grants it" → present at HEAD only; main `:114`, `:142-143` → **does not hold on main**
- Result 149, needles intact → simulated on HEAD (four-line trigger): 149; every `test_policy_skill.py` and `test_close_wiring.py` needle present → holds on HEAD
- Pack at 59; insert after `:36` → 60; test allows ≤ 60 → `wordpress.md:33-36`, `test_policy_skill.py:47` → holds
- Budget test is `< 150`; `BANNED_GRAMMAR` absent from the new text → `test_policy_skill.py:43`, `:7` → holds
- Gates case shape; runner selects case ids from argv → `cases.json` (`wp-constraints-carry-evidence`), `run-evals.py:243-244` → holds
- PIN / CLI / SKILLS at `bin/wp-upstream-skills.sh:7-9` → holds
- Fixture `SKILLS` at test `:16`; two count assertions → `:15`; only `:94` is a count → minor miss
- Stub `cp` fails on the missing name → `test-upstream-skills.sh:41`, red only when that name is last → narrowly holds; "the real CLI must refuse" → `cli.mjs:955-962`, `:3877-3885` (1.5.18) → **does not hold**
- `eff3785` fetched; the three abilities skills present → `ls-tree` → holds
- Audit skill refuses `__return_true` → `wp-abilities-audit/SKILL.md` Failure modes → holds; audit proposes the registrar class → it is in `wp-abilities-api/references/plugin-family-patterns.md:34` → **does not hold**
- `wp-abilities-verify` gives evidence on a route-option consumer → `wp-abilities-verify/SKILL.md` Prerequisites, step 2 → **does not hold** (static mode)
- WordPress facts in the Task 3 text → Stride WP 7.1: `class-wp-abilities-registry.php:283-313` (lazy, after `init`), `abilities-api.php:291`, `class-wp-ability.php:370` (`public` seeds `show_in_rest`) → holds
- "Rest is the one surface" at 96–115; bullets after 113 → `ntdst-framework/SKILL.md:96-115` → holds
- "Fails quiet" at `traps.md:7-16` → holds
- Golden-path route at 213 → `content-type-feature.md:208-214` → holds; `schema` is a known option → `api/Rest.php:748` → holds; `ability` on core ≤ 5.4.1 → `api/Rest.php:748-755` refuses the route → consequence, see S2
- Netdust-wp eval runs as specified → `run-correctness-eval.sh:130`, `:135` → **does not hold**
- Discriminators: `'ability' =>` is 0 today; "Playground MAY be the browser" is 1 (`wp-testing/SKILL.md:91`) → holds
- wp-testing `:35` and `:91` as described → holds
- `version-anchor.sh` exits 0 or 2 → exits 1 today → **does not hold**
- Drift reviewer `:3` "fifteen", `:620` the `---` before Output format → holds; `:11`, `:275` "Fifteen" not in Files → incomplete
- Check #16 grep: Stride ≥ 2 → 19 hits; Laika 0 → 0 → holds
- `baseline.md:1`, `:17`, `:23-31` → holds; origin/main: 11 module keys (`ntdst-baseline.php:67-93`), tag `v2.21.3` → holds
- workflow.md §0 ends at `:20`, "## 1." at `:22`; `sections/hero-text.json` exists → holds
- workflow.md 6175 ≤ 9000 → holds; whole-load budget "within budget" → 55,738 > 55,000 on main → **does not hold**
- Manifests: `plugin.json` ×2 + `marketplace.json` ×2; versions must match → `test_plugin_manifest.py:24` → holds
- `tests/run.sh` suites → `tests/run.sh:6`; upstream-skills and live-routing tests green today → holds
- `sync.sh` updates both caches → `sync.sh:87-115` (live caches, `--delete`), header `:20` "after git push" → mechanism holds, timing conflicts (S5)
- No Makefile / `site.yml` / `ARCHITECTURE-INVARIANTS.md`; `/feature-review` exists → holds
- ntdst-core and ntdst-baseline are `wordpress-muplugin` → `composer.json:4` in both → holds
- Cherry-picks `1a2745f` and `4112f4b` touch only `plans/` → apply without `59f6785` → holds
