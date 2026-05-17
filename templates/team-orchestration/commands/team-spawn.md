---
description: Spawn an ephemeral worker Claude session for a role + ticket in a tmux/cmux pane.
argument-hint: <role> <ticket> [prompt]
disable-model-invocation: true
allowed-tools: Bash(scripts/team_spawn.sh *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/team_spawn.sh $ARGUMENTS`
