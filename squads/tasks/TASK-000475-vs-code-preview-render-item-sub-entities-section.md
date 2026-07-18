---
id: TASK-475
sequence_id: 475
type: task
title: 'VS Code preview: render item sub-entities section'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: high
description: 'Client: preview lists item sub-entities (US1/F15 client)'
created_at: '2026-07-18T20:10:32Z'
updated_at: '2026-07-18T20:23:06Z'
---
<!-- sq:body -->
Story: US1 (REV-448 F15, High). **Discipline: CLIENT / TypeScript** (`clients/vscode/`). No core change.

## Scope

The item preview renders body, mermaid graphs (children + refs), and discussion, but its JSON model (`types.ts`) maps only `discussion` and omits the item's sub-entities. `sq show <id> --json` already exposes a full `subentities` array (each with local_id, title, status, assignee, severity, story, body).

- Extend the preview JSON model to carry `subentities`.
- Render a preview section listing sub-entities in JSON array order — at minimum the head badge line (status / severity / assignee / story) per entity; ideally each entity's body as collapsible prose, mirroring the discussion section.
- Escape entity prose through the existing markdown renderer with mermaid-fences off, consistent with the discussion section.

## Acceptance

- A feature preview shows its stories; a review preview shows its findings; a task preview shows its subtasks.
- Sub-entities render in JSON array order with the head badge line present per entity.
- Client-only: no new core/machine surface.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 475 add-subtask "<title>"`; track with `sq task 475 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:23:03Z] Ada Typescript:
  - Implemented: types.ts SqSubEntity + SqShowJson.subentities; sqAdapter.ts isSqSubEntity guard + isSqShowJson extended; previewDocument.ts buildSubEntitiesHtml/SubEntitiesOutcome (mirrors buildDiscussionHtml: failure msg / empty->'' / populated details, head badge line status+severity+assignee+story omitting nulls, per-entity body as collapsible <details> through renderMarkdownToHtml mermaid-fences-off); itemPreviewManager.ts wires getShowJson's subentities into the new section (both success and no-invocation-resolved paths).
  - Section sits between graphsHtml and discussionHtml in buildPreviewHtml. Client-only, no core change.
  - Gates: tsc --noEmit clean, eslint --max-warnings 0 clean, prettier --check clean, npm test 188/188 green, npm run test:canary 10/10 green.
<!-- sq:discussion:end -->
