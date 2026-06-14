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
  title: As an operator, I want the squad hierarchy in a VS Code sidebar tree with
    status, assignee and blocked-state at a glance, so that I can navigate the squad
    without leaving the editor
  status: Todo
- local_id: US2
  title: As an operator, I want clicking a tree item to open its rendered sq show
    in the markdown preview, so that I read a clean item without frontmatter or marker
    noise
  status: Todo
- local_id: US3
  title: As an operator, I want to filter and group the tree by type and open/closed
    state and refresh it on demand, so that I can focus on the work that matters right
    now
  status: Todo
created_at: '2026-06-14T20:45:15Z'
updated_at: '2026-06-14T20:45:23Z'
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
| US1 | Todo |  | As an operator, I want the squad hierarchy in a VS Code sidebar tree with status, assignee and blocked-state at a glance, so that I can navigate the squad without leaving the editor |
| US2 | Todo |  | As an operator, I want clicking a tree item to open its rendered sq show in the markdown preview, so that I read a clean item without frontmatter or marker noise |
| US3 | Todo |  | As an operator, I want to filter and group the tree by type and open/closed state and refresh it on demand, so that I can focus on the work that matters right now |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — As an operator, I want the squad hierarchy in a VS Code sidebar tree with status, assignee and blocked-state at a glance, so that I can navigate the squad without leaving the editor

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — As an operator, I want clicking a tree item to open its rendered sq show in the markdown preview, so that I read a clean item without frontmatter or marker noise

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — As an operator, I want to filter and group the tree by type and open/closed state and refresh it on demand, so that I can focus on the work that matters right now

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance criteria here — free-form paragraphs or bullet lists._
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
