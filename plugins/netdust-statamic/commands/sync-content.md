---
description: Pull content + assets from the remote (production) into local DDEV
---

Pull remote content into the local environment.

Steps:
1. Run `make pull-content` (production by default; `make pull-content env=staging` for another environment). It rsyncs each directory in `site.yml` `deploy.data_paths` (default `content users storage`) from the environment's `path` over SSH (`ssh_host` from `site.yml`). Assets come down only if their directory is listed there.
2. After sync, run `/cache-bust` so the stache picks up the new content.

**Direction guard:** This is always *down* (remote → local), and `--delete` makes local match the remote — commit or save local content edits first. There is no push-up verb — never rsync local content over an environment by hand.
