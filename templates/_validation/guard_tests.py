#!/usr/bin/env python3
"""Isolated unit tests for the bash guard. Run via `python3 guard_tests.py`
so the surrounding Bash invocation does not trigger the very hook under test."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path("/Users/hyunsoojang/Project/word-card-game/.claude/hooks/team-guard-bash.py")
PROJECT_DIR = "/Users/hyunsoojang/Project/word-card-game"


def run_guard(role: str, command: str) -> tuple[int, str]:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": PROJECT_DIR})
    env = {**os.environ, "CLAUDE_TEAM_ROLE": role, "CLAUDE_PROJECT_DIR": PROJECT_DIR}
    proc = subprocess.run(
        ["python3", str(HOOK)],
        input=payload, text=True, capture_output=True, env=env,
    )
    return proc.returncode, proc.stderr.strip()


CASES = [
    # (label, role, command, expected_rc, expected_block_substr)
    ("dev redirects into src/ allow",         "developer",  "echo hi > src/foo.ts",                                                          0, None),
    ("dev redirects into deny scope",         "developer",  "echo hi > .claude/hooks/x.py",                                                  2, "is not allowed to edit"),
    ("researcher tees own report path",       "researcher", "echo body | tee .team/tasks/foo/researcher.md",                                 0, None),
    ("researcher tees other-owner report",    "researcher", "echo body | tee .team/tasks/foo/developer.md",                                  2, "owned by developer"),
    ("dev cp to out-of-project (allowed)",    "developer",  "cp src/x.ts /tmp/x.ts",                                                         0, None),
    ("destructive rm -rf /",                  "developer",  "rm -rf /",                                                                      2, "destructive rm pattern"),
    ("dd of= into denied scope",              "developer",  "dd if=/dev/zero of=.claude/x.bin bs=1k count=1",                                2, "is not allowed to edit"),
    ("sed -i within allow scope",             "developer",  "sed -i '' 's/foo/bar/' src/file.ts",                                            0, None),
    ("sed -i into denied scope",              "developer",  "sed -i '' 's/foo/bar/' .team/file-ownership.json",                              2, "owned by lead"),
    ("plain ls (no write)",                   "developer",  "ls -la src/",                                                                   0, None),
    # tests/** is in developer.allow BUT explicit owner is qa-reviewer; owner check wins.
    ("touch tests/ blocked by owner",         "developer",  "touch tests/new.test.ts",                                                       2, "owned by qa-reviewer"),
    # plain new.test.ts in src is fine (allow + no other owner).
    ("touch src/ in allow",                   "developer",  "touch src/new.test.ts",                                                         0, None),
    ("touch in deny",                         "developer",  "touch .team/file-ownership.json",                                                2, None),  # owner=lead
    ("redirect to /dev/null is fine",         "developer",  "some-cmd 2>/dev/null",                                                          0, None),
]


def main() -> int:
    passed = failed = 0
    for label, role, cmd, want_rc, want_block in CASES:
        rc, err = run_guard(role, cmd)
        ok = (rc == want_rc) and (want_block is None or want_block in err)
        mark = "✓" if ok else "✗"
        print(f"  {mark}  [{role:11s}] rc={rc} {label}")
        if not ok:
            print(f"     expected rc={want_rc}", end="")
            if want_block:
                print(f", err contains {want_block!r}")
            else:
                print()
            print(f"     got      rc={rc}, err={err[:200]!r}")
            failed += 1
        else:
            passed += 1
    print(f"\n{passed} passed, {failed} failed (of {len(CASES)})")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
