#!/usr/bin/env python3
"""
run-trace.py — the in-loop run trace (netdust-agent)

SKELETON — signature shell only, authored by test-author (T01 RED phase).
The implementer fills in the real append/show behavior; this stub exists
solely so the RED test fails for a BEHAVIORAL reason (wrong exit code /
missing output), not "module not found".

    usage: run-trace.py append <feature-dir> <event> [k=v ...]
           run-trace.py show <feature-dir>

NOT YET IMPLEMENTED: JSONL append, feature-dir existence check, k=v
parsing/validation, and log rendering. Do not build on this file's
current behavior — see tests/test_run_trace.py for the real contract.
"""

import sys


def main(argv: list[str]) -> int:
    raise NotImplementedError(
        "run-trace.py is a signature shell (T01 RED phase) — "
        "append/show are not yet implemented"
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
