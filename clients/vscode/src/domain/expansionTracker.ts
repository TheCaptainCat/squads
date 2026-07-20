/**
 * Tracks which `DisplayNode` ids are currently expanded in a tree view, across refreshes.
 *
 * `TreeItem.id` gives vscode a stable *identity* for a node, but a provider that fires
 * `onDidChangeTreeData` for the whole tree (a root/`undefined` refresh — exactly what an
 * auto-refresh on an on-disk change does) does not get expand/collapse state preserved for
 * free just because the ids line up: the collapsible state rendered by `getTreeItem` on the
 * next pass is what the view actually shows. So the provider has to remember it itself: record
 * every `onDidExpandElement`/`onDidCollapseElement` here, then render a tracked id with
 * `vscode.TreeItemCollapsibleState.Expanded` instead of the default `Collapsed` next time.
 *
 * Kept vscode-free (plain ids in, plain ids out) so the tracking logic itself is unit-testable
 * without an extension host.
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
