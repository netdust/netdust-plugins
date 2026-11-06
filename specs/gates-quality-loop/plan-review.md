# Plan review — gates-quality-loop (plan 1: netdust-plugins), round 2
Reviewed-plan: eec0b41d0c4d979bd9e6a5258e2d0994645cc4d3 /home/ntdst/Projects/netdust-plugins/specs/gates-quality-loop/plan.md
Verdict: not ready

Round 1 (1 Blocking, 13 Should fix; in git at 15fd88e) is replaced by this round. Round 1's Blocking (no machine-readable test per row) is answered: the `Test:` marker parses beside `Browser:` in either order, `Accepted-by-human:` still matches, the credential scan does not fire on ordinary spec paths. 12 of the 13 Should fix hold against source.

## Blocking

B1 — The row's key is the test FILE, and files are shared by rows in every real registry: `~/Sites/laika/specs/CHECKS.md` has five `e2e` rows on `tests/E2E/productions.spec.ts`, `doorverwijsgids-build` nine on `app.spec.ts`, `daan` two on `pages-from-home.spec.ts`; `shakeout-qa.md:116-117` ("never add a second row") and `:52` describe that shape. As written: a feature re-driving laika's productions writes five rows with one `Test:` and `test_two_rows_cannot_share_one_log` refuses a correct manifest; a new test added to a file registered only under an older feature is "re-driven" and never proven, the opposite of R2; "its row" is undefined. Smallest change: `Test: <path> :: <title>`, the stem slugged from both, `revert-run` running that one test; uniqueness for new rows only; "a test file named by any registry row whose first feature is this feature, or by none, is new"; re-driven rows may share a file.

## Should fix

S1 the policy does not fit under 150 lines with the cuts named (148 with three over width, about 151 wrapped): name the Execution-mode cut (13 → 9) or two more lines (the duplicate sentence in `:85-91`, the `commands.gate` explanation). S2 the yield's content (`commands/shakeout.md:67-72`: accepted rows reviewed, the hunt's `not ours:`/`rejected:` overruled) and its pins (`test_close_wiring.py:72-73`) were dropped, not moved; `:74-79` contradicts steps 5-9. S3 R7's per-slice loop has no prompt home. S4 `feature-report.py`'s two joins (Test map row → task; flow → manifest row) are unnamed. S5 an untracked file at a branch-deleted path is overwritten then deleted; the second restore needs a tolerated `git rm`; a typechange `T` is unhandled. S6 "one fix round" restates a cap outside the policy. S7 Task 6 Step 3's prompt edits have no pin.

## Note

`ACCEPTED` is greedy (put `Test:` first); `CREDENTIAL` fires on `app-password.spec.ts`; the trial labels depart from the spec's `revert-fails` (say why); `## Risk model` is not an owned section (call it Threat model); name the agent's path `~/.claude/plugins/netdust-gates/bin/revert-run`; registry `test` cells may be backticked; `git cat-file -e <base>:<path>` is an exact alternative signal; `test_stop_hook_dedup` already fails on this branch (unrelated); Task 5 fits the harness.

## The cut

Holds as in round 1.

## Applied after the review (by the planning session, not the reviewer)

Two rounds is the policy's cap, so no third review ran; the plan goes to Stefan with this report. The plan's blob moved from `eec0b41d0c4d979bd9e6a5258e2d0994645cc4d3` to `9774f26c73bbc026e14bd7cf71c5b88cb685201a`. Every finding was applied:

- B1: `Test: <path> :: <title>`, written first in Evidence; the stem from path and slugged title; uniqueness for new rows only, re-driven rows may share a file; new = the file named by a registry row of this feature, or by none; `revert-run` takes the title and the agent passes a command running that one test. Tests: `test_two_new_rows_cannot_share_one_key`, `test_redriven_rows_may_share_a_file`, `test_new_test_in_an_older_file_needs_its_proof`.
- S1: the Execution-mode paragraph 13 → 9 lines, plus the duplicate sentence and the `commands.gate` explanation; the coder quotes `wc -l`.
- S2: step 8 carries the accepted rows and the hunt lines; the report lists them; `commands/shakeout.md`'s tail points at steps 5-9; the pins move with the text.
- S3: the per-slice line in the Close and the two-line slice rule, `Slice` pinned.
- S4: both joins named (the Unit text in a task heading; the flow name in the manifest's `Flow` cell); a mismatch is a named gap.
- S5: refusal on an untracked file at a deleted path; `--ignore-unmatch` on the `D` restore; `T` treated as `M`.
- S6: "the policy's fix round, then its stop".
- S7: the reviewer prompts, pack, `CLAUDE.md` and `plan-reviewer.md` tokens pinned in Test map row 4.
- Notes: `Test:` first; the scan skips the `Test:` value; the trial-label departure stated; Threat model; the agent's path; backticks stripped; `test_stop_hook_dedup` named as pre-existing. Not taken: the `git cat-file` signal (the registry rule with the title key answers B1 without it).
