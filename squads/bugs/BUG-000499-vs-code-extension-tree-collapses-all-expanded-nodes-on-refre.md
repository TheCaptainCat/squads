---
id: BUG-499
sequence_id: 499
type: bug
title: VS Code extension tree collapses all expanded nodes on refresh
status: Verified
author: manager
created_at: '2026-07-20T09:50:38Z'
updated_at: '2026-07-20T12:23:39Z'
---
<!-- sq:body -->
Symptom: in the VS Code extension, both tree views (squadsTree + squadsMeta) reset and fold every expanded node on refresh. The .squads.json watcher (F17) auto-refreshes often, so any expanded subtree collapses constantly during normal work — the tree won't stay open.

Ground truth: treeItemRendering.toTreeItem already sets a stable item.id = node.id and collapsibleState is only ever Collapsed/None (never Expanded). Refresh fires onDidChangeTreeData (full/root refresh) from the providers; the watcher calls provider.refresh() on .squads.json change (extension.ts ~95, squadWatcher.ts). Despite the stable id, expansion is not preserved.

Leads to investigate: (1) whether node.id is actually stable across a refresh (grouping/filter/child-count shifts could change it); (2) whether the provider must track expansion via TreeView.onDidExpandElement/onDidCollapseElement and render previously-expanded nodes with TreeItemCollapsibleState.Expanded on refresh; (3) whether the full-root emit pattern is the culprit vs a scoped emit. Fix so expansion survives auto-refresh. Files: clients/vscode/src/treeItemRendering.ts, treeDataProvider.ts, metaTreeDataProvider.ts, extension.ts, squadWatcher.ts.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-20T09:50:50Z] Pierre Chat:
  - Reported live: the extension tree resets and folds at refresh.
- [2026-07-20T09:58:38Z] Operator:
  - @manager Root cause: node.id is already stable everywhere (item ids, group:type:* ids, meta:* ids), so that's not it. Real cause: vscode's TreeView does NOT auto-preserve expand/collapse state across a full-root onDidChangeTreeData(undefined) refresh (which is exactly what the .squads.json watcher fires) — item.id alone isn't enough; the provider must track expansion itself.
  - Fix: added domain/expansionTracker.ts (ExpansionTracker, vscode-free) + domain/displayNode.ts::collectNodeIds. Both providers (treeDataProvider.ts, metaTreeDataProvider.ts) own one tracker, expose setExpanded(id, bool), and getTreeItem now renders toTreeItem(node, id => tracker.isExpanded(id)) — a node with children renders Expanded if tracked, else Collapsed as before (leaves still None). refresh() prunes tracked ids against collectNodeIds(roots) so deleted items don't linger. extension.ts wires each TreeView's onDidExpandElement/onDidCollapseElement to the matching provider's setExpanded — showCollapseAll untouched (still createTreeView, unrelated to this).
  - Verified: npm run check (tsc+eslint+prettier) clean; npm test 263/263 passing incl. new expansionTracker.test.ts (tracking/prune semantics) and collectNodeIds cases added to displayNode.test.ts. Also ran npm run test:e2e locally (exit 0) — extension activated, both views' focus commands and openItemPreview ran clean, confirming the TreeView + event wiring registers without throwing. Manual expand-then-auto-refresh persistence itself is a live-interaction behavior I verified by reasoning about the documented onDidExpandElement/onDidCollapseElement + getTreeItem contract, not by scripted UI interaction.
- [2026-07-20T09:58:53Z] Ada Typescript:
  - (re-posting under my own identity — previous comment was mis-attributed to operator by default; content stands as authored by me, Ada Typescript)
- [2026-07-20T12:23:38Z] Pierre Chat:
  - Verified live in the Extension Development Host: tree nodes stay expanded across refresh.
<!-- sq:discussion:end -->
