#!/usr/bin/env python3
"""
pretooluse-guard.py — netdust-gates

PreToolUse hook. Fires before a tool call executes. For Bash commands it
pattern-matches a conservative denylist of destructive actions and asks for
human confirmation before they run.

Purpose:
  Every other guardrail is post-hoc (a review catches "you didn't test" after
  the code exists). NOTHING intercepts `rm -rf`,
  `git push --force`, a direct push to main, `DROP TABLE`, or a prod cache
  flush BEFORE it runs. CLAUDE.md / RULES.md encode the intent, but that is
  advice the model can skip — not an enforced invariant. This hook makes the
  highest-risk irreversible actions surface a permission prompt deterministically,
  regardless of what the model intends. It is the execution-time Control floor
  named in the harness-completeness plan (Item 2) and its parked threat model
  (docs/harness-engineering-hardening-plan.md).

Decision policy (v1 — conservative, favor `ask` over `deny`):
  • A matched destructive pattern → permissionDecision "ask" (surface the
    literal command to a human; the model's stated intent is NOT trusted).
  • Everything else, any non-Bash tool, any parse failure → no output
    (passthrough): the call proceeds through the normal permission flow.
  v1 deliberately uses `ask` for ALL Bash patterns, never `deny` — a hard deny
  risks blocking legit work, and `ask` already stops the autonomous/injected
  case (a human sees the literal command).
  The deny tier (2026-09-02): the flow floor — a raw git write that bypasses the
  branch flow; the correction is agent-side and costs one tool call.

CRITICAL — fails OPEN. Per the Claude Code hook contract, exit 2 is the only
exit code that blocks a tool on the hook's own authority; any other exit code
(incl. crashes) lets the tool proceed. This script therefore wraps everything
in try/except and ALWAYS exits 0 — a malformed payload, an unexpected tool
shape, or an internal bug can never brick a session by blocking every call.
The guard adds friction on matched patterns; it never removes the ability to
work.

Output contract (when a pattern matches):
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "ask",
                          "permissionDecisionReason": "<why>"}}

Logs to ~/.claude/logs/memory-hook.log (shared with the other hooks).
"""

import hashlib
import json
import os
import subprocess
import re
import sys
from pathlib import Path
from datetime import datetime

LOG_PATH = Path.home() / ".claude" / "logs" / "memory-hook.log"

# The tools main() acts on. hooks.json must match every one (tests/test_hooks_wiring.py).
HANDLED_TOOLS = ("Bash", "Write", "Edit", "NotebookEdit")


def log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] pretooluse-guard: {msg}\n")
    except Exception:
        pass


# Denylist v1. Each entry: (label, compiled regex). The regex matches the
# command STRING. Patterns are anchored to command position where it matters
# so that a literal substring inside a quoted argument (grep 'DROP TABLE',
# echo 'rm -rf /') does NOT trip the guard — the dominant false-positive class.
#
# `(?m)` + a command-boundary prefix `(?:^|[;&|]\s*|\b(?:then|do|else)\s+)` lets
# us catch a destructive command at the start of the line OR after a shell
# separator (`;`, `&&`, `||`, `|`) or a control keyword, while a leading
# `echo`/`grep`/`cat`/`#` keeps the literal-in-argument cases out.
_SEP = r"(?:^|[;&|]\s*|\b(?:then|do|else)\s+)(?:\w+=\S*\s+)*"

DENYLIST: list[tuple[str, re.Pattern]] = [
    # Attack 1 — rm with BOTH recursive and force flags, as an actual command:
    # combined (-rf / -fr / -Rf) or separate (-r -f / -f -r), either order.
    # `rm -r` alone (recursive, not forced) is intentionally NOT in v1 — the
    # irreversible-without-prompt case is the force flag.
    ("rm -rf (recursive force delete)",
     re.compile(
         rf"(?m){_SEP}rm\s+(?:"
         r"-\S*r\S*f\S*|-\S*f\S*r\S*"
         r"|-[A-Za-z]*r[A-Za-z]*\s+-[A-Za-z]*f[A-Za-z]*"
         r"|-[A-Za-z]*f[A-Za-z]*\s+-[A-Za-z]*r[A-Za-z]*"
         r")",
         re.IGNORECASE)),

    # Attack 2 — git force-push, +refspec, or direct push to main/master.
    ("git force-push or +refspec",
     re.compile(rf"(?m){_SEP}git\s+push\b.*(?:--force(?:-with-lease)?|\s-[A-Za-z]*f|\s\+\S+:)", re.IGNORECASE)),
    # main/master must be a WHOLE ref argument (optionally a refspec destination
    # `HEAD:main` or a fully-qualified `refs/heads/main`) — a branch name that
    # merely contains the word (`feature/main-nav`) must not trip the guard.
    ("git push directly to main/master",
     re.compile(rf"(?m){_SEP}git\s+push\b[^\n]*[\s+](?:\S*:|refs/heads/)?(?:main|master)(?=\s|$)", re.IGNORECASE)),

    # Attack 5 — destructive SQL as an executed statement (mysql -e '...', psql -c).
    ("destructive SQL (DROP/TRUNCATE)",
     re.compile(r"(?:-e|-c|--execute|--command)\s*[\"'][^\"']*\b(?:DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE)\b", re.IGNORECASE)),

    # Destructive WP-CLI db subcommands.
    ("destructive wp-cli db (reset/drop)",
     re.compile(rf"(?m){_SEP}wp\s+(?:.*\s)?db\s+(?:reset|drop)\b", re.IGNORECASE)),

    # RULES.md rule 10 — cache/redis flush (destroys VAD's LMS cache exclusions).
    ("redis/cache flush (RULES.md rule 10)",
     re.compile(rf"(?m){_SEP}(?:redis-cli\s+(?:.*\s)?FLUSH(?:ALL|DB)|wp\s+(?:.*\s)?cache\s+flush)\b", re.IGNORECASE)),
]


# ── The vendored-package floor (2026-09-04) ─────────────────────────────────
#
# Netdust projects install netdust/ntdst-core, ntdst-baseline and netdust-flow
# with `composer --prefer-source`, so `vendor/<vendor>/<pkg>/` is a REAL git
# checkout of another repository. Editing one in place looks like it works and
# does not:
#
#   · `vendor/` is outside this project's deploy.payload, so the fix never
#     reaches a server — the deploy is a closed list and does not carry it;
#   · the next `composer install` / `composer update` overwrites it silently;
#   · the change is committed to nothing — it is not in this repo's history and
#     not in the package's either.
#
# The fix belongs in that package's own checkout, on its own branch, through
# its own flow, then released and pulled back by composer.
#
# `ask`, not `deny`, per this guard's policy: a temporary probe while debugging
# is legitimate, and a human seeing the path is enough to catch the case where
# it was meant to be a real fix. node_modules/ is the same shape for JS.
VENDOR_DIRS = ("vendor", "node_modules")


def _vendor_package_root(file_path: str) -> tuple[str, str] | None:
    """(<vendor-dir>, <package root>) when file_path sits inside a vendored
    package, else None. The package root is the directory two levels below the
    vendor dir (composer's <vendor>/<name>), or the vendor dir itself when the
    path is shallower."""
    try:
        parts = Path(file_path).resolve().parts
    except Exception:
        parts = Path(file_path).parts
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] in VENDOR_DIRS:
            pkg = parts[: i + 3] if len(parts) >= i + 3 else parts[: i + 1]
            return parts[i], str(Path(*pkg))
    return None


def check_vendor_floor(hook_input: dict) -> dict | None:
    """Ask before writing inside a vendored package. None to pass through."""
    tool_input = hook_input.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not isinstance(file_path, str) or not file_path:
        return None

    found = _vendor_package_root(file_path)
    if found is None:
        return None
    vendor_dir, pkg_root = found

    # A package with its own .git is a --prefer-source checkout: it HAS a real
    # home to fix this in, and saying so is the whole point of the message.
    try:
        is_checkout = (Path(pkg_root) / ".git").exists()
    except Exception:
        is_checkout = False

    if is_checkout:
        detail = (
            f"{pkg_root} is a real git checkout (composer --prefer-source). "
            f"Fix it THERE — its own branch, its own flow, release, then "
            f"`composer update` here. See netdust-devops:parallel-work."
        )
    else:
        detail = (
            f"{pkg_root} is dependency-managed. Change it upstream, or record a "
            f"patch your dependency tool re-applies — never by hand here."
        )

    reason = (
        f"netdust-gates guard: this writes inside `{vendor_dir}/`. That edit "
        f"does not survive and does not ship: `{vendor_dir}/` is outside this "
        f"project's deploy.payload, so it never reaches a server, and the next "
        f"install overwrites it. {detail} "
        f"Confirm only if this is a deliberate throwaway probe."
    )
    log(f"ask reason=vendor-floor path={file_path!r} pkg={pkg_root!r} checkout={is_checkout}")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }


# ── The flow floor (harness-inversion FR-24, 2026-09-02) ─────────────────────
#
# On a project carrying `site.yml`, the Makefile's verbs are the only door to a rung
# branch (the branches site.yml binds to environments). Agents routed around the flow
# when a verb died on a git error, or simply skipped it; the last gate — the deploy
# gate — refused hours after a commit landed on the wrong rung. This floor denies the
# raw git writes that bypass the flow AT THE COMMAND, naming the make verb that does it
# right. `deny`, not `ask`: the correction is
# agent-side and costs one tool call. `make …` commands are never inspected — the verbs
# are the door — except when input is PIPED into a confirming verb, which is the one
# way to run `make ship` without a human typing yes.
#
# Rung names: `scripts/site environments.<e>.branch` when that reader is present (the
# project's own truth), else a dependency-free read of `branch:` lines under
# `environments:` in site.yml, else the fleet defaults. No site.yml anywhere up to the
# git toplevel → not a flow project → this floor does not exist. Every tooling failure
# (git missing, unreadable cwd, a subprocess timeout) fails OPEN like the rest of the hook.

FLOW_DEFAULT_RUNGS = ("main", "master", "staging", "development")
FLOW_CONFIRMING_VERBS = r"(?:ship|unpromote|promote|deploy)"
# A make invocation that reaches a confirming verb (the verb must END there —
# `deploy-test` is not `deploy`).
FLOW_MAKE_CONFIRM = re.compile(
    rf"\bmake\b(?:\s+[^\s|<>;&'\"]+)*\s+{FLOW_CONFIRMING_VERBS}(?=[\s'\";&|)]|$)", re.IGNORECASE)
# …with its stdin forged: a pipe into it, ANY `<` redirect/here-doc/here-string in the
# command, or a pty/shell wrapper. The Makefile's own `[ -t 0 ]` check is the closing
# fix (a forged stdin is not a terminal); this is the belt.
FLOW_STDIN_FORGERY = re.compile(
    r"(?:\|\s*(?:[^\s|]+\s+)*?make\b|<|\b(?:expect|script|unbuffer|socat)\b|\b(?:sh|bash|zsh|dash)\s+-[a-z]*c\b)",
    re.IGNORECASE)
# Where a git write may start: the line, a shell separator/grouping, a command
# substitution, a control keyword, a wrapper, or an env assignment.
_FLOW_SEP = (r"(?:^|[;&|(){}]\s*|\$\(\s*|`\s*|\b(?:then|do|else)\s+"
             r"|\b(?:command|time|nice|sudo|exec|env)\s+(?:\w+=\S*\s+)*|(?:\b\w+=\S*\s+)+)")
# `git` with any global options between it and the verb (`-C path`, `-c k=v`, `--no-pager`, `-P`),
# an escaped `\git`, and a quoted verb.
_FLOW_GIT = r"\\?git(?:\s+(?:-[cC]\s*\S+|-[pP]\b|--[\w-]+(?:=\S+)?))*\s+['\"]?"
FLOW_WRITE_ON_BRANCH = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}(commit|merge|rebase|cherry-pick|am|revert|reset|"
    rf"checkout\s+-b|switch\s+-c|branch\s+(?:-f|--force|-M|-m)|update-ref|symbolic-ref|"
    rf"stash\s+(?:pop|apply))(?=[\s'\"]|$)", re.IGNORECASE)
FLOW_RESET_MOVES_REF = re.compile(r"--(?:hard|keep|merge|soft|mixed)\b|\bHEAD[~^]|@\{|\b[0-9a-f]{7,40}\b", re.IGNORECASE)
FLOW_PUSH = re.compile(rf"(?m){_FLOW_SEP}{_FLOW_GIT}push\b([^\n;&|]*)", re.IGNORECASE)
FLOW_FETCH = re.compile(rf"(?m){_FLOW_SEP}{_FLOW_GIT}fetch\b([^\n;&|]*)", re.IGNORECASE)
FLOW_BRANCH_DELETE = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}branch\s+(?:-[dD]|--delete)(?:\s+(?:-f|--force))?\s+(\S+)", re.IGNORECASE)
# a ref write that NAMES a rung — denied from any branch, the current one is irrelevant
FLOW_REF_WRITE = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}(?:branch\s+(?:-f|--force|-M|-m)\s+(\S+)|update-ref\s+(?:refs/heads/)?(\S+))",
    re.IGNORECASE)
FLOW_SWITCH_TO = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}(?:checkout|switch)(?:\s+-(?![bBcC]\b|-orphan)[a-zA-Z-]+)*\s+(?!-)(\S+)", re.IGNORECASE)

FLOW_VERB_FOR = {
    "commit": "make feature name=<x> first (a rung is deploy-only), then commit there",
    "merge": "make promote name=<x> — staging is rebuilt from production, never merged into by hand",
    "rebase": "make promote name=<x> — staging is rebuilt, never rebased",
    "cherry-pick": "make hotfix name=<x>, then make ship",
    "am": "make hotfix name=<x>, then make ship",
    "revert": "make hotfix name=<x> carrying the revert, then make ship",
    "reset": "make rollback env=<name> — a rung's history is the deploy ledger",
    "checkout -b": "make feature name=<x> / make hotfix name=<x> — they pick the right base from site.yml",
    "switch -c": "make feature name=<x> / make hotfix name=<x> — they pick the right base from site.yml",
    "branch -f": "make promote name=<x> — staging's pointer moves only by a rebuild, production's only by make ship",
    "update-ref": "make promote name=<x> — staging's pointer moves only by a rebuild, production's only by make ship",
    "symbolic-ref": "make feature name=<x> — never re-point HEAD at a rung by hand",
    "stash pop": "make feature name=<x>, then pop the stash there",
    "stash apply": "make feature name=<x>, then apply the stash there",
    "push": "make promote name=<x> (it pushes staging) or make deploy env=<name>",
    "fetch": "make promote name=<x> — staging is rebuilt by the flow, never by a fetch refspec",
    "branch -D": "make promote name=<x> / make unpromote name=<x> — a rung is never deleted; staging is rebuilt",
}


def _rung_named(args: str, rungs: set[str]) -> str | None:
    """A rung named as a WHOLE ref token in push/fetch args: `staging`,
    `HEAD:staging`, `+staging`, `refs/heads/staging`, `:staging`
    (delete) — never `feature/main-nav` or `hotfix/staging-fix`."""
    for b in rungs:
        if re.search(rf"(?:^|[\s:+])(?:refs/heads/)?{re.escape(b)}(?=\s|$)", args):
            return b
    return None


def _flow_project_root(cwd: str) -> Path | None:
    """The nearest ancestor of cwd (inclusive) carrying site.yml, stopping at the git
    toplevel or the filesystem root. None → not a flow project."""
    try:
        d = Path(cwd).resolve()
    except Exception:
        return None
    for p in (d, *d.parents):
        if (p / "site.yml").is_file():
            return p
        if (p / ".git").exists():
            return None
    return None


def _flow_rungs(root: Path) -> set[str]:
    """Branch names bound to environments. A dependency-free read of `branch:` lines
    under `environments:` in site.yml FIRST — this hook fires on every Bash call, and
    the reviewer measured ~160 ms per call when scripts/site ran N+1 interpreters;
    the regex costs nothing. `scripts/site` (the project's own reader) only when the
    regex finds nothing (an exotic YAML shape), then the fleet defaults."""
    try:
        text = (root / "site.yml").read_text()
        m = re.search(r"(?ms)^environments:\s*\n(.*?)(?=^\S|\Z)", text)
        if m:
            found = {v.strip("'\"") for v in re.findall(r"^\s+branch:\s*([^\s#]+)", m.group(1), re.M)}
            found.discard("")
            if found:
                return found
    except Exception as e:  # noqa: BLE001
        log(f"flow-floor site.yml read failed err={e}")
    reader = root / "scripts" / "site"
    if reader.is_file():
        try:
            envs = subprocess.run([sys.executable, str(reader), "environments"], cwd=root,
                                  capture_output=True, text=True, timeout=3)
            if envs.returncode == 0:
                out = set()
                for e in envs.stdout.split()[:12]:
                    r = subprocess.run([sys.executable, str(reader), f"environments.{e}.branch"],
                                       cwd=root, capture_output=True, text=True, timeout=3)
                    if r.returncode == 0 and r.stdout.strip():
                        out.add(r.stdout.strip())
                if out:
                    return out
        except Exception as e:  # noqa: BLE001 — fail open to the defaults
            log(f"flow-floor scripts/site failed err={e}")
    return set(FLOW_DEFAULT_RUNGS)


def _flow_current_branch(root: Path) -> str | None:
    try:
        r = subprocess.run(["git", "branch", "--show-current"], cwd=root,
                           capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception as e:  # noqa: BLE001
        log(f"flow-floor git failed err={e}")
        return None


def _flow_deny(what: str, verb: str, detail: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"netdust-gates flow floor: {what} bypasses the branch flow this project's "
            f"Makefile owns ({detail}). Use the verb instead: {verb}. The Makefile is the "
            f"only door to a rung branch: features and hotfixes branch from production; "
            f"staging is rebuilt by make promote, and production moves only by make ship."),
    }}


def check_flow_floor(hook_input: dict) -> dict | None:
    """Return a deny decision for a raw git write that bypasses the flow, else None."""
    try:
        tool_input = hook_input.get("tool_input") or {}
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        if not isinstance(command, str) or not command.strip():
            return None
        root = _flow_project_root(hook_input.get("cwd") or "")
        if root is None:
            return None

        m = FLOW_MAKE_CONFIRM.search(command)
        if m and FLOW_STDIN_FORGERY.search(command):
            return _flow_deny(f"forging stdin for `{m.group(0).strip()}`",
                              "run the verb and type the confirmation yourself — a confirming "
                              "verb is a human moment by design (the Makefile refuses a "
                              "non-terminal stdin too)",
                              "a typed confirmation is the operator's, never piped or redirected")

        rungs = _flow_rungs(root)
        current = _flow_current_branch(root)
        switches = FLOW_SWITCH_TO.findall(command)
        # the branch a write lands on: the LAST checkout/switch in the command, else current
        landing = switches[-1] if switches else current
        on_rung = landing in rungs
        where = f"on `{landing}`"

        m = FLOW_WRITE_ON_BRANCH.search(command)
        if m and on_rung:
            key = re.sub(r"\s+", " ", m.group(1).lower())
            if key == "reset" and not FLOW_RESET_MOVES_REF.search(command[m.end():m.end() + 200]):
                pass  # `git reset <paths>` unstages; the pointer does not move
            else:
                key = "branch -f" if key.startswith("branch") else key
                return _flow_deny(f"`git {key}` {where}", FLOW_VERB_FOR.get(key, "the make verb"),
                                  "a rung branch is deploy-only")

        m = FLOW_REF_WRITE.search(command)
        if m and any(t and t.split(":")[0] in rungs for t in m.groups()):
            key = "branch -f" if "branch" in m.group(0).lower() else "update-ref"
            return _flow_deny(f"`git {key}` re-pointing a rung", FLOW_VERB_FOR[key], "a rung pointer")

        m = FLOW_PUSH.search(command)
        if m:
            args = m.group(1)
            named = _rung_named(args, rungs)
            if named or re.search(r"--(?:all|mirror)\b", args) or (
                    on_rung and not re.search(r"\b(?:feature|hotfix)/", args)):
                return _flow_deny(f"`git push` of a rung branch {where}", FLOW_VERB_FOR["push"],
                                  "the flow pushes a rung only after it merged into it")

        m = FLOW_FETCH.search(command)
        if m:
            dest = re.findall(r"\S+:(?:refs/heads/)?(\S+)", m.group(1))
            if any(d in rungs for d in dest):
                return _flow_deny("`git fetch` with a refspec into a rung", FLOW_VERB_FOR["fetch"],
                                  "a rung pointer moved by a refspec")

        m = FLOW_BRANCH_DELETE.search(command)
        if m and m.group(1) in rungs:
            return _flow_deny(f"`git branch -D {m.group(1)}`", FLOW_VERB_FOR["branch -D"],
                              "a rung branch")
        return None
    except Exception as e:  # noqa: BLE001 — fail OPEN, always
        log(f"flow-floor error err={e}")
        return None


def ask_tier_waived() -> bool:
    """NETDUST_GUARD_ASK=off|0|false|no in the HOOK process environment (settings
    `env`, or the shell that launched Claude) turns the ask tier into a logged
    passthrough for unattended runs. The deny-tier floors are never waived, and an
    inline prefix on the Bash command string never reaches this process."""
    return os.environ.get("NETDUST_GUARD_ASK", "").strip().lower() in ("off", "0", "false", "no")


def match_denylist(command: str) -> tuple[str, str] | None:
    """Return (label, matched_text) for the first denylist hit, else None.
    A command that begins with a read-only echo/grep/cat is treated as inert
    (the destructive token is data, not an executed command)."""
    if not command or not command.strip():
        return None
    for label, pat in DENYLIST:
        m = pat.search(command)
        if m:
            return label, m.group(0).strip()
    return None


# ── The plan-review floor ────────────────────────────────────────────────────
#
# A plan that is OPEN on this branch — uncommitted, or committed here but not on
# the production rung — is reviewed by a fresh subagent before product code is
# written (`/plan-review`). The review is a file, `specs/<f>/plan-review.md`,
# naming the plan's git blob: `Reviewed-plan: <sha>`. The guard checks the file
# and the hash, nothing else — a plan edited after its review is open again.
#
# Legacy plans already on the production rung are not this branch's work. Writes
# under specs/, memory/, tasks/ and docs/ are how the plan and the review get
# written, so they are never refused. Fails open on anything unreadable.
PLAN_REVIEW_EXEMPT = ("specs", "memory", "tasks", "docs")
PLAN_REVIEW_LINE = re.compile(r"^Reviewed-plan:\s*([0-9a-f]{40})\s*$", re.M)


def _git_blob(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except Exception:
        return None
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _git_toplevel(cwd: str) -> Path | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                           capture_output=True, text=True, timeout=3)
    except Exception:
        return None
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def _production_rung(root: Path) -> str | None:
    """The production branch: site.yml's, else main, else master — whichever exists."""
    site = _flow_project_root(str(root))
    candidates: list[str] = []
    if site is not None:
        try:
            text = (site / "site.yml").read_text()
            m = re.search(r"(?ms)^\s+production:\s*\n(.*?)(?=^\s{0,2}\S|\Z)", text)
            if m:
                b = re.search(r"^\s+branch:\s*([^\s#]+)", m.group(1), re.M)
                if b:
                    candidates.append(b.group(1).strip("'\""))
        except Exception:
            pass
    candidates += ["main", "master"]
    for name in candidates:
        r = subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{name}"],
                           cwd=root, capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return name
    return None


def _open_plans(root: Path) -> list[Path]:
    """specs/*/plan.md that carry work of this branch: uncommitted, or with commits
    the production rung does not have."""
    plans = sorted((root / "specs").glob("*/plan.md")) if (root / "specs").is_dir() else []
    if not plans:
        return []
    rung = _production_rung(root)
    open_plans = []
    for plan in plans:
        rel = str(plan.relative_to(root))
        status = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=root,
                                capture_output=True, text=True, timeout=3).stdout.strip()
        if status:
            open_plans.append(plan)
            continue
        if rung is None:
            continue
        ahead = subprocess.run(["git", "log", "--oneline", f"{rung}..HEAD", "--", rel], cwd=root,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        if ahead:
            open_plans.append(plan)
    return open_plans


def check_plan_review_floor(hook_input: dict) -> dict | None:
    """Deny a product-code write while an open plan has no review of its current text."""
    tool_input = hook_input.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not isinstance(file_path, str) or not file_path:
        return None
    try:
        root = _git_toplevel(hook_input.get("cwd") or str(Path(file_path).parent))
        if root is None:
            return None
        target = Path(file_path).resolve()
        rel = target.relative_to(root.resolve())
    except Exception:
        return None
    if rel.parts and rel.parts[0] in PLAN_REVIEW_EXEMPT:
        return None
    try:
        for plan in _open_plans(root):
            blob = _git_blob(plan)
            review = plan.with_name("plan-review.md")
            names = PLAN_REVIEW_LINE.findall(review.read_text()) if review.is_file() else []
            if blob is not None and blob in names:
                continue
            feature = plan.parent.name
            why = ("has no plan-review.md" if not names
                   else "was edited after its review — the review names an older version")
            reason = (
                f"netdust-gates plan-review floor: specs/{feature}/plan.md is open on this "
                f"branch and {why}. A plan is reviewed by a fresh subagent before product "
                f"code is written: run /plan-review {feature}. Writing under specs/, memory/, "
                f"tasks/ or docs/ is not refused."
            )
            log(f"deny reason=plan-review-floor plan={plan!s} path={file_path!r}")
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                           "permissionDecision": "deny",
                                           "permissionDecisionReason": reason}}
    except Exception as e:  # noqa: BLE001 — fail open
        log(f"plan-review-floor passthrough err={e}")
    return None


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        log("passthrough reason=empty-stdin")
        return  # exit 0, no output → proceed

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        log(f"passthrough reason=stdin-json-parse-failed raw_len={len(raw)}")
        return  # fail OPEN

    tool_name = hook_input.get("tool_name", "")
    if tool_name not in HANDLED_TOOLS:
        return  # passthrough
    if tool_name != "Bash":
        # every path-carrying tool reaches the vendored-package floor, then the plan-review floor
        decision = check_vendor_floor(hook_input) or check_plan_review_floor(hook_input)
        if decision is not None:
            print(json.dumps(decision))
        return

    tool_input = hook_input.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not command.strip():
        return  # nothing to match → passthrough

    flow = check_flow_floor(hook_input)   # FR-24 — deny, before the ask-tier denylist
    if flow is not None:
        log(f"deny reason=flow-floor cmd={command[:80]!r}")
        print(json.dumps(flow))
        return

    hit = match_denylist(command)
    if not hit:
        return  # benign → passthrough (normal permission flow decides)

    label, matched = hit
    if ask_tier_waived():
        log(f"passthrough reason=unattended-waiver label={label!r} matched={matched!r}")
        return

    reason = (
        f"netdust-gates guard: this command matches a destructive pattern "
        f"({label}). The harness asks for explicit confirmation before "
        f"irreversible actions (rm -rf, force-push / push-to-main, DROP/"
        f"TRUNCATE, db reset/drop, cache flush) — regardless of stated intent. "
        f"Matched: {matched!r}. Confirm only if you intend exactly this."
    )
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    log(f"ask reason={label!r} matched={matched!r}")
    print(json.dumps(decision))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fail OPEN: never block a tool call because the guard itself broke.
        log(f"unhandled-exception err={e} (failing open)")
    sys.exit(0)
