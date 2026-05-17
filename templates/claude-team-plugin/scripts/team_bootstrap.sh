#!/usr/bin/env bash
# Bootstrap a project's .team/ skeleton from the plugin's default templates.
# Run from the project root (or pass project dir via CLAUDE_PROJECT_DIR).
#
#   /team-bootstrap          # idempotent, skips existing files
#   /team-bootstrap --force  # overwrite even if files exist
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

PLUGIN_TEMPLATES="$PLUGIN_ROOT/templates"
if [ ! -d "$PLUGIN_TEMPLATES" ]; then
  echo "Plugin templates not found at: $PLUGIN_TEMPLATES" >&2
  exit 1
fi

mkdir -p \
  "$PROJECT_DIR/.team/tasks" \
  "$PROJECT_DIR/.team/runtime" \
  "$PROJECT_DIR/.team/logs" \
  "$PROJECT_DIR/.team/roles"

copy_if_absent() {
  local src="$1" dst="$2"
  if [ -e "$dst" ] && [ "$FORCE" -ne 1 ]; then
    echo "SKIP   $dst (exists; pass --force to overwrite)"
  else
    cp "$src" "$dst"
    echo "WRITE  $dst"
  fi
}

# Defaults
copy_if_absent "$PLUGIN_TEMPLATES/file-ownership.json" "$PROJECT_DIR/.team/file-ownership.json"
copy_if_absent "$PLUGIN_TEMPLATES/role-presets.json"   "$PROJECT_DIR/.team/role-presets.json"
for role in lead requirement-analyst architect researcher developer qa-reviewer; do
  copy_if_absent "$PLUGIN_TEMPLATES/roles/$role.md" "$PROJECT_DIR/.team/roles/$role.md"
done

# Empty/placeholder docs
GOAL="$PROJECT_DIR/.team/current-goal.md"
if [ ! -f "$GOAL" ] || [ "$FORCE" -eq 1 ]; then
  cat > "$GOAL" <<'EOF'
# Current Goal

(set the active multi-role goal here — what the team is currently working on)
EOF
  echo "WRITE  $GOAL"
else
  echo "SKIP   $GOAL"
fi

CONFIG="$PROJECT_DIR/.team/team-config.json"
if [ ! -f "$CONFIG" ] || [ "$FORCE" -eq 1 ]; then
  cat > "$CONFIG" <<'EOF'
{
  "transport": "tmux"
}
EOF
  echo "WRITE  $CONFIG"
else
  echo "SKIP   $CONFIG"
fi

echo
echo "Bootstrap complete in $PROJECT_DIR/.team/"
echo "Next: open a tmux team session (your existing scripts/claude_team.sh start, or start one),"
echo "      then dispatch from the lead pane: /team-init <ticket>  →  /team-spawn <role> ..."
