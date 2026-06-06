#!/usr/bin/env python3
"""
subagent-stop.py — netdust-core harness

SubagentStop hook. Fires when a subagent considers stopping.

Purpose:
  Backstop for harnessed-development's testing gate. If a subagent wrote code (Edit/Write)
  but never invoked Skill("testing-workflow") to gate task completion, this
  hook blocks the stop and tells the subagent to invoke it now.

  This catches the case where the parent dispatched a subagent without the
  required "invoke testing-workflow before reporting done" instruction in the
  prompt, or where the subagent ignored the instruction.

Design:
  • Deterministic: regex over the subagent's transcript. No LLM call.
  • Cheap: < 100ms typical.
  • Bypass: respects stop_hook_active to avoid infinite loops if the subagent
    re-stops without invoking the skill (we only block once per subagent).
  • Silent on non-code subagents: research/explore subagents that don't edit
    code are not gated.

Logs to ~/.claude/logs/memory-hook.log (shared with session-stop.py).
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

LOG_PATH = Path.home() / ".claude" / "logs" / "memory-hook.log"

# Tool names that indicate the subagent modified code.
CODE_EDITING_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

# Skill we coach the subagent to invoke. Not gating — soft signal that the
# subagent walked the testing-workflow checklist. The hard gate is whether
# tests actually ran (see ran_tests_via_bash).
COACHING_SKILL = "testing-workflow"

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
    lines_added = 0
    lines_removed = 0

    test_cmd_pattern = re.compile(
        r"\b("
        r"vendor/bin/(phpunit|codecept)|"
        r"(ddev exec )?(phpunit|codecept)|"
        r"npx (vitest|playwright|jest)|"
        r"composer test|"
        r"npm (run )?test|pnpm test|yarn test|"
        r"bun (run )?(test|vitest|playwright)|"
        r"bunx (vitest|playwright|jest)"
        r")\b"
    )

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
                if not _is_code_path(tool_input.get("file_path") or ""):
                    continue
                edited = True
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
                if test_cmd_pattern.search(cmd):
                    ran_tests_bash = True

    return {
        "edited_code": edited,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "net_additions": lines_added - lines_removed,
        "invoked_testing": invoked_testing,
        "ran_tests_via_bash": ran_tests_bash,
    }


def build_block_message(activity: dict) -> str:
    """The message Claude (the subagent) sees when we block its stop."""
    coaching = ""
    if not activity["invoked_testing"]:
        coaching = (
            "\n\nNote: You also did not invoke Skill(\"testing-workflow\"). The "
            "skill is not gating — but it loads the task-complete checklist "
            "(test exists, test was red first, full suite green, static "
            "analysis clean). If you skipped it, you may have skipped the "
            "discipline too. Invoke it before re-running the suite."
        )

    return (
        "netdust-core/SubagentStop: testing gate not satisfied.\n\n"
        f"You added {activity['lines_added']} lines of code in this task and "
        "did not run the test suite. Per the harnessed-development skill "
        "(testing-workflow gate), "
        "a task that ships new behavior is not complete until tests for it "
        "have actually executed — not just been written, executed.\n\n"
        "Required:\n"
        "  - Run the test suite via Bash. Examples:\n"
        "      bun test          (Bun/TS projects)\n"
        "      npx vitest run    (Node/Vitest)\n"
        "      vendor/bin/phpunit               (PHP/PHPUnit)\n"
        "      vendor/bin/codecept run unit     (Codeception)\n"
        "      ddev exec phpunit                (WP under DDEV)\n\n"
        "Confirm the suite is green, then stop again. This hook fires once "
        "per stop cycle, so a second stop attempt passes through."
        f"{coaching}\n\n"
        "If this gate fires in error (genuinely test-free task — doc edits, "
        "dead-code refactor, formatting), say so out loud in your final "
        "response and stop again; the bypass is automatic."
    )


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
        f"ran_tests_bash={activity['ran_tests_via_bash']}"
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

    if activity["ran_tests_via_bash"]:
        sys.exit(0)

    # Block the stop and feed the message back to the subagent.
    decision_payload = {
        "decision": "block",
        "reason": build_block_message(activity),
    }
    log("blocked reason=missing-testing-workflow-invocation")
    print(json.dumps(decision_payload))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"unhandled-exception err={e}")
        sys.exit(0)
