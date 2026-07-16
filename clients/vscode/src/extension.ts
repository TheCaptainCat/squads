/**
 * Extension entry point.
 *
 * Foundation only: resolves `sq` for the first workspace folder and reports the outcome.
 * The activity-bar tree, item preview, and filter/group commands are later work built on
 * top of this module (`discovery.ts` / `sqAdapter.ts`).
 */
import * as vscode from 'vscode';

import { describeTriedOrder, resolveSqInvocation } from './discovery';
import { createNodeDiscoveryEnvironment } from './nodeEnvironment';

export function activate(context: vscode.ExtensionContext): void {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (root === undefined) {
    return;
  }

  const config = vscode.workspace.getConfiguration('squads');
  const sqPath = config.get<string>('sqPath', '');
  const command = config.get<string[]>('command', []);
  const env = createNodeDiscoveryEnvironment();

  const result = resolveSqInvocation(root, { sqPath, command }, env);
  if (!result.ok) {
    void vscode.window.showErrorMessage(
      `Squads: no sq invocation found. Tried, in order: ${describeTriedOrder(result.triedOrder)}. ` +
        'Set "squads.sqPath" or "squads.command" to override.',
    );
    return;
  }

  context.subscriptions.push({ dispose: () => undefined });
}

export function deactivate(): void {
  // Nothing to tear down yet.
}
