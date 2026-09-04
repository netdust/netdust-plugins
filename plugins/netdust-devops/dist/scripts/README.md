# Vendored scripts

Everything in this directory except your own additions is managed by
`netdust-devops`. `make devops-update` overwrites it, and `make doctor` reports
any file edited in place.

| File | What it does |
|---|---|
| `site` | reads one dotted key out of `site.yml`. The only reader the Makefile uses. |
| `devops-version` | vendors the core in, and reports version drift + files edited in place. |
| `deploy-context` | the deploy's view of the current environment. |
| `work-audit.sh` | reports work that exists only on this machine. Never writes. |
| `remote/refresh-db.sh` | runs ON the server for a server-to-server database refresh. |
| `remote/00-block-outgoing-mail.php` | mu-plugin that blocks mail on non-production. Self-disables on the production host. |
| `tests/deploy-test.sh` | proves the deploy tooling's refusals. Contacts no server. |
| `tests/flow-test.sh` | proves feature/hotfix/finish and every refusal in a throwaway repo. |

A fix belongs upstream in the plugin, not here. Editing a file in this
directory means the next `make devops-update` silently reverts it.
