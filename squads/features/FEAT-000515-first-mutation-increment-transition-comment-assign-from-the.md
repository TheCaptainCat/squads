---
id: FEAT-515
sequence_id: 515
type: feature
title: 'First mutation increment: transition/comment/assign from the TUI'
status: Draft
parent: EPIC-28
author: product-owner
priority: low
created_at: '2026-07-21T09:11:27Z'
updated_at: '2026-07-21T09:12:07Z'
---
<!-- sq:body -->
## Capability

The first increment that lets the TUI *do* something, not just show it: from within
`sq ui`, transition an item's status, add a comment, and change its assignee, using the
same validated service layer the CLI calls (locked transactions, workflow rules
enforced identically). This turns the TUI from a viewer into a place operators can
actually work a squad from.

This is a later increment, out of scope for the 0.12 browse-first cycle (FEAT-513,
FEAT-514). Captured now so the epic's full arc is visible on the board.

## Acceptance (indicative — to be refined when this increment is scoped)

- From the reader panel, the user can transition the selected item's status to any
  status its workflow allows, and an illegal transition is rejected the same way the
  CLI would reject it.
- The user can add a discussion comment to the selected item without leaving the TUI.
- The user can change the selected item's assignee.
- Every mutation goes through the same service layer as the CLI (no bespoke write
  path), so validation and locking behave identically.
- The tree/reader panel reflect a mutation immediately after it's made.

## Non-goals (this feature)

- Item creation (new epics/features/tasks/etc.) from the TUI.
- Body editing from the TUI.
- Any mutation not listed above (e.g. ref management, retype, remove).
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 515 add-story "As a <role>, I want … so that …"`; track with `sq feature 515 story <n> update --status <Status>`._

<!-- sq:summary -->
<!-- sq:summary:end -->

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
