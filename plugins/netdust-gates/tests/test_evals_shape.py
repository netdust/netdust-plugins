"""test_evals_shape.py — the eval cases are well-formed and the runner parses.
The cases themselves need the `claude` CLI and are run by hand: python3 evals/run-evals.py

The runner's child environment is tested through `child_env` and `prepare_sandbox`, because an
eval started inside herdr must never reach the live herdr server (two-session spec R11)."""
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "evals"
IDS = ["wp-feature-constraints", "security-surface-review-focus", "small-tweak-no-artifacts", "unit-cut-plan",
       "two-session-handoff", "coder-brief-no-recursion"]
KEYS = {"id", "prompt", "files", "expect", "absent", "timeout", "env", "stub_bin", "commit", "allow", "max_turns",
        "branch"}
STUB = (EVALS / "stubs" / "herdr").resolve()
LIVE = {"HERDR_ENV": "1", "HERDR_SOCKET_PATH": "/live/herdr.sock", "HERDR_PANE_ID": "w1:p1",
        "CLAUDE_CODE_MESSAGING_SOCKET": "/live/cc.sock", "CLAUDE_CODE_MESSAGING_TOKEN": "t",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/")}


def _compiles(cases: list[dict]) -> bool:
    try:
        return all(re.compile(e["match"]) and e["where"] for c in cases for e in c["expect"])
    except (re.error, KeyError):
        return False


def _runner():
    spec = importlib.util.spec_from_file_location("run_evals", EVALS / "run-evals.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sh(cmd: str, env: dict, cwd: Path) -> str:
    return subprocess.run(["bash", "-lc", cmd], env=env, cwd=cwd, capture_output=True, text=True).stdout.strip()


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()


def _sandbox_checks(runner) -> list[tuple[bool, str]]:
    child_env = getattr(runner, "child_env", None)
    prepare_sandbox = getattr(runner, "prepare_sandbox", None)
    if child_env is None or prepare_sandbox is None:
        return [(False, "run-evals.py exposes child_env and prepare_sandbox")]
    with tempfile.TemporaryDirectory(prefix="gates-shape-") as tmp:
        root = Path(tmp) / "sandbox"
        root.mkdir()
        bare = child_env({"id": "bare"}, dict(LIVE), root)
        herdr_keys = {k: v for k, v in bare.items() if k.startswith("HERDR_")}
        with_env = child_env({"id": "x", "env": {"HERDR_ENV": "1"}}, dict(LIVE), root)

        case = {"id": "stubbed", "files": {"target.txt": "old\n"}, "commit": True, "stub_bin": "stubs/herdr",
                "env": {"HERDR_ENV": "1"}}
        prepare_sandbox(case, root)
        stubbed = child_env(case, dict(LIVE), root)
        resolved = _sh("command -v herdr", stubbed, root)
        out = _sh("herdr worktree create --branch feature/stubbed", stubbed, root)
        wt = root / ".herdr" / "wt"
        calls = (root / ".herdr" / "calls.log").read_text() if (root / ".herdr" / "calls.log").is_file() else ""

        other = Path(tmp) / "other"
        other.mkdir()
        prepare_sandbox({"id": "o", "files": {"a.txt": "a\n"}, "commit": True, "branch": "feature/elsewhere"}, other)
        sibling = Path(tmp) / "other-sibling"
        _git(other, "worktree", "add", "-q", "-b", "feature/sibling", str(sibling))
        remove_worktrees = getattr(runner, "remove_worktrees", None)
        removed = remove_worktrees(other) if remove_worktrees else []
        return [
            (set(herdr_keys) == {"HERDR_SOCKET_PATH"} and Path(herdr_keys["HERDR_SOCKET_PATH"]).is_relative_to(root),
             f"child_env strips every inherited HERDR_ value and points the socket under the sandbox (got {herdr_keys})"),
            (not any(k.startswith("CLAUDE_CODE_MESSAGING_") for k in bare),
             "child_env strips CLAUDE_CODE_MESSAGING_*, so no child reaches a live Claude session"),
            (with_env.get("HERDR_ENV") == "1" and with_env.get("EVAL_ROOT") == str(root),
             "child_env applies the case's env and names the sandbox as EVAL_ROOT"),
            (resolved == str(STUB) and stubbed.get("HERDR_BIN_PATH") == str(STUB),
             f"with stub_bin, a login shell resolves herdr to the stub (got {resolved!r})"),
            (_git(root, "rev-parse", "--abbrev-ref", "HEAD") == "feature/stubbed" and _git(root, "rev-parse", "--verify", "-q", "HEAD")
             and _git(other, "rev-parse", "--abbrev-ref", "HEAD") == "feature/elsewhere",
             "prepare_sandbox with commit: true ends on feature/<case-id>, or the case's branch, with a valid HEAD"),
            (_git(wt, "rev-parse", "--is-inside-work-tree") == "true" and str(wt) in out
             and "worktree create" in calls,
             f"the stub's worktree create lands at $EVAL_ROOT/.herdr/wt, prints it and logs the call (got {out!r})"),
            (not sibling.exists() and str(sibling) in removed and _git(other, "worktree", "list").count("\n") == 0,
             f"remove_worktrees removes every worktree the sandbox registered, even one outside it (got {removed})"),
        ]


def run() -> list[tuple[bool, str]]:
    cases = json.loads((EVALS / "cases.json").read_text())
    try:
        compile((EVALS / "run-evals.py").read_text(), "run-evals.py", "exec")
        parses = True
    except SyntaxError:
        parses = False
    return [
        (set(IDS) <= {c["id"] for c in cases}, f"the R10 and two-session cases are present (got {[c['id'] for c in cases]}) — new incidents may add more"),
        (all({"id", "prompt", "files", "expect", "absent"} <= set(c) for c in cases),
         "every case carries id, prompt, files, expect, absent"),
        (all(set(c) <= KEYS for c in cases), f"every case key is one the runner reads ({sorted(KEYS)})"),
        (_compiles(cases), "every expect regex compiles and names where it looks"),
        (parses, "run-evals.py parses"),
        *(_sandbox_checks(_runner()) if parses else [(False, "run-evals.py loads")]),
    ]
