#!/usr/bin/env bash
# Behavioral eval for B1-tier discipline skills.
# For each skill: run a realistic coding prompt baseline (no skill) vs with-skill
# (skill text prepended), then a judge checks whether the skill's SIGNATURE
# behavior appears with-skill and is absent baseline. That delta = the skill enhances coding.
# Usage: run-behavioral-eval.sh <behavioral-cases.json> <out.json>
set -uo pipefail
CASES="${1:-evals/behavioral-cases.json}"
OUT="${2:-evals/outputs/behavioral-results.json}"

python3 - "$CASES" "$OUT" <<'PY'
import json, subprocess, sys

cases = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
results = []

def run(prompt, timeout=240):
    try:
        r = subprocess.run(["claude","-p",prompt,"--max-turns","6"],
                            capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR:{e}"

JUDGE = """Two AI agents answered the same coding request. ONE was given a discipline skill, the other was not. The skill's signature behavior is: "{signature}".

REQUEST: {query}

--- ANSWER A ---
{a}

--- ANSWER B ---
{b}

Question: Does exactly ONE of the answers exhibit the signature behavior "{signature}" markedly more than the other? Reply with EXACTLY one line:
WITH=A  (if A shows the signature behavior more)
WITH=B  (if B shows it more)
SAME    (if both show it equally or neither does)
Then a 1-sentence reason."""

for c in cases:
    skill_text = open(c["skill_path"], encoding="utf-8").read()[:6000]
    base = run(c["query"])
    withk = run(f"Apply this skill, then answer.\n\n<skill>\n{skill_text}\n</skill>\n\nRequest: {c['query']}")
    # randomize order so judge isn't biased by position: A=with, B=base
    verdict = run(JUDGE.format(signature=c["signature"], query=c["query"], a=withk[:3000], b=base[:3000]), timeout=120)
    enhanced = "WITH=A" in verdict.upper()
    results.append({
        "skill": c["skill"], "signature": c["signature"],
        "verdict": verdict[:200], "enhanced": enhanced,
        "baseline_len": len(base), "withskill_len": len(withk),
    })
    mark = "✓ ENHANCES" if enhanced else ("= no-delta" if "SAME" in verdict.upper() else "✗ check")
    print(f"{mark}  [{c['skill']:<24}] {verdict.splitlines()[0][:40] if verdict else '?'}")
    json.dump(results, open(out_path,"w"), indent=1)

ok=sum(1 for r in results if r["enhanced"])
print(f"\n=== {ok}/{len(results)} skills showed the with-skill behavioral delta ===")
PY
