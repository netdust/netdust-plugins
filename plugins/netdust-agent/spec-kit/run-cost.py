#!/usr/bin/env python3
"""
run-cost.py — per-dispatch / per-stage token-cost report (netdust-agent)

    usage: run-cost.py <feature-dir> [--transcript-dir <dir>]

Compiles token-usage totals from the LOCAL Claude Code session transcripts
(never from anything this repo writes) and, when available, attributes them
to the run's stage/gate segments recorded in `<feature-dir>/run-log.jsonl`
(specs/harness-efficiency/plan.md D6):

  Default transcript dir: `~/.claude/projects/<slug(cwd)>`, where <slug> is
  the absolute cwd with every `/` and `.` replaced by `-`. `--transcript-dir`
  overrides it (the default varies per machine).

  Inputs (ALL READ-ONLY — this tool never writes into the transcript dir):
    - every `*.jsonl` directly inside the transcript dir (main sessions)
    - every `<session>/subagents/agent-*.jsonl` (subagent dispatches), each
      paired with a sibling `agent-*.meta.json` carrying `agentType` and
      `description`

  For every line with `.type == "assistant"`, the fields under
  `.message.usage` are summed: output_tokens, cache_read_input_tokens,
  cache_creation_input_tokens, input_tokens.

  Window: if `<feature-dir>/run-log.jsonl` exists, the run window is
  [first event ts, last event ts] and only dispatches/assistant-lines whose
  first timestamp falls inside it are counted. Per-stage attribution further
  segments that window at the boundary events `gate-check-green`,
  `stage-enter`, each `review-gate`, and each `loop-disarm-*` event (same
  segmentation as `run-trace.py show --durations`).

  Timestamps are normalized before parsing: both the `...Z` and `...+00:00`
  suffix forms are accepted (`s.replace("Z", "+00:00")` before
  `datetime.fromisoformat`).

  Degradation paths (never a crash, never fabricated data):
    - transcript dir missing            -> print "no transcript found: <dir>",
                                            exit 0, no report
    - transcripts found, no run-log.jsonl -> per-dispatch table only, plus
                                            the note "per-stage attribution
                                            skipped (no run-log.jsonl)",
                                            exit 0
    - run-log.jsonl exists but has fewer than 2 boundary events -> per-
      dispatch table only, plus the note "per-stage attribution skipped
      (no segment boundaries in run-log.jsonl)" (distinct from the
      no-run-log message above — the log exists, it just carries nothing
      segmentable), exit 0
    - a malformed transcript line       -> skipped, no crash
    - a dispatch with no meta.json      -> labeled "unknown", no crash

  Output is stdout only — counts and metadata only, NEVER message content.

  Read-only guarantee: this tool must never write, rename, touch, or modify
  anything under the transcript dir. That property is a tested invariant
  (directory listing + file mtimes must be byte-identical before and after
  a run) — see specs/harness-efficiency/plan.md's invariant #2.

Exit codes: 0 success (including every degradation path above), 1 usage
error — same discipline as run-score.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

USAGE_FIELDS = (
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "input_tokens",
)

# Same boundary-event segmentation as run-trace.py show --durations (D5).
BOUNDARY_EVENTS = {"gate-check-green", "stage-enter"}


def _is_boundary(event_name: str) -> bool:
    if event_name in BOUNDARY_EVENTS:
        return True
    if event_name == "review-gate":
        return True
    if event_name.startswith("loop-disarm-"):
        return True
    # Manual `/loop off` emits the literal event `loop-disarmed` (see
    # commands/loop.md) — distinct from the `loop-disarm-*` prefix vocabulary
    # run-score.py's grading reads. Accepted here as an additional exact
    # name so per-stage attribution isn't silently skipped on a
    # manually-disarmed run; the emitter itself is unchanged.
    if event_name == "loop-disarmed":
        return True
    return False


def default_transcript_dir(cwd: Path | None = None) -> Path:
    """`~/.claude/projects/<slug>`, slug = absolute cwd with every `/` and
    `.` replaced by `-` (plan.md D6's ground-truthed slug rule)."""
    resolved = (cwd or Path.cwd()).resolve()
    slug = re.sub(r"[/.]", "-", str(resolved))
    return Path.home() / ".claude" / "projects" / slug


def parse_ts(raw: str) -> datetime | None:
    """Normalize both the `...Z` and `...+00:00` suffix forms and parse.
    Returns None (never raises) on anything unparseable — a non-string
    value, an empty/missing timestamp, or a syntactically valid but NAIVE
    (no timezone) timestamp — callers must treat that as "skip this
    line/event", never a crash. A naive timestamp is rejected rather than
    returned because it cannot be compared against the aware datetimes the
    rest of this module produces; treating it as unparseable upholds the
    never-crash contract."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def zero_usage() -> dict[str, int]:
    return {f: 0 for f in USAGE_FIELDS}


def add_usage(totals: dict[str, int], usage: dict) -> None:
    for f in USAGE_FIELDS:
        v = usage.get(f)
        if isinstance(v, (int, float)):
            totals[f] += v


def sum_usage_line(line: str) -> tuple[datetime | None, dict[str, int] | None]:
    """Parse one JSONL transcript line. Returns (ts, usage-totals) for an
    assistant line with a usage payload, or (None, None) if the line is
    malformed, not an assistant line, or has no usage — never raises."""
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(entry, dict) or entry.get("type") != "assistant":
        return None, None
    message = entry.get("message")
    if not isinstance(message, dict):
        return None, None
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return None, None
    ts = parse_ts(entry.get("timestamp", ""))
    totals = zero_usage()
    add_usage(totals, usage)
    return ts, totals


def read_transcript_lines(path: Path) -> list[tuple[datetime | None, dict[str, int]]]:
    """Every assistant/usage line in a transcript file, read-only. A
    malformed line is skipped, never crashes the read."""
    out: list[tuple[datetime | None, dict[str, int]]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        if not raw.strip():
            continue
        ts, totals = sum_usage_line(raw)
        if totals is None:
            continue
        out.append((ts, totals))
    return out


class Dispatch:
    def __init__(self, agent_type: str, description: str, model: str | None,
                 first_ts: datetime | None, last_ts: datetime | None,
                 totals: dict[str, int]):
        self.agent_type = agent_type
        self.description = description
        self.model = model
        self.first_ts = first_ts
        self.last_ts = last_ts
        self.totals = totals


def _model_of(path: Path, lines: list[str]) -> str | None:
    for raw in lines:
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and entry.get("type") == "assistant":
            message = entry.get("message")
            if isinstance(message, dict) and message.get("model"):
                return message.get("model")
    return None


def collect_dispatches(transcript_dir: Path) -> list[Dispatch]:
    """Every <session>/subagents/agent-*.jsonl dispatch, read-only. A
    dispatch with no sibling meta.json is labeled 'unknown', never crashes."""
    dispatches: list[Dispatch] = []
    for session_dir in sorted(transcript_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        subagents_dir = session_dir / "subagents"
        if not subagents_dir.is_dir():
            continue
        for jsonl_path in sorted(subagents_dir.glob("agent-*.jsonl")):
            entries = read_transcript_lines(jsonl_path)
            if not entries:
                continue
            timestamps = [ts for ts, _ in entries if ts is not None]
            first_ts = min(timestamps) if timestamps else None
            last_ts = max(timestamps) if timestamps else None
            totals = zero_usage()
            for _, u in entries:
                for f in USAGE_FIELDS:
                    totals[f] += u[f]

            # jsonl_path is agent-<id>.jsonl; the meta sibling is
            # agent-<id>.meta.json (same stem, .meta.json suffix appended).
            meta_path = jsonl_path.parent / (jsonl_path.stem + ".meta.json")
            agent_type = "unknown"
            description = "unknown"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    meta = {}
                if isinstance(meta, dict):
                    agent_type = meta.get("agentType") or "unknown"
                    description = meta.get("description") or "unknown"

            try:
                raw_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
            except OSError:
                raw_lines = []
            model = _model_of(jsonl_path, raw_lines)

            dispatches.append(Dispatch(
                agent_type=agent_type, description=description, model=model,
                first_ts=first_ts, last_ts=last_ts, totals=totals,
            ))
    return dispatches


class ControllerRow:
    def __init__(self, session_id: str, first_ts: datetime | None,
                 last_ts: datetime | None, totals: dict[str, int],
                 lines: list[tuple[datetime | None, dict[str, int]]] | None = None):
        self.session_id = session_id
        self.first_ts = first_ts
        self.last_ts = last_ts
        self.totals = totals
        # Individual (ts, usage) entries for this session's assistant lines.
        # Per-stage attribution (D6: "each dispatch/controller-line
        # attributed to the window containing its (first) timestamp") must
        # bucket controller usage per LINE, not attribute the whole
        # session's totals to the window containing its first timestamp —
        # a controller session spans every stage, so block-attribution
        # would systematically inflate the first window.
        self.lines = lines if lines is not None else []


def collect_controller_rows(transcript_dir: Path) -> list[ControllerRow]:
    """Every main-session *.jsonl directly inside transcript_dir, read-only."""
    rows: list[ControllerRow] = []
    for jsonl_path in sorted(transcript_dir.glob("*.jsonl")):
        entries = read_transcript_lines(jsonl_path)
        if not entries:
            continue
        timestamps = [ts for ts, _ in entries if ts is not None]
        first_ts = min(timestamps) if timestamps else None
        last_ts = max(timestamps) if timestamps else None
        totals = zero_usage()
        for _, u in entries:
            for f in USAGE_FIELDS:
                totals[f] += u[f]
        rows.append(ControllerRow(
            session_id=jsonl_path.stem, first_ts=first_ts, last_ts=last_ts,
            totals=totals, lines=entries,
        ))
    return rows


def read_run_log_events(run_log_path: Path) -> list[dict]:
    """Every well-formed event in run-log.jsonl, read-only. A malformed
    line is skipped, never crashes."""
    events: list[dict] = []
    try:
        text = run_log_path.read_text(encoding="utf-8")
    except OSError:
        return events
    for raw in text.splitlines():
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            events.append(entry)
    return events


def run_window(events: list[dict]) -> tuple[datetime | None, datetime | None]:
    """[first ts, last ts] over every parseable event timestamp."""
    parsed = [parse_ts(e.get("ts", "")) for e in events]
    parsed = [ts for ts in parsed if ts is not None]
    if not parsed:
        return None, None
    return min(parsed), max(parsed)


def boundary_segments(events: list[dict]) -> list[tuple[datetime, str, datetime, str]]:
    """Consecutive boundary-event pairs (gate-check-green, stage-enter,
    review-gate, loop-disarm-*) — same segmentation as run-trace.py show
    --durations (D5). Each item: (start_ts, start_label, end_ts, end_label)."""
    boundary_points: list[tuple[datetime, str]] = []
    for e in events:
        name = e.get("event", "")
        if not _is_boundary(name):
            continue
        ts = parse_ts(e.get("ts", ""))
        if ts is None:
            continue
        boundary_points.append((ts, name))
    boundary_points.sort(key=lambda p: p[0])

    segments = []
    for a, b in zip(boundary_points, boundary_points[1:]):
        segments.append((a[0], a[1], b[0], b[1]))
    return segments


def format_tokens(totals: dict[str, int]) -> str:
    return (f"output={totals['output_tokens']} "
            f"cache_read={totals['cache_read_input_tokens']} "
            f"cache_creation={totals['cache_creation_input_tokens']} "
            f"input={totals['input_tokens']}")


def format_wall_clock(first_ts: datetime | None, last_ts: datetime | None) -> str:
    if first_ts is None or last_ts is None:
        return "n/a"
    return str(last_ts - first_ts)


def render_per_dispatch_table(dispatches: list[Dispatch],
                               controller_rows: list[ControllerRow]) -> str:
    lines = ["── per-dispatch ──"]
    for d in dispatches:
        lines.append(
            f"{d.agent_type} | {d.description} | "
            f"first={d.first_ts.isoformat() if d.first_ts else 'n/a'} | "
            f"wall={format_wall_clock(d.first_ts, d.last_ts)} | "
            f"model={d.model or 'unknown'} | {format_tokens(d.totals)}"
        )
    for c in controller_rows:
        lines.append(
            f"(controller) {c.session_id} | "
            f"first={c.first_ts.isoformat() if c.first_ts else 'n/a'} | "
            f"wall={format_wall_clock(c.first_ts, c.last_ts)} | "
            f"{format_tokens(c.totals)}"
        )
    return "\n".join(lines)


def render_per_stage_table(
    segments: list[tuple[datetime, str, datetime, str]],
    dispatches: list[Dispatch],
    controller_rows: list[ControllerRow],
) -> str:
    lines = ["── per-stage ──"]
    last_index = len(segments) - 1
    for i, (start_ts, start_label, end_ts, end_label) in enumerate(segments):
        # Interior boundaries stay half-open (start <= ts < end) so a line
        # exactly ON a boundary is never double-counted by two adjacent
        # segments. The FINAL segment is the one exception: it is inclusive
        # of end_ts (start <= ts <= end) so a line exactly at win_end still
        # lands in a per-stage segment — otherwise it would appear in the
        # per-dispatch totals but in no per-stage segment, and the two
        # tables would fail to reconcile (C4 finding f).
        is_last = i == last_index
        totals = zero_usage()
        for d in dispatches:
            if d.first_ts is None:
                continue
            in_segment = (start_ts <= d.first_ts <= end_ts) if is_last \
                else (start_ts <= d.first_ts < end_ts)
            if in_segment:
                add_usage(totals, d.totals)
        # Controller lines are attributed INDIVIDUALLY (D6: "each
        # dispatch/controller-line attributed to the window containing its
        # (first) timestamp" — "(first)" governs multi-line dispatches; a
        # controller session's own assistant lines are each attributed on
        # their own timestamp, never the whole session as one block).
        for c in controller_rows:
            for ts, usage_totals in c.lines:
                if ts is None:
                    continue
                in_segment = (start_ts <= ts <= end_ts) if is_last \
                    else (start_ts <= ts < end_ts)
                if in_segment:
                    add_usage(totals, usage_totals)
        lines.append(
            f"{start_label} → {end_label} | "
            f"wall={format_wall_clock(start_ts, end_ts)} | "
            f"{format_tokens(totals)}"
        )
    return "\n".join(lines)


def _print_dispatch_only_fallback(
    dispatches: list[Dispatch],
    controller_rows: list[ControllerRow],
    reason: str,
) -> None:
    """The degraded report: per-dispatch table only, plus a one-line note
    naming WHY per-stage attribution was skipped. Consolidates what were
    three copy-pasted call sites (no run-log.jsonl, empty run-log.jsonl, no
    segment boundaries) so each degradation path states its own reason
    instead of all three sharing the misleading "no run-log.jsonl" text."""
    print(render_per_dispatch_table(dispatches, controller_rows))
    print()
    print(f"per-stage attribution skipped ({reason})")


def run(feature_dir: Path, transcript_dir: Path) -> int:
    if not feature_dir.is_dir():
        print(f"run-cost: no such feature dir: {feature_dir}", file=sys.stderr)
        return 1

    if not transcript_dir.is_dir():
        print(f"no transcript found: {transcript_dir}")
        return 0

    dispatches = collect_dispatches(transcript_dir)
    controller_rows = collect_controller_rows(transcript_dir)

    run_log_path = feature_dir / "run-log.jsonl"
    if not run_log_path.exists():
        _print_dispatch_only_fallback(dispatches, controller_rows, "no run-log.jsonl")
        return 0

    events = read_run_log_events(run_log_path)
    if not events:
        _print_dispatch_only_fallback(dispatches, controller_rows, "no run-log.jsonl")
        return 0

    win_start, win_end = run_window(events)

    if win_start is not None and win_end is not None:
        dispatches = [d for d in dispatches
                      if d.first_ts is not None and win_start <= d.first_ts <= win_end]
        # Controller rows are windowed at LINE granularity (D6: "main-
        # session assistant lines inside it are counted") — a session
        # whose first line predates the window must still contribute the
        # subset of its lines that fall inside it, not be dropped whole
        # because its first_ts precedes win_start.
        windowed_controller_rows = []
        for c in controller_rows:
            in_window_lines = [(ts, u) for ts, u in c.lines
                                if ts is not None and win_start <= ts <= win_end]
            if not in_window_lines:
                continue
            totals = zero_usage()
            for _, u in in_window_lines:
                add_usage(totals, u)
            timestamps = [ts for ts, _ in in_window_lines]
            windowed_controller_rows.append(ControllerRow(
                session_id=c.session_id, first_ts=min(timestamps),
                last_ts=max(timestamps), totals=totals, lines=in_window_lines,
            ))
        controller_rows = windowed_controller_rows

    segments = boundary_segments(events)
    if not segments:
        _print_dispatch_only_fallback(
            dispatches, controller_rows,
            "no segment boundaries in run-log.jsonl",
        )
        return 0

    # Per-stage table renders FIRST: it carries the boundary-event labels
    # (review-gate, stage-enter, loop-disarm-*) that give each token count
    # its stage attribution. The per-dispatch table (raw per-subagent
    # totals, unattributed to a stage) follows.
    print(render_per_stage_table(segments, dispatches, controller_rows))
    print()
    print(render_per_dispatch_table(dispatches, controller_rows))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="run-cost.py — per-dispatch and per-stage token-cost "
                     "report compiled from local Claude Code transcripts")
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("--transcript-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    transcript_dir = args.transcript_dir
    if transcript_dir is None:
        transcript_dir = default_transcript_dir()

    return run(args.feature_dir, transcript_dir)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
