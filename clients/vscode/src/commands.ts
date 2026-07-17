/**
 * View-title/palette commands: refresh, filter by type, the group-by-type and show-closed
 * view-title toggles, clear, the tree-node-selection command that opens the owned item-preview
 * webview, and the view-title button that opens the workflow cheatsheet in its own owned panel.
 */
import * as vscode from 'vscode';

import type { ItemPreviewManager } from './itemPreviewManager';
import type { SquadsMetaTreeDataProvider } from './metaTreeDataProvider';
import type { SquadsTreeDataProvider } from './treeDataProvider';

const ALL_TYPES_LABEL = 'All types';

/** Mirrors a toggle's current state into its `package.json` `view/title` `toggled` context key
 * so the title-bar icon renders pressed/unpressed in sync with the provider's own state. */
function syncToggleContext(key: string, value: boolean): void {
  void vscode.commands.executeCommand('setContext', key, value);
}

export function registerCommands(
  context: vscode.ExtensionContext,
  provider: SquadsTreeDataProvider,
  knownTypes: () => readonly string[],
  previewManager: ItemPreviewManager,
): void {
  // The title-bar toggle icons render pressed/unpressed from these context keys; seed them from
  // the provider's initial state so a fresh window starts in sync.
  syncToggleContext('squads.groupByType', provider.viewState.groupByType);
  syncToggleContext('squads.showClosed', provider.viewState.showClosed);

  context.subscriptions.push(
    vscode.commands.registerCommand('squads.refreshTree', () => {
      void provider.refresh();
    }),

    vscode.commands.registerCommand('squads.filterByType', async () => {
      const picked = await vscode.window.showQuickPick([ALL_TYPES_LABEL, ...knownTypes()], {
        placeHolder: 'Filter the squads tree by item type',
      });
      if (picked === undefined) {
        return;
      }
      provider.setFilter({ type: picked === ALL_TYPES_LABEL ? null : picked });
    }),

    vscode.commands.registerCommand('squads.toggleGroupByType', () => {
      provider.toggleGroupByType();
      syncToggleContext('squads.groupByType', provider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.toggleShowClosed', () => {
      provider.toggleShowClosed();
      syncToggleContext('squads.showClosed', provider.viewState.showClosed);
    }),

    vscode.commands.registerCommand('squads.clearFiltersAndGrouping', () => {
      provider.clearFilterAndGrouping();
      syncToggleContext('squads.groupByType', provider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.openItemPreview', async (itemId: unknown) => {
      if (typeof itemId !== 'string') {
        return;
      }
      await previewManager.openFromTree(itemId);
    }),

    vscode.commands.registerCommand('squads.openWorkflow', async () => {
      await previewManager.openWorkflow();
    }),
  );
}

/** The meta/roster view (F12) has no filter/group/show-closed state — just its own refresh. */
export function registerMetaCommands(
  context: vscode.ExtensionContext,
  provider: SquadsMetaTreeDataProvider,
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('squads.refreshMeta', () => {
      void provider.refresh();
    }),
  );
}
