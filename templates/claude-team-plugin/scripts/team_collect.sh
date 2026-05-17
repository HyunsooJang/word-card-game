#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"

if [ $# -lt 2 ]; then
  echo "usage: scripts/team_collect.sh <role> <ticket>" >&2
  echo "       scripts/team_collect.sh <ticket>          # all reports for ticket" >&2
  exit 2
fi

if [ $# -eq 1 ]; then
  TICKET="$1"
  TICKET_DIR="$PROJECT_DIR/.team/tasks/$TICKET"
  if [ ! -d "$TICKET_DIR" ]; then
    echo "No ticket dir: $TICKET_DIR" >&2
    exit 1
  fi
  for f in "$TICKET_DIR"/*.md; do
    [ -e "$f" ] || continue
    echo "===== $f ====="
    cat "$f"
    echo
  done
  exit 0
fi

ROLE="$1"
TICKET="$2"
REPORT="$PROJECT_DIR/.team/tasks/$TICKET/$ROLE.md"

if [ ! -f "$REPORT" ]; then
  echo "No report yet: .team/tasks/$TICKET/$ROLE.md" >&2
  echo "(worker may still be running — check with: scripts/team_status.sh)" >&2
  exit 1
fi

echo "===== .team/tasks/$TICKET/$ROLE.md ====="
cat "$REPORT"
