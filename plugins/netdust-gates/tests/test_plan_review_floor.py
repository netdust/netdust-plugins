"""test_plan_review_floor.py — the plan-review floor in the PreToolUse guard.

A plan that is OPEN on this branch (uncommitted, or committed here but not on the
production rung) must carry `specs/<f>/plan-review.md` naming the plan's current git
blob (`Reviewed-plan: <sha>`) before product code is written. The review is a subagent's
artifact (`/plan-review`); the guard checks the file, never the transcript.

Product code = anything outside specs/, memory/, tasks/, docs/. Writing the plan, the
review, notes or the ledger is never refused — that is how the review gets written.

Legacy plans already on the production rung are not this branch's work and are ignored.
Fails OPEN on anything the guard cannot read.
"""

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "pretooluse-guard.py"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=T", *args],
                          cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def _blob(text: str) -> str:
    data = text.encode()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _repo(tmp: Path, *, plan: str | None = "# plan v1\n", review_for: str | None = None,
          plan_on_main: bool = False, site_yml: bool = True) -> Path:
    """A git repo on feature/x cut from main. `plan` writes specs/f/plan.md; `review_for`
    writes plan-review.md naming that text's blob; `plan_on_main` commits the plan on
    main first (a legacy plan)."""
    root = tmp / "proj"
    (root / "web").mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    if site_yml:
        (root / "site.yml").write_text(
            "environments:\n  staging:\n    branch: staging\n  production:\n    branch: main\n")
    (root / "web" / "index.php").write_text("<?php\n")
    if plan_on_main and plan is not None:
        (root / "specs" / "f").mkdir(parents=True)
        (root / "specs" / "f" / "plan.md").write_text(plan)
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "checkout", "-q", "-b", "feature/x")
    if plan is not None and not plan_on_main:
        (root / "specs" / "f").mkdir(parents=True, exist_ok=True)
        (root / "specs" / "f" / "plan.md").write_text(plan)
    if review_for is not None:
        (root / "specs" / "f").mkdir(parents=True, exist_ok=True)
        (root / "specs" / "f" / "plan-review.md").write_text(
            f"# Plan review\n\nReviewed-plan: {_blob(review_for)}\n\nVerdict: ready\n")
    return root


def _run(root: Path, tool: str, rel: str) -> tuple[int, str]:
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool,
                          "tool_input": {"file_path": str(root / rel), "content": "x"},
                          "cwd": str(root)})
    rr = subprocess.run(["python3", str(HOOK)], input=payload, capture_output=True,
                        text=True, timeout=20, env={**os.environ})
    return rr.returncode, rr.stdout


def _decision(stdout: str) -> str:
    if not stdout.strip():
        return "passthrough"
    try:
        return json.loads(stdout)["hookSpecificOutput"]["permissionDecision"]
    except Exception:  # noqa: BLE001
        return f"unparseable: {stdout!r}"


def _case(desc: str, expected: str, rel: str = "web/app/x.php", tool: str = "Write",
          reason_has: str | None = None, **repo_kw) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = _repo(Path(tmp), **repo_kw)
        rc, out = _run(root, tool, rel)
    got = _decision(out)
    ok = rc == 0 and got == expected
    if ok and reason_has is not None:
        ok = reason_has in out
    return ok, f"plan-review {desc}: {tool} {rel} -> {expected} (got {got}, rc={rc})"


def run() -> list[tuple[bool, str]]:
    v1 = "# plan v1\n"
    v2 = "# plan v2 — edited after review\n"
    r = [
        _case("(a) an open plan with no review: product write is DENIED, naming /plan-review",
              "deny", reason_has="/plan-review"),
        _case("(a') …and Edit is denied the same way", "deny", tool="Edit"),
        _case("(b) the review names the plan's current blob: passthrough",
              "passthrough", review_for=v1),
        _case("(c) the plan was edited after the review: denied again — a review is of a version",
              "deny", plan=v2, review_for=v1),
        _case("(d) writing the plan itself is never refused", "passthrough",
              rel="specs/f/plan.md"),
        _case("(d') writing the review itself is never refused", "passthrough",
              rel="specs/f/plan-review.md"),
        _case("(d'') memory/, tasks/, docs/ are not product code", "passthrough",
              rel="memory/STATE.md"),
        _case("(e) a legacy plan already on the production rung is ignored", "passthrough",
              plan_on_main=True),
        _case("(f) no plan at all (bounded work): passthrough", "passthrough", plan=None),
        _case("(g) no site.yml: the rung falls back to main and the floor still holds",
              "deny", site_yml=False),
    ]
    # (h) a repo the guard cannot read fails OPEN
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Write",
                          "tool_input": {"file_path": "/nonexistent/p/web/x.php"},
                          "cwd": "/nonexistent/p"})
    rr = subprocess.run(["python3", str(HOOK)], input=payload, capture_output=True, text=True, timeout=20)
    r.append((rr.returncode == 0 and _decision(rr.stdout) == "passthrough",
              "plan-review (h): an unreadable project fails OPEN"))
    return r


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
