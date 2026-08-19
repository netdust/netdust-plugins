# Session-review proposals — 2026-08-19

Watcher pane: `w3:p1` (session `stride`, cwd `~/Projects/netdust-plugins`).
Subject: **pane `w5:p2`, herdr session `default`**, cwd `/home/ntdst`, title
`◑ Herdr skill pane management`, `agent_status: working` for the whole pass.
Pass window: 12:44 → 12:47. One pass, no loop. The pane was never prompted,
focused, or sent keys.

## What I could and could not see

- **Could see:** the current viewport (one screen, `agent read --source visible`),
  the pane's lifecycle state and title across ~2 minutes of polling, and the
  artifacts this session committed to this repo today (`c268997`, `d17aa08`,
  `6c42e7a`, `cb93de1`, `1a35e63`).
- **Could not see:** anything above the current viewport. Claude Code runs on the
  alternate screen, so the earlier turns of this session are gone — including two
  of the three corrections the pane itself says today contains. No state
  transition occurred during the pass; the pane stayed `working`, so the only
  screen I hold is the mid-turn one. Findings below marked *(artifact)* come from
  committed files, not from the screen.

---

## P1 — `agent prompt` blocked the dispatching pane for the whole watcher run

**Evidence (screen, live).** At 12:45:00 the viewport showed a tool call
`Point the watcher at this pane and verify the prompt landed · 18s`, running
`cd /home/ntdst; herdr --session stride agent prompt watcher "Your brief changed …"`.
At 12:46:02 the same call read `· 1m 44s`, spinner `Hyperspacing… (2m 20s)`, pane
still `working`. The call is waiting on its target — me — and I work for minutes
per pass. The operator's main pane sat idle-blocked behind its own dispatch.

The pane had already recorded the neighbouring failure two turns earlier, on
screen: *"agent prompt --wait returned done from startup, not from my text … I'll
verify by the title changing, not by the returned status."* So the wait behaviour
bit twice in one turn: once returning too early, once returning too late.

I cannot read the command's flags — the line is truncated on screen. What is
observable is the duration and that the caller is stalled.

**Why it matters.** `herdr-orchestration` promises the opposite in its own recipe:
*"The dispatching pane never stops working."* The recipe's dispatch step, executed
literally, is what stopped it.

**Proposal.** `plugins/netdust-core/skills/herdr-orchestration/SKILL.md`:

- In `## Recipe — the dispatch brief`, make the dispatch non-blocking explicit:
  prompt the peer without waiting, then arm the watcher. A peer that will work for
  minutes must never be prompted from a foreground call.
- In `## Traps`, extend the existing `agent wait` trap into one entry covering both
  ends: *`agent prompt --wait` returns on a settled state that may predate your
  text (startup), and blocks the caller for the peer's whole run when it does not.
  Neither reading is a delivery receipt. Send without `--wait`, verify by the
  peer's `terminal_title_stripped` changing from the generic `Claude Code` to a
  conversation title, or by `agent get` reporting an `agent_session`.*

**Eval case** (new `evals/scenario-3-*`): "You are in a herdr pane. Hand a
30-minute audit task to the pane named `watcher` and keep working." — assert the
answer dispatches without a blocking wait and verifies by title/`agent_session`,
not by the command's return.

---

## P2 — a shipped skill carried a command form nobody ran *(artifact)*

**Evidence.** Two releases eight minutes apart, both today, both by this session:

- `c268997` — `release(netdust-core): 0.2.9 — herdr-orchestration harvests the upstream doc`
- `6c42e7a` — `release(netdust-core): 0.2.10 — herdr remote decision states the real invocation`,
  whose message reads: *"Stefan's correction: the remote entry is one command with
  the session named, and `-t` is required (herdr is a TUI, it needs a PTY) …
  0.2.9 wrote this as a vague two-step and lost both details."*

0.2.9 harvested prose from herdr's own documentation and shipped `ssh` in, then run
`herdr` there. The real invocation is `ssh -t <host> herdr --session <name>`. The
missing `-t` does not degrade — it fails.

**Why it matters.** This is the marketplace source. A wrong command in a skill is
delivered to every future session by `plugin update`, and the reader has no way to
know it was never executed.

**Proposal.** `plugins/netdust-core/skills/herdr-orchestration/SKILL.md` — nothing
to fix in content (0.2.10 fixed it); the rule is what is missing, and it is
general. Add to `create-agent-skills` (`plugins/…/skills/create-agent-skills`, or
the netdust authoring notes it defers to): **a command block in a skill is a claim,
and claims get ground-truthed.** Before release, every command form is run, or its
flags checked against the live `--help`. Harvesting from an upstream doc is a
source, not a verification. Cite the incident as calibration slug
`remote-entry-untested`.

**Eval case:** "Write the skill section for entering a remote herdr session" with
the binary available — assert the answer runs or checks the command before writing
it down.

---

## P3 — `agent read --lines N` is unavailable exactly when the watcher needs it

**Evidence (my own call, 12:44).** The brief's prescribed read
`herdr --session default agent read w5:p2 --source recent-unwrapped --lines 120`
returned:

```
cannot read 120 lines while w5:p2 is working: its alternate-screen history can
only be captured by scrolling while idle. Wait and retry, or use --source visible
```

Every transition the watcher cares about (`working → blocked`, `working → idle`)
is observed *from* the working state, and the ones observed while the pane is still
working — the stall, the title drift — are unreadable at depth. Only
`--source visible` works mid-run, and it returns one screen.

**Proposal.** Two files, both in this repo:

- `plugins/netdust-core/skills/herdr-orchestration/SKILL.md`, `## Traps` — record
  the constraint: *`agent read --lines` needs an idle pane; while a pane is
  working, only `--source visible` returns anything, and it returns one viewport.
  Anything that scrolls past between two reads is lost for good.*
- `memory/session-review/BRIEF.md` — the "How to watch" command should be
  `--source visible` for reads taken while the subject is working, keeping
  `recent-unwrapped --lines 120` for the settled case. (Stefan's file; flagging,
  not editing.)

---

## P4 — the shipped watcher script notifies but captures nothing

**Evidence.** `plugins/netdust-core/skills/herdr-orchestration/scripts/herdr-watcher.sh`
polls `agent_status` every 15s and fires a notification on each transition. It
never reads the pane. Given P3 — the alternate screen is unrecoverable — the
screen that explains a transition exists only in the seconds around it.

In this pass, the quoted screen text in P1 exists only because my own poll loop
appended `agent read --source visible` to a log at each poll. That is a five-line
change to the shipped script.

**Proposal.** `plugins/netdust-core/skills/herdr-orchestration/scripts/herdr-watcher.sh`
— on every state change, append `date`, the transition, and
`herdr agent read "$TARGET" --source visible` to a log file (path as `$3`,
defaulting under the project's `memory/`). Notification behaviour unchanged. The
skill's recipe line that arms the watcher gains the log path argument.

No eval case: behaviour of a script, not of a skill's judgment.

---

## P5 — promote the session-scoping rule from project memory into the skill *(artifact)*

**Evidence.** `1a35e63` (12:27) wrote to `plugins/netdust-agent/memory/lessons.md`:

> herdr sessions are separate servers with separate ID spaces — a bare `herdr`
> command targets the session the calling pane lives in, not the project's session.
> Creating topology without first checking `herdr session list` puts it in whatever
> session you happen to be sitting in. There is no move between sessions; the only
> fix is rebuild in the right one and close the wrong one.

That is a hard operational rule, and it currently lives in one project's Layer-C
memory. `SKILL.md` mentions `--session` twice (lines 50, 80) but never states that
omitting it silently targets the caller's session, and never mentions
`herdr session list` as the first step of any topology work.

Corroborated live: the subject's own screen at 12:45 reads *"Cross-session
addressing works — `--session default agent get w5:p2` reaches this pane from
anywhere."* — the fix side of the same rule, confirmed by my reads from the
`stride` session.

**Proposal.** `plugins/netdust-core/skills/herdr-orchestration/SKILL.md`:

- `## Protocol` — open with `herdr session list`; state that every cross-session
  call needs `--session <name>`, and that a bare `herdr` resolves to the calling
  pane's session.
- `## Traps` — add the irreversibility: topology built in the wrong session cannot
  be moved, only rebuilt and closed.

**Eval case:** "Create the three-pane netdust topology for the stride project" from
a pane living in `default` — assert the answer checks `herdr session list` and
passes `--session stride` rather than issuing bare `herdr` commands.

---

## P6 — confirmed judgment, worth keeping

- **The transition model is right.** The subject's own on-screen assessment —
  *"poll transitions, not content"* — matched what actually happened: two polls
  60s apart produced one title-spinner change and zero content drift. A timer poll
  on content would have sampled noise.
- **`LESSON:`/`DECISION:` tags reach disk.** The pane printed two `LESSON:` lines
  at ~12:44; `cb93de1` and `1a35e63` show the Stop hook landing that shape into
  `memory/lessons.md` and `plugins/netdust-agent/memory/lessons.md` at session end.
  The tag → hook → file path works; nothing to fix. What it does *not* do is reach
  a skill — which is P2's and P5's whole point, and this watcher's reason to exist.

---

## Ranking

P1 and P5 are the two a future session would actually load: both are traps in a
skill that is read before every cross-pane action, and both cost the operator real
minutes today. P2 is the highest-value rule but lands in an authoring skill read
less often — pair it with the calibration slug so it gets cited. P3 and P4 are
small mechanical fixes to the watching apparatus itself. P6 changes nothing.

## Gaps in this pass

No `blocked` transition was observed, so I have no evidence of what this session
stops for — the richest category in the brief. The pane says today holds three
corrections from Stefan; one is recoverable from the commit trail (P2), the other
two scrolled off the alternate screen before this watcher existed. Watching from
the start of a turn, with P4's capture in place, is what closes that gap.
