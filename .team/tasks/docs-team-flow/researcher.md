---
role: researcher
ticket: docs-team-flow
pass: fix-pass (QA-required fixes)
date: 2026-05-08
---

## 조사 범위

QA Reviewer 보고서(`.team/tasks/docs-team-flow/qa-reviewer.md`)의 MUST 항목 두 건을 `docs/team-flow.md`에 직접 적용하는 fix-pass. 코드 파일 수정 없음.

---

## 근거 파일

| 파일 | 관련 위치 | 역할 |
|---|---|---|
| `.team/tasks/docs-team-flow/qa-reviewer.md` | Finding 2 (line 189 bare `/team-close`), Finding 8–10 (cross-directory links) | fix 지시의 원천 |
| `scripts/team_close.sh:8–11, 24` | `--all` 플래그 존재 확인, 인수 없을 때 exit 2 확인 | Fix 1 근거 |
| `docs/team-flow.md:34, 35, 48, 53, 93, 110, 114, 116, 127, 175, 197–201, 205` | 실제 편집 대상 라인 | Fix 2 적용 위치 |

---

## 현재 동작

`docs/team-flow.md`는 QA MUST 항목을 모두 통과하는 상태입니다. line 189의 User intervenes 에스컬레이션 항목은 `/team-close --all`로 수정되어 런타임에서 exit 2 오류 없이 모든 패인을 닫습니다. `docs/` 외부를 가리키는 모든 Markdown 링크(`../.claude/`, `../.team/`, `../scripts/`, `../templates/`)에 `../` 프리픽스가 추가되어 GitHub 및 디렉토리 기준 Markdown 렌더러에서 링크가 정상 해석됩니다. 총 편집된 링크 위치: 13곳(lines 34, 35, 48, 93, 110 ×2, 114, 127, 175, 197–201, 205 ×5).

---

## 리스크

**의도적으로 미적용한 옵션 항목:**

- **QA Finding 3 (cheatsheet `/team-close --all` variant 명시)**: 치트시트 항목에 `--all` 변형 설명 추가는 OPTIONAL로 분류됨. 문서를 불필요하게 늘리지 않기 위해 생략.
- **QA Finding 7 (단어 수 1248 vs 상한 1100)**: 13% 초과이나 줄 수(205줄)는 목표 범위 내이고 내용이 실질적임. QA가 OPTIONAL로 처리했으며, 트리밍 시 가독성 손실이 더 크다고 판단하여 생략.

**잔존 리스크 없음**: MUST 항목 두 건 모두 적용 완료.
