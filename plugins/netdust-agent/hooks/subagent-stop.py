#!/usr/bin/env python3
"""
subagent-stop.py — netdust-agent harness

SubagentStop hook. Fires when a subagent considers stopping.

Purpose:
  Backstop for the building spine's testing gate (Step 2.6/2.6b). If a subagent
  wrote code (Edit/Write) but never ran a test command via Bash, this hook
  blocks the stop and tells the subagent to run the suite now.

  This backstops BOTH halves of the Stage-2 test/dev split
  (building <test_dev_split>):
    • the test-author, which edits test files and must have RUN its RED test
      (the hook checks a test command executed, not that it PASSED — a RED
      test run satisfies it, which is correct: the author's test is meant to
      fail), and
    • the implementer, which edits production code and must have RUN the suite.

  Since testimony-seams (P0) it also enforces GREEN-ness for implementer-class
  closes — a verdict keyed to a machine-checked fact, never to actor testimony.
  The building addenda specify ONE close-out evidence line (designed evidence):

      HARNESS-EVIDENCE: role=<implementer|test-author> suite="<cmd>" exit=<int>
                        [lint=<int>] [mode=<split|solo>]

  This hook owns the only parser. The line is TESTIMONY: it contributes
  exit/role/mode KNOWLEDGE that may TIGHTEN a verdict, and it NEVER
  substitutes for the facts (C1 — facts beat testimony):
    • "a test ran" requires an actual Bash tool-use matching
      TEST_CMD_PATTERN — an evidence line alone, however well-formed, never
      satisfies the tests gate (no run, no close).
    • role=test-author is honored iff every edited code path is a test path
      (RED is the author's job — run-only suffices); any production-path edit
      makes it an implementer regardless of the claim.
    • an evidence suite command that does not match the test-command
      recognizer is ignored (no "green" via echo-grade pseudo-tests). The
      recognizer is TEST_CMD_PATTERN below — composer gate / bin/gate.sh
      count, same as for a real run.
    • when the evidence line and the scraped tool_result of the last test
      run DISAGREE, the RED one wins (max severity) — a claimed exit=0
      cannot overrule a scraped failure, and a confessed exit≠0 blocks even
      over a scraped green.
    • an implementer whose suite exited non-zero is blocked, reason naming
      the command and exit code. Unknown exit (no line, no scrapeable
      result) degrades to the pre-P0 ran-only behavior.

  On an implementer GREEN close while a harness loop is armed
  (tasks/.harness-loop.json), it appends one `suite-green` event (sha + cmd)
  through bin/run-trace.py — the evidence bin/loop-check.py's FINISHED
  verdict is keyed to. Emission fires ONLY when a SCRAPED green corroborates
  (a matching Bash run whose tool_result is non-error, i.e. exit 0) — never
  on the evidence line alone: this event mints the fact loop-check trusts,
  so it may not itself rest on testimony. Emission is fail-open and never
  affects the decision.

  It also enforces the sensitive-path routing floor (P1b): a SOLO
  implementer close that edited a production path matching the
  sensitive-glob list (bin/sensitive-globs.txt, overridable by
  .claude/sensitive-globs.txt) is blocked with an escalation instruction —
  the machine floor under the planner's "a Tier-A boundary task at
  effective-high stakes is ALWAYS split" rule (D1); a solo whose tasks.md
  reason cites its cluster's demoted standard/low stakes resolves as
  "solo-demoted" and passes the floor (D1's stakes clause). The MODE is
  resolved from the current task's `Test-author:` line in tasks.md (machine
  artifact; feature dir from the loop marker or an edited specs/<feature>/
  path) — never from the subagent-echoed evidence line, which could only
  loosen the floor. Unresolvable mode → fail-open, no block. The
  current-task heuristic assumes SERIALIZED dispatch (first unchecked task);
  [P] siblings in flight can misresolve — a files-segment intersection
  disambiguates when exactly one unchecked task names an edited file (see
  resolve_task_mode for the fail direction).

  It catches the case where the parent dispatched a subagent without the
  required close-out instruction, or where the subagent ignored it.

  What this hook CANNOT enforce: authorship independence (that the implementer
  didn't also write the test it ran). A single SubagentStop invocation sees one
  subagent's transcript, not the pair, so it cannot compare authors. The
  test/dev split's independence is enforced by the controller's dispatch order
  (test-author first, then implementer) and the two separate commits — not here.
  See building <how_each_gate_is_actually_enforced>.

Design:
  • Deterministic: regex over the subagent's transcript. No LLM call.
  • Cheap: < 100ms typical.
  • Bypass: respects stop_hook_active to avoid infinite loops if the subagent
    re-stops without invoking the skill (we only block once per subagent).
  • Silent on non-code subagents: research/explore subagents that don't edit
    code are not gated.

Logs to ~/.claude/logs/memory-hook.log (shared with session-stop.py).
"""

import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

LOG_PATH = Path.home() / ".claude" / "logs" / "memory-hook.log"
RUN_TRACE = Path(__file__).resolve().parent.parent / "bin" / "run-trace.py"
MARKER_REL = Path("tasks") / ".harness-loop.json"
SENSITIVE_GLOBS_DEFAULT = (
    Path(__file__).resolve().parent.parent / "bin" / "sensitive-globs.txt"
)
SENSITIVE_GLOBS_OVERRIDE_REL = Path(".claude") / "sensitive-globs.txt"

# Tool names that indicate the subagent modified code.
CODE_EDITING_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

# Skill we coach the subagent to invoke. Not gating — soft signal that the
# subagent walked the testing-workflow checklist. The hard gate is whether
# tests actually ran (see ran_tests_via_bash).
COACHING_SKILL = "testing-workflow"

# Standards backstop (goal #2): when a project has a linter/formatter configured,
# a code-editing task should also have RUN it. Enforced ONLY where standards are
# actually defined (project_has_linter) — projects without a linter are never
# falsely blocked. The authoritative enforcement is the standards-gate skill's
# close-out evidence line; this hook is the deterministic backstop, mirroring the
# testing gate.
STANDARDS_SKILL = "standards-gate"

# File suffixes that are NOT code — a Write/Edit touching only these has
# nothing to test. Research, spec, and map subagents write large .md reports;
# gating them blocks the stop and swallows their findings (the report gets
# replaced by the "run the suite" dance). We exempt these by PATH so an
# implementer subagent that writes real source is still gated.
#
# Conservative by design: anything NOT positively recognized as a doc — and
# any edit with NO file_path at all — counts as code (gate ON). Opening the
# "unknown → exempt" direction would re-create the 231-false-pass swallow hole.
NON_CODE_SUFFIXES = (
    ".md", ".mdx", ".markdown", ".txt", ".rst",
    ".json", ".yaml", ".yml", ".toml", ".csv",
    ".lock", ".log",
)


def _is_code_path(file_path: str) -> bool:
    """True if this path looks like source we'd want tested. Missing/empty
    path → True (conservative: gate stays on for ambiguous edits)."""
    if not file_path:
        return True
    lower = file_path.lower()
    return not lower.endswith(NON_CODE_SUFFIXES)


# Directory segments / filename shapes that mark a TEST path. Sibling of
# _is_code_path, used to cross-check a `role=test-author` claim against facts:
# the claim is honored iff EVERY edited code path is a test path. Missing/empty
# path → False (conservative: an unknown path is never a test path, so the
# role resolves implementer and the green gate stays on).
_TEST_DIR_SEGMENTS = {"tests", "test", "__tests__", "spec", "specs"}
_TEST_FILE_RE = re.compile(
    r"(^test_.*\.\w+$|[._-](test|spec)\.\w+$|(test|cest)s?\.php$)"
)


def _is_test_path(file_path: str) -> bool:
    if not file_path:
        return False
    p = file_path.replace("\\", "/").lower()
    parts = p.split("/")
    if any(seg in _TEST_DIR_SEGMENTS for seg in parts[:-1]):
        return True
    return bool(_TEST_FILE_RE.search(parts[-1]))


# Minimum added lines below which the gate is considered a no-op (auto-pass).
# Captures: typo fixes, one-line tweaks, doc-string edits, formatting nudges.
# Closes the gap where net_additions ≤ 0 missed refactor-swaps that add real
# new behavior (50 added + 50 removed = 0 net, but 50 lines of new code).
GATE_MIN_ADDITIONS = 3


def log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] subagent-stop: {msg}\n")
    except Exception:
        pass


def read_transcript(path: str) -> list[dict]:
    try:
        messages = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return messages
    except Exception as e:
        log(f"read-transcript-failed path={path} err={e}")
        return []


def _count_lines(s: str) -> int:
    """Count lines in a string. Empty string is 0; a single line without a
    trailing newline still counts as 1."""
    if not s:
        return 0
    return s.count("\n") + (0 if s.endswith("\n") else 1)


def _edit_line_counts(tool_name: str, tool_input: dict) -> tuple[int, int]:
    """Return (lines_added, lines_removed) for one code-editing tool_use block.

    Both numbers are non-negative. The caller decides what to do with them.

    - Edit:        added = new_string lines; removed = old_string lines
    - Write:       added = content lines; removed = 0
                   (overwrite case is rare; we treat full file as additions)
    - MultiEdit:   sum across edits[]
    - NotebookEdit: added = new_source lines; removed = old_source lines
    """
    if tool_name == "Edit":
        added = _count_lines(tool_input.get("new_string") or "")
        removed = _count_lines(tool_input.get("old_string") or "")
        return added, removed

    if tool_name == "Write":
        return _count_lines(tool_input.get("content") or ""), 0

    if tool_name == "MultiEdit":
        a = r = 0
        for edit in tool_input.get("edits") or []:
            if not isinstance(edit, dict):
                continue
            a += _count_lines(edit.get("new_string") or "")
            r += _count_lines(edit.get("old_string") or "")
        return a, r

    if tool_name == "NotebookEdit":
        added = _count_lines(tool_input.get("new_source") or "")
        removed = _count_lines(tool_input.get("old_source") or "")
        return added, removed

    return 0, 0


# Module-level so the tests assert the real compiled patterns (see tests/test_phpstan_standards.py).
# The SAME recognizers validate a claimed suite/lint command on the
# HARNESS-EVIDENCE line — a suite= value that doesn't look like a real test
# command is ignored (a claim can tighten, never loosen).
LINT_CMD_PATTERN = re.compile(
    r"\b("
    r"(npx |bunx )?(eslint|prettier|biome)\b|"
    r"vendor/bin/(phpcs|phpcbf|php-cs-fixer|phpstan)\b|"
    r"(ddev exec )?(phpcs|phpcbf|php-cs-fixer)\b|"
    # Bare `phpstan` is anchored on its subcommand (analyse/analyze), never
    # `phpstan\b` alone — otherwise `cat phpstan.neon` / prose mentions would
    # count as a standards run. vendor/bin/phpstan is path-anchored and safe.
    r"phpstan analy[sz]e\b|"
    r"(npm run|pnpm run|pnpm|yarn|bun run) (lint|format|cs|cs-fix|lint:fix)\b|"
    # A gate run (composer gate / bin/gate.sh) runs the unit tier AND the analyse/lint tiers — evidence for BOTH patterns.
    r"composer (run-script )?(lint|phpcs|cs|cs-fix|format|analy[sz]e|phpstan|gate)\b|"
    r"bin/gate\.sh\b"
    r")"
)

TEST_CMD_PATTERN = re.compile(
    r"\b("
    r"vendor/bin/(phpunit|codecept)|"
    r"(ddev exec )?(phpunit|codecept)|"
    r"npx (vitest|playwright|jest)|"
    r"composer test|"
    # A gate run (composer gate / bin/gate.sh) runs the unit tier AND the analyse/lint tiers — evidence for BOTH patterns.
    r"composer (run-script )?gate|"
    r"bin/gate\.sh|"
    r"npm (run )?test|pnpm test|yarn test|"
    r"bun (run )?(test|vitest|playwright)|"
    r"bunx (vitest|playwright|jest)"
    r")\b"
)

# The ONE close-out evidence line (testimony-seams invariant: one format, one
# parser — this hook owns the parser; the building addenda specify the format).
EVIDENCE_LINE_RE = re.compile(r"^\s*HARNESS-EVIDENCE:\s*(.+?)\s*$", re.MULTILINE)
EVIDENCE_FIELD_RE = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')
EXIT_CODE_RE = re.compile(r"exit code:?\s*(\d+)", re.IGNORECASE)


def scan_subagent_activity(messages: list[dict]) -> dict:
    """
    Walk the transcript and record what the subagent did.

    Returns:
      {
        "edited_code":          bool,  # called Edit/Write/etc
        "lines_added":          int,   # added lines across all edit tool_uses
        "lines_removed":        int,   # removed lines across all edit tool_uses
        "net_additions":        int,   # added − removed (for the no-op check)
        "invoked_testing":      bool,  # called Skill(testing-workflow)
        "ran_tests_via_bash":   bool,  # ran a test command via Bash
      }

    Why transcript-derived counts, not `git diff HEAD`:
      Subagents commit work BEFORE SubagentStop fires. A working-tree diff
      almost always reads zero post-commit, which used to swallow every
      gate (231 false auto-passes / 24h). The transcript is the authoritative
      record of what *this* subagent did in *this* run, regardless of git
      state.

    Why both lines_added and net_additions:
      net catches no-op tasks (delete-only, rename — auto-pass).
      lines_added catches refactor-swaps where net is near zero but real new
      behavior shipped (50 lines removed + 50 lines added = net 0 but very
      much new code that wants tests).
    """
    edited = False
    invoked_testing = False
    ran_tests_bash = False
    ran_lint_bash = False
    lines_added = 0
    lines_removed = 0
    code_paths: list[str] = []
    edited_paths: list[str] = []  # ALL edited paths incl. docs (specs detection)
    test_runs: list[dict] = []   # {"id": <tool_use id or "">, "cmd": <command>}
    lint_runs: list[dict] = []

    for msg in messages:
        if msg.get("type") != "assistant":
            continue

        content = msg.get("message", {}).get("content", "")
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue

            tool_name = block.get("name", "")
            tool_input = block.get("input", {}) or {}

            if tool_name in CODE_EDITING_TOOLS:
                # Only count edits to code files. A subagent that writes only
                # docs/specs/.md reports (research, planning) has nothing to
                # test and must not be gated. Path missing/unknown → treated
                # as code (gate stays on).
                edited_paths.append(tool_input.get("file_path") or "")
                if not _is_code_path(tool_input.get("file_path") or ""):
                    continue
                edited = True
                code_paths.append(tool_input.get("file_path") or "")
                a, r = _edit_line_counts(tool_name, tool_input)
                lines_added += a
                lines_removed += r

            elif tool_name == "Skill":
                skill = (tool_input.get("skill") or "").lower()
                # Match plain name or plugin-namespaced form.
                if skill == COACHING_SKILL or skill.endswith(f":{COACHING_SKILL}"):
                    invoked_testing = True

            elif tool_name == "Bash":
                cmd = tool_input.get("command", "") or ""
                if TEST_CMD_PATTERN.search(cmd):
                    ran_tests_bash = True
                    test_runs.append({"id": block.get("id") or "", "cmd": cmd})
                if LINT_CMD_PATTERN.search(cmd):
                    ran_lint_bash = True
                    lint_runs.append({"id": block.get("id") or "", "cmd": cmd})

    return {
        "edited_code": edited,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "net_additions": lines_added - lines_removed,
        "invoked_testing": invoked_testing,
        "ran_tests_via_bash": ran_tests_bash,
        "ran_lint_via_bash": ran_lint_bash,
        "code_paths": code_paths,
        "edited_paths": edited_paths,
        "test_runs": test_runs,
        "lint_runs": lint_runs,
    }


def parse_evidence_line(messages: list[dict]) -> dict | None:
    """Parse the LAST HARNESS-EVIDENCE line from the subagent's assistant text.

    Returns {"role": ..., "suite": ..., "exit": int, "lint": int, "mode": ...}
    with only the fields present, or None when the line is absent OR malformed
    (bad role/mode value, non-integer exit/lint). Malformed → None is the
    fail-open direction: absence falls back to transcript scraping, which a
    testimony field can never loosen anyway.
    """
    raw = None
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        content = msg.get("message", {}).get("content", "")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                for m in EVIDENCE_LINE_RE.finditer(block.get("text") or ""):
                    raw = m.group(1)
    if raw is None:
        return None

    fields: dict = {}
    for m in EVIDENCE_FIELD_RE.finditer(raw):
        key = m.group(1)
        fields[key] = m.group(2) if m.group(2) is not None else m.group(3)

    try:
        if "role" in fields and fields["role"] not in ("implementer", "test-author"):
            raise ValueError(f"bad role {fields['role']!r}")
        if "mode" in fields and fields["mode"] not in ("split", "solo"):
            raise ValueError(f"bad mode {fields['mode']!r}")
        for int_key in ("exit", "lint"):
            if int_key in fields:
                fields[int_key] = int(fields[int_key])
    except ValueError as e:
        log(f"evidence-line-malformed raw={raw!r} err={e}")
        return None
    return fields


def collect_tool_results(messages: list[dict]) -> dict[str, tuple[bool, str]]:
    """Map tool_use_id → (is_error, result text) from user-turn tool_result
    blocks — the scraped half of the evidence contract."""
    results: dict[str, tuple[bool, str]] = {}
    for msg in messages:
        if msg.get("type") != "user":
            continue
        content = msg.get("message", {}).get("content", "")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tid = block.get("tool_use_id") or ""
            if not tid:
                continue
            raw = block.get("content")
            if isinstance(raw, str):
                text = raw
            elif isinstance(raw, list):
                text = "\n".join(b.get("text", "") for b in raw if isinstance(b, dict))
            else:
                text = ""
            results[tid] = (bool(block.get("is_error")), text)
    return results


def scraped_run_status(runs: list[dict],
                       results: dict[str, tuple[bool, str]]) -> dict | None:
    """Status of the LAST run (test or lint) with a matched tool_result.

    Returns {"green": bool, "exit": "<label>", "cmd": ...} or None when no run
    has a scrapeable result (exit unknown → the pre-P0 ran-only behavior).
    `is_error` on a Bash tool_result marks a non-zero exit; a printed
    "exit code N" is extracted for the label when present. Runs without a
    result (older transcripts, missing ids) are skipped — scraped evidence is
    the heuristic fallback; the designed evidence line is primary.
    """
    for run in reversed(runs):
        res = results.get(run["id"])
        if res is None:
            continue
        is_err, text = res
        if not is_err:
            return {"green": True, "exit": "0", "cmd": run["cmd"]}
        m = EXIT_CODE_RE.search(text)
        return {"green": False, "exit": m.group(1) if m else "non-zero",
                "cmd": run["cmd"]}
    return None


def _read_globs(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def load_sensitive_globs(cwd: str) -> list[str]:
    """The sensitive-path glob list (P1b): a present project override file
    REPLACES the shipped defaults wholesale. A PRESENT-but-unreadable override
    fails open — floor OFF ([]), logged — never a fallback to defaults the
    project meant to replace, never a crash. Defaults absent/unreadable → []
    (no list, no floor)."""
    if cwd:
        override = Path(cwd) / SENSITIVE_GLOBS_OVERRIDE_REL
        try:
            if override.exists():
                return _read_globs(override)
        except Exception as e:
            log(f"sensitive-globs-override-unreadable path={override} err={e}")
            return []
    try:
        if SENSITIVE_GLOBS_DEFAULT.exists():
            return _read_globs(SENSITIVE_GLOBS_DEFAULT)
    except Exception as e:
        log(f"sensitive-globs-defaults-unreadable err={e}")
    return []


def matches_sensitive(file_path: str, globs: list[str]) -> bool:
    """Case-insensitive fnmatch against the path with a leading '/' prepended,
    so `*/auth/*` also matches a repo-relative `auth/login.php`. fnmatch's `*`
    crosses `/` boundaries by design — the list is segment/name shaped (see
    bin/sensitive-globs.txt for the anchoring calibration)."""
    if not file_path or not globs:
        return False
    p = "/" + file_path.replace("\\", "/").lower().lstrip("/")
    return any(fnmatch.fnmatch(p, g.lower()) for g in globs)


_TASKS_TASK_LINE_RE = re.compile(r"^- \[( |x|X)\] T\d+\b")
_TASKS_TEST_AUTHOR_RE = re.compile(
    r"^\s+Test-author:\s*(split|solo)\b\s*(?:[—-]\s*(.*))?$")
# harness-inversion FR-2/FR-7: a `Lane: behaviour` cluster's members carry NO
# Test-author line by design. The floor must still see them — a behaviour-mode
# close is a solo-class close (one agent, self-verified), so the sensitive-path
# floor applies to it exactly as to `solo`. Read from the cluster heading label
# (`· lane: behaviour`) or a `Lane:` line before the cluster's first task —
# the same two placements gate-check.py reads.
_TASKS_CLUSTER_RE = re.compile(r"^###\s+Cluster\b(.*)$", re.IGNORECASE)
_TASKS_LANE_LINE_RE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?Lane(?:\*\*)?:\s*(behaviou?r|contract)\b", re.IGNORECASE)
_TASKS_LANE_LABEL_RE = re.compile(r"\blane:\s*(behaviou?r|contract)\b", re.IGNORECASE)
# D1's stakes clause: a solo whose reason cites the cluster's demoted dial
# (`solo — standard stakes, …`) is the plan-sanctioned mode on a boundary task,
# not a self-downgrade. The citation lives in tasks.md — a machine artifact the
# planner wrote and gate-check's security-boundary-mode WARN vets — so honoring
# it here keeps the floor testimony-free. Mirrors gate-check.py's pattern.
_SOLO_STAKES_RE = re.compile(
    r"\b(?:standard|low)\b[^.\n]*\bstakes\b|\bstakes\b[^.\n]*\b(?:standard|low)\b",
    re.IGNORECASE)
_TASKS_FILES_RE = re.compile(r"\(files:\s*([^)]*)\)")
_SPECS_FEATURE_RE = re.compile(r"(?:^|/)specs/([^/]+)/")


def _basename(path: str) -> str:
    return (path or "").replace("\\", "/").rstrip("/").rsplit("/", 1)[-1].lower()


def resolve_task_mode(cwd: str, edited_paths: list[str]) -> str | None:
    """The current task's `Test-author:` mode ("split" | "solo"), resolved
    from the MACHINE artifact — tasks.md — never from the subagent-echoed
    evidence line (an echoed mode=split could only LOOSEN the sensitive
    floor, and testimony never loosens a verdict).

    Feature dir: the loop marker's feature_dir when armed, else the first
    edited path shaped specs/<feature>/….

    Current task — SERIALIZATION ASSUMPTION: the default heuristic is the
    FIRST unchecked task line (the loop/controller dispatch order — the
    controller checks the box only after the close). That assumes tasks are
    dispatched and closed SERIALLY; when [P] siblings are in flight
    simultaneously, the first unchecked line may be a SIBLING of the task
    actually closing here, and the mode can misresolve in EITHER direction —
    a sibling's `split` loosens the floor for a solo close (missed block), a
    sibling's `solo` fails closed (spurious block; cost = one stop
    round-trip). Disambiguation: when exactly one unchecked task's
    `(files: …)` basenames intersect the paths this subagent actually
    edited, that task's mode wins; zero or ambiguous intersection falls back
    to first-unchecked (never worse than the bare heuristic).

    Anything unresolvable — no marker and no specs path, no tasks.md, no
    unchecked task, no Test-author line on the resolved task (pre-0.8
    artifacts default to split upstream) — returns None and the caller fails
    open (no block)."""
    try:
        base = Path(cwd or ".")
        feature_dir = None
        marker_path = base / MARKER_REL
        if marker_path.exists():
            marker = json.loads(marker_path.read_text())
            fd = marker.get("feature_dir") or ""
            if fd:
                feature_dir = base / fd
        if feature_dir is None:
            for p in edited_paths:
                m = _SPECS_FEATURE_RE.search((p or "").replace("\\", "/"))
                if m:
                    feature_dir = base / "specs" / m.group(1)
                    break
        if feature_dir is None:
            return None
        tasks_path = feature_dir / "tasks.md"
        if not tasks_path.exists():
            return None

        # Collect every unchecked task: its (files: …) basenames + its mode.
        unchecked: list[dict] = []
        cur: dict | None = None
        in_fence = False
        lane = None          # the enclosing cluster's lane, once known
        seen_task = False    # a Lane: line counts only before the cluster's first task
        for ln in tasks_path.read_text().splitlines():
            if ln.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            cm = _TASKS_CLUSTER_RE.match(ln)
            if cm:
                lm = _TASKS_LANE_LABEL_RE.search(cm.group(1))
                lane = lm.group(1).lower() if lm else None
                seen_task = False
                cur = None
                continue
            if ln.startswith("#"):
                lane, seen_task, cur = None, False, None   # a phase boundary ends the cluster
                continue
            if not seen_task and lane is None:
                lm = _TASKS_LANE_LINE_RE.match(ln)
                if lm:
                    lane = lm.group(1).lower()
                    continue
            tm = _TASKS_TASK_LINE_RE.match(ln)
            if tm:
                seen_task = True
                cur = None
                if tm.group(1) == " ":
                    fm = _TASKS_FILES_RE.search(ln)
                    files = {_basename(tok) for tok in
                             (fm.group(1).split(",") if fm else [])
                             if tok.strip()}
                    cur = {"files": files,
                           "mode": "behaviour" if lane and lane.startswith("behavio") else None}
                    unchecked.append(cur)
                continue
            if cur is not None and cur["mode"] is None:
                am = _TASKS_TEST_AUTHOR_RE.match(ln)
                if am:
                    mode = am.group(1)
                    if (mode == "solo" and am.group(2)
                            and _SOLO_STAKES_RE.search(am.group(2))):
                        mode = "solo-demoted"  # D1 stakes clause — floor stands down
                    cur["mode"] = mode
        if not unchecked:
            return None

        edited_names = {_basename(p) for p in edited_paths if p}
        hits = [t for t in unchecked if t["files"] & edited_names]
        chosen = hits[0] if len(hits) == 1 else unchecked[0]
        return chosen["mode"]
    except Exception as e:
        log(f"resolve-task-mode-failed err={e}")
        return None


def emit_suite_green(cwd: str, cmd: str) -> None:
    """Append one `suite-green` event (sha + cmd) through bin/run-trace.py when
    a harness loop is armed for this cwd. Unarmed → skip silently. Fail-open:
    any failure is swallowed — trace emission must NEVER affect the block
    decision (mirrors loop-gate's trace() wrapper)."""
    try:
        marker_path = Path(cwd or ".") / MARKER_REL
        if not marker_path.exists():
            return
        marker = json.loads(marker_path.read_text())
        feature_dir = Path(cwd or ".") / (marker.get("feature_dir") or "")
        sha_proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=cwd or ".",
        )
        sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else "unknown"
        subprocess.run(
            [sys.executable, str(RUN_TRACE), "append", str(feature_dir),
             "suite-green", f"sha={sha}", f"cmd={cmd}"],
            capture_output=True, timeout=10, cwd=cwd or ".",
        )
        log(f"suite-green-traced feature={feature_dir} sha={sha}")
    except Exception as e:
        log(f"suite-green-trace-failed err={e}")


def project_has_linter(cwd: str) -> bool:
    """True if the project at cwd has a linter/formatter configured. The standards
    backstop fires only when this is True — enforce standards only where they are
    defined, so a project with no linter is never falsely blocked."""
    if not cwd:
        return False
    root = Path(cwd)
    config_names = [
        # JS/TS
        ".eslintrc", ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json",
        ".eslintrc.yml", ".eslintrc.yaml",
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts",
        ".prettierrc", ".prettierrc.json", ".prettierrc.js", ".prettierrc.cjs",
        ".prettierrc.yml", ".prettierrc.yaml", "prettier.config.js",
        "biome.json", "biome.jsonc",
        # PHP/WP
        "phpcs.xml", "phpcs.xml.dist", ".phpcs.xml", ".phpcs.xml.dist",
        ".php-cs-fixer.php", ".php-cs-fixer.dist.php",
        "phpstan.neon", "phpstan.neon.dist",
    ]
    for name in config_names:
        if (root / name).exists():
            return True
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            scripts = data.get("scripts", {}) or {}
            if "lint" in scripts or "format" in scripts:
                return True
            if any(tok in str(v) for v in scripts.values()
                   for tok in ("eslint", "prettier", "biome")):
                return True
            deps = {**(data.get("devDependencies") or {}), **(data.get("dependencies") or {})}
            if any(d in deps for d in ("eslint", "prettier", "@biomejs/biome")):
                return True
        except Exception:
            pass
    comp = root / "composer.json"
    if comp.exists():
        try:
            data = json.loads(comp.read_text())
            deps = {**(data.get("require") or {}), **(data.get("require-dev") or {})}
            if any(tok in d for d in deps
                   for tok in ("phpcs", "php_codesniffer", "php-cs-fixer", "wpcs",
                               "coding-standard", "phpstan")):
                return True
            scripts = data.get("scripts", {}) or {}
            # Word-bound, not raw substring: a script value like
            # "run analyses report" must not read as an analyse script.
            blob = " ".join(f"{k} {v}" for k, v in scripts.items())
            if re.search(r"\b(phpcs|phpstan|analy[sz]e)\b", blob):
                return True
        except Exception:
            pass
    return False


def build_block_message(activity: dict, missing: list[str],
                        details: dict | None = None) -> str:
    """The message Claude (the subagent) sees when we block its stop. `missing`
    is a subset of {"tests", "suite-red", "standards", "standards-red",
    "sensitive"} — the close-out gates not yet satisfied. `details` carries
    the facts the reason must name (suite cmd/exit, lint exit, sensitive
    paths)."""
    details = details or {}
    parts = [
        "netdust-agent/SubagentStop: close-out gate not satisfied.\n\n",
        f"You added {activity['lines_added']} lines of code in this task. Per "
        "the building spine, a task that ships new behavior is not complete "
        "until its close-out gates have actually executed — not just been "
        "intended, executed.\n",
    ]

    if "tests" in missing:
        parts.append(
            "\nMISSING — TESTS did not run. Run the suite via Bash:\n"
            "      bun test            (Bun/TS projects)\n"
            "      npx vitest run      (Node/Vitest)\n"
            "      vendor/bin/phpunit               (PHP/PHPUnit)\n"
            "      vendor/bin/codecept run unit     (Codeception)\n"
            "      ddev exec phpunit                (WP under DDEV)\n"
            "      composer gate       (or run the full gate — satisfies tests AND standards)\n"
        )

    if "suite-red" in missing:
        parts.append(
            "\nMISSING — SUITE IS RED. An implementer-class task may not stop "
            "on a failing suite (RED closes are the test-author's job, and "
            "only on test-path-only edits):\n"
            f"      suite: {details.get('suite_cmd', '<unknown>')}\n"
            f"      exit:  {details.get('suite_exit', 'non-zero')}\n"
            "Fix the failure (or escalate NEEDS_CONTEXT if the contract test "
            "is wrong — never weaken it), re-run the suite to green, and end "
            "with the updated HARNESS-EVIDENCE line.\n"
        )

    if "standards-red" in missing:
        parts.append(
            "\nMISSING — STANDARDS gate is RED. The linter ran and exited "
            f"non-zero (exit: {details.get('lint_exit', 'non-zero')}). Fix the "
            "violations (or justify narrowly inline), re-run to clean, and "
            "update the `Standards:` evidence line (and the optional "
            f"`lint=<code>` field). (See the {STANDARDS_SKILL} skill.)\n"
        )

    if "sensitive" in missing:
        paths = ", ".join(details.get("sensitive_paths", [])[:5]) or "<paths>"
        parts.append(
            "\nBLOCKED — SENSITIVE-PATH ROUTING FLOOR. This close edited "
            f"production path(s) on a security-boundary surface [{paths}] "
            "under a task whose tasks.md line reads `Test-author: solo`. The "
            "planner's hard rule — a Tier-A task on a security-boundary "
            "surface is ALWAYS split — has a machine floor here. Report "
            "NEEDS_CONTEXT to the controller: the task must be escalated to "
            "a split dispatch (independent test-author first) and the "
            "cluster's review tier promoted (building Step 2.8, one-way "
            "escalation). Do not silently re-classify the work, and do not "
            "edit the tasks.md mode yourself.\n"
        )

    if "standards" in missing:
        parts.append(
            "\nMISSING — STANDARDS gate. This project has a linter/formatter "
            "configured but you did not run it. Run it on the touched files:\n"
            "      npx eslint <files> && npx prettier --check <files>   (TS/JS)\n"
            "      vendor/bin/phpcs <files>                             (PHP/WP)\n"
            "      composer analyse | vendor/bin/phpstan analyse <files> (PHP static analysis)\n"
            "      composer gate       (or run the full gate — satisfies tests AND standards)\n"
            "Then record a `Standards: clean | <violations>` line in your "
            f"Test-evidence block. (See the {STANDARDS_SKILL} skill.)\n"
        )

    if "tests" in missing and not activity["invoked_testing"]:
        parts.append(
            "\nNote: you also did not invoke Skill(\"testing-workflow\"). It is "
            "not gating, but it loads the task-complete checklist (tier, "
            "RED-first, suite green, static analysis).\n"
        )

    parts.append(
        "\nFix the missing item(s), confirm green, then stop again. This hook "
        "fires once per stop cycle, so a second stop attempt passes through.\n"
        "If a gate fires in error (genuinely test-free task — doc edits, "
        "dead-code refactor), say so in your final response and stop again; the "
        "bypass is automatic."
    )
    return "".join(parts)


def main() -> None:
    try:
        raw = sys.stdin.read()
    except Exception as e:
        log(f"stdin-read-failed err={e}")
        sys.exit(0)

    try:
        hook_input = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        log(f"stdin-json-parse-failed raw_len={len(raw)}")
        sys.exit(0)

    # Avoid infinite block loops. Claude Code sets stop_hook_active=true on the
    # second stop attempt after we blocked the first. Let it through.
    if hook_input.get("stop_hook_active"):
        log("bypass reason=stop_hook_active")
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path or not Path(transcript_path).exists():
        log(f"no-transcript path={transcript_path!r}")
        sys.exit(0)

    messages = read_transcript(transcript_path)
    if not messages:
        log("empty-transcript")
        sys.exit(0)

    activity = scan_subagent_activity(messages)

    log(
        f"scanned msgs={len(messages)} "
        f"edited={activity['edited_code']} "
        f"added={activity['lines_added']} "
        f"removed={activity['lines_removed']} "
        f"net={activity['net_additions']} "
        f"invoked_testing={activity['invoked_testing']} "
        f"ran_tests_bash={activity['ran_tests_via_bash']} "
        f"ran_lint_bash={activity['ran_lint_via_bash']}"
    )

    # Decision rules (2026-05-27, revised):
    #  - No code edits in this transcript → let it stop.
    #  - lines_added < GATE_MIN_ADDITIONS AND net_additions ≤ 0 → auto-pass.
    #    Two ways a task can be a no-op:
    #      a) tiny diff (typo / 1-2 line tweak) — covered by lines_added check
    #      b) delete-only or net-zero rename — covered by net_additions check
    #    BOTH conditions must hold to auto-pass — this closes the
    #    refactor-swap gap (50 added + 50 removed → net 0 but real new
    #    behavior). A refactor-swap has lines_added ≥ GATE_MIN_ADDITIONS so
    #    it falls through to the gating check below.
    #  - Otherwise → require a test command actually executed via Bash.
    #    Skill("testing-workflow") invocation is logged but NOT gating —
    #    invoking a skill is one tool call; it does not prove the checklist
    #    was walked. Running the suite is the only evidence we can verify.
    #
    # Counts are computed from the transcript, NOT `git diff HEAD`.
    # Subagents commit work before SubagentStop fires, so working-tree
    # diffs read zero post-commit — that swallowed 231 gates in 24h on
    # phase-2.6. The transcript is the authoritative record of what THIS
    # subagent did in THIS run.
    if not activity["edited_code"]:
        sys.exit(0)

    is_tiny = activity["lines_added"] < GATE_MIN_ADDITIONS
    is_net_noop = activity["net_additions"] <= 0
    if is_tiny and is_net_noop:
        log(
            f"auto-pass reason=no-op-task "
            f"added={activity['lines_added']} net={activity['net_additions']}"
        )
        sys.exit(0)

    # ── The evidence contract (testimony-seams P0) ────────────────────────
    # Designed evidence (the HARNESS-EVIDENCE line) first, scraped evidence
    # (tool_result of the last test/lint command) as fallback. Testimony can
    # tighten a verdict, never loosen it.
    evidence = parse_evidence_line(messages)
    results = collect_tool_results(messages)

    # Resolve the ROLE from facts. test-author (run-only gate; RED is its job)
    # is honored iff every edited code path is a test path. A production-path
    # edit makes it an implementer regardless of the claim; an explicit
    # implementer claim on a test-only edit is honored (a claim can tighten).
    claimed_role = (evidence or {}).get("role")
    all_test_paths = bool(activity["code_paths"]) and all(
        _is_test_path(p) for p in activity["code_paths"]
    )
    role = "test-author" if (all_test_paths and claimed_role != "implementer") \
        else "implementer"

    # Resolve the SUITE status from BOTH channels and reconcile (C1b): the
    # evidence line (only when its suite command is recognized as a real test
    # command — no echo-grade pseudo-tests; the recognizer is the SAME
    # TEST_CMD_PATTERN a real run must match, so composer gate / bin/gate.sh
    # claims count too) AND the scraped last test-command tool_result. When
    # both are known and they disagree, the RED one wins (max severity —
    # testimony can tighten a scraped fact, never loosen it). Neither known
    # → exit unknown.
    ev_suite = None
    if (evidence is not None and "exit" in evidence
            and TEST_CMD_PATTERN.search(evidence.get("suite") or "")):
        ev_suite = {"green": evidence["exit"] == 0,
                    "exit": str(evidence["exit"]),
                    "cmd": evidence["suite"], "source": "evidence"}
    scraped = scraped_run_status(activity["test_runs"], results)
    sc_suite = {**scraped, "source": "scraped"} if scraped is not None else None

    if ev_suite is not None and sc_suite is not None:
        if ev_suite["green"] != sc_suite["green"]:
            suite = sc_suite if not sc_suite["green"] else ev_suite
        else:
            suite = ev_suite
    else:
        suite = ev_suite if ev_suite is not None else sc_suite

    # C1a: testimony never substitutes for the run itself. The tests gate is
    # satisfied ONLY by an actual Bash tool-use matching TEST_CMD_PATTERN —
    # the evidence line contributes exit/role/mode knowledge above, nothing
    # more.
    tests_ran = activity["ran_tests_via_bash"]

    # Resolve the LINT status the same way (the standards backstop upgrade:
    # "lint ran" → "lint ran and exited 0"; unknown exit stays ran-only).
    lint = None
    if evidence is not None and "lint" in evidence:
        lint = {"green": evidence["lint"] == 0, "exit": str(evidence["lint"])}
    else:
        scraped_lint = scraped_run_status(activity["lint_runs"], results)
        if scraped_lint is not None:
            lint = {"green": scraped_lint["green"], "exit": scraped_lint["exit"]}
    lint_ran = activity["ran_lint_via_bash"] or lint is not None

    # Which close-out gates are unmet?
    #  - TESTS: always required for a non-no-op code change; an implementer's
    #    suite must additionally be GREEN when its exit is known.
    #  - STANDARDS: required only when the project has a linter configured
    #    (enforce only where standards are defined — never block a project that
    #    has no linter), and RED lint blocks when the exit is known.
    cwd = hook_input.get("cwd", "")
    has_linter = project_has_linter(cwd)
    missing = []
    details: dict = {}
    if not tests_ran:
        missing.append("tests")
    elif role == "implementer" and suite is not None and not suite["green"]:
        missing.append("suite-red")
        details["suite_cmd"] = suite["cmd"]
        details["suite_exit"] = suite["exit"]
    if has_linter:
        if not lint_ran:
            missing.append("standards")
        elif lint is not None and not lint["green"]:
            missing.append("standards-red")
            details["lint_exit"] = lint["exit"]

    # ── The sensitive-path routing floor (testimony-seams P1b) ────────────
    # D1's hard rule — a Tier-A boundary task at effective-`high` stakes is
    # ALWAYS split — gets a machine floor here, keyed to the paths ACTUALLY
    # edited. The mode comes from tasks.md (machine artifact), NEVER from the
    # subagent-echoed evidence line: an echoed mode could only loosen the
    # floor, and testimony never loosens a verdict. A "solo-demoted" mode
    # (the task's solo reason cites its cluster's standard/low stakes — D1's
    # sanctioned demotion, also read from tasks.md) passes the floor.
    # Unresolvable mode → fail-open (no block).
    sensitive_hits: list[str] = []
    globs = load_sensitive_globs(cwd)
    if role == "implementer" and globs:
        candidates = [p for p in activity["code_paths"]
                      if p and not _is_test_path(p)
                      and matches_sensitive(p, globs)]
        if candidates and resolve_task_mode(cwd, activity["edited_paths"]) in ("solo", "behaviour"):
            sensitive_hits = candidates
            missing.append("sensitive")
            details["sensitive_paths"] = sensitive_hits

    log(
        f"evidence role={role} claimed={claimed_role} "
        f"suite={suite} lint={lint} sensitive={len(sensitive_hits)}"
    )

    # Record the green fact for the loop ledger (loop-check's FINISHED
    # consumes it): implementer suite verified green + loop armed → one
    # suite-green trace event. C1c: this event MINTS the fact loop-check
    # trusts, so it fires only when a SCRAPED green corroborates (matching
    # Bash run, non-error tool_result = exit 0) — never on the evidence line
    # alone. Emitted on the fact, independent of other gates; never affects
    # the decision.
    if (role == "implementer" and suite is not None and suite["green"]
            and sc_suite is not None and sc_suite["green"]):
        emit_suite_green(cwd, suite["cmd"])

    if not missing:
        sys.exit(0)

    # Block the stop and feed the message back to the subagent.
    decision_payload = {
        "decision": "block",
        "reason": build_block_message(activity, missing, details),
    }
    log(f"blocked missing={','.join(missing)} has_linter={has_linter}")
    print(json.dumps(decision_payload))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"unhandled-exception err={e}")
        sys.exit(0)
