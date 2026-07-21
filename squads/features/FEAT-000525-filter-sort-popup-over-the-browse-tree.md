---
id: FEAT-525
sequence_id: 525
type: feature
title: Filter/sort popup over the browse tree
status: Done
parent: EPIC-28
author: product-owner
priority: medium
subentities:
- local_id: US1
  title: Open/dismiss the filter+sort popup by keyboard
  status: Todo
- local_id: US2
  title: Set filters and apply, tree updates keeping ancestors as context
  status: Todo
- local_id: US3
  title: Show-closed toggle reveals and hides terminal items
  status: Todo
- local_id: US4
  title: Choose sibling sort order, clear/reset filters, see active-filter indicator
  status: Todo
created_at: '2026-07-21T12:14:41Z'
updated_at: '2026-07-21T14:38:09Z'
---
<!-- sq:body -->
## Capability

A keyboard-invoked popup over the browse tree (FEAT-513) lets the user set filters and sort,
applied to the tree in place. This is the direct answer to "there's no way to display
terminal/Done items" — the show-closed toggle lives here.

A pure read-only consumer of the existing service surface: filters map onto `ItemFilter`'s
existing dimensions (item type, status, assignee, label, spec-generic badge fields such as
priority) plus `tree_view`'s `include_closed` flag for show-closed. No new backend capability
is introduced — the popup only assembles and re-applies an `ItemFilter` + `include_closed` the
service already accepts.

Sort orders **siblings** within the tree (the tree is a hierarchy, not a flat list, so sort
never reorders across levels): by id (default), by a badge field (e.g. priority), by status, by
title, or by last-updated.

## Acceptance

- A keyboard shortcut opens the popup over the tree view; another (e.g. Escape) dismisses it
  without applying pending changes.
- The popup offers each `ItemFilter` dimension (item type, status, assignee, label, a badge
  field such as priority) plus a show-closed toggle; setting one or more and applying updates
  the tree to match, keeping ancestors of matches visible as context (mirroring `sq tree`'s
  own match+ancestor behavior) rather than pruning them out.
- Toggling show-closed on reveals terminal/Done items in the tree; toggling it back off hides
  them again.
- Choosing a sort dimension changes sibling order at every level of the tree; id order is the
  default when no sort is chosen.
- A clear/reset action returns every dimension to unset and sort to default in one step.
- While any filter dimension is active, a visible indicator on the browse view tells the user
  the tree is filtered (so an empty-looking or short tree is never mistaken for "no more
  items").
- Every interaction — open, dismiss, set each filter dimension, toggle show-closed, choose
  sort, clear — is reachable by keyboard alone, with no mouse dependency, so it works over a
  plain SSH session.

## Non-goals (this feature)

- No new filter/sort dimensions beyond what `ItemFilter` and `tree_view` already expose.
- No mutation of any item (no status change, comment, assignment) from the popup.
- No persisting filter/sort state across `sq ui` launches — each session starts unfiltered.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 525 add-story "As a <role>, I want … so that …"`; track with `sq feature 525 story <n> update --status <Status>`._

<!-- sq:summary -->
| Story | Status | Assignee | Title |
| --- | --- | --- | --- |
| US1 | Todo |  | Open/dismiss the filter+sort popup by keyboard |
| US2 | Todo |  | Set filters and apply, tree updates keeping ancestors as context |
| US3 | Todo |  | Show-closed toggle reveals and hides terminal items |
| US4 | Todo |  | Choose sibling sort order, clear/reset filters, see active-filter indicator |
<!-- sq:summary:end -->

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Open/dismiss the filter+sort popup by keyboard

<!-- sq:story:US1:head -->
**Status:** ⚪ Todo
<!-- sq:story:US1:head:end -->

<!-- sq:story:US1:body -->
A keyboard shortcut opens the filter/sort popup over the tree; Escape dismisses it without applying pending changes.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Set filters and apply, tree updates keeping ancestors as context

<!-- sq:story:US2:head -->
**Status:** ⚪ Todo
<!-- sq:story:US2:head:end -->

<!-- sq:story:US2:body -->
Setting one or more filter dimensions (type, status, assignee, label, badge field) and applying updates the tree to matches, keeping ancestors visible as context.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Show-closed toggle reveals and hides terminal items

<!-- sq:story:US3:head -->
**Status:** ⚪ Todo
<!-- sq:story:US3:head:end -->

<!-- sq:story:US3:body -->
A show-closed toggle reveals terminal/Done items in the tree; toggling it off hides them again.
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Choose sibling sort order, clear/reset filters, see active-filter indicator

<!-- sq:story:US4:head -->
**Status:** ⚪ Todo
<!-- sq:story:US4:head:end -->

<!-- sq:story:US4:body -->
A sort dimension reorders siblings at every level (id, badge field, status, title, or last-updated); a clear/reset action returns filters and sort to default in one step, and an indicator shows when the view is filtered.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
