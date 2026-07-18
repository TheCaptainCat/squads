/**
 * The activity-bar `TreeDataProvider`: renders the squad hierarchy by default, and switches to
 * a flat/filtered/grouped view once a filter or grouping is set. Thin glue only: it resolves
 * `sq`, calls the adapter, and turns the outcome into `vscode.TreeItem`s from
 * the vscode-free `DisplayNode`s built in `domain/`. That mapping is what's unit-tested; this
 * module's vscode wiring is exercised by reading + the deferred extension-host smoke test.
 */
import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import {
  buildBadgeVocabulary,
  buildFieldBindings,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
} from './domain/badgeCatalog';
import { type DisplayNode, errorDisplayNode, type TypeIconOverrides } from './domain/displayNode';
import {
  buildFilteredGroupedView,
  distinctTypes,
  type ListFilter,
  NO_FILTER,
} from './domain/listView';
import { buildStatusRoleMap, NO_STATUS_ROLES, type StatusRoleMap } from './domain/statusRole';
import { distinctTypesInTree, treeNodesToDisplay } from './domain/treeMapping';
import { buildTypeOrderMap, NO_TYPE_ORDER, type TypeOrderMap } from './domain/typeOrder';
import type { ProcessRunner } from './processRunner';
import {
  describeFailure,
  getCollectionsCatalog,
  getList,
  getStatusesCatalog,
  getTree,
  getTypeCatalog,
  type SqOutcome,
} from './sqAdapter';
import { toTreeItem } from './treeItemRendering';
import type { SqCollectionCatalogEntry, SqStatusCatalogEntry, SqTypeCatalogEntry } from './types';

export interface ViewState {
  readonly filter: ListFilter;
  /** Group-by-type view-title toggle (a direct boolean toggle, not a quick-pick selection —
   * open/closed is no longer a grouping axis alongside it). */
  readonly groupByType: boolean;
  /** Show-closed view-title toggle: whether the current fetch includes closed/terminal items,
   * in both the hierarchy tree and the flat/grouped view. */
  readonly showClosed: boolean;
}

export const DEFAULT_VIEW_STATE: ViewState = {
  filter: NO_FILTER,
  groupByType: false,
  showClosed: false,
};

export function isFlatViewActive(state: ViewState): boolean {
  return state.filter.type !== null || state.groupByType;
}

/** Degrade a failed/unreachable type-catalog fetch to `NO_TYPE_ORDER` (F1's graceful fallback)
 * rather than surfacing it as a tree-breaking error — group-by-type and the type-filter
 * quick-pick still work, just alphabetically, until the catalog is reachable again. */
function orderMapFrom(outcome: SqOutcome<readonly SqTypeCatalogEntry[]>): TypeOrderMap {
  return outcome.kind === 'success' ? buildTypeOrderMap(outcome.data) : NO_TYPE_ORDER;
}

/** Same graceful-degrade shape as `orderMapFrom`, for the type catalog's field->collection
 * bindings (F19): a failed fetch falls back to raw-code tooltip badges rather
 * than a broken view. */
function fieldBindingsFrom(outcome: SqOutcome<readonly SqTypeCatalogEntry[]>) {
  return outcome.kind === 'success' ? buildFieldBindings(outcome.data) : NO_FIELD_BINDINGS;
}

/** Same graceful-degrade shape as `orderMapFrom`, for the collections catalog's badge
 * vocabulary (F19): a failed fetch falls back to raw-code tooltip badges. */
function badgeVocabularyFrom(outcome: SqOutcome<readonly SqCollectionCatalogEntry[]>) {
  return outcome.kind === 'success' ? buildBadgeVocabulary(outcome.data) : NO_BADGE_VOCABULARY;
}

/** Same graceful-degrade shape as `orderMapFrom`, for the statuses catalog's status->role join
 * (F26): a failed fetch disables the active-green highlight rather than breaking the view. */
function statusRolesFrom(outcome: SqOutcome<readonly SqStatusCatalogEntry[]>): StatusRoleMap {
  return outcome.kind === 'success' ? buildStatusRoleMap(outcome.data) : NO_STATUS_ROLES;
}

/** The `squads.typeIcons` setting (F21): a user type-name -> codicon-id map, layered over the
 * bundled `ICON_BY_TYPE` defaults in `domain/displayNode.ts::iconForType`. Read fresh on every
 * refresh so an edit to the setting takes effect on the next refresh, same as `getSquadsConfig`
 * in `extension.ts`. */
function getTypeIconOverrides(): TypeIconOverrides {
  return vscode.workspace.getConfiguration('squads').get<Record<string, string>>('typeIcons', {});
}

export class SquadsTreeDataProvider implements vscode.TreeDataProvider<DisplayNode> {
  private readonly changeEmitter = new vscode.EventEmitter<DisplayNode | undefined>();
  readonly onDidChangeTreeData = this.changeEmitter.event;

  private roots: DisplayNode[] = [];
  private state: ViewState = DEFAULT_VIEW_STATE;
  private knownItemTypes: readonly string[] = [];

  constructor(
    private readonly runner: ProcessRunner,
    private readonly discovery: SqDiscovery,
    private readonly workspaceRoot: string,
    private readonly notifyError: (message: string) => void,
  ) {}

  getTreeItem(node: DisplayNode): vscode.TreeItem {
    return toTreeItem(node);
  }

  getChildren(node?: DisplayNode): DisplayNode[] {
    return node === undefined ? this.roots : [...node.children];
  }

  get viewState(): ViewState {
    return this.state;
  }

  /** Distinct item types seen in the last successful fetch — feeds the "filter by type"
   * quick-pick without the client hardcoding a type catalog. */
  getKnownTypes(): readonly string[] {
    return this.knownItemTypes;
  }

  setFilter(filter: ListFilter): void {
    this.state = { ...this.state, filter };
    void this.refresh();
  }

  /** Flips the group-by-type view-title toggle (F3). */
  toggleGroupByType(): void {
    this.state = { ...this.state, groupByType: !this.state.groupByType };
    void this.refresh();
  }

  /** Flips the show-closed view-title toggle (F4): whether the next fetch includes
   * closed/terminal items, in either the hierarchy tree or the flat/grouped view. */
  toggleShowClosed(): void {
    this.state = { ...this.state, showClosed: !this.state.showClosed };
    void this.refresh();
  }

  clearFilterAndGrouping(): void {
    this.state = { ...this.state, filter: NO_FILTER, groupByType: false };
    void this.refresh();
  }

  async refresh(): Promise<void> {
    const resolution = this.discovery.resolve();
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.fail(message);
      return;
    }
    const { invocation } = resolution;
    const allArgs = this.state.showClosed ? ['--all'] : [];
    // Fetched alongside the tree/list payload below (three extra spawns per refresh, cheap
    // next to the ones already there) rather than cached — a project's spec can change between
    // refreshes. A failure in any degrades gracefully (F1/F19/F26): `orderMapFrom` /
    // `fieldBindingsFrom` / `badgeVocabularyFrom` / `statusRolesFrom` fall back to plain-name
    // sort / raw-code tooltip badges / no active-green highlight instead of breaking the view.
    const catalogPromise = getTypeCatalog(this.runner, invocation, this.workspaceRoot);
    const collectionsPromise = getCollectionsCatalog(this.runner, invocation, this.workspaceRoot);
    const statusesPromise = getStatusesCatalog(this.runner, invocation, this.workspaceRoot);
    const iconOverrides = getTypeIconOverrides();

    if (isFlatViewActive(this.state)) {
      // `--all` (only when the show-closed toggle is on) carries closed items alongside open
      // ones, each with its own `is_open` flag, so one fetch is enough either way.
      const [outcome, catalogOutcome, collectionsOutcome, statusesOutcome] = await Promise.all([
        getList(this.runner, invocation, this.workspaceRoot, allArgs),
        catalogPromise,
        collectionsPromise,
        statusesPromise,
      ]);
      if (outcome.kind !== 'success') {
        this.failFrom(outcome);
        return;
      }
      const orderMap = orderMapFrom(catalogOutcome);
      this.roots = buildFilteredGroupedView(
        outcome.data,
        this.state.filter,
        this.state.groupByType,
        orderMap,
        iconOverrides,
        fieldBindingsFrom(catalogOutcome),
        badgeVocabularyFrom(collectionsOutcome),
        statusRolesFrom(statusesOutcome),
      );
      this.knownItemTypes = distinctTypes(outcome.data, orderMap);
      this.changeEmitter.fire(undefined);
      return;
    }

    // The tree payload now carries title + is_open on every node, so the hierarchy render is a
    // single `sq tree --json` spawn — no second `sq list` fetch for titles or known types.
    const [treeOutcome, catalogOutcome, collectionsOutcome, statusesOutcome] = await Promise.all([
      getTree(this.runner, invocation, this.workspaceRoot, undefined, this.state.showClosed),
      catalogPromise,
      collectionsPromise,
      statusesPromise,
    ]);
    if (treeOutcome.kind !== 'success') {
      this.failFrom(treeOutcome);
      return;
    }
    this.roots = treeNodesToDisplay(
      treeOutcome.data,
      iconOverrides,
      fieldBindingsFrom(catalogOutcome),
      badgeVocabularyFrom(collectionsOutcome),
      statusRolesFrom(statusesOutcome),
    );
    this.knownItemTypes = distinctTypesInTree(treeOutcome.data, orderMapFrom(catalogOutcome));
    this.changeEmitter.fire(undefined);
  }

  private failFrom(outcome: Exclude<SqOutcome<unknown>, { kind: 'success' }>): void {
    if (outcome.kind === 'spawn-error') {
      // The resolved invocation no longer works (e.g. the binary vanished) — drop the cache so
      // the next refresh re-probes discovery instead of retrying the same stale answer.
      this.discovery.invalidate();
    }
    this.fail(describeFailure(outcome));
  }

  private fail(message: string): void {
    this.roots = [errorDisplayNode(message)];
    this.notifyError(`Squads: ${message}`);
    this.changeEmitter.fire(undefined);
  }
}
