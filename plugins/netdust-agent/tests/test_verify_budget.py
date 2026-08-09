"""
test_verify_budget.py — the verification-effort telemetry line (bin/verify-budget.py).

Re-contracted 2026-08-09 (deliverable-first FR-10, the one permitted existing-test edit
per SC-6): the script REPORTS, it never halts. The load-bearing cases, in the order they
matter:

  1. It exits 0 on EVERY input — above ceiling, below ceiling, unmeasurable. The HALT
     mechanic was removed by human decision ("am i supposed to say stop coding?"); the
     structural controls on runaway verification are the deliverable-first gate and the
     behaviour clusters in gate-check.py, not an interrupt from this script.
  2. It still MEASURES exactly as before — same ratio, same ceilings, same stakes
     resolution, same exclusions. An over-ceiling range is marked `[over-ceiling]` on the
     one-line report; the dial changes what is REPORTED, never whether the run continues.
  3. Small diffs stay under the measurement floor and draw no `[over-ceiling]` marker.
  4. It fails OPEN on any git/tooling problem — with NO opinion: no report line, no PASS,
     just a cannot-measure notice. A tooling failure must never read as a verdict
     (calibration: the C1 false-green on the master-default repo shape).
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

# Every field the JSON payload carried before the FR-10 demotion. Consumers parse these;
# the demotion changed the exit code and the human line, never the JSON shape.
JSON_FIELDS = {"range", "stakes", "stakes_source", "ceiling", "test_lines",
               "impl_lines", "ratio", "below_measurement_floor", "halt"}


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

    # 1. THE DEMOTION CONTRACT (FR-10 / AC-6). 2000 test lines over 200 implementation
    #    lines is 10×, on a feature the plan itself calls `low` — the contact-page-8k
    #    shape. The script REPORTS it and exits 0: one line, `[over-ceiling]` marked,
    #    nothing halted, no human summoned.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 0
                    and "verify-ratio: ratio=10.00" in out
                    and "ceiling=1.0" in out and "stakes=low" in out
                    and "impl=+200" in out and "test=+2000" in out
                    and "[over-ceiling]" in out,
                    "an above-ceiling range exits 0 and prints the one-line report "
                    "with [over-ceiling]"))

    # ...and the interrupt mechanic is GONE: no HALT string in any output (contract
    # case d), no three-causes lecture, no stop instruction.
    results.append(("HALT" not in out and "STOP" not in out,
                    "the HALT mechanic is deleted — no HALT/STOP in over-ceiling output"))

    # 2. Under the ceiling: same exit code, same report shape, no marker. The ratio
    #    computation and the stakes dial are unchanged — 3.5× is inside `high`'s 4.0×.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="high")
    rc, out = _run(repo, spec)
    results.append((rc == 0
                    and "verify-ratio: ratio=3.50" in out
                    and "ceiling=4.0" in out and "stakes=high" in out
                    and "[over-ceiling]" not in out and "HALT" not in out,
                    "an under-ceiling range exits 0 with the same report shape, "
                    "no marker, no HALT"))

    # ...and the SAME 3.5× at `low` is marked over-ceiling — the dial still does its
    # only job, it just reports instead of interrupting.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 0 and "[over-ceiling]" in out and "stakes=low" in out,
                    "the same 3.5× at `low` is marked [over-ceiling] — and still exits 0"))

    # 2b. The --json payload keeps every pre-demotion field (contract case c) — including
    #     the legacy `halt` boolean, which still computes but no longer exits non-zero.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    rc, out = _run(repo, spec, "--json")
    payload = json.loads(out)
    results.append((rc == 0 and set(payload) == JSON_FIELDS
                    and payload["halt"] is True and payload["ratio"] == 10.0,
                    "--json keeps all pre-demotion fields (incl. `halt`) and exits 0 "
                    "even when over ceiling"))

    # 3. Below the measurement floor, no marker. A 20-line test over a 2-line fix is 10×
    #    and is not a runaway; the floor keeps the telemetry honest about tiny diffs.
    repo, spec = _repo(test_lines=20, impl_lines=2, stakes="low")
    rc, out = _run(repo, spec, "--json")
    payload = json.loads(out)
    results.append((rc == 0 and payload["below_measurement_floor"] is True
                    and payload["halt"] is False,
                    "a tiny diff at 10× stays under the measurement floor — no marker"))

    # 4. Missing `Stakes:` line → fall back to standard, and SAY so in the JSON source
    #    field. A silent default is how two gates end up disagreeing about a feature.
    repo, spec = _repo(test_lines=1000, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text("# Implementation Plan: Contact page\n\nNo dial here.\n")
    rc, out = _run(repo, spec, "--json")
    payload = json.loads(out)
    results.append((rc == 0 and payload["stakes"] == "standard"
                    and "pre-0.16" in payload["stakes_source"],
                    "a plan with no `Stakes:` line falls back to standard, visibly"))

    # 4b. F3 — a punctuated reason parses to the DECLARED level, same as gate-check.py's
    #     tolerant parsing: `Stakes: low (a lost lead)` is level `low`, not a fallback.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text(
        "# Implementation Plan: Contact page\n\n## Stakes  [GATE]\n"
        "Stakes: low (a lost lead, no money or data at risk)\n")
    rc, out = _run(repo, spec)
    results.append((rc == 0 and "stakes=low" in out and "[over-ceiling]" in out,
                    "F3: `Stakes: low (reason)` parses to level `low` in verify-budget too"))

    # 4c. F3 — ...and a mangled token never silently READS as a level. `low-ish` is
    #     unreadable → fall back to standard, loudly, instead of parsing its prefix.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text(
        "# Implementation Plan: Contact page\n\n## Stakes  [GATE]\nStakes: low-ish — eh\n")
    rc, out = _run(repo, spec, "--json")
    payload = json.loads(out)
    results.append((payload["stakes"] == "standard"
                    and "unreadable level `low-ish`" in payload["stakes_source"],
                    "F3: an unreadable token falls back to standard visibly, never "
                    "parses as its prefix"))

    # 4d. F3 — a FENCED `Stakes:` example (the plan quoting the template) is not a
    #     declared level. The real line below the fence must win: this plan is `low`, so
    #     3.5× is marked over-ceiling. Without fence-stripping the fenced `high` is read
    #     first and the marker never appears.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    (spec / "plan.md").write_text(
        "# Implementation Plan: Contact page\n\nThe template, quoted:\n\n"
        "```\nStakes: high — money on the line\n```\n\n"
        "## Stakes  [GATE]\nStakes: low — a lost lead at worst\n")
    rc, out = _run(repo, spec)
    results.append((rc == 0 and "stakes=low" in out and "[over-ceiling]" in out,
                    "F3: a fenced `Stakes:` sample is ignored — the real level is read"))

    # 4e. I7 — a test-only range (zero implementation lines) has no finite ratio; it
    #     reports `ratio=inf`, marked over-ceiling once past the floor, and STILL exits 0.
    repo, spec = _repo(test_lines=300, impl_lines=0, stakes="low")
    rc, out = _run(repo, spec)
    results.append((rc == 0 and "ratio=inf" in out and "[over-ceiling]" in out
                    and "HALT" not in out,
                    "I7: a test-only diff reports ratio=inf with [over-ceiling], exit 0"))

    # 5. --stakes overrides the plan without editing it (Class C/D/E work has no plan at
    #    all) — visible in the JSON source field.
    repo, spec = _repo(test_lines=700, impl_lines=200, stakes="low")
    rc, out = _run(repo, None, "--stakes", "high", "--json")
    payload = json.loads(out)
    results.append((rc == 0 and payload["stakes"] == "high"
                    and payload["stakes_source"] == "--stakes override",
                    "--stakes overrides the plan and works with no feature dir"))

    # 6. Fail OPEN on a bad range, with NO opinion: an unknown revision must never READ
    #    as a verdict — no PASS, and no telemetry line either (a measurement that did
    #    not happen must not report a number).
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(spec), "--base", "no-such-ref", "--repo", str(repo)],
        capture_output=True, text=True, timeout=60)
    results.append((proc.returncode == 0 and "cannot read the diff" in proc.stderr
                    and "BUDGET: PASS" not in proc.stdout
                    and "verify-ratio:" not in proc.stdout,
                    "an unresolvable git ref fails OPEN (exit 0), never blocks on tooling, "
                    "never prints PASS or a ratio line"))

    # 6b. C1 — an EMPTY --base (a caller's `$(git merge-base HEAD main)` on a repo with no
    #     `main` expands to nothing) must be cannot-measure, NOT a verdict. Before the fix,
    #     "" became the range `...HEAD` → empty diff → a false green on the exact
    #     master-default repo shape this telemetry exists to catch.
    repo, spec = _repo(test_lines=2000, impl_lines=200, stakes="low")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(spec), "--base", "", "--repo", str(repo)],
        capture_output=True, text=True, timeout=60)
    results.append((proc.returncode == 0
                    and "cannot determine base ref" in proc.stderr
                    and "budget not measured" in proc.stderr
                    and "BUDGET: PASS" not in proc.stdout
                    and "verify-ratio:" not in proc.stdout,
                    "C1: an empty --base exits 0 with a cannot-measure notice and NEVER "
                    "prints PASS or a ratio line"))

    # 6c. C1 — the call sites' base-resolution chain (main → master → origin/HEAD) on a
    #     MASTER-default repo (the Daan incident shape). The snippet below is the one
    #     integration.md / shakeout.md document verbatim; it must find `master`, and the
    #     known over-ratio range must then be MEASURED and marked, never silently
    #     unmeasurable.
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
    results.append((resolved == "master" and rc == 0 and "[over-ceiling]" in out,
                    "C1: on a master-default repo the documented resolution chain finds "
                    "`master` and the over-ratio range is measured and marked"))

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
