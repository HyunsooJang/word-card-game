#!/usr/bin/env python3
"""End-to-end team-orchestration pipeline.

Runs the full requirement → research+architecture → implementation → QA → integration
flow with exactly two user-approval gates:

    Gate 1: After requirement-analyst + auto-generated dev plan.
    Gate 2: After QA approves the artifact.

Between gates the orchestrator drives everything: spawn workers via team_spawn.sh,
poll for report files, decide implementor role from file-ownership, run a fix-loop
on yes-with-fixes (up to N iterations), and finally write the lead integration
block and clean up worker panes.

Run from a tmux pane (typically opened by /team-pipeline). The orchestrator is
where the user types y/n at gates; workers spawn into the existing 'workers'
window of the team session.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Constants ──────────────────────────────────────────────────────────────
POLL_INTERVAL_S = 2.0
WAIT_TIMEOUT_S = 900            # 15 min per worker
MAX_FIX_LOOPS = 5
LEAD_MODEL = os.environ.get("CLAUDE_TEAM_LEAD_MODEL", "claude-opus-4-7")
WORKER_MODEL = os.environ.get("CLAUDE_TEAM_WORKER_MODEL", "claude-sonnet-4-6")

PROJECT_DIR = Path(
    os.environ.get("CLAUDE_PROJECT_DIR")
    or os.environ.get("CLAUDE_TEAM_ROOT")
    or os.getcwd()
).resolve()
SCRIPTS_DIR = Path(__file__).resolve().parent
TASKS_DIR = PROJECT_DIR / ".team" / "tasks"
OWNERSHIP_FILE = PROJECT_DIR / ".team" / "file-ownership.json"
ROLE_PRESETS_FILE = PROJECT_DIR / ".team" / "role-presets.json"

# ── Output helpers ─────────────────────────────────────────────────────────
def _stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

def log(msg: str) -> None:
    print(f"[{_stamp()}] {msg}", flush=True)

def banner(msg: str) -> None:
    bar = "─" * max(len(msg), 60)
    print(f"\n{bar}\n{msg}\n{bar}", flush=True)

def die(msg: str, code: int = 1) -> None:
    print(f"[{_stamp()}] FATAL: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# ── State ──────────────────────────────────────────────────────────────────
def state_path(ticket_dir: Path) -> Path:
    return ticket_dir / "pipeline.json"

def load_state(ticket_dir: Path) -> dict:
    p = state_path(ticket_dir)
    if p.exists():
        return json.loads(p.read_text())
    return {
        "ticket": ticket_dir.name,
        "started": now_iso(),
        "gate_1_approved": False,
        "gate_2_approved": False,
        "iterations": 0,
        "dev_plan": None,
        "stages": {},
        "events": [],
    }

def save_state(ticket_dir: Path, state: dict) -> None:
    state["last_updated"] = now_iso()
    state_path(ticket_dir).write_text(
        json.dumps(state, indent=2, ensure_ascii=False)
    )

def event(state: dict, msg: str) -> None:
    state["events"].append({"t": now_iso(), "msg": msg})

# ── File-ownership lookup (for implementor decision) ──────────────────────
def load_ownership() -> dict:
    return json.loads(OWNERSHIP_FILE.read_text())

def role_for_path(path: str, ownership: dict) -> Optional[str]:
    """Return the role that owns the path, per file-ownership.json owners map."""
    for pattern, owner in ownership.get("owners", {}).items():
        if fnmatch.fnmatch(path, pattern):
            return owner
    return None

# ── Worker spawn + report polling ─────────────────────────────────────────
def spawn_worker(role: str, ticket: str, prompt_text: str) -> None:
    """Run team_spawn.sh with an inline prompt file."""
    log(f"spawn  {role:20s} for {ticket}")
    prompt_file = TASKS_DIR / ticket / f".{role}.prompt"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt_text)
    cmd = ["bash", str(SCRIPTS_DIR / "team_spawn.sh"),
           role, ticket, f"@{prompt_file}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"spawn failed for {role}: {proc.stderr.strip() or proc.stdout.strip()}")

def wait_for_report(ticket: str, role: str, *, label: Optional[str] = None) -> Path:
    label = label or role
    report = TASKS_DIR / ticket / f"{role}.md"
    log(f"wait   {label:20s} → {report.relative_to(PROJECT_DIR)}")
    start = time.time()
    last_log_size = -1
    while True:
        if report.exists() and report.stat().st_size > 0:
            # Stable for 1 polling cycle = treat as done
            sz1 = report.stat().st_size
            time.sleep(POLL_INTERVAL_S)
            sz2 = report.stat().st_size if report.exists() else 0
            if sz1 == sz2 and sz1 > 0:
                log(f"  ✓  {label:20s} report ready ({sz1} bytes)")
                return report
        if time.time() - start > WAIT_TIMEOUT_S:
            die(f"timeout waiting for {role} report after {WAIT_TIMEOUT_S}s")
        time.sleep(POLL_INTERVAL_S)

# ── claude -p one-shot (lead-role decisions) ──────────────────────────────
def lead_oneshot(prompt: str, *, label: str = "lead") -> str:
    log(f"llm    {label:20s} ({LEAD_MODEL})")
    env = {
        **os.environ,
        "CLAUDE_TEAM_ROLE": "lead",
        "CLAUDE_PROJECT_DIR": str(PROJECT_DIR),
        "CLAUDE_TEAM_ROOT": str(PROJECT_DIR),
    }
    cmd = [
        "claude", "--model", LEAD_MODEL, "-p",
        "--no-session-persistence",
        "--permission-mode", "bypassPermissions",
    ]
    proc = subprocess.run(
        cmd, input=prompt, text=True, capture_output=True, env=env, timeout=600,
    )
    if proc.returncode != 0:
        die(f"lead oneshot failed: {proc.stderr.strip()}")
    out = proc.stdout.strip()
    log(f"  ✓  {label:20s} {len(out)} chars returned")
    return out

def extract_json(text: str) -> dict:
    """Pull the first JSON object out of an LLM response."""
    # Prefer ```json fenced blocks.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    # Otherwise grab from first { to matching last }.
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        die(f"could not find JSON in LLM output:\n{text[:300]}")
    return json.loads(text[first:last + 1])

# ── Gate prompting (stdin) ────────────────────────────────────────────────
def gate_prompt(label: str, allowed: tuple[str, ...] = ("y", "n")) -> str:
    options = "/".join(f"[{c}]{name}" for c, name in
                       [("y", "es"), ("n", "o"), ("a", "bort")] if c in allowed)
    while True:
        print(f"\n>>> {label}  {options}: ", end="", flush=True)
        try:
            choice = input().strip().lower()
        except EOFError:
            return "n"
        if choice in allowed:
            return choice
        print(f"    invalid; expected one of {allowed}")

# ── Prompt rendering for routine workers ──────────────────────────────────
PROMPT_FOOTER = """
Then write your role report and exit. Do not modify any file outside the Allowed
scope above. The PreToolUse hook will block any cross-scope write at runtime."""

def prompt_req_analyst(ticket: str) -> str:
    return f"""# {ticket} — requirement-analyst

## Goal
Convert the user request in `.team/tasks/{ticket}/intake.md` into an
implementation-ready specification with unambiguous acceptance criteria.

## Context
Read first:
- `.team/tasks/{ticket}/intake.md`
References (Read tool):
- `.team/roles/*.md`
- `.team/file-ownership.json`
- `.team/role-presets.json`

## Allowed scope
- `docs/**`
- `.team/tasks/{ticket}/**`

## Denied scope
- `src/**`, `tests/**`
- `.team/roles/**`, `.team/file-ownership.json`
- `.claude/**`

## Completion criteria
- Acceptance criteria are unambiguous: an architect could decide structure and
  a researcher/developer could implement without re-asking.
- Audience defined.
- Required sections enumerated.
- Out-of-scope topics enumerated.
- All open questions in the `질문` section (empty if none block).

## Required report
Write to: `.team/tasks/{ticket}/requirement-analyst.md`
Sections (in order):
- 요구사항 요약
- 모호한 점
- 질문
- 구현 전제
{PROMPT_FOOTER}"""

def prompt_researcher(ticket: str, plan: dict) -> str:
    return f"""# {ticket} — researcher (evidence pass)

## Goal
Gather just enough evidence from the existing codebase/docs to inform the
implementor. You do NOT write the artifact; you report findings.

## Context
Read first (in order):
- `.team/tasks/{ticket}/requirement-analyst.md`
- `.team/tasks/{ticket}/architect.md` (if it exists)
Plan summary: {plan.get("summary", "")}

## Allowed scope
- `.team/tasks/{ticket}/researcher.md` (your report only)

## Denied scope
- All other paths (Read is fine; Write/Edit blocked except your report file).

## Completion criteria
- Every requirement maps to an existing file or is flagged as new.
- Risks of the planned change are listed with file:line where relevant.

## Required report
Write to: `.team/tasks/{ticket}/researcher.md`
Sections (in order):
- 조사 범위
- 근거 파일
- 현재 동작
- 리스크
{PROMPT_FOOTER}"""

def prompt_architect(ticket: str, plan: dict) -> str:
    return f"""# {ticket} — architect

## Goal
Decide the design/structure of the artifact and surface design risks. You do
NOT write the artifact.

## Context
Read first (in order):
- `.team/tasks/{ticket}/requirement-analyst.md`
- `.team/tasks/{ticket}/intake.md`
Plan summary: {plan.get("summary", "")}
Expected files: {plan.get("expected_files_modified", [])}

## Allowed scope
- `.team/tasks/{ticket}/architect.md` (your report only)

## Denied scope
- All other write paths.

## Completion criteria
- Concrete structural decision (e.g. TOC for a doc, state-machine for code).
- 1+ design risks with mitigation.
- Verification checklist for the next role.

## Required report
Write to: `.team/tasks/{ticket}/architect.md`
Sections (in order):
- 설계 판단
- 위험
- 수정 파일 (none — architect proposes only)
- 검증
{PROMPT_FOOTER}"""

def prompt_implementor(ticket: str, plan: dict, role: str,
                       prior_qa: Optional[Path] = None) -> str:
    impl_files = plan.get("expected_files_modified", [])
    files_block = "\n".join(f"- `{f}`" for f in impl_files) or "(see plan)"
    qa_block = ""
    if prior_qa:
        qa_block = f"""

## QA fixes (this is a fix-pass)
QA returned `yes-with-fixes`. Read `.team/tasks/{ticket}/qa-reviewer.md` and
apply every MUST item exactly. OPTIONAL items: skip unless trivial. Update
your report to note which findings you addressed and which you left."""
    return f"""# {ticket} — {role} (implementor pass)

## Goal
Produce the artifact per requirements + architect structure. You are acting as
the implementor for this ticket because file-ownership maps the artifact path
to your role.

## Context
Read first (in order):
- `.team/tasks/{ticket}/requirement-analyst.md`
- `.team/tasks/{ticket}/architect.md`
- `.team/tasks/{ticket}/researcher.md` (if exists)
- `.team/tasks/{ticket}/{role}.md` (your prior report, if a fix-pass)
{qa_block}

## Allowed scope
{files_block}
- `.team/tasks/{ticket}/{role}.md` (your report; overwrite is fine)

## Denied scope
- Anything not listed in Allowed scope above.

## Completion criteria
{chr(10).join(f"- {c}" for c in plan.get("completion_criteria", []))}
- Every reference (file/command) is traceable to an existing file.
- No fabricated commands, roles, or files.

## Required report
Write to: `.team/tasks/{ticket}/{role}.md` (overwrite is fine)
Sections (in order):
- 한 일
- 변경 파일
- 검증
- 리스크
{PROMPT_FOOTER}"""

def prompt_qa(ticket: str, plan: dict) -> str:
    return f"""# {ticket} — qa-reviewer

## Goal
Verify the artifact against requirements + architect structure. Surface gaps
with file:line evidence. Decide approval readiness.

## Context
Read first:
- `.team/tasks/{ticket}/requirement-analyst.md`
- `.team/tasks/{ticket}/architect.md`
- `.team/tasks/{ticket}/{plan["implementor_role"]}.md` (implementor report)
- The artifact files: {plan.get("expected_files_modified", [])}

## Allowed scope
- `.team/tasks/{ticket}/qa-reviewer.md` (your report only)

## Denied scope
- All other write paths. Do not edit the artifact even if it has bugs;
  surface findings instead.

## Completion criteria
- Every acceptance criterion mapped to a section/line OR flagged missing.
- Every architect TOC/structure item present OR skip-justified in the artifact.
- No factual errors against truth files (cite file:line).
- Approval readiness decided as one of: `yes` / `yes-with-fixes` / `no`.

## Required report
Write to: `.team/tasks/{ticket}/qa-reviewer.md`
Sections (in order):
- Findings (numbered, file:line)
- Missing tests (N/A or list)
- Regression risk
- Approval readiness: yes / yes-with-fixes <list> / no <reason>
{PROMPT_FOOTER}"""

# ── LLM-driven steps ──────────────────────────────────────────────────────
def generate_dev_plan(ticket: str) -> dict:
    intake = (TASKS_DIR / ticket / "intake.md").read_text()
    req = (TASKS_DIR / ticket / "requirement-analyst.md").read_text()
    ownership = json.dumps(load_ownership(), indent=2, ensure_ascii=False)
    prompt = f"""You are the team Lead. Produce a development plan as STRICT JSON
ONLY (no preamble, no commentary, no markdown fence). Use this schema:

{{
  "summary": "one-sentence plan",
  "needs_researcher": <bool>,
  "needs_architect": <bool>,
  "implementor_role": "<role from {{requirement-analyst, architect, researcher, developer, qa-reviewer}}>",
  "expected_files_modified": ["<path1>", "<path2>"],
  "skip_justifications": {{"<role>": "<one-sentence reason>"}},
  "completion_criteria": ["<criterion1>", "<criterion2>"]
}}

Choose `implementor_role` by looking at `expected_files_modified` and the
file-ownership owners map: the role that owns the primary artifact path is
the implementor. If the primary file pattern is not in `owners`, fall back
to `developer`.

# Ticket intake
{intake}

# Requirement analyst report
{req}

# File-ownership rules (for implementor role decision)
```json
{ownership}
```
"""
    raw = lead_oneshot(prompt, label="dev plan")
    plan = extract_json(raw)
    # Sanity: implementor_role must exist
    if plan.get("implementor_role") not in {
        "requirement-analyst", "architect", "researcher", "developer", "qa-reviewer"
    }:
        plan["implementor_role"] = "developer"
    return plan

def parse_qa_approval(ticket: str) -> tuple[str, list[str]]:
    """Read qa-reviewer.md, return (approval, must_fix_items)."""
    text = (TASKS_DIR / ticket / "qa-reviewer.md").read_text()
    # Find Approval readiness line
    m = re.search(r"^##\s*Approval\s*readiness\s*\n+(.+?)(?=\n##|\Z)",
                  text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if not m:
        return "unknown", []
    body = m.group(1).strip().splitlines()
    # Strip markdown emphasis/code so we can match plain `yes` / `no` / `yes-with-fixes`
    head = re.sub(r"[*`_]", "", body[0].strip().lower()).strip()
    if "yes-with-fixes" in head or ("yes" in head and "fix" in head):
        approval = "yes-with-fixes"
    elif head.startswith("yes"):
        approval = "yes"
    elif head.startswith("no"):
        approval = "no"
    else:
        approval = "unknown"
    must = [ln for ln in body if "[MUST]" in ln or "**[MUST]**" in ln]
    return approval, must

def generate_integration_block(ticket: str, state: dict) -> str:
    files = []
    for name in ("intake.md", "requirement-analyst.md", "architect.md",
                 "researcher.md", "qa-reviewer.md"):
        p = TASKS_DIR / ticket / name
        if p.exists():
            files.append(f"## {name}\n```\n{p.read_text()[:6000]}\n```\n")
    impl_role = state["dev_plan"]["implementor_role"]
    impl_path = TASKS_DIR / ticket / f"{impl_role}.md"
    if impl_path.exists():
        files.append(f"## {impl_role}.md\n```\n{impl_path.read_text()[:6000]}\n```\n")

    prompt = f"""You are the team Lead. Write the integration block (markdown only,
no preamble) that will be saved as `.team/tasks/{ticket}/lead.md`. Use this
template exactly, filling in real values:

```
## Integration
- Date closed: <UTC ISO timestamp>
- Final files merged: <list with line counts>
- All role reports: <list of <role>.md files>
- QA approval: <yes / yes-with-fixes (resolved over N iterations)>
- Pipeline iterations: <N>
- Skip justifications: <role: reason / role: reason>
- Residual risks: <or "none">
- Backlog noted (if any): <items not addressed in this ticket>
```

# Pipeline state
```json
{json.dumps(state, indent=2, ensure_ascii=False)[:4000]}
```

# Reports

{''.join(files)}
"""
    return lead_oneshot(prompt, label="integration block")

# ── Stage helpers ─────────────────────────────────────────────────────────
def show_file(path: Path, max_lines: int = 80) -> None:
    if not path.exists():
        print(f"  (missing: {path.relative_to(PROJECT_DIR)})")
        return
    print(f"\n── {path.relative_to(PROJECT_DIR)} ──")
    text = path.read_text()
    lines = text.splitlines()
    print("\n".join(lines[:max_lines]))
    if len(lines) > max_lines:
        print(f"  … (+{len(lines) - max_lines} more lines)")

def stage_done(state: dict, name: str) -> bool:
    return bool(state.get("stages", {}).get(name, {}).get("done"))

def mark_done(state: dict, name: str, **extra: Any) -> None:
    state.setdefault("stages", {}).setdefault(name, {})
    state["stages"][name]["done"] = True
    state["stages"][name].update(extra)

# ── Main pipeline ─────────────────────────────────────────────────────────
def run(ticket: str) -> int:
    ticket_dir = TASKS_DIR / ticket
    if not ticket_dir.exists():
        die(f"ticket not initialized: run /team-init {ticket} first")
    intake = ticket_dir / "intake.md"
    if not intake.exists():
        die(f"intake.md missing at {intake}")

    state = load_state(ticket_dir)
    save_state(ticket_dir, state)

    banner(f"Pipeline start: {ticket}")
    log(f"project: {PROJECT_DIR}")
    log(f"models : lead={LEAD_MODEL}  worker={WORKER_MODEL}")
    log(f"max fix-loops: {MAX_FIX_LOOPS}")

    # ── Stage 1: requirement-analyst ──
    if not stage_done(state, "requirement_analyst"):
        spawn_worker("requirement-analyst", ticket, prompt_req_analyst(ticket))
        wait_for_report(ticket, "requirement-analyst")
        mark_done(state, "requirement_analyst")
        event(state, "requirement-analyst done")
        save_state(ticket_dir, state)

    # ── Stage 2: dev plan + Gate 1 ──
    if not state.get("dev_plan"):
        plan = generate_dev_plan(ticket)
        state["dev_plan"] = plan
        event(state, "dev plan generated")
        save_state(ticket_dir, state)

    if not state.get("gate_1_approved"):
        banner("Gate 1 — Requirement + Dev plan approval")
        show_file(ticket_dir / "requirement-analyst.md", max_lines=120)
        print("\n── Auto-generated dev plan ──")
        print(json.dumps(state["dev_plan"], indent=2, ensure_ascii=False))
        choice = gate_prompt("Approve and proceed?", allowed=("y", "n", "a"))
        if choice != "y":
            event(state, f"gate_1 declined: {choice}")
            save_state(ticket_dir, state)
            die("Pipeline aborted at Gate 1")
        state["gate_1_approved"] = True
        event(state, "gate_1 approved")
        save_state(ticket_dir, state)

    plan = state["dev_plan"]
    impl_role = plan["implementor_role"]

    # ── Stage 3: parallel research + architect ──
    if plan.get("needs_researcher") and not stage_done(state, "researcher"):
        spawn_worker("researcher", ticket, prompt_researcher(ticket, plan))
    if plan.get("needs_architect") and not stage_done(state, "architect"):
        spawn_worker("architect", ticket, prompt_architect(ticket, plan))

    if plan.get("needs_researcher") and not stage_done(state, "researcher"):
        wait_for_report(ticket, "researcher")
        mark_done(state, "researcher")
        save_state(ticket_dir, state)
    if plan.get("needs_architect") and not stage_done(state, "architect"):
        wait_for_report(ticket, "architect")
        mark_done(state, "architect")
        save_state(ticket_dir, state)

    # ── Stage 4+5: implementor / qa with fix-loop ──
    iteration = state.get("iterations", 0)
    qa_approval = "unknown"
    while iteration <= MAX_FIX_LOOPS:
        impl_label = f"impl_iter_{iteration}"
        if not stage_done(state, impl_label):
            prior_qa = ticket_dir / "qa-reviewer.md" if iteration > 0 else None
            spawn_worker(impl_role, ticket,
                         prompt_implementor(ticket, plan, impl_role, prior_qa))
            wait_for_report(ticket, impl_role,
                            label=f"{impl_role} (iter {iteration})")
            mark_done(state, impl_label)
            event(state, f"implementor iter {iteration} done")
            save_state(ticket_dir, state)

        qa_label = f"qa_iter_{iteration}"
        if not stage_done(state, qa_label):
            spawn_worker("qa-reviewer", ticket, prompt_qa(ticket, plan))
            wait_for_report(ticket, "qa-reviewer",
                            label=f"qa-reviewer (iter {iteration})")
            mark_done(state, qa_label)
            save_state(ticket_dir, state)

        qa_approval, must_items = parse_qa_approval(ticket)
        log(f"QA approval (iter {iteration}): {qa_approval}  "
            f"({len(must_items)} MUST items)")
        event(state, f"qa iter {iteration}: {qa_approval}")
        state["qa_approval"] = qa_approval
        save_state(ticket_dir, state)

        if qa_approval == "yes":
            break
        if qa_approval in ("no", "unknown"):
            banner(f"QA returned `{qa_approval}` — escalating to user")
            show_file(ticket_dir / "qa-reviewer.md", max_lines=60)
            choice = gate_prompt("Continue with another fix-pass anyway?",
                                 allowed=("y", "n", "a"))
            if choice != "y":
                die(f"Pipeline stopped: QA returned `{qa_approval}`")
        # yes-with-fixes or user-chose-y: run another iteration
        iteration += 1
        state["iterations"] = iteration
        save_state(ticket_dir, state)
        if iteration > MAX_FIX_LOOPS:
            banner(f"Max fix-loops ({MAX_FIX_LOOPS}) exceeded")
            choice = gate_prompt("Force-accept current state? (will go to Gate 2)",
                                 allowed=("y", "n", "a"))
            if choice != "y":
                die("Pipeline stopped: max fix-loops exceeded")
            qa_approval = "force-accepted"
            break

    # ── Stage 6: Gate 2 ──
    if not state.get("gate_2_approved"):
        banner("Gate 2 — Final artifact approval")
        for f in plan.get("expected_files_modified", []):
            p = PROJECT_DIR / f
            if p.exists():
                lines = sum(1 for _ in p.read_text().splitlines())
                print(f"  {f:40s}  {p.stat().st_size} bytes / {lines} lines")
            else:
                print(f"  {f:40s}  (missing!)")
        print()
        show_file(ticket_dir / "qa-reviewer.md", max_lines=60)
        choice = gate_prompt("Accept and integrate?", allowed=("y", "n", "a"))
        if choice != "y":
            event(state, f"gate_2 declined: {choice}")
            save_state(ticket_dir, state)
            die("Pipeline aborted at Gate 2")
        state["gate_2_approved"] = True
        event(state, "gate_2 approved")
        save_state(ticket_dir, state)

    # ── Stage 7: integration block ──
    lead_md = ticket_dir / "lead.md"
    if not lead_md.exists():
        block = generate_integration_block(ticket, state)
        # Strip any markdown fence the LLM may have added
        block = re.sub(r"^```(?:markdown)?\s*\n?|\n?```\s*$", "", block.strip(),
                       flags=re.MULTILINE)
        lead_md.write_text(block + "\n")
        event(state, "integration block written")
        save_state(ticket_dir, state)
        log(f"wrote  lead.md  ({lead_md.stat().st_size} bytes)")

    # ── Stage 8: cleanup ──
    log("cleanup: closing all worker panes")
    subprocess.run(["bash", str(SCRIPTS_DIR / "team_close.sh"), "--all"],
                   capture_output=True, text=True)

    banner("Pipeline complete")
    show_file(lead_md, max_lines=40)
    return 0

# ── Entry ─────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket")
    args = ap.parse_args()
    try:
        return run(args.ticket)
    except KeyboardInterrupt:
        die("interrupted by user")
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
