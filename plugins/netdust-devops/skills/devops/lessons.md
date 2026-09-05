# Lessons — devops

Append-only. After any correction, the rule that prevents the repeat.

## A recipe comment is still shell

A `: "..."` line in a Makefile recipe is still a shell command. A backtick
inside it is command substitution, not punctuation — a comment mentioning the
verb it documented re-invoked make and recursed until the process table gave
out (make[90], no output, hangs on parse).
Recipe comments use single quotes and no backticks. `tests/test-makefile.sh`
asserts no recipe line contains one (2026-09-04).

## The terminal check goes first, not last

`make ship` originally checked for a terminal inside `_deploy-confirm`, after
the gate and both backups. A piped ship therefore took a production database
dump and a payload tarball before discovering it could never read the
confirmation. Any check that can refuse the whole verb belongs before the
first step that touches a server (2026-09-04).

## The production self-disable is an exact host match, never a substring

`00-block-outgoing-mail.php` tested `strpos( WP_HOME, '<production host>' )`.
Staging is commonly a SUBDOMAIN of production, and
`strpos('https://staging.example.com','example.com')` matches — so the block
disabled itself on staging and let real mail out. A fleet scan found **5 of 7
projects** shaped that way; none had ever blocked anything.
The decision lives in `ntdst_mail_block_is_production()`: compare the parsed
host exactly, and treat an empty or unparseable `WP_HOME` as not-production so
the guard fails closed. Two pins in `tests/test-makefile.sh` (2026-09-05).

## The mail block must be excluded from the payload, or the deploy deletes it

`block-mail` installs the block INTO `content/mu-plugins`, a payload directory
rsynced with `--delete`, and the file exists only on the server. Unexcluded,
`block-mail` followed by `deploy` leaves no block at all — 6 of 7 fleet
projects were in that state. `deploy.exclude` now carries
`00-block-outgoing-mail.php` in `site.yml.tmpl`; excluded paths are protected
from `--delete`. Pinned in `tests/test-makefile.sh` (2026-09-05).

## Standing an environment up the first time is not a deploy

`deploy.payload` is a closed list of tracked directories, so a first bring-up
carries almost nothing that matters: WP core, `vendor/`, `.env`, `wp-config.php`,
`index.php`, `.htaccess`, third-party plugins, uploads and the database are all
gitignored, outside the payload, or both. Shipping the payload into an empty
webroot yields a dead site AND stamps the ledger as deployed.
The order that works (josworld → Combell, 2026-09-05):
`.env` → `wp core download` → bootstrap files → `composer install` →
**mail block** → database import → `search-replace` → `wp rewrite flush --hard`
→ payload deploy → licensed assets by hand → uploads.
Two traps inside it: **`composer install` needs `--prefer-source`** when any
package is a private repo — composer's dist path fetches a GitHub API zipball
over HTTPS, which an SSH deploy key cannot authenticate (404), while
`--prefer-source` clones over SSH and works. And **`wp rewrite flush --hard` is
mandatory** after the import, because search-replace empties `rewrite_rules`
and every permalink 404s until it runs.

## Licensed assets are gitignored, not absent — look before asking

A licensed theme or plugin (YOOtheme Pro, FluentBooking Pro) is gitignored and
outside `deploy.payload`, so it never reaches a server by any verb. That does
NOT mean it is missing locally: it usually sits in the project's own working
tree at exactly the right version. Check `app/content/themes/` and
`app/content/plugins/` before asking the human for a zip, and re-apply these by
hand on every new environment — no verb carries them (2026-09-05).

## A child theme whose parent is missing makes `wp theme list` print nothing

Not the child, not an error — an empty table. On a fresh environment that empty
listing plus a blank 200 front page is the signature of a missing licensed
parent theme, while `wp option get template` still names it (2026-09-05).
