# Team Orchestration — Phase 1 Install

This staging directory contains a working team-orchestration scaffold built
under `templates/` (the only path the developer role can write to). It needs
to be promoted into the live `.claude/` and `scripts/` trees by the **lead**
role, because those targets are owned by lead per `.team/file-ownership.json`.

## What it ships

```
templates/team-orchestration/
├── INSTALL.md                                        # this file
├── install.sh                                        # deploy script (lead runs)
├── skills/
│   └── team-orchestration/
│       ├── SKILL.md                                  # trigger + playbook
│       └── references/
│           ├── pipeline.md                           # 5-stage pipeline rules
│           ├── dispatch-template.md                  # mandatory prompt format
│           └── escalation.md                         # QA fail / risk / gap handling
├── commands/
│   ├── team-init.md                                  # /team-init <ticket>
│   ├── team-spawn.md                                 # /team-spawn <role> <ticket> [prompt]
│   ├── team-collect.md                               # /team-collect <role> <ticket>
│   ├── team-close.md                                 # /team-close <role> [ticket]
│   └── team-status.md                                # /team-status
└── scripts/
    ├── team_init.sh
    ├── team_spawn.sh
    ├── team_collect.sh
    ├── team_close.sh
    └── team_status.sh
```

After deploy, these land at:

| Staging | Deployed |
|---|---|
| `templates/team-orchestration/skills/...` | `.claude/skills/team-orchestration/...` |
| `templates/team-orchestration/commands/*.md` | `.claude/commands/*.md` |
| `templates/team-orchestration/scripts/*.sh` | `scripts/*.sh` (chmod 755) |

## Why staging instead of direct install

The current Claude session is bound to `developer` role. Per
`.team/file-ownership.json`:

- developer.allow: `src/**`, `tests/**`, `templates/**`
- `.claude/skills/**`, `.claude/commands/**`, `scripts/**` are not in allow → blocked
- `.team/**` is owned by lead → blocked

This is the system working as designed. Promotion to live paths must be done
by the lead role, where allow includes `.team/**`, `docs/**`, and `*.md`.

## How to deploy (from the lead pane)

1. **Switch to the lead pane** in tmux/cmux.
2. **Sanity-check the staging contents**:
   ```sh
   ls templates/team-orchestration/
   bash templates/team-orchestration/install.sh        # dry run, prints plan
   ```
3. **Apply**:
   ```sh
   bash templates/team-orchestration/install.sh --apply
   ```
   To overwrite existing files (e.g. on a re-install), add `--force`.
4. **Verify**:
   ```sh
   ls .claude/skills/team-orchestration/
   ls .claude/commands/team-*.md
   ls scripts/team_*.sh
   ```
5. **Smoke test** (still in the lead pane, with the 6-pane team session running):
   ```sh
   /team-init smoke-test
   /team-spawn researcher smoke-test "Goal: confirm the spawn flow works.\
   Context: smoke test only.\
   Allowed scope: docs/**, .team/tasks/smoke-test/**.\
   Denied scope: src/**.\
   Completion criteria: write a one-line report.\
   Required report: write to .team/tasks/smoke-test/researcher.md with\
   sections: 조사 범위 / 근거 파일 / 현재 동작 / 리스크.\
   Then exit."
   /team-collect researcher smoke-test
   /team-close researcher smoke-test
   ```

## Phase 2 — extract to plugin

After Phase 1 validation in this project (one or two real tickets dispatched
end-to-end), the same files lift cleanly into a Claude Code plugin:

```
claude-team/                 # new repo
├── plugin.json
├── skills/team-orchestration/
├── commands/
├── scripts/
├── hooks/
│   └── pre-tool-use/check-file-ownership.json   # carry the existing hook
├── templates/
│   ├── roles/                                   # default role .md files
│   ├── role-presets.json
│   └── file-ownership.json                      # default config
└── README.md
```

Path adjustments needed at extraction time:

- Slash commands: replace `scripts/team_*.sh` paths with `${CLAUDE_PLUGIN_ROOT}/scripts/team_*.sh`.
- Scripts: keep `${CLAUDE_PROJECT_DIR}` for project state references — that
  stays correct.
- Hook: the existing `team-check-file-ownership.py` in this project already
  resolves project root via env, so it ports unchanged. Move it under
  `hooks/pre-tool-use/` in the plugin.

Don't extract before Phase 1 catches at least one real bug in the dispatch
loop — plugin abstraction amplifies what works AND what's broken.

## Known limitations (Phase 1)

- **tmux only**. cmux transport in `claude_team.sh` is not yet wired into
  `team_spawn.sh`. Add a transport branch in Phase 2 if cmux is the primary.
- **No automated retry**. QA fail loop is documented in `escalation.md` but
  Lead has to drive the loop manually.
- **No prompt linter**. The dispatch template is enforced by convention, not
  by a hook. A `team-dispatch-lint.py` PreToolUse hook could check for the
  six required fields before the worker reads stdin.
- **`claude -p` exit behavior**. The pane stays open after exit (because the
  team session uses `remain-on-exit on`). `/team-close` is needed to clean up.
  Consider adding `tmux set-option -p remain-on-exit off` in `team_spawn.sh`
  if auto-close is preferred.
