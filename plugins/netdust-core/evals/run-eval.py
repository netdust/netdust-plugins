#!/usr/bin/env python3
"""
run-eval.py — netdust-core harness eval helper

Two modes:
  --prepare   parse rubric + scenarios, write per-agent prompts to prompts/
  --score     parse judge outputs from outputs/, write scored eval-log.md

See README.md in this directory for the orchestration flow.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

# ── Paths ─────────────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent
PROMPTS_DIR = HERE / "prompts"
OUTPUTS_DIR = HERE / "outputs"

RUBRIC_PATH = Path.home() / "Sites" / "netdust-wp-manager" / "tasks" / "eval-rubric.md"
SCENARIOS_PATH = Path.home() / "Sites" / "netdust-wp-manager" / "tasks" / "eval-scenarios.md"
LOG_PATH = Path.home() / "Sites" / "netdust-wp-manager" / "tasks" / "eval-log.md"

# ── Rubric parsing ────────────────────────────────────────────────────────────

# Matches: "### A1. Implements `NTDST_Service_Meta` (directly or via...)"
RULE_HEADING = re.compile(r"^### ([A-EX]+\d+[a-z]?)\.\s+(.+)$", re.MULTILINE)

# Match the verdict line after a rule heading
VERDICT_LINE = re.compile(
    r"^- \*\*Verdict:\*\*\s+`(canonical|aspirational|dropped)`",
    re.MULTILINE,
)


def parse_rubric(text: str) -> dict[str, dict]:
    """Returns {rule_id: {title, verdict, body}}.

    Walks every '### X1. ...' heading, slices to next heading, extracts verdict
    from the first matching verdict line in that slice.
    """
    rules: dict[str, dict] = {}
    matches = list(RULE_HEADING.finditer(text))
    for i, m in enumerate(matches):
        rule_id = m.group(1)
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        verdict_match = VERDICT_LINE.search(body)
        verdict = verdict_match.group(1) if verdict_match else "unknown"

        rules[rule_id] = {"title": title, "verdict": verdict, "body": body}
    return rules


# ── Scenarios parsing ─────────────────────────────────────────────────────────

# Matches: "## Scenario 1 — Service class with cron" or "## Scenario 2a — ..."
SCENARIO_HEADING = re.compile(r"^## Scenario (\d+[a-z]?)\s+—\s+(.+)$", re.MULTILINE)

# Inside a scenario, the prompt is in a blockquote after "**Prompt (verbatim — pass to subagents):**"
PROMPT_BLOCK = re.compile(
    r"\*\*Prompt[^\*]*\*\*\s*\n+(>\s.*?)(?=\n\n\*\*Rules|\n\n## |\Z)",
    re.DOTALL,
)

# Rules-exercised section
RULES_BLOCK = re.compile(
    r"\*\*Rules this scenario exercises[^\*]*\*\*\s*\n+(.*?)(?=\n\n\*\*|\n## |\Z)",
    re.DOTALL,
)

# Rule IDs inside the rules block: "A1", "C3", "EX10", etc.
# Allow lowercase suffix (e.g. "2a" doesn't apply here but be safe)
RULE_ID = re.compile(r"\b([A-EX]+\d+[a-z]?)\b")


def parse_scenarios(text: str) -> list[dict]:
    """Returns [{id, title, prompt, rule_ids}, ...]."""
    scenarios: list[dict] = []
    matches = list(SCENARIO_HEADING.finditer(text))
    for i, m in enumerate(matches):
        scenario_id = m.group(1)
        # Skip non-scenario headings like "## Scenario design principles" / "## Scenario count"
        # We only want headings whose group(1) is a number/number+letter.
        # The regex already requires \d+ so design-principles won't match — good.

        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]

        prompt_match = PROMPT_BLOCK.search(body)
        if not prompt_match:
            print(f"WARN: scenario {scenario_id} has no prompt block, skipping", file=sys.stderr)
            continue
        prompt_raw = prompt_match.group(1).strip()
        # Strip the leading "> " from each blockquote line
        prompt = "\n".join(
            line[2:] if line.startswith("> ") else line[1:] if line.startswith(">") else line
            for line in prompt_raw.split("\n")
        ).strip()

        rules_match = RULES_BLOCK.search(body)
        rule_ids: list[str] = []
        if rules_match:
            # Dedupe while preserving order
            seen = set()
            for rid in RULE_ID.findall(rules_match.group(1)):
                if rid not in seen:
                    seen.add(rid)
                    rule_ids.append(rid)

        scenarios.append({
            "id": scenario_id,
            "title": title,
            "prompt": prompt,
            "rule_ids": rule_ids,
        })
    return scenarios


# ── Prompt builders ───────────────────────────────────────────────────────────

BASELINE_PROMPT_TMPL = """\
You are a senior WordPress / PHP developer being asked to write code for a Bedrock-based WordPress site running PHP 8.3. You write modern PHP — typed, readonly where appropriate, WP_Error for failures.

**CRITICAL FOR THIS EXPERIMENT (this is the baseline leg of an A/B test):**
- Do NOT invoke the Skill tool for any skill — not just harness skills, ANY skill except the ones the system loads automatically.
- Do NOT read any file under ~/.claude/plugins/ (skills, hooks, configs — none of it).
- Do NOT read any file under ~/Sites/stride/ — that reference codebase is the source of truth for "NTDST-correct code" and reading it would leak the patterns we're testing whether you produce.
- Work from your own PHP/WP knowledge only. Do not announce what you're not loading or reading — just answer the task.

You CAN read the prompt's stated requirements carefully. You CAN use general knowledge about WordPress, PHP 8.3, LearnDash, Composer/Bedrock, WP-CLI, REST API, $wpdb, etc. You CANNOT inspect the project's existing code or skills to copy patterns from.

---

{prompt}

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
"""

SKILL_ON_PROMPT_TMPL = """\
You are a senior WordPress / PHP developer working on the Stride LMS project (Bedrock, PHP 8.3, mu-plugins/stride-core/).

You may use the Skill tool freely. Skills relevant to this task (likely candidates: wp-security, wp-database, ntdst-architecture, ntdst-data, ntdst-patterns) may auto-trigger; you can also invoke them explicitly if you judge them relevant. You CAN read ~/Sites/stride/ for existing patterns — this is your normal working environment.

This is the skill-on leg of an A/B test against an unprimed baseline. Don't preemptively over-engineer or over-cite skills — answer the task as you naturally would with the harness loaded.

---

{prompt}

---

Write the requested code. Use PHP code blocks. Briefly note where each file should live in the project tree. Keep total response under 600 words including code.
"""

JUDGE_PROMPT_TMPL = """\
You are scoring an eval. Two PHP code outputs were produced by different agents for the same prompt — one baseline (no harness skills), one with the netdust-wp/netdust-core harness skills available. Your job: for each rule in the list, judge which outputs covered it.

**The prompt that was given to both agents:**

---
{scenario_prompt}
---

**Output A (baseline — no harness skills loaded):**

---
{baseline_output}
---

**Output B (skill-on — harness skills available):**

---
{skill_on_output}
---

**Rules to score** (each from `~/Sites/netdust-wp-manager/tasks/eval-rubric.md` — read that file for full definitions; brief reminders below):

{rule_list}

---

**Scoring protocol:**

For EACH rule above, output ONE line in this exact format (machine-parsed):

```
RULE_ID: <coverage> | <evidence>
```

Where `<coverage>` is one of:
- `both` — both outputs satisfy the rule
- `baseline_only` — only baseline satisfies
- `skill_only` — only skill-on satisfies
- `neither` — neither satisfies (rule not applicable OR both failed)
- `na` — rule is not exercisable by this scenario (the rule list may be over-inclusive; flag and skip)

And `<evidence>` is ≤25 words explaining your judgment, citing concrete code patterns ("uses `$wpdb->prepare` with %d placeholder", "missing nonce check", "registers via add_filter not WP_CLI::add_command", etc.).

**Be strict.** "The agent could have done X" is not coverage. The code on the page either does X or it doesn't. Code that says `// TODO: add nonce check` is not coverage.

**Be honest about NEGATIVE rules.** Some rule notes say "anti-pattern to detect" — if the output produces the anti-pattern, that's a fail (not coverage). E.g., if D4 says "dry-run is the default" and the output uses `--dry-run` opt-in (writes by default), that's `neither`, not `both`.

After scoring all rules, end with EXACTLY this one-line summary (don't change the format — it gets parsed):

```
SUMMARY: scenario_id={scenario_id} baseline_covered=N skill_covered=N skill_delta=N
```

Where N is the count, and `skill_delta` = number of rules where coverage is `skill_only` (NOT `baseline_only` and NOT `both`).

Don't add prose before or after the scoring lines and summary. The output will be parsed by a script.
"""


def build_baseline_prompt(scenario: dict) -> str:
    return BASELINE_PROMPT_TMPL.format(prompt=scenario["prompt"])


def build_skill_on_prompt(scenario: dict) -> str:
    return SKILL_ON_PROMPT_TMPL.format(prompt=scenario["prompt"])


def build_judge_prompt(
    scenario: dict,
    rules: dict[str, dict],
    baseline_output: str,
    skill_on_output: str,
) -> str:
    rule_list_lines = []
    for rid in scenario["rule_ids"]:
        if rid in rules:
            rule_list_lines.append(f"- **{rid}** ({rules[rid]['verdict']}): {rules[rid]['title']}")
        else:
            rule_list_lines.append(f"- **{rid}** (unknown — not found in rubric)")
    return JUDGE_PROMPT_TMPL.format(
        scenario_prompt=scenario["prompt"],
        baseline_output=baseline_output,
        skill_on_output=skill_on_output,
        rule_list="\n".join(rule_list_lines),
        scenario_id=scenario["id"],
    )


# ── Judge output parsing ──────────────────────────────────────────────────────

# Matches: "A1: both | uses readonly typed constructor properties"
SCORE_LINE = re.compile(
    r"^([A-EX]+\d+[a-z]?):\s*(both|baseline_only|skill_only|neither|na)\s*\|\s*(.+)$",
    re.MULTILINE,
)

SUMMARY_LINE = re.compile(
    r"^SUMMARY:\s*scenario_id=(\S+)\s+baseline_covered=(\d+)\s+skill_covered=(\d+)\s+skill_delta=(-?\d+)",
    re.MULTILINE,
)


def parse_judge_output(text: str) -> dict:
    """Returns {scores: [(rule_id, coverage, evidence), ...], summary: {...}}."""
    scores = []
    for m in SCORE_LINE.finditer(text):
        scores.append((m.group(1), m.group(2), m.group(3).strip()))

    summary = None
    sm = SUMMARY_LINE.search(text)
    if sm:
        summary = {
            "scenario_id": sm.group(1),
            "baseline_covered": int(sm.group(2)),
            "skill_covered": int(sm.group(3)),
            "skill_delta": int(sm.group(4)),
        }
    return {"scores": scores, "summary": summary}


# ── Modes ─────────────────────────────────────────────────────────────────────

def cmd_prepare() -> int:
    """Read rubric + scenarios, write all 24 prompt files."""
    if not RUBRIC_PATH.exists():
        print(f"ERROR: rubric not found at {RUBRIC_PATH}", file=sys.stderr)
        return 2
    if not SCENARIOS_PATH.exists():
        print(f"ERROR: scenarios not found at {SCENARIOS_PATH}", file=sys.stderr)
        return 2

    rubric = parse_rubric(RUBRIC_PATH.read_text())
    scenarios = parse_scenarios(SCENARIOS_PATH.read_text())

    print(f"Parsed {len(rubric)} rules, {len(scenarios)} scenarios.")

    PROMPTS_DIR.mkdir(exist_ok=True)
    # Clean stale prompts so re-runs don't leave outdated ones around
    for old in PROMPTS_DIR.glob("*.md"):
        old.unlink()

    written = 0
    for s in scenarios:
        sid = s["id"]
        # baseline + skill-on prompts can be written now
        (PROMPTS_DIR / f"scenario-{sid}-baseline.md").write_text(build_baseline_prompt(s))
        (PROMPTS_DIR / f"scenario-{sid}-skill-on.md").write_text(build_skill_on_prompt(s))
        written += 2

        # Judge prompt needs the two outputs — write a TEMPLATE that the
        # orchestrator can fill in (the rule list is fixed, the outputs aren't)
        # Use --score to regenerate the full judge prompt after outputs land.
        rule_list_lines = []
        for rid in s["rule_ids"]:
            if rid in rubric:
                rule_list_lines.append(f"- **{rid}** ({rubric[rid]['verdict']}): {rubric[rid]['title']}")
            else:
                rule_list_lines.append(f"- **{rid}** (unknown — not in rubric)")

        judge_template = (
            f"# JUDGE PROMPT TEMPLATE — scenario {sid}\n\n"
            f"# This file is a TEMPLATE. Before dispatching the judge subagent:\n"
            f"# 1. Ensure outputs/scenario-{sid}-baseline.md and outputs/scenario-{sid}-skill-on.md exist.\n"
            f"# 2. Run: python3 run-eval.py --build-judge {sid}\n"
            f"#    This writes prompts/scenario-{sid}-judge.md with both outputs inlined.\n\n"
            f"# Scenario prompt:\n"
            f"{s['prompt']}\n\n"
            f"# Rules to score:\n"
            + "\n".join(rule_list_lines)
            + "\n"
        )
        (PROMPTS_DIR / f"scenario-{sid}-judge.template.md").write_text(judge_template)
        written += 1

    print(f"Wrote {written} files to {PROMPTS_DIR}/")
    print()
    print("Next steps:")
    print(f"  1. For each scenario, dispatch the Agent tool with the contents of prompts/scenario-<id>-baseline.md")
    print(f"     and prompts/scenario-<id>-skill-on.md. Paste each output into outputs/scenario-<id>-baseline.md")
    print(f"     and outputs/scenario-<id>-skill-on.md respectively.")
    print(f"  2. Run: python3 {Path(__file__).name} --build-judge <id>  (per scenario, after both outputs land)")
    print(f"  3. Dispatch the judge prompt; paste output to outputs/scenario-<id>-judge.md")
    print(f"  4. When all 8 judges done, run: python3 {Path(__file__).name} --score")
    return 0


def cmd_build_judge(scenario_id: str) -> int:
    """Inline the baseline + skill-on outputs into a full judge prompt."""
    scenarios = parse_scenarios(SCENARIOS_PATH.read_text())
    rubric = parse_rubric(RUBRIC_PATH.read_text())

    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
    if not scenario:
        print(f"ERROR: scenario '{scenario_id}' not found", file=sys.stderr)
        return 2

    baseline_path = OUTPUTS_DIR / f"scenario-{scenario_id}-baseline.md"
    skill_on_path = OUTPUTS_DIR / f"scenario-{scenario_id}-skill-on.md"
    if not baseline_path.exists():
        print(f"ERROR: missing {baseline_path}", file=sys.stderr)
        return 2
    if not skill_on_path.exists():
        print(f"ERROR: missing {skill_on_path}", file=sys.stderr)
        return 2

    prompt = build_judge_prompt(
        scenario,
        rubric,
        baseline_path.read_text(),
        skill_on_path.read_text(),
    )
    out_path = PROMPTS_DIR / f"scenario-{scenario_id}-judge.md"
    out_path.write_text(prompt)
    print(f"Wrote {out_path}")
    print(f"  Scenario: {scenario['title']}")
    print(f"  Rules: {len(scenario['rule_ids'])}")
    print(f"  Baseline output: {len(baseline_path.read_text())} chars")
    print(f"  Skill-on output: {len(skill_on_path.read_text())} chars")
    return 0


def cmd_score() -> int:
    """Read every outputs/scenario-*-judge.md, parse scoring, write eval-log.md."""
    scenarios = parse_scenarios(SCENARIOS_PATH.read_text())
    rubric = parse_rubric(RUBRIC_PATH.read_text())

    results: list[dict] = []
    for s in scenarios:
        sid = s["id"]
        judge_path = OUTPUTS_DIR / f"scenario-{sid}-judge.md"
        if not judge_path.exists():
            print(f"WARN: missing {judge_path} — scenario {sid} won't be scored", file=sys.stderr)
            continue
        parsed = parse_judge_output(judge_path.read_text())
        results.append({
            "scenario": s,
            "parsed": parsed,
        })

    if not results:
        print("ERROR: no judge outputs found. Nothing to score.", file=sys.stderr)
        return 2

    log = render_log(results, rubric)

    # Append (don't overwrite) so historical runs are preserved
    if LOG_PATH.exists():
        existing = LOG_PATH.read_text()
        LOG_PATH.write_text(existing + "\n\n" + log)
    else:
        LOG_PATH.write_text(log)

    print(f"Wrote log to {LOG_PATH}")

    # Print a summary to stdout
    print()
    print("=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)
    total_baseline = 0
    total_skill = 0
    total_delta = 0
    for r in results:
        s = r["parsed"].get("summary")
        if not s:
            print(f"  scenario {r['scenario']['id']}: NO SUMMARY PARSED (judge output malformed?)")
            continue
        print(f"  scenario {s['scenario_id']:>3}: baseline={s['baseline_covered']:>2}/{len(r['scenario']['rule_ids']):<2}  "
              f"skill={s['skill_covered']:>2}/{len(r['scenario']['rule_ids']):<2}  "
              f"skill_delta={s['skill_delta']:+d}")
        total_baseline += s['baseline_covered']
        total_skill += s['skill_covered']
        total_delta += s['skill_delta']
    print("-" * 60)
    print(f"  totals:       baseline={total_baseline}  skill={total_skill}  skill_delta={total_delta:+d}")
    print()
    print("skill_delta is the headline number: total rules covered by skill-on")
    print("that baseline missed. If it's low across most scenarios, skills aren't")
    print("earning their context cost.")
    return 0


def render_log(results: list[dict], rubric: dict[str, dict]) -> str:
    """Markdown log of all scored scenarios."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# Eval log — {ts}", ""]
    lines.append(f"_Generated by `run-eval.py --score`. Source: `eval-rubric.md` + `eval-scenarios.md` + `outputs/`._")
    lines.append("")

    # Per-scenario tables
    for r in results:
        s = r["scenario"]
        parsed = r["parsed"]
        summary = parsed.get("summary") or {}

        lines.append(f"## Scenario {s['id']} — {s['title']}")
        lines.append("")
        lines.append(f"- **Rules scored:** {len(parsed['scores'])} / {len(s['rule_ids'])} expected")
        if summary:
            lines.append(f"- **Baseline covered:** {summary['baseline_covered']}")
            lines.append(f"- **Skill-on covered:** {summary['skill_covered']}")
            lines.append(f"- **skill_delta:** {summary['skill_delta']:+d}")
        else:
            lines.append("- **WARNING:** no summary line parsed from judge output")
        lines.append("")
        lines.append("| Rule | Verdict | Coverage | Evidence |")
        lines.append("|---|---|---|---|")
        for rid, coverage, evidence in parsed["scores"]:
            verdict = rubric.get(rid, {}).get("verdict", "?")
            # Escape pipes in evidence
            ev = evidence.replace("|", "\\|")
            lines.append(f"| {rid} | {verdict} | {coverage} | {ev} |")
        lines.append("")

    # Cross-scenario aggregate (canonical rules only)
    lines.append("## Aggregate — canonical rules only")
    lines.append("")
    canonical_rule_ids = {rid for rid, r in rubric.items() if r["verdict"] == "canonical"}
    coverage_by_rule: dict[str, list[tuple[str, str]]] = {}  # rule -> [(scenario_id, coverage), ...]
    for r in results:
        for rid, coverage, _ in r["parsed"]["scores"]:
            if rid in canonical_rule_ids and coverage != "na":
                coverage_by_rule.setdefault(rid, []).append((r["scenario"]["id"], coverage))

    if coverage_by_rule:
        lines.append("Rules where skill-on beat baseline in ≥1 scenario:")
        lines.append("")
        skill_wins = []
        for rid, hits in sorted(coverage_by_rule.items()):
            if any(c == "skill_only" for _, c in hits):
                skill_wins.append((rid, hits))
        if skill_wins:
            for rid, hits in skill_wins:
                detail = ", ".join(f"{sid}:{c}" for sid, c in hits)
                lines.append(f"- **{rid}** ({rubric[rid]['title'][:60]}): {detail}")
        else:
            lines.append("_(none — skills did not produce any net-new rule coverage)_")
        lines.append("")

        lines.append("Rules where baseline alone covered (skill-on missed or didn't beat):")
        lines.append("")
        baseline_only_rules = []
        for rid, hits in sorted(coverage_by_rule.items()):
            if any(c == "baseline_only" for _, c in hits):
                baseline_only_rules.append((rid, hits))
        if baseline_only_rules:
            for rid, hits in baseline_only_rules:
                detail = ", ".join(f"{sid}:{c}" for sid, c in hits)
                lines.append(f"- **{rid}** ({rubric[rid]['title'][:60]}): {detail}")
        else:
            lines.append("_(none)_")

    lines.append("")
    lines.append("## Headline question")
    lines.append("")
    lines.append("**Did loading the harness skills change the produced code on Stride-shaped tasks?**")
    lines.append("")
    lines.append("If `skill_delta` totals are high → skills earn their context cost.")
    lines.append("If close to zero → skills are either documenting baseline-default behavior")
    lines.append("OR baseline is already producing NTDST-correct code without them.")
    lines.append("")
    lines.append("Per the harness-improvement-plan, this result drives task 1.7 (read")
    lines.append("results honestly) and the deferred skill-doc-bug fixes from task 1.3.")
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="netdust-core eval helper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true",
                       help="Parse rubric + scenarios, write per-agent prompts to prompts/")
    group.add_argument("--build-judge", metavar="SCENARIO_ID",
                       help="Inline outputs into a judge prompt (after baseline + skill-on land)")
    group.add_argument("--score", action="store_true",
                       help="Read judge outputs from outputs/, write scored eval-log.md")

    args = parser.parse_args()

    if args.prepare:
        return cmd_prepare()
    if args.build_judge:
        return cmd_build_judge(args.build_judge)
    if args.score:
        return cmd_score()
    return 1


if __name__ == "__main__":
    sys.exit(main())
