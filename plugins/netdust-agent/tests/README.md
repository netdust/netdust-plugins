# netdust-core — harness tests

Tests that verify the harness actually does what its skills and READMEs claim.

## Why

The 2026-05-17 audit found:
- The Stop hook had silently no-op'd for months (no API key, no logging, nobody noticed).
- Two slash commands had a broken glob (`netdust-wp/skills/_*/*/`) that matched zero directories — they'd been broken since written.
- RED tests existed for three discipline skills but had never been run.

Pattern: the harness has been optimized for "looks comprehensive" rather than "is verifiably doing something". This directory closes that gap.

## The two calibration regressions

Two assertions in here exist to stop a specific, expensive failure recurring. Read them
before relaxing anything they touch:

- **`test_spec_gate_check.py`** — *"Tier B on a boundary surface WITH a named presence proof
  draws no warning."* If that warning comes back, every framework-primitive call in a
  WordPress feature gets pushed to Tier A + `split` again, and the contact page repeats
  itself (calibration: `contact-page-8k`).
- **`test_verify_budget.py`** — *"an unresolvable git ref fails OPEN."* The tripwire's only
  power is to interrupt a human. It must never spend that on its own tooling breaking.

## Run

```bash
bash plugins/netdust-agent/tests/run.sh
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
| `test_no_auto_memory.py` | A project can opt out of ALL Stop-hook writes (memory/, tasks/, .gitignore, auto-commit) by placing a `.no-auto-memory` marker at its root — the hook must never write into or commit the Layer-B fleet dir |
| `test_plugin_version_resolution.py` | "Active plugin version" comes from Claude Code's own registry (`installed_plugins.json`, v2 schema), not version-dir mtimes — covers both session-stop.py and session-start.sh resolvers |
| `test_pretooluse_guard.py` | The PreToolUse destructive-action guard: denylist matches emit `ask` (never `deny` in v1), fails OPEN on malformed input/non-Bash tools/internal errors, never exits 2 |
| `test_session_start.py` | session-start.sh emits memory blocks when memory/STATE.md, lessons.md, todo.md exist, and logs the right found/missing keys |
| `test_session_start_budget.py` | session-start.sh enforces a real token/size budget on injected memory content |
| `test_spec_gate_check.py` | The harness gate checker (`bin/gate-check.py`) |
| `test_standards_gate_hook.py` | The standards backstop added to `subagent-stop.py` |
| `test_stop_hook_dedup.py` | Dedup survives sidecar loss — the target file (not just the gitignored `.stop-hook-state.json` ring) is the durable dedup record, so losing the sidecar doesn't re-append every tag on the next scan |
| `test_stop_hook_idempotency.py` | The Stop hook's idempotency — re-running does not duplicate captured tags |
| `test_subagent_stop.py` | The SubagentStop testing-gate hook |
| `test_tag_scanner.py` | The Stop hook's deterministic tag scanner captures `DECISION:`, `RISK:`, `LESSON:`, `TODO:`, `SKILL-EDGE:` tags from a fabricated transcript and writes to the right files |

## Not covered (deliberate)

- The git-commit step. It works or doesn't; failing to commit is logged and non-fatal by design.
- The dashboard-sync step. Optional integration with an external project.
- Skill content quality. That's what RED tests are for — see each discipline skill's `red-tests.md`.
