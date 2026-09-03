---
id: FEAT-621
sequence_id: 621
type: feature
title: 'Roster view filtering: parity with work/records filter surfaces'
status: Done
author: product-owner
refs:
- PRD-863:implements
description: Roster view (TUI + VS Code) lacks the type/status filtering work/records
  gained; deferred follow-up
created_at: '2026-07-23T07:11:12Z'
updated_at: '2026-09-01T13:51:05Z'
---
<!-- sq:body -->
The Roster view (TUI + VS Code) lacks the type/status filtering that the work and records surfaces have. Add filter parity so the roster can be narrowed the same way. Deferred during the FEAT-570 dev-host pass; not scheduled.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 621 add-story "As a <role>, I want … so that …"`; track with `sq feature 621 story <n> update --status <Status>`._

<!-- sq:stories -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-23T07:11:32Z] Pierre Chat:
  - Deferred follow-up from the FEAT-570 visual pass: roster section has no filters; do it later.
- [2026-07-29T08:56:05Z] Olivia Lead:
  - Broken down, and the one-paragraph spec turns out to be wrong in both directions — evidence below. TASK-688 (VS Code) is the whole of it; I did NOT author a TUI task, because there is nothing to build there.
  - TUI: there is no separate Roster surface in sq ui. _tui/_tree.py builds ONE tree with three synthetic category groups (Work / Records / Roster, _GROUP_ORDER), fed by svc.tree_view(filter=...), and FilterScreen already exposes type, status, CATEGORY (work/records/roster), assignee, label, badge, sort and include-closed — all of which apply to roster items because they are in the same tree. Confirmed roster items are in the tree: sq tree --json returns 22 ROLE/SKILL/OP ids on this board. So the TUI already has roster filtering, including a category filter that narrows TO the roster. Recommend closing the TUI half as already satisfied rather than scheduling it.
  - VS Code: the gap is WIDER than filed, not narrower. The premise 'the type/status filtering that the work and records surfaces have' is false — package.json contributes filterByType / toggleGroupByType / toggleShowClosed / clearFiltersAndGrouping to squadsTree ONLY. squadsMeta and squadsRecords each get squads.refreshAll and nothing else. So Records has no filters either; that is the same gap on a second view and out of this feature's scope — @product-owner may want it as its own item.
  - Parity defined in TASK-688's body rather than assumed: it means the same ABILITY TO NARROW expressed in the dimensions a fixed-bucket tree has — hide-archived (Archived is terminal: is_open false, status role 'retired', so the existing show-closed predicate already means the right thing) and filter-to-one-status. Group-by-type is meaningless (the tree is already grouped by type) and filter-by-type is a deliberate non-goal (the three buckets ARE the type filter, and they collapse). BUG-687's state-visibility requirement is folded in as a per-increment obligation, with a depends-on so the toggle adopts Ada's idiom rather than inventing a second one.
- [2026-07-29T09:14:05Z] Catherine Manager:
  - TUI half closed as already satisfied, verified directly: sq ui builds one tree with Work/Records/Roster category groups, and its filter screen already offers status, category and show-closed — all of which apply to roster items because they are in the same tree. 22 roster ids confirmed present in sq tree --json. No TUI work needed; the VS Code half is TASK-688.
<!-- sq:discussion:end -->
