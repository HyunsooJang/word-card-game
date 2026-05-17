# docs-team-flow — intake

## User request
docs/team-flow.md 작성 — 신규 합류자가 팀 워크플로(역할/dispatch/리포트/escalation)를 빠르게 이해하도록.

## Pipeline plan
- [x] requirement-analyst
- [ ] researcher  (skip 정당화: doc-only 티켓이라 architect가 evidence + 구조 결합 통합)
- [x] architect
- [x] researcher (writer pass — docs/** owner)
- [ ] developer  (skip 정당화: 산출물이 docs/이라 owner가 researcher; 별도 developer 단계 불필요)
- [x] qa-reviewer
- [ ] integration

## Skip justifications
- researcher 첫 패스 생략: architect가 read-only로 .team/, .claude/, scripts/를 훑어 구조와 evidence를 한 번에 산출.
- developer 생략: docs/team-flow.md 의 owner가 researcher (file-ownership.json). researcher가 implementor 역할 겸직.
