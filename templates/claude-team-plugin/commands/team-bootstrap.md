---
description: One-time bootstrap of .team/ skeleton in the current project (ownership, roles, presets, dirs).
argument-hint: [--force]
disable-model-invocation: true
allowed-tools: Bash
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`bash "${CLAUDE_PLUGIN_ROOT}/scripts/team_bootstrap.sh" $ARGUMENTS`
