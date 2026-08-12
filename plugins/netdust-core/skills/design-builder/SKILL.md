---
name: design-builder
description: Use when recreating a reference site or design as production-ready code — triggers on "recreate this site", "artist website", "agency website", "design reference", "capture this reference", "build a site like X", or any implementation intent against a screenshot, URL, or captured reference. Drives a measured capture (tokens, typography, spacing, and real motion timings — never eyeballed) through a user-gated Discover → Plan → Execute sequence into the design-references store.
---

# Design Builder

## Overview

Turn a reference site into production-ready code through a measured, user-gated
build: Discover captures the reference with real tooling, Plan turns the capture
into a build contract, Execute builds section-by-section under mandatory visual
verification.

**Core principle:** Not done until measured. A design token or a motion timing
you didn't capture is a guess, and guesses are how this skill family failed
before — see `lessons.md`.

**Violating the letter of these rules is violating the spirit of these rules.**

## When to use

Use when the user hands you a reference (a live URL, a screenshot, or an
already-captured `~/Sites/design-references/<name>/` directory) with intent to
build or rebuild it. Don't use for a quick single component, a design
discussion with no build intent, or reviewing existing design work.

## The Iron Law

```
NO SECTION COMPLETION WITHOUT VISUAL VERIFICATION
```

Claiming a section is done without a screenshot comparison is lying. This
applies in Execute; see `workflows/execute.md`.

## Three phases, user-gated

| Phase | Input | Output | Gate |
|---|---|---|---|
| **Discover** | Reference (URL / video / existing capture) | Token sheet + measured motion tables, written to `~/Sites/design-references/<name>/` | User confirms the token sheet |
| **Plan** | Locked Discover output | Design bundle: `tokens.css`, component sheet, per-screen mockups, motion plan citing measured values | User approves the plan |
| **Execute** | Approved plan | Verified sections, built against the chosen stack | Each section: screenshot + comparison + user approval |

Workflows: `workflows/discover.md`, `workflows/plan.md`, `workflows/execute.md`.
Load the workflow for the phase you're in — don't front-load all three.

## Discover is measured, not eyeballed

The retired skill family guessed design tokens from a screenshot and inferred
motion ("probably a fade on scroll"). That guessing is the specific failure
this skill exists to correct — see `lessons.md`. Discover always runs the
page-analyzer MCP trio against the reference (`analyze_page`, `capture_motion`,
`download_assets`) before any token or motion claim, and the motion tables in
the token sheet are transcribed from `motion-spec.md`'s measured values —
never from watching a video and guessing. Full mechanics: `workflows/discover.md`.

## Where captures live

Every reference gets a directory under `~/Sites/design-references/<name>/`, per
that store's own `README.md` (read it — store shape, `REFERENCE.md` template,
usage boundary). This skill drives the capture into that store; it does not
invent its own output location.

## Reference material never ships

References are private study material. Discover and Plan may cite the
reference's layout, motion timing, and structural patterns. Execute never
copies the reference's actual imagery, copy, or brand marks into client work —
only the abstracted technique.

## Red flags — stop

| Thought | Reality |
|---|---|
| "Looks close enough" | Take screenshot. Compare pixel-level. |
| "This probably matches" / "probably a fade" | "Probably" means unmeasured. Run the capture. |
| "Just minor differences" | Minor differences are not done. |
| "I'll check mobile later" | Mobile is part of verification, every section. |
| "Section complete" | Only after screenshot comparison passes. |
| "The code is correct" | Code correctness is not visual match. |
| "I already checked" | Show the screenshot. |
| "It's an animation, can't measure it" | `capture_motion` measures it. Run the probe. |

## Rationalization prevention

| Excuse | Reality |
|---|---|
| "The tool isn't working" | Fix the tool. Don't fall back to eyeballing. |
| "Reference is video-only, no live URL" | Route Discover to stored videos + screenshots — see `workflows/discover.md`. Don't skip the capture. |
| "Takes too long to capture each section" | The capture IS the work. Not optional. |
| "I've built this pattern before" | Every reference is unique. Measure this one. |
| "User will see it anyway" | Catch mismatches before the user does. |

## Quick reference

- Discover: `workflows/discover.md` — run the analyzer trio, produce the token
  sheet + measured motion tables, lock the spec.
- Plan: `workflows/plan.md` — turn the locked spec into the design bundle,
  choose the target stack, get approval.
- Execute: `workflows/execute.md` — build one section at a time, verify with
  screenshots at desktop and 375px, max 3 fix attempts before escalating.

## See also

- `~/Sites/design-references/README.md` — the store this skill writes into.
- `lessons.md` — the two calibrations behind this rewrite.
