#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path


def load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def project_root(payload: dict) -> Path:
    raw = (
        os.environ.get("CLAUDE_TEAM_ROOT")
        or payload.get("project_dir")
        or payload.get("cwd")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or "."
    )
    return Path(raw).resolve()


def extract_path(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("file_path", "path"):
        if tool_input.get(key):
            return str(tool_input[key])
    return None


def normalize(root: Path, file_path: str) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(os.environ.get("CLAUDE_PROJECT_DIR") or root) / path
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def main() -> int:
    payload = load_payload()
    root = project_root(payload)
    config_path = root / ".team" / "file-ownership.json"
    if not config_path.exists():
        return 0

    try:
        ownership = json.loads(config_path.read_text(errors="ignore"))
    except json.JSONDecodeError:
        print(f"Invalid JSON: {config_path}", file=sys.stderr)
        return 2

    role = os.environ.get("CLAUDE_TEAM_ROLE") or ownership.get("default_role")
    file_path = extract_path(payload)
    if not role or not file_path:
        return 0

    rel_path = normalize(root, file_path)
    # Paths outside the project root are outside this team's enforcement domain.
    # normalize() returns an absolute path string when the target lies outside `root`.
    if rel_path.startswith("/"):
        return 0
    owners = ownership.get("owners", {})
    explicit_owner = next((owner for pattern, owner in owners.items() if fnmatch.fnmatch(rel_path, pattern)), None)
    if explicit_owner and explicit_owner != role:
        print(
            f"Blocked by file ownership: {rel_path} is owned by {explicit_owner}; current role is {role}.",
            file=sys.stderr,
        )
        return 2

    role_config = ownership.get("roles", {}).get(role, {})
    deny = role_config.get("deny", [])
    allow = role_config.get("allow", [])
    if any(fnmatch.fnmatch(rel_path, pattern) for pattern in deny):
        print(f"Blocked by role deny rule: {role} may not edit {rel_path}.", file=sys.stderr)
        return 2
    if allow and not any(fnmatch.fnmatch(rel_path, pattern) for pattern in allow):
        print(f"Blocked by role scope: {role} is not allowed to edit {rel_path}.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
