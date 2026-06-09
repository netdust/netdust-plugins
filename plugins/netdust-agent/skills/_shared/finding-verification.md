# Shared reference — Finding verification (adversarial, voted, rule-bounded)

One convergence primitive, used by every harness gate that produces or consumes a list of "findings" (threat-modeling mitigations, test-effectiveness blind spots, shake-out bugs, /code-review hits). Instead of each skill reinventing "is this finding real?", they all point here. Adapted from the adversarial-triage pattern in Anthropic's `defending-code-reference-harness` (the `/triage` skill), trimmed to a single-binary, single-team harness — no sandbox, no pipeline.

Use it whenever a gate has produced candidate findings and you must decide which are REAL before acting (fixing, reporting, blocking a merge). It collapses a noisy candidate list into a short, confirmed, owned one — and stops the harness re-flagging the same accepted non-issues every round.

---

## The skeptic stance (the core idea)

**Default to "the finding is WRONG." Make it prove itself.** A reviewer who starts from "the scanner/agent/previous-round is probably right" inherits the upstream misreading and confirms it. A reviewer who starts from "refute this" re-derives the claim from source and only confirms what survives. This is the difference between a review that converges and one that drifts.

Run it as a verification step, not a vibe: read the cited code yourself, trace reachability, hunt for the protection that makes the finding moot, then deliver a structured verdict. Uncertain → lean refuted, not confirmed.

---

## Voting (scale the rigor to the stakes)

For a batch of findings, spawn **N independent verifiers per finding** — each blind to the others, each told to refute. Tally by majority.

| Stakes | Votes (N) |
|---|---|
| Quick pass / low-risk surface | 1 |
| Default | 3 |
| Security-critical, pre-merge, or a finding that would block | 5 |

- Each verifier gets ONLY the one finding + read access to the cited source. It does not see the other verifiers' votes.
- **Majority confirmed → real.** Majority refuted → drop. Split → `needs_manual` (a human looks; do not silently confirm or drop).
- Confidence = agreement strength (3/3 > 2/3). Record the split, not just the verdict — a 2/3 confirm is weaker evidence than 3/3 and the report should say so.
- A single reviewer (N=1) is fine for a small, low-stakes sweep — the machinery scales DOWN. Don't spawn 5 verifiers for a 3-bug shake-out; don't trust 1 for a merge-blocking auth finding.

This is the same engine the workflow-tool's adversarial-verify pass uses informally; this reference is the standing, scalable form so the gate skills don't each hand-roll it.

---

## The verifier procedure (what each vote actually does)

Give every verifier these four steps — each exists because skipping it lets a specific false-confirmation through:

1. **Read the cited code yourself.** Open the file:line. Understand what it actually does. Do NOT trust the finding's description — upstream summaries misread code, and starting from the summary inherits the misreading.
2. **Trace reachability.** Can the dangerous input/path actually reach this point? Grep callers, follow the chain. A plausible-sounding chain is not enough — read the FIRST link's call site and quote its file:line. *Unreachable code is the single largest false-positive source.*
3. **Hunt for the protection that makes it moot.** Actively look for why the finding is WRONG: upstream validation, a guard already on the path, a type constraint, an auth gate, a config that disables it, dead/test-only code.
4. **Stress-test the protection.** Is it on EVERY path to the sink, or only the one traced? Any encoding/edge-case/alternate-entry that bypasses it?

Verdict block each verifier ends with:

```
VERDICT: CONFIRMED | REFUTED | CANNOT_VERIFY
CONFIDENCE: 0-10
EXCLUSION_RULE: <rule number from below, or none>
FIRST_LINK: <file:line of the first call site you read, or "none found">
RATIONALE: 2-5 sentences citing file:line evidence for reachability, the protection found/absent, and why it held or didn't
```

CONFIRMED requires ALL of: reachable from the relevant untrusted/dangerous input; protections insufficient or bypassable; the impact is real. REFUTED requires ANY of: unreachable; protected on all paths; misread; an exclusion rule applies. CANNOT_VERIFY only when static reasoning genuinely hit a wall (runtime-config-dependent, crosses into an unreadable binary) — use sparingly, never as the default.

---

## Exclusion rules (REFUTED even if technically accurate — cite the number)

These mirror threat-modeling's "out of scope" deferrals and architecture-invariants' "deliberate exceptions": a finding matching one is **not actionable here** and must not be re-raised every round. Cite the rule number in the verdict. Adapt per project — append project-specific rules in the consuming skill.

1. **Volumetric DoS / missing rate-limiting** handled at the infra/proxy layer. (Algorithmic-complexity / ReDoS / unbounded-recursion ARE still valid.)
2. **Test-only, dead, example, or fixture code** — or a crash/bug with no real-world impact.
3. **Intended design** — a documented, deliberate behavior (a back-compat path offered alongside the strong one; a ratified architecture exception).
4. **Memory-safety concern in a memory-safe language** outside an `unsafe`/FFI boundary.
5. **SSRF where the attacker controls only the path, not host or protocol.**
6. **User input flowing into an AI/LLM prompt** (prompt injection is not a code vuln in the target — unless the harness's own agent-authority surface, which IS in scope, see project rules).
7. **Trusted inputs as the vector** (operator env vars, CLI flags) UNLESS the stated environment marks them untrusted.
8. **Client-side code flagged for a server-side vulnerability class** (or vice versa).
9. **Outdated dependency versions** — managed by a separate update process.
10. **Weak randomness for non-security purposes** (jitter, shuffles, dev-only fallbacks).
11. **Low-impact nuisance** (log spoofing, CSRF on logout, self-XSS, tabnabbing, bare open-redirect) with no escalation path.
12. **Missing hardening / best-practice gap with no concrete exploit path** (absent security headers, no audit log, permissive config not actually reached by untrusted input).
13. **Framework-auto-escaped XSS** (React/Vue/Angular/Jinja-autoescape) UNLESS the sink is a raw-HTML escape hatch (`dangerouslySetInnerHTML`, `v-html`, `|safe`).
14. **Unguessable-by-construction identifiers** (UUIDv4, 128-bit+ tokens) flagged as "predictable".
15. **Theoretical-only TOCTOU/race** — no realistic window, or no security-relevant state changes between check and use.
16. **Already covered by a named, ratified deferral** in the project's threat model "out of scope" list or `ARCHITECTURE-INVARIANTS.md` "deliberate exceptions" — point at it, don't re-litigate.

When a real finding keeps getting raised that ISN'T on this list and ISN'T actionable, that's signal: add a project-specific exclusion rule (in the consuming skill or the project's threat model), so the next round inherits it.

---

## How the gates use this

- **threat-modeling** — the "out of scope (explicit deferrals)" list IS exclusion rules 1–16 applied to that feature's surface; new deferrals become project rules. Mitigations a verifier can't confirm are real gaps.
- **test-effectiveness** — when classifying whether a "blind" finding is a genuine coverage gap vs an accepted residual, run a verifier pass; rule 2 (test-only/dead) and rule 16 (ratified deferral) refute most false blinds.
- **shake-out** — its bug manifest is a finding list; vote each bug before fixing so the fix loop spends effort only on confirmed bugs (default N=3; N=1 for a tiny sweep).
- **/code-review & /security-review** — verify hits against this list before reporting; cite the exclusion-rule number so an accepted non-issue is never re-raised across rounds.

Keep it light: this is a *step inside* an existing gate, not a new gate. No new skill, no new trigger — the gates that already produce findings point here instead of each carrying their own "is it real?" prose.
