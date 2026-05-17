---
description: Capture recent output from one role or all Claude team roles.
argument-hint: [role-or-index]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh capture *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh capture $ARGUMENTS`
