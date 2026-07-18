---
id: TASK-478
sequence_id: 478
type: task
title: 'VS Code roster: drop assignee, add meta-type icons'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: low
description: 'Client: roster polish F18+F22 (US4 client)'
created_at: '2026-07-18T20:10:34Z'
updated_at: '2026-07-18T20:48:25Z'
---
<!-- sq:body -->
Story: US4 (REV-448 F18 + F22, Low). **Discipline: CLIENT / TypeScript** (`clients/vscode/`, `domain/metaView.ts`). No core change.

## Scope

Roster view (roles / skills / operators) polish — two findings, one file.

- **F18**: roster item descriptions build `${status} · ${assignee ?? 'unassigned'}` like the work tree, but assignee is meaningless for meta items and renders a noise `· unassigned`. Drop the assignee segment from roster descriptions; keep status alone. Only the work tree (`treeMapping`/`listView`) keeps assignee.
- **F22**: roster items fall back to the generic `circle-outline` because `ICON_BY_TYPE` holds only the 7 work-item types. Give the 3 meta types real codicons — role → `hubot`, operator → `account`, skill → `mortar-board` — via `ICON_BY_TYPE` or a small `META_ICON` map. Hardcoding these 3 is fine (role/skill/operator are contractually fixed, unlike F21's work-item types).

## Acceptance

- Roster descriptions show status alone — no `· unassigned` segment; work-tree descriptions unchanged.
- role/skill/operator render distinct codicons, not `circle-outline`.
- Client-only: no new core/machine surface.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 478 add-subtask "<title>"`; track with `sq task 478 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:48:22Z] Ada Typescript:
  - F18: metaView.ts itemToLeaf description is now item.status alone (no assignee segment); work-tree descriptions (treeMapping/listView) untouched.
  - F22: added META_ICON_BY_TYPE (role->hubot, operator->account, skill->mortar-board) + iconForMetaType() in displayNode.ts, kept deliberately separate from ICON_BY_TYPE/iconForType so TASK-479's squads.typeIcons override only touches work-item types, not the contractually-fixed reserved 3. metaView.ts now calls iconForMetaType.
  - TS gate: tsc/eslint/prettier clean, vitest 209/209 (2 new metaView cases), canary 10/10.
<!-- sq:discussion:end -->
