# Phase 1 Memory-Hook Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five audited defects in netdust-agent's live memory hooks (Track B removal, GLOBAL.md injection, plugin-version resolution, dedup hardening, Layer-B write exclusion) in the source repo, and land them in the installed plugin cache verifiably.

**Architecture:** All edits land in `/home/ntdst/Projects/netdust-plugins` (the canonical checkout; `origin git@github.com:netdust/netdust-plugins.git`, branch `main`) — NEVER in `~/.claude/plugins/cache/`. The live hooks are netdust-agent's (`plugins/netdust-agent/hooks/`); netdust-core's `hooks.json` is `{"hooks": {}}` (dead copies — do not touch its hooks). Repo hooks are currently **byte-identical** to the installed 0.3.0 cache, so all line numbers below are exact at repo HEAD (commit `26d9a65`). Delivery is: version bump in `.claude-plugin/marketplace.json` → commit → push → `claude plugin update` (canonical), with `scripts/sync.sh` as the dev-iteration fast path (fixed in Task 6 so it targets the right cache dir).

**Tech Stack:** Python 3 stdlib only (no pip deps, no pytest — the repo's `tests/run.sh` convention), bash, `installed_plugins.json` (Claude Code's version-2 install registry).

## Global Constraints

- **Hooks must never block or fail a session.** Every exit path in `session-stop.py` stays `sys.exit(0)`; the top-level catch-all stays. `session-start.sh` keeps `set -u` (no `set -e`) and its self-resolving `CLAUDE_PLUGIN_ROOT` fallback (L13).
- **Python: stdlib only.** No new imports beyond stdlib; no pytest (not installed — verified 2026-07-03).
- **Test convention:** each `tests/test_*.py` module exposes `run() -> list[tuple[bool, str]]`; the suite runs via `bash tests/run.sh` (all modules must stay green). Integration-style tests run the REAL hook via `subprocess` against a fabricated JSONL transcript with per-message top-level `uuid` — see `tests/test_stop_hook_idempotency.py` for the canonical fixture helpers (`_msg`, `_write_transcript`, `_run_hook`). No mocks.
- **HOME-isolation for anything touching `~/.claude`:** tests that exercise `installed_plugins.json`, symlinks, or logs set `HOME` to a temp dir in the subprocess env (`Path.home()` respects `HOME` on Linux; the bash script uses `$HOME` throughout).
- **Scope: exactly the 5 approved fixes.** No Track B replacement, no "block-once tag nudge" (explicitly deferred by the user), no netdust-core hook resurrection, no GLOBAL.md content pruning.
- **Edit target:** `/home/ntdst/Projects/netdust-plugins` only. The cache at `~/.claude/plugins/cache/netdust-plugins/` is a build artifact.
- Line numbers cited below are exact at commit `26d9a65`. Task 1 deletes ~120 lines from `session-stop.py`, so Tasks 2–3 reference **function names** as anchors, not line numbers.

---

## Gate decisions (Stage 1, Class A)

### 1a — Threat model: does NOT fire (trigger walk)

Run against the trigger list literally:

| Trigger | Touched? |
|---|---|
| User-controlled URLs / outbound request to user-supplied address | No — and Task 1 **deletes** the hooks' only outbound HTTP call (`call_haiku_api` → `api.anthropic.com`). |
| Auth / session / token surfaces | No — Task 1 **removes** the only credential handling (`ANTHROPIC_API_KEY`). |
| Untrusted parsing | No new parsing of third-party input. Inputs are the local Claude Code transcript JSONL (machine-written, local trust domain) and `installed_plugins.json` (Claude Code's own registry, local). Both are parsed defensively (fall back on any error) per the hooks' existing style. |
| BYOK credentials | Removed, not added. |
| Multi-tenancy / workspace boundaries | No. |

Net effect of this phase is a **shrinking** attack surface (one outbound call and one env-credential read deleted). No `## Threat model` section required. Pre-existing consideration noted, out of scope: transcript text Claude echoes (which can quote web content) is persisted into memory files by Track A — that behavior predates this phase and is unchanged by it.

### 1b — Architecture invariants: no doc exists; authoring deferred

No `ARCHITECTURE-INVARIANTS.md` anywhere in the repo (verified by `find`). Authoring a full invariants doc for the plugins monorepo is out of proportion for a 5-fix bundle and would widen scope. Instead, the two convergence points this plan **creates** are named explicitly and enforced by the sibling-site audits below:

1. **Active-plugin-version resolution** converges on `installed_plugins.json`'s `installPath` (single resolver semantics, three call sites — Tasks 4/5/6). mtime is demoted to a labeled fallback only.
2. **Project memory-write exclusion** converges on ONE early-exit check in `session-stop.py:main()` (Task 3) — every write path (STATE/lessons/todo/sidecar/gitignore/git-commit/dashboard-sync) sits downstream of it.

Deferral: promote these into a repo-level `ARCHITECTURE-INVARIANTS.md` when the repo next gets a Class-A feature (not this phase).

### 1g — Feature acceptance: n/a

No user-facing feature — hooks infrastructure only. No acceptance-flows matrix. Behavioral proof is the per-task subprocess tests plus the live-delivery verification in Task 8.

### 1c — Premise ground-truth (audit vs repo HEAD)

Repo `plugins/netdust-agent/hooks/` is byte-identical to the installed 0.3.0 cache (`diff -rq`: only `__pycache__` differs). Audit claims verified against source:

| Audit claim | Verified at repo HEAD |
|---|---|
| `call_haiku_api` ~L251–333 | Exact (L251–333). |
| `ANTHROPIC_API_KEY` gate ~L679 | Exact (L679; Track B block L677–696; `haiku=` log field L720). |
| `session-start.sh` GLOBAL read ~L136 | Exact (L136); netdust-agent has **no** `memory/` dir; the real file is `plugins/netdust-core/memory/GLOBAL.md` (4001 bytes; injected copy at netdust-core 0.2.1 cache). |
| Symlink refresh ~L123–133 via `ls -1t \| head -1` | Exact (block L115–133, `ls -1t` at L129). |
| `_netdust_plugin_dirs()` ~L500–513 mtime-max | Function spans **L486–519**; the env-var branch with `max(..., st_mtime)` is L500–513 (max at L511). Minor drift only. |
| 0.2.1 mtime 4 ms newer than 0.3.0 | Confirmed: `0.2.1` 2026-06-23 09:49:56.108 vs `0.3.0` …56.104; symlink `~/.claude/plugins/netdust-agent` currently → **0.2.1** (stale). |
| Sidecar ring resets on loss; watermark written after appends | Confirmed: `captured_hashes` capped at 200 (L54, L368); sidecar is gitignored (L541–555); appends L657–696 precede the sidecar write L713–718. |
| netdust-core `hooks.json` empty | Confirmed: `{"hooks": {}}`. |

**New findings the audit missed** (folded into scope where they are the same defect):

- `scripts/sync.sh` resolves the target cache version with `ls -1t | head -1` in **two** places (sync loop and verify loop) — the same mtime defect. Left unfixed, this phase's own delivery would sync fixes into the stale `0.2.1` dir. Included as Task 6 (same fix class, delivery-path-blocking).
- The netdust-wp symlink shows the bug class beyond the 4 ms race: it points at `0.4.1` (newest mtime, synced from the working tree today) while `installed_plugins.json` says `0.4.0` is installed.
- `installed_plugins.json` is **version-2 schema**: `{"plugins": {"<name>@<marketplace>": [{"installPath": "...", "version": "..."}]}}` — resolvers must split the key on `@` and take `entries[0].installPath`.
- `subagent-stop.py` is clean of both defect classes (no memory writes to the project, no version resolution) — no sibling work there.

### Decision record (small decisions this plan settles; `doubting-decisions` not loaded — the core approach is a user-approved fix list, not an open architectural choice; the two mechanism decisions below are ground-truthed against source, with alternatives stated)

**Fix 2 — GLOBAL.md ownership: MOVE it into `plugins/netdust-agent/memory/GLOBAL.md` (git mv from netdust-core).** Rationale:
- Zero code change: `session-start.sh` L136 already reads `${CLAUDE_PLUGIN_ROOT}/memory/GLOBAL.md`, and `CLAUDE_PLUGIN_ROOT` at fire time is netdust-agent's own install path. Moving the file makes the existing line correct.
- Survives plugin updates: the file ships inside the plugin, so every new version dir carries it. Pointing at netdust-core's path instead would require cross-plugin version resolution — the exact bug class fix 3 kills — and would couple netdust-agent to netdust-core being installed, violating agent's documented "standalone, self-contained" contract (`plugins/netdust-agent/CLAUDE.md`).
- Ownership split: netdust-core's hooks are dead (`{"hooks": {}}`); netdust-agent owns the memory hooks; the file its hook injects should live with the hook.
- Deferral (out of scope): GLOBAL.md's "Active priorities" section is mutable content that now requires a repo commit + plugin update to change; its natural long-term home is Layer B (`~/Sites/netdust-wp-manager/memory/GLOBAL.md`, manual). Flag for a later phase; do not prune content now.

**Fix 5 — exclusion mechanism: marker file `.no-auto-memory` at the project root**, checked once at the top of `session-stop.py:main()`. Rationale: file-presence checks are the codebase's idiom (`DASHBOARD_SYNC.exists()`, `daily_marker_already_written`, sidecar existence); a root-level marker covers ALL hook writes for that project (`memory/`, `tasks/`, `.gitignore`, git commit, dashboard sync) via one early exit — a single convergence point rather than per-writer guards; it generalizes to any future manual-only project without a code change (beats a hardcoded denylist) and needs no config plumbing (beats a config file). Deployment step (Task 8) creates the marker at `/home/ntdst/Sites/netdust-wp-manager/.no-auto-memory`.

**Fix 4 — coupling mechanism: make the appends idempotent (4a), keep the watermark write last.** With target-file content-dedup in place, a crash after append but before the sidecar write can no longer duplicate on re-fire — the target file itself becomes the durable dedup record (it is committed, unlike the gitignored sidecar). Writing the sidecar FIRST was the alternative and was rejected: it converts the failure mode from "duplicate" to "silent loss" (hashes recorded for content never written). Idempotent-append + watermark-last keeps at-least-once capture with exactly-once persistence.

---

## File structure

| File | Change |
|---|---|
| `plugins/netdust-agent/hooks/session-stop.py` | Task 1 (delete Track B), Task 2 (file-content dedup), Task 3 (marker exclusion), Task 4 (installPath resolver) |
| `plugins/netdust-agent/hooks/session-start.sh` | Task 5 (installPath symlink refresh); Task 7 needs no change here |
| `scripts/sync.sh` | Task 6 (installPath version pick, both loops) |
| `plugins/netdust-agent/memory/GLOBAL.md` | Task 7 (created via `git mv` from `plugins/netdust-core/memory/GLOBAL.md`) |
| `plugins/netdust-core/{README.md,RULES.md,CLAUDE.md}` | Task 7 (fix now-dangling GLOBAL.md references) |
| `.claude-plugin/marketplace.json` | Task 8 (version bumps) |
| `plugins/netdust-agent/tests/test_stop_hook_dedup.py` | New (Task 2) |
| `plugins/netdust-agent/tests/test_no_auto_memory.py` | New (Task 3) |
| `plugins/netdust-agent/tests/test_plugin_version_resolution.py` | New (Tasks 4–5) |
| `plugins/netdust-agent/tests/test_stop_hook_idempotency.py` | Task 1 (drop the now-moot `ANTHROPIC_API_KEY` env forcing comment — optional, keep green) |

Branch: create `fix/phase1-memory-hooks` off `main` before Task 1. One commit per task (see per-task commit steps).

---

## CLUSTER 1 — session-stop.py behavior (Tasks 1–3)

### Task 1: Remove Track B (Haiku summarizer) entirely

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-stop.py`

**Interfaces:**
- Produces: `session-stop.py` with Track A as the sole capture path; `done` log line WITHOUT the `haiku=` field. Later tasks edit the same `main()` — this task goes first so the file shrinks before they anchor into it.

**Test tier:** `no unit test: Tier B — pure code deletion with no new logic; regression evidence = full existing suite green (`bash tests/run.sh`) + the grep gate in Step 3 proving the surface is gone.`

- [ ] **Step 1: Delete the Track B code.** In `plugins/netdust-agent/hooks/session-stop.py` remove, top to bottom:
  - Module docstring: the whole "Track B — HAIKU SUMMARIZER" paragraph (L20–22) and the "Either track may run…" sentence (L24–25); reword the header so it describes ONE track: the deterministic tag scanner.
  - Config block: `HAIKU_MODEL` (L48), `HAIKU_TIMEOUT_SEC` (L49), `MAX_TRANSCRIPT_LINES` (L50), `MAX_EXISTING_STATE_LINES` (L52) — each is used only by Track B functions (verified: `MAX_TRANSCRIPT_LINES` only in `format_transcript_for_haiku`, `MAX_EXISTING_STATE_LINES` only in `read_existing_state`).
  - Imports: `urllib.request` (L40) and `urllib.error` (L41) — used only by `call_haiku_api` (verified by grep).
  - Functions: `format_transcript_for_haiku` (L134–154), `read_existing_state` (L157–166), the entire `call_haiku_api` (L251–333) including its section comment (L249).
  - Function `append_state` (L405–410) — its ONLY caller is the Track B block at L692 (verified by grep; Track A uses `append_state_from_tags`). Keep `append_state_marker` — the visibility marker still uses it.
  - In `main()`: the whole Track B block L677–696 (`haiku_status = ...` through the `written.append("todo.md(haiku)")` line, including the `ANTHROPIC_API_KEY` gate at L679).
  - Log line L720: change to `log(f"done cwd={cwd} tags=[{','.join(k for k,v in tags.items() if v)}] wrote=[{','.join(written)}]")` — the `haiku=` field is dropped entirely (clear absence; users approved either form).

- [ ] **Step 2: Run the existing suite — must stay green.**

Run: `bash /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests/run.sh`
Expected: `All harness tests passed.` (The idempotency tests force `ANTHROPIC_API_KEY: ""` in the subprocess env — harmless post-deletion; optionally delete that env line + its `# tag-scanner-only path` comment in `test_stop_hook_idempotency.py`'s `_run_hook`.)

- [ ] **Step 3: Grep gate — surface is gone.**

Run: `grep -n "haiku\|HAIKU\|api.anthropic.com\|ANTHROPIC_API_KEY\|urllib" /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/hooks/session-stop.py`
Expected: no matches (case-insensitive `haiku` may legitimately remain only if a comment explains the removal — prefer none).

- [ ] **Step 4: Update the agent plugin's own docs.**

Run: `grep -rln "Haiku\|Track B\|ANTHROPIC_API_KEY" /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent --include="*.md"`
For each hit that describes the Stop hook's capture tracks, delete/reword the Track B mention (Track A is now the only track). Do NOT touch netdust-core's docs here (its Track B description belongs to its dead hook copy; core doc drift is a known deferral — Task 7 touches core docs only for the GLOBAL.md move).

- [ ] **Step 5: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add plugins/netdust-agent
git commit -m "fix(netdust-agent): drop Track B Haiku summarizer from Stop hook — Track A tag scanner is the sole capture path"
```

---

### Task 2: Harden dedup — target file is the durable dedup record (fix 4a + 4b)

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-stop.py` (anchor: after `dedup_against_hashes`, and inside `main()` after the hash-ring dedup block; also inside `append_skill_edge`)
- Create: `plugins/netdust-agent/tests/test_stop_hook_dedup.py`

**Interfaces:**
- Produces: `_file_contains_normalized(path: Path, text: str) -> bool` (module-level, used by `main()` and `append_skill_edge`). Task 3 and 4 edit `main()` above/below this block — anchors are comments, not line numbers.

**Test tier:** `Tier A — test contract: after a first fire captures a tag, DELETING memory/.stop-hook-state.json and re-firing the same transcript appends NO duplicate to STATE.md/lessons.md/todo.md (denial path: content-dedup must hold with an empty hash ring), while a genuinely NEW tag on the same re-fire still appends exactly once (allow path). RED-first: this test FAILS against current HEAD (sidecar loss → full re-scan → duplicate).`

- [ ] **Step 1: Write the failing test.** Create `plugins/netdust-agent/tests/test_stop_hook_dedup.py`:

```python
"""
test_stop_hook_dedup.py — fix 4 (2026-07-03): dedup must survive sidecar loss.

The 200-entry captured_hashes ring lives in the GITIGNORED sidecar
(memory/.stop-hook-state.json). Lose the sidecar (fresh clone, cleanup,
crash before the sidecar write) and the ring resets — the old code then
re-appended every tag on the next full re-scan. The fix makes the TARGET
FILE the durable dedup record: before appending, the hook checks whether
the normalized tag body already exists in the target file.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-stop.py"


def _msg(role: str, text: str, uuid: str) -> dict:
    return {
        "type": role,
        "uuid": uuid,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _write_transcript(path: Path, messages: list[dict]) -> None:
    with open(path, "w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")


def _run_hook(cwd: Path, transcript: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    return subprocess.run(
        ["python3", str(HOOK)],
        input=payload, capture_output=True, text=True, timeout=10,
        env={**os.environ},
    )


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-dedup-"))
    try:
        cwd = tmp / "project"
        cwd.mkdir()
        transcript = tmp / "transcript.jsonl"
        msgs = [
            _msg("assistant", "DECISION: use marker files for hook exclusion", "u1"),
            _msg("assistant", "LESSON: sidecar hash ring is not durable", "u2"),
            _msg("assistant", "TODO: promote resolver into invariants doc", "u3"),
        ]
        _write_transcript(transcript, msgs)

        # Fire 1 — captures everything.
        _run_hook(cwd, transcript)
        state = (cwd / "memory" / "STATE.md").read_text()
        results.append((
            state.count("use marker files for hook exclusion") == 1,
            "fire 1 captures DECISION once",
        ))

        # Simulate sidecar loss, then re-fire the SAME transcript.
        sidecar = cwd / "memory" / ".stop-hook-state.json"
        results.append((sidecar.exists(), "sidecar exists after fire 1"))
        sidecar.unlink()
        _run_hook(cwd, transcript)

        state = (cwd / "memory" / "STATE.md").read_text()
        lessons = (cwd / "memory" / "lessons.md").read_text()
        todo = (cwd / "tasks" / "todo.md").read_text()
        results.append((
            state.count("use marker files for hook exclusion") == 1,
            "DENIAL: sidecar loss does NOT duplicate DECISION in STATE.md",
        ))
        results.append((
            lessons.count("sidecar hash ring is not durable") == 1,
            "DENIAL: sidecar loss does NOT duplicate LESSON in lessons.md",
        ))
        results.append((
            todo.count("promote resolver into invariants doc") == 1,
            "DENIAL: sidecar loss does NOT duplicate TODO in todo.md",
        ))

        # A genuinely NEW tag on a lost-sidecar re-fire still lands, once.
        sidecar.unlink(missing_ok=True)
        msgs.append(_msg("assistant", "DECISION: brand new decision after loss", "u4"))
        _write_transcript(transcript, msgs)
        _run_hook(cwd, transcript)
        state = (cwd / "memory" / "STATE.md").read_text()
        results.append((
            state.count("brand new decision after loss") == 1,
            "ALLOW: new tag still captured exactly once after sidecar loss",
        ))
        results.append((
            state.count("use marker files for hook exclusion") == 1,
            "DENIAL holds across a third fire",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results
```

- [ ] **Step 2: Run it — must FAIL (RED).**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: `test_stop_hook_dedup` module FAILS on the three DENIAL checks (current code duplicates after sidecar loss). All other modules stay green.

- [ ] **Step 3: Implement.** In `session-stop.py`, add after `dedup_against_hashes` (keep the hash ring — it is the cheap first check; the file check is the durable backstop):

```python
def _file_contains_normalized(path: Path, text: str) -> bool:
    """True if the normalized tag body already appears in the target file.

    Backstop for a lost sidecar (fix 4, 2026-07-03): the hash ring lives in
    a GITIGNORED sidecar and resets when it's lost — the target file itself
    is the durable dedup record. Whitespace-collapsed, lowercased substring
    match, mirroring normalized_hash()'s normalization."""
    if not text.strip() or not path.exists():
        return False
    try:
        norm_file = re.sub(r"\s+", " ", path.read_text()).strip().lower()
    except Exception:
        return False  # unreadable target → don't block capture
    norm_text = re.sub(r"\s+", " ", text).strip().lower()
    return norm_text in norm_file
```

In `main()`, immediately AFTER the existing `dedup_against_hashes` block (the five `tags[...] = dedup_against_hashes(...)` lines), add:

```python
    # ── Durable dedup: the target file itself (fix 4) ────────────────────────
    # The hash ring above lives in the gitignored sidecar and resets when the
    # sidecar is lost; the committed target files don't. Filter anything whose
    # normalized body already exists in its destination file.
    state_path = Path(cwd) / "memory" / "STATE.md"
    lessons_path = Path(cwd) / "memory" / "lessons.md"
    todo_path = Path(cwd) / "tasks" / "todo.md"
    tags["decisions"] = [d for d in tags["decisions"] if not _file_contains_normalized(state_path, d)]
    tags["risks"]     = [r for r in tags["risks"] if not _file_contains_normalized(state_path, r)]
    tags["lessons"]   = [l for l in tags["lessons"] if not _file_contains_normalized(lessons_path, l)]
    tags["todos"]     = [t for t in tags["todos"] if not _file_contains_normalized(todo_path, t)]
```

In `append_skill_edge`, guard the append the same way (the skill's `lessons.md` is the durable record for SKILL-EDGE):

```python
        if candidate.exists():
            lessons_path = candidate.parent / "lessons.md"
            if _file_contains_normalized(lessons_path, edge_case):
                return True  # already captured in a prior fire — idempotent
            lessons_path.touch(exist_ok=True)
```

**Coupling (fix 4b) — no ordering change:** appends are now idempotent, so the existing append-then-watermark order is safe: a crash after append but before the sidecar write causes a full re-scan next fire, and the file-content check drops the already-persisted tags. Do NOT move the sidecar write earlier (that would turn the failure mode into silent loss). Add this one-line comment above the `write_sidecar_atomic` call in `main()`:

```python
    # Watermark last, ON PURPOSE: appends are idempotent (file-content dedup),
    # so a crash before this line re-scans next fire without duplicating.
```

Known accepted limitation (document in the helper docstring if desired): a tag whose normalized body coincidentally appears verbatim inside unrelated file prose is skipped. Tag bodies are full sentences; acceptable for memory capture.

- [ ] **Step 4: Run tests — must PASS.**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: `All harness tests passed.` — including all pre-existing idempotency tests (the hash-ring behavior they pin is unchanged).

- [ ] **Step 5: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add plugins/netdust-agent
git commit -m "fix(netdust-agent): dedup survives sidecar loss — target file is the durable dedup record"
```

---

### Task 3: `.no-auto-memory` marker excludes a project from ALL Stop-hook writes (fix 5)

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-stop.py` (anchor: config block for the constant; top of `main()` right after `project = Path(cwd).name` for the check)
- Create: `plugins/netdust-agent/tests/test_no_auto_memory.py`

**Interfaces:**
- Consumes: nothing from Tasks 1–2 beyond the current `main()` shape.
- Produces: constant `NO_AUTO_MEMORY_MARKER = ".no-auto-memory"`; an early `sys.exit(0)` in `main()` that every write path (STATE/lessons/todo/sidecar/`.gitignore`/git commit/dashboard sync) sits downstream of. Task 8 deploys the marker to `/home/ntdst/Sites/netdust-wp-manager/`.

**Test tier:** `Tier A — test contract (guard ⇒ denial path mandatory): with <cwd>/.no-auto-memory present, a transcript full of DECISION/LESSON/TODO tags produces NO memory/ dir, NO tasks/ dir, NO .gitignore edit, NO git commit in the project (denial); with the marker absent, the identical transcript captures normally (allow). RED-first: fails against current HEAD (no exclusion exists).`

- [ ] **Step 1: Write the failing test.** Create `plugins/netdust-agent/tests/test_no_auto_memory.py`:

```python
"""
test_no_auto_memory.py — fix 5 (2026-07-03): a project can opt out of ALL
Stop-hook writes (memory/, tasks/, .gitignore, auto-commit) by placing a
.no-auto-memory marker at its root. Contract driver: the Layer-B fleet dir
(~/Sites/netdust-wp-manager) is manual-only per Stefan's CLAUDE.md — the
hook must never write into or commit it.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-stop.py"


def _msg(role: str, text: str, uuid: str) -> dict:
    return {
        "type": role,
        "uuid": uuid,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _write_transcript(path: Path, messages: list[dict]) -> None:
    with open(path, "w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")


def _run_hook(cwd: Path, transcript: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    return subprocess.run(
        ["python3", str(HOOK)],
        input=payload, capture_output=True, text=True, timeout=10,
        env={**os.environ},
    )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-noautomem-"))
    try:
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "DECISION: this must never be auto-captured here", "u1"),
            _msg("assistant", "LESSON: fleet memory is manual-only", "u2"),
            _msg("assistant", "TODO: should not appear", "u3"),
        ])

        # ── DENIAL: marker present → zero writes, zero commits ──────────────
        excluded = tmp / "fleet"
        excluded.mkdir()
        (excluded / ".no-auto-memory").touch()
        _git(excluded, "init", "-q")
        _git(excluded, "commit", "-q", "--allow-empty", "-m", "baseline")
        before = _git(excluded, "rev-parse", "HEAD").stdout.strip()

        proc = _run_hook(excluded, transcript)
        results.append((proc.returncode == 0, "hook exits 0 on excluded project"))
        results.append((not (excluded / "memory").exists(), "DENIAL: no memory/ created"))
        results.append((not (excluded / "tasks").exists(), "DENIAL: no tasks/ created"))
        results.append((not (excluded / ".gitignore").exists(), "DENIAL: no .gitignore written"))
        after = _git(excluded, "rev-parse", "HEAD").stdout.strip()
        results.append((before == after, "DENIAL: no auto-commit landed"))
        status = _git(excluded, "status", "--porcelain").stdout.strip()
        # Only the marker itself may show as untracked.
        results.append((
            status in ("", "?? .no-auto-memory"),
            f"DENIAL: working tree untouched (status: {status!r})",
        ))

        # ── ALLOW: no marker → normal capture ────────────────────────────────
        normal = tmp / "normal"
        normal.mkdir()
        _run_hook(normal, transcript)
        state = (normal / "memory" / "STATE.md")
        results.append((
            state.exists() and "never be auto-captured here" in state.read_text(),
            "ALLOW: capture proceeds without the marker",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results
```

- [ ] **Step 2: Run it — must FAIL (RED).**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: `test_no_auto_memory` module FAILS its DENIAL checks (memory/ gets created today). Others green.

- [ ] **Step 3: Implement.** In `session-stop.py` config block add:

```python
NO_AUTO_MEMORY_MARKER = ".no-auto-memory"   # at a project root: hook must not write there
```

In `main()`, directly after `project = Path(cwd).name` and BEFORE the transcript checks (nothing may be written past this point — the transcript-skip `log()` calls above write only to ~/.claude/logs, which is fine):

```python
    # ── Exclusion: manual-only projects (fix 5) ──────────────────────────────
    # A .no-auto-memory marker at the project root means this project's memory
    # is maintained by hand (e.g. the Layer-B fleet dir ~/Sites/netdust-wp-manager).
    # ALL write paths — memory/, tasks/, .gitignore, sidecar, git commit,
    # dashboard sync — are downstream of this single check.
    if (Path(cwd) / NO_AUTO_MEMORY_MARKER).exists():
        log(f"skip no-auto-memory cwd={cwd}")
        sys.exit(0)
```

- [ ] **Step 4: Run tests — must PASS.**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: `All harness tests passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add plugins/netdust-agent
git commit -m "fix(netdust-agent): .no-auto-memory marker excludes a project from all Stop-hook writes"
```

### Sibling-site audit — memory-write exclusion (Task 3)

Every write site in the hooks, checked against the single convergence point:

| Write site | Downstream of the marker check? |
|---|---|
| `append_state_from_tags` / `append_lessons_from_tags` / `append_todos_from_tags` / `append_state_marker` / `daily marker` | Yes — all called from `main()` after the check. |
| `write_sidecar_atomic`, `_ensure_sidecar_gitignored` | Yes. |
| `git_commit_memory`, `trigger_dashboard_sync` | Yes. |
| `append_skill_edge` | Writes to PLUGIN dirs, not the project — intentionally NOT excluded (skill lessons are harness-owned, not Layer B). |
| `session-start.sh` | READS only — reading Layer B memory is allowed by the contract; no change. |
| `subagent-stop.py` | Verified: writes only `~/.claude/logs/…` — no project writes, no exclusion needed. |
| `pretooluse-guard.py` | No project writes. |

`── REVIEW GATE ── (tier: STANDARD — multi-task behavior change in the Stop hook's capture logic; no 1a surface: the cluster deletes the only outbound call and credential read. Reviewer holds Tasks 1–3 + the sibling-site audit above. Integration gate: `bash plugins/netdust-agent/tests/run.sh` fully green from a clean checkout of the branch.)`

---

## CLUSTER 2 — version resolution + GLOBAL.md ownership (Tasks 4–7)

### Task 4: `session-stop.py` resolves active plugin dirs from `installed_plugins.json` (fix 3, site 1)

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-stop.py` (anchor: `_netdust_plugin_dirs()` and just above it)
- Create: `plugins/netdust-agent/tests/test_plugin_version_resolution.py` (this task adds the Python-side tests; Task 5 appends the bash-side tests to the same module)

**Interfaces:**
- Produces: `INSTALLED_PLUGINS_JSON: Path` (module constant, `Path.home()/".claude"/"plugins"/"installed_plugins.json"`), `_installed_plugin_paths() -> dict[str, Path]`, and a rewritten `_netdust_plugin_dirs()` whose order is: registry → CLAUDE_PLUGIN_ROOT-climb mtime fallback → legacy glob. Task 5's bash reads the same registry with the same `<name>@<marketplace>` key semantics.

**Test tier:** `Tier A — test contract: given a fake $HOME whose installed_plugins.json installPath names version A while sibling version B has a NEWER mtime, a SKILL-EDGE capture routes to version A's skills/<skill>/lessons.md and NOT version B's (denial of the mtime heuristic); with installed_plugins.json absent, the mtime fallback still resolves (allow/fallback path). RED-first: fails against current HEAD (mtime wins today).`

- [ ] **Step 1: Write the failing test.** Create `plugins/netdust-agent/tests/test_plugin_version_resolution.py`:

```python
"""
test_plugin_version_resolution.py — fix 3 (2026-07-03): "active plugin
version" must come from Claude Code's own registry
(~/.claude/plugins/installed_plugins.json, v2 schema:
plugins.<name>@<marketplace> = [{installPath, ...}]), NOT from version-dir
mtimes. Real incident: netdust-agent 0.2.1's mtime was 4 ms newer than the
actually-installed 0.3.0, so SKILL-EDGE lessons routed to the stale dir and
the ~/.claude/plugins/<plugin> symlinks pointed at 0.2.1.

Covers both resolvers: session-stop.py (_netdust_plugin_dirs, this file's
Python tests) and session-start.sh (symlink refresh, bash tests — Task 5).
"""

import json
import os
import subprocess
import shutil
import tempfile
import time
from pathlib import Path

HOOKS = Path(__file__).parent.parent / "hooks"
HOOK_STOP = HOOKS / "session-stop.py"
HOOK_START = HOOKS / "session-start.sh"


def _fake_home(tmp: Path) -> tuple[Path, Path, Path]:
    """Build a fake $HOME with two cache versions of netdust-agent where the
    WRONG one (stale) has the newer mtime, plus a registry naming the right one.
    Returns (home, active_dir, stale_dir)."""
    home = tmp / "home"
    cache = home / ".claude" / "plugins" / "cache" / "netdust-plugins" / "netdust-agent"
    active = cache / "9.9.9"
    stale = cache / "9.9.8"
    for d in (active, stale):
        (d / "skills" / "probe-skill").mkdir(parents=True)
        (d / "skills" / "probe-skill" / "SKILL.md").write_text("# probe\n")
    # mtime trap: stale NEWER than active.
    now = time.time()
    os.utime(active, (now - 60, now - 60))
    os.utime(stale, (now, now))
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    registry.write_text(json.dumps({
        "version": 2,
        "plugins": {
            "netdust-agent@netdust-plugins": [
                {"scope": "user", "installPath": str(active), "version": "9.9.9"}
            ]
        },
    }))
    return home, active, stale


def _run_stop_hook(cwd: Path, transcript: Path, home: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    env = {**os.environ, "HOME": str(home)}
    env.pop("CLAUDE_PLUGIN_ROOT", None)  # force registry path, no climb hint
    return subprocess.run(
        ["python3", str(HOOK_STOP)],
        input=payload, capture_output=True, text=True, timeout=10, env=env,
    )


def _msg(text: str, uuid: str) -> dict:
    return {"type": "assistant", "uuid": uuid,
            "message": {"content": [{"type": "text", "text": text}]}}


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-verres-"))
    try:
        home, active, stale = _fake_home(tmp)
        cwd = tmp / "project"
        cwd.mkdir()
        transcript = tmp / "t.jsonl"
        with open(transcript, "w") as f:
            f.write(json.dumps(_msg(
                "SKILL-EDGE: probe-skill: registry beats mtime", "u1")) + "\n")

        _run_stop_hook(cwd, transcript, home)
        active_lessons = active / "skills" / "probe-skill" / "lessons.md"
        stale_lessons = stale / "skills" / "probe-skill" / "lessons.md"
        results.append((
            active_lessons.exists() and "registry beats mtime" in active_lessons.read_text(),
            "SKILL-EDGE routes to installPath version (registry wins)",
        ))
        results.append((
            not stale_lessons.exists(),
            "DENIAL: newer-mtime stale version receives nothing",
        ))

        # Fallback: registry absent → mtime heuristic still resolves (via
        # CLAUDE_PLUGIN_ROOT climb), so the hook keeps working outside CC.
        home2, active2, stale2 = _fake_home(tmp / "second")
        (home2 / ".claude" / "plugins" / "installed_plugins.json").unlink()
        cwd2 = tmp / "project2"
        cwd2.mkdir()
        payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd2)})
        env = {**os.environ, "HOME": str(home2),
               "CLAUDE_PLUGIN_ROOT": str(stale2)}
        subprocess.run(["python3", str(HOOK_STOP)], input=payload,
                       capture_output=True, text=True, timeout=10, env=env)
        results.append((
            (stale2 / "skills" / "probe-skill" / "lessons.md").exists(),
            "FALLBACK: no registry → mtime climb still routes (stale2 is newest)",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results
```

- [ ] **Step 2: Run it — must FAIL (RED).**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: first two checks FAIL (current code routes to the newer-mtime `9.9.8`). Fallback check may already pass. Others green.

- [ ] **Step 3: Implement.** In `session-stop.py`, above `_netdust_plugin_dirs`:

```python
INSTALLED_PLUGINS_JSON = Path.home() / ".claude" / "plugins" / "installed_plugins.json"


def _installed_plugin_paths() -> dict[str, Path]:
    """plugin name -> active install dir, from Claude Code's own registry.

    v2 schema: {"plugins": {"<name>@<marketplace>": [{"installPath": ...}]}}.
    The registry is the ONLY truth for "active version" — version-dir mtimes
    are not (fix 3, 2026-07-03: 0.2.1's mtime was 4 ms newer than the
    installed 0.3.0). Returns {} on any error so callers can fall back."""
    try:
        data = json.loads(INSTALLED_PLUGINS_JSON.read_text())
        result: dict[str, Path] = {}
        for key, entries in data.get("plugins", {}).items():
            name = key.split("@", 1)[0]
            if not isinstance(entries, list) or not entries:
                continue
            install_path = entries[0].get("installPath")
            if install_path and Path(install_path).is_dir():
                result[name] = Path(install_path)
        return result
    except Exception:
        return {}
```

Rewrite `_netdust_plugin_dirs()` — registry first, existing behavior demoted to labeled fallbacks (keep the existing docstring's layout notes, add the ordering):

```python
def _netdust_plugin_dirs() -> list[Path]:
    """Locate all installed netdust-* plugin dirs, in trust order:

    1. installed_plugins.json installPath (authoritative — see
       _installed_plugin_paths).
    2. FALLBACK (registry missing/unreadable — e.g. bare test runs): climb
       from CLAUDE_PLUGIN_ROOT to the marketplace dir and pick each sibling's
       newest-mtime version dir. mtime is a heuristic, NOT truth.
    3. Legacy flat layout glob (~/.claude/plugins/netdust-*).
    """
    installed = _installed_plugin_paths()
    dirs = [p for name, p in installed.items() if name.startswith("netdust-")]
    if dirs:
        return dirs

    root_env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root_env:
        marketplace_dir = Path(root_env).parent.parent
        result = []
        for sibling in marketplace_dir.iterdir():
            if not sibling.is_dir() or not sibling.name.startswith("netdust-"):
                continue
            versions = [v for v in sibling.iterdir() if v.is_dir()]
            if not versions:
                continue
            latest = max(versions, key=lambda p: p.stat().st_mtime)
            result.append(latest)
        return result

    plugins_root = Path.home() / ".claude" / "plugins"
    if not plugins_root.exists():
        return []
    return [p for p in plugins_root.glob("netdust-*") if p.is_dir()]
```

- [ ] **Step 4: Run tests — must PASS.**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: `All harness tests passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add plugins/netdust-agent
git commit -m "fix(netdust-agent): resolve active plugin dirs from installed_plugins.json, not version-dir mtime (Stop hook)"
```

---

### Task 5: `session-start.sh` symlink refresh reads `installPath` (fix 3, site 2)

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-start.sh:115-133` (the "Stable plugin path symlinks" block)
- Modify: `plugins/netdust-agent/tests/test_plugin_version_resolution.py` (append bash-side checks to `run()`)

**Interfaces:**
- Consumes: the same registry semantics as Task 4 (`<name>@<marketplace>` key, `entries[0].installPath`) — keep the two implementations semantically identical.
- Produces: `~/.claude/plugins/<plugin>` symlinks that track `installPath`; mtime pick survives only as the no-registry fallback.

**Test tier:** `Tier A — test contract: with a fake $HOME (registry names version A, version B has newer mtime), running session-start.sh leaves the netdust-agent symlink pointing at A (denial of mtime); with the registry file removed, the symlink falls back to the newest-mtime dir (fallback path). RED-first: fails against current HEAD.`

- [ ] **Step 1: Extend the test.** In `test_plugin_version_resolution.py`, add inside `run()` (before the `finally`), reusing `_fake_home`:

```python
        # ── bash side: session-start.sh symlink refresh (Task 5) ────────────
        home3, active3, stale3 = _fake_home(tmp / "third")
        proj3 = tmp / "project3"
        proj3.mkdir()
        env3 = {**os.environ, "HOME": str(home3),
                "CLAUDE_PLUGIN_ROOT": str(active3)}
        subprocess.run(["bash", str(HOOK_START)], cwd=proj3,
                       capture_output=True, text=True, timeout=15, env=env3)
        link = home3 / ".claude" / "plugins" / "netdust-agent"
        results.append((
            link.is_symlink() and os.readlink(link) == str(active3),
            "symlink targets installPath, not newest-mtime dir",
        ))

        # Fallback: registry removed → mtime pick (stale3 is newest).
        (home3 / ".claude" / "plugins" / "installed_plugins.json").unlink()
        subprocess.run(["bash", str(HOOK_START)], cwd=proj3,
                       capture_output=True, text=True, timeout=15, env=env3)
        results.append((
            link.is_symlink() and os.readlink(link) == str(stale3),
            "FALLBACK: no registry → symlink uses newest-mtime dir",
        ))
```

- [ ] **Step 2: Run it — must FAIL (RED).**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: "symlink targets installPath" FAILS (current script picks `9.9.8` by mtime). Fallback check passes.

- [ ] **Step 3: Implement.** Replace `session-start.sh` L123–133 with (one python3 call for all plugins — python3 is already a hard dependency of the plugin's other hooks; do NOT depend on jq):

```bash
PLUGIN_CACHE="$HOME/.claude/plugins/cache/netdust-plugins"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"
if [[ -d "$PLUGIN_CACHE" ]]; then
  # Authoritative map: plugin<TAB>installPath from Claude Code's own registry
  # (fix 3, 2026-07-03 — version-dir mtimes lie; 0.2.1 was 4 ms "newer" than
  # the installed 0.3.0). Empty on any error → per-plugin mtime fallback below.
  ACTIVE_MAP=""
  if [[ -f "$INSTALLED_JSON" ]]; then
    ACTIVE_MAP=$(python3 - "$INSTALLED_JSON" <<'PY' 2>/dev/null || true
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for key, entries in data.get("plugins", {}).items():
    name = key.split("@", 1)[0]
    if name.startswith("netdust-") and isinstance(entries, list) and entries:
        p = entries[0].get("installPath")
        if p:
            print(f"{name}\t{p}")
PY
)
  fi
  for plugin in netdust-agent netdust-core netdust-wp netdust-statamic; do
    plugin_dir="$PLUGIN_CACHE/$plugin"
    [[ -d "$plugin_dir" ]] || continue
    active=$(printf '%s\n' "$ACTIVE_MAP" | awk -F'\t' -v p="$plugin" '$1 == p { print $2; exit }')
    if [[ -n "$active" && -d "$active" ]]; then
      ln -sfn "$active" "$HOME/.claude/plugins/$plugin"
    else
      # Fallback: newest-mtime version dir (registry missing this plugin).
      latest_version=$(ls -1t "$plugin_dir" 2>/dev/null | head -1)
      [[ -n "$latest_version" ]] || continue
      ln -sfn "$plugin_dir/$latest_version" "$HOME/.claude/plugins/$plugin"
    fi
  done
fi
```

Note `set -u` is active: `ACTIVE_MAP` is always initialized; the heredoc python exits 0 on error; `|| true` guards the substitution.

- [ ] **Step 4: Run tests — must PASS.**

Run: `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh`
Expected: `All harness tests passed.` — including the pre-existing `test_session_start_budget.py`.

- [ ] **Step 5: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add plugins/netdust-agent
git commit -m "fix(netdust-agent): session-start symlinks track installed_plugins.json installPath, not mtime"
```

---

### Task 6: `scripts/sync.sh` targets the installed version dir via `installPath` (fix 3, site 3 — delivery path)

**Files:**
- Modify: `scripts/sync.sh` (both `version="$(ls -1t ...)"` sites: the sync loop and the verify loop)

**Interfaces:**
- Consumes: same registry semantics as Tasks 4–5.
- Produces: a `resolve_installed_dir <plugin_name>` shell function used by both loops. Task 8 relies on this so the fast-path sync hits the ACTUALLY installed cache dir.

**Test tier:** `no unit test: Tier B — dev-tooling script whose main effects (claude plugin marketplace update, rsync into the live cache) are not reproducible in the harness sandbox; evidence = the Step 2 dry verification showing the resolved dir equals installed_plugins.json's installPath for every installed plugin.`

**Scope note:** this file was NOT in the audit's 5-fix list, but it is the SAME defect (mtime-as-active-version) and sits on this phase's delivery path: unfixed, `sync.sh` would rsync these very fixes into the stale `netdust-agent/0.2.1` dir and verification would pass against the wrong tree. Included under fix 3 as its third occurrence; flagged for the user in the plan summary.

- [ ] **Step 1: Implement.** In `scripts/sync.sh`, after the `CACHE_ROOT=` line, add:

```bash
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"

# resolve_installed_dir <plugin_name>
# Echoes the plugin's ACTIVE cache dir. Truth = installed_plugins.json's
# installPath (fix 3, 2026-07-03 — `ls -1t` picked netdust-agent 0.2.1 over
# the installed 0.3.0 on a 4 ms mtime difference). Falls back to newest-mtime
# when the registry misses the plugin. Echoes nothing if unresolvable.
resolve_installed_dir() {
  local plugin_name="$1" active=""
  if [[ -f "$INSTALLED_JSON" ]]; then
    active=$(python3 - "$plugin_name" "$INSTALLED_JSON" <<'PY' 2>/dev/null || true
import json, sys
name, path = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path))
except Exception:
    sys.exit(0)
for key, entries in data.get("plugins", {}).items():
    if key.split("@", 1)[0] == name and isinstance(entries, list) and entries:
        p = entries[0].get("installPath")
        if p:
            print(p)
        break
PY
)
  fi
  if [[ -n "$active" && -d "$active" ]]; then
    printf '%s\n' "$active"
    return 0
  fi
  local latest
  latest="$(ls -1t "$CACHE_ROOT/$plugin_name" 2>/dev/null | head -1)"
  [[ -n "$latest" ]] && printf '%s\n' "$CACHE_ROOT/$plugin_name/$latest"
}
```

In the **sync loop**, replace:
```bash
  version="$(ls -1t "$CACHE_ROOT/$plugin_name" | head -1)"
  if [[ -z "$version" ]]; then
    echo "  - $plugin_name: SKIP (no version dir found)"
    continue
  fi
  target="$CACHE_ROOT/$plugin_name/$version"
```
with:
```bash
  target="$(resolve_installed_dir "$plugin_name")"
  if [[ -z "$target" ]]; then
    echo "  - $plugin_name: SKIP (no installed version dir resolved)"
    continue
  fi
  version="$(basename "$target")"
```

In the **verify loop**, replace the `version="$(ls -1t ...)"` + `target=` pair the same way:
```bash
  target="$(resolve_installed_dir "$plugin_name")"
  [[ -n "$target" ]] || continue
```
(drop the now-unused `version=` line there).

Mind `set -euo pipefail` at the top of this script: `resolve_installed_dir` must not `exit` non-zero on the empty case — the `[[ -n ... ]] && printf` last line returns the test's status; end the function with `return 0` after the fallback printf block if needed:

```bash
  local latest
  latest="$(ls -1t "$CACHE_ROOT/$plugin_name" 2>/dev/null | head -1)"
  if [[ -n "$latest" ]]; then
    printf '%s\n' "$CACHE_ROOT/$plugin_name/$latest"
  fi
  return 0
```

- [ ] **Step 2: Dry verification (no sync run).**

Run:
```bash
cd /home/ntdst/Projects/netdust-plugins
bash -c 'source /dev/stdin <<EOF
$(sed -n "/^INSTALLED_JSON=/,/^}/p" scripts/sync.sh)
EOF
CACHE_ROOT="$HOME/.claude/plugins/cache/netdust-plugins"
for p in netdust-agent netdust-core netdust-wp netdust-statamic; do
  echo "$p -> $(resolve_installed_dir $p)"
done'
```
Expected: `netdust-agent -> .../netdust-agent/0.3.0` (NOT 0.2.1), `netdust-wp -> .../0.4.0` (NOT 0.4.1), core `0.2.1`, statamic `0.1.1` — each matching `installed_plugins.json`. Also `bash -n scripts/sync.sh` → no syntax errors.

- [ ] **Step 3: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add scripts/sync.sh
git commit -m "fix(scripts): sync.sh targets the installed cache dir from installed_plugins.json, not newest mtime"
```

### Sibling-site audit — mtime-as-active-version (Tasks 4–6)

All occurrences of the defect, accounted for:

| Site | Disposition |
|---|---|
| `session-stop.py` `_netdust_plugin_dirs()` (mtime max, L511) | Fixed Task 4; mtime survives only as labeled fallback #2. |
| `session-start.sh` L129 `ls -1t \| head -1` | Fixed Task 5; mtime survives only as no-registry fallback. |
| `scripts/sync.sh` sync loop + verify loop (2 sites) | Fixed Task 6; same fallback shape. |
| `subagent-stop.py`, `pretooluse-guard.py` | Verified clean — no version resolution. |

Grep gate at cluster close: `grep -rn "ls -1t\|st_mtime" plugins/netdust-agent/hooks scripts/` → every remaining hit sits inside a block whose comment names it a FALLBACK to the registry.

---

### Task 7: Move GLOBAL.md into netdust-agent (fix 2)

**Files:**
- Move: `plugins/netdust-core/memory/GLOBAL.md` → `plugins/netdust-agent/memory/GLOBAL.md` (via `git mv`; `plugins/netdust-core/memory/deploy-patterns.md` stays put — out of scope)
- Modify: `plugins/netdust-agent/memory/GLOBAL.md` (2-line header touch-up)
- Modify: `plugins/netdust-core/README.md` (L18, L118), `plugins/netdust-core/RULES.md` (L24), `plugins/netdust-core/CLAUDE.md` (L37) — repoint dangling references

**Interfaces:**
- Consumes: nothing — `session-start.sh` L136 (`HARNESS_GLOBAL="${CLAUDE_PLUGIN_ROOT}/memory/GLOBAL.md"`) is already correct once the file exists in the agent plugin; ZERO hook-code change in this task.
- Produces: `plugins/netdust-agent/memory/GLOBAL.md` shipped with every future agent version. netdust-core's dead `hooks/session-start.sh` (same L136) is left untouched — its `hooks.json` is `{"hooks": {}}` and resurrecting/cleaning core's hooks is out of scope.

**Test tier:** `no unit test: Tier B — file move + doc-reference repoint; the injection code path is already covered by the existing session-start tests, and adding a test that a cat'd file gets cat'd re-tests the shell. Evidence = the Step 2 manual fire showing "## Netdust harness — GLOBAL" in output and found=[…harness_global…] in the log, plus the live check in Task 8.`

- [ ] **Step 1: Move the file and touch up its header.**

```bash
cd /home/ntdst/Projects/netdust-plugins
mkdir -p plugins/netdust-agent/memory
git mv plugins/netdust-core/memory/GLOBAL.md plugins/netdust-agent/memory/GLOBAL.md
```

In the moved file, update the two header lines (L1–3): keep the title; change `Harness-level facts. Loaded into every WP session by `session-start.sh`.` to `Harness-level facts. Shipped with the netdust-agent plugin; injected into every session by its \`hooks/session-start.sh\` (moved here from netdust-core 2026-07-03 — agent owns the live memory hooks).` Do NOT edit any other content (the "Active priorities" mutable-content question is an explicit deferral, see Decision record).

- [ ] **Step 2: Manual fire — the injection works from the repo tree.**

Run:
```bash
cd "$(mktemp -d)" && CLAUDE_PLUGIN_ROOT=/home/ntdst/Projects/netdust-plugins/plugins/netdust-agent \
  bash /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/hooks/session-start.sh | head -20
tail -1 ~/.claude/logs/memory-hook.log
```
Expected: output contains `## Netdust harness — GLOBAL` followed by the file's content; the log line's `found=[...]` list includes `harness_global` (today it lands in `missing=[...]`).

- [ ] **Step 3: Repoint netdust-core's dangling references.**
  - `plugins/netdust-core/README.md` L18 (`| **Memory (harness-level)** | ...`): change to note `GLOBAL.md` now ships in **netdust-agent** (`plugins/netdust-agent/memory/GLOBAL.md`); `deploy-patterns.md` stays here.
  - `plugins/netdust-core/README.md` L118: change "The SessionStart hook injects all of these + `memory/GLOBAL.md` (harness-level)" to name netdust-agent's hook as the live injector and the file's new home.
  - `plugins/netdust-core/RULES.md` L24: `See memory/GLOBAL.md` → `See netdust-agent's memory/GLOBAL.md`.
  - `plugins/netdust-core/CLAUDE.md` L37: same repoint — the harness-level `GLOBAL.md` lives in netdust-agent, whose SessionStart hook is the live one.
  Verify no dangling repo references remain: `grep -rn "memory/GLOBAL" /home/ntdst/Projects/netdust-plugins/plugins --include="*.md" | grep -v netdust-agent/memory` — remaining hits must be either historical spec docs (`netdust-wp/docs/.../2026-05-17-harness-design.md` — leave) or the repointed lines themselves.

- [ ] **Step 4: Run the full suite (guard against accidental script edits).**

Run: `bash /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests/run.sh`
Expected: `All harness tests passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/ntdst/Projects/netdust-plugins
git add plugins/netdust-agent plugins/netdust-core
git commit -m "fix(netdust-agent): GLOBAL.md ships with the agent plugin — its hook is the live injector (moved from netdust-core)"
```

`── REVIEW GATE ── (tier: STANDARD — multi-file behavior change across two resolvers, a dev script, and a cross-plugin file move; no 1a surface: installed_plugins.json is Claude Code's own local registry, parsed defensively. Reviewer holds Tasks 4–7 + the mtime sibling-site audit, and specifically checks that the Python and bash registry parsers keep IDENTICAL key semantics (<name>@<marketplace>, entries[0].installPath). Integration gate: full `tests/run.sh` green + Task 6 Step 2 dry verification output pasted into the review.)`

---

## CLUSTER 3 — delivery + live verification (Task 8)

### Task 8: Ship repo → installed cache, deploy the marker, prove the fixes are live

**Files:**
- Modify: `.claude-plugin/marketplace.json` (netdust-agent `0.3.0` → `0.3.1`; netdust-core `0.2.1` → `0.2.2` — its content changed: GLOBAL.md moved out)
- Modify: `plugins/netdust-agent/.claude-plugin/plugin.json` and `plugins/netdust-core/.claude-plugin/plugin.json` IF they carry their own `version` field (check first: `grep -l '"version"' plugins/*/.claude-plugin/plugin.json 2>/dev/null`); keep in lockstep with marketplace.json
- Create (outside the repo): `/home/ntdst/Sites/netdust-wp-manager/.no-auto-memory`

**Interfaces:**
- Consumes: everything above merged to the branch; Task 6's fixed `sync.sh` for the fast path.

**Test tier:** `no unit test: Tier B — release/config mechanics; evidence = the live verification checklist below, each command with its expected output observed.`

**How changes get from repo → installed cache (write this down; it is the phase's delivery contract):**
1. **Canonical:** bump versions in `.claude-plugin/marketplace.json` (+ per-plugin `plugin.json` if versioned) → merge branch to `main` → `git push` → `claude plugin marketplace update netdust-plugins` → `claude plugin update netdust-agent@netdust-plugins` and `claude plugin update netdust-core@netdust-plugins`. The update creates NEW version dirs (`netdust-agent/0.3.1`, `netdust-core/0.2.2`) and rewrites `installed_plugins.json`'s `installPath` — which the fixed resolvers now follow.
2. **Dev fast path:** `./scripts/sync.sh` after a push — post-Task-6 it rsyncs the working tree into the dir `installed_plugins.json` names (previously it could hit a stale sibling). Version stays the same; use only for iteration, not for closing this phase.

- [ ] **Step 1: Merge + bump + push.** Merge `fix/phase1-memory-hooks` into `main` (per repo convention — see prior bump commit `26d9a65` for the manifest-bump message shape), set netdust-agent `0.3.1` and netdust-core `0.2.2` in `marketplace.json` (and plugin.json files if versioned), commit `chore: bump netdust-agent 0.3.1 + netdust-core 0.2.2 (phase-1 memory-hook fixes)`, `git push`.

- [ ] **Step 2: Update the installed plugins.**

```bash
claude plugin marketplace update netdust-plugins
claude plugin update netdust-agent@netdust-plugins
claude plugin update netdust-core@netdust-plugins
```

- [ ] **Step 3: Drop the Layer-B marker.**

```bash
touch /home/ntdst/Sites/netdust-wp-manager/.no-auto-memory
```
(Do not commit anything inside `netdust-wp-manager` for this — the marker is untracked machine state, exactly like the sidecar. If Stefan prefers it committed to the fleet repo, that is his manual Layer-B call.)

- [ ] **Step 4: Live verification checklist** (fresh Claude Code session for the hook-fire items):

```bash
# 1. Registry took the new versions:
python3 -c "import json;d=json.load(open('$HOME/.claude/plugins/installed_plugins.json'));print({k.split('@')[0]:v[0]['version'] for k,v in d['plugins'].items() if k.startswith('netdust')})"
# expect: netdust-agent 0.3.1, netdust-core 0.2.2

# 2. Installed hook == repo hook (the fix is LIVE, not just committed):
diff <(python3 -c "import json;d=json.load(open('$HOME/.claude/plugins/installed_plugins.json'));print(d['plugins']['netdust-agent@netdust-plugins'][0]['installPath'])" | xargs -I{} cat {}/hooks/session-stop.py) \
     /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/hooks/session-stop.py && echo HOOK-LIVE

# 3. Start a fresh session in any project, then:
tail -3 ~/.claude/logs/memory-hook.log
# expect: session-start line with found=[...harness_global...]
for p in netdust-agent netdust-core netdust-wp netdust-statamic; do echo "$p -> $(readlink ~/.claude/plugins/$p)"; done
# expect: every target == that plugin's installPath (agent → .../0.3.1, wp → .../0.4.0)

# 4. End a session in a scratch project after writing "DECISION: phase-1 live check"; then:
tail -1 ~/.claude/logs/memory-hook.log
# expect: done line with wrote=[STATE.md(tags)] and NO haiku= field

# 5. End a session in /home/ntdst/Sites/netdust-wp-manager; then:
tail -1 ~/.claude/logs/memory-hook.log
# expect: "skip no-auto-memory cwd=/home/ntdst/Sites/netdust-wp-manager"
cd /home/ntdst/Sites/netdust-wp-manager && git log --oneline -1 -- memory/ && git status --porcelain memory/ tasks/
# expect: no new auto-capture commit; no staged/dirty memory writes from the hook
```

- [ ] **Step 5: Record completion.** Note in the plan's review section which checklist items passed; any failure loops back to its owning task (do not patch the cache by hand).

`── REVIEW GATE ── (tier: LIGHT — release mechanics, version bumps, and a checklist; no code. Single generalist pass over the bump diff + the pasted verification outputs.)`

---

## Self-review (done at authoring)

- **Spec coverage:** fix 1 → Task 1; fix 2 → Task 7; fix 3 → Tasks 4/5/6 (three sites; site 3 is a flagged same-defect addition); fix 4a+4b → Task 2; fix 5 → Task 3 + marker deployment in Task 8. Delivery + live-proof requirement → Task 8. ✓
- **Deferrals (explicitly NOT in this phase):** block-once tag nudge (user decision); GLOBAL.md "Active priorities" migration to Layer B; netdust-core dead-hook cleanup + its Track B doc drift; repo-level ARCHITECTURE-INVARIANTS.md authoring.
- **Type/name consistency:** `_file_contains_normalized`, `NO_AUTO_MEMORY_MARKER`, `_installed_plugin_paths`, `INSTALLED_PLUGINS_JSON`, `resolve_installed_dir` — each defined once, referenced with the same name everywhere. Registry key semantics (`<name>@<marketplace>`, `entries[0].installPath`) identical across all three implementations. ✓
- **Placeholder scan:** every code step carries the actual code; every run step carries the command + expected output. ✓

---

## Review section (execution record, 2026-07-03)

- Cluster 1 (Tasks 1–3): closed. STANDARD review ×3 angles → 1 Important (stale API-key env in test_tag_scanner) + minors, fixed in 9d86269, re-review APPROVED.
- Cluster 2 (Tasks 4–7): closed. STANDARD review ×3 angles → 4 Important (heredoc try-scope parity, dead-core false-signal test, hardcoded plugin-list asymmetry, entries[0] rule untested), fixed in 3c32400 + dafb93b, both re-reviews APPROVED. Parser-parity check: PASS.
- Task 8: delivered. Fast-forward merge, bump 742d0bf (agent 0.3.1, core 0.2.2), pushed to origin/main, plugins updated. Live verification checklist: 5/5 PASS (registry versions; HOOK-LIVE diff; harness_global found + 4 symlinks on installPath; tag capture without haiku=; no-auto-memory skip in netdust-wp-manager).
- Deferrals carried forward: netdust-core dead-hook cleanup + Track-B doc drift (core CLAUDE.md); netdust-wp marketplace 0.4.1 vs installed 0.4.0 mismatch; pattern-miner.md dangling GLOBAL.md ref; sync.sh test coverage; cross-marketplace netdust-* symlink edge; GLOBAL.md "Active priorities" content migration to Layer B; block-once tag nudge (user-deferred).
