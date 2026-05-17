#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"

if [ $# -lt 1 ]; then
  echo "usage: scripts/team_init.sh <ticket-slug>" >&2
  echo "example: scripts/team_init.sh add-undo-button" >&2
  exit 2
fi

TICKET="$1"
TICKET_DIR="$PROJECT_DIR/.team/tasks/$TICKET"

if [ -d "$TICKET_DIR" ]; then
  echo "Ticket dir already exists: .team/tasks/$TICKET/" >&2
  exit 1
fi

mkdir -p "$TICKET_DIR"
INTAKE="$TICKET_DIR/intake.md"

cat > "$INTAKE" <<EOF
# $TICKET — intake

## User request
<paste the user's original request here>

## Lead notes
- Date opened: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Status: open

## Pipeline plan
- [ ] requirement-analyst
- [ ] researcher
- [ ] architect
- [ ] developer
- [ ] qa-reviewer
- [ ] integration

## Skip justifications
(record any stage skips with one-sentence reasoning)

## Escalation log
(append blocks here when escalation rules fire)
EOF

echo "Created: .team/tasks/$TICKET/intake.md"
echo "Next: edit intake.md, then dispatch the first role:"
echo "  /team-spawn requirement-analyst $TICKET \"<dispatch prompt>\""
