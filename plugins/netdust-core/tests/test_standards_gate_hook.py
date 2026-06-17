"""
test_standards_gate_hook.py — verifies the standards backstop added to subagent-stop.py.

The standards gate (goal #2) fires ONLY when the project has a linter/formatter
configured. So:
  - linter configured + code edited + tests ran but lint NOT run → block (standards)
  - linter configured + lint ran                                  → passthrough
  - NO linter configured                                          → never block on standards
This keeps parity with the testing gate while never falsely blocking a project that
has no linter. Existing testing-gate behavior is covered by test_subagent_stop.py and
must remain unchanged (those run in an empty cwd → no linter → standards inert).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "subagent-stop.py"

PKG_WITH_ESLINT = json.dumps({"devDependencies": {"eslint": "^9", "prettier": "^3"}})
COMPOSER_WITH_PHPCS = json.dumps({"require-dev": {"squizlabs/php_codesniffer": "^3"}})


def _msg(*tool_blocks):
    return {"type": "assistant", "message": {"content": list(tool_blocks)}}


def _write(content):
    return {"type": "tool_use", "name": "Write", "input": {"content": content}}


def _edit(old, new):
    return {"type": "tool_use", "name": "Edit",
            "input": {"old_string": old, "new_string": new}}


def _bash(cmd):
    return {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}


BIG = "\n".join(f"line {i}" for i in range(20))  # >GATE_MIN_ADDITIONS, net-positive


def _run(messages, cwd_files=None):
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        for name, content in (cwd_files or {}).items():
            (tp / name).write_text(content)
        transcript = tp / "t.jsonl"
        transcript.write_text("\n".join(json.dumps(m) for m in messages))
        hook_input = {"transcript_path": str(transcript), "cwd": str(tp)}
        proc = subprocess.run([sys.executable, str(HOOK)],
                              input=json.dumps(hook_input),
                              capture_output=True, text=True, timeout=15)
        decision = "passthrough"
        if proc.stdout.strip():
            try:
                decision = json.loads(proc.stdout).get("decision", "?")
            except json.JSONDecodeError:
                decision = "?"
        return decision, proc.stdout


def run():
    results = []

    # edited + tests ran, linter configured, lint NOT run → block on standards
    d, out = _run([_msg(_write(BIG), _bash("npx vitest run"))],
                  cwd_files={"package.json": PKG_WITH_ESLINT})
    results.append((d == "block" and "STANDARDS" in out,
                    "eslint configured + tests ran + no lint → block (standards)"))

    # edited + tests ran + lint ran, linter configured → passthrough
    d, out = _run([_msg(_write(BIG), _bash("npx vitest run"), _bash("npx eslint src/"))],
                  cwd_files={"package.json": PKG_WITH_ESLINT})
    results.append((d == "passthrough",
                    "eslint configured + tests + eslint ran → passthrough"))

    # NO linter config → standards never blocks (tests ran) → passthrough
    d, out = _run([_msg(_write(BIG), _bash("npx vitest run"))], cwd_files={})
    results.append((d == "passthrough",
                    "no linter configured + tests ran → passthrough (standards inert)"))

    # linter configured + NO tests + NO lint → block, message names BOTH
    d, out = _run([_msg(_write(BIG))], cwd_files={"package.json": PKG_WITH_ESLINT})
    results.append((d == "block" and "TESTS" in out and "STANDARDS" in out,
                    "linter + no tests + no lint → block naming both gates"))

    # no-op tiny edit (net 0), linter configured → still passthrough (no-op exemption holds)
    d, out = _run([_msg(_edit("foo", "bar"))], cwd_files={"package.json": PKG_WITH_ESLINT})
    results.append((d == "passthrough",
                    "no-op net-zero edit + linter → passthrough (no-op exemption)"))

    # PHP: composer phpcs configured + tests ran + phpcs NOT run → block standards
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"))],
                  cwd_files={"composer.json": COMPOSER_WITH_PHPCS})
    results.append((d == "block" and "STANDARDS" in out,
                    "phpcs configured + phpunit ran + no phpcs → block (standards)"))

    # PHP: phpcs configured + phpcs ran → passthrough
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"),
                        _bash("vendor/bin/phpcs wp-content/"))],
                  cwd_files={"composer.json": COMPOSER_WITH_PHPCS})
    results.append((d == "passthrough",
                    "phpcs configured + phpunit + phpcs ran → passthrough"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
