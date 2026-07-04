#!/usr/bin/env python3
"""
run-trace.py — the in-loop run trace (netdust-agent)

THE single-writer convergence point for every run event the harness emits
(plan.md's architecture-invariants section: "all run events converge through
`run-trace.py append` — one writer, one schema"). `loop-gate.py`, the spine
prose, and `/shakeout` all route through this file; nothing hand-rolls JSONL.

    usage: run-trace.py append <feature-dir> <event> [k=v ...]
           run-trace.py show <feature-dir>

`append` writes exactly one JSON line to `<feature-dir>/run-log.jsonl`
(created if absent, appended if present) with the shape:

    {"ts": "<iso8601>", "event": "<name>", "data": {"k": "v", ...}}

Denial paths (both reject BEFORE any write — no partial file):
  - nonexistent `<feature-dir>` -> exit 1, one-line reason on stderr, no file.
  - a `k=v` token missing `=` -> exit 1, one-line reason on stderr, no file.

`show` renders the log human-readably, one line per event. A missing or
empty log is not an error — it prints "no trace recorded" and exits 0.

Exit codes: 0 success, 1 usage/validation/denial error.
"""
from __future__ import annotations

import argparse
import json
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
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")

    return 0


def do_show(feature_dir: Path) -> int:
    log_path = feature_dir / LOG_NAME
    if not log_path.exists():
        print("no trace recorded")
        return 0

    text = log_path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        print("no trace recorded")
        return 0

    for raw in lines:
        entry = json.loads(raw)
        ts = entry.get("ts", "")
        event = entry.get("event", "")
        data = entry.get("data", {})
        print(f"{ts} {event} {data}")

    return 0


def main(argv: list[str]) -> int:
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

    args = ap.parse_args(argv)

    if args.command == "append":
        return do_append(args.feature_dir, args.event, args.kv)
    elif args.command == "show":
        return do_show(args.feature_dir)

    return 1  # unreachable — argparse enforces a valid subcommand


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
