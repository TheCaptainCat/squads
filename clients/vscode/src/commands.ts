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
 * Every view-title toggle (Work Items' group-by-type and show-closed; the Roster's
 * show-archived and its own group-by-type; Records' group-by-type and show-terminal) registers
 * *two* commands, not one: VS Code never reads a per-item `toggled` property on an extension's
 * `contributes.menus` (only core VS Code's own `ICommandAction` has it), so it's a no-op
 * everywhere. Each pair instead uses opposite `when` clauses plus a distinct icon (current
 * state) and title (the action) per half — the idiom VS Code's own `references-view`
 * call-hierarchy direction toggle uses (`showIncomingCalls`/`showOutgoingCalls`). A toggle's
 * *default* state is independent of this idiom: Work Items' group-by-type defaults off, the
 * Roster's and Records' default on — each pair's icon/`when` still just reflects whichever
 * state is current. The Roster's status filter is a quick-pick, not a toggle, so it has no such
 * pair — its active state instead shows in the view's `.description` (`extension.ts`,
 * `domain/metaFilter.ts::describeMetaFilterState`); Records has no such quick-pick, so it needs
 * no equivalent.
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
const ALL_STATUSES_LABEL = 'All statuses';

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
  syncToggleContext('squads.metaShowArchived', metaProvider.viewState.showArchived);
  syncToggleContext('squads.metaGroupByType', metaProvider.viewState.groupByType);
  syncToggleContext('squads.recordsGroupByType', recordsProvider.viewState.groupByType);
  syncToggleContext('squads.recordsShowTerminal', recordsProvider.viewState.showTerminal);

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

    // Both ids of this pair share this handler — either flips the same `showArchived` state
    // (module doc comment).
    vscode.commands.registerCommand('squads.toggleShowArchived', () => {
      metaProvider.toggleShowArchived();
      syncToggleContext('squads.metaShowArchived', metaProvider.viewState.showArchived);
    }),

    vscode.commands.registerCommand('squads.hideArchived', () => {
      metaProvider.toggleShowArchived();
      syncToggleContext('squads.metaShowArchived', metaProvider.viewState.showArchived);
    }),

    // Same pair shape as Work Items' toggleGroupByType/ungroupByType above, distinct ids
    // because the Roster's own `groupByType` state (default on) is a different piece of state.
    vscode.commands.registerCommand('squads.toggleGroupByTypeMeta', () => {
      metaProvider.toggleGroupByType();
      syncToggleContext('squads.metaGroupByType', metaProvider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.ungroupByTypeMeta', () => {
      metaProvider.toggleGroupByType();
      syncToggleContext('squads.metaGroupByType', metaProvider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.filterMetaByStatus', async () => {
      const picked = await vscode.window.showQuickPick(
        [ALL_STATUSES_LABEL, ...metaProvider.getKnownStatuses()],
        { placeHolder: 'Filter the Roster view by status' },
      );
      if (picked === undefined) {
        return;
      }
      metaProvider.setStatusFilter(picked === ALL_STATUSES_LABEL ? null : picked);
    }),

    // Returns to the Roster's default state — archived hidden, no status filter — same as
    // `clearFiltersAndGrouping` above returns to Work Items' own default (hide-closed) rather
    // than to unfiltered. "Clear" means default, not "show everything": a reader who wants
    // archived entries visible still needs the toggle.
    vscode.commands.registerCommand('squads.clearMetaFilter', () => {
      metaProvider.clearFilter();
      syncToggleContext('squads.metaShowArchived', metaProvider.viewState.showArchived);
      syncToggleContext('squads.metaGroupByType', metaProvider.viewState.groupByType);
    }),

    // Records' group-by-type pair — same shape as the Roster's above.
    vscode.commands.registerCommand('squads.toggleGroupByTypeRecords', () => {
      recordsProvider.toggleGroupByType();
      syncToggleContext('squads.recordsGroupByType', recordsProvider.viewState.groupByType);
    }),

    vscode.commands.registerCommand('squads.ungroupByTypeRecords', () => {
      recordsProvider.toggleGroupByType();
      syncToggleContext('squads.recordsGroupByType', recordsProvider.viewState.groupByType);
    }),

    // Records' terminal-hiding pair — the Records equivalent of the Roster's
    // toggleShowArchived/hideArchived (module doc comment); "terminal" rather than "closed"
    // per the wording call at the command-title level, "archived" doesn't fit either.
    vscode.commands.registerCommand('squads.toggleShowTerminal', () => {
      recordsProvider.toggleShowTerminal();
      syncToggleContext('squads.recordsShowTerminal', recordsProvider.viewState.showTerminal);
    }),

    vscode.commands.registerCommand('squads.hideTerminal', () => {
      recordsProvider.toggleShowTerminal();
      syncToggleContext('squads.recordsShowTerminal', recordsProvider.viewState.showTerminal);
    }),

    // Returns Records to its default — grouped, terminal hidden — not to show-everything; same
    // asymmetry as squads.clearMetaFilter above, restated here because it's Records' own call site.
    vscode.commands.registerCommand('squads.clearRecordsFilter', () => {
      recordsProvider.clearFilter();
      syncToggleContext('squads.recordsGroupByType', recordsProvider.viewState.groupByType);
      syncToggleContext('squads.recordsShowTerminal', recordsProvider.viewState.showTerminal);
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
