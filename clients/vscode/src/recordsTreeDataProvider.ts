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
 *
 * Unlike its siblings, this view never renders an empty root list: the type catalog decides
 * which buckets exist at all here, so a failed catalog fetch is reported as an error and a
 * genuinely empty result gets a placeholder saying which kind of empty it is (`refresh`).
 */
import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import {
  buildBadgeVocabulary,
  buildFieldBindings,
  NO_BADGE_VOCABULARY,
} from './domain/badgeCatalog';
import {
  collectNodeIds,
  type DisplayNode,
  emptyStateDisplayNode,
  errorDisplayNode,
} from './domain/displayNode';
import { ExpansionTracker } from './domain/expansionTracker';
import { DEFAULT_RECORDS_VIEW_STATE, type RecordsViewState } from './domain/recordsFilter';
import { buildRecordsView, recordsEmptyStateMessage } from './domain/recordsView';
import { resolveSquadDir, type SquadDirEnvironment } from './domain/squadDir';
import {
  buildRoleCatalogMap,
  buildStatusRoleMap,
  NO_ROLES,
  NO_STATUS_ROLES,
} from './domain/statusRole';
import { buildCategoryMap } from './domain/typeCategory';
import { buildTypeLabelMap } from './domain/typeLabels';
import { buildTypeOrderMap } from './domain/typeOrder';
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
    // Same catalogs the work tree fetches (the badge and status-role catalogs), plus the type
    // catalog's `category` that decides which buckets exist at all. A failed badge/status-role
    // fetch degrades to raw-code badge text / no colour highlight rather than breaking the view.
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
    // The type catalog is load-bearing for THIS view in a way it isn't for its siblings: the
    // work tree and the roster still have rows to show without it, but every bucket here is a
    // `records`-category type, so no catalog means no buckets, no leaves, and — with no
    // `viewsWelcome` behind an empty tree — a wholly blank panel that looks like an empty squad
    // rather than a failed fetch. Reported as the error it is instead.
    if (catalogOutcome.kind !== 'success') {
      this.failFrom(catalogOutcome, 'Records unavailable — could not read the type catalog');
      return;
    }
    const categoryMap = buildCategoryMap(catalogOutcome.data);
    const orderMap = buildTypeOrderMap(catalogOutcome.data);
    const labelMap = buildTypeLabelMap(catalogOutcome.data);
    const fieldBindings = buildFieldBindings(catalogOutcome.data);
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
    const roots = buildRecordsView(outcome.data, categoryMap, orderMap, this.state, {
      iconOverrides: getTypeIconOverrides(),
      fieldBindings,
      badgeVocabulary,
      statusRoles,
      roleCatalog,
      labelMap,
    });
    // A successful build with nothing in it is a legitimate state (a spec declaring no records
    // type, or every record filtered out) — but an empty tree renders as a blank panel, so it
    // says which of the two it is. Calm placeholder, not the red error node above.
    this.roots =
      roots.length === 0 ? [emptyStateDisplayNode(recordsEmptyStateMessage(categoryMap))] : roots;
    this.expansion.prune(collectNodeIds(this.roots));
    this.changeEmitter.fire(undefined);
  }

  /** `context`, when given, prefixes the raw `sq` failure text so the reader knows which fetch
   * failed and what it cost them — the list fetch failing means no rows, the type-catalog fetch
   * failing means no buckets, and the bare stderr alone says neither. */
  private failFrom(
    outcome: Exclude<SqOutcome<unknown>, { kind: 'success' }>,
    context?: string,
  ): void {
    if (outcome.kind === 'spawn-error') {
      this.discovery.invalidate();
    }
    const message = describeFailure(outcome);
    this.fail(context === undefined ? message : `${context}: ${message}`);
  }

  private fail(message: string): void {
    this.roots = [errorDisplayNode(message)];
    this.notifyError(`Squads: ${message}`);
    this.changeEmitter.fire(undefined);
  }
}
