#!/usr/bin/env bash
# Trigger-eval harness for netdust-agent.
# For each artifact + each query, asks claude -p (as a judge) whether an agent
# SHOULD reach for that artifact given the query. Compares to should_trigger.
# Usage: run-trigger-eval.sh <queries.json> <out.json>
set -uo pipefail
QUERIES="${1:-evals/trigger-queries.json}"
OUT="${2:-evals/outputs/trigger-results.json}"

python3 - "$QUERIES" "$OUT" <<'PY'
import json, subprocess, sys, time

queries = json.load(open(sys.argv[1]))
out_path = sys.argv[2]
results = []

JUDGE = """You are a skill-router. Given a coding-related user request and ONE candidate tool's description, answer whether an agent SHOULD reach for that tool for this request.

Tool name: {name}
Tool description: {desc}

User request: "{query}"

Answer with EXACTLY one word: YES (the agent should use this tool for this request) or NO (it should not). No explanation."""

for i, q in enumerate(queries):
    prompt = JUDGE.format(name=q["name"], desc=q["desc"][:1500], query=q["query"])
    try:
        r = subprocess.run(["claude","-p",prompt,"--max-turns","1"],
                            capture_output=True, text=True, timeout=120)
        ans = r.stdout.strip().upper()
        fired = ans.startswith("YES")
    except Exception as e:
        ans=f"ERROR:{e}"; fired=None
    correct = (fired == q["should_trigger"]) if fired is not None else None
    results.append({**q, "judge_answer": ans[:20], "fired": fired, "correct": correct})
    mark = "✓" if correct else ("✗" if correct is False else "?")
    print(f"{mark} [{q['name']:<26}] trig={q['should_trigger']} fired={fired}  {q['query'][:55]}")
    json.dump(results, open(out_path,"w"), indent=1)  # checkpoint each

# summary
ok=sum(1 for r in results if r["correct"])
tot=len(results)
print(f"\n=== {ok}/{tot} correct ({100*ok//tot if tot else 0}%) ===")
PY
