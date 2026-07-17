/**
 * Extension entry point: resolves `sq` for the first workspace folder, then wires up the
 * activity-bar tree, the `squads:` read-only preview, and the filter/group/refresh commands.
 */
import * as vscode from 'vscode';

import { registerCommands } from './commands';
import { SqDiscovery } from './discovery';
import { SQUADS_SCHEME } from './domain/showPreview';
import { createNodeDiscoveryEnvironment } from './nodeEnvironment';
import { nodeProcessRunner } from './processRunner';
import { SquadsShowDocumentProvider } from './showDocumentProvider';
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
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('squadsTree', treeDataProvider),
  );

  const showDocumentProvider = new SquadsShowDocumentProvider(
    nodeProcessRunner,
    discovery,
    root,
    notifyError,
  );
  context.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider(SQUADS_SCHEME, showDocumentProvider),
  );

  registerCommands(context, treeDataProvider, () => treeDataProvider.getKnownTypes());

  void treeDataProvider.refresh();
}

export function deactivate(): void {
  // Nothing to tear down: the tree/document provider disposables are owned by
  // `context.subscriptions` and torn down by VS Code itself.
}
