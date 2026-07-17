/**
 * Extension entry point: resolves `sq` for the first workspace folder, then wires up the
 * activity-bar work-item tree, the meta/roster view (F12), the owned item-preview webview, and
 * the filter/group/refresh commands.
 */
import * as vscode from 'vscode';

import { registerCommands, registerMetaCommands } from './commands';
import { SqDiscovery } from './discovery';
import { ItemPreviewManager } from './itemPreviewManager';
import { SquadsMetaTreeDataProvider } from './metaTreeDataProvider';
import { createNodeDiscoveryEnvironment } from './nodeEnvironment';
import { nodeProcessRunner } from './processRunner';
import { SquadsTreeDataProvider } from './treeDataProvider';

function getSquadsConfig(): { sqPath: string; command: readonly string[] } {
  const config = vscode.workspace.getConfiguration('squads');
  return {
    sqPath: config.get<string>('sqPath', ''),
    command: config.get<string[]>('command', []),
  };
}

export function activate(context: vscode.ExtensionContext): void {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (root === undefined) {
    return;
  }

  const env = createNodeDiscoveryEnvironment();
  const notifyError = (message: string): void => {
    void vscode.window.showErrorMessage(message);
  };
  // Shared so a discovered-then-vanished `sq` invalidated by either surface (tree or preview)
  // is re-probed for both, rather than each caching its own stale answer independently.
  const discovery = new SqDiscovery(root, getSquadsConfig, env);

  const treeDataProvider = new SquadsTreeDataProvider(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
  );
  // `createTreeView` (rather than `registerTreeDataProvider`) is what exposes
  // `showCollapseAll` — VS Code's native title-bar collapse-all icon, no custom command needed.
  context.subscriptions.push(
    vscode.window.createTreeView('squadsTree', { treeDataProvider, showCollapseAll: true }),
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
  );
  context.subscriptions.push(
    vscode.window.createTreeView('squadsMeta', {
      treeDataProvider: metaTreeDataProvider,
      showCollapseAll: true,
    }),
  );

  const previewManager = new ItemPreviewManager(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
    context.extensionUri,
  );

  registerCommands(
    context,
    treeDataProvider,
    () => treeDataProvider.getKnownTypes(),
    previewManager,
  );
  registerMetaCommands(context, metaTreeDataProvider);

  void treeDataProvider.refresh();
  void metaTreeDataProvider.refresh();
}

export function deactivate(): void {
  // Nothing to tear down: the tree/document provider disposables are owned by
  // `context.subscriptions` and torn down by VS Code itself.
}
