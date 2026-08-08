#!/usr/bin/env python3
"""
subagent-stop.py — netdust-agent harness

SubagentStop hook. Fires when a subagent considers stopping.

Purpose:
  Backstop for the building spine's testing gate (Step 2.6/2.6b). If a subagent wrote code (Edit/Write)
  but never invoked Skill("testing-workflow") to gate task completion, this
  hook blocks the stop and tells the subagent to invoke it now.

  This catches the case where the parent dispatched a subagent without the
  required "invoke testing-workflow before reporting done" instruction in the
  prompt, or where the subagent ignored the instruction.

  Same backstop shape for two more close-out gates:
    • STANDARDS — a configured linter must have actually run (project_has_linter).
    • DRIFT     — on projects that carry the ntdst-core framework, the PHP the
                  subagent wrote must pass netdust-wp's drift-check.py. Unlike
                  the other two, this one RUNS the check rather than asking
                  whether it appeared in the transcript: "did you run it" is
                  exactly the remember-to-invoke failure this gate exists to
                  fix, and running it lets the block say WHAT is wrong instead
                  of that something might be. Scoped to the lines the subagent
                  actually wrote — nobody gets blocked by pre-existing drift.

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
import os
import re
import subprocess
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

# Framework-drift backstop. Mirrors the standards gate's shape exactly: it fires
# ONLY where the rules apply — a project carrying the ntdst-core framework — so a
# project without it is never blocked. That conditional is the single most
# important property here; this hook can halt every agent close in every project.
#
# Difference from the other two gates: those check that a command APPEARED in the
# transcript. This one RUNS drift-check.py on the files the subagent edited. The
# rules are a fast local grep with no side effects, and "did you remember to run
# the reviewer" is the precise failure mode being fixed — the optional
# ntdst-drift-reviewer owned this rule set for months and prevented nothing
# (13/13 consumer projects hand-roll get_post_meta past the Data layer).
#
# FAIL OPEN, unconditionally: script missing, exit code we don't understand,
# unparseable output, timeout, any exception → the stop is ALLOWED. A hook that
# blocks because the hook broke halts all work and teaches people to bypass the
# mechanism, which costs more than the drift it would have caught.
DRIFT_SCRIPT_ENV = "NTDST_DRIFT_CHECK"      # explicit override (tests, odd installs)
DRIFT_TIMEOUT_SEC = 8                       # pathological input must not hang a close
DRIFT_MAX_LINES_PER_CHECK = 12              # matches drift-check.py's own report cap

# Where the framework lives, relative to the project root. Presence of one of
# these is what puts a project in scope.
FRAMEWORK_DIR_CANDIDATES = (
    "web/app/mu-plugins/ntdst-core",     # Bedrock
    "app/mu-plugins/ntdst-core",
    "wp-content/mu-plugins/ntdst-core",  # classic WP
    "mu-plugins/ntdst-core",
    "ntdst-core",
)

# Only PHP under these path segments is framework-governed code. Everything else
# (build scripts, root-level PHP, tooling) is out of the drift rules' scope.
DRIFT_PATH_MARKERS = ("/mu-plugins/", "/themes/")

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


def _edit_written_text(tool_name: str, tool_input: dict) -> str:
    """The text this tool_use PUT INTO the file (new content only).

    Used to attribute a drift finding to the subagent: a finding whose offending
    line does not appear in anything this subagent wrote is pre-existing drift,
    and blocking on it would make the gate the kind everybody disables.
    """
    if tool_name == "Edit":
        return tool_input.get("new_string") or ""
    if tool_name == "Write":
        return tool_input.get("content") or ""
    if tool_name == "NotebookEdit":
        return tool_input.get("new_source") or ""
    if tool_name == "MultiEdit":
        return "\n".join(
            (e.get("new_string") or "")
            for e in (tool_input.get("edits") or [])
            if isinstance(e, dict)
        )
    return ""


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
        "written_by_file":      dict,  # file_path -> text this subagent wrote into it
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
    written_by_file: dict[str, list[str]] = {}

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
                # Only count edits to code files. A subagent that writes only
                # docs/specs/.md reports (research, planning) has nothing to
                # test and must not be gated. Path missing/unknown → treated
                # as code (gate stays on).
                path = tool_input.get("file_path") or ""
                if not _is_code_path(path):
                    continue
                edited = True
                a, r = _edit_line_counts(tool_name, tool_input)
                lines_added += a
                lines_removed += r
                if path:
                    written_by_file.setdefault(path, []).append(
                        _edit_written_text(tool_name, tool_input)
                    )

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
        "written_by_file": {k: "\n".join(v) for k, v in written_by_file.items()},
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


def project_has_framework(cwd: str):
    """Return the project's ntdst-core directory, or None.

    The drift backstop fires ONLY when this is not None — the exact counterpart
    of project_has_linter(). A project without the framework has no framework to
    drift from and must never be blocked by this gate.
    """
    if not cwd:
        return None
    root = Path(cwd)
    for rel in FRAMEWORK_DIR_CANDIDATES:
        p = root / rel
        if p.is_dir():
            return p
    # Safety net for layouts the explicit list doesn't name. Bounded depth so
    # this stays a few stat() calls, not a tree walk.
    for pattern in ("*/mu-plugins/ntdst-core", "*/*/mu-plugins/ntdst-core"):
        for p in root.glob(pattern):
            if p.is_dir():
                return p
    return None


def find_drift_script():
    """Locate netdust-wp's drift-check.py, or None (→ gate no-ops, fail open).

    This hook ships in netdust-agent; the script ships in netdust-wp. Both the
    dev-repo layout (plugins/<plugin>/…) and the installed cache layout
    (cache/<marketplace>/<plugin>/<version>/…) are supported, plus the stable
    ~/.claude/plugins symlink.
    """
    override = os.environ.get(DRIFT_SCRIPT_ENV)
    if override:
        p = Path(override).expanduser()
        return p if p.is_file() else None

    here = Path(__file__).resolve()
    candidates = []
    if len(here.parents) > 2:
        # dev repo: plugins/netdust-agent/hooks/ → plugins/netdust-wp/bin/
        candidates.append(here.parents[2] / "netdust-wp" / "bin" / "drift-check.py")
    candidates.append(Path.home() / ".claude" / "plugins" / "netdust-wp" / "bin" / "drift-check.py")
    if len(here.parents) > 3:
        # installed cache: <marketplace>/netdust-agent/<ver>/hooks/
        candidates += sorted(
            here.parents[3].glob("netdust-wp/*/bin/drift-check.py"), reverse=True
        )
    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def drift_scope_files(activity: dict, cwd: str) -> list[str]:
    """The PHP files under mu-plugins/ or themes/ that this subagent edited.

    Derived from scan_subagent_activity's record, NOT re-derived from git: the
    subagent has usually committed by the time SubagentStop fires, so a
    working-tree diff reads empty (the same trap that swallowed 231 test gates).
    """
    files = []
    for raw in activity.get("written_by_file", {}):
        path = Path(raw)
        if not path.is_absolute() and cwd:
            path = Path(cwd) / path
        posix = path.as_posix()
        if not posix.lower().endswith(".php"):
            continue
        if not any(marker in posix for marker in DRIFT_PATH_MARKERS):
            continue
        try:
            if path.is_file():
                files.append(str(path.resolve()))
        except OSError:
            continue
    return sorted(set(files))


def run_drift_check(script, files: list[str]):
    """Run drift-check.py on `files`. Returns a findings list, or None when the
    result is indeterminate — and None means ALLOW THE STOP.

    drift-check.py exit codes: 0 clean, 1 findings, 2 bad invocation. Anything
    else (crash, signal, timeout) is indeterminate by definition.
    """
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--json", *files],
            capture_output=True,
            text=True,
            timeout=DRIFT_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        log(f"drift indeterminate reason=timeout secs={DRIFT_TIMEOUT_SEC}")
        return None
    except Exception as e:
        log(f"drift indeterminate reason=spawn-failed err={e}")
        return None

    if proc.returncode not in (0, 1):
        log(f"drift indeterminate reason=exit-{proc.returncode} stderr={proc.stderr.strip()[:200]!r}")
        return None

    try:
        payload = json.loads(proc.stdout)
        findings = payload["findings"]
        if not isinstance(findings, list):
            raise ValueError("findings is not a list")
    except Exception as e:
        log(f"drift indeterminate reason=unparseable err={e}")
        return None

    return findings


def attribute_findings(findings: list[dict], written_by_file: dict, cwd: str) -> list[dict]:
    """Keep only findings on a line THIS subagent wrote.

    drift-check scans whole files; a subagent that touched one method of a file
    with long-standing drift elsewhere in it did not introduce that drift and
    must not be blocked by it. The offending line (`code`, stripped) is matched
    against the text the subagent put into that file. Unmatched → pre-existing →
    dropped. Errs toward under-blocking, which is the safe direction.
    """
    by_resolved = {}
    for raw, text in written_by_file.items():
        p = Path(raw)
        if not p.is_absolute() and cwd:
            p = Path(cwd) / p
        try:
            by_resolved[str(p.resolve())] = text
        except OSError:
            by_resolved[str(p)] = text

    mine = []
    for f in findings:
        code = (f.get("code") or "").strip()
        if not code:
            continue
        try:
            key = str(Path(f.get("file", "")).resolve())
        except OSError:
            key = f.get("file", "")
        if code in by_resolved.get(key, ""):
            mine.append(f)
    return mine


def evaluate_drift(activity: dict, cwd: str) -> list[dict]:
    """The whole drift gate, wrapped so no failure can escape as a block.

    Every early return is [] — meaning "nothing to block on". The gate only ever
    produces findings on the happy path: framework project + PHP the subagent
    wrote + script found + clean run + attributable hits.
    """
    try:
        framework = project_has_framework(cwd)
        if framework is None:
            return []

        files = drift_scope_files(activity, cwd)
        if not files:
            return []

        script = find_drift_script()
        if script is None:
            log("drift skipped reason=script-not-found")
            return []

        findings = run_drift_check(script, files)
        if findings is None:
            return []          # indeterminate → fail open

        mine = attribute_findings(findings, activity.get("written_by_file", {}), cwd)
        log(
            f"drift scanned files={len(files)} total={len(findings)} "
            f"attributed={len(mine)} framework={framework}"
        )
        return mine
    except Exception as e:
        log(f"drift indeterminate reason=unhandled err={e}")
        return []


def _display_path(path: str, cwd: str) -> str:
    if not cwd:
        return path
    try:
        return str(Path(path).resolve().relative_to(Path(cwd).resolve()))
    except (ValueError, OSError):
        return path


def format_drift_findings(findings: list[dict], cwd: str) -> str:
    """Group by (check, message) the way drift-check.py's own report does — a
    malformed `ntdst-allow` carries a different message from a plain hit."""
    grouped: dict[tuple[str, str], list[dict]] = {}
    for f in findings:
        grouped.setdefault((f.get("check", "?"), f.get("message", "")), []).append(f)

    out = []
    for (key, message), group in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        out.append(f"  ■ {key} — {message}\n")
        out.append(f"    → {group[0].get('fix', '')}\n")
        for f in group[:DRIFT_MAX_LINES_PER_CHECK]:
            out.append(
                f"      {_display_path(f.get('file', ''), cwd)}:{f.get('line', '?')}"
                f"  {f.get('code', '')}\n"
            )
        if len(group) > DRIFT_MAX_LINES_PER_CHECK:
            out.append(f"      … and {len(group) - DRIFT_MAX_LINES_PER_CHECK} more\n")
    return "".join(out)


def build_block_message(activity: dict, missing: list[str],
                        drift_findings: list[dict] | None = None,
                        cwd: str = "") -> str:
    """The message Claude (the subagent) sees when we block its stop. `missing` is
    a subset of {"tests", "standards", "drift"} — the close-out gates not yet
    satisfied."""
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
        )

    if "standards" in missing:
        parts.append(
            "\nMISSING — STANDARDS gate. This project has a linter/formatter "
            "configured but you did not run it. Run it on the touched files:\n"
            "      npx eslint <files> && npx prettier --check <files>   (TS/JS)\n"
            "      vendor/bin/phpcs <files>                             (PHP/WP)\n"
            "Then record a `Standards: clean | <violations>` line in your "
            f"Test-evidence block. (See the {STANDARDS_SKILL} skill.)\n"
        )

    if "drift" in missing and drift_findings:
        parts.append(
            "\nMISSING — FRAMEWORK CONFORMANCE. This project carries ntdst-core, "
            "and drift-check.py flags "
            f"{len(drift_findings)} line(s) YOU wrote in this task (pre-existing "
            "drift elsewhere in these files was not counted):\n\n"
        )
        parts.append(format_drift_findings(drift_findings, cwd))
        parts.append(
            "\nEach one has a framework primitive that does the job properly — "
            "the `→` line names it. Two acceptable resolutions, no third:\n"
            "  1. FIX it — route through the primitive named above.\n"
            "  2. ANNOTATE it, if this is a deliberate, documented exception:\n"
            "         // ntdst-allow: <check-key> — <why this is correct here>\n"
            "     The reason is mandatory; an allow with no reason after the dash "
            "is itself a finding. Write the justification a reviewer would need, "
            "and cite the doc (ARCHITECTURE-INVARIANTS.md, a lessons entry) if one "
            "exists. Do NOT annotate a hit you have not actually justified — that "
            "is silencing the check, not using the escape hatch.\n"
            "Re-run it yourself to confirm:\n"
            "      python3 <netdust-wp>/bin/drift-check.py <files>\n"
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

    cwd = hook_input.get("cwd", "")

    # Drift is evaluated BEFORE the no-op auto-pass: it is about WHAT the code is,
    # not how much of it there is. A one-line swap can introduce a raw wp_ajax_
    # handler. evaluate_drift() returns [] on every failure path, so a broken
    # drift gate simply restores the previous behaviour.
    drift_findings = evaluate_drift(activity, cwd)

    is_tiny = activity["lines_added"] < GATE_MIN_ADDITIONS
    is_net_noop = activity["net_additions"] <= 0
    if is_tiny and is_net_noop and not drift_findings:
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
    #  - DRIFT: required only when the project carries ntdst-core AND the
    #    subagent wrote PHP under mu-plugins/ or themes/ AND drift-check.py
    #    flagged a line it actually wrote. Same conditional shape as STANDARDS,
    #    and computed above so a no-op-sized edit that still introduces drift
    #    doesn't slip through the tiny-diff auto-pass.
    has_linter = project_has_linter(cwd)
    missing = []
    if not activity["ran_tests_via_bash"]:
        missing.append("tests")
    if has_linter and not activity["ran_lint_via_bash"]:
        missing.append("standards")
    if drift_findings:
        missing.append("drift")

    if not missing:
        sys.exit(0)

    # Block the stop and feed the message back to the subagent.
    decision_payload = {
        "decision": "block",
        "reason": build_block_message(activity, missing, drift_findings, cwd),
    }
    log(f"blocked missing={','.join(missing)} has_linter={has_linter} "
        f"drift={len(drift_findings)}")
    print(json.dumps(decision_payload))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"unhandled-exception err={e}")
        sys.exit(0)
