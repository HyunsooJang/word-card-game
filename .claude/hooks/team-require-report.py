#!/usr/bin/env python3
from __future__ import annotations

import os


def main() -> int:
    role = os.environ.get("CLAUDE_TEAM_ROLE") or "unknown"
    if role == "lead":
        return 0
    print(
        "\nBefore stopping, finish with this report format:\n"
        "한 일:\n"
        "변경 파일:\n"
        "검증:\n"
        "리스크:\n"
        "다음 필요 결정:\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
