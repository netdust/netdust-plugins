# Handover — build netdust-gates v0

Written 2026-09-21 by the session that studied superpowers 6.4.1, last week's
transcripts and netdust-agent 0.28, and wrote the spec with Stefan. You continue from
the approved spec. Read `spec.md` beside this file first; it is the authority.

## Where you are

- Worktree `/home/ntdst/Projects/netdust-plugins-gates`, branch `feature/netdust-gates`,
  cut from `main` at `cc584b1`. The spec is committed (`6852436`).
- Stefan approved the spec on 2026-09-21: "spec is good, open a session here in herdr
  netdust-gates worktree to continue this building".

## The route — ruled by Stefan, do not re-open it

This build does NOT go through `netdust-agent:harnessed-development` → `planning` →
`building`, and you do not run `gate-check.py` or write a `tasks.md` in the 0.28 grammar.
That grammar is what this plugin replaces; Stefan was told so before he said go ahead and
again when the spec was presented. Global CLAUDE.md §1 is answered by that ruling for
this worktree. If anything about the route is unclear, ask Stefan in your pane — do not
fall back to the 0.28 ceremony on your own.

The route is the one netdust-gates itself will prescribe:

1. Invoke `superpowers:writing-plans`. Write the plan to `specs/netdust-gates/plan.md`
   in upstream's format — `Spec:` pointer, `Global Constraints`, `Review Focus`, per-task
   `Interfaces`. Add the two netdust lines from spec R1: `First working version`, and the
   simplest-design paragraph.
2. STOP. Stefan reviews the saved plan and picks the execution mode. Recommend Native:
   the tasks are mostly carry-and-trim plus one prose skill, and they share few interfaces.
3. Build under the mode he picks. One whole-branch review at the end, on the most capable
   model, joined by `netdust-agent:security-sentinel` for the hooks. One fix pass, each
   fix RED→GREEN, no re-review.

## Source map — where the carried pieces live (read them, do not trust this list blindly)

All under `plugins/netdust-agent/` in this same worktree. Copy from there; never edit there.

| v0 piece (spec) | Source |
|---|---|
| R7 guard: flow floor, vendor floor, ask tier | `hooks/pretooluse-guard.py` — `check_flow_floor`, `check_vendor_floor`, `match_denylist`; drop `check_upstream_floor` |
| R7 memory hooks | `hooks/session-start.sh` (strip the placement / harness paragraphs), `hooks/session-stop.py` |
| R7 tests | `tests/test_pretooluse_guard.py`, `test_session_start*.py`, `test_stop_hook_*.py`, `test_tag_scanner.py`, `hook_test_utils.py`, `run.sh` |
| R8 shake-out checks | `bin/gate-check.py` from `# ── the shake-out manifest` (~line 2410) to `run_shakeout_checks`; tests in `tests/test_spec_gate_check.py` (the shakeout cases only) |
| R6 agents | `agents/security-sentinel.md`, `agents/invariant-auditor.md`, `agents/shakeout-qa.md` |
| R6 command | `commands/shakeout.md` — rewrite shorter against `make gate` and `bin/shakeout-check.py` |
| R1 inputs | `skills/threat-modeling/`, `skills/architecture-invariants/`, `skills/_shared/calibrations.md` (the green-but-broken table feeds the edge-class catalog) |
| R4 pack | `plugins/netdust-wp/skills/wp-plan-requirements/SKILL.md` is the content to re-aim at `Global Constraints` / `Review Focus`; cite `ntdst-framework`, `ntdst-patterns`, `wp-security`, `wp-testing`, never restate them |

Upstream, for the plan format and the vocabulary netdust-gates must not collide with:
`~/.claude/plugins/cache/superpowers-marketplace/superpowers/6.4.1/skills/` —
`writing-plans`, `executing-plans`, `subagent-driven-development`, `brainstorming`.

## Known facts worth not re-deriving

- The 0.28 guard is registered with `"matcher": "Bash"` in `hooks/hooks.json`, so its
  Write/Edit branch never runs live. v0's `hooks.json` must cover
  `Bash|Write|Edit|NotebookEdit`, and a test must fail when it does not (spec R7).
- The hook tests call the scripts directly over stdin. That is why the wiring bug stayed
  green. Keep those tests, add the wiring test.
- The plugin also needs an entry in `.claude-plugin/marketplace.json` and its own
  `.claude-plugin/plugin.json` (version `0.1.0`).
- Skills are contracts, not books (global CLAUDE.md): the policy skill should land well
  under 150 lines. If it grows past that it is restating superpowers.

Treat the environment notes above as hints. Ground-truth the test runner
(`bash plugins/netdust-agent/tests/run.sh` is how 0.28 runs its suite) before relying on it.

## Boundaries

- Nothing under `plugins/netdust-agent/`, `netdust-wp/`, `netdust-devops/` or
  `netdust-core/` is edited. New files only, under `plugins/netdust-gates/`, plus the
  marketplace entry and `specs/netdust-gates/`.
- Commit by path on this branch. No merge, no push, no `git add -A`, no stash.
- The main checkout (`/home/ntdst/Projects/netdust-plugins`) has an uncommitted
  `plugins/netdust-wp/skills/ntdst-yootheme/lessons.md` that is Stefan's. Leave it.
- The site repo (`~/Sites/netdust`) is NOT part of this build. Its pilot setup (spec,
  last section) happens after the plugin exists, with Stefan.

## Report when done

Branch and sha; the test command and its output; the three eval cases and their result;
files created, with line counts; every ruling you made, each with what it costs if wrong.
