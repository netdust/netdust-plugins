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
from concurrent.futures import ThreadPoolExecutor

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
print(f"running {len(runnable)} cases x 2 arms, in parallel\n")

def run_case(c):
    """Both arms of one case, then its judge. Cases run concurrently — 24 serial
    claude -p calls with 35KB of context each took ~20 minutes."""
    sha = (c.get("baseline_ref") or "").split()[0] or None
    tmpl = "Reference documentation:\n\n{ctx}\n\n---\n\nUsing that documentation, answer:\n\n{q}"
    with ThreadPoolExecutor(max_workers=2) as ex:
        fb = ex.submit(ask, tmpl.format(ctx=load(c["context_before"], sha), q=c["prompt"]))
        fa = ex.submit(ask, tmpl.format(ctx=load(c["context_after"]),      q=c["prompt"]))
        a_before, a_after = fb.result(), fa.result()
    if a_before.startswith("ERROR:") or a_after.startswith("ERROR:"):
        return dict(id=c["id"], error=True, answer_before=a_before, answer_after=a_after)
    must, mustnt = c.get("must_contain",[]), c.get("must_not_contain",[])
    pb, pa = probe(a_before,must,mustnt), probe(a_after,must,mustnt)
    j = ask(JUDGE.format(q=c["prompt"], sig=c["with_skill_assertion"], a=a_after[:6000]), 180)
    return dict(id=c["id"], baseline_ref=c.get("baseline_ref"), before=pb, after=pa,
        discriminates=(not pb["clean"]) and pa["clean"],
        judge="PASS" if j.strip().upper().startswith("PASS") else "FAIL", judge_raw=j[:300],
        before_len=len(a_before), after_len=len(a_after),
        answer_before=a_before, answer_after=a_after)

with ThreadPoolExecutor(max_workers=4) as ex:
    results = list(ex.map(run_case, runnable))

for r in results:
    if r.get("error"):
        print(f"ERROR       {r['id']:<36} (no answer from one arm)"); continue
    pb, pa = r["before"], r["after"]
    mark = "PASS " if r["discriminates"] else ("BOTH-CLEAN" if pa["clean"] else "FAIL ")
    print(f"{mark:<11} {r['id']:<36} before_clean={pb['clean']!s:<5} after_clean={pa['clean']!s:<5} judge={r['judge']}")
    if pb["violations"]: print(f"              before taught (in code): {pb['violations']}")
    if pa["violations"]: print(f"              AFTER STILL TEACHES: {pa['violations']}")
    if pa["missing"]:    print(f"              after missing: {pa['missing']}")
    if pb.get("prose_mentions"): print(f"              before prose-mentions: {pb['prose_mentions']}  <- READ THESE")
    if pa.get("prose_mentions"): print(f"              after  prose-mentions: {pa['prose_mentions']}  <- READ THESE")
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
