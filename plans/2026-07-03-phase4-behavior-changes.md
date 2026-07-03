# Phase 4 — Memory-System Behavior Changes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Dispatch ONE implementer per task, sequentially — no parallel implementers (Task 8 writes 7 files but is deliberately ONE task for exactly this reason).

**Goal:** Change memory-system *behavior* per Stefan's locked 2026-07-03 decisions: drop the daily STATE.md marker entirely, teach `SKILL-EDGE:` + add a deterministic periodic `/skill-audit` nudge, resolve the `/memory-audit` dual-ownership drift, dedup the stop-hook test helpers, and auto-draft the missing fleet `STATE.md` files (uncommitted, DRAFT-headed) with the stride naming drift merged.

**Architecture:** Two repo clusters (netdust-agent hook behavior; command/doc reconciliation) + one machine-state cluster (fleet drafts in `~/Sites/netdust-wp-manager/memory/` — NOT this repo). Repo work lands on one branch, ships as netdust-agent 0.3.3 + netdust-core 0.2.4 via the phase-1 delivery contract (marketplace bump → push → `claude plugin update`). Fleet drafts never touch git.

**Tech Stack:** Python 3 (Stop hook + bespoke `tests/run.sh` runner), Bash (SessionStart hook), Claude Code command prompt files (`.md`), plugin marketplace manifests.

**Work class:** A (multi-task behavior change). Stage 0 skipped — the decision record is user-locked; nothing is open to design. `doubting-decisions` not fired: the load-bearing choices are Stefan's (do not re-litigate); the planner's discretionary deltas (stamp mechanism, canonical stride name, draft format) are single-file, reversible, and stated as Decisions below for override at review.

## Global Constraints

- **Decision record is locked.** The four decisions in the dispatch (marker DROP, nudge+sweep, auto-draft-uncommitted fleet view, Item-3 + helper-dedup scope) are user-approved 2026-07-03. Do not re-open them at any gate.
- **Hook safety contract:** `session-stop.py` must always `sys.exit(0)`, never block, complete < 3s. Every fire logs to `~/.claude/logs/memory-hook.log` — that log is now the ONLY liveness signal (the marker is gone).
- **Single memory-write exclusion (architecture invariant, phase 1):** the `.no-auto-memory` check at the top of `main()` (session-stop.py ~L537) is the single convergence point ALL hook write paths sit downstream of. No task may introduce a write path above it. `tests/test_no_auto_memory.py` is the standing denial test and must stay green untouched.
- **Session-start injection budgets:** STATE.md 32KB / lessons.md 16KB / MEMORY.md 24KB (pinned by `test_session_start_budget.py`). New injected lines in the memory-discipline block are ≤ ~400 bytes total.
- **Test runner contract:** `tests/run.sh` executes every file matching `test_*.py` via importlib with cwd = `tests/`. The shared helper module MUST NOT match that glob (name: `hook_test_utils.py`). Suite must be green after every task, same-or-higher pass count except where a test is deliberately deleted (Task 1: −1 test, +2 tests).
- **Version lockstep:** `.claude-plugin/marketplace.json` and each plugin's `.claude-plugin/plugin.json` carry the same version. This phase: netdust-agent `0.3.2 → 0.3.3`, netdust-core `0.2.3 → 0.2.4`.
- **Fleet drafts are machine state:** written under `~/Sites/netdust-wp-manager/memory/projects/`, left UNCOMMITTED with a DRAFT header. Never `git add`/`git commit` in netdust-wp-manager (Layer-B commits are Stefan's ritual). The `.no-auto-memory` marker there stays.
- **Branch:** `feat/phase4-memory-behavior` off `main` in `/home/ntdst/Projects/netdust-plugins`.

---

## Gate decisions (planner, explicit)

### 1a — Threat model: DOES NOT FIRE
Trigger list walked literally: user-controlled URLs — no. Auth/session/token surfaces — no. Untrusted parsing — the Stop hook parses session transcripts, but those are local files written by Claude Code itself on this machine (existing, self-produced surface; this phase REMOVES a write path from it, net surface reduction, no new parse). BYOK credentials — no. Multi-tenancy boundaries — no. Outbound requests to user-supplied addresses — no. No `## Threat model` section is embedded because no trigger matches, not because the work "feels safe."

### 1b — Architecture invariants: FIRES (cited inline; no doc exists yet)
The repo has no `ARCHITECTURE-INVARIANTS.md` (verified 2026-07-03). The phase-1 convergence point is cited here as the plan's invariant contract:

> **INV-1 (single memory-write exclusion):** every filesystem/git side-effect of `session-stop.py` — STATE.md, lessons.md, todo.md, skill lessons, `.gitignore`, sidecar, git commit, dashboard sync — executes strictly downstream of the one `.no-auto-memory` check in `main()`.

Task 1 (marker drop) *interacts* with INV-1 by deleting one downstream write path (`append_state_marker`). That strengthens the invariant (fewer writers); the constraint on the implementer is: touch nothing above the check, and leave `test_no_auto_memory.py` untouched-and-green as proof. Task 8's fleet-draft writes are the *manual layer* acting on `netdust-wp-manager` — INV-1 governs hook-side writes only; the marker file continues to exclude the hook there. **Deferral (carried from phase 1):** authoring the full repo `ARCHITECTURE-INVARIANTS.md` stays out of scope — too much ceremony for a two-hook repo mid-phase; record INV-1 in it whenever that deferral is picked up.

### 1g — Feature acceptance: N/A
No user-facing feature surface — hook internals, injected prompt text, command prompt files, and content drafts. No client/agent-driven endpoint. No acceptance-flows matrix. (Live delivery verification in Task 9 covers the "does the new behavior actually fire" question.)

### 1c — Premise ground-truthing: DONE (drift found — see final section)

---

## Decisions made by this plan (planner's discretion, reviewable)

1. **Periodic /skill-audit sweep mechanism = stamp file + conditional session-start nudge.** `/skill-audit` has no run artifact today, so "periodic" is undecidable without one. The command writes `~/.claude/logs/skill-audit-last-run` on completion; `session-start.sh` injects a ONE-line nudge inside the memory-discipline block when that stamp is missing or > 30 days old. Chosen over (a) documenting a cadence in GLOBAL.md — doesn't fire; (b) nothing automated — `compounding` Pass B already sweeps *spec-touched* skills at spec-close, but sessions that never reach spec-close were exactly the gap Stefan's decision names. This is the lightest thing that deterministically fires. Known trade-off: it nudges every session until the audit runs — accepted; it's one line and self-silencing.
2. **Stride canonical dir = `stride`.** It matches the site dir that owns the Layer-C memory (`~/Sites/stride/memory/`), it's what phase-2 used, and the other two dirs are satellites: `stride-lms/` holds business docs (DECISIONS.md, PIPELINE.md — moved into `stride/`), `stridelms/` is empty (deleted). The Statamic marketing site `~/Sites/stridelms` gets a pointer line inside `stride/STATE.md`, not its own fleet dir — one product line, one fleet entry.
3. **Draft format:** ≤ 40 lines, fleet-relevant only. Header: `> DRAFT (2026-07-03, auto-generated from <sources>) — review, edit, commit manually; Layer-B commits are Stefan's ritual.` Sections: Status · Stack/where it lives · Deploy · Open risks · Client/deal context (only if visible in sources).
4. **Fleet drafting = ONE task, sequential.** Each draft writes a different new file so parallel writes would be safe, but the SDD no-parallel-implementers rule wins — one implementer, seven drafts, one review.
5. **`/memory-audit` canonical owner = netdust-core.** Core's CLAUDE.md declares it ("core defines the memory convention"); the netdust-agent copy (byte-identical) is deleted so the command registers exactly once. Hardening Item 3.1 is marked shipped (see premise drift).
6. **Marker's replacement side-effect = nothing** (per decision record): the `done cwd=… wrote=[…]` line in `~/.claude/logs/memory-hook.log` already records every fire.

---

## File structure (what changes where)

| File | Change |
|---|---|
| `plugins/netdust-agent/hooks/session-stop.py` | delete `append_state_marker`, `daily_marker_already_written`, the visibility-marker block + `tags_seen_pre_dedup`/`genuine_empty_session`, (and `has_tag_content` if unreferenced); fix docstring |
| `plugins/netdust-agent/tests/test_tag_scanner.py` | replace `test_no_tags_writes_marker` with two denial tests |
| `plugins/netdust-agent/tests/test_stop_hook_idempotency.py` | delete `test_daily_marker_written_once_per_day`; retitle the deduped-re-fire marker test as a plain denial regression |
| `plugins/netdust-agent/hooks/session-start.sh` | Tag-shortcuts line gains SKILL-EDGE; new conditional skill-audit nudge |
| `plugins/netdust-agent/tests/test_session_start.py` | + stamp-nudge tests (present when stale/missing, absent when fresh) |
| `plugins/netdust-agent/commands/skill-audit.md` | + final "write the stamp" step |
| `plugins/netdust-agent/tests/hook_test_utils.py` | NEW shared helper module (msg / write_transcript / run_stop_hook) |
| `plugins/netdust-agent/tests/test_stop_hook_{idempotency,dedup}.py`, `test_no_auto_memory.py`, `test_tag_scanner.py` | import shared helpers, delete byte-identical local copies |
| `plugins/netdust-agent/commands/memory-audit.md` | DELETED (core copy is canonical) |
| `plugins/netdust-core/CLAUDE.md` | tagged-capture list gains SKILL-EDGE |
| `plans/2026-06-07-harness-completeness-and-rigor.md` | Item 3.1 marked shipped |
| `.claude-plugin/marketplace.json` + both `plugin.json` | agent 0.3.3, core 0.2.4 |
| `~/Sites/netdust-wp-manager/memory/projects/` (machine state) | stride merge + 7 DRAFT STATE.md files, uncommitted |

---

# CLUSTER 1 — netdust-agent hook behavior (Tasks 1–4)

## Task 1: Drop the daily marker — RED-first denial

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-stop.py` (docstring L20–23; delete L297–319; delete L565–576 vars + L611–623 marker block)
- Modify: `plugins/netdust-agent/tests/test_tag_scanner.py:165-183` (replace `test_no_tags_writes_marker`) + its entry in `run()` (~L265)
- Modify: `plugins/netdust-agent/tests/test_stop_hook_idempotency.py:268-297` (delete `test_daily_marker_written_once_per_day`) + registry entry L413; update docstrings at L76 and L209–212

**Interfaces:**
- Consumes: existing test-module shape — each test is `def test_x() -> tuple[bool, str]`, aggregated by a module-level `run()`; local helpers `_msg(role, text, uuid)`, `_write_transcript(path, messages)`, `_run_hook(cwd, transcript)`.
- Produces: the post-marker hook contract every later task relies on — *a no-tag transcript causes ZERO writes under the project* (only the sidecar + log move).

**Test contract (Tier A):** RED-first. Denial assertions: (1) no-tag transcript against a project WITH a pre-seeded `memory/STATE.md` → hook exits 0 and STATE.md is byte-identical after the fire; (2) no-tag transcript against a project with a `memory/` dir but NO STATE.md → STATE.md is not created. The old "marker written" and "once per day" tests are deleted because the behavior they pin is the behavior being removed.

- [ ] **Step 1: Write the failing tests.** In `test_tag_scanner.py`, replace `test_no_tags_writes_marker` (L165–183) with:

```python
def test_no_tags_writes_nothing() -> tuple[bool, str]:
    """DENIAL (0.3.3): a transcript with no tags must produce ZERO memory
    writes. The daily 'session ended' marker was dropped — liveness lives in
    ~/.claude/logs/memory-hook.log, not STATE.md."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-nomarker-"))
    try:
        (tmp / "memory").mkdir()
        seeded = "# STATE\n\nexisting content untouched by no-op fires\n"
        (tmp / "memory" / "STATE.md").write_text(seeded)
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "Just chatting, nothing tagged here.", "u1"),
        ])
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"no-writes: hook exited {result.returncode}"
        after = (tmp / "memory" / "STATE.md").read_text()
        if after != seeded:
            return False, f"no-writes: STATE.md mutated on a no-tag fire.\nGot:\n{after[:300]}"
        return True, "no-tag session: STATE.md byte-identical (marker dropped)"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_tags_creates_no_state_file() -> tuple[bool, str]:
    """DENIAL (0.3.3): a no-tag fire must not CREATE STATE.md either."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-nomarker2-"))
    try:
        (tmp / "memory").mkdir()  # scaffolding exists, file does not
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "No tags in this session.", "u1"),
        ])
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"no-create: hook exited {result.returncode}"
        if (tmp / "memory" / "STATE.md").exists():
            return False, "no-create: STATE.md created on a no-tag fire"
        return True, "no-tag session: STATE.md not created"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

  Adapt the helper names/imports to what the module already uses (it may build transcripts inline — follow its local pattern; `tempfile`/`shutil` imports may already exist, add if missing). Register both in `run()`, remove the old `test_no_tags_writes_marker()` entry.

- [ ] **Step 2: Run to verify RED.** `cd /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/tests && bash run.sh` — expect `test_tag_scanner` FAIL: STATE.md gains `[YYYY-MM-DD] — session ended (no significant changes captured)` so byte-identity fails and the no-create case fails.

- [ ] **Step 3: Delete the marker machinery.** In `hooks/session-stop.py`:
  1. Delete `append_state_marker` (L297–306) and `daily_marker_already_written` (L309–319) whole.
  2. Delete the `tags_seen_pre_dedup = has_tag_content(tags)` line (~L568) and its comment (~L565–567).
  3. Delete the entire "Visibility marker" block in `main()` (~L611–623): comment + `genuine_empty_session` + the `if` + `append_state_marker(...)` call.
  4. `grep -rn "has_tag_content" plugins/netdust-agent/` — if the only remaining hit is its definition, delete the function too (YAGNI); if any test imports it, leave it.
  5. Docstring L22–23: replace `  • No-op writes a visible marker to STATE.md (so you SEE the hook working)` with `  • A no-op fire writes NOTHING to the project — the log line above is the liveness signal (daily marker dropped in 0.3.3)`.

- [ ] **Step 4: Prune the idempotency tests.** In `test_stop_hook_idempotency.py`: delete `test_daily_marker_written_once_per_day` (L268–297) and its `run()` registry entry (L413). Keep `test_no_marker_when_tags_deduped_after_transcript_change` (L209–238) — it remains a valid denial regression — but update its docstring: the marker is gone entirely, so the assertion is now "a deduped re-fire writes nothing", not "no *spurious* marker". Update the L76-area docstring the same way.

- [ ] **Step 5: Run to verify GREEN.** `bash run.sh` — all modules pass; `test_tag_scanner` shows the two new denial descriptions; net test delta across the two modules: −2 old, +2 new.

- [ ] **Step 6: Commit.**
```bash
git add plugins/netdust-agent/hooks/session-stop.py plugins/netdust-agent/tests/test_tag_scanner.py plugins/netdust-agent/tests/test_stop_hook_idempotency.py
git commit -m "feat(agent)!: drop the daily 'no significant changes' STATE.md marker — no-op fires now write nothing; liveness is memory-hook.log only"
```

## Task 2: Teach SKILL-EDGE in the session-start Tag-shortcuts line

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-start.sh:280`

**Interfaces:**
- Consumes: the Stop-hook scanner regex `^\s*SKILL-EDGE:\s*([a-z0-9_-]+):\s*(.*)$` (case-insensitive) — VERIFIED at plan-time against `session-stop.py:134`; the taught syntax `SKILL-EDGE: <skill-name>: <lesson>` matches it, skill segment `[a-z0-9_-]+` only.
- Produces: the injected discipline text Task 6 (core CLAUDE.md) must stay consistent with.

**Test tier:** `no unit test: Tier B, injected-copy change — no branching logic; the scanner side is already pinned by test_tag_scanner's skill-edge test, and the budget tests stay green.`

- [ ] **Step 1: Extend the line.** Replace L280 with:

```bash
  OUTPUT+="**Tag shortcuts** (the Stop hook lifts these into memory deterministically — use them when you don't want to interrupt the flow to edit a file): write \`DECISION: ...\`, \`RISK: ...\`, \`LESSON: ...\`, \`TODO: ...\` in your response and they get captured. For a skill gotcha, write \`SKILL-EDGE: <skill-name>: <lesson>\` — it lands in that skill's lessons.md (skill name = the skill's directory name, lowercase/digits/hyphens).\n\n"
```

- [ ] **Step 2: Verify.** `bash -n plugins/netdust-agent/hooks/session-start.sh` (syntax) then `bash run.sh` in tests/ — `test_session_start` + `test_session_start_budget` green.

- [ ] **Step 3: Commit.**
```bash
git add plugins/netdust-agent/hooks/session-start.sh
git commit -m "feat(agent): teach SKILL-EDGE alongside DECISION/RISK/LESSON/TODO in the session-start tag shortcuts"
```

## Task 3: Periodic /skill-audit sweep — stamp file + conditional nudge

**Files:**
- Modify: `plugins/netdust-agent/hooks/session-start.sh` (insert after the Tag-shortcuts line, INSIDE the memory-discipline `if` block, before the "goal" line at L281)
- Modify: `plugins/netdust-agent/commands/skill-audit.md` (new final step)
- Modify: `plugins/netdust-agent/tests/test_session_start.py` (two new tests)

**Interfaces:**
- Consumes: stamp path contract `~/.claude/logs/skill-audit-last-run`, overridable via env `NETDUST_SKILL_AUDIT_STAMP` (test seam).
- Produces: that same stamp contract — `/skill-audit` writes it, `session-start.sh` reads its mtime.

**Test contract (Tier A):** conditional injection logic. RED-first in `test_session_start.py` using the module's existing run-the-script harness (it has a local `_run_hook`; pass the env override through it — extend its signature with `env_extra=None` if needed): (1) stamp missing → injected output contains `Skill-audit cadence`; (2) stamp file freshly touched (via `NETDUST_SKILL_AUDIT_STAMP` pointing at a tmp file) → output does NOT contain it (**denial path**). Both against a tmp project WITH `memory/STATE.md` (the nudge lives inside the discipline block).

- [ ] **Step 1: Write the two failing tests** (adapt to the module's harness shape):

```python
def test_skill_audit_nudge_when_stamp_missing() -> tuple[bool, str]:
    """No stamp (or >30d old) → one-line /skill-audit nudge is injected."""
    tmp = _project_with_memory()          # tmp project with memory/STATE.md
    out = _run_hook(tmp, env_extra={
        "NETDUST_SKILL_AUDIT_STAMP": str(tmp / "no-such-stamp"),
    })
    ok = "Skill-audit cadence" in out
    return ok, ("stale stamp: nudge injected" if ok
                else f"nudge missing from output: {out[:300]}")


def test_no_skill_audit_nudge_when_stamp_fresh() -> tuple[bool, str]:
    """DENIAL: a fresh stamp (<30d) must suppress the nudge."""
    tmp = _project_with_memory()
    stamp = tmp / "skill-audit-last-run"
    stamp.write_text("2026-07-03\n")      # mtime = now
    out = _run_hook(tmp, env_extra={"NETDUST_SKILL_AUDIT_STAMP": str(stamp)})
    ok = "Skill-audit cadence" not in out
    return ok, ("fresh stamp: nudge suppressed" if ok
                else "nudge injected despite fresh stamp")
```

  If the module has no `_project_with_memory` helper, build the tmp project inline the way its existing tests do. Register both in `run()`.

- [ ] **Step 2: Run to verify RED.** `bash run.sh` — both new tests FAIL (`Skill-audit cadence` never appears; test 1 red, test 2 green-by-accident is acceptable only if test 1 is red — the pair goes red/green together after Step 3).

- [ ] **Step 3: Implement the nudge.** In `session-start.sh`, immediately after the Tag-shortcuts `OUTPUT+=` line (still inside the `if [[ -f "$STATE" ]] || [[ -f "$LESSONS" ]]` block):

```bash
  # ── Periodic /skill-audit nudge (decision 2026-07-03) ─────────────────────
  # /skill-audit writes this stamp on completion; nudge when it's missing or
  # >30 days old. Env override is the test seam.
  SKILL_AUDIT_STAMP="${NETDUST_SKILL_AUDIT_STAMP:-$HOME/.claude/logs/skill-audit-last-run}"
  SKILL_AUDIT_STALE=1
  if [[ -f "$SKILL_AUDIT_STAMP" ]] && [[ -n "$(find "$SKILL_AUDIT_STAMP" -mtime -30 2>/dev/null)" ]]; then
    SKILL_AUDIT_STALE=0
  fi
  if (( SKILL_AUDIT_STALE )); then
    OUTPUT+="**Skill-audit cadence:** the last \`/skill-audit\` sweep is >30 days old or was never recorded. If this session leans on harness skills, propose running \`/skill-audit\` before it ends.\n\n"
  fi
```

- [ ] **Step 4: Add the stamp step to the command.** Append to `plugins/netdust-agent/commands/skill-audit.md`, after the "Output format" section and before "Boundaries":

```markdown
## Record the run

After printing the report, record the sweep so the session-start nudge goes quiet for 30 days:

```bash
mkdir -p ~/.claude/logs && date +%Y-%m-%d > ~/.claude/logs/skill-audit-last-run
```

This stamp is the ONLY file this command writes. It is machine state (like the memory-hook log), never committed.
```

  Also add `Write` to the frontmatter `allowed_tools` if the stamp write needs it (Bash suffices — leave `allowed_tools` as `["Bash", "Read"]`).

- [ ] **Step 5: Run to verify GREEN.** `bash run.sh` — both new tests pass, budget tests still green (the nudge is ~230 bytes).

- [ ] **Step 6: Commit.**
```bash
git add plugins/netdust-agent/hooks/session-start.sh plugins/netdust-agent/commands/skill-audit.md plugins/netdust-agent/tests/test_session_start.py
git commit -m "feat(agent): periodic /skill-audit sweep — command stamps its last run; session-start nudges when the stamp is >30d old"
```

## Task 4: Dedup the stop-hook test-helper triad into a shared non-test module

**Files:**
- Create: `plugins/netdust-agent/tests/hook_test_utils.py`
- Modify: `plugins/netdust-agent/tests/test_stop_hook_idempotency.py`, `test_stop_hook_dedup.py`, `test_no_auto_memory.py`, `test_tag_scanner.py` (only where local helpers are byte-equivalent to the shared ones)

**Interfaces:**
- Consumes: `run.sh` executes with cwd = `tests/`, so `import hook_test_utils` resolves via the cwd path entry that `python3 -c` adds. The glob `test_*.py` does not match `hook_test_utils.py` — it is never executed as a test module (this is the load-bearing naming rule).
- Produces: `msg(role: str, text: str, uuid: str) -> dict`, `write_transcript(path: Path, messages: list[dict]) -> None`, `run_stop_hook(cwd: Path, transcript: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess`.

**Test tier:** `no unit test: Tier B, test-infrastructure refactor — behavior-preserving by definition; the proof is run.sh green before AND after with an identical per-module pass count.`

- [ ] **Step 1: Record the baseline.** `bash run.sh | tail -8` — note the pass counts (post-Task-3 state).

- [ ] **Step 2: Create the shared module.**

```python
"""hook_test_utils.py — shared helpers for the stop-hook test family.

Deliberately NOT named test_*.py: run.sh's glob must never execute this as
a test module. Only byte-equivalent helpers were lifted here; modules whose
_run_hook targets a different hook (session-start, subagent-stop,
standards-gate) keep their own local variants on purpose.
"""
import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "session-stop.py"


def msg(role: str, text: str, uuid: str) -> dict:
    """One transcript message with a top-level uuid (real CC shape)."""
    return {
        "type": role,
        "uuid": uuid,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def write_transcript(path: Path, messages: list[dict]) -> None:
    with open(path, "w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")


def run_stop_hook(cwd: Path, transcript: Path,
                  env_extra: dict | None = None) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    return subprocess.run(
        ["python3", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, **(env_extra or {})},
    )
```

- [ ] **Step 3: Migrate the byte-equivalent call sites.** For each of the four stop-hook modules, DIFF its local `_msg` / `_write_transcript` / `_run_hook` against the shared versions first. Where equivalent, delete the local def and alias at the top so call sites don't churn:

```python
from hook_test_utils import (
    msg as _msg,
    write_transcript as _write_transcript,
    run_stop_hook as _run_hook,
)
```

  Where a local variant genuinely differs (extra env vars, different payload keys, a different hook path — expected in `test_session_start*.py`, `test_subagent_stop.py`, `test_standards_gate_hook.py`, possibly `test_plugin_version_resolution.py`), LEAVE IT LOCAL and do not force it into the shared module. Scope discipline: this task removes duplication, it does not redesign the harness.

- [ ] **Step 4: Run to verify identical.** `bash run.sh | tail -8` — same modules, same per-module pass counts as Step 1, zero failures.

- [ ] **Step 5: Commit.**
```bash
git add plugins/netdust-agent/tests/hook_test_utils.py plugins/netdust-agent/tests/test_stop_hook_idempotency.py plugins/netdust-agent/tests/test_stop_hook_dedup.py plugins/netdust-agent/tests/test_no_auto_memory.py plugins/netdust-agent/tests/test_tag_scanner.py
git commit -m "refactor(agent-tests): lift the _msg/_write_transcript/_run_hook triad into shared hook_test_utils (non-test filename so run.sh's glob skips it)"
```

**Integration gate (Cluster 1):** `bash plugins/netdust-agent/tests/run.sh` fully green; `grep -rn "no significant changes" plugins/netdust-agent/hooks/ plugins/netdust-agent/tests/` returns ZERO hits in code (docstring mentions of the historical behavior are acceptable only in past-tense comments); `test_no_auto_memory.py` is untouched by every diff in this cluster (`git diff main -- plugins/netdust-agent/tests/test_no_auto_memory.py` shows only the Task-4 helper-import hunk).

`── REVIEW GATE ── (tier: STANDARD — multi-file hook-behavior change; touches the Stop/SessionStart hooks but no 1a surface [local self-produced transcripts, no attacker-supplied input] and INV-1 is only strengthened. 2 finders + simplicity pass; escalate to FULL only if a finding lands on the .no-auto-memory exclusion path.)`

---

# CLUSTER 2 — command/doc reconciliation (Tasks 5–6)

## Task 5: Resolve /memory-audit dual ownership + close hardening Item 3.1

**Files:**
- Delete: `plugins/netdust-agent/commands/memory-audit.md`
- Modify: `plans/2026-06-07-harness-completeness-and-rigor.md:112`

**Interfaces:**
- Consumes: ground-truth that both copies are byte-identical (`diff` verified at plan-time) and both ALREADY implement propose-consolidation (dry-run + `--apply` archive, Steps A1–A4) — Item 3.1's ask is shipped; only the drift remains.
- Produces: `/memory-audit` resolves to exactly one plugin (netdust-core).

**Test tier:** `no unit test: Tier B, file deletion + doc checkbox — verification is the sibling-site audit grep below.`

- [ ] **Step 1: Delete the duplicate.** `git rm plugins/netdust-agent/commands/memory-audit.md` (core's byte-identical copy is canonical per its CLAUDE.md: "core defines the memory convention").

- [ ] **Step 2: Mark Item 3.1 shipped.** In `plans/2026-06-07-harness-completeness-and-rigor.md` L112, append to the item line: ` — **SHIPPED before 2026-07-03** (ground-truthed at phase-4 planning: /memory-audit already carries the full propose-consolidation flow, dry-run default + --apply archive, Steps A1–A4; the netdust-agent duplicate copy was removed 2026-07-03, netdust-core canonical).`

- [ ] **Step 3: Sibling-site audit — command registration.** Run `find /home/ntdst/Projects/netdust-plugins/plugins -name "memory-audit.md"` → exactly ONE hit (netdust-core). Run `grep -rn "memory-audit" plugins/netdust-agent/CLAUDE.md plugins/netdust-agent/.claude-plugin/plugin.json` → confirm nothing in netdust-agent still claims the command (the plugin.json description does not list it — verified at plan-time; if a hit appears, fix the reference in this task).

- [ ] **Step 4: Commit.**
```bash
git add -A plugins/netdust-agent/commands plans/2026-06-07-harness-completeness-and-rigor.md
git commit -m "fix(agent): remove duplicate /memory-audit command — netdust-core copy is canonical; mark hardening Item 3.1 shipped"
```

## Task 6: Add SKILL-EDGE to netdust-core's tagged-capture doc

**Files:**
- Modify: `plugins/netdust-core/CLAUDE.md` (the "Tagged capture" list: DECISION/RISK/LESSON/TODO bullets)

**Interfaces:**
- Consumes: the exact syntax taught in Task 2 (`SKILL-EDGE: <skill-name>: <lesson>`) and the scanner's routing (`skills/.../<skill>/lessons.md`) — keep the three teaching sites word-consistent.

**Test tier:** `no unit test: Tier B, documentation line.`

- [ ] **Step 1: Add the bullet** after the `TODO:` line in the Tagged capture list:

```markdown
- `SKILL-EDGE: <skill-name>: <lesson>` → that skill's `lessons.md` (any installed netdust-* plugin; skill name = the skill's directory name)
```

- [ ] **Step 2: Sibling-site audit — tag-teaching consistency.** `grep -rn "SKILL-EDGE" plugins/netdust-agent/hooks/session-start.sh plugins/netdust-core/CLAUDE.md plugins/netdust-agent/hooks/session-stop.py` → all three teach the same `SKILL-EDGE: <skill>: <text>` shape (session-stop.py's docstring already does — verified at plan-time). Fix any divergence here.

- [ ] **Step 3: Commit.**
```bash
git add plugins/netdust-core/CLAUDE.md
git commit -m "docs(core): document the SKILL-EDGE tag in the tagged-capture list (matches the session-start nudge + Stop-hook scanner)"
```

**Integration gate (Cluster 2):** `bash plugins/netdust-agent/tests/run.sh` still fully green (deleting a command file and editing docs must not move any test).

`── REVIEW GATE ── (tier: LIGHT — command-file deletion + doc lines, no code paths. Single generalist pass over the diff + the two sibling-audit grep outputs.)`

---

# CLUSTER 3 — fleet drafts + delivery (Tasks 7–9)

## Task 7: Merge the stride naming drift (machine state, uncommitted)

**Files (all under `~/Sites/netdust-wp-manager/memory/projects/` — NOT the plugins repo):**
- Move: `stride-lms/DECISIONS.md` → `stride/DECISIONS.md`; `stride-lms/PIPELINE.md` → `stride/PIPELINE.md`
- Delete dirs: `stride-lms/` (after the moves), `stridelms/` (verified empty at plan-time)
- Keep: `stride/PROPAGATION-2026-06-10.md` in place

**Interfaces:**
- Produces: the canonical `stride/` dir Task 8 drafts into.

**Test tier:** `no unit test: Tier B, file moves in machine state — verification is the ls check below.`

- [ ] **Step 1: Move + remove** (plain `mv`/`rmdir`, NOT `git mv` — the working tree must show Stefan the change; nothing gets staged or committed):

```bash
cd /home/ntdst/Sites/netdust-wp-manager/memory/projects
mv stride-lms/DECISIONS.md stride-lms/PIPELINE.md stride/
rmdir stride-lms stridelms
```

  If `rmdir` fails on either dir, STOP and list the unexpected contents — do not `rm -rf`; an unexpected file means the plan-time inventory drifted and Stefan decides.

- [ ] **Step 2: Verify.** `ls stride/` → `DECISIONS.md PIPELINE.md PROPAGATION-2026-06-10.md`; `ls | grep -c stride` → `1`. `git -C /home/ntdst/Sites/netdust-wp-manager status --short memory/projects/` shows the moves as unstaged working-tree changes — leave them exactly there.

## Task 8: Auto-draft the 7 missing fleet STATE.md files (uncommitted, DRAFT-headed)

**Files (create, all under `~/Sites/netdust-wp-manager/memory/projects/`):**
- `atelier296/STATE.md`, `cargo/STATE.md`, `netdust/STATE.md`, `ntdst-core/STATE.md`, `ntdst-starter/STATE.md`, `stride/STATE.md`, `vad-vormingen/STATE.md`
- (houvast/STATE.md already exists — do not touch)

**Interfaces:**
- Consumes: per-site sources in the table below; the draft template below.
- Produces: nothing downstream — Stefan reviews and commits manually.

**Test tier:** `no unit test: Tier B, content drafting — verification is the header + line-count check in Step 3.`

**This is ONE task on purpose** (Decision 4): seven independent new files would be parallel-safe, but the SDD no-parallel-implementers rule wins; one implementer drafts all seven sequentially.

**Draft template (every file starts exactly like this):**

```markdown
# <Site> — Fleet STATE

> DRAFT (2026-07-03, auto-generated from <sources used>) — review, edit, and
> commit manually. Layer-B commits are Stefan's ritual; nothing here is committed.

**Status:** <live / in build / dormant — one line>
**Stack / where it lives:** <framework, ~/Sites path, hosting if visible>
**Deploy:** <method from site.yml or memory, or "not determined from sources">
**Open risks:** <bullets, only risks with cross-site or client relevance>
**Client / deal context:** <only if visible in sources; omit the section otherwise>
```

Rules: ≤ 40 lines per file; fleet-relevant only (a future cross-site session's first read) — no per-project trivia, no session narratives; every claim traceable to a source; where a source is thin, say so in the draft rather than inventing.

**Per-site source table (ground-truthed 2026-07-03):**

| Fleet dir | Sources |
|---|---|
| `atelier296` | `~/Sites/atelier296/memory/STATE.md` + `lessons.md`; `git -C ~/Sites/atelier296 log --oneline -20` |
| `cargo` | `~/Sites/cargo/memory/STATE.md` + `lessons.md`; git log |
| `netdust` | `~/Sites/netdust/memory/STATE.md` + `lessons.md`; git log |
| `ntdst-core` | **no `~/Sites` dir exists** — source is the plugins monorepo: `/home/ntdst/Projects/netdust-plugins/memory/` + its git log; header must name that unusual source |
| `ntdst-starter` | **no Layer-C memory** — `git -C ~/Sites/ntdst-starter log --oneline -30` only (check `~/Sites/ntdst-starter-kit` for a README); header carries `low-confidence: git history only` |
| `stride` | `~/Sites/stride/memory/STATE.md` + `lessons.md`; the merged siblings `stride/DECISIONS.md`, `PIPELINE.md`, `PROPAGATION-2026-06-10.md` (from Task 7); git log. Include one pointer line: marketing site = `~/Sites/stridelms` (Statamic Peak) — one product line, one fleet entry (Decision 2) |
| `vad-vormingen` | `~/Sites/vad-vormingen/memory/STATE.md` + `lessons.md`; git log |

- [ ] **Step 1: Draft all seven**, sequentially, per the template + source table.
- [ ] **Step 2: Do NOT commit.** No `git add`, no commit, anywhere under netdust-wp-manager.
- [ ] **Step 3: Verify mechanically.**

```bash
cd /home/ntdst/Sites/netdust-wp-manager/memory/projects
for f in atelier296 cargo netdust ntdst-core ntdst-starter stride vad-vormingen; do
  head -3 "$f/STATE.md" | grep -q "DRAFT (2026-07-03" || echo "MISSING DRAFT HEADER: $f"
  [ "$(wc -l < "$f/STATE.md")" -le 40 ] || echo "OVER 40 LINES: $f"
done
git -C /home/ntdst/Sites/netdust-wp-manager status --short memory/projects/ | head -20
```

  Expected: no MISSING/OVER lines; git status shows only untracked/modified working-tree entries, nothing staged.

## Task 9: Ship — bump agent 0.3.3 + core 0.2.4, deliver, live-verify

**Files:**
- Modify: `.claude-plugin/marketplace.json` (netdust-agent `0.3.2 → 0.3.3`; netdust-core `0.2.3 → 0.2.4`)
- Modify: `plugins/netdust-agent/.claude-plugin/plugin.json` + `plugins/netdust-core/.claude-plugin/plugin.json` (same versions — lockstep, both carry a `version` field, verified at plan-time)

**Interfaces:**
- Consumes: Clusters 1–2 merged; the phase-1 delivery contract (marketplace bump → merge to main → push → `claude plugin marketplace update` → `claude plugin update <name>@netdust-plugins`), which rewrites `installed_plugins.json` installPath — the registry-based resolvers shipped in 0.3.1 follow it.

**Test tier:** `no unit test: Tier B, release mechanics — evidence is the live verification checklist, each command with observed output.`

- [ ] **Step 1: Merge + bump + push.** Merge `feat/phase4-memory-behavior` into `main`, set the four version fields, commit `chore: bump netdust-agent 0.3.3 + netdust-core 0.2.4 (phase-4 memory behavior changes)`, `git push`.

- [ ] **Step 2: Update the installed plugins.**

```bash
claude plugin marketplace update netdust-plugins
claude plugin update netdust-agent@netdust-plugins
claude plugin update netdust-core@netdust-plugins
```

- [ ] **Step 3: Live verification checklist** (fresh Claude Code session for hook-fire items; paste each output into the review record):
  1. `python3 -c "import json;d=json.load(open('$HOME/.claude/plugins/installed_plugins.json'));print({k:v[0]['installPath'] for k,v in d['plugins'].items() if k.startswith('netdust-agent') or k.startswith('netdust-core')})"` → paths end in `0.3.3` / `0.2.4`.
  2. In a scratch project with `memory/STATE.md`, run a session that writes NO tags, exit → `memory/STATE.md` unchanged (byte-compare), and `tail -3 ~/.claude/logs/memory-hook.log` shows the `done … wrote=[]` fire. **This is the decision-2 acceptance: liveness in the log, zero marker.**
  3. Same project, fresh session → the injected "Memory discipline" block contains the `SKILL-EDGE:` shortcut AND (stamp absent) the `Skill-audit cadence` nudge.
  4. Run `/skill-audit`, confirm `~/.claude/logs/skill-audit-last-run` exists; next fresh session → nudge gone.
  5. `/memory-audit` resolves (single registration, netdust-core).

- [ ] **Step 4: Record completion** in this plan's review section; any failed item loops back to its owning task — never patch the installed cache by hand.

**Integration gate (Cluster 3):** the Step-3 checklist IS the gate — 5/5 observed.

`── REVIEW GATE ── (tier: LIGHT — content drafts, machine-state file moves, and release mechanics; no code. Single generalist pass over: the 7 draft files [accuracy vs sources, header, ≤40 lines, nothing committed], the stride merge ls/git-status output, and the pasted verification outputs.)`

---

## Sibling-site audits (cross-cutting concerns, run at their named tasks)

1. **Marker string** (Cluster 1 gate): `grep -rn "no significant changes" plugins/` after Task 1 → allowed residuals ONLY: `plugins/netdust-core/commands/memory-audit.md` (its A1 archive rules must KEEP handling historical marker lines already sitting in fleet STATE.md files — do not "clean" them out of the command) and historical spec/plan docs (`netdust-wp/docs/.../2026-05-17-harness-design.md`, `plans/2026-07-03-phase*.md`). Zero hits in hooks/ and tests/ code.
2. **Tag-teaching sites** (Task 6 Step 2): session-start.sh L280 · netdust-core/CLAUDE.md tagged-capture list · session-stop.py module docstring — all three teach the identical `SKILL-EDGE: <skill>: <text>` syntax.
3. **Command registration** (Task 5 Step 3): exactly one `memory-audit.md` across `plugins/`.

## Deferrals (explicitly NOT this phase)

- Repo-level `ARCHITECTURE-INVARIANTS.md` authoring (carried from phase 1; INV-1 cited inline above).
- Phase-1's carried deferrals (netdust-wp 0.4.1 mismatch, pattern-miner GLOBAL.md ref, sync.sh coverage, etc.) stay carried.
- Any automation of Layer-B commits — Stefan's ritual by decision.

## Self-review (done at authoring)

- **Spec coverage:** Decision 1 (nudge) → Tasks 2+3+6; Decision 2 (marker drop) → Task 1 (+ live proof 9.3.2); Decision 3 (fleet drafts + stride merge) → Tasks 7+8; Item 3 → Task 5 (reshaped by ground-truth — see drift); helper dedup → Task 4; delivery → Task 9. ✓
- **Placeholder scan:** every code step carries real code; every run step carries command + expected output; no TBDs. ✓
- **Name consistency:** `hook_test_utils.py` / `msg` / `write_transcript` / `run_stop_hook`; `NETDUST_SKILL_AUDIT_STAMP`; `~/.claude/logs/skill-audit-last-run`; `Skill-audit cadence` (the greppable nudge marker) — each defined once, referenced identically in code, tests, and verification. ✓
- **Tier lines:** every task carries a test-tier line; Tier-A tasks (1, 3) carry denial-path contracts; Tier-B tasks carry `no unit test:` + reason, never a `Unit test:` line. ✓
- **Cluster sizing (1f/1h):** 4 / 2 / 3 tasks; no irreversible or security step in any cluster (the only deletion is a byte-identical duplicate file, recoverable from git); provisional tiers STANDARD / LIGHT / LIGHT with the one-way escalation rule noted at Cluster 1. ✓

## Premise drift found at ground-truthing (1c)

1. **Item 3 is already shipped.** Both `memory-audit.md` copies (netdust-core AND netdust-agent, byte-identical, 300 lines) already implement the full propose-consolidation flow — dry-run default, `--apply` archive, KEEP/ARCHIVE classification, dedup, budget targets (Steps A1–A4). The hardening plan's "currently warn-only" premise is stale. Phase-4 scope reshaped to: remove the duplicate registration (core canonical) + mark Item 3.1 done. Two documents cheaper than discovering it at dispatch.
2. **"9 missing STATE.md" is really 7 after the merge.** `houvast/STATE.md` already exists, and the stride trio (`stride`, `stride-lms`, `stridelms`) collapses to one canonical dir before drafting.
3. **`ntdst-core` has no `~/Sites` dir** — its draft sources from the plugins monorepo itself; **`ntdst-starter` has no Layer-C memory** — git-history-only, low-confidence header.
4. **The helper triad is wider than "3–4 modules" but heterogeneous:** `_msg` in 6 modules, `_run_hook` in 7 — several are divergent variants targeting other hooks. Dedup is scoped to the byte-equivalent stop-hook family (idempotency, dedup, no_auto_memory, tag_scanner); divergent locals stay local by design.
5. **`/memory-audit`'s marker-archival rules must survive the marker drop** — fleet STATE.md files may still carry historical marker lines on projects phase 2 didn't touch; the command keeps cleaning them (sibling audit 1 pins this).
