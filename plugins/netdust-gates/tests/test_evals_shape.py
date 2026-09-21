"""test_evals_shape.py — the eval cases are well-formed and the runner parses.
The cases themselves need the `claude` CLI and are run by hand: python3 evals/run-evals.py"""
import json
import re
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "evals"
IDS = ["wp-feature-constraints", "security-surface-review-focus", "small-tweak-no-artifacts"]


def _compiles(cases: list[dict]) -> bool:
    try:
        return all(re.compile(e["match"]) and e["where"] for c in cases for e in c["expect"])
    except (re.error, KeyError):
        return False


def run() -> list[tuple[bool, str]]:
    cases = json.loads((EVALS / "cases.json").read_text())
    try:
        compile((EVALS / "run-evals.py").read_text(), "run-evals.py", "exec")
        parses = True
    except SyntaxError:
        parses = False
    return [
        ([c["id"] for c in cases] == IDS, f"exactly the three R10 cases, in order (got {[c['id'] for c in cases]})"),
        (all({"id", "prompt", "files", "expect", "absent"} <= set(c) for c in cases),
         "every case carries id, prompt, files, expect, absent"),
        (_compiles(cases), "every expect regex compiles and names where it looks"),
        (parses, "run-evals.py parses"),
    ]
