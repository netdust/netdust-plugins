---
name: threat-modeling
description: Use when writing a plan or spec for any feature that touches user-controlled URLs, auth/session/token surfaces, untrusted parsing (frontmatter from external sources, AI tool-call args, JSON-from-network, file uploads, MD-from-third-parties), BYOK credentials, multi-tenancy boundaries, or any surface where an attacker could supply input the server will trust. Produces a `## Threat model` section that the plan embeds inline. Becomes the convergence target for /code-review on the implementing sub-phases — reviews verify against the named mitigations instead of free-form bug hunting. Opt-in via the project's CLAUDE.md — not auto-invoked.
---

<objective>
Produce a `## Threat model` section that the plan embeds inline, BEFORE task breakdown. The section names assets, actors, attacks, paired mitigations, and explicit out-of-scope deferrals. It exists so that:

1. The implementer has concrete security requirements, not vibes ("encrypt the keys" → "10 named mitigations including IPv4-mapped IPv6 SSRF blocking").
2. The `/code-review` gate has a fixed target to verify against — converges in 1 round instead of 2-3 on security-rich features.
3. Future sub-phases inherit the threat model and don't re-litigate.
4. Out-of-scope deferrals are documented, so reviewers don't repeatedly surface accepted-residual-risk items as new findings.

Without this section, every `/code-review` round on a security-rich surface independently re-discovers the attack surface. Each round catches a different subset. Convergence is slow and probabilistic. The cap-of-15 on medium-effort reviews can hide critical findings below the threshold for multiple rounds.
</objective>

<extremely_important>
This is NOT a security audit skill. This is a PLAN-WRITING skill. It runs once, at plan-writing time, BEFORE any tasks are dispatched. The output is a section in the plan, not a separate document.

If you find yourself running this skill AFTER tasks have shipped, you're using it as remediation, not prevention. That's still valuable (see Folio Phase 3 Sub-phase B, where the threat model was written retrospectively after 2 rounds of `/code-review` surfaced 30 findings) — but recognize the cost difference: prevention costs ~15 minutes of plan-writing; remediation costs the same 15 minutes PLUS the multi-round review-fix cycle that the prevention would have collapsed into one pass.

Opt-in is intentional. Most plans don't need this skill. Skill triggers only when the plan touches surfaces named in `<when_to_use>`. If you're unsure whether a plan qualifies, default to running this skill — false positives cost 15 minutes, false negatives cost hours of review-fix loops.
</extremely_important>

<when_to_use>

Invoke this skill when the plan being written touches ANY of these surfaces. The list is the trigger predicate — if you can answer "yes" to any one, the plan needs a threat model.

| Surface | Examples (any stack) |
|---|---|
| User-controlled URLs | Webhook endpoints, BYOK provider URLs (`baseUrl`), OAuth redirect URLs, image/file references in MD frontmatter pointing at remote, embed URLs, CMS bridge endpoints, external API gateways |
| Auth / session / token surfaces | New auth method, scope additions to existing tokens, OAuth flows, capability/role checks, multi-tenancy isolation, agent-vs-user vs-token distinctions |
| Untrusted parsing | Frontmatter from third-party MD files, AI tool-call argument JSON, webhook payload JSON, uploaded file contents, untrusted YAML, CSV imports, RSS/atom feeds |
| BYOK credentials | Storing user-supplied API keys, encrypting/decrypting them, passing them to outbound requests, sharing them across requests/agents |
| Multi-tenancy boundaries | Workspace isolation, project isolation, cross-workspace read paths, agent allow-lists, RBAC additions |
| File handling | Uploads (especially path traversal risk), downloads (especially content-type sniffing), MD parsing from untrusted sources, attachment storage |
| Outbound HTTP from server | Anything where the server makes a request to a URL the user supplied (SSRF class — covers most "user URLs" cases) |
| Stack-specific (WP) | New AJAX handler, REST endpoint registration, shortcode that takes attributes, settings page with user input, capability checks, nonce surfaces |
| Stack-specific (Statamic) | New form, content blueprint with user-controlled fields, custom fieldtype, addon that processes user input |
| Stack-specific (Bun/React) | New Hono route, new MCP tool, anywhere `req.body`/`req.params`/`req.query` lands without prior validation |

**Do not invoke when:**
- Refactors with no new attack surface (renaming, code-organization, internal API tweaks)
- Migrations on internal schema with no user-facing change
- UI polish, accessibility, visual-only work
- Performance work
- Test additions
- Documentation
- Internal automation (CLI scripts, dev tooling, build scripts) — unless those tools handle credentials

If the plan describes a feature you can't be sure about, ask the plan author "does this touch user-controlled URLs, auth, untrusted parsing, BYOK credentials, or multi-tenancy boundaries?" If they say no with confidence, skip. If they hedge, run the skill — false positives are cheap.

</when_to_use>

<process>

Walk the plan author through these six steps. The output of all six concatenated, formatted as the template in `<output_template>` below, becomes the `## Threat model` section.

**Step 1 — Identify assets being defended.**

For the feature in the plan, what is valuable enough that an attacker would want it? Common categories:

- Credentials (API keys, session tokens, refresh tokens, OAuth secrets, encryption keys)
- Sensitive data (PII, financial records, internal documents, member emails, agent prompts that contain workspace secrets)
- Server-side resources (the server's network position, its filesystem, CPU/memory, outbound bandwidth, identity to call other services)
- Integrity properties (workspace isolation, project isolation, audit trail, agent allow-list contracts)
- Availability (the ability to refuse a runaway agent / DoS the queue / saturate the test runner)

List 3-6 specific assets. Be concrete. "Credentials" is too vague — "the apiKey stored encrypted at rest in ai_keys.encrypted_key" is specific.

**Step 2 — Identify actors.**

Who might attack? Categories to consider:

- External attackers with no account / no Folio access
- Authenticated users who shouldn't have a particular permission (e.g. workspace member without admin role)
- Authenticated users who DO have permission but who are phished / tricked
- Compromised agents (Sub-phase C onwards — agents running with workspace tokens that could be steered by prompt injection)
- Insiders with stolen credentials (typically OUT of scope — note explicitly)
- Other workspaces' members trying to read across the workspace boundary

List 3-6 actor classes. Mark which ones are IN scope (defend against) and which are OUT of scope (acknowledged but not defended against).

**Step 3 — Enumerate attacks.**

For each (asset × actor) combination that's not trivially blocked, what's the attack? Be specific — name the vulnerability class AND the specific manifestation. Common patterns by surface:

For user-controlled URLs:
- SSRF (RFC1918, link-local, loopback, IPv6 loopback, IPv4-mapped IPv6 like `::ffff:127.0.0.1`, cloud metadata at 169.254.169.254)
- Credential exfiltration via the URL itself (if the server attaches an Authorization header)
- Persistence-path bypass (if validation is on one route but not the persisted-and-reused path)
- Local service abuse (default URLs pointing at localhost services)
- DNS rebinding (URL resolves to allowed IP at validation time, malicious IP at fetch time)
- Open redirect (server returns the URL to the client, who then auto-redirects)

For auth surfaces:
- Confused deputy (session-OR-token paths where the auth-narrowing isn't consistent)
- Token scope escalation (an agent's token getting workspace-admin privileges via a missing scope check)
- Cross-workspace read (one workspace's member querying another workspace's data via a missing scope predicate)
- Session fixation, CSRF (if the route is state-changing and same-origin policy isn't enforced)

For untrusted parsing:
- JSON.parse aborts the entire stream (no try/catch)
- Prototype pollution (Object.assign / merge of untrusted JSON)
- YAML billion-laughs / aliases
- Path traversal via filename strings ("../../etc/passwd")
- Symlink-following on filesystem operations
- Zip bombs / decompression bombs
- MD with embedded HTML that doesn't get sanitized

For BYOK credentials:
- Logging the key (server logs, error messages, telemetry, exception traces)
- Persisting the key unencrypted (transient files, backups, debug dumps)
- Encrypting with a key that's reused elsewhere
- Returning the key in API responses (even partially)

For multi-tenancy:
- Missing `workspaceId` predicate in a query
- Missing `projectId` predicate in a query  
- Resource ID in the URL not cross-checked against the auth context's allowed scope
- Cache key collisions across workspaces
- **Traverse-clause bypass (the leak that's correct-at-fetch, wide-at-serve):** the scoping predicate is applied where the data is *fetched* but NOT re-applied where it is *broadcast, listed, serialized, or live-pushed* to a caller on a different (narrower) scope. The query is right; the consumer leaks. Three recurring manifestations: (a) a workspace-/tenant-scoped event/feed delivered to a project-/role-narrowed subscriber without re-filtering each row by the subscriber's reach (SSE, websocket, activity stream, notification fan-out); (b) a "list X in tenant" endpoint that narrows by the *agent/service* allow-list but not by the *human* caller's narrower grant, so a partially-scoped member sees the whole tenant; (c) the scope check living on ONE auth method (session) or ONE route while a sibling path (a personal access token, an admin twin route, a null-scope/"all" sentinel row) skips it. **The tell:** the same "what can this actor see" predicate is hand-rolled at N call sites instead of computed once — every site is a place the next refactor silently diverges. Converge it into ONE `visibleScopeFor(actor)` helper and route every fetch/serve/broadcast surface through it. *(Folio worked example: CR-8/9/10/11 — workspace-scoped SSE rows, ws-scoped run lists, and a role-change event all reached a project-only invitee because the per-user narrowing was wired into one surface + one auth method; the fix was one `visibleProjectIds` convergence helper.)*

For untrusted streams (provider responses, webhook payloads, file uploads):
- Falsy-zero in token accumulators (`if (delta.tokens)` skips on zero)
- Buffer not flushed at end-of-stream
- Cache poisoning on rejected promises
- Stop-reason downgrades (silent loss of semantic distinctions like refusal vs stop)

Number each attack 1-N. Each attack will get a paired mitigation.

**Step 4 — Pair each attack with a specific mitigation.**

For each attack from Step 3, write a concrete mitigation. The mitigation must be checkable — a reviewer should be able to look at the code and say "yes, this is implemented" or "no, this is missing." Avoid mitigations that are vibes-based ("validate input" — what validation?) or testable only by absence ("don't log keys" — easy to miss).

Good mitigations look like:
- "One shared baseUrl validator function in apps/server/src/lib/ai/baseurl-validator.ts. Validates: scheme is https, resolved IP not in private range, not IPv4-mapped IPv6, cached resolution for the request lifetime. Called from BOTH /ai/test-key AND POST /ai-keys — both paths route through the validator before persistence OR network use."
- "ProviderEvent.done.reason adds 'refusal'. Each provider implementation maps its specific stop reasons explicitly. SDK-specific reasons that don't map should emit a warning log line, not silently become 'stop'."
- "JSON.parse calls are try/catch-wrapped in all four provider implementations. On failure: log + emit a type:'tool_call' event with arguments:{__parse_error:true, raw:<truncated>}."

Number each mitigation 1-N matching the attacks. Pair them clearly.

**Step 5 — Document out-of-scope deferrals.**

What attacks are acknowledged but NOT being defended against in this feature? Be explicit. Common defensible deferrals:

- DNS rebinding beyond cached resolution (acceptable residual risk for v1)
- Rotating master encryption keys without a deploy (operational, not v1)
- Per-key allow-lists (provider SDK constraint)
- Full audit-log of every outbound HTTP request (deferred to v1.1)
- Anti-CSRF beyond same-origin enforcement (SameSite=Lax cookie reliance)
- Stack-specific: WP's REST API capability nuances when interacting with custom REST endpoints (defer to the WP REST team)

Documenting these explicitly prevents the same items from being raised as findings in every subsequent `/code-review` round.

**Step 6 — Write the "how to use this section" closer.**

Add a closing paragraph that tells future readers how this section feeds into the workflow. Tell controller pre-flight to verify mitigations before dispatching tasks. Tell `/code-review` to check against the threat model instead of free-form. Tell `/evaluate` retros to list any missing mitigations as plan-correction defects. Tell downstream sub-phases to cross-reference, not re-litigate.

</process>

<output_template>

Concatenate Steps 1-6 into a section that goes into the plan with this exact structure. The plan author embeds it inline, BEFORE the task breakdown, typically right after the sub-phase map or scope overview.

```markdown
## Threat model

> One-paragraph context: what feature this threat model is for, when it was written (so future readers know how stale it is), and one sentence on why it exists. Example: "The BYOK + arbitrary baseUrl surface is security-rich. Without this section, /code-review rounds re-discover the attack surface independently and don't converge. This section is the convergence target — reviews verify against named mitigations."

### What we're defending

List 3-6 specific assets. Be concrete. Don't say "credentials" — say "the apiKey stored encrypted at rest in ai_keys.encrypted_key with the FOLIO_MASTER_KEY decryption secret in the server env."

### Who we're defending against

List 3-6 actor classes. For each, mark IN-scope (we defend) or OUT-of-scope (acknowledged, not defended).

### Attacks to defend against

Number each attack. For each: one sentence on the vulnerability class + the specific manifestation. Example:

1. **SSRF via baseUrl**: an attacker supplies baseUrl resolving to a private network address (RFC1918, link-local, loopback, IPv4-mapped IPv6 like `::ffff:127.0.0.1`, cloud metadata endpoints). The server then makes a request to that URL while testing the key, reaching private services the attacker shouldn't reach.

### Mitigations required

Numbered to match attacks. Each mitigation must be code-checkable.

1. **One shared baseUrl validator** ... (concrete, named functions, named files, named call sites).

### Out of scope (explicit deferrals)

List acknowledged-but-not-mitigated items. One sentence each explaining why deferred (v1.1 concern, residual risk acceptable, SDK constraint, etc.).

### How to use this section

- Controller pre-flight: verify mitigations are in plan-supplied code before dispatching tasks.
- `/code-review` invocations: include "Verify code against the threat model in the plan. Each numbered mitigation should be checked. Report which are in place, which are missing, and which are out of scope per the deferrals list."
- `/evaluate` retros: list mitigations that were not implemented as plan-correction defects.
- Downstream sub-phases: cross-reference, don't re-litigate. Extend if the surface grows.
```

</output_template>

<worked_example>

The canonical worked example is the threat model in Folio's Phase 3 plan at `~/Projects/folio/docs/superpowers/plans/2026-05-27-phase-3-agent-runner.md`, section `## Threat model` (around line 51). It covers BYOK + provider-API URLs across Sub-phases B and C. Specifically:

- 4 named assets (apiKey, master key, network position, workspace integrity)
- 5 actor classes (external attackers, members-with-write-no-admin, phished admins, malicious agents, insiders OUT of scope)
- 10 numbered attacks (SSRF + IPv4-mapped IPv6 bypass, credential exfil via baseUrl, persistence-path exfil, Ollama localhost default, error-message leak, untrusted stop-reason downgrade, interface lies, JSON.parse crash, falsy-zero tokens, proxy cache poisoning)
- 10 paired mitigations (centralized baseUrl validator, provider-narrowed baseUrl allow-list, sanitized errors, refusal added to ProviderEvent union, try/catch around JSON.parse, etc.)
- 6 explicit deferrals (DNS rebinding past cached resolution, per-request audit, master-key rotation, per-key allow-lists, anti-CSRF beyond same-origin, agent_run row exfil deferred to Sub-phase C)

Read it as the template for shape. It was written AFTER 2 rounds of /code-review surfaced ~30 security findings — making it a retrospective example. Future plans should produce something similar PROACTIVELY, before tasks are dispatched.

</worked_example>

<red_flags>

These thoughts mean you're about to skip the discipline. Stop.

| Thought | Reality |
|---|---|
| "The feature is small, threat modeling is overkill" | A small feature with user-controlled URLs is still a security-rich surface. The cost is 15 minutes; the cost of missing it is hours of /code-review iteration. |
| "I'll add the threat model later if /code-review finds things" | That's the failure mode this skill exists to prevent. Retrospective threat modeling works (see Folio Sub-phase B) but costs N rounds of /code-review FIRST. |
| "Most of these attacks won't happen in practice" | Edge cases in security context = exploitable. Cost-of-fix is 5-10 lines; cost-of-not-fixing-if-attacked is catastrophic. |
| "I don't know what attacks apply, I'll skip" | The attack catalog in `<process>` Step 3 lists them by surface. If the feature has user-controlled URLs, the SSRF / credential-exfil / DNS-rebinding attacks ALWAYS apply. Skip the skill only if NO surfaces match `<when_to_use>`. |
| "I'll write 'TBD' for now" | TBD = "this section is invisible to /code-review" = no convergence target. Write something explicit even if you mark deferrals; deferrals are themselves load-bearing. |
| "The plan is generic — I can't write a specific threat model" | If the plan is too generic to threat-model, the plan is too generic to dispatch. Refine the plan first. |
| "I'm not a security expert" | Neither is anyone else. The attack catalog in Step 3 is the floor — you're not expected to invent novel attacks, just to apply the named patterns to your surface. |

</red_flags>

<success_criteria>

This skill has succeeded when the plan contains a `## Threat model` section with:

1. Concrete assets (not "credentials" — "ai_keys.encrypted_key with FOLIO_MASTER_KEY decryption").
2. Actor classes with explicit IN/OUT-of-scope markers.
3. Numbered attacks paired 1:1 with numbered mitigations.
4. Each mitigation is code-checkable (a reviewer can verify it's in place by reading the code).
5. Explicit out-of-scope deferrals with one-sentence rationale.
6. A "how to use this section" paragraph that names controller pre-flight, /code-review, /evaluate, and downstream sub-phases.

If `/code-review` runs on the implementing sub-phase with the threat model as input and converges in ONE round (not 2-3), the skill earned its keep.

If `/code-review` keeps surfacing NEW critical-class findings the threat model didn't cover, the threat model was too shallow — extend it iteratively, but recognize that's the harness telling you the spec needs more work.

</success_criteria>

<integration>

| Skill | Relationship |
|---|---|
| `superpowers:writing-plans` | **COMPANION.** This skill runs ALONGSIDE writing-plans, not as a replacement. writing-plans produces the functional spec + task breakdown; threat-modeling produces the security section that sits before the task breakdown. Same plan file, two skills' output. |
| `netdust-core:harnessed-development` | **UPSTREAM + DOWNSTREAM.** harnessed-development FIRES this skill at Stage 1a (by trigger list, or on an ad-hoc security diff in Class D). When the plan is then executed, the controller pre-flight verifies tasks include the mitigations; testing-workflow still gates per-task; the threat model gates at /code-review at sub-phase close. |
| `/code-review` | **CONSUMER.** Reviews are invoked with the threat model as context. Reports converge against the named mitigations. |
| `/evaluate` | **CONSUMER.** Retros list any missing mitigations as plan-correction defects, and surface "the threat model was too shallow" findings if new critical issues emerged. |
| `superpowers:brainstorming` | **UPSTREAM.** During brainstorming for a feature that touches surfaces in `<when_to_use>`, the brainstormer should note "this needs a threat model" so writing-plans + this skill collaborate to produce it. |

**Calibration data behind this skill:** Folio Phase 3 Sub-phase B (2026-05-28) shipped 7 tasks of BYOK + provider-URL code WITHOUT a threat model in the plan. Two rounds of `/code-review` at `--effort=medium` surfaced ~30 security-class findings, with critical-class items still emerging in round 2 (SSRF IPv4-mapped IPv6 bypass, credential exfiltration via baseUrl, persistence-path validation gap, Ollama localhost-default). The cap-of-15 on medium-effort reviews compounded the problem — long-tail findings stayed below the threshold across multiple rounds. After the threat model was written retrospectively, round 3 became a verification pass instead of another discovery pass. The skill exists to do this work proactively next time.

See `~/Projects/folio/memory/lessons.md` entry "2026-05-28 — Plans for features touching user-controlled URLs require a Threat model section before task breakdown" for the lesson in feedback-memory form.

</integration>
