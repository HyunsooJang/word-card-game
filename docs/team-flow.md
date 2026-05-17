# Team Flow — 신규 기여자 운영 가이드

---

## 1. 문서 목적과 대상 독자

이 문서는 이 저장소의 **team-orchestration 운영 흐름**을 처음 접하는 기여자를 위한 온보딩 가이드입니다.  
Claude Code 일반 사용법이나 설치 방법은 다루지 않습니다.

**주 독자**: Claude Code 기본 사용법은 알지만 이 저장소의 역할 격리 규칙을 처음 접하는 기여자 / 엔지니어  
**부 독자**: 티켓 진행 상황을 추적해야 하는 기존 팀원

이 문서를 읽고 나면 아래 네 가지 질문에 답할 수 있어야 합니다.

1. 티켓은 어떻게 여는가?
2. 각 역할은 무엇을 담당하는가?
3. 리포트와 산출물은 어디에 쌓이는가?
4. 어떤 상황에서 escalation이 발생하고, 그때 Lead는 무엇을 해야 하는가?

---

## 2. 빠른 시작: 티켓 열기

모든 작업은 **티켓**으로 시작합니다. 아래 세 단계가 최소 절차입니다.

### 단계 1 — 티켓 디렉토리 생성

```
/team-init <ticket-slug>
```

예시: `/team-init add-undo-button`

[`/team-init`](../.claude/commands/team-init.md) 명령은 `.team/tasks/add-undo-button/intake.md`를 생성합니다.  
내부적으로 [`scripts/team_init.sh`](../scripts/team_init.sh)를 실행합니다.

### 단계 2 — Intake 보강

생성된 `.team/tasks/<ticket>/intake.md`를 열어 작업 목적, 배경, 초기 요구사항을 작성합니다.  
Lead가 첫 dispatch 전에 이 파일을 채워야 합니다.

### 단계 3 — 첫 역할 dispatch

```
/team-spawn requirement-analyst <ticket>
```

[`/team-spawn`](../.claude/commands/team-spawn.md)은 새 tmux/cmux 패인에 역할별 Claude 세션을 엽니다.  
열린 패인에 아래와 같은 dispatch 프롬프트를 붙여 넣으면 역할이 작업을 시작합니다.

### 예시 dispatch 프롬프트

다음은 [`templates/_validation/dispatch/01-requirement-analyst.txt`](../templates/_validation/dispatch/01-requirement-analyst.txt)에서 가져온 실제 프롬프트입니다.

```
# docs-team-flow — requirement-analyst

## Goal
Convert "Add docs/team-flow.md describing the team workflow for newcomers" into
an implementation-ready spec so a downstream architect/researcher can act
without further clarification.

## Context
- Ticket dir: .team/tasks/docs-team-flow/
- User request: see ticket dir intake.md

## Allowed scope
- docs/**
- .team/tasks/docs-team-flow/**

## Denied scope
- src/**
- tests/**

## Completion criteria
- Acceptance criteria for docs/team-flow.md are unambiguous.
- Audience explicitly defined.
- Required sections enumerated.
- Out-of-scope topics explicitly listed.
- Length target stated as a range.

## Required report
Write to: .team/tasks/docs-team-flow/requirement-analyst.md
Use these exact sections:
- 요구사항 요약
- 모호한 점
- 질문
- 구현 전제

Then exit.
```

모든 dispatch 프롬프트는 **Goal / Context / Allowed scope / Denied scope / Completion criteria / Required report** 여섯 블록을 포함해야 합니다. 전체 템플릿은 [`.claude/skills/team-orchestration/references/dispatch-template.md`](../.claude/skills/team-orchestration/references/dispatch-template.md)를 참조하세요.

---

## 3. 역할별 책임과 역할 격리

이 저장소는 6개 역할로 작업을 분리합니다. 각 역할은 서로 다른 파일 범위와 리포트 형식을 갖습니다.

| 역할 | 결정 / 산출물 | 리포트 섹션 |
|---|---|---|
| **lead** | 작업 분해·시퀀싱·최종 통합. 직접 구현하지 않음 | 한 일 / 변경 파일 / 검증 / 리스크 / 다음 필요 결정 |
| **requirement-analyst** | 모호함 제거, acceptance criteria 확정 | 요구사항 요약 / 모호한 점 / 질문 / 구현 전제 |
| **architect** | 상태 전이·정책 게이트·의존성 경계 리스크 검토 | 설계 판단 / 위험 / 수정 파일 / 검증 |
| **researcher** | 코드·문서·테스트 근거 수집 (코드 수정 불가) | 조사 범위 / 근거 파일 / 현재 동작 / 리스크 |
| **developer** | Lead가 지정한 파일만 구현 | 한 일 / 변경 파일 / 검증 / 리스크 |
| **qa-reviewer** | 동작 검증, 회귀 위험, 테스트 누락 확인 | Findings / Missing tests / Regression risk / Approval readiness |

리포트 형식의 원천은 [`.team/role-presets.json`](../.team/role-presets.json)이고, 역할 계약 전문은 [`.team/roles/`](../.team/roles/) 디렉토리에 있습니다.

### 역할 격리가 강제되는 방식

역할별 파일 접근 범위(`allow` / `deny`)와 최종 편집 권한(`owners`)은 [`.team/file-ownership.json`](../.team/file-ownership.json)에 정의되어 있습니다. 역할이 허용되지 않은 파일을 편집하려 하면 **PreToolUse ownership check** 훅이 실행 시점에 이를 거부합니다.

`allow` 범위와 `owner` 범위는 다를 수 있습니다. 예를 들어 `architect`는 `docs/**`를 읽을 수 있지만, `docs/**`의 편집 권한(owner)은 `researcher`에게 있습니다. dispatch 전에 반드시 `../.team/file-ownership.json`의 `owners` 블록을 확인하세요.

---

## 4. 표준 진행 순서

파이프라인은 단방향입니다:  
**requirements → analysis → implementation → QA → integration**

단계를 재정렬할 수 없습니다. 단계를 건너뛸 때는 티켓 파일에 한 문장 근거를 남겨야 합니다.

자세한 파이프라인 규칙은 [`.claude/skills/team-orchestration/references/pipeline.md`](../.claude/skills/team-orchestration/references/pipeline.md)를 참조하세요.

### 각 단계

**1. Requirement Analyst**
- 티켓 스코프가 모호하면 반드시 실행합니다.
- 사용자가 "함수 X를 파일 Z에서 Y로 이름 변경" 수준의 완전한 스펙을 제시한 경우에만 skip 가능합니다.

**2. Researcher + Architect (병렬 실행 가능)**
- Requirements가 확정된 뒤 두 역할을 동시에 dispatch할 수 있습니다.
- 두 역할의 출력이 독립적이므로 병렬 실행이 안전합니다.
- 두 역할 모두 완료될 때까지 다음 단계로 이동하지 않습니다.
- Researcher skip: Lead가 변경 파일 전체를 기억에서 정확히 나열할 수 있을 때.
- Architect skip: 변경이 다른 레이어에 전혀 영향을 주지 않는 leaf-level 편집일 때.

**3. Developer**
- Requirements + 분석 결과가 모두 준비된 뒤 실행합니다.
- **기본 구현 주체는 Developer**입니다. 단, `file-ownership.json`의 `owners` 블록이 다른 역할을 지정하면 해당 역할이 실제 편집 권한을 가집니다. 예: `docs/**`의 owner는 `researcher`이므로 doc-only 티켓에서는 Developer 단계가 생략될 수 있습니다.
- 두 Developer 세션이 파일 범위가 겹치지 않는 경우에 한해 병렬 실행이 가능합니다.

**4. QA Reviewer**
- Developer 완료 후 순차 실행합니다.
- Developer와 절대 병렬 실행하지 않습니다 (QA는 완성된 결과물을 검토해야 합니다).
- `Approval readiness: no` 보고 시 Developer를 재dispatch합니다. QA 승인 없이 통합하지 않습니다.

**5. Lead Integration**
- 모든 역할 리포트를 `/team-collect`로 수집하고, QA가 `Approval readiness: yes`인지 확인합니다.
- `.team/current-goal.md`를 갱신하고 티켓 파일에 closing 블록을 추가합니다.

---

## 5. 리포트와 작업 산출물 위치

모든 산출물은 `.team/tasks/<ticket>/` 아래에 쌓입니다.

- **`.team/tasks/<ticket>/intake.md`** — 티켓 목적·배경·초기 요구사항 (Lead 작성, 티켓 열 때 생성됨)
- **`.team/tasks/<ticket>/<role>.md`** — 각 역할이 작업 종료 시 작성하는 리포트  
  예: `.team/tasks/add-undo-button/researcher.md`
- **`.team/tasks/<ticket>/<role>.log`** — 역할 세션의 실행 로그
- **`.team/current-goal.md`** — 현재 진행 중인 목표 상태 (Lead만 갱신하는 단일 상태 문서)

역할 리포트를 읽으려면 `/team-collect <role> <ticket>` 명령을 사용합니다.

---

## 6. 에스컬레이션이 발생하는 경우

escalation이 발생하면 Lead가 티켓 아티팩트 아래에 trigger·결정·근거를 기록합니다.  
자세한 복구 절차와 로깅 형식은 [`.claude/skills/team-orchestration/references/escalation.md`](../.claude/skills/team-orchestration/references/escalation.md)를 참조하세요.

- **QA fail** — QA Reviewer가 `Approval readiness: no`를 보고하면, QA findings를 새 컨텍스트로 포함하여 Developer를 재dispatch합니다. QA 승인 없이 통합하지 않습니다.

- **Architect risk flag** — Architect 리포트의 `위험` 항목이 구현에 영향을 주면 Developer dispatch를 중단합니다. 위험을 Architect와 재설계하거나, 사용자에게 표면화하거나, Lead가 근거와 함께 override를 티켓에 기록합니다.

- **Requirement gap mid-implementation** — Developer가 미결 가정을 발견하면 해당 작업을 일시 정지하고 Requirement Analyst를 재dispatch합니다. 갱신된 답변이 티켓에 추가된 뒤 Developer를 재개합니다.

- **Researcher cannot find evidence** — Researcher가 증거를 찾지 못하면 Lead가 다음 중 하나를 결정하고 티켓에 기록합니다: 질문 완화, 범위 확장(git 히스토리·관련 레포), 또는 "greenfield 가정"으로 진행.

- **File ownership conflict** — 다른 인-플라이트 티켓이 동일 파일을 점유 중이면 해당 티켓이 닫힌 뒤 재dispatch합니다. 소유권이 이미 해제된 stale 상태라면 `file-ownership.json`을 갱신한 뒤 재dispatch합니다.

- **Worker pane stuck/unresponsive** — `/team-status`로 상태를 확인합니다. 복구 불가능하면 `/team-close <role>`로 패인을 닫고, 티켓에 실패를 기록한 뒤 조정된 프롬프트로 재dispatch합니다.

- **User intervenes mid-pipeline** — 진행 중인 모든 패인을 `/team-close --all`로 즉시 종료합니다. 티켓 파일에 `## Cancelled` 블록과 사용자의 새 지시를 추가하고, 새 요청으로 리셋합니다. 사용자 지시는 항상 워크플로 규칙보다 우선합니다.

---

## 7. 자주 쓰는 명령 치트시트

slash command가 기본 인터페이스입니다. 스크립트를 직접 실행할 경우 `scripts/` 디렉토리를 참조하세요.

- **[`/team-init <ticket>`](../.claude/commands/team-init.md)** — 티켓 디렉토리와 `intake.md`를 생성합니다. (`scripts/team_init.sh`)
- **[`/team-spawn <role> <ticket>`](../.claude/commands/team-spawn.md)** — 역할별 ephemeral Claude 세션을 tmux/cmux 패인에 엽니다. (`scripts/team_spawn.sh`)
- **[`/team-collect <role> <ticket>`](../.claude/commands/team-collect.md)** — 완료된 역할의 리포트 파일을 출력합니다. (`scripts/team_collect.sh`)
- **[`/team-status`](../.claude/commands/team-status.md)** — 활성 패인과 파일 소유권 상태를 표시합니다. (`scripts/team_status.sh`)
- **[`/team-close <role>`](../.claude/commands/team-close.md)** — 역할 패인을 닫습니다. (`scripts/team_close.sh`)

---

*원천 파일: [`.team/roles/`](../.team/roles/) · [`.team/role-presets.json`](../.team/role-presets.json) · [`.team/file-ownership.json`](../.team/file-ownership.json) · [`.claude/skills/team-orchestration/`](../.claude/skills/team-orchestration/) · [`.claude/commands/`](../.claude/commands/)*
