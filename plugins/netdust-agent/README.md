# netdust-agent

**A two-layer development harness for AI coding agents.** The skeleton (gates, steps, ordering) and the how-to (craft) it reaches for — kept as distinct, legibly-named layers, built on [superpowers](https://github.com/obra/superpowers-marketplace) with craft concepts from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT), and Netdust discipline as the spine.

> **Harness = the skeleton** (when/whether). **Craft = the how-to** the harness reaches for at each step. The harness decides *what fires, in what order, and proves it fired*; the craft is *how to actually do it well*.

---

## The two layers

### Harness — control flow (gates / steps / ordering)

Sequencers and gates. They decide what fires and prove it fired. `harnessed-development` is the single entry point — a pure sequencer that, at each stage, loads the right craft skill and wraps a gate around it.

| Skill | Role |
|---|---|
| `harnessed-development` | **Entry point.** Sequences brainstorm → plan(+gates) → execute → shake-out → finish. Carries the `<craft_routing>` table that maps each stage's gate to the craft skill it reaches for. |
| `threat-modeling` | Plan-time gate: embed a `## Threat model` when a security surface is touched. |
| `architecture-invariants` | Gate: name the convergence points; flag bypasses. |
| `feature-acceptance` | Gate: author + drive the `## Acceptance flows` matrix. |
| `testing-workflow` | Per-task gate: what *tier* of test does this task need, prove it RED-first. |
| `test-effectiveness` | Phase-close gate: would the green suite actually go RED? |
| `shake-out` | Spec-complete pre-merge sweep of the built artifact. |

### Craft — the how-to the harness reaches for (gerund-named)

What the harness *loads* at each step. Each craft skill **layers on top of its superpowers/plugin base** — it never replaces it, and never restates the generic mechanics. It adds only the Netdust harness contract.

| Craft skill | Layers on | Reached for at |
|---|---|---|
| `refining-ideas` | `superpowers:brainstorming` | Stage 0 — sharpen a vague idea (divergent→convergent) |
| `writing-tests` | `superpowers:test-driven-development` | Stage 2 — Tier-A RED→GREEN for the testing-workflow gate |
| `designing-apis` | *(addy: api-and-interface-design)* | Stage 1 — contract-first; designs in the convergence points |
| `building-frontend` | `frontend-design` plugin | Stage 2 — component/state/a11y/responsive on UI tasks |
| `engineering-context` | *(addy: context-engineering)* | session start / task switch — packs from the 3-layer memory |
| `versioning-with-git` | `superpowers:using-git-worktrees` | Stage 2/3 — atomic commit-craft (branch-flow stays in dev-stack) |
| `driving-the-browser` | `superpowers-chrome:browsing` | feature-acceptance / debugging — *how* to drive Chrome |
| `sourcing-from-docs` | *(addy: source-driven-development)* | any stage — cite official docs before asserting API behavior |
| `doubting-decisions` | *(addy: doubt-driven-development)* | post-plan — adversarial fresh-context attack on a decision |
| `simplifying-code` | *(addy: code-simplification)* | Stage 3 — reduce complexity, behavior preserved |
| `deploying` | `/deploy` + `dev-stack` | Stage 3 finish — route to the deploy dispatcher with guardrails |

**Naming convention:** *gerund = craft (how); phase/gate noun = harness (when/whether).* Read the skill list, know the layer.

---

## Agent personas

Four personas, one per important moment of the harness. **Personas load skills** — an agent is the *who* (role + judgment + dispatch context) that loads the relevant gates and craft skills to do its job. Skills stay the single source of *how*; agents don't duplicate them.

| Agent | Owns | Loads |
|---|---|---|
| `planner` | Stage 0→1: request → gated plan | brainstorming/refining-ideas, writing-plans, the plan-time gates (threat-modeling, architecture-invariants/designing-apis, feature-acceptance), sourcing-from-docs |
| `implementer` | Stage 2: one task to done, test-gated | testing-workflow/writing-tests, building-frontend, versioning-with-git, systematic-debugging; ends with the Test-evidence + STATUS blocks |
| `reviewer` | Stage 3: whole-diff, five-dimension pre-merge review | verifies the diff against the plan's threat model, `ARCHITECTURE-INVARIANTS.md`, and the test-effectiveness manifest; uses simplifying-code |
| `shakeout-qa` | Stage 3: exercise the built artifact end-to-end | shake-out, feature-acceptance, driving-the-browser, test-effectiveness; emits a pass/fail/not-reachable manifest |

`reviewer` reads the **diff**; `shakeout-qa` runs the **artifact**. The generalist `reviewer` runs alongside netdust-core's specialist reviewer agents (security-sentinel, performance-oracle, invariant-auditor, …), not instead of them.

---

## How it works

**Process, not prose.** Skills are workflows the agent follows, not reference docs it reads. The harness makes the discipline *structural* — a gate fires because the sequencer loads it, not because a CLAUDE.md reminder was honored.

**Layered, not duplicated.** Craft skills and agent personas are deliberately thin: they *load* their base (superpowers) and add only what the base can't know — the gate position, the conventions, the harness contract. The single source of any *how* lives in exactly one place, so nothing drifts.

**Invoke the entry point** — `harnessed-development` — for any non-trivial work. It classifies the work (new feature / existing plan / bug-fix bundle / security edit) and fires exactly the stages that class needs.

---

## Project structure

```
netdust-agent/
├── .claude-plugin/plugin.json   # manifest
├── CLAUDE.md                    # the two-layer model + naming/authority/layering rules
├── README.md                    # this file
├── docs/BLUEPRINT.md            # the layer map + design decisions
├── skills/
│   ├── harnessed-development/   # the entry sequencer (+ <craft_routing>)
│   ├── <harness gates>/         # threat-modeling, architecture-invariants,
│   │                            #   feature-acceptance, testing-workflow,
│   │                            #   test-effectiveness, shake-out
│   ├── <craft how-to>/          # writing-tests, designing-apis, building-frontend,
│   │                            #   engineering-context, versioning-with-git,
│   │                            #   driving-the-browser, refining-ideas,
│   │                            #   sourcing-from-docs, doubting-decisions,
│   │                            #   simplifying-code, deploying
│   └── _shared/                 # shared reference (finding-verification)
└── agents/                      # planner, implementer, reviewer, shakeout-qa
```

---

## Why netdust-agent?

Superpowers gives an agent generic engineering craft. It doesn't know *your* harness — your gates, your conventions, your flow. netdust-agent puts that on top: the gates enforce the discipline, the craft skills layer the harness contract onto the generic mechanics, and the agent personas orchestrate both at the right moment. The result is that "do this properly" engages the *whole* pipeline, every time, instead of relying on a session to remember each step.

Standalone by design. Intended to eventually replace the harness pieces of `netdust-core` (which keeps memory, hooks, the specialist reviewer agents, the ploi MCP, and `/deploy`).

## License

UNLICENSED (Netdust internal). Craft concepts adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT); built on [superpowers](https://github.com/obra/superpowers-marketplace).
