/**
 * Extension entry point: resolves `sq` for the first workspace folder, then wires up the
 * activity-bar work-item tree, the meta/roster view (F12), the records view, the
 * owned item-preview webview, the filter/group/refresh commands, and the `.squads.json` watcher
 * that auto-refreshes all three tree views on an on-disk change (F17).
 */
import * as vscode from 'vscode';

import { registerCommands, registerMetaCommands, registerRecordsCommands } from './commands';
import { SqDiscovery } from './discovery';
import { ItemPreviewManager } from './itemPreviewManager';
import { SquadsMetaTreeDataProvider } from './metaTreeDataProvider';
import { createNodeDiscoveryEnvironment, createNodeSquadDirEnvironment } from './nodeEnvironment';
import { nodeProcessRunner } from './processRunner';
import { SquadsRecordsTreeDataProvider } from './recordsTreeDataProvider';
import { SearchQuickPickController } from './searchQuickPick';
import { watchSquadIndex } from './squadWatcher';
import { SquadsTreeDataProvider } from './treeDataProvider';

function getSquadsConfig(): { sqPath: string; command: readonly string[] } {
  const config = vscode.workspace.getConfiguration('squads');
  return {
    sqPath: config.get<string>('sqPath', ''),
    command: config.get<string[]>('command', []),
  };
}

export function activate(context: vscode.ExtensionContext): void {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
  if (workspaceFolder === undefined) {
    return;
  }
  const root = workspaceFolder.uri.fsPath;

  const env = createNodeDiscoveryEnvironment();
  const notifyError = (message: string): void => {
    void vscode.window.showErrorMessage(message);
  };
  // Shared so a discovered-then-vanished `sq` invalidated by either surface (tree or preview)
  // is re-probed for both, rather than each caching its own stale answer independently.
  const discovery = new SqDiscovery(root, getSquadsConfig, env);
  // Shared with `watchSquadIndex` below: both need the same pure `.squads.toml` walk-up, one to
  // detect the no-squad empty state, the other to know what to watch.
  const squadDirEnv = createNodeSquadDirEnvironment();

  const treeDataProvider = new SquadsTreeDataProvider(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
    squadDirEnv,
  );
  // `createTreeView` (rather than `registerTreeDataProvider`) is what exposes
  // `showCollapseAll` — VS Code's native title-bar collapse-all icon, no custom command needed
  // — and gives us the `TreeView` handle its expand/collapse events are read from below.
  const treeView = vscode.window.createTreeView('squadsTree', {
    treeDataProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(
    treeView,
    // A full-root refresh (e.g. the `.squads.json` watcher below) doesn't preserve
    // expand/collapse state on its own even with a stable `item.id` — the provider has to
    // track it itself and re-render tracked ids `Expanded` (`treeDataProvider.setExpanded`,
    // `ExpansionTracker`).
    treeView.onDidExpandElement((event) => {
      treeDataProvider.setExpanded(event.element.id, true);
    }),
    treeView.onDidCollapseElement((event) => {
      treeDataProvider.setExpanded(event.element.id, false);
    }),
  );

  // The meta/roster view (F12): role/skill/operator under 3 fixed buckets, alongside the work
  // tree as a second collapsible section in the same activity-bar container — not
  // filterable/groupable, so it gets its own minimal provider rather than reusing the work
  // tree's filter/group/show-closed state machine.
  const metaTreeDataProvider = new SquadsMetaTreeDataProvider(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
    squadDirEnv,
  );
  const metaTreeView = vscode.window.createTreeView('squadsMeta', {
    treeDataProvider: metaTreeDataProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(
    metaTreeView,
    metaTreeView.onDidExpandElement((event) => {
      metaTreeDataProvider.setExpanded(event.element.id, true);
    }),
    metaTreeView.onDidCollapseElement((event) => {
      metaTreeDataProvider.setExpanded(event.element.id, false);
    }),
  );

  // The records view: declared `records`-category types (decision/guide, plus any
  // custom records type) under one bucket per type — the complement of the work tree's now-wider
  // reserved-type exclusion, alongside it and the roster view as a third collapsible section in
  // the same activity-bar container. Same minimal shape as the roster view: not
  // filterable/groupable, its own provider.
  const recordsTreeDataProvider = new SquadsRecordsTreeDataProvider(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
    squadDirEnv,
  );
  const recordsTreeView = vscode.window.createTreeView('squadsRecords', {
    treeDataProvider: recordsTreeDataProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(
    recordsTreeView,
    recordsTreeView.onDidExpandElement((event) => {
      recordsTreeDataProvider.setExpanded(event.element.id, true);
    }),
    recordsTreeView.onDidCollapseElement((event) => {
      recordsTreeDataProvider.setExpanded(event.element.id, false);
    }),
  );

  const previewManager = new ItemPreviewManager(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
    context.extensionUri,
  );

  const searchQuickPick = new SearchQuickPickController(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
    previewManager,
  );

  registerCommands(
    context,
    treeDataProvider,
    () => treeDataProvider.getKnownTypes(),
    previewManager,
    searchQuickPick,
  );
  registerMetaCommands(context, metaTreeDataProvider);
  registerRecordsCommands(context, recordsTreeDataProvider);

  void treeDataProvider.refresh();
  void metaTreeDataProvider.refresh();
  void recordsTreeDataProvider.refresh();

  // F17: auto-refresh all three tree views + any open item preview when `.squads.json` changes on
  // disk (an agent runs `sq`, a `git pull`) — no-ops cleanly for a non-local/remote workspace or
  // when no `.squads.toml` is found.
  context.subscriptions.push(
    watchSquadIndex(workspaceFolder, squadDirEnv, {
      onIndexChanged: () => {
        void treeDataProvider.refresh();
        void metaTreeDataProvider.refresh();
        void recordsTreeDataProvider.refresh();
        void previewManager.refreshOpenPreviews();
      },
    }),
  );
}

export function deactivate(): void {
  // Nothing to tear down: the tree/document provider disposables are owned by
  // `context.subscriptions` and torn down by VS Code itself.
}
