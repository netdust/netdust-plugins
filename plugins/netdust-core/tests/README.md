# netdust-core — harness tests

Tests that verify the harness actually does what its skills and READMEs claim.

## Why

The 2026-05-17 audit found:
- The Stop hook had silently no-op'd for months (no API key, no logging, nobody noticed).
- Two slash commands had a broken glob (`netdust-wp/skills/_*/*/`) that matched zero directories — they'd been broken since written.
- RED tests existed for three discipline skills but had never been run.

Pattern: the harness has been optimized for "looks comprehensive" rather than "is verifiably doing something". This directory closes that gap.

## Run

```bash
bash ~/.claude/plugins/netdust-core/tests/run.sh
```

Exits non-zero on any failure. Prints a summary line per test.

## Add a test

Drop a `test_*.py` file in this directory. Convention:

- Module exposes a `run() -> list[tuple[bool, str]]` function returning `(passed, description)` pairs.
- Each test creates its own temp dir (use `tempfile.mkdtemp(prefix="netdust-test-")`) and cleans up.
- No external dependencies — stdlib only (matches the "zero-cost deterministic" ethos of the rest of the harness).
- Tests run the **real** hook scripts via subprocess. No mocking. If the test passes, the hook works.

## What's covered today

| Test file | What it verifies |
|---|---|
| `test_tag_scanner.py` | Stop hook captures `DECISION:`, `RISK:`, `LESSON:`, `TODO:`, `SKILL-EDGE:` tags from a fabricated transcript and writes to the right files |
| `test_session_start.py` | session-start.sh emits memory blocks when memory/STATE.md, lessons.md, todo.md exist, and logs the right found/missing keys |
| `test_skill_audit_glob.py` | `/skill-audit` and `/red-test` commands reference globs that actually match real skill dirs (the regression that broke them silently) |

## Not covered (deliberate)

- The Haiku API path. It's opt-in, network-bound, and would need mocking that's worse than no test.
- The git-commit step. It works or doesn't; failing to commit is logged and non-fatal by design.
- The dashboard-sync step. Optional integration with an external project.
- Skill content quality. That's what RED tests are for — see each discipline skill's `red-tests.md`.
