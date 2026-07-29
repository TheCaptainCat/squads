/**
 * View-title/palette commands, including the preview panel's back/forward navigation commands —
 * a secondary path to the primary in-content toolbar rendered inside the preview HTML itself (see
 * `itemPreviewManager.ts`'s module doc comment for why), reachable via the `alt+left`/`alt+right`
 * keybindings and the Command Palette.
 *
 * `REFRESH_ALL_COMMAND` (`squads.refreshAll`) is the *one* definition of "refresh everything": all
 * three trees plus every open preview panel, orchestrated by the pure, unit-tested
 * `domain/refreshAll.ts` rather than inline here. `package.json`'s three `view/title` entries all
 * point at this single id, and `extension.ts`'s `.squads.json` watcher and the in-content preview
 * refresh button (`itemPreviewManager.ts`'s message handler) both invoke it by id
 * (`commandIds.ts`) rather than keeping their own copy of what "refresh everything" means.
 *
 * The two view-title toggles (group-by-type, show-closed) each register *two* commands, not one:
 * VS Code never reads a per-item `toggled` property on an extension's `contributes.menus` (only
 * core VS Code's own `ICommandAction` has it), so it's a no-op everywhere. Each pair instead uses
 * opposite `when` clauses plus a distinct icon (current state) and title (the action) per half —
 * the idiom VS Code's own `references-view` call-hierarchy direction toggle uses
 * (`showIncomingCalls`/`showOutgoingCalls`).
 */
import * as vscode from 'vscode';

import { REFRESH_ALL_COMMAND } from './commandIds';
import { refreshAll } from './domain/refreshAll';
import type { ItemPreviewManager } from './itemPreviewManager';
import type { SquadsMetaTreeDataProvider } from './metaTreeDataProvider';
import type { SquadsRecordsTreeDataProvider } from './recordsTreeDataProvider';
import type { SearchQuickPickController } from './searchQuickPick';
import type { SquadsTreeDataProvider } from './treeDataProvider';

const ALL_TYPES_LABEL = 'All types';

/** Mirrors a toggle's current state into a context key so the title-bar shows the right half of
 * its icon/title pair — see the module doc comment for why there are two commands per toggle. */
function syncToggleContext(key: string, value: boolean): void {
  void vscode.commands.executeCommand('setContext', key, value);
}

export function registerCommands(
  context: vscode.ExtensionContext,
  provider: SquadsTreeDataProvider,
  knownTypes: () => readonly string[],
  previewManager: ItemPreviewManager,
  searchQuickPick: SearchQuickPickController,
  metaProvider: SquadsMetaTreeDataProvider,
  recordsProvider: SquadsRecordsTreeDataProvider,
): void {
  // Which half of each icon-swapped title-bar pair shows is selected by these context keys; seed
  // them from the provider's initial state so a fresh window starts in sync.
  syncToggleContext('squads.groupByType', provider.viewState.groupByType);
  syncToggleContext('squads.showClosed', provider.viewState.showClosed);

  context.subscriptions.push(
    // The one refresh command every entry point routes through — see the module doc comment.
    vscode.commands.registerCommand(REFRESH_ALL_COMMAND, async () => {
      await refreshAll(provider, metaProvider, recordsProvider, previewManager);
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

    // Both ids of a pair (module doc comment) share this handler — either flips the same state.
    vscode.commands.registerCommand('squads.toggleGroupByType', () => {
      provider.toggleGroupByType();
      syncToggleContext('squads.groupByType', provider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.ungroupByType', () => {
      provider.toggleGroupByType();
      syncToggleContext('squads.groupByType', provider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.toggleShowClosed', () => {
      provider.toggleShowClosed();
      syncToggleContext('squads.showClosed', provider.viewState.showClosed);
    }),

    vscode.commands.registerCommand('squads.hideClosed', () => {
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

    vscode.commands.registerCommand('squads.previewBack', async () => {
      await previewManager.goBack();
    }),

    vscode.commands.registerCommand('squads.previewForward', async () => {
      await previewManager.goForward();
    }),

    vscode.commands.registerCommand('squads.search', () => {
      searchQuickPick.open();
    }),
  );
}
