"""test_evals_shape.py — the eval cases are well-formed and the runner parses.
The cases themselves need the `claude` CLI and are run by hand: python3 evals/run-evals.py

The runner's child environment is tested through `child_env` and `prepare_sandbox`, because an
eval started inside hc must never reach the live hc core (hc-flow spec R10)."""
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
STUB = (EVALS / "stubs" / "hc").resolve()
GIT_DENY = ["Bash(git -C *)", "Bash(git -c *)", "Bash(git --*)", "Bash(git push*)", "Bash(git config*)",
            "Bash(git worktree add*)", "Bash(git grep* -O*)", "Bash(git grep* --open-files-in-pager*)",
            "Bash(git * --output*)"]
# hc verbs that run or write outside Claude Code's sandbox, or reach another core or machine.
HC_DENY = ["Bash(hc server*)", "Bash(hc machine*)", "Bash(hc update*)", "Bash(hc exec*)", "Bash(hc file*)",
           "Bash(hc put*)", "Bash(hc keys*)", "Bash(hc connect*)", "Bash(hc * --on*)", "Bash(hc --on*)",
           "Bash(HC_*)", "Bash(herdr*)"]
HC_STATE_VERBS = ("server", "machine", "update", "exec", "file", "put", "keys", "connect")
LIVE = {"HERDR_ENV": "1", "HC_SESSION": "default", "HC_TERMINAL_ID": "t8", "HERDR_SOCKET_PATH": "/live/herdr.sock", "HERDR_PANE_ID": "w1:p1",
        "CLAUDE_CODE_MESSAGING_SOCKET": "/live/cc.sock", "CLAUDE_CODE_MESSAGING_TOKEN": "t",
        "PLOI_API_TOKEN": "t", "SSH_AUTH_SOCK": "/live/ssh.sock", "XDG_RUNTIME_DIR": "/run/user/1000",
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/live/bus", "NETDUST_GUARD_ASK": "off",
        "CLAUDE_CODE_SESSION_ID": "s", "CLAUDE_CODE_CHILD_SESSION": "1", "CLAUDE_CODE_SESSION_ATTENDED": "1",
        "CLAUDE_PID": "1", "CLAUDECODE": "1", "AI_AGENT": "claude",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/")}
PASSED = {"HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "PATH", "TMPDIR"}
SET = {"HERDR_SOCKET_PATH", "HC_SESSION", "EVAL_ROOT", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_STATE_HOME",
       "XDG_DATA_HOME", "TMPDIR"}
XDG = ("XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME")


def _socket_fits(env: dict) -> bool:
    return len(f"{env.get('XDG_RUNTIME_DIR', '')}/herdr-core/{env.get('HC_SESSION', '')}.sock") <= 107


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
        hc_keys = {k: v for k, v in bare.items() if k.startswith("HC_")}
        with_env = child_env({"id": "x", "env": {"HC_TERMINAL_ID": "t1"}}, dict(LIVE), root)
        deep = Path(tmp) / ("d" * 90)
        far_env = child_env({"id": "deep"}, dict(LIVE), deep)

        case = {"id": "stubbed", "files": {"target.txt": "old\n"}, "commit": True, "stub_bin": "stubs/hc",
                "env": {"HC_TERMINAL_ID": "t1"}}
        prepare_sandbox(case, root)
        stubbed = child_env(case, dict(LIVE), root)
        resolved = _sh("command -v hc", stubbed, root)
        # Only ever the stub: a real hc here would look for Stefan's core.
        stub_sh = lambda cmd: _sh(cmd, stubbed, root) if resolved == str(STUB) else ""
        out = stub_sh('hc run --bg --outlive-parent --name stubbed-coder coder "Plan: specs/x/plan.md"')
        calls = (root / ".hc" / "calls.log").read_text() if (root / ".hc" / "calls.log").is_file() else ""
        marker = (root / ".hc" / "run-coder").read_text() if (root / ".hc" / "run-coder").is_file() else ""
        space = stub_sh("hc get t1 --json")
        excluded = (root / ".git" / "info" / "exclude").read_text()

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
            (hc_keys == {"HC_SESSION": "eval"},
             f"child_env strips every inherited HC_ value and runs hc in its own session (got {hc_keys})"),
            (all(Path(bare.get(k, "/")).is_relative_to(root) for k in XDG) and _socket_fits(bare),
             f"hc's four XDG dirs are in the sandbox, its socket path within 107 bytes (got {[bare.get(k) for k in XDG]})"),
            (_socket_fits(far_env) and not any(Path(far_env.get(k, "/")).is_relative_to(Path.home()) for k in XDG)
             and len({str(Path(far_env.get(k, "/")).parent) for k in XDG}) == 1,
             f"a sandbox too deep for the socket gets one short scratch dir instead (got {far_env.get('XDG_RUNTIME_DIR')})"),
            (not any(k.startswith("CLAUDE_CODE_MESSAGING_") for k in bare),
             "child_env strips CLAUDE_CODE_MESSAGING_*, so no child reaches a live Claude session"),
            (Path(bare.get("TMPDIR", "/")).is_relative_to(root),
             "TMPDIR is inside the sandbox, the one temp dir Claude Code's sandbox lets Bash write"),
            (set(bare) <= PASSED | SET and Path(bare.get("XDG_RUNTIME_DIR", "/")).is_relative_to(root),
             f"child_env passes only an allowlist and keeps XDG_RUNTIME_DIR in the sandbox (got {sorted(set(bare) - PASSED)})"),
            (with_env.get("HC_TERMINAL_ID") == "t1" and with_env.get("EVAL_ROOT") == str(root),
             "child_env applies the case's env and names the sandbox as EVAL_ROOT"),
            (resolved == str(STUB), f"with stub_bin, a login shell resolves hc to the stub (got {resolved!r})"),
            (_git(root, "rev-parse", "--abbrev-ref", "HEAD") == "feature/stubbed" and _git(root, "rev-parse", "--verify", "-q", "HEAD")
             and _git(other, "rev-parse", "--abbrev-ref", "HEAD") == "feature/elsewhere",
             "prepare_sandbox with commit: true ends on feature/<case-id>, or the case's branch, with a valid HEAD"),
            (re.search(r"(?m)^run .*--outlive-parent.*coder", calls) is not None and marker.strip() == "coder"
             and _json(out).get("first_message", {}).get("sent") is True,
             f"the stub logs `run … coder …` to .hc/calls.log, marks .hc/run-coder and answers like hc (got {out!r})"),
            (_json(space).get("labels", {}).get("herdr.space") == "s1",
             f"the stub's `hc get t1` carries a herdr.space label, so the pair recipe finds its space (got {space!r})"),
            (".hc/" in excluded.splitlines() and ".herdr/" not in excluded.splitlines(),
             "the sandbox's .git/info/exclude hides .hc/, the stub's log"),
            (not sibling.exists() and str(sibling) in removed,
             f"remove_worktrees removes a worktree the sandbox cut beside itself (got {removed})"),
            (far_kept, f"remove_worktrees deletes nothing outside the sandbox's temp parent and reports it (kept {kept})"),
            (_strays_flagged(getattr(runner, "stray_worktrees", None), root),
             "a stubbed case fails on any worktree: the coder works in the checkout (hc-flow R6)"),
            (_escape_refused(prepare_sandbox, Path(tmp)), "a case's file cannot land outside its sandbox"),
            (_env_refused(child_env, root), "a case's env cannot set HC_* (but HC_TERMINAL_ID), HERDR_* or CLAUDE_*"),
            (_group_killed(getattr(runner, "spawn", None), root),
             "a case that times out has its whole process group killed, grandchildren included"),
        ]


def _strays_flagged(stray_worktrees, root: Path) -> bool:
    if stray_worktrees is None:
        return False
    one, other = str(root.parent / "wt"), str(root / ".claude" / "worktrees" / "agent-x")
    return (stray_worktrees({"stub_bin": "stubs/hc"}, root, [one, other]) == [one, other]
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
    for env in ({"HC_SESSION": "default"}, {"HERDR_SOCKET_PATH": "/live.sock"}, {"CLAUDE_CODE_MESSAGING_TOKEN": "t"}):
        try:
            child_env({"id": "e", "env": env}, dict(LIVE), root)
            return False
        except ValueError:
            pass
    return child_env({"id": "e", "env": {"HC_TERMINAL_ID": "t1"}}, dict(LIVE), root).get("HC_TERMINAL_ID") == "t1"


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


def _canary_reaches_sandbox(case) -> bool:
    if case is None:
        return False
    replies = [e["match"] for e in case["expect"] if e["where"] == "reply"]
    sandboxed = "touch: cannot touch '/home/x/eval-canary': Read-only file system"
    permission = "touch in '/home/x/eval-canary' needs approval. The path is outside the working directories"
    return (case.get("allow") == ["Bash(sh canary.sh)"] and "$HOME/eval-canary" in case["files"].get("canary.sh", "")
            and "~/eval-canary" in case["absent"] and len(replies) == 1
            and re.search(replies[0], sandboxed) is not None and re.search(replies[0], permission) is None)


def _sandbox_refusal(sandbox_refusal) -> bool:
    if sandbox_refusal is None:
        return False
    bash_case, plain_case = {"allow": ["Bash(git status*)"]}, {"allow": []}
    short, long = Path("/tmp/gates-eval-abcdefgh"), Path("/tmp/" + "x" * 120)
    have = lambda name: f"/usr/bin/{name}"
    missing = sandbox_refusal(bash_case, short, which=lambda name: None if name == "socat" else f"/usr/bin/{name}")
    too_long = sandbox_refusal(bash_case, long, which=have)
    return (missing is not None and "socat" in missing
            and too_long is not None and "108" in too_long
            and sandbox_refusal(plain_case, long, which=lambda name: None) is None
            and sandbox_refusal(bash_case, short, which=have) is None)


def _refuses(stub_for) -> bool:
    if stub_for is None:
        return False
    try:
        stub_for({"stub_bin": "../run-evals.py"})
    except ValueError:
        return stub_for({"stub_bin": "stubs/hc"}) == STUB
    return False


def _json(text: str) -> dict:
    try:
        return json.loads(text)
    except ValueError:
        return {}


def _grants_state_verb(rule: str) -> bool:
    m = re.match(r"Bash\(hc\s*(\S*)(.*)\)$", rule)
    return bool(m) and (m.group(1).rstrip("*") in HC_STATE_VERBS or m.group(1) in ("*", "")
                        or m.group(1).startswith("--on") or "--on" in m.group(2))


def _flag(args: list[str], name: str) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args[:-1]) if a == name]


def _isolation_checks(runner) -> list[tuple[bool, str]]:
    claude_args = getattr(runner, "claude_args", None)
    if claude_args is None:
        return [(False, "run-evals.py exposes claude_args, the argv every case runs with")]
    case = {"id": "x", "prompt": "p", "allow": ["Bash(hc run*)"]}
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
        (all(rule in deny for rule in HC_DENY),
         f"every case denies the hc verbs that act outside the sandbox, and herdr entirely {HC_DENY}"),
        (settings.get("sandbox") == {"enabled": True, "failIfUnavailable": True, "allowUnsandboxedCommands": False,
                                     "autoAllowBashIfSandboxed": False},
         f"every case's Bash runs in Claude Code's sandbox: never unsandboxed, never auto-allowed (got {settings.get('sandbox')})"),
        (_sandbox_refusal(getattr(runner, "sandbox_refusal", None)),
         "a case that may run Bash is refused while bwrap or socat is missing, or its .tmp is too long for the sandbox's sockets"),
        (_refuses(getattr(runner, "stub_for", None)),
         "a stub_bin outside evals/stubs/ is refused, so a case cannot shadow hc with any file"),
        (set(getattr(runner, "stub_digests", dict)()) == {"hc", "bash-env"},
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
        (not any(rule.startswith("Bash(printenv") and rule != "Bash(printenv HC_TERMINAL_ID)"
                 for c in cases for rule in c.get("allow", [])),
         "a case may read HC_TERMINAL_ID, never the whole environment (`Bash(printenv *)` matches a bare printenv)"),
        (not [rule for c in cases for rule in c.get("allow", []) if _grants_state_verb(rule)],
         f"no case's allow grants an hc verb that acts outside the sandbox {HC_STATE_VERBS} or --on"),
        (not [c["id"] for c in cases if "stub_bin" not in c and any(r.startswith("Bash(hc") for r in c.get("allow", []))],
         "a case that allows any hc verb runs on the stub, so `hc run` never starts a real program"),
        (all(c["prompt"].startswith("Role: coder\n") and "Plan: specs/greeting/plan.md" in c["prompt"]
             and "Entry: netdust-gates:policy" in c["prompt"] for c in cases if c["id"] == "coder-brief-no-recursion"),
         "coder-brief-no-recursion's prompt is shaped like the real brief, so it tests the exemption"),
        (_canary_reaches_sandbox(next((c for c in cases if c["id"] == "canary-home-write"), None)),
         "the canary's script passes the permission layer, so only the sandbox can stop its write to $HOME"),
        (not any(rule in ("Bash(hc *)", "Bash(hc*)") for c in cases for rule in c.get("allow", [])),
         "no case allows every hc verb, only the ones the stub serves"),
        (not any(rule.startswith("Bash(herdr") for c in cases for rule in c.get("allow", [])),
         "no case allows herdr: every flow runs on hc"),
        (not any("Bash(git *)" in c.get("allow", []) for c in cases),
         "no case allows every git command: `git -c alias.x='!sh'` is arbitrary execution"),
        (_compiles(cases), "every expect regex compiles and names where it looks"),
        (parses, "run-evals.py parses"),
        *(_sandbox_checks(_runner()) if parses else [(False, "run-evals.py loads")]),
        *(_isolation_checks(_runner()) if parses else []),
    ]
