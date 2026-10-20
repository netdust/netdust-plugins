# Branch review — shakeout-hunt

Range: 2e07547..7c075a9 (feature/shakeout-hunt, 1 commit, 5 files)
Reviewer: a fresh, read-only whole-branch reviewer, 2026-10-20. No plan (a bounded change designed
in chat: "e2e explore / bug bash as an extra hunt — is that something we can add to our skills?",
then "ok, goahead"), no threat model and no `ARCHITECTURE-INVARIANTS.md` in this repo, so no
security-sentinel and no invariant-auditor joined. The fix pass is the commit that carries this
file; each finding below says what it did.

Verdict: with fixes. It matches the agreed design and leaves a site without `e2e.config.ts` untouched.

## Blocking

None.

## Should fix

1. **`agents/shakeout-qa.md:45` "goes RED" is weaker than upstream's `ASSERTION_FAILED`.** A repro
   also goes red on an unmatched locator, a timeout or a broken setup — a false `fail` row the fix
   pass would chase. → fixed: "goes RED on its assertion — an `expect` failing, never a timeout,
   an unmatched locator or a setup error."
2. **`commands/shakeout.md:61-62` re-dispatches shakeout-qa, whose Sweep would hunt again** —
   unbounded cost, and new findings could keep the loop from exit 0. → fixed: "once per
   shake-out — a re-dispatch re-drives its flows and never hunts again."
3. **Explorer output (sessions, unmasked video) could land under `tests/` and be committed**; the
   checker scans only `shakeout.md`. → fixed: "Each explorer's `--output` sits under `.e2e/` and is
   never committed."

## Note

4. "and no other" in Which flows did not name the hunt; charters on a no-spec branch could reach a
   struck flow. → fixed: "the one addition (below)"; with no spec, only the approved flows' surfaces.
5. "never a deployed host" had no mechanism. → fixed: `--target` the dev site, none → BLOCKED.
6. The credential scan fires on plain words a denied-actor charter would use. → fixed: charters and
   findings "in words — no URL with a query, no `name: value`."
7. Cost is printed only when the provider reports one. → fixed: "where `e2e` reported one".
8. Charters drawn from the edge classes overlap Drive and replace upstream's postures. → fixed:
   charters use upstream's postures; Drive already takes the edge classes.
9. Nothing said what an overruled rejection becomes. → fixed in Step 4: its repro and a `fail` row,
   back to Step 3.
10. The manifests said charters reach Stefan; Step 4 shows only rejections. → descriptions aligned.
11. Registry home of a hunt regression test unclear; Done when silent on the hunt. → fixed: the
    repro lives in the feature's spec for that surface, under that surface's registry row; Done
    when names the hunt record.
12. Explorer writes pollute the state Drive screenshots. → fixed: "Re-seed through the project's
    recipe before you drive."
13. The wiring assertion pinned wording only. → widened to the opt-in, once-only, `--target`,
    `.e2e/` and assertion-only rules; `test_shakeout_check.py` pins the plain-lines contract (lines
    pass, a hunt table fails).
14. Eval case not owed by precedent (shakeout-qa changes in 0.3.0 and 0.8.1 shipped wiring tests
    only); a behavioural case would need a dev site, a browser and the e2e CLI. → not added; the
    first real hunt on a site that opts in is the proof.
