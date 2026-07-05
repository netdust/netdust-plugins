"""Tests for spec-kit/run-cost.py — per-dispatch / per-stage token-cost report.

Contract (specs/harness-efficiency/plan.md D6, tasks.md T11):

  run-cost.py <feature-dir> [--transcript-dir <dir>]

  Default transcript dir: ~/.claude/projects/<slug(cwd)>, slug = absolute cwd
  with every "/" and "." -> "-". `--transcript-dir` overrides it (this test
  suite ALWAYS overrides it — fixtures never point at a real transcript
  dir, per tasks.md's dependency note: "T11's fixture builder must never
  point tests at a real transcript dir").

  Inputs, all READ-ONLY:
    - every *.jsonl directly in the transcript dir (main sessions)
    - every <session>/subagents/agent-*.jsonl + sibling agent-*.meta.json
      (fields: agentType, description)
  For every line with .type == "assistant", sums .message.usage fields:
  output_tokens, cache_read_input_tokens, cache_creation_input_tokens,
  input_tokens.

  Window: <feature-dir>/run-log.jsonl, if present, bounds the run to
  [first ts, last ts]; per-stage table further segments that window at
  boundary events (gate-check-green, stage-enter, review-gate,
  loop-disarm-*) — same segmentation as run-trace.py show --durations (D5).
  No run-log.jsonl -> per-dispatch table only + note "per-stage attribution
  skipped", exit 0.

  Timestamps: both "...Z" and "...+00:00" suffix forms must parse.

  Denial / degradation paths (never a crash, never fabricated data, exit 0
  on all of them):
    - missing transcript dir     -> "no transcript found: <dir>", no report
    - no run-log.jsonl           -> per-dispatch only + the skip note
    - malformed transcript line  -> skipped
    - absent meta.json           -> dispatch labeled "unknown"

  Read-only guarantee (invariant #2): transcript-dir listing + every file's
  mtime must be byte-identical before and after a run.

  Exit codes: 0 success incl. every degradation path above, 1 usage error.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_COST = Path(__file__).resolve().parent.parent / "spec-kit" / "run-cost.py"


def run_cost(feature_dir: Path, transcript_dir: Path | None = None) -> tuple[int, str, str]:
    argv = [sys.executable, str(RUN_COST), str(feature_dir)]
    if transcript_dir is not None:
        argv += ["--transcript-dir", str(transcript_dir)]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout, p.stderr


# ── fixture builders ───────────────────────────────────────────────────────

def assistant_line(ts: str, usage: dict, model: str = "claude-sonnet-5") -> str:
    """One synthetic transcript line shaped like a real Claude Code
    transcript's assistant entry (ground-truthed field names only — output,
    not internals, of a real ~/.claude/projects/<slug>/*.jsonl file)."""
    return json.dumps({
        "type": "assistant",
        "timestamp": ts,
        "message": {"model": model, "role": "assistant", "usage": usage},
    })


def usage(output=0, cache_read=0, cache_creation=0, input_=0) -> dict:
    return {
        "output_tokens": output,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_creation,
        "input_tokens": input_,
    }


def write_main_session(transcript_dir: Path, session_id: str, lines: list[str]) -> Path:
    p = transcript_dir / f"{session_id}.jsonl"
    p.write_text("\n".join(lines) + "\n")
    return p


def write_subagent(transcript_dir: Path, session_id: str, agent_id: str,
                    lines: list[str], meta: dict | None) -> Path:
    sd = transcript_dir / session_id / "subagents"
    sd.mkdir(parents=True, exist_ok=True)
    jp = sd / f"agent-{agent_id}.jsonl"
    jp.write_text("\n".join(lines) + "\n")
    if meta is not None:
        (sd / f"agent-{agent_id}.meta.json").write_text(json.dumps(meta))
    return jp


def write_run_log(feature_dir: Path, events: list[tuple[str, str, dict]]) -> None:
    """events: list of (ts, event_name, data)."""
    lines = [json.dumps({"ts": ts, "event": ev, "data": data}) for ts, ev, data in events]
    (feature_dir / "run-log.jsonl").write_text("\n".join(lines) + "\n")


def make_feature(tmp: str) -> Path:
    d = Path(tmp) / "specs" / "demo"
    d.mkdir(parents=True)
    return d


def snapshot(transcript_dir: Path) -> dict[str, float]:
    """Filename -> mtime for every file under transcript_dir, recursively —
    used to prove the read-only invariant (#2) holds byte-for-byte."""
    return {
        str(p.relative_to(transcript_dir)): p.stat().st_mtime_ns
        for p in sorted(transcript_dir.rglob("*")) if p.is_file()
    }


def run() -> list[tuple[bool, str]]:
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    # ── Denial path: missing transcript dir -> exit 0, note, no report ────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        missing_dir = Path(tmp) / "does-not-exist"
        rc, out, err = run_cost(feature, transcript_dir=missing_dir)
        case("missing transcript dir -> exit 0", rc == 0)
        case("missing transcript dir -> 'no transcript found: <dir>' message",
             f"no transcript found: {missing_dir}" in (out + err))

    # ── Denial path: transcripts exist but no run-log.jsonl -> per-dispatch
    # only + skip note, exit 0 ─────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-a"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:00:00.000Z", usage(output=10, input_=5)),
        ])
        write_subagent(transcripts, session, "agent1", [
            assistant_line("2026-07-05T10:00:05.000Z", usage(output=20, input_=2)),
        ], meta={"agentType": "netdust-agent:implementer", "description": "T01 impl"})
        # deliberately no run-log.jsonl written
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("no run-log.jsonl -> exit 0", rc == 0)
        case("no run-log.jsonl -> 'per-stage attribution skipped' note",
             "per-stage attribution skipped" in (out + err).lower())
        case("no run-log.jsonl -> per-dispatch data still reported (agentType present)",
             "netdust-agent:implementer" in out)

    # ── Unit contract: per-dispatch totals equal hand-summed usage per
    # transcript; agentType/description read from meta.json; both
    # timestamp forms ("...Z" and "...+00:00") parsed without error ──────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-b"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T09:00:00.000Z",
                            usage(output=100, cache_read=50, cache_creation=25, input_=10)),
            assistant_line("2026-07-05T09:00:01+00:00",
                            usage(output=1, cache_read=1, cache_creation=1, input_=1)),
        ])
        write_subagent(transcripts, session, "agentXYZ", [
            assistant_line("2026-07-05T09:00:02.000Z",
                            usage(output=7, cache_read=3, cache_creation=2, input_=1)),
            assistant_line("2026-07-05T09:00:03+00:00",
                            usage(output=8, cache_read=4, cache_creation=1, input_=0)),
        ], meta={"agentType": "netdust-agent:reviewer", "description": "C1 review pass"})
        write_run_log(feature, [
            ("2026-07-05T09:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T09:00:04+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("well-formed fixture -> exit 0", rc == 0)
        # hand-summed subagent totals: output=15, cache_read=7,
        # cache_creation=3, input=1
        case("per-dispatch Σ output_tokens matches hand sum (15)", "15" in out)
        case("per-dispatch Σ cache_read_input_tokens matches hand sum (7)", "7" in out)
        case("per-dispatch agentType read from meta.json", "netdust-agent:reviewer" in out)
        case("per-dispatch description read from meta.json", "C1 review pass" in out)
        # main-session (controller) hand-summed totals: output=101, input=11
        case("controller row Σ output_tokens matches hand sum (101)", "101" in out)

    # ── Unit contract: window attribution to the correct stage segment ────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-c"
        write_main_session(transcripts, session, [])
        # one dispatch inside the FIRST segment (stage-enter -> review-gate)
        write_subagent(transcripts, session, "early", [
            assistant_line("2026-07-05T08:00:01+00:00", usage(output=50)),
        ], meta={"agentType": "netdust-agent:implementer", "description": "T01 early"})
        # one dispatch inside the SECOND segment (review-gate -> loop-disarm-finished)
        write_subagent(transcripts, session, "later", [
            assistant_line("2026-07-05T08:00:09+00:00", usage(output=999)),
        ], meta={"agentType": "netdust-agent:implementer", "description": "T02 later"})
        write_run_log(feature, [
            ("2026-07-05T08:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T08:00:05+00:00", "review-gate", {"cluster": "C1", "tier": "STANDARD"}),
            ("2026-07-05T08:00:10+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("segment fixture -> exit 0", rc == 0)
        text = out
        # The 999-token dispatch must be attributed to the LATER segment,
        # not merged into the same bucket as the 50-token early dispatch —
        # assert the two segment labels/boundaries both appear and are
        # distinguishable in the rendered per-stage table.
        idx_review_gate = text.find("review-gate")
        idx_999 = text.find("999")
        idx_50 = text.find("50")
        case("per-stage table renders a segment boundary (review-gate)",
             idx_review_gate != -1)
        case("later dispatch (999 tokens) attributed after the review-gate boundary",
             idx_999 != -1 and idx_review_gate != -1 and idx_999 > idx_review_gate)

    # ── Unit contract (C4 finding fix): per-stage attribution of controller
    # lines must be PER-LINE, not per-session-block. A controller session
    # spans every stage; attributing its whole totals to the window
    # containing the session's FIRST timestamp systematically inflates the
    # first window. Fixture: boundaries at 10:00 (stage-enter), 10:05
    # (review-gate), 10:30 (loop-disarm-finished); one main-session with an
    # assistant line at 10:02 (output=100, inside window 1) and another at
    # 10:10 (output=200, inside window 2). Window 1's per-stage total must
    # be 100 (not 300); window 2's must include the 200 line. ─────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-g"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:02:00+00:00", usage(output=100)),
            assistant_line("2026-07-05T10:10:00+00:00", usage(output=200)),
        ])
        write_run_log(feature, [
            ("2026-07-05T10:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T10:05:00+00:00", "review-gate", {"cluster": "C1", "tier": "STANDARD"}),
            ("2026-07-05T10:30:00+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("per-line controller attribution fixture -> exit 0", rc == 0)
        per_stage_section = out.split("── per-dispatch ──")[0]
        window1_line = ""
        window2_line = ""
        for line in per_stage_section.splitlines():
            if line.startswith("stage-enter"):
                window1_line = line
            elif line.startswith("review-gate"):
                window2_line = line
        case("per-stage window 1 (stage-enter -> review-gate) excludes the "
             "later controller line: output_tokens=100, not 300",
             "output=100 " in window1_line)
        case("per-stage window 2 (review-gate -> loop-disarm-finished) "
             "includes the later controller line: output_tokens=200",
             "output=200 " in window2_line)

    # ── Unit contract (C4 finding fix, in-window filter): D6 says "main-
    # session assistant LINES inside [the window] are counted" — the
    # window filter must drop out-of-window LINES, not the whole
    # controller row because its first line predates the window. Fixture:
    # a controller session with one line BEFORE win_start (09:50) and one
    # line INSIDE the window (10:02, output=100). The pre-window line must
    # be excluded; the in-window line's 100 tokens must still surface in
    # both the per-dispatch controller row AND the per-stage table — not
    # silently dropped because the session's first_ts precedes win_start. ──
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-h"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T09:50:00+00:00", usage(output=999999)),
            assistant_line("2026-07-05T10:02:00+00:00", usage(output=100)),
        ])
        write_run_log(feature, [
            ("2026-07-05T10:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T10:30:00+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("pre-window controller line fixture -> exit 0", rc == 0)
        case("pre-window controller line (999999) excluded from the run entirely",
             "999999" not in out)
        case("in-window controller line (output=100) still counted even though "
             "the session's FIRST line predates the run window",
             "output=100 " in out)

    # ── Denial path: malformed transcript line skipped without crash ──────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-d"
        write_main_session(transcripts, session, [
            "not json at all {{{",
            assistant_line("2026-07-05T07:00:00+00:00", usage(output=42)),
        ])
        write_run_log(feature, [
            ("2026-07-05T07:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T07:00:01+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("malformed transcript line -> exit 0 (no crash)", rc == 0)
        case("malformed transcript line skipped, well-formed sibling line still counted",
             "42" in out)

    # ── Denial path: absent meta.json -> dispatch labeled 'unknown' ───────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-e"
        write_main_session(transcripts, session, [])
        write_subagent(transcripts, session, "nometa", [
            assistant_line("2026-07-05T06:00:00+00:00", usage(output=5)),
        ], meta=None)  # no sibling meta.json written
        write_run_log(feature, [
            ("2026-07-05T06:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T06:00:01+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("absent meta.json -> exit 0 (no crash)", rc == 0)
        case("absent meta.json -> dispatch labeled 'unknown'", "unknown" in out)

    # ── READ-ONLY INVARIANT #2: transcript-dir listing + mtimes must be
    # byte-identical before and after a run. This is a dedicated assertion,
    # not folded into another case — a regression that writes into the
    # transcript dir must fail THIS test, standalone. ──────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-f"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T05:00:00+00:00", usage(output=1)),
        ])
        write_subagent(transcripts, session, "ro1", [
            assistant_line("2026-07-05T05:00:01+00:00", usage(output=2)),
        ], meta={"agentType": "netdust-agent:implementer", "description": "T01"})
        write_run_log(feature, [
            ("2026-07-05T05:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T05:00:02+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        before = snapshot(transcripts)
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        after = snapshot(transcripts)
        case("read-only invariant: transcript dir file listing unchanged", before.keys() == after.keys())
        case("read-only invariant: every transcript file's mtime unchanged", before == after)

    # ── Seam test: real (un-mocked) subprocess run against a full fixture
    # dir -> exit 0 + expected table content ───────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-seam"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T04:00:00+00:00", usage(output=3, input_=1)),
        ])
        write_subagent(transcripts, session, "seamagent", [
            assistant_line("2026-07-05T04:00:01+00:00", usage(output=6, input_=2)),
        ], meta={"agentType": "netdust-agent:test-author", "description": "T11 RED"})
        write_run_log(feature, [
            ("2026-07-05T04:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T04:00:02+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("seam: real subprocess run -> exit 0", rc == 0)
        case("seam: expected agentType surfaces in the real un-mocked run",
             "netdust-agent:test-author" in out)
        case("seam: expected description surfaces in the real un-mocked run",
             "T11 RED" in out)

    # ── Seam negative: nonexistent feature dir -> nonzero usage error ─────
    with tempfile.TemporaryDirectory() as tmp:
        nonexistent_feature = Path(tmp) / "specs" / "does-not-exist"
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        rc, out, err = run_cost(nonexistent_feature, transcript_dir=transcripts)
        case("seam negative: nonexistent feature dir -> nonzero exit", rc != 0)

    # =========================================================================
    # C4 review-gate findings (additive; original author cases above are
    # unchanged) — timestamp/input robustness, FAMILY 1.
    # =========================================================================

    # --- (a) non-string ts in a run-log boundary event -> treated as
    #     unparseable (None), no crash ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-nonstring-ts"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:00:01+00:00", usage(output=5)),
        ])
        (feature / "run-log.jsonl").write_text(
            json.dumps({"ts": 12345, "event": "stage-enter", "data": {"stage": "execute"}}) + "\n"
            + json.dumps({"ts": "2026-07-05T10:05:00+00:00", "event": "loop-disarm-finished", "data": {}}) + "\n"
        )
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("non-string run-log ts -> exit 0, no crash", rc == 0)
        case("non-string run-log ts -> no traceback", "Traceback" not in (out + err))

    # --- (c) naive timestamp (no Z/offset) in a run-log boundary event ->
    #     rejected as unparseable (would otherwise crash on aware-comparison
    #     in run_window/boundary_segments) ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-naive-ts"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:00:01+00:00", usage(output=5)),
        ])
        write_run_log(feature, [
            ("2026-07-05T10:00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T10:05:00+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("naive run-log ts -> exit 0, no crash", rc == 0)
        case("naive run-log ts -> no traceback", "Traceback" not in (out + err))

    # --- (d) out-of-order events in run-log -> run-cost already sorts
    #     boundary_points; verify positive-only segments (regression guard
    #     mirroring run-trace's fix, same run-log shape) ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-outoforder"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:00:01+00:00", usage(output=5)),
        ])
        write_run_log(feature, [
            ("2026-07-05T10:05:00+00:00", "loop-disarm-finished", {"iteration": "1"}),
            ("2026-07-05T10:00:00+00:00", "stage-enter", {"stage": "execute"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("out-of-order run-log -> exit 0", rc == 0)
        case("out-of-order run-log -> per-stage segment reflects sorted order, "
             "positive wall-clock (0:05:00), not negative",
             "wall=0:05:00" in out)

    # =========================================================================
    # C4 review-gate findings (additive; original author cases above are
    # unchanged) — boundary vocabulary + reconciliation, FAMILY 2.
    # =========================================================================

    # --- (e) manual `/loop off` emits literal event `loop-disarmed`
    #     (commands/loop.md) — must be accepted as a boundary event so
    #     per-stage attribution isn't silently skipped on manually-disarmed
    #     runs. The emitter (run-score.py's loop-disarm-* prefix vocabulary)
    #     is untouched. ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-manual-disarm"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:02:00+00:00", usage(output=50)),
        ])
        write_run_log(feature, [
            ("2026-07-05T10:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T10:05:00+00:00", "loop-disarmed", {"reason": "manual"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("manual loop-disarmed -> exit 0", rc == 0)
        case("manual loop-disarmed -> per-stage table rendered (2 boundaries "
             "recognized: stage-enter, loop-disarmed)",
             "── per-stage ──" in out)
        case("manual loop-disarmed -> segment labeled with the literal "
             "event name", "loop-disarmed" in out)

    # --- (f) closed-vs-half-open reconciliation: a controller line exactly
    #     AT win_end must appear in BOTH the per-dispatch total AND the
    #     final per-stage segment (the last segment is inclusive of end_ts;
    #     interior boundaries stay half-open so nothing double-counts). ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-win-end"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:02:00+00:00", usage(output=50)),
            assistant_line("2026-07-05T10:30:00+00:00", usage(output=77)),  # exactly win_end
        ])
        write_run_log(feature, [
            ("2026-07-05T10:00:00+00:00", "stage-enter", {"stage": "execute"}),
            ("2026-07-05T10:30:00+00:00", "loop-disarm-finished", {"iteration": "1"}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("win_end-boundary line fixture -> exit 0", rc == 0)
        per_stage_section = out.split("── per-dispatch ──")[0]
        per_dispatch_section = out.split("── per-dispatch ──")[1] if "── per-dispatch ──" in out else ""
        case("the last segment includes the line exactly at win_end "
             "(output=127, i.e. 50+77)",
             "output=127 " in per_stage_section)
        case("per-dispatch total for the win_end line's controller row is "
             "127 too (reconciles with the per-stage total)",
             "output=127 " in per_dispatch_section)

    # --- (g) run-log EXISTS but has <2 boundary events -> the message must
    #     say "no segment boundaries in run-log.jsonl", NOT the no-run-log
    #     message (which stays exact for the true no-run-log case). ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-no-boundaries"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:02:00+00:00", usage(output=50)),
        ])
        write_run_log(feature, [
            ("2026-07-05T10:00:00+00:00", "custom-non-boundary-event", {}),
        ])
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("run-log exists, no boundary events -> exit 0", rc == 0)
        case("run-log exists, no boundary events -> correct degradation "
             "message (not the no-run-log message)",
             "per-stage attribution skipped (no segment boundaries in "
             "run-log.jsonl)" in out)
        case("run-log exists, no boundary events -> does NOT print the "
             "no-run-log message", "no run-log.jsonl" not in out)

    # --- (g contract guard) the EXISTING no-run-log message stays EXACTLY
    #     as-is after the consolidation into a shared helper. ---
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp)
        transcripts = Path(tmp) / "transcripts"
        transcripts.mkdir()
        session = "sess-no-run-log"
        write_main_session(transcripts, session, [
            assistant_line("2026-07-05T10:02:00+00:00", usage(output=50)),
        ])
        # deliberately no run-log.jsonl written
        rc, out, err = run_cost(feature, transcript_dir=transcripts)
        case("no run-log.jsonl -> exact existing message unchanged",
             "per-stage attribution skipped (no run-log.jsonl)" in out)

    return results
