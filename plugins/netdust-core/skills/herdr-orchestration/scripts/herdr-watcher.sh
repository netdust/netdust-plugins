#!/bin/bash
# herdr blocked-state watcher — trial run.
# Polls a pane's agent state; notifies Stefan on transitions that need him.
# Usage: herdr-watcher.sh <pane-id> <label>
TARGET="${1:-w3:p4}"
LABEL="${2:-daan-23}"
prev=""
while true; do
  st=$(herdr agent get "$TARGET" 2>/dev/null | grep -o '"agent_status":"[a-z]*"' | head -1 | cut -d'"' -f4)
  [ -z "$st" ] && st="gone"
  if [ "$st" != "$prev" ]; then
    case "$st" in
      blocked)
        herdr notification show "$LABEL needs you" \
          --body "Pane $TARGET is waiting on an approval or question" \
          --position top-right --sound request ;;
      idle|done)
        if [ "$prev" = "working" ] || [ "$prev" = "blocked" ]; then
          herdr notification show "$LABEL settled ($st)" \
            --body "Pane $TARGET finished its run" \
            --position top-right --sound done
        fi ;;
      gone)
        herdr notification show "$LABEL watcher stopped" \
          --body "No agent detected in $TARGET anymore" \
          --position top-right --sound none
        exit 0 ;;
    esac
    echo "$(date +%H:%M:%S) $prev -> $st"
    prev="$st"
  fi
  sleep 15
done
