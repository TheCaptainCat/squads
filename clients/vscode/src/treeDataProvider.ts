/**
 * The activity-bar `TreeDataProvider`: renders the squad hierarchy by default, and switches to
 * a flat/filtered/grouped view once a filter or grouping is set. Thin glue only: it resolves
 * `sq`, calls the adapter, and turns the outcome into `vscode.TreeItem`s from
 * the vscode-free `DisplayNode`s built in `domain/`. That mapping is what's unit-tested; this
 * module's vscode wiring is exercised by reading + the deferred extension-host smoke test.
 */
import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import { type DisplayNode, errorDisplayNode } from './domain/displayNode';
import {
  buildFilteredGroupedView,
  distinctTypes,
  type GroupKey,
  type ListFilter,
  NO_FILTER,
} from './domain/listView';
import { buildTitleLookup, treeNodesToDisplay } from './domain/treeMapping';
import type { ProcessRunner } from './processRunner';
import { describeFailure, getList, getListSnapshot, getTree, type SqOutcome } from './sqAdapter';

export interface ViewState {
  readonly filter: ListFilter;
  readonly groupBy: readonly GroupKey[];
}

export const DEFAULT_VIEW_STATE: ViewState = { filter: NO_FILTER, groupBy: [] };

export function isFlatViewActive(state: ViewState): boolean {
  return state.filter.type !== null || state.filter.state !== null || state.groupBy.length > 0;
}

function toTreeItem(node: DisplayNode): vscode.TreeItem {
  const collapsibleState =
    node.children.length > 0
      ? vscode.TreeItemCollapsibleState.Collapsed
      : vscode.TreeItemCollapsibleState.None;
  const item = new vscode.TreeItem(node.label, collapsibleState);
  item.id = node.id;
  if (node.description !== '') {
    item.description = node.description;
  }
  if (node.tooltip !== '') {
    item.tooltip = node.tooltip;
  }
  item.iconPath = node.blocked
    ? new vscode.ThemeIcon(node.iconId, new vscode.ThemeColor('problemsErrorIcon.foreground'))
    : new vscode.ThemeIcon(node.iconId);
  if (node.itemId !== null) {
    item.contextValue = 'squadsItem';
    item.command = {
      command: 'squads.openItemPreview',
      title: 'Open in Preview',
      arguments: [node.itemId],
    };
  }
  return item;
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

  setGroupBy(groupBy: readonly GroupKey[]): void {
    this.state = { ...this.state, groupBy };
    void this.refresh();
  }

  clearFilterAndGrouping(): void {
    this.state = DEFAULT_VIEW_STATE;
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

    if (isFlatViewActive(this.state)) {
      const snapshot = await getListSnapshot(this.runner, invocation, this.workspaceRoot);
      if (snapshot.kind !== 'success') {
        this.failFrom(snapshot);
        return;
      }
      this.roots = buildFilteredGroupedView(
        snapshot.data.items,
        snapshot.data.openIds,
        this.state.filter,
        this.state.groupBy,
      );
      this.knownItemTypes = distinctTypes(snapshot.data.items);
      this.changeEmitter.fire(undefined);
      return;
    }

    // Hierarchy render only needs titles + known types (buildTitleLookup / distinctTypes) — no
    // open/closed classification — so a single `sq list --all` suffices; the double-fetch
    // getListSnapshot is reserved for the flat/grouped view above, which needs openIds.
    const [treeOutcome, listOutcome] = await Promise.all([
      getTree(this.runner, invocation, this.workspaceRoot),
      getList(this.runner, invocation, this.workspaceRoot, ['--all']),
    ]);
    if (treeOutcome.kind !== 'success') {
      this.failFrom(treeOutcome);
      return;
    }
    const titles = listOutcome.kind === 'success' ? buildTitleLookup(listOutcome.data) : undefined;
    if (listOutcome.kind === 'success') {
      this.knownItemTypes = distinctTypes(listOutcome.data);
    }
    this.roots = treeNodesToDisplay(treeOutcome.data, titles);
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
