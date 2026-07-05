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
                                            skipped", exit 0
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
import sys
from pathlib import Path


def default_transcript_dir(cwd: Path | None = None) -> Path:
    """Not implemented — signature shell only (test-author phase)."""
    raise NotImplementedError("default_transcript_dir: not implemented")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="run-cost.py — per-dispatch and per-stage token-cost "
                     "report compiled from local Claude Code transcripts")
    ap.add_argument("feature_dir", type=Path)
    ap.add_argument("--transcript-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    # Signature shell only: no parsing/summing logic yet. Sentinel body so
    # the RED this task's tests produce is behavioral (wrong exit code /
    # wrong stdout), never "module not found". The implementer replaces
    # this body; nothing above (argparse surface, docstring contract) is
    # implementation and should not need to change.
    raise NotImplementedError("run-cost.py: not implemented")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
