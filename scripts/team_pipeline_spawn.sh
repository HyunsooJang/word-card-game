#!/usr/bin/env bash
# Slash-command shim: open a NEW tmux window in the team session and run
# team_pipeline.py inside it. The user then switches to that window to
# interact with the pipeline (Gate 1 / Gate 2 stdin prompts).
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
TEAM_NAME="${CLAUDE_TEAM_SESSION:-$(basename "$PROJECT_DIR")-team}"

if [ $# -lt 1 ]; then
  echo "usage: scripts/team_pipeline_spawn.sh <ticket>" >&2
  exit 2
fi
TICKET="$1"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found. Pipeline requires tmux." >&2; exit 1
fi
if ! tmux has-session -t "$TEAM_NAME" 2>/dev/null; then
  echo "tmux session not found: $TEAM_NAME (run scripts/claude_team.sh start)" >&2
  exit 1
fi

WIN="pipeline-$TICKET"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if tmux list-windows -t "$TEAM_NAME" -F '#W' | grep -qx "$WIN"; then
  echo "Pipeline window already exists: $TEAM_NAME:$WIN" >&2
  echo "Switch to it (Ctrl-b w) or close it first via team_close." >&2
  exit 1
fi

tmux new-window -t "$TEAM_NAME" -n "$WIN" -c "$PROJECT_DIR"
tmux set-window-option -t "$TEAM_NAME:$WIN" remain-on-exit on >/dev/null 2>&1 || true

# Launch the orchestrator with lead role env so its file writes pass the hook.
tmux send-keys -t "$TEAM_NAME:$WIN" \
  "CLAUDE_TEAM_ROLE=lead CLAUDE_PROJECT_DIR=$(printf %q "$PROJECT_DIR") \
CLAUDE_TEAM_ROOT=$(printf %q "$PROJECT_DIR") \
python3 $(printf %q "$SCRIPT_DIR/team_pipeline.py") $(printf %q "$TICKET")" C-m

echo "Pipeline started in $TEAM_NAME:$WIN"
echo "Switch to it with Ctrl-b w (or  tmux select-window -t $TEAM_NAME:$WIN )"
echo "User stdin gates will pause inside that window — go there to approve."
