#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
TEAM_NAME="${CLAUDE_TEAM_SESSION:-$(basename "$PROJECT_DIR")-team}"
WORKER_WINDOW="workers"

echo "=== Team session ==="
echo "name:    $TEAM_NAME"
echo "project: $PROJECT_DIR"
echo

echo "=== Active worker panes ==="
if command -v tmux >/dev/null 2>&1 \
   && tmux list-windows -t "$TEAM_NAME" -F '#W' 2>/dev/null | grep -qx "$WORKER_WINDOW"; then
  tmux list-panes -t "$TEAM_NAME:$WORKER_WINDOW" \
    -F '#{pane_index}: #{pane_title}  cmd=#{pane_current_command}  pid=#{pane_pid}'
else
  echo "(no workers window or tmux unavailable)"
fi
echo

echo "=== Active tickets ==="
TASKS_DIR="$PROJECT_DIR/.team/tasks"
if [ -d "$TASKS_DIR" ]; then
  for d in "$TASKS_DIR"/*/; do
    [ -d "$d" ] || continue
    ticket=$(basename "$d")
    reports=$(find "$d" -maxdepth 1 -name '*.md' -type f -printf '%f\n' 2>/dev/null \
              || ls -1 "$d"*.md 2>/dev/null | xargs -n1 basename 2>/dev/null)
    echo "- $ticket"
    while IFS= read -r r; do
      [ -n "$r" ] && echo "    $r"
    done <<< "$reports"
  done
else
  echo "(no .team/tasks/ yet)"
fi
echo

echo "=== File ownership rules ==="
OWNERSHIP="$PROJECT_DIR/.team/file-ownership.json"
if [ -f "$OWNERSHIP" ]; then
  cat "$OWNERSHIP"
else
  echo "(no .team/file-ownership.json)"
fi
