#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}

    root = Path(os.environ.get("CLAUDE_TEAM_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    role = os.environ.get("CLAUDE_TEAM_ROLE") or "unknown"
    log_dir = root / ".team" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "time": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "hook_event_name": payload.get("hook_event_name"),
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
        "tool_response": payload.get("tool_response"),
    }
    with (log_dir / f"{role}.jsonl").open("a") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
