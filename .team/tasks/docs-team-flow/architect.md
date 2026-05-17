## 설계 판단
- 권장 구조는 **quick-start-first**다. 이유는 신규 독자가 가장 먼저 답하려는 질문이 "어떻게 티켓을 열고 첫 역할을 시작하나?"이기 때문이다. `team_init` 계열 명령과 intake 생성 흐름을 초반에 보여준 뒤, 역할/파이프라인/산출물/에스컬레이션을 점진적으로 설명하는 편이 onboarding 문서 목적에 맞다.
- 비교한 구조 후보는 아래 3가지다.
  1. **권장: quick-start-first** — 목적/독자 → 티켓 열기 → 역할/격리 → 표준 진행 순서 → 산출물 위치 → 에스컬레이션 → 명령 치트시트
  2. **대안: pipeline-first** — 목적/독자 → 표준 진행 순서 → 역할 → 산출물 → 에스컬레이션 → 명령. 장점은 운영 모델이 먼저 잡히지만, 초심자가 바로 따라 할 시작점이 늦게 나온다.
  3. **비권장: artifact-first** — 목적/독자 → 산출물 위치 → 역할 → 진행 순서 → 에스컬레이션 → 명령. 경로 탐색에는 유리하지만, 왜 그 파일이 생기는지 이해하기 전에 경로가 먼저 나와 입문 흐름이 끊긴다.
- 제안하는 `docs/team-flow.md` top-level TOC는 아래 7개 섹션이다. 하위 섹션은 꼭 필요한 곳에만 둔다.
  1. **문서 목적과 대상 독자** — 이 문서가 Claude Code 일반 사용법이 아니라, 이 저장소의 team-orchestration 운영 흐름을 처음 익히는 사람을 위한 onboarding 가이드임을 선언한다.
  2. **빠른 시작: 티켓 열기** — `/team-init <ticket>`를 첫 인터페이스로 소개하고, `.team/tasks/<ticket>/intake.md` 생성 → intake 보강 → `/team-spawn`으로 첫 역할 dispatch까지의 최소 절차를 예시 ticket slug와 함께 설명한다.
  3. **역할별 책임과 역할 격리** — lead / requirement-analyst / architect / researcher / developer / qa-reviewer가 각각 무엇을 결정하고 어떤 리포트를 남기는지 표로 요약하고, `.team/file-ownership.json`과 PreToolUse ownership check가 역할 경계를 강제한다는 점을 짧게 붙인다.
  4. **표준 진행 순서** — requirements → analysis → implementation → QA → integration의 방향성을 설명하고, requirement-analyst 이후 researcher+architect 병렬 가능 조건, skip은 근거가 있어야 한다는 운영 규칙, implementer의 기본값과 예외를 newcomer 수준으로 정리한다.
  5. **리포트와 작업 산출물 위치** — `.team/tasks/<ticket>/intake.md`, `.team/tasks/<ticket>/<role>.md`, `.team/tasks/<ticket>/<role>.log`, `.team/current-goal.md`가 각각 무엇을 담는지와 role report 경로 예시를 보여준다.
  6. **에스컬레이션이 발생하는 경우** — QA fail, Architect risk flag, Requirement gap mid-implementation, Researcher cannot find evidence, File ownership conflict, Worker pane stuck/unresponsive, User intervenes mid-pipeline의 trigger와 Lead의 즉시 조치를 한 줄 이상씩 적는다.
  7. **자주 쓰는 명령 치트시트** — `/team-init`, `/team-spawn`, `/team-collect`, `/team-status`, `/team-close`를 한 줄씩 설명하고, 필요하면 스크립트 경로는 괄호 수준의 보조 정보로만 덧붙인다.
- 섹션 3, 4, 6만 최소 하위 구조를 둔다.
  - 섹션 3: 역할 요약 표 + 역할 격리 한 단락
  - 섹션 4: 단계 순서 + skip/병렬 조건 짧은 bullet
  - 섹션 6: trigger/action 짝 목록
- 길이 목표는 requirement-analyst 제안에 맞춰 **약 700–1100단어**로 두고, 결과적으로 Markdown 기준 **대략 200–350줄 내외**에 들어오게 설계한다. 표는 1개, 짧은 bullet list는 허용하되 긴 배경 설명은 피한다.

## 위험
- **역할 allow 범위와 실제 owner를 초심자가 같은 개념으로 오해할 수 있다.** downside는 "architect도 docs/** allow인데 왜 docs 소유자는 researcher인가?" 같은 혼란이 생기는 것이다. **완화:** 역할 표 바로 아래에 "실제 최종 편집 권한은 `.team/file-ownership.json`이 정하고, allow/deny는 역할이 작업 중 접근 가능한 범위"라는 한 문단을 둔다.
- **Escalation 기록 위치가 intake.md와 lead.md 사이에서 충돌해 보인다.** downside는 newcomer 문서가 잘못된 canonical 위치를 단정할 위험이다. **완화:** 본문은 escalation을 "티켓 아티팩트 아래에 Lead가 기록한다" 수준으로 설명하고, 경로를 정확히 박아야 하는 것은 role report 위치만 canonical로 적는다.
- **표준 파이프라인의 Developer 절대성과 doc-only 예외가 충돌해 보일 수 있다.** downside는 "Developer는 절대 skip 불가"와 "docs/**는 researcher owner"가 같은 문서에서 모순처럼 읽히는 것이다. **완화:** 표준 진행 순서에서는 Developer를 기본 implementer로 설명하되, skip/예외 문장 하나로 "최종 편집 주체는 ownership 규칙을 따른다"를 붙여 doc-only 티켓을 예외로 흡수한다.
- **명령과 스크립트를 동급으로 나열하면 newcomer가 어느 인터페이스를 먼저 써야 하는지 놓칠 수 있다.** downside는 slash command 대신 내부 스크립트부터 실행하려는 우회 행동이 생기는 것이다. **완화:** 본문과 예시는 slash command 중심으로 쓰고, 스크립트는 치트시트 또는 괄호 주석에서만 보조적으로 언급한다.
- **치트시트를 너무 앞에 두면 운영 원리보다 명령 암기에 치우칠 수 있다.** downside는 역할 격리와 escalation 규칙을 이해하지 못한 채 명령만 따라 하는 문서가 되는 것이다. **완화:** 치트시트는 마지막 섹션에 두고, 앞선 섹션에서 이미 흐름/역할/산출물을 이해한 뒤 빠르게 다시 찾는 용도로 위치시킨다.

## 수정 파일
- 없음. architect는 구조 제안만 수행하고 문서 본문은 작성하지 않는다.

## 검증
- 다음 역할은 `docs/team-flow.md`의 top-level section 수가 **7개 이하**인지, 그리고 순서가 위 제안과 같은지 먼저 확인하면 된다.
- 문서 첫 화면만 읽어도 `/team-init <ticket>` → `.team/tasks/<ticket>/intake.md` 생성 → intake 작성 → `/team-spawn requirement-analyst <ticket>` 흐름이 보이면 구조를 제대로 따른 것이다.
- 역할 섹션에 **6개 역할 모두**가 있고, 각 역할이 "무엇을 결정/산출하는가" 기준으로 중복 없이 구분되면 구조 목표를 충족한다.
- 역할 섹션 또는 그 직후에 `.team/file-ownership.json`과 PreToolUse ownership check를 언급해 role isolation 설명이 들어가 있어야 한다.
- 산출물 섹션에는 최소한 다음 경로가 정확히 문자열 그대로 있어야 한다: `.team/tasks/<ticket>/intake.md`, `.team/tasks/<ticket>/<role>.md`, `.team/tasks/<ticket>/<role>.log`, `.team/current-goal.md`.
- 에스컬레이션 섹션에는 7개 trigger가 모두 들어가고, 각 항목이 "무슨 일이 발생했을 때 / Lead가 즉시 무엇을 하는지"까지 포함해야 한다.
- 치트시트에는 `/team-init`, `/team-spawn`, `/team-collect`, `/team-status`, `/team-close`가 모두 한 줄씩 있어야 하며, 스크립트 설명이 본문 주인공이 되어서는 안 된다.
- 최종 문서는 700–1100단어, 표 1개, 짧은 bullet list 중심이면 이 구조의 의도와 분량 제약을 모두 지킨 것으로 본다.
