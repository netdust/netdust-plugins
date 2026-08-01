"""
test_verify_budget.py — the verification-effort tripwire (bin/verify-budget.py).

The load-bearing cases, in the order they matter:

  1. A `low`-stakes feature carrying an auth subsystem's worth of tests HALTs. That is
     `contact-page-8k` reproduced in miniature, and it is the whole reason this script
     exists — before it, nothing in the machine could notice.
  2. The SAME diff at `high` stakes passes. The tripwire measures spend against declared
     consequence; it has no opinion about testing in the abstract, and if it grew one it
     would start firing on work that deserves its tests.
  3. Small diffs stay quiet. A tripwire that fires on ordinary work gets routed around,
     and a routed-around gate still costs a run while no longer informing.
  4. It fails OPEN on any git/tooling problem. Its only power is to interrupt a human;
     that power must never be exercised by accident.
"""
import atexit
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "bin" / "verify-budget.py"

PLAN = """# Implementation Plan: Contact page

## Stakes  [GATE]
Stakes: {level} — {reason}
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True,
                   capture_output=True, text=True, timeout=30)


def _repo(test_lines: int, impl_lines: int, stakes: str = "low",
          default_branch: str = "main"):
    """A throwaway repo with one commit on top of the default branch adding N test /
    M impl lines."""
    tmp = tempfile.mkdtemp()
    atexit.register(shutil.rmtree, tmp, ignore_errors=True)  # S3: no leaked tmp dirs
    repo = Path(tmp)
    _git(repo, "init", "-q", "-b", default_branch)
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")

    (repo / "README.md").write_text("base\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    # The feature lives on its own branch, as it does in the harness — `main...HEAD` is
    # empty when both refs point at the same commit.
    _git(repo, "checkout", "-q", "-b", "feat")

    spec_dir = repo / "specs" / "contact"
    spec_dir.mkdir(parents=True)
    (spec_dir / "plan.md").write_text(
        PLAN.format(level=stakes, reason="a lost lead, no money or data at risk"))

    if impl_lines:
        src = repo / "src"
        src.mkdir()
        (src / "contact.php").write_text(
            "\n".join(f"$line{i} = {i};" for i in range(impl_lines)) + "\n")

    tests = repo / "tests"
    tests.mkdir()
    (tests / "ContactTest.php").write_text(
        "\n".join(f"// assertion {i}" for i in range(test_lines)) + "\n")

    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "feature")
    return repo, spec_dir


def _run(repo: Path, spec_dir: Path | None, *extra: str):
    argv = [sys.executable, str(SCRIPT)]
    if spec_dir is not None:
        argv.append(str(spec_dir))
    argv += ["--base", "main", "--repo", str(repo), *extra]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout + proc.stderr


def run():
    results = []

    # 1. THE CALIBRATION CASE. 2000 test lines over 200 implementation lines is 10×, on a
    #    feature the plan itself calls `low`. HALT, and say what to do about it.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 1 and "BUDGET: HALT" in out and "10.00×" in out,
                    "a low-stakes feature at 10× test:impl HALTs"))

    # The HALT must route the human to a decision, not just complain. In particular it must
    # offer "the stakes line was wrong" FIRST — deleting tests is the wrong instinct and the
    # script must not leave room for it.
    results.append((("stakes line is wrong" in out
                     and "Do NOT resolve it by deleting" in out),
                    "the HALT names the three causes and forbids deleting tests"))

    # 2. The same diff at `high` stakes passes. Consequence is the measure, not volume.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="high")
    rc, out = _run(repo, spec)
    results.append((rc == 0 and "BUDGET: PASS" in out,
                    "3.5× passes at `high` stakes — consequence is the measure, not volume"))

    # ...and the SAME 3.5× fails at `low`, which is the dial doing its only job.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 1 and "BUDGET: HALT" in out,
                    "the same 3.5× HALTs at `low` — the dial is what changed, nothing else"))

    # 3. Below the measurement floor, stay quiet. A 20-line test over a 2-line fix is 10×
    #    and is not a runaway; firing here is how a tripwire loses its audience.
    repo, spec = _repo(test_lines=20, impl_lines=2, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 0 and "measurement floor" in out,
                    "a tiny diff at 10× stays quiet — under the measurement floor"))

    # 4. Missing `Stakes:` line → fall back to standard, and SAY so. A silent default is how
    #    two gates end up disagreeing about what a feature is.
    repo, spec = _repo(test_lines=1000, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text("# Implementation Plan: Contact page\n\nNo dial here.\n")
    rc, out = _run(repo, spec)
    results.append((rc == 1 and "stakes    standard" in out and "pre-0.16" in out,
                    "a plan with no `Stakes:` line falls back to standard, visibly"))

    # 4b. F3 — a punctuated reason parses to the DECLARED level, same as gate-check.py's
    #     tolerant parsing: `Stakes: low (a lost lead)` is level `low`, not a fallback.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text(
        "# Implementation Plan: Contact page\n\n## Stakes  [GATE]\n"
        "Stakes: low (a lost lead, no money or data at risk)\n")
    rc, out = _run(repo, spec)
    results.append((rc == 1 and "stakes    low" in out and "BUDGET: HALT" in out,
                    "F3: `Stakes: low (reason)` parses to level `low` in verify-budget too"))

    # 4c. F3 — ...and a mangled token never silently READS as a level. `low-ish` is
    #     unreadable → fall back to standard, loudly, instead of parsing its prefix.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text(
        "# Implementation Plan: Contact page\n\n## Stakes  [GATE]\nStakes: low-ish — eh\n")
    rc, out = _run(repo, spec)
    results.append(("stakes    standard" in out and "unreadable level `low-ish`" in out,
                    "F3: an unreadable token falls back to standard visibly, never "
                    "parses as its prefix"))

    # 4d. F3 — a FENCED `Stakes:` example (the plan quoting the template) is not a declared
    #     level. The real line below the fence must win: this plan is `low`, so 3.5× HALTs.
    #     Without fence-stripping the fenced `high` is read first and the tripwire sleeps.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text(
        "# Implementation Plan: Contact page\n\nThe template, quoted:\n\n"
        "```\nStakes: high — money on the line\n```\n\n"
        "## Stakes  [GATE]\nStakes: low — a lost lead at worst\n")
    rc, out = _run(repo, spec)
    results.append((rc == 1 and "stakes    low" in out and "BUDGET: HALT" in out,
                    "F3: a fenced `Stakes:` sample is ignored — the real level is read"))

    # 4e. I7 — a test-only range (zero implementation lines) has no ratio to judge and is
    #     a runaway shape by definition: still exit 1, with a DISTINCT message instead of
    #     a meaningless ∞-ratio comparison.
    repo, spec = _repo(test_lines=300, impl_lines=0, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 1 and "test-only range" in out and "BUDGET: HALT" in out,
                    "I7: a test-only diff HALTs with its own message, not an ∞ ratio"))

    # 5. --stakes overrides the plan without editing it (Class C/D/E work has no plan at all).
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    rc, out = _run(repo, None, "--stakes", "high")
    results.append((rc == 0 and "--stakes override" in out,
                    "--stakes overrides the plan and works with no feature dir"))

    # 6. Fail OPEN on a bad range. The script's only power is to interrupt a human; it must
    #    never spend that power on its own tooling failure. C1: fail-open is "no opinion" —
    #    an unknown revision must never READ as a verdict, so no "BUDGET: PASS" either.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(spec), "--base", "no-such-ref", "--repo", str(repo)],
        capture_output=True, text=True, timeout=60)
    results.append((proc.returncode == 0 and "cannot read the diff" in proc.stderr
                    and "BUDGET: PASS" not in proc.stdout,
                    "an unresolvable git ref fails OPEN (exit 0), never blocks on tooling, "
                    "never prints PASS"))

    # 6b. C1 — an EMPTY --base (a caller's `$(git merge-base HEAD main)` on a repo with no
    #     `main` expands to nothing) must be cannot-measure, NOT a verdict. Before the fix,
    #     "" became the range `...HEAD` → empty diff → "BUDGET: PASS" — the tripwire
    #     reporting green on the exact incident repo shape it exists to catch.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(spec), "--base", "", "--repo", str(repo)],
        capture_output=True, text=True, timeout=60)
    results.append((proc.returncode == 0
                    and "cannot determine base ref" in proc.stderr
                    and "budget not measured" in proc.stderr
                    and "BUDGET: PASS" not in proc.stdout,
                    "C1: an empty --base exits 0 with a cannot-measure notice and NEVER "
                    "prints PASS"))

    # 6c. C1 — the call sites' base-resolution chain (main → master → origin/HEAD) on a
    #     MASTER-default repo (the Daan incident shape). The snippet below is the one
    #     integration.md / shakeout.md document verbatim; it must find `master`, and the
    #     known over-ratio range must then HALT instead of being silently unmeasurable.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low",
                       default_branch="master")
    resolve = (
        "if git rev-parse --verify -q main >/dev/null; then BASE=main\n"
        "elif git rev-parse --verify -q master >/dev/null; then BASE=master\n"
        "else BASE=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null"
        " | sed 's|^origin/||'); fi\n"
        'echo "$BASE"\n')
    resolved = subprocess.run(
        ["bash", "-c", resolve], cwd=repo, capture_output=True, text=True, timeout=30
    ).stdout.strip()
    rc, out = 1, ""
    if resolved:  # only run the budget check with a real ref — that's the point
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(spec), "--base", resolved,
             "--repo", str(repo)], capture_output=True, text=True, timeout=60)
        rc, out = proc.returncode, proc.stdout + proc.stderr
    results.append((resolved == "master" and rc == 1 and "BUDGET: HALT" in out,
                    "C1: on a master-default repo the documented resolution chain finds "
                    "`master` and the over-ratio range HALTs"))

    # 6d. S5 — the php test-suffix match is case-SENSITIVE: `latest.php` and `contest.php`
    #     are implementation, not tests. Before the fix, IGNORECASE made `latest.php` end
    #     in "test.php", inflating the test side and deflating impl.
    repo, spec = _repo(test_lines=300, impl_lines=0, stakes="low")
    (repo / "latest.php").write_text(
        "\n".join(f"$latest{i} = {i};" for i in range(300)) + "\n")
    (repo / "contest.php").write_text(
        "\n".join(f"$contest{i} = {i};" for i in range(300)) + "\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "impl files with test-ish names")
    rc, out = _run(repo, spec, "--json")
    payload = json.loads(out)
    results.append((payload["test_lines"] == 300 and payload["impl_lines"] == 600,
                    "S5: latest.php / contest.php classify as implementation — the php "
                    "suffix match is case-sensitive"))

    # 7. Docs and the feature's own paperwork move the ratio in no direction — otherwise
    #    writing the plan would count against the plan's own budget.
    repo, spec = _repo(test_lines=300, impl_lines=300, stakes="low")
    (repo / "docs").mkdir()
    (repo / "docs" / "notes.md").write_text("\n".join(f"line {i}" for i in range(5000)) + "\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "docs")
    rc, out = _run(repo, spec, "--json")
    payload = json.loads(out)
    results.append((payload["test_lines"] == 300 and payload["impl_lines"] == 300,
                    "markdown and the feature's own spec/plan/tasks are excluded from both sides"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
