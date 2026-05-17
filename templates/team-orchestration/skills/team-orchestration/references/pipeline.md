# Pipeline reference

The pipeline is **directional**: requirements → analysis → implementation → QA → integration. Stages may be skipped with documented justification, but never reordered.

## Stage 1 — Requirement Analyst

**Run when**: ticket scope is ambiguous, acceptance criteria are not explicit, or the user request mentions a goal but not a behavior.

**Skip when**: user provides a precise behavioral spec (e.g., "rename function X to Y in file Z, no other changes").

**Output**: `.team/tasks/<ticket>/requirement-analyst.md` containing:
- 요구사항 요약
- 모호한 점
- 질문
- 구현 전제

If questions remain unanswered, surface them to the user before advancing.

## Stage 2 — Researcher + Architect (parallel)

**Researcher**: read code/docs/tests; report exact files, line ranges, current behavior, and risks. Cannot edit application code.

**Architect**: review state transitions, policy gates, dependency direction, data model impact, migration risk. May edit architecture docs only when explicitly assigned.

These two run **concurrently** because their inputs (the requirements doc) are stable and their outputs are independent. Wait for both before advancing.

**Skip Researcher when**: the codebase area is already well-known to Lead and no evidence question remains.

**Skip Architect when**: the change is a localized leaf-level edit with no cross-layer implications.

## Stage 3 — Developer

**Run only after**: requirements + (researcher or skip) + (architect or skip) are complete.

**Allowed scope**: explicitly assigned by Lead in the dispatch. Default `src/**` and `tests/**`. Lead must list specific files when the change is narrow.

**Output**: `.team/tasks/<ticket>/developer.md` with 한 일 / 변경 파일 / 검증 / 리스크.

**Parallelism rule**: two Developer tasks may run concurrently only if their allowed-scope file globs do not overlap. Verify against `file-ownership.json` before spawning.

## Stage 4 — QA Reviewer

**Run after**: Developer reports completion.

**Never parallel with**: the Developer it reviews. The whole point of QA is to catch what Developer missed; running them concurrently means QA reviews a moving target.

**Output**: `.team/tasks/<ticket>/qa-reviewer.md` with Findings / Missing tests / Regression risk / Approval readiness.

**On QA fail**: route back to Stage 3 with QA findings as new context. Do not skip and integrate.

## Stage 5 — Lead integration

1. Run `/team-collect` for each role; confirm all reports exist and QA is `Approval readiness: yes`.
2. Update `.team/current-goal.md` if the goal advanced.
3. Append a closing block to the ticket file:
   - Final integration result
   - Files actually merged
   - Residual risks accepted
   - Date closed
4. Release file ownership in `file-ownership.json` for any temporarily-held files.

## Decision: skip vs include a stage

When deciding whether to skip a stage, ask:

- Skip Requirement Analyst? → only if the user's request is *implementable as written*.
- Skip Researcher? → only if Lead can list every file the change will touch from memory with high confidence.
- Skip Architect? → only if the change cannot affect any other layer.
- Skip Developer? → never. (If no code change is needed, why is this a ticket?)
- Skip QA Reviewer? → never. Even doc changes get a regression-risk pass.

Log skip decisions in the ticket file with one-sentence justification.
