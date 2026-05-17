---
description: Run the end-to-end team pipeline (auto-dispatch, 2 user-approval gates).
argument-hint: <ticket>
disable-model-invocation: true
allowed-tools: Bash
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`bash scripts/team_pipeline_spawn.sh $ARGUMENTS`
