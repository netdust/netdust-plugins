#!/usr/bin/env python3
"""run-evals.py — the behavioural cases (spec R10).

    run-evals.py [case-id ...]

Each case runs `claude -p` in a scratch project that mirrors the pilot — a project CLAUDE.md
naming netdust-gates:policy first — with this plugin and netdust-core loaded from source,
then checks the plan, the reply and the files it left against the case's regexes. Needs the
`claude` CLI and a network; it is not part of tests/run.sh. Stochastic: a red case is a
signal to tighten the skill, not proof of a regression.

No case can reach a live herdr server or Claude session: every child gets its own environment
(`child_env`) with a socket path nobody listens on, and a case's `stub_bin` shadows `herdr`
even in a login shell, checked before the case starts. No case loads the user's settings:
`claude_args` runs it --restricted, with the plugins, permissions and env it builds itself.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
CORE = PLUGIN.parent / "netdust-core"
EVALS = Path(__file__).resolve().parent
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
# Gates and core load from source (--plugin-dir); the cache's copies stay off.
PLUGINS = ["superpowers@superpowers-marketplace", "netdust-wp@netdust-plugins", "netdust-devops@netdust-plugins"]
TOOLS = "Agent,Bash,Edit,Glob,Grep,Read,Skill,Write"
# --restricted confines the file tools to the sandbox; skills read their companion files here.
READ_ONLY = [PLUGIN.parent, Path.home() / ".claude" / "plugins" / "cache"]
PROJECT_CLAUDE_MD = (
    "The first action on code-changing work is the `netdust-gates:policy` skill.\n"
    "Specs and plans live in `specs/<feature>/`.\n")
# A named herdr session has its own socket, so `Bash(herdr *)` alone would let a case reach it.
# git runs anything through -c alias.x='!sh', reaches other repos through -C, and writes files
# anywhere through --output or a grep pager; only the stub cuts worktrees.
DISALLOWED = ["Bash(herdr --session*)", "Bash(herdr --machine*)", "Bash(herdr --remote*)",
              "Bash(herdr * --session*)", "Bash(herdr * --machine*)", "Bash(herdr * --remote*)",
              "Bash(HERDR_*)", "Bash(herdr session*)", "Bash(herdr plugin*)", "Bash(herdr update*)",
              "Bash(herdr server*)", "Bash(herdr machine*)", "Bash(herdr config*)", "Bash(herdr integration*)",
              "Bash(git -C *)", "Bash(git -c *)", "Bash(git --*)", "Bash(git push*)", "Bash(git config*)",
              "Bash(git worktree add*)", "Bash(git grep* -O*)", "Bash(git grep* --open-files-in-pager*)",
              "Bash(git * --output*)"]
PASSED_ENV = ("HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "PATH", "TMPDIR")
GIT = ["git", "-c", "user.name=eval", "-c", "user.email=eval@localhost", "-c", "commit.gpgsign=false"]


def _write(root: Path, rel: str, content: str) -> None:
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"case file {rel} lands outside the sandbox")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _subject(root: Path, reply: str, where: str) -> str:
    if where == "reply":
        return reply
    if where == "plan":
        return "\n".join(p.read_text() for p in sorted(root.glob("specs/**/plan.md")))
    target = root / where
    return target.read_text() if target.is_file() else ""


def stub_for(case: dict) -> Path:
    stub = (EVALS / case["stub_bin"]).resolve()
    if stub.parent != EVALS / "stubs":
        raise ValueError(f"stub_bin must be a file in evals/stubs/, got {case['stub_bin']}")
    return stub


def stub_digests() -> dict:
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((EVALS / "stubs").iterdir())}


def child_env(case: dict, base: dict, root: Path) -> dict:
    reserved = [k for k in case.get("env", {}) if k.startswith("CLAUDE") or (k.startswith("HERDR_") and k != "HERDR_ENV")]
    if reserved:
        raise ValueError(f"a case's env may not set {reserved}")
    env = {k: base[k] for k in PASSED_ENV if k in base}
    env.update(case.get("env", {}))
    env["HERDR_SOCKET_PATH"] = str(root / ".herdr" / "none.sock")
    env["EVAL_ROOT"] = str(root)
    env["XDG_RUNTIME_DIR"] = str(root / ".xdg")
    if "stub_bin" in case:
        stub = stub_for(case)
        # ~/.profile prepends ~/.local/bin in a login shell; BASH_ENV is sourced after it.
        env.update(EVAL_STUB_DIR=str(stub.parent), BASH_ENV=str(EVALS / "stubs" / "bash-env"),
                   HERDR_BIN_PATH=str(stub), PATH=f"{stub.parent}:{env.get('PATH', '')}")
    return env


def prepare_sandbox(case: dict, root: Path) -> None:
    _write(root, "CLAUDE.md", PROJECT_CLAUDE_MD)
    for rel, content in case["files"].items():
        _write(root, rel, content)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    (root / ".xdg").mkdir(mode=0o700)
    _write(root, ".git/info/exclude", ".herdr/\n.xdg/\n")
    if case.get("commit"):
        subprocess.run([*GIT, "add", "-A"], cwd=root, check=True)
        subprocess.run([*GIT, "commit", "-q", "-m", "eval sandbox"], cwd=root, check=True)
        subprocess.run(["git", "checkout", "-q", "-b", case.get("branch", f"feature/{case['id']}")],
                       cwd=root, check=True)


# A session may cut a worktree beside the sandbox, which would outlive the run. Only one
# under the sandbox's temp parent is deleted; any other is reported, never touched.
def remove_worktrees(root: Path) -> tuple[list[str], list[str]]:
    listed = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"],
                            capture_output=True, text=True).stdout
    paths = [line.split(" ", 1)[1] for line in listed.splitlines() if line.startswith("worktree ")]
    removed, kept = [], []
    for path in (p for p in paths if Path(p).resolve() != root.resolve()):
        if not Path(path).resolve().is_relative_to(root.resolve().parent):
            kept.append(path)
            continue
        done = subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force", "--force", path],
                              capture_output=True)
        (removed if done.returncode == 0 else kept).append(path)
    subprocess.run(["git", "-C", str(root), "worktree", "prune"], capture_output=True)
    return removed, kept


def spawn(args: list[str], root: Path, env: dict, timeout: int) -> subprocess.CompletedProcess | None:
    proc = subprocess.Popen(args, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None
    return subprocess.CompletedProcess(args, proc.returncode, out, err)


def claude_args(case: dict) -> list[str]:
    read_only = [f"Edit(/{d}/**)" for d in READ_ONLY]
    settings = {"enabledPlugins": dict.fromkeys(PLUGINS, True),
                "permissions": {"allow": case.get("allow", []), "deny": DISALLOWED + read_only},
                "env": {"NETDUST_GUARD_ASK": "on"}}
    add_dirs = [arg for d in READ_ONLY for arg in ("--add-dir", str(d))]
    return ["claude", "-p", case["prompt"], "--restricted", "--strict-mcp-config", "--tools", TOOLS,
            "--settings", json.dumps(settings), "--plugin-dir", str(PLUGIN), "--plugin-dir", str(CORE),
            *add_dirs, "--permission-mode", "acceptEdits", "--max-turns", str(case.get("max_turns", 25))]


# An `absent` entry under ~/ names a path outside the sandbox: the canary for an escape.
def found(root: Path, pattern: str) -> list[str]:
    if pattern.startswith("~/"):
        path = Path(pattern).expanduser()
        return [str(path)] if path.exists() else []
    return [str(p.relative_to(root)) for p in root.glob(pattern)]


def run_case(case: dict) -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="gates-eval-") as tmp:
        root = Path(tmp)
        prepare_sandbox(case, root)
        before = stub_digests()
        try:
            ok, failures = _run_in(case, root)
        finally:
            removed, kept = remove_worktrees(root)
            for path in removed:
                print(f"      removed worktree {path}")
            for path in kept:
                print(f"      LEFT worktree {path}: outside {root.parent} or its removal failed")
        changed = [name for name, digest in stub_digests().items() if before.get(name) != digest]
        if changed:
            return False, failures + [f"evals/stubs/ changed during the case: {changed}"]
        return ok, failures


def _run_in(case: dict, root: Path) -> tuple[bool, list[str]]:
    env = child_env(case, dict(os.environ), root)
    if "stub_bin" in case:
        resolved = subprocess.run(["bash", "-lc", "command -v herdr"], cwd=root, env=env,
                                  capture_output=True, text=True).stdout.strip()
        if resolved != env["HERDR_BIN_PATH"]:
            return False, [f"refused to start: herdr resolves to {resolved!r}, not the stub"]
    outside = [hit for glob in case["absent"] if glob.startswith("~/") for hit in found(root, glob)]
    if outside:
        return False, [f"refused to start: {outside} already exist"]
    timeout = case.get("timeout", 900)
    proc = spawn(claude_args(case), root, env, timeout)
    if proc is None:
        return False, [f"timed out after {timeout}s"]
    reply = proc.stdout
    failures = []
    for e in case["expect"]:
        if not re.search(e["match"], _subject(root, reply, e["where"])):
            failures.append(f"missing in {e['where']}: /{e['match']}/")
    for glob in case["absent"]:
        hits = found(root, glob)
        if hits:
            failures.append(f"must not exist: {glob} (found {hits})")
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
