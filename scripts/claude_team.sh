#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-${CLAUDE_TEAM_ROOT:-$(pwd)}}"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
TEAM_NAME="${CLAUDE_TEAM_SESSION:-${PROJECT_NAME}-team}"
CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_ARGS="${CLAUDE_ARGS:-}"
TEAM_CONFIG="$PROJECT_DIR/.team/team-config.json"
SURFACE_FILE="$PROJECT_DIR/.team/cmux-surfaces.json"
TRANSPORT="${CLAUDE_TEAM_TRANSPORT:-}"

ROLES=(lead requirement-analyst architect researcher developer qa-reviewer)

usage() {
  cat <<'MSG'
usage:
  scripts/claude_team.sh start [project-dir] [--transport cmux|tmux] [--attach]
  scripts/claude_team.sh list
  scripts/claude_team.sh send <role-or-index> <message...>
  scripts/claude_team.sh capture [role-or-index]
  scripts/claude_team.sh env <role-or-index>
  scripts/claude_team.sh install-commands [--force]

Environment:
  CLAUDE_TEAM_TRANSPORT=cmux|tmux
  CLAUDE_TEAM_SESSION=<session-name>
  CLAUDE_BIN=claude
  CLAUDE_ARGS=<extra args>
MSG
}

json_value() {
  python3 - "$@" <<'PY'
import json
import sys
from pathlib import Path

mode = sys.argv[1]

def load(path):
    return json.loads(Path(path).read_text())

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

if mode == "transport":
    path = Path(sys.argv[2])
    print(load(path).get("transport", "cmux") if path.exists() else "cmux")
elif mode == "target":
    data = load(sys.argv[2])
    target = sys.argv[3].strip().lower()
    aliases = {
        "leader": "lead",
        "requirements": "requirement-analyst",
        "dev": "developer",
        "qa": "qa-reviewer",
        "reviewer": "qa-reviewer",
    }
    target = aliases.get(target, target)
    for surface in data.get("surfaces", []):
        if str(surface.get("index")) == target or surface.get("role") == target:
            print(surface["surface_id"])
            raise SystemExit(0)
    raise SystemExit(f"Unknown team target: {target}")
elif mode == "list-surfaces":
    data = load(sys.argv[2])
    for surface in data.get("surfaces", []):
        print(f'{surface["index"]}: {surface["title"]} role={surface["role"]} surface={surface["surface_id"]}')
elif mode == "surface-ids":
    data = json.loads(sys.argv[2])
    ids = []
    for item in walk(data):
        for key in ("surface_id", "surfaceId"):
            value = item.get(key)
            if isinstance(value, str) and value not in ids:
                ids.append(value)
    print("\n".join(ids))
elif mode == "identify-surface":
    data = json.loads(sys.argv[2])
    for item in walk(data):
        for key in ("surface_id", "surfaceId", "surface"):
            value = item.get(key)
            if isinstance(value, str) and value:
                print(value)
                raise SystemExit(0)
    raise SystemExit("Could not find current cmux surface id")
elif mode == "new-surface":
    before = set(filter(None, Path(sys.argv[2]).read_text().splitlines()))
    after = list(filter(None, Path(sys.argv[3]).read_text().splitlines()))
    for item in after:
        if item not in before:
            print(item)
            raise SystemExit(0)
    raise SystemExit("Could not identify new cmux surface")
elif mode == "role":
    target = sys.argv[2].strip().lower()
    mapping = {
        "0": "lead",
        "lead": "lead",
        "leader": "lead",
        "1": "requirement-analyst",
        "requirement-analyst": "requirement-analyst",
        "requirements": "requirement-analyst",
        "2": "architect",
        "architect": "architect",
        "3": "researcher",
        "researcher": "researcher",
        "4": "developer",
        "developer": "developer",
        "dev": "developer",
        "5": "qa-reviewer",
        "qa-reviewer": "qa-reviewer",
        "qa": "qa-reviewer",
        "reviewer": "qa-reviewer",
    }
    print(mapping.get(target, target))
elif mode == "write-surfaces":
    path = Path(sys.argv[2])
    project_dir = Path(sys.argv[3])
    team_name = sys.argv[4]
    surfaces = sys.argv[5:]
    roles = ["lead", "requirement-analyst", "architect", "researcher", "developer", "qa-reviewer"]
    titles = [
        f"{project_dir.name}-lead",
        f"{project_dir.name}-requirements",
        f"{project_dir.name}-architect",
        f"{project_dir.name}-researcher",
        f"{project_dir.name}-developer",
        f"{project_dir.name}-qa",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "transport": "cmux",
        "team_name": team_name,
        "project_dir": str(project_dir),
        "surfaces": [
            {"index": index, "role": role, "title": titles[index], "surface_id": surface_id}
            for index, (role, surface_id) in enumerate(zip(roles, surfaces, strict=True))
        ],
    }, indent=2, ensure_ascii=False) + "\n")
else:
    raise SystemExit(f"unknown mode: {mode}")
PY
}

transport() {
  if [ -n "$TRANSPORT" ]; then
    echo "$TRANSPORT"
  else
    json_value transport "$TEAM_CONFIG"
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 was not found in PATH. Run: npx create-claude-team-cmux doctor --transport $(transport) --install" >&2
    exit 1
  fi
}

role_for_target() {
  json_value role "$1"
}

role_project_dir() {
  local role="$1"
  local worktree="$PROJECT_DIR/.claude/worktrees/$role"
  if [ -d "$worktree/.git" ] || [ -f "$worktree/.git" ]; then
    echo "$worktree"
  else
    echo "$PROJECT_DIR"
  fi
}

install_commands_to_dir() {
  local target_dir="$1"
  local force="$2"
  local silent="${3:-0}"
  local old_project_dir="$PROJECT_DIR"
  PROJECT_DIR="$target_dir"
  if [ "$silent" = "1" ]; then
    if [ "$force" = "1" ]; then
      cmd_install_commands --force >/dev/null
    else
      cmd_install_commands >/dev/null
    fi
  else
    if [ "$force" = "1" ]; then
      cmd_install_commands --force
    else
      cmd_install_commands
    fi
  fi
  PROJECT_DIR="$old_project_dir"
}

prepare_role_project_dir() {
  local role="$1"
  local dir
  dir="$(role_project_dir "$role")"
  install_commands_to_dir "$dir" 1 1
  if [ "$dir" != "$PROJECT_DIR" ]; then
    mkdir -p "$dir/scripts"
    cp "$PROJECT_DIR/scripts/claude_team.sh" "$dir/scripts/claude_team.sh"
    chmod 755 "$dir/scripts/claude_team.sh"
  fi
}

role_env() {
  local role="$1"
  local dir
  dir="$(role_project_dir "$role")"
  mkdir -p "$PROJECT_DIR/.team/runtime/$role"
  cat <<ENV
cd "$(printf "%q" "$dir")"
export CLAUDE_TEAM_ROLE="$(printf "%q" "$role")"
export CLAUDE_PROJECT_DIR="$(printf "%q" "$dir")"
export CLAUDE_TEAM_ROOT="$(printf "%q" "$PROJECT_DIR")"
export CLAUDE_SESSION_NAME="$(printf "%q" "$PROJECT_NAME-$role")"
export CLAUDE_TEAM_SESSION="$(printf "%q" "$TEAM_NAME")"
export CLAUDE_TEAM_TRANSPORT="$(printf "%q" "$(transport)")"
export HARNESS_DATABASE_URL="sqlite+aiosqlite:///$PROJECT_DIR/.team/runtime/$role/harness.db"
export HARNESS_ARTIFACT_STORAGE_PATH="$PROJECT_DIR/.team/runtime/$role/artifacts"
ENV
}

launch_command() {
  local role="$1"
  local title="$PROJECT_NAME-$role"
  local env_lines
  env_lines="$(role_env "$role" | awk '{ printf "%s; ", $0 }')"
  printf "%sprintf '\\033]2;%s\\033\\\\' %q && clear && echo '=== %s ===' && echo 'role: %s' && echo 'project: '\$CLAUDE_PROJECT_DIR && echo && exec %q %s" \
    "$(echo "$env_lines" | tr '\n' ' ')" "$title" "$title" "$title" "$role" "$CLAUDE_BIN" "$CLAUDE_ARGS"
}

tmux_pane_for_target() {
  case "$(role_for_target "$1")" in
    lead) echo 0 ;;
    requirement-analyst) echo 1 ;;
    architect) echo 2 ;;
    researcher) echo 3 ;;
    developer) echo 4 ;;
    qa-reviewer) echo 5 ;;
    *) echo "$1" ;;
  esac
}

start_tmux() {
  require_command tmux
  require_command "$CLAUDE_BIN"
  if tmux has-session -t "$TEAM_NAME" 2>/dev/null; then
    echo "Session already exists: $TEAM_NAME"
    echo "Attach with: tmux attach -t $TEAM_NAME"
    return
  fi

  tmux new-session -d -s "$TEAM_NAME" -n agents -c "$PROJECT_DIR"
  tmux split-window -t "$TEAM_NAME:0.0" -h -c "$PROJECT_DIR"
  tmux split-window -t "$TEAM_NAME:0.0" -v -c "$PROJECT_DIR"
  tmux split-window -t "$TEAM_NAME:0.1" -v -c "$PROJECT_DIR"
  tmux select-pane -t "$TEAM_NAME:0.0"
  tmux split-window -t "$TEAM_NAME:0.0" -v -c "$PROJECT_DIR"
  tmux select-pane -t "$TEAM_NAME:0.3"
  tmux split-window -t "$TEAM_NAME:0.3" -v -c "$PROJECT_DIR"
  tmux select-layout -t "$TEAM_NAME:0" tiled
  tmux set-option -t "$TEAM_NAME" pane-border-status top >/dev/null
  tmux set-option -t "$TEAM_NAME" pane-border-format " #P: #{@team_title} " >/dev/null
  tmux set-option -t "$TEAM_NAME" remain-on-exit on >/dev/null
  tmux set-window-option -t "$TEAM_NAME:0" automatic-rename off >/dev/null

  for i in "${!ROLES[@]}"; do
    local role="${ROLES[$i]}"
    local title="$PROJECT_NAME-$role"
    prepare_role_project_dir "$role"
    tmux select-pane -t "$TEAM_NAME:0.$i" -T "$title"
    tmux set-option -p -t "$TEAM_NAME:0.$i" @team_role "$role" >/dev/null
    tmux set-option -p -t "$TEAM_NAME:0.$i" @team_title "$title" >/dev/null
    tmux send-keys -t "$TEAM_NAME:0.$i" "$(launch_command "$role")" C-m
  done

  echo "Started tmux Claude team: $TEAM_NAME"
  echo "Attach with: tmux attach -t $TEAM_NAME"
}

attach_tmux() {
  require_command tmux
  if [ -n "${TMUX:-}" ]; then
    tmux switch-client -t "$TEAM_NAME"
  else
    exec tmux attach -t "$TEAM_NAME"
  fi
}

cmux_surface_ids() {
  json_value surface-ids "$(cmux list-surfaces --json)"
}

current_cmux_surface() {
  json_value identify-surface "$(cmux identify --json)"
}

new_cmux_surface() {
  local direction="$1"
  local before_file after_file
  before_file="$(mktemp)"
  after_file="$(mktemp)"
  cmux_surface_ids >"$before_file"
  cmux new-split "$direction" >/dev/null
  sleep 0.1
  cmux_surface_ids >"$after_file"
  json_value new-surface "$before_file" "$after_file"
  rm -f "$before_file" "$after_file"
}

start_cmux() {
  require_command cmux
  require_command "$CLAUDE_BIN"
  local lead req architect researcher developer qa
  lead="$(current_cmux_surface)"
  req="$(new_cmux_surface right)"
  architect="$(new_cmux_surface down)"
  researcher="$(new_cmux_surface down)"
  developer="$(new_cmux_surface down)"
  qa="$(new_cmux_surface down)"
  json_value write-surfaces "$SURFACE_FILE" "$PROJECT_DIR" "$TEAM_NAME" "$lead" "$req" "$architect" "$researcher" "$developer" "$qa"

  local surfaces=("$lead" "$req" "$architect" "$researcher" "$developer" "$qa")
  for i in "${!ROLES[@]}"; do
    prepare_role_project_dir "${ROLES[$i]}"
    cmux send-surface --surface "${surfaces[$i]}" "$(launch_command "${ROLES[$i]}")" >/dev/null
    cmux send-key-surface --surface "${surfaces[$i]}" enter >/dev/null
  done

  echo "Started cmux Claude team: $TEAM_NAME"
  echo "Surface map: $SURFACE_FILE"
  json_value list-surfaces "$SURFACE_FILE"
}

cmux_rpc() {
  python3 - "$@" <<'PY'
import json
import os
import socket
import sys

method = sys.argv[1]
params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
sock_path = os.environ.get("CMUX_SOCKET_PATH", "/tmp/cmux.sock")
payload = {"id": "claude-team", "method": method, "params": params}

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
    sock.connect(sock_path)
    sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
    chunks = []
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\n" in chunk:
            break

response = json.loads(b"".join(chunks).decode("utf-8"))
if not response.get("ok"):
    raise SystemExit(response.get("error") or response)
result = response.get("result")
if isinstance(result, dict):
    for key in ("text", "content", "buffer"):
        if isinstance(result.get(key), str):
            print(result[key])
            raise SystemExit(0)
if isinstance(result, str):
    print(result)
else:
    print(json.dumps(result, ensure_ascii=False))
PY
}

cmd_start() {
  local attach=0
  if [ -n "${1:-}" ] && [[ "$1" != --* ]]; then
    PROJECT_DIR="$1"
    shift
  fi
  PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
  PROJECT_NAME="$(basename "$PROJECT_DIR")"
  TEAM_NAME="${CLAUDE_TEAM_SESSION:-${PROJECT_NAME}-team}"
  TEAM_CONFIG="$PROJECT_DIR/.team/team-config.json"
  SURFACE_FILE="$PROJECT_DIR/.team/cmux-surfaces.json"
  while [ "${1:-}" ]; do
    case "$1" in
      --transport) TRANSPORT="$2"; shift 2 ;;
      --transport=*) TRANSPORT="${1#*=}"; shift ;;
      --attach) attach=1; shift ;;
      *) shift ;;
    esac
  done
  mkdir -p "$PROJECT_DIR/.team/logs" "$PROJECT_DIR/.team/tasks" "$PROJECT_DIR/.team/runtime"
  case "$(transport)" in
    cmux) start_cmux ;;
    tmux) start_tmux ;;
    *) echo "Unknown transport: $(transport)" >&2; exit 1 ;;
  esac
  if [ "$attach" = "1" ]; then
    case "$(transport)" in
      tmux) attach_tmux ;;
      cmux) echo "--attach is only supported for tmux. cmux starts in the current cmux workspace." >&2 ;;
    esac
  fi
}

cmd_list() {
  case "$(transport)" in
    cmux)
      [ -f "$SURFACE_FILE" ] || { echo "No cmux surface map found: $SURFACE_FILE" >&2; exit 1; }
      json_value list-surfaces "$SURFACE_FILE"
      ;;
    tmux)
      tmux list-panes -t "$TEAM_NAME:0" -F '#{pane_index}: #{@team_title} role=#{@team_role} command=#{pane_current_command}'
      ;;
  esac
}

cmd_send() {
  if [ "$#" -lt 2 ]; then
    echo "usage: scripts/claude_team.sh send <role-or-index> <message...>" >&2
    echo "example: scripts/claude_team.sh send developer Fix the card animation bug." >&2
    exit 2
  fi
  local target="$1"
  shift
  local message="$*"
  case "$(transport)" in
    cmux)
      local surface
      surface="$(json_value target "$SURFACE_FILE" "$target")"
      cmux send-surface --surface "$surface" "$message" >/dev/null
      cmux send-key-surface --surface "$surface" enter >/dev/null
      ;;
    tmux)
      tmux send-keys -t "$TEAM_NAME:0.$(tmux_pane_for_target "$target")" "$message" Enter
      ;;
  esac
  echo "Sent to $(role_for_target "$target")"
}

cmd_capture() {
  local target="${1:-}"
  case "$(transport)" in
    cmux)
      if [ -n "$target" ]; then
        local surface
        surface="$(json_value target "$SURFACE_FILE" "$target")"
        cmux_rpc surface.read_text "{\"surface_id\":\"$surface\"}" | tail -80
      else
        python3 - "$SURFACE_FILE" <<'PY' |
import json, sys
from pathlib import Path
for surface in json.loads(Path(sys.argv[1]).read_text()).get("surfaces", []):
    print(f'{surface["index"]}\t{surface["role"]}\t{surface["title"]}\t{surface["surface_id"]}')
PY
        while IFS=$'\t' read -r index role title surface; do
          echo "===== $index: $title ($role) ====="
          cmux_rpc surface.read_text "{\"surface_id\":\"$surface\"}" | tail -80
          echo
        done
      fi
      ;;
    tmux)
      if [ -n "$target" ]; then
        tmux capture-pane -t "$TEAM_NAME:0.$(tmux_pane_for_target "$target")" -p | tail -80
      else
        tmux list-panes -t "$TEAM_NAME:0" -F '#{pane_index} #{pane_title}' |
        while read -r pane title; do
          echo "===== $pane: $title ====="
          tmux capture-pane -t "$TEAM_NAME:0.$pane" -p | tail -80
          echo
        done
      fi
      ;;
  esac
}

cmd_env() {
  local role
  role="$(role_for_target "${1:?usage: scripts/claude_team.sh env <role-or-index>}")"
  role_env "$role"
}

write_command_file() {
  local target="$1"
  local force="$2"
  if [ -f "$target" ] && [ "$force" != "1" ]; then
    echo "Skipped existing: $target"
    return
  fi
  mkdir -p "$(dirname "$target")"
  cat >"$target"
  echo "Installed: $target"
}

cmd_install_commands() {
  local force=0
  while [ "${1:-}" ]; do
    case "$1" in
      --force) force=1; shift ;;
      *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
  done

  local command_dir="$PROJECT_DIR/.claude/commands"
  mkdir -p "$command_dir"

  write_command_file "$command_dir/team_capture.md" "$force" <<'CMD'
---
description: Capture recent output from one role or all Claude team roles.
argument-hint: [role-or-index]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh capture *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh capture $ARGUMENTS`
CMD

  write_command_file "$command_dir/team_env.md" "$force" <<'CMD'
---
description: Print the environment used for a Claude team role.
argument-hint: [role-or-index]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh env *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh env $ARGUMENTS`
CMD

  write_command_file "$command_dir/team_panes.md" "$force" <<'CMD'
---
description: List Claude team panes or cmux surfaces with role names.
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh list)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh list`
CMD

  write_command_file "$command_dir/team_start.md" "$force" <<'CMD'
---
description: Start the role-based Claude team using the configured cmux/tmux transport.
argument-hint: [project-dir]
disable-model-invocation: true
allowed-tools: Bash(scripts/claude_team.sh start *)
---

Direct team-control command. Do not invoke skills, plugins, planning, research, or documentation lookup for this slash command; only run the shell command below.

!`scripts/claude_team.sh start $ARGUMENTS`
CMD

  write_command_file "$command_dir/team_to.md" "$force" <<'CMD'
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
CMD
}

case "${1:-}" in
  start) shift; cmd_start "$@" ;;
  list|panes) shift; cmd_list "$@" ;;
  send) shift; cmd_send "$@" ;;
  capture) shift; cmd_capture "$@" ;;
  env) shift; cmd_env "$@" ;;
  install-commands) shift; cmd_install_commands "$@" ;;
  help|-h|--help|"") usage ;;
  *) echo "Unknown command: $1" >&2; usage; exit 1 ;;
esac
