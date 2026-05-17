#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
TEAM_NAME="${CLAUDE_TEAM_SESSION:-$(basename "$PROJECT_DIR")-team}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
WORKER_MODEL="${CLAUDE_TEAM_WORKER_MODEL:-claude-sonnet-4-6}"
WORKER_WINDOW="workers"

usage() {
  cat <<'MSG'
usage:
  scripts/team_spawn.sh <role> <ticket> "<inline prompt>"
  scripts/team_spawn.sh <role> <ticket> @<path-to-prompt-file>
  scripts/team_spawn.sh <role> <ticket>     # opens interactive pane (no prompt)

roles: lead | requirement-analyst | architect | researcher | developer | qa-reviewer

The pane is opened in the "workers" window of the existing tmux team session
(create it first via scripts/claude_team.sh start). The worker writes its
report to .team/tasks/<ticket>/<role>.md and (in -p mode) exits.
MSG
}

[ $# -ge 2 ] || { usage; exit 2; }

ROLE="$1"
TICKET="$2"
shift 2

case "$ROLE" in
  lead|requirement-analyst|architect|researcher|developer|qa-reviewer) ;;
  *) echo "Unknown role: $ROLE" >&2; exit 2 ;;
esac

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found. Phase 1 spawn requires tmux; cmux support is a follow-up." >&2
  exit 1
fi

if ! tmux has-session -t "$TEAM_NAME" 2>/dev/null; then
  echo "tmux session not found: $TEAM_NAME" >&2
  echo "Start the team first: scripts/claude_team.sh start" >&2
  exit 1
fi

TICKET_DIR="$PROJECT_DIR/.team/tasks/$TICKET"
mkdir -p "$TICKET_DIR"

PROMPT_FILE=""
INLINE_PROMPT=""
if [ $# -gt 0 ]; then
  if [[ "$1" == @* ]]; then
    PROMPT_FILE="${1#@}"
    [ -f "$PROMPT_FILE" ] || { echo "Prompt file not found: $PROMPT_FILE" >&2; exit 2; }
  else
    INLINE_PROMPT="$*"
    PROMPT_FILE="$(mktemp -t team-spawn-prompt.XXXXXX)"
    printf '%s\n' "$INLINE_PROMPT" > "$PROMPT_FILE"
  fi
fi

if ! tmux list-windows -t "$TEAM_NAME" -F '#W' | grep -qx "$WORKER_WINDOW"; then
  tmux new-window -t "$TEAM_NAME" -n "$WORKER_WINDOW" -c "$PROJECT_DIR"
  tmux send-keys -t "$TEAM_NAME:$WORKER_WINDOW" "echo 'team-orchestration workers'" C-m
fi
tmux set-window-option -t "$TEAM_NAME:$WORKER_WINDOW" remain-on-exit on >/dev/null 2>&1 || true

PANE_TITLE="$ROLE:$TICKET"
LAUNCHER="$(mktemp -t team-spawn-launch.XXXXXX)"
LOG_FILE="$PROJECT_DIR/.team/tasks/$TICKET/$ROLE.log"

{
  echo '#!/usr/bin/env bash'
  printf 'cd %q\n' "$PROJECT_DIR"
  printf 'export CLAUDE_TEAM_ROLE=%q\n' "$ROLE"
  printf 'export CLAUDE_PROJECT_DIR=%q\n' "$PROJECT_DIR"
  printf 'export CLAUDE_TEAM_ROOT=%q\n' "$PROJECT_DIR"
  printf 'printf "\\033]2;%%s\\033\\\\" %q\n' "$PANE_TITLE"
  echo 'clear'
  printf 'echo "=== %s ==="\n' "$PANE_TITLE"
  printf 'echo "Report: .team/tasks/%s/%s.md"\n' "$TICKET" "$ROLE"
  printf 'echo "Log:    .team/tasks/%s/%s.log"\n' "$TICKET" "$ROLE"
  echo 'echo'
  if [ -n "$PROMPT_FILE" ]; then
    printf 'LOG=%q\n' "$LOG_FILE"
    printf '%q --model %q -p --permission-mode acceptEdits --no-session-persistence < %q 2>&1 | tee "$LOG"\n' "$CLAUDE_BIN" "$WORKER_MODEL" "$PROMPT_FILE"
    echo 'rc=${PIPESTATUS[0]}'
    echo 'echo'
    echo 'echo "=== worker exited (status: $rc) ==="'
  else
    printf 'exec %q --model %q\n' "$CLAUDE_BIN" "$WORKER_MODEL"
  fi
} > "$LAUNCHER"
chmod +x "$LAUNCHER"

tmux split-window -t "$TEAM_NAME:$WORKER_WINDOW" -c "$PROJECT_DIR" "$LAUNCHER"
tmux select-layout -t "$TEAM_NAME:$WORKER_WINDOW" tiled >/dev/null
NEW_PANE="$(tmux display-message -p -t "$TEAM_NAME:$WORKER_WINDOW" '#{pane_id}')"
tmux select-pane -t "$NEW_PANE" -T "$PANE_TITLE"

echo "Spawned worker pane: $PANE_TITLE  ($NEW_PANE)"
echo "Report will be at: .team/tasks/$TICKET/$ROLE.md"
echo "View with: tmux select-window -t $TEAM_NAME:$WORKER_WINDOW"
