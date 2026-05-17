---
description: Bootstrap a ticket directory under .team/tasks/<ticket>/ with intake.md.
argument-hint: <ticket>
disable-model-invocation: true
allowed-tools: Bash(scripts/team_init.sh *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/team_init.sh $ARGUMENTS`
