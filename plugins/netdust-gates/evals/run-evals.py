#!/usr/bin/env python3
"""run-evals.py — the behavioural cases (spec R10).

    run-evals.py [case-id ...]

Each case runs `claude -p` in a scratch project that mirrors the pilot — netdust-agent
disabled, a project CLAUDE.md naming netdust-gates:policy first — with this plugin loaded,
then checks the plan, the reply and the files it left against the case's regexes. Needs the
`claude` CLI and a network; it is not part of tests/run.sh. Stochastic: a red case is a
signal to tighten the skill, not proof of a regression.

No case can reach a live herdr server or Claude session: every child gets its own environment
(`child_env`) with a socket path nobody listens on, and a case's `stub_bin` shadows `herdr`
even in a login shell, checked before the case starts.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
EVALS = Path(__file__).resolve().parent
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
SETTINGS = {"enabledPlugins": {"netdust-agent@netdust-plugins": False}}
PROJECT_CLAUDE_MD = (
    "The first action on code-changing work is the `netdust-gates:policy` skill.\n"
    "Specs and plans live in `specs/<feature>/`.\n")
# A named herdr session has its own socket, so `Bash(herdr *)` alone would let a case reach it.
DISALLOWED = ["Bash(herdr --session*)", "Bash(herdr --machine*)", "Bash(herdr --remote*)",
              "Bash(herdr * --session*)", "Bash(herdr * --machine*)", "Bash(herdr * --remote*)",
              "Bash(HERDR_*)", "SendMessage", "ListAgents", "EnterWorktree"]
GIT = ["git", "-c", "user.name=eval", "-c", "user.email=eval@localhost", "-c", "commit.gpgsign=false"]


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


def child_env(case: dict, base: dict, root: Path) -> dict:
    env = {k: v for k, v in base.items() if not k.startswith(("HERDR_", "CLAUDE_CODE_MESSAGING_"))}
    env.update(case.get("env", {}))
    env["HERDR_SOCKET_PATH"] = str(root / ".herdr" / "none.sock")
    env["EVAL_ROOT"] = str(root)
    if "stub_bin" in case:
        stub = (EVALS / case["stub_bin"]).resolve()
        # ~/.profile prepends ~/.local/bin in a login shell; BASH_ENV is sourced after it.
        env.update(EVAL_STUB_DIR=str(stub.parent), BASH_ENV=str(EVALS / "stubs" / "bash-env"),
                   HERDR_BIN_PATH=str(stub), PATH=f"{stub.parent}:{env.get('PATH', '')}")
    return env


def prepare_sandbox(case: dict, root: Path) -> None:
    _write(root, "CLAUDE.md", PROJECT_CLAUDE_MD)
    _write(root, ".claude/settings.json", json.dumps(SETTINGS))
    for rel, content in case["files"].items():
        _write(root, rel, content)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    if "stub_bin" in case:
        _write(root, ".git/info/exclude", ".herdr/\n")
    if case.get("commit"):
        subprocess.run([*GIT, "add", "-A"], cwd=root, check=True)
        subprocess.run([*GIT, "commit", "-q", "-m", "eval sandbox"], cwd=root, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", case.get("branch", f"feature/{case['id']}")],
                       cwd=root, check=True)


def _claude(case: dict) -> list[str]:
    cmd = ["claude", "-p", case["prompt"], "--plugin-dir", str(PLUGIN), "--permission-mode", "acceptEdits",
           "--max-turns", str(case.get("max_turns", 25)), "--disallowedTools", *DISALLOWED]
    return cmd + (["--allowedTools", *case["allow"]] if case.get("allow") else [])


def run_case(case: dict) -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="gates-eval-") as tmp:
        root = Path(tmp)
        prepare_sandbox(case, root)
        env = child_env(case, dict(os.environ), root)
        if "stub_bin" in case:
            resolved = subprocess.run(["bash", "-lc", "command -v herdr"], cwd=root, env=env,
                                      capture_output=True, text=True).stdout.strip()
            if resolved != env["HERDR_BIN_PATH"]:
                return False, [f"refused to start: herdr resolves to {resolved!r}, not the stub"]
        timeout = case.get("timeout", 900)
        try:
            proc = subprocess.run(_claude(case), cwd=root, env=env, capture_output=True, text=True,
                                  timeout=timeout)
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
