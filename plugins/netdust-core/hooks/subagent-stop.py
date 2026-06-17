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

# Standards backstop (goal #2): when a project has a linter/formatter configured,
# a code-editing task should also have RUN it. Enforced ONLY where standards are
# actually defined (project_has_linter) — projects without a linter are never
# falsely blocked. The authoritative enforcement is the standards-gate skill's
# close-out evidence line; this hook is the deterministic backstop, mirroring the
# testing gate.
STANDARDS_SKILL = "standards-gate"

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
    ran_lint_bash = False
    lines_added = 0
    lines_removed = 0

    lint_cmd_pattern = re.compile(
        r"\b("
        r"(npx |bunx )?(eslint|prettier|biome)\b|"
        r"vendor/bin/(phpcs|phpcbf|php-cs-fixer)\b|"
        r"(ddev exec )?(phpcs|phpcbf|php-cs-fixer)\b|"
        r"(npm run|pnpm run|pnpm|yarn|bun run) (lint|format|cs|cs-fix|lint:fix)\b|"
        r"composer (run-script )?(lint|phpcs|cs|cs-fix|format)\b"
        r")"
    )

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
                if lint_cmd_pattern.search(cmd):
                    ran_lint_bash = True

    return {
        "edited_code": edited,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "net_additions": lines_added - lines_removed,
        "invoked_testing": invoked_testing,
        "ran_tests_via_bash": ran_tests_bash,
        "ran_lint_via_bash": ran_lint_bash,
    }


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
                   for tok in ("phpcs", "php_codesniffer", "php-cs-fixer", "wpcs", "coding-standard")):
                return True
            scripts = data.get("scripts", {}) or {}
            if any("phpcs" in str(k) or "phpcs" in str(v) for k, v in scripts.items()):
                return True
        except Exception:
            pass
    return False


def build_block_message(activity: dict, missing: list[str]) -> str:
    """The message Claude (the subagent) sees when we block its stop. `missing` is
    a subset of {"tests", "standards"} — the close-out gates not yet satisfied."""
    parts = [
        "netdust-core/SubagentStop: close-out gate not satisfied.\n\n",
        f"You added {activity['lines_added']} lines of code in this task. Per "
        "harnessed-development, a task that ships new behavior is not complete "
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
        )

    if "standards" in missing:
        parts.append(
            "\nMISSING — STANDARDS gate. This project has a linter/formatter "
            "configured but you did not run it. Run it on the touched files:\n"
            "      npx eslint <files> && npx prettier --check <files>   (TS/JS)\n"
            "      vendor/bin/phpcs <files>                             (PHP/WP)\n"
            "Then record a `Standards: clean | <violations>` line in your "
            "Test-evidence block. (See the standards-gate skill.)\n"
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

    # Which close-out gates are unmet?
    #  - TESTS: always required for a non-no-op code change.
    #  - STANDARDS: required only when the project has a linter configured
    #    (enforce only where standards are defined — never block a project that
    #    has no linter). Mirrors the testing gate; closes goal #2.
    cwd = hook_input.get("cwd", "")
    has_linter = project_has_linter(cwd)
    missing = []
    if not activity["ran_tests_via_bash"]:
        missing.append("tests")
    if has_linter and not activity["ran_lint_via_bash"]:
        missing.append("standards")

    if not missing:
        sys.exit(0)

    # Block the stop and feed the message back to the subagent.
    decision_payload = {
        "decision": "block",
        "reason": build_block_message(activity, missing),
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
