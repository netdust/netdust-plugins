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
  - everything else / non-Bash   → passthrough (exit 0, no stdout = proceed)

Bash patterns deliberately never emit "deny" — "ask" already stops the
autonomous/injected case. The one deny tier is the upstream-invocation floor
on Write (seam artifacts require their superpowers skill in the transcript),
pinned in the cases at the bottom of this file.

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
import os
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
    """Parse the hook's stdout → 'allow'|'ask'|'deny', or
    'passthrough' if empty (proceed). 'unparseable'/'malformed' surface
    structural bugs."""
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


def _upstream_case(desc: str, relpath: str, expected: str, *,
                   invoked: list[str] = [], target_exists: bool = False,
                   content: str = "# spec", transcript: str | None = "auto",
                   expect_named: str | None = None) -> tuple[bool, str]:
    """Drive the upstream-invocation floor: Write to specs/<f>/<file> with a
    controlled transcript. transcript='auto' builds a JSONL carrying one Skill
    tool_use per name in `invoked`; None omits transcript_path entirely;
    any other string is used as the (possibly bogus) path."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        if target_exists:
            target.write_text("existing")
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": str(target), "content": content},
            "cwd": tmp,
        }
        if transcript == "auto":
            tp = Path(tmp) / "transcript.jsonl"
            lines = []
            for name in invoked:
                lines.append(json.dumps({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Skill", "input": {"skill": name}}]}}))
            lines.append(json.dumps({"type": "user", "message": {"content": "hello"}}))
            tp.write_text("\n".join(lines) + "\n")
            payload["transcript_path"] = str(tp)
        elif transcript is not None:
            payload["transcript_path"] = transcript
        result = subprocess.run(["python3", str(HOOK)], input=json.dumps(payload),
                                capture_output=True, text=True, timeout=10)
        got = _decision(result.stdout)
        passed = (got == expected) and (result.returncode == 0)
        if passed and expect_named and expected == "deny":
            obj = json.loads(result.stdout)
            passed = expect_named in obj["hookSpecificOutput"]["permissionDecisionReason"]
        return passed, f"{desc} (expected {expected}, got {got}, rc={result.returncode})"


# --- scenarios ------------------------------------------------------------


def _flow_repo(tmp: Path, branch: str, *, site_yml: bool = True, reader: bool = True) -> None:
    """A throwaway flow project: site.yml (three rungs), optionally a scripts/site
    reader, a git repo checked out on `branch`."""
    if site_yml:
        (tmp / "site.yml").write_text(
            "site: {name: t}\nenvironments:\n"
            "  development: {branch: development}\n  staging: {branch: staging}\n"
            "  production: {branch: main, confirm: true}\n")
    if reader:
        (tmp / "scripts").mkdir(exist_ok=True)
        (tmp / "scripts" / "site").write_text(
            "#!/usr/bin/env python3\nimport sys\n"
            "k=sys.argv[1]\nb={'environments.development.branch':'development',"
            "'environments.staging.branch':'staging','environments.production.branch':'main'}\n"
            "print('development\\nstaging\\nproduction') if k=='environments' else print(b[k])\n")
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(tmp), "PATH": os.environ.get("PATH", "")}
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=tmp, env=env, check=True)
    (tmp / "README").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp, env=env, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp, env=env, check=True)


def _flow_case(desc: str, branch: str, cmd: str, expected: str, **repo_kw) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        _flow_repo(Path(tmp), branch, **repo_kw)
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                              "tool_input": {"command": cmd}, "cwd": tmp})
        result = subprocess.run(["python3", str(HOOK)], input=payload,
                                capture_output=True, text=True, timeout=20)
    got = _decision(result.stdout) if result.returncode == 0 else f"exit{result.returncode}"
    ok = got == expected and (expected != "deny" or "make " in result.stdout)
    return ok, f"flow {desc}: on {branch!r}, {cmd!r} -> {expected} (got {got})"


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

    # === The upstream-invocation floor (2026-08-10): superpowers is the workhorse,
    # and prose alone never made the invocation happen — three sessions in three
    # days authored specs/plans without loading the upstream skill. Creating a
    # seam artifact without its upstream skill in the transcript → deny, with the
    # reason NAMING the skill so the agent self-corrects in one tool call. ===
    r.append(_upstream_case("new spec.md without brainstorming → deny naming it",
                            "specs/f/spec.md", "deny",
                            expect_named="superpowers:brainstorming"))
    r.append(_upstream_case("new spec.md WITH brainstorming invoked → passthrough",
                            "specs/f/spec.md", "passthrough",
                            invoked=["superpowers:brainstorming"]))
    r.append(_upstream_case("new plan.md without writing-plans → deny naming it",
                            "specs/f/plan.md", "deny",
                            invoked=["superpowers:brainstorming"],
                            expect_named="superpowers:writing-plans"))
    r.append(_upstream_case("new tasks.md without writing-plans → deny",
                            "specs/f/tasks.md", "deny",
                            expect_named="superpowers:writing-plans"))
    r.append(_upstream_case("new plan.md WITH writing-plans invoked → passthrough",
                            "specs/f/plan.md", "passthrough",
                            invoked=["superpowers:writing-plans"]))
    r.append(_upstream_case("EXISTING spec.md, no invocation → passthrough (edit, not create)",
                            "specs/f/spec.md", "passthrough", target_exists=True))
    r.append(_upstream_case("waiver comment in content → passthrough",
                            "specs/f/spec.md", "passthrough",
                            content="<!-- upstream: waived — Class B freshness -->\n# spec"))
    r.append(_upstream_case("no transcript_path in payload → passthrough (fail open)",
                            "specs/f/spec.md", "passthrough", transcript=None))
    r.append(_upstream_case("unreadable transcript_path → passthrough (fail open)",
                            "specs/f/spec.md", "passthrough",
                            transcript="/nonexistent/t.jsonl"))
    r.append(_upstream_case("Write outside specs/ → floor does not apply",
                            "docs/notes.md", "passthrough"))
    r.append(_upstream_case("review doc inside specs/ dir → floor does not apply",
                            "specs/f/review-A.md", "passthrough"))

    # -- the flow floor (harness-inversion FR-24, T13): deny x 10, allow x 4, fail-open x 2
    r += [
        _flow_case("(a) commit on the integration rung", "development", "git commit -m 'x'", "deny"),
        _flow_case("(b) hand merge into the review rung", "staging", "git merge feature/x", "deny"),
        _flow_case("(b2) switch-then-merge from a feature branch", "feature/x",
                   "git checkout development && git merge feature/x", "deny"),
        _flow_case("(c) push of a rung by name", "feature/x", "git push origin development", "deny"),
        _flow_case("(c2) bare push while on a rung", "main", "git push", "deny"),
        _flow_case("(d) checkout -b off a rung", "development", "git checkout -b feature/y", "deny"),
        _flow_case("(d2) switch -c off a rung", "staging", "git switch -c feature/y", "deny"),
        _flow_case("(e) piped yes into make ship", "main", "echo yes | make ship", "deny"),
        _flow_case("(e2) here-string into make release", "staging", "make release <<< yes", "deny"),
        _flow_case("(e3) branch -D of a rung", "feature/x", "git branch -D staging", "deny"),
        _flow_case("(f) commit on a feature branch", "feature/x", "git commit -m 'x'", "passthrough"),
        _flow_case("(f2) push of a feature branch", "feature/x", "git push -u origin feature/x", "passthrough"),
        _flow_case("(f3) make finish itself is never inspected", "feature/x", "make finish", "passthrough"),
        _flow_case("(f4) a read on a rung", "main", "git log --oneline -5", "passthrough"),
        _flow_case("(g) no site.yml -> today's behaviour", "development", "git commit -m 'x'",
                   "passthrough", site_yml=False, reader=False),
        _flow_case("(h) scripts/site missing -> rungs read from site.yml", "staging",
                   "git commit -m 'x'", "deny", reader=False),
    ]
    # (i) unreadable cwd -> fail open
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                          "tool_input": {"command": "git commit -m x"}, "cwd": "/nonexistent/x/y"})
    rr = subprocess.run(["python3", str(HOOK)], input=payload, capture_output=True, text=True, timeout=20)
    r.append((rr.returncode == 0 and _decision(rr.stdout) == "passthrough",
                    "flow (i): an unreadable cwd fails OPEN"))

    return r


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
