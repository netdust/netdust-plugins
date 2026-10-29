# Plan review — hc-flow (confirmation)
Reviewed-plan: 7b34a92ef85d4105a9a564303419b5d470c3338a
Verdict: ready

I confirmed that the file on disk hashes to 7b34a92e…. Blob f834e63 is not in the object store, so I checked the two described fixes against the current text. I did not diff the blobs.

## Blocking
None.

## Should fix
None.

## Note
- **S-3rd-1 is resolved.**
  - Task 2 Step 2 (plan:121-128) now stops at the shape test and the gate line. Its last sentence is: "(The three behavioural cases run in Task 4, once the policy and the skill teach hc.)"
  - Task 4 Step 2 (plan:183) now runs `python3 plugins/netdust-gates/evals/run-evals.py two-session-handoff coder-brief-no-recursion small-tweak-no-artifacts` after the policy and parallel-work rewrites. Expected: 3/3 green.
  - That run comes after Task 3 (the skill) and the Task 4 policy edit, so the order is right.
  - `run-evals.py:244` (`chosen = [c for c in CASES if not argv or c["id"] in argv]`) accepts several ids, so the command works as written.
- **N-3rd-1 is resolved.** Task 2's Interfaces (plan:104) now says: "`get t1` answers with `labels: {"herdr.space": "s1"}`". This matches the R5 recipe in Task 3 (plan:143), `--label herdr.space=<own space label, machine prefix stripped>`. `s1` has no machine prefix, so the stub's answer is usable as given.
- **Nothing else broke.**
  - Test map row 3 (plan:57) still lists the three behavioural cases, and they now run in Task 4. That is consistent, because they exercise the skill as the policy wires it.
  - Row 2's command (`run.sh test_evals_shape.py`) is still the only proof Task 2 runs.
  - Review Focus lines 1–6 still point at existing rows.
  - Task 4 Step 1 still expects FAIL and Step 2 expects PASS.
  - The Global Constraints and the threat-model mitigations are unchanged and still have a home in row 1 and row 2.

## Premises checked
- run-evals.py takes several case ids as positional args → plugins/netdust-gates/evals/run-evals.py:244 → holds
- The three behavioural cases run only after the policy and skill teach hc → plan:128, plan:183 → holds
- The stub's `get t1` carries a `herdr.space` label for the pair recipe → plan:104 against plan:143 → holds

---

# Plan review — hc-flow (third review)
Superseded review of blob f834e63267d8682757933c71867a225276f26a74
Verdict: ready with fixes

All the fixes and rulings checked hold. One new defect: a planned "Expected: 3/3 green" could not pass where the plan put it. Nothing Blocking.

## Should fix

**S-3rd-1. Task 2 Step 2 runs the three behavioural cases before the policy and the skill teach hc, so `two-session-handoff` cannot go green there.**
- The policy loads from source (`--plugin-dir`, run-evals.py:190). Until Task 4 its Execution mode still sends the session to `herdr agent start` (policy SKILL.md:100-102).
- The converted case sets only `HC_TERMINAL_ID`, `child_env` strips `HERDR_*`, and `Bash(herdr*)` is denied. The skill that teaches `hc run --bg --outlive-parent … coder` only arrives in Task 3.
- So `(?m)^run .*--outlive-parent` and `.hc/run-coder` = `coder` are missing, and the case fails. The other two cases pass, but only trivially.
- **Smallest change:** run only the shape test plus the gate line in Task 2 Step 2, and move the `run-evals.py` command and its "Expected: 3/3 green" to Task 4 Step 2, after the policy rewrite.

## Note

**N-3rd-1. The stub's `get` response needs a `herdr.space` label.** The reviewer reads its space id from `hc get $HC_TERMINAL_ID` (R5, Task 3). If the stub's `get` for `t1` returns no `labels: {"herdr.space": …}`, the session may stop or ask instead of running `hc run`, and the case would fail for a reason outside the skill. Say in Task 2's stub bullet that `get` answers with a `herdr.space` label (e.g. `s1`).

Status of earlier findings: S-new-1 through S-new-5 and N-new-1, 2, 4, 5, 6 resolved; N1, N4, S-new-2 and N-new-3 resolved by Stefan's rulings (spec R3, Settled facts).

---

# Plan review — hc-flow (second review)
Superseded review of blob 969cb43b11fd4494488c58dc0288e3591cf215d3
Verdict: ready with fixes

Nothing is Blocking. Every fix from the first review holds, except that part of S3b changed one case's meaning. The revision also brought in four new defects, all Should fix. Each one would turn a planned "Expected: PASS" red, or leave a check that cannot fail. I ran the Task 1 report proof myself in a scratch session (`HC_SESSION=rv`, `/tmp/hcXXXX` XDG dirs, stopped and removed afterwards; the default session was not touched). It passes, with one caveat in N-new-1.

## Status of the first review's findings

- **B1:** resolved. The live eval case is gone and `test-hc-report.sh` replaces it. The plan states this as a deviation from the spec's "one opt-in live case" under Simplest design, for Stefan to rule on (see Note N-new-3).
- **S1:** resolved. Task 4 Step 1 skips `__pycache__/`, `plugin.json`, `evals/stubs/` and the tests that assert absence, and builds its tokens by concatenation. A grep of the three plugins finds the forbidden tokens only in files the plan rewrites, deletes or exempts.
- **S2:** resolved in scope. The description (:3), `### A second agent`, the anti-pattern row (:152) and See also are all named. But one of the new assertions cannot fail; see S-new-3.
- **S3a, S3c, S3d:** resolved. The case uses a marker file `.hc/run-coder`, sets `"branch": "feature/greeting"` (run-evals.py:133 reads `case.get("branch")`), and names the `.git/info/exclude` and `stray_worktrees` changes.
- **S3b:** the allow list and the env are given, but dropping the env from `small-tweak-no-artifacts` weakens that case; see S-new-4.
- **S4:** resolved (the check is filesystem only).
- **S5:** resolved. The plan now has a `## Threat model`, Review Focus 6 and the verbs in `DISALLOWED`, and Review Focus 2 now says Bash writes are not enforced.
- **S6:** resolved. The judge procedure is written into row 3, and `evals/README.md` is in Task 3's Files.
- **N2, N3, N5, N6, N7:** addressed.
- **N1, N4:** still open, as you asked. N4 now also breaks a test; see S-new-2.

## Blocking

None.

## Should fix

**S-new-1. Task 3 and Task 2 contradict each other: if the brief goes in a file, `two-session-handoff` cannot pass.**
- **Task 3, R5 bullet:** "The brief is a file in the reviewer's scratchpad, pointed at." This is unconditional.
- **Task 2 Step 2:** expects `specs/greeting/plan\.md` and `netdust-gates:policy` in `.hc/calls.log`. The stub logs only argv (`printf '%s\n' "$*"`, as `stubs/herdr` does today). If the skill teaches pointing at a file, the argv holds a scratchpad path and both expectations fail.
- **Old skill:** the herdr-orchestration SKILL.md:188-190 made the file conditional: "A **long** brief is a file in your own scratchpad".
- **hc's manual:** the trap the plan itself quotes says "put the task in `run`".
- **Smallest change:** in Task 3, the `hc run` task carries the plan path, the branch and `netdust-gates:policy` inline, and only extra context goes in a file that the task points at.

**S-new-2. Task 2 never mentions the shape test's permission-mode rule, so Step 2's "Expected: PASS" fails.**
- **The rule:** test_evals_shape.py:258-260 requires that `two-session-handoff` has an `expect` on `.herdr/calls.log` whose match contains `--permission-mode` ("the coder started in the thinker's permission mode (R4)").
- **Why it fails:** Task 2 Step 2's new expect list drops it. The template hardcodes `--permission-mode auto` (Task 1), so the `hc run` argv carries no mode. Step 1's bullet list does not mention this rule.
- **Smallest change:** add a bullet to Step 1 that says what happens to this rule. Either delete it (if Stefan rules N4 as "the pair always runs in auto"), or rewrite it for `.hc/calls.log` with a mode passed in from the reviewer. This finding is tied to the N4 ruling, so the ruling has to come before Task 2.

**S-new-3. Task 4 Step 1: the assertion "no longer contains `worktree, always`" is vacuous.**
- **Why:** the source line is parallel-work/SKILL.md:78, `Edits anything → **worktree**, always.`, so the literal substring `worktree, always` does not occur today. The assertion passes before and after the change and guards nothing.
- **Smallest change:** assert the absence of `**worktree**, always`, or strip `*` before matching.

**S-new-4. Task 2 Step 2: removing the env from `small-tweak-no-artifacts` makes its check trivially true.**
- **Today:** the case runs with `HERDR_ENV=1` and is `absent` `.herdr/agent-start` (cases.json). It proves that a small tweak does not start a coder even when the session *could*.
- **After the plan:** "`small-tweak-no-artifacts` gets none, since it has no pair" leaves the session outside hc, where the policy never calls `hc run` anyway. So `absent .hc/run-coder` passes whatever the skill says.
- **Smallest change:** give all three cases `{"HC_TERMINAL_ID": "t1"}`.

**S-new-5. Task 1, the `coder.md` body skips the first-working-version report.**
- **Plan line 74:** "report to the parent with `hc send` at pre-flight, at a block, and at Close".
- **What expects it:** spec R5 lists "reviews at the first working version / a block / Close", policy SKILL.md:105-106 says the same, and Task 1 Step 3 itself relies on the coder sending "the first-working-version checkpoint".
- **Smallest change:** add "at the first working version" to the body list. Optionally, the template test could also assert that phrase.

## Note

**N-new-1. Task 1 Step 1, `test-hc-report.sh`: the "exit note" it asserts is the output of the wait, not a note.**
- **Source:** hc types notes only into a parent that reports status: notes.rs:56 `can_take_note` requires `t.reported`, and m6.rs:317 is `no_notes_into_programs_that_are_not_agents`. A plain `bash` parent never reports.
- **My scratch run:** the parent screen read `t2 started` / `review-done-42` / `t2 exited (exit 0, turn 0)` / `WAIT-RC=0`. The `exited` line is printed by `hc wait --children any` in the parent. The parent also received `hc send` untagged (notes.rs:139-160: no `<hc from=` unless both sides report).
- **Effect:** the test passes if it matches `exited`. It fails if the coder matches hc's note form `<hc>… exited`.
- **Change:** word the assertion as "the wait's `exited (exit 0` line", and don't claim it proves tagging.

**N-new-2. Task 2, `two-session-handoff`: `(?m)^run .*coder` also matches `--name greeting-coder`.**
- It does not prove the `coder` template was used, and `.hc/run-coder` cannot be checked through `expect` (`_subject` returns "" for a missing file, so an empty match passes).
- **Change:** have the stub write the template name into `.hc/run-coder`, and expect `^coder$` there.

**N-new-3. Simplest design, second bullet: dropping the live eval case reverses an approved spec call.**
- The spec's Settled facts say "One opt-in live case runs a real core …". The reason for dropping it holds: a `claude -p` parent is not a reporting terminal (client.rs:249-253; notes.rs:56).
- Like N1, it needs Stefan's explicit ruling at approval, not just a mention. The plan does list it for him.

**N-new-4. Task 4 Files: the decision-table row numbers are off.** The rows are at parallel-work SKILL.md:14-19 (agent rows 18-19), not 16-18, and the anti-pattern row is at :152, not ~:155. The "pane/tab/workspace wording" clause covers them in practice.

**N-new-5. `coder-brief-no-recursion`'s prompt still says "this checkout is your worktree".** Under R6 that wording is stale. The shape rule at test_evals_shape.py:261-263 checks only `Role: coder`, `Plan:` and `Entry:`, so rewording the line is free.

**N-new-6. Threat model mitigation "core tests use only scratch sessions, never a bare `hc` (→ row 1)": row 1 has no check for it.**
- Only the check on the real templates dir's mtimes is indirect evidence.
- **Cheap guard:** each `test-hc-*.sh` refuses to run unless `HC_SESSION` and `XDG_RUNTIME_DIR` are the scratch values.

**N1 and N4** (from the first review) still need Stefan's ruling at approval. N4 now decides S-new-2.

## Premises checked

- `hc run --bg --outlive-parent --name --cwd --label --parent` → `hc run --help` → holds
- `hc wait --children any|all` defaults to the caller → `hc wait --help` → holds
- `hc events --children-of`, `--label` → `hc events --help` → holds
- `hc read --lines`, `hc ls --all` shows `parent` → `hc read --help`; scratch run (`"parent":"t1"`) → holds
- `hc file write --on <m> <rel>` is relative to the remote home → `hc file write --help` → holds
- template header is line-based, `command` required and run through `sh`, the body is the opening message → src/docs/templates.md → holds
- the only extra way to reach a session is `hc connect --session`, covered by `Bash(hc connect*)`; `HC_SOCKET` is stripped by `HC_*` → cli.rs:101-106, paths.rs:27-28 → holds
- bash parent → child `hc send` → `hc wait --children any` returns 0 → scratch run 2026-10-29 → holds
- the bash parent receives the child's "exit note" → notes.rs:56, m6.rs:317 → does not hold as a note; the line comes from the wait output (N-new-1)
- `branch` case key lands the sandbox on `feature/greeting` → run-evals.py:133 → holds
- `absent` is a glob, so a marker file is needed → run-evals.py:182-187 → holds (marker used)
- `.git/info/exclude` at :129 and `stray_worktrees` at :155-158 → run-evals.py → holds
- shape test printenv rule :255-257 and "no case allows every verb" at :266 → test_evals_shape.py → holds
- the shape test's permission-mode rule is handled → test_evals_shape.py:258-260 → does not hold (S-new-2)
- the three stubbed cases carry the `HERDR_ENV` env and the herdr allow lists → cases.json:83, 345, 399 and the allow blocks → holds
- policy at 149 lines, `< 150` enforced → `wc -l`; test_policy_skill.py:43 → holds
- policy Execution mode names `HERDR_ENV=1`, `herdr agent start` → policy SKILL.md:94-107 → holds
- `test_policy_skill.py:52-54` token row → holds
- parallel-work description :3, `### A second agent` :75-79, anti-pattern :152, See also :159-169 → holds; the `worktree, always` literal does not hold (S-new-3)
- stale tokens appear only in files the plan rewrites, deletes or exempts → grep of the three plugins → holds
- the old brief was a file only when long → herdr-orchestration SKILL.md:188-190 → holds; the plan makes it unconditional (S-new-1)
- versions 0.5.4 / 0.13.1 / 0.9.6 → plugin.json files → holds
- `plugins/netdust-core/tests/` and `bin/` are new → absent → holds
- `herdr-orchestration/` holds the SKILL, `references/session-review.md`, `scripts/herdr-watcher.sh` and its evals (spec R2) → directory listing → holds; deleting the whole directory covers R2

---

*The first review (blob ecd789f…, verdict not ready: B1, S1–S6, N1–N7) is appended below for the record.*

# Plan review — hc-flow
Superseded review of blob ecd789f139e73bd56af369aeae7a90f25b183e19
Verdict: not ready

There is one Blocking finding. The live eval case R10 asks for cannot get a report the way the plan builds it. Everything else is a Should fix or a Note. The hc premises hold in hc 0.1.13 and its source: the flags, template format, XDG isolation, `file write --on` and the app labels.

## Blocking

**B1. Task 2 Step 2 and the Interfaces line about `--live-hc`: the `live-pair-report` case cannot get an `<hc from=` report.**
- **What the plan says:** "the case starts a `reviewer` child on `greeting.txt` and must quote the child's `<hc from=` report in its reply". The case's parent is `claude -p` from `run-evals.py` `claude_args()`, through `spawn()` at run-evals.py:162-171. That is not an hc terminal.
- **Why that fails:**
  - hc learns who called only from `HC_TERMINAL_ID` (client.rs:249-253 `terminal_id()`).
  - The plan's `child_env` strips every inherited `HC_*`, so the child has no parent.
  - With no parent, the reviewer template's `hc send $parent` has nowhere to go.
  - hc's notes and `<hc from=…>` tags are typed into the parent's terminal. A `-p` session has no terminal to type into (hc-skill.md:85-98).
  - `hc wait --children` defaults to "the caller" (`hc wait --help`), and here there is no caller.
  - So R10's settled call, "prove a parent→child report end to end", has no working task.
- **Smallest change:** state that for a `live_hc` case the runner starts the parent itself as an interactive Claude inside the scratch core: `hc run --bg --name parent --cwd $root -- claude …` with the case's args. It then collects with `hc wait parent` and `hc read parent --lines N`, and the regexes match against that read, not against `proc.stdout`. Also say how that parent claude gets the case's `--restricted` / `--settings` / `--plugin-dir` args (see S5).

## Should fix

**S1. Task 4 Step 1, `test_hc_wiring.py`: the wiring test fails on files the plan itself writes.**
- **Problem:**
  - It walks "every file under" the three plugins and exempts only `tests/test_session_start.py`.
  - The new `test_hc_wiring.py` contains all four forbidden tokens.
  - The new `test_policy_skill.py` row asserts `"herdr agent start"` and `"HERDR_ENV"` are absent, so it contains both strings literally.
  - The rewritten `test_evals_shape.py` must still feed an inherited `HERDR_*` env to prove `child_env` strips it. Today that is the `LIVE` dict at test_evals_shape.py:26, with `"HERDR_ENV": "1"`.
  - `plugins/netdust-gates/tests/__pycache__/` and `evals/__pycache__/` hold stale `.pyc` files with these strings.
- **Smallest change:** exempt the tests that assert absence (or build the tokens by concatenation), skip `__pycache__/`, and read text files only.

**S2. Task 4, parallel-work: the plan's file list leaves herdr-TUI rules that contradict R6 and R2.**
- **Problem:** Task 4 changes only "decision table rows 16–18, the DDEV section, See also". These lines stay:
  - The description, `parallel-work/SKILL.md:3`: "for terminal syntax run `herdr --skill`".
  - "### A second agent" at :75-79: "Edits anything → **worktree**, always."
  - The anti-pattern row ~:155: "Two agents pointed at one directory | one of them gets a worktree".
  - The pane/tab/workspace wording throughout, which is TUI vocabulary.
- R2 says parallel-work "reference hc only".
- **Why the test misses it:** the forbidden tokens don't include `herdr --skill`. The assertion "does not prescribe a worktree for 'a second agent that edits' when the first agent is a coder" has no threshold you can check.
- **Smallest change:**
  - Add these three places to Task 4's Files and Step 2.
  - Make the test assert that `herdr --skill` is absent from parallel-work and that "worktree, always" is gone.
  - Make it assert that the "A second agent" section names `urgent`.

**S3. Task 2 Step 2: the case conversions use runner features that don't exist, and leave the permissions unstated.**
- **(a) `absent` is a file glob, not a regex.** The plan writes "`absent` `.hc/calls.log` lines matching `^run `" and "`absent` `^run .*coder` in `.hc/calls.log`". But `absent` goes through `found()` → `root.glob(pattern)` (run-evals.py:182-187). Today's design uses a marker file the stub writes (`.herdr/agent-start`, cases.json:80). **Fix:** have the stub touch a marker (e.g. `.hc/run-coder`), or use a negative-lookahead `expect` like the existing greeting.txt one.
- **(b) The three cases keep their herdr `allow` lists, env and `printenv` rule.**
  - The plan doesn't name the hc `allow` list. Today it is `Bash(herdr agent start*)` … `Bash(printenv HERDR_ENV)` (cases.json:86-111 and 348-373).
  - It doesn't swap `"env": {"HERDR_ENV": "1"}` for `HC_TERMINAL_ID`.
  - Under `-p` with `autoAllowBashIfSandboxed: False` (run-evals.py:38-39), every `hc` call is denied unless allowed, so the cases fail for the wrong reason.
  - The shape test's printenv rule (test_evals_shape.py:255-257) and "no case allows every verb" rule (:266) also need their hc versions.
  - **Fix:** list the per-case allow set (e.g. `Bash(hc run*)`, `Bash(hc get*)`, `Bash(hc wait*)`, `Bash(hc send*)`, `Bash(hc read*)`, `Bash(hc templates*)`, `Bash(hc --skill*)`, `Bash(printenv HC_TERMINAL_ID)`), and give the env change.
- **(c) The `.git/HEAD` expectation cannot pass.** "expect `.git/HEAD` to match `feature/greeting`" fails because `prepare_sandbox` checks out `feature/{case id}` = `feature/two-session-handoff` (run-evals.py:132-133), and `git checkout`/`switch` aren't allowed. **Fix:** set `"branch": "feature/greeting"` on the case.
- **(d) Small omissions:** `prepare_sandbox`'s `.git/info/exclude` (run-evals.py:129) still lists `.herdr/` and needs `.hc/`. `stray_worktrees` (run-evals.py:155-158) still exempts `.herdr/wt`, and the plan's "absent any worktree" needs that exemption removed. Name both in the step.

**S4. Task 1 Step 1: the "live default session's `hc ls` is byte-identical" check is flaky and can start Stefan's default core.**
- **Problem:**
  - `hc ls` runs through `connect_or_start` (cli.rs:226; client.rs:73-95). With the env unset and no default core running, it **starts the default core**, which the plan's own Global Constraint forbids ("never touches the default session").
  - With Stefan's core live, `hc ls` shows agent states that change between the two calls, so byte equality fails at random.
- **Smallest change:** check only the filesystem. The real `~/.config/herdr-core/templates/` listing and mtimes stay unchanged, and the scratch templates dir holds the three files.

**S5. Task 2: the live case and the templates run agents outside every eval guard, and the plan has no `## Threat model`.**
- **Problem:**
  - `run-evals.py` builds its whole permission boundary in `claude_args()`: `--restricted`, deny list, bwrap `SANDBOX`, and no user settings (run-evals.py:174-180). The plan changes that boundary through `DISALLOWED` and `child_env`.
  - In the live case, the `reviewer` child runs the template command `claude --model opus --permission-mode auto --disallowedTools Edit Write NotebookEdit`. That loads Stefan's `~/.claude` settings, plugins and hooks, without `--restricted` or the sandbox, in auto mode. Bash writes are still allowed.
  - Any process the scratch core runs (`hc run <cmd>`, `hc exec`) runs outside Claude's bwrap sandbox.
- The policy's security-boundary rule covers "permission checks" (policy SKILL.md:46-49).
- **Smallest change:**
  - Add a short `## Threat model` covering the escape paths: the child's settings, `hc exec`, and `hc run <arbitrary cmd>`.
  - Write a scratch-only reviewer template whose command carries the eval's restricted args.
  - Allow only `hc run --bg * reviewer *`, `hc wait*` and `hc read*` in the live case; deny `hc exec*`, `hc file*`, `hc put*` and `hc keys*`.
  - Add a Review Focus line for it pointing at Test map row 2.
- **Related:** Review Focus 2 ("a reviewer edits the tree") is tested only by the string check in row 1. `--disallowedTools Edit Write NotebookEdit` leaves Bash writes possible, so say "read-only by tool list, not enforced", or add a Bash-write deny.

**S6. Test map row 3 / Task 3 Step 1: the command named is not runnable for these files.**
- `plugins/netdust-core/evals/RUNBOOK.md` is the runbook for a different eval: 8 scenarios generated from `~/Sites/netdust-wp-manager/tasks/eval-rubric.md` by `run-eval.py --prepare`. It does not describe `skills/*/evals/scenario-N-{baseline,skill-on,judge.template}.md`. The old herdr-orchestration judge templates say "inline both legs' outputs before dispatching the judge".
- **Smallest change:** write that procedure into the row: dispatch each leg as a general-purpose subagent, inline both outputs into the judge template, score PASS/FAIL per rule. Add `evals/README.md` to Task 3's Files, since Step 2 writes it.

## Note

**N1. Simplest design, the `gate` role is not a template.** This contradicts spec R3 ("Each role … is one template: at least … `gate`"). The reason holds against the source: hc-skill.md:105 says "background server; exit comes as a note", and `hc read gate` gives the output. Because it reverses an approved requirement, it needs Stefan's explicit ruling at plan approval, not just a mention.

**N2. Task 1 Step 3, the live proof.** The spec's fallback ("If it fails … start every agent through the Windows core with `--on wsl`") is missing from the plan. Say which tasks change if the proof fails (the skill's `## Machines` and the pair recipe in Task 3).

**N3. Global Constraints line 21 says the coder never runs `hc server`.** But Global Constraint 4, the Task 1 test and the Task 2 runner all run `hc server stop` against the scratch session. Reword it to "never against the default session".

**N4. Task 1, `coder.md` hardcodes `--permission-mode auto`.** The policy's Execution mode says "both in one permission mode" (policy SKILL.md:101). If the reviewer runs in another mode, the template breaks that rule. Either document that the pair always runs in auto, or pass the mode in from the reviewer.

**N5. Task 2, the live case under Claude Code's bwrap sandbox.**
- The plan's scratch XDG dirs live under `/tmp/hcXXXX`. That is outside the sandbox's writable paths (cwd and `$TMPDIR` = `root/.tmp`, run-evals.py:111-112).
- Unix-socket connects from sandboxed Bash may also be blocked.
- If the runner starts the core outside the sandbox (B1's shape), check at execution time that the client can still reach the socket.
- **Possible simplification:** put the XDG dirs under `root/.tmp` when that path is short enough (paths.rs:35-47 computes the limit).

**N6. Task 4, the policy is at 149 of 150 lines** (`wc -l`; test_policy_skill.py:42 requires `< 150`). The Execution mode rewrite has to come out at the same length or shorter.

**N7. Task 2 stub, the `run` JSON shape.** The real `RunResult` is the full public terminal record flattened, plus `first_message` (api/types.rs:745-758; terminals.rs:420). Copy the shape from `hc schema` rather than inventing a minimal one.

## Premises checked
- `hc` 0.1.13, `run --bg --outlive-parent --name --cwd --label` → `hc run --help` → holds
- template command runs from the core: `hc run reviewer "<task>"` / `<cmd>` → `hc --help` → holds
- `hc wait --children any|all`, `hc events --children-of` → `hc wait --help`, `hc events --help` → holds
- template header is line-based, `command:` required, body + appended task → docs/templates.md → holds
- `hc templates --json` exposes `command` (not body) → templates.rs:28-31 → holds (the body check must read the file)
- templates dir follows `XDG_CONFIG_HOME` → docs/templates.md "Setting XDG_CONFIG_HOME…"; paths.rs:22 → holds
- `hc file write --on m <rel path>` is relative to the remote home → `hc file write --help` → holds
- socket limit is 107 bytes; a custom `XDG_RUNTIME_DIR` stays off systemd → platform/unix.rs:83-93, systemd.rs:50-56 → holds
- a scratch-session `hc ls` cannot touch the default core → client.rs:73-95 (autostarts that session's core) → holds for scratch; the default-session `hc ls` in Task 1 does not hold (S4)
- `claude -p` can receive `<hc from=` reports → client.rs:249-253, hc-skill.md:85-98 → **does not hold** (B1)
- `run --bg <cmd>` exit arrives as a note to the parent → hc-skill.md:105 → holds
- app labels `herdr.space`/`herdr.tab`, strip the machine prefix, unknown id → new tab → app AGENTS.md:131-141 → holds
- `~/.herdr/worktrees/<repo>/<branch>` is the app's worktree location → app AGENTS.md:681 → holds
- `claude --disallowedTools`, `--permission-mode auto`, `--model opus` → `claude --help` → holds
- `stubs/herdr`, `child_env`, `stub_for`, `DISALLOWED`, the three stubbed cases → run-evals.py:49-118, cases.json → holds
- `absent` accepts a regex on a file's lines → run-evals.py:182-187 (glob only) → **does not hold** (S3a)
- case sandbox can land on `feature/greeting` → run-evals.py:132-133 → **does not hold** (S3c)
- policy Execution mode at ~95–107 names `HERDR_ENV=1`, `herdr agent start` → policy SKILL.md:94-107 → holds
- `test_policy_skill.py:52-54` token row → test_policy_skill.py:52-54 → holds
- parallel-work rows 16–18, DDEV section, See also → parallel-work SKILL.md:16-18, 81-121, 159-169 → holds; the description and :75-79, :155 are missed (S2)
- `plugins/netdust-core/tests/` and `bin/` are new → directories absent → holds
- `plugins/netdust-core/evals/RUNBOOK.md` runs skill judge templates → RUNBOOK.md:1-40 (a different eval) → **does not hold** (S6)
- versions 0.5.4 / 0.13.1 / 0.9.6 → the 0.6.0 / 0.14.0 / 0.9.7 bumps → plugin.json files, marketplace.json → holds
- `make review` does not write the coder's tree (the reviewer stays read-only) → dist/Makefile.netdust:225 (`git-common-dir/reviews`) → holds
- the only stale-token sources are the old skill dir, policy, parallel-work, gates evals and tests → grep of the three plugins → holds (plus `commands/session-review.md`, which is clean)
