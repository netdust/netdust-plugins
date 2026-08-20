
### 2026-08-19
- systemd `EnvironmentFile=` loads after `Environment=` and overrides it. Reading only a `.service` file's inline `Environment=` line gave me a wrong diagnosis (collie pointed at a dead socket). Read the `.env`, or verify from the process's actual behaviour.
- herdr sessions are separate servers with separate ID spaces — a bare `herdr` command targets the session the calling pane lives in, not the project's session. Creating topology without first checking `herdr session list` puts it in whatever session you happen to be sitting in. There is no move between sessions; the only fix is rebuild in the right one and close the wrong one.

### 2026-08-20
- `gate-check.py`'s task regex was `(T\d+)\b`, which cannot match `T07b`: `T\d+` stops at the digit and `\b` then demands a boundary between two word characters. Every `b`-suffixed task was invisible — skipped by the tier, files, test-author, proven-by and unit-test checks, and uncounted by the `<=4` cluster-size rule. Found on todai-client, where a FULL-tier security spec had three such tasks (T03b already shipped, T09b a Tier-A data-minimisation control) and still read `GATE: PASS`, while a 6-task cluster counted as 4. This is INV-4's own failure mode: a verdict reporting green while a named check never ran. When a checker's verdict looks too easy, test the PARSER against the corpus, not just the rules.
