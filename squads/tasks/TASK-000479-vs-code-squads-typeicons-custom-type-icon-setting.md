---
id: TASK-479
sequence_id: 479
type: task
title: 'VS Code: squads.typeIcons custom type-icon setting'
status: Done
parent: FEAT-471
author: tech-lead
assignee: typescript-dev
priority: low
description: 'Client: custom type-icon setting (US5/F21 client)'
created_at: '2026-07-18T20:10:35Z'
updated_at: '2026-07-18T20:52:50Z'
---
<!-- sq:body -->
Story: US5 (REV-448 F21, Low). **Discipline: CLIENT / TypeScript** (`clients/vscode/`, `domain/displayNode.ts`). No core change.

## Scope

`ICON_BY_TYPE` hardcodes the 7 bundled work-item types → codicons; it degrades gracefully to a generic icon for anything unrecognized, but a renamed/custom type gets no distinct icon, and icons aren't on the machine surface.

- Add a VS Code setting `squads.typeIcons`: `{ <typeName>: <codicon-id> }`, layered over the bundled `ICON_BY_TYPE` defaults.
- Keep the graceful generic fallback for anything still unmapped.
- Optionally seed the setting's description with the bundled defaults so adopters see the shape.

## Acceptance

- A user-mapped custom/renamed type renders the configured codicon; the bundled defaults still apply when the setting is unset; unmapped types still fall back to the generic icon.
- Client-only, spec-agnostic: no core change, no hardcoded assumption beyond the bundled default seed.
- TS gate parity: tsc strict + eslint zero-warnings + prettier; skew canary green.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 479 add-subtask "<title>"`; track with `sq task 479 subtask <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:subtasks -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-18T20:52:47Z] Ada Typescript:
  - Added squads.typeIcons setting (package.json: object, additionalProperties string, default {}, description seeds the 7 bundled defaults) layered over ICON_BY_TYPE in domain/displayNode.ts::iconForType(type, overrides = {}) — overrides win, then bundled default, then generic circle-outline fallback. Threaded as an optional TypeIconOverrides param through treeMapping.ts::treeNodesToDisplay and listView.ts::groupListItems/buildFilteredGroupedView (mirrors the existing TypeOrderMap threading pattern).
  - treeDataProvider.ts reads vscode.workspace.getConfiguration('squads').get('typeIcons', {}) fresh on every refresh() and passes it to both the tree and flat/grouped fetch paths. Roster (meta) icons are untouched — iconForMetaType/META_ICON_BY_TYPE (TASK-478) stays separate, so the 3 reserved types are never affected by this setting.
  - TS gate: tsc/eslint/prettier clean, vitest 212/212 (4 new override cases across treeMapping/listView), canary 10/10.
<!-- sq:discussion:end -->
