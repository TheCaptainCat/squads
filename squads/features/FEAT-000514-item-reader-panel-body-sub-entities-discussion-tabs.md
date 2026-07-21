---
id: FEAT-514
sequence_id: 514
type: feature
title: 'Item reader panel: body, sub-entities, discussion tabs'
status: InReview
parent: EPIC-28
author: product-owner
priority: medium
refs:
- FEAT-15:depends-on
- FEAT-19:depends-on
subentities:
- local_id: US1
  title: Selecting a node shows its detail
  status: Todo
- local_id: US2
  title: Body renders as markdown
  status: Todo
- local_id: US3
  title: Sub-entities and discussion as tabs
  status: Todo
- local_id: US4
  title: Status/priority/assignee at a glance
  status: Todo
created_at: '2026-07-21T09:11:26Z'
updated_at: '2026-07-21T12:05:30Z'
---
<!-- sq:body -->
## Capability

Selecting a node in the `sq ui` tree (FEAT-513) shows that item's full detail in a
reader panel: rendered markdown body, its sub-entities (stories/subtasks/findings, as
applicable to the type), and its discussion history, organized as tabs the user can
switch between. Status, priority, and assignee are visible at a glance without opening
a tab. Reading only — no editing of any of it from here.

Consumes the same frozen machine surface as FEAT-513: item detail, sub-entity state,
and discussion content all come from the `--json` shapes fixed in FEAT-15, addressed
through the shared resolver from FEAT-19.

## Acceptance

- Selecting any node in the tree populates the reader panel with that item's detail;
  changing the selection updates the panel accordingly.
- A body tab renders the item's markdown body legibly (headings, lists, emphasis,
  code blocks) rather than showing raw markdown source.
- A sub-entities tab lists the item's stories/subtasks/findings (whichever apply to its
  type) with each one's status, assignee, and title visible.
- A discussion tab shows the item's comment history in order, with author and
  timestamp per entry.
- Status, priority, and assignee are visible without switching tabs (e.g. a header or
  summary line above the tabs).
- The user can switch between tabs with the keyboard.
- An item with no sub-entities or no discussion shows an empty state on that tab rather
  than an error.

## Non-goals (this feature)

- No editing the body, no transitioning status, no commenting, no assigning — reading
  only. (That's FEAT-515, a later increment.)
- No search/filter within the discussion or sub-entity list.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 514 add-story "As a <role>, I want … so that …"`; track with `sq feature 514 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Selecting a node shows its detail |
| US2 | Todo |  | Body renders as markdown |
| US3 | Todo |  | Sub-entities and discussion as tabs |
| US4 | Todo |  | Status/priority/assignee at a glance |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Selecting a node shows its detail

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
Selecting any tree node populates the reader panel with that item's body, sub-entities, and discussion; changing selection updates the panel.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Body renders as markdown

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
The body tab renders the item's markdown (headings, lists, emphasis, code blocks) rather than showing raw source.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Sub-entities and discussion as tabs

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
Stories/subtasks/findings and the discussion history each get their own tab, switchable by keyboard, with empty-state handling when there's none.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Status/priority/assignee at a glance

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
Status, priority, and assignee are visible in a header/summary line without switching tabs.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
