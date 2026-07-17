/**
 * View-title/palette commands: refresh, filter by type/state, group by, clear, and the
 * tree-node-selection command that opens the owned item-preview webview.
 */
import * as vscode from 'vscode';

import type { GroupKey, ListFilter, OpenClosedState } from './domain/listView';
import type { ItemPreviewManager } from './itemPreviewManager';
import type { SquadsTreeDataProvider } from './treeDataProvider';

const ALL_TYPES_LABEL = 'All types';

const GROUP_BY_OPTIONS: readonly { readonly label: string; readonly value: readonly GroupKey[] }[] =
  [
    { label: 'None', value: [] },
    { label: 'Type', value: ['type'] },
    { label: 'Open/Closed', value: ['state'] },
    { label: 'Type, then Open/Closed', value: ['type', 'state'] },
    { label: 'Open/Closed, then Type', value: ['state', 'type'] },
  ];

const STATE_FILTER_OPTIONS: readonly {
  readonly label: string;
  readonly value: OpenClosedState | null;
}[] = [
  { label: 'All', value: null },
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

function withType(filter: ListFilter, type: string | null): ListFilter {
  return { type, state: filter.state };
}

function withState(filter: ListFilter, state: OpenClosedState | null): ListFilter {
  return { type: filter.type, state };
}

export function registerCommands(
  context: vscode.ExtensionContext,
  provider: SquadsTreeDataProvider,
  knownTypes: () => readonly string[],
  previewManager: ItemPreviewManager,
): void {
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
      provider.setFilter(
        withType(provider.viewState.filter, picked === ALL_TYPES_LABEL ? null : picked),
      );
    }),

    vscode.commands.registerCommand('squads.filterByState', async () => {
      const picked = await vscode.window.showQuickPick(
        STATE_FILTER_OPTIONS.map((option) => option.label),
        { placeHolder: 'Filter the squads tree by open/closed state' },
      );
      const option = STATE_FILTER_OPTIONS.find((candidate) => candidate.label === picked);
      if (option === undefined) {
        return;
      }
      provider.setFilter(withState(provider.viewState.filter, option.value));
    }),

    vscode.commands.registerCommand('squads.groupBy', async () => {
      const picked = await vscode.window.showQuickPick(
        GROUP_BY_OPTIONS.map((option) => option.label),
        { placeHolder: 'Group the squads tree' },
      );
      const option = GROUP_BY_OPTIONS.find((candidate) => candidate.label === picked);
      if (option === undefined) {
        return;
      }
      provider.setGroupBy(option.value);
    }),

    vscode.commands.registerCommand('squads.clearFiltersAndGrouping', () => {
      provider.clearFilterAndGrouping();
    }),

    vscode.commands.registerCommand('squads.openItemPreview', async (itemId: unknown) => {
      if (typeof itemId !== 'string') {
        return;
      }
      await previewManager.openFromTree(itemId);
    }),
  );
}
