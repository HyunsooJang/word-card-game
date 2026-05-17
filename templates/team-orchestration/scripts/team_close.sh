#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
TEAM_NAME="${CLAUDE_TEAM_SESSION:-$(basename "$PROJECT_DIR")-team}"
WORKER_WINDOW="workers"

if [ $# -lt 1 ]; then
  echo "usage: scripts/team_close.sh <role> [ticket]" >&2
  echo "       scripts/team_close.sh --all                 # close every worker pane" >&2
  exit 2
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found." >&2
  exit 1
fi

if ! tmux list-windows -t "$TEAM_NAME" -F '#W' 2>/dev/null | grep -qx "$WORKER_WINDOW"; then
  echo "No workers window in $TEAM_NAME." >&2
  exit 0
fi

if [ "$1" = "--all" ]; then
  tmux list-panes -t "$TEAM_NAME:$WORKER_WINDOW" -F '#{pane_id}' | while read -r pane; do
    tmux kill-pane -t "$pane" 2>/dev/null || true
  done
  echo "Closed all worker panes in $TEAM_NAME:$WORKER_WINDOW"
  exit 0
fi

ROLE="$1"
TICKET="${2:-}"
TARGET="$ROLE${TICKET:+:$TICKET}"

PANES=$(tmux list-panes -t "$TEAM_NAME:$WORKER_WINDOW" -F '#{pane_id}::#{pane_title}' \
  | awk -F:: -v t="$TARGET" 'index($2, t) == 1 { print $1 }')

if [ -z "$PANES" ]; then
  echo "No worker pane matching: $TARGET" >&2
  exit 1
fi

count=0
while IFS= read -r pane; do
  [ -n "$pane" ] || continue
  tmux kill-pane -t "$pane" 2>/dev/null && count=$((count+1)) || true
done <<< "$PANES"

echo "Closed $count pane(s) matching: $TARGET"
