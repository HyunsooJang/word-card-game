#!/usr/bin/env python3
"""PreToolUse hook for the Bash tool.

Two responsibilities:
1. Block known-destructive commands (rm -rf /, git reset --hard, secret cat, ...).
2. For file-modifying shell commands, extract the target path(s) and run them
   through the same ownership check as `team-check-file-ownership.py`. This
   closes the gap where shell `cp`/`mv`/`tee`/`>` could write outside the
   current role's allow scope, bypassing the LLM-side Edit/Write hook.

Detected file-write patterns (best-effort, regex-based):
    cmd > file           cmd >> file       cmd &> file
    cp [opts] ... DEST   mv [opts] ... DEST
    tee [-a] file
    dd of=path
    sed -i ... file
    touch file [file ...]
    install [opts] ... DEST

Known limitations (documented):
    - python -c "open('x', 'w')..." and similar embedded code: not detected.
    - bash -c "..." nested commands: not unwrapped.
    - Complex pipelines, command substitution, heredocs: best-effort only.
    - Quoted strings containing the patterns: may produce false positives.

False positives are acceptable because every detected target is checked
against the role's allow/deny scope; a target that already lies inside the
role's allowed paths passes through silently.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
OWNERSHIP_HOOK = HOOK_DIR / "team-check-file-ownership.py"

DESTRUCTIVE = [
    # Match `rm -rf /`, `rm -rf *`, `rm -rf ~`, `rm -rf $HOME` (terminator-aware,
    # since `/` and `*` are not word characters so a trailing `\b` won't match).
    (re.compile(r"\brm\s+-[rfRF]+\s+(?:/|\*|~|\$HOME)(?:\s|;|&|\||$)"),
     "destructive rm pattern"),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "hard reset"),
    (re.compile(r"\bgit\s+checkout\s+--\s+"), "destructive checkout"),
    (re.compile(r"\b(printenv|env|cat)\b.*(\.env|TOKEN|SECRET|PASSWORD|KEY)", re.I),
     "secret exposure risk"),
]


def detect_write_targets(command: str) -> list[tuple[str, str]]:
    """Return list of (path, reason) for shell write operations."""
    out: list[tuple[str, str]] = []

    def _add(path: str, reason: str) -> None:
        if not path or path.startswith("-"):
            return
        # Strip surrounding quotes if any
        if (path[0] == path[-1]) and path[0] in ("'", '"'):
            path = path[1:-1]
        # Skip common non-file targets
        if path in ("/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"):
            return
        if path.startswith("/dev/"):
            return
        out.append((path, reason))

    # Output redirects:  > file, >> file, &> file, n> file, n>> file
    for m in re.finditer(r"(?<![\w<>])(?:\d+)?(>>?|&>)\s*([^\s|;&<>()]+)", command):
        _add(m.group(2), f"redirect {m.group(1)}")

    # cp / mv / install: dest is the LAST positional non-flag arg up to a separator
    for cmd_name in ("cp", "mv", "install"):
        for m in re.finditer(
            rf"\b{cmd_name}\b((?:\s+-{{1,2}}[\w-]+(?:=\S+)?)*)((?:\s+[^|;&\n]+))",
            command,
        ):
            tail = m.group(2)
            tokens = [t for t in tail.split() if not t.startswith("-")]
            if len(tokens) >= 2:
                _add(tokens[-1], f"{cmd_name} dest")

    # tee [-a] FILE [FILE ...]
    for m in re.finditer(r"\btee\b((?:\s+-{1,2}[\w-]+)*)\s+([^|;&\n]+)", command):
        for tok in m.group(2).split():
            if not tok.startswith("-"):
                _add(tok, "tee")

    # dd of=PATH
    for m in re.finditer(r"\bdd\b[^|;&\n]*\bof=([^\s|;&]+)", command):
        _add(m.group(1), "dd of=")

    # sed -i ... FILE  (last arg before separator)
    for m in re.finditer(r"\bsed\b[^|;&\n]*?-i\b[^|;&\n]*", command):
        chunk = m.group(0)
        tokens = chunk.split()
        # Skip 'sed', '-i' (or '-i.bak'), and -e/-f and their values
        skip_next = False
        candidates = []
        for tok in tokens[1:]:
            if skip_next:
                skip_next = False
                continue
            if tok in ("-e", "-f"):
                skip_next = True
                continue
            if tok.startswith("-"):
                continue
            candidates.append(tok)
        if candidates:
            # First non-flag after -e/-f handling is the script; following are files.
            # Conservative: treat the LAST candidate as the file target.
            _add(candidates[-1], "sed -i")

    # touch FILE [FILE ...]
    for m in re.finditer(r"\btouch\b((?:\s+-{1,2}[\w-]+(?:=\S+)?)*)\s+([^|;&\n]+)", command):
        for tok in m.group(2).split():
            if not tok.startswith("-"):
                _add(tok, "touch")

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for path, reason in out:
        if path in seen:
            continue
        seen.add(path)
        deduped.append((path, reason))
    return deduped


def check_target_via_ownership_hook(file_path: str, original_payload: dict) -> tuple[int, str]:
    """Run team-check-file-ownership.py with a synthesized Edit-style payload.

    Returns (returncode, stderr).
    """
    if not OWNERSHIP_HOOK.exists():
        return 0, ""
    fake = {
        "tool_input": {"file_path": file_path},
        "cwd": original_payload.get("cwd"),
        "project_dir": original_payload.get("project_dir"),
    }
    try:
        proc = subprocess.run(
            ["python3", str(OWNERSHIP_HOOK)],
            input=json.dumps(fake),
            text=True,
            capture_output=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return 0, ""
    return proc.returncode, proc.stderr.strip()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    command = str((payload.get("tool_input") or {}).get("command") or "")
    if not command.strip():
        return 0

    # 1. Hard block: known-destructive patterns.
    for pattern, reason in DESTRUCTIVE:
        if pattern.search(command):
            print(f"Blocked shell command by Claude team guard: {reason}", file=sys.stderr)
            return 2

    # 2. Soft check: file-write detection routed through ownership hook.
    targets = detect_write_targets(command)
    for target, op_reason in targets:
        rc, stderr = check_target_via_ownership_hook(target, payload)
        if rc == 2:
            # Use the ownership hook's own reason text where possible.
            why = stderr or f"target {target} violates file-ownership rules"
            print(
                f"Blocked shell command by file-ownership guard ({op_reason}): {why}",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
