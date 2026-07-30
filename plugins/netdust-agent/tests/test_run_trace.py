"""Tests for bin/run-trace.py — the single-writer run-log convergence point.

Contract (specs/run-observability/spec.md, specs/run-observability/tasks.md T01):
  - `append <feature-dir> <event> [k=v ...]` writes one timestamped JSON line to
    `<feature-dir>/run-log.jsonl`.
  - `show <feature-dir>` renders the log (human-readable).
  - Nonexistent feature dir -> append rejected, nonzero exit, one-line reason,
    NO file created.
  - Malformed k=v (missing `=`) -> exit nonzero.
  - `show` on empty/missing log -> clean "no trace recorded", exit 0 (not an error).

T10 contract (specs/harness-efficiency/tasks.md T10, plan.md D5):
  - `show --durations` prints, AFTER the normal rendering, a segments table:
    header `── durations ──`, one row per consecutive pair of parseable
    events (`<event-a>[ <key data>] -> <event-b>[ <key data>]   <H:MM:SS>`),
    a `review-gate` row's key data includes `cluster=`/`tier=`, a
    `stage-enter` row's key data includes `stage=`, and a trailing
    `total (first -> last parseable event)  <H:MM:SS>` line.
  - Corrupt/unparseable-ts lines are skipped for segmentation purposes,
    consistent with `show`'s existing `<corrupt line>` degradation.
  - Fewer than 2 parseable (timestamped) events -> exactly
    `durations: not derivable (<2 timestamped events)`, exit 0.
  - WITHOUT `--durations`, output must be byte-identical to the pre-T10
    rendering (golden fixture captured before this task's implementation).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_TRACE = Path(__file__).resolve().parent.parent / "bin" / "run-trace.py"


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
    # chmod cannot deny root (permission bits are bypassed at euid 0), so in
    # root-run environments (remote containers) the RED condition never
    # materializes — skip, same convention as the suite's other env skips.
    if os.geteuid() == 0:
        case("append to unwritable feature dir: skipped (running as root — chmod cannot deny)", True)
    else:
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

    # =====================================================================
    # T10 — `show --durations` (specs/harness-efficiency/tasks.md T10,
    # plan.md D5). This flag does not exist in production yet: the
    # implementer's job is to make these cases pass with real segmentation
    # logic. Written RED-first by the test-author; DO NOT weaken.
    # =====================================================================

    # --- WITHOUT the flag: byte-identical to the pre-T10 golden fixture ---
    # This is the load-bearing regression guard: whatever segmentation logic
    # the implementer adds under --durations, the no-flag path must render
    # EXACTLY what it rendered before this task touched the file. The
    # fixture below is a literal capture of `show`'s output taken from the
    # pre-T10 production code — not re-derived from any post-change run.
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": "2026-07-05T10:00:00+00:00", "event": "stage-enter", "data": {"stage": "execute"}}\n'
            '{"ts": "2026-07-05T10:00:05+00:00", "event": "review-gate", "data": {"cluster": "C1", "tier": "STANDARD"}}\n'
            '{"ts": "2026-07-05T10:02:05+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
        )
        golden = (
            "2026-07-05T10:00:00+00:00 stage-enter {'stage': 'execute'}\n"
            "2026-07-05T10:00:05+00:00 review-gate {'cluster': 'C1', 'tier': 'STANDARD'}\n"
            "2026-07-05T10:02:05+00:00 stage-enter {'stage': 'review'}\n"
        )

        rc, out, err = run_trace("show", str(feature))

        case("show WITHOUT --durations -> exit 0", rc == 0)
        case("show WITHOUT --durations -> byte-identical to pre-T10 golden fixture",
             out == golden)

    # --- --durations: fixture log with known timestamps -> exact segment
    #     rows + total ---
    # stage-enter(10:00:00) -> review-gate(10:00:05): 0:00:05
    # review-gate(10:00:05) -> stage-enter(10:02:05): 0:02:00
    # total first->last: 10:00:00 -> 10:02:05 = 0:02:05
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": "2026-07-05T10:00:00+00:00", "event": "stage-enter", "data": {"stage": "execute"}}\n'
            '{"ts": "2026-07-05T10:00:05+00:00", "event": "review-gate", "data": {"cluster": "C1", "tier": "STANDARD"}}\n'
            '{"ts": "2026-07-05T10:02:05+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
        )

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (fixture log) -> exit 0", rc == 0)
        case("show --durations -> prints the '── durations ──' header",
             "── durations ──" in out)
        case("show --durations -> stage-enter row carries stage=",
             "stage=execute" in out and "stage=review" in out)
        case("show --durations -> review-gate row carries cluster=/tier=",
             "cluster=C1" in out and "tier=STANDARD" in out)
        case("show --durations -> segment 1 (stage-enter -> review-gate) delta is 0:00:05",
             any("stage-enter" in ln and "review-gate" in ln and "0:00:05" in ln
                 for ln in out.splitlines()))
        case("show --durations -> segment 2 (review-gate -> stage-enter) delta is 0:02:00",
             any("review-gate" in ln and "stage-enter" in ln and "0:02:00" in ln
                 for ln in out.splitlines()
                 if ln.strip() != "" and not ln.startswith("total")))
        case("show --durations -> total line present with first->last delta 0:02:05",
             any(ln.strip().startswith("total") and "0:02:05" in ln
                 for ln in out.splitlines()))

    # --- denial: single-event (parseable) log -> not derivable, exit 0 ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        run_trace("append", str(feature), "stage-enter", "stage=execute")

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (single event) -> exit 0", rc == 0)
        case("show --durations (single event) -> 'not derivable' message",
             "durations: not derivable (<2 timestamped events)" in (out + err))

    # --- corrupt line skipped: does not crash, excluded from segmentation ---
    # Two valid, parseable events plus one corrupt line in between. The
    # corrupt line must render as `<corrupt line>` (existing show behavior)
    # AND must not appear as, or break, a durations segment — segmentation
    # runs over the parseable events only, consistent with `show`'s
    # existing corrupt-line degradation.
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": "2026-07-05T10:00:00+00:00", "event": "stage-enter", "data": {"stage": "execute"}}\n'
            'not-json-at-all\n'
            '{"ts": "2026-07-05T10:00:30+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
        )

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (corrupt line present) -> exit 0, no crash", rc == 0)
        case("show --durations (corrupt line present) -> '<corrupt line>' still rendered",
             "<corrupt line>" in out)
        case("show --durations (corrupt line present) -> segment computed across the "
             "two parseable events (delta 0:00:30), corrupt line not a segment endpoint",
             any("stage-enter" in ln and "0:00:30" in ln for ln in out.splitlines()))
        case("show --durations (corrupt line present) -> total is 0:00:30",
             any(ln.strip().startswith("total") and "0:00:30" in ln
                 for ln in out.splitlines()))

    # --- empty/missing log + --durations: existing "no trace recorded"
    #     behavior unchanged (no durations section, no crash) ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (missing log) -> exit 0", rc == 0)
        case("show --durations (missing log) -> 'no trace recorded', unchanged",
             "no trace recorded" in (out + err).lower())
        case("show --durations (missing log) -> no durations header emitted",
             "── durations ──" not in out)

    # =====================================================================
    # C4 review-gate findings (additive; original author cases above are
    # unchanged) — timestamp/input robustness, FAMILY 1.
    # =====================================================================

    # --- (a) non-string ts value -> treated as unparseable (None), no crash ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": 12345, "event": "stage-enter", "data": {"stage": "execute"}}\n'
            '{"ts": "2026-07-05T10:00:05+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
        )

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (non-string ts) -> exit 0, no crash", rc == 0)
        case("show --durations (non-string ts) -> no traceback",
             "Traceback" not in (out + err))
        case("show --durations (non-string ts) -> not derivable "
             "(non-string ts line excluded, only 1 parseable event remains)",
             "durations: not derivable (<2 timestamped events)" in out)

    # --- (b) "data": null between two good events -> normalized to {},
    #     no crash in _format_event_label ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": "2026-07-05T10:00:00+00:00", "event": "stage-enter", "data": {"stage": "execute"}}\n'
            '{"ts": "2026-07-05T10:00:05+00:00", "event": "review-gate", "data": null}\n'
            '{"ts": "2026-07-05T10:02:05+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
        )

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (data: null) -> exit 0, no crash", rc == 0)
        case("show --durations (data: null) -> no traceback",
             "Traceback" not in (out + err))
        case("show --durations (data: null) -> review-gate row renders with "
             "no key data (bare event name, null normalized to {})",
             any("review-gate" in ln and "0:00:05" in ln for ln in out.splitlines()))

    # --- (c) naive timestamp (no Z/offset) -> rejected as unparseable
    #     (would otherwise crash on aware-comparison) ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": "2026-07-05T10:00:00", "event": "stage-enter", "data": {"stage": "execute"}}\n'
            '{"ts": "2026-07-05T10:00:05+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
        )

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (naive ts) -> exit 0, no crash", rc == 0)
        case("show --durations (naive ts) -> no traceback",
             "Traceback" not in (out + err))
        case("show --durations (naive ts) -> naive-ts line excluded, "
             "not derivable (<2 timestamped events)",
             "durations: not derivable (<2 timestamped events)" in out)

    # --- (d) out-of-order events in the run-log -> sorted before pairing,
    #     never a negative duration ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = Path(tmp) / "specs" / "demo"
        feature.mkdir(parents=True)
        log_path(feature).write_text(
            '{"ts": "2026-07-05T10:02:05+00:00", "event": "stage-enter", "data": {"stage": "review"}}\n'
            '{"ts": "2026-07-05T10:00:00+00:00", "event": "stage-enter", "data": {"stage": "execute"}}\n'
        )

        rc, out, err = run_trace("show", str(feature), "--durations")

        case("show --durations (out-of-order log) -> exit 0", rc == 0)
        case("show --durations (out-of-order log) -> no negative duration anywhere",
             not any("-1 day" in ln or ", -" in ln for ln in out.splitlines()))
        case("show --durations (out-of-order log) -> segment reflects sorted "
             "order (execute -> review), positive 0:02:05 delta",
             any("stage=execute" in ln and "stage=review" in ln and "0:02:05" in ln
                 for ln in out.splitlines()))

    return results
