#!/usr/bin/env bash
# Phase 1 deploy: copy team-orchestration staging into the project's
# .claude/ and scripts/ trees. Must be run from the LEAD pane (the only
# role with allow-scope covering .team/** and the right CLAUDE.md edits).
#
# Run from project root:
#   bash templates/team-orchestration/install.sh           # dry run
#   bash templates/team-orchestration/install.sh --apply   # actually copy
#   bash templates/team-orchestration/install.sh --apply --force   # overwrite

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
STAGING="$PROJECT_DIR/templates/team-orchestration"

APPLY=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --apply) APPLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [ ! -d "$STAGING" ]; then
  echo "Staging dir not found: $STAGING" >&2
  exit 1
fi

ROLE="${CLAUDE_TEAM_ROLE:-unknown}"
if [ "$ROLE" != "lead" ]; then
  echo "Warning: CLAUDE_TEAM_ROLE=$ROLE — install must run as lead." >&2
  echo "         The file-ownership hook will block writes to .claude/** and scripts/** otherwise." >&2
  echo "         If you're sure (e.g. running outside Claude), add CLAUDE_TEAM_ROLE=lead to env." >&2
fi

declare -a OPS=()

queue_copy() {
  local src="$1" dst="$2" mode="${3:-}"
  if [ -e "$dst" ] && [ "$FORCE" -ne 1 ]; then
    OPS+=("SKIP   $dst (exists; pass --force to overwrite)")
  else
    OPS+=("COPY   $src -> $dst${mode:+ (chmod $mode)}")
    if [ "$APPLY" -eq 1 ]; then
      mkdir -p "$(dirname "$dst")"
      cp "$src" "$dst"
      if [ -n "$mode" ]; then chmod "$mode" "$dst"; fi
    fi
  fi
}

# Skill
queue_copy "$STAGING/skills/team-orchestration/SKILL.md" \
           "$PROJECT_DIR/.claude/skills/team-orchestration/SKILL.md"
for ref in "$STAGING/skills/team-orchestration/references"/*.md; do
  [ -e "$ref" ] || continue
  base="$(basename "$ref")"
  queue_copy "$ref" "$PROJECT_DIR/.claude/skills/team-orchestration/references/$base"
done

# Slash commands
for cmd in "$STAGING/commands"/*.md; do
  [ -e "$cmd" ] || continue
  base="$(basename "$cmd")"
  queue_copy "$cmd" "$PROJECT_DIR/.claude/commands/$base"
done

# Scripts (.sh and .py)
for script in "$STAGING/scripts"/*.sh "$STAGING/scripts"/*.py; do
  [ -e "$script" ] || continue
  base="$(basename "$script")"
  queue_copy "$script" "$PROJECT_DIR/scripts/$base" 755
done

# Hooks (only files we ship; do not touch other .claude/hooks/* in the project)
if [ -d "$STAGING/hooks" ]; then
  for hook in "$STAGING/hooks"/*; do
    [ -e "$hook" ] || continue
    base="$(basename "$hook")"
    queue_copy "$hook" "$PROJECT_DIR/.claude/hooks/$base" 755
  done
fi

echo "=== team-orchestration install plan ==="
for op in "${OPS[@]}"; do
  echo "  $op"
done
echo

if [ "$APPLY" -ne 1 ]; then
  echo "Dry run only. Re-run with --apply to copy files."
  echo "Re-run with --apply --force to overwrite existing files."
  exit 0
fi

echo "Done."
echo
echo "Next steps (from lead pane):"
echo "  1. Verify: ls .claude/skills/team-orchestration/ .claude/commands/ scripts/"
echo "  2. Make sure tmux team session is running: scripts/claude_team.sh start"
echo "  3. Try: /team-init <ticket-slug>"
echo "  4. Then: /team-spawn requirement-analyst <ticket> \"<dispatch prompt>\""
