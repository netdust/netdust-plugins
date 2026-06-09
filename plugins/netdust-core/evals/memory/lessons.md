
### 2026-05-17
- when a skill description leans on architectural verbs ("planning, designing, scaffolding"), it under-triggers on implementation-time prompts that just say "add a service that does X". The trigger sentence needs the literal phrases users actually type ("add a service", "write a service", "create a service") plus framework-keyword cues (`NTDST_Service_Meta`, `metadata()`, `plugin-config.php`). Scenarios 5+7 fired the skill cleanly because they used framework vocabulary; scenario 1 didn't.
- re-eval after skill changes is cheap (~30 min wall time, single session) and the per-scenario shape tells you more than the headline delta. Scenario 1's flip from +0 to +4 is the load-bearing signal from this run; the unchanged +15 total understates the qualitative win.
