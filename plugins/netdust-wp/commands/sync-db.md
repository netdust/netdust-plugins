---
description: Pull the remote DB for the current site to local DDEV.
allowed_tools: ["Bash", "Read"]
---

Sync remote database to local DDEV environment.

1. **Identify the site** from current working directory or ask user
2. **Read site config** at `~/Sites/netdust-wp-manager/sites/[site]/site.yml`
3. **Run the sync script**:
   ```bash
   ~/Sites/netdust-wp-manager/scripts/db-pull.sh [site]
   ```
4. **Report** success or any errors

The script handles:
- SSH connection to remote
- mysqldump export
- Local DDEV import
- URL replacement (production → local)

⚠️ This overwrites your local database. Make sure local changes are backed up if needed.
