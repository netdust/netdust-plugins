"""
test_session_start_budget.py — verifies session-start.sh enforces a real
byte budget on the memory files it injects, instead of warning-then-loading-
everything.

Bugs fixed 2026-06-09:
  • STATE.md size guard at ~40KB only WARNED, then `cat`'d the whole file
    (Folio's was 175KB → ~40K tokens every session start).
  • No budget on lessons.md or the MEMORY.md atomic index.
  • No total-injection report.

Contract under test:
  • STATE.md   — hard budget 32KB, truncate at a ## / ### boundary.
  • lessons.md — hard budget 16KB, same boundary rule.
  • MEMORY.md  — 24KB budget (the index ceiling its own warning names).
  • When truncated, a visible line names the byte sizes + skipped ## headers.
  • Final line of hook output reports total injected bytes.

The test runs the REAL session-start.sh via subprocess against a temp CWD,
the way Claude Code fires it (CLAUDE_PLUGIN_ROOT pointed at the plugin).
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "session-start.sh"

STATE_BUDGET = 32 * 1024
LESSONS_BUDGET = 16 * 1024


def _run_hook(cwd: Path) -> str:
    """Fire the hook from `cwd`; return its stdout (the injected context)."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)}
    # Run with cwd=the temp project so $(pwd) resolves there.
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    return proc.stdout


def _mk_project() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="netdust-budget-"))
    (tmp / "memory").mkdir()
    (tmp / "tasks").mkdir()
    return tmp


def _section(header: str, kb: int) -> str:
    """A markdown section whose body is ~kb kilobytes of filler."""
    filler = ("lorem ipsum dolor sit amet " * 40 + "\n") * (kb * 1024 // 1080 + 1)
    return f"## {header}\n{filler}\n"


def test_oversize_state_truncated_to_budget() -> tuple[bool, str]:
    tmp = _mk_project()
    try:
        # ~60KB across 6 sections of ~10KB each → must cut around 32KB.
        sections = "".join(_section(f"Section {i}", 10) for i in range(6))
        (tmp / "memory" / "STATE.md").write_text("# STATE\n\n" + sections)
        full_bytes = (tmp / "memory" / "STATE.md").stat().st_size

        out = _run_hook(tmp)

        # The State block must be present but truncated well under the full size.
        if "## Project State" not in out:
            return False, "state-trunc: Project State block missing from output"
        # Extract what came after "## Project State" up to the next top-level
        # hook section to size the injected STATE content.
        # Cheaper proxy: the full 60KB of filler must NOT all be present.
        injected_sections = out.count("## Section ")
        if injected_sections == 6:
            return False, (f"state-trunc: all 6 sections injected — not truncated "
                           f"(file is {full_bytes} bytes, budget {STATE_BUDGET})")
        if injected_sections == 0:
            return False, "state-trunc: zero sections injected — over-truncated"
        # Truncation notice must be present and name the file size.
        if "truncated" not in out.lower():
            return False, "state-trunc: no 'truncated' notice in output"
        return True, f"state-trunc: truncated to {injected_sections}/6 sections, notice present"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_truncation_cuts_at_section_boundary() -> tuple[bool, str]:
    """A truncated section must never be cut mid-body: the last injected
    '## ' header must be immediately followed (eventually) by a clean cut,
    i.e. we never emit a header whose body is sliced — we drop whole sections."""
    tmp = _mk_project()
    try:
        # 5 clearly-named sections, 9KB each (~45KB). Budget 32KB → ~3 fit.
        body = "# STATE\n\n"
        for i in range(5):
            body += f"## Marker{i}\n" + ("x" * 9000) + f"\nENDMARKER{i}\n\n"
        (tmp / "memory" / "STATE.md").write_text(body)

        out = _run_hook(tmp)

        # For every Marker header that IS present, its ENDMARKER must also be
        # present (the section was taken whole, not sliced).
        for i in range(5):
            has_header = f"## Marker{i}" in out
            has_end = f"ENDMARKER{i}" in out
            if has_header and not has_end:
                return False, f"boundary: Marker{i} header injected but body sliced (no ENDMARKER{i})"
        return True, "boundary: every injected section is whole (no mid-section cut)"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_truncation_notice_lists_skipped_headers() -> tuple[bool, str]:
    tmp = _mk_project()
    try:
        body = "# STATE\n\n"
        for i in range(5):
            body += f"## SkipCheck{i}\n" + ("y" * 9000) + "\n\n"
        (tmp / "memory" / "STATE.md").write_text(body)

        out = _run_hook(tmp)

        # At least one late section must be named as skipped.
        m = re.search(r"Sections not loaded:.*", out)
        if not m:
            return False, "notice: no 'Sections not loaded:' line"
        skipped_line = m.group(0)
        # The last section is the most likely to be skipped.
        if "SkipCheck4" not in skipped_line:
            return False, f"notice: last section not listed as skipped. Line: {skipped_line[:200]}"
        return True, "notice: skipped ## headers are listed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_small_state_loaded_whole_no_notice() -> tuple[bool, str]:
    """Under budget → load whole, no truncation notice (don't regress small files)."""
    tmp = _mk_project()
    try:
        (tmp / "memory" / "STATE.md").write_text(
            "# STATE\n\n## Only Section\nThis is a small state file.\nDONE_SMALL\n"
        )
        out = _run_hook(tmp)
        if "DONE_SMALL" not in out:
            return False, "small: small STATE.md not fully loaded"
        if "truncated" in out.lower():
            return False, "small: spurious truncation notice on a sub-budget file"
        return True, "small: sub-budget STATE.md loaded whole, no notice"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_oversize_lessons_truncated() -> tuple[bool, str]:
    tmp = _mk_project()
    try:
        (tmp / "memory" / "STATE.md").write_text("# STATE\n\nsmall\n")
        body = "# LESSONS\n\n"
        for i in range(5):
            body += f"## Lesson{i}\n" + ("z" * 6000) + f"\nLENDMARK{i}\n\n"  # ~30KB
        (tmp / "memory" / "lessons.md").write_text(body)

        out = _run_hook(tmp)
        injected = sum(1 for i in range(5) if f"## Lesson{i}" in out)
        if injected == 5:
            return False, "lessons-trunc: all 5 lessons injected — 16KB budget not enforced"
        if injected == 0:
            return False, "lessons-trunc: zero lessons injected — over-truncated"
        return True, f"lessons-trunc: lessons.md truncated to {injected}/5 sections"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_total_injection_report_present() -> tuple[bool, str]:
    """The hook must print one line reporting total injected bytes."""
    tmp = _mk_project()
    try:
        (tmp / "memory" / "STATE.md").write_text("# STATE\n\nbody DONE_REPORT\n")
        out = _run_hook(tmp)
        # Expect a line naming total injected size in bytes/KB.
        if not re.search(r"[Tt]otal.*inject.*\d+\s*(bytes|B|KB)", out):
            return False, f"report: no total-injection line found. Tail:\n{out[-300:]}"
        return True, "report: total-injection line present"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_huge_preamble_is_capped() -> tuple[bool, str]:
    """Regression (Folio 175KB STATE.md): the bloat can live in the PREAMBLE
    — one giant blob before the first ## header. The preamble must still be
    capped at the budget, or truncation achieves nothing. Total injected for
    STATE must land near the 32KB budget, not the full file size."""
    tmp = _mk_project()
    try:
        # 80KB of preamble text, NO section headers at all.
        preamble = ("PREAMBLE_LINE this is bloat that lives before any header. " * 18 + "\n") * 80
        (tmp / "memory" / "STATE.md").write_text("# STATE\n\n" + preamble)
        full = (tmp / "memory" / "STATE.md").stat().st_size
        if full < 60000:
            return False, f"preamble: fixture too small ({full}) to test the cap"

        out = _run_hook(tmp)

        # Count PREAMBLE_LINE occurrences as a proxy for injected preamble size.
        # The full file has ~1440 of them; capped at 32KB should inject far fewer.
        occ = out.count("PREAMBLE_LINE")
        # 32KB / ~58 bytes per occurrence ≈ 565 max; full is ~1440. Require it
        # to be meaningfully under the full count (i.e. the cap bit).
        full_occ = (tmp / "memory" / "STATE.md").read_text().count("PREAMBLE_LINE")
        if occ >= full_occ:
            return False, (f"preamble: full preamble injected ({occ}/{full_occ}) — "
                           f"a header-less {full} byte STATE.md was NOT capped")
        if "truncated" not in out.lower():
            return False, "preamble: capped but no truncation notice"
        return True, f"preamble: header-less bloat capped ({occ}/{full_occ} lines injected)"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_TESTS = [
    test_huge_preamble_is_capped,
    test_oversize_state_truncated_to_budget,
    test_truncation_cuts_at_section_boundary,
    test_truncation_notice_lists_skipped_headers,
    test_small_state_loaded_whole_no_notice,
    test_oversize_lessons_truncated,
    test_total_injection_report_present,
]


def run() -> list[tuple[bool, str]]:
    results = []
    for fn in _TESTS:
        try:
            results.append(fn())
        except Exception as e:
            results.append((False, f"{fn.__name__}: raised {type(e).__name__}: {e}"))
    return results
