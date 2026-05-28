_Harness-self lessons for `netdust-wp`. Patterns that apply to the plugin's own development, not to user projects._

### 2026-05-17 — Stop hook silently skipping for months
Root cause: missing `ANTHROPIC_API_KEY` + no logging meant the hook was a no-op and nobody noticed. Fixed by (a) adding observability via `~/.claude/logs/memory-hook.log` and (b) switching the primary capture path to a deterministic tag-scanner that runs with zero deps. Haiku summarization is now opt-in, not the only path.

### 2026-05-17
- when a skill description leans on architectural verbs ("planning, designing, scaffolding"), it under-triggers on implementation-time prompts that just say "add a service that does X". The trigger sentence needs the literal phrases users actually type ("add a service", "write a service", "create a service") plus framework-keyword cues (`NTDST_Service_Meta`, `metadata()`, `plugin-config.php`). Scenarios 5+7 fired the skill cleanly because they used framework vocabulary; scenario 1 didn't.

### 2026-05-17
- when a skill description leans on architectural verbs ("planning, designing, scaffolding"), it under-triggers on implementation-time prompts that just say "add a service that does X". The trigger sentence needs the literal phrases users actually type ("add a service", "write a service", "create a service") plus framework-keyword cues (`NTDST_Service_Meta`, `metadata()`, `plugin-config.php`). Scenarios 5+7 fired the skill cleanly because they used framework vocabulary; scenario 1 didn't.

### 2026-05-17
- when a skill description leans on architectural verbs ("planning, designing, scaffolding"), it under-triggers on implementation-time prompts that just say "add a service that does X". The trigger sentence needs the literal phrases users actually type ("add a service", "write a service", "create a service") plus framework-keyword cues (`NTDST_Service_Meta`, `metadata()`, `plugin-config.php`). Scenarios 5+7 fired the skill cleanly because they used framework vocabulary; scenario 1 didn't.
- re-eval after skill changes is cheap (~30 min wall time, single session) and the per-scenario shape tells you more than the headline delta. Scenario 1's flip from +0 to +4 is the load-bearing signal from this run; the unchanged +15 total understates the qualitative win.
