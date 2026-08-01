#!/usr/bin/env python3
"""
run-trace.py — the in-loop run trace (netdust-agent)

THE single-writer convergence point for every run event the harness emits
(plan.md's architecture-invariants section: "all run events converge through
`run-trace.py append` — one writer, one schema"). `loop-gate.py`, the spine
prose, and `/shakeout` all route through this file; nothing hand-rolls JSONL.

    usage: run-trace.py append <feature-dir> <event> [k=v ...]
           run-trace.py show <feature-dir>
           run-trace.py verify-suite <feature-dir> -- <suite command...>

`append` writes exactly one JSON line to `<feature-dir>/run-log.jsonl`
(created if absent, appended if present) with the shape:

    {"ts": "<iso8601>", "event": "<name>", "data": {"k": "v", ...}}

Denial paths (all reject BEFORE any write completes — no partial file):
  - nonexistent `<feature-dir>` -> exit 1, one-line reason on stderr, no file.
  - a `k=v` token missing `=` -> exit 1, one-line reason on stderr, no file.
  - an OS-level write failure (e.g. permission denied, disk full) -> exit 1,
    one-line reason on stderr, no crash/traceback.

`show` renders the log human-readably, one line per event. A missing or
empty log is not an error — it prints "no trace recorded" and exits 0. A
torn/malformed line (e.g. a process killed mid-`append`) does not crash
`show` either — it renders `<corrupt line>` in that line's place and
continues with the rest of the log; `show` still always exits 0.

`show --durations` prints, AFTER the normal rendering, a segments table:
a `── durations ──` header, one row per consecutive pair of parseable
(timestamped) events — `<event-a>[ <key data>] → <event-b>[ <key data>]
  <H:MM:SS>` — where a `review-gate` row's key data includes
`cluster=`/`tier=` and a `stage-enter` row's key data includes `stage=`,
followed by a trailing `total (first → last parseable event)  <H:MM:SS>`
line. Corrupt/unparseable-ts lines are skipped for segmentation purposes
(consistent with the `<corrupt line>` degradation above) — they are never
a segment endpoint. No aggregation beyond the total is performed; the
segments between existing emission points ARE the per-stage/per-gate
durations. Denial path: fewer than 2 parseable events -> exactly
`durations: not derivable (<2 timestamped events)`, exit 0. Without the
flag, output is unchanged.

`verify-suite` is the SANCTIONED fact-minting path for a stale/missing
`suite-green` (the loop-check stale-evidence CONTINUE names it): run-trace
RUNS the given suite command ITSELF (argv after `--`, stdio inherited so
the suite's own output is the evidence), and appends one `suite-green`
event (sha of the feature dir's HEAD + the cmd) ONLY on a real exit 0. A
failing or unrunnable suite appends NOTHING and exits non-zero (the
suite's own exit code when it has one). The verdict is printed either way.
An agent echoing "the suite is green" has no way through here — the only
writer of the green fact observed the exit code itself. Denial paths:
nonexistent feature dir or empty command -> exit 1, nothing run, nothing
written.

Exit codes: 0 success, 1 usage/validation/denial error (verify-suite
propagates the suite's non-zero exit).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_NAME = "run-log.jsonl"


def parse_kv(tokens: list[str]) -> dict[str, str]:
    """Parse `k=v` tokens into a dict. Raises ValueError on a malformed token
    (no `=`) so the caller can reject the whole append before writing."""
    data: dict[str, str] = {}
    for tok in tokens:
        if "=" not in tok:
            raise ValueError(f"malformed k=v token (no '='): {tok!r}")
        k, _, v = tok.partition("=")
        data[k] = v
    return data


def do_append(feature_dir: Path, event: str, kv_tokens: list[str]) -> int:
    if not feature_dir.is_dir():
        print(f"run-trace: append rejected — no such feature dir: {feature_dir}",
              file=sys.stderr)
        return 1

    try:
        data = parse_kv(kv_tokens)
    except ValueError as e:
        print(f"run-trace: append rejected — {e}", file=sys.stderr)
        return 1

    line = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "data": data,
    }

    log_path = feature_dir / LOG_NAME
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
    except OSError as e:
        print(f"run-trace: append rejected — cannot write {log_path}: {e}",
              file=sys.stderr)
        return 1

    return 0


def do_verify_suite(feature_dir: Path, cmd: list[str]) -> int:
    """Run the suite command; append `suite-green` ONLY on a real exit 0.

    The fact is minted by THIS process observing the exit code — never by
    testimony. Failure (non-zero exit, or a command that cannot run) appends
    nothing and returns non-zero. All rejections happen BEFORE the command
    runs or anything is written."""
    if not feature_dir.is_dir():
        print(f"run-trace: verify-suite rejected — no such feature dir: "
              f"{feature_dir}", file=sys.stderr)
        return 1
    if not cmd:
        print("run-trace: verify-suite rejected — no suite command given "
              "(usage: verify-suite <feature-dir> -- <suite command...>)",
              file=sys.stderr)
        return 1

    cmd_str = " ".join(cmd)
    try:
        # stdio inherited on purpose: the suite's own output IS the evidence.
        proc = subprocess.run(cmd)
        exit_code = proc.returncode
    except OSError as e:
        print(f"run-trace: verify-suite RED — cannot run {cmd_str!r}: {e}",
              file=sys.stderr)
        return 1

    if exit_code != 0:
        print(f"run-trace: verify-suite RED (exit {exit_code}) — "
              "no suite-green appended", file=sys.stderr)
        return exit_code

    try:
        sha_proc = subprocess.run(
            ["git", "-C", str(feature_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else "unknown"
    except Exception:
        sha = "unknown"

    rc = do_append(feature_dir, "suite-green", [f"sha={sha}", f"cmd={cmd_str}"])
    if rc != 0:
        return rc
    print(f"run-trace: verify-suite GREEN — suite-green appended "
          f"(sha={sha} cmd={cmd_str})")
    return 0


def do_show(feature_dir: Path, durations: bool = False) -> int:
    log_path = feature_dir / LOG_NAME
    if not log_path.exists():
        print("no trace recorded")
        return 0

    text = log_path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        print("no trace recorded")
        return 0

    parseable_events: list[tuple[datetime, str, dict]] = []

    for raw in lines:
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            print("<corrupt line>")
            continue
        ts = entry.get("ts", "")
        event = entry.get("event", "")
        data = entry.get("data", {})
        print(f"{ts} {event} {data}")

        if durations:
            parsed_ts = _parse_ts(ts)
            if parsed_ts is not None:
                # Normalize a non-dict `data` (e.g. `null`) to {} here, at
                # parseable_events build time — matching the non-durations
                # loop's existing `entry.get("data", {})` guard above, so
                # _format_event_label never has to special-case it.
                safe_data = data if isinstance(data, dict) else {}
                parseable_events.append((parsed_ts, event, safe_data))

    if durations:
        if len(parseable_events) < 2:
            print("durations: not derivable (<2 timestamped events)")
            return 0

        # Sort by timestamp before pairing — a run-log can contain
        # out-of-order events (e.g. clock skew across dispatched agents);
        # pairing in raw file order would emit negative durations.
        parseable_events.sort(key=lambda e: e[0])

        print("── durations ──")
        for (ts_a, event_a, data_a), (ts_b, event_b, data_b) in zip(
            parseable_events, parseable_events[1:]
        ):
            label_a = _format_event_label(event_a, data_a)
            label_b = _format_event_label(event_b, data_b)
            delta = ts_b - ts_a
            print(f"{label_a} → {label_b}   {delta}")

        total = parseable_events[-1][0] - parseable_events[0][0]
        print(f"total (first → last parseable event)              {total}")

    return 0


def _parse_ts(ts: str) -> datetime | None:
    """Parse an event's `ts` field defensively. Returns None (rather than
    raising) for an empty/missing, non-string, naive (no timezone), or
    otherwise unparseable timestamp so the caller can skip it as a
    segmentation endpoint, consistent with `show`'s existing corrupt-line
    degradation. A successfully-parsed NAIVE datetime is rejected (returns
    None) rather than returned, because it cannot be compared/subtracted
    against the aware datetimes the rest of this module produces — treating
    it as unparseable upholds the never-crash contract."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _format_event_label(event: str, data: dict) -> str:
    """Render `<event>[ <key data>]` for a durations row. `review-gate`
    carries cluster=/tier=; `stage-enter` carries stage= (plan.md D5)."""
    key_data: dict = {}
    if event == "review-gate":
        for key in ("cluster", "tier"):
            if key in data:
                key_data[key] = data[key]
    elif event == "stage-enter":
        for key in ("stage",):
            if key in data:
                key_data[key] = data[key]

    if not key_data:
        return event
    rendered = " ".join(f"{k}={v}" for k, v in key_data.items())
    return f"{event} {rendered}"


def main(argv: list[str]) -> int:
    # verify-suite is handled BEFORE argparse: everything after `--` is the
    # suite command verbatim (argparse's REMAINDER/`--` handling is lossy for
    # commands whose own tokens start with `-`).
    if argv and argv[0] == "verify-suite":
        rest = argv[1:]
        if "--" in rest:
            sep = rest.index("--")
            head, cmd = rest[:sep], rest[sep + 1:]
        else:
            head, cmd = rest[:1], rest[1:]
        if len(head) != 1:
            print("run-trace: usage: verify-suite <feature-dir> -- "
                  "<suite command...>", file=sys.stderr)
            return 1
        return do_verify_suite(Path(head[0]), cmd)

    ap = argparse.ArgumentParser(
        description="run-trace.py — append/show the per-feature run log "
                     "(the single-writer trace convergence point)")
    sub = ap.add_subparsers(dest="command", required=True)

    p_append = sub.add_parser("append", help="append one event to the run log")
    p_append.add_argument("feature_dir", type=Path)
    p_append.add_argument("event")
    p_append.add_argument("kv", nargs="*", help="k=v data tokens")

    p_show = sub.add_parser("show", help="render the run log")
    p_show.add_argument("feature_dir", type=Path)
    p_show.add_argument("--durations", action="store_true",
                         help="print a segments/durations table after the "
                              "normal rendering (T10, plan.md D5)")

    args = ap.parse_args(argv)

    if args.command == "append":
        return do_append(args.feature_dir, args.event, args.kv)
    elif args.command == "show":
        return do_show(args.feature_dir, durations=args.durations)

    return 1  # unreachable — argparse enforces a valid subcommand


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
