#!/usr/bin/env bash
# Correctness eval for netdust-wp's re-anchor cases.
#
# DIFFERS FROM netdust-agent/evals/run-behavioral-eval.sh ON PURPOSE.
# That runner's baseline is NO SKILL, which is right for a discipline skill
# ("does it make the agent do something it skips by default"). These cases are
# CORRECTNESS re-anchors: the failure is that the skill taught a symbol the
# framework no longer has. A no-skill arm never says ntdst_router() at all, so
# it cannot show the fix landed. Baseline here is the OLD SKILL TEXT, read from
# the commit each case names in `baseline_ref`.
#
# Scoring is mechanical first (must_contain / must_not_contain on the answer),
# because these signatures are literal symbols and an LLM judge is not needed to
# see them. The judge runs second, for the qualitative half of the assertion.
#
# Usage: run-correctness-eval.sh [cases.json] [out.json]
set -uo pipefail
cd "$(dirname "$0")/.."   # plugins/netdust-wp
python3 - "${1:-evals/behavioral-lessons.json}" "${2:-evals/outputs/correctness-results.json}" <<'PY'
import json, subprocess, sys, os, re, pathlib

cases = json.load(open(sys.argv[1], encoding="utf-8"))["cases"]
out_path = sys.argv[2]
pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
REPO = subprocess.run(["git","rev-parse","--show-toplevel"],capture_output=True,text=True).stdout.strip()
CLEANROOM = "/tmp/claude-1000/cleanroom"
os.makedirs(CLEANROOM, exist_ok=True)
for stray in ("CLAUDE.md","AGENTS.md"):
    fp=os.path.join(CLEANROOM,stray)
    if os.path.exists(fp): os.remove(fp)
PREFIX = "plugins/netdust-wp/"

def ask(prompt, timeout=600, turns="14"):
    """--max-turns 6, not 1. At 1 these large-context prompts return the literal
    string "Error: Reached max turns (N)" and the probe then scores an EMPTY
    ANSWER as a skill failure. That produced a bogus 0/8 and a PASS->FAIL flip
    between two identical runs before it was caught."""
    try:
        r = subprocess.run(["claude","-p",prompt,"--max-turns",turns,
                            # CLEAN ROOM. Run 4 caught the BASELINE arm answering
                            # "those don't exist on current ntdst-core" — the FIXED
                            # knowledge, leaking in from the repo's own CLAUDE.md and
                            # context because the runner cd'd into the repo. A baseline
                            # that already knows the answer measures nothing.
                            "--system-prompt",
                            "You are a helpful assistant. Answer using ONLY the "
                            "reference documentation the user provides. Do not rely "
                            "on other knowledge of this framework.",
                            "--strict-mcp-config"],
                           cwd=CLEANROOM,
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        if not out or "Reached max turns" in out or out.startswith("Error:"):
            return f"ERROR:no-answer rc={r.returncode} out={out[:120]!r}"
        return out
    except Exception as e:
        return f"ERROR:{e}"

def load(paths, sha=None):
    """Concatenate context files, from a commit when sha is given, else worktree."""
    out = []
    for rel in paths:
        if sha:
            r = subprocess.run(["git","-C",REPO,"show",f"{sha}:{PREFIX}{rel}"],
                               capture_output=True, text=True)
            if r.returncode != 0:      # file may not exist at that sha (router.md -> pages.md)
                continue
            body = r.stdout
        else:
            fp = os.path.join(REPO, PREFIX, rel)
            if not os.path.exists(fp): continue
            body = open(fp, encoding="utf-8").read()
        out.append(f"===== {rel} =====\n{body}")
    return "\n\n".join(out)

CODE = re.compile(r"```(?:php|javascript|js)?\n(.*?)```", re.S)
def probe(ans, must, mustnt):
    """must_contain is checked against the WHOLE answer; must_not_contain only
    against CODE FENCES.

    Run 3 scored three cases FAIL on prose that said "$theme->apiAction() is
    retired, do not use it" and "there is no toRestResponse()" — the desired
    behaviour, counted as the violation. A bare substring probe cannot tell a
    USE from a WARNING. Code fences can: the failure mode these cases exist to
    catch is a session PASTING the dead symbol, and pasted code lives in a fence."""
    code = "\n".join(CODE.findall(ans))
    hits = [m for m in must   if m.lower() in ans.lower()]
    viol = [m for m in mustnt if m.lower() in code.lower()]
    return {"contains": hits, "missing": [m for m in must if m not in hits],
            "violations": viol, "prose_mentions": [m for m in mustnt if m.lower() in ans.lower() and m not in viol],
            "clean": len(hits)==len(must) and not viol}

JUDGE = """An AI was asked a WordPress framework question, with reference documentation supplied.

REQUEST: {q}

REQUIRED BEHAVIOR: {sig}

--- ITS ANSWER ---
{a}

Does the answer exhibit the REQUIRED BEHAVIOR? Reply EXACTLY one line, then one sentence of reason:
PASS
FAIL"""

results=[]
runnable=[c for c in cases if "context_after" in c]
print(f"running {len(runnable)} cases x 2 arms\n")
for c in runnable:
    sha = (c.get("baseline_ref") or "").split()[0] or None
    before_ctx = load(c["context_before"], sha)
    after_ctx  = load(c["context_after"])
    tmpl = "Reference documentation:\n\n{ctx}\n\n---\n\nUsing that documentation, answer:\n\n{q}"
    a_before = ask(tmpl.format(ctx=before_ctx, q=c["prompt"]))
    a_after  = ask(tmpl.format(ctx=after_ctx,  q=c["prompt"]))
    if a_before.startswith("ERROR:") or a_after.startswith("ERROR:"):
        print(f"ERROR       {c['id']:<36} before={a_before[:60] if a_before.startswith('ERROR:') else 'ok'} after={a_after[:60] if a_after.startswith('ERROR:') else 'ok'}")
        results.append(dict(id=c["id"], error=True, answer_before=a_before, answer_after=a_after))
        json.dump(results, open(out_path,"w"), indent=1); continue
    must, mustnt = c.get("must_contain",[]), c.get("must_not_contain",[])
    pb, pa = probe(a_before,must,mustnt), probe(a_after,must,mustnt)
    j = ask(JUDGE.format(q=c["prompt"], sig=c["with_skill_assertion"], a=a_after[:6000]), 180)
    judge_pass = j.strip().upper().startswith("PASS")
    discriminates = (not pb["clean"]) and pa["clean"]
    results.append(dict(id=c["id"], baseline_ref=c.get("baseline_ref"),
        before=pb, after=pa, discriminates=discriminates,
        judge="PASS" if judge_pass else "FAIL", judge_raw=j[:300],
        before_len=len(a_before), after_len=len(a_after),
        # The ANSWERS, in full. skill-eval: every flagged match must be read by
        # a human — a probe cannot tell "use apiAction()" from "apiAction() is
        # retired, do not use it". Without these, a violation count is an
        # opinion, not a diagnosis.
        answer_before=a_before, answer_after=a_after))
    mark = "PASS " if discriminates else ("BOTH-CLEAN" if pa["clean"] else "FAIL ")
    print(f"{mark:<11} {c['id']:<36} before_clean={pb['clean']!s:<5} after_clean={pa['clean']!s:<5} judge={'PASS' if judge_pass else 'FAIL'}")
    if pb["violations"]: print(f"              before taught (in code): {pb['violations']}")
    if pb.get("prose_mentions"): print(f"              before prose-mentions: {pb['prose_mentions']}  <- READ THESE")
    if pa.get("prose_mentions"): print(f"              after  prose-mentions: {pa['prose_mentions']}  <- READ THESE")
    if pa["violations"]: print(f"              AFTER STILL TEACHES: {pa['violations']}")
    if pa["missing"]:    print(f"              after missing: {pa['missing']}")
    json.dump(results, open(out_path,"w"), indent=1)

err=[r for r in results if r.get("error")]
scored=[r for r in results if not r.get("error")]
d=sum(1 for r in scored if r["discriminates"]); jp=sum(1 for r in scored if r["judge"]=="PASS")
print(f"\n=== {d}/{len(scored)} discriminate | {jp}/{len(scored)} judge PASS | {len(err)} ERRORED (not scored) ===")
flagged=[r["id"] for r in scored if r["after"]["violations"]]
if flagged:
    print("MANUAL READ REQUIRED (a probe cannot tell a use from a retirement note): " + ", ".join(flagged))
print(f"results: {out_path}")
PY
