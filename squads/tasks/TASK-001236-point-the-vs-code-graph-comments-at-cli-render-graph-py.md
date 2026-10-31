---
id: TASK-1236
sequence_id: 1236
type: task
title: Point the VS Code graph comments at _cli/_render/_graph.py
status: Done
parent: FEAT-1226
author: tech-lead
assignee: typescript-dev
refs:
- TASK-1228:depends-on
description: Comment-only fix of two stale _services/_refs.py pointers in graphDiagrams.ts
subentities:
- local_id: ST1
  title: Update the two helper pointers
  status: Done
  maps_to: US1
created_at: '2026-10-29T01:30:24Z'
updated_at: '2026-10-29T01:31:32Z'
priority: low
---
<!-- sq:body -->
The comments at lines 30 and 138 of `clients/vscode/src/domain/graphDiagrams.ts` name `_mermaid_node_id` and `_collect_edges` in `_services/_refs.py`. Both helpers now live in `src/squads/_cli/_render/_graph.py`, where TASK-1228 moved them. Update the two pointers; no code change.

Acceptance: both comments name `_cli/_render/_graph.py`; `npm run lint` and `npm test` in `clients/vscode/` stay green. New tests: 0.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1236 add-subtask "<title>"`; track with `sq task 1236 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Update the two helper pointers

<!-- sq:subtask:ST1:body -->
In `clients/vscode/src/domain/graphDiagrams.ts`, line 30 (`_mermaid_node_id`) and line 138 (`_collect_edges`): replace `_services/_refs.py` with `_cli/_render/_graph.py`, keeping the comment text otherwise as it is. Run `npm run lint` (eslint, zero warnings) and `npm test` (vitest) in `clients/vscode/` and record the results in a comment.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-29T01:31:16Z] `typescript-dev` Ada Typescript:
  - Both pointers in graphDiagrams.ts (lines 30, 138) now name _cli/_render/_graph.py; helpers confirmed there (_collect_edges, _mermaid_node_id). node_modules present. npm run lint: eslint --max-warnings 0, clean. npm test: 36 files, 760 tests passed.
- [2026-10-29T01:31:32Z] `manager` Catherine Manager:
  - Done 2026-10-29: comment-only change, verified (helpers live in _cli/_render/_graph.py; eslint clean, 760 client tests passed).
<!-- sq:discussion:end -->
