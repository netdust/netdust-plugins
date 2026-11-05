# Plan review — exposure-probe (plan 1 of the security-checks set)
Reviewed-plan: 93b7f24f5ff1c878f74a69bcf0b9490435876c20 /home/ntdst/Projects/netdust-plugins/specs/exposure-probe/plan.md
Verdict: not ready

(First round. Findings: 1 Blocking · 5 Should fix · 5 Note. The plan was fixed and reviewed again; the second round replaces this file. This round is kept in git history, commit "specs: exposure-probe — plan review round 1".)

B1 — a new `dist/scripts/` file is not vendored unless added to `devops-version`'s closed `MANAGED` list (`dist/scripts/devops-version:23-39,115-128`; `bin/new-project:200-202` scaffolds through the same `--update`). Without it no project ever receives `scripts/health-exposure` and `make health` ends with exit 127.
S1 — Task 2's "ssh stub reports drift (the existing stubs)" does not exist; no test runs `make health` end to end. S2 — a second `trap … EXIT` replaces the suite's cleanup trap (`tests/test-makefile.sh:186`). S3 — fixtures leave `production.url` at `https://example.invalid`, contradicting "only 127.0.0.1 in tests". S4 — threat-model mitigation 5 (no body printed) has no test. S5 — `classify()` has no default branch for 400, 402, 406, 429, 204 or a persisting 405.
N1 — the "nobody can unit-test a recipe" reason is false (`_health-disk` is tested directly); the script is still right, for readability and a standalone runnable. N2 — PHP is optional in this suite (`tests/test-makefile.sh:140` guards it); use `php -S 127.0.0.1:0` and parse the port from its first log line. N3 — `SITE` is a make variable, not exported; `_health-exposure` must pass it. N4 — both `plugin.json` and the marketplace description carry the changelog head, for both plugins. N5 — the first-working-version line should point at the coder's Step 5 run.

Cut: holds. Plan 1 (exposure-probe) and plan 2 (core-lint-gate) share no file; R1–R4 are covered by Tasks 1–3.
