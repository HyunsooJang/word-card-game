---
description: Print the report file written by a worker for a given role + ticket.
argument-hint: <role> <ticket>
disable-model-invocation: true
allowed-tools: Bash
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/team_collect.sh" $ARGUMENTS`
