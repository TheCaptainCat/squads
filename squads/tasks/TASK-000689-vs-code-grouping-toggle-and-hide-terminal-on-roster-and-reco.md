---
id: TASK-689
sequence_id: 689
type: task
title: 'VS Code: grouping toggle and hide-terminal on Roster and Records'
status: InProgress
parent: FEAT-621
author: op-pierre
description: Both views get a group-by-type toggle defaulting to grouped, plus a hide
  button
subentities:
- local_id: ST1
  title: Group-by-type toggle on Roster and Records
  status: Done
- local_id: ST2
  title: Hide-terminal button on Records
  status: Done
- local_id: ST3
  title: Visible active state and clear, both views
  status: Done
- local_id: ST4
  title: Dev-host verification per increment
  status: Todo
  assignee: op-pierre
created_at: '2026-07-29T09:50:19Z'
updated_at: '2026-07-29T10:03:56Z'
---
<!-- sq:body -->
## Scope

Both the **Roster** and **Records** trees gain two controls, matching what Work Items already has and reusing the idioms established in this release.

**A group-by-type toggle, defaulting to grouped.** Both trees are already bucketed per type, so the toggle's purpose is to let a reader *flatten* them into a single list. Grouped stays the default, so first-open appearance is unchanged.

**A hide button.** Roster already hides archived entries; Records gains the equivalent for terminal records — superseded and deprecated decisions, deprecated guides.

## Decisions already taken

**Records hides terminal records via the spec's own status role, never a literal status string.** Same mechanism the roster filter uses, so it survives a project renaming its statuses through a workflow override. Deliberately not the word 'closed' — that reads wrongly for a superseded decision.

**Grouped is the default for both.** A reader who has never touched the toggle sees today's shape.

This overrides an earlier scoping call that a grouping toggle is meaningless on a fixed-bucket tree. That reasoning was that it buys a flat list at the cost of a command and another piece of state to display and clear. The counter-argument, taken deliberately: a flat list is genuinely useful on a long roster or a large record set, and the cost is now much lower because the toggle idiom, the state-visibility mechanism and the clear-command shape all already exist from the roster work.

## Acceptance

- Both toggles use the two-command icon-swap idiom: distinct icon showing current state, title naming the action a click performs. A single command with a state flag renders identically on and off and is not acceptable.

- Active state is visible without opening a menu, on both views.

- Clear returns each view to its default (grouped, terminal hidden), not to show-everything, and that is documented at the call site.

- Work Items is untouched.

- Each behaviour has a test that fails when the behaviour is removed.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 689 add-subtask "<title>"`; track with `sq task 689 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Group-by-type toggle on Roster and Records |  |
| ST2 | Done |  | Hide-terminal button on Records |  |
| ST3 | Done |  | Visible active state and clear, both views |  |
| ST4 | Todo | op-pierre | Dev-host verification per increment |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Group-by-type toggle on Roster and Records

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Flatten toggle defaulting to grouped, two-command icon-swap idiom, on both views.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-07-29T10:03:32Z] Ada Typescript:
  - Group-by-type toggle added to both Roster and Records, defaulting to grouped (opposite default from Work Items' own group-by-type, which is untouched). New per-view state field (MetaViewState.groupByType / RecordsViewState.groupByType, both domain-level, vscode-free) plus flatten branch in buildMetaView/buildRecordsView — ungrouped mode returns one id-sorted flat list (compareIds, same comparator Work Items' own ungrouped view uses) instead of the per-type buckets, restricted to the view's own eligible types so nothing leaks across views.
  - Same two-command icon-swap idiom and titles as Work Items' pair (Group by Type / Ungroup, list-flat / list-tree icons) — new ids per view (toggleGroupByTypeMeta/ungroupByTypeMeta, toggleGroupByTypeRecords/ungroupByTypeRecords) since each is a distinct state with a different default, not the same command reused.
  - What to check in the dev host: Roster and Records both open grouped (unchanged first-open appearance); click Group by Type/Ungroup on each and confirm it flattens to one list and the button's icon/title swap; Work Items untouched.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Hide-terminal button on Records

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Hide superseded/deprecated decisions and deprecated guides, via the spec's status role, not a literal status string.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-07-29T10:03:44Z] Ada Typescript:
  - Hide-terminal on Records reuses the exact mechanism the Roster's hide-archived uses — resolveRole(status).hidden joined through the statuses/roles catalogs, never a literal status string. Superseded (role 'superseded') and Deprecated/Cancelled/Rejected (role 'retired') are all hidden:true; Accepted/Published (role 'in_force') are settled but hidden:false, so they stay visible while final-but-live, matching sq list --help's own documented split.
  - Wording: 'Terminal', not 'closed' — command titles are Show/Hide Terminal Records. Two-command icon-swap pair (squads.toggleShowTerminal/squads.hideTerminal), default hidden, contributed to squadsRecords view/title only.
  - What to check in the dev host: a superseded decision or deprecated guide is hidden by default; toggle reveals it (and merely-settled-but-live items like an Accepted decision stay visible throughout, never dimmed away).
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Visible active state and clear, both views

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Roster and Records each get a call-site-documented clear back to default (grouped, terminal hidden).
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-07-29T10:03:55Z] Ada Typescript:
  - All 4 new toggles (Roster group-by-type, Records group-by-type, Records show-terminal, plus the already-shipped Roster show-archived) are visible purely via their icon-swap pair — no new .description text needed, since every state added this round is a toggle with an icon pair, unlike the Roster's status filter (a quick-pick, no icon pair, TASK-688's reason .description exists at all). Recorded as a deliberate scope decision, not an oversight.
  - Clear added for Records (squads.clearRecordsFilter, 1_squads group, mirrors clearMetaFilter's placement): resets groupByType/showTerminal to default (grouped, terminal hidden) — not show-everything — documented at the command's registration site in commands.ts. Roster's existing clearMetaFilter now also resets the new groupByType field for free (already returns to DEFAULT_META_VIEW_STATE wholesale).
  - What to check in the dev host: flatten + show-terminal both on Records, confirm the toolbar shows both via their icons; Clear Filter, confirm the view returns to its first-open appearance. Same on Roster with its 3 states (status filter, show-archived, group-by-type).
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Dev-host verification per increment

<!-- sq:subtask:ST4:head -->
**Status:** ⚪ Todo
**Assignee:** Pierre Chat
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Live verification on the Windows dev host.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
