#!/usr/bin/env python3
"""
run-score.py — the evaluator rubric compiler (netdust-agent)

STUB (T04 RED phase — test-author). The implementer fills in the real
grading logic against `specs/run-observability/plan.md`'s thresholds
table. This skeleton exists only so `tests/test_run_score.py` fails
behaviorally (wrong/missing output) rather than with "no such file".

    usage: run-score.py <feature-dir>

Compiles `<feature-dir>/run-log.jsonl` + `<feature-dir>/tasks.md` +
`gate-check.py --json <feature-dir>` into `<feature-dir>/run-rubric.md` —
a markdown rubric grading five dimensions (seam integrity, cluster
discipline, loop efficiency, yield discipline, completion) with letter
grades A/B/C/D/n/a derived mechanically from documented thresholds.

Denial path (mandatory): if `<feature-dir>/run-log.jsonl` does not exist,
exit 0 with a "no trace recorded" note and write NO run-rubric.md file —
never fabricate grades from absent data.

Exit codes: 0 success (including the no-trace denial path), 1 usage error.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

LOG_NAME = "run-log.jsonl"
RUBRIC_NAME = "run-rubric.md"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="run-score.py — compile the per-feature run log + tasks.md "
                     "+ gate-check verdict into a graded run-rubric.md")
    ap.add_argument("feature_dir", type=Path)
    args = ap.parse_args(argv)

    feature_dir: Path = args.feature_dir
    log_path = feature_dir / LOG_NAME

    if not log_path.exists():
        print("no trace recorded")
        return 0

    raise NotImplementedError("run-score.py rubric compilation not yet implemented")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
