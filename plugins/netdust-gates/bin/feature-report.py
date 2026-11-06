#!/usr/bin/env python3
"""feature-report.py — the feature report, generated from artifacts, never written.

    feature-report.py <feature dir>

Reads <feature dir>/plan.md (the Test map and the `### Task N[ · Slice M]:` headings),
<feature dir>/shakeout.md and specs/CHECKS.md, and writes <feature dir>/report.md: one section
per slice (a plan with none is one section), each listing what was built and the user flows of
its Test map rows; every flow joined to its manifest row (the `Flow` cell carrying the flow's name),
that row's `Test:` key to its `@e2e` registry row, its screenshot and its revert log. A flow with
no row, a row with no test, a new test with no `assertion-failed` log, a Test map row no task
heading carries: each is a named GAP. A cell an artifact lacks says `missing`; nothing is guessed.
It also writes one trial line per feature under `## Trial log` in specs/CHECKS.md, dated, replaced
on every run. Exit 0; 1 when the plan is missing. Bare python3; the manifest grammar, the
new-or-re-driven rule and the log's checks are imported from shakeout-check.py beside this file.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

_spec = importlib.util.spec_from_file_location("shakeout_check", Path(__file__).resolve().parent / "shakeout-check.py")
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

TASK = re.compile(r"^###\s*Task\s+(?P<n>\d+)(?:\s*·\s*Slice\s+(?P<slice>\d+))?\s*[:：]\s*(?P<title>.+?)\s*$")
HUNT_LINE = re.compile(r"^(?:-\s*)?(?P<kind>not ours|rejected):\s*(?P<text>.+)$")
NO_FLOWS = {"", "none", "—", "-", "n/a"}


def _plain(text: str) -> str:
    return text.replace("`", "").strip()


def parse_tasks(plan: str) -> list[dict]:
    tasks = []
    for ln in sc._unfenced(plan):
        m = TASK.match(ln)
        if m:
            tasks.append({"n": int(m.group("n")), "slice": int(m.group("slice")) if m.group("slice") else None,
                          "title": m.group("title").strip()})
    return tasks


def parse_test_map(plan: str) -> list[dict]:
    """Rows of the first pipe table after `## Test map`: the Unit cell and the E2E flows cell."""
    lines = sc._unfenced(plan)
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip().lower().startswith("## test map"))
    except StopIteration:
        return []
    index, rows = None, []
    for ln in lines[start + 1:]:
        if sc.TABLE_SEPARATOR.match(ln):
            continue
        cells = sc._cells(ln)
        if index is None:
            if cells:
                names = [c.lower() for c in cells]
                unit = next((i for i, h in enumerate(names) if h.startswith("unit")), 0)
                flows = next((i for i, h in enumerate(names) if "e2e" in h or "flow" in h), len(cells) - 1)
                index = (unit, flows)
            elif ln.startswith("## "):
                break
            continue
        if cells is None:
            if rows:
                break
            continue
        unit = cells[index[0]] if index[0] < len(cells) else ""
        cell = cells[index[1]] if index[1] < len(cells) else ""
        flows = [f.strip() for f in re.split(r"[·,;]", cell) if f.strip().lower() not in NO_FLOWS]
        rows.append({"unit": unit, "flows": flows})
    return rows


def _task_for(unit: str, tasks: list[dict]) -> dict | None:
    needle = _plain(unit)
    return next((t for t in tasks if needle and needle in _plain(t["title"])), None)


def _hunt(manifest: str) -> tuple[str | None, list[str]]:
    lines = sc._unfenced(manifest)
    tally = next((ln.strip() for ln in lines if sc.HUNT.match(ln)), None)
    notes = [f"{m.group('kind')}: {m.group('text').strip()}" for ln in lines for m in [HUNT_LINE.match(ln.strip())] if m]
    return tally, notes


def _close_minutes(root: Path, feature: str) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(root), "log", "--diff-filter=A", "--format=%ct", "--",
                               f"specs/{feature}/review.md"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        proc = None
    stamps = proc.stdout.split() if proc and proc.returncode == 0 else []
    if not stamps:
        return f"Close: missing (no commit adds specs/{feature}/review.md)"
    added = int(stamps[-1])
    return (f"Close: {round((time.time() - added) / 60)} minutes "
            f"(specs/{feature}/review.md added {datetime.fromtimestamp(added):%Y-%m-%d %H:%M} → this run)")


class Report:
    def __init__(self, spec_dir: Path):
        self.spec_dir, self.root, self.feature = spec_dir, spec_dir.parent.parent, spec_dir.name
        manifest = (spec_dir / "shakeout.md").read_text() if (spec_dir / "shakeout.md").is_file() else ""
        self.rows = sc.parse_rows(manifest) if manifest else []
        self.tally, self.hunt_notes = _hunt(manifest) if manifest else (None, [])
        self.registry = sc._registry_rows(spec_dir)
        self.e2e = {}
        for r in self.registry:
            if r["tier"].lower() == "e2e":
                self.e2e.setdefault(r["test"].strip("`"), []).append(f"{r['surface']} ({r['entry']})")
        self.gaps = 0

    def gap(self, text: str) -> str:
        self.gaps += 1
        return f"- GAP: {text}"

    def _row_for(self, flow: str) -> dict | None:
        needle = flow.lower()
        return next((r for r in self.rows if needle in r["flow"].lower()), None)

    def _revert(self, path: str, title: str) -> tuple[str, bool]:
        """The revert cell and whether it is a gap — the checker's rule, so the report never disagrees with `make shakeout`."""
        if sc.row_is_redriven(self.root, path, title, self.registry, self.feature):
            return "revert: re-driven, no proof owed", False
        problem = sc.log_problem(self.spec_dir, self.root, path, title)
        if problem:
            return f"revert: {problem}", True
        return f"revert: assertion-failed (shakeout/{sc.stem(path, title)}.revert.txt)", False

    def flow_line(self, flow: str) -> str:
        row = self._row_for(flow)
        if row is None:
            return self.gap(f"{flow} — no manifest row carries this flow")
        accepted = sc.ACCEPTED.search(row["evidence"])
        if accepted:
            return f"- {flow} — accepted by the human ({row['n']}): {accepted.group('reason').strip()}"
        m = sc.TEST.search(row["evidence"])
        if not m:
            return self.gap(f"{flow} — no `Test:` marker in its row ({row['n']})")
        path, title = m.group("path").strip("`"), m.group("title").strip()
        shot = sc.BROWSER_EVIDENCE.search(row["evidence"])
        cells = [f"test: {path} :: {title}",
                 "@e2e: " + ("; ".join(self.e2e[path]) if path in self.e2e else "missing"),
                 "screenshot: " + (shot.group("path") if shot else ("none (wire)" if row["layer"].lower() == "wire" else "missing"))]
        revert, is_gap = self._revert(path, title)
        if is_gap:
            return self.gap(f"{flow} — {revert} · " + " · ".join(cells))
        return f"- {flow} — " + " · ".join(cells + [revert])

    def render(self, tasks: list[dict], test_map: list[dict]) -> str:
        placed: dict[int | None, list[dict]] = {}
        unplaced: list[dict] = []
        for row in test_map:
            task = _task_for(row["unit"], tasks)
            (placed.setdefault(task["slice"], []) if task else unplaced).append({**row, "task": task})
        sliced = any(t["slice"] is not None for t in tasks)
        out = [f"# {self.feature} — feature report", "",
               f"Generated by `feature-report.py` from `plan.md`, `shakeout.md` and `specs/CHECKS.md` on {date.today():%Y-%m-%d}; "
               "nothing here is written by hand.", "", _close_minutes(self.root, self.feature), ""]
        slices = sorted({t["slice"] for t in tasks}, key=lambda s: (s is None, s or 0))
        for s in slices:
            out.append(f"## Slice {s}" if s is not None else ("## Unsliced tasks" if sliced else "## The feature"))
            out += ["", "Built:"] + [f"- Task {t['n']}: {t['title']}" for t in tasks if t["slice"] == s] + ["", "Flows:"]
            flows = [f for row in placed.get(s, []) for f in row["flows"]]
            out += [self.flow_line(f) for f in flows] or ["- none (no Test map row of this slice names a flow)"]
            out.append("")
        if unplaced:
            out += ["## Unplaced", ""]
            for row in unplaced:
                out.append(self.gap(f"Test map row `{_plain(row['unit'])}` matches no task heading"
                                    + (f" — its flows: {', '.join(row['flows'])}" if row["flows"] else "")))
                out += [self.flow_line(f) for f in row["flows"]]
            out.append("")
        accepted = [(r["n"], r["flow"], sc.ACCEPTED.search(r["evidence"]).group("reason").strip())
                    for r in self.rows if sc.ACCEPTED.search(r["evidence"])]
        out += ["## Accepted by the human", ""] + ([f"- {n} ({flow}): {reason}" for n, flow, reason in accepted] or ["none"]) + [""]
        out += ["## The hunt", ""] + ([self.tally] + [f"- {n}" for n in self.hunt_notes] if self.tally else ["no hunt line in the manifest"]) + [""]
        out += [f"## Gaps: {self.gaps}", ""]
        return "\n".join(out)

    def trial_counts(self) -> tuple[int, int]:
        logs = sorted((self.spec_dir / "shakeout").glob("*.revert.txt")) if (self.spec_dir / "shakeout").is_dir() else []
        firsts = [log.read_text().partition("\n")[0].strip() for log in logs]
        return firsts.count("revert-run: passed"), firsts.count("revert-run: error")


def write_trial_line(checks: Path, line: str, feature: str) -> None:
    """One dated line per feature under `## Trial log`, the feature's earlier line replaced."""
    mine = re.compile(rf"^\d{{4}}-\d\d-\d\d · {re.escape(feature)} · revert-passed:")
    text = checks.read_text() if checks.is_file() else "# Checks registry\n"
    lines = text.rstrip("\n").split("\n")
    if "## Trial log" not in lines:
        lines += ["", "## Trial log", ""]
    head = lines.index("## Trial log")
    end = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    section = [ln for ln in lines[head + 1:end] if not mine.match(ln)]
    while section and not section[-1].strip():
        section.pop()
    section = (section or [""]) + [line]
    checks.write_text("\n".join(lines[:head + 1] + section + lines[end:]) + "\n")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: feature-report.py <feature dir>", file=sys.stderr)
        return 2
    spec_dir = Path(argv[0])
    plan = spec_dir / "plan.md"
    if not plan.is_file():
        print(f"feature-report: no plan at {plan} — the report is generated from it", file=sys.stderr)
        return 1
    text = plan.read_text()
    report = Report(spec_dir)
    rendered = report.render(parse_tasks(text), parse_test_map(text))
    (spec_dir / "report.md").write_text(rendered)
    passed, errors = report.trial_counts()
    line = f"{date.today():%Y-%m-%d} · {spec_dir.name} · revert-passed: {passed} · revert-errors: {errors} · report-gaps: {report.gaps}"
    write_trial_line(spec_dir.parent / "CHECKS.md", line, spec_dir.name)
    print(f"report: {spec_dir / 'report.md'} ({report.gaps} gap(s)); trial log: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
