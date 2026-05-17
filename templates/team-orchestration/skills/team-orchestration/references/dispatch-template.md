# Dispatch template reference

Every prompt sent to a worker via `/team-spawn` must follow this structure. Per-role variants follow the general template.

## General template

```
# <ticket-slug> — <role>

## Goal
<one sentence describing the outcome>

## Context
- Ticket dir: .team/tasks/<ticket>/
- Prior reports:
  - .team/tasks/<ticket>/requirement-analyst.md
  - .team/tasks/<ticket>/architect.md (if exists)
  - .team/tasks/<ticket>/researcher.md (if exists)
- Related code/docs: <paths>

## Allowed scope
- <glob 1>
- <glob 2>

## Denied scope
- <glob 1>
- <glob 2>

## Completion criteria
- <observable behavior or artifact>
- <test or check>

## Required report
Write your report to: .team/tasks/<ticket>/<role>.md
Use this format:
- <role-specific section 1>
- <role-specific section 2>
- ...

When the report is written, exit. Lead will collect.
```

## Per-role report formats

Sourced from `.team/role-presets.json`:

| Role | Report sections |
|---|---|
| `requirement-analyst` | 요구사항 요약 / 모호한 점 / 질문 / 구현 전제 |
| `architect` | 설계 판단 / 위험 / 수정 파일 / 검증 |
| `researcher` | 조사 범위 / 근거 파일 / 현재 동작 / 리스크 |
| `developer` | 한 일 / 변경 파일 / 검증 / 리스크 |
| `qa-reviewer` | Findings / Missing tests / Regression risk / Approval readiness |

## Per-role examples

### Requirement Analyst dispatch

```
# add-undo-button — requirement-analyst

## Goal
Convert the user's "add an undo button to the card flip screen" request into an
implementation-ready spec.

## Context
- Ticket dir: .team/tasks/add-undo-button/
- User request: see ticket dir intake.md
- Related screens: <to be discovered>

## Allowed scope
- docs/**
- .team/tasks/add-undo-button/**

## Denied scope
- src/**
- tests/**

## Completion criteria
- Acceptance criteria are unambiguous (a developer could implement directly)
- All open questions are listed; if any block implementation, surface them

## Required report
Write to .team/tasks/add-undo-button/requirement-analyst.md with:
- 요구사항 요약
- 모호한 점
- 질문
- 구현 전제
```

### Developer dispatch

```
# add-undo-button — developer

## Goal
Implement the undo button per the approved requirement and architect notes.

## Context
- Ticket dir: .team/tasks/add-undo-button/
- Requirements: .team/tasks/add-undo-button/requirement-analyst.md
- Architecture decision: .team/tasks/add-undo-button/architect.md
- Researcher evidence: .team/tasks/add-undo-button/researcher.md

## Allowed scope
- src/components/CardFlip.tsx
- src/state/cardStore.ts
- tests/components/CardFlip.test.tsx

## Denied scope
- src/state/* (except cardStore.ts)
- src/components/* (except CardFlip.tsx)

## Completion criteria
- Undo button visible only when flipState !== "initial"
- Click reverts the most recent flip; state stack is bounded to last 10 actions
- Focused tests for new behavior pass
- No type errors

## Required report
Write to .team/tasks/add-undo-button/developer.md with:
- 한 일
- 변경 파일 (with line counts)
- 검증 (commands run + results)
- 리스크
```

### QA Reviewer dispatch

```
# add-undo-button — qa-reviewer

## Goal
Verify the undo button implementation against the approved requirements; find
regressions and missing tests.

## Context
- Ticket dir: .team/tasks/add-undo-button/
- Requirements: .team/tasks/add-undo-button/requirement-analyst.md
- Developer report: .team/tasks/add-undo-button/developer.md
- Files changed (per developer report): <list>

## Allowed scope
- tests/**
- docs/**
- .team/tasks/add-undo-button/**

## Denied scope
- src/**

## Completion criteria
- All acceptance criteria traced to a passing test or documented gap
- Regression risk for adjacent flip-state code assessed
- Approval readiness: yes / no with reason

## Required report
Write to .team/tasks/add-undo-button/qa-reviewer.md with:
- Findings
- Missing tests
- Regression risk
- Approval readiness
```

## Common dispatch mistakes

- **Vague allowed scope** ("src/**" when only one file should change) → worker over-edits, QA rejects.
- **Forgetting prior context links** → worker re-derives requirements, may diverge.
- **No completion criteria** → worker stops at "I changed the file" without checking behavior.
- **Wrong report path** → Lead can't `/team-collect`.
