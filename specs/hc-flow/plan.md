# hc flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every multi-agent flow in the harness runs on herdr-core (`hc`): roles as templates, parent → child → report, no default worktree, and no herdr 0.9 recipe left in the live plugins.

**Architecture:** netdust-core ships the role templates (`hc-templates/`), an installer (`bin/hc-templates`) and a new skill `hc-orchestration` that replaces `herdr-orchestration`. netdust-gates' policy starts the coder through that skill, and its eval runner swaps the `herdr` stub for an `hc` stub plus a scratch-core sandbox. netdust-devops' parallel-work carries the urgent-only worktree rule. **First working version:** Task 1. After it, `hc templates` lists the roles, and the reviewer proves live, with Stefan, that a child started on WSL shows under its parent in the app.

**Tech Stack:** Markdown skills, POSIX sh, Python 3 (stdlib only, the tests' house style), herdr-core 0.1.13.

**Spec:** `specs/hc-flow/spec.md`

## Global Constraints

- herdr-core floor: `hc` 0.1.13 (installed 2026-10-29); no command or flag the 0.1.13 `hc --help` / `hc <cmd> --help` lacks.
- Inside-hc detection is `HC_TERMINAL_ID` set; outside hc the policy's fallback (one background subagent) stands (spec R2).
- No live reference to `herdr-orchestration`, `herdr agent start`, `herdr-watcher` or `HERDR_ENV` in `netdust-core`, `netdust-gates` or `netdust-devops`. Changelog text in `plugin.json`/`marketplace.json` descriptions and `plugins/netdust-agent/` are history, not live (spec R2).
- Worktrees: never inside `~/Sites`; when one is needed, `~/.herdr/worktrees/<repo>/<branch>` (spec R6).
- Anything that starts hc in a test or an eval uses its own `HC_SESSION` and scratch `XDG_CONFIG_HOME`/`XDG_STATE_HOME`/`XDG_RUNTIME_DIR`/`XDG_DATA_HOME` under a SHORT dir (`mktemp -d /tmp/hcXXXX`). hc refuses a socket path over 107 bytes, and the eval roots are too deep. It stops that core when done (`hc server stop` with the same env). It never touches the default session (spec R10).
- Repo gate: `bash plugins/netdust-gates/tests/run.sh && bash plugins/netdust-core/tests/run.sh` (the second runner is new in Task 1). There is no Makefile here; "make gate" in this plan means this line.
- The coder never runs `hc machine` or `hc update`, never runs `hc server` against the default session (scratch sessions only, per the line above), never installs into the real `~/.config/herdr-core`, and never touches the app. The operational steps after the merge belong to the reviewer and Stefan.

## Review Focus

1. **An eval or test reaches Stefan's live core** (an inherited `HC_SESSION`/`HC_TERMINAL_ID`, a missing XDG override, or `hc` resolving to the real binary in a stubbed case). Expected: refused before the case starts. → Test map row 2.
2. **A reviewer or sparring helper edits the tree.** Expected: read-only by tool list and instruction (`--disallowedTools Edit Write NotebookEdit`, and the body says read-only). This is NOT enforced against Bash writes; the reviewer-side guarantee is that the coder alone commits. → Test map row 1.
3. **The coder dies with its reviewer** (no `--outlive-parent`), or is found by a SendMessage name after a restart. Expected: it survives and is found with `hc get <feature>-coder`. → Test map rows 3 and 4.
4. **A worktree appears in `~/Sites`**, or one is made for non-urgent work. Expected: the coder works in the checkout; a worktree only for urgent work, at `~/.herdr/worktrees/…`. → Test map rows 3 and 4.
5. **A stale herdr 0.9 instruction survives somewhere a session reads it** (policy, parallel-work, a template, the observer). Expected: none. → Test map row 4.
6. **A stubbed eval case allows an hc verb that runs code outside the bwrap sandbox** (`hc exec`, `hc file`, `hc put`, `hc keys`, `hc run` of an arbitrary command, `hc machine`, `hc server`). Expected: those are in `DISALLOWED`, and no case's `allow` grants them. → Test map row 2.

## Simplest design

The simplest design ships three templates and a skill, and points the policy at them. It's what this plan does, with two deviations from the spec as first approved. Stefan ruled on both on 2026-10-29, and the spec now carries them:
- **The `gate` role is not a template (spec R3; ruled "Plain program").** Running `make gate` needs no agent: `hc run --bg --name gate make gate` reports its exit code to the parent as a note, and `hc read gate` gives the output. A Claude agent would add cost and nondeterminism for nothing. The skill documents it as the gate role.
- **The end-to-end proof is a shell test, not a live eval case** (ruled "Shell test + live check"). A `claude -p` eval parent is no hc terminal, so it can't receive reports (plan review B1). A real-Claude child would also run outside the eval sandbox, with Stefan's settings (S5). Task 1's `test-hc-report.sh` instead proves parent → child → report → wait in a scratch core with plain programs. Verified 2026-10-29: a `bash` parent read the child's `hc send` text and its exit note, and `hc wait --children any` returned 0. The live Claude proof stays the Task 1 checkpoint with Stefan.

## Threat model

- **Assets:** Stefan's live hc core (default session) with its terminals and machines, his `~/.config/herdr-core`, his `~/.claude` settings, and anything the WSL user can reach.
- **Attacks:**
  - an eval case or test inherits `HC_SESSION`/`HC_TERMINAL_ID`, or resolves `hc` to the real binary, and drives the live core
  - a case allows an hc verb that runs a program outside Claude's bwrap sandbox (`hc exec`, `hc run <cmd>`, `hc file`, `hc put`, `hc keys`)
  - a test starts the default core by calling `hc` with the env unset
  - a template child, started in real use, inherits auto mode and Stefan's plugins
- **Mitigations:**
  - `child_env` strips `HC_*`/`HERDR_*` and sets a scratch session; the stub must win `command -v hc` before a case starts; `DISALLOWED` covers the verbs above, and the shape test fails if any case's `allow` grants one (→ row 2)
  - core tests use only scratch sessions, never a bare `hc` (→ row 1)
- **Deferred:** a template child in real use runs with Stefan's settings in auto mode. That is the intended trust (same as the coder today), and it's bounded by the coder's tree and the reviewer's review.

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| 1. Role templates + installer, and the report mechanism | `bin/hc-templates [--on <machine>]` → `hc templates`; `hc run --bg` child → `hc send` → parent | shell · `plugins/netdust-core/tests/test-hc-templates.sh`, `test-hc-report.sh` · `bash plugins/netdust-core/tests/run.sh` | live proof (reviewer + Stefan, after Task 1): app shows a WSL child under its parent |
| 2. Eval sandbox on hc | `run-evals.py` `child_env()` / `stub_for()` / `claude_args()` | unit · `plugins/netdust-gates/tests/test_evals_shape.py` · `bash plugins/netdust-gates/tests/run.sh test_evals_shape.py` | — |
| 3. The hc-orchestration skill | `skills/hc-orchestration/SKILL.md` as loaded by a session | skill eval · `plugins/netdust-core/skills/hc-orchestration/evals/` · each leg dispatched as a fresh general-purpose subagent, both outputs inlined into `scenario-N-judge.template.md`, a judge subagent scores PASS/FAIL per rule (procedure in `evals/README.md`); behavioural cases `two-session-handoff`, `coder-brief-no-recursion`, `small-tweak-no-artifacts` · `python3 plugins/netdust-gates/evals/run-evals.py <id>` | — |
| 4. The wiring (policy, parallel-work, no stale herdr) | the policy, parallel-work and every live plugin file | unit · `plugins/netdust-gates/tests/test_policy_skill.py`, new `plugins/netdust-gates/tests/test_hc_wiring.py` · `bash plugins/netdust-gates/tests/run.sh` | — |
| 5. Release | `plugin.json` / `marketplace.json` versions, CLAUDE.md proposal | check · `bash plugins/netdust-devops/tests/test-marketplace.sh` | — |

## Tasks

### Task 1: Role templates and their installer (first working version)

**Files:**
- Create: `plugins/netdust-core/hc-templates/coder.md`, `reviewer.md`, `sparring.md`
- Create: `plugins/netdust-core/bin/hc-templates` (sh, executable)
- Create: `plugins/netdust-core/tests/run.sh`, `plugins/netdust-core/tests/test-hc-templates.sh`, `plugins/netdust-core/tests/test-hc-report.sh`

**Interfaces:**
- Produces: `bin/hc-templates` installs every `hc-templates/*.md` into `${XDG_CONFIG_HOME:-$HOME/.config}/herdr-core/templates/`. With `--on <machine>`, it writes each one with `hc file write --on <machine> .config/herdr-core/templates/<name>.md < file`. It prints one line per installed name and exits non-zero on the first failure. Template names: `coder`, `reviewer`, `sparring`.

Template frontmatter (hc's line format, not YAML, no quotes; `docs/templates.md` in herdr-core):
- `coder.md`: `command: claude --permission-mode auto`. The pair always runs in auto (Stefan's ruling); a reviewer in another mode starts the coder by hand. The body: `Role: coder`; follow `netdust-gates:policy` and skip Intake and the plan; never start a coder; helpers allowed (`reviewer`, `sparring`, and the gate as `hc run --bg --name gate make gate`); stay in this checkout; report to the parent with `hc send` at pre-flight, at the first working version, at a block, and at Close; long answers go to a file and the path is sent.
- `reviewer.md` and `sparring.md`: `command: claude --model opus --permission-mode auto --disallowedTools Edit Write NotebookEdit`. The body: read-only, don't start agents, scope exactly as given, report with `hc send $parent` when done or stuck, findings to a file and send the path. The reviewer reviews; sparring argues the other side of a technical ruling.

- [ ] **Step 1:** Write `test-hc-templates.sh`. In a scratch env (Global Constraints: short `mktemp -d /tmp/hcXXXX`, `HC_SESSION=t`, the four XDG vars, `trap` that stops the core and removes the dir), run `bin/hc-templates` and assert:
  - `hc templates --json` lists exactly `coder`, `reviewer`, `sparring`
  - each template's `command` starts with `claude`
  - `reviewer` and `sparring` commands contain `--disallowedTools Edit Write NotebookEdit`
  - each body contains `hc send` (read the file; `hc templates` exposes `command`, not the body), and `coder.md` contains `first working version`
  - each test script refuses to start unless `HC_SESSION` and `XDG_RUNTIME_DIR` are its own scratch values (the threat model's "never a bare `hc`")
  - the real `~/.config/herdr-core/templates/` listing and mtimes are unchanged (filesystem only; never call `hc` with the env unset, which would start the default core)
  - `bin/hc-templates --on nosuchmachine` exits non-zero

  Write `test-hc-report.sh` in the same scratch env. A `bash` parent (`hc run --bg --name parent bash -c '…'`) starts a child `sh` that runs `hc send <parent's HC_TERMINAL_ID> review-done-42`, then runs `hc wait --children any`. Assert:
  - `hc read parent` contains `review-done-42` and the wait's `exited (exit 0` line (a plain parent gets the text untagged and no note; tags and notes need a status-reporting agent, which the live check covers)
  - the wait's exit code is 0
  - `hc ls --all` shows the child with `parent` = the parent's address

  `tests/run.sh` runs every `test-*.sh` here and exits non-zero on any failure.
- [ ] **Step 2:** Write the three templates and `bin/hc-templates`, then run `bash plugins/netdust-core/tests/run.sh`. Expected: all assertions pass. Then run the gate line. Expected: exit 0.
- [ ] **Step 3:** Commit (`hc-flow: role templates, their installer and the report proof — spec R3, R4`). Send the reviewer the first-working-version checkpoint (`hc send`). The reviewer runs the live proof with Stefan before Task 2. If the app does NOT show a WSL-started child under its parent, the reviewer stops the coder before Task 3. The fallback (spec: start every agent through the Windows core with `--on wsl`) changes Task 3's `## The pair recipe` and `## Machines`, and only those.

### Task 2: The eval sandbox on hc

**Files:**
- Create: `plugins/netdust-gates/evals/stubs/hc` (replaces `stubs/herdr`, which is deleted)
- Modify: `plugins/netdust-gates/evals/run-evals.py` (`DISALLOWED`, `child_env`, the stub resolution check, `stub_for`, `prepare_sandbox`'s `.git/info/exclude` line, `stray_worktrees`, docstring), `plugins/netdust-gates/evals/cases.json` (the three `stub_bin` cases), `plugins/netdust-gates/tests/test_evals_shape.py`

**Interfaces:**
- Produces: a stubbed case gets `$EVAL_ROOT/.hc/calls.log`, one line per call (its argv). The stub contacts no core and answers in hc 0.1.13's JSON shapes (copy them from `hc schema`, e.g. `run` = the full terminal record plus `first_message`). It covers:
  - `run`: logs the argv incl. `--outlive-parent`, `--label`, the template and the task. When the template or program is `coder`, it also writes `coder` into the marker `.hc/run-coder` (an `absent` entry is a file glob, not a regex).
  - `get`, `ls`, `wait`, `send`, `read`, `templates`, `--skill`, `--help`, `--version`. `get t1` answers with `labels: {"herdr.space": "s1"}`, so a session following the pair recipe finds its space id.

  `child_env` removes every inherited `HC_*`, `HERDR_*` and `CLAUDE_CODE_MESSAGING_*` var. It sets `HC_SESSION=eval` and the XDG vars under `$EVAL_ROOT/.tmp` when the socket path fits in 107 bytes, else under a short `mktemp -d /tmp/hcXXXX` (removed after the case). It sets `HC_TERMINAL_ID` only when the case's `env` asks for it: the reserved-key rule becomes `CLAUDE*` and `HC_*` except `HC_TERMINAL_ID`.

  `DISALLOWED` swaps the herdr list for: `Bash(hc server*)`, `Bash(hc machine*)`, `Bash(hc update*)`, `Bash(hc exec*)`, `Bash(hc file*)`, `Bash(hc put*)`, `Bash(hc keys*)`, `Bash(hc connect*)`, `Bash(hc * --on*)`, `Bash(hc --on*)`, `Bash(HC_*)`, `Bash(herdr*)`; the git entries stay. `.git/info/exclude` lists `.hc/` in place of `.herdr/`. `stray_worktrees` exempts nothing: any worktree in a case is a stray.

- [ ] **Step 1:** Rewrite `test_evals_shape.py`'s herdr assertions for hc:
  - `child_env` strips an inherited `HC_*`/`HERDR_*` (the `LIVE` dict keeps feeding `HERDR_ENV`, plus `HC_SESSION` and `HC_TERMINAL_ID`) and points `XDG_RUNTIME_DIR` where the socket path fits in 107 bytes
  - a login shell resolves `hc` to `stubs/hc`
  - the stub logs `run … coder …` to `.hc/calls.log` and touches `.hc/run-coder`
  - a case `env` setting `HC_SESSION` is refused, while `HC_TERMINAL_ID` is allowed
  - the stub digest set is `{hc, bash-env}`
  - every verb of the Review Focus 6 list is in `DISALLOWED`, and no case's `allow` grants it
  - the printenv rule (today :255-257) reads `printenv HC_TERMINAL_ID`, and the "no case allows every verb" rule (:266) holds for `hc`
  - the permission-mode rule (today :258-260) is deleted: the pair always runs in auto, and the coder template carries it (Stefan's ruling)

  Run `bash plugins/netdust-gates/tests/run.sh test_evals_shape.py`. Expected: FAIL (no `stubs/hc`).
- [ ] **Step 2:** Implement the stub and the runner changes, and convert the three cases.

  Each of the three cases' `env` becomes `{"HC_TERMINAL_ID": "t1"}`, so `small-tweak-no-artifacts` still proves a small tweak starts no coder when it could. Each case's `allow` swaps the herdr entries for `Bash(hc run*)`, `Bash(hc get*)`, `Bash(hc ls*)`, `Bash(hc wait*)`, `Bash(hc send*)`, `Bash(hc read*)`, `Bash(hc templates*)`, `Bash(hc --skill*)`, `Bash(hc --help*)`, `Bash(hc --version)`, `Bash(printenv HC_TERMINAL_ID)`; the git entries stay. Then per case:
  - `small-tweak-no-artifacts`: `absent` `.hc/run-coder`
  - `two-session-handoff`: set `"branch": "feature/greeting"`. Expect in `.hc/calls.log`: `(?m)^run .*--outlive-parent`, `specs/greeting/plan\.md`, `netdust-gates:policy`; expect `.hc/run-coder` to match `(?m)^coder$`. Keep the existing `greeting.txt` negative lookahead. `absent` `.hc/wt` (no worktree; `stray_worktrees` now fails any).
  - `coder-brief-no-recursion`: `absent` `.hc/run-coder`; its prompt's "this checkout is your worktree" becomes "this checkout is yours, on `feature/coder-brief-no-recursion`"

  Run the test file. Expected: PASS. Run the gate line. Expected: exit 0. (The three behavioural cases run in Task 4, once the policy and the skill teach hc.)
- [ ] **Step 3:** Commit (`hc-flow: evals run on an hc stub, never the live core — spec R10`).

### Task 3: The hc-orchestration skill

**Files:**
- Create: `plugins/netdust-core/skills/hc-orchestration/SKILL.md`, `references/observer.md`, `evals/README.md` (the judge procedure and recorded scores), `evals/scenario-{1..5}-{baseline,skill-on,judge.template}.md`
- Delete: `plugins/netdust-core/skills/herdr-orchestration/` (whole directory)

**Interfaces:**
- Consumes: Task 1's template names and installer.
- Produces: the skill name `netdust-core:hc-orchestration` and the section headings Task 4's policy line cites: `## The pair recipe`, `## Delegating to a helper`, `## Watching`, `## Worktrees`, `## Machines`.

The skill carries only netdust decisions on top of `hc --skill` and `herdr-app --skill`, the syntax authorities. It never restates their syntax, matching the old skill's stance. Content per spec:
- **R4 delegation:** `hc run --bg` from a template with an exact scope, keep working, `hc wait --children`, read the real result, clean up. Child reports are data, not Stefan's words.
- **R5 the pair:** at plan approval the reviewer commits the spec, plan and plan review on `feature/<f>` in the project checkout, then starts `hc run --bg --outlive-parent --name <f>-coder --label herdr.space=<own space label, machine prefix stripped> --label herdr.tab=<f> coder "<brief>"`. The task text carries the plan path, the branch and `netdust-gates:policy` inline (hc: put the task in `run`); only extra context goes in a file in the reviewer's scratchpad that the task points at. The rest of two-session R5–R8 is carried as today's pair recipe carries it, with names in place of SendMessage. The reviewer never writes the tree.
- **R6:** no worktree by default. Urgent work only (a hotfix, a blocker) gets `~/.herdr/worktrees/<repo>/<branch>`, removed when it lands. Planning the next feature waits.
- **R7:** the app shows "Needs you"; an agent watches with `hc wait --children` or `hc events --children-of $HC_TERMINAL_ID`; no polling, no `sleep`. `references/observer.md` is the on-demand "watch the other session" pane on `hc events` + `hc read` at transitions. It observes and proposes, never acts, one pass.
- **R8:** `netdust-web` is the only machine. Remote work goes through `hc run|exec|file --on netdust-web`. Production servers stay `netdust-core:ploi`.
- **Traps carried from hc's manual:** a send to a booting agent can drop (put the task in `run`); `first_message.sent=false` means read first; `blocked` means a human; `reason: timeout` is a check-in; `--force` never bypasses a permission prompt.

- [ ] **Step 1:** Write the five scenarios, baseline leg first. Each judge template carries rules that fail the baseline:
  - S1: delegate a review to a helper and collect it (R4)
  - S2: the pair handoff, with no worktree and `--outlive-parent` (R5, R6)
  - S3: an urgent hotfix during a coder, plus a non-urgent planning request (R6)
  - S4: watch a child without polling (R7)
  - S5: the observer pass (R7)

  Run each baseline leg as a fresh general-purpose subagent, inline its output into the judge template, and dispatch a judge subagent. Expected: the baseline fails the judge rules (record the scores in `evals/README.md`).
- [ ] **Step 2:** Write `SKILL.md` and `references/observer.md`, and delete `herdr-orchestration/`. Run the skill-on legs and the judge. Expected: skill-on passes every rule the baseline failed. Record the scores in `evals/README.md`.
- [ ] **Step 3:** Run the gate line. Expected: exit 0. Commit (`hc-flow: hc-orchestration replaces herdr-orchestration — spec R2, R4–R8`).

### Task 4: The wiring — policy, parallel-work, no stale herdr

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md` (Execution mode paragraph, lines ~95–107; the file is at 149 of its 150-line cap, so the rewrite comes out no longer), `plugins/netdust-gates/tests/test_policy_skill.py:52-54`, `plugins/netdust-devops/skills/parallel-work/SKILL.md` (the description at :3, decision table rows :14-19, "### A second agent" at :75-79, the "A coder's worktree on a DDEV project" section, the anti-pattern row "Two agents pointed at one directory" at :152, See also; pane/tab/workspace wording becomes hc's terminals/children)
- Create: `plugins/netdust-gates/tests/test_hc_wiring.py`

**Interfaces:**
- Consumes: Task 3's skill name and headings.

- [ ] **Step 1:** Write the failing tests:
  - `test_policy_skill.py` row 52: tokens become `("Role: coder", "netdust-core:hc-orchestration", "the pair recipe", "hc run", "HC_TERMINAL_ID", "project's checkout")`, plus a new row asserting `"herdr agent start"` and `"HERDR_ENV"` are absent from the policy.
  - `test_hc_wiring.py`: walks the text files (`.md`, `.py`, `.sh`, `.json`, `.toml`, extension-less scripts) under `plugins/netdust-core`, `plugins/netdust-gates` and `plugins/netdust-devops`. It skips `__pycache__/`, `.claude-plugin/plugin.json`, `evals/stubs/` and the tests that assert absence (`tests/test_session_start.py`, `tests/test_policy_skill.py`, `tests/test_evals_shape.py`, itself). It builds its tokens by concatenation (`"herdr" + "-orchestration"`), so it never matches itself. It asserts none of the walked files contains `herdr-orchestration`, `herdr agent start`, `herdr-watcher`, `HERDR_ENV` or `herdr --skill`. It also asserts on parallel-work: it contains `~/.herdr/worktrees`; it no longer contains `**worktree**, always`; and its `### A second agent` section contains `urgent`.

  Run `bash plugins/netdust-gates/tests/run.sh`. Expected: FAIL on both files.
- [ ] **Step 2:** Rewrite the policy's Execution mode paragraph. Inside hc (`HC_TERMINAL_ID` set), the pair recipe in `netdust-core:hc-orchestration` starts the coder with `hc run`, in the project's checkout on `feature/<feature>`, and the pair runs in auto mode; outside hc, one background subagent there; a worktree only for urgent parallel work (`netdust-devops:parallel-work`). The policy stays under 150 lines.

  Then update parallel-work:
  - the description names `hc --skill` for terminal syntax
  - the second-agent row and `### A second agent`: a coder holds the checkout and other work waits, unless urgent → worktree under `~/.herdr/worktrees`
  - the "Two agents pointed at one directory" anti-pattern row says the same
  - the DDEV section stays, scoped to that urgent worktree
  - See also names `hc --skill` and `netdust-core:hc-orchestration`

  Run the gates tests. Expected: PASS. Then `python3 plugins/netdust-gates/evals/run-evals.py two-session-handoff coder-brief-no-recursion small-tweak-no-artifacts`. Expected: 3/3 green; a red case is a signal to tighten the skill, as the runner says. Run the gate line. Expected: exit 0.
- [ ] **Step 3:** Commit (`hc-flow: policy and parallel-work start the coder through hc, no default worktree — spec R2, R6`).

### Task 5: Release and the CLAUDE.md proposal

**Files:**
- Modify: `plugins/netdust-core/.claude-plugin/plugin.json` (→ 0.6.0), `plugins/netdust-gates/.claude-plugin/plugin.json` (→ 0.14.0), `plugins/netdust-devops/.claude-plugin/plugin.json` (→ 0.9.7), `.claude-plugin/marketplace.json` (the same three versions, each description prefixed with its one-line entry)
- Create: `specs/hc-flow/claude-md.diff` (a unified diff against `~/.claude/CLAUDE.md`: §1's old-names line maps `herdr`-era names to `netdust-core:hc-orchestration`; §2's coder sentence reads "in the project's checkout (a worktree only for urgent parallel work, under `~/.herdr/worktrees`) … started through netdust-core's pair recipe in hc"). Stefan applies it; the coder never edits `~/.claude/CLAUDE.md`.

- [ ] **Step 1:** Run `bash plugins/netdust-devops/tests/test-marketplace.sh`. Expected: PASS before the change (baseline).
- [ ] **Step 2:** Bump the versions and descriptions, and write the diff. Check it applies cleanly with `patch --dry-run ~/.claude/CLAUDE.md < specs/hc-flow/claude-md.diff`. Expected: no rejects. Run test-marketplace and the gate line. Expected: both exit 0.
- [ ] **Step 3:** Commit (`release: netdust-core 0.6.0, netdust-gates 0.14.0, netdust-devops 0.9.7 — the hc flow`). Push `feature/hc-flow` and report to the reviewer (Close per policy).

## After the merge — operational checklist (reviewer with Stefan, not the coder)

1. `bin/hc-templates` locally on WSL; `bin/hc-templates --on netdust-web` once netdust-web is added (spec R3).
2. `hc machine add netdust-web` on the WSL core and on the Windows core. Stefan answers any install prompt (spec R8).
3. One space per active project on the `wsl` machine (`herdr-app do space.new --machine wsl --name <p> --folder <path>`), with Stefan naming the list (spec R1).
4. Stefan applies `specs/hc-flow/claude-md.diff`.
5. The `~/Sites` cleanup: list each worktree with its branch, unmerged commits and dirty state. Push or pin (`refs/recovery/<name>`), then remove only what Stefan approves, one by one (spec R9).
6. `./scripts/sync.sh` after the push, so the plugin caches carry the new versions.
