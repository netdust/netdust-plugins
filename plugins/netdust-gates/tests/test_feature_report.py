"""test_feature_report.py — bin/feature-report.py writes specs/<feature>/report.md from plan.md
(the Test map and the tasks), shakeout.md and specs/CHECKS.md, one section per slice, every flow
joined to its test, its @e2e entry, its screenshot and its revert log; a missing join is a named
gap, never a guess; and one trial line per feature in specs/CHECKS.md, replaced on every run."""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "bin" / "feature-report.py"
FIXTURES = HERE / "fixtures" / "report"
LIST_LOG = "shakeout/tests__e2e__list.spec.ts--list-shows-rows.revert.txt"
FILTER_LOG = "shakeout/tests__e2e__list.spec.ts--list-filters-by-type.revert.txt"
DETAIL_LOG = "shakeout/tests__e2e__detail.spec.ts--detail-opens.revert.txt"


def _log(cls="assertion-failed") -> str:
    return (f"revert-run: {cls}\nfeature: feat\ntest: tests/e2e/list.spec.ts :: list shows rows\nbase: 0000000 (main)\n"
            f"swapped: src/list.php (M)\ncommand: npx playwright test\nexit: {0 if cls == 'passed' else 1}\n"
            "--- output: 1 lines, excerpt 1-1 ---\nError: expect(locator).toBeVisible() failed\n")


LOGS = {LIST_LOG: _log(), FILTER_LOG: _log()}


def _run(fixture="sliced", *, logs=LOGS, edit=None, runs=1):
    """Copy the fixture tree, write the case's revert logs into it, run the script, read what it wrote."""
    if not SCRIPT.exists():
        return 127, f"no script at {SCRIPT}", "", ""
    with tempfile.TemporaryDirectory(prefix="feature-report-") as tmp:
        root = Path(tmp)
        shutil.copytree(FIXTURES / fixture, root, dirs_exist_ok=True)
        feature = root / "specs" / "feat"
        for rel, text in (logs or {}).items():
            (feature / rel).parent.mkdir(parents=True, exist_ok=True)
            (feature / rel).write_text(text)
        if edit:
            edit(root)
        for _ in range(runs):
            proc = subprocess.run([sys.executable, str(SCRIPT), "specs/feat"], cwd=root, capture_output=True, text=True, timeout=30)
        report = (feature / "report.md").read_text() if (feature / "report.md").is_file() else ""
        checks = (root / "specs" / "CHECKS.md").read_text() if (root / "specs" / "CHECKS.md").is_file() else ""
        return proc.returncode, proc.stdout + proc.stderr, report, checks


def _case(desc, fixture="sliced", *, rc=0, has=(), lacks=(), checks_has=(), checks_count=None, **kw):
    got, out, report, checks = _run(fixture, **kw)
    ok = (got == rc and all(s in report for s in has) and not any(s in report for s in lacks)
          and all(s in checks for s in checks_has)
          and (checks_count is None or checks.count(checks_count[0]) == checks_count[1]))
    missing = [s for s in has if s not in report] + [f"checks:{s}" for s in checks_has if s not in checks]
    return ok, f"{desc} (rc {got}, expected {rc}{'; missing ' + repr(missing) if missing else ''}{'; out ' + out[-160:] if got != rc else ''})"


def _section(report: str, heading: str) -> str:
    m = re.search(rf"(?ms)^## {re.escape(heading)}.*?(?=^## |\Z)", report)
    return m.group(0) if m else ""


def _two_slices():
    got, out, report, _ = _run()
    s1, s2 = _section(report, "Slice 1"), _section(report, "Slice 2")
    ok = (got == 0 and s1 and s2 and "Task 1:" in s1 and "Task 2:" in s1 and "Task 3:" in s2 and "Task 3:" not in s1
          and "List shows rows" in s1 and "Detail opens" in s2 and "Detail opens" not in s1
          and "GAP" in report and "`Exporter`" in report and "matches no task" in report)
    return ok, f"test_two_slices_two_sections: one section per slice, its tasks and flows, the orphan Test map row a named gap (rc {got})"


def _flow_links():
    got, _, report, _ = _run()
    line = next((ln for ln in report.splitlines() if ln.lstrip("- ").startswith("List shows rows")), "")
    ok = (got == 0 and "tests/e2e/list.spec.ts :: list shows rows" in line and "rows list" in line
          and "/wp/wp-admin/admin.php?page=rows" in line and "shakeout/list.png" in line
          and "assertion-failed" in line and LIST_LOG in line)
    return ok, f"a flow line links its test, its @e2e entry, its screenshot and its revert log (got {line[:200]!r})"


def _no_review_commit(root: Path) -> None:
    pass


def run() -> list[tuple[bool, str]]:
    return [
        _two_slices(),
        _flow_links(),
        _case("test_unsliced_plan_is_one_section", "plain", has=("## The feature", "Task 1:", "Task 2:", "List shows rows"),
              lacks=("## Slice",), logs={LIST_LOG: _log()}),
        _case("test_lists_accepted_rows_and_hunt_lines",
              has=("## Accepted by the human", "AF-4", "the export needs the cron", "## The hunt",
                   "Hunt: 3 charters · 1 confirmed · 1 not ours · 1 rejected", "not ours: the footer's privacy link 404s",
                   "rejected: rows sort by id")),
        _case("test_missing_revert_is_a_named_gap: the detail test is new and has no log",
              has=("GAP", "Detail opens", DETAIL_LOG)),
        _case("…a passed log is a named gap too", logs={**LOGS, DETAIL_LOG: _log("passed")},
              has=("GAP", "Detail opens", "passed")),
        _case("test_trial_line_is_replaced_not_appended: two runs, one line", runs=2,
              checks_has=("## Trial log", "feat · revert-passed:"), checks_count=("feat · revert-passed:", 1)),
        _case("test_counts_follow_the_log_classes: passed and error logs are counted, gaps too",
              logs={**LOGS, DETAIL_LOG: _log("error"), "shakeout/tests__e2e__extra.spec.ts--extra.revert.txt": _log("passed")},
              checks_has=("feat · revert-passed: 1 · revert-errors: 1 · report-gaps: 2",)),
        _case("…the registry's table survives the trial log", checks_has=("| rows list | e2e |",)),
        _case("test_reads_artifacts_only: a flow with no manifest row, a row with no Test:, a test with no @e2e row, no review.md commit — each says missing or GAP, never a guess",
              edit=lambda root: (
                  (root / "specs/feat/plan.md").write_text((root / "specs/feat/plan.md").read_text().replace("| Detail opens |", "| Detail opens · Detail prints |")),
                  (root / "specs/feat/shakeout.md").write_text((root / "specs/feat/shakeout.md").read_text().replace(
                      "Test: tests/e2e/list.spec.ts :: list filters by type · ", "")),
                  (root / "specs/CHECKS.md").write_text((root / "specs/CHECKS.md").read_text().replace(
                      "| row detail | e2e | /rows/<id>/ | `tests/e2e/detail.spec.ts` | feat | 0000000 2026-11-06 |\n", ""))),
              has=("GAP: Detail prints", "no manifest row", "GAP: List filters by type", "no `Test:`", "@e2e: missing", "Close: missing")),
        _case("a feature dir with no plan.md exits 1", rc=1, edit=lambda root: (root / "specs/feat/plan.md").unlink()),
        _case("the report says it is generated and from which artifacts", has=("feature-report.py", "plan.md", "shakeout.md", "CHECKS.md")),
    ]
