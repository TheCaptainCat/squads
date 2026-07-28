/**
 * Tracks which ids are currently "expanded" — in either of two senses, both using this exact
 * same class — across refreshes.
 *
 * The original sense: which `DisplayNode` ids are expanded in a tree view. `TreeItem.id` gives
 * vscode a stable *identity* for a node, but a provider that fires `onDidChangeTreeData` for the
 * whole tree (a root/`undefined` refresh — exactly what an auto-refresh on an on-disk change
 * does) does not get expand/collapse state preserved for free just because the ids line up: the
 * collapsible state rendered by `getTreeItem` on the next pass is what the view actually shows.
 * So the provider has to remember it itself: record every
 * `onDidExpandElement`/`onDidCollapseElement` here, then render a tracked id with
 * `vscode.TreeItemCollapsibleState.Expanded` instead of the default `Collapsed` next time.
 *
 * The second sense: which `<details>` folds are open in the item-preview webview
 * (`itemPreviewManager.ts`, one tracker per open panel) — the same shape problem (a same-item
 * refresh rebuilds the sub-entities/graph HTML from scratch, discarding open/closed state unless
 * something remembers it) solved the same way: a `ToggleFoldMessage`
 * (`domain/previewMessages.ts`) reported from the webview stands in for
 * `onDidExpandElement`/`onDidCollapseElement`, and the next render stamps `open` back onto a
 * tracked id instead of introducing a second, drifting tracker.
 *
 * Kept vscode-free (plain ids in, plain ids out) so the tracking logic itself is unit-testable
 * without an extension host, in either use.
 */
export class ExpansionTracker {
  private readonly expandedIds = new Set<string>();

  isExpanded(id: string): boolean {
    return this.expandedIds.has(id);
  }

  setExpanded(id: string, expanded: boolean): void {
    if (expanded) {
      this.expandedIds.add(id);
    } else {
      this.expandedIds.delete(id);
    }
  }

  /** Forgets tracked ids absent from `currentIds` (e.g. a deleted item, an emptied-out group)
   * so the set can't grow without bound over a long session. Call after every refresh with the
   * freshly fetched tree's ids (`collectNodeIds`). */
  prune(currentIds: ReadonlySet<string>): void {
    for (const id of this.expandedIds) {
      if (!currentIds.has(id)) {
        this.expandedIds.delete(id);
      }
    }
  }
}
