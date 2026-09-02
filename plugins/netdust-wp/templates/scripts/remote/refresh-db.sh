#!/bin/bash
# Copy the production database into a non-production environment.
# Runs ON the Combell host — all sites share it, so nothing round-trips.
#
# Usage: refresh-db.sh <src_path> <dst_path> <src_url> <dst_url> <state_dir> <env> [wp_path]
#
# wp_path is the WordPress core directory relative to the site path. Bedrock
# uses web/wp, the custom stack uses wp, a standard install passes "" because
# WordPress sits at the root.
set -euo pipefail

SRC="$1"; DST="$2"; SRC_URL="$3"; DST_URL="$4"; STATE_DIR="$5"; ENV_NAME="$6"; WP_PATH="${7:-wp}"
WP_FLAG=()
[ -n "$WP_PATH" ] && WP_FLAG=(--path="$WP_PATH")
STAMP=$(date +%Y%m%d-%H%M%S)
DUMP="/tmp/vad-refresh-$STAMP.sql"

if [ "$ENV_NAME" = "production" ] || [ "$DST" = "$SRC" ]; then
  echo "refresh-db: refused — target is production" >&2
  exit 1
fi

echo "Backing up $ENV_NAME database..."
mkdir -p "$STATE_DIR/backups"
( cd "$DST" && wp db export "${WP_FLAG[@]}" --default-character-set=utf8mb4 - ) \
  | gzip > "$STATE_DIR/backups/db-$ENV_NAME-$STAMP.sql.gz"

echo "Exporting production database..."
# NOTE: this sed is duplicated in the Makefile's _pull-db target, which does the
# same job for production -> local. Change both together.
#
# Strip DEFINER clauses: the views are owned by the production DB user and the
# target user lacks SUPER/SET_USER_ID, so importing them verbatim fails with
# ERROR 1227. Dropping the clause makes the definer the importing user, and
# SQL SECURITY INVOKER keeps the views usable.
( cd "$SRC" && wp db export "${WP_FLAG[@]}" --default-character-set=utf8mb4 --single-transaction --quick - ) \
  | sed -E 's/DEFINER=[^ ]+ / /g; s/SQL SECURITY DEFINER/SQL SECURITY INVOKER/g' \
  > "$DUMP"

echo "Importing into $ENV_NAME..."
( cd "$DST" && wp db import "$DUMP" "${WP_FLAG[@]}" )
rm -f "$DUMP"

echo "Rewriting URLs: $SRC_URL -> $DST_URL"
( cd "$DST" && wp search-replace "$SRC_URL" "$DST_URL" --all-tables --precise --skip-columns=guid "${WP_FLAG[@]}" --quiet )

echo "Restoring mail simulation (the import overwrote it)..."
( cd "$DST" && wp eval '
$o = get_option( "fluentmail-settings", array() );
if ( ! is_array( $o ) ) { $o = array(); }
if ( ! isset( $o["misc"] ) || ! is_array( $o["misc"] ) ) { $o["misc"] = array(); }
$o["misc"]["simulate_emails"] = "yes";
update_option( "fluentmail-settings", $o );
$check = get_option( "fluentmail-settings" );
echo "simulate_emails=" . $check["misc"]["simulate_emails"] . PHP_EOL;
' "${WP_FLAG[@]}" )

# Transients are deliberately left alone. Deleting them all wipes run-once
# guards and re-runs migrations — see the June 2026 incident.
echo "Done. Views imported: $( cd "$DST" && wp db query "SELECT COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA=DATABASE();" --skip-column-names "${WP_FLAG[@]}" 2>/dev/null || echo '?' )"
