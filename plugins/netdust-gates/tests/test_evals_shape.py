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
import time
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "evals"
IDS = ["wp-feature-constraints", "security-surface-review-focus", "small-tweak-no-artifacts", "unit-cut-plan",
       "two-session-handoff", "coder-brief-no-recursion", "canary-home-write"]
KEYS = {"id", "prompt", "files", "expect", "absent", "timeout", "env", "stub_bin", "commit", "allow", "max_turns",
        "branch"}
STUB = (EVALS / "stubs" / "herdr").resolve()
GIT_DENY = ["Bash(git -C *)", "Bash(git -c *)", "Bash(git --*)", "Bash(git push*)", "Bash(git config*)",
            "Bash(git worktree add*)", "Bash(git grep* -O*)", "Bash(git grep* --open-files-in-pager*)",
            "Bash(git * --output*)"]
HERDR_DENY = ["Bash(herdr session*)", "Bash(herdr plugin*)", "Bash(herdr update*)", "Bash(herdr server*)",
              "Bash(herdr machine*)", "Bash(herdr config*)", "Bash(herdr integration*)"]
LIVE = {"HERDR_ENV": "1", "HERDR_SOCKET_PATH": "/live/herdr.sock", "HERDR_PANE_ID": "w1:p1",
        "CLAUDE_CODE_MESSAGING_SOCKET": "/live/cc.sock", "CLAUDE_CODE_MESSAGING_TOKEN": "t",
        "PLOI_API_TOKEN": "t", "SSH_AUTH_SOCK": "/live/ssh.sock", "XDG_RUNTIME_DIR": "/run/user/1000",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/live/bus", "NETDUST_GUARD_ASK": "off",
        "CLAUDE_CODE_SESSION_ID": "s", "CLAUDE_CODE_CHILD_SESSION": "1", "CLAUDE_CODE_SESSION_ATTENDED": "1",
        "CLAUDE_PID": "1", "CLAUDECODE": "1", "AI_AGENT": "claude",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/")}
PASSED = {"HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "PATH", "TMPDIR"}
SET = {"HERDR_SOCKET_PATH", "EVAL_ROOT", "XDG_RUNTIME_DIR", "TMPDIR"}


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
        out = _sh(f"{STUB} worktree create --branch feature/stubbed", stubbed, root)
        wt = root / ".herdr" / "wt"
        calls = (root / ".herdr" / "calls.log").read_text() if (root / ".herdr" / "calls.log").is_file() else ""

        other = Path(tmp) / "other"
        other.mkdir()
        prepare_sandbox({"id": "o", "files": {"a.txt": "a\n"}, "commit": True, "branch": "feature/elsewhere"}, other)
        sibling = Path(tmp) / "other-sibling"
        _git(other, "worktree", "add", "-q", "-b", "feature/sibling", str(sibling))
        with tempfile.TemporaryDirectory(prefix="gates-shape-far-") as far_tmp:
            far = Path(far_tmp) / "far"
            _git(other, "worktree", "add", "-q", "-b", "feature/far", str(far))
            remove_worktrees = getattr(runner, "remove_worktrees", None)
            removed, kept = remove_worktrees(other) if remove_worktrees else ([], [])
            far_kept = far.exists() and str(far) in kept
        return [
            (set(herdr_keys) == {"HERDR_SOCKET_PATH"} and Path(herdr_keys["HERDR_SOCKET_PATH"]).is_relative_to(root),
             f"child_env strips every inherited HERDR_ value and points the socket under the sandbox (got {herdr_keys})"),
            (not any(k.startswith("CLAUDE_CODE_MESSAGING_") for k in bare),
             "child_env strips CLAUDE_CODE_MESSAGING_*, so no child reaches a live Claude session"),
            (Path(bare.get("TMPDIR", "/")).is_relative_to(root),
             "TMPDIR is inside the sandbox, the one temp dir Claude Code's sandbox lets Bash write"),
            (set(bare) <= PASSED | SET and Path(bare.get("XDG_RUNTIME_DIR", "/")).is_relative_to(root),
             f"child_env passes only an allowlist and keeps XDG_RUNTIME_DIR in the sandbox (got {sorted(set(bare) - PASSED)})"),
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
            (not sibling.exists() and str(sibling) in removed,
             f"remove_worktrees removes a worktree the sandbox cut beside itself (got {removed})"),
            (far_kept, f"remove_worktrees deletes nothing outside the sandbox's temp parent and reports it (kept {kept})"),
            (_strays_flagged(getattr(runner, "stray_worktrees", None), root),
             "a stubbed case fails on any worktree but the stub's .herdr/wt (spec R2: only the coder writes its tree)"),
            (_escape_refused(prepare_sandbox, Path(tmp)), "a case's file cannot land outside its sandbox"),
            (_env_refused(child_env, root), "a case's env cannot set HERDR_* (but HERDR_ENV) or CLAUDE_*"),
            (_group_killed(getattr(runner, "spawn", None), root),
             "a case that times out has its whole process group killed, grandchildren included"),
        ]


def _strays_flagged(stray_worktrees, root: Path) -> bool:
    if stray_worktrees is None:
        return False
    own, other = str(root / ".herdr" / "wt"), str(root / ".claude" / "worktrees" / "agent-x")
    return (stray_worktrees({"stub_bin": "stubs/herdr"}, root, [own, other]) == [other]
            and stray_worktrees({}, root, [other]) == [])


def _escape_refused(prepare_sandbox, tmp: Path) -> bool:
    root = tmp / "escape"
    root.mkdir()
    try:
        prepare_sandbox({"id": "e", "files": {"../escaped.txt": "x"}}, root)
    except ValueError:
        return not (tmp / "escaped.txt").exists()
    return False


def _env_refused(child_env, root: Path) -> bool:
    for env in ({"HERDR_SOCKET_PATH": "/live.sock"}, {"CLAUDE_CODE_MESSAGING_TOKEN": "t"}):
        try:
            child_env({"id": "e", "env": env}, dict(LIVE), root)
            return False
        except ValueError:
            pass
    return child_env({"id": "e", "env": {"HERDR_ENV": "1"}}, dict(LIVE), root).get("HERDR_ENV") == "1"


def _group_killed(spawn, root: Path) -> bool:
    if spawn is None:
        return False
    pidfile = root / "grandchild.pid"
    proc = spawn(["bash", "-c", f"sleep 60 & echo $! > {pidfile}; wait"], root, dict(os.environ), 1)
    grandchild = int(pidfile.read_text())
    for _ in range(20):
        try:
            os.kill(grandchild, 0)
        except ProcessLookupError:
            return proc is None
        time.sleep(0.1)
    return False


def _sandbox_refusal(sandbox_refusal) -> bool:
    if sandbox_refusal is None:
        return False
    bash_case, plain_case = {"allow": ["Bash(git status*)"]}, {"allow": []}
    missing = sandbox_refusal(bash_case, which=lambda name: None if name == "socat" else f"/usr/bin/{name}")
    return (missing is not None and "socat" in missing
            and sandbox_refusal(plain_case, which=lambda name: None) is None
            and sandbox_refusal(bash_case, which=lambda name: f"/usr/bin/{name}") is None)


def _refuses(stub_for) -> bool:
    if stub_for is None:
        return False
    try:
        stub_for({"stub_bin": "../run-evals.py"})
    except ValueError:
        return stub_for({"stub_bin": "stubs/herdr"}) == STUB
    return False


def _flag(args: list[str], name: str) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args[:-1]) if a == name]


def _isolation_checks(runner) -> list[tuple[bool, str]]:
    claude_args = getattr(runner, "claude_args", None)
    if claude_args is None:
        return [(False, "run-evals.py exposes claude_args, the argv every case runs with")]
    case = {"id": "x", "prompt": "p", "allow": ["Bash(herdr agent start*)"]}
    args = claude_args(case)
    settings = json.loads((_flag(args, "--settings") or ["{}"])[0])
    enabled = {k for k, v in settings.get("enabledPlugins", {}).items() if v}
    plugin_dirs = {Path(d).name for d in _flag(args, "--plugin-dir")}
    deny = settings.get("permissions", {}).get("deny", [])
    return [
        ("--restricted" in args and "--strict-mcp-config" in args and _flag(args, "--tools"),
         "every case runs --restricted --strict-mcp-config with a --tools allowlist, so user settings never load"),
        (plugin_dirs == {"netdust-gates", "netdust-core"} and "superpowers@superpowers-marketplace" in enabled
         and not any(k.startswith(("netdust-gates@", "netdust-core@", "netdust-agent@")) for k in enabled),
         f"gates and core load from source only; --settings enables the rest (got {sorted(plugin_dirs)}, {sorted(enabled)})"),
        (settings.get("permissions", {}).get("allow") == case["allow"]
         and settings.get("env", {}).get("NETDUST_GUARD_ASK") == "on",
         "the runner's --settings carries the case's allow and keeps the destructive-command guard on"),
        ("Bash" in _flag(args, "--tools")[0].split(",") and "ToolSearch" not in _flag(args, "--tools")[0].split(","),
         "--tools names Bash (--restricted drops it otherwise) and not ToolSearch, so no deferred tool loads"),
        (_flag(args, "--add-dir") and all(f"Edit(/{d}/**)" in deny for d in _flag(args, "--add-dir"))
         and not any(rule.startswith("Write(") for rule in deny),
         "every --add-dir (the skills' companion files) is read-only: Edit(path) denies every file-editing tool"),
        (all(rule in settings.get("permissions", {}).get("deny", []) for rule in GIT_DENY),
         f"every case denies git's escape routes {GIT_DENY}"),
        (all(rule in deny for rule in HERDR_DENY), f"every case denies herdr's state verbs {HERDR_DENY}"),
        (settings.get("sandbox") == {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
                                     "autoAllowBashIfSandboxed": False},
         f"every case's Bash runs in Claude Code's sandbox: never unsandboxed, never auto-allowed (got {settings.get('sandbox')})"),
        (_sandbox_refusal(getattr(runner, "sandbox_refusal", None)),
         "a case that may run Bash is refused while bwrap or socat is missing, so it never runs unsandboxed"),
        (_refuses(getattr(runner, "stub_for", None)),
         "a stub_bin outside evals/stubs/ is refused, so a case cannot shadow herdr with any file"),
        (set(getattr(runner, "stub_digests", dict)()) == {"herdr", "bash-env"},
         "both stub files are hashed around each case, so a case that rewrites them fails"),
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
        (not any(rule.startswith("Bash(printenv") and rule != "Bash(printenv HERDR_ENV)"
                 for c in cases for rule in c.get("allow", [])),
         "a case may read HERDR_ENV, never the whole environment (`Bash(printenv *)` matches a bare printenv)"),
        (any(e["where"] == ".herdr/calls.log" and "--permission-mode" in e["match"]
             for c in cases if c["id"] == "two-session-handoff" for e in c["expect"]),
         "two-session-handoff expects the coder started in the thinker's permission mode (R4)"),
        (all(c["prompt"].startswith("Role: coder\n") and "Plan: specs/greeting/plan.md" in c["prompt"]
             and "Entry: netdust-gates:policy" in c["prompt"] for c in cases if c["id"] == "coder-brief-no-recursion"),
         "coder-brief-no-recursion's prompt is shaped like the real brief, so it tests the exemption"),
        (any(c["id"] == "canary-home-write" and "Bash(touch *)" in c.get("allow", []) and "~/eval-canary" in c["absent"]
             for c in cases),
         "the canary lets Bash try ~/eval-canary, so only the sandbox stands between it and $HOME"),
        (not any(rule == "Bash(herdr *)" for c in cases for rule in c.get("allow", [])),
         "no case allows every herdr verb, only the ones the stub serves"),
        (not any("Bash(git *)" in c.get("allow", []) for c in cases),
         "no case allows every git command: `git -c alias.x='!sh'` is arbitrary execution"),
        (_compiles(cases), "every expect regex compiles and names where it looks"),
        (parses, "run-evals.py parses"),
        *(_sandbox_checks(_runner()) if parses else [(False, "run-evals.py loads")]),
        *(_isolation_checks(_runner()) if parses else []),
    ]
