---
id: FEAT-000100
sequence_id: 100
type: feature
title: 'Read-only browse: sidebar tree + rendered preview'
status: Draft
parent: EPIC-000099
author: product-owner
priority: low
description: VS Code activity-bar tree from sq tree --json; clicking an item opens
  rendered sq show in the markdown preview; filter/group + refresh
subentities:
- local_id: US1
  title: Squad hierarchy in VS Code sidebar with status and blocked-state
  status: Todo
- local_id: US2
  title: Clicking a tree node opens rendered sq show in markdown preview
  status: Todo
- local_id: US3
  title: Filter and group tree by type/state, refresh on demand
  status: Todo
created_at: '2026-06-14T20:45:15Z'
updated_at: '2026-06-23T10:01:48Z'
---
<!-- sq:body -->
The first, browse-only increment of the VS Code extension (EPIC-000099). A `SquadsTreeDataProvider`
backed by `sq tree --json` renders the hierarchy in an activity-bar view; selecting a node opens the
item's rendered `sq show` in VS Code's markdown preview through a `squads:` read-only virtual
document. No mutations in this increment.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 100 add-story "As a <role>, I want … so that …"`; track with `sq feature 100 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Squad hierarchy in VS Code sidebar with status and blocked-state |
| US2 | Todo |  | Clicking a tree node opens rendered sq show in markdown preview |
| US3 | Todo |  | Filter and group tree by type/state, refresh on demand |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Squad hierarchy in VS Code sidebar with status and blocked-state

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
As an operator, I want the squad hierarchy in a VS Code sidebar tree with status, assignee and blocked-state at a glance, so that I can navigate the squad without leaving the editor.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Clicking a tree node opens rendered sq show in markdown preview

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
As an operator, I want clicking a tree item to open its rendered sq show in the markdown preview, so that I read a clean item without frontmatter or marker noise.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Filter and group tree by type/state, refresh on demand

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
As an operator, I want to filter and group the tree by type and open/closed state and refresh it on demand, so that I can focus on the work that matters right now.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
