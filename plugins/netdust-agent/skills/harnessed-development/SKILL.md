---
name: harnessed-development
description: The single entry point for any code-changing work in a Netdust project — an intake ROUTER that classifies the work (Class A–F) and routes it to `planning` or `building`, which overlay netdust gates on the superpowers workhorse skills. Triggers on "build a feature", "implement X", "ship X", "execute the plan", "work the plan", "fix this bug", "tweak X", "refactor this" (the deleted ntdst-execute-with-tests skill's triggers resolve here too, routed to `building`). The class dial scales ceremony to the work; use it for the tweak too — it routes the tweak light.
---

# Harnessed development — classify, route, done

Superpowers does the work; `planning` and `building` add the netdust gates. This skill
does exactly one job: state the class and the stakes in one sentence each, then route.
No stage work here.

## The class dial — priced by OPEN DECISIONS, not by files touched

| Class | Work | Route |
|---|---|---|
| **A** | new feature / multi-task change with real design decisions | `planning` → seam (human approves) → `building` |
| **B** | executing an existing written plan | `planning` in freshness-review mode → seam → `building` |
| **C** | bug-fix bundle from a review | `building` — one TDD cycle per behaviour finding |
| **D** | ad-hoc edit to a security-boundary file (auth/token/allow-list/crypto), even a one-liner | threat model on the diff, then `building` |
| **E** | small self-contained change — including **multi-file declarative config with no design questions** | `building` — one TDD cycle, no plan, no shake-out |
| **F** | vision-stage shaping, no code this session | `superpowers:brainstorming` only; notes at most, no artifacts |

Ask at intake: **would a competent human do this inside half an hour?** If yes, it is
Class E regardless of file count. Under-calling A/D (skipping a warranted plan or
security gate) is the dangerous direction; over-calling ceremony is how a config file
buys a three-hour session (calibration: `deliverable-last`). A security-boundary file is
always D, never E.

## The lane (decided per cluster, at plan time)

Class routes the work and stakes scales its verification; **the lane prices it.**
`planning` marks each cluster `Lane: behaviour` (config over a framework that already
has the rule — one cluster RED, bare tasks, no panel) or `Lane: contract` (a rule this
project chose — today's per-task grammar). `check_cluster_lanes` refuses `behaviour` on
a security-boundary path or under `high` stakes; nothing refuses `contract`, so
over-calling it is the cheap mistake and it merely warns. Class E work is behaviour-lane
by construction unless it touches a boundary file, which makes it D.

## The stakes dial (independent of class)

`Stakes: high | standard | low — <reason>`, by what a FAILURE costs: **high** — money,
data, access, privacy, irreversible; **standard** — breaks a working feature, visibly and
recoverably (the default); **low** — a broken page caught by looking. Class routes the
work; stakes scales its verification. Stakes never waives a guard, and calling a
framework primitive is not a decision (`contact-page-8k`).

## The seam

For Class A/B the plan/build boundary is a human checkpoint: `planning` stops at an
approved, gate-checked `tasks.md`; `building` re-runs `gate-check.py` itself at entry.
Never bridge it autonomously.
