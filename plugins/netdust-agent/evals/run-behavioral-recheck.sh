#!/usr/bin/env bash
set -uo pipefail
CASES="${1:-evals/behavioral-recheck.json}"; OUT="${2:-evals/outputs/behavioral-recheck-results.json}"
python3 - "$CASES" "$OUT" <<'PY'
import json, subprocess, sys
cases=json.load(open(sys.argv[1])); out=sys.argv[2]; results=[]
def run(p,t=240):
    try: return subprocess.run(["claude","-p",p,"--max-turns","6"],capture_output=True,text=True,timeout=t).stdout.strip()
    except Exception as e: return f"ERROR:{e}"
# Non-positional: judge each answer ALONE for whether it exhibits the signature. 0 or 1.
SCORE='Does this answer exhibit the behavior: "{sig}"? Answer EXACTLY 1 (yes, clearly) or 0 (no/weakly). One char only.\n\n--- ANSWER ---\n{ans}'
for c in cases:
    txt=open(c["skill_path"],encoding="utf-8").read()[:6000]
    base=run(c["query"]); withk=run(f"Apply this skill, then answer.\n\n<skill>\n{txt}\n</skill>\n\nRequest: {c['query']}")
    sb=run(SCORE.format(sig=c["signature"],ans=base[:3000]),120).strip()[:1]
    sw=run(SCORE.format(sig=c["signature"],ans=withk[:3000]),120).strip()[:1]
    enhanced = (sw=="1" and sb=="0")
    results.append({"skill":c["skill"],"baseline_score":sb,"withskill_score":sw,
                    "enhanced":enhanced,"baseline_len":len(base),"withskill_len":len(withk)})
    mark="✓ ENHANCES" if enhanced else ("= both-have-it" if sb==sw=="1" else ("✗ neither" if sb==sw=="0" else "?"))
    print(f"{mark}  [{c['skill']:<20}] baseline={sb} with-skill={sw}")
    json.dump(results,open(out,"w"),indent=1)
PY
