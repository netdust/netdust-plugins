"""
test_phpstan_standards.py — PHPStan recognized as standards evidence (FR-2, SC-2).

Contract (from the task's acceptance criteria, written BEFORE the implementation):

  1. LINT_CMD_PATTERN — the hook's real, module-level lint-command regex —
     matches PHPStan invocations (vendor/bin, ddev-prefixed, composer analyse,
     bare `phpstan analyse`) and keeps rejecting non-invocations. Pre-existing
     pattern behaviors (eslint, phpcs, composer lint) are regression-asserted.
  2. project_has_linter() recognizes phpstan.neon / phpstan.neon.dist as
     configured-linter files, and a composer.json with phpstan/phpstan (or the
     WP extension) in require-dev, or an `analyse` script, as configured.
  3. End-to-end (seam): the REAL hook run as a subprocess blocks on STANDARDS
     when phpstan is configured but never ran, and passes through when a
     phpstan command ran.

Looseness note (deliberate, matches the existing pattern style): the regex
matches command substrings anywhere, so the bare-binary form is anchored on
its subcommand (`phpstan analy[sz]e`), never bare `phpstan\\b` — that keeps
`cat phpstan.neon` and `echo phpstan is great` non-matching. vendor/bin/phpstan
is path-anchored and safe to match bare.

The pattern/function fixtures import the hook module ITSELF via importlib —
they assert the real compiled regex and the real project_has_linter, not copies.
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

# Must MATCH the lint pattern after the change (6 phpstan positives).
LINT_POSITIVE = [
    "vendor/bin/phpstan analyse --no-progress",
    "ddev exec vendor/bin/phpstan analyse",
    "composer analyse",
    "ddev composer analyse",
    "composer run-script analyse",
    "phpstan analyse",
]

# Pre-existing behaviors that must KEEP matching (regression).
LINT_POSITIVE_REGRESSION = [
    "npx eslint src/",
    "vendor/bin/phpcs foo.php",
    "composer lint",
]

# Must NOT match (realistic non-invocations; see looseness note above).
LINT_NEGATIVE = [
    "composer analyses src/",          # word boundary: not the analyse script
    'git commit -m "analyse"',         # analyse as prose, no runner
    "cat phpstan.neon",                # reading the config is not running it
    "echo phpstan is great",           # mid-sentence mention, no subcommand
    "composer test:unit",              # a test script, not a standards run
]

COMPOSER_PHPSTAN_DEP = json.dumps(
    {"require-dev": {"phpstan/phpstan": "^2.0",
                     "szepeviktor/phpstan-wordpress": "^2.0"}})
COMPOSER_ANALYSE_SCRIPT = json.dumps(
    {"scripts": {"analyse": "phpstan analyse --no-progress"}})
COMPOSER_PLAIN = json.dumps({"require": {"php": ">=8.1"}})


def run():
    results = []
    mod = _load_hook_module()
    pattern = getattr(mod, "LINT_CMD_PATTERN", None)
    if pattern is None:
        return [(False, "hook module exposes LINT_CMD_PATTERN at module level")]

    # === lint pattern: phpstan positives ===
    for cmd in LINT_POSITIVE:
        results.append((bool(pattern.search(cmd)),
                        f"lint pattern MATCHES: {cmd!r}"))

    # === lint pattern: pre-existing positives (regression) ===
    for cmd in LINT_POSITIVE_REGRESSION:
        results.append((bool(pattern.search(cmd)),
                        f"lint pattern still matches (regression): {cmd!r}"))

    # === lint pattern: negatives ===
    for cmd in LINT_NEGATIVE:
        results.append((not pattern.search(cmd),
                        f"lint pattern REJECTS: {cmd!r}"))

    # === test pattern untouched by the lift (regression) ===
    tpat = getattr(mod, "TEST_CMD_PATTERN", None)
    results.append((tpat is not None and bool(tpat.search("vendor/bin/phpunit"))
                    and not tpat.search("echo 'testing the api manually'"),
                    "TEST_CMD_PATTERN lifted unchanged (phpunit yes, prose no)"))

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
        ("plain composer.json (no linter)", COMPOSER_PLAIN, False),
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "composer.json").write_text(content)
            results.append((mod.project_has_linter(tmp) is expected,
                            f"project_has_linter: {label} → {expected}"))

    # === end-to-end seam: the real hook, un-mocked, subprocess ===

    # phpstan configured + tests ran + NO standards run → block on STANDARDS
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"))],
                  cwd_files={"phpstan.neon": "parameters:\n  level: 6\n"})
    results.append((d == "block" and "STANDARDS" in out,
                    "e2e: phpstan.neon + tests + no analyse → block (standards)"))

    # phpstan configured + tests + phpstan ran → passthrough
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"),
                        _bash("vendor/bin/phpstan analyse --no-progress"))],
                  cwd_files={"phpstan.neon": "parameters:\n  level: 6\n"})
    results.append((d == "passthrough",
                    "e2e: phpstan.neon + tests + phpstan analyse → passthrough"))

    # composer require-dev phpstan + tests + composer analyse → passthrough
    d, out = _run([_msg(_write(BIG), _bash("vendor/bin/phpunit"),
                        _bash("composer analyse"))],
                  cwd_files={"composer.json": COMPOSER_PHPSTAN_DEP})
    results.append((d == "passthrough",
                    "e2e: composer phpstan dep + composer analyse → passthrough"))

    return results


if __name__ == "__main__":
    rs = run()
    for ok, desc in rs:
        print(("pass" if ok else "FAIL") + "\t" + desc)
    sys.exit(0 if all(p for p, _ in rs) else 1)
