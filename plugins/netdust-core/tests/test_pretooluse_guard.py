"""
test_pretooluse_guard.py — verifies the PreToolUse destructive-action guard.

The hook reads a JSON payload on stdin with {tool_name, tool_input, cwd}.
For Bash tool calls it pattern-matches a conservative denylist of
destructive commands and emits a PreToolUse permission decision:

  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "ask" | "deny" | "allow",
                          "permissionDecisionReason": "..."}}

Decision policy (v1, from the parked threat model — favor `ask` over `deny`):
  - destructive pattern matched  → "ask"  (surface the literal command to a human)
  - highest-risk prod patterns   → "deny" (refuse regardless of stated intent)
  - everything else / non-Bash   → passthrough (exit 0, no stdout = proceed)

CRITICAL invariant tested here: the guard FAILS OPEN. Malformed stdin, a
non-Bash tool, or any internal error must NOT block the call — the hook
exits 0 with no decision (or an explicit allow), never exit 2. A PreToolUse
hook that fails closed would brick every tool call in the session.

Why a table test: the first SubagentStop gate shipped a 'no-diff auto-pass'
that silently swallowed 231 gates. A deterministic guard like this is only
trustworthy if every (command -> decision) pair is pinned, including the
false-positive cases that would otherwise tempt someone to loosen the regex.
"""

import json
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "pretooluse-guard.py"


# --- helpers --------------------------------------------------------------


def _run(tool_name: str, tool_input: dict, raw_stdin: str | None = None) -> tuple[int, str]:
    """Invoke the hook with a PreToolUse payload, return (exit_code, stdout).
    If raw_stdin is given, it is sent verbatim (for malformed-input tests)."""
    with tempfile.TemporaryDirectory() as tmp:
        if raw_stdin is None:
            payload = json.dumps({
                "hook_event_name": "PreToolUse",
                "tool_name": tool_name,
                "tool_input": tool_input,
                "cwd": tmp,
            })
        else:
            payload = raw_stdin
        result = subprocess.run(
            ["python3", str(HOOK)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout


def _decision(stdout: str) -> str:
    """Parse the hook's stdout → 'allow'|'ask'|'deny', or 'passthrough' if
    empty (proceed). 'unparseable'/'malformed' surface structural bugs."""
    if not stdout.strip():
        return "passthrough"
    try:
        obj = json.loads(stdout)
    except json.JSONDecodeError:
        return f"unparseable: {stdout!r}"
    hso = obj.get("hookSpecificOutput")
    if not isinstance(hso, dict):
        return f"malformed: {stdout!r}"
    if hso.get("hookEventName") != "PreToolUse":
        return f"wrong-event: {hso.get('hookEventName')!r}"
    return hso.get("permissionDecision", "?")


def _bash_case(desc: str, cmd: str, expected: str) -> tuple[bool, str]:
    rc, out = _run("Bash", {"command": cmd})
    got = _decision(out)
    # The guard must NEVER exit 2 (that's the only signal that blocks on its
    # own, bypassing the permission system) and must never crash (nonzero).
    passed = (got == expected) and (rc == 0)
    return passed, f"{desc}: {cmd!r} (expected {expected}, got {got}, rc={rc})"


def _raw_case(desc: str, raw: str, expected: str) -> tuple[bool, str]:
    rc, out = _run("Bash", {}, raw_stdin=raw)
    got = _decision(out)
    passed = (got == expected) and (rc == 0)
    return passed, f"{desc} (expected {expected}, got {got}, rc={rc})"


# --- scenarios ------------------------------------------------------------


def run() -> list[tuple[bool, str]]:
    r: list[tuple[bool, str]] = []

    # === Attack 1: rm -rf on broad paths → ask ===
    r.append(_bash_case("rm -rf /", "rm -rf /", "ask"))
    r.append(_bash_case("rm -rf $HOME", "rm -rf $HOME", "ask"))
    r.append(_bash_case("rm -rf ~", "rm -rf ~/", "ask"))
    r.append(_bash_case("rm -fr (flag order)", "rm -fr /var/www", "ask"))
    r.append(_bash_case("rm -rf with var expansion", 'rm -rf "$DIR"/', "ask"))
    r.append(_bash_case("rm -r -f (separate flags)", "rm -r -f /tmp/x", "ask"))
    r.append(_bash_case("rm -f -r (separate, reversed)", "rm -f -r /tmp/x", "ask"))
    r.append(_bash_case("rm -rf after && separator", "cd /tmp && rm -rf build", "ask"))
    # rm -r alone (recursive, NOT forced) is intentionally NOT in v1 denylist:
    r.append(_bash_case("rm -r alone → not in v1", "rm -r dir/", "passthrough"))

    # === Attack 2: git force-push / direct main push → ask ===
    r.append(_bash_case("git push --force", "git push --force origin main", "ask"))
    r.append(_bash_case("git push -f", "git push -f", "ask"))
    r.append(_bash_case("git push + refspec", "git push origin +HEAD:main", "ask"))
    r.append(_bash_case("git push origin main (direct)", "git push origin main", "ask"))
    r.append(_bash_case("git push origin master", "git push origin master", "ask"))

    # === Attack 5: destructive SQL / wp-cli → ask ===
    r.append(_bash_case("DROP TABLE", "mysql -e 'DROP TABLE users'", "ask"))
    r.append(_bash_case("DROP DATABASE", 'mysql -e "DROP DATABASE prod"', "ask"))
    r.append(_bash_case("TRUNCATE", "mysql -e 'TRUNCATE TABLE orders'", "ask"))
    r.append(_bash_case("wp db reset", "wp db reset --yes", "ask"))
    r.append(_bash_case("wp db drop", "wp db drop --yes", "ask"))

    # === RULES.md rule 10: redis/cache flush (destroys VAD exclusions) → ask ===
    r.append(_bash_case("redis-cli FLUSHALL", "redis-cli FLUSHALL", "ask"))
    r.append(_bash_case("redis-cli FLUSHDB", "redis-cli FLUSHDB", "ask"))
    r.append(_bash_case("wp cache flush", "wp cache flush", "ask"))

    # === False positives (MUST NOT match; guard stays silent → passthrough, so the
    # user's normal permission flow decides — the guard never forces `allow` and
    # never blocks legit work). These are the cases that tempt a looser regex. ===
    r.append(_bash_case("git status (benign)", "git status", "passthrough"))
    r.append(_bash_case("git push normal branch", "git push origin feature/foo", "passthrough"))
    r.append(_bash_case("git log", "git log --oneline -5", "passthrough"))
    r.append(_bash_case("ls", "ls -la", "passthrough"))
    r.append(_bash_case("rm single file (no -rf)", "rm foo.txt", "passthrough"))
    r.append(_bash_case("grep for 'DROP TABLE' in code", "grep -rn 'DROP TABLE' src/", "passthrough"))
    r.append(_bash_case("echo mentions rm -rf", "echo 'never run rm -rf /'", "passthrough"))
    # 'main' appearing as a path/word, not a push target:
    r.append(_bash_case("cat src/main.ts", "cat src/main.ts", "passthrough"))

    # === Fail-OPEN invariants (the guard must never brick the session) ===
    r.append(_raw_case("malformed JSON stdin → passthrough (fail open)",
                       "{not valid json", "passthrough"))
    r.append(_raw_case("empty stdin → passthrough", "", "passthrough"))
    # Non-Bash tool → guard does not apply → passthrough
    rc, out = _run("Read", {"file_path": "/etc/passwd"})
    r.append(((_decision(out) == "passthrough") and rc == 0,
              f"non-Bash tool (Read) → passthrough (got {_decision(out)}, rc={rc})"))
    # Bash with no command key → passthrough (nothing to match), never crash
    rc, out = _run("Bash", {})
    r.append(((_decision(out) == "passthrough") and rc == 0,
              f"Bash with no command → passthrough (got {_decision(out)}, rc={rc})"))

    # === The guard must NEVER exit 2 on any input (exit 2 blocks unconditionally) ===
    rc, _ = _run("Bash", {"command": "rm -rf /"})
    r.append((rc == 0, f"never exit 2 even on worst command (rc={rc})"))

    return r


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
