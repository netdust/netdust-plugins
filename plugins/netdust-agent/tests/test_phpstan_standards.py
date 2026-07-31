"""
test_phpstan_standards.py — PHPStan + full-gate runs as standards/test evidence.

Contract: (1) LINT_CMD_PATTERN matches phpstan + gate runs, rejects
non-invocations; (2) gate runs also satisfy TEST_CMD_PATTERN; (3) the
block message coaches phpstan/gate; (4) project_has_linter token-checks
composer scripts. The hook's own comments are the source of truth.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "subagent-stop.py"


def _load_hook_module():
    """Import the real hook file (hyphenated name → importlib)."""
    spec = importlib.util.spec_from_file_location("subagent_stop_hook", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- end-to-end helpers (same shape as test_standards_gate_hook.py) --------


def _msg(*tool_blocks):
    return {"type": "assistant", "message": {"content": list(tool_blocks)}}


def _write(content):
    return {"type": "tool_use", "name": "Write", "input": {"content": content}}


def _bash(cmd):
    return {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}


BIG = "\n".join(f"line {i}" for i in range(20))  # > GATE_MIN_ADDITIONS, net-positive


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


# --- fixtures ---------------------------------------------------------------

# Must MATCH the lint pattern (phpstan forms; the z-spelling kills analy[sz]e).
LINT_POSITIVE = [
    "vendor/bin/phpstan analyse --no-progress",
    "composer analyse",
    "composer run-script analyse",
    "phpstan analyse",
    "phpstan analyze",
]

# Full-gate runs — must match BOTH patterns (the gate runs the unit tier AND
# the analyse/lint tiers, so one gate run is evidence for both).
GATE_POSITIVE = [
    "composer gate",
    "ddev composer gate",
    "sh bin/gate.sh",
]

# Must NOT match either pattern (gate as prose / not the gate script).
GATE_NEGATIVE = [
    'git commit -m "gate"',
    "composer gates",
]

# Pre-existing behaviors that must KEEP matching (regression).
LINT_POSITIVE_REGRESSION = [
    "npx eslint src/",
    "vendor/bin/phpcs foo.php",
    "composer lint",
]

# Must NOT match (realistic non-invocations).
LINT_NEGATIVE = [
    "composer analyses src/",          # word boundary: not the analyse script
    'git commit -m "analyse"',         # analyse as prose, no runner
    "cat phpstan.neon",                # reading the config is not running it
    "composer test:unit",              # a test script, not a standards run
]

# The exact TEST_CMD_PATTERN source, incl. the gate additions — a literal
# equality check is stronger than spot-checking one positive + one negative.
EXPECTED_TEST_PATTERN = (
    r"\b("
    r"vendor/bin/(phpunit|codecept)|"
    r"(ddev exec )?(phpunit|codecept)|"
    r"npx (vitest|playwright|jest)|"
    r"composer test|"
    r"composer (run-script )?gate|"
    r"bin/gate\.sh|"
    r"npm (run )?test|pnpm test|yarn test|"
    r"bun (run )?(test|vitest|playwright)|"
    r"bunx (vitest|playwright|jest)"
    r")\b"
)

COMPOSER_PHPSTAN_DEP = json.dumps(
    {"require-dev": {"phpstan/phpstan": "^2.0",
                     "szepeviktor/phpstan-wordpress": "^2.0"}})
COMPOSER_ANALYSE_SCRIPT = json.dumps(
    {"scripts": {"analyse": "phpstan analyse --no-progress"}})
# Value deliberately phpstan-free so the fixture kills the `analyze` token
# itself, not the phpstan token.
COMPOSER_ANALYZE_SCRIPT = json.dumps(
    {"scripts": {"analyze": "tools/static-check.sh --strict"}})
COMPOSER_ANALYSES_PROSE = json.dumps(
    {"scripts": {"report": "run analyses report"}})
COMPOSER_PLAIN = json.dumps({"require": {"php": ">=8.1"}})


def run():
    results = []
    mod = _load_hook_module()
    pattern = getattr(mod, "LINT_CMD_PATTERN", None)
    if pattern is None:
        return [(False, "hook module exposes LINT_CMD_PATTERN at module level")]
    tpat = getattr(mod, "TEST_CMD_PATTERN", None)
    if tpat is None:
        return [(False, "hook module exposes TEST_CMD_PATTERN at module level")]

    # === lint pattern: phpstan positives ===
    for cmd in LINT_POSITIVE:
        results.append((bool(pattern.search(cmd)),
                        f"lint pattern MATCHES: {cmd!r}"))

    # === gate runs: evidence for BOTH patterns ===
    for cmd in GATE_POSITIVE:
        results.append((bool(pattern.search(cmd)),
                        f"lint pattern MATCHES gate run: {cmd!r}"))
        results.append((bool(tpat.search(cmd)),
                        f"test pattern MATCHES gate run: {cmd!r}"))
    for cmd in GATE_NEGATIVE:
        results.append((not pattern.search(cmd),
                        f"lint pattern REJECTS: {cmd!r}"))
        results.append((not tpat.search(cmd),
                        f"test pattern REJECTS: {cmd!r}"))

    # === lint pattern: pre-existing positives (regression) ===
    for cmd in LINT_POSITIVE_REGRESSION:
        results.append((bool(pattern.search(cmd)),
                        f"lint pattern still matches (regression): {cmd!r}"))

    # === lint pattern: negatives ===
    for cmd in LINT_NEGATIVE:
        results.append((not pattern.search(cmd),
                        f"lint pattern REJECTS: {cmd!r}"))

    # === test pattern: exact literal (lift + gate additions, nothing else) ===
    results.append((tpat.pattern == EXPECTED_TEST_PATTERN,
                    "TEST_CMD_PATTERN source equals the expected literal"))

    # === block message coaches phpstan + the full gate ===
    activity = {"lines_added": 20, "invoked_testing": True}
    tests_msg = mod.build_block_message(activity, ["tests"])
    results.append(("composer gate" in tests_msg,
                    "block message (tests): suggests composer gate"))
    std_msg = mod.build_block_message(activity, ["standards"])
    results.append(("composer analyse" in std_msg
                    and "vendor/bin/phpstan analyse" in std_msg
                    and "composer gate" in std_msg,
                    "block message (standards): suggests analyse + full gate"))

    # === configured-linter detection: phpstan config files ===
    for fname in ("phpstan.neon", "phpstan.neon.dist"):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / fname).write_text("parameters:\n  level: 6\n")
            results.append((mod.project_has_linter(tmp),
                            f"project_has_linter: {fname} recognized"))

    # === configured-linter detection: composer.json branches ===
    for label, content, expected in [
        ("phpstan/phpstan in require-dev", COMPOSER_PHPSTAN_DEP, True),
        ("analyse script", COMPOSER_ANALYSE_SCRIPT, True),
        ("analyze script (z-spelling)", COMPOSER_ANALYZE_SCRIPT, True),
        ("'run analyses report' script value", COMPOSER_ANALYSES_PROSE, False),
        ("plain composer.json (no linter)", COMPOSER_PLAIN, False),
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "composer.json").write_text(content)
            results.append((mod.project_has_linter(tmp) is expected,
                            f"project_has_linter: {label} → {expected}"))

    # === end-to-end seam: the real hook, un-mocked, subprocess ===

    # phpstan configured + tests ran + NO standards run → block on STANDARDS,
    # and the block message coaches the analyse + full-gate commands
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"))],
                  cwd_files={"phpstan.neon": "parameters:\n  level: 6\n"})
    results.append((d == "block" and "STANDARDS" in out
                    and "composer analyse" in out and "composer gate" in out,
                    "e2e: phpstan.neon + tests + no analyse → block "
                    "(standards, coaches analyse + gate)"))

    # phpstan configured + tests + phpstan ran → passthrough
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"),
                        _bash("vendor/bin/phpstan analyse --no-progress"))],
                  cwd_files={"phpstan.neon": "parameters:\n  level: 6\n"})
    results.append((d == "passthrough",
                    "e2e: phpstan.neon + tests + phpstan analyse → passthrough"))

    return results


if __name__ == "__main__":
    rs = run()
    for ok, desc in rs:
        print(("pass" if ok else "FAIL") + "\t" + desc)
    sys.exit(0 if all(p for p, _ in rs) else 1)
