---
description: Send a task message to a Claude team role.
argument-hint: [role-or-index] [message]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh send *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh send $ARGUMENTS`

Sent:

```
$ARGUMENTS
```
