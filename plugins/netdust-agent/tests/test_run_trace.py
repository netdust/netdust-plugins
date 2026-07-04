"""Tests for spec-kit/run-trace.py — the single-writer run-log convergence point.

Contract (specs/run-observability/spec.md, specs/run-observability/tasks.md T01):
  - `append <feature-dir> <event> [k=v ...]` writes one timestamped JSON line to
    `<feature-dir>/run-log.jsonl`.
  - `show <feature-dir>` renders the log (human-readable).
  - Nonexistent feature dir -> append rejected, nonzero exit, one-line reason,
    NO file created.
  - Malformed k=v (missing `=`) -> exit nonzero.
  - `show` on empty/missing log -> clean "no trace recorded", exit 0 (not an error).
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_TRACE = Path(__file__).resolve().parent.parent / "spec-kit" / "run-trace.py"


def run_trace(*args: str) -> tuple[int, str, str]:
    p = subprocess.run(
        [sys.executable, str(RUN_TRACE), *args],
        capture_output=True, text=True, timeout=60,
    )
    return p.returncode, p.stdout, p.stderr


def log_path(feature_dir: Path) -> Path:
    return feature_dir / "run-log.jsonl"


def read_lines(feature_dir: Path) -> list[dict]:
    p = log_path(feature_dir)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def run() -> list[tuple[bool, str]]:
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    # --- append: one well-formed line with event+data+ts ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)

        rc, out, err = run_trace("append", str(feature), "stage-enter", "stage=execute")
        lines = read_lines(feature)

        case("append -> exit 0", rc == 0)
        case("append -> exactly one line written",
             len(lines) == 1)
        case("append -> line carries event name",
             len(lines) == 1 and lines[0].get("event") == "stage-enter")
        case("append -> line carries k=v data",
             len(lines) == 1 and lines[0].get("data", {}).get("stage") == "execute")
        case("append -> line carries a timestamp",
             len(lines) == 1 and bool(lines[0].get("ts")))

    # --- second append: two lines, order preserved ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)

        run_trace("append", str(feature), "first-event", "n=1")
        run_trace("append", str(feature), "second-event", "n=2")
        lines = read_lines(feature)

        case("second append -> two lines total", len(lines) == 2)
        case("second append -> order preserved (first then second)",
             len(lines) == 2
             and lines[0].get("event") == "first-event"
             and lines[1].get("event") == "second-event")

    # --- denial: nonexistent feature dir ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "does-not-exist"

        rc, out, err = run_trace("append", str(feature), "stage-enter", "stage=execute")

        case("append to nonexistent feature dir -> nonzero exit", rc != 0)
        case("append to nonexistent feature dir -> one-line reason on stdout/stderr",
             len([l for l in (out + err).splitlines() if l.strip()]) >= 1)
        case("append to nonexistent feature dir -> no file created",
             not log_path(feature).exists() and not feature.exists())

    # --- denial: malformed k=v (missing `=`) ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)

        rc, out, err = run_trace("append", str(feature), "stage-enter", "no-equals-sign")

        case("malformed k=v (missing '=') -> nonzero exit", rc != 0)
        case("malformed k=v -> no file created",
             not log_path(feature).exists())

    # --- denial: feature dir exists but is unwritable (permission denied) ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        feature.chmod(0o500)
        try:
            rc, out, err = run_trace("append", str(feature), "stage-enter", "stage=execute")
        finally:
            feature.chmod(0o700)  # restore so tempdir cleanup can remove it

        case("append to unwritable feature dir -> nonzero exit, no crash", rc == 1)
        case("append to unwritable feature dir -> one-line reason, no traceback",
             len([l for l in (out + err).splitlines() if l.strip()]) >= 1
             and "Traceback" not in (out + err))
        case("append to unwritable feature dir -> no file created",
             not log_path(feature).exists())

    # --- show: on missing log -> clean "no trace recorded", exit 0 ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)

        rc, out, err = run_trace("show", str(feature))

        case("show on missing log -> exit 0 (not an error)", rc == 0)
        case("show on missing log -> 'no trace recorded' message",
             "no trace recorded" in (out + err).lower())

    # --- show: on empty log file -> clean "no trace recorded", exit 0 ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text("")

        rc, out, err = run_trace("show", str(feature))

        case("show on empty log -> exit 0 (not an error)", rc == 0)
        case("show on empty log -> 'no trace recorded' message",
             "no trace recorded" in (out + err).lower())

    # --- show: renders an existing log human-readably ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        run_trace("append", str(feature), "stage-enter", "stage=execute")

        rc, out, err = run_trace("show", str(feature))

        case("show on populated log -> exit 0", rc == 0)
        case("show on populated log -> event name visible in rendered output",
             "stage-enter" in out)

    # --- show: a torn/malformed trailing line degrades cleanly ---
    # Simulates a process killed mid-`append` (partial JSON on the last
    # line). `show` must not crash — the docstring's "a missing or empty
    # log is not an error" contract extends to a corrupt line: render what
    # is valid and mark the bad line, but never traceback or exit nonzero.
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        run_trace("append", str(feature), "stage-enter", "stage=execute")
        with log_path(feature).open("a", encoding="utf-8") as f:
            f.write('{"ts": "x", "event": "trunc\n')  # torn line, no closing brace

        rc, out, err = run_trace("show", str(feature))

        case("show on torn trailing line -> exit 0 (not a crash)", rc == 0)
        case("show on torn trailing line -> valid line still rendered",
             "stage-enter" in out)

    return results
