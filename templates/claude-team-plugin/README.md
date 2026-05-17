# claude-team

Subagent + tmux hybrid team orchestration for Claude Code.

A leader Claude session decomposes incoming work, dispatches ephemeral worker
sessions in tmux/cmux panes per role (`requirement-analyst`, `architect`,
`researcher`, `developer`, `qa-reviewer`), enforces per-role file ownership
through a PreToolUse hook, and integrates the workers' markdown reports back
into a single ticket dir under `.team/tasks/<ticket>/`.

This plugin packages the skill that teaches the leader how to decide,
the slash commands that drive the spawn/collect/close loop, the supporting
scripts, the file-ownership hook, and a default project template the
`/team-bootstrap` command writes into a new repo on first use.

## What ships

```
claude-team/
├── plugin.json
├── README.md
├── skills/
│   └── team-orchestration/
│       ├── SKILL.md
│       └── references/{pipeline,dispatch-template,escalation}.md
├── commands/
│   ├── team-bootstrap.md           # /team-bootstrap            (one-time)
│   ├── team-init.md                # /team-init <ticket>
│   ├── team-pipeline.md            # /team-pipeline <ticket>    (auto-flow)
│   ├── team-spawn.md               # /team-spawn <role> <ticket> [prompt]
│   ├── team-collect.md             # /team-collect <role> <ticket>
│   ├── team-close.md               # /team-close <role> [ticket]
│   └── team-status.md              # /team-status
├── hooks/
│   ├── hooks.json                  # PreToolUse(Edit|Write|NotebookEdit)
│   └── team-check-file-ownership.py
├── scripts/
│   ├── team_bootstrap.sh
│   ├── team_init.sh
│   ├── team_pipeline.py            # orchestrator (state machine)
│   ├── team_pipeline_spawn.sh      # opens a new tmux window for the orchestrator
│   ├── team_spawn.sh
│   ├── team_collect.sh
│   ├── team_close.sh
│   └── team_status.sh
└── templates/                      # written into project on /team-bootstrap
    ├── file-ownership.json         # corrected default (no `.team/**` blanket)
    ├── role-presets.json
    └── roles/{lead,requirement-analyst,architect,researcher,developer,qa-reviewer}.md
```

## Install

### Option A — local plugin dir (fastest for testing)

```sh
claude --plugin-dir /path/to/claude-team
```

This loads the plugin for one Claude session only. Useful while developing.

### Option B — install via Claude Code's plugin manager

```
/plugin install <git-url-or-path>
```

The plugin registers under `name: claude-team` and persists across sessions.

### Option C — vendored into a project

Copy the whole `claude-team/` dir into your project (e.g. `vendor/claude-team/`)
and reference it with `--plugin-dir vendor/claude-team` in a wrapper script.

## First-time project setup

In a project with no `.team/` yet, from the lead pane:

```
/team-bootstrap
```

This writes:

| Path | Contents |
|---|---|
| `.team/file-ownership.json` | Default ownership map (per-role report owners) |
| `.team/role-presets.json` | Per-role preferred skills + report formats |
| `.team/roles/<role>.md` | Each role's contract |
| `.team/current-goal.md` | Empty goal placeholder |
| `.team/team-config.json` | `{"transport": "tmux"}` default |
| `.team/{tasks,runtime,logs}/` | Empty dirs |

Pass `--force` to overwrite existing files (e.g. on plugin upgrade).

## Two flows

### A. Automatic pipeline (`/team-pipeline`)

The orchestrator drives the whole loop. The user only types y/n at two gates:

```
/team-init my-ticket             # create the ticket dir, edit intake.md
/team-pipeline my-ticket         # opens a new tmux window 'pipeline-my-ticket'
                                  # → switch with Ctrl-b w to interact
```

What happens behind the gates:

1. requirement-analyst worker spawned, report awaited.
2. Lead model (`claude-opus-4-7` by default) auto-generates a JSON dev plan
   (needs_researcher, needs_architect, implementor_role, expected_files,
   completion_criteria), choosing implementor by file-ownership.json.
3. **Gate 1** — requirement-analyst report + dev plan shown; user types y/n.
4. researcher + architect spawned in parallel (only if plan says so).
5. implementor (the role that owns the artifact path) spawned with full
   context. Report and artifact awaited.
6. qa-reviewer spawned. Approval readiness parsed.
   - `yes`        → continue
   - `yes-with-fixes` → fix-loop (max 5 iterations) routing QA findings back
                        to the implementor. After loop, re-QA.
   - `no` / `unknown` → escalate to user (y to continue another fix-pass).
7. **Gate 2** — final artifact summary + QA approval shown; user types y/n.
8. Lead model writes the integration block (`lead.md`), `--all` worker panes
   are closed.

State persists in `.team/tasks/<ticket>/pipeline.json`. Re-running the same
`/team-pipeline <ticket>` resumes from the last completed stage.

Configurable via env:
- `CLAUDE_TEAM_LEAD_MODEL` (default `claude-opus-4-7`)
- `CLAUDE_TEAM_WORKER_MODEL` (default `claude-sonnet-4-6`)

### B. Manual flow (existing single-step commands)

For debugging, partial runs, or when you want to drive the loop yourself:

From the **lead pane** (a tmux pane running interactive `claude`):

```
/team-init add-undo-button
# edit .team/tasks/add-undo-button/intake.md with the user request

/team-spawn requirement-analyst add-undo-button "Goal: ...
Allowed scope: docs/**, .team/tasks/add-undo-button/**.
Denied scope: src/**.
Completion criteria: acceptance criteria unambiguous.
Required report: .team/tasks/add-undo-button/requirement-analyst.md with
sections 요구사항 요약 / 모호한 점 / 질문 / 구현 전제. Then exit."

/team-collect requirement-analyst add-undo-button
/team-close   requirement-analyst add-undo-button

# then dispatch researcher + architect in parallel, then developer, then qa-reviewer
```

Worker panes spawn in a `workers` window of your tmux team session
(reused across spawns) and stay as `[exited]` after `claude -p` finishes,
so you can scroll back. `/team-close <role> [ticket]` removes them.

The full skill content (when to skip a stage, escalation handling,
parallelization rules) is loaded from `skills/team-orchestration/SKILL.md`
and surfaces automatically when the lead session triggers
`/team-orchestration` or matches the description.

## Requirements

- `tmux` on PATH (cmux transport is wired into companion `claude_team.sh` —
  not yet integrated here; add a transport branch in `team_spawn.sh` if
  you primarily use cmux).
- A pre-existing 6-pane team session: this plugin assumes one already exists
  (e.g. via the project's `scripts/claude_team.sh start`). The plugin spawns
  workers into a `workers` window of that session.

## Permission model

- The included `team-check-file-ownership.py` hook fires on `Edit`, `Write`,
  and `NotebookEdit` tool calls. It reads `.team/file-ownership.json` from
  the project root (`CLAUDE_PROJECT_DIR`) and:
  1. Blocks if the path matches an explicit `owners.<pattern>` and the
     current `CLAUDE_TEAM_ROLE` is not the listed owner.
  2. Blocks if the path matches the role's `deny` patterns.
  3. Blocks if the role has any `allow` patterns and the path matches none.
- Workers run with `--permission-mode acceptEdits`, so allowed Write calls
  go through automatically; denied ones still surface the hook's stderr in
  the worker pane and the worker reports back without producing the file.

### Known gap

The hook gates LLM `Edit/Write/NotebookEdit` tool calls but does **not** gate
shell-side file operations (`cp`, `mv`, `tee`, `>` redirection) invoked via
the `Bash` tool. A worker that uses `Bash` with `cp` could in principle
write outside its allow-scope. To close this, extend
`team-guard-bash.py` (companion hook) with file-modifying command patterns
and run them through the same allow/deny check.

## Versioning

`0.1.0` — initial extract from the `word-card-game` project's Phase 1
implementation. Validated end-to-end via a smoke ticket
(`researcher` role wrote a report at `.team/tasks/smoke-test/researcher.md`
through the spawn-collect-close loop).
