/**
 * The second activity-bar view's `TreeDataProvider` ("Roster"): renders the 3 fixed
 * reserved-type buckets (Roles/Skills/Operators) built by the vscode-free `domain/metaView.ts`.
 * Never groupable, but narrowable — `MetaViewState` (`domain/metaFilter.ts`) hides
 * archived-by-default entries and/or restricts to one status, a deliberately smaller state
 * machine than `SquadsTreeDataProvider`'s (no type filter or grouping: the 3 buckets already are
 * the type dimension). The fetch stays one unconditional `sq list --json --all` regardless of
 * `state` — unlike the work tree's `--all`-gated fetch, `--all` is needed unconditionally here so
 * toggling `showArchived` or picking any declared status back in doesn't require a second round
 * trip. Thin glue only, same split as `treeDataProvider.ts`: this module's vscode wiring is
 * exercised by the extension-host smoke test, `buildMetaView`/`domain/metaFilter.ts` are what's
 * unit-tested.
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
import {
  allDeclaredStatuses,
  DEFAULT_META_VIEW_STATE,
  type MetaViewState,
} from './domain/metaFilter';
import { buildMetaView } from './domain/metaView';
import { resolveSquadDir, type SquadDirEnvironment } from './domain/squadDir';
import {
  buildRoleCatalogMap,
  buildStatusRoleMap,
  NO_ROLES,
  NO_STATUS_ROLES,
} from './domain/statusRole';
import { buildTypeLabelMap, NO_LABELS } from './domain/typeLabels';
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
import { toTreeItem } from './treeItemRendering';

export class SquadsMetaTreeDataProvider implements vscode.TreeDataProvider<DisplayNode> {
  private readonly changeEmitter = new vscode.EventEmitter<DisplayNode | undefined>();
  readonly onDidChangeTreeData = this.changeEmitter.event;

  private roots: DisplayNode[] = [];
  // See `treeDataProvider.ts`'s matching field: a full-root refresh (this view's only kind)
  // does not preserve expand/collapse state on its own, even with a stable `item.id`.
  private readonly expansion = new ExpansionTracker();
  private state: MetaViewState = DEFAULT_META_VIEW_STATE;
  private knownStatuses: readonly string[] = [];

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

  get viewState(): MetaViewState {
    return this.state;
  }

  /** Every status the active spec declares (`domain/metaFilter.ts::allDeclaredStatuses`) —
   * feeds the status-filter quick-pick, same role `getKnownTypes` plays for the work tree's
   * type-filter quick-pick. */
  getKnownStatuses(): readonly string[] {
    return this.knownStatuses;
  }

  toggleShowArchived(): void {
    this.state = { ...this.state, showArchived: !this.state.showArchived };
    void this.refresh();
  }

  setStatusFilter(status: string | null): void {
    this.state = { ...this.state, statusFilter: status };
    void this.refresh();
  }

  clearFilter(): void {
    this.state = DEFAULT_META_VIEW_STATE;
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
    // Same catalogs the work tree fetches (the badge, status-role, and type catalogs), so the
    // roster's tooltip renders real collection badges, an Active role/skill/operator gets the
    // same colour highlight, and each bucket header resolves its spec-driven plural label
    // instead of a hardcoded literal; a failed fetch degrades to raw-code badge text / no
    // highlight / the raw type string as its own header rather than breaking the view
    // (`buildFieldBindings`/`buildBadgeVocabulary`/`buildStatusRoleMap`/`buildRoleCatalogMap`/
    // `buildTypeLabelMap` on an empty array is the same as each graceful-fallback default).
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
    const labelMap =
      catalogOutcome.kind === 'success' ? buildTypeLabelMap(catalogOutcome.data) : NO_LABELS;
    this.knownStatuses =
      statusesOutcome.kind === 'success' ? allDeclaredStatuses(statusesOutcome.data) : [];
    this.roots = buildMetaView(
      outcome.data,
      fieldBindings,
      badgeVocabulary,
      statusRoles,
      roleCatalog,
      labelMap,
      this.state,
    );
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
