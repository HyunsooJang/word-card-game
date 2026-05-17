---
description: Close an ephemeral worker pane for a role.
argument-hint: <role> [ticket]
disable-model-invocation: true
allowed-tools: Bash
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/team_close.sh" $ARGUMENTS`
