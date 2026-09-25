#!/usr/bin/env python3
"""run-evals.py — the behavioural cases (spec R10).

    run-evals.py [case-id ...]

Each case runs `claude -p` in a scratch project that mirrors the pilot — netdust-agent
disabled, a project CLAUDE.md naming netdust-gates:policy first — with this plugin loaded,
then checks the plan, the reply and the files it left against the case's regexes. Needs the
`claude` CLI and a network; it is not part of tests/run.sh. Stochastic: a red case is a
signal to tighten the skill, not proof of a regression.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
SETTINGS = {"enabledPlugins": {"netdust-agent@netdust-plugins": False}}
PROJECT_CLAUDE_MD = (
    "The first action on code-changing work is the `netdust-gates:policy` skill.\n"
    "Specs and plans live in `specs/<feature>/`.\n")


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _subject(root: Path, reply: str, where: str) -> str:
    if where == "reply":
        return reply
    if where == "plan":
        return "\n".join(p.read_text() for p in sorted(root.glob("specs/**/plan.md")))
    target = root / where
    return target.read_text() if target.is_file() else ""


def run_case(case: dict) -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="gates-eval-") as tmp:
        root = Path(tmp)
        _write(root, "CLAUDE.md", PROJECT_CLAUDE_MD)
        _write(root, ".claude/settings.json", json.dumps(SETTINGS))
        for rel, content in case["files"].items():
            _write(root, rel, content)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        timeout = case.get("timeout", 900)
        try:
            proc = subprocess.run(
                ["claude", "-p", case["prompt"], "--plugin-dir", str(PLUGIN),
                 "--permission-mode", "acceptEdits", "--max-turns", "25"],
                cwd=root, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, [f"timed out after {timeout}s"]
        reply = proc.stdout
        failures = []
        for e in case["expect"]:
            if not re.search(e["match"], _subject(root, reply, e["where"])):
                failures.append(f"missing in {e['where']}: /{e['match']}/")
        for glob in case["absent"]:
            found = [str(p.relative_to(root)) for p in root.glob(glob)]
            if found:
                failures.append(f"must not exist: {glob} (found {found})")
        return not failures, failures


def main(argv: list[str]) -> int:
    chosen = [c for c in CASES if not argv or c["id"] in argv]
    failed = 0
    for case in chosen:
        ok, failures = run_case(case)
        print(f"{'PASS' if ok else 'FAIL'}  {case['id']}")
        for f in failures:
            print(f"      {f}")
        failed += not ok
    print(f"\n{len(chosen) - failed}/{len(chosen)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
