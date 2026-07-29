/**
 * The third activity-bar view's `TreeDataProvider` ("Records"): renders one bucket
 * per declared `records`-category type (decision/guide, plus any custom records type), built by
 * the vscode-free `domain/recordsView.ts`, or a flat id-sorted list when `groupByType` is off.
 * Same shape as `metaTreeDataProvider.ts`: `RecordsViewState` (`domain/recordsFilter.ts`) is a
 * deliberately small state machine (group-by-type + hide-terminal, no status filter — Records
 * has no equivalent request for one yet). One `sq list --json --all` fetch (`--all` so a record
 * that ever reaches a settled/hidden status still shows up when `showTerminal` is toggled on,
 * with no second round trip) feeds every bucket. Thin glue only: this module's vscode wiring is
 * exercised by the extension-host smoke test, `buildRecordsView`/`domain/recordsFilter.ts` are
 * what's unit-tested.
 */
import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import {
  buildBadgeVocabulary,
  buildFieldBindings,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
} from './domain/badgeCatalog';
import {
  collectNodeIds,
  type DisplayNode,
  emptyStateDisplayNode,
  errorDisplayNode,
} from './domain/displayNode';
import { ExpansionTracker } from './domain/expansionTracker';
import { DEFAULT_RECORDS_VIEW_STATE, type RecordsViewState } from './domain/recordsFilter';
import { buildRecordsView } from './domain/recordsView';
import { resolveSquadDir, type SquadDirEnvironment } from './domain/squadDir';
import {
  buildRoleCatalogMap,
  buildStatusRoleMap,
  NO_ROLES,
  NO_STATUS_ROLES,
} from './domain/statusRole';
import { buildCategoryMap, NO_CATEGORIES } from './domain/typeCategory';
import { buildTypeLabelMap, NO_LABELS } from './domain/typeLabels';
import { buildTypeOrderMap, NO_TYPE_ORDER } from './domain/typeOrder';
import type { ProcessRunner } from './processRunner';
import {
  describeFailure,
  getCollectionsCatalog,
  getList,
  getRolesCatalog,
  getStatusesCatalog,
  getTypeCatalog,
  type SqOutcome,
} from './sqAdapter';
import { getTypeIconOverrides } from './treeDataProvider';
import { toTreeItem } from './treeItemRendering';

export class SquadsRecordsTreeDataProvider implements vscode.TreeDataProvider<DisplayNode> {
  private readonly changeEmitter = new vscode.EventEmitter<DisplayNode | undefined>();
  readonly onDidChangeTreeData = this.changeEmitter.event;

  private roots: DisplayNode[] = [];
  // See `treeDataProvider.ts`'s matching field: a full-root refresh (this view's only kind) does
  // not preserve expand/collapse state on its own, even with a stable `item.id`.
  private readonly expansion = new ExpansionTracker();
  private state: RecordsViewState = DEFAULT_RECORDS_VIEW_STATE;

  constructor(
    private readonly runner: ProcessRunner,
    private readonly discovery: SqDiscovery,
    private readonly workspaceRoot: string,
    private readonly notifyError: (message: string) => void,
    private readonly squadDirEnv: SquadDirEnvironment,
  ) {}

  getTreeItem(node: DisplayNode): vscode.TreeItem {
    return toTreeItem(node, (id) => this.expansion.isExpanded(id));
  }

  /** Wired to the owning `TreeView`'s expand/collapse events in `extension.ts`. */
  setExpanded(id: string, expanded: boolean): void {
    this.expansion.setExpanded(id, expanded);
  }

  getChildren(node?: DisplayNode): DisplayNode[] {
    return node === undefined ? this.roots : [...node.children];
  }

  get viewState(): RecordsViewState {
    return this.state;
  }

  toggleGroupByType(): void {
    this.state = { ...this.state, groupByType: !this.state.groupByType };
    void this.refresh();
  }

  toggleShowTerminal(): void {
    this.state = { ...this.state, showTerminal: !this.state.showTerminal };
    void this.refresh();
  }

  clearFilter(): void {
    this.state = DEFAULT_RECORDS_VIEW_STATE;
    void this.refresh();
  }

  async refresh(): Promise<void> {
    // Same no-squad short-circuit as `treeDataProvider.ts` — see its comment.
    if (resolveSquadDir(this.workspaceRoot, this.squadDirEnv) === undefined) {
      this.roots = [emptyStateDisplayNode('No squad detected here')];
      this.changeEmitter.fire(undefined);
      return;
    }
    const resolution = this.discovery.resolve();
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.fail(message);
      return;
    }
    const { invocation } = resolution;
    // Same catalogs the work tree fetches (the badge and status-role catalogs), plus the type catalog's `category`
    //  that decides which buckets exist at all. A failed fetch degrades to raw-code
    // badge text / no colour highlight / no buckets rather than breaking the view.
    const [outcome, catalogOutcome, collectionsOutcome, statusesOutcome, rolesOutcome] =
      await Promise.all([
        getList(this.runner, invocation, this.workspaceRoot, ['--all']),
        getTypeCatalog(this.runner, invocation, this.workspaceRoot),
        getCollectionsCatalog(this.runner, invocation, this.workspaceRoot),
        getStatusesCatalog(this.runner, invocation, this.workspaceRoot),
        getRolesCatalog(this.runner, invocation, this.workspaceRoot),
      ]);
    if (outcome.kind !== 'success') {
      this.failFrom(outcome);
      return;
    }
    const categoryMap =
      catalogOutcome.kind === 'success' ? buildCategoryMap(catalogOutcome.data) : NO_CATEGORIES;
    const orderMap =
      catalogOutcome.kind === 'success' ? buildTypeOrderMap(catalogOutcome.data) : NO_TYPE_ORDER;
    const labelMap =
      catalogOutcome.kind === 'success' ? buildTypeLabelMap(catalogOutcome.data) : NO_LABELS;
    const fieldBindings =
      catalogOutcome.kind === 'success'
        ? buildFieldBindings(catalogOutcome.data)
        : NO_FIELD_BINDINGS;
    const badgeVocabulary =
      collectionsOutcome.kind === 'success'
        ? buildBadgeVocabulary(collectionsOutcome.data)
        : NO_BADGE_VOCABULARY;
    const statusRoles =
      statusesOutcome.kind === 'success'
        ? buildStatusRoleMap(statusesOutcome.data)
        : NO_STATUS_ROLES;
    const roleCatalog =
      rolesOutcome.kind === 'success' ? buildRoleCatalogMap(rolesOutcome.data) : NO_ROLES;
    this.roots = buildRecordsView(outcome.data, categoryMap, orderMap, this.state, {
      iconOverrides: getTypeIconOverrides(),
      fieldBindings,
      badgeVocabulary,
      statusRoles,
      roleCatalog,
      labelMap,
    });
    this.expansion.prune(collectNodeIds(this.roots));
    this.changeEmitter.fire(undefined);
  }

  private failFrom(outcome: Exclude<SqOutcome<unknown>, { kind: 'success' }>): void {
    if (outcome.kind === 'spawn-error') {
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
