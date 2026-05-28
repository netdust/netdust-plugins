---
description: Audit a path or module for drift from NTDST framework conventions. Runs the ntdst-drift-reviewer agent on the given scope and returns a prioritized punch list (repository bypasses, pass-through methods, raw wp_ajax_ handlers, ob_start+include rendering, swallowed WP_Error, wrong Data API vocabulary, hardcoded meta prefixes). Use before refactoring a module so you refactor against a punch list instead of blind.
argument-hint: <path-or-module>
allowed-tools: Agent
---

Run an NTDST drift audit on: $ARGUMENTS

## Instructions

1. **Resolve the scope.** $ARGUMENTS is the path to audit. Examples:
   - `Modules/Enrollment/` — single module relative to stride-core
   - `web/app/mu-plugins/stride-core/Modules/Edition/Admin/` — absolute-ish path
   - `EditionService.php` — single file (resolve to its full path)

   If the path is ambiguous (e.g. just `Edition`), confirm with the user before invoking the agent. Don't guess across project roots.

2. **Check for explicit exclusions.** If the user wrote `$ARGUMENTS` with a "skip X" / "exclude X" / "but not X" clause, pass that exclusion to the agent. Common ones: `skip the Admin folder`, `exclude tests`, `only services not handlers`.

3. **Invoke the agent.** Use the `Agent` tool with:
   - `subagent_type`: `netdust-wp:ntdst-drift-reviewer` (if available in this session; otherwise `general-purpose` with explicit instructions to act as the drift-reviewer per `~/.claude/plugins/netdust-wp/agents/ntdst-drift-reviewer.md`)
   - `description`: `Drift audit on <scope>` (short, 3-5 words)
   - `prompt`: a self-contained brief covering:
     - The scope (resolved path)
     - Any exclusions the user specified
     - **MUST read first** (list these explicitly in the prompt, by absolute path):
       - `~/.claude/plugins/netdust-wp/agents/ntdst-drift-reviewer.md` — agent definition (rules, checklist, output format)
       - `~/.claude/plugins/netdust-wp/agents/ntdst-drift-reviewer.lessons.md` — calibration notes (false-positive corrections, rule nuances from past audits). Apply as additional exception rules. **Read this file EVEN IF YOU EXPECT IT TO BE EMPTY** — empty today doesn't mean empty next run; the human curates it over time.
       - `~/.claude/plugins/netdust-wp/agents/ntdst-core-gaps.md` — known framework gaps + their workarounds. **Read this file EVEN IF YOU EXPECT IT TO BE EMPTY** — same logic. If you find a project doing X because the framework forces it, check this file first; if the gap is already documented, don't re-surface it. If it's new, surface as a candidate entry under "Framework gaps observed."
       - `~/.claude/plugins/netdust-wp/skills/ntdst-architecture/references/anti-patterns.md` — the rule book
       - `~/.claude/plugins/netdust-wp/skills/ntdst-architecture/references/architecture.md` — framework tool-fit table
       - `~/.claude/plugins/netdust-wp/skills/ntdst-data/references/data-orm.md` — Data API vocabulary
       - `~/.claude/plugins/netdust-wp/skills/ntdst-architecture/lessons.md` — incident journal
       - Project memory if present: `~/.claude/projects/<project-id>/memory/MEMORY.md` — project-specific exceptions
     - "Produce the report in the exact format the agent file specifies"

   Listing the lessons file explicitly in the prompt — not just in the agent definition — is deliberate: it ensures both the proper agent AND the general-purpose fallback read it. Don't trust the agent's own "Before you start" section to be enough on its own.

4. **Return the agent's report verbatim** — don't summarize, don't editorialize, don't filter findings. The user reads the actual report.

5. **After returning the report**, offer one follow-up:
   - "Want me to fix the findings? I can do them in one focused commit (small list) or split per category (larger list)."
   - DO NOT start fixing automatically. The user decides scope.

## Quality bar

- The agent reads canon files (`anti-patterns.md`, `architecture.md`, `data-orm.md`, `lessons.md` in the netdust-wp skills) and the agent's own calibration notes (`ntdst-drift-reviewer.lessons.md`) before auditing. Make sure the prompt names those, so a general-purpose fallback knows what to consult.

- If $ARGUMENTS is empty or unclear, ask: "Which path do you want audited? e.g. `Modules/Enrollment/` or `Modules/Edition/Admin/`."

- If the resolved scope contains >50 files, mention that to the user and confirm scope. The agent will sample by default at that size; explicit confirmation gives the user a chance to narrow.

## What this command is NOT

- Not a refactor tool. The agent reviews; it does not write changes.
- Not a test runner. It scans static patterns, not behaviour.
- Not for cross-project audits. One project, one path at a time.
