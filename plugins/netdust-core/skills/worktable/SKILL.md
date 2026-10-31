---
name: worktable
description: "Use when a session works a planned feature (a `specs/<feature>/plan.md`) and the worktable MCP server is connected — its tools are schema, rows, create, update, action and history. Mirrors the plan into Studio: the feature (werkpakket) by repo and branch, each plan task as a Taak row, and every stop as a state change, so Stefan sees the fine-grained work on the Features board. Also when Stefan asks where a feature stands, what an agent is doing, or to sync, fix or catch up a feature's steps. Triggers on worktable, Studio, werkpakket, Features board, voortgang, plan steps, laatste stap, volgende stap. Not for theatre or fiche data, and not for the worker's Opdrachten."
---

# worktable — the plan, mirrored into Studio

`plan.md` is the truth; Studio mirrors it and may lag it. A session without worktable loses
nothing: the next session that has it catches the mirror up in one pass. So this skill never
blocks work, and it never invents state the plan does not hold.

## Is it here?

The session-start `Box:` line says `worktable ✓` or `✗` (`–` when `WORKTABLE_URL` is unset: set
it in the box's Claude settings `env` to the URL the MCP server's `--url` takes), and the worktable
MCP tools are listed or not. No tools, or a call that cannot connect: skip every step below, carry on, and say it once
in the final message ("worktable not reachable from this box; Studio catches up next local
session"). Never retry in a loop, never start the engine, never reach it another way: its MCP
server talks to loopback only, on purpose.

Call `schema` once per session before the first write: column and option names come from it,
not from memory. A refusal (422) says why in Dutch; read it, fix the call, never force it.

## 1. Find the feature

`rows` on `werkpakket`, filter `{ repo: <absolute repo path>, branch: <current branch> }`.
One row per repo and branch — the writer refuses a second. Missing: find the project
(`rows project` filtered on `repo`) and `create` the werkpakket with `naam`, `project_id`,
`branch`, `plan` (`specs/<feature>/plan.md`) and `fase`. No project for the repo: ask Stefan
which one, once, and stop syncing until he answers.

## 2. Sync the steps (at plan approval, and at every session start on a planned branch)

A plan step is a plan task: each `### Task N: <title>` heading in `plan.md`. Its label is
`Task N`, stored in the Taak's `stap` column — unique per feature, so a re-sync finds its row.

- `rows taak` filtered `{ werkpakket_id: <id> }`, limit 500.
- A task with no row: `create taak` with `titel` (the heading's title), `stap` (`Task N`),
  `werkpakket_id`, `wie: "claude"` and **no deadline** — a deadline puts it on Stefan's
  Op tafel and agenda. Create them in plan order, so the list reads in plan order.
- A changed title: `update` the `titel`. A task the plan dropped: `status: "overgeslagen"`,
  with why in `notities`. Never delete a row — an agent account cannot, and the history is the point.
- Tasks already done in git (their checkboxes ticked, or the commit is there) go straight to `gedaan`.

## 3. At every stop

A stop is a task started, a task finished, a block, and every checkpoint the policy names.

| Moment | Taak | Werkpakket |
|---|---|---|
| task starts | `status: "bezig"` | `volgende_stap` |
| task done | `status: "gedaan"`, `notities` one line: what changed, the commit's short sha | `laatste_stap`, `volgende_stap` |
| task blocked | `status: "geblokkeerd"`, `notities` the blocker | `fase: "geblokkeerd"`, `geblokkeerd_door` |
| block lifted | back to `bezig` | `fase` back, `geblokkeerd_door` emptied |

**Write the werkpakket last, every stop.** Its writer recounts `voortgang` ("14/32", done and
skipped over all) and stamps `bijgewerkt` on that write; both are read-only — never send them.

`fase` follows the policy: `ontwerp` (spec) → `plan` (plan and plan review) → `bouwen` (the
tasks) → `review` (Close: review, fix pass, shake-out) → `klaar` (promoted). `geparkeerd` is
Stefan's word, never yours.

## 4. At Close, before the hand-over

Read the feature's steps once more and compare them with the plan and git: every task done in
git is `gedaan`, every row still `open` or `bezig` has a reason. Name each mismatch in the
hand-over and fix it, or say why not. A box without worktable says so instead; it never fails the Close.

## Never

- Touch a Taak with `wie: "stefan"`, a deadline you did not set, or another feature's rows.
- Write `voortgang`, `bijgewerkt` or `organisatie_id` (the writers derive them).
- Mirror anything that is not in the plan: Studio shows the plan's work, not your scratch.
