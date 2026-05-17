#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_TEAM_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()


def main() -> int:
    root = project_root()
    role = os.environ.get("CLAUDE_TEAM_ROLE") or "unknown"
    role_file = root / ".team" / "roles" / f"{role}.md"
    current_goal = root / ".team" / "current-goal.md"
    ownership = root / ".team" / "file-ownership.json"
    presets = root / ".team" / "role-presets.json"

    print(f"\n[Claude Team Context]\nRole: {role}\nRoot: {root}\n")

    if current_goal.exists():
        print(current_goal.read_text(errors="ignore"))

    if role_file.exists():
        print("\n[Role Instructions]\n")
        print(role_file.read_text(errors="ignore"))

    if ownership.exists():
        try:
            data = json.loads(ownership.read_text(errors="ignore"))
            config = data.get("roles", {}).get(role, {})
            owners = data.get("owners", {})
            owned_paths = [pattern for pattern, owner in owners.items() if owner == role]
            print("\n[File Scope]\n")
            print(f"allow: {config.get('allow', [])}")
            print(f"deny: {config.get('deny', [])}")
            print(f"owned_paths: {owned_paths}")
        except json.JSONDecodeError:
            print("\n[File Scope]\nInvalid .team/file-ownership.json")

    if presets.exists():
        try:
            data = json.loads(presets.read_text(errors="ignore"))
            preset = data.get("roles", {}).get(role, {})
            if preset:
                print("\n[Role Preset]\n")
                for key in ("preferred_skills", "workflow", "report_format"):
                    if key in preset:
                        print(f"{key}: {preset[key]}")
        except json.JSONDecodeError:
            print("\n[Role Preset]\nInvalid .team/role-presets.json")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
