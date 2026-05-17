---
description: Start the role-based Claude team using the configured cmux/tmux transport.
argument-hint: [project-dir]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh start *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh start $ARGUMENTS`
