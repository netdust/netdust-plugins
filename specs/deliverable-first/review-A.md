# Review record — Cluster A (2026-08-09)

Reviewers: generalist (STANDARD, two angles) + code-simplicity, both independent, neither
authored the diff. Verdict: 0 Critical / 3 Important / 5 Suggestions + 9 simplicity items.

## Fixed now (ledger: Cluster A-fix)
- **I-1** → T10 — behaviour-block `RED until:` vacuously satisfiable (directory `.exists()`,
  substring files match). Probe-confirmed bypass of FR-6/7. Triggered the one-way FULL escalation.
- **I-2** → T11 — fr-source block boundary: colon-less FR def escapes the check and donates
  its `Source:` upward. Probe-confirmed.
- **I-3** → T12 (code half) + T07 extension (doc half) — the HALT contract survives in
  `hooks/loop-gate.py` (dead branch pinned green by a stub), `commands/integration.md`,
  `commands/shakeout.md`, `bin/README.md`; Cluster C's coherence grep widened to plugin root.
- Riders taken inside those cycles: S-2 (backtick false-dangle), S-4 (`Source:` needs a word
  character), S-5b (comment on the deliberate FAIL+WARN dual-fire).

## Parked
*Re-read once by the branch-closing panel; never a merge blocker; no tasks.*

- S-1 — FWV pass-message overclaims when `(files: )` is empty (check_files_segment FAILs the
  artifact anyway; cosmetic).
- S-3 — root-level `test_gate.py` counts as non-test deliverable (matches stated scope; only
  matters if a corpus ever keeps tests outside `tests/`).
- S-5a — argparse description still says "tripwire" (wording).
- Simplicity 1 — rebuild `parse_behaviour_clusters` on `parse_clusters` + `task_blocks` (−23,
  restructure, validated green).
- Simplicity 2 — dead `per_file` machinery in `verify-budget.measure()` (−5, pure deletion).
- Simplicity 3 — merge three parallel block-line structures (−7).
- Simplicity 4 — FR-7 rule stated three times in docstrings; keep one canonical (−9).
- Simplicity 5 — repeated presence-not-truth sentence (−2).
- Simplicity 6 — lazy `covered_ok` sentinel (−3).
- Simplicity 7 — defensive `try/except OSError` on `resolve()` (−3, borderline).
- Simplicity 8 — FAIL≡WARN condition duplication is contract-locked by test 23h (report-only;
  S-5b's comment is the action taken).
- Simplicity 9 — stale "tripwire" naming in verify-budget (wording; overlaps S-5a).

## Strengths (recorded so they survive)
Live-CLI seam cases + self-hosting corpus case per check; fence-strip inheritance tested per
check; the two-gate interlock (invalid waiver trips behaviour-cluster AND unit-test-contract);
docstrings honest about presence-not-truth throughout.
- S-A (sentinel) — verify-budget `--base` argument-injection guard (`--` separator); defensive only, `--base` is not artifact-controlled.
- Fleet (implementer, T05) — the hook's TEST_CMD_PATTERN recognizer does not know this repo's own runner (`bash plugins/netdust-agent/tests/run.sh`), so every agent close in the plugin repo argues with the gate; own spec/branch, not this feature's diff.
