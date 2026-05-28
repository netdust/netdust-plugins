---
description: Pull content + assets from the remote (production) into local DDEV
---

Pull remote content and assets into the local environment.

Steps:
1. Confirm the remote sync env vars are set in `.env` (`REMOTE_HOST`, `REMOTE_USER`, `REMOTE_PATH`, `REMOTE_SSH_KEY`).
2. Run `make sync-down` — pulls both content (`content/`) and assets (`public/assets/`) from production.
3. After sync, run `/cache-bust` (or `make cache-clear && php please statamic:stache:warm`) so the stache picks up the new content.
4. If you only need one side, use `make sync-content` or `make sync-assets`.

**Direction guard:** This command is always *down* (remote → local). To push local changes upstream use `make sync-up`, but **only** after confirming with the user — pushing local content over production is destructive.
