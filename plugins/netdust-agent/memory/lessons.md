
### 2026-08-19
- systemd `EnvironmentFile=` loads after `Environment=` and overrides it. Reading only a `.service` file's inline `Environment=` line gave me a wrong diagnosis (collie pointed at a dead socket). Read the `.env`, or verify from the process's actual behaviour.
- herdr sessions are separate servers with separate ID spaces — a bare `herdr` command targets the session the calling pane lives in, not the project's session. Creating topology without first checking `herdr session list` puts it in whatever session you happen to be sitting in. There is no move between sessions; the only fix is rebuild in the right one and close the wrong one.
