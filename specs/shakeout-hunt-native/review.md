# Branch review — shakeout-hunt-native

Range: 5a16263..5afaf0d (feature/shakeout-hunt-native, 1 commit, 9 files)
Reviewer: a fresh, read-only whole-branch reviewer, 2026-10-20. No plan (a bounded change approved
in chat: "i thought we were adding similar idea to our shakeout, not e2e itself", then the design
and its two conditions — bugs the branch did not cause never block, and a removal test — "ok"). No
threat model and no `ARCHITECTURE-INVARIANTS.md` in this repo, so no security-sentinel and no
invariant-auditor joined. The fix pass is the commit that carries this file.

Verdict: with fixes. The design is implemented faithfully; the required `Hunt:` line lacked an
honest form for hunts that cannot run, and the tally and trial were not yet countable.

## Blocking

None.

## Should fix

1. **No honest `Hunt:` line when the hunt cannot run** — no browser, staging or Playground access,
   a re-dispatch, a manifest from before 0.13 (`laika/specs/presskit` now fails). → fixed:
   `Hunt: 0 charters — <why>` in the agent, a re-dispatch keeps the record, Step 3 names the
   `✗ [shakeout-hunt]` recovery; the `ACCEPTED` fixture carries the zero form and a pass test.
2. **The checker accepted a bare `Hunt: 3 charters`.** → fixed: the tally must carry all four
   counts, a zero hunt its reason; tests for both.
3. **The trial command did not measure the last five hunts** — old manifests took the slots,
   spaces broke `xargs`, `-h` hid the file, "nothing" was ambiguous. → fixed: filter to hunts with
   a charter first, `-d '\n'`, `-H`; the rule reads `0 confirmed · 0 not ours`; sibling checkouts
   count once. Worktree globs left out: features land in the main checkouts.
4. **"Not ours" was not decidable and could not be pulled back.** → fixed: not ours only when no
   file the surface renders through is in the branch's `git diff --name-only` — in doubt, it is
   ours; Step 4 lets Stefan overrule a `not ours:` line like a rejection.

## Note

1. Fixture tally did not add up. → fixed: two charter lines, one rejection.
2. The credential-shaped tally branch was untested. → test added.
3. `_hunt_finding` sat under the registry banner. → moved beside `_row_problem`.
4. "no `name: value`" contradicted the record's own labels. → "nothing credential-shaped beyond
   these labels".
5. The checker stripped indentation, the trial's grep does not. → the tally must start its line;
   tested.
6. A not-ours repro was thrown away. → steps as exact as a `fail` row's.
7. The hunt's cost went unreported. → the report says how many actions it spent.
8. The trial had no trigger. → Step 4 shows the tally the check printed.
