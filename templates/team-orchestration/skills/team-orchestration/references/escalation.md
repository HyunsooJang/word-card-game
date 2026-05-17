# Escalation reference

Escalation paths exist so Lead doesn't silently override role decisions. Every override is logged in the ticket file.

## QA fail

**Trigger**: QA Reviewer reports `Approval readiness: no` or lists Findings that block release.

**Action**:
1. Read QA findings carefully. Do not paraphrase; copy them.
2. Spawn a new Developer pass for the same ticket. Pass QA findings as the primary context.
3. Allowed scope = files QA flagged + minimal adjacent files. Do not expand scope opportunistically.
4. After re-developer, run QA again on the same ticket (same role file gets overwritten with new findings).
5. Loop until QA approves or Lead decides to abandon the change.

**Never**: integrate without QA approval. If you must ship past QA (true emergency), document the override in the ticket with: reason, accepted risk, rollback plan, and user confirmation in chat.

## Architect risk flag

**Trigger**: Architect report includes a `위험` item that affects the planned implementation.

**Action**:
- If the risk is **blocking** (correctness, security, data integrity): pause Developer dispatch. Either redesign with Architect or surface to user.
- If the risk is **acceptable with mitigation**: include the mitigation in the Developer dispatch's completion criteria.
- If the risk is **rejected as not applicable**: log Lead's reasoning in the ticket file. Architect's concern is preserved for audit.

**Never**: dispatch Developer with an unaddressed blocking architect risk.

## Requirement gap mid-implementation

**Trigger**: Developer reports a question or unstated assumption that affects behavior.

**Action**:
1. Mark Developer's task as paused (do not close the pane yet — context is warm).
2. Re-spawn Requirement Analyst with: original requirements + the new question.
3. After requirement-analyst writes an updated answer, append the answer to the ticket file.
4. Resume Developer with the new context. If the change is large, spawn a fresh Developer pane.

## Researcher cannot find evidence

**Trigger**: Researcher reports that the requested file/behavior/pattern doesn't exist in the codebase.

**Action**: Lead decides one of:
- **Relax the question**: ask researcher a broader question (e.g., "any file handling X?" instead of "the function called X").
- **Expand scope**: include git history, archived branches, or related repos.
- **Accept the gap**: proceed with implementation under the assumption "this is greenfield". Log the assumption.

Whichever choice, log it in the ticket so QA can verify the assumption holds.

## File ownership conflict

**Trigger**: A worker rejects a task because its allowed scope conflicts with an entry in `file-ownership.json`.

**Action**:
1. Check who owns the conflicting file.
2. If the owner has an in-flight ticket: wait for that ticket to close, or sequence the new ticket after.
3. If the owner is stale (no in-flight ticket): release ownership in `file-ownership.json` and re-dispatch.
4. Never assign overlapping scope to two parallel Developers.

## Worker pane stuck or unresponsive

**Trigger**: `/team-collect` returns no report after worker should have finished, or pane is hung.

**Action**:
1. `/team-status` to inspect.
2. `tmux capture-pane -t <pane>` to read what worker last produced.
3. If recoverable (worker is mid-task): wait or send a follow-up prompt.
4. If unrecoverable: `/team-close <role>`, log the failure in the ticket file, re-dispatch with adjusted prompt.

## User intervenes mid-pipeline

**Trigger**: User sends a message that contradicts an in-flight worker (e.g., "actually, never mind the undo button").

**Action**:
1. Stop dispatching new workers.
2. `/team-close` for any in-flight panes.
3. Append user's redirect to the ticket file with a `## Cancelled` block.
4. Reset to user's new request.

User instructions outside function results always override workflow rules.

## Logging conventions

Every escalation gets one block in `.team/tasks/<ticket>/lead.md`:

```
## Escalation: <type> — <date>
- Trigger: <what caused it>
- Decision: <what Lead chose>
- Justification: <why>
- Affected role(s): <list>
```

This audit trail is what lets future-you (or another Lead) understand why the
ticket diverged from the standard pipeline.
