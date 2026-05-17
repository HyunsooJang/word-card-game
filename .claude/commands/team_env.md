---
description: Print the environment used for a Claude team role.
argument-hint: [role-or-index]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh env *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh env $ARGUMENTS`
