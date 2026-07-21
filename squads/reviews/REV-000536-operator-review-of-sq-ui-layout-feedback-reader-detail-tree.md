---
id: REV-536
sequence_id: 536
type: review
title: 'Operator review of sq ui: layout, feedback, reader detail, tree grouping'
status: Approved
author: op-pierre
refs:
- FEAT-513
- FEAT-514
- FEAT-525
- FEAT-526
description: Pierre's hands-on review of the sq ui browse + filter + search work
subentities:
- local_id: F1
  title: Search results panel only fills half the screen
  status: Fixed
  severity: medium
- local_id: F2
  title: No running indicator while a search is in flight
  status: Fixed
  severity: medium
- local_id: F3
  title: Reader sub-entities tab shows no sub-entity body
  status: Fixed
  severity: medium
- local_id: F4
  title: Discussion tab should render markdown (bullet lists etc.)
  status: Fixed
  severity: low
- local_id: F5
  title: Split the tree into Work and Roster top-level nodes
  status: Fixed
  severity: medium
created_at: '2026-07-21T14:12:09Z'
updated_at: '2026-07-21T14:37:55Z'
---
<!-- sq:body -->
Live review of `sq ui` on the branch. Findings below span the browse/reader (FEAT-513/514) and the filter/search increment (FEAT-525/526).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 536 add-finding "…" --severity medium`; track with `sq review 536 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Search results panel only fills half the screen |
| F2 | 🟡 medium | Fixed |  | No running indicator while a search is in flight |
| F3 | 🟡 medium | Fixed |  | Reader sub-entities tab shows no sub-entity body |
| F4 | 🟢 low | Fixed |  | Discussion tab should render markdown (bullet lists etc.) |
| F5 | 🟡 medium | Fixed |  | Split the tree into Work and Roster top-level nodes |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Search results panel only fills half the screen

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
The search results ListView leaves a large empty gap between the type/status selects and the list — the results area doesn't expand to fill the available height. Give the results list the remaining height (1fr) so it fills the screen.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-21T14:28:04Z] Elias Python:
  - Fixed: the selects row (a Horizontal) defaults to height:1fr like every Horizontal -- pinned it to height:auto via id (#search-filters) and gave the results ListView height:1fr explicitly, so it now fills the remaining screen.
  - Verified: new Pilot test asserts results height > 2x the filters row height.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — No running indicator while a search is in flight

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
The @work search gives no feedback — the UI looks frozen. Show a 'Searching…' state (status line and/or a loading indicator) while the worker runs, cleared when results arrive.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-21T14:28:05Z] Elias Python:
  - Fixed: SearchScreen sets the status line to 'Searching...' and ListView.loading=True right before dispatching the @work search, clearing both (loading=False, status cleared/set) once results or the empty state land.
  - Verified: new Pilot test gates svc.search behind an anyio.Event, asserts loading+status mid-flight, then releases the gate and asserts both clear.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Reader sub-entities tab shows no sub-entity body

<!-- sq:finding:F3:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
The sub-entities tab renders only the summary row (status/assignee/title), not each sub-entity's body prose. Show the body for each story/subtask/finding (e.g. head line + rendered body per sub-entity), not just the table.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-21T14:28:20Z] Elias Python:
  - Fixed: sub-entities tab now renders each story/subtask/finding as its own block (head line -- status/assignee/declared-field badges/mapped story, spec-generic, same derivation as the CLI's pane-title line -- plus its rendered body), not just the summary table. Read path: svc.get_block(parent_id, kind, local_id) -> SubentityDetail.body (read-only, already existed for 'sq <kind> show'). Widget changed Static->Markdown so the body actually renders as markdown; empty body per-block shows '(no body yet)', no sub-entities shows '(none)'.
  - Verified: extended test_subentities_tab_... in test_browse_screen.py to assert the head line, assignee and body prose all appear in the rendered markdown source; empty states for a story-less feature and a role (no kind) still pass. Plus a bracket-content regression test for the new body-rendering surface.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Discussion tab should render markdown (bullet lists etc.)

<!-- sq:finding:F4:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Comments render as plain text; bullet lists and other markdown aren't rendered. Render each comment body as markdown (like the body tab), keeping author/timestamp headers.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-07-21T14:28:21Z] Elias Python:
  - Fixed: discussion tab widget changed Static->Markdown; each comment renders as '**timestamp** _author_' + its body rendered as markdown (bullet lists etc. now actually render as list blocks), separated by a rule. Bracket-safe by construction, not by escaping: Markdown parses commonmark, not Textual's Content markup, so the BUG-535 class of bug doesn't apply to this widget at all (same reasoning as the existing body tab).
  - Verified: extended the discussion test to assert a bullet-containing comment mounts a MarkdownParagraph child (not raw text) and ordering/author still hold; empty state ('(none)') still passes.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Split the tree into Work and Roster top-level nodes

<!-- sq:finding:F5:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Mirror the VS Code extension: two top-level groups — Work (epics/features/tasks/bugs/decisions/reviews/…) and Roster (roles/operators/skills) — instead of one flat forest mixing them. Group tree_view's roots by meta-vs-work type under two synthetic parents.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-07-21T14:28:30Z] Elias Python:
  - Fixed: populate_tree now takes the active WorkflowSpec and adds two synthetic top-level nodes (Work, Roster; data=None, so selecting the group header itself is a no-op, not a reader load) before attaching each tree_view() root under whichever group matches spec.item_is_meta(root.item.type). Filter/sort untouched -- both already operate on the flat tree_view()-returned forest before grouping, so narrowing/sorting still work identically within each group (partition-after-sort preserves each group's relative order).
  - Verified: new Pilot test asserts the top-level labels are exactly ['Work','Roster'], work items land under Work, ROLE-1 lands under Roster, and the two sets are disjoint. Migrated every existing test that walked tree.root.children directly (structure is now one level deeper).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T14:31:10Z] Catherine Manager:
  - All five findings Fixed and verified: F1 results list now fills height (1fr), F2 'Searching…' + loading state during the worker, F3 sub-entities tab renders each block's head + body (read-only get_block), F4 discussion renders as markdown (bullets etc.), F5 tree split into Work/Roster top-level nodes. Full suite green, pyright/ruff/sq check clean, 38 tui tests. Left Requested for your re-review — approve when you're happy.
- [2026-07-21T14:37:53Z] Pierre Chat:
  - Re-reviewed on the branch — looks good. Approved.
<!-- sq:discussion:end -->
