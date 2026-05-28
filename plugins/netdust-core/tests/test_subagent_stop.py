"""
test_subagent_stop.py — verifies the SubagentStop testing-gate hook.

The hook reads a JSON payload on stdin with {transcript_path, stop_hook_active,
cwd}. Walks the assistant tool_use blocks in the transcript and decides:

  - No code edits         → passthrough (exit 0, no stdout)
  - Tiny edit AND net ≤ 0 → passthrough (no-op exemption)
  - Otherwise             → require ran_tests_via_bash; block if missing
  - stop_hook_active=true → passthrough (avoid infinite loops)

This test imports the hook as a module, builds synthetic transcripts, runs it
end-to-end via subprocess, and asserts each decision.

Why these tests matter:
  The first version of this gate had a 'no diff' auto-pass that silently
  swallowed every gate (231 false passes in 24h on a single branch). The
  audit log was the only signal that the gate had stopped working. Without
  regression tests, that kind of leak can re-introduce itself any time the
  hook is touched.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "subagent-stop.py"


# --- helpers --------------------------------------------------------------


def _msg(*tool_blocks: dict) -> dict:
    """Wrap a list of tool_use dicts in an assistant message."""
    return {
        "type": "assistant",
        "message": {"content": list(tool_blocks)},
    }


def _edit(old: str, new: str) -> dict:
    return {"type": "tool_use", "name": "Edit",
            "input": {"old_string": old, "new_string": new}}


def _write(content: str) -> dict:
    return {"type": "tool_use", "name": "Write",
            "input": {"file_path": "x.ts", "content": content}}


def _multiedit(*pairs: tuple[str, str]) -> dict:
    return {"type": "tool_use", "name": "MultiEdit",
            "input": {"file_path": "x.ts",
                      "edits": [{"old_string": o, "new_string": n}
                                for o, n in pairs]}}


def _notebook_edit(old: str, new: str) -> dict:
    return {"type": "tool_use", "name": "NotebookEdit",
            "input": {"old_source": old, "new_source": new}}


def _skill(name: str = "testing-workflow") -> dict:
    return {"type": "tool_use", "name": "Skill",
            "input": {"skill": name}}


def _bash(cmd: str) -> dict:
    return {"type": "tool_use", "name": "Bash",
            "input": {"command": cmd}}


def _run_hook(messages: list[dict], stop_hook_active: bool = False) -> tuple[int, str]:
    """Write `messages` to a temp transcript, invoke the hook, return
    (exit_code, stdout)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text("\n".join(json.dumps(m) for m in messages) + "\n")

        payload = {
            "transcript_path": str(transcript),
            "cwd": str(tmp_path),
            "stop_hook_active": stop_hook_active,
        }
        result = subprocess.run(
            ["python3", str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout


def _decision(stdout: str) -> str:
    """Parse the hook's stdout. Returns 'passthrough' if empty, otherwise
    the value of the 'decision' field (e.g. 'block')."""
    if not stdout.strip():
        return "passthrough"
    try:
        return json.loads(stdout).get("decision", "?")
    except json.JSONDecodeError:
        return f"unparseable: {stdout!r}"


def _case(desc: str, expected: str, messages: list[dict],
          stop_hook_active: bool = False) -> tuple[bool, str]:
    """Run one scenario and compare against expected decision."""
    rc, out = _run_hook(messages, stop_hook_active=stop_hook_active)
    got = _decision(out)
    passed = (got == expected) and (rc == 0)
    return passed, f"{desc} (expected {expected}, got {got}, rc={rc})"


# --- scenarios ------------------------------------------------------------


def run() -> list[tuple[bool, str]]:
    results: list[tuple[bool, str]] = []

    # === Edits exempt by no-op exemption ===

    results.append(_case(
        "no edits at all (research/exploration)",
        "passthrough",
        [_msg(_bash("ls -la"))],
    ))

    results.append(_case(
        "single-line deletion (Task 13 case)",
        "passthrough",
        [_msg(_edit(old="old line", new=""))],
    ))

    results.append(_case(
        "pure rename, net=0, added<3 → no-op",
        "passthrough",
        [_msg(_edit(old="const oldName = 1;", new="const newName = 1;"))],
    ))

    results.append(_case(
        "tiny one-line tweak, no tests → still auto-pass (under threshold)",
        "passthrough",
        [_msg(_edit(old="x = 1", new="x = 2"))],
    ))

    results.append(_case(
        "two-line typo fix, no tests → auto-pass (under threshold)",
        "passthrough",
        [_msg(_edit(old="foo\nbar", new="foo2\nbar2"))],
    ))

    # === Edits requiring tests ===

    results.append(_case(
        "new file (Write), no tests → block",
        "block",
        [_msg(_write("export function foo() {\n  return 42;\n}\n"))],
    ))

    results.append(_case(
        "new file (Write) + bun test → pass",
        "passthrough",
        [_msg(_write("export function foo() {\n  return 42;\n}\n")),
         _msg(_bash("bun test"))],
    ))

    results.append(_case(
        "new file + skill only, no bash → block (skill is not gating)",
        "block",
        [_msg(_write("export function foo() {\n  return 42;\n}\n")),
         _msg(_skill("testing-workflow"))],
    ))

    results.append(_case(
        "new file + bash only, no skill → pass (skill is not gating)",
        "passthrough",
        [_msg(_write("export function foo() {\n  return 42;\n}\n")),
         _msg(_bash("bun test"))],
    ))

    # === The refactor-swap hole the new threshold closes ===

    results.append(_case(
        "refactor-swap: 5 added + 5 removed (net 0, added ≥ 3) → block",
        "block",
        [_msg(_edit(
            old="a\nb\nc\nd\ne",
            new="x\ny\nz\nw\nv",
        ))],
    ))

    results.append(_case(
        "refactor-swap with bash test → pass",
        "passthrough",
        [_msg(_edit(
            old="a\nb\nc\nd\ne",
            new="x\ny\nz\nw\nv",
        )),
         _msg(_bash("vendor/bin/phpunit"))],
    ))

    # === Test command recognition (various runners) ===

    test_commands = [
        ("bun test", "bun test"),
        ("bun test with file arg", "cd apps/web && bun test src/foo.test.ts"),
        ("bun run test", "bun run test"),
        ("npx vitest", "npx vitest run"),
        ("npx playwright", "npx playwright test"),
        ("vendor/bin/phpunit", "vendor/bin/phpunit"),
        ("vendor/bin/codecept", "vendor/bin/codecept run unit"),
        ("ddev exec phpunit", "ddev exec phpunit --testsuite=unit"),
        ("ddev exec codecept", "ddev exec codecept run acceptance"),
        ("npm test", "npm test"),
        ("npm run test", "npm run test"),
        ("pnpm test", "pnpm test"),
        ("yarn test", "yarn test"),
        ("composer test", "composer test"),
        ("bunx vitest", "bunx vitest"),
    ]
    for label, cmd in test_commands:
        results.append(_case(
            f"recognized test runner: {label}",
            "passthrough",
            [_msg(_write("export const x = 1;\nexport const y = 2;\nexport const z = 3;\n")),
             _msg(_bash(cmd))],
        ))

    # === MultiEdit ===

    results.append(_case(
        "MultiEdit net=0 (all renames) → auto-pass",
        "passthrough",
        [_msg(_multiedit(("a", "a"), ("x", "y")))],
    ))

    results.append(_case(
        "MultiEdit net positive, no tests → block",
        "block",
        [_msg(_multiedit(("a", "a\nb\nc\nd"), ("x", "x\nz")))],
    ))

    # === NotebookEdit ===

    results.append(_case(
        "NotebookEdit small replace → no-op",
        "passthrough",
        [_msg(_notebook_edit("print(1)", "print(2)"))],
    ))

    results.append(_case(
        "NotebookEdit large new cell, no tests → block",
        "block",
        [_msg(_notebook_edit("", "x = 1\ny = 2\nz = 3\nw = 4\n"))],
    ))

    # === Skill recognition (logged but not gating) ===

    results.append(_case(
        "plugin-namespaced skill form is recognized (still not gating)",
        "passthrough",
        [_msg(_write("export const x = 1;\nexport const y = 2;\nexport const z = 3;\n")),
         _msg(_skill("netdust-core:testing-workflow")),
         _msg(_bash("bun test"))],
    ))

    # === stop_hook_active bypass ===

    results.append(_case(
        "stop_hook_active=true bypasses regardless of activity",
        "passthrough",
        [_msg(_write("export function foo() {\n  return 42;\n}\n"))],
        stop_hook_active=True,
    ))

    # === Bash that LOOKS like a test command but isn't ===

    results.append(_case(
        "Bash command containing 'test' as a word but not a test runner → still blocks",
        "block",
        [_msg(_write("export const a = 1;\nexport const b = 2;\nexport const c = 3;\n")),
         _msg(_bash("echo 'testing the api manually'"))],
    ))

    return results


if __name__ == "__main__":
    rs = run()
    for passed, desc in rs:
        print(f"{'PASS' if passed else 'FAIL'}\t{desc}")
    sys.exit(0 if all(p for p, _ in rs) else 1)
