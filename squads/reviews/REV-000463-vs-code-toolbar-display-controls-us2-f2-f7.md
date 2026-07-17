---
id: REV-463
sequence_id: 463
type: review
title: VS Code toolbar & display controls (US2/F2-F7)
status: Approved
author: reviewer
refs:
- TASK-454:addresses
subentities:
- local_id: F1
  title: Type-filter picker omits closed-only types when show-closed is off
  status: Open
  severity: low
- local_id: F2
  title: clearFiltersAndGrouping intentionally leaves show-closed on
  status: Open
  severity: low
created_at: '2026-07-17T15:28:30Z'
updated_at: '2026-07-17T15:30:55Z'
---
<!-- sq:body -->
Independent review of TASK-454 (Ada built it) — the toolbar & display-controls changes under `clients/vscode/**` implementing REV-448 F2–F7. Verified against the working-tree diff (uncommitted); the `resources/*.svg` churn is unrelated concurrent TASK-458 icon work and out of scope here.

Per-finding verdict: all six pass. No correctness defects found. Recommended verdict: Approve. Two low/nit observations recorded below (neither blocking).

Gates (run by reviewer): `npm run check` exit 0 (tsc strict + eslint 0-warnings + prettier); `npm test` 125/125; `npm run test:canary` 8/8.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 463 add-finding "…" --severity medium`; track with `sq review 463 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Type-filter picker omits closed-only types when show-closed is off |
| F2 | 🟢 low | Open |  | clearFiltersAndGrouping intentionally leaves show-closed on |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Type-filter picker omits closed-only types when show-closed is off

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`knownItemTypes` feeds the filter-by-type quick-pick. It is now derived from the active fetch, which only includes closed items when the show-closed toggle is on (flat: `distinctTypes(sq list [--all])`; hierarchy: `distinctTypesInTree(sq tree [--all])`). So a type present only among closed items won't appear in the picker while show-closed is off.

Low / arguably-correct: filtering to a type whose items are all hidden would show an empty view anyway, so the omission is self-consistent. Pre-change the flat branch always fetched `--all`, so this is a minor behavior narrowing, not a regression to fix. Noting for the record; no change required.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — clearFiltersAndGrouping intentionally leaves show-closed on

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
`clearFilterAndGrouping()` resets `filter` + `groupByType` but deliberately preserves `showClosed` (and `commands.ts` re-syncs only the `groupByType` context key afterward, which is correct since `showClosed` is untouched). This is a defensible design choice — show-closed is a display toggle, not a filter/grouping axis — and the context key stays in sync. Flagging only so the approver confirms the intent: "clear" no longer returns the view to DEFAULT_VIEW_STATE. No defect.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:29:12Z] Paul Reviewer:
  - Per-F verification (all pass):
  - F2 — shared `compareIds` (`Intl.Collator({numeric:true})`) in domain/idOrder.ts is used at both id-sort sites (sortedLeaves, for grouped-bucket leaves and ungrouped leaves). No plain `localeCompare`/`<` on ids remains; the two surviving localeCompare calls sort type *names* (distinctTypes, sortedTypeEntries), which is correct. Test proves REV-48 < REV-447.
  - F3/F4 — group-by-type and show-closed are view/title navigation icons using the native `toggled` context-key pattern (not quick-picks). Context keys (squads.groupByType/squads.showClosed) match between package.json and commands.ts, are seeded on register, and updated on each toggle. show-closed threads `--all` into BOTH fetches: getTree(includeClosed) and getList(allArgs); confirmed `sq tree --all` and `sq list --all` exist.
  - F5 — grouping axis fully removed: GroupKey/OpenClosedState/ClassifiedListItem/classifyListItems all 0 refs (grep-clean). group-by-type is the only grouping; no dead code (sortedEntries renamed to sortedTypeEntries, still used).
  - F6 — createTreeView('squadsTree', { treeDataProvider, showCollapseAll: true }) cleanly replaces registerTreeDataProvider; disposable pushed to subscriptions.
  - F7 — closed items dimmed via ThemeColor('disabledForeground') in iconForNode, mirroring the blocked-icon mechanism; driven by DisplayNode.closed = !is_open set in both treeMapping (tree) and listView (flat). Group/error nodes are closed:false. Priority blocked > closed > normal is reasonable.
  - package.json: no orphan command contributions — filterByState/groupBy dropped from both commands[] and menus; all 5 contributed commands are registered.
- [2026-07-17T15:29:22Z] Paul Reviewer:
  - Judgment call — removal of squads.filterByState (All/Open/Closed quick-pick): I agree it's redundant; keep it removed. With F5 dropping state-grouping and F4+F7 adding the show-closed toggle plus dimming, the states collapse cleanly: toggle-off = open-only (old 'Open'), toggle-on = all-with-closed-dimmed (old 'All' + at-a-glance distinction). The only state the toggle can't reproduce is 'closed-only', a marginal case that would re-introduce a second overlapping open/closed control and muddy exactly the UX Pierre asked to simplify. A closed-only view, if ever wanted, belongs as a future enhancement, not a blocker.
  - Test caveat (acceptable): the view/title toggled wiring and the dimmed-icon render are vscode-native, coverable only via extension-host smoke / manual eyeballing — no unit coverage possible. Domain logic (comparator, closed-field derivation, groupByType boolean, filter shape) is unit-tested and meaningful.
  - Recommended verdict: APPROVE. Gates green: npm run check exit 0, npm test 125/125, npm run test:canary 8/8. Two low observations (F1/F2) are non-blocking notes for the approver, no fix required. Leaving review status for the approver (main loop); not touching TASK-454 status.
<!-- sq:discussion:end -->
