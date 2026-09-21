# netdust-gates v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `netdust-gates` plugin, v0.1.0: one policy skill that injects Netdust standards into superpowers' spec and plan, two executables that verify (`make gate`, `bin/shakeout-check.py`), and the carried authority hooks.

**Architecture:** A new plugin under `plugins/netdust-gates/`, built almost entirely by carrying and trimming pieces of `plugins/netdust-agent/` (read-only source) plus one new prose skill with its pack and catalog. Superpowers keeps the loop; nothing here restates it.

**Tech Stack:** Bare `python3` (3.12, stdlib only), bash, Markdown skills/agents/commands, `claude` CLI for the behavioural evals.

**Spec:** `specs/netdust-gates/spec.md` (authority) · handover `specs/netdust-gates/BRIEF.md`

**First working version:** Task 2 — with `claude --plugin-dir plugins/netdust-gates`, a WordPress feature request's plan carries the pack's Global Constraints and the `First working version` / `Simplest design` lines; Task 3's eval case 1 proves it before any hook or checker exists.

**Simplest design:** The simplest design that meets the ask is one skill (policy + pack + catalog) and nothing else — no hooks, no checker, no agents, with `netdust-agent` left to supply the rest. It is not chosen because R7 and R8 name the two parts last week's evidence says did real work (`shakeout-manifest` ×12, `shakeout-credential` ×2, and a guard whose Write/Edit floors never ran live); without them "verify" and "authorize" are prose again, which is the failure this plugin exists to end. Beyond that the plan adds no design: every hook, test and check is a carry-and-trim of a 0.28 file, edited only where the spec removes something (upstream floor, herdr/placement block, skill-audit nudge, plan cross-check) or adds the wiring test.

## Global Constraints

- Nothing under `plugins/netdust-agent/`, `plugins/netdust-wp/`, `plugins/netdust-devops/` or `plugins/netdust-core/` is edited. New files only, under `plugins/netdust-gates/`, plus the marketplace entry and `specs/netdust-gates/`.
- Commit by path on `feature/netdust-gates`. No merge, no push, no `git add -A`, no stash. The main checkout's uncommitted `plugins/netdust-wp/skills/ntdst-yootheme/lessons.md` is Stefan's — leave it. `~/Sites/netdust` is not part of this build.
- Plugin version `0.1.0` in `plugin.json` and the marketplace entry.
- Registered for `Bash|Write|Edit|NotebookEdit`, with a test that fails when `hooks/hooks.json` does not cover a tool the guard handles (spec R7).
- Not carried, and not to be re-added (spec "Not in v0"): `gate-check.py`, lanes, tiers, clusters, placement, the model ladder, `/loop`, the loop ledger, `implementer` / `test-author` / `reviewer` agents, `compounding`, `convergence`, `run-score`, `run-trace`, `verify-budget`, `subagent-stop.py`, `loop-gate.py`, the upstream-invocation floor.
- The growth rule (spec R9): an incident lands as a gate tier in the project, a line in a constraints pack or the edge-class catalog, or an eval case — never a new plan field or a check on plan grammar.
- The policy skill stays under 150 lines; it invokes superpowers and never restates it. Skills are contracts, not books.
- Bare `python3`, stdlib only. Hooks fail OPEN: every path exits 0 unless a deny/ask decision is printed.
- Tests: each `tests/test_*.py` exposes `run() -> list[tuple[bool, str]]`; the suite is `bash plugins/netdust-gates/tests/run.sh` (optionally one file: `… run.sh test_<name>.py`).
- Comments only for a non-obvious why; keep carried comments where they explain one. No `!` negation in shell (it silently kills `&&` chains in Stefan's terminal) — use `test`/`grep -c`, and check files on disk after writing.
- No `.env` reads. Never `git stash`.

## Review Focus

Most likely first. Each line is pinned to a test in the owning task.

1. **A manifest that is missing, empty, or has no rows passing vacuously.** v0 has no plan table to say what is owed, so the checker must fail all three. → Task 6, tests "no manifest", "empty manifest", "header-only table".
2. **A `browser` row whose evidence escapes or fakes the screenshot** — `shakeout/../../x.png`, a file under 1 KB, a non-PNG, a non-`http` URL. → Task 6, tests "traversal", "too small", "not a PNG", "no http url".
3. **A stale `Ruling:` excusing a row.** Only the human's `Accepted-by-human:` does (spec R5), and never a credential. → Task 6, tests "old Ruling: token fails", "accepted with a credential is reported, never echoed".
4. **`NotebookEdit` into `vendor/`.** Its payload key is `notebook_path`, not `file_path`, so the vendor floor stayed silent for it. → Task 4, test "NotebookEdit into a vendored package".
5. **A tool the guard handles but `hooks.json` does not match — now, or added later.** The 0.28 bug (`"matcher": "Bash"`). The wiring test derives the tool list from `HANDLED_TOOLS` in the guard and includes a mutation case that reproduces the 0.28 matcher and must report the gap. → Task 4, `test_hooks_wiring.py`.

## Rulings made while planning

Each is a call the spec did not settle; each is cheap to reverse and Stefan can overrule at plan review.

| # | Ruling | Costs if wrong |
|---|---|---|
| 1 | **No plan cross-check in `shakeout-check.py`.** 0.28 read `## Acceptance flows` from its plan grammar; the upstream plan has no such table and R9 forbids adding one. So the checker reads `shakeout.md` alone, requires a valid `Layer` cell per row, and fails on a missing/empty manifest. `shakeout-qa` derives the flow list from the spec's user-facing requirements and `Review Focus`, and prints it in its report. | An agent can under-list flows or label a screen `wire` to dodge the PNG. The human's screenshot yield is the backstop. |
| 2 | **Not carried: the `architecture-invariants` skill.** R6 only *consumes* `ARCHITECTURE-INVARIANTS.md` (the policy skill turns touched convergence points into `Review Focus` lines; `invariant-auditor` reads the doc). Authoring the doc stays with 0.28. | A project with no invariants doc cannot author one from this plugin. netdust.be already has one. |
| 3 | **`threat-modeling` IS carried** (trimmed, ~25 lines) as `netdust-gates:threat-modeling`: R2 and R6 both presuppose a plan `## Threat model`. | None material. |
| 4 | **`memory/GLOBAL.md` carried, trimmed** to Stack, Cross-project hard rules, SSH aliases. Dropped: harness preferences (spec location moves into the policy skill), stale priorities, harness self-meta. | The pilot session loses the "Active priorities" list; it belongs to fleet memory (layer B) anyway. |
| 5 | **`NotebookEdit` made real:** the vendor floor also reads `notebook_path`. R7 registers the matcher for it; without this the registration would be decorative. | One line in the guard. |
| 6 | **Evals run in a scratch project that mirrors the pilot** (`netdust-agent` disabled, project `CLAUDE.md` naming `netdust-gates:policy` first) using `claude -p --plugin-dir`. `--bare` is unusable (needs an API key, not OAuth). Assertions are regexes on the plan/reply/files, not an LLM judge. | The evals are stochastic and cost a few minutes and tokens each; a red case is a signal to tighten the skill, not proof of a regression. |
| 7 | **Plan file stays uncommitted** until Stefan has reviewed it. | None. |

## For Stefan at review

- **`netdust-wp:wp-plan-requirements` overlaps the pack.** In the pilot `netdust-wp` stays enabled, and that skill's description also fires on "write a plan for a WP feature". Two injectors could both add sections. Spec R4 says the pack lives here for the pilot and moves to `netdust-wp` if it holds; I have not touched `netdust-wp` (boundary). Decide before Friday whether the pilot's `.claude/settings.json` should also disable that one skill, or accept the overlap.
- **Execution mode.** I recommend **Native** — see the handoff message.

---

### Task 1: Plugin skeleton, test runner, manifest test

**Files:**
- Create: `plugins/netdust-gates/.claude-plugin/plugin.json`
- Create: `plugins/netdust-gates/CLAUDE.md`
- Create: `plugins/netdust-gates/tests/run.sh` (carried)
- Create: `plugins/netdust-gates/tests/test_plugin_manifest.py`
- Modify: `.claude-plugin/marketplace.json` (add one entry after `netdust-agent`)

**Interfaces:**
- Produces: the runner protocol every later task's tests follow — `tests/test_*.py` exposing `run() -> list[tuple[bool, str]]`, run by `bash plugins/netdust-gates/tests/run.sh [test_file.py]`.
- Produces: `plugin.json` version `0.1.0`, matched by the marketplace entry.

- [ ] **Step 1: Carry the runner, add the one-file filter**

```bash
mkdir -p plugins/netdust-gates/.claude-plugin plugins/netdust-gates/tests
cp plugins/netdust-agent/tests/run.sh plugins/netdust-gates/tests/run.sh
sed -i 's/netdust-core test runner/netdust-gates test runner/; s/^for test_file in test_\*\.py; do/for test_file in ${1:-test_*.py}; do/' plugins/netdust-gates/tests/run.sh
grep -n "netdust-gates test runner\|for test_file" plugins/netdust-gates/tests/run.sh
```
Expected: two lines — the renamed header comment and `for test_file in ${1:-test_*.py}; do`.

- [ ] **Step 2: Write the failing manifest test**

`plugins/netdust-gates/tests/test_plugin_manifest.py`:

```python
"""test_plugin_manifest.py — the plugin is installable: manifest, marketplace entry, growth rule."""
import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent


def _entry():
    catalog = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    return next((p for p in catalog["plugins"] if p["name"] == "netdust-gates"), None)


def run() -> list[tuple[bool, str]]:
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    entry = _entry()
    claude_md = (PLUGIN / "CLAUDE.md").read_text()
    return [
        (manifest["name"] == "netdust-gates" and manifest["version"] == "0.1.0",
         f"plugin.json names netdust-gates 0.1.0 (got {manifest['name']} {manifest['version']})"),
        (entry is not None and entry["source"] == "./plugins/netdust-gates"
         and (REPO / entry["source"]).is_dir() and entry["version"] == manifest["version"],
         "marketplace.json carries a netdust-gates entry whose source exists and whose version matches plugin.json"),
        ("Never as a new plan field" in claude_md and "gate tier" in claude_md and "eval case" in claude_md,
         "CLAUDE.md states the growth rule (R9)"),
        ("netdust-agent" in claude_md and "never both" in claude_md.lower(),
         "CLAUDE.md says never enable netdust-agent beside it"),
    ]
```

- [ ] **Step 3: Run it to verify it fails**

Run: `bash plugins/netdust-gates/tests/run.sh test_plugin_manifest.py`
Expected: `FileNotFoundError … plugin.json`, `Modules failed: 1`.

- [ ] **Step 4: Write `plugin.json`, `CLAUDE.md` and the marketplace entry**

`plugins/netdust-gates/.claude-plugin/plugin.json`:

```json
{
  "name": "netdust-gates",
  "version": "0.1.0",
  "description": "Netdust's software-delivery policy over superpowers: standards injected into the spec and plan, verification by executables (make gate, the shake-out manifest check), authority hooks. Pilot on netdust.be; replaces netdust-agent there and never runs beside it.",
  "author": {
    "name": "Stefan Vermeulen",
    "email": "stefan@netdust.be",
    "url": "https://netdust.be"
  },
  "license": "UNLICENSED"
}
```

`plugins/netdust-gates/CLAUDE.md`:

```markdown
# netdust-gates

Stefan's software-delivery policy over superpowers, and nothing else. Superpowers runs the
loop in its own plan format; this plugin does three things:

1. **Inject** — Netdust standards go into the slots superpowers already carries to every
   implementer and reviewer (`Global Constraints`, `Review Focus`): `skills/policy/`.
2. **Verify** — by executables: the project's `make gate`, and `bin/shakeout-check.py`.
3. **Authorize** — hooks for what only Stefan can grant: `hooks/`.

The spec is `specs/netdust-gates/spec.md`; it is the authority.

## The growth rule

An incident lands as **a gate tier in the project**, **a line in a constraints pack or the
edge-class catalog**, or **an eval case**. Never as a new plan field or a new check on plan
grammar. netdust-agent went 0.18 → 0.28 in six weeks by doing the opposite.

## Boundaries

- Enable this or `netdust-agent` in a project, never both — both would fire their hooks.
- Not here, and not to be re-added: gate-check, lanes, tiers, clusters, placement, the model
  ladder, /loop, implementer / test-author / reviewer agents, compounding, convergence,
  run-score / run-trace / verify-budget.
- The policy skill stays under 150 lines; past that it is restating superpowers.

## Tests

`bash tests/run.sh` (all) · `bash tests/run.sh test_<name>.py` (one). Each `tests/test_*.py`
exposes `run()`. `python3 evals/run-evals.py` runs the three behavioural cases; it needs the
`claude` CLI and is not part of `run.sh`.
```

Marketplace: with the Edit tool, in `.claude-plugin/marketplace.json` replace

```
      "version": "0.28.0",
      "strict": false
    },
```

with the same lines followed by:

```
    {
      "name": "netdust-gates",
      "source": "./plugins/netdust-gates",
      "description": "0.1.0: Netdust's software-delivery policy over superpowers — the policy skill injects standards into the spec and plan (Global Constraints, Review Focus, the WordPress constraints pack), bin/shakeout-check.py verifies the shake-out manifest, and the carried hooks authorize (flow floor, vendored-package floor, destructive-command ask tier, memory injection). Pilot on netdust.be; replaces netdust-agent there, never runs beside it.",
      "version": "0.1.0",
      "strict": false
    },
```

- [ ] **Step 5: Run it to verify it passes; validate the catalog**

```bash
bash plugins/netdust-gates/tests/run.sh test_plugin_manifest.py
python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('catalog ok')"
```
Expected: 4 `pass` lines, `All harness tests passed.`, `catalog ok`.

- [ ] **Step 6: Commit**

```bash
git check-ignore -q plugins/netdust-gates/tests/__pycache__ && echo ignored || echo "NOT ignored: never add __pycache__"
git add plugins/netdust-gates/.claude-plugin/plugin.json plugins/netdust-gates/CLAUDE.md plugins/netdust-gates/tests/run.sh plugins/netdust-gates/tests/test_plugin_manifest.py .claude-plugin/marketplace.json
git commit -m "feat(gates): plugin skeleton, test runner, marketplace entry, growth rule" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: The policy skill, WordPress pack, edge-class catalog, threat-modeling

**Files:**
- Create: `plugins/netdust-gates/skills/policy/SKILL.md`
- Create: `plugins/netdust-gates/skills/policy/wordpress.md`
- Create: `plugins/netdust-gates/skills/policy/edge-classes.md`
- Create: `plugins/netdust-gates/skills/threat-modeling/SKILL.md`
- Test: `plugins/netdust-gates/tests/test_policy_skill.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: skill names `netdust-gates:policy`, `netdust-gates:threat-modeling`; the pack path `skills/policy/wordpress.md`; the catalog `skills/policy/edge-classes.md`. Token contract later tasks rely on: `Accepted-by-human:`, `First working version`, `Simplest design`, `Review Focus`, `Global Constraints`, `shakeout-check.py`.

- [ ] **Step 1: Write the failing shape test**

`plugins/netdust-gates/tests/test_policy_skill.py`:

```python
"""test_policy_skill.py — pins the policy skill's shape: it invokes upstream, names each
Netdust addition once, stays a contract (<150 lines), and the pack cites, never restates."""
import re
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
BANNED_GRAMMAR = ("gate-check", "tasks.md", "Lane:", "Cluster", "Stakes:", "Test-author")


def _has_all(text: str, needles: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [n for n in needles if n not in text]
    return not missing, missing


def run() -> list[tuple[bool, str]]:
    policy = (SKILLS / "policy" / "SKILL.md").read_text()
    pack = (SKILLS / "policy" / "wordpress.md").read_text()
    edges = (SKILLS / "policy" / "edge-classes.md").read_text()
    threat = (SKILLS / "threat-modeling" / "SKILL.md").read_text()
    frontmatter = re.match(r"---\nname: policy\ndescription: .+\n---\n", policy)

    ok_up, miss_up = _has_all(policy, ("superpowers:brainstorming", "superpowers:writing-plans",
                                       "superpowers:finishing-a-development-branch"))
    ok_tok, miss_tok = _has_all(policy, (
        "Global Constraints", "Review Focus", "First working version", "Simplest design",
        "Source:", "Accepted-by-human:", "Ruling:", "make gate", "shakeout-check.py",
        "security-sentinel", "invariant-auditor", "wordpress.md", "edge-classes.md",
        "netdust-gates:threat-modeling"))
    ok_pack, miss_pack = _has_all(pack, (
        "netdust-wp:ntdst-framework", "netdust-wp:ntdst-patterns", "netdust-wp:wp-security",
        "netdust-wp:wp-testing", "netdust-devops:devops", "make gate", "Brain Monkey",
        "wp-phpunit", "Playwright", "four pillars"))
    ok_edge, miss_edge = _has_all(edges, (
        "Empty", "Denied actor", "re-entry", "Concurrent", "Boundary", "Mid-flow", "Delivery seam"))
    ok_thr, miss_thr = _has_all(threat, ("Assets", "Attacks", "Mitigations", "Deferrals"))
    banned = [b for text in (policy, pack, edges, threat) for b in BANNED_GRAMMAR if b in text]

    return [
        (frontmatter is not None, "policy: frontmatter is `name: policy` + one-line description"),
        (len(policy.splitlines()) < 150, f"policy: under 150 lines (got {len(policy.splitlines())})"),
        (ok_up, f"policy: invokes the upstream skills (missing {miss_up})"),
        (ok_tok, f"policy: names each Netdust addition once (missing {miss_tok})"),
        (ok_pack, f"pack: cites the owning skills and runners (missing {miss_pack})"),
        (len(pack.splitlines()) <= 60 and "esc_html" not in pack and "sanitize_text_field" not in pack,
         "pack: short, and restates no wp-security function table"),
        (ok_edge, f"catalog: the edge classes are present (missing {miss_edge})"),
        (ok_thr, f"threat-modeling: the four lists are named (missing {miss_thr})"),
        (not banned, f"no 0.28 plan grammar anywhere in the skills (found {sorted(set(banned))})"),
    ]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash plugins/netdust-gates/tests/run.sh test_policy_skill.py`
Expected: `FileNotFoundError … skills/policy/SKILL.md`, `Modules failed: 1`.

- [ ] **Step 3: Write `skills/threat-modeling/SKILL.md`**

```markdown
---
name: threat-modeling
description: Use when a plan or a diff touches user-controlled URLs, auth/session/token/capability surfaces, untrusted parsing (uploads, payloads, frontmatter, AI tool-call args), stored credentials, multi-tenancy or cross-actor visibility, or outbound requests to user-supplied addresses. Produces the plan's `## Threat model` — assets, attacks, mitigations, deferrals — which becomes its Review Focus lines and the security review's target. Invoked by netdust-gates:policy.
---

# Threat modeling — before the tasks

Produce a `## Threat model` section in the plan BEFORE task breakdown — never retrofitted
after a review finds the hole (`drop-workspace-retrofit`: 2 review rounds and 11 findings,
against 1 round and 3–4 for the phases that modelled first).

**Fires when the work touches:** user-controlled URLs (webhooks, provider URLs, OAuth
redirects), auth/session/token/capability surfaces, untrusted parsing, stored credentials,
multi-tenancy or cross-actor visibility, outbound requests to user-supplied addresses. A
change to such a surface runs this on the DIFF, even for a one-liner (`class-d-gap`).

**The section's shape** — four short lists, concrete over complete:

1. **Assets** — what an attacker would want (tokens, PII, private content, write access).
2. **Attacks** — numbered, per surface: `1. **<attack>** → **<mitigation>**`. Name the actor
   and the input path; "someone bad does something" is not an attack.
3. **Mitigations** — each names WHERE it lives (the function, gate or check), so the review
   verifies a named list instead of hunting.
4. **Deferrals** — what is explicitly NOT defended, and why that is acceptable.

A property statement ("keys are encrypted") is not a threat model — it is a claim to
interrogate. On WordPress the four pillars (validate / sanitize / escape / authorize) apply
per data flow; `netdust-wp:wp-security` owns them.

Every mitigation becomes a `Review Focus` line pinned to a test, and the denial — the actor
who is refused — is asserted, not only the allowed path (`traverse-clause`: every route had a
guard, no test asserted the denial, cross-tenant reads shipped green).
```

- [ ] **Step 4: Write `skills/policy/edge-classes.md`**

```markdown
# Edge classes — where Review Focus lines come from

Green suites shipped every one of these. For a feature, name the classes it can actually
meet, most likely first, and pin each to a test in the task that owns the code. Omit a class
only with a written reason. (Incidents: Folio, 2026.)

1. **Empty / zero** — no data, blank input, first run, a prop a data layer toggles to empty
   (`refetch-toggle-blank-editor`: a refetch flipped `doc` to `undefined` and blanked the editor).
2. **Denied actor** — wrong role, second tenant, missing token; drive the denial through the
   whole chain, not the route function (`route-vs-service-guard`: the service ran a second
   mutation pass the route guard never saw).
3. **Wrong order / re-entry** — back button mid-wizard, refresh mid-flow, an action before its
   precondition, a second mount.
4. **Concurrent / double** — double-click submit, two tabs, racing requests
   (`double-submit-a11y-collision`).
5. **Boundary** — max length, zero, negative, off-by-one, unicode/emoji, the huge paste.
6. **Mid-flow failure** — network drop, a 500, the dependency down: does it roll back, clean
   up, tell the user (`bun-sqlite-no-rollback`).

Two more, from what green hid:

7. **Delivery seam** — the mail sends, the row writes, the webhook fires. The failure nobody
   sees by looking is the one even a low-stakes feature must drive.
8. **Shape, not behaviour / compiled, not rendered** — a test that asserts what a callable
   reference looks like never calls it (`shape-not-behaviour`); a build that exits 0 and
   changes a hash says nothing about the computed values on the page (`compiled-not-rendered`).
   Invoke it; compare rendered values to the design's own numbers.
```

- [ ] **Step 5: Write `skills/policy/wordpress.md`**

```markdown
# WordPress constraints pack

Read by `netdust-gates:policy` when the project is WordPress. **Global Constraints** is copied
into the plan verbatim; **Plan shape** steers the tasks. Each line points at the skill that
owns the rule — read that skill, do not paraphrase it here.

## Global Constraints (copy verbatim)

- Base: ntdst-core is the framework base and its layering applies to every new class —
  `netdust-wp:ntdst-framework`; where files live — `netdust-wp:ntdst-patterns`.
- Golden path: the plan names the slice this feature is built to (`netdust-wp:ntdst-patterns`
  → `golden-paths/`); every departure from it is named and justified, or `none`.
- Security: every data flow (AJAX action, REST route, form post, shortcode attribute,
  settings save, custom query) states its four pillars — validate, sanitize, escape,
  authorize — as `netdust-wp:wp-security` defines them; a pillar that does not apply is
  written `n/a — <why>`, never omitted.
- Drift: nothing `netdust-wp:ntdst-drift-reviewer` reports — the review checks the diff
  against this list, so a departure is a named deviation or a defect.
- Tests: the close is `make gate`. Unit = Brain Monkey, integration = wp-phpunit through
  DDEV, e2e = Playwright; commands and setup are `netdust-wp:wp-testing`'s.
- Local and ship: DDEV always; the Makefile is the only route to a server
  (`netdust-devops:devops`); anything that must ship names its `deploy.payload` path.

## Plan shape

- Each data flow gets a task whose test drives the **denial** — the unauthorized actor
  refused, the missing nonce rejected — not only the happy path.
- A user-facing WP screen is a `browser` flow for the shake-out; its login recipe is
  `netdust-wp:wp-testing`'s. Name the screen in the plan so `/shakeout` finds it.
- Third-party code (plugins, mu-plugins, WP core) is outside `deploy.payload`: a patched file
  there is declared in `health.markers`, or the next update silently reverts it.
```

- [ ] **Step 6: Write `skills/policy/SKILL.md`**

```markdown
---
name: policy
description: Use FIRST on any code-changing request in a Netdust project — build, fix, tweak, refactor. Wraps superpowers' brainstorm → plan → execute → review loop with Netdust's three additions: standards injected into the spec and plan, verification by executables (`make gate`, the shake-out check), and the stops only the human grants. Not for read-only questions, prose or research.
---

# netdust-gates:policy

Superpowers runs the loop and owns its rules; this skill never restates them. It adds three
things — **inject** (Netdust standards into the artifacts superpowers already carries to every
implementer and reviewer), **verify** (executables, not testimony), **authorize** (what only
Stefan grants). Anything not written here is upstream's rule.

## Where artifacts live

Spec `specs/<feature>/spec.md`, plan `specs/<feature>/plan.md` — the location preference that
`superpowers:brainstorming` and `superpowers:writing-plans` say overrides their
`docs/superpowers/...` defaults.

## Intake

Invoke `superpowers:brainstorming`. Its three paths (spike, bounded, architectural) stand as
defined there. Netdust adds:

- **Security boundary.** A change to a security-boundary file — auth, session, capability or
  permission checks, nonces, input parsing, outbound fetches of user-supplied URLs, stored
  credentials, tenancy — owes a threat model on the diff first, whatever its size
  (`class-d-gap`: a one-line SSRF-guard edit shipped without one). Use
  `netdust-gates:threat-modeling`.
- **Design work is prototype-first.** A page or UI request builds the visible first version,
  then decides the next thing with Stefan looking at it. Nothing here delays that.
- **A small change writes no artifact.** One file, or one declarative edit, with no open
  decision — would a competent human do it in half an hour? — takes the bounded path's chat
  design and the change itself: no spec file, no plan file. On a WordPress project it still
  meets the pack's constraints; it just is not planned in writing.

## The spec

Every requirement carries a `Source:` line: a quote of what Stefan said, or
`invented — approved <date>`. A requirement he has not approved is a question, not a
requirement. When the spec flags a security surface, the plan owes a `## Threat model`, written
with `netdust-gates:threat-modeling` before the tasks.

## The plan

Invoke `superpowers:writing-plans`; it owns the format. Netdust fills its slots:

- **Global Constraints** — on a WordPress project (a `site.yml` with `structure:`, or
  `roots/wordpress` in `composer.json`) copy the constraint lines of `wordpress.md`, beside
  this file, verbatim, then the spec's own. Other stacks: the spec's own until a pack exists.
- **Review Focus** — one line per mitigation in the threat model, per convergence point of an
  `ARCHITECTURE-INVARIANTS.md` the diff touches, and per class in `edge-classes.md` the feature
  can actually meet, most likely first. Each line is pinned to a test in the task that owns the
  code; a line with no test is a wish.
- **First working version** — one line under Architecture: the task that produces the first
  thing Stefan can see or run, ordered first. Tests and scaffolding for something nobody can
  yet see come after it.
- **Simplest design** — one paragraph: the simplest design that would meet the ask, and why
  the plan does or does not use it.

Nothing else is added. A plan field is not how an incident is remembered (see the plugin's
`CLAUDE.md`).

## Execution mode

Stefan chooses at the plan handoff; you recommend by rule. **Native** by default. Recommend
**subagent-driven** when a task encodes a rule this project chose, touches a security-boundary
path, or the plan is long enough to outlive one context. Give the rule that fired, in a sentence.

## Stops

Upstream's four stops stand. Netdust names the ones that occur: the plan approval and the
execution-mode choice; the shake-out screenshot yield (Close, step 2); and every devops verb
that belongs to the operator — `promote`, `unpromote`, `ship`, deploy — which Stefan runs or
confirms by typing. Everything else you decide and ledger as
`Ruling: <what> — <why> — <cost if wrong>`, and list in the final message. A shake-out exception
Stefan accepts is `Accepted-by-human:` in the manifest, never `Ruling:`; only he writes it.

## Close

1. `make gate` exits 0 — the project's own suite (`commands.gate` in `site.yml`). A project with
   no declared gate declares one as the first task of the work; that is not a reason to skip.
2. A user-facing change runs `/shakeout`: `shakeout-qa` drives the flows through the real
   browser or wire, commits them as tests and writes `specs/<feature>/shakeout.md`;
   `bin/shakeout-check.py` exits 0; Stefan sees one screenshot per surface.
3. Superpowers' single whole-branch review on the most capable model, joined by
   `security-sentinel` when the plan carries a `## Threat model` and `invariant-auditor` when
   the project carries `ARCHITECTURE-INVARIANTS.md`.
4. One fix pass, each fix RED→GREEN. No re-review — named checks and the suites close it. Then
   `superpowers:finishing-a-development-branch`.
```

- [ ] **Step 7: Run to verify it passes**

Run: `bash plugins/netdust-gates/tests/run.sh test_policy_skill.py; wc -l plugins/netdust-gates/skills/*/*.md`
Expected: 9 `pass` lines; policy `SKILL.md` well under 150 lines. If the banned-grammar case fails, remove the token it names — do not weaken the test.

- [ ] **Step 8: Commit**

```bash
git add plugins/netdust-gates/skills plugins/netdust-gates/tests/test_policy_skill.py
git commit -m "feat(gates): policy skill, WordPress pack, edge-class catalog, threat-modeling" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 3: The three behavioural evals (spec R10)

**Files:**
- Create: `plugins/netdust-gates/evals/cases.json`
- Create: `plugins/netdust-gates/evals/run-evals.py`
- Test: `plugins/netdust-gates/tests/test_evals_shape.py`

**Interfaces:**
- Consumes: `netdust-gates:policy` (Task 2) and its tokens.
- Produces: `python3 plugins/netdust-gates/evals/run-evals.py [case-id ...]` — exit 0 when every selected case passes. `cases.json` schema: a list of `{id, prompt, files: {relpath: content}, expect: [{where, match}], absent: [glob]}`; `where` is `"plan"` (all `specs/**/plan.md` concatenated), `"reply"`, or a relative file path.

- [ ] **Step 1: Write the failing shape test**

`plugins/netdust-gates/tests/test_evals_shape.py`:

```python
"""test_evals_shape.py — the eval cases are well-formed and the runner parses.
The cases themselves need the `claude` CLI and are run by hand: python3 evals/run-evals.py"""
import json
import re
from pathlib import Path

EVALS = Path(__file__).resolve().parent.parent / "evals"
IDS = ["wp-feature-constraints", "security-surface-review-focus", "small-tweak-no-artifacts"]


def _compiles(cases: list[dict]) -> bool:
    try:
        return all(re.compile(e["match"]) and e["where"] for c in cases for e in c["expect"])
    except (re.error, KeyError):
        return False


def run() -> list[tuple[bool, str]]:
    cases = json.loads((EVALS / "cases.json").read_text())
    try:
        compile((EVALS / "run-evals.py").read_text(), "run-evals.py", "exec")
        parses = True
    except SyntaxError:
        parses = False
    return [
        ([c["id"] for c in cases] == IDS, f"exactly the three R10 cases, in order (got {[c['id'] for c in cases]})"),
        (all({"id", "prompt", "files", "expect", "absent"} <= set(c) for c in cases),
         "every case carries id, prompt, files, expect, absent"),
        (_compiles(cases), "every expect regex compiles and names where it looks"),
        (parses, "run-evals.py parses"),
    ]
```

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/netdust-gates/tests/run.sh test_evals_shape.py`
Expected: `FileNotFoundError … cases.json`.

- [ ] **Step 3: Write `evals/cases.json`**

The three cases share nothing but the shape; the scratch project (`site.yml`, project `CLAUDE.md`, settings) is added by the runner. Write `plugins/netdust-gates/evals/cases.json`:

```json
[
  {
    "id": "wp-feature-constraints",
    "prompt": "specs/event-list/spec.md is approved by Stefan; do not ask questions. Write the implementation plan to specs/event-list/plan.md.",
    "files": {
      "site.yml": "structure:\n  type: bedrock\n  wpcli_path: web/wp\n",
      "composer.json": "{\"require\": {\"roots/wordpress\": \"^6.6\"}}\n",
      "specs/event-list/spec.md": "# Event list — spec\n\n## Requirements\n\n**R1 — Upcoming events page.** A public page `/events` lists published events dated today or later, soonest first.\n*Source: \"a page that lists upcoming events\"*\n\n**R2 — Empty state.** When there are none, the page says so.\n*Source: invented — approved 2026-09-21*\n\n## Security-relevant surfaces\n- [x] None of the above\n"
    },
    "expect": [
      {"where": "plan", "match": "(?s)## Global Constraints.*ntdst-core"},
      {"where": "plan", "match": "(?s)## Global Constraints.*make gate"},
      {"where": "plan", "match": "(?s)## Global Constraints.*(Brain Monkey|wp-phpunit)"},
      {"where": "plan", "match": "First working version"},
      {"where": "plan", "match": "(?i)Simplest design"},
      {"where": "plan", "match": "(?s)## Review Focus"}
    ],
    "absent": []
  },
  {
    "id": "security-surface-review-focus",
    "prompt": "specs/webhooks/spec.md is approved by Stefan; do not ask questions. Write the implementation plan to specs/webhooks/plan.md.",
    "files": {
      "site.yml": "structure:\n  type: bedrock\n  wpcli_path: web/wp\n",
      "composer.json": "{\"require\": {\"roots/wordpress\": \"^6.6\"}}\n",
      "specs/webhooks/spec.md": "# Webhook delivery — spec\n\n## Requirements\n\n**R1 — Callback URL.** An administrator pastes a callback URL in the settings screen; on every new order the server POSTs the order payload to it.\n*Source: \"send new orders to my own endpoint\"*\n\n**R2 — Admin only.** Only administrators can view or change the callback URL.\n*Source: invented — approved 2026-09-21*\n\n## Security-relevant surfaces\n- [x] User-controlled URLs / server-side outbound requests\n- [x] Auth / session / token / capability surfaces\n"
    },
    "expect": [
      {"where": "plan", "match": "(?i)## Threat model"},
      {"where": "plan", "match": "(?is)## Review Focus.*?(ssrf|private (address|range|ip)|loopback|169\\.254|rfc\\s?1918|internal (host|address))"},
      {"where": "plan", "match": "(?is)## Review Focus.*?(capabilit|authoriz|manage_options|nonce)"}
    ],
    "absent": []
  },
  {
    "id": "small-tweak-no-artifacts",
    "prompt": "Change the footer copyright year from 2025 to 2026 in footer.php.",
    "files": {
      "site.yml": "structure:\n  type: bedrock\n  wpcli_path: web/wp\n",
      "composer.json": "{\"require\": {\"roots/wordpress\": \"^6.6\"}}\n",
      "footer.php": "<footer><p>&copy; 2025 Netdust</p></footer>\n"
    },
    "expect": [
      {"where": "footer.php", "match": "2026"}
    ],
    "absent": ["specs/**/spec.md", "specs/**/plan.md", "docs/superpowers/**/*.md"]
  }
]
```

- [ ] **Step 4: Write `evals/run-evals.py`**

```python
#!/usr/bin/env python3
"""run-evals.py — the behavioural cases (spec R10).

    run-evals.py [case-id ...]

Each case runs `claude -p` in a scratch project that mirrors the pilot — netdust-agent
disabled, a project CLAUDE.md naming netdust-gates:policy first — with this plugin loaded,
then checks the plan, the reply and the files it left against the case's regexes. Needs the
`claude` CLI and a network; it is not part of tests/run.sh. Stochastic: a red case is a
signal to tighten the skill, not proof of a regression.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import re

PLUGIN = Path(__file__).resolve().parent.parent
CASES = json.loads((Path(__file__).parent / "cases.json").read_text())
SETTINGS = {"enabledPlugins": {"netdust-agent@netdust-plugins": False}}
PROJECT_CLAUDE_MD = (
    "The first action on code-changing work is the `netdust-gates:policy` skill.\n"
    "Specs and plans live in `specs/<feature>/`.\n")


def _write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _subject(root: Path, reply: str, where: str) -> str:
    if where == "reply":
        return reply
    if where == "plan":
        return "\n".join(p.read_text() for p in sorted(root.glob("specs/**/plan.md")))
    target = root / where
    return target.read_text() if target.is_file() else ""


def run_case(case: dict) -> tuple[bool, list[str]]:
    with tempfile.TemporaryDirectory(prefix="gates-eval-") as tmp:
        root = Path(tmp)
        _write(root, "CLAUDE.md", PROJECT_CLAUDE_MD)
        _write(root, ".claude/settings.json", json.dumps(SETTINGS))
        for rel, content in case["files"].items():
            _write(root, rel, content)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        proc = subprocess.run(
            ["claude", "-p", case["prompt"], "--plugin-dir", str(PLUGIN),
             "--permission-mode", "acceptEdits", "--max-turns", "25"],
            cwd=root, capture_output=True, text=True, timeout=900)
        reply = proc.stdout
        failures = []
        for e in case["expect"]:
            if not re.search(e["match"], _subject(root, reply, e["where"])):
                failures.append(f"missing in {e['where']}: /{e['match']}/")
        for glob in case["absent"]:
            found = [str(p.relative_to(root)) for p in root.glob(glob)]
            if found:
                failures.append(f"must not exist: {glob} (found {found})")
        return not failures, failures


def main(argv: list[str]) -> int:
    chosen = [c for c in CASES if not argv or c["id"] in argv]
    failed = 0
    for case in chosen:
        ok, failures = run_case(case)
        print(f"{'PASS' if ok else 'FAIL'}  {case['id']}")
        for f in failures:
            print(f"      {f}")
        failed += not ok
    print(f"\n{len(chosen) - failed}/{len(chosen)} cases passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run the shape test to verify it passes**

Run: `bash plugins/netdust-gates/tests/run.sh test_evals_shape.py`
Expected: 4 `pass` lines.

- [ ] **Step 6: Run the real evals — the First-working-version proof**

Run: `python3 plugins/netdust-gates/evals/run-evals.py` (a few minutes per case; needs the `claude` CLI).
Expected: `3/3 cases passed`. On a red case: read what the run left (rerun the one case, `python3 … run-evals.py <id>`), tighten the policy skill's wording (never the regex to fit), re-run the shape test and that case. Record the final 3/3 output for the report. If a case cannot go green after two skill edits, stop and report it — do not loosen the assertions.

- [ ] **Step 7: Commit**

```bash
git add plugins/netdust-gates/evals plugins/netdust-gates/tests/test_evals_shape.py plugins/netdust-gates/skills
git commit -m "feat(gates): three behavioural eval cases and their runner (R10)" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: The authority guard, its wiring test, the NotebookEdit fix (spec R7, part 1)

**Files:**
- Create (carried, trimmed): `plugins/netdust-gates/hooks/pretooluse-guard.py`
- Create (carried, trimmed): `plugins/netdust-gates/tests/test_pretooluse_guard.py`
- Create: `plugins/netdust-gates/hooks/hooks.json`
- Create: `plugins/netdust-gates/tests/test_hooks_wiring.py`

**Interfaces:**
- Consumes: the runner protocol (Task 1).
- Produces: `HANDLED_TOOLS = ("Bash", "Write", "Edit", "NotebookEdit")` in the guard, which `main()` dispatches on; `hooks/hooks.json` with a `PreToolUse` group matching `Bash|Write|Edit|NotebookEdit`; `tests/test_hooks_wiring.py` helpers `_hooks_json()`, `_guard()`, `_uncovered(tools, matchers) -> list[str]` (Task 5 extends this file).

- [ ] **Step 1: Carry the guard and its tests; confirm the carried suite is green as-is**

```bash
mkdir -p plugins/netdust-gates/hooks
cp plugins/netdust-agent/hooks/pretooluse-guard.py plugins/netdust-gates/hooks/
cp plugins/netdust-agent/tests/test_pretooluse_guard.py plugins/netdust-gates/tests/
bash plugins/netdust-gates/tests/run.sh test_pretooluse_guard.py | tail -4
```
Expected: `All harness tests passed.` (the carried behaviour, upstream floor included).

- [ ] **Step 2: Trim the upstream-invocation floor out of both files**

Run from the worktree root:

```bash
python3 - <<'PY'
def cut(s, start, end, keep_end=False):
    i = s.index(start)
    j = s.index(end, i) + (len(end) if keep_end else 0)
    return s[:i] + s[j:]

g = "plugins/netdust-gates/hooks/pretooluse-guard.py"
s = open(g).read()
s = cut(s, "# ── The upstream-invocation floor", "# ── The vendored-package floor")
s = cut(s, "def check_upstream_floor(", "# ── The flow floor")
s = s.replace('        if decision is None and tool_name == "Write":\n            decision = check_upstream_floor(hook_input)\n', "")
s = cut(s, "  The ONE deny tier (2026-08-10)", "edits of existing files.\n", keep_end=True)
open(g, "w").write(s)

t = "plugins/netdust-gates/tests/test_pretooluse_guard.py"
s = open(t).read()
s = cut(s, "def _upstream_case(", "# --- scenarios")
s = cut(s, "    # === The upstream-invocation floor", "    # -- the flow floor")
old = ("autonomous/injected case. The one deny tier is the upstream-invocation floor\n"
       "on Write (seam artifacts require their superpowers skill in the transcript),\n"
       "pinned in the cases at the bottom of this file.")
assert old in s
s = s.replace(old, "autonomous/injected case. The deny tier is the flow floor (raw git writes that\nbypass the branch flow), pinned in the cases below.")
open(t, "w").write(s)
PY
grep -c "upstream" plugins/netdust-gates/hooks/pretooluse-guard.py plugins/netdust-gates/tests/test_pretooluse_guard.py
```
Expected: both counts `0`. If either is not, `grep -n upstream` and remove the leftover by hand (a docstring mention is fine to reword; a live reference is not). Then add a docstring sentence to the guard's module docstring in place of the removed paragraph: `The deny tier (2026-09-02): the flow floor — a raw git write that bypasses the branch flow; the correction is agent-side and costs one tool call.` Also reword the Purpose paragraph so it no longer names `SubagentStop` (not carried).

Run: `bash plugins/netdust-gates/tests/run.sh test_pretooluse_guard.py | tail -3` → `All harness tests passed.`

- [ ] **Step 3: Write the failing tests (Review Focus 4 and 5)**

(a) In `test_pretooluse_guard.py`, make `_vendor_case` send the right payload key — replace the payload line

```python
        payload = {"tool_name": tool, "tool_input": {"file_path": str(target)}, "cwd": tmp}
```

with

```python
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        payload = {"tool_name": tool, "tool_input": {key: str(target)}, "cwd": tmp}
```

and add, after the `Edit in node_modules` case in `run()`:

```python
    r.append(_vendor_case("NotebookEdit into a vendored package (payload key is notebook_path)",
                          "vendor/other/lib/n.ipynb", "ask", tool="NotebookEdit"))
    r.append(_vendor_case("NotebookEdit outside vendor",
                          "web/app/plugins/mine/n.ipynb", "passthrough", tool="NotebookEdit"))
```

(b) `plugins/netdust-gates/tests/test_hooks_wiring.py`:

```python
"""test_hooks_wiring.py — hooks.json must reach every tool the hook scripts handle.

The 0.28 guard handled Write/Edit but hooks.json matched only `Bash`, so those floors never
ran live while every test — which calls the script over stdin — stayed green. These tests
read the wiring, not just the function."""
import importlib.util
import json
import re
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


def _hooks_json() -> dict:
    return json.loads((HOOKS / "hooks.json").read_text())["hooks"]


def _guard():
    spec = importlib.util.spec_from_file_location("pretooluse_guard", HOOKS / "pretooluse-guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _guard_matchers() -> list[str]:
    return [g["matcher"] for g in _hooks_json().get("PreToolUse", [])
            if any("pretooluse-guard.py" in h["command"] for h in g["hooks"])]


def _uncovered(tools, matchers) -> list[str]:
    return [t for t in tools if not any(re.fullmatch(m, t) for m in matchers)]


def _commands() -> list[str]:
    return [h["command"] for groups in _hooks_json().values() for g in groups for h in g["hooks"]]


def run() -> list[tuple[bool, str]]:
    handled = _guard().HANDLED_TOOLS
    matchers = _guard_matchers()
    reproduced = _uncovered(handled, ["Bash"])
    scripts = [re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)\"?$", c) for c in _commands()]
    return [
        (bool(matchers) and _uncovered(handled, matchers) == [],
         f"hooks.json matcher covers every tool the guard handles (matchers {matchers}, gap {_uncovered(handled, matchers)})"),
        (reproduced == [t for t in handled if t != "Bash"] and len(reproduced) >= 3,
         f"the test bites: the 0.28 matcher `Bash` is reported as missing {reproduced}"),
        (all(m and (HOOKS.parent / m.group(1)).is_file() for m in scripts),
         "every command hooks.json registers names a script that exists"),
    ]
```

- [ ] **Step 4: Run both to verify they fail**

Run: `bash plugins/netdust-gates/tests/run.sh test_pretooluse_guard.py | grep FAIL; bash plugins/netdust-gates/tests/run.sh test_hooks_wiring.py | tail -4`
Expected: the guard suite shows `FAIL … NotebookEdit into a vendored package … (got passthrough)`; the wiring module errors (`HANDLED_TOOLS` / `hooks.json` missing).

- [ ] **Step 5: Implement**

In `hooks/pretooluse-guard.py`:

1. After `LOG_PATH = …` add:

```python
# The tools main() acts on. hooks.json must match every one (tests/test_hooks_wiring.py).
HANDLED_TOOLS = ("Bash", "Write", "Edit", "NotebookEdit")
```

2. In `check_vendor_floor`, replace `file_path = tool_input.get("file_path", "")` with:

```python
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
```

3. In `main()`, replace the block from `tool_name = hook_input.get("tool_name", "")` through the `if tool_name != "Bash": return  # passthrough` lines with:

```python
    tool_name = hook_input.get("tool_name", "")
    if tool_name not in HANDLED_TOOLS:
        return  # passthrough
    if tool_name != "Bash":
        # every path-carrying tool reaches the vendored-package floor
        decision = check_vendor_floor(hook_input)
        if decision is not None:
            print(json.dumps(decision))
        return
```

4. Rename the product in the deny/ask messages and docstring: `sed -i 's/netdust-agent/netdust-gates/g' plugins/netdust-gates/hooks/pretooluse-guard.py`.

`plugins/netdust-gates/hooks/hooks.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/pretooluse-guard.py\"",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: Run to verify both pass**

Run: `bash plugins/netdust-gates/tests/run.sh test_pretooluse_guard.py | tail -3; bash plugins/netdust-gates/tests/run.sh test_hooks_wiring.py`
Expected: `All harness tests passed.` for each; 3 `pass` lines in the wiring module.

- [ ] **Step 7: Commit**

```bash
git add plugins/netdust-gates/hooks plugins/netdust-gates/tests/test_pretooluse_guard.py plugins/netdust-gates/tests/test_hooks_wiring.py
git commit -m "feat(gates): authority guard with wiring test — Write/Edit/NotebookEdit floors now reachable" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 5: Memory hooks — SessionStart injection and Stop-hook tag capture (spec R7, part 2)

**Files:**
- Create (carried, trimmed): `plugins/netdust-gates/hooks/session-start.sh`
- Create (carried): `plugins/netdust-gates/hooks/session-stop.py`
- Create (carried, trimmed): `plugins/netdust-gates/memory/GLOBAL.md`
- Create (carried): `plugins/netdust-gates/tests/hook_test_utils.py`, `test_session_start.py` (trimmed), `test_session_start_budget.py`, `test_stop_hook_add_pathspec.py`, `test_stop_hook_commit_scope.py`, `test_stop_hook_dedup.py`, `test_stop_hook_idempotency.py`, `test_stop_hook_root.py`, `test_tag_scanner.py`
- Modify: `plugins/netdust-gates/hooks/hooks.json`, `plugins/netdust-gates/tests/test_hooks_wiring.py`

**Interfaces:**
- Consumes: `hooks.json` and `test_hooks_wiring.py` helpers `_hooks_json()`, `_commands()` (Task 4).
- Produces: `SessionStart` and `Stop` registered; no `SubagentStop`, no `loop-gate`. `session-start.sh` no longer emits a herdr block, the skill-audit nudge, or any 0.28 harness text.

- [ ] **Step 1: Carry the hooks and their tests; confirm green as-is**

```bash
mkdir -p plugins/netdust-gates/memory
cp plugins/netdust-agent/hooks/session-start.sh plugins/netdust-agent/hooks/session-stop.py plugins/netdust-gates/hooks/
cd plugins/netdust-agent/tests && cp hook_test_utils.py test_session_start.py test_session_start_budget.py test_stop_hook_add_pathspec.py test_stop_hook_commit_scope.py test_stop_hook_dedup.py test_stop_hook_idempotency.py test_stop_hook_root.py test_tag_scanner.py ../../netdust-gates/tests/ && cd ../../..
python3 - <<'PY'
import re
src = open("plugins/netdust-agent/memory/GLOBAL.md").read()
keep = [p for p in re.split(r"(?m)^(?=## )", src)
        if p.startswith(("## Stack", "## Cross-project hard rules", "## SSH aliases"))]
head = ("# Global Memory — Netdust / Stefan\n\nHarness-level facts. Shipped with netdust-gates; "
        "injected into every session by `hooks/session-start.sh`.\n\n")
open("plugins/netdust-gates/memory/GLOBAL.md", "w").write(head + "".join(keep))
PY
grep -c "^## " plugins/netdust-gates/memory/GLOBAL.md
for t in test_session_start.py test_session_start_budget.py test_stop_hook_add_pathspec.py test_stop_hook_commit_scope.py test_stop_hook_dedup.py test_stop_hook_idempotency.py test_stop_hook_root.py test_tag_scanner.py; do bash plugins/netdust-gates/tests/run.sh $t | tail -1; done
```
Expected: `3` sections in GLOBAL.md; eight lines reading `All harness tests passed.`

- [ ] **Step 2: Write the failing tests**

(a) Append to `plugins/netdust-gates/tests/test_session_start.py` a test, and add it to `run()`:

```python
def test_no_agent_harness_text() -> tuple[bool, str]:
    """v0 carries memory injection only: no herdr/placement block, no skill-audit nudge, no
    0.28 harness vocabulary — even under HERDR_ENV=1 in a project with memory scaffolding."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "memory" / "STATE.md").write_text("Sentinel-STATE-X1")
        rc, out, _ = _run_hook(tmp, {"HERDR_ENV": "1", "HERDR_PANE_ID": "w1:p1",
                                     "NETDUST_SKILL_AUDIT_STAMP": str(tmp / "no-such-stamp")})
        stale = [w for w in ("herdr", "PLACEMENT", "skill-audit", "gate-check", "harnessed-development",
                             "spec-authoring", "Harness preferences") if w in out]
        return rc == 0 and "Sentinel-STATE-X1" in out and not stale, \
            f"session-start carries memory only, no 0.28 harness text (rc={rc}, found {stale})"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

(b) Append to `test_hooks_wiring.py`'s `run()` list:

```python
        (set(_hooks_json()) == {"PreToolUse", "SessionStart", "Stop"},
         f"only the carried events are registered — no SubagentStop, no loop gate (got {sorted(_hooks_json())})"),
        (not any("loop-gate" in c or "subagent-stop" in c for c in _commands()),
         "no command names a hook that was not carried"),
        (any("session-start.sh" in c for c in _commands()) and any("session-stop.py" in c for c in _commands()),
         "SessionStart and Stop point at the carried scripts"),
```

- [ ] **Step 3: Run to verify they fail**

Run: `bash plugins/netdust-gates/tests/run.sh test_session_start.py | grep FAIL; bash plugins/netdust-gates/tests/run.sh test_hooks_wiring.py | grep FAIL`
Expected: `FAIL … carries memory only … found ['herdr', 'PLACEMENT', 'skill-audit', …]`; the wiring module fails on the event set and script names.

- [ ] **Step 4: Trim `session-start.sh` and `test_session_start.py`; register the hooks**

```bash
python3 - <<'PY'
def cut(s, start, end):
    i = s.index(start); j = s.index(end, i)
    return s[:i] + s[j:]

h = "plugins/netdust-gates/hooks/session-start.sh"
s = open(h).read()
s = cut(s, "  # ── Periodic /skill-audit nudge", '  OUTPUT+="The goal: a session in 3 months')
s = cut(s, "# ── herdr (harness-inversion FR-19)", "# ── Log every fire")
s = s.replace("session-start.sh — netdust-agent harness", "session-start.sh — netdust-gates")
open(h, "w").write(s)

t = "plugins/netdust-gates/tests/test_session_start.py"
s = open(t).read()
s = cut(s, "def test_skill_audit_nudge_when_stamp_missing", "def test_site_yml_summary_carries_environments")
for gone in ("        test_skill_audit_nudge_when_stamp_missing(),\n",
             "        test_no_skill_audit_nudge_when_stamp_fresh(),\n",
             "        test_herdr_lines(),\n"):
    assert gone in s
    s = s.replace(gone, "")
s = s.replace("        test_log_records_missing_keys(),\n",
              "        test_log_records_missing_keys(),\n        test_no_agent_harness_text(),\n")
open(t, "w").write(s)
PY
sed -i 's/session-stop.py — netdust-agent harness/session-stop.py — netdust-gates/' plugins/netdust-gates/hooks/session-stop.py
```

Because Step 2(a) appended `test_no_agent_harness_text` after the `run()` function, move that definition above `run()` (Python resolves the name at call time, so this is tidiness only — do it so the file reads top-down). Also delete the `NETDUST_SKILL_AUDIT_STAMP` sentence from `_run_hook`'s docstring.

Replace `plugins/netdust-gates/hooks/hooks.json` with the full three-event file:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/pretooluse-guard.py\"",
            "async": false
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh\"",
            "async": false
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/session-stop.py\"",
            "async": false
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Run the whole suite**

Run: `bash plugins/netdust-gates/tests/run.sh | tail -6`
Expected: `Modules failed: 0`, `All harness tests passed.` If `test_session_start.py` still finds `herdr`/`skill-audit`, `grep -n` the hook for the leftover and remove it.

- [ ] **Step 6: Commit**

```bash
git add plugins/netdust-gates/hooks plugins/netdust-gates/memory plugins/netdust-gates/tests
git commit -m "feat(gates): carry SessionStart memory injection and Stop-hook tag capture" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: `bin/shakeout-check.py` — the manifest gate (spec R8)

**Files:**
- Create: `plugins/netdust-gates/bin/shakeout-check.py`
- Test: `plugins/netdust-gates/tests/test_shakeout_check.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `python3 bin/shakeout-check.py <feature dir>` — reads `<dir>/shakeout.md`; exit 0 iff no `fail` finding, 1 on any fail, 2 on bad usage. Output lines `  ✓|✗ [<check>] <detail>` and a final `SHAKEOUT: PASS|FAIL`. Check names: `shakeout-manifest`, `shakeout-credential`, `shakeout-accepted`. Manifest grammar (the table `shakeout-qa` writes, Task 7): `| # | Flow | Layer | Verdict | Evidence |`, `Layer` ∈ `browser|wire|cli`, browser evidence `Browser: <http url> · shakeout/<name>.png`, the human's exception `Accepted-by-human: <reason>`.

- [ ] **Step 1: Write the failing tests**

`plugins/netdust-gates/tests/test_shakeout_check.py` (four-backtick fence because the file contains triple backticks):

````python
"""test_shakeout_check.py — the manifest gate. A pass is a property of a file, never of a
verdict word: browser evidence needs an http URL and a real PNG; the WHOLE file is scanned for
credentials with no override; only the human's `Accepted-by-human:` excuses a row."""
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent.parent / "bin" / "shakeout-check.py"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG = {"shakeout/af-1.png": PNG_MAGIC + bytes(1200)}

HEAD = "# Shake-out — audit screen\n\n| # | Flow | Layer | Verdict | Evidence |\n|---|---|---|---|---|\n"
WIRE_PASS = "| AF-2 | REST list returns the rows | wire | pass | curl -s https://x.ddev.site/wp-json/audit/v1/rows → 200, 3 items |\n"
EVIDENCE = "Browser: https://x.ddev.site/wp/wp-admin/admin.php?page=audit · shakeout/af-1.png"
BROWSER = "| AF-1 | Audit page lists the rows | browser | pass | {} |\n"
DRIVEN = HEAD + BROWSER.format(EVIDENCE) + WIRE_PASS
ACCEPTED = HEAD + BROWSER.format("Accepted-by-human: no browser on this box, driven by Stefan 09-06") + WIRE_PASS


def _drive(manifest, binaries=None, target="feat") -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as root:
        feature = Path(root) / "feat"
        feature.mkdir()
        if manifest is not None:
            (feature / "shakeout.md").write_text(manifest)
        for name, data in (binaries or {}).items():
            path = feature / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        proc = subprocess.run([sys.executable, str(CHECKER), str(Path(root) / target)],
                              capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr


def _case(desc, manifest, binaries=None, *, rc=1, has=(), lacks=(), target="feat"):
    got, out = _drive(manifest, binaries, target)
    ok = got == rc and all(s in out for s in has) and not any(s in out for s in lacks)
    return ok, f"{desc} (rc {got}, expected {rc})"


CREDENTIALS = {
    "curl -u user:pass": DRIVEN.replace("curl -s https://", "curl -u shakeout:s3cr3tPw https://"),
    "user: name:pass": DRIVEN.replace("curl -s https://", "user: shakeout:s3cr3tPw · curl -s https://"),
    "bare pwd=": DRIVEN.replace("curl -s https://", "pwd=s3cr3t, curl -s https://"),
    "bare password:": DRIVEN.replace("curl -s https://", "password: s3cr3t, curl -s https://"),
    "E2E_PASS=": DRIVEN.replace("curl -s https://", "E2E_PASS=abc123, curl -s https://"),
    "--user_pass=": DRIVEN.replace("curl -s https://", "curl --user_pass=x https://"),
    "-u no space": DRIVEN.replace("curl -s https://", "curl -ushakeout:pw https://"),
    "Authorization: Bearer": DRIVEN.replace("curl -s https://", "curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9' https://"),
    "bare Basic": DRIVEN.replace("curl -s https://", "sent Basic c2hha2VvdXQ6czNjcjN0UHc= to https://"),
    "wp-login.php?": ACCEPTED.replace("Stefan 09-06", "Stefan 09-06 via https://x.ddev.site/wp/wp-login.php?redirect_to=%2Fwp-admin%2F"),
    "magic link": ACCEPTED.replace("Stefan 09-06", "Stefan 09-06 via https://x.ddev.site/3f9a1c2b/7a3c1d9e2f-b41c8d7e-9f0a2b3c4d"),
    "application-password": DRIVEN.replace("curl -s https://", "wp user application-password create shakeout shakeout --porcelain, then curl -s https://"),
    "6x4 app password": DRIVEN.replace("curl -s https://", "minted AbCd EfGh IjKl MnOp QrSt UvWx, curl -s https://"),
    "basic auth in URL": DRIVEN.replace("https://x.ddev.site/wp-json", "https://shakeout:s3cr3tPw@x.ddev.site/wp-json"),
    "--user=": DRIVEN.replace("curl -s https://", "curl --user=shakeout:s3cr3tPw https://"),
    "session cookie": DRIVEN.replace("curl -s https://", "curl -b wordpress_logged_in_0123456789abcdef0123456789abcdef=shakeout https://"),
    "storage_state": DRIVEN.replace("curl -s https://", "storage_state=auth.json · curl -s https://"),
    "pwd= POST body": DRIVEN.replace("curl -s https://", "curl -d 'log=shakeout&pwd=s3cr3tPw' https://x.ddev.site/wp/wp-login.php, then curl -s https://"),
    "bare Bearer": DRIVEN.replace("curl -s https://", "Bearer 4f9a2b7c1d8e3f6a5b4c9d0e1f2a3b4c · curl -s https://"),
    "bare JWT": DRIVEN.replace("curl -s https://", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc · curl -s https://"),
    "JSON token": DRIVEN.replace("→ 200, 3 items", '→ 200 {"access_token": "4f9a2b7c1d8e"}'),
}

NOT_CREDENTIALS = {
    "_wpnonce=": DRIVEN.replace("page=audit", "page=audit&_wpnonce=abc123"),
    "prose": DRIVEN.replace("→ 200, 3 items", "→ 200, the password reset flow renders"),
    "six short words": DRIVEN.replace("→ 200, 3 items", "→ 200, this page does show some rows"),
    "verdict word pass:": DRIVEN.replace("→ 200, 3 items", "→ 200; pass: body has 3 rows"),
    "--url= flag": DRIVEN.replace("curl -s https://x.ddev.site/wp-json/audit/v1/rows → 200, 3 items",
                                  "ddev wp --url=https://x.ddev.site option get siteurl → https://x.ddev.site"),
    "pop-up: prose": DRIVEN.replace("→ 200, 3 items", "→ 200, the pop-up: closes on Escape"),
}


def run() -> list[tuple[bool, str]]:
    r = [
        # Review Focus 1 — a missing, empty or rowless manifest never passes vacuously
        _case("no manifest → FAIL", None, has=("no shakeout.md",)),
        _case("empty manifest → FAIL", "", has=("no rows",)),
        _case("header-only table → FAIL", HEAD, has=("no rows",)),
        _case("a directory that does not exist → FAIL", None, target="missing", has=("not a directory",)),
        # the happy path and the browser evidence rules
        _case("driven browser row + PNG on disk → PASS", DRIVEN, PNG, rc=0,
              has=("2 rows, 1 browser rows driven", "SHAKEOUT: PASS")),
        _case("browser row with no `Browser:` evidence → FAIL naming AF-1",
              HEAD + BROWSER.format("looked at it, table renders") + WIRE_PASS, has=("AF-1: browser row without",)),
        _case("no http url (`Browser: not-reached · png`) → FAIL", DRIVEN.replace("https://x.ddev.site/wp/wp-admin/admin.php?page=audit", "not-reached"),
              PNG, has=("http url",)),
        _case("evidence names a PNG that is not on disk → FAIL", DRIVEN, has=("shakeout/af-1.png", "not found")),
        # Review Focus 2 — the screenshot cannot escape or be faked
        _case("traversal out of the feature dir → FAIL", DRIVEN.replace("shakeout/af-1.png", "shakeout/../../escape.png"),
              {"../escape.png": PNG_MAGIC + bytes(1200)}, has=("not found under the feature dir",)),
        _case("a PNG under 1 KB → FAIL", DRIVEN, {"shakeout/af-1.png": PNG_MAGIC + bytes(10)}, has=("bytes",)),
        _case("not a PNG → FAIL", DRIVEN, {"shakeout/af-1.png": b"GIF89a" + bytes(1200)}, has=("PNG magic",)),
        _case("`unverified-no-browser` on a browser row → FAIL", DRIVEN.replace("| pass |", "| unverified-no-browser |", 1), PNG),
        # rows the plan no longer classifies: the manifest's own Layer must be valid
        _case("a blank Layer cell → FAIL", DRIVEN.replace("| browser |", "|  |", 1), PNG, has=("not one of",)),
        _case("a `wire` row `fail` → FAIL naming AF-2", DRIVEN.replace(WIRE_PASS, "| AF-2 | REST list | wire | fail | curl → 500 |\n"), PNG, has=("AF-2",)),
        _case("a `wire` row `pass` alone → PASS", HEAD + WIRE_PASS, rc=0, has=("1 rows, 0 browser rows driven",)),
        _case("a fenced sample row is not read", "```\n| AF-9 | sample | browser | pass | none |\n```\n" + DRIVEN, PNG, rc=0, has=("2 rows",)),
        # Review Focus 3 — only the human's token excuses a row
        _case("`Accepted-by-human:` excuses the row → PASS", ACCEPTED, rc=0,
              has=("[shakeout-accepted] AF-1: accepted by the human", "no browser on this box")),
        _case("old `Ruling:` token fails", ACCEPTED.replace("Accepted-by-human:", "Ruling:"),
              has=("AF-1: browser row without",), lacks=("shakeout-accepted",)),
        _case("accepted with a credential is reported, never echoed",
              ACCEPTED.replace("Stefan 09-06", "Stefan 09-06 via https://x.ddev.site/3f9a1c2b/7a3c1d9e2f-b41c8d7e-9f0a2b3c4d"),
              has=("[shakeout-accepted] AF-1: accepted by the human", "✗ [shakeout-credential]"), lacks=("3f9a1c2b",)),
        _case("a fenced curl transcript below the table fails naming its line",
              DRIVEN + "\n## How I logged in\n\n```\ncurl -u shakeout:s3cr3tPw https://x.ddev.site/wp-json/\n```\n",
              PNG, has=("✗ [shakeout-credential] line 11:",)),
    ]
    r += [_case(f"credential `{label}` → FAIL shakeout-credential", m, PNG, has=("✗ [shakeout-credential]",))
          for label, m in CREDENTIALS.items()]
    r += [_case(f"`{label}` is not a credential", m, PNG, rc=0, lacks=("shakeout-credential",))
          for label, m in NOT_CREDENTIALS.items()]
    return r
````

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/netdust-gates/tests/run.sh test_shakeout_check.py | tail -5`
Expected: every case `FAIL` (the checker does not exist), `Modules failed: 1`.

- [ ] **Step 3: Write `bin/shakeout-check.py`**

Write `plugins/netdust-gates/bin/shakeout-check.py` (`mkdir -p plugins/netdust-gates/bin` first) with the text below, leaving the marker line `# @@CREDENTIAL@@` exactly as written. Step 3b fills it from the 0.28 source, so the pattern is carried, not retyped.

```python
#!/usr/bin/env python3
"""shakeout-check.py — the shake-out manifest gate.

    shakeout-check.py <feature dir>

Reads <feature dir>/shakeout.md and exits 0 only when every row passes on evidence a file can
prove, never on the verdict word: a `browser` row needs `Browser: <http url> · <png>` with a
real 1 KB–2 MB PNG under the feature dir; the whole file is scanned for credentials with no
override; only the human's `Accepted-by-human:` excuses a row. Bare python3.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BROWSER_EVIDENCE = re.compile(r"Browser:\s*(?P<url>https?://\S+)\s*·\s*(?P<path>\S+)")
ACCEPTED = re.compile(r"Accepted-by-human:\s*(?P<reason>.+)")
# @@CREDENTIAL@@
LAYERS = ("browser", "wire", "cli")
COLUMNS = {"n": "#", "flow": "Flow", "layer": "Layer", "verdict": "Verdict", "evidence": "Evidence"}
TABLE_ROW = re.compile(r"^\s*\|(?P<cells>.*\|)\s*$")
TABLE_SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SCREENSHOT_BYTES = (1024, 2 * 1024 * 1024)

Finding = tuple[str, str, str]  # (status, check, detail)


def _unfenced(text: str) -> list[str]:
    out, in_fence = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            out.append(ln)
    return out


def _cells(line: str) -> list[str] | None:
    m = TABLE_ROW.match(line)
    return [c.strip() for c in m.group("cells").rstrip("|").split("|")] if m else None


def parse_rows(text: str) -> list[dict]:
    """Rows of the first pipe table whose header names a `#` column."""
    lines = _unfenced(text)
    index, rows = None, []
    for i, ln in enumerate(lines):
        if TABLE_SEPARATOR.match(ln):
            continue
        cells = _cells(ln)
        if index is None:
            if cells and "#" in cells and i + 1 < len(lines) and TABLE_SEPARATOR.match(lines[i + 1]):
                names = [c.lower() for c in cells]
                index = {k: names.index(h.lower()) if h.lower() in names else None
                         for k, h in COLUMNS.items()}
            continue
        if cells is None:
            break
        rows.append({k: (cells[j] if j is not None and j < len(cells) else "")
                     for k, j in index.items()})
    return [r for r in rows if r["n"]]


def _screenshot_problem(path: str, spec_dir: Path) -> str | None:
    if not (path.startswith("shakeout/") and path.endswith(".png")):
        return f"screenshot `{path}` must be `shakeout/<name>.png`"
    try:
        target = (spec_dir / path).resolve()
        if not (target.is_file() and target.is_relative_to(spec_dir.resolve())):
            return f"screenshot `{path}` not found under the feature dir"
        size = target.stat().st_size
        if not SCREENSHOT_BYTES[0] <= size <= SCREENSHOT_BYTES[1]:
            return f"screenshot `{path}` is {size} bytes — a viewport PNG is 1 KB to 2 MB"
        with target.open("rb") as fh:
            magic = fh.read(8)
    except (OSError, ValueError) as e:
        return f"screenshot `{path!r}` could not be read ({e.__class__.__name__})"
    return None if magic == PNG_MAGIC else f"screenshot `{path}` does not open with the PNG magic"


def _row_problem(row: dict, spec_dir: Path) -> str | None:
    layer, verdict, evidence = row["layer"].lower(), row["verdict"].lower(), row["evidence"]
    if layer not in LAYERS:
        return f"layer `{row['layer']}` is not one of {', '.join(LAYERS)}"
    if layer != "browser":
        if verdict == "fail" or verdict.startswith("unverified"):
            return f"{layer} row verdict `{row['verdict']}`"
        return None
    if verdict != "pass":
        return f"browser row verdict `{row['verdict']}` — not driven"
    m = BROWSER_EVIDENCE.search(evidence)
    if not m:
        return "browser row without `Browser: <http url> · <screenshot path>` evidence"
    return _screenshot_problem(m.group("path"), spec_dir)


def check(spec_dir: Path) -> list[Finding]:
    if not spec_dir.is_dir():
        return [("fail", "shakeout-manifest", f"{spec_dir} is not a directory")]
    manifest = spec_dir / "shakeout.md"
    if not manifest.exists():
        return [("fail", "shakeout-manifest", "no shakeout.md — a user-facing change owes a manifest")]
    try:
        text = manifest.read_text()
    except (OSError, ValueError) as e:
        return [("fail", "shakeout-manifest", f"shakeout.md could not be read ({e.__class__.__name__})")]
    findings: list[Finding] = [
        ("fail", "shakeout-credential", f"line {i}: carries a credential — the whole file is committed")
        for i, ln in enumerate(text.splitlines(), 1) if CREDENTIAL.search(ln)]
    rows = parse_rows(text)
    if not rows:
        return findings + [("fail", "shakeout-manifest",
                            "shakeout.md has no rows — a manifest that lists no flow proves nothing")]
    driven = 0
    for row in rows:
        problem = _row_problem(row, spec_dir)
        accepted = ACCEPTED.search(row["evidence"])
        if accepted:
            reason = "" if CREDENTIAL.search(row["evidence"]) else f" — {accepted.group('reason').strip()}"
            findings.append(("pass", "shakeout-accepted", f"{row['n']}: accepted by the human{reason}"))
        elif problem:
            findings.append(("fail", "shakeout-manifest", f"{row['n']}: {problem}"))
        driven += row["layer"].lower() == "browser" and problem is None
    findings.append(("pass", "shakeout-manifest", f"shakeout: {len(rows)} rows, {driven} browser rows driven"))
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: shakeout-check.py <feature dir>", file=sys.stderr)
        return 2
    findings = check(Path(argv[0]))
    for status, name, detail in findings:
        print(f"  {'✓' if status == 'pass' else '✗'} [{name}] {detail}")
    failed = any(s == "fail" for s, _, _ in findings)
    print(f"\nSHAKEOUT: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 3b: Fill the marker from the 0.28 source**

```bash
python3 - <<'PY'
src = open("plugins/netdust-agent/bin/gate-check.py").read()
block = src[src.index("# The words the plan names"):src.index("def _split_cells")].rstrip()
p = "plugins/netdust-gates/bin/shakeout-check.py"
out = open(p).read()
assert "# @@CREDENTIAL@@" in out
open(p, "w").write(out.replace("# @@CREDENTIAL@@", block))
PY
grep -c "CREDENTIAL = re.compile" plugins/netdust-gates/bin/shakeout-check.py
```
Expected: `1`.

- [ ] **Step 4: Run to verify it passes**

Run: `bash plugins/netdust-gates/tests/run.sh test_shakeout_check.py | tail -8`
Expected: every case `pass` (about 49), `All harness tests passed.` A credential case that does not fail means the pasted regex differs from the source — re-extract it; do not edit the regex to fit.

- [ ] **Step 5: Confirm the checker is standalone**

Run: `grep -n "gate-check\|import gate" plugins/netdust-gates/bin/shakeout-check.py; echo "exit $?"`
Expected: no matching lines (`exit 1`).

- [ ] **Step 6: Commit**

```bash
git add plugins/netdust-gates/bin/shakeout-check.py plugins/netdust-gates/tests/test_shakeout_check.py
git commit -m "feat(gates): shakeout-check.py — manifest gate extracted from gate-check, Accepted-by-human token" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

### Task 7: The close — agents and `/shakeout` (spec R6)

**Files:**
- Create (carried, one edit): `plugins/netdust-gates/agents/security-sentinel.md`, `plugins/netdust-gates/agents/invariant-auditor.md`
- Create (re-aimed rewrite): `plugins/netdust-gates/agents/shakeout-qa.md`
- Create (rewrite, shorter): `plugins/netdust-gates/commands/shakeout.md`
- Test: `plugins/netdust-gates/tests/test_close_wiring.py`

**Interfaces:**
- Consumes: the manifest grammar and CLI of `bin/shakeout-check.py` (Task 6); the tokens `Accepted-by-human:` and `netdust-gates:policy`'s `edge-classes.md` (Task 2).
- Produces: agents `security-sentinel`, `invariant-auditor`, `shakeout-qa`; command `/netdust-gates:shakeout` — the four-step close named in the policy skill's Close section.

- [ ] **Step 1: Write the failing test**

`plugins/netdust-gates/tests/test_close_wiring.py`:

```python
"""test_close_wiring.py — the close (agents + /shakeout) speaks the checker's grammar and
carries none of the 0.28 machinery it replaces."""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
AGENTS = ("security-sentinel", "invariant-auditor", "shakeout-qa")
STALE = ("gate-check", "tasks.md", "Lane", "verify-budget", "model-ladder", "herdr-moments",
         "implementer", "Stage 3", "Acceptance flows", "Shake-out access", "FULL tier", "FULL-tier")


def _read(rel: str) -> str:
    return (PLUGIN / rel).read_text()


def _frontmatter_ok(text: str, name: str) -> bool:
    m = re.match(r"---\n(?P<fm>.*?)\n---\n", text, re.S)
    return bool(m) and f"name: {name}" in m.group("fm") and "description:" in m.group("fm")


def run() -> list[tuple[bool, str]]:
    agents = {a: _read(f"agents/{a}.md") for a in AGENTS}
    command = _read("commands/shakeout.md")
    stale = sorted({s for t in (*agents.values(), command) for s in STALE if s in t})
    qa = agents["shakeout-qa"]
    return [
        (all(_frontmatter_ok(agents[a], a) for a in AGENTS), "each agent has `name:` matching its file and a description"),
        (all(s in qa for s in ("Accepted-by-human:", "shakeout-check.py", "Browser:", "shakeout/<name>.png", "edge-classes.md"))
         and "Ruling:" not in qa,
         "shakeout-qa writes the checker's grammar and never `Ruling:`"),
        (all(s in command for s in ("bin/shakeout-check.py", "make gate", "Accepted-by-human:", "shakeout-qa",
                                    "screenshot", "netdust-gates:policy")),
         "/shakeout runs make gate, the qa agent, the checker, the screenshot yield and points at the policy close"),
        (not stale, f"none of the 0.28 machinery survives in the close (found {stale})"),
    ]
```

- [ ] **Step 2: Run to verify it fails**

Run: `bash plugins/netdust-gates/tests/run.sh test_close_wiring.py`
Expected: `FileNotFoundError … agents/security-sentinel.md`.

- [ ] **Step 3: Carry the two reviewers; edit the auditor's dispatch sentence**

```bash
mkdir -p plugins/netdust-gates/agents plugins/netdust-gates/commands
cp plugins/netdust-agent/agents/security-sentinel.md plugins/netdust-agent/agents/invariant-auditor.md plugins/netdust-gates/agents/
python3 - <<'PY'
p = "plugins/netdust-gates/agents/invariant-auditor.md"
s = open(p).read()
old = "Dispatch it at FULL-tier review gates and /shakeout on any project carrying an invariants doc, or standalone"
assert old in s
open(p, "w").write(s.replace(old, "Dispatch it at the whole-branch review on any project carrying an invariants doc, or standalone"))
PY
grep -c "FULL" plugins/netdust-gates/agents/invariant-auditor.md plugins/netdust-gates/agents/security-sentinel.md
```
Expected: both `0`.

- [ ] **Step 4: Write `agents/shakeout-qa.md`**

```markdown
---
name: shakeout-qa
model: sonnet
tools: Read, Grep, Glob, Bash, Skill, Edit, Write
description: Use this agent at close, on a user-facing change, to exercise the BUILT artifact end-to-end — real browser, real un-mocked wire — write `specs/<feature>/shakeout.md` for `bin/shakeout-check.py`, and commit every flow it drove as a test. Green unit tests are not a shake-out. It is the behavioural sibling of the reviewer: the reviewer reads the diff, shakeout-qa runs the artifact.
---

You are a QA engineer who owns the shake-out. Your job is not to read code — it is to USE the
thing: exercise the built artifact end-to-end in a real environment, write the manifest the
checker reads, and commit the flows you drove as the feature's tests. You do not fix: you drive,
observe, record, and hand back.

**Green unit tests are not shake-out.** A passing suite says the code is right in the small,
nothing about the feature when someone drives it. The blank-editor empty state, the route-vs-
service guard gap, the double-submit, the no-rollback divergence and the jsdom-masked race all
shipped past a green suite. So you run the real artifact, through its faithful layer.

## Where you may write

`tests/**`, `specs/<feature>/shakeout.md`, `specs/<feature>/shakeout/*.png` — nothing else. A
defect in the code is a manifest row for the fix pass, never an edit of yours.

## Which flows

No plan table lists them; you derive them, and your report shows the list so nothing is
silently absent: one flow per user-facing requirement in `specs/<feature>/spec.md`, plus one per
`Review Focus` line in `plan.md` that names something a user can see or do. Take each flow's
edges from `edge-classes.md` beside the `netdust-gates:policy` skill (empty, denied actor,
re-entry, concurrent, boundary, mid-flow failure, delivery seam). A flow driven on its happy path
only is `unverified`, not `pass`.

## The manifest

`specs/<feature>/shakeout.md`: one table, one row per flow:

| # | Flow | Layer | Verdict | Evidence |
|---|---|---|---|---|

`Layer` is `browser`, `wire` or `cli`. A flow a person drives on a screen is `browser`;
labelling it `wire` to skip the screenshot is the one lie the checker cannot see, and Stefan
looks at the screenshots. `Verdict` is `pass`, `fail`, `not-reachable` or `unverified-no-browser`.

A `browser` row is `pass` only when Evidence carries `Browser: <post-login url> ·
shakeout/<name>.png` — a real viewport PNG, 1 KB to 2 MB, committed under
`specs/<feature>/shakeout/`. `bin/shakeout-check.py` reads the evidence, never the verdict word.
A `wire` or `cli` row fails the check on `fail` or `unverified…`.

`Accepted-by-human: <reason>` in Evidence excuses one row. The human writes it — you never do —
and it never excuses a credential. The WHOLE file is scanned for credentials (login links,
application passwords, session cookies, basic auth, bearer tokens, storageState); a hit fails
with no override because the file is committed. Write the URL of the page AFTER login, never
the link that minted the session. Each row also names the test you committed for it.

## The flows become the tests

Every `browser` flow you drove is committed as a Playwright spec; every `wire` flow as an
integration test through the project's runner (on WordPress, `netdust-wp:wp-testing`). The row
names the file.

## Access and actors

The login comes from the project's recipe (WordPress: `netdust-wp:wp-testing`); you never invent
one. A recipe or URL on a production host is refused: stop and report BLOCKED. Drive the seeded
actors the recipe creates, never real user rows — the screenshots are committed.

## Protocol

1. **Sweep.** Re-run the suites, then walk the artifact end-to-end and record findings as
   manifest rows, not chat.
2. **Drive.** UI flows through a real browser — a Playwright spec if one exists, else
   `superpowers-chrome:browsing` against the running dev server; no UI flow is `pass` without a
   browser. Backend flows through the un-mocked wire. Screenshot the post-login surface.
3. **Bite check.** For each dangerous path in the diff: which test goes RED if it breaks? A path
   the suite would not catch is a finding even when everything is green.
4. **Write.** A `fail` row carries the exact reproduction — payload, click sequence, live-DOM
   observation — enough to reproduce it cold.
5. **Hand back.** You do not fix. The fix pass repairs each `fail` (RED→GREEN); you re-drive the
   affected flows — new screenshot, updated row — until the checker exits 0.

## Judgment

- **"Still broken" from the human is truth.** Reproduce the EXACT failing payload before
  calling it environmental.
- **Measure the live artifact.** Read the live DOM (`getBoundingClientRect`, computed styles);
  a from-source guess about rendered behaviour is a guess.
- **You are the artifact half; the reviewer is the diff half.** A guard present in the diff can
  still be bypassed by a real flow. Do not duplicate the reviewer's diff-reading.
- **Believe the failure before you explain it away.** When routes 500 that exist in code with
  passing tests, check migration state first.

Done when: every flow and edge carries a row, every browser pass has its screenshot on disk,
every driven flow is a committed test the row names, and every `fail` is reproducible cold.
```

- [ ] **Step 5: Write `commands/shakeout.md`**

````markdown
---
description: Close a user-facing change — make gate, shakeout-qa drives the artifact and writes the manifest, bin/shakeout-check.py must exit 0, the human sees one screenshot per surface. Then the whole-branch review per the netdust-gates:policy close.
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent"]
---

Run the close for `specs/<feature>/`. Four steps, in order.

## Step 1 — `make gate`

Run the project's own suite: `make gate`. It must exit 0. Exit 1 with "No commands.gate in
site.yml" means the project has no declared gate — declare it (`commands.gate`) as the first
fix, then run it; that is not a reason to skip.

## Step 2 — Drive the artifact

Dispatch **`shakeout-qa`** on the most capable available model for the flows: it derives the
flow list from the spec and the plan's `Review Focus`, drives each through its faithful layer
(browser for UI, un-mocked wire for backend), commits the flows as tests, and writes
`specs/<feature>/shakeout.md` with a screenshot under `specs/<feature>/shakeout/` for every
browser pass. It reports the flow list it derived; read it for what is missing.

A change with no user-facing surface has nothing to drive: say so and go to Step 4.

## Step 3 — The manifest gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/bin/shakeout-check.py" specs/<feature>
```

On exit 1: each `fail` row is one fix, RED→GREEN; re-dispatch `shakeout-qa` for the affected
flows; re-run the check until it exits 0. Nothing after this runs while it fails.

## Step 4 — The screenshot yield, then the branch review

Show Stefan one screenshot per surface — the PNGs the manifest's browser rows name, never a
per-flow slideshow. Beside them list every `✓ [shakeout-accepted]` row the check printed:
`Accepted-by-human:` is agent-writable, so one Stefan did not write is reverted and its row
re-driven. This is a stop; wait for him.

Then the whole-branch review and the single fix pass exactly as the `netdust-gates:policy`
Close section states them, and `superpowers:finishing-a-development-branch`. Report the
manifest, the review verdicts and every `Ruling:` from the ledger together.
````

- [ ] **Step 6: Ground-truth `${CLAUDE_PLUGIN_ROOT}` in a command**

Ask the `claude-code-guide` agent: "In a plugin's `commands/*.md` body, is `${CLAUDE_PLUGIN_ROOT}` substituted, or is it only expanded in hooks.json and MCP config?" If it is not substituted, replace the command's path with `~/.claude/plugins/netdust-gates/bin/shakeout-check.py` (the stable symlink `session-start.sh` refreshes for every `netdust-*` plugin in the registry) and keep the token `bin/shakeout-check.py` in the text so the test still holds.

- [ ] **Step 7: Run to verify it passes**

Run: `bash plugins/netdust-gates/tests/run.sh test_close_wiring.py`
Expected: 4 `pass` lines.

- [ ] **Step 8: Commit**

```bash
git add plugins/netdust-gates/agents plugins/netdust-gates/commands plugins/netdust-gates/tests/test_close_wiring.py
git commit -m "feat(gates): the close — security-sentinel, invariant-auditor, shakeout-qa, /shakeout" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Whole-branch verification and live wiring proof

**Files:** none created; the report is the deliverable.

**Interfaces:** consumes everything above.

- [ ] **Step 1: Full suite**

Run: `bash plugins/netdust-gates/tests/run.sh | tail -8`
Expected: `Modules failed: 0`, `All harness tests passed.` Record the module count and the last lines for the report.

- [ ] **Step 2: Boundaries held**

```bash
git diff --stat "$(git merge-base HEAD main)" -- plugins/netdust-agent plugins/netdust-wp plugins/netdust-devops plugins/netdust-core | tail -1
git diff --name-only "$(git merge-base HEAD main)" | grep -v "^plugins/netdust-gates/\|^specs/netdust-gates/\|^.claude-plugin/marketplace.json$" | wc -l
git status --short | grep -c "__pycache__"
```
Expected: the first prints nothing, the other two print `0`. Anything else: stop and fix before reporting.

- [ ] **Step 3: Live wiring proof — the 0.28 bug does not recur**

The tests call the script over stdin, which is why the 0.28 wiring bug stayed green. Prove the Write floor fires through the real hook wiring:

```bash
P=$(mktemp -d -t gates-live-XXXX) && mkdir -p "$P/.claude" && echo '{"enabledPlugins":{"netdust-agent@netdust-plugins":false}}' > "$P/.claude/settings.json"
( cd "$P" && claude -p "Create the file vendor/acme/lib/probe.php containing <?php echo 1;" --plugin-dir "$OLDPWD/plugins/netdust-gates" --permission-mode acceptEdits --max-turns 6 >/dev/null 2>&1 )
grep -c "vendor-floor.*$(basename "$P")" ~/.claude/logs/memory-hook.log
```
Expected: `1` or more — the hook log names a `vendor-floor` ask for this scratch path, which only a live tool call through `hooks.json` can produce (the tests use their own temp dirs). `0` means the matcher is not reaching Write: stop and debug the wiring.

- [ ] **Step 4: Eval and size record**

```bash
python3 plugins/netdust-gates/evals/run-evals.py
git ls-files plugins/netdust-gates | xargs wc -l | sort -n | tail -30
```
Expected: `3/3 cases passed` (rerun once if a stochastic miss; two misses on the same case is a skill defect — report it). Keep both outputs.

- [ ] **Step 5: Hand over for the branch review**

State branch and sha, the test command and its output, the eval results, files created with line counts, and every ruling made (this plan's table plus any ledgered during the build), each with what it costs if wrong. The whole-branch review runs next per the brief: the most capable model, joined by `netdust-agent:security-sentinel` for the hooks; one fix pass, each fix RED→GREEN, no re-review.

---

## Self-review

- **Spec coverage:** R1 → T2 (policy, `Source:`, Global Constraints, Review Focus, First working version, Simplest design); R2 → T2 (intake paragraph + threat-modeling); R3 → T2 (Execution mode); R4 → T2 (`wordpress.md`); R5 → T2 (Stops) + T6/T7 (`Accepted-by-human:`); R6 → T2 (Close) + T7; R7 → T4, T5; R8 → T6; R9 → T1 (`CLAUDE.md`) + the banned-grammar assertion in T2; R10 → T3. "Not in v0" is a Global Constraint and is asserted by T2's banned-token test, T4/T5's wiring tests and T7's stale-token test.
- **Placeholder scan:** none — every file is given in full, or carried by an exact command with its expected result. The one deferred fact (does `${CLAUDE_PLUGIN_ROOT}` expand in a command) is a named Step 6 check with a stated fallback.
- **Type/name consistency:** `HANDLED_TOOLS` (T4) is what `test_hooks_wiring.py` reads; `_hooks_json()` / `_commands()` defined in T4 are reused in T5; check names `shakeout-manifest` / `shakeout-credential` / `shakeout-accepted` in T6 are what T7's command mentions; `Accepted-by-human:` is spelled identically in T2, T6, T7.
- **Review Focus:** all five lines have a named test; the checker's rows-and-layer rule (Ruling 1) is pinned by "blank Layer" and "no manifest".
